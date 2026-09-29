from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from researcher.service.connector_campaign import definitions, implementation_digest, run_campaign, source_probe
from researcher.service.contracts import ServiceError


class ConnectorCampaignTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state = Path(self.tmp.name).resolve() / "state"
        self.values = {"OPENAI_API_KEY": "fixture-key-not-real", "PARALLEL_API_KEY": "fixture-parallel-key"}
        self.calls = []
        self.progress = []
        self.options = dict(names=["openai_models", "parallel_search"], max_budget_microusd=2000,
                            live=True, probe=self.probe, progress=self.progress.append)

    def probe(self, probe, credential):
        self.calls.append(probe.name)
        return {"schema": "connector-probe/v1", "name": probe.name, "classification": "success",
                "http_status": 200, "counts": {"result_count": 1}}

    def run_check(self, **kwargs):
        return run_campaign(self.state, self.values, **{**self.options, **kwargs})

    def test_dry_run_has_no_files_or_calls(self):
        report = self.run_check(live=False)
        self.assertFalse(report["network_checked"])
        self.assertEqual(report["request_ceiling"], 2)
        self.assertEqual(report["reserved_microusd_ceiling"], 1000)
        self.assertFalse(self.state.exists())
        self.assertFalse(self.calls)

    def test_manifest_bound_replay_never_reads_new_key_or_calls(self):
        report = self.run_check()
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(report["usage"][0]["reserved_microusd"], 1000)
        self.assertEqual(len(self.progress), 4)
        self.values = {}
        replayed = self.run_check(probe=lambda *args: self.fail("repeated network"))
        self.assertEqual({**report, "replayed": True}, replayed)

    def test_cached_report_does_not_validate_changed_or_read_current_credentials(self):
        report = self.run_check()
        self.values = {"OPENAI_API_KEY": "bad\nkey"}
        self.assertEqual(self.run_check(), {**report, "replayed": True})
        class NoRead(dict):
            def get(self, *_args):
                raise AssertionError("cached report read a credential")
        self.values = NoRead()
        with sqlite3.connect(self.state / "service.sqlite3") as db:
            event_count = db.execute("SELECT count(*) FROM events").fetchone()[0]
        self.assertEqual(self.run_check(), {**report, "replayed": True})
        with sqlite3.connect(self.state / "service.sqlite3") as db:
            self.assertEqual(db.execute("SELECT count(*) FROM events").fetchone()[0], event_count)
        self.assertEqual(len(self.calls), 2)

    def test_crash_after_report_checkpoint_finalizes_without_repeating_effects(self):
        with patch("researcher.service.connector_campaign.Store.finish", side_effect=RuntimeError("fixture crash")):
            with self.assertRaises(RuntimeError):
                self.run_check()
        self.assertEqual(len(self.calls), 2)
        self.values = {"OPENAI_API_KEY": "bad\nkey"}
        replayed = self.run_check(probe=lambda *_args: self.fail("repeated network"))
        self.assertTrue(replayed["replayed"])
        with sqlite3.connect(self.state / "service.sqlite3") as db:
            self.assertEqual(db.execute("SELECT status FROM jobs WHERE id='connector-checks'").fetchone()[0],
                             "retrieval_complete")
        self.assertEqual(len(self.calls), 2)

    def test_changed_selection_or_budget_cannot_reset_cumulative_cap(self):
        self.run_check()
        for changes in ({"names": ["openai_models"]}, {"max_budget_microusd": 3000}):
            with self.subTest(changes=changes), self.assertRaises(ServiceError):
                self.run_check(**changes)
        self.assertEqual(len(self.calls), 2)

    def test_changed_implementation_blocks_resume(self):
        self.run_check()
        with patch("researcher.service.connector_campaign.implementation_digest", return_value="changed"):
            with self.assertRaises(ServiceError):
                self.run_check()

    def test_contracts_and_retrieval_setup_are_implementation_bound(self):
        seen, changed = set(), set()
        def read(path):
            seen.add(path.name)
            return b"changed" if path.name in changed else b"fixture source"
        with patch.object(Path, "read_bytes", autospec=True, side_effect=read):
            initial = implementation_digest()
            for name in ("contracts.py", "retrieval_setup.py"):
                self.assertIn(name, seen)
                changed.add(name)
                self.assertNotEqual(implementation_digest(), initial)
                changed.clear()

    def test_unknown_outcome_is_reserved_and_never_retried(self):
        def crash(*args):
            raise KeyboardInterrupt
        with self.assertRaisesRegex(ServiceError, "DIAGNOSTIC_RECONCILIATION_REQUIRED"):
            self.run_check(probe=crash)
        with self.assertRaisesRegex(ServiceError, "DIAGNOSTIC_RECONCILIATION_REQUIRED"):
            self.run_check(probe=lambda *args: self.fail("retry"))

    def test_missing_keys_are_not_sent_or_reported_as_invalid(self):
        self.values = {}
        report = self.run_check()
        self.assertEqual([r["classification"] for r in report["results"]], ["not_configured"] * 2)
        self.assertFalse(self.calls)
        self.assertFalse(report["usage"])
        self.assertFalse(report["network_checked"])
        self.assertFalse(self.progress)

    def test_invalid_credential_rejected_before_state_creation(self):
        self.values["OPENAI_API_KEY"] = "bad\nkey"
        with self.assertRaises(ServiceError):
            self.run_check()
        self.assertFalse(self.state.exists())

    def test_reflected_credential_is_not_persisted(self):
        def leak(probe, key):
            return {"classification": key}
        with self.assertRaises(ServiceError):
            self.run_check(probe=leak)
        for file in self.state.glob("service.sqlite3*"):
            self.assertNotIn(self.values["OPENAI_API_KEY"].encode(), file.read_bytes())

    def test_budget_selection_and_concurrency_fail_before_state(self):
        for change in ({"max_budget_microusd": 999}, {"max_budget_microusd": True},
                       {"names": ["unknown"]}, {"names": ["openai_models"] * 2},
                       {"concurrency": 2}, {"concurrency": True}):
            with self.subTest(change=change), self.assertRaises(ServiceError):
                self.run_check(**change)
        self.assertFalse(self.state.exists())

    def test_source_probe_is_explicitly_bound_and_reserved(self):
        calls = []
        def source(name, key, directory, *, end_time):
            calls.append((name, end_time))
            return {"name": name, "classification": "success", "http_status": 200, "counts": {"items": 0}}
        self.values["X_BEARER_TOKEN"] = "fixture-x-key"
        result = self.run_check(names=["x"], max_budget_microusd=50_000, source=source, now=1_790_000_000)
        self.assertEqual(calls, [("x", 1_789_999_940)])
        self.assertEqual(result["usage"][0]["reserved_microusd"], 50_000)
        self.run_check(names=["x"], max_budget_microusd=50_000, source=source, now=1_790_000_010)
        self.assertEqual(len(calls), 1)

    def test_mcp_handshake_requests_are_reserved_before_one_session_and_replay(self):
        calls = []
        def mcp(key):
            calls.append(key)
            with sqlite3.connect(self.state / "service.sqlite3") as db:
                count = db.execute("SELECT source_requests FROM effects").fetchone()[0]
            self.assertEqual(count, 4)
            return {"name": "parallel_mcp_fetch", "classification": "success", "http_status": 200,
                    "counts": {"http_requests": 4, "tool_calls": 1}}
        options = {"names": ["parallel_mcp_fetch"], "max_budget_microusd": 10_000, "mcp": mcp}
        plan = self.run_check(**options, live=False)
        self.assertEqual(plan["request_ceiling"], 4)
        result = self.run_check(**options)
        self.assertEqual(result["usage"][0]["reserved_microusd"], 10_000)
        self.assertEqual(len(calls), 1)
        self.assertTrue(self.run_check(**options)["replayed"])
        self.assertEqual(len(calls), 1)

    def test_twenty_request_cap_includes_protocol_overhead(self):
        available = definitions()
        available["parallel_mcp_fetch"]["request_ceiling"] = 21
        with patch("researcher.service.connector_campaign.definitions", return_value=available):
            with self.assertRaisesRegex(ServiceError, "DIAGNOSTIC_REQUEST_LIMIT"):
                self.run_check(names=["parallel_mcp_fetch"], max_budget_microusd=10_000)
        self.assertFalse(self.state.exists())

    def test_registered_bridge_reserves_twelve_requests_once(self):
        calls = []
        def bridge(key):
            calls.append(key)
            with sqlite3.connect(self.state / "service.sqlite3") as db:
                count = db.execute("SELECT source_requests FROM effects").fetchone()[0]
            self.assertEqual(count, 12)
            return {"name": "parallel_registered_fetch", "classification": "success",
                    "http_status": None, "counts": {"result_count": 1}}
        options = {"names": ["parallel_registered_fetch"], "max_budget_microusd": 10_000,
                   "registered_mcp": bridge}
        report = self.run_check(**options)
        self.assertEqual(report["usage"][0]["source_request_reservations"], 12)
        self.assertTrue(self.run_check(**options)["replayed"])
        self.assertEqual(len(calls), 1)

    def test_x_field_presence_counts_read_verified_capture_not_source_text(self):
        lane = {"receipt": {"observations": [{"status_code": 200}]}, "state": "observed",
                "evidence": [{"metadata": []}, {"metadata": []}], "captures": [{"fixture": "capture"}]}
        rows = [{"created_at": "2026-09-29T00:00:00Z", "public_metrics": {"like_count": 0},
                 "conversation_id": "1", "author_id": "2", "lang": "en", "entities": {},
                 "text": "private synthetic text"},
                {"author_id": "3", "lang": "en", "note_tweet": {"text": "private extended text"},
                 "referenced_tweets": [{"type": "replied_to", "id": "4"}]}]
        with patch("researcher.service.connector_campaign.retrieval_sources.collect", return_value=lane), \
             patch("researcher.service.connector_campaign.retrieval_sources.verify") as verify, \
             patch("researcher.scripts.research_evidence.LocalResearchEvidenceStore") as evidence:
            def read(_capture):
                verify.assert_called_once()
                return json.dumps({"data": rows}).encode()
            evidence.return_value.read_body.side_effect = read
            report = source_probe("x", "synthetic-fixture-token", self.state, end_time=1_790_000_000)
        self.assertEqual(report["classification"], "success")
        self.assertEqual(report["counts"], {"items": 2, "abstracts": 0, "offline_replays": 1,
                         "x_posts": 2, "x_with_created_at": 1, "x_with_public_metrics": 1,
                         "x_with_conversation_id": 1, "x_with_author_id": 2, "x_with_lang": 2,
                         "x_with_entities": 1, "x_with_note_tweet": 1, "x_with_referenced_tweets": 1})
        self.assertTrue(all(type(value) is int for value in report["counts"].values()))
        self.assertNotIn("private", json.dumps(report))
        evidence.assert_called_once_with(self.state, read_only=True)


if __name__ == "__main__":
    unittest.main()
