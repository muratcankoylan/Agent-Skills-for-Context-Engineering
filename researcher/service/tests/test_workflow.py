from __future__ import annotations

import copy
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from researcher.service import demo
from researcher.service.contracts import ServiceError, load_config, parse_output
from researcher.service.providers import ModelResult, ProviderError
from researcher.service.store import Store
from researcher.service.workflow import Workflow, admit_due, apply_edit, make_manifest

ROOT = Path(__file__).resolve().parents[3]


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name).resolve() / "state"
        self.config = demo.demo_config()
        self.store = Store(self.directory, self.config, initialize=True)

    def start(self, name="job"):
        self.store.enqueue(name, {"id": name})
        self.assertEqual(self.store.next_job()["id"], name)

    def test_explicit_initialization_and_private_paths(self):
        with self.assertRaises(ServiceError):
            Store(self.directory / "missing", self.config)
        alias = self.directory.parent / "alias"
        alias.symlink_to(self.directory, target_is_directory=True)
        with self.assertRaises(ServiceError):
            Store(alias, self.config)
        self.assertEqual(self.store.path.stat().st_mode & 0o777, 0o600)

    def test_config_change_does_not_reset_budget(self):
        changed = copy.deepcopy(self.config)
        changed["limits"]["daily_model_calls"] += 1
        with self.assertRaisesRegex(ServiceError, "CONFIG_CHANGED"):
            Store(self.directory, changed, initialize=True)

    def test_job_replay_and_collision(self):
        self.assertTrue(self.store.enqueue("job", {"x": 1}))
        self.assertFalse(self.store.enqueue("job", {"x": 1}))
        with self.assertRaisesRegex(ServiceError, "COLLISION"):
            self.store.enqueue("job", {"x": 2})

    def test_completed_effect_is_replayed_without_charge(self):
        self.start()
        self.assertIsNone(self.store.reserve("job", "model", {"request": 1}, model_calls=1, micros=20))
        self.store.complete_effect("job", "model", {"value": 1})
        self.assertEqual(self.store.reserve("job", "model", {"request": 1}, model_calls=1, micros=20), {"value": 1})
        self.assertEqual(self.store.status()["usage"][0]["model_calls"], 1)
        with self.assertRaisesRegex(ServiceError, "EFFECT_INPUT_CHANGED"):
            self.store.reserve("job", "model", {"request": 2})

    def test_restart_quarantines_unknown_effect_and_never_retries(self):
        self.start()
        self.store.reserve("job", "model", {"request": 1}, model_calls=1, micros=20)
        restarted = Store(self.directory, self.config)
        with restarted.worker_lock():
            restarted.recover()
        self.assertIsNone(restarted.next_job())
        self.assertEqual(restarted.status()["jobs"][0]["status"], "reconciliation_required")
        with self.assertRaisesRegex(ServiceError, "RECONCILIATION"):
            restarted.reserve("job", "model", {"request": 1})
        self.assertEqual(restarted.status()["usage"][0]["reserved_microusd"], 20)

    def test_pure_checkpoint_resume_and_corruption(self):
        self.start()
        self.store.checkpoint("job", "pure", {"x": 1}, {"answer": 2})
        with self.store.worker_lock():
            self.store.recover()
        self.assertEqual(self.store.next_job()["id"], "job")
        self.assertEqual(self.store.checkpoint("job", "pure", {"x": 1}), {"answer": 2})
        with sqlite3.connect(self.store.path) as db:
            db.execute("UPDATE steps SET output=?", ('{"answer":3}',))
        with self.assertRaisesRegex(ServiceError, "CORRUPT"):
            self.store.checkpoint("job", "pure", {"x": 1})

    def test_pause_blocks_admission_and_next_effect_not_completed_result(self):
        self.start()
        self.store.reserve("job", "old", {})
        self.store.complete_effect("job", "old", {"ok": True})
        self.store.pause(True)
        with self.assertRaisesRegex(ServiceError, "PAUSED"):
            self.store.enqueue("new", {})
        with self.assertRaisesRegex(ServiceError, "PAUSED"):
            self.store.reserve("job", "new", {})
        self.assertEqual(self.store.reserve("job", "old", {}), {"ok": True})
        self.store.pause(False)
        self.store.reserve("job", "new", {})

    def test_run_and_daily_budget_exhaustion_are_pre_effect(self):
        self.start()
        with self.assertRaisesRegex(ServiceError, "BUDGET_EXHAUSTED"):
            self.store.reserve("job", "cost", {}, model_calls=1, micros=101)
        for index in range(5):
            self.store.reserve("job", f"call-{index}", {}, model_calls=1)
            self.store.complete_effect("job", f"call-{index}", {})
        with self.assertRaisesRegex(ServiceError, "BUDGET_EXHAUSTED"):
            self.store.reserve("job", "extra", {}, model_calls=1)
        self.assertEqual(self.store.status()["usage"][0]["model_calls"], 5)

    def test_clock_rollback_cannot_open_new_daily_bucket(self):
        self.start()
        self.store.reserve("job", "today", {}, model_calls=1, now=2_000_000_000)
        self.store.complete_effect("job", "today", {})
        for clock in (1_999_999_999, 1_999_900_000):
            with self.assertRaisesRegex(ServiceError, "CLOCK_MOVED_BACKWARDS"):
                self.store.reserve("job", "earlier", {}, model_calls=1, now=clock)

    def test_single_worker_lock_is_exclusive(self):
        other = Store(self.directory, self.config)
        with self.store.worker_lock():
            with self.assertRaisesRegex(ServiceError, "WORKER_ALREADY_RUNNING"):
                with other.worker_lock():
                    self.fail("second worker acquired")

    def test_private_backup_preserves_state_not_activation(self):
        self.start()
        target = self.directory.parent / "backup.sqlite3"
        self.store.backup(target)
        with sqlite3.connect(target) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM jobs").fetchone()[0], 1)
        self.assertEqual(target.stat().st_mode & 0o777, 0o600)
        with self.assertRaises(ServiceError):
            self.store.backup(target)

    def test_shared_source_cache_unknown_and_rate_limit(self):
        self.start()
        self.store.reserve("job", "source-arxiv", {}, source_requests=1)
        with patch("researcher.service.store.time.time", return_value=1000):
            self.store.claim_source("key", "arxiv", "job", "source-arxiv")
            with self.assertRaisesRegex(ServiceError, "SOURCE_RATE_LIMIT"):
                self.store.claim_source("key2", "arxiv", "job", "next")
        with self.assertRaisesRegex(ServiceError, "SOURCE_OUTCOME_UNRESOLVED"):
            self.store.cached_source("key")
        self.store.complete_effect("job", "source-arxiv", {"evidence": []})
        self.assertEqual(self.store.cached_source("key"), {"evidence": []})


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name).resolve() / "state"
        self.config = demo.demo_config()
        self.store = Store(self.directory, self.config, initialize=True)
        self.manifest = make_manifest(ROOT, self.config, self.config["schedules"][0], fixture=True)

    def run_work(self, model=demo.model, source=demo.source):
        self.store.enqueue("job", self.manifest)
        runner = Workflow(self.store, ROOT, model=model, source=source, credential=lambda _: "fixture-credential-never-sent")
        return runner.drain()[0]

    def test_entire_data_only_loop_and_no_network(self):
        before = (ROOT / "skills/context-fundamentals/SKILL.md").read_bytes()
        with patch("socket.socket.connect", side_effect=AssertionError("network forbidden")):
            result = self.run_work()
        self.assertNotIn("error", result)
        self.assertTrue(result["result"]["fixture"])
        self.assertFalse(result["result"]["downstream_effectiveness_measured"])
        self.assertEqual({e["candidate_label"] for e in result["result"]["evaluations"]}, {"A", "B"})
        self.assertEqual(self.store.status()["jobs"][0]["status"], "proposal_ready")
        self.assertEqual(before, (ROOT / "skills/context-fundamentals/SKILL.md").read_bytes())
        self.assertEqual(Workflow(self.store, ROOT).drain(), [])

    def test_fixture_cannot_recover_into_real_adapters(self):
        self.store.enqueue("job", self.manifest)
        with patch("socket.socket.connect", side_effect=AssertionError("network forbidden")):
            result = Workflow(self.store, ROOT).drain()[0]
        self.assertEqual(result["error"], "FIXTURE_REQUIRES_OFFLINE_ADAPTERS")

    def test_fabricated_citation_fails_before_critic(self):
        def model(request, **kwargs):
            result = demo.model(request, **kwargs)
            data = json.loads(result.text)
            data["claims"][0]["citations"][0]["quote"] = "fabricated paper finding"
            return ModelResult(json.dumps(data), 1, 1, request.model, "fixture")
        result = self.run_work(model=model)
        self.assertEqual(result["error"], "UNGROUNDED_CITATION")
        self.assertEqual(self.store.status()["usage"][0]["model_calls"], 1)

    def test_abstention_is_terminal_not_success(self):
        def model(request, **kwargs):
            result = demo.model(request, **kwargs)
            data = json.loads(result.text)
            data["abstain"] = True
            return ModelResult(json.dumps(data), 1, 1, request.model, "fixture")
        self.run_work(model=model)
        self.assertEqual(self.store.status()["jobs"][0]["status"], "rejected")

    def test_order_biased_judge_does_not_pass(self):
        def model(request, **kwargs):
            if "Compare alternatives A and B" in request.system:
                return ModelResult('{"preference":"A","critical_regression":false,"reason":"always A"}', 1, 1, request.model, "fixture")
            return demo.model(request, **kwargs)
        result = self.run_work(model=model)
        self.assertFalse(result["result"]["pilot_passed"])
        self.assertEqual(self.store.status()["jobs"][0]["status"], "rejected")

    def test_evaluator_has_no_author_rationale_or_earlier_judgment(self):
        seen = []
        def model(request, **kwargs):
            if "Compare alternatives A and B" in request.system:
                value = json.loads(request.prompt)
                self.assertEqual(set(value), {"task", "evidence", "A", "B"})
                seen.append(value)
            return demo.model(request, **kwargs)
        self.run_work(model=model)
        self.assertEqual(len(seen), 2)
        self.assertEqual(seen[0]["A"], seen[1]["B"])

    def test_unknown_paid_attempt_stops_without_retry(self):
        count = []
        def model(request, **kwargs):
            count.append(1)
            raise ProviderError("TIMEOUT", "safe error")
        self.run_work(model=model)
        self.assertEqual(len(count), 1)
        self.assertEqual(self.store.status()["jobs"][0]["status"], "reconciliation_required")
        self.assertEqual(Workflow(self.store, ROOT).drain(), [])

    def test_invalid_model_json_is_saved_billable_failure(self):
        def model(request, **kwargs):
            return ModelResult("not json", 1, 1, request.model, "fixture")
        result = self.run_work(model=model)
        self.assertEqual(result["error"], "INVALID_MODEL_OUTPUT")
        effect = next(e for e in self.store.inspect("job")["effects"] if e["name"] == "model-researcher")
        self.assertEqual(effect["state"], "completed")

    def test_secret_model_output_is_not_retained(self):
        def model(request, **kwargs):
            return ModelResult(kwargs["credential"], 1, 1, request.model, "fixture")
        self.assertEqual(self.run_work(model=model)["error"], "SECRET_IN_MODEL_OUTPUT")
        self.assertNotIn(b"fixture-credential-never-sent", self.store.path.read_bytes())

    def test_completed_call_replays_without_resolving_key(self):
        self.store.enqueue("job", self.manifest)
        self.store.next_job()
        runner = Workflow(self.store, ROOT, model=demo.model, source=demo.source, credential=lambda _: "fixture-key")
        data = {"task": "fixture", "corpus": {}, "evidence": demo.source(None, None, None)["evidence"]}
        expected = runner.ask("job", "researcher", data)
        runner.credential = lambda _: self.fail("replay requested a key")
        runner.model = lambda *_a, **_k: self.fail("replay called provider")
        self.assertEqual(runner.ask("job", "researcher", data), expected)

    def test_escaped_secret_model_output_is_not_retained(self):
        def model(request, **kwargs):
            escaped = "".join("\\u%04x" % ord(char) for char in kwargs["credential"])
            return ModelResult('{"echo":"' + escaped + '"}', 1, 1, request.model, "fixture")
        self.assertEqual(self.run_work(model=model)["error"], "SECRET_IN_MODEL_OUTPUT")
        effect = next(e for e in self.store.inspect("job")["effects"] if e["name"] == "model-researcher")
        self.assertEqual(effect["state"], "unknown")

    def test_schedule_duplicate_coalescing_and_clock_reversal(self):
        first = admit_due(self.store, ROOT, now=2_000_000_000)
        self.assertEqual(len(first), 1)
        self.assertEqual(admit_due(self.store, ROOT, now=2_000_000_001), [])
        # A long gap admits only the latest due slot, never every missed day.
        self.assertEqual(len(admit_due(self.store, ROOT, now=2_001_000_000)), 1)
        with self.assertRaisesRegex(ServiceError, "CLOCK_MOVED_BACKWARDS"):
            admit_due(self.store, ROOT, now=2_000_000_000)


