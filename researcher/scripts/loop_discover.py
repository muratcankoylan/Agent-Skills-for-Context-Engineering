#!/usr/bin/env python3
"""Discover candidate sources and append them to the inbox.

The discoverer only reads `researcher/discovery/manual-seed.jsonl`. Network
feed flags are unsupported and fail closed.
"""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from pathlib import Path
from typing import Any

if __package__:
    from .loop_common import (
        QUEUE_DIR,
        RESEARCHER,
        active_run_urls,
        closed_run_urls,
        load_config,
        normalize_source_url,
        queue_lock,
        read_jsonl,
        require_runtime_queue_directory,
        require_runtime_queue_ledgers,
        source_id_for,
        strict_json_loads,
        utc_now,
        write_jsonl,
    )
    from .loop_daily import queue_record_errors, queue_snapshot
else:  # Direct script execution.
    from loop_common import (
        QUEUE_DIR,
        RESEARCHER,
        active_run_urls,
        closed_run_urls,
        load_config,
        normalize_source_url,
        queue_lock,
        read_jsonl,
        require_runtime_queue_directory,
        require_runtime_queue_ledgers,
        source_id_for,
        strict_json_loads,
        utc_now,
        write_jsonl,
    )
    from loop_daily import queue_record_errors, queue_snapshot


SOURCE_TYPES = frozenset(
    {"paper", "engineering_blog", "documentation", "benchmark", "code", "talk", "other"}
)


