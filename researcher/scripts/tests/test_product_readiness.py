"""Tests for the product readiness declaration boundary."""

from __future__ import annotations

import json
import hashlib
import tempfile
import unittest
from copy import deepcopy
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from researcher.scripts.validate_product_readiness import (
    SpecState,
    StrictJSONError,
    load_strict_json,
    main,
    validate_manifest,
)


ROOT = Path(__file__).resolve().parents[3]


def spec_states(**overrides: str) -> dict[str, SpecState]:
    states: dict[str, SpecState] = {}
    for number in range(27):
        spec_id = f"SPEC-{number:03d}"
        status = overrides.get(spec_id, "draft")
        states[spec_id] = SpecState(
            status=status,
            revision=1,
            path=f"docs/specs/{spec_id}-fixture.md",
        )
    return states


def blocked_manifest() -> dict:
    return {
        "schema_version": "1.0.0",
        "product_id": "agent-skills-suite",
        "authority": {
            "active_environment_id": None,
            "authoritative": False,
            "baseline_commit": "1" * 40,
            "candidate_commit": None,
            "candidate_state": "uncommitted_worktree",
            "certification_mode": "blocked_assessment_only",
            "notice": "Non-authoritative fixture.",
            "production_ready": False,
            "production_scope": [],
        },
        "capabilities": [
            {
                "id": "control-center-ui",
                "product_id": "research-control-center",
                "category": "ui_surface",
                "status": "preparatory",
                "required_specs": ["SPEC-008", "SPEC-024"],
                "activation_enabled": False,
                "evidence": ["apps/control-center"],
                "blockers": ["Owner specifications are draft."],
            }
        ],
        "environments": [
            {
                "id": "hosted-beta",
                "status": "planned",
                "activation_enabled": False,
                "required_specs": ["SPEC-024", "SPEC-025"],
                "components": ["control-center-ui"],
            }
        ],
        "test_gates": [
            {
                "id": "ui-build",
                "status": "implemented",
                "evidence": ["apps/control-center/package.json"],
            }
        ],
        "blockers": ["The runtime-owning specifications are not operational."],
    }


