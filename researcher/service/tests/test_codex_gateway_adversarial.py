"""Independent SDK boundary regressions; no paid providers or actual keys."""
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from researcher.service import codex_gateway as gateway_module
from researcher.service.codex_campaign import CodexCampaign
from researcher.service.codex_gateway import Gateway, validate_stream
from researcher.service.contracts import ServiceError
from researcher.service.openai_campaign import initialize
from researcher.service.tests.test_codex_campaign import official_shaped_upstream, task, upstream, wire

FIXTURE_CREDENTIAL = "synthetic-boundary-credential"
SDK_PYTHON = os.environ.get("CODEX_WORKER_TEST_PYTHON")


class GatewayAdversarialTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name).resolve() / "authority"
        self.store = initialize(self.directory, cap_microusd=100_000_000, prior_spend_microusd=0)

    def start_job(self):
        self.store.enqueue("proof", {"fixture": True})
        self.store.next_job("proof")

    def gateway(self, calls, *, transport=None):
        return Gateway(self.store, "proof", task(), credential=FIXTURE_CREDENTIAL,
                       transport=transport or (lambda *_a, **_kw: calls.append(1) or upstream()),
                       now=lambda: 1790683200)

    def test_recreated_gateway_cannot_redispatch_completed_effect_without_reservation(self):
        self.start_job()
        calls = []
        raw = json.dumps(wire()).encode()
        with self.store.worker_lock():
            self.gateway(calls).exchange(raw)
            with self.assertRaises(ServiceError):
                self.gateway(calls).exchange(raw)
        self.assertEqual(calls, [1], "a completed reservation is not permission for a second dispatch")
        effects = self.store.inspect("proof")["effects"]
        self.assertEqual(len(effects), 1)
        self.assertEqual(effects[0]["state"], "completed")

    def test_recreated_gateway_cannot_retry_unknown_dispatch(self):
        self.start_job()
        calls = []
        def dropped(*_a, **_kw):
            calls.append(1)
            raise OSError("synthetic response lost")
        with self.store.worker_lock():
            with self.assertRaises(ServiceError):
                self.gateway(calls, transport=dropped).exchange(json.dumps(wire()).encode())
            with self.assertRaises(ServiceError):
                self.gateway(calls).exchange(json.dumps(wire()).encode())
        self.assertEqual(calls, [1])
        self.assertEqual(self.store.inspect("proof")["effects"][0]["state"], "unknown")

    def test_external_float_metadata_does_not_relax_integer_usage(self):
        raw = official_shaped_upstream()
        for field, old in (("input_tokens", b"12"), ("output_tokens", b"4"),
                           ("total_tokens", b"16"), ("cached_tokens", b"0"), ("reasoning_tokens", b"0")):
            for value in (b"12.0", b"1.2e1", b"true", b"-1", b"-0", b'"12"',
                          b"9007199254740992", b"NaN", b"1e309"):
                target = b'"' + field.encode() + b'": ' + old
                changed = raw.replace(target, b'"' + field.encode() + b'": ' + value)
                self.assertNotEqual(changed, raw)
                with self.subTest(field=field, value=value), self.assertRaises(ServiceError):
                    validate_stream(changed, task(), input_ceiling=1000)

    def test_external_json_duplicate_nonfinite_and_surrogate_are_safe_refusals(self):
        raw = official_shaped_upstream()
        additions = (b'"metadata": {"private-sentinel":0,"private-sentinel":1}',
                     b'"metadata": {"value":NaN}', b'"metadata": {"value":Infinity}',
                     b'"metadata": {"value":-Infinity}', b'"metadata": {"value":1e309}',
                     b'"metadata": {"value":-1e309}', b'"metadata": {"value":"\\ud800"}',
                     b'"metadata": {"value":')
        for replacement in additions:
            changed = raw.replace(b'"metadata": {}', replacement)
            with self.subTest(replacement=replacement), self.assertRaises(ServiceError) as caught:
                validate_stream(changed, task(), input_ceiling=1000)
            self.assertEqual(caught.exception.code, "CODEX_GATEWAY_SSE_JSON_INVALID")
            self.assertNotIn("private-sentinel", str(caught.exception))

    def test_external_event_depth_and_node_limits_remain_bounded(self):
        raw = official_shaped_upstream()
        nested = b'"metadata": ' + b'[' * 65 + b'0' + b']' * 65
        with self.assertRaisesRegex(ServiceError, "SSE_JSON_LIMIT"):
            validate_stream(raw.replace(b'"metadata": {}', nested), task(), input_ceiling=1000)
        with patch.object(gateway_module, "MAX_EVENT_NODES", 16), self.assertRaisesRegex(ServiceError, "SSE_JSON_LIMIT"):
            validate_stream(raw, task(), input_ceiling=1000)

    def test_malformed_external_json_retains_unknown_effect_and_cannot_retry(self):
        self.start_job()
        calls = []
        def malformed(*_a, **_kw):
            calls.append(1)
            return official_shaped_upstream().replace(b'"temperature": 1.0', b'"temperature": NaN')
        with self.store.worker_lock():
            with self.assertRaisesRegex(ServiceError, "SSE_JSON_INVALID"):
                self.gateway(calls, transport=malformed).exchange(json.dumps(wire()).encode())
            with self.assertRaises(ServiceError):
                self.gateway(calls).exchange(json.dumps(wire()).encode())
        self.assertEqual(calls, [1])
        effect = self.store.inspect("proof")["effects"][0]
        self.assertEqual(effect["state"], "unknown")
        self.assertGreater(effect["reserved_microusd"], 0)

    def test_known_credential_never_enters_manifest_or_progress(self):
        for location in ("prompt", "instructions", "campaign", "item", "binding"):
            with self.subTest(location=location), tempfile.TemporaryDirectory() as temporary:
                directory = Path(temporary).resolve() / "authority"
                initialize(directory, cap_microusd=100_000_000, prior_spend_microusd=0)
                events, calls = [], []
                def refused_worker(*_a, **_kw):
                    calls.append(1)
                    raise AssertionError("worker must not start")
                campaign = CodexCampaign(directory, sdk_python="/usr/bin/true",
                    credential=FIXTURE_CREDENTIAL, worker=refused_worker,
                    transport=lambda *_a, **_kw: self.fail("provider must not run"),
                    progress=events.append, now=lambda: 1790683200)
                values = {"campaign": "safe", "item": "safe", "instructions": "Return JSON.",
                          "prompt": "Safe task", "binding": None}
                values[location] = {"nested": FIXTURE_CREDENTIAL} if location == "binding" else FIXTURE_CREDENTIAL
                with self.assertRaises(ServiceError) as error:
                    campaign.call(**values)
                self.assertEqual(error.exception.code, "CREDENTIAL_IN_CONTEXT")
                self.assertEqual(events, [])
                self.assertEqual(calls, [])
                with campaign.store._history_snapshot() as db:
                    self.assertEqual(db.execute("SELECT count(*) FROM jobs").fetchone()[0], 0)
                    self.assertEqual(db.execute("SELECT count(*) FROM effects").fetchone()[0], 0)

    def test_escaped_credential_in_final_text_rejected_without_receipt(self):
        self.start_job()
        escaped = ''.join('\\u%04x' % ord(char) for char in FIXTURE_CREDENTIAL)
        with self.assertRaises(ServiceError):
            self.gateway([], transport=lambda *_a, **_kw: upstream('{"nested":"' + escaped + '"}'))\
                .exchange(json.dumps(wire()).encode())
        with self.store._history_snapshot() as db:
            row = db.execute("SELECT state,output FROM effects").fetchone()
            self.assertEqual(row["state"], "unknown")
            self.assertIsNone(row["output"])

    def test_commit_then_lost_local_ack_does_not_erase_completed_effect(self):
        self.start_job()
        calls = []
        with patch.object(gateway_module, "sdk_stream", side_effect=OSError("synthetic local ACK failure")):
            with self.assertRaises(ServiceError):
                self.gateway(calls).exchange(json.dumps(wire()).encode())
        self.assertEqual(calls, [1])
        self.assertEqual(self.store.inspect("proof")["effects"][0]["state"], "completed")

    def test_forward_transport_rejects_ambiguous_or_unsupported_framing(self):
        body = upstream()
        for framing in ({"Content-Length": str(len(body)), "Transfer-Encoding": "chunked"},
                        {"Transfer-Encoding": "gzip"}):
            with self.subTest(framing=framing):
                packet = {"body": "{}", "credential": FIXTURE_CREDENTIAL, "timeout": 1}
                stdin = type("Input", (), {"buffer": io.BytesIO(json.dumps(packet).encode())})()
                output = io.BytesIO()
                stdout = type("Output", (), {"buffer": output})()
                headers = {"Content-Type": "text/event-stream", **framing}
                with patch.object(gateway_module.sys, "stdin", stdin), patch.object(gateway_module.sys, "stdout", stdout),\
                     patch("researcher.service.providers._https_post", return_value=(200, headers, body)):
                    status = gateway_module._forward_child()
                self.assertNotEqual(status, 0)
                self.assertEqual(output.getvalue(), b"")

    def test_completed_frame_must_be_final_and_usage_cannot_exceed_cap(self):
        valid = upstream()
        for raw in (valid + valid, valid[:-1], upstream(usage={"input_tokens": 12, "output_tokens": 257, "total_tokens": 269})):
            with self.subTest(length=len(raw)), self.assertRaises(ServiceError):
                validate_stream(raw, task(), input_ceiling=1000)


