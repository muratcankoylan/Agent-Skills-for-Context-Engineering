"""One-attempt, metadata-only Raindrop cloud export.

Delivery receipts are observations, not effect/budget authority. In particular,
an unknown result must not restart research work or imply exactly-once delivery.
No environment discovery, SDK instrumentation, retries, or local daemon setup.
"""

from __future__ import annotations

import base64
import http.client
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Callable, Mapping

from researcher.service.contracts import ServiceError
from researcher.service import tracing

ENDPOINT = "https://api.raindrop.ai/v1/traces"
MAX_REQUEST_BYTES = 1_048_576
MAX_RESPONSE_BYTES = 65_536
TIMEOUT_SECONDS = 10
Transport = Callable[[str, Mapping[str, str], bytes, int], tuple[int, Mapping[str, str], bytes]]
_FRAMING = {"content-type", "content-length", "content-encoding", "transfer-encoding"}
_CODES = frozenset({"WALL_TIMEOUT", "TIMEOUT", "TRANSPORT_ERROR", "WORKER_START_FAILED",
                    "WORKER_FAILED", "MALFORMED_TRANSPORT", "RESPONSE_TOO_LARGE"})


class _TransportError(Exception):
    def __init__(self, code: str):
        self.code = code if code in _CODES else "TRANSPORT_ERROR"
        super().__init__(self.code)


def _json(raw: bytes) -> dict:
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("duplicate")
            value[key] = item
        return value

    def constant(_value):
        raise ValueError("constant")

    value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique, parse_constant=constant)
    if not isinstance(value, dict):
        raise ValueError("object")
    return value


def _headers(headers: Mapping[str, str]) -> dict[str, str]:
    if not isinstance(headers, Mapping) or len(headers) > 100:
        raise _TransportError("MALFORMED_TRANSPORT")
    result = {}
    for key, value in headers.items():
        if (not isinstance(key, str) or not isinstance(value, str) or len(key) > 128
                or len(value) > 4096 or not re.fullmatch(r"[A-Za-z0-9-]+", key)
                or any(ord(char) < 32 or ord(char) > 126 for char in value)):
            raise _TransportError("MALFORMED_TRANSPORT")
        lowered = key.lower()
        if lowered in result:
            raise _TransportError("MALFORMED_TRANSPORT")
        result[lowered] = value
    if ("content-length" in result and "transfer-encoding" in result
            or result.get("transfer-encoding", "chunked").lower() != "chunked"):
        raise _TransportError("MALFORMED_TRANSPORT")
    return result


def _native(url: str, headers: Mapping[str, str], body: bytes, timeout: int):
    if url != ENDPOINT:
        raise _TransportError("MALFORMED_TRANSPORT")
    connection = http.client.HTTPSConnection("api.raindrop.ai", timeout=timeout)
    deadline = time.monotonic() + timeout
    try:
        connection.request("POST", "/v1/traces", body=body, headers=dict(headers))
        response = connection.getresponse()
        pairs = response.getheaders()
        for name in _FRAMING:
            if sum(key.lower() == name for key, _ in pairs) > 1:
                raise _TransportError("MALFORMED_TRANSPORT")
        selected = _headers({key: value for key, value in pairs if key.lower() in _FRAMING})
        if response.status != 200:
            return response.status, selected, b""  # Never copy a remote error body.
        if ("content-length" in selected and (not re.fullmatch(r"[0-9]{1,10}", selected["content-length"])
                or int(selected["content-length"]) > MAX_RESPONSE_BYTES)):
            raise _TransportError("RESPONSE_TOO_LARGE")
        chunks, size = [], 0
        while size <= MAX_RESPONSE_BYTES:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise _TransportError("TIMEOUT")
            if connection.sock is not None:
                connection.sock.settimeout(remaining)
            chunk = response.read1(min(8192, MAX_RESPONSE_BYTES + 1 - size))
            if not chunk:
                break
            size += len(chunk)
            chunks.append(chunk)
        if size > MAX_RESPONSE_BYTES:
            raise _TransportError("RESPONSE_TOO_LARGE")
        return response.status, selected, b"".join(chunks)
    finally:
        connection.close()


