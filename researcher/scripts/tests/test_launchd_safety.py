"""Regression tests for dormant legacy launchd entry points."""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
LAUNCHD = ROOT / "researcher" / "orchestration" / "launchd"


class LaunchdSafetyTests(unittest.TestCase):
    def fixture(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        return temporary, Path(temporary.name).resolve()

    def test_all_launchd_wrappers_are_inert(self) -> None:
        for name in (
            "run-loop-step.sh",
            "run-loop-discover.sh",
            "run-loop-daily.sh",
        ):
            with self.subTest(name=name):
                completed = subprocess.run(
                    ["/bin/bash", str(LAUNCHD / name)],
                    cwd=ROOT,
                    env={**os.environ, "PATH": "/usr/bin:/bin"},
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(completed.returncode, 78)
                self.assertIn("activation is disabled", completed.stderr)
                self.assertNotIn("python", (LAUNCHD / name).read_text(encoding="utf-8"))

    def test_install_entry_point_fails_closed_without_home_side_effects(self) -> None:
        _, root = self.fixture()
        home = root / "home"
        home.mkdir()
        environment = {
            **os.environ,
            "HOME": str(home),
            "PATH": "/usr/bin:/bin",
        }
        completed = subprocess.run(
            ["/bin/bash", str(LAUNCHD / "install.sh")],
            cwd=root,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 78)
        self.assertIn("activation is disabled", completed.stderr)
        self.assertFalse((home / "Library" / "LaunchAgents").exists())


if __name__ == "__main__":
    unittest.main()
