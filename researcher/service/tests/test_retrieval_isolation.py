"""Independent source failures never become successful or repeated effects."""

from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from researcher.scripts.source_connectors import ConnectorError, LimitExceededError, MalformedResponseError
from researcher.service.contracts import ServiceError, digest, load_config
from researcher.service.demo import demo_config
from researcher.service.retrieval_sources import source_limits
from researcher.service.store import Store
from researcher.service.tests.test_daily_retrieval import DAY, ROOT, config, lane
from researcher.service.workflow import Workflow, make_manifest


class RetrievalIsolationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name).resolve() / "state"
        settings = config()
        settings["schedules"][0].update(sources=["deepmind", "huggingface"],
                                        source_queries={"deepmind": "", "huggingface": ""})
        self.config = load_config(json.dumps(settings))
        self.store = Store(self.directory, self.config, initialize=True)
        self.calls = []

    def enqueue(self, job="daily", fixture=True):
        manifest = make_manifest(ROOT, self.config, self.config["schedules"][0], fixture=fixture, window_end=DAY)
        self.store.enqueue(job, manifest)
        return manifest

    def source(self, name, *args, **kwargs):
        self.calls.append(name)
        if name == self.config["schedules"][0]["sources"][0]:
            raise LimitExceededError("TIME_LIMIT", "untrusted provider diagnostic must not be copied")
        return lane(name, *args, **kwargs)

    def runner(self, *, source=None, verifier=None, live=False):
        def forbidden(*args, **kwargs):
            self.fail("unrelated model, MCP, GitHub or legacy source invoked")
        return Workflow(self.store, ROOT, live=live, model=forbidden, source=forbidden,
                        credential=lambda name: "synthetic-test-key-not-sent",
                        retrieval_source=source or self.source,
                        retrieval_verify=verifier or (lambda *a, **k: None))

    def inputs(self, manifest, name):
        limits = asdict(source_limits(name))
        limits["max_milliseconds"] = int(limits.pop("max_seconds") * 1000)
        return {"policy": {"policy": manifest["retrieval_policy"], "source": name,
            "query": manifest["schedule"]["source_queries"][name], "window_start": manifest["window_start"],
            "window_end": manifest["window_end"], "limits": limits}, "manifest_digest": digest(manifest)}

    def test_timeout_isolated_other_lane_runs_and_partial_report_retains_unknown(self):
        self.enqueue()
        with patch("socket.create_connection", side_effect=AssertionError("network")), \
             patch("researcher.service.workflow.Workflow.ask", side_effect=AssertionError("model")), \
             patch("researcher.service.github.publish_proposal", side_effect=AssertionError("GitHub")), \
             patch("researcher.service.mcp_worker.bounded_collect_mcp", side_effect=AssertionError("MCP")):
            result = self.runner().drain()[0]["result"]
        self.assertEqual(self.calls, ["deepmind", "huggingface"])
        self.assertTrue(result["collection_completed"])
        self.assertTrue(result["reconciliation_required"])
        self.assertFalse(result["evidence_qualified"])
        self.assertEqual(result["source_failures"], [{"source": "deepmind", "effect_name": "retrieval-deepmind",
            "error_code": "TIME_LIMIT", "effect_state": "unknown", "reservation_retained": True}])
        coverage = result["context_digest"]["coverage"]
        self.assertEqual(coverage[0]["state"], "unavailable")
        self.assertFalse(coverage[0]["coverage_complete"])
        self.assertEqual(len(result["context_digest"]["items"]), 1)
        state = self.store.inspect("daily")
        self.assertEqual(state["job"]["status"], "reconciliation_required")
        self.assertEqual([e["state"] for e in state["effects"]], ["unknown", "completed"])
        self.assertNotIn("retrieval-deepmind", state["steps"])
        self.assertIn("retrieval-failure-deepmind", state["steps"])
        self.assertNotIn("untrusted provider diagnostic", json.dumps(state))
        self.assertEqual(self.store.status()["usage"][0]["source_request_reservations"], 2)
        self.assertEqual(self.runner().drain(), [])

    def test_paid_timeout_keeps_ceiling_and_later_free_lane_runs(self):
        self.config["schedules"][0].update(sources=["x", "deepmind"], source_queries={"x": "context engineering", "deepmind": ""})
        self.config.update(source_credentials={"x": "X_TEST_KEY"}, source_cost_microusd={"x": 100})
        self.config["limits"].update(run_budget_microusd=100, daily_budget_microusd=100)
        self.store = Store(self.directory.parent / "paid", self.config, initialize=True)
        self.enqueue()
        self.runner().drain()
        self.assertEqual(self.calls, ["x", "deepmind"])
        usage = self.store.status()["usage"][0]
        self.assertEqual(usage["reserved_microusd"], 100)
        self.assertEqual(usage["source_request_reservations"], 2)
        self.assertEqual(usage["model_calls"], 0)

    def test_restart_skips_unknown_first_lane_and_runs_never_attempted_second(self):
        self.enqueue()
        def crash(name, *args, **kwargs):
            self.calls.append(name)
            raise KeyboardInterrupt
        with self.assertRaises(KeyboardInterrupt):
            self.runner(source=crash).drain()
        self.store = Store(self.directory, self.config)
        result = self.runner().drain()[0]["result"]
        self.assertEqual(self.calls, ["deepmind", "huggingface"])
        self.assertEqual(result["source_failures"][0]["error_code"], "PROCESS_INTERRUPTED")
        self.assertEqual(self.store.inspect("daily")["effects"][0]["state"], "unknown")
        self.assertEqual(self.store.status()["usage"][0]["source_request_reservations"], 2)

    def test_crash_after_failure_record_before_gap_checkpoint_is_reconstructed(self):
        self.enqueue()
        original = self.store.checkpoint
        def checkpoint(job, name, inputs, output=None):
            if name == "retrieval-failure-deepmind" and output is not None:
                raise KeyboardInterrupt
            return original(job, name, inputs, output)
        with patch.object(self.store, "checkpoint", side_effect=checkpoint), self.assertRaises(KeyboardInterrupt):
            self.runner().drain()
        self.store = Store(self.directory, self.config)
        result = self.runner().drain()[0]["result"]
        self.assertEqual(self.calls, ["deepmind", "huggingface"])
        self.assertEqual(result["source_failures"][0]["error_code"], "TIME_LIMIT")

    def test_completed_second_lane_replays_after_restart_without_another_request(self):
        self.enqueue()
        def crash(name, *args, **kwargs):
            if name == "huggingface":
                raise KeyboardInterrupt
        with self.assertRaises(KeyboardInterrupt):
            self.runner(verifier=crash).drain()
        self.store = Store(self.directory, self.config)
        result = self.runner(source=lambda *a, **k: self.fail("duplicate source")).drain()[0]["result"]
        self.assertTrue(result["reconciliation_required"])
        self.assertEqual(self.calls, ["deepmind", "huggingface"])

    def test_shared_unknown_slot_is_gap_without_new_reservation_and_other_lane_uses_cache(self):
        self.enqueue("first", fixture=False)
        self.runner(live=True).drain()
        self.enqueue("second", fixture=False)
        result = self.runner(live=True, source=lambda *a, **k: self.fail("duplicate request")).drain()[0]["result"]
        self.assertEqual(result["source_failures"][0]["effect_state"], "blocked")
        self.assertFalse(result["source_failures"][0]["reservation_retained"])
        self.assertTrue(result["reconciliation_required"])
        self.assertEqual(self.store.status()["usage"][0]["source_request_reservations"], 2)
        self.assertEqual(self.store.inspect("first")["effects"][0]["state"], "unknown")

    def test_all_unavailable_report_is_empty_unqualified_and_no_retry(self):
        self.enqueue()
        def failed(*args, **kwargs):
            raise MalformedResponseError("ATOM_INVALID", "private source diagnostic")
        result = self.runner(source=failed).drain()[0]["result"]
        self.assertEqual(result["context_digest"]["items"], [])
        self.assertEqual(len(result["source_failures"]), 2)
        self.assertTrue(result["reconciliation_required"])
        self.assertFalse(result["production_ready"])
        self.assertEqual(self.runner().drain(), [])

    def test_local_spacing_is_known_failure_without_clearing_reservation(self):
        self.enqueue()
        def blocked(name, *args, **kwargs):
            if name == "deepmind":
                raise ServiceError("SOURCE_RATE_LIMIT")
            return lane(name, *args, **kwargs)
        result = self.runner(source=blocked).drain()[0]["result"]
        self.assertEqual(result["source_failures"][0]["effect_state"], "failed")
        self.assertFalse(result["reconciliation_required"])
        self.assertEqual(self.store.inspect("daily")["job"]["status"], "retrieval_complete")
        self.assertEqual(self.store.status()["usage"][0]["source_request_reservations"], 2)

    def test_integrity_failure_stops_remaining_lanes_and_does_not_resume_around_it(self):
        self.enqueue()
        def source(name, *args, **kwargs):
            self.calls.append(name)
            return lane(name, *args, **kwargs)
        def invalid(*args, **kwargs):
            raise ServiceError("SOURCE_REPLAY_MISMATCH")
        result = self.runner(source=source, verifier=invalid).drain()[0]
        self.assertEqual(result["error"], "SOURCE_REPLAY_MISMATCH")
        self.assertEqual(self.calls, ["deepmind"])
        self.store = Store(self.directory, self.config)
        self.assertEqual(self.runner().drain(), [])
        self.assertNotIn("report", self.store.inspect("daily")["steps"])

    def test_global_integrity_failure_after_isolated_unknown_still_blocks_recovery(self):
        self.enqueue()
        result = self.runner(verifier=lambda *a, **k: (_ for _ in ()).throw(ServiceError("SOURCE_REPLAY_MISMATCH"))).drain()[0]
        self.assertEqual(result["error"], "SOURCE_REPLAY_MISMATCH")
        self.store = Store(self.directory, self.config)
        self.assertEqual(self.runner().drain(), [])
        self.assertEqual(self.store.inspect("daily")["job"]["status"], "reconciliation_required")

    def test_capture_and_unexpected_dependency_failures_remain_global_barriers(self):
        for index, error in enumerate((ConnectorError("CAPTURE_FAILURE", "private"), RuntimeError("private"))):
            self.store = Store(self.directory.parent / str(index), self.config, initialize=True)
            self.enqueue()
            def source(*args, **kwargs):
                raise error
            result = self.runner(source=source).drain()[0]
            self.assertIn("error", result)
            self.assertNotIn("report", self.store.inspect("daily")["steps"])
            self.store = Store(self.store.directory, self.config)
            self.assertEqual(self.runner().drain(), [])

    def test_budget_pause_clock_and_database_errors_are_not_lane_failures(self):
        for index, code in enumerate(("BUDGET_EXHAUSTED", "ADMISSION_PAUSED", "CLOCK_MOVED_BACKWARDS", "STATE_DATABASE_ERROR")):
            self.store = Store(self.directory.parent / str(index), self.config, initialize=True)
            self.enqueue()
            def source(*args, **kwargs):
                raise ServiceError(code)
            result = self.runner(source=source).drain()[0]
            self.assertEqual(result["error"], code)
            self.assertNotIn("report", self.store.inspect("daily")["steps"])

    def test_store_failure_api_is_scope_and_digest_bound(self):
        manifest = self.enqueue()
        self.store.next_job()
        inputs = self.inputs(manifest, "deepmind")
        self.assertIsNone(self.store.retrieval_effect_outcome("daily", "retrieval-deepmind", inputs))
        self.store.reserve("daily", "retrieval-deepmind", inputs, source_requests=1)
        changed = deepcopy(inputs)
        changed["policy"]["query"] = "changed"
        with self.assertRaisesRegex(ServiceError, "EFFECT_INPUT_CHANGED"):
            self.store.record_retrieval_failure("daily", "retrieval-deepmind", changed, "TIME_LIMIT")
        for name in ("model-researcher", "retrieval-not-registered", "primary-0"):
            with self.subTest(name=name), self.assertRaisesRegex(ServiceError, "RETRIEVAL_EFFECT_SCOPE_INVALID"):
                self.store.record_retrieval_failure("daily", name, inputs, "TIME_LIMIT")
        self.store.record_retrieval_failure("daily", "retrieval-deepmind", inputs, "TIME_LIMIT")
        self.assertEqual(self.store.retrieval_effect_outcome("daily", "retrieval-deepmind", inputs),
                         {"state": "unknown", "error_code": "TIME_LIMIT"})
        self.assertEqual(self.store.inspect("daily")["job"]["status"], "running")
        with self.assertRaisesRegex(ServiceError, "EFFECT_NOT_STARTED"):
            self.store.record_retrieval_failure("daily", "retrieval-deepmind", inputs, "TIME_LIMIT", ambiguous=False)
        self.assertEqual(self.store.inspect("daily")["effects"][0]["state"], "unknown")

    def test_store_failure_api_cannot_mutate_native_research_effects(self):
        settings = demo_config()
        store = Store(self.directory.parent / "native", settings, initialize=True)
        manifest = make_manifest(ROOT, settings, settings["schedules"][0], fixture=True)
        store.enqueue("native", manifest)
        store.next_job()
        inputs = {"manifest_digest": digest(manifest), "policy": {"source": "arxiv"}}
        store.reserve("native", "retrieval-arxiv", inputs, source_requests=1)
        with self.assertRaisesRegex(ServiceError, "RETRIEVAL_EFFECT_SCOPE_INVALID"):
            store.record_retrieval_failure("native", "retrieval-arxiv", inputs, "TIME_LIMIT")
        self.assertEqual(store.inspect("native")["effects"][0]["state"], "started")

    def test_corrupted_gap_checkpoint_is_not_accepted(self):
        self.enqueue()
        original = self.store.checkpoint
        def stop(job, name, inputs, output=None):
            result = original(job, name, inputs, output)
            if name == "retrieval-failure-deepmind" and output is not None:
                raise KeyboardInterrupt
            return result
        with patch.object(self.store, "checkpoint", side_effect=stop), self.assertRaises(KeyboardInterrupt):
            self.runner().drain()
        with sqlite3.connect(self.store.path) as db:
            db.execute("UPDATE steps SET output='{}' WHERE name='retrieval-failure-deepmind'")
        self.store = Store(self.directory, self.config)
        result = self.runner(source=lambda *a, **k: self.fail("after corrupt checkpoint")).drain()[0]
        self.assertEqual(result["error"], "CHECKPOINT_CORRUPT")
        self.assertNotIn("report", self.store.inspect("daily")["steps"])


if __name__ == "__main__":
    unittest.main()
