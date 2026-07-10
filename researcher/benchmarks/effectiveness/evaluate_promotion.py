#!/usr/bin/env python3
"""Evaluate a Stage 3 summary against the locked promotion policy."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


def exact_two_sided_sign_p(improvements: int, regressions: int) -> float:
    discordant = improvements + regressions
    if discordant == 0:
        return 1.0
    smaller = min(improvements, regressions)
    tail = sum(math.comb(discordant, index) for index in range(smaller + 1))
    return min(1.0, 2.0 * tail / (2**discordant))


def paired_outcomes(records: list[dict[str, Any]], comparator: str) -> dict[str, Any]:
    indexed = {
        (record["task_id"], int(record["rep"]), record["condition"]): record
        for record in records
    }
    keys = sorted(
        (task_id, rep)
        for task_id, rep, condition in indexed
        if condition == "target"
    )
    improvements = regressions = ties = missing_pairs = 0
    for task_id, rep in keys:
        target = indexed.get((task_id, rep, "target"))
        baseline = indexed.get((task_id, rep, comparator))
        if target is None or baseline is None:
            missing_pairs += 1
            continue
        target_pass = bool(target.get("passed"))
        baseline_pass = bool(baseline.get("passed"))
        if target_pass and not baseline_pass:
            improvements += 1
        elif baseline_pass and not target_pass:
            regressions += 1
        else:
            ties += 1
    return {
        "improvements": improvements,
        "regressions": regressions,
        "ties": ties,
        "missing_pairs": missing_pairs,
        "exact_two_sided_p": exact_two_sided_sign_p(improvements, regressions),
    }


def gate(name: str, actual: Any, threshold: Any, passed: bool, comparison: str) -> dict[str, Any]:
    return {
        "name": name,
        "actual": actual,
        "comparison": comparison,
        "threshold": threshold,
        "passed": bool(passed),
    }


def evaluate(summary_doc: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    scope = policy["scope"]
    primary = policy["primary_gates"]
    category_policy = policy["category_gates"]
    summary = summary_doc["summary"]
    conditions = summary["conditions"]
    records = summary_doc.get("records", [])
    task_ids = sorted({record["task_id"] for record in records})
    condition_names = sorted({record["condition"] for record in records})
    reps_by_key: dict[tuple[str, str], set[int]] = {}
    for record in records:
        reps_by_key.setdefault((record["task_id"], record["condition"]), set()).add(int(record["rep"]))
    minimum_reps = min((len(value) for value in reps_by_key.values()), default=0)

    design_gates = [
        gate("model", summary_doc.get("models"), [scope["required_model"]], summary_doc.get("models") == [scope["required_model"]], "=="),
        gate("independent_tasks", len(task_ids), scope["minimum_independent_tasks"], len(task_ids) >= scope["minimum_independent_tasks"], ">="),
        gate("conditions", condition_names, sorted(scope["required_conditions"]), condition_names == sorted(scope["required_conditions"]), "=="),
        gate("minimum_replications", minimum_reps, scope["minimum_replications_per_task_condition"], minimum_reps >= scope["minimum_replications_per_task_condition"], ">="),
        gate("total_runs", len(records), scope["minimum_total_runs"], len(records) >= scope["minimum_total_runs"], ">="),
        gate("all_runs_scored", sum(1 for record in records if record.get("score")), len(records), all(record.get("score") for record in records), "=="),
    ]

    target = conditions["target"]
    control = conditions["control"]
    negative = conditions["negative"]
    retention_delta_control_pp = 100 * (target["anchor_retention_rate"] - control["anchor_retention_rate"])
    retention_delta_negative_pp = 100 * (target["anchor_retention_rate"] - negative["anchor_retention_rate"])
    pass_delta_control_pp = 100 * (target["pass_rate"] - control["pass_rate"])
    pass_delta_negative_pp = 100 * (target["pass_rate"] - negative["pass_rate"])
    target_control = paired_outcomes(records, "control")
    target_negative = paired_outcomes(records, "negative")

    primary_gates = [
        gate("target_anchor_retention", target["anchor_retention_rate"], primary["target_anchor_retention_min"], target["anchor_retention_rate"] >= primary["target_anchor_retention_min"], ">="),
        gate("target_minus_control_retention_pp", retention_delta_control_pp, primary["target_minus_control_retention_pp_min"], retention_delta_control_pp >= primary["target_minus_control_retention_pp_min"], ">="),
        gate("target_minus_negative_retention_pp", retention_delta_negative_pp, primary["target_minus_negative_retention_pp_min"], retention_delta_negative_pp >= primary["target_minus_negative_retention_pp_min"], ">="),
        gate("target_minus_control_pass_rate_pp", pass_delta_control_pp, primary["target_minus_control_pass_rate_pp_min"], pass_delta_control_pp >= primary["target_minus_control_pass_rate_pp_min"], ">="),
        gate("target_minus_negative_pass_rate_pp", pass_delta_negative_pp, primary["target_minus_negative_pass_rate_pp_min"], pass_delta_negative_pp >= primary["target_minus_negative_pass_rate_pp_min"], ">="),
        gate("paired_target_vs_control_p", target_control["exact_two_sided_p"], primary["paired_target_vs_control_exact_p_max"], target_control["exact_two_sided_p"] <= primary["paired_target_vs_control_exact_p_max"], "<="),
        gate("paired_target_vs_negative_p", target_negative["exact_two_sided_p"], primary["paired_target_vs_negative_exact_p_max"], target_negative["exact_two_sided_p"] <= primary["paired_target_vs_negative_exact_p_max"], "<="),
        gate("target_vs_control_regressions", target_control["regressions"], primary["target_pairwise_regressions_max"], target_control["regressions"] <= primary["target_pairwise_regressions_max"], "<="),
        gate("target_vs_negative_regressions", target_negative["regressions"], primary["target_pairwise_regressions_max"], target_negative["regressions"] <= primary["target_pairwise_regressions_max"], "<="),
        gate("target_forbidden_violations", target.get("forbidden_violations", 0), primary["target_forbidden_violations_max"], target.get("forbidden_violations", 0) <= primary["target_forbidden_violations_max"], "<="),
    ]

    category_gates: list[dict[str, Any]] = []
    categories = sorted(set(target.get("categories", {})) | set(control.get("categories", {})) | set(negative.get("categories", {})))
    for category in categories:
        target_rate = target["categories"][category]["retention_rate"]
        control_rate = control["categories"][category]["retention_rate"]
        negative_rate = negative["categories"][category]["retention_rate"]
        category_gates.extend([
            gate(f"{category}.target_retention", target_rate, category_policy["target_category_retention_min"], target_rate >= category_policy["target_category_retention_min"], ">="),
            gate(f"{category}.target_minus_control_pp", 100 * (target_rate - control_rate), category_policy["target_minus_control_category_pp_floor"], 100 * (target_rate - control_rate) >= category_policy["target_minus_control_category_pp_floor"], ">="),
            gate(f"{category}.target_minus_negative_pp", 100 * (target_rate - negative_rate), category_policy["target_minus_negative_category_pp_floor"], 100 * (target_rate - negative_rate) >= category_policy["target_minus_negative_category_pp_floor"], ">="),
        ])

    all_gates = design_gates + primary_gates + category_gates
    passed = all(item["passed"] for item in all_gates)
    return {
        "policy_id": policy["policy_id"],
        "summary_repo_sha": summary_doc.get("repo_sha"),
        "passed": passed,
        "automated_outcome": "promotion_candidate" if passed else "not_eligible",
        "human_review_required": True,
        "design_gates": design_gates,
        "primary_gates": primary_gates,
        "category_gates": category_gates,
        "paired": {"target_vs_control": target_control, "target_vs_negative": target_negative},
        "failed_gates": [item["name"] for item in all_gates if not item["passed"]],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("summary", type=Path)
    parser.add_argument("--policy", type=Path, default=Path(__file__).with_name("acceptance-policy.json"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = evaluate(json.loads(args.summary.read_text()), json.loads(args.policy.read_text()))
    payload = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(payload)
    print(payload, end="")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
