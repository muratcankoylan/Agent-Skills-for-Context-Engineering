"""Credential-isolated process boundary for live registered MCP observations.

Use bounded_collect_mcp from live workflows. Raw collect_mcp/read_tool are
internal adapters: third-party SDK error logging can serialize remote payloads.
The dedicated child disables logging and never forwards incidental stdout or
stderr. This is not a sandbox for arbitrary code or a network egress policy.
"""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import logging
import os
from pathlib import Path
import re
import selectors
import subprocess
import sys
import time

from researcher.scripts.schema_contract import (
    canonicalize,
    parse_json_strict,
    sha256_bytes,
)
from .mcp_evidence import (
    MCPEvidenceError,
    _contains_secret,
    _normalize,
    collect_mcp,
    validate_read,
)
from .tracing import annotate, instrument

MAX_INPUT_BYTES = 65_536
MAX_OUTPUT_BYTES = 262_144
SETUP_ALLOWANCE_SECONDS = 5


def _exchange(process, payload: bytes, deadline: float) -> bytes:
    """Concurrent bounded stdin/stdout, including child exit in one deadline."""
    output, offset = bytearray(), 0
    with selectors.DefaultSelector() as selector:
        for stream, event in (
            (process.stdin, selectors.EVENT_WRITE),
            (process.stdout, selectors.EVENT_READ),
        ):
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, event)
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise MCPEvidenceError(
                    "MCP_WALL_TIMEOUT", ambiguous=True, call_attempted=True
                )
            for key, _ in selector.select(remaining):
                stream = key.fileobj
                if stream is process.stdin:
                    try:
                        offset += os.write(
                            stream.fileno(), payload[offset : offset + 8192]
                        )
                    except BrokenPipeError:
                        offset = len(payload)
                    if offset == len(payload):
                        selector.unregister(stream)
                        stream.close()
                else:
                    chunk = os.read(stream.fileno(), 8192)
                    if not chunk:
                        selector.unregister(stream)
                        stream.close()
                    elif len(output) + len(chunk) > MAX_OUTPUT_BYTES:
                        raise MCPEvidenceError(
                            "MCP_WORKER_OUTPUT_LIMIT",
                            ambiguous=True,
                            call_attempted=True,
                        )
                    else:
                        output.extend(chunk)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise MCPEvidenceError(
                "MCP_WALL_TIMEOUT", ambiguous=True, call_attempted=True
            )
        try:
            status = process.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            raise MCPEvidenceError(
                "MCP_WALL_TIMEOUT", ambiguous=True, call_attempted=True
            ) from None
        if status:
            raise MCPEvidenceError(
                "MCP_WORKER_FAILED", ambiguous=True, call_attempted=True
            )
    return bytes(output)


def _run(payload: bytes, deadline: float) -> bytes:
    root = Path(__file__).resolve().parents[2]
    try:
        process = subprocess.Popen(
            [sys.executable, "-B", "-m", "researcher.service.mcp_worker"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            cwd=root,
            env={"PATH": os.defpath, "PYTHONPATH": str(root), "PYTHONUTF8": "1"},
        )
    except OSError:
        raise MCPEvidenceError("MCP_WORKER_START_FAILED") from None
    try:
        return _exchange(process, payload, deadline)
    except MCPEvidenceError:
        raise
    except Exception:
        raise MCPEvidenceError(
            "MCP_WORKER_FAILED", ambiguous=True, call_attempted=True
        ) from None
    finally:
        try:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=2)
        except (OSError, subprocess.TimeoutExpired):
            raise MCPEvidenceError(
                "MCP_WORKER_CLEANUP_FAILED", ambiguous=True, call_attempted=True
            ) from None
        finally:
            for stream in (process.stdin, process.stdout):
                if stream is not None:
                    stream.close()


def _verified_lane(
    config: dict, args: dict, lane: dict, credential: str | None
) -> dict:
    """Reconstruct the canonical contract, without claiming a new SDK observation."""
    text = lane["evidence"][0]["text"]
    value = parse_json_strict(text)
    raw = canonicalize(value)
    receipt = {
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
        "sdk_response_bytes": lane["sdk_response_bytes"],
        "output_limit_scope": "post_sdk_parse",
        "observation_only": True,
        "tool_calls": 1,
        "model_calls": 0,
    }
    if "sdk_response_sha256" in lane:
        receipt["sdk_response_sha256"] = lane["sdk_response_sha256"]
    expected = _normalize(config, args, receipt, credential)
    if canonicalize(lane) != canonicalize(expected):
        raise ValueError("record mismatch")
    return expected


