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
        "SKILL.md",
        "README.md",
        "AGENTS.md",
        "CLAUDE.md",
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
