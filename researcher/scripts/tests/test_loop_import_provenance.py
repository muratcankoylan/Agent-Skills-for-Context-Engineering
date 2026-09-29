"""Package imports must not execute top-level shadow modules from PYTHONPATH."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


class LoopImportProvenanceTests(unittest.TestCase):
    def test_package_mode_uses_canonical_sibling_modules(self) -> None:
        module_names = (
            "loop_common",
            "validate_run",
            "skill_frontmatter",
        )
        imports = (
            "researcher.scripts.loop_daily",
            "researcher.scripts.loop_discover",
            "researcher.scripts.loop_status",
            "researcher.scripts.loop_step",
            "researcher.scripts.research_loop",
            "researcher.scripts.run_benchmarks",
            "researcher.scripts.validate_repo",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            shadow_root = Path(temp_dir)
            for module_name in module_names:
                (shadow_root / f"{module_name}.py").write_text(
                    f"raise RuntimeError('shadow module executed: {module_name}')\n",
                    encoding="utf-8",
                )
            shadow_package = shadow_root / "researcher"
            shadow_package.mkdir()
            (shadow_package / "__init__.py").write_text(
                "raise RuntimeError('shadow researcher package executed')\n",
                encoding="utf-8",
            )
            environment = os.environ.copy()
            environment["PYTHONPATH"] = os.pathsep.join((str(shadow_root), str(ROOT)))
            completed = subprocess.run(
                [sys.executable, "-c", ";".join(f"import {name}" for name in imports)],
                cwd=ROOT,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)


if __name__ == "__main__":
    unittest.main()
