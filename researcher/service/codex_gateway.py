"""Single-request SDK gateway sharing the existing Campaign Store authority.

This is a tool-free provider boundary, not an agent loop. The pinned SDK owns
the thread/turn. Every admitted HTTP request reserves the original budget before
dispatch. Complete, bounded SSE is validated and durably acknowledged BEFORE
any model output reaches the SDK. No tool call, secret or ambient workspace
metadata is forwarded. A lost worker result never authorizes a replacement turn.
"""
from __future__ import annotations

from contextlib import contextmanager
import http.client
from http.server import BaseHTTPRequestHandler, HTTPServer
import hmac
import json
import math
import os
from pathlib import Path
import re
import secrets
import ssl
import subprocess
import sys
import threading
import time

from researcher.scripts.schema_contract import canonicalize, parse_json_strict
from .contracts import ServiceError, digest
from .codex_worker import BASE_INSTRUCTIONS

MAX_REQUEST = 262144
MAX_RESPONSE = 1048576
MAX_EVENT_NODES = 65536
MAX_EVENT_DEPTH = 64
POLICY = "codex-tool-free-buffered-v1"
ENDPOINT = "https://api.openai.com/v1/responses"
# Child failures carry only an exit code, never provider bodies, headers, or
# exception text. These are diagnostics, not evidence that billing did not occur.
FORWARD_EXIT_CODES = {
    20: "HTTP_AUTH_REJECTED", 21: "HTTP_RATE_LIMITED", 22: "HTTP_CLIENT_ERROR",
    23: "HTTP_SERVER_ERROR", 24: "HTTP_REDIRECT", 25: "HTTP_STATUS_UNEXPECTED",
    26: "TRANSPORT_TIMEOUT", 27: "TRANSPORT_TLS_ERROR", 28: "TRANSPORT_NETWORK_ERROR",
    29: "RESPONSE_FRAMING_INVALID", 30: "RESPONSE_TYPE_INVALID", 31: "RESPONSE_LIMIT",
    32: "FORWARD_INPUT_INVALID", 33: "FORWARD_WORKER_ERROR",
}
TOKEN_DETAILS = {
    "cached_input_tokens": ("input_tokens_details", "cached_tokens", "inputTokens", "cachedInputTokens"),
    "cache_write_input_tokens": ("input_tokens_details", "cache_write_tokens", "inputTokens", "cacheWriteInputTokens"),
    "reasoning_output_tokens": ("output_tokens_details", "reasoning_tokens", "outputTokens", "reasoningOutputTokens"),
}


def _error(code):
    raise ServiceError("CODEX_GATEWAY_" + code)


def validate_token_details(details, inputs, outputs):
    """Closed receipt shape. None means unreported, not a measured zero."""
    if type(details) is not dict or set(details) != set(TOKEN_DETAILS):
        _error("USAGE_DETAILS_CONTRACT")
    for key, value in details.items():
        limit = outputs if key == "reasoning_output_tokens" else inputs
        if value is not None and (type(value) is not int or not 0 <= value <= limit):
            _error("USAGE_DETAILS_CONTRACT")
    return details


def _usage_details(usage, inputs, outputs):
    details = {}
    for key, (group, field, _total, _sdk) in TOKEN_DETAILS.items():
        values = usage.get(group)
        if values is not None and type(values) is not dict:
            _error("USAGE_DETAILS_CONTRACT")
        details[key] = None if values is None else values.get(field)
    return validate_token_details(details, inputs, outputs)