def _isolated(url: str, headers: Mapping[str, str], body: bytes, timeout: int, *, allow_default_project=False):
    # DNS, TLS and response-header parsing can outlive a socket read timeout.
    # An isolated process places the whole single request under one wall limit.
    packet = {"url": url, "headers": dict(headers), "body": base64.b64encode(body).decode(),
              "timeout": timeout}
    if allow_default_project:
        packet["allow_default_project"] = allow_default_project
    root = Path(__file__).resolve().parents[2]
    try:
        process = subprocess.run([sys.executable, "-B", "-m", "researcher.service.trace_export"],
            input=json.dumps(packet).encode(), capture_output=True, cwd=root, timeout=timeout, check=False,
            env={"PATH": os.defpath, "PYTHONPATH": str(root), "PYTHONUTF8": "1"})
    except subprocess.TimeoutExpired:
        raise _TransportError("WALL_TIMEOUT") from None
    except OSError:
        raise _TransportError("WORKER_START_FAILED") from None
    if process.returncode or process.stderr or len(process.stdout) > 2 * MAX_RESPONSE_BYTES:
        raise _TransportError("WORKER_FAILED")
    try:
        data = _json(process.stdout)
        if set(data) == {"error"}:
            code = data["error"]
            raise _TransportError(code if isinstance(code, str) else "WORKER_FAILED")
        if set(data) != {"status", "headers", "body"}:
            raise ValueError("shape")
        return data["status"], data["headers"], base64.b64decode(data["body"], validate=True)
    except (ValueError, TypeError, KeyError, RecursionError):
        raise _TransportError("WORKER_FAILED") from None


def _result(span_count: int, status: str, *, rejected: int | None = None,
            warning: bool = False, error: str | None = None, attempted: bool = True) -> dict:
    return {"schema": "trace-export-result/v1", "status": status, "attempted": attempted,
            "span_count": span_count, "rejected_spans": rejected, "warning": warning, "error_code": error}


def preflight_config(*, credential: str, project_id: str, allow_default_project=False) -> dict:
    """Local, value-free diagnostics; no authentication or project lookup."""
    credential_valid = (isinstance(credential, str) and 1 <= len(credential) <= 4096
        and all(33 <= ord(char) <= 126 for char in credential))
    if project_id is None or project_id == "":
        project_category = "blank"
    elif not isinstance(project_id, str):
        project_category = "invalid_characters"
    elif project_id == "default":
        project_category = "explicit_default"
    elif len(project_id) > 63:
        project_category = "too_long"
    elif any("A" <= char <= "Z" for char in project_id):
        project_category = "uppercase"
    elif not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", project_id):
        project_category = "invalid_characters"
    elif re.fullmatch(r"[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}", project_id):
        # UUID-shaped strings satisfy the documented slug grammar. Shape does
        # not establish that this is the desired existing project.
        project_category = "uuid_like_slug"
    else:
        project_category = "explicit_slug"
    project_valid = (project_category in {"explicit_slug", "uuid_like_slug"}
                     or project_category == "explicit_default" and allow_default_project is True)
    errors = ([] if credential_valid else ["TRACE_EXPORT_INVALID_CREDENTIAL"])
    if type(allow_default_project) is not bool:
        errors.append("TRACE_EXPORT_INVALID_DEFAULT_APPROVAL")
    if not project_valid:
        errors.append("TRACE_EXPORT_DEFAULT_PROJECT_REQUIRES_APPROVAL" if project_category == "explicit_default"
                      else "TRACE_EXPORT_INVALID_PROJECT")
    return {"schema": "trace-export-preflight/v1", "local_ready": not errors,
            "network_checked": False, "authentication_verified": False,
            "project_verified": False, "production_ready": False,
            "credential": "set" if isinstance(credential, str) and credential else "empty",
            "credential_syntax_valid": credential_valid, "project_category": project_category,
            "default_project_approved": allow_default_project is True,
            "error_codes": errors}


def _prepare(payload: dict, credential: str, project_id: str, *, allow_default_project=False):
    tracing.validate_otlp(payload)
    preflight = preflight_config(credential=credential, project_id=project_id,
                                 allow_default_project=allow_default_project)
    if preflight["error_codes"]:
        # Keep the established transport API's project error; richer categories
        # are available through the separate zero-effect preflight command.
        code = preflight["error_codes"][0]
        raise ServiceError("TRACE_EXPORT_INVALID_PROJECT" if code == "TRACE_EXPORT_DEFAULT_PROJECT_REQUIRES_APPROVAL" else code)
    try:
        body = json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
        count = sum(len(scope["spans"]) for resource in payload["resourceSpans"] for scope in resource["scopeSpans"])
    except (UnicodeError, ValueError, TypeError, KeyError, RecursionError):
        raise ServiceError("TRACE_EXPORT_INVALID_PAYLOAD") from None
    if not 1 <= count <= 100 or len(body) > MAX_REQUEST_BYTES:
        raise ServiceError("TRACE_EXPORT_INVALID_PAYLOAD")
    if credential.encode("ascii") in body or credential in project_id:
        raise ServiceError("TRACE_EXPORT_CREDENTIAL_REFLECTION")
    headers = {"Content-Type": "application/json", "Accept": "application/json", "Accept-Encoding": "identity",
               "Authorization": f"Bearer {credential}", "X-Raindrop-Project-Id": project_id}
    return body, count, headers


