#!/usr/bin/env python3
"""Create and manage file-based research-to-skill runs.

This runner does not call an LLM. It creates durable artifacts that autonomous
agents or humans can fill in, then runs deterministic validation.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

if __package__:
    from .loop_common import DurabilityUncertainError, write_json, write_jsonl, write_text
    from .validate_run import (
        CANONICAL_LOCKED_SURFACES,
        LEGAL_STATE_TRANSITIONS,
        MAX_EVIDENCE_BATCH_BYTES,
        MAX_EVIDENCE_FILE_BYTES,
        MAX_EVIDENCE_FILES,
        RunValidator,
        expected_run_editable_surfaces,
        normalize_source_url,
        parse_utc_datetime,
        strict_json_loads,
        validate_state_document,
    )
else:  # Direct script execution.
    from loop_common import DurabilityUncertainError, write_json, write_jsonl, write_text
    from validate_run import (
        CANONICAL_LOCKED_SURFACES,
        LEGAL_STATE_TRANSITIONS,
        MAX_EVIDENCE_BATCH_BYTES,
        MAX_EVIDENCE_FILE_BYTES,
        MAX_EVIDENCE_FILES,
        RunValidator,
        expected_run_editable_surfaces,
        normalize_source_url,
        parse_utc_datetime,
        strict_json_loads,
        validate_state_document,
    )


ROOT = Path(__file__).resolve().parents[2]
RESEARCHER = ROOT / "researcher"
LOCKED_SURFACES = list(CANONICAL_LOCKED_SURFACES)
VALID_CLOSE_STATUS = {"accepted", "rejected", "reference-only", "abandoned"}
WRITABLE_CLOSE_STATUS = {"rejected", "reference-only", "abandoned"}
RUN_INIT_STAGING_NAME = ".run-init-staging"
LOCAL_CHECK_TIMEOUT_SECONDS = 300
INITIAL_RUN_DIRECTORIES = frozenset(
    {
        "logs",
        "proposals",
        "reports",
        "sources",
        "sources/evaluations",
        "sources/evidence",
        "sources/evidence/raw",
    }
)
INITIAL_RUN_FILES = frozenset(
    {
        "THREAD.md",
        "run-state.json",
        "proposals/mechanism-proposal.jsonl",
        "proposals/skill-proposal.md",
        "sources/evaluations/source-evaluation-draft.json",
        "sources/queue.jsonl",
    }
)


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value[:64] or "research-run"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def run_local_checker(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    """Run a local deterministic checker with a bounded, typed failure result."""

    try:
        return subprocess.run(
            cmd,
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=LOCAL_CHECK_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(
            cmd,
            124,
            "",
            f"checker timed out after {LOCAL_CHECK_TIMEOUT_SECONDS} seconds",
        )
    except OSError as exc:
        return subprocess.CompletedProcess(
            cmd,
            126,
            "",
            f"checker could not start: {exc}",
        )


def load_json(path: Path) -> Any:
    return strict_json_loads(path.read_text(encoding="utf-8"))


def run_relative(run_dir: Path) -> str:
    return str(run_dir.relative_to(ROOT))


def state_path(run_dir: Path) -> Path:
    return run_dir / "run-state.json"


def require_managed_runs_root() -> Path:
    """Return the canonical real runs root before any run-local side effect."""

    researcher_root = Path(os.path.abspath(RESEARCHER))
    runs_root = researcher_root / "runs"
    for candidate in (researcher_root, runs_root):
        try:
            info = os.lstat(candidate)
        except OSError as exc:
            raise ValueError(f"managed runs root is unavailable: {candidate}") from exc
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise ValueError(f"managed runs root must be a real directory: {candidate}")
        if candidate.resolve(strict=True) != candidate:
            raise ValueError(f"managed runs root escapes its canonical path: {candidate}")
    return runs_root


def _path_lexists(path: Path) -> bool:
    try:
        os.lstat(path)
    except FileNotFoundError:
        return False
    return True


def require_run_init_staging_root(runs_root: Path) -> Path:
    """Return the private repo-confined namespace used before run publication."""

    canonical_root = Path(os.path.abspath(ROOT))
    try:
        root_info = os.lstat(canonical_root)
    except OSError as exc:
        raise ValueError(f"repository root is unavailable: {canonical_root}") from exc
    expected_researcher = canonical_root / "researcher"
    if (
        stat.S_ISLNK(root_info.st_mode)
        or not stat.S_ISDIR(root_info.st_mode)
        or canonical_root.resolve(strict=True) != canonical_root
        or runs_root.parent != expected_researcher
    ):
        raise ValueError("run creation roots must be real and confined to the repository")

    staging_root = expected_researcher / RUN_INIT_STAGING_NAME
    created = False
    try:
        os.mkdir(staging_root, 0o700)
        created = True
    except FileExistsError:
        pass
    try:
        staging_info = os.lstat(staging_root)
    except OSError as exc:
        raise ValueError(f"run-init staging root is unavailable: {staging_root}") from exc
    if (
        stat.S_ISLNK(staging_info.st_mode)
        or not stat.S_ISDIR(staging_info.st_mode)
        or stat.S_IMODE(staging_info.st_mode) & 0o077
        or staging_root.resolve(strict=True) != staging_root
    ):
        raise ValueError(
            f"run-init staging root must be a private real directory: {staging_root}"
        )
    if created:
        try:
            _fsync_directory(expected_researcher)
        except OSError as exc:
            raise DurabilityUncertainError(
                f"run-init staging root is visible but parent durability is uncertain: "
                f"{staging_root}"
            ) from exc
    return staging_root


def _remove_staged_run(staged_run_dir: Path, staging_root: Path) -> None:
    """Remove one known unpublished tree without following a substituted link."""

    staged_run_dir = Path(os.path.abspath(staged_run_dir))
    if staged_run_dir.parent != staging_root:
        raise RuntimeError(f"refusing to clean an unconfined staged run: {staged_run_dir}")
    try:
        info = os.lstat(staged_run_dir)
    except FileNotFoundError:
        return
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise RuntimeError(f"refusing to clean a substituted staged run: {staged_run_dir}")
    shutil.rmtree(staged_run_dir)
    _fsync_directory(staging_root)


def require_managed_run_dir(run_dir: Path) -> Path:
    """Return a canonical direct child of the configured research-runs root."""

    runs_root = require_managed_runs_root()
    requested = Path(os.path.abspath(run_dir))
    try:
        info = os.lstat(requested)
    except OSError as exc:
        raise ValueError(f"run directory is unavailable: {run_dir}") from exc
    resolved = requested.resolve(strict=True)
    if (
        stat.S_ISLNK(info.st_mode)
        or not stat.S_ISDIR(info.st_mode)
        or requested != resolved
        or requested.parent != runs_root
    ):
        raise ValueError(f"run directory is outside the managed runs root: {run_dir}")
    return requested


def require_run_path(
    run_dir: Path,
    relative: str,
    *,
    kind: str,
    may_be_missing: bool = False,
) -> Path:
    """Validate a run-local path and every ancestor without following symlinks."""

    managed = require_managed_run_dir(run_dir)
    relative_path = Path(relative)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise ValueError(f"unsafe run-relative path: {relative}")
    candidate = managed / relative_path
    current = managed
    for part in relative_path.parts[:-1]:
        current = current / part
        try:
            info = os.lstat(current)
        except FileNotFoundError as exc:
            raise ValueError(f"required run directory is missing: {current}") from exc
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise ValueError(f"run path ancestor must be a real directory: {current}")
    try:
        info = os.lstat(candidate)
    except FileNotFoundError:
        if may_be_missing:
            return candidate
        raise ValueError(f"required run path is missing: {candidate}") from None
    if stat.S_ISLNK(info.st_mode):
        raise ValueError(f"run path must not be a symlink: {candidate}")
    if kind == "directory" and not stat.S_ISDIR(info.st_mode):
        raise ValueError(f"run path must be a directory: {candidate}")
    if kind == "file" and not stat.S_ISREG(info.st_mode):
        raise ValueError(f"run path must be a regular file: {candidate}")
    if kind == "file" and info.st_nlink != 1:
        raise ValueError(f"run path must have exactly one hard link: {candidate}")
    return candidate


@contextmanager
def run_state_lock(run_dir: Path) -> Iterator[None]:
    """Serialize state transitions for one run using a durable sidecar lock."""

    run_dir = require_managed_run_dir(run_dir)
    lock_path = run_dir / ".run-state.lock"
    try:
        lock_info = os.lstat(lock_path)
    except FileNotFoundError:
        pass
    else:
        if (
            stat.S_ISLNK(lock_info.st_mode)
            or not stat.S_ISREG(lock_info.st_mode)
            or lock_info.st_nlink != 1
        ):
            raise ValueError(f"run-state lock must be a regular file: {lock_path}")
    flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(lock_path, flags, 0o600)
    descriptor_info = os.fstat(descriptor)
    if not stat.S_ISREG(descriptor_info.st_mode) or descriptor_info.st_nlink != 1:
        os.close(descriptor)
        raise ValueError(f"run-state lock must be a single-link regular file: {lock_path}")
    with os.fdopen(descriptor, "a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            held_info = os.fstat(handle.fileno())
            path_info = os.lstat(lock_path)
            if (
                path_info.st_nlink != 1
                or (path_info.st_dev, path_info.st_ino)
                != (held_info.st_dev, held_info.st_ino)
            ):
                raise ValueError(
                    f"run-state lock pathname does not identify the held inode: {lock_path}"
                )
            yield
            try:
                path_info = os.lstat(lock_path)
                held_info = os.fstat(handle.fileno())
                if (
                    path_info.st_nlink != 1
                    or (path_info.st_dev, path_info.st_ino)
                    != (held_info.st_dev, held_info.st_ino)
                ):
                    raise ValueError("lock inode changed")
            except (OSError, ValueError) as exc:
                raise DurabilityUncertainError(
                    f"run-state lock pathname changed during the transition: {lock_path}"
                ) from exc
        except BaseException:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
            raise
        else:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def initial_state(run_dir: Path, title: str, source_url: str | None) -> dict[str, Any]:
    timestamp = utc_now()
    return {
        "run_id": run_dir.name,
        "source_id": "S001",
        "title": title,
        "source_url": source_url or "",
        "current_state": "initialized",
        "close_status": None,
        "close_reason": None,
        "locked_surfaces": LOCKED_SURFACES,
        "editable_surfaces": expected_run_editable_surfaces(run_dir.name),
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
    run_dir = require_managed_run_dir(run_dir)
    path = state_path(run_dir)
    if not path.exists():
        raise FileNotFoundError(f"run state is missing: {path}")
    state = load_json(path)
    if not isinstance(state, dict):
        raise ValueError(f"run state must be an object: {path}")
    errors = validate_state_document(state, expected_run_id=run_dir.name)
    if errors:
        raise ValueError(f"invalid run state {path}: {'; '.join(errors)}")
    return state


def write_state(run_dir: Path, state: dict[str, Any]) -> None:
    run_dir = require_managed_run_dir(run_dir)
    require_run_path(run_dir, "run-state.json", kind="file", may_be_missing=True)
    state["updated_at"] = utc_now()
    errors = validate_state_document(state, expected_run_id=run_dir.name)
    if errors:
        raise ValueError(f"refusing to write invalid run state: {'; '.join(errors)}")
    write_json(state_path(run_dir), state)


def _run_validator(run_dir: Path, *, integrity_only: bool = True) -> RunValidator:
    validator = RunValidator(run_dir, integrity_only=integrity_only)
    validator.root = ROOT
    return validator


def _finding_identity(finding: Any) -> str:
    return f"{finding.path}: {finding.message}"


def claimed_integrity_errors(
    run_dir: Path,
    state: dict[str, Any],
) -> list[str]:
    """Return exact claimed-artifact errors after enforcing state/queue identity."""

    validator = _run_validator(run_dir)
    validated_state = validator.validate_state()
    queue_record = validator.validate_queue()
    validator.validate_source_identity(validated_state, queue_record)
    structural_errors = [
        _finding_identity(finding)
        for finding in validator.findings
        if finding.severity == "error"
    ]
    if structural_errors:
        raise ValueError(
            "run structural integrity validation failed: "
            + "; ".join(structural_errors)
        )
    if validated_state != state:
        raise ValueError("run state changed during integrity validation")
    claimed_findings = validator.validate_claimed_integrity(
        validated_state,
        queue_record,
    )
    return [
        _finding_identity(finding)
        for finding in claimed_findings
        if finding.severity == "error"
    ]


def require_transition(run_dir: Path, state_name: str) -> dict[str, Any]:
    state = load_state(run_dir)
    current_state = state["current_state"]
    if state_name not in LEGAL_STATE_TRANSITIONS[current_state]:
        raise ValueError(f"illegal run-state transition {current_state} -> {state_name}")
    integrity_errors = claimed_integrity_errors(run_dir, state)
    if integrity_errors:
        raise ValueError(
            "run claimed-artifact integrity validation failed: "
            + "; ".join(integrity_errors)
        )
    return state


def require_completed_evaluation(
    run_dir: Path,
    state: dict[str, Any],
) -> tuple[Path, dict[str, Any]]:
    """Validate the candidate evaluation before the evaluated transition."""

    validator = _run_validator(run_dir)
    queue_record = validator.validate_queue()
    validator.validate_source_identity(state, queue_record)
    validator.validate_source_evaluation(state, queue_record)
    errors = [
        _finding_identity(finding)
        for finding in validator.findings
        if finding.severity == "error"
    ]
    if errors or validator.evaluation_path is None or validator.evaluation_data is None:
        raise ValueError(
            "completed evaluation is invalid: "
            + "; ".join(errors or ["validated evaluation was not loaded"])
        )
    return validator.evaluation_path, validator.evaluation_data


def require_completed_proposal(run_dir: Path, state: dict[str, Any]) -> Path:
    """Validate proposal provenance before the proposed transition."""

    validator = _run_validator(run_dir)
    queue_record = validator.validate_queue()
    validator.validate_source_identity(state, queue_record)
    source_status = validator.validate_source_evaluation(state, queue_record)
    validator.validate_proposal(source_status, state, queue_record)
    errors = [
        _finding_identity(finding)
        for finding in validator.findings
        if finding.severity == "error"
    ]
    if errors:
        raise ValueError("skill proposal is invalid: " + "; ".join(errors))
    return require_run_path(run_dir, "proposals/skill-proposal.md", kind="file")


def _commit_loaded_state(
    run_dir: Path,
    state: dict[str, Any],
    state_name: str,
    reason: str,
    evidence: str,
    *,
    state_updates: dict[str, Any] | None = None,
    timestamp: str | None = None,
) -> None:
    if state_updates:
        state.update(state_updates)
    state["current_state"] = state_name
    state.setdefault("state_history", []).append(
        {
            "state": state_name,
            "timestamp": timestamp or utc_now(),
            "reason": reason,
            "evidence": evidence,
        }
    )
    write_state(run_dir, state)


def append_thread_decision(
    run_dir: Path,
    decision: str,
    reason: str,
    evidence: str,
    next_action: str,
) -> bool:
    """Append a confined, non-authoritative note after an authoritative commit."""

    entry = (
        "\n```text\n"
        f"{utc_now()} decision: {decision}\n"
        f"reason: {reason}\n"
        f"evidence: {evidence}\n"
        f"next: {next_action}\n"
        "```\n"
    )
    try:
        thread = require_run_path(run_dir, "THREAD.md", kind="file")
        prior = thread.read_text(encoding="utf-8")
        write_text(thread, prior + entry)
    except (OSError, UnicodeError, ValueError) as exc:
        # A note is not lifecycle authority. Report it without making the
        # successful state commit look retryable to the caller.
        print(f"warning: thread note was not written: {exc}", file=sys.stderr)
        return False
    return True


def create_thread(
    run_dir: Path,
    title: str,
    source_url: str | None,
    *,
    identity_run_dir: Path | None = None,
) -> None:
    identity = identity_run_dir or run_dir
    identity_relative = run_relative(identity)
    thread = f"""# Research Thread: {identity.name}

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

