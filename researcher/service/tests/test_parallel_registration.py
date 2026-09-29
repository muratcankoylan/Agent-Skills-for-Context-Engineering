"""Offline service integration against the reviewed 2026-09-29 MCP schema.

Provider contract is the live observation; result content is synthetic. These
tests do not claim a second live generic-SDK call or semantic research quality.
"""

from contextlib import asynccontextmanager
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import ssl
import unittest
from unittest.mock import patch

from researcher.service.connector_checks import _body
from researcher.service.connector_mcp import ARGUMENTS, registered_parallel_probe
from researcher.service.contracts import load_config
from researcher.service.mcp_evidence import MCPEvidenceError, collect_mcp, validate_read
from researcher.service.mcp_tools import MCPToolError, _safe_error_code, read_tool
from researcher.service.tests.test_mcp_sdk import PINNED_AVAILABLE
from researcher.service.tests.test_mcp_tools import FakeSession

ROOT = Path(__file__).resolve().parents[1]


def registration():
    return json.loads((ROOT / "registrations" / "parallel-web-fetch.json").read_text())


class ParallelRegistrationTests(unittest.TestCase):
    def setUp(self):
        self.config = registration()
        self.session = FakeSession()
        self.session.listing = {"tools": [{"name": "web_fetch",
            "inputSchema": self.config["input_schema"], "outputSchema": self.config["output_schema"],
            "annotations": {"readOnlyHint": True, "destructiveHint": False}}]}
        self.session.result = {"isError": False, "content": [], "structuredContent": {
            "extract_id": "synthetic-extract", "session_id": "synthetic-session", "errors": [],
            "results": [{"url": ARGUMENTS["urls"][0], "excerpts": ["Synthetic fixture excerpt."]}]}}

    @asynccontextmanager
    async def factory(self, **_kwargs):
        yield self.session

    def test_exact_live_schema_fingerprint_not_an_invented_compatible_subset(self):
        contract = {name: self.config[name] for name in ("input_schema", "output_schema")}
        self.assertEqual(hashlib.sha256(_body(contract)).hexdigest(),
                         "074875a4422f67b357025b12529526584b3c30444237afc09985626a78bd0f70")
        self.assertEqual(self.config["url"], "https://search.parallel.ai/mcp-oauth")
        self.assertEqual(self.config["tool"], "web_fetch")
        self.assertLessEqual(self.config["max_output_bytes"], 32768)
        validate_read(self.config, ARGUMENTS)

    def test_real_bridge_accepts_registered_schema_and_marks_observation_not_authority(self):
        with patch("researcher.service.mcp_tools._sdk_session", self.factory):
            lane = collect_mcp(self.config, ARGUMENTS, credential="synthetic-parallel-credential")
        self.assertEqual(self.session.calls, ["initialize", "tools/list", "tools/call"])
        self.assertEqual(lane["source"], "mcp:parallel-fetch")
        self.assertEqual(lane["authority"], "none")
        self.assertEqual(lane["evidence"][0]["evidence_scope"], "mcp_observation")
        self.assertFalse(lane["semantic_quality_measured"])
        self.assertEqual(lane["request_reservation"]["source_requests"], 12)

    def test_registered_diagnostic_uses_isolated_bridge_and_requires_actual_extract(self):
        def collect(config, args, credential):
            self.assertEqual(config, self.config)
            self.assertEqual(args, ARGUMENTS)
            with patch("researcher.service.mcp_tools._sdk_session", self.factory):
                return collect_mcp(config, args, credential=credential)
        report = registered_parallel_probe("synthetic-parallel-credential", collect=collect)
        self.assertEqual(report["classification"], "success")
        self.assertEqual(report["counts"]["result_count"], 1)
        self.assertEqual(report["counts"]["http_request_ceiling"], 12)
        self.assertNotIn("Synthetic fixture excerpt", json.dumps(report))
        self.session.result["structuredContent"]["results"] = []
        report = registered_parallel_probe("synthetic-parallel-credential", collect=collect)
        self.assertEqual(report["classification"], "schema_invalid")

    def test_observed_schema_drift_rejected_before_tool_call(self):
        self.session.listing = deepcopy(self.session.listing)
        self.session.listing["tools"][0]["inputSchema"]["title"] = "changed-provider-contract"
        with patch("researcher.service.mcp_tools._sdk_session", self.factory):
            with self.assertRaisesRegex(ValueError, "TOOL_SCHEMA_MISMATCH"):
                collect_mcp(self.config, ARGUMENTS)
        self.assertEqual(self.session.calls, ["initialize", "tools/list"])

    def test_safe_worker_failure_code_is_retained_without_raw_errors(self):
        def rejected(*_args, **_kwargs):
            raise MCPEvidenceError("TOOL_SCHEMA_MISMATCH", call_attempted=False)
        report = registered_parallel_probe("synthetic-parallel-credential", collect=rejected)
        self.assertEqual(report["error_code"], "TOOL_SCHEMA_MISMATCH")
        self.assertEqual(report["counts"]["tool_call_attempted"], 0)

    def test_nested_transport_error_classification_never_uses_exception_text(self):
        import httpx
        request = httpx.Request("POST", "https://search.parallel.ai/mcp-oauth")
        for code, leaf in (("TOOL_SCHEMA_MISMATCH", MCPToolError("TOOL_SCHEMA_MISMATCH")),
                           ("TLS_CERTIFICATE_INVALID", ssl.SSLCertVerificationError("private error")),
                           ("HTTP_AUTH_REJECTED", httpx.HTTPStatusError("private error", request=request,
                                response=httpx.Response(401)))):
            wrapped = ExceptionGroup("private SDK detail", [ExceptionGroup("private detail", [leaf])])
            self.assertEqual(_safe_error_code(wrapped, "INITIALIZE"), code)
        self.assertEqual(_safe_error_code(RuntimeError("private detail"), "LIST"), "MCP_LIST_FAILED")

    def test_service_research_config_admits_one_registered_read_with_explicit_cost(self):
        config = json.loads((ROOT / "config.example.json").read_text())
        for route in config["models"].values():
            route["model"] = "fixture-pinned-model"
            route["input_microusd_per_million_tokens"] = 1
            route["output_microusd_per_million_tokens"] = 1
        config["mcp_tools"] = [{"registration": self.config, "credential_env": "PARALLEL_API_KEY",
                                "max_cost_microusd": 10000}]
        config["schedules"][0]["mcp_reads"] = [{"id": self.config["id"], "arguments": ARGUMENTS}]
        parsed = load_config(json.dumps(config))
        self.assertEqual(parsed["mcp_tools"][0]["registration"], self.config)


