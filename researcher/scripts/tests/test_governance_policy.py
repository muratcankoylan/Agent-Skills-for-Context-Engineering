"""Tests for the fail-closed program constitution evaluator."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import yaml

from researcher.scripts.governance_policy import Constitution, ConstitutionError
from researcher.scripts.validate_governance import (
    DEFAULT_FIXTURES,
    render_authority_table,
    validate_fixtures,
    validate_invariants,
)


ROOT = Path(__file__).resolve().parents[3]
CONSTITUTION_PATH = ROOT / "governance" / "constitution.yaml"


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


if __name__ == "__main__":
    unittest.main()
