#!/usr/bin/env python3
"""Validate specification lifecycle transitions against exact Git authorities.

The corpus inventory validates the candidate tree in isolation. This gate owns
the temporal question that an isolated tree cannot answer: whether a proposed
status or revision is a legal successor to its transition base. A separate
protected-default tree proves that a terminal predecessor was actually promoted
before its successor revision can be proposed. GitHub remains the authority for
the actor and merge event that moved those bytes onto the protected default.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

if __package__:
    from researcher.scripts import validate_authority_contract as _authority_contract
else:  # Direct script execution resolves the sibling from this script's directory.
    import validate_authority_contract as _authority_contract


# Explicit compatibility re-exports. The authority-contract implementation lives
# on its own protected surface; existing lifecycle consumers retain their API.
AUTHORITY_ACTOR_AUTOMATION = _authority_contract.AUTHORITY_ACTOR_AUTOMATION
AUTHORITY_ALLOW_REASON_CODE = _authority_contract.AUTHORITY_ALLOW_REASON_CODE
AUTHORITY_VOCABULARY_SPEC = _authority_contract.AUTHORITY_VOCABULARY_SPEC
AUTHORITY_VOCABULARY_MIN_REVISION = (
    _authority_contract.AUTHORITY_VOCABULARY_MIN_REVISION
)
AUTHORITY_VOCABULARY_PATH = _authority_contract.AUTHORITY_VOCABULARY_PATH
AUTHORITY_VOCABULARY_SCHEMA_PATH = (
    _authority_contract.AUTHORITY_VOCABULARY_SCHEMA_PATH
)
AUTHORITY_VOCABULARY_SCHEMA_ID = _authority_contract.AUTHORITY_VOCABULARY_SCHEMA_ID
AUTHORITY_VOCABULARY_SCHEMA_DIGEST = (
    _authority_contract.AUTHORITY_VOCABULARY_SCHEMA_DIGEST
)
AUTHORITY_VOCABULARY_SCHEMA_VERSION = (
    _authority_contract.AUTHORITY_VOCABULARY_SCHEMA_VERSION
)
AUTHORITY_FIXTURE_MANIFEST_PATH = _authority_contract.AUTHORITY_FIXTURE_MANIFEST_PATH
AUTHORITY_FIXTURE_MANIFEST_SCHEMA_VERSION = (
    _authority_contract.AUTHORITY_FIXTURE_MANIFEST_SCHEMA_VERSION
)
AUTHORITY_CONFORMANCE_RECEIPT_PATH = (
    _authority_contract.AUTHORITY_CONFORMANCE_RECEIPT_PATH
)
AUTHORITY_CONFORMANCE_RECEIPT_SCHEMA_VERSION = (
    _authority_contract.AUTHORITY_CONFORMANCE_RECEIPT_SCHEMA_VERSION
)
AUTHORITY_CONFORMANCE_SCOPE = _authority_contract.AUTHORITY_CONFORMANCE_SCOPE
AUTHORITY_RUNTIME_AUTHORITY = _authority_contract.AUTHORITY_RUNTIME_AUTHORITY
AUTHORITY_SPEC_METADATA_KEYS = _authority_contract.AUTHORITY_SPEC_METADATA_KEYS
AUTHORITY_CONSTITUTION_POLICY_PATH = (
    _authority_contract.AUTHORITY_CONSTITUTION_POLICY_PATH
)
AUTHORITY_CONSTITUTION_SCHEMA_VERSION = (
    _authority_contract.AUTHORITY_CONSTITUTION_SCHEMA_VERSION
)
AUTHORITY_VALIDATOR_PATH = _authority_contract.AUTHORITY_VALIDATOR_PATH
AUTHORITY_VALIDATOR_VERSION = _authority_contract.AUTHORITY_VALIDATOR_VERSION
AUTHORITY_VOCABULARY_READY_STATUSES = (
    _authority_contract.AUTHORITY_VOCABULARY_READY_STATUSES
)
AUTHORITY_IMPLEMENTED_STATUSES = _authority_contract.AUTHORITY_IMPLEMENTED_STATUSES
AUTHORITY_PREIMPLEMENTATION_STATUSES = (
    _authority_contract.AUTHORITY_PREIMPLEMENTATION_STATUSES
)
AUTHORITY_ENTRY_KEYS = _authority_contract.AUTHORITY_ENTRY_KEYS
AUTHORITY_ACTOR_BINDING_KEYS = _authority_contract.AUTHORITY_ACTOR_BINDING_KEYS
AUTHORITY_DEPENDENCY_REQUIREMENT_KEYS = (
    _authority_contract.AUTHORITY_DEPENDENCY_REQUIREMENT_KEYS
)
AUTHORITY_MAX_EFFECT_KEYS = _authority_contract.AUTHORITY_MAX_EFFECT_KEYS
AUTHORITY_MINIMUM_PROTECTED_SURFACES = (
    _authority_contract.AUTHORITY_MINIMUM_PROTECTED_SURFACES
)
AUTHORITY_GRANT_KEYS = _authority_contract.AUTHORITY_GRANT_KEYS
AUTHORITY_FIXTURE_POINTER_KEYS = _authority_contract.AUTHORITY_FIXTURE_POINTER_KEYS
AUTHORITY_FIXTURE_ENTRY_KEYS = _authority_contract.AUTHORITY_FIXTURE_ENTRY_KEYS
AUTHORITY_FIXTURE_CASE_KEYS = _authority_contract.AUTHORITY_FIXTURE_CASE_KEYS
AUTHORITY_CATALOG_FIXTURE_CASE_KEYS = (
    _authority_contract.AUTHORITY_CATALOG_FIXTURE_CASE_KEYS
)
AUTHORITY_DEPENDENCY_EVIDENCE_KEYS = (
    _authority_contract.AUTHORITY_DEPENDENCY_EVIDENCE_KEYS
)
AUTHORITY_CONFORMANCE_POLICY_KEYS = (
    _authority_contract.AUTHORITY_CONFORMANCE_POLICY_KEYS
)
AUTHORITY_CONFORMANCE_VALIDATOR_KEYS = (
    _authority_contract.AUTHORITY_CONFORMANCE_VALIDATOR_KEYS
)
AUTHORITY_CONFORMANCE_VALIDATOR_BUNDLE_KEYS = (
    _authority_contract.AUTHORITY_CONFORMANCE_VALIDATOR_BUNDLE_KEYS
)
AUTHORITY_CONFORMANCE_VALIDATOR_COMPONENT_KEYS = (
    _authority_contract.AUTHORITY_CONFORMANCE_VALIDATOR_COMPONENT_KEYS
)
AUTHORITY_CONFORMANCE_CASE_KEYS = _authority_contract.AUTHORITY_CONFORMANCE_CASE_KEYS
AUTHORITY_VALIDATOR_BUNDLE_ALGORITHM = (
    _authority_contract.AUTHORITY_VALIDATOR_BUNDLE_ALGORITHM
)
AUTHORITY_EVALUATOR_BUNDLE_VERSION = (
    _authority_contract.AUTHORITY_EVALUATOR_BUNDLE_VERSION
)
AUTHORITY_EVALUATOR_COMPONENT_PATHS = (
    _authority_contract.AUTHORITY_EVALUATOR_COMPONENT_PATHS
)
AuthoritySemanticProfile = _authority_contract.AuthoritySemanticProfile
AuthorityActorBinding = _authority_contract.AuthorityActorBinding
AuthorityDependencyRequirement = _authority_contract.AuthorityDependencyRequirement
POLICY_ONLY_READ_ACTORS = _authority_contract.POLICY_ONLY_READ_ACTORS
POLICY_ONLY_READ_PROFILES = _authority_contract.POLICY_ONLY_READ_PROFILES
REQUIRED_AUTHORITY_PROFILES = _authority_contract.REQUIRED_AUTHORITY_PROFILES
REQUIRED_AUTHORITY_VOCABULARY_OWNERS = (
    _authority_contract.REQUIRED_AUTHORITY_VOCABULARY_OWNERS
)
AuthorityFixtureCase = _authority_contract.AuthorityFixtureCase
AuthorityFixtureManifestBinding = _authority_contract.AuthorityFixtureManifestBinding
AuthorityEvaluatorComponentBinding = (
    _authority_contract.AuthorityEvaluatorComponentBinding
)
AuthorityEvaluatorBundleBinding = _authority_contract.AuthorityEvaluatorBundleBinding
AuthorityPolicyConformanceBinding = (
    _authority_contract.AuthorityPolicyConformanceBinding
)
AuthorityVocabularyBinding = _authority_contract.AuthorityVocabularyBinding
AuthorityVocabularySchemaBinding = (
    _authority_contract.AuthorityVocabularySchemaBinding
)
expected_authority_dependency_evidence = (
    _authority_contract.expected_authority_dependency_evidence
)
expected_authority_fixture_cases = _authority_contract.expected_authority_fixture_cases
expected_authority_catalog_boundary_cases = (
    _authority_contract.expected_authority_catalog_boundary_cases
)
parse_authority_fixture_manifest = _authority_contract.parse_authority_fixture_manifest
parse_authority_vocabulary = _authority_contract.parse_authority_vocabulary
parse_authority_vocabulary_schema = (
    _authority_contract.parse_authority_vocabulary_schema
)
authority_policy_case_results = _authority_contract.authority_policy_case_results
build_authority_evaluator_bundle = _authority_contract.build_authority_evaluator_bundle
expected_authority_policy_conditions = (
    _authority_contract.expected_authority_policy_conditions
)
validate_authority_policy_closure = (
    _authority_contract.validate_authority_policy_closure
)
parse_authority_policy_conformance = (
    _authority_contract.parse_authority_policy_conformance
)
load_authority_vocabulary = _authority_contract.load_authority_vocabulary
load_authority_vocabulary_schema = (
    _authority_contract.load_authority_vocabulary_schema
)


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


def load_candidate_authority_vocabulary(
    root: Path,
    candidate_specs: Mapping[str, SpecRevision],
) -> AuthorityVocabularyBinding | None:
    """Load schema-v2 artifacts while allowing the standalone schema under rev1."""

    authority_spec = candidate_specs.get(AUTHORITY_VOCABULARY_SPEC)
    present_metadata = (
        set()
        if authority_spec is None
        else AUTHORITY_SPEC_METADATA_KEYS.intersection(authority_spec.metadata)
    )
    schema_path = root / AUTHORITY_VOCABULARY_SCHEMA_PATH
    schema_present = schema_path.exists() or schema_path.is_symlink()
    registry_path = root / AUTHORITY_VOCABULARY_PATH
    fixture_path = root / AUTHORITY_FIXTURE_MANIFEST_PATH
    registry_present = registry_path.exists() or registry_path.is_symlink()
    fixture_present = fixture_path.exists() or fixture_path.is_symlink()
    receipt_path = root / AUTHORITY_CONFORMANCE_RECEIPT_PATH
    receipt_present = receipt_path.exists() or receipt_path.is_symlink()
    if not (
        present_metadata
        or schema_present
        or registry_present
        or fixture_present
        or receipt_present
    ):
        return None
    if authority_spec is None:
        if schema_present and not (registry_present or fixture_present or receipt_present):
            load_authority_vocabulary_schema(root)
            return None
        raise ValueError("authority vocabulary artifacts require canonical SPEC-000")
    if authority_spec.revision < AUTHORITY_VOCABULARY_MIN_REVISION:
        if present_metadata:
            raise ValueError(
                "pre-registry SPEC-000 forbids authority vocabulary metadata"
            )
        if registry_present or fixture_present or receipt_present:
            raise ValueError(
                "pre-registry SPEC-000 forbids registry, fixture, and receipt artifacts"
            )
        if schema_present:
            load_authority_vocabulary_schema(root)
        return None
    if present_metadata != AUTHORITY_SPEC_METADATA_KEYS:
        missing = sorted(AUTHORITY_SPEC_METADATA_KEYS - present_metadata)
        raise ValueError(
            "SPEC-000 revision 2 authority metadata must be the atomic six-key set; "
            f"missing={missing}"
        )
    if (
        authority_spec.status in AUTHORITY_PREIMPLEMENTATION_STATUSES
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


def parse_spec_revision(
    path: str, exact_bytes: bytes, *, allow_legacy: bool
) -> SpecRevision:
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
        contract_body="\n".join(lines[body_start:])
        + ("\n" if text.endswith("\n") else ""),
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
        elif (
            current.path != previous.path or current.exact_bytes != previous.exact_bytes
        ):
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
            authority_vocabulary.schema_path
            == record.metadata.get("Authority vocabulary schema")
            and authority_vocabulary.schema_digest
            == record.metadata.get("Authority vocabulary schema digest")
            and authority_vocabulary.schema_version
            == record.metadata.get("Authority vocabulary schema version")
            and authority_vocabulary.path
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
            and receipt.schema_version == AUTHORITY_CONFORMANCE_RECEIPT_SCHEMA_VERSION
            and receipt.scope == AUTHORITY_CONFORMANCE_SCOPE
            and receipt.runtime_authority == AUTHORITY_RUNTIME_AUTHORITY
            and receipt.registry_digest == authority_vocabulary.digest
            and receipt.fixture_manifest_digest
            == authority_vocabulary.fixture_manifest_digest
            and receipt.validator_bundle_algorithm
            == AUTHORITY_VALIDATOR_BUNDLE_ALGORITHM
            and receipt.validator_bundle_version == AUTHORITY_EVALUATOR_BUNDLE_VERSION
            and tuple(
                component.path for component in receipt.validator_bundle_components
            )
            == AUTHORITY_EVALUATOR_COMPONENT_PATHS
            and all(
                re.fullmatch(r"sha256:[0-9a-f]{64}", component.digest) is not None
                for component in receipt.validator_bundle_components
            )
            and re.fullmatch(r"sha256:[0-9a-f]{64}", receipt.validator_bundle_digest)
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
        requires_policy_conformance = (
            current.status in AUTHORITY_IMPLEMENTED_STATUSES
            and (
                (
                    current.spec_id == AUTHORITY_VOCABULARY_SPEC
                    and current.revision >= AUTHORITY_VOCABULARY_MIN_REVISION
                )
                or int(current.spec_id[-3:]) >= 4
            )
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
            if (
                current.status != "draft"
                or current.revision != 1
                or current.revises != "none"
            ):
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
        if previous.status != "draft" and current.metadata.get(
            "Dependency revisions"
        ) != previous.metadata.get("Dependency revisions"):
            report(
                "SPEC_DEPENDENCY_BINDING_CHANGED",
                current,
                "dependency revision bindings are immutable after architecture review",
            )
        if current.spec_id == "SPEC-026" and current.metadata.get(
            "Activation"
        ) != previous.metadata.get("Activation"):
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


def validate_promoted_revision_predecessors(
    transition_base: Mapping[str, SpecRevision],
    candidate: Mapping[str, SpecRevision],
    promoted_default: Mapping[str, SpecRevision],
    *,
    transition_base_adrs: Mapping[str, AdrRevision],
    promoted_default_adrs: Mapping[str, AdrRevision],
) -> list[LifecycleFinding]:
    """Require each replacement predecessor to be exact on protected default.

    The transition base may be another proposal branch in a stacked pull request.
    Its terminal metadata is useful for diff validation but carries no lifecycle
    authority until those exact bytes are reachable from the protected default.
    """

    findings: list[LifecycleFinding] = []

    def report(record: SpecRevision, message: str) -> None:
        findings.append(
            LifecycleFinding(
                "SPEC_REVISION_PREDECESSOR_NOT_PROMOTED",
                record.path,
                record.spec_id,
                message,
            )
        )

    for spec_id, current in sorted(candidate.items()):
        previous = transition_base.get(spec_id)
        if previous is None or current.revision <= previous.revision:
            continue

        promoted = promoted_default.get(spec_id)
        if promoted is None:
            report(
                current,
                "the protected default does not contain the terminal predecessor",
            )
            continue
        if promoted.path != previous.path:
            report(
                current,
                "the protected-default predecessor has a different canonical path",
            )
            continue
        if promoted.revision != previous.revision:
            report(
                current,
                "the protected-default predecessor has a different revision",
            )
            continue
        if promoted.status not in {"amended", "superseded"}:
            report(
                current,
                "the protected-default predecessor is not terminal as amended or superseded",
            )
            continue
        if promoted.replacement != previous.replacement:
            report(
                current,
                "the protected-default predecessor has a different replacement pointer",
            )
            continue
        if promoted.exact_bytes != previous.exact_bytes:
            report(
                current,
                "the protected-default predecessor bytes differ from the transition base",
            )
            continue

        decision_id = previous.lifecycle_decision
        base_decision = (
            transition_base_adrs.get(decision_id) if decision_id is not None else None
        )
        promoted_decision = (
            promoted_default_adrs.get(decision_id) if decision_id is not None else None
        )
        expected_transition = (
            f"{previous.spec_id}@{previous.revision} -> "
            f"{previous.status} -> {previous.replacement}"
        )
        if (
            base_decision is None
            or base_decision.status != "accepted"
            or base_decision.lifecycle_transition != expected_transition
        ):
            report(
                current,
                "the transition base lacks the exact accepted predecessor lifecycle ADR",
            )
            continue
        if (
            promoted_decision is None
            or promoted_decision.status != "accepted"
            or promoted_decision.lifecycle_transition != expected_transition
        ):
            report(
                current,
                "the protected default lacks the exact accepted predecessor lifecycle ADR",
            )
            continue
        if promoted_decision.path != base_decision.path:
            report(
                current,
                "the protected-default lifecycle ADR has a different canonical path",
            )
            continue
        if promoted_decision.exact_bytes != base_decision.exact_bytes:
            report(
                current,
                "the protected-default lifecycle ADR differs from the transition base",
            )

    return sorted(findings, key=lambda item: (item.path, item.code, item.message))


def _git(root: Path, arguments: list[str]) -> bytes:
    git_environment = {
        key: value for key, value in os.environ.items() if not key.startswith("GIT_")
    }
    git_environment["GIT_NO_REPLACE_OBJECTS"] = "1"
    git_environment["GIT_CONFIG_NOSYSTEM"] = "1"
    git_environment["GIT_CONFIG_GLOBAL"] = os.devnull
    completed = subprocess.run(
        ["git", "--no-replace-objects", *arguments],
        cwd=root,
        check=False,
        env=git_environment,
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
    paths = (
        _git(
            root,
            ["ls-tree", "-r", "--name-only", base_ref, "--", "docs/specs"],
        )
        .decode("utf-8")
        .splitlines()
    )
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
    paths = (
        _git(
            root,
            ["ls-tree", "-r", "--name-only", base_ref, "--", "docs/decisions"],
        )
        .decode("utf-8")
        .splitlines()
    )
    records: dict[str, AdrRevision] = {}
    for path in sorted(path for path in paths if ADR_PATH_RE.fullmatch(path)):
        record = parse_adr_revision(path, _git(root, ["show", f"{base_ref}:{path}"]))
        if record.adr_id in records:
            raise ValueError(
                f"duplicate base architecture decision ID: {record.adr_id}"
            )
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
    parser.add_argument(
        "--base-ref",
        required=True,
        help="exact Git commit/ref used as the candidate transition base",
    )
    parser.add_argument(
        "--promoted-ref",
        required=True,
        help="exact protected-default commit/ref that proves predecessor promotion",
    )
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        base_oid = _git(root, ["rev-parse", "--verify", f"{args.base_ref}^{{commit}}"])
        base_oid_text = base_oid.decode("ascii").strip()
        promoted_oid = _git(
            root,
            ["rev-parse", "--verify", f"{args.promoted_ref}^{{commit}}"],
        )
        promoted_oid_text = promoted_oid.decode("ascii").strip()
        base_specs = load_base(root, base_oid_text)
        promoted_specs = load_base(root, promoted_oid_text)
        base_adrs = load_base_adrs(root, base_oid_text)
        promoted_adrs = load_base_adrs(root, promoted_oid_text)
        candidate_specs = load_candidate(root)
        candidate_adrs = load_candidate_adrs(root)
        authority_vocabulary = load_candidate_authority_vocabulary(
            root, candidate_specs
        )
        findings = validate_lifecycle(
            base_specs,
            candidate_specs,
            authority_vocabulary=authority_vocabulary,
        )
        findings.extend(
            validate_promoted_revision_predecessors(
                base_specs,
                candidate_specs,
                promoted_specs,
                transition_base_adrs=base_adrs,
                promoted_default_adrs=promoted_adrs,
            )
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
                base_adrs,
                candidate_adrs,
            )
        )
        findings = sorted(
            findings, key=lambda item: (item.path, item.code, item.message)
        )
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"[SPEC_LIFECYCLE_ERROR] {exc}", file=sys.stderr)
        return 1
    if findings:
        print_findings(findings)
        return 1
    print(
        "Specification lifecycle check passed against "
        f"transition base {base_oid_text} and promoted default {promoted_oid_text}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
