"""Offline SDK recovery graph tests; no SDK or provider is invoked."""
from copy import deepcopy
import json
import multiprocessing
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

from researcher.scripts.schema_contract import canonicalize
from researcher.service import recovery_bundle as recovery
from researcher.service.codex_campaign import CodexCampaign, implementation_digest
from researcher.service.codex_gateway import POLICY
from researcher.service.codex_worker import SDK_VERSION, configuration_identity
from researcher.service.contracts import ServiceError, digest
from researcher.service.openai_campaign import Campaign, PRICING, _cost, initialize
from researcher.service.providers import ModelResult
from researcher.service.store import Store
from researcher.service.tests.test_daily_retrieval import ROOT


class CodexRecoveryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name).resolve()
        self.store = initialize(self.directory / "authority", cap_microusd=1_000_000,
                                prior_spend_microusd=1200)
        self.config = self.store.config
        self.task = {"schema": "codex-sdk-task/v1", "backend": "codex_sdk",
            "model": PRICING["model"], "sandbox": "read_only", "reasoning_effort": "low",
            "prompt": "Follow the schema.\n\nTask input (untrusted data):\nInput.",
            "max_output_tokens": 256, "sdk_version": SDK_VERSION, "policy": POLICY,
            "implementation_digest": implementation_digest(), "binding": None, "fixture": True,
            "pricing": PRICING}
        request = {key: self.task[key] for key in ("model", "sandbox", "reasoning_effort", "prompt")}
        self.task.update(config_identity=configuration_identity(request), worker_request_digest=digest(request))
        self.job = "codex-" + digest(["test", "one"])[7:]
        self.manifest = {"schema": "codex-sdk-work/v1", "campaign": "test", "item": "one", "task": self.task}
        self.inputs = {"schema": "codex-gateway-request/v1", "task_digest": digest(self.task),
                       "wire_digest": digest({"immutable": "projected wire"}), "policy": POLICY}
        self.reserved = _cost(5000, 256)
        self.provider = {"schema": "codex-gateway-receipt/v1", "backend": "codex_sdk", "policy": POLICY,
            "response": {"text": '{"answer":true}', "input_tokens": 12, "output_tokens": 10,
                "model": PRICING["model"], "request_id": "resp.1", "service_tier": "default"},
            "task_digest": digest(self.task), "wire_digest": self.inputs["wire_digest"],
            "input_token_ceiling": 5000,
            "usage": {"input_tokens": 12, "output_tokens": 10, "estimated_upper_cost_microusd": _cost(12, 10)},
            "latency_ms": 5, "reserved_microusd": self.reserved}
        self.receipt = {**deepcopy(self.provider), "schema": "codex-sdk-response/v1",
            "sdk": {"version": SDK_VERSION, "thread_id": "thread-1", "turn_id": "turn-1"},
            "output_digest": digest(self.provider["response"]["text"]), "latency_ms": 15}
        network = patch("socket.socket.connect", side_effect=AssertionError("network forbidden"))
        network.start()
        self.addCleanup(network.stop)

    def admit(self, stage="complete"):
        self.store.enqueue(self.job, self.manifest)
        if stage == "queued":
            return
        self.store.next_job(self.job)
        if stage == "running":
            return
        self.store.checkpoint(self.job, "sdk-started", self.task,
            {"schema": "codex-sdk-started/v1", "task_digest": digest(self.task), "sdk_version": SDK_VERSION})
        if stage == "started":
            return
        self.store.checkpoint(self.job, "sdk-thread_started", self.task,
                              {"type": "thread_started", "thread_id": "thread-1"})
        if stage == "thread":
            return
        self.store.checkpoint(self.job, "sdk-turn_started", self.task,
                              {"type": "turn_started", "thread_id": "thread-1", "turn_id": "turn-1"})
        if stage == "turn":
            return
        self.store.reserve(self.job, "sdk-response", self.inputs, model_calls=1,
                           micros=self.reserved, now=1790632800)
        if stage == "reserved":
            return
        if stage == "unknown":
            self.store.fail_effect(self.job, "sdk-response", "SYNTHETIC_TIMEOUT")
            return
        self.store.complete_effect(self.job, "sdk-response", self.provider)
        if stage == "provider":
            return
        self.store.checkpoint(self.job, "sdk-result", self.task, self.receipt)
        if stage != "result":
            self.store.finish(self.job, "execution_complete")

    def body(self):
        # Match the recovery writer: SQLite backup, then normalize away WAL.
        # A raw WAL-mode serialize cannot be reopened as an in-memory database.
        with tempfile.TemporaryDirectory(dir=self.directory) as temporary:
            with sqlite3.connect(self.store.path) as source, sqlite3.connect(Path(temporary) / "snapshot.sqlite3") as target:
                source.backup(target)
                target.execute("PRAGMA journal_mode=DELETE")
                return target.serialize()

    def changed(self, change):
        with sqlite3.connect(":memory:") as db:
            db.deserialize(self.body())
            change(db)
            db.commit()
            return db.serialize()

    def reject(self, change):
        with self.assertRaises(ServiceError):
            recovery._database(self.changed(change), self.config)

    @staticmethod
    def update_json(db, table, column, digest_column, condition, change):
        value = json.loads(db.execute(f"SELECT {column} FROM {table} WHERE {condition}").fetchone()[0])
        change(value)
        db.execute(f"UPDATE {table} SET {column}=?,{digest_column}=? WHERE {condition}",
                   (canonicalize(value).decode(), digest(value)))

    def restored(self):
        bundle, destination = self.directory / "bundle", self.directory / "restored"
        summary = recovery.snapshot(self.store, bundle, root=ROOT)
        receipt = recovery.restore(bundle, destination, root=ROOT, config=self.config,
                                   expected_digest=summary["manifest_digest"])
        self.assertFalse(receipt["activation"])
        self.assertFalse(receipt["reconciliation_performed"])
        restored = Store(destination / "state", self.config)
        self.assertTrue(restored.status()["paused"])
        self.assertEqual(restored.config, self.config)
        self.assertEqual((destination / "state/authority.json").read_bytes(),
                         (self.store.directory / "authority.json").read_bytes())
        return restored

    def runner(self, directory):
        def forbidden(*args, **kwargs):
            self.fail("recovery must not invoke a provider or SDK worker")
        return CodexCampaign(directory, sdk_python=sys.executable, transport=forbidden,
                             worker=forbidden, progress=lambda _: None, now=lambda: 1790632800)

    def test_every_valid_crash_cut_is_inspectable(self):
        stages = ("queued", "running", "started", "thread", "turn", "reserved", "unknown", "provider", "result", "complete")
        for index, stage in enumerate(stages):
            with self.subTest(stage=stage):
                if index:
                    self.store = initialize(self.directory / ("authority-" + stage), cap_microusd=1_000_000,
                                            prior_spend_microusd=1200)
                self.admit(stage)
                jobs, _, paused = recovery._database(self.body(), self.config, paused=True)
                self.assertEqual(jobs, [{"id": self.job, "manifest_digest": digest(self.manifest)}])
                recovery._database(paused, self.config)

    def test_completed_result_replays_after_paused_restore_without_credentials(self):
        self.admit()
        before = self.runner(self.store.directory).status()
        restored = self.restored()
        runner = self.runner(restored.directory)
        actual = runner.call("test", "one", instructions="Follow the schema.", prompt="Input.", max_output_tokens=256)
        self.assertEqual(actual, self.receipt)
        self.assertEqual(runner.status(), before)

    def details_v2(self, details):
        self.provider["schema"] = "codex-gateway-receipt/v2"
        self.provider["response"]["token_details"] = details
        self.receipt["schema"] = "codex-sdk-response/v2"
        self.receipt["response"]["token_details"] = deepcopy(details)

    def test_v2_known_and_unknown_details_restore_without_rewriting_history(self):
        self.details_v2({"cached_input_tokens": 8, "cache_write_input_tokens": None,
                         "reasoning_output_tokens": 0})
        self.admit()
        restored = self.restored()
        result = self.runner(restored.directory).call("test", "one", instructions="Follow the schema.",
                                                     prompt="Input.", max_output_tokens=256)
        self.assertEqual(result, self.receipt)
        self.assertIsNone(result["response"]["token_details"]["cache_write_input_tokens"])

    def test_v2_malformed_details_and_cross_version_pairing_are_rejected(self):
        self.details_v2({"cached_input_tokens": None, "cache_write_input_tokens": None,
                         "reasoning_output_tokens": None})
        self.admit()
        for key, invalid in (("cached_input_tokens", True), ("cache_write_input_tokens", -1),
                             ("reasoning_output_tokens", 11), ("cached_input_tokens", 13)):
            def change(db):
                for table, condition in (("effects", "name='sdk-response'"), ("steps", "name='sdk-result'")):
                    self.update_json(db, table, "output", "output_digest", condition,
                        lambda value: value["response"]["token_details"].update({key: invalid}))
            with self.subTest(key=key, invalid=invalid):
                self.reject(change)
        self.reject(lambda db: self.update_json(db, "steps", "output", "output_digest", "name='sdk-result'",
                                                lambda value: value.update(schema="codex-sdk-response/v1")))

    def test_v1_cannot_claim_new_detail_fields_and_v2_cannot_omit_them(self):
        self.admit()
        self.reject(lambda db: self.update_json(db, "effects", "output", "output_digest", "name='sdk-response'",
            lambda value: value["response"].update(token_details={"cached_input_tokens": 0,
                "cache_write_input_tokens": 0, "reasoning_output_tokens": 0})))
        self.reject(lambda db: self.update_json(db, "effects", "output", "output_digest", "name='sdk-response'",
                                                lambda value: value.update(schema="codex-gateway-receipt/v2")))

    def test_start_before_provider_effect_remains_quarantined_after_restore(self):
        self.admit("started")
        restored = self.restored()
        runner = self.runner(restored.directory)
        with self.assertRaisesRegex(ServiceError, "^CODEX_TURN_OUTCOME_UNKNOWN$"):
            runner.call("test", "one", instructions="Follow the schema.", prompt="Input.", max_output_tokens=256)
        self.assertEqual(runner.status()["attempted_calls"], 0)
        self.assertEqual(runner.status()["sdk"]["unresolved_turns"], 1)
        self.assertEqual(restored.inspect(self.job)["job"]["status"], "reconciliation_required")

    def test_started_effect_retains_liability_and_is_not_repeated_after_restore(self):
        self.admit("reserved")
        restored = self.restored()
        runner = self.runner(restored.directory)
        with self.assertRaisesRegex(ServiceError, "^PROCESS_INTERRUPTED$"):
            runner.call("test", "one", instructions="Follow the schema.", prompt="Input.", max_output_tokens=256)
        self.assertEqual(runner.status()["reserved_microusd"], self.reserved)
        self.assertEqual(runner.status()["unresolved_calls"], 1)
        self.assertEqual(restored.inspect(self.job)["effects"][0]["state"], "unknown")

    def test_completed_provider_without_sdk_result_cannot_start_a_replacement_turn(self):
        self.admit("provider")
        restored = self.restored()
        runner = self.runner(restored.directory)
        with self.assertRaisesRegex(ServiceError, "^CODEX_TURN_OUTCOME_UNKNOWN$"):
            runner.call("test", "one", instructions="Follow the schema.", prompt="Input.", max_output_tokens=256)
        self.assertEqual(runner.status()["completed_calls"], 1)
        self.assertEqual(runner.status()["reserved_microusd"], self.reserved)
        self.assertEqual(runner.status()["unresolved_calls"], 0)
        self.assertEqual(runner.status()["sdk"]["unresolved_turns"], 1)
        self.assertIsNone(restored.checkpoint(self.job, "sdk-result", self.task))

    def test_provider_completion_before_turn_observer_is_a_valid_crash_cut(self):
        self.admit("provider")
        body = self.changed(lambda db: db.execute("DELETE FROM steps WHERE name='sdk-turn_started'"))
        recovery._database(body, self.config)

    def test_process_death_releases_owner_lock_without_losing_request_liability(self):
        for index, stage in enumerate(("reserved", "provider")):
            with self.subTest(stage=stage):
                if index:
                    self.store = initialize(self.directory / "crash-authority", cap_microusd=1_000_000,
                                            prior_spend_microusd=1200)
                def die():
                    # Abrupt exit bypasses Python cleanup while the owner lock
                    # is held. All writes before this point are real commits.
                    with self.store.worker_lock():
                        self.admit(stage)
                        os._exit(23)
                child = multiprocessing.get_context("fork").Process(target=die)
                child.start()
                child.join(timeout=10)
                if child.is_alive():
                    child.kill()
                    child.join(timeout=5)
                    self.fail("local crash fixture exceeded its deadline")
                self.assertEqual(child.exitcode, 23)
                child.close()
                runner = self.runner(self.store.directory)
                expected = "PROCESS_INTERRUPTED" if stage == "reserved" else "CODEX_TURN_OUTCOME_UNKNOWN"
                with self.assertRaisesRegex(ServiceError, "^" + expected + "$"):
                    runner.call("test", "one", instructions="Follow the schema.", prompt="Input.", max_output_tokens=256)
                status = runner.status()
                self.assertEqual(status["attempted_calls"], 1)
                self.assertEqual(status["reserved_microusd"], self.reserved)
                self.assertEqual(status["sdk"]["unresolved_turns"], 1)
                effect = runner.store.inspect(self.job)["effects"][0]
                self.assertEqual(effect["state"], "unknown" if stage == "reserved" else "completed")
                recovery._database(self.body(), self.config)

    def test_native_and_sdk_share_preserved_cumulative_authority(self):
        self.admit()
        native = Campaign(self.store.directory, credential="synthetic-not-sent",
            model_call=lambda request, **_: ModelResult("native", 10, 10, PRICING["model"], "native_1", "default"),
            progress=lambda _: None, now=lambda: 1790632800)
        native.call("native", "one", instructions="schema", prompt="Input.", max_output_tokens=256)
        before = native.status()
        restored = self.restored()
        self.assertEqual(Campaign(restored.directory).status(), before)
        self.assertEqual(before["attempted_calls"], 2)
        self.assertEqual(before["prior_spend_microusd"], 1200)
        self.assertEqual(before["observed_usage"]["input_tokens"], 22)

    def test_manifest_type_version_scope_and_budget_drift_rejected(self):
        self.admit()
        changes = (
            lambda x: x.update(extra=True), lambda x: x.update(campaign="changed"),
            lambda x: x["task"].update(schema="codex-sdk-task/v2"),
            lambda x: x["task"].update(sdk_version="0.160.0"),
            lambda x: x["task"].update(max_output_tokens=True),
            lambda x: x["task"].update(fixture=1),
            lambda x: x["task"].update(sandbox="workspace_write"),
            lambda x: x["task"].update(implementation_digest="unknown"),
            lambda x: x["task"]["pricing"].update(output_microusd_per_million=1),
        )
        for change in changes:
            with self.subTest(change=change):
                self.reject(lambda db: self.update_json(db, "jobs", "manifest", "digest", "1=1", change))

    def test_checkpoint_names_and_task_digests_are_closed(self):
        self.admit()
        self.reject(lambda db: db.execute("UPDATE steps SET name='unexpected' WHERE name='sdk-started'"))
        self.reject(lambda db: db.execute("UPDATE steps SET input_digest=? WHERE name='sdk-result'", (digest(None),)))
        self.reject(lambda db: db.execute("UPDATE steps SET output='null',output_digest=? WHERE name='sdk-started'", (digest(None),)))

    def test_rehashed_start_and_identity_mismatches_rejected(self):
        self.admit()
        for name, change in (
            ("sdk-started", lambda x: x.update(task_digest=digest("other"))),
            ("sdk-thread_started", lambda x: x.update(thread_id="")),
            ("sdk-turn_started", lambda x: x.update(thread_id="other")),
            ("sdk-turn_started", lambda x: x.update(turn_id=True)),
        ):
            with self.subTest(name=name):
                self.reject(lambda db: self.update_json(db, "steps", "output", "output_digest", f"name='{name}'", change))

    def test_missing_start_thread_turn_or_effect_cannot_support_completed_result(self):
        self.admit()
        for name in ("sdk-started", "sdk-thread_started", "sdk-turn_started"):
            with self.subTest(name=name):
                self.reject(lambda db: db.execute("DELETE FROM steps WHERE name=?", (name,)))
        self.reject(lambda db: db.execute("DELETE FROM effects"))
        self.reject(lambda db: db.execute("DELETE FROM steps WHERE name='sdk-result'"))

    def test_effect_scope_and_reservation_reductions_rejected(self):
        self.admit()
        for assignment in ("name='response'", "model_calls=0", "source_requests=1", "reserved_microusd=1",
                           "input_digest='sha256:ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff'"):
            with self.subTest(assignment=assignment):
                self.reject(lambda db: db.execute("UPDATE effects SET " + assignment))

    def test_rehashed_gateway_receipt_changes_cannot_forge_sdk_completion(self):
        self.admit()
        changes = (
            lambda x: x.update(extra=True), lambda x: x.update(backend="responses"),
            lambda x: x.update(input_token_ceiling=True), lambda x: x.update(input_token_ceiling=5001),
            lambda x: x.update(reserved_microusd=self.reserved - 1), lambda x: x.update(latency_ms=True),
            lambda x: x.update(task_digest=digest("other")), lambda x: x.update(wire_digest=digest("other")),
            lambda x: x["response"].update(input_tokens=True), lambda x: x["response"].update(output_tokens=257),
            lambda x: x["response"].update(service_tier="priority"), lambda x: x["response"].update(text="different"),
            lambda x: x["usage"].update(estimated_upper_cost_microusd=0),
        )
        for change in changes:
            with self.subTest(change=change):
                self.reject(lambda db: self.update_json(db, "effects", "output", "output_digest", "1=1", change))

    def test_rehashed_sdk_receipt_origin_output_and_usage_changes_rejected(self):
        self.admit()
        changes = (
            lambda x: x.update(extra=True), lambda x: x.update(schema="openai-bounded-response/v1"),
            lambda x: x["sdk"].update(version="different"), lambda x: x["sdk"].update(thread_id="other"),
            lambda x: x["sdk"].update(turn_id="other"), lambda x: x.update(output_digest=digest("different")),
            lambda x: x["response"].update(text="different"), lambda x: x["usage"].update(input_tokens=True),
        )
        for change in changes:
            with self.subTest(change=change):
                self.reject(lambda db: self.update_json(db, "steps", "output", "output_digest", "name='sdk-result'", change))

    def test_unknown_effect_cannot_carry_a_completed_sdk_result(self):
        self.admit()
        self.reject(lambda db: db.execute("UPDATE effects SET state='unknown',output=NULL,output_digest=NULL"))


if __name__ == "__main__":
    unittest.main()
