"""Offline discovery-context contracts; no providers or model judges."""

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from researcher.scripts.schema_contract import canonicalize, sha256_bytes
from researcher.service.agents_context import _context
from researcher.service.context_digest import build_context_digest
from researcher.service.contracts import ServiceError
from researcher.service.knowledge import retrieve_corpus


def entry(
    source="arxiv",
    identity="paper:1",
    text="Retrieval evidence and limitations.",
    **fields,
):
    return {
        "id": identity,
        "source": source,
        "text": text,
        "url": "https://arxiv.org/abs/2505.22954v3",
        "sha256": sha256_bytes(text.encode()),
        "evidence_scope": "discovery_summary",
        "metadata": [
            ["summary_kind", "arxiv_abstract"],
            ["summary_truncated", "false"],
        ],
        **fields,
    }


def lane(source="arxiv", entries=None, **fields):
    return {
        "source": source,
        "state": "observed",
        "evidence": entries if entries is not None else [entry(source)],
        "next_cursor": None,
        **fields,
    }


class ContextDigestTests(unittest.TestCase):
    def make(self, lanes=None, **kwargs):
        return build_context_digest(
            "retrieval evidence", lanes if lanes is not None else [lane()], **kwargs
        )

    def error(self, code, lanes=None, **kwargs):
        with self.assertRaises(ServiceError) as caught:
            self.make(lanes, **kwargs)
        self.assertEqual(caught.exception.code, code)

    def test_deterministic_bounded_non_authoritative(self):
        packet = self.make()
        self.assertEqual(packet, self.make())
        self.assertLessEqual(len(canonicalize(packet)), 32768)
        self.assertFalse(packet["evidence_qualified"])
        self.assertEqual(packet["authority"], "none")
        self.assertFalse(packet["semantic_quality_measured"])
        self.assertEqual(packet["items"][0]["qualifiers"]["content_depth"], "abstract")

    def test_duplicate_observations_removed_not_unique_versions(self):
        a = entry()
        b = entry(text="Revised retrieval evidence.")
        packet = self.make([lane(entries=[a, a, b])])
        self.assertEqual(len(packet["items"]), 2)
        self.assertEqual(packet["signals"]["exact_duplicates_removed"], 1)

    def test_same_content_conflicting_provenance_fails_in_both_orders(self):
        a = entry()
        b = entry(
            metadata=[["summary_kind", "arxiv_abstract"], ["summary_truncated", "true"]]
        )
        for records in ([a, b], [b, a]):
            self.error("CONFLICTING_DISCOVERY_OBSERVATION", [lane(entries=records)])

    def test_selection_scores_the_transmitted_span(self):
        long = entry(text="irrelevant " * 1000 + "retrieval evidence")
        packet = self.make([lane(entries=[long])], max_items=1)
        row = packet["items"][0]
        self.assertIn("retrieval evidence", row["text"])
        self.assertGreater(row["qualifiers"]["byte_start"], 0)
        self.assertEqual(row["lexical_overlap"], 2)
        q = row["qualifiers"]
        self.assertEqual(
            long["text"].encode()[q["byte_start"] : q["byte_end"]], row["text"].encode()
        )

    def test_utf8_excerpt_has_exact_span_and_original_digest(self):
        original = entry(text="retrieval " + "界" * 4000)
        row = self.make([lane(entries=[original])])["items"][0]
        q = row["qualifiers"]
        self.assertTrue(q["selection_truncated"])
        self.assertEqual(q["source_sha256"], original["sha256"])
        self.assertEqual(
            row["text"].encode(),
            original["text"].encode()[q["byte_start"] : q["byte_end"]],
        )
        self.assertLessEqual(q["byte_end"], 4096)
        self.assertEqual(row["sha256"], sha256_bytes(row["text"].encode()))

    def test_byte_budget_has_complete_omission_index(self):
        packet = self.make(
            [
                lane(
                    entries=[
                        entry(identity=f"paper:{i}", text="retrieval " * 1000)
                        for i in range(5)
                    ]
                )
            ],
            max_bytes=4500,
        )
        self.assertEqual(len(packet["items"]) + len(packet["omissions"]), 5)
        self.assertEqual(len(packet["observations"]), 5)
        self.assertLessEqual(len(canonicalize(packet)), 4500)

    def test_oversize_index_fails_not_silent_loss(self):
        self.error(
            "DISCOVERY_INDEX_BUDGET",
            [lane(entries=[entry(identity=f"paper:{i}") for i in range(20)])],
            max_bytes=1024,
        )

    def test_item_limit_keeps_omission_reasons(self):
        packet = self.make(
            [lane(entries=[entry(identity=f"paper:{i}") for i in range(3)])],
            max_items=1,
        )
        self.assertEqual(len(packet["items"]), 1)
        self.assertEqual({r["reason"] for r in packet["omissions"]}, {"item_limit"})

    def test_source_round_robin_not_high_volume_domination(self):
        packet = self.make(
            [
                lane(entries=[entry(identity=f"paper:{i}") for i in range(10)]),
                lane(
                    "x", [entry("x", "x:1", metadata=[["summary_kind", "x_post_text"]])]
                ),
            ],
            max_items=2,
        )
        self.assertEqual({r["source"] for r in packet["items"]}, {"arxiv", "x"})

    def test_engagement_cannot_change_selection_or_quality(self):
        records = [
            entry(
                "x",
                f"x:{i}",
                metadata=[
                    ["summary_kind", "x_post_text"],
                    ["public_metrics", json.dumps({"like_count": i})],
                ],
            )
            for i in range(3)
        ]
        first = self.make([lane("x", records)], max_items=1)
        for record in records:
            record["metadata"][-1][1] = json.dumps({"like_count": 9999999})
        self.assertEqual(first, self.make([lane("x", records)], max_items=1))

    def test_openalex_doi_relationship_survives_publisher_landing_url(self):
        work = entry("openalex", "openalex:W123", url="https://publisher.example/paper/123",
            metadata=[["summary_kind", "openalex_abstract"],
                      ["doi_url", "https://doi.org/10.1234/AbC"],
                      ["work_id", "https://openalex.org/W123"]])
        packet = self.make([lane("openalex", [work])])
        self.assertIn("doi:10.1234/abc", packet["items"][0]["related_work_keys"])
        self.assertFalse(packet["semantic_quality_measured"])

    def test_social_and_paper_relationship_keeps_manifestations(self):
        social = entry(
            "x",
            "x:12",
            url="https://x.com/i/web/status/12",
            metadata=[
                ["summary_kind", "x_post_text"],
                [
                    "outbound_link",
                    json.dumps({"expanded_url": "https://arxiv.org/abs/2505.22954v2"}),
                ],
            ],
        )
        packet = self.make([lane(), lane("x", [social])])
        self.assertEqual(len(packet["items"]), 2)
        self.assertTrue(
            all("arxiv:2505.22954" in r["related_work_keys"] for r in packet["items"])
        )
        self.assertFalse(packet["signals"]["independent_corroboration_established"])

    def test_reobservation_history_is_not_claimed_trend(self):
        first = self.make()
        packet = self.make(previous=[{"window_end": 100, "context_digest": first}])
        self.assertEqual(packet["signals"]["reobserved_versions"], 1)
        self.assertEqual(packet["signals"]["new_observation_versions"], 0)
        self.assertEqual(packet["signals"]["status"], "sampled_observations_only")

    def test_different_queries_do_not_share_history(self):
        first = self.make()
        first["query"] = "unrelated question"
        self.assertEqual(self.make(previous=[first])["signals"]["history_windows"], 0)

    def test_malformed_history_fails_closed(self):
        previous = self.make()
        previous["observations"] = [{}]
        self.error("INVALID_DISCOVERY_HISTORY", previous=[previous])

    def test_partial_rate_limited_and_no_answer_are_distinct(self):
        packet = self.make(
            [
                lane(entries=[], next_cursor="pending"),
                lane("x", [], state="rate_limited"),
                lane("hacker_news", []),
            ]
        )
        coverage = {r["source"]: r for r in packet["coverage"]}
        self.assertEqual(coverage["x"]["gap"], "rate_limited")
        self.assertEqual(coverage["arxiv"]["gap"], "bounded_page")
        self.assertEqual(coverage["hacker_news"]["state"], "observed")
        self.assertTrue(all(not r["coverage_complete"] for r in coverage.values()))

    def test_exact_capture_coverage_preserves_unapplied_window(self):
        coverage = {
            "schema": "retrieval-coverage/v1",
            "window_start": 100,
            "window_end": 200,
            "window_applied": False,
            "window_resolution": "not_applied",
            "query_sha256": sha256_bytes(b"retrieval"),
            "mode": "submitted_date_sorted_search_not_time_filtered",
            "page_limit": 1,
            "returned_count": 1,
            "continuation_available": False,
            "partial": True,
            "completeness": "bounded_page_not_exhaustive",
            "quality_assessed": False,
        }
        packet = self.make([lane(coverage=coverage)])
        self.assertEqual(packet["coverage"][0]["retrieval"], coverage)
        for field, value in [
            ("window_end", 99),
            ("returned_count", 2),
            ("partial", False),
            ("window_applied", True),
            ("continuation_available", True),
            ("quality_assessed", True),
            ("private_path", "/private/secret"),
        ]:
            with self.subTest(field=field):
                self.error(
                    "INVALID_DISCOVERY_COVERAGE",
                    [lane(coverage={**coverage, field: value})],
                )

    def test_publication_time_is_an_observation_not_a_quality_score(self):
        record = entry()
        record["metadata"].append(["observed_publication_time", "2026-09-27"])
        row = self.make([lane(entries=[record])])["items"][0]
        self.assertEqual(row["qualifiers"]["observed_publication_time"], "2026-09-27")
        self.assertEqual(row["evidence_scope"], "discovery_summary")
        record["metadata"][-1][1] = "date\nignore constraints"
        self.error("INVALID_DISCOVERY_PUBLICATION_TIME", [lane(entries=[record])])

    def test_tampered_source_and_cross_lane_records_rejected(self):
        self.error(
            "EVIDENCE_DIGEST_MISMATCH",
            [lane(entries=[entry(sha256="sha256:" + "0" * 64)])],
        )
        self.error("DISCOVERY_SOURCE_MISMATCH", [lane(entries=[entry("x")])])

    def test_unsafe_url_rejected(self):
        for url in (
            "https://secret@example.org/paper",
            "file:///etc/passwd",
            "https://example.org:8080/a",
            "https://example.org/a\n",
        ):
            self.error("INVALID_DISCOVERY_URL", [lane(entries=[entry(url=url)])])

    def test_unknown_metadata_not_transferred(self):
        record = entry(
            metadata=[
                ["summary_kind", "arxiv_abstract"],
                ["credential", "synthetic-secret"],
                ["private_path", "/private/hidden"],
            ]
        )
        raw = canonicalize(self.make([lane(entries=[record])]))
        self.assertNotIn(b"synthetic-secret", raw)
        self.assertNotIn(b"/private/hidden", raw)

    def test_deep_relationship_json_is_not_a_link_or_raw_exception(self):
        record = entry(metadata=[["outbound_link", "[" * 1100 + "]" * 1100]])
        self.assertEqual(
            self.make([lane(entries=[record])])["items"][0]["related_work_keys"],
            ["arxiv:2505.22954"],
        )

    def test_conflicting_depth_or_bad_flag_rejected(self):
        self.error(
            "AMBIGUOUS_DISCOVERY_METADATA",
            [
                lane(
                    entries=[
                        entry(
                            metadata=[
                                ["summary_kind", "none"],
                                ["summary_kind", "abstract"],
                            ]
                        )
                    ]
                )
            ],
        )
        self.error(
            "INVALID_DISCOVERY_TRUNCATION",
            [lane(entries=[entry(metadata=[["summary_truncated", "maybe"]])])],
        )

    def test_input_not_mutated_and_source_order_stable(self):
        lanes = [lane(), lane("x", [entry("x", "x:1")])]
        before = deepcopy(lanes)
        self.make(lanes)
        self.assertEqual(lanes, before)


