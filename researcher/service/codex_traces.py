"""Metadata-only observation of SDK turns and emitted tool lifecycle events.

Arrival-time spans measure this observer, not provider inference or hidden tool
attempts. Paired SDK events additionally retain their monotonic duration. A
missing completion closes *observation* as interrupted/incomplete, never claims
the remote tool stopped. Usage is reported once at the fresh-thread turn level.
No prompts, output, tool payloads, raw IDs or broker capabilities are journaled.
Tracing failures do not change the worker result, retry it, or release budgets.
This adapter does not provide the missing spend or deployment authority.
"""
from __future__ import annotations

import secrets

from .codex_worker import MAX_ELAPSED_NS, MAX_TOOL_CALLS, TOOL_KINDS, TOOL_STATUSES, run_worker
from .tracing import Span, Tracer, _attributes, current_span

GATEWAY_FAILURE_KINDS = {
    "CODEX_GATEWAY_" + suffix: kind for suffix, kind in {
        "HTTP_AUTH_REJECTED": "http_auth", "HTTP_RATE_LIMITED": "http_rate_limit",
        "HTTP_CLIENT_ERROR": "http_client", "HTTP_SERVER_ERROR": "http_server",
        "HTTP_REDIRECT": "http_redirect", "HTTP_STATUS_UNEXPECTED": "http_status",
        "TRANSPORT_TIMEOUT": "timeout", "TRANSPORT_TLS_ERROR": "tls",
        "TRANSPORT_NETWORK_ERROR": "network", "RESPONSE_FRAMING_INVALID": "response_framing",
        "RESPONSE_TYPE_INVALID": "response_type", "RESPONSE_LIMIT": "response_limit",
        "FORWARD_INPUT_INVALID": "worker_input", "FORWARD_WORKER_ERROR": "worker_internal",
        "WALL_TIMEOUT": "timeout", "WORKER_START_FAILED": "worker_start",
        "WORKER_FAILED": "worker_failed", "TRANSPORT_UNKNOWN": "transport_unknown",
    }.items()
}


def role_for_item(item):
    """Closed generic trace role; action transcripts retain advisory specialties.

These are separate harness-dispatched SDK turns, not native SDK tool spans.
"""
    if item in {"researcher", "critic", "skill_editor", "evaluator"}:
        return item
    if item in {"agent_action_1", "agent_action_2", "agent_action_3", "agent_action_4"}:
        return "researcher"
    if item in {"agent_specialist_methods", "agent_specialist_transfer"}:
        return "critic"
    return "evaluator"


class _Projection:
    def __init__(self, tracer: Tracer, parent: Span):
        self.tracer, self.parent = tracer, parent
        self.active: dict[int, tuple[Span, int, str]] = {}
        self.last_index = 0
        self.last_elapsed = 0
        self.thread_id = self.turn_id = None
        self.incomplete = False

    def _finish(self, span, *, incomplete=False):
        if not span.recorded:
            return
        duration = max(0, self.tracer.monotonic_ns() - span.monotonic_ns)
        if incomplete:
            span.annotate(incomplete=True, outcome="unknown")
            span.set_status("interrupted")
        self.tracer.journal.finish(span.span_id, span.started_ns + duration,
                                   duration, span.status, span.attributes)

    def observe(self, event):
        # Worker validates this contract before calling us. Keep a second closed
        # boundary so fake/test/future workers cannot add payloads to telemetry.
        try:
            if type(event) is not dict:
                raise ValueError()
            kind = event.get("type")
            if kind == "thread_started":
                if (set(event) != {"type", "thread_id"} or self.thread_id is not None
                        or type(event["thread_id"]) is not str or not 1 <= len(event["thread_id"]) <= 256):
                    raise ValueError()
                self.thread_id = event["thread_id"]
                self.parent.reference("thread_ref", self.thread_id)
                return
            if kind == "turn_started":
                if (set(event) != {"type", "thread_id", "turn_id"}
                        or self.thread_id is None or event["thread_id"] != self.thread_id
                        or self.turn_id is not None or type(event["turn_id"]) is not str
                        or not 1 <= len(event["turn_id"]) <= 256):
                    raise ValueError()
                self.turn_id = event["turn_id"]
                self.parent.reference("turn_ref", self.turn_id)
                return
            keys = {"type", "thread_id", "turn_id", "call_index", "tool_kind", "elapsed_ns"}
            if kind == "tool_completed":
                keys.add("status")
            if (kind not in {"tool_started", "tool_completed"} or set(event) != keys
                    or self.turn_id is None or event["thread_id"] != self.thread_id
                    or event["turn_id"] != self.turn_id or event["tool_kind"] not in TOOL_KINDS
                    or type(event["call_index"]) is not int or not 1 <= event["call_index"] <= MAX_TOOL_CALLS
                    or type(event["elapsed_ns"]) is not int
                    or not self.last_elapsed <= event["elapsed_ns"] <= MAX_ELAPSED_NS):
                raise ValueError()
            index, elapsed = event["call_index"], event["elapsed_ns"]
            if kind == "tool_started":
                if index != self.last_index + 1:
                    raise ValueError()
                attributes = _attributes({"runtime": "codex_sdk", "observation_only": True,
                    "fixture": self.parent.attributes["fixture"], "tool_sequence": index,
                    "sdk.tool_kind": event["tool_kind"]})
                span = Span(self.tracer, self.parent.trace_id, secrets.token_hex(8), self.parent.span_id,
                            "sdk.tool", attributes, self.tracer.wall_ns(), self.tracer.monotonic_ns())
                self.active[index] = (span, elapsed, event["tool_kind"])
                self.last_index = index
                if self.tracer.journal is not None:
                    self.tracer.journal.begin(span.trace_id, span.span_id, span.parent_id,
                        span.operation, span.started_ns, span.attributes)
                    span.recorded = True
            else:
                if (index not in self.active or self.active[index][2] != event["tool_kind"]
                        or event["status"] not in TOOL_STATUSES):
                    raise ValueError()
                span, start, _kind = self.active.pop(index)
                status = event["status"]
                self.incomplete = self.incomplete or status == "unknown"
                span.annotate(sdk_tool_duration_ns=elapsed - start,
                    outcome={"completed": "completed", "failed": "failed", "declined": "rejected", "unknown": "unknown"}[status],
                    incomplete=status == "unknown")
                span.set_status("ok" if status == "completed" else "error")
                self._finish(span)
            self.last_elapsed = elapsed
        except Exception:
            self.incomplete = True
            self.tracer._failure("TRACE_WRITE_FAILED")

    def close(self):
        self.incomplete = self.incomplete or bool(self.active)
        for span, _elapsed, _kind in self.active.values():
            try:
                self._finish(span, incomplete=True)
            except Exception:
                self.tracer._failure("TRACE_WRITE_FAILED")
        self.active.clear()
        self.parent.annotate(items=self.last_index, incomplete=self.incomplete)


