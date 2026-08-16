#!/usr/bin/env python3
"""Validate the closed authority vocabulary and policy conformance contract.

This module owns the protected authority-contract surface independently of
specification lifecycle parsing. Lifecycle integration remains in
validate_spec_lifecycle so this module has no dependency on SpecRevision.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, replace
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Any, Iterable, Mapping


__all__ = (
    "AUTHORITY_ACTOR_BINDING_KEYS",
    "AUTHORITY_ACTOR_AUTOMATION",
    "AUTHORITY_ALLOW_REASON_CODE",
    "AUTHORITY_CATALOG_FIXTURE_CASE_KEYS",
    "AUTHORITY_CONFORMANCE_CASE_KEYS",
    "AUTHORITY_CONFORMANCE_POLICY_KEYS",
    "AUTHORITY_CONFORMANCE_RECEIPT_PATH",
    "AUTHORITY_CONFORMANCE_RECEIPT_SCHEMA_VERSION",
    "AUTHORITY_CONFORMANCE_SCOPE",
    "AUTHORITY_CONFORMANCE_VALIDATOR_BUNDLE_KEYS",
    "AUTHORITY_CONFORMANCE_VALIDATOR_COMPONENT_KEYS",
    "AUTHORITY_CONFORMANCE_VALIDATOR_KEYS",
    "AUTHORITY_CONSTITUTION_POLICY_PATH",
    "AUTHORITY_CONSTITUTION_SCHEMA_VERSION",
    "AUTHORITY_DEPENDENCY_EVIDENCE_KEYS",
    "AUTHORITY_DEPENDENCY_REQUIREMENT_KEYS",
    "AUTHORITY_ENTRY_KEYS",
    "AUTHORITY_FIXTURE_CASE_KEYS",
    "AUTHORITY_FIXTURE_ENTRY_KEYS",
    "AUTHORITY_FIXTURE_MANIFEST_PATH",
    "AUTHORITY_FIXTURE_MANIFEST_SCHEMA_VERSION",
    "AUTHORITY_FIXTURE_POINTER_KEYS",
    "AUTHORITY_IMPLEMENTED_STATUSES",
    "AUTHORITY_MAX_EFFECT_KEYS",
    "AUTHORITY_MINIMUM_PROTECTED_SURFACES",
    "AUTHORITY_GRANT_KEYS",
    "AUTHORITY_PREIMPLEMENTATION_STATUSES",
    "AUTHORITY_RUNTIME_AUTHORITY",
    "AUTHORITY_EVALUATOR_BUNDLE_VERSION",
    "AUTHORITY_EVALUATOR_COMPONENT_PATHS",
    "AUTHORITY_VALIDATOR_BUNDLE_ALGORITHM",
    "AUTHORITY_VALIDATOR_PATH",
    "AUTHORITY_VALIDATOR_VERSION",
    "AUTHORITY_VOCABULARY_MIN_REVISION",
    "AUTHORITY_VOCABULARY_PATH",
    "AUTHORITY_VOCABULARY_READY_STATUSES",
    "AUTHORITY_VOCABULARY_SCHEMA_DIGEST",
    "AUTHORITY_VOCABULARY_SCHEMA_VERSION",
    "AUTHORITY_VOCABULARY_SCHEMA_ID",
    "AUTHORITY_VOCABULARY_SCHEMA_PATH",
    "AUTHORITY_SPEC_METADATA_KEYS",
    "AUTHORITY_VOCABULARY_SPEC",
    "AuthorityActorBinding",
    "AuthorityDependencyRequirement",
    "AuthorityFixtureCase",
    "AuthorityFixtureManifestBinding",
    "AuthorityEvaluatorBundleBinding",
    "AuthorityEvaluatorComponentBinding",
    "AuthorityPolicyConformanceBinding",
    "AuthoritySemanticProfile",
    "AuthorityVocabularySchemaBinding",
    "AuthorityVocabularyBinding",
    "POLICY_ONLY_READ_ACTORS",
    "POLICY_ONLY_READ_PROFILES",
    "REQUIRED_AUTHORITY_PROFILES",
    "REQUIRED_AUTHORITY_VOCABULARY_OWNERS",
    "authority_policy_case_results",
    "build_authority_evaluator_bundle",
    "expected_authority_catalog_boundary_cases",
    "expected_authority_dependency_evidence",
    "expected_authority_fixture_cases",
    "expected_authority_policy_conditions",
    "load_authority_vocabulary",
    "load_authority_vocabulary_schema",
    "parse_authority_fixture_manifest",
    "parse_authority_policy_conformance",
    "parse_authority_vocabulary",
    "parse_authority_vocabulary_schema",
    "validate_authority_policy_closure",
)


AUTHORITY_VOCABULARY_SPEC = "SPEC-000"
AUTHORITY_VOCABULARY_MIN_REVISION = 2
AUTHORITY_VOCABULARY_SCHEMA_PATH = "governance/authority-vocabulary.schema.json"
AUTHORITY_VOCABULARY_SCHEMA_ID = (
    "https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/"
    "governance/authority-vocabulary.schema.json"
)
AUTHORITY_VOCABULARY_PATH = "governance/authority-vocabulary.json"
AUTHORITY_VOCABULARY_SCHEMA_DIGEST = (
    "sha256:b4143e94a4beee184af8a22bbadcfd366fe8d9b4efd690e9d8e9b94a5fac76d9"
)
AUTHORITY_VOCABULARY_SCHEMA_VERSION = "2.0.0"
AUTHORITY_FIXTURE_MANIFEST_PATH = "governance/fixtures/authority-vocabulary.json"
AUTHORITY_FIXTURE_MANIFEST_SCHEMA_VERSION = "2.0.0"
AUTHORITY_CONFORMANCE_RECEIPT_PATH = (
    "governance/generated/authority-vocabulary-conformance.json"
)
AUTHORITY_CONFORMANCE_RECEIPT_SCHEMA_VERSION = "3.0.0"
AUTHORITY_CONFORMANCE_SCOPE = "offline_class_policy_conformance"
AUTHORITY_RUNTIME_AUTHORITY = "none"
AUTHORITY_CONSTITUTION_POLICY_PATH = "governance/constitution.yaml"
AUTHORITY_CONSTITUTION_SCHEMA_VERSION = "2.0.0"
AUTHORITY_ALLOW_REASON_CODE = "OFFLINE_CLASS_POLICY_ALLOWED"
AUTHORITY_ACTOR_AUTOMATION = MappingProxyType(
    {
        "attested_supervisor_clock_sampler": True,
        "authenticated_reader": True,
        "authenticated_runtime_operator": True,
        "change_author": True,
        "community_contributor": False,
        "content_exporter": True,
        "content_proposer": True,
        "credential_reconciler": True,
        "human_maintainer": False,
        "independent_canary_attestor": True,
        "independent_epoch_sealer": True,
        "independent_verifier": True,
        "release_attestor": True,
        "repository_acceptance_reconciler": True,
        "research_proposer": True,
        "runtime_operator": True,
        "trusted_clock_reducer": True,
    }
)
AUTHORITY_MINIMUM_PROTECTED_SURFACES = frozenset(
    {
        ".github/CODEOWNERS",
        ".github/workflows/**",
        "governance/**",
        "researcher/benchmarks/**/hidden/**",
        "researcher/rubrics/**",
        "researcher/scripts/build_inventory.py",
        "researcher/scripts/governance_policy.py",
        "researcher/scripts/run_benchmarks.py",
        "researcher/scripts/validate_*.py",
    }
)
_AUTHORITY_EMERGENCY_CONTROLS = MappingProxyType(
    {
        "disable_changes_authority": False,
        "disable_mutates_history": False,
        "disable_stops_new_work": True,
    }
)
_AUTHORITY_AMENDMENT_PROCEDURE = MappingProxyType(
    {
        "prior_versions_retained": True,
        "required_actor": "human_maintainer",
        "required_state_sequence": ("draft", "reviewed", "merged", "effective"),
        "required_transport": "pull_request",
    }
)
# Compatibility constants retained while non-receipt callers migrate to the
# evaluator bundle. Receipt schema 3.0.0 does not consume either value.
AUTHORITY_VALIDATOR_PATH = "researcher/scripts/validate_spec_lifecycle.py"
AUTHORITY_VALIDATOR_VERSION = "1.1.0"
AUTHORITY_VALIDATOR_BUNDLE_ALGORITHM = "sha256-canonical-component-manifest-v1"
AUTHORITY_EVALUATOR_BUNDLE_VERSION = "1.0.0"
AUTHORITY_EVALUATOR_COMPONENT_PATHS = (
    AUTHORITY_VOCABULARY_SCHEMA_PATH,
    "researcher/scripts/governance_policy.py",
    "researcher/scripts/validate_authority_contract.py",
)
_AUTHORITY_EVALUATOR_EXECUTABLE_COMPONENT_PATHS = (
    "researcher/scripts/governance_policy.py",
    "researcher/scripts/validate_authority_contract.py",
)
AUTHORITY_VOCABULARY_READY_STATUSES = frozenset(
    {
        "accepted",
        "implemented",
        "verified",
        "operational",
    }
)
_AUTHORITY_DEPENDENCY_EVIDENCE_STAGES = frozenset(
    {
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
)
AUTHORITY_IMPLEMENTED_STATUSES = frozenset(
    {"implemented", "verified", "operational"}
)
AUTHORITY_PREIMPLEMENTATION_STATUSES = frozenset(
    {
        "draft",
        "architecture_reviewed",
        "accepted",
    }
)
AUTHORITY_ENTRY_KEYS = frozenset(
    {
        "action",
        "resource",
        "owner_spec",
        "actor_bindings",
        "max_effect",
        "dependency_requirements",
        "grant_operation",
    }
)
AUTHORITY_ACTOR_BINDING_KEYS = frozenset({"actor_class", "predicates"})
AUTHORITY_DEPENDENCY_REQUIREMENT_KEYS = frozenset(
    {
        "spec_id",
        "revision",
        "minimum_runtime_stage",
    }
)
AUTHORITY_MAX_EFFECT_KEYS = frozenset(
    {
        "code",
        "max_targets",
        "max_state_transitions",
    }
)
AUTHORITY_FIXTURE_POINTER_KEYS = frozenset({"path", "digest", "version"})
AUTHORITY_FIXTURE_ENTRY_KEYS = frozenset({"action", "resource", "cases"})
AUTHORITY_FIXTURE_CASE_KEYS = frozenset(
    {
        "case",
        "evidence_kind",
        "actor_class",
        "context",
        "effect",
        "grant",
        "dependencies",
        "expected_decision",
        "expected_policy_decision",
        "expected_registry_decision",
    }
)
AUTHORITY_CATALOG_FIXTURE_CASE_KEYS = AUTHORITY_FIXTURE_CASE_KEYS | frozenset(
    {"action", "resource"}
)
AUTHORITY_DEPENDENCY_EVIDENCE_KEYS = frozenset(
    {"spec_id", "revision", "runtime_stage"}
)
AUTHORITY_GRANT_KEYS = frozenset({"operation", "effect"})
AUTHORITY_SPEC_METADATA_KEYS = frozenset(
    {
        "Authority vocabulary schema",
        "Authority vocabulary schema digest",
        "Authority vocabulary schema version",
        "Authority vocabulary",
        "Authority vocabulary digest",
        "Authority vocabulary version",
    }
)
AUTHORITY_CONFORMANCE_POLICY_KEYS = frozenset({"path", "digest", "version"})
AUTHORITY_CONFORMANCE_VALIDATOR_BUNDLE_KEYS = frozenset(
    {
        "algorithm",
        "components",
        "digest",
        "version",
    }
)
AUTHORITY_CONFORMANCE_VALIDATOR_COMPONENT_KEYS = frozenset({"path", "digest"})
# Compatibility import name; schema 2.0.0 binds the complete bundle shape.
AUTHORITY_CONFORMANCE_VALIDATOR_KEYS = AUTHORITY_CONFORMANCE_VALIDATOR_BUNDLE_KEYS
AUTHORITY_CONFORMANCE_CASE_KEYS = frozenset(
    {
        "action",
        "resource",
        "case",
        "expected_decision",
        "expected_policy_decision",
        "expected_registry_decision",
        "expected_registry_reason_code",
        "registry_decision",
        "registry_reason_code",
        "policy_decision",
        "actual_decision",
        "context_digest",
        "matched_rule",
        "reason_code",
    }
)


@dataclass(frozen=True)
class AuthorityDependencyRequirement:
    """One exact, operational dependency identity required by a catalog entry."""

    spec_id: str
    revision: int
    minimum_runtime_stage: str = "operational"

    def to_payload(self) -> dict[str, object]:
        return {
            "minimum_runtime_stage": self.minimum_runtime_stage,
            "revision": self.revision,
            "spec_id": self.spec_id,
        }


@dataclass(frozen=True)
class AuthorityActorBinding:
    """One actor class and its non-transferable typed policy predicates."""

    actor_class: str
    predicates: tuple[dict[str, object], ...]

    def to_payload(self) -> dict[str, object]:
        return {
            "actor_class": self.actor_class,
            "predicates": [dict(predicate) for predicate in self.predicates],
        }


_BOOLEAN_TRUE_CONTEXT_FIELDS = frozenset(
    {
        "accepted_pointer_absent",
        "authenticated",
        "automated_identity_disclosed",
        "candidate_digest_verified",
        "capability_grant_valid",
        "independent_of_author",
        "latest_commit_reviewed",
        "required_checks_passed",
    }
)
_INTEGER_CONTEXT_FIELDS = frozenset(
    {
        "activation_epoch",
        "budget_ceiling",
        "canary_epoch",
        "expected_accepted_pointer_version",
        "expected_deployment_version",
        "expected_target_version",
        "organization_epoch",
        "safety_ledger_version",
        "split_and_look_ceiling",
    }
)
_UTC_DATETIME_CONTEXT_FIELDS = frozenset({"break_glass_expiry", "deadline"})


def _authority_predicate(key: str) -> dict[str, object]:
    if key in _BOOLEAN_TRUE_CONTEXT_FIELDS:
        return {
            "key": key,
            "operator": "equals",
            "value": True,
            "value_type": "boolean",
        }
    if key == "human_review_path":
        return {
            "key": key,
            "operator": "equals",
            "value": "pull_request",
            "value_type": "string",
        }
    if key.endswith("_digest"):
        value_type = "sha256_digest"
    elif key in _INTEGER_CONTEXT_FIELDS:
        value_type = "integer"
    elif key in _UTC_DATETIME_CONTEXT_FIELDS:
        value_type = "utc_datetime"
    else:
        value_type = "string"
    return {"key": key, "operator": "present", "value_type": value_type}


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
    action: str = ""
    resource: str = ""

    @property
    def max_effect(self) -> dict[str, object]:
        return {
            "code": self.max_effect_code,
            "max_state_transitions": self.max_state_transitions,
            "max_targets": self.max_targets,
        }

    @property
    def dependency_requirements(self) -> tuple[AuthorityDependencyRequirement, ...]:
        required: dict[str, int] = {AUTHORITY_VOCABULARY_SPEC: 2}
        for binding in self.dependency_floor:
            spec_id, revision_text = binding.split("@", maxsplit=1)
            required[spec_id] = int(revision_text)
        required.setdefault(self.owner_spec, 1)
        if self.owner_spec == AUTHORITY_VOCABULARY_SPEC:
            required[self.owner_spec] = AUTHORITY_VOCABULARY_MIN_REVISION
        return tuple(
            AuthorityDependencyRequirement(spec_id=spec_id, revision=revision)
            for spec_id, revision in sorted(required.items())
        )

    @property
    def actor_bindings(self) -> tuple[AuthorityActorBinding, ...]:
        bindings: list[AuthorityActorBinding] = []
        for actor_class in self.actor_classes:
            fields = set(self.decision_context_fields)
            guard_override = _REV1_ACTOR_GUARD_OVERRIDES.get(
                (self.action, self.resource, actor_class)
            )
            if guard_override is not None:
                fields.difference_update(_REV1_ACTOR_GUARD_FIELDS)
                fields.update(guard_override)
            else:
                if actor_class == "human_maintainer":
                    fields.add("authenticated")
                if actor_class.startswith("authenticated_"):
                    fields.add("authenticated")
            predicates = tuple(
                _authority_predicate(field) for field in sorted(fields)
            )
            bindings.append(
                AuthorityActorBinding(
                    actor_class=actor_class,
                    predicates=predicates,
                )
            )
        return tuple(sorted(bindings, key=lambda binding: binding.actor_class))

    def actor_binding(self, actor_class: str) -> AuthorityActorBinding:
        for binding in self.actor_bindings:
            if binding.actor_class == actor_class:
                return binding
        raise KeyError(actor_class)


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
REQUIRED_AUTHORITY_PROFILES: Mapping[tuple[str, str], AuthoritySemanticProfile] = {
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
        (
            "change_author",
            "community_contributor",
            "human_maintainer",
            "research_proposer",
        ),
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
        (
            "change_author",
            "community_contributor",
            "human_maintainer",
            "research_proposer",
        ),
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


_REV1_ACTOR_GUARD_FIELDS = frozenset(
    {
        "authenticated",
        "automated_identity_disclosed",
        "candidate_digest_verified",
        "capability_grant_valid",
        "human_review_path",
        "independent_of_author",
        "latest_commit_reviewed",
        "required_checks_passed",
    }
)
_REV1_ACTOR_GUARD_OVERRIDES: dict[tuple[str, str, str], frozenset[str]] = {}


def _bind_rev1_guards(
    pairs: Iterable[tuple[str, str]],
    actors: Iterable[str],
    *guards: str,
) -> None:
    for action, resource in pairs:
        for actor in actors:
            _REV1_ACTOR_GUARD_OVERRIDES[(action, resource, actor)] = frozenset(guards)


_bind_rev1_guards(
    {
        ("read", "candidate_artifact"),
        ("read", "public_content_draft"),
        ("read", "public_repository"),
        ("read", "pull_request"),
        ("read", "research_artifact"),
    },
    POLICY_ONLY_READ_ACTORS,
)
_bind_rev1_guards(
    {
        ("research", "candidate_artifact"),
        ("research", "research_artifact"),
        ("propose_change", "research_artifact"),
    },
    {"research_proposer"},
    "automated_identity_disclosed",
)
_bind_rev1_guards(
    {
        ("research", "candidate_artifact"),
        ("research", "research_artifact"),
        ("propose_change", "research_artifact"),
    },
    {"human_maintainer"},
    "authenticated",
)
_bind_rev1_guards(
    {("propose_change", "candidate_artifact")},
    {"change_author", "research_proposer"},
    "automated_identity_disclosed",
)
_bind_rev1_guards(
    {("propose_change", "candidate_artifact")},
    {"community_contributor"},
    "human_review_path",
)
_bind_rev1_guards(
    {("propose_change", "candidate_artifact")},
    {"human_maintainer"},
    "authenticated",
)
_bind_rev1_guards(
    {
        ("open_pull_request", "pull_request"),
        ("push_proposal", "proposal_branch"),
        ("respond_to_review", "pull_request"),
    },
    {"change_author", "research_proposer"},
    "automated_identity_disclosed",
    "human_review_path",
)
_bind_rev1_guards(
    {
        ("open_pull_request", "pull_request"),
        ("respond_to_review", "pull_request"),
    },
    {"community_contributor"},
    "human_review_path",
)
_bind_rev1_guards(
    {
        ("open_pull_request", "pull_request"),
        ("push_proposal", "proposal_branch"),
        ("respond_to_review", "pull_request"),
    },
    {"human_maintainer"},
    "authenticated",
)
_bind_rev1_guards(
    {("evaluate", "candidate_artifact"), ("evaluate", "research_artifact")},
    {"independent_verifier"},
    "independent_of_author",
)
_bind_rev1_guards(
    {("attest_release", "candidate_artifact"), ("attest_release", "pull_request")},
    {"release_attestor"},
    "candidate_digest_verified",
    "independent_of_author",
)
_bind_rev1_guards(
    {("execute_work", "candidate_artifact"), ("execute_work", "research_artifact")},
    {"runtime_operator"},
    "capability_grant_valid",
)
_bind_rev1_guards(
    {("emergency_disable", "emergency_control")},
    {"human_maintainer", "runtime_operator"},
)
_bind_rev1_guards(
    {("merge", "default_branch"), ("merge", "pull_request")},
    {"human_maintainer"},
    "authenticated",
    "latest_commit_reviewed",
    "required_checks_passed",
)
_bind_rev1_guards(
    {("activate_production", "production_deployment")},
    {"human_maintainer"},
    "authenticated",
    "latest_commit_reviewed",
    "required_checks_passed",
)
_bind_rev1_guards(
    {
        ("amend_constitution", "constitution"),
        ("change_protected_surface", "evaluator_policy"),
        ("change_protected_surface", "hidden_evaluation"),
        ("change_protected_surface", "protected_surface"),
        ("change_protected_surface", "public_private_boundary"),
    },
    {"human_maintainer"},
    "authenticated",
    "human_review_path",
)
_bind_rev1_guards(
    {
        ("approve_weight_training", "weight_training"),
        ("authorize_credential_destination", "credential_destination"),
        ("expose_private_record", "private_record"),
    },
    {"human_maintainer"},
    "authenticated",
)

_REV1_ACTOR_GUARD_OVERRIDES = MappingProxyType(
    dict(_REV1_ACTOR_GUARD_OVERRIDES)
)

POLICY_ONLY_READ_PROFILES = MappingProxyType(
    {
        pair: replace(profile, action=pair[0], resource=pair[1])
        for pair, profile in POLICY_ONLY_READ_PROFILES.items()
    }
)
REQUIRED_AUTHORITY_PROFILES = MappingProxyType(
    {
        pair: replace(profile, action=pair[0], resource=pair[1])
        for pair, profile in REQUIRED_AUTHORITY_PROFILES.items()
    }
)

REQUIRED_AUTHORITY_VOCABULARY_OWNERS = MappingProxyType(
    {
        pair: profile.owner_spec
        for pair, profile in REQUIRED_AUTHORITY_PROFILES.items()
    }
)


@dataclass(frozen=True)
class AuthorityFixtureCase:
    action: str
    resource: str
    case: str
    evidence_kind: str
    actor_class: str
    context: Mapping[str, object]
    effect_code: str
    max_targets: int
    max_state_transitions: int
    grant_effect_code: str
    grant_max_targets: int
    grant_max_state_transitions: int
    expected_decision: str
    expected_policy_decision: str
    expected_registry_decision: str
    expected_registry_reason_code: str
    grant_operation: str
    dependencies: tuple[tuple[str, int, str], ...]

    @property
    def effect(self) -> dict[str, object]:
        return {
            "code": self.effect_code,
            "max_state_transitions": self.max_state_transitions,
            "max_targets": self.max_targets,
        }

    @property
    def grant(self) -> dict[str, object]:
        return {
            "effect": {
                "code": self.grant_effect_code,
                "max_state_transitions": self.grant_max_state_transitions,
                "max_targets": self.grant_max_targets,
            },
            "operation": self.grant_operation,
        }

    @property
    def decision_context_fields(self) -> tuple[str, ...]:
        """Compatibility view; decisions use the actual scalar context."""

        return tuple(sorted(self.context))

    @property
    def dependency_evidence(self) -> tuple[tuple[str, int, str], ...]:
        """Compatibility view for callers migrating to `dependencies`."""

        return self.dependencies


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
class AuthorityEvaluatorComponentBinding:
    path: str
    digest: str

    def to_payload(self) -> dict[str, str]:
        return {"path": self.path, "digest": self.digest}


@dataclass(frozen=True)
class AuthorityEvaluatorBundleBinding:
    algorithm: str
    version: str
    components: tuple[AuthorityEvaluatorComponentBinding, ...]
    digest: str

    def to_payload(self) -> dict[str, object]:
        """Return the aggregate-digest input manifest."""

        return {
            "algorithm": self.algorithm,
            "version": self.version,
            "components": [component.to_payload() for component in self.components],
        }

    def to_receipt_value(self) -> dict[str, object]:
        """Return the closed receipt value, including the aggregate digest."""

        return {**self.to_payload(), "digest": self.digest}


@dataclass(frozen=True)
class AuthorityPolicyConformanceBinding:
    path: str
    digest: str
    schema_version: str
    scope: str
    runtime_authority: str
    constitution_policy_digest: str
    registry_digest: str
    fixture_manifest_digest: str
    validator_bundle_algorithm: str
    validator_bundle_digest: str
    validator_bundle_version: str
    validator_bundle_components: tuple[AuthorityEvaluatorComponentBinding, ...]
    case_count: int


@dataclass(frozen=True)
class AuthorityVocabularySchemaBinding:
    path: str
    digest: str
    schema_id: str
    schema_version: str


@dataclass(frozen=True)
class AuthorityVocabularyBinding:
    schema_path: str
    schema_digest: str
    schema_version: str
    path: str
    digest: str
    registry_schema_version: str
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

    @property
    def policy_conformance_scope(self) -> str | None:
        if self.policy_conformance is None:
            return None
        return self.policy_conformance.scope

    @property
    def policy_conformance_runtime_authority(self) -> str | None:
        if self.policy_conformance is None:
            return None
        return self.policy_conformance.runtime_authority


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
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")


def _exact_authority_value_equal(actual: object, expected: object) -> bool:
    """Compare validated JSON-like values without Python's bool/int aliasing."""

    if type(actual) is not type(expected):
        return False
    if isinstance(actual, dict) and isinstance(expected, dict):
        return set(actual) == set(expected) and all(
            _exact_authority_value_equal(actual[key], expected[key])
            for key in expected
        )
    if isinstance(actual, (list, tuple)) and isinstance(expected, (list, tuple)):
        return len(actual) == len(expected) and all(
            _exact_authority_value_equal(actual_item, expected_item)
            for actual_item, expected_item in zip(actual, expected, strict=True)
        )
    try:
        result = actual == expected
    except Exception:
        return False
    return type(result) is bool and result


