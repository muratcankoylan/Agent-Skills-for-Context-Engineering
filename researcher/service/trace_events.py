"""Explicit metadata-only operational Events associated with OTLP trace IDs.

An acknowledgement is not a UI/readback proof. Unknown delivery is never retried
here. The caller owns durable intent and separate Event/OTLP phase receipts.
"""
from __future__ import annotations

from datetime import datetime, timezone
import http.client
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

from researcher.service.contracts import ServiceError
from researcher.service import trace_export as wire, tracing

ENDPOINT = "https://api.raindrop.ai/v1/events/track"
TIMEOUT_SECONDS = 10
MAX_REQUEST_BYTES = 1_048_576
MAX_RESPONSE_BYTES = 65_536
ERROR_CODES = frozenset({"WALL_TIMEOUT", "TIMEOUT", "TRANSPORT_ERROR", "WORKER_START_FAILED",
    "WORKER_FAILED", "MALFORMED_TRANSPORT", "RESPONSE_TOO_LARGE", "REDIRECT_REFUSED",
    "HTTP_REJECTED", "UNEXPECTED_HTTP_STATUS", "UNEXPECTED_ENCODING", "INVALID_RESPONSE_LENGTH",
    "NONEMPTY_ACKNOWLEDGEMENT", "UNEXPECTED_CONTENT_TYPE", "MALFORMED_ACKNOWLEDGEMENT"})
_FRAMING = {"content-type", "content-length", "content-encoding", "transfer-encoding"}


