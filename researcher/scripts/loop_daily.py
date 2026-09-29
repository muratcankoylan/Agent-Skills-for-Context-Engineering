#!/usr/bin/env python3
"""Daily ops for the supervised file-based research loop.

Validates local runtime integrity first, then runs the deterministic gate
profile once and writes a dated snapshot. Running twice in a day overwrites
the same snapshot; successful gate invocations append runtime-only history.
"""

from __future__ import annotations

import argparse
import json
import os
import stat
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if __package__:
    from .loop_common import (
        QUEUE_DIR,
        RESEARCHER,
        ROOT,
        SNAPSHOTS_DIR,
        categorize_runs,
        list_run_dirs,
        load_config,
        load_run_state,
        normalize_source_url,
        read_jsonl,
        require_runtime_queue_directory,
        require_runtime_queue_ledgers,
        source_id_for,
        strict_json_loads,
        today_utc,
        unknown_run_entries,
        utc_now,
        write_text,
    )
    from .validate_run import MAX_RUNTIME_CLOCK_SKEW, parse_utc_datetime
else:  # Direct script execution.
    from loop_common import (
        QUEUE_DIR,
        RESEARCHER,
        ROOT,
        SNAPSHOTS_DIR,
        categorize_runs,
        list_run_dirs,
        load_config,
        load_run_state,
        normalize_source_url,
        read_jsonl,
        require_runtime_queue_directory,
        require_runtime_queue_ledgers,
        source_id_for,
        strict_json_loads,
        today_utc,
        unknown_run_entries,
        utc_now,
        write_text,
    )
    from validate_run import MAX_RUNTIME_CLOCK_SKEW, parse_utc_datetime

CHECK_TIMEOUT_SECONDS = 300
SOURCE_TYPES = frozenset(
    {"paper", "engineering_blog", "documentation", "benchmark", "code", "talk", "other"}
)
RUN_CLOSE_STATUSES = frozenset({"accepted", "rejected", "reference-only", "abandoned"})
LEGACY_REFERENCE_RUN_ID = "20260515-035228-executable-autonomous-research-frameworks"
WRITABLE_RUN_CLOSE_STATUSES = frozenset({"rejected", "reference-only", "abandoned"})


def _nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def closed_run_projection(
    run_dir: Path, state: dict[str, Any]
) -> tuple[dict[str, Any] | None, list[str]]:
    """Validate the minimal terminal artifact needed for done-ledger projection."""

    errors: list[str] = []
    reports = run_dir / "reports"
    path = reports / "closure.json"
    try:
        reports_info = os.lstat(reports)
        path_info = os.lstat(path)
        if stat.S_ISLNK(reports_info.st_mode) or not stat.S_ISDIR(
            reports_info.st_mode
        ):
            raise ValueError("reports directory is not a real directory")
        if (
            stat.S_ISLNK(path_info.st_mode)
            or not stat.S_ISREG(path_info.st_mode)
            or path_info.st_nlink != 1
        ):
            raise ValueError("closure is not a single-link regular file")
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            descriptor_info = os.fstat(descriptor)
            if (
                not stat.S_ISREG(descriptor_info.st_mode)
                or descriptor_info.st_nlink != 1
                or (descriptor_info.st_dev, descriptor_info.st_ino)
                != (path_info.st_dev, path_info.st_ino)
            ):
                raise ValueError("closure identity changed before reading")
            chunks: list[bytes] = []
            while True:
                chunk = os.read(descriptor, 1024 * 1024)
                if not chunk:
                    break
                chunks.append(chunk)
            descriptor_after = os.fstat(descriptor)
            before_identity = (
                descriptor_info.st_dev,
                descriptor_info.st_ino,
                descriptor_info.st_size,
                descriptor_info.st_mtime_ns,
                descriptor_info.st_ctime_ns,
            )
            after_identity = (
                descriptor_after.st_dev,
                descriptor_after.st_ino,
                descriptor_after.st_size,
                descriptor_after.st_mtime_ns,
                descriptor_after.st_ctime_ns,
            )
            if before_identity != after_identity:
                raise ValueError("closure changed while reading")
            payload = b"".join(chunks).decode("utf-8")
        finally:
            os.close(descriptor)
        final_info = os.lstat(path)
        if (
            final_info.st_nlink != 1
            or (final_info.st_dev, final_info.st_ino)
            != (path_info.st_dev, path_info.st_ino)
        ):
            raise ValueError("closure identity changed while reading")
        closure = strict_json_loads(payload)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return None, [f"closed run closure is unavailable or invalid: {run_dir.name}: {exc}"]
    if not isinstance(closure, dict):
        return None, [f"closed run closure is not an object: {run_dir.name}"]
    if closure.get("status") not in WRITABLE_RUN_CLOSE_STATUSES:
        errors.append(f"closed run closure status is unsupported: {run_dir.name}")
    if closure.get("status") != state.get("close_status"):
        errors.append(f"closure status differs from closed run state: {run_dir.name}")
    if closure.get("reason") != state.get("close_reason"):
        errors.append(f"closure reason differs from closed run state: {run_dir.name}")
    history = state.get("state_history")
    final = history[-1] if isinstance(history, list) and history else {}
    if closure.get("closed_at") != final.get("timestamp"):
        errors.append(f"closure timestamp differs from closed run state: {run_dir.name}")
    integrity_errors = closure.get("integrity_errors")
    if not isinstance(integrity_errors, list) or any(
        not isinstance(message, str) or not message.strip()
        for message in integrity_errors
    ):
        errors.append(f"closure integrity_errors are invalid: {run_dir.name}")
    if not isinstance(closure.get("reviewed_by"), str):
        errors.append(f"closure reviewed_by is invalid: {run_dir.name}")
    return closure, errors


