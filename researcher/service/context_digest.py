"""Pure, bounded daily discovery context; never evidence acceptance or authority.

The caller must replay captured responses before use. Selection uses lexical
overlap, declared content depth and source round-robin, not engagement or a claim
of semantic quality. The full observation index and every omission are retained.
"""

from __future__ import annotations

from collections import defaultdict
import json
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from researcher.scripts.schema_contract import canonicalize, sha256_bytes
from .contracts import ServiceError, digest, integer, obj, string, validate
from .knowledge import _tokens

MAX_INPUT_BYTES = 8 * 1024 * 1024
MAX_RECORDS = 256
MAX_EXCERPT_BYTES = 4096
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,159}\Z")
_ARXIV = re.compile(
    r"(?:abs|pdf|html)/([0-9]{4}\.[0-9]{4,5})(?:v[1-9][0-9]*)?(?:\.pdf)?\Z"
)
_TRACKING = frozenset({"fbclid", "gclid"})
_COVERAGE_SCHEMA = obj(
    {
        "schema": {"const": "retrieval-coverage/v1"},
        "window_start": integer(0, 2**53 - 1),
        "window_end": integer(1, 2**53 - 1),
        "window_applied": {"type": "boolean"},
        "window_resolution": {"enum": ["day", "second", "not_applied"]},
        "query_sha256": string(71, pattern=r"^sha256:[0-9a-f]{64}$"),
        "mode": string(96, pattern=r"^[a-z][a-z0-9_]{0,95}$"),
        "page_limit": {"const": 1, "type": "integer"},
        "returned_count": integer(0, 64),
        "continuation_available": {"type": "boolean"},
        "partial": {"type": "boolean"},
        "completeness": {"const": "bounded_page_not_exhaustive"},
        "quality_assessed": {"const": False, "type": "boolean"},
    }
)


def _text(value, maximum):
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise ServiceError("INVALID_DISCOVERY_TEXT")
    try:
        if len(value.encode("utf-8")) > maximum:
            raise ServiceError("DISCOVERY_TEXT_LIMIT")
    except UnicodeError:
        raise ServiceError("INVALID_DISCOVERY_TEXT") from None
    return value


def _url(value):
    _text(value, 8192)
    try:
        parsed = urlsplit(value)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.port not in (None, 443)
            or "\\" in value
            or any(ord(c) <= 32 or ord(c) == 127 for c in value)
        ):
            raise ValueError()
        query = [
            (k, v)
            for k, v in parse_qsl(parsed.query, keep_blank_values=True)
            if not k.lower().startswith("utm_") and k.lower() not in _TRACKING
        ]
        return urlunsplit(
            ("https", parsed.netloc.lower(), parsed.path or "/", urlencode(query), "")
        )
    except (ValueError, UnicodeError):
        raise ServiceError("INVALID_DISCOVERY_URL") from None


def _metadata(item):
    values = item.get("metadata", [])
    if isinstance(values, dict):
        values = list(values.items())
    if not isinstance(values, (list, tuple)) or len(values) > 128:
        raise ServiceError("INVALID_DISCOVERY_METADATA")
    result = defaultdict(list)
    for pair in values:
        if (
            not isinstance(pair, (list, tuple))
            or len(pair) != 2
            or not all(isinstance(v, str) for v in pair)
        ):
            raise ServiceError("INVALID_DISCOVERY_METADATA")
        if len(pair[0]) > 96 or len(pair[1].encode("utf-8")) > 32768:
            raise ServiceError("INVALID_DISCOVERY_METADATA")
        result[pair[0]].append(pair[1])
    return result


def _single(meta, name, default):
    values = meta.get(name, [])
    if len(set(values)) > 1:
        raise ServiceError("AMBIGUOUS_DISCOVERY_METADATA")
    return values[0] if values else default


def _work_key(url):
    parsed = urlsplit(url)
    if parsed.hostname in {"arxiv.org", "www.arxiv.org", "export.arxiv.org"}:
        match = _ARXIV.fullmatch(parsed.path.lstrip("/"))
        if match:
            return "arxiv:" + match[1]
    if parsed.hostname in {"doi.org", "dx.doi.org"} and parsed.path.startswith("/10."):
        return "doi:" + parsed.path[1:].casefold()
    return "url:" + sha256_bytes(url.encode())[7:]


