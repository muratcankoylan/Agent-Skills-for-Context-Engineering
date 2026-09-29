"""Bounded transport for the managed Agents API, not Responses or Agents SDK.

The caller owns admission, durable write intent, polling and reconciliation.
One call makes one request. A local timeout does not stop a remote session.
No public per-session cost/token budget field is assumed by this adapter.
"""

from __future__ import annotations

import base64
import http.client
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Callable, Mapping
from urllib.parse import quote, unquote, urlencode, urlsplit
from .tracing import annotate, instrument

MAX_BYTES = 1_048_576
BASE_URL = "https://api.openai.com/v1/agents/sessions"
Transport = Callable[[str, str, Mapping[str, str], bytes | None, int], tuple[int, Mapping[str, str], bytes]]


class AgentsError(Exception):
    def __init__(self, code: str, ambiguous: bool = True, *, session_id: str | None = None):
        self.code, self.ambiguous = code, ambiguous
        self.session_id = session_id
        super().__init__(f"Managed Agents request failed: {code}.")


def _fail(code: str, ambiguous: bool = True) -> None:
    raise AgentsError(code, ambiguous) from None


def _identifier(value: object, *, ambiguous: bool = True) -> str:
    if (not isinstance(value, str) or len(value) > 200
            or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", value) is None):
        _fail("INVALID_IDENTIFIER", ambiguous)
    return value


def _parse_json(raw: bytes) -> dict:
    def pairs(entries):
        result = {}
        for key, value in entries:
            if key in result:
                _fail("MALFORMED_JSON")
            result[key] = value
        return result

    def constant(_value):
        _fail("MALFORMED_JSON")

    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant)
    except (UnicodeError, ValueError, RecursionError):
        _fail("MALFORMED_JSON")
    if not isinstance(value, dict):
        _fail("MALFORMED_JSON")
    return value


def _json_tree(value: object, credential: str, *, ambiguous: bool) -> None:
    pending, count = [(value, 0)], 0
    while pending:
        current, depth = pending.pop()
        count += 1
        if depth > 64 or count > 65_536:
            _fail("JSON_COMPLEXITY_LIMIT", ambiguous)
        if isinstance(current, str):
            try:
                current.encode("utf-8")
            except UnicodeError:
                _fail("MALFORMED_JSON", ambiguous)
            if credential and credential in current:
                _fail("CREDENTIAL_REFLECTION", ambiguous)
        elif isinstance(current, dict):
            if any(not isinstance(key, str) for key in current):
                _fail("MALFORMED_JSON", ambiguous)
            pending.extend((entry, depth + 1) for pair in current.items() for entry in pair)
        elif isinstance(current, list):
            pending.extend((entry, depth + 1) for entry in current)
        elif current is None or type(current) in (bool, int):
            continue
        elif type(current) is float and math.isfinite(current):
            continue
        else:
            _fail("MALFORMED_JSON", ambiguous)


def _decode(raw: bytes, credential: str, *, ambiguous: bool) -> dict:
    if credential and credential.encode("ascii") in raw:
        _fail("CREDENTIAL_REFLECTION", ambiguous)
    try:
        data = _parse_json(raw)
    except AgentsError as error:
        _fail(error.code, ambiguous)
    _json_tree(data, credential, ambiguous=ambiguous)
    return data


def _count(value: object) -> bool:
    return type(value) is int and 0 <= value <= 2**53 - 1


def _usage(value: object) -> None:
    if value is None:
        return  # Unknown is not zero; counts are not a final invoice.
    if not isinstance(value, dict):
        _fail("MALFORMED_USAGE")
    if not all(_count(value.get(key)) for key in ("input_tokens", "output_tokens", "total_tokens")):
        _fail("MALFORMED_USAGE")
    if value["input_tokens"] + value["output_tokens"] != value["total_tokens"]:
        _fail("MALFORMED_USAGE")
    for details, key, total in (("input_tokens_details", "cached_tokens", "input_tokens"),
                                ("output_tokens_details", "reasoning_tokens", "output_tokens")):
        part = value.get(details)
        if not isinstance(part, dict) or not _count(part.get(key)) or part[key] > value[total]:
            _fail("MALFORMED_USAGE")


