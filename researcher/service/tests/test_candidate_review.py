"""Offline review/freeze/overlay contracts, not skill-effectiveness results."""

from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from researcher.service import candidate_review as review
from researcher.service.agents_evals import fixture_dataset, task_request
from researcher.service.agents_context import compile_request
from researcher.service.agents_runtime import SessionLedger, _write
from researcher.service.contracts import ServiceError, digest
from researcher.service.knowledge import retrieve_corpus
from researcher.scripts.schema_contract import sha256_bytes


class CandidateReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.parent = Path(self.tmp.name).resolve()
        self.parent.chmod(0o700)
        self.root = self.parent / "repository"
        self.path = "skills/sample/SKILL.md"
        target = self.root / self.path
        target.parent.mkdir(parents=True)
        self.original = (
            "---\nname: sample\ndescription: Read scoped retrieval evidence carefully.\n---\n"
            "## When to Activate\nOnly when retrieval is needed.\n"
            "## Guidance\nRead the source.\n"
            "## Integration\nPreserve boundaries.\n")
        target.write_text(self.original)
        for relative in review.DERIVED_PATHS:
            generated = self.root / relative
            generated.parent.mkdir(parents=True, exist_ok=True)
            generated.write_text("fixture original inventory\n")
        self.corpus = retrieve_corpus(self.root, "retrieval", ["sample"], 65536)
        text = "Fixture: retain source identity with exact evidence spans."
        self.evidence = [{"id": "fixture", "source": "fixture", "text": text,
                          "sha256": sha256_bytes(text.encode()), "evidence_scope": "synthetic_fixture"}]
        self.output = {"schema": "managed-research-proposal/v1", "authority": "none",
            "research": {"hypothesis": "Test source identity preservation.",
                "test_plan": "A synthetic wiring test only.", "abstain": False,
                "claims": [{"id": "claim", "statement": text,
                    "citations": [{"evidence_id": "fixture", "quote": text}],
                    "limitations": ["Synthetic, not scientific evidence."]}]},
            "critic": {"supported_claim_ids": ["claim"], "issues": [], "recommendation": "propose"},
            "proposal": {"path": self.path, "old_text": "Read the source.",
                "new_text": "Retain source identity with exact evidence spans.",
                "claim_ids": ["claim"], "rationale": "Fixture-only edit."}}
        self.head = "a" * 40
        self.binding = {"baseline_commit": self.head, "manifest_digest": digest({"fixture": True}),
                        "result_digest": digest(self.output)}
        self.destination = self.parent / "review"
        self.addCleanup(patch.stopall)
        patch.object(review, "_head", return_value=self.head).start()
        self.paths = sorted([self.path, *review.DERIVED_PATHS])
        self.path_patch = patch.object(review, "_paths", return_value=self.paths).start()
        self.validator = patch.object(review, "_run_validator", side_effect=lambda overlay, cmd, logs: {
            "name": cmd[0], "status": "completed", "exit_code": 0, "passed": True,
            "output_digest": sha256_bytes(b""), "output_bytes": 0}).start()

    def run_review(self, **kwargs):
        options = {"corpus": self.corpus, "evidence": self.evidence, "output": self.output,
                   "source_binding": self.binding}
        options.update(kwargs)
        return review.review_candidate(self.root, self.destination, **options)

    def test_freezes_materialized_bytes_and_leaves_source_unchanged(self):
        result = self.run_review()
        expected = self.original.replace("Read the source.", self.output["proposal"]["new_text"])
        self.assertEqual((self.root / self.path).read_text(), self.original)
        self.assertEqual((self.destination / "frozen" / self.path).read_text(), expected)
        self.assertEqual((self.destination / "overlay" / self.path).read_text(), expected)
        self.assertEqual(result["freeze_receipt"]["entries"][0]["digest"], sha256_bytes(expected.encode()))
        self.assertEqual(result["evaluation"], "unplanned_missing_dataset")
        self.assertFalse(result["production_ready"])
        self.assertFalse(result["multi_surface_consistency_assessed"])
        self.assertEqual(result["authority"], "none")
        self.assertEqual(result["model_calls"], 0)
        self.assertEqual(self.validator.call_count, 5)
        self.assertEqual(result["review_digest"], digest({k:v for k,v in result.items() if k != "review_digest"}))

    def test_explicit_fixture_plan_uses_frozen_candidate_not_author_rationale(self):
        result = self.run_review(dataset=fixture_dataset(), model="fixture-model", replications=1)
        plan = json.loads((self.destination / "evaluation-plan.json").read_text())
        self.assertEqual(result["evaluation_plan_digest"], plan["plan_digest"])
        self.assertEqual(plan["skills"]["candidate"], (self.destination / "frozen" / self.path).read_text())
        self.assertEqual(plan["skills"]["baseline"], self.original)
        self.assertEqual(plan["dataset"]["kind"], "fixture")
        for item in plan["items"]:
            request = task_request(plan, item["item_id"])
            self.assertNotIn('"gold"', request["prompt"])
            self.assertNotIn(self.output["proposal"]["rationale"], request["prompt"])

    def test_binding_drift_or_extra_fields_rejected_before_artifacts(self):
        for changed in ({**self.binding, "result_digest": digest({})},
                        {**self.binding, "manifest_digest": "invalid"},
                        {**self.binding, "baseline_commit": "b" * 40},
                        {**self.binding, "accepted": True}):
            with self.subTest(changed=changed), self.assertRaises(ServiceError):
                self.run_review(source_binding=changed)
            self.assertFalse(self.destination.exists())

    def test_source_baseline_changed_before_review(self):
        (self.root / self.path).write_text(self.original + "\nchanged")
        with self.assertRaisesRegex(ServiceError, "BASELINE_CHANGED"):
            self.run_review()
        self.assertFalse(self.destination.exists())

    def test_source_change_between_initial_read_and_snapshot_rejected(self):
        snapshot = review._snapshot
        def race(root, paths, destination=None):
            if destination is not None:
                (root / self.path).write_text(self.original + "\nconcurrent change")
            return snapshot(root, paths, destination)
        with patch.object(review, "_snapshot", side_effect=race):
            with self.assertRaisesRegex(ServiceError, "BASELINE_CHANGED"):
                self.run_review()
        self.assertFalse((self.destination / "candidate-cas").exists())

    def test_invalid_encoding_rejected_before_artifacts(self):
        output = deepcopy(self.output)
        output["research"]["hypothesis"] = "\ud800"
        with self.assertRaisesRegex(ServiceError, "INPUT_LIMIT_OR_ENCODING"):
            self.run_review(output=output)
        self.assertFalse(self.destination.exists())

    def test_locked_section_edit_rejected(self):
        output = deepcopy(self.output)
        output["proposal"].update(old_text="Preserve boundaries.", new_text="Change boundaries.")
        with self.assertRaisesRegex(ServiceError, "LOCKED"):
            self.run_review(output=output, source_binding={**self.binding, "result_digest": digest(output)})

    def test_abstention_is_not_candidate(self):
        output = deepcopy(self.output)
        output["proposal"] = None
        output["research"].update(abstain=True, claims=[])
        output["critic"].update(supported_claim_ids=[], recommendation="abstain")
        with self.assertRaisesRegex(ServiceError, "PROPOSAL_REQUIRED"):
            self.run_review(output=output, source_binding={**self.binding, "result_digest": digest(output)})

    def test_plan_needs_both_model_and_explicit_valid_labels(self):
        for kwargs in ({"model": "fixed"}, {"dataset": fixture_dataset()},
                       {"dataset": {"tasks": []}, "model": "fixed"},
                       {"dataset": fixture_dataset(), "model": "fixed", "replications": True}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ServiceError):
                self.run_review(**kwargs)
            self.assertFalse(self.destination.exists())

    def test_existing_or_in_checkout_destination_rejected(self):
        self.destination.mkdir()
        marker = self.destination / "marker"
        marker.write_text("retained")
        with self.assertRaises(FileExistsError):
            self.run_review()
        self.assertEqual(marker.read_text(), "retained")
        self.root.chmod(0o700)
        self.destination = self.root / "review"
        with self.assertRaisesRegex(ServiceError, "UNSAFE_DESTINATION"):
            self.run_review()

    def test_symlink_source_or_destination_rejected(self):
        target = self.root / self.path
        other = self.parent / "source"
        target.rename(other)
        target.symlink_to(other)
        with self.assertRaises(ValueError):
            self.run_review()
        target.unlink()
        other.rename(target)
        alias = self.parent / "alias"
        alias.symlink_to(self.parent, target_is_directory=True)
        self.destination = alias / "review"
        with self.assertRaises(ServiceError):
            self.run_review()

    def test_validator_failure_is_recorded_not_acceptance(self):
        self.validator.side_effect = lambda overlay, cmd, logs: {
            "name": cmd[0], "status": "completed", "exit_code": 1,
            "passed": False, "output_digest": sha256_bytes(b"failed"), "output_bytes": 6}
        result = self.run_review(dataset=fixture_dataset(), model="fixed", replications=1)
        self.assertEqual(result["disposition"], "structural_validation_failed")
        self.assertFalse(result["structural_checks_passed"])
        self.assertEqual(result["evaluation"], "planned_not_executed")

    def test_validator_mutation_fails_integrity_check(self):
        def mutate(overlay, cmd, logs):
            if cmd != review.DERIVATION:
                (overlay / self.path).write_text("mutated")
            return {"name": cmd[0], "passed": True}
        self.validator.side_effect = mutate
        with self.assertRaisesRegex(ServiceError, "SOURCE_OR_OVERLAY_CHANGED"):
            self.run_review()
        self.assertFalse((self.destination / "review.json").exists())

    def test_source_drift_during_validators_fails_integrity(self):
        def mutate(overlay, cmd, logs):
            (self.root / self.path).write_text(self.original + "\nchanged")
            return {"name": cmd[0], "passed": True}
        self.validator.side_effect = mutate
        with self.assertRaisesRegex(ServiceError, "SOURCE_OR_OVERLAY_CHANGED"):
            self.run_review()

    def test_extra_overlay_file_fails_integrity(self):
        def mutate(overlay, cmd, logs):
            if cmd != review.DERIVATION:
                (overlay / "extra.txt").write_text("not in frozen overlay")
            return {"name": cmd[0], "passed": True}
        self.validator.side_effect = mutate
        with self.assertRaisesRegex(ServiceError, "SOURCE_OR_OVERLAY_CHANGED"):
            self.run_review()

    def test_only_declared_inventory_outputs_can_be_derived(self):
        def derive(overlay, cmd, logs):
            if cmd == review.DERIVATION:
                for relative in review.DERIVED_PATHS:
                    (overlay / relative).write_text("trusted regenerated fixture\n")
            return {"name": cmd[0], "passed": True}
        self.validator.side_effect = derive
        result = self.run_review()
        self.assertTrue(result["structural_checks_passed"])
        derivation = result["derivation"]
        self.assertEqual(len(derivation["outputs"]), 2)
        self.assertNotEqual(derivation["before_files_digest"], derivation["after_files_digest"])
        self.assertTrue(derivation["non_derived_files_unchanged"])
        self.assertEqual(result["freeze_receipt"]["file_count"], 1)
        for relative in review.DERIVED_PATHS:
            self.assertEqual((self.root / relative).read_text(), "fixture original inventory\n")

    def test_derivation_cannot_write_skill_or_new_file(self):
        for relative in (self.path, "unexpected.txt"):
            self.destination = self.parent / ("review-" + str(len(relative)))
            def mutate(overlay, cmd, logs):
                if cmd == review.DERIVATION:
                    (overlay / relative).write_text("unauthorized")
                return {"name": cmd[0], "passed": True}
            self.validator.side_effect = mutate
            with self.subTest(relative=relative), self.assertRaisesRegex(ServiceError, "DERIVATION_UNAUTHORIZED"):
                self.run_review()

    def test_derived_inventory_drift_during_validator_rejected(self):
        def mutate(overlay, cmd, logs):
            if cmd != review.DERIVATION:
                (overlay / review.DERIVED_PATHS[0]).write_text("changed after derivation")
            return {"name": cmd[0], "passed": True}
        self.validator.side_effect = mutate
        with self.assertRaisesRegex(ServiceError, "SOURCE_OR_OVERLAY_CHANGED"):
            self.run_review()

    def managed(self):
        packet = {"schema": "managed-research-packet/v1", "corpus": self.corpus,
            "evidence": self.evidence, "model": "fixture-model", "query": "retrieval",
            "max_subagents": 0, "fixture": True, "baseline_commit": self.head,
            "implementation_digest": digest({"fixture": True}),
            "request": compile_request(model="fixture-model", query="retrieval", corpus=self.corpus,
                                       evidence=self.evidence, max_subagents=0)}
        ledger = SessionLedger.prepare(self.parent / "managed", packet)
        result = {"schema": "managed-research-result/v1", "manifest_digest": digest(packet),
            "session_id": "fixture-session", "turn_id": "fixture-turn", "result": self.output,
            "production_ready": False, "independent_evaluation": "not_run"}
        _write(ledger.directory / "result.json", result)
        _, state = ledger.load()
        state.update(phase="completed", session_id="fixture-session", result_digest=digest(result))
        ledger.save(state)
        return ledger, result

    def test_managed_completed_result_is_bound_to_review(self):
        ledger, envelope = self.managed()
        result = review.review_managed(self.root, ledger.directory, self.destination)
        origin = json.loads((self.destination / "managed-origin.json").read_text())
        self.assertEqual(origin["result_envelope_digest"], digest(envelope))
        self.assertEqual(origin["review_digest"], result["review_digest"])
        self.assertTrue(origin["fixture"])
        self.assertEqual(result["source_binding"]["result_digest"], digest(self.output))

    def test_managed_result_hash_forgery_rejected_before_review(self):
        ledger, envelope = self.managed()
        envelope["result"]["research"]["hypothesis"] = "forged"
        _write(ledger.directory / "result.json", envelope)
        with self.assertRaisesRegex(ServiceError, "RESULT_DIGEST_MISMATCH"):
            review.review_managed(self.root, ledger.directory, self.destination)
        self.assertFalse(self.destination.exists())

    def test_managed_rebound_cross_session_envelope_rejected(self):
        ledger, envelope = self.managed()
        _, state = ledger.load()
        envelope["session_id"] = "different-session"
        _write(ledger.directory / "result.json", envelope)
        state["result_digest"] = digest(envelope)
        ledger.save(state)
        with self.assertRaisesRegex(ServiceError, "BINDING_INVALID"):
            review.review_managed(self.root, ledger.directory, self.destination)

    def test_managed_noncompleted_session_cannot_freeze(self):
        ledger, _ = self.managed()
        _, state = ledger.load()
        state["phase"] = "running"
        ledger.save(state)
        with self.assertRaisesRegex(ServiceError, "NOT_COMPLETED"):
            review.review_managed(self.root, ledger.directory, self.destination)

