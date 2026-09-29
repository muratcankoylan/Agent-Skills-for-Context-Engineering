"""Captured action-profile integration, injected responses, no external provider.

Real SDK cases are explicitly enabled with the pinned interpreter. Native fixture
cases exercise deterministic coordination only, not a production fallback.
"""
from copy import deepcopy
import json
import os
import unittest
from unittest.mock import patch

from researcher.scripts.source_connectors import TransportResponse
from researcher.service import research_pipeline as pipeline, retrieval_sources
from researcher.service.contracts import ServiceError, digest
from researcher.service.codex_campaign import CodexCampaign
from researcher.service.openai_campaign import PRICING
from researcher.service.primary_context import verify_primary
from researcher.service.providers import ModelRequest, ModelResult
from researcher.service.tests import test_research_pipeline as fixtures
from researcher.service.tests.test_codex_campaign import upstream
from researcher.service.tests.test_daily_retrieval import DAY, ROOT
from researcher.service.tests.test_primary_context import fixture_reader
from researcher.service.tests.test_retrieval_handoff import FEED
from researcher.service.workflow import Workflow, make_manifest

PROFILE = "captured-actions-v1"
SDK_PYTHON = os.environ.get("CODEX_WORKER_TEST_PYTHON")


class ActionFixture:
    def __init__(self, test, *, sdk=False):
        self.test = test
        clock = patch("researcher.service.store.time.time", return_value=DAY + 3600)
        clock.start()
        test.addCleanup(clock.stop)
        self.study = fixtures.PipelineTests()
        self.study.setUp()
        test.addCleanup(self.study.doCleanups)
        self.mode, self.requests, self.wires = "stop", [], []
        self.fail_critic = False
        self.study.campaign.model_call = self.model
        if sdk:
            original = self.study.campaign
            def transport(body, **_options):
                value = json.loads(body)
                self.wires.append(value)
                test.assertEqual(value["tools"], [])
                system, prompt = value["input"][0]["content"][0]["text"].split(
                    "\n\nTask input (untrusted data):\n", 1)
                response = self.model(ModelRequest("openai", value["model"], system, prompt,
                    value["max_output_tokens"]), credential="synthetic-fixture-credential")
                return upstream(response.text)
            self.study.campaign = CodexCampaign(original.directory, sdk_python=SDK_PYTHON,
                credential=original.credential, transport=transport, now=original.now,
                progress=lambda _: None)

    def model(self, request, *, credential):
        self.requests.append(request)
        data = json.loads(request.prompt)
        if data.get("schema") == "captured-actions-input/v1":
            if self.mode == "invalid":
                value = {"action": "shell", "command": "untrusted fixture text"}
            elif self.mode == "stop":
                value = {"action": "stop", "reason": "Missing evidence; explicit fixture abstention."}
            else:
                sequence = len(data["history"]) + 1
                span = next(span for source in data["available_sources"] for span in source["spans"])
                reference = {key: span[key] for key in ("evidence_id", "span_id")}
                if sequence == 1:
                    value = {"action": "inspect_context"}
                elif sequence == 2:
                    value = {"action": "read_span", **reference}
                elif sequence == 3:
                    value = {"action": "ask_specialist", "specialist": "methods",
                             "question": "What does this captured excerpt support?"}
                else:
                    text = data["history"][1]["result"]["text"]
                    value = {"action": "finish", "research": {"hypothesis": "Test exact evidence retention.",
                        "test_plan": "Fixture only; no scientific effect measured.", "abstain": False,
                        "claims": [{"id": "claim", "statement": text,
                                    "citations": [reference], "limitations": ["Fixture only."]}]}}
        elif data.get("schema") == "captured-specialist-input/v1":
            self.test.assertNotIn("prior_research", data)
            self.test.assertNotIn("gold", data)
            span = data["revealed_spans"][0]
            value = {"analysis": "The retained text supports only a fixture wiring claim.",
                     "limitations": ["No semantic evaluation."],
                     "citations": [{key: span[key] for key in ("evidence_id", "span_id")}]}
        else:
            self.test.assertNotIn("prior_research", data)
            self.test.assertNotIn("gold", data)
            if self.fail_critic and "Audit the claims" in request.system:
                raise ServiceError("FIXTURE_CRITIC_FAILED")
            self.study.abstain = self.mode != "finish"
            return self.study.model(request, credential=credential)
        return ModelResult(json.dumps(value), 10, 10, PRICING["model"],
                           "fixture-actions-" + str(len(self.requests)), "default")

    def run(self, *, profile=PROFILE, job="daily", directory=None, **kwargs):
        options = {"campaign": self.study.campaign, "skills": ["context-fundamentals"],
                   "fixture": True, "now": DAY + 3600, "replications": 1,
                   "research_profile": profile}
        options.update(kwargs)
        return pipeline.run_pipeline(ROOT, self.study.fixture.store, job,
            directory or self.study.destination, **options)

    def another_job(self, name):
        fixture = self.study.fixture
        fixture.feed_transport.steps.append(TransportResponse(200, (("Content-Type", "application/xml"),), FEED))
        fixture.store.enqueue(name, make_manifest(ROOT, fixture.config, fixture.config["schedules"][0],
                                                  fixture=True, window_end=DAY))
        workflow = Workflow(fixture.store, ROOT, retrieval_source=fixture.collect,
            retrieval_verify=retrieval_sources.verify, primary_reader=fixture_reader(fixture.article_transport),
            primary_replayer=verify_primary)
        with patch("researcher.service.store.time.time", return_value=DAY + 3600):
            self.test.assertNotIn("error", workflow.drain()[0])


