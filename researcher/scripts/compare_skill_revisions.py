#!/usr/bin/env python3
"""Deterministic pre-check for pairwise skill revision review."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from skill_frontmatter import parse_frontmatter as parse_skill_frontmatter


def section_set(text: str) -> set[str]:
    return set(re.findall(r"^##\s+(.+)$", text, flags=re.MULTILINE))


def parse_frontmatter(text: str) -> dict[str, str]:
    data, _issues = parse_skill_frontmatter(text)
    return {key: str(value) for key, value in data.items()}


def candidate_metrics(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    frontmatter = parse_frontmatter(text)
    sections = section_set(text)
    words = re.findall(r"[A-Za-z0-9_-]+", text)
    gotchas = 0
    if "Gotchas" in sections:
        gotchas_match = re.search(r"## Gotchas\n(.+?)(?:\n## |\Z)", text, flags=re.DOTALL)
        if gotchas_match:
            gotchas = len(re.findall(r"^\d+\.", gotchas_match.group(1), flags=re.MULTILINE))
    return {
        "path": str(path),
        "name": frontmatter.get("name", ""),
        "description_present": bool(frontmatter.get("description")),
        "line_count": len(text.splitlines()),
        "word_count": len(words),
        "sections": sorted(sections),
        "gotcha_count": gotchas,
        "has_references": "References" in sections,
        "has_integration": "Integration" in sections,
        "has_guidelines": "Guidelines" in sections,
    }


def structural_score(metrics: dict[str, Any]) -> float:
    score = 0.0
    if metrics["name"]:
        score += 0.15
    if metrics["description_present"]:
        score += 0.15
    if metrics["line_count"] <= 500:
        score += 0.2
    if metrics["gotcha_count"] >= 3:
        score += 0.15
    if metrics["has_guidelines"]:
        score += 0.1
    if metrics["has_integration"]:
        score += 0.1
    if metrics["has_references"]:
        score += 0.05
    if metrics["line_count"] <= 300:
        score += 0.1
    return round(score, 3)


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare two skill revisions before rubric review")
    parser.add_argument("candidate_a", type=Path)
    parser.add_argument("candidate_b", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    a = candidate_metrics(args.candidate_a)
    b = candidate_metrics(args.candidate_b)
    a["structural_score"] = structural_score(a)
    b["structural_score"] = structural_score(b)
    shared_sections = sorted(set(a["sections"]) & set(b["sections"]))
    section_delta = {
        "only_a": sorted(set(a["sections"]) - set(b["sections"])),
        "only_b": sorted(set(b["sections"]) - set(a["sections"])),
        "shared": shared_sections,
    }

    if a["structural_score"] > b["structural_score"]:
        recommendation = "A"
    elif b["structural_score"] > a["structural_score"]:
        recommendation = "B"
    elif a["line_count"] < b["line_count"]:
        recommendation = "A"
    elif b["line_count"] < a["line_count"]:
        recommendation = "B"
    else:
        recommendation = "human_review"

    result = {
        "candidate_a": a,
        "candidate_b": b,
        "section_delta": section_delta,
        "deterministic_recommendation": recommendation,
        "note": "Use researcher/rubrics/pairwise-skill-revision.md for final semantic judgment.",
    }
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Recommendation: {recommendation}")
        print(f"A score={a['structural_score']} lines={a['line_count']} gotchas={a['gotcha_count']}")
        print(f"B score={b['structural_score']} lines={b['line_count']} gotchas={b['gotcha_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
