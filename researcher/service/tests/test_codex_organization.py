"""Actual coordinator -> captured sources -> pinned SDK -> durable pipeline.

Only the upstream answers and external sources are synthetic. No pipeline,
worker, SDK thread, or result-recovery adapter is substituted. These are wiring
and restart proofs, not evidence of research quality or production throughput.
"""

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from researcher.scripts.source_connectors import TransportResponse
from researcher.scripts.tests.test_source_connectors import ScriptedTransport
from researcher.service import organization, research_pipeline, retrieval_sources
from researcher.service.agents_evals import fixture_dataset
from researcher.service.codex_campaign import CodexCampaign
from researcher.service.codex_worker import SDK_VERSION
from researcher.service.contracts import digest, load_config
from researcher.service.openai_campaign import initialize
from researcher.service.primary_context import verify_primary
from researcher.service.providers import ModelRequest
from researcher.service.store import Store
from researcher.service.tests import test_research_pipeline as fixtures
from researcher.service.tests.test_codex_campaign import upstream
from researcher.service.tests.test_daily_retrieval import DAY, ROOT, config
from researcher.service.tests.test_organization import policy
from researcher.service.tests.test_primary_context import Transport, fixture_reader
from researcher.service.tests.test_retrieval_handoff import FEED
from researcher.service.workflow import Workflow, make_manifest

SDK_PYTHON = os.environ.get("CODEX_WORKER_TEST_PYTHON")


