"""Daily source boundary: explicit configuration, capture, and offline replay.

No source is a quality endorsement. One observed page is not exhaustive daily
coverage, and feed/recent-arXiv windows do not apply the requested time filter.
"""

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from urllib.parse import urlsplit

from researcher.scripts.research_evidence import LocalResearchEvidenceStore
from researcher.scripts.schema_contract import sha256_bytes
from researcher.scripts.source_connectors import (
    ArxivAtomAdapter, ConnectorDisabledError, Limits, QuerySpec, RetryAfter, RSSAtomAdapter,
    XRecentSearchAdapter, replay_discovery,
)
from researcher.scripts.source_search import (
    HackerNewsSearchAdapter, OpenAlexWorksAdapter, credential_value, window,
)
from .contracts import ServiceError
from .tracing import annotate, instrument


FEEDS = {
    "deepmind": "https://deepmind.google/blog/rss.xml",
    "huggingface": "https://huggingface.co/blog/feed.xml",
    "microsoft_research": "https://www.microsoft.com/en-us/research/feed/",
}
SOURCES = ("arxiv", "deepmind", "huggingface", "microsoft_research", "hacker_news", "x", "openalex")


def source_limits(name: str) -> Limits:
    if name not in SOURCES:
        raise ServiceError("UNREGISTERED_SOURCE")
    return Limits(max_items=6 if name in FEEDS else 10, max_requests=1,
                  max_pages=1, max_bytes=500_000, max_seconds=30, max_redirects=0)


def _plain(value):
    return json.loads(json.dumps(value, allow_nan=False))


def _adapter(name, start_time, end_time, credential=None, **kwargs):
    window(start_time, end_time)
    if name == "arxiv":
        return ArxivAtomAdapter(search_scope="title_abstract", sort_by="submittedDate",
                                include_provenance=True, **kwargs)
    if name in FEEDS:
        return RSSAtomAdapter(FEEDS[name], allowed_hosts=(urlsplit(FEEDS[name]).hostname,),
                              include_provenance=True, **kwargs)
    if name == "hacker_news":
        return HackerNewsSearchAdapter(start_time=start_time, end_time=end_time, **kwargs)
    if name == "openalex":
        return OpenAlexWorksAdapter(start_time=start_time, end_time=end_time,
                                   credential=credential, **kwargs)
    if name == "x":
        return XRecentSearchAdapter(environ={} if credential is None else {"X_BEARER_TOKEN": credential},
                                    start_time=start_time, end_time=end_time,
                                    include_provenance=True, include_context=True, **kwargs)
    raise ServiceError("UNREGISTERED_SOURCE")


def _query(name, query):
    return QuerySpec("" if name in FEEDS else query)


def _normalized(name, query, result, start_time, end_time):
    rate_limited = isinstance(result, RetryAfter)
    evidence = []
    if not rate_limited:
        for item in result.items:
            text = item.title + "\n\n" + item.summary
            metadata = list(item.metadata)
            if item.published_at is not None:
                metadata.append(("observed_publication_time", item.published_at))
            evidence.append({"id": item.identity, "source": name, "url": item.url,
                             "text": text, "sha256": sha256_bytes(text.encode("utf-8")),
                             "evidence_scope": "discovery_summary", "metadata": _plain(metadata)})
    cursor = None if rate_limited else result.next_cursor
    filtered = name in {"hacker_news", "x", "openalex"}
    mode = {"hacker_news": "algolia_story_search_by_date", "x": "x_recent_search",
            "openalex": "publication_date_search_not_change_feed",
            "arxiv": "submitted_date_sorted_search_not_time_filtered"}.get(name, "company_feed_window_not_query_search")
    output = {"source": name, "state": "rate_limited" if rate_limited else "observed",
              "evidence": evidence, "next_cursor": cursor,
              "coverage": {"schema": "retrieval-coverage/v1", "window_start": start_time,
                           "window_end": end_time, "window_applied": filtered,
                           "window_resolution": "day" if name == "openalex" else "second" if filtered else "not_applied",
                           "query_sha256": sha256_bytes(_query(name, query).text.encode("utf-8")),
                           "mode": mode, "page_limit": 1, "returned_count": len(evidence),
                           "continuation_available": cursor is not None,
                           "partial": rate_limited or cursor is not None or not filtered,
                           "completeness": "bounded_page_not_exhaustive", "quality_assessed": False}}
    if rate_limited:
        output["retry_after_seconds"] = result.retry_after_seconds
    return output


@instrument("source.retrieve")
def collect(name: str, query: str, directory: Path, *, start_time: int,
            end_time: int, credential: str | None = None) -> dict:
    """Observe at most one provider page; no pagination, retries, or ambient keys."""
    limits = source_limits(name)
    annotate(provider=name, transport="https")
    window(start_time, end_time)
    credential_value(credential)
    if name in {"x", "openalex"} and credential is None:
        raise ConnectorDisabledError("CONNECTOR_DISABLED", "source requires an explicitly supplied credential")
    query_spec = _query(name, query)
    # Validate adapter configuration before initializing private storage.
    adapter = _adapter(name, start_time, end_time, credential)
    captures = []
    store = LocalResearchEvidenceStore(directory)
    def capture(observation, body):
        value = store.capture(observation, body)
        captures.append(value.as_record())
        return value
    adapter._client._capture_sink = capture
    result = adapter.discover(query_spec, limits)
    annotate(source_requests=result.receipt.request_count, output_bytes=result.receipt.total_bytes,
             items=result.receipt.item_count, outcome="completed")
    return {**_normalized(name, query, result, start_time, end_time), "captures": captures,
            "receipt": _plain(asdict(result.receipt))}


@instrument("source.verify")
def verify(name: str, query: str, lane: dict, directory: Path, *, start_time: int,
           end_time: int) -> None:
    """Read-only replay, using a fixed non-secret placeholder for request shape."""
    limits = source_limits(name)
    window(start_time, end_time)
    store = LocalResearchEvidenceStore(directory, read_only=True)
    if not isinstance(lane, dict) or not isinstance(lane.get("captures"), list) or len(lane["captures"]) != 1:
        raise ServiceError("SOURCE_CAPTURE_INVALID")
    captures = [(store.read_observation(row), store.read_body(row)) for row in lane["captures"]]
    result = replay_discovery(
        lambda **kwargs: _adapter(name, start_time, end_time,
                                  "offline-replay-not-a-credential" if name in {"x", "openalex"} else None,
                                  **kwargs),
        captures, _query(name, query), limits)
    expected = _normalized(name, query, result, start_time, end_time)
    if {key: value for key, value in lane.items() if key not in {"captures", "receipt"}} != expected:
        raise ServiceError("SOURCE_REPLAY_MISMATCH")
    receipt = lane.get("receipt")
    replayed = _plain(asdict(result.receipt))
    if not isinstance(receipt, dict) or receipt.keys() != replayed.keys():
        raise ServiceError("SOURCE_RECEIPT_MISMATCH")
    for key in ("connector", "request_count", "total_bytes", "item_count", "observation_only", "authoritative"):
        if type(receipt[key]) is not type(replayed[key]) or receipt[key] != replayed[key]:
            raise ServiceError("SOURCE_RECEIPT_MISMATCH")
    if receipt["observations"] != [_plain(asdict(observation)) for observation, _ in captures]:
        raise ServiceError("SOURCE_RECEIPT_MISMATCH")
