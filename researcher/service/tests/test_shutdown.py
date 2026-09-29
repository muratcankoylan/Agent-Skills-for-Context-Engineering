"""Cooperative drain with real stores and explicit synthetic source/SDK fixtures."""
import contextlib
import io
import os
import threading
import unittest
from unittest.mock import patch

from researcher.service import research_pipeline as pipeline
from researcher.service.contracts import ServiceError
from researcher.service.shutdown import StopRequested, check_stop, stop_scope
from researcher.service.tests import test_organization as fixtures
from researcher.service.tests import test_codex_organization as sdk_fixtures


class ShutdownTests(unittest.TestCase):
    def fixture(self):
        case = fixtures.OrganizationTests()
        case.setUp()
        self.addCleanup(case.doCleanups)
        return case

    def serve(self, case, stop):
        with contextlib.redirect_stdout(io.StringIO()):
            return case.reopen().serve(case.workflow, max_cycles=1, stopped=stop,
                pipeline_runner=case.fake_pipeline, clock=lambda: case.clock, progress=lambda _: None)

    def test_signal_is_ephemeral_nested_and_thread_isolated(self):
        event, clear = threading.Event(), threading.Event()
        event.set()
        observed = []
        with stop_scope(event):
            with self.assertRaises(StopRequested):
                check_stop()
            with stop_scope(clear):
                check_stop()
            thread = threading.Thread(target=lambda: (check_stop(), observed.append("unaffected")))
            thread.start()
            thread.join(2)
            self.assertFalse(thread.is_alive())
            with self.assertRaises(StopRequested):
                check_stop()
        check_stop()
        self.assertEqual(observed, ["unaffected"])
        self.assertNotIsInstance(StopRequested(), Exception)
        with self.assertRaises(TypeError), stop_scope(lambda: True):
            pass

    def test_preexisting_stop_admits_no_source_or_pipeline(self):
        case = self.fixture()
        case.initialize()
        stop = threading.Event()
        stop.set()
        self.assertEqual(self.serve(case, stop), {"cycles": 0, "stopped": True})
        self.assertEqual((case.sources, case.primary_transport.calls, len(case.pipeline_calls)), (0, 0, 0))

    def test_stop_after_discovery_does_not_admit_primary_or_pipeline_and_resumes(self):
        case = self.fixture()
        case.initialize()
        stop = threading.Event()
        collector = case.workflow.retrieval_source
        def collect(*args, **kwargs):
            value = collector(*args, **kwargs)
            stop.set()
            return value
        case.workflow.retrieval_source = collect
        with patch.object(fixtures.module.Organization, "_deliver") as deliver:
            self.assertEqual(self.serve(case, stop), {"cycles": 0, "stopped": True})
            deliver.assert_called_once()
        self.assertEqual((case.sources, case.primary_transport.calls, len(case.pipeline_calls)), (1, 0, 0))
        job = case.config["schedules"][0]["id"] + ":" + str(fixtures.DAY)
        effects = case.source.inspect(job)["effects"]
        self.assertEqual([(row["name"], row["state"]) for row in effects], [("retrieval-deepmind", "completed")])
        self.assertEqual(case.reopen().status()["outcomes"], {})
        case.workflow.retrieval_source = collector
        self.assertEqual(self.serve(case, threading.Event()), {"cycles": 1, "stopped": False})
        self.assertEqual((case.sources, case.primary_transport.calls, len(case.pipeline_calls)), (1, 1, 1))

    def test_stop_after_primary_keeps_completed_source_without_research_admission(self):
        case = self.fixture()
        case.initialize()
        stop = threading.Event()
        reader = case.workflow.primary_reader
        def read(*args, **kwargs):
            value = reader(*args, **kwargs)
            stop.set()
            return value
        case.workflow.primary_reader = read
        self.assertEqual(self.serve(case, stop), {"cycles": 0, "stopped": True})
        self.assertEqual((case.sources, case.primary_transport.calls, len(case.pipeline_calls)), (1, 1, 0))
        case.workflow.primary_reader = reader
        self.serve(case, threading.Event())
        self.assertEqual((case.sources, case.primary_transport.calls, len(case.pipeline_calls)), (1, 1, 1))

    def test_stop_does_not_convert_real_source_uncertainty_into_success(self):
        case = self.fixture()
        case.initialize()
        stop = threading.Event()
        def broken(*_args, **_kwargs):
            stop.set()
            raise ServiceError("FIXTURE_REMOTE_UNKNOWN")
        case.workflow.retrieval_source = broken
        self.serve(case, stop)
        job = case.config["schedules"][0]["id"] + ":" + str(fixtures.DAY)
        effect = case.source.inspect(job)["effects"][0]
        self.assertEqual(effect["state"], "unknown")
        self.assertEqual(case.source.inspect(job)["job"]["status"], "reconciliation_required")
        self.assertEqual(len(case.pipeline_calls), 0)

    def test_stop_before_new_phase_does_not_create_failure_or_partial_candidate(self):
        case = self.fixture()
        directory = case.directory / "phase"
        directory.mkdir(mode=0o700)
        state = {"receipts": {}, "outcome": None}
        stop = threading.Event()
        stop.set()
        with stop_scope(stop), self.assertRaises(StopRequested):
            pipeline._phase(directory, state, "candidate", {}, lambda: self.fail("new phase"))
        self.assertEqual(list(directory.iterdir()), [])

    def test_completed_phase_replays_while_stop_requested(self):
        case = self.fixture()
        directory = case.directory / "phase"
        directory.mkdir(mode=0o700)
        state = {"receipts": {}, "outcome": None}
        first = pipeline._phase(directory, state, "packet", {}, lambda: {"fixture": True})
        stop = threading.Event()
        stop.set()
        with stop_scope(stop):
            self.assertEqual(pipeline._phase(directory, state, "packet", {}, lambda: self.fail("repeat")), first)

    def test_stop_during_atomic_candidate_phase_commits_before_next_phase(self):
        case = self.fixture()
        directory = case.directory / "phase"
        directory.mkdir(mode=0o700)
        state = {"receipts": {}, "outcome": None}
        stop = threading.Event()
        def candidate():
            stop.set()
            return {"fixture": True}
        with stop_scope(stop):
            result = pipeline._phase(directory, state, "candidate", {}, candidate)
            self.assertEqual(pipeline._record(directory / "candidate.json")["output"], result)
            with self.assertRaises(StopRequested):
                pipeline._phase(directory, state, "evaluation", {}, lambda: self.fail("evaluation admitted"))
        self.assertIn("candidate", state["receipts"])
        self.assertFalse((directory / "failure.json").exists())


