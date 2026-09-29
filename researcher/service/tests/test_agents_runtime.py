"""Crash and recovery tests for managed sessions. No network or model calls."""

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from researcher.service.agents_runtime import (
    ManagedResearch,
    SessionLedger,
    _effective_session,
    _pages,
    prepare_packet,
)
from researcher.service.contracts import ServiceError
from researcher.service.demo import source
from researcher.service.openai_agents import AgentsClient, BASE_URL

ROOT = Path(__file__).resolve().parents[3]


class FakeAgents:
    def __init__(self, packet):
        self.session = {
            "object": "agent.session",
            "id": "as_test",
            "status": "in_progress",
            "agent": deepcopy(packet["request"]["agent"]),
            "environment": {"type": "none"},
            "vault_ids": [],
            "required_actions": [],
            "usage": None,
        }
        self.create_count = self.cancel_count = self.read_count = 0
        self.fail_create = self.fail_cancel = self.fail_read = False
        self.turn_rows = []
        self.item_rows = []

    def create(self, _payload):
        self.create_count += 1
        if self.fail_create:
            raise OSError("sensitive remote diagnostic must not escape")
        return deepcopy(self.session)

    def retrieve(self, _id):
        self.read_count += 1
        if self.fail_read:
            raise OSError("offline")
        return deepcopy(self.session)

    def turns(self, _id, after=None):
        return {"data": deepcopy(self.turn_rows), "has_more": False}

    def items(self, _id, turn_id, after=None):
        return {"data": deepcopy(self.item_rows), "has_more": False}

    def cancel(self, _id, key):
        self.cancel_count += 1
        if self.fail_cancel:
            raise OSError("unknown cancellation")

    def finish(self, status="completed", *, output=None):
        self.session["status"] = "idle"
        self.turn_rows = [
            {
                "id": "turn_1",
                "session_id": "as_test",
                "subagent_id": None,
                "status": status,
                "usage": None,
            }
        ]
        answer = {
            "schema": "managed-research-proposal/v1",
            "authority": "none",
            "research": {
                "hypothesis": "No sufficient evidence.",
                "test_plan": "Collect independent evidence.",
                "abstain": True,
                "claims": [],
            },
            "critic": {
                "supported_claim_ids": [],
                "issues": ["Insufficient evidence."],
                "recommendation": "abstain",
            },
            "proposal": None,
        }
        self.item_rows = [
            {
                "id": "item_1",
                "type": "message",
                "role": "assistant",
                "turn_id": "turn_1",
                "phase": "final_answer",
                "status": "completed",
                "content": [
                    {"type": "output_text", "text": output or json.dumps(answer)}
                ],
            }
        ]


class ManagedRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name).resolve() / "managed"
        self.packet = prepare_packet(
            ROOT,
            model="fixture-model-v1",
            query="evidence context transfer",
            skills=["context-fundamentals"],
            evidence=source("", "", None)["evidence"],
        )
        self.ledger = SessionLedger.prepare(self.path, self.packet)
        self.client = FakeAgents(self.packet)
        self.now = 1000
        self.runtime = ManagedResearch(self.ledger, self.client, clock=lambda: self.now)

    def start(self):
        return self.runtime.submit(live=True, acknowledge_cost_risk=True)

    def test_live_and_cost_risk_ack_are_both_required_before_intent(self):
        for live, ack in [(False, True), (True, False), (False, False)]:
            with self.assertRaisesRegex(ServiceError, "COST_ACK"):
                self.runtime.submit(live=live, acknowledge_cost_risk=ack)
        self.assertEqual(self.client.create_count, 0)
        self.assertEqual(self.ledger.status()["phase"], "prepared")

    def test_default_managed_submission_is_retired_before_intent(self):
        runtime = ManagedResearch(self.ledger, AgentsClient("fixture-secret"), clock=lambda: self.now)
        with self.assertRaisesRegex(ServiceError, "MANAGED_SUBMISSION_RETIRED_USE_CODEX_SDK"):
            runtime.submit(live=True, acknowledge_cost_risk=True)
        self.assertEqual(self.ledger.status()["phase"], "prepared")

    def test_single_submit_and_resume_never_recreate(self):
        self.start()
        with self.assertRaisesRegex(ServiceError, "ALREADY_ATTEMPTED"):
            self.start()
        self.runtime.observe()
        self.assertEqual(self.client.create_count, 1)
        self.assertEqual(self.ledger.status()["session_id"], "as_test")

    def test_create_unknown_retains_intent_no_sensitive_diagnostic(self):
        self.client.fail_create = True
        with self.assertRaisesRegex(ServiceError, "RECONCILIATION") as raised:
            self.start()
        self.assertNotIn("sensitive", str(raised.exception))
        self.assertEqual(self.ledger.status()["phase"], "reconciliation_required")
        with self.assertRaises(ServiceError):
            self.start()
        self.assertEqual(self.client.create_count, 1)

    def test_crash_after_intent_is_not_new_submission(self):
        _, state = self.ledger.load()
        state["phase"] = "submitting"
        self.ledger.save(state)
        with self.assertRaisesRegex(ServiceError, "SESSION_ID_UNAVAILABLE"):
            self.runtime.observe()
        self.assertEqual(self.ledger.status()["phase"], "reconciliation_required")
        with self.assertRaises(ServiceError):
            self.start()
        self.assertEqual(self.client.create_count, 0)

    def test_idle_is_not_success_without_completed_root_turn(self):
        self.start()
        self.client.session["status"] = "idle"
        self.assertEqual(self.runtime.observe()["phase"], "running")

    def test_completed_abstention_persists_validated_result_and_no_reasoning(self):
        self.start()
        self.client.finish()
        self.client.item_rows.append(
            {"id": "reasoning_1", "type": "reasoning", "text": "private chain"}
        )
        result = self.runtime.observe()
        self.assertEqual(result["phase"], "completed")
        self.assertFalse(result["production_ready"])
        self.assertTrue(result["remote_stop_confirmed"])
        saved = (self.path / "result.json").read_text()
        self.assertNotIn("private chain", saved)
        self.assertIn('"independent_evaluation":"not_run"', saved)
        with patch.object(
            self.client,
            "retrieve",
            side_effect=AssertionError("must replay local terminal"),
        ):
            self.runtime.observe()

    def test_invalid_json_output_cannot_finish_as_valid_result(self):
        self.start()
        self.client.finish(output="not JSON")
        self.assertEqual(self.runtime.observe()["phase"], "invalid_output")
        self.assertFalse((self.path / "result.json").exists())

    def test_final_answer_must_match_completed_root_turn(self):
        self.start()
        self.client.finish()
        self.client.item_rows[0]["turn_id"] = "other_turn"
        self.assertEqual(self.runtime.observe()["phase"], "invalid_output")

    def test_commentary_cannot_be_treated_as_final_answer(self):
        self.start()
        self.client.finish()
        self.client.item_rows[0]["phase"] = "commentary"
        self.assertEqual(self.runtime.observe()["phase"], "invalid_output")

    def test_cancel_ack_not_proof_of_remote_stop_and_never_replayed(self):
        self.start()
        self.now = 1121
        result = self.runtime.observe()
        self.assertEqual(result["cancel"]["state"], "acknowledged_not_confirmed")
        self.assertFalse(result["remote_stop_confirmed"])
        self.runtime.observe()
        self.assertEqual(self.client.cancel_count, 1)
        self.client.finish("cancelled")
        self.assertTrue(self.runtime.observe()["remote_stop_confirmed"])

    def test_cancel_unknown_does_not_duplicate_mutation(self):
        self.start()
        self.client.fail_cancel = True
        self.assertEqual(self.runtime.cancel()["cancel"]["state"], "outcome_unknown")
        self.runtime.cancel()
        self.assertEqual(self.client.cancel_count, 1)

    def test_poll_disconnect_preserves_remote_pointer(self):
        self.start()
        self.client.fail_read = True
        with self.assertRaises(OSError):
            self.runtime.observe()
        self.client.fail_read = False
        self.runtime.observe()
        self.assertEqual(self.client.create_count, 1)

    def test_required_action_never_executes_tools(self):
        self.start()
        self.client.session.update(
            status="requires_action", required_actions=[{"type": "function_call"}]
        )
        self.assertEqual(self.runtime.observe()["phase"], "reconciliation_required")
        self.assertEqual(self.client.cancel_count, 1)

    def test_subagent_failure_not_hidden_by_root_success(self):
        self.start()
        self.client.finish()
        self.client.turn_rows.append(
            {
                "id": "turn_child",
                "session_id": "as_test",
                "subagent_id": "child",
                "status": "failed",
                "usage": None,
            }
        )
        self.assertEqual(self.runtime.observe()["reason"], "SUBAGENT_TURN_FAILED")

    def test_unknown_usage_is_not_zero_or_final_bill(self):
        self.start()
        result = self.runtime.observe()
        self.assertIsNone(result["observation"]["usage"])
        self.assertFalse(result["observation"]["usage_is_final_bill"])

    def test_context_tampering_rejected_before_network(self):
        packet = deepcopy(self.packet)
        packet["request"]["agent"]["tools"] = [{"type": "web_search"}]
        with self.assertRaisesRegex(ServiceError, "REQUEST_DRIFT"):
            SessionLedger.prepare(self.path.parent / "other", packet)
        self.assertEqual(self.client.create_count, 0)

    def test_effective_cloud_config_drift_retains_session_for_recovery(self):
        self.client.session["environment"] = {"type": "openai_hosted"}
        with self.assertRaises(ServiceError):
            self.start()
        self.assertEqual(self.ledger.status()["session_id"], "as_test")
        self.assertEqual(self.ledger.status()["phase"], "reconciliation_required")
        self.assertEqual(self.client.cancel_count, 1)

    def test_created_response_rejection_retains_identity_and_cancels_once(self):
        for failure in ("malformed_usage", "effective_tools_changed"):
            with self.subTest(failure=failure):
                session = deepcopy(self.client.session)
                session.update(created_at=1, last_active_at=2, metadata={}, error=None)
                session["agent"]["id"] = "agent_fixture"
                if failure == "malformed_usage":
                    session["usage"] = {}
                else:
                    session["agent"]["tools"] = [
                        {"type": "programmatic_tool_calling", "enabled": True}
                    ]
                calls = []

                def transport(method, url, headers, body, timeout):
                    calls.append((method, url, headers, body))
                    if url == BASE_URL:
                        return 201, {"Content-Type": "application/json"}, json.dumps(session).encode()
                    return 202, {}, b""

                ledger = SessionLedger.prepare(self.path.parent / failure, self.packet)
                runtime = ManagedResearch(
                    ledger, AgentsClient("fixture-secret", transport), clock=lambda: self.now
                )
                with self.assertRaisesRegex(ServiceError, "CREATE_RECONCILIATION"):
                    runtime.submit(live=True, acknowledge_cost_risk=True)
                status = ledger.status()
                self.assertEqual(status["session_id"], "as_test")
                self.assertEqual(status["phase"], "reconciliation_required")
                self.assertEqual(status["cancel"]["state"], "acknowledged_not_confirmed")
                self.assertFalse(status["remote_stop_confirmed"])
                self.assertEqual([row[:2] for row in calls], [
                    ("POST", BASE_URL), ("POST", BASE_URL + "/as_test/events")
                ])
                self.assertEqual(json.loads(calls[1][3]), {
                    "events": [{"type": "agent.session.input.cancel"}]
                })
                with self.assertRaisesRegex(ServiceError, "ALREADY_ATTEMPTED"):
                    runtime.submit(live=True, acknowledge_cost_risk=True)
                runtime.cancel()
                self.assertEqual(len(calls), 2)

    def test_effective_programmatic_execution_must_be_explicitly_disabled(self):
        missing = object()
        for tools in (missing, [], None, [{"type": "programmatic_tool_calling"}],
                      [{"type": "programmatic_tool_calling", "enabled": True}],
                      [{"type": "programmatic_tool_calling", "enabled": 0}],
                      [{"type": "programmatic_tool_calling", "enabled": False},
                       {"type": "web_search"}]):
            session = deepcopy(self.client.session)
            if tools is missing:
                session["agent"].pop("tools")
            else:
                session["agent"]["tools"] = tools
            with self.subTest(tools=tools):
                with self.assertRaisesRegex(ServiceError, "EFFECTIVE_CONFIGURATION"):
                    _effective_session(session, self.packet)

    def test_watch_read_failure_attempts_cancel_before_exiting(self):
        self.start()
        self.client.fail_read = True
        with self.assertRaisesRegex(ServiceError, "CHECK_REMOTE_STATE"):
            self.runtime.watch(max_polls=2, sleep=lambda _: None)
        self.assertEqual(self.client.cancel_count, 1)
        self.assertFalse(self.ledger.status()["remote_stop_confirmed"])

    def test_watch_polls_are_bounded_and_exhaustion_requests_cancel(self):
        self.start()
        progress = []
        result = self.runtime.watch(
            max_polls=2, sleep=lambda _: None, progress=progress.append
        )
        self.assertEqual(len(progress), 2)
        self.assertEqual(self.client.cancel_count, 1)
        self.assertFalse(result["remote_stop_confirmed"])

    def test_watch_interruption_attempts_cancel(self):
        self.start()

        def interrupt(_):
            raise KeyboardInterrupt()

        with self.assertRaisesRegex(ServiceError, "CHECK_REMOTE_STATE"):
            self.runtime.watch(max_polls=2, sleep=interrupt)
        self.assertEqual(self.client.cancel_count, 1)

    def test_effective_output_schema_drift_requests_cancel(self):
        self.client.session["agent"]["text"] = {"format": {"type": "text"}}
        with self.assertRaises(ServiceError):
            self.start()
        self.assertEqual(self.client.cancel_count, 1)

    def test_effective_config_rejects_bool_integer_substitution(self):
        mutations = (
            lambda s: s["agent"]["multi_agent"].update(enabled=0),
            lambda s: s["agent"]["text"]["format"]["schema"].update(
                additionalProperties=0
            ),
        )
        for mutate in mutations:
            session = deepcopy(self.client.session)
            mutate(session)
            with self.subTest(mutation=mutate):
                with self.assertRaisesRegex(ServiceError, "EFFECTIVE_CONFIGURATION"):
                    _effective_session(session, self.packet)

    def test_effective_subagent_count_is_integer_not_true(self):
        packet = deepcopy(self.packet)
        packet["request"]["agent"]["multi_agent"] = {
            "enabled": True,
            "max_concurrent_subagents": 1,
        }
        session = deepcopy(self.client.session)
        session["agent"]["multi_agent"] = {
            "enabled": True,
            "max_concurrent_subagents": True,
        }
        with self.assertRaisesRegex(ServiceError, "SUBAGENT_LIMIT"):
            _effective_session(session, packet)
        session["agent"]["multi_agent"] = {
            "enabled": 1,
            "max_concurrent_subagents": 1,
        }
        with self.assertRaisesRegex(ServiceError, "EFFECTIVE_CONFIGURATION"):
            _effective_session(session, packet)

    def test_effective_malformed_nested_config_has_safe_typed_failure(self):
        for field in ("text", "multi_agent"):
            session = deepcopy(self.client.session)
            session["agent"][field] = None
            with self.subTest(field=field):
                with self.assertRaisesRegex(ServiceError, "EFFECTIVE_CONFIGURATION"):
                    _effective_session(session, self.packet)

    def test_late_effective_drift_quarantines_and_cancels_known_session(self):
        self.start()
        self.client.session["environment"] = {"type": "openai_hosted"}
        with self.assertRaisesRegex(ServiceError, "EFFECTIVE_CONFIGURATION"):
            self.runtime.observe()
        status = self.ledger.status()
        self.assertEqual(status["phase"], "reconciliation_required")
        self.assertEqual(status["session_id"], "as_test")
        self.assertFalse(status["remote_stop_confirmed"])
        self.assertEqual(self.client.cancel_count, 1)
        with self.assertRaises(ServiceError):
            self.runtime.observe()
        self.assertEqual(self.client.cancel_count, 1)

    def test_wrong_observed_id_cancels_original_session_not_untrusted_id(self):
        self.start()
        self.client.session["id"] = "other_session"
        with patch.object(self.client, "cancel", wraps=self.client.cancel) as cancel:
            with self.assertRaisesRegex(ServiceError, "SESSION_ID_MISMATCH"):
                self.runtime.observe()
        self.assertEqual(cancel.call_args.args[0], "as_test")
        self.assertEqual(self.ledger.status()["phase"], "reconciliation_required")
        self.assertFalse(self.ledger.status()["remote_stop_confirmed"])

    def test_transport_identity_rejection_cancels_known_session_once(self):
        from researcher.service.openai_agents import AgentsError

        self.start()
        self.client.fail_cancel = True
        with patch.object(
            self.client,
            "retrieve",
            side_effect=AgentsError("SESSION_ID_MISMATCH", False),
        ):
            for _ in range(2):
                with self.assertRaises(AgentsError):
                    self.runtime.observe()
        status = self.ledger.status()
        self.assertEqual(status["session_id"], "as_test")
        self.assertEqual(status["phase"], "reconciliation_required")
        self.assertEqual(status["cancel"]["state"], "outcome_unknown")
        self.assertFalse(status["remote_stop_confirmed"])
        self.assertEqual(self.client.cancel_count, 1)

    def test_interrupt_after_create_keeps_known_id_and_cancels(self):
        save = self.ledger.save
        interrupted = False

        def interrupt_once(state):
            nonlocal interrupted
            if state["phase"] == "running" and not interrupted:
                interrupted = True
                raise KeyboardInterrupt()
            save(state)

        with patch.object(self.ledger, "save", side_effect=interrupt_once):
            with self.assertRaises(BaseException) as raised:
                self.start()
        self.assertIsInstance(raised.exception, ServiceError)
        self.assertEqual(self.ledger.status()["session_id"], "as_test")
        self.assertEqual(self.ledger.status()["phase"], "reconciliation_required")
        self.assertEqual(self.client.cancel_count, 1)
        self.assertFalse(self.ledger.status()["remote_stop_confirmed"])

    def test_failed_session_without_turn_history_cannot_confirm_stop(self):
        self.start()
        self.client.session["status"] = "failed"
        status = self.runtime.observe()
        self.assertEqual(status["phase"], "reconciliation_required")
        self.assertFalse(status["remote_stop_confirmed"])
        self.assertEqual(self.client.cancel_count, 1)

    def test_cancelled_root_does_not_hide_running_subagent(self):
        self.start()
        self.runtime.cancel()
        self.client.finish("cancelled")
        self.client.turn_rows.append(
            {
                "id": "turn_child",
                "session_id": "as_test",
                "subagent_id": "child",
                "status": "in_progress",
                "usage": None,
            }
        )
        self.assertFalse(self.runtime.observe()["remote_stop_confirmed"])
        self.client.turn_rows[-1]["status"] = "cancelled"
        status = self.runtime.observe()
        self.assertEqual(status["phase"], "cancelled")
        self.assertTrue(status["remote_stop_confirmed"])
        self.assertEqual(self.client.cancel_count, 1)

    def test_packet_digest_tamper_denied(self):
        packet = deepcopy(self.packet)
        packet["query"] = "tampered"
        (self.path / "packet.json").write_text(json.dumps(packet))
        with self.assertRaises(ServiceError):
            self.ledger.load()

    def test_terminal_result_digest_tamper_denied(self):
        self.start()
        self.client.finish()
        self.runtime.observe()
        (self.path / "result.json").write_text("{}")
        with self.assertRaisesRegex(ServiceError, "RESULT_DIGEST"):
            self.ledger.status()

    def test_two_workers_are_exclusive(self):
        with self.ledger.lock():
            with self.assertRaisesRegex(ServiceError, "WORKER_ALREADY"):
                with SessionLedger(self.path).lock():
                    self.fail("duplicate lock")

    def test_clock_rollback_does_not_extend_deadline(self):
        self.start()
        self.now = 999
        with self.assertRaisesRegex(ServiceError, "CLOCK_MOVED"):
            self.runtime.observe()

    def test_clock_rollback_does_not_block_cancellation(self):
        self.start()
        self.now = 999
        self.runtime.cancel()
        self.assertEqual(self.client.cancel_count, 1)

    def test_failed_session_with_running_turn_does_not_confirm_stop(self):
        self.start()
        self.client.finish("in_progress")
        self.client.session["status"] = "failed"
        result = self.runtime.observe()
        self.assertEqual(result["phase"], "reconciliation_required")
        self.assertFalse(result["remote_stop_confirmed"])
        self.assertEqual(self.client.cancel_count, 1)

    def test_safe_id_on_invalid_create_response_is_retained_and_cancelled(self):
        class KnownFailure(Exception):
            session_id = "as_known"

        with patch.object(self.client, "create", side_effect=KnownFailure):
            with self.assertRaises(ServiceError):
                self.start()
        self.assertEqual(self.ledger.status()["session_id"], "as_known")
        self.assertEqual(self.client.cancel_count, 1)

    def test_fixture_cannot_be_submitted(self):
        packet = deepcopy(self.packet)
        packet["fixture"] = True
        other = SessionLedger.prepare(self.path.parent / "fixture", packet)
        with self.assertRaisesRegex(ServiceError, "FIXTURE_CANNOT"):
            ManagedResearch(other, self.client).submit(
                live=True, acknowledge_cost_risk=True
            )


class PaginationTests(unittest.TestCase):
    def test_pagination_reads_all_pages(self):
        pages = {
            None: {"data": [{"id": "one"}], "last_id": "one", "has_more": True},
            "one": {"data": [{"id": "two"}], "has_more": False},
        }
        self.assertEqual(len(_pages(pages.__getitem__)), 2)

    def test_duplicate_records_and_cursor_cycles_fail_closed(self):
        with self.assertRaises(ServiceError):
            _pages(
                lambda _: {"data": [{"id": "one"}], "last_id": "one", "has_more": True}
            )

    def test_unknown_more_flag_and_empty_continuation_rejected(self):
        for page in [
            {"data": [], "has_more": 0},
            {"data": [], "has_more": True, "last_id": "one"},
        ]:
            with self.assertRaises(ServiceError):
                _pages(lambda _: page)


if __name__ == "__main__":
    unittest.main()