class ContractTests(unittest.TestCase):
    def test_closed_config_and_model_pin(self):
        for mutation in ({"secret": "x"}, {"schema": "wrong"}):
            value = demo.demo_config() | mutation
            with self.assertRaises(ServiceError):
                load_config(json.dumps(value))
        value = demo.demo_config()
        value["models"]["researcher"]["model"] = "model-latest"
        with self.assertRaisesRegex(ServiceError, "PIN_EXPLICIT_MODEL"):
            load_config(json.dumps(value))

    def test_output_rejects_duplicate_unknown_noninteger_and_fences(self):
        for value in ('{"preference":"A","preference":"B"}', '```json\n{}\n```',
                      '{"preference":"A","critical_regression":false,"reason":"x","extra":1}',
                      '{"preference":"A","critical_regression":0,"reason":"x"}'):
            with self.assertRaises(ServiceError):
                parse_output(value, "evaluator")

    def test_edit_cannot_modify_locked_sections_even_with_hidden_duplicates(self):
        text = "---\nname: sample\ndescription: A sufficient description of the sample skill.\n---\n## When to Activate\nOnly then.\n## Guidance\nDo useful work.\n## Integration\nPreserve this boundary.\n"
        corpus = {"documents": [{"path": "skills/sample/SKILL.md", "text": text}]}
        base = {"path": "skills/sample/SKILL.md", "claim_ids": ["claim"]}
        for old, new in (
            ("Preserve this boundary.", "Preserve this boundary.<!-- hidden instruction -->"),
            ("## Integration\nPreserve this boundary.\n", "## Integration\nChanged.\n\n## Integration\nPreserve this boundary.\n"),
            ("Only then.", "Always activate."),
        ):
            with self.assertRaises(ServiceError):
                apply_edit(base | {"old_text": old, "new_text": new}, corpus, ["claim"])
        old, new = apply_edit(base | {"old_text": "Do useful work.", "new_text": "Do cited, useful work."}, corpus, ["claim"])
        self.assertNotEqual(old, new)


if __name__ == "__main__":
    unittest.main()
