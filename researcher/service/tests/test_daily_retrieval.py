from __future__ import annotations

import copy
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from researcher.scripts.schema_contract import sha256_bytes
from researcher.service import demo
from researcher.service.context_digest import build_context_digest as real_digest
from researcher.service.contracts import ServiceError, load_config
from researcher.service.store import Store
from researcher.service.workflow import Workflow, admit_due, make_manifest

ROOT = Path(__file__).resolve().parents[3]
DAY = 1_790_208_000  # Whole UTC day; explicit fixtures do not depend on the clock.


def config():
    value = json.loads((ROOT / "researcher/service/config.retrieval.example.json").read_text())
    value["schedules"][0]["sources"] = ["deepmind"]
    value["schedules"][0]["source_queries"] = {"deepmind": ""}
    return load_config(json.dumps(value))


def lane(name, query, directory, *, start_time, end_time, credential=None):
    text = "A discovery observation, not qualified research evidence."
    return {"source": name, "state": "observed", "next_cursor": "more-pages",
            "captures": [], "receipt": {"request_count": 1, "total_bytes": len(text), "item_count": 1},
            "coverage": {"schema": "retrieval-coverage/v1", "window_start": start_time,
                "window_end": end_time, "window_applied": False, "window_resolution": "not_applied",
                "query_sha256": sha256_bytes(query.encode()),
                "mode": "fixture", "page_limit": 1, "returned_count": 1,
                "continuation_available": True, "partial": True,
                "completeness": "bounded_page_not_exhaustive", "quality_assessed": False},
            "evidence": [{"id": name + ":fixture", "source": name,
                "url": "https://example.org/fixture", "text": text,
                "sha256": sha256_bytes(text.encode()), "evidence_scope": "discovery_summary",
                "metadata": [["summary_kind", "description"], ["summary_truncated", "false"]]}]}


def packet(query, lanes, **kwargs):
    return {"schema": "research-context-digest/v1", "authority": "none",
            "evidence_qualified": False, "items": [e for item in lanes for e in item["evidence"]],
            "history_count": len(kwargs.get("previous", []))}


class DailyRetrievalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name).resolve() / "state"
        self.config = config()
        self.store = Store(self.directory, self.config, initialize=True)
        self.builder = patch("researcher.service.context_digest.build_context_digest", side_effect=packet)
        self.build = self.builder.start()
        self.addCleanup(self.builder.stop)

    def manifest(self, end=DAY, fixture=True):
        return make_manifest(ROOT, self.config, self.config["schedules"][0],
                             fixture=fixture, window_end=end)

    def enqueue(self, job="daily", end=DAY, fixture=True):
        manifest = self.manifest(end, fixture)
        self.store.enqueue(job, manifest)
        return manifest

    def runner(self, source=lane, verify=lambda *a, **k: None, live=False):
        def forbidden(*args, **kwargs):
            self.fail("retrieval crossed into model, credential or research-source execution")
        return Workflow(self.store, ROOT, live=live, model=forbidden, source=forbidden,
                        credential=forbidden, retrieval_source=source, retrieval_verify=verify)

    def test_retrieval_finishes_without_model_mcp_or_publication(self):
        self.enqueue()
        with patch("researcher.service.workflow.Workflow.ask", side_effect=AssertionError("model")), \
             patch("researcher.service.github.publish_proposal", side_effect=AssertionError("github")), \
             patch("researcher.service.mcp_worker.bounded_collect_mcp", side_effect=AssertionError("mcp")):
            result = self.runner().drain()[0]
        self.assertNotIn("error", result)
        self.assertEqual(result["result"]["disposition"], "retrieval_only")
        self.assertFalse(result["result"]["evidence_qualified"])
        self.assertEqual(self.store.status()["jobs"][0]["status"], "retrieval_complete")
        self.assertEqual(self.store.status()["usage"][0]["model_calls"], 0)
        self.assertEqual(self.store.status()["usage"][0]["reserved_microusd"], 0)
        self.assertEqual(self.runner().drain(), [])
        self.assertNotIn("freeze", self.store.inspect("daily")["steps"])

    def test_live_execution_remains_explicit(self):
        self.enqueue(fixture=False)
        self.assertEqual(self.runner().drain()[0]["error"], "LIVE_EXECUTION_REQUIRES_OPT_IN")

    def test_real_digest_receives_qualified_boundaries_and_prior_observations(self):
        self.build.side_effect = real_digest
        self.enqueue("previous", DAY - 86400)
        first = self.runner().drain()[0]
        self.assertNotIn("error", first)
        self.enqueue()
        second = self.runner().drain()[0]
        self.assertNotIn("error", second)
        packet = second["result"]["context_digest"]
        self.assertEqual(packet["authority"], "none")
        self.assertFalse(packet["evidence_qualified"])
        self.assertEqual(len(self.build.call_args.kwargs["previous"]), 1)
        self.assertEqual(len(packet["observations"]), 1)

    def test_fixture_requires_explicit_offline_retrieval_adapters(self):
        self.enqueue()
        result = Workflow(self.store, ROOT).drain()[0]
        self.assertEqual(result["error"], "FIXTURE_REQUIRES_OFFLINE_ADAPTERS")

    def test_rate_limited_and_empty_lanes_produce_visible_digest(self):
        def empty(name, query, directory, **kwargs):
            result = lane(name, query, directory, **kwargs)
            result.update(state="rate_limited", evidence=[], retry_after_seconds=3600)
            result["coverage"].update(returned_count=0)
            return result
        self.enqueue()
        result = self.runner(empty).drain()[0]
        self.assertNotIn("error", result)
        self.assertEqual(result["result"]["sources"], [{"source": "deepmind", "state": "rate_limited", "items": 0}])
        self.assertEqual(self.build.call_args.args[1][0]["retry_after_seconds"], 3600)

    def test_daily_admission_grace_duplicate_and_coalesced_window(self):
        with patch("researcher.service.workflow.retrieve_corpus", side_effect=AssertionError("corpus read")):
            self.assertEqual(admit_due(self.store, ROOT, now=DAY), [])
            self.assertEqual(len(admit_due(self.store, ROOT, now=DAY + 30)), 1)
            self.assertEqual(admit_due(self.store, ROOT, now=DAY + 40), [])
            later = admit_due(self.store, ROOT, now=DAY + 10 * 86400 + 30)
        self.assertEqual(len(later), 1)
        manifest = json.loads(self.store.inspect(later[0])["job"]["manifest"])
        self.assertEqual(manifest["window_start"], DAY + 9 * 86400)
        self.assertEqual(manifest["window_end"], DAY + 10 * 86400)

    def test_restart_after_completed_source_replays_without_request_or_charge(self):
        self.enqueue()
        def crash(*args, **kwargs):
            raise KeyboardInterrupt
        with self.assertRaises(KeyboardInterrupt):
            self.runner(verify=crash).drain()
        self.store = Store(self.directory, self.config)
        result = self.runner(source=lambda *a, **k: self.fail("duplicate request")).drain()[0]
        self.assertNotIn("error", result)
        self.assertEqual(self.store.status()["usage"][0]["source_request_reservations"], 1)

    def test_unknown_source_after_restart_is_not_retried(self):
        self.enqueue()
        def crash(*args, **kwargs):
            raise KeyboardInterrupt
        with self.assertRaises(KeyboardInterrupt):
            self.runner(source=crash).drain()
        self.store = Store(self.directory, self.config)
        result = self.runner(source=lambda *a, **k: self.fail("duplicate request")).drain()[0]["result"]
        self.assertTrue(result["reconciliation_required"])
        self.assertEqual(result["source_failures"][0]["error_code"], "PROCESS_INTERRUPTED")
        self.assertEqual(result["context_digest"]["items"], [])
        self.assertEqual(self.runner(source=lambda *a, **k: self.fail("duplicate request")).drain(), [])
        self.assertEqual(self.store.status()["jobs"][0]["status"], "reconciliation_required")
        self.assertEqual(self.store.status()["usage"][0]["source_request_reservations"], 1)

    def test_prior_digest_selection_is_bound_to_completed_earlier_windows(self):
        self.enqueue("previous", DAY - 86400)
        self.runner().drain()
        self.enqueue("same-window", DAY)
        self.runner().drain()
        current = self.enqueue("current", DAY)
        prior = self.store.prior_retrieval("current", current)
        self.assertEqual([item["window_end"] for item in prior], [DAY - 86400])
        self.runner().drain()
        self.assertEqual(self.build.call_args.kwargs["previous"], prior)

    def test_prior_digest_corruption_fails_closed(self):
        self.enqueue("previous", DAY - 86400)
        self.runner().drain()
        current = self.enqueue("current", DAY)
        with sqlite3.connect(self.store.path) as db:
            db.execute("UPDATE steps SET output='{}' WHERE job='previous' AND name='report'")
        with self.assertRaisesRegex(ServiceError, "HISTORY_DIGEST_MISMATCH"):
            self.store.prior_retrieval("current", current)

    def test_prior_digest_history_is_bounded_and_excludes_future_fixture_mix(self):
        for index in range(1, 10):
            self.enqueue("past-" + str(index), DAY - index * 86400)
            self.runner().drain()
        self.enqueue("future", DAY + 86400)
        self.runner().drain()
        self.enqueue("live-past", DAY - 86400, fixture=False)
        self.runner(live=True).drain()
        current = self.enqueue()
        prior = self.store.prior_retrieval("daily", current)
        self.assertEqual([entry["window_end"] for entry in prior],
                         [DAY - index * 86400 for index in range(1, 8)])

    def test_restart_keeps_prior_selection_frozen(self):
        self.enqueue()
        self.build.side_effect = KeyboardInterrupt
        with self.assertRaises(KeyboardInterrupt):
            self.runner().drain()
        self.assertEqual(self.store.inspect("daily")["steps"]["prior-retrieval"], {"entries": []})
        self.store = Store(self.directory, self.config)
        self.build.side_effect = packet
        with patch.object(self.store, "prior_retrieval", side_effect=AssertionError("history reselected")):
            result = self.runner(source=lambda *a, **k: self.fail("request repeated")).drain()[0]
        self.assertNotIn("error", result)
        self.assertEqual(self.build.call_args.kwargs["previous"], [])

    def test_cache_reuse_is_window_query_and_policy_bound(self):
        self.enqueue("first", fixture=False)
        calls = []
        def source(*args, **kwargs):
            calls.append((args[1], kwargs["start_time"], kwargs["end_time"]))
            return lane(*args, **kwargs)
        self.runner(source=source, live=True).drain()
        self.enqueue("same", fixture=False)
        self.runner(source=source, live=True).drain()
        self.assertEqual(len(calls), 1)
        self.enqueue("next", end=DAY + 86400, fixture=False)
        self.runner(source=source, live=True).drain()
        self.assertEqual(len(calls), 2)
        self.assertEqual(self.store.status()["usage"][0]["source_request_reservations"], 2)

    def test_source_request_budget_stops_before_collector(self):
        self.config["limits"]["daily_source_requests"] = 1
        self.store = Store(self.directory.parent / "budget-state", self.config, initialize=True)
        self.enqueue("first")
        self.runner().drain()
        self.enqueue("next", DAY + 86400)
        result = self.runner(source=lambda *a, **k: self.fail("unreserved source request")).drain()[0]
        self.assertEqual(result["error"], "BUDGET_EXHAUSTED")
        self.assertEqual(self.store.status()["usage"][0]["source_request_reservations"], 1)

    def test_paid_source_reservation_remains_charged_and_blocks_next_attempt(self):
        self.config["schedules"][0].update(sources=["x"], source_queries={"x": "agent memory"})
        self.config.update(source_credentials={"x": "FIXTURE_X_TOKEN"}, source_cost_microusd={"x": 100})
        self.config["limits"].update(run_budget_microusd=100, daily_budget_microusd=100)
        self.config = load_config(json.dumps(self.config))
        self.store = Store(self.directory.parent / "paid-policy-state", self.config, initialize=True)
        self.enqueue("first")
        runner = self.runner()
        runner.credential = lambda name: "synthetic-token-never-sent"
        self.assertNotIn("error", runner.drain()[0])
        self.assertEqual(self.store.status()["usage"][0]["reserved_microusd"], 100)
        self.enqueue("next", DAY + 86400)
        runner.retrieval_source = lambda *a, **k: self.fail("unreserved paid request")
        self.assertEqual(runner.drain()[0]["error"], "BUDGET_EXHAUSTED")

    def test_bad_paid_credential_fails_before_reservation_or_source_call(self):
        self.config["schedules"][0].update(sources=["x"], source_queries={"x": "agent memory"})
        self.config.update(source_credentials={"x": "FIXTURE_X_TOKEN"}, source_cost_microusd={"x": 100})
        self.config["limits"].update(run_budget_microusd=100, daily_budget_microusd=100)
        self.config = load_config(json.dumps(self.config))
        for index, secret in enumerate(("short", "bad token", None)):
            self.store = Store(self.directory.parent / f"bad-token-{index}", self.config, initialize=True)
            self.enqueue("invalid-token")
            runner = self.runner(source=lambda *a, **k: self.fail("invalid credential reached source"))
            runner.credential = lambda name: secret
            result = runner.drain()[0]
            self.assertEqual(result["error"], "INVALID_SOURCE_CREDENTIAL")
            self.assertEqual(self.store.inspect("invalid-token")["effects"], [])
            self.assertEqual(sum(row["reserved_microusd"] for row in self.store.status()["usage"]), 0)

    def test_failed_retrieval_does_not_pollute_native_research_memory(self):
        mixed = demo.demo_config()
        mixed["schedules"].append(self.config["schedules"][0])
        mixed = load_config(json.dumps(mixed))
        store = Store(self.directory.parent / "mixed-state", mixed, initialize=True)
        failed = make_manifest(ROOT, mixed, mixed["schedules"][1], fixture=True, window_end=DAY)
        store.enqueue("failed-retrieval", failed)
        self.assertEqual(store.next_job()["id"], "failed-retrieval")
        store.finish("failed-retrieval", "failed", "SOURCE_REPLAY_MISMATCH")
        research = make_manifest(ROOT, mixed, mixed["schedules"][0], fixture=True)
        store.enqueue("research", research)
        self.assertEqual(store.prior_feedback("research", research)["entries"], [])

    def test_thirty_logical_days_deterministic_simulation_not_quality_benchmark(self):
        """Exercise orchestration and accounting, not live coverage or research quality.

        The injected manifest factory keeps every report fixture=true. Real
        admission, reservations, checkpoints, restart recovery, history selection
        and context-digest code execute against private temporary SQLite state.
        Synthetic paid-source reservations test accounting; no bill is incurred.
        """
        self.config["schedules"][0].update(sources=["x"], source_queries={"x": "agent memory"})
        self.config.update(source_credentials={"x": "FIXTURE_X_TOKEN"}, source_cost_microusd={"x": 100})
        self.config["limits"].update(run_budget_microusd=100, daily_budget_microusd=100,
                                     daily_source_requests=1, run_source_requests=1)
        self.config = load_config(json.dumps(self.config))
        self.store = Store(self.directory.parent / "month-simulation", self.config, initialize=True)
        self.build.side_effect = real_digest
        requests, credential_reads, verified, reports, admitted_jobs = [], [], [], [], []
        interrupted = False

        def fixture_manifest(root, value, schedule, **kwargs):
            return make_manifest(root, value, schedule, fixture=True,
                                 window_end=kwargs.get("window_end"))

        def source(name, query, directory, *, start_time, end_time, credential=None):
            index = (end_time - DAY) // 86400
            requests.append(index)
            self.assertEqual(credential, "synthetic-month-token-never-sent")
            observed = lane(name, query, directory, start_time=start_time, end_time=end_time)
            observed["next_cursor"] = None
            observed["coverage"].update(continuation_available=False, window_applied=True,
                window_resolution="second", mode="deterministic_month_fixture",
                query_sha256=sha256_bytes(query.encode()), partial=False)
            if index in {7, 14}:
                observed["evidence"] = []
                observed["receipt"]["item_count"] = 0
                observed["coverage"]["returned_count"] = 0
                if index == 14:
                    observed.update(state="rate_limited", retry_after_seconds=3600)
                    observed["coverage"]["partial"] = True
            else:
                text = f"Synthetic agent memory observation, revision {index // 5}; not real research."
                observed["evidence"][0].update(text=text, sha256=sha256_bytes(text.encode()))
                observed["receipt"]["total_bytes"] = len(text.encode())
            return observed

        def verify(name, query, observed, directory, *, start_time, end_time):
            nonlocal interrupted
            index = (end_time - DAY) // 86400
            verified.append(index)
            self.assertEqual(observed["source"], name)
            self.assertEqual(observed["coverage"]["window_start"], start_time)
            self.assertEqual(observed["coverage"]["window_end"], end_time)
            for entry in observed["evidence"]:
                self.assertEqual(entry["sha256"], sha256_bytes(entry["text"].encode()))
            if index == 10 and not interrupted:
                interrupted = True
                raise KeyboardInterrupt  # After the source effect has been durably completed.

        def runner():
            value = self.runner(source=source, verify=verify)
            def credential(name):
                credential_reads.append(name)
                self.assertEqual(name, "FIXTURE_X_TOKEN")
                return "synthetic-month-token-never-sent"
            value.credential = credential
            return value

        with patch("researcher.service.workflow.make_manifest", side_effect=fixture_manifest), \
             patch("researcher.service.workflow.Workflow.ask", side_effect=AssertionError("model call")), \
             patch("researcher.service.github.publish_proposal", side_effect=AssertionError("GitHub call")), \
             patch("researcher.service.mcp_worker.bounded_collect_mcp", side_effect=AssertionError("MCP call")), \
             patch("socket.socket", side_effect=AssertionError("network is forbidden in this fixture")):
            for index in range(30):
                now = DAY + index * 86400 + 30
                with patch("researcher.service.workflow.time.time", return_value=now):
                    admitted = admit_due(self.store, ROOT, now=now)
                    self.assertEqual(len(admitted), 1)
                    admitted_jobs.extend(admitted)
                    self.assertEqual(admit_due(self.store, ROOT, now=now), [])
                    if index == 10:
                        with self.assertRaises(KeyboardInterrupt):
                            runner().drain()
                        self.assertEqual(requests.count(index), 1)
                        self.store = Store(self.store.directory, self.config)
                        self.assertEqual(admit_due(self.store, ROOT, now=now), [])
                    result = runner().drain()[0]
                    self.assertNotIn("error", result)
                    report = result["result"]
                    reports.append(report)
                    self.assertTrue(report["fixture"])
                    self.assertEqual(report["disposition"], "retrieval_only")
                    self.assertFalse(report["evidence_qualified"])
                    self.assertFalse(report["production_ready"])
                    self.assertEqual(report["context_digest"]["signals"]["history_windows"], min(index, 7))
                    self.assertFalse(report["context_digest"]["semantic_quality_measured"])
                    retained = self.store.inspect(admitted[0])["steps"]["prior-retrieval"]["entries"]
                    self.assertEqual(len(retained), min(index, 7))
                    self.assertTrue(all(item["window_end"] < report["window_end"] for item in retained))
                    self.assertEqual(runner().drain(), [])
                    usage = self.store.status()["usage"][0]
                    self.assertEqual(usage["source_request_reservations"], 1)
                    self.assertEqual(usage["reserved_microusd"], 100)
                    self.assertEqual(usage["model_calls"], 0)

        self.assertEqual(len(admitted_jobs), len(set(admitted_jobs)))
        self.assertEqual(requests, list(range(30)))
        self.assertEqual(len(credential_reads), 30)
        self.assertEqual(len(verified), 31)  # One replay, no repeated source effect.
        self.assertEqual(reports[1]["context_digest"]["signals"]["reobserved_versions"], 1)
        self.assertEqual(reports[5]["context_digest"]["signals"]["new_observation_versions"], 1)
        self.assertEqual(reports[5]["context_digest"]["signals"]["reobserved_work_keys"], 1)
        self.assertEqual(sum(report["context_digest"]["signals"]["new_observation_versions"]
                             for report in reports), 6)
        self.assertEqual(reports[7]["sources"][0], {"source": "x", "state": "observed", "items": 0})
        self.assertEqual(reports[14]["sources"][0], {"source": "x", "state": "rate_limited", "items": 0})
        self.assertEqual(reports[14]["context_digest"]["coverage"][0]["gap"], "rate_limited")
        self.assertEqual(sum(len(report["context_digest"]["observations"]) for report in reports), 28)
        with sqlite3.connect(self.store.path) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM jobs WHERE status='retrieval_complete'").fetchone()[0], 30)
            self.assertEqual(db.execute("SELECT count(*),sum(source_requests),sum(model_calls),sum(reserved_microusd) "
                                        "FROM effects WHERE state='completed'").fetchone(), (30, 30, 0, 3000))


