"""Offline provider contracts. No source API, credential lookup or model calls."""

from copy import deepcopy
from datetime import UTC, datetime
import json
import unittest
from urllib.parse import parse_qs, urlsplit

from researcher.scripts import source_connectors as c
from researcher.scripts.source_search import (
    HackerNewsSearchAdapter, OpenAlexWorksAdapter, reconstruct_abstract,
)
from researcher.scripts.tests.test_source_connectors import ScriptedTransport, resolver_for, response

START = int(datetime(2026, 9, 27, tzinfo=UTC).timestamp())
END = START + 86400
TOKEN = "synthetic-test-token-never-live"
LIMITS = c.Limits(max_items=10, max_requests=1, max_pages=1, max_redirects=0)


def hn_payload(**changes):
    value = {"hits": [{"objectID": "123", "title": "A retrieval mechanism", "url": "https://example.org/paper",
                       "story_text": "Evidence <b>not instructions</b>", "author": "researcher",
                       "created_at_i": START + 60, "points": 12, "num_comments": 3}],
             "page": 0, "nbPages": 1, "nbHits": 1}
    value.update(changes)
    return value


def openalex_payload(**changes):
    value = {"meta": {"count": 1}, "results": [{"id": "https://openalex.org/W123",
        "title": "A paper", "doi": "https://doi.org/10.1234/one", "publication_date": "2026-09-27",
        "abstract_inverted_index": {"Evidence": [0], "survives": [1], "transfer.": [2]},
        "primary_location": {"landing_page_url": "https://arxiv.org/abs/2609.12345v1",
                             "pdf_url": "https://arxiv.org/pdf/2609.12345v1"},
        "open_access": {"is_oa": True}, "ids": {"openalex": "https://openalex.org/W123"}}]}
    value.update(changes)
    return value


def x_payload(**changes):
    value = {"data": [{"id": "123", "text": "Short post", "created_at": "2026-09-27T00:01:00Z",
                        "conversation_id": "111", "public_metrics": {"like_count": 7},
                        "note_tweet": {"text": "Long post preserving qualifiers."},
                        "referenced_tweets": [{"id": "111", "type": "replied_to"}]}],
             "meta": {"result_count": 1}}
    value.update(changes)
    return value


def adapter(kind, payload, *, captures=None, **options):
    raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
    transport = ScriptedTransport(response(raw, "application/json"))
    klass, host = {"hn": (HackerNewsSearchAdapter, "hn.algolia.com"),
                   "openalex": (OpenAlexWorksAdapter, "api.openalex.org"),
                   "x": (c.XRecentSearchAdapter, "api.x.com")}[kind]
    kwargs = {"start_time": START, "end_time": END, "transport": transport,
              "resolver": resolver_for(host)}
    if captures is not None:
        kwargs["capture_sink"] = lambda observation, body: captures.append((observation, body))
    if kind == "openalex":
        kwargs["credential"] = TOKEN
    if kind == "x":
        kwargs.update(environ={"X_BEARER_TOKEN": TOKEN}, include_provenance=True, include_context=True)
    kwargs.update(options)
    return klass(**kwargs), transport