@unittest.skipUnless(os.environ.get("CODEX_WORKER_TEST_PYTHON"), "explicit pinned SDK interpreter required")
class SDKShutdownTests(unittest.TestCase):
    def setUp(self):
        self.case = sdk_fixtures.SDKOrganizationTests()
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.stop = threading.Event()

    def serve(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return self.case.coordinator().serve(self.case.workflow, max_cycles=1, stopped=self.stop,
                clock=lambda: self.case.clock, progress=lambda _: None)

    def stopping_transport(self, count, *, fail=False):
        original = self.case.campaign.transport
        def transport(*args, **kwargs):
            output = original(*args, **kwargs)
            if len(self.case.wires) == count:
                self.stop.set()
                if fail:
                    raise TimeoutError("synthetic timeout")
            return output
        self.case.campaign.transport = transport
        return original

    def test_stop_during_researcher_commits_then_resumes_critic_without_repeat(self):
        self.case.coordinator(create=True)
        original = self.stopping_transport(1)
        self.assertEqual(self.serve(), {"cycles": 0, "stopped": True})
        self.assertEqual(len(self.case.wires), 1)
        self.assertEqual(self.case.campaign.status()["completed_calls"], 1)
        self.assertEqual(self.case.coordinator().status()["outcomes"], {"interrupted_or_running": 1})
        self.stop.clear()
        self.case.campaign.transport = original
        self.assertEqual(self.serve(), {"cycles": 1, "stopped": False})
        self.assertEqual(len(self.case.wires), 2)
        self.assertEqual(self.case.coordinator().status()["outcomes"], {"abstained": 1})

    def test_stop_before_sdk_intent_has_no_effect_and_completed_receipt_can_replay(self):
        campaign = self.case.campaign
        options = {"instructions": "Return JSON.", "prompt": "Fixture-only drain proof."}
        self.stop.set()
        with stop_scope(self.stop), self.assertRaises(StopRequested):
            campaign.call("drain-proof", "researcher", **options)
        self.assertEqual(campaign.status()["attempted_calls"], 0)
        self.assertFalse(self.case.wires)
        from researcher.service.tests.test_codex_campaign import upstream
        campaign.transport = lambda *_args, **_kwargs: upstream()
        self.stop.clear()
        receipt = campaign.call("drain-proof", "researcher", **options)
        self.stop.set()
        campaign.credential = None
        with stop_scope(self.stop):
            self.assertEqual(campaign.call("drain-proof", "researcher", **options), receipt)
        self.assertEqual(campaign.status()["attempted_calls"], 1)

    def test_stop_after_specialist_replays_actions_without_repeating_consultation(self):
        from researcher.service.tests.test_pipeline_actions import ActionFixture
        fixture = ActionFixture(self, sdk=True)
        fixture.mode = "finish"
        original = fixture.study.campaign.transport
        def transport(*args, **kwargs):
            response = original(*args, **kwargs)
            if len(fixture.wires) == 4:
                self.stop.set()
            return response
        fixture.study.campaign.transport = transport
        with stop_scope(self.stop), self.assertRaises(StopRequested):
            fixture.run()
        self.assertEqual(len(fixture.wires), 4)
        self.assertFalse((fixture.study.destination / "failure.json").exists())
        self.stop.clear()
        fixture.study.campaign.transport = original
        self.assertEqual(fixture.run()["outcome"], "awaiting_dataset")
        self.assertEqual(len(fixture.wires), 7)

    def test_stop_during_evaluation_preserves_completed_task_and_resumes(self):
        from researcher.service.agents_evals import fixture_dataset
        self.case.dataset = fixture_dataset()
        self.case.answers.abstain = False
        self.case.coordinator(create=True)
        original = self.stopping_transport(4)
        self.assertEqual(self.serve(), {"cycles": 0, "stopped": True})
        self.assertEqual(len(self.case.wires), 4)
        self.assertEqual(self.case.campaign.status()["completed_calls"], 4)
        self.stop.clear()
        self.case.campaign.transport = original
        self.assertEqual(self.serve(), {"cycles": 1, "stopped": False})
        self.assertEqual(len(self.case.wires), 15)
        self.assertEqual(self.case.coordinator().status()["outcomes"], {"evaluated_not_accepted": 1})

    def test_unknown_inflight_is_terminal_quarantined_not_restarted_by_stop(self):
        self.case.coordinator(create=True)
        original = self.stopping_transport(1, fail=True)
        self.serve()
        self.assertEqual(len(self.case.wires), 1)
        status = self.case.campaign.status()
        self.assertEqual(status["attempted_calls"], 1)
        self.assertEqual(status["completed_calls"], 0)
        self.assertGreater(status["reserved_microusd"], 0)
        self.assertEqual(self.case.coordinator().status()["outcomes"], {"failed": 1})
        self.stop.clear()
        self.case.campaign.transport = original
        self.serve()
        self.assertEqual(len(self.case.wires), 1)


if __name__ == "__main__":
    unittest.main()
