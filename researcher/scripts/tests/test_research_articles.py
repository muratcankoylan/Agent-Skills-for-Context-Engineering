from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from researcher.scripts import research_articles as articles
from researcher.scripts.research_articles import (
    ArticleError,
    ArticleLimits,
    replay_article,
    replay_article_failure,
    reextract_article,
    retrieve_article,
)
from researcher.scripts.research_evidence import LocalResearchEvidenceStore
from researcher.scripts.source_connectors import TransportRequest, TransportResponse


URL = "https://arxiv.org/html/2609.00001v2"


class FakeTransport:
    def __init__(
        self,
        body: bytes,
        *,
        status: int = 200,
        media: str = "text/html; charset=utf-8",
        headers: tuple[tuple[str, str], ...] = (),
        truncated: bool = False,
    ):
        self.response = TransportResponse(
            status, (("Content-Type", media), *headers), body, truncated
        )
        self.requests: list[TransportRequest] = []

    def request(self, request: TransportRequest) -> TransportResponse:
        self.requests.append(request)
        return self.response


def public_resolver(host: str, port: int) -> tuple[str, ...]:
    return ("93.184.216.34",)


class ResearchArticleTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.store = LocalResearchEvidenceStore(
            Path(temporary.name).resolve() / "captures"
        )

    def retrieve(
        self,
        body: bytes,
        *,
        url: str = URL,
        limits: ArticleLimits | None = None,
        **options: object,
    ) -> tuple[dict[str, object], FakeTransport]:
        transport = FakeTransport(body, **options)
        result = retrieve_article(
            url,
            self.store,
            transport=transport,
            resolver=public_resolver,
            limits=limits,
        )
        return result, transport

    def test_arxiv_version_is_preserved_with_exact_private_capture_and_offline_replay(
        self,
    ) -> None:
        body = b"<!doctype html><html><head><title>Page chrome</title></head><body><main><article><h1>Research</h1><p>Context <em>engineering</em> &amp; memory.</p></article></main></body></html>"
        record, transport = self.retrieve(body)
        self.assertEqual(record["source_url"], URL)
        self.assertEqual(record["scope"], "article_html")
        self.assertEqual(record["boundary_ordinal"], 1)
        self.assertEqual(record["text"], "Research\nContext engineering & memory.")
        self.assertEqual(record["authority"], "none")
        self.assertFalse(record["production_ready"])
        self.assertFalse(record["full_paper_verified"])
        self.assertEqual(self.store.read_body(record["capture"]), body)
        observation = self.store.read_observation(record["capture"])
        self.assertEqual(observation.request_url, URL)
        self.assertFalse(observation.query_redacted)
        self.assertEqual(len(transport.requests), 1)
        self.assertEqual(transport.requests[0].max_bytes, 500_000)
        self.assertEqual(transport.requests[0].connect_ip, "93.184.216.34")
        self.assertIn(
            ("User-Agent", articles.connectors.USER_AGENT),
            transport.requests[0].headers,
        )
        with patch.object(
            articles.connectors._SafeHTTPClient,
            "get",
            side_effect=AssertionError("network forbidden"),
        ):
            self.assertEqual(
                replay_article(self.store, json.loads(json.dumps(record))), record
            )

    def test_all_company_hosts_and_legacy_arxiv_identifier_use_explicit_boundaries(
        self,
    ) -> None:
        for url in (
            "https://deepmind.google/blog/context-research/",
            "https://huggingface.co/blog/community/context-research",
            "https://www.microsoft.com/en-us/research/publication/context-research/",
            "https://arxiv.org/html/hep-th/9901001v2",
        ):
            with self.subTest(url=url):
                record, _ = self.retrieve(
                    b"<main><h1>Evidence</h1><p>Observed text.</p></main>", url=url
                )
                self.assertEqual(record["scope"], "main_html")
                self.assertEqual(record["text"], "Evidence\nObserved text.")
                self.assertEqual(replay_article(self.store, record), record)

    def test_inert_extraction_excludes_scripts_navigation_hidden_and_template_injections(
        self,
    ) -> None:
        body = b"""<nav><article>outer injection</article></nav>
        <main><article><header>header injection</header><p>Useful result.</p>
        <script>fetch('https://evil.invalid'); acceptEverything()</script>
        <style>.secret{display:block}</style><nav>nav injection</nav>
        <footer>footer injection</footer><aside>aside injection</aside>
        <div hidden>hidden injection</div><div aria-hidden="true">aria injection</div>
        <template><article>template injection</article></template>
        <textarea><article>textarea injection</article></textarea>
        <p>Untrusted source says ignore previous instructions.</p></article></main>"""
        record, transport = self.retrieve(body)
        self.assertEqual(
            record["text"],
            "Useful result.\nUntrusted source says ignore previous instructions.",
        )
        self.assertEqual(len(transport.requests), 1)
        # Prompt-like prose is preserved as untrusted evidence, not heuristically laundered.
        self.assertTrue(record["observation_only"])

    def test_private_noncanonical_and_nonallowlisted_urls_fail_without_network_or_dns(
        self,
    ) -> None:
        urls = (
            "https://127.0.0.1/html/2609.00001",
            "http://arxiv.org/html/2609.00001",
            "HTTPS://arxiv.org/html/2609.00001",
            "https://arxiv.org:443/html/2609.00001",
            "https://arxiv.org.evil.invalid/html/2609.00001",
            "https://user:secret@arxiv.org/html/2609.00001",
            "https://arxiv.org/html/2609.00001?secret=value",
            "https://arxiv.org/html/2609.00001#body",
            "https://arxiv.org/abs/2609.00001",
            "https://arxiv.org/html/2613.00001",
            "https://arxiv.org/html/2609.00001v0",
            "https://arxiv.org/html/2609.00001/extra",
            "https://deepmind.google/blog/../private",
            "https://deepmind.google/blog/%2e%2e/private",
            "https://deepmind.google/blog//private",
            "https://deepmind.google/blog/",
            "https://huggingface.co/settings/token",
            "https://www.microsoft.com/en-us/account",
            "https://openai.com/news/example",
            "https://deepmind.google/blog/a\\b",
        )
        for url in urls:
            with self.subTest(url=url):
                transport = FakeTransport(b"<article>Never read.</article>")
                with patch.object(
                    articles.connectors,
                    "_resolve_public_ips",
                    side_effect=AssertionError("DNS forbidden"),
                ):
                    with self.assertRaises(ArticleError) as error:
                        retrieve_article(url, self.store, transport=transport)
                self.assertEqual(error.exception.code, "ARTICLE_URL_DENIED")
                self.assertEqual(error.exception.captures, ())
                self.assertEqual(transport.requests, [])

    def test_allowed_host_resolving_to_private_or_mixed_ips_is_denied(self) -> None:
        for addresses in (("127.0.0.1",), ("93.184.216.34", "10.0.0.1")):
            transport = FakeTransport(b"<article>Never read.</article>")
            with self.assertRaises(ArticleError) as error:
                retrieve_article(
                    URL, self.store, transport=transport, resolver=lambda *_: addresses
                )
            self.assertEqual(error.exception.code, "DNS_NOT_PUBLIC")
            self.assertEqual(transport.requests, [])

    def test_invalid_encoding_declared_charset_and_media_are_captured_but_not_accepted(
        self,
    ) -> None:
        for body, media in (
            (b"<article>bad\xff</article>", "text/html"),
            (b"<article>bad\0</article>", "text/html"),
            (b"<article>bad\x1b</article>", "text/html"),
            (b"<article>Text.</article>", "text/html; charset=iso-8859-1"),
            (b'<meta charset="windows-1252"><article>Text.</article>', "text/html"),
            (b"<article>Text.</article>", "application/pdf"),
            (b"<article>Text.</article>", "application/json"),
        ):
            with self.subTest(media=media, body=body):
                transport = FakeTransport(body, media=media)
                with self.assertRaises(ArticleError) as error:
                    retrieve_article(
                        URL, self.store, transport=transport, resolver=public_resolver
                    )
                self.assertEqual(len(transport.requests), 1)
                self.assertEqual(len(error.exception.captures), 1)
                self.assertEqual(
                    self.store.read_body(error.exception.captures[0]), body
                )

    def test_missing_ambiguous_unclosed_and_empty_article_boundaries_fail(self) -> None:
        cases = (
            (b"<div>body without article boundary</div>", "ARTICLE_BOUNDARY_MISSING"),
            (
                b"<article>one</article><article>two</article>",
                "ARTICLE_BOUNDARY_AMBIGUOUS",
            ),
            (b"<main>one</main><main>two</main>", "ARTICLE_BOUNDARY_AMBIGUOUS"),
            (b"<article>not closed", "ARTICLE_BOUNDARY_UNCLOSED"),
            (
                b"<main><article>not explicitly closed</main>",
                "ARTICLE_BOUNDARY_UNCLOSED",
            ),
            (b"<article><script>inert</script></article>", "ARTICLE_TEXT_EMPTY"),
            (
                b'<base href="https://evil.invalid/"><article>Text</article>',
                "ARTICLE_BASE_UNSUPPORTED",
            ),
            (
                b'<article><a href="a" href="b">Text</a></article>',
                "ARTICLE_ATTRIBUTES_AMBIGUOUS",
            ),
        )
        for body, code in cases:
            with self.subTest(code=code):
                with self.assertRaises(ArticleError) as error:
                    self.retrieve(body)
                self.assertEqual(error.exception.code, code)
                self.assertEqual(len(error.exception.captures), 1)

    def test_duplicate_unused_presentation_attributes_do_not_reject_evidence(
        self,
    ) -> None:
        # Captured arXiv HTML 2502.06975v1 line110 has these exact title values.
        body = b"""<html><body><nav><a href="/html/2502.06975v1"
            title="Report an Issue" title="Report an issue">Report</a></nav>
            <main><article class="one" class="two" id="a" id="b">
            <p style="color:red" style="color:blue" data-extra="one" data-extra="two">Evidence.</p>
            <a href="/html/2609.00002v1" title="One" title="Two">Source</a>
            </article></main></body></html>"""
        record, transport = self.retrieve(body)
        self.assertEqual(record["text"], "Evidence.\nSource")
        self.assertEqual(len(record["links"]), 1)
        self.assertEqual(
            record["links"][0]["resolved_url"], "https://arxiv.org/html/2609.00002v1"
        )
        self.assertFalse(record["links"][0]["retrieval_authorized"])
        self.assertEqual(len(transport.requests), 1)
        self.assertEqual(replay_article(self.store, record), record)

    def test_duplicate_extraction_attributes_still_fail_including_case_variants(
        self,
    ) -> None:
        for body in (
            b'<article><a href="https://example.org/a" HREF="https://example.org/b">Source</a></article>',
            b'<base href="https://example.org/" href="https://evil.invalid/"><article>Text</article>',
            b'<article hidden="" hidden="false">Text</article>',
            b'<article aria-hidden="true" aria-hidden="false">Text</article>',
            b'<meta charset="utf-8" charset="latin-1"><article>Text</article>',
            b'<meta http-equiv="content-type" http-equiv="refresh" content="text/html"><article>Text</article>',
            b'<meta http-equiv="content-type" content="text/html;charset=utf-8" content="text/html;charset=latin-1"><article>Text</article>',
            b'<article><a href="/same" href="/same">Identical duplicates remain rejected</a></article>',
        ):
            with self.subTest(body=body), self.assertRaises(ArticleError) as error:
                self.retrieve(body)
            self.assertEqual(error.exception.code, "ARTICLE_ATTRIBUTES_AMBIGUOUS")

    def test_redirects_are_captured_and_never_followed_even_within_allowlist(
        self,
    ) -> None:
        for target in (
            "/html/2609.00002",
            "http://127.0.0.1/private",
            "https://evil.invalid/article",
        ):
            transport = FakeTransport(
                b"Redirect body", status=302, headers=(("Location", target),)
            )
            with self.assertRaises(ArticleError) as error:
                retrieve_article(
                    URL, self.store, transport=transport, resolver=public_resolver
                )
            self.assertEqual(error.exception.code, "REDIRECT_LIMIT")
            self.assertEqual(len(transport.requests), 1)
            self.assertEqual(len(error.exception.captures), 1)

    def test_oversized_and_truncated_responses_never_become_text(self) -> None:
        transport = FakeTransport(b"x" * 500_001)
        with self.assertRaises(ArticleError) as error:
            retrieve_article(
                URL, self.store, transport=transport, resolver=public_resolver
            )
        self.assertEqual(error.exception.code, "BYTE_LIMIT")
        self.assertEqual(error.exception.captures, ())
        for headers, truncated in ((("Content-Length", "999"),), False), ((), True):
            transport = FakeTransport(
                b"<article>partial</article>", headers=headers, truncated=truncated
            )
            with self.assertRaises(ArticleError) as error:
                retrieve_article(
                    URL, self.store, transport=transport, resolver=public_resolver
                )
            self.assertEqual(error.exception.code, "TRUNCATED_RESPONSE")
            self.assertTrue(
                self.store.read_observation(error.exception.captures[0]).truncated
            )

    def test_http_failure_and_rate_limit_preserve_captures_without_retries(
        self,
    ) -> None:
        for status, code in (
            (403, "HTTP_STATUS"),
            (500, "HTTP_STATUS"),
            (429, "ARTICLE_RATE_LIMITED"),
            (206, "ARTICLE_RESPONSE_INVALID"),
        ):
            transport = FakeTransport(
                b"<article>Unaccepted error body</article>", status=status
            )
            with self.assertRaises(ArticleError) as error:
                retrieve_article(
                    URL, self.store, transport=transport, resolver=public_resolver
                )
            self.assertEqual(error.exception.code, code)
            self.assertEqual(len(transport.requests), 1)
            self.assertEqual(len(error.exception.captures), 1)

    def test_duplicate_content_type_and_compression_fail_closed(self) -> None:
        for headers, code, capture_count in (
            ((("Content-Type", "application/pdf"),), "ARTICLE_RESPONSE_INVALID", 1),
            ((("Content-Encoding", "gzip"),), "CONTENT_ENCODING_UNSUPPORTED", 0),
        ):
            transport = FakeTransport(b"<article>Evidence</article>", headers=headers)
            with self.assertRaises(ArticleError) as error:
                retrieve_article(
                    URL, self.store, transport=transport, resolver=public_resolver
                )
            self.assertEqual(error.exception.code, code)
            self.assertEqual(len(error.exception.captures), capture_count)
            self.assertEqual(len(transport.requests), 1)

    def test_expired_transport_deadline_never_publishes_success(self) -> None:
        transport = FakeTransport(b"<article>Late evidence</article>")
        with patch.object(
            articles.time,
            "monotonic",
            side_effect=lambda: 16.0 if transport.requests else 0.0,
        ):
            with self.assertRaises(ArticleError) as error:
                retrieve_article(
                    URL, self.store, transport=transport, resolver=public_resolver
                )
        self.assertEqual(error.exception.code, "TIME_LIMIT")
        self.assertEqual(len(transport.requests), 1)
        self.assertEqual(error.exception.captures, ())

    def test_utf8_byte_caps_and_spans_are_exact_not_full_paper_claims(self) -> None:
        original = "é" * 5_000
        record, _ = self.retrieve(
            ("<article>" + original + "</article>").encode(),
            limits=ArticleLimits(max_text_bytes=8_193),
        )
        text_bytes = record["text"].encode("utf-8")
        self.assertEqual(len(text_bytes), 8_192)
        self.assertEqual(record["available_text_bytes"], 10_000)
        self.assertEqual(record["omitted_text_bytes"], 1_808)
        self.assertEqual(record["text_status"], "byte_capped")
        self.assertEqual(
            record["span_basis"], "normalized-extracted-text-utf8-bytes/v1"
        )
        cursor = 0
        for span in record["spans"]:
            self.assertEqual(span["start_byte"], cursor)
            chunk = text_bytes[span["start_byte"] : span["end_byte"]]
            self.assertEqual(
                span["sha256"], "sha256:" + hashlib.sha256(chunk).hexdigest()
            )
            cursor = span["end_byte"]
        self.assertEqual(cursor, len(text_bytes))
        self.assertFalse(record["full_paper_verified"])
        self.assertEqual(replay_article(self.store, record), record)

    def test_links_are_inert_bounded_and_explicitly_unretrieved(self) -> None:
        body = b'<article>Research<a href="/html/2609.00002v1">paper</a><a href="https://example.org/paper?id=1&amp;x=2">source</a><a href="javascript:alert(1)">unsafe</a><a href="https://user:secret@example.org/">credentials</a><a href="/html/2609.00003">omitted</a></article>'
        record, transport = self.retrieve(body, limits=ArticleLimits(max_links=2))
        self.assertEqual(record["link_count"], 5)
        self.assertEqual(record["rejected_link_count"], 2)
        self.assertEqual(record["omitted_link_count"], 1)
        self.assertEqual(len(record["links"]), 2)
        self.assertEqual(
            record["links"][1]["resolved_url"], "https://example.org/paper?id=1&x=2"
        )
        self.assertTrue(
            all(
                link["status"] == "pending_untrusted" and link["retrieved"] is False
                for link in record["links"]
            )
        )
        self.assertEqual(len(transport.requests), 1)

    def test_limits_can_only_reduce_fixed_network_and_extraction_ceilings(self) -> None:
        for change in (
            {"max_bytes": 500_001},
            {"max_seconds": 16},
            {"max_text_bytes": 100_001},
            {"max_links": 201},
            {"max_bytes": True},
            {"max_seconds": 0.5},
            {"max_bytes": 0},
            {"max_links": -1},
        ):
            with self.subTest(change=change), self.assertRaises(ArticleError):
                ArticleLimits(**change)
        transport = FakeTransport(b"<article>Text</article>")
        with self.assertRaises(ArticleError):
            retrieve_article(
                URL,
                self.store,
                transport=transport,
                resolver=public_resolver,
                limits={"max_bytes": 1},
            )
        self.assertEqual(transport.requests, [])

    def test_replay_rejects_each_tampered_derived_or_authority_field(self) -> None:
        record, _ = self.retrieve(
            b'<article>Evidence <a href="/html/2609.00002">link</a></article>'
        )
        for changes in (
            {"text": "Forged evidence"},
            {"source_url": "https://arxiv.org/html/2609.00002"},
            {"authority": "accepted"},
            {"full_paper_verified": True},
            {"observation_only": 1},
            {"reader_sha256": "sha256:" + "0" * 64},
            {"parser_policy": "different"},
            {"text_sha256": "sha256:" + "0" * 64},
            {"spans": []},
            {"links": []},
            {"scope": "main_html"},
            {"omitted_text_bytes": 20},
            {"unknown": "field"},
            {"limits": as_limits(record) | {"max_requests": 2}},
        ):
            with self.subTest(changes=list(changes)), self.assertRaises(ArticleError):
                replay_article(self.store, deepcopy(record) | changes)

    def test_replay_binds_to_exact_stored_request_and_body_integrity(self) -> None:
        record, _ = self.retrieve(b"<article>Evidence</article><!--one-->")
        observation, body = self.store.read(record["capture"])
        other = self.store.capture(
            replace(observation, request_url="https://arxiv.org/html/2609.00002"), body
        )
        forged = deepcopy(record)
        forged["capture"] = other.as_record()
        with self.assertRaises(ArticleError):
            replay_article(self.store, forged)
        # Corruption outside the selected text must fail too, even at equal size.
        body_path = self.store.root / "bodies" / record["capture"]["body_sha256"][7:]
        body_path.write_bytes(b"<article>Evidence</article><!--two-->")
        with self.assertRaises(ArticleError):
            replay_article(self.store, record)

    def test_structure_depth_is_bounded_and_cancellation_propagates(self) -> None:
        with self.assertRaises(ArticleError) as error:
            self.retrieve(
                b"<article>" + b"<div>" * 257 + b"x" + b"</div>" * 257 + b"</article>"
            )
        self.assertEqual(error.exception.code, "ARTICLE_STRUCTURE_LIMIT")
        transport = FakeTransport(b"")
        with patch.object(transport, "request", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                retrieve_article(
                    URL, self.store, transport=transport, resolver=public_resolver
                )

    def test_failed_response_and_parser_rejections_are_reproduced_offline(self) -> None:
        for body, options in (
            (b"<article>bad\xff</article>", {}),
            (b"<article>Text</article>", {"media": "application/pdf"}),
            (b"<div>No boundary</div>", {}),
            (b"<article>one</article><article>two</article>", {}),
            (b"<article>unclosed", {}),
            (b"<article><script>inert</script></article>", {}),
            (b"<article>Not accepted</article>", {"status": 206}),
            (b"error", {"status": 403}),
            (b"error", {"status": 503}),
            (b"rate limit", {"status": 429}),
            (b"partial", {"truncated": True}),
        ):
            with self.subTest(body=body, options=options):
                with self.assertRaises(ArticleError) as error:
                    self.retrieve(body, **options)
                code, captures = error.exception.code, list(error.exception.captures)
                with patch.object(
                    articles.connectors._SafeHTTPClient,
                    "get",
                    side_effect=AssertionError("network forbidden"),
                ):
                    assessment = replay_article_failure(self.store, URL, code, captures)
                self.assertTrue(assessment["response_rejection_reproduced"])
                self.assertFalse(assessment["historic_cause_verified"])
                self.assertEqual(assessment["captures"], captures)
                self.assertNotIn("text", assessment)
                with self.assertRaises(ArticleError):
                    replay_article_failure(self.store, URL, "DNS_FAILURE", captures)

    def test_failed_redirect_replay_reports_missing_location_evidence(self) -> None:
        for headers, code in (
            (
                (("Location", "https://evil.invalid/path?private=value"),),
                "REDIRECT_LIMIT",
            ),
            ((), "REDIRECT_INVALID"),
        ):
            with self.assertRaises(ArticleError) as error:
                self.retrieve(b"redirect", status=302, headers=headers)
            self.assertEqual(error.exception.code, code)
            captures = list(error.exception.captures)
            assessment = replay_article_failure(self.store, URL, code, captures)
            self.assertEqual(
                assessment["failure_basis"], "captured_redirect_header_unavailable"
            )
            self.assertFalse(assessment["response_rejection_reproduced"])
            self.assertNotIn("private=value", json.dumps(assessment))
            with self.assertRaises(ArticleError):
                replay_article_failure(self.store, URL, "HTTP_STATUS", captures)

    def test_successful_capture_cannot_be_relabelled_as_parser_or_transport_failure(
        self,
    ) -> None:
        record, _ = self.retrieve(b"<article>Valid evidence.</article>")
        captures = [record["capture"]]
        for code in (
            "ARTICLE_BOUNDARY_MISSING",
            "ARTICLE_RESPONSE_INVALID",
            "HTTP_STATUS",
            "REDIRECT_LIMIT",
            "ARTICLE_RATE_LIMITED",
            "TRANSPORT_FAILURE",
            "DNS_FAILURE",
            "ARTICLE_OBSERVATION_FAILED",
        ):
            with self.subTest(code=code), self.assertRaises(ArticleError):
                replay_article_failure(self.store, URL, code, captures)
        for code in ("TIME_LIMIT", "CAPTURE_FAILURE"):
            assessment = replay_article_failure(self.store, URL, code, captures)
            self.assertEqual(
                assessment["failure_basis"], "capture_or_deadline_outcome_unverified"
            )
            self.assertFalse(assessment["response_rejection_reproduced"])
            self.assertFalse(assessment["historic_cause_verified"])
            self.assertNotIn("text", assessment)

    def test_uncaptured_failures_have_closed_codes_and_unverified_historical_cause(
        self,
    ) -> None:
        for code in (
            "TIME_LIMIT",
            "TRANSPORT_FAILURE",
            "DNS_CAPACITY",
            "DNS_FAILURE",
            "DNS_INVALID",
            "DNS_NOT_PUBLIC",
            "DNS_EMPTY",
            "BYTE_LIMIT",
            "CONTENT_ENCODING_UNSUPPORTED",
            "CONTENT_LENGTH_INVALID",
            "HEADER_INVALID",
            "CAPTURE_CAPACITY",
            "CAPTURE_FAILURE",
            "ARTICLE_OBSERVATION_FAILED",
        ):
            assessment = replay_article_failure(self.store, URL, code, [])
            self.assertEqual(
                assessment["failure_basis"], "uncaptured_failure_cause_unverified"
            )
            self.assertFalse(assessment["response_rejection_reproduced"])
            self.assertFalse(assessment["historic_cause_verified"])
        for code in (
            "HTTP_STATUS",
            "ARTICLE_BOUNDARY_MISSING",
            "TRUNCATED_RESPONSE",
            "REDIRECT_LIMIT",
            "ARTICLE_RATE_LIMITED",
            "ARTICLE_URL_DENIED",
            "SUCCESS",
            "FORGED",
            "x\nHTTP_STATUS",
            True,
            None,
        ):
            with self.subTest(code=code), self.assertRaises(ArticleError):
                replay_article_failure(self.store, URL, code, [])

    def test_url_policy_failure_is_reproduced_without_dns(self) -> None:
        for url in ("https://127.0.0.1/private", "https://example.org/article"):
            with patch.object(
                articles.connectors,
                "_resolve_public_ips",
                side_effect=AssertionError("DNS forbidden"),
            ):
                assessment = replay_article_failure(
                    self.store, url, "ARTICLE_URL_DENIED", []
                )
            self.assertEqual(
                assessment["failure_basis"], "local_url_policy_rejection_reproduced"
            )
            with self.assertRaises(ArticleError):
                replay_article_failure(self.store, url, "DNS_FAILURE", [])

    def test_failed_replay_rejects_capture_shape_url_and_body_tampering(self) -> None:
        with self.assertRaises(ArticleError) as error:
            self.retrieve(b"<div>Missing boundary</div>")
        captures = list(error.exception.captures)
        for value in (
            None,
            {},
            (),
            captures * 2,
            [captures[0] | {"unknown": True}],
            [captures[0] | {"authoritative": True}],
        ):
            with self.subTest(value=value), self.assertRaises(ArticleError):
                replay_article_failure(
                    self.store, URL, "ARTICLE_BOUNDARY_MISSING", value
                )
        observation, body = self.store.read(captures[0])
        variants = (
            replace(observation, request_url="https://arxiv.org/html/2609.00002"),
            replace(observation, query_redacted=True),
            replace(observation, media_type="application/pdf"),
            replace(
                observation,
                safe_headers=(*observation.safe_headers, ("content-length", "999")),
            ),
        )
        for changed in variants:
            forged = self.store.capture(changed, body).as_record()
            with self.assertRaises(ArticleError):
                replay_article_failure(
                    self.store, URL, "ARTICLE_BOUNDARY_MISSING", [forged]
                )
        body_path = self.store.root / "bodies" / captures[0]["body_sha256"][7:]
        body_path.write_bytes(b"corrupt")
        with self.assertRaises(ArticleError) as rejected:
            replay_article_failure(
                self.store, URL, "ARTICLE_BOUNDARY_MISSING", captures
            )
        self.assertEqual(rejected.exception.code, "ARTICLE_FAILURE_REPLAY_INVALID")

    def test_reextraction_uses_existing_capture_current_policy_and_no_network(
        self,
    ) -> None:
        record, _ = self.retrieve(
            b'<article title="First" title="Second">Existing captured evidence.</article>'
        )
        old_result = deepcopy(record)
        old_result["reader_sha256"] = "sha256:" + "0" * 64
        old_result["parser_policy"] = "single-article-else-single-main-inert-utf8/v1"
        old_bytes = json.dumps(old_result, sort_keys=True)
        with (
            patch.object(
                articles.connectors._SafeHTTPClient,
                "get",
                side_effect=AssertionError("HTTP forbidden"),
            ),
            patch.object(
                articles.connectors,
                "_resolve_public_ips",
                side_effect=AssertionError("DNS forbidden"),
            ),
        ):
            with self.assertRaises(ArticleError):
                replay_article(self.store, old_result)
            extracted = reextract_article(self.store, URL, old_result["capture"])
            self.assertEqual(extracted, record)
            capped = reextract_article(
                self.store,
                URL,
                old_result["capture"],
                limits=ArticleLimits(max_text_bytes=8),
            )
        self.assertEqual(extracted["parser_policy"], articles.PARSER_POLICY)
        self.assertEqual(extracted["text"], "Existing captured evidence.")
        self.assertEqual(capped["text_status"], "byte_capped")
        self.assertFalse(capped["full_paper_verified"])
        self.assertEqual(json.dumps(old_result, sort_keys=True), old_bytes)

    def test_reextraction_rejects_wrong_url_capture_corruption_and_unsafe_limits(
        self,
    ) -> None:
        record, _ = self.retrieve(b"<article>Existing evidence.</article>")
        for url, capture, limits in (
            ("https://arxiv.org/html/2609.00002v1", record["capture"], None),
            ("https://127.0.0.1/private", record["capture"], None),
            (URL, record["capture"] | {"unknown": "value"}, None),
            (URL, record["capture"] | {"authoritative": True}, None),
            (URL, record["capture"], {"max_bytes": 500_001}),
        ):
            with self.subTest(url=url, limits=limits), self.assertRaises(ArticleError):
                reextract_article(self.store, url, capture, limits=limits)
        body_path = self.store.root / "bodies" / record["capture"]["body_sha256"][7:]
        body_path.write_bytes(b"corrupt")
        with self.assertRaises(ArticleError):
            reextract_article(self.store, URL, record["capture"])


def as_limits(record: dict[str, object]) -> dict[str, object]:
    return dict(record["limits"])


if __name__ == "__main__":
    unittest.main()