class DatedSearchTests(unittest.TestCase):
    def test_hn_exact_query_date_filter_and_single_page(self):
        instance, transport = adapter("hn", hn_payload(nbPages=2, nbHits=11))
        page = instance.discover(c.QuerySpec("agent memory OR episodic"), LIMITS)
        query = parse_qs(urlsplit(transport.requests[0].url).query)
        self.assertEqual(query["query"], ["agent memory OR episodic"])
        self.assertEqual(query["numericFilters"], [f"created_at_i>={START},created_at_i<{END}"])
        self.assertEqual(query["tags"], ["story"])
        self.assertEqual(len(transport.requests), 1)
        self.assertEqual(page.next_cursor, "unfetched_page:1")
        self.assertEqual(dict(page.items[0].metadata)["discussion_url"], "https://news.ycombinator.com/item?id=123")
        self.assertIn("<b>", page.items[0].summary)  # Observed data, never executed.

    def test_hn_empty_and_missing_article_still_use_discussion(self):
        instance, _ = adapter("hn", hn_payload(hits=[], nbHits=0, nbPages=0))
        self.assertEqual(instance.discover(c.QuerySpec("x"), LIMITS).items, ())
        data = hn_payload()
        data["hits"][0].update(url=None, story_text=None)
        instance, _ = adapter("hn", data)
        lead = instance.discover(c.QuerySpec("x"), LIMITS).items[0]
        self.assertTrue(lead.url.startswith("https://news.ycombinator.com/"))
        self.assertEqual(dict(lead.metadata)["summary_kind"], "none")

    def test_hn_malformed_duplicate_and_out_of_window_rejected(self):
        mutations = [lambda p: p.update(nbHits=True), lambda p: p.update(page=1),
                     lambda p: p["hits"].append(deepcopy(p["hits"][0])),
                     lambda p: p["hits"][0].update(created_at_i=END),
                     lambda p: p["hits"][0].update(created_at_i=True),
                     lambda p: p["hits"][0].update(points=-1)]
        for change in mutations:
            with self.subTest(change=change):
                data = hn_payload()
                change(data)
                instance, _ = adapter("hn", data)
                with self.assertRaises(c.MalformedResponseError):
                    instance.discover(c.QuerySpec("x"), LIMITS)

    def test_bounds_and_cursors_fail_before_http(self):
        for start, end in ((True, END), (START, START), (START, END + 32 * 86400)):
            with self.assertRaises(ValueError):
                HackerNewsSearchAdapter(start_time=start, end_time=end)
        instance, transport = adapter("hn", hn_payload())
        for query in (c.QuerySpec("x", "1"), c.QuerySpec("")):
            with self.assertRaises(c.ConnectorError):
                instance.discover(query, LIMITS)
        self.assertEqual(transport.requests, [])
        self.assertEqual(instance.discover(c.QuerySpec(""), c.Limits(max_requests=0)).items, ())

    def test_openalex_header_dates_identifiers_and_abstract(self):
        instance, transport = adapter("openalex", openalex_payload(meta={"count": 12}))
        page = instance.discover(c.QuerySpec("episodic agent memory"), LIMITS)
        request = transport.requests[0]
        query = parse_qs(urlsplit(request.url).query)
        self.assertEqual(query["filter"], ["from_publication_date:2026-09-27,to_publication_date:2026-09-27"])
        self.assertIn("abstract_inverted_index", query["select"][0])
        self.assertNotIn(TOKEN, request.url)
        self.assertEqual(dict(request.headers)["Authorization"], "Bearer " + TOKEN)
        self.assertEqual(page.items[0].summary, "Evidence survives transfer.")
        self.assertEqual(page.items[0].identity, "openalex:W123")
        self.assertEqual(page.next_cursor, "unfetched_page:2")
        self.assertNotIn(TOKEN, repr(page))

    def test_openalex_null_abstract_is_title_only_not_full_text(self):
        data = openalex_payload()
        data["results"][0]["abstract_inverted_index"] = None
        instance, _ = adapter("openalex", data)
        item = instance.discover(c.QuerySpec("x"), LIMITS).items[0]
        self.assertEqual(item.summary, "")
        self.assertEqual(dict(item.metadata)["summary_kind"], "none")

    def test_abstract_positions_and_unicode_bounds(self):
        self.assertEqual(reconstruct_abstract({"é": [1], "a": [0, 2]}), "a é a")
        for value in ({"a": [True]}, {"a": [1]}, {"a": [0, 0]}, {"a": [0], "b": [0]},
                      {"a": [8192]}, {"é" * 1025: [0]}, [], {"a": []}):
            with self.subTest(value=repr(value)[:80]), self.assertRaises(ValueError):
                reconstruct_abstract(value)

    def test_openalex_missing_credential_does_not_read_environment(self):
        instance, transport = adapter("openalex", openalex_payload(), credential=None)
        with self.assertRaises(c.ConnectorDisabledError):
            instance.discover(c.QuerySpec("x"), LIMITS)
        self.assertEqual(transport.requests, [])

    def test_openalex_malformed_papers_rejected(self):
        changes = [lambda p: p.update(meta={"count": True}),
                   lambda p: p["results"][0].update(id="https://openalex.org.evil/W123"),
                   lambda p: p["results"][0].update(publication_date="2026-09-28"),
                   lambda p: p["results"][0].update(abstract_inverted_index={"a": [0, 0]})]
        for change in changes:
            data = openalex_payload()
            change(data)
            instance, _ = adapter("openalex", data)
            with self.assertRaises(c.MalformedResponseError):
                instance.discover(c.QuerySpec("x"), LIMITS)

    def test_rate_limit_is_observed_without_sleep_or_retry(self):
        for kind in ("hn", "openalex"):
            instance, transport = adapter(kind, {})
            transport.steps = [c.TransportResponse(429, (("Content-Type", "application/json"), ("Retry-After", "60")), b"{}")]
            result = instance.discover(c.QuerySpec("x"), LIMITS)
            self.assertIsInstance(result, c.RetryAfter)
            self.assertEqual(result.retry_after_seconds, 60)
            self.assertEqual(len(transport.requests), 1)

    def test_real_adapter_offline_replay_and_missing_capture(self):
        for kind, payload, klass in (("hn", hn_payload(), HackerNewsSearchAdapter),
                                     ("openalex", openalex_payload(), OpenAlexWorksAdapter)):
            captures = []
            instance, _ = adapter(kind, payload, captures=captures)
            result = instance.discover(c.QuerySpec("x"), LIMITS)
            def factory(**kwargs):
                return klass(start_time=START, end_time=END,
                             **({"credential": "offline-replay-dummy"} if kind == "openalex" else {}), **kwargs)
            self.assertEqual(c.replay_discovery(factory, captures, c.QuerySpec("x"), LIMITS).items, result.items)
            with self.assertRaises(c.ConnectorError):
                c.replay_discovery(factory, [], c.QuerySpec("x"), LIMITS)

    def test_credential_reflections_rejected_before_capture(self):
        encoded = "".join("\\u%04x" % ord(ch) for ch in TOKEN)
        for kind in ("openalex", "x"):
            for body in (json.dumps({"error": TOKEN}).encode(), ('{"error":"' + encoded + '"}').encode(),
                         ('{"error":"' + encoded + '","error":"shadowed"}').encode()):
                captures = []
                instance, _ = adapter(kind, body, captures=captures)
                with self.assertRaises(c.PolicyError) as error:
                    instance.discover(c.QuerySpec("x"), LIMITS)
                self.assertEqual(error.exception.code, "CREDENTIAL_REFLECTED")
                self.assertEqual(captures, [])
                self.assertNotIn(TOKEN, str(error.exception))

    def test_credential_reflected_in_header_or_transport_exception_is_not_retained(self):
        for kind in ("openalex", "x"):
            captures = []
            instance, transport = adapter(kind, {}, captures=captures)
            transport.steps = [c.TransportResponse(200, (("Content-Type", "application/json"), ("ETag", TOKEN)), b"{}")]
            with self.assertRaises(c.PolicyError):
                instance.discover(c.QuerySpec("x"), LIMITS)
            self.assertEqual(captures, [])
            def raises(request):
                raise RuntimeError("sensitive transport context " + TOKEN)
            transport.steps = [raises]
            with self.assertRaises(c.ConnectorError) as error:
                instance.discover(c.QuerySpec("x"), LIMITS)
            self.assertNotIn(TOKEN, str(error.exception))
            self.assertEqual(captures, [])

    def test_provider_duplicate_json_keys_and_excess_page_fail_closed(self):
        for kind in ("hn", "openalex"):
            instance, _ = adapter(kind, b'{"results":[],"results":[]}')
            with self.assertRaises(c.MalformedResponseError):
                instance.discover(c.QuerySpec("x"), LIMITS)
        data = hn_payload(hits=hn_payload()["hits"] * 11, nbHits=11)
        instance, _ = adapter("hn", data)
        with self.assertRaises(c.MalformedResponseError):
            instance.discover(c.QuerySpec("x"), LIMITS)