def project_events(payload: dict) -> list[dict]:
    """Project validated roots only, without guessing missing roots in a batch."""
    tracing.validate_otlp(payload)
    events, seen = [], set()
    for span in payload["resourceSpans"][0]["scopeSpans"][0]["spans"]:
        if "parentSpanId" in span:
            continue
        if span["traceId"] in seen:
            raise ServiceError("TRACE_EVENT_DUPLICATE_ROOT")
        seen.add(span["traceId"])
        started, ended = int(span["startTimeUnixNano"]), int(span["endTimeUnixNano"])
        timestamp = datetime.fromtimestamp(started // 1_000_000_000, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        timestamp += f".{started % 1_000_000_000:09d}Z"
        properties = {"metadata_only": True, "status": {0: "unset", 1: "ok", 2: "error"}[span["status"]["code"]],
                      "duration_ms": (ended - started) // 1_000_000}
        for attribute in span["attributes"]:
            if attribute["key"] == "fixture":
                properties["fixture"] = attribute["value"]["boolValue"]
        events.append({"event_id": span["traceId"], "user_id": "context-research-harness",
                       "event": span["name"], "timestamp": timestamp, "properties": properties})
    return events


def _result(count, status, *, error=None, attempted=True, http_status=None):
    result = {"schema": "trace-event-export/v1", "status": status, "attempted": attempted,
              "event_count": count, "error_code": error}
    if http_status is not None:
        result["http_status"] = http_status
    return result


def validate_event_result(value, count) -> None:
    """Validate a receipt, including terminal/count/attempt consistency."""
    fields = {"schema", "status", "attempted", "event_count", "error_code"}
    if (type(count) is not int or not 0 <= count <= 100 or not isinstance(value, dict)
            or set(value) not in (fields, fields | {"http_status"})
            or value["schema"] != "trace-event-export/v1" or type(value["event_count"]) is not int
            or value["event_count"] != count or type(value["attempted"]) is not bool):
        raise ServiceError("TRACE_EVENT_INVALID_RESULT")
    status, error, attempted = value["status"], value["error_code"], value["attempted"]
    valid = ((status == "empty" and count == 0 and not attempted and error is None)
        or (status == "exported" and count > 0 and attempted and error is None)
        or (status == "rejected" and count > 0 and attempted and error == "HTTP_REJECTED")
        or (status == "unknown" and count > 0 and isinstance(error, str)
            and error in ERROR_CODES - {"HTTP_REJECTED"} and attempted == (error != "WORKER_START_FAILED")))
    if not valid:
        raise ServiceError("TRACE_EVENT_INVALID_RESULT")
    if "http_status" in value:
        observed = value["http_status"]
        if (type(observed) is not int or not 100 <= observed <= 599 or not attempted or count == 0
                or status == "exported" and observed not in (200, 204)
                or status == "rejected" and not 400 <= observed <= 499
                or error == "REDIRECT_REFUSED" and not 300 <= observed <= 399
                or error == "UNEXPECTED_HTTP_STATUS" and (observed == 204 or 300 <= observed <= 499)):
            raise ServiceError("TRACE_EVENT_INVALID_RESULT")


def _prepare(payload, credential, project_id, allow_default_project):
    events = project_events(payload)
    if not events:
        return b"[]", 0, {}
    preflight = wire.preflight_config(credential=credential, project_id=project_id,
                                     allow_default_project=allow_default_project)
    if preflight["error_codes"]:
        raise ServiceError(preflight["error_codes"][0])
    body = json.dumps(events, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
    original = json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
    if len(body) > MAX_REQUEST_BYTES:
        raise ServiceError("TRACE_EVENT_INVALID_PAYLOAD")
    if credential.encode("ascii") in body or credential.encode("ascii") in original or credential in project_id:
        raise ServiceError("TRACE_EXPORT_CREDENTIAL_REFLECTION")
    headers = {"Content-Type": "application/json", "Accept": "application/json", "Accept-Encoding": "identity",
               "Authorization": f"Bearer {credential}", "X-Raindrop-Project-Id": project_id}
    return body, len(events), headers


def _native(url, headers, body, timeout):
    if url != ENDPOINT or type(timeout) is not int or timeout != TIMEOUT_SECONDS:
        raise wire._TransportError("MALFORMED_TRANSPORT")
    connection = http.client.HTTPSConnection("api.raindrop.ai", timeout=timeout)
    deadline = time.monotonic() + timeout
    try:
        connection.request("POST", "/v1/events/track", body=body, headers=dict(headers))
        response = connection.getresponse()
        pairs = response.getheaders()
        if len(pairs) > 100 or any(sum(key.lower() == name for key, _ in pairs) > 1 for name in _FRAMING):
            raise wire._TransportError("MALFORMED_TRANSPORT")
        selected = wire._headers({key: value for key, value in pairs if key.lower() in _FRAMING})
        # No remote rejection/error text is needed or forwarded. Success bodies
        # stay private to the child; only its validated closed receipt escapes.
        if response.status not in (200, 204):
            return response.status, selected, b""
        length = selected.get("content-length")
        if length is not None:
            if not re.fullmatch(r"[0-9]{1,10}", length):
                raise wire._TransportError("MALFORMED_TRANSPORT")
            if int(length) > MAX_RESPONSE_BYTES:
                raise wire._TransportError("RESPONSE_TOO_LARGE")
        chunks, size = [], 0
        while size <= MAX_RESPONSE_BYTES:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise wire._TransportError("TIMEOUT")
            if connection.sock is not None:
                connection.sock.settimeout(remaining)
            chunk = response.read1(1 if response.status == 204 else min(8192, MAX_RESPONSE_BYTES + 1 - size))
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
            if response.status == 204:
                break
        if size > MAX_RESPONSE_BYTES:
            raise wire._TransportError("RESPONSE_TOO_LARGE")
        return response.status, selected, b"".join(chunks)
    finally:
        connection.close()


def _dispatch(body, count, headers, transport):
    observed = None
    try:
        status, response_headers, raw = transport(ENDPOINT, headers, body, TIMEOUT_SECONDS)
        if type(status) is not int or not 100 <= status <= 599 or not isinstance(raw, bytes):
            raise wire._TransportError("MALFORMED_TRANSPORT")
        observed = status
        lowered = wire._headers(response_headers)
    except wire._TransportError as error:
        return _result(count, "unknown", error=error.code, attempted=error.code != "WORKER_START_FAILED",
                       http_status=observed)
    except TimeoutError:
        return _result(count, "unknown", error="TIMEOUT", http_status=observed)
    except Exception:
        return _result(count, "unknown", error="TRANSPORT_ERROR", http_status=observed)
    if len(raw) > MAX_RESPONSE_BYTES:
        return _result(count, "unknown", error="RESPONSE_TOO_LARGE", http_status=status)
    if 300 <= status <= 399:
        return _result(count, "unknown", error="REDIRECT_REFUSED", http_status=status)
    if 400 <= status <= 499:
        return _result(count, "rejected", error="HTTP_REJECTED", http_status=status)
    if status not in (200, 204):
        return _result(count, "unknown", error="UNEXPECTED_HTTP_STATUS", http_status=status)
    if status == 204 and "transfer-encoding" in lowered:
        return _result(count, "unknown", error="MALFORMED_TRANSPORT", http_status=status)
    if lowered.get("content-encoding", "identity").lower() != "identity":
        return _result(count, "unknown", error="UNEXPECTED_ENCODING", http_status=status)
    length = lowered.get("content-length")
    if length is not None and (not re.fullmatch(r"[0-9]{1,10}", length) or int(length) != (0 if status == 204 else len(raw))):
        return _result(count, "unknown", error="INVALID_RESPONSE_LENGTH", http_status=status)
    if status == 204:
        if raw:
            return _result(count, "unknown", error="NONEMPTY_ACKNOWLEDGEMENT", http_status=status)
    else:
        if lowered.get("content-type", "").split(";", 1)[0].strip().lower() != "application/json":
            return _result(count, "unknown", error="UNEXPECTED_CONTENT_TYPE", http_status=status)
        # Empirically verified on 2026-09-29: the cloud returned HTTP 200 with
        # {"events":[{"event_id":<submitted ID>}]} and the Event appeared in UI.
        # SDK 0.0.69 accepts successful HTTP responses, but that broader behavior
        # is not our contract: require the exact complete, unique submitted set.
        try:
            data = wire._json(raw)
            if set(data) != {"events"} or not isinstance(data["events"], list) or len(data["events"]) != count:
                raise ValueError()
            received = []
            for event in data["events"]:
                if not isinstance(event, dict) or set(event) != {"event_id"} or not isinstance(event["event_id"], str):
                    raise ValueError()
                received.append(event["event_id"])
            expected = [event["event_id"] for event in json.loads(body)]
            if len(expected) != count or len(set(received)) != count or set(received) != set(expected):
                raise ValueError()
        except (ValueError, TypeError, KeyError, RecursionError):
            return _result(count, "unknown", error="MALFORMED_ACKNOWLEDGEMENT", http_status=status)
    return _result(count, "exported", http_status=status)


def _isolated(payload, credential, project_id, count, allow_default_project):
    packet = {"payload": payload, "credential": credential, "project_id": project_id,
              "allow_default_project": allow_default_project}
    root = Path(__file__).resolve().parents[2]
    try:
        process = subprocess.run([sys.executable, "-B", "-m", "researcher.service.trace_events"],
            input=json.dumps(packet, allow_nan=False, separators=(",", ":")).encode(), capture_output=True,
            cwd=root, timeout=TIMEOUT_SECONDS, check=False,
            env={"PATH": os.defpath, "PYTHONPATH": str(root), "PYTHONUTF8": "1"})
    except subprocess.TimeoutExpired:
        return _result(count, "unknown", error="WALL_TIMEOUT")
    except OSError:
        return _result(count, "unknown", error="WORKER_START_FAILED", attempted=False)
    if process.returncode or process.stderr or len(process.stdout) > 4096:
        return _result(count, "unknown", error="WORKER_FAILED")
    try:
        result = wire._json(process.stdout)
        validate_event_result(result, count)
        return result
    except (ValueError, TypeError, KeyError, RecursionError, ServiceError):
        return _result(count, "unknown", error="WORKER_FAILED")


def export_events(payload: dict, *, credential: str, project_id: str,
                  transport: wire.Transport | None = None, allow_default_project=False) -> dict:
    """Make one fixed-origin attempt; injected transports are offline test seams."""
    body, count, headers = _prepare(payload, credential, project_id, allow_default_project)
    if count == 0:
        return _result(0, "empty", attempted=False)
    if transport is None:
        return _isolated(payload, credential, project_id, count, allow_default_project)
    return _dispatch(body, count, headers, transport)


def _worker() -> None:
    # The credential only arrives on stdin. The child emits a closed receipt,
    # never raw response headers/body or exception diagnostics.
    try:
        raw = sys.stdin.buffer.read(2 * MAX_REQUEST_BYTES + 1)
        if len(raw) > 2 * MAX_REQUEST_BYTES:
            raise ValueError()
        packet = wire._json(raw)
        if set(packet) != {"payload", "credential", "project_id", "allow_default_project"}:
            raise ValueError()
        body, count, headers = _prepare(packet["payload"], packet["credential"], packet["project_id"],
                                        packet["allow_default_project"])
        result = _dispatch(body, count, headers, _native) if count else _result(0, "empty", attempted=False)
        validate_event_result(result, count)
    except Exception:
        raise SystemExit(2) from None
    sys.stdout.write(json.dumps(result, separators=(",", ":")))


if __name__ == "__main__":
    _worker()
