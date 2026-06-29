#!/usr/bin/env python3
"""Daily ops for the autonomous research loop.

Runs the deterministic gates, the benchmark harness, and writes a dated
snapshot report. Designed to be idempotent: running twice in a day overwrites
the same dated snapshot but appends to benchmark history each time.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from loop_common import (
    QUEUE_DIR,
    REPORTS_DIR,
    RESEARCHER,
    ROOT,
    SNAPSHOTS_DIR,
    categorize_runs,
    load_config,
    load_run_state,
    read_jsonl,
    today_utc,
    utc_now,
)


def run_subprocess(cmd: list[str]) -> dict[str, Any]:
    completed = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
    parsed: Any = None
    if completed.stdout.strip():
        try:
            parsed = json.loads(completed.stdout)
        except json.JSONDecodeError:
            parsed = None
    return {
        "exit_code": completed.returncode,
        "passed": completed.returncode == 0,
        "stdout_json": parsed,
        "stderr": completed.stderr.strip(),
    }


def run_repo_validation() -> dict[str, Any]:
    return run_subprocess([sys.executable, str(RESEARCHER / "scripts" / "validate_repo.py"), "--strict", "--json"])


def run_benchmarks() -> dict[str, Any]:
    return run_subprocess([sys.executable, str(RESEARCHER / "scripts" / "run_benchmarks.py"), "--record", "--json"])


def run_activation_cases() -> dict[str, Any]:
    return run_subprocess([sys.executable, str(RESEARCHER / "scripts" / "check_activation_cases.py"), "--json"])


def run_run_validations() -> dict[str, Any]:
    buckets = categorize_runs()
    results: list[dict[str, Any]] = []
    for run_dir in buckets["active"] + buckets["parked"]:
        result = run_subprocess(
            [
                sys.executable,
                str(RESEARCHER / "scripts" / "validate_run.py"),
                "--run-dir",
                str(run_dir),
                "--json",
            ]
        )
        results.append({"run_id": run_dir.name, **result})
    return {
        "checked": len(results),
        "passing": sum(1 for record in results if record.get("passed")),
        "results": results,
    }


def queue_snapshot() -> dict[str, Any]:
    buckets = categorize_runs()
    inbox = read_jsonl(QUEUE_DIR / "inbox.jsonl")
    parked = read_jsonl(QUEUE_DIR / "parked.jsonl")
    done = read_jsonl(QUEUE_DIR / "done.jsonl")
    quarantine = read_jsonl(QUEUE_DIR / "quarantine.jsonl")
    return {
        "inbox": len(inbox),
        "active": len(buckets["active"]),
        "parked": len(parked),
        "closed": len(buckets["closed"]),
        "done_ledger": len(done),
        "quarantine": len(quarantine),
        "unknown": len(buckets["unknown"]),
    }


def claims_due_for_review() -> list[dict[str, Any]]:
    claims_path = RESEARCHER / "claims" / "index.jsonl"
    if not claims_path.exists():
        return []
    today = today_utc()
    due: list[dict[str, Any]] = []
    for line in claims_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if record.get("volatility") == "high":
            last_reviewed = record.get("last_reviewed", "")
            if last_reviewed < today:
                due.append({"claim_id": record.get("claim_id"), "owning_skill": record.get("owning_skill"), "last_reviewed": last_reviewed})
    return due


def render_snapshot(
    timestamp: str,
    repo: dict[str, Any],
    activation: dict[str, Any],
    benchmarks: dict[str, Any],
    run_validations: dict[str, Any],
    queue: dict[str, Any],
    claims: list[dict[str, Any]],
) -> str:
    lines = [
        f"# Researcher Snapshot {timestamp}",
        "",
        "## Queue",
        f"- inbox: {queue['inbox']}",
        f"- active runs: {queue['active']}",
        f"- parked runs: {queue['parked']}",
        f"- closed runs (state): {queue['closed']}",
        f"- done ledger entries: {queue['done_ledger']}",
        f"- quarantined sources: {queue['quarantine']}",
        f"- unknown run state: {queue['unknown']}",
        "",
        "## Gates",
        f"- repo validation: {'passed' if repo.get('passed') else 'failed'}",
        f"- activation cases: {'passed' if activation.get('passed') else 'failed'}",
        f"- benchmark harness: {'passed' if benchmarks.get('passed') else 'failed'}",
        f"- per-run validations: {run_validations['passing']}/{run_validations['checked']} passing",
        "",
        "## Volatile Claims Due For Review",
    ]
    if not claims:
        lines.append("- none")
    else:
        for claim in claims:
            lines.append(
                f"- {claim['claim_id']} ({claim['owning_skill']}) last reviewed {claim['last_reviewed'] or 'never'}"
            )
    lines.extend(
        [
            "",
            "## Parked Runs",
        ]
    )
    parked = read_jsonl(QUEUE_DIR / "parked.jsonl")
    if not parked:
        lines.append("- none")
    else:
        for record in parked:
            lines.append(f"- {record.get('run_id')}: {record.get('reason')} (parked {record.get('parked_at')})")
    return "\n".join(lines) + "\n"


def daily(config: dict[str, Any]) -> dict[str, Any]:
    timestamp = utc_now()
    today = today_utc()
    repo = run_repo_validation()
    activation = run_activation_cases()
    benchmarks = run_benchmarks()
    run_validations = run_run_validations()
    queue = queue_snapshot()
    claims = claims_due_for_review()

    snapshot_text = render_snapshot(timestamp, repo, activation, benchmarks, run_validations, queue, claims)
    snapshot_path = SNAPSHOTS_DIR / f"{today}.md"
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(snapshot_text, encoding="utf-8")

    summary = {
        "timestamp": timestamp,
        "snapshot": str(snapshot_path.relative_to(ROOT)),
        "passing": all([repo.get("passed"), activation.get("passed"), benchmarks.get("passed")]),
        "queue": queue,
        "claims_due_for_review": len(claims),
        "run_validations": {
            "checked": run_validations["checked"],
            "passing": run_validations["passing"],
        },
    }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Run daily ops for the autonomous research loop")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    config = load_config()
    result = daily(config)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(
            f"daily: snapshot={result['snapshot']} "
            f"queue=inbox{result['queue']['inbox']}/active{result['queue']['active']}/parked{result['queue']['parked']} "
            f"all_gates_pass={result['passing']}"
        )
    return 0 if result["passing"] else 1


if __name__ == "__main__":
    sys.exit(main())
