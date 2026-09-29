"""Captured primary alternatives and local pre-dispatch spacing, no live HTTP."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from researcher.scripts.source_connectors import LimitExceededError, TransportResponse
from researcher.scripts.tests.test_source_connectors import ScriptedTransport
from researcher.service import primary_context as primary, retrieval_sources
from researcher.service.context_digest import build_context_digest
from researcher.service.contracts import ServiceError, load_config
from researcher.service.retrieval_handoff import verified_bundle
from researcher.service.store import Store
from researcher.service.tests.test_daily_retrieval import DAY, ROOT, config, lane as synthetic_lane
from researcher.service.tests.test_primary_context import HTML, evidence, fixture_reader, lane
from researcher.service.workflow import Workflow, make_manifest


class SelectionTests(unittest.TestCase):
    def select(self, entries, *, profile=primary.SELECTION_PROFILE, limit=2):
        lanes = [lane(entries)]
        packet = build_context_digest("context engineering", lanes)
        return primary.select_primary(lanes, packet, limit, profile=profile)

    def test_default_preserves_v1_single_host_and_no_new_field(self):
        entries = [evidence("https://arxiv.org/abs/2609.00001v1", identity="one"),
                   evidence("https://arxiv.org/abs/2609.00002v1", identity="two")]
        old = self.select(entries, profile=None)
        self.assertEqual(len(old["selected"]), 1)
        self.assertEqual(old["omissions"][0]["reason"], "host_read_limit")
        self.assertNotIn("selection_profile", old)
        new = self.select(entries)
        self.assertEqual(len(new["selected"]), 2)
        self.assertEqual(new["omissions"], [])
        self.assertEqual(new["selection_profile"], primary.SELECTION_PROFILE)

    def test_diversity_precedes_same_host_fill_and_total_limit_is_two(self):
        entries = [evidence("https://arxiv.org/abs/2609.00001v1", identity="one"),
                   evidence("https://arxiv.org/abs/2609.00002v1", identity="two"),
                   evidence("https://huggingface.co/blog/context", identity="three")]
        result = self.select(entries)
        self.assertEqual({row["source_url"].split("/")[2] for row in result["selected"]},
                         {"arxiv.org", "huggingface.co"})
        self.assertEqual(result["omissions"][0]["reason"], "primary_read_limit")
        self.assertEqual(len(self.select(entries, limit=1)["selected"]), 1)

    def test_distinct_urls_only_and_untrusted_or_unmatched_rows_never_fill(self):
        entries = [evidence("https://arxiv.org/abs/2609.00001v1", identity="one"),
                   evidence("https://arxiv.org/abs/2609.00001v1", identity="duplicate"),
                   evidence("https://arxiv.org/abs/2609.00002v1", identity="second"),
                   evidence("https://example.org/article", identity="bad"),
                   evidence("https://huggingface.co/blog/unrelated", identity="offtopic", text="Unrelated subject")]
        result = self.select(entries)
        self.assertEqual(len({row["source_url"] for row in result["selected"]}), 2)
        self.assertEqual({row["reason"] for row in result["omissions"]},
                         {"duplicate_primary_url", "no_allowlisted_primary_html", "no_query_term_overlap"})

    def test_profile_is_explicit_closed_and_requires_configured_capacity(self):
        for profile in ("unknown", True, "", {}):
            with self.subTest(profile=profile), self.assertRaises(ServiceError):
                self.select([], profile=profile)
        settings = config()
        settings["schedules"][0]["primary_selection_profile"] = primary.SELECTION_PROFILE
        with self.assertRaisesRegex(ServiceError, "PRIMARY_PROFILE_REQUIRES_READ_LIMIT"):
            load_config(json.dumps(settings))
        settings["schedules"][0]["primary_read_limit"] = 2
        checked = load_config(json.dumps(settings))
        manifest = make_manifest(ROOT, checked, checked["schedules"][0], fixture=True, window_end=DAY)
        self.assertEqual(manifest["schedule"]["primary_selection_profile"], primary.SELECTION_PROFILE)


FEED = b'''<rss><channel>
<item><title>Context engineering first</title><link>https://deepmind.google/blog/context-first/</link>
<description>Context engineering matched evidence.</description></item>
<item><title>Context engineering second</title><link>https://deepmind.google/blog/context-second/</link>
<description>Context engineering matched evidence.</description></item>
<item><title>Context engineering third</title><link>https://deepmind.google/blog/context-third/</link>
<description>Context engineering matched evidence.</description></item>
</channel></rss>'''


class CaptureSelectionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name).resolve()
        self.config = config()
        self.config["schedules"][0].update(query="context engineering", primary_read_limit=2,
            primary_selection_profile=primary.SELECTION_PROFILE)
        self.config = load_config(json.dumps(self.config))
        self.store = Store(self.directory / "state", self.config, initialize=True)
        self.article_requests = []
        self.all_missing = False
        self.feed = ScriptedTransport(TransportResponse(200, (("Content-Type", "application/xml"),), FEED))
        original = retrieval_sources._adapter
        def collect(*args, **kwargs):
            def adapter(name, start, end, credential=None, **options):
                return original(name, start, end, credential, transport=self.feed,
                                resolver=lambda *_: ("93.184.216.34",), **options)
            with patch.object(retrieval_sources, "_adapter", side_effect=adapter):
                return retrieval_sources.collect(*args, **kwargs)
        test = self
        class Articles:
            def request(self, request):
                test.article_requests.append(request.url)
                missing = test.all_missing or request.url.endswith("context-first/")
                return TransportResponse(404 if missing else 200, (("Content-Type", "text/html"),),
                                         b"<html>Missing representation</html>" if missing else HTML)
        self.workflow = Workflow(self.store, ROOT, retrieval_source=collect,
            retrieval_verify=retrieval_sources.verify, primary_reader=fixture_reader(Articles()),
            primary_replayer=primary.verify_primary)
        network = patch("socket.socket.connect", side_effect=AssertionError("network forbidden"))
        network.start()
        self.addCleanup(network.stop)

    def run_job(self):
        manifest = make_manifest(ROOT, self.config, self.config["schedules"][0], fixture=True, window_end=DAY)
        self.store.enqueue("daily", manifest)
        result = self.workflow.drain()[0]
        self.assertNotIn("error", result)
        return result["result"]

    def test_first_404_and_second_success_retained_replayed_without_third_attempt(self):
        report = self.run_job()
        context = report["primary_context"]
        self.assertEqual((len(context["cards"]), len(context["gaps"])), (1, 1))
        self.assertEqual(context["gaps"][0]["error_code"], "HTTP_STATUS")
        self.assertEqual(context["selection_profile"], primary.SELECTION_PROFILE)
        self.assertEqual(len(self.article_requests), 2)
        self.assertEqual(len(set(self.article_requests)), 2)
        self.assertEqual(context["selection_omissions"][0]["reason"], "primary_read_limit")
        bundle = verified_bundle(self.store, "daily", now=DAY + 3600, fixture=True)
        self.assertEqual(bundle["retrieval_context"]["primary_cards"], 1)
        self.assertEqual(bundle["retrieval_context"]["primary_gaps"], 1)
        self.assertEqual(self.workflow.drain(), [])
        self.assertEqual((len(self.feed.requests), len(self.article_requests)), (1, 2))
        self.assertEqual(self.store.status()["usage"][0]["source_request_reservations"], 3)

    def test_two_404s_exhaust_slots_and_no_automatic_retry(self):
        self.all_missing = True
        report = self.run_job()
        self.assertEqual((len(report["primary_context"]["cards"]), len(report["primary_context"]["gaps"])), (0, 2))
        with self.assertRaisesRegex(ServiceError, "PRIMARY_REQUIRED"):
            verified_bundle(self.store, "daily", now=DAY + 3600, fixture=True)
        self.assertEqual(self.workflow.drain(), [])
        self.assertEqual(len(self.article_requests), 2)

    def test_profile_tampering_is_not_grandfathered_by_replay(self):
        self.run_job()
        with self.store._connect() as db:
            row = db.execute("SELECT output FROM steps WHERE job='daily' AND name='primary-selection'").fetchone()
            output = json.loads(row[0])
            output.pop("selection_profile")
            from researcher.service.contracts import digest
            db.execute("UPDATE steps SET output=?,output_digest=? WHERE job='daily' AND name='primary-selection'",
                       (json.dumps(output), digest(output)))
        with self.assertRaisesRegex(ServiceError, "SELECTION_MISMATCH"):
            verified_bundle(self.store, "daily", now=DAY + 3600, fixture=True)
        self.assertEqual(len(self.article_requests), 2)


class DiscoverySpacingTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name).resolve()
        self.clock = DAY + 3600
        timer = patch("researcher.service.store.time.time", side_effect=lambda: self.clock)
        timer.start()
        self.addCleanup(timer.stop)
        self.config = config()
        self.config["schedules"][0].update(sources=["arxiv"], source_queries={"arxiv": "agent memory"})
        self.store = Store(self.directory / "state", self.config, initialize=True)
        self.calls, self.waits = [], []
        self.store.claim_source("previous-primary", "arxiv", "previous", "primary-0")
        self.clock += 1
        manifest = make_manifest(ROOT, self.config, self.config["schedules"][0], window_end=DAY)
        self.store.enqueue("daily", manifest)

    def collect(self, name, query, directory, **kwargs):
        self.calls.append(name)
        return synthetic_lane(name, query, directory, **kwargs)

    def wait(self, seconds):
        self.waits.append(seconds)
        self.clock += seconds

    def run_job(self, *, collector=None, wait=None):
        workflow = Workflow(self.store, ROOT, live=True, retrieval_source=collector or self.collect,
            retrieval_verify=lambda *_a, **_k: None, primary_wait=wait or self.wait,
            credential=lambda *_: self.fail("credential lookup"))
        with patch("socket.socket.connect", side_effect=AssertionError("network forbidden")), \
             patch("time.sleep", side_effect=AssertionError("unbounded sleep")):
            rows = workflow.drain()
        return rows

    def test_previous_primary_spacing_waits_once_before_one_collector_call(self):
        result = self.run_job()[0]
        self.assertNotIn("error", result)
        self.assertEqual(self.waits, [3])
        self.assertEqual(self.calls, ["arxiv"])
        self.assertEqual(result["result"]["source_failures"], [])
        self.assertEqual(self.run_job(), [])
        self.assertEqual(self.store.status()["usage"][0]["source_request_reservations"], 1)

    def test_persistently_blocked_gate_never_dispatches_or_retries_on_restart(self):
        result = self.run_job(wait=self.waits.append)[0]["result"]
        self.assertEqual(self.waits, [3])
        self.assertEqual(self.calls, [])
        self.assertEqual(result["source_failures"][0]["error_code"], "SOURCE_RATE_LIMIT")
        self.assertEqual(result["source_failures"][0]["effect_state"], "failed")
        self.assertEqual(self.run_job(), [])
        self.assertEqual(self.store.status()["usage"][0]["source_request_reservations"], 1)

    def test_collector_failure_after_spacing_is_never_retried(self):
        def failure(*args, **kwargs):
            self.calls.append("attempted")
            raise LimitExceededError("TIME_LIMIT", "fixture timeout after dispatch")
        result = self.run_job(collector=failure)[0]["result"]
        self.assertEqual(self.waits, [3])
        self.assertEqual(self.calls, ["attempted"])
        self.assertEqual(result["source_failures"][0]["effect_state"], "unknown")
        self.assertEqual(self.run_job(collector=failure), [])
        self.assertEqual(self.calls, ["attempted"])

    def test_collector_spacing_named_error_is_not_a_second_dispatch_opportunity(self):
        def failure(*args, **kwargs):
            self.calls.append("attempted")
            raise ServiceError("SOURCE_RATE_LIMIT")
        self.run_job(collector=failure)
        self.assertEqual(self.waits, [3])
        self.assertEqual(self.calls, ["attempted"])
        self.assertEqual(self.run_job(collector=failure), [])
        self.assertEqual(self.calls, ["attempted"])

    def test_non_spacing_claim_error_is_not_waited_or_retried(self):
        with patch.object(self.store, "claim_source", side_effect=ServiceError("SOURCE_ALREADY_RESERVED")):
            result = self.run_job()[0]
        self.assertEqual(result["error"], "SOURCE_ALREADY_RESERVED")
        self.assertEqual((self.waits, self.calls), ([], []))


if __name__ == "__main__":
    unittest.main()