class RetrievalContractTests(unittest.TestCase):
    def test_free_example_needs_no_models_or_paid_credentials(self):
        value = load_config((ROOT / "researcher/service/config.retrieval.example.json").read_text())
        self.assertEqual(value["models"], {})
        self.assertEqual(value["limits"]["daily_model_calls"], 0)
        self.assertEqual(value["source_credentials"], {})

    def test_default_research_cannot_disable_models_or_use_discovery_only_sources(self):
        for change in ("models", "calls", "sources", "skills"):
            value = demo.demo_config()
            if change == "models":
                value["models"] = {}
            elif change == "calls":
                value["limits"]["daily_model_calls"] = 0
            elif change == "sources":
                value["schedules"][0]["sources"] = ["x"]
            else:
                value["schedules"][0].pop("skills")
            with self.subTest(change=change), self.assertRaises(ServiceError):
                load_config(json.dumps(value))

    def test_retrieval_rejects_missing_queries_mcp_and_non_daily_schedules(self):
        for mutation in ({"source_queries": {}}, {"interval_seconds": 3600},
                         {"mcp_reads": [{"id": "unexpected", "arguments": {}}]}):
            value = config()
            value["schedules"][0].update(mutation)
            with self.assertRaises(ServiceError):
                load_config(json.dumps(value))

    def test_paid_sources_need_explicit_credential_and_positive_cost_policy(self):
        value = config()
        value["schedules"][0].update(sources=["x"], source_queries={"x": "context engineering"})
        for credentials, costs in (({}, {}), ({"x": "X_BEARER_TOKEN"}, {}),
                                    ({"x": "X_BEARER_TOKEN"}, {"x": 0})):
            candidate = copy.deepcopy(value)
            candidate.update(source_credentials=credentials, source_cost_microusd=costs)
            with self.assertRaises(ServiceError):
                load_config(json.dumps(candidate))
        value.update(source_credentials={"x": "X_BEARER_TOKEN"}, source_cost_microusd={"x": 100})
        value["limits"].update(run_budget_microusd=100, daily_budget_microusd=100)
        self.assertEqual(load_config(json.dumps(value))["source_cost_microusd"]["x"], 100)


if __name__ == "__main__":
    unittest.main()
