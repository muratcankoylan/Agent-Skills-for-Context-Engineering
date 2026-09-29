#!/usr/bin/env python3
"""Validate publish readiness for a single research run.

This complements validate_repo.py. Repo validation answers whether the corpus is
structurally healthy; run validation answers whether one run is ready to produce
reviewable corpus changes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import stat
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import SplitResult, urlsplit, urlunsplit


ROOT = Path(__file__).resolve().parents[2]
RUN_STATES = (
    "initialized",
    "retrieved",
    "evaluated",
    "proposed",
    "novelty_checked",
    "validated",
    "pr_ready",
    "closed",
)
VALID_STATES = frozenset(RUN_STATES)

# Ordinary progress is linear. A run may instead close from any active state so
# rejected, abandoned, and reference-only work can terminate without fabricating
# intermediate evidence. Closed runs are terminal.
LEGAL_STATE_TRANSITIONS = {
    state: frozenset({RUN_STATES[index + 1], "closed"})
    for index, state in enumerate(RUN_STATES[:-2])
}
LEGAL_STATE_TRANSITIONS["pr_ready"] = frozenset({"closed"})
LEGAL_STATE_TRANSITIONS["closed"] = frozenset()
VALID_CLOSE_STATUS = {"accepted", "rejected", "reference-only", "abandoned"}
MAX_EVIDENCE_FILES = 32
MAX_EVIDENCE_FILE_BYTES = 64 * 1024 * 1024
MAX_EVIDENCE_BATCH_BYTES = 256 * 1024 * 1024
MAX_RUNTIME_CLOCK_SKEW = timedelta(minutes=5)
LEGACY_REFERENCE_RUN_ID = "20260515-035228-executable-autonomous-research-frameworks"
REQUIRED_SOURCE_EVAL_KEYS = {
    "evaluation_id",
    "timestamp",
    "source",
    "gatekeeper",
    "scoring",
    "decision",
    "extraction",
}
CANONICAL_LOCKED_SURFACES = (
    "researcher/rubrics/content-curation.md",
    "researcher/rubrics/skill-change.md",
    "researcher/rubrics/harness-change.md",
    "researcher/mechanisms/registry.jsonl",
    ".claude-plugin/marketplace.json",
    ".plugin/plugin.json",
    "researcher/scripts/validate_repo.py",
)
PLACEHOLDER_PATTERNS = [
    r"\[Short Title\]",
    r"Describe the implementable mechanism",
    r"State one of:",
    r'path: ""',
    r'section: ""',
    r'summary: ""',
    r"Verdict: pending",
]


class DuplicateKeyError(ValueError):
    """A durable JSON object contains an ambiguous duplicate member name."""


class NonFiniteJSONNumberError(ValueError):
    """A JSON document contains a non-RFC numeric constant."""


def strict_json_loads(payload: str) -> Any:
    """Parse RFC JSON, rejecting duplicate keys and non-finite constants."""

    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise DuplicateKeyError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def reject_nonfinite(constant: str) -> Any:
        raise NonFiniteJSONNumberError(
            f"non-finite JSON number is not permitted: {constant}"
        )

    return json.loads(
        payload,
        object_pairs_hook=reject_duplicates,
        parse_constant=reject_nonfinite,
    )


def normalize_source_url(url: str) -> str:
    """Return the canonical, credential-free HTTP(S) source identity."""

    stripped = url.strip()
    try:
        parsed = urlsplit(stripped)
        port = parsed.port
    except ValueError as exc:
        raise ValueError("source URL is malformed") from exc
    scheme = parsed.scheme.lower()
    hostname = parsed.hostname
    if scheme not in {"http", "https"} or hostname is None:
        raise ValueError("source URL must be an absolute HTTP(S) URL")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("source URL must not contain credentials")
    try:
        canonical_host = hostname.encode("idna").decode("ascii").lower()
    except UnicodeError as exc:
        raise ValueError("source URL hostname is invalid") from exc
    if ":" in canonical_host:
        canonical_host = f"[{canonical_host}]"
    default_port = (scheme == "http" and port == 80) or (
        scheme == "https" and port == 443
    )
    netloc = canonical_host if port is None or default_port else f"{canonical_host}:{port}"
    normalized = SplitResult(scheme, netloc, parsed.path or "/", parsed.query, "")
    return urlunsplit(normalized)


def parse_utc_datetime(value: object) -> datetime | None:
    """Parse a timezone-aware UTC ISO-8601 timestamp."""

    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        return None
    return parsed


def exact_json_equal(left: Any, right: Any) -> bool:
    """Compare JSON-domain values without Python bool/int aliasing."""

    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(
            exact_json_equal(left[key], right[key]) for key in left
        )
    if isinstance(left, list):
        return len(left) == len(right) and all(
            exact_json_equal(a, b) for a, b in zip(left, right)
        )
    return bool(left == right)


def expected_run_editable_surfaces(run_id: str) -> list[str]:
    base = f"researcher/runs/{run_id}"
    return [
        f"{base}/sources/",
        f"{base}/proposals/",
        f"{base}/reports/",
        f"{base}/logs/",
    ]


def source_evaluation_shape_errors(
    data: dict[str, Any],
    *,
    observed_at: datetime | None = None,
) -> list[str]:
    """Return the deterministic content-curation errors for one evaluation.

    ``validate_repo`` imports this module for the state-history contract, so
    importing its ``Validator`` here would create a circular import. Keep this
    narrow, side-effect-free equivalent available for eventual reuse by both
    validators instead of importing a repository validator through an
    execution-path-dependent module name.
    """

    errors: list[str] = []
    missing = sorted(REQUIRED_SOURCE_EVAL_KEYS - data.keys())
    if missing:
        errors.append(f"source evaluation missing keys: {', '.join(missing)}")
        return errors

    for field in ("evaluation_id", "timestamp"):
        value = data.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{field} must be a non-empty string")
    evaluation_timestamp = parse_utc_datetime(data.get("timestamp"))
    if evaluation_timestamp is None:
        errors.append("timestamp must be a timezone-aware UTC ISO-8601 value")
    elif evaluation_timestamp > (observed_at or datetime.now(timezone.utc)):
        errors.append("timestamp must not postdate evaluation validation")

    source = data.get("source")
    if not isinstance(source, dict):
        errors.append("source must be an object")
        return errors
    source_url = source.get("url")
    if not isinstance(source_url, str) or not source_url.strip():
        errors.append("source.url must be a non-empty string")
    else:
        try:
            normalized_url = normalize_source_url(source_url)
        except ValueError as exc:
            errors.append(str(exc))
        else:
            if source_url != normalized_url:
                errors.append("source.url must use canonical HTTP(S) form")
    if source.get("retrieval_status") not in {"retrieved", "partial", "failed"}:
        errors.append("source.retrieval_status is invalid")
    if source.get("source_type") not in {
        "paper",
        "engineering_blog",
        "documentation",
        "benchmark",
        "code",
        "talk",
        "other",
    }:
        errors.append("source.source_type is invalid")
    if source.get("primary_or_secondary") not in {"primary", "secondary"}:
        errors.append("source.primary_or_secondary is invalid")
    source_title = source.get("title")
    if not isinstance(source_title, str) or not source_title.strip():
        errors.append("source.title must be a non-empty string")
    decision = data.get("decision")
    if not isinstance(decision, dict):
        errors.append("decision must be an object")
        return errors
    retrieval_status = source.get("retrieval_status")
    decision_verdict = decision.get("verdict")
    if retrieval_status == "failed" and decision_verdict != "REJECT":
        errors.append("failed retrieval must reject or reroute before evaluation")
    if retrieval_status != "retrieved" and decision_verdict == "APPROVE":
        errors.append("only retrieved sources may receive APPROVE")

    gatekeeper = data.get("gatekeeper")
    if not isinstance(gatekeeper, dict):
        errors.append("gatekeeper must be an object")
        return errors
    gate_keys = (
        "G1_mechanism_specificity",
        "G2_implementable_artifacts",
        "G3_beyond_basics",
        "G4_source_verifiability",
    )
    gate_values: list[bool] = []
    for key in gate_keys:
        gate = gatekeeper.get(key)
        value = gate.get("pass") if isinstance(gate, dict) else None
        if not isinstance(value, bool):
            errors.append("all gate pass values must be booleans")
            return errors
        evidence = gate.get("evidence") if isinstance(gate, dict) else None
        if not isinstance(evidence, str) or not evidence.strip():
            errors.append(f"{key}.evidence must be a non-empty string")
        gate_values.append(value)
    expected_gatekeeper = "PASS" if all(gate_values) else "REJECT"
    if gatekeeper.get("verdict") != expected_gatekeeper:
        errors.append(f"gatekeeper verdict must be {expected_gatekeeper}")
    author_or_org = source.get("author_or_org")
    if gate_values[-1] and (
        not isinstance(author_or_org, str) or not author_or_org.strip()
    ):
        errors.append("passing source verification requires source.author_or_org")

    scoring = data.get("scoring")
    if not isinstance(scoring, dict):
        errors.append("scoring must be an object")
        return errors
    score_keys = (
        "D1_technical_depth_actionability",
        "D2_repo_relevance",
        "D3_evidence_rigor",
        "D4_novelty_insight",
    )
    scores: dict[str, float] = {}
    scores_valid = True
    for key in score_keys:
        dimension = scoring.get(key)
        score = dimension.get("score") if isinstance(dimension, dict) else None
        if (
            isinstance(score, bool)
            or not isinstance(score, (int, float))
            or not math.isfinite(float(score))
            or score not in {0, 1, 2}
        ):
            errors.append(f"{key}.score must be one of 0, 1, or 2")
            scores_valid = False
            continue
        scores[key] = float(score)
        reasoning = dimension.get("reasoning") if isinstance(dimension, dict) else None
        if not isinstance(reasoning, str) or not reasoning.strip():
            errors.append(f"{key}.reasoning must be a non-empty string")

    if not scores_valid:
        return errors

    recomputed_total = (
        scores["D1_technical_depth_actionability"] * 0.35
        + scores["D2_repo_relevance"] * 0.30
        + scores["D3_evidence_rigor"] * 0.20
        + scores["D4_novelty_insight"] * 0.15
    )
    recorded_total = scoring.get("weighted_total")
    if (
        isinstance(recorded_total, bool)
        or not isinstance(recorded_total, (int, float))
        or not math.isfinite(float(recorded_total))
    ):
        errors.append("scoring.weighted_total must be numeric")
        return errors
    if abs(float(recorded_total) - recomputed_total) > 0.011:
        errors.append(
            f"weighted_total {recorded_total} does not match recomputed "
            f"{recomputed_total:.3f}"
        )

    gates_pass = all(gate_values)
    if not gates_pass:
        expected_decision = {"verdict": "REJECT", "override_triggered": None}
    elif scores["D1_technical_depth_actionability"] == 0:
        expected_decision = {"verdict": "REJECT", "override_triggered": "O1"}
    elif scores["D2_repo_relevance"] == 0:
        expected_decision = {"verdict": "REJECT", "override_triggered": "O2"}
    elif scores["D3_evidence_rigor"] == 1 and recomputed_total >= 1.4:
        expected_decision = {
            "verdict": "HUMAN_REVIEW",
            "override_triggered": "O3",
        }
    elif scores["D4_novelty_insight"] == 2 and recomputed_total < 1.4:
        expected_decision = {
            "verdict": "HUMAN_REVIEW",
            "override_triggered": "O4",
        }
    elif recomputed_total >= 1.4:
        expected_decision = {"verdict": "APPROVE", "override_triggered": None}
    elif recomputed_total >= 0.9:
        expected_decision = {"verdict": "HUMAN_REVIEW", "override_triggered": None}
    else:
        expected_decision = {"verdict": "REJECT", "override_triggered": None}

    if decision_verdict != expected_decision["verdict"]:
        errors.append(
            "decision verdict must be "
            f"{expected_decision['verdict']} under content-curation rubric"
        )
    actual_override = decision.get("override_triggered")
    if actual_override == "null":
        actual_override = None
    expected_override = expected_decision["override_triggered"]
    if actual_override != expected_override:
        errors.append(f"override_triggered must be {expected_override or 'null'}")
    if decision.get("confidence") not in {"high", "medium", "low"}:
        errors.append("decision.confidence is invalid")
    justification = decision.get("justification")
    if not isinstance(justification, str) or not justification.strip():
        errors.append("decision.justification must be a non-empty string")

    extraction = data.get("extraction")
    if not isinstance(extraction, dict):
        errors.append("extraction must be an object")
        return errors
    target = extraction.get("candidate_skill_target")
    if target not in {"new skill", "existing skill", "reference only", "reject"}:
        errors.append("extraction.candidate_skill_target is invalid")
    if extraction.get("taxonomy_category") not in {
        "context_retrieval",
        "context_processing",
        "context_management",
        "rag",
        "memory",
        "tool_integration",
        "multi_agent",
        "evaluation",
        "harness_engineering",
        "project_development",
    }:
        errors.append("extraction.taxonomy_category is invalid")
    if extraction.get("estimated_complexity") not in {"low", "medium", "high"}:
        errors.append("extraction.estimated_complexity is invalid")
    artifacts = extraction.get("implementable_artifacts")
    failure_modes = extraction.get("failure_modes")
    for field, value in (
        ("implementable_artifacts", artifacts),
        ("failure_modes", failure_modes),
    ):
        if not isinstance(value, list) or any(
            not isinstance(item, str) or not item.strip() for item in value
        ):
            errors.append(f"extraction.{field} must be a list of non-empty strings")
    if decision_verdict in {"APPROVE", "HUMAN_REVIEW"}:
        mechanism = extraction.get("mechanism")
        if not isinstance(mechanism, str) or not mechanism.strip():
            errors.append("approved or reviewed extraction requires a mechanism summary")
        if not isinstance(artifacts, list) or not artifacts:
            errors.append("approved or reviewed extraction requires implementable artifacts")
        if not isinstance(failure_modes, list) or not failure_modes:
            errors.append("approved or reviewed extraction requires failure modes")
        if target not in {"new skill", "existing skill", "reference only"}:
            errors.append("approved or reviewed extraction requires a candidate skill target")
        if target in {"new skill", "existing skill"}:
            skill_name = extraction.get("candidate_skill_name")
            if not isinstance(skill_name, str) or not skill_name.strip():
                errors.append("candidate_skill_name is required for a skill target")
    return errors


def validate_state_history(
    data: dict[str, Any],
    *,
    observed_at: datetime | None = None,
) -> list[str]:
    """Return deterministic errors for a run-state document.

    This is the shared transition contract used by both mutation commands and
    repository/readiness validators. It deliberately validates the entire
    history before permitting another transition so manual edits cannot create
    a plausible current state atop an impossible path.
    """

    errors: list[str] = []
    observation_time = observed_at or datetime.now(timezone.utc)
    current = data.get("current_state")
    if current not in VALID_STATES:
        errors.append(f"current_state must be one of {sorted(VALID_STATES)}")

    history = data.get("state_history")
    if not isinstance(history, list) or not history:
        errors.append("state_history must be a non-empty list")
        return errors

    history_states: list[str | None] = []
    history_times: list[datetime | None] = []
    for index, entry in enumerate(history):
        if not isinstance(entry, dict):
            errors.append(f"state_history[{index}] must be an object")
            history_states.append(None)
            continue
        state = entry.get("state")
        if state not in VALID_STATES:
            errors.append(
                f"state_history[{index}].state must be one of {sorted(VALID_STATES)}"
            )
            history_states.append(None)
        else:
            history_states.append(state)
        for field in ("timestamp", "reason"):
            if not isinstance(entry.get(field), str) or not entry[field].strip():
                errors.append(
                    f"state_history[{index}].{field} must be a non-empty string"
                )
        if not isinstance(entry.get("evidence"), str):
            errors.append(f"state_history[{index}].evidence must be a string")
        parsed_timestamp = parse_utc_datetime(entry.get("timestamp"))
        if parsed_timestamp is None:
            errors.append(
                f"state_history[{index}].timestamp must be a timezone-aware UTC ISO-8601 value"
            )
        elif parsed_timestamp > observation_time + MAX_RUNTIME_CLOCK_SKEW:
            errors.append(f"state_history[{index}].timestamp is future-dated")
        history_times.append(parsed_timestamp)

    if history_states[0] != "initialized":
        errors.append("state_history[0].state must be initialized")

    for index, (source, target) in enumerate(
        zip(history_states, history_states[1:]), start=1
    ):
        if source is None or target is None:
            continue
        if target not in LEGAL_STATE_TRANSITIONS[source]:
            errors.append(
                f"state_history[{index}] has illegal transition {source} -> {target}"
            )
    for index, (prior, current_time) in enumerate(
        zip(history_times, history_times[1:]), start=1
    ):
        if prior is not None and current_time is not None and current_time < prior:
            errors.append(f"state_history[{index}].timestamp moves backward")

    final_state = history_states[-1]
    if current in VALID_STATES and final_state is not None and current != final_state:
        errors.append(
            "current_state must equal the final state_history state "
            f"({final_state})"
        )
    if current == "closed" and data.get("close_status") == "accepted":
        predecessor = history_states[-2] if len(history_states) >= 2 else None
        if predecessor != "pr_ready":
            errors.append("accepted closure must immediately follow pr_ready")
    return errors


def validate_state_document(
    data: dict[str, Any],
    *,
    expected_run_id: str | None = None,
    observed_at: datetime | None = None,
) -> list[str]:
    """Validate the complete durable run-state boundary.

    This function is intentionally pure so mutators, queue supervisors, and
    validators can enforce one state-document contract without constructing a
    ``RunValidator`` or depending on repository-global paths.
    """

    observation_time = observed_at or datetime.now(timezone.utc)
    errors = validate_state_history(data, observed_at=observation_time)
    required_string_fields = ["run_id", "title", "created_at", "updated_at"]
    if expected_run_id != LEGACY_REFERENCE_RUN_ID:
        required_string_fields.append("source_id")
    for field in required_string_fields:
        value = data.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{field} must be a non-empty string")
    created_at = parse_utc_datetime(data.get("created_at"))
    updated_at = parse_utc_datetime(data.get("updated_at"))
    if created_at is None:
        errors.append("created_at must be a timezone-aware UTC ISO-8601 value")
    if updated_at is None:
        errors.append("updated_at must be a timezone-aware UTC ISO-8601 value")
    if created_at is not None and created_at > observation_time + MAX_RUNTIME_CLOCK_SKEW:
        errors.append("created_at is future-dated")
    if updated_at is not None and updated_at > observation_time + MAX_RUNTIME_CLOCK_SKEW:
        errors.append("updated_at is future-dated")
    history = data.get("state_history")
    if isinstance(history, list) and history:
        first_timestamp = parse_utc_datetime(
            history[0].get("timestamp") if isinstance(history[0], dict) else None
        )
        last_timestamp = parse_utc_datetime(
            history[-1].get("timestamp") if isinstance(history[-1], dict) else None
        )
        if created_at is not None and first_timestamp is not None and created_at != first_timestamp:
            errors.append("created_at must equal the initial state timestamp")
        if updated_at is not None and last_timestamp is not None and updated_at < last_timestamp:
            errors.append("updated_at must not precede the final state timestamp")
    source_url = data.get("source_url")
    if not isinstance(source_url, str):
        errors.append("source_url must be a string")
    elif source_url:
        try:
            normalized_url = normalize_source_url(source_url)
        except ValueError as exc:
            errors.append(str(exc))
        else:
            if source_url != normalized_url:
                errors.append("source_url must use canonical HTTP(S) form")

    run_id = data.get("run_id")
    if expected_run_id is not None and run_id != expected_run_id:
        errors.append(f"run_id must equal managed directory name ({expected_run_id})")
    if data.get("current_state") == "closed" and data.get("close_status") == "accepted":
        errors.append(
            "accepted closure is unsupported in the legacy loop; authority remains none"
        )

    if isinstance(run_id, str) and run_id.strip():
        base = f"researcher/runs/{run_id}"
        exact_evidence = {
            "initialized": base,
            "proposed": f"{base}/proposals/skill-proposal.md",
            "novelty_checked": f"{base}/reports/novelty-result.json",
            "validated": f"{base}/reports/run-readiness.json",
            "pr_ready": f"{base}/reports/pr-readiness.md",
            "closed": f"{base}/reports/closure.json",
        }
        history_entries = data.get("state_history")
        if isinstance(history_entries, list):
            for index, entry in enumerate(history_entries):
                if not isinstance(entry, dict):
                    continue
                state_name = entry.get("state")
                evidence = entry.get("evidence")
                if state_name in exact_evidence and evidence != exact_evidence[state_name]:
                    errors.append(
                        f"state_history[{index}].evidence must bind {exact_evidence[state_name]}"
                    )
                elif state_name == "evaluated" and not (
                    isinstance(evidence, str)
                    and not PurePosixPath(evidence).is_absolute()
                    and ".." not in PurePosixPath(evidence).parts
                    and str(PurePosixPath(evidence)) == evidence
                    and evidence.startswith(f"{base}/sources/evaluations/")
                    and evidence.endswith(".json")
                ):
                    errors.append(
                        f"state_history[{index}].evidence must bind a run evaluation JSON file"
                    )
                elif state_name == "retrieved":
                    evidence_values = (
                        [item.strip() for item in evidence.split(",")]
                        if isinstance(evidence, str)
                        else []
                    )
                    raw_prefix = f"{base}/sources/evidence/raw"
                    normalized = all(
                        not PurePosixPath(value).is_absolute()
                        and ".." not in PurePosixPath(value).parts
                        and str(PurePosixPath(value)) == value
                        for value in evidence_values
                    )
                    manifest = data.get("retrieval_evidence")
                    manifest_paths = (
                        [item.get("path") for item in manifest if isinstance(item, dict)]
                        if isinstance(manifest, list)
                        else []
                    )
                    exact_legacy_reference = (
                        run_id == LEGACY_REFERENCE_RUN_ID
                        and evidence_values == [raw_prefix]
                        and not manifest_paths
                    )
                    if not normalized or not (
                        exact_legacy_reference
                        or evidence_values == manifest_paths
                    ):
                        errors.append(
                            f"state_history[{index}].evidence must exactly bind retrieval_evidence paths"
                        )

    for field in ("locked_surfaces", "editable_surfaces"):
        surfaces = data.get(field)
        if not isinstance(surfaces, list):
            errors.append(f"{field} must be a list")
            continue
        invalid = [
            index
            for index, value in enumerate(surfaces)
            if not isinstance(value, str) or not value.strip()
        ]
        for index in invalid:
            errors.append(f"{field}[{index}] must be a non-empty string")
        string_surfaces = [value for value in surfaces if isinstance(value, str)]
        if len(string_surfaces) != len(set(string_surfaces)):
            errors.append(f"{field} must not contain duplicates")
    if data.get("locked_surfaces") != list(CANONICAL_LOCKED_SURFACES):
        errors.append("locked_surfaces must equal the canonical protected-surface list")
    if isinstance(run_id, str) and run_id.strip() and data.get(
        "editable_surfaces"
    ) != expected_run_editable_surfaces(run_id):
        errors.append("editable_surfaces must equal the canonical run-local surface list")

    if "close_status" not in data:
        errors.append("close_status is required")
    if "close_reason" not in data:
        errors.append("close_reason is required")
    if data.get("current_state") == "closed":
        if data.get("close_status") not in VALID_CLOSE_STATUS:
            errors.append("closed state requires a valid close_status")
        close_reason = data.get("close_reason")
        if not isinstance(close_reason, str) or not close_reason.strip():
            errors.append("closed state requires a non-empty close_reason")
    elif data.get("close_status") is not None or data.get("close_reason") is not None:
        errors.append("active state must not carry closure metadata")
    return errors


@dataclass
class Finding:
    severity: str
    path: str
    message: str


class RunValidator:
    def __init__(self, run_dir: Path, *, integrity_only: bool = False) -> None:
        # Preserve the lexical path so a symlink passed as the run directory is
        # observable. Path.resolve() here would erase precisely the condition
        # that this boundary must reject.
        self.run_dir = Path(os.path.abspath(run_dir))
        self.root = ROOT.resolve()
        self.integrity_only = integrity_only
        self.findings: list[Finding] = []
        self._evaluation_path: Path | None = None
        self._evaluation_data: dict[str, Any] | None = None
        self._novelty_data: dict[str, Any] | None = None

    @property
    def evaluation_path(self) -> Path | None:
        return self._evaluation_path

    @property
    def evaluation_data(self) -> dict[str, Any] | None:
        return self._evaluation_data

    def rel(self, path: Path | str) -> str:
        p = Path(path)
        try:
            return str(p.relative_to(self.root))
        except ValueError:
            return str(p)

    def error(self, path: Path | str, message: str) -> None:
        self.findings.append(Finding("error", self.rel(path), message))

    def warn(self, path: Path | str, message: str) -> None:
        self.findings.append(Finding("warning", self.rel(path), message))

    @staticmethod
    def path_lexists(path: Path) -> bool:
        try:
            os.lstat(path)
        except FileNotFoundError:
            return False
        except OSError:
            return True
        return True

    def require_managed_path(
        self,
        path: Path,
        *,
        kind: str,
        required: bool = True,
    ) -> bool:
        """Reject aliases and nonconforming nodes before reading an artifact."""

        candidate = Path(os.path.abspath(path))
        try:
            relative = candidate.relative_to(self.run_dir)
        except ValueError:
            self.error(candidate, "run artifact escapes the managed run directory")
            return False

        root = Path(os.path.abspath(self.root))
        try:
            run_relative = self.run_dir.relative_to(root)
            components = [root]
            current = root
        except ValueError:
            # There is no trusted ancestor for an explicitly supplied external
            # run. Validate the run node itself and every descendant consumed;
            # callers that own a separate root can set ``validator.root``.
            run_relative = Path()
            components = [self.run_dir]
            current = self.run_dir
        for part in run_relative.parts:
            current /= part
            components.append(current)
        for part in relative.parts:
            current /= part
            components.append(current)

        for index, component in enumerate(components):
            try:
                info = os.lstat(component)
            except FileNotFoundError:
                if required or index < len(components) - 1:
                    self.error(component, f"{kind} missing")
                return False
            except OSError as exc:
                self.error(component, f"cannot inspect managed path: {exc}")
                return False
            if stat.S_ISLNK(info.st_mode):
                self.error(component, "managed path component must not be a symlink")
                return False
            if index < len(components) - 1 and not stat.S_ISDIR(info.st_mode):
                self.error(component, "managed path ancestor must be a directory")
                return False

        final_mode = info.st_mode
        if kind == "directory" and not stat.S_ISDIR(final_mode):
            self.error(candidate, "managed path must be a directory")
            return False
        if kind == "file" and not stat.S_ISREG(final_mode):
            self.error(candidate, "managed path must be a regular file")
            return False
        if kind == "file" and info.st_nlink != 1:
            self.error(candidate, "managed file must have exactly one hard link")
            return False
        return True

    @staticmethod
    def read_text_file(path: Path) -> str:
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
        with os.fdopen(descriptor, "r", encoding="utf-8") as handle:
            return handle.read()

    def validate_claimed_integrity(
        self,
        state: dict[str, Any] | None,
        queue_record: dict[str, Any] | None,
        *,
        require_unclaimed_readiness: bool = False,
    ) -> list[Finding]:
        """Validate evidence already claimed by lifecycle history.

        Full publish-readiness validation additionally requires the evaluation,
        proposal, and novelty artifacts even before the corresponding transition.
        This method deliberately excludes state/queue/closure shape so a reduced
        terminal decision can record artifact-integrity failures without
        laundering malformed lifecycle authority.
        """

        finding_start = len(self.findings)
        current_state = (state or {}).get("current_state")
        close_status = (state or {}).get("close_status")
        history = (state or {}).get("state_history")
        history_states = {
            entry.get("state")
            for entry in history
            if isinstance(entry, dict)
        } if isinstance(history, list) else set()
        reached_retrieved = "retrieved" in history_states
        evidence_manifest = (state or {}).get("retrieval_evidence")
        legacy_reference = (
            self.run_dir
            == self.root / "researcher" / "runs" / LEGACY_REFERENCE_RUN_ID
            and current_state == "closed"
            and close_status == "reference-only"
        )
        if reached_retrieved and evidence_manifest is None and not legacy_reference:
            self.error(
                self.run_dir / "run-state.json",
                "retrieved lifecycle requires a retrieval_evidence manifest",
            )
        if evidence_manifest is not None:
            self.validate_evidence(state or {}, queue_record)

        source_status: str | None = None
        if require_unclaimed_readiness or "evaluated" in history_states:
            source_status = self.validate_source_evaluation(state, queue_record)
        novelty_data: dict[str, Any] | None = None
        if require_unclaimed_readiness or "novelty_checked" in history_states:
            novelty_data = self.validate_novelty()
        if require_unclaimed_readiness or "proposed" in history_states:
            self.validate_proposal(
                source_status,
                state,
                queue_record,
                novelty_data,
            )
        if "validated" in history_states:
            self.validate_readiness_report(state)
        if "pr_ready" in history_states or close_status == "accepted":
            self.validate_pr_readiness()
        return self.findings[finding_start:]

    def run(self) -> dict[str, Any]:
        if self.require_managed_path(self.run_dir, kind="directory"):
            state_data = self.validate_state()
            current_state = (state_data or {}).get("current_state")
            close_status = (state_data or {}).get("close_status")
            queue_record = self.validate_queue()
            self.validate_source_identity(state_data, queue_record)
            requires_full_readiness = current_state != "closed" or close_status == "accepted"
            terminal_integrity_errors: list[str] = []
            integrity_findings = self.validate_claimed_integrity(
                state_data,
                queue_record,
                require_unclaimed_readiness=(
                    requires_full_readiness and not self.integrity_only
                ),
            )
            if not requires_full_readiness:
                terminal_integrity_errors = [
                    f"{finding.path}: {finding.message}"
                    for finding in integrity_findings
                    if finding.severity == "error"
                ]
                integrity_finding_start = len(self.findings) - len(integrity_findings)
                self.findings[integrity_finding_start:] = [
                    finding
                    for finding in integrity_findings
                    if finding.severity != "error"
                ]
            self.validate_closure(state_data, terminal_integrity_errors)
            if not requires_full_readiness and terminal_integrity_errors:
                closure_path = self.run_dir / "reports" / "closure.json"
                closure = self.load_json(closure_path)
                if isinstance(closure, dict) and closure.get(
                    "integrity_errors"
                ) == terminal_integrity_errors:
                    for message in terminal_integrity_errors:
                        self.warn(
                            closure_path,
                            f"terminal closure records integrity failure: {message}",
                        )
                else:
                    self.findings.extend(
                        finding
                        for finding in integrity_findings
                        if finding.severity == "error"
                    )

        errors = sum(1 for finding in self.findings if finding.severity == "error")
        warnings = sum(1 for finding in self.findings if finding.severity == "warning")
        return {
            "ok": errors == 0,
            "run_dir": self.rel(self.run_dir),
            "summary": {"errors": errors, "warnings": warnings},
            "findings": [asdict(finding) for finding in self.findings],
        }

    def validate_state(self) -> dict[str, Any] | None:
        path = self.run_dir / "run-state.json"
        data = self.load_json(path)
        if not isinstance(data, dict):
            return None
        for message in validate_state_document(
            data,
            expected_run_id=self.run_dir.name,
        ):
            self.error(path, message)
        return data

    def validate_queue(self) -> dict[str, Any] | None:
        queue = self.run_dir / "sources" / "queue.jsonl"
        if not self.require_managed_path(queue, kind="file"):
            return None
        records: list[dict[str, Any]] = []
        try:
            lines = self.read_text_file(queue).splitlines()
        except (OSError, UnicodeError) as exc:
            self.error(queue, f"cannot read source queue: {exc}")
            return None
        for line_number, line in enumerate(lines, start=1):
            if not line.strip():
                continue
            try:
                record = strict_json_loads(line)
            except (
                json.JSONDecodeError,
                DuplicateKeyError,
                NonFiniteJSONNumberError,
            ) as exc:
                self.error(queue, f"line {line_number} invalid JSONL: {exc}")
                continue
            if not isinstance(record, dict):
                self.error(queue, f"line {line_number} must be an object")
                continue
            records.append(record)
            for field in ("id", "title"):
                value = record.get(field)
                if not isinstance(value, str) or not value.strip():
                    self.error(
                        queue,
                        f"line {line_number} {field} must be a non-empty string",
                    )
            if not isinstance(record.get("url"), str):
                self.error(queue, f"line {line_number} url must be a string")
            if not isinstance(record.get("author_or_org"), str):
                self.error(queue, f"line {line_number} author_or_org must be a string")
            if record.get("source_type") not in {
                "paper",
                "engineering_blog",
                "documentation",
                "benchmark",
                "code",
                "talk",
                "other",
            }:
                self.error(queue, f"line {line_number} source_type is invalid")
            if record.get("retrieval_status") not in {
                "partial",
                "retrieved",
                "failed",
            }:
                self.error(queue, f"line {line_number} retrieval_status is invalid")
        if len(records) != 1:
            self.error(queue, "source queue must contain exactly one object record")
            return None
        return records[0]

    def validate_source_identity(
        self,
        state: dict[str, Any] | None,
        queue_record: dict[str, Any] | None,
        evaluation: dict[str, Any] | None = None,
        evaluation_path: Path | None = None,
    ) -> None:
        """Require exact URL/title identity at every durable source surface."""

        if not isinstance(state, dict) or not isinstance(queue_record, dict):
            return
        state_path = self.run_dir / "run-state.json"
        queue_path = self.run_dir / "sources" / "queue.jsonl"
        for state_field, queue_field in (
            ("source_id", "id"),
            ("title", "title"),
            ("source_url", "url"),
        ):
            if (
                state_field == "source_id"
                and self.run_dir.name == LEGACY_REFERENCE_RUN_ID
                and state.get(state_field) is None
            ):
                continue
            if state.get(state_field) != queue_record.get(queue_field):
                self.error(
                    queue_path,
                    f"queue {queue_field} differs from state {state_field}",
                )
        history = state.get("state_history")
        history_states = {
            item.get("state")
            for item in history
            if isinstance(item, dict)
        } if isinstance(history, list) else set()
        if "retrieved" in history_states and queue_record.get(
            "retrieval_status"
        ) != "retrieved":
            self.error(
                queue_path,
                "retrieved lifecycle requires queue retrieval_status retrieved",
            )
        if evaluation is None:
            return
        source = evaluation.get("source")
        if not isinstance(source, dict):
            self.error(evaluation_path or state_path, "evaluation source must be an object")
            return
        evaluation_timestamp = parse_utc_datetime(evaluation.get("timestamp"))
        created_at = parse_utc_datetime(state.get("created_at"))
        if (
            evaluation_timestamp is not None
            and created_at is not None
            and evaluation_timestamp < created_at
        ):
            self.error(
                evaluation_path or state_path,
                "evaluation timestamp precedes run creation",
            )
        evaluated_entry = next(
            (
                item
                for item in history
                if isinstance(item, dict) and item.get("state") == "evaluated"
            ),
            None,
        ) if isinstance(history, list) else None
        evaluated_at = parse_utc_datetime(
            evaluated_entry.get("timestamp")
            if isinstance(evaluated_entry, dict)
            else None
        )
        if (
            evaluation_timestamp is not None
            and evaluated_at is not None
            and evaluation_timestamp > evaluated_at
        ):
            self.error(
                evaluation_path or state_path,
                "evaluation timestamp postdates the evaluated transition",
            )
        for field, queue_field in (
            ("title", "title"),
            ("url", "url"),
            ("author_or_org", "author_or_org"),
            ("source_type", "source_type"),
        ):
            if source.get(field) != queue_record.get(queue_field):
                self.error(
                    evaluation_path or state_path,
                    f"evaluation source {field} differs from queue {queue_field}",
                )
        if "evaluated" in history_states:
            expected_file = self.rel(evaluation_path) if evaluation_path else None
            decision = evaluation.get("decision")
            expected_decision = (
                decision.get("verdict") if isinstance(decision, dict) else None
            )
            if queue_record.get("retrieval_status") != source.get("retrieval_status"):
                self.error(
                    evaluation_path or state_path,
                    "queue retrieval_status differs from evaluation source status",
                )
            if queue_record.get("evaluation_file") != expected_file:
                self.error(
                    evaluation_path or state_path,
                    "queue evaluation_file does not bind the completed evaluation",
                )
            if queue_record.get("evaluation_decision") != expected_decision:
                self.error(
                    evaluation_path or state_path,
                    "queue evaluation_decision differs from completed evaluation",
                )

    def validate_evidence(
        self,
        state: dict[str, Any],
        queue_record: dict[str, Any] | None,
    ) -> None:
        raw_dir = self.run_dir / "sources" / "evidence" / "raw"
        if queue_record is None:
            self.error(raw_dir, "retrieval evidence requires one valid queue record")
            return
        if not self.require_managed_path(raw_dir, kind="directory"):
            return
        paths = queue_record.get("raw_evidence")
        digests = queue_record.get("raw_evidence_sha256")
        sizes = queue_record.get("raw_evidence_size_bytes")
        if not (
            isinstance(paths, list)
            and isinstance(digests, list)
            and isinstance(sizes, list)
            and paths
            and len(paths) == len(digests) == len(sizes)
        ):
            self.error(raw_dir, "retrieval evidence manifest is incomplete")
            return
        if len(paths) > MAX_EVIDENCE_FILES:
            self.error(raw_dir, "retrieval evidence file-count limit exceeded")
            return
        manifest: list[dict[str, Any]] = []
        expected_files: set[Path] = set()
        batch_size = 0
        for index, (path_value, digest_value, size_value) in enumerate(
            zip(paths, digests, sizes)
        ):
            if not isinstance(path_value, str):
                self.error(raw_dir, f"raw_evidence[{index}] must be a string")
                continue
            if not (
                isinstance(digest_value, str)
                and re.fullmatch(r"sha256:[0-9a-f]{64}", digest_value)
            ):
                self.error(raw_dir, f"raw_evidence_sha256[{index}] is invalid")
                continue
            if (
                type(size_value) is not int
                or size_value <= 0
                or size_value > MAX_EVIDENCE_FILE_BYTES
            ):
                self.error(raw_dir, f"raw_evidence_size_bytes[{index}] is invalid")
                continue
            batch_size += size_value
            if batch_size > MAX_EVIDENCE_BATCH_BYTES:
                self.error(raw_dir, "retrieval evidence batch-size limit exceeded")
                break
            hexdigest = digest_value.removeprefix("sha256:")
            expected = raw_dir / hexdigest
            candidate = Path(os.path.abspath(self.root / path_value))
            if candidate != expected:
                self.error(raw_dir, f"evidence path is not its content address: {path_value}")
                continue
            expected_files.add(candidate)
            if not self.require_managed_path(candidate, kind="file"):
                continue
            info = os.lstat(candidate)
            if info.st_nlink != 1 or info.st_size != size_value:
                self.error(candidate, "evidence bytes or file identity do not match manifest")
                continue
            if info.st_mode & 0o222:
                self.error(candidate, "evidence file must have no write permission bits")
            try:
                digest = self.sha256_file(candidate)
            except OSError as exc:
                self.error(candidate, f"cannot read evidence file: {exc}")
                continue
            if digest != hexdigest:
                self.error(candidate, "evidence bytes or file identity do not match manifest")
                continue
            manifest.append(
                {"path": path_value, "sha256": digest_value, "size_bytes": size_value}
            )
        try:
            observed_files = set(raw_dir.iterdir())
        except OSError as exc:
            self.error(raw_dir, f"cannot enumerate evidence directory: {exc}")
            return
        for observed in observed_files:
            self.require_managed_path(observed, kind="file")
        if observed_files != expected_files:
            self.error(raw_dir, "evidence directory has missing or unmanifested entries")
        if state.get("retrieval_evidence") != manifest:
            self.error(
                self.run_dir / "run-state.json",
                "state and queue evidence manifests differ",
            )

    @staticmethod
    def sha256_file(path: Path) -> str:
        digest = hashlib.sha256()
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
        with os.fdopen(descriptor, "rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
        return digest.hexdigest()

    def validate_source_evaluation(
        self,
        state: dict[str, Any] | None = None,
        queue_record: dict[str, Any] | None = None,
    ) -> str | None:
        eval_dir = self.run_dir / "sources" / "evaluations"
        if not self.require_managed_path(eval_dir, kind="directory"):
            return None
        completed: list[Path] = []
        drafts: list[Path] = []
        try:
            with os.scandir(eval_dir) as iterator:
                entries = sorted(Path(entry.path) for entry in iterator)
        except OSError as exc:
            self.error(eval_dir, f"cannot enumerate source evaluations: {exc}")
            return None
        for entry in entries:
            if not self.require_managed_path(entry, kind="file"):
                continue
            if entry.suffix != ".json":
                continue
            if "draft" in entry.stem:
                drafts.append(entry)
            else:
                completed.append(entry)
        if drafts and not completed:
            self.error(eval_dir, "run has only draft source evaluations")
            return None
        if not completed:
            self.error(eval_dir, "completed source evaluation missing")
            return None
        if len(completed) != 1:
            self.error(eval_dir, "run must contain exactly one completed source evaluation")
            return None

        data = self.load_json(completed[0])
        if not isinstance(data, dict):
            return None
        self._evaluation_path = completed[0]
        self._evaluation_data = data
        for message in source_evaluation_shape_errors(data):
            self.error(completed[0], message)
        history = (state or {}).get("state_history")
        evaluated_entry = next(
            (
                entry
                for entry in history or []
                if isinstance(entry, dict) and entry.get("state") == "evaluated"
            ),
            None,
        )
        if isinstance(evaluated_entry, dict) and evaluated_entry.get("evidence") != self.rel(
            completed[0]
        ):
            self.error(
                completed[0],
                "evaluated state history does not bind the completed evaluation",
            )
        self.validate_source_identity(state, queue_record, data, completed[0])
        source = data.get("source")
        status = source.get("retrieval_status") if isinstance(source, dict) else None
        if status != "retrieved":
            self.error(completed[0], "publish-ready run requires retrieved source evaluation")
        decision = data.get("decision")
        if isinstance(decision, dict) and decision.get("verdict") == "REJECT":
            self.error(completed[0], "rejected source cannot produce publish-ready changes")
        return str(status) if status else None

    def validate_proposal(
        self,
        source_status: str | None,
        state: dict[str, Any] | None = None,
        queue_record: dict[str, Any] | None = None,
        novelty_data: dict[str, Any] | None = None,
    ) -> None:
        path = self.run_dir / "proposals" / "skill-proposal.md"
        if not self.require_managed_path(path, kind="file"):
            return
        try:
            text = self.read_text_file(path)
        except (OSError, UnicodeError) as exc:
            self.error(path, f"cannot read skill proposal: {exc}")
            return
        for pattern in PLACEHOLDER_PATTERNS:
            if re.search(pattern, text):
                self.error(path, f"proposal still contains placeholder: {pattern}")
        required_prefixes = [
            "- URL:",
            "- Title:",
            "- Author or organization:",
            "- Source type:",
            "- Retrieval status:",
            "- Evaluation file:",
            "- Decision:",
            "- Target path:",
            "- Activation scenario:",
            "- Verdict:",
            "- Max mechanism overlap:",
            "- Top mechanism overlaps:",
            "- Human-review rationale:",
            "- Evidence limitations:",
            "- Possible duplication:",
            "- Required human review:",
        ]
        for prefix in required_prefixes:
            if re.search(rf"^{re.escape(prefix)}\s*$", text, flags=re.MULTILINE):
                self.error(path, f"proposal field is blank: {prefix}")

        fields: dict[str, str] = {}
        duplicates: set[str] = set()
        for line in text.splitlines():
            match = re.fullmatch(r"-[ \t]+([^:]+):[ \t]*(.*)", line)
            if match is None:
                continue
            label = match.group(1).strip()
            value = match.group(2).strip()
            if label in fields:
                duplicates.add(label)
            else:
                fields[label] = value
        for label in sorted(duplicates):
            self.error(path, f"proposal field is duplicated: {label}")
        for prefix in required_prefixes:
            label = prefix.removeprefix("- ").removesuffix(":")
            if label not in fields:
                self.error(path, f"proposal field is missing: {prefix}")

        expected_fields: dict[str, str] = {}
        if isinstance(state, dict):
            title = state.get("title")
            if isinstance(title, str):
                expected_fields["Title"] = title
                heading = re.search(r"^#[ \t]+Skill Proposal:[ \t]*(.+)$", text, re.MULTILINE)
                if heading is None or heading.group(1).strip() != title:
                    self.error(path, "proposal heading differs from run title")
        if isinstance(queue_record, dict):
            for label, key in (
                ("URL", "url"),
                ("Title", "title"),
                ("Author or organization", "author_or_org"),
                ("Source type", "source_type"),
            ):
                value = queue_record.get(key)
                if isinstance(value, str):
                    expected_fields[label] = value
        if source_status is not None:
            expected_fields["Retrieval status"] = source_status
        if self._evaluation_path is not None:
            expected_fields["Evaluation file"] = self.rel(self._evaluation_path)
        evaluation_decision = (
            self._evaluation_data.get("decision")
            if isinstance(self._evaluation_data, dict)
            else None
        )
        if isinstance(evaluation_decision, dict) and isinstance(
            evaluation_decision.get("verdict"), str
        ):
            expected_fields["Decision"] = evaluation_decision["verdict"]
        for label, expected in expected_fields.items():
            if fields.get(label) != expected:
                self.error(path, f"proposal {label} differs from validated source artifacts")

        novelty = novelty_data or self._novelty_data
        if isinstance(novelty, dict):
            novelty_verdict = novelty.get("verdict")
            expected_fields = {
                "Verdict": str(novelty_verdict or ""),
                "Max mechanism overlap": str(novelty.get("max_mechanism_score", "")),
            }
            if novelty_verdict == "pass":
                expected_fields["Human-review rationale"] = "none"
            else:
                rationale = novelty.get("human_review_rationale")
                if isinstance(rationale, str) and rationale.strip():
                    expected_fields["Human-review rationale"] = rationale
            overlaps = novelty.get("top_mechanism_overlaps")
            if isinstance(overlaps, list):
                overlap_ids = [
                    item.get("mechanism_id")
                    for item in overlaps
                    if isinstance(item, dict)
                    and isinstance(item.get("mechanism_id"), str)
                    and item.get("mechanism_id")
                ]
                expected_fields["Top mechanism overlaps"] = (
                    ", ".join(overlap_ids) if overlap_ids else "none"
                )
            for label, expected in expected_fields.items():
                if fields.get(label) != expected:
                    self.error(path, f"proposal {label} differs from novelty result")
        has_evidence_row = False
        for line in text.splitlines()[30:]:
            if not line.startswith("|") or line.count("|") < 3:
                continue
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if not cells or cells[0] in {"Claim", "---"} or set("".join(cells)) <= {"-", " "}:
                continue
            if any(cells):
                has_evidence_row = True
                break
        if source_status != "retrieved" and has_evidence_row:
            self.error(path, "proposal cites evidence from a source that is not fully retrieved")

    def validate_novelty(self) -> dict[str, Any] | None:
        path = self.run_dir / "reports" / "novelty-result.json"
        data = self.load_json(path)
        if not isinstance(data, dict):
            return None
        self._novelty_data = data
        verdict = data.get("verdict")
        if verdict not in {"pass", "human_review", "likely_duplicate"}:
            self.error(path, "novelty verdict is invalid")
        rationale = data.get("human_review_rationale")
        if verdict == "pass" and rationale is not None:
            self.error(path, "pass novelty verdict must not carry human_review_rationale")
        if verdict != "pass" and (
            not isinstance(rationale, str)
            or not rationale.strip()
            or rationale != rationale.strip()
        ):
            self.error(
                path,
                "non-pass novelty verdict requires a canonical non-empty human_review_rationale",
            )
        proposal = self.run_dir / "proposals" / "skill-proposal.md"
        if not self.require_managed_path(proposal, kind="file"):
            return data
        command = [
            sys.executable,
            str(ROOT / "researcher" / "scripts" / "novelty_check.py"),
            "--root",
            str(self.root),
            "--file",
            str(proposal),
            "--json",
        ]
        try:
            completed = subprocess.run(
                command,
                cwd=self.root,
                text=True,
                capture_output=True,
                check=False,
                timeout=60,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            self.error(path, f"cannot recompute novelty result: {exc}")
            return data
        try:
            expected = strict_json_loads(completed.stdout)
        except (
            json.JSONDecodeError,
            DuplicateKeyError,
            NonFiniteJSONNumberError,
        ) as exc:
            self.error(path, f"novelty checker returned invalid JSON: {exc}")
            return data
        if not isinstance(expected, dict):
            self.error(path, "novelty checker did not return an object")
            return data
        expected_exit = 0 if expected.get("verdict") == "pass" else 2
        if completed.returncode != expected_exit:
            self.error(path, "novelty checker exit status disagrees with its verdict")
        observed = dict(data)
        observed.pop("human_review_rationale", None)
        if not exact_json_equal(observed, expected):
            self.error(path, "novelty result differs from deterministic recomputation")
        return data

    def validate_readiness_report(self, state: dict[str, Any] | None) -> None:
        path = self.run_dir / "reports" / "run-readiness.json"
        data = self.load_json(path)
        if not isinstance(data, dict):
            return
        if data.get("ok") is not True:
            self.error(path, "claimed validated stage requires a passing readiness report")
        expected_run = self.rel(self.run_dir)
        if data.get("run_dir") != expected_run:
            self.error(path, "readiness report run_dir differs from the managed run")
        summary = data.get("summary")
        findings = data.get("findings")
        if not isinstance(summary, dict) or not isinstance(findings, list):
            self.error(path, "readiness report summary or findings is invalid")
        else:
            errors = sum(
                isinstance(finding, dict) and finding.get("severity") == "error"
                for finding in findings
            )
            warnings = sum(
                isinstance(finding, dict) and finding.get("severity") == "warning"
                for finding in findings
            )
            if summary != {"errors": errors, "warnings": warnings}:
                self.error(path, "readiness report summary disagrees with findings")
            if errors:
                self.error(path, "claimed validated stage contains readiness errors")
        history = (state or {}).get("state_history")
        entry = next(
            (
                item
                for item in history or []
                if isinstance(item, dict) and item.get("state") == "validated"
            ),
            None,
        )
        if not isinstance(entry, dict) or entry.get("evidence") != self.rel(path):
            self.error(path, "validated state history does not bind the readiness report")

    def validate_pr_readiness(self) -> None:
        path = self.run_dir / "reports" / "pr-readiness.md"
        if not self.require_managed_path(path, kind="file"):
            return
        try:
            text = self.read_text_file(path)
        except (OSError, UnicodeError) as exc:
            self.error(path, f"cannot read PR readiness notes: {exc}")
            return
        for heading in ("Summary", "Test Plan", "Risks"):
            match = re.search(
                rf"^##[ \t]+{re.escape(heading)}[ \t]*$"
                rf"(?P<body>.*?)(?=^##[ \t]+|\Z)",
                text,
                flags=re.MULTILINE | re.DOTALL,
            )
            if match is None:
                self.error(path, f"PR readiness notes missing ## {heading}")
            elif not match.group("body").strip():
                self.error(path, f"PR readiness section is blank: ## {heading}")
        if "human approval" not in text.lower():
            self.error(path, "PR readiness notes missing human approval")

    def validate_closure(
        self,
        state: dict[str, Any] | None,
        evidence_errors: list[str] | None = None,
    ) -> None:
        path = self.run_dir / "reports" / "closure.json"
        current_state = (state or {}).get("current_state")
        if current_state != "closed":
            if self.path_lexists(path):
                self.require_managed_path(path, kind="file")
                self.error(path, "active run must not contain closure.json")
            return
        if not self.require_managed_path(path, kind="file"):
            return
        data = self.load_json(path)
        if not isinstance(data, dict):
            return
        if data.get("status") not in VALID_CLOSE_STATUS:
            self.error(path, f"closure status must be one of {sorted(VALID_CLOSE_STATUS)}")
        if not data.get("reason"):
            self.error(path, "closure reason is required")
        if data.get("status") == "accepted" and not data.get("reviewed_by"):
            self.error(path, "accepted closure requires reviewed_by")
        integrity_errors = data.get("integrity_errors")
        if integrity_errors is not None and (
            not isinstance(integrity_errors, list)
            or any(
                not isinstance(message, str) or not message.strip()
                for message in integrity_errors
            )
        ):
            self.error(
                path,
                "closure integrity_errors must be a list of non-empty strings",
            )
        observed_evidence_errors = evidence_errors or []
        if observed_evidence_errors and integrity_errors != observed_evidence_errors:
            self.error(path, "closure integrity_errors differ from observed integrity failures")
        if (
            not observed_evidence_errors
            and isinstance(integrity_errors, list)
            and integrity_errors
            and data.get("status") != "accepted"
        ):
            self.error(path, "closure records integrity_errors but evidence currently validates")
        if data.get("status") == "accepted" and integrity_errors is not None:
            self.error(path, "accepted closure must not carry integrity_errors")
        if state is None:
            return
        if data.get("status") != state.get("close_status"):
            self.error(path, "closure status differs from run state")
        if data.get("reason") != state.get("close_reason"):
            self.error(path, "closure reason differs from run state")
        history = state.get("state_history")
        final = history[-1] if isinstance(history, list) and history else {}
        expected_evidence = self.rel(path)
        if final.get("evidence") != expected_evidence:
            self.error(path, "closure evidence path differs from final state history")
        if final.get("reason") != data.get("reason"):
            self.error(path, "closure reason differs from final state history")
        if final.get("timestamp") != data.get("closed_at"):
            self.error(path, "closure timestamp differs from final state history")

    def load_json(self, path: Path) -> Any:
        if not self.require_managed_path(path, kind="file"):
            return None
        try:
            return strict_json_loads(self.read_text_file(path))
        except (
            json.JSONDecodeError,
            DuplicateKeyError,
            NonFiniteJSONNumberError,
        ) as exc:
            self.error(path, f"invalid JSON: {exc}")
            return None
        except (OSError, UnicodeError) as exc:
            self.error(path, f"cannot read JSON file: {exc}")
            return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate publish readiness for a research run")
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--integrity-only",
        action="store_true",
        help="validate durable runtime integrity without requiring future readiness artifacts",
    )
    args = parser.parse_args()

    result = RunValidator(args.run_dir, integrity_only=args.integrity_only).run()
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        summary = result["summary"]
        print(
            f"Run validation {'passed' if result['ok'] else 'failed'}: "
            f"{summary['errors']} errors, {summary['warnings']} warnings"
        )
        for finding in result["findings"]:
            print(f"[{finding['severity']}] {finding['path']}: {finding['message']}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
