"""Tests that catalog checks never masquerade as executed benchmarks."""

from __future__ import annotations

import subprocess
import os
import unittest
import tempfile
from pathlib import Path
from unittest import mock

from researcher.scripts import run_benchmarks


class EffectivenessAnswerVerifierTests(unittest.TestCase):
    def test_exact_assignment_rejects_wrong_and_contradictory_values(self) -> None:
        verifier = (
            Path(__file__).resolve().parents[2]
            / "benchmarks/effectiveness/tasks/001-filesystem-context-offload/verify.sh"
        )
        cases = (
            ("API_RATE_LIMIT=8475", 0),
            ("Found `API_RATE_LIMIT = 8475`", 0),
            ("API_RATE_LIMIT=84750", 12),
            ("API_RATE_LIMIT=8475wrong", 12),
            ("OTHER_API_RATE_LIMIT=8475", 12),
            ("API_RATE_LIMIT=8475\nAPI_RATE_LIMIT=", 12),
            ("API_RATE_LIMIT=8475\nAPI_RATE_LIMIT=9999", 12),
            ("API_RATE_LIMIT=9999", 12),
            ("No answer", 12),
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".runner").mkdir()
            for answer, expected_exit in cases:
                with self.subTest(answer=answer):
                    (root / ".runner/final.txt").write_text(answer, encoding="utf-8")
                    result = subprocess.run(
                        ["bash", str(verifier)], cwd=root, capture_output=True,
                        text=True, timeout=10, check=False,
                    )
                    self.assertEqual(result.returncode, expected_exit, result.stderr)


class ScenarioCatalogTests(unittest.TestCase):
    def test_matching_labels_are_reported_as_catalog_only(self) -> None:
        scenarios = [{"scenario_id": "adv-1", "expected_gate": "gate-a"}]
        result = run_benchmarks.validate_scenario_catalog(
            scenarios,
            {"adv-1": {"expected_gate": "gate-a"}},
        )
        self.assertTrue(result["passed"])
        self.assertEqual(result["name"], "scenario-catalog-consistency")
        self.assertEqual(result["kind"], "catalog_validation")
        self.assertEqual(result["executed_scenarios"], 0)
        self.assertEqual(result["execution_status"], "not_executed")

    def test_duplicate_ids_and_mismatched_labels_fail(self) -> None:
        scenarios = [
            {"scenario_id": "adv-1", "expected_gate": "gate-a"},
            {"scenario_id": "adv-1", "expected_gate": "gate-a"},
            {"scenario_id": "adv-2", "expected_gate": "gate-b"},
        ]
        result = run_benchmarks.validate_scenario_catalog(
            scenarios,
            {
                "adv-1": {"expected_gate": "gate-a"},
                "adv-2": {"expected_gate": "wrong-gate"},
            },
        )
        reasons = {failure["reason"] for failure in result["failures"]}
        self.assertIn("duplicate scenario_id", reasons)
        self.assertIn("expected_gate differs from golden", reasons)
        self.assertFalse(result["passed"])

    def test_nonobject_scenario_is_a_typed_catalog_failure(self) -> None:
        result = run_benchmarks.validate_scenario_catalog([[]], {})
        self.assertFalse(result["passed"])
        self.assertEqual(result["failures"][0]["reason"], "scenario must be an object")

    def test_catalog_load_failure_returns_a_nonpassing_result(self) -> None:
        executable = {
            "name": "gate",
            "kind": "executable_check",
            "passed": True,
        }
        with mock.patch.object(
            run_benchmarks, "run_command", return_value=executable
        ), mock.patch.object(
            run_benchmarks,
            "load_scenarios",
            side_effect=ValueError("malformed scenario input"),
        ):
            result = run_benchmarks.run_benchmarks(record=False)
        self.assertFalse(result["ok"])
        catalog = result["checks"][-1]
        self.assertFalse(catalog["passed"])
        self.assertIn("malformed scenario input", catalog["failures"][0]["reason"])


