import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("compare_reasoning", ROOT / "compare_reasoning.py")
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def record(task, condition, rep, passed, retention, duration=100, status="finished"):
    result = {
        "task_id": task,
        "condition": condition,
        "rep": rep,
        "status": status,
        "passed": passed,
        "duration_ms": duration,
    }
    if status == "finished":
        result["score"] = {
            "anchors": {"found": round(retention * 10), "total": 10, "retention_rate": retention},
            "categories": {},
        }
    return result


class CompareReasoningTests(unittest.TestCase):
    def test_exact_sign_test(self):
        self.assertEqual(MODULE.exact_two_sided(0, 0), 1.0)
        self.assertEqual(MODULE.exact_two_sided(3, 0), 0.25)
        self.assertEqual(MODULE.exact_two_sided(6, 0), 0.03125)

    def test_pair_mapping_keeps_improvements_regressions_and_errors_separate(self):
        left_records = [
            record("001", "control", 0, False, 0.9),
            record("001", "control", 1, True, 1.0),
            record("001", "control", 2, True, 1.0),
        ]
        right_records = [
            record("001", "control", 0, True, 1.0, 200),
            record("001", "control", 1, False, 0.9, 200),
            record("001", "control", 2, False, 0.0, status="error"),
        ]
        result = MODULE.compare(
            MODULE.index_records({"records": left_records}),
            MODULE.index_records({"records": right_records}),
            "control",
            "control",
        )
        self.assertEqual(result["planned_pairs"], 3)
        self.assertEqual(result["complete_pairs"], 2)
        self.assertEqual(result["improvements"], 1)
        self.assertEqual(result["regressions"], 1)
        self.assertEqual(result["ties"], 0)
        self.assertEqual(result["median_duration_ratio"], 2.0)
        self.assertFalse(result["pairs"][2]["complete"])


if __name__ == "__main__":
    unittest.main()
