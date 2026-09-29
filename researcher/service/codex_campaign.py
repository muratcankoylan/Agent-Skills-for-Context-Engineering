"""Codex SDK roles using the original cumulative authority, never a new budget.

Versioned SDK tasks and receipts coexist with historical native records. Each
fresh thread has exactly one admitted provider request. Started-but-uncommitted
turns remain quarantined, including a crash before the first provider request.
The deterministic research/citation and evaluation logic is shared, not copied.
"""
from __future__ import annotations

from contextvars import ContextVar
from pathlib import Path
import re
import tempfile
import threading
import time

from researcher.scripts.schema_contract import canonicalize, parse_json_strict, sha256_bytes
from .codex_gateway import Gateway, POLICY, TOKEN_DETAILS, forward, validate_token_details
from .codex_traces import role_for_item, run_traced_worker
from .codex_worker import SDK_VERSION, _validate_request, configuration_identity, run_worker
from .contracts import ServiceError, digest
from .openai_campaign import Campaign, PRICING, _reflected
from .shutdown import check_stop

_REPLAY_ONLY = ContextVar("sdk_origin_replay_only", default=False)


def implementation_digest():
    from .openai_campaign import implementation_digest as campaign_implementation
    names = ("codex_campaign", "codex_gateway", "codex_worker", "codex_traces", "codex_config_boundary", "shutdown")
    return digest({"shared": campaign_implementation(), **{
        name: sha256_bytes(Path(__file__).with_name(name + ".py").read_bytes()) for name in names}})


def sdk_status(store):
    """Private operator projection. Provider completion is not turn completion."""
    jobs = []
    with store._history_snapshot() as db:
        for row in db.execute("SELECT id,manifest,digest,status,reason FROM jobs ORDER BY created,id"):
            manifest = store._history_value(row["manifest"], row["digest"], 1_000_000)
            if manifest.get("schema") != "codex-sdk-work/v1":
                continue
            steps = {step["name"]: store._history_value(step["output"], step["output_digest"], 2_000_000)
                     for step in db.execute("SELECT name,output,output_digest FROM steps WHERE job=?", (row["id"],))}
            started, completed = "sdk-started" in steps, "sdk-result" in steps
            jobs.append({"job_id": row["id"], "backend": "codex_sdk", "status": row["status"],
                "reason": row["reason"], "started": started, "receipt_available": completed,
                "unresolved": started and not completed,
                "thread_id": steps.get("sdk-thread_started", {}).get("thread_id"),
                "turn_id": steps.get("sdk-turn_started", {}).get("turn_id"),
                "remote_stop_confirmed": False})
    return {"schema": "codex-runtime-status/v1", "backend": "codex_sdk", "sdk_version": SDK_VERSION,
        "policy": POLICY, "turns": len(jobs), "completed_turns": sum(job["receipt_available"] for job in jobs),
        "unresolved_turns": sum(job["unresolved"] for job in jobs), "jobs": jobs[-100:],
        "automatic_retry": False, "native_tools_enabled": False}


