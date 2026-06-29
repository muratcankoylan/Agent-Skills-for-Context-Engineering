#!/usr/bin/env python3
"""Create and manage file-based research-to-skill runs.

This runner does not call an LLM. It creates durable artifacts that autonomous
agents or humans can fill in, then runs deterministic validation.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[2]
RESEARCHER = ROOT / "researcher"
LOCKED_SURFACES = [
    "researcher/rubrics/content-curation.md",
    "researcher/rubrics/skill-change.md",
    "researcher/rubrics/harness-change.md",
    "researcher/mechanisms/registry.jsonl",
    ".claude-plugin/marketplace.json",
    ".plugin/plugin.json",
    "researcher/scripts/validate_repo.py",
]
VALID_CLOSE_STATUS = {"accepted", "rejected", "reference-only", "abandoned"}


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value[:64] or "research-run"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def append_jsonl(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(data, sort_keys=True) + "\n")


def run_relative(run_dir: Path) -> str:
    return str(run_dir.relative_to(ROOT))


def state_path(run_dir: Path) -> Path:
    return run_dir / "run-state.json"


def initial_state(run_dir: Path, title: str, source_url: str | None) -> dict[str, Any]:
    timestamp = utc_now()
    return {
        "run_id": run_dir.name,
        "title": title,
        "source_url": source_url or "",
        "current_state": "initialized",
        "close_status": None,
        "close_reason": None,
        "locked_surfaces": LOCKED_SURFACES,
        "editable_surfaces": [
            f"{run_relative(run_dir)}/sources/",
            f"{run_relative(run_dir)}/proposals/",
            f"{run_relative(run_dir)}/reports/",
            f"{run_relative(run_dir)}/logs/",
        ],
        "state_history": [
            {
                "state": "initialized",
                "timestamp": timestamp,
                "reason": "run initialized",
                "evidence": run_relative(run_dir),
            }
        ],
        "created_at": timestamp,
        "updated_at": timestamp,
    }


def load_state(run_dir: Path) -> dict[str, Any]:
    path = state_path(run_dir)
    if not path.exists():
        return initial_state(run_dir, run_dir.name, None)
    return load_json(path)


def write_state(run_dir: Path, state: dict[str, Any]) -> None:
    state["updated_at"] = utc_now()
    write_json(state_path(run_dir), state)


def set_state(run_dir: Path, state_name: str, reason: str, evidence: str = "") -> None:
    state = load_state(run_dir)
    state["current_state"] = state_name
    state.setdefault("state_history", []).append(
        {
            "state": state_name,
            "timestamp": utc_now(),
            "reason": reason,
            "evidence": evidence,
        }
    )
    write_state(run_dir, state)
    append_thread_decision(run_dir, f"state -> {state_name}", reason, evidence, "continue run")


def append_thread_decision(run_dir: Path, decision: str, reason: str, evidence: str, next_action: str) -> None:
    thread = run_dir / "THREAD.md"
    if not thread.exists():
        return
    entry = (
        "\n```text\n"
        f"{utc_now()} decision: {decision}\n"
        f"reason: {reason}\n"
        f"evidence: {evidence}\n"
        f"next: {next_action}\n"
        "```\n"
    )
    with thread.open("a", encoding="utf-8") as handle:
        handle.write(entry)


def create_thread(run_dir: Path, title: str, source_url: str | None) -> None:
    thread = f"""# Research Thread: {run_dir.name}

## Mission

- Objective: {title}
- Scope: Evaluate candidate sources and produce reviewable skill proposals.
- Started: {utc_now()}
- Owner: autonomous-research-loop
- Current status: active

## Locked Surfaces

- `researcher/rubrics/content-curation.md`
- `researcher/rubrics/skill-change.md`
- `researcher/rubrics/harness-change.md`
- `researcher/mechanisms/registry.jsonl`
- `.claude-plugin/marketplace.json`
- `.plugin/plugin.json`
- `researcher/scripts/validate_repo.py`
- Merge policy: agents may prepare PRs, but human approval is required for push and merge.

## Editable Surfaces

- `{run_dir.relative_to(ROOT)}/sources/`
- `{run_dir.relative_to(ROOT)}/proposals/`
- `{run_dir.relative_to(ROOT)}/reports/`

## Source Queue

| ID | Source | Status | Next Action |
| --- | --- | --- | --- |
| S001 | {source_url or 'TBD'} | discovered | evaluate |

## Decisions

```text
T+00:00 decision: run initialized
reason: file-based research loop created durable state
evidence: {run_dir.relative_to(ROOT)}
next: fill source evaluation and skill proposal
```

