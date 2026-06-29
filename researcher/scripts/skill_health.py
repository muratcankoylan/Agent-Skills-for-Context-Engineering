#!/usr/bin/env python3
"""Deterministic per-skill health metrics.

Produces a quality score per skill plus a corpus aggregate. Catches drift before
users notice: missing sections, stale claims, dead internal links, weak gotchas.

Run with no arguments for the default report. Use --json for machine output.
Output is written to researcher/reports/skill-health.json by default and can be
piped into the daily snapshot for longitudinal trend tracking.

This script is intentionally deterministic. It does not call any LLM and does
not make outbound HTTP requests unless --check-urls is set (off by default).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from skill_frontmatter import parse_frontmatter as parse_skill_frontmatter


ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = ROOT / "skills"
CLAIMS_FILE = ROOT / "researcher" / "claims" / "index.jsonl"
MECHANISMS_FILE = ROOT / "researcher" / "mechanisms" / "registry.jsonl"
ACTIVATION_FILE = ROOT / "researcher" / "fixtures" / "activation-cases.jsonl"
DEFAULT_OUTPUT = ROOT / "researcher" / "reports" / "skill-health.json"
HISTORY_FILE = ROOT / "researcher" / "reports" / "skill-health-history.jsonl"

REQUIRED_SECTIONS = [
    "## When to Activate",
    "## Core Concepts",
    "## Practical Guidance",
    "## Gotchas",
    "## Integration",
    "## References",
]

NUMERIC_CLAIM_PATTERNS = [
    re.compile(r"\b\d+(?:\.\d+)?\s*%"),
    re.compile(r"\b\d+(?:\.\d+)?\s*x\b"),
    re.compile(r"\b\d+(?:\.\d+)?\s*ms\b"),
    re.compile(r"\b\d+(?:\.\d+)?\s*s(?:ec|econds)?\b"),
    re.compile(r"\b\d+(?:\.\d+)?\s*tokens?\b", re.IGNORECASE),
    re.compile(r"\b\d+(?:k|K|M|B|x)\b"),
]

BENCHMARK_NAMES = {
    "LoCoMo",
    "LongMemEval",
    "BrowseComp",
    "SWE-bench",
    "RULER",
    "DMR",
    "HotPotQA",
    "MMLU",
    "GSM8K",
    "HumanEval",
}

CLAIM_ID_PATTERN = re.compile(r"\bclaim-[a-z0-9][a-z0-9-]*[a-z0-9]\b")
INTERNAL_SKILL_LINK = re.compile(r"\[([^\]]+)\]\((?:\.\./)?skills/([a-z0-9-]+)/(?:[^)]*)\)")
EXTERNAL_LINK = re.compile(r"\[(?:[^\]]+)\]\((https?://[^)]+)\)")
FENCE_LINE = re.compile(r"^\s*```")


@dataclass
class SkillHealth:
    name: str
    path: str
    line_count: int = 0
    line_count_ok: bool = True
    frontmatter_valid: bool = True
    frontmatter_issues: list[str] = field(default_factory=list)
    missing_sections: list[str] = field(default_factory=list)
    gotcha_count: int = 0
    code_example_count: int = 0
    internal_links_total: int = 0
    internal_links_resolved: int = 0
    external_link_count: int = 0
    external_link_results: list[dict[str, Any]] = field(default_factory=list)
    numeric_claims_total: int = 0
    numeric_claims_with_id: int = 0
    claim_ids_referenced: list[str] = field(default_factory=list)
    claim_ids_unknown: list[str] = field(default_factory=list)
    mechanism_count: int = 0
    activation_case_count: int = 0
    score: float = 0.0
    flagged: bool = False


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def parse_frontmatter(text: str) -> tuple[dict[str, str], list[str]]:
    data, issues = parse_skill_frontmatter(text)
    return {key: str(value) for key, value in data.items()}, issues


def count_gotchas(text: str) -> int:
    match = re.search(r"^## Gotchas\s*\n(.+?)(?=\n## |\Z)", text, flags=re.DOTALL | re.MULTILINE)
    if not match:
        return 0
    body = match.group(1)
    return len(re.findall(r"^\s*\d+\.\s+", body, flags=re.MULTILINE))


def count_code_examples(text: str) -> int:
    fence_open = 0
    for line in text.splitlines():
        if FENCE_LINE.match(line):
            fence_open += 1
    return fence_open // 2


def count_numeric_claims(text: str) -> int:
    total = 0
    for pattern in NUMERIC_CLAIM_PATTERNS:
        total += len(pattern.findall(text))
    for name in BENCHMARK_NAMES:
        total += text.count(name)
    return total


def collect_internal_links(text: str) -> tuple[int, int]:
    matches = INTERNAL_SKILL_LINK.findall(text)
    total = len(matches)
    resolved = 0
    for _, target in matches:
        if (SKILLS_DIR / target / "SKILL.md").exists():
            resolved += 1
    return total, resolved


def collect_external_links(text: str, check_urls: bool, timeout: float) -> tuple[int, list[dict[str, Any]]]:
    urls = EXTERNAL_LINK.findall(text)
    results: list[dict[str, Any]] = []
    if not check_urls:
        return len(urls), results
    for url in urls:
        try:
            request = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "skill-health/0.1"})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                results.append({"url": url, "status": response.status})
        except urllib.error.HTTPError as exc:
            results.append({"url": url, "status": exc.code, "error": str(exc)})
        except (urllib.error.URLError, TimeoutError) as exc:
            results.append({"url": url, "status": "unreachable", "error": str(exc)})
    return len(urls), results


def collect_claim_ids(text: str, known_claim_ids: set[str]) -> tuple[list[str], list[str], int]:
    found = list(set(CLAIM_ID_PATTERN.findall(text)))
    unknown = [cid for cid in found if cid not in known_claim_ids]
    return sorted(found), sorted(unknown), len(found)


def normalize(value: int, target: int) -> float:
    if target <= 0:
        return 0.0
    return min(1.0, value / target)


def compute_score(record: SkillHealth) -> float:
    required_section_score = (len(REQUIRED_SECTIONS) - len(record.missing_sections)) / len(REQUIRED_SECTIONS)
    gotcha_score = normalize(record.gotcha_count, target=3)
    code_score = normalize(record.code_example_count, target=2)
    if record.internal_links_total:
        internal_score = record.internal_links_resolved / record.internal_links_total
    else:
        internal_score = 1.0
    if record.numeric_claims_total:
        claim_score = record.numeric_claims_with_id / record.numeric_claims_total
    else:
        claim_score = 1.0
    activation_score = 1.0 if record.activation_case_count >= 1 else 0.5
    mechanism_score = 1.0 if record.mechanism_count >= 1 else 0.5
    frontmatter_score = 1.0 if record.frontmatter_valid else 0.0

    return round(
        0.20 * required_section_score
        + 0.15 * gotcha_score
        + 0.10 * code_score
        + 0.15 * internal_score
        + 0.10 * activation_score
        + 0.15 * claim_score
        + 0.10 * mechanism_score
        + 0.05 * frontmatter_score,
        4,
    )


def evaluate_skill(
    skill_dir: Path,
    known_claim_ids: set[str],
    mechanism_owners: dict[str, int],
    activation_owners: dict[str, int],
    check_urls: bool,
    url_timeout: float,
) -> SkillHealth:
    skill_file = skill_dir / "SKILL.md"
    record = SkillHealth(
        name=skill_dir.name,
        path=str(skill_file.relative_to(ROOT)),
    )
    if not skill_file.exists():
        record.frontmatter_valid = False
        record.frontmatter_issues.append("SKILL.md missing")
        record.flagged = True
        return record

    text = skill_file.read_text(encoding="utf-8")
    lines = text.splitlines()
    record.line_count = len(lines)
    record.line_count_ok = record.line_count <= 500

    frontmatter, issues = parse_frontmatter(text)
    record.frontmatter_issues = issues
    name = frontmatter.get("name", "")
    description = frontmatter.get("description", "")
    if not name:
        issues.append("missing name")
    elif name != skill_dir.name:
        issues.append(f"name '{name}' does not match directory '{skill_dir.name}'")
    if not description:
        issues.append("missing description")
    elif len(description) > 1024:
        issues.append("description exceeds 1024 characters")
    if re.search(r"\b(I can|Use me|You can use this)\b", description):
        issues.append("description may not be third person")
    record.frontmatter_valid = not issues and bool(name) and bool(description)

    for section in REQUIRED_SECTIONS:
        if section not in text:
            record.missing_sections.append(section)

    record.gotcha_count = count_gotchas(text)
    record.code_example_count = count_code_examples(text)
    record.internal_links_total, record.internal_links_resolved = collect_internal_links(text)
    record.external_link_count, record.external_link_results = collect_external_links(text, check_urls, url_timeout)

    record.numeric_claims_total = count_numeric_claims(text)
    found, unknown, with_id = collect_claim_ids(text, known_claim_ids)
    record.claim_ids_referenced = found
    record.claim_ids_unknown = unknown
    record.numeric_claims_with_id = with_id

    record.mechanism_count = mechanism_owners.get(skill_dir.name, 0)
    record.activation_case_count = activation_owners.get(skill_dir.name, 0)

    record.score = compute_score(record)
    record.flagged = record.score < 0.75 or not record.line_count_ok or bool(record.missing_sections) or not record.frontmatter_valid
    return record


def build_report(check_urls: bool, url_timeout: float) -> dict[str, Any]:
    if not SKILLS_DIR.exists():
        return {
            "ok": False,
            "error": f"skills directory missing at {SKILLS_DIR}",
            "skills": [],
        }

    claims = load_jsonl(CLAIMS_FILE)
    known_claim_ids = {record.get("claim_id") for record in claims if record.get("claim_id")}

    mechanisms = load_jsonl(MECHANISMS_FILE)
    mechanism_owners: dict[str, int] = {}
    for entry in mechanisms:
        owner = entry.get("owning_skill")
        if isinstance(owner, str):
            mechanism_owners[owner] = mechanism_owners.get(owner, 0) + 1

    activation_owners: dict[str, int] = {}
    for entry in load_jsonl(ACTIVATION_FILE):
        owner = entry.get("expected_primary_skill")
        if isinstance(owner, str):
            activation_owners[owner] = activation_owners.get(owner, 0) + 1

    skills: list[SkillHealth] = []
    for skill_dir in sorted(p for p in SKILLS_DIR.iterdir() if p.is_dir()):
        skills.append(
            evaluate_skill(
                skill_dir,
                known_claim_ids,
                mechanism_owners,
                activation_owners,
                check_urls,
                url_timeout,
            )
        )

    scores = [record.score for record in skills]
    corpus_score = round(sum(scores) / len(scores), 4) if scores else 0.0
    flagged = sum(1 for record in skills if record.flagged)

    return {
        "ok": flagged == 0,
        "summary": {
            "skill_count": len(skills),
            "corpus_score": corpus_score,
            "min_score": min(scores) if scores else 0.0,
            "max_score": max(scores) if scores else 0.0,
            "flagged": flagged,
            "known_claim_ids": len(known_claim_ids),
            "mechanism_owners": mechanism_owners,
            "activation_owners": activation_owners,
        },
        "skills": [asdict(record) for record in skills],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Deterministic skill health report")
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON to stdout")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="path to write the JSON report")
    parser.add_argument("--check-urls", action="store_true", help="perform HEAD requests on external URLs")
    parser.add_argument("--url-timeout", type=float, default=10.0, help="seconds per external HEAD request")
    parser.add_argument("--strict", action="store_true", help="exit non-zero if any skill is flagged")
    parser.add_argument("--no-history", action="store_true", help="do not append a one-line summary to the history file")
    args = parser.parse_args()

    report = build_report(args.check_urls, args.url_timeout)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    if not args.no_history:
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        history_entry = {
            "ok": report.get("ok"),
            "summary": report.get("summary"),
        }
        with HISTORY_FILE.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(history_entry, sort_keys=True) + "\n")

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        summary = report.get("summary", {})
        print(
            f"Skill health: corpus={summary.get('corpus_score', 0.0)} "
            f"min={summary.get('min_score', 0.0)} "
            f"flagged={summary.get('flagged', 0)} "
            f"skills={summary.get('skill_count', 0)}"
        )
        for record in report.get("skills", []):
            marker = "FLAG" if record["flagged"] else "ok  "
            print(f"  {marker} {record['name']:<28} score={record['score']:.3f} lines={record['line_count']}")
        print(f"Wrote report to {args.output.relative_to(ROOT)}")

    if args.strict and not report.get("ok"):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
