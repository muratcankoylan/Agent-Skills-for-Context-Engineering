"""Expose hosted-agent security regressions to the repository CI test root."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


TEST_PATH = (
    Path(__file__).resolve().parents[3]
    / "skills"
    / "hosted-agents"
    / "tests"
    / "test_sandbox_manager.py"
)
MODULE_NAME = "hosted_agents_sandbox_manager_security_tests"
MODULE_SPEC = importlib.util.spec_from_file_location(MODULE_NAME, TEST_PATH)
if MODULE_SPEC is None or MODULE_SPEC.loader is None:
    raise RuntimeError(f"Unable to load hosted-agent tests from {TEST_PATH}")

TEST_MODULE = importlib.util.module_from_spec(MODULE_SPEC)
sys.modules[MODULE_NAME] = TEST_MODULE
MODULE_SPEC.loader.exec_module(TEST_MODULE)

# unittest discovery inspects TestCase classes bound in this module. Re-export
# the canonical suite so CI and focused local discovery execute the same tests.
RepositoryValidationTests = TEST_MODULE.RepositoryValidationTests
CommandBoundaryTests = TEST_MODULE.CommandBoundaryTests
CredentialBoundaryTests = TEST_MODULE.CredentialBoundaryTests
SessionAuthorizationTests = TEST_MODULE.SessionAuthorizationTests
ReferenceSecurityTests = TEST_MODULE.ReferenceSecurityTests