def _related_work_keys(url, meta):
    keys = {_work_key(url)}
    for raw in meta.get("outbound_link", [])[:20]:
        try:
            link = json.loads(raw)
            if isinstance(link, dict):
                candidate = link.get("unwound_url") or link.get("expanded_url")
                if isinstance(candidate, str) and candidate.startswith("https://"):
                    keys.add(_work_key(_url(candidate)))
        except (ValueError, ServiceError, RecursionError):
            # Invalid relationship is not permission to follow an arbitrary URL.
            continue
    for key in ("doi", "doi_url", "work_id"):
        for value in meta.get(key, [])[:8]:
            if key == "doi" and value.startswith("10."):
                keys.add("doi:" + value.casefold())
            elif value.startswith("arxiv:") and len(value) < 100:
                keys.add(value)
            elif value.startswith("https://doi.org/"):
                keys.add(_work_key(_url(value)))
    return sorted(keys)


def content_depth(kind, source):
    """Describe declared format, never source credibility or claim truth."""
    if kind in {"none", "title", "title_only"}:
        return "title_only"
    if kind in {"arxiv_abstract", "openalex_abstract", "abstract"}:
        return "abstract"
    if kind in {
        "rss_content",
        "rss_content_encoded",
        "atom_content",
        "content_encoded",
        "article_body",
    }:
        return "article_text"
    if kind.startswith("x_") or source in {"x", "hacker_news"}:
        return "social_signal"
    return "snippet" if kind != "unknown" else "unknown"


def _excerpt(raw, query_terms):
    """Select a lexical-match chunk while retaining exact UTF-8 byte offsets."""
    best, start = None, 0
    while start < len(raw):
        text = raw[start : start + MAX_EXCERPT_BYTES].decode("utf-8", errors="ignore")
        end = start + len(text.encode("utf-8"))
        score = len(query_terms & set(_tokens(text)))
        if best is None or score > best[0]:
            best = (score, start, end, text)
        start = end
    return best


def _row(item, query_terms):
    if not isinstance(item, dict):
        raise ServiceError("INVALID_DISCOVERY_RECORD")
    source_id = _text(item.get("id"), 160)
    source = _text(item.get("source"), 64)
    if not _ID.fullmatch(source_id) or not _ID.fullmatch(source):
        raise ServiceError("INVALID_DISCOVERY_ID")
    text = _text(item.get("text"), 131072)
    raw = text.encode("utf-8")
    if item.get("sha256") != sha256_bytes(raw):
        raise ServiceError("EVIDENCE_DIGEST_MISMATCH")
    url = _url(item.get("url"))
    meta = _metadata(item)
    kind = _single(meta, "summary_kind", "unknown")
    if not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", kind):
        raise ServiceError("INVALID_DISCOVERY_DEPTH")
    truncated = _single(meta, "summary_truncated", "unknown")
    if truncated not in {"true", "false", "unknown"}:
        raise ServiceError("INVALID_DISCOVERY_TRUNCATION")
    depth = content_depth(kind, source)
    # Selection is lexical, not a completeness or entailment judgment.
    overlap, byte_start, byte_end, excerpt = _excerpt(raw, query_terms)
    excerpt_bytes = excerpt.encode("utf-8")
    identity = (
        "context_"
        + digest({"source": source, "id": source_id, "sha256": item["sha256"]})[7:]
    )
    row = {
        "id": identity,
        "source_id": source_id,
        "source": source,
        "url": url,
        "text": excerpt,
        "sha256": sha256_bytes(excerpt_bytes),
        "evidence_scope": "discovery_summary",
        "qualifiers": {
            "summary_kind": kind,
            "source_truncated": truncated,
            "selection_truncated": len(excerpt_bytes) < len(raw),
            "source_sha256": item["sha256"],
            "byte_start": byte_start,
            "byte_end": byte_end,
            "content_depth": depth,
        },
        "related_work_keys": _related_work_keys(url, meta),
        "lexical_overlap": overlap,
    }
    publication = _single(meta, "observed_publication_time", None)
    if publication is not None:
        _text(publication, 128)
        if any(ord(c) < 32 or ord(c) == 127 for c in publication):
            raise ServiceError("INVALID_DISCOVERY_PUBLICATION_TIME")
        # Providers expose both RFC dates and ISO timestamps. Preserve the
        # observation without deriving freshness or precision from its syntax.
        row["qualifiers"]["observed_publication_time"] = publication
    return row


