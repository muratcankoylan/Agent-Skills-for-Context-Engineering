"""Installer effects are confined to disposable fixture trees, never user data."""
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[3]
INSTALLER = ROOT / "examples/digital-brain-skill/scripts/install.sh"


class InstallSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="install-safety-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.brain = self.root / "source" / "digital-brain"
        (self.brain / "scripts").mkdir(parents=True)
        shutil.copyfile(INSTALLER, self.brain / "scripts/install.sh")
        (self.brain / "SKILL.md").write_text("# Fixture skill\n", encoding="utf-8")
        (self.brain / "notes").mkdir()
        (self.brain / "notes/my note.md").write_text("preserve literal bytes\n", encoding="utf-8")
        (self.brain / ".example").write_text("included\n", encoding="utf-8")
        self.home = self.root / "home"
        self.project = self.root / "project"
        self.home.mkdir()
        self.project.mkdir()

    def run_install(self, choice="3", parent=None, *, home=None, project=None, extra="", path=None):
        answers = choice + "\n"
        if choice == "3":
            answers += str(parent) + "\n"
        environment = {
            "PATH": os.pathsep.join((str(Path(sys.executable).parent), os.defpath)),
            "HOME": str(home or self.home), "LC_ALL": "C", "PYTHONDONTWRITEBYTECODE": "1",
        }
        if path is not None:
            environment["PATH"] = str(path)
        return subprocess.run(["/bin/bash", str(self.brain / "scripts/install.sh")],
                              input=answers + extra, text=True, capture_output=True,
                              cwd=project or self.project, env=environment, timeout=15)

    def assert_installed(self, parent):
        target = parent / "digital-brain"
        self.assertEqual((target / "SKILL.md").read_bytes(), (self.brain / "SKILL.md").read_bytes())
        self.assertEqual((target / "notes/my note.md").read_text(), "preserve literal bytes\n")
        self.assertEqual((target / ".example").read_text(), "included\n")
        self.assertFalse((target / "scripts/install.sh").exists())

    def test_existing_directory_and_user_data_are_never_overwritten_even_with_yes(self):
        parent = self.root / "installed"
        target = parent / "digital-brain"
        target.mkdir(parents=True)
        marker = target / "my-private-notes.txt"
        marker.write_text("do not remove")
        result = self.run_install(parent=parent, extra="y\n")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(marker.read_text(), "do not remove")
        self.assertEqual(list(target.iterdir()), [marker])

    def test_symlink_parent_is_rejected_without_writing_through_it(self):
        outside = self.root / "outside"
        outside.mkdir()
        alias = self.root / "alias"
        alias.symlink_to(outside, target_is_directory=True)
        result = self.run_install(parent=alias)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(outside.iterdir()), [])
        self.assertTrue(alias.is_symlink())

    def test_source_descendant_rejected_before_partial_copy(self):
        parent = self.brain / "nested"
        parent.mkdir()
        result = self.run_install(parent=parent)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(parent.iterdir()), [])

    def test_absolute_spaces_unicode_and_literal_backslash_supported(self):
        parent = self.root / "Install Here Ω \\ literal"
        parent.mkdir()
        result = self.run_install(parent=parent)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_installed(parent)

    def test_relative_custom_parent_is_literal_and_preserves_source(self):
        parent = self.project / "folder with spaces"
        parent.mkdir()
        before = (self.brain / "scripts/install.sh").read_bytes()
        result = self.run_install(parent="./folder with spaces")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_installed(parent)
        self.assertEqual((self.brain / "scripts/install.sh").read_bytes(), before)

    def test_user_and_project_modes_create_only_skill_parent_directories(self):
        for choice, anchor in (("1", self.home), ("2", self.project)):
            with self.subTest(choice=choice):
                result = self.run_install(choice=choice)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assert_installed(anchor / ".claude/skills")

    def test_existing_regular_file_is_preserved(self):
        parent = self.root / "parent"
        parent.mkdir()
        target = parent / "digital-brain"
        target.write_bytes(b"existing data")
        result = self.run_install(parent=parent)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(target.read_bytes(), b"existing data")

    def test_existing_and_dangling_target_symlinks_are_preserved(self):
        for name, existing in (("existing", True), ("dangling", False)):
            with self.subTest(name=name):
                parent = self.root / name
                parent.mkdir()
                outside = self.root / (name + "-outside")
                if existing:
                    outside.mkdir()
                target = parent / "digital-brain"
                target.symlink_to(outside, target_is_directory=True)
                result = self.run_install(parent=parent, extra="y\n")
                self.assertNotEqual(result.returncode, 0)
                self.assertTrue(target.is_symlink())
                if existing:
                    self.assertEqual(list(outside.iterdir()), [])

    def test_symlink_user_skills_ancestor_rejected(self):
        outside = self.root / "outside"
        outside.mkdir()
        (self.home / ".claude").symlink_to(outside, target_is_directory=True)
        result = self.run_install(choice="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(outside.iterdir()), [])

    def test_custom_parent_must_exist_and_may_not_traverse(self):
        for parent in (self.root / "missing/child", self.project / "../home", ""):
            with self.subTest(parent=str(parent)):
                result = self.run_install(parent=parent)
                self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root / "missing").exists())
        self.assertEqual(list(self.home.iterdir()), [])

    def test_source_root_target_rejected_without_deleting_source(self):
        before = (self.brain / "SKILL.md").read_bytes()
        result = self.run_install(parent=self.brain.parent, extra="y\n")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((self.brain / "SKILL.md").read_bytes(), before)

    def test_broad_target_home_project_and_filesystem_root_rejected(self):
        # / is tested only after the installer has a fail-closed target policy.
        for kind in ("home", "project"):
            parent = self.root / kind / "broad"
            target = parent / "digital-brain"
            target.mkdir(parents=True)
            marker = target / "keep"
            marker.write_text("keep")
            options = {kind: target}
            result = self.run_install(parent=parent, extra="y\n", **options)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(marker.read_text(), "keep")
        for parent in ("/", "//", "///"):
            result = self.run_install(parent=parent)
            self.assertNotEqual(result.returncode, 0)
        self.assertNotEqual(self.run_install(choice="1", home=Path("/")).returncode, 0)
        self.assertNotEqual(self.run_install(choice="2", project=Path("/")).returncode, 0)

    def test_source_symlink_and_special_file_rejected_before_target_creation(self):
        parent = self.root / "parent"
        parent.mkdir()
        linked = self.brain / "linked"
        linked.symlink_to(self.brain / "SKILL.md")
        result = self.run_install(parent=parent)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((parent / "digital-brain").exists())
        linked.unlink()
        os.mkfifo(linked)
        result = self.run_install(parent=parent)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((parent / "digital-brain").exists())

    def test_invalid_choice_eof_and_control_characters_do_not_install(self):
        for choice, parent in (("9", None), ("", None), ("3", "bad\tpath")):
            with self.subTest(choice=choice, parent=parent):
                result = self.run_install(choice=choice, parent=parent)
                self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(self.home.iterdir()), [])
        self.assertEqual(list(self.project.iterdir()), [])

    def test_concurrent_installs_have_one_exclusive_winner(self):
        parent = self.root / "parent"
        parent.mkdir()
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: self.run_install(parent=parent), range(2)))
        self.assertEqual(sorted(result.returncode for result in results), [0, 1])
        self.assert_installed(parent)

    def test_new_personal_data_is_private_and_parent_permissions_preserved(self):
        parent = self.root / "parent"
        parent.mkdir(mode=0o755)
        before = parent.stat().st_mode
        result = self.run_install(parent=parent)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(parent.stat().st_mode, before)
        self.assertEqual((parent / "digital-brain").stat().st_mode & 0o777, 0o700)
        self.assertEqual((parent / "digital-brain/SKILL.md").stat().st_mode & 0o777, 0o600)

    def test_missing_python_dependency_fails_before_effects(self):
        empty_bin = self.root / "empty-bin"
        empty_bin.mkdir()
        result = self.run_install(choice="1", path=empty_bin)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Python 3 is required", result.stderr)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_bounded_source_and_hardlinked_files_are_rejected_before_copy(self):
        parent = self.root / "parent"
        parent.mkdir()
        large = self.brain / "too-large"
        with large.open("wb") as stream:
            stream.truncate(16 * 1024 * 1024 + 1)
        result = self.run_install(parent=parent)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SOURCE_TOO_LARGE", result.stderr)
        self.assertEqual(list(parent.iterdir()), [])
        large.unlink()
        os.link(self.brain / "SKILL.md", self.brain / "hardlink")
        self.assertNotEqual(self.run_install(parent=parent).returncode, 0)
        self.assertEqual(list(parent.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
