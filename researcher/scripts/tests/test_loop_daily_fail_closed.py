"""Fail-closed health aggregation tests for daily loop reporting."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from researcher.scripts import loop_daily


class SubprocessResultTests(unittest.TestCase):
    def test_zero_exit_with_malformed_or_nonpassing_json_fails_closed(self) -> None:
        cases = ["not json", '{"ok": false}', "{}", ""]
        for stdout in cases:
            with self.subTest(stdout=stdout), mock.patch.object(
                loop_daily.subprocess,
                "run",
                return_value=subprocess.CompletedProcess([], 0, stdout, ""),
            ):
                result = loop_daily.run_subprocess(["validator"])
                self.assertFalse(result["passed"])
                self.assertEqual(result["failure_reason"], "missing or non-passing JSON result")

    def test_zero_exit_requires_explicit_ok_true(self) -> None:
        with mock.patch.object(
            loop_daily.subprocess,
            "run",
            return_value=subprocess.CompletedProcess([], 0, '{"ok": true}', ""),
        ):
            self.assertTrue(loop_daily.run_subprocess(["validator"])["passed"])

    def test_timeout_is_a_typed_failure(self) -> None:
        with mock.patch.object(
            loop_daily.subprocess,
            "run",
            side_effect=subprocess.TimeoutExpired(["validator"], 300),
        ):
            result = loop_daily.run_subprocess(["validator"])
        self.assertFalse(result["passed"])
        self.assertIsNone(result["exit_code"])
        self.assertEqual(result["failure_reason"], "timeout after 300 seconds")

    def test_launch_failure_is_a_typed_failure(self) -> None:
        with mock.patch.object(
            loop_daily.subprocess,
            "run",
            side_effect=FileNotFoundError("python unavailable"),
        ):
            result = loop_daily.run_subprocess(["validator"])
        self.assertFalse(result["passed"])
        self.assertIsNone(result["exit_code"])
        self.assertIn("could not start", result["failure_reason"])


class DailyAggregationTests(unittest.TestCase):
    @staticmethod
    def create_empty_ledgers(queue_dir: Path) -> None:
        queue_dir.mkdir(parents=True, exist_ok=True)
        for name in ("inbox.jsonl", "parked.jsonl", "done.jsonl", "quarantine.jsonl"):
            (queue_dir / name).write_text("", encoding="utf-8")

    @staticmethod
    def passing_profile() -> dict[str, object]:
        return {
            "passed": True,
            "stdout_json": {
                "checks": [
                    {"name": "repo-validation", "passed": True},
                    {"name": "activation-cases", "passed": True},
                ]
            },
        }

    def test_run_validation_aggregate_is_conjunctive(self) -> None:
        run_dirs = [Path("run-a"), Path("run-b")]
        with mock.patch.object(
            loop_daily,
            "categorize_runs",
            return_value={"active": run_dirs, "parked": [], "closed": [], "unknown": []},
        ), mock.patch.object(
            loop_daily,
            "run_subprocess",
            side_effect=[
                {"passed": True},
                {"passed": False},
            ],
        ):
            result = loop_daily.run_run_validations()
        self.assertEqual(result["checked"], 2)
        self.assertEqual(result["passing"], 1)
        self.assertFalse(result["passed"])

    def test_daily_fails_for_failed_run_or_unknown_state(self) -> None:
        cases = [
            ({"checked": 1, "passing": 0, "passed": False, "results": []}, 0),
            ({"checked": 0, "passing": 0, "passed": True, "results": []}, 1),
        ]
        for run_validations, unknown in cases:
            with self.subTest(run_validations=run_validations, unknown=unknown):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    snapshots = root / "researcher" / "reports" / "snapshots"
                    with mock.patch.object(loop_daily, "ROOT", root), mock.patch.object(
                        loop_daily, "SNAPSHOTS_DIR", snapshots
                    ), mock.patch.object(
                        loop_daily, "run_benchmarks", return_value=self.passing_profile()
                    ), mock.patch.object(
                        loop_daily, "run_run_validations", return_value=run_validations
                    ), mock.patch.object(
                        loop_daily,
                        "queue_snapshot",
                        return_value={
                            "unknown": unknown,
                            "parse_ok": True,
                            "referential_ok": True,
                            "_buckets": {
                                "active": [],
                                "parked": [],
                                "closed": [],
                                "unknown": [],
                            },
                        },
                    ), mock.patch.object(
                        loop_daily, "claims_due_for_review", return_value=[]
                    ), mock.patch.object(
                        loop_daily, "render_snapshot", return_value="# snapshot\n"
                    ):
                        result = loop_daily.daily({})
                self.assertFalse(result["passing"])

    def test_daily_allows_zero_runs_when_every_observed_invariant_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            with mock.patch.object(loop_daily, "ROOT", root), mock.patch.object(
                loop_daily,
                "SNAPSHOTS_DIR",
                root / "researcher" / "reports" / "snapshots",
            ), mock.patch.object(
                loop_daily, "run_benchmarks", return_value=self.passing_profile()
            ), mock.patch.object(
                loop_daily,
                "run_run_validations",
                return_value={"checked": 0, "passing": 0, "passed": True, "results": []},
            ), mock.patch.object(
                loop_daily,
                "queue_snapshot",
                return_value={
                    "unknown": 0,
                    "pending_reap": 0,
                    "parse_ok": True,
                    "referential_ok": True,
                    "_buckets": {
                        "active": [],
                        "parked": [],
                        "closed": [],
                        "unknown": [],
                    },
                },
            ), mock.patch.object(
                loop_daily, "claims_due_for_review", return_value=[]
            ), mock.patch.object(
                loop_daily, "render_snapshot", return_value="# snapshot\n"
            ):
                self.assertTrue(loop_daily.daily({})["passing"])

    def test_malformed_claim_is_typed_and_makes_daily_nonpassing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            claims_dir = root / "claims"
            claims_dir.mkdir()
            (claims_dir / "index.jsonl").write_text(
                '{"claim_id":"claim-x","owning_skill":"skill-x",'
                '"volatility":"high","last_reviewed":7}\n',
                encoding="utf-8",
            )
            with mock.patch.object(loop_daily, "RESEARCHER", root):
                claims = loop_daily.claims_due_for_review()
            self.assertEqual(len(claims), 1)
            self.assertTrue(claims[0]["invalid"])

            with mock.patch.object(loop_daily, "ROOT", root), mock.patch.object(
                loop_daily,
                "SNAPSHOTS_DIR",
                root / "reports" / "snapshots",
            ), mock.patch.object(
                loop_daily, "run_benchmarks", return_value=self.passing_profile()
            ), mock.patch.object(
                loop_daily,
                "run_run_validations",
                return_value={"checked": 0, "passing": 0, "passed": True, "results": []},
            ), mock.patch.object(
                loop_daily,
                "queue_snapshot",
                return_value={
                    "unknown": 0,
                    "pending_reap": 0,
                    "parse_ok": True,
                    "referential_ok": True,
                    "_buckets": {
                        "active": [],
                        "parked": [],
                        "closed": [],
                        "unknown": [],
                    },
                },
            ), mock.patch.object(
                loop_daily, "claims_due_for_review", return_value=claims
            ), mock.patch.object(
                loop_daily, "render_snapshot", return_value="# snapshot\n"
            ):
                result = loop_daily.daily({})
            self.assertFalse(result["passing"])
            self.assertFalse(result["claims_valid"])

    def test_torn_claim_ledger_is_a_typed_invalid_claim(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            claims_dir = root / "claims"
            claims_dir.mkdir()
            (claims_dir / "index.jsonl").write_text("{torn\n", encoding="utf-8")
            with mock.patch.object(loop_daily, "RESEARCHER", root):
                claims = loop_daily.claims_due_for_review()
        self.assertEqual(len(claims), 1)
        self.assertTrue(claims[0]["invalid"])
        self.assertIn("could not be parsed", claims[0]["error"])

    def test_daily_passes_the_supplied_config_to_queue_validation(self) -> None:
        config = {"budgets": {"max_inbox_size": 0, "max_parked": 0}}
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            with mock.patch.object(loop_daily, "ROOT", root), mock.patch.object(
                loop_daily,
                "SNAPSHOTS_DIR",
                root / "researcher" / "reports" / "snapshots",
            ), mock.patch.object(
                loop_daily,
                "queue_snapshot",
                return_value={
                    "unknown": 0,
                    "pending_reap": 0,
                    "parse_ok": True,
                    "referential_ok": True,
                    "_buckets": {
                        "active": [],
                        "parked": [],
                        "closed": [],
                        "unknown": [],
                    },
                },
            ) as snapshot, mock.patch.object(
                loop_daily,
                "run_run_validations",
                return_value={"checked": 0, "passing": 0, "passed": True, "results": []},
            ), mock.patch.object(
                loop_daily, "run_benchmarks", return_value=self.passing_profile()
            ), mock.patch.object(
                loop_daily, "claims_due_for_review", return_value=[]
            ), mock.patch.object(
                loop_daily, "render_snapshot", return_value="# snapshot\n"
            ):
                loop_daily.daily(config)
        snapshot.assert_called_once_with(include_details=True, config=config)

    def test_daily_fails_when_any_queue_file_is_malformed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            queue_dir = root / "queue"
            self.create_empty_ledgers(queue_dir)
            (queue_dir / "inbox.jsonl").write_text("{not-json}\n", encoding="utf-8")
            with mock.patch.object(loop_daily, "QUEUE_DIR", queue_dir):
                snapshot = loop_daily.queue_snapshot()
        self.assertFalse(snapshot["parse_ok"])
        self.assertIn("Expecting property name", snapshot["parse_error"])

    def test_run_enumeration_failure_is_a_typed_nonpassing_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            queue_dir = Path(temp_dir)
            self.create_empty_ledgers(queue_dir)
            with mock.patch.object(loop_daily, "QUEUE_DIR", queue_dir), mock.patch.object(
                loop_daily, "list_run_dirs", side_effect=ValueError("boom")
            ):
                snapshot = loop_daily.queue_snapshot()
        self.assertTrue(snapshot["parse_ok"])
        self.assertFalse(snapshot["referential_ok"])
        self.assertIn("boom", snapshot["referential_errors"][0])

    def test_closed_runs_are_included_in_routine_validation(self) -> None:
        closed = Path("closed-run")
        with mock.patch.object(
            loop_daily,
            "categorize_runs",
            return_value={"active": [], "parked": [], "closed": [closed], "unknown": []},
        ), mock.patch.object(
            loop_daily, "run_subprocess", return_value={"passed": True}
        ) as run:
            result = loop_daily.run_run_validations()
        self.assertTrue(result["passed"])
        self.assertEqual(result["checked"], 1)
        self.assertIn("closed-run", run.call_args.args[0])

    def test_orphan_parked_record_fails_referential_integrity(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            queue_dir = root / "queue"
            self.create_empty_ledgers(queue_dir)
            (queue_dir / "parked.jsonl").write_text(
                '{"run_id":"missing-run","reason":"orphan","parked_at":"2026-08-17T00:00:00+00:00"}\n',
                encoding="utf-8",
            )
            with mock.patch.object(loop_daily, "QUEUE_DIR", queue_dir), mock.patch.object(
                loop_daily, "list_run_dirs", return_value=[]
            ), mock.patch.object(loop_daily, "unknown_run_entries", return_value=[]):
                snapshot = loop_daily.queue_snapshot()
        self.assertFalse(snapshot["referential_ok"])
        self.assertIn("parked run does not exist", snapshot["referential_errors"][0])

    def test_duplicate_or_over_budget_inbox_is_not_healthy(self) -> None:
        candidate = {
            "source_id": loop_daily.source_id_for("https://example.test/source"),
            "url": "https://example.test/source",
            "url_normalized": "https://example.test/source",
            "title": "source",
            "author_or_org": "fixture",
            "source_type": "paper",
            "candidate_reason": "fixture",
            "feed": "manual-seed",
            "discovered_at": "2026-08-17T00:00:00+00:00",
            "attempts": 0,
            "last_status": "queued",
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            queue_dir = root / "queue"
            self.create_empty_ledgers(queue_dir)
            (queue_dir / "inbox.jsonl").write_text(
                json.dumps(candidate) + "\n" + json.dumps(candidate) + "\n",
                encoding="utf-8",
            )
            with mock.patch.object(loop_daily, "QUEUE_DIR", queue_dir), mock.patch.object(
                loop_daily, "list_run_dirs", return_value=[]
            ), mock.patch.object(
                loop_daily, "unknown_run_entries", return_value=[]
            ), mock.patch.object(
                loop_daily,
                "load_config",
                return_value={"budgets": {"max_inbox_size": 1, "max_parked": 12}},
            ):
                snapshot = loop_daily.queue_snapshot()
        self.assertFalse(snapshot["referential_ok"])
        self.assertTrue(
            any("exceeds configured max_inbox_size" in item for item in snapshot["referential_errors"])
        )
        self.assertTrue(
            any("duplicate source_id" in item for item in snapshot["referential_errors"])
        )

    def test_closed_parked_run_is_recoverable_pending_reap_not_budget_corruption(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir).resolve()
            queue_dir = root / "queue"
            self.create_empty_ledgers(queue_dir)
            (queue_dir / "parked.jsonl").write_text(
                '{"parked_at":"2026-08-17T00:00:00+00:00",'
                '"reason":"closed","run_id":"closed-run"}\n',
                encoding="utf-8",
            )
            run_dir = root / "runs" / "closed-run"
            (run_dir / "reports").mkdir(parents=True)
            state = {
                "current_state": "closed",
                "close_status": "rejected",
                "close_reason": "not accepted",
                "state_history": [
                    {"timestamp": "2026-08-17T00:00:01+00:00"}
                ],
            }
            (run_dir / "reports" / "closure.json").write_text(
                json.dumps(
                    {
                        "status": "rejected",
                        "reason": "not accepted",
                        "closed_at": "2026-08-17T00:00:01+00:00",
                        "reviewed_by": "operator",
                        "integrity_errors": [],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            with mock.patch.object(
                loop_daily, "list_run_dirs", return_value=[run_dir]
            ), mock.patch.object(
                loop_daily, "unknown_run_entries", return_value=[]
            ), mock.patch.object(
                loop_daily, "load_run_state", return_value=state
            ):
                snapshot = loop_daily.queue_snapshot(
                    include_details=True,
                    queue_dir=queue_dir,
                    config={
                        "budgets": {"max_inbox_size": 0, "max_parked": 0}
                    },
                )

        self.assertTrue(snapshot["parse_ok"])
        self.assertTrue(snapshot["referential_ok"])
        self.assertEqual(snapshot["pending_reap"], 1)
        self.assertEqual(snapshot["_pending_reap"], [run_dir])
        self.assertEqual(snapshot["_buckets"]["parked"], [])

    def test_closed_run_without_valid_closure_is_not_pending_reap(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir).resolve()
            queue_dir = root / "queue"
            self.create_empty_ledgers(queue_dir)
            run_dir = root / "runs" / "closed-run"
            run_dir.mkdir(parents=True)
            state = {
                "current_state": "closed",
                "close_status": "rejected",
                "close_reason": "not accepted",
                "state_history": [
                    {"timestamp": "2026-08-17T00:00:01+00:00"}
                ],
            }
            with mock.patch.object(
                loop_daily, "list_run_dirs", return_value=[run_dir]
            ), mock.patch.object(
                loop_daily, "unknown_run_entries", return_value=[]
            ), mock.patch.object(
                loop_daily, "load_run_state", return_value=state
            ):
                snapshot = loop_daily.queue_snapshot(
                    include_details=True,
                    queue_dir=queue_dir,
                    config={
                        "budgets": {"max_inbox_size": 0, "max_parked": 0}
                    },
                )
        self.assertFalse(snapshot["referential_ok"])
        self.assertEqual(snapshot["pending_reap"], 0)
        self.assertEqual(snapshot["_pending_reap"], [])
        self.assertTrue(
            any(
                "closure is unavailable or invalid" in error
                for error in snapshot["referential_errors"]
            )
        )

    def test_future_runtime_queue_timestamp_is_invalid(self) -> None:
        errors = loop_daily.queue_record_errors(
            "parked",
            0,
            {
                "run_id": "run-x",
                "reason": "needs review",
                "parked_at": "2099-01-01T00:00:00+00:00",
            },
        )
        self.assertIn("parked[0].parked_at is future-dated", errors)


if __name__ == "__main__":
    unittest.main()