def _external_event(record):
    """Parse external JSON, not the integer-only durable-record profile.

    Responses frames legitimately contain finite temperature/top_p/logprob
    metadata. It is validated as JSON but never copied to a durable receipt.
    Usage remains separately validated as exact bounded integers. Rejecting
    duplicate keys and nonfinite numbers is still mandatory at this boundary.
    """
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                _error("SSE_JSON_INVALID")
            value[key] = item
        return value

    def finite(number):
        value = float(number)
        if not math.isfinite(value):
            _error("SSE_JSON_INVALID")
        return value

    def integer(number):
        if number == "-0":
            _error("SSE_JSON_INVALID")
        return int(number)

    try:
        value = json.loads(record, object_pairs_hook=unique, parse_float=finite,
                           parse_int=integer,
                           parse_constant=lambda _: _error("SSE_JSON_INVALID"))
        pending, count = [(value, 0)], 0
        while pending:
            item, depth = pending.pop()
            count += 1
            if count > MAX_EVENT_NODES or depth > MAX_EVENT_DEPTH:
                _error("SSE_JSON_LIMIT")
            if type(item) is dict:
                pending.extend((child, depth + 1) for child in item.values())
                pending.extend((key, depth + 1) for key in item)
            elif type(item) is list:
                pending.extend((child, depth + 1) for child in item)
            elif isinstance(item, str):
                item.encode("utf-8")  # Refuse lone JSON-escaped surrogates too.
        return value
    except ServiceError:
        raise
    except (ValueError, OverflowError, RecursionError, UnicodeError):
        _error("SSE_JSON_INVALID")


def project_request(raw, task):
    """Allow only the measured first-turn SDK envelope, not arbitrary proxying.

    Remove SDK-generated host paths and unstable telemetry/cache identities.
    Preserve its base instructions and the exact immutable user task. We do not
    accept conversation continuations, references, attachments or remote tools.
    """
    if not isinstance(raw, bytes) or not 1 <= len(raw) <= MAX_REQUEST:
        _error("REQUEST_LIMIT")
    try:
        value = parse_json_strict(raw.decode("utf-8"))
    except (ValueError, TypeError, UnicodeError, RecursionError):
        _error("INVALID_JSON")
    required = {"model", "input", "tool_choice", "parallel_tool_calls",
                "reasoning", "store", "stream", "include", "prompt_cache_key", "client_metadata"}
    if (type(value) is not dict or not required <= value.keys() or value.keys() - required - {"text", "instructions", "tools"}
            or value["model"] != task["model"] or value["store"] is not False or value["stream"] is not True
            or value["reasoning"] not in ({"effort": task["reasoning_effort"]},
                {"effort": task["reasoning_effort"], "context": "all_turns"})
            or value["tool_choice"] != "auto" or type(value["parallel_tool_calls"]) is not bool
            or value["include"] != ["reasoning.encrypted_content"]
            or ("instructions" in value and value["instructions"] != BASE_INSTRUCTIONS)):
        _error("REQUEST_CONTRACT")
    items = value["input"]
    if type(items) is not list or not 3 <= len(items) <= 12:
        _error("INPUT_CONTRACT")
    users, bases, additional = [], int("instructions" in value), 0
    for item in items:
        if type(item) is dict and item.get("type") == "additional_tools":
            additional += 1
            if (set(item) != {"type", "id", "role", "tools"} or item["role"] != "developer"
                    or type(item["tools"]) is not list or additional > 1):
                _error("TOOLS_CHANGED")
            continue  # Never forward code-mode tool namespaces to the provider.
        if (type(item) is not dict or set(item) != {"type", "id", "role", "content"}
                or item["type"] != "message" or item["role"] not in {"developer", "user"}
                or not isinstance(item["id"], str) or len(item["id"]) > 128
                or type(item["content"]) is not list or not 1 <= len(item["content"]) <= 4
                or any(type(part) is not dict or set(part) != {"type", "text"}
                    or part["type"] != "input_text" or not isinstance(part["text"], str) for part in item["content"])):
            _error("INPUT_CONTRACT")
        if item["role"] == "user":
            users.append(item)
        elif item["content"] == [{"type": "input_text", "text": BASE_INSTRUCTIONS}]:
            bases += 1
    if (bases != 1 or len(users) != 2 or any(len(item["content"]) != 1 for item in users)
            or items[-1] != users[-1] or users[-1]["content"][0]["text"] != task["prompt"]):
        _error("TASK_CHANGED")
    if not users[0]["content"][0]["text"].startswith("<environment_context>"):
        _error("AMBIENT_INPUT")
    tools = value.get("tools")
    if (tools is not None and (type(tools) is not list or len(tools) != 3
            or any(type(tool) is not dict for tool in tools)
            or {(tool.get("type"), tool.get("name")) for tool in tools} != {
                ("function", "request_user_input"), ("custom", "apply_patch"), ("function", "view_image")})):
        _error("TOOLS_CHANGED")
    text = value.get("text", {})
    if type(text) is not dict or text.keys() - {"verbosity", "format"}:
        _error("FORMAT_CHANGED")
    expected_format = None
    if "output_schema" in task:
        expected_format = {"type": "json_schema", "strict": True, "schema": task["output_schema"],
                           "name": "codex_output_schema"}
    if text.get("format") != expected_format or text.get("verbosity", "low") != "low":
        _error("FORMAT_CHANGED")
    body = {"model": value["model"], "instructions": BASE_INSTRUCTIONS,
            "input": [{"role": "user", "content": users[-1]["content"]}],
            "reasoning": {"effort": task["reasoning_effort"]}, "tools": [], "tool_choice": "none",
            "parallel_tool_calls": False, "store": False, "stream": True,
            "background": False, "service_tier": "default", "truncation": "disabled",
            "max_output_tokens": task["max_output_tokens"]}
    if text:
        body["text"] = text
    encoded = canonicalize(body)
    if len(encoded) > 131072:
        _error("CONTEXT_LIMIT")
    return encoded


