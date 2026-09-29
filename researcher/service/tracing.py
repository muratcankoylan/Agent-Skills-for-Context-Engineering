"""Private, bounded operation traces. Never a budget or execution authority.

Only registered operation names and typed metadata enter this journal. Prompts,
tool arguments/results, headers, URLs, exception text and credentials do not.
Export is an explicit separate operation; instrumentation performs no network I/O.
"""
from __future__ import annotations

import asyncio
import contextlib
from contextvars import ContextVar
from dataclasses import dataclass
import fcntl
from functools import wraps
import hashlib
import hmac
import inspect
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import stat
import sys
import threading
import time

from .contracts import ServiceError
from researcher.scripts.schema_contract import parse_json_strict

TOOLS = {
    "workflow.execute": ("workflow", False), "workflow.retrieve": ("workflow", False),
    "workflow.effect": ("tool", True), "model.call": ("generation", True),
    "agent.research": ("agent", False), "agent.evaluate": ("agent", False),
    "managed.submit": ("agent", True), "managed.watch": ("agent", False),
    "managed.observe": ("agent", True), "managed.cancel": ("agent", True),
    "managed.http": ("connection", True), "source.retrieve": ("tool", True),
    "source.primary": ("tool", True), "source.verify": ("validation", False),
    "mcp.read": ("tool", True), "mcp.initialize": ("connection", True),
    "mcp.list": ("connection", True), "mcp.invoke": ("tool", True),
    "repository.publish": ("tool", True), "pipeline.run": ("workflow", False),
    "pipeline.phase": ("validation", False), "candidate.review": ("validation", False),
    "organization.cycle": ("workflow", False), "connector.check": ("connection", True),
    "managed.generation": ("generation", True), "managed.tool": ("tool", True),
    "managed.agent": ("agent", False),
    "sdk.turn": ("agent", True), "sdk.tool": ("tool", True),
    "agent.action": ("tool", False),
}
ENUMS = {
    "provider": {"openai", "anthropic", "gemini", "arxiv", "hacker_news", "x", "openalex",
                 "deepmind", "huggingface", "microsoft_research", "parallel", "firecrawl", "github", "mcp", "internal"},
    "transport": {"https", "mcp", "subprocess", "injected", "local"},
    "role": {"researcher", "critic", "editor", "judge", "skill_editor", "evaluator", "control", "candidate", "unknown"},
    "outcome": {"completed", "replayed", "rejected", "unknown", "abstained", "failed", "cancelled", "prepared"},
    "error.type": {"ServiceError", "ProviderError", "AgentsError", "MCPToolError", "MCPEvidenceError",
                   "TimeoutError", "OSError", "ValueError", "TypeError", "KeyboardInterrupt", "SystemExit", "CancelledError", "Exception"},
    "http.method": {"GET", "POST", "DELETE"},
    "runtime": {"codex_sdk"},
    "action.name": {"inspect_context", "read_span", "ask_specialist", "finish", "stop"},
    "dispatch": {"harness"},
    "failure.kind": {"http_auth", "http_rate_limit", "http_client", "http_server", "http_redirect",
                     "http_status", "timeout", "tls", "network", "response_framing", "response_type",
                     "response_limit", "worker_input", "worker_internal", "worker_start", "worker_failed",
                     "transport_unknown", "unclassified"},
    "sdk.tool_kind": {"commandExecution", "fileChange", "mcpToolCall", "dynamicToolCall",
                      "collabAgentToolCall", "webSearch", "imageView"},
}
COUNTS = {"input_bytes", "output_bytes", "input_tokens", "output_tokens", "reserved_microusd",
          "cached_input_tokens", "cache_write_input_tokens", "reasoning_output_tokens",
          "estimated_cost_microusd", "source_requests", "model_calls", "items", "attempt", "poll",
          "http.status_code", "rejected_attributes", "tool_sequence", "sdk_tool_duration_ns"}
BOOLEANS = {"fixture", "ambiguous", "replayed", "incomplete", "usage_known", "usage_details_known", "observation_only"}
REFERENCES = {"operation_ref", "session_ref", "error.code_ref", "model_ref", "source_ref", "thread_ref", "turn_ref"}
MAX_SPANS = 10000
MAX_EXPORT = 100
MAX_ATTRIBUTES = 32
MAX_EXPORT_ATTEMPTS = 10000
MAX_STORAGE_BYTES = 32 * 1024 * 1024
_SCHEMA = (
    "CREATE TABLE IF NOT EXISTS spans (seq INTEGER PRIMARY KEY AUTOINCREMENT, "
    "trace_id TEXT NOT NULL, span_id TEXT NOT NULL UNIQUE, parent_id TEXT, "
    "operation TEXT NOT NULL, start_ns INTEGER NOT NULL, end_ns INTEGER, "
    "duration_ns INTEGER, status TEXT NOT NULL, attributes TEXT NOT NULL, exported INTEGER NOT NULL DEFAULT 0)",
    "CREATE INDEX IF NOT EXISTS trace_lookup ON spans(trace_id,seq)",
    "CREATE TABLE IF NOT EXISTS export_attempts (seq INTEGER PRIMARY KEY AUTOINCREMENT, "
    "attempt_id TEXT NOT NULL UNIQUE, started_ns INTEGER NOT NULL, finished_ns INTEGER, "
    "status TEXT NOT NULL, span_ids TEXT NOT NULL, result TEXT)",
    "CREATE TABLE IF NOT EXISTS export_claims (span_id TEXT PRIMARY KEY, attempt_id TEXT NOT NULL)",
)
EXPORT_ERRORS = {"WALL_TIMEOUT", "TIMEOUT", "TRANSPORT_ERROR", "WORKER_START_FAILED", "WORKER_FAILED",
                 "MALFORMED_TRANSPORT", "RESPONSE_TOO_LARGE", "REDIRECT_REFUSED", "UNEXPECTED_HTTP_STATUS",
                 "UNEXPECTED_CONTENT_TYPE", "UNEXPECTED_ENCODING", "INVALID_RESPONSE_LENGTH", "MALFORMED_ACKNOWLEDGEMENT"}
