"""Synchronous, observation-only MCP evidence for the durable service boundary.

The caller must reserve 12 source requests and its operator-declared cost ceiling
before calling. This module does not reserve, retry, discover, install, or grant
authority. The request ceiling is not measured usage; MCP cost remains unknown.
The gateway's output cap is post-SDK-parse, so deployment still needs egress and
process-memory controls. Canonical structured values are not raw HTTP captures.
"""

from __future__ import annotations

import asyncio
import re

from jsonschema import Draft202012Validator

from researcher.scripts.schema_contract import canonicalize, sha256_bytes

from .contracts import SLUG, ServiceError
from .mcp_tools import MCPToolError, _registration, _snapshot, read_tool
from .tracing import instrument

MAX_REQUESTS = 12


class MCPEvidenceError(ServiceError):
    """Safe failure metadata used to quarantine uncertain remote outcomes."""

    def __init__(self, code: str, *, ambiguous=False, call_attempted=False):
        if not isinstance(code, str) or not re.fullmatch(r"[A-Z0-9_]{1,100}", code):
            code = "MCP_EVIDENCE_FAILED"
        super().__init__(code)
        self.ambiguous = bool(ambiguous)
        self.call_attempted = bool(call_attempted)


def _inputs(registration: dict, arguments: dict) -> tuple[dict, dict]:
    config, _ = _registration(registration)
    if not re.fullmatch(SLUG, config["id"]):
        raise MCPToolError("INVALID_REGISTRATION")
    args, _ = _snapshot(arguments, 16_384)
    if not Draft202012Validator(config["input_schema"]).is_valid(args):
        raise MCPToolError("INPUT_SCHEMA_MISMATCH")
    return config, args


def validate_read(registration: dict, arguments: dict) -> None:
    """Validate detached, bounded configuration and arguments without DNS or I/O."""
    try:
        _inputs(registration, arguments)
    except Exception as error:
        code = error.code if isinstance(error, MCPToolError) else "INVALID_MCP_READ"
        raise MCPEvidenceError(code) from None


def validate_registration(registration: dict) -> None:
    """Reject malformed unused registrations at configuration admission too."""
    try:
        config, _ = _registration(registration)
        if not re.fullmatch(SLUG, config["id"]):
            raise MCPToolError("INVALID_REGISTRATION")
    except Exception as error:
        code = error.code if isinstance(error, MCPToolError) else "INVALID_MCP_REGISTRATION"
        raise MCPEvidenceError(code) from None


def _contains_secret(value: object, credential: str | None) -> bool:
    if credential is None:
        return False
    pending = [value]
    while pending:
        item = pending.pop()
        if isinstance(item, dict):
            pending.extend(item.keys())
            pending.extend(item.values())
        elif isinstance(item, list):
            pending.extend(item)
        elif isinstance(item, str) and credential in item:
            return True
    return False


