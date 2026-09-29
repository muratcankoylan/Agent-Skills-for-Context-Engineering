"""Command-line interface.

    dwl compile-persona --name orwell --corpus personas/orwell/corpus --provider anthropic
    dwl write --persona personas/orwell/persona.json --brief eval/briefs/b01.json \
        --provider anthropic --max-usd 2.0
    dwl benchmark --personas personas --briefs eval/briefs --results eval/results \
        --providers anthropic,openai --conditions oneshot,selfrefine,dwl --max-usd 25 --dry-run

Paid execution is disabled. Offline budgets have explicit defaults. --dry-run
prints a proposed plan and illustrative call forecast without an API call;
it is not a proof of token usage, plan length, or billing bounds.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .adapters import Budget, make_adapter
from .adapters.base import LiveExecutionDisabled
from .benchmark import BenchItem, judge_symmetric, run_item
from .env import find_env_file, key_status, load_env
from .harness import RunConfig, WritingRun
from .persona import Persona, compile_persona
from .state import atomic_json, completed_result, digest, input_identity, run_once

# Illustrative calls per condition, assuming eight paragraphs, not a hard bound.
_CALL_FORECAST = {"oneshot": 1, "selfrefine": 3, "dwl": 1 + 8 * (1 + 3 + 3 + 1)}


def _offline_only(providers, *, detector="none"):
    if any(provider not in {"none", "mock"} for provider in providers) or detector != "none":
        raise LiveExecutionDisabled("paid example execution disabled pending admitted SDK/broker")


def _cmd_check_env(args: argparse.Namespace) -> int:
    """Report which keys are visible, masked. Makes no API calls."""
    env_path = Path(args.env_file) if args.env_file else find_env_file()
    print(f".env file: {env_path if env_path else 'not found (using real environment only)'}")
    status = key_status()
    for name, masked in status.items():
        required = "unused: live example execution is disabled"
        state = "set" if masked != "<unset>" else "MISSING"
        print(f"  {name}: {state} {masked} ({required})")
    for name in ("DWL_ANTHROPIC_MODEL", "DWL_OPENAI_MODEL"):
        pinned = os.environ.get(name)
        print(f"  {name}: {pinned if pinned else 'unpinned (adapter default)'}")
    missing = [n for n in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY") if status[n] == "<unset>"]
    if missing:
        print(
            "\nNo keys are needed for this draft's offline tests and forecasts. "
            "Providing keys does not enable paid execution."
        )
    return 0


def _cmd_compile_persona(args: argparse.Namespace) -> int:
    _offline_only([args.provider])
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
        print(f"illustrative calls (eight paragraphs): {_CALL_FORECAST['dwl']}")
        return 0
    _offline_only([args.provider])
    budget = Budget(max_calls=args.max_calls, max_usd=args.max_usd,
                    ledger_path=Path(args.runs_dir) / ".state" / "write-budget.json")
    adapter = make_adapter(args.provider, args.model, budget)
    run = WritingRun(
        adapter, persona, brief,
        RunConfig(target_words=target_words, runs_dir=Path(args.runs_dir)), run_id=args.run_id,
    )
    final = run.run()
    print(f"run {run.run_id} complete: {run.run_dir}/final.md")
    print(f"spent: {budget.summary()}")
    print("\n" + final)
    return 0


def _cmd_benchmark(args: argparse.Namespace) -> int:
    providers = [p.strip() for p in args.providers.split(",") if p.strip()]
    conditions = [c.strip() for c in args.conditions.split(",") if c.strip()]
    if (not providers or len(set(providers)) != len(providers)
            or any(p not in {"anthropic", "openai", "mock"} for p in providers)
            or not conditions or len(set(conditions)) != len(conditions)
            or any(c not in _CALL_FORECAST for c in conditions)):
        raise ValueError("invalid or duplicate provider/condition")
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
    print(f"plan: {len(items)} cells, illustrative ~{worst_calls} LLM calls (not a hard bound)")
    print(f"offline estimate cap: ${args.max_usd:.6f} total, {args.max_calls} calls TOTAL")
    if args.dry_run:
        for item in items:
            print(f"  {item.brief_id} / {item.persona_name} / {item.condition} / {item.provider}")
        return 0

    results_dir = Path(args.results)
    _offline_only(providers, detector=args.detector)
    shared_budget = Budget(max_calls=args.max_calls, max_usd=args.max_usd,
                           ledger_path=results_dir / ".state" / "benchmark-budget.json")
    for completed, item in enumerate(items, start=1):
        adapter = make_adapter(item.provider, None, shared_budget)
        persona = Persona.load(Path(args.personas) / item.persona_name / "persona.json")
        result = run_item(item, adapter, persona, results_dir, args.target_words)
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
    judges = [j.strip() for j in args.judges.split(",") if j.strip()]
    if not judges or len(set(judges)) != len(judges):
        raise ValueError("invalid or duplicate judges")
    _offline_only(judges)
    # Receipts have four identity components; the aggregate judgments.json is not a cell.
    files = sorted(results_dir.glob("*__*__*__*.json"))
    by_key: dict[tuple, dict] = {}
    for file in files:
        data = completed_result(file)
        item = data.get("item")
        if (type(item) is not dict or set(item) != {"brief_id", "brief", "persona_name", "condition", "provider"}
                or any(not isinstance(v, str) for v in item.values())
                or item["condition"] not in _CALL_FORECAST or not isinstance(data.get("text"), str)):
            raise ValueError("invalid benchmark cell")
        expected = f"{item['brief_id']}__{item['persona_name']}__{item['condition']}__{item['provider']}.json"
        if file.name != expected or any("/" in item[k] or "\\" in item[k] or item[k] in {"", ".", ".."}
                                        for k in ("brief_id", "persona_name", "provider")):
            raise ValueError("benchmark filename identity mismatch")
        key = (item["brief_id"], item["persona_name"], item["provider"])
        by_key.setdefault(key, {})[item["condition"]] = data
    budget = Budget(max_calls=args.max_calls, max_usd=args.max_usd,
                    ledger_path=results_dir / ".state" / "judge-budget.json")
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
                brief = conditions["dwl"]["item"]["brief"]
                if conditions[baseline]["item"]["brief"] != brief:
                    raise ValueError("baseline and candidate brief differ")
                pair = [brief_id, persona_name, provider, baseline, judge_provider]
                identity = input_identity(judge, persona, brief, {
                    "pair": pair, "candidate": conditions["dwl"], "baseline": conditions[baseline],
                })
                verdicts = run_once(results_dir / ".state" / "judges" / f"{digest(pair)}.json", identity,
                    lambda: judge_symmetric(judge, brief, persona,
                                           conditions["dwl"]["text"], conditions[baseline]["text"]))
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
    atomic_json(out_path, out_rows)
    print(f"judgments written: {out_path} (spent ${budget.spent_usd:.2f})")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="dwl", description=__doc__)
    parser.add_argument("--env-file", help="path to a .env file (default: nearest .env in this directory or a parent)")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("check-env", help="report which API keys are visible (masked, no API calls)")
    p.set_defaults(func=_cmd_check_env)

    p = sub.add_parser("compile-persona", help="compile a writer corpus into a persona artifact")
    p.add_argument("--name", required=True)
    p.add_argument("--corpus", required=True)
    p.add_argument("--out")
    p.add_argument("--provider", default="none", help="none|mock; paid adapters are disabled")
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
    p.add_argument("--run-id", help="exact completed-run reuse; interrupted runs are not replayed")
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
    p.add_argument("--max-calls", type=int, default=80, help="total campaign call cap, including resumed calls")
    p.add_argument("--max-usd", type=float, default=25.0, help="offline estimate cap, not a billing guarantee")
    p.add_argument("--detector", choices=("none", "pangram"), default="none",
                   help="explicit opt-in; pangram currently refuses pending admitted connector")
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
    load_env(Path(args.env_file) if args.env_file else None)
    if hasattr(args, "max_calls"):
        Budget(max_calls=args.max_calls, max_usd=args.max_usd)  # Validate forecasts too.
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
