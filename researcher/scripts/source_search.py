"""One-page dated discovery. No relevance judgment, full-text or sync guarantee.

Algolia searches HN stories, not their external article bodies. OpenAlex searches
works by publication date (day precision), not created/updated change feeds.
Credentials are supplied explicitly and never appear in observation URLs.
"""

from __future__ import annotations

from datetime import UTC, datetime
import json
import re
import time
from urllib.parse import quote, urlencode

if __package__:
    from . import source_connectors as c
else:
    import source_connectors as c


def window(start_time: int, end_time: int) -> tuple[int, int]:
    if (type(start_time) is not int or type(end_time) is not int
            or not 0 <= start_time < end_time <= 253402300799
            or end_time - start_time > 31 * 86400):
        raise ValueError("window must be increasing UTC seconds, at most 31 days")
    return start_time, end_time


def credential_value(value: str | None) -> str | None:
    if value is not None and (not isinstance(value, str) or not 8 <= len(value) <= 4096
                              or not value.isascii() or any(ord(ch) <= 32 or ord(ch) == 127 for ch in value)):
        raise ValueError("credential must be an explicitly supplied bounded ASCII token")
    return value


class CredentialGuardedTransport:
    """Reject reflected credentials before any response bytes reach capture."""

    def __init__(self, transport, credential: str):
        self.transport = transport
        self._credential = credential

    def request(self, request):
        try:
            response = self.transport.request(request)
        except c.ConnectorError:
            raise c.ConnectorError("CREDENTIAL_TRANSPORT_FAILURE", "authenticated transport failed") from None
        except Exception:
            raise c.ConnectorError("CREDENTIAL_TRANSPORT_FAILURE", "authenticated transport failed") from None
        token = self._credential
        raw = response.body
        if any(not isinstance(name, str) or not isinstance(value, str) for name, value in response.headers):
            raise c.MalformedResponseError("HEADER_INVALID", "response header is invalid")
        reflected = token.encode() in raw or quote(token, safe="").encode() in raw
        reflected = reflected or any(token in name or token in value for name, value in response.headers)
        # JSON escapes can hide the token from a byte substring check. Parse only
        # for this pre-capture guard; normal strict source parsing still follows.
        try:
            decoded = json.loads(raw, object_pairs_hook=lambda pairs: [part for pair in pairs for part in pair])
        except (ValueError, UnicodeError):
            decoded = None
        except RecursionError:
            raise c.MalformedResponseError("JSON_DEPTH", "response nesting is excessive") from None
        pending = [decoded]
        while pending:
            item = pending.pop()
            if isinstance(item, str):
                reflected = reflected or token in item
            elif isinstance(item, dict):
                pending.extend(item.keys())
                pending.extend(item.values())
            elif isinstance(item, list):
                pending.extend(item)
        if reflected:
            raise c.PolicyError("CREDENTIAL_REFLECTED", "response reflected a credential; capture refused")
        return response


def _integer(value, minimum=0, maximum=2**53 - 1):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError("invalid integer")
    return value


def _text(value, maximum, *, empty=False):
    if not isinstance(value, str) or (not value.strip() and not empty) or len(value.encode("utf-8")) > maximum:
        raise ValueError("invalid bounded text")
    return value


def _url(value):
    _text(value, 8192)
    if not value.startswith("https://") or "\\" in value or any(ord(ch) <= 32 for ch in value):
        raise ValueError("invalid absolute HTTPS URL")
    return c._canonical_url(value, base_url="https://invalid.example/")


class _Search(c._NetworkAdapter):
    def __init__(self, *, start_time, end_time, transport=None,
                 resolver=c._system_resolver, clock=time.monotonic, now=c._default_now,
                 capture_sink=None):
        self.start_time, self.end_time = window(start_time, end_time)
        super().__init__(transport=transport, resolver=resolver, clock=clock, now=now,
                         capture_sink=capture_sink)

    def _request(self, query, limits, parameters, headers=()):
        budget = self._budget(limits)
        if not limits.permits_observation:
            return budget, c._empty_page(self.connector, query, budget)
        if query.cursor is not None:
            raise c.ConnectorError("CURSOR_UNSUPPORTED", "this adapter observes one explicit page only")
        if not query.text.strip():
            raise c.ConnectorError("QUERY_REQUIRED", "search requires an explicit provider query")
        if limits.max_items > 100:
            raise c.ConnectorError("ITEM_LIMIT_INCOMPATIBLE", "search page exceeds provider bound")
        response = self._client.get(connector=self.connector,
            url=self._URL + "?" + urlencode(parameters), allowed_hosts=self._HOSTS,
            headers=(("Accept", "application/json"), ("Accept-Encoding", "identity"),
                     ("User-Agent", c.USER_AGENT), *headers), budget=budget)
        if isinstance(response, c._RateLimited):
            return budget, c._rate_limit_result(self.connector, response, budget)
        return budget, c._parse_json(self.connector, response, budget)


