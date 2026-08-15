"""Determinism and reconciliation tests for the generated corpus inventory."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

from researcher.scripts.build_inventory import (
    InventoryBuilder,
    atomic_write_text,
    pretty_json,
    render_summary,
)
from researcher.scripts.governance_policy import Constitution
from researcher.scripts.tests.test_spec_lifecycle import (
    authority_conformance_document,
    authority_documents,
    canonical_json,
    conforming_constitution,
)
from researcher.scripts.validate_spec_lifecycle import (
    AUTHORITY_CONFORMANCE_RECEIPT_PATH,
    AUTHORITY_CONSTITUTION_POLICY_PATH,
    AUTHORITY_FIXTURE_MANIFEST_PATH,
    AUTHORITY_VALIDATOR_PATH,
    AUTHORITY_VOCABULARY_PATH,
    AuthorityVocabularyBinding,
    parse_authority_vocabulary,
)


ROOT = Path(__file__).resolve().parents[3]


def copy_fixture(source: Path, target: Path) -> None:
    """Copy only inputs consumed by InventoryBuilder, excluding large runtime trees."""

    target.mkdir(parents=True, exist_ok=True)
    for relative in [
        ".claude-plugin/marketplace.json",
        ".plugin/plugin.json",
        ".github/workflows/validate.yml",
        "SKILL.md",
        "README.md",
        "AGENTS.md",
        "CLAUDE.md",
        "requirements-dev.in",
        "requirements-dev.txt",
        "researcher/README.md",
        "researcher/mechanisms/registry.jsonl",
        "researcher/mechanisms/ledgers/accepted.jsonl",
        "researcher/mechanisms/ledgers/rejected.jsonl",
        "researcher/claims/index.jsonl",
        "researcher/corpus/index.json",
        "researcher/corpus/inventory.schema.json",
        "governance/constitution.yaml",
        "governance/export-policy.yaml",
        "governance/export-policy.schema.json",
        "researcher/exports/schemas/export-records.schema.json",
        "researcher/fixtures/export/restricted-request.json",
        "researcher/fixtures/export/private-root/restricted-source.json",
        "researcher/exports/examples/restricted-citation-v1/export-manifest.json",
        "researcher/exports/examples/restricted-citation-v1/citation/restricted-fixture.json",
        "researcher/fixtures/activation-cases.jsonl",
        "researcher/benchmarks/router/prompts.jsonl",
        "researcher/benchmarks/scenarios/adversarial.jsonl",
        "researcher/benchmarks/goldens/adversarial-goldens.json",
        "researcher/benchmarks/PLAN.md",
        "researcher/benchmarks/router/README.md",
        "researcher/benchmarks/effectiveness/README.md",
        "researcher/benchmarks/sdk-runner/README.md",
        "researcher/benchmarks/sdk-runner/package.json",
        "researcher/benchmarks/sdk-runner/package-lock.json",
        "researcher/benchmarks/sdk-runner/tsconfig.json",
        "researcher/benchmarks/sdk-runner/src/common.ts",
        "researcher/benchmarks/sdk-runner/src/durableFs.test.ts",
        "researcher/benchmarks/sdk-runner/src/durableFs.ts",
        "researcher/benchmarks/sdk-runner/src/durableJson.test.ts",
        "researcher/benchmarks/sdk-runner/src/durableJson.ts",
        "researcher/benchmarks/sdk-runner/src/liveBlock.test.ts",
        "researcher/benchmarks/sdk-runner/src/routerEngine.test.ts",
        "researcher/benchmarks/sdk-runner/src/routerEngine.ts",
        "researcher/benchmarks/sdk-runner/src/routerManifest.test.ts",
        "researcher/benchmarks/sdk-runner/src/routerManifest.ts",
        "researcher/benchmarks/sdk-runner/src/routerRunStore.test.ts",
        "researcher/benchmarks/sdk-runner/src/routerRunStore.ts",
        "researcher/benchmarks/sdk-runner/src/sdkImport.test.ts",
        "researcher/benchmarks/sdk-runner/src/sourceFreeze.test.ts",
        "researcher/benchmarks/sdk-runner/src/sourceFreeze.ts",
        "researcher/benchmarks/sdk-runner/src/runRouter.ts",
        "researcher/benchmarks/sdk-runner/src/runEffectiveness.ts",
        "researcher/benchmarks/sdk-runner/test/denyCursorSdkLoader.mjs",
        "researcher/benchmarks/sdk-runner/test/registerDenyCursorSdk.mjs",
        "researcher/scripts/validate_governance.py",
        "researcher/scripts/build_inventory.py",
        "researcher/scripts/render_router_report.py",
        "researcher/scripts/tests/test_render_router_report.py",
        "researcher/scripts/validate_spec_lifecycle.py",
        "researcher/scripts/validate_export.py",
        "researcher/scripts/export_policy.py",
        "researcher/scripts/validate_public_repo.py",
        "researcher/scripts/tests/test_public_repo.py",
        "researcher/scripts/tests/test_spec_lifecycle.py",
        "researcher/artifacts/README.md",
        "researcher/runbooks/schema-migration.md",
        "researcher/scripts/validate_schemas.py",
        "researcher/scripts/schema_contract.py",
        "researcher/scripts/artifact_store.py",
        "researcher/scripts/migrate_legacy.py",
        "researcher/scripts/tests/test_schema_contract.py",
        "researcher/scripts/tests/test_artifact_store.py",
        "researcher/scripts/validate_platform_compat.py",
        "researcher/scripts/validate_repo.py",
        "researcher/scripts/skill_health.py",
        "researcher/scripts/check_activation_cases.py",
        "researcher/scripts/run_benchmarks.py",
    ]:
        source_path = source / relative
        target_path = target / relative
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)

    for schema_file in sorted((source / "researcher/schemas").rglob("*")):
        if not schema_file.is_file() or "node_modules" in schema_file.parts:
            continue
        target_path = target / schema_file.relative_to(source)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(schema_file, target_path)

    for skill_file in sorted((source / "skills").glob("*/SKILL.md")):
        target_path = target / skill_file.relative_to(source)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(skill_file, target_path)

    for readme in sorted((source / "examples").glob("*/README.md")):
        target_path = target / readme.relative_to(source)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(readme, target_path)

    shutil.copytree(source / "docs" / "specs", target / "docs" / "specs")
    shutil.copytree(source / "docs" / "decisions", target / "docs" / "decisions")
    shutil.copytree(
        source / "researcher" / "orchestration" / "prompts",
        target / "researcher" / "orchestration" / "prompts",
    )
    review = source / "docs" / "reviews" / "2026-08-15-autonomous-organization-readiness.md"
    target_review = target / review.relative_to(source)
    target_review.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(review, target_review)

    source_tasks = source / "researcher" / "benchmarks" / "effectiveness" / "tasks"
    target_tasks = target / "researcher" / "benchmarks" / "effectiveness" / "tasks"
    shutil.copytree(source_tasks, target_tasks)


def finding_codes(root: Path) -> set[str]:
    builder = InventoryBuilder(root)
    builder.build()
    return {finding.code for finding in builder.findings}


def write_generic_spec000_revision_two(root: Path, *, status: str = "accepted") -> None:
    path = root / "docs/specs/SPEC-000-program-constitution.md"
    original_bytes = path.read_bytes()
    prior_digest = f"sha256:{hashlib.sha256(original_bytes).hexdigest()}"
    text = original_bytes.decode("utf-8")
    if "Status: amended\n" in text:
        text = text.replace("Status: amended", f"Status: {status}", 1)
    else:
        text = text.replace("Status: implemented", f"Status: {status}", 1)
    text = text.replace("Revision: 1", "Revision: 2", 1)
    text = text.replace("Revises: none", f"Revises: {prior_digest}", 1)
    text = text.replace("Adoption decision: ADR-0005\n", "", 1)
    text = text.replace("Lifecycle decision: ADR-0008\n", "", 1)
    text = text.replace("Replacement: SPEC-000@2\n", "", 1)
    path.write_text(text, encoding="utf-8")


def write_authority_revision(
    root: Path,
    *,
    status: str = "accepted",
    include_conformance: bool = False,
) -> AuthorityVocabularyBinding:
    _registry, _fixture, registry_bytes, fixture_bytes = authority_documents()
    binding = parse_authority_vocabulary(
        registry_bytes,
        expected_digest=f"sha256:{hashlib.sha256(registry_bytes).hexdigest()}",
        expected_constitution_revision=2,
        expected_registry_version=2,
        fixture_manifest_bytes=fixture_bytes,
    )
    registry_path = root / AUTHORITY_VOCABULARY_PATH
    fixture_path = root / AUTHORITY_FIXTURE_MANIFEST_PATH
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    fixture_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_bytes(registry_bytes)
    fixture_path.write_bytes(fixture_bytes)

    write_generic_spec000_revision_two(root, status=status)
    spec_path = root / "docs/specs/SPEC-000-program-constitution.md"
    spec_text = spec_path.read_text(encoding="utf-8")
    authority_metadata = (
        f"Authority vocabulary: {binding.path}\n"
        f"Authority vocabulary digest: {binding.digest}\n"
        f"Authority vocabulary version: {binding.registry_version}\n"
    )
    spec_text = spec_text.replace(
        "Dependency revisions: none\n",
        f"Dependency revisions: none\n{authority_metadata}",
        1,
    )
    spec_path.write_text(spec_text, encoding="utf-8")

    if include_conformance:
        policy_path = root / AUTHORITY_CONSTITUTION_POLICY_PATH
        policy_document = conforming_constitution().document
        policy_path.write_text(
            yaml.safe_dump(policy_document, sort_keys=False),
            encoding="utf-8",
        )
        constitution = Constitution.load(policy_path)
        validator_bytes = (root / AUTHORITY_VALIDATOR_PATH).read_bytes()
        _receipt, receipt_bytes = authority_conformance_document(
            binding,
            constitution,
            validator_bytes,
        )
        receipt_path = root / AUTHORITY_CONFORMANCE_RECEIPT_PATH
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_bytes(receipt_bytes)

    return binding


def replace_spec000_metadata(root: Path, key: str, value: str) -> None:
    path = root / "docs/specs/SPEC-000-program-constitution.md"
    text = path.read_text(encoding="utf-8")
    prefix = f"{key}: "
    lines = text.splitlines(keepends=True)
    matches = [index for index, line in enumerate(lines) if line.startswith(prefix)]
    if len(matches) != 1:
        raise AssertionError(f"expected one {key!r} metadata line, found {len(matches)}")
    newline = "\n" if lines[matches[0]].endswith("\n") else ""
    lines[matches[0]] = f"{prefix}{value}{newline}"
    path.write_text("".join(lines), encoding="utf-8")


def replace_spec004_status(root: Path, status: str) -> None:
    path = root / "docs/specs/SPEC-004-event-journal.md"
    text = path.read_text(encoding="utf-8")
    text = text.replace("Status: draft", f"Status: {status}", 1)
    text = text.replace(
        "Depends on: SPEC-000, SPEC-001, SPEC-002, SPEC-003\n",
        "Depends on: SPEC-000, SPEC-001, SPEC-002, SPEC-003\n"
        "Dependency revisions: SPEC-000@2, SPEC-001@1, SPEC-002@1, SPEC-003@1\n",
        1,
    )
    path.write_text(text, encoding="utf-8")


class RepositoryInventoryTests(unittest.TestCase):
    def fixture(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name) / "repo"
        copy_fixture(ROOT, root)
        return temporary, root

    def test_current_repository_has_no_unresolved_references(self) -> None:
        builder = InventoryBuilder(ROOT)
        inventory = builder.build()
        self.assertEqual(builder.findings, [])
        self.assertEqual(inventory["unresolved_references"], [])

    def test_two_builds_are_byte_identical(self) -> None:
        first = InventoryBuilder(ROOT).build()
        second = InventoryBuilder(ROOT).build()
        self.assertEqual(pretty_json(first), pretty_json(second))
        self.assertEqual(render_summary(first), render_summary(second))

    def test_committed_generated_outputs_match_builder(self) -> None:
        inventory = InventoryBuilder(ROOT).build()
        self.assertEqual(
            (ROOT / "researcher/corpus/inventory.json").read_text(encoding="utf-8"),
            pretty_json(inventory),
        )
        self.assertEqual(
            (ROOT / "researcher/generated/corpus-summary.md").read_text(encoding="utf-8"),
            render_summary(inventory),
        )

    def test_generated_files_do_not_affect_source_tree_digest(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        first = InventoryBuilder(root).build()["source_tree_digest"]
        inventory_path = root / "researcher/corpus/inventory.json"
        summary_path = root / "researcher/generated/corpus-summary.md"
        inventory_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        inventory_path.write_text("generated noise", encoding="utf-8")
        summary_path.write_text("generated noise", encoding="utf-8")
        second = InventoryBuilder(root).build()["source_tree_digest"]
        self.assertEqual(first, second)

    def test_canonical_input_change_updates_source_tree_digest(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        first = InventoryBuilder(root).build()["source_tree_digest"]
        skill = root / "skills/context-fundamentals/SKILL.md"
        skill.write_text(skill.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        second = InventoryBuilder(root).build()["source_tree_digest"]
        self.assertNotEqual(first, second)

    def test_unregistered_root_benchmark_runner_file_is_source_bound_and_rejected(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        path = root / "researcher/benchmarks/sdk-runner/unregistered.env"
        path.write_text("UNREGISTERED=true\n", encoding="utf-8")
        builder = InventoryBuilder(root)
        inventory = builder.build()
        self.assertIn(
            ("UNREGISTERED_BENCHMARK_RUNNER_CONTRACT", path.relative_to(root).as_posix()),
            {(finding.code, finding.path) for finding in builder.findings},
        )
        self.assertIn(path.relative_to(root).as_posix(), {source["path"] for source in inventory["sources"]})

    def test_unregistered_nested_benchmark_runner_file_is_source_bound_and_rejected(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        path = root / "researcher/benchmarks/sdk-runner/tools/dist/unregistered.js"
        path.parent.mkdir(parents=True)
        path.write_text("export const unsafe = true;\n", encoding="utf-8")
        builder = InventoryBuilder(root)
        inventory = builder.build()
        self.assertIn(
            ("UNREGISTERED_BENCHMARK_RUNNER_CONTRACT", path.relative_to(root).as_posix()),
            {(finding.code, finding.path) for finding in builder.findings},
        )
        self.assertIn(path.relative_to(root).as_posix(), {source["path"] for source in inventory["sources"]})

    def test_benchmark_runner_vendor_and_generated_roots_are_excluded(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        runner_dir = root / "researcher/benchmarks/sdk-runner"
        paths = [runner_dir / "node_modules/vendor.js", runner_dir / "dist/generated.js"]
        for path in paths:
            path.parent.mkdir(parents=True)
            path.write_text("generated\n", encoding="utf-8")
        builder = InventoryBuilder(root)
        inventory = builder.build()
        source_paths = {source["path"] for source in inventory["sources"]}
        for path in paths:
            self.assertNotIn(path.relative_to(root).as_posix(), source_paths)
        self.assertNotIn(
            "UNREGISTERED_BENCHMARK_RUNNER_CONTRACT",
            {finding.code for finding in builder.findings},
        )

    def test_benchmark_methodology_change_updates_source_tree_digest(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        before = InventoryBuilder(root).build()
        path = root / "researcher/benchmarks/PLAN.md"
        path.write_text(path.read_text(encoding="utf-8") + "\nMethodology candidate.\n", encoding="utf-8")
        after = InventoryBuilder(root).build()
        before_records = {
            record["id"]: record for record in before["artifacts"]["benchmark_runners"]["records"]
        }
        after_records = {
            record["id"]: record for record in after["artifacts"]["benchmark_runners"]["records"]
        }
        self.assertNotEqual(before_records["methodology:PLAN.md"]["digest"], after_records["methodology:PLAN.md"]["digest"])
        self.assertNotEqual(before["source_tree_digest"], after["source_tree_digest"])

    def test_benchmark_stage_readmes_are_records_and_sources(self) -> None:
        inventory = InventoryBuilder(ROOT).build()
        records = {
            record["id"]: record
            for record in inventory["artifacts"]["benchmark_runners"]["records"]
        }
        expected = {
            "methodology:router:README.md": "researcher/benchmarks/router/README.md",
            "methodology:effectiveness:README.md": (
                "researcher/benchmarks/effectiveness/README.md"
            ),
        }
        source_paths = {source["path"] for source in inventory["sources"]}
        for record_id, path in expected.items():
            with self.subTest(record_id=record_id):
                self.assertEqual(records[record_id]["path"], path)
                self.assertIn(path, source_paths)

    def test_benchmark_stage_readme_mutations_update_bound_digests(self) -> None:
        cases = {
            "methodology:router:README.md": "researcher/benchmarks/router/README.md",
            "methodology:effectiveness:README.md": (
                "researcher/benchmarks/effectiveness/README.md"
            ),
        }
        for record_id, relative in cases.items():
            with self.subTest(record_id=record_id):
                temporary, root = self.fixture()
                self.addCleanup(temporary.cleanup)
                before = InventoryBuilder(root).build()
                path = root / relative
                path.write_text(
                    path.read_text(encoding="utf-8") + "\nReview mutation.\n",
                    encoding="utf-8",
                )
                after = InventoryBuilder(root).build()
                before_records = {
                    record["id"]: record
                    for record in before["artifacts"]["benchmark_runners"]["records"]
                }
                after_records = {
                    record["id"]: record
                    for record in after["artifacts"]["benchmark_runners"]["records"]
                }
                before_sources = {source["path"]: source for source in before["sources"]}
                after_sources = {source["path"]: source for source in after["sources"]}
                self.assertNotEqual(
                    before_records[record_id]["digest"],
                    after_records[record_id]["digest"],
                )
                self.assertNotEqual(
                    before_sources[relative]["digest"],
                    after_sources[relative]["digest"],
                )
                self.assertNotEqual(before["source_tree_digest"], after["source_tree_digest"])

    def test_benchmark_runner_status_fails_closed_with_live_execution_removed(self) -> None:
        category = InventoryBuilder(ROOT).build()["artifacts"]["benchmark_runners"]
        self.assertEqual(
            category["status"],
            {"router": "dry_run_only", "effectiveness": "scaffold_dry_run_only"},
        )
        private_substrate = {
            "src:durableFs.test.ts",
            "src:durableFs.ts",
            "src:durableJson.test.ts",
            "src:durableJson.ts",
            "src:routerEngine.test.ts",
            "src:routerEngine.ts",
            "src:routerManifest.test.ts",
            "src:routerManifest.ts",
            "src:routerRunStore.test.ts",
            "src:routerRunStore.ts",
            "src:sourceFreeze.test.ts",
            "src:sourceFreeze.ts",
        }
        self.assertTrue(
            private_substrate.issubset({record["id"] for record in category["records"]})
        )

    def test_router_report_accounting_and_evidence_are_source_bound(self) -> None:
        inventory = InventoryBuilder(ROOT).build()
        validator_paths = {
            record["path"] for record in inventory["artifacts"]["validators"]["records"]
        }
        support_paths = {
            record["path"]
            for record in inventory["artifacts"]["validators"]["support_files"]
        }
        self.assertIn("researcher/scripts/render_router_report.py", validator_paths)
        self.assertIn(
            "researcher/scripts/tests/test_render_router_report.py",
            support_paths,
        )

    def test_specification_program_is_inventory_backed(self) -> None:
        inventory = InventoryBuilder(ROOT).build()
        specifications = inventory["artifacts"]["specifications"]
        self.assertEqual(specifications["count"], 27)
        self.assertEqual(
            {record["id"] for record in specifications["records"]},
            {f"SPEC-{number:03d}" for number in range(27)},
        )

    def test_architecture_decisions_are_inventory_backed(self) -> None:
        inventory = InventoryBuilder(ROOT).build()
        decisions = inventory["artifacts"]["architecture_decisions"]
        self.assertEqual(decisions["count"], 10)
        self.assertEqual(
            {record["id"] for record in decisions["records"]},
            {f"ADR-{number:04d}" for number in range(1, 11)},
        )

    def test_orchestration_briefs_are_inventory_backed_and_non_authoritative(self) -> None:
        inventory = InventoryBuilder(ROOT).build()
        briefs = inventory["artifacts"]["orchestration_briefs"]
        self.assertEqual(briefs["count"], 7)
        self.assertEqual(
            briefs["owner"],
            "SPEC-005, SPEC-012, SPEC-013, and SPEC-014 bootstrap proposal",
        )
        self.assertEqual(briefs["authority"], "none")
        self.assertEqual(briefs["activation_ceiling"], "supervised_proposal")
        self.assertEqual(briefs["enforcement_boundary"], "external_harness")
        self.assertEqual(briefs["attempt_manifest_instance_classification"], "private")
        self.assertEqual(
            briefs["model_visible_launch"],
            "allowlisted_new_identity_projection_only",
        )
        self.assertEqual(
            briefs["public_projection"],
            "allowlisted_new_identity_projection_only",
        )
        self.assertEqual(
            briefs["checkpoint_contract"],
            "SPEC-005 CheckpointEnvelope with SPEC-012 ContextCheckpointPayload",
        )
        self.assertEqual(briefs["attempt_separation"], "builder_and_verifier_distinct")
        self.assertTrue(briefs["closed_prompt_namespace"])
        self.assertTrue(all(record["status"] == "bootstrap_proposal" for record in briefs["records"]))
        roles = {record["role"] for record in briefs["records"]}
        self.assertEqual(
            roles,
            {
                "attempt_manifest_template",
                "bundle_contract",
                "readiness_review",
                "resume_template",
                "root_brief",
                "verifier_brief",
                "work_brief_template",
            },
        )
        source_paths = {record["path"] for record in inventory["sources"]}
        self.assertTrue({record["path"] for record in briefs["records"]} <= source_paths)

    def test_orchestration_brief_change_updates_source_tree_digest(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        before = InventoryBuilder(root).build()["source_tree_digest"]
        path = root / "researcher/orchestration/prompts/organization-root-brief.md"
        path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        after = InventoryBuilder(root).build()["source_tree_digest"]
        self.assertNotEqual(before, after)

    def test_orchestration_briefs_avoid_self_hashes_and_bind_verifier_criteria(self) -> None:
        resume = (
            ROOT / "researcher/orchestration/prompts/resume-brief.template.md"
        ).read_text(encoding="utf-8")
        verifier = (
            ROOT / "researcher/orchestration/prompts/fresh-verifier-brief.md"
        ).read_text(encoding="utf-8")
        work_brief = (
            ROOT / "researcher/orchestration/prompts/spec-work-brief.template.md"
        ).read_text(encoding="utf-8")

        envelope_block = resume.split("### SPEC-005 CheckpointEnvelope", 1)[1].split(
            "```", 2
        )[1]
        self.assertNotIn("checkpoint_envelope_digest:", envelope_block)
        self.assertIn(
            "It is never a member of the envelope it hashes.",
            resume,
        )

        ready_predicates = verifier.split("`ready` is permitted if and only if", 1)[1]
        self.assertIn("criteria digest equals the exact criteria contract", ready_predicates)
        self.assertIn("criteria-derivation receipt", ready_predicates)
        self.assertIn("evaluator epoch, policy, rubric, thresholds", ready_predicates)
        self.assertIn("required_passing_conclusion", ready_predicates)
        self.assertIn("can never yield `ready`", ready_predicates)

        self.assertNotIn("scheduled|decision_available", work_brief)
        self.assertIn("event_driven_single_delivery_no_progress_polling", work_brief)
        self.assertIn("never exposes hidden-evaluation scheduling or progress", work_brief)

    def test_unregistered_orchestration_brief_is_reported_and_source_bound(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        before = InventoryBuilder(root).build()["source_tree_digest"]
        extra = root / "researcher/orchestration/prompts/shadow-brief.md"
        extra.write_text("# Shadow brief\n", encoding="utf-8")
        builder = InventoryBuilder(root)
        after = builder.build()["source_tree_digest"]
        self.assertNotEqual(before, after)
        self.assertIn(
            "UNREGISTERED_ORCHESTRATION_BRIEF",
            {finding.code for finding in builder.findings},
        )

    def test_architecture_decision_change_updates_source_tree_digest(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        before = InventoryBuilder(root).build()["source_tree_digest"]
        path = root / "docs/decisions/0006-validate-public-release-boundary.md"
        path.write_text(path.read_text(encoding="utf-8") + "\nAmendment candidate.\n", encoding="utf-8")
        after = InventoryBuilder(root).build()["source_tree_digest"]
        self.assertNotEqual(before, after)

    def test_unindexed_architecture_decision_is_reported(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        source = root / "docs/decisions/0006-validate-public-release-boundary.md"
        extra = root / "docs/decisions/0007-unindexed.md"
        extra.write_text(
            source.read_text(encoding="utf-8")
            .replace("ADR-0006", "ADR-0007", 1)
            .replace("SPEC-000, SPEC-002", "SPEC-000", 1),
            encoding="utf-8",
        )
        self.assertIn("MISSING_ADR_INDEX_LINK", finding_codes(root))

    def test_hidden_architecture_decision_link_cannot_satisfy_index_coverage(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        path = root / "docs/decisions/README.md"
        row = (
            "- [ADR-0006: Validate the complete public release boundary]"
            "(0006-validate-public-release-boundary.md)"
        )
        text = path.read_text(encoding="utf-8").replace(
            row,
            f"<!-- {row} -->\n   ```markdown\n{row}\n   ```",
            1,
        )
        path.write_text(text, encoding="utf-8")
        self.assertIn("MISSING_ADR_INDEX_LINK", finding_codes(root))

    def test_case_variant_architecture_decision_extension_is_source_bound_and_rejected(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        before = InventoryBuilder(root).build()["source_tree_digest"]
        source = root / "docs/decisions/0006-validate-public-release-boundary.md"
        invalid = root / "docs/decisions/0007-shadow.MD"
        invalid.write_text(
            source.read_text(encoding="utf-8").replace("ADR-0006", "ADR-0007", 1),
            encoding="utf-8",
        )
        builder = InventoryBuilder(root)
        after = builder.build()["source_tree_digest"]
        self.assertNotEqual(before, after)
        self.assertIn("INVALID_ADR_FILENAME", {finding.code for finding in builder.findings})

    def test_alternate_architecture_decision_extension_is_source_bound_and_rejected(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        before = InventoryBuilder(root).build()["source_tree_digest"]
        invalid = root / "docs/decisions/0007-shadow.markdown"
        invalid.write_text("# ADR-0007: Shadow decision\n", encoding="utf-8")
        builder = InventoryBuilder(root)
        after = builder.build()["source_tree_digest"]
        self.assertNotEqual(before, after)
        self.assertIn("INVALID_ADR_FILENAME", {finding.code for finding in builder.findings})

    def test_raw_html_cannot_hide_architecture_decision_index(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        path = root / "docs/decisions/README.md"
        text = path.read_text(encoding="utf-8").replace(
            "## Records",
            "<pre>\n## Records",
            1,
        )
        path.write_text(text + "\n</pre>\n", encoding="utf-8")
        self.assertIn("INVALID_ADR_INDEX", finding_codes(root))

    def test_architecture_decision_metadata_is_strict_and_calendar_valid(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        path = root / "docs/decisions/0006-validate-public-release-boundary.md"
        text = path.read_text(encoding="utf-8")
        text = text.replace("- Status: accepted", "- Status: accepted\n- Status: proposed", 1)
        text = text.replace("- Date: 2026-08-10", "- Date: 2026-99-99", 1)
        path.write_text(text, encoding="utf-8")
        codes = finding_codes(root)
        self.assertIn("INVALID_ADR_METADATA", codes)
        self.assertIn("INVALID_ADR_DATE", codes)

    def test_architecture_decision_supersession_is_explicit_and_resolved(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        path = root / "docs/decisions/0006-validate-public-release-boundary.md"
        original = path.read_text(encoding="utf-8")
        mutated = original.replace(
            "- Specs: SPEC-000, SPEC-002",
            "- Specs: SPEC-000, SPEC-002\n- Supersedes: ADR-9999",
            1,
        )
        self.assertNotEqual(original, mutated)
        path.write_text(mutated, encoding="utf-8")
        self.assertIn("DANGLING_ADR_SUPERSESSION", finding_codes(root))

    def test_adr_supersession_must_point_backward(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        decisions = root / "docs/decisions"
        first = decisions / "0007-first.md"
        second = decisions / "0008-second.md"
        first.write_text(
            "# ADR-0007: First\n\n- Status: accepted\n- Date: 2026-08-11\n"
            "- Spec: SPEC-004\n- Supersedes: ADR-0008\n\n## Decision\n\nFirst.\n",
            encoding="utf-8",
        )
        second.write_text(
            "# ADR-0008: Second\n\n- Status: accepted\n- Date: 2026-08-11\n"
            "- Spec: SPEC-004\n- Supersedes: ADR-0007\n\n## Decision\n\nSecond.\n",
            encoding="utf-8",
        )
        index = decisions / "README.md"
        index.write_text(
            index.read_text(encoding="utf-8")
            + "\n- [ADR-0007: First](0007-first.md)\n"
            + "- [ADR-0008: Second](0008-second.md)\n",
            encoding="utf-8",
        )
        self.assertIn("INVALID_ADR_SUPERSESSION", finding_codes(root))

    def test_spec_adoption_decision_must_be_accepted(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        path = root / "docs/decisions/0005-canonical-specification-program.md"
        original = path.read_text(encoding="utf-8")
        mutated = original.replace("- Status: accepted", "- Status: proposed", 1)
        self.assertNotEqual(original, mutated)
        path.write_text(mutated, encoding="utf-8")
        self.assertIn("UNACCEPTED_SPEC_ADOPTION_DECISION", finding_codes(root))

    def test_spec_adoption_decision_must_scope_the_specification(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        path = root / "docs/decisions/0005-canonical-specification-program.md"
        original = path.read_text(encoding="utf-8")
        mutated = original.replace(
            "- Specs: SPEC-000 through SPEC-026",
            "- Specs: SPEC-004 through SPEC-026",
            1,
        )
        self.assertNotEqual(original, mutated)
        path.write_text(mutated, encoding="utf-8")
        self.assertIn("OUT_OF_SCOPE_SPEC_ADOPTION_DECISION", finding_codes(root))

    def test_spec_heading_must_match_filename(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        path = root / "docs/specs/SPEC-004-event-journal.md"
        path.write_text(
            path.read_text(encoding="utf-8").replace("# SPEC-004:", "# SPEC-005:", 1),
            encoding="utf-8",
        )
        self.assertIn("SPEC_FILENAME_MISMATCH", finding_codes(root))

    def test_duplicate_specification_id_is_reported(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        source = root / "docs/specs/SPEC-004-event-journal.md"
        duplicate = root / "docs/specs/SPEC-027-duplicate.md"
        shutil.copy2(source, duplicate)
        self.assertIn("DUPLICATE_SPEC_ID", finding_codes(root))

    def test_nonconforming_specification_filename_is_not_silently_ignored(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        source = root / "docs/specs/SPEC-026-training-rl-lab.md"
        invalid = root / "docs/specs/SPEC-027.md"
        invalid.write_text(
            source.read_text(encoding="utf-8").replace("SPEC-026", "SPEC-027"),
            encoding="utf-8",
        )
        self.assertIn("INVALID_SPEC_FILENAME", finding_codes(root))

    def test_lowercase_specification_filename_is_source_bound_and_rejected(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        before = InventoryBuilder(root).build()["source_tree_digest"]
        source = root / "docs/specs/SPEC-026-training-rl-lab.md"
        invalid = root / "docs/specs/spec-027-shadow.md"
        invalid.write_text(
            source.read_text(encoding="utf-8").replace("SPEC-026", "SPEC-027"),
            encoding="utf-8",
        )
        builder = InventoryBuilder(root)
        after = builder.build()["source_tree_digest"]
        self.assertNotEqual(before, after)
        self.assertIn("INVALID_SPEC_FILENAME", {finding.code for finding in builder.findings})

    def test_case_variant_specification_extension_is_source_bound_and_rejected(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        before = InventoryBuilder(root).build()["source_tree_digest"]
        source = root / "docs/specs/SPEC-026-training-rl-lab.md"
        invalid = root / "docs/specs/SPEC-027-shadow.MD"
        invalid.write_text(
            source.read_text(encoding="utf-8").replace("SPEC-026", "SPEC-027"),
            encoding="utf-8",
        )
        builder = InventoryBuilder(root)
        after = builder.build()["source_tree_digest"]
        self.assertNotEqual(before, after)
        self.assertIn("INVALID_SPEC_FILENAME", {finding.code for finding in builder.findings})

    def test_alternate_specification_extension_is_source_bound_and_rejected(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        before = InventoryBuilder(root).build()["source_tree_digest"]
        invalid = root / "docs/specs/SPEC-027-shadow.markdown"
        invalid.write_text("# SPEC-027: Shadow specification\n", encoding="utf-8")
        builder = InventoryBuilder(root)
        after = builder.build()["source_tree_digest"]
        self.assertNotEqual(before, after)
        self.assertIn("INVALID_SPEC_FILENAME", {finding.code for finding in builder.findings})

    def test_raw_html_cannot_hide_specification_index(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        path = root / "docs/specs/README.md"
        text = path.read_text(encoding="utf-8").replace(
            "## Specification index",
            "<pre>\n## Specification index",
            1,
        )
        path.write_text(text + "\n</pre>\n", encoding="utf-8")
        self.assertIn("INVALID_SPEC_INDEX", finding_codes(root))

    def test_nested_specification_is_source_bound_and_rejected(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        before = InventoryBuilder(root).build()["source_tree_digest"]
        source = root / "docs/specs/SPEC-004-event-journal.md"
        nested = root / "docs/specs/archive/SPEC-004-conflict.md"
        nested.parent.mkdir(parents=True)
        shutil.copy2(source, nested)
        builder = InventoryBuilder(root)
        after = builder.build()["source_tree_digest"]
        self.assertNotEqual(before, after)
        self.assertIn("INVALID_SPEC_PATH", {finding.code for finding in builder.findings})

    def test_invalid_specification_metadata_is_reported(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        path = root / "docs/specs/SPEC-004-event-journal.md"
        text = path.read_text(encoding="utf-8")
        text = text.replace("Status: draft", "Status: maybe", 1)
        text = text.replace("Classification: split", "Classification: unknown", 1)
        text = text.replace("Wave: 1", "Wave: nine", 1)
        path.write_text(text, encoding="utf-8")
        codes = finding_codes(root)
        self.assertIn("INVALID_SPEC_STATUS", codes)
        self.assertIn("INVALID_SPEC_CLASSIFICATION", codes)
        self.assertIn("INVALID_SPEC_WAVE", codes)

    def test_specification_revision_metadata_is_strict(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        path = root / "docs/specs/SPEC-004-event-journal.md"
        text = path.read_text(encoding="utf-8")
        text = text.replace("Revision: 1", "Revision: 2", 1)
        path.write_text(text, encoding="utf-8")
        self.assertIn("INVALID_SPEC_REVISION", finding_codes(root))

    def test_specification_metadata_serialization_is_canonical(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        path = root / "docs/specs/SPEC-004-event-journal.md"
        original = path.read_text(encoding="utf-8")
        mutated = original.replace("Status: draft", "Status:    draft   ", 1)
        self.assertNotEqual(original, mutated)
        path.write_text(mutated, encoding="utf-8")
        self.assertIn("INVALID_SPEC_METADATA_FORMAT", finding_codes(root))

    def test_deferred_training_activation_is_revision_bound(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        path = root / "docs/specs/SPEC-026-training-rl-lab.md"
        original = path.read_text(encoding="utf-8")
        mutated = original.replace("Activation: deferred", "Activation: active", 1)
        self.assertNotEqual(original, mutated)
        path.write_text(mutated, encoding="utf-8")
        self.assertIn("INVALID_SPEC_ACTIVATION", finding_codes(root))

    def test_active_specification_binds_every_direct_dependency_revision(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        path = root / "docs/specs/SPEC-002-public-private-boundary.md"
        original = path.read_text(encoding="utf-8")
        mutated = (
            original.replace("Status: amended\n", "Status: implemented\n", 1)
            .replace(
                "Lifecycle decision: ADR-0010\nReplacement: SPEC-002@2\n",
                "",
                1,
            )
            .replace(
                "Dependency revisions: SPEC-000@1\n",
                "Dependency revisions: none\n",
                1,
            )
        )
        self.assertNotEqual(original, mutated)
        path.write_text(mutated, encoding="utf-8")
        self.assertEqual(
            finding_codes(root),
            {"SPEC_DEPENDENCY_REVISION_MISMATCH"},
        )

    def test_downstream_active_spec_requires_authority_vocabulary_floor(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        path = root / "docs/specs/SPEC-004-event-journal.md"
        original = path.read_text(encoding="utf-8")
        mutated = original.replace("Status: draft", "Status: architecture_reviewed", 1)
        mutated = mutated.replace(
            "Depends on: SPEC-000, SPEC-001, SPEC-002, SPEC-003\n",
            "Depends on: SPEC-000, SPEC-001, SPEC-002, SPEC-003\n"
            "Dependency revisions: SPEC-000@1, SPEC-001@1, SPEC-002@1, SPEC-003@1\n",
            1,
        )
        self.assertNotEqual(original, mutated)
        path.write_text(mutated, encoding="utf-8")
        self.assertIn(
            "SPEC_AUTHORITY_VOCABULARY_NOT_READY",
            finding_codes(root),
        )

    def test_spec000_revision_two_requires_registry_and_fixture(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        write_generic_spec000_revision_two(root)
        self.assertIn("SPEC_AUTHORITY_VOCABULARY_INVALID", finding_codes(root))

        for relative in (
            AUTHORITY_VOCABULARY_PATH,
            AUTHORITY_FIXTURE_MANIFEST_PATH,
        ):
            with self.subTest(missing=relative):
                temporary, root = self.fixture()
                self.addCleanup(temporary.cleanup)
                write_authority_revision(root)
                (root / relative).unlink()
                self.assertIn("SPEC_AUTHORITY_VOCABULARY_INVALID", finding_codes(root))

    def test_unowned_and_premature_authority_artifacts_are_rejected(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        _registry, _fixture, registry_bytes, fixture_bytes = authority_documents()
        registry_path = root / AUTHORITY_VOCABULARY_PATH
        fixture_path = root / AUTHORITY_FIXTURE_MANIFEST_PATH
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        registry_path.write_bytes(registry_bytes)
        fixture_path.write_bytes(fixture_bytes)
        self.assertIn("UNEXPECTED_AUTHORITY_ARTIFACT", finding_codes(root))

        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        write_authority_revision(root, status="accepted", include_conformance=True)
        self.assertIn("UNEXPECTED_AUTHORITY_ARTIFACT", finding_codes(root))

    def test_authority_metadata_path_digest_and_version_are_exact(self) -> None:
        mutations = (
            ("Authority vocabulary", "governance/detached-authority.json"),
            ("Authority vocabulary digest", "sha256:" + "0" * 64),
            ("Authority vocabulary version", "3"),
            ("Authority vocabulary version", "02"),
        )
        for key, value in mutations:
            with self.subTest(key=key, value=value):
                temporary, root = self.fixture()
                self.addCleanup(temporary.cleanup)
                write_authority_revision(root)
                replace_spec000_metadata(root, key, value)
                self.assertIn("SPEC_AUTHORITY_VOCABULARY_INVALID", finding_codes(root))

    def test_authority_registry_symlink_is_rejected(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        write_authority_revision(root)
        registry_path = root / AUTHORITY_VOCABULARY_PATH
        detached_path = registry_path.with_name("authority-vocabulary-detached.json")
        registry_path.rename(detached_path)
        registry_path.symlink_to(detached_path.name)
        codes = finding_codes(root)
        self.assertIn("SPEC_AUTHORITY_VOCABULARY_INVALID", codes)
        self.assertIn("PATH_ESCAPE", codes)

    def test_noncanonical_authority_registry_json_is_rejected(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        write_authority_revision(root)
        registry_path = root / AUTHORITY_VOCABULARY_PATH
        document = json.loads(registry_path.read_text(encoding="utf-8"))
        noncanonical_bytes = json.dumps(document, sort_keys=True).encode("utf-8")
        registry_path.write_bytes(noncanonical_bytes)
        replace_spec000_metadata(
            root,
            "Authority vocabulary digest",
            f"sha256:{hashlib.sha256(noncanonical_bytes).hexdigest()}",
        )
        self.assertIn("SPEC_AUTHORITY_VOCABULARY_INVALID", finding_codes(root))

    def test_authority_registry_semantic_drift_is_rejected(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        write_authority_revision(root)
        registry_path = root / AUTHORITY_VOCABULARY_PATH
        document = json.loads(registry_path.read_text(encoding="utf-8"))
        document["entries"][0]["actor_classes"] = ["invented_actor"]
        mutated_bytes = canonical_json(document)
        registry_path.write_bytes(mutated_bytes)
        replace_spec000_metadata(
            root,
            "Authority vocabulary digest",
            f"sha256:{hashlib.sha256(mutated_bytes).hexdigest()}",
        )
        self.assertIn("SPEC_AUTHORITY_VOCABULARY_INVALID", finding_codes(root))

    def test_authority_fixture_semantic_drift_is_rejected(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        write_authority_revision(root)
        fixture_path = root / AUTHORITY_FIXTURE_MANIFEST_PATH
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        fixture["entries"][0]["cases"].pop()
        fixture_bytes = canonical_json(fixture)
        fixture_path.write_bytes(fixture_bytes)

        registry_path = root / AUTHORITY_VOCABULARY_PATH
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        registry["fixture_manifest"]["digest"] = (
            f"sha256:{hashlib.sha256(fixture_bytes).hexdigest()}"
        )
        registry_bytes = canonical_json(registry)
        registry_path.write_bytes(registry_bytes)
        replace_spec000_metadata(
            root,
            "Authority vocabulary digest",
            f"sha256:{hashlib.sha256(registry_bytes).hexdigest()}",
        )
        self.assertIn("SPEC_AUTHORITY_VOCABULARY_INVALID", finding_codes(root))

    def test_implemented_authority_revision_requires_conformance(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        write_authority_revision(root, status="implemented")
        self.assertIn(
            "SPEC_AUTHORITY_POLICY_CONFORMANCE_REQUIRED",
            finding_codes(root),
        )

    def test_authority_policy_and_conformance_drift_are_rejected(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        write_authority_revision(root, status="implemented", include_conformance=True)
        policy_path = root / AUTHORITY_CONSTITUTION_POLICY_PATH
        policy_path.write_text(
            policy_path.read_text(encoding="utf-8") + "\n",
            encoding="utf-8",
        )
        self.assertIn("SPEC_AUTHORITY_VOCABULARY_INVALID", finding_codes(root))

        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        write_authority_revision(root, status="implemented", include_conformance=True)
        receipt_path = root / AUTHORITY_CONFORMANCE_RECEIPT_PATH
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["case_count"] += 1
        receipt_path.write_bytes(canonical_json(receipt))
        self.assertIn("SPEC_AUTHORITY_VOCABULARY_INVALID", finding_codes(root))

    def test_authority_inputs_are_inventory_source_bound(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        binding = write_authority_revision(
            root,
            status="implemented",
            include_conformance=True,
        )
        builder = InventoryBuilder(root)
        inventory = builder.build()
        self.assertEqual(builder.findings, [])
        sources = {record["path"]: record for record in inventory["sources"]}
        expected_paths = {
            AUTHORITY_VOCABULARY_PATH,
            AUTHORITY_FIXTURE_MANIFEST_PATH,
            AUTHORITY_CONFORMANCE_RECEIPT_PATH,
            AUTHORITY_CONSTITUTION_POLICY_PATH,
            AUTHORITY_VALIDATOR_PATH,
        }
        self.assertTrue(expected_paths.issubset(sources))
        for relative in expected_paths:
            exact_bytes = (root / relative).read_bytes()
            self.assertEqual(
                sources[relative]["digest"],
                f"sha256:{hashlib.sha256(exact_bytes).hexdigest()}",
            )
        spec000 = next(
            record
            for record in inventory["artifacts"]["specifications"]["records"]
            if record["id"] == "SPEC-000"
        )
        authority_record = spec000["authority_vocabulary"]
        self.assertEqual(authority_record["digest"], binding.digest)
        self.assertEqual(
            authority_record["fixture_manifest"]["digest"],
            binding.fixture_manifest_digest,
        )
        self.assertIn("policy_conformance", authority_record)

        before = inventory["source_tree_digest"]
        receipt_path = root / AUTHORITY_CONFORMANCE_RECEIPT_PATH
        receipt_path.write_text(
            receipt_path.read_text(encoding="utf-8") + "\n",
            encoding="utf-8",
        )
        after = InventoryBuilder(root).build()["source_tree_digest"]
        self.assertNotEqual(before, after)

    def test_downstream_stage_gates_use_validated_authority_binding(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        write_authority_revision(root)
        replace_spec004_status(root, "architecture_reviewed")
        builder = InventoryBuilder(root)
        builder.build()
        self.assertEqual(builder.findings, [])

        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        write_authority_revision(root)
        replace_spec004_status(root, "implemented")
        self.assertIn(
            "SPEC_AUTHORITY_POLICY_CONFORMANCE_REQUIRED",
            finding_codes(root),
        )

        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        write_authority_revision(
            root,
            status="implemented",
            include_conformance=True,
        )
        replace_spec004_status(root, "implemented")
        builder = InventoryBuilder(root)
        builder.build()
        self.assertEqual(builder.findings, [])

    def test_terminal_specification_requires_decision_and_replacement(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        path = root / "docs/specs/SPEC-004-event-journal.md"
        text = path.read_text(encoding="utf-8").replace(
            "Status: draft", "Status: superseded", 1
        )
        path.write_text(text, encoding="utf-8")
        result = finding_codes(root)
        self.assertIn("MISSING_SPEC_LIFECYCLE_DECISION", result)
        self.assertIn("MISSING_SPEC_REPLACEMENT", result)

    def test_active_specification_cannot_claim_a_lifecycle_decision(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        path = root / "docs/specs/SPEC-004-event-journal.md"
        original = path.read_text(encoding="utf-8")
        mutated = original.replace(
            "Depends on: SPEC-000, SPEC-001, SPEC-002, SPEC-003\n",
            "Depends on: SPEC-000, SPEC-001, SPEC-002, SPEC-003\n"
            "Lifecycle decision: ADR-0006\n",
            1,
        )
        self.assertNotEqual(original, mutated)
        path.write_text(mutated, encoding="utf-8")
        self.assertIn("INVALID_SPEC_LIFECYCLE_DECISION", finding_codes(root))

    def test_terminal_specification_decision_binds_exact_revision_and_action(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        path = root / "docs/specs/SPEC-004-event-journal.md"
        original = path.read_text(encoding="utf-8")
        mutated = original.replace("Status: draft", "Status: superseded", 1).replace(
            "Depends on: SPEC-000, SPEC-001, SPEC-002, SPEC-003\n",
            "Depends on: SPEC-000, SPEC-001, SPEC-002, SPEC-003\n"
            "Lifecycle decision: ADR-0005\nReplacement: SPEC-004@2\n",
            1,
        )
        self.assertNotEqual(original, mutated)
        path.write_text(mutated, encoding="utf-8")
        self.assertIn("SPEC_LIFECYCLE_DECISION_MISMATCH", finding_codes(root))

    def test_malformed_adr_lifecycle_transition_is_rejected(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        path = root / "docs/decisions/0006-validate-public-release-boundary.md"
        original = path.read_text(encoding="utf-8")
        mutated = original.replace(
            "- Specs: SPEC-000, SPEC-002\n",
            "- Specs: SPEC-000, SPEC-002\n"
            "- Lifecycle transition: SPEC-002@1 -> superseded -> SPEC-999@9\n",
            1,
        )
        self.assertNotEqual(original, mutated)
        path.write_text(mutated, encoding="utf-8")
        self.assertIn("INVALID_ADR_LIFECYCLE_TRANSITION", finding_codes(root))

    def test_lifecycle_transition_adr_has_one_exact_spec_scope(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        path = root / "docs/decisions/0006-validate-public-release-boundary.md"
        original = path.read_text(encoding="utf-8")
        mutated = original.replace(
            "- Specs: SPEC-000, SPEC-002\n",
            "- Specs: SPEC-000, SPEC-002\n"
            "- Lifecycle transition: SPEC-002@1 -> superseded -> SPEC-002@2\n",
            1,
        )
        self.assertNotEqual(original, mutated)
        path.write_text(mutated, encoding="utf-8")
        self.assertIn(
            "INVALID_ADR_LIFECYCLE_TRANSITION_SCOPE",
            finding_codes(root),
        )

    def test_dangling_specification_dependency_is_reported(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        path = root / "docs/specs/SPEC-004-event-journal.md"
        original = path.read_text(encoding="utf-8")
        mutated = original.replace(
            "Depends on: SPEC-000, SPEC-001, SPEC-002, SPEC-003",
            "Depends on: SPEC-000, SPEC-001, SPEC-002, SPEC-999",
            1,
        )
        self.assertNotEqual(original, mutated)
        path.write_text(mutated, encoding="utf-8")
        self.assertIn("DANGLING_SPEC_DEPENDENCY", finding_codes(root))

    def test_duplicate_specification_dependency_is_reported(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        path = root / "docs/specs/SPEC-004-event-journal.md"
        original = path.read_text(encoding="utf-8")
        mutated = original.replace(
            "Depends on: SPEC-000, SPEC-001, SPEC-002, SPEC-003",
            "Depends on: SPEC-000, SPEC-001, SPEC-002, SPEC-003, SPEC-003",
            1,
        )
        self.assertNotEqual(original, mutated)
        path.write_text(mutated, encoding="utf-8")
        self.assertIn("DUPLICATE_SPEC_DEPENDENCY", finding_codes(root))

    def test_specification_dependency_cycle_is_reported(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        path = root / "docs/specs/SPEC-000-program-constitution.md"
        path.write_text(
            path.read_text(encoding="utf-8").replace("Depends on: none", "Depends on: SPEC-004", 1),
            encoding="utf-8",
        )
        codes = finding_codes(root)
        self.assertIn("SPEC_DEPENDENCY_CYCLE", codes)
        self.assertIn("INVALID_SPEC_WAVE", codes)

    def test_missing_and_duplicate_specification_index_links_are_reported(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        path = root / "docs/specs/README.md"
        text = path.read_text(encoding="utf-8")
        missing_link = "[SPEC-004](SPEC-004-event-journal.md)"
        duplicate_row = (
            "| [SPEC-005](SPEC-005-work-orders.md) | Work orders and recovery | "
            "Queue, immutable attempts, leases, retries, checkpoints, and recovery |"
        )
        text = text.replace(missing_link, "SPEC-004", 1)
        text = text.replace(duplicate_row, f"{duplicate_row}\n{duplicate_row}", 1)
        path.write_text(text, encoding="utf-8")
        codes = finding_codes(root)
        self.assertIn("MISSING_SPEC_INDEX_LINK", codes)
        self.assertIn("DUPLICATE_SPEC_INDEX_LINK", codes)

    def test_comments_and_fenced_code_cannot_satisfy_spec_index_coverage(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        path = root / "docs/specs/README.md"
        text = path.read_text(encoding="utf-8")
        row = (
            "| [SPEC-004](SPEC-004-event-journal.md) | Event journal and projections | "
            "Append-only journal plus reproducible projectors |"
        )
        text = text.replace(row, "| SPEC-004 | Event journal | Missing visible link |", 1)
        hidden_row = f"<!--\n{row}\n-->\n   ```markdown\n{row}\n   ```\n"
        text = text.replace("## Critical path", f"{hidden_row}\n## Critical path", 1)
        path.write_text(text, encoding="utf-8")
        self.assertIn("MISSING_SPEC_INDEX_LINK", finding_codes(root))

    def test_unclosed_fence_invalidates_specification_index(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        path = root / "docs/specs/README.md"
        text = path.read_text(encoding="utf-8").replace(
            "## Critical path",
            "   ```markdown\n## Critical path",
            1,
        )
        path.write_text(text, encoding="utf-8")
        self.assertIn("INVALID_SPEC_INDEX", finding_codes(root))

    def test_unindexed_specification_file_is_reported(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        source = root / "docs/specs/SPEC-026-training-rl-lab.md"
        extra = root / "docs/specs/SPEC-027-unindexed.md"
        extra.write_text(
            source.read_text(encoding="utf-8").replace("SPEC-026", "SPEC-027").replace("Wave: 6", "Wave: 6"),
            encoding="utf-8",
        )
        self.assertIn("MISSING_SPEC_INDEX_LINK", finding_codes(root))

    def test_specification_graph_must_include_every_declared_dependency(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        path = root / "docs/specs/README.md"
        text = path.read_text(encoding="utf-8")
        mutated = text.replace(
            '    S000 --> S004["SPEC-004 Event Journal and State Projections"]\n',
            "",
            1,
        )
        self.assertNotEqual(text, mutated)
        path.write_text(mutated, encoding="utf-8")
        self.assertIn("MISSING_SPEC_GRAPH_EDGE", finding_codes(root))

    def test_specification_graph_requires_one_flowchart_declaration_first(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        path = root / "docs/specs/README.md"
        text = path.read_text(encoding="utf-8").replace("flowchart TD\n", "", 1)
        path.write_text(text, encoding="utf-8")
        self.assertIn("INVALID_SPEC_GRAPH", finding_codes(root))

    def test_commented_mermaid_block_cannot_supply_missing_dependency(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        path = root / "docs/specs/README.md"
        edge = '    S000 --> S004["SPEC-004 Event Journal and State Projections"]\n'
        original = path.read_text(encoding="utf-8")
        without_edge = original.replace(edge, "", 1)
        self.assertNotEqual(original, without_edge)
        hidden = f"<!--\n```mermaid\nflowchart TD\n{edge}```\n-->\n"
        mutated = without_edge.replace(
            "The graph expresses", f"{hidden}\nThe graph expresses", 1
        )
        self.assertNotEqual(without_edge, mutated)
        path.write_text(mutated, encoding="utf-8")
        self.assertIn("MISSING_SPEC_GRAPH_EDGE", finding_codes(root))

    def test_specification_graph_rejects_undeclared_and_duplicate_edges(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        path = root / "docs/specs/README.md"
        text = path.read_text(encoding="utf-8")
        text = text.replace(
            "flowchart TD\n",
            "flowchart TD\n    S026 --> S000\n    S003 --> S004\n",
            1,
        )
        path.write_text(text, encoding="utf-8")
        codes = finding_codes(root)
        self.assertIn("EXTRA_SPEC_GRAPH_EDGE", codes)
        self.assertIn("DUPLICATE_SPEC_GRAPH_EDGE", codes)

    def test_specification_graph_labels_bind_exact_identity_and_title(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        path = root / "docs/specs/README.md"
        original = path.read_text(encoding="utf-8")
        mutated = original.replace(
            'S000 --> S004["SPEC-004 Event Journal and State Projections"]',
            'S000 --> S004["SPEC-999 Wrong contract"]',
            1,
        )
        self.assertNotEqual(original, mutated)
        path.write_text(mutated, encoding="utf-8")
        self.assertIn("SPEC_GRAPH_LABEL_MISMATCH", finding_codes(root))

    def test_specification_graph_rejects_standalone_label_override(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        path = root / "docs/specs/README.md"
        text = path.read_text(encoding="utf-8").replace(
            "flowchart TD\n",
            'flowchart TD\n    S004["SPEC-999 Wrong contract"]\n',
            1,
        )
        path.write_text(text, encoding="utf-8")
        self.assertIn("INVALID_SPEC_GRAPH_LINE", finding_codes(root))

    def test_duplicate_mechanism_has_stable_reason_code(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        path = root / "researcher/mechanisms/registry.jsonl"
        first = path.read_text(encoding="utf-8").splitlines()[0]
        path.write_text(path.read_text(encoding="utf-8") + first + "\n", encoding="utf-8")
        self.assertIn("DUPLICATE_MECHANISM_ID", finding_codes(root))

    def test_duplicate_claim_has_stable_reason_code(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        path = root / "researcher/claims/index.jsonl"
        first = path.read_text(encoding="utf-8").splitlines()[0]
        path.write_text(path.read_text(encoding="utf-8") + first + "\n", encoding="utf-8")
        self.assertIn("DUPLICATE_CLAIM_ID", finding_codes(root))

    def test_duplicate_activation_case_has_stable_reason_code(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        path = root / "researcher/fixtures/activation-cases.jsonl"
        first = path.read_text(encoding="utf-8").splitlines()[0]
        path.write_text(path.read_text(encoding="utf-8") + first + "\n", encoding="utf-8")
        self.assertIn("DUPLICATE_ACTIVATION_CASE_ID", finding_codes(root))

    def test_duplicate_router_prompt_has_stable_reason_code(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        path = root / "researcher/benchmarks/router/prompts.jsonl"
        first = path.read_text(encoding="utf-8").splitlines()[0]
        path.write_text(path.read_text(encoding="utf-8") + first + "\n", encoding="utf-8")
        self.assertIn("DUPLICATE_ROUTER_PROMPT_ID", finding_codes(root))

    def test_duplicate_scenario_has_stable_reason_code(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        path = root / "researcher/benchmarks/scenarios/adversarial.jsonl"
        first = path.read_text(encoding="utf-8").splitlines()[0]
        path.write_text(path.read_text(encoding="utf-8") + first + "\n", encoding="utf-8")
        self.assertIn("DUPLICATE_SCENARIO_ID", finding_codes(root))

    def test_dangling_corpus_mechanism_is_reported(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        path = root / "researcher/corpus/index.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        value["skills"][0]["mechanism_ids"].append("missing-mechanism")
        path.write_text(json.dumps(value), encoding="utf-8")
        self.assertIn("DANGLING_MECHANISM", finding_codes(root))

    def test_missing_accepted_ledger_event_is_reported(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        path = root / "researcher/mechanisms/ledgers/accepted.jsonl"
        retained = [
            line
            for line in path.read_text(encoding="utf-8").splitlines()
            if '"anchored-iterative-summary"' not in line
        ]
        path.write_text("\n".join(retained) + "\n", encoding="utf-8")
        codes = finding_codes(root)
        self.assertIn("MISSING_ACCEPTED_LEDGER_EVENT", codes)
        self.assertIn("DANGLING_LEDGER_SOURCE", codes)

    def test_orphan_accepted_event_is_reported(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        path = root / "researcher/mechanisms/ledgers/accepted.jsonl"
        event = {
            "mechanism_id": "not-in-registry",
            "status": "accepted",
            "source": "researcher/mechanisms/registry.jsonl",
            "rationale": "fixture",
        }
        path.write_text(path.read_text(encoding="utf-8") + json.dumps(event) + "\n", encoding="utf-8")
        self.assertIn("ORPHAN_ACCEPTED_LEDGER_EVENT", finding_codes(root))

    def test_missing_golden_is_reported(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        path = root / "researcher/benchmarks/goldens/adversarial-goldens.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        del value[next(iter(value))]
        path.write_text(json.dumps(value), encoding="utf-8")
        self.assertIn("MISSING_GOLDEN", finding_codes(root))

    def test_non_executable_verifier_is_reported(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        verify = root / "researcher/benchmarks/effectiveness/tasks/001-filesystem-context-offload/verify.sh"
        verify.chmod(0o644)
        self.assertIn("INVALID_EFFECTIVENESS_TASK", finding_codes(root))

    def test_manifest_skill_mismatch_is_reported(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        path = root / ".claude-plugin/marketplace.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        value["plugins"][0]["skills"].pop()
        path.write_text(json.dumps(value), encoding="utf-8")
        self.assertIn("MANIFEST_SKILL_MISMATCH", finding_codes(root))

    def test_plugin_version_mismatch_is_reported(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        path = root / ".plugin/plugin.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        value["version"] = "999.0.0"
        path.write_text(json.dumps(value), encoding="utf-8")
        self.assertIn("PLUGIN_VERSION_MISMATCH", finding_codes(root))

    def test_duplicate_json_key_is_rejected(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        path = root / ".plugin/plugin.json"
        path.write_text('{"name":"a","name":"b"}', encoding="utf-8")
        self.assertIn("PARSE_ERROR", finding_codes(root))

    @unittest.skipIf(not hasattr(os, "symlink"), "symlink support required")
    def test_symlinked_canonical_input_is_rejected(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        target = root / "skills/context-fundamentals/SKILL.md"
        outside = Path(temporary.name) / "outside.md"
        outside.write_text(target.read_text(encoding="utf-8"), encoding="utf-8")
        target.unlink()
        target.symlink_to(outside)
        self.assertIn("PATH_ESCAPE", finding_codes(root))

    def test_atomic_failure_preserves_prior_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "inventory.json"
            target.write_text("prior", encoding="utf-8")
            with mock.patch("researcher.scripts.build_inventory.os.replace", side_effect=OSError("fixture")):
                with self.assertRaises(OSError):
                    atomic_write_text(target, "new")
            self.assertEqual(target.read_text(encoding="utf-8"), "prior")
            self.assertEqual(list(Path(temporary).glob("*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
