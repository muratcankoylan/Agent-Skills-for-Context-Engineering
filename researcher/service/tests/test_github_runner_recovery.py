"""Composite ephemeral-runner loss drills; fake provider, no GitHub/network.

These are offline file/SQLite recovery scenarios, not managed-service uptime or
scientific effectiveness measurements. A pre-effect bundle cannot attest that
the original runner performed no effects after its snapshot was taken.
"""

import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from researcher.service import demo, recovery_bundle
from researcher.service.agents_runtime import ManagedResearch, SessionLedger, prepare_packet
from researcher.service.contracts import ServiceError
from researcher.service.store import Store
from researcher.service.tests.test_agents_runtime import FakeAgents
from researcher.service.workflow import make_manifest


ROOT = Path(__file__).resolve().parents[3]


class GithubRunnerRecoveryScenarios(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name).resolve()
        self.config = demo.demo_config()
        self.store = Store(self.directory / "runner-one-state", self.config, initialize=True)
        # This is an explicitly injected manual packet, not a forged production
        # source-handoff receipt. No fixture flags or authority fields are edited.
        self.packet = prepare_packet(ROOT, model="fixture-model-v1",
            query="offline recovery of context transfer research",
            skills=["context-fundamentals"], evidence=demo.source("", "", None)["evidence"])
        self.ledger = SessionLedger.prepare(self.directory / "runner-one-session", self.packet)
        self.provider = FakeAgents(self.packet)
        self.now = 1000
        self.runtime = ManagedResearch(self.ledger, self.provider, clock=lambda: self.now)
        self.bundle = self.directory / "uploaded-private-bundle"
        self.destination = self.directory / "runner-two-restored"
        forbidden = patch("socket.socket.connect", side_effect=AssertionError("network forbidden"))
        forbidden.start()
        self.addCleanup(forbidden.stop)

    def submit(self):
        # Explicit execution flags reach only the injected in-memory provider.
        return self.runtime.submit(live=True, acknowledge_cost_risk=True)

    def snapshot(self):
        self.receipt = recovery_bundle.snapshot(self.store, self.bundle, root=ROOT,
                                                sessions={"research": self.ledger})
        return self.receipt

    def restore(self):
        receipt = recovery_bundle.restore(self.bundle, self.destination, root=ROOT,
            config=self.config, expected_digest=self.receipt["manifest_digest"])
        store = Store(self.destination / "state", self.config)
        ledger = SessionLedger(self.destination / "sessions/research")
        self.assertTrue(store.status()["paused"])
        self.assertFalse(receipt["activation"])
        self.assertFalse(receipt["reconciliation_performed"])
        self.assertNotEqual(ledger.directory, self.ledger.directory)
        return store, ledger, ManagedResearch(ledger, self.provider, clock=lambda: self.now)

    def assert_no_outbox(self, store):
        # This preview stores publication intents/effects in the shared tables,
        # not in a separate outbox table.
        with sqlite3.connect(store.path) as database:
            self.assertEqual(database.execute("SELECT count(*) FROM jobs WHERE status='published'").fetchone()[0], 0)
            self.assertEqual(database.execute("SELECT count(*) FROM steps WHERE name='publication'").fetchone()[0], 0)
            effects = [row[0] for row in database.execute("SELECT name FROM effects")]
            self.assertTrue(all(name == "fixture-read" for name in effects))

    def test_known_session_survives_runner_loss_and_observation_without_recreate(self):
        self.submit()
        original = self.ledger.load()
        self.snapshot()
        store, ledger, runtime = self.restore()
        self.assertEqual(original, ledger.load())
        self.assertEqual(runtime.observe()["session_id"], "as_test")
        self.assertEqual((self.provider.create_count, self.provider.read_count), (1, 1))
        with self.assertRaisesRegex(ServiceError, "CREATE_ALREADY_ATTEMPTED"):
            runtime.submit(live=True, acknowledge_cost_risk=True)
        self.assertEqual(self.provider.create_count, 1)
        self.assert_no_outbox(store)

    def test_unknown_create_survives_restore_without_retry_or_sensitive_error(self):
        self.provider.fail_create = True
        with self.assertRaisesRegex(ServiceError, "RECONCILIATION_REQUIRED"):
            self.submit()
        self.snapshot()
        store, ledger, runtime = self.restore()
        self.assertEqual(ledger.status()["phase"], "reconciliation_required")
        self.assertIsNone(ledger.status()["session_id"])
        self.provider.fail_create = False
        with self.assertRaisesRegex(ServiceError, "CREATE_ALREADY_ATTEMPTED"):
            runtime.submit(live=True, acknowledge_cost_risk=True)
        with self.assertRaisesRegex(ServiceError, "SESSION_ID_UNAVAILABLE"):
            runtime.observe()
        self.assertEqual((self.provider.create_count, self.provider.read_count), (1, 0))
        self.assertNotIn("sensitive remote", (ledger.directory / "session.json").read_text())
        self.assert_no_outbox(store)

    def test_crash_after_durable_intent_before_create_remains_uncertain_after_restore(self):
        # SystemExit models abrupt process loss outside the normal error handler.
        with patch.object(self.provider, "create", side_effect=SystemExit("runner lost")):
            with self.assertRaises(SystemExit):
                self.submit()
        self.assertEqual(self.ledger.status()["phase"], "submitting")
        self.snapshot()
        _, ledger, runtime = self.restore()
        with self.assertRaisesRegex(ServiceError, "CREATE_ALREADY_ATTEMPTED"):
            runtime.submit(live=True, acknowledge_cost_risk=True)
        with self.assertRaisesRegex(ServiceError, "SESSION_ID_UNAVAILABLE"):
            runtime.observe()
        self.assertEqual(ledger.status()["phase"], "reconciliation_required")
        self.assertEqual(self.provider.create_count, 0)

    def test_completed_answer_restores_but_never_becomes_independent_evaluation(self):
        self.submit()
        self.provider.finish()
        self.runtime.observe()
        original = (self.ledger.directory / "result.json").read_bytes()
        self.snapshot()
        store, ledger, runtime = self.restore()
        self.provider.fail_read = True
        reads = self.provider.read_count
        status = runtime.observe()
        self.assertEqual(status["phase"], "completed")
        self.assertEqual(status["reason"], "AWAITING_INDEPENDENT_EVALUATION")
        self.assertFalse(status["production_ready"])
        self.assertEqual(self.provider.read_count, reads)
        self.assertEqual((ledger.directory / "result.json").read_bytes(), original)
        result = json.loads(original)
        self.assertEqual(result["independent_evaluation"], "not_run")
        self.assertIsNone(result["result"]["proposal"])
        self.assertEqual(self.provider.create_count, 1)
        self.assert_no_outbox(store)

    def test_missing_uploaded_result_blob_rejects_restore_without_empty_initialization(self):
        self.submit()
        self.provider.finish()
        self.runtime.observe()
        self.snapshot()
        manifest = json.loads((self.bundle / "manifest.json").read_bytes())
        row = next(row for row in manifest["files"] if row["path"] == "sessions/research/result.json")
        # Only a disposable fixture blob is removed; the source ledger survives.
        (self.bundle / "blobs" / row["sha256"][7:]).unlink()
        with self.assertRaises(ServiceError):
            self.restore()
        self.assertFalse(self.destination.exists())
        self.assertEqual(self.ledger.status()["phase"], "completed")
        self.assertEqual(self.provider.create_count, 1)

    def test_incomplete_artifact_upload_is_not_treated_as_new_empty_state(self):
        self.snapshot()
        (self.bundle / "manifest.json").unlink()
        with self.assertRaisesRegex(ServiceError, "BUNDLE_INCOMPLETE"):
            self.restore()
        self.assertFalse(self.destination.exists())
        self.assertEqual(self.provider.create_count, 0)

    def test_pre_effect_snapshot_does_not_attest_later_remote_effect_absence(self):
        self.snapshot()  # At this point the ledger genuinely is prepared.
        self.submit()  # The original runner later creates remote work.
        _, restored, runtime = self.restore()
        self.assertEqual(restored.status()["phase"], "prepared")
        self.assertIsNone(restored.status()["session_id"])
        self.assertEqual(self.ledger.status()["session_id"], "as_test")
        # Never issue a second authorized create from the stale bundle. Restore
        # does not prove global exactly-once execution across lost snapshots.
        with self.assertRaisesRegex(ServiceError, "COST_ACK_REQUIRED"):
            runtime.submit(live=False, acknowledge_cost_risk=False)
        self.assertEqual(self.provider.create_count, 1)

    def test_post_effect_snapshot_preserves_unknown_sqlite_reservation_and_session(self):
        manifest = make_manifest(ROOT, self.config, self.config["schedules"][0], fixture=True)
        self.store.enqueue("interrupted-job", manifest)
        self.store.next_job("interrupted-job")
        self.store.reserve("interrupted-job", "fixture-read", {"purpose": "runner-loss-drill"},
                           source_requests=1, micros=7)
        self.store.fail_effect("interrupted-job", "fixture-read", "FIXTURE_UNKNOWN")
        self.submit()
        before = self.store.inspect("interrupted-job")
        usage = self.store.status()["usage"]
        self.snapshot()
        store, ledger, runtime = self.restore()
        self.assertEqual(store.inspect("interrupted-job"), before)
        self.assertEqual(store.status()["usage"], usage)
        self.assertEqual(ledger.status()["phase"], "running")
        with self.assertRaisesRegex(ServiceError, "CREATE_ALREADY_ATTEMPTED"):
            runtime.submit(live=True, acknowledge_cost_risk=True)
        self.assertEqual(runtime.observe()["phase"], "running")
        self.assertEqual(store.inspect("interrupted-job")["effects"][0]["state"], "unknown")
        self.assertEqual(self.provider.create_count, 1)
        self.assert_no_outbox(store)


if __name__ == "__main__":
    unittest.main()