@unittest.skipUnless(SDK_PYTHON, "explicit pinned SDK interpreter required")
class SDKOrganizationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name).resolve()
        self.clock = DAY + 3600
        timer = patch("researcher.service.store.time.time", side_effect=lambda: self.clock)
        timer.start()
        self.addCleanup(timer.stop)
        self.config = config()
        self.config["schedules"][0].update(query="context engineering", primary_read_limit=1)
        self.config = load_config(json.dumps(self.config))
        self.source = Store(self.directory / "source", self.config, initialize=True)
        self.authority = self.directory / "authority"
        initialize(self.authority, cap_microusd=100_000_000, prior_spend_microusd=0)
        self.destination = self.directory / "organization"
        self.dataset = None
        self.wires = []
        self.source_calls = 0
        self.primary_transport = Transport()
        # Reuse only the deterministic answer generator, never its setUp or its
        # socket patch. The SDK connects to the real local gateway subprocess.
        self.answers = fixtures.PipelineTests()
        self.answers.calls = []
        self.answers.abstain = True
        self.answers.bad_grounding = False
        self.campaign = self.new_campaign(credential="synthetic-fixture-credential")
        self.workflow = self.new_workflow()

    def forbidden(self, *_args, **_kwargs):
        self.fail("retrieval attempted a credential or legacy model effect")

    def transport(self, body, **_options):
        data = json.loads(body)
        self.wires.append(data)
        self.assertEqual(data["tools"], [])
        self.assertEqual(data["tool_choice"], "none")
        self.assertNotIn("client_metadata", data)
        self.assertNotIn("prompt_cache_key", data)
        system, prompt = data["input"][0]["content"][0]["text"].split(
            "\n\nTask input (untrusted data):\n", 1)
        request = ModelRequest("openai", data["model"], system, prompt, data["max_output_tokens"])
        answer = self.answers.model(request, credential="synthetic-fixture-credential")
        return upstream(answer.text)

    def new_campaign(self, *, credential=None):
        return CodexCampaign(self.authority, sdk_python=SDK_PYTHON, credential=credential,
            transport=self.transport, progress=lambda _: None, now=lambda: self.clock)

    def collect(self, *args, **kwargs):
        self.source_calls += 1
        original = retrieval_sources._adapter
        transport = ScriptedTransport(TransportResponse(200,
            (("Content-Type", "application/xml"),), FEED))

        def adapter(name, start, end, credential=None, **options):
            return original(name, start, end, credential, transport=transport,
                resolver=lambda *_args: ("93.184.216.34",), **options)

        with patch.object(retrieval_sources, "_adapter", side_effect=adapter):
            return retrieval_sources.collect(*args, **kwargs)

    def new_workflow(self):
        return Workflow(self.source, ROOT, retrieval_source=self.collect,
            retrieval_verify=retrieval_sources.verify,
            primary_reader=fixture_reader(self.primary_transport), primary_replayer=verify_primary,
            model=self.forbidden, credential=self.forbidden)

    def coordinator(self, *, create=False):
        constructor = organization.Organization.initialize if create else organization.Organization
        return constructor(self.destination, ROOT, self.source, self.campaign,
            policy=policy(), dataset=self.dataset, fixture=True)

    def reopen(self):
        # New objects read the existing authorities. No credential is available
        # for recovery and no authority or source state is reinitialized.
        self.source = Store(self.directory / "source", self.config)
        self.campaign = self.new_campaign()
        self.workflow = self.new_workflow()
        return self.coordinator()

    def manual(self):
        job = "reviewed-manual-sdk-job"
        self.source.enqueue(job, make_manifest(ROOT, self.config,
            self.config["schedules"][0], fixture=True, window_end=DAY))
        self.assertNotIn("error", self.workflow.drain()[0])
        return job

    def assert_sdk_origins(self, count):
        status = self.campaign.status()
        self.assertEqual(status["attempted_calls"], count)
        self.assertEqual(status["completed_calls"], count)
        self.assertEqual(status["sdk"]["completed_turns"], count)
        self.assertEqual(status["sdk"]["unresolved_turns"], 0)
        self.assertEqual(len(self.wires), count)
        self.assertEqual(len(self.answers.calls), count)
        with self.campaign.store._history_snapshot() as database:
            rows = database.execute(
                "SELECT output,output_digest FROM steps WHERE name='sdk-result'").fetchall()
            receipts = [self.campaign.store._history_value(
                row["output"], row["output_digest"], 2_000_000) for row in rows]
        self.assertEqual(len(receipts), count)
        self.assertEqual(len({receipt["sdk"]["thread_id"] for receipt in receipts}), count)
        for receipt in receipts:
            self.assertEqual(receipt["backend"], "codex_sdk")
            self.assertEqual(receipt["sdk"]["version"], SDK_VERSION)
            self.assertTrue(receipt["sdk"]["thread_id"])
            self.assertTrue(receipt["sdk"]["turn_id"])
            self.assertEqual(receipt["output_digest"], digest(receipt["response"]["text"]))

    def test_scheduled_serve_and_fresh_object_restart_do_not_duplicate_sdk_turns(self):
        coordinator = self.coordinator(create=True)
        summaries = []
        served = coordinator.serve(self.workflow, max_cycles=1,
            progress=summaries.append, clock=lambda: self.clock)
        self.assertEqual(served["cycles"], 1)
        first = summaries[0]
        self.assertEqual(tuple(first[key] for key in (
            "source_admissions", "source_executions", "research_admissions")), (1, 1, 1))
        self.assertEqual(first["job"]["outcome"], "abstained")
        job = self.config["schedules"][0]["id"] + ":" + str(DAY)
        self.assertEqual(first["job"]["job_digest"], digest(job))
        self.assertEqual(self.source.inspect(job)["job"]["status"], "retrieval_complete")
        self.assert_sdk_origins(2)
        budget_before = self.campaign.status()
        sources_before = self.source.status()["usage"]
        reopened = self.reopen()
        summaries.clear()
        reopened.serve(self.workflow, max_cycles=1,
            progress=summaries.append, clock=lambda: self.clock)
        self.assertEqual(tuple(summaries[0][key] for key in (
            "source_admissions", "source_executions", "research_admissions")), (0, 0, 0))
        self.assertEqual(self.source_calls, 1)
        self.assertEqual(self.source.status()["usage"], sources_before)
        self.assertEqual(self.campaign.status(), budget_before)
        self.assertEqual(reopened.status()["outcomes"], {"abstained": 1})
        self.assert_sdk_origins(2)

    def test_manual_candidate_and_evals_recover_receipt_index_gap_without_sdk_calls(self):
        self.answers.abstain = False
        self.dataset = fixture_dataset()
        job = self.manual()
        coordinator = self.coordinator(create=True)
        save = coordinator._save

        def interrupt_terminal_save(index):
            if any(row["phase"] == "terminal" for row in index["jobs"].values()):
                raise OSError("synthetic index publication failure")
            save(index)

        with patch.object(coordinator, "_save", side_effect=interrupt_terminal_save):
            with self.assertRaises(OSError):
                coordinator.cycle(self.workflow, now=self.clock)
        self.assert_sdk_origins(15)
        children = list((self.destination / "jobs").iterdir())
        self.assertEqual(len(children), 1)
        pipeline_directory = children[0] / "pipeline"
        result = research_pipeline._record(pipeline_directory / "result.json")
        self.assertEqual(result["outcome"], "evaluated_not_accepted", result)
        self.assertEqual(result["execution_backend"], "codex_sdk")
        self.assertFalse(result["production_ready"])
        self.assertFalse(result["scientific_improvement_demonstrated"])
        self.assertEqual(result["publication"], "not_attempted")
        candidate = research_pipeline._record(pipeline_directory / "candidate.json")["output"]
        self.assertTrue(candidate["structural_checks_passed"])
        self.assertEqual(candidate["freeze_receipt"]["file_count"], 1)
        evaluation = research_pipeline._record(pipeline_directory / "evaluation.json")["output"]
        self.assertEqual(evaluation["backend"], "codex_sdk")
        self.assertEqual(len(evaluation["origins"]), 12)
        self.assertEqual(len({row["session_id"] for row in evaluation["results"]}), 12)
        before = self.campaign.status()
        reopened = self.reopen()
        recovered = reopened.cycle(self.workflow, now=self.clock)
        self.assertEqual(tuple(recovered[key] for key in (
            "source_admissions", "source_executions", "research_admissions")), (0, 0, 1))
        self.assertEqual(recovered["job"]["job_digest"], digest(job))
        self.assertEqual(recovered["job"]["pipeline_result_digest"], digest(result))
        self.assertEqual(recovered["job"]["outcome"], "evaluated_not_accepted")
        self.assertEqual(self.source_calls, 1)
        self.assertEqual(self.campaign.status(), before)
        self.assertEqual(reopened.status()["outcomes"], {"evaluated_not_accepted": 1})
        self.assert_sdk_origins(15)

    def test_source_pause_independently_blocks_discovery_and_completed_source_dispatch(self):
        coordinator = self.coordinator(create=True)
        self.assertFalse(self.campaign.store.status()["paused"])
        self.source.pause(True)
        paused = coordinator.cycle(self.workflow, now=self.clock)
        self.assertTrue(paused["paused"])
        self.assertEqual(paused["source_admissions"], 0)
        self.assertEqual(paused["research_admissions"], 0)
        self.assertEqual(self.source_calls, 0)
        self.assert_sdk_origins(0)
        self.source.pause(False)
        job = self.manual()
        self.source.pause(True)
        paused = coordinator.cycle(self.workflow, now=self.clock)
        self.assertTrue(paused["paused"])
        self.assertIsNone(paused["job"])
        self.assertEqual(paused["research_admissions"], 0)
        self.assertFalse(self.campaign.store.status()["paused"])
        self.assert_sdk_origins(0)
        self.source.pause(False)
        completed = coordinator.cycle(self.workflow, now=self.clock)
        self.assertEqual(completed["source_admissions"], 0)
        self.assertEqual(completed["source_executions"], 0)
        self.assertEqual(completed["job"]["job_digest"], digest(job))
        self.assertEqual(completed["job"]["outcome"], "abstained")
        self.assertEqual(self.source_calls, 1)
        self.assert_sdk_origins(2)


if __name__ == "__main__":
    unittest.main()
