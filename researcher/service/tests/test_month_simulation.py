"""Thirty logical UTC days, compressed and entirely offline.

Actual admission, capture adapters/replay, SQLite reservations, checkpoints and
digest history execute. Synthetic provider responses are not month-long live
observations, a scientific-quality benchmark or a deployment availability claim.
"""

from datetime import UTC, datetime
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from researcher.scripts.source_connectors import LimitExceededError, TransportResponse
from researcher.scripts.tests.test_source_connectors import ScriptedTransport
from researcher.scripts.tests.test_source_search import x_payload
from researcher.service import retrieval_sources
from researcher.service.contracts import ServiceError, load_config
from researcher.service.openai_campaign import configuration
from researcher.service.store import Store
from researcher.service.tests.test_daily_retrieval import DAY, ROOT, config
from researcher.service.workflow import Workflow, admit_due, make_manifest


class MonthSimulationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name).resolve()
        self.socket = patch("socket.socket.connect", side_effect=AssertionError("live network forbidden"))
        self.socket.start()
        self.addCleanup(self.socket.stop)

    def test_thirty_scheduled_windows_with_captured_responses_and_fault_probes(self):
        settings = config()
        settings["schedules"][0].update(sources=["x", "deepmind"], query="context memory research",
            source_queries={"x": "context memory", "deepmind": ""})
        settings.update(source_credentials={"x": "SYNTHETIC_X_TOKEN"}, source_cost_microusd={"x": 100})
        settings["limits"].update(run_budget_microusd=100, daily_budget_microusd=200,
                                   daily_source_requests=4, run_source_requests=2)
        settings = load_config(json.dumps(settings))
        store = Store(self.directory / "state", settings, initialize=True)
        attempts, transports, replays, reports, jobs = [], [], [], [], []
        probe = False
        interrupted = False
        adapter_factory = retrieval_sources._adapter

        def fixture_manifest(root, value, schedule, **kwargs):
            return make_manifest(root, value, schedule, fixture=True, window_end=kwargs.get("window_end"))

        def collect(name, query, directory, *, start_time, end_time, credential=None):
            index = (end_time - DAY) // 86400
            attempts.append((index, name, probe))
            if probe and name == "x":
                raise LimitExceededError("TIME_LIMIT", "injected unknown provider outcome")
            status, headers = 200, ()
            if name == "x":
                self.assertEqual(credential, "synthetic-month-token-never-live")
                payload = x_payload()
                payload["data"][0]["created_at"] = datetime.fromtimestamp(start_time + 60, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
                payload["data"][0]["note_tweet"]["text"] = f"Synthetic context memory observation version {index // 5}."
                if index == 7:
                    payload = {"data": [], "meta": {"result_count": 0}}
                if index == 14:
                    status, headers, payload = 429, (("Retry-After", "3600"),), {}
                body, media = json.dumps(payload).encode(), "application/json"
            else:
                body = ("<rss><channel><item><title>Context memory research</title>"
                        "<link>https://deepmind.google/blog/context-memory/</link>"
                        f"<description>Synthetic mechanism revision {index // 5}; not scientific evidence.</description>"
                        "</item></channel></rss>").encode()
                media = "application/xml"
            transport = ScriptedTransport(TransportResponse(status, (("Content-Type", media), *headers), body))
            transports.append(transport)
            def offline_adapter(source, start, end, key=None, **kwargs):
                return adapter_factory(source, start, end, key, transport=transport,
                                       resolver=lambda *a: ("93.184.216.34",), **kwargs)
            with patch.object(retrieval_sources, "_adapter", side_effect=offline_adapter):
                return retrieval_sources.collect(name, query, directory, start_time=start_time,
                                                 end_time=end_time, credential=credential)

        def verify(name, query, observed, directory, *, start_time, end_time):
            nonlocal interrupted
            index = (end_time - DAY) // 86400
            replays.append((index, name, probe))
            retrieval_sources.verify(name, query, observed, directory, start_time=start_time, end_time=end_time)
            if index == 10 and name == "x" and not interrupted:
                interrupted = True
                raise KeyboardInterrupt  # Completed effect retained, replay must not issue HTTP.

        def forbidden(*args, **kwargs):
            self.fail("month retrieval crossed model/MCP/GitHub boundary")

        def runner():
            return Workflow(store, ROOT, model=forbidden, source=forbidden,
                credential=lambda name: "synthetic-month-token-never-live",
                retrieval_source=collect, retrieval_verify=verify)

        with patch("researcher.service.workflow.make_manifest", side_effect=fixture_manifest), \
             patch("researcher.service.workflow.Workflow.ask", side_effect=forbidden), \
             patch("researcher.service.github.publish_proposal", side_effect=forbidden), \
             patch("researcher.service.mcp_worker.bounded_collect_mcp", side_effect=forbidden):
            for index in range(30):
                now = DAY + index * 86400 + 30
                with patch("researcher.service.workflow.time.time", return_value=now):
                    admitted = admit_due(store, ROOT, now=now)
                    self.assertEqual(len(admitted), 1)
                    jobs.extend(admitted)
                    self.assertEqual(admit_due(store, ROOT, now=now), [])
                    if index == 3:
                        before = store.status()
                        with self.assertRaisesRegex(ServiceError, "CLOCK_MOVED_BACKWARDS"):
                            admit_due(store, ROOT, now=now - 1)
                        self.assertEqual(before, store.status())
                    if index == 10:
                        with self.assertRaises(KeyboardInterrupt):
                            runner().drain()
                    # Fresh Store object every logical day, plus interrupted-effect replay.
                    store = Store(store.directory, settings)
                    self.assertEqual(admit_due(store, ROOT, now=now), [])
                    result = runner().drain()[0]
                    self.assertNotIn("error", result)
                    report = result["result"]
                    reports.append(report)
                    self.assertTrue(report["fixture"])
                    self.assertFalse(report["evidence_qualified"])
                    self.assertFalse(report["production_ready"])
                    self.assertTrue(report["collection_completed"])
                    self.assertEqual(report["context_digest"]["signals"]["history_windows"], min(index, 7))
                    history = store.inspect(admitted[0])["steps"]["prior-retrieval"]["entries"]
                    self.assertTrue(all(item["window_end"] < report["window_end"] for item in history))
                    self.assertLessEqual(len(history), 7)
                    self.assertEqual(runner().drain(), [])
                    if index == 8:
                        # Extra explicit fault probe, not one of the 30 completed scheduled windows.
                        probe = True
                        store.enqueue("outage-probe", fixture_manifest(ROOT, settings, settings["schedules"][0], window_end=now // 86400 * 86400))
                        partial = runner().drain()[0]["result"]
                        self.assertTrue(partial["reconciliation_required"])
                        self.assertEqual(partial["source_failures"][0]["effect_state"], "unknown")
                        self.assertEqual(partial["sources"][1]["state"], "observed")
                        store = Store(store.directory, settings)
                        self.assertEqual(runner().drain(), [])
                        probe = False
                    if index == 20:
                        store.enqueue("budget-probe", fixture_manifest(ROOT, settings, settings["schedules"][0], window_end=now // 86400 * 86400))
                        self.assertEqual(store.next_job()["id"], "budget-probe")
                        with self.assertRaisesRegex(ServiceError, "BUDGET_EXHAUSTED"):
                            store.reserve("budget-probe", "unadmitted", {}, source_requests=1, micros=201)
                        self.assertEqual(store.inspect("budget-probe")["effects"], [])
                        store.finish("budget-probe", "failed", "BUDGET_EXHAUSTED")

        self.assertEqual(len(set(jobs)), 30)
        self.assertEqual(len(attempts), 62)  # 60 scheduled lanes +2 outage probe lanes.
        self.assertEqual(len(transports), 61)  # Injected unknown outcome has no transport fixture.
        self.assertEqual(sum(len(transport.requests) for transport in transports), 61)
        self.assertEqual(len(replays), 62)  # 61 retained captures +1 interrupted-effect replay.
        self.assertEqual(attempts.count((10, "x", False)), 1)
        self.assertEqual(replays.count((10, "x", False)), 2)
        self.assertEqual(reports[7]["sources"][0]["items"], 0)
        self.assertEqual(reports[14]["sources"][0]["state"], "rate_limited")
        self.assertGreater(reports[1]["context_digest"]["signals"]["reobserved_versions"], 0)
        self.assertGreater(reports[5]["context_digest"]["signals"]["new_observation_versions"], 0)
        with sqlite3.connect(store.path) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM jobs WHERE status='retrieval_complete'").fetchone()[0], 30)
            self.assertEqual(db.execute("SELECT count(*) FROM jobs WHERE status='reconciliation_required'").fetchone()[0], 1)
            self.assertEqual(db.execute("SELECT count(*),sum(source_requests),sum(model_calls),sum(reserved_microusd) FROM effects").fetchone(), (62, 62, 0, 3100))
            self.assertEqual(db.execute("SELECT count(*) FROM effects WHERE state='unknown'").fetchone()[0], 1)
            self.assertEqual(db.execute("SELECT count(DISTINCT day) FROM effects").fetchone()[0], 30)

    def test_cumulative_authority_does_not_reset_over_thirty_logical_days(self):
        """Only reservation units are simulated; no provider request is constructed."""
        settings = configuration(150, 0)
        store = Store(self.directory / "budget", settings, initialize=True)
        admitted, rejected = 0, 0
        for index in range(30):
            now = DAY + index * 86400 + 30
            with patch("researcher.service.store.time.time", return_value=now):
                store = Store(store.directory, settings)
                job = f"logical-day-{index}"
                store.enqueue(job, {"schema": "offline-reservation-probe/v1", "logical_day": index})
                store.next_job()
                if index < 15:
                    store.reserve(job, "synthetic", {"day": index}, micros=10, model_calls=1, now=now)
                    store.complete_effect(job, "synthetic", {"fixture": True})
                    store.finish(job, "execution_complete")
                    admitted += 1
                else:
                    with self.assertRaisesRegex(ServiceError, "LIFETIME_BUDGET_EXHAUSTED"):
                        store.reserve(job, "synthetic", {"day": index}, micros=10, model_calls=1, now=now)
                    store.finish(job, "failed", "LIFETIME_BUDGET_EXHAUSTED")
                    rejected += 1
        self.assertEqual((admitted, rejected), (15, 15))
        with sqlite3.connect(store.path) as db:
            self.assertEqual(db.execute("SELECT count(*),sum(reserved_microusd) FROM effects").fetchone(), (15, 150))


if __name__ == "__main__":
    unittest.main()