def _session(data: dict, expected_id: str | None = None) -> dict:
    if (data.get("object") != "agent.session"
            or data.get("status") not in ("idle", "in_progress", "requires_action", "failed")
            or not {"usage", "required_actions", "metadata", "error"} <= data.keys()
            or not _count(data.get("created_at")) or not _count(data.get("last_active_at"))
            or data.get("error") is not None and not isinstance(data["error"], str)):
        _fail("MALFORMED_SESSION")
    identifier = _identifier(data.get("id"))
    if expected_id is not None and identifier != expected_id:
        _fail("SESSION_ID_MISMATCH")
    agent, environment = data.get("agent"), data.get("environment")
    if (not isinstance(agent, dict) or not isinstance(environment, dict)
            or environment.get("type") not in ("none", "openai_hosted", "self_hosted")):
        _fail("MALFORMED_SESSION")
    _identifier(agent.get("id"))
    _identifier(agent.get("model"))
    if environment["type"] != "none":
        _identifier(environment.get("id"))
    if (not isinstance(data["metadata"], dict)
            or any(not isinstance(value, str) for value in data["metadata"].values())
            or not isinstance(data["required_actions"], list) or len(data["required_actions"]) > 100):
        _fail("MALFORMED_SESSION")
    for action in data["required_actions"]:
        if not isinstance(action, dict):
            _fail("MALFORMED_SESSION")
        if action.get("type") == "function_call":
            for field in ("call_id", "turn_id", "name"):
                _identifier(action.get(field))
            if "arguments" not in action:
                _fail("MALFORMED_SESSION")
        elif action.get("type") == "environment_connection":
            _identifier(action.get("environment_id"))
        else:
            _fail("MALFORMED_SESSION")
    _usage(data["usage"])
    return data


def _turn(data: dict, session_id: str) -> None:
    if (data.get("object") != "agent.session.turn" or data.get("session_id") != session_id
            or data.get("status") not in ("queued", "in_progress", "waiting", "completed", "failed", "cancelled")
            or not {"usage", "subagent_id", "started_at", "completed_at", "error"} <= data.keys()
            or not _count(data.get("created_at"))):
        _fail("MALFORMED_TURN")
    _identifier(data.get("agent_id"))
    if data["subagent_id"] is not None:
        _identifier(data["subagent_id"])
    for field in ("started_at", "completed_at"):
        if data[field] is not None and not _count(data[field]):
            _fail("MALFORMED_TURN")
    if data["error"] is not None:
        error = data["error"]
        if not isinstance(error, dict) or not isinstance(error.get("message"), str):
            _fail("MALFORMED_TURN")
        _identifier(error.get("code"))
    _usage(data["usage"])


def _item(data: dict) -> None:
    _identifier(data.get("type"))
    _identifier(data.get("turn_id"))
    if data.get("type") != "message":
        return  # Opaque tool records remain untrusted data, never executable input.
    if (data.get("role") not in ("user", "assistant")
            or "phase" not in data or data["phase"] not in (None, "commentary", "final_answer")
            or data.get("status") not in ("in_progress", "completed", "incomplete")
            or not isinstance(data.get("content"), list)):
        _fail("MALFORMED_ITEM")
    for part in data["content"]:
        if not isinstance(part, dict):
            _fail("MALFORMED_ITEM")
        kind = part.get("type")
        field = {"input_text": "text", "output_text": "text", "input_image": "image_url"}.get(kind) if isinstance(kind, str) else None
        if field is None or not isinstance(part.get(field), str):
            _fail("MALFORMED_ITEM")


def _page(data: dict) -> dict:
    rows = data.get("data")
    if (data.get("object") != "list" or not isinstance(rows, list) or len(rows) > 100
            or type(data.get("has_more")) is not bool
            or not {"first_id", "last_id"} <= data.keys()):
        _fail("MALFORMED_PAGE")
    identifiers = []
    for row in rows:
        if not isinstance(row, dict):
            _fail("MALFORMED_PAGE")
        identifier = row.get("id")
        if identifier is None and row.get("type") == "message" and row.get("role") == "user":
            identifiers.append(None)
        else:
            identifiers.append(_identifier(identifier))
    recorded = [value for value in identifiers if value is not None]
    if (len(set(recorded)) != len(recorded)
            or data["first_id"] != (identifiers[0] if identifiers else None)
            or data["last_id"] != (identifiers[-1] if identifiers else None)
            or data["has_more"] and data["last_id"] is None):
        _fail("MALFORMED_PAGE")
    return data


