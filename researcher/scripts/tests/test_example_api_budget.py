"""Expose example paid-call budget regressions to repository CI discovery."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parents[3]
BUDGET_TEST_PATH = (
    REPO_ROOT / "examples/interleaved-thinking/tests/test_api_budget.py"
)


def _load_budget_tests() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "interleaved_thinking_api_budget_tests",
        BUDGET_TEST_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load API budget tests at {BUDGET_TEST_PATH}")
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
    return loader.loadTestsFromModule(_load_budget_tests())