def parse_authority_vocabulary_schema(
    exact_bytes: bytes,
    *,
    expected_digest: str,
    expected_version: str = AUTHORITY_VOCABULARY_SCHEMA_VERSION,
) -> AuthorityVocabularySchemaBinding:
    """Bind the exact canonical schema before any registry bytes are trusted."""

    if re.fullmatch(r"sha256:[0-9a-f]{64}", expected_digest) is None:
        raise ValueError(
            "authority vocabulary schema digest must be sha256:<64 lowercase hex>"
        )
    if expected_version != AUTHORITY_VOCABULARY_SCHEMA_VERSION:
        raise ValueError(
            "authority vocabulary schema version must be "
            f"{AUTHORITY_VOCABULARY_SCHEMA_VERSION}"
        )
    actual_digest = f"sha256:{hashlib.sha256(exact_bytes).hexdigest()}"
    if actual_digest != expected_digest:
        raise ValueError(
            "authority vocabulary schema digest mismatch: expected "
            f"{expected_digest}, got {actual_digest}"
        )
    data = _strict_json_loads(exact_bytes, label="authority vocabulary schema")
    if not isinstance(data, dict):
        raise ValueError("authority vocabulary schema root must be an object")
    root_keys = {
        "$defs",
        "$id",
        "$schema",
        "oneOf",
        "title",
        "x-authority-schema-version",
    }
    if set(data) != root_keys:
        raise ValueError(
            "authority vocabulary schema root fields do not match the closed identity"
        )
    if data["$schema"] != "https://json-schema.org/draft/2020-12/schema":
        raise ValueError("authority vocabulary schema dialect is invalid")
    if data["$id"] != AUTHORITY_VOCABULARY_SCHEMA_ID:
        raise ValueError("authority vocabulary schema $id is invalid")
    if data["x-authority-schema-version"] != AUTHORITY_VOCABULARY_SCHEMA_VERSION:
        raise ValueError("authority vocabulary schema marker is invalid")
    if (
        data["title"]
        != "Authority vocabulary registry and synthetic offline fixtures 2.0.0"
    ):
        raise ValueError("authority vocabulary schema title is invalid")
    if not _exact_authority_value_equal(
        data["oneOf"],
        [
            {"$ref": "#/$defs/fixtureManifest"},
            {"$ref": "#/$defs/registry"},
        ],
    ):
        raise ValueError("authority vocabulary schema root alternatives are invalid")
    definitions = data["$defs"]
    if not isinstance(definitions, dict) or not {
        "fixtureManifest",
        "registry",
    }.issubset(definitions):
        raise ValueError("authority vocabulary schema definitions are incomplete")
    if actual_digest != AUTHORITY_VOCABULARY_SCHEMA_DIGEST:
        raise ValueError(
            "authority vocabulary schema bytes do not match the code-pinned "
            f"schema 2.0.0 digest {AUTHORITY_VOCABULARY_SCHEMA_DIGEST}"
        )
    if exact_bytes != _canonical_json_bytes(data):
        raise ValueError(
            "authority vocabulary schema must use canonical sorted pretty serialization"
        )
    return AuthorityVocabularySchemaBinding(
        path=AUTHORITY_VOCABULARY_SCHEMA_PATH,
        digest=actual_digest,
        schema_id=AUTHORITY_VOCABULARY_SCHEMA_ID,
        schema_version=AUTHORITY_VOCABULARY_SCHEMA_VERSION,
    )


