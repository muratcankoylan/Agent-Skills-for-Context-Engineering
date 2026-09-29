"""Real pinned MCP SDK over httpx.MockTransport, never a live endpoint.

Only HTTP transport and DNS resolution are injected. StreamableHTTPTransport,
ClientSession, protocol parsing, schema handling, and our gateway are real. This
suite is skipped unless the optional exact SDK/httpx dependency profile exists.
"""

from copy import deepcopy
from importlib.metadata import PackageNotFoundError, version
import inspect
import unittest
from unittest.mock import AsyncMock, patch

from researcher.scripts.schema_contract import canonicalize, parse_json_strict
from researcher.service.mcp_evidence import collect_mcp
from researcher.service.mcp_tools import MCPToolError, PROTOCOL_VERSION, read_tool
from researcher.service.tests.test_mcp_tools import registration

try:
    PINNED_AVAILABLE = version("mcp") == "1.30.0" and version("httpx") == "0.28.1"
except PackageNotFoundError:
    PINNED_AVAILABLE = False


@unittest.skipUnless(PINNED_AVAILABLE, "requires optional mcp==1.30.0/httpx==0.28.1")
class ActualMCPTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        import httpx

        # Import real SDK annotations before intercepting only client creation.
        from mcp.client.streamable_http import streamable_http_client

        self.assertTrue(inspect.isfunction(streamable_http_client))

        self.httpx = httpx
        self.real_client = httpx.AsyncClient
        self.config = registration()
        self.config["timeout_seconds"] = 2
        self.requests = []
        self.clients = []
        self.initialized = {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "offline-contract-server", "version": "1"},
        }
        self.listing = {
            "tools": [
                {
                    "name": self.config["tool"],
                    "inputSchema": deepcopy(self.config["input_schema"]),
                    "outputSchema": deepcopy(self.config["output_schema"]),
                }
            ]
        }
        self.result = {
            "content": [{"type": "text", "text": "untrusted representation"}],
            "structuredContent": {"text": "exact SDK observation"},
            "isError": False,
        }
        self.redirect = None
        self.fail_call = False
        self.invalid_json = None
        self.sessionful = False
        self.dns = AsyncMock()
        self.patches = [
            patch("httpx.AsyncClient", self.client_factory),
            patch("researcher.service.mcp_tools._public_dns", self.dns),
            patch(
                "socket.getaddrinfo",
                side_effect=AssertionError("network DNS forbidden"),
            ),
            patch(
                "socket.socket.connect",
                side_effect=AssertionError("network connection forbidden"),
            ),
        ]
        for patched in self.patches:
            patched.start()
            self.addCleanup(patched.stop)

    def client_factory(self, **kwargs):
        self.clients.append(kwargs)
        # Real httpx client, response handling, hooks, and lifecycle remain intact.
        return self.real_client(
            transport=self.httpx.MockTransport(self.handle), **kwargs
        )

    async def handle(self, request):
        payload = (
            parse_json_strict(request.content.decode()) if request.content else None
        )
        self.requests.append((request, payload))
        if self.invalid_json is not None:
            return self.httpx.Response(
                200,
                headers={"Content-Type": "application/json"},
                content=self.invalid_json,
            )
        if self.redirect:
            return self.httpx.Response(307, headers={"Location": self.redirect})
        if self.sessionful and request.method == "GET":
            return self.httpx.Response(405)
        if request.method != "POST":
            raise AssertionError("Unexpected transport method")
        method = payload["method"]
        if method == "notifications/initialized":
            return self.httpx.Response(202)
        if method == "tools/call" and self.fail_call:
            raise self.httpx.ReadError("offline transport failure", request=request)
        result = {
            "initialize": self.initialized,
            "tools/list": self.listing,
            "tools/call": self.result,
        }[method]
        headers = (
            {"Mcp-Session-Id": "offline-session"}
            if self.sessionful and method == "initialize"
            else {}
        )
        return self.httpx.Response(
            200,
            headers=headers,
            json={"jsonrpc": "2.0", "id": payload["id"], "result": result},
        )

    def methods(self):
        return [
            payload["method"] if payload else request.method
            for request, payload in self.requests
        ]

    async def call(self, **kwargs):
        return await read_tool(self.config, {"query": "context"}, **kwargs)

    async def test_actual_sdk_signatures_and_complete_protocol_exchange(self):
        from mcp import ClientSession
        from mcp.client.streamable_http import streamable_http_client
        from mcp.types import LATEST_PROTOCOL_VERSION

        self.assertEqual(LATEST_PROTOCOL_VERSION, PROTOCOL_VERSION)
        self.assertIn(
            "http_client", inspect.signature(streamable_http_client).parameters
        )
        self.assertIn(
            "terminate_on_close", inspect.signature(streamable_http_client).parameters
        )
        self.assertIn(
            "read_timeout_seconds", inspect.signature(ClientSession).parameters
        )
        result = await self.call()
        self.assertEqual(result["value"], {"text": "exact SDK observation"})
        self.assertEqual(result["authority"], "none")
        self.assertEqual(
            self.methods(),
            ["initialize", "notifications/initialized", "tools/list", "tools/call"],
        )
        self.assertEqual(
            self.requests[-1][1]["params"]["arguments"], {"query": "context"}
        )
        capabilities = self.requests[0][1]["params"]["capabilities"]
        for name in ("sampling", "elicitation", "roots"):
            self.assertNotIn(name, capabilities)
        self.assertEqual(len(self.clients), 1)
        self.assertIs(self.clients[0]["trust_env"], False)
        self.assertIs(self.clients[0]["follow_redirects"], False)
        self.assertEqual(set(self.clients[0]["event_hooks"]), {"request", "response"})
        self.assertEqual(self.dns.await_count, len(self.requests))
        self.assertTrue(all(request.method == "POST" for request, _ in self.requests))
        self.assertTrue(
            all(str(request.url) == self.config["url"] for request, _ in self.requests)
        )

    async def test_explicit_credential_only_in_transport_headers(self):
        token = "offline-test-explicit-token"
        result = await self.call(credential=token)
        for request, payload in self.requests:
            self.assertEqual(request.headers["authorization"], "Bearer " + token)
            self.assertNotIn(token, canonicalize(payload).decode())
        self.assertNotIn(token, canonicalize(result).decode())

    async def test_protocol_mismatch_stops_before_tool_discovery(self):
        self.initialized["protocolVersion"] = "2025-06-18"
        with self.assertRaises(MCPToolError) as raised:
            await self.call()
        # Preserve typed policy errors through AnyIO's cleanup ExceptionGroup.
        self.assertEqual(raised.exception.code, "PROTOCOL_MISMATCH")
        self.assertFalse(raised.exception.call_attempted)
        self.assertNotIn("tools/list", self.methods())
        self.assertNotIn("tools/call", self.methods())

    async def test_changed_remote_schema_stops_before_tool_call(self):
        self.listing["tools"][0]["inputSchema"]["properties"]["query"]["maxLength"] = 20
        with self.assertRaises(MCPToolError) as raised:
            await self.call()
        self.assertEqual(raised.exception.code, "TOOL_SCHEMA_MISMATCH")
        self.assertFalse(raised.exception.call_attempted)
        self.assertNotIn("tools/call", self.methods())

    async def test_real_sdk_rejects_invalid_structured_output(self):
        self.result["structuredContent"] = {"text": False}
        with self.assertRaises(MCPToolError) as raised:
            await self.call()
        self.assertTrue(raised.exception.call_attempted)
        # The SDK rejects before returning call_tool. Our bridge conservatively
        # treats this as unknown, even though MockTransport observed a response.
        self.assertTrue(raised.exception.outcome_unknown)
        self.assertEqual(self.methods().count("tools/call"), 1)

    async def test_post_sdk_parse_cap_covers_unselected_text_content(self):
        self.result["content"][0]["text"] = "x" * 5000
        with self.assertRaises(MCPToolError) as raised:
            await self.call()
        self.assertEqual(raised.exception.code, "RECORD_LIMIT")
        self.assertTrue(raised.exception.call_attempted)
        self.assertFalse(raised.exception.outcome_unknown)
        self.assertEqual(self.methods().count("tools/call"), 1)

    async def test_same_origin_redirect_not_followed_by_actual_sdk(self):
        self.redirect = self.config["url"] + "/redirected"
        with self.assertRaises(MCPToolError):
            await self.call()
        self.assertEqual(len(self.requests), 1)
        self.assertEqual(str(self.requests[0][0].url), self.config["url"])

    async def test_transport_failure_after_call_is_unknown_without_retry(self):
        self.fail_call = True
        with self.assertRaises(MCPToolError) as raised:
            await self.call()
        self.assertTrue(raised.exception.call_attempted)
        self.assertTrue(raised.exception.outcome_unknown)
        self.assertEqual(self.methods().count("tools/call"), 1)

    async def test_sessionful_sdk_does_not_delete_remote_session_on_close(self):
        self.sessionful = True
        result = await self.call()
        self.assertEqual(result["value"], {"text": "exact SDK observation"})
        self.assertIn("GET", self.methods())
        self.assertNotIn("DELETE", [request.method for request, _ in self.requests])
        self.assertEqual(self.methods().count("tools/call"), 1)

    async def test_sync_evidence_adapter_uses_actual_sdk_offline(self):
        # The sync adapter owns an event loop, so invoke it outside this test's
        # loop. The process-wide transport patch still routes every byte locally.
        import asyncio

        lane = await asyncio.to_thread(collect_mcp, self.config, {"query": "context"})
        self.assertEqual(lane["authority"], "none")
        self.assertEqual(lane["evidence"][0]["evidence_scope"], "mcp_observation")
        self.assertEqual(
            lane["evidence"][0]["text"], '{"text":"exact SDK observation"}'
        )
        self.assertEqual(self.methods().count("tools/call"), 1)


if __name__ == "__main__":
    unittest.main()