def _coverage(lane, name, state, count, cursor):
    result = {
        "source": name,
        "state": state,
        "observed_items": count,
        "pagination_remaining": cursor is not None,
        "coverage_complete": False,
        "gap": state
        if state != "observed"
        else ("bounded_page" if cursor else "provider_window_not_exhaustive"),
    }
    captured = lane.get("coverage")
    if captured is not None:
        validate(captured, _COVERAGE_SCHEMA, "INVALID_DISCOVERY_COVERAGE")
        if (
            captured["window_start"] >= captured["window_end"]
            or captured["returned_count"] != count
            or captured["continuation_available"] != (cursor is not None)
            or captured["window_applied"]
            != (captured["window_resolution"] != "not_applied")
            or (
                (
                    state != "observed"
                    or cursor is not None
                    or not captured["window_applied"]
                )
                and not captured["partial"]
            )
        ):
            raise ServiceError("INVALID_DISCOVERY_COVERAGE")
        result["retrieval"] = dict(captured)
    return result


def _history(previous, query):
    if not isinstance(previous, (list, tuple)) or len(previous) > 7:
        raise ServiceError("INVALID_DISCOVERY_HISTORY")
    history = []
    for record in previous:
        if not isinstance(record, dict):
            raise ServiceError("INVALID_DISCOVERY_HISTORY")
        packet = record.get("context_digest", record)
        if (
            not isinstance(packet, dict)
            or packet.get("schema") != "research-context-digest/v1"
            or packet.get("authority") != "none"
            or packet.get("evidence_qualified") is not False
        ):
            raise ServiceError("INVALID_DISCOVERY_HISTORY")
        if packet.get("query") != query:
            continue
        observations = packet.get("observations")
        if not isinstance(observations, list) or len(observations) > MAX_RECORDS:
            raise ServiceError("INVALID_DISCOVERY_HISTORY")
        for row in observations:
            if (
                not isinstance(row, dict)
                or not isinstance(row.get("id"), str)
                or not _ID.fullmatch(row["id"])
                or not isinstance(row.get("related_work_keys"), list)
                or len(row["related_work_keys"]) > 40
                or any(
                    not isinstance(k, str) or len(k) > 8192
                    for k in row["related_work_keys"]
                )
            ):
                raise ServiceError("INVALID_DISCOVERY_HISTORY")
        history.append(observations)
    return history


