"""Small local-only locked/atomic state boundary for the draft example.

This is not the repository's production execution journal or a cloud store.
Started operations are never replayed automatically after a crash.
"""
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import tempfile


def encoded(value) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False,
                      separators=(",", ":")).encode("ascii")


def digest(value) -> str:
    return hashlib.sha256(encoded(value)).hexdigest()


def source_digest() -> str:
    root = Path(__file__).parent
    return digest({str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in sorted(root.rglob("*.py"))})


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate state key")
        result[key] = value
    return result


def read_json(path: Path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 8_388_608:
        raise ValueError("invalid state file")
    return json.loads(path.read_bytes(), object_pairs_hook=_pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite state")))


def atomic_json(path: Path, value) -> None:
    raw = encoded(value)
    if len(raw) > 8_388_608 or path.is_symlink():
        raise ValueError("invalid state write")
    descriptor, name = tempfile.mkstemp(prefix=".dwl-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(name):
            os.unlink(name)


@contextmanager
def locked(path: Path):
    path = Path(path)
    if path.is_symlink():
        raise ValueError("symlink state path refused")
    path = path.parent.resolve() / path.name
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        os.close(descriptor)


def run_once(path: Path, identity: dict, execute):
    """Return only a matching, digest-checked completed result; never retry started.

    A completed receipt is one atomic record, so there is no separate result/index
    commit gap. Local failure after the effect leaves `started` and blocks retry.
    """
    binding = digest(identity)
    with locked(path.with_suffix(path.suffix + ".lock")):
        if path.exists():
            record = read_json(path)
            if (type(record) is not dict or record.get("schema") != "dwl-operation/v1"
                    or record.get("identity") != binding):
                raise ValueError("operation identity changed or receipt malformed")
            if record.get("status") != "completed":
                raise RuntimeError("operation delivery unknown; explicit reconciliation required")
            if (set(record) != {"schema", "identity", "status", "result", "result_digest"}
                    or record["result_digest"] != digest(record["result"])):
                raise ValueError("completed receipt is malformed")
            return record["result"]
        atomic_json(path, {"schema": "dwl-operation/v1", "identity": binding, "status": "started"})
        result = execute()
        atomic_json(path, {"schema": "dwl-operation/v1", "identity": binding, "status": "completed",
                           "result": result, "result_digest": digest(result)})
        return result


def input_identity(adapter, persona, brief: str, config: dict) -> dict:
    persona_data = persona.to_dict()
    persona_data.pop("compiled_at", None)  # Timestamp is not semantic corpus identity.
    return {"source": source_digest(), "adapter": adapter.identity(), "persona": persona_data,
            "brief": brief, "config": config,
            "budget": {"max_calls": adapter.budget.max_calls,
                       "max_microusd": adapter.budget.max_microusd}}


def completed_result(path: Path) -> dict:
    record = read_json(path)
    if (type(record) is not dict or set(record) != {"schema", "identity", "status", "result", "result_digest"}
            or record["schema"] != "dwl-operation/v1" or record["status"] != "completed"
            or type(record["result"]) is not dict or record["result_digest"] != digest(record["result"])):
        raise ValueError("invalid completed operation")
    return record["result"]