def _native(method: str, url: str, headers: Mapping[str, str], body: bytes | None, timeout: int):
    target = urlsplit(url)
    if (target.scheme != "https" or target.netloc != "api.openai.com" or target.fragment
            or not (target.path == "/v1/agents/sessions" or target.path.startswith("/v1/agents/sessions/"))):
        _fail("INVALID_ENDPOINT", False)
    connection = http.client.HTTPSConnection("api.openai.com", timeout=timeout)
    deadline = time.monotonic() + timeout
    try:
        connection.request(method, target.path + ("?" + target.query if target.query else ""), body, dict(headers))
        response = connection.getresponse()
        pairs = response.getheaders()
        framing_headers = {"content-type", "content-length", "content-encoding", "transfer-encoding"}
        for name in framing_headers:
            if sum(key.lower() == name for key, _ in pairs) > 1:
                _fail("MALFORMED_TRANSPORT")
        # Uninterpreted list-valued headers (for example CORS expose headers)
        # can legally repeat. Only decoding/framing fields cross this boundary.
        response_headers = {key: value for key, value in pairs if key.lower() in framing_headers}
        if response.status not in (200, 201, 202, 204):
            return response.status, response_headers, b""
        chunks, size = [], 0
        while size <= MAX_BYTES:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                _fail("TIMEOUT")
            if connection.sock is not None:
                connection.sock.settimeout(remaining)
            chunk = response.read1(min(65_536, MAX_BYTES + 1 - size))
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
        if size > MAX_BYTES:
            _fail("RESPONSE_TOO_LARGE")
        return response.status, response_headers, b"".join(chunks)
    finally:
        connection.close()


