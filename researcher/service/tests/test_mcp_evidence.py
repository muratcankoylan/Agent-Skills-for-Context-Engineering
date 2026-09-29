"""Offline synchronous MCP admission, evidence integrity, and effect ambiguity."""

import asyncio
from contextlib import asynccontextmanager
from copy import deepcopy
import traceback
import unittest
from unittest.mock import AsyncMock, patch

from researcher.scripts.schema_contract import canonicalize, sha256_bytes
from researcher.service.contracts import ServiceError
from researcher.service.mcp_evidence import (
    MAX_REQUESTS,
    MCPEvidenceError,
    collect_mcp,
    validate_read,
)
from researcher.service.mcp_tools import MCPToolError
from researcher.service.tests.test_mcp_tools import FakeSession, registration


def receipt(config=None, args=None, value=None):
    config = registration() if config is None else config
    args = {"query": "context"} if args is None else args
    value = {"text": "captured statement"} if value is None else value
    raw = canonicalize(value)
    return {
        "schema": "research-mcp-read/v1",
        "authority": "none",
        "registration_id": config["id"],
        "registration_sha256": sha256_bytes(canonicalize(config)),
        "tool": config["tool"],
        "protocol_version": config["protocol_version"],
        "arguments_sha256": sha256_bytes(canonicalize(args)),
        "value": value,
        "value_sha256": sha256_bytes(raw),
        "output_bytes": len(raw),
        "sdk_response_bytes": len(raw) + 80,
        "output_limit_scope": "post_sdk_parse",
        "observation_only": True,
        "tool_calls": 1,
        "model_calls": 0,
    }


class MCPEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.config = registration()
        self.args = {"query": "context"}
        self.gateway = AsyncMock(return_value=receipt())
        self.patch = patch("researcher.service.mcp_evidence.read_tool", self.gateway)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def collect(self, **kwargs):
        return collect_mcp(self.config, self.args, **kwargs)

    def assert_error(self, code, function, *, ambiguous=False, attempted=False):
        with self.assertRaises(MCPEvidenceError) as raised:
            function()
        error = raised.exception
        self.assertIsInstance(error, ServiceError)
        self.assertEqual(error.code, code)
        self.assertIs(error.ambiguous, ambiguous)
        self.assertIs(error.call_attempted, attempted)
        return error

    def test_normalized_literal_evidence_and_no_authority(self):
        result = self.collect()
        entry = result["evidence"][0]
        self.assertEqual(result["source"], "mcp:papers")
        self.assertEqual(result["state"], "observed")
        self.assertEqual(result["authority"], "none")
        self.assertEqual(entry["metadata"]["authority"], "none")
        self.assertEqual(entry["evidence_scope"], "mcp_observation")
        self.assertEqual(entry["text"], '{"text":"captured statement"}')
        self.assertEqual(entry["sha256"], sha256_bytes(entry["text"].encode()))
        self.assertEqual(result["output_sha256"], entry["sha256"])
        self.assertEqual(entry["url"], self.config["url"])
        self.assertFalse(result["semantic_quality_measured"])
        self.gateway.assert_awaited_once_with(self.config, self.args, credential=None)

    def test_request_ceiling_is_not_usage_or_free_cost_claim(self):
        result = self.collect()
        self.assertEqual(
            result["request_reservation"],
            {
                "source_requests": MAX_REQUESTS,
                "scope": "http_request_ceiling",
                "actual_requests_measured": False,
            },
        )
        self.assertEqual(MAX_REQUESTS, 12)
        self.assertEqual(result["cost_status"], "unknown")
        self.assertTrue(result["operator_cost_allowance_required"])
        self.assertEqual(result["tool_calls"], 1)
        self.assertEqual(result["model_calls"], 0)
        self.assertNotIn("paid_calls", result)
        self.assertNotIn("request_count", result)
        self.assertNotIn("captures", result)

    def test_deterministic_identity_binds_registration_arguments_and_output(self):
        original = self.collect()["evidence"][0]["id"]
        self.assertEqual(original, self.collect()["evidence"][0]["id"])
        for key in ("registration", "arguments", "output"):
            with self.subTest(key=key):
                config, args, value = (
                    registration(),
                    {"query": "context"},
                    {"text": "captured statement"},
                )
                if key == "registration":
                    config["id"] = "other"
                elif key == "arguments":
                    args["query"] = "memory"
                else:
                    value["text"] = "different"
                self.gateway.return_value = receipt(config, args, value)
                changed = collect_mcp(config, args)
                self.assertNotEqual(original, changed["evidence"][0]["id"])

    def test_unicode_canonical_text_has_exact_digest(self):
        value = {"text": 'Başlık 🧪 空間\nquote: "yes"'}
        self.gateway.return_value = receipt(value=value)
        entry = self.collect()["evidence"][0]
        self.assertEqual(entry["text"].encode("utf-8"), canonicalize(value))
        self.assertEqual(entry["sha256"], sha256_bytes(canonicalize(value)))

    def test_validation_has_no_gateway_dns_or_subprocess_calls(self):
        with (
            patch("socket.getaddrinfo", side_effect=AssertionError("DNS forbidden")),
            patch(
                "subprocess.Popen", side_effect=AssertionError("subprocess forbidden")
            ),
        ):
            self.assertIsNone(validate_read(self.config, self.args))
        self.gateway.assert_not_called()

    def test_service_slug_is_stricter_than_gateway_name(self):
        for invalid in ("Upper", "dots.id", "x" * 65, "papers\n"):
            with self.subTest(invalid=invalid):
                self.config["id"] = invalid
                self.assert_error("INVALID_REGISTRATION", self.collect)
        self.gateway.assert_not_called()

    def test_invalid_arguments_rejected_before_dispatch(self):
        for args in ({}, {"query": False}, {"query": "x", "extra": 1}, []):
            with self.subTest(args=args):
                self.args = args
                code = (
                    "INVALID_RECORD"
                    if isinstance(args, list)
                    else "INPUT_SCHEMA_MISMATCH"
                )
                self.assert_error(code, self.collect)
        self.gateway.assert_not_called()

    def test_closed_registration_and_unsafe_endpoint_rejected(self):
        self.config["extra"] = True
        self.assert_error("INVALID_REGISTRATION", self.collect)
        self.config = registration()
        self.config["url"] = "https://127.0.0.1/mcp"
        self.assert_error("UNSAFE_ENDPOINT", self.collect)
        self.gateway.assert_not_called()

    def test_remote_schema_reference_rejected_without_resolution(self):
        self.config["input_schema"]["properties"]["query"] = {
            "$ref": "https://example.org/schema"
        }
        with patch("socket.getaddrinfo", side_effect=AssertionError("DNS forbidden")):
            self.assert_error(
                "INVALID_SCHEMA", lambda: validate_read(self.config, self.args)
            )

    def test_oversized_or_invalid_observed_output_is_terminal_failure(self):
        self.gateway.return_value = receipt(value={"text": "x" * 5000})
        self.assert_error("OUTPUT_LIMIT", self.collect, attempted=True)
        self.gateway.return_value = receipt(value={"text": False})
        self.assert_error("OUTPUT_SCHEMA_MISMATCH", self.collect, attempted=True)

    def test_oversized_sdk_envelope_rejected_even_with_small_value(self):
        self.gateway.return_value["sdk_response_bytes"] = 4097
        self.assert_error("OUTPUT_LIMIT", self.collect, attempted=True)

    def test_counterfeit_receipt_or_authority_rejected(self):
        for key, value in (
            ("value_sha256", "sha256:" + "0" * 64),
            ("registration_sha256", "sha256:" + "0" * 64),
            ("arguments_sha256", "sha256:" + "0" * 64),
            ("authority", "accepted"),
            ("model_calls", False),
            ("observation_only", 1),
            ("output_bytes", True),
            ("tool", "write_papers"),
            ("extra", "unregistered"),
        ):
            with self.subTest(key=key):
                self.gateway.return_value = receipt()
                self.gateway.return_value[key] = value
                self.assert_error("MCP_RECEIPT_MISMATCH", self.collect, attempted=True)

    def test_explicit_credential_forwarded_but_never_returned(self):
        token = 'secret-quoted-"-token'
        result = self.collect(credential=token)
        self.gateway.assert_awaited_once_with(self.config, self.args, credential=token)
        self.assertNotIn(token, str(result))

    def test_escaped_credential_reflection_rejected_before_persistence(self):
        token = 'secret-quoted-"-token'
        self.gateway.return_value = receipt(value={"text": "echo " + token})
        error = self.assert_error(
            "CREDENTIAL_LEAK", lambda: self.collect(credential=token), attempted=True
        )
        self.assertNotIn(token, str(error))
        self.assertNotIn(token, repr(error))
        self.assertNotIn(token, "".join(traceback.format_exception(error)))

    def test_credential_in_decoded_arguments_rejected_before_dispatch(self):
        token = 'secret-quoted-"-token'
        self.args["query"] = token
        self.assert_error("CREDENTIAL_LEAK", lambda: self.collect(credential=token))
        self.gateway.assert_not_called()

    def test_invalid_credential_rejected_before_dispatch(self):
        for token in ("short", "line\nbreak", 42):
            with self.subTest(token=token):
                self.assert_error(
                    "INVALID_CREDENTIAL", lambda: self.collect(credential=token)
                )
        self.gateway.assert_not_called()

    def test_tool_error_ambiguity_preserved_without_retry(self):
        for attempted, unknown in ((False, False), (True, False), (True, True)):
            with self.subTest(attempted=attempted, unknown=unknown):
                self.gateway.reset_mock()
                self.gateway.side_effect = MCPToolError(
                    "TIMEOUT", call_attempted=attempted, outcome_unknown=unknown
                )
                self.assert_error(
                    "TIMEOUT", self.collect, ambiguous=unknown, attempted=attempted
                )
                self.gateway.assert_awaited_once()

    def test_generic_gateway_failure_is_safe_and_ambiguous(self):
        token = "private-exception-token"
        self.gateway.side_effect = RuntimeError(token)
        error = self.assert_error(
            "MCP_READ_FAILED", self.collect, ambiguous=True, attempted=True
        )
        self.assertNotIn(token, "".join(traceback.format_exception(error)))
        self.gateway.assert_awaited_once()

    def test_cancellation_is_quarantinable_service_error(self):
        self.gateway.side_effect = asyncio.CancelledError()
        self.assert_error(
            "MCP_READ_FAILED", self.collect, ambiguous=True, attempted=True
        )

    def test_active_event_loop_rejected_without_unawaited_coroutine(self):
        async def active():
            self.assert_error("ASYNC_CONTEXT_UNSUPPORTED", self.collect)

        asyncio.run(active())
        self.gateway.assert_not_called()

    def test_input_and_output_detached_from_caller_objects(self):
        initial = deepcopy(self.config)
        output = self.collect()
        self.config["id"] = "changed"
        self.gateway.return_value["value"]["text"] = "mutated"
        self.assertEqual(output["source"], "mcp:papers")
        self.assertIn("captured statement", output["evidence"][0]["text"])
        self.assertEqual(self.gateway.call_args.args[0], initial)

    def test_real_gateway_with_fake_session_not_network(self):
        self.patch.stop()
        session = FakeSession()

        @asynccontextmanager
        async def factory(**kwargs):
            yield session

        with (
            patch("researcher.service.mcp_tools._sdk_session", factory),
            patch("socket.getaddrinfo", side_effect=AssertionError("DNS forbidden")),
            patch(
                "subprocess.Popen", side_effect=AssertionError("subprocess forbidden")
            ),
        ):
            result = self.collect()
        self.assertEqual(session.calls, ["initialize", "tools/list", "tools/call"])
        self.assertEqual(result["authority"], "none")
        self.assertEqual(result["evidence"][0]["text"], '{"text":"captured statement"}')


if __name__ == "__main__":
    unittest.main()