## Experiments And Evaluations

| ID | Artifact | Rubric | Result | Notes |
| --- | --- | --- | --- | --- |

## Open Questions

- None recorded.

## Handover Summary

- Best current candidate: none yet
- Rejected candidates: none yet
- Unresolved risks: source evaluation is a draft until rubric fields are completed
- Files to read first: `THREAD.md`, `sources/evaluations/source-evaluation-draft.json`, `proposals/skill-proposal.md`
- Next concrete action: retrieve the source and complete content curation
"""
    (run_dir / "THREAD.md").write_text(thread, encoding="utf-8")


def create_source_evaluation(
    run_dir: Path,
    title: str,
    source_url: str,
    author_or_org: str,
    source_type: str,
) -> None:
    template = load_json(RESEARCHER / "templates" / "source-evaluation.json")
    template["evaluation_id"] = str(uuid4())
    template["timestamp"] = utc_now()
    template["source"].update(
        {
            "url": source_url,
            "title": title,
            "author_or_org": author_or_org,
            "published_at": "",
            "source_type": source_type,
            "retrieval_status": "partial" if source_url else "failed",
            "primary_or_secondary": "primary",
        }
    )
    template["decision"].update(
        {
            "verdict": "HUMAN_REVIEW",
            "override_triggered": "null",
            "confidence": "low",
            "justification": "Draft scaffold. Complete gates and scoring after retrieval.",
        }
    )
    write_json(run_dir / "sources" / "evaluations" / "source-evaluation-draft.json", template)


def create_skill_proposal(run_dir: Path, title: str, source_url: str) -> None:
    proposal = (RESEARCHER / "templates" / "skill-proposal.md").read_text(encoding="utf-8")
    proposal = proposal.replace("# Skill Proposal: [Short Title]", f"# Skill Proposal: {title}")
    proposal = proposal.replace("- URL:", f"- URL: {source_url}")
    proposal = proposal.replace("- Title:", f"- Title: {title}")
    proposal = proposal.replace("- Retrieval status:", "- Retrieval status: partial")
    proposal = proposal.replace("- Decision: APPROVE / HUMAN_REVIEW / REJECT", "- Decision: HUMAN_REVIEW")
    (run_dir / "proposals" / "skill-proposal.md").write_text(proposal, encoding="utf-8")
    (run_dir / "proposals" / "mechanism-proposal.jsonl").write_text(
        (RESEARCHER / "templates" / "mechanism-proposal.jsonl").read_text(encoding="utf-8"),
        encoding="utf-8",
    )


def update_queue(run_dir: Path, **updates: Any) -> None:
    queue = run_dir / "sources" / "queue.jsonl"
    if not queue.exists():
        raise FileNotFoundError(f"source queue missing: {queue}")
    records = [json.loads(line) for line in queue.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not records:
        raise ValueError("source queue is empty")
    records[0].update(updates)
    queue.write_text("\n".join(json.dumps(record, sort_keys=True) for record in records) + "\n", encoding="utf-8")


def completed_evaluation(run_dir: Path) -> Path:
    eval_dir = run_dir / "sources" / "evaluations"
    completed = sorted(path for path in eval_dir.glob("*.json") if "draft" not in path.stem)
    if not completed:
        raise FileNotFoundError("completed source evaluation missing")
    return completed[0]


def proposal_file(run_dir: Path) -> Path:
    path = run_dir / "proposals" / "skill-proposal.md"
    if not path.exists():
        raise FileNotFoundError(f"skill proposal missing: {path}")
    return path


def retrieve_source(args: argparse.Namespace) -> int:
    run_dir = args.run_dir.resolve()
    raw_dir = run_dir / "sources" / "evidence" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for source in args.file or []:
        target = raw_dir / source.name
        shutil.copy2(source, target)
        copied.append(str(target.relative_to(ROOT)))
    update_queue(
        run_dir,
        retrieval_status="retrieved",
        retrieved_at=utc_now(),
        raw_evidence=copied,
        retrieval_notes=args.notes,
    )
    set_state(
        run_dir,
        "retrieved",
        "source evidence retrieved",
        ", ".join(copied) if copied else "manual retrieval recorded",
    )
    return 0


def mark_evaluated(args: argparse.Namespace) -> int:
    run_dir = args.run_dir.resolve()
    eval_path = completed_evaluation(run_dir)
    data = load_json(eval_path)
    update_queue(
        run_dir,
        retrieval_status=data.get("source", {}).get("retrieval_status", "retrieved"),
        evaluation_file=str(eval_path.relative_to(ROOT)),
        evaluation_decision=data.get("decision", {}).get("verdict", ""),
    )
    set_state(run_dir, "evaluated", "completed source evaluation recorded", str(eval_path.relative_to(ROOT)))
    return 0


def mark_proposed(args: argparse.Namespace) -> int:
    run_dir = args.run_dir.resolve()
    path = proposal_file(run_dir)
    set_state(run_dir, "proposed", "skill proposal recorded", str(path.relative_to(ROOT)))
    return 0


def run_novelty(args: argparse.Namespace) -> int:
    run_dir = args.run_dir.resolve()
    path = proposal_file(run_dir)
    result_path = run_dir / "reports" / "novelty-result.json"
    cmd = [
        sys.executable,
        str(RESEARCHER / "scripts" / "novelty_check.py"),
        "--file",
        str(path),
        "--json",
    ]
    completed = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)
    if completed.stdout:
        result = json.loads(completed.stdout)
    else:
        result = {
            "verdict": "human_review",
            "error": completed.stderr or "novelty_check.py produced no output",
        }
    if args.human_review_rationale:
        result["human_review_rationale"] = args.human_review_rationale
    write_json(result_path, result)
    set_state(run_dir, "novelty_checked", "novelty result recorded", str(result_path.relative_to(ROOT)))
    return completed.returncode


def run_run_validator(run_dir: Path) -> int:
    report_json = run_dir / "reports" / "run-readiness.json"
    report_md = run_dir / "reports" / "run-readiness.md"
    cmd = [
        sys.executable,
        str(RESEARCHER / "scripts" / "validate_run.py"),
        "--run-dir",
        str(run_dir),
        "--json",
    ]
    completed = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)
    report_json.write_text(completed.stdout or json.dumps({"ok": False, "error": completed.stderr}), encoding="utf-8")
    try:
        data = json.loads(completed.stdout)
        summary = data.get("summary", {})
        text = (
            "# Run Readiness Report\n\n"
            f"Run validation {'passed' if data.get('ok') else 'failed'}: "
            f"{summary.get('errors', 0)} errors, {summary.get('warnings', 0)} warnings.\n"
        )
    except json.JSONDecodeError:
        text = f"# Run Readiness Report\n\nValidation command failed.\n\n{completed.stderr}\n"
    report_md.write_text(text, encoding="utf-8")
    if completed.returncode == 0:
        set_state(run_dir, "validated", "run readiness validation passed", str(report_json.relative_to(ROOT)))
    return completed.returncode


def run_validator(run_dir: Path) -> int:
    report_json = run_dir / "reports" / "validation-report.json"
    report_md = run_dir / "reports" / "validation-report.md"
    cmd = [
        sys.executable,
        str(RESEARCHER / "scripts" / "validate_repo.py"),
        "--strict",
        "--root",
        str(ROOT),
        "--json",
    ]
    completed = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)
    if completed.stdout:
        report_json.write_text(completed.stdout, encoding="utf-8")
    else:
        report_json.write_text(
            json.dumps(
                {
                    "ok": False,
                    "summary": {"errors": 1, "warnings": 0, "skill_count": 0},
                    "findings": [
                        {
                            "severity": "error",
                            "path": "researcher/scripts/validate_repo.py",
                            "message": completed.stderr or "validator produced no output",
                        }
                    ],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    summary = "Validation command exited with code " + str(completed.returncode)
    if completed.stdout:
        try:
            data = json.loads(completed.stdout)
            summary = (
                f"Validation {'passed' if data.get('ok') else 'failed'}: "
                f"{data.get('summary', {}).get('errors', 0)} errors, "
                f"{data.get('summary', {}).get('warnings', 0)} warnings."
            )
        except json.JSONDecodeError:
            pass
    report_md.write_text(f"# Validation Report\n\n{summary}\n", encoding="utf-8")
    return completed.returncode


def write_pr_readiness(args: argparse.Namespace) -> int:
    run_dir = args.run_dir.resolve()
    path = run_dir / "reports" / "pr-readiness.md"
    text = f"""# PR Readiness Notes

