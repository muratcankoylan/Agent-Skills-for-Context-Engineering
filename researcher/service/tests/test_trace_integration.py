"""Real local harness paths with scripted provider/MCP replies, never live APIs."""
import asyncio
from contextlib import asynccontextmanager
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from researcher.service import demo
from researcher.service.contracts import ServiceError
from researcher.service.mcp_tools import read_tool
from researcher.service.store import Store
from researcher.service.tests.test_mcp_tools import FakeSession, registration
from researcher.service.tracing import TraceJournal, Tracer, otlp_payload
from researcher.service.workflow import Workflow

ROOT = Path(__file__).resolve().parents[3]


class TraceIntegrationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()

    def test_full_fixture_research_tree_has_usage_latency_and_no_payload(self):
        with patch("socket.socket.connect", side_effect=AssertionError("network forbidden")):
            result = demo.run_demo(ROOT, self.root / "state")
        self.assertEqual(result["paid_model_calls"], 0)
        journal = TraceJournal(self.root / "state/telemetry")
        rows = journal.rows()
        operations = [row["operation"] for row in rows]
        self.assertIn("workflow.execute", operations)
        self.assertIn("model.call", operations)
        self.assertIn("workflow.effect", operations)
        self.assertEqual(len({row["trace_id"] for row in rows}), 1)
        self.assertTrue(all(row["duration_ns"] >= 0 for row in rows))
        model_rows = [row for row in rows if row["operation"] == "model.call"]
        self.assertTrue(model_rows)
        self.assertTrue(all(row["attributes"]["usage_known"] for row in model_rows))
        self.assertEqual(journal.status()["unfinished_spans"], 0)
        wire = json.dumps(otlp_payload(rows))
        for value in ("fixture-credential-never-sent", "fixture-model-v1", "retain source identifiers",
                      "source_url", "prompt", "request_id", str(ROOT)):
            self.assertNotIn(value, wire)

    def test_trace_disk_failure_preserves_effect_result_replay_and_budget(self):
        store = Store(self.root / "state", demo.demo_config(), initialize=True)
        workflow = Workflow(store, ROOT)
        store.enqueue("job", {"fixture": True})
        store.next_job()
        calls = []
        def effect():
            calls.append(1)
            return {"value": "private output"}
        with patch.object(workflow.tracer.journal, "begin", side_effect=OSError("private disk path")):
            self.assertEqual(workflow.effect("job", "model", {}, effect, model_calls=1, micros=4),
                             {"value": "private output"})
            self.assertEqual(workflow.effect("job", "model", {}, effect, model_calls=1, micros=4),
                             {"value": "private output"})
        self.assertEqual(calls, [1])
        self.assertEqual(store.status()["usage"][0]["model_calls"], 1)
        self.assertEqual(store.status()["usage"][0]["reserved_microusd"], 4)
        self.assertGreater(workflow.tracer.health()["write_failures"], 0)

    def test_logging_failure_cannot_mask_unknown_effect_or_release_reservation(self):
        store = Store(self.root / "state", demo.demo_config(), initialize=True)
        workflow = Workflow(store, ROOT)
        store.enqueue("job", {"fixture": True})
        store.next_job()
        def fail():
            raise ServiceError("DEPENDENCY_FAILURE")
        with patch.object(workflow.tracer.journal, "finish", side_effect=OSError("disk")):
            with self.assertRaisesRegex(ServiceError, "DEPENDENCY_FAILURE"):
                workflow.effect("job", "model", {}, fail, model_calls=1, micros=4)
        self.assertEqual(store.status()["usage"][0]["reserved_microusd"], 4)
        with self.assertRaises(ServiceError):
            workflow.effect("job", "model", {}, fail, model_calls=1, micros=4)
        self.assertEqual(store.status()["usage"][0]["model_calls"], 1)

    def test_async_mcp_child_operations_have_parent_spans_not_tool_payloads(self):
        journal = TraceJournal(self.root / "telemetry")
        tracer = Tracer(journal)
        session = FakeSession()
        @asynccontextmanager
        async def factory(**kwargs):
            yield session
        async def run():
            with tracer.span("workflow.retrieve"):
                return await read_tool(registration(), {"query": "private-paper-query"},
                                       credential="private-api-secret", session_factory=factory)
        self.assertEqual(asyncio.run(run())["tool_calls"], 1)
        rows = journal.rows()
        self.assertEqual({row["operation"] for row in rows},
                         {"workflow.retrieve", "mcp.read", "mcp.initialize", "mcp.list", "mcp.invoke"})
        parent = next(row for row in rows if row["operation"] == "mcp.read")
        for row in rows:
            if row["operation"] in {"mcp.initialize", "mcp.list", "mcp.invoke"}:
                self.assertEqual(row["parent_id"], parent["span_id"])
        wire = json.dumps(otlp_payload(rows))
        for value in ("private-paper-query", "private-api-secret", "captured statement", "search_papers"):
            self.assertNotIn(value, wire)


if __name__ == "__main__":
    unittest.main()