class BoundaryTests(unittest.TestCase):
    def test_selector_rejects_secrets_runtime_and_traversal(self):
        for name in (".env", ".env.local", "nested/.env.prod", "researcher/runtime/x.json",
                     "researcher/runs/private/output.json", "../escape", "/absolute", "a/../b"):
            with self.subTest(name=name), patch.object(review, "_git", return_value=name.encode()+b"\0"):
                with self.assertRaisesRegex(ServiceError, "UNSAFE_SOURCE_PATH"):
                    review._paths(Path("/unused"))

    def test_selector_count_cap(self):
        with patch.object(review, "_git", return_value=b"x\0"), patch.object(review, "MAX_FILES", 0):
            with self.assertRaisesRegex(ServiceError, "SOURCE_LIMIT"):
                review._paths(Path("/unused"))

    def test_minimal_environment_does_not_inherit_secret_or_python_hooks(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "synthetic", "PYTHONPATH": "/bad", "HTTP_PROXY": "bad"}):
            env = review._environment(Path("/private/scratch"))
        self.assertNotIn("OPENAI_API_KEY", env)
        self.assertNotIn("PYTHONPATH", env)
        self.assertNotIn("HTTP_PROXY", env)

    def test_real_bounded_validator_process_and_private_log(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            scripts = root / "researcher/scripts"
            scripts.mkdir(parents=True)
            # Trusted test-only validator, never supplied by a candidate.
            (scripts / "validate_repo.py").write_text("print('known fixture output')\n")
            logs = root / "logs"
            logs.mkdir()
            result = review._run_validator(root, review.VALIDATORS[0], logs)
            self.assertTrue(result["passed"])
            self.assertEqual(result["output_digest"], sha256_bytes(b"known fixture output\n"))
            self.assertNotIn("known fixture output", json.dumps(result))
            self.assertEqual((logs / "repository.log").stat().st_mode & 0o777, 0o600)

    def test_readonly_foreign_owned_checkout_trust_is_exact_root_only(self):
        root = Path("/reviewed/read-only-release")
        with patch.object(review.subprocess, "run", return_value=SimpleNamespace(returncode=0, stdout=b"proof")) as run:
            self.assertEqual(review._git(root, "rev-parse", "HEAD"), b"proof")
        args = run.call_args.args[0]
        self.assertEqual([value for value in args if value.startswith("safe.directory=")],
                         ["safe.directory=" + str(root)])
        self.assertIn("core.fsmonitor=false", args)
        self.assertIn("core.hooksPath=/dev/null", args)
        self.assertEqual(args[-4:], ["-C", str(root), "rev-parse", "HEAD"])
        self.assertEqual(run.call_args.kwargs["env"]["GIT_CONFIG_NOSYSTEM"], "1")
        self.assertEqual(run.call_args.kwargs["env"]["GIT_CONFIG_GLOBAL"], os.devnull)


if __name__ == "__main__":
    unittest.main()