def run_traced_worker(request: dict, *, tracer: Tracer, role: str, identity: str,
                      fixture: bool = False, worker=run_worker, usage_details=None,
                      gateway_error=None, **options) -> dict:
    """Observe one existing worker invocation; no implicit journal or exporter.

SDK item coverage is partial by design: denied tools may emit no item, and one
turn may contain many upstream requests. ``items`` is observed tool starts, not
model-call count. The caller still supplies its own admitted loopback broker.
An existing parent owns the journal, so nested observations cannot create a
cross-journal parent reference that neither export can reconstruct.
``usage_details`` may read the admitted gateway's receipt after the worker
returns. Missing SDK counters are defaulted by the SDK, so worker usage alone
is not evidence for cache/reasoning details. Unknown details are omitted.
``gateway_error`` is observed on this thread before the span closes, including
when the worker raises. Only a closed failure category is exported; classification
does not resolve ambiguous spend, authorize a retry, or modify the worker result.
"""
    if "on_event" in options:
        raise ValueError("SDK trace adapter owns its metadata callback")
    active_parent = current_span()
    if active_parent is not None:
        tracer = active_parent.tracer
    with tracer.span("sdk.turn", identity=identity, attributes={"runtime": "codex_sdk",
            "role": role, "transport": "subprocess", "fixture": fixture,
            "observation_only": True}) as parent:
        projection = _Projection(tracer, parent)
        try:
            try:
                parent.reference("model_ref", request.get("model", ""))
            except Exception:
                projection.incomplete = True
                tracer._failure("TRACE_REFERENCE_FAILED")
            result = worker(request, on_event=projection.observe, **options)
            try:
                status = result.get("status", "unknown")
                parent.annotate(outcome={"interrupted": "cancelled"}.get(status, status),
                                ambiguous=status == "unknown", usage_known=result.get("usage") is not None)
                if status != "completed":
                    parent.set_status("interrupted" if status == "interrupted" else "error")
                if result.get("error_code") is not None:
                    parent.reference("error.code_ref", result["error_code"])
                usage = result.get("usage")
                if usage is not None:
                    parent.annotate(input_tokens=usage["inputTokens"], output_tokens=usage["outputTokens"])
                details = usage_details() if usage_details is not None else None
                parent.annotate(usage_details_known=False)
                if details is not None and usage is not None:
                    from .codex_gateway import validate_token_details
                    validate_token_details(details, usage["inputTokens"], usage["outputTokens"])
                    parent.annotate(**{key: value for key, value in details.items() if value is not None},
                                    usage_details_known=all(value is not None for value in details.values()))
            except Exception:
                # The worker owns result validation. Telemetry can degrade, but
                # cannot turn a returned result into a new failure or retry.
                projection.incomplete = True
                tracer._failure("TRACE_WRITE_FAILED")
            return result
        finally:
            try:
                code = gateway_error() if gateway_error is not None else None
                if code is not None:
                    if type(code) is not str:
                        raise ValueError()
                    parent.annotate(**{"failure.kind": GATEWAY_FAILURE_KINDS.get(code, "unclassified"),
                                       "ambiguous": True, "outcome": "unknown"})
                    parent.set_status("error")
            except Exception:
                projection.incomplete = True
                tracer._failure("TRACE_WRITE_FAILED")
            projection.close()
