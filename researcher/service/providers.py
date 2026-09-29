"""Bounded, tool-free native model calls. The caller owns budgets and effect state.

No credentials are discovered, persisted or included in error messages. Each call
performs at most one POST; even a failed response may have incurred provider cost.
Transport injection is for trusted tests, not an operator-configurable endpoint.
"""

from __future__ import annotations

from dataclasses import dataclass
import http.client
import json
import re
import time
from typing import Callable, Mapping
from urllib.parse import urlsplit


MAX_RESPONSE_BYTES = 1024 * 1024
MAX_REQUEST_BYTES = 1024 * 1024
Transport = Callable[[str, Mapping[str, str], bytes, int], tuple[int, Mapping[str, str], bytes]]


@dataclass(frozen=True)
class ModelRequest:
    provider: str
    model: str
    system: str
    prompt: str
    max_output_tokens: int
    timeout_seconds: int = 60
    reasoning_effort: str | None = None


@dataclass(frozen=True)
class ModelResult:
    text: str
    input_tokens: int
    output_tokens: int
    model: str
    request_id: str | None
    service_tier: str | None = None


class ProviderError(Exception):
    def __init__(self, code: str, safe_message: str, ambiguous: bool = True):
        self.code = code
        self.safe_message = safe_message
        self.ambiguous = ambiguous
        super().__init__(safe_message)


def _fail(code: str, ambiguous: bool = True) -> None:
    # Never interpolate remote bodies, credentials or transport exceptions.
    raise ProviderError(code, f"Model provider request failed: {code}.", ambiguous) from None