def load_authority_vocabulary_schema(
    root: Path,
    *,
    expected_digest: str | None = None,
    expected_version: str = AUTHORITY_VOCABULARY_SCHEMA_VERSION,
) -> AuthorityVocabularySchemaBinding:
    """Load and directly validate the canonical authority schema."""

    exact_bytes = read_canonical_repository_file(
        root,
        AUTHORITY_VOCABULARY_SCHEMA_PATH,
        label="authority vocabulary schema",
    )
    digest = expected_digest or f"sha256:{hashlib.sha256(exact_bytes).hexdigest()}"
    return parse_authority_vocabulary_schema(
        exact_bytes,
        expected_digest=digest,
        expected_version=expected_version,
    )


def read_canonical_repository_file(
    root: Path,
    relative_path: str,
    *,
    label: str,
) -> bytes:
    """Read one exact in-root file without accepting lexical symlink aliases."""

    root = Path(root)
    if type(relative_path) is not str or not relative_path:
        raise ValueError(f"{label} path must be a canonical repository-relative path")
    pure_path = PurePosixPath(relative_path)
    if (
        pure_path.is_absolute()
        or pure_path.as_posix() != relative_path
        or any(part in {"", ".", ".."} for part in pure_path.parts)
    ):
        raise ValueError(f"{label} path must be a canonical repository-relative path")
    if root.is_symlink() or not root.is_dir():
        raise ValueError(f"{label} repository root must be a regular directory")
    try:
        resolved_root = root.resolve(strict=True)
    except OSError as exc:
        raise ValueError(f"{label} repository root cannot be resolved: {exc}") from exc

    current = root
    for part in pure_path.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(
                f"{label} must be a regular canonical repository file "
                "without symlink ancestors"
            )
    if not current.is_file():
        raise ValueError(f"{label} must be a regular canonical repository file")
    try:
        resolved = current.resolve(strict=True)
        resolved.relative_to(resolved_root)
    except (OSError, ValueError) as exc:
        raise ValueError(f"{label} must resolve inside the repository root") from exc
    return current.read_bytes()


def canonical_repository_output_path(
    root: Path,
    relative_path: str,
    *,
    label: str,
) -> Path:
    """Validate an in-root output path before any directory or file creation."""

    root = Path(root)
    if type(relative_path) is not str or not relative_path:
        raise ValueError(f"{label} path must be a canonical repository-relative path")
    pure_path = PurePosixPath(relative_path)
    if (
        pure_path.is_absolute()
        or pure_path.as_posix() != relative_path
        or any(part in {"", ".", ".."} for part in pure_path.parts)
    ):
        raise ValueError(f"{label} path must be a canonical repository-relative path")
    if root.is_symlink() or not root.is_dir():
        raise ValueError(f"{label} repository root must be a regular directory")
    resolved_root = root.resolve(strict=True)
    current = root
    for part in pure_path.parts[:-1]:
        current = current / part
        if current.is_symlink():
            raise ValueError(
                f"{label} must not have a symlink ancestor in the repository"
            )
        if current.exists():
            if not current.is_dir():
                raise ValueError(f"{label} parent must be a directory")
            try:
                current.resolve(strict=True).relative_to(resolved_root)
            except (OSError, ValueError) as exc:
                raise ValueError(
                    f"{label} parent must resolve inside the repository root"
                ) from exc
    target = root / relative_path
    if target.is_symlink() or (target.exists() and not target.is_file()):
        raise ValueError(f"{label} must be a regular canonical repository file")
    return target


def _governance_policy_module() -> Any:
    if __package__:
        from researcher.scripts import governance_policy
    else:  # Direct script execution resolves the sibling from this script's directory.
        import governance_policy
    return governance_policy