@unittest.skipUnless(SDK_PYTHON, "explicit pinned SDK interpreter required")
class RealSDKGatewayAdversarialTests(unittest.TestCase):
    def test_real_gpt6_tool_attempt_never_reaches_worker_and_cannot_retry(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary).resolve() / "authority"
            initialize(directory, cap_microusd=100_000_000, prior_spend_microusd=0)
            calls = []
            def malicious_tool_response(body, **_options):
                calls.append(json.loads(body))
                return upstream(output=[{"type": "function_call", "id": "fc_attack",
                    "call_id": "call_attack", "name": "exec_command",
                    "arguments": '{"cmd":"touch forbidden-marker"}'}])
            campaign = CodexCampaign(directory, sdk_python=SDK_PYTHON, credential=FIXTURE_CREDENTIAL,
                transport=malicious_tool_response, progress=lambda _: None, now=lambda: 1790683200)
            for _ in range(2):
                with self.assertRaises(ServiceError):
                    campaign.call("attack", "researcher", instructions="Return JSON only.", prompt="An inert source.")
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0]["tools"], [])
            self.assertEqual(calls[0]["tool_choice"], "none")
            self.assertNotIn("additional_tools", json.dumps(calls[0]))
            self.assertEqual(campaign.status()["attempted_calls"], 1)
            self.assertEqual(campaign.status()["unresolved_calls"], 1)
            with campaign.store._history_snapshot() as db:
                effect = db.execute("SELECT state,output FROM effects").fetchone()
                self.assertEqual(effect["state"], "unknown")
                self.assertIsNone(effect["output"])


if __name__ == "__main__":
    unittest.main()
