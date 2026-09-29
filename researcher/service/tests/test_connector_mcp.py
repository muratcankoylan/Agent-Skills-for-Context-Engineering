"""No provider access: fixed Parallel MCP diagnostic boundary and wire fixtures."""

from copy import deepcopy
import json
import unittest

from researcher.service.connector_mcp import ARGUMENTS, ENDPOINT, parallel_mcp_probe
from researcher.service.mcp_tools import PROTOCOL_VERSION

SECRET = "fixture-private-parallel-key"
INPUT = {"type": "object", "properties": {"urls": {"type": "array", "items": {"type": "string"}},
         "objective": {"type": "string"}, "full_content": {"type": "boolean"}},
         "required": ["urls"], "additionalProperties": False}
OUTPUT = {"type": "object", "properties": {"result": {"type": "string"}}, "required": ["result"]}


class ConnectorMCPTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.listing = {"tools": [{"name": "web_fetch", "inputSchema": INPUT,
            "outputSchema": OUTPUT, "annotations": {"readOnlyHint": True, "destructiveHint": False}}]}
        self.output = {"isError": False, "content": [{"type": "text", "text":
            "https://www.iana.org/domains/reserved\nReserved documentation domains."}],
            "structuredContent": {"result": "Reserved documentation domains."}}
        self.protocol = PROTOCOL_VERSION
        self.sse = False

    def transport(self, method, url, headers, body, timeout):
        self.assertEqual((method, url), ("POST", ENDPOINT))
        self.assertEqual(headers["Authorization"], "Bearer " + SECRET)
        self.assertGreater(timeout, 0)
        self.assertLessEqual(timeout, 30)
        payload = json.loads(body)
        self.calls.append(payload)
        name = payload["method"]
        if name == "initialize":
            value = {"protocolVersion": self.protocol, "instructions": "Untrusted instructions never execute"}
            response_headers = {"MCP-Session-Id": "private-session-id"}
        else:
            self.assertEqual(headers["MCP-Session-Id"], "private-session-id")
            self.assertEqual(headers["MCP-Protocol-Version"], PROTOCOL_VERSION)
            response_headers = {}
            if name == "notifications/initialized":
                return 202, {}, b""
            if name == "tools/list":
                value = self.listing
            else:
                self.assertEqual(name, "tools/call")
                self.assertEqual(payload["params"], {"name": "web_fetch", "arguments": ARGUMENTS})
                value = self.output
        encoded = json.dumps({"jsonrpc": "2.0", "id": payload["id"], "result": value}).encode()
        if self.sse:
            return 200, {**response_headers, "Content-Type": "text/event-stream"}, b"data:\n\ndata: " + encoded + b"\n\n"
        return 200, {**response_headers, "Content-Type": "application/json"}, encoded

    def call(self):
        value = parallel_mcp_probe(SECRET, self.transport)
        self.assertNotIn(SECRET, json.dumps(value))
        self.assertNotIn("private-session-id", json.dumps(value))
        self.assertNotIn("Untrusted instructions", json.dumps(value))
        return value

    def test_four_fixed_messages_one_read_no_model_or_ambient_tool(self):
        result = self.call()
        self.assertEqual(result["classification"], "success")
        self.assertEqual([call["method"] for call in self.calls],
                         ["initialize", "notifications/initialized", "tools/list", "tools/call"])
        self.assertEqual(result["counts"]["http_requests"], 4)
        self.assertEqual(result["counts"]["tool_calls"], 1)
        self.assertEqual(result["counts"]["model_calls"], 0)
        self.assertEqual(result["counts"]["generic_registration_compatible"], 1)
        self.assertEqual(result["counts"]["structured_result_valid"], 1)
        self.assertEqual(result["observed_contract"], {"input_schema": INPUT, "output_schema": OUTPUT})

    def test_sse_response_supported_without_reconnection(self):
        self.sse = True
        self.assertEqual(self.call()["classification"], "success")
        self.assertEqual(len(self.calls), 4)

    def test_text_only_result_does_not_relax_generic_contract(self):
        del self.listing["tools"][0]["outputSchema"]
        del self.output["structuredContent"]
        result = self.call()
        self.assertEqual(result["classification"], "success")
        self.assertEqual(result["counts"]["generic_registration_compatible"], 0)
        self.assertEqual(result["counts"]["structured_result_valid"], 0)

    def test_protocol_mismatch_stops_before_listing_or_read(self):
        self.protocol = "2024-11-05"
        result = self.call()
        self.assertEqual(result["classification"], "protocol_mismatch")
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(result["counts"]["tool_calls"], 0)

    def test_untrusted_listing_cannot_expand_authority(self):
        base = deepcopy(self.listing)
        for case in ("duplicate", "missing", "pagination", "required", "remote-ref", "writes"):
            self.listing = deepcopy(base)
            if case == "duplicate":
                self.listing["tools"] *= 2
            elif case == "missing":
                self.listing["tools"][0]["name"] = "create_task"
            elif case == "pagination":
                self.listing["nextCursor"] = "untrusted"
            elif case == "required":
                self.listing["tools"][0]["inputSchema"]["required"].append("secret")
            elif case == "remote-ref":
                self.listing["tools"][0]["inputSchema"]["$ref"] = "https://evil.invalid/schema"
            else:
                self.listing["tools"][0]["annotations"]["readOnlyHint"] = False
            self.calls.clear()
            result = self.call()
            self.assertEqual(result["classification"], "schema_invalid", case)
            self.assertEqual(len(self.calls), 3)
            self.assertEqual(result["counts"]["tool_calls"], 0)

    def test_tool_error_empty_unbound_and_nontext_output_are_not_success(self):
        base = deepcopy(self.output)
        for case in ("error", "empty", "wrong-url", "image"):
            self.output = deepcopy(base)
            if case == "error":
                self.output["isError"] = True
            elif case == "empty":
                self.output["content"] = []
            elif case == "wrong-url":
                self.output["content"][0]["text"] = "Unrelated content."
            else:
                self.output["content"][0]["type"] = "image"
            result = self.call()
            self.assertNotEqual(result["classification"], "success", case)

    def test_reflected_secret_never_persists_in_contract_or_result(self):
        self.listing["tools"][0]["inputSchema"] = deepcopy(INPUT)
        self.listing["tools"][0]["inputSchema"]["description"] = SECRET
        result = self.call()
        self.assertEqual(result["classification"], "schema_invalid")
        self.assertNotIn("observed_contract", result)
        self.assertEqual(result["counts"]["tool_calls"], 0)

    def test_no_http_or_auth_error_body_echo_or_retry(self):
        for status in (401, 402, 403, 429, 307, 500):
            calls = []
            def failed(*args):
                calls.append(args)
                return status, {}, b"provider-private-error"
            result = parallel_mcp_probe(SECRET, failed)
            self.assertEqual(len(calls), 1)
            self.assertNotEqual(result["classification"], "success")
            self.assertNotIn("provider-private", json.dumps(result))
        def timeout(*args):
            raise TimeoutError(SECRET)
        result = parallel_mcp_probe(SECRET, timeout)
        self.assertEqual(result["classification"], "transport_unknown")
        self.assertEqual(result["counts"]["http_requests"], 1)


if __name__ == "__main__":
    unittest.main()