def _isolated(method: str, url: str, headers: Mapping[str, str], body: bytes | None, timeout: int):
    payload = {"method": method, "url": url, "headers": dict(headers), "timeout": timeout,
               "body": base64.b64encode(body).decode() if body is not None else None}
    root = Path(__file__).resolve().parents[2]
    try:
        process = subprocess.run([sys.executable, "-B", "-m", "researcher.service.openai_agents"],
                                 input=json.dumps(payload).encode(), capture_output=True, cwd=root,
                                 env={"PATH": os.defpath, "PYTHONPATH": str(root), "PYTHONUTF8": "1"},
                                 timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        _fail("WALL_TIMEOUT")
    except OSError:
        _fail("WORKER_START_FAILED", False)
    if process.returncode or process.stderr or len(process.stdout) > 2 * MAX_BYTES:
        _fail("WORKER_FAILED")
    try:
        value = _parse_json(process.stdout)
        if set(value) == {"error"}:
            code = value["error"]
            _fail(code if isinstance(code, str) and re.fullmatch(r"[A-Z_]{1,64}", code) else "WORKER_FAILED")
        return value["status"], value["headers"], base64.b64decode(value["body"], validate=True)
    except (ValueError, KeyError, TypeError):
        _fail("WORKER_FAILED")


class AgentsClient:
    """Explicit credential, fixed origin and one request per public method."""

    def __init__(self, credential: str, transport: Transport | None = None, timeout_seconds: int = 30):
        if (not isinstance(credential, str) or not credential or len(credential) > 4096
                or any(ord(char) < 33 or ord(char) > 126 for char in credential)):
            _fail("INVALID_CREDENTIAL", False)
        if type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 300:
            _fail("INVALID_TIMEOUT", False)
        self._credential, self._transport, self._timeout = credential, transport or _isolated, timeout_seconds

    def __repr__(self) -> str:
        return f"AgentsClient(timeout_seconds={self._timeout})"

    @instrument("managed.http")
    def _request(self, method: str, path: str, payload: dict | None = None, operation_key: str | None = None) -> dict:
        annotate(provider="openai", transport="https", **{"http.method": method})
        if self._credential in path or self._credential in unquote(path):
            _fail("CREDENTIAL_REFLECTION", False)
        ambiguous = method != "GET"
        headers = {"Authorization": f"Bearer {self._credential}", "OpenAI-Beta": "agents=v1",
                   "Accept": "application/json", "Content-Type": "application/json"}
        if operation_key is not None:
            if not isinstance(operation_key, str) or not re.fullmatch(r"[A-Za-z0-9._:-]{1,256}", operation_key):
                _fail("INVALID_OPERATION_KEY", False)
            if self._credential in operation_key:
                _fail("CREDENTIAL_REFLECTION", False)
            headers["Idempotency-Key"] = operation_key
        body = None
        if payload is not None:
            _json_tree(payload, self._credential, ambiguous=False)
            try:
                body = json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()
            except (UnicodeError, ValueError, OverflowError, RecursionError):
                _fail("MALFORMED_JSON", False)
            if len(body) > MAX_BYTES:
                _fail("REQUEST_TOO_LARGE", False)
        try:
            annotate(input_bytes=0 if body is None else len(body))
            status, response_headers, raw = self._transport(method, BASE_URL + path, headers, body, self._timeout)
            if type(status) is not int or not isinstance(response_headers, Mapping) or not isinstance(raw, bytes):
                _fail("MALFORMED_TRANSPORT")
            if len(raw) > MAX_BYTES:
                _fail("RESPONSE_TOO_LARGE")
            annotate(output_bytes=len(raw), **{"http.status_code": status})
            if any(not isinstance(key, str) or not isinstance(value, str) for key, value in response_headers.items()):
                _fail("MALFORMED_TRANSPORT")
            _json_tree(dict(response_headers), self._credential, ambiguous=ambiguous)
            normalized = {key.lower(): value for key, value in response_headers.items()}
            if len(normalized) != len(response_headers):
                _fail("MALFORMED_TRANSPORT")
            if 300 <= status <= 399:
                _fail("REDIRECT_REFUSED")
            if status in (401, 403):
                _fail("AUTH_ERROR")
            if status == 429:
                _fail("RATE_OR_SPEND_LIMIT")
            success_statuses = (200, 202, 204) if operation_key is not None else (200,)
            if method == "POST" and path == "" and operation_key is None:
                # Session creation returns 201. Do not broaden read/cancel
                # success codes or lose a created session's recovery identity.
                success_statuses = (200, 201)
            if status not in success_statuses:
                _fail("HTTP_ERROR")
            if normalized.get("content-encoding", "identity").lower() != "identity":
                _fail("UNEXPECTED_ENCODING")
            if "content-length" in normalized:
                length = normalized["content-length"]
                if not re.fullmatch(r"[0-9]{1,10}", length) or int(length) != len(raw):
                    _fail("TRUNCATED_RESPONSE")
            if "transfer-encoding" in normalized and ("content-length" in normalized or normalized["transfer-encoding"].lower() != "chunked"):
                _fail("MALFORMED_TRANSPORT")
            if status == 204 and raw:
                _fail("MALFORMED_TRANSPORT")
            if operation_key is not None and not raw:
                return {}  # Acknowledgement is not proof the turn has cancelled.
            if normalized.get("content-type", "").split(";", 1)[0].strip().lower() != "application/json":
                _fail("UNEXPECTED_CONTENT_TYPE")
            data = _decode(raw, self._credential, ambiguous=ambiguous)
            if data.get("error") is not None and data.get("object") != "agent.session":
                _fail("API_RESPONSE_ERROR")
            return data
        except AgentsError as error:
            _fail(error.code, ambiguous and error.ambiguous)
        except TimeoutError:
            _fail("TIMEOUT", ambiguous)
        except Exception:
            _fail("TRANSPORT_ERROR", ambiguous)

    def create(self, payload: dict) -> dict:
        allowed = {"environment", "agent", "agent_id", "input", "metadata", "stream", "vault_ids"}
        if not isinstance(payload, dict) or set(payload) - allowed or payload.get("stream", False) is not False:
            _fail("INVALID_CREATE_REQUEST", False)
        agent, environment = payload.get("agent", {}), payload.get("environment")
        if (not isinstance(agent, dict) or not isinstance(environment, dict)
                or environment.get("type") not in ("none", "openai_hosted", "self_hosted")
                or set(agent) - {"instructions", "model", "multi_agent", "reasoning", "service_tier", "text", "tools"}):
            _fail("INVALID_CREATE_REQUEST", False)
        if "input" in payload and not isinstance(payload["input"], (str, list)):
            _fail("INVALID_CREATE_REQUEST", False)
        if "agent_id" in payload:
            _identifier(payload["agent_id"], ambiguous=False)
        if "agent_id" not in payload or "model" in agent:
            model = _identifier(agent.get("model"), ambiguous=False)
            if set(re.split(r"[._-]", model.lower())) & {"latest", "auto", "default"}:
                _fail("INVALID_MODEL", False)
        if environment["type"] == "none" and not payload.get("input"):
            _fail("INITIAL_INPUT_REQUIRED", False)
        data = self._request("POST", "", payload)
        try:
            return _session(data)
        except AgentsError as error:
            # A known remote identity is needed for reconciliation even when a
            # different session field is malformed. This is after strict JSON
            # parsing and complete credential-reflection rejection.
            session_id = None
            if data.get("object") == "agent.session":
                try:
                    session_id = _identifier(data.get("id"))
                except AgentsError:
                    pass
            raise AgentsError(error.code, error.ambiguous, session_id=session_id) from None

    def retrieve(self, session_id: str) -> dict:
        session_id = _identifier(session_id, ambiguous=False)
        try:
            return _session(self._request("GET", "/" + quote(session_id, safe="")), session_id)
        except AgentsError as error:
            _fail(error.code, False)

    def _list(self, session_id: str, resource: str, after: str | None) -> dict:
        session_id = _identifier(session_id, ambiguous=False)
        query = {"limit": 100, "order": "asc"}
        if after is not None:
            query["after"] = _identifier(after, ambiguous=False)
        try:
            page = _page(self._request("GET", f"/{quote(session_id, safe='')}/{resource}?{urlencode(query)}"))
            if after is not None and page["has_more"] and page["last_id"] == after:
                _fail("PAGINATION_NOT_ADVANCING")
            for row in page["data"]:
                _turn(row, session_id) if resource == "turns" else _item(row)
            return page
        except AgentsError as error:
            _fail(error.code, False)

    def turns(self, session_id: str, after: str | None = None) -> dict:
        return self._list(session_id, "turns", after)

    def traces(self, session_id: str, after: str | None = None) -> dict:
        """Read one OTLP snapshot page, never a live stream or usage invoice."""
        session_id = _identifier(session_id, ambiguous=False)
        query = {"limit": 20, "order": "asc"}
        if after is not None:
            query["after"] = _identifier(after, ambiguous=False)
        try:
            page = _page(self._request("GET", f"/{quote(session_id, safe='')}/traces?{urlencode(query)}"))
            if len(page["data"]) > 20 or after is not None and page["last_id"] == after:
                _fail("PAGINATION_NOT_ADVANCING")
            return page
        except AgentsError as error:
            _fail(error.code, False)

    def items(self, session_id: str, turn_id: str, after: str | None = None) -> dict:
        """Return the full page. The caller filters turn_id after pagination.

        The REST reference does not document a turn_id query parameter. Validate
        caller intent here without inventing one or breaking cursor invariants.
        """
        _identifier(turn_id, ambiguous=False)
        return self._list(session_id, "items", after)

    def cancel(self, session_id: str, operation_key: str) -> None:
        session_id = _identifier(session_id, ambiguous=False)
        if not isinstance(operation_key, str):
            _fail("INVALID_OPERATION_KEY", False)
        data = self._request("POST", f"/{quote(session_id, safe='')}/events",
                             {"events": [{"type": "agent.session.input.cancel"}]}, operation_key)
        if data:
            _fail("UNEXPECTED_CANCEL_RESPONSE")


def _worker() -> None:
    try:
        raw = sys.stdin.buffer.read(2 * MAX_BYTES + 1)
        if len(raw) > 2 * MAX_BYTES:
            _fail("REQUEST_TOO_LARGE", False)
        value = _parse_json(raw)
        body = base64.b64decode(value["body"], validate=True) if value["body"] is not None else None
        status, headers, raw = _native(value["method"], value["url"], value["headers"], body, value["timeout"])
        result = {"status": status, "headers": headers, "body": base64.b64encode(raw).decode()}
    except AgentsError as error:
        result = {"error": error.code}
    except TimeoutError:
        result = {"error": "TIMEOUT"}
    except Exception:
        result = {"error": "TRANSPORT_ERROR"}
    sys.stdout.write(json.dumps(result, ensure_ascii=True))


if __name__ == "__main__":
    _worker()
