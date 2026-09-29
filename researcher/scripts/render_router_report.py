#!/usr/bin/env python3
"""Render a published-quality Markdown report from router benchmark results.

Reads per-run JSON files produced by runRouter.ts and emits:
  - Per-model top-1 / top-3 accuracy with bootstrap 95% CIs
  - Per-model format failure rate
  - Per-model wall time stats
  - Per-skill confusion matrix (when expected was X, what was predicted)
  - Per-prompt cross-model agreement and per-prompt failures
  - Per-rep consistency check (within-prompt-model)

Usage:
  python3 researcher/scripts/render_router_report.py \
      --results researcher/benchmarks/router/results/<date>-<seed> \
      --fixture researcher/benchmarks/router/prompts.jsonl \
      --output researcher/benchmarks/router/results-published/<date>.md

The output is committed; raw per-run JSONs stay gitignored.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


KNOWN_STATUSES = {
    "finished",
    "format_failure",
    "error",
    "cancelled",
    "model_unavailable",
    "dry_run",
}


def strict_json_loads(text: str, label: str) -> Any:
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise ValueError(f"duplicate JSON key {key!r} in {label}")
            value[key] = item
        return value

    try:
        return json.loads(text, object_pairs_hook=reject_duplicates)
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid JSON in {label}: {error}") from error


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if line.strip():
            value = strict_json_loads(line, f"{path}:{line_number}")
            if not isinstance(value, dict):
                raise ValueError(f"JSONL record must be an object: {path}:{line_number}")
            records.append(value)
    return records


def load_run_records(results_dir: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted(results_dir.glob("*.json")):
        if path.name == "summary.json":
            continue
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"router result is not a regular file: {path}")
        try:
            data = strict_json_loads(path.read_text(encoding="utf-8"), str(path))
        except ValueError as error:
            raise ValueError(f"invalid router result JSON: {error}") from error
        if not isinstance(data, dict):
            raise ValueError(f"router result must be an object: {path}")
        records.append(data)
    return records


def fixture_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def load_summary_metadata(summary_path: Path, expected_fixture_digest: str) -> dict[str, Any]:
    if not summary_path.exists():
        raise ValueError(f"router summary is missing: {summary_path}")
    if summary_path.is_symlink() or not summary_path.is_file():
        raise ValueError(f"router summary is not a regular file: {summary_path}")
    try:
        summary = strict_json_loads(summary_path.read_text(encoding="utf-8"), str(summary_path))
    except ValueError as error:
        raise ValueError(f"invalid router summary JSON: {error}") from error
    if not isinstance(summary, dict):
        raise ValueError(f"router summary must be an object: {summary_path}")
    if summary.get("fixture_sha") != expected_fixture_digest:
        raise ValueError(
            "router summary fixture digest does not match the supplied fixture: "
            f"{summary.get('fixture_sha')!r} != {expected_fixture_digest!r}"
        )
    if not isinstance(summary.get("seed"), int) or isinstance(summary.get("seed"), bool):
        raise ValueError("router summary seed must be an integer")
    if not isinstance(summary.get("reps"), int) or isinstance(summary.get("reps"), bool):
        raise ValueError("router summary reps must be an integer")
    if summary["reps"] <= 0:
        raise ValueError("router summary reps must be positive")
    models = summary.get("models")
    if (
        not isinstance(models, list)
        or not models
        or any(not isinstance(model, str) or not model for model in models)
        or len(set(models)) != len(models)
    ):
        raise ValueError("router summary models must be unique non-empty strings")
    return summary


def build_prompt_index(prompts_list: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    prompts: dict[str, dict[str, Any]] = {}
    for index, prompt in enumerate(prompts_list, start=1):
        if not isinstance(prompt, dict):
            raise ValueError(f"router fixture record {index} must be an object")
        prompt_id = prompt.get("prompt_id")
        expected = prompt.get("expected_primary_skill")
        if not isinstance(prompt_id, str) or not prompt_id:
            raise ValueError(f"router fixture record {index} requires prompt_id")
        if not isinstance(expected, str) or not expected:
            raise ValueError(f"router fixture {prompt_id} requires expected_primary_skill")
        if prompt_id in prompts:
            raise ValueError(f"router fixture contains duplicate prompt_id {prompt_id}")
        prompts[prompt_id] = prompt
    return prompts


def expected_shuffle_seed(prompt_id: str, model_id: str, rep: int, seed: int) -> int:
    identity = f"{prompt_id}|{model_id}|{rep}|{seed}"
    return int.from_bytes(hashlib.sha256(identity.encode("utf-8")).digest()[:4], "big")


def validate_records(
    records: list[dict[str, Any]],
    prompts: dict[str, dict[str, Any]],
    summary: dict[str, Any],
) -> None:
    models = set(summary["models"])
    reps = summary["reps"]
    seed = summary["seed"]
    if summary.get("prompts") != len(prompts):
        raise ValueError("router summary prompt count does not match the supplied fixture")
    expected_total_runs = len(prompts) * len(models) * reps
    if "total_runs" in summary:
        total_runs = summary["total_runs"]
        if not isinstance(total_runs, int) or isinstance(total_runs, bool):
            raise ValueError("router summary total_runs must be an integer")
        if total_runs != expected_total_runs:
            raise ValueError(
                "router summary total_runs does not match the expected plan cardinality: "
                f"{total_runs} != {expected_total_runs}"
            )
    expected_identities = {
        (prompt_id, model_id, rep, expected_shuffle_seed(prompt_id, model_id, rep, seed))
        for prompt_id in prompts
        for model_id in models
        for rep in range(reps)
    }
    logical_identities: set[tuple[str, str, int]] = set()
    identities: set[tuple[str, str, int, int]] = set()
    validated_records: list[tuple[dict[str, Any], str, tuple[str, str, int]]] = []
    for index, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            raise ValueError(f"router result {index} must be an object")
        status = validate_status(record)
        prompt_id = record.get("prompt_id")
        model_id = record.get("model_id")
        rep = record.get("rep")
        shuffle_seed = record.get("shuffle_seed")
        if not isinstance(prompt_id, str) or prompt_id not in prompts:
            raise ValueError(f"router result {index} has foreign prompt_id {prompt_id!r}")
        if not isinstance(model_id, str) or not model_id or model_id not in models:
            raise ValueError(f"router result {index} has foreign model_id {model_id!r}")
        if not isinstance(rep, int) or isinstance(rep, bool) or rep < 0 or rep >= reps:
            raise ValueError(f"router result {index} has invalid replication {rep!r}")
        logical_identity = (prompt_id, model_id, rep)
        if logical_identity in logical_identities:
            raise ValueError(f"duplicate router result identity: {logical_identity!r}")
        logical_identities.add(logical_identity)
        expected_seed = expected_shuffle_seed(prompt_id, model_id, rep, seed)
        if shuffle_seed != expected_seed:
            raise ValueError(
                f"router result {logical_identity!r} has shuffle seed {shuffle_seed!r}; "
                f"expected {expected_seed}"
            )
        identities.add((*logical_identity, shuffle_seed))
        validated_records.append((record, status, logical_identity))

    if len(records) != expected_total_runs:
        raise ValueError(
            "router result population does not match the complete expected plan: "
            f"record count {len(records)} != {expected_total_runs}"
        )
    if identities != expected_identities:
        missing = sorted(expected_identities - identities)
        extra = sorted(identities - expected_identities)
        raise ValueError(
            "router result population does not match the complete expected plan: "
            f"missing={missing[:5]!r}, extra={extra[:5]!r}"
        )

    score_fields = {"predicted_primary", "predicted_top3", "top1_correct", "top3_correct"}
    for record, status, identity in validated_records:
        present_score_fields = score_fields.intersection(record)
        if status != "finished":
            if present_score_fields:
                raise ValueError(
                    f"non-finished router result {identity!r} contains score fields: "
                    f"{sorted(present_score_fields)}"
                )
            continue

        predicted_primary = record.get("predicted_primary")
        predicted_top3 = record.get("predicted_top3")
        if not isinstance(predicted_primary, str) or not predicted_primary:
            raise ValueError(f"finished router result {identity!r} requires predicted_primary")
        if (
            not isinstance(predicted_top3, list)
            or not 1 <= len(predicted_top3) <= 3
            or any(not isinstance(skill, str) or not skill for skill in predicted_top3)
            or len(set(predicted_top3)) != len(predicted_top3)
            or predicted_top3[0] != predicted_primary
        ):
            raise ValueError(f"finished router result {identity!r} has invalid predicted_top3")
        expected_skill = prompts[identity[0]]["expected_primary_skill"]
        recomputed_top1 = predicted_primary == expected_skill
        recomputed_top3 = expected_skill in predicted_top3
        if record.get("top1_correct") is not recomputed_top1:
            raise ValueError(f"finished router result {identity!r} has forged top1_correct")
        if record.get("top3_correct") is not recomputed_top3:
            raise ValueError(f"finished router result {identity!r} has forged top3_correct")


def validate_comparable_summaries(
    candidate: dict[str, Any], baseline: dict[str, Any]
) -> None:
    for field in ("seed", "reps"):
        if candidate[field] != baseline[field]:
            raise ValueError(
                f"router baseline {field} is not comparable: "
                f"{baseline[field]!r} != {candidate[field]!r}"
            )
    if sorted(candidate["models"]) != sorted(baseline["models"]):
        raise ValueError(
            "router baseline models are not comparable: "
            f"{sorted(baseline['models'])!r} != {sorted(candidate['models'])!r}"
        )


def validate_comparable_record_sets(
    candidate: list[dict[str, Any]], baseline: list[dict[str, Any]]
) -> None:
    def identities(records: list[dict[str, Any]]) -> set[tuple[str, str, int]]:
        return {
            (record["prompt_id"], record["model_id"], record["rep"])
            for record in records
        }

    candidate_ids = identities(candidate)
    baseline_ids = identities(baseline)
    if candidate_ids != baseline_ids:
        missing = sorted(candidate_ids - baseline_ids)
        extra = sorted(baseline_ids - candidate_ids)
        raise ValueError(
            "router baseline record population is not comparable: "
            f"missing={missing[:5]!r}, extra={extra[:5]!r}"
        )
    candidate_usable = {
        (record["prompt_id"], record["model_id"], record["rep"])
        for record in candidate
        if is_usable_finished(record)
    }
    baseline_usable = {
        (record["prompt_id"], record["model_id"], record["rep"])
        for record in baseline
        if is_usable_finished(record)
    }
    if candidate_usable != baseline_usable:
        raise ValueError("router baseline usable population is not comparable")


def bootstrap_ci(values: list[int], iterations: int = 2000, seed: int = 0) -> tuple[float, float, float]:
    if not values:
        return (0.0, 0.0, 0.0)
    rng = random.Random(seed)
    n = len(values)
    samples: list[float] = []
    for _ in range(iterations):
        draw = [values[rng.randrange(n)] for _ in range(n)]
        samples.append(sum(draw) / n)
    samples.sort()
    point = sum(values) / n
    lower = samples[int(iterations * 0.025)]
    upper = samples[int(iterations * 0.975)]
    return (point, lower, upper)


def stable_seed(label: str) -> int:
    """Derive a process-independent 32-bit seed from an exact label."""

    return int.from_bytes(hashlib.sha256(label.encode("utf-8")).digest()[:4], "big")


def validate_status(record: dict[str, Any]) -> str:
    status = record.get("status")
    if status not in KNOWN_STATUSES:
        identity = "/".join(
            str(record.get(field, "unknown")) for field in ("model_id", "prompt_id", "rep")
        )
        raise ValueError(f"unknown router result status {status!r} for {identity}")
    return status


def is_usable_finished(record: dict[str, Any]) -> bool:
    """Return whether a finished record has both required boolean scores."""

    return (
        validate_status(record) == "finished"
        and isinstance(record.get("top1_correct"), bool)
        and isinstance(record.get("top3_correct"), bool)
    )


def summarize_per_model(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_model: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        validate_status(record)
        by_model[record["model_id"]].append(record)

    summary: dict[str, dict[str, Any]] = {}
    for model_id, model_records in by_model.items():
        usable = [r for r in model_records if is_usable_finished(r)]
        top1 = [int(r["top1_correct"]) for r in usable]
        top3 = [int(r["top3_correct"]) for r in usable]
        format_failures = sum(1 for r in model_records if r.get("status") == "format_failure")
        sdk_errors = sum(1 for r in model_records if r.get("status") == "error")
        cancelled = sum(1 for r in model_records if r.get("status") == "cancelled")
        unavailable = sum(1 for r in model_records if r.get("status") == "model_unavailable")
        dry_runs = sum(1 for r in model_records if r.get("status") == "dry_run")
        invalid_finished = sum(
            1
            for r in model_records
            if r.get("status") == "finished" and not is_usable_finished(r)
        )
        durations = [
            r.get("duration_ms", 0)
            for r in model_records
            if isinstance(r.get("duration_ms"), int)
        ]
        total_records = len(model_records)
        usable_records = len(usable)

        top1_point, top1_lower, top1_upper = bootstrap_ci(
            top1, seed=stable_seed(f"{model_id}:top1")
        )
        top3_point, top3_lower, top3_upper = bootstrap_ci(
            top3, seed=stable_seed(f"{model_id}:top3")
        )

        summary[model_id] = {
            "total_records": total_records,
            "usable_records": usable_records,
            "format_failures": format_failures,
            "sdk_errors": sdk_errors,
            "cancelled": cancelled,
            "model_unavailable": unavailable,
            "dry_runs": dry_runs,
            "invalid_finished_records": invalid_finished,
            "sdk_finished_rate": round(
                (usable_records + invalid_finished + format_failures) / total_records, 4
            ),
            "usable_rate": round(usable_records / total_records, 4),
            "top1_accuracy": round(top1_point, 4) if top1 else None,
            "top1_ci": [round(top1_lower, 4), round(top1_upper, 4)] if top1 else None,
            "top3_accuracy": round(top3_point, 4) if top3 else None,
            "top3_ci": [round(top3_lower, 4), round(top3_upper, 4)] if top3 else None,
            "median_duration_ms": int(statistics.median(durations)) if durations else None,
            "p95_duration_ms": int(sorted(durations)[int(0.95 * len(durations)) - 1]) if len(durations) >= 20 else None,
        }
    return summary


def build_confusion(records: list[dict[str, Any]], prompts: dict[str, dict[str, Any]]) -> dict[str, dict[str, int]]:
    matrix: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in records:
        if not is_usable_finished(r):
            continue
        expected = prompts.get(r["prompt_id"], {}).get("expected_primary_skill")
        predicted = r.get("predicted_primary")
        if not expected or not predicted:
            continue
        matrix[expected][predicted] += 1
    return {expected: dict(row) for expected, row in matrix.items()}


def per_prompt_breakdown(records: list[dict[str, Any]], prompts: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    by_prompt: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in records:
        by_prompt[r["prompt_id"]].append(r)

    rows: list[dict[str, Any]] = []
    for prompt_id, prompt_records in sorted(by_prompt.items()):
        meta = prompts.get(prompt_id, {})
        expected = meta.get("expected_primary_skill")
        usable = [r for r in prompt_records if is_usable_finished(r)]
        total = len(prompt_records)
        top1 = sum(1 for r in usable if r["top1_correct"])
        top3 = sum(1 for r in usable if r["top3_correct"])
        unique_predictions = sorted(
            {r.get("predicted_primary") for r in usable if r.get("predicted_primary")}
        )
        rows.append(
            {
                "prompt_id": prompt_id,
                "expected": expected,
                "runs": total,
                "usable_records": len(usable),
                "usable_rate": round(len(usable) / total, 3) if total else 0.0,
                "top1_rate": round(top1 / len(usable), 3) if usable else None,
                "top3_rate": round(top3 / len(usable), 3) if usable else None,
                "unique_predicted_primary": unique_predictions,
            }
        )
    return rows


def hardest_prompts(per_prompt: list[dict[str, Any]], n: int = 10) -> list[dict[str, Any]]:
    usable_rows = [row for row in per_prompt if isinstance(row.get("top1_rate"), (int, float))]
    return sorted(usable_rows, key=lambda row: row["top1_rate"])[:n]


def format_rate(value: Any, digits: int = 3) -> str:
    return f"{value:.{digits}f}" if isinstance(value, (int, float)) else "-"


def format_ci(value: Any) -> str:
    if not isinstance(value, list) or len(value) != 2:
        return "-"
    if not all(isinstance(item, (int, float)) for item in value):
        return "-"
    return f"[{value[0]:.3f}, {value[1]:.3f}]"


def render(summary: dict[str, dict[str, Any]], confusion: dict[str, dict[str, int]], per_prompt: list[dict[str, Any]], meta: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Router Benchmark Results")
    lines.append("")
    lines.append(f"_run timestamp: {meta.get('timestamp')}_")
    lines.append(f"_repo commit: `{meta.get('repo_sha', 'unknown')}`_")
    lines.append(f"_fixture sha256-16: `{meta.get('fixture_sha', 'unknown')}`_")
    lines.append(f"_seed: {meta.get('seed')}_")
    lines.append(f"_runs: {meta.get('total_runs')}_  ")
    lines.append(f"_models: {', '.join(meta.get('models', []))}_  ")
    lines.append(f"_reps per (prompt, model): {meta.get('reps')}_")
    lines.append("")
    lines.append("## Methodology")
    lines.append("")
    lines.append(
        "Each prompt is presented to each model with the benchmark's skill activation descriptions in a "
        "deterministically-shuffled order (different shuffle per replication). The model must return "
        "JSON with a ranked list of skill names. Top-1 accuracy is whether the first ranked skill "
        "matches the human-labeled `expected_primary_skill`; top-3 is whether the expected skill appears "
        "in the first three positions."
    )
    lines.append("")
    lines.append(
        "No skills are loaded into the agent (`settingSources: []`); the only routing signal is the "
        "in-prompt descriptions. Accuracy and confidence intervals use only `finished` records with "
        "both boolean score fields. SDK errors, cancellations, dry runs, legacy model-unavailable "
        "records, and malformed finished records are reported as outcomes but never scored as "
        "incorrect. Confidence intervals are 95% bootstrap with 2000 resamples."
    )
    lines.append("")
    lines.append("## Per-model leaderboard")
    lines.append("")
    lines.append(
        "| Model | Top-1 | 95% CI | Top-3 | 95% CI | Usable / Total | SDK Finished | "
        "Usable Rate | Format Failures | SDK Errors | Cancelled | Unavailable | Dry Runs | "
        "Invalid Finished | Median ms |"
    )
    lines.append(
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | "
        "--- | --- |"
    )
    for model_id, stats in sorted(summary.items(), key=lambda item: -(item[1].get("top1_accuracy") or 0)):
        top1 = stats.get("top1_accuracy")
        top1_ci = stats.get("top1_ci")
        top3 = stats.get("top3_accuracy")
        top3_ci = stats.get("top3_ci")
        median = stats.get("median_duration_ms")
        lines.append(
            f"| `{model_id}` | "
            f"{format_rate(top1)} | "
            f"{format_ci(top1_ci)} | "
            f"{format_rate(top3)} | "
            f"{format_ci(top3_ci)} | "
            f"{stats.get('usable_records')} / {stats.get('total_records')} | "
            f"{format_rate(stats.get('sdk_finished_rate'))} | "
            f"{format_rate(stats.get('usable_rate'))} | "
            f"{stats.get('format_failures')} | "
            f"{stats.get('sdk_errors')} | "
            f"{stats.get('cancelled')} | "
            f"{stats.get('model_unavailable')} | "
            f"{stats.get('dry_runs')} | "
            f"{stats.get('invalid_finished_records')} | "
            f"{median if median else '-'} |"
        )

    lines.append("")
    lines.append("## Per-skill confusion (when expected is X, predicted is Y)")
    lines.append("")
    lines.append(
        "Rows are the ground-truth `expected_primary_skill`; columns are what models actually "
        "predicted. Only usable `finished` records are counted."
    )
    lines.append("")
    all_predicted: set[str] = set()
    for row in confusion.values():
        all_predicted.update(row.keys())
    sorted_predicted = sorted(all_predicted)
    header = "| Expected \\ Predicted |" + "".join(f" `{p}` |" for p in sorted_predicted)
    sep = "| --- |" + "".join(" --- |" for _ in sorted_predicted)
    lines.append(header)
    lines.append(sep)
    for expected in sorted(confusion.keys()):
        row_total = sum(confusion[expected].values())
        cells = []
        for predicted in sorted_predicted:
            count = confusion[expected].get(predicted, 0)
            if count == 0:
                cells.append(" - |")
            elif predicted == expected:
                cells.append(f" **{count}** |")
            else:
                cells.append(f" {count} |")
        lines.append(f"| `{expected}` (n={row_total}) |" + "".join(cells))

    hardest = hardest_prompts(per_prompt, n=10)
    lines.append("")
    lines.append("## Hardest prompts (lowest top-1 across all models)")
    lines.append("")
    lines.append("| Prompt | Expected | Usable / Total | Top-1 Rate | Predicted Primaries |")
    lines.append("| --- | --- | --- | --- | --- |")
    for row in hardest:
        predicted = ", ".join(f"`{p}`" for p in row["unique_predicted_primary"][:5])
        lines.append(
            f"| {row['prompt_id']} | `{row['expected']}` | "
            f"{row['usable_records']} / {row['runs']} | {row['top1_rate']:.2f} | {predicted} |"
        )

    lines.append("")
    lines.append("## Reproducibility")
    lines.append("")
    lines.append("Rebuild this report from the preserved records with:")
    lines.append("")
    lines.append("```bash")
    lines.append("python3 researcher/scripts/render_router_report.py \\")
    lines.append("    --results researcher/benchmarks/router/results/<run> \\")
    lines.append("    --fixture researcher/benchmarks/router/prompts.jsonl \\")
    lines.append("    --output researcher/benchmarks/router/results-published/<date>.md")
    lines.append("```")
    lines.append("")
    lines.append(
        "Per-run JSON artifacts (prompt, model, replication, raw model output, parsed ranking) are "
        "preserved under the gitignored `results/` directory next to the summary that drives this report."
    )
    lines.append(
        "The current SDK package is deliberately zero-call. Re-executing the experiment requires the "
        "recorded source revision's runner or a later human-merged manifest-bound activation; this "
        "report generator does not imply that the current branch can make paid calls."
    )
    return "\n".join(lines) + "\n"


def delta_section(
    new_summary: dict[str, dict[str, Any]],
    new_confusion: dict[str, dict[str, int]],
    new_per_prompt: list[dict[str, Any]],
    baseline_summary: dict[str, dict[str, Any]],
    baseline_confusion: dict[str, dict[str, int]],
    baseline_per_prompt: list[dict[str, Any]],
    baseline_label: str,
) -> list[str]:
    lines: list[str] = []
    lines.append("## Delta vs baseline")
    lines.append("")
    lines.append(f"_baseline: {baseline_label}_")
    lines.append("")
    lines.append("### Per-model accuracy change")
    lines.append("")
    lines.append("| Model | Baseline Top-1 | New Top-1 | Delta | Baseline Top-3 | New Top-3 | Delta |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    models = sorted(set(new_summary) | set(baseline_summary))
    for model in models:
        bt1 = baseline_summary.get(model, {}).get("top1_accuracy")
        nt1 = new_summary.get(model, {}).get("top1_accuracy")
        bt3 = baseline_summary.get(model, {}).get("top3_accuracy")
        nt3 = new_summary.get(model, {}).get("top3_accuracy")
        d1 = (nt1 - bt1) if isinstance(bt1, (int, float)) and isinstance(nt1, (int, float)) else None
        d3 = (nt3 - bt3) if isinstance(bt3, (int, float)) and isinstance(nt3, (int, float)) else None
        bt1_s = f"{bt1:.3f}" if isinstance(bt1, (int, float)) else "-"
        nt1_s = f"{nt1:.3f}" if isinstance(nt1, (int, float)) else "-"
        bt3_s = f"{bt3:.3f}" if isinstance(bt3, (int, float)) else "-"
        nt3_s = f"{nt3:.3f}" if isinstance(nt3, (int, float)) else "-"
        d1_s = f"{'+' if d1 and d1 > 0 else ''}{d1:.3f}" if d1 is not None else "-"
        d3_s = f"{'+' if d3 and d3 > 0 else ''}{d3:.3f}" if d3 is not None else "-"
        lines.append(f"| `{model}` | {bt1_s} | {nt1_s} | {d1_s} | {bt3_s} | {nt3_s} | {d3_s} |")
    lines.append("")
    lines.append("### Per-skill top-1 rate change")
    lines.append("")
    lines.append("Counts a row as correct when the predicted primary equals the expected primary.")
    lines.append("")
    lines.append("| Skill (expected) | Baseline | New | Delta |")
    lines.append("| --- | --- | --- | --- |")
    all_skills = sorted(set(baseline_confusion) | set(new_confusion))
    for skill in all_skills:
        b_row = baseline_confusion.get(skill, {})
        n_row = new_confusion.get(skill, {})
        b_total = sum(b_row.values())
        n_total = sum(n_row.values())
        b_correct = b_row.get(skill, 0)
        n_correct = n_row.get(skill, 0)
        b_rate = b_correct / b_total if b_total else 0.0
        n_rate = n_correct / n_total if n_total else 0.0
        delta = n_rate - b_rate
        delta_s = f"{'+' if delta > 0 else ''}{delta:.3f}"
        marker = " <- improved" if delta >= 0.05 else (" <- regressed" if delta <= -0.05 else "")
        lines.append(
            f"| `{skill}` | {b_correct}/{b_total} = {b_rate:.3f} | {n_correct}/{n_total} = {n_rate:.3f} | {delta_s}{marker} |"
        )
    lines.append("")
    lines.append("### Previously-hardest prompts")
    lines.append("")
    baseline_hardest_ids = {
        row["prompt_id"] for row in hardest_prompts(baseline_per_prompt, n=10)
    }
    lines.append("| Prompt | Expected | Baseline Top-1 Rate | New Top-1 Rate | Delta |")
    lines.append("| --- | --- | --- | --- | --- |")
    new_by_id = {row["prompt_id"]: row for row in new_per_prompt}
    baseline_by_id = {row["prompt_id"]: row for row in baseline_per_prompt}
    for prompt_id in sorted(baseline_hardest_ids):
        baseline = baseline_by_id.get(prompt_id, {})
        new = new_by_id.get(prompt_id, {})
        b_rate = baseline.get("top1_rate")
        n_rate = new.get("top1_rate")
        if isinstance(b_rate, (int, float)) and isinstance(n_rate, (int, float)):
            delta = n_rate - b_rate
            delta_s = f"{'+' if delta > 0 else ''}{delta:.3f}"
        else:
            delta_s = "-"
        expected = baseline.get("expected") or new.get("expected") or "-"
        lines.append(
            f"| {prompt_id} | `{expected}` | {format_rate(b_rate, 2)} | "
            f"{format_rate(n_rate, 2)} | {delta_s} |"
        )
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description="Render router benchmark report")
    parser.add_argument("--results", type=Path, required=True, help="Directory of per-run JSON files")
    parser.add_argument("--fixture", type=Path, required=True, help="Router prompts JSONL")
    parser.add_argument("--output", type=Path, required=True, help="Destination Markdown file")
    parser.add_argument("--baseline", type=Path, help="Optional baseline results directory to compute deltas against")
    parser.add_argument("--baseline-label", type=str, help="Human label for the baseline (e.g. '2026-05-15 v2.2.0 descriptions')")
    args = parser.parse_args()

    if not args.results.exists():
        print(f"results dir missing: {args.results}", file=sys.stderr)
        return 1

    records = load_run_records(args.results)
    if not records:
        print("no per-run records found", file=sys.stderr)
        return 1
    prompts_list = load_jsonl(args.fixture)
    prompts = build_prompt_index(prompts_list)

    summary_path = args.results / "summary.json"
    computed_fixture_digest = fixture_digest(args.fixture)
    summary_meta = load_summary_metadata(summary_path, computed_fixture_digest)
    validate_records(records, prompts, summary_meta)

    meta = {
        "timestamp": summary_meta.get("timestamp") or "unknown",
        "repo_sha": summary_meta.get("repo_sha") or "unknown",
        "fixture_sha": computed_fixture_digest,
        "seed": summary_meta["seed"],
        "total_runs": len(records),
        "models": sorted({r["model_id"] for r in records}),
        "reps": summary_meta["reps"],
    }

    summary = summarize_per_model(records)
    confusion = build_confusion(records, prompts)
    per_prompt = per_prompt_breakdown(records, prompts)

    rendered = render(summary, confusion, per_prompt, meta)

    if args.baseline:
        if not args.baseline.exists():
            raise ValueError(f"baseline results directory is missing: {args.baseline}")
        baseline_records = load_run_records(args.baseline)
        baseline_summary_path = args.baseline / "summary.json"
        baseline_meta = load_summary_metadata(baseline_summary_path, computed_fixture_digest)
        validate_records(baseline_records, prompts, baseline_meta)
        validate_comparable_summaries(summary_meta, baseline_meta)
        validate_comparable_record_sets(records, baseline_records)
        baseline_summary = summarize_per_model(baseline_records)
        baseline_confusion = build_confusion(baseline_records, prompts)
        baseline_per_prompt = per_prompt_breakdown(baseline_records, prompts)
        delta = delta_section(
            summary,
            confusion,
            per_prompt,
            baseline_summary,
            baseline_confusion,
            baseline_per_prompt,
            args.baseline_label or str(args.baseline),
        )
        rendered = rendered.rstrip("\n") + "\n\n" + "\n".join(delta) + "\n"

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(f"wrote {args.output}")
    print(json.dumps({"models": meta["models"], "total_runs": meta["total_runs"], "per_model_top1": {k: v.get("top1_accuracy") for k, v in summary.items()}}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
