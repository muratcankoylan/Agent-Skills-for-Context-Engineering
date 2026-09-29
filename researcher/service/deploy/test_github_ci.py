"""Run the workflow's actual authority-selection shell with a bounded fake Git.

No GitHub event, repository mutation, provider key, or network is required. The
fake accepts only explicitly declared objects and the reviewed read-only Git
commands, so successful shell exit alone cannot hide the wrong authority.
"""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = ROOT / ".github/workflows/validate.yml"
BASE = "a" * 40
PROMOTED = "b" * 40
FAKE_GIT = '''import json, os, sys
from pathlib import Path
args = sys.argv[1:]
with Path(os.environ["FAKE_GIT_CALLS"]).open("a") as stream:
    stream.write(json.dumps(args) + "\\n")
if not args or args.pop(0) != "--no-replace-objects":
    sys.exit(71)
objects = json.loads(os.environ["FAKE_GIT_OBJECTS"])
if len(args) == 3 and args[:2] == ["cat-file", "-e"]:
    sys.exit(0 if args[2] in [value + "^{commit}" for value in objects] else 72)
branch = os.environ["DEFAULT_BRANCH"]
if args == ["-c", "core.hooksPath=/dev/null", "fetch", "--no-tags", "origin",
            "+refs/heads/" + branch + ":refs/remotes/origin/" + branch]:
    sys.exit(0)
if args == ["rev-parse", "refs/remotes/origin/" + branch + "^{commit}"]:
    print(os.environ["FAKE_GIT_PROMOTED"])
    sys.exit(0)
if args == ["merge-base", "HEAD", os.environ["FAKE_GIT_PROMOTED"]]:
    print(os.environ["FAKE_GIT_BASE"])
    sys.exit(0)
sys.exit(73)
'''


class GithubLifecycleWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # BaseLoader retains GitHub's YAML key "on" as text under YAML 1.1 too.
        cls.workflow = yaml.load(WORKFLOW.read_text(), Loader=yaml.BaseLoader)
        cls.steps = cls.workflow["jobs"]["validate"]["steps"]
        cls.authorities = next(step for step in cls.steps if step.get("id") == "lifecycle-authorities")

    def execute(self, *, objects=None, **changes):
        with tempfile.TemporaryDirectory(prefix="github-lifecycle-test-") as directory:
            root = Path(directory)
            binary = root / "git"
            binary.write_text(f"#!{sys.executable}\n" + FAKE_GIT)
            binary.chmod(0o700)
            output = root / "outputs"
            calls = root / "git-calls"
            environment = {
                "PATH": str(root) + ":/usr/bin:/bin",
                "HOME": str(root),
                "EVENT_NAME": "merge_group",
                "DEFAULT_BRANCH": "main",
                "PR_BASE_SHA": "c" * 40,
                "PR_BASE_REF": "unrelated-proposal",
                "PUSH_BEFORE_SHA": "d" * 40,
                "MERGE_GROUP_BASE_SHA": BASE,
                "MERGE_GROUP_BASE_REF": "refs/heads/main",
                "GITHUB_OUTPUT": str(output),
                "FAKE_GIT_CALLS": str(calls),
                "FAKE_GIT_OBJECTS": json.dumps(objects if objects is not None else [BASE, PROMOTED]),
                "FAKE_GIT_BASE": BASE,
                "FAKE_GIT_PROMOTED": PROMOTED,
                "GIT_NO_REPLACE_OBJECTS": "1",
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_CONFIG_GLOBAL": "/dev/null",
            }
            environment.update(changes)
            result = subprocess.run(
                ["/bin/bash", "--noprofile", "--norc", "-e", "-o", "pipefail", "-c", self.authorities["run"]],
                cwd=root, env=environment, capture_output=True, text=True, timeout=10, check=False,
            )
            values = dict(line.split("=", 1) for line in output.read_text().splitlines()) if output.exists() else {}
            arguments = [json.loads(line) for line in calls.read_text().splitlines()] if calls.exists() else []
            return result, values, arguments

    def test_merge_queue_trigger_and_event_bindings_are_explicit(self):
        self.assertEqual(self.workflow["on"]["merge_group"], {"types": ["checks_requested"]})
        self.assertEqual(self.authorities["env"]["MERGE_GROUP_BASE_SHA"], "${{ github.event.merge_group.base_sha }}")
        self.assertEqual(self.authorities["env"]["MERGE_GROUP_BASE_REF"], "${{ github.event.merge_group.base_ref }}")
        self.assertEqual(self.workflow["permissions"], {"contents": "read"})
        self.assertEqual(self.steps[0]["with"]["persist-credentials"], "false")
        self.assertEqual([step["name"] for step in self.steps[:5]], [
            "Checkout", "Pin lifecycle Git authorities", "Set up Python",
            "Install pinned lifecycle parser dependency", "Specification lifecycle against protected base",
        ])

    def test_merge_group_uses_event_default_base_not_candidate_or_newer_tip(self):
        result, values, calls = self.execute()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(values, {"base_sha": BASE, "promoted_sha": BASE})
        self.assertEqual(calls, [["--no-replace-objects", "cat-file", "-e", BASE + "^{commit}"]] * 2)

    def test_merge_group_supports_exact_sha256_and_non_main_default(self):
        digest = "e" * 64
        result, values, calls = self.execute(objects=[digest], MERGE_GROUP_BASE_SHA=digest,
                                            DEFAULT_BRANCH="release/stable", MERGE_GROUP_BASE_REF="refs/heads/release/stable")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(values, {"base_sha": digest, "promoted_sha": digest})
        self.assertEqual(len(calls), 2)

    def test_merge_group_wrong_or_missing_default_reference_fails_before_git(self):
        for changes in ({"MERGE_GROUP_BASE_REF": ""}, {"MERGE_GROUP_BASE_REF": "main"},
                        {"MERGE_GROUP_BASE_REF": "refs/heads/proposal"},
                        {"MERGE_GROUP_BASE_REF": "refs/heads/main\nrefs/heads/other"},
                        {"DEFAULT_BRANCH": "", "MERGE_GROUP_BASE_REF": "refs/heads/"}):
            with self.subTest(changes=changes):
                result, values, calls = self.execute(**changes)
                self.assertEqual(result.returncode, 2)
                self.assertIn("protected default branch", result.stderr)
                self.assertEqual((values, calls), ({}, []))

    def test_merge_group_malformed_or_zero_sha_fails_before_git(self):
        for value in ("", "0" * 40, "0" * 64, "a" * 39, "a" * 41, "A" * 40,
                      "g" * 40, BASE + "\n", " " + BASE, BASE + "; false", "HEAD", "refs/heads/main"):
            with self.subTest(value=value):
                result, values, calls = self.execute(MERGE_GROUP_BASE_SHA=value)
                self.assertEqual(result.returncode, 2)
                self.assertIn("exact nonzero base SHA", result.stderr)
                self.assertEqual((values, calls), ({}, []))

    def test_merge_group_missing_git_object_does_not_publish_authority(self):
        result, values, calls = self.execute(objects=[])
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(values, {})
        self.assertEqual(calls, [["--no-replace-objects", "cat-file", "-e", BASE + "^{commit}"]])

    def test_main_pull_request_still_uses_its_exact_base(self):
        result, values, calls = self.execute(EVENT_NAME="pull_request", PR_BASE_SHA=BASE, PR_BASE_REF="main")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(values, {"base_sha": BASE, "promoted_sha": BASE})
        self.assertEqual(len(calls), 2)

    def test_stacked_pull_request_keeps_promoted_default_separate(self):
        result, values, calls = self.execute(EVENT_NAME="pull_request", PR_BASE_SHA=BASE, PR_BASE_REF="proposal")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(values, {"base_sha": BASE, "promoted_sha": PROMOTED})
        self.assertEqual(calls[0][-1], "+refs/heads/main:refs/remotes/origin/main")
        self.assertEqual(calls[-1][-1], PROMOTED + "^{commit}")

    def test_push_and_manual_workflow_authorities_remain_distinct(self):
        for event, changes, expected in (
            ("push", {"PUSH_BEFORE_SHA": BASE}, {"base_sha": BASE, "promoted_sha": BASE}),
            ("workflow_dispatch", {}, {"base_sha": BASE, "promoted_sha": PROMOTED}),
        ):
            with self.subTest(event=event):
                result, values, _ = self.execute(EVENT_NAME=event, **changes)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(values, expected)

    def test_unsupported_events_cannot_fall_back_to_merge_group_values(self):
        result, values, calls = self.execute(EVENT_NAME="pull_request_target")
        self.assertEqual(result.returncode, 2)
        self.assertEqual((values, calls), ({}, []))


class AgentsTransportWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.workflow = yaml.load(
            (ROOT / ".github/workflows/agents-api.yml").read_text(), Loader=yaml.BaseLoader)
        self.job = self.workflow["jobs"]["offline-contracts"]

    def test_transport_import_closure_is_installed_before_contract_execution(self):
        steps = self.job["steps"]
        commands = [(index, step.get("run", "")) for index, step in enumerate(steps)]
        installations = [(index, command) for index, command in commands
                         if "pip install" in command]
        self.assertEqual(len(installations), 1)
        index, install = installations[0]
        self.assertEqual(install.splitlines(), [
            "python -m pip install --require-hashes --only-binary=:all: -r requirements-dev.txt",
            "python -m pip check",
        ])
        tests = [(index, command) for index, command in commands if "test_openai_agents.py" in command]
        self.assertEqual(len(tests), 1)
        self.assertLess(index, tests[0][0])
        self.assertEqual(tests[0][1],
            "python -m unittest discover -s researcher/service/tests -p test_openai_agents.py -v")
        self.assertEqual(self.job["strategy"]["matrix"]["python"], ["3.11", "3.12"])
        self.assertNotIn("stdlib-only", " ".join(step.get("name", "") for step in steps))
        self.assertEqual(self.workflow["permissions"], {"contents": "read"})
        self.assertEqual(steps[0]["with"]["persist-credentials"], "false")

    def test_dependency_and_shared_schema_changes_trigger_both_transport_gates(self):
        for event in ("pull_request", "push"):
            with self.subTest(event=event):
                self.assertTrue({"requirements-dev.in", "requirements-dev.txt",
                    "researcher/scripts/schema_contract.py", "researcher/service/**",
                    ".github/workflows/agents-api.yml"}.issubset(self.workflow["on"][event]["paths"]))


if __name__ == "__main__":
    unittest.main()
