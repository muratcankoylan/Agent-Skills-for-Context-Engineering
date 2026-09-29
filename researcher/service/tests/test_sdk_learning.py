"""Cross-day fixture evidence, not research-quality or elapsed-uptime claims."""

from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from researcher.scripts.source_connectors import TransportResponse
from researcher.service import research_pipeline as pipeline, sdk_learning as learning, retrieval_sources
from researcher.service.agents_evals import fixture_dataset
from researcher.service.contracts import ServiceError, digest
from researcher.service.primary_context import verify_primary
from researcher.service.tests import test_research_pipeline as fixtures
from researcher.service.tests.test_daily_retrieval import DAY, ROOT
from researcher.service.tests.test_primary_context import fixture_reader
from researcher.service.tests.test_retrieval_handoff import FEED
from researcher.service.workflow import Workflow, make_manifest


class LearningTests(unittest.TestCase):
    def setUp(self):
        self.clock = DAY + 3600
        timer = patch("researcher.service.store.time.time", side_effect=lambda: self.clock)
        timer.start()
        self.addCleanup(timer.stop)
        self.study = fixtures.PipelineTests()
        self.study.setUp()
        self.addCleanup(self.study.doCleanups)
        self.sources = []
        self.day = 0

    def next_day(self, *, previous=None, dataset=None, seed=1):
        study = self.study
        job = "daily" if self.day == 0 else "day-" + str(self.day)
        end = DAY + self.day * 86400
        self.clock = end + 3600
        if self.day:
            f = study.fixture
            f.feed_transport.steps.append(TransportResponse(200, (("Content-Type", "application/xml"),), FEED))
            f.store.enqueue(job, make_manifest(ROOT, f.config, f.config["schedules"][0],
                                              fixture=True, window_end=end))
            workflow = Workflow(f.store, ROOT, retrieval_source=f.collect, retrieval_verify=retrieval_sources.verify,
                primary_reader=fixture_reader(f.article_transport), primary_replayer=verify_primary)
            with patch("researcher.service.store.time.time", return_value=end + 3600):
                self.assertNotIn("error", workflow.drain()[0])
        destination = study.parent / ("study-" + str(self.day))
        sources = list(reversed(self.sources)) if previous is None else previous
        result = pipeline.run_pipeline(ROOT, study.fixture.store, job, destination,
            campaign=study.campaign, skills=["context-fundamentals"], dataset=dataset,
            fixture=True, now=end + 3600, seed=seed, replications=1, learning_sources=sources)
        self.sources.append(destination)
        self.day += 1
        return result

    def test_later_day_gets_only_researcher_memory_and_replay_is_call_free(self):
        self.assertEqual(self.next_day()["outcome"], "abstained")
        second = self.next_day()
        self.assertEqual(second["learning"]["included"], 1)
        self.assertEqual(len(self.study.calls), 4)
        researcher, critic = self.study.calls[-2:]
        self.assertIn("Revisit a prior hypothesis or abstention", researcher.system)
        self.assertIn("State what changed", researcher.system)
        self.assertNotIn("prior hypothesis or abstention", critic.system)
        archive = json.loads(researcher.prompt)["prior_research"]
        self.assertEqual(archive["entries"][0]["hypothesis"], "Test evidence preservation.")
        self.assertNotIn("prior_research", json.loads(critic.prompt))
        self.assertNotIn(str(self.study.parent), json.dumps(archive))
        self.assertNotIn("gold", json.dumps(archive))
        again = pipeline.run_pipeline(ROOT, self.study.fixture.store, "day-1", self.sources[1],
            campaign=self.study.campaign, skills=["context-fundamentals"], fixture=True,
            now=DAY + 86400 + 3600, replications=1, learning_sources=[self.sources[0]])
        self.assertEqual(again, second)
        self.assertEqual(len(self.study.calls), 4)

    def test_exact_frozen_duplicate_stops_second_evaluation_and_editor_is_isolated(self):
        self.study.abstain = False
        first = self.next_day(dataset=fixture_dataset())
        second = self.next_day(dataset=fixture_dataset())
        self.assertEqual(first["outcome"], "evaluated_not_accepted", first)
        self.assertEqual(second["outcome"], "duplicate_candidate", second)
        self.assertEqual(len(self.study.calls), 18)  # 3 + 12, then 3 and zero evals.
        self.assertEqual(second["detail"]["source_result_digest"], digest(first))
        self.assertFalse((self.sources[1] / "evaluation.json").exists())
        for request in self.study.calls:
            if "Form one falsifiable" not in request.system:
                self.assertNotIn("prior_research", json.loads(request.prompt))
                self.assertNotIn('"gold"', request.prompt)
        self.assertEqual(pipeline._record(self.sources[1] / "candidate.json")["output"]["freeze_receipt"]["file_count"], 1)
        review = pipeline._record(self.sources[0] / "candidate.json")["output"]
        frozen = self.sources[0] / "candidate-review/frozen" / review["candidate"]["declared_changed_surfaces"][0]
        frozen.write_bytes(frozen.read_bytes() + b"\nTampered.\n")
        with self.assertRaisesRegex(ServiceError, "FROZEN_CANDIDATE_CHANGED"):
            pipeline.run_pipeline(ROOT, self.study.fixture.store, "day-1", self.sources[1],
                campaign=self.study.campaign, skills=["context-fundamentals"], dataset=fixture_dataset(),
                fixture=True, now=DAY + 86400 + 3600, replications=1, learning_sources=self.sources[:1])
        self.assertEqual(len(self.study.calls), 18)

    def test_previously_unevaluated_candidate_does_not_block_first_evaluation(self):
        self.study.abstain = False
        first = self.next_day()
        second = self.next_day(dataset=fixture_dataset())
        self.assertEqual(first["outcome"], "awaiting_dataset", first)
        self.assertEqual(second["outcome"], "evaluated_not_accepted", second)
        self.assertEqual(len(self.study.calls), 18)
        self.assertTrue((self.sources[1] / "evaluation.json").exists())

    def test_changed_evaluation_seed_runs_a_new_independent_plan(self):
        self.study.abstain = False
        first = self.next_day(dataset=fixture_dataset())
        second = self.next_day(dataset=fixture_dataset(), seed=2)
        self.assertEqual(first["outcome"], "evaluated_not_accepted", first)
        self.assertEqual(second["outcome"], "evaluated_not_accepted", second)
        self.assertEqual(len(self.study.calls), 30)
        plans = [pipeline._record(path / "candidate.json")["output"]["evaluation_plan_digest"] for path in self.sources]
        self.assertNotEqual(*plans)

    def test_prior_receipt_corruption_fails_before_new_model_work(self):
        self.next_day()
        path = self.sources[0] / "research.json"
        value = pipeline._read(path)
        value["record"]["output"]["research"]["hypothesis"] = "forged"
        pipeline._write(path, value)
        result = self.next_day()
        self.assertEqual(result["outcome"], "failed")
        self.assertEqual(result["detail"]["code"], "PIPELINE_RECEIPT_DIGEST_MISMATCH")
        self.assertEqual(len(self.study.calls), 2)

    def test_changed_baseline_and_corpus_are_omitted_not_reused(self):
        self.next_day()
        self.next_day()
        packet = pipeline._record(self.sources[1] / "packet.json")["output"]
        baseline = packet["baseline_commit"]
        packet["baseline_commit"] = "a" * 40
        value = learning.build(ROOT, self.study.fixture.store, self.study.campaign, packet,
                               "day-1", self.sources[:1])
        self.assertEqual(value["archive"]["omissions"]["incompatible"], 1)
        self.assertEqual(value["archive"]["entries"], [])
        self.assertEqual(value["candidates"], [])
        packet["baseline_commit"] = baseline
        packet["corpus"]["documents"][0]["text"] += "\nDifferent baseline bytes.\n"
        value = learning.build(ROOT, self.study.fixture.store, self.study.campaign, packet,
                               "day-1", self.sources[:1])
        self.assertEqual(value["archive"]["omissions"]["incompatible"], 1)

    def test_archive_selection_is_immutable_on_resume(self):
        self.next_day()
        self.next_day()
        with self.assertRaisesRegex(ServiceError, "INPUT_CHANGED"):
            pipeline.run_pipeline(ROOT, self.study.fixture.store, "day-1", self.sources[1],
                campaign=self.study.campaign, skills=["context-fundamentals"], fixture=True,
                now=DAY + 86400 + 3600, replications=1, learning_sources=[])
        self.assertEqual(len(self.study.calls), 4)

    def test_archive_has_closed_fields_and_byte_bound(self):
        self.next_day()
        self.next_day()
        archive = pipeline._record(self.sources[1] / "learning.json")["archive"]
        for key in ("gold", "scores", "critic", "answers", "raw_trace"):
            bad = deepcopy(archive)
            bad["entries"][0][key] = "not permitted"
            with self.assertRaisesRegex(ServiceError, "LEARNING_INVALID_ARCHIVE"):
                learning.validate_archive(bad)
        bad = deepcopy(archive)
        bad["entries"][0]["hypothesis"] = "é" * 16384
        with self.assertRaises(ServiceError):
            learning.validate_archive(bad)

    def test_entry_omissions_are_explicit_and_candidate_scan_remains_separate(self):
        for _ in range(7):
            result = self.next_day()
        self.assertEqual(result["learning"]["included"], 5)
        self.assertEqual(result["learning"]["omissions"]["entry_limit"], 1)
        self.assertLessEqual(len(json.dumps(pipeline._record(self.sources[-1] / "learning.json")["archive"]).encode()), 32768)

    def test_paths_duplicate_alias_and_current_study_fail_closed(self):
        self.next_day()
        source = self.sources[0]
        with self.assertRaises(ServiceError):
            learning.source_paths([source, source])
        with self.assertRaises(ServiceError):
            learning.source_paths([source], current=source)
        alias = self.study.parent / "alias"
        alias.symlink_to(source, target_is_directory=True)
        with self.assertRaises(ServiceError):
            learning.source_paths([alias])
        with self.assertRaises(ServiceError):
            learning.source_paths([source] * 33)

    def test_recomputed_learning_hash_cannot_change_checkpoint(self):
        self.next_day()
        self.next_day()
        path = self.sources[1] / "learning.json"
        record = pipeline._record(path)
        record["archive"]["entries"][0]["hypothesis"] = "Forged memory."
        pipeline._write(path, pipeline._envelope(record))
        with self.assertRaisesRegex(ServiceError, "PIPELINE_LEARNING_CHANGED"):
            pipeline.run_pipeline(ROOT, self.study.fixture.store, "day-1", self.sources[1],
                campaign=self.study.campaign, skills=["context-fundamentals"], fixture=True,
                now=DAY + 86400 + 3600, replications=1, learning_sources=self.sources[:1])
        self.assertEqual(len(self.study.calls), 4)

    def test_source_capture_mutation_is_not_accepted_as_memory(self):
        self.next_day()
        self.next_day()
        packet = pipeline._record(self.sources[1] / "packet.json")["output"]
        self.study.fixture.mutate_step("report", lambda value: value.update(evidence_qualified=True), update_digest=True)
        with self.assertRaises(ServiceError):
            learning.build(ROOT, self.study.fixture.store, self.study.campaign, packet, "day-1", self.sources[:1])
        self.assertEqual(len(self.study.calls), 4)

    def test_exact_identity_requires_baseline_corpus_path_and_bytes(self):
        identity = {"baseline_commit": "a" * 40, "corpus_digest": digest("corpus"),
                    "path": "skills/evaluation/SKILL.md", "text_sha256": digest("text")}
        checkpoint = {"candidates": [{**identity, "source_result_digest": digest("source")}]}
        self.assertIsNone(learning.duplicate(checkpoint, identity))
        for key in identity:
            different = {**identity, key: "different"}
            self.assertIsNone(learning.duplicate(checkpoint, different, evaluation_plan_digest=digest("plan")))
        self.assertIsNone(learning.duplicate(checkpoint, identity, evaluation_plan_digest=digest("plan")))
        checkpoint["candidates"][0]["evaluation_plan_digest"] = digest("plan")
        self.assertIsNotNone(learning.duplicate(checkpoint, identity, evaluation_plan_digest=digest("plan")))
        self.assertIsNone(learning.duplicate(checkpoint, identity, evaluation_plan_digest=digest("different plan")))

    def test_byte_limit_reports_whole_entry_omission(self):
        self.next_day()
        self.next_day()
        packet = pipeline._record(self.sources[1] / "packet.json")["output"]
        with patch.object(learning, "MAX_ARCHIVE_BYTES", 500):
            record = learning.build(ROOT, self.study.fixture.store, self.study.campaign,
                                    packet, "day-1", self.sources[:1], source_limit_omissions=4)
        self.assertEqual(record["archive"]["entries"], [])
        self.assertEqual(record["archive"]["omissions"]["byte_limit"], 1)
        self.assertEqual(record["archive"]["omissions"]["source_limit"], 4)


