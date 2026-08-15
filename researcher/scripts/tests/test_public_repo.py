"""Tests for the deterministic public repository release boundary."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from researcher.scripts.validate_public_repo import validate_public_tree


class PublicRepositoryValidationTests(unittest.TestCase):
    def fixture(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name).resolve()
        self.addCleanup(temporary.cleanup)
        return temporary, root

    @staticmethod
    def write(root: Path, relative: str, body: str | bytes) -> None:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(body, bytes):
            path.write_bytes(body)
        else:
            path.write_text(body, encoding="utf-8")

    def test_clean_public_text_and_binary_pass(self) -> None:
        _, root = self.fixture()
        self.write(root, "README.md", "Use an environment variable, never a secret value.\n")
        self.write(root, "asset.bin", b"\x00\xff/private/path")
        self.assertEqual(validate_public_tree(root, ["README.md", "asset.bin"]), [])

    def test_developer_local_path_families_fail_without_echoing_values(self) -> None:
        _, root = self.fixture()
        private_paths = [
            "/" + "Users" + "/alice/project",
            "/" + "home" + "/alice/project",
            "/" + "USERS" + "/alice/project",
            "/" + "HOME" + "/alice/project",
            "/" + "mnt" + "/c/Users/alice/project",
            "/" + "private" + "/" + "var" + "/folders/example/file",
            "/" + "PRIVATE" + "/" + "var" + "/folders/example/file",
            "/" + "var" + "/folders/example/file",
            "C:" + "\\" + "Users" + "\\alice\\project\\",
            "\\" + "\\" + "Users" + "\\alice\\project\\",
        ]
        for index, private_path in enumerate(private_paths):
            relative = f"fixture-{index}.txt"
            self.write(root, relative, f"RUN tool {private_path}\n")
            findings = validate_public_tree(root, [relative])
            self.assertEqual([finding.code for finding in findings], ["PRIVATE_LOCAL_PATH"])
            self.assertNotIn(private_path, findings[0].message)

    def test_forbidden_credential_filenames_fail(self) -> None:
        _, root = self.fixture()
        self.write(root, ".env.production", "EXAMPLE=true\n")
        self.write(root, "service-account.json", "{}\n")
        findings = validate_public_tree(root, [".env.production", "service-account.json"])
        self.assertEqual([finding.code for finding in findings], [
            "FORBIDDEN_CREDENTIAL_FILE",
            "FORBIDDEN_CREDENTIAL_FILE",
        ])

    def test_documented_environment_examples_are_allowed(self) -> None:
        _, root = self.fixture()
        self.write(root, ".env.example", "API_KEY=replace-me\n")
        self.assertEqual(validate_public_tree(root, [".env.example"]), [])

    def test_ignored_private_and_runtime_paths_cannot_be_forced_into_git(self) -> None:
        _, root = self.fixture()
        forbidden_paths = [
            ".cursor/private-settings.json",
            ".specstory/session.md",
            "Private/notes.md",
            "outputs/spec.md",
            "researcher/artifacts/private/blob",
            "researcher/benchmarks/router/results/run.json",
            "researcher/exports/private/plan.json",
            "researcher/exports/staging/manifest.json",
            "researcher/queue/inbox.jsonl",
            "researcher/reports/logs/loop.log",
            "researcher/reports/status.md",
            "researcher/runs/active-run/run-state.json",
            "researcher/runs/readme.md",
            "researcher/runs/20260515-035228-EXECUTABLE-autonomous-research-frameworks/private.json",
            "researcher/schemas/reports/runtime/report.json",
            "private/case-collision.md",
            "Outputs/case-collision.md",
        ]
        for relative in forbidden_paths:
            self.write(root, relative, "private runtime state\n")
        findings = validate_public_tree(root, forbidden_paths)
        self.assertEqual(
            [finding.code for finding in findings],
            ["FORBIDDEN_PRIVATE_PATH"] * len(forbidden_paths),
        )

    def test_documented_run_surfaces_remain_public(self) -> None:
        _, root = self.fixture()
        paths = [
            "researcher/runs/README.md",
            "researcher/runs/20260515-035228-executable-autonomous-research-frameworks/run-state.json",
        ]
        for relative in paths:
            self.write(root, relative, "public fixture\n")
        self.assertEqual(validate_public_tree(root, paths), [])

    def test_private_key_header_fails(self) -> None:
        _, root = self.fixture()
        markers = [
            "-----BEGIN " + "PRIVATE KEY-----",
            "-----BEGIN " + "ENCRYPTED PRIVATE KEY-----",
            "-----BEGIN " + "PGP PRIVATE KEY BLOCK-----",
        ]
        for index, marker in enumerate(markers):
            relative = f"key-fixture-{index}.txt"
            self.write(root, relative, marker + "\n")
            findings = validate_public_tree(root, [relative])
            self.assertEqual([finding.code for finding in findings], ["PRIVATE_KEY_MATERIAL"])

    def test_text_like_files_must_be_utf8_without_nul(self) -> None:
        _, root = self.fixture()
        self.write(root, "invalid.md", b"\xffnot utf8")
        self.write(root, "controls.json", b'{"key":"value"}\0\1')
        findings = validate_public_tree(root, ["controls.json", "invalid.md"])
        self.assertEqual(
            [finding.code for finding in findings],
            ["NON_UTF8_TEXT_FILE", "NON_UTF8_TEXT_FILE"],
        )

    def test_path_escape_and_duplicate_inputs_fail_closed(self) -> None:
        _, root = self.fixture()
        self.write(root, "safe.txt", "safe\n")
        codes = [
            finding.code
            for finding in validate_public_tree(root, ["safe.txt", "safe.txt", "../outside"])
        ]
        self.assertIn("DUPLICATE_TRACKED_PATH", codes)
        self.assertIn("TRACKED_PATH_ESCAPE", codes)


if __name__ == "__main__":
    unittest.main()
