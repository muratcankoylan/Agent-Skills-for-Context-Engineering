#!/usr/bin/env python3
"""Deterministic partial-credit verifier for Stage 3 handoff tasks."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_score(score: dict[str, Any]) -> None:
    runner = Path(".runner")
    runner.mkdir(parents=True, exist_ok=True)
    (runner / "score.json").write_text(
        json.dumps(score, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def evaluate(rubric_path: Path) -> tuple[int, dict[str, Any], str]:
    rubric = json.loads(rubric_path.read_text(encoding="utf-8"))
    output_path = Path(rubric.get("output_file", "HANDOFF.md"))
    source_path = Path(rubric.get("source_file", "history.md"))
    max_bytes = int(rubric.get("max_bytes", 2500))
    min_headings = int(rubric.get("min_headings", 6))
    anchors = rubric.get("anchors", [])
    forbidden = rubric.get("forbidden", [])

    structural: dict[str, Any] = {
        "output_exists": output_path.is_file(),
        "within_budget": False,
        "heading_requirement_met": False,
        "source_unchanged": False,
        "bytes": None,
        "heading_count": 0,
        "max_bytes": max_bytes,
        "min_headings": min_headings,
    }
    text = ""
    if output_path.is_file():
        payload = output_path.read_bytes()
        structural["bytes"] = len(payload)
        structural["within_budget"] = len(payload) <= max_bytes
        text = payload.decode("utf-8", errors="replace")
        heading_count = len(re.findall(r"^#{1,3}\s+", text, flags=re.MULTILINE))
        structural["heading_count"] = heading_count
        structural["heading_requirement_met"] = heading_count >= min_headings

    expected_source_sha = str(rubric.get("source_sha256", ""))
    actual_source_sha = sha256_file(source_path) if source_path.is_file() else None
    structural["source_sha256"] = actual_source_sha
    structural["source_unchanged"] = actual_source_sha == expected_source_sha

    category_totals: dict[str, int] = defaultdict(int)
    category_found: dict[str, int] = defaultdict(int)
    missing: list[dict[str, str]] = []
    found_count = 0
    for anchor in anchors:
        value = str(anchor["value"])
        category = str(anchor["category"])
        category_totals[category] += 1
        found = value in text
        if found:
            found_count += 1
            category_found[category] += 1
        else:
            missing.append({"value": value, "category": category})

    categories = {
        category: {
            "found": category_found[category],
            "total": total,
            "retention_rate": round(category_found[category] / total, 4) if total else 0.0,
        }
        for category, total in sorted(category_totals.items())
    }
    anchor_total = len(anchors)
    forbidden_present = [
        {"value": str(item["value"]), "category": str(item["category"])}
        for item in forbidden
        if str(item["value"]) in text
    ]
    anchors_complete = found_count == anchor_total
    forbidden_clear = not forbidden_present
    structural_complete = all(
        structural[key]
        for key in ("output_exists", "within_budget", "heading_requirement_met", "source_unchanged")
    )
    passed = structural_complete and anchors_complete and forbidden_clear
    score: dict[str, Any] = {
        "schema_version": 1,
        "task_id": rubric.get("task_id"),
        "passed": passed,
        "structural": structural,
        "anchors": {
            "found": found_count,
            "total": anchor_total,
            "retention_rate": round(found_count / anchor_total, 4) if anchor_total else 0.0,
            "missing": missing,
        },
        "forbidden": {
            "violations": len(forbidden_present),
            "total": len(forbidden),
            "violation_rate": round(len(forbidden_present) / len(forbidden), 4) if forbidden else 0.0,
            "present": forbidden_present,
        },
        "categories": categories,
    }

    if not structural["output_exists"]:
        return 21, score, f"missing {output_path}"
    if not structural["within_budget"]:
        return 22, score, f"{output_path} exceeds {max_bytes} bytes: {structural['bytes']}"
    if not structural["heading_requirement_met"]:
        return 23, score, f"expected at least {min_headings} Markdown sections; found {structural['heading_count']}"
    if not anchors_complete:
        values = ", ".join(item["value"] for item in missing)
        return 24, score, f"missing {len(missing)}/{anchor_total} anchors: {values}"
    if not forbidden_clear:
        values = ", ".join(item["value"] for item in forbidden_present)
        return 27, score, f"present {len(forbidden_present)}/{len(forbidden)} forbidden anchors: {values}"
    if not structural["source_unchanged"]:
        return 25, score, f"{source_path} was modified"
    return 0, score, f"handoff_valid bytes={structural['bytes']} anchors={found_count}/{anchor_total}"


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: verify_handoff.py /absolute/path/to/rubric.json", file=sys.stderr)
        return 2
    try:
        code, score, message = evaluate(Path(argv[1]))
        write_score(score)
        stream = sys.stdout if code == 0 else sys.stderr
        print(message, file=stream)
        return code
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        write_score({"schema_version": 1, "passed": False, "scorer_error": str(error)})
        print(f"scorer error: {error}", file=sys.stderr)
        return 26


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
