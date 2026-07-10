import hashlib
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "verify_handoff.py"
SPEC = importlib.util.spec_from_file_location("verify_handoff", MODULE_PATH)
assert SPEC and SPEC.loader
verify_handoff = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verify_handoff)


class VerifyHandoffTests(unittest.TestCase):
    def make_fixture(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        history = root / "history.md"
        history.write_text("immutable source\n", encoding="utf-8")
        rubric = {
            "task_id": "test",
            "output_file": "HANDOFF.md",
            "source_file": "history.md",
            "source_sha256": hashlib.sha256(history.read_bytes()).hexdigest(),
            "max_bytes": 500,
            "min_headings": 2,
            "anchors": [
                {"value": "ERROR-7", "category": "error"},
                {"value": "risk-9", "category": "risks"},
                {"value": "next-eu", "category": "next_actions"},
            ],
        }
        rubric_path = root / "rubric.json"
        rubric_path.write_text(json.dumps(rubric), encoding="utf-8")
        return temp, root, rubric_path

    def evaluate_in(self, root, rubric_path):
        old_cwd = Path.cwd()
        try:
            os.chdir(root)
            return verify_handoff.evaluate(rubric_path)
        finally:
            os.chdir(old_cwd)

    def test_full_credit_pass(self):
        temp, root, rubric = self.make_fixture()
        self.addCleanup(temp.cleanup)
        (root / "HANDOFF.md").write_text(
            "## State\nERROR-7 and risk-9\n## Next\nnext-eu\n", encoding="utf-8"
        )
        code, score, _ = self.evaluate_in(root, rubric)
        self.assertEqual(code, 0)
        self.assertTrue(score["passed"])
        self.assertEqual(score["anchors"]["found"], 3)
        self.assertEqual(score["anchors"]["retention_rate"], 1.0)

    def test_partial_credit_reports_all_missing_anchors_and_categories(self):
        temp, root, rubric = self.make_fixture()
        self.addCleanup(temp.cleanup)
        (root / "HANDOFF.md").write_text(
            "## State\nERROR-7\n## Next\nomitted\n", encoding="utf-8"
        )
        code, score, message = self.evaluate_in(root, rubric)
        self.assertEqual(code, 24)
        self.assertFalse(score["passed"])
        self.assertEqual(score["anchors"]["found"], 1)
        self.assertEqual(score["anchors"]["total"], 3)
        self.assertEqual(score["anchors"]["retention_rate"], 0.3333)
        self.assertEqual(
            [item["value"] for item in score["anchors"]["missing"]],
            ["risk-9", "next-eu"],
        )
        self.assertEqual(score["categories"]["error"]["retention_rate"], 1.0)
        self.assertEqual(score["categories"]["risks"]["retention_rate"], 0.0)
        self.assertIn("missing 2/3 anchors", message)

    def test_budget_failure_keeps_anchor_score(self):
        temp, root, rubric = self.make_fixture()
        self.addCleanup(temp.cleanup)
        text = "## State\nERROR-7 risk-9\n## Next\nnext-eu\n" + ("x" * 600)
        (root / "HANDOFF.md").write_text(text, encoding="utf-8")
        code, score, _ = self.evaluate_in(root, rubric)
        self.assertEqual(code, 22)
        self.assertEqual(score["anchors"]["retention_rate"], 1.0)
        self.assertFalse(score["structural"]["within_budget"])

    def test_source_mutation_fails_after_scoring(self):
        temp, root, rubric = self.make_fixture()
        self.addCleanup(temp.cleanup)
        (root / "HANDOFF.md").write_text(
            "## State\nERROR-7 risk-9\n## Next\nnext-eu\n", encoding="utf-8"
        )
        (root / "history.md").write_text("mutated\n", encoding="utf-8")
        code, score, _ = self.evaluate_in(root, rubric)
        self.assertEqual(code, 25)
        self.assertFalse(score["structural"]["source_unchanged"])


if __name__ == "__main__":
    unittest.main()
