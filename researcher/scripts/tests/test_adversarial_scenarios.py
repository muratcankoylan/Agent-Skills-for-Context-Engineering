from __future__ import annotations

import unittest
import tempfile
from pathlib import Path
from unittest import mock

from researcher.scripts import adversarial_scenarios


class AdversarialScenarioExecutionTests(unittest.TestCase):
    def test_empty_or_partial_catalog_cannot_claim_a_passing_gate(self) -> None:
        for catalog in ([], [{"scenario_id": "adv-wrong-rubric-math", "expected_gate": "validation_error"}]):
            with self.subTest(catalog=catalog):
                report = adversarial_scenarios.execute_catalog(catalog)
                self.assertFalse(report["passed"])
                self.assertTrue(report["catalog_errors"])

    def test_duplicate_scenario_does_not_count_as_another_execution(self) -> None:
        catalog = adversarial_scenarios.load_catalog(
            adversarial_scenarios.ROOT / "researcher/benchmarks/scenarios/adversarial.jsonl"
        )
        report = adversarial_scenarios.execute_catalog([*catalog, catalog[0]])
        self.assertFalse(report["passed"])
        self.assertEqual(report["executed_scenarios"], 7)
        self.assertTrue(any("duplicate" in error for error in report["catalog_errors"]))

    def test_nonobject_catalog_entry_fails_closed_without_execution(self) -> None:
        report = adversarial_scenarios.execute_catalog([[]])
        self.assertFalse(report["passed"])
        self.assertEqual(report["executed_scenarios"], 0)
        self.assertEqual(report["execution_status"], "not_executed")

    def test_duplicate_json_keys_are_rejected_at_loading_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            catalog = Path(directory) / "catalog.jsonl"
            catalog.write_text('{"scenario_id":"a","scenario_id":"b"}\n', encoding="utf-8")
            with self.assertRaises(ValueError):
                adversarial_scenarios.load_catalog(catalog)

    def test_complete_catalog_executes_seven_registered_mutations(self) -> None:
        catalog = adversarial_scenarios.load_catalog(
            adversarial_scenarios.ROOT
            / "researcher"
            / "benchmarks"
            / "scenarios"
            / "adversarial.jsonl"
        )
        report = adversarial_scenarios.execute_catalog(catalog)
        self.assertTrue(report["passed"], report["failures"])
        self.assertEqual(report["catalog_entries"], 7)
        self.assertEqual(report["executed_scenarios"], 7)
        self.assertEqual(report["execution_status"], "executed")
        self.assertEqual(
            {result["scenario_id"] for result in report["results"]},
            {item["scenario_id"] for item in catalog},
        )
        self.assertTrue(any(result["limitation"] for result in report["results"]))

    def test_unknown_scenario_fails_closed(self) -> None:
        report = adversarial_scenarios.execute_catalog(
            [{"scenario_id": "adv-unknown", "expected_gate": "deny"}]
        )
        self.assertFalse(report["passed"])
        self.assertEqual(report["failures"][0]["observed_gate"], "runner_missing")
        self.assertEqual(report["executed_scenarios"], 0)

    def test_expected_gate_metadata_drift_fails(self) -> None:
        report = adversarial_scenarios.execute_catalog(
            [
                {
                    "scenario_id": "adv-wrong-rubric-math",
                    "expected_gate": "incorrect-gate",
                }
            ]
        )
        self.assertFalse(report["passed"])
        self.assertIn("metadata drift", report["failures"][0]["evidence"][-1])

    def test_weighted_math_regression_is_falsifiable(self) -> None:
        with mock.patch.object(
            adversarial_scenarios,
            "source_evaluation_shape_errors",
            return_value=[],
        ):
            result = adversarial_scenarios._wrong_rubric_math()
        self.assertFalse(result.passed)
        self.assertEqual(result.observed_gate, "false_green")

    def test_private_semantic_scope_is_not_overclaimed(self) -> None:
        result = adversarial_scenarios._credible_generic_source()
        self.assertTrue(result.passed)
        self.assertIn("no autonomous prose classifier", result.limitation or "")


if __name__ == "__main__":
    unittest.main()
