#!/usr/bin/env python3
"""Shared helpers for the legacy, supervised research-loop scripts.

All queue mutations go through atomic writes (`write_json`, `write_jsonl`) and
process-wide advisory file locks (`queue_lock`) on Unix runtimes with
``fcntl.flock``. The module remains importable without ``fcntl`` for capability
detection, but every queue or append mutation then fails before filesystem
changes. These helpers do not provide production event-journal authority.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator, TextIO

try:
    import fcntl as _fcntl
except ImportError:  # pragma: no cover - exercised through isolated import tests
    _fcntl = None

# Compatibility alias for the existing legacy tests and callers. New code uses
# ``_fcntl`` so an unsupported runtime remains importable and can fail closed.
fcntl = _fcntl

if __package__:
    from .validate_run import (
        DuplicateKeyError,
        NonFiniteJSONNumberError,
        normalize_source_url as _normalize_source_url,
        strict_json_loads,
        validate_state_document,
    )
else:  # Direct script execution.
    from validate_run import (
        DuplicateKeyError,
        NonFiniteJSONNumberError,
        normalize_source_url as _normalize_source_url,
        strict_json_loads,
        validate_state_document,
    )


ROOT = Path(__file__).resolve().parents[2]
RESEARCHER = ROOT / "researcher"
QUEUE_DIR = RESEARCHER / "queue"
ORCH_DIR = RESEARCHER / "orchestration"
REPORTS_DIR = RESEARCHER / "reports"
RUNS_DIR = RESEARCHER / "runs"
SNAPSHOTS_DIR = REPORTS_DIR / "snapshots"
LOCK_DIR = QUEUE_DIR / ".locks"
JSONL_QUARANTINE_DIR = REPORTS_DIR / "jsonl-quarantine"
RUNTIME_QUEUE_LEDGERS = ("inbox.jsonl", "parked.jsonl", "done.jsonl", "quarantine.jsonl")


class DurabilityUncertainError(RuntimeError):
    """A visible write may not have reached stable storage; reconcile, do not retry."""

    effects_may_have_committed = True


class LockingUnavailableError(RuntimeError):
    """The runtime cannot provide the required process-wide advisory lock."""


class AppendRollbackError(RuntimeError):
    """An append failed and restoring the prior ledger state was unsuccessful."""

    effects_may_have_committed = True


class LockReleaseOutcomeUncertainError(DurabilityUncertainError):
    """The protected body completed but releasing its advisory lock failed."""


def _require_fcntl() -> Any:
    """Return the Unix lock backend or fail before any mutation side effect."""

    if _fcntl is None:
        raise LockingUnavailableError(
            "legacy queue mutations require fcntl.flock; supported supervised "
            "platforms are macOS and Linux"
        )
    return _fcntl


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def load_json(path: Path) -> Any:
    return strict_json_loads(path.read_text(encoding="utf-8"))


def _atomic_write(path: Path, payload: str) -> None:
    path = Path(os.path.abspath(path))
    _ensure_real_directory(path.parent)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )
    replaced = False
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
        replaced = True
        try:
            _fsync_directory(path.parent)
        except OSError as exc:
            raise DurabilityUncertainError(
                f"replacement is visible but parent durability is uncertain: {path}"
            ) from exc
    except Exception:
        if not replaced:
            try:
                os.unlink(tmp_name)
            except FileNotFoundError:
                pass
        raise


def write_json(path: Path, data: Any) -> None:
    _atomic_write(path, json.dumps(data, indent=2, allow_nan=False) + "\n")


def write_text(path: Path, payload: str) -> None:
    _atomic_write(path, payload)


def _quarantine_bad_line(path: Path, line_number: int, line: str, exc: Exception) -> None:
    JSONL_QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    line_digest = hashlib.sha256(line.encode("utf-8")).hexdigest()[:12]
    target = (
        JSONL_QUARANTINE_DIR
        / f"{path.name}.{timestamp}.{line_number}.{line_digest}.txt"
    )
    target.write_text(f"# {exc}\n{line}\n", encoding="utf-8")


def read_jsonl(path: Path, *, tolerant: bool = False) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        try:
            value = strict_json_loads(line)
        except (
            json.JSONDecodeError,
            DuplicateKeyError,
            NonFiniteJSONNumberError,
        ) as exc:
            if not tolerant:
                raise
            _quarantine_bad_line(path, line_number, raw, exc)
            continue
        if not isinstance(value, dict):
            if not tolerant:
                raise ValueError(f"{path}:{line_number} expected object, got {type(value).__name__}")
            _quarantine_bad_line(path, line_number, raw, ValueError("not an object"))
            continue
        records.append(value)
    return records


def write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> None:
    lines = [
        json.dumps(record, sort_keys=True, allow_nan=False) for record in records
    ]
    _atomic_write(path, ("\n".join(lines) + "\n") if lines else "")


def _require_lock_path_identity(path: Path, handle: TextIO) -> None:
    """Require the lock pathname to still name the locked single-link inode."""

    path_info = os.lstat(path)
    descriptor_info = os.fstat(handle.fileno())
    if (
        stat.S_ISLNK(path_info.st_mode)
        or not stat.S_ISREG(path_info.st_mode)
        or path_info.st_nlink != 1
        or not stat.S_ISREG(descriptor_info.st_mode)
        or descriptor_info.st_nlink != 1
        or (path_info.st_dev, path_info.st_ino)
        != (descriptor_info.st_dev, descriptor_info.st_ino)
    ):
        raise ValueError(f"lock pathname no longer identifies the held inode: {path}")


@contextmanager
def _exclusive_flock(
    handle: TextIO,
    *,
    lock_path: Path | None = None,
) -> Iterator[None]:
    """Hold an exclusive flock and preserve an active body exception on release."""

    backend = _require_fcntl()
    backend.flock(handle.fileno(), backend.LOCK_EX)
    try:
        if lock_path is not None:
            _require_lock_path_identity(lock_path, handle)
        yield
        if lock_path is not None:
            try:
                _require_lock_path_identity(lock_path, handle)
            except (OSError, ValueError) as exc:
                raise DurabilityUncertainError(
                    f"lock pathname changed during the protected operation: {lock_path}"
                ) from exc
    except BaseException:
        try:
            backend.flock(handle.fileno(), backend.LOCK_UN)
        except OSError:
            # The body failure is the primary error. Replacing it with a release
            # error would hide the operation that may have left partial state.
            pass
        raise
    else:
        try:
            backend.flock(handle.fileno(), backend.LOCK_UN)
        except OSError as exc:
            raise LockReleaseOutcomeUncertainError(
                "lock release failed after the protected operation completed; "
                "filesystem effects may already have committed"
            ) from exc


def _append_lock_path(path: Path) -> Path:
    identity = str(path.resolve(strict=False)).encode("utf-8")
    return LOCK_DIR / f"append-{hashlib.sha256(identity).hexdigest()}.lock"


@contextmanager
def _open_lock_file(path: Path) -> Iterator[TextIO]:
    """Open a single-link regular lock inode without following aliases."""

    _require_fcntl()
    path = Path(os.path.abspath(path))
    _ensure_real_directory(path.parent)
    flags = (
        os.O_RDWR
        | os.O_CREAT
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    descriptor = os.open(path, flags, 0o600)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ValueError(f"lock must be a single-link regular file: {path}")
        with os.fdopen(descriptor, "a+", encoding="utf-8") as handle:
            descriptor = -1
            yield handle
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _require_real_directory(path: Path) -> Path:
    """Reject a symlinked directory or repository-local symlink ancestor."""

    candidate = Path(os.path.abspath(path))
    root = Path(os.path.abspath(ROOT))
    try:
        relative = candidate.relative_to(root)
    except ValueError:
        components = [candidate]
    else:
        components = [root]
        current = root
        for part in relative.parts:
            current /= part
            components.append(current)
    for component in components:
        info = os.lstat(component)
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise ValueError(f"runtime directory must be a real directory: {component}")
    return candidate


def _ensure_real_directory(path: Path) -> Path:
    """Create missing directory components only below a verified real parent."""

    candidate = Path(os.path.abspath(path))
    missing: list[Path] = []
    current = candidate
    while True:
        try:
            os.lstat(current)
        except FileNotFoundError:
            missing.append(current)
            parent = current.parent
            if parent == current:
                raise ValueError(f"no real parent exists for runtime directory: {candidate}")
            current = parent
            continue
        break
    _require_real_directory(current)
    for directory in reversed(missing):
        try:
            os.mkdir(directory, 0o700)
        except FileExistsError:
            # Another cooperating process may create the same runtime directory
            # between discovery and creation. Identity is revalidated below.
            pass
        _require_real_directory(directory)
    return candidate


def _descriptor_matches_path(path: Path, descriptor: int) -> bool:
    """Return whether the lexical path still names the opened descriptor inode."""

    try:
        path_info = os.lstat(path)
    except OSError:
        return False
    descriptor_info = os.fstat(descriptor)
    return (
        not stat.S_ISLNK(path_info.st_mode)
        and stat.S_ISREG(path_info.st_mode)
        and path_info.st_nlink == 1
        and stat.S_ISREG(descriptor_info.st_mode)
        and descriptor_info.st_nlink == 1
        and (path_info.st_dev, path_info.st_ino)
        == (descriptor_info.st_dev, descriptor_info.st_ino)
    )


def _rollback_failed_append(
    path: Path,
    descriptor: int,
    *,
    created: bool,
    original_size: int,
    cause: BaseException,
) -> None:
    """Restore the pre-append ledger bytes or report an uncertain outcome."""

    try:
        if not _descriptor_matches_path(path, descriptor):
            raise OSError("append target identity changed during rollback")
        if created:
            path.unlink()
        else:
            os.ftruncate(descriptor, original_size)
            os.fsync(descriptor)
    except BaseException as exc:
        raise AppendRollbackError(
            f"append failed and prior ledger state could not be restored: {path}"
        ) from cause


def _append_payload(path: Path, payload: bytes) -> bool:
    """Append under both the caller's sidecar and the legacy ledger-inode lock."""

    flags = (
        os.O_WRONLY
        | os.O_APPEND
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    descriptor = -1
    created = False
    original_size = 0
    try:
        try:
            descriptor = os.open(path, flags | os.O_CREAT | os.O_EXCL, 0o600)
            created = True
        except FileExistsError:
            descriptor = os.open(path, flags)

        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ValueError(f"append target must be a single-link regular file: {path}")
        if not _descriptor_matches_path(path, descriptor):
            raise ValueError(f"append target pathname changed during open: {path}")
        # Older cooperating writers lock only this inode. Acquire before
        # measuring rollback length: an older writer may append while we wait.
        # The wrapper borrows the descriptor; the outer finally owns its close.
        with os.fdopen(descriptor, "a", encoding="utf-8", closefd=False) as handle:
            with _exclusive_flock(handle):
                if not _descriptor_matches_path(path, descriptor):
                    raise ValueError("append target identity changed while locking")
                original_size = os.fstat(descriptor).st_size
                try:
                    remaining = memoryview(payload)
                    while remaining:
                        written = os.write(descriptor, remaining)
                        if written <= 0:
                            raise OSError("append write made no progress")
                        remaining = remaining[written:]
                    os.fsync(descriptor)
                    if not _descriptor_matches_path(path, descriptor):
                        raise OSError("append target identity changed before commit")
                except BaseException as exc:
                    # Roll back only attempted writes, while still holding the
                    # inode lock. Validation/acquisition denial is not a write.
                    _rollback_failed_append(
                        path,
                        descriptor,
                        created=created,
                        original_size=original_size,
                        cause=exc,
                    )
                    raise
        return created
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    """Append one legacy record under a process-wide advisory lock.

    Write or file-fsync failures are rolled back before returning failure. A
    typed uncertainty error is raised if rollback, parent fsync, lock identity,
    or lock release cannot prove a single outcome; callers must reconcile by a
    stable record identity rather than retrying blindly.
    """

    _require_fcntl()
    path = Path(os.path.abspath(path))
    payload = (json.dumps(record, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
    _ensure_real_directory(path.parent)
    _ensure_real_directory(LOCK_DIR)
    append_lock_path = _append_lock_path(path)
    with _open_lock_file(append_lock_path) as lock_handle:
        with _exclusive_flock(lock_handle, lock_path=append_lock_path):
            created = _append_payload(path, payload)
            if created:
                try:
                    _fsync_directory(path.parent)
                except OSError as exc:
                    raise DurabilityUncertainError(
                        f"new ledger is visible but parent durability is uncertain: {path}"
                    ) from exc


@contextmanager
def queue_lock(name: str) -> Iterator[None]:
    """Exclusive advisory Unix lock for one queue transaction family."""

    _require_fcntl()
    if type(name) is not str or not re.fullmatch(r"[a-z0-9][a-z0-9_.-]{0,127}", name):
        raise ValueError(f"invalid queue lock name: {name}")
    _ensure_real_directory(LOCK_DIR)
    lock_path = LOCK_DIR / f"{name}.lock"
    with _open_lock_file(lock_path) as handle:
        with _exclusive_flock(handle, lock_path=lock_path):
            yield


def load_config() -> dict[str, Any]:
    return load_json(ORCH_DIR / "config.json")


def require_runtime_queue_directory(path: Path | None = None) -> Path:
    """Return a real queue directory without following a repository symlink."""

    lexical = Path(os.path.abspath(path if path is not None else QUEUE_DIR))
    canonical = Path(os.path.abspath(RESEARCHER / "queue"))
    if lexical == canonical:
        researcher_lexical = Path(os.path.abspath(RESEARCHER))
        try:
            researcher_info = os.lstat(researcher_lexical)
        except OSError as exc:
            raise ValueError(
                f"researcher root is unavailable: {researcher_lexical}"
            ) from exc
        if stat.S_ISLNK(researcher_info.st_mode) or not stat.S_ISDIR(
            researcher_info.st_mode
        ):
            raise ValueError(f"researcher root is unsafe: {researcher_lexical}")
        if researcher_lexical.resolve(strict=True) != researcher_lexical:
            raise ValueError(f"researcher root escapes its canonical path: {RESEARCHER}")
    try:
        info = os.lstat(lexical)
    except OSError as exc:
        raise ValueError(f"runtime queue directory is unavailable: {lexical}") from exc
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise ValueError(f"runtime queue directory is unsafe: {lexical}")
    if lexical == canonical and lexical.resolve(strict=True) != lexical:
        raise ValueError(f"runtime queue directory escapes its canonical path: {lexical}")
    return lexical


def require_runtime_runs_directory(path: Path | None = None) -> Path:
    """Return a real runs directory without following a repository alias."""

    lexical = Path(os.path.abspath(path if path is not None else RUNS_DIR))
    canonical = Path(os.path.abspath(RESEARCHER / "runs"))
    try:
        info = os.lstat(lexical)
    except OSError as exc:
        raise ValueError(f"runtime runs directory is unavailable: {lexical}") from exc
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise ValueError(f"runtime runs directory is unsafe: {lexical}")
    if lexical == canonical:
        _require_real_directory(lexical)
        if lexical.resolve(strict=True) != lexical:
            raise ValueError(f"runtime runs directory escapes its canonical path: {lexical}")
    return lexical


def initialize_runtime_queue_ledgers() -> list[Path]:
    """Explicitly create missing runtime ledgers without replacing existing bytes."""

    queue_dir = require_runtime_queue_directory()
    created: list[Path] = []
    for name in RUNTIME_QUEUE_LEDGERS:
        path = queue_dir / name
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(path, flags, 0o600)
        except FileExistsError:
            info = os.lstat(path)
            if (
                stat.S_ISLNK(info.st_mode)
                or not stat.S_ISREG(info.st_mode)
                or info.st_nlink != 1
            ):
                raise ValueError(f"runtime queue ledger is unsafe: {path}")
            continue
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        created.append(path)
    if created:
        _fsync_directory(queue_dir)
    return created


def require_runtime_queue_ledgers(queue_dir: Path | None = None) -> dict[str, Path]:
    """Require the complete initialized regular-file ledger set."""

    queue_dir = require_runtime_queue_directory(queue_dir)
    ledgers: dict[str, Path] = {}
    for name in RUNTIME_QUEUE_LEDGERS:
        path = queue_dir / name
        try:
            info = os.lstat(path)
        except OSError as exc:
            raise ValueError(
                "runtime queue ledgers are not initialized; run loop_status.py "
                "--initialize-runtime first"
            ) from exc
        if (
            stat.S_ISLNK(info.st_mode)
            or not stat.S_ISREG(info.st_mode)
            or info.st_nlink != 1
        ):
            raise ValueError(f"runtime queue ledger is unsafe: {path}")
        ledgers[name] = path
    return ledgers


def source_id_for(url: str) -> str:
    digest = hashlib.sha256(url.strip().encode("utf-8")).hexdigest()
    return digest[:32]


def normalize_source_url(url: str) -> str:
    """Compatibility export for the shared durable source-URL contract."""

    return _normalize_source_url(url)


def list_run_dirs() -> list[Path]:
    runs_dir = require_runtime_runs_directory(RUNS_DIR)
    result: list[Path] = []
    for path in runs_dir.iterdir():
        try:
            info = os.lstat(path)
        except OSError:
            continue
        if not stat.S_ISLNK(info.st_mode) and stat.S_ISDIR(info.st_mode):
            result.append(path)
    return sorted(result)


def unknown_run_entries(real_run_dirs: Iterable[Path] | None = None) -> list[Path]:
    """Return unsafe/unrecognized entries under the runtime runs root."""

    runs_dir = require_runtime_runs_directory(RUNS_DIR)
    real = set(real_run_dirs if real_run_dirs is not None else list_run_dirs())
    unknown: list[Path] = []
    for entry in runs_dir.iterdir():
        if entry in real:
            continue
        try:
            info = os.lstat(entry)
        except OSError:
            unknown.append(entry)
            continue
        if entry.name == "README.md" and stat.S_ISREG(info.st_mode):
            continue
        unknown.append(entry)
    return sorted(unknown)


def load_run_state(run_dir: Path) -> dict[str, Any] | None:
    state_file = run_dir / "run-state.json"
    try:
        info = os.lstat(state_file)
    except OSError:
        return None
    if (
        stat.S_ISLNK(info.st_mode)
        or not stat.S_ISREG(info.st_mode)
        or info.st_nlink != 1
    ):
        return None
    try:
        state = load_json(state_file)
    except (json.JSONDecodeError, DuplicateKeyError, NonFiniteJSONNumberError):
        return None
    if not isinstance(state, dict) or validate_state_document(
        state, expected_run_id=run_dir.name
    ):
        return None
    return state


def active_run_urls() -> set[str]:
    urls: set[str] = set()
    for run_dir in list_run_dirs():
        state = load_run_state(run_dir)
        if not state:
            continue
        if state.get("current_state") == "closed":
            continue
        url = state.get("source_url")
        if isinstance(url, str) and url:
            urls.add(url)
    return urls


def closed_run_urls() -> set[str]:
    urls: set[str] = set()
    for run_dir in list_run_dirs():
        state = load_run_state(run_dir)
        if not state:
            continue
        if state.get("current_state") != "closed":
            continue
        url = state.get("source_url")
        if isinstance(url, str) and url:
            urls.add(url)
    return urls


def categorize_runs() -> dict[str, list[Path]]:
    buckets: dict[str, list[Path]] = {
        "active": [],
        "parked": [],
        "closed": [],
        "unknown": [],
    }
    parked_ids = {record.get("run_id") for record in read_jsonl(QUEUE_DIR / "parked.jsonl")}
    real_run_dirs = set(list_run_dirs())
    buckets["unknown"].extend(unknown_run_entries(real_run_dirs))
    for run_dir in sorted(real_run_dirs):
        state = load_run_state(run_dir)
        if not state:
            buckets["unknown"].append(run_dir)
            continue
        current = state.get("current_state")
        if current == "closed":
            buckets["closed"].append(run_dir)
        elif run_dir.name in parked_ids:
            buckets["parked"].append(run_dir)
        else:
            buckets["active"].append(run_dir)
    return buckets


def runs_created_today() -> int:
    today = today_utc()
    count = 0
    for run_dir in list_run_dirs():
        state = load_run_state(run_dir)
        if state and state.get("created_at", "").startswith(today):
            count += 1
    return count
