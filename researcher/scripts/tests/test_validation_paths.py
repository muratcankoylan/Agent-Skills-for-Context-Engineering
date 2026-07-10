"""Regression tests for validation path and reference-validator discovery."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import skill_health  # noqa: E402
import validate_platform_compat as vpc  # noqa: E402


class SkillHealthOutputPathTests(unittest.TestCase):
    def test_relative_output_is_repo_root_relative(self) -> None:
        self.assertEqual(
            skill_health.normalize_output_path(Path("researcher/reports/custom-health.json")),
            skill_health.ROOT / "researcher/reports/custom-health.json",
        )

    def test_display_path_inside_repo_is_relative(self) -> None:
        path = skill_health.ROOT / "researcher/reports/custom-health.json"
        self.assertEqual(skill_health.display_path(path), "researcher/reports/custom-health.json")

    def test_display_path_outside_repo_is_absolute(self) -> None:
        path = Path("/tmp/contextlab-health.json")
        self.assertEqual(skill_health.display_path(path), str(path))


class ReferenceValidatorCommandTests(unittest.TestCase):
    def test_prefers_agentskills_console_script_on_path(self) -> None:
        with patch.object(vpc.shutil, "which", return_value="/venv/bin/agentskills"):
            self.assertEqual(vpc.reference_validator_command(), ["/venv/bin/agentskills"])

    def test_falls_back_to_current_python_module_entrypoint(self) -> None:
        with (
            patch.object(vpc.shutil, "which", return_value=None),
            patch.object(vpc.importlib.util, "find_spec", return_value=object()),
            patch.object(vpc.sys, "executable", "/venv/bin/python"),
        ):
            self.assertEqual(
                vpc.reference_validator_command(),
                ["/venv/bin/python", "-m", "skills_ref.cli"],
            )

    def test_returns_none_when_reference_validator_is_unavailable(self) -> None:
        with (
            patch.object(vpc.shutil, "which", return_value=None),
            patch.object(vpc.importlib.util, "find_spec", return_value=None),
        ):
            self.assertIsNone(vpc.reference_validator_command())


if __name__ == "__main__":
    unittest.main()
