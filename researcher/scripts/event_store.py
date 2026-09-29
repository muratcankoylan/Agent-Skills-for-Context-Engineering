#!/usr/bin/env python3
"""Local, canonical, append-only event journal for SPEC-004.

The portable identity is the registered ``OrganizationEvent``. SQLite owns
only acceptance order, receipt metadata, the hash chain, and rebuildable
projections. Runtime databases and receipts are private operational state.
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import tempfile
import time
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, Mapping
from urllib.parse import quote

try:
    from schema_contract import (  # type: ignore[import-not-found]
        ContractError,
        SchemaRegistry,
        canonical_digest,
        canonicalize,
        parse_json_strict,
        sha256_bytes,
    )
except ModuleNotFoundError:
    from researcher.scripts.schema_contract import (
        ContractError,
        SchemaRegistry,
        canonical_digest,
        canonicalize,
        parse_json_strict,
        sha256_bytes,
    )


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUNTIME_ROOT = ROOT / "researcher" / "runtime" / "event-journal"
DEFAULT_DATABASE_PATH = DEFAULT_RUNTIME_ROOT / "journal.sqlite3"
DEFAULT_MIGRATION_MANIFEST = (
    ROOT / "researcher" / "event_journal" / "migrations" / "manifest.json"
)
CHAIN_PROFILE = "organization-journal-chain-v1"
MAX_EVENT_BYTES = 65_536
MAX_SCAN_LIMIT = 1_000
MINIMUM_SQLITE_VERSION = (3, 37, 0)
BACKUP_DATABASE_NAME = "journal.sqlite3"
BACKUP_RECEIPT_NAME = "receipt.json"
OPERATOR_HALT_SUFFIX = ".operator-halt"


class EventStoreError(RuntimeError):
    """Stable, non-sensitive event-store failure."""

    code = "EVENT_STORE_ERROR"

    def __init__(self, safe_message: str, **details: Any):
        super().__init__(f"[{self.code}] {safe_message}")
        self.safe_message = safe_message
        self.details = details


class SubjectVersionConflict(EventStoreError):
    code = "SUBJECT_VERSION_CONFLICT"


class EventIdentityConflict(EventStoreError):
    code = "EVENT_ID_CONFLICT"


class IdempotencyConflict(EventStoreError):
    code = "IDEMPOTENCY_CONFLICT"


class EventCausationConflict(EventStoreError):
    code = "EVENT_CAUSATION_CONFLICT"


class JournalCorrupt(EventStoreError):
    code = "JOURNAL_CORRUPT"


class JournalBusy(EventStoreError):
    code = "JOURNAL_BUSY"


class MigrationDrift(EventStoreError):
    code = "MIGRATION_DRIFT"


class MigrationAhead(EventStoreError):
    code = "MIGRATION_AHEAD"


class MigrationFailed(EventStoreError):
    code = "MIGRATION_FAILED"


class InvalidCursor(EventStoreError):
    code = "INVALID_CURSOR"


class BackupFailed(EventStoreError):
    code = "BACKUP_FAILED"


class BackupDestinationExists(EventStoreError):
    code = "BACKUP_DESTINATION_EXISTS"


class RestoreInvalid(EventStoreError):
    code = "RESTORE_INVALID"


@dataclass(frozen=True)
class AppendReceipt:
    sequence: int
    event_id: str
    event_digest: str
    subject_kind: str
    subject_id: str
    subject_version: int
    received_at: str
    previous_entry_hash: str | None
    entry_hash: str
    duplicate: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class JournalEntryRecord:
    sequence: int
    received_at: str
    event: dict[str, Any]
    event_digest: str
    previous_entry_hash: str | None
    entry_hash: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EventPage:
    entries: tuple[JournalEntryRecord, ...]
    after_sequence: int
    next_after_sequence: int
    high_water_sequence: int
    has_more: bool


@dataclass(frozen=True)
class IntegrityReport:
    entry_count: int
    subject_count: int
    last_sequence: int
    last_entry_hash: str | None
    schema_version: int
    result: str = "pass"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class JournalStats:
    entry_count: int
    subject_count: int
    last_sequence: int
    last_entry_hash: str | None
    database_size_bytes: int
    page_count: int
    page_size: int


@dataclass(frozen=True)
class BackupReceipt:
    schema_version: str
    backup_name: str
    backup_digest: str
    size_bytes: int
    source_last_sequence: int
    source_last_entry_hash: str | None
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MigrationSource:
    version: int
    name: str
    digest: str
    statements: tuple[str, ...]


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def entry_hash(
    *,
    sequence: int,
    received_at: str,
    event_digest: str,
    previous_entry_hash: str | None,
) -> str:
    return canonical_digest(
        {
            "chain_profile": CHAIN_PROFILE,
            "sequence": sequence,
            "received_at": received_at,
            "event_digest": event_digest,
            "previous_entry_hash": previous_entry_hash,
        }
    )


def _strict_integer(value: object, *, minimum: int, code: str, label: str) -> int:
    error_type: type[EventStoreError] = InvalidCursor if code == "INVALID_CURSOR" else EventStoreError
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise error_type(
            f"{label} must be an integer >= {minimum}", value_type=type(value).__name__
        )
    if value > (1 << 53) - 1:
        raise error_type(f"{label} exceeds the canonical safe-integer range")
    return value


def _validated_time(value: str) -> str:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise EventStoreError("journal clock must return a UTC RFC 3339 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EventStoreError("journal clock returned an invalid timestamp") from exc
    if parsed.tzinfo is None:
        raise EventStoreError("journal clock returned a timezone-free timestamp")
    return value


def _valid_digest(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 71
        and value.startswith("sha256:")
        and all(character in "0123456789abcdef" for character in value[7:])
    )


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _publish_no_clobber(temporary: Path, destination: Path) -> None:
    try:
        os.link(temporary, destination)
    except FileExistsError as exc:
        raise BackupDestinationExists("destination already exists", destination=destination.name) from exc
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
    _fsync_directory(destination.parent)


def _atomic_no_clobber_bytes(destination: Path, body: bytes) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(body)
            handle.flush()
            os.fsync(handle.fileno())
        _publish_no_clobber(temporary, destination)
    except Exception:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        raise


def _migration_statements(body: str) -> list[str]:
    statements: list[str] = []
    buffer: list[str] = []
    for line in body.splitlines(keepends=True):
        buffer.append(line)
        candidate = "".join(buffer)
        if sqlite3.complete_statement(candidate):
            if candidate.strip():
                statements.append(candidate)
            buffer = []
    if "".join(buffer).strip():
        raise MigrationFailed("migration contains an incomplete SQL statement")
    return statements


def _ensure_private_root(path: Path, error_type: type[EventStoreError]) -> None:
    if path.is_symlink() or (path.exists() and not path.is_dir()):
        raise error_type("generation root is not a private directory")
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    mode = path.stat().st_mode & 0o777
    if mode & 0o077:
        raise error_type("generation root grants group or other access")


def _new_generation_staging(root: Path, prefix: str) -> tuple[str, Path, Path]:
    generation_name = f"{prefix}-{uuid.uuid4()}"
    destination = root / generation_name
    if destination.exists() or destination.is_symlink():
        raise BackupDestinationExists("generation identity collided; retry")
    staging = Path(tempfile.mkdtemp(prefix=".staging-", dir=root))
    os.chmod(staging, 0o700)
    return generation_name, staging, destination


def _publish_generation(staging: Path, destination: Path) -> None:
    if destination.exists() or destination.is_symlink():
        raise BackupDestinationExists("generation destination already exists")
    os.rename(staging, destination)
    _fsync_directory(destination.parent)


def _checkpoint_closed_database(
    database: Path,
    error_type: type[EventStoreError],
) -> None:
    """Checkpoint a private staged database and remove clean WAL control files."""

    connection: sqlite3.Connection | None = None
    try:
        connection = sqlite3.connect(database, isolation_level=None)
        result = connection.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
        if result is None or int(result[0]) != 0:
            raise error_type("staged database WAL could not be checkpointed")
    except sqlite3.Error as exc:
        raise error_type("staged database WAL checkpoint failed") from exc
    finally:
        if connection is not None:
            connection.close()
    for suffix in ("-wal", "-shm", "-journal"):
        sidecar = Path(f"{database}{suffix}")
        if sidecar.is_symlink() or (sidecar.exists() and not sidecar.is_file()):
            raise error_type("staged database has an invalid SQLite sidecar")
        try:
            sidecar.unlink()
        except FileNotFoundError:
            pass
    _fsync_directory(database.parent)


class EventStore:
    """SQLite implementation of SPEC-004's local EventStore interface."""

    def __init__(
        self,
        path: Path = DEFAULT_DATABASE_PATH,
        *,
        registry: SchemaRegistry | None = None,
        migration_manifest: Path = DEFAULT_MIGRATION_MANIFEST,
        busy_timeout_ms: int = 5_000,
        clock: Callable[[], str] = utc_now,
        initialize: bool = True,
    ) -> None:
        if sqlite3.sqlite_version_info < MINIMUM_SQLITE_VERSION:
            raise EventStoreError("SQLite 3.37 or newer is required for STRICT tables")
        if isinstance(busy_timeout_ms, bool) or not isinstance(busy_timeout_ms, int) or busy_timeout_ms < 1:
            raise EventStoreError("busy timeout must be a positive integer")
        self.path = Path(path).absolute()
        self.registry = registry or SchemaRegistry.load()
        self.migration_manifest_path = Path(migration_manifest).absolute()
        self.busy_timeout_ms = busy_timeout_ms
        self.clock = clock
        self._migration_sources: dict[int, MigrationSource] = {}
        self._manifest = self._load_migration_manifest()
        self._expected_schema_fingerprint = self._build_expected_schema_fingerprint()
        if initialize:
            self._initialize()
        else:
            if not self.path.is_file() or self.path.is_symlink():
                raise JournalCorrupt("journal database is missing or not a regular file")
            self.verify_integrity()

    @property
    def operator_halt_path(self) -> Path:
        return Path(f"{self.path}{OPERATOR_HALT_SUFFIX}")

    def _assert_not_halted(self) -> None:
        marker = self.operator_halt_path
        if marker.is_symlink() or marker.exists():
            raise JournalCorrupt(
                "journal is under an operator integrity halt",
                halt_marker=marker.name,
            )

    def _latch_operator_halt(self) -> None:
        """Persist a database-independent halt after detected journal corruption."""

        marker = self.operator_halt_path
        if marker.is_symlink() or marker.exists():
            return
        try:
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{marker.name}.", suffix=".tmp", dir=marker.parent
            )
            temporary = Path(temporary_name)
            try:
                os.fchmod(descriptor, 0o600)
                with os.fdopen(descriptor, "wb") as handle:
                    handle.write(
                        canonicalize(
                            {
                                "schema_version": "1.0.0",
                                "code": "JOURNAL_CORRUPT",
                                "action": "operator_recovery_required",
                            }
                        )
                        + b"\n"
                    )
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary, marker)
                _fsync_directory(marker.parent)
            except Exception:
                try:
                    temporary.unlink()
                except FileNotFoundError:
                    pass
                raise
        except OSError:
            # The originating integrity error remains authoritative even when a
            # damaged or read-only filesystem prevents persistence of the latch.
            return

    def clear_operator_halt(self) -> IntegrityReport:
        """Clear a latched halt only after an explicit successful full audit."""

        marker = self.operator_halt_path
        if marker.is_symlink() or (marker.exists() and not marker.is_file()):
            raise JournalCorrupt("operator halt marker is not a regular file")
        report = self.verify_integrity()
        try:
            marker.unlink()
        except FileNotFoundError:
            return report
        _fsync_directory(marker.parent)
        return report

    @property
    def latest_schema_version(self) -> int:
        return int(self._manifest["latest_version"])

    @property
    def application_id(self) -> int:
        return int(self._manifest["application_id"])

    def _load_migration_manifest(self) -> dict[str, Any]:
        try:
            value = parse_json_strict(self.migration_manifest_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ContractError) as exc:
            raise MigrationFailed("migration manifest is unreadable") from exc
        if not isinstance(value, dict) or set(value) != {
            "schema_version",
            "application_id",
            "latest_version",
            "migrations",
        }:
            raise MigrationFailed("migration manifest fields differ from the contract")
        if value["schema_version"] != "1.0.0":
            raise MigrationFailed("migration manifest version is unsupported")
        application_id = value["application_id"]
        latest = value["latest_version"]
        migrations = value["migrations"]
        if (
            isinstance(application_id, bool)
            or not isinstance(application_id, int)
            or not 1 <= application_id <= 0x7FFFFFFF
            or isinstance(latest, bool)
            or not isinstance(latest, int)
            or latest < 1
            or not isinstance(migrations, list)
        ):
            raise MigrationFailed("migration manifest metadata is invalid")
        versions: list[int] = []
        migration_root = (ROOT / "researcher" / "event_journal" / "migrations").resolve()
        for migration in migrations:
            if not isinstance(migration, dict) or set(migration) != {"version", "name", "path", "digest"}:
                raise MigrationFailed("migration entry fields differ from the contract")
            version = migration["version"]
            if isinstance(version, bool) or not isinstance(version, int) or version < 1:
                raise MigrationFailed("migration version is invalid")
            path = (ROOT / str(migration["path"])).resolve()
            try:
                path.relative_to(migration_root)
            except ValueError as exc:
                raise MigrationFailed("migration path escapes the public migration root") from exc
            if not path.is_file() or path.is_symlink():
                raise MigrationFailed("migration is missing or not a regular file")
            try:
                body = path.read_bytes()
                statements = tuple(_migration_statements(body.decode("utf-8")))
            except (OSError, UnicodeError) as exc:
                raise MigrationFailed("migration bytes are unreadable", version=version) from exc
            if sha256_bytes(body) != migration["digest"]:
                raise MigrationDrift("migration bytes disagree with their pinned digest", version=version)
            self._migration_sources[version] = MigrationSource(
                version=version,
                name=str(migration["name"]),
                digest=str(migration["digest"]),
                statements=statements,
            )
            versions.append(version)
        if versions != list(range(1, latest + 1)):
            raise MigrationFailed("migration versions must be contiguous and complete")
        return value

    @staticmethod
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

    def _build_expected_schema_fingerprint(self) -> str:
        connection = sqlite3.connect(":memory:", isolation_level=None)
        connection.row_factory = sqlite3.Row
        try:
            for version in range(1, self.latest_schema_version + 1):
                source = self._migration_sources[version]
                for statement in source.statements:
                    connection.execute(statement)
            return self._schema_fingerprint(connection)
        except sqlite3.Error as exc:
            raise MigrationFailed("pinned migrations cannot construct the expected schema") from exc
        finally:
            connection.close()

    def _connect(
        self,
        *,
        readonly: bool = False,
        allow_halted: bool = False,
    ) -> sqlite3.Connection:
        connection: sqlite3.Connection | None = None
        if not allow_halted:
            self._assert_not_halted()
        try:
            if readonly:
                uri = f"file:{quote(str(self.path))}?mode=ro"
                connection = sqlite3.connect(
                    uri,
                    uri=True,
                    timeout=self.busy_timeout_ms / 1000,
                    isolation_level=None,
                )
            else:
                connection = sqlite3.connect(
                    self.path,
                    timeout=self.busy_timeout_ms / 1000,
                    isolation_level=None,
                )
            connection.row_factory = sqlite3.Row
            connection.execute(f"PRAGMA busy_timeout = {self.busy_timeout_ms}")
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA trusted_schema = OFF")
            connection.execute("PRAGMA synchronous = FULL")
            if readonly:
                connection.execute("PRAGMA query_only = ON")
            return connection
        except sqlite3.Error as exc:
            if connection is not None:
                connection.close()
            mapped = self._map_sqlite_error(exc)
            if isinstance(mapped, JournalBusy):
                raise mapped from exc
            raise JournalCorrupt("journal connection could not be configured") from exc

    def _initialize(self) -> None:
        _ensure_private_root(self.path.parent, JournalCorrupt)
        if self.path.is_symlink() or (self.path.exists() and not self.path.is_file()):
            raise JournalCorrupt("journal path is not a regular file")
        created = False
        if not self.path.exists():
            flags = os.O_RDWR | os.O_CREAT | os.O_EXCL
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            try:
                descriptor = os.open(self.path, flags, 0o600)
            except FileExistsError:
                pass
            except OSError as exc:
                raise JournalCorrupt("journal file could not be created privately") from exc
            else:
                os.close(descriptor)
                created = True
        if self.path.stat().st_mode & 0o077:
            raise JournalCorrupt("journal database permissions are not private")
        connection: sqlite3.Connection | None = None
        try:
            connection = self._connect()
            mode = str(connection.execute("PRAGMA journal_mode = WAL").fetchone()[0]).lower()
            if mode != "wal":
                raise JournalCorrupt("journal database did not enter WAL mode", mode=mode)
            existing_application_id = int(connection.execute("PRAGMA application_id").fetchone()[0])
            existing_objects = int(
                connection.execute(
                    "SELECT count(*) FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"
                ).fetchone()[0]
            )
            if existing_application_id == 0 and existing_objects == 0:
                connection.execute(f"PRAGMA application_id = {self.application_id}")
            elif existing_application_id != self.application_id:
                raise JournalCorrupt("SQLite application ID does not identify this journal")
            self._apply_migrations(connection)
        except sqlite3.Error as exc:
            mapped = self._map_sqlite_error(exc)
            if isinstance(mapped, JournalBusy):
                raise mapped from exc
            raise JournalCorrupt("journal initialization failed") from exc
        finally:
            if connection is not None:
                connection.close()
        if created:
            os.chmod(self.path, 0o600)
        self.verify_integrity()

    def _apply_migrations(self, connection: sqlite3.Connection) -> None:
        current = int(connection.execute("PRAGMA user_version").fetchone()[0])
        if current > self.latest_schema_version:
            raise MigrationAhead(
                "journal schema is newer than this runtime",
                current=current,
                supported=self.latest_schema_version,
            )
        for migration in self._manifest["migrations"]:
            version = int(migration["version"])
            source = self._migration_sources[version]
            try:
                connection.execute("BEGIN IMMEDIATE")
                locked_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
                if locked_version >= version:
                    row = connection.execute(
                        "SELECT name, digest FROM schema_migrations WHERE version = ?",
                        (version,),
                    ).fetchone()
                    if row is None or row["name"] != migration["name"] or row["digest"] != migration["digest"]:
                        raise MigrationDrift("applied migration metadata disagrees with the manifest")
                    connection.execute("COMMIT")
                    continue
                if locked_version != version - 1:
                    raise MigrationFailed("journal schema version is not contiguous")
                for statement in source.statements:
                    connection.execute(statement)
                connection.execute(
                    "INSERT INTO schema_migrations(version, name, digest, applied_at) VALUES (?, ?, ?, ?)",
                    (version, migration["name"], migration["digest"], _validated_time(self.clock())),
                )
                connection.execute(f"PRAGMA user_version = {version}")
                connection.execute("COMMIT")
            except EventStoreError:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise
            except sqlite3.Error as exc:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                mapped = self._map_sqlite_error(exc)
                if isinstance(mapped, JournalBusy):
                    raise mapped from exc
                raise MigrationFailed("migration transaction failed", version=version) from exc

    def append(
        self,
        event: Mapping[str, Any],
        expected_subject_version: int,
    ) -> AppendReceipt:
        expected = _strict_integer(
            expected_subject_version,
            minimum=0,
            code="INVALID_EXPECTED_VERSION",
            label="expected subject version",
        )
        body = canonicalize(event)
        if len(body) > MAX_EVENT_BYTES:
            raise EventStoreError("canonical event exceeds the 64 KiB journal limit")
        parsed_event = parse_json_strict(body.decode("utf-8"))
        if not isinstance(parsed_event, dict):
            raise EventStoreError("event store accepts only JSON object records")
        canonical_event = parsed_event
        self._after_event_snapshot()
        entry = self.registry.resolve_for_write(
            str(canonical_event.get("kind")), str(canonical_event.get("schema_version"))
        )
        if entry.kind != "OrganizationEvent":
            raise EventStoreError("event store accepts only OrganizationEvent records")
        self.registry.validate(canonical_event, kind="OrganizationEvent", version="1.0.0")
        digest = sha256_bytes(body)
        subject = canonical_event["subject"]
        if subject["version"] != expected + 1:
            raise SubjectVersionConflict(
                "event subject version must equal expected version plus one",
                expected=expected,
                event_version=subject["version"],
            )
        idempotency = canonical_event["idempotency"]
        connection = self._connect()
        receipt: AppendReceipt | None = None
        try:
            connection.execute("BEGIN IMMEDIATE")
            self._verify_append_preconditions(connection)
            event_row = connection.execute(
                "SELECT * FROM journal_entries WHERE event_id = ?", (canonical_event["id"],)
            ).fetchone()
            key_row = connection.execute(
                "SELECT * FROM journal_entries WHERE idempotency_scope = ? AND idempotency_key_digest = ?",
                (idempotency["scope"], idempotency["key_digest"]),
            ).fetchone()
            if event_row is not None and key_row is not None and event_row["sequence"] != key_row["sequence"]:
                raise JournalCorrupt("event identity and idempotency key resolve to different entries")
            if event_row is not None:
                if (
                    key_row is None
                    or event_row["event_digest"] != digest
                    or bytes(event_row["event_json"]) != body
                    or event_row["idempotency_scope"] != idempotency["scope"]
                    or event_row["idempotency_key_digest"] != idempotency["key_digest"]
                ):
                    raise EventIdentityConflict("event ID was reused with different immutable bytes")
                duplicate_metadata = {
                    "subject_kind": subject["kind"],
                    "subject_id": subject["id"],
                    "subject_version": subject["version"],
                    "event_type": canonical_event["event_type"],
                    "classification": canonical_event["classification"],
                    "occurred_at": canonical_event["occurred_at"],
                }
                if any(event_row[key] != value for key, value in duplicate_metadata.items()):
                    raise JournalCorrupt("duplicate entry metadata disagrees with canonical bytes")
                try:
                    _validated_time(str(event_row["received_at"]))
                except EventStoreError as exc:
                    raise JournalCorrupt("duplicate entry receipt timestamp is invalid") from exc
                duplicate_hash = entry_hash(
                    sequence=int(event_row["sequence"]),
                    received_at=str(event_row["received_at"]),
                    event_digest=digest,
                    previous_entry_hash=event_row["previous_entry_hash"],
                )
                if event_row["entry_hash"] != duplicate_hash:
                    raise JournalCorrupt("duplicate entry hash is invalid")
                connection.execute("COMMIT")
                return replace(self._receipt_from_row(event_row), duplicate=True)
            if key_row is not None:
                raise IdempotencyConflict("idempotency key was reused for a different event")

            version_row = connection.execute(
                "SELECT version, last_sequence FROM subject_versions WHERE subject_kind = ? AND subject_id = ?",
                (subject["kind"], subject["id"]),
            ).fetchone()
            current_version = int(version_row["version"]) if version_row is not None else 0
            if current_version != expected:
                raise SubjectVersionConflict(
                    "subject version changed before append",
                    expected=expected,
                    current=current_version,
                )
            if version_row is not None:
                prior_row = connection.execute(
                    "SELECT * FROM journal_entries WHERE sequence = ?",
                    (version_row["last_sequence"],),
                ).fetchone()
                if prior_row is None:
                    raise JournalCorrupt("subject-version tail does not resolve to an event")
                prior_raw = bytes(prior_row["event_json"])
                try:
                    prior_event = parse_json_strict(prior_raw.decode("utf-8"))
                except (UnicodeError, ContractError) as exc:
                    raise JournalCorrupt("subject-version tail is not strict JSON") from exc
                if not isinstance(prior_event, dict) or canonicalize(prior_event) != prior_raw:
                    raise JournalCorrupt("subject-version tail is not canonical")
                try:
                    self.registry.validate(
                        prior_event,
                        kind="OrganizationEvent",
                        version="1.0.0",
                    )
                except ContractError as exc:
                    raise JournalCorrupt("subject-version tail no longer satisfies its contract") from exc
                prior_subject = prior_event["subject"]
                if (
                    prior_row["event_digest"] != sha256_bytes(prior_raw)
                    or prior_row["subject_kind"] != subject["kind"]
                    or prior_row["subject_id"] != subject["id"]
                    or prior_row["subject_version"] != expected
                    or prior_subject["kind"] != subject["kind"]
                    or prior_subject["id"] != subject["id"]
                    or prior_subject["version"] != expected
                    or int(version_row["last_sequence"]) != int(prior_row["sequence"])
                ):
                    raise JournalCorrupt("subject-version index disagrees with its tail event")
                if (
                    canonical_event["causation_event_id"] != prior_row["event_id"]
                    or canonical_event["correlation_event_id"] != prior_event["correlation_event_id"]
                ):
                    raise EventCausationConflict(
                        "event does not continue its subject correlation and causation chain"
                    )
            control = connection.execute(
                "SELECT last_sequence, last_entry_hash FROM journal_control WHERE singleton = 1"
            ).fetchone()
            if control is None:
                raise JournalCorrupt("journal control row is missing")
            sequence = (int(control["last_sequence"]) if control["last_sequence"] is not None else 0) + 1
            previous_hash = control["last_entry_hash"]
            received_at = _validated_time(self.clock())
            digest_for_entry = entry_hash(
                sequence=sequence,
                received_at=received_at,
                event_digest=digest,
                previous_entry_hash=previous_hash,
            )
            connection.execute(
                """
                INSERT INTO journal_entries(
                    sequence, event_id, idempotency_scope, idempotency_key_digest,
                    subject_kind, subject_id, subject_version, event_type, classification,
                    occurred_at, event_json, event_digest, received_at,
                    previous_entry_hash, entry_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sequence,
                    canonical_event["id"],
                    idempotency["scope"],
                    idempotency["key_digest"],
                    subject["kind"],
                    subject["id"],
                    subject["version"],
                    canonical_event["event_type"],
                    canonical_event["classification"],
                    canonical_event["occurred_at"],
                    sqlite3.Binary(body),
                    digest,
                    received_at,
                    previous_hash,
                    digest_for_entry,
                ),
            )
            if version_row is None:
                connection.execute(
                    "INSERT INTO subject_versions(subject_kind, subject_id, version, last_sequence) VALUES (?, ?, ?, ?)",
                    (subject["kind"], subject["id"], subject["version"], sequence),
                )
            else:
                connection.execute(
                    """
                    UPDATE subject_versions SET version = ?, last_sequence = ?
                    WHERE subject_kind = ? AND subject_id = ? AND version = ?
                    """,
                    (subject["version"], sequence, subject["kind"], subject["id"], expected),
                )
                if connection.execute("SELECT changes()").fetchone()[0] != 1:
                    raise JournalCorrupt("subject version update lost its writer lock")
            connection.execute(
                """
                UPDATE journal_control
                SET last_sequence = ?, last_entry_hash = ?, integrity_state = 'healthy',
                    last_verified_sequence = ?, last_verified_hash = ?, last_verified_at = ?
                WHERE singleton = 1
                """,
                (sequence, digest_for_entry, sequence, digest_for_entry, received_at),
            )
            receipt = AppendReceipt(
                sequence=sequence,
                event_id=canonical_event["id"],
                event_digest=digest,
                subject_kind=subject["kind"],
                subject_id=subject["id"],
                subject_version=subject["version"],
                received_at=received_at,
                previous_entry_hash=previous_hash,
                entry_hash=digest_for_entry,
            )
            self._before_commit(connection, receipt)
            connection.execute("COMMIT")
        except Exception as exc:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            mapped = self._map_sqlite_error(exc)
            if isinstance(mapped, (JournalCorrupt, MigrationDrift)):
                self._latch_operator_halt()
            if mapped is not exc:
                raise mapped from exc
            raise
        finally:
            connection.close()
        assert receipt is not None
        self._after_commit(receipt)
        return receipt

    def _after_event_snapshot(self) -> None:
        """Test seam after caller-owned input has been detached into canonical bytes."""

    def _before_commit(self, connection: sqlite3.Connection, receipt: AppendReceipt) -> None:
        """Test seam for crash/fault injection before the transaction commits."""

    def _after_commit(self, receipt: AppendReceipt) -> None:
        """Test seam for delivery failure after the durable commit."""

    def _verify_append_preconditions(self, connection: sqlite3.Connection) -> None:
        """Verify bounded write-critical state; full scans remain explicit audits."""

        self._verify_database_contract(connection, full_storage_check=False)
        controls = connection.execute("SELECT * FROM journal_control").fetchall()
        if len(controls) != 1 or controls[0]["singleton"] != 1:
            raise JournalCorrupt("journal control row cardinality is invalid")
        control = controls[0]
        if control["integrity_state"] != "healthy":
            raise JournalCorrupt("journal is under an operator integrity halt")
        sequence_value = control["last_sequence"]
        tail_sequence = int(sequence_value) if sequence_value is not None else 0
        sqlite_sequence_row = connection.execute(
            "SELECT seq FROM sqlite_sequence WHERE name = 'journal_entries'"
        ).fetchone()
        sqlite_sequence = int(sqlite_sequence_row["seq"]) if sqlite_sequence_row is not None else 0
        if sqlite_sequence != tail_sequence:
            raise JournalCorrupt("SQLite sequence tail disagrees with journal control")
        if tail_sequence == 0:
            if (
                control["last_entry_hash"] is not None
                or control["last_verified_sequence"] is not None
                or control["last_verified_hash"] is not None
                or control["last_verified_at"] is not None
                or connection.execute("SELECT 1 FROM journal_entries LIMIT 1").fetchone()
                is not None
                or connection.execute("SELECT 1 FROM subject_versions LIMIT 1").fetchone()
                is not None
            ):
                raise JournalCorrupt("empty journal control metadata is inconsistent")
            return
        tail = connection.execute(
            "SELECT * FROM journal_entries WHERE sequence = ?",
            (tail_sequence,),
        ).fetchone()
        if tail is None:
            raise JournalCorrupt("journal control tail does not resolve to an entry")
        raw = bytes(tail["event_json"])
        try:
            event = parse_json_strict(raw.decode("utf-8"))
        except (UnicodeError, ContractError) as exc:
            raise JournalCorrupt("journal tail is not strict canonical JSON") from exc
        if not isinstance(event, dict) or canonicalize(event) != raw:
            raise JournalCorrupt("journal tail is not canonical")
        try:
            self.registry.validate(event, kind="OrganizationEvent", version="1.0.0")
        except ContractError as exc:
            raise JournalCorrupt("journal tail no longer satisfies its contract") from exc
        digest = sha256_bytes(raw)
        subject = event["subject"]
        idempotency = event["idempotency"]
        duplicated = {
            "event_id": event["id"],
            "idempotency_scope": idempotency["scope"],
            "idempotency_key_digest": idempotency["key_digest"],
            "subject_kind": subject["kind"],
            "subject_id": subject["id"],
            "subject_version": subject["version"],
            "event_type": event["event_type"],
            "classification": event["classification"],
            "occurred_at": event["occurred_at"],
        }
        if tail["event_digest"] != digest or any(
            tail[key] != value for key, value in duplicated.items()
        ):
            raise JournalCorrupt("journal tail metadata disagrees with canonical event bytes")
        try:
            _validated_time(str(tail["received_at"]))
        except EventStoreError as exc:
            raise JournalCorrupt("journal tail receipt timestamp is invalid") from exc
        expected_hash = entry_hash(
            sequence=tail_sequence,
            received_at=str(tail["received_at"]),
            event_digest=digest,
            previous_entry_hash=tail["previous_entry_hash"],
        )
        if (
            tail["entry_hash"] != expected_hash
            or control["last_entry_hash"] != expected_hash
            or control["last_verified_sequence"] != tail_sequence
            or control["last_verified_hash"] != expected_hash
            or control["last_verified_at"] != tail["received_at"]
        ):
            raise JournalCorrupt("journal control tail metadata is invalid")

    def _map_sqlite_error(self, exc: Exception) -> Exception:
        if not isinstance(exc, sqlite3.Error):
            return exc
        code = getattr(exc, "sqlite_errorcode", None)
        primary = code & 0xFF if isinstance(code, int) else None
        if primary in {sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED}:
            return JournalBusy("journal writer lock could not be acquired")
        if isinstance(exc, sqlite3.IntegrityError):
            return JournalCorrupt("unexpected SQLite constraint failure during append")
        return EventStoreError("SQLite write failed")

    def _receipt_from_row(self, row: sqlite3.Row) -> AppendReceipt:
        return AppendReceipt(
            sequence=int(row["sequence"]),
            event_id=str(row["event_id"]),
            event_digest=str(row["event_digest"]),
            subject_kind=str(row["subject_kind"]),
            subject_id=str(row["subject_id"]),
            subject_version=int(row["subject_version"]),
            received_at=str(row["received_at"]),
            previous_entry_hash=row["previous_entry_hash"],
            entry_hash=str(row["entry_hash"]),
        )

    def read(
        self,
        *,
        after_sequence: int = 0,
        scan_limit: int = 100,
        filters: Mapping[str, str] | None = None,
    ) -> EventPage:
        after = _strict_integer(after_sequence, minimum=0, code="INVALID_CURSOR", label="after sequence")
        limit = _strict_integer(scan_limit, minimum=1, code="INVALID_CURSOR", label="scan limit")
        if limit > MAX_SCAN_LIMIT:
            raise InvalidCursor("scan limit exceeds the bounded maximum", maximum=MAX_SCAN_LIMIT)
        selected = dict(filters or {})
        allowed_filters = {"subject_kind", "subject_id", "event_type", "classification"}
        if set(selected) - allowed_filters or not all(isinstance(value, str) for value in selected.values()):
            raise InvalidCursor("event filters contain an unsupported field or value")
        connection = self._connect(readonly=True)
        try:
            with self._read_snapshot(connection):
                report = self._verify_integrity_connection(connection)
                if after > report.last_sequence:
                    raise InvalidCursor("cursor is beyond the journal high-water sequence")
                rows = connection.execute(
                    "SELECT * FROM journal_entries WHERE sequence > ? ORDER BY sequence LIMIT ?",
                    (after, limit),
                ).fetchall()
                entries: list[JournalEntryRecord] = []
                for row in rows:
                    if any(row[key] != value for key, value in selected.items()):
                        continue
                    entries.append(self._record_from_row(row))
                next_after = int(rows[-1]["sequence"]) if rows else after
                return EventPage(
                    entries=tuple(entries),
                    after_sequence=after,
                    next_after_sequence=next_after,
                    high_water_sequence=report.last_sequence,
                    has_more=next_after < report.last_sequence,
                )
        finally:
            connection.close()

    def _record_from_row(self, row: sqlite3.Row) -> JournalEntryRecord:
        event = parse_json_strict(bytes(row["event_json"]).decode("utf-8"))
        if not isinstance(event, dict):
            raise JournalCorrupt("stored event is not an object")
        return JournalEntryRecord(
            sequence=int(row["sequence"]),
            received_at=str(row["received_at"]),
            event=event,
            event_digest=str(row["event_digest"]),
            previous_entry_hash=row["previous_entry_hash"],
            entry_hash=str(row["entry_hash"]),
        )

    def subject_version(self, subject_kind: str, subject_id: str) -> int:
        if not subject_kind or not subject_id:
            raise EventStoreError("subject identity must be non-empty")
        connection = self._connect(readonly=True)
        try:
            with self._read_snapshot(connection):
                self._verify_integrity_connection(connection)
                row = connection.execute(
                    "SELECT version FROM subject_versions WHERE subject_kind = ? AND subject_id = ?",
                    (subject_kind, subject_id),
                ).fetchone()
                return int(row["version"]) if row is not None else 0
        finally:
            connection.close()

    def verify_integrity(self) -> IntegrityReport:
        connection = self._connect(readonly=True, allow_halted=True)
        try:
            with self._read_snapshot(connection):
                return self._verify_integrity_connection(connection)
        finally:
            connection.close()

    @contextmanager
    def _read_snapshot(self, connection: sqlite3.Connection) -> Iterator[None]:
        try:
            connection.execute("BEGIN")
            yield
            connection.execute("COMMIT")
        except Exception as exc:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            if isinstance(exc, sqlite3.Error):
                mapped = self._map_sqlite_error(exc)
                if isinstance(mapped, JournalBusy):
                    raise mapped from exc
                raise JournalCorrupt("journal read transaction failed") from exc
            raise

    def _verify_database_contract(
        self,
        connection: sqlite3.Connection,
        *,
        full_storage_check: bool,
    ) -> int:
        application_id = int(connection.execute("PRAGMA application_id").fetchone()[0])
        schema_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
        mode = str(connection.execute("PRAGMA journal_mode").fetchone()[0]).lower()
        synchronous = int(connection.execute("PRAGMA synchronous").fetchone()[0])
        if application_id != self.application_id or schema_version != self.latest_schema_version:
            raise JournalCorrupt("journal identity or schema version is inconsistent")
        if mode != "wal" or synchronous != 2:
            raise JournalCorrupt("journal durability pragmas are not WAL/FULL")
        if self._schema_fingerprint(connection) != self._expected_schema_fingerprint:
            raise JournalCorrupt("journal SQLite schema differs from pinned migrations")
        if full_storage_check:
            integrity = connection.execute("PRAGMA integrity_check").fetchall()
            if [row[0] for row in integrity] != ["ok"]:
                raise JournalCorrupt("SQLite integrity check failed")
            if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
                raise JournalCorrupt("SQLite foreign-key check failed")
        migration_rows = connection.execute(
            "SELECT version, name, digest, applied_at FROM schema_migrations ORDER BY version"
        ).fetchall()
        expected_migrations = [
            (item["version"], item["name"], item["digest"])
            for item in self._manifest["migrations"]
        ]
        actual_migrations = [
            (row["version"], row["name"], row["digest"]) for row in migration_rows
        ]
        if actual_migrations != expected_migrations:
            raise MigrationDrift("applied migration ledger disagrees with the manifest")
        for row in migration_rows:
            try:
                _validated_time(str(row["applied_at"]))
            except EventStoreError as exc:
                raise MigrationDrift("applied migration timestamp is invalid") from exc
        return schema_version

    def _verify_integrity_connection(self, connection: sqlite3.Connection) -> IntegrityReport:
        try:
            return self._verify_integrity_connection_unlatched(connection)
        except (JournalCorrupt, MigrationDrift):
            self._latch_operator_halt()
            raise

    def _verify_integrity_connection_unlatched(
        self,
        connection: sqlite3.Connection,
    ) -> IntegrityReport:
        try:
            schema_version = self._verify_database_contract(
                connection,
                full_storage_check=True,
            )

            rows = connection.execute("SELECT * FROM journal_entries ORDER BY sequence").fetchall()
            previous_hash: str | None = None
            subjects: dict[tuple[str, str], tuple[int, int, str, str]] = {}
            for expected_sequence, row in enumerate(rows, start=1):
                sequence = int(row["sequence"])
                if sequence != expected_sequence:
                    raise JournalCorrupt("journal sequence contains a gap")
                raw = bytes(row["event_json"])
                try:
                    event = parse_json_strict(raw.decode("utf-8"))
                except (UnicodeError, ContractError) as exc:
                    raise JournalCorrupt("stored event bytes are not strict canonical JSON") from exc
                if not isinstance(event, dict) or canonicalize(event) != raw:
                    raise JournalCorrupt("stored event bytes are not canonical")
                try:
                    self.registry.validate(event, kind="OrganizationEvent", version="1.0.0")
                except ContractError as exc:
                    raise JournalCorrupt("stored event no longer satisfies its registered contract") from exc
                digest = sha256_bytes(raw)
                if row["event_digest"] != digest:
                    raise JournalCorrupt("stored event digest is invalid")
                subject = event["subject"]
                idempotency = event["idempotency"]
                duplicated = {
                    "event_id": event["id"],
                    "idempotency_scope": idempotency["scope"],
                    "idempotency_key_digest": idempotency["key_digest"],
                    "subject_kind": subject["kind"],
                    "subject_id": subject["id"],
                    "subject_version": subject["version"],
                    "event_type": event["event_type"],
                    "classification": event["classification"],
                    "occurred_at": event["occurred_at"],
                }
                if any(row[key] != value for key, value in duplicated.items()):
                    raise JournalCorrupt("journal index metadata disagrees with canonical event bytes")
                if row["previous_entry_hash"] != previous_hash:
                    raise JournalCorrupt("journal previous-entry link is broken")
                try:
                    _validated_time(str(row["received_at"]))
                except EventStoreError as exc:
                    raise JournalCorrupt("journal receipt timestamp is invalid") from exc
                expected_hash = entry_hash(
                    sequence=sequence,
                    received_at=str(row["received_at"]),
                    event_digest=digest,
                    previous_entry_hash=previous_hash,
                )
                if row["entry_hash"] != expected_hash:
                    raise JournalCorrupt("journal entry hash is invalid")
                key = (subject["kind"], subject["id"])
                prior = subjects.get(key)
                prior_version = prior[0] if prior is not None else 0
                if subject["version"] != prior_version + 1:
                    raise JournalCorrupt("subject versions are not contiguous")
                if prior is not None and (
                    event["causation_event_id"] != prior[2]
                    or event["correlation_event_id"] != prior[3]
                ):
                    raise JournalCorrupt("subject correlation or causation chain is broken")
                subjects[key] = (
                    subject["version"],
                    sequence,
                    event["id"],
                    event["correlation_event_id"],
                )
                previous_hash = expected_hash

            self._after_integrity_rows_scanned(connection, len(rows))
            control_rows = connection.execute("SELECT * FROM journal_control").fetchall()
            if len(control_rows) != 1 or control_rows[0]["singleton"] != 1:
                raise JournalCorrupt("journal control row cardinality is invalid")
            control = control_rows[0]
            last_sequence = len(rows)
            expected_last_hash = previous_hash
            if (
                control["integrity_state"] != "healthy"
                or control["last_sequence"] != (last_sequence or None)
                or control["last_entry_hash"] != expected_last_hash
                or control["last_verified_sequence"] != (last_sequence or None)
                or control["last_verified_hash"] != expected_last_hash
            ):
                raise JournalCorrupt("journal control tail disagrees with stored entries")
            if last_sequence:
                if control["last_verified_at"] != rows[-1]["received_at"]:
                    raise JournalCorrupt("journal verification timestamp disagrees with its tail")
            elif control["last_verified_at"] is not None:
                raise JournalCorrupt("empty journal has a verification timestamp")
            sqlite_sequence_row = connection.execute(
                "SELECT seq FROM sqlite_sequence WHERE name = 'journal_entries'"
            ).fetchone()
            sqlite_sequence = int(sqlite_sequence_row["seq"]) if sqlite_sequence_row is not None else 0
            if sqlite_sequence != last_sequence:
                raise JournalCorrupt("SQLite sequence tail disagrees with journal entries")
            subject_rows = connection.execute(
                "SELECT subject_kind, subject_id, version, last_sequence FROM subject_versions"
            ).fetchall()
            actual_subjects = {
                (row["subject_kind"], row["subject_id"]): (row["version"], row["last_sequence"])
                for row in subject_rows
            }
            expected_subjects = {
                key: (value[0], value[1]) for key, value in subjects.items()
            }
            if actual_subjects != expected_subjects:
                raise JournalCorrupt("subject-version index disagrees with journal entries")
            return IntegrityReport(
                entry_count=len(rows),
                subject_count=len(subjects),
                last_sequence=last_sequence,
                last_entry_hash=expected_last_hash,
                schema_version=schema_version,
            )
        except EventStoreError:
            raise
        except sqlite3.Error as exc:
            mapped = self._map_sqlite_error(exc)
            if isinstance(mapped, JournalBusy):
                raise mapped from exc
            raise JournalCorrupt("journal schema or SQLite state is unreadable") from exc

    def _after_integrity_rows_scanned(
        self,
        connection: sqlite3.Connection,
        row_count: int,
    ) -> None:
        """Test seam for proving read-snapshot isolation across a concurrent commit."""

    def stats(self) -> JournalStats:
        connection = self._connect(readonly=True)
        try:
            with self._read_snapshot(connection):
                report = self._verify_integrity_connection(connection)
                page_count = int(connection.execute("PRAGMA page_count").fetchone()[0])
                page_size = int(connection.execute("PRAGMA page_size").fetchone()[0])
                return JournalStats(
                    entry_count=report.entry_count,
                    subject_count=report.subject_count,
                    last_sequence=report.last_sequence,
                    last_entry_hash=report.last_entry_hash,
                    database_size_bytes=page_count * page_size,
                    page_count=page_count,
                    page_size=page_size,
                )
        finally:
            connection.close()

    def backup(
        self,
        generation_root: Path,
        *,
        copy_deadline_seconds: float = 30.0,
    ) -> BackupReceipt:
        """Publish one complete immutable backup generation atomically."""

        if (
            isinstance(copy_deadline_seconds, bool)
            or not isinstance(copy_deadline_seconds, (int, float))
            or copy_deadline_seconds <= 0
        ):
            raise BackupFailed("backup copy deadline must be positive")
        generation_root = Path(generation_root).absolute()
        _ensure_private_root(generation_root, BackupFailed)
        generation_name, staging, destination = _new_generation_staging(
            generation_root,
            "backup",
        )
        database = staging / BACKUP_DATABASE_NAME
        receipt_path = staging / BACKUP_RECEIPT_NAME
        source: sqlite3.Connection | None = None
        target: sqlite3.Connection | None = None
        started = time.monotonic()

        def progress(_: int, __: int, ___: int) -> None:
            if time.monotonic() - started > copy_deadline_seconds:
                raise BackupFailed("online backup copy exceeded its deadline")

        try:
            source = self._connect(readonly=True)
            target = sqlite3.connect(database, isolation_level=None)
            os.chmod(database, 0o600)
            with self._read_snapshot(source):
                self._verify_integrity_connection(source)
                source.backup(target, pages=128, progress=progress, sleep=0.01)
            target.execute("PRAGMA journal_mode = WAL")
            target.execute("PRAGMA synchronous = FULL")
            target.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            target.close()
            target = None
            source.close()
            source = None

            backup_store = EventStore(
                database,
                registry=self.registry,
                migration_manifest=self.migration_manifest_path,
                busy_timeout_ms=self.busy_timeout_ms,
                clock=self.clock,
                initialize=False,
            )
            report = backup_store.verify_integrity()
            _checkpoint_closed_database(database, BackupFailed)
            created_at = _validated_time(self.clock())
            with database.open("rb") as handle:
                os.fsync(handle.fileno())
            body = database.read_bytes()
            receipt = BackupReceipt(
                schema_version="1.0.0",
                backup_name=generation_name,
                backup_digest=sha256_bytes(body),
                size_bytes=len(body),
                source_last_sequence=report.last_sequence,
                source_last_entry_hash=report.last_entry_hash,
                created_at=created_at,
            )
            _atomic_no_clobber_bytes(
                receipt_path,
                canonicalize(receipt.to_dict()) + b"\n",
            )
            if database.stat().st_mode & 0o777 != 0o600:
                raise BackupFailed("backup database permissions are not private")
            if receipt_path.stat().st_mode & 0o777 != 0o600:
                raise BackupFailed("backup receipt permissions are not private")
            _fsync_directory(staging)
            _publish_generation(staging, destination)
            return receipt
        except Exception:
            if target is not None:
                target.close()
            if source is not None:
                source.close()
            if staging.exists():
                shutil.rmtree(staging)
            raise

    def restore_verified(
        self,
        backup_generation: Path,
        generation_root: Path,
    ) -> "EventStore":
        """Verify a closed backup generation and atomically publish a fresh live generation."""

        backup_generation = Path(backup_generation).absolute()
        generation_root = Path(generation_root).absolute()
        try:
            generation_root.relative_to(backup_generation)
        except ValueError:
            pass
        else:
            raise RestoreInvalid(
                "restore destination must not modify the immutable backup generation"
            )
        if backup_generation.is_symlink() or not backup_generation.is_dir():
            raise RestoreInvalid("backup generation is missing or not a directory")
        if backup_generation.stat().st_mode & 0o077:
            raise RestoreInvalid("backup generation permissions are not private")
        children = {path.name for path in backup_generation.iterdir()}
        if children != {BACKUP_DATABASE_NAME, BACKUP_RECEIPT_NAME}:
            raise RestoreInvalid("backup generation contents differ from the closed contract")
        backup_path = backup_generation / BACKUP_DATABASE_NAME
        receipt_path = backup_generation / BACKUP_RECEIPT_NAME
        if (
            backup_path.is_symlink()
            or not backup_path.is_file()
            or receipt_path.is_symlink()
            or not receipt_path.is_file()
        ):
            raise RestoreInvalid("backup generation members are invalid")
        if backup_path.stat().st_mode & 0o077 or receipt_path.stat().st_mode & 0o077:
            raise RestoreInvalid("backup generation member permissions are not private")
        try:
            value = parse_json_strict(receipt_path.read_text(encoding="utf-8"))
            if not isinstance(value, dict):
                raise RestoreInvalid("backup receipt is not an object")
            receipt = BackupReceipt(**value)
        except (OSError, TypeError, ContractError) as exc:
            raise RestoreInvalid("backup receipt is missing or invalid") from exc
        self._validate_backup_receipt(receipt, backup_generation.name)
        if (
            receipt.size_bytes != backup_path.stat().st_size
            or receipt.backup_digest != sha256_bytes(backup_path.read_bytes())
        ):
            raise RestoreInvalid("backup bytes disagree with their receipt")
        _ensure_private_root(generation_root, RestoreInvalid)
        _, staging, destination = _new_generation_staging(generation_root, "restore")
        temporary = staging / BACKUP_DATABASE_NAME
        try:
            descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with backup_path.open("rb") as source, os.fdopen(descriptor, "wb") as target:
                shutil.copyfileobj(source, target)
                target.flush()
                os.fsync(target.fileno())
            temporary_store = EventStore(
                temporary,
                registry=self.registry,
                migration_manifest=self.migration_manifest_path,
                busy_timeout_ms=self.busy_timeout_ms,
                clock=self.clock,
                initialize=False,
            )
            copied_body = temporary.read_bytes()
            if (
                len(copied_body) != receipt.size_bytes
                or sha256_bytes(copied_body) != receipt.backup_digest
            ):
                raise RestoreInvalid("copied backup bytes disagree with their receipt")
            copied_report = temporary_store.verify_integrity()
            if (
                copied_report.last_sequence != receipt.source_last_sequence
                or copied_report.last_entry_hash != receipt.source_last_entry_hash
            ):
                raise RestoreInvalid("copied backup tail disagrees with its receipt")
            _checkpoint_closed_database(temporary, RestoreInvalid)
            if temporary.stat().st_mode & 0o777 != 0o600:
                raise RestoreInvalid("restored database permissions are not private")
            _fsync_directory(staging)
            _publish_generation(staging, destination)
        except Exception:
            if staging.exists():
                shutil.rmtree(staging)
            raise
        restored = EventStore(
            destination / BACKUP_DATABASE_NAME,
            registry=self.registry,
            migration_manifest=self.migration_manifest_path,
            busy_timeout_ms=self.busy_timeout_ms,
            clock=self.clock,
            initialize=False,
        )
        final_report = restored.verify_integrity()
        if (
            final_report.last_sequence != receipt.source_last_sequence
            or final_report.last_entry_hash != receipt.source_last_entry_hash
        ):
            raise RestoreInvalid("published restore tail disagrees with its receipt")
        return restored

    @staticmethod
    def _validate_backup_receipt(receipt: BackupReceipt, backup_name: str) -> None:
        if (
            receipt.schema_version != "1.0.0"
            or receipt.backup_name != backup_name
            or isinstance(receipt.size_bytes, bool)
            or not isinstance(receipt.size_bytes, int)
            or receipt.size_bytes < 0
            or isinstance(receipt.source_last_sequence, bool)
            or not isinstance(receipt.source_last_sequence, int)
            or receipt.source_last_sequence < 0
            or not _valid_digest(receipt.backup_digest)
            or (
                receipt.source_last_sequence == 0
                and receipt.source_last_entry_hash is not None
            )
            or (
                receipt.source_last_sequence > 0
                and not _valid_digest(receipt.source_last_entry_hash)
            )
        ):
            raise RestoreInvalid("backup receipt fields are invalid")
        try:
            _validated_time(receipt.created_at)
        except EventStoreError as exc:
            raise RestoreInvalid("backup receipt timestamp is invalid") from exc

    def iter_rows_for_projection(self, connection: sqlite3.Connection) -> Iterable[sqlite3.Row]:
        """Return verified rows to the repository-owned projector transaction."""

        self._verify_integrity_connection(connection)
        return connection.execute("SELECT * FROM journal_entries ORDER BY sequence").fetchall()


__all__ = [
    "AppendReceipt",
    "BackupDestinationExists",
    "BackupFailed",
    "BackupReceipt",
    "CHAIN_PROFILE",
    "DEFAULT_DATABASE_PATH",
    "EventIdentityConflict",
    "EventCausationConflict",
    "EventPage",
    "EventStore",
    "EventStoreError",
    "IdempotencyConflict",
    "IntegrityReport",
    "InvalidCursor",
    "JournalBusy",
    "JournalCorrupt",
    "JournalEntryRecord",
    "JournalStats",
    "MigrationAhead",
    "MigrationDrift",
    "MigrationFailed",
    "RestoreInvalid",
    "SubjectVersionConflict",
    "entry_hash",
]
