#!/usr/bin/env python3
"""Deterministically smoke-test skill activation boundaries."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from skill_frontmatter import parse_frontmatter as parse_skill_frontmatter


ROOT = Path(__file__).resolve().parents[2]
STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "into",
    "from",
    "agent",
    "agents",
    "skill",
    "skills",
    "build",
    "create",
    "design",
    "whether",
    "output",
    "outputs",
    "before",
    "later",
    "can",
    "should",
}


def tokens(text: str) -> set[str]:
    raw = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", text.lower())
    return {token.replace("_", "-") for token in raw if token not in STOPWORDS}


def parse_frontmatter(text: str) -> dict[str, str]:
    data, _issues = parse_skill_frontmatter(text)
    return {key: str(value) for key, value in data.items()}


def activation_text(text: str) -> str:
    frontmatter = parse_frontmatter(text)
    parts = [frontmatter.get("description", "")]
    match = re.search(r"## When to Activate\n(.+?)(?:\n## |\Z)", text, flags=re.DOTALL)
    if match:
        parts.append(match.group(1))
    return "\n".join(parts)


def load_skills(root: Path) -> dict[str, set[str]]:
    skills: dict[str, set[str]] = {}
    for path in sorted((root / "skills").glob("*/SKILL.md")):
        skills[path.parent.name] = tokens(activation_text(path.read_text(encoding="utf-8")))
    return skills


def load_cases(path: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            cases.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number} invalid JSONL: {exc}") from exc
    return cases


def rank_skills(prompt: str, skills: dict[str, set[str]]) -> list[dict[str, Any]]:
    prompt_tokens = tokens(prompt)
    ranked: list[dict[str, Any]] = []
    for name, skill_tokens in skills.items():
        shared = prompt_tokens & skill_tokens
        score = len(shared) / max(len(prompt_tokens), 1)
        ranked.append({"skill": name, "score": round(score, 4), "shared_terms": sorted(shared)})
    ranked.sort(key=lambda item: (item["score"], item["skill"]), reverse=True)
    return ranked


def evaluate(root: Path, cases_path: Path) -> dict[str, Any]:
    skills = load_skills(root)
    results: list[dict[str, Any]] = []
    for case in load_cases(cases_path):
        ranked = rank_skills(case["prompt"], skills)
        top_three = [item["skill"] for item in ranked[:3]]
        rejected_in_top_three = sorted(set(case.get("rejected_skills", [])) & set(top_three))
        expected = case["expected_primary_skill"]
        passed = expected in top_three and not rejected_in_top_three
        results.append(
            {
                "case_id": case["case_id"],
                "passed": passed,
                "expected_primary_skill": expected,
                "top_three": top_three,
                "rejected_in_top_three": rejected_in_top_three,
                "ranked": ranked[:5],
            }
        )
    failures = [result for result in results if not result["passed"]]
    return {
        "ok": not failures,
        "summary": {"cases": len(results), "failures": len(failures)},
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check deterministic skill activation cases")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument(
        "--cases",
        type=Path,
        default=ROOT / "researcher" / "fixtures" / "activation-cases.jsonl",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = evaluate(args.root, args.cases)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(
            f"Activation cases {'passed' if result['ok'] else 'failed'}: "
            f"{result['summary']['cases']} cases, {result['summary']['failures']} failures"
        )
        for item in result["results"]:
            if not item["passed"]:
                print(f"- {item['case_id']}: expected {item['expected_primary_skill']} top={item['top_three']}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
