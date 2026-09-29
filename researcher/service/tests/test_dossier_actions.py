"""Private action transcripts are visible, bound, escaped and never authority."""
import json
import unittest
from unittest.mock import patch

from researcher.service import dossier, research_pipeline as pipeline
from researcher.service.contracts import ServiceError, digest
from researcher.service.openai_campaign import PRICING
from researcher.service.providers import ModelResult
from researcher.service.tests import test_research_pipeline as fixtures


class DossierActionTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.PipelineTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.campaign.model_call = self.model
        self.actions = 0
        self.reference = None

    def model(self, request, *, credential):
        data = json.loads(request.prompt)
        if data.get("schema") == "captured-actions-input/v1":
            self.actions += 1
            if self.actions == 1:
                span = data["available_sources"][0]["spans"][0]
                self.reference = {key: span[key] for key in ("evidence_id", "span_id")}
                value = {"action": "read_span", **self.reference}
            elif self.actions == 2:
                value = {"action": "ask_specialist", "specialist": "methods", "question": "What is missing?"}
            else:
                value = {"action": "stop", "reason": "Fixture lacks independent methods evidence."}
        elif data.get("schema") == "captured-specialist-input/v1":
            value = {"analysis": "<script>Untrusted fixture advice</script>",
                     "limitations": ["Synthetic only."], "citations": [self.reference]}
        else:
            return self.fixture.model(request, credential=credential)
        return ModelResult(json.dumps(value), 10, 10, PRICING["model"], "fixture-action", "default")

    def run_pipeline(self):
        result = self.fixture.run_pipeline(research_profile="captured-actions-v1")
        self.assertEqual(result["outcome"], "abstained", result)
        return result

    def test_real_fixture_transcript_shows_actions_and_escaped_advice_without_effects(self):
        result = self.run_pipeline()
        before = self.fixture.campaign.status()
        with patch("socket.socket.connect", side_effect=AssertionError("network")):
            value = dossier.build([self.fixture.destination], [])
        record = value["pipelines"][0]["action_record"]
        self.assertFalse(record["historical_origin_verified"])
        self.assertEqual([row["action"]["action"] for row in record["transcript"]["decisions"]],
                         ["read_span", "ask_specialist", "stop"])
        self.assertEqual(result["research_actions"]["transcript_digest"], digest(record["transcript"]))
        page = dossier.html(value)
        self.assertIn("captured reads and specialist responses", page)
        self.assertIn("&lt;script&gt;", page)
        self.assertNotIn("<script>", page)
        self.assertEqual(self.fixture.campaign.status(), before)

    def test_changed_tool_result_is_refused_even_with_recomputed_outer_checksum(self):
        self.run_pipeline()
        path = self.fixture.destination / "research-actions.json"
        record = pipeline._record(path)
        record["transcript"]["decisions"][0]["result"]["text"] = "invented method"
        pipeline._write(path, pipeline._envelope(record))
        with self.assertRaises(ServiceError):
            dossier.build([self.fixture.destination], [])

    def test_missing_action_checkpoint_is_not_hidden_by_dossier(self):
        self.run_pipeline()
        (self.fixture.destination / "research-actions.json").unlink()
        with self.assertRaises(ServiceError):
            dossier.build([self.fixture.destination], [])

    def test_default_profile_has_no_fabricated_action_history(self):
        self.fixture.campaign.model_call = self.fixture.model
        self.fixture.run_pipeline()
        value = dossier.build([self.fixture.destination], [])
        self.assertIsNone(value["pipelines"][0]["action_record"])

    def test_malformed_options_returns_controlled_binding_error(self):
        self.run_pipeline()
        directory = self.fixture.destination
        inputs = pipeline._record(directory / "input.json")
        state = pipeline._record(directory / "state.json")
        packet = pipeline._record(directory / "packet.json")
        for invalid in (None, [], "untrusted"):
            inputs["options"] = invalid
            state["input_digest"] = digest(inputs)
            packet["input_digest"] = digest({"input": digest(inputs)})
            state["receipts"]["packet"] = digest(packet)
            result = pipeline._result(state, state["outcome"])
            state["result_digest"] = digest(result)
            for name, record in (("input", inputs), ("state", state), ("packet", packet), ("result", result)):
                pipeline._write(directory / (name + ".json"), pipeline._envelope(record))
            with self.subTest(invalid=invalid), self.assertRaisesRegex(ServiceError, "DOSSIER_BINDING"):
                dossier.build([directory], [])


if __name__ == "__main__":
    unittest.main()
