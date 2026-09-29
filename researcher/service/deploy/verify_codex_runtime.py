"""Pinned Linux SDK prerequisites and explicit real-SDK/fake-provider test gate."""
import argparse
import contextlib
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from researcher.service.codex_preflight import PreflightError, _execute, _private_directory, run_preflight  # noqa: E402

DEPENDENCIES = {
    "openai-codex": "0.159.0", "openai-codex-cli-bin": "0.159.0",
    "pydantic": "2.13.5", "pydantic-core": "2.46.5", "packaging": "26.3",
    "annotated-types": "0.8.0", "typing-extensions": "4.16.0", "typing-inspection": "0.4.4",
}
TEST_GROUPS = ("test_codex_campaign", "test_codex_pipeline.SDKPipelineTests",
               "test_codex_organization.SDKOrganizationTests", "test_sdk_learning.SDKLearningTests",
               "test_pipeline_actions.SDKPipelineActionTests", "test_shutdown.SDKShutdownTests")
OUTCOMES = ("failures", "errors", "skipped", "expected_failures", "unexpected_successes")
TOOL_FREE_DIAGNOSTICS = frozenset({"TIMEOUT", "OUTPUT_LIMIT", "INVALID_RESULT", "CHILD_FAILED"})


def _tool_free_diagnostic(error):
    # Only closed local child codes are observable. Never return exception text,
    # stderr, paths, arbitrary code objects or provider/test fixture material.
    if not isinstance(error, PreflightError):
        return None
    try:
        code = error.code
    except Exception:
        return None
    return code if type(code) is str and code in TOOL_FREE_DIAGNOSTICS else None


def _validate_tests(value):
    keys = {"groups", "planned", "executed", "passed", "source_digest", "source_unchanged", *OUTCOMES}
    if (type(value) is not dict or set(value) != keys or type(value["groups"]) is not dict
            or set(value["groups"]) != set(TEST_GROUPS)
            or any(type(count) is not int or not 1 <= count <= 200 for count in value["groups"].values())
            or any(type(value[key]) is not int or not 0 <= value[key] <= 600 for key in ("planned", "executed", *OUTCOMES))
            or value["planned"] != sum(value["groups"].values()) or value["executed"] > value["planned"]
            or type(value["passed"]) is not bool or type(value["source_unchanged"]) is not bool
            or not isinstance(value["source_digest"], str) or len(value["source_digest"]) != 71
            or not value["source_digest"].startswith("sha256:")
            or any(char not in "0123456789abcdef" for char in value["source_digest"][7:])):
        raise PreflightError("INVALID_RESULT")
    passed = value["source_unchanged"] and value["executed"] == value["planned"] and not any(value[key] for key in OUTCOMES)
    if value["passed"] != passed:
        raise PreflightError("INVALID_RESULT")
    return value


def _test_child():
    import socket
    import unittest
    from unittest.mock import patch
    from researcher.service.release_scenarios import _DiscardDiagnostics, _loopback_only, source_identity
    capture = _DiscardDiagnostics()
    with contextlib.redirect_stdout(capture), contextlib.redirect_stderr(capture), \
            patch("socket.socket.connect", _loopback_only(socket.socket.connect)), \
            patch("socket.socket.connect_ex", _loopback_only(socket.socket.connect_ex)):
        before = source_identity(ROOT)
        loader = unittest.TestLoader()
        groups = {name: loader.loadTestsFromName("researcher.service.tests." + name) for name in TEST_GROUPS}
        counts = {name: suite.countTestCases() for name, suite in groups.items()}
        suite = unittest.TestSuite(groups.values())
        result = unittest.TextTestRunner(stream=capture, verbosity=0).run(suite)
        unchanged = before == source_identity(ROOT)
    value = {"groups": counts, "planned": sum(counts.values()), "executed": result.testsRun,
             "failures": len(result.failures), "errors": len(result.errors), "skipped": len(result.skipped),
             "expected_failures": len(result.expectedFailures), "unexpected_successes": len(result.unexpectedSuccesses),
             "source_digest": before["release_source_digest"], "source_unchanged": unchanged,
             "passed": bool(unchanged and all(counts.values()) and not loader.errors and result.wasSuccessful()
                            and result.testsRun == sum(counts.values()) and not result.skipped and not result.expectedFailures)}
    return _validate_tests(value)