WIRE_ATTRIBUTES = {"gen_ai.usage.input_tokens": "input_tokens", "gen_ai.usage.output_tokens": "output_tokens",
                   "gen_ai.system": "provider"}
EVENT_ID_ATTRIBUTE = "traceloop.association.properties.event_id"
EVENT_USER_ATTRIBUTE = "traceloop.association.properties.user_id"
EVENT_USER = "context-research-harness"
TOOL_SPANS = frozenset({"source.retrieve", "source.primary", "mcp.invoke", "repository.publish",
                        "sdk.tool", "agent.action"})
TOOL_KIND_ATTRIBUTE = "traceloop.span.kind"
TOOL_NAME_ATTRIBUTE = "traceloop.entity.name"
_CURRENT: ContextVar["Span | None"] = ContextVar("research_trace_span", default=None)
FAILURE_CODES = {"TRACE_INVALID_ATTRIBUTES", "TRACE_REFERENCE_FAILED", "TRACE_INITIALIZATION_FAILED",
                 "TRACE_WRITE_FAILED", "TRACE_INTERNAL_FAILURE"}


def _attributes(attributes):
    if not isinstance(attributes, dict) or len(attributes) > MAX_ATTRIBUTES:
        raise ServiceError("TRACE_INVALID_ATTRIBUTES")
    for key, value in attributes.items():
        valid = False
        if key in ENUMS:
            valid = isinstance(value, str) and value in ENUMS[key]
        elif key in COUNTS:
            valid = type(value) is int and 0 <= value <= 2**53 - 1
            if key == "http.status_code":
                valid = valid and 100 <= value <= 599
        elif key in BOOLEANS:
            valid = type(value) is bool
        elif key in REFERENCES:
            valid = isinstance(value, str) and re.fullmatch(r"[a-f0-9]{32}", value) is not None
        if not valid:
            raise ServiceError("TRACE_INVALID_ATTRIBUTES")
    return dict(attributes)


def _span_id(value, size):
    return (isinstance(value, str) and re.fullmatch(r"[a-f0-9]{" + str(size) + r"}", value)
            and int(value, 16) != 0)


def _nanoseconds(value):
    return type(value) is int and 0 <= value <= 2**63 - 1


def _record(value):
    """Validate both write inputs and rows read back from mutable local storage."""
    required = {"seq", "trace_id", "span_id", "parent_id", "operation", "start_ns", "end_ns",
                "duration_ns", "status", "attributes", "exported"}
    if (not isinstance(value, dict) or set(value) != required
            or type(value["seq"]) is not int or not 1 <= value["seq"] <= 2**63 - 1
            or not _span_id(value["trace_id"], 32) or not _span_id(value["span_id"], 16)
            or (value["parent_id"] is not None and not _span_id(value["parent_id"], 16))
            or value["parent_id"] == value["span_id"]
            or not isinstance(value["operation"], str) or value["operation"] not in TOOLS
            or not _nanoseconds(value["start_ns"])
            or type(value["exported"]) is not int or value["exported"] not in (0, 1)):
        raise ServiceError("TRACE_INVALID_RECORD")
    if value["end_ns"] is None:
        valid = value["duration_ns"] is None and value["status"] == "running" and value["exported"] == 0
    else:
        valid = (_nanoseconds(value["end_ns"]) and _nanoseconds(value["duration_ns"])
                 and value["end_ns"] == value["start_ns"] + value["duration_ns"]
                 and isinstance(value["status"], str) and value["status"] in {"ok", "error", "interrupted"})
    if not valid:
        raise ServiceError("TRACE_INVALID_RECORD")
    _attributes(value["attributes"])
    return value


def _stored_record(row):
    value = dict(row)
    try:
        encoded = value["attributes"]
        if not isinstance(encoded, str) or len(encoded) > 8192:
            raise ValueError()
        value["attributes"] = parse_json_strict(encoded)
        return _record(value)
    except (ValueError, TypeError, KeyError, OverflowError, RecursionError):
        raise ServiceError("TRACE_INVALID_RECORD") from None


def _span_ids(values):
    if (not isinstance(values, list) or not 1 <= len(values) <= MAX_EXPORT
            or any(not _span_id(value, 16) for value in values) or len(set(values)) != len(values)):
        raise ServiceError("TRACE_INVALID_EXPORT_RECEIPT")
    return values


def _export_result(value, count):
    if isinstance(value, dict) and value.get("schema") == "trace-export-result/v2":
        return _bundle_result(value, count)
    keys = {"schema", "status", "attempted", "span_count", "rejected_spans", "warning", "error_code"}
    if (not isinstance(value, dict) or set(value) != keys or value["schema"] != "trace-export-result/v1"
            or type(value["attempted"]) is not bool or type(value["warning"]) is not bool
            or type(value["span_count"]) is not int or value["span_count"] != count
            or not isinstance(value["status"], str)):
        raise ServiceError("TRACE_INVALID_EXPORT_RECEIPT")
    rejected, code, status = value["rejected_spans"], value["error_code"], value["status"]
    if status == "unknown":
        valid = (rejected is None and value["warning"] is False and isinstance(code, str) and code in EXPORT_ERRORS
                 and value["attempted"] is (code != "WORKER_START_FAILED"))
    elif type(rejected) is int and value["attempted"]:
        valid = ((status == "exported" and rejected == 0 and code is None)
                 or (status == "partial" and 1 <= rejected <= count and code == "PARTIAL_REJECTION")
                 or (status == "rejected" and rejected == count and code == "HTTP_REJECTED" and not value["warning"]))
    else:
        valid = False
    if not valid:
        raise ServiceError("TRACE_INVALID_EXPORT_RECEIPT")
    return dict(value)


