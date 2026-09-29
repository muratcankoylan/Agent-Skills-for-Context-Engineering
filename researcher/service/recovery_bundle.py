"""Bounded private offline recovery bundles. Restoring never activates a service.

This is a closed state-tree format, not an archive extractor. File digests detect
corruption, not a malicious operator who can rewrite the manifest. Keep bundles
on encrypted private storage and retain the returned manifest digest separately.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping
import contextlib
import functools
import json
import os
from pathlib import Path, PurePosixPath
import re
import sqlite3
import stat
import time

from researcher.scripts.artifact_store import _atomic_write_bytes, _fsync_directory
from researcher.scripts.research_evidence import (
    CapturedEvidence, LocalResearchEvidenceStore, ResearchEvidenceError, _decode_observation,
)
from researcher.scripts.schema_contract import canonicalize, parse_json_strict, sha256_bytes
from .agents_runtime import PHASES, SessionLedger, _validate_packet
from .contracts import ServiceError, digest, load_config
from .environment import _stable_bytes, read_config_file
from .store import SCHEMA, Store
from .workflow import git_head, implementation

SCHEMA_VERSION = "research-recovery-bundle/v1"
MAX_BYTES = 256 * 1024 * 1024
MAX_FILES = 10000
MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_MANIFEST_BYTES = 8 * 1024 * 1024
HEX = r"[0-9a-f]{64}"
NAME = re.compile(r"[a-z][a-z0-9_-]{0,63}\Z")
DIGEST = re.compile(r"sha256:" + HEX + r"\Z")


def _error(code="INVALID"):
    return ServiceError("RECOVERY_" + code)


def _sanitized(function):
    @functools.wraps(function)
    def call(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except ServiceError:
            raise
        except (OSError, ValueError, TypeError, KeyError, AttributeError, RecursionError,
                sqlite3.Error, ResearchEvidenceError):
            raise _error("INVALID") from None
    return call


def _limits(max_bytes, max_files):
    if (type(max_bytes) is not int or not 1 <= max_bytes <= MAX_BYTES
            or type(max_files) is not int or not 1 <= max_files <= MAX_FILES):
        raise _error("LIMIT_INVALID")


def _directory(path, *, private=True):
    path = Path(path).absolute()
    if ".." in path.parts or path.resolve() != path:
        raise _error("PATH_UNSAFE")
    for parent in (*reversed(path.parents), path):
        info = parent.lstat()
        # A root-owned sticky /tmp ancestor is permitted, never a writable
        # non-sticky ancestor controlled by another account.
        if (not stat.S_ISDIR(info.st_mode) or info.st_uid not in {0, os.getuid()}
                or (info.st_mode & 0o022 and not info.st_mode & stat.S_ISVTX)):
            raise _error("PATH_UNSAFE")
    info = path.stat()
    if private and (info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700):
        raise _error("PATH_UNSAFE")
    return path


def _new_directory(path):
    path = Path(path).absolute()
    _directory(path.parent)
    if path.exists() or path.is_symlink():
        raise _error("DESTINATION_EXISTS")
    try:
        path.mkdir(mode=0o700)
    except FileExistsError:
        raise _error("DESTINATION_EXISTS") from None
    _fsync_directory(path.parent)
    return path


def _read(path, maximum=MAX_FILE_BYTES):
    return _stable_bytes(path, maximum=maximum, private=True, prefix="RECOVERY")


def _relative(value):
    if (not isinstance(value, str) or not value or len(value) > 512
            or "\\" in value or any(ord(c) < 32 for c in value)):
        raise _error("PATH_UNSAFE")
    path = PurePosixPath(value)
    if path.is_absolute() or path.as_posix() != value or any(p in {".", ".."} for p in path.parts):
        raise _error("PATH_UNSAFE")
    return value


def _state_path(value, directory):
    """Closed on-disk service namespace; no env, keys, git or arbitrary files."""
    if value == "":
        return directory
    if directory:
        return bool(re.fullmatch(
            r"(?:evidence|primary-evidence)(?:/(?:bodies|observations))?"
            r"|candidate-cas(?:/(?:sha256(?:/[0-9a-f]{2})?|metadata|locks|freeze-receipts))?"
            r"|candidate-[0-9a-f]{16}(?:/skills(?:/[a-z][a-z0-9_-]{0,63})?)?", value))
    return bool(re.fullmatch(
        r"service\.sqlite3(?:-wal|-shm)?|worker\.lock"
        rf"|(?:evidence|primary-evidence)/(?:\.lock|(?:bodies|observations)/{HEX})"
        rf"|candidate-cas/(?:sha256/[0-9a-f]{{2}}/{HEX}|(?:metadata|freeze-receipts)/{HEX}\.json|locks/{HEX}\.lock)"
        r"|candidate-[0-9a-f]{16}/skills/[a-z][a-z0-9_-]{0,63}/SKILL\.md", value))


def _session_path(value, directory):
    return value == "" if directory else value in {"packet.json", "session.json", "result.json", "session.lock"}


def _configuration(config):
    if config.get("schema") == "openai-budget-authority/v1":
        from .openai_campaign import configuration
        expected = configuration(config.get("cap_microusd"), config.get("prior_spend_microusd"))
    else:
        expected = load_config(canonicalize(config).decode())
    if config != expected:
        raise _error("CONFIG_MISMATCH")
    return expected


def _policy(config):
    if config.get("schema") == "openai-budget-authority/v1":
        return lambda value, directory: value == "" if directory else value in {
            "authority.json", "service.sqlite3", "service.sqlite3-wal", "service.sqlite3-shm", "worker.lock"}
    return _state_path


def _ignored(value):
    return (value in {"worker.lock", "session.lock", "service.sqlite3-wal", "service.sqlite3-shm"}
            or value.endswith("/.lock") or value.startswith("candidate-cas/locks/"))


def _entries(path, maximum):
    entries = []
    with os.scandir(path) as iterator:
        for entry in iterator:
            if len(entries) >= maximum:
                raise _error("FILE_LIMIT")
            entries.append(path / entry.name)
    return sorted(entries)


def _tree(root, policy, *, max_bytes, max_files):
    _directory(root)
    files, directories, total, visited = {}, [], 0, 0

    def visit(path, relative):
        nonlocal total, visited
        # Existing candidate drafts have 0755 intermediate directories inside
        # the private0700 state root; no outside account can traverse that root.
        _directory(path, private=not relative)
        if path.stat().st_uid != os.getuid():
            raise _error("PATH_UNSAFE")
        before = path.stat()
        directories.append(relative)
        if len(directories) > max_files * 4 + 32:
            raise _error("FILE_LIMIT")
        for entry in _entries(path, max_files * 5 + 128):
            visited += 1
            if visited > max_files * 5 + 128:
                raise _error("FILE_LIMIT")
            name = entry.relative_to(root).as_posix()
            info = entry.lstat()
            is_directory = stat.S_ISDIR(info.st_mode)
            # Traces are private diagnostics, not execution or budget authority.
            # Explicitly exclude only this reserved top-level directory; never
            # loosen the accepted-state policy for any other unexpected file.
            if name == "telemetry":
                _directory(entry)
                if info.st_uid != os.getuid():
                    raise _error("PATH_UNSAFE")
                continue
            if not policy(name, is_directory):
                raise _error("UNEXPECTED_FILE")
            if is_directory:
                visit(entry, name)
                continue
            if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.getuid()
                    or stat.S_IMODE(info.st_mode) != 0o600):
                raise _error("PATH_UNSAFE")
            if name == "service.sqlite3":
                continue  # Only SQLite backup may read this mutable file.
            if _ignored(name):
                if not name.startswith("service.sqlite3-") and info.st_size:
                    raise _error("LOCK_INVALID")
                continue
            body = _read(entry)
            total += len(body)
            if total > max_bytes or len(files) >= max_files:
                raise _error("SIZE_LIMIT" if total > max_bytes else "FILE_LIMIT")
            files[name] = body
        after = path.stat()
        if (before.st_dev, before.st_ino, before.st_mtime_ns) != (after.st_dev, after.st_ino, after.st_mtime_ns):
            raise _error("TREE_CHANGED")

    visit(root, "")
    return files, directories


def _decode(body):
    try:
        return parse_json_strict(body.decode("utf-8"))
    except (ValueError, UnicodeError, RecursionError):
        raise _error("JSON_INVALID") from None


def _source(root):
    return {"implementation_digest": implementation(root), "baseline_commit": git_head(root)}


def _backup(store, target, maximum):
    store._safe_paths()
    descriptor = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    os.close(descriptor)
    with contextlib.closing(sqlite3.connect(store.path.as_uri() + "?mode=ro", uri=True)) as source, \
            contextlib.closing(sqlite3.connect(target)) as destination:
        deadline = time.monotonic() + 30
        page_size = source.execute("PRAGMA page_size").fetchone()[0]
        def progress(_status, _remaining, total):
            if time.monotonic() > deadline:
                raise _error("BACKUP_DEADLINE")
            if total * page_size > min(MAX_FILE_BYTES, maximum):
                raise _error("SIZE_LIMIT")
        source.backup(destination, pages=128, progress=progress, sleep=0.05)
        destination.execute("PRAGMA journal_mode=DELETE")


def _sdk_job(db, job, manifest, config):
    """Validate the v1 single-request SDK graph without executing or resuming it.

    Version constants describe retained records, not whatever SDK happens to be
    installed during restore. Missing terminal records are valid crash states;
    they remain missing and must not acquire replay authority during recovery.
    """
    def require(condition):
        if not condition:
            raise _error("SDK_RECORD_INVALID")

    def exact(value, keys):
        return type(value) is dict and set(value) == set(keys)

    def integer(value, lower=0, upper=2**63 - 1):
        return type(value) is int and lower <= value <= upper

    def identifier(value):
        return isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value)

    def hashed(value):
        return isinstance(value, str) and DIGEST.fullmatch(value)

    def cost(inputs, outputs):
        pricing = config["pricing"]
        return (inputs * pricing["input_microusd_per_million"]
                + outputs * pricing["output_microusd_per_million"] + 999999) // 1000000

    require(exact(manifest, ("schema", "campaign", "item", "task"))
            and manifest["schema"] == "codex-sdk-work/v1")
    require(all(isinstance(manifest[key], str) and re.fullmatch(r"[A-Za-z0-9_.:-]{1,160}", manifest[key])
                for key in ("campaign", "item")))
    require(job == "codex-" + digest([manifest["campaign"], manifest["item"]])[7:])
    task = manifest["task"]
    require(exact(task, ("schema", "backend", "model", "sandbox", "reasoning_effort", "prompt",
                         "max_output_tokens", "sdk_version", "policy", "implementation_digest",
                         "binding", "fixture", "pricing", "config_identity", "worker_request_digest")))
    require(task["schema"] == "codex-sdk-task/v1" and task["backend"] == "codex_sdk"
            and task["sdk_version"] == "0.159.0" and task["policy"] == "codex-tool-free-buffered-v1"
            and task["model"] == config["pricing"]["model"] and task["sandbox"] == "read_only"
            and task["reasoning_effort"] in {"none", "low", "medium", "high"}
            and integer(task["max_output_tokens"], 256, 8192)
            and type(task["fixture"]) is bool and hashed(task["implementation_digest"])
            and isinstance(task["config_identity"], str) and re.fullmatch(HEX, task["config_identity"])
            and task["worker_request_digest"] == digest({key: task[key]
                for key in ("model", "sandbox", "reasoning_effort", "prompt")})
            and canonicalize(task["pricing"]) == canonicalize(config["pricing"])
            and isinstance(task["prompt"], str) and task["prompt"].strip()
            and "\x00" not in task["prompt"] and len(canonicalize(task)) <= 131072)
    task_digest = digest(task)
    status = db.execute("SELECT status FROM jobs WHERE id=?", (job,)).fetchone()[0]
    require(status in {"queued", "running", "reconciliation_required", "execution_complete"})
    steps = {}
    for name, input_digest, raw, output_digest in db.execute(
            "SELECT name,input_digest,output,output_digest FROM steps WHERE job=?", (job,)):
        require(name in {"sdk-started", "sdk-thread_started", "sdk-turn_started", "sdk-result"}
                and input_digest == task_digest)
        value = _decode(raw.encode())
        require(type(value) is dict and digest(value) == output_digest)
        steps[name] = value
    started = steps.get("sdk-started")
    thread = steps.get("sdk-thread_started")
    turn = steps.get("sdk-turn_started")
    result = steps.get("sdk-result")
    if started is not None:
        require(exact(started, ("schema", "task_digest", "sdk_version"))
                and started == {"schema": "codex-sdk-started/v1", "task_digest": task_digest,
                                "sdk_version": "0.159.0"})
    if thread is not None:
        require(started is not None and exact(thread, ("type", "thread_id"))
                and thread["type"] == "thread_started" and identifier(thread["thread_id"]))
    if turn is not None:
        require(thread is not None and exact(turn, ("type", "thread_id", "turn_id"))
                and turn["type"] == "turn_started" and turn["thread_id"] == thread["thread_id"]
                and identifier(turn["turn_id"]))
    effects = list(db.execute("SELECT name,input_digest,state,model_calls,source_requests,reserved_microusd,"
                              "output,output_digest FROM effects WHERE job=?", (job,)))
    require(len(effects) <= 1)
    provider = None
    if effects:
        name, input_digest, state, model_calls, source_requests, reserved, raw, output_digest = effects[0]
        # The model request can race ahead of turn/start's returned ID. The
        # earlier thread-start observer is synchronous, so it must be retained.
        require(started is not None and thread is not None and name == "sdk-response"
                and state in {"started", "unknown", "completed"}
                and integer(model_calls, 1, 1) and integer(source_requests, 0, 0)
                and integer(reserved, cost(4096, task["max_output_tokens"]),
                            cost(131072 + 4096, task["max_output_tokens"])) and hashed(input_digest))
        if state == "completed":
            provider = _decode(raw.encode())
            require(digest(provider) == output_digest
                    and exact(provider, ("schema", "backend", "policy", "response", "task_digest",
                                         "wire_digest", "input_token_ceiling", "usage", "latency_ms",
                                         "reserved_microusd")))
            require(provider["schema"] in {"codex-gateway-receipt/v1", "codex-gateway-receipt/v2"}
                    and provider["backend"] == "codex_sdk" and provider["policy"] == task["policy"]
                    and provider["task_digest"] == task_digest and hashed(provider["wire_digest"])
                    and integer(provider["input_token_ceiling"], 4096, 131072 + 4096)
                    and integer(provider["latency_ms"])
                    and type(provider["reserved_microusd"]) is int
                    and provider["reserved_microusd"] == reserved
                    and reserved == cost(provider["input_token_ceiling"], task["max_output_tokens"]))
            response, usage = provider["response"], provider["usage"]
            response_keys = ("text", "input_tokens", "output_tokens", "model", "request_id", "service_tier")
            if provider["schema"] == "codex-gateway-receipt/v2":
                response_keys += ("token_details",)
            require(exact(response, response_keys)
                    and isinstance(response["text"], str) and response["text"].strip()
                    and len(response["text"].encode("utf-8")) <= 131072
                    and response["model"] == task["model"] and response["service_tier"] == "default"
                    and isinstance(response["request_id"], str)
                    and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,199}", response["request_id"])
                    and integer(response["input_tokens"], 0, provider["input_token_ceiling"])
                    and integer(response["output_tokens"], 0, task["max_output_tokens"]))
            if provider["schema"] == "codex-gateway-receipt/v2":
                # Retained v1 receipts predate observed details. Never infer
                # their cache/reasoning counters from SDK-normalized zeroes.
                details = response["token_details"]
                require(exact(details, ("cached_input_tokens", "cache_write_input_tokens", "reasoning_output_tokens"))
                        and all(value is None or integer(value, 0, response[
                            "output_tokens" if key == "reasoning_output_tokens" else "input_tokens"])
                            for key, value in details.items()))
            require(exact(usage, ("input_tokens", "output_tokens", "estimated_upper_cost_microusd"))
                    and all(integer(value) for value in usage.values())
                    and usage == {"input_tokens": response["input_tokens"], "output_tokens": response["output_tokens"],
                                  "estimated_upper_cost_microusd": cost(response["input_tokens"], response["output_tokens"])})
            require(input_digest == digest({"schema": "codex-gateway-request/v1", "task_digest": task_digest,
                                            "wire_digest": provider["wire_digest"], "policy": task["policy"]}))
        else:
            require(raw is None and output_digest is None and result is None)
    if result is not None:
        require(provider is not None and turn is not None
                and exact(result, (*provider.keys(), "sdk", "output_digest")))
        require(result["schema"] == "codex-sdk-response/" + provider["schema"].rsplit("/", 1)[1]
                and integer(result["latency_ms"])
                and exact(result["sdk"], ("version", "thread_id", "turn_id"))
                and result["sdk"] == {"version": "0.159.0", "thread_id": thread["thread_id"], "turn_id": turn["turn_id"]}
                and result["output_digest"] == digest(provider["response"]["text"]))
        require(all(canonicalize(result[key]) == canonicalize(value)
                    for key, value in provider.items() if key not in {"schema", "latency_ms"}))
    require(status != "execution_complete" or result is not None)


def _database(body, config, *, paused=False):
    """Read the exact known schema without triggers or application execution."""
    expected = sqlite3.connect(":memory:")
    expected.executescript(SCHEMA)
    schema = expected.execute("SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name").fetchall()
    expected.close()
    try:
        with contextlib.closing(sqlite3.connect(":memory:")) as db:
            db.deserialize(body)
            db.execute("PRAGMA trusted_schema=OFF")
            if (db.execute("SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name").fetchall() != schema
                    or db.execute("PRAGMA integrity_check").fetchone() != ("ok",)
                    or db.execute("PRAGMA foreign_key_check").fetchall()):
                raise _error("DATABASE_INVALID")
            meta = dict(db.execute("SELECT key,value FROM meta"))
            if (meta.get("schema") != "research-service-store/v1" or meta.get("config_digest") != digest(config)
                    or meta.get("paused") not in {"true", "false"}):
                raise _error("CONFIG_MISMATCH")
            jobs, values = [], []
            for job, raw, expected_digest in db.execute("SELECT id,manifest,digest FROM jobs ORDER BY id"):
                manifest = _decode(raw.encode())
                if config.get("schema") == "openai-budget-authority/v1":
                    if isinstance(manifest, dict) and manifest.get("schema") == "codex-sdk-work/v1":
                        _sdk_job(db, job, manifest, config)
                        valid = True
                    else:
                        valid = (set(manifest) == {"schema", "campaign", "item", "inputs", "input_token_ceiling", "reservation_microusd"}
                                 and manifest["schema"] == "openai-bounded-work/v1"
                                 and manifest["inputs"]["pricing"] == config["pricing"])
                else:
                    valid = (manifest.get("config_digest") == digest(config)
                             and manifest.get("schema") in {"research-work/v1", "retrieval-work/v1"})
                if digest(manifest) != expected_digest or not valid:
                    raise _error("JOB_MANIFEST_INVALID")
                jobs.append({"id": job, "manifest_digest": expected_digest})
                values.append(manifest)
            for raw, expected_digest in db.execute("SELECT output,output_digest FROM steps"):
                value = _decode(raw.encode())
                if digest(value) != expected_digest:
                    raise _error("CHECKPOINT_INVALID")
                values.append(value)
            for state, raw, expected_digest, model, requests, cost in db.execute(
                    "SELECT state,output,output_digest,model_calls,source_requests,reserved_microusd FROM effects"):
                if state not in {"started", "unknown", "failed", "completed"} or min(model, requests, cost) < 0:
                    raise _error("EFFECT_INVALID")
                if state == "completed":
                    value = _decode(raw.encode())
                    if digest(value) != expected_digest:
                        raise _error("EFFECT_INVALID")
                    values.append(value)
                elif raw is not None or expected_digest is not None:
                    raise _error("EFFECT_INVALID")
            if paused:
                db.execute("UPDATE meta SET value='true' WHERE key='paused'")
                db.commit()
            return jobs, values, db.serialize() if paused else body
    except (sqlite3.Error, TypeError, AttributeError):
        raise _error("DATABASE_INVALID") from None


def _closure(files, values):
    """Check captured and frozen content relations, including interrupted blobs."""
    captures = set()
    for prefix in ("state/evidence", "state/primary-evidence"):
        for name, body in files.items():
            if name.startswith(prefix + "/bodies/") or name.startswith(prefix + "/observations/"):
                if sha256_bytes(body)[7:] != name.rsplit("/", 1)[1]:
                    raise _error("CONTENT_HASH_MISMATCH")
            if name.startswith(prefix + "/observations/"):
                observation = _decode_observation(body)
                payload = files.get(prefix + "/bodies/" + observation.response_sha256[7:])
                if payload is None or len(payload) != observation.response_bytes:
                    raise _error("CAPTURE_MISSING")
                captures.add((observation.response_sha256, sha256_bytes(body), len(payload)))
    for name, body in files.items():
        if name.startswith("state/candidate-cas/sha256/"):
            hexadecimal = sha256_bytes(body)[7:]
            if name != f"state/candidate-cas/sha256/{hexadecimal[:2]}/{hexadecimal}":
                raise _error("CONTENT_HASH_MISMATCH")
            if f"state/candidate-cas/metadata/{hexadecimal}.json" not in files:
                raise _error("CAS_METADATA_MISSING")
        elif name.startswith("state/candidate-cas/metadata/"):
            value = _decode(body)
            if (set(value) != {"schema_version", "digest", "classification", "size_bytes"}
                    or value["digest"] != "sha256:" + Path(name).stem):
                raise _error("CAS_METADATA_INVALID")
            hexadecimal = value["digest"][7:]
            payload = files.get(f"state/candidate-cas/sha256/{hexadecimal[:2]}/{hexadecimal}")
            if payload is None or len(payload) != value["size_bytes"]:
                raise _error("CAS_CONTENT_MISSING")
        elif name.startswith("state/candidate-cas/freeze-receipts/"):
            value = _decode(body)
            if (value.get("kind") != "FreezeReceipt" or sha256_bytes(value["candidate_id"].encode())[7:] != Path(name).stem):
                raise _error("FREEZE_RECEIPT_INVALID")
            for entry in value["entries"]:
                hexadecimal = entry["digest"][7:]
                payload = files.get(f"state/candidate-cas/sha256/{hexadecimal[:2]}/{hexadecimal}")
                if payload is None or len(payload) != entry["size_bytes"]:
                    raise _error("CAS_CONTENT_MISSING")

    def visit(value):
        if isinstance(value, dict):
            if {"body_sha256", "metadata_sha256", "size_bytes"} <= set(value):
                record = CapturedEvidence.from_record(value)
                if (record.body_sha256, record.metadata_sha256, record.size_bytes) not in captures:
                    raise _error("CAPTURE_MISSING")
            if value.get("kind") == "FreezeReceipt":
                key = sha256_bytes(value["candidate_id"].encode())[7:]
                raw = files.get(f"state/candidate-cas/freeze-receipts/{key}.json")
                if raw is None or _decode(raw) != value:
                    raise _error("FREEZE_RECEIPT_MISSING")
            for item in value.values():
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)
    for value in values:
        visit(value)


def _session_records(files, name, jobs, values):
    prefix = f"sessions/{name}/"
    packet = _decode(files[prefix + "packet.json"])
    envelope = _decode(files[prefix + "session.json"])
    _validate_packet(packet)
    if (set(envelope) != {"record", "digest"} or digest(envelope["record"]) != envelope["digest"]):
        raise _error("SESSION_MANIFEST_INVALID")
    state = envelope["record"]
    if (state.get("manifest_digest") != digest(packet) or state.get("schema") != "managed-session-state/v1"
            or state.get("phase") not in PHASES or type(state.get("revision")) is not int
            or type(state.get("last_clock")) is not int):
        raise _error("SESSION_MANIFEST_INVALID")
    if state["phase"] == "completed" and digest(_decode(files[prefix + "result.json"])) != state.get("result_digest"):
        raise _error("SESSION_MANIFEST_INVALID")
    context = packet.get("retrieval_context")
    if context is not None:
        matching = [item for item in jobs if digest(item["id"]) == context["job_digest"]
                    and item["manifest_digest"] == context["manifest_digest"]]
        if (len(matching) != 1 or not any(
                value.get("schema") == "research-retrieval-report/v1"
                and value.get("job") == matching[0]["id"] and digest(value) == context["report_digest"]
                for value in values if isinstance(value, dict))):
            raise _error("SESSION_SOURCE_MISSING")
    return {"name": name, "manifest_digest": digest(packet), "phase": state["phase"]}


@_sanitized
def snapshot(store: Store, target: Path, *, root: Path,
             sessions: Mapping[str, SessionLedger] | None = None,
             max_bytes: int = MAX_BYTES, max_files: int = MAX_FILES) -> dict:
    """Create a new private bundle. Caller must stop admission and all writers.

    Worker/session/capture locks also fail closed if a cooperating writer runs.
    Only explicitly supplied managed ledgers are in scope; remote work is not
    stopped by a local snapshot. Unknown effects remain unknown.
    """
    _limits(max_bytes, max_files)
    sessions = {} if sessions is None else sessions
    if (not isinstance(sessions, Mapping) or len(sessions) > 32
            or any(not isinstance(key, str) or not NAME.fullmatch(key) or not isinstance(value, SessionLedger)
                   for key, value in sessions.items())):
        raise _error("SESSIONS_INVALID")
    config = _configuration(store.config)
    policy = _policy(config)
    if config["schema"] == "openai-budget-authority/v1" and sessions:
        raise _error("SESSIONS_INVALID")
    target = Path(target).absolute()
    if any(target == directory or directory in target.parents
           for directory in [store.directory, *(ledger.directory for ledger in sessions.values())]):
        raise _error("DESTINATION_INVALID")
    with contextlib.ExitStack() as locks:
        locks.enter_context(store.worker_lock())
        for _, ledger in sorted(sessions.items()):
            locks.enter_context(ledger.lock())
        for name in (() if config["schema"] == "openai-budget-authority/v1" else ("evidence", "primary-evidence")):
            directory = store.directory / name
            if directory.exists() or directory.is_symlink():
                _directory(directory)
                locks.enter_context(LocalResearchEvidenceStore(directory, read_only=True)._locked(write=False))
        files, directories = _tree(store.directory, policy, max_bytes=max_bytes, max_files=max_files)
        if config["schema"] == "openai-budget-authority/v1" and _decode(files["authority.json"]) != config:
            raise _error("CONFIG_MISMATCH")
        # The live WAL database bytes are deliberately discarded. Only SQLite's
        # consistent backup is used, not a filesystem copy of active pages.
        target = _new_directory(target)
        database = target / "database.snapshot"
        if len(files) >= max_files:
            raise _error("FILE_LIMIT")
        _backup(store, database, max_bytes - sum(map(len, files.values())))
        # A standalone DELETE-mode image can be inspected/deserialized without
        # ever consulting sidecars belonging to the source database.
        files["service.sqlite3"] = _read(database)
        jobs, values, _ = _database(files["service.sqlite3"], config)
        database.unlink()
        _fsync_directory(target)
        files = {"state/" + name: body for name, body in files.items()}
        directories = ["state" + ("/" + name if name else "") for name in directories]
        session_manifests = []
        for name, ledger in sorted(sessions.items()):
            packet, state = ledger.load()
            content, _ = _tree(ledger.directory, _session_path,
                               max_bytes=max_bytes - sum(map(len, files.values())),
                               max_files=max_files - len(files))
            files.update({f"sessions/{name}/{path}": body for path, body in content.items()})
            directories.extend(["sessions", "sessions/" + name])
            item = _session_records(files, name, jobs, values)
            if item != {"name": name, "manifest_digest": digest(packet), "phase": state["phase"]}:
                raise _error("SESSION_CHANGED")
            session_manifests.append(item)
        if len(files) > max_files or sum(map(len, files.values())) > max_bytes:
            raise _error("SIZE_LIMIT")
        _closure(files, values)
        source = _source(root)
        record = {"schema": SCHEMA_VERSION, "authority": "none", "activation": False,
                  "source": source, "config_digest": digest(config), "jobs": jobs,
                  "sessions": session_manifests, "created_at": int(time.time()),
                  "directories": sorted(set(directories)),
                  "files": [{"path": path, "sha256": sha256_bytes(body), "size_bytes": len(body)}
                            for path, body in sorted(files.items())],
                  "total_bytes": sum(map(len, files.values()))}
        if len(canonicalize(record)) > MAX_MANIFEST_BYTES:
            raise _error("MANIFEST_LIMIT")
        blobs = target / "blobs"
        blobs.mkdir(mode=0o700)
        for body in files.values():
            path = blobs / sha256_bytes(body)[7:]
            if not path.exists():
                _atomic_write_bytes(path, body, no_clobber=True)
        _atomic_write_bytes(target / "manifest.json", canonicalize(record), no_clobber=True)
        _fsync_directory(target)
        return {"manifest_digest": digest(record), "file_count": len(files), "total_bytes": record["total_bytes"],
                "activation": False, "encrypted": False}


def _bundle(bundle, *, max_bytes, max_files, expected_digest, policy):
    bundle = _directory(bundle)
    if [path.name for path in _entries(bundle, 3)] != ["blobs", "manifest.json"]:
        raise _error("BUNDLE_INCOMPLETE")
    record = _decode(_read(bundle / "manifest.json", MAX_MANIFEST_BYTES))
    if (not isinstance(record, dict) or set(record) != {"schema", "authority", "activation", "source", "config_digest",
            "jobs", "sessions", "created_at", "directories", "files", "total_bytes"}
            or record["schema"] != SCHEMA_VERSION or record["authority"] != "none" or record["activation"] is not False
            or not isinstance(expected_digest, str) or not DIGEST.fullmatch(expected_digest)
            or digest(record) != expected_digest):
        raise _error("MANIFEST_MISMATCH")
    rows = record["files"]
    if not isinstance(rows, list) or not rows or len(rows) > max_files:
        raise _error("FILE_LIMIT")
    session_names = [item["name"] for item in record["sessions"]]
    if (len(session_names) > 32 or len(set(session_names)) != len(session_names)
            or any(not NAME.fullmatch(name) for name in session_names)):
        raise _error("SESSIONS_INVALID")

    def allowed(path, directory):
        _relative(path)
        if path == "sessions":
            return directory and bool(session_names)
        if path == "state":
            return directory
        if path.startswith("state/"):
            return policy(path[6:], directory) and not _ignored(path[6:])
        parts = path.split("/", 2)
        if len(parts) >= 2 and parts[0] == "sessions" and parts[1] in session_names:
            return _session_path(parts[2] if len(parts) == 3 else "", directory) and not path.endswith("/session.lock")
        return False

    directories = record["directories"]
    if (not isinstance(directories, list) or directories != sorted(set(directories))
            or len(directories) > max_files * 4 + 32 or any(not allowed(path, True) for path in directories)):
        raise _error("PATH_UNSAFE")
    if any(PurePosixPath(path).parent.as_posix() not in {".", *directories} for path in directories):
        raise _error("DIRECTORY_MISSING")
    files, total = {}, 0
    _directory(bundle / "blobs")
    for row in rows:
        if (type(row) is not dict or set(row) != {"path", "sha256", "size_bytes"}
                or not allowed(row["path"], False) or row["path"] in files
                or not isinstance(row["sha256"], str) or not DIGEST.fullmatch(row["sha256"])
                or type(row["size_bytes"]) is not int or not 0 <= row["size_bytes"] <= MAX_FILE_BYTES):
            raise _error("FILE_INVALID")
        total += row["size_bytes"]
        if total > max_bytes:
            raise _error("SIZE_LIMIT")
        body = _read(bundle / "blobs" / row["sha256"][7:])
        if sha256_bytes(body) != row["sha256"] or len(body) != row["size_bytes"]:
            raise _error("CONTENT_HASH_MISMATCH")
        parent = PurePosixPath(row["path"]).parent
        if parent.as_posix() not in directories:
            raise _error("DIRECTORY_MISSING")
        files[row["path"]] = body
    if (total != record["total_bytes"] or "state/service.sqlite3" not in files
            or [path.name for path in _entries(bundle / "blobs", max_files)] != sorted({row["sha256"][7:] for row in rows})):
        raise _error("BUNDLE_INCOMPLETE")
    return record, files


@_sanitized
def restore(bundle: Path, target: Path, *, root: Path, config: dict, expected_digest: str,
            max_bytes: int = MAX_BYTES, max_files: int = MAX_FILES) -> dict:
    """Verify an offline bundle and restore a fresh, explicitly paused state.

    The trusted manifest digest must come from the snapshot result, separately
    retained from the bundle. No credentials, worker activation or remote
    reconciliation are performed. All reservations and session phases survive.
    """
    _limits(max_bytes, max_files)
    _configuration(config)
    record, files = _bundle(bundle, max_bytes=max_bytes, max_files=max_files,
                            expected_digest=expected_digest, policy=_policy(config))
    if record["source"] != _source(root) or record["config_digest"] != digest(config):
        raise _error("SOURCE_CONFIG_MISMATCH")
    if config["schema"] == "openai-budget-authority/v1" and (
            record["sessions"] or _decode(files["state/authority.json"]) != config):
        raise _error("CONFIG_MISMATCH")
    jobs, values, paused_database = _database(files["state/service.sqlite3"], config, paused=True)
    if jobs != record["jobs"]:
        raise _error("JOB_MANIFEST_INVALID")
    _closure(files, values)
    if [_session_records(files, item["name"], jobs, values) for item in record["sessions"]] != record["sessions"]:
        raise _error("SESSION_MANIFEST_INVALID")
    target = _new_directory(target)
    for name in record["directories"]:
        (target / name).mkdir(mode=0o700, parents=False)
    for name, body in files.items():
        _atomic_write_bytes(target / name,
                            paused_database if name == "state/service.sqlite3" else body, no_clobber=True)
    for name in ("evidence", "primary-evidence"):
        if (target / "state" / name).is_dir():
            _atomic_write_bytes(target / "state" / name / ".lock", b"", no_clobber=True)
    database = target / "state/service.sqlite3"
    # This deliberate local mutation is the only change to restored state.
    # Never recover/clear started or unknown effects during restore itself.
    receipt = {"schema": "research-recovery-restore/v1", "bundle_manifest_digest": expected_digest,
               "source_database_sha256": sha256_bytes(files["state/service.sqlite3"]),
               "restored_database_sha256": sha256_bytes(_read(database)),
               "source": record["source"], "config_digest": record["config_digest"],
               "activation": False, "paused": True, "reconciliation_performed": False,
               "file_count": len(files), "total_bytes": record["total_bytes"], "sessions": record["sessions"]}
    _atomic_write_bytes(target / "restore.json", canonicalize(receipt), no_clobber=True)
    _fsync_directory(target / "state")
    _fsync_directory(target)
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description="Offline private recovery; never activates workers")
    parser.add_argument("command", choices=("snapshot", "restore"))
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--state", type=Path)
    parser.add_argument("--session", action="append", default=[], metavar="NAME=PATH")
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--manifest-digest")
    args = parser.parse_args(argv)
    try:
        config = _configuration(_decode(read_config_file(args.config).encode()))
        if args.command == "snapshot":
            if args.state is None or args.bundle is not None or args.manifest_digest is not None:
                raise _error("ARGUMENT_INVALID")
            sessions = {}
            for value in args.session:
                name, separator, path = value.partition("=")
                if not separator or name in sessions:
                    raise _error("ARGUMENT_INVALID")
                sessions[name] = SessionLedger(Path(path))
            result = snapshot(Store(args.state, config), args.destination, root=args.root, sessions=sessions)
        else:
            if args.bundle is None or args.manifest_digest is None or args.state is not None or args.session:
                raise _error("ARGUMENT_INVALID")
            result = restore(args.bundle, args.destination, root=args.root, config=config,
                             expected_digest=args.manifest_digest)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (ServiceError, OSError, ValueError, TypeError, KeyError):
        print(json.dumps({"error": "RECOVERY_FAILED", "activation": False}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