def authority_evaluator_runtime_component_bytes() -> tuple[tuple[str, bytes], ...]:
    """Return executable component bytes; the target root supplies schema bytes."""

    root = Path(__file__).resolve().parents[2]
    governance_policy = _governance_policy_module()
    governance_source = getattr(governance_policy, "__file__", None)
    if type(governance_source) is not str:
        raise ValueError("executing governance policy has no canonical source file")
    module_paths = {
        "researcher/scripts/governance_policy.py": Path(governance_source),
        "researcher/scripts/validate_authority_contract.py": Path(__file__),
    }
    components: list[tuple[str, bytes]] = []
    for relative_path in _AUTHORITY_EVALUATOR_EXECUTABLE_COMPONENT_PATHS:
        expected_path = (root / relative_path).resolve(strict=True)
        if module_paths[relative_path].resolve(strict=True) != expected_path:
            raise ValueError(
                "executing authority evaluator module does not originate from its "
                f"canonical source path: {relative_path}"
            )
        components.append(
            (
                relative_path,
                read_canonical_repository_file(
                    root,
                    relative_path,
                    label="executing authority evaluator component",
                ),
            )
        )
    return tuple(components)


def build_authority_evaluator_bundle(
    component_bytes: Mapping[str, bytes] | Iterable[tuple[str, bytes]],
) -> AuthorityEvaluatorBundleBinding:
    """Bind the exact evaluator components in canonical path order."""

    entries = (
        tuple(component_bytes.items())
        if isinstance(component_bytes, Mapping)
        else tuple(component_bytes)
    )
    if any(not isinstance(entry, tuple) or len(entry) != 2 for entry in entries):
        raise ValueError("authority evaluator components must be path/bytes pairs")
    paths = tuple(entry[0] for entry in entries)
    if any(type(path) is not str for path in paths):
        raise ValueError("authority evaluator component paths must be strings")
    if len(paths) != len(set(paths)):
        raise ValueError("authority evaluator component paths must be unique")
    if set(paths) != set(AUTHORITY_EVALUATOR_COMPONENT_PATHS):
        raise ValueError(
            "authority evaluator components must match the exact canonical path set"
        )
    if any(type(exact_bytes) is not bytes for _path, exact_bytes in entries):
        raise ValueError("authority evaluator component values must be exact bytes")
    entries = tuple(sorted(entries, key=lambda entry: entry[0]))

    components = tuple(
        AuthorityEvaluatorComponentBinding(
            path=path,
            digest=f"sha256:{hashlib.sha256(exact_bytes).hexdigest()}",
        )
        for path, exact_bytes in entries
    )
    payload = {
        "algorithm": AUTHORITY_VALIDATOR_BUNDLE_ALGORITHM,
        "version": AUTHORITY_EVALUATOR_BUNDLE_VERSION,
        "components": [component.to_payload() for component in components],
    }
    return AuthorityEvaluatorBundleBinding(
        algorithm=AUTHORITY_VALIDATOR_BUNDLE_ALGORITHM,
        version=AUTHORITY_EVALUATOR_BUNDLE_VERSION,
        components=components,
        digest=f"sha256:{hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()}",
    )


def expected_authority_dependency_evidence(
    profile: AuthoritySemanticProfile,
) -> list[dict[str, object]]:
    return [
        {
            "spec_id": requirement.spec_id,
            "revision": requirement.revision,
            "runtime_stage": "operational",
        }
        for requirement in profile.dependency_requirements
    ]


def _sample_context(binding: AuthorityActorBinding) -> dict[str, object]:
    context: dict[str, object] = {}
    for predicate in binding.predicates:
        key = str(predicate["key"])
        if predicate["operator"] == "equals":
            context[key] = predicate["value"]
        elif predicate["value_type"] == "sha256_digest":
            context[key] = f"sha256:{hashlib.sha256(key.encode()).hexdigest()}"
        elif predicate["value_type"] == "integer":
            context[key] = 1
        elif predicate["value_type"] == "utc_datetime":
            context[key] = "2030-01-01T00:00:00Z"
        elif predicate["value_type"] == "string":
            context[key] = f"synthetic_{key}"
        else:  # Defensive: profiles must use only policy schema-v2 value types.
            raise RuntimeError(f"unsupported authority predicate value type for {key}")
    return context


def _wrong_scalar_for_predicate(predicate: Mapping[str, object]) -> object:
    value_type = predicate["value_type"]
    if value_type in {"string", "sha256_digest", "utc_datetime"}:
        return 7
    return "wrong_type"


