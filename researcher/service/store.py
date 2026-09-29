"""One transactional workflow owner for a single-host service deployment.

SQLite is supported only on a local persistent volume. A process-lifetime OS
lock fences the worker; transactions arbitrate admission and reservations.
Unacknowledged external effects are never automatically retried after restart.
This is not the legacy research-run journal or an implementation of all SPEC-004.
"""

from __future__ import annotations

import contextlib
import fcntl
import os
from pathlib import Path
import re
import sqlite3
import stat
import time
from typing import Iterator

from researcher.scripts.schema_contract import canonicalize, parse_json_strict, sha256_bytes
from .contracts import EDIT_SCHEMA, RESEARCH_SCHEMA, SCHEDULE, ServiceError, digest, validate

MAX_FEEDBACK_BYTES = 32768
MAX_HISTORY_JOBS = 10000
_TERMINAL_HISTORY = ("proposal_ready", "published", "rejected", "failed")

SCHEMA = """
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE jobs (id TEXT PRIMARY KEY, manifest TEXT NOT NULL, digest TEXT NOT NULL,
 status TEXT NOT NULL, created INTEGER NOT NULL, updated INTEGER NOT NULL, reason TEXT);
CREATE TABLE steps (job TEXT NOT NULL REFERENCES jobs(id), name TEXT NOT NULL,
 input_digest TEXT NOT NULL, output TEXT NOT NULL, output_digest TEXT NOT NULL,
 PRIMARY KEY(job,name));
CREATE TABLE effects (job TEXT NOT NULL REFERENCES jobs(id), name TEXT NOT NULL,
 input_digest TEXT NOT NULL, state TEXT NOT NULL, day TEXT NOT NULL,
 model_calls INTEGER NOT NULL, source_requests INTEGER NOT NULL,
 reserved_microusd INTEGER NOT NULL, output TEXT, output_digest TEXT, reason TEXT,
 PRIMARY KEY(job,name));
CREATE TABLE events (seq INTEGER PRIMARY KEY AUTOINCREMENT, job TEXT, kind TEXT NOT NULL,
 at INTEGER NOT NULL, data TEXT NOT NULL);
CREATE TABLE source_slots (key TEXT PRIMARY KEY, source TEXT NOT NULL, job TEXT NOT NULL,
 name TEXT NOT NULL, reserved INTEGER NOT NULL);
"""


def _encode(value: object) -> str:
    return canonicalize(value).decode("utf-8")


def _decode(text: str):
    return parse_json_strict(text)


