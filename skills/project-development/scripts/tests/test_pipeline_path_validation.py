"""Path validation tests for the pipeline template.

Run directly or via the standard library test runner:

    python -m unittest skills/project-development/scripts/tests/test_pipeline_path_validation.py
    python skills/project-development/scripts/tests/test_pipeline_path_validation.py
"""

from __future__ import annotations

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "pipeline_template.py"
MODULE_SPEC = importlib.util.spec_from_file_location(
    "pipeline_template", MODULE_PATH
)
if MODULE_SPEC is None or MODULE_SPEC.loader is None:
    raise RuntimeError(f"Unable to load pipeline_template.py from {MODULE_PATH}")
PIPELINE = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(PIPELINE)


class BatchIdValidationTests(unittest.TestCase):
    """Tests for batch_id sanitization in get_batch_dir and get_output_dir."""

    def test_valid_batch_ids_accepted(self) -> None:
        valid_ids = [
            "2025-01-15",
            "batch_2025",
            "abc-123_DEF",
            "a",
            "A0-9_z",
        ]
        for batch_id in valid_ids:
            with self.subTest(batch_id=batch_id):
                batch_dir = PIPELINE.get_batch_dir(batch_id)
                output_dir = PIPELINE.get_output_dir(batch_id)
                self.assertIn(batch_id, batch_dir.name)
                self.assertIn(batch_id, output_dir.name)

    def test_dotdot_rejected(self) -> None:
        for batch_id in ["..", "../etc", "../../tmp", "foo/../bar"]:
            with self.subTest(batch_id=batch_id):
                with self.assertRaises(ValueError):
                    PIPELINE.get_batch_dir(batch_id)
                with self.assertRaises(ValueError):
                    PIPELINE.get_output_dir(batch_id)

    def test_path_separators_rejected(self) -> None:
        for batch_id in [
            "foo/bar",
            "foo\\bar",
            "/foo",
            "\\foo",
            "foo/bar/baz",
        ]:
            with self.subTest(batch_id=batch_id):
                with self.assertRaises(ValueError):
                    PIPELINE.get_batch_dir(batch_id)
                with self.assertRaises(ValueError):
                    PIPELINE.get_output_dir(batch_id)

    def test_empty_batch_id_rejected(self) -> None:
        with self.assertRaises(ValueError):
            PIPELINE.get_batch_dir("")
        with self.assertRaises(ValueError):
            PIPELINE.get_output_dir("")

    def test_non_string_batch_id_rejected(self) -> None:
        for batch_id in [None, 123, 1.5, ["batch"], {"id": "batch"}]:  # type: ignore[assignment]
            with self.subTest(batch_id=batch_id):
                with self.assertRaises(ValueError):
                    PIPELINE.get_batch_dir(batch_id)  # type: ignore[arg-type]
                with self.assertRaises(ValueError):
                    PIPELINE.get_output_dir(batch_id)  # type: ignore[arg-type]


class DeletionSafetyRegressionTests(unittest.TestCase):
    """Regression tests ensuring stage_clean cannot escape DATA_DIR."""

    def setUp(self) -> None:
        self.original_data_dir = PIPELINE.DATA_DIR
        self.temp_root = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_root.cleanup)
        PIPELINE.DATA_DIR = Path(self.temp_root.name) / "data"

    def tearDown(self) -> None:
        PIPELINE.DATA_DIR = self.original_data_dir

    def test_stage_clean_does_not_delete_outside_data_dir(self) -> None:
        # Create a target directory outside the configured DATA_DIR and place a
        # file that must survive any clean attempt.
        outside_dir = Path(self.temp_root.name) / "outside"
        outside_dir.mkdir(parents=True)
        sentinel = outside_dir / "sentinel.txt"
        sentinel.write_text("must survive")

        # A traversal batch_id must be rejected before any filesystem mutation.
        with self.assertRaises(ValueError):
            PIPELINE.stage_clean("../outside")

        self.assertTrue(sentinel.exists(), "stage_clean escaped DATA_DIR and deleted files")


if __name__ == "__main__":
    unittest.main()