def _valid_identifier(value: object) -> bool:
    return (isinstance(value, str) and len(value) <= 200
            and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", value) is not None)


def _validate(request: ModelRequest, credential: str) -> None:
    if (not isinstance(request, ModelRequest) or not isinstance(request.provider, str)
            or request.provider not in {"openai", "anthropic", "gemini"}):
        _fail("INVALID_PROVIDER", False)
    if (not _valid_identifier(request.model)
            or set(re.split(r"[._-]", request.model.lower())) & {"latest", "auto", "default"}):
        _fail("INVALID_MODEL", False)
    if (not isinstance(credential, str) or not credential or len(credential) > 4096
            or any(ord(char) < 33 or ord(char) > 126 for char in credential)):
        _fail("INVALID_CREDENTIAL", False)
    if (type(request.max_output_tokens) is not int or not 1 <= request.max_output_tokens <= 131072
            or type(request.timeout_seconds) is not int or not 1 <= request.timeout_seconds <= 300):
        _fail("INVALID_LIMIT", False)
    if not isinstance(request.system, str) or not isinstance(request.prompt, str) or not request.prompt.strip():
        _fail("INVALID_PROMPT", False)
    if request.reasoning_effort is not None and (request.provider != "openai"
            or request.reasoning_effort not in {"none", "low", "medium", "high"}):
        _fail("INVALID_REASONING_EFFORT", False)


def _encode(request: ModelRequest, credential: str) -> tuple[str, dict[str, str], bytes]:
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if request.provider == "openai":
        url = "https://api.openai.com/v1/responses"
        headers["Authorization"] = f"Bearer {credential}"
        payload = {"model": request.model, "instructions": request.system,
                   "input": request.prompt, "max_output_tokens": request.max_output_tokens,
                   "store": False, "stream": False, "background": False,
                   "service_tier": "default", "tools": [], "truncation": "disabled"}
        if request.reasoning_effort is not None:
            payload["reasoning"] = {"effort": request.reasoning_effort}
    elif request.provider == "anthropic":
        url = "https://api.anthropic.com/v1/messages"
        headers.update({"x-api-key": credential, "anthropic-version": "2023-06-01"})
        payload = {"model": request.model, "system": request.system,
                   "messages": [{"role": "user", "content": request.prompt}],
                   "max_tokens": request.max_output_tokens, "stream": False}
    else:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{request.model}:generateContent"
        headers["x-goog-api-key"] = credential
        payload = {"systemInstruction": {"parts": [{"text": request.system}]},
                   "contents": [{"role": "user", "parts": [{"text": request.prompt}]}],
                   "generationConfig": {"candidateCount": 1, "maxOutputTokens": request.max_output_tokens}}
    try:
        body = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (UnicodeError, ValueError):
        _fail("INVALID_PROMPT", False)
    if len(body) > MAX_REQUEST_BYTES:
        _fail("REQUEST_TOO_LARGE", False)
    return url, headers, body


def _https_post(url: str, headers: Mapping[str, str], body: bytes, timeout_seconds: int
                ) -> tuple[int, Mapping[str, str], bytes]:
    parsed = urlsplit(url)
    connection = http.client.HTTPSConnection(parsed.hostname, timeout=timeout_seconds)
    deadline = time.monotonic() + timeout_seconds
    try:
        connection.request("POST", parsed.path, body=body, headers=dict(headers))
        response = connection.getresponse()
        pairs = response.getheaders()
        sensitive_headers = {"content-type", "content-length", "content-encoding", "transfer-encoding"}
        for name in sensitive_headers:
            if sum(key.lower() == name for key, _ in pairs) > 1:
                _fail("MALFORMED_TRANSPORT")
        # Only these headers affect decoding/framing. List-valued CORS headers
        # may legally repeat, including with differently cased field names.
        # Do not mistake an uninterpreted header for ambiguous message framing.
        response_headers = {key: value for key, value in pairs if key.lower() in sensitive_headers}
        if response.status != 200:
            return response.status, response_headers, b""
        chunks: list[bytes] = []
        size = 0
        while size <= MAX_RESPONSE_BYTES:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                _fail("TIMEOUT")
            if connection.sock is not None:
                connection.sock.settimeout(remaining)
            chunk = response.read1(min(65536, MAX_RESPONSE_BYTES + 1 - size))
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
        if size > MAX_RESPONSE_BYTES:
            _fail("RESPONSE_TOO_LARGE")
        return response.status, response_headers, b"".join(chunks)
    finally:
        connection.close()


def _object(value: object) -> dict:
    if not isinstance(value, dict):
        _fail("MALFORMED_RESPONSE")
    return value


def _array(value: object) -> list:
    if not isinstance(value, list) or not value:
        _fail("MALFORMED_RESPONSE")
    return value


def _text(value: object) -> str:
    if not isinstance(value, str):
        _fail("MALFORMED_RESPONSE")
    try:
        value.encode("utf-8")
    except UnicodeError:
        _fail("MALFORMED_RESPONSE")
    return value


def _count(value: object) -> int:
    if type(value) is not int or not 0 <= value <= 2**53 - 1:
        _fail("MALFORMED_USAGE")
    return value


def _parse_json(body: bytes) -> dict:
    def unique(pairs: list[tuple[str, object]]) -> dict:
        result: dict = {}
        for key, value in pairs:
            if key in result:
                _fail("MALFORMED_JSON")
            result[key] = value
        return result

    try:
        result = json.loads(body.decode("utf-8"), object_pairs_hook=unique,
                            parse_constant=lambda _: _fail("MALFORMED_JSON"))
    except (UnicodeError, ValueError, RecursionError):
        _fail("MALFORMED_JSON")
    return _object(result)


def _openai(data: dict) -> tuple[str, int, int]:
    if data.get("object") != "response" or data.get("status") != "completed":
        _fail("INCOMPLETE_RESPONSE")
    if data.get("error") is not None or data.get("incomplete_details") is not None:
        _fail("PROVIDER_RESPONSE_ERROR")
    texts = []
    for raw in _array(data.get("output")):
        item = _object(raw)
        if item.get("type") == "reasoning":
            if item.get("status") not in (None, "completed"):
                _fail("INCOMPLETE_RESPONSE")
            continue  # Never expose a model's internal reasoning as the answer.
        if (item.get("type") != "message" or item.get("role") != "assistant"
                or item.get("status") != "completed"):
            _fail("UNEXPECTED_CONTENT")
        for raw_part in _array(item.get("content")):
            part = _object(raw_part)
            if part.get("type") == "refusal":
                _fail("REFUSAL")
            if part.get("type") != "output_text":
                _fail("UNEXPECTED_CONTENT")
            texts.append(_text(part.get("text")))
    usage = _object(data.get("usage"))
    inputs, outputs = _count(usage.get("input_tokens")), _count(usage.get("output_tokens"))
    if _count(usage.get("total_tokens")) != inputs + outputs:
        _fail("MALFORMED_USAGE")
    return "\n".join(texts), inputs, outputs


def _anthropic(data: dict) -> tuple[str, int, int]:
    if data.get("stop_reason") == "refusal":
        _fail("REFUSAL")
    if data.get("stop_reason") != "end_turn":
        _fail("INCOMPLETE_RESPONSE")
    if data.get("type") != "message" or data.get("role") != "assistant":
        _fail("MALFORMED_RESPONSE")
    texts = []
    for raw in _array(data.get("content")):
        part = _object(raw)
        if part.get("type") != "text":
            _fail("UNEXPECTED_CONTENT")
        texts.append(_text(part.get("text")))
    usage = _object(data.get("usage"))
    inputs = _count(usage.get("input_tokens"))
    for category in ("cache_creation_input_tokens", "cache_read_input_tokens"):
        if category in usage:
            inputs += _count(usage[category])
    return "\n".join(texts), inputs, _count(usage.get("output_tokens"))


def _gemini(data: dict) -> tuple[str, int, int]:
    if "promptFeedback" in data and _object(data["promptFeedback"]).get("blockReason"):
        _fail("REFUSAL")
    candidates = _array(data.get("candidates"))
    if len(candidates) != 1:
        _fail("UNEXPECTED_CONTENT")
    candidate = _object(candidates[0])
    if candidate.get("finishReason") != "STOP":
        _fail("INCOMPLETE_RESPONSE")
    content = _object(candidate.get("content"))
    if content.get("role") != "model":
        _fail("MALFORMED_RESPONSE")
    texts = []
    for raw in _array(content.get("parts")):
        part = _object(raw)
        if set(part) - {"text", "thought", "thoughtSignature"}:
            _fail("UNEXPECTED_CONTENT")
        if "thought" in part and type(part["thought"]) is not bool:
            _fail("MALFORMED_RESPONSE")
        value = _text(part.get("text"))
        if not part.get("thought", False):
            texts.append(value)
    usage = _object(data.get("usageMetadata"))
    inputs = _count(usage.get("promptTokenCount"))
    outputs = _count(usage.get("candidatesTokenCount")) + _count(usage.get("thoughtsTokenCount", 0))
    if (_count(usage.get("toolUsePromptTokenCount", 0)) != 0
            or _count(usage.get("totalTokenCount")) != inputs + outputs):
        _fail("MALFORMED_USAGE")
    return "\n".join(texts), inputs, outputs


def complete(request: ModelRequest, *, credential: str, transport: Transport | None = None) -> ModelResult:
    """Perform exactly one bounded request; never retry or select a model implicitly.

    Normalized usage counts are evidence, not an invoice. Cache pricing and model
    rates belong to the caller's versioned pricing/budget policy. An ambiguous
    failure must keep its reservation pending until the owner reconciles it.
    """
    _validate(request, credential)
    url, headers, body = _encode(request, credential)
    try:
        status, response_headers, raw = (transport or _https_post)(url, headers, body, request.timeout_seconds)
    except ProviderError:
        raise
    except TimeoutError:
        _fail("TIMEOUT")
    except Exception:
        _fail("TRANSPORT_ERROR")
    if type(status) is not int or not isinstance(response_headers, Mapping) or not isinstance(raw, bytes):
        _fail("MALFORMED_TRANSPORT")
    if 300 <= status <= 399:
        _fail("REDIRECT_REFUSED")
    if status != 200:
        _fail("HTTP_ERROR")
    if len(raw) > MAX_RESPONSE_BYTES:
        _fail("RESPONSE_TOO_LARGE")
    if any(not isinstance(key, str) or not isinstance(value, str) for key, value in response_headers.items()):
        _fail("MALFORMED_TRANSPORT")
    lowered = {key.lower(): value for key, value in response_headers.items()}
    if len(lowered) != len(response_headers):
        _fail("MALFORMED_TRANSPORT")
    content_type = lowered.get("content-type", "")
    if not isinstance(content_type, str) or content_type.split(";", 1)[0].strip().lower() != "application/json":
        _fail("UNEXPECTED_CONTENT_TYPE")
    if lowered.get("content-encoding", "identity").lower() != "identity":
        _fail("UNEXPECTED_ENCODING")
    if "content-length" in lowered:
        length = lowered["content-length"]
        if not re.fullmatch(r"[0-9]{1,10}", length):
            _fail("MALFORMED_TRANSPORT")
        if int(length) != len(raw):
            _fail("TRUNCATED_RESPONSE")
    data = _parse_json(raw)
    if data.get("error") is not None:
        _fail("PROVIDER_RESPONSE_ERROR")
    text, inputs, outputs = {"openai": _openai, "anthropic": _anthropic, "gemini": _gemini}[request.provider](data)
    if not text.strip():
        _fail("EMPTY_RESPONSE")
    if outputs > request.max_output_tokens:
        _fail("OUTPUT_LIMIT_EXCEEDED")
    model = _text(data.get("modelVersion" if request.provider == "gemini" else "model"))
    if not _valid_identifier(model):
        _fail("MALFORMED_RESPONSE")
    identifier = data.get("responseId" if request.provider == "gemini" else "id")
    if identifier is not None and not _valid_identifier(identifier):
        _fail("MALFORMED_RESPONSE")
    tier = data.get("service_tier") if request.provider == "openai" else None
    if tier is not None and tier != "default":
        _fail("UNEXPECTED_SERVICE_TIER")
    return ModelResult(text, inputs, outputs, model, identifier, tier)