def queue_record_errors(
    name: str,
    index: int,
    record: dict[str, Any],
    *,
    observed_at: datetime | None = None,
) -> list[str]:
    prefix = f"{name}[{index}]"
    errors: list[str] = []
    timestamp_fields: list[str] = []
    if name in {"inbox", "quarantine"}:
        for field in (
            "source_id",
            "url",
            "url_normalized",
            "feed",
            "discovered_at",
            "last_status",
        ):
            if not _nonempty_string(record.get(field)):
                errors.append(f"{prefix}.{field} must be a non-empty string")
        for field in ("title", "author_or_org", "candidate_reason"):
            if not isinstance(record.get(field), str):
                errors.append(f"{prefix}.{field} must be a string")
        if record.get("source_type") not in SOURCE_TYPES:
            errors.append(f"{prefix}.source_type is invalid")
        try:
            normalized_url = normalize_source_url(str(record.get("url", "")))
        except ValueError as exc:
            errors.append(f"{prefix}.url is invalid: {exc}")
        else:
            if record.get("url_normalized") != normalized_url:
                errors.append(f"{prefix}.url_normalized is not canonical")
            if record.get("source_id") != source_id_for(normalized_url):
                errors.append(f"{prefix}.source_id does not match the canonical URL")
        if record.get("feed") != "manual-seed":
            errors.append(f"{prefix}.feed must be manual-seed")
        expected_status = "queued" if name == "inbox" else "quarantined"
        if record.get("last_status") != expected_status:
            errors.append(f"{prefix}.last_status must be {expected_status}")
        if type(record.get("attempts")) is not int or record["attempts"] < 0:
            errors.append(f"{prefix}.attempts must be a non-negative integer")
        if name == "quarantine":
            for field in ("quarantined_at", "quarantine_reason"):
                if not _nonempty_string(record.get(field)):
                    errors.append(f"{prefix}.{field} must be a non-empty string")
        timestamp_fields = ["discovered_at"]
        if name == "quarantine":
            timestamp_fields.append("quarantined_at")
    elif name == "parked":
        for field in ("run_id", "reason", "parked_at"):
            if not _nonempty_string(record.get(field)):
                errors.append(f"{prefix}.{field} must be a non-empty string")
        timestamp_fields = ["parked_at"]
    elif name == "done_ledger":
        for field in ("run_id", "reason", "closed_at", "reaped_at"):
            if not _nonempty_string(record.get(field)):
                errors.append(f"{prefix}.{field} must be a non-empty string")
        if record.get("status") not in RUN_CLOSE_STATUSES:
            errors.append(f"{prefix}.status is invalid")
        timestamp_fields = ["closed_at", "reaped_at"]

    observation_time = observed_at or datetime.now(timezone.utc)
    parsed_times: dict[str, datetime] = {}
    for field in timestamp_fields:
        parsed = parse_utc_datetime(record.get(field))
        if parsed is None:
            errors.append(f"{prefix}.{field} must be a timezone-aware UTC timestamp")
        else:
            parsed_times[field] = parsed
            if parsed > observation_time + MAX_RUNTIME_CLOCK_SKEW:
                errors.append(f"{prefix}.{field} is future-dated")
    if (
        "discovered_at" in parsed_times
        and "quarantined_at" in parsed_times
        and parsed_times["quarantined_at"] < parsed_times["discovered_at"]
    ):
        errors.append(f"{prefix}.quarantined_at precedes discovered_at")
    if (
        "closed_at" in parsed_times
        and "reaped_at" in parsed_times
        and parsed_times["reaped_at"] < parsed_times["closed_at"]
    ):
        errors.append(f"{prefix}.reaped_at precedes closed_at")
    return errors