def expected_authority_fixture_cases(
    profile: AuthoritySemanticProfile,
) -> tuple[dict[str, object], ...]:
    """Return the exhaustive actor, guard, dependency, effect, and grant cases."""

    allowed_binding = profile.actor_bindings[0]
    exact_effect = profile.max_effect
    dependency_evidence = expected_authority_dependency_evidence(profile)
    common: dict[str, object] = {
        "evidence_kind": "synthetic_offline",
        "actor_class": allowed_binding.actor_class,
        "context": _sample_context(allowed_binding),
        "effect": exact_effect,
        "grant": {"operation": profile.grant_operation, "effect": exact_effect},
        "dependencies": dependency_evidence,
        "expected_decision": "deny",
        "expected_policy_decision": "deny",
        "expected_registry_decision": "deny",
    }

    cases: list[dict[str, object]] = []
    for binding in profile.actor_bindings:
        valid_context = _sample_context(binding)
        cases.append(
            dict(
                common,
                case=f"allow__{binding.actor_class}",
                actor_class=binding.actor_class,
                context=valid_context,
                expected_decision="allow",
                expected_policy_decision="allow",
                expected_registry_decision="allow",
            )
        )
        for predicate in binding.predicates:
            key = str(predicate["key"])
            missing_context = dict(valid_context)
            del missing_context[key]
            cases.append(
                dict(
                    common,
                    case=f"missing_guard__{binding.actor_class}__{key}",
                    actor_class=binding.actor_class,
                    context=missing_context,
                )
            )
        representative = binding.predicates[0]
        representative_key = str(representative["key"])
        wrong_type_context = dict(valid_context)
        wrong_type_context[representative_key] = _wrong_scalar_for_predicate(
            representative
        )
        cases.append(
            dict(
                common,
                case=f"wrong_type_guard__{binding.actor_class}",
                actor_class=binding.actor_class,
                context=wrong_type_context,
            )
        )
        boolean_predicate = next(
            (
                predicate
                for predicate in binding.predicates
                if predicate["value_type"] == "boolean"
            ),
            None,
        )
        if boolean_predicate is not None:
            false_context = dict(valid_context)
            false_context[str(boolean_predicate["key"])] = False
            cases.append(
                dict(
                    common,
                    case=f"false_guard__{binding.actor_class}",
                    actor_class=binding.actor_class,
                    context=false_context,
                )
            )
        string_predicate = next(
            (
                predicate
                for predicate in binding.predicates
                if predicate["value_type"] in {"string", "utc_datetime"}
            ),
            None,
        )
        if string_predicate is not None:
            empty_context = dict(valid_context)
            empty_context[str(string_predicate["key"])] = ""
            cases.append(
                dict(
                    common,
                    case=f"empty_guard__{binding.actor_class}",
                    actor_class=binding.actor_class,
                    context=empty_context,
                )
            )
        digest_predicate = next(
            (
                predicate
                for predicate in binding.predicates
                if predicate["value_type"] == "sha256_digest"
            ),
            None,
        )
        if digest_predicate is not None:
            malformed_context = dict(valid_context)
            malformed_context[str(digest_predicate["key"])] = "sha256:not-a-digest"
            cases.append(
                dict(
                    common,
                    case=f"malformed_digest_guard__{binding.actor_class}",
                    actor_class=binding.actor_class,
                    context=malformed_context,
                )
            )

    extra_context = _sample_context(allowed_binding)
    extra_context["unreviewed_context"] = "synthetic_unreviewed_context"
    cases.append(
        dict(
            common,
            case="extra_context_field",
            context=dict(sorted(extra_context.items())),
            expected_policy_decision="allow",
        )
    )

    dependency_mutations: dict[str, list[dict[str, object]]] = {}
    lower = [dict(item) for item in dependency_evidence]
    lower[0]["revision"] = int(lower[0]["revision"]) - 1
    dependency_mutations["dependency_lower_revision"] = lower
    higher = [dict(item) for item in dependency_evidence]
    higher[0]["revision"] = int(higher[0]["revision"]) + 1
    dependency_mutations["dependency_higher_revision"] = higher
    accepted = [dict(item) for item in dependency_evidence]
    accepted[0]["runtime_stage"] = "accepted"
    dependency_mutations["dependency_accepted_stage"] = accepted
    terminal = [dict(item) for item in dependency_evidence]
    terminal[0]["runtime_stage"] = "superseded"
    dependency_mutations["dependency_terminal_stage"] = terminal
    dependency_mutations["dependency_missing"] = [
        dict(item) for item in dependency_evidence[1:]
    ]
    extra = [dict(item) for item in dependency_evidence]
    extra.append(
        {"spec_id": "SPEC-999", "revision": 1, "runtime_stage": "operational"}
    )
    dependency_mutations["dependency_extra"] = extra
    for case_name, dependencies in dependency_mutations.items():
        cases.append(dict(common, case=case_name, dependencies=dependencies))

    narrow_effect = {
        "code": profile.max_effect_code,
        "max_state_transitions": 0,
        "max_targets": 0,
    }
    cases.append(
        dict(
            common,
            case="narrowed_effect",
            effect=narrow_effect,
            expected_decision="allow",
            expected_policy_decision="allow",
            expected_registry_decision="allow",
        )
    )
    widened_targets = dict(exact_effect)
    widened_targets["max_targets"] = profile.max_targets + 1
    cases.append(dict(common, case="widened_effect_targets", effect=widened_targets))
    widened_transitions = dict(exact_effect)
    widened_transitions["max_state_transitions"] = (
        profile.max_state_transitions + 1
    )
    cases.append(
        dict(common, case="widened_effect_transitions", effect=widened_transitions)
    )
    mixed_effect = dict(narrow_effect)
    mixed_effect["max_state_transitions"] = profile.max_state_transitions + 1
    cases.append(dict(common, case="mixed_effect_widening", effect=mixed_effect))
    cases.append(
        dict(
            common,
            case="wrong_effect_code",
            effect={
                "code": "unbounded_effect",
                "max_state_transitions": profile.max_state_transitions,
                "max_targets": profile.max_targets,
            },
        )
    )
    cases.append(
        dict(
            common,
            case="wrong_actor",
            actor_class="unauthorized_actor",
        )
    )
    wrong_operation_grant = {
        "operation": "unauthorized_operation",
        "effect": exact_effect,
    }
    cases.append(
        dict(common, case="wrong_grant_operation", grant=wrong_operation_grant)
    )
    narrow_grant_effect = dict(exact_effect)
    narrow_grant_effect["max_targets"] = max(0, profile.max_targets - 1)
    cases.append(
        dict(
            common,
            case="grant_too_narrow",
            grant={
                "operation": profile.grant_operation,
                "effect": narrow_grant_effect,
            },
        )
    )
    cases.append(
        dict(
            common,
            case="grant_effect_code_mismatch",
            grant={
                "operation": profile.grant_operation,
                "effect": {
                    "code": "unbounded_effect",
                    "max_state_transitions": profile.max_state_transitions,
                    "max_targets": profile.max_targets,
                },
            },
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
    if (
        unknown_pair["action"],
        unknown_pair["resource"],
    ) in REQUIRED_AUTHORITY_PROFILES:
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
        dependencies=[
            {
                "spec_id": "SPEC-000",
                "revision": 2,
                "runtime_stage": "operational",
            }
        ],
    )
    read_cases: list[dict[str, object]] = []
    for (read_action, read_resource), read_profile in sorted(
        POLICY_ONLY_READ_PROFILES.items()
    ):
        profile_cases = expected_authority_fixture_cases(read_profile)
        for profile_case in profile_cases:
            is_allow = profile_case["expected_registry_decision"] == "allow"
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
            case for case in profile_cases if case["case"] == "allow__human_maintainer"
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
                grant={
                    "operation": "append_organization_event",
                    "effect": {
                        "code": "append_one_organization_event",
                        "max_state_transitions": 1,
                        "max_targets": 1,
                    },
                },
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
        grant={
            "operation": "append_organization_event",
            "effect": {
                "code": "append_one_organization_event",
                "max_state_transitions": 1,
                "max_targets": 1,
            },
        },
        expected_decision="deny",
        expected_policy_decision="deny",
        expected_registry_decision="deny",
        dependencies=[
            {
                "spec_id": "SPEC-000",
                "revision": 2,
                "runtime_stage": "operational",
            }
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


def _expected_registry_reason_code(
    case_name: str,
    expected_registry_decision: str,
) -> str:
    """Bind each canonical fixture name to its reviewed registry branch."""

    if expected_registry_decision == "allow":
        return "REGISTRY_ALLOW"
    if expected_registry_decision == "non_event":
        return "REGISTRY_POLICY_ONLY_READ"
    segments = case_name.split("__")
    if any(segment == "wrong_actor" for segment in segments):
        return "REGISTRY_ACTOR_DENY"
    if any(
        segment == "extra_context_field"
        or segment.startswith(
            (
                "empty_guard",
                "false_guard",
                "malformed_digest_guard",
                "missing_guard",
                "wrong_type_guard",
            )
        )
        for segment in segments
    ):
        return "REGISTRY_GUARD_DENY"
    if any(
        segment
        in {
            "event_append_denied",
            "mixed_effect_widening",
            "widened_effect_targets",
            "widened_effect_transitions",
            "wrong_effect_code",
        }
        for segment in segments
    ):
        return "REGISTRY_EFFECT_DENY"
    if any(
        segment
        in {
            "grant_effect_code_mismatch",
            "grant_too_narrow",
            "wrong_grant_operation",
        }
        for segment in segments
    ):
        return "REGISTRY_GRANT_DENY"
    if any(segment.startswith("dependency_") for segment in segments):
        return "REGISTRY_DEPENDENCY_DENY"
    if case_name in {
        "legacy_publish_draft_denied",
        "noncatalog_event_append_denied",
        "read_unknown_resource_denied",
        "unknown_action",
        "unknown_pair",
        "unknown_resource",
    }:
        return "REGISTRY_PAIR_DENY"
    raise ValueError(f"authority fixture case has no reviewed registry reason: {case_name}")


def _validate_max_effect_shape(value: Any, *, label: str) -> None:
    if not isinstance(value, dict) or set(value) != AUTHORITY_MAX_EFFECT_KEYS:
        raise ValueError(f"{label} max_effect does not match the closed schema")
    if (
        not _is_authority_token(value["code"])
    ):
        raise ValueError(f"{label} max_effect code is invalid")
    for key in ("max_targets", "max_state_transitions"):
        if type(value[key]) is not int or value[key] < 0:  # bool is not an integer here
            raise ValueError(f"{label} {key} must be a non-negative integer")


def _is_authority_token(value: Any) -> bool:
    return (
        type(value) is str
        and len(value) <= 128
        and re.fullmatch(r"[a-z][a-z0-9_]*", value) is not None
    )


def _validate_context_scalar(value: Any, *, label: str) -> None:
    if type(value) is bool:
        return
    if type(value) is int:
        if value < 0 or value > 9_007_199_254_740_991:
            raise ValueError(f"{label} integer is outside the portable non-negative range")
        return
    if type(value) is not str:
        raise ValueError(f"{label} must be a string, boolean, or non-negative integer")
    if len(value) > 4096:
        raise ValueError(f"{label} string exceeds 4096 characters")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError(f"{label} string must be valid UTF-8 scalar text") from exc
    if value and value != value.strip():
        raise ValueError(f"{label} string must not have edge whitespace")
    if value and not value.strip():
        raise ValueError(f"{label} string must not be whitespace-only")
    if any(ord(character) < 32 or 127 <= ord(character) <= 159 for character in value):
        raise ValueError(f"{label} string must not contain C0 or C1 controls")


def _validate_dependency_evidence(value: Any, *, label: str) -> None:
    if not isinstance(value, list):
        raise ValueError(f"{label} dependencies must be an array")
    identities: list[str] = []
    for index, item in enumerate(value):
        if (
            not isinstance(item, dict)
            or set(item) != AUTHORITY_DEPENDENCY_EVIDENCE_KEYS
        ):
            raise ValueError(
                f"{label} dependency evidence {index} has an invalid schema"
            )
        if (
            not isinstance(item["spec_id"], str)
            or re.fullmatch(r"SPEC-[0-9]{3}", item["spec_id"]) is None
        ):
            raise ValueError(f"{label} dependency evidence {index} has an invalid spec")
        if type(item["revision"]) is not int or item["revision"] < 1:
            raise ValueError(
                f"{label} dependency evidence {index} has an invalid revision"
            )
        if item["runtime_stage"] not in _AUTHORITY_DEPENDENCY_EVIDENCE_STAGES:
            raise ValueError(
                f"{label} dependency evidence {index} has an invalid runtime_stage"
            )
        identities.append(item["spec_id"])
    if identities != sorted(set(identities)):
        raise ValueError(
            f"{label} dependency evidence must be sorted and duplicate-free"
        )


def _parse_authority_fixture_case(
    action: str,
    resource: str,
    case: Mapping[str, Any],
    *,
    label: str,
) -> AuthorityFixtureCase:
    if not _is_authority_token(action) or not _is_authority_token(resource):
        raise ValueError(f"{label} action/resource identity is invalid")
    case_keys = set(case)
    if (
        case_keys != AUTHORITY_FIXTURE_CASE_KEYS
        and case_keys != AUTHORITY_CATALOG_FIXTURE_CASE_KEYS
    ):
        raise ValueError(f"{label} does not match the closed schema")
    if not _is_authority_token(case["case"]):
        raise ValueError(f"{label} has an invalid case name")
    if case["evidence_kind"] != "synthetic_offline":
        raise ValueError(f"{label} evidence_kind must be synthetic_offline")
    if not _is_authority_token(case["actor_class"]):
        raise ValueError(f"{label} has an invalid actor class")
    context = case["context"]
    if not isinstance(context, dict):
        raise ValueError(f"{label} context must be an object")
    if list(context) != sorted(context) or any(
        not _is_authority_token(key) for key in context
    ):
        raise ValueError(f"{label} context keys must be sorted unique authority tokens")
    for key, value in context.items():
        _validate_context_scalar(value, label=f"{label} context.{key}")
    _validate_max_effect_shape(case["effect"], label=label)
    grant = case["grant"]
    if not isinstance(grant, dict) or set(grant) != AUTHORITY_GRANT_KEYS:
        raise ValueError(f"{label} grant does not match the closed schema")
    if not _is_authority_token(grant["operation"]):
        raise ValueError(f"{label} grant operation is invalid")
    _validate_max_effect_shape(grant["effect"], label=f"{label} grant")
    _validate_dependency_evidence(case["dependencies"], label=label)
    if case["expected_decision"] not in {"allow", "deny"}:
        raise ValueError(f"{label} expected_decision is invalid")
    if case["expected_policy_decision"] not in {"allow", "deny"}:
        raise ValueError(f"{label} expected_policy_decision is invalid")
    if case["expected_registry_decision"] not in {"allow", "deny", "non_event"}:
        raise ValueError(f"{label} expected_registry_decision is invalid")
    effect = case["effect"]
    grant_effect = grant["effect"]
    return AuthorityFixtureCase(
        action=action,
        resource=resource,
        case=case["case"],
        evidence_kind=case["evidence_kind"],
        actor_class=case["actor_class"],
        context=MappingProxyType(dict(context)),
        effect_code=effect["code"],
        max_targets=effect["max_targets"],
        max_state_transitions=effect["max_state_transitions"],
        grant_effect_code=grant_effect["code"],
        grant_max_targets=grant_effect["max_targets"],
        grant_max_state_transitions=grant_effect["max_state_transitions"],
        expected_decision=case["expected_decision"],
        expected_policy_decision=case["expected_policy_decision"],
        expected_registry_decision=case["expected_registry_decision"],
        expected_registry_reason_code=_expected_registry_reason_code(
            case["case"], case["expected_registry_decision"]
        ),
        grant_operation=grant["operation"],
        dependencies=tuple(
            (item["spec_id"], item["revision"], item["runtime_stage"])
            for item in case["dependencies"]
        ),
    )


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
        raise ValueError(
            "authority fixture manifest root fields do not match the closed schema"
        )
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
        raise ValueError(
            "authority fixture manifest constitution_revision is not current"
        )
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
            raise ValueError(
                f"authority fixture entry {index} does not match the closed schema"
            )
        action = entry["action"]
        resource = entry["resource"]
        if not _is_authority_token(action) or not _is_authority_token(resource):
            raise ValueError(f"authority fixture entry {index} has an invalid identity")
        pair = (action, resource)
        if pair in seen_pairs:
            raise ValueError(f"duplicate authority fixture entry: {action}/{resource}")
        seen_pairs.add(pair)
        profile = expected_profiles.get(pair)
        if profile is None:
            raise ValueError(f"detached authority fixture entry: {action}/{resource}")
        cases = entry["cases"]
        if not isinstance(cases, list) or not cases:
            raise ValueError(
                f"authority fixture entry {index} cases must be a non-empty array"
            )
        names: list[str] = []
        for case_index, case in enumerate(cases):
            if not isinstance(case, dict) or set(case) != AUTHORITY_FIXTURE_CASE_KEYS:
                raise ValueError(
                    f"authority fixture entry {index} case {case_index} does not match "
                    "the closed schema"
                )
            names.append(case["case"])
            parsed_cases.append(
                _parse_authority_fixture_case(
                    action,
                    resource,
                    case,
                    label=f"authority fixture entry {index} case {case_index}",
                )
            )
        expected_cases = list(expected_authority_fixture_cases(profile))
        if names != sorted(set(names)) or not _exact_authority_value_equal(
            cases, expected_cases
        ):
            raise ValueError(
                f"authority fixture entry {index} must prove every actor and guard plus "
                "the exact negative semantic profile"
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
        or not _exact_authority_value_equal(
            catalog_boundary_cases, expected_boundary_cases
        )
    ):
        raise ValueError(
            "authority fixture manifest must contain the exact catalog-boundary cases"
        )
    for index, case in enumerate(catalog_boundary_cases):
        if (
            not isinstance(case, dict)
            or set(case) != AUTHORITY_CATALOG_FIXTURE_CASE_KEYS
        ):
            raise ValueError(
                f"authority catalog-boundary fixture {index} has an invalid schema"
            )
        parsed_cases.append(
            _parse_authority_fixture_case(
                case["action"],
                case["resource"],
                case,
                label=f"authority catalog-boundary fixture {index}",
            )
        )
    for case in parsed_cases:
        actual_decision, actual_reason = _authority_registry_boundary_decision(case)
        if (
            actual_decision != case.expected_registry_decision
            or actual_reason != case.expected_registry_reason_code
        ):
            raise ValueError(
                "authority fixture case does not preserve its reviewed registry "
                f"branch: {case.action}/{case.resource}/{case.case} expected "
                f"{case.expected_registry_decision}/{case.expected_registry_reason_code}, "
                f"got {actual_decision}/{actual_reason}"
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
    schema_binding: AuthorityVocabularySchemaBinding,
    expected_digest: str,
    expected_constitution_revision: int,
    expected_registry_version: int,
    fixture_manifest_bytes: bytes | None = None,
) -> AuthorityVocabularyBinding:
    """Strictly parse the machine authority vocabulary bound by SPEC-000."""

    if (
        type(schema_binding) is not AuthorityVocabularySchemaBinding
        or schema_binding.path != AUTHORITY_VOCABULARY_SCHEMA_PATH
        or schema_binding.schema_id != AUTHORITY_VOCABULARY_SCHEMA_ID
        or schema_binding.schema_version != AUTHORITY_VOCABULARY_SCHEMA_VERSION
        or schema_binding.digest != AUTHORITY_VOCABULARY_SCHEMA_DIGEST
    ):
        raise ValueError("authority vocabulary requires a validated schema 2.0.0 binding")
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
        raise ValueError(
            "authority vocabulary root fields do not match the closed schema"
        )
    if data["kind"] != "AuthorityVocabularyRegistry":
        raise ValueError(
            "authority vocabulary kind must be AuthorityVocabularyRegistry"
        )
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
        raise ValueError(
            "authority fixture manifest pointer does not match the closed schema"
        )
    if fixture_pointer["path"] != AUTHORITY_FIXTURE_MANIFEST_PATH:
        raise ValueError(
            f"authority fixture manifest path must be {AUTHORITY_FIXTURE_MANIFEST_PATH}"
        )
    if (
        not isinstance(fixture_pointer["digest"], str)
        or re.fullmatch(r"sha256:[0-9a-f]{64}", fixture_pointer["digest"]) is None
    ):
        raise ValueError("authority fixture manifest digest is invalid")
    if (
        type(fixture_pointer["version"]) is not int
        or fixture_pointer["version"] != expected_registry_version
    ):
        raise ValueError("authority fixture manifest version is invalid or stale")

    parsed_entries: list[tuple[str, str, str]] = []
    seen_pairs: set[tuple[str, str]] = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict) or set(entry) != AUTHORITY_ENTRY_KEYS:
            raise ValueError(
                f"authority entry {index} does not match the closed schema"
            )
        action = entry["action"]
        resource = entry["resource"]
        owner_spec = entry["owner_spec"]
        if not _is_authority_token(action):
            raise ValueError(f"authority entry {index} has invalid action")
        if not _is_authority_token(resource):
            raise ValueError(f"authority entry {index} has invalid resource")
        if (
            not isinstance(owner_spec, str)
            or re.fullmatch(r"SPEC-[0-9]{3}", owner_spec) is None
        ):
            raise ValueError(f"authority entry {index} has invalid owner_spec")
        pair = (action, resource)
        if pair in seen_pairs:
            raise ValueError(f"duplicate authority pair: {action}/{resource}")
        seen_pairs.add(pair)
        profile = REQUIRED_AUTHORITY_PROFILES.get(pair)
        if profile is None:
            raise ValueError(f"unreviewed authority pair: {action}/{resource}")
        _validate_max_effect_shape(
            entry["max_effect"], label=f"authority entry {index}"
        )
        if owner_spec != profile.owner_spec:
            raise ValueError(
                f"required authority pair {action}/{resource} must be owned by "
                f"{profile.owner_spec}"
            )
        actor_bindings = entry["actor_bindings"]
        if not isinstance(actor_bindings, list) or not actor_bindings:
            raise ValueError(f"authority entry {index} actor_bindings must be non-empty")
        actor_names: list[str] = []
        for binding_index, binding in enumerate(actor_bindings):
            if (
                not isinstance(binding, dict)
                or set(binding) != AUTHORITY_ACTOR_BINDING_KEYS
                or not _is_authority_token(binding.get("actor_class"))
                or not isinstance(binding.get("predicates"), list)
                or not binding["predicates"]
            ):
                raise ValueError(
                    f"authority entry {index} actor binding {binding_index} is invalid"
                )
            actor_names.append(binding["actor_class"])
            predicate_keys: list[str] = []
            for predicate_index, predicate_payload in enumerate(binding["predicates"]):
                predicate = _governance_policy_module().parse_policy_predicate(
                    predicate_payload,
                    location=(
                        f"authority entry {index} actor binding {binding_index} "
                        f"predicate {predicate_index}"
                    ),
                )
                if predicate.to_payload() != predicate_payload:
                    raise ValueError(
                        f"authority entry {index} actor binding {binding_index} "
                        "predicate is not canonical"
                    )
                predicate_keys.append(predicate.key)
            if predicate_keys != sorted(set(predicate_keys)):
                raise ValueError(
                    f"authority entry {index} actor binding {binding_index} "
                    "predicates must be sorted and key-unique"
                )
        if actor_names != sorted(set(actor_names)):
            raise ValueError(
                f"authority entry {index} actor bindings must be sorted and unique"
            )
        if not _exact_authority_value_equal(
            actor_bindings,
            [binding.to_payload() for binding in profile.actor_bindings],
        ):
            raise ValueError(
                f"authority entry {index} actor_bindings do not match the profile"
            )
        if not _exact_authority_value_equal(entry["max_effect"], profile.max_effect):
            raise ValueError(
                f"authority entry {index} max_effect does not match the profile"
            )
        dependency_requirements = entry["dependency_requirements"]
        if not isinstance(dependency_requirements, list) or not dependency_requirements:
            raise ValueError(
                f"authority entry {index} dependency_requirements must be non-empty"
            )
        dependency_ids: list[str] = []
        for requirement_index, requirement in enumerate(dependency_requirements):
            if (
                not isinstance(requirement, dict)
                or set(requirement) != AUTHORITY_DEPENDENCY_REQUIREMENT_KEYS
                or not isinstance(requirement["spec_id"], str)
                or re.fullmatch(r"SPEC-[0-9]{3}", requirement["spec_id"]) is None
                or type(requirement["revision"]) is not int
                or requirement["revision"] < 1
                or requirement["minimum_runtime_stage"] != "operational"
            ):
                raise ValueError(
                    f"authority entry {index} dependency requirement "
                    f"{requirement_index} is invalid"
                )
            dependency_ids.append(requirement["spec_id"])
        if dependency_ids != sorted(set(dependency_ids)):
            raise ValueError(
                f"authority entry {index} dependency requirements must be sorted and unique"
            )
        if not _exact_authority_value_equal(
            dependency_requirements,
            [
                requirement.to_payload()
                for requirement in profile.dependency_requirements
            ],
        ):
            raise ValueError(
                f"authority entry {index} dependency_requirements do not match the profile"
            )
        if (
            not _is_authority_token(entry["grant_operation"])
            or entry["grant_operation"] != profile.grant_operation
        ):
            raise ValueError(
                f"authority entry {index} grant_operation does not match the profile"
            )
        parsed_entries.append((action, resource, owner_spec))
    if parsed_entries != sorted(parsed_entries):
        raise ValueError(
            "authority vocabulary entries must be sorted by action/resource/owner"
        )
    if [(action, resource) for action, resource, _owner in parsed_entries] != sorted(
        REQUIRED_AUTHORITY_PROFILES
    ):
        raise ValueError(
            "authority vocabulary must contain every reviewed pair exactly once"
        )
    if exact_bytes != _canonical_json_bytes(data):
        raise ValueError(
            "authority vocabulary JSON must use canonical sorted pretty serialization"
        )
    if fixture_manifest_bytes is None:
        raise ValueError(
            "authority fixture manifest is required and cannot be detached"
        )
    fixture_binding = parse_authority_fixture_manifest(
        fixture_manifest_bytes,
        expected_digest=fixture_pointer["digest"],
        expected_constitution_revision=expected_constitution_revision,
        expected_registry_version=expected_registry_version,
        expected_profiles=REQUIRED_AUTHORITY_PROFILES,
    )
    return AuthorityVocabularyBinding(
        schema_path=schema_binding.path,
        schema_digest=schema_binding.digest,
        schema_version=schema_binding.schema_version,
        path=AUTHORITY_VOCABULARY_PATH,
        digest=actual_digest,
        registry_schema_version=data["schema_version"],
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
    pair = (case.action, case.resource)
    profile = REQUIRED_AUTHORITY_PROFILES.get(pair) or POLICY_ONLY_READ_PROFILES.get(
        pair
    )
    if profile is None:
        return ("deny", "REGISTRY_PAIR_DENY")
    if case.actor_class not in profile.actor_classes:
        return ("deny", "REGISTRY_ACTOR_DENY")
    actor_binding = profile.actor_binding(case.actor_class)
    predicates = tuple(
        _governance_policy_module().parse_policy_predicate(
            payload,
            location=f"authority profile {case.action}/{case.resource}/{case.actor_class}",
        )
        for payload in actor_binding.predicates
    )
    if set(case.context) != {predicate.key for predicate in predicates} or not all(
        _governance_policy_module().policy_predicate_matches(predicate, case.context)
        for predicate in predicates
    ):
        return ("deny", "REGISTRY_GUARD_DENY")
    if (
        case.effect_code != profile.max_effect_code
        or case.max_targets > profile.max_targets
        or case.max_state_transitions > profile.max_state_transitions
    ):
        return ("deny", "REGISTRY_EFFECT_DENY")
    if (
        case.grant_operation != profile.grant_operation
        or not _authority_grant_effect_satisfied(case)
    ):
        return ("deny", "REGISTRY_GRANT_DENY")
    if not _authority_dependency_floor_satisfied(case, profile):
        return ("deny", "REGISTRY_DEPENDENCY_DENY")
    if pair in POLICY_ONLY_READ_PROFILES:
        return ("non_event", "REGISTRY_POLICY_ONLY_READ")
    return ("allow", "REGISTRY_ALLOW")


def _authority_grant_effect_satisfied(case: AuthorityFixtureCase) -> bool:
    return (
        case.grant_effect_code == case.effect_code
        and case.max_targets <= case.grant_max_targets
        and case.max_state_transitions <= case.grant_max_state_transitions
    )


def _authority_dependency_floor_satisfied(
    case: AuthorityFixtureCase,
    profile: AuthoritySemanticProfile | None,
) -> bool:
    """Evaluate only the exact revision/status floor, independent of other denials."""

    requirements = (
        profile.dependency_requirements
        if profile is not None
        else (AuthorityDependencyRequirement("SPEC-000", 2),)
    )
    required = {
        requirement.spec_id: (
            requirement.revision,
            requirement.minimum_runtime_stage,
        )
        for requirement in requirements
    }
    evidence = {
        spec_id: (revision, runtime_stage)
        for spec_id, revision, runtime_stage in case.dependencies
    }
    return set(evidence) == set(required) and all(
        evidence[spec_id] == requirement for spec_id, requirement in required.items()
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
        canonical_context = dict(case.context)
        dependency_value = [
            {
                "spec_id": spec_id,
                "revision": revision,
                "runtime_stage": runtime_stage,
            }
            for spec_id, revision, runtime_stage in case.dependencies
        ]
        canonical_context.update(
            {
                "dependency_evidence_digest": f"sha256:{hashlib.sha256(_canonical_json_bytes(dependency_value)).hexdigest()}",
                "dependency_floor_satisfied": _authority_dependency_floor_satisfied(
                    case, profile
                ),
                "grant_operation": case.grant_operation,
                "grant_effect_satisfied": _authority_grant_effect_satisfied(case),
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
            if registry_decision in {"allow", "non_event"}
            and policy_decision == "allow"
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
                "expected_registry_reason_code": case.expected_registry_reason_code,
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
    actor_class: str | None = None,
) -> tuple[dict[str, object], ...]:
    """Return the canonical typed conditions for one atomic actor allow path."""

    if actor_class is None:
        if len(profile.actor_classes) != 1:
            raise ValueError("actor_class is required for a multi-actor authority profile")
        actor_class = profile.actor_classes[0]
    try:
        binding = profile.actor_binding(actor_class)
    except KeyError as exc:
        raise ValueError(f"actor class {actor_class} is not bound by the profile") from exc
    conditions = {
        str(predicate["key"]): dict(predicate) for predicate in binding.predicates
    }
    conditions.update(
        {
            "dependency_evidence_digest": {
                "key": "dependency_evidence_digest",
                "operator": "present",
                "value_type": "sha256_digest",
            },
            "dependency_floor_satisfied": {
                "key": "dependency_floor_satisfied",
                "operator": "equals",
                "value": True,
                "value_type": "boolean",
            },
            "grant_effect_satisfied": {
                "key": "grant_effect_satisfied",
                "operator": "equals",
                "value": True,
                "value_type": "boolean",
            },
            "grant_operation": {
                "key": "grant_operation",
                "operator": "equals",
                "value": profile.grant_operation,
                "value_type": "string",
            },
            "requested_effect_code": {
                "key": "requested_effect_code",
                "operator": "equals",
                "value": profile.max_effect_code,
                "value_type": "string",
            },
            "requested_max_state_transitions": {
                "key": "requested_max_state_transitions",
                "operator": "less_than_or_equal",
                "value": profile.max_state_transitions,
                "value_type": "integer",
            },
            "requested_max_targets": {
                "key": "requested_max_targets",
                "operator": "less_than_or_equal",
                "value": profile.max_targets,
                "value_type": "integer",
            },
        }
    )
    return tuple(conditions[key] for key in sorted(conditions))


_AUTHORITY_PROTECTED_SOD_GROUPS = (
    ("attestor", ("independent_canary_attestor", "release_attestor")),
    (
        "author",
        (
            "change_author",
            "community_contributor",
            "content_proposer",
            "human_maintainer",
            "research_proposer",
        ),
    ),
    ("sealer", ("independent_epoch_sealer",)),
    ("verifier", ("independent_verifier",)),
)


def _is_synthetic_offline_principal(value: object) -> bool:
    """Recognize fixture identities without claiming provider authentication."""

    if type(value) is not str or not value.startswith("synthetic:"):
        return False
    return _is_authority_token(value.removeprefix("synthetic:"))


def validate_authority_policy_closure(constitution: Any) -> None:
    """Reject noncatalog, overbroad, duplicate, or weaker allow-rule paths."""

    if getattr(constitution, "schema_major", None) != 2:
        raise ValueError("authority conformance requires Constitution schema major 2")
    document = constitution.document
    if document.get("schema_version") != AUTHORITY_CONSTITUTION_SCHEMA_VERSION:
        raise ValueError(
            "authority conformance requires exact Constitution schema version "
            f"{AUTHORITY_CONSTITUTION_SCHEMA_VERSION}"
        )
    if (
        document.get("lifecycle_state") != "effective"
        or document.get("effective_commit") != "$SELF"
    ):
        raise ValueError(
            "authority conformance requires lifecycle_state effective bound to "
            "effective_commit $SELF"
        )
    actor_descriptors = document.get("actor_classes", {})
    actual_actor_automation = {
        actor: descriptor.get("automated")
        for actor, descriptor in actor_descriptors.items()
        if isinstance(descriptor, dict)
    }
    if not _exact_authority_value_equal(
        actual_actor_automation, dict(AUTHORITY_ACTOR_AUTOMATION)
    ):
        raise ValueError(
            "authority conformance requires the exact reviewed actor-class "
            "automation descriptors"
        )
    protected_surfaces = set(document.get("protected_surfaces", ()))
    missing_protected_surfaces = sorted(
        AUTHORITY_MINIMUM_PROTECTED_SURFACES - protected_surfaces
    )
    if missing_protected_surfaces:
        raise ValueError(
            "authority conformance omits reviewed protected surfaces: "
            f"{missing_protected_surfaces}"
        )
    unprotected_components = [
        path
        for path in AUTHORITY_EVALUATOR_COMPONENT_PATHS
        if constitution.classify_path(path) != "protected_surface"
    ]
    if unprotected_components:
        raise ValueError(
            "authority conformance classifies evaluator components as public: "
            f"{unprotected_components}"
        )
    if not _exact_authority_value_equal(
        document.get("emergency_controls"), dict(_AUTHORITY_EMERGENCY_CONTROLS)
    ):
        raise ValueError(
            "authority conformance requires the exact reviewed emergency controls"
        )
    expected_amendment = dict(_AUTHORITY_AMENDMENT_PROCEDURE)
    expected_amendment["required_state_sequence"] = list(
        _AUTHORITY_AMENDMENT_PROCEDURE["required_state_sequence"]
    )
    if not _exact_authority_value_equal(
        document.get("amendment_procedure"), expected_amendment
    ):
        raise ValueError(
            "authority conformance requires the exact reviewed amendment procedure"
        )
    try:
        rules = constitution.rules
    except (AttributeError, KeyError, TypeError) as exc:
        raise ValueError("constitution does not expose validated policy rules") from exc
    deny_rule_ids = sorted(
        rule["rule_id"] for rule in rules if rule.get("effect") == "deny"
    )
    if deny_rule_ids:
        raise ValueError(
            "authority default-deny class-policy oracle must not contain explicit "
            f"deny rules: {deny_rule_ids}"
        )
    seen_paths: set[tuple[str, str, str]] = set()
    for rule in rules:
        if rule.get("effect") != "allow":
            continue
        if not all(len(rule[field]) == 1 for field in ("actors", "actions", "resources")):
            raise ValueError(
                f"allow rule {rule['rule_id']} must bind one atomic actor/action/resource path"
            )
        actor = rule["actors"][0]
        action = rule["actions"][0]
        resource = rule["resources"][0]
        pair = (action, resource)
        profile = REQUIRED_AUTHORITY_PROFILES.get(
            pair
        ) or POLICY_ONLY_READ_PROFILES.get(pair)
        if profile is None or actor not in profile.actor_classes:
            raise ValueError(
                f"allow rule {rule['rule_id']} contains noncatalog path "
                f"{actor}/{action}/{resource}"
            )
        if rule.get("reason_code") != AUTHORITY_ALLOW_REASON_CODE:
            raise ValueError(
                f"allow rule {rule['rule_id']} must use offline-only reason code "
                f"{AUTHORITY_ALLOW_REASON_CODE}"
            )
        predicates = constitution.predicates_for_rule(rule["rule_id"])
        if not _exact_authority_value_equal(
            [predicate.to_payload() for predicate in predicates],
            list(expected_authority_policy_conditions(profile, actor)),
        ):
            raise ValueError(
                f"allow rule {rule['rule_id']} has a noncanonical predicate "
                f"for {actor}/{action}/{resource}"
            )
        path = (actor, action, resource)
        if path in seen_paths:
            raise ValueError(f"duplicate allow path for {actor}/{action}/{resource}")
        seen_paths.add(path)

    expected_paths = {
        (actor, action, resource)
        for (action, resource), profile in {
            **REQUIRED_AUTHORITY_PROFILES,
            **POLICY_ONLY_READ_PROFILES,
        }.items()
        for actor in profile.actor_classes
    }
    if seen_paths != expected_paths:
        missing = sorted(expected_paths - seen_paths)
        extra = sorted(seen_paths - expected_paths)
        raise ValueError(
            f"authority allow-path closure mismatch: missing={missing}, extra={extra}"
        )

    sod_rules = constitution.separation_of_duty_rules
    if len(sod_rules) != 1:
        raise ValueError("authority conformance requires one protected-lineage SoD rule")
    sod_rule = sod_rules[0]
    actual_groups = tuple(
        (group.duty, tuple(group.actor_classes)) for group in sod_rule.groups
    )
    if (
        sod_rule.scope != "protected_change_lineage"
        or sod_rule.constraint
        != "distinct_authenticated_principal_across_groups"
        or actual_groups != _AUTHORITY_PROTECTED_SOD_GROUPS
    ):
        raise ValueError("authority protected-lineage SoD rule is not exact")

    # Before SPEC-024 defines authenticated runtime resolution, these optional
    # bindings are only synthetic offline fixtures. Provider handles would make
    # case, Unicode, and account-linking aliases look falsely authoritative.
    invalid_principals = sorted(
        (actor, principal)
        for actor, principals in constitution.identity_bindings.items()
        for principal in principals
        if not _is_synthetic_offline_principal(principal)
    )
    if invalid_principals:
        raise ValueError(
            "authority offline identity bindings require synthetic:<lowercase_token> "
            "fixture principals; runtime/provider identity requires future SPEC-024 "
            f"resolver evidence: {invalid_principals}"
        )

    actor_duties = {
        actor: duty
        for duty, actors in _AUTHORITY_PROTECTED_SOD_GROUPS
        for actor in actors
    }
    principal_duties: dict[str, set[str]] = {}
    for actor, principals in constitution.identity_bindings.items():
        duty = actor_duties.get(actor)
        if duty is None:
            continue
        for principal in principals:
            principal_duties.setdefault(principal, set()).add(duty)
    conflicts = {
        principal: sorted(duties)
        for principal, duties in principal_duties.items()
        if len(duties) > 1
    }
    if conflicts:
        raise ValueError(
            "offline identity bindings span protected-lineage duties: "
            f"{conflicts}"
        )


def parse_authority_policy_conformance(
    exact_bytes: bytes,
    *,
    registry: AuthorityVocabularyBinding,
    constitution: Any,
    evaluator_component_bytes: Mapping[str, bytes] | Iterable[tuple[str, bytes]],
) -> AuthorityPolicyConformanceBinding:
    """Validate and independently reproduce an implemented-stage receipt."""

    if type(constitution) is not _governance_policy_module().Constitution:
        raise ValueError(
            "authority policy conformance requires the canonical Constitution "
            "evaluator implementation"
        )
    data = _strict_json_loads(exact_bytes, label="authority policy conformance receipt")
    if not isinstance(data, dict):
        raise ValueError("authority policy conformance receipt root must be an object")
    root_keys = {
        "kind",
        "schema_version",
        "scope",
        "runtime_authority",
        "constitution_revision",
        "registry_version",
        "constitution_policy",
        "registry_digest",
        "fixture_manifest_digest",
        "validator_bundle",
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
    if data["scope"] != AUTHORITY_CONFORMANCE_SCOPE:
        raise ValueError("authority policy conformance receipt scope is invalid")
    if data["runtime_authority"] != AUTHORITY_RUNTIME_AUTHORITY:
        raise ValueError(
            "authority policy conformance receipt must declare runtime_authority none"
        )
    if (
        type(data["constitution_revision"]) is not int
        or data["constitution_revision"] != registry.constitution_revision
        or type(data["registry_version"]) is not int
        or data["registry_version"] != registry.registry_version
    ):
        raise ValueError(
            "authority policy conformance receipt revision binding is stale"
        )

    policy = data["constitution_policy"]
    if not isinstance(policy, dict) or set(policy) != AUTHORITY_CONFORMANCE_POLICY_KEYS:
        raise ValueError("authority policy conformance policy binding is invalid")
    expected_policy_digest = f"sha256:{constitution.digest}"
    if (
        policy["path"] != AUTHORITY_CONSTITUTION_POLICY_PATH
        or policy["digest"] != expected_policy_digest
        or policy["version"] != constitution.version
    ):
        raise ValueError(
            "authority policy conformance receipt binds the wrong constitution"
        )
    if data["registry_digest"] != registry.digest:
        raise ValueError(
            "authority policy conformance receipt binds the wrong registry"
        )
    if data["fixture_manifest_digest"] != registry.fixture_manifest_digest:
        raise ValueError(
            "authority policy conformance receipt binds the wrong fixture manifest"
        )

    validator_bundle = data["validator_bundle"]
    component_entries = (
        tuple(evaluator_component_bytes.items())
        if isinstance(evaluator_component_bytes, Mapping)
        else tuple(evaluator_component_bytes)
    )
    expected_bundle = build_authority_evaluator_bundle(component_entries)
    provided_components = dict(component_entries)
    runtime_components = dict(authority_evaluator_runtime_component_bytes())
    if any(
        provided_components.get(path) != runtime_components[path]
        for path in _AUTHORITY_EVALUATOR_EXECUTABLE_COMPONENT_PATHS
    ):
        raise ValueError(
            "authority policy conformance receipt component bytes do not match "
            "the executing evaluator"
        )
    try:
        parse_authority_vocabulary_schema(
            provided_components[AUTHORITY_VOCABULARY_SCHEMA_PATH],
            expected_digest=registry.schema_digest,
            expected_version=registry.schema_version,
        )
    except ValueError as exc:
        raise ValueError(
            "authority policy conformance receipt evaluator bundle contains an "
            f"invalid schema component: {exc}"
        ) from exc
    if (
        not isinstance(validator_bundle, dict)
        or set(validator_bundle) != AUTHORITY_CONFORMANCE_VALIDATOR_BUNDLE_KEYS
        or not isinstance(validator_bundle.get("components"), list)
        or any(
            not isinstance(component, dict)
            or set(component) != AUTHORITY_CONFORMANCE_VALIDATOR_COMPONENT_KEYS
            for component in validator_bundle.get("components", [])
        )
        or not _exact_authority_value_equal(
            validator_bundle, expected_bundle.to_receipt_value()
        )
    ):
        raise ValueError(
            "authority policy conformance receipt binds the wrong evaluator bundle"
        )

    expected_results = list(authority_policy_case_results(registry, constitution))
    try:
        validate_authority_policy_closure(constitution)
    except ValueError as exc:
        raise ValueError(
            f"constitution policy does not implement the authority registry: {exc}"
        ) from exc
    nonconforming = [
        result
        for result in expected_results
        if result["policy_decision"] != result["expected_policy_decision"]
        or result["registry_decision"] != result["expected_registry_decision"]
        or result["registry_reason_code"]
        != result["expected_registry_reason_code"]
        or result["actual_decision"] != result["expected_decision"]
    ]
    if nonconforming:
        first = nonconforming[0]
        raise ValueError(
            "constitution policy does not implement the authority registry: "
            f"{first['action']}/{first['resource']}/{first['case']} expected "
            f"policy={first['expected_policy_decision']}, "
            f"registry={first['expected_registry_decision']}, "
            f"registry_reason={first['expected_registry_reason_code']}, "
            f"combined={first['expected_decision']}; got "
            f"policy={first['policy_decision']}, "
            f"registry={first['registry_decision']}, "
            f"registry_reason={first['registry_reason_code']}, "
            f"combined={first['actual_decision']}"
        )
    if (
        type(data["case_count"]) is not int
        or data["case_count"] != len(expected_results)
        or type(data["skipped_case_count"]) is not int
        or data["skipped_case_count"] != 0
        or data["result"] != "pass"
    ):
        raise ValueError(
            "authority policy conformance receipt summary is not an exact pass"
        )
    cases = data["cases"]
    if not isinstance(cases, list):
        raise ValueError("authority policy conformance receipt cases must be an array")
    for index, case in enumerate(cases):
        if not isinstance(case, dict) or set(case) != AUTHORITY_CONFORMANCE_CASE_KEYS:
            raise ValueError(
                f"authority policy conformance case {index} does not match the closed schema"
            )
    if not _exact_authority_value_equal(cases, expected_results):
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
        scope=data["scope"],
        runtime_authority=data["runtime_authority"],
        constitution_policy_digest=policy["digest"],
        registry_digest=data["registry_digest"],
        fixture_manifest_digest=data["fixture_manifest_digest"],
        validator_bundle_algorithm=expected_bundle.algorithm,
        validator_bundle_digest=expected_bundle.digest,
        validator_bundle_version=expected_bundle.version,
        validator_bundle_components=expected_bundle.components,
        case_count=data["case_count"],
    )


def _load_constitution_for_conformance(path: Path) -> Any:
    return _governance_policy_module().Constitution.load(path)


def load_authority_vocabulary(
    root: Path,
    metadata: Mapping[str, str],
    *,
    expected_constitution_revision: int,
) -> AuthorityVocabularyBinding:
    present_metadata = AUTHORITY_SPEC_METADATA_KEYS.intersection(metadata)
    if present_metadata != AUTHORITY_SPEC_METADATA_KEYS:
        missing = sorted(AUTHORITY_SPEC_METADATA_KEYS - present_metadata)
        extra_state = "partial" if present_metadata else "absent"
        raise ValueError(
            "authority vocabulary metadata must provide the atomic six-key set; "
            f"state={extra_state}, missing={missing}"
        )
    schema_path_value = metadata.get("Authority vocabulary schema")
    schema_digest = metadata.get("Authority vocabulary schema digest")
    schema_version_value = metadata.get("Authority vocabulary schema version")
    if schema_path_value != AUTHORITY_VOCABULARY_SCHEMA_PATH:
        raise ValueError(
            "Authority vocabulary schema must be the canonical path "
            f"{AUTHORITY_VOCABULARY_SCHEMA_PATH}"
        )
    if schema_digest is None or re.fullmatch(
        r"sha256:[0-9a-f]{64}", schema_digest
    ) is None:
        raise ValueError(
            "Authority vocabulary schema digest must be sha256:<64 lowercase hex>"
        )
    if schema_version_value != AUTHORITY_VOCABULARY_SCHEMA_VERSION:
        raise ValueError(
            "Authority vocabulary schema version must be "
            f"{AUTHORITY_VOCABULARY_SCHEMA_VERSION}"
        )
    schema_binding = load_authority_vocabulary_schema(
        root,
        expected_digest=schema_digest,
        expected_version=schema_version_value,
    )

    path_value = metadata.get("Authority vocabulary")
    digest = metadata.get("Authority vocabulary digest")
    version_value = metadata.get("Authority vocabulary version")
    if path_value != AUTHORITY_VOCABULARY_PATH:
        raise ValueError(
            f"Authority vocabulary must be the canonical path {AUTHORITY_VOCABULARY_PATH}"
        )
    if digest is None or re.fullmatch(r"sha256:[0-9a-f]{64}", digest) is None:
        raise ValueError(
            "Authority vocabulary digest must be sha256:<64 lowercase hex>"
        )
    if version_value is None or re.fullmatch(r"[1-9][0-9]*", version_value) is None:
        raise ValueError(
            "Authority vocabulary version must be a canonical positive integer"
        )
    registry_version = int(version_value)
    registry_bytes = read_canonical_repository_file(
        root,
        AUTHORITY_VOCABULARY_PATH,
        label="authority vocabulary",
    )
    fixture_bytes = read_canonical_repository_file(
        root,
        AUTHORITY_FIXTURE_MANIFEST_PATH,
        label="authority fixture manifest",
    )
    binding = parse_authority_vocabulary(
        registry_bytes,
        schema_binding=schema_binding,
        expected_digest=digest,
        expected_constitution_revision=expected_constitution_revision,
        expected_registry_version=registry_version,
        fixture_manifest_bytes=fixture_bytes,
    )
    receipt_path = root / AUTHORITY_CONFORMANCE_RECEIPT_PATH
    if not receipt_path.exists():
        if receipt_path.is_symlink():
            raise ValueError(
                "authority policy conformance receipt must be a regular canonical "
                "repository file"
            )
        return binding
    receipt_bytes = read_canonical_repository_file(
        root,
        AUTHORITY_CONFORMANCE_RECEIPT_PATH,
        label="authority policy conformance receipt",
    )
    constitution_path = root / AUTHORITY_CONSTITUTION_POLICY_PATH
    constitution_bytes = read_canonical_repository_file(
        root,
        AUTHORITY_CONSTITUTION_POLICY_PATH,
        label="authority constitution policy",
    )
    evaluator_component_bytes: list[tuple[str, bytes]] = []
    for component_path_value in AUTHORITY_EVALUATOR_COMPONENT_PATHS:
        evaluator_component_bytes.append(
            (
                component_path_value,
                read_canonical_repository_file(
                    root,
                    component_path_value,
                    label="authority evaluator bundle component",
                ),
            )
        )
    constitution = _load_constitution_for_conformance(constitution_path)
    if constitution.digest != hashlib.sha256(constitution_bytes).hexdigest():
        raise ValueError("authority constitution policy changed while being loaded")
    conformance = parse_authority_policy_conformance(
        receipt_bytes,
        registry=binding,
        constitution=constitution,
        evaluator_component_bytes=evaluator_component_bytes,
    )
    return replace(binding, policy_conformance=conformance)
    "AuthorityActorBinding",
    "AuthorityDependencyRequirement",