class HackerNewsSearchAdapter(_Search):
    connector = "hacker_news"
    _URL = "https://hn.algolia.com/api/v1/search_by_date"
    _HOSTS = frozenset({"hn.algolia.com"})

    def discover(self, query: c.QuerySpec, limits: c.Limits):
        budget, payload = self._request(query, limits, {
            "query": query.text, "tags": "story", "page": 0,
            "hitsPerPage": min(limits.max_items, 100),
            "numericFilters": f"created_at_i>={self.start_time},created_at_i<{self.end_time}",
        })
        if isinstance(payload, (c.LeadPage, c.RetryAfter)):
            return payload
        try:
            if not isinstance(payload, dict) or not isinstance(payload.get("hits"), list):
                raise ValueError("missing hits")
            hits = payload["hits"]
            count = _integer(payload.get("nbHits"))
            pages = _integer(payload.get("nbPages"))
            if _integer(payload.get("page")) != 0 or len(hits) > limits.max_items or count < len(hits):
                raise ValueError("invalid page")
            if (count == 0 and (hits or pages > 1)) or (count > 0 and (not hits or pages == 0)):
                raise ValueError("contradictory page counts")
            leads, seen = [], set()
            for item in hits:
                if not isinstance(item, dict):
                    raise ValueError("invalid story")
                identity = _text(item.get("objectID"), 32)
                if not re.fullmatch(r"[0-9]{1,32}", identity) or identity in seen:
                    raise ValueError("invalid duplicate identity")
                seen.add(identity)
                created = _integer(item.get("created_at_i"))
                if not self.start_time <= created < self.end_time:
                    raise ValueError("story outside requested window")
                title = _text(item.get("title"), 8192)
                discussion = "https://news.ycombinator.com/item?id=" + identity
                raw_url = item.get("url")
                if raw_url is not None and not isinstance(raw_url, str):
                    raise ValueError("invalid article URL")
                original = raw_url if isinstance(raw_url, str) else ""
                url = _url(raw_url) if original.startswith("https://") else discussion
                summary = item.get("story_text") or ""
                summary = _text(summary, 65536, empty=True)
                metadata = [("discussion_url", discussion), ("summary_kind", "hn_story_html" if summary else "none"),
                            ("summary_truncated", str(len(summary) > 16384).lower()),
                            ("retrieval_mode", "algolia_story_search_by_date")]
                if original:
                    metadata.append(("external_url", _text(original, 8192)))
                if item.get("author") is not None:
                    metadata.append(("author", _text(item["author"], 256)))
                for name in ("points", "num_comments"):
                    if item.get(name) is not None:
                        metadata.append((name, str(_integer(item[name], maximum=1_000_000_000))))
                leads.append(c.Lead(identity="hacker_news:item:" + identity, source=self.connector,
                    title=title, url=url, published_at=datetime.fromtimestamp(created, UTC).isoformat(),
                    summary=summary[:16384], metadata=c._bounded_metadata(metadata)))
            more = pages > 1 or count > len(leads)
            return c.LeadPage(tuple(leads), "unfetched_page:1" if more else None,
                              budget.receipt(self.connector, len(leads)))
        except (ValueError, TypeError, KeyError, UnicodeError, OverflowError):
            raise c.MalformedResponseError("HN_SEARCH_SCHEMA_INVALID", "HN search response violates its bounded contract",
                                            budget.receipt(self.connector, 0)) from None


def reconstruct_abstract(index) -> str:
    """Strict position-preserving OpenAlex abstract reconstruction, not full text."""
    if index is None:
        return ""
    if not isinstance(index, dict) or len(index) > 8192:
        raise ValueError("invalid abstract index")
    positions = {}
    for token, offsets in index.items():
        _text(token, 2048)
        if not isinstance(offsets, list) or not 1 <= len(offsets) <= 8192:
            raise ValueError("invalid abstract positions")
        for offset in offsets:
            _integer(offset, maximum=8191)
            if offset in positions:
                raise ValueError("duplicate abstract position")
            positions[offset] = token
    if not positions:
        return ""
    if set(positions) != set(range(len(positions))):
        raise ValueError("gapped abstract index")
    text = " ".join(positions[i] for i in range(len(positions)))
    return _text(text, 65536)