def run_tool_free_tests(service_python, workspace_parent):
    python = Path(service_python)
    if not python.is_absolute() or not python.is_file() or not os.access(python, os.X_OK):
        raise PreflightError("INVALID_INPUT")
    parent = _private_directory(workspace_parent)
    with tempfile.TemporaryDirectory(prefix="codex-tool-free-gate-", dir=parent) as temporary:
        fixture = Path(temporary)
        for name in ("home", "tmp", "codex"):
            (fixture / name).mkdir(mode=0o700)
        env = {"PATH": str(python.parent) + ":/usr/bin:/bin", "HOME": str(fixture / "home"),
               "TMPDIR": str(fixture / "tmp"), "CODEX_HOME": str(fixture / "codex"),
               "CODEX_WORKER_TEST_PYTHON": sys.executable, "PYTHONDONTWRITEBYTECODE": "1",
               "LANG": "C.UTF-8", "TZ": "UTC"}
        raw = _execute([str(python), "-I", "-B", str(Path(__file__).resolve()), "--tool-free-child"], env, ROOT, 300)
        try:
            value = json.loads(raw)
            return _validate_tests(value)
        except (TypeError, ValueError, RecursionError):
            raise PreflightError("INVALID_RESULT") from None


def verify(*, workspace_parent, profile, service_python=None):
    result = {"schema": "codex-linux-prerequisite/v3", "authority": "none", "production_ready": False,
              "status": "blocked", "failure_code": None, "dependency_versions_match": False,
              "target": "linux-aarch64-or-x86_64-cpython312", "preflight": None,
              "tool_free_tests": None, "tool_free_diagnostic_code": None, "provider_calls": 0,
              "source_sha256": {name: hashlib.sha256((ROOT / "researcher/service" / name).read_bytes()).hexdigest()
                                for name in ("codex_preflight.py", "codex_worker.py", "codex_config_boundary.py")}}
    if service_python is not None and profile != "tool_free":
        result["failure_code"] = "TOOL_FREE_PROFILE_REQUIRED"
        return result
    if sys.platform != "linux" or platform.machine() not in ("aarch64", "x86_64") or sys.version_info[:2] != (3, 12):
        result["failure_code"] = "UNSUPPORTED_LOCK_TARGET"
        return result
    try:
        matched = all(importlib.metadata.version(name) == version for name, version in DEPENDENCIES.items())
    except importlib.metadata.PackageNotFoundError:
        matched = False
    if not matched:
        result["failure_code"] = "DEPENDENCY_MISMATCH"
        return result
    result["dependency_versions_match"] = True
    try:
        result["preflight"] = run_preflight(sdk_python=sys.executable, workspace_parent=workspace_parent, profile=profile)
    except PreflightError as error:
        result["failure_code"] = error.code
        return result
    result["status"] = result["preflight"]["status"]
    result["failure_code"] = result["preflight"]["failure_code"]
    if result["status"] == "passed" and service_python is not None:
        try:
            result["tool_free_tests"] = run_tool_free_tests(service_python, workspace_parent)
            if not result["tool_free_tests"]["passed"]:
                result.update(status="blocked", failure_code="TOOL_FREE_TESTS_FAILED")
        except Exception as error:
            result.update(status="blocked", failure_code="TOOL_FREE_TESTS_UNAVAILABLE",
                          tool_free_diagnostic_code=_tool_free_diagnostic(error))
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-parent", required=True)
    parser.add_argument("--profile", choices=("tool_free", "native_tools"), required=True)
    parser.add_argument("--service-python", help="Explicit core-dependency Python enables mandatory zero-skip tool-free SDK tests")
    args = parser.parse_args(argv)
    result = verify(**vars(args))
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    if sys.argv[1:] == ["--tool-free-child"]:
        print(json.dumps(_test_child(), sort_keys=True, separators=(",", ":")))
    else:
        raise SystemExit(main())
