#!/usr/bin/env python3
"""Deterministically compare medium and xhigh effectiveness summaries."""

from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any


def exact_two_sided(improvements: int, regressions: int) -> float:
    discordant = improvements + regressions
    if not discordant:
        return 1.0
    tail = sum(math.comb(discordant, k) for k in range(0, min(improvements, regressions) + 1))
    return min(1.0, 2.0 * tail / (2**discordant))


def index_records(document: dict[str, Any]) -> dict[tuple[str, str, int], dict[str, Any]]:
    return {
        (str(record["task_id"]), str(record["condition"]), int(record["rep"])): record
        for record in document["records"]
        if record.get("condition") in {"control", "target"}
    }


def scored(record: dict[str, Any] | None) -> bool:
    return bool(record and record.get("status") == "finished" and record.get("score", {}).get("anchors"))


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    finished = [record for record in records if record.get("status") == "finished"]
    scored_records = [record for record in records if scored(record)]
    found = sum(record["score"]["anchors"]["found"] for record in scored_records)
    total = sum(record["score"]["anchors"]["total"] for record in scored_records)
    forbidden = sum(record["score"].get("forbidden", {}).get("violations", 0) for record in scored_records)
    categories: dict[str, dict[str, int]] = defaultdict(lambda: {"found": 0, "total": 0})
    for record in scored_records:
        for name, score in record["score"]["categories"].items():
            categories[name]["found"] += score["found"]
            categories[name]["total"] += score["total"]
    return {
        "records": len(records),
        "finished": len(finished),
        "scored": len(scored_records),
        "runtime_errors": len(records) - len(finished),
        "passed": sum(bool(record.get("passed")) for record in scored_records),
        "pass_rate": round(sum(bool(record.get("passed")) for record in scored_records) / len(scored_records), 4) if scored_records else None,
        "anchors_found": found,
        "anchors_total": total,
        "anchor_retention_rate": round(found / total, 4) if total else None,
        "forbidden_violations": forbidden,
        "average_duration_ms": round(sum(record["duration_ms"] for record in finished) / len(finished)) if finished else None,
        "average_output_bytes": round(sum(record.get("score", {}).get("structural", {}).get("bytes", 0) for record in scored_records) / len(scored_records)) if scored_records else None,
        "categories": {
            name: {
                **value,
                "retention_rate": round(value["found"] / value["total"], 4) if value["total"] else None,
            }
            for name, value in sorted(categories.items())
        },
    }


def compare(left: dict[tuple[str, str, int], dict[str, Any]], right: dict[tuple[str, str, int], dict[str, Any]], left_condition: str, right_condition: str) -> dict[str, Any]:
    task_reps = sorted({(task, rep) for task, condition, rep in left if condition == left_condition} | {(task, rep) for task, condition, rep in right if condition == right_condition})
    pairs = []
    improvements = regressions = ties = 0
    retention_deltas = []
    duration_ratios = []
    for task, rep in task_reps:
        a = left.get((task, left_condition, rep))
        b = right.get((task, right_condition, rep))
        complete = scored(a) and scored(b)
        row: dict[str, Any] = {"task_id": task, "rep": rep, "complete": complete}
        if complete:
            assert a is not None and b is not None
            a_pass, b_pass = bool(a.get("passed")), bool(b.get("passed"))
            if b_pass and not a_pass:
                outcome = "improvement"
                improvements += 1
            elif a_pass and not b_pass:
                outcome = "regression"
                regressions += 1
            else:
                outcome = "tie"
                ties += 1
            a_rate = a["score"]["anchors"]["retention_rate"]
            b_rate = b["score"]["anchors"]["retention_rate"]
            delta = b_rate - a_rate
            retention_deltas.append(delta)
            if a.get("duration_ms", 0) > 0:
                duration_ratios.append(b.get("duration_ms", 0) / a["duration_ms"])
            row.update({
                "left_passed": a_pass,
                "right_passed": b_pass,
                "outcome": outcome,
                "left_retention": a_rate,
                "right_retention": b_rate,
                "retention_delta_pp": round(delta * 100, 4),
                "left_duration_ms": a.get("duration_ms"),
                "right_duration_ms": b.get("duration_ms"),
            })
        else:
            row["left_status"] = a.get("status") if a else "missing"
            row["right_status"] = b.get("status") if b else "missing"
        pairs.append(row)
    return {
        "planned_pairs": len(task_reps),
        "complete_pairs": sum(row["complete"] for row in pairs),
        "improvements": improvements,
        "regressions": regressions,
        "ties": ties,
        "exact_two_sided_p": exact_two_sided(improvements, regressions),
        "mean_pair_retention_delta_pp": round(statistics.mean(retention_deltas) * 100, 4) if retention_deltas else None,
        "median_duration_ratio": round(statistics.median(duration_ratios), 4) if duration_ratios else None,
        "pairs": pairs,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("medium")
    parser.add_argument("xhigh")
    parser.add_argument("--output", required=True)
    parser.add_argument("--allow-incomplete", action="store_true")
    args = parser.parse_args()
    medium_doc = json.loads(Path(args.medium).read_text())
    xhigh_doc = json.loads(Path(args.xhigh).read_text())
    medium = index_records(medium_doc)
    xhigh = index_records(xhigh_doc)
    by_effort: dict[str, Any] = {}
    for effort, records in (("medium", medium), ("xhigh", xhigh)):
        by_effort[effort] = {
            condition: summarize([record for (_, current, _), record in records.items() if current == condition])
            for condition in ("control", "target")
        }
    comparisons = {
        "xhigh_control_vs_medium_control": compare(medium, xhigh, "control", "control"),
        "xhigh_target_vs_medium_target": compare(medium, xhigh, "target", "target"),
        "xhigh_target_vs_xhigh_control": compare(xhigh, xhigh, "control", "target"),
    }
    runtime_errors = [
        {"task_id": task, "condition": condition, "rep": rep, "notes": record.get("notes", "")[-500:]}
        for (task, condition, rep), record in sorted(xhigh.items())
        if record.get("status") != "finished"
    ]
    complete = all(value["complete_pairs"] == value["planned_pairs"] for value in comparisons.values())
    output = {
        "schema_version": 1,
        "complete": complete,
        "medium_source": str(Path(args.medium).resolve()),
        "xhigh_source": str(Path(args.xhigh).resolve()),
        "medium_repo_sha": medium_doc.get("repo_sha"),
        "xhigh_repo_sha": xhigh_doc.get("repo_sha"),
        "by_effort": by_effort,
        "comparisons": comparisons,
        "xhigh_runtime_errors": runtime_errors,
        "publication_eligible": complete and not runtime_errors,
    }
    Path(args.output).write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({
        "complete": complete,
        "publication_eligible": output["publication_eligible"],
        "runtime_errors": len(runtime_errors),
        "comparisons": {name: {key: value[key] for key in ("complete_pairs", "improvements", "regressions", "ties", "exact_two_sided_p", "median_duration_ratio")} for name, value in comparisons.items()},
    }, indent=2))
    return 0 if output["publication_eligible"] or args.allow_incomplete else 3


if __name__ == "__main__":
    raise SystemExit(main())
