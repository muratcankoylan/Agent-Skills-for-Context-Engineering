#!/usr/bin/env python3
"""Shared helpers for the continuous research loop scripts.

All queue mutations go through atomic writes (`write_json`, `write_jsonl`) and
optional file locks (`queue_lock`). On Unix, locking uses `fcntl.flock`
exclusive locks so concurrent loop_step + loop_discover invocations cannot
race on the inbox or parked queue. On Windows `fcntl` is unavailable, so the
fallback is an in-process `threading.Lock`; this protects against races
between threads in the same process but does not provide inter-process
locking.
"""

from __future__ import annotations

import errno
import hashlib
import json
import os
import tempfile
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator

try:
    import fcntl
except ModuleNotFoundError:  # pragma: no cover
    fcntl = None  # type: ignore[assignment]


ROOT = Path(__file__).resolve().parents[2]
RESEARCHER = ROOT / "researcher"
QUEUE_DIR = RESEARCHER / "queue"
ORCH_DIR = RESEARCHER / "orchestration"
REPORTS_DIR = RESEARCHER / "reports"
RUNS_DIR = RESEARCHER / "runs"
SNAPSHOTS_DIR = REPORTS_DIR / "snapshots"
LOCK_DIR = QUEUE_DIR / ".locks"
JSONL_QUARANTINE_DIR = REPORTS_DIR / "jsonl-quarantine"

# On Windows `fcntl` is unavailable, so fall back to an in-process lock.
# Each named queue lock gets its own `threading.Lock`; `append_jsonl` uses a
# per-path lock for best-effort in-process serialization.
_FALLBACK_LOCKS: dict[str, threading.Lock] = {}
_GLOBAL_FALLBACK_LOCK = threading.Lock()


def _fallback_lock(name: str | None = None) -> threading.Lock:
    if name is None:
        return _GLOBAL_FALLBACK_LOCK
    lock = _FALLBACK_LOCKS.get(name)
    if lock is None:
        lock = _FALLBACK_LOCKS[name] = threading.Lock()
    return lock


def _lock_acquire(handle, *, name: str | None = None) -> None:
    """Acquire an exclusive lock using fcntl when available, else a thread lock."""
    if fcntl is not None:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        except OSError as exc:
            if exc.errno not in {errno.EACCES, errno.EAGAIN}:
                raise
    else:
        _fallback_lock(name).acquire()


def _lock_release(handle, *, name: str | None = None) -> None:
    """Release the lock acquired by `_lock_acquire`."""
    if fcntl is not None:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass
    else:
        _fallback_lock(name).release()


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
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        _lock_acquire(handle, name=str(path))
        try:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
            handle.flush()
        finally:
            _lock_release(handle, name=str(path))


@contextmanager
def queue_lock(name: str) -> Iterator[None]:
    """Exclusive lock for queue mutations. Use one lock per queue file family.

    On Unix this is an advisory fcntl flock; on Windows it falls back to an
    in-process threading lock.
    """

    LOCK_DIR.mkdir(parents=True, exist_ok=True)
    lock_path = LOCK_DIR / f"{name}.lock"
    handle = open(lock_path, "a+")
    try:
        _lock_acquire(handle, name=name)
        yield
    finally:
        _lock_release(handle, name=name)
        handle.close()


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
