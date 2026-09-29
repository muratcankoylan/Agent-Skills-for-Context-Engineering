#!/usr/bin/env python3
"""Persistent, effect-free scheduler for local production rehearsals.

This module is a pre-acceptance implementation artifact. It can register UTC
interval schedules and produce fenced work orders, but it deliberately cannot
execute network, model, GitHub, or repository mutation effects. A future
accepted dispatcher must consume the work-order contract through a reducer.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import stat
import sys
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable, Mapping


SCHEMA_VERSION = 1
APPLICATION_ID = 1_095_519_604
DEFAULT_BUSY_TIMEOUT_MS = 5_000
MAX_INTERVAL_SECONDS = 31 * 24 * 60 * 60
MAX_LEASE_SECONDS = 24 * 60 * 60
MAX_TICK_ORDERS = 1_000
MAX_PAYLOAD_BYTES = 16_384
MAX_READ_ONLY_DATABASE_BYTES = 32 * 1024 * 1024
SCHEDULE_ID = re.compile(r"^[a-z][a-z0-9-]{0,62}$")
WORK_ORDER_NAMESPACE = uuid.UUID("52af88c5-426b-523e-aadd-7a71e34fe41c")
ALLOWED_ACTIONS = frozenset(
    {
        "benchmark.catalog",
        "discover.sources",
        "health.snapshot",
        "reconcile.outbox",
    }
)


class SchedulerError(RuntimeError):
    code = "SCHEDULER_ERROR"

    def __init__(self, message: str):
        super().__init__(f"[{self.code}] {message}")
        self.safe_message = message


class InvalidSchedule(SchedulerError):
    code = "INVALID_SCHEDULE"


class InvalidTime(SchedulerError):
    code = "INVALID_TIME"


class SchedulerStoreUnsafe(SchedulerError):
    code = "SCHEDULER_STORE_UNSAFE"


class WorkOrderConflict(SchedulerError):
    code = "WORK_ORDER_CONFLICT"


class WorkOrderNotFound(SchedulerError):
    code = "WORK_ORDER_NOT_FOUND"


@dataclass(frozen=True)
class Schedule:
    schedule_id: str
    action: str
    interval_seconds: int
    next_due_at: str
    enabled: bool
    payload: dict[str, Any]
    version: int


@dataclass(frozen=True)
class WorkOrder:
    work_order_id: str
    schedule_id: str
    action: str
    due_at: str
    state: str
    attempt: int
    generation: int
    lease_owner: str | None
    lease_until: str | None
    fence: str | None
    payload: dict[str, Any]
    result: dict[str, Any] | None


def parse_utc(value: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise InvalidTime("timestamp must be a non-empty string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise InvalidTime("timestamp must be ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise InvalidTime("timestamp must include a UTC offset")
    parsed = parsed.astimezone(UTC)
    if parsed.microsecond:
        raise InvalidTime("timestamp must use whole-second precision")
    return parsed


def format_utc(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise InvalidTime("timestamp must include a UTC offset")
    return (
        value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )


def _canonical_json(value: Mapping[str, Any]) -> str:
    if not isinstance(value, Mapping):
        raise InvalidSchedule("payload must be an object")
    try:
        encoded = json.dumps(
            dict(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise InvalidSchedule("payload must be finite JSON") from exc
    if len(encoded.encode("utf-8")) > MAX_PAYLOAD_BYTES:
        raise InvalidSchedule("payload exceeds byte limit")
    decoded = json.loads(encoded)
    if not isinstance(
        decoded, dict
    ):  # Defensive: Mapping subclasses cannot alter shape.
        raise InvalidSchedule("payload must encode as an object")
    return encoded


def _validate_schedule(
    schedule_id: str,
    action: str,
    interval_seconds: int,
    next_due_at: str,
    enabled: bool,
    payload: Mapping[str, Any],
) -> tuple[str, str]:
    if not isinstance(schedule_id, str) or not SCHEDULE_ID.fullmatch(schedule_id):
        raise InvalidSchedule("schedule_id must match the canonical identifier profile")
    if action not in ALLOWED_ACTIONS:
        raise InvalidSchedule("action is not in the effect-free rehearsal allowlist")
    if isinstance(interval_seconds, bool) or not isinstance(interval_seconds, int):
        raise InvalidSchedule("interval_seconds must be an integer")
    if not 1 <= interval_seconds <= MAX_INTERVAL_SECONDS:
        raise InvalidSchedule("interval_seconds is outside the bounded range")
    if not isinstance(enabled, bool):
        raise InvalidSchedule("enabled must be a boolean")
    canonical_due = format_utc(parse_utc(next_due_at))
    return canonical_due, _canonical_json(payload)


def _safe_database_path(path: Path, *, create: bool = True) -> Path:
    requested = path.absolute()
    current = requested.parent
    while current != current.parent:
        if current.is_symlink():
            raise SchedulerStoreUnsafe("database ancestors cannot be symlink aliases")
        current = current.parent
    if requested.exists() or requested.is_symlink():
        metadata = os.lstat(requested)
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
            raise SchedulerStoreUnsafe("database must be a direct regular file")
        if metadata.st_nlink != 1:
            raise SchedulerStoreUnsafe("database must have exactly one hard link")
    parent = requested.parent
    if create:
        parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    elif not requested.is_file() or not parent.is_dir():
        raise SchedulerStoreUnsafe("read-only scheduler storage must already exist")
    canonical_parent = parent.resolve(strict=True)
    canonical_path = canonical_parent / requested.name
    current = canonical_parent
    while True:
        metadata = os.lstat(current)
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise SchedulerStoreUnsafe("database ancestors must be real directories")
        if current == current.parent:
            break
        current = current.parent
    return canonical_path


def _read_only_database_state(path: Path) -> tuple:
    """Bounded checkpointed-only snapshot; never create/checkpoint sidecars.

    Immutable SQLite reads skip locking/change detection. The caller must hold
    the run's existing cooperative lock; before/after snapshots detect drift.
    Nonempty WAL or rollback journals are rejected, never silently ignored.
    """
    if not hasattr(os, "O_NOFOLLOW"):
        raise SchedulerStoreUnsafe("read-only scheduler requires no-follow opens")
    path = _safe_database_path(path, create=False)
    if path.parent.stat().st_mode & 0o077:
        raise SchedulerStoreUnsafe("read-only scheduler directory must be private")

    def signature(info):
        return (
            info.st_dev,
            info.st_ino,
            info.st_mode,
            info.st_nlink,
            info.st_size,
            info.st_mtime_ns,
            info.st_ctime_ns,
        )

    sidecars = []
    for suffix in ("-wal", "-shm", "-journal"):
        sidecar = Path(str(path) + suffix)
        try:
            info = sidecar.lstat()
        except FileNotFoundError:
            sidecars.append(None)
            continue
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_nlink != 1
            or info.st_mode & 0o077
            or info.st_size > 1024 * 1024
        ):
            raise SchedulerStoreUnsafe("read-only scheduler sidecar is unsafe")
        if suffix != "-shm" and info.st_size:
            raise SchedulerStoreUnsafe(
                "read-only verification requires a checkpointed scheduler"
            )
        sidecars.append(signature(info))
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_mode & 0o077
            or not 100 <= before.st_size <= MAX_READ_ONLY_DATABASE_BYTES
        ):
            raise SchedulerStoreUnsafe(
                "read-only scheduler file is unsafe or exceeds bounds"
            )
        digest, received = hashlib.sha256(), 0
        while received <= MAX_READ_ONLY_DATABASE_BYTES:
            chunk = os.read(
                descriptor, min(65536, MAX_READ_ONLY_DATABASE_BYTES + 1 - received)
            )
            if not chunk:
                break
            received += len(chunk)
            digest.update(chunk)
        after = os.fstat(descriptor)
        if received != before.st_size or signature(before) != signature(after):
            raise SchedulerStoreUnsafe("scheduler changed during read-only snapshot")
        return signature(after), digest.hexdigest(), tuple(sidecars)
    finally:
        os.close(descriptor)


_SCHEMA_SQL = f"""
BEGIN IMMEDIATE;
CREATE TABLE IF NOT EXISTS schedules (
    schedule_id TEXT PRIMARY KEY,
    action TEXT NOT NULL,
    interval_seconds INTEGER NOT NULL CHECK(interval_seconds > 0),
    next_due_at TEXT NOT NULL,
    enabled INTEGER NOT NULL CHECK(enabled IN (0, 1)),
    payload_json TEXT NOT NULL,
    version INTEGER NOT NULL CHECK(version > 0),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
) STRICT;
CREATE TABLE IF NOT EXISTS work_orders (
    work_order_id TEXT PRIMARY KEY,
    schedule_id TEXT NOT NULL REFERENCES schedules(schedule_id),
    action TEXT NOT NULL,
    due_at TEXT NOT NULL,
    state TEXT NOT NULL CHECK(state IN ('queued','running','succeeded','failed')),
    attempt INTEGER NOT NULL CHECK(attempt >= 0),
    generation INTEGER NOT NULL CHECK(generation >= 0),
    lease_owner TEXT,
    lease_until TEXT,
    fence TEXT,
    payload_json TEXT NOT NULL,
    result_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(schedule_id, due_at)
) STRICT;
CREATE INDEX IF NOT EXISTS work_orders_claim
    ON work_orders(state, due_at, lease_until, work_order_id);
