import importlib.metadata
import json
import os
import platform
import sys
import unittest

assert os.environ.get("CODEX_WORKER_TEST_PYTHON") == sys.executable
for name in ("openai-codex", "openai-codex-cli-bin"):
    assert importlib.metadata.version(name) == "0.159.0"
loader = unittest.TestLoader()
suite = loader.loadTestsFromName("researcher.service.tests.test_codex_worker")
real = loader.loadTestsFromName("researcher.service.tests.test_codex_worker.RealSdkProofTests")
planned, real_planned = suite.countTestCases(), real.countTestCases()
assert planned >= 25 and real_planned >= 12 and not loader.errors
result = unittest.TextTestRunner(verbosity=2).run(suite)
passed = result.wasSuccessful() and result.testsRun == planned and not result.skipped
print(json.dumps({"schema": "isolated-sdk-proof/v1", "system": platform.system(),
    "machine": platform.machine(), "python": platform.python_version(), "uid": os.getuid(),
    "planned": planned, "executed": result.testsRun, "real_sdk_test_methods": real_planned,
    "failures": len(result.failures), "errors": len(result.errors), "skipped": len(result.skipped),
    "passed": bool(passed), "provider_calls": 0, "production_ready": False}, sort_keys=True))
sys.exit(0 if passed else 1)
