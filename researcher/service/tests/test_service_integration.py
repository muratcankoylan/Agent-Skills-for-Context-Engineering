"""Offline cross-component tests, never a claim of live model effectiveness."""

import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

from researcher.service import demo
from researcher.service.contracts import ServiceError, load_config
from researcher.service.mcp_evidence import MCPEvidenceError, collect_mcp
from researcher.service.store import Store
from researcher.service.tests.test_mcp_evidence import receipt
from researcher.service.tests.test_mcp_tools import registration
from researcher.service.workflow import Workflow, make_manifest

ROOT = Path(__file__).resolve().parents[3]


class ServiceIntegrationTests(unittest.TestCase):
    def run_config(self, config, *, fixture=True, source=demo.source):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        store = Store(Path(directory.name).resolve() / "state", config, initialize=True)
        store.enqueue("scenario", make_manifest(ROOT, config, config["schedules"][0], fixture=fixture))
        runner = Workflow(store, ROOT, live=not fixture, model=demo.model,
                          source=source, credential=lambda _: "synthetic-credential")
        return store, runner

    def test_multiple_query_and_skill_fixtures(self):
        for skill, query in (
            ("context-fundamentals", "Preserve source evidence across agent context transfers"),
            ("memory-systems", "Retrieve stale and conflicting memory with provenance"),
            ("tool-design", "Clarify tool contracts and reject ambiguous arguments"),
        ):
            with self.subTest(skill=skill):
                config = demo.demo_config()
                config["schedules"][0].update(query=query, skills=[skill])
                store, runner = self.run_config(config)
                with patch("socket.socket.connect", side_effect=AssertionError("network forbidden")):
                    result = runner.drain()[0]
                self.assertNotIn("error", result)
                self.assertEqual(store.status()["jobs"][0]["status"], "proposal_ready")
                self.assertTrue(result["result"]["fixture"])

    def test_no_answer_stops_before_model(self):
        def empty(*args):
            value = demo.source(*args)
            value["evidence"] = []
            return value
        store, runner = self.run_config(demo.demo_config(), source=empty)
        self.assertEqual(runner.drain()[0]["error"], "NO_CAPTURED_EVIDENCE")
        self.assertEqual(store.status()["usage"][0]["model_calls"], 0)

    def test_next_cycle_gets_bounded_memory_and_suppresses_exact_repeat(self):
        config = demo.demo_config()
        store, runner = self.run_config(config)
        first = runner.drain()[0]
        self.assertNotIn("error", first)
        store.enqueue("next-cycle", make_manifest(ROOT, config, config["schedules"][0], fixture=True))
        second = runner.drain()[0]
        self.assertEqual(second["result"]["reason"], "DUPLICATE_CANDIDATE")
        feedback = store.inspect("next-cycle")["steps"]["prior-feedback"]
        self.assertEqual(len(feedback["entries"]), 1)
        self.assertEqual(feedback["entries"][0]["job"], "scenario")
        self.assertNotIn("judgment", json.dumps(feedback))
        # First run needs five fixture calls; repeat stops after three roles.
        self.assertEqual(store.status()["usage"][0]["model_calls"], 8)
        self.assertNotIn("model-evaluator-0", {e["name"] for e in store.inspect("next-cycle")["effects"]})

    def mcp_config(self):
        config = demo.demo_config()
        config["mcp_tools"] = [{"registration": registration(), "credential_env": None, "max_cost_microusd": 10}]
        config["schedules"][0]["mcp_reads"] = [{"id": "papers", "arguments": {"query": "context"}}]
        return load_config(json.dumps(config))

    def test_mcp_wired_through_durable_reservation_before_gateway(self):
        config = self.mcp_config()
        store, runner = self.run_config(config, fixture=False)
        async def gateway(*_args, **_kwargs):
            effects = store.inspect("scenario")["effects"]
            selected = next(e for e in effects if e["name"] == "mcp-papers")
            self.assertEqual(selected["state"], "started")
            self.assertEqual(selected["source_requests"], 12)
            self.assertEqual(selected["reserved_microusd"], 10)
            return receipt()
        # Source provenance replay is independently tested; this composition
        # test substitutes only that network boundary and the SDK gateway.
        with patch("researcher.service.workflow.verify_source"), patch(
            "researcher.service.mcp_evidence.read_tool", AsyncMock(side_effect=gateway)
        ), patch("researcher.service.mcp_worker.bounded_collect_mcp", side_effect=collect_mcp
        ), patch("socket.socket.connect", side_effect=AssertionError("network forbidden")):
            result = runner.drain()[0]
        self.assertNotIn("error", result)
        self.assertEqual(store.status()["usage"][0]["source_request_reservations"], 13)
        self.assertEqual(store.status()["usage"][0]["model_calls"], 5)

    def test_mcp_budget_failure_occurs_before_gateway(self):
        config = self.mcp_config()
        config["limits"]["daily_source_requests"] = 12
        store, runner = self.run_config(config, fixture=False)
        with patch("researcher.service.workflow.verify_source"), patch("researcher.service.mcp_worker.bounded_collect_mcp") as call:
            result = runner.drain()[0]
        self.assertEqual(result["error"], "BUDGET_EXHAUSTED")
        call.assert_not_called()
        self.assertEqual(store.status()["usage"][0]["model_calls"], 0)

    def test_unknown_mcp_quarantines_and_fixture_cannot_invoke(self):
        config = self.mcp_config()
        for fixture in (False, True):
            store, runner = self.run_config(config, fixture=fixture)
            with patch("researcher.service.workflow.verify_source"), patch(
                "researcher.service.mcp_worker.bounded_collect_mcp",
                side_effect=MCPEvidenceError("MCP_TIMEOUT", ambiguous=True, call_attempted=True)
            ) as call:
                result = runner.drain()[0]
            if fixture:
                call.assert_not_called()
                self.assertEqual(result["error"], "FIXTURE_CANNOT_CALL_MCP")
            else:
                call.assert_called_once()
                self.assertEqual(store.status()["jobs"][0]["status"], "reconciliation_required")

    def test_mcp_config_rejects_unregistered_duplicate_and_invalid_arguments(self):
        baseline = self.mcp_config()
        for mutate in (
            lambda c: c["schedules"][0]["mcp_reads"][0].update(id="unknown"),
            lambda c: c["schedules"][0]["mcp_reads"][0].update(arguments={"unexpected": 1}),
            lambda c: c["mcp_tools"].append(copy.deepcopy(c["mcp_tools"][0])),
        ):
            config = copy.deepcopy(baseline)
            mutate(config)
            with self.assertRaises(ServiceError):
                load_config(json.dumps(config))

    def test_mcp_config_rejects_unused_bad_registration_and_impossible_limits(self):
        baseline = self.mcp_config()
        for mutate in (
            lambda c: c["mcp_tools"][0]["registration"].update(url="http://127.0.0.1/mcp"),
            lambda c: c["mcp_tools"][0].update(max_cost_microusd=101),
            lambda c: c["mcp_tools"][0]["registration"].update(max_output_bytes=65536),
        ):
            config = copy.deepcopy(baseline)
            mutate(config)
            with self.assertRaises(ServiceError):
                load_config(json.dumps(config))
        baseline["schedules"][0]["mcp_reads"] = []
        baseline["mcp_tools"][0]["registration"]["url"] = "https://localhost/mcp"
        with self.assertRaises(ServiceError):
            load_config(json.dumps(baseline))
