"""Deterministic retrieval, source boundaries, and literal citation grounding."""

from copy import deepcopy
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from researcher.scripts.schema_contract import canonicalize, sha256_bytes
from researcher.service.knowledge import (
    KnowledgeError,
    MAX_BYTES,
    retrieve_corpus,
    validate_citations,
)


class KnowledgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.body = "# Alpha\n\n## Retrieval\nEvidence retrieval improves retrieval.\n\n## Other\nUnrelated cooking.\n"
        self.write("alpha", self.body)

    def write(self, skill, text):
        path = self.root / "skills" / skill / "SKILL.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8") if isinstance(text, str) else text)
        return path

    def assert_code(self, code, function, *args):
        with self.assertRaises(KnowledgeError) as error:
            function(*args)
        self.assertEqual(error.exception.code, code)

    def retrieve(self, query="retrieval", skills=("alpha",), budget=MAX_BYTES):
        return retrieve_corpus(self.root, query, skills, budget)

    def test_deterministic_rank_and_exact_baseline(self):
        result = self.retrieve()
        self.assertEqual(result, self.retrieve())
        self.assertEqual(
            result["documents"],
            [
                {
                    "path": "skills/alpha/SKILL.md",
                    "sha256": sha256_bytes(self.body.encode()),
                    "text": self.body,
                }
            ],
        )
        self.assertEqual(len(result["excerpts"]), 1)
        self.assertIn("## Retrieval", result["excerpts"][0]["text"])
        self.assertGreater(result["excerpts"][0]["score_micros"], 0)
        self.assertEqual(
            {row["reason"] for row in result["omissions"]}, {"no_query_match"}
        )
        self.assertFalse(result["semantic_quality_measured"])

    def test_bm25_length_normalization_and_query_frequency(self):
        self.write("beta", "## Retrieval\nretrieval " + "padding " * 80)
        first = self.retrieve(skills=("alpha", "beta"))
        self.assertEqual(first["excerpts"][0]["path"], "skills/alpha/SKILL.md")
        repeated = self.retrieve("retrieval retrieval", ("alpha", "beta"))
        self.assertEqual(first["excerpts"], repeated["excerpts"])

    def test_tied_scores_use_path_not_selection_order(self):
        self.write("beta", self.body)
        result = self.retrieve(skills=("beta", "alpha"))
        self.assertEqual(result["selected_skills"], ["beta", "alpha"])
        self.assertEqual(
            [row["path"] for row in result["excerpts"]],
            ["skills/alpha/SKILL.md", "skills/beta/SKILL.md"],
        )

    def test_unicode_exact_utf8_offsets_and_normalized_matching(self):
        raw = "# Başlık 🧪\r\n\r\n## Kanıt\r\nÇÖZÜM ölçümü.\r\n\r\n## 空間\r\n資料検索。\r\n"
        self.write("alpha", raw)
        for query in ("çözüm", "資料検索"):
            with self.subTest(query=query):
                result = self.retrieve(query)
                self.assertTrue(result["excerpts"])
                for row in result["excerpts"]:
                    self.assertEqual(
                        raw.encode()[row["byte_start"] : row["byte_end"]],
                        row["text"].encode(),
                    )
                    self.assertEqual(row["source_sha256"], sha256_bytes(raw.encode()))

    def test_fenced_heading_is_not_a_section_boundary(self):
        self.write("alpha", "# Alpha\n## Rules\n```text\n## retrieval\n```\nDone.\n")
        result = self.retrieve()
        self.assertEqual(len(result["excerpts"]), 1)
        self.assertTrue(result["excerpts"][0]["text"].startswith("## Rules"))

    def test_budget_keeps_full_documents_and_records_omissions(self):
        self.write("alpha", "## Retrieval\n" + "retrieval " * 2000)
        complete = self.retrieve()
        budget = len(canonicalize(complete)) - 1
        reduced = self.retrieve(budget=budget)
        self.assertEqual(reduced["documents"], complete["documents"])
        self.assertEqual(reduced["excerpts"], [])
        self.assertEqual(reduced["omissions"][0]["reason"], "budget")
        exact = len(canonicalize(reduced))
        self.assertEqual(self.retrieve(budget=exact), reduced)
        self.assert_code(
            "BUDGET_INSUFFICIENT", self.retrieve, "retrieval", ("alpha",), exact - 1
        )

    def test_budget_counts_canonical_escaping(self):
        self.write("alpha", "## Retrieval\n" + 'retrieval \\"quoted\\"\n' * 100)
        result = self.retrieve()
        self.assertLessEqual(len(canonicalize(result)), MAX_BYTES)
        self.assert_code(
            "BUDGET_INSUFFICIENT",
            self.retrieve,
            "retrieval",
            ("alpha",),
            len(self.body),
        )

    def test_unknown_term_returns_explicit_omissions(self):
        result = self.retrieve("unfindabletoken")
        self.assertEqual(result["excerpts"], [])
        self.assertTrue(result["documents"])
        self.assertEqual(len(result["omissions"]), 3)

    def test_invalid_inputs(self):
        for query in ("", " \n", "!!!", "\x00", "\ud800", "x" * 4097, 3):
            with self.subTest(query=repr(query)):
                self.assert_code("INVALID_QUERY", self.retrieve, query)
        for skills in (
            [],
            "alpha",
            ["alpha", "alpha"],
            ["../alpha"],
            ["/alpha"],
            ["alpha/x"],
            ["alpha\\x"],
            [None],
        ):
            with self.subTest(skills=skills):
                self.assert_code("INVALID_SKILLS", self.retrieve, "retrieval", skills)
        for budget in (True, 0, -1, MAX_BYTES + 1, 1.5):
            self.assert_code(
                "INVALID_BUDGET", self.retrieve, "retrieval", ("alpha",), budget
            )

    def test_missing_oversize_and_malformed_sources(self):
        self.assert_code("SOURCE_MISSING", self.retrieve, "query", ("missing",))
        self.write("alpha", b"x" * (MAX_BYTES + 1))
        self.assert_code("SOURCE_TOO_LARGE", self.retrieve)
        for body in (b"", b"\xff", b"text\0text", b"## Heading\n```\nopen fence"):
            self.write("alpha", body)
            self.assert_code("INVALID_SOURCE", self.retrieve)

    def test_combined_source_budget_and_section_limit(self):
        self.write("alpha", "retrieval " * 7000)
        self.write("beta", "retrieval " * 7000)
        self.assert_code(
            "SOURCE_TOO_LARGE", self.retrieve, "retrieval", ("alpha", "beta")
        )
        self.write("alpha", "## Section\nretrieval\n" * 513)
        self.assert_code("SOURCE_TOO_LARGE", self.retrieve)

    def test_source_symlink_hardlink_directory_and_fifo(self):
        target = self.write("beta", self.body)
        path = self.root / "skills/alpha/SKILL.md"
        path.unlink()
        path.symlink_to(target)
        self.assert_code("UNSAFE_PATH", self.retrieve)
        path.unlink()
        os.link(target, path)
        self.assert_code("UNSAFE_PATH", self.retrieve)
        path.unlink()
        path.mkdir()
        self.assert_code("UNSAFE_PATH", self.retrieve)
        path.rmdir()
        os.mkfifo(path)
        self.assert_code("UNSAFE_PATH", self.retrieve)

    def test_root_and_skill_ancestor_symlinks(self):
        alias = self.root / "alias"
        alias.symlink_to(self.root, target_is_directory=True)
        self.assert_code(
            "UNSAFE_PATH", retrieve_corpus, alias, "retrieval", ["alpha"], MAX_BYTES
        )
        real = self.root / "skills/alpha"
        real.rename(self.root / "original")
        real.symlink_to(self.root / "original", target_is_directory=True)
        self.assert_code("UNSAFE_PATH", self.retrieve)

    def test_relative_and_parent_root_rejected(self):
        for root in (Path("."), self.root / "..", str(self.root)):
            self.assert_code(
                "UNSAFE_PATH", retrieve_corpus, root, "query", ["alpha"], MAX_BYTES
            )

    def test_same_length_source_mutation_during_read(self):
        original_read = os.read
        mutated = False

        def read_then_mutate(descriptor, maximum):
            nonlocal mutated
            chunk = original_read(descriptor, maximum)
            if not mutated:
                mutated = True
                self.write("alpha", self.body.replace("Evidence", "Falsely!"))
            return chunk

        with patch(
            "researcher.service.knowledge.os.read", side_effect=read_then_mutate
        ):
            self.assert_code("SOURCE_CHANGED", self.retrieve)

    def test_source_path_replacement_during_read(self):
        original_read = os.read
        replaced = False

        def read_then_replace(descriptor, maximum):
            nonlocal replaced
            chunk = original_read(descriptor, maximum)
            if not replaced:
                replaced = True
                path = self.root / "skills/alpha/SKILL.md"
                path.rename(path.with_name("old.md"))
                self.write("alpha", self.body)
            return chunk

        with patch(
            "researcher.service.knowledge.os.read", side_effect=read_then_replace
        ):
            self.assert_code("SOURCE_CHANGED", self.retrieve)


