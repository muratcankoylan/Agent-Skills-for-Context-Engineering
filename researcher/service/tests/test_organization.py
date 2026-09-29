"""Coordinator fixtures use actual Stores, source capture/replay and no network."""

from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from researcher.scripts.source_connectors import TransportResponse
from researcher.scripts.tests.test_source_connectors import ScriptedTransport
from researcher.service import organization as module, research_pipeline as pipeline, retrieval_sources
from researcher.service.contracts import ServiceError, digest, load_config
from researcher.service.openai_campaign import Campaign, initialize
from researcher.service.primary_context import verify_primary
from researcher.service.retrieval_handoff import verified_bundle
from researcher.service.store import Store
from researcher.service.tests.test_daily_retrieval import DAY, ROOT, config
from researcher.service.tests.test_primary_context import Transport, fixture_reader
from researcher.service.tests.test_retrieval_handoff import FEED
from researcher.service.workflow import Workflow, make_manifest


def policy():
    return {"schema": "research-organization-policy/v1",
        "schedules": [{"schedule_id": config()["schedules"][0]["id"], "skills": ["context-fundamentals"]}],
        "poll_seconds": 5, "max_source_jobs_per_cycle": 1, "maximum_age_seconds": 172800,
        "evaluation": {"seed": 1, "replications": 1, "max_sessions": 144}}


class OrganizationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name).resolve()
        self.clock = DAY + 3600
        timer = patch("researcher.service.store.time.time", side_effect=lambda: self.clock)
        timer.start()
        self.addCleanup(timer.stop)
        network = patch("socket.socket.connect", side_effect=AssertionError("network forbidden"))
        network.start()
        self.addCleanup(network.stop)
        self.config = config()
        self.config["schedules"][0].update(query="context engineering", primary_read_limit=1)
        self.config = load_config(json.dumps(self.config))
        self.source = Store(self.directory / "source", self.config, initialize=True)
        self.authority = self.directory / "authority"
        initialize(self.authority, cap_microusd=100000000, prior_spend_microusd=0)
        self.campaign = Campaign(self.authority, model_call=self.forbidden, progress=lambda _: None,
                                 now=lambda: self.clock)
        self.policy = policy()
        self.destination = self.directory / "organization"
        self.sources, self.pipeline_calls = 0, []
        self.outcome = "abstained"
        self.primary_transport = Transport()
        self.workflow = Workflow(self.source, ROOT, retrieval_source=self.collect,
            retrieval_verify=retrieval_sources.verify,
            primary_reader=fixture_reader(self.primary_transport), primary_replayer=verify_primary,
            model=self.forbidden, credential=self.forbidden)

    def forbidden(self, *args, **kwargs):
        self.fail("fixture attempted a credential or model effect")

    def collect(self, *args, **kwargs):
        self.sources += 1
        original = retrieval_sources._adapter
        transport = ScriptedTransport(TransportResponse(200, (("Content-Type", "application/xml"),), FEED))
        def adapter(name, start, end, credential=None, **options):
            return original(name, start, end, credential, transport=transport,
                            resolver=lambda *a: ("93.184.216.34",), **options)
        with patch.object(retrieval_sources, "_adapter", side_effect=adapter):
            return retrieval_sources.collect(*args, **kwargs)

    def initialize(self, **kwargs):
        return module.Organization.initialize(self.destination, ROOT, self.source, self.campaign,
            policy=self.policy, fixture=True, **kwargs)

    def reopen(self, **kwargs):
        return module.Organization(self.destination, ROOT, self.source, self.campaign,
            policy=self.policy, fixture=True, **kwargs)

    def fake_pipeline(self, root, source, job, directory, **kwargs):
        self.pipeline_calls.append((job, kwargs))
        # This explicit fixture adapter still exercises actual discovery/primary
        # capture verification before emitting a clearly fixture-only outcome.
        verified_bundle(source, job, now=self.clock, fixture=True)
        directory.mkdir(mode=0o700)
        result = {"schema": "research-pipeline-result/v1", "authority": "none",
            "production_ready": False, "scientific_improvement_demonstrated": False,
            "outcome": self.outcome, "publication": "not_attempted", "fixture": True,
            "detail": {"code": "FIXTURE_REJECTION"} if self.outcome == "failed" else None}
        pipeline._write(directory / "result.json", pipeline._envelope(result))
        return result

    def cycle(self, organization, **kwargs):
        return organization.cycle(self.workflow, now=self.clock, pipeline_runner=self.fake_pipeline, **kwargs)

    def manual(self, name="reviewed-manual-job", *, end=DAY):
        self.source.enqueue(name, make_manifest(ROOT, self.config, self.config["schedules"][0],
                                               fixture=True, window_end=end))
        result = self.workflow.drain()[0]
        self.assertNotIn("error", result)
        return name

    def test_daily_slot_and_terminal_abstention_have_no_duplicate_effects(self):
        organization = self.initialize()
        result = self.cycle(organization)
        self.assertEqual((result["source_admissions"], result["source_executions"], result["research_admissions"]), (1, 1, 1))
        self.assertEqual(result["job"]["outcome"], "abstained")
        job = self.config["schedules"][0]["id"] + ":" + str(DAY)
        self.assertEqual(self.pipeline_calls[0][0], job)
        self.assertIs(self.pipeline_calls[0][1]["campaign"], self.campaign)
        self.assertEqual(self.source.inspect(job)["job"]["status"], "retrieval_complete")
        before = self.source.status()["usage"]
        again = self.cycle(self.reopen())
        self.assertEqual((again["source_admissions"], again["source_executions"], again["research_admissions"]), (0, 0, 0))
        self.assertEqual(self.sources, 1)
        self.assertEqual(len(self.pipeline_calls), 1)
        self.assertEqual(before, self.source.status()["usage"])
        self.assertEqual(organization.status()["outcomes"], {"abstained": 1})
        self.assertEqual(self.campaign.status()["attempted_calls"], 0)

    def test_manual_completed_job_is_dispatched_before_new_source_admission(self):
        job = self.manual()
        result = self.cycle(self.initialize())
        self.assertEqual(result["source_admissions"], 0)
        self.assertEqual(result["source_executions"], 0)
        self.assertEqual(self.pipeline_calls[0][0], job)
        self.assertEqual(result["job"]["job_digest"], digest(job))
        text = json.dumps(result)
        self.assertNotIn(job, text)
        self.assertNotIn(str(self.directory), text)
        self.assertNotIn(self.config["schedules"][0]["query"], text)

    def test_midnight_lag_clock_rollback_and_next_day_slot(self):
        organization = self.initialize()
        self.clock = DAY + 29
        self.assertEqual(self.cycle(organization)["source_admissions"], 0)
        self.assertFalse(self.pipeline_calls)
        self.clock = DAY + 30
        self.assertEqual(self.cycle(organization)["source_admissions"], 1)
        self.clock -= 1
        with self.assertRaisesRegex(ServiceError, "CLOCK_MOVED_BACKWARDS"):
            self.cycle(organization)
        self.clock = DAY + 86400 + 30
        self.assertEqual(self.cycle(organization)["source_admissions"], 1)
        self.assertEqual(len(self.pipeline_calls), 2)

    def test_failure_receipt_is_retained_and_not_retried(self):
        organization = self.initialize()
        self.outcome = "failed"
        first = self.cycle(organization)
        self.assertEqual(first["job"]["code"], "FIXTURE_REJECTION")
        self.assertEqual(self.cycle(self.reopen())["research_admissions"], 0)
        self.assertEqual(len(self.pipeline_calls), 1)
        self.assertEqual(organization.status()["outcomes"], {"failed": 1})

    def test_arbitrary_exception_text_is_not_persisted_or_retried(self):
        organization = self.initialize()
        def fail(*args, **kwargs):
            raise ValueError("untrusted-secret-or-private-path")
        result = organization.cycle(self.workflow, now=self.clock, pipeline_runner=fail)
        self.assertEqual(result["job"]["code"], "ORGANIZATION_LOCAL_FAILURE")
        self.assertNotIn("untrusted-secret", json.dumps(result))
        self.assertEqual(self.cycle(self.reopen())["research_admissions"], 0)
        self.assertFalse(self.pipeline_calls)

    def test_both_pause_controls_stop_source_and_research_admission(self):
        organization = self.initialize()
        for store in (self.source, self.campaign.store):
            store.pause(True)
            result = self.cycle(organization)
            self.assertTrue(result["paused"])
            self.assertEqual(result["source_admissions"], 0)
            self.assertEqual(result["research_admissions"], 0)
            store.pause(False)
        self.assertEqual(self.sources, 0)
        self.assertFalse(self.pipeline_calls)
        self.assertEqual(self.cycle(organization)["research_admissions"], 1)

    def test_pause_during_source_work_stops_pipeline_admission(self):
        organization = self.initialize()
        original = self.workflow.drain
        def drain(*args):
            result = original(*args)
            self.campaign.store.pause(True)
            return result
        with patch.object(self.workflow, "drain", side_effect=drain):
            result = self.cycle(organization)
        self.assertTrue(result["paused"])
        self.assertEqual(result["source_executions"], 1)
        self.assertFalse(self.pipeline_calls)
        self.campaign.store.pause(False)
        self.assertEqual(self.cycle(organization)["research_admissions"], 1)

    def test_process_lock_excludes_another_cycle_and_status_remains_readable(self):
        organization = self.initialize()
        other = self.reopen()
        with organization._lock():
            self.assertEqual(other.status()["jobs"], 0)
            with self.assertRaisesRegex(ServiceError, "ALREADY_RUNNING"):
                self.cycle(other)
        self.assertEqual(self.cycle(other)["research_admissions"], 1)

    def test_immutable_authority_policy_config_dataset_and_source_identity(self):
        self.initialize()
        self.policy["poll_seconds"] = 6
        with self.assertRaisesRegex(ServiceError, "INPUT_CHANGED"):
            self.reopen()
        self.policy = policy()
        other = self.directory / "other-authority"
        initialize(other, cap_microusd=100000000, prior_spend_microusd=0)
        with self.assertRaisesRegex(ServiceError, "INPUT_CHANGED"):
            module.Organization(self.destination, ROOT, self.source,
                Campaign(other, model_call=self.forbidden), policy=self.policy, fixture=True)
        changed = deepcopy(self.config)
        changed["schedules"][0]["query"] = "different retrieval question"
        source = Store(self.directory / "other-source", changed, initialize=True)
        with self.assertRaisesRegex(ServiceError, "INPUT_CHANGED"):
            module.Organization(self.destination, ROOT, source, self.campaign,
                                policy=self.policy, fixture=True)

    def test_strict_policy_and_source_control_plane_restrictions(self):
        for changed in ({**self.policy, "poll_seconds": True}, {**self.policy, "extra": 1},
                        {**self.policy, "schedules": []},
                        {**self.policy, "schedules": self.policy["schedules"] * 2}):
            with self.subTest(policy=changed), self.assertRaises(ServiceError):
                module.validate_policy(changed, self.config)
        from researcher.service.demo import demo_config
        with self.assertRaises(ServiceError):
            module.validate_policy(self.policy, demo_config())
        for key in ("enabled", "notify"):
            changed = deepcopy(self.config)
            changed["github"][key] = True
            with self.assertRaisesRegex(ServiceError, "RETRIEVAL_ONLY_REQUIRED"):
                module.validate_policy(self.policy, changed)

    def test_stale_or_failed_source_has_terminal_ineligible_receipt(self):
        self.manual(end=DAY - 3 * 86400)
        organization = self.initialize()
        result = self.cycle(organization)
        self.assertEqual(result["job"]["outcome"], "source_not_eligible")
        self.assertEqual(result["research_admissions"], 0)
        self.assertFalse(self.pipeline_calls)
        row = next(iter(organization._load()["jobs"].values()))
        self.assertEqual(row["phase"], "terminal")

    def test_unknown_source_effect_is_retained_without_research_or_retry(self):
        job = self.config["schedules"][0]["id"] + ":" + str(DAY)
        self.source.enqueue(job, make_manifest(ROOT, self.config, self.config["schedules"][0],
                                               fixture=True, window_end=DAY))
        self.source.next_job(job)
        self.source.reserve(job, "primary-0", {"fixture": "uncertain read"}, source_requests=1,
                            now=self.clock)
        self.source.fail_effect(job, "primary-0", "FIXTURE_TIMEOUT", ambiguous=True)
        organization = self.initialize()
        result = self.cycle(organization)
        self.assertEqual(result["job"]["outcome"], "source_not_eligible")
        self.assertEqual(self.cycle(self.reopen())["research_admissions"], 0)
        self.assertEqual(self.source.inspect(job)["job"]["status"], "reconciliation_required")
        self.assertEqual(self.sources, 0)
        self.assertFalse(self.pipeline_calls)

    def test_bounded_source_enumeration_and_partial_organization_fail_closed(self):
        self.manual("first")
        self.manual("second")
        organization = self.initialize()
        with patch.object(module, "MAX_JOBS", 1), self.assertRaisesRegex(ServiceError, "SOURCE_SCAN_LIMIT"):
            self.cycle(organization)
        self.assertFalse(self.pipeline_calls)
        other = self.directory / "partial"
        other.mkdir(mode=0o700)
        with self.assertRaises(ServiceError):
            module.Organization(other, ROOT, self.source, self.campaign, policy=self.policy, fixture=True)
        self.assertEqual(list(other.iterdir()), [])

    def test_index_receipt_and_pipeline_result_tampering_stop_new_work(self):
        organization = self.initialize()
        self.cycle(organization)
        index = organization._load()
        key = next(iter(index["jobs"]))
        result_path = self.destination / "jobs" / key / "pipeline/result.json"
        result = pipeline._record(result_path)
        result["outcome"] = "no_proposal"
        pipeline._write(result_path, pipeline._envelope(result))
        with self.assertRaisesRegex(ServiceError, "PIPELINE_RESULT_CHANGED"):
            self.cycle(organization)
        self.assertEqual(len(self.pipeline_calls), 1)

    def test_completed_receipt_checkpoint_gap_reconciles_without_pipeline_retry(self):
        organization = self.initialize()
        original = organization._save
        def fail(index):
            if any(row["phase"] == "terminal" for row in index["jobs"].values()):
                raise KeyboardInterrupt()
            original(index)
        with patch.object(organization, "_save", side_effect=fail), self.assertRaises(KeyboardInterrupt):
            self.cycle(organization)
        self.assertEqual(len(self.pipeline_calls), 1)
        result = self.cycle(self.reopen())
        self.assertEqual(result["job"]["outcome"], "abstained")
        self.assertEqual(len(self.pipeline_calls), 1)

    def test_actual_pipeline_interruption_resumes_same_private_directory(self):
        organization = self.initialize()
        calls = []
        def research(_name, packet):
            calls.append(packet)
            if len(calls) == 1:
                raise KeyboardInterrupt()
            return {"schema": "managed-research-proposal/v1", "authority": "none",
                "research": {"hypothesis": "Fixture abstention", "test_plan": "No experiment", "abstain": True, "claims": []},
                "critic": {"supported_claim_ids": [], "issues": [], "recommendation": "abstain"}, "proposal": None}
        with patch.object(self.campaign, "research", side_effect=research):
            with self.assertRaises(KeyboardInterrupt):
                organization.cycle(self.workflow, now=self.clock)
            self.assertEqual(self.reopen().cycle(self.workflow, now=self.clock)["job"]["outcome"], "abstained")
        self.assertEqual(len(calls), 2)
        self.assertEqual(self.sources, 1)
        self.assertEqual(len(list((self.destination / "jobs").iterdir())), 1)
        self.assertEqual(self.campaign.status()["attempted_calls"], 0)

    def test_oserror_after_receipt_commit_preserves_outcome_on_restart(self):
        organization = self.initialize()
        original = organization._save
        def fail(index):
            if any(row["phase"] == "terminal" for row in index["jobs"].values()):
                raise OSError("simulated index publication failure")
            original(index)
        with patch.object(organization, "_save", side_effect=fail), self.assertRaises(OSError):
            self.cycle(organization)
        result = self.cycle(self.reopen())
        self.assertEqual(result["job"]["outcome"], "abstained")
        self.assertIsNotNone(result["job"]["pipeline_result_digest"])
        self.assertEqual(len(self.pipeline_calls), 1)
        self.assertEqual(self.sources, 1)

    def test_compressed_30_day_slots_restart_with_injected_outcomes(self):
        # Calendar compression exercises coordinator dispatch, not elapsed-time
        # reliability or measured research yield. Outcome labels are injected.
        self.initialize()
        outcomes = ("abstained", "awaiting_dataset", "failed")
        authority_before = self.campaign.status()
        for day in range(30):
            self.clock = DAY + day * 86400 + 3600
            self.outcome = outcomes[day % 3]
            result = self.cycle(self.reopen())
            self.assertEqual(result["source_admissions"], 1)
            self.assertEqual(result["research_admissions"], 1)
            self.assertEqual(result["job"]["outcome"], self.outcome)
            self.assertEqual(self.pipeline_calls[-1][0],
                self.config["schedules"][0]["id"] + ":" + str(DAY + day * 86400))
            self.assertIs(self.pipeline_calls[-1][1]["campaign"], self.campaign)
            before = (self.sources, len(self.pipeline_calls), self.source.status()["usage"])
            repeated = self.cycle(self.reopen())
            self.assertEqual((repeated["source_admissions"], repeated["source_executions"],
                              repeated["research_admissions"]), (0, 0, 0))
            self.assertEqual(before, (self.sources, len(self.pipeline_calls), self.source.status()["usage"]))
        self.assertEqual((self.sources, len(self.pipeline_calls)), (30, 30))
        self.assertEqual(self.reopen().status()["outcomes"], {name: 10 for name in outcomes})
        self.assertEqual(self.campaign.status(), authority_before)

    def test_known_pipeline_checkpoint_interruption_remains_resumable(self):
        organization = self.initialize()
        def interrupted(*args, **kwargs):
            self.fake_pipeline(*args, **kwargs)
            raise ServiceError("PIPELINE_CHECKPOINT_INTERRUPTED")
        with self.assertRaisesRegex(ServiceError, "PIPELINE_CHECKPOINT_INTERRUPTED"):
            organization.cycle(self.workflow, now=self.clock, pipeline_runner=interrupted)
        self.assertEqual(organization.status()["outcomes"], {"interrupted_or_running": 1})
        def reconcile(root, source, job, directory, **kwargs):
            return pipeline._record(directory / "result.json")
        result = self.reopen().cycle(self.workflow, now=self.clock, pipeline_runner=reconcile)
        self.assertEqual(result["job"]["outcome"], "abstained")
        self.assertEqual((self.sources, len(self.pipeline_calls)), (1, 1))

    def test_missing_dataset_is_forwarded_without_manufactured_labels(self):
        organization = self.initialize()
        self.outcome = "awaiting_dataset"
        result = self.cycle(organization)
        self.assertIsNone(self.pipeline_calls[0][1]["dataset"])
        self.assertEqual(result["job"]["outcome"], "awaiting_dataset")
        self.assertIsNone(pipeline._record(self.destination / "input.json")["dataset"])

    def test_finite_serve_and_stop_event_do_not_schedule_extra_cycles(self):
        organization = self.initialize()
        events = []
        stop = threading.Event()
        def emit(value):
            events.append(value)
            stop.set()
        result = organization.serve(self.workflow, max_cycles=3, stopped=stop,
            pipeline_runner=self.fake_pipeline, progress=emit, clock=lambda: self.clock)
        self.assertEqual(result, {"cycles": 1, "stopped": True})
        self.assertEqual(len(events), 1)
        with self.assertRaisesRegex(ServiceError, "INVALID_CYCLE_LIMIT"):
            organization.serve(self.workflow)

    def test_fixture_rejects_default_real_provider_and_live_rejects_test_runner(self):
        actual = Campaign(self.authority)
        with self.assertRaisesRegex(ServiceError, "FIXTURE_PROVIDER_FORBIDDEN"):
            module.Organization.initialize(self.destination, ROOT, self.source, actual,
                policy=self.policy, fixture=True)
        with self.assertRaisesRegex(ServiceError, "CODEX_SDK_REQUIRED"):
            module.Organization.initialize(self.destination, ROOT, self.source, actual,
                                           policy=self.policy)
        from researcher.service.codex_campaign import CodexCampaign
        import sys
        actual = CodexCampaign(self.authority, sdk_python=sys.executable)
        organization = module.Organization.initialize(self.destination, ROOT, self.source, actual,
                                                       policy=self.policy)
        workflow = Workflow(self.source, ROOT, live=True)
        with self.assertRaisesRegex(ServiceError, "TEST_ADAPTER_FORBIDDEN"):
            organization.cycle(workflow, live=True, now=self.clock, pipeline_runner=self.fake_pipeline)
        self.assertFalse(self.pipeline_calls)

    def test_cli_init_and_status_need_no_credentials_and_no_runtime_activation(self):
        import sys
        cfg, pol = self.directory / "config.json", self.directory / "policy.json"
        pipeline._write(cfg, self.config)
        pipeline._write(pol, self.policy)
        arguments = ["--state", str(self.destination), "--repo", str(ROOT),
            "--source-state", str(self.source.directory), "--source-config", str(cfg),
            "--authority", str(self.authority), "--policy", str(pol), "--sdk-python", sys.executable]
        for command in ("init", "status"):
            out = io.StringIO()
            with patch("sys.stdout", out), patch.object(module, "read_env_file", side_effect=self.forbidden):
                self.assertEqual(module.main([command, *arguments]), 0)
            value = json.loads(out.getvalue())
            self.assertEqual(value["jobs"], 0)
            self.assertNotIn(str(self.directory), out.getvalue())
        self.assertFalse(self.source.status()["jobs"])


if __name__ == "__main__":
    unittest.main()
