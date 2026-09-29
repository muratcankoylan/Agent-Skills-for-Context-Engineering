"""Non-authoritative specification coverage, drift and input-boundary fixtures."""

from __future__ import annotations

import contextlib
import copy
import hashlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from researcher.scripts import spec_program as program


ROOT = Path(__file__).resolve().parents[3]


def spec_text(
    spec_id="SPEC-000", dependencies="none", *, status="draft", criteria=None
):
    return (
        f"# {spec_id}: Fixture\n\nStatus: {status}\nRevision: 1\nRevises: none\n"
        "Wave: 0\nClassification: public\nOwners: fixture\n"
        f"Depends on: {dependencies}\n\n## Decision\n\nA bounded fixture.\n\n"
        "## Acceptance criteria\n\n"
        + (
            criteria
            if criteria is not None
            else "- [x] Preserve exact bytes.\n- [ ] Reject forged authority.\n"
        )
    )


def filled_plan(root):
    value = program.build_program(root)
    value["schema"] = "spec-execution-plan/v1"
    for item in value["specs"]:
        item.update(
            objective="Propose the bounded contract.",
            code_paths=[],
            slices=[
                {
                    "id": "offline-contract",
                    "deliverable": "A deterministic offline adapter.",
                    "verification": "Golden replay and adversarial rejection cases.",
                    "rollback": "Disable the adapter, retain original evidence.",
                }
            ],
        )
        for criterion in item["criteria"]:
            criterion["verification_method"] = (
                "An isolated known-answer and counterexample fixture."
            )
    return value


class SpecProgramTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        (self.root / "docs/specs").mkdir(parents=True)
        self.write("SPEC-000")

    def write(self, spec_id, dependencies="none", **kwargs):
        path = self.root / f"docs/specs/{spec_id}-fixture.md"
        path.write_text(spec_text(spec_id, dependencies, **kwargs), encoding="utf-8")
        return path

    def assert_program_error(self, code):
        with self.assertRaises(program.ProgramError) as raised:
            program.build_program(self.root)
        self.assertEqual(raised.exception.code, code)

    def codes(self, value):
        return {finding["code"] for finding in program.validate_plan(value, self.root)}

    def test_actual_program_contains_all_specs_and_unassessed_criteria(self):
        value = program.build_program(ROOT)
        self.assertEqual(
            {item["id"] for item in value["specs"]},
            {f"SPEC-{i:03d}" for i in range(27)},
        )
        self.assertGreater(sum(len(item["criteria"]) for item in value["specs"]), 200)
        self.assertEqual(value["authority"], "none")
        self.assertIs(value["production_ready"], False)
        for item in value["specs"]:
            self.assertIn(
                {"code": "default_branch_authority_unverified", "dependency": None},
                item["blockers"],
            )
            self.assertTrue(
                all(row["state"] == "unassessed" for row in item["criteria"])
            )

    def test_repository_execution_plan_matches_current_contracts(self):
        plan = json.loads(
            (ROOT / "docs/product/spec-execution-plan.json").read_text(encoding="utf-8")
        )
        self.assertEqual(program.validate_plan(plan, ROOT), [])

    def test_deterministic_order_and_exact_byte_and_text_digests(self):
        self.write("SPEC-002", "SPEC-000")
        self.write("SPEC-001", "SPEC-000")
        value = program.build_program(self.root)
        self.assertEqual(value, program.build_program(self.root))
        self.assertEqual(
            value["topological_order"], ["SPEC-000", "SPEC-001", "SPEC-002"]
        )
        item = value["specs"][0]
        source = (self.root / item["path"]).read_bytes()
        self.assertEqual(
            item["source_digest"], "sha256:" + hashlib.sha256(source).hexdigest()
        )
        criterion = item["criteria"][0]
        digest = hashlib.sha256(criterion["text"].encode()).hexdigest()
        self.assertEqual(criterion["id"], "SPEC-000:ac:" + digest)
        self.assertEqual(criterion["text_digest"], "sha256:" + digest)
        self.assertIs(criterion["source_checked"], True)
        self.assertEqual(criterion["state"], "unassessed")

    def test_comments_and_fences_are_not_criteria_and_continuations_bind(self):
        self.write(
            "SPEC-000",
            criteria=(
                "<!-- - [x] Hidden assertion. -->\n"
                "```md\n- [x] A fenced example.\n```\n"
                "- [ ] Visible condition\n  with a second line.\n\n"
                "Narrative after the checklist is not an extra criterion.\n"
            ),
        )
        rows = program.build_program(self.root)["specs"][0]["criteria"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["text"], "Visible condition\nwith a second line.")

    def test_checked_and_unchecked_boxes_never_establish_authority(self):
        self.write("SPEC-000", status="operational")
        value = program.build_program(self.root)
        self.assertIs(value["production_ready"], False)
        self.assertEqual(
            value["specs"][0]["blockers"],
            [{"code": "default_branch_authority_unverified", "dependency": None}],
        )
        self.assertTrue(
            all(row["state"] == "unassessed" for row in value["specs"][0]["criteria"])
        )

    def test_comment_literal_code_span_ambiguity_is_rejected(self):
        for criteria in (
            "- [ ] Reject literal `<!-- unsafe -->` at the boundary.\n",
            "- [ ] Reject literal `<!--` at the boundary.\n",
            "- [ ] Reject literal ``<!-- unsafe -->`` at the boundary.\n",
            "- [ ] Reject literal `\n<!-- unsafe -->\n` at the boundary.\n",
            "- [ ] Reject literal `<!--\nunsafe -->` at the boundary.\n",
        ):
            with self.subTest(criteria=criteria):
                self.write("SPEC-000", criteria=criteria)
                self.assert_program_error("INVALID_ACCEPTANCE_MARKDOWN")

    def test_ordinary_comments_and_fenced_literal_examples_remain_noncriteria(self):
        self.write(
            "SPEC-000",
            criteria=(
                "<!-- - [x] An ordinary hidden checklist item. -->\n\n"
                "```markdown\n- [x] Fenced `<!-- unsafe -->` example.\n```\n\n"
                "- [ ] Preserve visible <!-- hidden comment --> text.\n"
            ),
        )
        rows = program.build_program(self.root)["specs"][0]["criteria"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["text"], "Preserve visible  text.")

    def test_lazy_wrapped_requirement_text_is_not_dropped(self):
        self.write(
            "SPEC-000",
            criteria="- [ ] First line\nrequires the next line.\n\n  A second paragraph.\n",
        )
        text = program.build_program(self.root)["specs"][0]["criteria"][0]["text"]
        self.assertEqual(
            text, "First line\nrequires the next line.\n\nA second paragraph."
        )

    def test_terminal_and_draft_dependency_blockers(self):
        self.write("SPEC-000", status="amended")
        self.write("SPEC-001", "SPEC-000")
        self.write("SPEC-002", "SPEC-001")
        specs = {row["id"]: row for row in program.build_program(self.root)["specs"]}
        self.assertIn(
            {"code": "terminal_revision_not_active", "dependency": None},
            specs["SPEC-000"]["blockers"],
        )
        self.assertIn(
            {"code": "dependency_terminal_revision", "dependency": "SPEC-000"},
            specs["SPEC-001"]["blockers"],
        )
        self.assertIn(
            {"code": "dependency_not_accepted", "dependency": "SPEC-001"},
            specs["SPEC-002"]["blockers"],
        )

    def test_dependency_bindings_are_observed_and_drift_is_a_blocker(self):
        path = self.write("SPEC-001", "SPEC-000")
        path.write_text(
            path.read_text().replace(
                "Depends on: SPEC-000\n",
                "Depends on: SPEC-000\nDependency revisions: SPEC-000@2\n",
            )
        )
        row = program.build_program(self.root)["specs"][1]
        self.assertEqual(row["dependency_revisions"], {"SPEC-000": 2})
        self.assertIn(
            {"code": "dependency_revision_mismatch", "dependency": "SPEC-000"},
            row["blockers"],
        )

    def test_no_specs_and_no_criteria_fail(self):
        path = self.root / "docs/specs/SPEC-000-fixture.md"
        path.unlink()
        self.assert_program_error("INVALID_SPEC_COUNT")
        self.write("SPEC-000", criteria="```md\n- [x] Not a real criterion.\n```\n")
        self.assert_program_error("NO_ACCEPTANCE_CRITERIA")

    def test_malformed_markdown_does_not_silently_drop_criteria(self):
        for criteria in (
            "- [ ] Good.\n```\n",
            "- [ ] Good.\n<!-- unfinished",
            "- [?] Unknown marker.\n",
            "<div>\n- [ ] Hidden by HTML.\n</div>\n",
            "- [ ] One.\n\n## Acceptance criteria\n\n- [ ] Two.\n",
        ):
            with self.subTest(criteria=criteria):
                self.write("SPEC-000", criteria=criteria)
                self.assert_program_error("INVALID_ACCEPTANCE_MARKDOWN")

    def test_duplicate_criterion_text_fails(self):
        self.write(
            "SPEC-000", criteria="- [ ] Same criterion.\n- [x] Same criterion.\n"
        )
        self.assert_program_error("DUPLICATE_CRITERION")

    def test_duplicate_or_mismatched_spec_identity_fails(self):
        other = self.root / "docs/specs/SPEC-000-second.md"
        other.write_text(spec_text())
        self.assert_program_error("INVALID_SPEC_IDENTITY")
        other.unlink()
        (self.root / "docs/specs/SPEC-001-wrong.md").write_text(spec_text())
        self.assert_program_error("INVALID_SPEC_IDENTITY")

    def test_cycle_missing_and_duplicate_dependencies_fail(self):
        self.write("SPEC-000", "SPEC-001")
        self.assert_program_error("MISSING_DEPENDENCY")
        self.write("SPEC-001", "SPEC-000")
        self.assert_program_error("DEPENDENCY_CYCLE")
        self.write("SPEC-000", "SPEC-001, SPEC-001")
        self.assert_program_error("INVALID_DEPENDENCIES")

    def test_malformed_headers_and_filenames_fail(self):
        path = self.write("SPEC-000")
        original = path.read_bytes()
        for body in (
            original.replace(b"Revision: 1", b"Revision: 01"),
            original.replace(b"Status: draft", b"Status: draft\nStatus: accepted"),
            original + b"\xff",
        ):
            with self.subTest(body=body):
                path.write_bytes(body)
                with self.assertRaises(program.ProgramError):
                    program.build_program(self.root)
        path.write_bytes(original)
        (self.root / "docs/specs/SPEC-invalid.md").write_text("Invalid.")
        self.assert_program_error("INVALID_SPEC_PATH")

    def test_source_count_size_and_unicode_bounds(self):
        with patch.object(program, "MAX_SPECS", 0):
            self.assert_program_error("INVALID_SPEC_COUNT")
        with patch.object(program, "MAX_DIRECTORY_ENTRIES", 0):
            self.assert_program_error("TOO_MANY_FILES")
        with patch.object(program, "MAX_SPEC_BYTES", 10):
            self.assert_program_error("INPUT_TOO_LARGE")
        with patch.object(program, "MAX_SOURCE_BYTES", 10):
            self.assert_program_error("INPUT_TOO_LARGE")
        with patch.object(program, "MAX_CRITERIA", 1):
            self.assert_program_error("TOO_MANY_CRITERIA")
        with patch.object(program, "MAX_TOTAL_CRITERIA", 1):
            self.assert_program_error("TOO_MANY_CRITERIA")
        self.write("SPEC-000", criteria="- [ ] " + "界" * 3000 + "\n")
        self.assert_program_error("INVALID_ACCEPTANCE_MARKDOWN")

    def test_huge_revision_and_dependency_binding_are_typed_errors(self):
        path = self.write("SPEC-000")
        path.write_text(
            path.read_text().replace("Revision: 1", "Revision: 9007199254740992")
        )
        self.assert_program_error("INVALID_SPEC_IDENTITY")
        self.write("SPEC-000")
        path = self.write("SPEC-001", "SPEC-000")
        path.write_text(
            path.read_text().replace(
                "Depends on: SPEC-000\n",
                "Depends on: SPEC-000\nDependency revisions: SPEC-000@"
                + "9" * 5000
                + "\n",
            )
        )
        self.assert_program_error("INVALID_DEPENDENCIES")

    def test_file_replaced_by_fifo_at_open_is_rejected_without_blocking(self):
        original_open = os.open
        path = self.root / "docs/specs/SPEC-000-fixture.md"

        def swapped_open(target, flags, *args, **kwargs):
            self.assertTrue(flags & os.O_NONBLOCK)
            path.unlink()
            os.mkfifo(path)
            return original_open(target, flags, *args, **kwargs)

        with patch.object(program.os, "open", side_effect=swapped_open):
            self.assert_program_error("SOURCE_CHANGED")

    def test_symlink_and_hardlink_spec_files_fail(self):
        path = self.write("SPEC-000")
        saved = self.root / "original.md"
        path.rename(saved)
        path.symlink_to(saved)
        self.assert_program_error("UNSAFE_PATH")
        path.unlink()
        os.link(saved, path)
        self.assert_program_error("UNSAFE_PATH")

    def test_directory_alias_and_missing_root_do_not_repair(self):
        directory = self.root / "docs/specs"
        directory.rename(self.root / "saved-specs")
        directory.symlink_to(self.root / "saved-specs", target_is_directory=True)
        self.assert_program_error("UNSAFE_PATH")
        missing = self.root / "absent"
        with self.assertRaises(program.ProgramError):
            program.build_program(missing)
        self.assertFalse(missing.exists())

    def test_plan_accepts_complete_unassessed_coverage_and_empty_touchpoints(self):
        self.assertEqual(program.validate_plan(filled_plan(self.root), self.root), [])

    def test_plan_drift_checked_box_revision_bool_and_authority_are_rejected(self):
        original = filled_plan(self.root)
        changes = [
            (lambda p: p.update(authority="accepted"), "PLAN_SOURCE_DRIFT"),
            (lambda p: p.update(production_ready=0), "PLAN_SOURCE_DRIFT"),
            (lambda p: p["specs"][0].update(revision=True), "PLAN_SOURCE_DRIFT"),
            (lambda p: p["specs"][0].update(status="accepted"), "PLAN_SOURCE_DRIFT"),
            (
                lambda p: p["specs"][0].update(source_digest="sha256:" + "0" * 64),
                "PLAN_SOURCE_DRIFT",
            ),
            (
                lambda p: p["specs"][0]["criteria"][0].update(source_checked=1),
                "PLAN_CRITERION_DRIFT",
            ),
            (
                lambda p: p["specs"][0]["criteria"][0].update(state="passed"),
                "PLAN_CRITERION_DRIFT",
            ),
        ]
        for change, code in changes:
            with self.subTest(code=code, change=change):
                value = copy.deepcopy(original)
                change(value)
                self.assertIn(code, self.codes(value))

    def test_plan_omitted_extra_duplicate_specs_and_criteria(self):
        original = filled_plan(self.root)
        for target in ("specs", "criteria"):
            for action in ("omit", "extra", "duplicate", "unknown"):
                with self.subTest(target=target, action=action):
                    value = copy.deepcopy(original)
                    rows = (
                        value["specs"]
                        if target == "specs"
                        else value["specs"][0]["criteria"]
                    )
                    if action == "omit":
                        rows.pop()
                    elif action in {"extra", "duplicate"}:
                        rows.append(copy.deepcopy(rows[0]))
                    else:
                        rows[0]["id"] = "unknown"
                    self.assertIn("PLAN_COVERAGE_INVALID", self.codes(value))

    def test_plan_rejects_arbitrary_evidence_and_extra_keys_at_every_level(self):
        original = filled_plan(self.root)
        for location in ("root", "spec", "criterion", "slice"):
            value = copy.deepcopy(original)
            target = {
                "root": value,
                "spec": value["specs"][0],
                "criterion": value["specs"][0]["criteria"][0],
                "slice": value["specs"][0]["slices"][0],
            }[location]
            target["evidence_passed"] = True
            self.assertIn("PLAN_KEYS_INVALID", self.codes(value))

    def test_plan_requires_nonblank_bounded_delivery_verification_and_rollback(self):
        original = filled_plan(self.root)
        for key in ("deliverable", "verification", "rollback"):
            value = copy.deepcopy(original)
            value["specs"][0]["slices"][0][key] = " \n"
            self.assertIn("PLAN_TEXT_INVALID", self.codes(value))
        value = copy.deepcopy(original)
        value["specs"][0]["objective"] = "界" * 3000
        self.assertIn("PLAN_TEXT_INVALID", self.codes(value))
        value = copy.deepcopy(original)
        value["specs"][0]["criteria"][0]["verification_method"] = ""
        self.assertIn("PLAN_TEXT_INVALID", self.codes(value))

    def test_plan_slice_ids_count_and_ordering(self):
        value = filled_plan(self.root)
        value["specs"][0]["slices"] *= 2
        self.assertIn("PLAN_SLICES_INVALID", self.codes(value))
        value = filled_plan(self.root)
        value["specs"][0]["slices"] = []
        self.assertIn("PLAN_SLICES_INVALID", self.codes(value))
        self.write("SPEC-001", "SPEC-000")
        value = filled_plan(self.root)
        value["topological_order"].reverse()
        self.assertIn("PLAN_SOURCE_DRIFT", self.codes(value))

    def test_plan_code_paths_are_existing_regular_confined_files(self):
        source = self.root / "safe.py"
        source.write_text("pass\n")
        alias = self.root / "alias.py"
        alias.symlink_to(source)
        value = filled_plan(self.root)
        value["specs"][0]["code_paths"] = ["safe.py"]
        self.assertEqual(self.codes(value), set())
        for path in (
            "../safe.py",
            str(source),
            "alias.py",
            "missing.py",
            "docs/specs",
            "docs//specs/SPEC-000-fixture.md",
            "./safe.py",
            "docs/../safe.py",
            "bad\\path",
        ):
            with self.subTest(path=path):
                value["specs"][0]["code_paths"] = [path]
                self.assertIn("PLAN_PATHS_INVALID", self.codes(value))

    def test_plan_source_edit_and_criterion_edit_invalidate_old_plan(self):
        value = filled_plan(self.root)
        self.write("SPEC-000", criteria="- [ ] A different requirement.\n")
        codes = self.codes(value)
        self.assertIn("PLAN_SOURCE_DRIFT", codes)
        self.assertIn("PLAN_COVERAGE_INVALID", codes)

    def test_plan_structure_and_size_bounds(self):
        value = filled_plan(self.root)
        value["unexpected"] = 1.5
        self.assertIn("INVALID_PLAN_JSON", self.codes(value))
        value["unexpected"] = "\ud800"
        self.assertIn("INVALID_PLAN_JSON", self.codes(value))
        value["unexpected"] = value
        self.assertIn("PLAN_TOO_LARGE", self.codes(value))
        with patch.object(program, "MAX_PLAN_BYTES", 10):
            self.assertIn("PLAN_TOO_LARGE", self.codes(filled_plan(self.root)))

    def test_cli_template_is_json_but_explicitly_unfilled_and_invalid(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = program.main(["plan", "--root", str(self.root)])
        self.assertEqual(result, 0)
        value = json.loads(output.getvalue())
        self.assertEqual(value["specs"][0]["objective"], "")
        self.assertIn("PLAN_TEXT_INVALID", self.codes(value))

    def test_cli_rejects_duplicate_keys_unsafe_numbers_and_argument_errors(self):
        path = self.root / "plan.json"
        for body in (
            '{"schema":"a","schema":"b"}',
            '{"value":NaN}',
            '{"value":1.0}',
            '{"value":9007199254740992}',
        ):
            path.write_text(body)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = program.main(["check", "plan.json", "--root", str(self.root)])
            self.assertEqual(result, 1)
            self.assertEqual(
                json.loads(output.getvalue())["findings"][0]["code"],
                "INVALID_PLAN_JSON",
            )
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = program.main(["unknown"])
        self.assertEqual(result, 1)
        self.assertEqual(
            json.loads(output.getvalue())["findings"][0]["code"], "INVALID_ARGUMENTS"
        )

    def test_cli_and_api_read_only_bytes_modes_mtimes_and_no_subprocess(self):
        value = filled_plan(self.root)
        path = self.root / "plan.json"
        path.write_text(json.dumps(value))

        def snapshot():
            return {
                p.relative_to(self.root).as_posix(): (
                    p.read_bytes(),
                    p.stat().st_mode,
                    p.stat().st_mtime_ns,
                )
                for p in self.root.rglob("*")
                if p.is_file()
            }

        before = snapshot()
        output = io.StringIO()
        with (
            patch("subprocess.run", side_effect=AssertionError("no execution")),
            contextlib.redirect_stdout(output),
        ):
            self.assertEqual(
                program.main(["check", "plan.json", "--root", str(self.root)]), 0
            )
            self.assertEqual(program.validate_plan(value, self.root), [])
        self.assertEqual(json.loads(output.getvalue())["findings"], [])
        self.assertEqual(snapshot(), before)


if __name__ == "__main__":
    unittest.main()
