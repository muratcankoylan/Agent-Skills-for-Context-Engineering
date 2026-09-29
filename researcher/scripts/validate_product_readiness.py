#!/usr/bin/env python3
"""Validate a non-authoritative, blocked product-readiness assessment.

Version 1 deliberately cannot certify production readiness. That transition
requires an accepted attestation contract and an external exact-candidate
verifier, neither of which exists in the assessed repository.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = Path("docs/product/production-readiness.json")
SPEC_ID_PATTERN = re.compile(r"^SPEC-[0-9]{3}$")
SPEC_FILE_PATTERN = re.compile(r"^(SPEC-[0-9]{3})-.*\.md$")
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$|^[0-9a-f]{64}$")
TEST_GATE_STATES = {"planned", "implemented", "passing", "blocked"}
CAPABILITY_STATES = {
    "available",
    "blocked",
    "deferred",
    "implemented",
    "operational",
    "partial",
    "planned",
    "preparatory",
}
ENVIRONMENT_STATES = {
    "active",
    "alternative-planned",
    "blocked",
    "manual-engineering-only",
    "planned",
}
CANDIDATE_STATES = {"committed", "uncommitted_worktree"}


class StrictJSONError(ValueError):
    """Raised when a readiness document is not strict JSON."""


@dataclass(frozen=True)
class Finding:
    code: str
    message: str


@dataclass(frozen=True)
class SpecState:
    status: str
    revision: int
    path: str


def _reject_constant(value: str) -> None:
    raise StrictJSONError(f"non-finite JSON number is forbidden: {value}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise StrictJSONError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def load_strict_json(path: Path) -> Any:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise StrictJSONError(f"cannot read readiness manifest: {exc}") from exc

    try:
        return json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (json.JSONDecodeError, StrictJSONError) as exc:
        raise StrictJSONError(f"invalid readiness manifest: {exc}") from exc


def load_spec_states(root: Path = ROOT) -> dict[str, SpecState]:
    specs: dict[str, SpecState] = {}
    spec_root = root / "docs" / "specs"
    for path in sorted(spec_root.glob("SPEC-[0-9][0-9][0-9]-*.md")):
        match = SPEC_FILE_PATTERN.fullmatch(path.name)
        if match is None:
            continue
        spec_id = match.group(1)
        status: str | None = None
        revision: int | None = None
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError) as exc:
            raise ValueError(f"cannot read {path}: {exc}") from exc
        for line in lines[:20]:
            if line.startswith("Status:"):
                status = line.partition(":")[2].strip()
            elif line.startswith("Revision:"):
                raw_revision = line.partition(":")[2].strip()
                try:
                    revision = int(raw_revision)
                except ValueError as exc:
                    raise ValueError(
                        f"{path}: Revision must be an integer"
                    ) from exc
        if status is None or revision is None:
            raise ValueError(f"{path}: missing Status or Revision metadata")
        if spec_id in specs:
            raise ValueError(f"duplicate specification identity: {spec_id}")
        specs[spec_id] = SpecState(
            status=status,
            revision=revision,
            path=path.relative_to(root).as_posix(),
        )
    return specs


def _nonblank(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _string_list_errors(value: Any, label: str) -> list[Finding]:
    if not isinstance(value, list):
        return [Finding("INVALID_LIST", f"{label} must be an array")]
    findings: list[Finding] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not _nonblank(item):
            findings.append(
                Finding("INVALID_STRING", f"{label}[{index}] must be nonblank")
            )
            continue
        assert isinstance(item, str)
        if item in seen:
            findings.append(
                Finding("DUPLICATE_VALUE", f"{label} repeats {item}")
            )
        seen.add(item)
    return findings


def _has_repository_evidence(value: Any, root: Path) -> bool:
    """Return whether an evidence array names an existing confined repo path."""

    if not isinstance(value, list):
        return False
    resolved_root = root.resolve()
    for item in value:
        if not _nonblank(item):
            continue
        assert isinstance(item, str)
        candidate = Path(item)
        if candidate.is_absolute():
            continue
        try:
            resolved = (resolved_root / candidate).resolve(strict=True)
            resolved.relative_to(resolved_root)
        except (OSError, RuntimeError, ValueError):
            continue
        if resolved.exists():
            return True
    return False


def _required_spec_errors(
    value: Any,
    label: str,
    spec_states: dict[str, SpecState],
) -> tuple[list[str], list[Finding]]:
    findings = _string_list_errors(value, label)
    if findings or not isinstance(value, list):
        return [], findings
    result: list[str] = []
    for item in value:
        assert isinstance(item, str)
        if SPEC_ID_PATTERN.fullmatch(item) is None:
            findings.append(
                Finding("INVALID_SPEC_ID", f"{label} contains invalid spec id {item}")
            )
        elif item not in spec_states:
            findings.append(
                Finding("UNKNOWN_SPEC", f"{label} references unknown {item}")
            )
        else:
            result.append(item)
    return result, findings


def _activation_errors(
    *,
    enabled: Any,
    required_specs: list[str],
    label: str,
    authoritative: bool,
    spec_states: dict[str, SpecState],
) -> list[Finding]:
    if not isinstance(enabled, bool):
        return [
            Finding("INVALID_ACTIVATION_FLAG", f"{label}.activation_enabled must be boolean")
        ]
    if not enabled:
        return []

    findings: list[Finding] = []
    if not authoritative:
        findings.append(
            Finding(
                "NON_AUTHORITATIVE_ACTIVATION",
                f"{label} enables activation while authority.authoritative is false",
            )
        )
    for spec_id in required_specs:
        state = spec_states[spec_id]
        if state.status != "operational":
            findings.append(
                Finding(
                    "OWNER_SPEC_NOT_OPERATIONAL",
                    f"{label} enables activation but {spec_id}@{state.revision} is {state.status}",
                )
            )
    return findings


def validate_manifest(
    manifest: Any,
    spec_states: dict[str, SpecState],
    *,
    root: Path = ROOT,
) -> list[Finding]:
    if not isinstance(manifest, dict):
        return [Finding("INVALID_ROOT", "readiness manifest must be a JSON object")]

    findings: list[Finding] = []
    for key in (
        "schema_version",
        "product_id",
        "authority",
        "capabilities",
        "environments",
        "test_gates",
        "blockers",
    ):
        if key not in manifest:
            findings.append(Finding("MISSING_FIELD", f"manifest is missing {key}"))

    if manifest.get("schema_version") != "1.0.0":
        findings.append(
            Finding("UNSUPPORTED_SCHEMA", "schema_version must be exactly 1.0.0")
        )
    if not _nonblank(manifest.get("product_id")):
        findings.append(Finding("INVALID_PRODUCT_ID", "product_id must be nonblank"))

    authority = manifest.get("authority")
    authoritative = False
    production_ready = False
    candidate_state: str | None = None
    candidate_commit: str | None = None
    production_scope: list[str] = []
    active_environment_id: str | None = None
    if not isinstance(authority, dict):
        findings.append(Finding("INVALID_AUTHORITY", "authority must be an object"))
    else:
        authoritative_value = authority.get("authoritative")
        production_ready_value = authority.get("production_ready")
        if not isinstance(authoritative_value, bool):
            findings.append(
                Finding("INVALID_AUTHORITY", "authority.authoritative must be boolean")
            )
        else:
            authoritative = authoritative_value
        if not isinstance(production_ready_value, bool):
            findings.append(
                Finding("INVALID_AUTHORITY", "authority.production_ready must be boolean")
            )
        else:
            production_ready = production_ready_value
        baseline_commit = authority.get("baseline_commit")
        if not isinstance(baseline_commit, str) or COMMIT_PATTERN.fullmatch(baseline_commit) is None:
            findings.append(
                Finding(
                    "INVALID_BASELINE_COMMIT",
                    "authority.baseline_commit must be a full lowercase Git object id",
                )
            )
        candidate_state_value = authority.get("candidate_state")
        if candidate_state_value not in CANDIDATE_STATES:
            findings.append(
                Finding(
                    "INVALID_CANDIDATE_STATE",
                    f"authority.candidate_state must be one of {sorted(CANDIDATE_STATES)}",
                )
            )
        else:
            candidate_state = candidate_state_value
        candidate_commit_value = authority.get("candidate_commit")
        if candidate_commit_value is not None and (
            not isinstance(candidate_commit_value, str)
            or COMMIT_PATTERN.fullmatch(candidate_commit_value) is None
        ):
            findings.append(
                Finding(
                    "INVALID_CANDIDATE_COMMIT",
                    "authority.candidate_commit must be null or a full lowercase Git object id",
                )
            )
        elif isinstance(candidate_commit_value, str):
            candidate_commit = candidate_commit_value
        if candidate_state == "committed" and candidate_commit is None:
            findings.append(
                Finding(
                    "MISSING_CANDIDATE_COMMIT",
                    "a committed candidate state requires authority.candidate_commit",
                )
            )
        if candidate_state == "uncommitted_worktree" and candidate_commit is not None:
            findings.append(
                Finding(
                    "UNCOMMITTED_CANDIDATE_HAS_COMMIT",
                    "an uncommitted worktree assessment cannot claim a candidate commit",
                )
            )
        if not _nonblank(authority.get("notice")):
            findings.append(
                Finding("INVALID_AUTHORITY_NOTICE", "authority.notice must be nonblank")
            )
        if authority.get("certification_mode") != "blocked_assessment_only":
            findings.append(
                Finding(
                    "INVALID_CERTIFICATION_MODE",
                    "authority.certification_mode must be blocked_assessment_only",
                )
            )
        scope_value = authority.get("production_scope")
        findings.extend(_string_list_errors(scope_value, "authority.production_scope"))
        if isinstance(scope_value, list):
            production_scope = [item for item in scope_value if isinstance(item, str)]
        active_environment_value = authority.get("active_environment_id")
        if active_environment_value is not None and not _nonblank(active_environment_value):
            findings.append(
                Finding(
                    "INVALID_ACTIVE_ENVIRONMENT",
                    "authority.active_environment_id must be null or nonblank",
                )
            )
        elif isinstance(active_environment_value, str):
            active_environment_id = active_environment_value

    capabilities = manifest.get("capabilities")
    capability_ids: set[str] = set()
    capability_activation: list[bool] = []
    if not isinstance(capabilities, list) or not capabilities:
        findings.append(
            Finding("INVALID_CAPABILITIES", "capabilities must be a nonempty array")
        )
    else:
        for index, capability in enumerate(capabilities):
            label = f"capabilities[{index}]"
            if not isinstance(capability, dict):
                findings.append(Finding("INVALID_CAPABILITY", f"{label} must be an object"))
                continue
            capability_id = capability.get("id")
            if not _nonblank(capability_id):
                findings.append(Finding("INVALID_CAPABILITY_ID", f"{label}.id must be nonblank"))
            else:
                assert isinstance(capability_id, str)
                if capability_id in capability_ids:
                    findings.append(
                        Finding("DUPLICATE_CAPABILITY", f"duplicate capability id {capability_id}")
                    )
                capability_ids.add(capability_id)
                label = f"capability {capability_id}"
            if not _nonblank(capability.get("product_id")):
                findings.append(
                    Finding("INVALID_CAPABILITY_PRODUCT", f"{label}.product_id must be nonblank")
                )
            if not _nonblank(capability.get("category")):
                findings.append(
                    Finding("INVALID_CAPABILITY_CATEGORY", f"{label}.category must be nonblank")
                )
            status = capability.get("status")
            if status not in CAPABILITY_STATES:
                findings.append(
                    Finding(
                        "INVALID_CAPABILITY_STATUS",
                        f"{label}.status must be one of {sorted(CAPABILITY_STATES)}",
                    )
                )
            required_specs, spec_findings = _required_spec_errors(
                capability.get("required_specs"),
                f"{label}.required_specs",
                spec_states,
            )
            findings.extend(spec_findings)
            enabled = capability.get("activation_enabled")
            findings.extend(
                _activation_errors(
                    enabled=enabled,
                    required_specs=required_specs,
                    label=label,
                    authoritative=authoritative,
                    spec_states=spec_states,
                )
            )
            if isinstance(enabled, bool):
                capability_activation.append(enabled)
            findings.extend(_string_list_errors(capability.get("evidence"), f"{label}.evidence"))
            capability_blockers = capability.get("blockers")
            findings.extend(_string_list_errors(capability_blockers, f"{label}.blockers"))
            if enabled is True:
                if isinstance(capability_blockers, list) and capability_blockers:
                    findings.append(
                        Finding(
                            "ACTIVE_CAPABILITY_HAS_BLOCKERS",
                            f"{label} is enabled but still declares blockers",
                        )
                    )
                if status != "operational":
                    findings.append(
                        Finding(
                            "ACTIVE_CAPABILITY_NOT_OPERATIONAL",
                            f"{label} is enabled but status is not operational",
                        )
                    )
                if not _has_repository_evidence(capability.get("evidence"), root):
                    findings.append(
                        Finding(
                            "ACTIVE_CAPABILITY_WITHOUT_REPOSITORY_EVIDENCE",
                            f"{label} has no existing repository evidence path",
                        )
                    )

    environments = manifest.get("environments")
    environment_ids: set[str] = set()
    active_environments = 0
    if not isinstance(environments, list) or not environments:
        findings.append(
            Finding("INVALID_ENVIRONMENTS", "environments must be a nonempty array")
        )
    else:
        for index, environment in enumerate(environments):
            label = f"environments[{index}]"
            if not isinstance(environment, dict):
                findings.append(Finding("INVALID_ENVIRONMENT", f"{label} must be an object"))
                continue
            environment_id = environment.get("id")
            if not _nonblank(environment_id):
                findings.append(Finding("INVALID_ENVIRONMENT_ID", f"{label}.id must be nonblank"))
            else:
                assert isinstance(environment_id, str)
                if environment_id in environment_ids:
                    findings.append(
                        Finding("DUPLICATE_ENVIRONMENT", f"duplicate environment id {environment_id}")
                    )
                environment_ids.add(environment_id)
                label = f"environment {environment_id}"
            status = environment.get("status")
            if status not in ENVIRONMENT_STATES:
                findings.append(
                    Finding(
                        "INVALID_ENVIRONMENT_STATUS",
                        f"{label}.status must be one of {sorted(ENVIRONMENT_STATES)}",
                    )
                )
            required_specs, spec_findings = _required_spec_errors(
                environment.get("required_specs"),
                f"{label}.required_specs",
                spec_states,
            )
            findings.extend(spec_findings)
            enabled = environment.get("activation_enabled")
            findings.extend(
                _activation_errors(
                    enabled=enabled,
                    required_specs=required_specs,
                    label=label,
                    authoritative=authoritative,
                    spec_states=spec_states,
                )
            )
            if enabled is True:
                active_environments += 1
                if status != "active":
                    findings.append(
                        Finding(
                            "ENABLED_ENVIRONMENT_NOT_ACTIVE",
                            f"{label} is enabled but status is not active",
                        )
                    )
            components = environment.get("components")
            findings.extend(_string_list_errors(components, f"{label}.components"))
            if isinstance(components, list):
                for component in components:
                    if isinstance(component, str) and component not in capability_ids:
                        findings.append(
                            Finding(
                                "UNKNOWN_ENVIRONMENT_COMPONENT",
                                f"{label}.components references unknown capability {component}",
                            )
                        )

    test_gates = manifest.get("test_gates")
    gate_ids: set[str] = set()
    all_gates_passing = True
    if not isinstance(test_gates, list) or not test_gates:
        findings.append(Finding("INVALID_TEST_GATES", "test_gates must be a nonempty array"))
        all_gates_passing = False
    else:
        for index, gate in enumerate(test_gates):
            label = f"test_gates[{index}]"
            if not isinstance(gate, dict):
                findings.append(Finding("INVALID_TEST_GATE", f"{label} must be an object"))
                all_gates_passing = False
                continue
            gate_id = gate.get("id")
            if not _nonblank(gate_id):
                findings.append(Finding("INVALID_TEST_GATE_ID", f"{label}.id must be nonblank"))
            else:
                assert isinstance(gate_id, str)
                if gate_id in gate_ids:
                    findings.append(Finding("DUPLICATE_TEST_GATE", f"duplicate test gate id {gate_id}"))
                gate_ids.add(gate_id)
                label = f"test gate {gate_id}"
            status = gate.get("status")
            if status not in TEST_GATE_STATES:
                findings.append(
                    Finding(
                        "INVALID_TEST_GATE_STATUS",
                        f"{label}.status must be one of {sorted(TEST_GATE_STATES)}",
                    )
                )
                all_gates_passing = False
            elif status != "passing":
                all_gates_passing = False
            evidence_errors = _string_list_errors(gate.get("evidence"), f"{label}.evidence")
            findings.extend(evidence_errors)
            if status == "passing" and gate.get("evidence") == []:
                findings.append(
                    Finding("PASSING_GATE_WITHOUT_EVIDENCE", f"{label} has no evidence")
                )
            if status == "passing" and not _has_repository_evidence(
                gate.get("evidence"), root
            ):
                findings.append(
                    Finding(
                        "PASSING_GATE_WITHOUT_REPOSITORY_EVIDENCE",
                        f"{label} has no existing repository evidence path",
                    )
                )

    blockers = manifest.get("blockers")
    blocker_errors = _string_list_errors(blockers, "blockers")
    findings.extend(blocker_errors)
    has_blockers = isinstance(blockers, list) and bool(blockers)

    if production_ready:
        findings.append(
            Finding(
                "READINESS_CERTIFICATION_UNSUPPORTED",
                "schema version 1 validates blocked assessments only; it cannot certify production readiness",
            )
        )
        if not authoritative:
            findings.append(
                Finding(
                    "FALSE_PRODUCTION_READY",
                    "production_ready cannot be true while authoritative is false",
                )
            )
        if has_blockers:
            findings.append(
                Finding("FALSE_PRODUCTION_READY", "production_ready cannot have blockers")
            )
        if not all_gates_passing:
            findings.append(
                Finding("FALSE_PRODUCTION_READY", "production_ready requires every test gate passing")
            )
        if active_environments == 0:
            findings.append(
                Finding("FALSE_PRODUCTION_READY", "production_ready requires an active environment")
            )
        if candidate_state != "committed" or candidate_commit is None:
            findings.append(
                Finding(
                    "FALSE_PRODUCTION_READY",
                    "production_ready requires an exact committed candidate",
                )
            )
        if not production_scope:
            findings.append(
                Finding(
                    "FALSE_PRODUCTION_READY",
                    "production_ready requires a nonempty authority.production_scope",
                )
            )
        if active_environment_id is None:
            findings.append(
                Finding(
                    "FALSE_PRODUCTION_READY",
                    "production_ready requires authority.active_environment_id",
                )
            )
    elif not has_blockers and not blocker_errors:
        findings.append(
            Finding(
                "MISSING_READINESS_BLOCKER",
                "a non-production-ready declaration must name at least one blocker",
            )
        )

    if authoritative and "SPEC-000" in spec_states:
        constitution = spec_states["SPEC-000"]
        if constitution.status != "operational":
            findings.append(
                Finding(
                    "AUTHORITY_SPEC_NOT_OPERATIONAL",
                    f"authoritative is true but SPEC-000@{constitution.revision} is {constitution.status}",
                )
            )
    unknown_scope = sorted(set(production_scope) - capability_ids)
    for capability_id in unknown_scope:
        findings.append(
            Finding(
                "UNKNOWN_PRODUCTION_SCOPE_CAPABILITY",
                f"authority.production_scope references unknown capability {capability_id}",
            )
        )
    if production_ready and not unknown_scope and isinstance(capabilities, list):
        by_id = {
            item.get("id"): item
            for item in capabilities
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        }
        for capability_id in production_scope:
            capability = by_id.get(capability_id)
            if not isinstance(capability, dict) or capability.get("activation_enabled") is not True:
                findings.append(
                    Finding(
                        "FALSE_PRODUCTION_READY",
                        f"production-scope capability {capability_id} is not enabled",
                    )
                )
    if active_environment_id is not None:
        if active_environment_id not in environment_ids:
            findings.append(
                Finding(
                    "UNKNOWN_ACTIVE_ENVIRONMENT",
                    f"authority.active_environment_id references unknown environment {active_environment_id}",
                )
            )
        elif isinstance(environments, list):
            selected = next(
                (
                    item
                    for item in environments
                    if isinstance(item, dict) and item.get("id") == active_environment_id
                ),
                None,
            )
            if production_ready and (
                not isinstance(selected, dict)
                or selected.get("activation_enabled") is not True
                or selected.get("status") != "active"
            ):
                findings.append(
                    Finding(
                        "FALSE_PRODUCTION_READY",
                        f"selected environment {active_environment_id} is not active",
                    )
                )

    return findings


def build_report(
    manifest: Any,
    findings: list[Finding],
    spec_states: dict[str, SpecState],
    manifest_path: Path,
) -> dict[str, Any]:
    authority = manifest.get("authority", {}) if isinstance(manifest, dict) else {}
    production_ready = (
        authority.get("production_ready") is True if isinstance(authority, dict) else False
    )
    return {
        "valid": not findings,
        "production_ready": production_ready and not findings,
        "readiness": "ready" if production_ready and not findings else "blocked",
        "manifest": manifest_path.as_posix(),
        "spec_states": {
            spec_id: asdict(state) for spec_id, state in sorted(spec_states.items())
        },
        "findings": [asdict(finding) for finding in findings],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument(
        "--require-ready",
        action="store_true",
        help="also fail when the declaration is truthful but production remains blocked",
    )
    args = parser.parse_args(argv)

    root = args.root.resolve()
    manifest_path = args.manifest
    if not manifest_path.is_absolute():
        manifest_path = root / manifest_path

    try:
        manifest = load_strict_json(manifest_path)
        spec_states = load_spec_states(root)
        findings = validate_manifest(manifest, spec_states, root=root)
    except (StrictJSONError, ValueError) as exc:
        manifest = {}
        spec_states = {}
        findings = [Finding("READINESS_INPUT_ERROR", str(exc))]

    report = build_report(manifest, findings, spec_states, manifest_path)
    if args.as_json:
        print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    else:
        state = "VALID" if report["valid"] else "INVALID"
        print(f"Product readiness declaration: {state}; {report['readiness']}")
        for finding in findings:
            print(f"- {finding.code}: {finding.message}")

    if findings:
        return 1
    if args.require_ready and not report["production_ready"]:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
