#!/usr/bin/env python3
"""Validate specification lifecycle transitions against an exact Git base.

The corpus inventory validates the candidate tree in isolation. This gate owns
the temporal question that an isolated tree cannot answer: whether a proposed
status or revision is a legal successor to the protected base. GitHub remains
the authority for whether that candidate was actually human-merged.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Iterable, Mapping


ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH_RE = re.compile(r"^docs/specs/SPEC-[0-9]{3}-[a-z0-9-]+\.md$")
SPEC_HEADING_RE = re.compile(r"^# (?P<id>SPEC-[0-9]{3}): (?P<title>.+)$")
ADR_PATH_RE = re.compile(r"^docs/decisions/[0-9]{4}-[a-z0-9-]+\.md$")
ADR_HEADING_RE = re.compile(r"^# (?P<id>ADR-[0-9]{4}): (?P<title>.+)$")
ACTIVE_STATUSES = {
    "draft",
    "architecture_reviewed",
    "accepted",
    "implemented",
    "verified",
    "operational",
}
STAGE_RANK = {
    "draft": 0,
    "architecture_reviewed": 1,
    "accepted": 2,
    "implemented": 3,
    "verified": 4,
    "operational": 5,
}
AUTHORITY_VOCABULARY_SPEC = "SPEC-000"
AUTHORITY_VOCABULARY_MIN_REVISION = 2
AUTHORITY_VOCABULARY_PATH = "governance/authority-vocabulary.json"
AUTHORITY_VOCABULARY_SCHEMA_VERSION = "1.0.0"
AUTHORITY_FIXTURE_MANIFEST_PATH = "governance/fixtures/authority-vocabulary.json"
AUTHORITY_FIXTURE_MANIFEST_SCHEMA_VERSION = "1.0.0"
AUTHORITY_CONFORMANCE_RECEIPT_PATH = (
    "governance/generated/authority-vocabulary-conformance.json"
)
AUTHORITY_CONFORMANCE_RECEIPT_SCHEMA_VERSION = "1.0.0"
AUTHORITY_CONSTITUTION_POLICY_PATH = "governance/constitution.yaml"
AUTHORITY_VALIDATOR_PATH = "researcher/scripts/validate_spec_lifecycle.py"
AUTHORITY_VALIDATOR_VERSION = "1.0.0"
AUTHORITY_VOCABULARY_READY_STATUSES = {
    "accepted",
    "implemented",
    "verified",
    "operational",
}
AUTHORITY_IMPLEMENTED_STATUSES = {"implemented", "verified", "operational"}
AUTHORITY_PREIMPLEMENTATION_STATUSES = {
    "draft",
    "architecture_reviewed",
    "accepted",
}
AUTHORITY_ENTRY_KEYS = {
    "action",
    "resource",
    "owner_spec",
    "actor_classes",
    "max_effect",
    "dependency_floor",
    "decision_context_fields",
    "grant_operation",
}
AUTHORITY_MAX_EFFECT_KEYS = {
    "code",
    "max_targets",
    "max_state_transitions",
}
AUTHORITY_FIXTURE_POINTER_KEYS = {"path", "digest", "version"}
AUTHORITY_FIXTURE_ENTRY_KEYS = {"action", "resource", "cases"}
AUTHORITY_FIXTURE_CASE_KEYS = {
    "case",
    "actor_class",
    "decision_context_fields",
    "effect",
    "expected_decision",
    "expected_policy_decision",
    "expected_registry_decision",
    "grant_operation",
    "omitted_context_field",
    "dependency_evidence",
}
AUTHORITY_CATALOG_FIXTURE_CASE_KEYS = AUTHORITY_FIXTURE_CASE_KEYS | {
    "action",
    "resource",
}
AUTHORITY_DEPENDENCY_EVIDENCE_KEYS = {"spec", "revision", "status"}
AUTHORITY_CONFORMANCE_POLICY_KEYS = {"path", "digest", "version"}
AUTHORITY_CONFORMANCE_VALIDATOR_KEYS = {"path", "digest", "version"}
AUTHORITY_CONFORMANCE_CASE_KEYS = {
    "action",
    "resource",
    "case",
    "expected_decision",
    "expected_policy_decision",
    "expected_registry_decision",
    "registry_decision",
    "registry_reason_code",
    "policy_decision",
    "actual_decision",
    "context_digest",
    "matched_rule",
    "reason_code",
}
TERMINAL_STATUSES = {"amended", "superseded", "retired"}
KNOWN_STATUSES = ACTIVE_STATUSES | TERMINAL_STATUSES
ACCEPTED_OR_LATER = {
    "accepted",
    "implemented",
    "verified",
    "operational",
    *TERMINAL_STATUSES,
}
LEGAL_SAME_REVISION_TRANSITIONS = {
    "draft": {"draft", "architecture_reviewed", "retired"},
    "architecture_reviewed": {
        "architecture_reviewed",
        "accepted",
        "amended",
        "superseded",
        "retired",
    },
    "accepted": {"accepted", "implemented", "amended", "superseded", "retired"},
    "implemented": {"implemented", "verified", "amended", "superseded", "retired"},
    "verified": {"verified", "operational", "amended", "superseded", "retired"},
    "operational": {"operational", "amended", "superseded", "retired"},
    "amended": {"amended"},
    "superseded": {"superseded"},
    "retired": {"retired"},
}
LEGACY_ADOPTION = {
    "SPEC-000": ("implementing", "implemented"),
    "SPEC-001": ("implementing", "implemented"),
    "SPEC-002": ("implementing", "implemented"),
    "SPEC-003": ("implemented", "implemented"),
}
LEGACY_ADOPTION_DECISION = "ADR-0005"
LEGACY_ADOPTION_OWNERS = {
    "SPEC-000": "human maintainer; governance agent",
    "SPEC-001": "corpus steward agent; human maintainer",
    "SPEC-002": "human maintainer; export steward agent",
    "SPEC-003": "platform steward agent; human maintainer",
}
LEGACY_ADOPTION_DEPENDENCY_REVISIONS = {
    "SPEC-000": "none",
    "SPEC-001": "SPEC-000@1",
    "SPEC-002": "SPEC-000@1",
    "SPEC-003": "SPEC-001@1, SPEC-002@1",
}
CONTRACT_METADATA_KEYS = {
    "Wave",
    "Classification",
    "Owners",
    "Depends on",
    "Activation",
}


@dataclass(frozen=True)
class LifecycleFinding:
    code: str
    path: str
    spec_id: str | None
    message: str


@dataclass(frozen=True)
class SpecRevision:
    path: str
    spec_id: str
    title: str
    status: str
    revision: int
    revises: str
    adoption_decision: str | None
    lifecycle_decision: str | None
    replacement: str | None
    metadata: Mapping[str, str]
    contract_body: str
    exact_bytes: bytes
    legacy_metadata: bool = False

    @property
    def digest(self) -> str:
        return f"sha256:{hashlib.sha256(self.exact_bytes).hexdigest()}"

    @property
    def contract_identity(self) -> tuple[object, ...]:
        mutable_lines = (
            b"Status:",
            b"Dependency revisions:",
            b"Lifecycle decision:",
            b"Replacement:",
        )
        stable_lines: list[bytes] = []
        in_header = True
        for line in self.exact_bytes.splitlines(keepends=True):
            if line.startswith(b"## "):
                in_header = False
            if in_header and line.startswith(mutable_lines):
                continue
            stable_lines.append(line)
        return (b"".join(stable_lines),)


@dataclass(frozen=True)
class AdrRevision:
    path: str
    adr_id: str
    title: str
    status: str
    lifecycle_transition: str | None
    exact_bytes: bytes


@dataclass(frozen=True)
class AuthoritySemanticProfile:
    """Closed semantics for one constitution-recognized action/resource pair."""

    owner_spec: str
    actor_classes: tuple[str, ...]
    max_effect_code: str
    max_targets: int
    max_state_transitions: int
    dependency_floor: tuple[str, ...]
    decision_context_fields: tuple[str, ...]
    grant_operation: str

    @property
    def max_effect(self) -> dict[str, object]:
        return {
            "code": self.max_effect_code,
            "max_state_transitions": self.max_state_transitions,
            "max_targets": self.max_targets,
        }


def _authority_context(*additional: str) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                "expected_target_version",
                "operation_id",
                "target_id",
                *additional,
            }
        )
    )


def _authority_profile(
    owner_spec: str,
    actor_classes: tuple[str, ...],
    max_effect_code: str,
    max_state_transitions: int,
    grant_operation: str,
    *,
    context: tuple[str, ...] = (),
    dependency_floor: tuple[str, ...] = (),
    max_targets: int = 1,
) -> AuthoritySemanticProfile:
    floor = dependency_floor or (f"{owner_spec}@1",)
    return AuthoritySemanticProfile(
        owner_spec=owner_spec,
        actor_classes=tuple(sorted(actor_classes)),
        max_effect_code=max_effect_code,
        max_targets=max_targets,
        max_state_transitions=max_state_transitions,
        dependency_floor=tuple(sorted(floor)),
        decision_context_fields=_authority_context(*context),
        grant_operation=grant_operation,
    )


POLICY_ONLY_READ_ACTORS = (
    "change_author",
    "community_contributor",
    "human_maintainer",
    "independent_verifier",
    "release_attestor",
    "research_proposer",
    "runtime_operator",
)
POLICY_ONLY_READ_PROFILES: Mapping[tuple[str, str], AuthoritySemanticProfile] = {
    ("read", "candidate_artifact"): _authority_profile(
        "SPEC-000",
        POLICY_ONLY_READ_ACTORS,
        "read_one_candidate_artifact",
        0,
        "read_candidate_artifact",
        dependency_floor=("SPEC-000@2",),
    ),
    ("read", "public_content_draft"): _authority_profile(
        "SPEC-000",
        POLICY_ONLY_READ_ACTORS,
        "read_one_public_content_draft",
        0,
        "read_public_content_draft",
        dependency_floor=("SPEC-000@2",),
    ),
    ("read", "public_repository"): _authority_profile(
        "SPEC-000",
        POLICY_ONLY_READ_ACTORS,
        "read_one_public_repository_view",
        0,
        "read_public_repository",
        dependency_floor=("SPEC-000@2",),
    ),
    ("read", "pull_request"): _authority_profile(
        "SPEC-000",
        POLICY_ONLY_READ_ACTORS,
        "read_one_pull_request",
        0,
        "read_pull_request",
        dependency_floor=("SPEC-000@2",),
    ),
    ("read", "research_artifact"): _authority_profile(
        "SPEC-000",
        POLICY_ONLY_READ_ACTORS,
        "read_one_research_artifact",
        0,
        "read_research_artifact",
        dependency_floor=("SPEC-000@2",),
    ),
}


# This is intentionally a closed, mechanism-level profile rather than an owner
# lookup. A registry cannot gain meaning by inventing plausible strings: every
# actor, guard, effect ceiling, dependency floor, and grant operation is
# reviewed as part of the SPEC-000 revision that changes this table.
REQUIRED_AUTHORITY_PROFILES: Mapping[
    tuple[str, str], AuthoritySemanticProfile
] = {
    ("amend_constitution", "constitution"): _authority_profile(
        "SPEC-000",
        ("human_maintainer",),
        "propose_one_constitution_amendment",
        1,
        "amend_constitution",
        context=("human_review_path",),
        dependency_floor=("SPEC-000@2",),
    ),
    ("activate_production", "production_deployment"): _authority_profile(
        "SPEC-025",
        ("human_maintainer",),
        "activate_one_deployment_pointer",
        1,
        "activate_deployment_pointer",
        context=(
            "accepted_public_commit",
            "canary_attestation",
            "configuration_digest",
            "manifest_digest",
            "operation_id",
            "promotion_record",
        ),
    ),
    ("approve_weight_training", "weight_training"): _authority_profile(
        "SPEC-000",
        ("human_maintainer",),
        "approve_one_weight_training_run",
        1,
        "approve_weight_training",
        dependency_floor=("SPEC-000@2",),
    ),
    ("attest_release", "candidate_artifact"): _authority_profile(
        "SPEC-000",
        ("release_attestor",),
        "record_one_candidate_release_attestation",
        1,
        "attest_release",
        context=("candidate_digest_verified", "independent_of_author"),
        dependency_floor=("SPEC-000@2",),
    ),
    ("attest_release", "pull_request"): _authority_profile(
        "SPEC-000",
        ("release_attestor",),
        "record_one_pull_request_release_attestation",
        1,
        "attest_release",
        context=("candidate_digest_verified", "independent_of_author"),
        dependency_floor=("SPEC-000@2",),
    ),
    ("authorize_credential_destination", "credential_destination"): _authority_profile(
        "SPEC-000",
        ("human_maintainer",),
        "authorize_one_credential_destination",
        1,
        "authorize_credential_destination",
        dependency_floor=("SPEC-000@2",),
    ),
    ("attest_canary_health", "deployment_canary"): _authority_profile(
        "SPEC-025",
        ("independent_canary_attestor",),
        "attest_one_canary_result",
        1,
        "attest_canary_result",
        context=(
            "accepted_public_commit",
            "activation_request",
            "canary_epoch",
            "clock_proofs",
            "configuration_digest",
            "expected_deployment_version",
            "gate_set",
            "manifest_digest",
            "observation_interval",
            "policy_digest",
            "prior_active_pointer",
            "promotion_record",
            "raw_measurement_refs",
        ),
    ),
    ("authorize_disaster_recovery", "event_journal"): _authority_profile(
        "SPEC-004",
        ("human_maintainer",),
        "create_one_degraded_disaster_generation",
        1,
        "create_degraded_disaster_generation",
        context=(
            "accepted_public_commit",
            "deployment_transition",
            "disaster_declaration",
            "halted_tail",
            "operation_id",
            "possible_loss_interval",
        ),
        dependency_floor=("SPEC-004@1", "SPEC-025@1"),
    ),
    ("authorize_hidden_evaluation", "evaluation_epoch"): _authority_profile(
        "SPEC-016",
        ("human_maintainer",),
        "authorize_one_hidden_evaluation_epoch",
        1,
        "authorize_hidden_epoch",
        context=(
            "accepted_public_commit",
            "budget_ceiling",
            "manifest_digest",
            "operation_id",
            "split_and_look_ceiling",
        ),
    ),
    ("change_protected_surface", "evaluator_policy"): _authority_profile(
        "SPEC-000",
        ("human_maintainer",),
        "propose_one_evaluator_policy_change",
        1,
        "change_protected_surface",
        context=("human_review_path",),
        dependency_floor=("SPEC-000@2",),
    ),
    ("change_protected_surface", "hidden_evaluation"): _authority_profile(
        "SPEC-000",
        ("human_maintainer",),
        "propose_one_hidden_evaluation_change",
        1,
        "change_protected_surface",
        context=("human_review_path",),
        dependency_floor=("SPEC-000@2",),
    ),
    ("change_protected_surface", "protected_surface"): _authority_profile(
        "SPEC-000",
        ("human_maintainer",),
        "propose_one_protected_surface_change",
        1,
        "change_protected_surface",
        context=("human_review_path",),
        dependency_floor=("SPEC-000@2",),
    ),
    ("change_protected_surface", "public_private_boundary"): _authority_profile(
        "SPEC-000",
        ("human_maintainer",),
        "propose_one_public_private_boundary_change",
        1,
        "change_protected_surface",
        context=("human_review_path",),
        dependency_floor=("SPEC-000@2",),
    ),
    ("cancel_work", "work_order"): _authority_profile(
        "SPEC-006",
        ("human_maintainer",),
        "request_one_work_cancellation",
        1,
        "request_work_cancellation",
        context=("accepted_public_commit", "attempt_id", "fence", "operation_id"),
    ),
    ("change_deployment", "production_deployment"): _authority_profile(
        "SPEC-025",
        ("human_maintainer",),
        "stage_one_deployment_change",
        1,
        "stage_deployment_change",
        context=(
            "accepted_public_commit",
            "configuration_digest",
            "manifest_digest",
            "operation_id",
        ),
    ),
    ("close_run", "research_run"): _authority_profile(
        "SPEC-006",
        ("human_maintainer",),
        "close_one_research_run",
        1,
        "transition_research_run_close",
        context=("accepted_public_commit", "operation_id"),
    ),
    ("create_content_draft", "content_draft"): _authority_profile(
        "SPEC-015",
        ("content_proposer",),
        "create_one_private_content_draft",
        1,
        "create_content_draft",
        context=("accepted_public_commit", "operation_id", "source_evidence_digest"),
    ),
    ("evaluate", "candidate_artifact"): _authority_profile(
        "SPEC-000",
        ("independent_verifier",),
        "record_one_independent_candidate_evaluation",
        1,
        "evaluate_candidate_artifact",
        context=("independent_of_author",),
        dependency_floor=("SPEC-000@2",),
    ),
    ("evaluate", "research_artifact"): _authority_profile(
        "SPEC-000",
        ("independent_verifier",),
        "record_one_independent_research_evaluation",
        1,
        "evaluate_research_artifact",
        context=("independent_of_author",),
        dependency_floor=("SPEC-000@2",),
    ),
    ("emergency_disable", "emergency_control"): _authority_profile(
        "SPEC-025",
        ("human_maintainer", "runtime_operator"),
        "disable_one_emergency_scope",
        1,
        "disable_production_effects",
        context=("operation_id", "safety_ledger_version"),
    ),
    ("export_approved_draft", "content_draft"): _authority_profile(
        "SPEC-015",
        ("content_exporter",),
        "export_one_approved_draft_locally",
        1,
        "export_approved_content_draft",
        context=("approval_receipt", "destination_class", "operation_id"),
    ),
    ("execute_work", "candidate_artifact"): _authority_profile(
        "SPEC-000",
        ("runtime_operator",),
        "execute_one_bounded_candidate_work_effect",
        1,
        "execute_candidate_work",
        context=("capability_grant_valid",),
        dependency_floor=("SPEC-000@2",),
    ),
    ("execute_work", "research_artifact"): _authority_profile(
        "SPEC-000",
        ("runtime_operator",),
        "execute_one_bounded_research_work_effect",
        1,
        "execute_research_work",
        context=("capability_grant_valid",),
        dependency_floor=("SPEC-000@2",),
    ),
    ("expose_private_record", "private_record"): _authority_profile(
        "SPEC-000",
        ("human_maintainer",),
        "export_one_approved_private_record",
        1,
        "expose_private_record",
        dependency_floor=("SPEC-000@2",),
    ),
    ("initialize_repository_acceptance", "repository_acceptance"): _authority_profile(
        "SPEC-004",
        ("human_maintainer",),
        "atomically_create_repository_acceptance_baseline_and_organization_epoch_from_absent_pointer",
        2,
        "initialize_repository_acceptance",
        context=(
            "accepted_commit",
            "accepted_tree",
            "accepted_pointer_absent",
            "git_observation",
            "inventory_digest",
            "organization_epoch",
            "repository_identity",
            "source_tree_digest",
        ),
        max_targets=2,
    ),
    ("invoke_break_glass", "credential_binding"): _authority_profile(
        "SPEC-024",
        ("human_maintainer",),
        "invoke_one_bounded_break_glass_binding",
        1,
        "invoke_break_glass",
        context=(
            "accepted_public_commit",
            "break_glass_expiry",
            "incident_id",
            "one_use_receipt",
            "operation_id",
        ),
    ),
    ("manage_credential_binding", "credential_binding"): _authority_profile(
        "SPEC-024",
        ("human_maintainer",),
        "change_one_credential_binding",
        1,
        "manage_credential_binding",
        context=(
            "accepted_public_commit",
            "binding_digest",
            "credential_class",
            "operation_id",
        ),
    ),
    ("merge", "default_branch"): _authority_profile(
        "SPEC-000",
        ("human_maintainer",),
        "advance_one_default_branch_to_reviewed_head",
        1,
        "merge_reviewed_head",
        context=("latest_commit_reviewed", "required_checks_passed"),
        dependency_floor=("SPEC-000@2",),
    ),
    ("merge", "pull_request"): _authority_profile(
        "SPEC-000",
        ("human_maintainer",),
        "merge_one_pull_request_reviewed_head",
        1,
        "merge_reviewed_head",
        context=("latest_commit_reviewed", "required_checks_passed"),
        dependency_floor=("SPEC-000@2",),
    ),
    ("open_pull_request", "pull_request"): _authority_profile(
        "SPEC-000",
        ("change_author", "community_contributor", "human_maintainer", "research_proposer"),
        "open_one_governed_pull_request",
        1,
        "open_pull_request",
        context=("automated_identity_disclosed", "human_review_path"),
        dependency_floor=("SPEC-000@2",),
    ),
    ("operate_deployment", "production_deployment"): _authority_profile(
        "SPEC-025",
        ("authenticated_runtime_operator",),
        "execute_one_in_epoch_operation",
        1,
        "operate_within_activation_epoch",
        context=("activation_epoch", "configuration_digest", "operation_id"),
    ),
    ("park_run", "research_run"): _authority_profile(
        "SPEC-006",
        ("human_maintainer",),
        "park_one_research_run",
        1,
        "transition_research_run_park",
        context=("accepted_public_commit", "operation_id"),
    ),
    ("pause_run", "research_run"): _authority_profile(
        "SPEC-006",
        ("human_maintainer",),
        "pause_one_research_run",
        1,
        "transition_research_run_pause",
        context=("accepted_public_commit", "operation_id"),
    ),
    ("prove_clock_deadline", "clock_domain"): _authority_profile(
        "SPEC-005",
        ("trusted_clock_reducer",),
        "emit_one_purpose_scoped_deadline_proof",
        0,
        "emit_clock_deadline_proof",
        context=("clock_observation", "deadline", "proof_purpose"),
    ),
    ("propose_change", "candidate_artifact"): _authority_profile(
        "SPEC-000",
        (
            "change_author",
            "community_contributor",
            "human_maintainer",
            "research_proposer",
        ),
        "propose_one_candidate_artifact_change",
        1,
        "propose_candidate_change",
        context=("automated_identity_disclosed", "human_review_path"),
        dependency_floor=("SPEC-000@2",),
    ),
    ("propose_change", "research_artifact"): _authority_profile(
        "SPEC-000",
        ("human_maintainer", "research_proposer"),
        "propose_one_research_artifact_change",
        1,
        "propose_research_change",
        context=("automated_identity_disclosed",),
        dependency_floor=("SPEC-000@2",),
    ),
    ("push_proposal", "proposal_branch"): _authority_profile(
        "SPEC-000",
        ("change_author", "human_maintainer", "research_proposer"),
        "push_one_proposal_branch_head",
        1,
        "push_proposal_branch",
        context=("automated_identity_disclosed", "human_review_path"),
        dependency_floor=("SPEC-000@2",),
    ),
    ("query_status", "status_projection"): _authority_profile(
        "SPEC-006",
        ("authenticated_reader",),
        "read_one_status_projection",
        0,
        "read_status_projection",
    ),
    ("reconcile_clock", "clock_domain"): _authority_profile(
        "SPEC-005",
        ("human_maintainer",),
        "accept_one_bounded_clock_bridge",
        1,
        "accept_clock_reconciliation",
        context=(
            "accepted_public_commit",
            "clock_bridge",
            "current_observation",
            "operation_id",
            "prior_observation",
        ),
    ),
    ("reconcile_repository_acceptance", "repository_acceptance"): _authority_profile(
        "SPEC-007",
        ("repository_acceptance_reconciler",),
        "append_one_repository_acceptance_event_and_accepted_pointer_receipt",
        1,
        "record_repository_acceptance",
        context=(
            "authority_set_digest",
            "base_commit",
            "default_branch",
            "expected_accepted_pointer",
            "expected_accepted_pointer_version",
            "first_parent_interval",
            "git_observation_receipts",
            "head_commit",
            "merge_commit",
            "merge_actor",
            "merge_tree",
            "provider_revisions",
            "pull_request",
            "repository_identity",
            "ruleset_digest",
        ),
    ),
    ("record_draft_decision", "content_draft"): _authority_profile(
        "SPEC-015",
        ("human_maintainer",),
        "record_one_content_draft_decision",
        1,
        "record_content_draft_decision",
        context=("accepted_public_commit", "draft_digest", "operation_id"),
    ),
    ("record_pr_decision", "pull_request"): _authority_profile(
        "SPEC-007",
        ("human_maintainer",),
        "record_one_pull_request_readiness_decision",
        1,
        "record_pull_request_decision",
        context=("accepted_public_commit", "head_sha", "operation_id", "pull_request"),
    ),
    ("recover_journal", "event_journal"): _authority_profile(
        "SPEC-004",
        ("human_maintainer",),
        "reopen_one_continuous_journal_generation",
        1,
        "reopen_continuous_journal_generation",
        context=(
            "accepted_public_commit",
            "continuation_proof",
            "halted_tail",
            "operation_id",
            "recovery_ticket",
        ),
    ),
    ("resolve_ambiguous_effect", "external_effect"): _authority_profile(
        "SPEC-005",
        ("human_maintainer",),
        "record_one_ambiguous_effect_disposition",
        1,
        "record_ambiguous_effect_disposition",
        context=(
            "accepted_public_commit",
            "attempt_id",
            "evidence_digest",
            "fence",
            "operation_id",
        ),
    ),
    ("research", "candidate_artifact"): _authority_profile(
        "SPEC-000",
        ("human_maintainer", "research_proposer"),
        "append_one_candidate_research_artifact",
        1,
        "research_candidate_artifact",
        context=("automated_identity_disclosed",),
        dependency_floor=("SPEC-000@2",),
    ),
    ("research", "research_artifact"): _authority_profile(
        "SPEC-000",
        ("human_maintainer", "research_proposer"),
        "append_one_research_artifact",
        1,
        "research_artifact",
        context=("automated_identity_disclosed",),
        dependency_floor=("SPEC-000@2",),
    ),
    ("respond_to_review", "pull_request"): _authority_profile(
        "SPEC-000",
        ("change_author", "community_contributor", "human_maintainer", "research_proposer"),
        "append_one_pull_request_review_response",
        1,
        "respond_to_pull_request_review",
        context=("automated_identity_disclosed", "human_review_path"),
        dependency_floor=("SPEC-000@2",),
    ),
    ("resume_run", "research_run"): _authority_profile(
        "SPEC-006",
        ("human_maintainer",),
        "resume_one_research_run",
        1,
        "transition_research_run_resume",
        context=("accepted_public_commit", "operation_id"),
    ),
    ("revoke_capability", "capability"): _authority_profile(
        "SPEC-024",
        ("credential_reconciler",),
        "revoke_one_capability_stop_only",
        1,
        "revoke_capability",
        context=("capability_digest", "operation_id", "revocation_reason"),
    ),
    ("sample_clock", "clock_domain"): _authority_profile(
        "SPEC-005",
        ("attested_supervisor_clock_sampler",),
        "append_one_clock_observation",
        1,
        "append_clock_observation",
        context=("boot_id", "clock_source", "observation_digest", "operation_id"),
    ),
    ("seal_hidden_evaluation", "evaluation_epoch"): _authority_profile(
        "SPEC-016",
        ("independent_epoch_sealer",),
        "activate_one_human_authorized_hidden_evaluation_epoch_and_append_immutable_seal_receipt",
        1,
        "seal_hidden_epoch",
        context=("authorization_receipt", "manifest_digest", "operation_id"),
    ),
}

REQUIRED_AUTHORITY_VOCABULARY_OWNERS = {
    pair: profile.owner_spec for pair, profile in REQUIRED_AUTHORITY_PROFILES.items()
}


@dataclass(frozen=True)
class AuthorityFixtureCase:
    action: str
    resource: str
    case: str
    actor_class: str
    decision_context_fields: tuple[str, ...]
    effect_code: str
    max_targets: int
    max_state_transitions: int
    expected_decision: str
    expected_policy_decision: str
    expected_registry_decision: str
    grant_operation: str
    omitted_context_field: str
    dependency_evidence: tuple[tuple[str, int, str], ...]


@dataclass(frozen=True)
class AuthorityFixtureManifestBinding:
    path: str
    digest: str
    schema_version: str
    constitution_revision: int
    registry_version: int
    fixture_pairs: tuple[tuple[str, str], ...]
    cases: tuple[AuthorityFixtureCase, ...]


@dataclass(frozen=True)
class AuthorityPolicyConformanceBinding:
    path: str
    digest: str
    schema_version: str
    constitution_policy_digest: str
    registry_digest: str
    fixture_manifest_digest: str
    validator_digest: str
    validator_version: str
    case_count: int


@dataclass(frozen=True)
class AuthorityVocabularyBinding:
    path: str
    digest: str
    schema_version: str
    constitution_revision: int
    registry_version: int
    entries: tuple[tuple[str, str, str], ...]
    fixture_manifest_path: str
    fixture_manifest_digest: str
    fixture_manifest_version: int
    fixture_cases: tuple[AuthorityFixtureCase, ...]
    policy_conformance: AuthorityPolicyConformanceBinding | None = None

    @property
    def policy_conformance_receipt_digest(self) -> str | None:
        if self.policy_conformance is None:
            return None
        return self.policy_conformance.digest


def _strict_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _strict_json_integer(value: str) -> int:
    if re.fullmatch(r"-?(?:0|[1-9][0-9]*)", value) is None:
        raise ValueError(f"invalid JSON integer: {value}")
    parsed = int(value)
    if abs(parsed) > 9_007_199_254_740_991:
        raise ValueError(f"JSON integer exceeds the portable exact range: {value}")
    return parsed


def _strict_json_loads(exact_bytes: bytes, *, label: str) -> Any:
    try:
        return json.loads(
            exact_bytes.decode("utf-8"),
            object_pairs_hook=_strict_json_object,
            parse_int=_strict_json_integer,
            parse_float=lambda value: (_ for _ in ()).throw(
                ValueError(f"floating point is forbidden: {value}")
            ),
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"non-finite number is forbidden: {value}")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} is not strict UTF-8 JSON: {exc}") from exc


def _canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode(
        "utf-8"
    )


def expected_authority_dependency_evidence(
    profile: AuthoritySemanticProfile,
) -> list[dict[str, object]]:
    evidence: list[dict[str, object]] = []
    for binding in profile.dependency_floor:
        spec_id, revision = binding.split("@", maxsplit=1)
        evidence.append(
            {
                "spec": spec_id,
                "revision": int(revision),
                "status": "operational",
            }
        )
    return evidence


def expected_authority_fixture_cases(
    profile: AuthoritySemanticProfile,
) -> tuple[dict[str, object], ...]:
    """Return the exhaustive actor, guard, dependency, effect, and grant cases."""

    allowed_actor = profile.actor_classes[0]
    fields = list(profile.decision_context_fields)
    exact_effect = profile.max_effect
    dependency_evidence = expected_authority_dependency_evidence(profile)
    common: dict[str, object] = {
        "actor_class": allowed_actor,
        "decision_context_fields": fields,
        "effect": exact_effect,
        "expected_decision": "deny",
        "expected_policy_decision": "deny",
        "expected_registry_decision": "deny",
        "grant_operation": profile.grant_operation,
        "omitted_context_field": "none",
        "dependency_evidence": dependency_evidence,
    }

    cases: list[dict[str, object]] = []
    for actor_class in profile.actor_classes:
        cases.append(
            dict(
                common,
                case=f"allow__{actor_class}",
                actor_class=actor_class,
                expected_decision="allow",
                expected_policy_decision="allow",
                expected_registry_decision="allow",
            )
        )
    for omitted_field in profile.decision_context_fields:
        cases.append(
            dict(
                common,
                case=f"missing_guard__{omitted_field}",
                decision_context_fields=[
                    field for field in fields if field != omitted_field
                ],
                omitted_context_field=omitted_field,
            )
        )
    below_floor = [dict(item) for item in dependency_evidence]
    below_floor[0]["revision"] = int(below_floor[0]["revision"]) - 1
    cases.append(
        dict(
            common,
            case="below_dependency_floor",
            dependency_evidence=below_floor,
        )
    )
    owner_inactive = [dict(item) for item in dependency_evidence]
    owner_record = next(
        item for item in owner_inactive if item["spec"] == profile.owner_spec
    )
    owner_record["status"] = "draft"
    cases.append(
        dict(
            common,
            case="owner_inactive",
            dependency_evidence=owner_inactive,
        )
    )
    cases.append(
        dict(
            common,
            case="widened_effect",
            effect={
                "code": "unbounded_effect",
                "max_state_transitions": profile.max_state_transitions + 1,
                "max_targets": profile.max_targets + 1,
            },
        )
    )
    cases.append(dict(common, case="wrong_actor", actor_class="unauthorized_actor"))
    cases.append(
        dict(
            common,
            case="wrong_grant",
            grant_operation="unauthorized_operation",
        )
    )
    return tuple(sorted(cases, key=lambda case: str(case["case"])))


def expected_authority_catalog_boundary_cases() -> tuple[dict[str, object], ...]:
    base_pair = ("query_status", "status_projection")
    profile = REQUIRED_AUTHORITY_PROFILES[base_pair]
    allow = next(
        case
        for case in expected_authority_fixture_cases(profile)
        if str(case["case"]).startswith("allow__")
    )
    unknown_action = dict(
        allow,
        action="unknown_action",
        resource=base_pair[1],
        case="unknown_action",
        expected_decision="deny",
        expected_policy_decision="deny",
        expected_registry_decision="deny",
    )
    unknown_resource = dict(
        allow,
        action=base_pair[0],
        resource="unknown_resource",
        case="unknown_resource",
        expected_decision="deny",
        expected_policy_decision="deny",
        expected_registry_decision="deny",
    )
    unknown_pair = dict(
        allow,
        action=base_pair[0],
        resource="work_order",
        case="unknown_pair",
        expected_decision="deny",
        expected_policy_decision="deny",
        expected_registry_decision="deny",
    )
    if (unknown_pair["action"], unknown_pair["resource"]) in REQUIRED_AUTHORITY_PROFILES:
        raise RuntimeError("unknown-pair fixture accidentally became a registered pair")
    legacy_publish = dict(
        allow,
        action="publish_draft",
        resource="public_content_draft",
        case="legacy_publish_draft_denied",
        actor_class="research_proposer",
        expected_decision="deny",
        expected_policy_decision="deny",
        expected_registry_decision="deny",
        dependency_evidence=[
            {"spec": "SPEC-000", "revision": 2, "status": "operational"}
        ],
    )
    read_cases: list[dict[str, object]] = []
    for (read_action, read_resource), read_profile in sorted(
        POLICY_ONLY_READ_PROFILES.items()
    ):
        profile_cases = expected_authority_fixture_cases(read_profile)
        for profile_case in profile_cases:
            is_allow = str(profile_case["case"]).startswith("allow__")
            read_cases.append(
                dict(
                    profile_case,
                    action=read_action,
                    resource=read_resource,
                    case=f"read_{read_resource}__{profile_case['case']}",
                    expected_registry_decision="non_event" if is_allow else "deny",
                )
            )
        allowed_case = next(
            case
            for case in profile_cases
            if case["case"] == "allow__human_maintainer"
        )
        read_cases.append(
            dict(
                allowed_case,
                action=read_action,
                resource=read_resource,
                case=f"read_{read_resource}__event_append_denied",
                effect={
                    "code": "append_one_organization_event",
                    "max_state_transitions": 1,
                    "max_targets": 1,
                },
                grant_operation="append_organization_event",
                expected_decision="deny",
                expected_policy_decision="deny",
                expected_registry_decision="deny",
            )
        )
    representative_read = next(
        case
        for case in read_cases
        if case["case"] == "read_public_repository__allow__human_maintainer"
    )
    unknown_read_resource = dict(
        representative_read,
        resource="unknown_read_resource",
        case="read_unknown_resource_denied",
        expected_decision="deny",
        expected_policy_decision="deny",
        expected_registry_decision="deny",
    )
    noncatalog_append = dict(
        allow,
        action="noncatalog_event_append",
        resource="organization_event",
        case="noncatalog_event_append_denied",
        effect={
            "code": "append_one_organization_event",
            "max_state_transitions": 1,
            "max_targets": 1,
        },
        grant_operation="append_organization_event",
        expected_decision="deny",
        expected_policy_decision="deny",
        expected_registry_decision="deny",
        dependency_evidence=[
            {"spec": "SPEC-000", "revision": 2, "status": "operational"}
        ],
    )
    return tuple(
        sorted(
            (
                legacy_publish,
                noncatalog_append,
                *read_cases,
                unknown_read_resource,
                unknown_action,
                unknown_pair,
                unknown_resource,
            ),
            key=lambda case: str(case["case"]),
        )
    )


def _validate_max_effect_shape(value: Any, *, label: str) -> None:
    if not isinstance(value, dict) or set(value) != AUTHORITY_MAX_EFFECT_KEYS:
        raise ValueError(f"{label} max_effect does not match the closed schema")
    if not isinstance(value["code"], str) or re.fullmatch(
        r"[a-z][a-z0-9_]*", value["code"]
    ) is None:
        raise ValueError(f"{label} max_effect code is invalid")
    for key in ("max_targets", "max_state_transitions"):
        if type(value[key]) is not int or value[key] < 0:  # bool is not an integer here
            raise ValueError(f"{label} {key} must be a non-negative integer")


def _validate_dependency_evidence(value: Any, *, label: str) -> None:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{label} dependency_evidence must be a non-empty array")
    identities: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict) or set(item) != AUTHORITY_DEPENDENCY_EVIDENCE_KEYS:
            raise ValueError(f"{label} dependency evidence {index} has an invalid schema")
        if not isinstance(item["spec"], str) or re.fullmatch(
            r"SPEC-[0-9]{3}", item["spec"]
        ) is None:
            raise ValueError(f"{label} dependency evidence {index} has an invalid spec")
        if type(item["revision"]) is not int or item["revision"] < 0:
            raise ValueError(f"{label} dependency evidence {index} has an invalid revision")
        if item["status"] not in ACTIVE_STATUSES:
            raise ValueError(f"{label} dependency evidence {index} has an invalid status")
        identities.append(item["spec"])
    if identities != sorted(set(identities)):
        raise ValueError(f"{label} dependency evidence must be sorted and duplicate-free")


def parse_authority_fixture_manifest(
    exact_bytes: bytes,
    *,
    expected_digest: str,
    expected_constitution_revision: int,
    expected_registry_version: int,
    expected_profiles: Mapping[tuple[str, str], AuthoritySemanticProfile],
) -> AuthorityFixtureManifestBinding:
    """Validate the digest-bound, exhaustive allow/deny fixture manifest."""

    actual_digest = f"sha256:{hashlib.sha256(exact_bytes).hexdigest()}"
    if actual_digest != expected_digest:
        raise ValueError(
            f"authority fixture manifest digest mismatch: expected {expected_digest}, "
            f"got {actual_digest}"
        )
    data = _strict_json_loads(exact_bytes, label="authority fixture manifest")
    if not isinstance(data, dict):
        raise ValueError("authority fixture manifest root must be an object")
    root_keys = {
        "kind",
        "schema_version",
        "constitution_revision",
        "registry_version",
        "entries",
        "catalog_boundary_cases",
    }
    if set(data) != root_keys:
        raise ValueError("authority fixture manifest root fields do not match the closed schema")
    if data["kind"] != "AuthorityVocabularyFixtureManifest":
        raise ValueError("authority fixture manifest kind is invalid")
    if data["schema_version"] != AUTHORITY_FIXTURE_MANIFEST_SCHEMA_VERSION:
        raise ValueError(
            "authority fixture manifest schema_version must be "
            f"{AUTHORITY_FIXTURE_MANIFEST_SCHEMA_VERSION}"
        )
    if (
        type(data["constitution_revision"]) is not int
        or data["constitution_revision"] != expected_constitution_revision
    ):
        raise ValueError("authority fixture manifest constitution_revision is not current")
    if (
        type(data["registry_version"]) is not int
        or data["registry_version"] != expected_registry_version
    ):
        raise ValueError("authority fixture manifest registry_version is not current")
    entries = data["entries"]
    if not isinstance(entries, list) or not entries:
        raise ValueError("authority fixture manifest entries must be a non-empty array")

    parsed_pairs: list[tuple[str, str]] = []
    parsed_cases: list[AuthorityFixtureCase] = []
    seen_pairs: set[tuple[str, str]] = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict) or set(entry) != AUTHORITY_FIXTURE_ENTRY_KEYS:
            raise ValueError(f"authority fixture entry {index} does not match the closed schema")
        action = entry["action"]
        resource = entry["resource"]
        if not isinstance(action, str) or not isinstance(resource, str):
            raise ValueError(f"authority fixture entry {index} has an invalid identity")
        pair = (action, resource)
        if pair in seen_pairs:
            raise ValueError(f"duplicate authority fixture entry: {action}/{resource}")
        seen_pairs.add(pair)
        profile = expected_profiles.get(pair)
        if profile is None:
            raise ValueError(f"detached authority fixture entry: {action}/{resource}")
        cases = entry["cases"]
        if not isinstance(cases, list):
            raise ValueError(f"authority fixture entry {index} cases must be an array")
        names: list[str] = []
        for case_index, case in enumerate(cases):
            if not isinstance(case, dict) or set(case) != AUTHORITY_FIXTURE_CASE_KEYS:
                raise ValueError(
                    f"authority fixture entry {index} case {case_index} does not match "
                    "the closed schema"
                )
            if not isinstance(case["case"], str) or re.fullmatch(
                r"[a-z][a-z0-9_]*", case["case"]
            ) is None:
                raise ValueError(f"authority fixture entry {index} has an invalid case name")
            names.append(case["case"])
            if not isinstance(case["actor_class"], str):
                raise ValueError(f"authority fixture entry {index} has an invalid actor")
            if (
                not isinstance(case["decision_context_fields"], list)
                or any(not isinstance(field, str) for field in case["decision_context_fields"])
                or case["decision_context_fields"]
                != sorted(set(case["decision_context_fields"]))
            ):
                raise ValueError(
                    f"authority fixture entry {index} has invalid decision context fields"
                )
            _validate_max_effect_shape(
                case["effect"], label=f"authority fixture entry {index} case {case_index}"
            )
            _validate_dependency_evidence(
                case["dependency_evidence"],
                label=f"authority fixture entry {index} case {case_index}",
            )
            if case["expected_decision"] not in {"allow", "deny"}:
                raise ValueError(
                    f"authority fixture entry {index} has an invalid expected decision"
                )
            if case["expected_policy_decision"] not in {"allow", "deny"} or case[
                "expected_registry_decision"
            ] not in {"allow", "deny", "non_event"}:
                raise ValueError(
                    f"authority fixture entry {index} has invalid boundary expectations"
                )
            if not isinstance(case["grant_operation"], str) or not isinstance(
                case["omitted_context_field"], str
            ):
                raise ValueError(f"authority fixture entry {index} has invalid case metadata")
        expected_cases = list(expected_authority_fixture_cases(profile))
        if names != sorted(set(names)) or cases != expected_cases:
            raise ValueError(
                f"authority fixture entry {index} must prove every actor and guard plus "
                "the exact negative semantic profile"
            )
        for case in cases:
            effect = case["effect"]
            parsed_cases.append(
                AuthorityFixtureCase(
                    action=action,
                    resource=resource,
                    case=case["case"],
                    actor_class=case["actor_class"],
                    decision_context_fields=tuple(case["decision_context_fields"]),
                    effect_code=effect["code"],
                    max_targets=effect["max_targets"],
                    max_state_transitions=effect["max_state_transitions"],
                    expected_decision=case["expected_decision"],
                    expected_policy_decision=case["expected_policy_decision"],
                    expected_registry_decision=case["expected_registry_decision"],
                    grant_operation=case["grant_operation"],
                    omitted_context_field=case["omitted_context_field"],
                    dependency_evidence=tuple(
                        (item["spec"], item["revision"], item["status"])
                        for item in case["dependency_evidence"]
                    ),
                )
            )
        parsed_pairs.append(pair)

    expected_pairs = sorted(expected_profiles)
    if parsed_pairs != expected_pairs:
        raise ValueError(
            "authority fixture entries must be sorted and cover every registry entry exactly once"
        )
    catalog_boundary_cases = data["catalog_boundary_cases"]
    expected_boundary_cases = list(expected_authority_catalog_boundary_cases())
    if (
        not isinstance(catalog_boundary_cases, list)
        or catalog_boundary_cases != expected_boundary_cases
    ):
        raise ValueError(
            "authority fixture manifest must contain the exact catalog-boundary cases"
        )
    for index, case in enumerate(catalog_boundary_cases):
        if not isinstance(case, dict) or set(case) != AUTHORITY_CATALOG_FIXTURE_CASE_KEYS:
            raise ValueError(f"authority catalog-boundary fixture {index} has an invalid schema")
        _validate_max_effect_shape(
            case["effect"], label=f"authority catalog-boundary fixture {index}"
        )
        _validate_dependency_evidence(
            case["dependency_evidence"],
            label=f"authority catalog-boundary fixture {index}",
        )
        parsed_cases.append(
            AuthorityFixtureCase(
                action=case["action"],
                resource=case["resource"],
                case=case["case"],
                actor_class=case["actor_class"],
                decision_context_fields=tuple(case["decision_context_fields"]),
                effect_code=case["effect"]["code"],
                max_targets=case["effect"]["max_targets"],
                max_state_transitions=case["effect"]["max_state_transitions"],
                expected_decision=case["expected_decision"],
                expected_policy_decision=case["expected_policy_decision"],
                expected_registry_decision=case["expected_registry_decision"],
                grant_operation=case["grant_operation"],
                omitted_context_field=case["omitted_context_field"],
                dependency_evidence=tuple(
                    (item["spec"], item["revision"], item["status"])
                    for item in case["dependency_evidence"]
                ),
            )
        )
    if exact_bytes != _canonical_json_bytes(data):
        raise ValueError(
            "authority fixture manifest JSON must use canonical sorted pretty serialization"
        )
    return AuthorityFixtureManifestBinding(
        path=AUTHORITY_FIXTURE_MANIFEST_PATH,
        digest=actual_digest,
        schema_version=data["schema_version"],
        constitution_revision=data["constitution_revision"],
        registry_version=data["registry_version"],
        fixture_pairs=tuple(parsed_pairs),
        cases=tuple(parsed_cases),
    )


def parse_authority_vocabulary(
    exact_bytes: bytes,
    *,
    expected_digest: str,
    expected_constitution_revision: int,
    expected_registry_version: int,
    fixture_manifest_bytes: bytes | None = None,
) -> AuthorityVocabularyBinding:
    """Strictly parse the machine authority vocabulary bound by SPEC-000."""

    actual_digest = f"sha256:{hashlib.sha256(exact_bytes).hexdigest()}"
    if actual_digest != expected_digest:
        raise ValueError(
            f"authority vocabulary digest mismatch: expected {expected_digest}, got {actual_digest}"
        )
    data = _strict_json_loads(exact_bytes, label="authority vocabulary")
    if not isinstance(data, dict):
        raise ValueError("authority vocabulary root must be an object")
    root_keys = {
        "kind",
        "schema_version",
        "owner_spec",
        "constitution_revision",
        "registry_version",
        "entries",
        "fixture_manifest",
    }
    if set(data) != root_keys:
        raise ValueError("authority vocabulary root fields do not match the closed schema")
    if data["kind"] != "AuthorityVocabularyRegistry":
        raise ValueError("authority vocabulary kind must be AuthorityVocabularyRegistry")
    if data["schema_version"] != AUTHORITY_VOCABULARY_SCHEMA_VERSION:
        raise ValueError(
            f"authority vocabulary schema_version must be {AUTHORITY_VOCABULARY_SCHEMA_VERSION}"
        )
    if data["owner_spec"] != AUTHORITY_VOCABULARY_SPEC:
        raise ValueError("authority vocabulary owner_spec must be SPEC-000")
    if (
        type(data["constitution_revision"]) is not int
        or data["constitution_revision"] != expected_constitution_revision
        or expected_constitution_revision < AUTHORITY_VOCABULARY_MIN_REVISION
    ):
        raise ValueError("authority vocabulary constitution_revision is not current")
    if (
        type(data["registry_version"]) is not int
        or data["registry_version"] != expected_registry_version
        or expected_registry_version != expected_constitution_revision
    ):
        raise ValueError("authority vocabulary registry_version is invalid or stale")
    entries = data["entries"]
    if not isinstance(entries, list) or not entries:
        raise ValueError("authority vocabulary entries must be a non-empty array")
    fixture_pointer = data["fixture_manifest"]
    if (
        not isinstance(fixture_pointer, dict)
        or set(fixture_pointer) != AUTHORITY_FIXTURE_POINTER_KEYS
    ):
        raise ValueError("authority fixture manifest pointer does not match the closed schema")
    if fixture_pointer["path"] != AUTHORITY_FIXTURE_MANIFEST_PATH:
        raise ValueError(
            f"authority fixture manifest path must be {AUTHORITY_FIXTURE_MANIFEST_PATH}"
        )
    if not isinstance(fixture_pointer["digest"], str) or re.fullmatch(
        r"sha256:[0-9a-f]{64}", fixture_pointer["digest"]
    ) is None:
        raise ValueError("authority fixture manifest digest is invalid")
    if (
        type(fixture_pointer["version"]) is not int
        or fixture_pointer["version"] != expected_registry_version
    ):
        raise ValueError("authority fixture manifest version is invalid or stale")

    parsed_entries: list[tuple[str, str, str]] = []
    seen_pairs: set[tuple[str, str]] = set()
    token = re.compile(r"^[a-z][a-z0-9_]*$")
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict) or set(entry) != AUTHORITY_ENTRY_KEYS:
            raise ValueError(f"authority entry {index} does not match the closed schema")
        action = entry["action"]
        resource = entry["resource"]
        owner_spec = entry["owner_spec"]
        if not isinstance(action, str) or token.fullmatch(action) is None:
            raise ValueError(f"authority entry {index} has invalid action")
        if not isinstance(resource, str) or token.fullmatch(resource) is None:
            raise ValueError(f"authority entry {index} has invalid resource")
        if not isinstance(owner_spec, str) or re.fullmatch(
            r"SPEC-[0-9]{3}", owner_spec
        ) is None:
            raise ValueError(f"authority entry {index} has invalid owner_spec")
        pair = (action, resource)
        if pair in seen_pairs:
            raise ValueError(f"duplicate authority pair: {action}/{resource}")
        seen_pairs.add(pair)
        profile = REQUIRED_AUTHORITY_PROFILES.get(pair)
        if profile is None:
            raise ValueError(f"unreviewed authority pair: {action}/{resource}")
        _validate_max_effect_shape(entry["max_effect"], label=f"authority entry {index}")
        if owner_spec != profile.owner_spec:
            raise ValueError(
                f"required authority pair {action}/{resource} must be owned by "
                f"{profile.owner_spec}"
            )
        if entry["actor_classes"] != list(profile.actor_classes):
            raise ValueError(f"authority entry {index} actor_classes do not match the profile")
        if entry["max_effect"] != profile.max_effect:
            raise ValueError(f"authority entry {index} max_effect does not match the profile")
        if entry["dependency_floor"] != list(profile.dependency_floor):
            raise ValueError(
                f"authority entry {index} dependency_floor does not match the profile"
            )
        if entry["decision_context_fields"] != list(profile.decision_context_fields):
            raise ValueError(
                f"authority entry {index} decision_context_fields do not match the profile"
            )
        if entry["grant_operation"] != profile.grant_operation:
            raise ValueError(
                f"authority entry {index} grant_operation does not match the profile"
            )
        parsed_entries.append((action, resource, owner_spec))
    if parsed_entries != sorted(parsed_entries):
        raise ValueError("authority vocabulary entries must be sorted by action/resource/owner")
    if [(action, resource) for action, resource, _owner in parsed_entries] != sorted(
        REQUIRED_AUTHORITY_PROFILES
    ):
        raise ValueError("authority vocabulary must contain every reviewed pair exactly once")
    if exact_bytes != _canonical_json_bytes(data):
        raise ValueError("authority vocabulary JSON must use canonical sorted pretty serialization")
    if fixture_manifest_bytes is None:
        raise ValueError("authority fixture manifest is required and cannot be detached")
    fixture_binding = parse_authority_fixture_manifest(
        fixture_manifest_bytes,
        expected_digest=fixture_pointer["digest"],
        expected_constitution_revision=expected_constitution_revision,
        expected_registry_version=expected_registry_version,
        expected_profiles=REQUIRED_AUTHORITY_PROFILES,
    )
    return AuthorityVocabularyBinding(
        path=AUTHORITY_VOCABULARY_PATH,
        digest=actual_digest,
        schema_version=data["schema_version"],
        constitution_revision=data["constitution_revision"],
        registry_version=data["registry_version"],
        entries=tuple(parsed_entries),
        fixture_manifest_path=fixture_binding.path,
        fixture_manifest_digest=fixture_binding.digest,
        fixture_manifest_version=fixture_binding.registry_version,
        fixture_cases=fixture_binding.cases,
    )


def _authority_registry_boundary_decision(
    case: AuthorityFixtureCase,
) -> tuple[str, str]:
    if case.action == "read":
        profile = POLICY_ONLY_READ_PROFILES.get((case.action, case.resource))
        if profile is None:
            return ("deny", "REGISTRY_NON_EVENT_APPEND_DENY")
        if case.actor_class not in profile.actor_classes:
            return ("deny", "REGISTRY_ACTOR_DENY")
        if case.decision_context_fields != profile.decision_context_fields:
            return ("deny", "REGISTRY_GUARD_DENY")
        if (
            case.effect_code != profile.max_effect_code
            or case.max_targets != profile.max_targets
            or case.max_state_transitions != profile.max_state_transitions
        ):
            return ("deny", "REGISTRY_NON_EVENT_APPEND_DENY")
        if case.grant_operation != profile.grant_operation:
            return ("deny", "REGISTRY_GRANT_DENY")
        if not _authority_dependency_floor_satisfied(case, profile):
            return ("deny", "REGISTRY_DEPENDENCY_DENY")
        return ("non_event", "REGISTRY_POLICY_ONLY_READ")
    profile = REQUIRED_AUTHORITY_PROFILES.get((case.action, case.resource))
    if profile is None:
        return ("deny", "REGISTRY_PAIR_DENY")
    if case.actor_class not in profile.actor_classes:
        return ("deny", "REGISTRY_ACTOR_DENY")
    if case.decision_context_fields != profile.decision_context_fields:
        return ("deny", "REGISTRY_GUARD_DENY")
    if (
        case.effect_code != profile.max_effect_code
        or case.max_targets != profile.max_targets
        or case.max_state_transitions != profile.max_state_transitions
    ):
        return ("deny", "REGISTRY_EFFECT_DENY")
    if case.grant_operation != profile.grant_operation:
        return ("deny", "REGISTRY_GRANT_DENY")
    if not _authority_dependency_floor_satisfied(case, profile):
        return ("deny", "REGISTRY_DEPENDENCY_DENY")
    return ("allow", "REGISTRY_ALLOW")


def _authority_dependency_floor_satisfied(
    case: AuthorityFixtureCase,
    profile: AuthoritySemanticProfile | None,
) -> bool:
    """Evaluate only the exact revision/status floor, independent of other denials."""

    if profile is None:
        required = {"SPEC-000": 2}
    else:
        required = {
            binding.split("@", maxsplit=1)[0]: int(
                binding.split("@", maxsplit=1)[1]
            )
            for binding in profile.dependency_floor
        }
    evidence = {
        spec_id: (revision, status)
        for spec_id, revision, status in case.dependency_evidence
    }
    return set(evidence) == set(required) and all(
        evidence[spec_id][0] >= revision
        and evidence[spec_id][1] in AUTHORITY_VOCABULARY_READY_STATUSES
        for spec_id, revision in required.items()
    )


def authority_policy_case_results(
    registry: AuthorityVocabularyBinding,
    constitution: Any,
) -> tuple[dict[str, object], ...]:
    """Execute the combined registry boundary and Constitution.decide gate."""

    results: list[dict[str, object]] = []
    for case in registry.fixture_cases:
        profile = REQUIRED_AUTHORITY_PROFILES.get(
            (case.action, case.resource)
        ) or POLICY_ONLY_READ_PROFILES.get((case.action, case.resource))
        registry_decision, registry_reason = _authority_registry_boundary_decision(case)
        canonical_context = {
            field: True for field in sorted(case.decision_context_fields)
        }
        dependency_value = [
            {"spec": spec_id, "revision": revision, "status": status}
            for spec_id, revision, status in case.dependency_evidence
        ]
        canonical_context.update(
            {
                "dependency_evidence_digest": f"sha256:{hashlib.sha256(_canonical_json_bytes(dependency_value)).hexdigest()}",
                "dependency_floor_satisfied": _authority_dependency_floor_satisfied(
                    case, profile
                ),
                "grant_operation": case.grant_operation,
                "requested_effect_code": case.effect_code,
                "requested_max_state_transitions": case.max_state_transitions,
                "requested_max_targets": case.max_targets,
            }
        )
        context_digest = f"sha256:{hashlib.sha256(_canonical_json_bytes(canonical_context)).hexdigest()}"
        decision = constitution.decide(
            case.actor_class,
            case.action,
            case.resource,
            canonical_context,
        )
        policy_decision = "allow" if decision.allowed else "deny"
        actual_decision = (
            "allow"
            if registry_decision in {"allow", "non_event"} and policy_decision == "allow"
            else "deny"
        )
        matched_rule = decision.matched_rule
        reason_code = decision.reason_code
        results.append(
            {
                "action": case.action,
                "resource": case.resource,
                "case": case.case,
                "expected_decision": case.expected_decision,
                "expected_policy_decision": case.expected_policy_decision,
                "expected_registry_decision": case.expected_registry_decision,
                "registry_decision": registry_decision,
                "registry_reason_code": registry_reason,
                "policy_decision": policy_decision,
                "actual_decision": actual_decision,
                "context_digest": context_digest,
                "matched_rule": matched_rule,
                "reason_code": reason_code,
            }
        )
    return tuple(results)


def expected_authority_policy_conditions(
    profile: AuthoritySemanticProfile,
) -> tuple[dict[str, object], ...]:
    """Return the sole accepted allow-rule predicate shape for one profile."""

    conditions: dict[str, dict[str, object]] = {
        field: {"key": field, "operator": "present"}
        for field in profile.decision_context_fields
    }
    conditions.update(
        {
            "dependency_evidence_digest": {
                "key": "dependency_evidence_digest",
                "operator": "present",
            },
            "dependency_floor_satisfied": {
                "key": "dependency_floor_satisfied",
                "operator": "equals",
                "value": True,
            },
            "grant_operation": {
                "key": "grant_operation",
                "operator": "equals",
                "value": profile.grant_operation,
            },
            "requested_effect_code": {
                "key": "requested_effect_code",
                "operator": "equals",
                "value": profile.max_effect_code,
            },
            "requested_max_state_transitions": {
                "key": "requested_max_state_transitions",
                "operator": "equals",
                "value": profile.max_state_transitions,
            },
            "requested_max_targets": {
                "key": "requested_max_targets",
                "operator": "equals",
                "value": profile.max_targets,
            },
        }
    )
    return tuple(conditions[key] for key in sorted(conditions))


def validate_authority_policy_closure(constitution: Any) -> None:
    """Reject noncatalog, overbroad, duplicate, or weaker allow-rule paths."""

    try:
        rules = constitution.rules
    except (AttributeError, KeyError, TypeError) as exc:
        raise ValueError("constitution does not expose validated policy rules") from exc
    seen_paths: set[tuple[str, str, str]] = set()
    for rule in rules:
        if rule.get("effect") != "allow":
            continue
        for action in rule["actions"]:
            for resource in rule["resources"]:
                pair = (action, resource)
                profile = REQUIRED_AUTHORITY_PROFILES.get(
                    pair
                ) or POLICY_ONLY_READ_PROFILES.get(pair)
                if profile is None:
                    raise ValueError(
                        f"allow rule {rule['rule_id']} contains noncatalog pair "
                        f"{action}/{resource}"
                    )
                if not set(rule["actors"]).issubset(profile.actor_classes):
                    raise ValueError(
                        f"allow rule {rule['rule_id']} widens actors for "
                        f"{action}/{resource}"
                    )
                if rule.get("conditions", []) != list(
                    expected_authority_policy_conditions(profile)
                ):
                    raise ValueError(
                        f"allow rule {rule['rule_id']} has a noncanonical predicate "
                        f"for {action}/{resource}"
                    )
                for actor in rule["actors"]:
                    path = (actor, action, resource)
                    if path in seen_paths:
                        raise ValueError(
                            f"duplicate allow path for {actor}/{action}/{resource}"
                        )
                    seen_paths.add(path)


def parse_authority_policy_conformance(
    exact_bytes: bytes,
    *,
    registry: AuthorityVocabularyBinding,
    constitution: Any,
    validator_bytes: bytes,
) -> AuthorityPolicyConformanceBinding:
    """Validate and independently reproduce an implemented-stage receipt."""

    data = _strict_json_loads(exact_bytes, label="authority policy conformance receipt")
    if not isinstance(data, dict):
        raise ValueError("authority policy conformance receipt root must be an object")
    root_keys = {
        "kind",
        "schema_version",
        "constitution_revision",
        "registry_version",
        "constitution_policy",
        "registry_digest",
        "fixture_manifest_digest",
        "validator",
        "case_count",
        "skipped_case_count",
        "result",
        "cases",
    }
    if set(data) != root_keys:
        raise ValueError(
            "authority policy conformance receipt fields do not match the closed schema"
        )
    if data["kind"] != "AuthorityVocabularyConformanceReceipt":
        raise ValueError("authority policy conformance receipt kind is invalid")
    if data["schema_version"] != AUTHORITY_CONFORMANCE_RECEIPT_SCHEMA_VERSION:
        raise ValueError(
            "authority policy conformance receipt schema_version must be "
            f"{AUTHORITY_CONFORMANCE_RECEIPT_SCHEMA_VERSION}"
        )
    if (
        type(data["constitution_revision"]) is not int
        or data["constitution_revision"] != registry.constitution_revision
        or type(data["registry_version"]) is not int
        or data["registry_version"] != registry.registry_version
    ):
        raise ValueError("authority policy conformance receipt revision binding is stale")

    policy = data["constitution_policy"]
    if not isinstance(policy, dict) or set(policy) != AUTHORITY_CONFORMANCE_POLICY_KEYS:
        raise ValueError("authority policy conformance policy binding is invalid")
    expected_policy_digest = f"sha256:{constitution.digest}"
    if (
        policy["path"] != AUTHORITY_CONSTITUTION_POLICY_PATH
        or policy["digest"] != expected_policy_digest
        or policy["version"] != constitution.version
    ):
        raise ValueError("authority policy conformance receipt binds the wrong constitution")
    if data["registry_digest"] != registry.digest:
        raise ValueError("authority policy conformance receipt binds the wrong registry")
    if data["fixture_manifest_digest"] != registry.fixture_manifest_digest:
        raise ValueError("authority policy conformance receipt binds the wrong fixture manifest")

    validator = data["validator"]
    if not isinstance(validator, dict) or set(validator) != AUTHORITY_CONFORMANCE_VALIDATOR_KEYS:
        raise ValueError("authority policy conformance validator binding is invalid")
    expected_validator_digest = f"sha256:{hashlib.sha256(validator_bytes).hexdigest()}"
    if (
        validator["path"] != AUTHORITY_VALIDATOR_PATH
        or validator["digest"] != expected_validator_digest
        or validator["version"] != AUTHORITY_VALIDATOR_VERSION
    ):
        raise ValueError("authority policy conformance receipt binds the wrong validator")

    expected_results = list(authority_policy_case_results(registry, constitution))
    try:
        validate_authority_policy_closure(constitution)
    except ValueError as exc:
        raise ValueError(
            "constitution policy does not implement the authority registry: "
            f"{exc}"
        ) from exc
    nonconforming = [
        result
        for result in expected_results
        if result["policy_decision"] != result["expected_policy_decision"]
        or result["registry_decision"] != result["expected_registry_decision"]
        or result["actual_decision"] != result["expected_decision"]
    ]
    if nonconforming:
        first = nonconforming[0]
        raise ValueError(
            "constitution policy does not implement the authority registry: "
            f"{first['action']}/{first['resource']}/{first['case']} expected "
            f"policy={first['expected_policy_decision']}, "
            f"registry={first['expected_registry_decision']}, "
            f"combined={first['expected_decision']}; got "
            f"policy={first['policy_decision']}, "
            f"registry={first['registry_decision']}, "
            f"combined={first['actual_decision']}"
        )
    if (
        type(data["case_count"]) is not int
        or data["case_count"] != len(expected_results)
        or type(data["skipped_case_count"]) is not int
        or data["skipped_case_count"] != 0
        or data["result"] != "pass"
    ):
        raise ValueError("authority policy conformance receipt summary is not an exact pass")
    cases = data["cases"]
    if not isinstance(cases, list):
        raise ValueError("authority policy conformance receipt cases must be an array")
    for index, case in enumerate(cases):
        if not isinstance(case, dict) or set(case) != AUTHORITY_CONFORMANCE_CASE_KEYS:
            raise ValueError(
                f"authority policy conformance case {index} does not match the closed schema"
            )
    if cases != expected_results:
        raise ValueError(
            "authority policy conformance receipt does not cover every manifest case exactly"
        )
    if exact_bytes != _canonical_json_bytes(data):
        raise ValueError(
            "authority policy conformance receipt must use canonical sorted pretty serialization"
        )
    return AuthorityPolicyConformanceBinding(
        path=AUTHORITY_CONFORMANCE_RECEIPT_PATH,
        digest=f"sha256:{hashlib.sha256(exact_bytes).hexdigest()}",
        schema_version=data["schema_version"],
        constitution_policy_digest=policy["digest"],
        registry_digest=data["registry_digest"],
        fixture_manifest_digest=data["fixture_manifest_digest"],
        validator_digest=validator["digest"],
        validator_version=validator["version"],
        case_count=data["case_count"],
    )


def _load_constitution_for_conformance(path: Path) -> Any:
    try:
        from researcher.scripts.governance_policy import Constitution
    except ModuleNotFoundError:  # direct script execution from researcher/scripts
        from governance_policy import Constitution
    return Constitution.load(path)


def load_authority_vocabulary(
    root: Path,
    metadata: Mapping[str, str],
    *,
    expected_constitution_revision: int,
) -> AuthorityVocabularyBinding:
    path_value = metadata.get("Authority vocabulary")
    digest = metadata.get("Authority vocabulary digest")
    version_value = metadata.get("Authority vocabulary version")
    if path_value != AUTHORITY_VOCABULARY_PATH:
        raise ValueError(
            f"Authority vocabulary must be the canonical path {AUTHORITY_VOCABULARY_PATH}"
        )
    if digest is None or re.fullmatch(r"sha256:[0-9a-f]{64}", digest) is None:
        raise ValueError("Authority vocabulary digest must be sha256:<64 lowercase hex>")
    if version_value is None or re.fullmatch(r"[1-9][0-9]*", version_value) is None:
        raise ValueError("Authority vocabulary version must be a canonical positive integer")
    registry_version = int(version_value)
    path = root / AUTHORITY_VOCABULARY_PATH
    if path.is_symlink() or not path.is_file():
        raise ValueError("authority vocabulary must be a regular canonical repository file")
    fixture_path = root / AUTHORITY_FIXTURE_MANIFEST_PATH
    if fixture_path.is_symlink() or not fixture_path.is_file():
        raise ValueError("authority fixture manifest must be a regular canonical repository file")
    binding = parse_authority_vocabulary(
        path.read_bytes(),
        expected_digest=digest,
        expected_constitution_revision=expected_constitution_revision,
        expected_registry_version=registry_version,
        fixture_manifest_bytes=fixture_path.read_bytes(),
    )
    receipt_path = root / AUTHORITY_CONFORMANCE_RECEIPT_PATH
    if receipt_path.is_symlink():
        raise ValueError(
            "authority policy conformance receipt must be a regular canonical repository file"
        )
    if not receipt_path.exists():
        return binding
    if not receipt_path.is_file():
        raise ValueError(
            "authority policy conformance receipt must be a regular canonical repository file"
        )
    constitution_path = root / AUTHORITY_CONSTITUTION_POLICY_PATH
    validator_path = root / AUTHORITY_VALIDATOR_PATH
    if constitution_path.is_symlink() or not constitution_path.is_file():
        raise ValueError("authority constitution policy must be a regular canonical file")
    if validator_path.is_symlink() or not validator_path.is_file():
        raise ValueError("authority conformance validator must be a regular canonical file")
    conformance = parse_authority_policy_conformance(
        receipt_path.read_bytes(),
        registry=binding,
        constitution=_load_constitution_for_conformance(constitution_path),
        validator_bytes=validator_path.read_bytes(),
    )
    return replace(binding, policy_conformance=conformance)


def load_candidate_authority_vocabulary(
    root: Path,
    candidate_specs: Mapping[str, SpecRevision],
) -> AuthorityVocabularyBinding | None:
    """Load the sole canonical registry or reject detached registry artifacts."""

    authority_spec = candidate_specs.get(AUTHORITY_VOCABULARY_SPEC)
    metadata_keys = {
        "Authority vocabulary",
        "Authority vocabulary digest",
        "Authority vocabulary version",
    }
    has_metadata = authority_spec is not None and bool(
        metadata_keys.intersection(authority_spec.metadata)
    )
    registry_path = root / AUTHORITY_VOCABULARY_PATH
    fixture_path = root / AUTHORITY_FIXTURE_MANIFEST_PATH
    registry_present = registry_path.exists() or registry_path.is_symlink()
    fixture_present = fixture_path.exists() or fixture_path.is_symlink()
    receipt_path = root / AUTHORITY_CONFORMANCE_RECEIPT_PATH
    receipt_present = receipt_path.exists() or receipt_path.is_symlink()
    if not (has_metadata or registry_present or fixture_present or receipt_present):
        return None
    if authority_spec is None:
        raise ValueError("authority vocabulary artifacts require canonical SPEC-000")
    if (
        authority_spec.revision >= AUTHORITY_VOCABULARY_MIN_REVISION
        and authority_spec.status in AUTHORITY_PREIMPLEMENTATION_STATUSES
        and receipt_present
    ):
        raise ValueError(
            "pre-implementation SPEC-000 revisions forbid the canonical "
            "authority-policy conformance receipt"
        )
    binding = load_authority_vocabulary(
        root,
        authority_spec.metadata,
        expected_constitution_revision=authority_spec.revision,
    )
    if (
        authority_spec.status in AUTHORITY_IMPLEMENTED_STATUSES
        and binding.policy_conformance is None
    ):
        raise ValueError(
            "implemented, verified, and operational SPEC-000 revisions require "
            "the validated authority-policy conformance receipt"
        )
    return binding


def parse_spec_revision(path: str, exact_bytes: bytes, *, allow_legacy: bool) -> SpecRevision:
    try:
        text = exact_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"specification is not UTF-8: {exc}") from exc
    lines = text.splitlines()
    heading = SPEC_HEADING_RE.fullmatch(lines[0] if lines else "")
    if heading is None:
        raise ValueError("first line must be '# SPEC-NNN: Title'")

    metadata: dict[str, str] = {}
    body_start = len(lines)
    for index, raw_line in enumerate(lines[1:], start=1):
        stripped = raw_line.strip()
        if stripped.startswith("## "):
            body_start = index
            break
        if not stripped:
            continue
        if stripped.startswith("- ") and allow_legacy:
            stripped = stripped[2:].strip()
        if ":" not in stripped:
            raise ValueError(f"metadata line has no colon: {stripped!r}")
        key, value = (part.strip() for part in stripped.split(":", 1))
        if not allow_legacy and raw_line != f"{key}: {value}":
            raise ValueError(
                "metadata must use canonical 'Key: value' serialization without extra whitespace"
            )
        if key in metadata:
            raise ValueError(f"duplicate metadata key: {key}")
        metadata[key] = value

    if not allow_legacy:
        blank_lines = [
            index for index, line in enumerate(lines[:body_start]) if line == ""
        ]
        if blank_lines != [1, body_start - 1]:
            raise ValueError(
                "specification header requires one blank line after the heading and one before the body"
            )

    status = metadata.get("Status", "")
    legacy_metadata = allow_legacy and "Revision" not in metadata
    if not legacy_metadata and status not in KNOWN_STATUSES:
        raise ValueError(f"unsupported status: {status!r}")
    if legacy_metadata:
        revision = 1
        revises = "none"
    else:
        try:
            revision = int(metadata.get("Revision", ""))
        except ValueError as exc:
            raise ValueError(f"invalid revision: {metadata.get('Revision')!r}") from exc
        if revision < 1:
            raise ValueError("revision must be positive")
        revises = metadata.get("Revises", "")

    return SpecRevision(
        path=path,
        spec_id=heading.group("id"),
        title=heading.group("title"),
        status=status,
        revision=revision,
        revises=revises,
        adoption_decision=metadata.get("Adoption decision"),
        lifecycle_decision=metadata.get("Lifecycle decision"),
        replacement=metadata.get("Replacement"),
        metadata=metadata,
        contract_body="\n".join(lines[body_start:]) + ("\n" if text.endswith("\n") else ""),
        exact_bytes=exact_bytes,
        legacy_metadata=legacy_metadata,
    )


def parse_adr_revision(path: str, exact_bytes: bytes) -> AdrRevision:
    try:
        text = exact_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"architecture decision is not UTF-8: {exc}") from exc
    lines = text.splitlines()
    heading = ADR_HEADING_RE.fullmatch(lines[0] if lines else "")
    if heading is None:
        raise ValueError("ADR first line must be '# ADR-NNNN: Title'")
    status: str | None = None
    lifecycle_transition: str | None = None
    for raw_line in lines[1:]:
        stripped = raw_line.strip()
        if stripped.startswith("## "):
            break
        if not stripped:
            continue
        if stripped.startswith("- Status:"):
            if status is not None:
                raise ValueError("duplicate ADR Status metadata")
            status = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("- Lifecycle transition:"):
            if lifecycle_transition is not None:
                raise ValueError("duplicate ADR Lifecycle transition metadata")
            lifecycle_transition = stripped.split(":", 1)[1].strip()
    if not status:
        raise ValueError("ADR Status metadata is required")
    return AdrRevision(
        path=path,
        adr_id=heading.group("id"),
        title=heading.group("title"),
        status=status,
        lifecycle_transition=lifecycle_transition,
        exact_bytes=exact_bytes,
    )


def validate_adr_lifecycle(
    base: Mapping[str, AdrRevision],
    candidate: Mapping[str, AdrRevision],
) -> list[LifecycleFinding]:
    findings: list[LifecycleFinding] = []
    base_numbers = [int(adr_id[-4:]) for adr_id in base]
    maximum_base_number = max(base_numbers, default=-1)
    for adr_id in sorted(set(candidate) - set(base)):
        current = candidate[adr_id]
        if int(adr_id[-4:]) <= maximum_base_number:
            findings.append(
                LifecycleFinding(
                    "ADR_NUMBER_NOT_APPEND_ONLY",
                    current.path,
                    adr_id,
                    f"new ADR number must exceed base maximum ADR-{maximum_base_number:04d}",
                )
            )
    for adr_id, previous in sorted(base.items()):
        if previous.status != "accepted":
            continue
        current = candidate.get(adr_id)
        if current is None:
            findings.append(
                LifecycleFinding(
                    "ADR_DELETION_FORBIDDEN",
                    previous.path,
                    adr_id,
                    "an accepted architecture decision cannot be deleted",
                )
            )
        elif current.path != previous.path or current.exact_bytes != previous.exact_bytes:
            findings.append(
                LifecycleFinding(
                    "ACCEPTED_ADR_IMMUTABLE",
                    current.path,
                    adr_id,
                    "an accepted architecture decision is byte-immutable; add a later ADR that explicitly supersedes it",
                )
            )
    return sorted(findings, key=lambda item: (item.path, item.code, item.message))


def validate_lifecycle_decision_bindings(
    base: Mapping[str, SpecRevision],
    candidate: Mapping[str, SpecRevision],
    candidate_adrs: Mapping[str, AdrRevision],
) -> list[LifecycleFinding]:
    """Bind every terminal transition to one exact accepted ADR decision."""

    findings: list[LifecycleFinding] = []
    for spec_id, current in sorted(candidate.items()):
        previous = base.get(spec_id)
        if (
            previous is None
            or previous.legacy_metadata
            or current.status == previous.status
            or current.status not in TERMINAL_STATUSES
            or current.lifecycle_decision is None
        ):
            continue
        decision = candidate_adrs.get(current.lifecycle_decision)
        expected_target = (
            current.replacement
            if current.status in {"amended", "superseded"}
            else "none"
        )
        expected = (
            f"{current.spec_id}@{current.revision} -> "
            f"{current.status} -> {expected_target}"
        )
        if (
            decision is None
            or decision.status != "accepted"
            or decision.lifecycle_transition != expected
        ):
            findings.append(
                LifecycleFinding(
                    "SPEC_LIFECYCLE_DECISION_MISMATCH",
                    current.path,
                    current.spec_id,
                    f"{current.lifecycle_decision} must be accepted and bind exact "
                    f"transition {expected!r}",
                )
            )
    return sorted(findings, key=lambda item: (item.path, item.code, item.message))


def validate_lifecycle(
    base: Mapping[str, SpecRevision],
    candidate: Mapping[str, SpecRevision],
    *,
    authority_vocabulary: AuthorityVocabularyBinding | None = None,
) -> list[LifecycleFinding]:
    findings: list[LifecycleFinding] = []

    def report(code: str, record: SpecRevision, message: str) -> None:
        findings.append(LifecycleFinding(code, record.path, record.spec_id, message))

    def direct_dependencies(record: SpecRevision) -> tuple[str, ...]:
        value = record.metadata.get("Depends on", "")
        if value == "none":
            return ()
        return tuple(part.strip() for part in value.split(",") if part.strip())

    def dependency_revisions(record: SpecRevision) -> dict[str, int] | None:
        value = record.metadata.get("Dependency revisions")
        if value == "none":
            return {}
        if not value:
            return None
        parsed: dict[str, int] = {}
        for part in value.split(","):
            match = re.fullmatch(
                r"(SPEC-[0-9]{3})@([1-9][0-9]*)",
                part.strip(),
            )
            if match is None or match.group(1) in parsed:
                return None
            parsed[match.group(1)] = int(match.group(2))
        return parsed

    def authority_binding_matches(record: SpecRevision | None) -> bool:
        if record is None or authority_vocabulary is None:
            return False
        return (
            authority_vocabulary.path
            == record.metadata.get("Authority vocabulary")
            and authority_vocabulary.digest
            == record.metadata.get("Authority vocabulary digest")
            and str(authority_vocabulary.registry_version)
            == record.metadata.get("Authority vocabulary version")
            and authority_vocabulary.constitution_revision == record.revision
            and authority_vocabulary.constitution_revision
            >= AUTHORITY_VOCABULARY_MIN_REVISION
            and authority_vocabulary.fixture_manifest_path
            == AUTHORITY_FIXTURE_MANIFEST_PATH
            and authority_vocabulary.fixture_manifest_version
            == authority_vocabulary.registry_version
            and re.fullmatch(
                r"sha256:[0-9a-f]{64}",
                authority_vocabulary.fixture_manifest_digest,
            )
            is not None
        )

    def policy_conformance_matches() -> bool:
        if authority_vocabulary is None:
            return False
        receipt = authority_vocabulary.policy_conformance
        return (
            receipt is not None
            and receipt.path == AUTHORITY_CONFORMANCE_RECEIPT_PATH
            and receipt.schema_version
            == AUTHORITY_CONFORMANCE_RECEIPT_SCHEMA_VERSION
            and receipt.registry_digest == authority_vocabulary.digest
            and receipt.fixture_manifest_digest
            == authority_vocabulary.fixture_manifest_digest
            and receipt.validator_version == AUTHORITY_VALIDATOR_VERSION
            and re.fullmatch(r"sha256:[0-9a-f]{64}", receipt.validator_digest)
            is not None
            and receipt.case_count == len(authority_vocabulary.fixture_cases)
        )

    for spec_id in sorted(set(base) - set(candidate)):
        record = base[spec_id]
        report(
            "SPEC_DELETION_FORBIDDEN",
            record,
            "canonical specification revisions remain in history and cannot be deleted",
        )

    for spec_id, current in sorted(candidate.items()):
        previous = base.get(spec_id)
        if (
            current.spec_id == AUTHORITY_VOCABULARY_SPEC
            and current.revision >= AUTHORITY_VOCABULARY_MIN_REVISION
            and not authority_binding_matches(current)
        ):
            report(
                "SPEC_AUTHORITY_VOCABULARY_INVALID",
                current,
                "SPEC-000 revision 2 or later requires the exact revision-bound, "
                "digest-pinned AuthorityVocabularyRegistry and fixture manifest",
            )
        if (
            current.spec_id == AUTHORITY_VOCABULARY_SPEC
            and current.revision >= AUTHORITY_VOCABULARY_MIN_REVISION
            and current.status in AUTHORITY_PREIMPLEMENTATION_STATUSES
            and authority_vocabulary is not None
            and authority_vocabulary.policy_conformance is not None
        ):
            report(
                "SPEC_AUTHORITY_POLICY_CONFORMANCE_PREMATURE",
                current,
                "draft, architecture-reviewed, and accepted SPEC-000 revisions "
                "must not carry an implementation-stage conformance receipt",
            )
        requires_policy_conformance = current.status in AUTHORITY_IMPLEMENTED_STATUSES and (
            (
                current.spec_id == AUTHORITY_VOCABULARY_SPEC
                and current.revision >= AUTHORITY_VOCABULARY_MIN_REVISION
            )
            or int(current.spec_id[-3:]) >= 4
        )
        authority_spec = (
            current
            if current.spec_id == AUTHORITY_VOCABULARY_SPEC
            else candidate.get(AUTHORITY_VOCABULARY_SPEC)
        )
        if requires_policy_conformance and (
            not authority_binding_matches(authority_spec)
            or not policy_conformance_matches()
        ):
            report(
                "SPEC_AUTHORITY_POLICY_CONFORMANCE_REQUIRED",
                current,
                "implemented, verified, and operational stages require the exact "
                "recomputed authority-policy conformance receipt with zero skipped cases",
            )
        if previous is None:
            if current.status != "draft" or current.revision != 1 or current.revises != "none":
                report(
                    "INVALID_INITIAL_SPEC_REVISION",
                    current,
                    "a new specification must enter as draft revision 1 with Revises: none",
                )
            if (
                current.spec_id == "SPEC-026"
                and current.revision == 1
                and current.metadata.get("Activation") != "deferred"
            ):
                report(
                    "INVALID_SPEC_ACTIVATION",
                    current,
                    "SPEC-026 revision 1 must remain Activation: deferred",
                )
            continue

        adoption = LEGACY_ADOPTION.get(spec_id)
        if previous.legacy_metadata and adoption is not None:
            expected_base, expected_current = adoption
            expected_keys = set(previous.metadata) | {
                "Revision",
                "Revises",
                "Owners",
                "Adoption decision",
                "Dependency revisions",
            }
            preserved_legacy_metadata = all(
                current.metadata.get(key) == value
                for key, value in previous.metadata.items()
                if key != "Status"
            )
            if (
                previous.status == expected_base
                and current.status == expected_current
                and current.revision == 1
                and current.revises == "none"
                and current.adoption_decision == LEGACY_ADOPTION_DECISION
                and current.lifecycle_decision is None
                and current.metadata.get("Owners") == LEGACY_ADOPTION_OWNERS[spec_id]
                and current.metadata.get("Dependency revisions")
                == LEGACY_ADOPTION_DEPENDENCY_REVISIONS[spec_id]
                and set(current.metadata) == expected_keys
                and preserved_legacy_metadata
                and previous.path == current.path
                and previous.title == current.title
                and previous.contract_body == current.contract_body
            ):
                continue
            report(
                "INVALID_LEGACY_LIFECYCLE_ADOPTION",
                current,
                "legacy SPEC-000 through SPEC-003 normalization must match ADR-0005 exactly",
            )
            continue

        if previous.legacy_metadata:
            report(
                "UNDECLARED_LEGACY_SPEC",
                current,
                "legacy metadata is allowed only for the explicit ADR-0005 adoption set",
            )
            continue

        if current.path != previous.path:
            report(
                "SPEC_PATH_CHANGED",
                current,
                "a specification identity cannot move to a different canonical path",
            )

        if current.revision < previous.revision:
            report(
                "SPEC_REVISION_REGRESSION",
                current,
                f"revision {current.revision} is older than base revision {previous.revision}",
            )
            continue
        if current.revision > previous.revision:
            if current.revision != previous.revision + 1:
                report(
                    "SPEC_REVISION_GAP",
                    current,
                    "a replacement revision must increment by exactly one",
                )
            if current.status != "draft":
                report(
                    "SPEC_REVISION_NOT_DRAFT",
                    current,
                    "a replacement revision must restart at draft",
                )
            if current.revises != previous.digest:
                report(
                    "SPEC_REVISION_DIGEST_MISMATCH",
                    current,
                    f"Revises must bind the exact base bytes as {previous.digest}",
                )
            if previous.status not in {"amended", "superseded"}:
                report(
                    "SPEC_REVISION_PREDECESSOR_ACTIVE",
                    current,
                    "the prior revision must first be human-merged as amended or superseded",
                )
            expected_replacement = f"{current.spec_id}@{current.revision}"
            if previous.status in {"amended", "superseded"} and (
                previous.replacement != expected_replacement
            ):
                report(
                    "SPEC_REPLACEMENT_MISMATCH",
                    current,
                    "the terminal predecessor must name this exact replacement as "
                    f"{expected_replacement}",
                )
            continue

        if current.revises != previous.revises:
            report(
                "SPEC_REVISION_IDENTITY_CHANGED",
                current,
                "Revises cannot change without a new revision",
            )
        if current.adoption_decision != previous.adoption_decision:
            report(
                "SPEC_ADOPTION_METADATA_CHANGED",
                current,
                "the one-time adoption decision is immutable within its revision",
            )
        if (
            previous.status != "draft"
            and current.metadata.get("Dependency revisions")
            != previous.metadata.get("Dependency revisions")
        ):
            report(
                "SPEC_DEPENDENCY_BINDING_CHANGED",
                current,
                "dependency revision bindings are immutable after architecture review",
            )
        if (
            current.spec_id == "SPEC-026"
            and current.metadata.get("Activation") != previous.metadata.get("Activation")
        ):
            report(
                "SPEC_ACTIVATION_REVISION_REQUIRED",
                current,
                "changing SPEC-026 Activation requires a new digest-linked revision",
            )
        lifecycle_metadata_changed = (
            current.lifecycle_decision != previous.lifecycle_decision
            or current.replacement != previous.replacement
        )
        lifecycle_metadata_initialization = (
            previous.lifecycle_decision is None
            and previous.replacement is None
            and current.status != previous.status
            and current.status in TERMINAL_STATUSES
        )
        if lifecycle_metadata_changed and not lifecycle_metadata_initialization:
            report(
                "SPEC_LIFECYCLE_METADATA_CHANGED",
                current,
                "Lifecycle decision and Replacement may be written once only on entry to a terminal state",
            )
        allowed = LEGAL_SAME_REVISION_TRANSITIONS.get(previous.status, set())
        if current.status not in allowed:
            report(
                "INVALID_SPEC_STATUS_TRANSITION",
                current,
                f"{previous.status} -> {current.status} is not a legal same-revision transition",
            )
        if current.status in TERMINAL_STATUSES and current.lifecycle_decision is None:
            report(
                "MISSING_SPEC_LIFECYCLE_DECISION",
                current,
                "a terminal transition requires a Lifecycle decision",
            )
        if current.status in ACTIVE_STATUSES and current.lifecycle_decision is not None:
            report(
                "INVALID_SPEC_LIFECYCLE_DECISION",
                current,
                "Lifecycle decision must be absent until entry to a terminal state",
            )
        if current.status in {"amended", "superseded"} and not current.replacement:
            report(
                "MISSING_SPEC_REPLACEMENT",
                current,
                "an amended or superseded transition requires an exact Replacement",
            )
        elif current.status in {"amended", "superseded"}:
            expected_replacement = f"{current.spec_id}@{current.revision + 1}"
            if current.replacement != expected_replacement:
                report(
                    "SPEC_REPLACEMENT_MISMATCH",
                    current,
                    "an amended or superseded transition must name the next revision of "
                    f"the same specification as {expected_replacement}",
                )

        contract_changed = current.contract_identity != previous.contract_identity
        status_changed = current.status != previous.status
        if status_changed and contract_changed:
            report(
                "SPEC_STATUS_TRANSITION_NOT_ISOLATED",
                current,
                "a lifecycle transition cannot also change the contract",
            )
        elif previous.status in ACCEPTED_OR_LATER and contract_changed:
            report(
                "SPEC_REVISION_REQUIRED",
                current,
                "an accepted contract change requires a new draft revision",
            )
        elif previous.status == "architecture_reviewed" and contract_changed:
            report(
                "SPEC_REVISION_REQUIRED",
                current,
                "an architecture-reviewed contract change requires a new draft revision",
            )

        if (
            status_changed
            and current.status in STAGE_RANK
            and current.status != "draft"
        ):
            if int(current.spec_id[-3:]) >= 4:
                authority_spec = candidate.get(AUTHORITY_VOCABULARY_SPEC)
                if (
                    authority_spec is None
                    or authority_spec.revision < AUTHORITY_VOCABULARY_MIN_REVISION
                    or authority_spec.status not in AUTHORITY_VOCABULARY_READY_STATUSES
                    or not authority_binding_matches(authority_spec)
                ):
                    report(
                        "SPEC_AUTHORITY_VOCABULARY_NOT_READY",
                        current,
                        "SPEC-004 and later cannot advance until the candidate tree "
                        "contains accepted SPEC-000 revision 2 or later with the "
                        "AuthorityVocabularyRegistry",
                    )
            required_rank = STAGE_RANK[current.status]
            expected_dependencies = set(direct_dependencies(current))
            bound_revisions = dependency_revisions(current)
            if bound_revisions is None or set(bound_revisions) != expected_dependencies:
                report(
                    "SPEC_DEPENDENCY_REVISION_MISMATCH",
                    current,
                    "the transition must bind every direct dependency exactly as SPEC-NNN@revision",
                )
                bound_revisions = {}
            for dependency_id in direct_dependencies(current):
                dependency = candidate.get(dependency_id)
                if dependency is None:
                    report(
                        "SPEC_DEPENDENCY_NOT_READY",
                        current,
                        f"direct dependency {dependency_id} is absent from the candidate tree",
                    )
                    continue
                if bound_revisions.get(dependency_id) != dependency.revision:
                    report(
                        "SPEC_DEPENDENCY_REVISION_MISMATCH",
                        current,
                        f"binding for {dependency_id} must match candidate revision "
                        f"{dependency.revision}",
                    )
                if (
                    dependency_id == AUTHORITY_VOCABULARY_SPEC
                    and int(current.spec_id[-3:]) >= 4
                    and bound_revisions.get(dependency_id, 0)
                    < AUTHORITY_VOCABULARY_MIN_REVISION
                ):
                    report(
                        "SPEC_AUTHORITY_VOCABULARY_NOT_READY",
                        current,
                        "the frozen SPEC-000 dependency must be revision 2 or later",
                    )
                dependency_rank = STAGE_RANK.get(dependency.status)
                if dependency_rank is None or dependency_rank < required_rank:
                    report(
                        "SPEC_DEPENDENCY_NOT_READY",
                        current,
                        f"{current.status} requires {dependency_id}@{dependency.revision} "
                        f"at {current.status} or later, found {dependency.status}",
                    )

    return sorted(findings, key=lambda item: (item.path, item.code, item.message))


def _git(root: Path, arguments: list[str]) -> bytes:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=root,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(stderr or f"git {' '.join(arguments)} failed")
    return completed.stdout


def load_candidate(root: Path) -> dict[str, SpecRevision]:
    records: dict[str, SpecRevision] = {}
    for path in sorted((root / "docs" / "specs").glob("SPEC-*.md")):
        relative = path.relative_to(root).as_posix()
        if SPEC_PATH_RE.fullmatch(relative) is None:
            continue
        record = parse_spec_revision(relative, path.read_bytes(), allow_legacy=False)
        if record.spec_id in records:
            raise ValueError(f"duplicate specification ID: {record.spec_id}")
        records[record.spec_id] = record
    return records


def load_base(root: Path, base_ref: str) -> dict[str, SpecRevision]:
    _git(root, ["rev-parse", "--verify", f"{base_ref}^{{commit}}"])
    paths = _git(
        root,
        ["ls-tree", "-r", "--name-only", base_ref, "--", "docs/specs"],
    ).decode("utf-8").splitlines()
    records: dict[str, SpecRevision] = {}
    for path in sorted(path for path in paths if SPEC_PATH_RE.fullmatch(path)):
        record = parse_spec_revision(
            path,
            _git(root, ["show", f"{base_ref}:{path}"]),
            allow_legacy=True,
        )
        if record.spec_id in records:
            raise ValueError(f"duplicate base specification ID: {record.spec_id}")
        records[record.spec_id] = record
    return records


def load_candidate_adrs(root: Path) -> dict[str, AdrRevision]:
    records: dict[str, AdrRevision] = {}
    for path in sorted((root / "docs" / "decisions").glob("[0-9][0-9][0-9][0-9]-*.md")):
        relative = path.relative_to(root).as_posix()
        if ADR_PATH_RE.fullmatch(relative) is None:
            continue
        record = parse_adr_revision(relative, path.read_bytes())
        if record.adr_id in records:
            raise ValueError(f"duplicate architecture decision ID: {record.adr_id}")
        records[record.adr_id] = record
    return records


def load_base_adrs(root: Path, base_ref: str) -> dict[str, AdrRevision]:
    paths = _git(
        root,
        ["ls-tree", "-r", "--name-only", base_ref, "--", "docs/decisions"],
    ).decode("utf-8").splitlines()
    records: dict[str, AdrRevision] = {}
    for path in sorted(path for path in paths if ADR_PATH_RE.fullmatch(path)):
        record = parse_adr_revision(path, _git(root, ["show", f"{base_ref}:{path}"]))
        if record.adr_id in records:
            raise ValueError(f"duplicate base architecture decision ID: {record.adr_id}")
        records[record.adr_id] = record
    return records


def print_findings(findings: Iterable[LifecycleFinding]) -> None:
    for finding in findings:
        identity = f" ({finding.spec_id})" if finding.spec_id else ""
        print(
            f"[{finding.code}] {finding.path}{identity}: {finding.message}",
            file=sys.stderr,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-ref", required=True, help="exact Git commit or protected base ref")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        base_specs = load_base(root, args.base_ref)
        candidate_specs = load_candidate(root)
        candidate_adrs = load_candidate_adrs(root)
        authority_vocabulary = load_candidate_authority_vocabulary(root, candidate_specs)
        findings = validate_lifecycle(
            base_specs,
            candidate_specs,
            authority_vocabulary=authority_vocabulary,
        )
        findings.extend(
            validate_lifecycle_decision_bindings(
                base_specs,
                candidate_specs,
                candidate_adrs,
            )
        )
        findings.extend(
            validate_adr_lifecycle(
                load_base_adrs(root, args.base_ref),
                candidate_adrs,
            )
        )
        findings = sorted(findings, key=lambda item: (item.path, item.code, item.message))
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"[SPEC_LIFECYCLE_ERROR] {exc}", file=sys.stderr)
        return 1
    if findings:
        print_findings(findings)
        return 1
    print(f"Specification lifecycle check passed against {args.base_ref}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