def _event_progress(value, count):
    from .trace_events import validate_event_result
    if (not isinstance(value, dict) or set(value) != {"schema", "events"}
            or value["schema"] != "trace-export-progress/v2"):
        raise ServiceError("TRACE_INVALID_EXPORT_RECEIPT")
    events = value["events"]
    if (not isinstance(events, dict) or type(events.get("event_count")) is not int
            or not 0 <= events["event_count"] <= count):
        raise ServiceError("TRACE_INVALID_EXPORT_RECEIPT")
    validate_event_result(events, events["event_count"])
    return value


def _bundle_result(value, count):
    keys = {"schema", "status", "attempted", "span_count", "events", "traces"}
    if (set(value) != keys or type(value["span_count"]) is not int or value["span_count"] != count
            or type(value["attempted"]) is not bool):
        raise ServiceError("TRACE_INVALID_EXPORT_RECEIPT")
    _event_progress({"schema": "trace-export-progress/v2", "events": value["events"]}, count)
    events, traces = value["events"], value["traces"]
    if events["status"] in {"exported", "empty"}:
        if not isinstance(traces, dict) or traces.get("schema") != "trace-export-result/v1":
            raise ServiceError("TRACE_INVALID_EXPORT_RECEIPT")
        _export_result(traces, count)
        status, attempted = traces["status"], events["attempted"] or traces["attempted"]
    else:
        if traces is not None:
            raise ServiceError("TRACE_INVALID_EXPORT_RECEIPT")
        status, attempted = events["status"], events["attempted"]
    if value["status"] != status or value["attempted"] is not attempted:
        raise ServiceError("TRACE_INVALID_EXPORT_RECEIPT")
    return dict(value)


def _export_record(row):
    value = dict(row)
    try:
        if (set(value) != {"seq", "attempt_id", "started_ns", "finished_ns", "status", "span_ids", "result"}
                or type(value["seq"]) is not int or not 1 <= value["seq"] <= 2**63 - 1
                or not _span_id(value["attempt_id"], 32) or not _nanoseconds(value["started_ns"])
                or not isinstance(value["span_ids"], str) or len(value["span_ids"]) > 4096):
            raise ValueError()
        value["span_ids"] = _span_ids(parse_json_strict(value["span_ids"]))
        if value["status"] == "running":
            if value["finished_ns"] is not None:
                raise ValueError()
            if value["result"] is not None:
                if not isinstance(value["result"], str) or len(value["result"]) > 4096:
                    raise ValueError()
                value["result"] = _event_progress(parse_json_strict(value["result"]), len(value["span_ids"]))
        else:
            if (not _nanoseconds(value["finished_ns"]) or not isinstance(value["result"], str)
                    or len(value["result"]) > 4096):
                raise ValueError()
            value["result"] = _export_result(parse_json_strict(value["result"]), len(value["span_ids"]))
            if value["status"] != value["result"]["status"]:
                raise ValueError()
        return value
    except (ValueError, TypeError, KeyError, OverflowError, RecursionError):
        raise ServiceError("TRACE_INVALID_EXPORT_RECEIPT") from None


def _private(path, *, directory=False):
    info = path.lstat()
    mode = 0o700 if directory else 0o600
    if (path.resolve() != path or stat.S_ISLNK(info.st_mode) or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != mode
            or (not stat.S_ISDIR(info.st_mode) if directory else not stat.S_ISREG(info.st_mode))
            or (not directory and info.st_nlink != 1)):
        raise ServiceError("TRACE_UNSAFE_PATH")


