"""Credential-free preflight contracts. Native SDK measurements are explicit CLI runs."""
import contextlib
import io
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import time
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

from researcher.service import codex_preflight as preflight


def completed(profile="native_tools"):
    value = preflight._result(profile)
    for key in preflight.CHECKS if profile == "native_tools" else preflight.CHECKS[:3]:
        value["checks"][key] = "passed"
    value.update(status="passed", sdk_version=preflight.VERSION, runtime_version=preflight.VERSION,
                 native_tool_execution_verified=profile == "native_tools")
    return value


class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="preflight-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.root.chmod(0o700)

    def run_probe(self, **kwargs):
        return preflight.run_preflight(sdk_python=sys.executable, workspace_parent=self.root, **kwargs)

    def test_tool_free_scope_cannot_claim_tools_or_actual_message_execution(self):
        with patch.object(preflight, "_execute", return_value=preflight._json(completed("tool_free"))):
            result = self.run_probe(profile="tool_free")
        self.assertEqual(result["status"], "passed")
        self.assertFalse(result["native_tool_execution_verified"])
        self.assertFalse(result["tool_free_message_execution_verified"])
        self.assertFalse(result["host_file_containment_verified"])
        self.assertFalse(result["production_ready"])
        self.assertEqual(result["provider_calls"], 0)

    def test_native_result_requires_every_check_and_observed_runtime_identity(self):
        for mutate in (lambda v: v["checks"].update(native_noop="not_run"),
                       lambda v: v.update(runtime_version=None),
                       lambda v: v.update(native_tool_execution_verified=False),
                       lambda v: v.update(provider_calls=False),
                       lambda v: v.update(unknown="private")):
            value = completed()
            mutate(value)
            with self.subTest(value=value), self.assertRaises(preflight.PreflightError):
                preflight._validate_result(value, "native_tools")

    def test_tool_free_cannot_smuggle_native_result(self):
        value = completed("tool_free")
        value["checks"]["native_noop"] = "passed"
        with self.assertRaises(preflight.PreflightError):
            preflight._validate_result(value, "tool_free")

    def test_exact_clean_child_environment_and_no_ambient_credentials(self):
        def execute(command, env, cwd, timeout):
            self.assertEqual(set(env), {"PATH", "HOME", "CODEX_HOME", "TMPDIR", "LANG", "TZ"})
            self.assertNotIn("private-credential", repr(env))
            self.assertEqual(command[1:3], ["-I", "-B"])
            self.assertEqual(command[-3:-1], ["--child", "native_tools"])
            fixture = Path(command[-1])
            self.assertEqual(cwd, fixture / "workspace")
            for path in fixture.iterdir():
                self.assertEqual(path.stat().st_mode & 0o777, 0o700)
            self.assertEqual(timeout, 30)
            return preflight._json(completed())
        with patch.dict(os.environ, {"OPENAI_API_KEY": "private-credential", "PYTHONPATH": "/untrusted"}), \
                patch.object(preflight, "_execute", side_effect=execute):
            self.assertEqual(self.run_probe()["status"], "passed")
        self.assertEqual(list(self.root.iterdir()), [])

    def test_invalid_profile_timeout_and_interpreter_do_not_spawn(self):
        with patch.object(preflight, "_execute") as execute:
            for args in ({"profile": "full_access"}, {"timeout_seconds": True},
                         {"timeout_seconds": 0}, {"timeout_seconds": 121}):
                with self.subTest(args=args), self.assertRaises(preflight.PreflightError):
                    self.run_probe(**args)
            with self.assertRaises(preflight.PreflightError):
                preflight.run_preflight(sdk_python="python", workspace_parent=self.root)
            execute.assert_not_called()

    def test_missing_nonprivate_alias_or_broad_parent_is_rejected_without_repair(self):
        alias = self.root / "alias"
        alias.symlink_to(self.root, target_is_directory=True)
        for parent in (self.root / "missing", alias, Path("/")):
            with self.subTest(parent=parent), self.assertRaises(preflight.PreflightError):
                preflight.run_preflight(sdk_python=sys.executable, workspace_parent=parent)
        self.assertFalse((self.root / "missing").exists())
        self.root.chmod(0o755)
        with self.assertRaises(preflight.PreflightError):
            self.run_probe()
        self.assertEqual(self.root.stat().st_mode & 0o777, 0o755)

    def test_vanished_child_and_timeout_have_safe_bounded_results(self):
        for error, status, code in ((OSError("secret error"), "blocked", "CHILD_FAILED"),
                                   (preflight.PreflightError("TIMEOUT"), "unknown", "TIMEOUT")):
            with patch.object(preflight, "_execute", side_effect=error):
                value = self.run_probe()
            self.assertEqual((value["status"], value["failure_code"]), (status, code))
            self.assertNotIn("secret", json.dumps(value))
            self.assertEqual(list(self.root.iterdir()), [])

    def test_duplicate_nonfinite_and_raw_output_fail_closed(self):
        for raw in (b'{"schema":1,"schema":2}', b'{"v":NaN}', b'private error', b'[]'):
            with patch.object(preflight, "_execute", return_value=raw):
                value = self.run_probe()
            self.assertEqual(value["failure_code"], "INVALID_RESULT")
            self.assertNotIn("private error", json.dumps(value))

    def test_missing_sdk_has_no_runtime_or_native_claim(self):
        with patch.object(preflight.importlib.metadata, "version", side_effect=preflight.importlib.metadata.PackageNotFoundError):
            value = preflight._child("native_tools", str(self.root))
        self.assertEqual(value["failure_code"], "SDK_MISSING")
        self.assertEqual(value["checks"]["dependencies"], "failed")
        self.assertIsNone(value["runtime_version"])

    def test_wrong_sdk_version_fails_before_client_import(self):
        with patch.object(preflight.importlib.metadata, "version", return_value="0.0.1"):
            value = preflight._child("tool_free", str(self.root))
        self.assertEqual(value["failure_code"], "VERSION_MISMATCH")

    def test_runtime_identity_accepts_platform_suffix_not_different_version(self):
        preflight._runtime_identity(SimpleNamespace(serverInfo=SimpleNamespace(version="0.159.0 (Mac OS)")))
        preflight._runtime_identity(SimpleNamespace(serverInfo=None, userAgent="codex/0.159.0 (Mac OS)"))
        for value in (None, "", "0.159.01", "0.159.0-private", 159):
            with self.subTest(value=value), self.assertRaises(preflight.PreflightError):
                preflight._runtime_identity(SimpleNamespace(serverInfo=SimpleNamespace(version=value)))

    def test_tool_free_child_initializes_only_without_thread_turn_or_provider_method(self):
        calls = []
        fake = SimpleNamespace(start=lambda: calls.append("start"),
            initialize=lambda: calls.append("initialize") or SimpleNamespace(serverInfo=None, userAgent="codex/0.159.0"),
            close=lambda: calls.append("close"))
        client_module = ModuleType("openai_codex.client")
        client_module.CodexConfig = lambda **values: SimpleNamespace(**values)
        def client(config, approval_handler):
            self.assertFalse(config.experimental_api)
            self.assertIn('approval_policy="never"', config.config_overrides)
            self.assertIn('model_providers.research_broker.base_url="http://127.0.0.1:9/v1"', config.config_overrides)
            self.assertEqual(approval_handler("item/fileChange/requestApproval", {}), {"decision": "decline"})
            return fake
        client_module.CodexClient = client
        types_module = ModuleType("openai_codex.generated.v2_all")
        types_module.CommandExecResponse = object
        with patch.dict(sys.modules, {"openai_codex.client": client_module, "openai_codex.generated.v2_all": types_module}), \
                patch.object(preflight.importlib.metadata, "version", return_value=preflight.VERSION):
            value = preflight._child("tool_free", str(self.root))
        self.assertEqual(value["status"], "passed")
        self.assertEqual(calls, ["start", "initialize", "close"])

    def test_cli_failure_is_json_only_and_nonzero(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = preflight.main(["--sdk-python", "python", "--workspace-parent", str(self.root),
                                     "--profile", "native_tools"])
        self.assertEqual(status, 1)
        self.assertEqual(json.loads(output.getvalue())["failure_code"], "INVALID_INPUT")

    def test_executor_caps_diagnostic_growth_and_reaps_child(self):
        with self.assertRaises(preflight.PreflightError) as caught:
            preflight._execute([sys.executable, "-I", "-c", "print('x'*20000)"],
                               {"PATH": "/usr/bin:/bin"}, self.root, 2)
        self.assertEqual(caught.exception.code, "OUTPUT_LIMIT")

    def test_executor_deadline_covers_no_output_child(self):
        start = time.monotonic()
        with self.assertRaises(preflight.PreflightError) as caught:
            preflight._execute([sys.executable, "-I", "-c", "import time;time.sleep(10)"],
                               {"PATH": "/usr/bin:/bin"}, self.root, 0.1)
        self.assertEqual(caught.exception.code, "TIMEOUT")
        self.assertLess(time.monotonic() - start, 3)

    def test_executor_deadline_reaps_pipe_holding_descendant(self):
        heartbeat = self.root / "heartbeat"
        child = ("import pathlib,time\n"
                 f"p=pathlib.Path({str(heartbeat)!r})\n"
                 "for i in range(200):\n p.write_text(str(i));time.sleep(0.01)\n")
        code = ("import subprocess,sys,pathlib;"
                f"subprocess.Popen([sys.executable,'-I','-c',{child!r}])")
        with self.assertRaises(preflight.PreflightError) as caught:
            preflight._execute([sys.executable, "-I", "-c", code], {"PATH": "/usr/bin:/bin"}, self.root, 0.3)
        self.assertEqual(caught.exception.code, "TIMEOUT")
        before = heartbeat.read_bytes()
        time.sleep(0.1)
        self.assertEqual(heartbeat.read_bytes(), before)


class NativeContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="native-contract-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.workspace = self.root / "workspace"
        self.sibling = self.root / "sibling"
        self.workspace.mkdir()
        self.sibling.mkdir()
        self.checks = dict.fromkeys(preflight.CHECKS, "not_run")
        self.calls = []

    def client(self, mode="correct"):
        def request(method, params, response_model):
            self.calls.append((method, params))
            self.assertEqual(method, "command/exec")
            self.assertEqual(params["timeoutMs"], 5000)
            self.assertEqual(params["outputBytesCap"], 8192)
            self.assertFalse(params["sandboxPolicy"]["networkAccess"])
            self.assertNotIn("disableTimeout", params)
            self.assertNotIn("disableOutputCap", params)
            number = len(self.calls)
            if mode == "namespace":
                return SimpleNamespace(exit_code=1, stdout="", stderr="bwrap: No permissions to create a new namespace private")
            if mode == "generic_failure":
                return SimpleNamespace(exit_code=1, stdout="", stderr="private failure")
            if mode == "malformed":
                return SimpleNamespace(exit_code=True, stdout="NATIVE_OK\n", stderr="")
            if number == 1:
                return SimpleNamespace(exit_code=0, stdout="NATIVE_OK\n", stderr="")
            target = Path(params["command"][-1])
            allowed = number == 3
            if mode == "readonly_escape" and number == 2 or mode == "sibling_escape" and number == 4:
                allowed = True
            if allowed and mode != "false_write_ack":
                target.write_bytes(b"codex-preflight\n")
            return SimpleNamespace(exit_code=0, stdout="WRITE_OK\n" if allowed else "WRITE_DENIED\n", stderr="")
        return SimpleNamespace(request=request)

    def test_fixed_commands_validate_success_denials_and_exact_file_bytes(self):
        preflight._native_checks(self.client(), self.workspace, self.sibling, object, self.checks)
        self.assertTrue(all(self.checks[key] == "passed" for key in preflight.CHECKS[3:]))
        self.assertEqual(len(self.calls), 4)
        self.assertEqual(list(self.sibling.iterdir()), [])
        self.assertEqual(self.calls[2][1]["sandboxPolicy"], {
            "type": "workspaceWrite", "networkAccess": False, "writableRoots": [],
            "excludeSlashTmp": True, "excludeTmpdirEnvVar": True})

    def test_namespace_failure_is_distinct_and_never_relaxes_policy(self):
        with self.assertRaises(preflight.PreflightError) as caught:
            preflight._native_checks(self.client("namespace"), self.workspace, self.sibling, object, self.checks)
        self.assertEqual(caught.exception.code, "NATIVE_NAMESPACE_DENIED")
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.checks["native_noop"], "failed")

    def test_generic_failure_or_malformed_response_cannot_count_as_denial(self):
        for mode, code in (("generic_failure", "NATIVE_SANDBOX_UNAVAILABLE"), ("malformed", "INVALID_COMMAND_RESULT")):
            self.calls.clear()
            with self.subTest(mode=mode), self.assertRaises(preflight.PreflightError) as caught:
                preflight._native_checks(self.client(mode), self.workspace, self.sibling, object, self.checks)
            self.assertEqual(caught.exception.code, code)

    def test_read_only_escape_fails_and_stops(self):
        with self.assertRaises(preflight.PreflightError) as caught:
            preflight._native_checks(self.client("readonly_escape"), self.workspace, self.sibling, object, self.checks)
        self.assertEqual(caught.exception.code, "READ_ONLY_WRITE_ALLOWED")
        self.assertEqual(len(self.calls), 2)

    def test_workspace_success_needs_actual_file_not_just_ack(self):
        with self.assertRaises(preflight.PreflightError) as caught:
            preflight._native_checks(self.client("false_write_ack"), self.workspace, self.sibling, object, self.checks)
        self.assertEqual(caught.exception.code, "WORKSPACE_WRITE_FAILED")

    def test_sibling_write_escape_is_not_accepted(self):
        with self.assertRaises(preflight.PreflightError) as caught:
            preflight._native_checks(self.client("sibling_escape"), self.workspace, self.sibling, object, self.checks)
        self.assertEqual(caught.exception.code, "OUTSIDE_WRITE_ALLOWED")


