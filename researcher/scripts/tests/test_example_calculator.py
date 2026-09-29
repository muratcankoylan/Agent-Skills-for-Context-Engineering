"""Expose the example calculator regression suite to the repository CI gate."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parents[3]
CALCULATOR_TEST_PATH = (
    REPO_ROOT / "examples/interleaved-thinking/tests/test_calculator.py"
)


def _load_calculator_tests() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "interleaved_thinking_calculator_tests",
        CALCULATOR_TEST_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load calculator tests at {CALCULATOR_TEST_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_tests(
    loader: unittest.TestLoader,
    tests: unittest.TestSuite,
    pattern: str | None,
) -> unittest.TestSuite:
    """Load the canonical example tests during normal repository discovery."""

    del tests, pattern
    return loader.loadTestsFromModule(_load_calculator_tests())
