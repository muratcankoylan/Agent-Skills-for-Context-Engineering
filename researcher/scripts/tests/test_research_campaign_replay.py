"""Offline campaign provenance replay, never live research evidence."""

from __future__ import annotations

import copy
import os
import unittest
from contextlib import ExitStack
from unittest.mock import patch

from researcher.scripts import research_sourcing as sourcing
from researcher.scripts.schema_contract import canonicalize, sha256_bytes
from researcher.scripts.tests import test_research_sourcing as fixtures


class CampaignReplayTests(unittest.TestCase):
    setUp = fixtures.SourcingIntegrationTests.setUp
    run_once = fixtures.SourcingIntegrationTests.run_once

    def verify(self):
        with ExitStack() as stack:
            for target in (
                "socket.getaddrinfo",
                "socket.socket.connect",
                "researcher.scripts.research_sourcing.run_sourcing",
                "researcher.scripts.research_pipeline.run_pipeline",
                "researcher.scripts.research_sourcing.build_context_pack",
                "researcher.scripts.research_pipeline._implementation_identity",
            ):
                stack.enter_context(patch(target, side_effect=AssertionError(target)))
            return sourcing.verify_sourcing_campaign(self.output)

    def snapshot(self):
        return {
            path.relative_to(self.root).as_posix(): (
                path.stat().st_mode,
                path.stat().st_mtime_ns,
                path.read_bytes() if path.is_file() else None,
            )
            for path in self.root.rglob("*")
        }

    def test_complete_capture_replay_is_read_only_and_preserves_historical_identity(
        self,
    ):
        result = self.run_once()
        before = self.snapshot()
        replay = self.verify()
        self.assertEqual(set(replay), {"manifest", "result", "observations", "packet"})
        self.assertEqual(canonicalize(replay["result"]), canonicalize(result))
        self.assertEqual(replay["observations"][0]["record"]["query"], "agent memory")
        self.assertEqual(
            replay["packet"], sourcing._load(self.output / "discovery-packet.json")
        )
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(len(self.transport.requests), 1)

    def test_company_window_and_compact_packet_replay(self):
        self.value["compact"] = True
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
        self.transport = fixtures.ScriptedTransport(
            fixtures.response(
                fixtures.atom_feed(
                    fixtures.atom_entry(
                        "Publisher research", "https://huggingface.co/blog/research"
                    )
                ),
                "application/atom+xml",
            )
        )
        result = self.run_once()
        before = self.snapshot()
        replay = self.verify()
        self.assertEqual(replay["result"], result)
        self.assertEqual(replay["packet"]["schema"], "local-research-discovery/v2")
        self.assertEqual(replay["observations"][0]["query"], "")
        self.assertEqual(
            replay["observations"][0]["record"]["query"], self.value["question"]
        )
        self.assertEqual(before, self.snapshot())

    def test_complete_result_envelope_rejects_authority_types_and_child_misbindings(
        self,
    ):
        original = self.run_once()
        variants = []
        for field, bad in (
            ("schema", "forged"),
            ("authority", "accepted"),
            ("model_calls", 1),
            ("model_calls", False),
            ("paid_calls", False),
            ("production_ready", 0),
            ("production_ready", True),
            ("unknown", "not admitted"),
        ):
            value = copy.deepcopy(original)
            value[field] = bad
            variants.append(value)
        for field, bad in (
            ("lane_id", "other"),
            ("run_id", "00000000-0000-0000-0000-000000000000"),
            ("cache_key", "other"),
            ("record_sha256", "sha256:" + "0" * 64),
        ):
            value = copy.deepcopy(original)
            value["children"][0][field] = bad
            variants.append(value)
        value = copy.deepcopy(original)
        value["x"]["execution_enabled"] = 0
        variants.append(value)
        for value in variants:
            with self.subTest(result=value):
                sourcing._write(self.output / "result.json", value)
                before = self.snapshot()
                with self.assertRaises(sourcing.SourcingError):
                    self.verify()
                self.assertEqual(before, self.snapshot())

    def test_missing_lane_or_lock_is_not_recreated(self):
        self.run_once()
        for path in (
            self.output / "lane-control.json",
            self.output / ".run.lock",
            self.cache / ".run.lock",
        ):
            with self.subTest(path=path.name):
                backup = path.with_name(path.name + ".retained")
                path.rename(backup)
                before = self.snapshot()
                with self.assertRaises(sourcing.SourcingError):
                    self.verify()
                self.assertEqual(before, self.snapshot())
                self.assertFalse(path.exists())
                backup.rename(path)

    def test_missing_campaign_is_not_created(self):
        with self.assertRaises(sourcing.SourcingError):
            self.verify()
        self.assertFalse(self.output.exists())

    def test_changed_lane_intent_or_plan_fails(self):
        self.run_once()
        path = self.output / "lane-control.json"
        original = sourcing._load(path)
        for value in (
            dict(original, cache_key="other"),
            dict(original, manifest_sha256="sha256:" + "0" * 64),
            dict(original, authority="none"),
        ):
            sourcing._write(path, value)
            with self.assertRaises(sourcing.SourcingError):
                self.verify()
        sourcing._write(path, original)
        path = self.output / "manifest.json"
        original = sourcing._load(path)
        for field, value in (("authority", "accepted"), ("budget", {"model_calls": 1})):
            manifest = copy.deepcopy(original)
            manifest["identity"]["plan"][field] = value
            sourcing._write(path, manifest)
            with self.assertRaises(sourcing.SourcingError):
                self.verify()

    def test_aliased_or_hardlinked_campaign_data_is_rejected(self):
        self.run_once()
        for relative in (
            "manifest.json",
            "lane-control.json",
            "result.json",
            "discovery-packet.json",
        ):
            path = self.output / relative
            saved = path.with_name(relative + ".retained")
            path.rename(saved)
            for hardlink in (False, True):
                with self.subTest(relative=relative, hardlink=hardlink):
                    if hardlink:
                        os.link(saved, path)
                    else:
                        path.symlink_to(saved)
                    with self.assertRaises(sourcing.SourcingError):
                        self.verify()
                    path.unlink()
            saved.rename(path)

    def test_unrelated_valid_child_cannot_be_relabelled_as_campaign_lane(self):
        original = self.run_once()
        # Same visible query, different provider selection semantics: the packet
        # can reconstruct successfully, but this is not the requested source run.
        self.value["lanes"][0]["sort"] = "lastUpdatedDate"
        self.transport = fixtures.ScriptedTransport(
            fixtures.response(self.body, "application/atom+xml")
        )
        with patch.object(sourcing.time, "sleep"):
            unrelated = self.run_once(self.root / "unrelated-campaign")
        record = sourcing.pipeline.read_verified_observation(
            self.cache / unrelated["children"][0]["cache_key"]
        )
        manifest = sourcing._load(self.output / "manifest.json")
        lane = manifest["identity"]["plan"]["lanes"][0]
        observations = [
            {
                "lane_id": lane["id"],
                "facet": lane["facet"],
                "query": lane["query"],
                "record": record,
            }
        ]
        packet = sourcing.build_discovery_packet(
            manifest["identity"]["plan"]["question"],
            observations,
            max_bytes=manifest["identity"]["plan"]["max_packet_bytes"],
        )
        substituted = copy.deepcopy(original)
        substituted["children"] = unrelated["children"]
        substituted["packet_sha256"] = sha256_bytes(canonicalize(packet))
        sourcing._write(self.output / "result.json", substituted)
        sourcing._write(self.output / "discovery-packet.json", packet)
        sourcing._write(
            self.output / "lane-control.json",
            {
                "manifest_sha256": sha256_bytes(canonicalize(manifest)),
                "cache_key": unrelated["children"][0]["cache_key"],
            },
        )
        with self.assertRaises(sourcing.SourcingError):
            self.verify()

    def test_cached_child_identity_must_match_frozen_query_source_context(self):
        result = self.run_once()
        path = self.cache / result["children"][0]["cache_key"] / "manifest.json"
        original = sourcing._load(path)
        for field, value in (
            ("query", "wrong query"),
            ("sources", ["huggingface"]),
            ("skills", ["context-fundamentals"]),
            ("context_digest", "sha256:" + "0" * 64),
            ("implementation", {"researcher/scripts/other.py": "sha256:" + "0" * 64}),
            (
                "arxiv_search",
                {
                    "scope": "title_abstract",
                    "match": "terms",
                    "sort": "relevance",
                    "include_provenance": 1,
                },
            ),
        ):
            with self.subTest(field=field):
                changed = copy.deepcopy(original)
                changed["identity"][field] = value
                sourcing._write(path, changed)
                with self.assertRaises(sourcing.SourcingError):
                    self.verify()


if __name__ == "__main__":
    unittest.main()