def run_subprocess(cmd: list[str]) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            cmd,
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=CHECK_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "exit_code": None,
            "passed": False,
            "stdout_json": None,
            "stderr": str(exc),
            "failure_reason": f"timeout after {CHECK_TIMEOUT_SECONDS} seconds",
        }
    except OSError as exc:
        return {
            "exit_code": None,
            "passed": False,
            "stdout_json": None,
            "stderr": str(exc),
            "failure_reason": f"checker could not start: {exc}",
        }
    parsed: Any = None
    if completed.stdout.strip():
        try:
            parsed = strict_json_loads(completed.stdout)
        except (json.JSONDecodeError, ValueError):
            parsed = None
    reported_ok = isinstance(parsed, dict) and parsed.get("ok") is True
    passed = completed.returncode == 0 and reported_ok
    return {
        "exit_code": completed.returncode,
        "passed": passed,
        "stdout_json": parsed,
        "stderr": completed.stderr.strip(),
        "failure_reason": (
            None
            if passed
            else "nonzero exit"
            if completed.returncode != 0
            else "missing or non-passing JSON result"
        ),
    }


def run_benchmarks() -> dict[str, Any]:
    return run_subprocess([sys.executable, str(RESEARCHER / "scripts" / "run_benchmarks.py"), "--record", "--json"])


def project_benchmark_check(
    benchmarks: dict[str, Any], check_name: str
) -> dict[str, Any]:
    payload = benchmarks.get("stdout_json")
    checks = payload.get("checks") if isinstance(payload, dict) else None
    if not isinstance(checks, list):
        return {
            "name": check_name,
            "passed": False,
            "failure_reason": "deterministic profile did not return a check list",
        }
    for check in checks:
        if isinstance(check, dict) and check.get("name") == check_name:
            return {
                "name": check_name,
                "passed": check.get("passed") is True,
                "failure_reason": check.get("failure_reason"),
            }
    return {
        "name": check_name,
        "passed": False,
        "failure_reason": "deterministic profile omitted the required check",
    }


def run_run_validations(run_dirs: list[Any] | None = None) -> dict[str, Any]:
    if run_dirs is None:
        try:
            buckets = categorize_runs()
            run_dirs = buckets["active"] + buckets["parked"] + buckets["closed"]
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            return {
                "checked": 0,
                "passing": 0,
                "passed": False,
                "failure_reason": f"cannot enumerate run state: {exc}",
                "results": [],
            }
    results: list[dict[str, Any]] = []
    for run_dir in run_dirs:
        result = run_subprocess(
            [
                sys.executable,
                str(RESEARCHER / "scripts" / "validate_run.py"),
                "--run-dir",
                str(run_dir),
                "--integrity-only",
                "--json",
            ]
        )
        results.append({"run_id": run_dir.name, **result})
    return {
        "checked": len(results),
        "passing": sum(1 for record in results if record.get("passed")),
        "passed": all(record.get("passed") is True for record in results),
        "results": results,
    }


