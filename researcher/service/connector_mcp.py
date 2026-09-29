"""Fixed Parallel MCP diagnostic, not ambient discovery or tool authorization.

Four one-shot HTTP messages, one operator-selected public URL, no model, callback,
reconnection, redirects, or automatic registration. The generic SDK bridge remains
strict: observing a text-only result does not make it valid structured evidence.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import time

from jsonschema import Draft202012Validator

from .connector_checks import (
    MAX_RESPONSE_BYTES, PROBES, _EXTRACT_URL, _body, _headers, _https, _json, _reflects, _success,
)
from .contracts import ServiceError
from .mcp_tools import PROTOCOL_VERSION, _registration, _schema
from researcher.scripts.source_search import credential_value

ENDPOINT = "https://search.parallel.ai/mcp-oauth"
TOOL = "web_fetch"
ARGUMENTS = {"urls": [_EXTRACT_URL], "objective": "Identify why these domains are reserved",
             "full_content": False}
REQUEST_CEILING = 4
RESERVE_MICRO_USD = 10_000


def parallel_registration():
    """The reviewed live tool contract, never a schema inferred during dispatch."""
    path = Path(__file__).with_name("registrations") / "parallel-web-fetch.json"
    registration, _ = _registration(_json(path.read_bytes()))
    if (registration["id"], registration["url"], registration["tool"]) != (
            "parallel-fetch", ENDPOINT, TOOL):
        raise ServiceError("PARALLEL_REGISTRATION_MISMATCH")
    return registration


def registered_parallel_probe(credential, collect=None):
    """Use the actual isolated generic service bridge for one registered fetch.

Caller owns a durable twelve-request reservation. Ambiguous tool outcomes raise
instead of becoming reusable successful receipts. No response text is returned.
"""
    from .mcp_evidence import MAX_REQUESTS, MCPEvidenceError
    from .mcp_worker import bounded_collect_mcp
    config = parallel_registration()
    result = {"schema": "connector-mcp-probe/v1", "name": "parallel_registered_fetch",
              "classification": "schema_invalid", "http_status": None, "counts": {}}
    try:
        lane = (collect or bounded_collect_mcp)(config, ARGUMENTS, credential=credential)
        value = _json(lane["evidence"][0]["text"].encode("utf-8"))
        counts = _success(PROBES["parallel_extract"], value)
        result["counts"] = {**counts, "http_request_ceiling": MAX_REQUESTS,
            "tool_calls": lane["tool_calls"], "model_calls": lane["model_calls"],
            "output_bytes": lane["output_bytes"]}
        result["output_sha256"] = lane["output_sha256"]
        result["classification"] = "success"
    except MCPEvidenceError as error:
        if error.ambiguous:
            raise ServiceError("DIAGNOSTIC_OUTCOME_UNKNOWN") from None
        result["classification"] = "mcp_contract_or_access_rejected"
        # MCPEvidenceError constrains this to a fixed safe uppercase code. Keep
        # it: access failure and a contract mismatch require different remedies.
        result["error_code"] = error.code
        result["counts"]["tool_call_attempted"] = int(error.call_attempted)
    except (ValueError, KeyError, TypeError):
        pass
    return result


def _message(body, headers, request_id):
    mime = headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if mime == "application/json":
        values = [_json(body)]
    elif mime == "text/event-stream":
        values = []
        # No SSE resume or server-driven requests. Ignore empty priming events;
        # any nonempty event must be this request's one JSON-RPC response.
        for event in body.decode("utf-8").replace("\r\n", "\n").split("\n\n"):
            data = [line[5:].lstrip(" ") for line in event.split("\n") if line.startswith("data:")]
            if data and "\n".join(data).strip():
                values.append(_json("\n".join(data).encode()))
    else:
        raise ValueError()
    if len(values) != 1:
        raise ValueError()
    value = values[0]
    if (not isinstance(value, dict) or value.get("jsonrpc") != "2.0"
            or type(value.get("id")) is not int or value["id"] != request_id
            or "error" in value or "method" in value or not isinstance(value.get("result"), dict)):
        raise ValueError()
    return value["result"]


def parallel_mcp_probe(credential, transport=None):
    """One diagnostic session, after caller reserves four requests and cost.

