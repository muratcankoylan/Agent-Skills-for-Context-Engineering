"""Opt-in larger HTML capture policy, reusing the byte-frozen v1 inert parser.

This changes wire capacity, not evidence authority or extraction depth. The
legacy reader remains unchanged so existing captures retain exact replay.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import time

from . import research_articles as base
from . import source_connectors as connectors
from .research_evidence import CapturedEvidence, LocalResearchEvidenceStore
from .schema_contract import canonicalize

PROFILE = "large-paper-html-v1"
SCHEMA = "local-research-article/v2"
ArticleError = base.ArticleError


@dataclass(frozen=True, slots=True)
class ArticleLimits:
    max_bytes: int = 1_500_000
    max_seconds: int = 15
    max_text_bytes: int = 100_000
    max_links: int = 200

    def __post_init__(self):
        for name, low, high in (("max_bytes", 1, 1_500_000),
                ("max_seconds", 1, 15), ("max_text_bytes", 1, 100_000), ("max_links", 0, 200)):
            if type(getattr(self, name)) is not int or not low <= getattr(self, name) <= high:
                raise ArticleError("ARTICLE_LIMIT_INVALID")


def policy_binding() -> dict:
    return {"profile": PROFILE, "limits": asdict(ArticleLimits()),
            "reader_sha256": base._digest(Path(__file__).read_bytes()),
            "base_reader_sha256": base._digest(Path(base.__file__).read_bytes())}


def _record(url, limits, capture, observation, body):
    result = base._record(url, limits, capture, observation, body)
    return {**result, "schema": SCHEMA, "read_profile": PROFILE,
            "base_reader_sha256": result["reader_sha256"],
            "reader_sha256": policy_binding()["reader_sha256"]}


def retrieve_article(url: str, store: LocalResearchEvidenceStore, *,
                     transport=None, resolver=connectors._system_resolver,
                     limits: ArticleLimits | None = None) -> dict:
    hostname = base._validate_url(url)
    selected = ArticleLimits() if limits is None else limits
    if type(selected) is not ArticleLimits or not isinstance(store, LocalResearchEvidenceStore):
        raise ArticleError("ARTICLE_INPUT_INVALID")
    budget = connectors._Budget.start(connectors.Limits(max_items=1, max_requests=1,
        max_pages=1, max_redirects=0, max_bytes=selected.max_bytes,
        max_seconds=selected.max_seconds), time.monotonic, connectors._default_now)
    captures = []

    def capture(observation, body):
        captures.append(store.capture(observation, body))

    client = connectors._SafeHTTPClient(transport=transport, resolver=resolver,
        clock=time.monotonic, now=connectors._default_now, capture_sink=capture)
    try:
        response = client.get(connector="primary-article-html-large-v1", url=url,
            allowed_hosts=frozenset({hostname}), headers=(("User-Agent", connectors.USER_AGENT),
                ("Accept", "text/html,application/xhtml+xml"), ("Accept-Encoding", "identity")),
            budget=budget)
        if isinstance(response, connectors._RateLimited):
            raise ArticleError("ARTICLE_RATE_LIMITED")
        if len(captures) != 1 or len(budget.observations) != 1:
            raise ArticleError("ARTICLE_CAPTURE_INVALID")
        result = _record(url, selected, captures[0], budget.observations[0], response.body)
        budget.after_transport()
        return result
    except Exception as error:
        code = error.code if isinstance(error, (ArticleError, connectors.ConnectorError)) else "ARTICLE_OBSERVATION_FAILED"
        raise ArticleError(code, tuple(item.as_record() for item in captures)) from None


def replay_article(store: LocalResearchEvidenceStore, record: dict) -> dict:
    """Offline exact comparison including both policy and base-parser digests."""
    try:
        if type(record) is not dict or not isinstance(store, LocalResearchEvidenceStore):
            raise ValueError()
        url = record["source_url"]
        base._validate_url(url)
        raw_limits = record["limits"]
        if type(raw_limits) is not dict or set(raw_limits) != set(asdict(ArticleLimits())):
            raise ValueError()
        limits = ArticleLimits(**raw_limits)
        capture = CapturedEvidence.from_record(record["capture"])
        observation, body = store.read(capture)
        expected = _record(url, limits, capture, observation, body)
        if canonicalize(record) != canonicalize(expected):
            raise ValueError()
        return expected
    except Exception:
        raise ArticleError("ARTICLE_REPLAY_INVALID") from None


def replay_article_failure(store: LocalResearchEvidenceStore, url: str,
                           error_code: str, captures: list[dict]) -> dict:
    """Reproduce captured rejection; never attest an uncaptured historic cause."""
    try:
        if (not isinstance(store, LocalResearchEvidenceStore) or type(captures) is not list
                or len(captures) > 1 or any(type(item) is not dict for item in captures)):
            raise ValueError()
        # The same parser and network policy govern smaller responses. Keep the
        # original failure replay for these bytes and for uncaptured outcomes.
        if not captures or CapturedEvidence.from_record(captures[0]).size_bytes <= 500_000:
            result = base.replay_article_failure(store, url, error_code, captures)
        else:
            base._validate_url(url)
            capture = CapturedEvidence.from_record(captures[0])
            observation, body = store.read(capture)
            length = connectors._content_length(observation.safe_headers)
            if (observation.request_url != url or observation.query_redacted
                    or len(body) > ArticleLimits().max_bytes or len(body) != capture.size_bytes
                    or observation.response_bytes != len(body)
                    or capture.body_sha256 != base._digest(body)
                    or observation.response_sha256 != capture.body_sha256
                    or observation.connected_ip != observation.resolved_ips[0]
                    or connectors._normalize_headers(observation.safe_headers) != observation.safe_headers
                    or connectors._media_type(observation.safe_headers) != observation.media_type
                    or length is not None and length != len(body) and not observation.truncated):
                raise ValueError()
            reproduced = False
            expected = None
            if error_code in {"TIME_LIMIT", "CAPTURE_FAILURE"}:
                basis = "capture_or_deadline_outcome_unverified"
            elif observation.truncated:
                expected = "TRUNCATED_RESPONSE"
            elif observation.status_code in connectors.REDIRECT_STATUSES:
                if error_code not in {"REDIRECT_LIMIT", "REDIRECT_INVALID"}:
                    raise ValueError()
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
                    raise ValueError()
            if expected is not None:
                if expected != error_code:
                    raise ValueError()
                reproduced, basis = True, "captured_response_rejection_reproduced"
            result = {"authority": "none", "source_url": url, "error_code": error_code,
                      "captures": [capture.as_record()], "failure_basis": basis,
                      "response_rejection_reproduced": reproduced, "historic_cause_verified": False,
                      "parser_policy": base.PARSER_POLICY}
        binding = policy_binding()
        return {**result, "schema": "local-research-article-failure-replay/v2",
                "read_profile": PROFILE, "reader_sha256": binding["reader_sha256"],
                "base_reader_sha256": binding["base_reader_sha256"]}
    except Exception:
        raise ArticleError("ARTICLE_FAILURE_REPLAY_INVALID") from None