PRAGMA application_id = {APPLICATION_ID};
PRAGMA user_version = {SCHEMA_VERSION};
COMMIT;
"""


class LocalScheduler:
    """SQLite scheduler with transactional enqueue and lease fencing."""

    def __init__(
        self,
        database: Path,
        *,
        busy_timeout_ms: int = DEFAULT_BUSY_TIMEOUT_MS,
        read_only: bool = False,
    ):
        if type(read_only) is not bool:
            raise SchedulerStoreUnsafe("read_only must be a boolean")
        if isinstance(busy_timeout_ms, bool) or not isinstance(busy_timeout_ms, int):
            raise SchedulerStoreUnsafe("busy_timeout_ms must be an integer")
        if not 1 <= busy_timeout_ms <= 60_000:
            raise SchedulerStoreUnsafe("busy_timeout_ms is outside the bounded range")
        self.read_only = read_only
        self.database = _safe_database_path(database, create=not read_only)
        self.busy_timeout_ms = busy_timeout_ms
        self._read_only_state = (
            _read_only_database_state(self.database) if read_only else None
        )
        if not read_only:
            self._initialize()

    def _check_read_only_state(self) -> None:
        if (
            self.read_only
            and _read_only_database_state(self.database) != self._read_only_state
        ):
            raise SchedulerStoreUnsafe("read-only scheduler storage changed")

    def _require_writable(self) -> None:
        if self.read_only:
            raise SchedulerStoreUnsafe("read-only scheduler cannot mutate work")

    def _connect(self) -> sqlite3.Connection:
        if self.read_only:
            self._check_read_only_state()
            # https://www.sqlite.org/uri.html: immutable forces read-only and
            # disables SQLite locks/change detection. Accept only checkpointed
            # storage under the caller's cooperative lock, never live WAL.
            connection = sqlite3.connect(
                self.database.as_uri() + "?mode=ro&immutable=1",
                uri=True,
                isolation_level=None,
            )
            try:
                connection.row_factory = sqlite3.Row
                connection.execute("PRAGMA query_only = ON")
                connection.execute("PRAGMA temp_store = MEMORY")
                if (
                    connection.execute("PRAGMA application_id").fetchone()[0]
                    != APPLICATION_ID
                    or connection.execute("PRAGMA user_version").fetchone()[0]
                    != SCHEMA_VERSION
                ):
                    raise SchedulerStoreUnsafe(
                        "database identity or version is incompatible"
                    )
                self._validate_schema(connection)
                if connection.execute("PRAGMA quick_check").fetchall()[0][0] != "ok":
                    raise SchedulerStoreUnsafe("read-only scheduler is corrupt")
                self._check_read_only_state()
                return connection
            except BaseException:
                connection.close()
                raise
        _safe_database_path(self.database)
        for suffix in ("-wal", "-shm"):
            sidecar = Path(str(self.database) + suffix)
            if sidecar.exists() or sidecar.is_symlink():
                info = sidecar.lstat()
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                    raise SchedulerStoreUnsafe(
                        "database sidecars must be direct single-link files"
                    )
        connection = sqlite3.connect(
            self.database,
            timeout=self.busy_timeout_ms / 1_000,
            isolation_level=None,
        )
        connection.row_factory = sqlite3.Row
        connection.execute(f"PRAGMA busy_timeout = {self.busy_timeout_ms}")
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA synchronous = FULL")
        return connection

    def _initialize(self) -> None:
        connection = self._connect()
        try:
            # Inspect identity before any adoption or WAL mutation. Arbitrary
            # databases, including future versions, must remain untouched.
            application_id = connection.execute("PRAGMA application_id").fetchone()[0]
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            objects = connection.execute("SELECT name FROM sqlite_master").fetchall()
            fresh = application_id == 0 and version == 0 and not objects
            if not fresh and (
                application_id != APPLICATION_ID or version != SCHEMA_VERSION
            ):
                raise SchedulerStoreUnsafe(
                    "database identity or version is incompatible"
                )
            if not fresh:
                self._validate_schema(connection)
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute("PRAGMA synchronous = FULL")
            connection.executescript(_SCHEMA_SQL)
            application_id = connection.execute("PRAGMA application_id").fetchone()[0]
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if application_id != APPLICATION_ID or version != SCHEMA_VERSION:
                raise SchedulerStoreUnsafe(
                    "database identity or version is incompatible"
                )
            self._validate_schema(connection)
            os.chmod(self.database, 0o600)
        except sqlite3.Error as exc:
            raise SchedulerStoreUnsafe(
                "scheduler database initialization failed"
            ) from exc
        finally:
            connection.close()

    @staticmethod
    def _validate_schema(connection: sqlite3.Connection) -> None:
        # Match constraints, indexes, triggers, and tables, not just columns.
        # The same DDL defines fresh storage and the expected schema identity.
        reference = sqlite3.connect(":memory:")
        try:
            reference.executescript(_SCHEMA_SQL)
            query = "SELECT type, name, tbl_name, sql FROM sqlite_master ORDER BY type, name"
            expected = [tuple(row) for row in reference.execute(query)]
            observed = [tuple(row) for row in connection.execute(query)]
            if observed != expected:
                raise SchedulerStoreUnsafe(
                    "scheduler schema differs from its declared version"
                )
        finally:
            reference.close()

    def register(
        self,
        *,
        schedule_id: str,
        action: str,
        interval_seconds: int,
        next_due_at: str,
        payload: Mapping[str, Any] | None = None,
        enabled: bool = True,
        observed_at: str,
    ) -> Schedule:
        self._require_writable()
        observed = format_utc(parse_utc(observed_at))
        canonical_due, payload_json = _validate_schedule(
            schedule_id,
            action,
            interval_seconds,
            next_due_at,
            enabled,
            {} if payload is None else payload,
        )
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            current = connection.execute(
                "SELECT * FROM schedules WHERE schedule_id = ?", (schedule_id,)
            ).fetchone()
            if current is None:
                version = 1
                connection.execute(
                    """INSERT INTO schedules(
                           schedule_id, action, interval_seconds, next_due_at, enabled,
                           payload_json, version, created_at, updated_at
                       ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        schedule_id,
                        action,
                        interval_seconds,
                        canonical_due,
                        int(enabled),
                        payload_json,
                        version,
                        observed,
                        observed,
                    ),
                )
            else:
                identical = (
                    current["action"] == action
                    and current["interval_seconds"] == interval_seconds
                    and current["next_due_at"] == canonical_due
                    and current["enabled"] == int(enabled)
                    and current["payload_json"] == payload_json
                )
                if identical:
                    version = int(current["version"])
                else:
                    version = int(current["version"]) + 1
                    connection.execute(
                        """UPDATE schedules SET action = ?, interval_seconds = ?,
                               next_due_at = ?, enabled = ?, payload_json = ?,
                               version = ?, updated_at = ? WHERE schedule_id = ?""",
                        (
                            action,
                            interval_seconds,
                            canonical_due,
                            int(enabled),
                            payload_json,
                            version,
                            observed,
                            schedule_id,
                        ),
                    )
            connection.execute("COMMIT")
        except BaseException:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()
        return self.get_schedule(schedule_id)

    def get_schedule(self, schedule_id: str) -> Schedule:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT * FROM schedules WHERE schedule_id = ?", (schedule_id,)
            ).fetchone()
        finally:
            connection.close()
            self._check_read_only_state()
        if row is None:
            raise InvalidSchedule("schedule does not exist")
        return _schedule_from_row(row)

    def tick(self, *, observed_at: str, max_orders: int = 100) -> tuple[WorkOrder, ...]:
        self._require_writable()
        now = parse_utc(observed_at)
        now_text = format_utc(now)
        if isinstance(max_orders, bool) or not isinstance(max_orders, int):
            raise InvalidSchedule("max_orders must be an integer")
        if not 0 <= max_orders <= MAX_TICK_ORDERS:
            raise InvalidSchedule("max_orders is outside the bounded range")
        if max_orders == 0:
            return ()
        created_ids: list[str] = []
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            schedules = connection.execute(
                "SELECT * FROM schedules WHERE enabled = 1 ORDER BY next_due_at, schedule_id"
            ).fetchall()
            remaining = max_orders
            for row in schedules:
                due = parse_utc(row["next_due_at"])
                interval = timedelta(seconds=int(row["interval_seconds"]))
                while due <= now and remaining > 0:
                    due_text = format_utc(due)
                    order_id = _work_order_id(row["schedule_id"], due_text)
                    connection.execute(
                        """INSERT OR IGNORE INTO work_orders(
                               work_order_id, schedule_id, action, due_at, state,
                               attempt, generation, payload_json, created_at, updated_at
                           ) VALUES (?, ?, ?, ?, 'queued', 0, 0, ?, ?, ?)""",
                        (
                            order_id,
                            row["schedule_id"],
                            row["action"],
                            due_text,
                            row["payload_json"],
                            now_text,
                            now_text,
                        ),
                    )
                    if connection.execute("SELECT changes()").fetchone()[0] == 1:
                        created_ids.append(order_id)
                    else:
                        existing = connection.execute(
                            "SELECT action, payload_json FROM work_orders WHERE work_order_id = ?",
                            (order_id,),
                        ).fetchone()
                        if existing is None or (
                            existing["action"] != row["action"]
                            or existing["payload_json"] != row["payload_json"]
                        ):
                            raise WorkOrderConflict(
                                "existing schedule slot is bound to different work"
                            )
                    # Bound historical-slot scanning as well as new inserts. A
                    # crash can leave an already-created slot while the
                    # schedule cursor still points at it; duplicates must not
                    # turn one tick into an unbounded catch-up loop.
                    remaining -= 1
                    due += interval
                connection.execute(
                    "UPDATE schedules SET next_due_at = ?, updated_at = ? WHERE schedule_id = ?",
                    (format_utc(due), now_text, row["schedule_id"]),
                )
                if remaining == 0:
                    break
            connection.execute("COMMIT")
        except BaseException:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()
        return tuple(self.get_work_order(order_id) for order_id in created_ids)

    def claim(
        self,
        *,
        worker_id: str,
        observed_at: str,
        lease_seconds: int,
        max_attempts: int = 3,
    ) -> WorkOrder | None:
        self._require_writable()
        if not isinstance(worker_id, str) or not SCHEDULE_ID.fullmatch(worker_id):
            raise WorkOrderConflict(
                "worker_id must match the canonical identifier profile"
            )
        if isinstance(lease_seconds, bool) or not isinstance(lease_seconds, int):
            raise WorkOrderConflict("lease_seconds must be an integer")
        if not 1 <= lease_seconds <= MAX_LEASE_SECONDS:
            raise WorkOrderConflict("lease_seconds is outside the bounded range")
        if (
            isinstance(max_attempts, bool)
            or not isinstance(max_attempts, int)
            or not 1 <= max_attempts <= 100
        ):
            raise WorkOrderConflict("max_attempts must be a positive integer")
        now = parse_utc(observed_at)
        now_text = format_utc(now)
        lease_until = format_utc(now + timedelta(seconds=lease_seconds))
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """UPDATE work_orders SET state = 'failed', lease_owner = NULL,
                       lease_until = NULL, result_json = ?, updated_at = ?
                   WHERE attempt >= ? AND (state = 'queued' OR
                       (state = 'running' AND lease_until <= ?))""",
                (
                    _canonical_json({"error_code": "ATTEMPTS_EXHAUSTED"}),
                    now_text,
                    max_attempts,
                    now_text,
                ),
            )
            row = connection.execute(
                """SELECT * FROM work_orders
                   WHERE attempt < ? AND due_at <= ? AND (
                       state = 'queued' OR
                       (state = 'running' AND lease_until <= ?)
                   )
                   ORDER BY due_at, work_order_id LIMIT 1""",
                (max_attempts, now_text, now_text),
            ).fetchone()
            if row is None:
                connection.execute("COMMIT")
                return None
            generation = int(row["generation"]) + 1
            attempt = int(row["attempt"]) + 1
            fence = f"{row['work_order_id']}:{generation}"
            connection.execute(
                """UPDATE work_orders SET state = 'running', attempt = ?, generation = ?,
                       lease_owner = ?, lease_until = ?, fence = ?, updated_at = ?
                   WHERE work_order_id = ?""",
                (
                    attempt,
                    generation,
                    worker_id,
                    lease_until,
                    fence,
                    now_text,
                    row["work_order_id"],
                ),
            )
            connection.execute("COMMIT")
            return self.get_work_order(row["work_order_id"])
        except BaseException:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()

    def complete(
        self,
        work_order_id: str,
        *,
        fence: str,
        result: Mapping[str, Any],
        observed_at: str,
    ) -> WorkOrder:
        return self._finish(
            work_order_id,
            fence=fence,
            result=result,
            observed_at=observed_at,
            retry=False,
            final_state="succeeded",
        )

    def fail(
        self,
        work_order_id: str,
        *,
        fence: str,
        result: Mapping[str, Any],
        observed_at: str,
        retry: bool,
    ) -> WorkOrder:
        return self._finish(
            work_order_id,
            fence=fence,
            result=result,
            observed_at=observed_at,
            retry=retry,
            final_state="failed",
        )

    def _finish(
        self,
        work_order_id: str,
        *,
        fence: str,
        result: Mapping[str, Any],
        observed_at: str,
        retry: bool,
        final_state: str,
    ) -> WorkOrder:
        self._require_writable()
        if not isinstance(retry, bool):
            raise WorkOrderConflict("retry must be a boolean")
        now_text = format_utc(parse_utc(observed_at))
        result_json = _canonical_json(result)
        state = "queued" if retry else final_state
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM work_orders WHERE work_order_id = ?", (work_order_id,)
            ).fetchone()
            if row is None:
                raise WorkOrderNotFound("work order does not exist")
            if (
                row["state"] == state
                and row["fence"] == fence
                and row["result_json"] == result_json
            ):
                connection.execute("COMMIT")
                return _work_order_from_row(row)
            if row["state"] != "running" or row["fence"] != fence:
                raise WorkOrderConflict(
                    "work order fence is stale or state is not running"
                )
            if now_text < row["updated_at"] or now_text >= row["lease_until"]:
                raise WorkOrderConflict(
                    "completion timestamp is outside the active lease"
                )
            connection.execute(
                """UPDATE work_orders SET state = ?, lease_owner = NULL,
                       lease_until = NULL, result_json = ?, updated_at = ?
                   WHERE work_order_id = ?""",
                (state, result_json, now_text, work_order_id),
            )
            connection.execute("COMMIT")
        except BaseException:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()
        return self.get_work_order(work_order_id)

    def get_work_order(self, work_order_id: str) -> WorkOrder:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT * FROM work_orders WHERE work_order_id = ?", (work_order_id,)
            ).fetchone()
        finally:
            connection.close()
            self._check_read_only_state()
        if row is None:
            raise WorkOrderNotFound("work order does not exist")
        return _work_order_from_row(row)

    def list_work_orders(self) -> tuple[WorkOrder, ...]:
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT * FROM work_orders ORDER BY due_at, work_order_id"
            ).fetchall()
        finally:
            connection.close()
            self._check_read_only_state()
        return tuple(_work_order_from_row(row) for row in rows)


