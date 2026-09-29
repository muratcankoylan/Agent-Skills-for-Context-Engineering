"""End-to-end offline captures through a managed packet, never provider calls."""

from copy import deepcopy
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from researcher.scripts.schema_contract import canonicalize
from researcher.scripts.source_connectors import TransportResponse
from researcher.scripts.tests.test_source_connectors import ScriptedTransport
from researcher.service import retrieval_sources
from researcher.service.agents_context import compile_request
from researcher.service.agents_runtime import ManagedResearch, SessionLedger, main as managed_main
from researcher.service.contracts import ServiceError, digest
from researcher.service.retrieval_handoff import prepare_from_retrieval, verified_bundle
from researcher.service.store import Store
from researcher.service.tests.test_agents_runtime import FakeAgents
from researcher.service.tests.test_daily_retrieval import DAY, ROOT, config
from researcher.service.tests.test_primary_context import Transport, fixture_reader
from researcher.service.primary_context import verify_primary
from researcher.service.workflow import Workflow, make_manifest

FEED = b'''<rss><channel><item><title>Context engineering research</title>
<link>https://deepmind.google/blog/context-research/</link>
<description>Measured retrieval tests require a matched baseline.</description>
</item></channel></rss>'''


class RetrievalHandoffTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name).resolve()
        self.config = config()
        self.config["schedules"][0]["primary_read_limit"] = 1
        self.config["schedules"][0]["query"] = "context engineering"
        self.store = Store(self.directory / "source", self.config, initialize=True)
        self.destination = self.directory / "managed"
        self.network = patch("socket.socket.connect", side_effect=AssertionError("network forbidden"))
        self.network.start()
        self.addCleanup(self.network.stop)
        self.feed_transport = ScriptedTransport(
            TransportResponse(200, (("Content-Type", "application/xml"),), FEED))
        original = retrieval_sources._adapter

        def collect(*args, **kwargs):
            def adapter(name, start, end, credential=None, **options):
                return original(name, start, end, credential,
                    transport=self.feed_transport, resolver=lambda *a: ("93.184.216.34",), **options)
            with patch.object(retrieval_sources, "_adapter", side_effect=adapter):
                return retrieval_sources.collect(*args, **kwargs)

        self.article_transport = Transport()
        self.collect = collect
        self.manifest = make_manifest(ROOT, self.config, self.config["schedules"][0],
                                      fixture=True, window_end=DAY)
        self.store.enqueue("daily", self.manifest)
        result = Workflow(self.store, ROOT, retrieval_source=collect,
            retrieval_verify=retrieval_sources.verify,
            primary_reader=fixture_reader(self.article_transport),
            primary_replayer=verify_primary).drain()[0]
        self.assertNotIn("error", result)
        self.report = result["result"]

    def bundle(self, **kwargs):
        return verified_bundle(self.store, "daily", now=DAY + 3600, fixture=True, **kwargs)

    def prepare(self, **kwargs):
        return prepare_from_retrieval(self.store, "daily", ROOT, self.destination,
            model="gpt-6-astra", skills=["context-fundamentals"],
            now=DAY + 3600, fixture=True, **kwargs)

    def mutate_step(self, name, change, *, update_digest=False, change_effect=False):
        with sqlite3.connect(self.store.path) as db:
            value = json.loads(db.execute("SELECT output FROM steps WHERE job='daily' AND name=?", (name,)).fetchone()[0])
            change(value)
            raw = canonicalize(value).decode()
            db.execute("UPDATE steps SET output=? WHERE job='daily' AND name=?", (raw, name))
            if update_digest:
                db.execute("UPDATE steps SET output_digest=? WHERE job='daily' AND name=?", (digest(value), name))
            if change_effect:
                db.execute("UPDATE effects SET output=?,output_digest=? WHERE job='daily' AND name=?", (raw, digest(value), name))

    def test_capture_to_managed_packet_replays_without_network_or_budget_changes(self):
        before = self.store.inspect("daily")
        bundle = self.bundle()
        self.assertEqual(before, self.store.inspect("daily"))
        self.assertEqual(len(self.feed_transport.requests), 1)
        self.assertEqual(self.article_transport.calls, 1)
        self.assertGreaterEqual(len(bundle["evidence"]), 2)
        context = bundle["retrieval_context"]
        self.assertTrue(context["capture_replayed"])
        self.assertFalse(context["scientific_quality_assessed"])
        self.assertFalse(context["full_paper_verified"])
        link = context["primary_links"][0]
        self.assertEqual(link["discovery_id"], bundle["evidence"][0]["id"])
        self.assertEqual(link["excerpt_ids"], [row["id"] for row in bundle["evidence"][1:]])
        ledger = self.prepare()
        packet, state = ledger.load()
        self.assertEqual(state["phase"], "prepared")
        request_context = json.loads(packet["request"]["input"])
        self.assertEqual(request_context["retrieval_context"], context)
        self.assertIn("paired baseline", packet["request"]["agent"]["instructions"])
        self.assertNotIn(str(self.store.directory), packet["request"]["input"])
        self.assertNotIn('"captures"', packet["request"]["input"])
        self.assertNotIn('"source_url"', packet["request"]["input"])
        self.assertEqual(packet["request"]["agent"]["tools"],
                         [{"type": "programmatic_tool_calling", "enabled": False}])
        self.assertEqual(before, self.store.inspect("daily"))

    def test_fixture_cannot_dispatch_to_managed_runtime(self):
        ledger = self.prepare()
        packet, _ = ledger.load()
        client = FakeAgents(packet)
        with self.assertRaises(ServiceError):
            ManagedResearch(ledger, client).submit(live=True, acknowledge_cost_risk=True, max_seconds=30)
        self.assertEqual(client.create_count, 0)

    def test_duplicate_destination_is_not_overwritten_or_resumed(self):
        ledger = self.prepare()
        before = ledger.packet_path.read_bytes()
        with self.assertRaises(FileExistsError):
            self.prepare()
        self.assertEqual(before, ledger.packet_path.read_bytes())

    def test_live_fixture_mismatch_and_stale_future_windows_fail(self):
        with self.assertRaisesRegex(ServiceError, "FIXTURE_MISMATCH"):
            verified_bundle(self.store, "daily", now=DAY + 3600)
        for current in (DAY, DAY - 1, DAY + 172801):
            with self.subTest(now=current), self.assertRaisesRegex(ServiceError, "STALE"):
                verified_bundle(self.store, "daily", now=current, fixture=True)
        self.assertFalse(self.destination.exists())

    def test_nonterminal_partial_and_unknown_are_not_research_admission(self):
        for status in ("queued", "running", "failed", "reconciliation_required"):
            with sqlite3.connect(self.store.path) as db:
                db.execute("UPDATE jobs SET status=? WHERE id='daily'", (status,))
            with self.subTest(status=status), self.assertRaisesRegex(ServiceError, "INCOMPLETE"):
                self.prepare()
        self.assertFalse(self.destination.exists())

    def test_forged_terminal_state_cannot_hide_unknown_effect(self):
        with sqlite3.connect(self.store.path) as db:
            db.execute("UPDATE effects SET state='unknown' WHERE name='retrieval-deepmind'")
        with self.assertRaisesRegex(ServiceError, "EFFECT_INVALID"):
            self.prepare()

    def test_manifest_and_checkpoint_hash_tampering_fail(self):
        self.mutate_step("report", lambda v: v.update(evidence_qualified=True))
        with self.assertRaisesRegex(ServiceError, "DIGEST_MISMATCH"):
            self.prepare()

    def test_rehashed_report_invention_fails_reconstruction(self):
        self.mutate_step("report", lambda v: v.update(evidence_qualified=True), update_digest=True)
        with self.assertRaisesRegex(ServiceError, "REPORT_MISMATCH"):
            self.prepare()

    def test_rehashed_source_invention_fails_actual_capture_replay(self):
        self.mutate_step("retrieval-deepmind", lambda v: v["evidence"][0].update(url="https://example.org/invented"),
                         update_digest=True, change_effect=True)
        with self.assertRaisesRegex(ServiceError, "SOURCE_REPLAY_MISMATCH"):
            self.prepare()

    def test_rehashed_primary_span_invention_fails_replay(self):
        self.mutate_step("primary-0", lambda v: v["article"].update(text="invented"),
                         update_digest=True, change_effect=True)
        with self.assertRaisesRegex(ServiceError, "PRIMARY_REPLAY_INVALID"):
            self.prepare()

    def test_missing_primary_checkpoint_fails_before_ledger_creation(self):
        with sqlite3.connect(self.store.path) as db:
            db.execute("DELETE FROM steps WHERE name='primary-0'")
        with self.assertRaisesRegex(ServiceError, "CHECKPOINT_MISSING"):
            self.prepare()
        self.assertFalse(self.destination.exists())

    def test_effect_checkpoint_disagreement_fails(self):
        self.mutate_step("retrieval-deepmind", lambda v: v.update(next_cursor="invented"), update_digest=True)
        with self.assertRaisesRegex(ServiceError, "EFFECT_MISMATCH"):
            self.prepare()

    def test_read_requires_exact_checkpoint_input_binding(self):
        with sqlite3.connect(self.store.path) as db:
            db.execute("UPDATE steps SET input_digest=? WHERE name='primary-context'", (digest({}),))
        with self.assertRaisesRegex(ServiceError, "INPUT_CHANGED"):
            self.prepare()

    def test_no_primary_card_is_explicit_abstention_gate(self):
        self.config["schedules"][0]["primary_read_limit"] = 0
        self.store = Store(self.directory / "abstract-only", self.config, initialize=True)
        manifest = make_manifest(ROOT, self.config, self.config["schedules"][0],
                                 fixture=True, window_end=DAY)
        self.store.enqueue("daily", manifest)
        # A captured/replayed empty feed has no primary candidate to read.
        original = retrieval_sources._adapter
        transport = ScriptedTransport(TransportResponse(200,
            (("Content-Type", "application/xml"),), b"<rss><channel/></rss>"))
        def collect(*args, **kwargs):
            def adapter(name, start, end, credential=None, **options):
                return original(name, start, end, credential, transport=transport,
                                resolver=lambda *a: ("93.184.216.34",), **options)
            with patch.object(retrieval_sources, "_adapter", side_effect=adapter):
                return retrieval_sources.collect(*args, **kwargs)
        result = Workflow(self.store, ROOT, retrieval_source=collect,
                          retrieval_verify=retrieval_sources.verify).drain()[0]
        self.assertNotIn("error", result)
        with self.assertRaisesRegex(ServiceError, "PRIMARY_REQUIRED"):
            self.prepare()
        self.assertFalse(self.destination.exists())

    def test_two_papers_keep_disjoint_parent_links_without_titles_in_excerpts(self):
        self.config["schedules"][0]["primary_read_limit"] = 2
        self.store = Store(self.directory / "two-papers", self.config, initialize=True)
        feed = FEED.replace(b"</channel>", b'''<item><title>Context engineering comparison</title>
            <link>https://arxiv.org/abs/2609.00001v1</link>
            <description>Context research second observation.</description></item></channel>''')
        self.feed_transport = ScriptedTransport(TransportResponse(200,
            (("Content-Type", "application/xml"),), feed))
        manifest = make_manifest(ROOT, self.config, self.config["schedules"][0],
                                 fixture=True, window_end=DAY)
        self.store.enqueue("daily", manifest)
        result = Workflow(self.store, ROOT, retrieval_source=self.collect,
            retrieval_verify=retrieval_sources.verify,
            primary_reader=fixture_reader(Transport(body=b"<article><p>Context measurement without title.</p></article>")),
            primary_replayer=verify_primary).drain()[0]
        self.assertNotIn("error", result)
        bundle = self.bundle()
        links = bundle["retrieval_context"]["primary_links"]
        self.assertEqual(len(links), 2)
        self.assertEqual(len({link["discovery_id"] for link in links}), 2)
        self.assertFalse(set(links[0]["excerpt_ids"]) & set(links[1]["excerpt_ids"]))
        packet, _ = self.prepare().load()
        self.assertEqual(json.loads(packet["request"]["input"])["retrieval_context"]["primary_links"], links)

    def test_unknown_extra_effect_blocks_preparation(self):
        with sqlite3.connect(self.store.path) as db:
            db.execute("INSERT INTO effects SELECT job,'unexpected',input_digest,state,day,model_calls,"
                       "source_requests,reserved_microusd,output,output_digest,reason FROM effects "
                       "WHERE name='retrieval-deepmind'")
        with self.assertRaisesRegex(ServiceError, "UNEXPECTED_EFFECT"):
            self.prepare()

    def test_primary_parent_link_invention_fails_compilation(self):
        packet, _ = self.prepare().load()
        changed = deepcopy(packet["retrieval_context"])
        changed["primary_links"][0]["discovery_id"] = "context_" + "0" * 64
        with self.assertRaisesRegex(ServiceError, "LINK_INVALID"):
            compile_request(model=packet["model"], query=packet["query"], corpus=packet["corpus"],
                            evidence=packet["evidence"], retrieval_context=changed)

    def test_prepared_context_expiry_is_checked_before_remote_submission(self):
        ledger = self.prepare()
        packet, _ = ledger.load()
        # Live shape in a separate local fixture, never an actual API client.
        packet["fixture"] = packet["retrieval_context"]["fixture"] = False
        packet["request"] = compile_request(model=packet["model"], query=packet["query"],
            corpus=packet["corpus"], evidence=packet["evidence"],
            retrieval_context=packet["retrieval_context"])
        ledger = SessionLedger.prepare(self.directory / "expired", packet)
        client = FakeAgents(packet)
        for now in (DAY + 172801, DAY + 3599):
            with self.subTest(now=now), self.assertRaisesRegex(ServiceError, "STALE"):
                ManagedResearch(ledger, client, clock=lambda: now).submit(
                    live=True, acknowledge_cost_risk=True, max_seconds=30)
        self.assertEqual(client.create_count, 0)
        self.assertEqual(ledger.status()["phase"], "prepared")

    def test_context_binding_and_fixture_cannot_be_changed_after_preparation(self):
        ledger = self.prepare()
        packet, _ = ledger.load()
        for key, value in (("evidence_digest", digest([])), ("full_paper_verified", True),
                           ("authority", "accepted"), ("window_end", DAY + 1)):
            changed = deepcopy(packet["retrieval_context"])
            changed[key] = value
            with self.subTest(key=key), self.assertRaises(ServiceError):
                compile_request(model=packet["model"], query=packet["query"], corpus=packet["corpus"],
                    evidence=packet["evidence"], retrieval_context=changed)
        changed = deepcopy(packet)
        changed["fixture"] = False
        with self.assertRaisesRegex(ServiceError, "FIXTURE_MISMATCH"):
            SessionLedger.prepare(self.directory / "forged", changed)

    def test_env_file_blank_cannot_fall_back_to_process(self):
        self.prepare()
        with patch("researcher.service.environment.read_env_file", return_value={"OPENAI_API_KEY": ""}), \
             patch.dict("os.environ", {"OPENAI_API_KEY": "not-a-real-key"}), \
             patch("researcher.service.openai_agents.AgentsClient", side_effect=AssertionError("client")), \
             patch("sys.stdout", new_callable=io.StringIO) as output:
            code = managed_main(["observe", "--state", str(self.destination),
                                 "--env-file", str(self.directory / "env")])
        self.assertEqual(code, 1)
        self.assertIn("CREDENTIAL_UNAVAILABLE", output.getvalue())


if __name__ == "__main__":
    unittest.main()