def validate_stream(raw, task, *, input_ceiling):
    """Do not expose partial model output, tools or unverified terminal events."""
    from .providers import _openai, _valid_identifier
    if not isinstance(raw, bytes) or not 1 <= len(raw) <= MAX_RESPONSE:
        _error("RESPONSE_LIMIT")
    try:
        normalized = raw.decode("utf-8").replace("\r\n", "\n")
        if not normalized.endswith("\n\n"):
            _error("SSE_CONTRACT")
        lines = normalized.split("\n")
        records, data, completed = [], [], None
        for line in lines:
            if line == "":
                if data:
                    records.append("\n".join(data))
                    data = []
            elif line.startswith("data: "):
                data.append(line[6:])
            elif not (line.startswith("event: ") or line.startswith(":")):
                _error("SSE_CONTRACT")
        if data or len(records) > 4096:
            _error("SSE_CONTRACT")
        for record in records:
            if record == "[DONE]":
                if completed is None:
                    _error("INCOMPLETE")
                continue
            event = _external_event(record)
            if type(event) is not dict or not isinstance(event.get("type"), str) or completed is not None:
                _error("SSE_CONTRACT")
            kind = event["type"]
            if kind in {"error", "response.failed", "response.incomplete"}:
                _error("PROVIDER_FAILED")
            if "item" in event and (type(event["item"]) is not dict or event["item"].get("type") not in {"message", "reasoning"}):
                _error("TOOL_OUTPUT_FORBIDDEN")
            if kind == "response.completed":
                completed = event.get("response")
        if type(completed) is not dict:
            _error("INCOMPLETE")
        text, inputs, outputs = _openai(completed)
        if (completed.get("model") != task["model"] or completed.get("service_tier") != "default"
                or not _valid_identifier(completed.get("id")) or not text.strip()
                or inputs > input_ceiling or outputs > task["max_output_tokens"]
                or len(text.encode("utf-8")) > 131072):
            _error("RECEIPT_CONTRACT")
        # One final message is the entire tool-free contract. No commentary or
        # hidden reasoning is persisted/replayed as an answer.
        messages = [item for item in completed["output"] if item.get("type") == "message"]
        if len(messages) != 1 or messages[0].get("phase") not in (None, "final_answer"):
            _error("ANSWER_CONTRACT")
        return {"text": text, "input_tokens": inputs, "output_tokens": outputs,
                "model": completed["model"], "request_id": completed["id"], "service_tier": "default",
                "token_details": _usage_details(completed["usage"], inputs, outputs)}
    except ServiceError:
        raise
    except Exception:
        _error("INVALID_RESPONSE")


