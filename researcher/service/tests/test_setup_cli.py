"""No-network CLI setup and private config publication with synthetic keys."""

from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path
import stat
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from researcher.service.__main__ import main
from researcher.service.contracts import ServiceError
from researcher.service.retrieval_setup import build_config, write_config
from researcher.service.tests.test_retrieval_setup import values

ROOT = Path(__file__).resolve().parents[3]
TOKEN = "synthetic-never-a-real-key-123456789"


class SetupCLITests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name).resolve()
        self.env = self.directory / "private.env"
        self.config = self.directory / "service.json"
        self.env.write_text(
            "\n".join(
                f"{k}={json.dumps(v)}" for k, v in values(OPENAI_API_KEY=TOKEN).items()
            )
            + "\n"
        )
        self.env.chmod(0o600)

    def command(self, args, *, forbid_state=True):
        stdout, stderr = io.StringIO(), io.StringIO()
        with (
            redirect_stdout(stdout),
            redirect_stderr(stderr),
            patch(
                "socket.socket.connect", side_effect=AssertionError("network forbidden")
            ),
            patch.dict(os.environ, {"OPENAI_API_KEY": "unrelated-ambient-key"}),
        ):
            before = dict(os.environ)
            if forbid_state:
                with patch(
                    "researcher.service.__main__.Store",
                    side_effect=AssertionError("state forbidden"),
                ):
                    result = main(args)
            else:
                result = main(args)
            self.assertEqual(dict(os.environ), before)
        self.assertNotIn(TOKEN, stdout.getvalue() + stderr.getvalue())
        self.assertNotIn("unrelated-ambient-key", stdout.getvalue() + stderr.getvalue())
        return result, stdout.getvalue(), stderr.getvalue()

    def test_preflight_needs_no_state_and_never_authenticates(self):
        code, output, _ = self.command(["preflight", "--env-file", str(self.env)])
        report = json.loads(output)
        self.assertEqual(code, 0)
        self.assertTrue(report["local_ready"])
        self.assertFalse(report["source_authentication_verified"])
        self.assertFalse(report["network_checked"])
        self.assertFalse(report["production_ready"])
        self.assertEqual(report["credentials"]["OPENAI_API_KEY"], "set")

    def test_configure_writes_only_a_secret_free_private_config(self):
        code, output, _ = self.command(
            ["configure", "--env-file", str(self.env), "--output", str(self.config)]
        )
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(output)["config_written"])
        self.assertNotIn(TOKEN, self.config.read_text())
        self.assertEqual(stat.S_IMODE(self.config.stat().st_mode), 0o600)
        self.assertEqual(self.config.stat().st_nlink, 1)
        self.assertEqual(
            set(p.name for p in self.directory.iterdir()),
            {"private.env", "service.json"},
        )
        code, output, _ = self.command(
            ["preflight", "--env-file", str(self.env), "--config", str(self.config)]
        )
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(output)["local_ready"])

    def test_template_passes_when_copied_to_private_file(self):
        self.env.write_bytes((ROOT / ".env.example").read_bytes())
        code, _, _ = self.command(["preflight", "--env-file", str(self.env)])
        self.assertEqual(code, 0)

    def test_configure_missing_settings_reports_no_write(self):
        self.env.write_text("OPENAI_API_KEY=" + TOKEN + "\n")
        code, output, _ = self.command(
            ["configure", "--env-file", str(self.env), "--output", str(self.config)]
        )
        self.assertEqual(code, 1)
        self.assertFalse(json.loads(output)["config_written"])
        self.assertIn(
            "RESEARCH_RETRIEVAL_SOURCES", json.loads(output)["missing_variables"]
        )
        self.assertFalse(self.config.exists())

    def test_existing_output_is_untouched(self):
        self.config.write_text("keep-existing-config")
        code, _, error = self.command(
            ["configure", "--env-file", str(self.env), "--output", str(self.config)]
        )
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(error)["error"], "CONFIG_OUTPUT_EXISTS")
        self.assertEqual(self.config.read_text(), "keep-existing-config")
        self.assertFalse(list(self.directory.glob(".retrieval-config-*")))

    def test_missing_state_and_setup_activation_flags_fail_before_state(self):
        for args in (
            ["status"],
            ["preflight"],
            ["preflight", "--env-file", str(self.env), "--live"],
            [
                "preflight",
                "--env-file",
                str(self.env),
                "--state",
                str(self.directory / "state"),
            ],
            ["configure", "--env-file", str(self.env)],
            ["preflight", "--env-file", str(self.env), "--output", str(self.config)],
        ):
            self.assertEqual(self.command(args)[0], 1)
        self.assertFalse((self.directory / "state").exists())

    def test_env_parse_error_is_sanitized_before_any_state(self):
        self.env.write_text("OPENAI_API_KEY=$(" + TOKEN + ")\n")
        self.assertEqual(self.command(["preflight", "--env-file", str(self.env)])[0], 1)

    def test_fifo_config_rejected_before_opening_or_initializing_state(self):
        os.mkfifo(self.config)
        for command, arguments in (
            ("preflight", ["--env-file", str(self.env)]),
            ("init", ["--state", str(self.directory / "new-state")]),
        ):
            code, _, error = self.command([command, "--config", str(self.config), *arguments])
            self.assertEqual(code, 1)
            self.assertEqual(json.loads(error)["error"], "CONFIG_FILE_UNSAFE")
        self.assertFalse((self.directory / "new-state").exists())

    def test_env_file_is_authoritative_for_worker_not_global(self):
        config = build_config(values())
        self.config.write_text(json.dumps(config))
        self.env.write_text("X_BEARER_TOKEN=\nOPENAI_API_KEY=" + TOKEN + "\n")
        with (
            patch("researcher.service.__main__.Store") as store,
            patch("researcher.service.__main__.Workflow") as workflow,
        ):
            workflow.return_value.drain.return_value = []
            code, _, _ = self.command(
                [
                    "work",
                    "--config",
                    str(self.config),
                    "--state",
                    str(self.directory / "state"),
                    "--env-file",
                    str(self.env),
                ],
                forbid_state=False,
            )
            self.assertEqual(code, 0)
            store.assert_called_once()
            reader = workflow.call_args.kwargs["credential"]
            # A free-only worker does not receive the otherwise-present model key.
            for name in ("OPENAI_API_KEY", "X_BEARER_TOKEN"):
                with self.assertRaises(ServiceError) as error:
                    reader(name)
                self.assertEqual(error.exception.code, "ENV_CREDENTIAL_NOT_ALLOWED")

    def test_output_rejects_relative_symlink_fifo_directory_and_aliases(self):
        config = build_config(values())
        with self.assertRaises(ServiceError):
            write_config(Path("relative.json"), config)
        target = self.directory / "existing"
        target.write_text("unchanged")
        leaf = self.directory / "alias.json"
        leaf.symlink_to(target)
        folder = self.directory / "alias-folder"
        folder.symlink_to(self.directory, target_is_directory=True)
        fifo = self.directory / "fifo"
        os.mkfifo(fifo)
        for path in (leaf, folder / "output.json", fifo, self.directory):
            with self.subTest(path=path.name), self.assertRaises(ServiceError):
                write_config(path, config)
        self.assertEqual(target.read_text(), "unchanged")
        self.assertFalse((self.directory / "output.json").exists())
        self.assertFalse(list(self.directory.glob(".retrieval-config-*")))

    def test_temporary_name_collision_does_not_remove_an_existing_file(self):
        collision = self.directory / ".retrieval-config-collision"
        collision.write_text("must remain")
        with patch(
            "researcher.service.retrieval_setup.secrets.token_hex",
            return_value="collision",
        ):
            with self.assertRaises(ServiceError):
                write_config(self.config, build_config(values()))
        self.assertEqual(collision.read_text(), "must remain")
        self.assertFalse(self.config.exists())


if __name__ == "__main__":
    unittest.main()
