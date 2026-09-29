"""Pure bounded discovery packets, not relevance judgments or accepted evidence.

The caller must verify pipeline observations and captured bytes before calling.
This module binds the supplied records but performs no I/O, extraction replay,
model execution, or authenticity verification. The exact integer-JCS packet has
a 1..262144 byte budget. Its complete provenance index is mandatory; only whole
work text records may be omitted. Lane order expresses operator priority, not
semantic relevance. Source occurrences are not independent corroboration.
"""

from __future__ import annotations

import copy
import re
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import urlsplit, urlunsplit

if __package__:
    from .schema_contract import ContractError, canonicalize, sha256_bytes
    from .source_connectors import Lead
else:
    from schema_contract import ContractError, canonicalize, sha256_bytes
    from source_connectors import Lead


MAX_PACKET_BYTES = 262_144
MAX_LANES = 12
MAX_INPUT_BYTES = 16 * 1024 * 1024
_CAPTURE_SCOPE = "source_response_set_not_exact_support_span"
_DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")
_ARXIV = re.compile(
    r"(?P<work>(?:[0-9]{4}\.[0-9]{4,5}|[A-Za-z-]+(?:\.[A-Za-z]{2})?/[0-9]{7}))"
    r"(?P<version>v[1-9][0-9]*)?\Z"
)
_SOURCE_MODES = {
    "arxiv": ("arxiv", "provider_query_search", True, 3),
    "github": ("github_api", "latest_commit_window_not_query_search", False, 3),
    "hacker_news": ("hacker_news", "bounded_feed_window_with_literal_filter", True, 3),
    "deepmind": ("rss_atom", "company_feed_window_not_query_search", False, 20),
    "huggingface": ("rss_atom", "company_feed_window_not_query_search", False, 20),
    "microsoft_research": (
        "rss_atom",
        "company_feed_window_not_query_search",
        False,
        20,
    ),
}


class DiscoveryError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _text(value: Any, maximum: int, *, empty: bool = False) -> str:
    if not isinstance(value, str) or (not value and not empty) or "\x00" in value:
        raise DiscoveryError("INVALID_TEXT", "text must be bounded Unicode")
    try:
        size = len(value.encode("utf-8"))
    except UnicodeError as error:
        raise DiscoveryError("INVALID_TEXT", "text must be bounded Unicode") from error
    if size > maximum:
        raise DiscoveryError("INVALID_TEXT", "text exceeds its byte limit")
    return value


def _digest(value: Any) -> str:
    if not isinstance(value, str) or _DIGEST.fullmatch(value) is None:
        raise DiscoveryError("INVALID_DIGEST", "source binding is not a SHA-256 digest")
    return value


def _list(value: Any, maximum: int) -> Sequence:
    if (
        not isinstance(value, Sequence)
        or isinstance(value, (str, bytes, bytearray))
        or len(value) > maximum
    ):
        raise DiscoveryError("INVALID_SEQUENCE", "input sequence exceeds its bounds")
    return value


def _canonical_url(value: str) -> str:
    _text(value, 8192)
    if "\\" in value or any(ord(char) <= 32 or ord(char) == 127 for char in value):
        raise DiscoveryError("INVALID_URL", "URL contains unsafe characters")
    try:
        parsed = urlsplit(value)
        host = parsed.hostname
        port = parsed.port
        if parsed.scheme != "https" or not host or parsed.username or parsed.password:
            raise ValueError("not credential-free HTTPS")
        authority = f"[{host}]" if ":" in host else host
        if port is not None and port != 443:
            authority += ":" + str(port)
        return urlunsplit(("https", authority, parsed.path or "/", parsed.query, ""))
    except ValueError as error:
        raise DiscoveryError(
            "INVALID_URL", "URL must be credential-free HTTPS"
        ) from error


def _work_identity(value: str) -> tuple[str, str, str | None]:
    canonical = _canonical_url(value)
    parsed = urlsplit(canonical)
    if (
        parsed.hostname in {"arxiv.org", "export.arxiv.org"}
        and parsed.port in (None, 443)
        and not parsed.query
    ):
        for prefix in ("/abs/", "/pdf/", "/html/"):
            if not parsed.path.startswith(prefix):
                continue
            identifier = parsed.path[len(prefix) :]
            if prefix == "/pdf/" and identifier.endswith(".pdf"):
                identifier = identifier[:-4]
            match = _ARXIV.fullmatch(identifier)
            if match:
                work = match["work"]
                return (
                    "arxiv:" + work,
                    "https://arxiv.org/abs/" + work,
                    match["version"],
                )
    return "url:" + sha256_bytes(canonical.encode())[7:], canonical, None


