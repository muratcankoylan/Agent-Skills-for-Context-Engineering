"""Opt-in larger primary reads through actual fixture capture and handoff."""

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from researcher.scripts import research_articles_large as large
from researcher.scripts.tests.test_research_articles import FakeTransport, public_resolver
from researcher.scripts.tests.test_research_articles_large import html_bytes
from researcher.scripts.source_connectors import TransportResponse
from researcher.scripts.tests.test_source_connectors import ScriptedTransport
from researcher.service import primary_context, retrieval_sources
from researcher.service.contracts import ServiceError, load_config
from researcher.service.primary_context import collect_primary, verify_primary
from researcher.service.retrieval_handoff import verified_bundle
from researcher.service.store import Store
from researcher.service.tests.test_daily_retrieval import DAY, ROOT, config
from researcher.service.tests.test_retrieval_handoff import FEED
from researcher.service.workflow import Workflow, make_manifest

URL = "https://deepmind.google/blog/context-research/"


class PrimaryProfileTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name).resolve()
        self.config = config()
        self.config["schedules"][0].update(query="context engineering", primary_read_limit=1,
                                           primary_read_profile=large.PROFILE)
        self.config = load_config(json.dumps(self.config))
        network = patch("socket.socket.connect", side_effect=AssertionError("network forbidden"))
        network.start()
        self.addCleanup(network.stop)
        self.article_transport = FakeTransport(html_bytes(665363))
        self.feed_transport = ScriptedTransport(
            TransportResponse(200, (("Content-Type", "application/xml"),), FEED))

    def reader(self, url, directory, *, profile=None):
        retrieve = large.retrieve_article
        def captured(url, store):
            return retrieve(url, store, transport=self.article_transport, resolver=public_resolver)
        with patch.object(large, "retrieve_article", side_effect=captured):
            return collect_primary(url, directory, profile=profile)

    def collect(self, *args, **kwargs):
        original = retrieval_sources._adapter
        def adapter(name, start, end, credential=None, **options):
            return original(name, start, end, credential, transport=self.feed_transport,
                            resolver=public_resolver, **options)
        with patch.object(retrieval_sources, "_adapter", side_effect=adapter):
            return retrieval_sources.collect(*args, **kwargs)

    def test_optional_profile_is_validated_without_default_config_mutation(self):
        original = config()
        self.assertNotIn("primary_read_profile", original["schedules"][0])
        self.assertEqual(load_config(json.dumps(original)), original)
        for changes in ({"primary_read_profile": "unlimited"}, {"primary_read_profile": True},
                        {"primary_read_limit": 0}, {"primary_read_profile": None}):
            value = deepcopy(self.config)
            value["schedules"][0].update(changes)
            with self.subTest(changes=changes), self.assertRaises(ServiceError):
                load_config(json.dumps(value))

    def test_outcome_requires_matching_profile_and_both_reader_hashes(self):
        destination = self.directory / "captures"
        outcome = self.reader(URL, destination, profile=large.PROFILE)
        self.assertEqual(outcome["schema"], "primary-read-outcome/v2")
        self.assertEqual(outcome["reader_policy"], large.policy_binding())
        verify_primary(URL, outcome, destination, profile=large.PROFILE)
        with self.assertRaises(ServiceError):
            verify_primary(URL, outcome, destination)
        for key in ("reader_sha256", "base_reader_sha256", "profile"):
            changed = deepcopy(outcome)
            changed["reader_policy"][key] = "changed"
            with self.subTest(key=key), self.assertRaises(ServiceError):
                verify_primary(URL, changed, destination, profile=large.PROFILE)
        changed = deepcopy(outcome)
        changed["article"]["limits"]["max_bytes"] = 500000
        with self.assertRaises(ServiceError):
            verify_primary(URL, changed, destination, profile=large.PROFILE)

    def test_service_rejects_honest_but_different_lower_reader_limits(self):
        from researcher.scripts.research_evidence import LocalResearchEvidenceStore
        destination = self.directory / "captures"
        article = large.retrieve_article(URL, LocalResearchEvidenceStore(destination),
            transport=self.article_transport, resolver=public_resolver,
            limits=large.ArticleLimits(max_bytes=700000))
        outcome = {**primary_context.outcome_base(URL, large.PROFILE),
                   "state": "observed", "article": article}
        with self.assertRaises(ServiceError):
            verify_primary(URL, outcome, destination, profile=large.PROFILE)

    def test_bad_profile_does_not_create_capture_state(self):
        destination = self.directory / "absent"
        with self.assertRaises(ServiceError):
            collect_primary(URL, destination, profile="unlimited")
        self.assertFalse(destination.exists())
        self.assertFalse(self.article_transport.requests)

    def test_large_failure_and_deferred_outcomes_are_profile_bound(self):
        self.article_transport = FakeTransport(html_bytes(665363), truncated=True)
        destination = self.directory / "captures"
        outcome = self.reader(URL, destination, profile=large.PROFILE)
        self.assertEqual(outcome["state"], "unavailable")
        self.assertEqual(outcome["error_code"], "TRUNCATED_RESPONSE")
        verify_primary(URL, outcome, destination, profile=large.PROFILE)
        deferred = {**primary_context.outcome_base(URL, large.PROFILE),
                    "state": "deferred", "error_code": "LOCAL_ARXIV_SPACING"}
        verify_primary(URL, deferred, destination, profile=large.PROFILE)
        with self.assertRaises(ServiceError):
            verify_primary(URL, deferred, destination)

    def test_workflow_and_handoff_bind_same_large_policy_and_resume_without_calls(self):
        store = Store(self.directory / "source", self.config, initialize=True)
        manifest = make_manifest(ROOT, self.config, self.config["schedules"][0],
                                 fixture=True, window_end=DAY)
        store.enqueue("daily", manifest)
        runner = Workflow(store, ROOT, retrieval_source=self.collect,
            retrieval_verify=retrieval_sources.verify, primary_reader=self.reader,
            primary_replayer=verify_primary)
        result = runner.drain()[0]
        self.assertNotIn("error", result)
        self.assertEqual(result["result"]["primary_context"]["cards"][0]["reader_policy"],
                         large.policy_binding())
        before = store.inspect("daily")
        bundle = verified_bundle(store, "daily", now=DAY + 3600, fixture=True)
        self.assertEqual(bundle["retrieval_context"]["primary_cards"], 1)
        self.assertTrue(bundle["retrieval_context"]["capture_replayed"])
        self.assertFalse(bundle["retrieval_context"]["full_paper_verified"])
        self.assertEqual(before, store.inspect("daily"))
        self.assertEqual(len(self.feed_transport.requests), 1)
        self.assertEqual(len(self.article_transport.requests), 1)
        self.assertEqual(self.article_transport.requests[0].max_bytes, 1500000)
        self.assertEqual(runner.drain(), [])
        self.assertEqual(verified_bundle(store, "daily", now=DAY + 3600, fixture=True), bundle)
        self.assertEqual(store.status()["usage"][0]["source_request_reservations"], 2)
        self.assertEqual(store.status()["usage"][0]["model_calls"], 0)
        self.assertEqual(store.status()["usage"][0]["reserved_microusd"], 0)
        self.assertEqual(len(self.article_transport.requests), 1)
        with patch.object(primary_context.large_articles, "policy_binding", return_value={
                **large.policy_binding(), "reader_sha256": "sha256:" + "0" * 64}):
            with self.assertRaisesRegex(ServiceError, "INPUT_CHANGED"):
                verified_bundle(store, "daily", now=DAY + 3600, fixture=True)


if __name__ == "__main__":
    unittest.main()
