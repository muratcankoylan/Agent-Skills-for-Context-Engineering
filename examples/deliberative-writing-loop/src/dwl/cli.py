"""Command-line interface.

    dwl compile-persona --name orwell --corpus personas/orwell/corpus --provider anthropic
    dwl write --persona personas/orwell/persona.json --brief eval/briefs/b01.json \
        --provider anthropic --max-usd 2.0
    dwl benchmark --personas personas --briefs eval/briefs --results eval/results \
        --providers anthropic,openai --conditions oneshot,selfrefine,dwl --max-usd 25 --dry-run

Budget gates are required thinking, so they have explicit defaults and are
printed before any call is made. --dry-run prints the plan and worst-case cost
forecast without a single API call.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .adapters import Budget, make_adapter
from .adapters.pangram import PangramClient
from .benchmark import BenchItem, judge_symmetric, run_item
from .harness import RunConfig, WritingRun
from .persona import Persona, compile_persona

# Worst-case calls per condition for a ~900-word piece (8 paragraphs).
_CALL_FORECAST = {"oneshot": 1, "selfrefine": 3, "dwl": 1 + 8 * (1 + 3 + 3 + 1)}


def _cmd_compile_persona(args: argparse.Namespace) -> int:
    budget = Budget(max_calls=args.max_calls, max_usd=args.max_usd)
    adapter = None if args.provider == "none" else make_adapter(args.provider, args.model, budget)
    persona = compile_persona(args.name, Path(args.corpus), adapter)
    out = Path(args.out or Path(args.corpus).parent / "persona.json")
    persona.save(out)
    print(f"persona written: {out}")
    print(f"  corpus hash: {persona.corpus_hash}, words: {persona.style.word_count}")
    print(f"  tacit layer: {'yes' if persona.tacit else 'NO (deterministic layers only)'}")
    if adapter is not None:
        print(f"  budget: {budget.summary()}")
    return 0


def _cmd_write(args: argparse.Namespace) -> int:
    persona = Persona.load(Path(args.persona))
    brief_path = Path(args.brief)
    if brief_path.suffix == ".json":
        brief_data = json.loads(brief_path.read_text(encoding="utf-8"))
        brief = brief_data["brief"]
        target_words = int(brief_data.get("target_words", args.target_words))
    else:
        brief = brief_path.read_text(encoding="utf-8")
        target_words = args.target_words
    budget = Budget(max_calls=args.max_calls, max_usd=args.max_usd)
    print(f"budget: max {budget.max_calls} calls, ${budget.max_usd:.2f}")
    if args.dry_run:
        print(f"dry run: would write ~{target_words} words as {persona.name} via {args.provider}")
        print(f"worst-case calls: {_CALL_FORECAST['dwl']}")
        return 0
    adapter = make_adapter(args.provider, args.model, budget)
    run = WritingRun(
        adapter, persona, brief,
        RunConfig(target_words=target_words, runs_dir=Path(args.runs_dir)),
    )
    final = run.run()
    print(f"run {run.run_id} complete: {run.run_dir}/final.md")
    print(f"spent: {budget.summary()}")
    print("\n" + final)
    return 0


def _cmd_benchmark(args: argparse.Namespace) -> int:
    providers = [p.strip() for p in args.providers.split(",") if p.strip()]
    conditions = [c.strip() for c in args.conditions.split(",") if c.strip()]
    persona_files = sorted(Path(args.personas).glob("*/persona.json"))
    brief_files = sorted(Path(args.briefs).glob("*.json"))
    if not persona_files:
        print(f"no persona.json files under {args.personas}; run compile-persona first", file=sys.stderr)
        return 1
    if not brief_files:
        print(f"no brief JSON files under {args.briefs}", file=sys.stderr)
        return 1

    items: list[BenchItem] = []
    for brief_file in brief_files:
        data = json.loads(brief_file.read_text(encoding="utf-8"))
        for persona_file in persona_files:
            for condition in conditions:
                for provider in providers:
                    items.append(
                        BenchItem(
                            brief_id=brief_file.stem,
                            brief=data["brief"],
                            persona_name=persona_file.parent.name,
                            condition=condition,
                            provider=provider,
                        )
                    )
    worst_calls = sum(_CALL_FORECAST.get(i.condition, 5) for i in items)
    print(f"plan: {len(items)} cells, worst-case ~{worst_calls} LLM calls")
    print(f"budget cap: ${args.max_usd:.2f} total, {args.max_calls} calls per cell")
    if args.dry_run:
        for item in items:
            print(f"  {item.brief_id} / {item.persona_name} / {item.condition} / {item.provider}")
        return 0

    results_dir = Path(args.results)
    shared_budget = Budget(max_calls=args.max_calls * len(items), max_usd=args.max_usd)
    pangram = PangramClient()
    if not pangram.available:
        print("note: PANGRAM_API_KEY not set; detector column will be skipped")
    for completed, item in enumerate(items, start=1):
        adapter = make_adapter(item.provider, None, shared_budget)
        persona = Persona.load(Path(args.personas) / item.persona_name / "persona.json")
        result = run_item(item, adapter, persona, results_dir, args.target_words, pangram)
        print(
            f"[{completed}/{len(items)}] {item.brief_id}/{item.persona_name}/"
            f"{item.condition}/{item.provider}: style_distance="
            f"{result['metrics']['style_distance']} slop/kw={result['metrics']['slop_score_per_kw']} "
            f"(spent ${shared_budget.spent_usd:.2f})"
        )
    print(f"done. results in {results_dir}. total spent: ${shared_budget.spent_usd:.2f}")
    return 0


def _cmd_judge(args: argparse.Namespace) -> int:
    """Pairwise judging over existing result files: dwl vs each baseline,
    judged by every provider, both orders, stable verdicts only."""
    results_dir = Path(args.results)
    files = sorted(results_dir.glob("*.json"))
    by_key: dict[tuple, dict] = {}
    for file in files:
        data = json.loads(file.read_text(encoding="utf-8"))
        item = data.get("item", {})
        key = (item.get("brief_id"), item.get("persona_name"), item.get("provider"))
        by_key.setdefault(key, {})[item.get("condition")] = data
    judges = [j.strip() for j in args.judges.split(",") if j.strip()]
    budget = Budget(max_calls=args.max_calls, max_usd=args.max_usd)
    out_rows = []
    for (brief_id, persona_name, provider), conditions in sorted(by_key.items()):
        if "dwl" not in conditions:
            continue
        persona = Persona.load(Path(args.personas) / persona_name / "persona.json")
        for baseline in ("oneshot", "selfrefine"):
            if baseline not in conditions:
                continue
            for judge_provider in judges:
                judge = make_adapter(judge_provider, None, budget)
                verdicts = judge_symmetric(
                    judge,
                    conditions["dwl"]["item"]["brief"],
                    persona,
                    conditions["dwl"]["text"],
                    conditions[baseline]["text"],
                )
                out_rows.append(
                    {
                        "brief_id": brief_id,
                        "persona": persona_name,
                        "generator_provider": provider,
                        "baseline": baseline,
                        "judge": judge_provider,
                        "self_judged": judge_provider == provider,
                        # A = dwl, B = baseline in the stable verdicts
                        "stable": verdicts["stable"],
                    }
                )
                print(
                    f"{brief_id}/{persona_name}/{provider} dwl-vs-{baseline} "
                    f"judge={judge_provider}: {verdicts['stable']}"
                )
    out_path = results_dir / "judgments.json"
    out_path.write_text(json.dumps(out_rows, indent=2), encoding="utf-8")
    print(f"judgments written: {out_path} (spent ${budget.spent_usd:.2f})")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="dwl", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("compile-persona", help="compile a writer corpus into a persona artifact")
    p.add_argument("--name", required=True)
    p.add_argument("--corpus", required=True)
    p.add_argument("--out")
    p.add_argument("--provider", default="anthropic", help="anthropic|openai|mock|none (none = deterministic layers only)")
    p.add_argument("--model")
    p.add_argument("--max-calls", type=int, default=3)
    p.add_argument("--max-usd", type=float, default=1.0)
    p.set_defaults(func=_cmd_compile_persona)

    p = sub.add_parser("write", help="run the deliberative loop for one brief")
    p.add_argument("--persona", required=True)
    p.add_argument("--brief", required=True)
    p.add_argument("--provider", default="anthropic")
    p.add_argument("--model")
    p.add_argument("--target-words", type=int, default=900)
    p.add_argument("--runs-dir", default="runs")
    p.add_argument("--max-calls", type=int, default=80)
    p.add_argument("--max-usd", type=float, default=3.0)
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=_cmd_write)

    p = sub.add_parser("benchmark", help="run the three-condition benchmark grid")
    p.add_argument("--personas", default="personas")
    p.add_argument("--briefs", default="eval/briefs")
    p.add_argument("--results", default="eval/results")
    p.add_argument("--providers", default="anthropic,openai")
    p.add_argument("--conditions", default="oneshot,selfrefine,dwl")
    p.add_argument("--target-words", type=int, default=900)
    p.add_argument("--max-calls", type=int, default=80, help="per-cell call cap")
    p.add_argument("--max-usd", type=float, default=25.0, help="total dollar cap")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=_cmd_benchmark)

    p = sub.add_parser("judge", help="cross-judge existing benchmark results")
    p.add_argument("--results", default="eval/results")
    p.add_argument("--personas", default="personas")
    p.add_argument("--judges", default="anthropic,openai")
    p.add_argument("--max-calls", type=int, default=200)
    p.add_argument("--max-usd", type=float, default=10.0)
    p.set_defaults(func=_cmd_judge)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
