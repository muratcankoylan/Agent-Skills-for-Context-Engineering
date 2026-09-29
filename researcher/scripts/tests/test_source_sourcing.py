"""Offline contracts for opt-in source content/provenance enrichment."""

from __future__ import annotations

import base64
import json
import socket
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from researcher.scripts import source_connectors as sources
from researcher.scripts.source_connectors import (
    ArxivAtomAdapter,
    ConnectorError,
    LeadPage,
    Limits,
    MalformedResponseError,
    PinnedHTTPSTransport,
    QuerySpec,
    RSSAtomAdapter,
    XRecentSearchAdapter,
    replay_discovery,
)
from researcher.scripts.tests.test_source_connectors import (
    ScriptedTransport,
    atom_entry,
    atom_feed,
    resolver_for,
    response,
)


def paper(identifier: str = "2609.12345v2", extra: str = "") -> bytes:
    return atom_feed(
        '<entry xmlns:arxiv="http://arxiv.org/schemas/atom">'
        f"<id>http://arxiv.org/abs/{identifier}</id><title>Research paper</title>"
        "<updated>2026-09-07T00:00:00Z</updated>"
        "<published>2026-08-01T00:00:00Z</published>"
        f'<link href="https://arxiv.org/abs/{identifier}" rel="alternate"/>'
        f'<link href="http://arxiv.org/pdf/{identifier}" type="application/pdf"/>'
        "<summary>A bounded research mechanism.</summary>"
        "<author><name>Research Author</name></author>"
        '<category term="cs.AI"/><category term="cs.CL"/>'
        '<arxiv:primary_category term="cs.AI"/>'
        "<arxiv:doi>10.1234/research.42</arxiv:doi>"
        f"{extra}</entry>"
    )


class SourcingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.enterContext(
            patch.object(
                socket, "getaddrinfo", side_effect=AssertionError("network forbidden")
            )
        )
        self.enterContext(
            patch.object(
                PinnedHTTPSTransport,
                "request",
                side_effect=AssertionError("network forbidden"),
            )
        )

    def arxiv(self, body: bytes | None = None, **options):
        transport = ScriptedTransport(response(body or paper(), "application/atom+xml"))
        adapter = ArxivAtomAdapter(
            transport=transport, resolver=resolver_for("export.arxiv.org"), **options
        )
        return adapter, transport

    def feed(self, body: bytes, **options):
        transport = ScriptedTransport(response(body, "application/atom+xml"))
        adapter = RSSAtomAdapter(
            "https://feeds.example/feed.atom",
            allowed_hosts={"feeds.example"},
            transport=transport,
            resolver=resolver_for("feeds.example"),
            **options,
        )
        return adapter, transport

    def x(self, item: dict[str, object], **options):
        body = json.dumps({"data": [item], "meta": {"result_count": 1}}).encode()
        transport = ScriptedTransport(response(body, "application/json"))
        adapter = XRecentSearchAdapter(
            environ={"X_BEARER_TOKEN": "offline-fixture-not-a-credential"},
            transport=transport,
            resolver=resolver_for("api.x.com"),
            **options,
        )
        return adapter, transport

    def test_sort_is_explicit_and_legacy_default_is_unchanged(self) -> None:
        for sort in ("relevance", "submittedDate", "lastUpdatedDate"):
            with self.subTest(sort=sort):
                adapter, transport = self.arxiv(sort_by=sort)
                adapter.discover(QuerySpec("context engineering"), Limits())
                params = parse_qs(urlsplit(transport.requests[0].url).query)
                self.assertEqual(params["sortBy"], [sort])
                self.assertEqual(params["sortOrder"], ["descending"])
        adapter, transport = self.arxiv()
        page = adapter.discover(QuerySpec("agents"), Limits(max_items=1))
        self.assertEqual(page.next_cursor, "1")
        self.assertEqual(page.items[0].published_at, "2026-09-07T00:00:00Z")
        self.assertEqual(page.items[0].metadata, (("author", "Research Author"),))
        self.assertEqual(
            parse_qs(urlsplit(transport.requests[0].url).query)["sortBy"],
            ["submittedDate"],
        )

    def test_invalid_configuration_is_rejected_before_client_setup(self) -> None:
        factories = (
            lambda value: ArxivAtomAdapter(include_provenance=value),
            lambda value: RSSAtomAdapter(
                "https://feeds.example/feed",
                allowed_hosts={"feeds.example"},
                include_provenance=value,
            ),
            lambda value: XRecentSearchAdapter(environ={}, include_provenance=value),
        )
        with patch.object(
            sources,
            "_SafeHTTPClient",
            side_effect=AssertionError("client setup forbidden"),
        ):
            for factory in factories:
                for value in (None, 1, "true", []):
                    with (
                        self.subTest(factory=factory, value=value),
                        self.assertRaises(ValueError),
                    ):
                        factory(value)
            for value in (None, "newest", [], 1):
                with self.subTest(sort=value), self.assertRaises(ValueError):
                    ArxivAtomAdapter(sort_by=value)

    def test_arxiv_enrichment_preserves_timestamps_categories_and_pdf(self) -> None:
        adapter, transport = self.arxiv(include_provenance=True)
        page = adapter.discover(QuerySpec("agents"), Limits())
        lead = page.items[0]
        metadata = dict(lead.metadata)
        self.assertEqual(lead.published_at, "2026-08-01T00:00:00Z")
        self.assertEqual(metadata["updated"], "2026-09-07T00:00:00Z")
        self.assertEqual(metadata["work_id"], "arxiv:2609.12345")
        self.assertEqual(metadata["version"], "2")
        self.assertEqual(metadata["doi"], "10.1234/research.42")
        self.assertEqual(metadata["primary_category"], "cs.AI")
        self.assertEqual(
            [value for key, value in lead.metadata if key == "category"],
            ["cs.AI", "cs.CL"],
        )
        self.assertEqual(metadata["article_url"], lead.url)
        self.assertEqual(metadata["pdf_url"], "https://arxiv.org/pdf/2609.12345v2")
        self.assertEqual(metadata["summary_kind"], "arxiv_abstract")
        self.assertEqual(metadata["summary_truncated"], "false")
        self.assertEqual(len(transport.requests), 1)
        self.assertTrue(
            transport.requests[0].url.startswith("https://export.arxiv.org/")
        )

    def test_arxiv_supports_old_identifiers_and_unversioned_links(self) -> None:
        for identifier, work, version in (
            ("hep-th/9901001v3", "hep-th/9901001", "3"),
            ("math.GT/0309136v1", "math.GT/0309136", "1"),
            ("2609.12345", "2609.12345", None),
        ):
            with self.subTest(identifier=identifier):
                adapter, _ = self.arxiv(paper(identifier), include_provenance=True)
                metadata = dict(
                    adapter.discover(QuerySpec("agents"), Limits()).items[0].metadata
                )
                self.assertEqual(metadata["work_id"], "arxiv:" + work)
                self.assertEqual(metadata.get("version"), version)

    def test_arxiv_invalid_or_conflicting_provenance_fails_with_receipt(self) -> None:
        cases = (
            paper().replace(b"http://arxiv.org/pdf/", b"https://evil.example/pdf/"),
            paper().replace(b"/pdf/2609.12345v2", b"/pdf/2609.99999v2"),
            paper().replace(
                b"<id>http://arxiv.org/abs/2609.12345v2",
                b"<id>http://arxiv.org/abs/2609.99999v2",
            ),
            paper().replace(b"10.1234/research.42", b"not-a-doi"),
            paper(extra='<arxiv:primary_category term="cs.RO"/>'),
            paper().replace(b"Research Author", b"A" * 33_000),
        )
        for body in cases:
            with self.subTest(body_size=len(body)):
                adapter, _ = self.arxiv(body, include_provenance=True)
                with self.assertRaises(MalformedResponseError) as error:
                    adapter.discover(QuerySpec("agents"), Limits())
                self.assertEqual(error.exception.code, "FEED_PROVENANCE_INVALID")
                self.assertEqual(error.exception.receipt.request_count, 1)
                self.assertEqual(error.exception.receipt.total_bytes, len(body))

    def test_arxiv_cursor_binds_query_scope_match_sort_without_query_disclosure(
        self,
    ) -> None:
        adapter, _ = self.arxiv(include_provenance=True)
        cursor = adapter.discover(
            QuerySpec("private research query"), Limits(max_items=1)
        ).next_cursor
        self.assertTrue(cursor.startswith("arxiv-v1:"))
        decoded = base64.urlsafe_b64decode(cursor[9:]).decode()
        self.assertNotIn("private research query", decoded)
        cases = (
            ("changed private nonce phrase", {}),
            ("private research query", {"search_scope": "title_abstract"}),
            ("private research query", {"search_match": "phrase"}),
            ("private research query", {"sort_by": "relevance"}),
        )
        for query, options in cases:
            with self.subTest(options=options):
                other, transport = self.arxiv(include_provenance=True, **options)
                with self.assertRaises(ConnectorError) as error:
                    other.discover(QuerySpec(query, cursor), Limits(max_items=1))
                self.assertEqual(error.exception.code, "CURSOR_SCOPE_MISMATCH")
                self.assertEqual(transport.requests, [])
                self.assertNotIn(query, str(error.exception))
        other, transport = self.arxiv(include_provenance=True)
        other.discover(QuerySpec("private research query", cursor), Limits(max_items=1))
        self.assertEqual(
            parse_qs(urlsplit(transport.requests[0].url).query)["start"], ["1"]
        )

    def test_arxiv_cursor_rejects_missing_mutated_and_out_of_bound_fields(self) -> None:
        adapter, _ = self.arxiv(include_provenance=True)
        cursor = adapter.discover(QuerySpec("agents"), Limits(max_items=1)).next_cursor
        valid = json.loads(base64.urlsafe_b64decode(cursor[9:]))
        corrupt = []
        for key in valid:
            changed = dict(valid)
            del changed[key]
            corrupt.append(changed)
        for offset in (2, True, -1, 30_001):
            corrupt.append({**valid, "offset": offset})
        for payload in corrupt:
            encoded = (
                "arxiv-v1:"
                + base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
            )
            other, transport = self.arxiv(include_provenance=True)
            with (
                self.subTest(payload=payload),
                self.assertRaises(ConnectorError) as error,
            ):
                other.discover(QuerySpec("agents", encoded), Limits(max_items=1))
            self.assertEqual(error.exception.code, "CURSOR_INVALID")
            self.assertEqual(transport.requests, [])
        for malformed in ("1", "", "arxiv-v1:not-base64"):
            other, transport = self.arxiv(include_provenance=True)
            with self.assertRaises(ConnectorError):
                other.discover(QuerySpec("agents", malformed), Limits())
            self.assertEqual(transport.requests, [])

    def test_local_offset_ceiling_is_explicit_not_end_of_results(self) -> None:
        scope = sources._arxiv_cursor_scope(
            QuerySpec("agents"), "all", "terms", "submittedDate"
        )
        cursor = sources._arxiv_next_cursor(30_000, scope)
        adapter, transport = self.arxiv(include_provenance=True)
        with self.assertRaises(ConnectorError) as error:
            adapter.discover(QuerySpec("agents", cursor), Limits(max_items=1))
        self.assertEqual(error.exception.code, "CURSOR_LIMIT")
        self.assertEqual(transport.requests, [])

    def test_feed_full_content_is_selected_before_teaser(self) -> None:
        bodies = (
            atom_feed(
                '<entry><title>Research</title><link href="https://research.example/paper"/><summary>Teaser</summary><content type="html">&lt;p&gt;mechanismneedle &lt;b&gt;method&lt;/b&gt;&lt;/p&gt;</content></entry>'
            ),
            b'<rss xmlns:content="http://purl.org/rss/1.0/modules/content/"><channel><item><title>Research</title><link>https://research.example/paper</link><description>Teaser</description><content:encoded><![CDATA[<p>mechanismneedle <b>method</b></p>]]></content:encoded></item></channel></rss>',
        )
        for body, kind in zip(bodies, ("atom_content", "rss_content_encoded")):
            with self.subTest(kind=kind):
                legacy, _ = self.feed(body)
                self.assertEqual(
                    legacy.discover(QuerySpec("mechanismneedle"), Limits()).items, ()
                )
                adapter, _ = self.feed(body, include_provenance=True)
                page = adapter.discover(QuerySpec("mechanismneedle"), Limits())
                self.assertEqual(page.items[0].summary, "mechanismneedle method")
                self.assertEqual(dict(page.items[0].metadata)["summary_kind"], kind)

    def test_feed_filter_uses_full_body_and_records_summary_truncation(self) -> None:
        body = atom_feed(
            '<entry><title>Research</title><link href="https://research.example/paper"/><content>'
            + "word " * 4_000
            + "mechanismneedle</content></entry>"
        )
        adapter, _ = self.feed(body, include_provenance=True)
        page = adapter.discover(QuerySpec("mechanismneedle"), Limits())
        self.assertEqual(len(page.items), 1)
        self.assertEqual(len(page.items[0].summary), 16_384)
        self.assertNotIn("mechanismneedle", page.items[0].summary)
        self.assertEqual(dict(page.items[0].metadata)["summary_truncated"], "true")

    def test_xml_base_is_inherited_at_feed_entry_and_link(self) -> None:
        body = b'<feed xmlns="http://www.w3.org/2005/Atom" xml:base="https://research.example/"><entry xml:base="papers/"><title>Research</title><link xml:base="2026/" href="new"/><summary>Method</summary></entry></feed>'
        adapter, transport = self.feed(body, include_provenance=True)
        page = adapter.discover(QuerySpec(), Limits())
        self.assertEqual(page.items[0].url, "https://research.example/papers/2026/new")
        self.assertEqual(len(transport.requests), 1)
        unsafe = body.replace(b"https://research.example/", b"file:///private/")
        adapter, _ = self.feed(unsafe, include_provenance=True)
        with self.assertRaises(MalformedResponseError) as error:
            adapter.discover(QuerySpec(), Limits())
        self.assertEqual(error.exception.code, "FEED_ITEM_INVALID")

    def test_empty_feed_content_is_not_claimed_to_be_a_full_article(self) -> None:
        body = atom_feed(
            '<entry><title>Research</title><link href="https://research.example/paper"/><content src="https://research.example/full"/></entry>'
        )
        adapter, transport = self.feed(body, include_provenance=True)
        lead = adapter.discover(QuerySpec(), Limits()).items[0]
        self.assertEqual(lead.summary, "")
        self.assertEqual(dict(lead.metadata)["summary_kind"], "none")
        self.assertEqual(len(transport.requests), 1)

    def test_feed_cursors_cannot_cross_content_modes(self) -> None:
        body = atom_feed(atom_entry("Research", "https://research.example/paper"))
        legacy, _ = self.feed(body)
        cursor = legacy.discover(QuerySpec(), Limits()).next_cursor
        enriched, transport = self.feed(body, include_provenance=True)
        with self.assertRaises(ConnectorError) as error:
            enriched.discover(QuerySpec(cursor=cursor), Limits())
        self.assertEqual(error.exception.code, "CURSOR_SCOPE_MISMATCH")
        self.assertEqual(transport.requests, [])

    def test_x_long_form_aliases_and_link_relationships_keep_legacy_wire(self) -> None:
        links = {
            "urls": [
                {
                    "url": "https://t.co/a",
                    "expanded_url": "https://arxiv.org/abs/2609.12345v2",
                    "unwound_url": "https://arxiv.org/abs/2609.12345v2",
                }
            ]
        }
        for note_name, reference_name in (
            ("note_tweet", "referenced_tweets"),
            ("note_post", "referenced_posts"),
        ):
            item = {
                "id": "123",
                "text": "Teaser",
                "author_id": "42",
                note_name: {"text": "Full method", "entities": links},
                reference_name: [{"type": "quoted", "id": "456"}],
            }
            adapter, transport = self.x(item, include_provenance=True)
            page = adapter.discover(QuerySpec("research"), Limits(max_items=10))
            lead = page.items[0]
            metadata = dict(lead.metadata)
            self.assertEqual(lead.summary, "Full method")
            self.assertEqual(metadata["summary_kind"], "x_" + note_name)
            self.assertEqual(json.loads(metadata["outbound_link"]), links["urls"][0])
            self.assertEqual(
                json.loads(metadata["referenced_post"]), {"type": "quoted", "id": "456"}
            )
            self.assertEqual(metadata["enrichment_wire_status"], "not_live_validated")
            self.assertEqual(
                parse_qs(urlsplit(transport.requests[0].url).query)["tweet.fields"],
                ["created_at,author_id,lang,entities,note_tweet,referenced_tweets"],
            )
            self.assertEqual(
                metadata["request_contract"],
                "x-v2-tweets-recent:tweet.fields=created_at,author_id,lang,entities,note_tweet,referenced_tweets",
            )
            self.assertEqual(len(transport.requests), 1)

    def test_x_default_fields_unchanged_and_enrichment_has_no_dialect_retry(
        self,
    ) -> None:
        adapter, transport = self.x({"id": "123", "text": "Research"})
        adapter.discover(QuerySpec("research"), Limits(max_items=10))
        self.assertEqual(
            parse_qs(urlsplit(transport.requests[0].url).query)["tweet.fields"],
            ["created_at,author_id,lang"],
        )
        transport = ScriptedTransport(
            response(b'{"error":"unsupported field"}', "application/json", status=400),
            response(b'{"meta":{"result_count":0}}', "application/json"),
        )
        enriched = XRecentSearchAdapter(
            environ={"X_BEARER_TOKEN": "offline-fixture-not-a-credential"},
            include_provenance=True,
            transport=transport,
            resolver=resolver_for("api.x.com"),
        )
        with self.assertRaises(ConnectorError) as error:
            enriched.discover(QuerySpec("research"), Limits(max_items=10))
        self.assertEqual(error.exception.code, "HTTP_STATUS")
        self.assertEqual(len(transport.requests), 1)
        self.assertEqual(len(transport.steps), 1)

    def test_x_matching_aliases_are_unambiguous_and_conflicts_fail_closed(self) -> None:
        note = {"text": "Full method"}
        base = {
            "id": "123",
            "text": "Teaser",
            "note_tweet": note,
            "note_post": dict(note),
        }
        adapter, _ = self.x(base, include_provenance=True)
        metadata = dict(
            adapter.discover(QuerySpec("research"), Limits(max_items=10))
            .items[0]
            .metadata
        )
        self.assertEqual(metadata["summary_kind"], "x_long_form_note")
        bad = (
            {**base, "note_post": {"text": "Conflicting text"}},
            {
                **base,
                "note_post": {
                    "text": "Full method",
                    "entities": {"urls": [{"url": "https://example.org/"}]},
                },
            },
            {
                **base,
                "referenced_tweets": [{"id": "1", "type": "quoted"}],
                "referenced_posts": [{"id": "2", "type": "quoted"}],
            },
        )
        for item in bad:
            adapter, _ = self.x(item, include_provenance=True)
            with self.assertRaises(MalformedResponseError) as error:
                adapter.discover(QuerySpec("research"), Limits(max_items=10))
            self.assertEqual(error.exception.code, "X_PROVENANCE_INVALID")
            self.assertEqual(error.exception.receipt.request_count, 1)

    def test_x_optional_payload_types_urls_and_counts_are_bounded(self) -> None:
        bad = (
            {"note_tweet": None},
            {"note_post": {"text": []}},
            {"entities": []},
            {"entities": {"urls": "not-list"}},
            {"entities": {"urls": [{"url": "javascript:alert(1)"}]}},
            {"entities": {"urls": [{"url": "https://user:password@example.org/"}]}},
            {"entities": {"urls": [{"url": "https://example.org/"}] * 21}},
            {"referenced_posts": [{"id": "not-id", "type": "quoted"}]},
        )
        for extra in bad:
            adapter, _ = self.x(
                {"id": "123", "text": "Teaser", **extra}, include_provenance=True
            )
            with (
                self.subTest(extra=extra),
                self.assertRaises(MalformedResponseError) as error,
            ):
                adapter.discover(QuerySpec("research"), Limits(max_items=10))
            self.assertEqual(error.exception.code, "X_PROVENANCE_INVALID")

    def test_x_long_text_truncation_and_http_link_observation_are_explicit(
        self,
    ) -> None:
        item = {
            "id": "123",
            "text": "Teaser",
            "note_tweet": {"text": "word " * 4_000},
            "entities": {
                "urls": [
                    {
                        "url": "https://t.co/a",
                        "expanded_url": "http://research.example/paper",
                    }
                ]
            },
        }
        adapter, transport = self.x(item, include_provenance=True)
        page = adapter.discover(QuerySpec("research"), Limits(max_items=10))
        metadata = dict(page.items[0].metadata)
        self.assertEqual(metadata["summary_truncated"], "true")
        self.assertEqual(len(page.items[0].summary), 16_384)
        self.assertEqual(
            json.loads(metadata["outbound_link"])["expanded_url"],
            "http://research.example/paper",
        )
        self.assertFalse(page.receipt.authoritative)
        self.assertEqual(len(transport.requests), 1)

    def test_enriched_and_legacy_adapters_replay_under_their_exact_factories(
        self,
    ) -> None:
        for enriched in (False, True):
            for source in ("arxiv", "rss", "x"):
                with self.subTest(source=source, enriched=enriched):
                    captures = []
                    options = {
                        "include_provenance": enriched,
                        "capture_sink": lambda meta, body: captures.append(
                            (meta, body)
                        ),
                    }
                    query, limits = QuerySpec("research"), Limits(max_items=10)
                    if source == "arxiv":
                        adapter, _ = self.arxiv(sort_by="lastUpdatedDate", **options)

                        def factory(**kwargs):
                            return ArxivAtomAdapter(
                                sort_by="lastUpdatedDate",
                                include_provenance=enriched,
                                **kwargs,
                            )
                    elif source == "rss":
                        adapter, _ = self.feed(paper(), **options)

                        def factory(**kwargs):
                            return RSSAtomAdapter(
                                "https://feeds.example/feed.atom",
                                allowed_hosts={"feeds.example"},
                                include_provenance=enriched,
                                **kwargs,
                            )
                    else:
                        adapter, _ = self.x(
                            {
                                "id": "123",
                                "text": "Research",
                                "note_post": {"text": "Research full method"},
                            },
                            **options,
                        )

                        def factory(**kwargs):
                            return XRecentSearchAdapter(
                                environ={
                                    "X_BEARER_TOKEN": "offline-fixture-not-a-credential"
                                },
                                include_provenance=enriched,
                                **kwargs,
                            )

                    original = adapter.discover(query, limits)
                    replay = replay_discovery(factory, captures, query, limits)
                    self.assertIsInstance(replay, LeadPage)
                    self.assertEqual(replay.items, original.items)
                    self.assertEqual(replay.next_cursor, original.next_cursor)
                    self.assertEqual(
                        replay.receipt.total_bytes, original.receipt.total_bytes
                    )


if __name__ == "__main__":
    unittest.main()