def export_payload(payload: dict, *, credential: str, project_id: str,
                   transport: Transport | None = None, allow_default_project=False) -> dict:
    """Validate before any I/O; return only bounded enums/counts, never wire text.

    The injected transport is for trusted offline tests. Production always uses
    the isolated fixed-origin transport, no redirects, ambient proxies or retry.
    """
    body, count, headers = _prepare(payload, credential, project_id,
                                    allow_default_project=allow_default_project)
    try:
        if transport is None:
            status, response_headers, raw = _isolated(ENDPOINT, headers, body, TIMEOUT_SECONDS,
                                                     allow_default_project=allow_default_project)
        else:
            status, response_headers, raw = transport(ENDPOINT, headers, body, TIMEOUT_SECONDS)
        if type(status) is not int or not 100 <= status <= 599 or not isinstance(raw, bytes):
            raise _TransportError("MALFORMED_TRANSPORT")
        lowered = _headers(response_headers)
    except _TransportError as error:
        return _result(count, "unknown", error=error.code, attempted=error.code != "WORKER_START_FAILED")
    except TimeoutError:
        return _result(count, "unknown", error="TIMEOUT")
    except Exception:
        return _result(count, "unknown", error="TRANSPORT_ERROR")
    if 300 <= status <= 399:
        return _result(count, "unknown", error="REDIRECT_REFUSED")
    if 400 <= status <= 499:
        return _result(count, "rejected", rejected=count, error="HTTP_REJECTED")
    if status != 200:
        return _result(count, "unknown", error="UNEXPECTED_HTTP_STATUS")
    if len(raw) > MAX_RESPONSE_BYTES:
        return _result(count, "unknown", error="RESPONSE_TOO_LARGE")
    if lowered.get("content-type", "").split(";", 1)[0].strip().lower() != "application/json":
        return _result(count, "unknown", error="UNEXPECTED_CONTENT_TYPE")
    if lowered.get("content-encoding", "identity").lower() != "identity":
        return _result(count, "unknown", error="UNEXPECTED_ENCODING")
    length = lowered.get("content-length")
    if length is not None and (not re.fullmatch(r"[0-9]{1,10}", length) or int(length) != len(raw)):
        return _result(count, "unknown", error="INVALID_RESPONSE_LENGTH")
    try:
        data = _json(raw)
        if set(data) - {"partialSuccess"}:
            raise ValueError("shape")
        partial = data.get("partialSuccess", {})
        if not isinstance(partial, dict) or set(partial) - {"rejectedSpans", "errorMessage"}:
            raise ValueError("shape")
        rejected, message = partial.get("rejectedSpans", 0), partial.get("errorMessage", "")
        if isinstance(rejected, str) and re.fullmatch(r"0|[1-9][0-9]{0,2}", rejected):
            rejected = int(rejected)
        if (type(rejected) is not int or not 0 <= rejected <= count or not isinstance(message, str)
                or len(message) > 8192):
            raise ValueError("values")
        message.encode("utf-8")
        return _result(count, "partial" if rejected else "exported", rejected=rejected,
                       warning=bool(message), error="PARTIAL_REJECTION" if rejected else None)
    except (ValueError, UnicodeError, TypeError, RecursionError):
        return _result(count, "unknown", error="MALFORMED_ACKNOWLEDGEMENT")


def _worker() -> None:
    # Internal child receives its credential only on stdin and emits bounded
    # framing/body or a fixed error code. No exception/HTTP diagnostics escape.
    try:
        raw = sys.stdin.buffer.read(2 * MAX_REQUEST_BYTES + 1)
        if len(raw) > 2 * MAX_REQUEST_BYTES:
            raise _TransportError("WORKER_FAILED")
        packet = _json(raw)
        if (set(packet) not in ({"url", "headers", "body", "timeout"},
                               {"url", "headers", "body", "timeout", "allow_default_project"})
                or packet["url"] != ENDPOINT or packet["timeout"] != TIMEOUT_SECONDS
                or type(packet.get("allow_default_project", False)) is not bool):
            raise _TransportError("WORKER_FAILED")
        incoming = packet["headers"]
        if not isinstance(incoming, dict) or not isinstance(incoming.get("Authorization"), str):
            raise _TransportError("WORKER_FAILED")
        auth = incoming["Authorization"]
        if not auth.startswith("Bearer "):
            raise _TransportError("WORKER_FAILED")
        raw_body = base64.b64decode(packet["body"], validate=True)
        body, _, headers = _prepare(_json(raw_body), auth[7:], incoming.get("X-Raindrop-Project-Id"),
                                    allow_default_project=packet.get("allow_default_project", False))
        if incoming != headers or body != raw_body:
            raise _TransportError("WORKER_FAILED")
        status, headers, body = _native(packet["url"], headers, body, packet["timeout"])
        result = {"status": status, "headers": headers, "body": base64.b64encode(body).decode()}
    except _TransportError as error:
        result = {"error": error.code}
    except TimeoutError:
        result = {"error": "TIMEOUT"}
    except Exception:
        result = {"error": "TRANSPORT_ERROR"}
    sys.stdout.write(json.dumps(result, separators=(",", ":")))


if __name__ == "__main__":
    _worker()
