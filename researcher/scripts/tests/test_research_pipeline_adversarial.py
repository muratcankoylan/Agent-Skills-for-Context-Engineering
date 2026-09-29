"""Offline extraction ablation, not a model/skill or scientific-quality benchmark.

The checkpoint has not yet been bound into a final scheduler result. Raw captured
bytes remain fixed, while an attacker can edit its derived leads and counters.
The baseline deliberately checks only blob integrity and receipt membership; it
is not a copy of the entire historical pipeline or an authenticity boundary.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import contextmanager
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from researcher.scripts import research_pipeline as pipeline
from researcher.scripts.research_evidence import LocalResearchEvidenceStore
from researcher.scripts.source_connectors import (
    ArxivAtomAdapter,
    ConnectorError,
    HackerNewsAPIAdapter,
    LeadPage,
    PinnedHTTPSTransport,
    QuerySpec,
    RetryAfter,
)
from researcher.scripts.tests.test_source_connectors import (
    FIXED_NOW,
    ScriptedTransport,
    atom_entry,
    atom_feed,
    resolver_for,
    response,
)


QUERY = "agent"
REPETITIONS = 3
ROOT = Path(__file__).resolve().parents[3]
MANIFEST_DIGEST = "sha256:" + "0" * 64
ARXIV_EXPECTED = [
    ("Agent memory", "https://arxiv.org/abs/2609.00001v1", "First abstract."),
    ("Agent context", "https://arxiv.org/abs/2609.00002v1", "Second abstract."),
]
HN_EXPECTED = [
    ("Agent memory", "https://example.com/memory", "Memory discussion."),
    ("Agent context", "https://example.com/context", "Context discussion."),
]


def _plain(value):
    return json.loads(json.dumps(value))


@contextmanager
def _offline_only():
    with (
        patch.object(
            socket, "getaddrinfo", side_effect=AssertionError("DNS forbidden")
        ),
        patch.object(
            socket, "create_connection", side_effect=AssertionError("network forbidden")
        ),
        patch.object(
            PinnedHTTPSTransport,
            "request",
            side_effect=AssertionError("network forbidden"),
        ),
    ):
        yield


def _capture_fixture(store, source, replies):
    """Use the production extractor with scripted transport, never canned leads."""
    captures = []
    transport = ScriptedTransport(*replies)

    def capture(observation, body):
        captures.append(asdict(store.capture(observation, body)))

    if source == "arxiv":
        adapter = ArxivAtomAdapter(
            transport=transport,
            resolver=resolver_for("export.arxiv.org"),
            now=lambda: FIXED_NOW,
            capture_sink=capture,
        )
    else:
        adapter = HackerNewsAPIAdapter(
            feed="newstories",
            transport=transport,
            resolver=resolver_for("hacker-news.firebaseio.com"),
            now=lambda: FIXED_NOW,
            capture_sink=capture,
        )
    try:
        with _offline_only():
            result = adapter.discover(QuerySpec(QUERY), pipeline.LIMITS)
    except ConnectorError as error:
        assert error.receipt is not None
        assert not transport.steps, "fixture left unused transport responses"
        return {
            "source": source,
            "manifest_digest": MANIFEST_DIGEST,
            "status": "failed",
            "capture_complete": False,
            "captures": captures,
            "receipt": _plain(asdict(error.receipt)),
            "leads": [],
            "error_code": error.code,
        }
    record = {
        "source": source,
        "manifest_digest": MANIFEST_DIGEST,
        "status": "observed" if isinstance(result, LeadPage) else "rate_limited",
        "capture_complete": True,
        "captures": captures,
        "receipt": _plain(asdict(result.receipt)),
        "leads": [_plain(asdict(item)) for item in result.items]
        if isinstance(result, LeadPage)
        else [],
    }
    if isinstance(result, RetryAfter):
        record["retry_after_seconds"] = result.retry_after_seconds
    assert not transport.steps, "fixture left unused transport responses"
    return record


def _fixtures(store):
    arxiv_body = atom_feed(
        *[
            atom_entry(title, url, stable_id=url, summary=summary)
            for title, url, summary in ARXIV_EXPECTED
        ]
    )
    hn_bodies = [
        [101, 102],
        *[
            {
                "id": 101 + index,
                "title": title,
                "url": url,
                "text": summary,
            }
            for index, (title, url, summary) in enumerate(HN_EXPECTED)
        ],
    ]
    return {
        "arxiv": _capture_fixture(
            store, "arxiv", [response(arxiv_body, "application/atom+xml")]
        ),
        "hacker_news": _capture_fixture(
            store,
            "hacker_news",
            [
                response(json.dumps(value).encode(), "application/json")
                for value in hn_bodies
            ],
        ),
        "empty": _capture_fixture(
            store, "arxiv", [response(atom_feed(), "application/atom+xml")]
        ),
        "malformed": _capture_fixture(
            store, "arxiv", [response(b"not XML", "application/atom+xml")]
        ),
        "rate_limited": _capture_fixture(
            store,
            "arxiv",
            [
                response(
                    b"limited",
                    "text/plain",
                    status=429,
                    headers=(("Retry-After", "17"),),
                )
            ],
        ),
    }


def _hash_membership_baseline(store, record, query):
    """Ablate extraction only: hashes, capture coverage and memberships remain."""
    del query
    observations = record["receipt"]["observations"]
    if len(record["captures"]) != len(observations):
        raise ValueError("capture coverage mismatch")
    for capture in record["captures"]:
        observation, _ = store.read(capture)
        if _plain(asdict(observation)) not in observations:
            raise ValueError("capture is not in receipt")


def _cases(fixtures):
    cases = [
        ("valid_" + name, True, copy.deepcopy(record))
        for name, record in fixtures.items()
    ]

    def add(name, fixture="arxiv"):
        record = copy.deepcopy(fixtures[fixture])
        cases.append((name, False, record))
        return record

    for field, value in (
        ("title", "Fabricated breakthrough"),
        ("url", "https://example.invalid/fabricated"),
        ("summary", "The captured source proves an invented improvement."),
    ):
        add("forged_" + field)["leads"][0][field] = value
    appended = add("appended_lead")
    extra = copy.deepcopy(appended["leads"][0])
    extra.update(identity="arxiv:forged", title="Uncaptured result")
    appended["leads"].append(extra)
    appended["receipt"]["item_count"] = len(appended["leads"])
    removed = add("removed_lead")
    removed["leads"].pop()
    removed["receipt"]["item_count"] = len(removed["leads"])
    add("reordered_leads")["leads"].reverse()

    duplicate = add("duplicate_capture_membership", "hacker_news")
    duplicate["captures"][2] = copy.deepcopy(duplicate["captures"][1])
    resealed = add("duplicate_capture_resealed_receipt", "hacker_news")
    resealed["captures"][2] = copy.deepcopy(resealed["captures"][1])
    observations = resealed["receipt"]["observations"]
    observations[2] = copy.deepcopy(observations[1])
    resealed["receipt"]["total_bytes"] = sum(
        item["response_bytes"] for item in observations
    )

    add("forged_retry_delay", "rate_limited")["retry_after_seconds"] = 999
    limited = add("successful_response_labeled_rate_limited")
    limited.update(status="rate_limited", leads=[], retry_after_seconds=17)
    limited["receipt"]["item_count"] = 0
    successful = add("rate_limit_labeled_successful", "rate_limited")
    successful.update(status="observed", leads=[])
    successful.pop("retry_after_seconds")
    failed = add("successful_response_labeled_failed")
    failed.update(status="failed", leads=[], error_code="ARXIV_SCHEMA_INVALID")
    failed["receipt"]["item_count"] = 0
    add("forged_parser_error_code", "malformed")["error_code"] = "INVENTED_ERROR"
    return cases


def _evaluate(check, store, record):
    start = time.perf_counter_ns()
    try:
        with _offline_only():
            check(store, record, QUERY)
        result = {"accepted": True}
    except (ValueError, RuntimeError) as error:
        result = {"accepted": False, "error_type": type(error).__name__}
        if hasattr(error, "code"):
            result["error_code"] = error.code
    result["elapsed_ns"] = time.perf_counter_ns() - start
    return result


def _implementation_identity():
    return {
        name: "sha256:" + hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        for name in (
            "researcher/scripts/research_pipeline.py",
            "researcher/scripts/research_evidence.py",
            "researcher/scripts/source_connectors.py",
            "researcher/scripts/tests/test_source_connectors.py",
            "researcher/scripts/tests/test_research_pipeline_adversarial.py",
        )
    }


def run_extraction_ablation():
    identities = _implementation_identity()
    with tempfile.TemporaryDirectory(prefix="extraction-ablation-") as temporary:
        store = LocalResearchEvidenceStore(Path(temporary).resolve() / "evidence")
        fixtures = _fixtures(store)
        rows = []
        for name, valid, record in _cases(fixtures):
            row = {"case": name, "expected_valid": valid}
            for condition, check in (
                ("hash_membership_only", _hash_membership_baseline),
                ("captured_extraction_replay", pipeline._validate_captures),
            ):
                outcomes = [_evaluate(check, store, record) for _ in range(REPETITIONS)]
                row[condition] = {
                    "outcomes": outcomes,
                    "false_accepts": sum(
                        item["accepted"] and not valid for item in outcomes
                    ),
                    "false_rejects": sum(
                        not item["accepted"] and valid for item in outcomes
                    ),
                    "decision_stable": len({item["accepted"] for item in outcomes})
                    == 1,
                }
            rows.append(row)
        fixture_hashes = {
            name: [capture["body_sha256"] for capture in record["captures"]]
            for name, record in fixtures.items()
        }
    if identities != _implementation_identity():
        raise AssertionError("implementation changed during ablation")
    return {
        "schema": "local-extraction-ablation/v1",
        "authority": "none",
        "observed_at": datetime.now(UTC).isoformat(),
        "measurement_scope": "finite_offline_extraction_consistency_fault_matrix",
        "semantic_quality_measured": False,
        "skill_effectiveness_measured": False,
        "network_calls": 0,
        "model_calls": 0,
        "query": QUERY,
        "limits": asdict(pipeline.LIMITS),
        "repetitions": REPETITIONS,
        "repetitions_meaning": "same deterministic inputs, repeatability only; not independent samples",
        "cases_executed": len(rows),
        "valid_cases": sum(row["expected_valid"] for row in rows),
        "invalid_cases": sum(not row["expected_valid"] for row in rows),
        "fixture_body_digests": fixture_hashes,
        "implementation": identities,
        "git_head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "checkout_binding": "file digests above identify tested dirty-worktree bytes, not HEAD alone",
        "limitations": [
            "The hash-membership baseline isolates the missing extraction check; it is not an entire historical pipeline.",
            "Fixture mutations are visible and author-selected, not a sealed held-out task set.",
            "No population confidence interval or production/generalization claim follows from this finite deterministic matrix.",
            "Replay can share extractor bugs; hand-authored known-answer assertions are separate tests.",
            "Elapsed times include offline guards and local file reads; they are not a production latency benchmark.",
            "An operator rewriting raw captures and every trust root is outside the threat model.",
        ],
        "passed": all(
            row["captured_extraction_replay"]["false_accepts"] == 0
            and row["captured_extraction_replay"]["false_rejects"] == 0
            and row["captured_extraction_replay"]["decision_stable"]
            for row in rows
        ),
        "results": rows,
    }


class ResearchPipelineAdversarialTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="extraction-regression-")
        self.addCleanup(temporary.cleanup)
        self.store = LocalResearchEvidenceStore(
            Path(temporary.name).resolve() / "evidence"
        )
        self.fixtures = _fixtures(self.store)

    def test_known_answers_are_not_inferred_from_replay(self):
        for name, expected in (("arxiv", ARXIV_EXPECTED), ("hacker_news", HN_EXPECTED)):
            with self.subTest(source=name):
                self.assertEqual(
                    [
                        (lead["title"], lead["url"], lead["summary"])
                        for lead in self.fixtures[name]["leads"]
                    ],
                    expected,
                )
        self.assertEqual(self.fixtures["empty"]["leads"], [])
        self.assertEqual(self.fixtures["rate_limited"]["retry_after_seconds"], 17)

    def test_valid_extractions_and_rate_limits_have_no_false_rejections(self):
        for name, valid, record in _cases(self.fixtures):
            if valid:
                with self.subTest(case=name):
                    self.assertTrue(
                        _evaluate(pipeline._validate_captures, self.store, record)[
                            "accepted"
                        ]
                    )

    def test_checkpoint_mutations_pass_hash_only_but_fail_replay(self):
        for name, valid, record in _cases(self.fixtures):
            if not valid:
                with self.subTest(case=name):
                    self.assertTrue(
                        _evaluate(_hash_membership_baseline, self.store, record)[
                            "accepted"
                        ]
                    )
                    self.assertFalse(
                        _evaluate(pipeline._validate_captures, self.store, record)[
                            "accepted"
                        ]
                    )

    def test_ablation_reports_every_condition_without_semantic_claims(self):
        report = run_extraction_ablation()
        self.assertEqual(report["cases_executed"], 18)
        self.assertEqual(report["valid_cases"], 5)
        self.assertEqual(report["invalid_cases"], 13)
        self.assertFalse(report["semantic_quality_measured"])
        self.assertFalse(report["skill_effectiveness_measured"])
        self.assertEqual(report["network_calls"], 0)
        self.assertEqual(report["model_calls"], 0)
        failures = [
            row["case"]
            for row in report["results"]
            if row["captured_extraction_replay"]["false_accepts"]
            or row["captured_extraction_replay"]["false_rejects"]
        ]
        self.assertTrue(report["passed"], str(failures))


if __name__ == "__main__":
    if "--report" in sys.argv:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("--report", type=Path, required=True)
        args = parser.parse_args()
        result = run_extraction_ablation()
        pipeline._atomic_write(
            args.report, json.dumps(result, sort_keys=True, indent=2).encode()
        )
        print(
            json.dumps(
                {
                    key: result[key]
                    for key in (
                        "passed",
                        "cases_executed",
                        "valid_cases",
                        "invalid_cases",
                    )
                }
            )
        )
        raise SystemExit(0 if result["passed"] else 1)
    unittest.main()