def _lead(record: Any, expected_source: str) -> Lead:
    if not isinstance(record, Mapping) or set(record) != {
        "identity",
        "source",
        "title",
        "url",
        "published_at",
        "summary",
        "metadata",
    }:
        raise DiscoveryError(
            "INVALID_LEAD", "lead fields do not match the typed contract"
        )
    metadata = _list(record["metadata"], 96)
    pairs = []
    for item in metadata:
        if len(_list(item, 2)) != 2:
            raise DiscoveryError("INVALID_LEAD", "metadata must contain string pairs")
        pairs.append((_text(item[0], 256), _text(item[1], 32_768, empty=True)))
    if sum(len((key + value).encode()) for key, value in pairs) > 32_768:
        raise DiscoveryError("INVALID_LEAD", "lead metadata exceeds its byte limit")
    try:
        lead = Lead(**{**record, "metadata": tuple(pairs)})
    except (TypeError, ValueError) as error:
        raise DiscoveryError(
            "INVALID_LEAD", "lead violates the typed contract"
        ) from error
    if lead.source != expected_source:
        raise DiscoveryError("INVALID_LEAD", "lead source does not match its adapter")
    _canonical_url(lead.url)
    return lead


def _captures(source: Mapping) -> list[dict]:
    result = []
    for capture in _list(source.get("captures"), 8):
        if (
            not isinstance(capture, Mapping)
            or set(capture)
            != {
                "body_sha256",
                "metadata_sha256",
                "size_bytes",
                "observation_only",
                "authoritative",
            }
            or capture["observation_only"] is not True
            or capture["authoritative"] is not False
            or type(capture["size_bytes"]) is not int
            or not 0 <= capture["size_bytes"] <= 1_500_000
        ):
            raise DiscoveryError(
                "INVALID_CAPTURE", "capture is not a bounded observation"
            )
        result.append(
            {
                "body_sha256": _digest(capture["body_sha256"]),
                "metadata_sha256": _digest(capture["metadata_sha256"]),
                "size_bytes": capture["size_bytes"],
            }
        )
    return result


def _packet_size(packet: dict) -> int:
    # packet_bytes includes its own integer encoding. Decimal width stabilizes.
    while True:
        size = len(canonicalize(packet))
        if packet["metrics"]["packet_bytes"] == size:
            return size
        packet["metrics"]["packet_bytes"] = size


def expand_discovery_provenance(packet: Mapping) -> list[dict]:
    """Resolve v2 references into a v1-shaped work index, without I/O or authority.

    This is a comparison/inspection view, not a newly budgeted packet. It does
    not revalidate captured bytes or the remaining packet fields.
    """
    if not isinstance(packet, Mapping) or packet.get("schema") not in (
        "local-research-discovery/v1",
        "local-research-discovery/v2",
    ):
        raise DiscoveryError("INVALID_PACKET", "unknown discovery packet format")
    try:
        index = copy.deepcopy(list(_list(packet["work_index"], 1440)))
        if packet["schema"] == "local-research-discovery/v1":
            return index
        if packet.get("occurrence_defaults") != {"capture_scope": _CAPTURE_SCOPE}:
            raise DiscoveryError("INVALID_REFERENCE", "unknown occurrence defaults")
        lanes = {}
        for lane in _list(packet["lanes"], MAX_LANES):
            lane_id = _text(lane["lane_id"], 128)
            if lane_id in lanes:
                raise DiscoveryError("INVALID_REFERENCE", "duplicate lane reference")
            lanes[lane_id] = lane
        seen = set()
        for work in index:
            expanded = []
            for occurrence in work["occurrences"]:
                if set(occurrence) != {
                    "occurrence_id",
                    "lane_id",
                    "source_index",
                    "lead_identity",
                    "original_url",
                    "version",
                }:
                    raise DiscoveryError(
                        "INVALID_REFERENCE", "invalid compact occurrence fields"
                    )
                lane_id = _text(occurrence["lane_id"], 128)
                lane = lanes[lane_id]
                source_index = occurrence["source_index"]
                if type(source_index) is not int or not 0 <= source_index < len(
                    lane["sources"]
                ):
                    raise DiscoveryError(
                        "INVALID_REFERENCE", "source reference is out of bounds"
                    )
                identifier = _text(occurrence["occurrence_id"], 128)
                if identifier in seen:
                    raise DiscoveryError(
                        "INVALID_REFERENCE", "duplicate occurrence reference"
                    )
                seen.add(identifier)
                source = lane["sources"][source_index]
                expanded.append(
                    {
                        "occurrence_id": identifier,
                        "lane_id": lane_id,
                        "facet": lane["facet"],
                        "query": lane["query"],
                        "effective_query": source["effective_query"],
                        "run_id": lane["run_id"],
                        "source": source["source"],
                        "adapter_source": source["adapter_source"],
                        "lead_identity": occurrence["lead_identity"],
                        "original_url": occurrence["original_url"],
                        "version": occurrence["version"],
                        "captures": copy.deepcopy(source["captures"]),
                        "capture_scope": _CAPTURE_SCOPE,
                    }
                )
            work["occurrences"] = expanded
        return index
    except (KeyError, TypeError, IndexError) as error:
        raise DiscoveryError(
            "INVALID_REFERENCE", "discovery provenance reference is invalid"
        ) from error