class XWindowTests(unittest.TestCase):
    def test_explicit_window_and_context_fields_no_thread_fetch(self):
        instance, transport = adapter("x", x_payload())
        result = instance.discover(c.QuerySpec("from:researcher memory"), LIMITS)
        query = parse_qs(urlsplit(transport.requests[0].url).query)
        self.assertEqual(query["start_time"], ["2026-09-27T00:00:00Z"])
        self.assertEqual(query["end_time"], ["2026-09-28T00:00:00Z"])
        self.assertIn("public_metrics,conversation_id", query["tweet.fields"][0])
        self.assertEqual(dict(result.items[0].metadata)["conversation_id"], "111")
        self.assertEqual(result.items[0].summary, "Long post preserving qualifiers.")
        self.assertEqual(len(transport.requests), 1)

    def test_window_metrics_and_conversation_fail_closed(self):
        for change in ({"created_at": "2026-09-28T00:00:00Z"}, {"created_at": "2026-09-27T00:00:00"},
                       {"public_metrics": {"like_count": True}}, {"conversation_id": "wrong"}):
            data = x_payload()
            data["data"][0].update(change)
            instance, _ = adapter("x", data)
            with self.assertRaises(c.MalformedResponseError):
                instance.discover(c.QuerySpec("x"), LIMITS)

    def test_window_validation_and_legacy_default_wire(self):
        for values in ({"start_time": True}, {"end_time": START}, {"end_time": END + 7 * 86400}):
            with self.assertRaises(ValueError):
                adapter("x", x_payload(), **values)
        instance, transport = adapter("x", x_payload(), start_time=None, end_time=None,
                                      include_context=False, include_provenance=False)
        instance.discover(c.QuerySpec("x"), LIMITS)
        query = parse_qs(urlsplit(transport.requests[0].url).query)
        self.assertEqual(query["tweet.fields"], ["created_at,author_id,lang"])
        self.assertNotIn("start_time", query)

    def test_bounded_x_rejects_duplicates_overfull_pages_and_boolean_counts(self):
        data = x_payload()
        for payload in (x_payload(meta={"result_count": True}),
                        x_payload(data=data["data"] * 2, meta={"result_count": 2}),
                        x_payload(data=data["data"] * 11, meta={"result_count": 11})):
            instance, _ = adapter("x", payload)
            with self.assertRaises(c.MalformedResponseError):
                instance.discover(c.QuerySpec("x"), LIMITS)

    def test_window_is_checked_even_without_provenance_enrichment(self):
        payload = x_payload()
        payload["data"][0]["created_at"] = "2026-09-28T00:00:00Z"
        instance, _ = adapter("x", payload, include_context=False, include_provenance=False)
        with self.assertRaises(c.MalformedResponseError):
            instance.discover(c.QuerySpec("x"), LIMITS)


if __name__ == "__main__":
    unittest.main()
