#!/usr/bin/env python3
"""Human-facing status dashboard for the supervised legacy loop."""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

if __package__:
    from .loop_daily import queue_snapshot
    from .run_benchmarks import repository_state
    from .validate_run import RunValidator
    from .loop_common import (
        REPORTS_DIR,
        RESEARCHER,
        ROOT,
        initialize_runtime_queue_ledgers,
        strict_json_loads,
        today_utc,
        utc_now,
        write_text,
    )
else:  # Direct script execution.
    from loop_daily import queue_snapshot
    from run_benchmarks import repository_state
    from validate_run import RunValidator
    from loop_common import (
        REPORTS_DIR,
        RESEARCHER,
        ROOT,
        initialize_runtime_queue_ledgers,
        strict_json_loads,
        today_utc,
        utc_now,
        write_text,
    )


STATUS_FILE = REPORTS_DIR / "status.md"
PARKED_REVIEW_FILE = REPORTS_DIR / "parked-review.md"
MAX_BENCHMARK_AGE = timedelta(hours=24)
EXPECTED_CHECKS = {
    "repo-validation",
    "activation-cases",
    "scenario-catalog-consistency",
}
EXECUTABLE_CHECKS = {"repo-validation", "activation-cases"}
CATALOG_CHECK = "scenario-catalog-consistency"


def _validate_executable_check(check: dict[str, Any]) -> None:
    if check.get("kind") != "executable_check":
        raise ValueError(
            f"benchmark history {check.get('name')} kind is invalid"
        )
    if type(check.get("passed")) is not bool:
        raise ValueError("benchmark history check results must be boolean")
    exit_code = check.get("exit_code")
    if exit_code is not None and type(exit_code) is not int:
        raise ValueError("benchmark history executable exit_code is invalid")
    stdout_json = check.get("stdout_json")
    if stdout_json is not None and not isinstance(stdout_json, dict):
        raise ValueError("benchmark history executable stdout_json is invalid")
    if not isinstance(check.get("stderr"), str):
        raise ValueError("benchmark history executable stderr is invalid")
    failure_reason = check.get("failure_reason")
    if check["passed"]:
        if exit_code != 0 or not isinstance(stdout_json, dict) or stdout_json.get("ok") is not True:
            raise ValueError(
                "benchmark history executable pass lacks a passing execution result"
            )
        if failure_reason is not None:
            raise ValueError(
                "benchmark history passing executable has a failure reason"
            )
    elif not isinstance(failure_reason, str) or not failure_reason.strip():
        raise ValueError(
            "benchmark history failed executable lacks a failure reason"
        )


def _validate_catalog_check(check: dict[str, Any]) -> None:
    if check.get("kind") != "catalog_validation":
        raise ValueError("benchmark history catalog kind is invalid")
    if type(check.get("passed")) is not bool:
        raise ValueError("benchmark history check results must be boolean")
    if type(check.get("catalog_entries")) is not int or check["catalog_entries"] < 0:
        raise ValueError("benchmark history catalog entry count is invalid")
    if check.get("executed_scenarios") != 0:
        raise ValueError("benchmark history catalog must report zero executed scenarios")
    if check.get("execution_status") != "not_executed":
        raise ValueError("benchmark history catalog execution status is invalid")
    if not isinstance(check.get("scope"), str) or not check["scope"].strip():
        raise ValueError("benchmark history catalog scope is missing")
    failures = check.get("failures")
    if not isinstance(failures, list):
        raise ValueError("benchmark history catalog failures must be a list")
    if check["passed"] is (len(failures) != 0):
        raise ValueError("benchmark history catalog result disagrees with failures")


