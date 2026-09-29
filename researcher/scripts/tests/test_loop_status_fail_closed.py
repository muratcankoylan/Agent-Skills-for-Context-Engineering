"""Fail-closed regressions for the legacy status projection."""

from __future__ import annotations

import tempfile
import unittest
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from researcher.scripts import loop_status


class LoopStatusIntegrityTests(unittest.TestCase):
    @staticmethod
    def benchmark(
        repository: dict[str, object], *, activation_passed: bool = True
    ) -> dict[str, object]:
        checks = [
            {
                "name": "repo-validation",
                "kind": "executable_check",
                "passed": True,
                "exit_code": 0,
                "stdout_json": {"ok": True},
                "stderr": "",
                "failure_reason": None,
            },
            {
                "name": "activation-cases",
                "kind": "executable_check",
                "passed": activation_passed,
                "exit_code": 0 if activation_passed else 1,
                "stdout_json": {"ok": activation_passed},
                "stderr": "",
                "failure_reason": None if activation_passed else "nonzero exit",
            },
            {
                "name": "scenario-catalog-consistency",
                "kind": "catalog_validation",
                "passed": True,
                "catalog_entries": 7,
                "executed_scenarios": 0,
                "execution_status": "not_executed",
                "scope": "catalog consistency only",
                "failures": [],
            },
        ]
        return {
            "schema_version": "1.0.0",
            "timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "repository": repository,
            "ok": activation_passed,
            "recording_error": None,
            "summary": {
                "checks": 3,
                "executable_checks": 2,
                "failures": 0 if activation_passed else 1,
                "catalog_entries": 7,
                "executed_scenarios": 0,
            },
            "checks": checks,
        }

    @staticmethod
    def green_benchmark(repository: dict[str, object]) -> dict[str, object]:
        return LoopStatusIntegrityTests.benchmark(repository)

    def test_queue_or_run_integrity_failure_precedes_dashboard_write(self) -> None:
        cases = [
            {
                "parse_ok": False,
                "parse_error": "bad queue",
                "referential_ok": False,
                "unknown": 0,
            },
            {
                "parse_ok": True,
                "parse_error": None,
                "referential_ok": False,
                "referential_errors": ["orphan parked run"],
                "unknown": 0,
            },
            {
                "parse_ok": True,
                "parse_error": None,
                "referential_ok": True,
                "unknown": 1,
            },
        ]
        for health in cases:
            with self.subTest(health=health), tempfile.TemporaryDirectory() as temp_dir:
                status = Path(temp_dir) / "status.md"
                with mock.patch.object(
                    loop_status, "queue_snapshot", return_value=health
                ), mock.patch.object(loop_status, "STATUS_FILE", status):
                    with self.assertRaises(ValueError):
                        loop_status.render_status()
                self.assertFalse(status.exists())

    def test_cli_replaces_stale_green_status_with_explicit_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir).resolve()
            status = root / "researcher" / "reports" / "status.md"
            status.parent.mkdir(parents=True)
            status.write_text("old health looked green\n", encoding="utf-8")
            with mock.patch.object(
                loop_status,
                "queue_snapshot",
                return_value={
                    "parse_ok": False,
                    "parse_error": "torn inbox",
                    "referential_ok": False,
                    "unknown": 0,
                },
            ), mock.patch.object(loop_status, "STATUS_FILE", status), mock.patch.object(
                loop_status, "ROOT", root
            ), mock.patch.object(sys, "argv", ["loop_status.py", "--json"]):
                self.assertEqual(loop_status.main(), 1)

            rendered = status.read_text(encoding="utf-8")
            self.assertNotIn("old health looked green", rendered)
            self.assertIn("## Overall Health\n- failed", rendered)
            self.assertIn("queue parsing failed: torn inbox", rendered)

    def test_torn_latest_benchmark_record_does_not_fall_back_to_old_green(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            reports = Path(temp_dir)
            (reports / "benchmark-history.jsonl").write_text(
                '{"ok":true}\n{"ok":',
                encoding="utf-8",
            )
            with mock.patch.object(loop_status, "REPORTS_DIR", reports):
                with self.assertRaises(ValueError):
                    loop_status.latest_benchmark()

    def test_minimal_green_object_is_not_accepted_as_current_health(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            reports = Path(temp_dir)
            (reports / "benchmark-history.jsonl").write_text(
                '{"ok":true}\n', encoding="utf-8"
            )
            with mock.patch.object(loop_status, "REPORTS_DIR", reports), self.assertRaisesRegex(
                ValueError, "schema_version"
            ):
                loop_status.latest_benchmark()

    def test_skeletal_check_objects_are_rejected(self) -> None:
        repository: dict[str, object] = {
            "head": "a" * 40,
            "tree": "b" * 40,
            "tracked_clean": True,
        }
        record = self.green_benchmark(repository)
        record["checks"] = [
            {"name": "repo-validation", "passed": True},
            {"name": "activation-cases", "passed": True},
            {"name": "scenario-catalog-consistency", "passed": True},
        ]
        with self.assertRaisesRegex(ValueError, "kind"):
            loop_status.validate_benchmark_record(record)

    def test_benchmark_history_rejects_symlinks_and_hardlinks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            reports = Path(temp_dir)
            outside = reports / "outside.jsonl"
            outside.write_text("{}\n", encoding="utf-8")
            history = reports / "benchmark-history.jsonl"
            history.symlink_to(outside.name)
            with mock.patch.object(loop_status, "REPORTS_DIR", reports), self.assertRaisesRegex(
                ValueError, "single-link regular file"
            ):
                loop_status.latest_benchmark()
            history.unlink()
            history.hardlink_to(outside)
            with mock.patch.object(loop_status, "REPORTS_DIR", reports), self.assertRaisesRegex(
                ValueError, "single-link regular file"
            ):
                loop_status.latest_benchmark()

    def test_latest_failed_checks_make_top_level_health_nonpassing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            status = root / "status.md"
            health = {
                "parse_ok": True,
                "referential_ok": True,
                "unknown": 0,
                "pending_reap": 0,
                "_records": {
                    "inbox": [],
                    "parked": [],
                    "done_ledger": [],
                    "quarantine": [],
                },
                "_buckets": {"active": [], "parked": [], "closed": [], "unknown": []},
                "_states": {},
            }
            repository = {
                "head": "a" * 40,
                "tree": "b" * 40,
                "tracked_clean": True,
            }
            benchmark = self.benchmark(repository, activation_passed=False)
            with mock.patch.object(
                loop_status, "queue_snapshot", return_value=health
            ), mock.patch.object(
                loop_status, "latest_benchmark", return_value=benchmark
            ), mock.patch.object(
                loop_status, "latest_snapshot", return_value=None
            ), mock.patch.object(
                loop_status, "STATUS_FILE", status
            ), mock.patch.object(
                loop_status, "PARKED_REVIEW_FILE", root / "parked.md"
            ), mock.patch.object(
                loop_status, "ROOT", root
            ), mock.patch.object(
                loop_status, "repository_state", return_value=repository
            ):
                result = loop_status.render_status()
            self.assertFalse(result["ok"])
            self.assertTrue(result["rendered"])
            self.assertTrue(status.exists())

    def test_current_run_integrity_is_rechecked_for_status_health(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir).resolve()
            run_dir = root / "researcher" / "runs" / "run-x"
            run_dir.mkdir(parents=True)
            status = root / "status.md"
            repository: dict[str, object] = {
                "head": "a" * 40,
                "tree": "b" * 40,
                "tracked_clean": True,
            }
            health = {
                "parse_ok": True,
                "referential_ok": True,
                "unknown": 0,
                "pending_reap": 0,
                "_records": {
                    "inbox": [],
                    "parked": [],
                    "done_ledger": [],
                    "quarantine": [],
                },
                "_buckets": {
                    "active": [run_dir],
                    "parked": [],
                    "closed": [],
                    "unknown": [],
                },
                "_states": {
                    "run-x": {
                        "current_state": "evaluated",
                        "created_at": "2026-08-17T00:00:00+00:00",
                        "updated_at": "2026-08-17T00:00:00+00:00",
                    }
                },
            }
            failed_validation = {
                "ok": False,
                "run_dir": "researcher/runs/run-x",
                "summary": {"errors": 1, "warnings": 0},
                "findings": [],
            }
            validator = mock.Mock()
            validator.run.return_value = failed_validation
            with mock.patch.object(
                loop_status, "queue_snapshot", return_value=health
            ), mock.patch.object(
                loop_status, "RunValidator", return_value=validator
            ), mock.patch.object(
                loop_status,
                "latest_benchmark",
                return_value=self.green_benchmark(repository),
            ), mock.patch.object(
                loop_status, "latest_snapshot", return_value=None
            ), mock.patch.object(
                loop_status, "STATUS_FILE", status
            ), mock.patch.object(
                loop_status, "PARKED_REVIEW_FILE", root / "parked.md"
            ), mock.patch.object(loop_status, "ROOT", root), mock.patch.object(
                loop_status, "repository_state", return_value=repository
            ):
                result = loop_status.render_status()
            self.assertFalse(result["ok"])
            self.assertTrue(
                any(
                    "current run integrity failed" in error
                    for error in result["health_errors"]
                )
            )

    def test_initializer_does_not_report_corrupt_existing_ledgers_ready(self) -> None:
        with mock.patch.object(
            loop_status, "initialize_runtime_queue_ledgers", return_value=[]
        ), mock.patch.object(
            loop_status,
            "queue_snapshot",
            return_value={
                "parse_ok": False,
                "parse_error": "torn inbox",
                "referential_ok": False,
                "unknown": 0,
            },
        ), mock.patch.object(sys, "argv", ["loop_status.py", "--initialize-runtime"]):
            self.assertEqual(loop_status.main(), 1)


if __name__ == "__main__":
    unittest.main()
