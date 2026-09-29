"""Production preparation must not expose credentials to public PR code."""
from pathlib import Path
import re
import subprocess
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[3]


class ReleaseWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.raw = (ROOT / ".github/workflows/release-rehearsal.yml").read_text()
        self.workflow = yaml.load(self.raw, Loader=yaml.BaseLoader)

    def test_pr_and_merge_queue_run_without_privileged_triggers_or_credentials(self):
        self.assertEqual(set(self.workflow["on"]), {"pull_request", "push", "merge_group", "workflow_dispatch"})
        self.assertEqual(self.workflow["permissions"], {"contents": "read"})
        self.assertNotIn("secrets.", self.raw)
        self.assertNotIn("id-token:", self.raw)
        for job in self.workflow["jobs"].values():
            self.assertEqual(job["runs-on"], "ubuntu-24.04")
            self.assertNotIn("permissions", job)
            self.assertNotIn("environment", job)
            self.assertLessEqual(int(job["timeout-minutes"]), 15)

    def test_actions_pinned_and_checkout_never_persists_token(self):
        for job in self.workflow["jobs"].values():
            for step in job["steps"]:
                if "uses" in step:
                    self.assertRegex(step["uses"], r"^[A-Za-z0-9_/-]+@[0-9a-f]{40}$")
                if step.get("uses", "").startswith("actions/checkout@"):
                    self.assertEqual(step["with"]["persist-credentials"], "false")
                    self.assertNotIn("ref", step["with"])
                    self.assertNotIn("repository", step["with"])

    def test_only_aggregate_report_is_uploaded(self):
        uploads = [step for job in self.workflow["jobs"].values() for step in job["steps"]
                   if step.get("uses", "").startswith("actions/upload-artifact@")]
        self.assertEqual(len(uploads), 1)
        self.assertEqual(uploads[0]["with"]["path"], "release-rehearsal.json")
        self.assertNotIn("include-hidden-files", uploads[0]["with"])
        self.assertLessEqual(int(uploads[0]["with"]["retention-days"]), 14)

    def test_container_cannot_receive_source_secrets_or_network_at_smoke_time(self):
        commands = "\n".join(step.get("run", "") for step in self.workflow["jobs"]["runtime-image"]["steps"])
        self.assertRegex(commands, r"BASE_IMAGE=python:3\.12\.14-slim-bookworm@sha256:[a-f0-9]{64}")
        self.assertNotIn("docker push", commands)
        for command in commands.splitlines():
            if "docker run" not in command:
                continue
            sdk_gate = "--service-python" in command
            for required in ("--network none", "--read-only", "--cap-drop ALL",
                             "--security-opt no-new-privileges",
                             "--memory 2g" if sdk_gate else "--memory 256m",
                             "--pids-limit 256" if sdk_gate else "--pids-limit 64"):
                self.assertIn(required, command)
            forbidden = r"(?:^|\s)(-v|--volume|--env|-e|--privileged)(?:\s|=)" if sdk_gate else r"(?:^|\s)(-v|--volume|--mount|--env|-e|--privileged)(?:\s|=)"
            self.assertIsNone(re.search(forbidden, command))
            if sdk_gate:
                self.assertEqual(command.count("--mount"), 1)
                self.assertIn('--mount "type=bind,source=${GITHUB_WORKSPACE},target=/repo,readonly"', command)
                self.assertIn("--tmpfs /state:rw,nosuid,nodev,exec,size=512m,uid=10001,gid=10001,mode=0700", command)

    def test_real_sdk_gate_is_mandatory_zero_skip_tool_free_not_native_bypass(self):
        steps = self.workflow["jobs"]["runtime-image"]["steps"]
        gates = [step for step in steps if "verify_codex_runtime.py" in step.get("run", "")]
        self.assertEqual(len(gates), 1)
        gate = gates[0]
        self.assertNotIn("if", gate)
        self.assertNotIn("continue-on-error", gate)
        self.assertNotIn("||", gate["run"])
        self.assertIn("--profile tool_free", gate["run"])
        self.assertIn("--service-python /opt/context-research/venv/bin/python", gate["run"])
        self.assertIn("--entrypoint /opt/context-research/codex-venv/bin/python", gate["run"])
        self.assertNotIn("danger-full-access", gate["run"])

    def test_local_rendering_and_runtime_outputs_are_not_release_inputs(self):
        paths = ["output/pdfs/architecture.pdf", "tmp/pdfs/render.png", "xcrun_db",
                 ".env.local", "researcher/runtime/private.json"]
        result = subprocess.run(["git", "check-ignore", "--", *paths], cwd=ROOT,
                                capture_output=True, text=True, check=True)
        self.assertEqual(set(result.stdout.splitlines()), set(paths))
        template = subprocess.run(["git", "check-ignore", "--", ".env.example"], cwd=ROOT,
                                  capture_output=True, text=True)
        self.assertEqual(template.returncode, 1)


if __name__ == "__main__":
    unittest.main()
