#!/usr/bin/env python3
"""Build and reconcile the repository's deterministic corpus inventory.

The inventory is a derived view, never an authority over its inputs. It has no
wall-clock timestamp or embedded Git SHA. ``source_tree_digest`` binds only the
exact byte snapshots that :class:`InventoryBuilder` consumed and lists those
declared inputs. It is not an exhaustive repository or runtime-behavior digest,
a freeze or security boundary, or a promise that daily, status, or validator
results can be reproduced from the digest. This avoids both self-referential
generated-output hashes and an unsound completeness claim.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import stat
import sys
import tempfile
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

if __package__:
    from researcher.scripts.skill_frontmatter import parse_frontmatter
    from researcher.scripts.validate_authority_contract import (
        AUTHORITY_CONFORMANCE_RECEIPT_PATH,
        AUTHORITY_CONSTITUTION_POLICY_PATH,
        AUTHORITY_EVALUATOR_COMPONENT_PATHS,
        AUTHORITY_FIXTURE_MANIFEST_PATH,
        AUTHORITY_IMPLEMENTED_STATUSES,
        AUTHORITY_SPEC_METADATA_KEYS,
        AUTHORITY_VOCABULARY_MIN_REVISION,
        AUTHORITY_VOCABULARY_PATH,
        AUTHORITY_VOCABULARY_READY_STATUSES,
        AUTHORITY_VOCABULARY_SCHEMA_ID,
        AUTHORITY_VOCABULARY_SCHEMA_PATH,
        AUTHORITY_VOCABULARY_SCHEMA_VERSION,
        AUTHORITY_VOCABULARY_SPEC,
        AuthorityVocabularyBinding,
        load_authority_vocabulary_schema,
    )
    from researcher.scripts.validate_spec_lifecycle import (
        SpecRevision,
        load_candidate_authority_vocabulary,
        parse_spec_revision,
    )
else:  # Direct script execution resolves siblings from this script's directory.
    from skill_frontmatter import parse_frontmatter  # type: ignore[import-not-found]
    from validate_authority_contract import (  # type: ignore[import-not-found]
        AUTHORITY_CONFORMANCE_RECEIPT_PATH,
        AUTHORITY_CONSTITUTION_POLICY_PATH,
        AUTHORITY_EVALUATOR_COMPONENT_PATHS,
        AUTHORITY_FIXTURE_MANIFEST_PATH,
        AUTHORITY_IMPLEMENTED_STATUSES,
        AUTHORITY_SPEC_METADATA_KEYS,
        AUTHORITY_VOCABULARY_MIN_REVISION,
        AUTHORITY_VOCABULARY_PATH,
        AUTHORITY_VOCABULARY_READY_STATUSES,
        AUTHORITY_VOCABULARY_SCHEMA_ID,
        AUTHORITY_VOCABULARY_SCHEMA_PATH,
        AUTHORITY_VOCABULARY_SCHEMA_VERSION,
        AUTHORITY_VOCABULARY_SPEC,
        AuthorityVocabularyBinding,
        load_authority_vocabulary_schema,
    )
    from validate_spec_lifecycle import (  # type: ignore[import-not-found]
        SpecRevision,
        load_candidate_authority_vocabulary,
        parse_spec_revision,
    )


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INVENTORY = ROOT / "researcher" / "corpus" / "inventory.json"
DEFAULT_SUMMARY = ROOT / "researcher" / "generated" / "corpus-summary.md"
SCHEMA_VERSION = "1.0.0"

SPEC_FILENAME_RE = re.compile(r"^SPEC-(?P<number>[0-9]{3})-(?P<slug>[a-z0-9-]+)\.md$")
SPEC_HEADING_RE = re.compile(r"^# SPEC-(?P<number>[0-9]{3}): (?P<title>.+)$")
SPEC_INDEX_ROW_RE = re.compile(
    r"^\|\s*\[SPEC-(?P<number>[0-9]{3})\]\((?P<path>SPEC-[^)]+\.md)\)"
    r"\s*\|[^|\n]+\|[^|\n]+\|\s*$"
)
SPEC_ID_RE = re.compile(r"^SPEC-[0-9]{3}$")
SPEC_GRAPH_EDGE_RE = re.compile(
    r'^\s*S(?P<source>[0-9]{3})(?:\["(?P<source_label>[^"\]]*)"\])?\s*-->\s*'
    r'S(?P<target>[0-9]{3})(?:\["(?P<target_label>[^"\]]*)"\])?\s*$'
)
SPEC_STATUSES = {
    "draft",
    "architecture_reviewed",
    "accepted",
    "implemented",
    "verified",
    "operational",
    "amended",
    "superseded",
    "retired",
}
SPEC_CLASSIFICATIONS = {"public", "private", "split"}
SPEC_REQUIRED_METADATA = (
    "Status",
    "Revision",
    "Revises",
    "Wave",
    "Classification",
    "Owners",
    "Depends on",
)
SPEC_OPTIONAL_METADATA = {
    "Activation",
    "Adoption decision",
    "Authority vocabulary schema",
    "Authority vocabulary schema digest",
    "Authority vocabulary schema version",
    "Authority vocabulary",
    "Authority vocabulary digest",
    "Authority vocabulary version",
    "Dependency revisions",
    "Lifecycle decision",
    "Replacement",
}
SPEC_METADATA_ORDER = (
    "Status",
    "Revision",
    "Revises",
    "Activation",
    "Wave",
    "Classification",
    "Owners",
    "Depends on",
    "Dependency revisions",
    "Authority vocabulary schema",
    "Authority vocabulary schema digest",
    "Authority vocabulary schema version",
    "Authority vocabulary",
    "Authority vocabulary digest",
    "Authority vocabulary version",
    "Adoption decision",
    "Lifecycle decision",
    "Replacement",
)
SPEC_REVISION_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
SPEC_LIFECYCLE_DECISION_RE = re.compile(r"^ADR-[0-9]{4}$")
SPEC_REPLACEMENT_RE = re.compile(r"^SPEC-[0-9]{3}@[1-9][0-9]*$")
SPEC_DEPENDENCY_REVISION_RE = re.compile(r"^(SPEC-[0-9]{3})@([1-9][0-9]*)$")
SPEC_TERMINAL_STATUSES = {"amended", "superseded", "retired"}
AUTHORITY_VOCABULARY_METADATA_KEYS = frozenset(AUTHORITY_SPEC_METADATA_KEYS)
ADR_FILENAME_RE = re.compile(r"^(?P<number>[0-9]{4})-(?P<slug>[a-z0-9-]+)\.md$")
ADR_HEADING_RE = re.compile(r"^# ADR-(?P<number>[0-9]{4}): (?P<title>.+)$")
ADR_INDEX_ROW_RE = re.compile(
    r"^- \[ADR-(?P<number>[0-9]{4}): (?P<title>[^\]]+)\]"
    r"\((?P<path>[0-9]{4}-[^)]+\.md)\)$"
)
ADR_STATUSES = {"accepted", "deprecated", "proposed", "superseded"}
ADR_ALLOWED_METADATA = {
    "Status",
    "Date",
    "Spec",
    "Specs",
    "Supersedes",
    "Lifecycle transition",
}
ADR_ID_RE = re.compile(r"^ADR-[0-9]{4}$")
ADR_LIFECYCLE_TRANSITION_RE = re.compile(
    r"^(?P<spec>SPEC-[0-9]{3})@(?P<revision>[1-9][0-9]*) -> "
    r"(?P<status>amended|superseded|retired) -> "
    r"(?P<replacement>SPEC-[0-9]{3}@[1-9][0-9]*|none)$"
)
FENCE_OPEN_RE = re.compile(r"^ {0,3}(?P<fence>`{3,}|~{3,})(?P<info>.*)$")
LEVEL_TWO_HEADING_RE = re.compile(r"^## (?P<title>.+?)\s*$")
RAW_HTML_BLOCK_START_RE = re.compile(
    r"^ {0,3}<(?:/?[A-Za-z][A-Za-z0-9-]*(?:[ \t/>]|$)|[!?])",
    re.IGNORECASE,
)

VALIDATOR_OWNERSHIP = (
    {
        "id": "governance-policy",
        "path": "researcher/scripts/validate_governance.py",
        "owns": [
            "constitutional invariants",
            "generated authority view",
            "authority conformance orchestration",
        ],
    },
    {
        "id": "authority-policy-evaluator",
        "path": "researcher/scripts/governance_policy.py",
        "owns": [
            "Constitution decision evaluation",
            "fail-closed policy rule matching",
        ],
    },
    {
        "id": "authority-catalog-contract",
        "path": "researcher/scripts/validate_authority_contract.py",
        "owns": [
            "standalone authority schema, registry, fixture, and semantic profile validation",
            "structural authority-policy closure",
            "authority evaluator-bundle identity",
            "authority conformance receipt validation",
        ],
    },
    {
        "id": "repository-inventory",
        "path": "researcher/scripts/build_inventory.py",
        "owns": [
            "identifier uniqueness",
            "cross-artifact references",
            "specification graph",
            "authority artifact parity and source binding",
            "live counts",
            "generated inventory",
        ],
    },
    {
        "id": "specification-lifecycle",
        "path": "researcher/scripts/validate_spec_lifecycle.py",
        "owns": [
            "base-aware specification status transitions",
            "accepted contract revision identity",
            "promoted revision predecessor authority",
            "terminal specification decisions",
        ],
    },
    {
        "id": "specification-development-plan",
        "path": "researcher/scripts/spec_program.py",
        "owns": [
            "non-authoritative exact-source planning coverage",
            "acceptance-criterion planning identity and dependency drift",
        ],
    },
    {
        "id": "export-policy",
        "path": "researcher/scripts/validate_export.py",
        "owns": ["classification export routes", "public projections", "staged export closure"],
    },
    {
        "id": "public-repository-boundary",
        "path": "researcher/scripts/validate_public_repo.py",
        "owns": [
            "tracked local paths",
            "private runtime and run-init staging roots",
            "credential filenames",
            "private-key material",
        ],
    },
    {
        "id": "schema-contract",
        "path": "researcher/scripts/validate_schemas.py",
        "owns": ["schema registry", "canonical records", "legacy adapters", "conformance evidence"],
    },
    {
        "id": "platform-compatibility",
        "path": "researcher/scripts/validate_platform_compat.py",
        "owns": ["Agent Skills format", "platform install layouts", "reference validator"],
    },
    {
        "id": "repository-structure",
        "path": "researcher/scripts/validate_repo.py",
        "owns": ["content invariants", "rubric math", "source evaluations", "run fixtures"],
    },
    {
        "id": "skill-health",
        "path": "researcher/scripts/skill_health.py",
        "owns": ["skill body quality score"],
    },
    {
        "id": "activation-cases",
        "path": "researcher/scripts/check_activation_cases.py",
        "owns": ["activation boundary smoke tests"],
    },
    {
        "id": "deterministic-benchmark-catalog",
        "path": "researcher/scripts/run_benchmarks.py",
        "owns": [
            "repository and activation gate invocation",
            "adversarial scenario catalog consistency",
            "explicit non-execution accounting",
        ],
    },
    {
        "id": "router-report",
        "path": "researcher/scripts/render_router_report.py",
        "owns": [
            "router outcome taxonomy",
            "accuracy denominators",
            "deterministic confidence intervals",
            "published router report rendering",
        ],
    },
)

SUPERVISED_LOOP_COMPONENTS = (
    {
        "id": "loop-common",
        "path": "researcher/scripts/loop_common.py",
        "owns": "legacy queue locking, atomic local writes with typed uncertain-durability failures, and run discovery helpers",
    },
    {
        "id": "loop-discovery",
        "path": "researcher/scripts/loop_discover.py",
        "owns": "manual-seed normalization and bounded inbox admission",
    },
    {
        "id": "loop-step",
        "path": "researcher/scripts/loop_step.py",
        "owns": "one-step supervised bookkeeping with network retrieval disabled",
    },
    {
        "id": "loop-daily",
        "path": "researcher/scripts/loop_daily.py",
        "owns": "reduced local health profile and daily snapshot",
    },
    {
        "id": "loop-status",
        "path": "researcher/scripts/loop_status.py",
        "owns": "human-facing legacy-loop status projection",
    },
    {
        "id": "research-run-state",
        "path": "researcher/scripts/research_loop.py",
        "owns": "supervised research-run commands and legal state transitions",
    },
    {
        "id": "research-run-readiness",
        "path": "researcher/scripts/validate_run.py",
        "owns": "single-run structure, history, and publication-readiness validation",
    },
)

SUPERVISED_LOOP_TEST_FILES = (
    "researcher/scripts/tests/test_benchmark_catalog.py",
    "researcher/scripts/tests/test_build_inventory.py",
    "researcher/scripts/tests/test_launchd_safety.py",
    "researcher/scripts/tests/test_loop_common.py",
    "researcher/scripts/tests/test_loop_common_locking.py",
    "researcher/scripts/tests/test_loop_daily_fail_closed.py",
    "researcher/scripts/tests/test_loop_discover.py",
    "researcher/scripts/tests/test_loop_import_provenance.py",
    "researcher/scripts/tests/test_loop_lock_capability.py",
    "researcher/scripts/tests/test_loop_status_fail_closed.py",
    "researcher/scripts/tests/test_loop_step.py",
    "researcher/scripts/tests/test_public_repo.py",
    "researcher/scripts/tests/test_research_loop_state_machine.py",
    "researcher/scripts/tests/test_validate_run_hardening.py",
)
SUPERVISED_LOOP_TEST_PREFIXES = (
    "test_benchmark_catalog",
    "test_build_inventory",
    "test_launchd",
    "test_loop",
    "test_public_repo",
    "test_research_loop",
    "test_validate_run",
)

SUPERVISED_SCRIPT_FILES = (
    "researcher/scripts/__init__.py",
    "researcher/scripts/adversarial_scenarios.py",
    "researcher/scripts/artifact_store.py",
    "researcher/scripts/build_inventory.py",
    "researcher/scripts/check_activation_cases.py",
    "researcher/scripts/compare_skill_revisions.py",
    "researcher/scripts/export_policy.py",
    "researcher/scripts/event_store.py",
    "researcher/scripts/governance_policy.py",
    "researcher/scripts/local_rehearsal.py",
    "researcher/scripts/local_scheduler.py",
    "researcher/scripts/loop_common.py",
    "researcher/scripts/loop_daily.py",
    "researcher/scripts/loop_discover.py",
    "researcher/scripts/loop_status.py",
    "researcher/scripts/loop_step.py",
    "researcher/scripts/migrate_legacy.py",
    "researcher/scripts/novelty_check.py",
    "researcher/scripts/prompt_compiler.py",
    "researcher/scripts/render_router_report.py",
    "researcher/scripts/run_projector.py",
    "researcher/scripts/research_loop.py",
    "researcher/scripts/research_context.py",
    "researcher/scripts/research_articles.py",
    "researcher/scripts/research_articles_large.py",
    "researcher/scripts/research_discovery.py",
    "researcher/scripts/research_evidence.py",
    "researcher/scripts/research_evolution.py",
    "researcher/scripts/research_experiment.py",
    "researcher/scripts/research_pipeline.py",
    "researcher/scripts/research_sourcing.py",
    "researcher/scripts/run_benchmarks.py",
    "researcher/scripts/schema_contract.py",
    "researcher/scripts/skill_frontmatter.py",
    "researcher/scripts/skill_health.py",
    "researcher/scripts/source_connectors.py",
    "researcher/scripts/source_search.py",
    "researcher/scripts/spec_program.py",
    "researcher/scripts/tests/__init__.py",
    "researcher/scripts/tests/test_adversarial_scenarios.py",
    "researcher/scripts/tests/test_artifact_store.py",
    "researcher/scripts/tests/test_benchmark_catalog.py",
    "researcher/scripts/tests/test_build_inventory.py",
    "researcher/scripts/tests/test_export_policy.py",
    "researcher/scripts/tests/test_deliberative_writing_safety.py",
    "researcher/scripts/tests/test_event_store.py",
    "researcher/scripts/tests/test_example_api_budget.py",
    "researcher/scripts/tests/test_example_calculator.py",
    "researcher/scripts/tests/test_install_safety.py",
    "researcher/scripts/tests/test_judge_agent_frontmatter.py",
    "researcher/scripts/tests/test_governance_policy.py",
    "researcher/scripts/tests/test_launchd_safety.py",
    "researcher/scripts/tests/test_hosted_agents_sandbox_manager.py",
    "researcher/scripts/tests/test_local_rehearsal.py",
    "researcher/scripts/tests/test_local_scheduler.py",
    "researcher/scripts/tests/test_loop_common.py",
    "researcher/scripts/tests/test_loop_common_locking.py",
    "researcher/scripts/tests/test_loop_daily_fail_closed.py",
    "researcher/scripts/tests/test_loop_discover.py",
    "researcher/scripts/tests/test_loop_import_provenance.py",
    "researcher/scripts/tests/test_loop_lock_capability.py",
    "researcher/scripts/tests/test_loop_status_fail_closed.py",
    "researcher/scripts/tests/test_loop_step.py",
    "researcher/scripts/tests/test_public_repo.py",
    "researcher/scripts/tests/test_pipeline_template_paths.py",
    "researcher/scripts/tests/test_product_readiness.py",
    "researcher/scripts/tests/test_validate_pr_package.py",
    "researcher/scripts/tests/test_prompt_compiler.py",
    "researcher/scripts/tests/test_render_router_report.py",
    "researcher/scripts/tests/test_research_loop_state_machine.py",
    "researcher/scripts/tests/test_research_context.py",
    "researcher/scripts/tests/test_research_articles.py",
    "researcher/scripts/tests/test_research_articles_large.py",
    "researcher/scripts/tests/test_research_discovery.py",
    "researcher/scripts/tests/test_research_campaign_replay.py",
    "researcher/scripts/tests/test_research_evidence.py",
    "researcher/scripts/tests/test_research_evolution.py",
    "researcher/scripts/tests/test_research_experiment.py",
    "researcher/scripts/tests/test_research_pipeline.py",
    "researcher/scripts/tests/test_research_pipeline_adversarial.py",
    "researcher/scripts/tests/test_schema_contract.py",
    "researcher/scripts/tests/test_skill_frontmatter.py",
    "researcher/scripts/tests/test_source_connectors.py",
    "researcher/scripts/tests/test_source_search.py",
    "researcher/scripts/tests/test_source_sourcing.py",
    "researcher/scripts/tests/test_research_sourcing.py",
    "researcher/scripts/tests/test_spec_lifecycle.py",
    "researcher/scripts/tests/test_spec_program.py",
    "researcher/scripts/tests/test_validate_run_hardening.py",
    "researcher/scripts/validate_authority_contract.py",
    "researcher/scripts/validate_export.py",
    "researcher/scripts/validate_event_journal.py",
    "researcher/scripts/validate_governance.py",
    "researcher/scripts/validate_platform_compat.py",
    "researcher/scripts/validate_product_readiness.py",
    "researcher/scripts/validate_pr_package.py",
    "researcher/scripts/validate_public_repo.py",
    "researcher/scripts/validate_repo.py",
    "researcher/scripts/validate_run.py",
    "researcher/scripts/validate_schemas.py",
    "researcher/scripts/validate_spec_lifecycle.py",
)
SUPERVISED_ORCHESTRATION_FILES = (
    "researcher/orchestration/config.json",
    "researcher/orchestration/launchd/com.context-engineering.loop-daily.plist",
    "researcher/orchestration/launchd/com.context-engineering.loop-discover.plist",
    "researcher/orchestration/launchd/com.context-engineering.loop-step.plist",
    "researcher/orchestration/launchd/install.sh",
    "researcher/orchestration/launchd/run-loop-daily.sh",
    "researcher/orchestration/launchd/run-loop-discover.sh",
    "researcher/orchestration/launchd/run-loop-step.sh",
    "researcher/orchestration/launchd/uninstall.sh",
    "researcher/orchestration/prompts/README.md",
    "researcher/orchestration/prompts/attempt-manifest.template.md",
    "researcher/orchestration/prompts/fresh-verifier-brief.md",
    "researcher/orchestration/prompts/organization-root-brief.md",
    "researcher/orchestration/prompts/resume-brief.template.md",
    "researcher/orchestration/prompts/spec-work-brief.template.md",
)
SUPERVISED_TEMPLATE_FILES = (
    "researcher/templates/mechanism-proposal.jsonl",
    "researcher/templates/research-thread.md",
    "researcher/templates/skill-proposal.md",
    "researcher/templates/source-evaluation.json",
)
SUPERVISED_DISCOVERY_FILES = ("researcher/discovery/manual-seed.jsonl",)
SUPERVISED_CLOSED_ROOTS = (
    ("researcher/scripts", SUPERVISED_SCRIPT_FILES, frozenset({"__pycache__"})),
    ("researcher/orchestration", SUPERVISED_ORCHESTRATION_FILES, frozenset()),
    ("researcher/templates", SUPERVISED_TEMPLATE_FILES, frozenset()),
    ("researcher/discovery", SUPERVISED_DISCOVERY_FILES, frozenset()),
)
SUPERVISED_PACKAGE_INITIALIZERS = (
    "researcher/__init__.py",
    "researcher/scripts/__init__.py",
)

REFERENCE_RUN_FILES = (
    "THREAD.md",
    "proposals/mechanism-proposal.jsonl",
    "proposals/skill-proposal.md",
    "reports/closure.json",
    "reports/validation-report.json",
    "reports/validation-report.md",
    "run-state.json",
    "sources/evaluations/source-evaluation-draft.json",
    "sources/evidence/deep-research-summary.md",
    "sources/evidence/raw/autonomous-research-frameworks-executable.json",
    "sources/evidence/raw/autonomous-research-harness-evolution.json",
    "sources/queue.jsonl",
)
REFERENCE_RUN_DIRECTORIES = (
    "proposals",
    "reports",
    "sources",
    "sources/evaluations",
    "sources/evidence",
    "sources/evidence/raw",
)

LIVE_DOCUMENT_LINKS = {
    "README.md": "researcher/generated/corpus-summary.md",
    "AGENTS.md": "researcher/generated/corpus-summary.md",
    "CLAUDE.md": "researcher/generated/corpus-summary.md",
    "researcher/README.md": "generated/corpus-summary.md",
}


class InventoryError(ValueError):
    """Raised for structural errors that prevent deterministic parsing."""


class DuplicateKeyError(InventoryError):
    pass


@dataclass(frozen=True)
class Finding:
    code: str
    path: str
    artifact_id: str | None
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def canonical_json_bytes(value: Any) -> bytes:
    """Canonical bytes for deterministic repository views.

    This is the repository's v1 sorted-key profile. SPEC-003 replaces it with
    a registered cross-language canonicalization profile for durable records.
    Inventory values are limited to strings, integers, booleans, null, lists,
    and objects, so JSON number edge cases cannot enter this view.
    """

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def pretty_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"


def sha256_bytes(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def record_digest(value: Any) -> str:
    return sha256_bytes(canonical_json_bytes(value))


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def parse_json_text(text: str) -> Any:
    return json.loads(text, object_pairs_hook=_reject_duplicate_keys)


def _strip_html_comments(text: str) -> tuple[str, bool]:
    """Remove CommonMark HTML comments and report an unclosed comment."""

    output: list[str] = []
    cursor = 0
    while True:
        start = text.find("<!--", cursor)
        if start < 0:
            output.append(text[cursor:])
            return "".join(output), False
        output.append(text[cursor:start])
        end = text.find("-->", start + 4)
        if end < 0:
            output.append("\n" * text[start:].count("\n"))
            return "".join(output), True
        comment = text[start : end + 3]
        output.append("\n" * comment.count("\n"))
        cursor = end + 3


def _is_fence_close(line: str, character: str, minimum_length: int) -> bool:
    return re.fullmatch(
        rf" {{0,3}}{re.escape(character)}{{{minimum_length},}}[ \t]*",
        line,
    ) is not None


def contains_raw_html_block(text: str) -> bool:
    """Return whether visible Markdown contains a raw HTML block opener."""

    visible_text, _ = _strip_html_comments(text)
    return any(RAW_HTML_BLOCK_START_RE.match(line) for line in visible_text.splitlines())


def markdown_level_two_sections(text: str) -> tuple[dict[str, list[list[str]]], bool]:
    """Return visible level-two sections and malformed comment/fence status."""

    sections: dict[str, list[list[str]]] = {}
    current: list[str] | None = None
    fence_character: str | None = None
    fence_length = 0
    visible_text, malformed_comment = _strip_html_comments(text)
    for line in visible_text.splitlines():
        if fence_character is not None:
            if current is not None:
                current.append(line)
            if _is_fence_close(line, fence_character, fence_length):
                fence_character = None
                fence_length = 0
            continue
        fence_match = FENCE_OPEN_RE.fullmatch(line)
        if fence_match is not None:
            if current is not None:
                current.append(line)
            fence = fence_match.group("fence")
            fence_character = fence[0]
            fence_length = len(fence)
            continue
        heading_match = LEVEL_TWO_HEADING_RE.fullmatch(line)
        if heading_match is not None:
            current = []
            sections.setdefault(heading_match.group("title"), []).append(current)
            continue
        if current is not None:
            current.append(line)
    return sections, malformed_comment or fence_character is not None


def visible_unfenced_lines(lines: Iterable[str]) -> list[str]:
    """Remove CommonMark fenced blocks from an already comment-free section."""

    visible: list[str] = []
    fence_character: str | None = None
    fence_length = 0
    for line in lines:
        if fence_character is not None:
            if _is_fence_close(line, fence_character, fence_length):
                fence_character = None
                fence_length = 0
            continue
        fence_match = FENCE_OPEN_RE.fullmatch(line)
        if fence_match is not None:
            fence = fence_match.group("fence")
            fence_character = fence[0]
            fence_length = len(fence)
            continue
        visible.append(line)
    return visible


def fenced_blocks(lines: Iterable[str], language: str) -> tuple[list[list[str]], bool]:
    """Extract complete fenced blocks with one exact language identifier."""

    blocks: list[list[str]] = []
    current: list[str] | None = None
    fence_character: str | None = None
    fence_length = 0
    selected = False
    for line in lines:
        if fence_character is not None:
            if _is_fence_close(line, fence_character, fence_length):
                if selected and current is not None:
                    blocks.append(current)
                current = None
                fence_character = None
                fence_length = 0
                selected = False
            elif selected and current is not None:
                current.append(line)
            continue
        fence_match = FENCE_OPEN_RE.fullmatch(line)
        if fence_match is None:
            continue
        fence = fence_match.group("fence")
        fence_character = fence[0]
        fence_length = len(fence)
        selected = fence_match.group("info").strip() == language
        current = [] if selected else None
    return blocks, fence_character is not None


def atomic_write_text(path: Path, text: str) -> None:
    """Flush and atomically replace one generated file in its target directory."""

    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        if hasattr(os, "O_DIRECTORY"):
            directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    except Exception:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        raise


class InventoryBuilder:
    def __init__(self, root: Path) -> None:
        # Keep the caller's lexical root as well as its canonical filesystem
        # identity. macOS commonly exposes /var as the /private/var symlink;
        # paths constructed from either spelling still need an in-root lexical
        # name without resolving the source itself and hiding a symlink.
        self.lexical_root = Path(os.path.abspath(root))
        self.root = self.lexical_root.resolve()
        self.findings: list[Finding] = []
        self.sources: dict[str, dict[str, Any]] = {}
        self._source_bytes: dict[str, bytes] = {}
        self.skill_names: set[str] = set()
        self.mechanisms: dict[str, dict[str, Any]] = {}
        self.claims: dict[str, dict[str, Any]] = {}
        self._authority_binding: AuthorityVocabularyBinding | None = None

    def add_finding(
        self,
        code: str,
        path: Path | str,
        message: str,
        artifact_id: str | None = None,
    ) -> None:
        self.findings.append(Finding(code, self.relative(path), artifact_id, message))

    def relative(self, path: Path | str) -> str:
        value = Path(path)
        if not value.is_absolute():
            normalized = PurePosixPath(str(value).replace("\\", "/"))
            if normalized.is_absolute() or ".." in normalized.parts:
                raise InventoryError(f"path escapes repository: {path}")
            return normalized.as_posix()
        # Preserve the lexical repository path here. add_source validates the
        # filesystem identity separately so an in-repository symlink is
        # reported against its lexical name instead of resolved away.
        lexical = Path(os.path.abspath(value))
        for candidate_root in (self.lexical_root, self.root):
            try:
                return lexical.relative_to(candidate_root).as_posix()
            except ValueError:
                continue
        raise InventoryError(f"path escapes repository: {path}")

    def add_source(self, path: Path) -> tuple[str, int]:
        relative = self.relative(path)
        cached = self._source_bytes.get(relative)
        if cached is not None:
            return sha256_bytes(cached), len(cached)
        components = PurePosixPath(relative).parts
        zero_digest = "sha256:" + "0" * 64
        if not components:
            self.add_finding("PATH_ESCAPE", relative, "source path is empty")
            return zero_digest, 0

        nofollow = getattr(os, "O_NOFOLLOW", 0)
        nonblock = getattr(os, "O_NONBLOCK", 0)
        directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | nofollow
        directory_fd: int | None = None
        directory_fds: list[int] = []
        directory_identities: list[tuple[Path, tuple[int, int]]] = []
        verification_directory_fds: list[int] = []
        source_fd: int | None = None
        verification_source_fd: int | None = None
        try:
            root_info = os.lstat(self.root)
            if stat.S_ISLNK(root_info.st_mode) or not stat.S_ISDIR(root_info.st_mode):
                raise InventoryError("trusted repository root is not a real directory")
            directory_fd = os.open(self.root, directory_flags)
            directory_fds.append(directory_fd)
            opened_root = os.fstat(directory_fd)
            if (root_info.st_dev, root_info.st_ino) != (
                opened_root.st_dev,
                opened_root.st_ino,
            ):
                raise InventoryError("repository root changed while opening source")
            directory_identities.append(
                (self.root, (opened_root.st_dev, opened_root.st_ino))
            )

            lexical = self.root
            for component in components[:-1]:
                lexical /= component
                lexical_info = os.lstat(lexical)
                if stat.S_ISLNK(lexical_info.st_mode) or not stat.S_ISDIR(
                    lexical_info.st_mode
                ):
                    raise InventoryError(
                        f"source ancestor is not a real directory: {component}"
                    )
                child_fd = os.open(component, directory_flags, dir_fd=directory_fd)
                opened_info = os.fstat(child_fd)
                if (
                    not stat.S_ISDIR(opened_info.st_mode)
                    or (lexical_info.st_dev, lexical_info.st_ino)
                    != (opened_info.st_dev, opened_info.st_ino)
                ):
                    os.close(child_fd)
                    raise InventoryError(
                        f"source ancestor changed while opening: {component}"
                    )
                directory_fd = child_fd
                directory_fds.append(child_fd)
                directory_identities.append(
                    (lexical, (opened_info.st_dev, opened_info.st_ino))
                )

            lexical_final = lexical / components[-1]
            lexical_info = os.lstat(lexical_final)
            if (
                stat.S_ISLNK(lexical_info.st_mode)
                or not stat.S_ISREG(lexical_info.st_mode)
                or lexical_info.st_nlink != 1
            ):
                raise InventoryError(
                    "source must be a real single-link regular file"
                )
            source_fd = os.open(
                components[-1],
                os.O_RDONLY | nofollow | nonblock,
                dir_fd=directory_fd,
            )
            before = os.fstat(source_fd)
            if (
                not stat.S_ISREG(before.st_mode)
                or before.st_nlink != 1
                or (lexical_info.st_dev, lexical_info.st_ino)
                != (before.st_dev, before.st_ino)
            ):
                raise InventoryError("source identity changed while opening")
            chunks: list[bytes] = []
            while True:
                chunk = os.read(source_fd, 1024 * 1024)
                if not chunk:
                    break
                chunks.append(chunk)
            after = os.fstat(source_fd)
            final_entry = os.stat(
                components[-1], dir_fd=directory_fd, follow_symlinks=False
            )
            identity_before = (
                before.st_dev,
                before.st_ino,
                before.st_size,
                before.st_mtime_ns,
                before.st_ctime_ns,
            )
            identity_after = (
                after.st_dev,
                after.st_ino,
                after.st_size,
                after.st_mtime_ns,
                after.st_ctime_ns,
            )
            if (
                identity_before != identity_after
                or not stat.S_ISREG(after.st_mode)
                or after.st_nlink != 1
                or (after.st_dev, after.st_ino)
                != (final_entry.st_dev, final_entry.st_ino)
                or not stat.S_ISREG(final_entry.st_mode)
                or final_entry.st_nlink != 1
            ):
                raise InventoryError("source changed while it was being hashed")
            body = b"".join(chunks)
            if len(body) != after.st_size:
                raise InventoryError("source byte count differs from stable file size")

            # A stable source descriptor is not sufficient: an ancestor can be
            # renamed away and replaced while the old descriptor remains valid.
            # Reopen the complete lexical chain and require every current name
            # to still designate the exact directory identity opened before the
            # read. Keep the verification descriptors open until acceptance.
            verification_parent_fd: int | None = None
            for index, (lexical_directory, expected_identity) in enumerate(
                directory_identities
            ):
                current_info = os.lstat(lexical_directory)
                if stat.S_ISLNK(current_info.st_mode) or not stat.S_ISDIR(
                    current_info.st_mode
                ):
                    raise InventoryError(
                        "source ancestor became unsafe while it was being hashed"
                    )
                if index == 0:
                    reopened_fd = os.open(lexical_directory, directory_flags)
                else:
                    reopened_fd = os.open(
                        components[index - 1],
                        directory_flags,
                        dir_fd=verification_parent_fd,
                    )
                verification_directory_fds.append(reopened_fd)
                reopened_info = os.fstat(reopened_fd)
                current_identity = (current_info.st_dev, current_info.st_ino)
                reopened_identity = (reopened_info.st_dev, reopened_info.st_ino)
                if (
                    not stat.S_ISDIR(reopened_info.st_mode)
                    or current_identity != expected_identity
                    or reopened_identity != expected_identity
                ):
                    raise InventoryError(
                        "source ancestor identity changed while it was being hashed"
                    )
                verification_parent_fd = reopened_fd

            current_final_info = os.lstat(self.root.joinpath(*components))
            verification_source_fd = os.open(
                components[-1],
                os.O_RDONLY | nofollow | nonblock,
                dir_fd=verification_parent_fd,
            )
            reopened_final = os.fstat(verification_source_fd)
            reopened_identity = (
                reopened_final.st_dev,
                reopened_final.st_ino,
                reopened_final.st_size,
                reopened_final.st_mtime_ns,
                reopened_final.st_ctime_ns,
            )
            settled = os.fstat(source_fd)
            settled_identity = (
                settled.st_dev,
                settled.st_ino,
                settled.st_size,
                settled.st_mtime_ns,
                settled.st_ctime_ns,
            )
            if (
                stat.S_ISLNK(current_final_info.st_mode)
                or not stat.S_ISREG(current_final_info.st_mode)
                or current_final_info.st_nlink != 1
                or not stat.S_ISREG(reopened_final.st_mode)
                or reopened_final.st_nlink != 1
                or (current_final_info.st_dev, current_final_info.st_ino)
                != (reopened_final.st_dev, reopened_final.st_ino)
                or reopened_identity != identity_after
                or settled_identity != identity_after
            ):
                raise InventoryError(
                    "source lexical identity changed while it was being hashed"
                )
        except (InventoryError, OSError) as exc:
            self.add_finding(
                "PATH_ESCAPE",
                relative,
                f"source is missing or has an unsafe filesystem identity: {exc}",
            )
            return zero_digest, 0
        finally:
            if verification_source_fd is not None:
                os.close(verification_source_fd)
            if source_fd is not None:
                os.close(source_fd)
            for opened_fd in reversed(verification_directory_fds):
                os.close(opened_fd)
            for opened_fd in reversed(directory_fds):
                os.close(opened_fd)
        digest = sha256_bytes(body)
        self._source_bytes[relative] = body
        self.sources[relative] = {"path": relative, "digest": digest, "size_bytes": len(body)}
        return digest, len(body)

    def read_source_bytes(self, path: Path) -> bytes:
        """Return the exact byte snapshot recorded by ``add_source``."""

        relative = self.relative(path)
        self.add_source(path)
        try:
            return self._source_bytes[relative]
        except KeyError as exc:
            raise InventoryError(f"source snapshot is unavailable: {relative}") from exc

    def read_source_text(self, path: Path) -> str:
        return self.read_source_bytes(path).decode("utf-8")

    def load_json(self, path: Path) -> Any | None:
        try:
            return parse_json_text(self.read_source_text(path))
        except (
            OSError,
            UnicodeError,
            json.JSONDecodeError,
            DuplicateKeyError,
            InventoryError,
        ) as exc:
            self.add_finding("PARSE_ERROR", path, str(exc))
            return None

    def load_jsonl(self, path: Path) -> list[tuple[int, dict[str, Any], str]]:
        try:
            lines = self.read_source_text(path).splitlines()
        except (OSError, UnicodeError, InventoryError) as exc:
            self.add_finding("PARSE_ERROR", path, str(exc))
            return []
        records: list[tuple[int, dict[str, Any], str]] = []
        for line_number, raw in enumerate(lines, start=1):
            if not raw.strip():
                continue
            try:
                value = parse_json_text(raw)
            except (json.JSONDecodeError, DuplicateKeyError) as exc:
                self.add_finding("PARSE_ERROR", path, f"line {line_number}: {exc}")
                continue
            if not isinstance(value, dict):
                self.add_finding("PARSE_ERROR", path, f"line {line_number}: expected object")
                continue
            records.append((line_number, value, record_digest(value)))
        return records

    @staticmethod
    def _category(owner: str, records: Iterable[dict[str, Any]], **extra: Any) -> dict[str, Any]:
        materialized = list(records)
        return {"owner": owner, "count": len(materialized), "records": materialized, **extra}

    def build(self) -> dict[str, Any]:
        skills = self.build_skills()
        mechanisms = self.build_mechanisms()
        claims = self.build_claims()
        ledgers = self.build_ledgers()
        corpus, relationships = self.build_corpus_index()
        activation = self.build_activation_cases()
        relationships["skill_activation_cases"] = sorted(
            (
                {"skill_id": record["expected_primary_skill"], "case_id": record["id"]}
                for record in activation["records"]
            ),
            key=lambda item: (item["skill_id"], item["case_id"]),
        )
        router = self.build_router_prompts()
        scenarios, goldens = self.build_adversarial()
        effectiveness = self.build_effectiveness_tasks()
        benchmark_runners = self.build_benchmark_runners()
        examples = self.build_examples()
        manifests = self.build_manifests()
        validators = self.build_validators()
        supervised_loop = self.build_supervised_loop()
        schemas = self.build_schemas()
        export_contracts = self.build_export_contracts()
        schema_contracts = self.build_schema_contracts()
        orchestration_briefs = self.build_orchestration_briefs()
        specifications = self.build_specifications()
        authority_contracts = self.build_authority_contracts()
        architecture_decisions = self.build_architecture_decisions(
            {record["id"] for record in specifications["records"]}
        )
        decisions_by_id = {
            record["id"]: record for record in architecture_decisions["records"]
        }
        for record in specifications["records"]:
            adoption_decision = record.get("adoption_decision")
            if adoption_decision is None:
                continue
            decision = decisions_by_id.get(adoption_decision)
            if decision is None:
                self.add_finding(
                    "DANGLING_SPEC_ADOPTION_DECISION",
                    self.root / record["path"],
                    f"adoption decision does not exist: {adoption_decision}",
                    record["id"],
                )
                continue
            if decision["status"] != "accepted":
                self.add_finding(
                    "UNACCEPTED_SPEC_ADOPTION_DECISION",
                    self.root / record["path"],
                    f"adoption decision must be accepted: {adoption_decision}",
                    record["id"],
                )
            if record["id"] not in decision["specifications"]:
                self.add_finding(
                    "OUT_OF_SCOPE_SPEC_ADOPTION_DECISION",
                    self.root / record["path"],
                    f"{adoption_decision} does not scope {record['id']}",
                    record["id"],
                )
        for record in specifications["records"]:
            lifecycle_decision = record.get("lifecycle_decision")
            if lifecycle_decision is None:
                continue
            decision = decisions_by_id.get(lifecycle_decision)
            if decision is None:
                self.add_finding(
                    "DANGLING_SPEC_LIFECYCLE_DECISION",
                    self.root / record["path"],
                    f"lifecycle decision does not exist: {lifecycle_decision}",
                    record["id"],
                )
                continue
            if decision["status"] != "accepted":
                self.add_finding(
                    "UNACCEPTED_SPEC_LIFECYCLE_DECISION",
                    self.root / record["path"],
                    f"lifecycle decision must be accepted: {lifecycle_decision}",
                    record["id"],
                )
            if record["id"] not in decision["specifications"]:
                self.add_finding(
                    "OUT_OF_SCOPE_SPEC_LIFECYCLE_DECISION",
                    self.root / record["path"],
                    f"{lifecycle_decision} does not scope {record['id']}",
                    record["id"],
                )
            if record["status"] in SPEC_TERMINAL_STATUSES:
                expected_target = (
                    record.get("replacement")
                    if record["status"] in {"amended", "superseded"}
                    else "none"
                )
                expected_transition = (
                    f"{record['id']}@{record['revision']} -> "
                    f"{record['status']} -> {expected_target}"
                )
                if decision.get("lifecycle_transition") != expected_transition:
                    self.add_finding(
                        "SPEC_LIFECYCLE_DECISION_MISMATCH",
                        self.root / record["path"],
                        f"{lifecycle_decision} must bind exact transition "
                        f"{expected_transition!r}",
                        record["id"],
                    )
        self.validate_live_document_links()

        artifacts = {
            "skills": skills,
            "mechanisms": mechanisms,
            "claims": claims,
            "mechanism_ledgers": ledgers,
            "corpus_index": corpus,
            "activation_cases": activation,
            "router_prompts": router,
            "adversarial_scenarios": scenarios,
            "adversarial_goldens": goldens,
            "effectiveness_tasks": effectiveness,
            "benchmark_runners": benchmark_runners,
            "examples": examples,
            "manifests": manifests,
            "validators": validators,
            "supervised_loop": supervised_loop,
            "schemas": schemas,
            "export_contracts": export_contracts,
            "schema_contracts": schema_contracts,
            "authority_contracts": authority_contracts,
            "orchestration_briefs": orchestration_briefs,
            "specifications": specifications,
            "architecture_decisions": architecture_decisions,
        }
        source_records = sorted(self.sources.values(), key=lambda item: item["path"])
        source_tree_digest = sha256_bytes(
            canonical_json_bytes({"schema_version": SCHEMA_VERSION, "sources": source_records})
        )
        unresolved = sorted(
            (finding.to_dict() for finding in self.findings),
            key=lambda item: (item["code"], item["path"], item["artifact_id"] or "", item["message"]),
        )
        return {
            "schema_version": SCHEMA_VERSION,
            "repository_revision": {
                "kind": "canonical_source_tree",
                "digest": source_tree_digest,
                "git_commit_excluded_to_avoid_self_reference": True,
            },
            "source_tree_digest": source_tree_digest,
            "sources": source_records,
            "artifacts": artifacts,
            "relationships": relationships,
            "compatibility": {
                "plugin_versions": manifests["versions"],
                "manifest_skill_sets": manifests["skill_sets"],
                "benchmark_runner": {
                    "router": benchmark_runners["status"]["router"],
                    "effectiveness": benchmark_runners["status"]["effectiveness"],
                    "paid_results": "runtime_or_published_only",
                },
                "supervised_loop": supervised_loop["status"],
                "historical_reports_are_snapshots": True,
            },
            "validator_ownership": validators["records"],
            "unresolved_references": unresolved,
        }

    def build_skills(self) -> dict[str, Any]:
        records: list[dict[str, Any]] = []
        skills_dir = self.root / "skills"
        if not skills_dir.exists():
            self.add_finding("PARSE_ERROR", skills_dir, "skills directory is missing")
            return self._category("skills/*/SKILL.md", records)
        for skill_dir in sorted(path for path in skills_dir.iterdir() if path.is_dir()):
            skill_file = skill_dir / "SKILL.md"
            if not skill_file.exists():
                self.add_finding("PARSE_ERROR", skill_file, "SKILL.md is missing", skill_dir.name)
                continue
            digest, _ = self.add_source(skill_file)
            try:
                frontmatter, issues = parse_frontmatter(
                    self.read_source_text(skill_file)
                )
            except (OSError, UnicodeError, InventoryError) as exc:
                self.add_finding("PARSE_ERROR", skill_file, str(exc), skill_dir.name)
                continue
            for issue in issues:
                self.add_finding("PARSE_ERROR", skill_file, issue, skill_dir.name)
            name = frontmatter.get("name")
            if not isinstance(name, str) or not name:
                name = skill_dir.name
            if name != skill_dir.name:
                self.add_finding(
                    "SKILL_PATH_MISMATCH",
                    skill_file,
                    f"frontmatter name {name!r} does not match directory {skill_dir.name!r}",
                    str(name),
                )
            if name in self.skill_names:
                self.add_finding("DUPLICATE_SKILL_ID", skill_file, "duplicate skill identifier", name)
            self.skill_names.add(name)
            records.append({"id": name, "path": self.relative(skill_file), "digest": digest})
        return self._category("skills/*/SKILL.md", sorted(records, key=lambda item: item["id"]))

    def build_mechanisms(self) -> dict[str, Any]:
        path = self.root / "researcher" / "mechanisms" / "registry.jsonl"
        records: list[dict[str, Any]] = []
        for line_number, value, digest in self.load_jsonl(path):
            mechanism_id = value.get("mechanism_id")
            if not isinstance(mechanism_id, str) or not mechanism_id:
                self.add_finding("PARSE_ERROR", path, f"line {line_number}: mechanism_id is required")
                continue
            if mechanism_id in self.mechanisms:
                self.add_finding(
                    "DUPLICATE_MECHANISM_ID", path, f"duplicate at line {line_number}", mechanism_id
                )
            owner = value.get("owning_skill")
            if owner not in self.skill_names:
                self.add_finding(
                    "DANGLING_SKILL", path, f"unknown owning_skill {owner!r}", mechanism_id
                )
            self.mechanisms[mechanism_id] = value
            records.append(
                {
                    "id": mechanism_id,
                    "owning_skill": owner,
                    "status": value.get("status"),
                    "line": line_number,
                    "digest": digest,
                }
            )
        return self._category(
            "researcher/mechanisms/registry.jsonl", sorted(records, key=lambda item: item["id"])
        )

    def build_claims(self) -> dict[str, Any]:
        path = self.root / "researcher" / "claims" / "index.jsonl"
        records: list[dict[str, Any]] = []
        for line_number, value, digest in self.load_jsonl(path):
            claim_id = value.get("claim_id")
            if not isinstance(claim_id, str) or not claim_id:
                self.add_finding("PARSE_ERROR", path, f"line {line_number}: claim_id is required")
                continue
            if claim_id in self.claims:
                self.add_finding("DUPLICATE_CLAIM_ID", path, f"duplicate at line {line_number}", claim_id)
            owner = value.get("owning_skill")
            if owner not in self.skill_names:
                self.add_finding("DANGLING_SKILL", path, f"unknown owning_skill {owner!r}", claim_id)
            self.claims[claim_id] = value
            records.append(
                {
                    "id": claim_id,
                    "owning_skill": owner,
                    "volatility": value.get("volatility"),
                    "line": line_number,
                    "digest": digest,
                }
            )
        return self._category(
            "researcher/claims/index.jsonl", sorted(records, key=lambda item: item["id"])
        )

    def build_ledgers(self) -> dict[str, Any]:
        ledger_dir = self.root / "researcher" / "mechanisms" / "ledgers"
        accepted_path = ledger_dir / "accepted.jsonl"
        rejected_path = ledger_dir / "rejected.jsonl"
        accepted = self.load_jsonl(accepted_path)
        rejected = self.load_jsonl(rejected_path)
        records: list[dict[str, Any]] = []
        accepted_ids: set[str] = set()
        durable_provenance: set[str] = set()
        superseded_lines = {
            value.get("supersedes_legacy_line")
            for _, value, _ in accepted
            if isinstance(value.get("supersedes_legacy_line"), int)
        }
        seen_event_ids: set[str] = set()
        for ledger_name, path, entries in (
            ("accepted", accepted_path, accepted),
            ("rejected", rejected_path, rejected),
        ):
            for line_number, value, digest in entries:
                mechanism_id = value.get("mechanism_id")
                event_id = value.get("event_id")
                if isinstance(event_id, str):
                    if event_id in seen_event_ids:
                        self.add_finding(
                            "DUPLICATE_LEDGER_EVENT_ID", path, f"duplicate event at line {line_number}", event_id
                        )
                    seen_event_ids.add(event_id)
                if not isinstance(mechanism_id, str) or not mechanism_id:
                    self.add_finding("PARSE_ERROR", path, f"line {line_number}: mechanism_id is required")
                    continue
                if ledger_name == "accepted":
                    accepted_ids.add(mechanism_id)
                    if mechanism_id not in self.mechanisms:
                        self.add_finding(
                            "ORPHAN_ACCEPTED_LEDGER_EVENT", path, "mechanism is absent from registry", mechanism_id
                        )
                    elif self.mechanisms[mechanism_id].get("status") != "accepted":
                        self.add_finding(
                            "LEDGER_STATUS_MISMATCH", path, "accepted ledger disagrees with registry", mechanism_id
                        )
                    source = value.get("source") or value.get("source_path")
                    source_exists = isinstance(source, str) and (self.root / source).exists()
                    has_commit = isinstance(value.get("source_commit"), str) and bool(value["source_commit"])
                    if source_exists and (value.get("event_type") is None or has_commit):
                        durable_provenance.add(mechanism_id)
                    if isinstance(value.get("run_dir"), str) and line_number not in superseded_lines:
                        run_path = self.root / value["run_dir"]
                        if not run_path.exists():
                            self.add_finding(
                                "DANGLING_LEDGER_RUN",
                                path,
                                f"line {line_number}: run_dir is unavailable",
                                mechanism_id,
                            )
                records.append(
                    {
                        "ledger": ledger_name,
                        "line": line_number,
                        "event_id": event_id,
                        "mechanism_id": mechanism_id,
                        "event_type": value.get("event_type", "legacy"),
                        "digest": digest,
                    }
                )
        for mechanism_id, mechanism in sorted(self.mechanisms.items()):
            if mechanism.get("status") == "accepted" and mechanism_id not in accepted_ids:
                self.add_finding(
                    "MISSING_ACCEPTED_LEDGER_EVENT",
                    accepted_path,
                    "accepted registry mechanism has no accepted-ledger event",
                    mechanism_id,
                )
            if mechanism.get("status") == "accepted" and mechanism_id not in durable_provenance:
                self.add_finding(
                    "DANGLING_LEDGER_SOURCE",
                    accepted_path,
                    "accepted mechanism has no durable public provenance event",
                    mechanism_id,
                )
        return self._category(
            "researcher/mechanisms/ledgers/*.jsonl",
            records,
            accepted_event_count=len(accepted),
            rejected_event_count=len(rejected),
            accepted_mechanism_count=len(accepted_ids),
        )

    def build_corpus_index(self) -> tuple[dict[str, Any], dict[str, Any]]:
        path = self.root / "researcher" / "corpus" / "index.json"
        value = self.load_json(path)
        records: list[dict[str, Any]] = []
        mechanism_relations: list[dict[str, str]] = []
        claim_relations: list[dict[str, str]] = []
        indexed_skills: set[str] = set()
        indexed_mechanisms: set[str] = set()
        indexed_claims: set[str] = set()
        if not isinstance(value, dict) or not isinstance(value.get("skills"), list):
            self.add_finding("UNKNOWN_SCHEMA", path, "corpus index must contain a skills list")
            return self._category("researcher/corpus/index.json", records), {
                "skill_mechanisms": [],
                "skill_claims": [],
                "skill_activation_cases": [],
            }
        for item in value["skills"]:
            if not isinstance(item, dict):
                self.add_finding("UNKNOWN_SCHEMA", path, "skill entry must be an object")
                continue
            name = item.get("name")
            if not isinstance(name, str) or not name:
                self.add_finding("UNKNOWN_SCHEMA", path, "skill entry is missing name")
                continue
            if name in indexed_skills:
                self.add_finding("DUPLICATE_SKILL_ID", path, "duplicate corpus skill", name)
            indexed_skills.add(name)
            if name not in self.skill_names:
                self.add_finding("DANGLING_SKILL", path, "indexed skill is not published", name)
            expected_path = f"skills/{name}/SKILL.md"
            if item.get("path") != expected_path:
                self.add_finding(
                    "SKILL_PATH_MISMATCH", path, f"expected {expected_path}, got {item.get('path')}", name
                )
            mechanism_ids = item.get("mechanism_ids", [])
            claim_ids = item.get("claim_ids", [])
            if not isinstance(mechanism_ids, list) or not isinstance(claim_ids, list):
                self.add_finding("UNKNOWN_SCHEMA", path, "mechanism_ids and claim_ids must be lists", name)
                continue
            for mechanism_id in mechanism_ids:
                if mechanism_id not in self.mechanisms:
                    self.add_finding(
                        "DANGLING_MECHANISM", path, "unknown mechanism reference", str(mechanism_id)
                    )
                    continue
                indexed_mechanisms.add(mechanism_id)
                owner = self.mechanisms[mechanism_id].get("owning_skill")
                if owner != name:
                    self.add_finding(
                        "MECHANISM_OWNER_MISMATCH",
                        path,
                        f"registry owner is {owner!r}, index consumer is {name!r}",
                        mechanism_id,
                    )
                mechanism_relations.append({"skill_id": name, "mechanism_id": mechanism_id})
            for claim_id in claim_ids:
                if claim_id not in self.claims:
                    self.add_finding("DANGLING_CLAIM", path, "unknown claim reference", str(claim_id))
                    continue
                indexed_claims.add(claim_id)
                relation = "owned" if self.claims[claim_id].get("owning_skill") == name else "related"
                claim_relations.append(
                    {"skill_id": name, "claim_id": claim_id, "relationship": relation}
                )
            skill_path = self.root / expected_path
            body_claim_ids: list[str] = []
            if skill_path.exists():
                try:
                    text = self.read_source_text(skill_path)
                except (OSError, UnicodeError, InventoryError) as exc:
                    self.add_finding("PARSE_ERROR", skill_path, str(exc), name)
                else:
                    body_claim_ids = sorted(
                        claim_id for claim_id in self.claims if claim_id in text
                    )
            records.append(
                {
                    "id": name,
                    "path": item.get("path"),
                    "activation_scenarios": item.get("activation_scenarios", []),
                    "mechanism_ids": sorted(mechanism_ids),
                    "claim_ids": sorted(claim_ids),
                    "explicit_body_claim_ids": body_claim_ids,
                }
            )
        for skill_id in sorted(self.skill_names - indexed_skills):
            self.add_finding("UNINDEXED_SKILL", path, "published skill is absent from corpus index", skill_id)
        for mechanism_id in sorted(set(self.mechanisms) - indexed_mechanisms):
            self.add_finding(
                "UNINDEXED_MECHANISM", path, "registry mechanism is absent from corpus relationships", mechanism_id
            )
        for claim_id in sorted(set(self.claims) - indexed_claims):
            self.add_finding("UNINDEXED_CLAIM", path, "claim is absent from corpus relationships", claim_id)
        return (
            self._category(
                "researcher/corpus/index.json",
                sorted(records, key=lambda item: item["id"]),
                semantics="curated_relationship_source",
            ),
            {
                "skill_mechanisms": sorted(
                    mechanism_relations, key=lambda item: (item["skill_id"], item["mechanism_id"])
                ),
                "skill_claims": sorted(
                    claim_relations, key=lambda item: (item["skill_id"], item["claim_id"])
                ),
                "skill_activation_cases": [],
            },
        )

    def build_activation_cases(self) -> dict[str, Any]:
        path = self.root / "researcher" / "fixtures" / "activation-cases.jsonl"
        records: list[dict[str, Any]] = []
        seen: set[str] = set()
        for line_number, value, digest in self.load_jsonl(path):
            case_id = value.get("case_id")
            if not isinstance(case_id, str) or not case_id:
                self.add_finding("PARSE_ERROR", path, f"line {line_number}: case_id is required")
                continue
            if case_id in seen:
                self.add_finding(
                    "DUPLICATE_ACTIVATION_CASE_ID", path, f"duplicate at line {line_number}", case_id
                )
            seen.add(case_id)
            referenced = [value.get("expected_primary_skill")]
            referenced.extend(value.get("acceptable_secondary_skills", []))
            referenced.extend(value.get("rejected_skills", []))
            for skill_id in referenced:
                if skill_id not in self.skill_names:
                    self.add_finding(
                        "DANGLING_SKILL", path, f"activation case references {skill_id!r}", case_id
                    )
            records.append(
                {
                    "id": case_id,
                    "expected_primary_skill": value.get("expected_primary_skill"),
                    "line": line_number,
                    "digest": digest,
                }
            )
        return self._category(
            "researcher/fixtures/activation-cases.jsonl", sorted(records, key=lambda item: item["id"])
        )

    def build_router_prompts(self) -> dict[str, Any]:
        path = self.root / "researcher" / "benchmarks" / "router" / "prompts.jsonl"
        records: list[dict[str, Any]] = []
        seen: set[str] = set()
        for line_number, value, digest in self.load_jsonl(path):
            prompt_id = value.get("prompt_id")
            if not isinstance(prompt_id, str) or not prompt_id:
                self.add_finding("PARSE_ERROR", path, f"line {line_number}: prompt_id is required")
                continue
            if prompt_id in seen:
                self.add_finding(
                    "DUPLICATE_ROUTER_PROMPT_ID", path, f"duplicate at line {line_number}", prompt_id
                )
            seen.add(prompt_id)
            referenced = [value.get("expected_primary_skill")]
            referenced.extend(value.get("acceptable_secondary_skills", []))
            referenced.extend(value.get("rejected_skills", []))
            for skill_id in referenced:
                if skill_id not in self.skill_names:
                    self.add_finding("DANGLING_SKILL", path, f"router prompt references {skill_id!r}", prompt_id)
            if not isinstance(value.get("prompt"), str) or not value["prompt"].strip():
                self.add_finding("UNKNOWN_SCHEMA", path, "router prompt text is required", prompt_id)
            records.append(
                {
                    "id": prompt_id,
                    "expected_primary_skill": value.get("expected_primary_skill"),
                    "line": line_number,
                    "digest": digest,
                }
            )
        return self._category(
            "researcher/benchmarks/router/prompts.jsonl", sorted(records, key=lambda item: item["id"])
        )

    def build_adversarial(self) -> tuple[dict[str, Any], dict[str, Any]]:
        scenario_dir = self.root / "researcher" / "benchmarks" / "scenarios"
        methodology_path = self.root / "researcher" / "benchmarks" / "README.md"
        methodology_digest, methodology_size = self.add_source(methodology_path)
        scenario_records: list[dict[str, Any]] = []
        scenarios: dict[str, dict[str, Any]] = {}
        for path in sorted(scenario_dir.glob("*.jsonl")):
            for line_number, value, digest in self.load_jsonl(path):
                scenario_id = value.get("scenario_id")
                if not isinstance(scenario_id, str) or not scenario_id:
                    self.add_finding("PARSE_ERROR", path, f"line {line_number}: scenario_id is required")
                    continue
                if scenario_id in scenarios:
                    self.add_finding(
                        "DUPLICATE_SCENARIO_ID", path, f"duplicate at line {line_number}", scenario_id
                    )
                scenarios[scenario_id] = value
                scenario_records.append(
                    {
                        "id": scenario_id,
                        "expected_gate": value.get("expected_gate"),
                        "path": self.relative(path),
                        "line": line_number,
                        "digest": digest,
                    }
                )
        golden_path = self.root / "researcher" / "benchmarks" / "goldens" / "adversarial-goldens.json"
        golden_value = self.load_json(golden_path)
        golden_records: list[dict[str, Any]] = []
        if not isinstance(golden_value, dict):
            self.add_finding("UNKNOWN_SCHEMA", golden_path, "golden file must be an object")
            golden_value = {}
        for scenario_id in sorted(set(scenarios) - set(golden_value)):
            self.add_finding("MISSING_GOLDEN", golden_path, "scenario has no golden", scenario_id)
        for scenario_id in sorted(set(golden_value) - set(scenarios)):
            self.add_finding("ORPHAN_GOLDEN", golden_path, "golden has no scenario", scenario_id)
        for scenario_id, golden in sorted(golden_value.items()):
            expected_gate = golden.get("expected_gate") if isinstance(golden, dict) else None
            if scenario_id in scenarios and expected_gate != scenarios[scenario_id].get("expected_gate"):
                self.add_finding(
                    "GOLDEN_GATE_MISMATCH", golden_path, "golden and scenario expected_gate differ", scenario_id
                )
            golden_records.append(
                {"id": scenario_id, "expected_gate": expected_gate, "digest": record_digest(golden)}
            )
        return (
            self._category(
                "researcher/benchmarks/scenarios/*.jsonl",
                sorted(scenario_records, key=lambda item: item["id"]),
                execution_status="catalog_only",
                methodology={
                    "path": self.relative(methodology_path),
                    "digest": methodology_digest,
                    "size_bytes": methodology_size,
                },
            ),
            self._category("researcher/benchmarks/goldens/adversarial-goldens.json", golden_records),
        )

    def build_effectiveness_tasks(self) -> dict[str, Any]:
        tasks_dir = self.root / "researcher" / "benchmarks" / "effectiveness" / "tasks"
        records: list[dict[str, Any]] = []
        seen: set[str] = set()
        if not tasks_dir.exists():
            self.add_finding("INVALID_EFFECTIVENESS_TASK", tasks_dir, "tasks directory is missing")
            return self._category("researcher/benchmarks/effectiveness/tasks/*", records)
        for task_dir in sorted(path for path in tasks_dir.iterdir() if path.is_dir()):
            metadata_path = task_dir / "metadata.json"
            metadata = self.load_json(metadata_path)
            if not isinstance(metadata, dict):
                self.add_finding("INVALID_EFFECTIVENESS_TASK", metadata_path, "metadata must be an object")
                continue
            task_id = metadata.get("id")
            slug = metadata.get("slug")
            if not isinstance(task_id, str) or not isinstance(slug, str):
                self.add_finding("INVALID_EFFECTIVENESS_TASK", metadata_path, "id and slug are required")
                continue
            if task_id in seen:
                self.add_finding(
                    "DUPLICATE_EFFECTIVENESS_TASK_ID", metadata_path, "duplicate task id", task_id
                )
            seen.add(task_id)
            expected_dir = f"{task_id}-{slug}"
            if task_dir.name != expected_dir:
                self.add_finding(
                    "INVALID_EFFECTIVENESS_TASK",
                    task_dir,
                    f"directory must be named {expected_dir}",
                    task_id,
                )
            required = [task_dir / "README.md", task_dir / "task.md", task_dir / "verify.sh"]
            starting = task_dir / "starting"
            for required_path in required:
                if not required_path.is_file():
                    self.add_finding(
                        "INVALID_EFFECTIVENESS_TASK", required_path, "required task file is missing", task_id
                    )
                else:
                    self.add_source(required_path)
            if not starting.is_dir() or not any(path.is_file() for path in starting.rglob("*")):
                self.add_finding(
                    "INVALID_EFFECTIVENESS_TASK", starting, "starting directory must contain a file", task_id
                )
            else:
                for starting_file in sorted(path for path in starting.rglob("*") if path.is_file()):
                    self.add_source(starting_file)
            verify = task_dir / "verify.sh"
            if verify.exists() and not (verify.stat().st_mode & stat.S_IXUSR):
                self.add_finding(
                    "INVALID_EFFECTIVENESS_TASK", verify, "verify.sh must be executable", task_id
                )
            for key in ("target_skill", "irrelevant_skill"):
                skill_id = metadata.get(key)
                if skill_id != "none" and skill_id not in self.skill_names:
                    self.add_finding(
                        "DANGLING_SKILL", metadata_path, f"{key} references {skill_id!r}", task_id
                    )
            records.append(
                {
                    "id": task_id,
                    "slug": slug,
                    "path": self.relative(task_dir),
                    "target_skill": metadata.get("target_skill"),
                    "irrelevant_skill": metadata.get("irrelevant_skill"),
                    "metadata_digest": record_digest(metadata),
                }
            )
        return self._category(
            "researcher/benchmarks/effectiveness/tasks/*", sorted(records, key=lambda item: item["id"])
        )

    def build_examples(self) -> dict[str, Any]:
        examples_dir = self.root / "examples"
        records: list[dict[str, Any]] = []
        for example_dir in sorted(path for path in examples_dir.iterdir() if path.is_dir()):
            readme = example_dir / "README.md"
            if not readme.exists():
                self.add_finding("PARSE_ERROR", example_dir, "example directory is missing README.md")
                continue
            digest, _ = self.add_source(readme)
            records.append({"id": example_dir.name, "path": self.relative(example_dir), "digest": digest})
        return self._category("examples/*/README.md", records)

    def build_benchmark_runners(self) -> dict[str, Any]:
        runner_dir = self.root / "researcher" / "benchmarks" / "sdk-runner"
        records: list[dict[str, Any]] = []
        contract_paths = [
            "README.md",
            "package.json",
            "package-lock.json",
            "tsconfig.json",
            "src/common.ts",
            "src/durableFs.test.ts",
            "src/durableFs.ts",
            "src/durableJson.test.ts",
            "src/durableJson.ts",
            "src/liveBlock.test.ts",
            "src/routerEngine.test.ts",
            "src/routerEngine.ts",
            "src/routerManifest.test.ts",
            "src/routerManifest.ts",
            "src/routerRunStore.test.ts",
            "src/routerRunStore.ts",
            "src/sdkImport.test.ts",
            "src/sourceFreeze.test.ts",
            "src/sourceFreeze.ts",
            "src/runRouter.ts",
            "src/runEffectiveness.ts",
            "test/denyCursorSdkLoader.mjs",
            "test/registerDenyCursorSdk.mjs",
        ]
        expected_contract_paths = set(contract_paths)
        excluded_roots = {"dist", "node_modules"}

        def contract_files(directory: Path) -> Iterable[Path]:
            for child in sorted(directory.iterdir(), key=lambda path: path.name):
                if directory == runner_dir and child.name in excluded_roots:
                    continue
                if child.is_dir() and not child.is_symlink():
                    yield from contract_files(child)
                else:
                    yield child

        observed_contract_paths = (
            {
                path.relative_to(runner_dir).as_posix()
                for path in contract_files(runner_dir)
            }
            if runner_dir.is_dir()
            else set()
        )
        for relative in sorted(observed_contract_paths - expected_contract_paths):
            path = runner_dir / relative
            self.add_source(path)
            self.add_finding(
                "UNREGISTERED_BENCHMARK_RUNNER_CONTRACT",
                path,
                "benchmark runner file is not registered in the closed contract set",
                relative,
            )
        for relative in contract_paths:
            path = runner_dir / relative
            if not path.exists():
                self.add_finding("PARSE_ERROR", path, "benchmark runner contract file is missing", relative)
                continue
            digest, size = self.add_source(path)
            records.append(
                {
                    "id": relative.replace("/", ":"),
                    "path": self.relative(path),
                    "digest": digest,
                    "size_bytes": size,
                }
            )
        documentation_paths = (
            ("methodology:PLAN.md", runner_dir.parent / "PLAN.md"),
            ("methodology:router:README.md", runner_dir.parent / "router" / "README.md"),
            (
                "methodology:effectiveness:README.md",
                runner_dir.parent / "effectiveness" / "README.md",
            ),
        )
        for record_id, path in documentation_paths:
            if not path.exists():
                self.add_finding(
                    "PARSE_ERROR",
                    path,
                    "benchmark methodology source is missing",
                    record_id,
                )
                continue
            digest, size = self.add_source(path)
            records.append(
                {
                    "id": record_id,
                    "path": self.relative(path),
                    "digest": digest,
                    "size_bytes": size,
                }
            )
        return self._category(
            "researcher/benchmarks/sdk-runner",
            sorted(records, key=lambda item: item["id"]),
            status={"router": "dry_run_only", "effectiveness": "scaffold_dry_run_only"},
        )

    def build_manifests(self) -> dict[str, Any]:
        marketplace_path = self.root / ".claude-plugin" / "marketplace.json"
        plugin_path = self.root / ".plugin" / "plugin.json"
        root_skill_path = self.root / "SKILL.md"
        marketplace = self.load_json(marketplace_path)
        plugin = self.load_json(plugin_path)
        root_skill_digest, _ = self.add_source(root_skill_path)
        root_version: str | None = None
        try:
            version_lines = [
                line.partition(":")[2].strip()
                for line in self.read_source_text(root_skill_path).splitlines()
                if line.startswith("**Version**:")
            ]
            if len(version_lines) == 1:
                root_version = version_lines[0]
            else:
                self.add_finding("UNKNOWN_SCHEMA", root_skill_path, "expected exactly one **Version** line")
        except (OSError, UnicodeError, InventoryError) as exc:
            self.add_finding("PARSE_ERROR", root_skill_path, str(exc))
        marketplace_version = None
        marketplace_skills: list[str] = []
        if isinstance(marketplace, dict):
            marketplace_version = marketplace.get("metadata", {}).get("version")
            plugins = marketplace.get("plugins")
            if isinstance(plugins, list) and len(plugins) == 1 and isinstance(plugins[0], dict):
                raw_paths = plugins[0].get("skills", [])
                if isinstance(raw_paths, list):
                    marketplace_skills = sorted(Path(value).name for value in raw_paths if isinstance(value, str))
        plugin_version = plugin.get("version") if isinstance(plugin, dict) else None
        versions = {
            "marketplace": marketplace_version,
            "open_plugin": plugin_version,
            "collection_skill": root_version,
        }
        if len(set(versions.values())) != 1:
            self.add_finding("PLUGIN_VERSION_MISMATCH", plugin_path, f"version surfaces differ: {versions}")
        actual_skills = sorted(self.skill_names)
        if marketplace_skills != actual_skills:
            self.add_finding(
                "MANIFEST_SKILL_MISMATCH",
                marketplace_path,
                f"manifest={marketplace_skills}, published={actual_skills}",
            )
        records = [
            {"id": "claude-marketplace", "path": self.relative(marketplace_path), "version": marketplace_version},
            {"id": "open-plugin", "path": self.relative(plugin_path), "version": plugin_version},
            {
                "id": "collection-skill",
                "path": self.relative(root_skill_path),
                "version": root_version,
                "digest": root_skill_digest,
            },
        ]
        return self._category(
            "publication manifests",
            records,
            versions=versions,
            skill_sets={"published": actual_skills, "marketplace": marketplace_skills},
        )

    def build_validators(self) -> dict[str, Any]:
        records: list[dict[str, Any]] = []
        for descriptor in VALIDATOR_OWNERSHIP:
            descriptor_path = descriptor["path"]
            descriptor_id = descriptor["id"]
            assert isinstance(descriptor_path, str)
            assert isinstance(descriptor_id, str)
            path = self.root / descriptor_path
            if not path.exists():
                self.add_finding("PARSE_ERROR", path, "declared validator is missing", descriptor_id)
                continue
            digest, _ = self.add_source(path)
            records.append({**descriptor, "digest": digest})
        support_records: list[dict[str, Any]] = []
        for relative in (
            ".gitignore",
            ".github/workflows/validate.yml",
            "requirements-dev.in",
            "requirements-dev.txt",
            "researcher/scripts/tests/test_render_router_report.py",
            "researcher/scripts/tests/test_benchmark_catalog.py",
            "researcher/scripts/tests/test_public_repo.py",
            "researcher/scripts/tests/test_spec_program.py",
            "docs/product/spec-execution-plan.json",
            "docs/product/living-organization-plan.md",
        ):
            path = self.root / relative
            if not path.is_file():
                self.add_finding("PARSE_ERROR", path, "validation support file is missing", relative)
                continue
            digest, size = self.add_source(path)
            support_records.append({"path": relative, "digest": digest, "size_bytes": size})
        return self._category(
            "declared validator ownership",
            records,
            support_files=support_records,
        )

    def scan_closed_tree(self, root: Path, *, artifact_id: str) -> dict[str, str]:
        """Return every descendant's no-follow filesystem type.

        Closed committed fixtures may not delegate any part of their identity to
        a symlink, device, pipe, socket, or hard-linked alias. The caller compares
        this complete mapping with a declared manifest, including directories.
        """

        observed: dict[str, str] = {}
        pending: list[tuple[Path, PurePosixPath]] = [(root, PurePosixPath())]
        while pending:
            directory, prefix = pending.pop()
            try:
                entries = sorted(os.scandir(directory), key=lambda entry: entry.name)
            except OSError as exc:
                self.add_finding(
                    "PARSE_ERROR",
                    directory,
                    f"cannot inspect closed fixture: {exc}",
                    artifact_id,
                )
                continue
            for entry in entries:
                relative = prefix / entry.name
                relative_text = relative.as_posix()
                path = directory / entry.name
                try:
                    info = entry.stat(follow_symlinks=False)
                except OSError as exc:
                    observed[relative_text] = "unsafe"
                    self.add_finding(
                        "PARSE_ERROR",
                        path,
                        f"cannot inspect closed fixture entry: {exc}",
                        artifact_id,
                    )
                    continue
                if stat.S_ISDIR(info.st_mode):
                    observed[relative_text] = "directory"
                    pending.append((path, relative))
                elif stat.S_ISREG(info.st_mode) and info.st_nlink == 1:
                    observed[relative_text] = "file"
                else:
                    observed[relative_text] = "unsafe"
                    self.add_finding(
                        "UNREGISTERED_SUPERVISED_LOOP_COMPONENT",
                        path,
                        "closed reference-run entries must be real, single-link "
                        "directories or regular files",
                        artifact_id,
                    )
        return observed

    def collect_supervised_loop_tests(self, tests_root: Path) -> list[str]:
        """Resolve the closed supervised-test manifest without following links."""

        expected_by_name = {
            Path(relative).name: relative for relative in SUPERVISED_LOOP_TEST_FILES
        }
        try:
            root_info = os.lstat(tests_root)
        except OSError as exc:
            self.add_finding(
                "MISSING_SUPERVISED_LOOP_TEST",
                tests_root,
                f"cannot inspect supervised-test root: {exc}",
                "supervised-loop-tests",
            )
            return []
        if stat.S_ISLNK(root_info.st_mode) or not stat.S_ISDIR(root_info.st_mode):
            self.add_finding(
                "UNSAFE_SUPERVISED_LOOP_TEST",
                tests_root,
                "supervised-test root must be a real directory",
                "supervised-loop-tests",
            )
            return []

        try:
            entries = sorted(os.scandir(tests_root), key=lambda entry: entry.name)
        except OSError as exc:
            self.add_finding(
                "MISSING_SUPERVISED_LOOP_TEST",
                tests_root,
                f"cannot enumerate supervised-test root: {exc}",
                "supervised-loop-tests",
            )
            return []

        safe_expected: set[str] = set()
        for entry in entries:
            if not entry.name.endswith(".py") or not any(
                entry.name.startswith(prefix)
                for prefix in SUPERVISED_LOOP_TEST_PREFIXES
            ):
                continue
            path = tests_root / entry.name
            try:
                info = entry.stat(follow_symlinks=False)
            except OSError as exc:
                self.add_finding(
                    "UNSAFE_SUPERVISED_LOOP_TEST",
                    path,
                    f"cannot inspect supervised test: {exc}",
                    entry.name,
                )
                continue
            relative = expected_by_name.get(entry.name)
            if relative is None:
                self.add_finding(
                    "UNREGISTERED_SUPERVISED_LOOP_TEST",
                    path,
                    "matching supervised test is absent from the closed manifest",
                    entry.name,
                )
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                self.add_finding(
                    "UNSAFE_SUPERVISED_LOOP_TEST",
                    path,
                    "supervised test must be a real single-link regular file",
                    entry.name,
                )
                continue
            if relative is None:
                continue
            safe_expected.add(entry.name)

        for name in sorted(set(expected_by_name) - safe_expected):
            path = tests_root / name
            if not any(
                finding.path == self.relative(path)
                and finding.code == "UNSAFE_SUPERVISED_LOOP_TEST"
                for finding in self.findings
            ):
                self.add_finding(
                    "MISSING_SUPERVISED_LOOP_TEST",
                    path,
                    "declared supervised test is missing",
                    name,
                )
        return sorted(expected_by_name[name] for name in safe_expected)

    def collect_closed_supervised_root(
        self,
        root_relative: str,
        expected_files: tuple[str, ...],
        excluded_directory_names: frozenset[str],
    ) -> list[str]:
        """Validate one exact supervised source root without admitting extras."""

        root = self.root / root_relative
        current = self.root
        try:
            for component in PurePosixPath(root_relative).parts:
                current /= component
                info = os.lstat(current)
                if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
                    raise InventoryError(
                        f"closed supervised root ancestor is unsafe: {component}"
                    )
        except (InventoryError, OSError) as exc:
            self.add_finding(
                "UNSAFE_SUPERVISED_SOURCE_ROOT",
                root,
                str(exc),
                root_relative,
            )
            return []

        prefix = f"{root_relative}/"
        expected_relative = {
            relative.removeprefix(prefix): relative
            for relative in expected_files
            if relative.startswith(prefix)
        }
        if len(expected_relative) != len(expected_files):
            self.add_finding(
                "PARSE_ERROR",
                root,
                "closed supervised manifest contains a path outside its root",
                root_relative,
            )
            return []
        expected_directories: set[str] = set()
        for relative in expected_relative:
            parent = PurePosixPath(relative).parent
            while parent != PurePosixPath("."):
                expected_directories.add(parent.as_posix())
                parent = parent.parent

        safe_files: set[str] = set()

        def inspect_generated_cache(
            directory: Path,
            relative_parent: PurePosixPath,
        ) -> None:
            """Allow only ordinary interpreter cache entries in an exclusion.

            The directory is excluded from the declared-input digest, not from
            namespace validation. In particular, a source or config file under
            ``__pycache__`` must not disappear from diagnostics merely because
            generated bytecode is allowed there.
            """

            try:
                entries = sorted(os.scandir(directory), key=lambda entry: entry.name)
            except OSError as exc:
                self.add_finding(
                    "UNSAFE_SUPERVISED_SOURCE_FILE",
                    directory,
                    f"cannot inspect generated cache exclusion: {exc}",
                    relative_parent.as_posix(),
                )
                return
            for entry in entries:
                relative = relative_parent / entry.name
                path = directory / entry.name
                try:
                    info = entry.stat(follow_symlinks=False)
                except OSError as exc:
                    self.add_finding(
                        "UNSAFE_SUPERVISED_SOURCE_FILE",
                        path,
                        f"cannot inspect generated cache entry: {exc}",
                        relative.as_posix(),
                    )
                    continue
                ordinary_bytecode = (
                    stat.S_ISREG(info.st_mode)
                    and info.st_nlink == 1
                    and re.fullmatch(
                        r"[A-Za-z_][A-Za-z0-9_]*\.cpython-[0-9]+"
                        r"(?:\.opt-[0-9]+)?\.pyc",
                        entry.name,
                    )
                    is not None
                )
                if ordinary_bytecode:
                    continue
                code = (
                    "UNREGISTERED_SUPERVISED_SOURCE_FILE"
                    if stat.S_ISREG(info.st_mode) and info.st_nlink == 1
                    else "UNSAFE_SUPERVISED_SOURCE_FILE"
                )
                self.add_finding(
                    code,
                    path,
                    "generated cache exclusion contains a non-bytecode or unsafe entry",
                    relative.as_posix(),
                )

        pending: list[tuple[Path, PurePosixPath]] = [(root, PurePosixPath())]
        while pending:
            directory, relative_parent = pending.pop()
            try:
                entries = sorted(os.scandir(directory), key=lambda entry: entry.name)
            except OSError as exc:
                self.add_finding(
                    "UNSAFE_SUPERVISED_SOURCE_ROOT",
                    directory,
                    f"cannot enumerate closed supervised root: {exc}",
                    root_relative,
                )
                continue
            for entry in entries:
                relative = relative_parent / entry.name
                relative_text = relative.as_posix()
                path = directory / entry.name
                try:
                    info = entry.stat(follow_symlinks=False)
                except OSError as exc:
                    self.add_finding(
                        "UNSAFE_SUPERVISED_SOURCE_FILE",
                        path,
                        f"cannot inspect supervised source: {exc}",
                        relative_text,
                    )
                    continue
                if stat.S_ISDIR(info.st_mode):
                    if entry.name in excluded_directory_names:
                        inspect_generated_cache(path, relative)
                        continue
                    if relative_text not in expected_directories:
                        self.add_finding(
                            "UNREGISTERED_SUPERVISED_SOURCE_FILE",
                            path,
                            "directory is absent from the closed supervised manifest",
                            relative_text,
                        )
                        continue
                    pending.append((path, relative))
                    continue
                expected = expected_relative.get(relative_text)
                if expected is None:
                    self.add_finding(
                        "UNREGISTERED_SUPERVISED_SOURCE_FILE",
                        path,
                        "file is absent from the closed supervised manifest",
                        relative_text,
                    )
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                    self.add_finding(
                        "UNSAFE_SUPERVISED_SOURCE_FILE",
                        path,
                        "supervised source must be a real single-link regular file",
                        relative_text,
                    )
                    continue
                if expected is not None:
                    safe_files.add(expected)

        for relative in sorted(set(expected_files) - safe_files):
            path = self.root / relative
            if not any(
                finding.path == self.relative(path)
                and finding.code == "UNSAFE_SUPERVISED_SOURCE_FILE"
                for finding in self.findings
            ):
                self.add_finding(
                    "MISSING_SUPERVISED_SOURCE_FILE",
                    path,
                    "declared supervised source is missing",
                    relative,
                )
        return sorted(safe_files)

    def build_supervised_loop(self) -> dict[str, Any]:
        """Bind the legacy supervised loop without treating it as activation authority."""

        records: list[dict[str, Any]] = []
        for descriptor in SUPERVISED_LOOP_COMPONENTS:
            relative = descriptor["path"]
            path = self.root / relative
            if not path.is_file():
                self.add_finding(
                    "PARSE_ERROR",
                    path,
                    "declared supervised-loop component is missing",
                    descriptor["id"],
                )
                continue
            digest, size = self.add_source(path)
            records.append({**descriptor, "digest": digest, "size_bytes": size})

        scripts_root = self.root / "researcher" / "scripts"

        support_paths = [
            "researcher/__init__.py",
            "researcher/scripts/__init__.py",
            "researcher/discovery/manual-seed.jsonl",
            "researcher/orchestration/config.json",
            "researcher/runbooks/continuous-operation.md",
            "researcher/templates/source-evaluation.json",
            "researcher/templates/skill-proposal.md",
            "researcher/templates/mechanism-proposal.jsonl",
            "researcher/scripts/novelty_check.py",
            "researcher/scripts/validate_repo.py",
            "researcher/scripts/run_benchmarks.py",
            "researcher/scripts/check_activation_cases.py",
            "researcher/scripts/skill_frontmatter.py",
            "researcher/orchestration/launchd/install.sh",
            "researcher/orchestration/launchd/uninstall.sh",
            "researcher/orchestration/launchd/run-loop-step.sh",
            "researcher/orchestration/launchd/run-loop-discover.sh",
            "researcher/orchestration/launchd/run-loop-daily.sh",
            "researcher/orchestration/launchd/com.context-engineering.loop-step.plist",
            "researcher/orchestration/launchd/com.context-engineering.loop-discover.plist",
            "researcher/orchestration/launchd/com.context-engineering.loop-daily.plist",
        ]
        reference_run = (
            self.root
            / "researcher"
            / "runs"
            / "20260515-035228-executable-autonomous-research-frameworks"
        )
        runs_root = reference_run.parent
        safe_reference_root = True
        for candidate in (self.root / "researcher", runs_root, reference_run):
            try:
                info = os.lstat(candidate)
            except OSError:
                safe_reference_root = False
                break
            if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
                safe_reference_root = False
                break
        if not safe_reference_root:
            self.add_finding(
                "PARSE_ERROR",
                reference_run,
                "committed reference-run fixture is missing or unsafe",
                "legacy-reference-run",
            )
        else:
            expected_reference_entries = {
                **{
                    relative: "directory"
                    for relative in REFERENCE_RUN_DIRECTORIES
                },
                **{relative: "file" for relative in REFERENCE_RUN_FILES},
            }
            observed_reference_entries = self.scan_closed_tree(
                reference_run,
                artifact_id="legacy-reference-run",
            )
            missing_reference_entries = sorted(
                set(expected_reference_entries) - set(observed_reference_entries)
            )
            extra_reference_entries = sorted(
                set(observed_reference_entries) - set(expected_reference_entries)
            )
            mismatched_reference_entries = sorted(
                relative
                for relative in set(expected_reference_entries).intersection(
                    observed_reference_entries
                )
                if observed_reference_entries[relative]
                != expected_reference_entries[relative]
            )
            if missing_reference_entries:
                self.add_finding(
                    "PARSE_ERROR",
                    reference_run,
                    "committed reference-run manifest is missing entries: "
                    f"{missing_reference_entries}",
                    "legacy-reference-run",
                )
            if extra_reference_entries:
                self.add_finding(
                    "UNREGISTERED_SUPERVISED_LOOP_COMPONENT",
                    reference_run,
                    "committed reference-run manifest has unregistered entries: "
                    f"{extra_reference_entries}",
                    "legacy-reference-run",
                )
            for relative in mismatched_reference_entries:
                self.add_finding(
                    "UNREGISTERED_SUPERVISED_LOOP_COMPONENT",
                    reference_run / relative,
                    "committed reference-run entry has an unsafe filesystem identity "
                    f"({observed_reference_entries[relative]} != "
                    f"{expected_reference_entries[relative]})",
                    "legacy-reference-run",
                )
            reference_state_path = reference_run / "run-state.json"
            reference_state = (
                self.load_json(reference_state_path)
                if observed_reference_entries.get("run-state.json") == "file"
                else None
            )
            if not isinstance(reference_state, dict) or (
                reference_state.get("current_state") != "closed"
                or reference_state.get("close_status") != "reference-only"
                or reference_state.get("run_id") != reference_run.name
            ):
                self.add_finding(
                    "PARSE_ERROR",
                    reference_state_path,
                    "committed reference run must be closed as reference-only with exact run_id",
                    "legacy-reference-run",
                )
            for relative in REFERENCE_RUN_FILES:
                if observed_reference_entries.get(relative) == "file":
                    support_paths.append(self.relative(reference_run / relative))
        tests_root = scripts_root / "tests"
        support_paths.extend(self.collect_supervised_loop_tests(tests_root))
        for root_relative, expected_files, exclusions in SUPERVISED_CLOSED_ROOTS:
            support_paths.extend(
                self.collect_closed_supervised_root(
                    root_relative,
                    expected_files,
                    exclusions,
                )
            )
        support_paths.extend(SUPERVISED_PACKAGE_INITIALIZERS)
        support_paths = sorted(set(support_paths))

        registered_python = {
            descriptor["path"] for descriptor in SUPERVISED_LOOP_COMPONENTS
        } | {
            relative
            for relative in support_paths
            if relative.startswith("researcher/") and relative.endswith(".py")
        }
        discovered_dependencies: set[str] = set()
        pending = [
            *(descriptor["path"] for descriptor in SUPERVISED_LOOP_COMPONENTS),
            *SUPERVISED_PACKAGE_INITIALIZERS,
        ]
        visited: set[str] = set()
        while pending:
            relative = pending.pop()
            if relative in visited:
                continue
            visited.add(relative)
            path = self.root / relative
            if not path.is_file():
                continue
            try:
                tree = ast.parse(self.read_source_text(path), filename=relative)
            except (OSError, UnicodeError, SyntaxError, InventoryError) as exc:
                self.add_finding("PARSE_ERROR", path, str(exc), relative)
                continue

            importlib_modules: set[str] = set()
            import_module_names: set[str] = set()
            builtins_modules: set[str] = set()
            builtin_import_names: set[str] = {"__import__"}
            subprocess_modules: set[str] = set()
            subprocess_functions: set[str] = set()
            os_modules: set[str] = set()
            os_execution_functions: dict[str, str] = {}
            sys_modules: set[str] = set()
            python_executable_names: set[str] = set()
            assignments: dict[str, list[ast.expr]] = {}
            for node in ast.walk(tree):
                if isinstance(node, (ast.Assign, ast.AnnAssign)):
                    value = node.value
                    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                    if value is not None:
                        for target in targets:
                            if isinstance(target, ast.Name):
                                assignments.setdefault(target.id, []).append(value)
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        bound = alias.asname or alias.name.split(".")[0]
                        if alias.name == "importlib" or alias.name.startswith("importlib."):
                            importlib_modules.add(bound)
                        if alias.name == "builtins" or alias.name.startswith("builtins."):
                            builtins_modules.add(bound)
                        if alias.name == "subprocess" or alias.name.startswith("subprocess."):
                            subprocess_modules.add(bound)
                        if alias.name == "os" or alias.name.startswith("os."):
                            os_modules.add(bound)
                        if alias.name == "sys" or alias.name.startswith("sys."):
                            sys_modules.add(bound)
                elif isinstance(node, ast.ImportFrom) and node.level == 0:
                    if node.module == "importlib":
                        for alias in node.names:
                            if alias.name == "import_module":
                                import_module_names.add(alias.asname or alias.name)
                            elif alias.name == "*":
                                import_module_names.add("import_module")
                    elif node.module == "builtins":
                        for alias in node.names:
                            if alias.name == "__import__":
                                builtin_import_names.add(alias.asname or alias.name)
                    elif node.module == "subprocess":
                        for alias in node.names:
                            if alias.name in {
                                "call",
                                "check_call",
                                "check_output",
                                "Popen",
                                "run",
                            }:
                                subprocess_functions.add(alias.asname or alias.name)
                    elif node.module == "os":
                        for alias in node.names:
                            if alias.name.startswith(("exec", "spawn")):
                                os_execution_functions[alias.asname or alias.name] = alias.name
                    elif node.module == "sys":
                        for alias in node.names:
                            if alias.name == "executable":
                                python_executable_names.add(alias.asname or alias.name)

            dynamic_argument_nodes: set[int] = set()

            def dynamic_import_kind(call: ast.Call) -> str | None:
                function = call.func
                if isinstance(function, ast.Name):
                    if function.id in import_module_names:
                        return "importlib.import_module"
                    if function.id in builtin_import_names:
                        return "__import__"
                if isinstance(function, ast.Attribute) and isinstance(
                    function.value, ast.Name
                ):
                    if (
                        function.attr == "import_module"
                        and function.value.id in importlib_modules
                    ):
                        return "importlib.import_module"
                    if (
                        function.attr == "__import__"
                        and function.value.id in builtins_modules
                    ):
                        return "builtins.__import__"
                return None

            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                dynamic_kind = dynamic_import_kind(node)
                if dynamic_kind is None:
                    continue
                self.add_finding(
                    "DYNAMIC_SUPERVISED_LOOP_IMPORT",
                    path,
                    f"unsupported dynamic import call {dynamic_kind} at line {node.lineno}",
                    relative,
                )
                for argument in [
                    *node.args,
                    *(keyword.value for keyword in node.keywords),
                ]:
                    dynamic_argument_nodes.update(id(value) for value in ast.walk(argument))

            def expand_expression(
                expression: ast.expr,
                seen: frozenset[str] = frozenset(),
            ) -> list[ast.expr]:
                if isinstance(expression, ast.Name) and expression.id not in seen:
                    values = assignments.get(expression.id)
                    if values:
                        expanded: list[ast.expr] = []
                        for value in values:
                            expanded.extend(
                                expand_expression(value, seen | {expression.id})
                            )
                        return expanded
                return [expression]

            def is_python_executable(expression: ast.expr) -> bool:
                for value in expand_expression(expression):
                    if (
                        isinstance(value, ast.Attribute)
                        and value.attr == "executable"
                        and isinstance(value.value, ast.Name)
                        and value.value.id in sys_modules
                    ):
                        return True
                    if isinstance(value, ast.Name) and value.id in python_executable_names:
                        return True
                    if isinstance(value, ast.Constant) and isinstance(value.value, str):
                        executable = PurePosixPath(value.value).name
                        if re.fullmatch(r"python(?:3(?:\.[0-9]+)?)?", executable):
                            return True
                return False

            def contains_static_python_path(expression: ast.expr) -> bool:
                for value in expand_expression(expression):
                    if isinstance(value, ast.Constant) and isinstance(value.value, str):
                        if value.value.endswith(".py"):
                            return True
                    if any(
                        isinstance(child, ast.Constant)
                        and isinstance(child.value, str)
                        and child.value.endswith(".py")
                        for child in ast.walk(value)
                    ):
                        return True
                return False

            def check_python_argv(argv_expression: ast.expr, line: int) -> None:
                for argv in expand_expression(argv_expression):
                    if not isinstance(argv, (ast.List, ast.Tuple)) or not argv.elts:
                        continue
                    if not is_python_executable(argv.elts[0]) or len(argv.elts) < 2:
                        continue
                    script = argv.elts[1]
                    if (
                        isinstance(script, ast.Constant)
                        and isinstance(script.value, str)
                        and script.value.startswith("-")
                    ):
                        continue
                    if contains_static_python_path(script):
                        continue
                    self.add_finding(
                        "DYNAMIC_SUPERVISED_LOOP_ENTRYPOINT",
                        path,
                        "computed Python subprocess entrypoint is unsupported "
                        f"at line {line}",
                        relative,
                    )

            subprocess_methods = {
                "call",
                "check_call",
                "check_output",
                "Popen",
                "run",
            }
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                function = node.func
                is_subprocess = (
                    isinstance(function, ast.Name)
                    and function.id in subprocess_functions
                ) or (
                    isinstance(function, ast.Attribute)
                    and function.attr in subprocess_methods
                    and isinstance(function.value, ast.Name)
                    and function.value.id in subprocess_modules
                )
                if is_subprocess:
                    argv = node.args[0] if node.args else next(
                        (
                            keyword.value
                            for keyword in node.keywords
                            if keyword.arg == "args"
                        ),
                        None,
                    )
                    if argv is not None:
                        check_python_argv(argv, node.lineno)
                    continue
                os_method: str | None = None
                if isinstance(function, ast.Name):
                    os_method = os_execution_functions.get(function.id)
                elif (
                    isinstance(function, ast.Attribute)
                    and isinstance(function.value, ast.Name)
                    and function.value.id in os_modules
                    and function.attr.startswith(("exec", "spawn"))
                ):
                    os_method = function.attr
                if os_method is None:
                    continue
                if os_method.startswith("exec") and len(node.args) >= 2:
                    if is_python_executable(node.args[0]):
                        check_python_argv(node.args[1], node.lineno)
                elif os_method.startswith("spawn") and len(node.args) >= 3:
                    if is_python_executable(node.args[1]):
                        check_python_argv(node.args[2], node.lineno)

            local_dependencies: set[str] = set()
            current_package = list(PurePosixPath(relative).parent.parts)

            def module_candidate(
                module_name: str,
                *,
                definitely_local: bool,
            ) -> str | None:
                if module_name.startswith("researcher.") or module_name == "researcher":
                    module_path = module_name.replace(".", "/")
                elif current_package == ["researcher", "scripts"]:
                    module_path = f"researcher/scripts/{module_name.split('.')[0]}"
                else:
                    return None
                file_candidate = f"{module_path}.py"
                package_candidate = f"{module_path}/__init__.py"
                if (self.root / file_candidate).is_file():
                    return file_candidate
                if (self.root / package_candidate).is_file():
                    return package_candidate
                return file_candidate if definitely_local else None

            for node in ast.walk(tree):
                module_names: list[tuple[str, bool]] = []
                if isinstance(node, ast.ImportFrom):
                    if node.level > 0:
                        ascents = node.level - 1
                        if ascents > len(current_package):
                            self.add_finding(
                                "UNREGISTERED_SUPERVISED_LOOP_DEPENDENCY",
                                path,
                                f"relative import escapes package at line {node.lineno}",
                                relative,
                            )
                            continue
                        base = current_package[: len(current_package) - ascents]
                        if node.module:
                            resolved = ".".join([*base, *node.module.split(".")])
                            module_names.append((resolved, True))
                            if (self.root / resolved.replace(".", "/")).is_dir():
                                module_names.extend(
                                    (f"{resolved}.{alias.name}", True)
                                    for alias in node.names
                                    if alias.name != "*"
                                )
                        else:
                            module_names.extend(
                                (".".join([*base, alias.name]), True)
                                for alias in node.names
                                if alias.name != "*"
                            )
                    elif node.level == 0 and node.module:
                        if node.module in {"researcher", "researcher.scripts"}:
                            module_names.append((node.module, True))
                            module_names.extend(
                                (f"{node.module}.{alias.name}", True)
                                for alias in node.names
                                if alias.name != "*"
                            )
                        else:
                            module_names.append(
                                (
                                    node.module,
                                    node.module.startswith("researcher."),
                                )
                            )
                elif isinstance(node, ast.Import):
                    module_names.extend(
                        (
                            alias.name,
                            alias.name == "researcher"
                            or alias.name.startswith("researcher."),
                        )
                        for alias in node.names
                    )
                for module_name, definitely_local in module_names:
                    candidate = module_candidate(
                        module_name,
                        definitely_local=definitely_local,
                    )
                    if candidate is not None:
                        local_dependencies.add(candidate)
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    if id(node) in dynamic_argument_nodes:
                        continue
                    literal_path = PurePosixPath(node.value)
                    if node.value.endswith(".py") and "/" not in node.value:
                        candidate = f"researcher/scripts/{node.value}"
                        if (self.root / candidate).is_file():
                            local_dependencies.add(candidate)
                    elif (
                        len(literal_path.parts) == 3
                        and literal_path.parts[:2] == ("researcher", "scripts")
                        and literal_path.name.endswith(".py")
                        and str(literal_path) == node.value
                    ):
                        local_dependencies.add(node.value)
            for dependency in sorted(local_dependencies):
                discovered_dependencies.add(dependency)
                # AST discovery is diagnostic only. Never read or source-bind
                # a path until the explicit support manifest has independently
                # admitted it.
                if dependency in registered_python and dependency not in visited:
                    pending.append(dependency)

        for relative in sorted(discovered_dependencies - registered_python):
            path = self.root / relative
            self.add_finding(
                "UNREGISTERED_SUPERVISED_LOOP_DEPENDENCY",
                path,
                "local runtime dependency is absent from the declared supervised-loop support manifest",
                relative,
            )

        support_records: list[dict[str, Any]] = []
        for relative in support_paths:
            path = self.root / relative
            if not path.is_file():
                self.add_finding(
                    "PARSE_ERROR",
                    path,
                    "supervised-loop support file is missing",
                    relative,
                )
                continue
            digest, size = self.add_source(path)
            support_records.append(
                {"path": relative, "digest": digest, "size_bytes": size}
            )

        return self._category(
            "legacy supervised loop; replacement authority belongs to SPEC-004, SPEC-005, SPEC-008, SPEC-009, SPEC-010, and SPEC-025",
            records,
            support_files=support_records,
            binding_scope="declared_component_binding",
            support_manifest={
                "kind": "explicit_declared_nonexhaustive",
                "closed_roots": [
                    root_relative
                    for root_relative, _expected, _exclusions in SUPERVISED_CLOSED_ROOTS
                ],
                "package_initializers": list(SUPERVISED_PACKAGE_INITIALIZERS),
                "reference_fixture": {
                    "files": len(REFERENCE_RUN_FILES),
                    "directories": len(REFERENCE_RUN_DIRECTORIES),
                },
                "generated_cache_exclusion": "ordinary_cpython_bytecode_only",
            },
            ast_scan="defense_in_depth_nonexhaustive",
            digest_role="inventory_input_change_detection_only_not_freeze_or_security_boundary",
            result_reproducibility="not_claimed_for_daily_status_or_validator_results",
            status={
                "launchd_installer": "disabled",
                "launchd_wrappers": "dormant_inert",
                "direct_execution": "supervised_only",
                "declared_network_retrieval": "removed",
                "runtime_authority": "none",
                "scenario_execution": "catalog_only",
            },
        )

    def build_schemas(self) -> dict[str, Any]:
        path = self.root / "researcher" / "corpus" / "inventory.schema.json"
        value = self.load_json(path)
        records: list[dict[str, Any]] = []
        if isinstance(value, dict):
            records.append(
                {
                    "id": "repository-inventory-v1",
                    "path": self.relative(path),
                    "schema_id": value.get("$id"),
                    "digest": record_digest(value),
                }
            )
        return self._category("researcher/corpus/inventory.schema.json", records)

    def build_export_contracts(self) -> dict[str, Any]:
        paths = [
            "governance/export-policy.yaml",
            "governance/export-policy.schema.json",
            "researcher/exports/schemas/export-records.schema.json",
            "researcher/fixtures/export/restricted-request.json",
            "researcher/fixtures/export/private-root/restricted-source.json",
            "researcher/exports/examples/restricted-citation-v1/export-manifest.json",
            "researcher/exports/examples/restricted-citation-v1/citation/restricted-fixture.json",
            "researcher/scripts/export_policy.py",
        ]
        records: list[dict[str, Any]] = []
        for relative in paths:
            path = self.root / relative
            if not path.exists():
                self.add_finding("PARSE_ERROR", path, "export contract artifact is missing", relative)
                continue
            digest, size = self.add_source(path)
            records.append({"id": relative, "path": relative, "digest": digest, "size_bytes": size})
        return self._category("governance/export-policy.yaml and export fixtures", records)

    def build_schema_contracts(self) -> dict[str, Any]:
        registry_path = self.root / "researcher/schemas/registry.json"
        registry = self.load_json(registry_path)
        records: list[dict[str, Any]] = []
        if not isinstance(registry, dict) or not isinstance(registry.get("entries"), list):
            self.add_finding("UNKNOWN_SCHEMA", registry_path, "schema registry has no entries array")
            return self._category("researcher/schemas/registry.json", records)
        seen: set[tuple[str, str]] = set()
        id_prefixes = registry.get("id_prefixes")
        registered_prefixes: dict[str, str] = {}
        for index, entry in enumerate(registry["entries"]):
            if not isinstance(entry, dict):
                self.add_finding("UNKNOWN_SCHEMA", registry_path, f"entry {index} is not an object")
                continue
            kind = entry.get("kind")
            version = entry.get("version")
            if not isinstance(kind, str) or not isinstance(version, str):
                self.add_finding("UNKNOWN_SCHEMA", registry_path, f"entry {index} lacks kind/version")
                continue
            key = (kind, version)
            if key in seen:
                self.add_finding("DUPLICATE_SCHEMA_ID", registry_path, "kind/version is duplicated", kind)
            seen.add(key)
            prefix = entry.get("id_prefix")
            if isinstance(prefix, str):
                registered_prefixes[prefix] = kind
            schema_relative = entry.get("schema_path")
            expected_digest = entry.get("schema_digest")
            if not isinstance(schema_relative, str) or not isinstance(expected_digest, str):
                self.add_finding("UNKNOWN_SCHEMA", registry_path, "schema path or digest is missing", kind)
                continue
            schema_path = self.root / schema_relative
            if not schema_path.is_file():
                self.add_finding("PARSE_ERROR", schema_path, "registered schema file is missing", kind)
                continue
            digest, _ = self.add_source(schema_path)
            if digest != expected_digest:
                self.add_finding(
                    "SCHEMA_DIGEST_MISMATCH",
                    schema_path,
                    f"registry={expected_digest}, actual={digest}",
                    kind,
                )
            golden_paths = entry.get("golden_paths")
            if not isinstance(golden_paths, list) or not golden_paths:
                self.add_finding("UNKNOWN_SCHEMA", registry_path, "schema has no golden", kind)
            else:
                for golden_relative in golden_paths:
                    if not isinstance(golden_relative, str):
                        self.add_finding("UNKNOWN_SCHEMA", registry_path, "golden path is not text", kind)
                        continue
                    golden_path = self.root / golden_relative
                    if not golden_path.is_file():
                        self.add_finding("PARSE_ERROR", golden_path, "registered golden is missing", kind)
                    else:
                        self.add_source(golden_path)
            records.append(
                {
                    "id": f"{kind}@{version}",
                    "kind": kind,
                    "version": version,
                    "schema_path": schema_relative,
                    "schema_digest": digest,
                    "owner_spec": entry.get("owner_spec"),
                    "status": entry.get("status"),
                    "compatibility": entry.get("compatibility"),
                    "id_prefix": prefix,
                }
            )
        if id_prefixes != registered_prefixes:
            self.add_finding(
                "SCHEMA_PREFIX_MISMATCH",
                registry_path,
                "registry id_prefixes disagree with schema entries",
            )
        supporting_paths = [
            "researcher/schemas/registry.schema.json",
            "researcher/schemas/fixtures/canonicalization-v1.json",
            "researcher/schemas/fixtures/editable-surface-policy-v1.json",
            "researcher/schemas/public-legacy-sources.json",
            "researcher/schemas/generated/conformance-report.json",
            "researcher/schemas/generated/current-artifacts-report.json",
            "researcher/schemas/generated/migration-dry-run.json",
            "researcher/schemas/generated/compatibility-matrix.md",
            "researcher/schemas/README.md",
            "researcher/artifacts/README.md",
            "researcher/runbooks/schema-migration.md",
            "researcher/scripts/schema_contract.py",
            "researcher/scripts/artifact_store.py",
            "researcher/scripts/migrate_legacy.py",
            "researcher/scripts/tests/test_schema_contract.py",
            "researcher/scripts/tests/test_artifact_store.py",
            "researcher/schemas/typescript/.gitignore",
            "researcher/schemas/typescript/package.json",
            "researcher/schemas/typescript/package-lock.json",
            "researcher/schemas/typescript/tsconfig.json",
            "researcher/schemas/typescript/src/canonicalize.ts",
            "researcher/schemas/typescript/src/conformance.ts",
            "researcher/schemas/typescript/src/errors.ts",
            "researcher/schemas/typescript/src/index.ts",
            "researcher/schemas/typescript/src/json.ts",
            "researcher/schemas/typescript/src/registry.ts",
            "researcher/schemas/typescript/src/semantics.ts",
            "researcher/schemas/typescript/test/conformance.test.ts",
            "researcher/schemas/typescript/test/runtime-registry.test.ts",
        ]
        for relative in supporting_paths:
            path = self.root / relative
            if not path.is_file():
                self.add_finding("PARSE_ERROR", path, "schema contract artifact is missing", relative)
            else:
                self.add_source(path)
        return self._category(
            "researcher/schemas/registry.json",
            sorted(records, key=lambda item: item["id"]),
            canonicalization_profile=registry.get("canonicalization_profile"),
            id_prefix_count=len(registered_prefixes),
        )

    def build_authority_contracts(self) -> dict[str, Any]:
        """Inventory the standalone schema without treating it as authority."""

        path = self.root / AUTHORITY_VOCABULARY_SCHEMA_PATH
        source_digest, _size_bytes = self.add_source(path)
        records: list[dict[str, Any]] = []
        try:
            schema = load_authority_vocabulary_schema(self.root)
        except (OSError, UnicodeError, ValueError) as exc:
            self.add_finding(
                "AUTHORITY_VOCABULARY_SCHEMA_INVALID",
                path,
                str(exc),
                "authority-vocabulary-schema@2.0.0",
            )
            return self._category(AUTHORITY_VOCABULARY_SPEC, records)
        if (
            schema.path != AUTHORITY_VOCABULARY_SCHEMA_PATH
            or schema.schema_id != AUTHORITY_VOCABULARY_SCHEMA_ID
            or schema.schema_version != AUTHORITY_VOCABULARY_SCHEMA_VERSION
            or schema.digest != source_digest
        ):
            self.add_finding(
                "AUTHORITY_VOCABULARY_SCHEMA_INVALID",
                path,
                "authority schema loader and inventory source identity differ",
                "authority-vocabulary-schema@2.0.0",
            )
            return self._category(AUTHORITY_VOCABULARY_SPEC, records)
        authority_binding = self._authority_binding
        binding_state = (
            "bound"
            if authority_binding is not None
            and authority_binding.schema_path == schema.path
            and authority_binding.schema_digest == schema.digest
            and authority_binding.schema_version == schema.schema_version
            else "dormant_unbound"
        )
        records.append(
            {
                "id": "authority-vocabulary-schema@2.0.0",
                "kind": "AuthorityVocabularySchema",
                "path": schema.path,
                "schema_id": schema.schema_id,
                "version": schema.schema_version,
                "digest": schema.digest,
                "binding_state": binding_state,
            }
        )
        return self._category(AUTHORITY_VOCABULARY_SPEC, records)

    def build_orchestration_briefs(self) -> dict[str, Any]:
        """Bind the non-authoritative long-horizon bootstrap prompt bundle."""

        expected = {
            "docs/reviews/2026-08-15-autonomous-organization-readiness.md": "readiness_review",
            "researcher/orchestration/prompts/README.md": "bundle_contract",
            "researcher/orchestration/prompts/attempt-manifest.template.md": "attempt_manifest_template",
            "researcher/orchestration/prompts/fresh-verifier-brief.md": "verifier_brief",
            "researcher/orchestration/prompts/organization-root-brief.md": "root_brief",
            "researcher/orchestration/prompts/resume-brief.template.md": "resume_template",
            "researcher/orchestration/prompts/spec-work-brief.template.md": "work_brief_template",
        }
        prompt_root = self.root / "researcher" / "orchestration" / "prompts"
        discovered: set[str] = set()
        if prompt_root.is_dir():
            for path in sorted(prompt_root.rglob("*")):
                if not path.is_file() and not path.is_symlink():
                    continue
                relative = self.relative(path)
                discovered.add(relative)
                if relative not in expected:
                    self.add_source(path)
                    self.add_finding(
                        "UNREGISTERED_ORCHESTRATION_BRIEF",
                        path,
                        "orchestration prompt namespace is closed; register or remove this file",
                    )

        records: list[dict[str, Any]] = []
        for relative, role in sorted(expected.items()):
            path = self.root / relative
            if not path.is_file():
                self.add_finding(
                    "PARSE_ERROR",
                    path,
                    "registered orchestration brief is missing",
                    relative,
                )
                continue
            digest, size = self.add_source(path)
            records.append(
                {
                    "id": relative,
                    "path": relative,
                    "role": role,
                    "digest": digest,
                    "size_bytes": size,
                    "status": "bootstrap_proposal",
                }
            )

        return self._category(
            "SPEC-005, SPEC-012, SPEC-013, and SPEC-014 bootstrap proposal",
            records,
            authority="none",
            activation_ceiling="supervised_proposal",
            enforcement_boundary="external_harness",
            attempt_manifest_instance_classification="private",
            model_visible_launch="allowlisted_new_identity_projection_only",
            public_projection="allowlisted_new_identity_projection_only",
            checkpoint_contract=(
                "SPEC-005 CheckpointEnvelope with SPEC-012 ContextCheckpointPayload"
            ),
            attempt_separation="builder_and_verifier_distinct",
            closed_prompt_namespace=prompt_root.is_dir() and discovered <= set(expected),
        )

    def build_specifications(self) -> dict[str, Any]:
        """Build and validate the canonical specification dependency graph."""

        self._authority_binding = None
        specs_dir = self.root / "docs" / "specs"
        index_path = specs_dir / "README.md"
        template_path = specs_dir / "SPEC-TEMPLATE.md"
        lifecycle_validator_path = self.root / "researcher" / "scripts" / "validate_spec_lifecycle.py"
        lifecycle_test_path = (
            self.root / "researcher" / "scripts" / "tests" / "test_spec_lifecycle.py"
        )
        for supporting_path in (
            index_path,
            template_path,
            lifecycle_validator_path,
            lifecycle_test_path,
        ):
            if supporting_path.is_file():
                self.add_source(supporting_path)
            else:
                self.add_finding(
                    "PARSE_ERROR",
                    supporting_path,
                    "specification program supporting document is missing",
                )

        try:
            index_text = self.read_source_text(index_path)
        except (OSError, UnicodeError, InventoryError):
            index_text = ""

        roadmap_sections, malformed_roadmap = markdown_level_two_sections(index_text)
        if malformed_roadmap:
            self.add_finding(
                "INVALID_SPEC_INDEX",
                index_path,
                "roadmap contains an unclosed HTML comment or fenced block",
            )
        if contains_raw_html_block(index_text):
            self.add_finding(
                "INVALID_SPEC_INDEX",
                index_path,
                "canonical roadmap cannot contain raw HTML blocks",
            )
        index_sections = roadmap_sections.get("Specification index", [])
        if len(index_sections) != 1:
            self.add_finding(
                "INVALID_SPEC_INDEX",
                index_path,
                f"expected one visible Specification index section, found {len(index_sections)}",
            )
            visible_index_lines: list[str] = []
        else:
            visible_index_lines = visible_unfenced_lines(index_sections[0])

        index_link_counts: dict[str, int] = {}
        index_link_numbers: dict[str, str] = {}
        for line in visible_index_lines:
            index_match = SPEC_INDEX_ROW_RE.fullmatch(line)
            if index_match is None:
                continue
            target = index_match.group("path")
            index_link_counts[target] = index_link_counts.get(target, 0) + 1
            index_link_numbers[target] = index_match.group("number")

        records: list[dict[str, Any]] = []
        specs_by_id: dict[str, dict[str, Any]] = {}
        paths_by_id: dict[str, Path] = {}
        lifecycle_specs: dict[str, SpecRevision] = {}
        candidate_paths = sorted(
            path
            for path in specs_dir.rglob("*")
            if path.is_file()
            and path not in {index_path, template_path}
        )
        specification_paths: list[Path] = []
        for path in candidate_paths:
            if path.parent != specs_dir:
                self.add_source(path)
                self.add_finding(
                    "INVALID_SPEC_PATH",
                    path,
                    "canonical specifications must be direct children of docs/specs",
                )
                continue
            specification_paths.append(path)
        for path in specification_paths:
            digest, _ = self.add_source(path)
            filename_match = SPEC_FILENAME_RE.fullmatch(path.name)
            if filename_match is None:
                self.add_finding(
                    "INVALID_SPEC_FILENAME",
                    path,
                    "specification filename must match SPEC-NNN-lowercase-slug.md",
                )
                continue
            filename_number = filename_match.group("number")
            filename_id = f"SPEC-{filename_number}"
            try:
                exact_bytes = self.read_source_bytes(path)
                text = exact_bytes.decode("utf-8")
            except (OSError, UnicodeError, InventoryError) as exc:
                self.add_finding("PARSE_ERROR", path, str(exc), filename_id)
                continue
            if b"\r" in exact_bytes:
                self.add_finding(
                    "INVALID_SPEC_ENCODING",
                    path,
                    "canonical specifications must use LF line endings",
                    filename_id,
                )
            lines = text.splitlines()
            heading_match = SPEC_HEADING_RE.fullmatch(lines[0] if lines else "")
            if heading_match is None:
                self.add_finding(
                    "INVALID_SPEC_HEADING",
                    path,
                    "first line must be '# SPEC-NNN: Title'",
                    filename_id,
                )
                continue
            heading_number = heading_match.group("number")
            spec_id = f"SPEC-{heading_number}"
            if heading_number != filename_number:
                self.add_finding(
                    "SPEC_FILENAME_MISMATCH",
                    path,
                    f"heading {spec_id} does not match filename {filename_id}",
                    spec_id,
                )

            try:
                lifecycle_record = parse_spec_revision(
                    self.relative(path),
                    exact_bytes,
                    allow_legacy=False,
                )
            except ValueError:
                lifecycle_record = None
            if lifecycle_record is not None and lifecycle_record.spec_id not in lifecycle_specs:
                lifecycle_specs[lifecycle_record.spec_id] = lifecycle_record

            metadata: dict[str, str] = {}
            metadata_order: list[str] = []
            for raw_line in lines[1:]:
                stripped = raw_line.strip()
                if stripped.startswith("## "):
                    break
                if not stripped:
                    continue
                if ":" not in stripped:
                    self.add_finding(
                        "INVALID_SPEC_METADATA",
                        path,
                        f"metadata line has no colon: {stripped!r}",
                        spec_id,
                    )
                    continue
                key, value = (part.strip() for part in stripped.split(":", 1))
                if raw_line != f"{key}: {value}":
                    self.add_finding(
                        "INVALID_SPEC_METADATA_FORMAT",
                        path,
                        "metadata must use canonical 'Key: value' serialization without extra whitespace",
                        spec_id,
                    )
                if key in metadata:
                    self.add_finding(
                        "INVALID_SPEC_METADATA",
                        path,
                        f"duplicate metadata key: {key}",
                        spec_id,
                    )
                else:
                    metadata_order.append(key)
                metadata[key] = value

            order_index = {key: index for index, key in enumerate(SPEC_METADATA_ORDER)}
            known_order = [key for key in metadata_order if key in order_index]
            if known_order != sorted(known_order, key=order_index.__getitem__):
                self.add_finding(
                    "INVALID_SPEC_METADATA_ORDER",
                    path,
                    "specification metadata must use canonical header order",
                    spec_id,
                )

            missing = [key for key in SPEC_REQUIRED_METADATA if not metadata.get(key)]
            unknown = sorted(
                set(metadata) - set(SPEC_REQUIRED_METADATA) - SPEC_OPTIONAL_METADATA
            )
            if missing:
                self.add_finding(
                    "INVALID_SPEC_METADATA",
                    path,
                    f"missing metadata: {', '.join(missing)}",
                    spec_id,
                )
            if unknown:
                self.add_finding(
                    "INVALID_SPEC_METADATA",
                    path,
                    f"unknown metadata: {', '.join(unknown)}",
                    spec_id,
                )
            if (
                spec_id != AUTHORITY_VOCABULARY_SPEC
                and AUTHORITY_VOCABULARY_METADATA_KEYS.intersection(metadata)
            ):
                self.add_finding(
                    "INVALID_SPEC_METADATA",
                    path,
                    "Authority vocabulary metadata is valid only on SPEC-000",
                    spec_id,
                )

            status_value = metadata.get("Status", "")
            if status_value not in SPEC_STATUSES:
                self.add_finding(
                    "INVALID_SPEC_STATUS",
                    path,
                    f"unsupported status: {status_value!r}",
                    spec_id,
                )
            try:
                revision = int(metadata.get("Revision", ""))
            except ValueError:
                revision = -1
            if revision < 1:
                self.add_finding(
                    "INVALID_SPEC_REVISION",
                    path,
                    f"Revision must be a positive integer: {metadata.get('Revision')!r}",
                    spec_id,
                )
            revises = metadata.get("Revises", "")
            if revision == 1 and revises != "none":
                self.add_finding(
                    "INVALID_SPEC_REVISION",
                    path,
                    "revision 1 must declare Revises: none",
                    spec_id,
                )
            elif revision > 1 and SPEC_REVISION_DIGEST_RE.fullmatch(revises) is None:
                self.add_finding(
                    "INVALID_SPEC_REVISION",
                    path,
                    "revision greater than 1 must bind the prior file digest",
                    spec_id,
                )
            if spec_id == "SPEC-026" and revision == 1 and metadata.get("Activation") != "deferred":
                self.add_finding(
                    "INVALID_SPEC_ACTIVATION",
                    path,
                    "SPEC-026 revision 1 must remain Activation: deferred",
                    spec_id,
                )
            lifecycle_decision = metadata.get("Lifecycle decision")
            adoption_decision = metadata.get("Adoption decision")
            if adoption_decision is not None and (
                SPEC_LIFECYCLE_DECISION_RE.fullmatch(adoption_decision) is None
            ):
                self.add_finding(
                    "INVALID_SPEC_ADOPTION_DECISION",
                    path,
                    f"Adoption decision must be ADR-NNNN: {adoption_decision!r}",
                    spec_id,
                )
            if (
                lifecycle_decision is not None
                and SPEC_LIFECYCLE_DECISION_RE.fullmatch(lifecycle_decision) is None
            ):
                self.add_finding(
                    "INVALID_SPEC_LIFECYCLE_DECISION",
                    path,
                    f"Lifecycle decision must be ADR-NNNN: {lifecycle_decision!r}",
                    spec_id,
                )
            if status_value not in SPEC_TERMINAL_STATUSES and lifecycle_decision is not None:
                self.add_finding(
                    "INVALID_SPEC_LIFECYCLE_DECISION",
                    path,
                    "Lifecycle decision is valid only on a terminal specification revision",
                    spec_id,
                )
            replacement = metadata.get("Replacement")
            if replacement is not None and replacement != "none" and (
                SPEC_REPLACEMENT_RE.fullmatch(replacement) is None
            ):
                self.add_finding(
                    "INVALID_SPEC_REPLACEMENT",
                    path,
                    f"Replacement must be none or SPEC-NNN@revision: {replacement!r}",
                    spec_id,
                )
            if status_value in SPEC_TERMINAL_STATUSES and lifecycle_decision is None:
                self.add_finding(
                    "MISSING_SPEC_LIFECYCLE_DECISION",
                    path,
                    f"{status_value} specifications require a Lifecycle decision",
                    spec_id,
                )
            if status_value in {"amended", "superseded"} and (
                replacement is None or replacement == "none"
            ):
                self.add_finding(
                    "MISSING_SPEC_REPLACEMENT",
                    path,
                    f"{status_value} specifications require a replacement revision",
                    spec_id,
                )
            elif status_value in {"amended", "superseded"}:
                expected_replacement = f"{spec_id}@{revision + 1}"
                if replacement != expected_replacement:
                    self.add_finding(
                        "INVALID_SPEC_REPLACEMENT",
                        path,
                        f"{status_value} must name {expected_replacement}",
                        spec_id,
                    )
            if status_value == "retired" and replacement not in {None, "none"}:
                self.add_finding(
                    "INVALID_SPEC_REPLACEMENT",
                    path,
                    "retired specifications cannot name a replacement revision",
                    spec_id,
                )
            if status_value not in SPEC_TERMINAL_STATUSES and replacement is not None:
                self.add_finding(
                    "INVALID_SPEC_REPLACEMENT",
                    path,
                    "Replacement is valid only on a terminal specification revision",
                    spec_id,
                )
            try:
                wave = int(metadata.get("Wave", ""))
            except ValueError:
                wave = -1
            if wave < 0 or wave > 6:
                self.add_finding(
                    "INVALID_SPEC_WAVE",
                    path,
                    f"wave must be an integer from 0 through 6: {metadata.get('Wave')!r}",
                    spec_id,
                )
            classification = metadata.get("Classification", "")
            if classification not in SPEC_CLASSIFICATIONS:
                self.add_finding(
                    "INVALID_SPEC_CLASSIFICATION",
                    path,
                    f"unsupported classification: {classification!r}",
                    spec_id,
                )
            owners = [owner.strip() for owner in metadata.get("Owners", "").split(";") if owner.strip()]
            if not owners:
                self.add_finding(
                    "INVALID_SPEC_METADATA",
                    path,
                    "Owners must contain at least one role",
                    spec_id,
                )
            depends_value = metadata.get("Depends on", "")
            dependencies = [] if depends_value == "none" else [
                dependency.strip() for dependency in depends_value.split(",") if dependency.strip()
            ]
            duplicate_dependencies = sorted(
                dependency for dependency in set(dependencies) if dependencies.count(dependency) > 1
            )
            if duplicate_dependencies:
                self.add_finding(
                    "DUPLICATE_SPEC_DEPENDENCY",
                    path,
                    f"duplicate dependency identifiers: {', '.join(duplicate_dependencies)}",
                    spec_id,
                )
            if depends_value != "none" and depends_value != ", ".join(dependencies):
                self.add_finding(
                    "INVALID_SPEC_DEPENDENCY",
                    path,
                    "dependencies must be comma-and-space separated in canonical order",
                    spec_id,
                )
            invalid_dependencies = [dependency for dependency in dependencies if not SPEC_ID_RE.fullmatch(dependency)]
            if invalid_dependencies:
                self.add_finding(
                    "INVALID_SPEC_DEPENDENCY",
                    path,
                    f"invalid dependency identifiers: {', '.join(invalid_dependencies)}",
                    spec_id,
                )

            record = {
                "id": spec_id,
                "title": heading_match.group("title"),
                "status": status_value,
                "revision": revision,
                "revises": revises,
                "wave": wave,
                "classification": classification,
                "owners": owners,
                "dependencies": dependencies,
                "path": self.relative(path),
                "digest": digest,
            }
            if "Activation" in metadata:
                record["activation"] = metadata["Activation"]
            if adoption_decision is not None:
                record["adoption_decision"] = adoption_decision
            if "Dependency revisions" in metadata:
                record["dependency_revisions"] = metadata["Dependency revisions"]
            if lifecycle_decision is not None:
                record["lifecycle_decision"] = lifecycle_decision
            if replacement is not None:
                record["replacement"] = replacement
            if spec_id in specs_by_id:
                self.add_finding(
                    "DUPLICATE_SPEC_ID",
                    path,
                    f"identifier already declared by {self.relative(paths_by_id[spec_id])}",
                    spec_id,
                )
            else:
                specs_by_id[spec_id] = record
                paths_by_id[spec_id] = path
            records.append(record)

        authority_binding: AuthorityVocabularyBinding | None = None
        authority_binding_error = False
        canonical_authority_paths = (
            AUTHORITY_VOCABULARY_PATH,
            AUTHORITY_FIXTURE_MANIFEST_PATH,
            AUTHORITY_CONFORMANCE_RECEIPT_PATH,
        )
        present_authority_paths: list[str] = []
        for relative in canonical_authority_paths:
            authority_path = self.root / relative
            if os.path.lexists(authority_path):
                present_authority_paths.append(relative)
                self.add_source(authority_path)
        conformance_path = self.root / AUTHORITY_CONFORMANCE_RECEIPT_PATH
        if os.path.lexists(conformance_path):
            for relative in (
                AUTHORITY_CONSTITUTION_POLICY_PATH,
                *AUTHORITY_EVALUATOR_COMPONENT_PATHS,
            ):
                authority_input = self.root / relative
                if os.path.lexists(authority_input):
                    self.add_source(authority_input)
        try:
            authority_binding = load_candidate_authority_vocabulary(
                self.root,
                lifecycle_specs,
            )
        except (OSError, UnicodeError, ValueError) as exc:
            authority_binding_error = True
            authority_spec_path = paths_by_id.get(
                AUTHORITY_VOCABULARY_SPEC,
                self.root / AUTHORITY_VOCABULARY_PATH,
            )
            self.add_finding(
                "SPEC_AUTHORITY_VOCABULARY_INVALID",
                authority_spec_path,
                str(exc),
                AUTHORITY_VOCABULARY_SPEC,
            )

        authority_spec_record = specs_by_id.get(AUTHORITY_VOCABULARY_SPEC)
        authority_spec_revision = lifecycle_specs.get(AUTHORITY_VOCABULARY_SPEC)
        authority_artifacts_declared = (
            authority_spec_revision is not None
            and authority_spec_revision.revision >= AUTHORITY_VOCABULARY_MIN_REVISION
            and AUTHORITY_VOCABULARY_METADATA_KEYS.issubset(
                authority_spec_revision.metadata
            )
        )
        if not authority_artifacts_declared:
            for relative in present_authority_paths:
                self.add_finding(
                    "UNEXPECTED_AUTHORITY_ARTIFACT",
                    self.root / relative,
                    "authority artifacts require the complete canonical metadata binding "
                    "on SPEC-000 revision 2 or later",
                    AUTHORITY_VOCABULARY_SPEC,
                )
        if (
            AUTHORITY_CONFORMANCE_RECEIPT_PATH in present_authority_paths
            and authority_spec_record is not None
            and authority_spec_record["status"]
            in {"draft", "architecture_reviewed", "accepted"}
        ):
            self.add_finding(
                "UNEXPECTED_AUTHORITY_ARTIFACT",
                self.root / AUTHORITY_CONFORMANCE_RECEIPT_PATH,
                "authority-policy conformance is an implementation-stage artifact and "
                "must be absent before SPEC-000 is implemented",
                AUTHORITY_VOCABULARY_SPEC,
            )
        if authority_binding is not None and authority_spec_record is not None:
            self._authority_binding = authority_binding
            authority_record: dict[str, Any] = {
                "schema": {
                    "path": authority_binding.schema_path,
                    "digest": authority_binding.schema_digest,
                    "version": authority_binding.schema_version,
                },
                "path": authority_binding.path,
                "digest": authority_binding.digest,
                "schema_version": authority_binding.registry_schema_version,
                "constitution_revision": authority_binding.constitution_revision,
                "registry_version": authority_binding.registry_version,
                "fixture_manifest": {
                    "path": authority_binding.fixture_manifest_path,
                    "digest": authority_binding.fixture_manifest_digest,
                    "version": authority_binding.fixture_manifest_version,
                },
            }
            conformance = authority_binding.policy_conformance
            if conformance is not None:
                authority_record["policy_conformance"] = {
                    "path": conformance.path,
                    "digest": conformance.digest,
                    "schema_version": conformance.schema_version,
                    "scope": conformance.scope,
                    "runtime_authority": conformance.runtime_authority,
                    "constitution_policy_digest": conformance.constitution_policy_digest,
                    "registry_digest": conformance.registry_digest,
                    "fixture_manifest_digest": conformance.fixture_manifest_digest,
                    "validator_bundle": {
                        "algorithm": conformance.validator_bundle_algorithm,
                        "version": conformance.validator_bundle_version,
                        "components": [
                            {
                                "path": component.path,
                                "digest": component.digest,
                            }
                            for component in conformance.validator_bundle_components
                        ],
                        "digest": conformance.validator_bundle_digest,
                    },
                    "case_count": conformance.case_count,
                }
            authority_spec_record["authority_vocabulary"] = authority_record

        if (
            authority_spec_record is not None
            and authority_spec_record["revision"] >= AUTHORITY_VOCABULARY_MIN_REVISION
            and authority_binding is None
            and not authority_binding_error
        ):
            self.add_finding(
                "SPEC_AUTHORITY_VOCABULARY_INVALID",
                paths_by_id[AUTHORITY_VOCABULARY_SPEC],
                "SPEC-000 revision 2 or later requires the exact revision-bound, "
                "digest-pinned AuthorityVocabularyRegistry and fixture manifest",
                AUTHORITY_VOCABULARY_SPEC,
            )
        if (
            authority_spec_record is not None
            and authority_spec_record["revision"] >= AUTHORITY_VOCABULARY_MIN_REVISION
            and authority_spec_record["status"] in AUTHORITY_IMPLEMENTED_STATUSES
            and (
                authority_binding is None
                or authority_binding.policy_conformance is None
            )
        ):
            self.add_finding(
                "SPEC_AUTHORITY_POLICY_CONFORMANCE_REQUIRED",
                paths_by_id[AUTHORITY_VOCABULARY_SPEC],
                "implemented, verified, and operational SPEC-000 revisions require "
                "the exact validated authority-policy conformance receipt",
                AUTHORITY_VOCABULARY_SPEC,
            )

        for spec_id, record in sorted(specs_by_id.items()):
            for dependency in record["dependencies"]:
                target = specs_by_id.get(dependency)
                if target is None:
                    self.add_finding(
                        "DANGLING_SPEC_DEPENDENCY",
                        paths_by_id[spec_id],
                        f"dependency does not exist: {dependency}",
                        spec_id,
                    )
                    continue
                if dependency == spec_id:
                    self.add_finding(
                        "SPEC_DEPENDENCY_CYCLE",
                        paths_by_id[spec_id],
                        "specification depends on itself",
                        spec_id,
                    )
                if target["wave"] > record["wave"]:
                    self.add_finding(
                        "INVALID_SPEC_WAVE",
                        paths_by_id[spec_id],
                        f"wave {record['wave']} depends on later wave {target['wave']} ({dependency})",
                        spec_id,
                    )

        visit_state: dict[str, int] = {}
        cycle_reports: set[tuple[str, ...]] = set()

        def visit(spec_id: str, stack: tuple[str, ...]) -> None:
            state = visit_state.get(spec_id, 0)
            if state == 2:
                return
            if state == 1:
                start = stack.index(spec_id)
                cycle = stack[start:] + (spec_id,)
                normalized = tuple(sorted(set(cycle)))
                if normalized not in cycle_reports:
                    cycle_reports.add(normalized)
                    self.add_finding(
                        "SPEC_DEPENDENCY_CYCLE",
                        paths_by_id[spec_id],
                        f"dependency cycle: {' -> '.join(cycle)}",
                        spec_id,
                    )
                return
            visit_state[spec_id] = 1
            for dependency in specs_by_id[spec_id]["dependencies"]:
                if dependency in specs_by_id:
                    visit(dependency, stack + (spec_id,))
            visit_state[spec_id] = 2

        for spec_id in sorted(specs_by_id):
            visit(spec_id, ())

        graph_edges: list[tuple[str, str]] = []
        graph_label_counts: dict[str, int] = {}
        dependency_sections = roadmap_sections.get("Dependency graph", [])
        if len(dependency_sections) != 1:
            self.add_finding(
                "INVALID_SPEC_GRAPH",
                index_path,
                f"expected one visible Dependency graph section, found {len(dependency_sections)}",
            )
            graph_lines: list[str] = []
        else:
            graph_blocks, malformed_fence = fenced_blocks(dependency_sections[0], "mermaid")
            if malformed_fence or len(graph_blocks) != 1:
                self.add_finding(
                    "INVALID_SPEC_GRAPH",
                    index_path,
                    f"expected one complete visible mermaid block, found {len(graph_blocks)}",
                )
                graph_lines = []
            else:
                graph_lines = graph_blocks[0]
        nonblank_graph_lines = [
            (line_number, line.strip())
            for line_number, line in enumerate(graph_lines, start=1)
            if line.strip()
        ]
        flowchart_lines = [
            line_number
            for line_number, line in nonblank_graph_lines
            if line == "flowchart TD"
        ]
        if not nonblank_graph_lines or nonblank_graph_lines[0][1] != "flowchart TD":
            self.add_finding(
                "INVALID_SPEC_GRAPH",
                index_path,
                "mermaid dependency graph must begin with 'flowchart TD'",
            )
        if len(flowchart_lines) != 1:
            self.add_finding(
                "INVALID_SPEC_GRAPH",
                index_path,
                f"mermaid dependency graph must contain one 'flowchart TD' declaration, found {len(flowchart_lines)}",
            )
        for line_number, line in enumerate(graph_lines, start=1):
            stripped = line.strip()
            if not stripped or stripped == "flowchart TD":
                continue
            if "-->" not in line:
                self.add_finding(
                    "INVALID_SPEC_GRAPH_LINE",
                    index_path,
                    f"line {line_number} is not a dependency edge",
                )
                continue
            graph_match = SPEC_GRAPH_EDGE_RE.fullmatch(line)
            if graph_match is None:
                self.add_finding(
                    "INVALID_SPEC_GRAPH_LINE",
                    index_path,
                    f"line {line_number} is not a canonical SNNN --> SNNN edge",
                )
                continue
            graph_edges.append(
                (
                    f"SPEC-{graph_match.group('source')}",
                    f"SPEC-{graph_match.group('target')}",
                )
            )
            for endpoint, label in (
                (f"SPEC-{graph_match.group('source')}", graph_match.group("source_label")),
                (f"SPEC-{graph_match.group('target')}", graph_match.group("target_label")),
            ):
                endpoint_record = specs_by_id.get(endpoint)
                if label is None or endpoint_record is None:
                    continue
                graph_label_counts[endpoint] = graph_label_counts.get(endpoint, 0) + 1
                expected_label = f"{endpoint} {endpoint_record['title']}"
                if label != expected_label:
                    self.add_finding(
                        "SPEC_GRAPH_LABEL_MISMATCH",
                        index_path,
                        f"graph label for {endpoint} must be {expected_label!r}",
                        endpoint,
                    )

        for spec_id in sorted(specs_by_id):
            label_count = graph_label_counts.get(spec_id, 0)
            if label_count != 1:
                self.add_finding(
                    "SPEC_GRAPH_LABEL_COUNT",
                    index_path,
                    f"{spec_id} must have exactly one canonical graph label, found {label_count}",
                    spec_id,
                )

        graph_edge_counts: dict[tuple[str, str], int] = {}
        for edge in graph_edges:
            graph_edge_counts[edge] = graph_edge_counts.get(edge, 0) + 1
        for edge, count in sorted(graph_edge_counts.items()):
            if count > 1:
                self.add_finding(
                    "DUPLICATE_SPEC_GRAPH_EDGE",
                    index_path,
                    f"dependency edge {edge[0]} -> {edge[1]} appears {count} times",
                )

        expected_graph_edges = {
            (dependency, spec_id)
            for spec_id, record in specs_by_id.items()
            for dependency in record["dependencies"]
            if dependency in specs_by_id
        }
        actual_graph_edges = set(graph_edges)
        for source, target in sorted(expected_graph_edges - actual_graph_edges):
            self.add_finding(
                "MISSING_SPEC_GRAPH_EDGE",
                index_path,
                f"dependency metadata requires {source} -> {target}",
            )
        for source, target in sorted(actual_graph_edges - expected_graph_edges):
            self.add_finding(
                "EXTRA_SPEC_GRAPH_EDGE",
                index_path,
                f"diagram edge is not declared in metadata: {source} -> {target}",
            )

        known_filenames = {path.name for path in specification_paths}
        for filename in sorted(known_filenames):
            count = index_link_counts.get(filename, 0)
            path = specs_dir / filename
            if count == 0:
                self.add_finding(
                    "MISSING_SPEC_INDEX_LINK",
                    index_path,
                    f"specification is not linked: {filename}",
                )
            elif count > 1:
                self.add_finding(
                    "DUPLICATE_SPEC_INDEX_LINK",
                    index_path,
                    f"specification is linked {count} times: {filename}",
                )
            filename_match = SPEC_FILENAME_RE.fullmatch(filename)
            if filename_match and index_link_numbers.get(filename) not in {None, filename_match.group("number")}:
                self.add_finding(
                    "SPEC_INDEX_MISMATCH",
                    index_path,
                    f"link label does not match target: {filename}",
                )
        for filename in sorted(set(index_link_counts) - known_filenames):
            self.add_finding(
                "UNKNOWN_SPEC_INDEX_LINK",
                index_path,
                f"index links an unknown specification: {filename}",
            )

        for record in records:
            if record["status"] not in {
                "architecture_reviewed",
                "accepted",
                "implemented",
                "verified",
                "operational",
            }:
                continue
            raw_bindings = record.get("dependency_revisions")
            parsed_bindings: dict[str, int] = {}
            if raw_bindings == "none":
                binding_parts: list[str] = []
            elif isinstance(raw_bindings, str):
                binding_parts = [part.strip() for part in raw_bindings.split(",")]
                if raw_bindings != ", ".join(binding_parts):
                    self.add_finding(
                        "INVALID_SPEC_DEPENDENCY_REVISIONS",
                        self.root / record["path"],
                        "dependency revision bindings must be comma-and-space separated",
                        record["id"],
                    )
            else:
                binding_parts = []
                self.add_finding(
                    "MISSING_SPEC_DEPENDENCY_REVISIONS",
                    self.root / record["path"],
                    "architecture-reviewed and later specifications must bind exact dependency revisions",
                    record["id"],
                )
            for part in binding_parts:
                match = SPEC_DEPENDENCY_REVISION_RE.fullmatch(part)
                if match is None:
                    self.add_finding(
                        "INVALID_SPEC_DEPENDENCY_REVISIONS",
                        self.root / record["path"],
                        f"invalid dependency revision binding: {part!r}",
                        record["id"],
                    )
                    continue
                dependency_id = match.group(1)
                if dependency_id in parsed_bindings:
                    self.add_finding(
                        "INVALID_SPEC_DEPENDENCY_REVISIONS",
                        self.root / record["path"],
                        f"duplicate dependency revision binding: {dependency_id}",
                        record["id"],
                    )
                    continue
                parsed_bindings[dependency_id] = int(match.group(2))
            expected_ids = set(record["dependencies"])
            if set(parsed_bindings) != expected_ids:
                self.add_finding(
                    "SPEC_DEPENDENCY_REVISION_MISMATCH",
                    self.root / record["path"],
                    "dependency revision bindings must cover the direct dependency set exactly",
                    record["id"],
                )
            if int(record["id"][-3:]) >= 4:
                authority_spec = specs_by_id.get(AUTHORITY_VOCABULARY_SPEC)
                if (
                    authority_spec is None
                    or authority_spec["revision"] < AUTHORITY_VOCABULARY_MIN_REVISION
                    or authority_spec["status"]
                    not in AUTHORITY_VOCABULARY_READY_STATUSES
                    or authority_binding is None
                    or authority_binding.constitution_revision
                    != authority_spec["revision"]
                ):
                    self.add_finding(
                        "SPEC_AUTHORITY_VOCABULARY_NOT_READY",
                        self.root / record["path"],
                        "SPEC-004 and later cannot be architecture-reviewed or active "
                        "until accepted SPEC-000 revision 2 or later is current with "
                        "its exact AuthorityVocabularyRegistry and fixture manifest",
                        record["id"],
                    )
                if record["status"] in AUTHORITY_IMPLEMENTED_STATUSES and (
                    authority_binding is None
                    or authority_binding.policy_conformance is None
                ):
                    self.add_finding(
                        "SPEC_AUTHORITY_POLICY_CONFORMANCE_REQUIRED",
                        self.root / record["path"],
                        "implemented, verified, and operational SPEC-004 and later "
                        "require the exact validated authority-policy conformance receipt",
                        record["id"],
                    )
                if (
                    AUTHORITY_VOCABULARY_SPEC in expected_ids
                    and parsed_bindings.get(AUTHORITY_VOCABULARY_SPEC, 0)
                    < AUTHORITY_VOCABULARY_MIN_REVISION
                ):
                    self.add_finding(
                        "SPEC_AUTHORITY_VOCABULARY_NOT_READY",
                        self.root / record["path"],
                        "the frozen SPEC-000 dependency must be revision 2 or later",
                        record["id"],
                    )
        return self._category(
            "docs/specs/",
            sorted(records, key=lambda item: (item["id"], item["path"])),
            lifecycle=sorted(SPEC_STATUSES),
        )

    def build_architecture_decisions(self, specification_ids: set[str]) -> dict[str, Any]:
        """Source-bind durable ADRs and validate their canonical index."""

        decisions_dir = self.root / "docs" / "decisions"
        index_path = decisions_dir / "README.md"
        if index_path.is_file():
            self.add_source(index_path)
            try:
                index_text = self.read_source_text(index_path)
            except (OSError, UnicodeError, InventoryError) as exc:
                self.add_finding("PARSE_ERROR", index_path, str(exc))
                index_text = ""
        else:
            self.add_finding("PARSE_ERROR", index_path, "architecture decision index is missing")
            index_text = ""

        decision_sections, malformed_index = markdown_level_two_sections(index_text)
        if malformed_index:
            self.add_finding(
                "INVALID_ADR_INDEX",
                index_path,
                "decision index contains an unclosed HTML comment or fenced block",
            )
        if contains_raw_html_block(index_text):
            self.add_finding(
                "INVALID_ADR_INDEX",
                index_path,
                "canonical decision index cannot contain raw HTML blocks",
            )
        records_sections = decision_sections.get("Records", [])
        if len(records_sections) != 1:
            self.add_finding(
                "INVALID_ADR_INDEX",
                index_path,
                f"expected one visible Records section, found {len(records_sections)}",
            )
            visible_record_lines: list[str] = []
        else:
            visible_record_lines = visible_unfenced_lines(records_sections[0])

        index_links: dict[str, list[tuple[str, str]]] = {}
        for line in visible_record_lines:
            match = ADR_INDEX_ROW_RE.fullmatch(line)
            if match is None:
                continue
            index_links.setdefault(match.group("path"), []).append(
                (match.group("number"), match.group("title"))
            )

        records: list[dict[str, Any]] = []
        decisions_by_id: dict[str, dict[str, Any]] = {}
        paths_by_id: dict[str, Path] = {}
        direct_paths: list[Path] = []
        candidate_paths = sorted(
            path
            for path in decisions_dir.rglob("*")
            if path.is_file()
            and path != index_path
        )
        for path in candidate_paths:
            digest, _ = self.add_source(path)
            if path.parent != decisions_dir:
                self.add_finding(
                    "INVALID_ADR_PATH",
                    path,
                    "architecture decisions must be direct children of docs/decisions",
                )
                continue
            direct_paths.append(path)
            filename_match = ADR_FILENAME_RE.fullmatch(path.name)
            if filename_match is None:
                self.add_finding(
                    "INVALID_ADR_FILENAME",
                    path,
                    "ADR filename must match NNNN-lowercase-slug.md",
                )
                continue
            filename_number = filename_match.group("number")
            filename_id = f"ADR-{filename_number}"
            try:
                text = self.read_source_text(path)
            except (OSError, UnicodeError, InventoryError) as exc:
                self.add_finding("PARSE_ERROR", path, str(exc), filename_id)
                continue
            lines = text.splitlines()
            heading_match = ADR_HEADING_RE.fullmatch(lines[0] if lines else "")
            if heading_match is None:
                self.add_finding(
                    "INVALID_ADR_HEADING",
                    path,
                    "first line must be '# ADR-NNNN: Title'",
                    filename_id,
                )
                continue
            adr_id = f"ADR-{heading_match.group('number')}"
            if adr_id != filename_id:
                self.add_finding(
                    "ADR_FILENAME_MISMATCH",
                    path,
                    f"heading {adr_id} does not match filename {filename_id}",
                    adr_id,
                )

            metadata: dict[str, str] = {}
            for line in lines[1:]:
                stripped = line.strip()
                if stripped.startswith("## "):
                    break
                if not stripped:
                    continue
                metadata_match = re.fullmatch(r"- (?P<key>[^:]+):(?P<value>.*)", stripped)
                if metadata_match is None:
                    self.add_finding(
                        "INVALID_ADR_METADATA",
                        path,
                        f"metadata line must be '- Key: value': {stripped!r}",
                        adr_id,
                    )
                    continue
                key = metadata_match.group("key").strip()
                value = metadata_match.group("value").strip()
                if key not in ADR_ALLOWED_METADATA:
                    self.add_finding(
                        "INVALID_ADR_METADATA",
                        path,
                        f"unknown metadata key: {key}",
                        adr_id,
                    )
                    continue
                if key in metadata:
                    self.add_finding(
                        "INVALID_ADR_METADATA",
                        path,
                        f"duplicate metadata key: {key}",
                        adr_id,
                    )
                    continue
                metadata[key] = value

            status = metadata.get("Status", "")
            date_value = metadata.get("Date", "")
            supersedes = metadata.get("Supersedes")
            lifecycle_transition = metadata.get("Lifecycle transition")
            if status not in ADR_STATUSES:
                self.add_finding(
                    "INVALID_ADR_STATUS",
                    path,
                    f"unsupported status: {status!r}",
                    adr_id,
                )
            try:
                parsed_date = date.fromisoformat(date_value)
                valid_date = parsed_date.isoformat() == date_value
            except ValueError:
                valid_date = False
            if not valid_date:
                self.add_finding(
                    "INVALID_ADR_DATE",
                    path,
                    f"date must be a real ISO calendar date: {date_value!r}",
                    adr_id,
                )
            if supersedes is not None and (
                ADR_ID_RE.fullmatch(supersedes) is None or supersedes == adr_id
            ):
                self.add_finding(
                    "INVALID_ADR_SUPERSESSION",
                    path,
                    f"Supersedes must name a different ADR-NNNN: {supersedes!r}",
                    adr_id,
                )
            elif supersedes is not None and int(supersedes[-4:]) >= int(adr_id[-4:]):
                self.add_finding(
                    "INVALID_ADR_SUPERSESSION",
                    path,
                    "Supersedes must point backward to a lower append-only ADR number",
                    adr_id,
                )
            if lifecycle_transition is not None:
                transition_match = ADR_LIFECYCLE_TRANSITION_RE.fullmatch(
                    lifecycle_transition
                )
                if transition_match is None:
                    self.add_finding(
                        "INVALID_ADR_LIFECYCLE_TRANSITION",
                        path,
                        "Lifecycle transition must be 'SPEC-NNN@revision -> "
                        "amended|superseded|retired -> SPEC-NNN@next|none'",
                        adr_id,
                    )
                else:
                    transition_spec = transition_match.group("spec")
                    transition_revision = int(transition_match.group("revision"))
                    transition_status = transition_match.group("status")
                    transition_replacement = transition_match.group("replacement")
                    expected_replacement = f"{transition_spec}@{transition_revision + 1}"
                    if (
                        transition_status in {"amended", "superseded"}
                        and transition_replacement != expected_replacement
                    ) or (
                        transition_status == "retired"
                        and transition_replacement != "none"
                    ):
                        self.add_finding(
                            "INVALID_ADR_LIFECYCLE_TRANSITION",
                            path,
                            "lifecycle transition replacement must be the next revision "
                            "of the same specification, or none for retirement",
                            adr_id,
                        )

            scope_keys = [key for key in ("Spec", "Specs") if metadata.get(key)]
            if len(scope_keys) != 1:
                self.add_finding(
                    "INVALID_ADR_SPEC_SCOPE",
                    path,
                    "exactly one non-empty Spec or Specs field is required",
                    adr_id,
                )
                spec_scope = ""
                referenced_specs: list[str] = []
            else:
                scope_key = scope_keys[0]
                spec_scope = metadata[scope_key]
                referenced_specs = []
                if scope_key == "Spec":
                    if SPEC_ID_RE.fullmatch(spec_scope) is None:
                        self.add_finding(
                            "INVALID_ADR_SPEC_SCOPE",
                            path,
                            f"Spec must be one exact identifier: {spec_scope!r}",
                            adr_id,
                        )
                    else:
                        referenced_specs = [spec_scope]
                else:
                    range_match = re.fullmatch(
                        r"SPEC-(?P<start>[0-9]{3}) through SPEC-(?P<end>[0-9]{3})",
                        spec_scope,
                    )
                    if range_match is not None:
                        start = int(range_match.group("start"))
                        end = int(range_match.group("end"))
                        if start > end:
                            self.add_finding(
                                "INVALID_ADR_SPEC_SCOPE",
                                path,
                                f"specification range is reversed: {spec_scope!r}",
                                adr_id,
                            )
                        else:
                            referenced_specs = [
                                f"SPEC-{number:03d}" for number in range(start, end + 1)
                            ]
                    else:
                        candidates = [value.strip() for value in spec_scope.split(",")]
                        invalid_candidates = [
                            value for value in candidates if SPEC_ID_RE.fullmatch(value) is None
                        ]
                        duplicate_candidates = sorted(
                            value
                            for value in set(candidates)
                            if value and candidates.count(value) > 1
                        )
                        if invalid_candidates or not candidates:
                            self.add_finding(
                                "INVALID_ADR_SPEC_SCOPE",
                                path,
                                f"Specs must be a canonical range or comma-separated identifiers: {spec_scope!r}",
                                adr_id,
                            )
                        if duplicate_candidates:
                            self.add_finding(
                                "INVALID_ADR_SPEC_SCOPE",
                                path,
                                f"duplicate specification identifiers: {', '.join(duplicate_candidates)}",
                                adr_id,
                            )
                        referenced_specs = sorted(
                            {value for value in candidates if SPEC_ID_RE.fullmatch(value)}
                        )

            for spec_id in referenced_specs:
                if spec_id not in specification_ids:
                    self.add_finding(
                        "DANGLING_ADR_SPEC",
                        path,
                        f"decision references unknown specification: {spec_id}",
                        adr_id,
                    )

            if lifecycle_transition is not None:
                transition_match = ADR_LIFECYCLE_TRANSITION_RE.fullmatch(
                    lifecycle_transition
                )
                if transition_match is not None:
                    transition_spec = transition_match.group("spec")
                    if scope_keys != ["Spec"] or referenced_specs != [transition_spec]:
                        self.add_finding(
                            "INVALID_ADR_LIFECYCLE_TRANSITION_SCOPE",
                            path,
                            "a lifecycle-transition ADR is one-purpose: Spec must "
                            f"name exactly {transition_spec}",
                            adr_id,
                        )

            record = {
                "id": adr_id,
                "title": heading_match.group("title"),
                "status": status,
                "date": date_value,
                "spec_scope": spec_scope,
                "specifications": referenced_specs,
                "path": self.relative(path),
                "digest": digest,
            }
            if supersedes is not None:
                record["supersedes"] = supersedes
            if lifecycle_transition is not None:
                record["lifecycle_transition"] = lifecycle_transition
            if adr_id in decisions_by_id:
                self.add_finding(
                    "DUPLICATE_ADR_ID",
                    path,
                    f"identifier already declared by {self.relative(paths_by_id[adr_id])}",
                    adr_id,
                )
            else:
                decisions_by_id[adr_id] = record
                paths_by_id[adr_id] = path
            records.append(record)

        for record in records:
            supersedes = record.get("supersedes")
            if supersedes is None or ADR_ID_RE.fullmatch(supersedes) is None:
                continue
            target = decisions_by_id.get(supersedes)
            if target is None:
                self.add_finding(
                    "DANGLING_ADR_SUPERSESSION",
                    self.root / record["path"],
                    f"Supersedes references unknown decision: {supersedes}",
                    record["id"],
                )
            elif target["status"] != "accepted":
                self.add_finding(
                    "INVALID_ADR_SUPERSESSION",
                    self.root / record["path"],
                    f"Supersedes target must be accepted: {supersedes}",
                    record["id"],
                )

        accepted_successors: dict[str, list[str]] = {}
        for record in records:
            supersedes = record.get("supersedes")
            if record["status"] == "accepted" and isinstance(supersedes, str):
                accepted_successors.setdefault(supersedes, []).append(record["id"])
        for target_id, successors in sorted(accepted_successors.items()):
            if len(successors) > 1:
                for successor_id in successors:
                    successor = decisions_by_id[successor_id]
                    self.add_finding(
                        "AMBIGUOUS_ADR_SUPERSESSION",
                        self.root / successor["path"],
                        f"{target_id} has multiple accepted direct successors: "
                        f"{', '.join(sorted(successors))}",
                        successor_id,
                    )

        known_filenames = {path.name for path in direct_paths}
        for filename in sorted(known_filenames):
            links = index_links.get(filename, [])
            if not links:
                self.add_finding(
                    "MISSING_ADR_INDEX_LINK",
                    index_path,
                    f"architecture decision is not linked: {filename}",
                )
                continue
            if len(links) > 1:
                self.add_finding(
                    "DUPLICATE_ADR_INDEX_LINK",
                    index_path,
                    f"architecture decision is linked {len(links)} times: {filename}",
                )
            filename_match = ADR_FILENAME_RE.fullmatch(filename)
            if filename_match is None:
                continue
            adr_id = f"ADR-{filename_match.group('number')}"
            decision_record = decisions_by_id.get(adr_id)
            if decision_record is None:
                continue
            expected_link = (filename_match.group("number"), decision_record["title"])
            if any(link != expected_link for link in links):
                self.add_finding(
                    "ADR_INDEX_MISMATCH",
                    index_path,
                    f"index identity or title does not match {filename}",
                    adr_id,
                )
        for filename in sorted(set(index_links) - known_filenames):
            self.add_finding(
                "UNKNOWN_ADR_INDEX_LINK",
                index_path,
                f"index links an unknown architecture decision: {filename}",
            )

        return self._category(
            "docs/decisions/",
            sorted(records, key=lambda item: (item["id"], item["path"])),
            lifecycle=sorted(ADR_STATUSES),
        )

    def validate_live_document_links(self) -> None:
        for relative, required_link in LIVE_DOCUMENT_LINKS.items():
            path = self.root / relative
            try:
                text = self.read_source_text(path)
            except (OSError, UnicodeError, InventoryError) as exc:
                self.add_finding("PARSE_ERROR", path, str(exc))
                continue
            if required_link not in text:
                self.add_finding(
                    "STALE_COUNT",
                    path,
                    f"live document must link to generated inventory: {required_link}",
                )


def render_summary(inventory: dict[str, Any]) -> str:
    artifacts = inventory["artifacts"]
    rows = [
        ("Specifications", artifacts["specifications"]["count"]),
        ("Authority contracts", artifacts["authority_contracts"]["count"]),
        ("Architecture decisions", artifacts["architecture_decisions"]["count"]),
        ("Orchestration briefs", artifacts["orchestration_briefs"]["count"]),
        ("Published skills", artifacts["skills"]["count"]),
        ("Mechanism registry records", artifacts["mechanisms"]["count"]),
        ("Accepted-ledger events", artifacts["mechanism_ledgers"]["accepted_event_count"]),
        ("Rejected-ledger events", artifacts["mechanism_ledgers"]["rejected_event_count"]),
        ("Provenance-tracked claims", artifacts["claims"]["count"]),
        ("Activation cases", artifacts["activation_cases"]["count"]),
        ("Router prompts", artifacts["router_prompts"]["count"]),
        ("Adversarial scenario catalog entries", artifacts["adversarial_scenarios"]["count"]),
        ("Adversarial goldens", artifacts["adversarial_goldens"]["count"]),
        ("Effectiveness tasks", artifacts["effectiveness_tasks"]["count"]),
        ("Supervised loop components", artifacts["supervised_loop"]["count"]),
        ("Example projects", artifacts["examples"]["count"]),
    ]
    lines = [
        "<!-- GENERATED by researcher/scripts/build_inventory.py. DO NOT EDIT. -->",
        "# Live corpus inventory",
        "",
        "This is a generated view of canonical repository artifacts, not a second source of truth.",
        "",
        f"- Schema: `{inventory['schema_version']}`",
        f"- Declared input digest: `{inventory['source_tree_digest']}`",
        (
            "- Digest scope: exact byte snapshots consumed by InventoryBuilder only; "
            "not an exhaustive runtime-behavior digest, freeze/security boundary, or "
            "daily/status/validator result-reproduction guarantee."
        ),
        f"- Unresolved references: `{len(inventory['unresolved_references'])}`",
        "",
        "| Artifact | Count |",
        "| --- | ---: |",
        *[f"| {label} | {count} |" for label, count in rows],
        "",
        "## Compatibility",
        "",
        f"- Plugin version: `{artifacts['manifests']['versions']['open_plugin']}`",
        f"- Router runner: `{inventory['compatibility']['benchmark_runner']['router']}`",
        f"- Effectiveness runner: `{inventory['compatibility']['benchmark_runner']['effectiveness']}`",
        f"- Legacy launchd installer: `{artifacts['supervised_loop']['status']['launchd_installer']}`",
        f"- Legacy launchd wrappers: `{artifacts['supervised_loop']['status']['launchd_wrappers']}`",
        f"- Legacy direct execution: `{artifacts['supervised_loop']['status']['direct_execution']}`",
        f"- Legacy declared network retrieval: `{artifacts['supervised_loop']['status']['declared_network_retrieval']}`",
        f"- Adversarial scenarios: `{artifacts['adversarial_scenarios']['execution_status']}`",
        "",
        (
            "Historical reports retain the counts and measurements from their dated snapshot. "
            "Current documents should link here instead of copying live totals."
        ),
        "",
    ]
    return "\n".join(lines)


def print_findings(findings: Iterable[Finding]) -> None:
    for finding in findings:
        identity = f" ({finding.artifact_id})" if finding.artifact_id else ""
        print(f"[{finding.code}] {finding.path}{identity}: {finding.message}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--check", action="store_true", help="fail on unresolved references or generated drift")
    modes.add_argument("--write", action="store_true", help="atomically refresh generated inventory and summary")
    modes.add_argument("--json", action="store_true", help="print the generated inventory without writing")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--inventory", type=Path)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()

    root = args.root.resolve()
    inventory_path = args.inventory or root / "researcher" / "corpus" / "inventory.json"
    summary_path = args.summary or root / "researcher" / "generated" / "corpus-summary.md"
    builder = InventoryBuilder(root)
    try:
        inventory = builder.build()
    except (InventoryError, OSError) as exc:
        print(f"[PARSE_ERROR] {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(pretty_json(inventory), end="")
        print_findings(builder.findings)
        return 1 if builder.findings else 0

    if builder.findings:
        print_findings(builder.findings)
        print(f"Inventory generation failed: {len(builder.findings)} unresolved finding(s)", file=sys.stderr)
        return 1

    inventory_text = pretty_json(inventory)
    summary_text = render_summary(inventory)
    if args.write:
        atomic_write_text(inventory_path, inventory_text)
        atomic_write_text(summary_path, summary_text)
        print(
            f"Inventory written: {artifacts_count(inventory)} artifact records, "
            f"declared-input digest {inventory['source_tree_digest'][7:19]}"
        )
        return 0

    drift: list[Finding] = []
    if not inventory_path.exists() or inventory_path.read_text(encoding="utf-8") != inventory_text:
        drift.append(
            Finding("GENERATED_DRIFT", str(inventory_path.relative_to(root)), None, "run build_inventory.py --write")
        )
    if not summary_path.exists() or summary_path.read_text(encoding="utf-8") != summary_text:
        drift.append(
            Finding("STALE_COUNT", str(summary_path.relative_to(root)), None, "generated summary is stale")
        )
    if drift:
        print_findings(drift)
        return 1
    print(
        f"Inventory check passed: {artifacts_count(inventory)} artifact records, "
        f"{len(inventory['sources'])} declared input snapshots, "
        f"digest {inventory['source_tree_digest'][7:19]}"
    )
    return 0


def artifacts_count(inventory: dict[str, Any]) -> int:
    return sum(
        category.get("count", 0)
        for category in inventory["artifacts"].values()
        if isinstance(category, dict)
    )


if __name__ == "__main__":
    raise SystemExit(main())