class LinuxVerifierTests(unittest.TestCase):
    def setUp(self):
        path = Path(preflight.__file__).parent / "deploy/verify_codex_runtime.py"
        spec = importlib.util.spec_from_file_location("codex_linux_verifier_fixture", path)
        self.verifier = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.verifier)

    def test_other_architecture_or_python_abi_never_claims_lock_compatibility(self):
        for machine, version in (("ppc64le", (3, 12)), ("aarch64", (3, 11))):
            with patch.object(self.verifier.sys, "platform", "linux"), \
                    patch.object(self.verifier.platform, "machine", return_value=machine), \
                    patch.object(self.verifier.sys, "version_info", version), \
                    patch.object(self.verifier, "run_preflight") as probe:
                value = self.verifier.verify(workspace_parent="unused", profile="native_tools")
            probe.assert_not_called()
            self.assertEqual(value["failure_code"], "UNSUPPORTED_LOCK_TARGET")

    def test_dependency_drift_never_runs_runtime(self):
        with patch.object(self.verifier.sys, "platform", "linux"), \
                patch.object(self.verifier.platform, "machine", return_value="aarch64"), \
                patch.object(self.verifier.sys, "version_info", (3, 12)), \
                patch.object(self.verifier.importlib.metadata, "version", return_value="wrong"), \
                patch.object(self.verifier, "run_preflight") as probe:
            value = self.verifier.verify(workspace_parent="unused", profile="native_tools")
        probe.assert_not_called()
        self.assertEqual(value["failure_code"], "DEPENDENCY_MISMATCH")

    def test_native_failure_is_preserved_not_skipped_or_relaxed(self):
        failed = preflight._result("native_tools")
        failed["failure_code"] = "NATIVE_NAMESPACE_DENIED"
        with patch.object(self.verifier.sys, "platform", "linux"), \
                patch.object(self.verifier.platform, "machine", return_value="aarch64"), \
                patch.object(self.verifier.sys, "version_info", (3, 12)), \
                patch.object(self.verifier.importlib.metadata, "version", side_effect=self.verifier.DEPENDENCIES.__getitem__), \
                patch.object(self.verifier, "run_preflight", return_value=failed) as probe:
            value = self.verifier.verify(workspace_parent="unused", profile="native_tools")
        probe.assert_called_once_with(sdk_python=sys.executable, workspace_parent="unused", profile="native_tools")
        self.assertEqual(value["status"], "blocked")
        self.assertEqual(value["failure_code"], "NATIVE_NAMESPACE_DENIED")
        self.assertFalse(value["production_ready"])
        self.assertEqual(set(value["source_sha256"]),
                         {"codex_worker.py", "codex_preflight.py", "codex_config_boundary.py"})

    def test_hash_lock_closes_all_eight_dependencies(self):
        path = Path(preflight.__file__).parent / "deploy/requirements-codex-linux-aarch64.txt"
        rows = [line for line in path.read_text().splitlines() if line and not line.startswith("#")]
        self.assertEqual(len(rows), 8)
        self.assertEqual({row.split("==")[0] for row in rows}, set(self.verifier.DEPENDENCIES))
        for row in rows:
            self.assertRegex(row, r"^[a-z-]+==[0-9.]+ --hash=sha256:[0-9a-f]{64}$")

    def test_tool_free_test_gate_rejects_skips_empty_groups_and_boolean_counts(self):
        self.assertIn("test_sdk_learning.SDKLearningTests", self.verifier.TEST_GROUPS)
        count = len(self.verifier.TEST_GROUPS)
        good = {"groups": dict.fromkeys(self.verifier.TEST_GROUPS, 1), "planned": count, "executed": count,
                "passed": True, "source_digest": "sha256:" + "a" * 64, "source_unchanged": True,
                **dict.fromkeys(self.verifier.OUTCOMES, 0)}
        self.verifier._validate_tests(good)
        for mutation in ({"skipped": 1}, {"executed": True}, {"source_unchanged": False},
                         {"groups": {}}, {"executed": 2}, {"expected_failures": 1}):
            with self.subTest(mutation=mutation), self.assertRaises(preflight.PreflightError):
                self.verifier._validate_tests({**good, **mutation})
        self.assertFalse(self.verifier._validate_tests({**good, "skipped": 1, "passed": False})["passed"])

    def test_tool_free_gate_cannot_change_native_failure_into_success(self):
        value = self.verifier.verify(workspace_parent="unused", profile="native_tools", service_python=sys.executable)
        self.assertEqual(value["failure_code"], "TOOL_FREE_PROFILE_REQUIRED")

    def tool_free_failure(self, error):
        with patch.object(self.verifier.sys, "platform", "linux"), \
                patch.object(self.verifier.platform, "machine", return_value="aarch64"), \
                patch.object(self.verifier.sys, "version_info", (3, 12)), \
                patch.object(self.verifier.importlib.metadata, "version", side_effect=self.verifier.DEPENDENCIES.__getitem__), \
                patch.object(self.verifier, "run_preflight", return_value=completed("tool_free")), \
                patch.object(self.verifier, "run_tool_free_tests", side_effect=error):
            return self.verifier.verify(workspace_parent="unused", profile="tool_free", service_python=sys.executable)

    def test_closed_child_diagnostics_preserve_fail_closed_aggregate(self):
        for code in ("TIMEOUT", "OUTPUT_LIMIT", "INVALID_RESULT", "CHILD_FAILED"):
            with self.subTest(code=code):
                value = self.tool_free_failure(preflight.PreflightError(code))
                self.assertEqual(value["schema"], "codex-linux-prerequisite/v3")
                self.assertEqual((value["status"], value["failure_code"], value["tool_free_diagnostic_code"]),
                                 ("blocked", "TOOL_FREE_TESTS_UNAVAILABLE", code))
                self.assertIsNone(value["tool_free_tests"])
                self.assertFalse(value["production_ready"])

    def test_unknown_codes_and_raw_errors_never_reach_receipts(self):
        for error in (preflight.PreflightError("/private/sentinel stderr"),
                      preflight.PreflightError(["private-sentinel"]),
                      preflight.PreflightError(True), OSError("private-sentinel stderr"),
                      RuntimeError("private-sentinel stdout")):
            with self.subTest(kind=type(error).__name__):
                value = self.tool_free_failure(error)
                self.assertEqual(value["failure_code"], "TOOL_FREE_TESTS_UNAVAILABLE")
                self.assertIsNone(value["tool_free_diagnostic_code"])
                self.assertNotIn("sentinel", json.dumps(value))

    def test_throwing_error_code_cannot_replace_safe_failure(self):
        class BrokenCode(preflight.PreflightError):
            def __getattribute__(self, name):
                if name == "code":
                    raise RuntimeError("private-sentinel")
                return super().__getattribute__(name)
        value = self.tool_free_failure(BrokenCode("TIMEOUT"))
        self.assertEqual(value["failure_code"], "TOOL_FREE_TESTS_UNAVAILABLE")
        self.assertIsNone(value["tool_free_diagnostic_code"])
        self.assertNotIn("sentinel", json.dumps(value))

    def test_child_deadline_stays_300_seconds_and_no_skips_are_forgiven(self):
        count = len(self.verifier.TEST_GROUPS)
        value = {"groups": dict.fromkeys(self.verifier.TEST_GROUPS, 1), "planned": count, "executed": count,
                 "passed": False, "source_digest": "sha256:" + "a" * 64, "source_unchanged": True,
                 **dict.fromkeys(self.verifier.OUTCOMES, 0), "skipped": 1}
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(self.verifier, "_execute", return_value=json.dumps(value).encode()) as execute:
            result = self.verifier.run_tool_free_tests(sys.executable, Path(directory).resolve())
        self.assertEqual(execute.call_args.args[-1], 300)
        self.assertFalse(result["passed"])
        self.assertEqual(result["skipped"], 1)


if __name__ == "__main__":
    unittest.main()