class ExecutableCheckTests(unittest.TestCase):
    def test_repository_binding_ignores_ambient_git_locator_variables(self) -> None:
        with mock.patch.dict(
            os.environ,
            {
                "GIT_DIR": "/tmp/forged-git-dir",
                "GIT_WORK_TREE": "/tmp/forged-work-tree",
                "GIT_INDEX_FILE": "/tmp/forged-index",
            },
        ):
            state = run_benchmarks.repository_state()
        self.assertRegex(state["head"], r"^[0-9a-f]{40,64}$")
        self.assertRegex(state["tree"], r"^[0-9a-f]{40,64}$")

    def test_zero_exit_without_explicit_passing_json_fails(self) -> None:
        for stdout in ["not json", "{}", '{"ok": false}']:
            with self.subTest(stdout=stdout), mock.patch.object(
                run_benchmarks.subprocess,
                "run",
                return_value=subprocess.CompletedProcess([], 0, stdout, ""),
            ):
                result = run_benchmarks.run_command("gate", ["gate"])
                self.assertFalse(result["passed"])
                self.assertEqual(result["kind"], "executable_check")

    def test_timeout_is_a_typed_executable_check_failure(self) -> None:
        with mock.patch.object(
            run_benchmarks.subprocess,
            "run",
            side_effect=subprocess.TimeoutExpired(["gate"], 300),
        ):
            result = run_benchmarks.run_command("gate", ["gate"])
        self.assertFalse(result["passed"])
        self.assertIsNone(result["exit_code"])
        self.assertEqual(result["failure_reason"], "timeout after 300 seconds")

    def test_launch_failure_is_a_typed_executable_check_failure(self) -> None:
        with mock.patch.object(
            run_benchmarks.subprocess,
            "run",
            side_effect=FileNotFoundError("python unavailable"),
        ):
            result = run_benchmarks.run_command("gate", ["gate"])
        self.assertFalse(result["passed"])
        self.assertIsNone(result["exit_code"])
        self.assertIn("could not start", result["failure_reason"])

    def test_repository_binding_launch_failure_is_fail_closed(self) -> None:
        with mock.patch.object(
            run_benchmarks.subprocess,
            "run",
            side_effect=FileNotFoundError("git unavailable"),
        ):
            state = run_benchmarks.repository_state()
        self.assertIsNone(state["head"])
        self.assertIsNone(state["tree"])
        self.assertFalse(state["tracked_clean"])

    def test_summary_separates_executable_checks_from_unexecuted_catalog(self) -> None:
        executable = {
            "name": "gate",
            "kind": "executable_check",
            "passed": True,
        }
        scenarios = [{"scenario_id": "adv-1", "expected_gate": "gate-a"}]
        with mock.patch.object(
            run_benchmarks, "run_command", return_value=executable
        ), mock.patch.object(
            run_benchmarks, "load_scenarios", return_value=scenarios
        ), mock.patch.object(
            run_benchmarks,
            "load_goldens",
            return_value={"adv-1": {"expected_gate": "gate-a"}},
        ):
            result = run_benchmarks.run_benchmarks(record=False)

        self.assertTrue(result["ok"])
        self.assertEqual(result["summary"]["executable_checks"], 2)
        self.assertEqual(result["summary"]["catalog_entries"], 1)
        self.assertEqual(result["summary"]["executed_scenarios"], 0)
        self.assertNotIn("benchmarks", result["summary"])
        self.assertNotIn("scenarios", result["summary"])

    def test_dirty_recording_failure_is_not_appended_to_history(self) -> None:
        executable = {
            "name": "gate",
            "kind": "executable_check",
            "passed": True,
        }
        with mock.patch.object(
            run_benchmarks, "run_command", return_value=executable
        ), mock.patch.object(
            run_benchmarks, "load_scenarios", return_value=[]
        ), mock.patch.object(
            run_benchmarks, "load_goldens", return_value={}
        ), mock.patch.object(
            run_benchmarks,
            "repository_state",
            return_value={"head": "a" * 40, "tree": "b" * 40, "tracked_clean": False},
        ), mock.patch.object(run_benchmarks, "append_jsonl") as append:
            result = run_benchmarks.run_benchmarks(record=True)
        self.assertFalse(result["ok"])
        self.assertIsNotNone(result["recording_error"])
        append.assert_not_called()


if __name__ == "__main__":
    unittest.main()
