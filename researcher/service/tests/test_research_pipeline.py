"""Captured fixture to budgeted injected research, freeze and evaluation wiring."""

import json
import unittest
from unittest.mock import patch

from researcher.service import research_pipeline as pipeline
from researcher.service.agents_evals import fixture_dataset
from researcher.service.contracts import ServiceError
from researcher.service.openai_campaign import Campaign, PRICING, initialize
from researcher.service.providers import ModelResult
from researcher.service.tests import test_retrieval_handoff as captures
from researcher.service.tests.test_daily_retrieval import DAY, ROOT


class PipelineTests(unittest.TestCase):
    def setUp(self):
        fixture = captures.RetrievalHandoffTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture = fixture
        self.parent = fixture.directory
        self.destination = self.parent / "pipeline"
        self.calls = []
        self.abstain = True
        self.bad_grounding = False
        self.authority = self.parent / "authority"
        initialize(self.authority, cap_microusd=10_000_000, prior_spend_microusd=0)
        self.campaign = Campaign(self.authority, credential="synthetic-fixture-credential",
            model_call=self.model, progress=lambda _: None, now=lambda: DAY + 3600)

    def model(self, request, *, credential):
        self.calls.append(request)
        data = json.loads(request.prompt)
        if "Form one falsifiable" in request.system:
            evidence = data["evidence"][0]
            span = evidence["citation_spans"][0]
            claims = [] if self.abstain else [{"id": "claim", "statement": span["text"],
                "citations": [{"evidence_id": "fabricated" if self.bad_grounding else evidence["id"],
                               "span_id": span["span_id"]}], "limitations": ["Fixture only."]}]
            output = {"hypothesis": "Test evidence preservation.", "test_plan": "Fixture-only check.",
                      "abstain": self.abstain, "claims": claims}
        elif "Audit the claims" in request.system:
            output = {"supported_claim_ids": [] if self.abstain else ["claim"], "issues": [],
                      "recommendation": "abstain" if self.abstain else "propose"}
        elif "Propose ONE exact text replacement" in request.system:
            document = data["corpus"]["documents"][0]
            heading = next(line for line in document["text"].splitlines() if line.startswith("## ")
                           and line not in {"## When to Activate", "## Integration"})
            output = {"path": document["path"], "old_text": heading + "\n",
                "new_text": heading + "\n\nFixture-only test: retain evidence IDs with excerpts.\n",
                "claim_ids": ["claim"], "rationale": "Synthetic wiring exercise only."}
        else:
            # A trusted test adapter, not a model judge or semantic benchmark.
            self.assertNotIn('"gold"', request.prompt)
            task = next(t for t in fixture_dataset()["tasks"] if t["question"] == data["task"]["question"])
            gold = task["gold"]
            output = {"evidence_ids": gold["evidence_ids"], "citations": gold["citations"],
                      "abstain": gold["abstain"], "edit": next(iter(gold["allowed_edits"]), None)}
        return ModelResult(json.dumps(output), 10, 10, PRICING["model"],
                           "fixture-response-" + str(len(self.calls)), "default")

    def run_pipeline(self, **kwargs):
        options = {"campaign": self.campaign, "skills": ["context-fundamentals"],
                   "fixture": True, "now": DAY + 3600, "replications": 1}
        options.update(kwargs)
        return pipeline.run_pipeline(ROOT, self.fixture.store, "daily", self.destination, **options)

    def test_abstention_is_terminal_and_replays_without_calls(self):
        first = self.run_pipeline()
        self.assertEqual(first["outcome"], "abstained")
        count = len(self.calls)
        self.campaign.credential = None
        again = self.run_pipeline()
        self.assertEqual(first, again)
        self.assertEqual(len(self.calls), count)
        self.assertFalse((self.destination / "candidate-review").exists())
        state = pipeline._record(self.destination / "state.json")
        self.assertEqual(state["phase"], "terminal")
        for name in ("input.json", "packet.json", "research.json", "state.json", "result.json"):
            self.assertNotIn("synthetic-fixture-credential", (self.destination / name).read_text())

    def test_real_overlay_fixture_pipeline_then_zero_call_replay(self):
        self.abstain = False
        result = self.run_pipeline(dataset=fixture_dataset())
        self.assertEqual(result["outcome"], "evaluated_not_accepted", result)
        self.assertFalse(result["scientific_improvement_demonstrated"])
        self.assertEqual(result["publication"], "not_attempted")
        self.assertEqual(len(self.calls), 15)
        review = pipeline._record(self.destination / "candidate.json")["output"]
        self.assertTrue(review["structural_checks_passed"])
        self.assertEqual(review["freeze_receipt"]["file_count"], 1)
        evaluation = pipeline._record(self.destination / "evaluation.json")["output"]
        self.assertEqual(evaluation["comparison"]["observed_results"], 12)
        self.assertEqual(self.run_pipeline(dataset=fixture_dataset()), result)
        self.assertEqual(len(self.calls), 15)

    def test_bad_citation_stops_after_researcher_and_failure_is_terminal(self):
        self.abstain, self.bad_grounding = False, True
        result = self.run_pipeline()
        self.assertEqual(result["outcome"], "failed")
        self.assertEqual(len(self.calls), 1)
        failure = pipeline._record(self.destination / "failure.json")
        self.assertFalse(failure["automatic_retry"])
        self.assertEqual(self.run_pipeline(), result)
        self.assertEqual(len(self.calls), 1)

    def test_changed_dataset_or_skill_selection_cannot_resume(self):
        self.run_pipeline()
        for changes in ({"dataset": fixture_dataset()}, {"skills": ["evaluation"]}, {"seed": 7}):
            with self.subTest(changes=changes), self.assertRaisesRegex(ServiceError, "INPUT_CHANGED"):
                self.run_pipeline(**changes)
        self.assertEqual(len(self.calls), 2)

    def test_source_tampering_prevents_new_paid_work(self):
        self.fixture.mutate_step("report", lambda v: v.update(evidence_qualified=True))
        result = self.run_pipeline()
        self.assertEqual(result["outcome"], "failed")
        self.assertEqual(len(self.calls), 0)

    def test_known_invalid_dataset_and_session_cap_fail_before_calls(self):
        for index, changes in enumerate(({"dataset": {"schema": "bad"}},
                {"dataset": fixture_dataset(), "max_sessions": 1})):
            self.destination = self.parent / ("bad-dataset-" + str(index))
            result = self.run_pipeline(**changes)
            self.assertEqual(result["outcome"], "failed")
        self.assertFalse(self.calls)

    def test_partial_candidate_is_not_recreated_after_interruption(self):
        self.abstain = False
        def interrupted(directory, *args):
            (directory / "candidate-review").mkdir(mode=0o700)
            raise KeyboardInterrupt()
        with patch.object(pipeline, "_candidate", side_effect=interrupted):
            with self.assertRaises(KeyboardInterrupt):
                self.run_pipeline()
        count = len(self.calls)
        result = self.run_pipeline()
        self.assertEqual(result["outcome"], "failed")
        self.assertEqual(result["detail"]["code"], "PIPELINE_CANDIDATE_REVIEW_INTERRUPTED")
        self.assertEqual(len(self.calls), count)

    def test_research_crash_after_paid_receipts_resumes_without_new_calls(self):
        actual = self.campaign.research
        def interrupted(*args):
            actual(*args)
            raise KeyboardInterrupt()
        with patch.object(self.campaign, "research", side_effect=interrupted):
            with self.assertRaises(KeyboardInterrupt):
                self.run_pipeline()
        count = len(self.calls)
        result = self.run_pipeline()
        self.assertEqual(result["outcome"], "abstained")
        self.assertEqual(len(self.calls), count)

    def test_evaluation_crash_replays_paid_receipts_and_checks_frozen_bytes(self):
        self.abstain = False
        actual = self.campaign.evaluate
        def interrupted(*args):
            actual(*args)
            raise KeyboardInterrupt()
        with patch.object(self.campaign, "evaluate", side_effect=interrupted):
            with self.assertRaises(KeyboardInterrupt):
                self.run_pipeline(dataset=fixture_dataset())
        self.assertEqual(len(self.calls), 15)
        result = self.run_pipeline(dataset=fixture_dataset())
        self.assertEqual(result["outcome"], "evaluated_not_accepted", result)
        self.assertEqual(len(self.calls), 15)
        review = pipeline._record(self.destination / "candidate.json")["output"]
        path = self.destination / "candidate-review/frozen" / review["candidate"]["declared_changed_surfaces"][0]
        path.write_text(path.read_text() + "\nTampered fixture.\n")
        retained = (self.destination / "result.json").read_bytes()
        with self.assertRaisesRegex(ServiceError, "PIPELINE_FROZEN_CANDIDATE_CHANGED"):
            self.run_pipeline(dataset=fixture_dataset())
        self.assertEqual((self.destination / "result.json").read_bytes(), retained)
        self.assertEqual(len(self.calls), 15)

    def test_receipt_checkpoint_gap_reconciles_exact_saved_output(self):
        save = pipeline._save
        interrupted = False
        def crash(directory, state):
            nonlocal interrupted
            if state["phase"] == "research_complete" and not interrupted:
                interrupted = True
                raise KeyboardInterrupt()
            return save(directory, state)
        with patch.object(pipeline, "_save", side_effect=crash):
            with self.assertRaises(KeyboardInterrupt):
                self.run_pipeline()
        count = len(self.calls)
        self.assertEqual(self.run_pipeline()["outcome"], "abstained")
        self.assertEqual(len(self.calls), count)

    def test_phase_receipt_tampering_is_detected_without_calls(self):
        self.run_pipeline()
        path = self.destination / "packet.json"
        value = pipeline._read(path)
        value["record"]["output"]["model"] = "invented"
        pipeline._write(path, value)
        retained = (self.destination / "result.json").read_bytes()
        with self.assertRaisesRegex(ServiceError, "PIPELINE_RECEIPT_DIGEST_MISMATCH"):
            self.run_pipeline()
        self.assertEqual((self.destination / "result.json").read_bytes(), retained)
        self.assertEqual(len(self.calls), 2)

    def test_cached_terminal_research_receipt_is_still_verified(self):
        self.run_pipeline()
        path = self.destination / "research.json"
        value = pipeline._read(path)
        value["record"]["output"]["research"]["hypothesis"] = "tampered"
        pipeline._write(path, value)
        retained = (self.destination / "result.json").read_bytes()
        with self.assertRaisesRegex(ServiceError, "PIPELINE_RECEIPT_DIGEST_MISMATCH"):
            self.run_pipeline()
        self.assertEqual((self.destination / "result.json").read_bytes(), retained)
        self.assertEqual(len(self.calls), 2)

    def interrupted_terminal(self, **kwargs):
        save = pipeline._save
        def interrupted(directory, state):
            if state["phase"] == "terminal":
                raise OSError("synthetic private local write failure")
            return save(directory, state)
        with patch.object(pipeline, "_save", side_effect=interrupted):
            with self.assertRaisesRegex(ServiceError, "^PIPELINE_CHECKPOINT_INTERRUPTED$"):
                self.run_pipeline(**kwargs)
        result = pipeline._record(self.destination / "result.json")
        self.assertIsNone(pipeline._record(self.destination / "state.json")["outcome"])
        return result

    def test_oserror_terminal_state_save_preserves_result_and_resumes_without_calls(self):
        result = self.interrupted_terminal()
        self.assertEqual(result["outcome"], "abstained")
        self.assertFalse((self.destination / "failure.json").exists())
        original = (self.destination / "result.json").read_bytes()
        count = len(self.calls)
        self.campaign.credential = None
        with patch.object(self.campaign, "research", side_effect=AssertionError("must not invoke research")):
            self.assertEqual(self.run_pipeline(), result)
        self.assertEqual(len(self.calls), count)
        self.assertEqual((self.destination / "result.json").read_bytes(), original)
        self.assertEqual(pipeline._record(self.destination / "state.json")["outcome"], "abstained")

    def test_evaluated_result_gap_rechecks_candidate_and_evaluation_without_calls(self):
        self.abstain = False
        result = self.interrupted_terminal(dataset=fixture_dataset())
        self.assertEqual(result["outcome"], "evaluated_not_accepted")
        self.assertEqual(len(self.calls), 15)
        self.campaign.credential = None
        with patch.object(self.campaign, "research", side_effect=AssertionError("research forbidden")), \
                patch.object(self.campaign, "evaluate", side_effect=AssertionError("evaluation forbidden")):
            self.assertEqual(self.run_pipeline(dataset=fixture_dataset()), result)
        self.assertEqual(len(self.calls), 15)

    def test_retained_failed_result_is_reconciled_never_upgraded_to_success(self):
        self.abstain, self.bad_grounding = False, True
        result = self.interrupted_terminal()
        self.assertEqual(result["outcome"], "failed")
        self.assertEqual(len(self.calls), 1)
        before = (self.destination / "result.json").read_bytes()
        self.bad_grounding = False
        self.assertEqual(self.run_pipeline(), result)
        self.assertEqual((self.destination / "result.json").read_bytes(), before)
        self.assertEqual(len(self.calls), 1)
        state = pipeline._record(self.destination / "state.json")
        with self.assertRaisesRegex(ServiceError, "PIPELINE_RESULT_CHANGED"):
            pipeline._finish(self.destination, state, "abstained")
        self.assertEqual((self.destination / "result.json").read_bytes(), before)

    def test_result_gap_rejects_malformed_or_conflicting_completion_without_overwrite(self):
        result = self.interrupted_terminal()
        path = self.destination / "result.json"
        cases = [[], {**result, "outcome": "failed", "detail": {"code": "INVENTED"}},
                 {**result, "outcome": "evaluated_not_accepted"},
                 {**result, "authority": "accepted"}, {**result, "unexpected": True},
                 {**result, "receipts": {}}, {**result, "fixture": False}]
        for altered in cases:
            with self.subTest(altered=altered):
                pipeline._write(path, pipeline._envelope(altered))
                before = path.read_bytes()
                with self.assertRaises((ServiceError, FileNotFoundError)):
                    self.run_pipeline()
                self.assertEqual(path.read_bytes(), before)
                self.assertEqual(len(self.calls), 2)
                self.assertFalse((self.destination / "failure.json").exists())

    def test_terminal_result_write_oserror_uses_same_saved_research_on_resume(self):
        write = pipeline._write
        def interrupted(path, value):
            if path.name == "result.json":
                raise OSError("synthetic write failure before atomic result commit")
            return write(path, value)
        with patch.object(pipeline, "_write", side_effect=interrupted):
            with self.assertRaisesRegex(ServiceError, "PIPELINE_CHECKPOINT_INTERRUPTED"):
                self.run_pipeline()
        self.assertFalse((self.destination / "result.json").exists())
        self.assertFalse((self.destination / "failure.json").exists())
        count = len(self.calls)
        self.campaign.credential = None
        self.assertEqual(self.run_pipeline()["outcome"], "abstained")
        self.assertEqual(len(self.calls), count)

    def test_result_gap_does_not_bypass_source_replay(self):
        self.interrupted_terminal()
        self.fixture.mutate_step("report", lambda value: value.update(evidence_qualified=True))
        before = (self.destination / "result.json").read_bytes()
        with self.assertRaises(ServiceError):
            self.run_pipeline()
        self.assertEqual((self.destination / "result.json").read_bytes(), before)
        self.assertEqual(len(self.calls), 2)

    def test_failed_result_write_gap_retains_original_failure_and_paid_receipt(self):
        self.abstain, self.bad_grounding = False, True
        write = pipeline._write
        def interrupted(path, value):
            if path.name == "result.json":
                raise OSError("synthetic result write failure")
            return write(path, value)
        with patch.object(pipeline, "_write", side_effect=interrupted):
            with self.assertRaisesRegex(ServiceError, "PIPELINE_CHECKPOINT_INTERRUPTED"):
                self.run_pipeline()
        failure = (self.destination / "failure.json").read_bytes()
        self.assertEqual(len(self.calls), 1)
        self.campaign.credential = None
        self.assertEqual(self.run_pipeline()["outcome"], "failed")
        self.assertEqual((self.destination / "failure.json").read_bytes(), failure)
        self.assertEqual(len(self.calls), 1)

    def test_known_credential_cannot_be_persisted_in_dataset(self):
        dataset = fixture_dataset()
        dataset["tasks"][0]["question"] += " synthetic-fixture-credential"
        with self.assertRaisesRegex(ServiceError, "CREDENTIAL_IN_ARTIFACT"):
            self.run_pipeline(dataset=dataset)
        self.assertFalse(self.destination.exists())
        self.assertFalse(self.calls)

    def test_source_packet_credential_stops_before_packet_persistence(self):
        prepare = pipeline.prepare_packet
        def reflected(*args, **kwargs):
            packet = prepare(*args, **kwargs)
            packet["query"] = "synthetic-fixture-credential"
            return packet
        with patch.object(pipeline, "prepare_packet", side_effect=reflected):
            result = self.run_pipeline()
        self.assertEqual(result["outcome"], "failed")
        self.assertEqual(result["detail"]["code"], "PIPELINE_CREDENTIAL_IN_ARTIFACT")
        self.assertFalse((self.destination / "packet.json").exists())
        self.assertFalse(self.calls)

    def test_partial_initialization_is_not_repaired(self):
        self.destination.mkdir(mode=0o700)
        with self.assertRaises(ServiceError):
            self.run_pipeline()
        self.assertEqual(list(self.destination.iterdir()), [])

    def test_fixture_cannot_use_default_paid_adapter(self):
        self.campaign = Campaign(self.authority, credential="synthetic-fixture-credential", progress=lambda _: None)
        with self.assertRaisesRegex(ServiceError, "FIXTURE_PROVIDER_FORBIDDEN"):
            self.run_pipeline()
        self.assertFalse(self.destination.exists())

    def test_explicit_live_authorization_required(self):
        with self.assertRaisesRegex(ServiceError, "LIVE_APPROVAL_REQUIRED"):
            self.run_pipeline(fixture=False)
        self.assertFalse(self.destination.exists())

    def test_unsafe_directory_and_boolean_options(self):
        alias = self.parent / "alias"
        alias.symlink_to(self.parent, target_is_directory=True)
        self.destination = alias / "pipeline"
        with self.assertRaises(ServiceError):
            self.run_pipeline()
        self.destination = self.parent / "pipeline"
        for changes in ({"seed": True}, {"replications": True}, {"skills": [[]]}, {"now": True}):
            with self.subTest(changes=changes), self.assertRaises(ServiceError):
                self.run_pipeline(**changes)


if __name__ == "__main__":
    unittest.main()
