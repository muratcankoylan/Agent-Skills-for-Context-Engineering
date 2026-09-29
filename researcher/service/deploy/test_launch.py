"""Release preflight and packaging-contract tests, not Docker/systemd execution."""

import importlib.util
from pathlib import Path
import re
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


DIRECTORY = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("deployment_launch", DIRECTORY / "launch.py")
launch = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(launch)


class DeploymentTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="research-deploy-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve() / "release"
        self.root.mkdir()
        (self.root / ".git").mkdir()
        (self.root / "requirements-dev.txt").write_text("fixture-lock\n")
        self.lock = self.root.parent / "runtime-lock.txt"
        self.lock.write_text("fixture-lock\n")
        self.environment = {"RESEARCH_RELEASE_DIR": str(self.root), "RESEARCH_RELEASE_COMMIT": "a" * 40,
                            "RESEARCH_DEPENDENCY_LOCK": str(self.lock)}
        self.source_sdk = self.root / "researcher/service/deploy/requirements-codex-linux.txt"
        self.source_sdk.parent.mkdir(parents=True)
        self.source_sdk.write_text("fixture-sdk-lock\n")
        self.sdk_lock = self.root.parent / "sdk-lock.txt"
        self.sdk_lock.write_text("fixture-sdk-lock\n")
        self.environment["RESEARCH_CODEX_DEPENDENCY_LOCK"] = str(self.sdk_lock)

    def git(self, head=None, dirty=""):
        return [subprocess.CompletedProcess([], 0, head or "a" * 40, ""),
                subprocess.CompletedProcess([], 0, str(self.root), ""),
                subprocess.CompletedProcess([], 0, dirty, "")]

    def test_clean_readonly_release_and_lock_match(self):
        with patch.object(launch.os, "access", return_value=False), patch.object(launch.subprocess, "run", side_effect=self.git()) as git:
            self.assertEqual(launch.verify_release(self.environment), self.root)
        self.assertEqual(git.call_count, 3)
        for call in git.call_args_list:
            self.assertEqual(call.kwargs["timeout"], 15)
            self.assertEqual(call.kwargs["env"]["GIT_OPTIONAL_LOCKS"], "0")
            self.assertIn("core.fsmonitor=false", call.args[0])

    def test_pin_required_before_git(self):
        for pin in ("", "main", "latest", "a" * 39, "A" * 40):
            with patch.object(launch.subprocess, "run") as git:
                with self.assertRaisesRegex(ValueError, "PINNED_RELEASE_COMMIT_REQUIRED"):
                    launch.verify_release({**self.environment, "RESEARCH_RELEASE_COMMIT": pin})
                git.assert_not_called()

    def test_mcp_profile_is_explicit_binary_choice(self):
        for profile in ("", "true", "yes", "2", " 1"):
            with patch.object(launch.subprocess, "run") as git:
                with self.assertRaisesRegex(ValueError, "INVALID_MCP_DEPENDENCY_PROFILE"):
                    launch.verify_release({**self.environment, "RESEARCH_INSTALL_MCP": profile})
                git.assert_not_called()

    def test_optional_mcp_profile_binds_both_locks(self):
        source_mcp = self.root / "researcher/service/requirements-mcp.txt"
        source_mcp.parent.mkdir(parents=True, exist_ok=True)
        source_mcp.write_text("fixture-mcp-lock\n")
        runtime_mcp = self.root.parent / "runtime-mcp-lock.txt"
        runtime_mcp.write_text("fixture-mcp-lock\n")
        for profile in ("0", "1"):
            environment = {**self.environment, "RESEARCH_INSTALL_MCP": profile,
                           "RESEARCH_MCP_DEPENDENCY_LOCK": str(runtime_mcp)}
            with patch.object(launch.os, "access", return_value=False), patch.object(launch.subprocess, "run", side_effect=self.git()):
                self.assertEqual(launch.verify_release(environment), self.root)
        runtime_mcp.write_text("different-mcp-lock\n")
        for profile in ("0", "1"):
            environment = {**self.environment, "RESEARCH_INSTALL_MCP": profile,
                           "RESEARCH_MCP_DEPENDENCY_LOCK": str(runtime_mcp)}
            with patch.object(launch.os, "access", return_value=False), patch.object(launch.subprocess, "run", side_effect=self.git()):
                with self.assertRaisesRegex(ValueError, "MCP_RUNTIME_DEPENDENCY_LOCK_MISMATCH"):
                    launch.verify_release(environment)
        runtime_mcp.write_text("fixture-mcp-lock\n")
        self.lock.write_text("different-core-lock\n")
        with patch.object(launch.os, "access", return_value=False), patch.object(launch.subprocess, "run", side_effect=self.git()):
            with self.assertRaisesRegex(ValueError, "^RUNTIME_DEPENDENCY_LOCK_MISMATCH$"):
                launch.verify_release(environment)

    def test_enabled_mcp_requires_real_matching_lock(self):
        source_mcp = self.root / "researcher/service/requirements-mcp.txt"
        source_mcp.parent.mkdir(parents=True, exist_ok=True)
        source_mcp.write_text("fixture-mcp-lock\n")
        linked_lock = self.root.parent / "linked-mcp-lock.txt"
        linked_lock.symlink_to(source_mcp)
        oversized_lock = self.root.parent / "oversized-mcp-lock.txt"
        oversized_lock.write_bytes(b"x" * 262145)
        for path in ("", "relative.txt", str(self.root.parent / "absent.txt"), str(linked_lock), str(oversized_lock)):
            environment = {**self.environment, "RESEARCH_INSTALL_MCP": "1", "RESEARCH_MCP_DEPENDENCY_LOCK": path}
            with patch.object(launch.os, "access", return_value=False), patch.object(launch.subprocess, "run", side_effect=self.git()):
                with self.assertRaisesRegex(ValueError, "MCP_RUNTIME_DEPENDENCY_LOCK_MISMATCH"):
                    launch.verify_release(environment)

    def test_writable_or_external_worktree_release_rejected(self):
        with patch.object(launch.os, "access", return_value=True), patch.object(launch.subprocess, "run") as git:
            with self.assertRaisesRegex(ValueError, "READ_ONLY_RELEASE_REQUIRED"):
                launch.verify_release(self.environment)
            git.assert_not_called()
        (self.root / ".git").rmdir()
        (self.root / ".git").write_text("gitdir: /unmounted/private-worktree\n")
        with self.assertRaisesRegex(ValueError, "STANDALONE_RELEASE_CLONE_REQUIRED"):
            launch.verify_release(self.environment)

    def test_wrong_commit_dirty_files_and_lock_mismatch_fail(self):
        for results, code in ((self.git(head="b" * 40), "RELEASE_COMMIT_MISMATCH"),
                              (self.git(dirty="!! private-state/"), "RELEASE_CLONE_NOT_CLEAN")):
            with patch.object(launch.os, "access", return_value=False), patch.object(launch.subprocess, "run", side_effect=results):
                with self.assertRaisesRegex(ValueError, code):
                    launch.verify_release(self.environment)
        self.lock.write_text("other-runtime-lock\n")
        with patch.object(launch.os, "access", return_value=False), patch.object(launch.subprocess, "run", side_effect=self.git()):
            with self.assertRaisesRegex(ValueError, "RUNTIME_DEPENDENCY_LOCK_MISMATCH"):
                launch.verify_release(self.environment)

    def test_root_and_repo_argument_override_cannot_execute_service(self):
        with patch.object(launch.os, "geteuid", return_value=0), patch.object(launch.os, "execv") as execute:
            self.assertEqual(launch.main(), 1)
            execute.assert_not_called()
        for arguments in (["launch.py", "status", "--repo", str(self.root), "--repo=/other"],
                          ["launch.py", "status", "--repo"], ["launch.py", "status"]):
            with patch.object(launch.os, "geteuid", return_value=10001), patch.object(launch, "verify_release", return_value=self.root), \
                    patch.object(launch.sys, "argv", arguments), patch.object(launch.os, "execv") as execute:
                self.assertEqual(launch.main(), 1)
                execute.assert_not_called()

    def test_dockerfile_has_explicit_pin_hashes_no_source_copy_and_nonroot(self):
        dockerfile = (DIRECTORY / "Dockerfile").read_text()
        self.assertIn("ARG BASE_IMAGE\nFROM ${BASE_IMAGE}", dockerfile)
        self.assertNotIn("ARG BASE_IMAGE=", dockerfile)
        self.assertIn("--require-hashes --only-binary=:all:", dockerfile)
        self.assertIn("USER 10001:10001", dockerfile)
        self.assertIn("PYTHONPATH=/repo", dockerfile)
        copies = [line for line in dockerfile.splitlines() if line.startswith("COPY ")]
        self.assertEqual(copies, ["COPY requirements-dev.txt /opt/context-research/requirements-dev.txt",
                                  "COPY researcher/service/requirements-mcp.txt /opt/context-research/requirements-mcp.txt",
                                  "COPY researcher/service/deploy/requirements-codex-linux.txt /opt/context-research/requirements-codex-linux.txt",
                                  "COPY researcher/service/deploy/launch.py /opt/context-research/launch.py"])
        self.assertIn("ARG INSTALL_MCP=0", dockerfile)
        self.assertIn('if sys.argv[1] in ("0", "1")', dockerfile)
        self.assertIn('if [ "$INSTALL_MCP" = "1" ]; then', dockerfile)
        self.assertIn("RESEARCH_INSTALL_MCP=${INSTALL_MCP}", dockerfile)
        self.assertIn("RESEARCH_MCP_DEPENDENCY_LOCK=/opt/context-research/requirements-mcp.txt", dockerfile)
        self.assertIn("!researcher/service/requirements-mcp.txt", (DIRECTORY / "Dockerfile.dockerignore").read_text())
        self.assertIn("!researcher/service/deploy/requirements-codex-linux.txt", (DIRECTORY / "Dockerfile.dockerignore").read_text())
        self.assertIn("RESEARCH_CODEX_DEPENDENCY_LOCK=/opt/context-research/requirements-codex-linux.txt", dockerfile)
        self.assertIn("RESEARCH_CODEX_PYTHON=/opt/context-research/codex-venv/bin/python", dockerfile)
        self.assertIn('platform.machine() in ("aarch64","x86_64")', dockerfile)
        self.assertNotIn("INSTALL_CODEX", dockerfile)
        self.assertIn('assert version("openai-codex") == version("openai-codex-cli-bin") == "0.159.0"', dockerfile)
        self.assertIn('CMD ["status"', dockerfile)
        self.assertNotIn("latest", dockerfile)

    def test_explicit_organization_selector_preserves_release_preflight(self):
        for prefix, module in (([], "researcher.service"),
                               (["organization"], "researcher.service.organization")):
            arguments = ["launch.py", *prefix, "status", "--repo", str(self.root)]
            with patch.object(launch.os, "geteuid", return_value=10001), \
                    patch.object(launch, "verify_release", return_value=self.root) as verify, \
                    patch.object(launch, "verify_sdk_startup") as sdk, \
                    patch.object(launch.sys, "argv", arguments), \
                    patch.object(launch.os, "environ", {}), patch.object(launch.os, "chdir"), \
                    patch.object(launch.os, "execv") as execute:
                self.assertEqual(launch.main(), 0)
                verify.assert_called_once()
                sdk.assert_not_called()
                sdk_arguments = [] if not prefix else ["--sdk-python", launch.sys.executable]
                execute.assert_called_once_with(launch.sys.executable,
                    [launch.sys.executable, "-B", "-m", module, "status", "--repo", str(self.root), *sdk_arguments])
        with patch.object(launch.os, "geteuid", return_value=10001), \
                patch.object(launch, "verify_release", side_effect=ValueError("RELEASE_CLONE_NOT_CLEAN")), \
                patch.object(launch.sys, "argv", ["launch.py", "organization", "serve", "--repo", str(self.root)]), \
                patch.object(launch.os, "execv") as execute:
            self.assertEqual(launch.main(), 1)
            execute.assert_not_called()

    def test_systemd_templates_bound_state_identity_resources_and_api_loopback(self):
        for name in ("context-research.service", "context-research-api.service", "context-research-organization.service"):
            unit = (DIRECTORY / name).read_text()
            for setting in ("User=context-research", "Group=context-research", "UMask=0077",
                            "StateDirectoryMode=0700", "ProtectSystem=strict", "NoNewPrivileges=true",
                            "ReadWritePaths=/var/lib/context-research", "CapabilityBoundingSet=",
                            "EnvironmentFile=/etc/context-research/release.env"):
                self.assertIn(setting, unit)
            mode = "mixed" if name == "context-research-organization.service" else "control-group"
            self.assertIn(f"KillMode={mode}", unit)
            self.assertIn("Environment=RESEARCH_CODEX_DEPENDENCY_LOCK=/opt/context-research/requirements-codex-linux.txt", unit)
            self.assertIn("Environment=RESEARCH_CODEX_PYTHON=/opt/context-research/codex-venv/bin/python", unit)
            self.assertIn("MemoryMax=", unit)
            self.assertIn("TasksMax=", unit)
        worker = (DIRECTORY / "context-research.service").read_text()
        api = (DIRECTORY / "context-research-api.service").read_text()
        self.assertIn("--live", worker)
        self.assertIn("--host 127.0.0.1 --port 8787", api)
        self.assertNotIn("worker.env", api)
        self.assertNotIn("operator.env", worker)

    def test_organization_unit_has_one_existing_authority_and_no_implicit_dataset(self):
        unit = (DIRECTORY / "context-research-organization.service").read_text()
        self.assertIn("Conflicts=context-research.service", unit)
        self.assertIn("launch.py organization serve", unit)
        self.assertIn("--authority /var/lib/context-research/authority", unit)
        self.assertIn("--source-state /var/lib/context-research/retrieval", unit)
        self.assertIn("--state /var/lib/context-research/organization", unit)
        self.assertIn("--env-file /etc/context-research/provider-literals.env --live", unit)
        self.assertNotIn("worker.env", unit)
        self.assertNotIn("operator.env", unit)
        self.assertNotIn("--dataset", unit)
        self.assertIn("TasksMax=256", unit)
        self.assertIn("TimeoutStopSec=600", unit)
        self.assertNotIn("SendSIGKILL=no", unit)

    def test_real_sdk_gate_includes_current_actions_and_cooperative_drain(self):
        verifier = (DIRECTORY / "verify_codex_runtime.py").read_text()
        self.assertIn('"test_pipeline_actions.SDKPipelineActionTests"', verifier)
        self.assertIn('"test_shutdown.SDKShutdownTests"', verifier)

    def test_optional_and_core_locks_agree_on_shared_packages(self):
        root = DIRECTORY.parents[2]
        def pins(path):
            rows = re.findall(r"^([A-Za-z0-9_.-]+)==([^\s;\\]+)", path.read_text(), re.MULTILINE)
            normalized = [(name.lower().replace('_', '-'), version) for name, version in rows]
            self.assertTrue(normalized)
            self.assertEqual(len(normalized), len(dict(normalized)))
            return dict(normalized)
        core = pins(root / "requirements-dev.txt")
        optional = pins(root / "researcher/service/requirements-mcp.txt")
        shared = core.keys() & optional.keys()
        self.assertIn("click", shared)
        self.assertEqual({name: core[name] for name in shared},
                         {name: optional[name] for name in shared})
        self.assertIn("-c ../../requirements-dev.txt",
                      (root / "researcher/service/requirements-mcp.in").read_text().splitlines())
        sdk = pins(DIRECTORY / "requirements-codex-linux.txt")
        self.assertEqual(len(sdk), 8)
        for other in (core, optional):
            shared = sdk.keys() & other.keys()
            self.assertEqual({name: sdk[name] for name in shared}, {name: other[name] for name in shared})

    def test_mandatory_sdk_lock_missing_mismatched_or_symlinked_never_launches(self):
        alias = self.root.parent / "sdk-alias.txt"
        alias.symlink_to(self.sdk_lock)
        for value in ("", "relative.txt", str(alias), str(self.root.parent / "absent.txt")):
            with self.subTest(value=value), patch.object(launch.os, "access", return_value=False), \
                    patch.object(launch.subprocess, "run", side_effect=self.git()), \
                    self.assertRaisesRegex(ValueError, "CODEX_RUNTIME_DEPENDENCY_LOCK_MISMATCH"):
                launch.verify_release({**self.environment, "RESEARCH_CODEX_DEPENDENCY_LOCK": value})
        self.sdk_lock.write_text("different\n")
        with patch.object(launch.os, "access", return_value=False), \
                patch.object(launch.subprocess, "run", side_effect=self.git()), \
                self.assertRaisesRegex(ValueError, "CODEX_RUNTIME_DEPENDENCY_LOCK_MISMATCH"):
            launch.verify_release(self.environment)

    def test_sdk_argument_must_match_actual_preflight_interpreter(self):
        for tail in (["--sdk-python", "/different/python"], ["--sdk-python=/configured/python"],
                     ["--sdk-python", "/configured/python", "--sdk-python", "/configured/python"]):
            with patch.object(launch.os, "geteuid", return_value=10001), \
                    patch.object(launch, "verify_release", return_value=self.root), \
                    patch.object(launch, "verify_sdk_startup") as sdk, \
                    patch.object(launch.sys, "argv", ["launch.py", "organization", "status", "--repo", str(self.root), *tail]), \
                    patch.object(launch.os, "environ", {"RESEARCH_CODEX_PYTHON": "/configured/python"}), \
                    patch.object(launch.os, "execv") as execute:
                self.assertEqual(launch.main(), 1)
                sdk.assert_not_called()
                execute.assert_not_called()

    def test_failed_sdk_startup_cannot_execute_service(self):
        with patch.object(launch.os, "geteuid", return_value=10001), \
                patch.object(launch, "verify_release", return_value=self.root), \
                patch.object(launch, "verify_sdk_startup", side_effect=ValueError("CODEX_RUNTIME_STARTUP_FAILED")), \
                patch.object(launch.sys, "argv", ["launch.py", "organization", "serve", "--repo", str(self.root)]), \
                patch.object(launch.os, "execv") as execute:
            self.assertEqual(launch.main(), 1)
            execute.assert_not_called()

    def test_model_admission_probes_sdk_but_readonly_and_source_commands_do_not(self):
        for prefix, command, expected in ((["organization"], "cycle", True),
                                           (["organization"], "serve", True),
                                           (["organization"], "init", False),
                                           (["organization"], "status", False),
                                           ([], "api", False), ([], "serve", False)):
            with self.subTest(prefix=prefix, command=command), patch.object(launch.os, "geteuid", return_value=10001), \
                    patch.object(launch, "verify_release", return_value=self.root), \
                    patch.object(launch, "verify_sdk_startup") as sdk, \
                    patch.object(launch.sys, "argv", ["launch.py", *prefix, command, "--repo", str(self.root)]), \
                    patch.object(launch.os, "environ", {}), patch.object(launch.os, "chdir"), \
                    patch.object(launch.os, "execv"):
                self.assertEqual(launch.main(), 0)
                self.assertEqual(sdk.call_count, int(expected))

    def test_sdk_preflight_uses_temporary_private_fixture_and_tool_free_profile(self):
        observed = []
        def probe(**kwargs):
            observed.append(kwargs)
            self.assertTrue(kwargs["workspace_parent"].is_dir())
            self.assertEqual(kwargs["workspace_parent"].stat().st_mode & 0o777, 0o700)
            return {"status": "passed"}
        module = SimpleNamespace(run_preflight=probe, PreflightError=ValueError)
        spec = SimpleNamespace(loader=SimpleNamespace(exec_module=lambda _: None))
        with patch.object(launch.importlib.util, "spec_from_file_location", return_value=spec), \
                patch.object(launch.importlib.util, "module_from_spec", return_value=module):
            launch.verify_sdk_startup(self.root, "/configured/python")
        self.assertEqual(len(observed), 1)
        self.assertEqual(observed[0]["profile"], "tool_free")
        self.assertEqual(observed[0]["timeout_seconds"], 30)
        self.assertEqual(observed[0]["sdk_python"], "/configured/python")
        self.assertFalse(observed[0]["workspace_parent"].exists())

    def test_generic_sdk_lock_contains_exact_both_architecture_binary_hashes(self):
        lock = (DIRECTORY / "requirements-codex-linux.txt").read_text()
        for value in ("1dc7b8b21c27ce89b44000ab990ada18285b85233a6e4bb734859302c18f9561",
                      "29b55f02dec12a817a1ab882e187a34ddabadc5b8a55b6d04cfd0d22755a9a88",
                      "4fdc8b93a41521988916eeaa271173fcca7fa0803d62f87675aac8dcec1c8e29",
                      "0fc5be0abd4a407e200d844b404e33639a554e7bd0d448e7b9ae181be4789ac2"):
            self.assertIn("--hash=sha256:" + value, lock)

    def test_ci_audits_each_deployed_node_surface(self):
        import yaml

        root = DIRECTORY.parents[2]
        workflow = yaml.safe_load((root / ".github/workflows/validate.yml").read_text())
        steps = {step.get("working-directory"): step
                 for step in workflow["jobs"]["validate"]["steps"]}
        for directory in ("apps/control-center", "researcher/schemas/typescript",
                          "researcher/benchmarks/sdk-runner"):
            commands = steps[directory]["run"].splitlines()
            self.assertIn("npm audit --omit=dev", commands)
            self.assertTrue(any(command.startswith("npm ci --ignore-scripts")
                                for command in commands))
            self.assertLess(commands.index("npm audit --omit=dev"),
                            next(index for index, command in enumerate(commands)
                                 if command.startswith("npm run")))


if __name__ == "__main__":
    unittest.main()
