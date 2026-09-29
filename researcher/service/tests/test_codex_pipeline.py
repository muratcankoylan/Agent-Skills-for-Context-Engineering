"""Real pinned SDK across captured sources, three roles, freeze and fresh evals.

Answers/sources are explicitly synthetic. The real SDK controls every thread;
injected upstream streams test execution/provenance, not research effectiveness.
"""
import json
import os
import unittest

from researcher.service.codex_campaign import CodexCampaign
from researcher.service.providers import ModelRequest
from researcher.service.tests.test_codex_campaign import upstream
from researcher.service.tests import test_research_pipeline as fixtures
from researcher.service.agents_evals import fixture_dataset
from researcher.service import research_pipeline as pipeline

SDK_PYTHON = os.environ.get("CODEX_WORKER_TEST_PYTHON")


@unittest.skipUnless(SDK_PYTHON, "explicit pinned SDK interpreter required")
class SDKPipelineTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.PipelineTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        original = self.fixture.campaign
        self.wires = []
        def transport(body, **_options):
            data = json.loads(body)
            self.wires.append(data)
            self.assertEqual(data["tools"], [])
            self.assertNotIn("client_metadata", data)
            system, prompt = data["input"][0]["content"][0]["text"].split("\n\nTask input (untrusted data):\n", 1)
            request = ModelRequest("openai", data["model"], system, prompt, data["max_output_tokens"])
            output = self.fixture.model(request, credential="synthetic-fixture-credential")
            return upstream(output.text)
        self.fixture.campaign = CodexCampaign(original.directory, sdk_python=SDK_PYTHON,
            credential=original.credential, transport=transport, progress=lambda _: None, now=original.now)

    def test_abstention_origin_and_replay(self):
        result = self.fixture.run_pipeline()
        self.assertEqual(result["outcome"], "abstained", result)
        self.assertEqual(result["execution_backend"], "codex_sdk")
        self.assertEqual(len(self.wires), 2)
        self.fixture.campaign.credential = None
        self.assertEqual(self.fixture.run_pipeline(), result)
        self.assertEqual(len(self.wires), 2)

    def test_roles_freeze_and_twelve_independent_sdk_eval_threads(self):
        self.fixture.abstain = False
        result = self.fixture.run_pipeline(dataset=fixture_dataset())
        self.assertEqual(result["outcome"], "evaluated_not_accepted", result)
        self.assertEqual(result["execution_backend"], "codex_sdk")
        self.assertEqual(len(self.wires), 15)
        record = pipeline._record(self.fixture.destination / "evaluation.json")["output"]
        self.assertEqual(record["backend"], "codex_sdk")
        self.assertTrue(record["fixture"])
        self.assertEqual(len(record["origins"]), 12)
        threads = {item["session_id"] for item in record["results"]}
        self.assertEqual(len(threads), 12)
        for item in record["results"]:
            proof = record["origins"][item["item_id"]]
            self.assertEqual(proof["result_digest"], item["result_digest"])
            self.assertEqual(proof["receipt"]["sdk"]["thread_id"], item["session_id"])
        self.fixture.campaign.credential = None
        self.assertEqual(self.fixture.run_pipeline(dataset=fixture_dataset()), result)
        self.assertEqual(len(self.wires), 15)
        self.assertFalse(result["scientific_improvement_demonstrated"])


if __name__ == "__main__":
    unittest.main()