def _work_order_id(schedule_id: str, due_at: str) -> str:
    return f"wo_{uuid.uuid5(WORK_ORDER_NAMESPACE, f'{schedule_id}:{due_at}')}"


def _schedule_from_row(row: sqlite3.Row) -> Schedule:
    return Schedule(
        schedule_id=row["schedule_id"],
        action=row["action"],
        interval_seconds=int(row["interval_seconds"]),
        next_due_at=row["next_due_at"],
        enabled=bool(row["enabled"]),
        payload=json.loads(row["payload_json"]),
        version=int(row["version"]),
    )


def _work_order_from_row(row: sqlite3.Row) -> WorkOrder:
    return WorkOrder(
        work_order_id=row["work_order_id"],
        schedule_id=row["schedule_id"],
        action=row["action"],
        due_at=row["due_at"],
        state=row["state"],
        attempt=int(row["attempt"]),
        generation=int(row["generation"]),
        lease_owner=row["lease_owner"],
        lease_until=row["lease_until"],
        fence=row["fence"],
        payload=json.loads(row["payload_json"]),
        result=json.loads(row["result_json"])
        if row["result_json"] is not None
        else None,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    sub = parser.add_subparsers(dest="command", required=True)
    register = sub.add_parser("register")
    register.add_argument("--id", required=True)
    register.add_argument("--action", choices=sorted(ALLOWED_ACTIONS), required=True)
    register.add_argument("--interval-seconds", type=int, required=True)
    register.add_argument("--next-due-at", required=True)
    register.add_argument("--observed-at", required=True)
    register.add_argument("--payload-json", default="{}")
    tick = sub.add_parser("tick")
    tick.add_argument("--observed-at", required=True)
    tick.add_argument("--max-orders", type=int, default=100)
    sub.add_parser("status")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = _parser().parse_args(list(argv) if argv is not None else None)
    try:
        scheduler = LocalScheduler(args.database)
        if args.command == "register":
            try:
                payload = json.loads(args.payload_json)
            except json.JSONDecodeError as exc:
                raise InvalidSchedule("payload-json must be valid JSON") from exc
            result: Any = scheduler.register(
                schedule_id=args.id,
                action=args.action,
                interval_seconds=args.interval_seconds,
                next_due_at=args.next_due_at,
                payload=payload,
                observed_at=args.observed_at,
            )
            output = asdict(result)
        elif args.command == "tick":
            output = {
                "authority": "none",
                "activation_enabled": False,
                "work_orders": [
                    asdict(item)
                    for item in scheduler.tick(
                        observed_at=args.observed_at, max_orders=args.max_orders
                    )
                ],
            }
        else:
            orders = scheduler.list_work_orders()
            output = {
                "authority": "none",
                "activation_enabled": False,
                "work_orders": [asdict(item) for item in orders],
            }
        print(json.dumps(output, sort_keys=True, allow_nan=False))
        return 0
    except SchedulerError as exc:
        print(
            json.dumps({"ok": False, "code": exc.code, "error": exc.safe_message}),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
