"""Offline recovery drills, not availability or disaster-recovery benchmarks."""

from copy import deepcopy
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from researcher.scripts.artifact_store import _atomic_write_bytes
from researcher.scripts.schema_contract import canonicalize, sha256_bytes
from researcher.service import demo, recovery_bundle as recovery
from researcher.service.agents_runtime import ManagedResearch, SessionLedger, prepare_packet
from researcher.service.contracts import ServiceError, digest
from researcher.service.retrieval_handoff import verified_bundle
from researcher.service.store import Store
from researcher.service.tests.test_agents_runtime import FakeAgents
from researcher.service.tests.test_daily_retrieval import DAY, ROOT
from researcher.service.workflow import Workflow, make_manifest


class RecoveryBundleTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name).resolve()
        self.config = demo.demo_config()
        self.store = Store(self.directory / "state", self.config, initialize=True)
        self.bundle = self.directory / "bundle"
        self.destination = self.directory / "restored"
        self.network = patch("socket.socket.connect", side_effect=AssertionError("network forbidden"))
        self.network.start()
        self.addCleanup(self.network.stop)

    def snapshot(self, **kwargs):
        self.summary = recovery.snapshot(self.store, self.bundle, root=ROOT, **kwargs)
        return self.summary

    def restore(self, **kwargs):
        return recovery.restore(self.bundle, self.destination, root=ROOT, config=self.config,
                                expected_digest=self.summary["manifest_digest"], **kwargs)

    def job(self):
        manifest = make_manifest(ROOT, self.config, self.config["schedules"][0], fixture=True)
        self.store.enqueue("offline", manifest)
        self.store.next_job()
        return manifest

    def rewrite_manifest(self, change):
        path = self.bundle / "manifest.json"
        value = json.loads(path.read_bytes())
        change(value)
        _atomic_write_bytes(path, canonicalize(value))
        self.summary["manifest_digest"] = digest(value)

    def captured(self):
        # Reuse the actual capture-based fixture, not invented replay receipts.
        from researcher.service.tests.test_retrieval_handoff import RetrievalHandoffTests
        fixture = RetrievalHandoffTests("test_capture_to_managed_packet_replays_without_network_or_budget_changes")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.store, self.config = fixture.store, fixture.config
        return fixture

    def test_empty_snapshot_restores_paused_and_source_is_unchanged(self):
        before = self.store.status()
        summary = self.snapshot()
        receipt = self.restore()
        restored = Store(self.destination / "state", self.config)
        self.assertTrue(restored.status()["paused"])
        self.assertEqual(before, self.store.status())
        self.assertEqual(summary["file_count"], 1)
        self.assertFalse(receipt["activation"])
        self.assertFalse(receipt["reconciliation_performed"])
        self.assertNotEqual(receipt["source_database_sha256"], receipt["restored_database_sha256"])
        with self.assertRaisesRegex(ServiceError, "PAUSED"):
            restored.enqueue("never", {})

    def test_non_authoritative_traces_are_not_in_execution_recovery(self):
        from researcher.service.tracing import Tracer
        tracer = Tracer.at(self.store.directory)
        with tracer.span("workflow.execute"):
            pass
        before = tracer.journal.status()
        self.snapshot()
        self.restore()
        self.assertFalse((self.destination / "state/telemetry").exists())
        self.assertEqual(tracer.journal.status(), before)

    def test_trace_directory_alias_does_not_bypass_recovery_path_checks(self):
        target = self.directory / "alias-target"
        target.mkdir(mode=0o700)
        (self.store.directory / "telemetry").symlink_to(target, target_is_directory=True)
        with self.assertRaises(ServiceError):
            self.snapshot()

    def test_real_captures_replay_read_only_after_restore_and_no_duplicate_effects(self):
        fixture = self.captured()
        before = self.store.inspect("daily")
        self.snapshot()
        self.restore()
        restored = Store(self.destination / "state", self.config)
        observed = verified_bundle(restored, "daily", now=DAY + 3600, fixture=True)
        self.assertGreater(observed["retrieval_context"]["primary_cards"], 0)
        self.assertEqual(before, restored.inspect("daily"))
        files_before = {path: (path.read_bytes(), path.stat().st_mtime_ns)
                        for path in (self.destination / "state/evidence").rglob("*") if path.is_file()}
        verified_bundle(restored, "daily", now=DAY + 3600, fixture=True)
        self.assertEqual(files_before, {path: (path.read_bytes(), path.stat().st_mtime_ns)
                         for path in files_before})
        restored.pause(False)  # Explicit drill-only operator action, never restore behavior.
        def forbidden(*a, **k):
            self.fail("completed retrieval repeated")
        self.assertEqual(Workflow(restored, ROOT, retrieval_source=forbidden,
                                 retrieval_verify=forbidden).drain(), [])
        self.assertEqual(before["effects"], restored.inspect("daily")["effects"])
        self.assertEqual(len(fixture.feed_transport.requests), 1)
        self.assertEqual(fixture.article_transport.calls, 1)

    def test_candidate_cas_and_freeze_receipt_survive_for_materialization(self):
        # This fixture really creates a CAS, freeze receipt and data-only skill delta.
        demo.run_demo(ROOT, self.directory / "candidate-state")
        self.store = Store(self.directory / "candidate-state", self.config)
        with sqlite3.connect(self.store.path) as db:
            frozen = json.loads(db.execute("SELECT output FROM steps WHERE name='freeze'").fetchone()[0])
        path = frozen["receipt"]["entries"][0]["path"]
        original = Workflow(self.store, ROOT).frozen_text(frozen, path)
        self.snapshot()
        self.restore()
        restored = Store(self.destination / "state", self.config)
        self.assertEqual(Workflow(restored, ROOT).frozen_text(frozen, path), original)
        self.assertIn("Fixture evidence-transfer check", original)

    def test_started_and_unknown_effects_keep_reservations_and_never_repeat(self):
        self.job()
        self.store.reserve("offline", "model-researcher", {"request": 1}, model_calls=1, micros=27)
        self.store.reserve("offline", "source-arxiv", {"request": 2}, source_requests=1, micros=3)
        self.store.fail_effect("offline", "source-arxiv", "NETWORK_UNCERTAIN")
        before = self.store.inspect("offline")
        self.snapshot()
        self.restore()
        restored = Store(self.destination / "state", self.config)
        self.assertEqual(before, restored.inspect("offline"))
        self.assertEqual(restored.status()["usage"], self.store.status()["usage"])
        restored.pause(False)
        def forbidden(*a, **k):
            self.fail("unknown effect repeated")
        self.assertEqual(Workflow(restored, ROOT, model=forbidden, source=forbidden).drain(), [])
        effects = restored.inspect("offline")["effects"]
        self.assertEqual([row["state"] for row in effects], ["unknown", "unknown"])
        self.assertEqual(restored.status()["usage"][0]["reserved_microusd"], 30)

    def test_managed_submission_intent_and_completed_results_are_preserved(self):
        packet = prepare_packet(ROOT, model="fixture-model-v1", query="context transfer",
                                skills=["context-fundamentals"], evidence=demo.source("", "", None)["evidence"])
        ledger = SessionLedger.prepare(self.directory / "managed", packet)
        _, state = ledger.load()
        state["phase"] = "submitting"
        ledger.save(state)
        self.snapshot(sessions={"research": ledger})
        self.restore()
        restored = SessionLedger(self.destination / "sessions/research")
        self.assertEqual(ledger.load(), restored.load())
        client = FakeAgents(packet)
        with self.assertRaisesRegex(ServiceError, "ALREADY_ATTEMPTED"):
            ManagedResearch(restored, client).submit(live=True, acknowledge_cost_risk=True)
        self.assertEqual(client.create_count, 0)

    def test_managed_completed_result_is_included(self):
        packet = prepare_packet(ROOT, model="fixture-model-v1", query="context transfer",
                                skills=["context-fundamentals"], evidence=demo.source("", "", None)["evidence"])
        ledger = SessionLedger.prepare(self.directory / "managed", packet)
        client = FakeAgents(packet)
        runtime = ManagedResearch(ledger, client, clock=lambda: 1000)
        runtime.submit(live=True, acknowledge_cost_risk=True)
        client.finish()
        runtime.observe()
        self.snapshot(sessions={"research": ledger})
        self.restore()
        restored = SessionLedger(self.destination / "sessions/research")
        self.assertEqual(restored.load(), ledger.load())
        self.assertEqual((restored.directory / "result.json").read_bytes(), (ledger.directory / "result.json").read_bytes())

    def test_missing_capture_is_rejected_before_bundle_commits(self):
        self.captured()
        capture = next((self.store.directory / "evidence/bodies").iterdir())
        capture.unlink()
        with self.assertRaises(ServiceError):
            self.snapshot()
        self.assertFalse((self.bundle / "manifest.json").exists())

    def test_handoff_session_is_bound_to_backed_up_capture_job(self):
        fixture = self.captured()
        ledger = fixture.prepare()
        self.snapshot(sessions={"bound": ledger})
        self.restore()
        self.assertEqual(SessionLedger(self.destination / "sessions/bound").load(), ledger.load())
        self.store = Store(self.directory / "unrelated", self.config, initialize=True)
        self.bundle = self.directory / "unrelated-bundle"
        with self.assertRaisesRegex(ServiceError, "SESSION_SOURCE_MISSING"):
            self.snapshot(sessions={"bound": ledger})

    def test_missing_cas_blob_is_rejected(self):
        demo.run_demo(ROOT, self.directory / "candidate-state")
        self.store = Store(self.directory / "candidate-state", self.config)
        next((self.store.directory / "candidate-cas/sha256").glob("*/*")).unlink()
        with self.assertRaisesRegex(ServiceError, "CAS_CONTENT_MISSING"):
            self.snapshot()

    def test_unknown_environment_and_git_files_are_never_copied(self):
        for name in (".env", ".env.local", "api-key.txt", ".git", "other.sqlite3"):
            path = self.store.directory / name
            _atomic_write_bytes(path, b"synthetic-secret-do-not-copy")
            with self.subTest(name=name), self.assertRaisesRegex(ServiceError, "UNEXPECTED_FILE"):
                self.snapshot()
            path.unlink()
            self.assertFalse(self.bundle.exists())

    def test_snapshot_and_restore_destinations_must_be_fresh(self):
        self.snapshot()
        with self.assertRaisesRegex(ServiceError, "DESTINATION_EXISTS"):
            self.snapshot()
        self.restore()
        before = (self.destination / "restore.json").read_bytes()
        with self.assertRaisesRegex(ServiceError, "DESTINATION_EXISTS"):
            self.restore()
        self.assertEqual(before, (self.destination / "restore.json").read_bytes())

    def test_symlinks_hardlinks_and_permissions_fail(self):
        self.snapshot()
        record = json.loads((self.bundle / "manifest.json").read_bytes())
        blob = self.bundle / "blobs" / record["files"][0]["sha256"][7:]
        blob.chmod(0o644)
        with self.assertRaises(ServiceError):
            self.restore()
        blob.chmod(0o600)
        alias = self.directory / "hardlink"
        os.link(blob, alias)
        with self.assertRaises(ServiceError):
            self.restore()
        alias.unlink()
        moved = self.directory / "payload"
        blob.rename(moved)
        blob.symlink_to(moved)
        with self.assertRaises(ServiceError):
            self.restore()
        self.assertFalse(self.destination.exists())

    def test_symlink_ancestor_and_destination_are_rejected(self):
        alias = self.directory / "alias"
        alias.symlink_to(self.store.directory, target_is_directory=True)
        with self.assertRaises(ServiceError):
            recovery.snapshot(Store(alias, self.config), self.bundle, root=ROOT)
        self.snapshot()
        self.destination.symlink_to(self.store.directory, target_is_directory=True)
        with self.assertRaises(ServiceError):
            self.restore()

    def test_unsafe_ownership_is_rejected(self):
        original = Path.lstat
        def changed(path):
            result = original(path)
            if path == self.store.directory:
                values = list(result)
                values[4] = os.getuid() + 2000
                return os.stat_result(values)
            return result
        with patch.object(Path, "lstat", changed), self.assertRaisesRegex(ServiceError, "PATH_UNSAFE"):
            self.snapshot()

    def test_digest_pinning_tampering_and_traversal_rejected(self):
        self.snapshot()
        manifest = self.bundle / "manifest.json"
        original = manifest.read_bytes()
        _atomic_write_bytes(manifest, original.replace(b'"activation":false', b'"activation":true'))
        with self.assertRaisesRegex(ServiceError, "MANIFEST_MISMATCH"):
            self.restore()
        _atomic_write_bytes(manifest, original)
        self.rewrite_manifest(lambda value: value["files"][0].update(path="state/../../escape"))
        with self.assertRaises(ServiceError):
            self.restore()
        self.assertFalse(self.destination.exists())

    def test_changed_blob_and_missing_blob_rejected(self):
        self.snapshot()
        blob = next((self.bundle / "blobs").iterdir())
        body = blob.read_bytes()
        _atomic_write_bytes(blob, body[:-1] + bytes([body[-1] ^ 1]))
        with self.assertRaisesRegex(ServiceError, "CONTENT_HASH_MISMATCH"):
            self.restore()
        blob.unlink()
        with self.assertRaises(ServiceError):
            self.restore()
        self.assertFalse(self.destination.exists())

    def test_source_and_config_drift_are_rejected(self):
        self.snapshot()
        with patch.object(recovery, "_source", return_value={}):
            with self.assertRaisesRegex(ServiceError, "SOURCE_CONFIG_MISMATCH"):
                self.restore()
        self.config = deepcopy(self.config)
        self.config["limits"]["daily_model_calls"] += 1
        with self.assertRaisesRegex(ServiceError, "SOURCE_CONFIG_MISMATCH"):
            self.restore()
        self.assertFalse(self.destination.exists())

    def test_byte_and_file_limits_are_enforced(self):
        with self.assertRaisesRegex(ServiceError, "SIZE_LIMIT"):
            self.snapshot(max_bytes=1)
        self.bundle = self.directory / "complete"
        self.snapshot()
        with self.assertRaisesRegex(ServiceError, "SIZE_LIMIT"):
            self.restore(max_bytes=1)
        for limit in (0, True, recovery.MAX_FILES + 1):
            with self.subTest(limit=limit), self.assertRaisesRegex(ServiceError, "LIMIT_INVALID"):
                self.restore(max_files=limit)

    def test_real_file_count_bound_includes_capture_artifacts(self):
        self.captured()
        with self.assertRaisesRegex(ServiceError, "FILE_LIMIT"):
            self.snapshot(max_files=1)

    def test_fifo_is_rejected_without_opening_it(self):
        self.captured()
        body = next((self.store.directory / "evidence/bodies").iterdir())
        body.unlink()
        os.mkfifo(body, 0o600)
        with self.assertRaisesRegex(ServiceError, "PATH_UNSAFE"):
            self.snapshot()

    def test_worker_and_session_locks_prevent_snapshots(self):
        with self.store.worker_lock(), self.assertRaisesRegex(ServiceError, "WORKER_ALREADY_RUNNING"):
            self.snapshot()
        packet = prepare_packet(ROOT, model="fixture-model-v1", query="context transfer",
                                skills=["context-fundamentals"], evidence=demo.source("", "", None)["evidence"])
        ledger = SessionLedger.prepare(self.directory / "managed", packet)
        with ledger.lock(), self.assertRaisesRegex(ServiceError, "MANAGED_WORKER_ALREADY_RUNNING"):
            self.snapshot(sessions={"research": ledger})

    def test_database_checkpoint_corruption_rejected(self):
        self.job()
        self.store.checkpoint("offline", "pure", {"x": 1}, {"answer": 2})
        with sqlite3.connect(self.store.path) as db:
            db.execute("UPDATE steps SET output='{}'")
        with self.assertRaisesRegex(ServiceError, "CHECKPOINT_INVALID"):
            self.snapshot()
        self.assertFalse((self.bundle / "manifest.json").exists())

    def test_untrusted_extra_sqlite_trigger_is_not_executed(self):
        self.snapshot()
        record = json.loads((self.bundle / "manifest.json").read_bytes())
        blob = self.bundle / "blobs" / record["files"][0]["sha256"][7:]
        with sqlite3.connect(blob) as db:
            db.execute("CREATE TRIGGER surprise AFTER UPDATE ON meta BEGIN DELETE FROM effects; END")
        body = blob.read_bytes()
        hashed = sha256_bytes(body)
        blob.rename(blob.parent / hashed[7:])
        def update(value):
            value["files"][0].update(sha256=hashed, size_bytes=len(body))
            value["total_bytes"] = len(body)
        self.rewrite_manifest(update)
        with self.assertRaisesRegex(ServiceError, "DATABASE_INVALID"):
            self.restore()
        self.assertFalse(self.destination.exists())

    def test_campaign_authority_preserves_completed_unknown_and_cumulative_budget(self):
        from researcher.service.openai_campaign import Campaign, PRICING, initialize
        from researcher.service.providers import ModelResult, ProviderError
        directory = self.directory / "authority"
        initialize(directory, cap_microusd=1000000, prior_spend_microusd=1200)
        calls = []
        def model(request, *, credential):
            calls.append(request.prompt)
            if request.prompt == "outage":
                raise ProviderError("MODEL_WALL_TIMEOUT", "synthetic unknown")
            return ModelResult('{"answer":true}', 12, 10, PRICING["model"], "fixture-response", "default")
        runner = Campaign(directory, credential="synthetic-never-sent", model_call=model,
                          progress=lambda event: None, now=lambda: 1790632800)
        first = runner.call("recovery", "one", instructions="schema", prompt="observed", max_output_tokens=256)
        with self.assertRaisesRegex(ServiceError, "MODEL_WALL_TIMEOUT"):
            runner.call("recovery", "two", instructions="schema", prompt="outage", max_output_tokens=256)
        self.store, self.config = runner.store, runner.store.config
        before = runner.status()
        self.snapshot()
        self.restore()
        restored = Campaign(self.destination / "state", model_call=lambda *a, **k: self.fail("duplicate model effect"),
                            progress=lambda event: None, now=lambda: 1790632800)
        self.assertTrue(restored.store.status()["paused"])
        self.assertEqual(restored.status(), before)
        # Completed receipt replay remains safe even while paused, without a key.
        self.assertEqual(first, restored.call("recovery", "one", instructions="schema", prompt="observed", max_output_tokens=256))
        with self.assertRaisesRegex(ServiceError, "EFFECT_RECONCILIATION_REQUIRED"):
            restored.call("recovery", "two", instructions="schema", prompt="outage", max_output_tokens=256)
        self.assertEqual(calls, ["observed", "outage"])
        self.assertEqual(restored.status(), before)
        self.assertEqual((directory / "authority.json").read_bytes(),
                         (self.destination / "state/authority.json").read_bytes())

    def test_campaign_namespace_and_authority_identity_are_closed(self):
        from researcher.service.openai_campaign import initialize
        self.store = initialize(self.directory / "authority", cap_microusd=1000000, prior_spend_microusd=0)
        self.config = self.store.config
        path = self.store.directory / "evidence"
        path.mkdir(mode=0o700)
        with self.assertRaisesRegex(ServiceError, "UNEXPECTED_FILE"):
            self.snapshot()
        path.rmdir()
        value = deepcopy(self.config)
        value["prior_spend_microusd"] = 1
        _atomic_write_bytes(self.store.directory / "authority.json", canonicalize(value))
        with self.assertRaisesRegex(ServiceError, "CONFIG_MISMATCH"):
            self.snapshot()


if __name__ == "__main__":
    unittest.main()
