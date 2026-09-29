from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from researcher.scripts import research_sourcing as sourcing
from researcher.scripts.local_rehearsal import RehearsalError
from researcher.scripts.tests.test_source_connectors import (
    ScriptedTransport,
    atom_feed,
    atom_entry,
    response,
    resolver_for,
)


def brief():
    return {
        "schema": sourcing.SCHEMA,
        "question": "How can agent memory fail?",
        "skills": ["memory-systems"],
        "lanes": [
            {
                "id": "control",
                "facet": "Original information need",
                "source": "arxiv",
                "query": "agent memory",
                "match": "terms",
                "sort": "relevance",
            },
            {
                "id": "industry",
                "facet": "Publisher discovery window",
                "source": "microsoft_research",
                "query": "",
                "match": "terms",
                "sort": "submittedDate",
            },
        ],
        "x_queries": ['"agent memory" has:links -is:retweet'],
    }


class SourcingPlanTests(unittest.TestCase):
    def test_explicit_lanes_budget_and_disabled_x(self):
        plan = sourcing.build_plan(brief())
        self.assertEqual(plan["budget"]["max_http_attempts"], 9)
        self.assertEqual(plan["budget"]["max_response_bytes"], 1_000_000)
        self.assertEqual(plan["budget"]["paid_calls"], 0)
        self.assertFalse(plan["x"]["execution_enabled"])
        self.assertEqual(plan["lanes"][1]["query"], "")

    def test_duplicate_and_fabricated_feed_query_rejected(self):
        value = brief()
        duplicate = dict(value["lanes"][0], id="duplicate")
        value["lanes"].append(duplicate)
        with self.assertRaises(sourcing.SourcingError):
            sourcing.build_plan(value)
        value = brief()
        value["lanes"][1]["query"] = "pretend this searches a whole company"
        with self.assertRaises(sourcing.SourcingError):
            sourcing.build_plan(value)

    def test_invalid_boundary_never_executes(self):
        variants = []
        for field, bad in [
            ("schema", "other"),
            ("skills", "memory-systems"),
            ("max_packet_bytes", True),
            ("max_packet_bytes", 999999),
            ("question", "x\x00y"),
            ("question", "😀" * 600),
            ("x_queries", ["x" * 513]),
        ]:
            candidate = brief()
            candidate[field] = bad
            variants.append(candidate)
        for field, bad in [
            ("source", "x"),
            ("source", "http://127.0.0.1"),
            ("id", "../../escape"),
            ("sort", "arbitrary"),
            ("query", ""),
            ("facet", ""),
        ]:
            candidate = brief()
            candidate["lanes"][0][field] = bad
            variants.append(candidate)
        with patch.object(sourcing.pipeline, "run_pipeline") as execute:
            for candidate in variants:
                with (
                    self.subTest(candidate=candidate),
                    self.assertRaises(sourcing.SourcingError),
                ):
                    sourcing.run_sourcing(candidate, Path("unused"), live=True)
            execute.assert_not_called()

    def test_plan_preserves_literal_query_no_generated_expansion(self):
        value = brief()
        value["lanes"][0]["query"] = 'NOT author:"somebody" OR memory'
        plan = sourcing.build_plan(value)
        self.assertEqual(plan["lanes"][0]["query"], value["lanes"][0]["query"])
        self.assertEqual(len(plan["lanes"]), 2)

    def test_missing_optin_has_zero_network(self):
        with patch.object(sourcing.pipeline, "run_pipeline") as execute:
            with self.assertRaises(sourcing.SourcingError):
                sourcing.run_sourcing(brief(), Path("unused"))
            execute.assert_not_called()

    def test_compact_plan_is_explicit_and_typed(self):
        self.assertNotIn("compact", sourcing.build_plan(brief()))
        value = brief()
        value["compact"] = True
        self.assertTrue(sourcing.build_plan(value)["compact"])
        value["compact"] = 1
        with self.assertRaises(sourcing.SourcingError):
            sourcing.build_plan(value)


class SourcingPolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.cache = Path(self.temp.name).resolve()

    def test_reservation_survives_failure_and_denies_duplicate(self):
        with self.assertRaises(RuntimeError):
            with sourcing._arxiv_gate(self.cache, {"query": "one"}, "key"):
                raise RuntimeError("unknown transport outcome")
        with self.assertRaises(sourcing.SourcingError):
            with sourcing._arxiv_gate(self.cache, {"query": "one"}, "other-key"):
                self.fail("duplicate admitted")

    def test_different_query_waits_three_seconds(self):
        with patch.object(sourcing.time, "time_ns", return_value=100_000_000_000):
            with sourcing._arxiv_gate(self.cache, {"query": "one"}, "key1"):
                pass
        with (
            patch.object(sourcing.time, "time_ns", return_value=101_000_000_000),
            patch.object(sourcing.time, "sleep") as sleep,
        ):
            with sourcing._arxiv_gate(self.cache, {"query": "two"}, "key2"):
                pass
            sleep.assert_called_once_with(2.001)

    def test_clock_rollback_denies(self):
        with patch.object(sourcing.time, "time_ns", return_value=100_000_000_000):
            with sourcing._arxiv_gate(self.cache, {"query": "one"}, "key1"):
                pass
        with patch.object(sourcing.time, "time_ns", return_value=99_000_000_000):
            with self.assertRaises(sourcing.SourcingError):
                with sourcing._arxiv_gate(self.cache, {"query": "two"}, "key2"):
                    self.fail("clock rollback admitted")

    def test_brief_duplicate_keys_and_symlink_rejected(self):
        path = self.cache / "brief.json"
        path.write_text('{"schema": "one", "schema": "two"}')
        with self.assertRaises(sourcing.SourcingError):
            sourcing._load(path)
        link = self.cache / "alias.json"
        link.symlink_to(path)
        with self.assertRaises(OSError):
            sourcing._load(link)

    def test_shared_cache_owner_is_exclusive(self):
        with sourcing._run_lock(self.cache):
            with self.assertRaises(RehearsalError):
                with sourcing._run_lock(self.cache):
                    self.fail("concurrent supervisor admitted")

    def test_public_cache_rejected_without_chmod(self):
        path = self.cache / "public"
        path.mkdir(mode=0o755)
        with self.assertRaises(sourcing.SourcingError):
            sourcing._private(path)
        self.assertEqual(path.stat().st_mode & 0o777, 0o755)


