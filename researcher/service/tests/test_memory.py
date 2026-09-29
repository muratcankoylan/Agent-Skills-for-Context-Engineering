"""Bounded prior hypotheses and exact candidate identity, never model judging."""

from copy import deepcopy
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from researcher.scripts.schema_contract import canonicalize, sha256_bytes
from researcher.service.contracts import ServiceError, digest
from researcher.service.demo import demo_config
from researcher.service.store import MAX_FEEDBACK_BYTES, Store


BASELINE = "1" * 40
PATH = "skills/context-fundamentals/SKILL.md"
ORIGINAL = "# Fixture skill\nRetain an evidence reference.\n"
CHANGED = "# Fixture skill\nRetain the exact evidence reference.\n"


class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.config = demo_config()
        self.store = Store(Path(self.temporary.name).resolve() / "state", self.config,
                           initialize=True)
        self.current = self.add("current", status=None)[0]

    def add(self, job, *, status="proposal_ready", baseline=BASELINE, schedule=None,
            fixture=False, path=PATH, original=ORIGINAL, changed=CHANGED,
            hypothesis="Preserve evidence across context transfer.",
            test_plan="Compare exact reference retention in a held-out task.",
            timestamp=100, report=True):
        corpus = {"documents": [{"path": path, "text": original,
                                 "sha256": sha256_bytes(original.encode())}]}
        manifest = {"schema": "research-work/v1", "baseline_commit": baseline,
                    "config_digest": digest(self.config), "corpus_digest": digest(corpus),
                    "implementation_digest": digest("implementation-fixture"),
                    "schedule": deepcopy(schedule or self.config["schedules"][0]),
                    "fixture": fixture, "prompt_version": "fixture-v1"}
        research = {"hypothesis": hypothesis, "test_plan": test_plan, "abstain": False,
                    "claims": [{"id": "claim-one", "statement": "PRIVATE_CLAIM_TEXT",
                                "citations": [{"evidence_id": "source-two", "quote": "PRIVATE_QUOTE"},
                                              {"evidence_id": "source-one", "quote": "PRIVATE_QUOTE"}],
                                "limitations": ["PRIVATE_LIMITATION"]}]}
        record = {"schema": "research-service-review/v1", "job": job,
                  "baseline_commit": baseline, "corpus_digest": digest(corpus),
                  "fixture": fixture, "research": research,
                  "proposal": {"path": path, "old_text": original, "new_text": changed,
                               "claim_ids": ["claim-one"], "rationale": "PRIVATE_RATIONALE"},
                  "critic": {"issues": ["PRIVATE_CRITIC_ANSWER"]},
                  "evaluations": [{"judgment": {"reason": "PRIVATE_JUDGE_ANSWER"}}],
                  "raw_trace": "PRIVATE_RAW_TRACE", "credential": "PRIVATE_SECRET"}
        with patch("researcher.service.store.time.time", return_value=timestamp):
            self.store.enqueue(job, manifest)
            self.store.checkpoint(job, "corpus", {"manifest": digest(manifest)}, corpus)
            if report:
                self.store.checkpoint(job, "report", {"manifest": digest(manifest)}, record)
            if status:
                self.store.finish(job, status, "FIXTURE_REJECTION" if status == "rejected" else None)
        return manifest, record, corpus

    def update(self, table, column, value, job, *, name=None):
        self.assertIn(table, {"jobs", "steps"})
        self.assertIn(column, {"manifest", "digest", "output", "output_digest", "input_digest", "reason"})
        with sqlite3.connect(self.store.path) as db:
            if table == "jobs":
                db.execute(f"UPDATE jobs SET {column}=? WHERE id=?", (value, job))
            else:
                db.execute(f"UPDATE steps SET {column}=? WHERE job=? AND name=?", (value, job, name))

    def feedback(self, limit=5):
        return self.store.prior_feedback("current", self.current, limit)

    def seen(self, *, job="current", baseline=BASELINE, path=PATH, text=CHANGED):
        return self.store.candidate_seen(job, baseline, path, sha256_bytes(text.encode()))

    def test_empty_archive_and_limit_validation(self):
        result = self.feedback()
        self.assertEqual(result["entries"], [])
        self.assertEqual(result["omitted"], {"limit": 0, "budget": 0, "without_report": 0})
        self.assertEqual(result["authority"], "none")
        self.assertIs(result["semantic_novelty_measured"], False)
        self.assertFalse(self.seen())
        for limit in (True, False, 0, -1, 6, 1.0, "2"):
            with self.subTest(limit=limit), self.assertRaisesRegex(ServiceError, "INVALID_FEEDBACK_LIMIT"):
                self.feedback(limit)

    def test_feedback_matches_full_schedule_baseline_and_fixture_mode(self):
        self.add("eligible", status="rejected")
        self.add("other-baseline", baseline="2" * 40)
        self.add("fixture", fixture=True)
        schedule = deepcopy(self.config["schedules"][0])
        schedule["query"] = "Different need under the same schedule ID"
        self.add("other-query", schedule=schedule)
        schedule = deepcopy(self.config["schedules"][0])
        schedule["id"] = "other-id"
        self.add("other-id", schedule=schedule)
        self.store.finish("current", "proposal_ready")
        self.assertEqual([row["job"] for row in self.feedback()["entries"]], ["eligible"])

    def test_feedback_is_closed_projection_without_judge_or_trace_payloads(self):
        _, report, _ = self.add("prior", status="rejected")
        result = self.feedback()
        entry = result["entries"][0]
        self.assertEqual(set(entry), {"job", "report_digest", "hypothesis", "test_plan",
                                     "outcome", "reason", "evidence_refs"})
        self.assertEqual(entry["report_digest"], digest(report))
        self.assertEqual(entry["outcome"], "rejected")
        self.assertEqual(entry["reason"], "FIXTURE_REJECTION")
        self.assertEqual(entry["evidence_refs"], ["source-one", "source-two"])
        self.assertNotIn("PRIVATE_", json.dumps(result))
        self.assertEqual(entry["hypothesis"], report["research"]["hypothesis"])
        self.assertEqual(entry["test_plan"], report["research"]["test_plan"])

    def test_stable_ordering_limit_and_missing_report_counts(self):
        for job, timestamp in (("old", 90), ("tie-b", 110), ("new", 120), ("tie-a", 110)):
            self.add(job, timestamp=timestamp)
        self.add("no-report", status="rejected", report=False, timestamp=130)
        self.add("failed", status="failed", timestamp=80)
        self.add("unknown", status="reconciliation_required", timestamp=200)
        first = self.feedback(2)
        self.assertEqual(canonicalize(first), canonicalize(self.feedback(2)))
        self.assertEqual([row["job"] for row in first["entries"]], ["new", "tie-a"])
        self.assertEqual(first["omitted"], {"limit": 3, "budget": 0, "without_report": 1})

    def test_unicode_whole_entry_budget_and_later_small_entry(self):
        text = "🧪" * 3000
        self.add("large-new", hypothesis=text, test_plan=text, timestamp=300)
        self.add("large-old", hypothesis=text, test_plan=text, timestamp=200)
        self.add("small", timestamp=100)
        result = self.feedback()
        self.assertLessEqual(len(canonicalize(result)), MAX_FEEDBACK_BYTES)
        self.assertEqual([row["job"] for row in result["entries"]], ["large-new", "small"])
        self.assertEqual(result["entries"][0]["hypothesis"], text)
        self.assertEqual(result["entries"][0]["test_plan"], text)
        self.assertEqual(result["omitted"]["budget"], 1)

    def test_candidate_exact_bytes_same_baseline_and_path(self):
        self.add("prior", status="proposal_ready")
        self.assertTrue(self.seen())
        self.assertFalse(self.seen(text=CHANGED + "\n"))
        self.assertFalse(self.seen(path="skills/evaluation/SKILL.md"))
        self.assertFalse(self.seen(job="prior"))

    def test_candidate_lookup_crosses_schedule_but_not_fixture_or_baseline(self):
        self.add("other-baseline", baseline="2" * 40)
        self.add("fixture", fixture=True)
        self.assertFalse(self.seen())
        schedule = deepcopy(self.config["schedules"][0])
        schedule.update(id="other", query="A related research need")
        self.add("other-schedule", schedule=schedule)
        self.assertTrue(self.seen())

    def test_candidate_statuses_exclude_failed_pending_unknown_and_current(self):
        for status in (None, "failed", "reconciliation_required"):
            self.add("excluded-" + str(status), status=status)
        self.assertFalse(self.seen())
        for status in ("proposal_ready", "published", "rejected"):
            text = CHANGED + status
            self.add(status, status=status, changed=text)
            self.assertTrue(self.seen(text=text))

    def test_candidate_reconstruction_uses_original_not_proposal_claimed_digest(self):
        _, report, _ = self.add("prior")
        report["candidate_digest"] = sha256_bytes(b"forged")
        self.update("steps", "output", json.dumps(report), "prior", name="report")
        self.update("steps", "output_digest", digest(report), "prior", name="report")
        self.assertTrue(self.seen())
        self.assertFalse(self.seen(text="forged"))

    def test_manifest_and_output_corruption_fail_closed(self):
        manifest, report, _ = self.add("prior")
        changed = deepcopy(manifest)
        changed["baseline_commit"] = "2" * 40
        self.update("jobs", "manifest", json.dumps(changed), "prior")
        for method in (self.feedback, self.seen):
            with self.assertRaisesRegex(ServiceError, "HISTORY_DIGEST_MISMATCH"):
                method()
        self.update("jobs", "manifest", json.dumps(manifest), "prior")
        report["research"]["hypothesis"] = "Tampered"
        self.update("steps", "output", json.dumps(report), "prior", name="report")
        for method in (self.feedback, self.seen):
            with self.assertRaisesRegex(ServiceError, "HISTORY_DIGEST_MISMATCH"):
                method()

    def test_rehashed_report_still_requires_exact_parent_binding(self):
        _, report, _ = self.add("prior")
        report["baseline_commit"] = "2" * 40
        self.update("steps", "output", json.dumps(report), "prior", name="report")
        self.update("steps", "output_digest", digest(report), "prior", name="report")
        for method in (self.feedback, self.seen):
            with self.assertRaisesRegex(ServiceError, "HISTORY_REPORT_BINDING_MISMATCH"):
                method()

    def test_report_input_binding_checked_before_projection(self):
        self.add("prior")
        self.update("steps", "input_digest", digest({"manifest": "unrelated"}), "prior", name="report")
        with self.assertRaisesRegex(ServiceError, "HISTORY_INPUT_MISMATCH"):
            self.feedback()

    def test_corpus_output_and_input_corruption_prevent_duplicate_decision(self):
        _, _, corpus = self.add("prior")
        self.update("steps", "output", '{"documents":[]}', "prior", name="corpus")
        with self.assertRaisesRegex(ServiceError, "HISTORY_DIGEST_MISMATCH"):
            self.seen()
        self.update("steps", "output", json.dumps(corpus), "prior", name="corpus")
        self.update("steps", "input_digest", digest({"manifest": "other"}), "prior", name="corpus")
        with self.assertRaisesRegex(ServiceError, "HISTORY_INPUT_MISMATCH"):
            self.seen()

    def test_valid_hash_invalid_edit_is_not_a_known_candidate(self):
        _, report, _ = self.add("prior")
        report["proposal"]["old_text"] = "Not in baseline"
        self.update("steps", "output", json.dumps(report), "prior", name="report")
        self.update("steps", "output_digest", digest(report), "prior", name="report")
        with self.assertRaisesRegex(ServiceError, "HISTORY_PROPOSAL_INVALID"):
            self.seen()

    def test_corruption_after_match_and_beyond_feedback_limit_is_not_ignored(self):
        self.add("match", timestamp=200)
        self.add("corrupt", timestamp=100)
        self.update("steps", "output_digest", digest({}), "corrupt", name="report")
        with self.assertRaisesRegex(ServiceError, "HISTORY_DIGEST_MISMATCH"):
            self.seen()
        with self.assertRaisesRegex(ServiceError, "HISTORY_DIGEST_MISMATCH"):
            self.feedback(1)

    def test_current_manifest_identity_and_missing_job_are_checked(self):
        changed = deepcopy(self.current)
        changed["fixture"] = True
        with self.assertRaisesRegex(ServiceError, "HISTORY_CURRENT_INPUT_CHANGED"):
            self.store.prior_feedback("current", changed)
        with self.assertRaisesRegex(ServiceError, "HISTORY_CURRENT_INPUT_CHANGED"):
            self.seen(baseline="2" * 40)
        with self.assertRaisesRegex(ServiceError, "JOB_NOT_FOUND"):
            self.store.prior_feedback("missing", self.current)
        for value in (True, "a" * 64, "sha256:" + "z" * 64):
            with self.assertRaisesRegex(ServiceError, "INVALID_CANDIDATE_IDENTITY"):
                self.store.candidate_seen("current", BASELINE, PATH, value)

    def test_scan_limit_fails_closed_instead_of_claiming_novelty(self):
        self.add("one")
        self.add("two")
        with patch("researcher.service.store.MAX_HISTORY_JOBS", 1):
            for method in (self.feedback, self.seen):
                with self.assertRaisesRegex(ServiceError, "HISTORY_SCAN_LIMIT"):
                    method()

    def test_reads_do_not_change_any_logical_state(self):
        self.add("prior")
        with sqlite3.connect(self.store.path) as db:
            before = list(db.iterdump())
        self.feedback()
        self.seen()
        with self.store._history_snapshot() as db:
            with self.assertRaises(sqlite3.OperationalError):
                db.execute("UPDATE jobs SET reason='WRITE_NOT_ALLOWED'")
        with sqlite3.connect(self.store.path) as db:
            self.assertEqual(list(db.iterdump()), before)


if __name__ == "__main__":
    unittest.main()