class ProductReadinessValidationTests(unittest.TestCase):
    def test_pr_audit_observation_binds_exact_raw_query_outputs(self) -> None:
        receipt_path = ROOT / "docs/product/pr-audit-receipt-2026-08-25.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        capture = receipt["capture"]

        for path_field, digest_field in (
            ("default_branch_raw_path", "default_branch_raw_sha256"),
            ("pull_request_raw_path", "pull_request_raw_sha256"),
            ("ruleset_raw_path", "ruleset_raw_sha256"),
        ):
            raw_path = ROOT / capture[path_field]
            self.assertTrue(raw_path.is_file())
            observed = hashlib.sha256(raw_path.read_bytes()).hexdigest()
            self.assertEqual(observed, capture[digest_field])

        raw_prs = json.loads((ROOT / capture["pull_request_raw_path"]).read_text())
        raw_rules = json.loads((ROOT / capture["ruleset_raw_path"]).read_text())
        raw_default_branch = json.loads(
            (ROOT / capture["default_branch_raw_path"]).read_text()
        )
        self.assertEqual(receipt["default_branch_observation"], raw_default_branch)
        self.assertEqual(
            raw_default_branch["object"]["sha"], receipt["default_branch_commit"]
        )
        self.assertEqual(receipt["pull_requests"], raw_prs)
        self.assertEqual(receipt["default_branch_ruleset"], raw_rules)
        self.assertEqual(len(raw_prs), 36)
        self.assertEqual(raw_rules["source"], receipt["repository"])
        self.assertEqual(raw_rules["target"], "branch")
        self.assertEqual(
            raw_rules["conditions"]["ref_name"]["include"], ["~DEFAULT_BRANCH"]
        )

    def test_manifest_declares_public_product_owner_specs(self) -> None:
        manifest = json.loads(
            (ROOT / "docs/product/production-readiness.json").read_text(encoding="utf-8")
        )
        required = {
            capability["id"]: capability["required_specs"]
            for capability in manifest["capabilities"]
        }
        self.assertEqual(required["skills.catalog"], ["SPEC-001", "SPEC-003"])
        self.assertEqual(
            required["skills.packaging"], ["SPEC-001", "SPEC-002", "SPEC-003"]
        )
        self.assertEqual(
            required["skills.release-validation"],
            ["SPEC-000", "SPEC-001", "SPEC-002", "SPEC-003"],
        )

    def test_truthful_blocked_declaration_is_valid(self) -> None:
        self.assertEqual(validate_manifest(blocked_manifest(), spec_states()), [])

    def test_activation_fails_when_owner_spec_is_not_operational(self) -> None:
        manifest = blocked_manifest()
        manifest["authority"]["authoritative"] = True
        manifest["capabilities"][0]["activation_enabled"] = True
        codes = [
            finding.code for finding in validate_manifest(manifest, spec_states())
        ]
        self.assertIn("OWNER_SPEC_NOT_OPERATIONAL", codes)
        self.assertIn("AUTHORITY_SPEC_NOT_OPERATIONAL", codes)
        self.assertIn("ACTIVE_CAPABILITY_HAS_BLOCKERS", codes)

    def test_activation_fails_while_capability_declares_blockers(self) -> None:
        manifest = blocked_manifest()
        manifest["authority"]["authoritative"] = True
        manifest["capabilities"][0]["activation_enabled"] = True
        operational = spec_states(
            **{
                "SPEC-000": "operational",
                "SPEC-008": "operational",
                "SPEC-024": "operational",
            }
        )
        codes = [
            finding.code for finding in validate_manifest(manifest, operational)
        ]
        self.assertIn("ACTIVE_CAPABILITY_HAS_BLOCKERS", codes)

    def test_unknown_spec_and_component_fail_closed(self) -> None:
        manifest = blocked_manifest()
        manifest["capabilities"][0]["required_specs"] = ["SPEC-999"]
        manifest["environments"][0]["components"] = ["missing-component"]
        codes = [
            finding.code for finding in validate_manifest(manifest, spec_states())
        ]
        self.assertIn("UNKNOWN_SPEC", codes)
        self.assertIn("UNKNOWN_ENVIRONMENT_COMPONENT", codes)

    def test_production_ready_requires_authority_gates_and_active_environment(self) -> None:
        manifest = blocked_manifest()
        manifest["authority"]["production_ready"] = True
        codes = [
            finding.code for finding in validate_manifest(manifest, spec_states())
        ]
        self.assertGreaterEqual(codes.count("FALSE_PRODUCTION_READY"), 3)

    def test_v1_cannot_self_certify_an_operational_fixture(self) -> None:
        manifest = blocked_manifest()
        manifest["authority"] = {
            "active_environment_id": "hosted-beta",
            "authoritative": True,
            "baseline_commit": "1" * 40,
            "candidate_commit": "2" * 40,
            "candidate_state": "committed",
            "certification_mode": "blocked_assessment_only",
            "notice": "Authoritative operational fixture.",
            "production_ready": True,
            "production_scope": ["control-center-ui"],
        }
        manifest["capabilities"][0]["activation_enabled"] = True
        manifest["capabilities"][0]["blockers"] = []
        manifest["capabilities"][0]["status"] = "operational"
        manifest["environments"][0]["activation_enabled"] = True
        manifest["environments"][0]["status"] = "active"
        manifest["test_gates"][0]["status"] = "passing"
        manifest["blockers"] = []
        operational = spec_states(
            **{
                "SPEC-000": "operational",
                "SPEC-008": "operational",
                "SPEC-024": "operational",
                "SPEC-025": "operational",
            }
        )
        findings = validate_manifest(manifest, operational)
        self.assertEqual(
            [finding.code for finding in findings],
            ["READINESS_CERTIFICATION_UNSUPPORTED"],
        )

    def test_ready_rejects_arbitrary_statuses_and_nonexistent_evidence(self) -> None:
        manifest = blocked_manifest()
        manifest["authority"] = {
            "active_environment_id": "hosted-beta",
            "authoritative": True,
            "baseline_commit": "1" * 40,
            "candidate_commit": "2" * 40,
            "candidate_state": "committed",
            "certification_mode": "blocked_assessment_only",
            "notice": "Authoritative operational fixture.",
            "production_ready": True,
            "production_scope": ["control-center-ui"],
        }
        manifest["capabilities"][0].update(
            {
                "activation_enabled": True,
                "blockers": [],
                "evidence": ["does/not/exist"],
                "status": "definitely-not-implemented",
            }
        )
        manifest["environments"][0].update(
            {
                "activation_enabled": True,
                "status": "not-active",
            }
        )
        manifest["test_gates"][0].update(
            {
                "evidence": ["also/missing"],
                "status": "passing",
            }
        )
        manifest["blockers"] = []
        operational = spec_states(
            **{
                "SPEC-000": "operational",
                "SPEC-008": "operational",
                "SPEC-024": "operational",
                "SPEC-025": "operational",
            }
        )

        codes = [
            finding.code for finding in validate_manifest(manifest, operational)
        ]
        self.assertIn("INVALID_CAPABILITY_STATUS", codes)
        self.assertIn("ACTIVE_CAPABILITY_NOT_OPERATIONAL", codes)
        self.assertIn("ACTIVE_CAPABILITY_WITHOUT_REPOSITORY_EVIDENCE", codes)
        self.assertIn("INVALID_ENVIRONMENT_STATUS", codes)
        self.assertIn("ENABLED_ENVIRONMENT_NOT_ACTIVE", codes)
        self.assertIn("PASSING_GATE_WITHOUT_REPOSITORY_EVIDENCE", codes)

    def test_deferred_capability_may_remain_outside_production_scope(self) -> None:
        manifest = blocked_manifest()
        manifest["authority"] = {
            "active_environment_id": "hosted-beta",
            "authoritative": True,
            "baseline_commit": "1" * 40,
            "candidate_commit": "2" * 40,
            "candidate_state": "committed",
            "certification_mode": "blocked_assessment_only",
            "notice": "Authoritative operational fixture.",
            "production_ready": True,
            "production_scope": ["control-center-ui"],
        }
        manifest["capabilities"][0].update(
            {"activation_enabled": True, "blockers": [], "status": "operational"}
        )
        manifest["capabilities"].append(
            {
                "id": "future-training",
                "product_id": "research-control-center",
                "category": "deferred_lab",
                "status": "deferred",
                "required_specs": ["SPEC-026"],
                "activation_enabled": False,
                "evidence": ["docs/specs/SPEC-026-training-rl-lab.md"],
                "blockers": ["Deferred from the production scope."],
            }
        )
        manifest["environments"][0].update(
            {"activation_enabled": True, "status": "active"}
        )
        manifest["test_gates"][0]["status"] = "passing"
        manifest["blockers"] = []
        operational = spec_states(
            **{
                "SPEC-000": "operational",
                "SPEC-008": "operational",
                "SPEC-024": "operational",
                "SPEC-025": "operational",
            }
        )

        findings = validate_manifest(manifest, operational)
        self.assertEqual(
            [finding.code for finding in findings],
            ["READINESS_CERTIFICATION_UNSUPPORTED"],
        )

    def test_duplicate_capability_and_gate_ids_fail(self) -> None:
        manifest = blocked_manifest()
        manifest["capabilities"].append(deepcopy(manifest["capabilities"][0]))
        manifest["test_gates"].append(deepcopy(manifest["test_gates"][0]))
        codes = [
            finding.code for finding in validate_manifest(manifest, spec_states())
        ]
        self.assertIn("DUPLICATE_CAPABILITY", codes)
        self.assertIn("DUPLICATE_TEST_GATE", codes)

    def test_non_ready_declaration_requires_a_blocker(self) -> None:
        manifest = blocked_manifest()
        manifest["blockers"] = []
        codes = [
            finding.code for finding in validate_manifest(manifest, spec_states())
        ]
        self.assertIn("MISSING_READINESS_BLOCKER", codes)

    def test_strict_json_rejects_duplicate_keys_and_nonfinite_numbers(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "manifest.json"
            for body in ('{"x": 1, "x": 2}', '{"x": NaN}'):
                path.write_text(body, encoding="utf-8")
                with self.assertRaises(StrictJSONError):
                    load_strict_json(path)

    def test_strict_json_reads_canonical_object(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "manifest.json"
            payload = blocked_manifest()
            path.write_text(json.dumps(payload), encoding="utf-8")
            self.assertEqual(load_strict_json(path), payload)

    def test_cli_distinguishes_truthful_validation_from_release_gate(self) -> None:
        with redirect_stdout(StringIO()):
            self.assertEqual(main(["--root", str(ROOT)]), 0)
            self.assertEqual(main(["--root", str(ROOT), "--require-ready"]), 2)


if __name__ == "__main__":
    unittest.main()