def build_context_digest(query, lanes, *, max_bytes=32768, max_items=20, previous=()):
    """Build replay-bound discovery context; no I/O, paid calls or state mutation.

    Budget applies to the complete canonical JSON, including coverage and the
    omission ledger. If this mandatory index cannot fit, fail instead of hiding
    losses. `previous` contains at most seven verified digest/report snapshots.
    """
    _text(query, 4096)
    if (
        type(max_bytes) is not int
        or not 1024 <= max_bytes <= 131072
        or type(max_items) is not int
        or not 1 <= max_items <= 64
    ):
        raise ServiceError("INVALID_DISCOVERY_BUDGET")
    if not isinstance(lanes, (list, tuple)) or not 1 <= len(lanes) <= 12:
        raise ServiceError("INVALID_DISCOVERY_LANES")
    if not isinstance(previous, (list, tuple)) or len(previous) > 7:
        raise ServiceError("INVALID_DISCOVERY_HISTORY")
    try:
        if (
            len(canonicalize({"lanes": list(lanes), "previous": list(previous)}))
            > MAX_INPUT_BYTES
        ):
            raise ServiceError("DISCOVERY_INPUT_LIMIT")
    except ServiceError:
        raise
    except (ValueError, TypeError, RecursionError):
        raise ServiceError("INVALID_DISCOVERY_INPUT") from None
    terms = set(_tokens(query))
    rows, seen, coverage, lane_names = [], set(), [], set()
    bindings = {}
    duplicates = 0
    for lane in lanes:
        if not isinstance(lane, dict):
            raise ServiceError("INVALID_DISCOVERY_LANE")
        name = _text(lane.get("source"), 64)
        if not _ID.fullmatch(name) or name in lane_names:
            raise ServiceError("DUPLICATE_DISCOVERY_LANE")
        lane_names.add(name)
        state = lane.get("state")
        if state not in {"observed", "rate_limited", "unavailable", "failed"}:
            raise ServiceError("INVALID_DISCOVERY_STATE")
        entries = lane.get("evidence", [])
        if (
            not isinstance(entries, list)
            or len(entries) > 64
            or (state != "observed" and entries)
        ):
            raise ServiceError("INVALID_DISCOVERY_RECORDS")
        cursor = lane.get("next_cursor")
        if cursor is not None:
            _text(cursor, 2048)
        coverage.append(_coverage(lane, name, state, len(entries), cursor))
        for entry in entries:
            row = _row(entry, terms)
            if row["source"] != name:
                raise ServiceError("DISCOVERY_SOURCE_MISMATCH")
            if row["id"] in seen:
                if bindings[row["id"]] != row:
                    raise ServiceError("CONFLICTING_DISCOVERY_OBSERVATION")
                duplicates += 1
                continue
            seen.add(row["id"])
            bindings[row["id"]] = row
            rows.append(row)
    if len(rows) > MAX_RECORDS:
        raise ServiceError("DISCOVERY_RECORD_LIMIT")
    rows.sort(key=lambda r: r["id"])
    history = _history(previous, query)
    historic_ids = {r["id"] for page in history for r in page}
    historic_works = {
        key for page in history for r in page for key in r.get("related_work_keys", [])
    }
    works = {key for row in rows for key in row["related_work_keys"]}
    observations = [
        {k: row[k] for k in ("id", "source_id", "source", "related_work_keys")}
        for row in rows
    ]
    result = {
        "schema": "research-context-digest/v1",
        "authority": "none",
        "evidence_qualified": False,
        "query": query,
        "method": "lexical-depth-source-round-robin-v1",
        "semantic_quality_measured": False,
        "items": [],
        "observations": observations,
        "coverage": coverage,
        "omissions": [],
        "signals": {
            "history_windows": len(history),
            "status": "sampled_observations_only" if history else "no_history",
            "new_observation_versions": len(seen - historic_ids),
            "reobserved_versions": len(seen & historic_ids),
            "new_related_work_keys": len(works - historic_works),
            "reobserved_work_keys": len(works & historic_works),
            "exact_duplicates_removed": duplicates,
            "independent_corroboration_established": False,
        },
    }
    # Round-robin prevents a high-volume provider from occupying the whole
    # context. Topic families belong in explicit source queries, not word lists.
    buckets = defaultdict(list)
    depth_order = {
        "article_text": 0,
        "abstract": 1,
        "snippet": 2,
        "social_signal": 3,
        "title_only": 4,
        "unknown": 5,
    }
    for row in rows:
        buckets[row["source"]].append(row)
    for bucket in buckets.values():
        bucket.sort(
            key=lambda r: (
                -r["lexical_overlap"],
                depth_order[r["qualifiers"]["content_depth"]],
                r["id"] in historic_ids,
                r["id"],
            )
        )
    ordered = []
    for offset in range(max((len(b) for b in buckets.values()), default=0)):
        ordered.extend(
            buckets[source][offset]
            for source in sorted(buckets)
            if offset < len(buckets[source])
        )
    result["omissions"] = [{"id": r["id"], "reason": "budget"} for r in ordered]
    if len(canonicalize(result)) > max_bytes:
        raise ServiceError("DISCOVERY_INDEX_BUDGET")
    for row in ordered:
        omission = next(o for o in result["omissions"] if o["id"] == row["id"])
        if len(result["items"]) >= max_items:
            omission["reason"] = "item_limit"
            continue
        result["omissions"].remove(omission)
        result["items"].append(row)
        if len(canonicalize(result)) > max_bytes:
            result["items"].pop()
            result["omissions"].append(omission)
    result["omissions"].sort(key=lambda o: o["id"])
    if len(canonicalize(result)) > max_bytes:
        raise ServiceError("DISCOVERY_INDEX_BUDGET")
    return result