class OpenAlexWorksAdapter(_Search):
    connector = "openalex"
    _URL = "https://api.openalex.org/works"
    _HOSTS = frozenset({"api.openalex.org"})
    _FIELDS = "id,doi,title,publication_date,abstract_inverted_index,primary_location,open_access,ids"

    def __init__(self, *, credential=None, **kwargs):
        self._credential = credential_value(credential)
        super().__init__(**kwargs)
        if self._credential:
            self._client._transport = CredentialGuardedTransport(self._client._transport, self._credential)

    def discover(self, query: c.QuerySpec, limits: c.Limits):
        if self._credential is None:
            raise c.ConnectorDisabledError("CONNECTOR_DISABLED", "OpenAlex requires an explicitly supplied API key")
        start = datetime.fromtimestamp(self.start_time, UTC).date().isoformat()
        end = datetime.fromtimestamp(self.end_time - 1, UTC).date().isoformat()
        budget, payload = self._request(query, limits, {
            "search": query.text, "filter": f"from_publication_date:{start},to_publication_date:{end}",
            "select": self._FIELDS, "per-page": min(limits.max_items, 100), "page": 1,
        }, (("Authorization", "Bearer " + self._credential),))
        if isinstance(payload, (c.LeadPage, c.RetryAfter)):
            return payload
        try:
            if not isinstance(payload, dict) or not isinstance(payload.get("results"), list) or not isinstance(payload.get("meta"), dict):
                raise ValueError("missing works")
            values, meta = payload["results"], payload["meta"]
            count = _integer(meta.get("count"))
            if len(values) > limits.max_items or count < len(values):
                raise ValueError("invalid page")
            if count > 0 and not values:
                raise ValueError("contradictory work count")
            leads, seen = [], set()
            for item in values:
                if not isinstance(item, dict):
                    raise ValueError("invalid work")
                work_url = _text(item.get("id"), 128)
                if not re.fullmatch(r"https://openalex.org/W[0-9]{1,24}", work_url) or work_url in seen:
                    raise ValueError("invalid duplicate work identity")
                seen.add(work_url)
                publication = _text(item.get("publication_date"), 10)
                if datetime.strptime(publication, "%Y-%m-%d").date().isoformat() != publication or not start <= publication <= end:
                    raise ValueError("work outside publication dates")
                title = _text(item.get("title"), 8192)
                abstract = reconstruct_abstract(item.get("abstract_inverted_index"))
                metadata = [("work_id", work_url), ("summary_kind", "openalex_abstract" if abstract else "none"),
                            ("summary_truncated", str(len(abstract) > 16384).lower()),
                            ("publication_date", publication), ("retrieval_mode", "publication_date_search_not_change_feed")]
                doi = item.get("doi")
                if doi:
                    metadata.append(("doi_url", _url(doi)))
                ids = item.get("ids") or {}
                if not isinstance(ids, dict):
                    raise ValueError("invalid identifiers")
                for key in ("doi", "pmid", "pmcid"):
                    if ids.get(key):
                        metadata.append((key + "_url", _url(ids[key])))
                location = item.get("primary_location") or {}
                if not isinstance(location, dict):
                    raise ValueError("invalid location")
                article = location.get("landing_page_url")
                # Source HTTP locations remain untrusted metadata, not fetch authority.
                for key in ("landing_page_url", "pdf_url"):
                    if location.get(key):
                        metadata.append((key, _text(location[key], 8192)))
                url = _url(article) if isinstance(article, str) and article.startswith("https://") else work_url
                leads.append(c.Lead(identity="openalex:" + work_url.rsplit("/", 1)[-1], source=self.connector,
                    title=title, url=url, published_at=publication, summary=abstract[:16384],
                    metadata=c._bounded_metadata(metadata)))
            return c.LeadPage(tuple(leads), "unfetched_page:2" if count > len(leads) else None,
                              budget.receipt(self.connector, len(leads)))
        except (ValueError, TypeError, KeyError, UnicodeError, OverflowError):
            raise c.MalformedResponseError("OPENALEX_SCHEMA_INVALID", "OpenAlex response violates its bounded contract",
                                            budget.receipt(self.connector, 0)) from None
