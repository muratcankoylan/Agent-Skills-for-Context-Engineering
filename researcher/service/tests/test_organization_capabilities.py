"""Explicit coordinator capabilities, using existing offline fixture objects.

Import fixture modules by alias rather than importing/subclassing TestCases, so
unittest discovery does not execute their original tests a second time.
"""
from copy import deepcopy
import io
import json
import sys
import threading
import unittest
from unittest.mock import Mock, patch

from researcher.scripts.schema_contract import canonicalize
from researcher.service import organization as module, research_pipeline as pipeline
from researcher.service.contracts import ServiceError
from researcher.service.trace_pump import TracePump
from researcher.service.trace_events import ENDPOINT as EVENT_ENDPOINT
from researcher.service.trace_export import ENDPOINT as TRACE_ENDPOINT
from researcher.service.tests import test_organization as fixtures


KEY = "private-offline-trace-credential"


class OrganizationCapabilityTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.OrganizationTests(methodName="runTest")
        self.addCleanup(self.f.doCleanups)
        self.f.setUp()
        self.transports = []

    def pumps(self, **options):
        pumps = []
        def acknowledge(url, *_args):
            if url == EVENT_ENDPOINT:
                return 204, {}, b""
            self.assertEqual(url, TRACE_ENDPOINT)
            return 200, {"content-type": "application/json"}, b"{}"
        for state in (self.f.authority, self.f.source.directory):
            transport = Mock(side_effect=acknowledge)
            self.transports.append(transport)
            pumps.append(TracePump(state, credential=KEY, project_id="fixture-test", live=True,
                                   transport=transport, clock=lambda: 100, **options))
        return tuple(pumps)

    def test_default_policy_roundtrip_is_byte_compatible_without_new_default(self):
        original = deepcopy(self.f.policy)
        validated = module.validate_policy(original, self.f.config)
        self.assertEqual(canonicalize(validated), canonicalize(self.f.policy))
        self.assertNotIn("research_profile", validated)
        validated["evaluation"]["seed"] = 9
        self.assertEqual(original, self.f.policy)

    def test_optional_profile_is_closed_and_not_a_permission_wildcard(self):
        for value in (None, True, {}, [], "tool_free", "native_tools", "captured-actions-v2"):
            with self.subTest(value=value), self.assertRaisesRegex(ServiceError, "ORGANIZATION_POLICY_INVALID"):
                module.validate_policy({**self.f.policy, "research_profile": value}, self.f.config)
        value = {**self.f.policy, "research_profile": "captured-actions-v1"}
        self.assertEqual(module.validate_policy(value, self.f.config), value)
        self.assertEqual(self.f.source.status()["jobs"], [])
        self.assertEqual(self.f.campaign.status()["attempted_calls"], 0)

    def test_default_pipeline_call_does_not_receive_new_profile_key(self):
        organization = self.f.initialize()
        result = self.f.cycle(organization)
        self.assertEqual(result["job"]["outcome"], "abstained")
        self.assertNotIn("research_profile", self.f.pipeline_calls[0][1])
        saved = pipeline._record(self.f.destination / "input.json")
        self.assertEqual(canonicalize(saved["policy"]), canonicalize(fixtures.policy()))
        self.assertNotIn("research_profile", saved["policy"])

    def test_explicit_profile_forwarded_and_identity_cannot_change_on_reopen(self):
        self.f.policy["research_profile"] = "captured-actions-v1"
        organization = self.f.initialize()
        self.f.cycle(organization)
        self.assertEqual(self.f.pipeline_calls[0][1]["research_profile"], "captured-actions-v1")
        self.assertEqual(pipeline._record(self.f.destination / "input.json")["policy"], self.f.policy)
        del self.f.policy["research_profile"]
        with self.assertRaisesRegex(ServiceError, "ORGANIZATION_INPUT_CHANGED"):
            self.f.reopen()

    def test_both_journals_export_after_cycle_span_closes(self):
        self.f.manual()
        organization = self.f.initialize()
        pumps = self.pumps()
        events, observed, event_ids = [], [], set()
        journals = (self.f.campaign.tracer.journal, self.f.workflow.tracer.journal)

        def send(url, _headers, body, _timeout):
            self.assertTrue(all(journal.status()["unfinished_spans"] == 0 for journal in journals))
            if url == EVENT_ENDPOINT:
                event_ids.update(event["event_id"] for event in json.loads(body))
                return 204, {}, b""
            self.assertEqual(url, TRACE_ENDPOINT)
            spans = json.loads(body)["resourceSpans"][0]["scopeSpans"][0]["spans"]
            self.assertTrue(all("endTimeUnixNano" in span for span in spans))
            self.assertTrue(all(span["traceId"] in event_ids for span in spans))
            observed.extend(span["name"] for span in spans)
            return 200, {"content-type": "application/json"}, b"{}"

        for transport in self.transports:
            transport.side_effect = send
        result = self.f.cycle(organization, trace_pumps=pumps, progress=events.append)
        self.assertEqual(result["job"]["outcome"], "abstained")
        self.assertEqual([event["journal"] for event in events], [0, 1])
        self.assertEqual([event["status"] for event in events], ["exported", "exported"])
        self.assertIn("organization.cycle", observed)
        self.assertIn("workflow.execute", observed)
        self.assertTrue(all([call.args[0] for call in transport.call_args_list]
                            == [EVENT_ENDPOINT, TRACE_ENDPOINT] for transport in self.transports))
        self.assertTrue(all(journal.status()["pending_export"] == 0 for journal in journals))
        self.assertNotIn(KEY, json.dumps(events))

    def test_pause_blocks_research_but_does_not_block_approved_trace_delivery(self):
        self.f.manual()
        organization = self.f.initialize()
        for store in (self.f.source, self.f.campaign.store):
            with self.subTest(store=store is self.f.source):
                store.pause(True)
                before = self.f.source.status()["usage"], self.f.campaign.status()
                events = []
                result = self.f.cycle(organization, trace_pumps=self.pumps(), progress=events.append)
                self.assertTrue(result["paused"])
                self.assertEqual((result["source_admissions"], result["research_admissions"]), (0, 0))
                self.assertEqual(events[0]["status"], "exported")
                self.assertEqual(before, (self.f.source.status()["usage"], self.f.campaign.status()))
                store.pause(False)
        self.assertFalse(self.f.pipeline_calls)

    def test_failed_pipeline_stays_failed_with_completed_trace_delivery(self):
        self.f.outcome = "failed"
        organization = self.f.initialize()
        events = []
        result = self.f.cycle(organization, trace_pumps=self.pumps(), progress=events.append)
        self.assertEqual(result["job"]["outcome"], "failed")
        self.assertEqual(result["job"]["code"], "FIXTURE_REJECTION")
        self.assertEqual(events[0]["status"], "exported")
        cycles = [row for row in self.f.campaign.tracer.journal.rows() if row["operation"] == "organization.cycle"]
        self.assertEqual(cycles[-1]["status"], "error")
        self.assertIsNotNone(cycles[-1]["end_ns"])
        self.assertEqual(organization.status()["outcomes"], {"failed": 1})

    def test_throwing_cycle_keeps_original_exception_after_both_delivery_ticks(self):
        organization = self.f.initialize()
        pumps, events = self.pumps(), []
        original = ServiceError("FIXTURE_ORIGINAL_FAILURE")
        with patch.object(organization, "_load", side_effect=original), self.assertRaises(ServiceError) as caught:
            self.f.cycle(organization, trace_pumps=pumps, progress=events.append)
        self.assertIs(caught.exception, original)
        self.assertEqual([event["journal"] for event in events], [0, 1])
        self.assertEqual(events[0]["status"], "exported")
        self.assertEqual(self.f.campaign.tracer.journal.status()["unfinished_spans"], 0)
        self.assertFalse(self.f.pipeline_calls)

    def test_cloud_failure_does_not_change_job_result_cost_or_resume(self):
        self.f.manual(name=self.f.config["schedules"][0]["id"] + ":" + str(fixtures.DAY))
        organization = self.f.initialize()
        pumps, events = self.pumps(), []
        before = self.f.source.status()["usage"], self.f.campaign.status()
        for transport in self.transports:
            transport.side_effect = TimeoutError("untrusted private cloud error")
        result = self.f.cycle(organization, trace_pumps=pumps, progress=events.append)
        self.assertEqual(result["job"]["outcome"], "abstained")
        self.assertEqual([event["status"] for event in events], ["halted", "halted"])
        self.assertNotIn("private", json.dumps(events))
        self.assertEqual(before, (self.f.source.status()["usage"], self.f.campaign.status()))
        key = next(iter(organization._load()["jobs"]))
        self.assertEqual(pipeline._record(self.f.destination / "jobs" / key / "receipt.json"), result["job"])
        again = self.f.cycle(self.f.reopen(), trace_pumps=pumps, progress=events.append)
        self.assertEqual(again["research_admissions"], 0)
        self.assertEqual(len(self.f.pipeline_calls), 1)
        self.assertTrue(all(transport.call_count == 1 for transport in self.transports))

    def test_serve_ticks_both_journals_before_cycle_progress_and_respects_cadence(self):
        self.f.manual()
        organization = self.f.initialize()
        events, pumps = [], self.pumps()
        stop = threading.Event()
        with patch.object(stop, "wait", return_value=False) as wait:
            result = organization.serve(self.f.workflow, max_cycles=2, stopped=stop,
                pipeline_runner=self.f.fake_pipeline, progress=events.append,
                clock=lambda: self.f.clock, trace_pumps=pumps)
        self.assertEqual(result, {"cycles": 2, "stopped": False})
        self.assertEqual([event.get("event") for event in events],
                         ["trace_delivery", "trace_delivery", None] * 2)
        self.assertEqual([event["status"] for event in events if event.get("event")],
                         ["exported", "exported", "deferred", "deferred"])
        self.assertTrue(all(transport.call_count == 2 for transport in self.transports))
        wait.assert_called_once_with(self.f.policy["poll_seconds"])

    def test_trace_progress_failure_does_not_replace_success_or_skip_second_journal(self):
        self.f.manual()
        organization = self.f.initialize()
        pumps = self.pumps()
        result = self.f.cycle(organization, trace_pumps=pumps,
                             progress=Mock(side_effect=BrokenPipeError("private output sink")))
        self.assertEqual(result["job"]["outcome"], "abstained")
        self.assertTrue(all(transport.call_count == 2 for transport in self.transports))

    def test_trace_progress_failure_cannot_mask_original_cycle_error(self):
        organization = self.f.initialize()
        pumps = self.pumps()
        original = ServiceError("FIXTURE_ORIGINAL_FAILURE")
        with patch.object(organization, "_load", side_effect=original), self.assertRaises(ServiceError) as caught:
            self.f.cycle(organization, trace_pumps=pumps,
                         progress=Mock(side_effect=OSError("private sink error")))
        self.assertIs(caught.exception, original)

    def test_no_pumps_preserves_cycle_shape_and_does_not_emit_delivery_events(self):
        organization = self.f.initialize()
        emit = Mock()
        result = self.f.cycle(organization, progress=emit)
        self.assertEqual(set(result), {"schema", "organization_digest", "at", "source_admissions",
            "source_executions", "research_admissions", "job", "paused", "fixture"})
        emit.assert_not_called()
        self.assertEqual(self.f.campaign.tracer.journal.status()["export_attempts"], 0)

    def test_invalid_pump_capabilities_fail_before_state_or_research(self):
        organization = self.f.initialize()
        pump = self.pumps()[0]
        for pumps in ([pump], (object(),), (pump, pump, pump)):
            with self.subTest(kind=type(pumps).__name__), patch.object(organization, "_lock") as lock:
                with self.assertRaisesRegex(ServiceError, "ORGANIZATION_INVALID_TRACE_PUMPS"):
                    self.f.cycle(organization, trace_pumps=pumps)
                lock.assert_not_called()
        self.assertFalse(self.f.pipeline_calls)

    def args(self, command, *extra):
        return [command, "--state", str(self.f.destination), "--repo", str(fixtures.ROOT),
            "--source-state", str(self.f.source.directory), "--source-config", "/not-read-config",
            "--authority", str(self.f.authority), "--policy", "/not-read-policy",
            "--sdk-python", sys.executable, *extra]

    def test_cli_invalid_combinations_refuse_before_reading_env_or_state(self):
        cases = [("init", ["--trace-export"]), ("status", ["--trace-export"]),
                 ("status", ["--trace-allow-default-project"]), ("status", ["--live"]),
                 ("cycle", ["--trace-export"]), ("cycle", ["--env-file", "/not-read"]),
                 ("cycle", ["--live"]), ("cycle", ["--live", "--env-file", "/not-read", "--max-cycles", "1"]),
                 ("cycle", ["--live", "--env-file", "/not-read", "--trace-allow-default-project"])]
        for command, flags in cases:
            with self.subTest(command=command, flags=flags), patch("sys.stdout", io.StringIO()) as out, \
                 patch.object(module, "read_env_file") as env, patch.object(module, "read_config_file") as config, \
                 patch.object(module, "Store") as store, patch.object(module, "TracePump") as pump:
                self.assertEqual(module.main(self.args(command, *flags)), 2)
                self.assertEqual(json.loads(out.getvalue())["error"], "ORGANIZATION_EXPLICIT_EXECUTION_REQUIRED")
                env.assert_not_called()
                config.assert_not_called()
                store.assert_not_called()
                pump.assert_not_called()

    def test_cli_invalid_trace_config_fails_before_opening_authorities(self):
        for values, flags, expected in (
            ({"OPENAI_API_KEY": "offline", "RAINDROP_WRITE_KEY": ""}, [], "TRACE_EXPORT_INVALID_CREDENTIAL"),
            ({"OPENAI_API_KEY": "offline", "RAINDROP_WRITE_KEY": KEY, "RAINDROP_PROJECT_ID": "default"},
             [], "TRACE_EXPORT_DEFAULT_PROJECT_REQUIRES_APPROVAL"),
            ({"OPENAI_API_KEY": "offline", "RAINDROP_WRITE_KEY": KEY, "RAINDROP_PROJECT_ID": ""},
             ["--trace-allow-default-project"], "TRACE_EXPORT_INVALID_PROJECT")):
            with self.subTest(expected=expected), patch("sys.stdout", io.StringIO()) as out, \
                 patch.object(module, "read_config_file", side_effect=[json.dumps(self.f.config), json.dumps(self.f.policy)]), \
                 patch.object(module, "read_env_file", return_value=values), patch.object(module, "Store") as store, \
                 patch("researcher.service.codex_campaign.CodexCampaign") as campaign:
                code = module.main(self.args("cycle", "--live", "--env-file", "/not-read", "--trace-export", *flags))
                self.assertEqual(code, 2)
                self.assertEqual(json.loads(out.getvalue())["error"], expected)
                store.assert_not_called()
                campaign.assert_not_called()
                self.assertNotIn(KEY, out.getvalue())

    def test_cli_credential_presence_alone_does_not_create_exporter(self):
        values = {"OPENAI_API_KEY": "offline", "RAINDROP_WRITE_KEY": KEY, "RAINDROP_PROJECT_ID": "default"}
        coordinator = Mock()
        coordinator.cycle.return_value = {"fixture": True}
        with patch("sys.stdout", io.StringIO()), \
             patch.object(module, "read_config_file", side_effect=[json.dumps(self.f.config), json.dumps(self.f.policy)]), \
             patch.object(module, "read_env_file", return_value=values), \
             patch.object(module, "Store"), patch("researcher.service.codex_campaign.CodexCampaign"), \
             patch.object(module, "Organization", return_value=coordinator), patch.object(module, "Workflow"), \
             patch.object(module, "TracePump") as pump:
            self.assertEqual(module.main(self.args("cycle", "--live", "--env-file", "/not-read")), 0)
        pump.assert_not_called()
        self.assertEqual(coordinator.cycle.call_args.kwargs["trace_pumps"], ())

    def test_cli_explicit_trace_flags_build_only_source_and_authority_capabilities(self):
        values = {"OPENAI_API_KEY": "offline", "RAINDROP_WRITE_KEY": KEY, "RAINDROP_PROJECT_ID": "default"}
        coordinator = Mock()
        coordinator.cycle.return_value = {"fixture": True}
        pumps = [object(), object()]
        with patch("sys.stdout", io.StringIO()), \
             patch.object(module, "read_config_file", side_effect=[json.dumps(self.f.config), json.dumps(self.f.policy)]), \
             patch.object(module, "read_env_file", return_value=values), \
             patch.object(module, "Store"), patch("researcher.service.codex_campaign.CodexCampaign") as campaign, \
             patch.object(module, "Organization", return_value=coordinator), patch.object(module, "Workflow"), \
             patch.object(module, "TracePump", side_effect=pumps) as pump:
            code = module.main(self.args("cycle", "--live", "--env-file", "/not-read", "--trace-export",
                                         "--trace-allow-default-project"))
            self.assertEqual(code, 0)
        self.assertEqual([call.args[0] for call in pump.call_args_list], [self.f.authority, self.f.source.directory])
        self.assertTrue(all(call.kwargs["allow_default_project"] is True for call in pump.call_args_list))
        self.assertEqual(coordinator.cycle.call_args.kwargs["trace_pumps"], tuple(pumps))
        self.assertNotIn(KEY, repr(campaign.call_args))
