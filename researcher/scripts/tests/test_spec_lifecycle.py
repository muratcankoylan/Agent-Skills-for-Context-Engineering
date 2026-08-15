"""Base-aware specification lifecycle tests."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import yaml

from researcher.scripts import validate_authority_contract as authority_contract
from researcher.scripts import validate_spec_lifecycle as spec_lifecycle
from researcher.scripts.governance_policy import Constitution
from researcher.scripts.validate_spec_lifecycle import (
    AUTHORITY_CONFORMANCE_RECEIPT_SCHEMA_VERSION,
    AUTHORITY_CONSTITUTION_POLICY_PATH,
    AUTHORITY_EVALUATOR_BUNDLE_VERSION,
    AUTHORITY_EVALUATOR_COMPONENT_PATHS,
    AUTHORITY_FIXTURE_MANIFEST_PATH,
    AUTHORITY_VALIDATOR_BUNDLE_ALGORITHM,
    AUTHORITY_VOCABULARY_PATH,
    POLICY_ONLY_READ_PROFILES,
    REQUIRED_AUTHORITY_PROFILES,
    AuthorityEvaluatorBundleBinding,
    AuthorityVocabularyBinding,
    authority_policy_case_results,
    build_authority_evaluator_bundle,
    expected_authority_catalog_boundary_cases,
    expected_authority_fixture_cases,
    expected_authority_policy_conditions,
    load_candidate_authority_vocabulary,
    load_authority_vocabulary,
    parse_authority_vocabulary,
    parse_authority_policy_conformance,
    parse_adr_revision,
    parse_spec_revision,
    validate_adr_lifecycle,
    validate_lifecycle,
    validate_lifecycle_decision_bindings,
    validate_promoted_revision_predecessors,
)


ROOT = Path(__file__).resolve().parents[3]


def spec_bytes(
    *,
    spec_id: str = "SPEC-004",
    status: str = "draft",
    revision: int = 1,
    revises: str = "none",
    body: str = "Contract A.",
    lifecycle_decision: str | None = None,
    replacement: str | None = None,
    activation: str | None = None,
    depends_on: str = "none",
    dependency_revisions: str | None = None,
    authority_path: str | None = None,
    authority_digest: str | None = None,
    authority_version: int | str | None = None,
) -> bytes:
    decision = (
        f"Lifecycle decision: {lifecycle_decision}\n"
        if lifecycle_decision is not None
        else ""
    )
    replacement_line = (
        f"Replacement: {replacement}\n" if replacement is not None else ""
    )
    activation_line = f"Activation: {activation}\n" if activation is not None else ""
    dependency_revisions_line = (
        f"Dependency revisions: {dependency_revisions}\n"
        if dependency_revisions is not None
        else ""
    )
    authority_lines = ""
    if authority_path is not None:
        authority_lines += f"Authority vocabulary: {authority_path}\n"
    if authority_digest is not None:
        authority_lines += f"Authority vocabulary digest: {authority_digest}\n"
    if authority_version is not None:
        authority_lines += f"Authority vocabulary version: {authority_version}\n"
    return (
        f"# {spec_id}: Fixture\n\n"
        f"Status: {status}\n"
        f"Revision: {revision}\n"
        f"Revises: {revises}\n"
        "Wave: 1\n"
        "Classification: split\n"
        "Owners: test agent; human maintainer\n"
        f"Depends on: {depends_on}\n"
        f"{activation_line}{dependency_revisions_line}{authority_lines}"
        f"{decision}{replacement_line}\n"
        "## Decision\n\n"
        f"{body}\n"
    ).encode("utf-8")


def revision(exact_bytes: bytes, *, allow_legacy: bool = False):
    return parse_spec_revision(
        "docs/specs/SPEC-004-fixture.md",
        exact_bytes,
        allow_legacy=allow_legacy,
    )


def revision_at(path: str, exact_bytes: bytes, *, allow_legacy: bool = False):
    return parse_spec_revision(path, exact_bytes, allow_legacy=allow_legacy)


def terminal_adr(body: str = "Decision A."):
    return parse_adr_revision(
        "docs/decisions/0007-fixture.md",
        (
            "# ADR-0007: Fixture\n\n"
            "- Status: accepted\n"
            "- Date: 2026-08-15\n"
            "- Spec: SPEC-004\n"
            "- Lifecycle transition: SPEC-004@1 -> amended -> SPEC-004@2\n\n"
            "## Decision\n\n"
            f"{body}\n"
        ).encode("utf-8"),
    )


def canonical_json(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")


def authority_documents(
    *, constitution_revision: int = 2, registry_version: int = 2
) -> tuple[dict, dict, bytes, bytes]:
    fixture_entries = []
    registry_entries = []
    for (action, resource), profile in sorted(REQUIRED_AUTHORITY_PROFILES.items()):
        registry_entries.append(
            {
                "action": action,
                "resource": resource,
                "owner_spec": profile.owner_spec,
                "actor_classes": list(profile.actor_classes),
                "max_effect": profile.max_effect,
                "dependency_floor": list(profile.dependency_floor),
                "decision_context_fields": list(profile.decision_context_fields),
                "grant_operation": profile.grant_operation,
            }
        )
        fixture_entries.append(
            {
                "action": action,
                "resource": resource,
                "cases": list(expected_authority_fixture_cases(profile)),
            }
        )
    fixture = {
        "kind": "AuthorityVocabularyFixtureManifest",
        "schema_version": "1.0.0",
        "constitution_revision": constitution_revision,
        "registry_version": registry_version,
        "catalog_boundary_cases": list(expected_authority_catalog_boundary_cases()),
        "entries": fixture_entries,
    }
    fixture_bytes = canonical_json(fixture)
    registry = {
        "kind": "AuthorityVocabularyRegistry",
        "schema_version": "1.0.0",
        "owner_spec": "SPEC-000",
        "constitution_revision": constitution_revision,
        "registry_version": registry_version,
        "fixture_manifest": {
            "path": AUTHORITY_FIXTURE_MANIFEST_PATH,
            "digest": f"sha256:{hashlib.sha256(fixture_bytes).hexdigest()}",
            "version": registry_version,
        },
        "entries": registry_entries,
    }
    registry_bytes = canonical_json(registry)
    return registry, fixture, registry_bytes, fixture_bytes


def parse_valid_authority() -> AuthorityVocabularyBinding:
    _registry, _fixture, registry_bytes, fixture_bytes = authority_documents()
    return parse_authority_vocabulary(
        registry_bytes,
        expected_digest=f"sha256:{hashlib.sha256(registry_bytes).hexdigest()}",
        expected_constitution_revision=2,
        expected_registry_version=2,
        fixture_manifest_bytes=fixture_bytes,
    )


def conforming_constitution() -> Constitution:
    actors = {"human_maintainer"}
    actions = set()
    resources = set()
    rules = []
    for index, ((action, resource), profile) in enumerate(
        sorted(REQUIRED_AUTHORITY_PROFILES.items())
    ):
        actors.update(profile.actor_classes)
        actions.add(action)
        resources.add(resource)
        rules.append(
            {
                "rule_id": f"authority-profile-{index:03d}",
                "effect": "allow",
                "actors": list(profile.actor_classes),
                "actions": [action],
                "resources": [resource],
                "conditions": list(expected_authority_policy_conditions(profile)),
                "reason_code": "AUTHORITY_PROFILE_ALLOWED",
            }
        )
    for index, ((action, resource), profile) in enumerate(
        sorted(POLICY_ONLY_READ_PROFILES.items())
    ):
        actors.update(profile.actor_classes)
        actions.add(action)
        resources.add(resource)
        rules.append(
            {
                "rule_id": f"policy-only-read-{index:03d}",
                "effect": "allow",
                "actors": list(profile.actor_classes),
                "actions": [action],
                "resources": [resource],
                "conditions": list(expected_authority_policy_conditions(profile)),
                "reason_code": "POLICY_ONLY_READ_ALLOWED",
            }
        )
    document = {
        "schema_version": "1.0.0",
        "constitution_version": "2.0.0",
        "lifecycle_state": "effective",
        "effective_commit": "fixture",
        "default_effect": "deny",
        "promotion_event": "human_merged_commit",
        "actor_classes": {
            actor: {"automated": actor != "human_maintainer", "conflicts_with": []}
            for actor in sorted(actors)
        },
        "actions": sorted(actions),
        "resource_classes": sorted(resources),
        "protected_surfaces": ["governance/**"],
        "rules": rules,
        "emergency_controls": {},
        "amendment_procedure": {},
    }
    return Constitution(document, "a" * 64, Path(AUTHORITY_CONSTITUTION_POLICY_PATH))


def constitution_with_added_allow_rule(
    rule: dict,
    *,
    actions: tuple[str, ...] = (),
    resources: tuple[str, ...] = (),
) -> Constitution:
    document = deepcopy(conforming_constitution().document)
    for action in actions:
        if action not in document["actions"]:
            document["actions"].append(action)
    for resource in resources:
        if resource not in document["resource_classes"]:
            document["resource_classes"].append(resource)
    document["rules"].append(rule)
    return Constitution(
        document,
        "c" * 64,
        Path(AUTHORITY_CONSTITUTION_POLICY_PATH),
    )


def evaluator_component_bytes() -> tuple[tuple[str, bytes], ...]:
    return tuple(
        (relative, (ROOT / relative).read_bytes())
        for relative in AUTHORITY_EVALUATOR_COMPONENT_PATHS
    )


def authority_conformance_document(
    registry: AuthorityVocabularyBinding,
    constitution: Constitution,
    component_bytes: tuple[tuple[str, bytes], ...],
) -> tuple[dict, bytes]:
    results = list(authority_policy_case_results(registry, constitution))
    evaluator_bundle = build_authority_evaluator_bundle(component_bytes)
    receipt = {
        "kind": "AuthorityVocabularyConformanceReceipt",
        "schema_version": AUTHORITY_CONFORMANCE_RECEIPT_SCHEMA_VERSION,
        "constitution_revision": registry.constitution_revision,
        "registry_version": registry.registry_version,
        "constitution_policy": {
            "path": AUTHORITY_CONSTITUTION_POLICY_PATH,
            "digest": f"sha256:{constitution.digest}",
            "version": constitution.version,
        },
        "registry_digest": registry.digest,
        "fixture_manifest_digest": registry.fixture_manifest_digest,
        "validator_bundle": evaluator_bundle.to_receipt_value(),
        "case_count": len(results),
        "skipped_case_count": 0,
        "result": "pass",
        "cases": results,
    }
    return receipt, canonical_json(receipt)


def authority_spec_bytes(
    binding: AuthorityVocabularyBinding,
    *,
    status: str = "accepted",
    revision: int = 2,
    revises: str = "sha256:" + "1" * 64,
) -> bytes:
    return spec_bytes(
        spec_id="SPEC-000",
        status=status,
        revision=revision,
        revises=revises,
        dependency_revisions="none",
        authority_path=binding.path,
        authority_digest=binding.digest,
        authority_version=binding.registry_version,
    )


def codes(
    base,
    candidate,
    *,
    authority_vocabulary: AuthorityVocabularyBinding | None = None,
) -> set[str]:
    return {
        finding.code
        for finding in validate_lifecycle(
            base, candidate, authority_vocabulary=authority_vocabulary
        )
    }


def promoted_codes(
    base,
    candidate,
    promoted_default,
    *,
    base_adrs=None,
    promoted_adrs=None,
) -> set[str]:
    return {
        finding.code
        for finding in validate_promoted_revision_predecessors(
            base,
            candidate,
            promoted_default,
            transition_base_adrs=base_adrs or {},
            promoted_default_adrs=promoted_adrs or {},
        )
    }


class AuthorityVocabularyLifecycleTests(unittest.TestCase):
    def test_package_imports_ignore_same_named_pythonpath_shadows(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            shadow_root = Path(temporary)
            for name in (
                "governance_policy.py",
                "skill_frontmatter.py",
                "validate_authority_contract.py",
                "validate_spec_lifecycle.py",
            ):
                (shadow_root / name).write_text(
                    'raise RuntimeError("SHADOW_MODULE_EXECUTED")\n',
                    encoding="utf-8",
                )
            environment = dict(os.environ)
            environment["PYTHONPATH"] = os.pathsep.join(
                (str(shadow_root), str(ROOT))
            )
            script = "\n".join(
                (
                    "from pathlib import Path",
                    "import researcher.scripts.validate_spec_lifecycle as lifecycle",
                    f"root = Path({str(ROOT)!r})",
                    "policy = lifecycle._authority_contract._load_constitution_for_conformance(root / 'governance/constitution.yaml')",
                    "assert policy.__class__.__module__ == 'researcher.scripts.governance_policy'",
                    "import researcher.scripts.build_inventory as inventory",
                    "import researcher.scripts.validate_governance as governance",
                    "expected = (root / 'researcher/scripts/validate_authority_contract.py').resolve()",
                    "assert Path(lifecycle._authority_contract.__file__).resolve() == expected",
                    "assert inventory.AuthorityVocabularyBinding.__module__ == 'researcher.scripts.validate_authority_contract'",
                    "assert governance.build_authority_evaluator_bundle.__module__ == 'researcher.scripts.validate_authority_contract'",
                    "assert governance.Constitution.__module__ == 'researcher.scripts.governance_policy'",
                )
            )
            completed = subprocess.run(
                [sys.executable, "-c", script],
                cwd=shadow_root,
                env=environment,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                completed.returncode,
                0,
                msg=f"stdout={completed.stdout}\nstderr={completed.stderr}",
            )

    def test_lifecycle_explicitly_reexports_authority_contract_api(self) -> None:
        for name in authority_contract.__all__:
            with self.subTest(name=name):
                self.assertIs(
                    getattr(spec_lifecycle, name),
                    getattr(authority_contract, name),
                )
        self.assertFalse(
            hasattr(authority_contract, "load_candidate_authority_vocabulary")
        )

    @staticmethod
    def parse_documents(
        registry: dict,
        fixture: dict,
        *,
        rebind_fixture: bool = True,
    ) -> AuthorityVocabularyBinding:
        registry = deepcopy(registry)
        fixture = deepcopy(fixture)
        fixture_bytes = canonical_json(fixture)
        if rebind_fixture:
            registry["fixture_manifest"]["digest"] = (
                f"sha256:{hashlib.sha256(fixture_bytes).hexdigest()}"
            )
        registry_bytes = canonical_json(registry)
        return parse_authority_vocabulary(
            registry_bytes,
            expected_digest=f"sha256:{hashlib.sha256(registry_bytes).hexdigest()}",
            expected_constitution_revision=2,
            expected_registry_version=2,
            fixture_manifest_bytes=fixture_bytes,
        )

    @staticmethod
    def first_entry(registry: dict) -> dict:
        return registry["entries"][0]

    @staticmethod
    def first_fixture(fixture: dict) -> dict:
        return fixture["entries"][0]

    def test_valid_revision_two_registry_and_manifest_pass(self) -> None:
        binding = parse_valid_authority()
        self.assertEqual(binding.constitution_revision, 2)
        self.assertEqual(binding.registry_version, 2)
        self.assertEqual(len(binding.entries), len(REQUIRED_AUTHORITY_PROFILES))
        self.assertIn(
            ("authorize_disaster_recovery", "event_journal", "SPEC-004"),
            binding.entries,
        )
        self.assertIn(
            ("initialize_repository_acceptance", "repository_acceptance", "SPEC-004"),
            binding.entries,
        )
        self.assertIn(
            ("manage_credential_binding", "credential_binding", "SPEC-024"),
            binding.entries,
        )
        self.assertIn(
            ("revoke_capability", "capability", "SPEC-024"),
            binding.entries,
        )
        self.assertIn(
            ("invoke_break_glass", "credential_binding", "SPEC-024"),
            binding.entries,
        )
        initialization = REQUIRED_AUTHORITY_PROFILES[
            ("initialize_repository_acceptance", "repository_acceptance")
        ]
        self.assertEqual(initialization.max_targets, 2)
        self.assertEqual(initialization.max_state_transitions, 2)
        seal = REQUIRED_AUTHORITY_PROFILES[
            ("seal_hidden_evaluation", "evaluation_epoch")
        ]
        self.assertEqual(seal.max_targets, 1)
        self.assertEqual(seal.max_state_transitions, 1)
        self.assertIn("immutable_seal_receipt", seal.max_effect_code)

    def test_carried_forward_catalog_is_closed_and_revision_two_owned(self) -> None:
        carried_forward = {
            ("amend_constitution", "constitution"),
            ("approve_weight_training", "weight_training"),
            ("attest_release", "candidate_artifact"),
            ("attest_release", "pull_request"),
            ("authorize_credential_destination", "credential_destination"),
            ("change_protected_surface", "evaluator_policy"),
            ("change_protected_surface", "hidden_evaluation"),
            ("change_protected_surface", "protected_surface"),
            ("change_protected_surface", "public_private_boundary"),
            ("evaluate", "candidate_artifact"),
            ("evaluate", "research_artifact"),
            ("execute_work", "candidate_artifact"),
            ("execute_work", "research_artifact"),
            ("expose_private_record", "private_record"),
            ("merge", "default_branch"),
            ("merge", "pull_request"),
            ("open_pull_request", "pull_request"),
            ("propose_change", "candidate_artifact"),
            ("propose_change", "research_artifact"),
            ("push_proposal", "proposal_branch"),
            ("research", "candidate_artifact"),
            ("research", "research_artifact"),
            ("respond_to_review", "pull_request"),
        }
        self.assertTrue(carried_forward <= set(REQUIRED_AUTHORITY_PROFILES))
        for pair in carried_forward:
            profile = REQUIRED_AUTHORITY_PROFILES[pair]
            self.assertEqual(profile.owner_spec, "SPEC-000")
            self.assertEqual(profile.dependency_floor, ("SPEC-000@2",))
        self.assertNotIn(
            ("publish_draft", "public_content_draft"),
            REQUIRED_AUTHORITY_PROFILES,
        )
        self.assertNotIn(("read", "public_repository"), REQUIRED_AUTHORITY_PROFILES)

    def test_repository_and_canary_guards_are_exact(self) -> None:
        expected_common = {"expected_target_version", "operation_id", "target_id"}
        cases = {
            ("initialize_repository_acceptance", "repository_acceptance"): {
                "accepted_commit",
                "accepted_tree",
                "accepted_pointer_absent",
                "git_observation",
                "inventory_digest",
                "organization_epoch",
                "repository_identity",
                "source_tree_digest",
            },
            ("reconcile_repository_acceptance", "repository_acceptance"): {
                "authority_set_digest",
                "base_commit",
                "default_branch",
                "expected_accepted_pointer",
                "expected_accepted_pointer_version",
                "first_parent_interval",
                "git_observation_receipts",
                "head_commit",
                "merge_actor",
                "merge_commit",
                "merge_tree",
                "provider_revisions",
                "pull_request",
                "repository_identity",
                "ruleset_digest",
            },
            ("attest_canary_health", "deployment_canary"): {
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
            },
        }
        for pair, target_fields in cases.items():
            with self.subTest(pair=pair):
                self.assertEqual(
                    set(REQUIRED_AUTHORITY_PROFILES[pair].decision_context_fields),
                    expected_common | target_fields,
                )

    def test_fixture_manifest_exercises_every_allowed_actor_and_guard(self) -> None:
        emergency = REQUIRED_AUTHORITY_PROFILES[
            ("emergency_disable", "emergency_control")
        ]
        cases = expected_authority_fixture_cases(emergency)
        names = {str(case["case"]) for case in cases}
        for actor in emergency.actor_classes:
            self.assertIn(f"allow__{actor}", names)
        for field in emergency.decision_context_fields:
            self.assertIn(f"missing_guard__{field}", names)
        self.assertTrue(
            {
                "below_dependency_floor",
                "owner_inactive",
                "wrong_actor",
                "widened_effect",
                "wrong_grant",
            }
            <= names
        )

    def test_catalog_boundary_fixtures_cover_denied_append_and_policy_only_read(
        self,
    ) -> None:
        cases = {
            str(case["case"]): case
            for case in expected_authority_catalog_boundary_cases()
        }
        expected_read_resources = {
            "candidate_artifact",
            "public_content_draft",
            "public_repository",
            "pull_request",
            "research_artifact",
        }
        self.assertEqual(
            {
                resource
                for action, resource in POLICY_ONLY_READ_PROFILES
                if action == "read"
            },
            expected_read_resources,
        )
        for resource in expected_read_resources:
            profile = POLICY_ONLY_READ_PROFILES[("read", resource)]
            for actor in profile.actor_classes:
                name = f"read_{resource}__allow__{actor}"
                self.assertEqual(cases[name]["expected_registry_decision"], "non_event")
                self.assertEqual(cases[name]["expected_decision"], "allow")
            self.assertEqual(
                cases[f"read_{resource}__wrong_actor"]["expected_decision"],
                "deny",
            )
            self.assertEqual(
                cases[f"read_{resource}__event_append_denied"]["expected_decision"],
                "deny",
            )
        self.assertEqual(
            cases["read_unknown_resource_denied"]["expected_decision"], "deny"
        )
        for name in (
            "legacy_publish_draft_denied",
            "noncatalog_event_append_denied",
        ):
            self.assertEqual(cases[name]["expected_decision"], "deny")

    def test_generic_revision_two_fails_and_bound_revision_two_passes(self) -> None:
        base_bytes = spec_bytes(
            spec_id="SPEC-000",
            status="amended",
            lifecycle_decision="ADR-0007",
            replacement="SPEC-000@2",
        )
        base = revision_at("docs/specs/SPEC-000-fixture.md", base_bytes)
        revises = f"sha256:{hashlib.sha256(base_bytes).hexdigest()}"
        generic = revision_at(
            "docs/specs/SPEC-000-fixture.md",
            spec_bytes(spec_id="SPEC-000", revision=2, revises=revises),
        )
        self.assertIn(
            "SPEC_AUTHORITY_VOCABULARY_INVALID",
            codes({base.spec_id: base}, {generic.spec_id: generic}),
        )

        binding = parse_valid_authority()
        bound = revision_at(
            "docs/specs/SPEC-000-fixture.md",
            authority_spec_bytes(
                binding,
                status="draft",
                revision=2,
                revises=revises,
            ),
        )
        self.assertEqual(
            validate_lifecycle(
                {base.spec_id: base},
                {bound.spec_id: bound},
                authority_vocabulary=binding,
            ),
            [],
        )

    def test_registry_is_strict_duplicate_free_integer_only_canonical_json(
        self,
    ) -> None:
        registry, _fixture, registry_bytes, fixture_bytes = authority_documents()
        duplicate = registry_bytes.replace(
            b'{\n  "constitution_revision"',
            b'{\n  "kind": "AuthorityVocabularyRegistry",\n  "constitution_revision"',
            1,
        )
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            parse_authority_vocabulary(
                duplicate,
                expected_digest=f"sha256:{hashlib.sha256(duplicate).hexdigest()}",
                expected_constitution_revision=2,
                expected_registry_version=2,
                fixture_manifest_bytes=fixture_bytes,
            )

        floating = registry_bytes.replace(
            b'"registry_version": 2', b'"registry_version": 2.0'
        )
        with self.assertRaisesRegex(ValueError, "floating point is forbidden"):
            parse_authority_vocabulary(
                floating,
                expected_digest=f"sha256:{hashlib.sha256(floating).hexdigest()}",
                expected_constitution_revision=2,
                expected_registry_version=2,
                fixture_manifest_bytes=fixture_bytes,
            )

        noncanonical = json.dumps(registry, sort_keys=True).encode("utf-8")
        with self.assertRaisesRegex(
            ValueError, "canonical sorted pretty serialization"
        ):
            parse_authority_vocabulary(
                noncanonical,
                expected_digest=f"sha256:{hashlib.sha256(noncanonical).hexdigest()}",
                expected_constitution_revision=2,
                expected_registry_version=2,
                fixture_manifest_bytes=fixture_bytes,
            )

    def test_registry_revision_and_version_are_spec_revision_bound(self) -> None:
        registry, fixture, _registry_bytes, _fixture_bytes = authority_documents()
        for field, value in (
            ("constitution_revision", 3),
            ("registry_version", 3),
        ):
            mutated = deepcopy(registry)
            mutated[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.parse_documents(mutated, fixture)

    def test_registry_semantic_profile_mutations_fail(self) -> None:
        registry, fixture, _registry_bytes, _fixture_bytes = authority_documents()
        mutations = {
            "owner": lambda entry: entry.__setitem__("owner_spec", "SPEC-999"),
            "actor": lambda entry: entry.__setitem__(
                "actor_classes",
                ["human_maintainer"]
                if entry["actor_classes"] != ["human_maintainer"]
                else ["research_agent"],
            ),
            "effect": lambda entry: entry["max_effect"].__setitem__("max_targets", 2),
            "guard": lambda entry: entry.__setitem__(
                "decision_context_fields", entry["decision_context_fields"][1:]
            ),
            "grant": lambda entry: entry.__setitem__(
                "grant_operation", "unauthorized_operation"
            ),
            "dependency": lambda entry: entry.__setitem__("dependency_floor", []),
            "arbitrary_pair": lambda entry: entry.__setitem__(
                "action", "invent_authority"
            ),
        }
        for name, mutate in mutations.items():
            mutated = deepcopy(registry)
            mutate(self.first_entry(mutated))
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.parse_documents(mutated, fixture)

    def test_fixture_semantic_mutations_fail(self) -> None:
        registry, fixture, _registry_bytes, _fixture_bytes = authority_documents()
        profile = REQUIRED_AUTHORITY_PROFILES[
            (
                self.first_fixture(fixture)["action"],
                self.first_fixture(fixture)["resource"],
            )
        ]

        def case(document: dict, name: str) -> dict:
            return next(
                item
                for item in self.first_fixture(document)["cases"]
                if item["case"] == name or item["case"].startswith(name + "__")
            )

        mutations = {
            "wrong_actor": lambda document: case(document, "wrong_actor").__setitem__(
                "actor_class", profile.actor_classes[0]
            ),
            "missing_guard": lambda document: case(
                document, "missing_guard"
            ).__setitem__(
                "decision_context_fields", list(profile.decision_context_fields)
            ),
            "widened_effect": lambda document: case(
                document, "widened_effect"
            ).__setitem__("effect", profile.max_effect),
            "wrong_grant": lambda document: case(document, "wrong_grant").__setitem__(
                "grant_operation", profile.grant_operation
            ),
            "below_dependency_floor": lambda document: case(
                document, "below_dependency_floor"
            )["dependency_evidence"][0].__setitem__(
                "revision", int(profile.dependency_floor[0].split("@")[1])
            ),
            "owner_inactive": lambda document: case(document, "owner_inactive")[
                "dependency_evidence"
            ][0].__setitem__("status", "operational"),
        }
        for name, mutate in mutations.items():
            mutated = deepcopy(fixture)
            mutate(mutated)
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.parse_documents(registry, mutated)

    def test_missing_duplicate_and_detached_fixture_entries_fail(self) -> None:
        registry, fixture, _registry_bytes, _fixture_bytes = authority_documents()
        variants: dict[str, dict] = {}
        missing = deepcopy(fixture)
        missing["entries"].pop()
        variants["missing"] = missing
        duplicate = deepcopy(fixture)
        duplicate["entries"].append(deepcopy(duplicate["entries"][-1]))
        variants["duplicate"] = duplicate
        detached = deepcopy(fixture)
        unknown = deepcopy(detached["entries"][-1])
        unknown["action"] = "invent_authority"
        unknown["resource"] = "unknown_resource"
        detached["entries"].append(unknown)
        variants["detached"] = detached
        missing_case = deepcopy(fixture)
        missing_case["entries"][0]["cases"].pop()
        variants["missing_case"] = missing_case
        duplicate_case = deepcopy(fixture)
        duplicate_case["entries"][0]["cases"].append(
            deepcopy(duplicate_case["entries"][0]["cases"][-1])
        )
        variants["duplicate_case"] = duplicate_case
        for name, mutated in variants.items():
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.parse_documents(registry, mutated)

    def test_registry_fixture_pointer_path_digest_and_version_mutations_fail(
        self,
    ) -> None:
        registry, fixture, _registry_bytes, _fixture_bytes = authority_documents()
        for field, value, rebind in (
            ("path", "governance/fixtures/detached.json", True),
            ("digest", "sha256:" + "0" * 64, False),
            ("version", 3, True),
        ):
            mutated = deepcopy(registry)
            mutated["fixture_manifest"][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.parse_documents(mutated, fixture, rebind_fixture=rebind)

    def test_spec_metadata_path_digest_and_version_bind_canonical_registry(
        self,
    ) -> None:
        _registry, _fixture, registry_bytes, fixture_bytes = authority_documents()
        digest = f"sha256:{hashlib.sha256(registry_bytes).hexdigest()}"
        good_metadata = {
            "Authority vocabulary": AUTHORITY_VOCABULARY_PATH,
            "Authority vocabulary digest": digest,
            "Authority vocabulary version": "2",
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "governance" / "fixtures").mkdir(parents=True)
            (root / AUTHORITY_VOCABULARY_PATH).write_bytes(registry_bytes)
            (root / AUTHORITY_FIXTURE_MANIFEST_PATH).write_bytes(fixture_bytes)
            self.assertEqual(
                load_authority_vocabulary(
                    root, good_metadata, expected_constitution_revision=2
                ).digest,
                digest,
            )
            mutations = {
                "path": ("Authority vocabulary", "governance/arbitrary.json"),
                "digest": ("Authority vocabulary digest", "sha256:" + "0" * 64),
                "version": ("Authority vocabulary version", "3"),
                "noncanonical_version": ("Authority vocabulary version", "02"),
            }
            for name, (field, value) in mutations.items():
                metadata = dict(good_metadata)
                metadata[field] = value
                with self.subTest(name=name), self.assertRaises(ValueError):
                    load_authority_vocabulary(
                        root, metadata, expected_constitution_revision=2
                    )

    def test_revision_one_rejects_dangling_canonical_authority_symlinks(self) -> None:
        authority_spec = revision_at(
            "docs/specs/SPEC-000-fixture.md",
            spec_bytes(
                spec_id="SPEC-000",
                status="accepted",
                revision=1,
                revises="none",
                dependency_revisions="none",
            ),
        )
        for relative in (
            AUTHORITY_VOCABULARY_PATH,
            AUTHORITY_FIXTURE_MANIFEST_PATH,
        ):
            with (
                self.subTest(relative=relative),
                tempfile.TemporaryDirectory() as directory,
            ):
                root = Path(directory)
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.symlink_to(root / "missing-authority-artifact.json")
                with self.assertRaisesRegex(ValueError, "Authority vocabulary"):
                    load_candidate_authority_vocabulary(
                        root,
                        {authority_spec.spec_id: authority_spec},
                    )

    def test_combined_registry_and_policy_boundary_executes_every_case(self) -> None:
        registry = parse_valid_authority()
        constitution = conforming_constitution()
        calls: list[tuple[str, str, str]] = []

        class RecordingConstitution:
            def decide(self, actor, action, resource, context):
                calls.append((actor, action, resource))
                return constitution.decide(actor, action, resource, context)

        results = authority_policy_case_results(registry, RecordingConstitution())
        self.assertEqual(len(results), len(registry.fixture_cases))
        self.assertEqual(len(calls), len(registry.fixture_cases))
        self.assertTrue(
            all(
                result["actual_decision"] == result["expected_decision"]
                and result["policy_decision"] == result["expected_policy_decision"]
                and result["registry_decision"] == result["expected_registry_decision"]
                for result in results
            )
        )
        policy_reasons = {str(result["reason_code"]) for result in results}
        registry_reasons = {str(result["registry_reason_code"]) for result in results}
        self.assertTrue(
            {
                "REGISTRY_ACTOR_DENY",
                "REGISTRY_DEPENDENCY_DENY",
                "REGISTRY_GUARD_DENY",
                "REGISTRY_EFFECT_DENY",
                "REGISTRY_GRANT_DENY",
            }
            <= registry_reasons
        )
        self.assertIn("AUTHORITY_PROFILE_ALLOWED", policy_reasons)

    def test_unconditional_allow_policy_cannot_be_masked_by_registry_denials(
        self,
    ) -> None:
        registry = parse_valid_authority()
        base_policy = conforming_constitution()
        document = deepcopy(base_policy.document)
        profile = REQUIRED_AUTHORITY_PROFILES[("query_status", "status_projection")]
        document["rules"] = [
            {
                "rule_id": "unconditional-status-query",
                "effect": "allow",
                "actors": [profile.actor_classes[0]],
                "actions": ["query_status"],
                "resources": ["status_projection"],
                "conditions": [],
                "reason_code": "UNCONDITIONAL_STATUS_QUERY",
            }
        ]
        policy = Constitution(
            document,
            "b" * 64,
            Path(AUTHORITY_CONSTITUTION_POLICY_PATH),
        )
        component_bytes = evaluator_component_bytes()
        _receipt, receipt_bytes = authority_conformance_document(
            registry, policy, component_bytes
        )
        with self.assertRaisesRegex(
            ValueError, "does not implement the authority registry"
        ):
            parse_authority_policy_conformance(
                receipt_bytes,
                registry=registry,
                constitution=policy,
                evaluator_component_bytes=component_bytes,
            )

    def test_structural_closure_rejects_dormant_noncatalog_and_weaker_allow_rules(
        self,
    ) -> None:
        registry = parse_valid_authority()
        component_bytes = evaluator_component_bytes()
        retained_legacy = constitution_with_added_allow_rule(
            {
                "rule_id": "retained-legacy-publish-backdoor",
                "effect": "allow",
                "actors": ["research_proposer"],
                "actions": ["publish_draft"],
                "resources": ["public_content_draft"],
                "conditions": [
                    {
                        "key": "automated_identity_disclosed",
                        "operator": "equals",
                        "value": False,
                    }
                ],
                "reason_code": "RETAINED_LEGACY_ALLOW",
            },
            actions=("publish_draft",),
            resources=("public_content_draft",),
        )

        pair = ("query_status", "status_projection")
        profile = REQUIRED_AUTHORITY_PROFILES[pair]
        alternate_conditions = list(expected_authority_policy_conditions(profile))
        target_condition = next(
            condition
            for condition in alternate_conditions
            if condition["key"] == "target_id"
        )
        target_condition.clear()
        target_condition.update(
            {"key": "target_id", "operator": "equals", "value": False}
        )
        alternate_guard = constitution_with_added_allow_rule(
            {
                "rule_id": "dormant-alternate-guard-backdoor",
                "effect": "allow",
                "actors": [profile.actor_classes[0]],
                "actions": [pair[0]],
                "resources": [pair[1]],
                "conditions": alternate_conditions,
                "reason_code": "ALTERNATE_GUARD_ALLOW",
            }
        )

        for name, policy, message in (
            ("retained_legacy", retained_legacy, "noncatalog pair"),
            ("alternate_guard", alternate_guard, "noncanonical predicate"),
        ):
            results = authority_policy_case_results(registry, policy)
            self.assertTrue(
                all(
                    result["actual_decision"] == result["expected_decision"]
                    and result["policy_decision"] == result["expected_policy_decision"]
                    and result["registry_decision"]
                    == result["expected_registry_decision"]
                    for result in results
                ),
                f"{name} must remain dormant in finite fixtures",
            )
            _receipt, receipt_bytes = authority_conformance_document(
                registry, policy, component_bytes
            )
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, message):
                parse_authority_policy_conformance(
                    receipt_bytes,
                    registry=registry,
                    constitution=policy,
                    evaluator_component_bytes=component_bytes,
                )

    def test_valid_policy_conformance_receipt_is_recomputed_and_bound(self) -> None:
        registry = parse_valid_authority()
        constitution = conforming_constitution()
        component_bytes = evaluator_component_bytes()
        _receipt, receipt_bytes = authority_conformance_document(
            registry, constitution, component_bytes
        )
        binding = parse_authority_policy_conformance(
            receipt_bytes,
            registry=registry,
            constitution=constitution,
            evaluator_component_bytes=component_bytes,
        )
        self.assertEqual(binding.case_count, len(registry.fixture_cases))
        self.assertEqual(binding.registry_digest, registry.digest)
        self.assertEqual(
            binding.fixture_manifest_digest, registry.fixture_manifest_digest
        )
        self.assertEqual(
            binding.validator_bundle_algorithm,
            AUTHORITY_VALIDATOR_BUNDLE_ALGORITHM,
        )
        self.assertEqual(
            binding.validator_bundle_version,
            AUTHORITY_EVALUATOR_BUNDLE_VERSION,
        )
        self.assertEqual(
            tuple(component.path for component in binding.validator_bundle_components),
            AUTHORITY_EVALUATOR_COMPONENT_PATHS,
        )

    def test_policy_conformance_rejects_an_unbound_constitution_wrapper(self) -> None:
        registry = parse_valid_authority()
        constitution = conforming_constitution()
        component_bytes = evaluator_component_bytes()
        _receipt, receipt_bytes = authority_conformance_document(
            registry,
            constitution,
            component_bytes,
        )
        wrapper = SimpleNamespace(
            digest=constitution.digest,
            version=constitution.version,
            rules=constitution.rules,
            decide=constitution.decide,
        )

        with self.assertRaisesRegex(ValueError, "canonical Constitution evaluator"):
            parse_authority_policy_conformance(
                receipt_bytes,
                registry=registry,
                constitution=wrapper,
                evaluator_component_bytes=component_bytes,
            )

    def test_evaluator_bundle_is_exact_ordered_and_mutation_bound(self) -> None:
        component_bytes = evaluator_component_bytes()
        bundle = build_authority_evaluator_bundle(component_bytes)
        self.assertIsInstance(bundle, AuthorityEvaluatorBundleBinding)
        self.assertEqual(bundle.algorithm, AUTHORITY_VALIDATOR_BUNDLE_ALGORITHM)
        self.assertEqual(bundle.version, AUTHORITY_EVALUATOR_BUNDLE_VERSION)
        self.assertEqual(
            bundle.digest,
            f"sha256:{hashlib.sha256(canonical_json(bundle.to_payload())).hexdigest()}",
        )
        self.assertEqual(
            build_authority_evaluator_bundle(dict(component_bytes)),
            bundle,
        )
        self.assertEqual(
            build_authority_evaluator_bundle(tuple(reversed(component_bytes))),
            bundle,
        )
        reverse_mapping = dict(reversed(component_bytes))
        self.assertEqual(build_authority_evaluator_bundle(reverse_mapping), bundle)
        self.assertEqual(
            set(bundle.to_receipt_value()),
            {"algorithm", "version", "components", "digest"},
        )

        invalid_component_sets = {
            "missing": component_bytes[:-1],
            "extra": component_bytes + (("researcher/scripts/extra.py", b"extra"),),
            "duplicate": (component_bytes[0], component_bytes[0]),
            "relocated": (
                ("researcher/scripts/relocated.py", component_bytes[0][1]),
                component_bytes[1],
            ),
        }
        for name, invalid in invalid_component_sets.items():
            with self.subTest(name=name), self.assertRaises(ValueError):
                build_authority_evaluator_bundle(invalid)

        mutated_component_bytes = (
            (component_bytes[0][0], component_bytes[0][1] + b" mutated"),
            component_bytes[1],
        )
        mutated_bundle = build_authority_evaluator_bundle(mutated_component_bytes)
        self.assertNotEqual(mutated_bundle.digest, bundle.digest)

        registry = parse_valid_authority()
        constitution = conforming_constitution()
        _receipt, receipt_bytes = authority_conformance_document(
            registry, constitution, component_bytes
        )
        with self.assertRaisesRegex(ValueError, "executing evaluator"):
            parse_authority_policy_conformance(
                receipt_bytes,
                registry=registry,
                constitution=constitution,
                evaluator_component_bytes=mutated_component_bytes,
            )

    def test_policy_conformance_receipt_mutations_fail_closed(self) -> None:
        registry = parse_valid_authority()
        constitution = conforming_constitution()
        component_bytes = evaluator_component_bytes()
        receipt, _receipt_bytes = authority_conformance_document(
            registry, constitution, component_bytes
        )
        mutations = {
            "policy_digest": lambda value: value["constitution_policy"].__setitem__(
                "digest", "sha256:" + "0" * 64
            ),
            "registry_digest": lambda value: value.__setitem__(
                "registry_digest", "sha256:" + "0" * 64
            ),
            "fixture_digest": lambda value: value.__setitem__(
                "fixture_manifest_digest", "sha256:" + "0" * 64
            ),
            "validator_bundle_digest": lambda value: value[
                "validator_bundle"
            ].__setitem__("digest", "sha256:" + "0" * 64),
            "validator_bundle_version": lambda value: value[
                "validator_bundle"
            ].__setitem__("version", "9.9.9"),
            "validator_bundle_algorithm": lambda value: value[
                "validator_bundle"
            ].__setitem__("algorithm", "sha256-other-v1"),
            "validator_component_digest": lambda value: value["validator_bundle"][
                "components"
            ][0].__setitem__("digest", "sha256:" + "0" * 64),
            "validator_components_reordered": lambda value: value["validator_bundle"][
                "components"
            ].reverse(),
            "case_count": lambda value: value.__setitem__(
                "case_count", value["case_count"] - 1
            ),
            "skipped": lambda value: value.__setitem__("skipped_case_count", 1),
            "result": lambda value: value.__setitem__("result", "partial"),
            "missing_case": lambda value: value["cases"].pop(),
            "changed_result": lambda value: value["cases"][0].__setitem__(
                "actual_decision", "deny"
            ),
        }
        for name, mutate in mutations.items():
            candidate = deepcopy(receipt)
            mutate(candidate)
            candidate_bytes = canonical_json(candidate)
            with self.subTest(name=name), self.assertRaises(ValueError):
                parse_authority_policy_conformance(
                    candidate_bytes,
                    registry=registry,
                    constitution=constitution,
                    evaluator_component_bytes=component_bytes,
                )

    def test_unchanged_constitution_cannot_unlock_implementation(self) -> None:
        registry = parse_valid_authority()
        constitution = Constitution.load(ROOT / AUTHORITY_CONSTITUTION_POLICY_PATH)
        component_bytes = evaluator_component_bytes()
        _receipt, receipt_bytes = authority_conformance_document(
            registry, constitution, component_bytes
        )
        with self.assertRaisesRegex(
            ValueError, "does not implement the authority registry"
        ):
            parse_authority_policy_conformance(
                receipt_bytes,
                registry=registry,
                constitution=constitution,
                evaluator_component_bytes=component_bytes,
            )

    def test_implemented_stages_require_validated_policy_conformance(self) -> None:
        registry = parse_valid_authority()
        authority_base = revision_at(
            "docs/specs/SPEC-000-fixture.md",
            authority_spec_bytes(registry, status="accepted"),
        )
        authority_implemented = revision_at(
            "docs/specs/SPEC-000-fixture.md",
            authority_spec_bytes(registry, status="implemented"),
        )
        self.assertIn(
            "SPEC_AUTHORITY_POLICY_CONFORMANCE_REQUIRED",
            codes(
                {authority_base.spec_id: authority_base},
                {authority_implemented.spec_id: authority_implemented},
                authority_vocabulary=registry,
            ),
        )

        constitution = conforming_constitution()
        component_bytes = evaluator_component_bytes()
        _receipt, receipt_bytes = authority_conformance_document(
            registry, constitution, component_bytes
        )
        conformance = parse_authority_policy_conformance(
            receipt_bytes,
            registry=registry,
            constitution=constitution,
            evaluator_component_bytes=component_bytes,
        )
        conforming_registry = replace(registry, policy_conformance=conformance)
        self.assertIn(
            "SPEC_AUTHORITY_POLICY_CONFORMANCE_PREMATURE",
            codes(
                {authority_base.spec_id: authority_base},
                {authority_base.spec_id: authority_base},
                authority_vocabulary=conforming_registry,
            ),
        )
        spec_base = revision(
            spec_bytes(
                status="accepted",
                depends_on="SPEC-000",
                dependency_revisions="SPEC-000@2",
            )
        )
        spec_implemented = revision(
            spec_bytes(
                status="implemented",
                depends_on="SPEC-000",
                dependency_revisions="SPEC-000@2",
            )
        )
        base = {
            authority_base.spec_id: authority_base,
            spec_base.spec_id: spec_base,
        }
        candidate = {
            authority_implemented.spec_id: authority_implemented,
            spec_implemented.spec_id: spec_implemented,
        }
        self.assertEqual(
            validate_lifecycle(
                base,
                candidate,
                authority_vocabulary=conforming_registry,
            ),
            [],
        )
        forged_receipt = replace(
            conformance,
            case_count=conformance.case_count - 1,
        )
        forged_registry = replace(
            registry,
            policy_conformance=forged_receipt,
        )
        self.assertIn(
            "SPEC_AUTHORITY_POLICY_CONFORMANCE_REQUIRED",
            codes(
                base,
                candidate,
                authority_vocabulary=forged_registry,
            ),
        )


class SpecificationLifecycleTests(unittest.TestCase):
    def test_new_specification_must_enter_as_draft_revision_one(self) -> None:
        candidate = revision(spec_bytes(status="accepted"))
        self.assertIn(
            "INVALID_INITIAL_SPEC_REVISION",
            codes({}, {candidate.spec_id: candidate}),
        )

    def test_spec_026_revision_one_activation_is_deferred(self) -> None:
        candidate = revision(spec_bytes(spec_id="SPEC-026", activation="active"))
        self.assertIn(
            "INVALID_SPEC_ACTIVATION",
            codes({}, {candidate.spec_id: candidate}),
        )

    def test_spec_026_activation_change_requires_new_revision(self) -> None:
        base = revision(spec_bytes(spec_id="SPEC-026", activation="deferred"))
        candidate = revision(spec_bytes(spec_id="SPEC-026", activation="active"))
        self.assertIn(
            "SPEC_ACTIVATION_REVISION_REQUIRED",
            codes({base.spec_id: base}, {candidate.spec_id: candidate}),
        )

    def test_status_only_forward_transition_is_valid(self) -> None:
        base = revision(spec_bytes(spec_id="SPEC-003", status="draft"))
        candidate = revision(
            spec_bytes(
                spec_id="SPEC-003",
                status="architecture_reviewed",
                dependency_revisions="none",
            )
        )
        self.assertEqual(
            validate_lifecycle({base.spec_id: base}, {candidate.spec_id: candidate}), []
        )

    def test_wave_one_cannot_freeze_pre_registry_constitution(self) -> None:
        base = revision(spec_bytes(status="draft", depends_on="SPEC-000"))
        candidate = revision(
            spec_bytes(
                status="architecture_reviewed",
                depends_on="SPEC-000",
                dependency_revisions="SPEC-000@1",
            )
        )
        constitution = parse_spec_revision(
            "docs/specs/SPEC-000-fixture.md",
            spec_bytes(
                spec_id="SPEC-000",
                status="implemented",
                dependency_revisions="none",
            ),
            allow_legacy=False,
        )
        self.assertIn(
            "SPEC_AUTHORITY_VOCABULARY_NOT_READY",
            codes(
                {base.spec_id: base, constitution.spec_id: constitution},
                {candidate.spec_id: candidate, constitution.spec_id: constitution},
            ),
        )

        authority_binding = parse_valid_authority()
        constitution_v2 = parse_spec_revision(
            "docs/specs/SPEC-000-fixture.md",
            authority_spec_bytes(authority_binding),
            allow_legacy=False,
        )
        candidate_v2 = revision(
            spec_bytes(
                status="architecture_reviewed",
                depends_on="SPEC-000",
                dependency_revisions="SPEC-000@2",
            )
        )
        self.assertEqual(
            validate_lifecycle(
                {base.spec_id: base, constitution_v2.spec_id: constitution_v2},
                {
                    candidate_v2.spec_id: candidate_v2,
                    constitution_v2.spec_id: constitution_v2,
                },
                authority_vocabulary=authority_binding,
            ),
            [],
        )

    def test_forward_transition_requires_each_dependency_at_same_stage(self) -> None:
        base = revision(
            spec_bytes(
                status="architecture_reviewed",
                depends_on="SPEC-003",
                dependency_revisions="SPEC-003@1",
            )
        )
        candidate = revision(
            spec_bytes(
                status="accepted",
                depends_on="SPEC-003",
                dependency_revisions="SPEC-003@1",
            )
        )
        dependency = parse_spec_revision(
            "docs/specs/SPEC-003-fixture.md",
            spec_bytes(
                spec_id="SPEC-003",
                status="architecture_reviewed",
                dependency_revisions="none",
            ),
            allow_legacy=False,
        )
        authority_binding = parse_valid_authority()
        authority = parse_spec_revision(
            "docs/specs/SPEC-000-fixture.md",
            authority_spec_bytes(authority_binding),
            allow_legacy=False,
        )
        result = codes(
            {
                base.spec_id: base,
                dependency.spec_id: dependency,
                authority.spec_id: authority,
            },
            {
                candidate.spec_id: candidate,
                dependency.spec_id: dependency,
                authority.spec_id: authority,
            },
            authority_vocabulary=authority_binding,
        )
        self.assertIn("SPEC_DEPENDENCY_NOT_READY", result)

        accepted_dependency = parse_spec_revision(
            "docs/specs/SPEC-003-fixture.md",
            spec_bytes(
                spec_id="SPEC-003",
                status="accepted",
                dependency_revisions="none",
            ),
            allow_legacy=False,
        )
        self.assertEqual(
            validate_lifecycle(
                {
                    base.spec_id: base,
                    dependency.spec_id: dependency,
                    authority.spec_id: authority,
                },
                {
                    candidate.spec_id: candidate,
                    accepted_dependency.spec_id: accepted_dependency,
                    authority.spec_id: authority,
                },
                authority_vocabulary=authority_binding,
            ),
            [],
        )

    def test_terminal_dependency_does_not_satisfy_stage_floor(self) -> None:
        base = revision(spec_bytes(status="draft", depends_on="SPEC-003"))
        candidate = revision(
            spec_bytes(
                status="architecture_reviewed",
                depends_on="SPEC-003",
                dependency_revisions="SPEC-003@1",
            )
        )
        dependency = parse_spec_revision(
            "docs/specs/SPEC-003-fixture.md",
            spec_bytes(
                spec_id="SPEC-003",
                status="retired",
                lifecycle_decision="ADR-0007",
            ),
            allow_legacy=False,
        )
        self.assertIn(
            "SPEC_DEPENDENCY_NOT_READY",
            codes(
                {base.spec_id: base, dependency.spec_id: dependency},
                {candidate.spec_id: candidate, dependency.spec_id: dependency},
            ),
        )

    def test_dependency_revision_binding_must_match_candidate_revision(self) -> None:
        base = revision(spec_bytes(status="draft", depends_on="SPEC-003"))
        candidate = revision(
            spec_bytes(
                status="architecture_reviewed",
                depends_on="SPEC-003",
                dependency_revisions="SPEC-003@1",
            )
        )
        dependency = parse_spec_revision(
            "docs/specs/SPEC-003-fixture.md",
            spec_bytes(
                spec_id="SPEC-003",
                status="architecture_reviewed",
                revision=2,
                revises="sha256:" + "0" * 64,
                dependency_revisions="none",
            ),
            allow_legacy=False,
        )
        self.assertIn(
            "SPEC_DEPENDENCY_REVISION_MISMATCH",
            codes(
                {base.spec_id: base, dependency.spec_id: dependency},
                {candidate.spec_id: candidate, dependency.spec_id: dependency},
            ),
        )

    def test_skipped_status_is_rejected(self) -> None:
        base = revision(spec_bytes(status="draft"))
        candidate = revision(spec_bytes(status="accepted"))
        self.assertIn(
            "INVALID_SPEC_STATUS_TRANSITION",
            codes({base.spec_id: base}, {candidate.spec_id: candidate}),
        )

    def test_architecture_reviewed_revision_can_enter_amendment_state(self) -> None:
        base = revision(spec_bytes(status="architecture_reviewed"))
        candidate = revision(
            spec_bytes(
                status="amended",
                lifecycle_decision="ADR-0007",
                replacement="SPEC-004@2",
            )
        )
        self.assertEqual(
            validate_lifecycle({base.spec_id: base}, {candidate.spec_id: candidate}), []
        )

    def test_terminal_transition_rejects_wrong_replacement_identity(self) -> None:
        base = revision(spec_bytes(status="architecture_reviewed"))
        candidate = revision(
            spec_bytes(
                status="superseded",
                lifecycle_decision="ADR-0007",
                replacement="SPEC-999@9",
            )
        )
        self.assertIn(
            "SPEC_REPLACEMENT_MISMATCH",
            codes({base.spec_id: base}, {candidate.spec_id: candidate}),
        )

    def test_status_transition_cannot_change_contract(self) -> None:
        base = revision(spec_bytes(status="draft", body="A"))
        candidate = revision(spec_bytes(status="architecture_reviewed", body="B"))
        self.assertIn(
            "SPEC_STATUS_TRANSITION_NOT_ISOLATED",
            codes({base.spec_id: base}, {candidate.spec_id: candidate}),
        )

    def test_line_ending_rewrite_changes_the_contract(self) -> None:
        base = revision(spec_bytes(status="implemented", dependency_revisions="none"))
        candidate = revision(
            spec_bytes(status="verified", dependency_revisions="none").replace(
                b"\n", b"\r\n"
            )
        )
        self.assertIn(
            "SPEC_STATUS_TRANSITION_NOT_ISOLATED",
            codes({base.spec_id: base}, {candidate.spec_id: candidate}),
        )

    def test_noncanonical_mutable_metadata_whitespace_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "canonical 'Key: value'"):
            revision(
                spec_bytes(status="accepted", dependency_revisions="none").replace(
                    b"Status: accepted\n", b"Status:    accepted   \n"
                )
            )

    def test_metadata_reordering_changes_the_contract(self) -> None:
        base_bytes = spec_bytes(status="implemented", dependency_revisions="none")
        candidate_bytes = spec_bytes(status="verified", dependency_revisions="none")
        candidate_bytes = candidate_bytes.replace(
            b"Classification: split\nOwners: test agent; human maintainer\n",
            b"Owners: test agent; human maintainer\nClassification: split\n",
        )
        base = revision(base_bytes)
        candidate = revision(candidate_bytes)
        self.assertIn(
            "SPEC_STATUS_TRANSITION_NOT_ISOLATED",
            codes({base.spec_id: base}, {candidate.spec_id: candidate}),
        )

    def test_draft_contract_can_change_in_place(self) -> None:
        base = revision(spec_bytes(status="draft", body="A"))
        candidate = revision(spec_bytes(status="draft", body="B"))
        self.assertEqual(
            validate_lifecycle({base.spec_id: base}, {candidate.spec_id: candidate}), []
        )

    def test_accepted_contract_change_requires_new_revision(self) -> None:
        base = revision(spec_bytes(status="accepted", body="A"))
        candidate = revision(spec_bytes(status="accepted", body="B"))
        self.assertIn(
            "SPEC_REVISION_REQUIRED",
            codes({base.spec_id: base}, {candidate.spec_id: candidate}),
        )

    def test_new_revision_binds_exact_base_bytes_and_restarts_at_draft(self) -> None:
        base_bytes = spec_bytes(
            status="amended",
            body="A",
            lifecycle_decision="ADR-0007",
            replacement="SPEC-004@2",
        )
        base = revision(base_bytes)
        digest = f"sha256:{hashlib.sha256(base_bytes).hexdigest()}"
        candidate = revision(
            spec_bytes(status="draft", revision=2, revises=digest, body="B")
        )
        self.assertEqual(
            validate_lifecycle({base.spec_id: base}, {candidate.spec_id: candidate}), []
        )
        decision = terminal_adr()
        self.assertEqual(
            validate_promoted_revision_predecessors(
                {base.spec_id: base},
                {candidate.spec_id: candidate},
                {base.spec_id: base},
                transition_base_adrs={decision.adr_id: decision},
                promoted_default_adrs={decision.adr_id: decision},
            ),
            [],
        )

    def test_new_revision_requires_exact_predecessor_on_promoted_default(self) -> None:
        base_bytes = spec_bytes(
            status="amended",
            body="A",
            lifecycle_decision="ADR-0007",
            replacement="SPEC-004@2",
        )
        base = revision(base_bytes)
        digest = f"sha256:{hashlib.sha256(base_bytes).hexdigest()}"
        candidate = revision(
            spec_bytes(status="draft", revision=2, revises=digest, body="B")
        )
        self.assertEqual(
            promoted_codes(
                {base.spec_id: base},
                {candidate.spec_id: candidate},
                {},
            ),
            {"SPEC_REVISION_PREDECESSOR_NOT_PROMOTED"},
        )

        for malformed_promoted in (
            replace(base, path="docs/specs/SPEC-004-relocated.md"),
            replace(base, revision=99),
            replace(base, replacement="SPEC-004@999"),
        ):
            with self.subTest(promoted=malformed_promoted):
                self.assertEqual(
                    promoted_codes(
                        {base.spec_id: base},
                        {candidate.spec_id: candidate},
                        {base.spec_id: malformed_promoted},
                    ),
                    {"SPEC_REVISION_PREDECESSOR_NOT_PROMOTED"},
                )

        active_default = revision(spec_bytes(status="accepted", body="A"))
        self.assertEqual(
            promoted_codes(
                {base.spec_id: base},
                {candidate.spec_id: candidate},
                {active_default.spec_id: active_default},
            ),
            {"SPEC_REVISION_PREDECESSOR_NOT_PROMOTED"},
        )

        divergent_default = revision(
            spec_bytes(
                status="amended",
                body="different bytes",
                lifecycle_decision="ADR-0007",
                replacement="SPEC-004@2",
            )
        )
        self.assertEqual(
            promoted_codes(
                {base.spec_id: base},
                {candidate.spec_id: candidate},
                {divergent_default.spec_id: divergent_default},
            ),
            {"SPEC_REVISION_PREDECESSOR_NOT_PROMOTED"},
        )

        decision = terminal_adr()
        self.assertEqual(
            promoted_codes(
                {base.spec_id: base},
                {candidate.spec_id: candidate},
                {base.spec_id: base},
                base_adrs={decision.adr_id: decision},
                promoted_adrs={},
            ),
            {"SPEC_REVISION_PREDECESSOR_NOT_PROMOTED"},
        )
        divergent_decision = terminal_adr("Different decision bytes.")
        self.assertEqual(
            promoted_codes(
                {base.spec_id: base},
                {candidate.spec_id: candidate},
                {base.spec_id: base},
                base_adrs={decision.adr_id: decision},
                promoted_adrs={divergent_decision.adr_id: divergent_decision},
            ),
            {"SPEC_REVISION_PREDECESSOR_NOT_PROMOTED"},
        )
        relocated_decision = replace(
            decision,
            path="docs/decisions/0008-relocated-fixture.md",
        )
        self.assertEqual(
            promoted_codes(
                {base.spec_id: base},
                {candidate.spec_id: candidate},
                {base.spec_id: base},
                base_adrs={decision.adr_id: decision},
                promoted_adrs={relocated_decision.adr_id: relocated_decision},
            ),
            {"SPEC_REVISION_PREDECESSOR_NOT_PROMOTED"},
        )

    def test_same_revision_transition_does_not_require_promoted_predecessor(
        self,
    ) -> None:
        base = revision(spec_bytes(status="architecture_reviewed"))
        candidate = revision(
            spec_bytes(
                status="amended",
                lifecycle_decision="ADR-0007",
                replacement="SPEC-004@2",
            )
        )
        self.assertEqual(
            validate_promoted_revision_predecessors(
                {base.spec_id: base},
                {candidate.spec_id: candidate},
                {},
                transition_base_adrs={},
                promoted_default_adrs={},
            ),
            [],
        )

    def test_cli_distinguishes_proposal_base_from_promoted_default(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            spec_path = root / "docs/specs/SPEC-004-fixture.md"
            adr_path = root / "docs/decisions/0007-fixture.md"
            spec_path.parent.mkdir(parents=True)
            adr_path.parent.mkdir(parents=True)

            def git(*arguments: str) -> None:
                subprocess.run(
                    ["git", *arguments],
                    cwd=root,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )

            def git_output(*arguments: str) -> str:
                return subprocess.run(
                    ["git", *arguments],
                    cwd=root,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                ).stdout.strip()

            git("init", "-b", "main")
            git("config", "user.name", "Lifecycle Test")
            git("config", "user.email", "lifecycle@example.invalid")
            git("config", "commit.gpgsign", "false")
            git("config", "core.hooksPath", str(root / ".no-hooks"))
            spec_path.write_bytes(spec_bytes(status="accepted", body="A"))
            git("add", ".")
            git("commit", "-m", "active predecessor")

            git("checkout", "-b", "proposal")
            terminal_bytes = spec_bytes(
                status="amended",
                body="A",
                lifecycle_decision="ADR-0007",
                replacement="SPEC-004@2",
            )
            spec_path.write_bytes(terminal_bytes)
            adr_path.write_bytes(terminal_adr().exact_bytes)
            git("add", ".")
            git("commit", "-m", "terminal predecessor proposal")

            digest = f"sha256:{hashlib.sha256(terminal_bytes).hexdigest()}"
            spec_path.write_bytes(
                spec_bytes(status="draft", revision=2, revises=digest, body="B")
            )
            main_oid = git_output("rev-parse", "main^{commit}")
            proposal_oid = git_output("rev-parse", "proposal^{commit}")
            git("replace", main_oid, proposal_oid)
            command = [
                sys.executable,
                str(ROOT / "researcher/scripts/validate_spec_lifecycle.py"),
                "--root",
                str(root),
                "--base-ref",
                "proposal",
                "--promoted-ref",
                "main",
            ]
            missing_promoted_ref = subprocess.run(
                command[:-2],
                cwd=root,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(missing_promoted_ref.returncode, 2)
            self.assertIn("--promoted-ref", missing_promoted_ref.stderr)

            unresolved = subprocess.run(
                [*command[:-1], "does-not-exist"],
                cwd=root,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(unresolved.returncode, 0)
            self.assertIn("SPEC_LIFECYCLE_ERROR", unresolved.stderr)

            rejected = subprocess.run(
                command,
                cwd=root,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(rejected.returncode, 1)
            self.assertIn(
                "SPEC_REVISION_PREDECESSOR_NOT_PROMOTED",
                rejected.stderr,
            )

            git("branch", "-f", "main", "proposal")
            accepted = subprocess.run(
                command,
                cwd=root,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(accepted.returncode, 0, accepted.stderr)
            self.assertIn("promoted default", accepted.stdout)

    def test_ci_pins_promoted_default_separately_from_proposal_base(self) -> None:
        workflow = (ROOT / ".github/workflows/validate.yml").read_text(encoding="utf-8")
        workflow_data = yaml.safe_load(workflow)
        step_names = [
            step["name"] for step in workflow_data["jobs"]["validate"]["steps"]
        ]
        self.assertEqual(
            step_names[:5],
            [
                "Checkout",
                "Pin lifecycle Git authorities",
                "Set up Python",
                "Install pinned lifecycle parser dependency",
                "Specification lifecycle against protected base",
            ],
        )
        self.assertIn(
            "types: [opened, synchronize, reopened, edited, ready_for_review]",
            workflow,
        )
        self.assertIn(
            "PR_BASE_REF: ${{ github.event.pull_request.base.ref }}",
            workflow,
        )
        self.assertIn("id: lifecycle-authorities", workflow)
        self.assertIn("git --no-replace-objects", workflow)
        self.assertIn('GIT_NO_REPLACE_OBJECTS: "1"', workflow)
        self.assertIn("--no-deps", workflow)
        self.assertIn("--only-binary=:all:", workflow)
        self.assertIn("--require-hashes", workflow)
        self.assertIn("pyyaml==6.0.3", workflow)
        self.assertIn(
            "sha256:ba1cc08a7ccde2d2ec775841541641e4548226580ab850948cbfda66a1befcdc",
            workflow,
        )
        self.assertIn(
            "BASE_SHA: ${{ steps.lifecycle-authorities.outputs.base_sha }}",
            workflow,
        )
        self.assertIn('--promoted-ref "$PROMOTED_SHA"', workflow)
        parser_dependency = workflow.index(
            "- name: Install pinned lifecycle parser dependency"
        )
        lifecycle_gate = workflow.index(
            "- name: Specification lifecycle against protected base"
        )
        self.assertLess(parser_dependency, lifecycle_gate)
        self.assertLess(
            lifecycle_gate, workflow.index("- name: Repository secret scan")
        )
        self.assertLess(
            lifecycle_gate, workflow.index("- name: Install validation dependencies")
        )

    def test_active_revision_must_first_enter_terminal_amendment_state(self) -> None:
        base_bytes = spec_bytes(status="accepted", body="A")
        base = revision(base_bytes)
        digest = f"sha256:{hashlib.sha256(base_bytes).hexdigest()}"
        candidate = revision(
            spec_bytes(status="draft", revision=2, revises=digest, body="B")
        )
        self.assertIn(
            "SPEC_REVISION_PREDECESSOR_ACTIVE",
            codes({base.spec_id: base}, {candidate.spec_id: candidate}),
        )

    def test_successor_must_match_terminal_replacement_pointer(self) -> None:
        base_bytes = spec_bytes(
            status="amended",
            body="A",
            lifecycle_decision="ADR-0007",
            replacement="SPEC-999@9",
        )
        base = revision(base_bytes)
        digest = f"sha256:{hashlib.sha256(base_bytes).hexdigest()}"
        candidate = revision(
            spec_bytes(status="draft", revision=2, revises=digest, body="B")
        )
        self.assertIn(
            "SPEC_REPLACEMENT_MISMATCH",
            codes({base.spec_id: base}, {candidate.spec_id: candidate}),
        )

    def test_terminal_lifecycle_metadata_is_immutable_without_transition(self) -> None:
        base = revision(
            spec_bytes(
                status="retired", lifecycle_decision="ADR-0007", replacement="none"
            )
        )
        candidate = revision(
            spec_bytes(
                status="retired", lifecycle_decision="ADR-0008", replacement="none"
            )
        )
        self.assertIn(
            "SPEC_LIFECYCLE_METADATA_CHANGED",
            codes({base.spec_id: base}, {candidate.spec_id: candidate}),
        )

    def test_active_transition_cannot_add_a_lifecycle_decision(self) -> None:
        base = revision(spec_bytes(status="implemented", dependency_revisions="none"))
        candidate = revision(
            spec_bytes(
                status="verified",
                dependency_revisions="none",
                lifecycle_decision="ADR-0006",
            )
        )
        result = codes({base.spec_id: base}, {candidate.spec_id: candidate})
        self.assertIn("INVALID_SPEC_LIFECYCLE_DECISION", result)
        self.assertIn("SPEC_LIFECYCLE_METADATA_CHANGED", result)

    def test_new_revision_rejects_wrong_digest_and_non_draft_status(self) -> None:
        base = revision(spec_bytes(status="accepted"))
        candidate = revision(
            spec_bytes(
                status="accepted",
                revision=2,
                revises="sha256:" + "0" * 64,
            )
        )
        result = codes({base.spec_id: base}, {candidate.spec_id: candidate})
        self.assertIn("SPEC_REVISION_NOT_DRAFT", result)
        self.assertIn("SPEC_REVISION_DIGEST_MISMATCH", result)

    def test_deletion_is_rejected(self) -> None:
        base = revision(spec_bytes())
        self.assertIn("SPEC_DELETION_FORBIDDEN", codes({base.spec_id: base}, {}))

    def test_same_identity_cannot_move_to_a_different_path(self) -> None:
        base = revision_at(
            "docs/specs/SPEC-004-original.md",
            spec_bytes(status="accepted", dependency_revisions="none"),
        )
        candidate = revision_at(
            "docs/specs/SPEC-004-renamed.md",
            spec_bytes(status="accepted", dependency_revisions="none"),
        )
        self.assertIn(
            "SPEC_PATH_CHANGED",
            codes({base.spec_id: base}, {candidate.spec_id: candidate}),
        )

    def test_adoption_decision_is_immutable_within_revision(self) -> None:
        base = parse_spec_revision(
            "docs/specs/SPEC-000-fixture.md",
            spec_bytes(status="implemented").replace(
                b"Depends on: none\n",
                b"Depends on: none\nDependency revisions: none\nAdoption decision: ADR-0005\n",
            ),
            allow_legacy=False,
        )
        candidate = parse_spec_revision(
            "docs/specs/SPEC-000-fixture.md",
            base.exact_bytes.replace(
                b"Status: implemented", b"Status: verified"
            ).replace(b"Adoption decision: ADR-0005\n", b""),
            allow_legacy=False,
        )
        self.assertIn(
            "SPEC_ADOPTION_METADATA_CHANGED",
            codes({base.spec_id: base}, {candidate.spec_id: candidate}),
        )

    def test_legacy_adoption_is_exact_and_decision_bound(self) -> None:
        legacy = (
            "# SPEC-000: Fixture\n\n"
            "- Status: implementing\n"
            "- Wave: 0\n"
            "- Classification: public\n"
            "- Depends on: none\n\n"
            "## Decision\n\nContract A.\n"
        ).encode("utf-8")
        current = (
            "# SPEC-000: Fixture\n\n"
            "Status: implemented\n"
            "Revision: 1\n"
            "Revises: none\n"
            "Wave: 0\n"
            "Classification: public\n"
            "Owners: human maintainer; governance agent\n"
            "Depends on: none\n"
            "Dependency revisions: none\n"
            "Adoption decision: ADR-0005\n\n"
            "## Decision\n\nContract A.\n"
        ).encode("utf-8")
        base = parse_spec_revision(
            "docs/specs/SPEC-000-fixture.md", legacy, allow_legacy=True
        )
        candidate = parse_spec_revision(
            "docs/specs/SPEC-000-fixture.md", current, allow_legacy=False
        )
        self.assertEqual(
            validate_lifecycle({base.spec_id: base}, {candidate.spec_id: candidate}), []
        )

        changed = parse_spec_revision(
            "docs/specs/SPEC-000-fixture.md",
            current.replace(b"Contract A.", b"Contract B."),
            allow_legacy=False,
        )
        self.assertIn(
            "INVALID_LEGACY_LIFECYCLE_ADOPTION",
            codes({base.spec_id: base}, {changed.spec_id: changed}),
        )

        metadata_changed = parse_spec_revision(
            "docs/specs/SPEC-000-fixture.md",
            current.replace(b"Classification: public", b"Classification: split"),
            allow_legacy=False,
        )
        self.assertIn(
            "INVALID_LEGACY_LIFECYCLE_ADOPTION",
            codes({base.spec_id: base}, {metadata_changed.spec_id: metadata_changed}),
        )


class ArchitectureDecisionLifecycleTests(unittest.TestCase):
    @staticmethod
    def adr(
        body: str = "Decision A.",
        status: str = "accepted",
        lifecycle_transition: str | None = None,
    ):
        transition_line = (
            f"- Lifecycle transition: {lifecycle_transition}\n"
            if lifecycle_transition is not None
            else ""
        )
        return parse_adr_revision(
            "docs/decisions/0001-fixture.md",
            (
                "# ADR-0001: Fixture\n\n"
                f"- Status: {status}\n"
                "- Date: 2026-08-10\n"
                "- Spec: SPEC-000\n"
                f"{transition_line}\n"
                "## Decision\n\n"
                f"{body}\n"
            ).encode("utf-8"),
        )

    def test_terminal_spec_transition_requires_exact_adr_binding(self) -> None:
        base = revision(spec_bytes(status="architecture_reviewed"))
        candidate = revision(
            spec_bytes(
                status="superseded",
                lifecycle_decision="ADR-0001",
                replacement="SPEC-004@2",
            )
        )
        unrelated = self.adr(lifecycle_transition="SPEC-999@1 -> retired -> none")
        self.assertIn(
            "SPEC_LIFECYCLE_DECISION_MISMATCH",
            {
                finding.code
                for finding in validate_lifecycle_decision_bindings(
                    {base.spec_id: base},
                    {candidate.spec_id: candidate},
                    {"ADR-0001": unrelated},
                )
            },
        )

        exact = self.adr(lifecycle_transition="SPEC-004@1 -> superseded -> SPEC-004@2")
        self.assertEqual(
            validate_lifecycle_decision_bindings(
                {base.spec_id: base},
                {candidate.spec_id: candidate},
                {"ADR-0001": exact},
            ),
            [],
        )

    def test_accepted_adr_is_byte_immutable(self) -> None:
        base = self.adr()
        candidate = self.adr(body="Decision B.")
        result = validate_adr_lifecycle(
            {base.adr_id: base}, {candidate.adr_id: candidate}
        )
        self.assertIn("ACCEPTED_ADR_IMMUTABLE", {finding.code for finding in result})

    def test_accepted_adr_cannot_be_deleted(self) -> None:
        base = self.adr()
        result = validate_adr_lifecycle({base.adr_id: base}, {})
        self.assertIn("ADR_DELETION_FORBIDDEN", {finding.code for finding in result})

    def test_new_adr_number_must_exceed_base_maximum(self) -> None:
        base = parse_adr_revision(
            "docs/decisions/0006-base.md",
            (
                "# ADR-0006: Base\n\n- Status: accepted\n- Date: 2026-08-10\n"
                "- Spec: SPEC-000\n\n## Decision\n\nBase.\n"
            ).encode("utf-8"),
        )
        inserted = parse_adr_revision(
            "docs/decisions/0005-inserted.md",
            (
                "# ADR-0005: Inserted\n\n- Status: proposed\n- Date: 2026-08-11\n"
                "- Spec: SPEC-000\n\n## Decision\n\nInserted.\n"
            ).encode("utf-8"),
        )
        result = validate_adr_lifecycle(
            {base.adr_id: base},
            {base.adr_id: base, inserted.adr_id: inserted},
        )
        self.assertIn(
            "ADR_NUMBER_NOT_APPEND_ONLY",
            {finding.code for finding in result},
        )

    def test_proposed_adr_may_change_before_acceptance(self) -> None:
        base = self.adr(status="proposed")
        candidate = self.adr(body="Reviewed decision.", status="accepted")
        self.assertEqual(
            validate_adr_lifecycle({base.adr_id: base}, {candidate.adr_id: candidate}),
            [],
        )


if __name__ == "__main__":
    unittest.main()