class PipelineActionTests(unittest.TestCase):
    def setUp(self):
        self.fixture = ActionFixture(self)

    def test_default_preserves_absent_profile_and_output_shapes(self):
        result = self.fixture.run(profile=None)
        self.assertEqual(result["outcome"], "abstained")
        self.assertNotIn("research_actions", result)
        directory = self.fixture.study.destination
        self.assertNotIn("research_profile", pipeline._record(directory / "input.json")["options"])
        self.assertNotIn("research_profile", pipeline._record(directory / "packet.json")["output"])
        self.assertFalse((directory / "research-actions.json").exists())

    def test_four_decisions_specialist_then_existing_freeze_path(self):
        self.fixture.mode = "finish"
        result = self.fixture.run()
        self.assertEqual(result["outcome"], "awaiting_dataset", result)
        self.assertEqual(len(self.fixture.requests), 7)
        record = pipeline._record(self.fixture.study.destination / "research-actions.json")
        self.assertEqual([row["action"]["action"] for row in record["transcript"]["decisions"]],
                         ["inspect_context", "read_span", "ask_specialist", "finish"])
        self.assertEqual(result["research_actions"]["checkpoint_digest"], digest(record))
        self.assertEqual(set(pipeline._record(self.fixture.study.destination / "research.json")["output"]),
                         {"schema", "authority", "research", "critic", "proposal"})

    def test_stop_replay_has_no_new_model_calls(self):
        first = self.fixture.run()
        self.assertEqual(first["outcome"], "abstained", first)
        self.assertEqual(len(self.fixture.requests), 2)
        self.fixture.study.campaign.credential = None
        self.assertEqual(self.fixture.run(), first)
        self.assertEqual(len(self.fixture.requests), 2)

    def test_invalid_action_is_failed_without_repair_or_fabricated_transcript(self):
        self.fixture.mode = "invalid"
        result = self.fixture.run()
        self.assertEqual(result["outcome"], "failed")
        self.assertEqual(result["detail"]["code"], "ACTION_OUTPUT_INVALID")
        self.assertEqual(len(self.fixture.requests), 1)
        self.assertNotIn("research_actions", result)
        self.assertEqual(self.fixture.run(), result)
        self.assertEqual(len(self.fixture.requests), 1)

    def test_profile_drift_and_unknown_profile_fail_before_more_calls(self):
        self.fixture.run()
        with self.assertRaisesRegex(ServiceError, "INPUT_CHANGED"):
            self.fixture.run(profile=None)
        with self.assertRaisesRegex(ServiceError, "INVALID_RESEARCH_PROFILE"):
            self.fixture.run(profile="unregistered")
        self.assertEqual(len(self.fixture.requests), 2)

    def test_transcript_projection_tampering_rejected_even_with_new_envelope_digest(self):
        self.fixture.mode = "finish"
        self.fixture.run()
        path = self.fixture.study.destination / "research-actions.json"
        record = pipeline._record(path)
        record["transcript"]["decisions"][1]["result"]["text"] = "forged captured text"
        record["transcript"]["transcript_digest"] = digest({k: v for k, v in record["transcript"].items()
                                                           if k != "transcript_digest"})
        pipeline._write(path, pipeline._envelope(record))
        with self.assertRaisesRegex(ServiceError, "ACTION_TRANSCRIPT_INVALID"):
            self.fixture.run()
        self.assertEqual(len(self.fixture.requests), 7)

    def test_action_receipt_before_state_checkpoint_resumes_without_repeating_decision(self):
        original = pipeline._save
        interrupted = False
        def save(directory, state):
            nonlocal interrupted
            if not interrupted and "research_actions" in state:
                interrupted = True
                raise KeyboardInterrupt()
            return original(directory, state)
        with patch.object(pipeline, "_save", side_effect=save), self.assertRaises(KeyboardInterrupt):
            self.fixture.run()
        self.assertEqual(len(self.fixture.requests), 1)
        self.assertTrue((self.fixture.study.destination / "research-actions.json").exists())
        self.assertEqual(self.fixture.run()["outcome"], "abstained")
        self.assertEqual(len(self.fixture.requests), 2)

    def test_failed_critic_retains_actions_and_does_not_retry(self):
        self.fixture.fail_critic = True
        result = self.fixture.run()
        self.assertEqual(result["outcome"], "failed")
        self.assertIn("research_actions", result)
        self.assertEqual(len(self.fixture.requests), 2)
        self.assertEqual(self.fixture.run(), result)
        self.assertEqual(len(self.fixture.requests), 2)

    def test_preexisting_malformed_actions_fail_before_any_model_dispatch(self):
        with patch.object(self.fixture.study.campaign, "research", side_effect=KeyboardInterrupt), \
                self.assertRaises(KeyboardInterrupt):
            self.fixture.run()
        self.assertFalse(self.fixture.requests)
        pipeline._write(self.fixture.study.destination / "research-actions.json",
                        pipeline._envelope({"malformed": True}))
        result = self.fixture.run()
        self.assertEqual(result["outcome"], "failed")
        self.assertEqual(result["detail"]["code"], "PIPELINE_ACTIONS_BINDING_MISMATCH")
        self.assertFalse(self.fixture.requests)
        self.assertEqual(self.fixture.study.campaign.status()["attempted_calls"], 0)

    def test_learning_replays_profile_and_keeps_archive_out_of_critic(self):
        first = self.fixture.run(learning_sources=[])
        self.fixture.another_job("second")
        second = self.fixture.run(job="second", directory=self.fixture.study.parent / "second",
                                  learning_sources=[self.fixture.study.destination])
        self.assertEqual((first["outcome"], second["outcome"]), ("abstained", "abstained"))
        self.assertEqual(second["learning"]["included"], 1)
        decisions = [json.loads(request.prompt) for request in self.fixture.requests
                     if json.loads(request.prompt).get("schema") == "captured-actions-input/v1"]
        self.assertEqual(len(decisions[-1]["prior_research"]["entries"]), 1)
        self.assertEqual(len(self.fixture.requests), 4)


