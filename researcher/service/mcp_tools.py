"""Manually registered MCP reads, with no ambient discovery or model callbacks.

The optional network bridge pins the maintained v1 SDK and one protocol revision.
Output limits apply AFTER SDK parsing, not to transport buffering. DNS is checked
but not socket-pinned: deployment MUST enforce public-endpoint egress and process
memory limits. Remote annotations cannot establish that a tool is actually read
only; operator registration and server-side least-privilege credentials must do
that. A timeout does not prove the remote tool did not execute. Do not enable SDK
payload/debug logging for credential-bearing sessions.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import timedelta
from importlib.metadata import PackageNotFoundError, version
import ipaddress
import json
import re
import socket
import ssl
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator
from .tracing import annotate, child_span, instrument

from researcher.scripts.schema_contract import (
    canonicalize,
    parse_json_strict,
    sha256_bytes,
)

SDK_VERSION = "1.30.0"
PROTOCOL_VERSION = "2025-11-25"
MAX_OUTPUT_BYTES = 131_072
_FIELDS = {
    "id",
    "url",
    "tool",
    "input_schema",
    "output_schema",
    "max_output_bytes",
    "timeout_seconds",
    "protocol_version",
}
_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")


class MCPToolError(ValueError):
    def __init__(
        self, code: str, *, call_attempted: bool = False, outcome_unknown: bool = False
    ):
        super().__init__(f"MCP read failed: {code}")
        self.code = code
        self.call_attempted = call_attempted
        self.outcome_unknown = outcome_unknown


def _safe_error_code(error: Exception, phase: str) -> str:
    """Preserve bounded typed causes through SDK task groups, never error text."""
    pending, seen, policy, statuses, timed_out, tls_failed = [error], set(), [], [], False, False
    while pending and len(seen) < 128:
        item = pending.pop()
        if id(item) in seen:
            continue
        seen.add(id(item))
        if isinstance(item, MCPToolError) and re.fullmatch(r"[A-Z0-9_]{1,100}", item.code):
            policy.append(item.code)
        if isinstance(item, TimeoutError):
            timed_out = True
        if isinstance(item, ssl.SSLCertVerificationError):
            tls_failed = True
        # The optional SDK depends on httpx, but base offline validation does not.
        if type(item).__module__ == "httpx" and type(item).__name__ == "HTTPStatusError":
            status = getattr(getattr(item, "response", None), "status_code", None)
            if type(status) is int:
                statuses.append(status)
        if isinstance(item, BaseExceptionGroup):
            pending.extend(item.exceptions[:128])
        for child in (item.__cause__, item.__context__):
            if isinstance(child, BaseException):
                pending.append(child)
    if policy:
        return sorted(policy)[0]
    if timed_out:
        return "TIMEOUT"
    if tls_failed:
        return "TLS_CERTIFICATE_INVALID"
    for status, code in ((401, "HTTP_AUTH_REJECTED"), (402, "HTTP_BILLING_BLOCKED"),
                         (403, "HTTP_PERMISSION_DENIED"), (429, "HTTP_RATE_LIMITED")):
        if status in statuses:
            return code
    return "MCP_" + phase + "_FAILED"


def _bound_structure(value: object, maximum: int) -> None:
    if not isinstance(value, dict):
        raise MCPToolError("INVALID_RECORD")
    pending, nodes = [(value, 0)], 0
    while pending:
        item, depth = pending.pop()
        nodes += 1
        if depth > 32 or nodes > 16_384:
            raise MCPToolError("RECORD_LIMIT")
        if isinstance(item, dict):
            pending.extend((child, depth + 1) for child in item.values())
        elif isinstance(item, list):
            pending.extend((child, depth + 1) for child in item)
        elif isinstance(item, str) and len(item) > maximum:
            raise MCPToolError("RECORD_LIMIT")


def _snapshot(value: object, maximum: int) -> tuple[dict, bytes]:
    _bound_structure(value, maximum)
    try:
        raw = canonicalize(value)
        if len(raw) > maximum:
            raise MCPToolError("RECORD_LIMIT")
        return parse_json_strict(raw.decode("utf-8")), raw
    except MCPToolError:
        raise
    except Exception:
        raise MCPToolError("INVALID_RECORD") from None


def _endpoint(url: object) -> str:
    try:
        if (
            not isinstance(url, str)
            or len(url) > 2048
            or any(ord(char) < 33 or ord(char) > 126 for char in url)
            or any(char in url for char in ("\\", "%", "?", "#"))
        ):
            raise ValueError
        parsed = urlsplit(url)
        host = parsed.hostname
        if (
            parsed.scheme != "https"
            or not host
            or parsed.username is not None
            or parsed.password is not None
            or parsed.port not in (None, 443)
            or any(part in (".", "..") for part in parsed.path.split("/"))
        ):
            raise ValueError
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            if (
                "." not in host
                or host.endswith(".")
                or host.rsplit(".", 1)[-1].isdigit()
                or any(
                    not re.fullmatch(
                        r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?", label
                    )
                    for label in host.split(".")
                )
                or host.endswith((".localhost", ".local", ".internal", ".home.arpa"))
            ):
                raise ValueError
        else:
            if not address.is_global:
                raise ValueError
        return host
    except (ValueError, TypeError):
        raise MCPToolError("UNSAFE_ENDPOINT") from None


def _schema(schema: object) -> None:
    if not isinstance(schema, dict) or schema.get("type") != "object":
        raise MCPToolError("INVALID_SCHEMA")
    pending = [schema]
    while pending:
        item = pending.pop()
        if isinstance(item, dict):
            # Never allow a validator or SDK to retrieve a remote reference.
            if (
                "$id" in item
                or "$dynamicRef" in item
                or "$recursiveRef" in item
                or (
                    "$ref" in item
                    and (
                        not isinstance(item["$ref"], str)
                        or not item["$ref"].startswith("#/")
                    )
                )
                or (
                    "$schema" in item
                    and item["$schema"]
                    != "https://json-schema.org/draft/2020-12/schema"
                )
            ):
                raise MCPToolError("INVALID_SCHEMA")
            pending.extend(item.values())
        elif isinstance(item, list):
            pending.extend(item)
    try:
        Draft202012Validator.check_schema(schema)
    except Exception:
        raise MCPToolError("INVALID_SCHEMA") from None


def _registration(value: dict) -> tuple[dict, bytes]:
    record, raw = _snapshot(value, 32_768)
    if set(record) != _FIELDS:
        raise MCPToolError("INVALID_REGISTRATION")
    for key in ("id", "tool"):
        if not isinstance(record[key], str) or not _NAME.fullmatch(record[key]):
            raise MCPToolError("INVALID_REGISTRATION")
    _endpoint(record["url"])
    if record["protocol_version"] != PROTOCOL_VERSION:
        raise MCPToolError("PROTOCOL_MISMATCH")
    if (
        type(record["timeout_seconds"]) is not int
        or not 1 <= record["timeout_seconds"] <= 120
        or type(record["max_output_bytes"]) is not int
        or not 1 <= record["max_output_bytes"] <= MAX_OUTPUT_BYTES
    ):
        raise MCPToolError("INVALID_LIMIT")
    for key in ("input_schema", "output_schema"):
        _schema(record[key])
    return record, raw


def _record(value: object, maximum: int) -> tuple[dict, bytes]:
    if not isinstance(value, dict) and callable(getattr(value, "model_dump", None)):
        value = value.model_dump(mode="json", by_alias=True, exclude_none=True)
    return _snapshot(value, maximum)


def _tool_record(value: object, maximum: int) -> tuple[dict, bytes]:
    """Bound the whole SDK envelope; canonicalize only selected evidence.