def queue_snapshot(
    *,
    include_details: bool = False,
    queue_dir: Path | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        queue_dir = require_runtime_queue_directory(
            QUEUE_DIR if queue_dir is None else queue_dir
        )
    except ValueError as exc:
        return {
            "inbox": 0,
            "parked": 0,
            "done_ledger": 0,
            "quarantine": 0,
            "active": 0,
            "closed": 0,
            "unknown": 0,
            "parse_ok": False,
            "parse_error": str(exc),
            "referential_ok": False,
            "referential_errors": ["runtime queue directory identity is invalid"],
        }
    try:
        ledgers = require_runtime_queue_ledgers(queue_dir)
    except ValueError as exc:
        return {
            "inbox": 0,
            "parked": 0,
            "done_ledger": 0,
            "quarantine": 0,
            "active": 0,
            "closed": 0,
            "unknown": 0,
            "parse_ok": False,
            "parse_error": str(exc),
            "referential_ok": False,
            "referential_errors": ["queue ledger identity is invalid"],
        }
    queue_paths = {
        "inbox": ledgers["inbox.jsonl"],
        "parked": ledgers["parked.jsonl"],
        "done_ledger": ledgers["done.jsonl"],
        "quarantine": ledgers["quarantine.jsonl"],
    }
    try:
        records = {
            name: read_jsonl(path, tolerant=False)
            for name, path in queue_paths.items()
        }
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return {
            **{name: 0 for name in queue_paths},
            "active": 0,
            "closed": 0,
            "unknown": 0,
            "parse_ok": False,
            "parse_error": str(exc),
            "referential_ok": False,
            "referential_errors": ["queue records could not be parsed"],
        }

    counts = {name: len(values) for name, values in records.items()}
    observed_at = datetime.now(timezone.utc)
    shape_errors = [
        error
        for name, values in records.items()
        for index, record in enumerate(values)
        for error in queue_record_errors(
            name,
            index,
            record,
            observed_at=observed_at,
        )
    ]
    if shape_errors:
        return {
            **counts,
            "active": 0,
            "closed": 0,
            "unknown": 0,
            "parse_ok": False,
            "parse_error": "; ".join(shape_errors),
            "referential_ok": False,
            "referential_errors": ["queue record shape is invalid"],
        }
    try:
        real_run_paths = list_run_dirs()
        unknown_entries = unknown_run_entries(real_run_paths)
        states = {path.name: load_run_state(path) for path in real_run_paths}
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return {
            **counts,
            "active": 0,
            "closed": 0,
            "unknown": 0,
            "parse_ok": True,
            "parse_error": None,
            "referential_ok": False,
            "referential_errors": [f"run state could not be categorized: {exc}"],
        }
    errors: list[str] = []
    max_parked_limit: int | None = None
    try:
        budgets = (config if config is not None else load_config()).get("budgets", {})
        max_inbox_size = budgets.get("max_inbox_size")
        if type(max_inbox_size) is not int or max_inbox_size < 0:
            errors.append("configured max_inbox_size must be a non-negative integer")
        elif counts["inbox"] > max_inbox_size:
            errors.append(
                f"inbox count {counts['inbox']} exceeds configured "
                f"max_inbox_size {max_inbox_size}"
            )
        configured_max_parked = budgets.get("max_parked")
        if type(configured_max_parked) is not int or configured_max_parked < 0:
            errors.append("configured max_parked must be a non-negative integer")
        else:
            max_parked_limit = configured_max_parked
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        errors.append(f"runtime queue budgets are unavailable or invalid: {exc}")
    real_runs = {path.name: path for path in real_run_paths}
    parked_ids: list[str] = []
    for index, record in enumerate(records["parked"]):
        run_id = record.get("run_id")
        if not isinstance(run_id, str) or not run_id:
            errors.append(f"parked[{index}] has invalid run_id")
            continue
        parked_ids.append(run_id)
        state = states.get(run_id)
        if state is None:
            errors.append(f"parked run does not exist: {run_id}")
    if len(set(parked_ids)) != len(parked_ids):
        errors.append("parked queue contains duplicate run_id values")
    done_ids: list[str] = []
    closure_results: dict[str, tuple[dict[str, Any] | None, list[str]]] = {}
    for index, record in enumerate(records["done_ledger"]):
        run_id = record.get("run_id")
        if not isinstance(run_id, str) or not run_id:
            errors.append(f"done[{index}] has invalid run_id")
            continue
        done_ids.append(run_id)
        state = states.get(run_id)
        if state is None or state.get("current_state") != "closed":
            errors.append(f"done entry is not backed by a closed run: {run_id}")
            continue
        if record.get("status") != state.get("close_status"):
            errors.append(f"done status differs from closed run state: {run_id}")
        if record.get("reason") != state.get("close_reason"):
            errors.append(f"done reason differs from closed run state: {run_id}")
        closure, closure_errors = closed_run_projection(real_runs[run_id], state)
        closure_results[run_id] = (closure, closure_errors)
        errors.extend(closure_errors)
        if closure is None:
            continue
        if closure.get("status") != record.get("status"):
            errors.append(f"done status differs from closure: {run_id}")
        if closure.get("reason") != record.get("reason"):
            errors.append(f"done reason differs from closure: {run_id}")
        if closure.get("closed_at") != record.get("closed_at"):
            errors.append(f"done closed_at differs from closure: {run_id}")
    if len(set(done_ids)) != len(done_ids):
        errors.append("done ledger contains duplicate run_id values")
    for field in ("source_id", "url_normalized"):
        inbox_values = [record[field] for record in records["inbox"]]
        quarantine_values = [record[field] for record in records["quarantine"]]
        if len(set(inbox_values)) != len(inbox_values):
            errors.append(f"inbox contains duplicate {field} values")
        if len(set(quarantine_values)) != len(quarantine_values):
            errors.append(f"quarantine contains duplicate {field} values")
        overlap = set(inbox_values) & set(quarantine_values)
        if overlap:
            errors.append(f"inbox and quarantine overlap on {field}")
    buckets: dict[str, list[Any]] = {
        "active": [],
        "parked": [],
        "closed": [],
        "unknown": list(unknown_entries),
    }
    parked_id_set = set(parked_ids)
    for run_id, run_dir in real_runs.items():
        state = states.get(run_id)
        if state is None:
            buckets["unknown"].append(run_dir)
        elif state.get("current_state") == "closed":
            buckets["closed"].append(run_dir)
        elif run_id in parked_id_set:
            buckets["parked"].append(run_dir)
        else:
            buckets["active"].append(run_dir)

    active_parked_ids = {
        run_id
        for run_id in parked_id_set
        if isinstance(states.get(run_id), dict)
        and states[run_id].get("current_state") != "closed"
    }
    if active_parked_ids != {path.name for path in buckets["parked"]}:
        errors.append("parked queue and run-state projection differ")
    if max_parked_limit is not None and len(active_parked_ids) > max_parked_limit:
        errors.append(
            f"parked count {len(active_parked_ids)} exceeds configured "
            f"max_parked {max_parked_limit}"
        )

    pending_reap: list[Any] = []
    for run_dir in buckets["closed"]:
        state = states.get(run_dir.name) or {}
        exact_reference = (
            run_dir.name == LEGACY_REFERENCE_RUN_ID
            and run_dir.resolve()
            == (ROOT / "researcher" / "runs" / LEGACY_REFERENCE_RUN_ID).resolve()
            and state.get("close_status") == "reference-only"
        )
        if not exact_reference:
            if run_dir.name in closure_results:
                _closure, closure_errors = closure_results[run_dir.name]
            else:
                _closure, closure_errors = closed_run_projection(run_dir, state)
                errors.extend(closure_errors)
            if not closure_errors and (
                run_dir.name not in done_ids or run_dir.name in parked_id_set
            ):
                pending_reap.append(run_dir)

    counts.update(
        {
            "parse_ok": True,
            "parse_error": None,
            "referential_ok": not errors,
            "referential_errors": errors,
        }
    )
    result = {
        **counts,
        "active": len(buckets["active"]),
        "closed": len(buckets["closed"]),
        "unknown": len(buckets["unknown"]),
        "pending_reap": len(pending_reap),
    }
    if include_details:
        result["_records"] = records
        result["_buckets"] = buckets
        result["_states"] = states
        result["_pending_reap"] = pending_reap
    return result


def claims_due_for_review() -> list[dict[str, Any]]:
    claims_path = RESEARCHER / "claims" / "index.jsonl"
    if not claims_path.exists():
        return []
    today = today_utc()
    due: list[dict[str, Any]] = []
    try:
        records = read_jsonl(claims_path, tolerant=False)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return [
            {
                "claim_id": "invalid-claim-ledger",
                "owning_skill": "unknown",
                "last_reviewed": "invalid",
                "invalid": True,
                "error": f"claim ledger could not be parsed: {exc}",
            }
        ]
    for record in records:
        required = {
            "claim_id": record.get("claim_id"),
            "owning_skill": record.get("owning_skill"),
            "volatility": record.get("volatility"),
            "last_reviewed": record.get("last_reviewed"),
        }
        invalid = [
            key
            for key, value in required.items()
            if not isinstance(value, str) or not value.strip()
        ]
        if invalid:
            due.append(
                {
                    "claim_id": str(record.get("claim_id") or "invalid-claim"),
                    "owning_skill": str(record.get("owning_skill") or "unknown"),
                    "last_reviewed": str(record.get("last_reviewed") or "invalid"),
                    "invalid": True,
                    "error": "claim fields must be non-empty strings: "
                    + ", ".join(invalid),
                }
            )
            continue
        if required["volatility"] == "high" and required["last_reviewed"] < today:
            due.append(
                {
                    "claim_id": required["claim_id"],
                    "owning_skill": required["owning_skill"],
                    "last_reviewed": required["last_reviewed"],
                    "invalid": False,
                }
            )
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
        f"- closed runs pending reap: {queue.get('pending_reap', 0)}",
        f"- queue files parse: {'passed' if queue.get('parse_ok') else 'failed'}",
        f"- queue/run references: {'passed' if queue.get('referential_ok') else 'failed'}",
        "",
        "## Gates",
        f"- repo validation: {'passed' if repo.get('passed') else 'failed'}",
        f"- activation cases: {'passed' if activation.get('passed') else 'failed'}",
        f"- deterministic checks and scenario catalog: {'passed' if benchmarks.get('passed') else 'failed'}",
        f"- per-run integrity checks: {run_validations['passing']}/{run_validations['checked']} passing",
        "",
        "## Volatile Claims Due For Review",
    ]
    if not claims:
        lines.append("- none")
    else:
        for claim in claims:
            if claim.get("invalid") is True:
                lines.append(
                    f"- invalid claim record: {claim.get('error')}"
                )
            else:
                lines.append(
                    f"- {claim['claim_id']} ({claim['owning_skill']}) last reviewed {claim['last_reviewed'] or 'never'}"
                )
    lines.extend(
        [
            "",
            "## Parked Runs",
        ]
    )
    parked = queue.get("_records", {}).get("parked", [])
    if not parked:
        lines.append("- none")
    else:
        for record in parked:
            lines.append(f"- {record.get('run_id')}: {record.get('reason')} (parked {record.get('parked_at')})")
    return "\n".join(lines) + "\n"