The observed contract is private diagnostic data, never an installed registration.
Raw content and session identifiers are discarded. Exceptions are fixed enums.
"""
    try:
        if credential_value(credential) is None:
            raise ValueError()
    except ValueError:
        raise ServiceError("INVALID_SOURCE_CREDENTIAL") from None
    result = {"schema": "connector-mcp-probe/v1", "name": "parallel_mcp_fetch",
              "classification": "transport_unknown", "http_status": None,
              "counts": {"http_requests": 0, "tool_calls": 0, "model_calls": 0}}
    headers = {"Accept": "application/json, text/event-stream", "Accept-Encoding": "identity",
               "Content-Type": "application/json", "Authorization": "Bearer " + credential,
               "User-Agent": "context-research-connector-check/1", "Connection": "close"}
    deadline = time.monotonic() + 90
    send = transport or _https

    def request(method, request_id=None, params=None):
        payload = {"jsonrpc": "2.0", "method": method}
        if request_id is not None:
            payload["id"] = request_id
        if params is not None:
            payload["params"] = params
        remaining = min(30, deadline - time.monotonic())
        if remaining <= 0 or result["counts"]["http_requests"] >= REQUEST_CEILING:
            raise TimeoutError()
        result["counts"]["http_requests"] += 1
        if method == "tools/call":
            result["counts"]["tool_calls"] += 1
        status, raw_headers, body = send("POST", ENDPOINT, dict(headers), _body(payload), remaining)
        if type(status) is not int or not 100 <= status <= 599:
            raise ValueError()
        result["http_status"] = status
        if not isinstance(body, bytes) or len(body) > MAX_RESPONSE_BYTES:
            raise ValueError()
        response_headers = _headers(raw_headers)
        if _reflects(credential, body, raw_headers):
            raise ValueError()
        length = response_headers.get("content-length")
        if (length is not None and (not length.isascii() or not length.isdecimal()
                or int(length) != len(body) or "transfer-encoding" in response_headers)
                or response_headers.get("content-encoding", "identity").lower() != "identity"
                or response_headers.get("transfer-encoding", "chunked").lower() != "chunked"):
            raise ValueError()
        expected = 202 if request_id is None else 200
        if status != expected:
            result["classification"] = {401: "auth_rejected", 402: "billing_blocked",
                403: "permission_denied", 429: "rate_limited"}.get(status, "endpoint_unavailable")
            raise ServiceError("MCP_HTTP_REJECTED")
        if request_id is None:
            if body:
                raise ValueError()
            return None
        decoded = _message(body, response_headers, request_id)
        if _reflects(credential, b"", raw_headers, decoded):
            raise ValueError()
        if method == "initialize":
            session = response_headers.get("mcp-session-id")
            if session is not None:
                if not 1 <= len(session) <= 4096 or any(not 33 <= ord(ch) <= 126 for ch in session):
                    raise ValueError()
                headers["MCP-Session-Id"] = session
        return decoded

    try:
        initialized = request("initialize", 1, {"protocolVersion": PROTOCOL_VERSION,
            "capabilities": {}, "clientInfo": {"name": "context-research-diagnostic", "version": "1"}})
        if initialized.get("protocolVersion") != PROTOCOL_VERSION:
            result["classification"] = "protocol_mismatch"
            return result
        headers["MCP-Protocol-Version"] = PROTOCOL_VERSION
        result["counts"]["initialized"] = 1
        request("notifications/initialized")
        listed = request("tools/list", 2)
        rows = listed.get("tools")
        if (not isinstance(rows, list) or not 1 <= len(rows) <= 64 or listed.get("nextCursor") is not None
                or any(not isinstance(row, dict) or not isinstance(row.get("name"), str) for row in rows)
                or len({row["name"] for row in rows}) != len(rows)):
            raise ValueError()
        selected = [row for row in rows if row["name"] == TOOL]
        if len(selected) != 1:
            raise ValueError()
        tool = selected[0]
        schema = tool.get("inputSchema")
        _schema(schema)
        if not Draft202012Validator(schema).is_valid(ARGUMENTS):
            raise ValueError()
        annotations = tool.get("annotations", {})
        if (not isinstance(annotations, dict) or annotations.get("readOnlyHint") is False
                or annotations.get("destructiveHint") is True):
            raise ValueError()
        result["counts"]["listed_tools"] = len(rows)
        result["counts"]["input_contract_valid"] = 1
        # Store only the selected bounded contract, not instructions or unrelated
        # tool definitions. It remains untrusted until explicitly registered.
        contract = {"input_schema": schema, "output_schema": tool.get("outputSchema")}
        if len(_body(contract)) > 32768:
            raise ValueError()
        result["observed_contract"] = contract
        result["contract_sha256"] = hashlib.sha256(_body(contract)).hexdigest()
        registration = None
        if isinstance(contract["output_schema"], dict):
            candidate = {"id": "parallel-fetch", "url": ENDPOINT, "tool": TOOL,
                **contract, "max_output_bytes": 131072, "timeout_seconds": 60,
                "protocol_version": PROTOCOL_VERSION}
            try:
                registration, _ = _registration(candidate)
            except Exception:
                pass
        result["counts"]["generic_registration_compatible"] = int(registration is not None)
        output = request("tools/call", 3, {"name": TOOL, "arguments": ARGUMENTS})
        if output.get("isError", False) is not False:
            result["classification"] = "tool_failed"
            return result
        structured = output.get("structuredContent")
        blocks = output.get("content")
        if (not isinstance(blocks, list) or not 1 <= len(blocks) <= 32
                or any(not isinstance(block, dict) or block.get("type") != "text"
                       or not isinstance(block.get("text"), str) for block in blocks)):
            raise ValueError()
        text = "\n".join(block["text"] for block in blocks)
        if not text.strip() or len(text.encode()) > 131072 or _EXTRACT_URL not in text:
            raise ValueError()
        result["counts"]["content_bytes"] = len(text.encode())
        result["counts"]["structured_result_valid"] = int(registration is not None
            and isinstance(structured, dict)
            and Draft202012Validator(registration["output_schema"]).is_valid(structured))
        result["classification"] = "success"
    except ServiceError:
        pass
    except (ValueError, TypeError, KeyError, RecursionError):
        result["classification"] = "schema_invalid"
    except Exception:
        result["classification"] = "transport_unknown"
    return result
