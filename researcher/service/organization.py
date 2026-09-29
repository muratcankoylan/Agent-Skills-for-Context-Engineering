"""Foreground coordination of retrieval and one shared-budget proposal study.

Private receipts are recovery records, never knowledge promotion or budget
authority. There is no provider call, credential discovery or publishing here.
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import json
import os
from pathlib import Path
import re
import signal
import threading
import time

from researcher.scripts.schema_contract import canonicalize, parse_json_strict
from . import research_pipeline as pipeline
from .agents_evals import _dataset
from .contracts import ServiceError, array, digest, integer, load_config, obj, string, validate
from .environment import _stable_bytes, credential_reader, read_config_file, read_env_file
from .knowledge import retrieve_corpus
from .openai_campaign import Campaign, implementation_digest as campaign_implementation
from .retrieval_setup import configured_credential_names
from .store import Store
from .workflow import Workflow, git_head, implementation, make_manifest
from .tracing import annotate, current_span, traced
from .trace_pump import TracePump
from .shutdown import StopRequested, check_stop, stop_scope

MAX_JOBS = 10000
MAX_SOURCE_MANIFEST_BYTES = 16 * 1024 * 1024
POLICY_SCHEMA = obj({
    "schema": {"const": "research-organization-policy/v1"},
    "schedules": array(obj({"schedule_id": string(64, pattern=r"^[a-z][a-z0-9_-]{0,63}$"),
        "skills": array(string(96, pattern=r"^[a-z][a-z0-9-]{0,95}$"), 3, 1)}), 10, 1),
    "poll_seconds": integer(5, 3600), "max_source_jobs_per_cycle": integer(1, 4),
    "maximum_age_seconds": integer(60, 604800),
    "evaluation": obj({"seed": integer(0, 2**31 - 1), "replications": integer(1, 10),
                       "max_sessions": integer(1, 480)}),
    "research_profile": {"const": "captured-actions-v1"},
}, required=["schema", "schedules", "poll_seconds", "max_source_jobs_per_cycle",
             "maximum_age_seconds", "evaluation"])
_HEX = re.compile(r"[0-9a-f]{64}\Z")
_SHA = re.compile(r"sha256:[0-9a-f]{64}\Z")
_OUTCOMES = {"abstained", "no_proposal", "structural_validation_failed", "awaiting_dataset",
             "evaluated_not_accepted", "duplicate_candidate", "failed"}


def validate_policy(policy, config):
    validate(policy, POLICY_SCHEMA, "ORGANIZATION_POLICY_INVALID")
    config = load_config(canonicalize(config).decode())
    if (config["models"] or config["limits"]["daily_model_calls"]
            or config["limits"]["run_model_calls"] or config["github"]["enabled"]
            or config["github"]["notify"] or config.get("mcp_tools")
            or any(s.get("mode") != "retrieve" or s.get("mcp_reads") for s in config["schedules"])):
        raise ServiceError("ORGANIZATION_RETRIEVAL_ONLY_REQUIRED")
    names = [item["schedule_id"] for item in policy["schedules"]]
    if len(set(names)) != len(names) or set(names) != {s["id"] for s in config["schedules"]}:
        raise ServiceError("ORGANIZATION_SCHEDULE_COVERAGE")
    return parse_json_strict(canonicalize(policy).decode())


def _code(error):
    value = getattr(error, "code", "ORGANIZATION_LOCAL_FAILURE")
    return value if isinstance(value, str) and re.fullmatch(r"[A-Z0-9_]{1,100}", value) else "ORGANIZATION_LOCAL_FAILURE"


def _paused(store):
    with store._history_snapshot() as db:
        values = dict(db.execute("SELECT key,value FROM meta WHERE key IN ('paused','config_digest')"))
    if values.get("config_digest") != digest(store.config) or values.get("paused") not in {"true", "false"}:
        raise ServiceError("ORGANIZATION_STORE_BINDING_CHANGED")
    return values["paused"] == "true"


def _inputs(root, source_store, campaign, policy, dataset, fixture):
    schedules = {s["id"]: s for s in source_store.config["schedules"]}
    corpus = {item["schedule_id"]: digest(retrieve_corpus(root, schedules[item["schedule_id"]]["query"],
        item["skills"], 65536)) for item in policy["schedules"]}
    return {"schema": "research-organization-input/v1", "authority": "none",
        "root_digest": digest(str(root)), "baseline_commit": git_head(root),
        "implementation_digest": implementation(root), "corpus_digests": corpus,
        "source_directory_digest": digest(str(source_store.directory)),
        "source_config_digest": digest(source_store.config),
        "authority_directory_digest": digest(str(campaign.directory)),
        "authority_config_digest": digest(campaign.store.config),
        "campaign_implementation_digest": campaign_implementation(),
        "runtime": campaign.execution_identity(),
        "policy": policy, "dataset": dataset, "dataset_digest": digest(dataset), "fixture": fixture}


class Organization:
    """One local coordinator; creation never initializes either supplied Store."""

    def __init__(self, directory: Path, root: Path, source_store: Store, campaign: Campaign,
                 *, policy: dict, dataset: dict | None = None, fixture: bool = False,
                 _initialize: bool = False):
        if (not isinstance(source_store, Store) or not isinstance(campaign, Campaign)
                or type(fixture) is not bool):
            raise ServiceError("ORGANIZATION_SHARED_AUTHORITY_REQUIRED")
        if fixture and not campaign.fixture_execution:
            raise ServiceError("ORGANIZATION_FIXTURE_PROVIDER_FORBIDDEN")
        if not fixture and campaign.backend != "codex_sdk":
            raise ServiceError("ORGANIZATION_CODEX_SDK_REQUIRED")
        self.root = pipeline._directory(root)
        self.directory = directory.absolute()
        pipeline._directory(self.directory.parent, private=True)
        if (self.directory.resolve() != self.directory or self.directory == self.root
                or self.root in self.directory.parents):
            raise ServiceError("ORGANIZATION_UNSAFE_DIRECTORY")
        self.source_store, self.campaign, self.fixture = source_store, campaign, fixture
        self.tracer = campaign.tracer
        self.policy = validate_policy(policy, source_store.config)
        self.dataset = None if dataset is None else _dataset(dataset)
        if self.dataset is not None and len(self.dataset["tasks"]) * self.policy["evaluation"]["replications"] * 3 > self.policy["evaluation"]["max_sessions"]:
            raise ServiceError("EVAL_SESSION_LIMIT")
        self.dataset = parse_json_strict(canonicalize(self.dataset).decode())
        self.inputs = _inputs(self.root, source_store, campaign, self.policy, self.dataset, fixture)
        pipeline._no_credential(self.inputs, campaign)
        if _initialize:
            if self.directory.exists() or self.directory.is_symlink():
                raise ServiceError("ORGANIZATION_ALREADY_EXISTS")
            self.directory.mkdir(mode=0o700, exist_ok=False)
            (self.directory / "jobs").mkdir(mode=0o700)
            fd = os.open(self.directory / "organization.lock", os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(fd)
            pipeline._write(self.directory / "input.json", pipeline._envelope(self.inputs))
            self._save({"schema": "research-organization-index/v1", "input_digest": digest(self.inputs),
                        "last_clock": 0, "jobs": {}})
        self._load()

    @classmethod
    def initialize(cls, directory, root, source_store, campaign, **kwargs):
        return cls(directory, root, source_store, campaign, _initialize=True, **kwargs)

    @contextlib.contextmanager
    def _lock(self):
        _stable_bytes(self.directory / "organization.lock", maximum=0, private=True, prefix="ORGANIZATION_LOCK")
        fd = os.open(self.directory / "organization.lock", os.O_RDWR | os.O_NOFOLLOW)
        try:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise ServiceError("ORGANIZATION_ALREADY_RUNNING") from None
            yield
        finally:
            os.close(fd)

    def _save(self, index):
        pipeline._write(self.directory / "index.json", pipeline._envelope(index))

    def _load(self):
        pipeline._directory(self.directory, private=True)
        pipeline._directory(self.directory / "jobs", private=True)
        _stable_bytes(self.directory / "organization.lock", maximum=0, private=True, prefix="ORGANIZATION_LOCK")
        pipeline._same(pipeline._record(self.directory / "input.json"), self.inputs, "ORGANIZATION_INPUT_CHANGED")
        pipeline._same(_inputs(self.root, self.source_store, self.campaign, self.policy, self.dataset, self.fixture),
                       self.inputs, "ORGANIZATION_INPUT_CHANGED")
        index = pipeline._record(self.directory / "index.json")
        if (type(index) is not dict or set(index) != {"schema", "input_digest", "last_clock", "jobs"}
                or index["schema"] != "research-organization-index/v1"
                or index["input_digest"] != digest(self.inputs)
                or type(index["last_clock"]) is not int or index["last_clock"] < 0
                or type(index["jobs"]) is not dict or len(index["jobs"]) > MAX_JOBS):
            raise ServiceError("ORGANIZATION_INDEX_INVALID")
        for key, row in index["jobs"].items():
            if (not _HEX.fullmatch(key) or type(row) is not dict
                    or set(row) != {"job", "manifest_digest", "phase", "receipt_digest"}
                    or type(row["job"]) is not str or not 1 <= len(row["job"].encode()) <= 200
                    or not _SHA.fullmatch(str(row["manifest_digest"]))
                    or key != digest({"job": row["job"], "manifest": row["manifest_digest"]})[7:]
                    or row["phase"] not in {"started", "terminal"}
                    or (row["phase"] == "started" and row["receipt_digest"] is not None)):
                raise ServiceError("ORGANIZATION_INDEX_INVALID")
            child = self.directory / "jobs" / key
            pipeline._directory(child, private=True)
            if row["phase"] == "terminal":
                self._receipt(key, row)
        return index

    def _receipt(self, key, row):
        value = pipeline._record(self.directory / "jobs" / key / "receipt.json")
        if (type(value) is not dict or set(value) != {"schema", "authority", "input_digest",
                "job_digest", "source_manifest_digest", "outcome", "code", "pipeline_result_digest"}
                or value["schema"] != "research-organization-job/v1" or value["authority"] != "none"
                or value["input_digest"] != digest(self.inputs) or value["job_digest"] != digest(row["job"])
                or value["source_manifest_digest"] != row["manifest_digest"]
                or value["outcome"] not in _OUTCOMES | {"source_not_eligible"}
                or value["code"] is not None and not re.fullmatch(r"[A-Z0-9_]{1,100}", str(value["code"]))
                or value["pipeline_result_digest"] is not None and not _SHA.fullmatch(str(value["pipeline_result_digest"]))
                or row["receipt_digest"] is not None and digest(value) != row["receipt_digest"]):
            raise ServiceError("ORGANIZATION_RECEIPT_INVALID")
        if value["pipeline_result_digest"] is not None:
            result = pipeline._record(self.directory / "jobs" / key / "pipeline/result.json")
            if digest(result) != value["pipeline_result_digest"]:
                raise ServiceError("ORGANIZATION_PIPELINE_RESULT_CHANGED")
        return value

    def status(self):
        index = self._load()
        counts = {}
        for key, row in index["jobs"].items():
            outcome = self._receipt(key, row)["outcome"] if row["phase"] == "terminal" else "interrupted_or_running"
            counts[outcome] = counts.get(outcome, 0) + 1
        return {"schema": "research-organization-status/v1", "authority": "none", "production_ready": False,
            "organization_digest": digest(self.inputs), "jobs": len(index["jobs"]), "outcomes": counts,
            "source_paused": _paused(self.source_store), "campaign_paused": _paused(self.campaign.store),
            "fixture": self.fixture, "publication": "disabled", "budget": self.campaign.status()}

    def _source_rows(self):
        rows, total = [], 0
        with self.source_store._history_snapshot() as db:
            for number, row in enumerate(db.execute("SELECT id,manifest,digest,status,created FROM jobs ORDER BY created,id LIMIT ?", (MAX_JOBS + 1,))):
                total += len(row["manifest"].encode())
                if number >= MAX_JOBS or total > MAX_SOURCE_MANIFEST_BYTES:
                    raise ServiceError("ORGANIZATION_SOURCE_SCAN_LIMIT")
                manifest = Store._retrieval_manifest(row)
                if (manifest["schedule"] not in self.source_store.config["schedules"]
                        or manifest["config_digest"] != digest(self.source_store.config)
                        or manifest["fixture"] != self.fixture
                        or row["status"] not in {"queued", "running", "retrieval_complete",
                            "retrieval_partial", "failed", "reconciliation_required"}):
                    raise ServiceError("ORGANIZATION_SOURCE_BINDING_CHANGED")
                key = digest({"job": row["id"], "manifest": row["digest"]})[7:]
                rows.append({**dict(row), "key": key, "parsed": manifest})
        return rows

    def _finish(self, index, key, outcome, *, code=None, result_digest=None):
        row = index["jobs"][key]
        value = {"schema": "research-organization-job/v1", "authority": "none",
            "input_digest": digest(self.inputs), "job_digest": digest(row["job"]),
            "source_manifest_digest": row["manifest_digest"], "outcome": outcome,
            "code": code, "pipeline_result_digest": result_digest}
        pipeline._write(self.directory / "jobs" / key / "receipt.json", pipeline._envelope(value))
        row.update(phase="terminal", receipt_digest=digest(value))
        self._save(index)
        return value

    def _select(self, index, rows):
        available = {r["key"]: r for r in rows}
        for key, row in index["jobs"].items():
            if key not in available:
                raise ServiceError("ORGANIZATION_SOURCE_JOB_REMOVED")
            if row["phase"] == "started":
                return available[key]
        return next((row for row in rows if row["key"] not in index["jobs"]
                     and row["status"] not in {"queued", "running"}), None)

    def _learning_sources(self, index, key):
        """Freeze the bounded archive selection before the first research call.

        Restart validates these same references, never refreshes a paid study's
        context from a newer archive. The underlying pipeline replays sources.
        """
        from .sdk_learning import MAX_SOURCES
        path = self.directory / "jobs" / key / "learning-sources.json"
        if path.exists() or path.is_symlink():
            saved = pipeline._record(path)
        else:
            available = {r["key"]: r for r in self._source_rows()}
            previous = []
            for identity, row in index["jobs"].items():
                if identity == key or row["phase"] != "terminal":
                    continue
                receipt = self._receipt(identity, row)
                if receipt["pipeline_result_digest"] is not None:
                    previous.append(identity)
            previous.sort(key=lambda k: (available[k]["parsed"]["window_end"], available[k]["created"], k), reverse=True)
            saved = {"schema": "organization-learning-selection/v1", "input_digest": digest(self.inputs),
                "job_key": key, "sources": [{"key": identity,
                    "receipt_digest": index["jobs"][identity]["receipt_digest"]}
                    for identity in previous[:MAX_SOURCES]], "omitted": max(0, len(previous) - MAX_SOURCES)}
            pipeline._write(path, pipeline._envelope(saved))
        if (type(saved) is not dict or set(saved) != {"schema", "input_digest", "job_key", "sources", "omitted"}
                or saved["schema"] != "organization-learning-selection/v1" or saved["input_digest"] != digest(self.inputs)
                or saved["job_key"] != key or type(saved["sources"]) is not list or len(saved["sources"]) > MAX_SOURCES
                or type(saved["omitted"]) is not int or not 0 <= saved["omitted"] <= MAX_JOBS):
            raise ServiceError("ORGANIZATION_LEARNING_CHANGED")
        sources, seen = [], set()
        for ref in saved["sources"]:
            if (type(ref) is not dict or set(ref) != {"key", "receipt_digest"}
                    or not isinstance(ref["key"], str) or ref["key"] == key or ref["key"] in seen
                    or ref["key"] not in index["jobs"]):
                raise ServiceError("ORGANIZATION_LEARNING_CHANGED")
            row = index["jobs"][ref["key"]]
            if row["phase"] != "terminal" or row["receipt_digest"] != ref["receipt_digest"]:
                raise ServiceError("ORGANIZATION_LEARNING_CHANGED")
            self._receipt(ref["key"], row)
            seen.add(ref["key"])
            sources.append(self.directory / "jobs" / ref["key"] / "pipeline")
        return sources, saved["omitted"]

    def _run(self, index, row, *, live, now, runner):
        key = row["key"]
        child = self.directory / "jobs" / key
        if key not in index["jobs"]:
            if len(index["jobs"]) >= MAX_JOBS:
                raise ServiceError("ORGANIZATION_JOB_LIMIT")
            if child.exists() or child.is_symlink():
                raise ServiceError("ORGANIZATION_PARTIAL_ADMISSION")
            child.mkdir(mode=0o700)
            index["jobs"][key] = {"job": row["id"], "manifest_digest": row["digest"],
                                  "phase": "started", "receipt_digest": None}
            self._save(index)
        receipt = child / "receipt.json"
        if receipt.exists() or receipt.is_symlink():
            saved = self._receipt(key, index["jobs"][key])
            index["jobs"][key].update(phase="terminal", receipt_digest=digest(saved))
            self._save(index)
            return saved
        if (row["status"] != "retrieval_complete"
                or not 30 <= now - row["parsed"]["window_end"] <= self.policy["maximum_age_seconds"]):
            return self._finish(index, key, "source_not_eligible", code="SOURCE_NOT_FRESH_COMPLETE")
        skills = next(item["skills"] for item in self.policy["schedules"]
                      if item["schedule_id"] == row["parsed"]["schedule"]["id"])
        try:
            learning_sources, learning_omissions = self._learning_sources(index, key)
            profile = ({"research_profile": self.policy["research_profile"]}
                       if "research_profile" in self.policy else {})
            result = runner(self.root, self.source_store, row["id"], child / "pipeline",
                campaign=self.campaign, skills=skills, dataset=self.dataset,
                **self.policy["evaluation"], maximum_age_seconds=self.policy["maximum_age_seconds"],
                fixture=self.fixture, live=live, now=now if self.fixture else None,
                learning_sources=learning_sources, learning_omissions=learning_omissions, **profile)
            if (type(result) is not dict or result.get("schema") != "research-pipeline-result/v1"
                    or result.get("authority") != "none" or result.get("outcome") not in _OUTCOMES
                    or result.get("fixture") is not self.fixture or result.get("publication") != "not_attempted"
                    or result.get("production_ready") is not False
                    or result.get("scientific_improvement_demonstrated") is not False):
                raise ServiceError("ORGANIZATION_PIPELINE_RESULT_INVALID")
            pipeline._same(pipeline._record(child / "pipeline/result.json"), result,
                           "ORGANIZATION_PIPELINE_RESULT_CHANGED")
            error = None
            if result["outcome"] == "failed":
                detail = result.get("detail")
                error = detail.get("code") if isinstance(detail, dict) else None
                if not isinstance(error, str) or not re.fullmatch(r"[A-Z0-9_]{1,100}", error):
                    error = "ORGANIZATION_PIPELINE_FAILURE"
        except Exception as error:
            if isinstance(error, ServiceError) and error.code == "PIPELINE_CHECKPOINT_INTERRUPTED":
                # The pipeline's durable phase receipts decide whether any
                # effect can resume. Do not replace a committed result merely
                # because its local terminal checkpoint was interrupted.
                raise
            return self._finish(index, key, "failed", code=_code(error))
        # A receipt may commit before its index checkpoint. Storage failures
        # must escape so restart reconciles that receipt, never overwrite a
        # successful pipeline outcome with a fabricated execution failure.
        return self._finish(index, key, result["outcome"], code=error, result_digest=digest(result))

    @traced("organization.cycle")
    def _cycle(self, workflow, *, live, now, runner):
        if (not isinstance(workflow, Workflow) or workflow.store is not self.source_store
                or workflow.root != self.root or type(live) is not bool
                or not self.fixture and (not live or not workflow.live)):
            raise ServiceError("ORGANIZATION_EXECUTION_NOT_AUTHORIZED")
        if runner is not pipeline.run_pipeline and not self.fixture:
            raise ServiceError("ORGANIZATION_TEST_ADAPTER_FORBIDDEN")
        index = self._load()
        current = pipeline._clock(now)
        if current < index["last_clock"]:
            raise ServiceError("CLOCK_MOVED_BACKWARDS")
        index["last_clock"] = current
        self._save(index)
        self.source_store.observe_clock(current)
        summary = {"schema": "research-organization-cycle/v1", "organization_digest": digest(self.inputs),
                   "at": current, "source_admissions": 0, "source_executions": 0,
                   "research_admissions": 0, "job": None, "paused": False, "fixture": self.fixture}
        if _paused(self.source_store) or _paused(self.campaign.store):
            summary["paused"] = True
            return summary
        check_stop()
        rows = self._source_rows()
        selected = self._select(index, rows)
        if selected is None:
            # Same UTC slot/job ID and ingestion lag as admit_due. This bounded
            # variant also makes the fixture class explicit in each manifest.
            maximum = self.policy["max_source_jobs_per_cycle"]
            with self.source_store.worker_lock():
                for schedule in self.source_store.config["schedules"]:
                    check_stop()
                    slot = current // schedule["interval_seconds"] * schedule["interval_seconds"]
                    if current - slot < 30:
                        continue
                    manifest = make_manifest(self.root, self.source_store.config, schedule,
                                             fixture=self.fixture, window_end=slot)
                    if self.source_store.enqueue(f"{schedule['id']}:{slot}", manifest):
                        summary["source_admissions"] += 1
                    if summary["source_admissions"] >= maximum:
                        break
            summary["source_executions"] = len(workflow.drain(maximum))
            selected = self._select(index, self._source_rows())
        if selected is not None:
            check_stop()
            if _paused(self.source_store) or _paused(self.campaign.store):
                summary["paused"] = True
                return summary
            # No source lock is held: run_pipeline owns its capture replay lock,
            # then each paid effect is fenced by the supplied Campaign's lock.
            summary["job"] = self._run(index, selected, live=live, now=current, runner=runner)
            summary["research_admissions"] = int(summary["job"]["outcome"] != "source_not_eligible")
        outcome = summary["job"]["outcome"] if summary["job"] is not None else None
        if outcome in {"failed", "structural_validation_failed"}:
            current_span().set_status("error")
            annotate(outcome="failed", items=1)
        else:
            annotate(outcome="abstained" if outcome in {"abstained", "no_proposal"}
                else "rejected" if outcome in {"duplicate_candidate", "source_not_eligible"}
                else "prepared" if outcome == "awaiting_dataset" else "completed",
                items=int(summary["job"] is not None))
        return summary

    @staticmethod
    def _check_pumps(pumps):
        # Only the trusted caller may supply these capabilities. No policy,
        # model action, receipt or provider response constructs an exporter.
        if (type(pumps) is not tuple or len(pumps) > 2
                or any(type(pump) is not TracePump for pump in pumps)):
            raise ServiceError("ORGANIZATION_INVALID_TRACE_PUMPS")

    @staticmethod
    def _deliver(pumps, emit):
        for number, pump in enumerate(pumps):
            result = pump.tick()
            if emit is not None:
                try:
                    emit({"event": "trace_delivery", "journal": number, **result})
                except Exception:
                    # A closed stdout/progress sink is not a research failure.
                    # Preserve the original result/exception and the other
                    # journal's delivery opportunity. Durable receipts survive.
                    pass

    def cycle(self, workflow, *, live=False, now=None, pipeline_runner=None,
              trace_pumps=(), progress=None):
        self._check_pumps(trace_pumps)
        with self._lock():
            try:
                return self._cycle(workflow, live=live, now=now, runner=pipeline_runner or pipeline.run_pipeline)
            finally:
                # The decorated cycle span is now closed, including on failure.
                # Telemetry cannot change a job receipt or spending reservation.
                self._deliver(trace_pumps, progress)

    def serve(self, workflow, *, live=False, max_cycles=None, stopped=None,
              pipeline_runner=None, progress=None, clock=time.time, trace_pumps=()):
        self._check_pumps(trace_pumps)
        if (max_cycles is not None and (type(max_cycles) is not int or not 1 <= max_cycles <= 1000000)
                or self.fixture and max_cycles is None):
            raise ServiceError("ORGANIZATION_INVALID_CYCLE_LIMIT")
        stop = threading.Event() if stopped is None else stopped
        emit = progress or (lambda value: print(json.dumps(value, sort_keys=True), flush=True))
        completed = 0
        with self._lock(), stop_scope(stop):
            while not stop.is_set() and (max_cycles is None or completed < max_cycles):
                try:
                    try:
                        result = self._cycle(workflow, live=live, now=int(clock()),
                                             runner=pipeline_runner or pipeline.run_pipeline)
                    finally:
                        self._deliver(trace_pumps, emit)
                except StopRequested:
                    # Nonterminal phase/effect checkpoints remain resumable.
                    # Never manufacture a failed research/evaluation receipt.
                    break
                completed += 1
                emit(result)
                if max_cycles is None or completed < max_cycles:
                    stop.wait(self.policy["poll_seconds"])
        return {"cycles": completed, "stopped": stop.is_set()}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("init", "status", "cycle", "serve"))
    for name in ("state", "repo", "source-state", "source-config", "authority", "policy"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--dataset", type=Path)
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--trace-export", action="store_true",
                        help="Export bounded metadata batches after cycles using explicit Raindrop credentials")
    parser.add_argument("--trace-allow-default-project", action="store_true",
                        help="Approve an explicitly configured default Raindrop project")
    parser.add_argument("--max-cycles", type=int)
    parser.add_argument("--sdk-python", type=Path, required=True)
    args = parser.parse_args(argv)
    os.umask(0o077)
    try:
        running = args.command in {"cycle", "serve"}
        if (running and (not args.live or args.env_file is None)
                or not running and (args.live or args.env_file is not None)
                or args.command != "serve" and args.max_cycles is not None
                or args.trace_export and not running
                or args.trace_allow_default_project and not args.trace_export):
            raise ServiceError("ORGANIZATION_EXPLICIT_EXECUTION_REQUIRED")
        config = load_config(read_config_file(args.source_config))
        policy = parse_json_strict(read_config_file(args.policy))
        dataset = None if args.dataset is None else pipeline._read(args.dataset)
        validate_policy(policy, config)
        values = read_env_file(args.env_file) if running else {}
        # Preflight both capabilities before opening state or admitting work.
        # Presence of a write key alone never enables cloud export.
        pumps = tuple(TracePump(state, credential=values.get("RAINDROP_WRITE_KEY", ""),
            project_id=values.get("RAINDROP_PROJECT_ID", ""), live=args.live,
            allow_default_project=args.trace_allow_default_project)
            for state in (args.authority, args.source_state)) if args.trace_export else ()
        source = Store(args.source_state, config)
        from .codex_campaign import CodexCampaign
        campaign = CodexCampaign(args.authority, credential=values.get("OPENAI_API_KEY"),
                                 sdk_python=str(args.sdk_python), live=args.live)
        constructor = Organization.initialize if args.command == "init" else Organization
        organization = constructor(args.state, args.repo, source, campaign, policy=policy, dataset=dataset)
        if not running:
            result = organization.status()
        else:
            if not values.get("OPENAI_API_KEY"):
                raise ServiceError("OPENAI_CREDENTIAL_REQUIRED")
            workflow = Workflow(source, args.repo, live=True,
                credential=credential_reader(values, configured_credential_names(config, "work")))
            if args.command == "cycle":
                result = organization.cycle(workflow, live=True, trace_pumps=pumps,
                    progress=lambda value: print(json.dumps(value, sort_keys=True), flush=True))
            else:
                stopped = threading.Event()
                for sig in (signal.SIGINT, signal.SIGTERM):
                    signal.signal(sig, lambda *_: stopped.set())
                result = organization.serve(workflow, live=True, max_cycles=args.max_cycles,
                                            stopped=stopped, trace_pumps=pumps)
        print(json.dumps(result, sort_keys=True))
        return 0
    except KeyboardInterrupt:
        print(json.dumps({"error": "ORGANIZATION_INTERRUPTED"}))
        return 130
    except Exception as error:
        print(json.dumps({"error": _code(error)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
