#!/usr/bin/env python3
"""Deterministic, rebuildable research-run projection for SPEC-004."""

from __future__ import annotations

import fcntl
import os
import sqlite3
import tempfile
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterator, Mapping
from urllib.parse import quote

try:
    from event_store import (  # type: ignore[import-not-found]
        EventStore,
        EventStoreError,
        JournalCorrupt,
        _fsync_directory,
        _migration_statements,
        _validated_time,
    )
    from schema_contract import (  # type: ignore[import-not-found]
        ContractError,
        canonical_digest,
        parse_json_strict,
        sha256_bytes,
    )
except ModuleNotFoundError:
    from researcher.scripts.event_store import (
        EventStore,
        EventStoreError,
        JournalCorrupt,
        _fsync_directory,
        _migration_statements,
        _validated_time,
    )
    from researcher.scripts.schema_contract import (
        ContractError,
        canonical_digest,
        parse_json_strict,
        sha256_bytes,
    )


ROOT = Path(__file__).resolve().parents[2]
PROJECTOR_NAME = "research-run"
PROJECTOR_VERSION = "1.0.0"
DEFAULT_PROJECTION_MANIFEST = (
    ROOT / "researcher" / "event_journal" / "projections" / "research-run" / "manifest.json"
)
EMPTY_PROJECTION_TIME = "1970-01-01T00:00:00Z"
RUN_STATES = {
    "initialized",
    "retrieved",
    "evaluated",
    "proposed",
    "novelty_checked",
    "validated",
    "pr_ready",
    "closed",
}


class ProjectorError(EventStoreError):
    code = "PROJECTOR_ERROR"


class ProjectionCorrupt(ProjectorError):
    code = "PROJECTION_CORRUPT"


@dataclass(frozen=True)
class RunProjection:
    subject_id: str
    subject_version: int
    current_state: str
    close_status: str | None
    last_occurred_at: str
    classification: str
    last_sequence: int
    last_event_id: str

    def digest_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProjectionQuarantine:
    subject_kind: str
    subject_id: str
    first_sequence: int
    event_id: str
    reason_code: str

    def digest_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProjectionSnapshot:
    projector_name: str
    projector_version: str
    last_sequence: int
    source_hash: str | None
    state_digest: str
    projections: tuple[RunProjection, ...]
    quarantines: tuple[ProjectionQuarantine, ...]


def projection_state_digest(
    projections: list[RunProjection] | tuple[RunProjection, ...],
    quarantines: list[ProjectionQuarantine] | tuple[ProjectionQuarantine, ...],
) -> str:
    """Digest stable materialized state; rebuild time is deliberately excluded."""

    return canonical_digest(
        {
            "profile": "research-run-projection-v1",
            "projections": [
                item.digest_record() for item in sorted(projections, key=lambda item: item.subject_id)
            ],
            "quarantines": [
                item.digest_record()
                for item in sorted(
                    quarantines,
                    key=lambda item: (item.subject_kind, item.subject_id),
                )
            ],
        }
    )


def _schema_fingerprint(connection: sqlite3.Connection) -> str:
    rows = connection.execute(
        """
        SELECT type, name, tbl_name, sql
        FROM sqlite_schema
        ORDER BY type, name
        """
    ).fetchall()
    return canonical_digest(
        [
            {
                "type": str(row["type"]),
                "name": str(row["name"]),
                "table": str(row["tbl_name"]),
                "sql": str(row["sql"]),
            }
            for row in rows
        ]
    )