class CitationTests(unittest.TestCase):
    def setUp(self):
        self.text = "A source reports αβ improved in its own test, not ours."
        self.evidence = [
            {
                "id": "paper-a",
                "text": self.text,
                "sha256": sha256_bytes(self.text.encode()),
                "source_url": "https://example.com/paper",
            }
        ]
        self.citation = {
            "evidence_id": "paper-a",
            "quote": "αβ improved in its own test",
        }

    def assert_code(self, code, citations=None, evidence=None):
        with self.assertRaises(KnowledgeError) as error:
            validate_citations(
                [self.citation] if citations is None else citations,
                self.evidence if evidence is None else evidence,
            )
        self.assertEqual(error.exception.code, code)

    def test_literal_quote_and_multiple_distinct_quotes(self):
        self.assertIsNone(validate_citations([self.citation], self.evidence))
        self.assertIsNone(
            validate_citations(
                [self.citation, {"evidence_id": "paper-a", "quote": "not ours"}],
                self.evidence,
            )
        )

    def test_unknown_missing_and_nonliteral_quote(self):
        for citation in (
            {"evidence_id": "missing", "quote": "source"},
            {"evidence_id": "paper-a", "quote": "αβ improved in OUR test"},
        ):
            self.assert_code("UNGROUNDED_CITATION", [citation])

    def test_corrupt_digest_or_text_even_on_uncited_evidence(self):
        for change in ({"sha256": "sha256:" + "0" * 64}, {"text": self.text + "!"}):
            bad = {**self.evidence[0], "id": "uncited", **change}
            self.assert_code("EVIDENCE_DIGEST_MISMATCH", evidence=self.evidence + [bad])

    def test_duplicate_citations_and_evidence(self):
        self.assert_code("DUPLICATE_CITATION", [self.citation, deepcopy(self.citation)])
        self.assert_code("DUPLICATE_EVIDENCE", evidence=self.evidence * 2)

    def test_shapes_bounds_and_invalid_unicode(self):
        for citations in (
            [],
            "paper-a",
            [{**self.citation, "extra": True}],
            [self.citation] * 65,
        ):
            self.assert_code("INVALID_CITATION", citations)
        for quote in ("", " ", "\x00", "\ud800", "a" * 8193, None):
            self.assert_code("INVALID_CITATION", [{**self.citation, "quote": quote}])
        for evidence in ([], "paper-a", [{}], self.evidence * 257):
            self.assert_code("INVALID_EVIDENCE", evidence=evidence)

    def test_grounding_does_not_claim_entailment(self):
        # A literal fragment can omit the qualifier. This helper deliberately
        # leaves sentence-level support/qualification to the independent judge.
        validate_citations(
            [{"evidence_id": "paper-a", "quote": "αβ improved"}], self.evidence
        )


if __name__ == "__main__":
    unittest.main()