MCP annotations and envelope metadata permit finite JSON floats. They are not
durable research evidence. Keep a byte count/digest of the full SDK JSON while
requiring the exact structured value to satisfy our integer-only record profile.
This serialization is NOT the original HTTP bytes.
"""
    if not isinstance(value, dict) and callable(getattr(value, "model_dump", None)):
        value = value.model_dump(mode="json", by_alias=True, exclude_none=True)
    _bound_structure(value, maximum)
    try:
        encoded = json.dumps(value, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False, allow_nan=False).encode("utf-8")
        if len(encoded) > maximum:
            raise MCPToolError("RECORD_LIMIT")
        selected, _ = _snapshot({key: value.get(key) for key in ("isError", "structuredContent")}, maximum)
        return selected, encoded
    except MCPToolError:
        raise
    except Exception:
        raise MCPToolError("INVALID_RECORD") from None


async def _public_dns(host: str) -> None:
    addresses = await asyncio.get_running_loop().getaddrinfo(
        host, 443, type=socket.SOCK_STREAM
    )
    if not addresses or len(addresses) > 32:
        raise MCPToolError("UNSAFE_ENDPOINT")
    try:
        if any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
            raise ValueError
    except ValueError:
        raise MCPToolError("UNSAFE_ENDPOINT") from None


@asynccontextmanager
async def _sdk_session(*, registration: dict, credential: str | None):
    try:
        if version("mcp") != SDK_VERSION:
            raise MCPToolError("SDK_VERSION_MISMATCH")
        import httpx
        from mcp import ClientSession
        from mcp.client.streamable_http import streamable_http_client
        from mcp.types import LATEST_PROTOCOL_VERSION
    except (ImportError, PackageNotFoundError):
        raise MCPToolError("SDK_UNAVAILABLE") from None
    if LATEST_PROTOCOL_VERSION != PROTOCOL_VERSION:
        raise MCPToolError("PROTOCOL_MISMATCH")
    endpoint = httpx.URL(registration["url"])
    requests, methods = 0, set()

    async def request_guard(request):
        nonlocal requests
        requests += 1
        if (
            requests > 12
            or request.url != endpoint
            or request.method not in {"GET", "POST"}
        ):
            raise MCPToolError("OUTBOUND_POLICY")
        if request.method == "POST":
            message = parse_json_strict(request.content.decode("utf-8"))
            method = message.get("method")
            if (
                method
                not in {
                    "initialize",
                    "notifications/initialized",
                    "tools/list",
                    "tools/call",
                }
                or method in methods
            ):
                raise MCPToolError("OUTBOUND_POLICY")
            if (
                method == "tools/call"
                and message.get("params", {}).get("name") != registration["tool"]
            ):
                raise MCPToolError("OUTBOUND_POLICY")
            methods.add(method)
        await _public_dns(endpoint.host)

    async def response_guard(response):
        # v1.30 follows same-origin redirects independently of follow_redirects.
        if 300 <= response.status_code < 400:
            raise MCPToolError("REDIRECT_FORBIDDEN")

    headers = (
        {"Authorization": f"Bearer {credential}"} if credential is not None else {}
    )
    async with httpx.AsyncClient(
        headers=headers,
        trust_env=False,
        follow_redirects=False,
        timeout=httpx.Timeout(registration["timeout_seconds"]),
        event_hooks={"request": [request_guard], "response": [response_guard]},
    ) as client:
        async with streamable_http_client(
            registration["url"],
            http_client=client,
            terminate_on_close=False,
        ) as (read, write, _):
            async with ClientSession(
                read,
                write,
                read_timeout_seconds=timedelta(seconds=registration["timeout_seconds"]),
            ) as session:
                yield session


@instrument("mcp.read")
async def read_tool(
    registration: dict,
    arguments: dict,
    *,
    credential: str | None = None,
    session_factory=None,
) -> dict:
    """Read one operator-registered tool after exact, bounded tools/list matching.

    A trusted injected factory is an async context manager accepting keyword
    ``registration`` and ``credential`` and yielding an SDK-shaped session with
    async initialize(), list_tools(), call_tool(name, arguments=...). The factory
    owns no policy. Neither server instructions nor tool annotations grant access.
    This profile requires structuredContent and integer-only canonical JSON.
    """
    attempted, returned, phase = False, False, "ADMISSION"
    annotate(provider="mcp", transport="mcp")
    loop = asyncio.get_running_loop()
    began = loop.time()
    try:
        config, config_bytes = _registration(registration)
        args, args_bytes = _snapshot(arguments, 16_384)
        if credential is not None and (
            not isinstance(credential, str)
            or not 8 <= len(credential) <= 4096
            or any(ord(char) < 33 or ord(char) > 126 for char in credential)
        ):
            raise MCPToolError("INVALID_CREDENTIAL")
        if credential is not None and credential.encode() in config_bytes + args_bytes:
            raise MCPToolError("CREDENTIAL_LEAK")
        if not Draft202012Validator(config["input_schema"]).is_valid(args):
            raise MCPToolError("INPUT_SCHEMA_MISMATCH")
        factory = _sdk_session if session_factory is None else session_factory
        deadline = began + config["timeout_seconds"]
        if loop.time() >= deadline:
            raise TimeoutError
        async with asyncio.timeout(deadline - loop.time()):
            phase = "CONNECT"
            async with factory(
                registration=parse_json_strict(config_bytes.decode()),
                credential=credential,
            ) as session:
                phase = "INITIALIZE"
                with child_span("mcp.initialize"):
                    initialized, _ = _record(await session.initialize(), 32_768)
                if initialized.get("protocolVersion") != config["protocol_version"]:
                    raise MCPToolError("PROTOCOL_MISMATCH")
                phase = "LIST"
                with child_span("mcp.list"):
                    listing, _ = _record(await session.list_tools(), 524_288)
                tools = listing.get("tools")
                if (
                    not isinstance(tools, list)
                    or not 1 <= len(tools) <= 64
                    or listing.get("nextCursor") is not None
                ):
                    raise MCPToolError("TOOL_LIST_LIMIT")
                if any(
                    not isinstance(tool, dict) or not isinstance(tool.get("name"), str)
                    for tool in tools
                ):
                    raise MCPToolError("TOOL_IDENTITY_MISMATCH")
                if len({tool["name"] for tool in tools}) != len(tools):
                    raise MCPToolError("TOOL_IDENTITY_MISMATCH")
                selected = [tool for tool in tools if tool["name"] == config["tool"]]
                if len(selected) != 1:
                    raise MCPToolError("TOOL_IDENTITY_MISMATCH")
                tool = selected[0]
                for remote, local in (
                    ("inputSchema", "input_schema"),
                    ("outputSchema", "output_schema"),
                ):
                    if canonicalize(tool.get(remote)) != canonicalize(config[local]):
                        raise MCPToolError("TOOL_SCHEMA_MISMATCH")
                annotations = tool.get("annotations", {})
                if (
                    not isinstance(annotations, dict)
                    or annotations.get("readOnlyHint") is False
                    or annotations.get("destructiveHint") is True
                ):
                    raise MCPToolError("TOOL_READ_CONFLICT")
                attempted = True
                phase = "CALL"
                with child_span("mcp.invoke"):
                    response = await session.call_tool(config["tool"], arguments=args)
                returned = True
                phase = "RESULT"
                result, result_bytes = _tool_record(response, config["max_output_bytes"])
                if credential is not None and (credential.encode() in result_bytes
                        or json.dumps(credential, ensure_ascii=False)[1:-1].encode() in result_bytes):
                    raise MCPToolError("CREDENTIAL_LEAK")
                if type(result.get("isError")) is not bool or result["isError"]:
                    raise MCPToolError("TOOL_FAILED")
                value = result.get("structuredContent")
                if not isinstance(value, dict):
                    raise MCPToolError("STRUCTURED_OUTPUT_REQUIRED")
                if not Draft202012Validator(config["output_schema"]).is_valid(value):
                    raise MCPToolError("OUTPUT_SCHEMA_MISMATCH")
                if loop.time() >= deadline:
                    raise TimeoutError
                value_bytes = canonicalize(value)
                output = {
                    "schema": "research-mcp-read/v1",
                    "authority": "none",
                    "registration_id": config["id"],
                    "registration_sha256": sha256_bytes(config_bytes),
                    "tool": config["tool"],
                    "protocol_version": config["protocol_version"],
                    "arguments_sha256": sha256_bytes(args_bytes),
                    "value": value,
                    "value_sha256": sha256_bytes(value_bytes),
                    "output_bytes": len(value_bytes),
                    "sdk_response_bytes": len(result_bytes),
                    "sdk_response_sha256": sha256_bytes(result_bytes),
                    "output_limit_scope": "post_sdk_parse",
                    "observation_only": True,
                    "tool_calls": 1,
                    "model_calls": 0,
                }
                phase = "EXIT"
            if loop.time() >= deadline:
                raise TimeoutError
            annotate(input_bytes=len(args_bytes), output_bytes=len(value_bytes), outcome="completed")
            return output
    except asyncio.CancelledError:
        raise
    except Exception as error:
        code = _safe_error_code(error, phase)
        raise MCPToolError(
            code, call_attempted=attempted, outcome_unknown=attempted and not returned
        ) from None
