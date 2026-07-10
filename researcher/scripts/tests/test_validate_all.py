"""Regression tests for the repository validation wrapper."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import validate_all  # noqa: E402


class ValidateAllTests(unittest.TestCase):
    def test_build_steps_uses_current_python_for_python_gates(self) -> None:
        with patch.object(validate_all.sys, "executable", "/venv/bin/python"):
            steps = validate_all.build_steps()
        self.assertTrue(steps)
        for step in steps:
            self.assertEqual(step.command[0], "/venv/bin/python", step)

    def test_required_gates_are_present_in_order(self) -> None:
        step_names = [step.name for step in validate_all.build_steps()]
        self.assertEqual(
            step_names,
            [
                "compile researcher scripts",
                "researcher unit tests",
                "platform compatibility",
                "repository validation",
                "skill health",
                "activation cases",
                "adversarial benchmarks",
            ],
        )

    def test_compile_targets_include_validation_wrapper_and_tests(self) -> None:
        self.assertIn("researcher/scripts/validate_all.py", validate_all.COMPILE_TARGETS)
        self.assertIn("researcher/scripts/tests/test_validation_paths.py", validate_all.COMPILE_TARGETS)
        self.assertIn("researcher/scripts/tests/test_validate_all.py", validate_all.COMPILE_TARGETS)


if __name__ == "__main__":
    unittest.main()