@instrument("mcp.read")
def bounded_collect_mcp(
    registration: dict, arguments: dict, *, credential: str | None = None
) -> dict:
    """One isolated attempt; caller must commit request/cost reservation first."""
    annotate(provider="mcp", transport="subprocess")
    started = time.monotonic()
    try:
        validate_read(registration, arguments)
        if credential is not None and (
            not isinstance(credential, str)
            or not 8 <= len(credential) <= 4096
            or any(ord(char) < 33 or ord(char) > 126 for char in credential)
        ):
            raise MCPEvidenceError("INVALID_CREDENTIAL")
        if _contains_secret(registration, credential) or _contains_secret(
            arguments, credential
        ):
            raise MCPEvidenceError("CREDENTIAL_LEAK")
        payload = canonicalize(
            {
                "registration": registration,
                "arguments": arguments,
                "credential": credential,
            }
        )
        if len(payload) > MAX_INPUT_BYTES:
            raise MCPEvidenceError("MCP_WORKER_INPUT_LIMIT")
        request = parse_json_strict(payload.decode())
    except MCPEvidenceError:
        raise
    except Exception:
        raise MCPEvidenceError("INVALID_MCP_READ") from None
    deadline = (
        started + request["registration"]["timeout_seconds"] + SETUP_ALLOWANCE_SECONDS
    )
    if time.monotonic() >= deadline:
        raise MCPEvidenceError("MCP_WALL_TIMEOUT")
    raw = _run(payload, deadline)
    try:
        if len(raw) > MAX_OUTPUT_BYTES:
            raise ValueError("output limit")
        output = parse_json_strict(raw.decode("utf-8"))
        if _contains_secret(output, credential):
            raise ValueError("credential reflection")
        if set(output) == {"error", "ambiguous", "call_attempted"}:
            if (
                type(output["ambiguous"]) is not bool
                or type(output["call_attempted"]) is not bool
                or not isinstance(output["error"], str)
                or not re.fullmatch(r"[A-Z0-9_]{1,100}", output["error"])
            ):
                raise ValueError("error contract")
            if output["ambiguous"] and not output["call_attempted"]:
                raise ValueError("inconsistent error")
            raise MCPEvidenceError(
                output["error"],
                ambiguous=output["ambiguous"],
                call_attempted=output["call_attempted"],
            )
        if set(output) != {"result"}:
            raise ValueError("output contract")
        result = _verified_lane(
            request["registration"], request["arguments"], output["result"], credential
        )
        if time.monotonic() >= deadline:
            raise MCPEvidenceError(
                "MCP_WALL_TIMEOUT", ambiguous=True, call_attempted=True
            )
        return result
    except MCPEvidenceError:
        raise
    except Exception:
        raise MCPEvidenceError(
            "MCP_WORKER_OUTPUT_INVALID", ambiguous=True, call_attempted=True
        ) from None


def main() -> int:
    # Dedicated-process policy, not a concurrent global logger mutation in the
    # parent. SDK ERROR logs can contain malformed response bodies and secrets.
    logging.disable(sys.maxsize)
    try:
        raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
        if len(raw) > MAX_INPUT_BYTES:
            raise MCPEvidenceError("MCP_WORKER_INPUT_LIMIT")
        request = parse_json_strict(raw.decode("utf-8"))
        if set(request) != {"registration", "arguments", "credential"}:
            raise MCPEvidenceError("INVALID_MCP_READ")
        with (
            open(os.devnull, "w") as discard,
            redirect_stdout(discard),
            redirect_stderr(discard),
        ):
            result = collect_mcp(
                request["registration"],
                request["arguments"],
                credential=request["credential"],
            )
        output = {"result": result}
    except MCPEvidenceError as error:
        output = {
            "error": error.code,
            "ambiguous": error.ambiguous,
            "call_attempted": error.call_attempted,
        }
    except Exception:
        output = {
            "error": "MCP_WORKER_FAILED",
            "ambiguous": True,
            "call_attempted": True,
        }
    encoded = canonicalize(output)
    if len(encoded) > MAX_OUTPUT_BYTES:
        encoded = canonicalize(
            {
                "error": "MCP_WORKER_OUTPUT_LIMIT",
                "ambiguous": True,
                "call_attempted": True,
            }
        )
    sys.stdout.write(encoded.decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