class ResearchRunProjector:
    """Pure journal reducer plus an independently replaceable materialized view."""

    def __init__(
        self,
        store: EventStore,
        path: Path | None = None,
        *,
        manifest_path: Path = DEFAULT_PROJECTION_MANIFEST,
    ) -> None:
        self.store = store
        self.path = (
            Path(path).absolute()
            if path is not None
            else store.path.with_name(f"{store.path.name}.research-run-projection.sqlite3")
        )
        self._assert_separate_paths()
        self.manifest_path = Path(manifest_path).absolute()
        self._manifest, self._schema_statements = self._load_contract()
        self._expected_schema_fingerprint = self._build_expected_schema_fingerprint()

    @property
    def application_id(self) -> int:
        return int(self._manifest["application_id"])

    @property
    def user_version(self) -> int:
        return int(self._manifest["user_version"])

    def _load_contract(self) -> tuple[dict[str, Any], tuple[str, ...]]:
        try:
            value = parse_json_strict(self.manifest_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ContractError) as exc:
            raise ProjectionCorrupt("projection schema manifest is unreadable; rebuild contract") from exc
        required = {
            "schema_version",
            "application_id",
            "user_version",
            "projector_name",
            "projector_version",
            "path",
            "digest",
        }
        if not isinstance(value, dict) or set(value) != required:
            raise ProjectionCorrupt("projection schema manifest fields differ from the contract")
        if (
            value["schema_version"] != "1.0.0"
            or value["projector_name"] != PROJECTOR_NAME
            or value["projector_version"] != PROJECTOR_VERSION
            or isinstance(value["application_id"], bool)
            or not isinstance(value["application_id"], int)
            or not 1 <= value["application_id"] <= 0x7FFFFFFF
            or value["user_version"] != 1
        ):
            raise ProjectionCorrupt("projection schema manifest metadata is invalid")
        contract_root = (
            ROOT / "researcher" / "event_journal" / "projections" / "research-run"
        ).resolve()
        schema_path = (ROOT / str(value["path"])).resolve()
        try:
            schema_path.relative_to(contract_root)
        except ValueError as exc:
            raise ProjectionCorrupt("projection schema path escapes its public contract root") from exc
        if not schema_path.is_file() or schema_path.is_symlink():
            raise ProjectionCorrupt("projection schema is missing or not a regular file")
        try:
            body = schema_path.read_bytes()
            statements = tuple(_migration_statements(body.decode("utf-8")))
        except (OSError, UnicodeError, EventStoreError) as exc:
            raise ProjectionCorrupt("projection schema bytes are unreadable") from exc
        if sha256_bytes(body) != value["digest"]:
            raise ProjectionCorrupt("projection schema bytes disagree with their pinned digest")
        return value, statements

    def _build_expected_schema_fingerprint(self) -> str:
        connection = sqlite3.connect(":memory:", isolation_level=None)
        connection.row_factory = sqlite3.Row
        try:
            for statement in self._schema_statements:
                connection.execute(statement)
            return _schema_fingerprint(connection)
        except sqlite3.Error as exc:
            raise ProjectionCorrupt("pinned projection schema cannot be constructed") from exc
        finally:
            connection.close()

    def _assert_separate_paths(self) -> None:
        """Reject output/lock aliases before touching authoritative journal files.

        Check reserved names even when SQLite has not created its sidecars yet.
        Resolved names catch ancestor symlinks; inode identity catches hardlinks.
        These cooperative local-process checks are not filesystem race isolation.
        """

        protected = [
            self.store.path,
            *(Path(f"{self.store.path}{suffix}") for suffix in ("-wal", "-shm", "-journal")),
            self.store.operator_halt_path,
        ]
        destinations = (self.path, Path(f"{self.path}.lock"))

        def inode(path: Path) -> tuple[int, int] | None:
            try:
                status = path.stat()
            except FileNotFoundError:
                return None
            return status.st_dev, status.st_ino

        try:
            reserved_names = {
                name
                for path in protected
                for name in (Path(os.path.abspath(path)), path.resolve())
            }
            reserved_inodes = {identity for path in protected if (identity := inode(path)) is not None}
            for path in destinations:
                if (
                    Path(os.path.abspath(path)) in reserved_names
                    or path.resolve() in reserved_names
                    or (inode(path) in reserved_inodes)
                ):
                    raise ProjectionCorrupt("projection output or lock aliases journal storage")
        except ProjectionCorrupt:
            raise
        except (OSError, RuntimeError, ValueError) as exc:
            raise ProjectionCorrupt("projection/journal path separation cannot be verified") from exc

    @contextmanager
    def _rebuild_lock(self) -> Iterator[None]:
        self._assert_separate_paths()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = Path(f"{self.path}.lock")
        if lock_path.is_symlink() or (lock_path.exists() and not lock_path.is_file()):
            raise ProjectionCorrupt("projection rebuild lock is not a regular file")
        flags = os.O_RDWR | os.O_CREAT
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            descriptor = os.open(lock_path, flags, 0o600)
        except OSError as exc:
            raise ProjectorError("projection rebuild lock could not be opened") from exc
        try:
            os.fchmod(descriptor, 0o600)
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            yield
        except OSError as exc:
            raise ProjectorError("projection rebuild lock failed") from exc
        finally:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
            finally:
                os.close(descriptor)

    def _journal_rows(
        self,
        to_sequence: int | None,
    ) -> tuple[list[tuple[Mapping[str, Any], Mapping[str, Any]]], int, str | None, str]:
        connection = self.store._connect(readonly=True)
        try:
            with self.store._read_snapshot(connection):
                integrity = self.store._verify_integrity_connection(connection)
                target = integrity.last_sequence if to_sequence is None else to_sequence
                if target > integrity.last_sequence:
                    raise ProjectorError("projection target exceeds the journal high-water sequence")
                rows = connection.execute(
                    "SELECT * FROM journal_entries WHERE sequence <= ? ORDER BY sequence",
                    (target,),
                ).fetchall()
                detached: list[tuple[Mapping[str, Any], Mapping[str, Any]]] = []
                for row in rows:
                    detached.append((self.store._record_from_row(row).event, dict(row)))
                source_hash = str(rows[-1]["entry_hash"]) if rows else None
                updated_at = str(rows[-1]["received_at"]) if rows else EMPTY_PROJECTION_TIME
                return detached, target, source_hash, updated_at
        finally:
            connection.close()

    @staticmethod
    def _reduce(
        rows: list[tuple[Mapping[str, Any], Mapping[str, Any]]],
        target: int,
        source_hash: str | None,
    ) -> ProjectionSnapshot:
        projections: dict[str, RunProjection] = {}
        quarantines: dict[str, ProjectionQuarantine] = {}
        for event, row in rows:
            subject = event["subject"]
            if subject["kind"] != "research_run":
                continue
            subject_id = str(subject["id"])
            if subject_id in quarantines:
                continue
            payload = event["payload"]
            prior = projections.get(subject_id)
            reason_code: str | None = None
            if payload.get("kind") != "ResearchRunTransition":
                reason_code = "UNSUPPORTED_EVENT_PAYLOAD"
            elif prior is None:
                if (
                    subject["version"] != 1
                    or payload["history_index"] != 0
                    or payload["from_state"] is not None
                    or payload["to_state"] != "initialized"
                ):
                    reason_code = "RUN_PROJECTION_INITIAL_STATE_INVALID"
            elif prior.current_state == "closed":
                reason_code = "RUN_PROJECTION_CLOSED_TERMINAL"
            elif (
                subject["version"] != prior.subject_version + 1
                or payload["history_index"] != prior.subject_version
                or payload["from_state"] != prior.current_state
            ):
                reason_code = "RUN_PROJECTION_STATE_DIVERGED"
            if reason_code is not None:
                quarantines[subject_id] = ProjectionQuarantine(
                    subject_kind="research_run",
                    subject_id=subject_id,
                    first_sequence=int(row["sequence"]),
                    event_id=str(event["id"]),
                    reason_code=reason_code,
                )
                continue
            closure = payload["closure"]
            projections[subject_id] = RunProjection(
                subject_id=subject_id,
                subject_version=int(subject["version"]),
                current_state=str(payload["to_state"]),
                close_status=str(closure["status"]) if isinstance(closure, Mapping) else None,
                last_occurred_at=str(event["occurred_at"]),
                classification=str(event["classification"]),
                last_sequence=int(row["sequence"]),
                last_event_id=str(event["id"]),
            )
        ordered_projections = tuple(sorted(projections.values(), key=lambda item: item.subject_id))
        ordered_quarantines = tuple(
            sorted(quarantines.values(), key=lambda item: (item.subject_kind, item.subject_id))
        )
        return ProjectionSnapshot(
            projector_name=PROJECTOR_NAME,
            projector_version=PROJECTOR_VERSION,
            last_sequence=target,
            source_hash=source_hash,
            state_digest=projection_state_digest(ordered_projections, ordered_quarantines),
            projections=ordered_projections,
            quarantines=ordered_quarantines,
        )

    def _expected_snapshot(
        self,
        to_sequence: int | None,
    ) -> tuple[ProjectionSnapshot, str]:
        rows, target, source_hash, updated_at = self._journal_rows(to_sequence)
        return self._reduce(rows, target, source_hash), updated_at

    def rebuild(self, *, to_sequence: int | None = None) -> ProjectionSnapshot:
        if to_sequence is not None and (
            isinstance(to_sequence, bool) or not isinstance(to_sequence, int) or to_sequence < 0
        ):
            raise ProjectorError("projection target sequence must be a non-negative integer")
        if to_sequence is not None and to_sequence > (1 << 53) - 1:
            raise ProjectorError("projection target exceeds the canonical safe-integer range")
        destination = self.path
        with self._rebuild_lock():
            snapshot, updated_at = self._expected_snapshot(to_sequence)
            if self.path != destination:
                raise ProjectionCorrupt("projection destination changed during rebuild")
            self._publish_snapshot(snapshot, updated_at)
            return snapshot

    def _publish_snapshot(self, snapshot: ProjectionSnapshot, updated_at: str) -> None:
        self._assert_separate_paths()
        destination = self.path
        if self.path.is_symlink() or (self.path.exists() and not self.path.is_file()):
            raise ProjectionCorrupt("projection path is not a regular file")
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.", suffix=".tmp", dir=self.path.parent
        )
        os.close(descriptor)
        temporary = Path(temporary_name)
        os.chmod(temporary, 0o600)
        connection: sqlite3.Connection | None = None
        try:
            connection = sqlite3.connect(temporary, isolation_level=None)
            connection.row_factory = sqlite3.Row
            if str(connection.execute("PRAGMA journal_mode = DELETE").fetchone()[0]).lower() != "delete":
                raise ProjectionCorrupt("projection database did not enter rollback-journal mode")
            connection.execute("PRAGMA synchronous = FULL")
            connection.execute(f"PRAGMA application_id = {self.application_id}")
            connection.execute(f"PRAGMA user_version = {self.user_version}")
            connection.execute("BEGIN IMMEDIATE")
            for statement in self._schema_statements:
                connection.execute(statement)
            connection.execute(
                """
                INSERT INTO projector_control(
                    singleton, projector_name, projector_version, last_sequence,
                    source_hash, state_digest, updated_at
                ) VALUES (1, ?, ?, ?, ?, ?, ?)
                """,
                (
                    PROJECTOR_NAME,
                    PROJECTOR_VERSION,
                    snapshot.last_sequence,
                    snapshot.source_hash,
                    snapshot.state_digest,
                    updated_at,
                ),
            )
            for item in snapshot.projections:
                connection.execute(
                    """
                    INSERT INTO research_run_projections(
                        subject_id, subject_version, current_state, close_status,
                        last_occurred_at, classification, last_sequence, last_event_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item.subject_id,
                        item.subject_version,
                        item.current_state,
                        item.close_status,
                        item.last_occurred_at,
                        item.classification,
                        item.last_sequence,
                        item.last_event_id,
                    ),
                )
            quarantine_times = self._quarantine_times(snapshot)
            for item in snapshot.quarantines:
                connection.execute(
                    """
                    INSERT INTO projection_quarantines(
                        subject_kind, subject_id, first_sequence, event_id,
                        reason_code, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item.subject_kind,
                        item.subject_id,
                        item.first_sequence,
                        item.event_id,
                        item.reason_code,
                        quarantine_times[item.first_sequence],
                    ),
                )
            self._before_commit(connection, snapshot)
            connection.execute("COMMIT")
            connection.close()
            connection = None
            self._validate_projection_file(temporary)
            with temporary.open("rb") as handle:
                os.fsync(handle.fileno())
            if temporary.stat().st_mode & 0o777 != 0o600:
                raise ProjectionCorrupt("projection database permissions are not private")
            if self.path != destination:
                raise ProjectionCorrupt("projection destination changed during publication")
            self._assert_separate_paths()
            os.replace(temporary, destination)
            _fsync_directory(destination.parent)
        except Exception as exc:
            if connection is not None:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                connection.close()
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
            if isinstance(exc, (EventStoreError, JournalCorrupt)):
                raise
            if isinstance(exc, sqlite3.Error):
                raise ProjectionCorrupt("projection rebuild database write failed") from exc
            raise

    def _quarantine_times(self, snapshot: ProjectionSnapshot) -> dict[int, str]:
        if not snapshot.quarantines:
            return {}
        wanted = {item.first_sequence for item in snapshot.quarantines}
        connection = self.store._connect(readonly=True)
        try:
            with self.store._read_snapshot(connection):
                self.store._verify_integrity_connection(connection)
                placeholders = ",".join("?" for _ in wanted)
                rows = connection.execute(
                    f"SELECT sequence, received_at FROM journal_entries WHERE sequence IN ({placeholders})",
                    tuple(sorted(wanted)),
                ).fetchall()
                values = {int(row["sequence"]): str(row["received_at"]) for row in rows}
                if set(values) != wanted:
                    raise JournalCorrupt("quarantine source entries are missing from the journal")
                return values
        finally:
            connection.close()

    def _before_commit(
        self,
        connection: sqlite3.Connection,
        snapshot: ProjectionSnapshot,
    ) -> None:
        """Test seam for proving that a failed rebuild preserves the prior generation."""

    def _connect_projection(self, path: Path) -> sqlite3.Connection:
        try:
            uri = f"file:{quote(str(path))}?mode=ro"
            connection = sqlite3.connect(uri, uri=True, isolation_level=None)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA query_only = ON")
            connection.execute("BEGIN")
            return connection
        except sqlite3.Error as exc:
            raise ProjectionCorrupt("projection database could not be opened; rebuild") from exc

    def _validate_projection_file(
        self,
        path: Path,
    ) -> tuple[ProjectionSnapshot, str, tuple[Mapping[str, Any], ...]]:
        connection = self._connect_projection(path)
        try:
            if (
                int(connection.execute("PRAGMA application_id").fetchone()[0]) != self.application_id
                or int(connection.execute("PRAGMA user_version").fetchone()[0]) != self.user_version
                or _schema_fingerprint(connection) != self._expected_schema_fingerprint
            ):
                raise ProjectionCorrupt("projection identity or schema differs from its contract; rebuild")
            if [row[0] for row in connection.execute("PRAGMA integrity_check").fetchall()] != ["ok"]:
                raise ProjectionCorrupt("projection SQLite integrity check failed; rebuild")
            control_rows = connection.execute("SELECT * FROM projector_control").fetchall()
            if len(control_rows) != 1 or control_rows[0]["singleton"] != 1:
                raise ProjectionCorrupt("projection control cardinality is invalid; rebuild")
            control = control_rows[0]
            if (
                control["projector_name"] != PROJECTOR_NAME
                or control["projector_version"] != PROJECTOR_VERSION
                or isinstance(control["last_sequence"], bool)
                or not isinstance(control["last_sequence"], int)
                or control["last_sequence"] < 0
                or control["last_sequence"] > (1 << 53) - 1
            ):
                raise ProjectionCorrupt("projection checkpoint metadata is invalid; rebuild")
            last_sequence = int(control["last_sequence"])
            source_hash = control["source_hash"]
            if (last_sequence == 0) != (source_hash is None):
                raise ProjectionCorrupt("projection checkpoint source hash is invalid; rebuild")
            try:
                updated_at = _validated_time(str(control["updated_at"]))
            except EventStoreError as exc:
                raise ProjectionCorrupt("projection checkpoint timestamp is invalid; rebuild") from exc
            projections = tuple(
                RunProjection(
                    subject_id=str(row["subject_id"]),
                    subject_version=int(row["subject_version"]),
                    current_state=str(row["current_state"]),
                    close_status=str(row["close_status"]) if row["close_status"] is not None else None,
                    last_occurred_at=str(row["last_occurred_at"]),
                    classification=str(row["classification"]),
                    last_sequence=int(row["last_sequence"]),
                    last_event_id=str(row["last_event_id"]),
                )
                for row in connection.execute(
                    "SELECT * FROM research_run_projections ORDER BY subject_id"
                ).fetchall()
            )
            quarantine_rows = tuple(
                dict(row)
                for row in connection.execute(
                    "SELECT * FROM projection_quarantines ORDER BY subject_kind, subject_id"
                ).fetchall()
            )
            quarantines = tuple(
                ProjectionQuarantine(
                    subject_kind=str(row["subject_kind"]),
                    subject_id=str(row["subject_id"]),
                    first_sequence=int(row["first_sequence"]),
                    event_id=str(row["event_id"]),
                    reason_code=str(row["reason_code"]),
                )
                for row in quarantine_rows
            )
            if any(
                item.last_sequence > last_sequence
                or item.current_state not in RUN_STATES
                or (item.current_state == "closed") != (item.close_status is not None)
                for item in projections
            ) or any(item.first_sequence > last_sequence for item in quarantines):
                raise ProjectionCorrupt("materialized rows exceed or contradict their checkpoint; rebuild")
            state_digest = projection_state_digest(projections, quarantines)
            if state_digest != control["state_digest"]:
                raise ProjectionCorrupt("projection digest disagrees with materialized state; rebuild")
            snapshot = ProjectionSnapshot(
                projector_name=PROJECTOR_NAME,
                projector_version=PROJECTOR_VERSION,
                last_sequence=last_sequence,
                source_hash=source_hash,
                state_digest=state_digest,
                projections=projections,
                quarantines=quarantines,
            )
            connection.execute("COMMIT")
            return snapshot, updated_at, quarantine_rows
        except Exception as exc:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            if isinstance(exc, ProjectionCorrupt):
                raise
            if isinstance(exc, sqlite3.Error):
                raise ProjectionCorrupt("projection database could not be read; rebuild") from exc
            raise
        finally:
            connection.close()

    def snapshot(self) -> ProjectionSnapshot | None:
        self._assert_separate_paths()
        if self.path.is_symlink() or (self.path.exists() and not self.path.is_file()):
            raise ProjectionCorrupt("projection path is not a regular file; rebuild")
        if not self.path.exists():
            return None
        if self.path.stat().st_mode & 0o077:
            raise ProjectionCorrupt("projection database permissions are not private; rebuild")
        actual, actual_updated_at, quarantine_rows = self._validate_projection_file(self.path)
        expected, expected_updated_at = self._expected_snapshot(actual.last_sequence)
        if actual != expected or actual_updated_at != expected_updated_at:
            raise ProjectionCorrupt("projection rows disagree with their journal source; rebuild")
        expected_quarantine_times = self._quarantine_times(expected)
        if any(
            row["created_at"] != expected_quarantine_times[int(row["first_sequence"])]
            for row in quarantine_rows
        ):
            raise ProjectionCorrupt("projection quarantine provenance is invalid; rebuild")
        return actual


__all__ = [
    "DEFAULT_PROJECTION_MANIFEST",
    "PROJECTOR_NAME",
    "PROJECTOR_VERSION",
    "ProjectionCorrupt",
    "ProjectionQuarantine",
    "ProjectionSnapshot",
    "ProjectorError",
    "ResearchRunProjector",
    "RunProjection",
    "projection_state_digest",
]
