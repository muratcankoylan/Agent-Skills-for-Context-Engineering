"""Determinism and reconciliation tests for the generated corpus inventory."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from researcher.scripts.build_inventory import (
    InventoryBuilder,
    atomic_write_text,
    pretty_json,
    render_summary,
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
        "researcher/benchmarks/sdk-runner/package.json",
        "researcher/benchmarks/sdk-runner/package-lock.json",
        "researcher/benchmarks/sdk-runner/tsconfig.json",
        "researcher/benchmarks/sdk-runner/src/common.ts",
        "researcher/benchmarks/sdk-runner/src/runRouter.ts",
        "researcher/benchmarks/sdk-runner/src/runEffectiveness.ts",
        "researcher/scripts/validate_governance.py",
        "researcher/scripts/build_inventory.py",
        "researcher/scripts/validate_export.py",
        "researcher/scripts/export_policy.py",
        "researcher/scripts/validate_public_repo.py",
        "researcher/scripts/tests/test_public_repo.py",
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

    source_tasks = source / "researcher" / "benchmarks" / "effectiveness" / "tasks"
    target_tasks = target / "researcher" / "benchmarks" / "effectiveness" / "tasks"
    shutil.copytree(source_tasks, target_tasks)


def finding_codes(root: Path) -> set[str]:
    builder = InventoryBuilder(root)
    builder.build()
    return {finding.code for finding in builder.findings}


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
        self.assertEqual(decisions["count"], 6)
        self.assertEqual(
            {record["id"] for record in decisions["records"]},
            {f"ADR-{number:04d}" for number in range(1, 7)},
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

    def test_dangling_specification_dependency_is_reported(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        path = root / "docs/specs/SPEC-004-event-journal.md"
        path.write_text(
            path.read_text(encoding="utf-8").replace("Depends on: SPEC-003", "Depends on: SPEC-999", 1),
            encoding="utf-8",
        )
        self.assertIn("DANGLING_SPEC_DEPENDENCY", finding_codes(root))

    def test_duplicate_specification_dependency_is_reported(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        path = root / "docs/specs/SPEC-004-event-journal.md"
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "Depends on: SPEC-003",
                "Depends on: SPEC-003, SPEC-003",
                1,
            ),
            encoding="utf-8",
        )
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
        text = text.replace(
            '    S003 --> S004["SPEC-004 Event Journal and State Projections"]\n',
            "",
            1,
        )
        path.write_text(text, encoding="utf-8")
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
        edge = '    S003 --> S004["SPEC-004 Event Journal and State Projections"]\n'
        text = path.read_text(encoding="utf-8").replace(edge, "", 1)
        hidden = f"<!--\n```mermaid\nflowchart TD\n{edge}```\n-->\n"
        text = text.replace("The graph expresses", f"{hidden}\nThe graph expresses", 1)
        path.write_text(text, encoding="utf-8")
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
        text = path.read_text(encoding="utf-8").replace(
            'S003 --> S004["SPEC-004 Event Journal and State Projections"]',
            'S003 --> S004["SPEC-999 Wrong contract"]',
            1,
        )
        path.write_text(text, encoding="utf-8")
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
