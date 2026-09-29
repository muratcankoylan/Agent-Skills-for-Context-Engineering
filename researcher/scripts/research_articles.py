#!/usr/bin/env python3
"""Bounded, inert HTML observations, never full-paper or research authority.

The caller selects a URL from verified discovery provenance. This module does
not verify that selection, follow extracted links, execute page code, or publish
anything. Network and private capture invariants belong to existing components.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from email.message import Message
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import time
from urllib.parse import urljoin, urlsplit

if __package__:
    from . import source_connectors as connectors
    from .research_evidence import CapturedEvidence, LocalResearchEvidenceStore
else:
    import source_connectors as connectors
    from research_evidence import CapturedEvidence, LocalResearchEvidenceStore


SCHEMA = "local-research-article/v1"
PARSER_POLICY = "single-article-else-single-main-inert-utf8/v2"
_HOST_PATHS = {
    "deepmind.google": "/blog/",
    "huggingface.co": "/blog/",
    "www.microsoft.com": "/en-us/research/",
}
_ARXIV_ID = re.compile(
    r"(?:[0-9]{2}(?:0[1-9]|1[0-2])\.[0-9]{4,5}"
    r"|[A-Za-z][A-Za-z0-9.-]*/[0-9]{2}(?:0[1-9]|1[0-2])[0-9]{3})"
    r"(?:v[1-9][0-9]{0,5})?\Z"
)
_IGNORED = frozenset(
    {
        "head",
        "script",
        "style",
        "nav",
        "header",
        "footer",
        "aside",
        "template",
        "noscript",
        "iframe",
        "object",
        "svg",
        "canvas",
        "form",
        "textarea",
    }
)
_VOID = frozenset(
    {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }
)
_BLOCK = frozenset(
    {
        "address",
        "article",
        "blockquote",
        "br",
        "dd",
        "div",
        "dl",
        "dt",
        "figcaption",
        "figure",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "hr",
        "li",
        "main",
        "ol",
        "p",
        "pre",
        "section",
        "table",
        "td",
        "th",
        "tr",
        "ul",
    }
)


class ArticleError(RuntimeError):
    """Failed observation; completed raw captures may still be inspected."""

    def __init__(self, code: str, captures: tuple[dict[str, object], ...] = ()):
        super().__init__("article observation failed validation")
        self.code = code
        self.captures = captures


@dataclass(frozen=True, slots=True)
class ArticleLimits:
    max_bytes: int = 500_000
    max_seconds: int = 15
    max_text_bytes: int = 100_000
    max_links: int = 200

    def __post_init__(self) -> None:
        for name, minimum, ceiling in (
            ("max_bytes", 1, 500_000),
            ("max_seconds", 1, 15),
            ("max_text_bytes", 1, 100_000),
            ("max_links", 0, 200),
        ):
            value = getattr(self, name)
            if type(value) is not int or not minimum <= value <= ceiling:
                raise ArticleError("ARTICLE_LIMIT_INVALID")


def _digest(body: bytes) -> str:
    return "sha256:" + hashlib.sha256(body).hexdigest()


def _validate_url(url: str) -> str:
    if (
        not isinstance(url, str)
        or not 1 <= len(url) <= 2_048
        or not url.startswith("https://")
        or not url.isascii()
        or any(ord(char) <= 32 or ord(char) == 127 for char in url)
    ):
        raise ArticleError("ARTICLE_URL_DENIED")
    try:
        parsed = urlsplit(url)
        if (
            parsed.scheme != "https"
            or parsed.netloc != parsed.hostname
            or parsed.query
            or parsed.fragment
            or "?" in url
            or "#" in url
            or "%" in parsed.path
            or "\\" in url
            or "//" in parsed.path
            or any(part in {".", ".."} for part in parsed.path.split("/"))
            or not re.fullmatch(r"/[A-Za-z0-9_./-]+", parsed.path)
        ):
            raise ArticleError("ARTICLE_URL_DENIED")
        if parsed.hostname == "arxiv.org":
            if not parsed.path.startswith("/html/") or not _ARXIV_ID.fullmatch(
                parsed.path[6:]
            ):
                raise ArticleError("ARTICLE_URL_DENIED")
        else:
            prefix = _HOST_PATHS.get(parsed.hostname or "")
            if (
                prefix is None
                or not parsed.path.startswith(prefix)
                or len(parsed.path) <= len(prefix)
            ):
                raise ArticleError("ARTICLE_URL_DENIED")
        return parsed.hostname
    except ValueError:
        raise ArticleError("ARTICLE_URL_DENIED") from None


def _require_utf8_charset(value: str) -> None:
    message = Message()
    message["content-type"] = value
    charsets = [
        item for key, item in message.get_params()[1:] if key.lower() == "charset"
    ]
    if any(
        not isinstance(item, str) or item.lower() not in {"utf-8", "utf8"}
        for item in charsets
    ):
        raise ArticleError("ARTICLE_ENCODING_UNSUPPORTED")


@dataclass
class _Boundary:
    tag: str
    ordinal: int
    parts: list[str] = field(default_factory=list)
    links: list[dict[str, object]] = field(default_factory=list)
    link_count: int = 0
    rejected_links: int = 0
    closed: bool = False


class _ArticleParser(HTMLParser):
    def __init__(self, url: str, limits: ArticleLimits):
        super().__init__(convert_charrefs=True)
        self.url = url
        self.limits = limits
        self.stack: list[tuple[str, bool, _Boundary | None]] = []
        self.boundaries: list[_Boundary] = []
        self.tags_seen = 0

    def _active(self) -> list[_Boundary]:
        return [boundary for _, _, boundary in self.stack if boundary is not None]

    def _suppressed(self) -> bool:
        return bool(self.stack and self.stack[-1][1])

    def _text(self, text: str) -> None:
        if not self._suppressed():
            for boundary in self._active():
                boundary.parts.append(text)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags_seen += 1
        if self.tags_seen > 50_000 or len(self.stack) >= 256:
            raise ArticleError("ARTICLE_STRUCTURE_LIMIT")
        # Ambiguity matters only for attributes this inert parser consumes.
        # Duplicate presentation attributes (arXiv emits duplicate title) cannot
        # change text/links here. Never choose first/last among consumed values.
        consumed = {"hidden", "aria-hidden"}
        if tag in {"a", "base"}:
            consumed.add("href")
        elif tag == "meta":
            consumed.update({"charset", "http-equiv", "content"})
        attributes: dict[str, str | None] = {}
        for name, value in attrs:
            if name in consumed:
                if name in attributes:
                    raise ArticleError("ARTICLE_ATTRIBUTES_AMBIGUOUS")
                attributes[name] = value
        if tag == "base" and attributes.get("href"):
            raise ArticleError("ARTICLE_BASE_UNSUPPORTED")
        if tag == "meta":
            if "charset" in attributes:
                _require_utf8_charset(
                    "text/html; charset=" + (attributes["charset"] or "")
                )
            if (attributes.get("http-equiv") or "").lower() == "content-type":
                _require_utf8_charset(attributes.get("content") or "")
        ignored = (
            self._suppressed()
            or tag in _IGNORED
            or "hidden" in attributes
            or (attributes.get("aria-hidden") or "").lower() == "true"
        )
        if not ignored and tag in _BLOCK:
            self._text("\n")
        boundary = None
        if tag in {"article", "main"} and not ignored:
            if len(self.boundaries) >= 8:
                raise ArticleError("ARTICLE_BOUNDARY_AMBIGUOUS")
            boundary = _Boundary(tag, len(self.boundaries))
            self.boundaries.append(boundary)
        if tag not in _VOID:
            self.stack.append((tag, ignored, boundary))
        if not ignored and tag == "a" and attributes.get("href") is not None:
            self._link(attributes["href"] or "")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in _VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                if tag in _BLOCK:
                    self._text("\n")
                # Only an explicit closing boundary proves its delimited extent.
                boundary = self.stack[index][2]
                if boundary is not None:
                    boundary.closed = True
                del self.stack[index:]
                return

    def handle_data(self, data: str) -> None:
        self._text(data)

    def _link(self, href: str) -> None:
        for boundary in self._active():
            boundary.link_count += 1
            try:
                resolved = urljoin(self.url, href)
                parsed = urlsplit(resolved)
                valid = (
                    bool(href)
                    and len(href.encode("utf-8")) <= 4_096
                    and len(resolved.encode("utf-8")) <= 4_096
                    and not any(ord(char) < 32 or ord(char) == 127 for char in href)
                    and parsed.scheme in {"https", "http"}
                    and bool(parsed.hostname)
                    and parsed.username is None
                    and parsed.password is None
                )
            except ValueError:
                valid = False
            if not valid:
                boundary.rejected_links += 1
            elif len(boundary.links) < self.limits.max_links:
                boundary.links.append(
                    {
                        "source_href": href,
                        "resolved_url": resolved,
                        "status": "pending_untrusted",
                        "retrieved": False,
                        "retrieval_authorized": False,
                    }
                )

    def selected(self) -> _Boundary:
        choices = [item for item in self.boundaries if item.tag == "article"]
        if not choices:
            choices = [item for item in self.boundaries if item.tag == "main"]
        if not choices:
            raise ArticleError("ARTICLE_BOUNDARY_MISSING")
        if len(choices) != 1:
            raise ArticleError("ARTICLE_BOUNDARY_AMBIGUOUS")
        if not choices[0].closed:
            raise ArticleError("ARTICLE_BOUNDARY_UNCLOSED")
        return choices[0]


def _record(
    url: str,
    limits: ArticleLimits,
    capture: CapturedEvidence,
    observation: connectors.ResponseObservation,
    body: bytes,
) -> dict[str, object]:
    if (
        observation.request_url != url
        or observation.query_redacted
        or observation.truncated
        or observation.status_code != 200
        or len(body) > limits.max_bytes
        or len(body) != capture.size_bytes
        or observation.response_bytes != len(body)
        or capture.body_sha256 != _digest(body)
        or observation.response_sha256 != capture.body_sha256
        or observation.media_type not in {"text/html", "application/xhtml+xml"}
    ):
        raise ArticleError("ARTICLE_RESPONSE_INVALID")
    content_types = [
        value for name, value in observation.safe_headers if name == "content-type"
    ]
    if len(content_types) != 1:
        raise ArticleError("ARTICLE_RESPONSE_INVALID")
    _require_utf8_charset(content_types[0])
    try:
        html = body.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        raise ArticleError("ARTICLE_ENCODING_UNSUPPORTED") from None
    if any(ord(char) < 32 and char not in "\t\r\n\f" for char in html):
        raise ArticleError("ARTICLE_ENCODING_UNSUPPORTED")
    parser = _ArticleParser(url, limits)
    parser.feed(html)
    parser.close()
    boundary = parser.selected()
    # Byte spans below refer to this whitespace-normalized extraction, NOT HTML.
    normalized = "\n".join(
        cleaned
        for line in "".join(boundary.parts).splitlines()
        if (cleaned := " ".join(line.split()))
    ).encode("utf-8")
    if not normalized:
        raise ArticleError("ARTICLE_TEXT_EMPTY")
    text = normalized[: limits.max_text_bytes].decode("utf-8", errors="ignore")
    retained = text.encode("utf-8")
    spans: list[dict[str, object]] = []
    start = 0
    while start < len(retained):
        chunk = (
            retained[start : start + 4_096]
            .decode("utf-8", errors="ignore")
            .encode("utf-8")
        )
        spans.append(
            {
                "start_byte": start,
                "end_byte": start + len(chunk),
                "sha256": _digest(chunk),
            }
        )
        start += len(chunk)
    return {
        "schema": SCHEMA,
        "authority": "none",
        "production_ready": False,
        "observation_only": True,
        "full_paper_verified": False,
        "source_url": url,
        "parser_policy": PARSER_POLICY,
        "reader_sha256": _digest(Path(__file__).read_bytes()),
        "limits": asdict(limits),
        "capture": capture.as_record(),
        "scope": boundary.tag + "_html",
        "boundary_ordinal": boundary.ordinal,
        "text": text,
        "text_bytes": len(retained),
        "text_sha256": _digest(retained),
        "available_text_bytes": len(normalized),
        "available_text_sha256": _digest(normalized),
        "omitted_text_bytes": len(normalized) - len(retained),
        "text_status": "byte_capped"
        if len(retained) < len(normalized)
        else "bounded_extraction",
        "span_basis": "normalized-extracted-text-utf8-bytes/v1",
        "spans": spans,
        "links": boundary.links,
        "link_count": boundary.link_count,
        "rejected_link_count": boundary.rejected_links,
        "omitted_link_count": boundary.link_count
        - boundary.rejected_links
        - len(boundary.links),
        "excluded_content_policy": sorted(_IGNORED),
    }


def retrieve_article(
    url: str,
    store: LocalResearchEvidenceStore,
    *,
    transport: connectors.Transport | None = None,
    resolver: connectors.Resolver = connectors._system_resolver,
    limits: ArticleLimits | None = None,
) -> dict[str, object]:
    hostname = _validate_url(url)
    selected_limits = ArticleLimits() if limits is None else limits
    if type(selected_limits) is not ArticleLimits or not isinstance(
        store, LocalResearchEvidenceStore
    ):
        raise ArticleError("ARTICLE_INPUT_INVALID")
    budget = connectors._Budget.start(
        connectors.Limits(
            max_items=1,
            max_requests=1,
            max_pages=1,
            max_redirects=0,
            max_bytes=selected_limits.max_bytes,
            max_seconds=selected_limits.max_seconds,
        ),
        time.monotonic,
        connectors._default_now,
    )
    captures: list[CapturedEvidence] = []

    def capture_response(
        observation: connectors.ResponseObservation, body: bytes
    ) -> None:
        captures.append(store.capture(observation, body))

    client = connectors._SafeHTTPClient(
        transport=transport,
        resolver=resolver,
        clock=time.monotonic,
        now=connectors._default_now,
        capture_sink=capture_response,
    )
    try:
        response = client.get(
            connector="primary-article-html",
            url=url,
            allowed_hosts=frozenset({hostname}),
            headers=(
                ("User-Agent", connectors.USER_AGENT),
                ("Accept", "text/html,application/xhtml+xml"),
                ("Accept-Encoding", "identity"),
            ),
            budget=budget,
        )
        if isinstance(response, connectors._RateLimited):
            raise ArticleError("ARTICLE_RATE_LIMITED")
        if len(captures) != 1 or len(budget.observations) != 1:
            raise ArticleError("ARTICLE_CAPTURE_INVALID")
        result = _record(
            url, selected_limits, captures[0], budget.observations[0], response.body
        )
        budget.after_transport()
        return result
    except Exception as error:
        code = (
            error.code
            if isinstance(error, (ArticleError, connectors.ConnectorError))
            else "ARTICLE_OBSERVATION_FAILED"
        )
        raise ArticleError(code, tuple(item.as_record() for item in captures)) from None


def replay_article(
    store: LocalResearchEvidenceStore, record: dict[str, object]
) -> dict[str, object]:
    """Reparse the bound capture offline; any changed field fails closed."""
    try:
        if type(record) is not dict or not isinstance(
            store, LocalResearchEvidenceStore
        ):
            raise ArticleError("ARTICLE_REPLAY_INVALID")
        url = record["source_url"]
        _validate_url(url)
        raw_limits = record["limits"]
        if type(raw_limits) is not dict or set(raw_limits) != set(
            asdict(ArticleLimits())
        ):
            raise ArticleError("ARTICLE_REPLAY_INVALID")
        limits = ArticleLimits(**raw_limits)
        capture = CapturedEvidence.from_record(record["capture"])
        observation, body = store.read(capture)
        expected = _record(url, limits, capture, observation, body)

        def canonical(value: object) -> str:
            return json.dumps(
                value,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )

        if canonical(record) != canonical(expected):
            raise ArticleError("ARTICLE_REPLAY_MISMATCH")
        return expected
    except Exception:
        raise ArticleError("ARTICLE_REPLAY_INVALID") from None


def reextract_article(
    store: LocalResearchEvidenceStore,
    url: str,
    capture_record: dict[str, object],
    *,
    limits: ArticleLimits | None = None,
) -> dict[str, object]:
    """Apply the current parser to an existing exact capture, with no HTTP.

    Unlike replay_article this does not attest that an older parser produced the
    same extraction. The caller preserves the old result and binds a separate
    new extraction to its selection, original capture and current reader hash.
    """
    try:
        _validate_url(url)
        selected_limits = ArticleLimits() if limits is None else limits
        if (
            not isinstance(store, LocalResearchEvidenceStore)
            or type(capture_record) is not dict
            or type(selected_limits) is not ArticleLimits
        ):
            raise ArticleError("ARTICLE_REEXTRACTION_INVALID")
        capture = CapturedEvidence.from_record(capture_record)
        observation, body = store.read(capture)
        return _record(url, selected_limits, capture, observation, body)
    except ArticleError:
        raise
    except Exception:
        raise ArticleError("ARTICLE_REEXTRACTION_INVALID") from None


def replay_article_failure(
    store: LocalResearchEvidenceStore,
    url: str,
    error_code: str,
    captures: list[dict[str, object]],
) -> dict[str, object]:
    """Validate a default-policy failed read without network or derived evidence.

    A reproduced rejection means these bytes fail the current reader policy,
    not that a historical transport/clock event has been independently proved.
    Location is intentionally absent from capture metadata, so redirects cannot
    reproduce the distinction between missing Location and the zero-follow cap.
    """
    uncaptured_codes = {
        "TIME_LIMIT",
        "DNS_CAPACITY",
        "DNS_FAILURE",
        "DNS_INVALID",
        "DNS_NOT_PUBLIC",
        "DNS_EMPTY",
        "TRANSPORT_FAILURE",
        "BYTE_LIMIT",
        "CONTENT_ENCODING_UNSUPPORTED",
        "CONTENT_LENGTH_INVALID",
        "HEADER_INVALID",
        "CAPTURE_CAPACITY",
        "CAPTURE_FAILURE",
        "ARTICLE_OBSERVATION_FAILED",
    }
    try:
        if (
            not isinstance(store, LocalResearchEvidenceStore)
            or type(url) is not str
            or not 1 <= len(url.encode("utf-8")) <= 2_048
            or any(ord(char) < 32 or ord(char) == 127 for char in url)
            or type(error_code) is not str
            or not re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", error_code)
            or type(captures) is not list
            or len(captures) > 1
            or any(type(item) is not dict for item in captures)
        ):
            raise ArticleError("ARTICLE_FAILURE_REPLAY_INVALID")
        denied = False
        try:
            _validate_url(url)
        except ArticleError:
            denied = True
        reproduced = False
        verified_captures: list[dict[str, object]] = []
        if denied:
            if error_code != "ARTICLE_URL_DENIED" or captures:
                raise ArticleError("ARTICLE_FAILURE_REPLAY_INVALID")
            basis = "local_url_policy_rejection_reproduced"
        elif not captures:
            if error_code not in uncaptured_codes:
                raise ArticleError("ARTICLE_FAILURE_REPLAY_INVALID")
            basis = "uncaptured_failure_cause_unverified"
        else:
            capture = CapturedEvidence.from_record(captures[0])
            observation, body = store.read(capture)
            headers = observation.safe_headers
            content_length = connectors._content_length(headers)
            if (
                observation.request_url != url
                or observation.query_redacted
                or len(body) > ArticleLimits().max_bytes
                or len(body) != capture.size_bytes
                or observation.response_bytes != len(body)
                or capture.body_sha256 != _digest(body)
                or observation.response_sha256 != capture.body_sha256
                or observation.connected_ip != observation.resolved_ips[0]
                or connectors._normalize_headers(headers) != headers
                or connectors._media_type(headers) != observation.media_type
                or (
                    content_length is not None
                    and content_length != len(body)
                    and not observation.truncated
                )
            ):
                raise ArticleError("ARTICLE_FAILURE_REPLAY_INVALID")
            verified_captures = [capture.as_record()]
            if error_code in {"TIME_LIMIT", "CAPTURE_FAILURE"}:
                # A completed raw capture may be an orphan after its caller's
                # deadline. Its existence neither disproves that failure nor
                # authorizes publishing successfully parsed derived text.
                basis = "capture_or_deadline_outcome_unverified"
            else:
                expected = None
                if observation.truncated:
                    expected = "TRUNCATED_RESPONSE"
                elif observation.status_code in connectors.REDIRECT_STATUSES:
                    if error_code not in {"REDIRECT_LIMIT", "REDIRECT_INVALID"}:
                        raise ArticleError("ARTICLE_FAILURE_REPLAY_INVALID")
                    basis = "captured_redirect_header_unavailable"
                elif observation.status_code == 429:
                    expected = "ARTICLE_RATE_LIMITED"
                elif not 200 <= observation.status_code < 300:
                    expected = "HTTP_STATUS"
                else:
                    try:
                        _record(url, ArticleLimits(), capture, observation, body)
                    except ArticleError as error:
                        expected = error.code
                    if expected is None:
                        raise ArticleError("ARTICLE_FAILURE_REPLAY_INVALID")
                if expected is not None:
                    if error_code != expected:
                        raise ArticleError("ARTICLE_FAILURE_REPLAY_INVALID")
                    reproduced = True
                    basis = "captured_response_rejection_reproduced"
        return {
            "schema": "local-research-article-failure-replay/v1",
            "authority": "none",
            "source_url": url,
            "error_code": error_code,
            "captures": verified_captures,
            "failure_basis": basis,
            "response_rejection_reproduced": reproduced,
            "historic_cause_verified": False,
            "parser_policy": PARSER_POLICY,
            "reader_sha256": _digest(Path(__file__).read_bytes()),
        }
    except Exception:
        raise ArticleError("ARTICLE_FAILURE_REPLAY_INVALID") from None


__all__ = [
    "ArticleError",
    "ArticleLimits",
    "retrieve_article",
    "replay_article",
    "reextract_article",
    "replay_article_failure",
]
