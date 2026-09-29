#!/usr/bin/env python3
"""Run deterministic repository checks and validate benchmark catalogs.

The scenario catalog records threats and expected gates. Catalog validation is
not scenario execution, so this command reports the executable and catalog-only
counts separately.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if __package__:
    from .loop_common import append_jsonl, strict_json_loads
else:  # Direct script execution.
    from loop_common import append_jsonl, strict_json_loads


ROOT = Path(__file__).resolve().parents[2]
RESEARCHER = ROOT / "researcher"
CHECK_TIMEOUT_SECONDS = 300
RESULT_SCHEMA_VERSION = "1.0.0"


def repository_state() -> dict[str, Any]:
    """Capture the exact tracked checkout identity used by a recorded run."""

    def git(*arguments: str) -> subprocess.CompletedProcess[str]:
        environment = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith("GIT_")
        }
        environment["GIT_NO_REPLACE_OBJECTS"] = "1"
        command = ["git", "-C", str(ROOT), *arguments]
        try:
            return subprocess.run(
                command,
                cwd=ROOT,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )
        except subprocess.TimeoutExpired:
            return subprocess.CompletedProcess(
                command, 124, "", "git binding timed out after 30 seconds"
            )
        except OSError as exc:
            return subprocess.CompletedProcess(
                command, 126, "", f"git binding could not start: {exc}"
            )

    head = git("rev-parse", "HEAD^{commit}")
    tree = git("rev-parse", "HEAD^{tree}")
    status = git("status", "--porcelain", "--untracked-files=all")
    valid_oid = re.compile(r"[0-9a-f]{40,64}")
    head_value = head.stdout.strip()
    tree_value = tree.stdout.strip()
    return {
        "head": head_value if head.returncode == 0 and valid_oid.fullmatch(head_value) else None,
        "tree": tree_value if tree.returncode == 0 and valid_oid.fullmatch(tree_value) else None,
        "tracked_clean": status.returncode == 0 and not status.stdout.strip(),
    }


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def run_command(name: str, cmd: list[str]) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            cmd,
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=CHECK_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "name": name,
            "kind": "executable_check",
            "passed": False,
            "exit_code": None,
            "stdout_json": None,
            "stderr": str(exc),
            "failure_reason": f"timeout after {CHECK_TIMEOUT_SECONDS} seconds",
        }
    except OSError as exc:
        return {
            "name": name,
            "kind": "executable_check",
            "passed": False,
            "exit_code": None,
            "stdout_json": None,
            "stderr": str(exc),
            "failure_reason": f"checker could not start: {exc}",
        }
    parsed: Any = None
    if completed.stdout:
        try:
            parsed = strict_json_loads(completed.stdout)
        except (json.JSONDecodeError, ValueError):
            parsed = None
    reported_ok = isinstance(parsed, dict) and parsed.get("ok") is True
    passed = completed.returncode == 0 and reported_ok
    return {
        "name": name,
        "kind": "executable_check",
        "passed": passed,
        "exit_code": completed.returncode,
        "stdout_json": parsed,
        "stderr": completed.stderr,
        "failure_reason": (
            None
            if passed
            else "nonzero exit"
            if completed.returncode != 0
            else "missing or non-passing JSON result"
        ),
    }


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if line.strip():
            value = strict_json_loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number}: expected an object")
            records.append(value)
    return records


def load_scenarios() -> list[dict[str, Any]]:
    scenarios: list[dict[str, Any]] = []
    for path in sorted((RESEARCHER / "benchmarks" / "scenarios").glob("*.jsonl")):
        scenarios.extend(load_jsonl(path))
    return scenarios


def load_goldens() -> dict[str, dict[str, Any]]:
    goldens: dict[str, dict[str, Any]] = {}
    for path in sorted((RESEARCHER / "benchmarks" / "goldens").glob("*.json")):
        data = strict_json_loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"{path}: golden root must be an object")
        for scenario_id, expected in data.items():
            goldens[scenario_id] = expected
    return goldens


def validate_scenario_catalog(
    scenarios: list[Any],
    goldens: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Validate scenario/golden consistency without claiming gate execution."""

    if goldens is None:
        goldens = load_goldens()
    failures: list[dict[str, Any]] = []
    scenario_ids: set[str] = set()
    for index, scenario in enumerate(scenarios):
        if not isinstance(scenario, dict):
            failures.append(
                {
                    "scenario_id": f"invalid:{index}",
                    "reason": "scenario must be an object",
                }
            )
            continue
        scenario_id = scenario.get("scenario_id")
        expected_gate = scenario.get("expected_gate")
        if not isinstance(scenario_id, str) or not scenario_id.strip():
            failures.append(
                {"scenario_id": "unknown", "reason": "scenario_id must be a non-empty string"}
            )
            continue
        if scenario_id in scenario_ids:
            failures.append({"scenario_id": scenario_id, "reason": "duplicate scenario_id"})
            continue
        scenario_ids.add(scenario_id)
        if not isinstance(expected_gate, str) or not expected_gate.strip():
            failures.append(
                {"scenario_id": scenario_id, "reason": "expected_gate must be a non-empty string"}
            )
            continue
        golden = goldens.get(scenario_id)
        if not isinstance(golden, dict):
            failures.append({"scenario_id": scenario_id, "reason": "missing golden"})
            continue
        if golden.get("expected_gate") != expected_gate:
            failures.append(
                {
                    "scenario_id": scenario_id,
                    "reason": "expected_gate differs from golden",
                    "scenario": expected_gate,
                    "golden": golden.get("expected_gate"),
                }
            )
    for extra in sorted(set(goldens) - scenario_ids):
        failures.append({"scenario_id": extra, "reason": "golden has no matching scenario"})
    return {
        "name": "scenario-catalog-consistency",
        "kind": "catalog_validation",
        "passed": not failures,
        "catalog_entries": len(scenarios),
        "executed_scenarios": 0,
        "execution_status": "not_executed",
        "scope": "validates scenario identifiers and expected-gate labels against goldens only",
        "failures": failures,
    }


