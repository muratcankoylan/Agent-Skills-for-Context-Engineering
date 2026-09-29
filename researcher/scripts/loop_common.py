#!/usr/bin/env python3
"""Shared helpers for the continuous research loop scripts.

Read helpers remain importable when Unix locking is unavailable. Operations
requiring process exclusion (`queue_lock`, `append_jsonl`) then fail before
creating paths. Generic atomic writers still require their caller's queue lock.
This is advisory locking for cooperating processes on trusted local filesystems,
not a Windows mutation backend, distributed lock or crash-recovery journal.
Append sidecars protect target creation; the ledger-inode flock is retained to
coordinate with older writers and path aliases. Do not unlink live lock files.
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
    import fcntl
except ImportError:
    fcntl = None


ROOT = Path(__file__).resolve().parents[2]
RESEARCHER = ROOT / "researcher"
QUEUE_DIR = RESEARCHER / "queue"
ORCH_DIR = RESEARCHER / "orchestration"
REPORTS_DIR = RESEARCHER / "reports"
RUNS_DIR = RESEARCHER / "runs"
SNAPSHOTS_DIR = REPORTS_DIR / "snapshots"
LOCK_DIR = QUEUE_DIR / ".locks"
JSONL_QUARANTINE_DIR = REPORTS_DIR / "jsonl-quarantine"


class LockingUnavailableError(RuntimeError):
    """The platform cannot supply the required process-wide lock."""


class LockReleaseOutcomeUncertainError(RuntimeError):
    """The body finished but unlocking failed; do not blindly repeat effects."""

    effects_may_have_committed = True


def _require_fcntl() -> Any:
    if fcntl is None:
        raise LockingUnavailableError("queue mutation requires Unix fcntl.flock")
    return fcntl


@contextmanager
def _exclusive_flock(handle: TextIO) -> Iterator[None]:
    backend = _require_fcntl()
    backend.flock(handle.fileno(), backend.LOCK_EX)
    try:
        yield
    except BaseException:
        try:
            backend.flock(handle.fileno(), backend.LOCK_UN)
        except OSError:
            pass  # Preserve the original body failure; closing still releases the descriptor.
        raise
    else:
        try:
            backend.flock(handle.fileno(), backend.LOCK_UN)
        except OSError as exc:
            raise LockReleaseOutcomeUncertainError(
                "protected effects may have committed before lock release failed"
            ) from exc


@contextmanager
def _lock_file(path: Path) -> Iterator[None]:
    _require_fcntl()
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ValueError("lock must be a single-link regular file")
        with os.fdopen(descriptor, "a+", encoding="utf-8") as handle:
            descriptor = -1
            with _exclusive_flock(handle):
                yield
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _atomic_write(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise


def write_json(path: Path, data: Any) -> None:
    _atomic_write(path, json.dumps(data, indent=2) + "\n")


def _quarantine_bad_line(path: Path, line_number: int, line: str, exc: Exception) -> None:
    JSONL_QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    target = JSONL_QUARANTINE_DIR / f"{path.name}.{timestamp}.{line_number}.txt"
    target.write_text(f"# {exc}\n{line}\n", encoding="utf-8")


def read_jsonl(path: Path, *, tolerant: bool = True) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
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
    lines = [json.dumps(record, sort_keys=True) for record in records]
    _atomic_write(path, ("\n".join(lines) + "\n") if lines else "")


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    _require_fcntl()
    payload = json.dumps(record, sort_keys=True) + "\n"
    # A denied sidecar lock must not create an empty ledger. The target lock is
    # still needed for old writers and hardlink/case aliases; a later target-lock
    # failure can leave an empty new file, which must not be treated as a receipt.
    identity = hashlib.sha256(str(path.resolve()).encode("utf-8")).hexdigest()
    with _lock_file(LOCK_DIR / f"append-{identity}.lock"):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            with _exclusive_flock(handle):
                handle.write(payload)
                handle.flush()


@contextmanager
def queue_lock(name: str) -> Iterator[None]:
    """Exclusive lock for queue mutations. Use one lock per queue file family."""

    _require_fcntl()
    if not isinstance(name, str) or re.fullmatch(r"[a-z0-9][a-z0-9_.-]{0,127}", name) is None:
        raise ValueError("invalid queue lock name")
    with _lock_file(LOCK_DIR / f"{name}.lock"):
        yield


def load_config() -> dict[str, Any]:
    return load_json(ORCH_DIR / "config.json")


def source_id_for(url: str) -> str:
    digest = hashlib.sha256(url.strip().lower().encode("utf-8")).hexdigest()
    return digest[:16]


def list_run_dirs() -> list[Path]:
    if not RUNS_DIR.exists():
        return []
    return sorted(path for path in RUNS_DIR.iterdir() if path.is_dir())


def load_run_state(run_dir: Path) -> dict[str, Any] | None:
    state_file = run_dir / "run-state.json"
    if not state_file.exists():
        return None
    try:
        return load_json(state_file)
    except json.JSONDecodeError:
        return None


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
    for run_dir in list_run_dirs():
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
