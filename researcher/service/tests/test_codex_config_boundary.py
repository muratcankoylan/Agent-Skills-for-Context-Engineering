"""Read-only host-layer closure and pre-SDK refusal. No provider or host writes."""
import io
import os
from pathlib import Path
import stat
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from researcher.service import codex_config_boundary as boundary
from researcher.service import codex_preflight as preflight
from researcher.service import codex_worker as worker
from researcher.service.tests.test_codex_worker import request, TOKEN


class ConfigBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.etc = self.root / "etc"
        self.etc.mkdir()

    def system_check(self):
        # Fixture lives under a user-owned temp ancestor, never mutate /etc.
        # Keep actual lstat/type/mode/iteration; only fixture ownership differs.
        original = Path.lstat
        def root_owned(path, *args, **kwargs):
            value = original(path, *args, **kwargs)
            return SimpleNamespace(st_mode=value.st_mode, st_uid=0,
                                   st_dev=value.st_dev, st_ino=value.st_ino)
        with patch.object(Path, "lstat", root_owned):
            # /tmp's sticky world-write mode is not a production trusted chain.
            real_check = boundary._trusted_directory
            def fixture_chain(path):
                if path in (self.etc, self.etc / "codex"):
                    real_check(path)
            with patch.object(boundary, "_trusted_directory", side_effect=fixture_chain):
                boundary._system_layer(self.etc)

    def test_absent_and_empty_system_namespace_are_read_only(self):
        self.system_check()
        self.assertFalse((self.etc / "codex").exists())
        target = self.etc / "codex"
        target.mkdir(mode=0o755)
        before = target.stat()
        self.system_check()
        after = target.stat()
        self.assertEqual((before.st_mode, before.st_mtime_ns), (after.st_mode, after.st_mtime_ns))
        self.assertEqual(list(target.iterdir()), [])

    def test_every_system_entry_refused_without_parsing_or_repair(self):
        target = self.etc / "codex"
        target.mkdir()
        for name in ("config.toml", "managed_config.toml", "requirements.toml", "unknown-future-layer"):
            with self.subTest(name=name):
                file = target / name
                file.write_bytes(b"private invalid config: must not read or log")
                before = file.stat()
                with self.assertRaises(boundary.ConfigBoundaryError):
                    self.system_check()
                self.assertEqual(before.st_mtime_ns, file.stat().st_mtime_ns)
                self.assertEqual(file.read_bytes(), b"private invalid config: must not read or log")
                file.unlink()
        (target / "hooks").mkdir()
        with self.assertRaises(boundary.ConfigBoundaryError):
            self.system_check()

    def test_symlink_file_and_dangling_namespace_refused(self):
        target = self.etc / "codex"
        for destination in (self.root, self.root / "missing"):
            target.symlink_to(destination, target_is_directory=True)
            with self.assertRaises(boundary.ConfigBoundaryError):
                self.system_check()
            target.unlink()
        target.write_bytes(b"not a directory")
        with self.assertRaises(boundary.ConfigBoundaryError):
            self.system_check()

    def test_untrusted_owner_write_permissions_and_nondirectory_fail(self):
        for mode, uid in ((stat.S_IFDIR | 0o755, 1000), (stat.S_IFDIR | 0o775, 0),
                          (stat.S_IFDIR | 0o777, 0), (stat.S_IFLNK | 0o777, 0),
                          (stat.S_IFREG | 0o644, 0)):
            with self.subTest(mode=mode, uid=uid), patch.object(Path, "lstat", return_value=SimpleNamespace(
                    st_mode=mode, st_uid=uid)), self.assertRaises(boundary.ConfigBoundaryError):
                boundary._trusted_directory(self.root)
        with patch.object(Path, "lstat", return_value=SimpleNamespace(st_mode=stat.S_IFDIR | 0o755, st_uid=0)):
            boundary._trusted_directory(self.root)

    def test_entire_resolved_ancestor_chain_is_checked(self):
        with patch.object(Path, "lstat", return_value=SimpleNamespace(st_uid=0)), \
                patch.object(Path, "resolve", return_value=Path("/private/etc")), \
                patch.object(boundary, "_trusted_directory", side_effect=[None, boundary.ConfigBoundaryError()]) as check:
            with self.assertRaises(boundary.ConfigBoundaryError):
                boundary._system_layer(Path("/etc"))
        self.assertEqual([call.args[0] for call in check.call_args_list], [Path("/private/etc"), Path("/private")])

    def test_os_inspection_errors_fail_closed_without_sensitive_message(self):
        for error in (PermissionError("private sentinel"), OSError("private sentinel"), RuntimeError("private sentinel")):
            with patch.object(boundary, "_system_layer", side_effect=error), self.assertRaises(boundary.ConfigBoundaryError) as caught:
                boundary.verify_config_boundary()
            self.assertEqual(str(caught.exception), "CODEX_CONFIG_BOUNDARY_UNVERIFIED")

    def test_unknown_platform_never_attempts_sdk_or_preferences(self):
        with patch.object(boundary.sys, "platform", "win32"), patch.object(boundary, "_system_layer") as system:
            with self.assertRaises(boundary.ConfigBoundaryError):
                boundary.verify_config_boundary()
            system.assert_not_called()

    def test_macos_policy_presence_and_inspection_failure_refuse(self):
        for response in (True, OSError("private native error")):
            with patch.object(boundary.sys, "platform", "darwin"), patch.object(boundary, "_system_layer"), \
                    patch.object(boundary, "_macos_preferences_present", side_effect=[response]):
                with self.assertRaises(boundary.ConfigBoundaryError):
                    boundary.verify_config_boundary()
        with patch.object(boundary.sys, "platform", "darwin"), patch.object(boundary, "_system_layer"), \
                patch.object(boundary, "_macos_preferences_present", return_value=False):
            boundary.verify_config_boundary()

    def test_macos_queries_both_keys_and_all_scopes_without_decoding_values(self):
        cf = SimpleNamespace(CFStringCreateWithCString=Mock(side_effect=[100, 101, 102]),
            CFRelease=Mock(), CFPreferencesCopyAppValue=Mock(return_value=None),
            CFPreferencesCopyValue=Mock(return_value=None))
        with patch.object(boundary.ctypes, "CDLL", return_value=cf), patch.object(boundary.ctypes, "c_void_p") as pointer:
            pointer.in_dll.side_effect = [SimpleNamespace(value=value) for value in (1, 2, 3, 4)]
            self.assertFalse(boundary._macos_preferences_present())
        self.assertEqual([c.args[1] for c in cf.CFStringCreateWithCString.call_args_list],
                         [b"com.openai.codex", b"config_toml_base64", b"requirements_toml_base64"])
        self.assertEqual(cf.CFPreferencesCopyAppValue.call_count, 2)
        self.assertEqual(cf.CFPreferencesCopyValue.call_count, 8)
        self.assertEqual([c.args[0] for c in cf.CFRelease.call_args_list], [102, 101, 100])

    def test_managed_value_presence_releases_value_and_refuses_even_wrong_type(self):
        cf = SimpleNamespace(CFStringCreateWithCString=Mock(side_effect=[100, 101]),
            CFRelease=Mock(), CFPreferencesCopyAppValue=Mock(return_value=777),
            CFPreferencesCopyValue=Mock())
        with patch.object(boundary.ctypes, "CDLL", return_value=cf), patch.object(boundary.ctypes, "c_void_p") as pointer:
            pointer.in_dll.side_effect = [SimpleNamespace(value=value) for value in (1, 2, 3, 4)]
            self.assertTrue(boundary._macos_preferences_present())
        cf.CFPreferencesCopyValue.assert_not_called()
        self.assertEqual([c.args[0] for c in cf.CFRelease.call_args_list], [777, 101, 100])

    def test_worker_refuses_before_child_spawn(self):
        with patch.object(worker, "verify_system_config", side_effect=boundary.ConfigBoundaryError()), \
                patch.object(worker.subprocess, "Popen") as spawn:
            with self.assertRaises(worker.WorkerError) as caught:
                worker.run_worker(request(), broker_url="http://127.0.0.1:1234/v1", broker_token=TOKEN,
                                  sdk_python=sys.executable, workspace=str(self.root))
        self.assertEqual(caught.exception.code, "CODEX_WORKER_CONFIG_BOUNDARY_UNVERIFIED")
        spawn.assert_not_called()

    def test_worker_child_rechecks_before_import_and_keeps_unknown_policy(self):
        packet = worker._json({"request": request(), "broker_url": "http://127.0.0.1:1234/v1",
                               "broker_token": TOKEN, "workspace": str(self.root)})
        with patch.object(worker, "verify_config_boundary", side_effect=boundary.ConfigBoundaryError()), \
                patch.object(worker.sys, "stdin", SimpleNamespace(buffer=io.BytesIO(packet))), \
                patch.object(worker, "_emit") as emit, patch.object(worker.importlib.metadata, "version") as version:
            worker._child()
        version.assert_not_called()
        result = emit.call_args.args[1]
        self.assertEqual((result["status"], result["error_code"]), ("unknown", "CODEX_WORKER_CONFIG_BOUNDARY_UNVERIFIED"))
        self.assertIsNone(result["thread_id"])
        self.assertIsNone(result["output_text"])

    def test_preflight_parent_and_child_refuse_before_execution(self):
        with patch.object(preflight, "verify_config_boundary", side_effect=boundary.ConfigBoundaryError()), \
                patch.object(preflight, "verify_system_config", side_effect=boundary.ConfigBoundaryError()), \
                patch.object(preflight, "_execute") as execute, patch.object(preflight.importlib.metadata, "version") as version:
            parent = preflight.run_preflight(sdk_python=sys.executable, workspace_parent=self.root, profile="tool_free")
            child = preflight._child("tool_free", str(self.root))
        execute.assert_not_called()
        version.assert_not_called()
        for result in (parent, child):
            self.assertEqual((result["status"], result["failure_code"]), ("blocked", "CONFIG_BOUNDARY_UNVERIFIED"))
            self.assertEqual(result["provider_calls"], 0)
            self.assertFalse(result["production_ready"])
            self.assertEqual(preflight._validate_result(result, "tool_free"), result)

    def test_parent_inspection_does_not_call_potentially_blocking_os_preferences(self):
        with patch.object(boundary.sys, "platform", "darwin"), patch.object(boundary, "_system_layer"), \
                patch.object(boundary, "_macos_preferences_present") as preferences:
            boundary.verify_system_config()
        preferences.assert_not_called()

    def test_campaign_implementation_identity_binds_boundary_source_bytes(self):
        from researcher.service import codex_campaign
        original = Path.read_bytes
        boundary_source = Path(boundary.__file__).resolve()
        def changed(path):
            content = original(path)
            return content + b"\n# fixture-only source mutation\n" if path.resolve() == boundary_source else content
        with patch("researcher.service.openai_campaign.implementation_digest", return_value="f" * 64):
            before = codex_campaign.implementation_digest()
            with patch.object(Path, "read_bytes", changed):
                after = codex_campaign.implementation_digest()
        self.assertNotEqual(before, after)


if __name__ == "__main__":
    unittest.main()