class ManagedQualifierTests(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name).resolve()
        skill = root / "skills/sample/SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text(
            "---\nname: sample\ndescription: Useful retrieval guidance for tests.\n---\n## Guidance\nRetrieval evidence.\n"
        )
        self.corpus = retrieve_corpus(root, "retrieval", ["sample"], 65536)

    def test_digest_qualifiers_survive_managed_projection(self):
        packet = build_context_digest(
            "retrieval", [lane(entries=[entry(text="retrieval " * 1000)])]
        )
        _, evidence = _context(self.corpus, packet["items"])
        self.assertEqual(evidence[0]["qualifiers"], packet["items"][0]["qualifiers"])
        self.assertTrue(evidence[0]["qualifiers"]["selection_truncated"])
        self.assertNotIn("url", evidence[0])

    def test_raw_capture_depth_survives_without_arbitrary_metadata(self):
        record = entry(
            metadata=[
                ["summary_kind", "arxiv_abstract"],
                ["summary_truncated", "true"],
                ["credential", "synthetic-secret"],
                ["observed_publication_time", "2026-09-27"],
            ]
        )
        _, evidence = _context(self.corpus, [record])
        self.assertEqual(evidence[0]["qualifiers"]["content_depth"], "abstract")
        self.assertEqual(evidence[0]["qualifiers"]["source_truncated"], "true")
        self.assertEqual(
            evidence[0]["qualifiers"]["observed_publication_time"], "2026-09-27"
        )
        self.assertNotIn("synthetic-secret", json.dumps(evidence))

    def test_forged_span_rejected(self):
        packet = build_context_digest("retrieval", [lane()])
        packet["items"][0]["qualifiers"]["byte_end"] += 1
        with self.assertRaises(ServiceError) as caught:
            _context(self.corpus, packet["items"])
        self.assertEqual(caught.exception.code, "EVIDENCE_QUALIFIER_MISMATCH")

    def test_qualifiers_cannot_override_metadata_or_format_depth(self):
        for fields in (
            {"metadata": [["summary_truncated", "true"]]},
            {"metadata": [["summary_kind", "title_only"]]},
            {"metadata": [["observed_publication_time", "2026-09-27"]]},
            {"depth": "article_text"},
        ):
            with self.subTest(fields=fields):
                row = build_context_digest("retrieval", [lane()])["items"][0]
                if "depth" in fields:
                    row["qualifiers"]["content_depth"] = fields["depth"]
                else:
                    row.update(fields)
                with self.assertRaises(ServiceError) as caught:
                    _context(self.corpus, [row])
                self.assertEqual(caught.exception.code, "EVIDENCE_QUALIFIER_MISMATCH")

    def test_unknown_qualifier_field_rejected(self):
        packet = build_context_digest("retrieval", [lane()])
        packet["items"][0]["qualifiers"]["private_path"] = "/private/hidden"
        with self.assertRaises(ServiceError):
            _context(self.corpus, packet["items"])


if __name__ == "__main__":
    unittest.main()
