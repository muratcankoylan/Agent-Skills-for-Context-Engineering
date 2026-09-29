"""SDK observation contracts; optional real SDK uses only a loopback fixture."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from researcher.service.codex_traces import GATEWAY_FAILURE_KINDS, run_traced_worker
from researcher.service.codex_worker import MAX_ELAPSED_NS
from researcher.service import tracing
from researcher.service.tests.test_codex_worker import SDK_PYTHON, TOKEN, fixture_server, request

PRIVATE = "private-content-and-credential-sentinel"
THREAD = "private-thread-fixture"
TURN = "private-turn-fixture"


def start(on_event):
    on_event({"type": "thread_started", "thread_id": THREAD})
    on_event({"type": "turn_started", "thread_id": THREAD, "turn_id": TURN})


def tool(kind, index, elapsed, **fields):
    return {"type": kind, "thread_id": THREAD, "turn_id": TURN,
            "call_index": index, "tool_kind": "mcpToolCall", "elapsed_ns": elapsed, **fields}


class CodexTraceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="codex-traces-")
        self.addCleanup(temporary.cleanup)
        self.journal = tracing.TraceJournal(Path(temporary.name).resolve() / "telemetry")
        self.tracer = tracing.Tracer(self.journal)

    def invoke(self, worker, **options):
        return run_traced_worker(request(model=PRIVATE, prompt=PRIVATE), tracer=self.tracer,
                                 role="researcher", identity=PRIVATE, fixture=True,
                                 worker=worker, **options)

    def test_overlapping_tools_are_siblings_and_usage_is_not_double_counted(self):
        result = {"status": "completed", "usage": {"inputTokens": 12, "outputTokens": 4},
                  "output_text": PRIVATE}
        def worker(_request, on_event):
            start(on_event)
            parent = tracing.current_span()
            for event in (tool("tool_started", 1, 10), tool("tool_started", 2, 20),
                          tool("tool_completed", 1, 30, status="completed"),
                          tool("tool_completed", 2, 50, status="failed")):
                on_event(event)
                self.assertIs(tracing.current_span(), parent)
            return result
        self.assertIs(self.invoke(worker), result)
        parent, first, second = self.journal.rows()
        for child in (first, second):
            self.assertEqual(child["parent_id"], parent["span_id"])
            self.assertEqual(child["trace_id"], parent["trace_id"])
            self.assertNotIn("input_tokens", child["attributes"])
        self.assertEqual([first["status"], second["status"]], ["ok", "error"])
        self.assertEqual([first["attributes"]["sdk_tool_duration_ns"], second["attributes"]["sdk_tool_duration_ns"]], [20, 30])
        self.assertEqual(parent["attributes"]["input_tokens"], 12)
        self.assertEqual(parent["attributes"]["items"], 2)
        self.assertFalse(parent["attributes"]["incomplete"])
        self.assertIsNone(tracing.current_span())
        encoded = json.dumps([self.journal.rows(), tracing.otlp_payload(self.journal.rows())])
        for secret in (PRIVATE, THREAD, TURN):
            self.assertNotIn(secret, encoded)
            for path in self.journal.directory.iterdir():
                self.assertNotIn(secret.encode(), path.read_bytes())

    def test_missing_usage_is_not_fabricated_zero_and_unknown_is_error(self):
        result = {"status": "unknown", "usage": None, "error_code": PRIVATE}
        self.assertIs(self.invoke(lambda *args, **kwargs: result), result)
        row = self.journal.rows()[0]
        self.assertEqual(row["status"], "error")
        self.assertFalse(row["attributes"]["usage_known"])
        self.assertTrue(row["attributes"]["ambiguous"])
        self.assertNotIn("input_tokens", row["attributes"])
        self.assertNotIn(PRIVATE, json.dumps(row))

    def test_gateway_categories_are_closed_and_do_not_change_worker_result(self):
        result = {"status": "unknown", "usage": None}
        for code, kind in {**GATEWAY_FAILURE_KINDS, PRIVATE: "unclassified"}.items():
            calls = []
            def worker(*_args, **_kwargs):
                calls.append(1)
                return result
            self.assertIs(self.invoke(worker, gateway_error=lambda: code), result)
            row = self.journal.rows()[-1]
            self.assertEqual(row["attributes"]["failure.kind"], kind)
            self.assertTrue(row["attributes"]["ambiguous"])
            self.assertEqual(row["attributes"]["outcome"], "unknown")
            self.assertEqual(row["status"], "error")
            self.assertEqual(calls, [1])
        payload = tracing.otlp_payload(self.journal.rows())
        tracing.validate_otlp(payload)
        self.assertNotIn(PRIVATE, json.dumps(payload))
        self.assertNotIn("CODEX_GATEWAY_", json.dumps(payload))

    def test_gateway_observation_survives_worker_exception_without_replacing_it(self):
        error = ValueError(PRIVATE)
        def worker(*_args, **_kwargs):
            raise error
        with self.assertRaises(ValueError) as caught:
            self.invoke(worker, gateway_error=lambda: "CODEX_GATEWAY_HTTP_RATE_LIMITED")
        self.assertIs(caught.exception, error)
        self.assertEqual(self.journal.rows()[0]["attributes"]["failure.kind"], "http_rate_limit")

    def test_gateway_callback_failure_degrades_observation_only(self):
        result = {"status": "completed", "usage": None}
        def broken():
            raise OSError(PRIVATE)
        for callback in (broken, lambda: {"secret": PRIVATE}):
            self.assertIs(self.invoke(lambda *_a, **_k: result, gateway_error=callback), result)
            row = self.journal.rows()[-1]
            self.assertTrue(row["attributes"]["incomplete"])
            self.assertNotIn("failure.kind", row["attributes"])
        self.assertNotIn(PRIVATE, json.dumps(self.journal.rows()))

    def test_no_gateway_error_adds_no_failure_attribute(self):
        self.invoke(lambda *_a, **_k: {"status": "completed", "usage": None}, gateway_error=lambda: None)
        self.assertNotIn("failure.kind", self.journal.rows()[0]["attributes"])

    def test_sdk_defaulted_zero_details_are_not_authoritative(self):
        result = {"status": "completed", "usage": {"inputTokens": 20, "outputTokens": 10,
                  "cachedInputTokens": 0, "cacheWriteInputTokens": 0, "reasoningOutputTokens": 0}}
        self.invoke(lambda *args, **kwargs: result)
        row = self.journal.rows()[0]
        self.assertFalse(row["attributes"]["usage_details_known"])
        for key in ("cached_input_tokens", "cache_write_input_tokens", "reasoning_output_tokens"):
            self.assertNotIn(key, row["attributes"])

    def test_partial_detail_observations_export_only_known_counts_including_zero(self):
        result = {"status": "completed", "usage": {"inputTokens": 20, "outputTokens": 10}}
        details = {"cached_input_tokens": 0, "cache_write_input_tokens": None, "reasoning_output_tokens": 7}
        self.invoke(lambda *args, **kwargs: result, usage_details=lambda: details)
        row = self.journal.rows()[0]
        self.assertFalse(row["attributes"]["usage_details_known"])
        self.assertEqual(row["attributes"]["cached_input_tokens"], 0)
        self.assertEqual(row["attributes"]["reasoning_output_tokens"], 7)
        self.assertNotIn("cache_write_input_tokens", row["attributes"])
        tracing.validate_otlp(tracing.otlp_payload(self.journal.rows()))

    def test_invalid_detail_callback_is_observation_failure_not_worker_retry(self):
        result = {"status": "completed", "usage": {"inputTokens": 20, "outputTokens": 10}}
        for details in ({"prompt": PRIVATE}, {"cached_input_tokens": False,
                         "cache_write_input_tokens": None, "reasoning_output_tokens": None}):
            self.assertIs(self.invoke(lambda *args, **kwargs: result, usage_details=lambda: details), result)
        for row in self.journal.rows():
            self.assertFalse(row["attributes"]["usage_details_known"])
            self.assertTrue(row["attributes"]["incomplete"])
            self.assertNotIn("cached_input_tokens", row["attributes"])
            self.assertNotIn(PRIVATE, json.dumps(row))

    def test_unfinished_tool_marks_observation_interrupted_not_remote_cancelled(self):
        def worker(_request, on_event):
            start(on_event)
            on_event(tool("tool_started", 1, 10))
            return {"status": "unknown", "usage": None}
        self.invoke(worker)
        parent, child = self.journal.rows()
        self.assertTrue(parent["attributes"]["incomplete"])
        self.assertTrue(child["attributes"]["incomplete"])
        self.assertEqual(child["status"], "interrupted")
        self.assertEqual(child["attributes"]["outcome"], "unknown")
        self.assertNotIn("sdk_tool_duration_ns", child["attributes"])

    def test_unknown_tool_completion_marks_parent_incomplete(self):
        def worker(_request, on_event):
            start(on_event)
            on_event(tool("tool_started", 1, 10))
            on_event(tool("tool_completed", 1, 20, status="unknown"))
            return {"status": "completed", "usage": None}
        self.invoke(worker)
        self.assertTrue(self.journal.rows()[0]["attributes"]["incomplete"])

    def test_extra_payload_is_rejected_without_changing_result_or_leaking(self):
        result = {"status": "completed", "usage": None}
        def worker(_request, on_event):
            start(on_event)
            on_event(tool("tool_started", 1, 10, arguments=PRIVATE))
            return result
        self.assertIs(self.invoke(worker), result)
        rows = self.journal.rows()
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["attributes"]["incomplete"])
        self.assertNotIn(PRIVATE, json.dumps(rows))

    def test_invalid_event_order_timing_and_identity_are_not_projected(self):
        cases = (tool("tool_started", 2, 10), tool("tool_started", 1, -1),
                 tool("tool_started", 1, MAX_ELAPSED_NS + 1),
                 {**tool("tool_started", 1, 10), "thread_id": PRIVATE},
                 tool("tool_completed", 1, 10, status="completed"))
        for event in cases:
            with self.subTest(event=event):
                def worker(_request, on_event):
                    start(on_event)
                    on_event(event)
                    return {"status": "completed", "usage": None}
                self.invoke(worker)
        self.assertTrue(all(row["operation"] == "sdk.turn" for row in self.journal.rows()))
        self.assertTrue(all(row["attributes"]["incomplete"] for row in self.journal.rows()))

    def test_journal_failures_never_retry_or_change_returned_result(self):
        for method in ("begin", "finish"):
            calls = []
            result = {"status": "completed", "usage": None}
            def worker(_request, on_event):
                calls.append(1)
                start(on_event)
                on_event(tool("tool_started", 1, 10))
                on_event(tool("tool_completed", 1, 20, status="completed"))
                return result
            with self.subTest(method=method), patch.object(self.journal, method, side_effect=OSError(PRIVATE)):
                self.assertIs(self.invoke(worker), result)
            self.assertEqual(calls, [1])

    def test_result_projection_error_does_not_reclassify_worker_result(self):
        result = {"status": "completed", "usage": {"unexpected": PRIVATE}}
        self.assertIs(self.invoke(lambda *args, **kwargs: result), result)
        self.assertTrue(self.journal.rows()[0]["attributes"]["incomplete"])

    def test_worker_exception_identity_is_preserved_with_interrupted_child(self):
        error = ValueError(PRIVATE)
        def worker(_request, on_event):
            start(on_event)
            on_event(tool("tool_started", 1, 10))
            raise error
        with self.assertRaises(ValueError) as caught:
            self.invoke(worker)
        self.assertIs(caught.exception, error)
        parent, child = self.journal.rows()
        self.assertEqual(parent["status"], "error")
        self.assertEqual(child["status"], "interrupted")
        self.assertNotIn(PRIVATE, json.dumps(self.journal.rows()))

    def test_explicit_status_and_exception_precedence(self):
        with self.tracer.span("sdk.turn") as span:
            span.set_status("error")
        with self.assertRaises(KeyboardInterrupt):
            with self.tracer.span("sdk.turn") as span:
                span.set_status("ok")
                raise KeyboardInterrupt()
        with self.tracer.span("sdk.turn") as span:
            span.set_status(PRIVATE)
        self.assertEqual([row["status"] for row in self.journal.rows()], ["error", "interrupted", "ok"])

    def test_absent_journal_does_not_change_result(self):
        self.tracer = tracing.Tracer(None)
        result = {"status": "completed", "usage": None}
        def worker(_request, on_event):
            start(on_event)
            on_event(tool("tool_started", 1, 10))
            on_event(tool("tool_completed", 1, 20, status="completed"))
            return result
        self.assertIs(self.invoke(worker), result)

    def test_active_parent_owns_journal_and_child_ancestry(self):
        other = tracing.TraceJournal(self.journal.directory.parent / "other-telemetry")
        with self.tracer.span("workflow.execute") as parent:
            run_traced_worker(request(), tracer=tracing.Tracer(other), role="researcher", identity="nested",
                              worker=lambda *args, **kwargs: {"status": "completed", "usage": None})
        self.assertEqual(other.rows(), [])
        root, child = self.journal.rows()
        self.assertEqual(child["parent_id"], parent.span_id)
        self.assertEqual(child["trace_id"], root["trace_id"])

    def test_bad_request_still_reaches_worker_validation(self):
        error = ValueError("worker-owned-validation")
        calls = []
        def worker(value, **kwargs):
            calls.append(value)
            raise error
        with self.assertRaises(ValueError) as caught:
            run_traced_worker([], tracer=self.tracer, role="researcher", identity="invalid",
                              worker=worker)
        self.assertIs(caught.exception, error)
        self.assertEqual(calls, [[]])


@unittest.skipUnless(SDK_PYTHON, "explicit pinned SDK environment required")
class RealSDKTraceTests(unittest.TestCase):
    def test_actual_sdk_gateway_failure_exports_category_and_cannot_retry(self):
        from researcher.service.codex_campaign import CodexCampaign
        from researcher.service.contracts import ServiceError
        from researcher.service.openai_campaign import initialize
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary).resolve() / "authority"
            initialize(directory, cap_microusd=100_000_000, prior_spend_microusd=0)
            calls = []
            def transport(*_args, **_kwargs):
                calls.append(1)
                raise ServiceError("CODEX_GATEWAY_HTTP_RATE_LIMITED")
            campaign = CodexCampaign(directory, sdk_python=SDK_PYTHON, credential="fixture-key",
                transport=transport, progress=lambda _: None, now=lambda: 1790683200)
            for _ in range(2):
                with self.assertRaises(ServiceError):
                    campaign.call("failure-trace", "researcher", instructions="Return JSON.", prompt="Fixture.")
            self.assertEqual(calls, [1])
            self.assertGreater(campaign.status()["reserved_microusd"], 0)
            row = next(row for row in campaign.tracer.journal.rows() if row["operation"] == "sdk.turn")
            self.assertEqual(row["attributes"]["failure.kind"], "http_rate_limit")
            self.assertTrue(row["attributes"]["ambiguous"])
            tracing.validate_otlp(tracing.otlp_payload([row]))

    def test_actual_patch_denial_and_execution_have_truthful_observation_coverage(self):
        for sandbox in ("read_only", "workspace_write"):
            with self.subTest(sandbox=sandbox), tempfile.TemporaryDirectory() as workspace, \
                    tempfile.TemporaryDirectory() as state, fixture_server("patch") as (url, records):
                journal = tracing.TraceJournal(Path(state).resolve() / "telemetry")
                result = run_traced_worker(request(sandbox=sandbox), tracer=tracing.Tracer(journal),
                    role="researcher", identity="synthetic-local-sdk", fixture=True,
                    broker_url=url, broker_token=TOKEN, sdk_python=SDK_PYTHON,
                    workspace=workspace, timeout_seconds=20)
                self.assertEqual(result["status"], "completed", result)
                self.assertEqual(len(records), 2)
                parent, *children = journal.rows()
                self.assertEqual(parent["attributes"]["input_tokens"], 24)
                self.assertEqual(parent["attributes"]["output_tokens"], 8)
                self.assertFalse(parent["attributes"]["incomplete"])
                if sandbox == "read_only":
                    self.assertEqual(children, [])
                    self.assertFalse((Path(workspace) / "proof.txt").exists())
                else:
                    self.assertEqual(len(children), 1)
                    self.assertEqual(children[0]["attributes"]["sdk.tool_kind"], "fileChange")
                    self.assertEqual(children[0]["status"], "ok")
                    self.assertGreater(children[0]["attributes"]["sdk_tool_duration_ns"], 0)
                    self.assertTrue((Path(workspace) / "proof.txt").exists())
                payload = json.dumps(tracing.otlp_payload(journal.rows()))
                for secret in (TOKEN, "proof.txt", request()["prompt"], result["thread_id"], result["turn_id"]):
                    self.assertNotIn(secret, payload)


if __name__ == "__main__":
    unittest.main()