def run_multiday_scenario(destination: Path, sdk_python: str) -> dict:
    """Retain actual Organization + SDK/local-provider 3-day fixture receipts.

    Explicit fresh destination only. Creates a synthetic authority, never opens
    a real one or calls a provider. No environment/key lookup. Dates are simulated.
    """
    from researcher.service.codex_campaign import CodexCampaign
    from researcher.service.organization import Organization
    from researcher.service.openai_campaign import initialize
    from researcher.service.providers import ModelRequest
    from researcher.service.store import Store
    from researcher.service.tests.test_codex_campaign import upstream
    from researcher.service.tests.test_organization import policy
    from researcher.service.tests.test_daily_retrieval import config
    from researcher.service.tests.test_primary_context import Transport
    from researcher.scripts.tests.test_source_connectors import ScriptedTransport
    destination = destination.absolute()
    pipeline._directory(destination.parent, private=True)
    destination.mkdir(mode=0o700, exist_ok=False)
    configuration = config()
    configuration["schedules"][0].update(query="context engineering", primary_read_limit=1)
    clock = [DAY + 3600]
    source = Store(destination / "source", configuration, initialize=True)
    initialize(destination / "authority", cap_microusd=100_000_000, prior_spend_microusd=0)
    answers = fixtures.PipelineTests()
    answers.calls, answers.abstain, answers.bad_grounding = [], False, False
    wires = []
    def transport(body, **_options):
        data = json.loads(body)
        wires.append(data)
        if data["tools"]:
            raise AssertionError("fixture unexpectedly advertised tools")
        system, prompt = data["input"][0]["content"][0]["text"].split("\n\nTask input (untrusted data):\n", 1)
        result = answers.model(ModelRequest("openai", data["model"], system, prompt, data["max_output_tokens"]),
                               credential="synthetic-fixture-credential")
        return upstream(result.text)
    campaign = CodexCampaign(destination / "authority", sdk_python=sdk_python,
        credential="synthetic-fixture-credential", transport=transport, now=lambda: clock[0], progress=lambda _: None)
    adapter = retrieval_sources._adapter
    source_requests = []
    def collect(*args, **kwargs):
        source_requests.append(1)
        transport = ScriptedTransport(TransportResponse(200, (("Content-Type", "application/xml"),), FEED))
        def use(name, start, end, credential=None, **options):
            return adapter(name, start, end, credential, transport=transport,
                           resolver=lambda *_: ("93.184.216.34",), **options)
        with patch.object(retrieval_sources, "_adapter", side_effect=use):
            return retrieval_sources.collect(*args, **kwargs)
    primary = Transport()
    workflow = Workflow(source, ROOT, retrieval_source=collect, retrieval_verify=retrieval_sources.verify,
        primary_reader=fixture_reader(primary), primary_replayer=verify_primary)
    kwargs = {"policy": policy(), "dataset": fixture_dataset(), "fixture": True}
    Organization.initialize(destination / "organization", ROOT, source, campaign, **kwargs)
    days = []
    with patch("researcher.service.store.time.time", side_effect=lambda: clock[0]):
        for day in range(3):
            clock[0] = DAY + day * 86400 + 3600
            answers.abstain = day == 2
            before = len(wires)
            organization = Organization(destination / "organization", ROOT, source, campaign, **kwargs)
            cycle = organization.cycle(workflow, now=clock[0])
            index = organization._load()
            key = next(k for k, row in index["jobs"].items() if digest(row["job"]) == cycle["job"]["job_digest"])
            directory = destination / "organization/jobs" / key / "pipeline"
            result = pipeline._record(directory / "result.json")
            research = pipeline._record(directory / "research.json")["output"]
            replay = organization.cycle(workflow, now=clock[0])
            if replay["research_admissions"] != 0:
                raise AssertionError("terminal study redispatched")
            days.append({"day": day + 1, "simulated_utc_epoch": clock[0], "cycle": cycle,
                "result": result, "research": research, "model_calls": len(wires) - before,
                "replay_admissions": replay["research_admissions"], "pipeline_path": str(directory),
                "evaluation_present": (directory / "evaluation.json").exists()})
    result = {"schema": "sdk-learning-scenario/v1", "fixture": True,
        "provider_calls": 0, "scientific_effectiveness_measured": False, "elapsed_days_measured": False,
        "runtime": campaign.execution_identity(), "days": days, "sdk_provider_fixture_calls": len(wires),
        "source_fixture_requests": len(source_requests), "primary_fixture_requests": primary.calls,
        "budget": campaign.status()}
    pipeline._write(destination / "scenario.json", pipeline._envelope(result))
    return result