def _normalize(config: dict, args: dict, result: dict, credential: str | None) -> dict:
    saved, _ = _snapshot(result, config["max_output_bytes"] + 4096)
    if _contains_secret(saved, credential):
        raise MCPToolError("CREDENTIAL_LEAK")
    value = saved.get("value")
    if not isinstance(value, dict) or not Draft202012Validator(
        config["output_schema"]
    ).is_valid(value):
        raise MCPToolError("OUTPUT_SCHEMA_MISMATCH")
    value_bytes = canonicalize(value)
    output_digest = sha256_bytes(value_bytes)
    registration_digest = sha256_bytes(canonicalize(config))
    arguments_digest = sha256_bytes(canonicalize(args))
    response_size = saved.get("sdk_response_bytes")
    envelope_hash = saved.get("sdk_response_sha256")
    if envelope_hash is not None and (
        not isinstance(envelope_hash, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", envelope_hash)
    ):
        raise MCPToolError("MCP_RECEIPT_MISMATCH")
    if (
        len(value_bytes) > config["max_output_bytes"]
        or type(response_size) is not int
        or not len(value_bytes) <= response_size <= config["max_output_bytes"]
    ):
        raise MCPToolError("OUTPUT_LIMIT")
    expected = {
        "schema": "research-mcp-read/v1",
        "authority": "none",
        "registration_id": config["id"],
        "registration_sha256": registration_digest,
        "tool": config["tool"],
        "protocol_version": config["protocol_version"],
        "arguments_sha256": arguments_digest,
        "value": value,
        "value_sha256": output_digest,
        "output_bytes": len(value_bytes),
        "sdk_response_bytes": response_size,
        "output_limit_scope": "post_sdk_parse",
        "observation_only": True,
        "tool_calls": 1,
        "model_calls": 0,
    }
    # Backward-compatible receipts without this field remain valid. New bridge
    # observations bind the complete SDK JSON envelope, not original HTTP bytes.
    envelope = {"sdk_response_sha256": envelope_hash} if envelope_hash is not None else {}
    expected.update(envelope)
    # Canonical comparison distinguishes boolean/integer substitutions.
    if canonicalize(saved) != canonicalize(expected):
        raise MCPToolError("MCP_RECEIPT_MISMATCH")
    identity = sha256_bytes(
        canonicalize([registration_digest, arguments_digest, output_digest])
    ).split(":", 1)[1]
    source = "mcp:" + config["id"]
    provenance = {
        "authority": "none",
        "registration_sha256": registration_digest,
        "arguments_sha256": arguments_digest,
        "output_sha256": output_digest,
        "tool": config["tool"],
        "protocol_version": config["protocol_version"],
        "representation": "canonical_structured_value",
        "output_limit_scope": "post_sdk_parse",
    }
    return {
        "source": source,
        "state": "observed",
        "authority": "none",
        "evidence": [
            {
                "id": "mcp-" + identity,
                "source": source,
                "url": config["url"],
                "text": value_bytes.decode("utf-8"),
                "sha256": output_digest,
                "evidence_scope": "mcp_observation",
                "metadata": provenance,
            }
        ],
        "next_cursor": None,
        "registration_sha256": registration_digest,
        "arguments_sha256": arguments_digest,
        "output_sha256": output_digest,
        "request_reservation": {
            "source_requests": MAX_REQUESTS,
            "scope": "http_request_ceiling",
            "actual_requests_measured": False,
        },
        "cost_status": "unknown",
        "operator_cost_allowance_required": True,
        "tool_calls": 1,
        "model_calls": 0,
        "output_bytes": len(value_bytes),
        "sdk_response_bytes": response_size,
        **envelope,
        "semantic_quality_measured": False,
    }


@instrument("mcp.read")
def collect_mcp(
    registration: dict, arguments: dict, *, credential: str | None = None
) -> dict:
    """Read exactly one registered tool, producing one literal evidence record.

    This sync adapter must run outside an active asyncio event loop. A failure
    after dispatch but before a response is observed is not safe to retry.
    """
    try:
        config, args = _inputs(registration, arguments)
        if credential is not None and (
            not isinstance(credential, str)
            or not 8 <= len(credential) <= 4096
            or any(ord(char) < 33 or ord(char) > 126 for char in credential)
        ):
            raise MCPToolError("INVALID_CREDENTIAL")
        if _contains_secret(config, credential) or _contains_secret(args, credential):
            raise MCPToolError("CREDENTIAL_LEAK")
    except Exception as error:
        code = error.code if isinstance(error, MCPToolError) else "INVALID_MCP_READ"
        raise MCPEvidenceError(code) from None
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        pass
    else:
        raise MCPEvidenceError("ASYNC_CONTEXT_UNSUPPORTED")
    try:
        result = asyncio.run(read_tool(config, args, credential=credential))
    except MCPToolError as error:
        raise MCPEvidenceError(
            error.code,
            ambiguous=error.outcome_unknown,
            call_attempted=error.call_attempted,
        ) from None
    except (Exception, asyncio.CancelledError):
        raise MCPEvidenceError(
            "MCP_READ_FAILED", ambiguous=True, call_attempted=True
        ) from None
    try:
        return _normalize(config, args, result, credential)
    except Exception as error:
        code = error.code if isinstance(error, MCPToolError) else "MCP_EVIDENCE_FAILED"
        raise MCPEvidenceError(code, call_attempted=True) from None