class CodexCampaign(Campaign):
    backend = "codex_sdk"

    def __init__(self, directory: Path, *, sdk_python: str, credential=None, transport=None,
                 worker=None, live=False, progress=None, now=None, concurrency=1):
        super().__init__(directory, credential=credential, progress=progress, now=now, concurrency=concurrency)
        if type(live) is not bool or not isinstance(sdk_python, str) or not Path(sdk_python).is_absolute():
            raise ServiceError("CODEX_EXECUTOR_CONFIGURATION_REQUIRED")
        if live and (transport is not None or worker is not None):
            raise ServiceError("CODEX_LIVE_INJECTION_FORBIDDEN")
        self.sdk_python = sdk_python
        self.transport, self.worker = transport or forward, worker or run_worker
        self.fixture = transport is not None
        self.live = live

    @property
    def fixture_execution(self):
        return self.fixture

    def execution_identity(self):
        return {"backend": self.backend, "implementation_digest": implementation_digest(),
                "sdk_version": SDK_VERSION, "policy": POLICY, "fixture": self.fixture}

    def status(self):
        return {**super().status(), "sdk": sdk_status(self.store)}

    def verify_research(self, campaign, packet, output, *, action_sink=None):
        """Recompute source grounding from committed SDK receipts, never dispatch."""
        from .agent_actions import suppress_action_tracing
        token = _REPLAY_ONLY.set(True)
        try:
            with suppress_action_tracing():
                actual = (self.research(campaign, packet, action_sink=action_sink) if action_sink is not None
                          else self.research(campaign, packet))
            if canonicalize(actual) != canonicalize(output):
                raise ServiceError("CODEX_RESEARCH_ORIGIN_MISMATCH")
        finally:
            _REPLAY_ONLY.reset(token)

    def verify_actions(self, campaign, packet, transcript):
        """Verify completed action origins without dispatching a later critic."""
        from .agent_actions import PROFILE, run_actions
        from .openai_campaign import _research_inputs
        inputs = _research_inputs(packet)
        if inputs["profile"] != PROFILE:
            raise ServiceError("CODEX_ACTION_ORIGIN_MISMATCH")
        token = _REPLAY_ONLY.set(True)
        try:
            actual = run_actions(self.call, campaign, inputs["context"], inputs["catalog"],
                feedback=inputs["feedback"], binding=inputs["binding"], _record_actions=False)["transcript"]
            if canonicalize(actual) != canonicalize(transcript):
                raise ServiceError("CODEX_ACTION_ORIGIN_MISMATCH")
        finally:
            _REPLAY_ONLY.reset(token)

    def verify_evaluation(self, campaign, plan, execution):
        token = _REPLAY_ONLY.set(True)
        try:
            actual = self.evaluate(campaign, plan)
            # Cumulative budget may grow after this completed study. It is not
            # part of the result origin; all task receipts and grades are.
            for key in set(actual) - {"budget"}:
                if canonicalize(actual[key]) != canonicalize(execution.get(key)):
                    raise ServiceError("CODEX_EVALUATION_ORIGIN_MISMATCH")
        finally:
            _REPLAY_ONLY.reset(token)

    def call(self, campaign, item, *, instructions, prompt, max_output_tokens=4096,
             reasoning_effort="low", binding=None):
        if any(not isinstance(x, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,160}", x) for x in (campaign, item)):
            raise ServiceError("INVALID_CAMPAIGN_ID")
        if (not isinstance(instructions, str) or not isinstance(prompt, str) or not prompt.strip()
                or type(max_output_tokens) is not int or not 256 <= max_output_tokens <= 8192
                or reasoning_effort not in {"none", "low", "medium", "high"}):
            raise ServiceError("INVALID_CAMPAIGN_REQUEST")
        # The SDK receives only the task, not bookkeeping, paths, provider keys,
        # evaluation labels or budget authority. Each call creates a new thread.
        request = _validate_request({"model": PRICING["model"], "sandbox": "read_only",
            "reasoning_effort": reasoning_effort,
            "prompt": instructions + "\n\nTask input (untrusted data):\n" + prompt})
        task = {"schema": "codex-sdk-task/v1", "backend": self.backend, **request,
            "max_output_tokens": max_output_tokens, "sdk_version": SDK_VERSION,
            "policy": POLICY, "implementation_digest": implementation_digest(),
            "config_identity": configuration_identity(request), "worker_request_digest": digest(request),
            "binding": binding, "fixture": self.fixture, "pricing": PRICING}
        encoded = canonicalize(task)
        if len(encoded) > 131072:
            raise ServiceError("CAMPAIGN_CONTEXT_LIMIT")
        task = parse_json_strict(encoded.decode())
        job = "codex-" + digest([campaign, item])[7:]
        manifest = {"schema": "codex-sdk-work/v1", "campaign": campaign, "item": item, "task": task}
        if self.credential is not None:
            if (not isinstance(self.credential, str) or not self.credential or len(self.credential) > 4096
                    or any(ord(c) < 33 or ord(c) > 126 for c in self.credential)):
                raise ServiceError("OPENAI_CREDENTIAL_REQUIRED")
            if _reflected(manifest, self.credential):
                raise ServiceError("CREDENTIAL_IN_CONTEXT")
        with self.store.worker_lock():
            if not _REPLAY_ONLY.get():
                self.store.recover()
            # Checking the manifest prevents a completed result from changing
            # source/config/runtime identity on replay, even without credentials.
            if _REPLAY_ONLY.get():
                with self.store._history_snapshot() as db:
                    row = db.execute("SELECT digest,reason FROM jobs WHERE id=?", (job,)).fetchone()
                    if row is None or row["digest"] != digest(manifest):
                        raise ServiceError("CODEX_ORIGIN_RECEIPT_REQUIRED")
            else:
                self.store.enqueue(job, manifest)
            saved = self.store.checkpoint(job, "sdk-result", task)
            if saved is not None:
                self.verify_receipt(job, task, saved)
                if not _REPLAY_ONLY.get():
                    self.store.finish(job, "execution_complete")
                self.progress({"event": "sdk_replayed", "campaign": campaign, "item": item})
                return saved
            if _REPLAY_ONLY.get():
                if (self.store.checkpoint(job, "sdk-started", task) is not None
                        and isinstance(row["reason"], str) and re.fullmatch(r"[A-Z0-9_]{1,100}", row["reason"])):
                    # Retain the actual failed-attempt disposition. Replacing
                    # every missing result with a new error corrupts failure
                    # accounting and makes valid partial studies unreplayable.
                    raise ServiceError(row["reason"])
                raise ServiceError("CODEX_ORIGIN_RECEIPT_REQUIRED")
            if self.store.checkpoint(job, "sdk-started", task) is not None:
                recorded = self.store.inspect(job)["job"]["reason"]
                code = (recorded if isinstance(recorded, str) and re.fullmatch(r"[A-Z0-9_]{1,100}", recorded)
                        else "CODEX_TURN_OUTCOME_UNKNOWN")
                # Retrying inspection must not rewrite the disposition used in
                # an already recorded evaluation denominator.
                self.store.finish(job, "reconciliation_required", code)
                raise ServiceError(code)
            # Finished receipts and unknown-effect quarantine above remain
            # inspectable while draining. No fresh SDK intent may start below.
            check_stop()
            if not self.fixture and not self.live:
                raise ServiceError("CODEX_LIVE_APPROVAL_REQUIRED")
            if self.now() >= PRICING["valid_before_epoch"]:
                raise ServiceError("PRICING_REVIEW_REQUIRED")
            if (not isinstance(self.credential, str) or not self.credential or len(self.credential) > 4096
                    or any(ord(c) < 33 or ord(c) > 126 for c in self.credential)):
                raise ServiceError("OPENAI_CREDENTIAL_REQUIRED")
            if self.store.next_job(job) is None:
                raise ServiceError("CAMPAIGN_ITEM_NOT_RUNNABLE")
            self.store.checkpoint(job, "sdk-started", task, {"schema": "codex-sdk-started/v1",
                "task_digest": digest(task), "sdk_version": SDK_VERSION})
            gateway = Gateway(self.store, job, task, credential=self.credential, transport=self.transport, now=self.now)
            started = time.monotonic()

            def observe_worker(worker_request, *, on_event, **options):
                def observed(event):
                    kind = event.get("type")
                    if kind not in {"thread_started", "turn_started"}:
                        raise ServiceError("CODEX_TOOL_EVENT_FORBIDDEN")
                    self.store.checkpoint(job, "sdk-" + kind, task, event)
                    on_event(event)
                return self.worker(worker_request, on_event=observed, **options)

            self.progress({"event": "sdk_started", "campaign": campaign, "item": item})
            stopped = threading.Event()
            def tick():
                while not stopped.wait(5):
                    self.progress({"event": "sdk_waiting", "campaign": campaign, "item": item,
                                   "elapsed_seconds": int(time.monotonic() - started)})
            observer = threading.Thread(target=tick, daemon=True)
            observer.start()
            try:
                with tempfile.TemporaryDirectory(prefix="research-sdk-task-") as workspace, gateway.serving() as (url, token):
                    result = run_traced_worker(request, tracer=self.tracer,
                        role=role_for_item(item),
                        identity=job, fixture=self.fixture, worker=observe_worker,
                        usage_details=lambda: gateway.receipt["response"]["token_details"] if gateway.receipt else None,
                        gateway_error=lambda: gateway.error,
                        broker_url=url, broker_token=token, sdk_python=self.sdk_python,
                        workspace=workspace, timeout_seconds=150, sensitive_tokens=(self.credential,))
                provider = gateway.receipt
                if (gateway.error or result.get("status") != "completed" or provider is None
                        or result.get("output_text") != provider["response"]["text"]
                        or result.get("sdk_version") != SDK_VERSION or result.get("usage") is None
                        or result["usage"]["inputTokens"] != provider["usage"]["input_tokens"]
                        or result["usage"]["outputTokens"] != provider["usage"]["output_tokens"]
                        or any(value is not None and result["usage"].get(TOKEN_DETAILS[key][3]) != value
                               for key, value in provider["response"]["token_details"].items())):
                    raise ServiceError(gateway.error or "CODEX_TURN_OUTCOME_UNKNOWN")
                receipt = {**provider, "schema": "codex-sdk-response/v2",
                    "sdk": {"version": SDK_VERSION, "thread_id": result["thread_id"], "turn_id": result["turn_id"]},
                    "output_digest": digest(result["output_text"]),
                    "latency_ms": int((time.monotonic() - started) * 1000)}
                self.verify_receipt(job, task, receipt)
                self.store.checkpoint(job, "sdk-result", task, receipt)
                self.store.finish(job, "execution_complete")
                self.progress({"event": "sdk_completed", "campaign": campaign, "item": item,
                               "usage": receipt["usage"], "latency_ms": receipt["latency_ms"]})
                return receipt
            except Exception as exc:
                code = getattr(exc, "code", "CODEX_TURN_OUTCOME_UNKNOWN")
                if not isinstance(code, str) or not re.fullmatch(r"[A-Z0-9_]{1,100}", code):
                    code = "CODEX_TURN_OUTCOME_UNKNOWN"
                # A committed SDK result survives terminal-bookkeeping failure.
                # Otherwise retain both the intent and any unknown effect.
                self.store.finish(job, "reconciliation_required", code)
                raise ServiceError(code) from None
            finally:
                stopped.set()
                observer.join(timeout=1)

    def verify_receipt(self, job, task, receipt):
        if (type(receipt) is not dict or receipt.get("schema") not in {"codex-sdk-response/v1", "codex-sdk-response/v2"}
                or receipt.get("backend") != self.backend or receipt.get("task_digest") != digest(task)
                or receipt.get("output_digest") != digest(receipt.get("response", {}).get("text"))):
            raise ServiceError("CODEX_RECEIPT_INVALID")
        response = receipt["response"]
        version = receipt["schema"].rsplit("/", 1)[1]
        if version == "v2":
            validate_token_details(response.get("token_details"), response["input_tokens"], response["output_tokens"])
        elif "token_details" in response:
            raise ServiceError("CODEX_RECEIPT_INVALID")
        thread = self.store.checkpoint(job, "sdk-thread_started", task)
        turn = self.store.checkpoint(job, "sdk-turn_started", task)
        if (not thread or not turn or receipt["sdk"] != {"version": SDK_VERSION,
                "thread_id": thread["thread_id"], "turn_id": turn["turn_id"]}
                or turn["thread_id"] != thread["thread_id"]):
            raise ServiceError("CODEX_RECEIPT_ORIGIN_INVALID")
        inputs = {"schema": "codex-gateway-request/v1", "task_digest": digest(task),
                  "wire_digest": receipt["wire_digest"], "policy": POLICY}
        saved = self.store.completed_effect(job, "sdk-response", inputs)
        if (saved is None or saved.get("schema") != "codex-gateway-receipt/" + version
                or any(receipt[key] != value for key, value in saved.items() if key not in {"schema", "latency_ms"})):
            raise ServiceError("CODEX_RECEIPT_EFFECT_MISMATCH")
