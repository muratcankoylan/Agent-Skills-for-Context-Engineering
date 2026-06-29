#!/usr/bin/env python3
"""Run deterministic researcher benchmark checks."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
RESEARCHER = ROOT / "researcher"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def run_command(name: str, cmd: list[str]) -> dict[str, Any]:
    completed = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)
    parsed: Any = None
    if completed.stdout:
        try:
            parsed = json.loads(completed.stdout)
        except json.JSONDecodeError:
            parsed = None
    return {
        "name": name,
        "passed": completed.returncode == 0,
        "exit_code": completed.returncode,
        "stdout_json": parsed,
        "stderr": completed.stderr,
    }


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def load_scenarios() -> list[dict[str, Any]]:
    scenarios: list[dict[str, Any]] = []
    for path in sorted((RESEARCHER / "benchmarks" / "scenarios").glob("*.jsonl")):
        scenarios.extend(load_jsonl(path))
    return scenarios


def load_goldens() -> dict[str, dict[str, Any]]:
    goldens: dict[str, dict[str, Any]] = {}
    for path in sorted((RESEARCHER / "benchmarks" / "goldens").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for scenario_id, expected in data.items():
            goldens[scenario_id] = expected
    return goldens


def evaluate_scenarios(scenarios: list[dict[str, Any]]) -> dict[str, Any]:
    goldens = load_goldens()
    failures: list[dict[str, Any]] = []
    scenario_ids = {scenario.get("scenario_id") for scenario in scenarios}
    for scenario in scenarios:
        if not scenario.get("scenario_id") or not scenario.get("expected_gate"):
            failures.append({"scenario_id": scenario.get("scenario_id", "unknown"), "reason": "missing required fields"})
            continue
        scenario_id = scenario["scenario_id"]
        golden = goldens.get(scenario_id)
        if not golden:
            failures.append({"scenario_id": scenario_id, "reason": "missing golden"})
            continue
        if golden.get("expected_gate") != scenario.get("expected_gate"):
            failures.append(
                {
                    "scenario_id": scenario_id,
                    "reason": "expected_gate differs from golden",
                    "scenario": scenario.get("expected_gate"),
                    "golden": golden.get("expected_gate"),
                }
            )
    for extra in sorted(set(goldens) - scenario_ids):
        failures.append({"scenario_id": extra, "reason": "golden has no matching scenario"})
    return {
        "name": "adversarial-scenario-shape",
        "passed": not failures,
        "scenario_count": len(scenarios),
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
    scenarios = load_scenarios()
    checks.append(evaluate_scenarios(scenarios))
    failures = [check for check in checks if not check.get("passed")]
    result = {
        "timestamp": utc_now(),
        "ok": not failures,
        "summary": {"benchmarks": len(checks), "failures": len(failures), "scenarios": len(scenarios)},
        "checks": checks,
    }
    if record:
        history = RESEARCHER / "reports" / "benchmark-history.jsonl"
        with history.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(result, sort_keys=True) + "\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Run researcher benchmark harness")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--record", action="store_true", help="append result to benchmark history")
    args = parser.parse_args()

    result = run_benchmarks(args.record)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        summary = result["summary"]
        print(
            f"Benchmarks {'passed' if result['ok'] else 'failed'}: "
            f"{summary['benchmarks']} checks, {summary['failures']} failures, {summary['scenarios']} scenarios"
        )
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
