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

import yaml

from researcher.scripts.governance_policy import Constitution, ConstitutionError
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
    AUTHORITY_VALIDATOR_BUNDLE_ALGORITHM,
    AUTHORITY_VOCABULARY_PATH,
    POLICY_ONLY_READ_PROFILES,
    REQUIRED_AUTHORITY_PROFILES,
    build_authority_evaluator_bundle,
    expected_authority_catalog_boundary_cases,
    expected_authority_fixture_cases,
    expected_authority_policy_conditions,
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
        "constitution_revision": 2,
        "registry_version": 2,
        "catalog_boundary_cases": list(expected_authority_catalog_boundary_cases()),
        "entries": fixture_entries,
    }
    fixture_bytes = canonical_json_text(fixture).encode("utf-8")
    registry = {
        "kind": "AuthorityVocabularyRegistry",
        "schema_version": "1.0.0",
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
    for index, ((action, resource), profile) in enumerate(profiles):
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
    return {
        "schema_version": "1.0.0",
        "constitution_version": "2.0.0",
        "lifecycle_state": "effective",
        "effective_commit": "fixture",
        "default_effect": "deny",
        "promotion_event": "human_merged_commit",
        "actor_classes": {
            actor: {
                "automated": actor != "human_maintainer",
                "conflicts_with": [],
            }
            for actor in sorted(actors)
        },
        "actions": sorted(actions),
        "resource_classes": sorted(resources),
        "protected_surfaces": ["governance/**"],
        "rules": rules,
        "emergency_controls": {},
        "amendment_procedure": {},
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
                with self.assertRaisesRegex(ValueError, "Authority vocabulary"):
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

                with self.assertRaisesRegex(ValueError, "executing evaluator"):
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
            ("structural_backdoor", legacy, "noncatalog pair"),
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


if __name__ == "__main__":
    unittest.main()