## Summary

{args.summary}

## Test Plan

{args.test_plan}

## Risks

{args.risks}

Merge and push require explicit human approval.
"""
    path.write_text(text, encoding="utf-8")
    set_state(run_dir, "pr_ready", "PR readiness notes recorded", str(path.relative_to(ROOT)))
    return 0


def close_run(args: argparse.Namespace) -> int:
    if args.status not in VALID_CLOSE_STATUS:
        raise ValueError(f"status must be one of {sorted(VALID_CLOSE_STATUS)}")
    run_dir = args.run_dir.resolve()
    closure = {
        "status": args.status,
        "reason": args.reason,
        "closed_at": utc_now(),
        "reviewed_by": args.reviewed_by,
    }
    path = run_dir / "reports" / "closure.json"
    write_json(path, closure)
    state = load_state(run_dir)
    state["current_state"] = "closed"
    state["close_status"] = args.status
    state["close_reason"] = args.reason
    state.setdefault("state_history", []).append(
        {
            "state": "closed",
            "timestamp": utc_now(),
            "reason": args.reason,
            "evidence": str(path.relative_to(ROOT)),
        }
    )
    write_state(run_dir, state)
    append_thread_decision(run_dir, f"closed as {args.status}", args.reason, str(path.relative_to(ROOT)), "stop run")
    return 0


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"JSONL file missing: {path}")
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number} invalid JSONL: {exc}") from exc
    return records


def run_readiness_ok(run_dir: Path) -> bool:
    cmd = [
        sys.executable,
        str(RESEARCHER / "scripts" / "validate_run.py"),
        "--run-dir",
        str(run_dir),
        "--json",
    ]
    completed = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        return False
    try:
        return bool(json.loads(completed.stdout).get("ok"))
    except json.JSONDecodeError:
        return False


def promote_mechanisms(args: argparse.Namespace) -> int:
    if not args.reviewed_by:
        raise ValueError("--reviewed-by is required for mechanism promotion")
    run_dir = args.run_dir.resolve()
    proposal_path = run_dir / "proposals" / "mechanism-proposal.jsonl"
    proposals = load_jsonl(proposal_path)
    if not proposals:
        raise ValueError("mechanism proposal file is empty")

    registry_path = RESEARCHER / "mechanisms" / "registry.jsonl"
    accepted_ledger = RESEARCHER / "mechanisms" / "ledgers" / "accepted.jsonl"
    rejected_ledger = RESEARCHER / "mechanisms" / "ledgers" / "rejected.jsonl"
    existing_ids = {
        record.get("mechanism_id")
        for record in load_jsonl(registry_path)
        if record.get("mechanism_id")
    }
    promoted = 0
    rejected = 0
    readiness_ok = run_readiness_ok(run_dir)

    for proposal in proposals:
        status = proposal.get("status_recommendation")
        mechanism_id = proposal.get("mechanism_id")
        if not mechanism_id or mechanism_id == "kebab-case-id":
            raise ValueError("mechanism proposal contains placeholder mechanism_id")
        event = {
            "mechanism_id": mechanism_id,
            "status": status,
            "reviewed_by": args.reviewed_by,
            "run_dir": run_relative(run_dir),
            "rationale": proposal.get("review_rationale", ""),
            "timestamp": utc_now(),
        }
        if status in {"accepted", "candidate"}:
            if not readiness_ok and not args.allow_unready:
                raise ValueError("run readiness must pass before promoting accepted or candidate mechanisms")
            if mechanism_id in existing_ids:
                raise ValueError(f"mechanism already exists in registry: {mechanism_id}")
            registry_entry = {
                "mechanism_id": mechanism_id,
                "owning_skill": proposal.get("owning_skill", ""),
                "status": status,
                "activation_scenario": proposal.get("activation_scenario", ""),
                "behavior_change": proposal.get("behavior_change", ""),
                "evidence": proposal.get("evidence_claim_ids", []),
                "failure_modes": proposal.get("failure_modes", []),
            }
            append_jsonl(registry_path, registry_entry)
            append_jsonl(accepted_ledger, event)
            existing_ids.add(mechanism_id)
            promoted += 1
        elif status == "rejected":
            append_jsonl(rejected_ledger, event)
            rejected += 1
        else:
            raise ValueError("status_recommendation must be accepted, candidate, or rejected")

    set_state(
        run_dir,
        "validated" if promoted else "closed",
        f"mechanism promotion complete: {promoted} promoted, {rejected} rejected",
        str(proposal_path.relative_to(ROOT)),
    )
    return 0


def create_run(args: argparse.Namespace) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    run_dir = RESEARCHER / "runs" / f"{timestamp}-{slugify(args.title)}"
    for child in [
        run_dir / "sources" / "evaluations",
        run_dir / "proposals",
        run_dir / "reports",
        run_dir / "logs",
        run_dir / "sources" / "evidence" / "raw",
    ]:
        child.mkdir(parents=True, exist_ok=False)

    source_record = {
        "id": "S001",
        "url": args.url,
        "title": args.title,
        "author_or_org": args.author_or_org,
        "source_type": args.source_type,
        "retrieval_status": "partial" if args.url else "failed",
        "candidate_reason": args.reason,
        "created_at": utc_now(),
    }
    (run_dir / "sources" / "queue.jsonl").write_text(
        json.dumps(source_record) + "\n",
        encoding="utf-8",
    )
    create_thread(run_dir, args.title, args.url)
    write_state(run_dir, initial_state(run_dir, args.title, args.url))
    create_source_evaluation(run_dir, args.title, args.url, args.author_or_org, args.source_type)
    create_skill_proposal(run_dir, args.title, args.url)
    run_validator(run_dir)
    return run_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="Create durable research-to-skill run artifacts")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="initialize a research run")
    init.add_argument("--title", required=True, help="candidate source or run title")
    init.add_argument("--url", default="", help="candidate source URL")
    init.add_argument("--author-or-org", default="", help="source author or organization")
    init.add_argument(
        "--source-type",
        default="other",
        choices=["paper", "engineering_blog", "documentation", "benchmark", "code", "talk", "other"],
    )
    init.add_argument("--reason", default="", help="why this source/run matters")

    validate = sub.add_parser("validate", help="run deterministic repo validation")
    validate.add_argument("--run-dir", type=Path, help="optional run directory to store report")

    retrieve = sub.add_parser("retrieve", help="record retrieved source evidence for a run")
    retrieve.add_argument("--run-dir", type=Path, required=True)
    retrieve.add_argument("--file", type=Path, action="append", help="raw evidence file to copy into the run")
    retrieve.add_argument("--notes", default="", help="retrieval notes")

    evaluate = sub.add_parser("evaluate", help="mark a run as source-evaluated")
    evaluate.add_argument("--run-dir", type=Path, required=True)

    propose = sub.add_parser("propose", help="mark a run as having a proposal")
    propose.add_argument("--run-dir", type=Path, required=True)

    novelty = sub.add_parser("novelty", help="run novelty check and persist result")
    novelty.add_argument("--run-dir", type=Path, required=True)
    novelty.add_argument("--human-review-rationale", default="")

    validate_run = sub.add_parser("validate-run", help="validate run publish readiness")
    validate_run.add_argument("--run-dir", type=Path, required=True)

    pr_ready = sub.add_parser("pr-ready", help="write PR readiness notes")
    pr_ready.add_argument("--run-dir", type=Path, required=True)
    pr_ready.add_argument("--summary", required=True)
    pr_ready.add_argument("--test-plan", required=True)
    pr_ready.add_argument("--risks", required=True)

    close = sub.add_parser("close", help="close a run with rationale")
    close.add_argument("--run-dir", type=Path, required=True)
    close.add_argument("--status", required=True, choices=sorted(VALID_CLOSE_STATUS))
    close.add_argument("--reason", required=True)
    close.add_argument("--reviewed-by", default="")

    promote = sub.add_parser("promote-mechanisms", help="promote reviewed mechanism proposals")
    promote.add_argument("--run-dir", type=Path, required=True)
    promote.add_argument("--reviewed-by", required=True)
    promote.add_argument(
        "--allow-unready",
        action="store_true",
        help="allow promotion before run readiness; intended only for bootstrapping fixtures",
    )

    args = parser.parse_args()
    if args.command == "init":
        run_dir = create_run(args)
        print(run_dir.relative_to(ROOT))
        return 0
    if args.command == "validate":
        if args.run_dir:
            (args.run_dir / "reports").mkdir(parents=True, exist_ok=True)
            return run_validator(args.run_dir)
        cmd = [sys.executable, str(RESEARCHER / "scripts" / "validate_repo.py"), "--strict"]
        return subprocess.run(cmd, cwd=ROOT, check=False).returncode
    if args.command == "retrieve":
        return retrieve_source(args)
    if args.command == "evaluate":
        return mark_evaluated(args)
    if args.command == "propose":
        return mark_proposed(args)
    if args.command == "novelty":
        return run_novelty(args)
    if args.command == "validate-run":
        return run_run_validator(args.run_dir.resolve())
    if args.command == "pr-ready":
        return write_pr_readiness(args)
    if args.command == "close":
        return close_run(args)
    if args.command == "promote-mechanisms":
        return promote_mechanisms(args)
    return 1


if __name__ == "__main__":
    sys.exit(main())