def run_benchmarks(record: bool) -> dict[str, Any]:
    checks = [
        run_command(
            "repo-validation",
            [sys.executable, str(RESEARCHER / "scripts" / "validate_repo.py"), "--strict", "--json"],
        ),
        run_command(
            "activation-cases",
            [sys.executable, str(RESEARCHER / "scripts" / "check_activation_cases.py"), "--json"],
        ),
    ]
    try:
        scenarios = load_scenarios()
        catalog_check = validate_scenario_catalog(scenarios)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        scenarios = []
        catalog_check = {
            "name": "scenario-catalog-consistency",
            "kind": "catalog_validation",
            "passed": False,
            "catalog_entries": 0,
            "executed_scenarios": 0,
            "execution_status": "not_executed",
            "scope": "catalog inputs could not be validated",
            "failures": [{"scenario_id": "catalog", "reason": str(exc)}],
        }
    checks.append(catalog_check)
    failures = [check for check in checks if not check.get("passed")]
    repository = repository_state()
    recording_error = (
        "recorded results require a clean tracked and untracked checkout"
        if record and repository.get("tracked_clean") is not True
        else None
    )
    result = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "timestamp": utc_now(),
        "repository": repository,
        "ok": not failures and recording_error is None,
        "recording_error": recording_error,
        "summary": {
            "checks": len(checks),
            "executable_checks": sum(
                1 for check in checks if check.get("kind") == "executable_check"
            ),
            "failures": len(failures) + (1 if recording_error else 0),
            "catalog_entries": len(scenarios),
            "executed_scenarios": 0,
        },
        "checks": checks,
    }
    if record and recording_error is None:
        history = RESEARCHER / "reports" / "benchmark-history.jsonl"
        append_jsonl(history, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run deterministic checks and validate benchmark catalogs"
    )
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--record", action="store_true", help="append result to benchmark history")
    args = parser.parse_args()

    result = run_benchmarks(args.record)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        summary = result["summary"]
        print(
            f"Checks {'passed' if result['ok'] else 'failed'}: "
            f"{summary['checks']} checks, {summary['failures']} failures, "
            f"{summary['catalog_entries']} catalog entries, "
            f"{summary['executed_scenarios']} scenarios executed"
        )
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
