"""Daily lane fixtures use actual adapters, private capture storage and replay."""

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from researcher.scripts import source_connectors as c
from researcher.scripts.tests.test_source_connectors import ScriptedTransport
from researcher.scripts.tests.test_source_search import START, END, TOKEN, hn_payload, openalex_payload, x_payload
from researcher.service import retrieval_sources as r
from researcher.service.contracts import ServiceError


class RetrievalSourceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name).resolve() / "evidence"

    def collect(self, source, payload, *, status=200, headers=()):
        body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        media = "application/xml" if isinstance(payload, bytes) else "application/json"
        transport = ScriptedTransport(c.TransportResponse(status, (("Content-Type", media), *headers), body))
        original = r._adapter
        def offline(name, start_time, end_time, credential=None, **kwargs):
            return original(name, start_time, end_time, credential,
                            transport=transport, resolver=lambda host, port: ("93.184.216.34",), **kwargs)
        with patch.object(r, "_adapter", side_effect=offline):
            lane = r.collect(source, "episodic memory", self.directory, start_time=START, end_time=END,
                             credential=TOKEN if source in {"x", "openalex"} else None)
        return lane, transport

    def verify(self, source, lane, **kwargs):
        with patch("socket.socket.connect", side_effect=AssertionError("network forbidden")):
            r.verify(source, "episodic memory", lane, self.directory,
                     start_time=kwargs.get("start_time", START), end_time=kwargs.get("end_time", END))

    def snapshot(self):
        return {str(path.relative_to(self.directory)): (path.stat().st_mode, path.stat().st_mtime_ns,
                  path.read_bytes() if path.is_file() else None)
                for path in self.directory.rglob("*")}

    def test_registered_names_limits_and_no_ambient_keys(self):
        self.assertEqual(r.SOURCES, ("arxiv", "deepmind", "huggingface", "microsoft_research", "hacker_news", "x", "openalex"))
        for name in r.SOURCES:
            self.assertEqual(r.source_limits(name).max_requests, 1)
            self.assertEqual(r.source_limits(name).max_items, 6 if name in r.FEEDS else 10)
        with self.assertRaises(ServiceError):
            r.source_limits("arbitrary-url")
        for name in ("x", "openalex"):
            with patch("os.environ", {"X_BEARER_TOKEN": TOKEN, "OPENALEX_API_KEY": TOKEN}):
                with self.assertRaises(c.ConnectorDisabledError):
                    r.collect(name, "query", self.directory, start_time=START, end_time=END)
        self.assertFalse(self.directory.exists())

    def test_each_new_source_capture_replays_without_writes_or_network(self):
        for name, payload in (("hacker_news", hn_payload()), ("openalex", openalex_payload()), ("x", x_payload())):
            with self.subTest(name=name):
                lane, transport = self.collect(name, payload)
                before = self.snapshot()
                self.verify(name, lane)
                self.assertEqual(before, self.snapshot())
                self.assertEqual(len(transport.requests), 1)
                self.assertEqual(len(lane["captures"]), 1)
                self.assertEqual(lane["coverage"]["window_resolution"], "day" if name == "openalex" else "second")
                self.assertFalse(lane["coverage"]["quality_assessed"])
                self.assertEqual(lane["evidence"][0]["evidence_scope"], "discovery_summary")
                self.assertNotIn(TOKEN, json.dumps(lane))

    def test_more_provider_results_mark_partial_without_advancing(self):
        lane, transport = self.collect("hacker_news", hn_payload(nbHits=100, nbPages=10))
        self.assertTrue(lane["coverage"]["partial"])
        self.assertTrue(lane["coverage"]["continuation_available"])
        self.assertEqual(lane["next_cursor"], "unfetched_page:1")
        self.assertEqual(len(transport.requests), 1)
        self.verify("hacker_news", lane)

    def test_empty_result_is_observed_not_relevant_or_complete_claim(self):
        lane, _ = self.collect("hacker_news", hn_payload(hits=[], nbHits=0, nbPages=0))
        self.assertEqual(lane["state"], "observed")
        self.assertEqual(lane["evidence"], [])
        self.assertEqual(lane["coverage"]["completeness"], "bounded_page_not_exhaustive")
        self.verify("hacker_news", lane)

    def test_rate_limit_saved_and_replayed_without_retry(self):
        lane, transport = self.collect("openalex", {}, status=429, headers=(("Retry-After", "60"),))
        self.assertEqual(lane["state"], "rate_limited")
        self.assertTrue(lane["coverage"]["partial"])
        self.assertEqual(lane["retry_after_seconds"], 60)
        self.assertEqual(transport.steps, [])
        self.verify("openalex", lane)

    def test_mutated_text_url_coverage_cursor_receipt_fail_replay(self):
        lane, _ = self.collect("hacker_news", hn_payload())
        changes = [lambda value: value["evidence"][0].update(text="forged"),
                   lambda value: value["evidence"][0].update(url="https://evil.example/"),
                   lambda value: value["coverage"].update(quality_assessed=True),
                   lambda value: value.update(next_cursor="forged"),
                   lambda value: value["receipt"].update(request_count=True),
                   lambda value: value["receipt"]["observations"][0].update(response_bytes=0)]
        for change in changes:
            altered = deepcopy(lane)
            change(altered)
            with self.assertRaises(ServiceError):
                self.verify("hacker_news", altered)

    def test_changed_window_and_query_fail_replay(self):
        lane, _ = self.collect("hacker_news", hn_payload())
        with self.assertRaises(ServiceError):
            self.verify("hacker_news", lane, end_time=END - 1)
        with self.assertRaises(ServiceError):
            r.verify("hacker_news", "different", lane, self.directory, start_time=START, end_time=END)

    def test_missing_duplicate_and_corrupt_captures_fail(self):
        lane, _ = self.collect("hacker_news", hn_payload())
        for captures in ([], lane["captures"] * 2, [{**lane["captures"][0], "body_sha256": "sha256:" + "0" * 64}]):
            altered = {**lane, "captures": captures}
            with self.assertRaises((ValueError, RuntimeError)):
                self.verify("hacker_news", altered)

    def test_company_title_only_and_depth_metadata_survive(self):
        feed = b'<rss><channel><item><title>Title only</title><link>https://deepmind.google/blog/one/</link></item></channel></rss>'
        lane, _ = self.collect("deepmind", feed)
        metadata = dict(lane["evidence"][0]["metadata"])
        self.assertEqual(metadata["summary_kind"], "none")
        self.assertFalse(lane["coverage"]["window_applied"])
        self.assertTrue(lane["coverage"]["partial"])
        self.verify("deepmind", lane)

    def test_large_feed_reports_truncation_not_full_body(self):
        feed = ('<rss><channel><item><title>T</title><link>https://deepmind.google/blog/one/</link>'
                '<description>' + 'long ' * 5000 + '</description></item></channel></rss>').encode()
        lane, _ = self.collect("deepmind", feed)
        self.assertEqual(dict(lane["evidence"][0]["metadata"])["summary_truncated"], "true")
        self.verify("deepmind", lane)

    def test_invalid_bounds_fail_before_storage(self):
        with self.assertRaises(ValueError):
            r.collect("hacker_news", "query", self.directory, start_time=True, end_time=END)
        self.assertFalse(self.directory.exists())


if __name__ == "__main__":
    unittest.main()
