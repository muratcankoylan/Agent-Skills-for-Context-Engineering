import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "evaluator.py"
MODULE_SPEC = importlib.util.spec_from_file_location(
    "evaluation_evaluator", MODULE_PATH
)
if MODULE_SPEC is None or MODULE_SPEC.loader is None:
    raise RuntimeError(f"Unable to load evaluator.py from {MODULE_PATH}")
EVALUATOR = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(EVALUATOR)


class AgentEvaluatorTests(unittest.TestCase):
    def test_weighted_overall_uses_rubric_dimension_weight(self) -> None:
        rubric = {
            "accuracy": EVALUATOR.RubricDimension(
                name="accuracy",
                weight=0.75,
                description="Accuracy",
                levels={},
            ),
            "completeness": EVALUATOR.RubricDimension(
                name="completeness",
                weight=0.25,
                description="Completeness",
                levels={},
            ),
        }
        evaluator = EVALUATOR.AgentEvaluator(rubric=rubric)

        def fake_dimension_score(
            dimension, task, output, ground_truth=None, tool_calls=None
        ):
            return 1.0 if dimension.name == "accuracy" else 0.0

        evaluator._evaluate_dimension = fake_dimension_score

        result = evaluator.evaluate({"type": "general"}, "output")

        self.assertAlmostEqual(result["overall_score"], 0.75)
        self.assertTrue(result["passed"])
        self.assertEqual(result["dimension_scores"]["accuracy"]["weight"], 0.75)
        self.assertEqual(result["dimension_scores"]["completeness"]["weight"], 0.25)


if __name__ == "__main__":
    unittest.main()