- `{identity_relative}/sources/`
- `{identity_relative}/proposals/`
- `{identity_relative}/reports/`

## Source Queue

| ID | Source | Status | Next Action |
| --- | --- | --- | --- |
| S001 | {source_url or 'TBD'} | discovered | evaluate |

## Decisions

```text
T+00:00 decision: run initialized
reason: file-based research loop created durable state
evidence: {identity_relative}
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
    write_text(run_dir / "THREAD.md", thread)


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
    proposal = proposal.replace(
        "- Retrieval status:",
        f"- Retrieval status: {'partial' if source_url else 'failed'}",
    )
    proposal = proposal.replace("- Decision: APPROVE / HUMAN_REVIEW / REJECT", "- Decision: HUMAN_REVIEW")
    write_text(run_dir / "proposals" / "skill-proposal.md", proposal)
    write_text(
        run_dir / "proposals" / "mechanism-proposal.jsonl",
        (RESEARCHER / "templates" / "mechanism-proposal.jsonl").read_text(encoding="utf-8"),
    )


def _read_staged_text(path: Path) -> str:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ValueError(f"staged artifact must be a single-link regular file: {path}")
        with os.fdopen(descriptor, "r", encoding="utf-8") as handle:
            descriptor = -1
            return handle.read()
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def validate_and_fsync_staged_run(
    staged_run_dir: Path,
    final_run_dir: Path,
    staging_root: Path,
    runs_root: Path,
) -> None:
    """Validate a complete initialized tree before its single publish rename."""

    staged_run_dir = Path(os.path.abspath(staged_run_dir))
    final_run_dir = Path(os.path.abspath(final_run_dir))
    if staged_run_dir.parent != staging_root or final_run_dir.parent != runs_root:
        raise ValueError("staged and final run paths must remain in their managed roots")

    observed_directories: set[str] = set()
    observed_files: set[str] = set()
    directories_to_sync: list[Path] = []
    for current_raw, directory_names, file_names in os.walk(
        staged_run_dir,
        topdown=True,
        followlinks=False,
    ):
        current = Path(current_raw)
        current_info = os.lstat(current)
        if stat.S_ISLNK(current_info.st_mode) or not stat.S_ISDIR(current_info.st_mode):
            raise ValueError(f"staged run path must be a real directory: {current}")
        directories_to_sync.append(current)
        for name in directory_names:
            candidate = current / name
            info = os.lstat(candidate)
            if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
                raise ValueError(f"staged run directory is invalid: {candidate}")
            observed_directories.add(str(candidate.relative_to(staged_run_dir)))
        for name in file_names:
            candidate = current / name
            info = os.lstat(candidate)
            if (
                stat.S_ISLNK(info.st_mode)
                or not stat.S_ISREG(info.st_mode)
                or info.st_nlink != 1
                or info.st_size <= 0
            ):
                raise ValueError(f"staged run artifact is invalid: {candidate}")
            observed_files.add(str(candidate.relative_to(staged_run_dir)))
            descriptor = os.open(
                candidate,
                os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
            )
            try:
                opened = os.fstat(descriptor)
                if (
                    not stat.S_ISREG(opened.st_mode)
                    or opened.st_nlink != 1
                    or (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino)
                ):
                    raise ValueError(f"staged run artifact changed during validation: {candidate}")
                os.fsync(descriptor)
            finally:
                os.close(descriptor)

    if observed_directories != INITIAL_RUN_DIRECTORIES:
        raise ValueError(
            "staged run directory scaffold differs from the required initialized scaffold"
        )
    if observed_files != INITIAL_RUN_FILES:
        raise ValueError(
            "staged run file scaffold differs from the required initialized scaffold"
        )

    state_file = staged_run_dir / "run-state.json"
    try:
        state = strict_json_loads(_read_staged_text(state_file))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"staged run state is unreadable: {state_file}") from exc
    if not isinstance(state, dict):
        raise ValueError("staged run state must be an object")
    state_errors = validate_state_document(state, expected_run_id=final_run_dir.name)
    if state_errors:
        raise ValueError(f"staged run state is invalid: {'; '.join(state_errors)}")
    final_relative = run_relative(final_run_dir)
    expected_editable = expected_run_editable_surfaces(final_run_dir.name)
    if state.get("editable_surfaces") != expected_editable:
        raise ValueError("staged run state does not embed the final editable surfaces")

    queue_file = staged_run_dir / "sources" / "queue.jsonl"
    queue_lines = [
        line
        for line in _read_staged_text(queue_file).splitlines()
        if line.strip()
    ]
    if len(queue_lines) != 1:
        raise ValueError("staged source queue must contain exactly one record")
    try:
        queue = strict_json_loads(queue_lines[0])
    except (json.JSONDecodeError, ValueError) as exc:
        raise ValueError("staged source queue is invalid JSONL") from exc
    if not isinstance(queue, dict) or any(
        queue.get(queue_key) != state.get(state_key)
        for queue_key, state_key in (
            ("id", "source_id"),
            ("title", "title"),
            ("url", "source_url"),
        )
    ):
        raise ValueError("staged source queue does not match final run identity")
    expected_retrieval_status = "partial" if state["source_url"] else "failed"
    if (
        not isinstance(queue.get("author_or_org"), str)
        or queue.get("source_type")
        not in {
            "paper",
            "engineering_blog",
            "documentation",
            "benchmark",
            "code",
            "talk",
            "other",
        }
        or queue.get("retrieval_status") != expected_retrieval_status
        or not isinstance(queue.get("candidate_reason"), str)
        or parse_utc_datetime(queue.get("created_at")) is None
    ):
        raise ValueError("staged source queue violates the initialized queue contract")

    thread = _read_staged_text(staged_run_dir / "THREAD.md")
    if (
        f"# Research Thread: {final_run_dir.name}" not in thread
        or f"evidence: {final_relative}" not in thread
        or staged_run_dir.name in thread
    ):
        raise ValueError("staged thread does not exclusively embed the final run identity")

    for directory in sorted(
        directories_to_sync,
        key=lambda path: len(path.parts),
        reverse=True,
    ):
        _fsync_directory(directory)
    _fsync_directory(staging_root)


def source_queue_record(
    run_dir: Path, *, state: dict[str, Any] | None = None
) -> tuple[Path, dict[str, Any]]:
    queue = require_run_path(run_dir, "sources/queue.jsonl", kind="file")
    records: list[Any] = []
    for line_number, line in enumerate(
        queue.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        try:
            records.append(strict_json_loads(line))
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValueError(
                f"source queue line {line_number} is invalid JSON: {exc}"
            ) from exc
    if len(records) != 1 or not isinstance(records[0], dict):
        raise ValueError("source queue must contain exactly one object record")
    record = records[0]
    for key in ("id", "title", "url"):
        if not isinstance(record.get(key), str):
            raise ValueError(f"source queue {key} must be a string")
    state_document = state if state is not None else load_state(run_dir)
    expected = {
        "id": state_document.get("source_id", "S001"),
        "title": state_document.get("title"),
        "url": state_document.get("source_url"),
    }
    for key, value in expected.items():
        if record.get(key) != value:
            raise ValueError(f"source queue {key} differs from run state")
    return queue, record


def update_queue(
    run_dir: Path, *, state: dict[str, Any] | None = None, **updates: Any
) -> None:
    queue, record = source_queue_record(run_dir, state=state)
    record.update(updates)
    write_jsonl(queue, [record])


def proposal_file(run_dir: Path) -> Path:
    return require_run_path(run_dir, "proposals/skill-proposal.md", kind="file")


def proposal_with_novelty_result(
    proposal: str,
    result: dict[str, Any],
    human_review_rationale: str,
) -> str:
    """Project deterministic novelty fields into the proposal exactly once."""

    verdict = result.get("verdict")
    max_mechanism_score = result.get("max_mechanism_score")
    overlaps = result.get("top_mechanism_overlaps")
    if not isinstance(verdict, str) or type(max_mechanism_score) not in {int, float}:
        raise ValueError("novelty result is missing its verdict or mechanism score")
    if not isinstance(overlaps, list) or any(
        not isinstance(item, dict)
        or not isinstance(item.get("mechanism_id"), str)
        or not item["mechanism_id"]
        for item in overlaps
    ):
        raise ValueError("novelty result top_mechanism_overlaps is invalid")
    replacements = {
        "Verdict": verdict,
        "Max mechanism overlap": str(max_mechanism_score),
        "Top mechanism overlaps": ", ".join(
            item["mechanism_id"] for item in overlaps
        ) or "none",
        "Human-review rationale": human_review_rationale.strip()
        if verdict != "pass"
        else "none",
    }
    rendered = proposal
    for label, value in replacements.items():
        rendered, count = re.subn(
            rf"^- {re.escape(label)}:.*$",
            f"- {label}: {value}",
            rendered,
            flags=re.MULTILINE,
        )
        if count != 1:
            raise ValueError(f"proposal must contain exactly one - {label}: field")
    return rendered


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _snapshot_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None


def _restore_text(path: Path, prior: str | None) -> None:
    if prior is not None:
        write_text(path, prior)
        return
    try:
        info = os.lstat(path)
    except FileNotFoundError:
        return
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise RuntimeError(f"cannot safely roll back non-regular artifact: {path}")
    path.unlink()
    _fsync_directory(path.parent)


def _visible_state_matches(
    run_dir: Path,
    state_name: str,
    updates: dict[str, Any] | None = None,
) -> bool:
    try:
        visible = load_json(state_path(run_dir))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False
    if not isinstance(visible, dict) or visible.get("current_state") != state_name:
        return False
    return all(visible.get(key) == value for key, value in (updates or {}).items())


def publish_evidence_file(source: Path, raw_dir: Path) -> tuple[Path, str, int]:
    """Publish exact manually supplied bytes under a revalidated content address."""

    resolved = source.resolve(strict=True)
    if not resolved.is_file():
        raise ValueError(f"evidence attachment must be a regular file: {source}")
    raw_dir.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".evidence-",
        suffix=".tmp",
        dir=str(raw_dir),
    )
    temporary = Path(temporary_name)
    digest = hashlib.sha256()
    try:
        with os.fdopen(descriptor, "wb") as output_handle, resolved.open(
            "rb"
        ) as input_handle:
            copied_size = 0
            while chunk := input_handle.read(1024 * 1024):
                copied_size += len(chunk)
                if copied_size > MAX_EVIDENCE_FILE_BYTES:
                    raise ValueError(
                        f"evidence attachment exceeds {MAX_EVIDENCE_FILE_BYTES} bytes: {source}"
                    )
                digest.update(chunk)
                output_handle.write(chunk)
            if copied_size == 0:
                raise ValueError(f"evidence attachment must not be empty: {source}")
            output_handle.flush()
            os.fsync(output_handle.fileno())
        hexdigest = digest.hexdigest()
        target = raw_dir / hexdigest
        published_size = temporary.stat().st_size
        published_new = False
        try:
            os.link(temporary, target)
        except FileExistsError:
            pass
        else:
            published_new = True
            _fsync_directory(raw_dir)
        temporary.unlink()
        info = os.lstat(target)
        if (
            stat.S_ISLNK(info.st_mode)
            or not stat.S_ISREG(info.st_mode)
            or info.st_nlink != 1
            or info.st_size != published_size
        ):
            raise RuntimeError(
                f"evidence target is not a single-link regular file: {target}"
            )
        if _sha256_file(target) != hexdigest:
            raise RuntimeError(
                f"content-addressed evidence collision or corruption: {target}"
            )
        os.chmod(target, 0o400, follow_symlinks=False)
        if published_new:
            _fsync_directory(raw_dir)
        return target, hexdigest, info.st_size
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def validate_manual_evidence(
    run_dir: Path,
    *,
    state: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Rehash and validate the complete content-addressed evidence directory."""

    run_dir = require_managed_run_dir(run_dir)
    queue_path = require_run_path(run_dir, "sources/queue.jsonl", kind="file")
    raw_dir = require_run_path(run_dir, "sources/evidence/raw", kind="directory")
    records = [
        strict_json_loads(line)
        for line in queue_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(records) != 1 or not isinstance(records[0], dict):
        raise ValueError("source queue must contain exactly one object record")
    record = records[0]
    paths = record.get("raw_evidence")
    digests = record.get("raw_evidence_sha256")
    sizes = record.get("raw_evidence_size_bytes")
    if not (
        isinstance(paths, list)
        and isinstance(digests, list)
        and isinstance(sizes, list)
        and paths
        and len(paths) == len(digests) == len(sizes)
    ):
        raise ValueError("retrieved source queue has an incomplete evidence manifest")
    if len(paths) > MAX_EVIDENCE_FILES:
        raise ValueError("retrieved source queue exceeds the evidence file-count limit")

    manifest: list[dict[str, Any]] = []
    expected_files: set[Path] = set()
    batch_size = 0
    for index, (path_value, digest_value, size_value) in enumerate(
        zip(paths, digests, sizes)
    ):
        if not isinstance(path_value, str):
            raise ValueError(f"raw_evidence[{index}] must be a string")
        if not (
            isinstance(digest_value, str)
            and re.fullmatch(r"sha256:[0-9a-f]{64}", digest_value)
        ):
            raise ValueError(f"raw_evidence_sha256[{index}] is invalid")
        if (
            type(size_value) is not int
            or size_value <= 0
            or size_value > MAX_EVIDENCE_FILE_BYTES
        ):
            raise ValueError(f"raw_evidence_size_bytes[{index}] is invalid")
        batch_size += size_value
        if batch_size > MAX_EVIDENCE_BATCH_BYTES:
            raise ValueError("retrieved source queue exceeds the evidence batch-size limit")
        hexdigest = digest_value.removeprefix("sha256:")
        expected = raw_dir / hexdigest
        lexical = Path(os.path.abspath(ROOT / path_value))
        if lexical != expected:
            raise ValueError(f"evidence path is not its exact content address: {path_value}")
        candidate = require_run_path(
            run_dir,
            str(expected.relative_to(run_dir)),
            kind="file",
        )
        info = os.lstat(candidate)
        if info.st_nlink != 1:
            raise ValueError(f"evidence file must have one hard link: {path_value}")
        if info.st_mode & 0o222:
            raise ValueError(f"evidence file must not have write bits: {path_value}")
        if info.st_size != size_value or _sha256_file(candidate) != hexdigest:
            raise ValueError(f"evidence bytes do not match manifest: {path_value}")
        expected_files.add(candidate)
        manifest.append(
            {"path": path_value, "sha256": digest_value, "size_bytes": size_value}
        )

    observed_files = set(raw_dir.iterdir())
    if observed_files != expected_files:
        raise ValueError("evidence directory contains missing or unmanifested entries")
    state_document = state if state is not None else load_json(state_path(run_dir))
    if state_document.get("retrieval_evidence") != manifest:
        raise ValueError("run state and source queue evidence manifests differ")
    return manifest


def retrieve_source(args: argparse.Namespace) -> int:
    run_dir = require_managed_run_dir(args.run_dir)
    sources = list(args.file or [])
    if not sources:
        raise ValueError("at least one --file evidence attachment is required")
    if len(sources) > MAX_EVIDENCE_FILES:
        raise ValueError(
            f"at most {MAX_EVIDENCE_FILES} evidence attachments are allowed"
        )
    raw_dir = require_run_path(
        run_dir, "sources/evidence/raw", kind="directory"
    )
    queue_path = require_run_path(run_dir, "sources/queue.jsonl", kind="file")
    copied: list[str] = []
    digests: list[str] = []
    sizes: list[int] = []
    with run_state_lock(run_dir):
        state = require_transition(run_dir, "retrieved")
        source_queue_record(run_dir, state=state)
        prior_queue = queue_path.read_text(encoding="utf-8")
        prior_entries = set(raw_dir.iterdir())
        manifest: list[dict[str, Any]] = []
        try:
            seen_digests: set[str] = set()
            for source in sources:
                target, digest, size = publish_evidence_file(source, raw_dir)
                if digest in seen_digests:
                    continue
                seen_digests.add(digest)
                copied.append(str(target.relative_to(ROOT)))
                digests.append(f"sha256:{digest}")
                sizes.append(size)
                if sum(sizes) > MAX_EVIDENCE_BATCH_BYTES:
                    raise ValueError(
                        f"evidence batch exceeds {MAX_EVIDENCE_BATCH_BYTES} bytes"
                    )
            manifest = [
                {"path": path, "sha256": digest, "size_bytes": size}
                for path, digest, size in zip(copied, digests, sizes)
            ]
            expected_entries = {ROOT / entry["path"] for entry in manifest}
            if set(raw_dir.iterdir()) != expected_entries:
                raise ValueError(
                    "evidence directory contains pre-existing or incomplete entries"
                )
            update_queue(
                run_dir,
                state=state,
                retrieval_status="retrieved",
                retrieved_at=utc_now(),
                raw_evidence=copied,
                raw_evidence_sha256=digests,
                raw_evidence_size_bytes=sizes,
                retrieval_notes=args.notes,
            )
            evidence = ", ".join(copied)
            _commit_loaded_state(
                run_dir,
                state,
                "retrieved",
                "source evidence retrieved",
                evidence,
                state_updates={"retrieval_evidence": manifest},
            )
        except BaseException:
            try:
                visible_state = load_json(state_path(run_dir))
            except (OSError, UnicodeError, json.JSONDecodeError):
                visible_state = {}
            committed = (
                visible_state.get("current_state") == "retrieved"
                and visible_state.get("retrieval_evidence") == manifest
            )
            if not committed:
                try:
                    write_text(queue_path, prior_queue)
                    for entry in set(raw_dir.iterdir()) - prior_entries:
                        os.chmod(entry, 0o600, follow_symlinks=False)
                        entry.unlink()
                    _fsync_directory(raw_dir)
                except BaseException as cleanup_error:
                    raise RuntimeError(
                        "retrieval rollback failed; manual reconciliation is required"
                    ) from cleanup_error
            raise
    append_thread_decision(
        run_dir,
        "state -> retrieved",
        "source evidence retrieved",
        evidence,
        "continue run",
    )
    return 0


def mark_evaluated(args: argparse.Namespace) -> int:
    run_dir = require_managed_run_dir(args.run_dir)
    with run_state_lock(run_dir):
        state = require_transition(run_dir, "evaluated")
        eval_path, data = require_completed_evaluation(run_dir, state)
        queue_path = require_run_path(run_dir, "sources/queue.jsonl", kind="file")
        prior_queue = _snapshot_text(queue_path)
        try:
            update_queue(
                run_dir,
                retrieval_status=data.get("source", {}).get(
                    "retrieval_status", "retrieved"
                ),
                evaluation_file=str(eval_path.relative_to(ROOT)),
                evaluation_decision=data.get("decision", {}).get("verdict", ""),
            )
            evidence = str(eval_path.relative_to(ROOT))
            _commit_loaded_state(
                run_dir,
                state,
                "evaluated",
                "completed source evaluation recorded",
                evidence,
            )
        except BaseException:
            if not _visible_state_matches(run_dir, "evaluated"):
                try:
                    _restore_text(queue_path, prior_queue)
                except BaseException as cleanup_error:
                    raise RuntimeError(
                        "evaluation rollback failed; manual reconciliation is required"
                    ) from cleanup_error
            raise
    append_thread_decision(
        run_dir,
        "state -> evaluated",
        "completed source evaluation recorded",
        evidence,
        "continue run",
    )
    return 0


def mark_proposed(args: argparse.Namespace) -> int:
    run_dir = require_managed_run_dir(args.run_dir)
    with run_state_lock(run_dir):
        state = require_transition(run_dir, "proposed")
        path = require_completed_proposal(run_dir, state)
        evidence = str(path.relative_to(ROOT))
        _commit_loaded_state(
            run_dir,
            state,
            "proposed",
            "skill proposal recorded",
            evidence,
        )
    append_thread_decision(
        run_dir,
        "state -> proposed",
        "skill proposal recorded",
        evidence,
        "continue run",
    )
    return 0


def run_novelty(args: argparse.Namespace) -> int:
    run_dir = require_managed_run_dir(args.run_dir)
    require_transition(run_dir, "novelty_checked")
    path = proposal_file(run_dir)
    require_run_path(run_dir, "reports", kind="directory")
    result_path = require_run_path(
        run_dir, "reports/novelty-result.json", kind="file", may_be_missing=True
    )
    cmd = [
        sys.executable,
        str(RESEARCHER / "scripts" / "novelty_check.py"),
        "--file",
        str(path),
        "--json",
    ]
    completed = run_local_checker(cmd)
    result: dict[str, Any]
    try:
        parsed = strict_json_loads(completed.stdout)
    except (json.JSONDecodeError, ValueError):
        parsed = None
    if isinstance(parsed, dict):
        result = parsed
    else:
        result = {
            "verdict": "error",
            "error": completed.stderr or "novelty_check.py produced no JSON object",
        }
    if args.human_review_rationale:
        result["human_review_rationale"] = args.human_review_rationale
    verdict = result.get("verdict")
    expected_exit = 0 if verdict == "pass" else 2 if verdict in {
        "human_review",
        "likely_duplicate",
    } else None
    can_advance = (
        expected_exit is not None
        and completed.returncode == expected_exit
        and (verdict == "pass" or bool(args.human_review_rationale.strip()))
    )
    with run_state_lock(run_dir):
        state = require_transition(run_dir, "novelty_checked")
        prior_result = _snapshot_text(result_path)
        prior_proposal = _snapshot_text(path)
        try:
            write_json(result_path, result)
            if can_advance:
                proposal = proposal_with_novelty_result(
                    path.read_text(encoding="utf-8"),
                    result,
                    args.human_review_rationale,
                )
                write_text(path, proposal)
                validator = _run_validator(run_dir)
                queue_record = validator.validate_queue()
                validator.validate_source_identity(state, queue_record)
                source_status = validator.validate_source_evaluation(
                    state,
                    queue_record,
                )
                novelty_data = validator.validate_novelty()
                validator.validate_proposal(
                    source_status,
                    state,
                    queue_record,
                    novelty_data,
                )
                postcondition_errors = [
                    _finding_identity(finding)
                    for finding in validator.findings
                    if finding.severity == "error"
                ]
                if postcondition_errors:
                    raise ValueError(
                        "novelty transition postcondition failed: "
                        + "; ".join(postcondition_errors)
                    )
                evidence = str(result_path.relative_to(ROOT))
                _commit_loaded_state(
                    run_dir,
                    state,
                    "novelty_checked",
                    "novelty result recorded",
                    evidence,
                )
        except BaseException:
            if can_advance and not _visible_state_matches(run_dir, "novelty_checked"):
                try:
                    _restore_text(result_path, prior_result)
                    _restore_text(path, prior_proposal)
                except BaseException as cleanup_error:
                    raise RuntimeError(
                        "novelty rollback failed; manual reconciliation is required"
                    ) from cleanup_error
            raise
    if not can_advance:
        return completed.returncode or 1
    append_thread_decision(
        run_dir,
        "state -> novelty_checked",
        "novelty result recorded",
        evidence,
        "continue run",
    )
    return 0


def run_run_validator(run_dir: Path) -> int:
    run_dir = require_managed_run_dir(run_dir)
    require_transition(run_dir, "validated")
    require_run_path(run_dir, "reports", kind="directory")
    report_json = require_run_path(
        run_dir, "reports/run-readiness.json", kind="file", may_be_missing=True
    )
    report_md = require_run_path(
        run_dir, "reports/run-readiness.md", kind="file", may_be_missing=True
    )
    cmd = [
        sys.executable,
        str(RESEARCHER / "scripts" / "validate_run.py"),
        "--run-dir",
        str(run_dir),
        "--json",
    ]
    completed = run_local_checker(cmd)
    parsed: dict[str, Any] | None = None
    try:
        candidate = strict_json_loads(completed.stdout)
        if isinstance(candidate, dict):
            parsed = candidate
    except (json.JSONDecodeError, ValueError):
        pass
    validation_passed = (
        completed.returncode == 0
        and parsed is not None
        and parsed.get("ok") is True
    )
    with run_state_lock(run_dir):
        state = require_transition(run_dir, "validated")
        prior_reports = {
            report_json: _snapshot_text(report_json),
            report_md: _snapshot_text(report_md),
        }
        try:
            if parsed is not None:
                write_json(report_json, parsed)
                summary = parsed.get("summary", {})
                text = (
                    "# Run Readiness Report\n\n"
                    f"Run validation {'passed' if validation_passed else 'failed'}: "
                    f"{summary.get('errors', 0)} errors, "
                    f"{summary.get('warnings', 0)} warnings.\n"
                )
            else:
                error = completed.stderr or "validate_run.py produced no JSON object"
                write_json(report_json, {"ok": False, "error": error})
                text = (
                    "# Run Readiness Report\n\n"
                    f"Validation command failed.\n\n{error}\n"
                )
            write_text(report_md, text)
            if validation_passed:
                evidence = str(report_json.relative_to(ROOT))
                _commit_loaded_state(
                    run_dir,
                    state,
                    "validated",
                    "run readiness validation passed",
                    evidence,
                )
        except BaseException:
            if validation_passed and not _visible_state_matches(run_dir, "validated"):
                try:
                    for artifact, prior in prior_reports.items():
                        _restore_text(artifact, prior)
                except BaseException as cleanup_error:
                    raise RuntimeError(
                        "validation rollback failed; manual reconciliation is required"
                    ) from cleanup_error
            raise
    if validation_passed:
        append_thread_decision(
            run_dir,
            "state -> validated",
            "run readiness validation passed",
            evidence,
            "continue run",
        )
        return 0
    return completed.returncode or 1


def run_validator(run_dir: Path) -> int:
    run_dir = require_managed_run_dir(run_dir)
    require_run_path(run_dir, "reports", kind="directory")
    report_json = require_run_path(
        run_dir, "reports/validation-report.json", kind="file", may_be_missing=True
    )
    report_md = require_run_path(
        run_dir, "reports/validation-report.md", kind="file", may_be_missing=True
    )
    cmd = [
        sys.executable,
        str(RESEARCHER / "scripts" / "validate_repo.py"),
        "--strict",
        "--root",
        str(ROOT),
        "--json",
    ]
    completed = run_local_checker(cmd)
    if completed.stdout:
        write_text(report_json, completed.stdout)
    else:
        write_text(
            report_json,
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
        )
    summary = "Validation command exited with code " + str(completed.returncode)
    if completed.stdout:
        try:
            data = strict_json_loads(completed.stdout)
            summary = (
                f"Validation {'passed' if data.get('ok') else 'failed'}: "
                f"{data.get('summary', {}).get('errors', 0)} errors, "
                f"{data.get('summary', {}).get('warnings', 0)} warnings."
            )
        except (json.JSONDecodeError, ValueError):
            pass
    write_text(report_md, f"# Validation Report\n\n{summary}\n")
    return completed.returncode


def write_pr_readiness(args: argparse.Namespace) -> int:
    for field in ("summary", "test_plan", "risks"):
        value = getattr(args, field, None)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"--{field.replace('_', '-')} must contain non-whitespace text")
    run_dir = require_managed_run_dir(args.run_dir)
    require_run_path(run_dir, "reports", kind="directory")
    path = require_run_path(
        run_dir, "reports/pr-readiness.md", kind="file", may_be_missing=True
    )
    text = f"""# PR Readiness Notes

## Summary

{args.summary}

## Test Plan

{args.test_plan}

## Risks

{args.risks}

Merge and push require explicit human approval.
"""
    with run_state_lock(run_dir):
        state = require_transition(run_dir, "pr_ready")
        prior = _snapshot_text(path)
        try:
            write_text(path, text)
            evidence = str(path.relative_to(ROOT))
            _commit_loaded_state(
                run_dir,
                state,
                "pr_ready",
                "PR readiness notes recorded",
                evidence,
            )
        except BaseException:
            if not _visible_state_matches(run_dir, "pr_ready"):
                try:
                    _restore_text(path, prior)
                except BaseException as cleanup_error:
                    raise RuntimeError(
                        "PR-readiness rollback failed; manual reconciliation is required"
                    ) from cleanup_error
            raise
    append_thread_decision(
        run_dir,
        "state -> pr_ready",
        "PR readiness notes recorded",
        evidence,
        "continue run",
    )
    return 0


def close_run(args: argparse.Namespace) -> int:
    if args.status not in VALID_CLOSE_STATUS:
        raise ValueError(f"status must be one of {sorted(VALID_CLOSE_STATUS)}")
    if not isinstance(args.reason, str) or not args.reason.strip():
        raise ValueError("closure reason is required")
    if args.status == "accepted":
        raise ValueError(
            "accepted closure is disabled in the legacy loop; production acceptance "
            "requires the specification-owned freeze and authority pipeline"
        )
    run_dir = require_managed_run_dir(args.run_dir)
    require_run_path(run_dir, "reports", kind="directory")
    path = require_run_path(
        run_dir, "reports/closure.json", kind="file", may_be_missing=True
    )
    with run_state_lock(run_dir):
        state = load_state(run_dir)
        current_state = state["current_state"]
        if "closed" not in LEGAL_STATE_TRANSITIONS[current_state]:
            raise ValueError(f"illegal run-state transition {current_state} -> closed")
        integrity_errors = claimed_integrity_errors(run_dir, state)
        timestamp = utc_now()
        closure = {
            "status": args.status,
            "reason": args.reason,
            "closed_at": timestamp,
            "reviewed_by": args.reviewed_by,
            "integrity_errors": integrity_errors,
        }
        prior = _snapshot_text(path)
        state_updates = {
            "close_status": args.status,
            "close_reason": args.reason,
        }
        try:
            write_json(path, closure)
            evidence = str(path.relative_to(ROOT))
            _commit_loaded_state(
                run_dir,
                state,
                "closed",
                args.reason,
                evidence,
                state_updates=state_updates,
                timestamp=timestamp,
            )
        except BaseException:
            if not _visible_state_matches(run_dir, "closed", state_updates):
                try:
                    _restore_text(path, prior)
                except BaseException as cleanup_error:
                    raise RuntimeError(
                        "closure rollback failed; manual reconciliation is required"
                    ) from cleanup_error
            raise
    append_thread_decision(run_dir, f"closed as {args.status}", args.reason, str(path.relative_to(ROOT)), "stop run")
    return 0


def promote_mechanisms(args: argparse.Namespace) -> int:
    require_managed_run_dir(args.run_dir)
    raise ValueError(
        "legacy mechanism promotion is disabled; reviewed promotion requires the "
        "specification-owned journal, freeze receipt, and transactional registry authority"
    )


def create_run(args: argparse.Namespace) -> Path:
    source_url = normalize_source_url(args.url) if args.url else ""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    runs_root = require_managed_runs_root()
    run_dir = runs_root / f"{timestamp}-{slugify(args.title)}"
    if _path_lexists(run_dir):
        raise FileExistsError(f"run already exists: {run_dir}")
    staging_root = require_run_init_staging_root(runs_root)
    staged_run_dir = staging_root / f".{run_dir.name}.{uuid4().hex}.tmp"
    published = False
    os.mkdir(staged_run_dir, 0o700)
    try:
        for relative in sorted(
            INITIAL_RUN_DIRECTORIES,
            key=lambda value: (len(Path(value).parts), value),
        ):
            os.mkdir(staged_run_dir / relative, 0o700)

        source_record = {
            "id": "S001",
            "url": source_url,
            "title": args.title,
            "author_or_org": args.author_or_org,
            "source_type": args.source_type,
            "retrieval_status": "partial" if source_url else "failed",
            "candidate_reason": args.reason,
            "created_at": utc_now(),
        }
        write_jsonl(staged_run_dir / "sources" / "queue.jsonl", [source_record])
        create_thread(
            staged_run_dir,
            args.title,
            source_url,
            identity_run_dir=run_dir,
        )
        state = initial_state(run_dir, args.title, source_url)
        state_errors = validate_state_document(state, expected_run_id=run_dir.name)
        if state_errors:
            raise ValueError(
                f"refusing to stage invalid initialized state: {'; '.join(state_errors)}"
            )
        write_json(staged_run_dir / "run-state.json", state)
        create_source_evaluation(
            staged_run_dir,
            args.title,
            source_url,
            args.author_or_org,
            args.source_type,
        )
        create_skill_proposal(staged_run_dir, args.title, source_url)
        validate_and_fsync_staged_run(
            staged_run_dir,
            run_dir,
            staging_root,
            runs_root,
        )
        if _path_lexists(run_dir):
            raise FileExistsError(f"run appeared before publication: {run_dir}")
        os.rename(staged_run_dir, run_dir)
        published = True
        try:
            _fsync_directory(runs_root)
        except OSError as exc:
            raise DurabilityUncertainError(
                f"run is visible but runs-root durability is uncertain: {run_dir}"
            ) from exc
    except BaseException:
        if not published:
            _remove_staged_run(staged_run_dir, staging_root)
        raise

    structural_report = _run_validator(run_dir, integrity_only=True).run()
    if not structural_report["ok"]:
        messages = "; ".join(
            f"{finding['path']}: {finding['message']}"
            for finding in structural_report["findings"]
            if finding["severity"] == "error"
        )
        raise RuntimeError(
            f"published initialized run failed structural validation: {messages}"
        )
    if run_validator(run_dir) != 0:
        raise RuntimeError(
            f"run published but failed deterministic validation; inspect {run_dir / 'reports'}"
        )
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
    retrieve.add_argument(
        "--file",
        type=Path,
        action="append",
        required=True,
        help="raw evidence file to publish immutably into the run (repeatable)",
    )
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
    close.add_argument("--status", required=True, choices=sorted(WRITABLE_CLOSE_STATUS))
    close.add_argument("--reason", required=True)
    close.add_argument("--reviewed-by", default="")

    promote = sub.add_parser(
        "promote-mechanisms", help="fail closed; legacy promotion is disabled"
    )
    promote.add_argument("--run-dir", type=Path, required=True)
    promote.add_argument("--reviewed-by", required=True)

    args = parser.parse_args()
    if args.command == "init":
        run_dir = create_run(args)
        print(run_dir.relative_to(ROOT))
        return 0
    if args.command == "validate":
        if args.run_dir:
            return run_validator(args.run_dir)
        cmd = [sys.executable, str(RESEARCHER / "scripts" / "validate_repo.py"), "--strict"]
        completed = run_local_checker(cmd)
        if completed.stdout:
            print(completed.stdout, end="")
        if completed.stderr:
            print(completed.stderr, end="\n" if not completed.stderr.endswith("\n") else "", file=sys.stderr)
        return completed.returncode
    if args.command == "retrieve":
        return retrieve_source(args)
    if args.command == "evaluate":
        return mark_evaluated(args)
    if args.command == "propose":
        return mark_proposed(args)
    if args.command == "novelty":
        return run_novelty(args)
    if args.command == "validate-run":
        return run_run_validator(args.run_dir)
    if args.command == "pr-ready":
        return write_pr_readiness(args)
    if args.command == "close":
        return close_run(args)
    if args.command == "promote-mechanisms":
        return promote_mechanisms(args)
    return 1


if __name__ == "__main__":
    sys.exit(main())
