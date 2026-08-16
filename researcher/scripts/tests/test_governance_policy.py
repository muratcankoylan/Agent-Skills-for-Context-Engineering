"""Tests for the fail-closed program constitution evaluator."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
import yaml

from researcher.scripts.governance_policy import (
    MAX_POLICY_STRING_LENGTH,
    MAX_POLICY_TOKEN_LENGTH,
    MAX_PORTABLE_INTEGER,
    Constitution,
    ConstitutionError,
)
from researcher.scripts.validate_governance import (
    DEFAULT_FIXTURES,
    canonical_json_text,
    render_authority_table,
    validate_authority_conformance,
    validate_fixtures,
    validate_invariants,
)
from researcher.scripts.validate_authority_contract import (
    AUTHORITY_CONFORMANCE_RECEIPT_PATH,
    AUTHORITY_CONFORMANCE_RECEIPT_SCHEMA_VERSION,
    AUTHORITY_EVALUATOR_BUNDLE_VERSION,
    AUTHORITY_EVALUATOR_COMPONENT_PATHS,
    AUTHORITY_FIXTURE_MANIFEST_PATH,
    AUTHORITY_FIXTURE_MANIFEST_SCHEMA_VERSION,
    AUTHORITY_VALIDATOR_BUNDLE_ALGORITHM,
    AUTHORITY_VOCABULARY_PATH,
    AUTHORITY_VOCABULARY_SCHEMA_PATH,
    AUTHORITY_VOCABULARY_SCHEMA_VERSION,
    POLICY_ONLY_READ_PROFILES,
    REQUIRED_AUTHORITY_PROFILES,
    build_authority_evaluator_bundle,
    expected_authority_catalog_boundary_cases,
    expected_authority_fixture_cases,
    expected_authority_policy_conditions,
    validate_authority_policy_closure,
)


ROOT = Path(__file__).resolve().parents[3]
CONSTITUTION_PATH = ROOT / "governance" / "constitution.yaml"


def authority_documents() -> tuple[bytes, bytes]:
    registry_entries = []
    fixture_entries = []
    for (action, resource), profile in sorted(REQUIRED_AUTHORITY_PROFILES.items()):
        registry_entries.append(
            {
                "action": action,
                "resource": resource,
                "owner_spec": profile.owner_spec,
                "actor_bindings": [
                    binding.to_payload() for binding in profile.actor_bindings
                ],
                "max_effect": profile.max_effect,
                "dependency_requirements": [
                    requirement.to_payload()
                    for requirement in profile.dependency_requirements
                ],
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
        "schema_version": AUTHORITY_FIXTURE_MANIFEST_SCHEMA_VERSION,
        "constitution_revision": 2,
        "registry_version": 2,
        "catalog_boundary_cases": list(expected_authority_catalog_boundary_cases()),
        "entries": fixture_entries,
    }
    fixture_bytes = canonical_json_text(fixture).encode("utf-8")
    registry = {
        "kind": "AuthorityVocabularyRegistry",
        "schema_version": AUTHORITY_VOCABULARY_SCHEMA_VERSION,
        "owner_spec": "SPEC-000",
        "constitution_revision": 2,
        "registry_version": 2,
        "fixture_manifest": {
            "path": AUTHORITY_FIXTURE_MANIFEST_PATH,
            "digest": f"sha256:{hashlib.sha256(fixture_bytes).hexdigest()}",
            "version": 2,
        },
        "entries": registry_entries,
    }
    return canonical_json_text(registry).encode("utf-8"), fixture_bytes


def conforming_policy_document() -> dict:
    actors = {"human_maintainer"}
    actions: set[str] = set()
    resources: set[str] = set()
    rules = []
    profiles = list(sorted(REQUIRED_AUTHORITY_PROFILES.items())) + list(
        sorted(POLICY_ONLY_READ_PROFILES.items())
    )
    for action_resource, profile in profiles:
        action, resource = action_resource
        actors.update(profile.actor_classes)
        actions.add(action)
        resources.add(resource)
        for actor in sorted(profile.actor_classes):
            rules.append(
                {
                    "rule_id": f"authority-profile-{len(rules):03d}",
                    "effect": "allow",
                    "actors": [actor],
                    "actions": [action],
                    "resources": [resource],
                    "conditions": list(
                        expected_authority_policy_conditions(profile, actor)
                    ),
                    "reason_code": "OFFLINE_CLASS_POLICY_ALLOWED",
                }
            )
    separation_groups = [
        {
            "duty": "attestor",
            "actor_classes": [
                "independent_canary_attestor",
                "release_attestor",
            ],
        },
        {
            "duty": "author",
            "actor_classes": [
                "change_author",
                "community_contributor",
                "content_proposer",
                "human_maintainer",
                "research_proposer",
            ],
        },
        {
            "duty": "sealer",
            "actor_classes": ["independent_epoch_sealer"],
        },
        {
            "duty": "verifier",
            "actor_classes": ["independent_verifier"],
        },
    ]
    actors.update(
        actor
        for group in separation_groups
        for actor in group["actor_classes"]
    )
    return {
        "schema_version": "2.0.0",
        "constitution_version": "2.0.0",
        "lifecycle_state": "effective",
        "effective_commit": "$SELF",
        "default_effect": "deny",
        "promotion_event": "human_merged_commit",
        "identity_bindings": {actor: [] for actor in sorted(actors)},
        "actor_classes": {
            actor: {
                "automated": actor
                not in {"community_contributor", "human_maintainer"}
            }
            for actor in sorted(actors)
        },
        "actions": sorted(actions),
        "resource_classes": sorted(resources),
        "protected_surfaces": [
            ".github/CODEOWNERS",
            ".github/workflows/**",
            "governance/**",
            "researcher/benchmarks/**/hidden/**",
            "researcher/rubrics/**",
            "researcher/scripts/build_inventory.py",
            "researcher/scripts/governance_policy.py",
            "researcher/scripts/run_benchmarks.py",
            "researcher/scripts/validate_*.py",
        ],
        "separation_of_duty": [
            {
                "rule_id": "protected-change-lineage-separation",
                "scope": "protected_change_lineage",
                "constraint": "distinct_authenticated_principal_across_groups",
                "groups": separation_groups,
            }
        ],
        "rules": rules,
        "emergency_controls": {
            "disable_changes_authority": False,
            "disable_mutates_history": False,
            "disable_stops_new_work": True,
        },
        "amendment_procedure": {
            "prior_versions_retained": True,
            "required_actor": "human_maintainer",
            "required_state_sequence": [
                "draft",
                "reviewed",
                "merged",
                "effective",
            ],
            "required_transport": "pull_request",
        },
    }


def evaluator_component_bytes(
    root: Path = ROOT,
) -> tuple[tuple[str, bytes], ...]:
    return tuple(
        (relative, (root / relative).read_bytes())
        for relative in AUTHORITY_EVALUATOR_COMPONENT_PATHS
    )


def write_revision_two_root(
    root: Path,
    *,
    status: str = "accepted",
    policy_document: dict | None = None,
) -> Constitution:
    registry_bytes, fixture_bytes = authority_documents()
    registry_digest = f"sha256:{hashlib.sha256(registry_bytes).hexdigest()}"
    schema_bytes = (ROOT / AUTHORITY_VOCABULARY_SCHEMA_PATH).read_bytes()
    schema_digest = f"sha256:{hashlib.sha256(schema_bytes).hexdigest()}"
    spec = (
        "# SPEC-000: Fixture\n\n"
        f"Status: {status}\n"
        "Revision: 2\n"
        f"Revises: sha256:{'1' * 64}\n"
        "Wave: 0\n"
        "Classification: public\n"
        "Owners: human maintainer; governance agent\n"
        "Depends on: none\n"
        "Dependency revisions: none\n"
        f"Authority vocabulary schema: {AUTHORITY_VOCABULARY_SCHEMA_PATH}\n"
        f"Authority vocabulary schema digest: {schema_digest}\n"
        f"Authority vocabulary schema version: {AUTHORITY_VOCABULARY_SCHEMA_VERSION}\n"
        f"Authority vocabulary: {AUTHORITY_VOCABULARY_PATH}\n"
        f"Authority vocabulary digest: {registry_digest}\n"
        "Authority vocabulary version: 2\n\n"
        "## Decision\n\nFixture.\n"
    )
    spec_path = root / "docs/specs/SPEC-000-fixture.md"
    spec_path.parent.mkdir(parents=True)
    spec_path.write_text(spec, encoding="utf-8")
    registry_path = root / AUTHORITY_VOCABULARY_PATH
    fixture_path = root / AUTHORITY_FIXTURE_MANIFEST_PATH
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    fixture_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_bytes(registry_bytes)
    fixture_path.write_bytes(fixture_bytes)
    for relative in AUTHORITY_EVALUATOR_COMPONENT_PATHS:
        component_path = root / relative
        component_path.parent.mkdir(parents=True, exist_ok=True)
        component_path.write_bytes((ROOT / relative).read_bytes())
    constitution_path = root / "governance/constitution.yaml"
    constitution_path.write_text(
        yaml.safe_dump(
            policy_document or conforming_policy_document(),
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return Constitution.load(constitution_path)


class ConstitutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.constitution = Constitution.load(CONSTITUTION_PATH)

    def test_repository_constitution_is_valid(self) -> None:
        self.assertEqual(validate_invariants(self.constitution), [])
        self.assertEqual(validate_fixtures(self.constitution, DEFAULT_FIXTURES), [])

    def test_exhaustive_cross_product_is_total_and_deterministic(self) -> None:
        context = {
            "authenticated": True,
            "latest_commit_reviewed": True,
            "required_checks_passed": True,
            "automated_identity_disclosed": True,
            "human_review_path": "pull_request",
            "independent_of_author": True,
            "candidate_digest_verified": True,
            "capability_grant_valid": True,
        }
        decisions = []
        for actor in self.constitution.actor_classes:
            for action in self.constitution.actions:
                for resource in self.constitution.resource_classes:
                    first = self.constitution.decide(actor, action, resource, context)
                    second = self.constitution.decide(actor, action, resource, context)
                    self.assertEqual(first, second)
                    decisions.append(first)
        expected = (
            len(self.constitution.actor_classes)
            * len(self.constitution.actions)
            * len(self.constitution.resource_classes)
        )
        self.assertEqual(len(decisions), expected)

    def test_only_human_maintainer_can_merge(self) -> None:
        context = {
            "authenticated": True,
            "latest_commit_reviewed": True,
            "required_checks_passed": True,
        }
        for actor in self.constitution.actor_classes:
            with self.subTest(actor=actor):
                decision = self.constitution.decide(actor, "merge", "pull_request", context)
                self.assertEqual(decision.allowed, actor == "human_maintainer")

    def test_deny_overrides_allow(self) -> None:
        document = yaml.safe_load(CONSTITUTION_PATH.read_text(encoding="utf-8"))
        document["rules"].append(
            {
                "rule_id": "deny-human-merge-test",
                "effect": "deny",
                "actors": ["human_maintainer"],
                "actions": ["merge"],
                "resources": ["pull_request"],
                "reason_code": "TEST_DENY",
            }
        )
        policy = Constitution(document, "fixture-digest", CONSTITUTION_PATH)
        decision = policy.decide(
            "human_maintainer",
            "merge",
            "pull_request",
            {
                "authenticated": True,
                "latest_commit_reviewed": True,
                "required_checks_passed": True,
            },
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason_code, "TEST_DENY")

    def test_missing_condition_denies(self) -> None:
        decision = self.constitution.decide(
            "change_author",
            "open_pull_request",
            "pull_request",
            {"automated_identity_disclosed": True},
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason_code, "DEFAULT_DENY")

    def test_unknown_vocabulary_denies(self) -> None:
        self.assertEqual(
            self.constitution.decide("unknown", "read", "public_repository").reason_code,
            "UNKNOWN_ACTOR",
        )
        self.assertEqual(
            self.constitution.decide("human_maintainer", "unknown", "public_repository").reason_code,
            "UNKNOWN_ACTION",
        )
        self.assertEqual(
            self.constitution.decide("human_maintainer", "read", "unknown").reason_code,
            "UNKNOWN_RESOURCE",
        )

    def test_version_mismatch_fails_closed(self) -> None:
        with self.assertRaises(ConstitutionError):
            Constitution.load(CONSTITUTION_PATH, expected_digest="0" * 64)

    def test_invalid_schema_major_fails_closed(self) -> None:
        document = yaml.safe_load(CONSTITUTION_PATH.read_text(encoding="utf-8"))
        document["schema_version"] = "2.0.0"
        with self.assertRaises(ConstitutionError):
            Constitution(document, "fixture-digest", CONSTITUTION_PATH)

    def test_non_human_merge_allow_rule_is_rejected(self) -> None:
        document = yaml.safe_load(CONSTITUTION_PATH.read_text(encoding="utf-8"))
        document["rules"].append(
            {
                "rule_id": "invalid-agent-merge",
                "effect": "allow",
                "actors": ["change_author"],
                "actions": ["merge"],
                "resources": ["pull_request"],
                "reason_code": "INVALID_ALLOW",
            }
        )
        with self.assertRaises(ConstitutionError):
            Constitution(document, "fixture-digest", CONSTITUTION_PATH)

    def test_generated_view_is_byte_stable(self) -> None:
        first = render_authority_table(self.constitution)
        second = render_authority_table(self.constitution)
        self.assertEqual(first, second)
        self.assertIn(self.constitution.digest, first)

    def test_every_rule_has_a_reachable_decision(self) -> None:
        for rule in self.constitution.rules:
            context = {}
            for condition in rule.get("conditions", []):
                operator = condition["operator"]
                if operator == "equals":
                    context[condition["key"]] = condition["value"]
                elif operator == "not_equals":
                    context[condition["key"]] = object()
                elif operator == "in":
                    context[condition["key"]] = condition["value"][0]
                elif operator == "not_in":
                    context[condition["key"]] = "outside-fixture"
                elif operator == "present":
                    context[condition["key"]] = True
            decision = self.constitution.decide(
                rule["actors"][0],
                rule["actions"][0],
                rule["resources"][0],
                context,
            )
            with self.subTest(rule=rule["rule_id"]):
                if rule["effect"] == "deny":
                    self.assertFalse(decision.allowed)
                    self.assertEqual(decision.reason_code, rule["reason_code"])
                else:
                    self.assertTrue(decision.allowed)
                    self.assertEqual(decision.reason_code, rule["reason_code"])

    def test_atomic_view_generation_does_not_leave_partial_target(self) -> None:
        # A write failure is simulated by targeting a directory. The existing
        # sentinel file remains untouched because replacement is the last step.
        from researcher.scripts.validate_governance import atomic_write

        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "view.md"
            target.write_text("sentinel", encoding="utf-8")
            atomic_write(target, "replacement")
            self.assertEqual(target.read_text(encoding="utf-8"), "replacement")

    def test_path_classification_rejects_escape(self) -> None:
        with self.assertRaises(ConstitutionError):
            self.constitution.classify_path("../outside")


class AuthorityConformanceIntegrationTests(unittest.TestCase):
    def test_evaluator_bundle_manifest_is_exact_and_deterministic(self) -> None:
        components = evaluator_component_bytes()
        first = build_authority_evaluator_bundle(components)
        second = build_authority_evaluator_bundle(components)

        self.assertEqual(first, second)
        self.assertEqual(first.algorithm, AUTHORITY_VALIDATOR_BUNDLE_ALGORITHM)
        self.assertEqual(first.version, AUTHORITY_EVALUATOR_BUNDLE_VERSION)
        self.assertEqual(
            tuple(component.path for component in first.components),
            AUTHORITY_EVALUATOR_COMPONENT_PATHS,
        )
        self.assertRegex(first.digest, r"^sha256:[0-9a-f]{64}$")

        malformed_component_sets = {
            "missing": components[:-1],
            "extra": (
                *components,
                ("researcher/scripts/validate_spec_lifecycle.py", b"unrelated"),
            ),
            "relocated": (
                ("researcher/scripts/relocated_governance_policy.py", components[0][1]),
                components[1],
            ),
        }
        for name, malformed in malformed_component_sets.items():
            with self.subTest(name=name), self.assertRaisesRegex(
                ValueError,
                "exact canonical path set",
            ):
                build_authority_evaluator_bundle(malformed)
        self.assertEqual(
            build_authority_evaluator_bundle(tuple(reversed(components))),
            first,
        )
        with self.assertRaisesRegex(ValueError, "paths must be unique"):
            build_authority_evaluator_bundle((components[0], components[0]))

        for index, (path, exact_bytes) in enumerate(components):
            mutated = list(components)
            mutated[index] = (path, exact_bytes + b"\n")
            with self.subTest(component=path):
                self.assertNotEqual(
                    build_authority_evaluator_bundle(mutated).digest,
                    first.digest,
                )

    def test_current_revision_one_repository_remains_backward_compatible(self) -> None:
        policy = Constitution.load(CONSTITUTION_PATH)
        self.assertEqual(
            validate_authority_conformance(ROOT, policy, write=False),
            [],
        )
        self.assertFalse((ROOT / AUTHORITY_CONFORMANCE_RECEIPT_PATH).exists())

    def test_revision_one_rejects_unowned_canonical_authority_artifacts(self) -> None:
        spec = (
            "# SPEC-000: Fixture\n\n"
            "Status: accepted\n"
            "Revision: 1\n"
            "Revises: none\n"
            "Wave: 0\n"
            "Classification: public\n"
            "Owners: human maintainer; governance agent\n"
            "Depends on: none\n"
            "Dependency revisions: none\n\n"
            "## Decision\n\nFixture.\n"
        )
        for relative in (
            AUTHORITY_VOCABULARY_PATH,
            AUTHORITY_FIXTURE_MANIFEST_PATH,
            AUTHORITY_CONFORMANCE_RECEIPT_PATH,
        ):
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                spec_path = root / "docs/specs/SPEC-000-fixture.md"
                spec_path.parent.mkdir(parents=True)
                spec_path.write_text(spec, encoding="utf-8")
                artifact_path = root / relative
                artifact_path.parent.mkdir(parents=True, exist_ok=True)
                artifact_path.write_text("{}\n", encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "pre-registry SPEC-000"):
                    validate_authority_conformance(
                        root,
                        Constitution.load(CONSTITUTION_PATH),
                        write=False,
                    )

    def test_accepted_validates_design_but_forbids_a_prospective_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            policy = write_revision_two_root(root)
            receipt_path = root / AUTHORITY_CONFORMANCE_RECEIPT_PATH
            self.assertEqual(
                validate_authority_conformance(root, policy, write=False),
                [],
            )
            with self.assertRaisesRegex(ValueError, "requires SPEC-000 to be implemented"):
                validate_authority_conformance(root, policy, write=True)
            self.assertFalse(receipt_path.exists())

    def test_accepted_candidate_rejects_an_otherwise_valid_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            policy = write_revision_two_root(root, status="implemented")
            validate_authority_conformance(root, policy, write=True)
            spec_path = root / "docs/specs/SPEC-000-fixture.md"
            spec_path.write_text(
                spec_path.read_text(encoding="utf-8").replace(
                    "Status: implemented",
                    "Status: accepted",
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "pre-implementation"):
                validate_authority_conformance(root, policy, write=False)

    def test_accepted_can_land_design_before_policy_implementation(self) -> None:
        revision_one_policy = yaml.safe_load(
            CONSTITUTION_PATH.read_text(encoding="utf-8")
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            policy = write_revision_two_root(
                root,
                policy_document=revision_one_policy,
            )
            self.assertEqual(
                validate_authority_conformance(root, policy, write=False),
                [],
            )
            self.assertFalse((root / AUTHORITY_CONFORMANCE_RECEIPT_PATH).exists())

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            policy = write_revision_two_root(
                root,
                status="implemented",
                policy_document=revision_one_policy,
            )
            with self.assertRaisesRegex(
                ValueError,
                "does not implement the authority registry",
            ):
                validate_authority_conformance(root, policy, write=True)
            self.assertFalse((root / AUTHORITY_CONFORMANCE_RECEIPT_PATH).exists())

    def test_implemented_round_trip_is_deterministic_atomic_and_public_safe(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            policy = write_revision_two_root(root, status="implemented")
            receipt_path = root / AUTHORITY_CONFORMANCE_RECEIPT_PATH
            with self.assertRaisesRegex(ValueError, "require.*validated"):
                validate_authority_conformance(root, policy, write=False)
            self.assertEqual(
                validate_authority_conformance(root, policy, write=True),
                [],
            )
            first = receipt_path.read_bytes()
            self.assertEqual(
                validate_authority_conformance(root, policy, write=False),
                [],
            )
            self.assertEqual(
                validate_authority_conformance(root, policy, write=True),
                [],
            )
            self.assertEqual(receipt_path.read_bytes(), first)
            receipt = json.loads(first)
            self.assertEqual(
                receipt["schema_version"],
                AUTHORITY_CONFORMANCE_RECEIPT_SCHEMA_VERSION,
            )
            self.assertEqual(receipt["result"], "pass")
            self.assertEqual(receipt["skipped_case_count"], 0)
            self.assertEqual(receipt["case_count"], len(receipt["cases"]))
            self.assertEqual(
                receipt["validator_bundle"]["algorithm"],
                AUTHORITY_VALIDATOR_BUNDLE_ALGORITHM,
            )
            self.assertEqual(
                receipt["validator_bundle"]["version"],
                AUTHORITY_EVALUATOR_BUNDLE_VERSION,
            )
            self.assertEqual(
                tuple(
                    component["path"]
                    for component in receipt["validator_bundle"]["components"]
                ),
                AUTHORITY_EVALUATOR_COMPONENT_PATHS,
            )
            self.assertNotIn("validator", receipt)
            self.assertNotIn(str(root), first.decode("utf-8"))
            self.assertEqual(
                list(receipt_path.parent.glob(f".{receipt_path.name}.*.tmp")),
                [],
            )

    def test_cli_write_then_check_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_revision_two_root(root, status="implemented")
            decisions = root / "governance/fixtures/authority-decisions.jsonl"
            decisions.write_text("", encoding="utf-8")
            command = [
                sys.executable,
                str(ROOT / "researcher/scripts/validate_governance.py"),
                "--root",
                str(root),
            ]
            written = subprocess.run(
                [*command, "--write"],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(written.returncode, 0, written.stdout + written.stderr)
            checked = subprocess.run(
                [*command, "--check"],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
            self.assertTrue((root / AUTHORITY_CONFORMANCE_RECEIPT_PATH).is_file())

    def test_missing_receipt_fails_closed_at_implemented_status(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            policy = write_revision_two_root(root, status="implemented")
            with self.assertRaisesRegex(ValueError, "require.*validated"):
                validate_authority_conformance(root, policy, write=False)

    def test_terminal_receipt_is_optional_but_must_validate_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            policy = write_revision_two_root(root, status="retired")
            self.assertEqual(
                validate_authority_conformance(root, policy, write=False),
                [],
            )

        for valid in (True, False):
            with self.subTest(valid=valid), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                policy = write_revision_two_root(root, status="implemented")
                validate_authority_conformance(root, policy, write=True)
                spec_path = root / "docs/specs/SPEC-000-fixture.md"
                spec_path.write_text(
                    spec_path.read_text(encoding="utf-8").replace(
                        "Status: implemented",
                        "Status: retired",
                    ),
                    encoding="utf-8",
                )
                if valid:
                    self.assertEqual(
                        validate_authority_conformance(root, policy, write=False),
                        [],
                    )
                else:
                    receipt_path = root / AUTHORITY_CONFORMANCE_RECEIPT_PATH
                    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
                    receipt["case_count"] += 1
                    receipt_path.write_text(
                        canonical_json_text(receipt),
                        encoding="utf-8",
                    )
                    with self.assertRaises(ValueError):
                        validate_authority_conformance(root, policy, write=False)

    def test_stale_and_partial_receipts_fail_closed(self) -> None:
        mutations = {
            "registry": lambda value: value.__setitem__(
                "registry_digest", "sha256:" + "0" * 64
            ),
            "fixture": lambda value: value.__setitem__(
                "fixture_manifest_digest", "sha256:" + "0" * 64
            ),
            "bundle_digest": lambda value: value["validator_bundle"].__setitem__(
                "digest", "sha256:" + "0" * 64
            ),
            "component_digest": lambda value: value["validator_bundle"][
                "components"
            ][0].__setitem__("digest", "sha256:" + "0" * 64),
            "component_missing": lambda value: value["validator_bundle"][
                "components"
            ].pop(),
            "component_extra": lambda value: value["validator_bundle"][
                "components"
            ].append(
                {
                    "path": "researcher/scripts/validate_spec_lifecycle.py",
                    "digest": "sha256:" + "0" * 64,
                }
            ),
            "component_reordered": lambda value: value["validator_bundle"][
                "components"
            ].reverse(),
            "component_relocated": lambda value: value["validator_bundle"][
                "components"
            ][0].__setitem__(
                "path",
                "researcher/scripts/relocated_governance_policy.py",
            ),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                policy = write_revision_two_root(root, status="implemented")
                self.assertEqual(
                    validate_authority_conformance(root, policy, write=True),
                    [],
                )
                receipt_path = root / AUTHORITY_CONFORMANCE_RECEIPT_PATH
                receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
                mutate(receipt)
                receipt_path.write_text(canonical_json_text(receipt), encoding="utf-8")
                with self.assertRaises(ValueError):
                    validate_authority_conformance(root, policy, write=False)
                self.assertEqual(
                    validate_authority_conformance(root, policy, write=True),
                    [],
                )

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            policy = write_revision_two_root(root, status="implemented")
            validate_authority_conformance(root, policy, write=True)
            receipt_path = root / AUTHORITY_CONFORMANCE_RECEIPT_PATH
            receipt_path.write_text("{", encoding="utf-8")
            with self.assertRaises(ValueError):
                validate_authority_conformance(root, policy, write=False)

    def test_exact_policy_and_evaluator_component_source_bytes_are_bound(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            policy = write_revision_two_root(root, status="implemented")
            validate_authority_conformance(root, policy, write=True)

            policy_document = deepcopy(policy.document)
            policy_document["effective_commit"] = "changed-policy-bytes"
            policy_path = root / "governance/constitution.yaml"
            policy_path.write_text(
                yaml.safe_dump(policy_document, sort_keys=False),
                encoding="utf-8",
            )
            changed_policy = Constitution.load(policy_path)
            with self.assertRaises(ValueError):
                validate_authority_conformance(root, changed_policy, write=False)

        for relative in (
            AUTHORITY_VOCABULARY_PATH,
            AUTHORITY_FIXTURE_MANIFEST_PATH,
        ):
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                policy = write_revision_two_root(root, status="implemented")
                validate_authority_conformance(root, policy, write=True)
                source = root / relative
                source.write_bytes(source.read_bytes() + b"\n")
                with self.assertRaises(ValueError):
                    validate_authority_conformance(root, policy, write=False)

        for relative in AUTHORITY_EVALUATOR_COMPONENT_PATHS:
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                policy = write_revision_two_root(root, status="implemented")
                validate_authority_conformance(root, policy, write=True)
                component_path = root / relative
                component_path.write_bytes(component_path.read_bytes() + b"\n")
                with self.assertRaises(ValueError):
                    validate_authority_conformance(root, policy, write=False)

    def test_evaluator_component_relocation_via_symlink_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            policy = write_revision_two_root(root, status="implemented")
            component_path = root / AUTHORITY_EVALUATOR_COMPONENT_PATHS[0]
            relocated_path = root / "relocated" / component_path.name
            relocated_path.parent.mkdir(parents=True)
            relocated_path.write_bytes(component_path.read_bytes())
            component_path.unlink()
            component_path.symlink_to(relocated_path)

            with self.assertRaisesRegex(ValueError, "symlink ancestors"):
                validate_authority_conformance(root, policy, write=True)

    def test_evaluator_component_symlinked_ancestors_fail_closed(self) -> None:
        for destination in ("external", "internal"):
            with self.subTest(destination=destination), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary) / "repository"
                policy = write_revision_two_root(root, status="implemented")
                scripts_path = root / "researcher/scripts"
                if destination == "external":
                    relocated_path = ROOT / "researcher/scripts"
                    shutil.rmtree(scripts_path)
                else:
                    relocated_path = root / "relocated-scripts"
                    scripts_path.rename(relocated_path)
                scripts_path.symlink_to(relocated_path, target_is_directory=True)

                with self.assertRaisesRegex(ValueError, "symlink ancestors"):
                    validate_authority_conformance(root, policy, write=True)

    def test_receipt_cannot_bind_evaluator_bytes_that_are_not_executing(self) -> None:
        for relative in AUTHORITY_EVALUATOR_COMPONENT_PATHS:
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                policy = write_revision_two_root(root, status="implemented")
                component_path = root / relative
                component_path.write_bytes(
                    b'raise RuntimeError("POISONED_EVALUATOR_WAS_NOT_EXECUTED")\n'
                )

                message = (
                    "authority vocabulary schema"
                    if relative == AUTHORITY_VOCABULARY_SCHEMA_PATH
                    else "executing evaluator"
                )
                with self.assertRaisesRegex(ValueError, message):
                    validate_authority_conformance(root, policy, write=True)
                self.assertFalse((root / AUTHORITY_CONFORMANCE_RECEIPT_PATH).exists())

    def test_receipt_write_rejects_a_symlinked_output_parent(self) -> None:
        for destination in ("external", "internal"):
            with self.subTest(destination=destination), tempfile.TemporaryDirectory() as temporary:
                temporary_root = Path(temporary)
                root = temporary_root / "repository"
                policy = write_revision_two_root(root, status="implemented")
                generated_path = root / "governance/generated"
                if destination == "external":
                    output_root = temporary_root / "external-output"
                else:
                    output_root = root / "relocated-output"
                output_root.mkdir(parents=True)
                generated_path.symlink_to(output_root, target_is_directory=True)

                with self.assertRaisesRegex(ValueError, "symlink ancestor"):
                    validate_authority_conformance(root, policy, write=True)
                self.assertFalse(
                    (output_root / Path(AUTHORITY_CONFORMANCE_RECEIPT_PATH).name).exists()
                )

    def test_unrelated_lifecycle_bytes_do_not_change_evaluator_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            policy = write_revision_two_root(root, status="implemented")
            lifecycle_path = root / "researcher/scripts/validate_spec_lifecycle.py"
            lifecycle_path.write_bytes(b"unrelated lifecycle implementation A\n")

            self.assertEqual(
                validate_authority_conformance(root, policy, write=True),
                [],
            )
            receipt_path = root / AUTHORITY_CONFORMANCE_RECEIPT_PATH
            first = receipt_path.read_bytes()
            first_bundle = json.loads(first)["validator_bundle"]

            lifecycle_path.write_bytes(b"unrelated lifecycle implementation B\n")
            self.assertEqual(
                validate_authority_conformance(root, policy, write=False),
                [],
            )
            self.assertEqual(
                validate_authority_conformance(root, policy, write=True),
                [],
            )
            second = receipt_path.read_bytes()
            self.assertEqual(second, first)
            self.assertEqual(json.loads(second)["validator_bundle"], first_bundle)

    def test_structural_backdoor_and_overpermissive_policy_cannot_emit_receipt(
        self,
    ) -> None:
        legacy = conforming_policy_document()
        legacy["actions"].append("publish_draft")
        legacy["rules"].append(
            {
                "rule_id": "dormant-retained-publish",
                "effect": "allow",
                "actors": ["research_proposer"],
                "actions": ["publish_draft"],
                "resources": ["public_content_draft"],
                "conditions": [
                    {
                        "key": "automated_identity_disclosed",
                        "operator": "equals",
                        "value_type": "boolean",
                        "value": False,
                    }
                ],
                "reason_code": "RETAINED_PUBLISH_ALLOW",
            }
        )

        overpermissive = conforming_policy_document()
        query_rule = next(
            rule
            for rule in overpermissive["rules"]
            if rule["actions"] == ["query_status"]
            and rule["resources"] == ["status_projection"]
        )
        query_rule["conditions"] = []

        for name, document, message in (
            ("structural_backdoor", legacy, "contains noncatalog path"),
            ("overpermissive", overpermissive, "noncanonical predicate"),
        ):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                policy = write_revision_two_root(
                    root,
                    status="implemented",
                    policy_document=document,
                )
                with self.assertRaisesRegex(ValueError, message):
                    validate_authority_conformance(root, policy, write=True)
                self.assertFalse(
                    (root / AUTHORITY_CONFORMANCE_RECEIPT_PATH).exists()
                )


class TypedPolicyEvaluatorTests(unittest.TestCase):
    """Generic schema-2 predicate and structural policy tests."""

    @staticmethod
    def schema_two_document(
        conditions: list[dict] | None = None,
    ) -> dict:
        if conditions is None:
            conditions = [
                {
                    "key": "authorized",
                    "operator": "equals",
                    "value_type": "boolean",
                    "value": True,
                }
            ]
        return {
            "schema_version": "2.0.0",
            "constitution_version": "2.0.0",
            "lifecycle_state": "effective",
            "effective_commit": "fixture-commit",
            "default_effect": "deny",
            "promotion_event": "human_merged_commit",
            "identity_bindings": {
                "human_maintainer": ["synthetic:maintainer"],
                "worker": ["synthetic:worker"],
            },
            "actor_classes": {
                "human_maintainer": {"automated": False},
                "worker": {"automated": True},
            },
            "actions": ["inspect"],
            "resource_classes": ["status_projection"],
            "protected_surfaces": ["governance/**"],
            "separation_of_duty": [
                {
                    "rule_id": "separate-fixture-duties",
                    "scope": "fixture_lineage",
                    "constraint": (
                        "distinct_authenticated_principal_across_groups"
                    ),
                    "groups": [
                        {"duty": "author", "actor_classes": ["worker"]},
                        {
                            "duty": "reviewer",
                            "actor_classes": ["human_maintainer"],
                        },
                    ],
                }
            ],
            "rules": [
                {
                    "rule_id": "allow-worker-inspection",
                    "effect": "allow",
                    "actors": ["worker"],
                    "actions": ["inspect"],
                    "resources": ["status_projection"],
                    "conditions": conditions,
                    "reason_code": "FIXTURE_ALLOWED",
                }
            ],
            "emergency_controls": {
                "disable_changes_authority": False,
                "disable_mutates_history": False,
                "disable_stops_new_work": True,
            },
            "amendment_procedure": {
                "prior_versions_retained": True,
                "required_actor": "human_maintainer",
                "required_state_sequence": [
                    "draft",
                    "reviewed",
                    "merged",
                    "effective",
                ],
                "required_transport": "pull_request",
            },
        }

    @staticmethod
    def schema_one_document(condition: dict) -> dict:
        return {
            "schema_version": "1.0.0",
            "constitution_version": "1.0.0",
            "lifecycle_state": "effective",
            "effective_commit": "fixture-commit",
            "default_effect": "deny",
            "promotion_event": "human_merged_commit",
            "actor_classes": {
                "human_maintainer": {
                    "automated": False,
                    "conflicts_with": [],
                }
            },
            "actions": ["inspect"],
            "resource_classes": ["status_projection"],
            "protected_surfaces": ["governance/**"],
            "rules": [
                {
                    "rule_id": "legacy-inspection",
                    "effect": "allow",
                    "actors": ["human_maintainer"],
                    "actions": ["inspect"],
                    "resources": ["status_projection"],
                    "conditions": [condition],
                    "reason_code": "LEGACY_ALLOWED",
                }
            ],
            "emergency_controls": {},
            "amendment_procedure": {},
        }

    @staticmethod
    def load_document(document: dict) -> Constitution:
        return Constitution(
            deepcopy(document),
            "fixture-digest",
            Path("typed-policy-fixture.yaml"),
        )

    def decision_for(
        self,
        policy: Constitution,
        context: dict,
    ) -> bool:
        return policy.decide(
            "worker",
            "inspect",
            "status_projection",
            context,
        ).allowed

    def test_schema_two_exposes_stable_parsed_policy_api(self) -> None:
        conditions = [
            {
                "key": "attempts",
                "operator": "less_than_or_equal",
                "value_type": "integer",
                "value": 2,
            },
            {
                "key": "authorized",
                "operator": "equals",
                "value_type": "boolean",
                "value": True,
            },
            {
                "key": "target_id",
                "operator": "present",
                "value_type": "string",
            },
        ]
        policy = self.load_document(self.schema_two_document(conditions))

        self.assertEqual(policy.schema_major, 2)
        self.assertEqual(
            policy.identity_bindings,
            {
                "human_maintainer": ("synthetic:maintainer",),
                "worker": ("synthetic:worker",),
            },
        )
        self.assertEqual(
            policy.separation_of_duty_rules[0].groups[0].duty,
            "author",
        )
        decision = policy.decide(
            "worker",
            "inspect",
            "status_projection",
            {"attempts": 1, "authorized": True, "target_id": "fixture"},
        )
        self.assertEqual(decision.scope, "offline_class_policy_decision")
        self.assertEqual(decision.runtime_authority, "none")
        predicates = policy.predicates_for_rule("allow-worker-inspection")
        self.assertEqual(
            predicates[0].to_payload(),
            conditions[0],
        )
        self.assertNotIn("value", predicates[2].to_payload())
        self.assertTrue(
            self.decision_for(
                policy,
                {"attempts": 2, "authorized": True, "target_id": "target-1"},
            )
        )

    def test_loaded_policy_is_isolated_from_input_and_snapshot_mutation(self) -> None:
        document = conforming_policy_document()
        policy = Constitution(
            document,
            "immutable-fixture-digest",
            Path("immutable-policy-fixture.yaml"),
        )
        validate_authority_policy_closure(policy)
        first_rule = policy.rules[0]
        context = {}
        for condition in first_rule["conditions"]:
            if condition["operator"] == "equals":
                context[condition["key"]] = condition["value"]
            elif condition["value_type"] == "integer":
                context[condition["key"]] = 0
            elif condition["value_type"] == "sha256_digest":
                context[condition["key"]] = f"sha256:{'a' * 64}"
            elif condition["value_type"] == "utc_datetime":
                context[condition["key"]] = "2025-01-01T00:00:00Z"
            else:
                context[condition["key"]] = "fixture"
        baseline = policy.decide(
            first_rule["actors"][0],
            first_rule["actions"][0],
            first_rule["resources"][0],
            context,
        )
        self.assertTrue(baseline.allowed)

        document["rules"].clear()
        document["actor_classes"].clear()
        returned_document = policy.document
        returned_document["rules"].clear()
        returned_document["actor_classes"].clear()
        returned_rules = policy.rules
        returned_rules[0]["conditions"].clear()
        returned_rules[0]["actors"].append("human_maintainer")

        self.assertEqual(policy.digest, "immutable-fixture-digest")
        self.assertEqual(
            policy.decide(
                first_rule["actors"][0],
                first_rule["actions"][0],
                first_rule["resources"][0],
                context,
            ),
            baseline,
        )
        self.assertNotEqual(policy.document["rules"], [])
        validate_authority_policy_closure(policy)

    def test_equals_supports_each_canonical_scalar_type(self) -> None:
        digest = f"sha256:{'a' * 64}"
        cases = (
            ("boolean", True),
            ("integer", MAX_PORTABLE_INTEGER),
            ("string", "release candidate"),
            ("sha256_digest", digest),
            ("utc_datetime", "2024-02-29T23:59:59Z"),
        )
        for value_type, value in cases:
            with self.subTest(value_type=value_type):
                policy = self.load_document(
                    self.schema_two_document(
                        [
                            {
                                "key": "evidence",
                                "operator": "equals",
                                "value_type": value_type,
                                "value": value,
                            }
                        ]
                    )
                )
                self.assertTrue(self.decision_for(policy, {"evidence": value}))

    def test_schema_two_never_aliases_booleans_in_equals(self) -> None:
        cases = (
            ("boolean", True, (1, 1.0)),
            ("integer", 1, (True, 1.0)),
        )
        for value_type, expected, aliases in cases:
            policy = self.load_document(
                self.schema_two_document(
                    [
                        {
                            "key": "evidence",
                            "operator": "equals",
                            "value_type": value_type,
                            "value": expected,
                        }
                    ]
                )
            )
            self.assertTrue(self.decision_for(policy, {"evidence": expected}))
            for alias in aliases:
                with self.subTest(value_type=value_type, alias=alias):
                    self.assertFalse(
                        self.decision_for(policy, {"evidence": alias})
                    )

    def test_schema_one_equals_and_in_no_longer_alias_booleans(self) -> None:
        cases = (
            ({"key": "evidence", "operator": "equals", "value": True}, True),
            ({"key": "evidence", "operator": "equals", "value": 1}, 1),
            ({"key": "evidence", "operator": "in", "value": [True]}, True),
            ({"key": "evidence", "operator": "in", "value": [1]}, 1),
        )
        for condition, exact_value in cases:
            policy = self.load_document(self.schema_one_document(condition))
            exact = policy.decide(
                "human_maintainer",
                "inspect",
                "status_projection",
                {"evidence": exact_value},
            )
            self.assertTrue(exact.allowed)
            aliases = (1, 1.0) if exact_value is True else (True, 1.0)
            for alias in aliases:
                if type(alias) is type(exact_value):
                    continue
                with self.subTest(condition=condition, alias=alias):
                    decision = policy.decide(
                        "human_maintainer",
                        "inspect",
                        "status_projection",
                        {"evidence": alias},
                    )
                    self.assertFalse(decision.allowed)

    def test_current_revision_one_boolean_conditions_reject_numeric_aliases(
        self,
    ) -> None:
        policy = Constitution.load(CONSTITUTION_PATH)
        base_context = {"human_review_path": "pull_request"}
        self.assertTrue(
            policy.decide(
                "change_author",
                "open_pull_request",
                "pull_request",
                {**base_context, "automated_identity_disclosed": True},
            ).allowed
        )
        for alias in (1, 1.0):
            with self.subTest(alias=alias):
                self.assertFalse(
                    policy.decide(
                        "change_author",
                        "open_pull_request",
                        "pull_request",
                        {
                            **base_context,
                            "automated_identity_disclosed": alias,
                        },
                    ).allowed
                )

    def test_integer_ceiling_narrows_and_rejects_non_integer_context(self) -> None:
        policy = self.load_document(
            self.schema_two_document(
                [
                    {
                        "key": "attempts",
                        "operator": "less_than_or_equal",
                        "value_type": "integer",
                        "value": 2,
                    }
                ]
            )
        )
        for actual in (0, 1, 2):
            with self.subTest(actual=actual):
                self.assertTrue(self.decision_for(policy, {"attempts": actual}))
        for actual in (3, True, 1.0, -1, None, [], {}):
            with self.subTest(actual=actual):
                self.assertFalse(self.decision_for(policy, {"attempts": actual}))
        self.assertFalse(
            policy.decide(
                "worker",
                "inspect",
                "status_projection",
                [("attempts", 1)],
            ).allowed
        )

    def test_present_validates_nonboolean_scalar_type_and_content(self) -> None:
        cases = (
            ("integer", 0, (True, 0.0, -1, None)),
            ("string", "target", ("", " ", " target", None, [], {})),
            (
                "sha256_digest",
                f"sha256:{'f' * 64}",
                ("", "f" * 64, f"sha256:{'F' * 64}", None),
            ),
            (
                "utc_datetime",
                "2025-01-01T00:00:00Z",
                ("2025-01-01T00:00:00+00:00", "2025-02-29T00:00:00Z", None),
            ),
        )
        for value_type, valid, invalid_values in cases:
            policy = self.load_document(
                self.schema_two_document(
                    [
                        {
                            "key": "evidence",
                            "operator": "present",
                            "value_type": value_type,
                        }
                    ]
                )
            )
            self.assertTrue(self.decision_for(policy, {"evidence": valid}))
            self.assertFalse(self.decision_for(policy, {}))
            for invalid in invalid_values:
                with self.subTest(value_type=value_type, invalid=invalid):
                    self.assertFalse(
                        self.decision_for(policy, {"evidence": invalid})
                    )

    def test_mandatory_boolean_requires_explicit_equals_semantics(self) -> None:
        malformed = {
            "key": "authorized",
            "operator": "present",
            "value_type": "boolean",
        }
        with self.assertRaisesRegex(ConstitutionError, "cannot be used for boolean"):
            self.load_document(self.schema_two_document([malformed]))

        policy = self.load_document(
            self.schema_two_document(
                [
                    {
                        "key": "authorized",
                        "operator": "equals",
                        "value_type": "boolean",
                        "value": False,
                    }
                ]
            )
        )
        self.assertTrue(self.decision_for(policy, {"authorized": False}))
        for context in ({}, {"authorized": 0}, {"authorized": None}):
            self.assertFalse(self.decision_for(policy, context))

    def test_wrong_typed_operands_are_rejected_during_load(self) -> None:
        invalid_values = {
            "boolean": (1, 0, 1.0, None, "true", "", [], {}),
            "integer": (
                True,
                1.0,
                -1,
                MAX_PORTABLE_INTEGER + 1,
                None,
                "1",
                "",
                [],
                {},
            ),
            "string": (
                "",
                " ",
                " leading",
                "trailing ",
                "control\u0000",
                "control\u0085",
                "x" * (MAX_POLICY_STRING_LENGTH + 1),
                "\ud800",
                None,
                1,
                1.0,
                True,
                [],
                {},
            ),
            "sha256_digest": (
                "",
                "a" * 64,
                f"sha256:{'a' * 63}",
                f"sha256:{'A' * 64}",
                None,
                [],
                {},
            ),
            "utc_datetime": (
                "",
                "0000-01-01T00:00:00Z",
                "2025-02-29T00:00:00Z",
                "2025-01-01T00:00:00.000Z",
                "2025-01-01T00:00:00+00:00",
                "2025-01-01T00:00:60Z",
                None,
                [],
                {},
            ),
        }
        for value_type, values in invalid_values.items():
            for value in values:
                with self.subTest(value_type=value_type, value=value):
                    condition = {
                        "key": "evidence",
                        "operator": "equals",
                        "value_type": value_type,
                        "value": value,
                    }
                    with self.assertRaises(ConstitutionError):
                        self.load_document(
                            self.schema_two_document([condition])
                        )

    def test_malformed_predicate_shapes_are_rejected(self) -> None:
        malformed = (
            [],
            {},
            {"key": "evidence", "operator": "equals"},
            {
                "key": "evidence",
                "operator": "equals",
                "value_type": "string",
            },
            {
                "key": "evidence",
                "operator": "present",
                "value_type": "string",
                "value": "unexpected",
            },
            {
                "key": "evidence",
                "operator": "less_than_or_equal",
                "value_type": "string",
                "value": "two",
            },
            {
                "key": "evidence",
                "operator": "unknown",
                "value_type": "string",
                "value": "x",
            },
            {
                "key": "evidence",
                "operator": [],
                "value_type": "string",
                "value": "x",
            },
            {
                "key": "evidence",
                "operator": "equals",
                "value_type": {},
                "value": "x",
            },
            {
                "key": "evidence",
                "operator": "equals",
                "value_type": "string",
                "value": "x",
                "unexpected": True,
            },
        )
        for condition in malformed:
            with self.subTest(condition=condition):
                with self.assertRaises(ConstitutionError):
                    self.load_document(self.schema_two_document([condition]))

        duplicate_keys = self.schema_two_document(
            [
                {
                    "key": "evidence",
                    "operator": "present",
                    "value_type": "string",
                },
                {
                    "key": "evidence",
                    "operator": "present",
                    "value_type": "integer",
                },
            ]
        )
        with self.assertRaisesRegex(ConstitutionError, "duplicate predicate keys"):
            self.load_document(duplicate_keys)

        unsorted = self.schema_two_document(
            [
                {
                    "key": "zeta",
                    "operator": "present",
                    "value_type": "string",
                },
                {
                    "key": "alpha",
                    "operator": "present",
                    "value_type": "string",
                },
            ]
        )
        with self.assertRaisesRegex(ConstitutionError, "sorted by key"):
            self.load_document(unsorted)

    def test_schema_two_closes_root_actor_rule_and_condition_shapes(self) -> None:
        documents = []

        root = self.schema_two_document()
        root["alternate_policy_rules"] = []
        documents.append(root)

        actor = self.schema_two_document()
        actor["actor_classes"]["worker"]["conflicts_with"] = []
        documents.append(actor)

        rule = self.schema_two_document()
        rule["rules"][0]["alternate_conditions"] = []
        documents.append(rule)

        condition = self.schema_two_document()
        condition["rules"][0]["conditions"][0]["if_present"] = True
        documents.append(condition)

        emergency = self.schema_two_document()
        emergency["emergency_controls"]["disable_changes_authority"] = True
        documents.append(emergency)

        emergency_extension = self.schema_two_document()
        emergency_extension["emergency_controls"]["activation_authority"] = (
            "runtime_operator"
        )
        documents.append(emergency_extension)

        emergency_boolean_alias = self.schema_two_document()
        emergency_boolean_alias["emergency_controls"][
            "disable_stops_new_work"
        ] = 1
        documents.append(emergency_boolean_alias)

        amendment = self.schema_two_document()
        amendment["amendment_procedure"]["required_actor"] = "worker"
        documents.append(amendment)

        amendment_extension = self.schema_two_document()
        amendment_extension["amendment_procedure"]["direct_push"] = True
        documents.append(amendment_extension)

        amendment_boolean_alias = self.schema_two_document()
        amendment_boolean_alias["amendment_procedure"][
            "prior_versions_retained"
        ] = 1
        documents.append(amendment_boolean_alias)

        for index, document in enumerate(documents):
            with self.subTest(index=index):
                with self.assertRaises(ConstitutionError):
                    self.load_document(document)

        for required in ("identity_bindings", "separation_of_duty"):
            document = self.schema_two_document()
            del document[required]
            with self.subTest(missing=required):
                with self.assertRaises(ConstitutionError):
                    self.load_document(document)

    def test_identity_bindings_require_canonical_synthetic_principals(self) -> None:
        invalid_principals = (
            "opaque",
            "github:Alice",
            "github:alice",
            "User:alice",
            "synthetic:",
            "synthetic:Upper",
            "synthetic:has space",
            "synthetic:\u00e1lice",
            "synthetic:\u007f",
            f"synthetic:{'a' * 129}",
        )
        for principal in invalid_principals:
            with self.subTest(principal=principal):
                document = self.schema_two_document()
                document["identity_bindings"]["worker"] = [principal]
                with self.assertRaisesRegex(
                    ConstitutionError,
                    "canonical synthetic offline principal",
                ):
                    self.load_document(document)

        empty = self.schema_two_document()
        empty["identity_bindings"] = {
            "human_maintainer": [],
            "worker": [],
        }
        self.assertEqual(self.load_document(empty).identity_bindings["worker"], ())

        unsorted = self.schema_two_document()
        unsorted["identity_bindings"]["worker"] = [
            "synthetic:z",
            "synthetic:a",
        ]
        with self.assertRaisesRegex(ConstitutionError, "sorted and duplicate-free"):
            self.load_document(unsorted)

    def test_identity_and_group_assignments_cannot_bypass_separation(self) -> None:
        cross_group_principal = self.schema_two_document()
        cross_group_principal["identity_bindings"] = {
            "human_maintainer": ["synthetic:shared"],
            "worker": ["synthetic:shared"],
        }
        with self.assertRaisesRegex(ConstitutionError, "protected groups"):
            self.load_document(cross_group_principal)

        missing_actor_binding = self.schema_two_document()
        del missing_actor_binding["identity_bindings"]["worker"]
        with self.assertRaisesRegex(ConstitutionError, "exactly match"):
            self.load_document(missing_actor_binding)

        repeated_actor = self.schema_two_document()
        repeated_actor["separation_of_duty"][0]["groups"][1][
            "actor_classes"
        ] = ["worker"]
        with self.assertRaisesRegex(ConstitutionError, "more than one group"):
            self.load_document(repeated_actor)

        unsorted_groups = self.schema_two_document()
        unsorted_groups["separation_of_duty"][0]["groups"].reverse()
        with self.assertRaisesRegex(ConstitutionError, "sorted by duty"):
            self.load_document(unsorted_groups)

        unsorted_group_actors = self.schema_two_document()
        unsorted_group_actors["separation_of_duty"][0]["groups"][0][
            "actor_classes"
        ] = ["worker", "human_maintainer"]
        with self.assertRaisesRegex(ConstitutionError, "sorted and duplicate-free"):
            self.load_document(unsorted_group_actors)

        open_group = self.schema_two_document()
        open_group["separation_of_duty"][0]["groups"][0]["fallback"] = True
        with self.assertRaisesRegex(ConstitutionError, "closed group schema"):
            self.load_document(open_group)

        duplicate_rule = self.schema_two_document()
        duplicate_rule["separation_of_duty"].append(
            deepcopy(duplicate_rule["separation_of_duty"][0])
        )
        with self.assertRaisesRegex(ConstitutionError, "duplicate separation"):
            self.load_document(duplicate_rule)

        unsorted_rules = self.schema_two_document()
        earlier_rule = deepcopy(unsorted_rules["separation_of_duty"][0])
        earlier_rule["rule_id"] = "another-duty-rule"
        unsorted_rules["separation_of_duty"].append(earlier_rule)
        with self.assertRaisesRegex(ConstitutionError, "sorted by rule_id"):
            self.load_document(unsorted_rules)

    def test_schema_two_caps_and_canonicalizes_policy_strings(self) -> None:
        mutations = []

        effective_commit = self.schema_two_document()
        effective_commit["effective_commit"] = " commit "
        mutations.append(effective_commit)

        protected_surface = self.schema_two_document()
        protected_surface["protected_surfaces"] = ["governance/\u0085/**"]
        mutations.append(protected_surface)

        token = self.schema_two_document()
        overlong_token = "a" * (MAX_POLICY_TOKEN_LENGTH + 1)
        token["actions"] = [overlong_token]
        token["rules"][0]["actions"] = [overlong_token]
        mutations.append(token)

        rule_id = self.schema_two_document()
        rule_id["rules"][0]["rule_id"] = "a" * (MAX_POLICY_TOKEN_LENGTH + 1)
        mutations.append(rule_id)

        reason = self.schema_two_document()
        reason["rules"][0]["reason_code"] = "A" * (
            MAX_POLICY_TOKEN_LENGTH + 1
        )
        mutations.append(reason)

        for index, document in enumerate(mutations):
            with self.subTest(index=index):
                with self.assertRaises(ConstitutionError):
                    self.load_document(document)

    def test_duplicate_yaml_keys_fail_before_policy_evaluation(self) -> None:
        documents = (
            "schema_version: 1.0.0\nschema_version: 1.0.0\n",
            (
                "actor_classes:\n"
                "  human_maintainer:\n"
                "    automated: false\n"
                "    automated: true\n"
            ),
        )
        for payload in documents:
            with self.subTest(payload=payload), tempfile.TemporaryDirectory() as temporary:
                path = Path(temporary) / "constitution.yaml"
                path.write_text(payload, encoding="utf-8")
                with self.assertRaisesRegex(ConstitutionError, "duplicate key"):
                    Constitution.load(path)

    def test_json_schema_accepts_both_majors_and_rejects_v2_backdoors(self) -> None:
        schema = json.loads(
            (ROOT / "governance/authority.schema.json").read_text(encoding="utf-8")
        )
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(
            schema,
            format_checker=FormatChecker(),
        )
        revision_one = yaml.safe_load(CONSTITUTION_PATH.read_text(encoding="utf-8"))
        self.assertEqual(list(validator.iter_errors(revision_one)), [])
        self.assertEqual(
            list(validator.iter_errors(self.schema_two_document())),
            [],
        )

        alternate_rule = self.schema_two_document()
        alternate_rule["alternate_policy_rules"] = []
        self.assertNotEqual(list(validator.iter_errors(alternate_rule)), [])

        opaque_principal = self.schema_two_document()
        opaque_principal["identity_bindings"]["worker"] = ["opaque"]
        self.assertNotEqual(list(validator.iter_errors(opaque_principal)), [])

        malformed_actor_key = self.schema_two_document()
        malformed_actor_key["identity_bindings"]["Worker Alias"] = []
        self.assertNotEqual(list(validator.iter_errors(malformed_actor_key)), [])

        unsafe_emergency = self.schema_two_document()
        unsafe_emergency["emergency_controls"]["disable_stops_new_work"] = False
        self.assertNotEqual(list(validator.iter_errors(unsafe_emergency)), [])

        unsafe_amendment = self.schema_two_document()
        unsafe_amendment["amendment_procedure"]["required_transport"] = "direct_push"
        self.assertNotEqual(list(validator.iter_errors(unsafe_amendment)), [])

        null_operand = self.schema_two_document()
        null_operand["rules"][0]["conditions"][0]["value"] = None
        self.assertNotEqual(list(validator.iter_errors(null_operand)), [])


if __name__ == "__main__":
    unittest.main()