class TraceJournal:
    def __init__(self, directory: Path, *, max_spans=MAX_SPANS, initialize=True, read_only=False):
        """Writers initialize by default; inspection must explicitly open existing.

        Existing-only opens never repair keys/schema/files. Read-only connections
        use SQLite locking (not immutable snapshots), accept rollback-journal
        databases only, and refuse recovery sidecars instead of repairing them.
        Paths remain cooperative owner-writable storage, not same-UID isolation.
        """
        if type(max_spans) is not int or not 1 <= max_spans <= MAX_SPANS:
            raise ServiceError("TRACE_INVALID_LIMIT")
        if type(initialize) is not bool or type(read_only) is not bool or (initialize and read_only):
            raise ServiceError("TRACE_INVALID_OPEN_MODE")
        self.directory = Path(directory).absolute()
        self.read_only, self.initialize = read_only, initialize
        self.path = self.directory / "traces.sqlite3"
        self.max_spans = max_spans
        if not initialize:
            self._open_existing()
            return
        _private(self.directory.parent, directory=True)
        self.directory.mkdir(mode=0o700, exist_ok=True)
        _private(self.directory, directory=True)
        lock = self.directory / "trace.lock"
        fd = os.open(lock, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            _private(lock)
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            key_path = self.directory / "correlation.key"
            if not key_path.exists():
                key_fd = os.open(key_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
                try:
                    os.write(key_fd, secrets.token_bytes(32))
                    os.fsync(key_fd)
                finally:
                    os.close(key_fd)
            _private(key_path)
            self._key = key_path.read_bytes()
            if len(self._key) != 32:
                raise ServiceError("TRACE_CORRUPT_KEY")
            if not self.path.exists():
                db_fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
                os.close(db_fd)
            with self.connect() as db:
                for statement in _SCHEMA:
                    db.execute(statement)
            directory_fd = os.open(self.directory, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            os.close(fd)

    def _existing_files(self):
        try:
            _private(self.directory.parent, directory=True)
            _private(self.directory, directory=True)
            for name in ("trace.lock", "correlation.key", "traces.sqlite3"):
                _private(self.directory / name)
            if (self.directory / "correlation.key").stat().st_size != 32:
                raise ServiceError("TRACE_CORRUPT_KEY")
            if not 100 <= self.path.stat().st_size <= MAX_STORAGE_BYTES:
                raise ServiceError("TRACE_STORAGE_FAILED")
            # mode=ro may still create WAL shared-memory files. This journal
            # never enables WAL; refuse foreign WAL mode rather than ignore it.
            with self.path.open("rb") as stream:
                header = stream.read(100)
            if header[:16] != b"SQLite format 3\x00" or header[18:20] != b"\x01\x01":
                raise ServiceError("TRACE_STORAGE_FAILED")
            for suffix in ("journal", "wal", "shm"):
                sidecar = self.directory / ("traces.sqlite3-" + suffix)
                if sidecar.exists() or sidecar.is_symlink():
                    _private(sidecar)
                    if sidecar.stat().st_size:
                        raise ServiceError("TRACE_RECOVERY_REQUIRED")
        except FileNotFoundError:
            raise ServiceError("TRACE_JOURNAL_NOT_FOUND") from None

    @staticmethod
    def _validate_schema(db):
        expected = {statement.replace(" IF NOT EXISTS", "") for statement in _SCHEMA}
        actual = {row[0] for row in db.execute(
            "SELECT sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'")}
        if actual != expected or db.execute("PRAGMA quick_check(1)").fetchone()[0] != "ok":
            raise ServiceError("TRACE_STORAGE_FAILED")

    def _open_existing(self):
        self._existing_files()
        fd = os.open(self.directory / "trace.lock", os.O_RDONLY | os.O_NOFOLLOW)
        try:
            fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
            self._existing_files()
            self._key = (self.directory / "correlation.key").read_bytes()
            if len(self._key) != 32:
                raise ServiceError("TRACE_CORRUPT_KEY")
            with self.connect(read_only=True) as db:
                self._validate_schema(db)
        finally:
            os.close(fd)

    @contextlib.contextmanager
    def connect(self, *, read_only=False):
        if self.read_only and not read_only:
            raise ServiceError("TRACE_READ_ONLY")
        if read_only or not self.initialize:
            self._existing_files()
        _private(self.directory, directory=True)
        _private(self.path)
        for name in ("traces.sqlite3-journal", "traces.sqlite3-wal", "traces.sqlite3-shm"):
            path = self.directory / name
            if path.exists() or path.is_symlink():
                _private(path)
        db = None
        try:
            db = sqlite3.connect(self.path.as_uri() + ("?mode=ro" if read_only else "?mode=rw"), uri=True, timeout=0.1)
            db.row_factory = sqlite3.Row
            if read_only:
                db.execute("PRAGMA query_only=ON")
            else:
                db.execute("PRAGMA synchronous=FULL")
                db.execute("PRAGMA max_page_count=8192")
            with db:
                yield db
        except sqlite3.Error:
            raise ServiceError("TRACE_STORAGE_FAILED") from None
        finally:
            if db is not None:
                db.close()

    def reference(self, value):
        if not isinstance(value, (str, bytes)):
            raise ServiceError("TRACE_INVALID_REFERENCE")
        raw = value.encode() if isinstance(value, str) else value
        if len(raw) > 4096:
            raise ServiceError("TRACE_INVALID_REFERENCE")
        return hmac.new(self._key, raw, hashlib.sha256).hexdigest()[:32]

    def begin(self, trace_id, span_id, parent_id, operation, started, attributes):
        if not isinstance(operation, str) or operation not in TOOLS:
            raise ServiceError("TRACE_UNKNOWN_OPERATION")
        _record({"seq": 1, "trace_id": trace_id, "span_id": span_id, "parent_id": parent_id,
                 "operation": operation, "start_ns": started, "end_ns": None, "duration_ns": None,
                 "status": "running", "attributes": attributes, "exported": 0})
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT count(*) FROM spans").fetchone()[0] >= self.max_spans:
                raise ServiceError("TRACE_CAPACITY_REACHED")
            db.execute("INSERT INTO spans(trace_id,span_id,parent_id,operation,start_ns,status,attributes) "
                       "VALUES(?,?,?,?,?,'running',?)", (trace_id, span_id, parent_id, operation, started,
                        json.dumps(attributes, sort_keys=True, separators=(",", ":"))))

    def finish(self, span_id, ended, duration, status, attributes):
        if (not _span_id(span_id, 16) or not _nanoseconds(ended) or not _nanoseconds(duration)
                or not isinstance(status, str) or status not in {"ok", "error", "interrupted"}):
            raise ServiceError("TRACE_INVALID_STATUS")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            original = db.execute("SELECT * FROM spans WHERE span_id=?", (span_id,)).fetchone()
            if original is None:
                raise ServiceError("TRACE_MISSING_START")
            row = _stored_record(original)
            if row["status"] != "running":
                raise ServiceError("TRACE_MISSING_START")
            _record({**row, "end_ns": ended, "duration_ns": duration, "status": status, "attributes": attributes})
            cursor = db.execute("UPDATE spans SET end_ns=?,duration_ns=?,status=?,attributes=? "
                "WHERE span_id=? AND status='running'", (ended, duration, status,
                    json.dumps(attributes, sort_keys=True, separators=(",", ":")), span_id))
            if cursor.rowcount != 1:
                raise ServiceError("TRACE_MISSING_START")

    def rows(self, *, limit=MAX_EXPORT, after=0, pending=False):
        if (type(limit) is not int or not 1 <= limit <= MAX_EXPORT or type(after) is not int
                or not 0 <= after <= 2**63 - 1 or type(pending) is not bool):
            raise ServiceError("TRACE_INVALID_QUERY")
        with self.connect(read_only=True) as db:
            rows = db.execute("SELECT * FROM spans WHERE seq>? " +
                ("AND exported=0 AND end_ns IS NOT NULL AND NOT EXISTS "
                 "(SELECT 1 FROM export_claims WHERE export_claims.span_id=spans.span_id) " if pending else "")
                + "ORDER BY seq LIMIT ?", (after, limit)).fetchall()
        return [_stored_record(row) for row in rows]

    def require_event_roots(self, span_ids):
        """Require a current root or retained successful Event phase per trace.

        This is local delivery evidence, not cloud readback. Historical receipts
        do not bind an export destination; continuation assumes that the operator
        has not changed this journal's configured Raindrop target.
        """
        _span_ids(span_ids)
        with self.connect(read_only=True) as db:
            db.execute("BEGIN")
            selected = {}
            for span_id in span_ids:
                row = db.execute("SELECT * FROM spans WHERE span_id=?", (span_id,)).fetchone()
                if row is None:
                    raise ServiceError("TRACE_INVALID_EXPORT_RECEIPT")
                record = _stored_record(row)
                if record["end_ns"] is None:
                    raise ServiceError("TRACE_EVENT_ROOT_UNCONFIRMED")
                selected[span_id] = record
            confirmed_attempts = {}
            for trace_id in {row["trace_id"] for row in selected.values()}:
                roots = db.execute("SELECT * FROM spans WHERE trace_id=? AND parent_id IS NULL LIMIT 2",
                                   (trace_id,)).fetchall()
                if len(roots) != 1:
                    raise ServiceError("TRACE_EVENT_ROOT_UNCONFIRMED")
                root = _stored_record(roots[0])
                if root["end_ns"] is None:
                    raise ServiceError("TRACE_EVENT_ROOT_UNCONFIRMED")
                if root["span_id"] in selected:
                    continue  # This batch must ACK Event creation before OTLP.
                claim = db.execute("SELECT attempt_id FROM export_claims WHERE span_id=?",
                                   (root["span_id"],)).fetchone()
                if claim is None:
                    raise ServiceError("TRACE_EVENT_ROOT_UNCONFIRMED")
                attempt_id = claim["attempt_id"]
                if attempt_id not in confirmed_attempts:
                    row = db.execute("SELECT * FROM export_attempts WHERE attempt_id=?", (attempt_id,)).fetchone()
                    if row is None:
                        raise ServiceError("TRACE_INVALID_EXPORT_RECEIPT")
                    attempt = _export_record(row)
                    result = attempt["result"]
                    if (not isinstance(result, dict) or result.get("schema") not in
                            {"trace-export-progress/v2", "trace-export-result/v2"}
                            or result["events"]["status"] != "exported"):
                        raise ServiceError("TRACE_EVENT_ROOT_UNCONFIRMED")
                    claimed = {row[0] for row in db.execute(
                        "SELECT span_id FROM export_claims WHERE attempt_id=?", (attempt_id,))}
                    if claimed != set(attempt["span_ids"]):
                        raise ServiceError("TRACE_INVALID_EXPORT_RECEIPT")
                    acknowledged_roots = set()
                    for member_id in attempt["span_ids"]:
                        member = db.execute("SELECT * FROM spans WHERE span_id=?", (member_id,)).fetchone()
                        if member is None:
                            raise ServiceError("TRACE_EVENT_ROOT_UNCONFIRMED")
                        member = _stored_record(member)
                        if member["end_ns"] is None:
                            raise ServiceError("TRACE_INVALID_EXPORT_RECEIPT")
                        if member["parent_id"] is None:
                            acknowledged_roots.add(member_id)
                    if len(acknowledged_roots) != result["events"]["event_count"]:
                        raise ServiceError("TRACE_INVALID_EXPORT_RECEIPT")
                    confirmed_attempts[attempt_id] = acknowledged_roots
                if root["span_id"] not in confirmed_attempts[attempt_id]:
                    raise ServiceError("TRACE_INVALID_EXPORT_RECEIPT")

    def begin_export(self, span_ids):
        """Commit one non-retryable batch intent before either delivery phase."""
        _span_ids(span_ids)
        attempt_id = secrets.token_hex(16)
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT count(*) FROM export_attempts").fetchone()[0] >= MAX_EXPORT_ATTEMPTS:
                raise ServiceError("TRACE_EXPORT_CAPACITY_REACHED")
            for span_id in span_ids:
                row = db.execute("SELECT * FROM spans WHERE span_id=?", (span_id,)).fetchone()
                if row is None:
                    raise ServiceError("TRACE_INVALID_EXPORT_RECEIPT")
                record = _stored_record(row)
                if record["end_ns"] is None or record["exported"]:
                    raise ServiceError("TRACE_INVALID_EXPORT_RECEIPT")
                if db.execute("SELECT 1 FROM export_claims WHERE span_id=?", (span_id,)).fetchone():
                    raise ServiceError("TRACE_EXPORT_ALREADY_ATTEMPTED")
            db.execute("INSERT INTO export_attempts(attempt_id,started_ns,status,span_ids) VALUES(?,?,'running',?)",
                       (attempt_id, time.time_ns(), json.dumps(span_ids, separators=(",", ":"))))
            db.executemany("INSERT INTO export_claims(span_id,attempt_id) VALUES(?,?)",
                           [(span_id, attempt_id) for span_id in span_ids])
        return attempt_id

    def record_event_export(self, attempt_id, result):
        """Persist the Event phase before attempting linked OTLP delivery.

        A crash retains the phase receipt inside the running attempt. It never
        grants permission to resume or resend either remote effect.
        """
        if not _span_id(attempt_id, 32):
            raise ServiceError("TRACE_INVALID_EXPORT_RECEIPT")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM export_attempts WHERE attempt_id=?", (attempt_id,)).fetchone()
            if row is None:
                raise ServiceError("TRACE_INVALID_EXPORT_RECEIPT")
            attempt = _export_record(row)
            progress = _event_progress({"schema": "trace-export-progress/v2", "events": result},
                                       len(attempt["span_ids"]))
            roots = 0
            for span_id in attempt["span_ids"]:
                original = db.execute("SELECT * FROM spans WHERE span_id=?", (span_id,)).fetchone()
                if original is None:
                    raise ServiceError("TRACE_INVALID_EXPORT_RECEIPT")
                roots += _stored_record(original)["parent_id"] is None
            if roots != result["event_count"] or attempt["status"] != "running":
                raise ServiceError("TRACE_INVALID_EXPORT_RECEIPT")
            if attempt["result"] is not None:
                if attempt["result"] == progress:
                    return
                raise ServiceError("TRACE_EXPORT_ALREADY_FINISHED")
            db.execute("UPDATE export_attempts SET result=? WHERE attempt_id=?",
                       (json.dumps(progress, sort_keys=True, separators=(",", ":")), attempt_id))

    def finish_export(self, attempt_id, result):
        """Full ACK and exported flags commit together; uncertainty never retries."""
        if not _span_id(attempt_id, 32):
            raise ServiceError("TRACE_INVALID_EXPORT_RECEIPT")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM export_attempts WHERE attempt_id=?", (attempt_id,)).fetchone()
            if row is None:
                raise ServiceError("TRACE_INVALID_EXPORT_RECEIPT")
            attempt = _export_record(row)
            result = _export_result(result, len(attempt["span_ids"]))
            if attempt["status"] != "running":
                if attempt["result"] == result:
                    return
                raise ServiceError("TRACE_EXPORT_ALREADY_FINISHED")
            if result["schema"] == "trace-export-result/v2":
                if (attempt["result"] is None or attempt["result"]["events"] != result["events"]):
                    raise ServiceError("TRACE_INVALID_EXPORT_RECEIPT")
            elif attempt["result"] is not None:
                raise ServiceError("TRACE_INVALID_EXPORT_RECEIPT")
            claimed = [row[0] for row in db.execute("SELECT span_id FROM export_claims WHERE attempt_id=?", (attempt_id,))]
            if set(claimed) != set(attempt["span_ids"]):
                raise ServiceError("TRACE_INVALID_EXPORT_RECEIPT")
            for span_id in attempt["span_ids"]:
                original = db.execute("SELECT * FROM spans WHERE span_id=?", (span_id,)).fetchone()
                if original is None or _stored_record(original)["end_ns"] is None or original["exported"]:
                    raise ServiceError("TRACE_INVALID_EXPORT_RECEIPT")
            if result["status"] == "exported":
                db.executemany("UPDATE spans SET exported=1 WHERE span_id=?", [(value,) for value in attempt["span_ids"]])
            db.execute("UPDATE export_attempts SET finished_ns=?,status=?,result=? WHERE attempt_id=?",
                       (time.time_ns(), result["status"], json.dumps(result, sort_keys=True, separators=(",", ":")), attempt_id))

    def export_rows(self, *, limit=MAX_EXPORT, after=0):
        if (type(limit) is not int or not 1 <= limit <= MAX_EXPORT or type(after) is not int
                or not 0 <= after <= 2**63 - 1):
            raise ServiceError("TRACE_INVALID_QUERY")
        with self.connect(read_only=True) as db:
            rows = db.execute("SELECT * FROM export_attempts WHERE seq>? ORDER BY seq LIMIT ?", (after, limit)).fetchall()
        return [_export_record(row) for row in rows]

    def status(self):
        with self.connect(read_only=True) as db:
            total, running, unacknowledged = db.execute("SELECT count(*),sum(end_ns IS NULL), "
                "sum(exported=0 AND end_ns IS NOT NULL) FROM spans").fetchone()
            pending = db.execute("SELECT count(*) FROM spans WHERE exported=0 AND end_ns IS NOT NULL "
                "AND NOT EXISTS (SELECT 1 FROM export_claims WHERE export_claims.span_id=spans.span_id)").fetchone()[0]
            attempts, unfinished, unknown = db.execute("SELECT count(*),sum(status='running'),sum(status='unknown') FROM export_attempts").fetchone()
        return {"schema": "research-trace-status/v1", "spans": total, "unfinished_spans": running or 0,
                "pending_export": pending or 0, "max_spans": self.max_spans,
                "storage_bytes": self.path.stat().st_size, "authority": "none",
                "unacknowledged_spans": unacknowledged or 0, "export_attempts": attempts,
                "unfinished_exports": unfinished or 0, "unknown_exports": unknown or 0}

    def prune_exported(self, *, before_ns):
        if type(before_ns) is not int or before_ns < 0:
            raise ServiceError("TRACE_INVALID_RETENTION")
        with self.connect() as db:
            removed = db.execute("DELETE FROM spans WHERE exported=1 AND end_ns<?", (before_ns,)).rowcount
        return removed


@dataclass
class Span:
    tracer: "Tracer"
    trace_id: str
    span_id: str
    parent_id: str | None
    operation: str
    attributes: dict
    started_ns: int
    monotonic_ns: int
    recorded: bool = False
    status: str = "ok"

    def set_status(self, status):
        """Represent a failed returned outcome without inventing an exception."""
        if isinstance(status, str) and status in {"ok", "error", "interrupted"}:
            self.status = status
        else:
            self.tracer._failure("TRACE_INVALID_ATTRIBUTES")

    def annotate(self, **attributes):
        try:
            merged = _attributes({**self.attributes, **_attributes(attributes)})
            self.attributes = merged
        except Exception:
            self.tracer._failure("TRACE_INVALID_ATTRIBUTES")

    def reference(self, field, value):
        try:
            self.annotate(**{field: self.tracer.journal.reference(value)})
        except Exception:
            self.tracer._failure("TRACE_REFERENCE_FAILED")


class Tracer:
    def __init__(self, journal: TraceJournal | None, *, wall_ns=time.time_ns, monotonic_ns=time.monotonic_ns):
        self.journal, self.wall_ns, self.monotonic_ns = journal, wall_ns, monotonic_ns
        self.failures = 0
        self.last_failure = None
        self._guard = threading.Lock()

    @classmethod
    def at(cls, parent):
        try:
            return cls(TraceJournal(Path(parent) / "telemetry"))
        except Exception:
            result = cls(None)
            result._failure("TRACE_INITIALIZATION_FAILED")
            return result

    def _failure(self, code):
        code = code if isinstance(code, str) and code in FAILURE_CODES else "TRACE_INTERNAL_FAILURE"
        with self._guard:
            self.failures += 1
            self.last_failure = code
            first = self.failures == 1
        if first:
            try:
                print(json.dumps({"event": "trace_degraded", "code": code}), file=sys.stderr, flush=True)
            except Exception:
                pass  # Observability cannot replace an effect result or exception.

    def health(self):
        return {"available": self.journal is not None, "write_failures": self.failures,
                "last_failure": self.last_failure, "remote_export_enabled": False}

    @contextlib.contextmanager
    def span(self, operation, *, attributes=None, identity=None):
        parent = _CURRENT.get()
        trace_id = parent.trace_id if parent else secrets.token_hex(16)
        if parent is None and identity is not None and self.journal is not None:
            try:
                trace_id = self.journal.reference(operation + ":" + identity)
            except Exception:
                self._failure("TRACE_REFERENCE_FAILED")
        try:
            safe_attributes = _attributes(attributes or {})
        except Exception:
            safe_attributes = {}
            self._failure("TRACE_INVALID_ATTRIBUTES")
        timing_valid = True
        try:
            started, monotonic = self.wall_ns(), self.monotonic_ns()
            if not _nanoseconds(started) or not _nanoseconds(monotonic):
                raise ValueError()
        except Exception:
            started = monotonic = 0
            timing_valid = False
            self._failure("TRACE_WRITE_FAILED")
        span = Span(self, trace_id, secrets.token_hex(8), parent.span_id if parent else None,
                    operation, safe_attributes, started, monotonic)
        try:
            if self.journal is not None and timing_valid:
                self.journal.begin(trace_id, span.span_id, span.parent_id, operation, span.started_ns, span.attributes)
                span.recorded = True
        except Exception:
            self._failure("TRACE_WRITE_FAILED")
        token = _CURRENT.set(span)
        status = "ok"
        try:
            yield span
        except BaseException as error:
            status = "interrupted" if isinstance(error, (KeyboardInterrupt, SystemExit, asyncio.CancelledError)) else "error"
            name = type(error).__name__
            span.annotate(**{"error.type": name if name in ENUMS["error.type"] else "Exception"})
            # A keyed reference permits local correlation without publishing
            # arbitrary exception text or a credential disguised as an error.
            try:
                code = getattr(error, "code", None)
            except Exception:
                code = None
                self._failure("TRACE_REFERENCE_FAILED")
            if isinstance(code, str):
                span.reference("error.code_ref", code)
            raise
        finally:
            try:
                _CURRENT.reset(token)
            except Exception:
                self._failure("TRACE_WRITE_FAILED")
            try:
                duration = max(0, self.monotonic_ns() - span.monotonic_ns)
                if span.recorded:
                    self.journal.finish(span.span_id, span.started_ns + duration, duration,
                                        span.status if status == "ok" else status, span.attributes)
            except Exception:
                self._failure("TRACE_WRITE_FAILED")


def current_span():
    return _CURRENT.get()


def annotate(**attributes):
    span = current_span()
    if span is not None:
        span.annotate(**attributes)


@contextlib.contextmanager
def child_span(operation, **attributes):
    parent = current_span()
    if parent is None:
        yield None
    else:
        with parent.tracer.span(operation, attributes=attributes) as span:
            yield span


def traced(operation):
    """Explicit methods only; never inspect or serialize arguments/results."""
    if operation not in TOOLS:
        raise ValueError("unregistered trace operation")
    def decorate(function):
        if inspect.iscoroutinefunction(function):
            @wraps(function)
            async def invoke_async(self, *args, **kwargs):
                parent = current_span()
                with (parent.tracer if parent else self.tracer).span(operation):
                    return await function(self, *args, **kwargs)
            return invoke_async
        @wraps(function)
        def invoke(self, *args, **kwargs):
            parent = current_span()
            with (parent.tracer if parent else self.tracer).span(operation):
                return function(self, *args, **kwargs)
        return invoke
    return decorate


def instrument(operation):
    """Plain functions join an active trace only; no implicit journal or effects."""
    if not isinstance(operation, str) or operation not in TOOLS:
        raise ValueError("unregistered trace operation")
    def decorate(function):
        if inspect.iscoroutinefunction(function):
            @wraps(function)
            async def invoke_async(*args, **kwargs):
                with child_span(operation):
                    return await function(*args, **kwargs)
            return invoke_async
        @wraps(function)
        def invoke(*args, **kwargs):
            with child_span(operation):
                return function(*args, **kwargs)
        return invoke
    return decorate


def otlp_payload(rows):
    if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_EXPORT:
        raise ServiceError("TRACE_INVALID_OTLP")
    spans = []
    for row in rows:
        _record(row)
        if row["end_ns"] is None:
            raise ServiceError("TRACE_UNFINISHED_EXPORT")
        # Explicit association keeps non-LLM spans in Raindrop and joins them
        # to the separately published operational Event. It carries no content.
        attributes = [
            {"key": EVENT_ID_ATTRIBUTE, "value": {"stringValue": row["trace_id"]}},
            {"key": EVENT_USER_ATTRIBUTE, "value": {"stringValue": EVENT_USER}},
        ]
        # Raindrop's SDK uses these exact attributes for tool spans. Only leaf
        # capabilities qualify; workflow.effect is a wrapper, not another tool.
        if row["operation"] in TOOL_SPANS:
            attributes.extend([
                {"key": TOOL_KIND_ATTRIBUTE, "value": {"stringValue": "tool"}},
                {"key": TOOL_NAME_ATTRIBUTE, "value": {"stringValue": row["operation"]}},
            ])
        for key, value in _attributes(row["attributes"]).items():
            kind = "boolValue" if type(value) is bool else "intValue" if type(value) is int else "stringValue"
            if key in {"input_tokens", "output_tokens"}:
                key = "gen_ai.usage." + key
            elif key == "provider" and value in {"openai", "anthropic", "gemini"}:
                key = "gen_ai.system"
            attributes.append({"key": key, "value": {kind: str(value) if kind == "intValue" else value}})
        item = {"traceId": row["trace_id"], "spanId": row["span_id"], "name": row["operation"],
                "kind": 3 if TOOLS[row["operation"]][1] else 1, "startTimeUnixNano": str(row["start_ns"]),
                "endTimeUnixNano": str(row["end_ns"]), "status": {"code": 1 if row["status"] == "ok" else 2},
                "attributes": attributes}
        if row["parent_id"] is not None:
            item["parentSpanId"] = row["parent_id"]
        spans.append(item)
    value = {"resourceSpans": [{"resource": {"attributes": [{"key": "service.name",
             "value": {"stringValue": "context-research-harness"}}]}, "scopeSpans": [{"scope": {
             "name": "researcher.service", "version": "1"}, "spans": spans}]}]}
    validate_otlp(value)
    return value


def validate_otlp(value):
    """Closed metadata-only wire contract; never forwards arbitrary OTLP input."""
    try:
        if not isinstance(value, dict) or set(value) != {"resourceSpans"} or len(value["resourceSpans"]) != 1:
            raise ValueError()
        resource = value["resourceSpans"][0]
        if (set(resource) != {"resource", "scopeSpans"} or resource["resource"] != {"attributes": [
                {"key": "service.name", "value": {"stringValue": "context-research-harness"}}]}
                or len(resource["scopeSpans"]) != 1):
            raise ValueError()
        scope = resource["scopeSpans"][0]
        if set(scope) != {"scope", "spans"} or scope["scope"] != {"name": "researcher.service", "version": "1"}:
            raise ValueError()
        spans = scope["spans"]
        if not isinstance(spans, list) or not 1 <= len(spans) <= MAX_EXPORT:
            raise ValueError()
        ids = set()
        for item in spans:
            required = {"traceId", "spanId", "name", "kind", "startTimeUnixNano", "endTimeUnixNano", "status", "attributes"}
            if not isinstance(item, dict) or set(item) not in (required, required | {"parentSpanId"}):
                raise ValueError()
            for key, count in (("traceId", 32), ("spanId", 16), ("parentSpanId", 16)):
                if key in item and (not isinstance(item[key], str) or not re.fullmatch("[a-f0-9]{" + str(count) + "}", item[key]) or int(item[key], 16) == 0):
                    raise ValueError()
            identity = (item["traceId"], item["spanId"])
            if identity in ids or item.get("parentSpanId") == item["spanId"]:
                raise ValueError()
            ids.add(identity)
            if (item["name"] not in TOOLS or type(item["kind"]) is not int
                    or item["kind"] != (3 if TOOLS[item["name"]][1] else 1)):
                raise ValueError()
            for key in ("startTimeUnixNano", "endTimeUnixNano"):
                if not isinstance(item[key], str) or not re.fullmatch(r"[0-9]{1,19}", item[key]) or int(item[key]) > 2**63 - 1:
                    raise ValueError()
            if int(item["endTimeUnixNano"]) < int(item["startTimeUnixNano"]):
                raise ValueError()
            if set(item["status"]) != {"code"} or type(item["status"]["code"]) is not int or item["status"]["code"] not in (0, 1, 2):
                raise ValueError()
            attributes = {}
            associations = {}
            tool_attributes = {}
            if not isinstance(item["attributes"], list):
                raise ValueError()
            for attr in item["attributes"]:
                if set(attr) != {"key", "value"} or len(attr["value"]) != 1:
                    raise ValueError()
                if attr["key"] in {EVENT_ID_ATTRIBUTE, EVENT_USER_ATTRIBUTE}:
                    expected = item["traceId"] if attr["key"] == EVENT_ID_ATTRIBUTE else EVENT_USER
                    if attr["key"] in associations or attr["value"] != {"stringValue": expected}:
                        raise ValueError()
                    associations[attr["key"]] = expected
                    continue
                if attr["key"] in {TOOL_KIND_ATTRIBUTE, TOOL_NAME_ATTRIBUTE}:
                    expected = "tool" if attr["key"] == TOOL_KIND_ATTRIBUTE else item["name"]
                    if (item["name"] not in TOOL_SPANS or attr["key"] in tool_attributes
                            or attr["value"] != {"stringValue": expected}):
                        raise ValueError()
                    tool_attributes[attr["key"]] = expected
                    continue
                logical_key = WIRE_ATTRIBUTES.get(attr["key"], attr["key"])
                if logical_key in attributes:
                    raise ValueError()
                key, content = next(iter(attr["value"].items()))
                if key == "intValue" and isinstance(content, str) and re.fullmatch(r"[0-9]{1,16}", content):
                    content = int(content)
                elif key not in {"boolValue", "stringValue"}:
                    raise ValueError()
                if (key == "boolValue" and type(content) is not bool) or (key == "stringValue" and not isinstance(content, str)):
                    raise ValueError()
                if attr["key"] == "gen_ai.system" and content not in {"openai", "anthropic", "gemini"}:
                    raise ValueError()
                attributes[logical_key] = content
            # Legacy OTLP previews remain inspectable. Fresh projections always
            # include both exact association attributes; partial pairs are invalid.
            if associations and len(associations) != 2:
                raise ValueError()
            if tool_attributes and len(tool_attributes) != 2:
                raise ValueError()
            _attributes(attributes)
        if len(json.dumps(value, allow_nan=False).encode()) > 1_000_000:
            raise ValueError()
    except (ValueError, TypeError, KeyError, IndexError, AttributeError, OverflowError, RecursionError):
        raise ServiceError("TRACE_INVALID_OTLP") from None