def validate_benchmark_record(record: dict[str, Any]) -> datetime:
    if record.get("schema_version") != "1.0.0":
        raise ValueError("benchmark history schema_version is unsupported")
    timestamp = record.get("timestamp")
    if not isinstance(timestamp, str):
        raise ValueError("benchmark history timestamp is missing")
    try:
        observed_at = datetime.fromisoformat(timestamp)
    except ValueError as exc:
        raise ValueError("benchmark history timestamp is invalid") from exc
    if observed_at.tzinfo is None:
        raise ValueError("benchmark history timestamp must be timezone-aware")
    if type(record.get("ok")) is not bool:
        raise ValueError("benchmark history ok must be boolean")
    repository = record.get("repository")
    if not isinstance(repository, dict):
        raise ValueError("benchmark history repository binding is missing")
    for key in ("head", "tree"):
        value = repository.get(key)
        if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{40,64}", value):
            raise ValueError(f"benchmark history repository.{key} is invalid")
    if type(repository.get("tracked_clean")) is not bool:
        raise ValueError("benchmark history repository.tracked_clean must be boolean")
    checks = record.get("checks")
    if not isinstance(checks, list):
        raise ValueError("benchmark history checks must be a list")
    if any(not isinstance(check, dict) for check in checks):
        raise ValueError("benchmark history checks must contain objects")
    names = {check.get("name") for check in checks}
    if names != EXPECTED_CHECKS or len(checks) != len(EXPECTED_CHECKS):
        raise ValueError("benchmark history check identities are incomplete")
    checks_by_name = {check["name"]: check for check in checks}
    for name in EXECUTABLE_CHECKS:
        _validate_executable_check(checks_by_name[name])
    _validate_catalog_check(checks_by_name[CATALOG_CHECK])
    computed_ok = all(check["passed"] for check in checks)
    if record.get("ok") is not computed_ok:
        raise ValueError("benchmark history ok disagrees with check results")
    summary = record.get("summary")
    if not isinstance(summary, dict):
        raise ValueError("benchmark history summary is missing")
    expected_summary = {
        "checks": len(checks),
        "executable_checks": 2,
        "failures": sum(not check["passed"] for check in checks),
        "executed_scenarios": 0,
    }
    for key, expected in expected_summary.items():
        if type(summary.get(key)) is not int or summary[key] != expected:
            raise ValueError(f"benchmark history summary.{key} is inconsistent")
    if type(summary.get("catalog_entries")) is not int or summary["catalog_entries"] < 0:
        raise ValueError("benchmark history summary.catalog_entries is invalid")
    catalog = checks_by_name[CATALOG_CHECK]
    if summary["catalog_entries"] != catalog["catalog_entries"]:
        raise ValueError(
            "benchmark history summary.catalog_entries disagrees with catalog"
        )
    if record.get("recording_error") is not None:
        raise ValueError("benchmark history records an unreproducible checkout")
    if repository.get("tracked_clean") is not True:
        raise ValueError("benchmark history records a dirty checkout")
    return observed_at.astimezone(timezone.utc)


def latest_benchmark() -> dict[str, Any] | None:
    history = REPORTS_DIR / "benchmark-history.jsonl"
    try:
        path_info = os.lstat(history)
    except FileNotFoundError:
        return None
    if (
        stat.S_ISLNK(path_info.st_mode)
        or not stat.S_ISREG(path_info.st_mode)
        or path_info.st_nlink != 1
    ):
        raise ValueError("benchmark history must be a single-link regular file")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(history, flags)
    try:
        descriptor_info = os.fstat(descriptor)
        if (
            not stat.S_ISREG(descriptor_info.st_mode)
            or descriptor_info.st_nlink != 1
            or (descriptor_info.st_dev, descriptor_info.st_ino)
            != (path_info.st_dev, path_info.st_ino)
        ):
            raise ValueError("benchmark history identity changed before reading")
        with os.fdopen(descriptor, "r", encoding="utf-8") as handle:
            descriptor = -1
            payload = handle.read()
        final_info = os.lstat(history)
        if (
            final_info.st_nlink != 1
            or (final_info.st_dev, final_info.st_ino)
            != (path_info.st_dev, path_info.st_ino)
        ):
            raise ValueError("benchmark history identity changed while reading")
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    last: dict[str, Any] | None = None
    prior_timestamp: datetime | None = None
    for line in payload.splitlines():
        if not line.strip():
            continue
        value = strict_json_loads(line)
        if not isinstance(value, dict):
            raise ValueError("benchmark history entries must be objects")
        observed_at = validate_benchmark_record(value)
        if prior_timestamp is not None and observed_at < prior_timestamp:
            raise ValueError("benchmark history timestamps move backward")
        prior_timestamp = observed_at
        last = value
    return last


def latest_snapshot() -> Path | None:
    snapshot_dir = REPORTS_DIR / "snapshots"
    if not snapshot_dir.exists():
        return None
    candidates = sorted(snapshot_dir.glob("*.md"))
    return candidates[-1] if candidates else None


