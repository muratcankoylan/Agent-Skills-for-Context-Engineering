import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("evaluate_promotion", ROOT / "evaluate_promotion.py")
assert SPEC and SPEC.loader
evaluate_promotion = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(evaluate_promotion)
POLICY = json.loads((ROOT / "acceptance-policy.json").read_text())


def build_summary(tasks=6, target_regression=False):
    records = []
    totals = {condition: {"passed": 0, "found": 0, "total": 0} for condition in ("control", "target", "negative")}
    for task_index in range(tasks):
        task_id = f"{task_index + 1:03d}"
        for rep in range(3):
            for condition in ("control", "target", "negative"):
                passed = True
                found = 10
                if condition in ("control", "negative") and rep == 0:
                    passed = False
                    found = 9
                if target_regression and task_index == 0 and rep == 1 and condition == "target":
                    passed = False
                    found = 9
                totals[condition]["passed"] += int(passed)
                totals[condition]["found"] += found
                totals[condition]["total"] += 10
                records.append({
                    "task_id": task_id,
                    "condition": condition,
                    "rep": rep,
                    "passed": passed,
                    "score": {
                        "anchors": {"found": found, "total": 10, "retention_rate": found / 10},
                        "categories": {"risks": {"found": found, "total": 10, "retention_rate": found / 10}},
                    },
                })
    conditions = {}
    for condition, values in totals.items():
        total_runs = tasks * 3
        retention = values["found"] / values["total"]
        conditions[condition] = {
            "total": total_runs,
            "passed": values["passed"],
            "pass_rate": values["passed"] / total_runs,
            "anchor_retention_rate": retention,
            "categories": {"risks": {"found": values["found"], "total": values["total"], "retention_rate": retention}},
        }
    return {
        "repo_sha": "locked-fixture-sha",
        "models": ["gpt-5.6-sol"],
        "summary": {"conditions": conditions},
        "records": records,
    }


class PromotionEvaluationTests(unittest.TestCase):
    def test_exact_two_sided_sign_probability(self):
        self.assertEqual(evaluate_promotion.exact_two_sided_sign_p(6, 0), 0.03125)
        self.assertEqual(evaluate_promotion.exact_two_sided_sign_p(2, 0), 0.5)
        self.assertEqual(evaluate_promotion.exact_two_sided_sign_p(0, 0), 1.0)

    def test_qualifying_evidence_is_candidate_not_automatic_promotion(self):
        result = evaluate_promotion.evaluate(build_summary(), POLICY)
        self.assertTrue(result["passed"])
        self.assertEqual(result["automated_outcome"], "promotion_candidate")
        self.assertTrue(result["human_review_required"])
        self.assertEqual(result["failed_gates"], [])

    def test_underpowered_evidence_is_rejected(self):
        result = evaluate_promotion.evaluate(build_summary(tasks=3), POLICY)
        self.assertFalse(result["passed"])
        self.assertEqual(result["automated_outcome"], "not_eligible")
        self.assertIn("independent_tasks", result["failed_gates"])
        self.assertIn("total_runs", result["failed_gates"])

    def test_any_target_regression_is_rejected(self):
        result = evaluate_promotion.evaluate(build_summary(target_regression=True), POLICY)
        self.assertFalse(result["passed"])
        self.assertIn("target_vs_control_regressions", result["failed_gates"])
        self.assertIn("target_vs_negative_regressions", result["failed_gates"])


if __name__ == "__main__":
    unittest.main()