def build_discovery_packet(
    question: str,
    observations: Sequence[Mapping],
    max_bytes: int = 65_536,
    *,
    compact: bool = False,
) -> dict:
    """Build v1 by default; opt into v2 shared lane/source provenance references."""
    _text(question, 4096)
    if type(compact) is not bool:
        raise DiscoveryError("INVALID_COMPACT_MODE", "compact must be a boolean")
    if type(max_bytes) is not int or not 1 <= max_bytes <= MAX_PACKET_BYTES:
        raise DiscoveryError("INVALID_BUDGET", "packet budget must be 1..262144 bytes")
    observations = _list(observations, MAX_LANES)
    if not observations:
        raise DiscoveryError(
            "INVALID_SEQUENCE", "at least one observation lane is required"
        )
    try:
        input_bytes = canonicalize(list(observations))
    except (ContractError, RecursionError) as error:
        raise DiscoveryError(
            "INVALID_INPUT", "observations must use integer-only JSON"
        ) from error
    if len(input_bytes) > MAX_INPUT_BYTES:
        raise DiscoveryError(
            "INPUT_TOO_LARGE", "observation inputs exceed their byte limit"
        )
    lanes, work_index, contents, lane_work_ids, pending_links = [], {}, {}, [], []
    seen_lanes = set()
    raw_count = 0
    for lane in observations:
        if not isinstance(lane, Mapping) or set(lane) != {
            "lane_id",
            "facet",
            "query",
            "record",
        }:
            raise DiscoveryError(
                "INVALID_LANE", "lane fields do not match the packet contract"
            )
        lane_id = _text(lane["lane_id"], 128)
        if lane_id in seen_lanes:
            raise DiscoveryError("DUPLICATE_LANE", "lane identifiers must be distinct")
        seen_lanes.add(lane_id)
        facet, query = _text(lane["facet"], 512), _text(lane["query"], 2048, empty=True)
        record = lane["record"]
        if not isinstance(record, Mapping) or (
            record.get("schema") != "local-research-observation/v1"
            or record.get("authority") != "none"
            or record.get("production_ready") is not False
            or record.get("research_quality_measured") is not False
            or type(record.get("model_calls")) is not int
            or record["model_calls"] != 0
            or type(record.get("paid_calls")) is not int
            or record["paid_calls"] != 0
            or not isinstance(record.get("network_mode"), str)
            or record["network_mode"] not in {"live_public", "injected_fixture"}
            or not isinstance(record.get("status"), str)
            or record["status"] not in {"partial", "awaiting_researcher"}
        ):
            raise DiscoveryError(
                "INVALID_OBSERVATION",
                "pipeline observation identity or authority is invalid",
            )
        run_question = _text(record.get("query"), 2048)
        run_id = _text(record.get("run_id"), 128)
        manifest = _digest(record.get("manifest_digest"))
        lane_record = {
            "lane_id": lane_id,
            "facet": facet,
            "query": query,
            "run_question": run_question,
            "run_id": run_id,
            "manifest_digest": manifest,
            "observation_digest": sha256_bytes(canonicalize(dict(record))),
            "network_mode": record["network_mode"],
            "status": record["status"],
            "sources": [],
        }
        ids, seen_sources = [], set()
        for source_index, source in enumerate(
            _list(record.get("sources"), len(_SOURCE_MODES))
        ):
            if (
                not isinstance(source, Mapping)
                or not isinstance(source.get("source"), str)
                or source.get("source") not in _SOURCE_MODES
            ):
                raise DiscoveryError(
                    "INVALID_SOURCE", "source is not a registered observation mode"
                )
            source_name = source["source"]
            if source_name in seen_sources:
                raise DiscoveryError(
                    "INVALID_SOURCE", "source is repeated within a run"
                )
            seen_sources.add(source_name)
            expected_source, mode, query_applied, max_leads = _SOURCE_MODES[source_name]
            if query_applied and (
                not query.strip() or run_question != " ".join(query.split())
            ):
                raise DiscoveryError(
                    "INVALID_OBSERVATION",
                    "query-bearing source does not match its lane",
                )
            leads = _list(source.get("leads"), max_leads)
            status = source.get("status")
            captures = _captures(source)
            if (
                source.get("manifest_digest") != manifest
                or not isinstance(status, str)
                or status not in {"observed", "rate_limited", "failed"}
                or type(source.get("capture_complete")) is not bool
                or (status != "observed" and leads)
                or (
                    status == "observed"
                    and (not source["capture_complete"] or not captures)
                )
            ):
                raise DiscoveryError(
                    "INVALID_SOURCE", "source status or capture binding is inconsistent"
                )
            source_record = {
                "source": source_name,
                "adapter_source": expected_source,
                "mode": mode,
                "query_applied": query_applied,
                "status": status,
                "effective_query": run_question if query_applied else "",
                "lead_count": len(leads),
                "capture_complete": source["capture_complete"],
                "captures": captures,
            }
            if "error_code" in source:
                source_record["error_code"] = _text(source["error_code"], 128)
            if "retry_after_seconds" in source:
                delay = source["retry_after_seconds"]
                if type(delay) is not int or not 0 <= delay <= 86_400:
                    raise DiscoveryError("INVALID_SOURCE", "retry delay is invalid")
                source_record["retry_after_seconds"] = delay
            lane_record["sources"].append(source_record)
            seen_leads = set()
            for lead_index, value in enumerate(leads):
                lead = _lead(value, expected_source)
                if lead.identity in seen_leads:
                    raise DiscoveryError(
                        "INVALID_LEAD", "lead identity is repeated within a source"
                    )
                seen_leads.add(lead.identity)
                work_id, canonical_url, version = _work_identity(lead.url)
                occurrence = f"{len(lanes)}:{source_index}:{lead_index}"
                raw_count += 1
                if work_id not in work_index:
                    work_index[work_id] = {
                        "work_id": work_id,
                        "canonical_url": canonical_url,
                        "occurrences": [],
                    }
                    contents[work_id] = {"work_id": work_id, "observations": []}
                if work_id not in ids:
                    ids.append(work_id)
                if compact:
                    provenance = {
                        "occurrence_id": occurrence,
                        "lane_id": lane_id,
                        "source_index": source_index,
                        "lead_identity": lead.identity,
                        "original_url": lead.url,
                        "version": version,
                    }
                else:
                    provenance = {
                        "occurrence_id": occurrence,
                        "lane_id": lane_id,
                        "facet": facet,
                        "query": query,
                        "effective_query": run_question if query_applied else "",
                        "run_id": run_id,
                        "source": source_name,
                        "adapter_source": lead.source,
                        "lead_identity": lead.identity,
                        "original_url": lead.url,
                        "version": version,
                        "captures": captures,
                        "capture_scope": _CAPTURE_SCOPE,
                    }
                work_index[work_id]["occurrences"].append(provenance)
                contents[work_id]["observations"].append(
                    {
                        "occurrence_id": occurrence,
                        "title": lead.title,
                        "summary": lead.summary,
                        "published_at": lead.published_at,
                        "metadata": [list(pair) for pair in lead.metadata],
                        "summary_scope": "provider_supplied_text_not_verified_full_paper",
                    }
                )
                seen_links = set()
                for key, url in lead.metadata:
                    if not url.lower().startswith("https://"):
                        continue
                    link_url = _canonical_url(url)
                    if link_url in seen_links or link_url == _canonical_url(lead.url):
                        continue
                    seen_links.add(link_url)
                    pending_links.append(
                        {
                            "url": link_url,
                            "work_id": _work_identity(link_url)[0],
                            "from_work_id": work_id,
                            "occurrence_id": occurrence,
                            "metadata_field": key,
                            "status": "pending_unverified",
                            "intended_use": "candidate_primary_source_lookup",
                            "primary_source_confirmed": False,
                            "authority": "none",
                        }
                    )
        if not seen_sources:
            raise DiscoveryError(
                "INVALID_SOURCE", "observation needs at least one source outcome"
            )
        lanes.append(lane_record)
        lane_work_ids.append(ids)
    order = []
    seen = set()
    positions = [0] * len(lane_work_ids)
    while True:
        emitted = False
        for lane_number, ids in enumerate(lane_work_ids):
            while (
                positions[lane_number] < len(ids)
                and ids[positions[lane_number]] in seen
            ):
                positions[lane_number] += 1
            if positions[lane_number] < len(ids):
                work_id = ids[positions[lane_number]]
                positions[lane_number] += 1
                seen.add(work_id)
                order.append(work_id)
                emitted = True
        if not emitted:
            break
    packet = {
        "schema": "local-research-discovery/v2"
        if compact
        else "local-research-discovery/v1",
        "authority": "none",
        "production_ready": False,
        "content_role": "untrusted_discovery_data",
        "question": question,
        "max_bytes": max_bytes,
        "lanes": lanes,
        "selection_policy": "round_robin_lanes_whole_work_records_not_relevance_ranking",
        "work_index": list(work_index.values()),
        "selected_works": [],
        "omitted_works": [
            {"work_id": work_id, "reason": "budget"} for work_id in order
        ],
        "pending_primary_source_leads": pending_links,
        "accepted_claims": 0,
        "model_calls": 0,
        "paid_calls": 0,
        "semantic_relevance_measured": False,
        "independent_corroboration_measured": False,
        "provenance_verification": "caller_required_not_performed_by_pure_builder",
        "metrics": {
            "raw_leads": raw_count,
            "unique_works": len(work_index),
            "duplicate_occurrences": raw_count - len(work_index),
            "selected_works": 0,
            "omitted_works": len(work_index),
            "selected_occurrences": 0,
            "omitted_occurrences": raw_count,
            "packet_bytes": 0,
            "measurement_scope": "selection_coverage_budget_identity_only",
        },
    }
    if compact:
        packet["occurrence_defaults"] = {"capture_scope": _CAPTURE_SCOPE}
    if _packet_size(packet) > max_bytes:
        raise DiscoveryError(
            "BUDGET_INSUFFICIENT", "budget cannot hold the complete provenance index"
        )
    for work_id in order:
        candidate = contents[work_id]
        omission = {"work_id": work_id, "reason": "budget"}
        count = len(candidate["observations"])
        metrics = packet["metrics"]
        updates = {}
        delta = (
            len(canonicalize(candidate))
            + bool(packet["selected_works"])
            - len(canonicalize(omission))
            - (len(packet["omitted_works"]) > 1)
        )
        for key, increment in (
            ("selected_works", 1),
            ("omitted_works", -1),
            ("selected_occurrences", count),
            ("omitted_occurrences", -count),
        ):
            updates[key] = metrics[key] + increment
            delta += len(str(updates[key])) - len(str(metrics[key]))
        # Include packet_bytes' own decimal width without repeatedly encoding
        # the entire provenance index for every candidate and rejected attempt.
        base_size = metrics["packet_bytes"] + delta
        projected = base_size
        while True:
            actual = base_size + len(str(projected)) - len(str(metrics["packet_bytes"]))
            if actual == projected:
                break
            projected = actual
        if projected <= max_bytes:
            packet["selected_works"].append(candidate)
            packet["omitted_works"].remove(omission)
            metrics.update(updates, packet_bytes=projected)
    return packet