def load_manual_seed(path: Path) -> list[dict[str, Any]]:
    expected = Path(os.path.abspath(RESEARCHER / "discovery" / "manual-seed.jsonl"))
    candidate = Path(os.path.abspath(path))
    if candidate != expected:
        raise ValueError(f"manual-seed path must be {expected}")
    for component, expected_type in (
        (Path(os.path.abspath(RESEARCHER)), stat.S_ISDIR),
        (candidate.parent, stat.S_ISDIR),
        (candidate, stat.S_ISREG),
    ):
        try:
            info = os.lstat(component)
        except OSError as exc:
            raise ValueError(f"manual-seed input is unavailable: {component}") from exc
        if stat.S_ISLNK(info.st_mode) or not expected_type(info.st_mode):
            raise ValueError(f"manual-seed input has an unsafe identity: {component}")
        if stat.S_ISREG(info.st_mode) and info.st_nlink != 1:
            raise ValueError(f"manual-seed input must be a single-link file: {component}")
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(candidate.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = strict_json_loads(line)
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValueError(f"manual-seed line {line_number} invalid JSON: {exc}") from exc
        if not isinstance(record, dict):
            raise ValueError(f"manual-seed line {line_number} must be an object")
        records.append(record)
    return records


def existing_urls(inbox: list[dict[str, Any]], quarantine: list[dict[str, Any]]) -> set[str]:
    urls: set[str] = set()
    for record in inbox + quarantine:
        url = record.get("url")
        if isinstance(url, str):
            urls.add(normalize_source_url(url))
    urls.update(normalize_source_url(value) for value in active_run_urls())
    urls.update(normalize_source_url(value) for value in closed_run_urls())
    return urls


def normalize_candidate(record: dict[str, Any], feed: str) -> dict[str, Any]:
    raw_url = str(record.get("url", "")).strip()
    if not raw_url:
        raise ValueError("candidate is missing url")
    normalized = normalize_source_url(raw_url)
    source_type = str(record.get("source_type", "other")).strip()
    if source_type not in SOURCE_TYPES:
        raise ValueError("candidate source_type is invalid")
    return {
        "source_id": source_id_for(normalized),
        "url": raw_url,
        "url_normalized": normalized,
        "title": str(record.get("title", "")).strip(),
        "author_or_org": str(record.get("author_or_org", "")).strip(),
        "source_type": source_type,
        "candidate_reason": str(record.get("candidate_reason", "")).strip(),
        "feed": feed,
        "discovered_at": utc_now(),
        "attempts": 0,
        "last_status": "queued",
    }


def discover(config: dict[str, Any], dry_run: bool, limit: int | None) -> dict[str, Any]:
    feeds = config.get("feeds", {})
    unsupported = [
        name
        for name in ("enable_parallel_deep_research", "enable_web_search")
        if feeds.get(name) is True
    ]
    if unsupported:
        raise ValueError(
            "unsupported network feed requested: " + ", ".join(sorted(unsupported))
        )
    queue_dir = require_runtime_queue_directory(QUEUE_DIR)
    require_runtime_queue_ledgers(queue_dir)
    inbox_path = queue_dir / "inbox.jsonl"
    quarantine_path = queue_dir / "quarantine.jsonl"
    discovery_max = limit if limit is not None else config.get("limits", {}).get("discovery_max_new_per_run", 8)
    max_inbox_size = config.get("budgets", {}).get("max_inbox_size", 200)
    if type(discovery_max) is not int or discovery_max < 0:
        raise ValueError("discovery_max_new_per_run must be a non-negative integer")
    if type(max_inbox_size) is not int or max_inbox_size < 0:
        raise ValueError("max_inbox_size must be a non-negative integer")

    manual_seed_rel = feeds.get("manual_seed")
    if not isinstance(manual_seed_rel, str) or not manual_seed_rel.strip():
        raise ValueError("feeds.manual_seed must name the required repository seed")
    manual_path = RESEARCHER.parent / manual_seed_rel
    candidates: list[dict[str, Any]] = []
    for index, record in enumerate(load_manual_seed(manual_path), start=1):
        try:
            candidate = normalize_candidate(record, feed="manual-seed")
        except ValueError as exc:
            raise ValueError(f"manual-seed candidate {index} is invalid: {exc}") from exc
        errors = queue_record_errors("inbox", index - 1, candidate)
        if errors:
            raise ValueError("manual-seed candidate is invalid: " + "; ".join(errors))
        candidates.append(candidate)

    snapshot = queue_snapshot(queue_dir=queue_dir, config=config)
    if not (
        snapshot.get("parse_ok") is True
        and snapshot.get("referential_ok") is True
        and snapshot.get("unknown") == 0
    ):
        raise ValueError(
            "runtime queue integrity failed before discovery: "
            + str(snapshot.get("parse_error") or snapshot.get("referential_errors"))
        )

    with queue_lock("inbox"):
        inbox = read_jsonl(inbox_path)
        quarantine = read_jsonl(quarantine_path)
        existing_errors = [
            error
            for name, records in (("inbox", inbox), ("quarantine", quarantine))
            for index, record in enumerate(records)
            for error in queue_record_errors(name, index, record)
        ]
        if existing_errors:
            raise ValueError(
                "existing discovery queues are invalid: " + "; ".join(existing_errors)
            )
        seen = existing_urls(inbox, quarantine)
        new_records: list[dict[str, Any]] = []
        capacity_remaining = max(0, max_inbox_size - len(inbox))
        admission_limit = min(discovery_max, capacity_remaining)
        for candidate in candidates:
            if len(new_records) >= admission_limit:
                break
            key = candidate["url_normalized"]
            if key in seen:
                continue
            new_records.append(candidate)
            seen.add(key)

        if not dry_run and new_records:
            inbox.extend(new_records)
            write_jsonl(inbox_path, inbox)

        return {
            "ok": True,
            "dry_run": dry_run,
            "new": len(new_records),
            "inbox_size": len(inbox) if not dry_run else len(inbox) + len(new_records),
            "capacity_remaining": max(0, capacity_remaining - len(new_records)),
            "first_new": new_records[:3],
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Discover candidate sources and append to inbox")
    parser.add_argument("--dry-run", action="store_true", help="show what would be added without writing")
    parser.add_argument("--limit", type=int, default=None, help="override discovery_max_new_per_run")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    config = load_config()
    result = discover(config, args.dry_run, args.limit)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        suffix = " (dry-run)" if result["dry_run"] else ""
        print(
            f"Discovery added {result['new']} sources{suffix}; "
            f"inbox now {result['inbox_size']}, capacity remaining {result['capacity_remaining']}"
        )
        for record in result["first_new"]:
            print(f"- {record['source_id']} {record['url']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