def render_status() -> dict[str, Any]:
    queue_health = queue_snapshot(include_details=True)
    if queue_health.get("parse_ok") is not True:
        raise ValueError(
            f"queue parsing failed: {queue_health.get('parse_error') or 'unknown error'}"
        )
    if queue_health.get("referential_ok") is not True:
        errors = queue_health.get("referential_errors") or ["unknown error"]
        raise ValueError(f"queue/run integrity failed: {'; '.join(errors)}")
    if queue_health.get("unknown") != 0:
        raise ValueError(
            f"unknown or unsafe run entries: {queue_health.get('unknown')}"
        )
    buckets = queue_health.pop("_buckets")
    states = queue_health.pop("_states")
    records = queue_health.pop("_records")
    parked = records["parked"]
    inbox = records["inbox"]
    quarantine = records["quarantine"]
    done = records["done_ledger"]
    run_integrity: list[dict[str, Any]] = []
    for run_dir in buckets["active"] + buckets["parked"] + buckets["closed"]:
        validator = RunValidator(run_dir, integrity_only=True)
        validator.root = ROOT
        result = validator.run()
        run_integrity.append(result)
    bench = latest_benchmark()
    snapshot = latest_snapshot()
    health_errors: list[str] = []
    if queue_health.get("pending_reap") != 0:
        health_errors.append(
            f"closed runs pending reap: {queue_health.get('pending_reap')}"
        )
    failed_runs = [result for result in run_integrity if result.get("ok") is not True]
    if failed_runs:
        health_errors.append(
            "current run integrity failed: "
            + ", ".join(str(result.get("run_dir")) for result in failed_runs)
        )
    if bench is None:
        health_errors.append("no deterministic-check history is available")
    else:
        observed_at = validate_benchmark_record(bench)
        now = datetime.now(timezone.utc)
        if observed_at > now + timedelta(minutes=5) or now - observed_at > MAX_BENCHMARK_AGE:
            health_errors.append("latest deterministic checks are stale or future-dated")
        current_repository = repository_state()
        if bench.get("repository") != current_repository:
            health_errors.append("latest deterministic checks bind a different tracked checkout")
        if current_repository.get("tracked_clean") is not True:
            health_errors.append("tracked checkout is dirty")
        checks = bench.get("checks", [])
        if not checks or not all(check.get("passed") is True for check in checks):
            health_errors.append("latest deterministic checks did not pass")

    lines = [
        "# Researcher Loop Status",
        f"_generated {utc_now()}_",
        "",
        "## Overall Health",
        f"- {'passing' if not health_errors else 'failed'}",
    ]
    if health_errors:
        lines.extend(f"- error: {error}" for error in health_errors)
    lines.extend(
        [
        "",
        "## Queue",
        f"- inbox: {len(inbox)}",
        f"- active runs: {len(buckets['active'])}",
        f"- parked runs: {len(parked)}",
        f"- closed runs (state): {len(buckets['closed'])}",
        f"- done ledger: {len(done)}",
        f"- quarantined: {len(quarantine)}",
        f"- unknown or unsafe run entries: {len(buckets['unknown'])}",
        f"- closed runs pending reap: {queue_health.get('pending_reap', 0)}",
        f"- runs created today: {sum(1 for state in states.values() if state and state.get('created_at', '').startswith(today_utc()))}",
        "",
        "## Latest Deterministic Checks",
        ]
    )
    if bench:
        summary = bench.get("summary", {})
        lines.extend(
            [
                f"- timestamp: {bench.get('timestamp')}",
                f"- ok: {bench.get('ok')}",
                f"- checks: {summary.get('checks')} failures: {summary.get('failures')}",
                f"- catalog entries: {summary.get('catalog_entries')} scenarios executed: {summary.get('executed_scenarios')}",
            ]
        )
    else:
        lines.append("- no benchmark history yet")
    lines.append("")
    lines.append("## Latest Snapshot")
    lines.append(f"- {snapshot.relative_to(ROOT)}" if snapshot else "- no snapshot yet")
    lines.append("")
    lines.append("## Active Runs")
    if not buckets["active"]:
        lines.append("- none")
    for run_dir in buckets["active"]:
        state = states.get(run_dir.name) or {}
        lines.append(
            f"- {run_dir.name}: state={state.get('current_state')} updated={state.get('updated_at')}"
        )
    lines.append("")
    lines.append("## Parked Runs")
    if not parked:
        lines.append("- none")
    for record in parked:
        lines.append(f"- {record.get('run_id')}: {record.get('reason')} (parked {record.get('parked_at')})")
    lines.append("")
    lines.append("## Inbox Preview")
    if not inbox:
        lines.append("- empty")
    for record in inbox[:5]:
        lines.append(f"- {record.get('source_id')} {record.get('title') or '[untitled]'}")

    write_text(STATUS_FILE, "\n".join(lines) + "\n")

    if parked:
        parked_lines = ["# Parked Runs Needing Review", f"_generated {utc_now()}_", ""]
        for record in parked:
            run_dir = RESEARCHER / "runs" / record.get("run_id", "")
            state = states.get(run_dir.name) or {}
            parked_lines.extend(
                [
                    f"## {record.get('run_id')}",
                    f"- reason: {record.get('reason')}",
                    f"- parked at: {record.get('parked_at')}",
                    f"- current state: {state.get('current_state')}",
                    f"- title: {state.get('title')}",
                    "- source: retained in private run state; not projected here",
                    f"- thread: {(run_dir / 'THREAD.md').relative_to(ROOT) if (run_dir / 'THREAD.md').exists() else 'missing'}",
                    "",
                ]
            )
        write_text(PARKED_REVIEW_FILE, "\n".join(parked_lines))
    elif PARKED_REVIEW_FILE.exists():
        write_text(PARKED_REVIEW_FILE, "# Parked Runs Needing Review\n\n- none\n")

    return {
        "ok": not health_errors,
        "rendered": True,
        "health_errors": health_errors,
        "status_path": str(STATUS_FILE.relative_to(ROOT)),
        "parked_review_path": str(PARKED_REVIEW_FILE.relative_to(ROOT)) if parked else None,
        "queue": {
            "inbox": len(inbox),
            "active": len(buckets["active"]),
            "parked": len(parked),
            "closed": len(buckets["closed"]),
            "done": len(done),
            "quarantine": len(quarantine),
            "unknown": len(buckets["unknown"]),
            "pending_reap": queue_health.get("pending_reap", 0),
        },
        "runs_created_today": sum(
            1
            for state in states.values()
            if state and state.get("created_at", "").startswith(today_utc())
        ),
        "latest_benchmark_ok": (
            all(check.get("passed") is True for check in bench.get("checks", []))
            if bench
            else None
        ),
        "run_integrity": run_integrity,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Write loop status dashboard")
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--initialize-runtime",
        action="store_true",
        help="create missing empty runtime queue ledgers before checking status",
    )
    args = parser.parse_args()
    if args.initialize_runtime:
        try:
            created = initialize_runtime_queue_ledgers()
            health = queue_snapshot()
            valid = (
                health.get("parse_ok") is True
                and health.get("referential_ok") is True
                and health.get("unknown") == 0
                and health.get("pending_reap") == 0
            )
            result = {
                "ok": valid,
                "initialized": True,
                "validated": valid,
                "created": [str(path.relative_to(ROOT)) for path in created],
                "queue": health,
            }
        except (OSError, UnicodeError, ValueError) as exc:
            result = {"ok": False, "initialized": False, "error": str(exc)}
        if args.json:
            print(json.dumps(result, indent=2))
        elif result["ok"]:
            print(
                f"runtime ledgers ready; created={len(result['created'])}; "
                f"validated={result['validated']}"
            )
        else:
            error = result.get("error") or result.get("queue", {}).get(
                "parse_error"
            ) or "; ".join(
                result.get("queue", {}).get("referential_errors", [])
            )
            print(f"runtime initialization failed: {error}", file=sys.stderr)
        return 0 if result["ok"] else 1
    try:
        result = render_status()
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, RuntimeError) as exc:
        error = str(exc)
        try:
            write_text(
                STATUS_FILE,
                "\n".join(
                    [
                        "# Researcher Loop Status",
                        f"_generated {utc_now()}_",
                        "",
                        "## Overall Health",
                        "- failed",
                        f"- error: {error}",
                        "",
                    ]
                ),
            )
        except (OSError, UnicodeError, ValueError, RuntimeError) as invalidation_exc:
            result = {
                "ok": False,
                "rendered": False,
                "error": error,
                "invalidation_error": str(invalidation_exc),
            }
        else:
            result = {
                "ok": False,
                "rendered": True,
                "error": error,
                "health_errors": [error],
                "status_path": str(STATUS_FILE.relative_to(ROOT)),
                "parked_review_path": None,
            }
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result.get("rendered"):
            print(f"status written to {result['status_path']}")
            if result["parked_review_path"]:
                print(f"parked review at {result['parked_review_path']}")
            for error in result.get("health_errors", []):
                print(f"health failed: {error}", file=sys.stderr)
        else:
            print(f"status failed: {result['error']}", file=sys.stderr)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