class SourcingIntegrationTests(unittest.TestCase):
    """Scripted network fixtures only; no returned record is a live benchmark."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.cache = self.root / "cache"
        self.output = self.root / "campaign"
        self.value = brief()
        self.value["lanes"] = self.value["lanes"][:1]
        self.body = atom_feed(
            atom_entry("Memory experiment", "https://arxiv.org/abs/2501.00001v2")
        )
        self.transport = ScriptedTransport(response(self.body, "application/atom+xml"))
        original = sourcing.pipeline._adapter

        def factory(name, sink, **kwargs):
            if "transport" not in kwargs:
                kwargs.update(
                    transport=self.transport,
                    resolver=resolver_for("export.arxiv.org", "huggingface.co"),
                )
            return original(name, sink, **kwargs)

        self.mock = patch.object(sourcing.pipeline, "_adapter", side_effect=factory)
        self.mock.start()
        self.addCleanup(self.mock.stop)

    def run_once(self, output=None):
        return sourcing.run_sourcing(
            self.value, output or self.output, live=True, cache_dir=self.cache
        )

    def test_capture_to_packet_exact_resume_and_cross_campaign_cache(self):
        result = self.run_once()
        self.assertEqual(len(self.transport.requests), 1)
        self.assertEqual(result, self.run_once())
        second = self.run_once(self.root / "second")
        self.assertEqual(second["children"], result["children"])
        self.assertEqual(len(self.transport.requests), 1)
        self.assertTrue((self.output / "discovery-packet.json").is_file())

    def test_changed_campaign_intent_denied_without_network(self):
        self.run_once()
        self.value["lanes"][0]["query"] = "different query"
        with self.assertRaises(sourcing.SourcingError):
            self.run_once()
        self.assertEqual(len(self.transport.requests), 1)

    def test_compact_campaign_resume_verifies_referenced_provenance(self):
        self.value["compact"] = True
        result = self.run_once()
        self.assertEqual(result, self.run_once())
        packet = sourcing._load(self.output / "discovery-packet.json")
        self.assertEqual(packet["schema"], "local-research-discovery/v2")
        self.assertEqual(len(self.transport.requests), 1)

    def test_lost_child_does_not_trigger_network_in_completed_campaign(self):
        result = self.run_once()
        child = self.cache / result["children"][0]["cache_key"] / "observation.json"
        child.rename(child.with_name("lost-observation.json"))
        with self.assertRaises(sourcing.SourcingError):
            self.run_once()
        self.assertEqual(len(self.transport.requests), 1)

    def test_packet_tamper_fails_without_network(self):
        self.run_once()
        path = self.output / "discovery-packet.json"
        value = sourcing._load(path)
        value["accepted_claims"] = 99
        sourcing._write(path, value)
        with self.assertRaises(sourcing.SourcingError):
            self.run_once()
        self.assertEqual(len(self.transport.requests), 1)

    def test_unfinished_campaign_lost_child_does_not_refetch(self):
        self.value["lanes"] = [
            dict(
                id="company",
                facet="Publisher window",
                source="huggingface",
                query="",
                match="terms",
                sort="submittedDate",
            )
        ]
        self.transport = ScriptedTransport(
            response(
                atom_feed(atom_entry("Publisher", "https://huggingface.co/blog/paper")),
                "application/atom+xml",
            )
        )
        with patch.object(
            sourcing, "build_discovery_packet", side_effect=RuntimeError("interrupt")
        ):
            with self.assertRaises(RuntimeError):
                self.run_once()
        marker = sourcing._load(self.output / "lane-company.json")
        child = self.cache / marker["cache_key"]
        child.rename(self.root / "lost-child")
        with self.assertRaises(sourcing.SourcingError):
            self.run_once()
        self.assertEqual(len(self.transport.requests), 1)

    def test_company_window_integrates_without_sending_question(self):
        self.value["lanes"] = [
            dict(
                id="company",
                facet="Publisher window",
                source="huggingface",
                query="",
                match="terms",
                sort="submittedDate",
            )
        ]
        self.transport = ScriptedTransport(
            response(
                atom_feed(
                    atom_entry("Publisher entry", "https://huggingface.co/blog/paper")
                ),
                "application/atom+xml",
            )
        )
        result = self.run_once()
        record = sourcing.pipeline.read_verified_observation(
            self.cache / result["children"][0]["cache_key"]
        )
        self.assertEqual(record["sources"][0]["source"], "huggingface")
        self.assertEqual(
            self.transport.requests[0].url, "https://huggingface.co/blog/feed.xml"
        )
        self.assertEqual(len(record["sources"][0]["leads"]), 1)

    def test_primary_read_rejects_unrelated_url_before_fetch(self):
        self.run_once()
        with patch.object(sourcing, "retrieve_article") as fetch:
            with self.assertRaises(sourcing.SourcingError):
                sourcing.read_primary(
                    self.output, "https://arxiv.org/html/2501.99999", live=True
                )
            fetch.assert_not_called()

    def test_explicit_discovered_primary_read_and_replay(self):
        from researcher.scripts.research_articles import retrieve_article

        self.run_once()
        transport = ScriptedTransport(
            response(
                b"<html><article><h1>Paper</h1><p>Bound evidence.</p></article></html>",
                "text/html",
            )
        )

        def fetch(url, store):
            return retrieve_article(
                url, store, transport=transport, resolver=resolver_for("arxiv.org")
            )

        with (
            patch.object(sourcing, "retrieve_article", side_effect=fetch),
            patch.object(sourcing.time, "sleep"),
        ):
            result = sourcing.read_primary(
                self.output, "https://arxiv.org/html/2501.00001v2", live=True
            )
            self.assertEqual(result["status"], "observed")
            self.assertEqual(
                result,
                sourcing.read_primary(
                    self.output, "https://arxiv.org/html/2501.00001v2", live=True
                ),
            )
        self.assertEqual(len(transport.requests), 1)
        self.assertTrue(result["input"]["selected_from"])
        with patch.object(
            sourcing,
            "retrieve_article",
            side_effect=AssertionError("offline re-extraction attempted HTTP"),
        ):
            extracted = sourcing.read_primary(
                self.output, "https://arxiv.org/html/2501.00001v2", reextract=True
            )
            self.assertEqual(extracted["new_http_attempts"], 0)
            self.assertEqual(extracted["article"], result["article"])
            self.assertEqual(
                extracted,
                sourcing.read_primary(
                    self.output, "https://arxiv.org/html/2501.00001v2", reextract=True
                ),
            )
        saved = next((self.output / "articles").glob("*/result.json"))
        forged = sourcing._load(saved)
        forged.update(authority="production", production_ready=True, schema="forged")
        sourcing._write(saved, forged)
        with self.assertRaises(sourcing.SourcingError):
            sourcing.read_primary(
                self.output, "https://arxiv.org/html/2501.00001v2", live=True
            )
        self.assertEqual(len(transport.requests), 1)


if __name__ == "__main__":
    unittest.main()