def sdk_stream(response):
    """Minimal SDK-compatible stream made ONLY from the committed safe receipt."""
    item = {"type": "message", "id": "msg_gateway", "role": "assistant", "status": "completed",
            "phase": "final_answer", "content": [{"type": "output_text", "text": response["text"], "annotations": []}]}
    terminal = {"id": response["request_id"], "object": "response", "model": response["model"],
        "service_tier": "default", "status": "completed", "output": [item],
        "usage": {"input_tokens": response["input_tokens"], "output_tokens": response["output_tokens"],
            "total_tokens": response["input_tokens"] + response["output_tokens"]}}
    # The SDK may normalize absent counters to zero. Only the receipt retains
    # the provider's missingness, so downstream metrics must use that authority.
    details = validate_token_details(response["token_details"], response["input_tokens"], response["output_tokens"])
    for key, (group, field, _total, _sdk) in TOKEN_DETAILS.items():
        if details[key] is not None:
            terminal["usage"].setdefault(group, {})[field] = details[key]
    events = [{"type": "response.created", "response": {"id": response["request_id"], "status": "in_progress", "output": []}},
        {"type": "response.output_item.added", "output_index": 0, "item": item},
        {"type": "response.output_item.done", "output_index": 0, "item": item},
        {"type": "response.completed", "response": terminal}]
    return b"".join(b"event: " + event["type"].encode() + b"\ndata: " + canonicalize(event) + b"\n\n" for event in events)


def forward(body, *, credential, timeout_seconds=120):
    """Fixed-endpoint one-POST subprocess; no redirects/proxies/SDK retries."""
    try:
        packet = json.dumps({"body": body.decode("utf-8"), "credential": credential,
                             "timeout": timeout_seconds}).encode()
        _forward_packet(packet)
    except (ValueError, TypeError, AttributeError, UnicodeError):
        _error("FORWARD_INPUT_INVALID")
    try:
        result = subprocess.run([sys.executable, "-B", "-m", "researcher.service.codex_gateway", "--forward"],
            cwd=Path(__file__).resolve().parents[2], input=packet, capture_output=True,
            env={"PATH": os.defpath, "PYTHONUTF8": "1"}, timeout=timeout_seconds, check=False)
    except subprocess.TimeoutExpired:
        _error("WALL_TIMEOUT")
    except OSError:
        _error("WORKER_START_FAILED")
    if result.returncode:
        # Do not decode arbitrary output from a failed or replaced worker.
        if not result.stdout and not result.stderr and result.returncode in FORWARD_EXIT_CODES:
            _error(FORWARD_EXIT_CODES[result.returncode])
        _error("WORKER_FAILED")
    if result.stderr or not 1 <= len(result.stdout) <= MAX_RESPONSE:
        _error("WORKER_FAILED")
    return result.stdout


def _forward_packet(raw):
    if not isinstance(raw, bytes) or not 1 <= len(raw) <= MAX_REQUEST + 8192:
        raise ValueError()
    packet = parse_json_strict(raw.decode("utf-8"))
    if (type(packet) is not dict or set(packet) != {"body", "credential", "timeout"}
            or type(packet["body"]) is not str or not 1 <= len(packet["body"].encode("utf-8")) <= MAX_REQUEST
            or type(packet["credential"]) is not str or not 1 <= len(packet["credential"]) <= 4096
            or any(ord(char) < 33 or ord(char) > 126 for char in packet["credential"])
            or type(packet["timeout"]) is not int or not 1 <= packet["timeout"] <= 120):
        raise ValueError()
    return packet