class Store:
    def __init__(self, directory: Path, config: dict, *, initialize: bool = False):
        self.directory = Path(directory).absolute()
        self.config = config
        if initialize:
            self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        if (not self.directory.is_dir() or self.directory.resolve() != self.directory
                or stat.S_IMODE(self.directory.stat().st_mode) != 0o700):
            raise ServiceError("PRIVATE_STATE_DIRECTORY_REQUIRED")
        self.path = self.directory / "service.sqlite3"
        self._safe_paths()
        if not self.path.exists():
            if not initialize:
                raise ServiceError("STATE_NOT_INITIALIZED")
            # O_EXCL prevents two initializers from silently replacing state.
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(fd)
            with sqlite3.connect(self.path) as db:
                db.executescript("BEGIN IMMEDIATE;" + SCHEMA)
                db.executemany("INSERT INTO meta VALUES (?,?)", [
                    ("schema", "research-service-store/v1"),
                    ("config_digest", digest(config)), ("paused", "false"), ("last_clock", "0")])
        with self._connect() as db:
            meta = dict(db.execute("SELECT key,value FROM meta"))
            if meta.get("schema") != "research-service-store/v1":
                raise ServiceError("STORE_SCHEMA_MISMATCH")
            if meta.get("config_digest") != digest(config):
                raise ServiceError("CONFIG_CHANGED_REQUIRES_MIGRATION")

    def _safe_paths(self):
        for name in ("service.sqlite3", "service.sqlite3-wal", "service.sqlite3-shm", "worker.lock"):
            path = self.directory / name
            if path.is_symlink():
                raise ServiceError("UNSAFE_STATE_PATH")
            if path.exists():
                info = path.stat()
                if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                        or info.st_uid != os.getuid() or info.st_mode & 0o077):
                    raise ServiceError("UNSAFE_STATE_PATH")

    @contextlib.contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        self._safe_paths()
        db = sqlite3.connect(self.path.as_uri() + "?mode=rw", uri=True, timeout=5)
        db.row_factory = sqlite3.Row
        try:
            db.execute("PRAGMA foreign_keys=ON")
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA synchronous=FULL")
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except sqlite3.DatabaseError:
            db.rollback()
            raise ServiceError("STATE_DATABASE_ERROR") from None
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    @contextlib.contextmanager
    def worker_lock(self):
        self._safe_paths()
        fd = os.open(self.directory / "worker.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise ServiceError("WORKER_ALREADY_RUNNING") from None
            yield
        finally:
            os.close(fd)

    @staticmethod
    def _event(db, job: str | None, kind: str, data: dict):
        db.execute("INSERT INTO events(job,kind,at,data) VALUES (?,?,?,?)",
                   (job, kind, int(time.time()), _encode(data)))

    @staticmethod
    def _observe_clock(db, now: int):
        previous = int(db.execute("SELECT value FROM meta WHERE key='last_clock'").fetchone()[0])
        if now < previous:
            raise ServiceError("CLOCK_MOVED_BACKWARDS")
        db.execute("UPDATE meta SET value=? WHERE key='last_clock'", (str(now),))

    def observe_clock(self, now: int):
        if type(now) is not int or now < 0:
            raise ServiceError("INVALID_CLOCK")
        with self._connect() as db:
            self._observe_clock(db, now)

    def enqueue(self, job_id: str, manifest: dict) -> bool:
        identity = digest(manifest)
        if len(job_id) > 200 or len(canonicalize(manifest)) > 1_000_000:
            raise ServiceError("JOB_LIMIT")
        with self._connect() as db:
            old = db.execute("SELECT digest FROM jobs WHERE id=?", (job_id,)).fetchone()
            if old:
                if old[0] != identity:
                    raise ServiceError("JOB_IDENTITY_COLLISION")
                return False
            if db.execute("SELECT value FROM meta WHERE key='paused'").fetchone()[0] == "true":
                raise ServiceError("ADMISSION_PAUSED")
            if db.execute("SELECT count(*) FROM jobs WHERE status='queued'").fetchone()[0] >= 32:
                raise ServiceError("QUEUE_FULL")
            now = int(time.time())
            db.execute("INSERT INTO jobs VALUES (?,?,?,?,?,?,NULL)",
                       (job_id, _encode(manifest), identity, "queued", now, now))
            self._event(db, job_id, "admitted", {"manifest_digest": identity})
            return True

    def recover(self):
        """Called with worker lock held; preserve unknown effects and reservations."""
        with self._connect() as db:
            pending = list(db.execute("SELECT job,name FROM effects WHERE state='started'"))
            for row in pending:
                db.execute("UPDATE effects SET state='unknown',reason='PROCESS_INTERRUPTED' WHERE job=? AND name=?", tuple(row))
                db.execute("UPDATE jobs SET status='reconciliation_required',reason='PROCESS_INTERRUPTED' WHERE id=?", (row[0],))
                self._event(db, row[0], "effect_unknown", {"step": row[1]})
            # Pure computation can resume from its last committed checkpoint.
            db.execute("UPDATE jobs SET status='queued' WHERE status='running'")
            # Only independent, read-only retrieval lanes may continue around
            # an unknown source effect. The effect is never reset or retried.
            candidates = list(db.execute("SELECT * FROM jobs WHERE status='reconciliation_required' AND reason='PROCESS_INTERRUPTED'"))
            for row in candidates:
                manifest = self._isolation_manifest(row)
                if manifest is None or db.execute(
                    "SELECT 1 FROM steps WHERE job=? AND name='report'", (row["id"],)
                ).fetchone():
                    continue
                unresolved = list(db.execute(
                    "SELECT name FROM effects WHERE job=? AND state IN ('started','unknown')", (row["id"],)
                ))
                allowed = {"retrieval-" + source for source in manifest["schedule"]["sources"]}
                if unresolved and all(effect["name"] in allowed for effect in unresolved):
                    db.execute("UPDATE jobs SET status='queued' WHERE id=?", (row["id"],))
                    self._event(db, row["id"], "retrieval_collection_resumed", {"unknown_effects_retained": True})

    def _isolation_manifest(self, row):
        manifest = self._history_value(row["manifest"], row["digest"], 1_000_000)
        if manifest.get("schema") != "retrieval-work/v1":
            return None
        schedule = manifest.get("schedule")
        validate(schedule, SCHEDULE, "RETRIEVAL_EFFECT_SCOPE_INVALID")
        if (schedule.get("mode") != "retrieve" or schedule not in self.config["schedules"]
                or manifest.get("config_digest") != digest(self.config)):
            raise ServiceError("RETRIEVAL_EFFECT_SCOPE_INVALID")
        return manifest

    def _retrieval_effect_row(self, db, job, name, inputs):
        row = db.execute("SELECT * FROM jobs WHERE id=?", (job,)).fetchone()
        if row is None:
            raise ServiceError("JOB_NOT_FOUND")
        manifest = self._isolation_manifest(row)
        if (manifest is None or name not in {"retrieval-" + source for source in manifest["schedule"]["sources"]}
                or inputs.get("manifest_digest") != row["digest"]
                or not isinstance(inputs.get("policy"), dict)
                or inputs["policy"].get("source") != name.removeprefix("retrieval-")):
            raise ServiceError("RETRIEVAL_EFFECT_SCOPE_INVALID")
        effect = db.execute("SELECT * FROM effects WHERE job=? AND name=?", (job, name)).fetchone()
        if effect is not None and (effect["input_digest"] != digest(inputs) or effect["model_calls"] != 0):
            raise ServiceError("EFFECT_INPUT_CHANGED")
        return row, effect

    def retrieval_effect_outcome(self, job: str, name: str, inputs: dict):
        """Inspect one bound source effect without retrying or forgiving it."""
        with self._connect() as db:
            _, effect = self._retrieval_effect_row(db, job, name, inputs)
            if effect is None:
                return None
            if effect["state"] == "completed":
                output = self._history_value(effect["output"], effect["output_digest"], 2_000_000)
                return {"state": "completed", "output": output}
            if effect["state"] not in {"failed", "unknown"}:
                raise ServiceError("EFFECT_RECONCILIATION_REQUIRED")
            code = effect["reason"]
            if not isinstance(code, str) or not re.fullmatch(r"[A-Z0-9_]{1,100}", code):
                raise ServiceError("EFFECT_RECEIPT_CORRUPT")
            return {"state": effect["state"], "error_code": code}

    def record_retrieval_failure(self, job: str, name: str, inputs: dict, code: str,
                                 *, ambiguous: bool = True):
        """Retain the reservation and uncertainty while other source lanes run."""
        if type(ambiguous) is not bool or not isinstance(code, str) or not re.fullmatch(r"[A-Z0-9_]{1,100}", code):
            raise ServiceError("INVALID_RETRIEVAL_FAILURE")
        with self._connect() as db:
            row, effect = self._retrieval_effect_row(db, job, name, inputs)
            if row["status"] != "running" or effect is None or effect["state"] != "started":
                raise ServiceError("EFFECT_NOT_STARTED")
            state = "unknown" if ambiguous else "failed"
            db.execute("UPDATE effects SET state=?,reason=? WHERE job=? AND name=?", (state, code, job, name))
            self._event(db, job, "retrieval_lane_failed", {"step": name, "code": code,
                                                         "effect_state": state, "reservation_retained": True})

    def next_job(self, job_id: str | None = None) -> dict | None:
        with self._connect() as db:
            if db.execute("SELECT value FROM meta WHERE key='paused'").fetchone()[0] == "true":
                return None
            row = (db.execute("SELECT * FROM jobs WHERE status='queued' AND id=?", (job_id,)).fetchone()
                   if job_id is not None else db.execute(
                       "SELECT * FROM jobs WHERE status='queued' ORDER BY created,id LIMIT 1").fetchone())
            if row is None:
                return None
            db.execute("UPDATE jobs SET status='running',updated=? WHERE id=?", (int(time.time()), row["id"]))
            return {"id": row["id"], "manifest": _decode(row["manifest"])}

    def checkpoint(self, job: str, name: str, inputs: dict, output: dict | None = None):
        identity = digest(inputs)
        with self._connect() as db:
            row = db.execute("SELECT * FROM steps WHERE job=? AND name=?", (job, name)).fetchone()
            if row:
                if row["input_digest"] != identity:
                    raise ServiceError("CHECKPOINT_INPUT_CHANGED")
                value = _decode(row["output"])
                if digest(value) != row["output_digest"]:
                    raise ServiceError("CHECKPOINT_CORRUPT")
                if output is not None and digest(output) != row["output_digest"]:
                    raise ServiceError("CHECKPOINT_OUTPUT_CHANGED")
                return value
            if output is not None:
                if len(canonicalize(output)) > 2_000_000:
                    raise ServiceError("CHECKPOINT_LIMIT")
                db.execute("INSERT INTO steps VALUES (?,?,?,?,?)",
                           (job, name, identity, _encode(output), digest(output)))
                self._event(db, job, "checkpoint", {"step": name, "output_digest": digest(output)})
            return output

    def reserve(self, job: str, name: str, inputs: dict, *, model_calls: int = 0,
                source_requests: int = 0, micros: int = 0, now: int | None = None):
        identity = digest(inputs)
        current = int(time.time()) if now is None else now
        if type(current) is not int or current < 0:
            raise ServiceError("INVALID_CLOCK")
        day = time.strftime("%Y-%m-%d", time.gmtime(current))
        with self._connect() as db:
            row = db.execute("SELECT * FROM effects WHERE job=? AND name=?", (job, name)).fetchone()
            if row:
                if row["input_digest"] != identity:
                    raise ServiceError("EFFECT_INPUT_CHANGED")
                if row["state"] != "completed":
                    raise ServiceError("EFFECT_RECONCILIATION_REQUIRED")
                value = _decode(row["output"])
                if digest(value) != row["output_digest"]:
                    raise ServiceError("EFFECT_RECEIPT_CORRUPT")
                return value
            self._observe_clock(db, current)
            if db.execute("SELECT value FROM meta WHERE key='paused'").fetchone()[0] == "true":
                raise ServiceError("ADMISSION_PAUSED")
            state = db.execute("SELECT status FROM jobs WHERE id=?", (job,)).fetchone()
            if state is None or state[0] != "running":
                raise ServiceError("JOB_NOT_RUNNING")
            if any(type(x) is not int or x < 0 for x in (model_calls, source_requests, micros)):
                raise ServiceError("INVALID_RESERVATION")
            limits = self.config["limits"]
            # An optional lifetime ceiling never resets at midnight or restart.
            # Completed, failed and unknown reservations all consume it.
            lifetime = limits.get("lifetime_budget_microusd")
            if lifetime is not None:
                if type(lifetime) is not int or lifetime < 0:
                    raise ServiceError("INVALID_LIFETIME_BUDGET")
                used = db.execute("SELECT coalesce(sum(reserved_microusd),0) FROM effects").fetchone()[0]
                if used + micros > lifetime:
                    raise ServiceError("LIFETIME_BUDGET_EXHAUSTED")
            for where, parameter, call_cap, budget_cap, source_cap in (
                ("day=?", day, limits["daily_model_calls"], limits["daily_budget_microusd"], limits["daily_source_requests"]),
                # Four fixed feeds plus two explicitly registered MCP reads,
                # each reserving the bridge's twelve-request transport ceiling.
                ("job=?", job, limits["run_model_calls"], limits["run_budget_microusd"],
                 limits.get("run_source_requests", 28)),
            ):
                used = db.execute("SELECT coalesce(sum(model_calls),0),coalesce(sum(reserved_microusd),0),coalesce(sum(source_requests),0) FROM effects WHERE " + where, (parameter,)).fetchone()
                if (used[0] + model_calls > call_cap or used[1] + micros > budget_cap
                        or used[2] + source_requests > source_cap):
                    raise ServiceError("BUDGET_EXHAUSTED")
            db.execute("INSERT INTO effects VALUES (?,?,?,?,?,?,?,?,NULL,NULL,NULL)",
                       (job, name, identity, "started", day, model_calls, source_requests, micros))
            self._event(db, job, "effect_reserved", {"step": name, "reserved_microusd": micros,
                                                    "model_calls": model_calls, "source_requests": source_requests})
            return None

    def completed_effect(self, job: str, name: str, inputs: dict):
        """Replay without resolving a credential or reserving another attempt."""
        with self._connect() as db:
            row = db.execute("SELECT * FROM effects WHERE job=? AND name=?", (job, name)).fetchone()
            if row is None:
                return None
            if row["input_digest"] != digest(inputs):
                raise ServiceError("EFFECT_INPUT_CHANGED")
            if row["state"] != "completed":
                raise ServiceError("EFFECT_RECONCILIATION_REQUIRED")
            output = _decode(row["output"])
            if digest(output) != row["output_digest"]:
                raise ServiceError("EFFECT_RECEIPT_CORRUPT")
            return output

    def complete_effect(self, job: str, name: str, output: dict):
        if len(canonicalize(output)) > 2_000_000:
            raise ServiceError("EFFECT_OUTPUT_LIMIT")
        with self._connect() as db:
            row = db.execute("SELECT state FROM effects WHERE job=? AND name=?", (job, name)).fetchone()
            if row is None or row[0] != "started":
                raise ServiceError("EFFECT_NOT_STARTED")
            db.execute("UPDATE effects SET state='completed',output=?,output_digest=? WHERE job=? AND name=?",
                       (_encode(output), digest(output), job, name))
            self._event(db, job, "effect_completed", {"step": name, "output_digest": digest(output)})

    def cached_source(self, key: str):
        with self._connect() as db:
            row = db.execute("SELECT e.state,e.output,e.output_digest FROM source_slots s JOIN effects e ON e.job=s.job AND e.name=s.name WHERE s.key=?", (key,)).fetchone()
            if row is None:
                return None
            if row["state"] != "completed":
                raise ServiceError("SOURCE_OUTCOME_UNRESOLVED")
            result = _decode(row["output"])
            if digest(result) != row["output_digest"]:
                raise ServiceError("SOURCE_CACHE_CORRUPT")
            return result

    def claim_source(self, key: str, source: str, job: str, name: str):
        with self._connect() as db:
            now = int(time.time())
            if source == "arxiv":
                last = db.execute("SELECT max(reserved) FROM source_slots WHERE source='arxiv'").fetchone()[0]
                if last is not None and now - last < 3:
                    raise ServiceError("SOURCE_RATE_LIMIT")
            try:
                db.execute("INSERT INTO source_slots VALUES (?,?,?,?,?)", (key, source, job, name, now))
            except sqlite3.IntegrityError:
                raise ServiceError("SOURCE_ALREADY_RESERVED") from None

    def fail_effect(self, job: str, name: str, code: str, *, ambiguous: bool = True):
        with self._connect() as db:
            db.execute("UPDATE effects SET state=?,reason=? WHERE job=? AND name=? AND state='started'",
                       ("unknown" if ambiguous else "failed", code, job, name))
            db.execute("UPDATE jobs SET status=?,reason=?,updated=? WHERE id=?",
                       ("reconciliation_required" if ambiguous else "failed", code, int(time.time()), job))
            self._event(db, job, "effect_failed", {"step": name, "code": code, "ambiguous": ambiguous})

    def finish(self, job: str, status: str, reason: str | None = None):
        if status not in {"proposal_ready", "rejected", "failed", "published", "reconciliation_required",
                          "retrieval_complete", "execution_complete"}:
            raise ServiceError("INVALID_TERMINAL_STATUS")
        with self._connect() as db:
            # A catch-all caller must not overwrite an uncertain external outcome.
            unknown = db.execute("SELECT 1 FROM effects WHERE job=? AND state IN ('started','unknown')", (job,)).fetchone()
            if unknown:
                status = "reconciliation_required"
            db.execute("UPDATE jobs SET status=?,reason=?,updated=? WHERE id=?",
                       (status, reason, int(time.time()), job))
            self._event(db, job, status, {"reason": reason})

    def pause(self, paused: bool):
        if type(paused) is not bool:
            raise ServiceError("INVALID_PAUSE")
        with self._connect() as db:
            db.execute("UPDATE meta SET value=? WHERE key='paused'", ("true" if paused else "false",))
            self._event(db, None, "pause_changed", {"paused": paused})

    def status(self) -> dict:
        with self._connect() as db:
            rows = [dict(r) for r in db.execute("SELECT id,status,created,updated,reason FROM jobs ORDER BY created DESC LIMIT 100")]
            usage = [dict(r) for r in db.execute("SELECT day,sum(model_calls) model_calls,sum(source_requests) source_request_reservations,sum(reserved_microusd) reserved_microusd FROM effects GROUP BY day ORDER BY day DESC LIMIT 7")]
            return {"schema": "research-service-status/v1", "production_ready": False,
                    "paused": db.execute("SELECT value FROM meta WHERE key='paused'").fetchone()[0] == "true",
                    "jobs": rows, "usage": usage,
                    "last_event": db.execute("SELECT coalesce(max(seq),0) FROM events").fetchone()[0]}

    def inspect(self, job: str) -> dict:
        with self._connect() as db:
            row = db.execute("SELECT * FROM jobs WHERE id=?", (job,)).fetchone()
            if row is None:
                raise ServiceError("JOB_NOT_FOUND")
            return {"job": dict(row), "steps": {r["name"]: _decode(r["output"]) for r in db.execute("SELECT name,output FROM steps WHERE job=?", (job,))},
                    "effects": [dict(r) for r in db.execute("SELECT name,state,day,model_calls,source_requests,reserved_microusd,reason FROM effects WHERE job=?", (job,))]}

    @contextlib.contextmanager
    def _history_snapshot(self):
        """Read one live-WAL snapshot without SQL writes or journal reconfiguration.

        This is not immutable-file verification: SQLite may manage read-side
        WAL coordination. No workflow state, receipts or artifacts are changed.
        """
        self._safe_paths()
        db = sqlite3.connect(self.path.as_uri() + "?mode=ro", uri=True, timeout=5)
        db.row_factory = sqlite3.Row
        try:
            db.execute("PRAGMA query_only=ON")
            db.execute("BEGIN")
            yield db
        except sqlite3.DatabaseError:
            raise ServiceError("STATE_DATABASE_ERROR") from None
        finally:
            db.close()

    @staticmethod
    def _history_value(raw, expected, maximum):
        try:
            if not isinstance(raw, str) or len(raw.encode("utf-8")) > maximum:
                raise ValueError
            value = _decode(raw)
            if type(value) is not dict or digest(value) != expected:
                raise ValueError
            return value
        except (ValueError, TypeError, UnicodeError, RecursionError):
            raise ServiceError("HISTORY_DIGEST_MISMATCH") from None

    @classmethod
    def _history_manifest(cls, row):
        value = cls._history_value(row["manifest"], row["digest"], 1_000_000)
        if (value.get("schema") != "research-work/v1"
                or not isinstance(value.get("baseline_commit"), str)
                or not re.fullmatch(r"[0-9a-f]{40}", value["baseline_commit"])
                or type(value.get("fixture")) is not bool
                or not isinstance(value.get("corpus_digest"), str)
                or not re.fullmatch(r"sha256:[0-9a-f]{64}", value["corpus_digest"])):
            raise ServiceError("HISTORY_MANIFEST_INVALID")
        validate(value.get("schedule"), SCHEDULE, "HISTORY_MANIFEST_INVALID")
        return value

    @classmethod
    def _history_step(cls, db, row, name):
        step = db.execute("SELECT * FROM steps WHERE job=? AND name=?", (row["id"], name)).fetchone()
        if step is None:
            return None
        if step["input_digest"] != digest({"manifest": row["digest"]}):
            raise ServiceError("HISTORY_INPUT_MISMATCH")
        return cls._history_value(step["output"], step["output_digest"], 2_000_000)

    @classmethod
    def _history_report(cls, db, row, manifest):
        report = cls._history_step(db, row, "report")
        if report is None:
            return None
        if (report.get("schema") != "research-service-review/v1"
                or report.get("job") != row["id"]
                or report.get("baseline_commit") != manifest["baseline_commit"]
                or report.get("corpus_digest") != manifest["corpus_digest"]
                or type(report.get("fixture")) is not bool
                or report["fixture"] != manifest["fixture"]):
            raise ServiceError("HISTORY_REPORT_BINDING_MISMATCH")
        validate(report.get("research"), RESEARCH_SCHEMA, "HISTORY_RESEARCH_INVALID")
        return report

    @classmethod
    def _history_rows(cls, db, current_job):
        # Refuse an incomplete scan rather than call an unseen candidate novel.
        rows = db.execute("SELECT * FROM jobs WHERE id<>? AND status IN (?,?,?,?) "
                          "ORDER BY updated DESC,id ASC LIMIT ?",
                          (current_job, *_TERMINAL_HISTORY, MAX_HISTORY_JOBS + 1))
        for index, row in enumerate(rows):
            if index == MAX_HISTORY_JOBS:
                raise ServiceError("HISTORY_SCAN_LIMIT")
            # Failed discovery jobs share the store but never enter author memory
            # or candidate novelty checks. Validate their identity before excluding.
            value = cls._history_value(row["manifest"], row["digest"], 1_000_000)
            if value.get("schema") == "retrieval-work/v1":
                cls._retrieval_manifest(row)
                continue
            yield row

    @classmethod
    def _retrieval_manifest(cls, row):
        value = cls._history_value(row["manifest"], row["digest"], 1_000_000)
        validate(value.get("schedule"), SCHEDULE, "HISTORY_MANIFEST_INVALID")
        start, end = value.get("window_start"), value.get("window_end")
        if (value.get("schema") != "retrieval-work/v1"
                or value["schedule"].get("mode") != "retrieve"
                or type(value.get("fixture")) is not bool
                or type(start) is not int or type(end) is not int
                or start < 0 or end != start + 86400 or end % 86400):
            raise ServiceError("HISTORY_MANIFEST_INVALID")
        return value

    def prior_retrieval(self, current_job: str, manifest: dict, limit: int = 7) -> list[dict]:
        """Verified completed daily digests, never same/future-day or live/fixture mixing.

        This is observation history, not accepted knowledge. The caller freezes
        this selection in a checkpoint before constructing a digest.
        """
        if type(limit) is not int or not 1 <= limit <= 7:
            raise ServiceError("INVALID_RETRIEVAL_HISTORY_LIMIT")
        with self._history_snapshot() as db:
            current = db.execute("SELECT * FROM jobs WHERE id=?", (current_job,)).fetchone()
            if current is None:
                raise ServiceError("JOB_NOT_FOUND")
            bound = self._retrieval_manifest(current)
            if digest(manifest) != current["digest"]:
                raise ServiceError("HISTORY_CURRENT_INPUT_CHANGED")
            rows = db.execute("SELECT * FROM jobs WHERE id<>? AND status='retrieval_complete' "
                              "ORDER BY id LIMIT ?", (current_job, MAX_HISTORY_JOBS + 1))
            eligible = []
            for index, row in enumerate(rows):
                if index == MAX_HISTORY_JOBS:
                    raise ServiceError("HISTORY_SCAN_LIMIT")
                previous = self._retrieval_manifest(row)
                if (previous["fixture"] != bound["fixture"]
                        or digest(previous["schedule"]) != digest(bound["schedule"])
                        or previous["window_end"] >= bound["window_end"]):
                    continue
                report = self._history_step(db, row, "report")
                if (report is None or report.get("schema") != "research-retrieval-report/v1"
                        or report.get("job") != row["id"]
                        or report.get("disposition") != "retrieval_only"
                        or report.get("evidence_qualified") is not False
                        or report.get("fixture") != bound["fixture"]
                        or report.get("schedule_id") != bound["schedule"]["id"]
                        or report.get("window_start") != previous["window_start"]
                        or report.get("window_end") != previous["window_end"]
                        or not isinstance(report.get("context_digest"), dict)
                        or len(canonicalize(report["context_digest"])) > 32768):
                    raise ServiceError("HISTORY_REPORT_BINDING_MISMATCH")
                eligible.append((previous["window_end"], row["id"], report["context_digest"]))
            result, days = [], set()
            for end, _job, packet in sorted(eligible, key=lambda item: (-item[0], item[1])):
                if end in days:
                    continue
                days.add(end)
                result.append({"window_end": end, "context_digest": packet})
                if len(result) == limit:
                    break
            return result

    def prior_feedback(self, current_job: str, manifest: dict, limit: int = 5) -> dict:
        """Small hypothesis archive, not novelty, accepted knowledge or judge feedback.

        Match the entire schedule, baseline and fixture/live mode. Complete
        entries are packed newest-first; omissions are counted, never truncated.
        The caller checkpoints this once and must not expose it to evaluators.
        """
        if type(limit) is not int or not 1 <= limit <= 5:
            raise ServiceError("INVALID_FEEDBACK_LIMIT")
        with self._history_snapshot() as db:
            current = db.execute("SELECT * FROM jobs WHERE id=?", (current_job,)).fetchone()
            if current is None:
                raise ServiceError("JOB_NOT_FOUND")
            bound = self._history_manifest(current)
            if digest(manifest) != current["digest"]:
                raise ServiceError("HISTORY_CURRENT_INPUT_CHANGED")
            result = {"schema": "research-prior-feedback/v1", "authority": "none",
                      "semantic_novelty_measured": False, "baseline_commit": bound["baseline_commit"],
                      "schedule_digest": digest(bound["schedule"]), "fixture": bound["fixture"],
                      "entries": [], "omitted": {"limit": 0, "budget": 0, "without_report": 0}}
            for row in self._history_rows(db, current_job):
                previous = self._history_manifest(row)
                if (previous["baseline_commit"] != bound["baseline_commit"]
                        or previous["fixture"] != bound["fixture"]
                        or digest(previous["schedule"]) != result["schedule_digest"]):
                    continue
                report = self._history_report(db, row, previous)
                if report is None:
                    result["omitted"]["without_report"] += 1
                    continue
                reason = row["reason"]
                if reason is not None and (not isinstance(reason, str)
                                          or not re.fullmatch(r"[A-Z0-9_]{1,100}", reason)):
                    raise ServiceError("HISTORY_REASON_INVALID")
                research = report["research"]
                entry = {"job": row["id"], "report_digest": digest(report),
                         "hypothesis": research["hypothesis"], "test_plan": research["test_plan"],
                         "outcome": row["status"], "reason": reason,
                         "evidence_refs": sorted({citation["evidence_id"] for claim in research["claims"]
                                                  for citation in claim["citations"]})}
                if len(result["entries"]) >= limit:
                    result["omitted"]["limit"] += 1
                    continue
                result["entries"].append(entry)
                # Leave room for bounded omission counters growing to 10000.
                if len(canonicalize(result)) > MAX_FEEDBACK_BYTES - 15:
                    result["entries"].pop()
                    result["omitted"]["budget"] += 1
            if len(canonicalize(result)) > MAX_FEEDBACK_BYTES:
                raise ServiceError("FEEDBACK_BUDGET_EXCEEDED")
            return result

    def candidate_seen(self, current_job: str, baseline_commit: str, path: str,
                       text_sha256: str) -> bool:
        """Exact prior proposed bytes only; not semantic novelty or acceptance."""
        if (not isinstance(baseline_commit, str) or not re.fullmatch(r"[0-9a-f]{40}", baseline_commit)
                or not isinstance(path, str) or not re.fullmatch(r"skills/[a-z][a-z0-9_-]*/SKILL\.md", path)
                or not isinstance(text_sha256, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", text_sha256)):
            raise ServiceError("INVALID_CANDIDATE_IDENTITY")
        found = False
        with self._history_snapshot() as db:
            current = db.execute("SELECT * FROM jobs WHERE id=?", (current_job,)).fetchone()
            if current is None:
                raise ServiceError("JOB_NOT_FOUND")
            bound = self._history_manifest(current)
            if bound["baseline_commit"] != baseline_commit:
                raise ServiceError("HISTORY_CURRENT_INPUT_CHANGED")
            for row in self._history_rows(db, current_job):
                previous = self._history_manifest(row)
                if (row["status"] == "failed" or previous["baseline_commit"] != baseline_commit
                        or previous["fixture"] != bound["fixture"]):
                    continue
                report = self._history_report(db, row, previous)
                if report is None:
                    continue
                proposal = validate(report.get("proposal"), EDIT_SCHEMA, "HISTORY_PROPOSAL_INVALID")
                if proposal["path"] != path:
                    continue
                corpus = self._history_step(db, row, "corpus")
                if corpus is None or digest(corpus) != previous["corpus_digest"]:
                    raise ServiceError("HISTORY_CORPUS_MISMATCH")
                documents = corpus.get("documents")
                if (type(documents) is not list or not 1 <= len(documents) <= 32
                        or any(type(item) is not dict for item in documents)):
                    raise ServiceError("HISTORY_CORPUS_MISMATCH")
                matching = [item for item in documents if item.get("path") == path]
                if len(matching) != 1:
                    raise ServiceError("HISTORY_CORPUS_MISMATCH")
                original = matching[0].get("text")
                if (not isinstance(original, str) or len(original.encode("utf-8")) > 131072
                        or sha256_bytes(original.encode("utf-8")) != matching[0].get("sha256")
                        or original.count(proposal["old_text"]) != 1):
                    raise ServiceError("HISTORY_PROPOSAL_INVALID")
                changed = original.replace(proposal["old_text"], proposal["new_text"], 1)
                if changed == original or len(changed.encode("utf-8")) > 131072:
                    raise ServiceError("HISTORY_PROPOSAL_INVALID")
                found = found or sha256_bytes(changed.encode("utf-8")) == text_sha256
        return found

    def backup(self, target: Path):
        """Inspection backup only. It does not authorize replacing a live writer."""
        target = target.absolute()
        if target.exists() or target.is_symlink() or target.parent.resolve() != target.parent:
            raise ServiceError("BACKUP_TARGET_MUST_BE_NEW")
        fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        self._safe_paths()
        with sqlite3.connect(self.path.as_uri() + "?mode=ro", uri=True) as src, sqlite3.connect(target) as dst:
            deadline = time.monotonic() + 30
            def progress(_status, _remaining, _total):
                if time.monotonic() > deadline:
                    raise ServiceError("BACKUP_DEADLINE")
            src.backup(dst, pages=128, progress=progress, sleep=0.05)
            if dst.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ServiceError("BACKUP_INTEGRITY")