@unittest.skipUnless(SDK_PYTHON, "explicit pinned SDK interpreter required")
class SDKPipelineActionTests(unittest.TestCase):
    def setUp(self):
        self.fixture = ActionFixture(self, sdk=True)

    def test_real_sdk_four_actions_specialist_freeze_and_origin_replay(self):
        self.fixture.mode = "finish"
        first = self.fixture.run()
        self.assertEqual(first["outcome"], "awaiting_dataset", first)
        self.assertEqual(len(self.fixture.wires), 7)
        self.fixture.study.campaign.credential = None
        self.assertEqual(self.fixture.run(), first)
        self.assertEqual(len(self.fixture.wires), 7)

    def test_coherently_rehashed_receipt_reference_is_not_sdk_origin(self):
        self.fixture.run()
        directory = self.fixture.study.destination
        state, result = (pipeline._record(directory / name) for name in ("state.json", "result.json"))
        record = pipeline._record(directory / "research-actions.json")
        record["transcript"]["decisions"][0]["receipt_digest"] = digest("forged reference")
        record["transcript"]["transcript_digest"] = digest({k: v for k, v in record["transcript"].items()
                                                           if k != "transcript_digest"})
        summary = {"profile": PROFILE, "checkpoint_digest": digest(record),
                   "transcript_digest": digest(record["transcript"])}
        state["research_actions"], result["research_actions"] = deepcopy(summary), deepcopy(summary)
        state["result_digest"] = digest(result)
        for name, value in (("research-actions.json", record), ("state.json", state), ("result.json", result)):
            pipeline._write(directory / name, pipeline._envelope(value))
        with self.assertRaisesRegex(ServiceError, "CODEX_ACTION_ORIGIN_MISMATCH"):
            self.fixture.run()
        self.assertEqual(len(self.fixture.wires), 2)

    def test_failed_critic_action_receipts_replay_without_missing_call_dispatch(self):
        self.fixture.fail_critic = True
        first = self.fixture.run()
        self.assertEqual(first["outcome"], "failed")
        self.assertIn("research_actions", first)
        self.assertEqual(len(self.fixture.wires), 2)
        self.assertEqual(self.fixture.run(), first)
        self.assertEqual(len(self.fixture.wires), 2)

    def test_action_receipt_state_gap_uses_existing_sdk_origins(self):
        save, interrupted = pipeline._save, False
        def checkpoint(directory, state):
            nonlocal interrupted
            if not interrupted and "research_actions" in state:
                interrupted = True
                raise KeyboardInterrupt()
            return save(directory, state)
        with patch.object(pipeline, "_save", side_effect=checkpoint), self.assertRaises(KeyboardInterrupt):
            self.fixture.run()
        self.assertEqual(len(self.fixture.wires), 1)
        result = self.fixture.run()
        self.assertEqual(result["outcome"], "abstained", result)
        self.assertEqual(len(self.fixture.wires), 2)


if __name__ == "__main__":
    unittest.main()
