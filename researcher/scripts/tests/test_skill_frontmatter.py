"""Unit tests for the shared SKILL.md frontmatter parser.

Run directly or via the standard library test runner:

    python3 -m unittest researcher.scripts.tests.test_skill_frontmatter
    python3 researcher/scripts/tests/test_skill_frontmatter.py
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = SCRIPTS_DIR.parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import skill_frontmatter as sf  # noqa: E402


VALID_DESC = "A valid description that is comfortably longer than the minimum."


class SplitFrontmatterTests(unittest.TestCase):
    def test_lf(self) -> None:
        inner, body = sf.split_frontmatter(f"---\nname: foo\ndescription: {VALID_DESC}\n---\n# Body\ntext")
        self.assertIn("name: foo", inner)
        self.assertEqual(body, "# Body\ntext")

    def test_crlf(self) -> None:
        text = f"---\r\nname: foo\r\ndescription: {VALID_DESC}\r\n---\r\n# Body\r\ntext"
        inner, body = sf.split_frontmatter(text)
        self.assertIn("name: foo", inner)
        self.assertFalse(inner.endswith("\r"))
        self.assertEqual(body, "# Body\r\ntext")

    def test_bom(self) -> None:
        text = f"\ufeff---\nname: foo\ndescription: {VALID_DESC}\n---\nbody"
        inner, body = sf.split_frontmatter(text)
        self.assertIn("name: foo", inner)
        self.assertEqual(body, "body")

    def test_no_frontmatter(self) -> None:
        inner, body = sf.split_frontmatter("# Heading\nno frontmatter")
        self.assertIsNone(inner)
        self.assertEqual(body, "# Heading\nno frontmatter")

    def test_unterminated_frontmatter(self) -> None:
        inner, _ = sf.split_frontmatter("---\nname: foo\nnever closes")
        self.assertIsNone(inner)


class ParseFrontmatterTests(unittest.TestCase):
    def test_valid_plain(self) -> None:
        data, issues = sf.parse_frontmatter(f"---\nname: foo\ndescription: {VALID_DESC}\n---\nbody")
        self.assertEqual(issues, [])
        self.assertEqual(data["name"], "foo")
        self.assertEqual(data["description"], VALID_DESC)

    def test_quoted_description_with_colon(self) -> None:
        text = '---\nname: foo\ndescription: "This skill: handles colons safely and clearly."\n---\nbody'
        data, issues = sf.parse_frontmatter(text)
        self.assertEqual(issues, [])
        self.assertEqual(data["description"], "This skill: handles colons safely and clearly.")

    def test_block_scalar_description(self) -> None:
        text = "---\nname: foo\ndescription: >\n  multi line\n  description text that is long enough\n---\nbody"
        data, issues = sf.parse_frontmatter(text)
        self.assertEqual(issues, [])
        self.assertIn("multi line description", data["description"])

    def test_missing_frontmatter(self) -> None:
        _data, issues = sf.parse_frontmatter("# No frontmatter")
        self.assertTrue(any("delimiter" in i for i in issues))

    def test_missing_name(self) -> None:
        _data, issues = sf.parse_frontmatter(f"---\ndescription: {VALID_DESC}\n---\nbody")
        self.assertIn("missing name", issues)

    def test_missing_description(self) -> None:
        _data, issues = sf.parse_frontmatter("---\nname: foo\n---\nbody")
        self.assertIn("missing description", issues)

    def test_short_description(self) -> None:
        _data, issues = sf.parse_frontmatter("---\nname: foo\ndescription: too short\n---\nbody")
        self.assertTrue(any("too short" in i for i in issues))

    def test_non_mapping_frontmatter(self) -> None:
        if sf.yaml is None:
            self.skipTest("PyYAML required for mapping validation")
        _data, issues = sf.parse_frontmatter("---\n- just\n- a\n- list\n---\nbody")
        self.assertTrue(any("mapping" in i for i in issues))


@unittest.skipIf(sf.yaml is None, "PyYAML required for strict-YAML regression test")
class StrictYamlRegressionTests(unittest.TestCase):
    """Guards the exact bug fixed in this PR: unquoted colons in descriptions."""

    def test_unquoted_colon_is_rejected(self) -> None:
        text = "---\nname: foo\ndescription: This skill: does several things without quoting\n---\nbody"
        _data, issues = sf.parse_frontmatter(text)
        self.assertTrue(any("invalid YAML" in i for i in issues), issues)


class FallbackParserTests(unittest.TestCase):
    def test_fallback_plain(self) -> None:
        inner = f"name: foo\ndescription: {VALID_DESC}"
        data, issues = sf._parse_frontmatter_fallback(inner, [])
        self.assertEqual(issues, [])
        self.assertEqual(data["description"], VALID_DESC)

    def test_fallback_block_scalar(self) -> None:
        inner = "name: foo\ndescription: >\n  multi line\n  description long enough now"
        data, issues = sf._parse_frontmatter_fallback(inner, [])
        self.assertEqual(issues, [])
        self.assertIn("multi line description", data["description"])


class FormatFrontmatterTests(unittest.TestCase):
    def test_round_trip_with_colon(self) -> None:
        desc = "This skill: handles colons, commas, and 'quotes' all at once."
        rendered = sf.format_frontmatter("foo-bar", desc)
        data, issues = sf.parse_frontmatter(rendered + "body")
        self.assertEqual(issues, [])
        self.assertEqual(data["name"], "foo-bar")
        self.assertEqual(data["description"], desc)


class CorpusIntegrationTests(unittest.TestCase):
    """Every published skill must parse cleanly with zero issues."""

    def test_all_skills_parse_clean(self) -> None:
        skills_dir = REPO_ROOT / "skills"
        skill_files = sorted(skills_dir.glob("*/SKILL.md"))
        self.assertTrue(skill_files, "no skills found")
        for path in skill_files:
            with self.subTest(skill=path.parent.name):
                data, issues = sf.parse_frontmatter(path.read_text(encoding="utf-8"))
                self.assertEqual(issues, [], f"{path.parent.name}: {issues}")
                self.assertEqual(data["name"], path.parent.name)

    @unittest.skipIf(sf.yaml is None, "PyYAML required for strict example validation")
    def test_example_and_template_frontmatter_is_strict_yaml(self) -> None:
        """Demo and template skills must be strict-YAML parseable so developers can copy them."""
        extra = [REPO_ROOT / "template" / "SKILL.md", REPO_ROOT / "SKILL.md"]
        example_skills = sorted((REPO_ROOT / "examples").glob("**/SKILL.md"))
        for path in extra + example_skills:
            if not path.exists():
                continue
            with self.subTest(skill=str(path.relative_to(REPO_ROOT))):
                inner, _ = sf.split_frontmatter(path.read_text(encoding="utf-8"))
                self.assertIsNotNone(inner, f"{path} missing frontmatter")
                loaded = sf.yaml.safe_load(inner)
                self.assertIsInstance(loaded, dict)
                self.assertTrue(str(loaded.get("description", "")).strip())


if __name__ == "__main__":
    unittest.main()
