"""Adversarial tests for the allowlisted public export boundary."""

from __future__ import annotations

import base64
import copy
import json
import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from researcher.scripts.build_inventory import pretty_json, record_digest, sha256_bytes
from researcher.scripts.export_policy import (
    DEFAULT_POLICY_PATH,
    ExportBoundaryError,
    ExportPolicy,
    check_staging,
    ensure_private_record_path,
    plan_export,
    render_export,
)


ROOT = Path(__file__).resolve().parents[3]


def citation_source(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "title": "Synthetic Restricted Harness Study",
        "url": "https://example.invalid/restricted",
        "source_type": "restricted_fixture",
        "authors": ["Fixture Author"],
        "published_at": "2026-08-10",
        "license_note": "Metadata only",
        "body": "SYNTHETIC_RESTRICTED_BODY_MUST_NOT_EXPORT_42",
    }
    value.update(overrides)
    return value


def export_request(**entry_overrides: object) -> dict[str, object]:
    entry: dict[str, object] = {
        "entry_id": "entry_fixture",
        "projection_id": "proj_fixture",
        "source_path": "source.json",
        "source_classification": "restricted_source",
        "artifact_kind": "citation_metadata",
        "transformation_id": "restricted_citation_v1",
        "output_path": "citation/fixture.json",
    }
    entry.update(entry_overrides)
    return {
        "schema_version": "1.0.0",
        "id": "export_fixture",
        "kind": "ExportRequest",
        "classification": "private_operational",
        "retention": "review_cycle",
        "entries": [entry],
    }


class ExportBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.policy = ExportPolicy.load(DEFAULT_POLICY_PATH)

    def workspace(self, source: dict[str, object] | None = None) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        private = root / "private"
        private.mkdir()
        (private / "source.json").write_text(
            pretty_json(source or citation_source()), encoding="utf-8"
        )
        return temporary, root

    def assert_code(self, code: str, operation) -> None:
        with self.assertRaises(ExportBoundaryError) as raised:
            operation()
        self.assertEqual(raised.exception.code, code)

    def test_restricted_source_projects_metadata_without_raw_body(self) -> None:
        temporary, root = self.workspace()
        self.addCleanup(temporary.cleanup)
        plan = plan_export(export_request(), root / "private", self.policy)
        manifest, receipt = render_export(plan, root / "private", root / "staging", self.policy)
        validation = check_staging(root / "staging", self.policy)
        public_bytes = (root / "staging/citation/fixture.json").read_bytes()
        manifest_bytes = (root / "staging/export-manifest.json").read_bytes()
        self.assertNotIn(b"SYNTHETIC_RESTRICTED_BODY", public_bytes)
        self.assertNotIn(b"source_path", manifest_bytes)
        self.assertNotIn(b"source_digest", manifest_bytes)
        self.assertEqual(manifest["classification"], "public_derived")
        self.assertEqual(receipt["classification"], "private_operational")
        self.assertIn("source_digest", receipt["sources"][0])
        self.assertEqual(validation["result"], "pass")

    def test_plan_is_private_and_binds_exact_source(self) -> None:
        temporary, root = self.workspace()
        self.addCleanup(temporary.cleanup)
        plan = plan_export(export_request(), root / "private", self.policy)
        self.assertEqual(plan["classification"], "private_operational")
        self.assertRegex(plan["entries"][0]["source_digest"], r"^sha256:[0-9a-f]{64}$")
        self.assertEqual(plan["entries"][0]["source_path"], "source.json")

    def test_render_is_byte_deterministic_across_fresh_directories(self) -> None:
        temporary, root = self.workspace()
        self.addCleanup(temporary.cleanup)
        plan = plan_export(export_request(), root / "private", self.policy)
        first_manifest, first_receipt = render_export(
            plan, root / "private", root / "staging-one", self.policy
        )
        second_manifest, second_receipt = render_export(
            plan, root / "private", root / "staging-two", self.policy
        )
        self.assertEqual(first_manifest, second_manifest)
        self.assertEqual(first_receipt, second_receipt)
        for relative in ["export-manifest.json", "citation/fixture.json"]:
            self.assertEqual(
                (root / "staging-one" / relative).read_bytes(),
                (root / "staging-two" / relative).read_bytes(),
            )

    def test_secret_reference_source_is_denied(self) -> None:
        temporary, root = self.workspace()
        self.addCleanup(temporary.cleanup)
        request = export_request(source_classification="secret_reference")
        self.assert_code(
            "CLASSIFICATION_DENIED",
            lambda: plan_export(request, root / "private", self.policy),
        )

    def test_unknown_request_field_is_denied(self) -> None:
        temporary, root = self.workspace()
        self.addCleanup(temporary.cleanup)
        request = export_request()
        request["ambient_authority"] = True
        self.assert_code("UNKNOWN_FIELD", lambda: plan_export(request, root / "private", self.policy))

    def test_unknown_entry_field_is_denied(self) -> None:
        temporary, root = self.workspace()
        self.addCleanup(temporary.cleanup)
        request = export_request()
        request["entries"][0]["credential"] = "fixture"
        self.assert_code("UNKNOWN_FIELD", lambda: plan_export(request, root / "private", self.policy))

    def test_source_path_traversal_is_denied(self) -> None:
        temporary, root = self.workspace()
        self.addCleanup(temporary.cleanup)
        request = export_request(source_path="../source.json")
        self.assert_code("PATH_ESCAPE", lambda: plan_export(request, root / "private", self.policy))

    def test_output_path_traversal_is_denied(self) -> None:
        temporary, root = self.workspace()
        self.addCleanup(temporary.cleanup)
        request = export_request(output_path="citation/../../escape.json")
        self.assert_code("PATH_ESCAPE", lambda: plan_export(request, root / "private", self.policy))

    def test_casefolded_output_collision_is_denied(self) -> None:
        temporary, root = self.workspace()
        self.addCleanup(temporary.cleanup)
        request = export_request()
        second = copy.deepcopy(request["entries"][0])
        second.update(
            {
                "entry_id": "entry_second",
                "projection_id": "proj_second",
                "output_path": "citation/FIXTURE.json",
            }
        )
        request["entries"].append(second)
        self.assert_code("PATH_COLLISION", lambda: plan_export(request, root / "private", self.policy))

    @unittest.skipIf(not hasattr(os, "symlink"), "symlink support required")
    def test_symlink_source_is_denied(self) -> None:
        temporary, root = self.workspace()
        self.addCleanup(temporary.cleanup)
        source = root / "private/source.json"
        real = root / "real.json"
        source.replace(real)
        source.symlink_to(real)
        self.assert_code(
            "PATH_ESCAPE",
            lambda: plan_export(export_request(), root / "private", self.policy),
        )

    def test_source_change_after_plan_is_denied(self) -> None:
        temporary, root = self.workspace()
        self.addCleanup(temporary.cleanup)
        plan = plan_export(export_request(), root / "private", self.policy)
        (root / "private/source.json").write_text(
            pretty_json(citation_source(title="Changed")), encoding="utf-8"
        )
        self.assert_code(
            "SOURCE_CHANGED",
            lambda: render_export(plan, root / "private", root / "staging", self.policy),
        )
        self.assertFalse((root / "staging").exists())

    def test_existing_staging_directory_is_denied(self) -> None:
        temporary, root = self.workspace()
        self.addCleanup(temporary.cleanup)
        plan = plan_export(export_request(), root / "private", self.policy)
        (root / "staging").mkdir()
        self.assert_code(
            "OUTPUT_EXISTS",
            lambda: render_export(plan, root / "private", root / "staging", self.policy),
        )

    def test_concurrent_render_has_one_winner_and_one_typed_denial(self) -> None:
        temporary, root = self.workspace()
        self.addCleanup(temporary.cleanup)
        plan = plan_export(export_request(), root / "private", self.policy)

        def attempt() -> str:
            try:
                render_export(plan, root / "private", root / "staging", self.policy)
                return "success"
            except ExportBoundaryError as exc:
                return exc.code

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: attempt(), range(2)))
        self.assertEqual(results.count("success"), 1)
        self.assertEqual(len(set(results) & {"OUTPUT_BUSY", "OUTPUT_EXISTS"}), 1)

    def test_extra_staged_file_is_denied(self) -> None:
        temporary, root = self.workspace()
        self.addCleanup(temporary.cleanup)
        plan = plan_export(export_request(), root / "private", self.policy)
        render_export(plan, root / "private", root / "staging", self.policy)
        (root / "staging/extra.txt").write_text("extra", encoding="utf-8")
        self.assert_code("UNAPPROVED_OUTPUT", lambda: check_staging(root / "staging", self.policy))

    def test_tampered_output_is_denied(self) -> None:
        temporary, root = self.workspace()
        self.addCleanup(temporary.cleanup)
        plan = plan_export(export_request(), root / "private", self.policy)
        render_export(plan, root / "private", root / "staging", self.policy)
        output = root / "staging/citation/fixture.json"
        output.write_text(output.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        self.assert_code("DIGEST_MISMATCH", lambda: check_staging(root / "staging", self.policy))

    def test_private_manifest_field_is_denied(self) -> None:
        temporary, root = self.workspace()
        self.addCleanup(temporary.cleanup)
        plan = plan_export(export_request(), root / "private", self.policy)
        render_export(plan, root / "private", root / "staging", self.policy)
        manifest_path = root / "staging/export-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["source_digest"] = plan["entries"][0]["source_digest"]
        manifest_path.write_text(pretty_json(manifest), encoding="utf-8")
        self.assert_code("UNKNOWN_FIELD", lambda: check_staging(root / "staging", self.policy))

    def test_plain_hex_and_base64_canaries_are_denied(self) -> None:
        canary = "synthetic-canary-9d8547"
        variants = [canary, canary.encode().hex(), base64.b64encode(canary.encode()).decode()]
        for index, variant in enumerate(variants):
            with self.subTest(index=index):
                source = {
                    "title": "Private review",
                    "summary": variant,
                    "reason_code": "FIXTURE",
                }
                temporary, root = self.workspace(source)
                try:
                    request = export_request(
                        source_classification="private_human",
                        artifact_kind="research_summary",
                        transformation_id="research_summary_v1",
                        output_path=f"research-summary/fixture-{index}.json",
                    )
                    plan = plan_export(request, root / "private", self.policy)
                    self.assert_code(
                        "SECRET_CANARY",
                        lambda: render_export(
                            plan,
                            root / "private",
                            root / "staging",
                            self.policy,
                            canaries=[canary],
                        ),
                    )
                finally:
                    temporary.cleanup()

    def test_high_confidence_secret_structures_are_denied(self) -> None:
        patterns = [
            "-----BEGIN PRIVATE KEY-----",
            "Authorization: Bearer fixture-token",
            "https://example.invalid/?X-Amz-Signature=fixture",
            "/Users/private-user/Library/fixture",
        ]
        for index, text in enumerate(patterns):
            with self.subTest(index=index):
                source = {"title": "Private review", "summary": text, "reason_code": "FIXTURE"}
                temporary, root = self.workspace(source)
                try:
                    request = export_request(
                        source_classification="private_human",
                        artifact_kind="research_summary",
                        transformation_id="research_summary_v1",
                        output_path=f"research-summary/pattern-{index}.json",
                    )
                    plan = plan_export(request, root / "private", self.policy)
                    self.assert_code(
                        "SECRET_PATTERN",
                        lambda: render_export(plan, root / "private", root / "staging", self.policy),
                    )
                finally:
                    temporary.cleanup()

    def test_invalid_projected_field_type_leaves_no_staging_tree(self) -> None:
        temporary, root = self.workspace(citation_source(authors=7))
        self.addCleanup(temporary.cleanup)
        plan = plan_export(export_request(), root / "private", self.policy)
        self.assert_code(
            "SOURCE_INVALID",
            lambda: render_export(plan, root / "private", root / "staging", self.policy),
        )
        self.assertFalse((root / "staging").exists())
        self.assertEqual(list(root.glob(".staging.*")), [])

    def test_duplicate_json_keys_in_source_are_denied(self) -> None:
        temporary, root = self.workspace()
        self.addCleanup(temporary.cleanup)
        (root / "private/source.json").write_text(
            '{"title":"a","title":"b","url":"x","source_type":"fixture"}',
            encoding="utf-8",
        )
        self.assert_code(
            "SOURCE_INVALID",
            lambda: plan_export(export_request(), root / "private", self.policy),
        )

    @unittest.skipIf(not hasattr(os, "symlink"), "symlink support required")
    def test_symlink_in_staged_tree_is_denied(self) -> None:
        temporary, root = self.workspace()
        self.addCleanup(temporary.cleanup)
        plan = plan_export(export_request(), root / "private", self.policy)
        render_export(plan, root / "private", root / "staging", self.policy)
        output = root / "staging/citation/fixture.json"
        outside = root / "outside.json"
        output.replace(outside)
        output.symlink_to(outside)
        self.assert_code("PATH_ESCAPE", lambda: check_staging(root / "staging", self.policy))

    @unittest.skipIf(not hasattr(os, "link"), "hardlink support required")
    def test_hardlink_in_staged_tree_is_denied(self) -> None:
        temporary, root = self.workspace()
        self.addCleanup(temporary.cleanup)
        plan = plan_export(export_request(), root / "private", self.policy)
        render_export(plan, root / "private", root / "staging", self.policy)
        output = root / "staging/citation/fixture.json"
        outside = root / "outside.json"
        os.link(output, outside)
        self.assert_code("PATH_ESCAPE", lambda: check_staging(root / "staging", self.policy))

    def test_policy_digest_change_invalidates_plan(self) -> None:
        temporary, root = self.workspace()
        self.addCleanup(temporary.cleanup)
        plan = plan_export(export_request(), root / "private", self.policy)
        changed_policy = ExportPolicy(
            copy.deepcopy(self.policy.document),
            "sha256:" + "f" * 64,
            self.policy.source,
        )
        self.assert_code(
            "POLICY_MISMATCH",
            lambda: render_export(plan, root / "private", root / "staging", changed_policy),
        )

    def test_unknown_projected_output_field_is_denied(self) -> None:
        temporary, root = self.workspace()
        self.addCleanup(temporary.cleanup)
        plan = plan_export(export_request(), root / "private", self.policy)
        render_export(plan, root / "private", root / "staging", self.policy)
        output_path = root / "staging/citation/fixture.json"
        output = json.loads(output_path.read_text(encoding="utf-8"))
        output["unexpected"] = "value"
        output_body = pretty_json(output).encode()
        output_path.write_bytes(output_body)
        manifest_path = root / "staging/export-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["entries"][0]["output_digest"] = sha256_bytes(output_body)
        manifest["entries"][0]["size_bytes"] = len(output_body)
        manifest_path.write_text(pretty_json(manifest), encoding="utf-8")
        self.assert_code("UNKNOWN_FIELD", lambda: check_staging(root / "staging", self.policy))

    def test_private_record_destination_inside_repo_is_restricted(self) -> None:
        self.assert_code(
            "PRIVATE_DESTINATION_REQUIRED",
            lambda: ensure_private_record_path(ROOT / "researcher/exports/plan.json"),
        )
        ensure_private_record_path(ROOT / "researcher/exports/private/plan.json")
        ensure_private_record_path(ROOT / "Private/plan.json")

    def test_transformation_digest_is_policy_bound(self) -> None:
        transform = self.policy.transforms["restricted_citation_v1"]
        temporary, root = self.workspace()
        self.addCleanup(temporary.cleanup)
        plan = plan_export(export_request(), root / "private", self.policy)
        manifest, _ = render_export(plan, root / "private", root / "staging", self.policy)
        self.assertEqual(manifest["entries"][0]["transformation_digest"], record_digest(transform))


if __name__ == "__main__":
    unittest.main()
