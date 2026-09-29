"""Metadata checks for illustrative judge documents, not runtime registrations."""

import hashlib
from pathlib import Path
import re
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[3]
DOCUMENTS = (
    ("index.md", "llm-as-judge-agents", "Agents Index"),
    ("evaluator-agent/evaluator-agent.md", "evaluator-agent", "Evaluator Agent"),
    ("orchestrator-agent/orchestrator-agent.md", "orchestrator-agent", "Orchestrator Agent"),
    ("research-agent/research-agent.md", "research-agent", "Research Agent"),
)

# Freeze the exact main bodies at 6dbe1a1d868eab51a3bc9011b0f55e2891513e40.
# This replacement changes metadata only, including preserving terminal newlines.
# Intentional future body edits require reviewing and updating these baselines.
ORIGINAL_BODY_SHA256 = {
    "index.md": "8c85022761a077ebfa6b726d7de2a89d1af16a2ac95a091f7d9ec1b53d2f7ea7",
    "evaluator-agent/evaluator-agent.md": "69aa6364b5cc7015848ac0a62699b8e50d15ccd2e6e5cd4c5855bc3847832b11",
    "orchestrator-agent/orchestrator-agent.md": "84397b839c971c663f828ba6f76e82f51e2de404115d842d9f58ec1e50f87778",
    "research-agent/research-agent.md": "ef665f1a41159017b870032bc1bf1421e94b54c4df57aba39f549f40d7bd5c7f",
}


def metadata(document: str) -> tuple[dict[str, str], str]:
    """Require two unique string fields; permissions/configuration are out of scope."""
    match = re.match(r"\A---\n(.*?)\n---\n", document, re.DOTALL)
    if match is None:
        raise ValueError("Missing frontmatter")
    node = yaml.compose(match.group(1), Loader=yaml.SafeLoader)
    if not isinstance(node, yaml.MappingNode):
        raise ValueError("Expected mapping")
    keys = [key.value for key, _ in node.value]
    if len(keys) != 2 or set(keys) != {"name", "description"}:
        raise ValueError("Invalid metadata fields")
    parsed = yaml.safe_load(match.group(1))
    if not all(type(value) is str and value.strip() for value in parsed.values()):
        raise ValueError("Metadata must contain nonempty strings")
    return parsed, document[match.end():]


class JudgeAgentFrontmatterTests(unittest.TestCase):
    def check_document(self, index: int) -> dict[str, str]:
        path, name, heading = DOCUMENTS[index]
        document = (ROOT / "examples/llm-as-judge-skills/agents" / path).read_text()
        fields, body = metadata(document)
        self.assertEqual(fields["name"], name)
        self.assertGreater(len(fields["description"]), 20)
        self.assertTrue(body.lstrip().startswith(f"# {heading}\n"))
        return fields

    def test_index(self):
        self.assertIn("agents: evaluator", self.check_document(0)["description"])

    def test_evaluator(self):
        self.check_document(1)

    def test_orchestrator(self):
        self.check_document(2)

    def test_research(self):
        self.check_document(3)

    def test_names_are_unique(self):
        names = [self.check_document(index)["name"] for index in range(len(DOCUMENTS))]
        self.assertEqual(len(names), len(set(names)))

    def test_original_document_body_bytes_are_preserved(self):
        for path, expected in ORIGINAL_BODY_SHA256.items():
            with self.subTest(path=path):
                document = (ROOT / "examples/llm-as-judge-skills/agents" / path).read_bytes()
                header = re.match(rb"\A---\n.*?\n---\n", document, re.DOTALL)
                self.assertIsNotNone(header)
                body = document[header.end():]
                self.assertEqual(hashlib.sha256(body).hexdigest(), expected)

    def test_original_unquoted_index_description_is_invalid_yaml(self):
        with self.assertRaises(yaml.YAMLError):
            metadata('---\nname: index\ndescription: Index of agents: evaluator\n---\n# Body\n')

    def test_boolean_numeric_null_and_empty_descriptions_are_not_strings(self):
        for value in ("true", "false", "1", "null", '""', '" "'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                metadata(f'---\nname: "index"\ndescription: {value}\n---\n# Body\n')

    def test_duplicate_missing_and_runtime_fields_are_rejected(self):
        for header in (
            'name: "index"\nname: "other"\ndescription: "Agent index"',
            'name: "index"',
            'name: "index"\ndescription: "Agent index"\ntools: [shell]',
            'name: "index"\ndescription: "Agent index"\npermissionMode: bypassPermissions',
            '- name\n- description',
        ):
            with self.subTest(header=header), self.assertRaises(ValueError):
                metadata(f"---\n{header}\n---\n# Body\n")

    def test_missing_delimiters_are_rejected(self):
        for document in ('# Body\n', '---\nname: "index"\ndescription: "Agent index"\n# Body\n'):
            with self.subTest(document=document), self.assertRaises(ValueError):
                metadata(document)


if __name__ == "__main__":
    unittest.main()
