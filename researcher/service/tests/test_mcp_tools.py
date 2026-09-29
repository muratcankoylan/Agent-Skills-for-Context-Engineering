"""Offline policy contracts; no live MCP server, credentials or subprocesses."""

import asyncio
from contextlib import asynccontextmanager
from copy import deepcopy
import traceback
import unittest
from unittest.mock import AsyncMock, patch
from importlib.metadata import PackageNotFoundError
from types import ModuleType

from researcher.scripts.schema_contract import canonicalize, sha256_bytes
from researcher.service.mcp_tools import (
    MCPToolError,
    PROTOCOL_VERSION,
    read_tool,
    _sdk_session,
)


def registration():
    return {
        "id": "papers",
        "url": "https://research.example/mcp",
        "tool": "search_papers",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
            "additionalProperties": False,
        },
        "output_schema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
            "additionalProperties": False,
        },
        "max_output_bytes": 4096,
        "timeout_seconds": 1,
        "protocol_version": PROTOCOL_VERSION,
    }


class FakeSession:
    def __init__(self):
        reg = registration()
        self.calls = []
        self.initialized = {"protocolVersion": PROTOCOL_VERSION}
        self.listing = {
            "tools": [
                {
                    "name": reg["tool"],
                    "inputSchema": reg["input_schema"],
                    "outputSchema": reg["output_schema"],
                }
            ]
        }
        self.result = {
            "isError": False,
            "content": [],
            "structuredContent": {"text": "captured statement"},
        }
        self.delay_phase = None
        self.exception = None
        self.closed = False

    async def phase(self, name):
        self.calls.append(name)
        if self.delay_phase == name:
            await asyncio.sleep(2)

    async def initialize(self):
        await self.phase("initialize")
        return self.initialized

    async def list_tools(self):
        await self.phase("tools/list")
        return self.listing

    async def call_tool(self, name, *, arguments):
        await self.phase("tools/call")
        if self.exception:
            raise self.exception
        self.arguments = deepcopy(arguments)
        return self.result


class MCPToolTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.session = FakeSession()
        self.factory_calls = []

    @asynccontextmanager
    async def factory(self, *, registration, credential):
        self.factory_calls.append(
            {"registration": registration, "credential": credential}
        )
        try:
            yield self.session
        finally:
            self.session.closed = True

    async def call(self, reg=None, args=None, credential=None):
        return await read_tool(
            reg or registration(),
            {"query": "context"} if args is None else args,
            credential=credential,
            session_factory=self.factory,
        )

    async def error(self, code, **kwargs):
        with self.assertRaises(MCPToolError) as caught:
            await self.call(**kwargs)
        self.assertEqual(caught.exception.code, code)
        return caught.exception

    async def test_exact_read_sequence_and_evidence_digest(self):
        result = await self.call(credential="fixture-secret")
        self.assertEqual(self.session.calls, ["initialize", "tools/list", "tools/call"])
        self.assertEqual(
            result["value_sha256"], sha256_bytes(canonicalize(result["value"]))
        )
        self.assertEqual(
            result["registration_sha256"], sha256_bytes(canonicalize(registration()))
        )
        self.assertEqual(result["authority"], "none")
        self.assertEqual(result["output_limit_scope"], "post_sdk_parse")
        self.assertTrue(self.session.closed)
        self.assertNotIn("fixture-secret", repr(result))

    async def test_closed_registration_and_argument_schema_precede_effects(self):
        for reg in (
            {**registration(), "command": "npx evil"},
            {key: value for key, value in registration().items() if key != "id"},
        ):
            await self.error("INVALID_REGISTRATION", reg=reg)
        for arguments in ({}, {"query": 3}, {"query": "x", "write": True}):
            await self.error("INPUT_SCHEMA_MISMATCH", args=arguments)
        self.assertEqual(self.factory_calls, [])

    async def test_malicious_endpoints_never_open_a_session(self):
        urls = [
            "http://research.example/mcp",
            "https://localhost/mcp",
            "https://x.local/mcp",
            "https://127.0.0.1/mcp",
            "https://0177.0.0.1/mcp",
            "https://10.1.2.3/mcp",
            "https://169.254.169.254/",
            "https://[::1]/mcp",
            "https://[fc00::1]/mcp",
            "https://[::ffff:127.0.0.1]/mcp",
            "https://metadata.google.internal/mcp",
            "https://user:pass@research.example/mcp",
            "https://research.example/mcp?token=x",
            "https://research.example/mcp#x",
            "https://research.example/%2e%2e/secret",
            "https://research.example/../secret",
            "https://research.example:8443/mcp",
            "https://research.example\\@localhost/mcp",
            "https://research.example/mcp\nX:bad",
            "file:///tmp/mcp",
        ]
        for url in urls:
            with self.subTest(url=url):
                await self.error("UNSAFE_ENDPOINT", reg={**registration(), "url": url})
        self.assertEqual(self.factory_calls, [])

    async def test_protocol_pin_checked_before_listing_or_call(self):
        await self.error(
            "PROTOCOL_MISMATCH", reg={**registration(), "protocol_version": "auto"}
        )
        self.session.initialized["protocolVersion"] = "2025-06-18"
        await self.error("PROTOCOL_MISMATCH")
        self.assertEqual(self.session.calls, ["initialize"])

    async def test_limits_and_remote_schema_refs_rejected_before_effects(self):
        for key, value in (
            ("timeout_seconds", True),
            ("timeout_seconds", 121),
            ("max_output_bytes", 0),
            ("max_output_bytes", 131073),
        ):
            await self.error("INVALID_LIMIT", reg={**registration(), key: value})
        for schema in (
            {"type": "object", "$ref": "https://evil.example/schema"},
            {"type": "object", "$dynamicRef": "#evil"},
            {"type": "object", "properties": {"x": {"type": "bogus"}}},
        ):
            await self.error(
                "INVALID_SCHEMA", reg={**registration(), "input_schema": schema}
            )
        self.assertEqual(self.factory_calls, [])

    async def test_name_and_exact_input_output_schema_binding(self):
        for key, value, code in (
            ("name", "write_papers", "TOOL_IDENTITY_MISMATCH"),
            ("inputSchema", {"type": "object"}, "TOOL_SCHEMA_MISMATCH"),
            ("outputSchema", {"type": "object"}, "TOOL_SCHEMA_MISMATCH"),
        ):
            self.session = FakeSession()
            self.session.listing["tools"][0][key] = value
            await self.error(code)
            self.assertNotIn("tools/call", self.session.calls)

    async def test_annotations_cannot_grant_unregistered_tools_and_conflicts_fail(self):
        for annotations in ({"readOnlyHint": False}, {"destructiveHint": True}):
            self.session = FakeSession()
            self.session.listing["tools"][0]["annotations"] = annotations
            await self.error("TOOL_READ_CONFLICT")
        self.session = FakeSession()
        self.session.listing["tools"][0].update(
            name="unregistered_write", annotations={"readOnlyHint": True}
        )
        await self.error("TOOL_IDENTITY_MISMATCH")
        self.assertNotIn("tools/call", self.session.calls)

    async def test_bound_listing_no_auto_pagination_or_duplicate_names(self):
        self.session.listing["nextCursor"] = "second-page"
        await self.error("TOOL_LIST_LIMIT")
        self.session = FakeSession()
        self.session.listing["tools"] *= 2
        await self.error("TOOL_IDENTITY_MISMATCH")
        self.session = FakeSession()
        self.session.listing["tools"] *= 65
        await self.error("TOOL_LIST_LIMIT")
        self.assertNotIn("tools/call", self.session.calls)

    async def test_output_schema_no_fallback_from_invalid_structured_value(self):
        self.session.result["structuredContent"] = {"text": 3}
        self.session.result["content"] = [
            {"type": "text", "text": '{"text":"plausible"}'}
        ]
        await self.error("OUTPUT_SCHEMA_MISMATCH")
        self.assertEqual(self.session.calls.count("tools/call"), 1)

    async def test_text_only_and_error_output_are_not_evidence(self):
        self.session.result.pop("structuredContent")
        await self.error("STRUCTURED_OUTPUT_REQUIRED")
        self.session = FakeSession()
        self.session.result["isError"] = True
        error = await self.error("TOOL_FAILED")
        self.assertTrue(error.call_attempted)
        self.assertFalse(error.outcome_unknown)

    async def test_output_postparse_byte_cap(self):
        self.session.result["structuredContent"]["text"] = "α" * 2100
        await self.error("RECORD_LIMIT")

    async def test_timeout_during_call_records_unknown_outcome_without_retry(self):
        self.session.delay_phase = "tools/call"
        error = await self.error("TIMEOUT")
        self.assertTrue(error.call_attempted)
        self.assertTrue(error.outcome_unknown)
        self.assertTrue(self.session.closed)
        self.assertEqual(self.session.calls.count("tools/call"), 1)

    async def test_timeout_before_call_has_no_tool_attempt(self):
        self.session.delay_phase = "initialize"
        error = await self.error("TIMEOUT")
        self.assertFalse(error.call_attempted)
        self.assertFalse(error.outcome_unknown)

    async def test_credential_echo_and_exception_redaction(self):
        self.session.result["structuredContent"]["text"] = "fixture-secret"
        await self.error("CREDENTIAL_LEAK", credential="fixture-secret")
        self.session = FakeSession()
        self.session.exception = RuntimeError("Bearer fixture-secret in remote error")
        error = await self.error("MCP_CALL_FAILED", credential="fixture-secret")
        formatted = "".join(traceback.format_exception(error))
        self.assertNotIn("fixture-secret", formatted)
        self.assertTrue(error.outcome_unknown)

    async def test_credential_must_be_explicit_and_never_in_arguments(self):
        with patch.dict("os.environ", {"MCP_TOKEN": "ambient-secret"}):
            await self.call()
        self.assertIsNone(self.factory_calls[0]["credential"])
        for secret in ("bad\nsecret", "x", 3):
            await self.error("INVALID_CREDENTIAL", credential=secret)
        await self.error(
            "CREDENTIAL_LEAK",
            args={"query": "fixture-secret"},
            credential="fixture-secret",
        )

    async def test_registration_snapshot_prevents_injected_mutation(self):
        reg = registration()

        @asynccontextmanager
        async def mutating(*, registration, credential):
            registration["tool"] = "different"
            yield self.session

        await read_tool(reg, {"query": "context"}, session_factory=mutating)
        self.assertEqual(reg, registration())

    async def test_sdk_dependency_gate_never_opens_transport(self):
        with patch("researcher.service.mcp_tools.version", return_value="2.2.0"):
            with self.assertRaises(MCPToolError) as caught:
                await read_tool(registration(), {"query": "context"})
        self.assertEqual(caught.exception.code, "SDK_VERSION_MISMATCH")

    async def test_public_dns_rejects_private_resolution(self):
        from researcher.service.mcp_tools import _public_dns

        loop = asyncio.get_running_loop()
        with patch.object(
            loop,
            "getaddrinfo",
            AsyncMock(return_value=[(2, 1, 6, "", ("10.0.0.1", 443))]),
        ):
            with self.assertRaises(MCPToolError) as caught:
                await _public_dns("research.example")
        self.assertEqual(caught.exception.code, "UNSAFE_ENDPOINT")

    async def test_sdk_unavailable_never_opens_transport(self):
        with patch(
            "researcher.service.mcp_tools.version", side_effect=PackageNotFoundError
        ):
            with self.assertRaises(MCPToolError) as caught:
                await read_tool(registration(), {"query": "context"})
        self.assertEqual(caught.exception.code, "SDK_UNAVAILABLE")

    async def test_sdk_bridge_flags_redirects_methods_and_no_callbacks(self):
        try:
            import httpx
        except ImportError:
            self.skipTest(
                "optional HTTP client is absent; injected-session contracts still run"
            )
        observed = {}

        class FakeClient:
            def __init__(self, **kwargs):
                observed["http"] = kwargs

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return False

        @asynccontextmanager
        async def transport(url, **kwargs):
            observed["transport"] = kwargs
            yield "read", "write", lambda: None

        @asynccontextmanager
        async def session(read, write, **kwargs):
            self.assertEqual((read, write), ("read", "write"))
            observed["session"] = kwargs
            yield self.session

        # These are explicit SDK-signature test doubles, not a claim that an
        # installed older SDK is compatible with the pinned network bridge.
        sdk = ModuleType("mcp")
        sdk.ClientSession = session
        transport_module = ModuleType("mcp.client.streamable_http")
        transport_module.streamable_http_client = transport
        types_module = ModuleType("mcp.types")
        types_module.LATEST_PROTOCOL_VERSION = PROTOCOL_VERSION

        with (
            patch("researcher.service.mcp_tools.version", return_value="1.30.0"),
            patch("researcher.service.mcp_tools._public_dns", AsyncMock()),
            patch.object(httpx, "AsyncClient", FakeClient),
            patch.dict(
                "sys.modules",
                {
                    "mcp": sdk,
                    "mcp.types": types_module,
                    "mcp.client.streamable_http": transport_module,
                },
            ),
        ):
            async with _sdk_session(
                registration=registration(), credential="fixture-secret"
            ):
                self.assertFalse(observed["http"]["trust_env"])
                self.assertFalse(observed["http"]["follow_redirects"])
                self.assertEqual(
                    observed["http"]["headers"],
                    {"Authorization": "Bearer fixture-secret"},
                )
                self.assertFalse(observed["transport"]["terminate_on_close"])
                self.assertEqual(set(observed["session"]), {"read_timeout_seconds"})
                hooks = observed["http"]["event_hooks"]
                request_hook, response_hook = hooks["request"][0], hooks["response"][0]
                endpoint = registration()["url"]
                for method in (
                    "initialize",
                    "notifications/initialized",
                    "tools/list",
                    "tools/call",
                ):
                    params = {"name": "search_papers"} if method == "tools/call" else {}
                    await request_hook(
                        httpx.Request(
                            "POST", endpoint, json={"method": method, "params": params}
                        )
                    )
                for request in (
                    httpx.Request("DELETE", endpoint),
                    httpx.Request("GET", "https://other.example/mcp"),
                    httpx.Request(
                        "POST", endpoint, json={"method": "sampling/createMessage"}
                    ),
                    httpx.Request(
                        "POST",
                        endpoint,
                        json={
                            "method": "tools/call",
                            "params": {"name": "search_papers"},
                        },
                    ),
                ):
                    with self.assertRaises(MCPToolError) as caught:
                        await request_hook(request)
                    self.assertEqual(caught.exception.code, "OUTBOUND_POLICY")
                with self.assertRaises(MCPToolError) as caught:
                    await response_hook(
                        httpx.Response(307, headers={"location": endpoint + "/"})
                    )
                self.assertEqual(caught.exception.code, "REDIRECT_FORBIDDEN")

    async def test_timeout_covers_session_cleanup(self):
        @asynccontextmanager
        async def delayed_cleanup(*, registration, credential):
            yield self.session
            await asyncio.sleep(2)

        with self.assertRaises(MCPToolError) as caught:
            await read_tool(
                registration(), {"query": "context"}, session_factory=delayed_cleanup
            )
        self.assertEqual(caught.exception.code, "TIMEOUT")
        self.assertTrue(caught.exception.call_attempted)
        self.assertFalse(caught.exception.outcome_unknown)

    async def test_schema_identifier_and_deep_or_float_records_fail_closed(self):
        await self.error(
            "INVALID_SCHEMA",
            reg={
                **registration(),
                "input_schema": {
                    "type": "object",
                    "$id": "https://other.example/schema",
                },
            },
        )
        deep = {}
        current = deep
        for _ in range(35):
            current["nested"] = {}
            current = current["nested"]
        await self.error("RECORD_LIMIT", args=deep)
        await self.error("INVALID_RECORD", args={"query": 1.5})
        self.assertEqual(self.factory_calls, [])


if __name__ == "__main__":
    unittest.main()