def _forward_child():
    from .providers import ProviderError, _https_post
    codes = {name: code for code, name in FORWARD_EXIT_CODES.items()}
    try:
        packet = _forward_packet(sys.stdin.buffer.read(MAX_REQUEST + 8193))
    except Exception:
        return codes["FORWARD_INPUT_INVALID"]
    try:
        status, headers, raw = _https_post(ENDPOINT, {"Authorization": "Bearer " + packet["credential"],
            "Content-Type": "application/json", "Accept": "text/event-stream"}, packet["body"].encode(), packet["timeout"])
        if type(status) is not int or not 100 <= status <= 599:
            return codes["FORWARD_WORKER_ERROR"]
        if status != 200:
            if status in (401, 403):
                return codes["HTTP_AUTH_REJECTED"]
            if status == 429:
                return codes["HTTP_RATE_LIMITED"]
            if 400 <= status <= 499:
                return codes["HTTP_CLIENT_ERROR"]
            if 500 <= status <= 599:
                return codes["HTTP_SERVER_ERROR"]
            if 300 <= status <= 399:
                return codes["HTTP_REDIRECT"]
            return codes["HTTP_STATUS_UNEXPECTED"]
        lower = {key.lower(): value for key, value in headers.items()}
        if not isinstance(raw, bytes):
            return codes["FORWARD_WORKER_ERROR"]
        if not 1 <= len(raw) <= MAX_RESPONSE:
            return codes["RESPONSE_LIMIT"]
        if lower.get("content-type", "").split(";")[0].strip() != "text/event-stream":
            return codes["RESPONSE_TYPE_INVALID"]
        if lower.get("content-encoding", "identity") != "identity":
            return codes["RESPONSE_FRAMING_INVALID"]
        if "content-length" in lower and "transfer-encoding" in lower:
            return codes["RESPONSE_FRAMING_INVALID"]
        if lower.get("transfer-encoding", "chunked") != "chunked":
            return codes["RESPONSE_FRAMING_INVALID"]
        if "content-length" in lower and (not re.fullmatch(r"[0-9]{1,7}", lower["content-length"])
                                            or int(lower["content-length"]) != len(raw)):
            return codes["RESPONSE_FRAMING_INVALID"]
        sys.stdout.buffer.write(raw)
        return 0
    except ssl.SSLError:
        return codes["TRANSPORT_TLS_ERROR"]
    except TimeoutError:
        return codes["TRANSPORT_TIMEOUT"]
    except http.client.HTTPException:
        return codes["RESPONSE_FRAMING_INVALID"]
    except OSError:
        return codes["TRANSPORT_NETWORK_ERROR"]
    except ProviderError as error:
        name = {"TIMEOUT": "TRANSPORT_TIMEOUT", "MALFORMED_TRANSPORT": "RESPONSE_FRAMING_INVALID",
                "RESPONSE_TOO_LARGE": "RESPONSE_LIMIT"}.get(error.code, "FORWARD_WORKER_ERROR")
        return codes[name]
    except Exception:
        return codes["FORWARD_WORKER_ERROR"]