@unittest.skipUnless(os.environ.get("CODEX_WORKER_TEST_PYTHON"), "explicit pinned SDK interpreter required")
class SDKLearningTests(unittest.TestCase):
    def test_three_day_sdk_organization_dossier(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = run_multiday_scenario(Path(temporary).resolve() / "scenario",
                                          os.environ["CODEX_WORKER_TEST_PYTHON"])
            self.assertEqual([day["result"]["outcome"] for day in result["days"]],
                ["evaluated_not_accepted", "duplicate_candidate", "abstained"])
            self.assertEqual([day["model_calls"] for day in result["days"]], [15, 3, 2])
            self.assertEqual([day["result"]["learning"]["included"] for day in result["days"]], [0, 1, 2])
            self.assertEqual([day["replay_admissions"] for day in result["days"]], [0, 0, 0])
            self.assertEqual(result["provider_calls"], 0)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario-dir", type=Path)
    parser.add_argument("--sdk-python")
    args, rest = parser.parse_known_args()
    if args.scenario_dir is not None:
        if not args.sdk_python:
            parser.error("--sdk-python is required; no ambient SDK selection")
        print(json.dumps(run_multiday_scenario(args.scenario_dir, args.sdk_python), sort_keys=True))
    else:
        unittest.main(argv=[__file__, *rest])
