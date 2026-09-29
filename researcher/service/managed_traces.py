"""Bounded, lossy projection of managed-session trace snapshots.

The public Agents tracing guide documents ``data[].otlp.resourceSpans[]`` but
not a stable wire discriminator for its displayed agent/generation/tool roles.
Every span is therefore registered as ``managed.agent`` with INTERNAL kind;
this is an unclassified grouping, not a claim about the original span's role.
Only exact standard GenAI usage attributes are recognized. Counts may arrive
late, overlap between nested spans, or be absent; never sum them as a bill.

Projection is pure. Collection uses an explicitly supplied read client, never
retries, persists no raw provider data, and does not export anything itself.
Provider trace/span IDs are deliberately retained for graph correlation.
"""
from __future__ import annotations

import json
import math
import re

from .contracts import ServiceError
from .tracing import validate_otlp

MAX_PAGES = 3
MAX_SPANS = 100
MAX_BYTES = 1_000_000
MAX_NODES = 25_000
MAX_DEPTH = 32
_USAGE = {"gen_ai.usage.input_tokens", "gen_ai.usage.output_tokens"}


def _fail(code="MANAGED_TRACE_INVALID"):
    raise ServiceError(code) from None


def _identifier(value):
    if (not isinstance(value, str) or not 1 <= len(value) <= 200
            or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", value) is None):
        _fail()
    return value


def _bounded_json(value):
    # Inspect before serializing: malicious depth, huge strings and unsupported
    # Python values must not cause unbounded recursion/allocation in json.dumps.
    pending, nodes, text_bytes = [(value, 0)], 0, 0
    while pending:
        item, depth = pending.pop()
        nodes += 1
        if nodes > MAX_NODES or depth > MAX_DEPTH:
            _fail("MANAGED_TRACE_LIMIT")
        if isinstance(item, str):
            if len(item) > MAX_BYTES:
                _fail("MANAGED_TRACE_LIMIT")
            try:
                text_bytes += len(item.encode("utf-8"))
            except UnicodeError:
                _fail()
            if text_bytes > MAX_BYTES:
                _fail("MANAGED_TRACE_LIMIT")
        elif type(item) in (dict, list):
            if len(item) > MAX_NODES or len(pending) + len(item) > MAX_NODES:
                _fail("MANAGED_TRACE_LIMIT")
            if type(item) is dict:
                if any(type(key) is not str for key in item):
                    _fail()
                pending.extend((child, depth + 1) for pair in item.items() for child in pair)
            else:
                pending.extend((child, depth + 1) for child in item)
        elif item is None or type(item) is bool:
            pass
        elif type(item) is int:
            if abs(item) > 2**64 - 1:
                _fail()
        elif type(item) is float and math.isfinite(item):
            pass
        else:
            _fail()
    if len(json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")) > MAX_BYTES:
        _fail("MANAGED_TRACE_LIMIT")


def _object(value):
    if type(value) is not dict:
        _fail()
    return value


def _array(value, maximum=MAX_SPANS):
    if type(value) is not list:
        _fail()
    if len(value) > maximum:
        _fail("MANAGED_TRACE_LIMIT")
    return value


def _hex(value, length):
    if (not isinstance(value, str) or re.fullmatch(r"[a-fA-F0-9]{" + str(length) + "}", value) is None
            or int(value, 16) == 0):
        _fail()
    return value.lower()


def _time(value):
    if (not isinstance(value, str) or re.fullmatch(r"[0-9]{1,19}", value) is None
            or int(value) > 2**63 - 1):
        _fail()
    return str(int(value))


def _usage(attributes):
    result, seen = {}, set()
    for attribute in _array(attributes, 256):
        attribute = _object(attribute)
        key = attribute.get("key")
        if not isinstance(key, str) or not key or key in seen or "value" not in attribute:
            _fail()
        seen.add(key)
        if key not in _USAGE:
            continue
        value = _object(attribute["value"])
        if set(value) != {"intValue"}:
            _fail()
        count = value["intValue"]
        if isinstance(count, str) and re.fullmatch(r"[0-9]{1,16}", count):
            count = int(count)
        if type(count) is not int or not 0 <= count <= 2**53 - 1:
            _fail()
        result[key] = count
    return result


def _span(raw):
    raw = _object(raw)
    kind = raw.get("kind", 0)
    if type(kind) is not int or kind not in range(6):
        _fail()
    status = _object(raw.get("status", {})).get("code", 0)
    if type(status) is not int or status not in (0, 1, 2):
        _fail()
    span = {"traceId": _hex(raw.get("traceId"), 32), "spanId": _hex(raw.get("spanId"), 16),
            "name": "managed.agent", "kind": 1,
            "startTimeUnixNano": _time(raw.get("startTimeUnixNano")),
            "endTimeUnixNano": _time(raw.get("endTimeUnixNano")), "status": {"code": status}}
    if int(span["endTimeUnixNano"]) < int(span["startTimeUnixNano"]):
        _fail()
    # An absent or empty protobuf parent means root. A nonempty zero ID is
    # malformed rather than a usable graph edge.
    if raw.get("parentSpanId") not in (None, ""):
        span["parentSpanId"] = _hex(raw["parentSpanId"], 16)
    if span.get("parentSpanId") == span["spanId"]:
        _fail("MANAGED_TRACE_GRAPH")
    usage = _usage(raw.get("attributes", []))
    known = len(usage) == 2
    attributes = [{"key": "gen_ai.system", "value": {"stringValue": "openai"}},
                  {"key": "usage_known", "value": {"boolValue": known}}]
    attributes.extend({"key": key, "value": {"intValue": str(value)}} for key, value in sorted(usage.items()))
    span["attributes"] = attributes
    return span, kind != 1, known


def _check_graph(spans):
    by_id = {(item["traceId"], item["spanId"]): item for item in spans}
    missing, checked = set(), set()
    for identity, span in by_id.items():
        parent = span.get("parentSpanId")
        if parent is not None and (identity[0], parent) not in by_id:
            missing.add(identity)
        path, current = set(), identity
        while current in by_id and current not in checked:
            if current in path:
                _fail("MANAGED_TRACE_GRAPH")
            path.add(current)
            parent = by_id[current].get("parentSpanId")
            if parent is None:
                break
            current = (current[0], parent)
        checked.update(path)
    return missing


def project_managed_traces(pages: list[dict], *, session_id: str) -> dict:
    """Project a caller-fetched, ascending snapshot; never claim full coverage.

    This function cannot authenticate the origin of fixture/provider dictionaries.
    The caller must fetch them through the admitted client for ``session_id``.
    Explicit session bindings, when returned, must match. Missing parents are
    retained and flagged because capped snapshots may omit ancestor spans.
    """
    _identifier(session_id)
    if type(pages) is not list or not 1 <= len(pages) <= MAX_PAGES:
        _fail("MANAGED_TRACE_LIMIT")
    _bounded_json(pages)
    record_ids, spans, original_spans = set(), [], {}
    duplicates = normalized = usage_known = 0
    for index, page in enumerate(pages):
        page = _object(page)
        if (page.get("object") != "list" or type(page.get("has_more")) is not bool
                or (index and not pages[index - 1]["has_more"])):
            _fail("MANAGED_TRACE_PAGE")
        if "session_id" in page and page["session_id"] != session_id:
            _fail("MANAGED_TRACE_SESSION")
        records = _array(page.get("data"), 20)
        ids = [_identifier(_object(record).get("id")) for record in records]
        if ("first_id" not in page or "last_id" not in page
                or page["first_id"] != (ids[0] if ids else None)
                or page["last_id"] != (ids[-1] if ids else None)
                or (page["has_more"] and not ids)):
            _fail("MANAGED_TRACE_PAGE")
        for record, record_id in zip(records, ids):
            if record_id in record_ids:
                _fail("MANAGED_TRACE_PAGE")
            record_ids.add(record_id)
            if "session_id" in record and record["session_id"] != session_id:
                _fail("MANAGED_TRACE_SESSION")
            otlp = _object(record.get("otlp"))
            for resource in _array(otlp.get("resourceSpans", [])):
                for scope in _array(_object(resource).get("scopeSpans", [])):
                    for raw in _array(_object(scope).get("spans", [])):
                        span, normalized_kind, known = _span(raw)
                        identity = (span["traceId"], span["spanId"])
                        # Compare the bounded original, not its lossy projection:
                        # conflicting discarded content must not masquerade as an
                        # identical duplicate. This value never leaves memory.
                        original = json.dumps(raw, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
                        if identity in original_spans:
                            if original_spans[identity] != original:
                                _fail("MANAGED_TRACE_CONFLICT")
                            duplicates += 1
                            continue
                        if len(spans) >= MAX_SPANS:
                            _fail("MANAGED_TRACE_LIMIT")
                        original_spans[identity] = original
                        spans.append(span)
                        normalized += normalized_kind
                        usage_known += known
    missing = _check_graph(spans)
    truncated = pages[-1]["has_more"]
    for span in spans:
        span["attributes"].append({"key": "incomplete", "value": {"boolValue": truncated or
            (span["traceId"], span["spanId"]) in missing}})
    payload = None
    if spans:
        payload = {"resourceSpans": [{"resource": {"attributes": [{"key": "service.name",
            "value": {"stringValue": "context-research-harness"}}]}, "scopeSpans": [{"scope": {
            "name": "researcher.service", "version": "1"}, "spans": spans}]}]}
        validate_otlp(payload)
    return {"payload": payload, "summary": {"schema": "managed-trace-projection/v1",
        "page_count": len(pages), "record_count": len(record_ids), "span_count": len(spans),
        "duplicate_spans": duplicates, "missing_parent_spans": len(missing),
        "normalized_kind_spans": normalized, "usage_known_spans": usage_known,
        "pagination_truncated": truncated, "coverage": "available_snapshot",
        "classification": "unclassified", "usage": "reported_not_billing"}}


def collect_managed_traces(client, session_id: str, *, max_pages: int = MAX_PAGES) -> dict:
    """One to three explicit read calls, no retry or persistent raw capture.

    The passed client must expose ``traces(session_id, after=None)`` with fixed
    ascending order, limit 20, bounded transport, and authenticated origin.
    Admission, credentials and export authority remain with the caller.
    """
    _identifier(session_id)
    if type(max_pages) is not int or not 1 <= max_pages <= MAX_PAGES:
        _fail("MANAGED_TRACE_LIMIT")
    pages, after = [], None
    for _ in range(max_pages):
        pages.append(client.traces(session_id, after=after))
        result = project_managed_traces(pages, session_id=session_id)
        if not pages[-1]["has_more"] or result["summary"]["span_count"] == MAX_SPANS:
            return result
        after = pages[-1]["last_id"]
    return result
