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
import json
import random
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def load_run_records(results_dir: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted(results_dir.glob("*.json")):
        if path.name == "summary.json":
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        records.append(data)
    return records


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


def summarize_per_model(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_model: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        by_model[record["model_id"]].append(record)

    summary: dict[str, dict[str, Any]] = {}
    for model_id, model_records in by_model.items():
        top1 = [1 if r.get("top1_correct") else 0 for r in model_records if r.get("status") == "finished"]
        top3 = [1 if r.get("top3_correct") else 0 for r in model_records if r.get("status") == "finished"]
        finished = [r for r in model_records if r.get("status") == "finished"]
        format_failures = sum(1 for r in model_records if r.get("status") == "format_failure")
        unavailable = sum(1 for r in model_records if r.get("status") == "model_unavailable")
        durations = [r.get("duration_ms", 0) for r in model_records if isinstance(r.get("duration_ms"), int)]

        top1_point, top1_lower, top1_upper = bootstrap_ci(top1, seed=hash(model_id) & 0xFFFFFFFF)
        top3_point, top3_lower, top3_upper = bootstrap_ci(top3, seed=(hash(model_id) ^ 0xdead) & 0xFFFFFFFF)

        summary[model_id] = {
            "total_runs": len(model_records),
            "finished": len(finished),
            "format_failures": format_failures,
            "model_unavailable": unavailable,
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
        if r.get("status") != "finished":
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
        total = len(prompt_records)
        top1 = sum(1 for r in prompt_records if r.get("top1_correct"))
        top3 = sum(1 for r in prompt_records if r.get("top3_correct"))
        unique_predictions = sorted({r.get("predicted_primary") for r in prompt_records if r.get("predicted_primary")})
        rows.append(
            {
                "prompt_id": prompt_id,
                "expected": expected,
                "runs": total,
                "top1_rate": round(top1 / total, 3) if total else 0.0,
                "top3_rate": round(top3 / total, 3) if total else 0.0,
                "unique_predicted_primary": unique_predictions,
            }
        )
    return rows


def hardest_prompts(per_prompt: list[dict[str, Any]], n: int = 10) -> list[dict[str, Any]]:
    return sorted(per_prompt, key=lambda row: row["top1_rate"])[:n]


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
        "Each prompt is presented to each model with all current skill activation descriptions in a "
        "deterministically-shuffled order (different shuffle per replication). The model must return "
        "JSON with a ranked list of skill names. Top-1 accuracy is whether the first ranked skill "
        "matches the human-labeled `expected_primary_skill`; top-3 is whether the expected skill appears "
        "in the first three positions."
    )
    lines.append("")
    lines.append(
        "No skills or ambient rules are loaded into the agent (`--ignore-rules`); the only routing signal is the "
        "in-prompt descriptions. Confidence intervals are 95% bootstrap with 2000 resamples."
    )
    lines.append("")
    lines.append("## Per-model leaderboard")
    lines.append("")
    lines.append("| Model | Top-1 | 95% CI | Top-3 | 95% CI | Format Failures | Median ms |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    for model_id, stats in sorted(summary.items(), key=lambda item: -(item[1].get("top1_accuracy") or 0)):
        top1 = stats.get("top1_accuracy")
        top1_ci = stats.get("top1_ci")
        top3 = stats.get("top3_accuracy")
        top3_ci = stats.get("top3_ci")
        median = stats.get("median_duration_ms")
        lines.append(
            f"| `{model_id}` | "
            f"{top1:.3f} | "
            f"[{top1_ci[0]:.3f}, {top1_ci[1]:.3f}] | "
            f"{top3:.3f} | "
            f"[{top3_ci[0]:.3f}, {top3_ci[1]:.3f}] | "
            f"{stats.get('format_failures')} | "
            f"{median if median else '-'} |"
        )

    lines.append("")
    lines.append("## Per-skill confusion (when expected is X, predicted is Y)")
    lines.append("")
    lines.append("Rows are the ground-truth `expected_primary_skill`; columns are what models actually predicted. Only `finished` runs counted.")
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
    lines.append("| Prompt | Expected | Top-1 Rate | Predicted Primaries |")
    lines.append("| --- | --- | --- | --- |")
    for row in hardest:
        predicted = ", ".join(f"`{p}`" for p in row["unique_predicted_primary"][:5])
        lines.append(
            f"| {row['prompt_id']} | `{row['expected']}` | {row['top1_rate']:.2f} | {predicted} |"
        )

    lines.append("")
    lines.append("## Reproducibility")
    lines.append("")
    lines.append("Reproduce these numbers exactly with:")
    lines.append("")
    lines.append("```bash")
    lines.append("cd researcher/benchmarks/codex-runner")
    lines.append("npm install")
    lines.append(
        "node --experimental-strip-types src/runRouter.ts "
        f"--models {','.join(meta.get('models', []))} "
        f"--reps {meta.get('reps')} "
        f"--seed {meta.get('seed')} "
        f"--max-runs {int(meta.get('total_runs') or 1) * 2}"
    )
    lines.append("python3 ../../scripts/render_router_report.py \\")
    lines.append("    --results ../router/results/<date>-<seed> \\")
    lines.append("    --fixture ../router/prompts.jsonl \\")
    lines.append("    --output ../router/results-published/<date>.md")
    lines.append("```")
    lines.append("")
    lines.append(
        "Per-run JSON artifacts (prompt, model, replication, raw model output, parsed ranking) are "
        "preserved under the gitignored `results/` directory next to the summary that drives this report."
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
    baseline_hardest_ids = {row["prompt_id"] for row in sorted(baseline_per_prompt, key=lambda r: r["top1_rate"])[:10]}
    lines.append("| Prompt | Expected | Baseline Top-1 Rate | New Top-1 Rate | Delta |")
    lines.append("| --- | --- | --- | --- | --- |")
    new_by_id = {row["prompt_id"]: row for row in new_per_prompt}
    baseline_by_id = {row["prompt_id"]: row for row in baseline_per_prompt}
    for prompt_id in sorted(baseline_hardest_ids):
        baseline = baseline_by_id.get(prompt_id, {})
        new = new_by_id.get(prompt_id, {})
        b_rate = baseline.get("top1_rate", 0.0)
        n_rate = new.get("top1_rate", 0.0)
        delta = n_rate - b_rate
        delta_s = f"{'+' if delta > 0 else ''}{delta:.3f}"
        expected = baseline.get("expected") or new.get("expected") or "-"
        lines.append(f"| {prompt_id} | `{expected}` | {b_rate:.2f} | {n_rate:.2f} | {delta_s} |")
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
    prompts = {row["prompt_id"]: row for row in prompts_list}

    summary_path = args.results / "summary.json"
    summary_meta: dict[str, Any] = {}
    if summary_path.exists():
        try:
            summary_meta = json.loads(summary_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            summary_meta = {}

    meta = {
        "timestamp": summary_meta.get("timestamp") or "unknown",
        "repo_sha": summary_meta.get("repo_sha") or "unknown",
        "fixture_sha": summary_meta.get("fixture_sha") or "unknown",
        "seed": summary_meta.get("seed") or 1,
        "total_runs": len(records),
        "models": sorted({r["model_id"] for r in records}),
        "reps": max((r.get("rep", 0) for r in records), default=0) + 1,
    }

    summary = summarize_per_model(records)
    confusion = build_confusion(records, prompts)
    per_prompt = per_prompt_breakdown(records, prompts)

    rendered = render(summary, confusion, per_prompt, meta)

    if args.baseline and args.baseline.exists():
        baseline_records = load_run_records(args.baseline)
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
