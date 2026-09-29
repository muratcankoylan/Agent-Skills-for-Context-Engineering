"""Bounded, credential-free release rehearsals with explicit evidence scope.

This runs actual harness tests with injected providers. It is not a deployment,
live API benchmark, or proof of durable state on GitHub-hosted runners.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

SCENARIOS = {
    "managed-lifecycle": ("test_agents_runtime", "test_openai_agents"),
    "runner-recovery": ("test_github_runner_recovery",),
    "budget-and-uncertainty": ("test_openai_campaign",),
    "capture-grounding": ("test_retrieval_handoff", "test_citation_spans", "test_primary_profile"),
    "pipeline-checkpoints": ("test_research_pipeline",),
    "daily-restarts": ("test_month_simulation", "test_organization", "test_organization_capabilities"),
    "artifact-recovery": ("test_recovery_bundle",),
    "frozen-candidates": ("test_candidate_review",),
    "publication-boundary": ("test_github",),
    "operator-isolation": ("test_api", "test_environment"),
    "trace-isolation": ("test_tracing", "test_trace_export", "test_trace_events", "test_trace_cli",
                        "test_trace_pump", "test_trace_integration", "test_managed_traces"),
}
MAX_WORKER_OUTPUT = 65536
OUTCOMES = ("failures", "errors", "skipped", "unexpected_successes", "expected_failures")
FAILURE_REASONS = {"SCENARIO_DEADLINE_EXCEEDED", "INVALID_SCENARIO_RESULT"}


def validate_row(row, *, elapsed=False):
    """A closed result contract: no empty work, contradictions or raw diagnostics."""
    common = {"scenario", "passed"} | ({"elapsed_ms"} if elapsed else set())
    if not isinstance(row, dict) or row.get("scenario") not in SCENARIOS or type(row.get("passed")) is not bool:
        raise ValueError("INVALID_SCENARIO_RESULT")
    if elapsed and (type(row.get("elapsed_ms")) is not int or row["elapsed_ms"] < 0):
        raise ValueError("INVALID_SCENARIO_RESULT")
    if "reason" in row:
        if set(row) != common | {"reason"} or row["passed"] or row["reason"] not in FAILURE_REASONS:
            raise ValueError("INVALID_SCENARIO_RESULT")
        return row
    if set(row) != common | {"planned", "executed", "modules", *OUTCOMES}:
        raise ValueError("INVALID_SCENARIO_RESULT")
    counts = row["modules"]
    if (not isinstance(counts, dict) or set(counts) != set(SCENARIOS[row["scenario"]])
            or any(type(count) is not int or count < 0 for count in counts.values())
            or type(row["planned"]) is not int or row["planned"] != sum(counts.values())
            or type(row["executed"]) is not int or not 0 <= row["executed"] <= row["planned"]):
        raise ValueError("INVALID_SCENARIO_RESULT")
    for field in OUTCOMES:
        if (not isinstance(row[field], list) or any(not isinstance(value, str)
                or not re.fullmatch(r"[A-Za-z0-9_.]{1,300}", value) for value in row[field])):
            raise ValueError("INVALID_SCENARIO_RESULT")
    passed = (all(counts.values()) and row["executed"] == row["planned"]
              and all(not row[field] for field in OUTCOMES))
    if row["passed"] != bool(passed):
        raise ValueError("INVALID_SCENARIO_RESULT")
    return row


def _loopback_only(original):
    def connect(connection, address):
        try:
            allowed = (connection.family in (socket.AF_INET, socket.AF_INET6)
                       and isinstance(address, tuple) and ipaddress.ip_address(address[0]).is_loopback)
        except (ValueError, TypeError, IndexError):
            allowed = False
        if not allowed:
            raise AssertionError("release rehearsal permits numeric loopback only")
        return original(connection, address)
    return connect


def source_identity(root):
    from .candidate_review import _paths, _snapshot
    from .workflow import git_head, implementation
    paths = {path for folder in ("researcher/service", "researcher/scripts")
             for path in (root / folder).rglob("*.py") if "__pycache__" not in path.parts}
    paths.update((root / ".github/workflows").glob("*.yml"))
    paths.update((root / "researcher/service/deploy").glob("*"))
    files = {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
             for path in sorted(paths) if path.is_file()}
    closure = hashlib.sha256(json.dumps(files, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    # Structural scenarios also consume corpus/generated/configuration bytes.
    # Reuse candidate review's bounded, private-path-rejecting source boundary;
    # Git HEAD alone cannot identify an unpublished working tree.
    release = _snapshot(root, _paths(root))
    return {"commit": git_head(root), "implementation_digest": implementation(root),
            "scenario_source_digest": "sha256:" + closure, "scenario_source_files": len(files),
            "release_source_digest": release["files_digest"], "release_source_files": len(release["files"])}


def _identifier(test):
    value = test.id()
    return value if re.fullmatch(r"[A-Za-z0-9_.]{1,300}", value) else "unidentified_test"


class _DiscardDiagnostics:
    def write(self, value):
        return len(value)

    def flush(self):
        pass


def _worker(name):
    """Never export tracebacks or fixture/source content into public artifacts."""
    # The selected tests are reviewed repository code, not untrusted candidate
    # execution. The socket guard is a regression tripwire, not an OS sandbox.
    capture = _DiscardDiagnostics()
    with contextlib.redirect_stdout(capture), contextlib.redirect_stderr(capture), \
         patch("socket.socket.connect", _loopback_only(socket.socket.connect)), \
         patch("socket.socket.connect_ex", _loopback_only(socket.socket.connect_ex)):
        loader = unittest.TestLoader()
        suites = {module: loader.loadTestsFromName("researcher.service.tests." + module)
                  for module in SCENARIOS[name]}
        counts = {module: suite.countTestCases() for module, suite in suites.items()}
        suite = unittest.TestSuite(suites.values())
        planned = suite.countTestCases()
        result = unittest.TextTestRunner(stream=capture, verbosity=0, buffer=False).run(suite)
    return {"scenario": name, "planned": planned, "executed": result.testsRun, "modules": counts,
        "failures": [_identifier(test) for test, _ in result.failures],
        "errors": [_identifier(test) for test, _ in result.errors],
        "skipped": [_identifier(test) for test, _ in result.skipped],
        "unexpected_successes": [_identifier(test) for test in result.unexpectedSuccesses],
        "expected_failures": [_identifier(test) for test, _ in result.expectedFailures],
        "passed": bool(all(counts.values()) and result.testsRun == planned and result.wasSuccessful()
                       and not result.skipped and not result.expectedFailures)}


def execute(name, root, *, timeout_seconds=180, progress=lambda row: None):
    if name not in SCENARIOS or type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 300:
        raise ValueError("INVALID_REHEARSAL_REQUEST")
    started = time.monotonic()
    progress({"event": "scenario_started", "scenario": name})
    with tempfile.TemporaryDirectory(prefix="research-rehearsal-") as temporary:
        # No ambient provider/GitHub credentials, dotfiles or user-site packages.
        environment = {"PATH": os.defpath, "HOME": temporary, "TMPDIR": temporary,
            "PYTHONPATH": str(root), "PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONUTF8": "1", "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_TERMINAL_PROMPT": "0", "GIT_NO_REPLACE_OBJECTS": "1"}
        with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
            process = subprocess.Popen([sys.executable, "-m", "researcher.service.release_scenarios",
                "--worker", name], cwd=root, env=environment, stdout=output, stderr=errors,
                start_new_session=True)
            try:
                deadline = time.monotonic() + timeout_seconds
                while process.poll() is None:
                    # Raw writes bypassing the Python diagnostic sink are polled
                    # too. This is a trusted-test resource tripwire, not a sandbox.
                    if (os.fstat(output.fileno()).st_size > MAX_WORKER_OUTPUT
                            or os.fstat(errors.fileno()).st_size > MAX_WORKER_OUTPUT):
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait(timeout=5)
                        break
                    if time.monotonic() >= deadline:
                        raise subprocess.TimeoutExpired(process.args, timeout_seconds)
                    time.sleep(0.05)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=5)
                row = {"scenario": name, "passed": False, "reason": "SCENARIO_DEADLINE_EXCEEDED"}
            except BaseException:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=5)
                raise
            else:
                output.seek(0)
                raw = output.read(MAX_WORKER_OUTPUT + 1)
                errors.seek(0)
                unexpected_error = errors.read(1)
                try:
                    row = json.loads(raw)
                    validate_row(row)
                    if (len(raw) > MAX_WORKER_OUTPUT or unexpected_error or not isinstance(row, dict)
                            or row.get("scenario") != name or type(row.get("passed")) is not bool
                            or process.returncode not in (0, 1)
                            or (process.returncode == 0) != row["passed"]):
                        raise ValueError()
                except (ValueError, UnicodeError):
                    row = {"scenario": name, "passed": False, "reason": "INVALID_SCENARIO_RESULT"}
    row["elapsed_ms"] = round((time.monotonic() - started) * 1000)
    progress({"event": "scenario_completed", "scenario": name, "passed": row["passed"]})
    return row


def report(rows, identity):
    names = [row.get("scenario") for row in rows]
    if not rows or len(names) != len(set(names)) or any(name not in SCENARIOS for name in names):
        raise ValueError("INVALID_SCENARIO_COVERAGE")
    for row in rows:
        validate_row(row, elapsed=True)
    return {"schema": "research-release-rehearsal/v1", "source": identity,
        "scope": "deterministic harness fault scenarios with injected providers",
        "hosted_github_execution": False, "live_provider_execution": False,
        "scientific_effectiveness_measured": False, "deployment_activation": False,
        "planned_scenarios": len(rows), "executed_tests": sum(row.get("executed", 0) for row in rows),
        "complete_catalog": set(names) == set(SCENARIOS),
        "passed": all(row.get("passed") is True for row in rows), "scenarios": rows}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=tuple(SCENARIOS), action="append")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--worker", choices=tuple(SCENARIOS), help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.worker:
        if args.scenario or args.output:
            parser.error("worker mode has no output or scenario overrides")
        value = _worker(args.worker)
    else:
        root = Path(__file__).resolve().parents[2]
        identity = source_identity(root)
        names = args.scenario or list(SCENARIOS)
        if len(names) != len(set(names)):
            parser.error("duplicate scenarios are not independent evidence")
        def progress(row):
            print(json.dumps(row, sort_keys=True), file=sys.stderr, flush=True)
        rows = [execute(name, root, progress=progress) for name in names]
        if identity != source_identity(root):
            raise ValueError("REHEARSAL_SOURCE_CHANGED")
        value = report(rows, identity)
        if args.output:
            # Fresh files only. This public aggregate contains no raw diagnostics,
            # private paths, prompts, provider outputs or credentials.
            with args.output.open("x", encoding="utf-8") as destination:
                json.dump(value, destination, indent=2, sort_keys=True)
                destination.write("\n")
    print(json.dumps(value, sort_keys=True))
    return 0 if value["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