def daily(config: dict[str, Any]) -> dict[str, Any]:
    timestamp = utc_now()
    today = today_utc()
    queue = queue_snapshot(include_details=True, config=config)
    queue_ok = (
        queue.get("parse_ok") is True
        and queue.get("referential_ok") is True
        and queue.get("unknown") == 0
        and queue.get("pending_reap") == 0
    )
    buckets = queue.get("_buckets") if queue_ok else None
    if isinstance(buckets, dict):
        run_dirs = buckets["active"] + buckets["parked"] + buckets["closed"]
        run_validations = run_run_validations(run_dirs)
    else:
        run_validations = {
            "checked": 0,
            "passing": 0,
            "passed": False,
            "failure_reason": "runtime queue or run-state integrity failed",
            "results": [],
        }
    local_integrity_ok = queue_ok and run_validations.get("passed") is True
    if local_integrity_ok:
        benchmarks = run_benchmarks()
    else:
        benchmarks = {
            "passed": False,
            "stdout_json": None,
            "failure_reason": "deterministic profile skipped after local integrity failure",
        }
    repo = project_benchmark_check(benchmarks, "repo-validation")
    activation = project_benchmark_check(benchmarks, "activation-cases")
    claims = claims_due_for_review()
    claims_valid = not any(claim.get("invalid") is True for claim in claims)

    snapshot_text = render_snapshot(timestamp, repo, activation, benchmarks, run_validations, queue, claims)
    snapshot_path = SNAPSHOTS_DIR / f"{today}.md"
    write_text(snapshot_path, snapshot_text)

    all_run_validations_pass = (
        run_validations.get("passed") is True
        and run_validations.get("passing") == run_validations.get("checked")
    )
    public_queue = {key: value for key, value in queue.items() if not key.startswith("_")}
    summary = {
        "timestamp": timestamp,
        "snapshot": str(snapshot_path.relative_to(ROOT)),
        "passing": all(
            [
                repo.get("passed") is True,
                activation.get("passed") is True,
                benchmarks.get("passed") is True,
                all_run_validations_pass,
                queue.get("unknown") == 0,
                queue.get("pending_reap") == 0,
                queue.get("parse_ok") is True,
                queue.get("referential_ok") is True,
                claims_valid,
            ]
        ),
        "queue": public_queue,
        "claims_due_for_review": len(claims),
        "claims_valid": claims_valid,
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