@unittest.skipUnless(PINNED_AVAILABLE, "requires pinned MCP SDK")
class ParallelActualSDKTests(unittest.IsolatedAsyncioTestCase):
    def fixture(self):
        from researcher.service.tests.test_mcp_sdk import ActualMCPTests
        fixture = ActualMCPTests("test_actual_sdk_signatures_and_complete_protocol_exchange")
        fixture.setUp()
        for item in fixture.patches:
            self.addCleanup(item.stop)
        fixture.config = registration()
        fixture.config["timeout_seconds"] = 2
        fixture.listing = {"tools": [{"name": "web_fetch", "inputSchema": fixture.config["input_schema"],
                                     "outputSchema": fixture.config["output_schema"]}]}
        fixture.result = {"isError": False, "content": [{"type": "text", "text": "Fixture"}],
            "structuredContent": {"extract_id": "synthetic-extract", "session_id": "synthetic-session",
                "errors": [], "results": [{"url": ARGUMENTS["urls"][0], "excerpts": ["Fixture"]}]}}
        return fixture

    async def test_real_sdk_roundtrips_observed_contract_with_no_network(self):
        fixture = self.fixture()
        receipt = await read_tool(fixture.config, ARGUMENTS, credential="synthetic-credential")
        self.assertEqual(receipt["value"], fixture.result["structuredContent"])
        self.assertEqual(receipt["tool_calls"], 1)
        self.assertEqual(len(fixture.requests), 4)

    async def test_incidental_float_metadata_is_not_promoted_to_evidence(self):
        fixture = self.fixture()
        fixture.result["_meta"] = {"elapsed_seconds": 0.125}
        fixture.result["content"][0]["annotations"] = {"priority": 0.5}
        receipt = await read_tool(fixture.config, ARGUMENTS)
        self.assertEqual(receipt["value"], fixture.result["structuredContent"])
        self.assertNotIn("elapsed_seconds", json.dumps(receipt))
        self.assertNotIn("priority", json.dumps(receipt))
        self.assertRegex(receipt["sdk_response_sha256"], r"^sha256:[0-9a-f]{64}$")
        self.assertGreater(receipt["sdk_response_bytes"], receipt["output_bytes"])

    async def test_floats_in_structured_evidence_still_fail_closed(self):
        fixture = self.fixture()
        fixture.result["structuredContent"]["provider_elapsed"] = 0.125
        with self.assertRaises(MCPToolError) as caught:
            await read_tool(fixture.config, ARGUMENTS)
        self.assertEqual(caught.exception.code, "INVALID_RECORD")


if __name__ == "__main__":
    unittest.main()
