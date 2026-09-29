"""SDK gateway, immutable-turn and real SDK integration proofs. No provider calls."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from researcher.service.codex_campaign import CodexCampaign
from researcher.service.codex_gateway import BASE_INSTRUCTIONS, Gateway, project_request, sdk_stream, validate_stream
from researcher.service.contracts import ServiceError, digest
from researcher.service.openai_campaign import Campaign, PRICING, initialize
from researcher.service.tests.test_codex_worker import stream

SDK_PYTHON = os.environ.get("CODEX_WORKER_TEST_PYTHON")


def task():
    return {"model": PRICING["model"], "prompt": "Return a source-bound result.",
            "reasoning_effort": "low", "max_output_tokens": 256}


def wire(value=None):
    value = value or task()
    return {"model": value["model"], "instructions": BASE_INSTRUCTIONS,
        "input": [{"type": "message", "id": "msg_" + str(i), "role": role,
                   "content": [{"type": "input_text", "text": text}]} for i, (role, text) in enumerate([
            ("developer", "<permissions instructions>restricted</permissions instructions>"),
            ("user", "<environment_context>/private/host/secret/path</environment_context>"),
            ("user", value["prompt"])])],
        "tools": [{"type": kind, "name": name} for kind, name in [
            ("function", "request_user_input"), ("custom", "apply_patch"), ("function", "view_image")]],
        "tool_choice": "auto", "parallel_tool_calls": True, "reasoning": {"effort": "low"},
        "store": False, "stream": True, "include": ["reasoning.encrypted_content"],
        "prompt_cache_key": "private-thread", "client_metadata": {"private": "host"},
        "text": {"verbosity": "low"}}


def upstream(text='{"ok":true}', **changes):
    item = {"type": "message", "id": "msg_fixture", "role": "assistant", "status": "completed",
            "content": [{"type": "output_text", "text": text, "annotations": []}]}
    raw = stream(item, "resp_sdk_fixture")
    events = [json.loads(record.split(b"data: ", 1)[1]) for record in raw.split(b"\n\n") if record]
    events[-1]["response"].update({"object": "response", "model": PRICING["model"], "service_tier": "default", **changes})
    return b"".join(b"event: " + row["type"].encode() + b"\ndata: " + json.dumps(row).encode() + b"\n\n" for row in events)


def official_shaped_upstream(text='{"ok":true}'):
    """Synthetic content, official Responses streaming envelope shape.

    https://developers.openai.com/api/reference/typescript/resources/beta/subresources/responses/methods/create
    External envelope metadata is JSON, not our integer-only receipt profile.
    """
    events = [json.loads(record.split(b"data: ", 1)[1])
              for record in upstream(text).split(b"\n\n") if record]
    metadata = {"object": "response", "created_at": 1790683200, "model": PRICING["model"],
        "temperature": 1.0, "top_p": 0.95, "error": None, "incomplete_details": None,
        "service_tier": "default", "parallel_tool_calls": False, "tools": [], "tool_choice": "none",
        "store": False, "text": {"format": {"type": "text"}}, "metadata": {}}
    for event in (events[0], events[-1]):
        event["response"].update(metadata)
    events.insert(1, {"type": "response.in_progress", "response": dict(events[0]["response"])})
    events.insert(3, {"type": "response.output_text.delta", "item_id": "msg_fixture", "output_index": 0,
        "content_index": 0, "delta": text, "logprobs": [{"token": "fixture", "logprob": -0.125,
            "bytes": [102], "top_logprobs": []}]})
    for number, event in enumerate(events):
        event["sequence_number"] = number
    return b"".join(b"event: " + row["type"].encode() + b"\ndata: " + json.dumps(row).encode() + b"\n\n"
                    for row in events)


class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name).resolve() / "authority"
        self.store = initialize(self.directory, cap_microusd=100_000_000, prior_spend_microusd=0)
        self.store.enqueue("proof", {"fixture": True})
        self.store.next_job("proof")

    def gateway(self, transport=None):
        return Gateway(self.store, "proof", task(), credential="private-provider-secret",
                       transport=transport or (lambda *_a, **_k: upstream()), now=lambda: 1790683200)

    def test_projection_drops_tools_and_ambient_identity_sets_paid_limits(self):
        body = project_request(json.dumps(wire()).encode(), task())
        value = json.loads(body)
        self.assertEqual(value["tools"], [])
        self.assertEqual(value["tool_choice"], "none")
        self.assertEqual(value["max_output_tokens"], 256)
        self.assertEqual(value["service_tier"], "default")
        self.assertNotIn(b"/private/host", body)
        self.assertNotIn("prompt_cache_key", value)
        self.assertNotIn("client_metadata", value)

    def test_changed_request_before_effect(self):
        mutations = [{"model": "other"}, {"stream": False}, {"store": True}, {"input": []},
                     {"reasoning": {"effort": "high"}}, {"tools": []}, {"previous_response_id": "old"},
                     {"text": {"format": {"type": "json_object"}}}]
        for mutation in mutations:
            with self.subTest(mutation=mutation), self.assertRaises(ServiceError):
                project_request(json.dumps({**wire(), **mutation}).encode(), task())

    def test_duplicate_keys_rejected(self):
        with self.assertRaises(ServiceError):
            project_request(b'{"model":"a","model":"b"}', task())

    def test_receipt_committed_before_sdk_gets_stream(self):
        gateway = self.gateway()
        raw = gateway.exchange(json.dumps(wire()).encode())
        self.assertEqual(self.store.inspect("proof")["effects"][0]["state"], "completed")
        self.assertIn(b"response.completed", raw)
        self.assertEqual(gateway.receipt["backend"], "codex_sdk")
        self.assertEqual(Campaign(self.directory, progress=lambda _: None).status()["attempted_calls"], 1)

    def test_retry_denied_no_second_provider_request(self):
        calls = []
        gateway = self.gateway(lambda *_a, **_k: calls.append(1) or upstream())
        gateway.exchange(json.dumps(wire()).encode())
        with self.assertRaises(ServiceError):
            gateway.exchange(json.dumps(wire()).encode())
        self.assertEqual(calls, [1])
        self.assertEqual(gateway.error, "CODEX_GATEWAY_SECOND_REQUEST_FORBIDDEN")

    def test_unknown_stream_keeps_reservation(self):
        gateway = self.gateway(lambda *_a, **_k: upstream()[:150])
        with self.assertRaises(ServiceError):
            gateway.exchange(json.dumps(wire()).encode())
        effect = self.store.inspect("proof")["effects"][0]
        self.assertEqual(effect["state"], "unknown")
        self.assertGreater(effect["reserved_microusd"], 0)

    def test_commit_failure_never_forwards_model_output(self):
        gateway = self.gateway()
        with patch.object(self.store, "complete_effect", side_effect=OSError("private")), self.assertRaises(ServiceError):
            gateway.exchange(json.dumps(wire()).encode())
        self.assertIsNone(gateway.receipt)
        self.assertEqual(self.store.inspect("proof")["effects"][0]["state"], "unknown")

    def test_tool_final_and_intermediate_are_rejected(self):
        for body in (upstream(output=[{"type": "function_call", "name": "exec_command"}]),
            b'event: response.output_item.added\ndata: {"type":"response.output_item.added","item":{"type":"custom_tool_call"}}\n\n' + upstream()):
            with self.subTest(body=body[:30]), self.assertRaises(ServiceError):
                validate_stream(body, task(), input_ceiling=1000)

    def test_missing_or_lying_usage_and_model_rejected(self):
        for changes in ({"usage": None}, {"usage": {"input_tokens": 12, "output_tokens": 4, "total_tokens": 99}},
                        {"model": "different"}, {"service_tier": "priority"}, {"status": "incomplete"}):
            with self.subTest(changes=changes), self.assertRaises(ServiceError):
                validate_stream(upstream(**changes), task(), input_ceiling=1000)

    def test_observed_usage_details_survive_receipt_and_sdk_stream(self):
        usage = {"input_tokens": 20, "output_tokens": 10, "total_tokens": 30,
                 "input_tokens_details": {"cached_tokens": 8, "cache_write_tokens": 6},
                 "output_tokens_details": {"reasoning_tokens": 7}}
        gateway = self.gateway(lambda *_a, **_k: upstream(usage=usage))
        raw = gateway.exchange(json.dumps(wire()).encode())
        terminal = json.loads(raw.split(b"data: ")[-1])["response"]
        self.assertEqual(terminal["usage"], usage)
        self.assertEqual(gateway.receipt["schema"], "codex-gateway-receipt/v2")
        self.assertEqual(gateway.receipt["response"]["token_details"], {
            "cached_input_tokens": 8, "cache_write_input_tokens": 6, "reasoning_output_tokens": 7})
        from researcher.service.openai_campaign import _cost
        self.assertEqual(gateway.receipt["usage"]["estimated_upper_cost_microusd"], _cost(20, 10))

    def test_official_float_metadata_is_external_only_not_a_receipt_number(self):
        gateway = self.gateway(lambda *_a, **_k: official_shaped_upstream())
        gateway.exchange(json.dumps(wire()).encode())
        response = gateway.receipt["response"]
        self.assertEqual((response["input_tokens"], response["output_tokens"]), (12, 4))
        self.assertEqual(set(response), {"text", "input_tokens", "output_tokens", "model",
                                        "request_id", "service_tier", "token_details"})
        from researcher.scripts.schema_contract import canonicalize, parse_json_strict
        self.assertEqual(parse_json_strict(canonicalize(gateway.receipt).decode()), gateway.receipt)
        self.assertNotIn("temperature", response)
        self.assertNotIn("logprobs", response)

    def test_missing_and_null_usage_details_stay_unknown_not_zero(self):
        base = {"input_tokens": 20, "output_tokens": 10, "total_tokens": 30}
        for groups in ({}, {"input_tokens_details": None, "output_tokens_details": None},
                       {"input_tokens_details": {"cached_tokens": None, "cache_write_tokens": None},
                        "output_tokens_details": {"reasoning_tokens": None}}):
            with self.subTest(groups=groups):
                value = validate_stream(upstream(usage={**base, **groups}), task(), input_ceiling=1000)
                self.assertEqual(value["token_details"], dict.fromkeys(
                    ("cached_input_tokens", "cache_write_input_tokens", "reasoning_output_tokens")))
                terminal = json.loads(sdk_stream(value).split(b"data: ")[-1])["response"]
                self.assertEqual(terminal["usage"], base)
        value = validate_stream(upstream(usage={**base, "input_tokens_details": {"cached_tokens": 0}}),
                                task(), input_ceiling=1000)
        self.assertEqual(value["token_details"]["cached_input_tokens"], 0)
        terminal = json.loads(sdk_stream(value).split(b"data: ")[-1])["response"]
        self.assertEqual(terminal["usage"]["input_tokens_details"], {"cached_tokens": 0})
        self.assertNotIn("output_tokens_details", terminal["usage"])

    def test_malformed_usage_details_fail_closed(self):
        base = {"input_tokens": 20, "output_tokens": 10, "total_tokens": 30}
        for group, field, limit in (("input_tokens_details", "cached_tokens", 20),
                                    ("input_tokens_details", "cache_write_tokens", 20),
                                    ("output_tokens_details", "reasoning_tokens", 10)):
            for value in (False, True, -1, limit + 1, "0", 1.5, [], {}):
                with self.subTest(field=field, value=value), self.assertRaises(ServiceError):
                    validate_stream(upstream(usage={**base, group: {field: value}}), task(), input_ceiling=1000)
            for value in (False, 0, [], "private"):
                with self.subTest(group=group, value=value), self.assertRaises(ServiceError):
                    validate_stream(upstream(usage={**base, group: value}), task(), input_ceiling=1000)

    def test_secret_reflection_rejected_before_persistence(self):
        gateway = self.gateway(lambda *_a, **_k: upstream('private-provider-secret'))
        with self.assertRaises(ServiceError):
            gateway.exchange(json.dumps(wire()).encode())
        self.assertIsNone(gateway.receipt)

    def test_shared_budget_and_pause_prevent_dispatch(self):
        calls = []
        self.store.pause(True)
        with self.assertRaises(ServiceError):
            self.gateway(lambda *_a, **_k: calls.append(1)).exchange(json.dumps(wire()).encode())
        self.assertEqual(calls, [])


@unittest.skipUnless(SDK_PYTHON, "explicit pinned SDK interpreter required")
class RealSDKCampaignTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name).resolve() / "authority"
        initialize(self.directory, cap_microusd=100_000_000, prior_spend_microusd=1_000_000)
        self.calls = []
        def transport(body, **options):
            self.calls.append(json.loads(body))
            return upstream()
        self.campaign = CodexCampaign(self.directory, sdk_python=SDK_PYTHON,
            credential="fixture-key-not-a-provider-credential", transport=transport,
            progress=lambda _: None, now=lambda: 1790683200)

    def call(self, **changes):
        return self.campaign.call("proof", "researcher", instructions="Return JSON only.", prompt="Prove local execution.", **changes)

    def test_real_sdk_one_request_authority_origin_and_credential_free_replay(self):
        result = self.call()
        self.assertEqual(result["backend"], "codex_sdk")
        self.assertTrue(result["sdk"]["thread_id"])
        self.assertTrue(result["sdk"]["turn_id"])
        self.assertEqual(result["output_digest"], digest(result["response"]["text"]))
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.calls[0]["tools"], [])
        self.campaign.credential = None
        self.assertEqual(self.call(), result)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.campaign.status()["prior_spend_microusd"], 1_000_000)

    def test_real_sdk_official_shaped_external_sse_and_receipt_replay(self):
        def transport(body, **options):
            self.calls.append(json.loads(body))
            return official_shaped_upstream()
        self.campaign.transport = transport
        result = self.call()
        self.assertEqual(result["response"]["text"], '{"ok":true}')
        self.assertTrue(result["sdk"]["thread_id"])
        self.assertTrue(result["sdk"]["turn_id"])
        self.assertEqual(result["usage"]["input_tokens"], 12)
        self.assertEqual(result["usage"]["output_tokens"], 4)
        self.campaign.credential = None
        self.assertEqual(self.call(), result)
        self.assertEqual(len(self.calls), 1)

    def test_changed_binding_cannot_reuse_receipt(self):
        self.call(binding={"source": "a"})
        with self.assertRaises(ServiceError):
            self.call(binding={"source": "b"})
        self.assertEqual(len(self.calls), 1)

    def test_real_sdk_detail_receipt_trace_and_export_preserve_observed_counts(self):
        from researcher.service import tracing, trace_export
        usage = {"input_tokens": 20, "output_tokens": 10, "total_tokens": 30,
                 "input_tokens_details": {"cached_tokens": 8, "cache_write_tokens": 6},
                 "output_tokens_details": {"reasoning_tokens": 7}}
        self.campaign.transport = lambda *_a, **_k: upstream(usage=usage)
        journal = tracing.TraceJournal(self.directory.parent / "telemetry")
        self.campaign.tracer = tracing.Tracer(journal)
        result = self.call()
        self.assertEqual(result["schema"], "codex-sdk-response/v2")
        details = {"cached_input_tokens": 8, "cache_write_input_tokens": 6, "reasoning_output_tokens": 7}
        self.assertEqual(result["response"]["token_details"], details)
        row = next(row for row in journal.rows() if row["operation"] == "sdk.turn")
        for key, value in details.items():
            self.assertEqual(row["attributes"][key], value)
        self.assertTrue(row["attributes"]["usage_details_known"])
        payload = tracing.otlp_payload(journal.rows())
        tracing.validate_otlp(payload)
        outbound = []
        def transport(url, headers, body, timeout):
            outbound.append(json.loads(body))
            return 200, {"Content-Type": "application/json"}, b"{}"
        exported = trace_export.export_payload(payload, credential="fixture-write-key",
            project_id="fixture-project", transport=transport)
        self.assertEqual(exported["status"], "exported")
        self.assertEqual(outbound, [payload])
        for private in (self.campaign.credential, result["sdk"]["thread_id"], result["sdk"]["turn_id"],
                        "Prove local execution.", "fixture-write-key"):
            self.assertNotIn(private, json.dumps(payload))
        # Reading the retained result neither executes another SDK turn nor
        # creates a second set of token metrics.
        before = journal.rows()
        self.campaign.credential = None
        self.assertEqual(self.call(), result)
        self.assertEqual(journal.rows(), before)

    def test_real_sdk_missing_detail_defaults_do_not_become_observed_zero_metrics(self):
        from researcher.service import tracing
        self.campaign.transport = lambda *_a, **_k: upstream(usage={
            "input_tokens": 20, "output_tokens": 10, "total_tokens": 30})
        journal = tracing.TraceJournal(self.directory.parent / "telemetry")
        self.campaign.tracer = tracing.Tracer(journal)
        result = self.call()
        self.assertTrue(all(value is None for value in result["response"]["token_details"].values()))
        row = next(row for row in journal.rows() if row["operation"] == "sdk.turn")
        self.assertFalse(row["attributes"]["usage_details_known"])
        self.assertFalse(set(result["response"]["token_details"]) & set(row["attributes"]))

    def test_known_sdk_detail_mismatch_keeps_provider_receipt_without_accepting_result(self):
        from researcher.service.codex_worker import run_worker
        def wrong(*args, **kwargs):
            result = run_worker(*args, **kwargs)
            result["usage"]["cachedInputTokens"] = 1
            return result
        self.campaign.worker = wrong
        with self.assertRaises(ServiceError):
            self.call()
        with self.assertRaises(ServiceError):
            self.call()
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.campaign.status()["sdk"]["unresolved_turns"], 1)

    def test_unknown_worker_after_provider_completion_is_never_retried(self):
        from researcher.service.codex_worker import run_worker
        def lost(*args, **kwargs):
            result = run_worker(*args, **kwargs)
            return {**result, "status": "unknown", "output_text": None}
        self.campaign.worker = lost
        with self.assertRaises(ServiceError):
            self.call()
        with self.assertRaises(ServiceError):
            self.call()
        self.assertEqual(len(self.calls), 1)

    def test_result_commit_survives_terminal_bookkeeping_failure(self):
        original = self.campaign.store.finish
        def finish(job, status, reason=None):
            if status == "execution_complete":
                raise OSError("lost status")
            return original(job, status, reason)
        with patch.object(self.campaign.store, "finish", side_effect=finish), self.assertRaises(ServiceError):
            self.call()
        self.assertEqual(self.call()["backend"], "codex_sdk")
        self.assertEqual(len(self.calls), 1)

    def test_tombstone_before_provider_dispatch_blocks_restart(self):
        def died(*_args, **_kwargs):
            raise OSError("process death")
        self.campaign.worker = died
        with self.assertRaises(ServiceError):
            self.call()
        with self.assertRaises(ServiceError):
            self.call()
        self.assertEqual(len(self.calls), 0)
        self.assertEqual(self.campaign.status()["sdk"]["unresolved_turns"], 1)

    def test_failed_evaluation_receipts_remain_in_denominator_and_verify_without_retry(self):
        from researcher.service.agents_evals import build_plan, fixture_dataset
        data = fixture_dataset()
        data["tasks"] = data["tasks"][:1]
        plan = build_plan(data, baseline_skill="baseline", candidate_skill="candidate",
                          model=PRICING["model"], replications=1)
        calls = []
        def died(*_args, **_kwargs):
            calls.append(1)
            raise OSError("worker interrupted")
        self.campaign.worker = died
        result = self.campaign.evaluate("failed-eval", plan)
        self.assertEqual(len(result["failures"]), 3)
        self.assertEqual(len(result["results"]), 3)
        self.campaign.verify_evaluation("failed-eval", plan, result)
        repeated = self.campaign.evaluate("failed-eval", plan)
        self.assertEqual(repeated["failures"], result["failures"])
        self.campaign.verify_evaluation("failed-eval", plan, repeated)
        self.campaign.verify_evaluation("failed-eval", plan, result)
        self.assertEqual(len(calls), 3)
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()