class Gateway:
    """Caller MUST hold Store.worker_lock across this gateway and the SDK turn."""
    def __init__(self, store, job, task, *, credential, transport=None, now=None):
        self.store, self.job, self.task = store, job, task
        self.credential, self.transport = credential, transport or forward
        self.now = now or (lambda: int(time.time()))
        self.token = secrets.token_urlsafe(32)
        self.receipt = None
        self.error = None
        self._used = False
        self._mutex = threading.Lock()

    def exchange(self, raw):
        from .openai_campaign import PRICING, _cost, _reflected
        with self._mutex:
            if self._used:
                self.error = "CODEX_GATEWAY_SECOND_REQUEST_FORBIDDEN"
                _error("SECOND_REQUEST_FORBIDDEN")
            self._used = True
        try:
            if self.now() >= PRICING["valid_before_epoch"]:
                raise ServiceError("PRICING_REVIEW_REQUIRED")
            body = project_request(raw, self.task)
            if _reflected(parse_json_strict(body.decode()), self.credential) or self.token in body.decode():
                _error("CREDENTIAL_IN_CONTEXT")
            inputs = {"schema": "codex-gateway-request/v1", "task_digest": digest(self.task),
                      "wire_digest": digest(parse_json_strict(body.decode())), "policy": POLICY}
            ceiling = len(body) + 4096
            reserve = _cost(ceiling, self.task["max_output_tokens"])
            prior = self.store.reserve(self.job, "sdk-response", inputs, model_calls=1, micros=reserve, now=self.now())
            if prior is not None:
                _error("REQUEST_ALREADY_ADMITTED")
            started = time.monotonic()
            raw_response = self.transport(body, credential=self.credential, timeout_seconds=120)
            # Scan the entire stream BEFORE any text is persisted or released.
            if not isinstance(raw_response, bytes) or len(raw_response) > MAX_RESPONSE:
                _error("RESPONSE_LIMIT")
            if _reflected(raw_response.decode("utf-8"), self.credential) or self.token in raw_response.decode("utf-8"):
                _error("CREDENTIAL_REFLECTION")
            response = validate_stream(raw_response, self.task, input_ceiling=ceiling)
            if _reflected(response, self.credential) or _reflected(response, self.token):
                _error("CREDENTIAL_REFLECTION")
            receipt = {"schema": "codex-gateway-receipt/v2", "backend": "codex_sdk", "policy": POLICY,
                "response": response, "task_digest": digest(self.task), "wire_digest": inputs["wire_digest"],
                "input_token_ceiling": ceiling,
                "usage": {"input_tokens": response["input_tokens"], "output_tokens": response["output_tokens"],
                          "estimated_upper_cost_microusd": _cost(response["input_tokens"], response["output_tokens"])},
                "latency_ms": int((time.monotonic() - started) * 1000), "reserved_microusd": reserve}
            self.store.complete_effect(self.job, "sdk-response", receipt)
            self.receipt = receipt
            return sdk_stream(response)
        except Exception as exc:
            code = getattr(exc, "code", "CODEX_GATEWAY_OUTCOME_UNKNOWN")
            if not isinstance(code, str) or not re.fullmatch(r"[A-Z0-9_]{1,100}", code):
                code = "CODEX_GATEWAY_OUTCOME_UNKNOWN"
            self.error = code
            self.store.fail_effect(self.job, "sdk-response", code, ambiguous=True)
            raise ServiceError(code) from None

    @contextmanager
    def serving(self):
        owner = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass

            def setup(self):
                super().setup()
                self.connection.settimeout(5)

            def do_POST(self):
                try:
                    if (self.path != "/v1/responses"
                            or len(self.headers.get_all("Authorization", [])) != 1
                            or not hmac.compare_digest(self.headers["Authorization"], "Bearer " + owner.token)
                            or len(self.headers.get_all("Content-Length", [])) != 1
                            or self.headers.get_all("Transfer-Encoding")
                            or self.headers.get("Content-Encoding", "identity") != "identity"
                            or self.headers.get("Content-Type") != "application/json"):
                        raise ValueError()
                    length = self.headers["Content-Length"]
                    if not re.fullmatch(r"[0-9]{1,7}", length) or not 1 <= int(length) <= MAX_REQUEST:
                        raise ValueError()
                    raw = self.rfile.read(int(length))
                    if len(raw) != int(length):
                        raise ValueError()
                    body = owner.exchange(raw)
                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream")
                except Exception:
                    body = b'{"error":{"message":"SDK gateway refused request"}}'
                    self.send_response(409)
                    self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Connection", "close")
                self.end_headers()
                try:
                    self.wfile.write(body)
                except OSError:
                    pass  # Receipt remains committed; lost local ACK is not a resend permit.

        server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        thread.start()
        try:
            yield f"http://127.0.0.1:{server.server_port}/v1", self.token
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    raise SystemExit(_forward_child() if sys.argv[1:] == ["--forward"] else 2)
