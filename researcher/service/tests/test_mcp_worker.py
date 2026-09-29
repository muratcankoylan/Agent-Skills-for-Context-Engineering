"""Isolated MCP process policy, bounded pipes, and real SDK log-leak regression."""

from copy import deepcopy
import io
import logging
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
import unittest
from unittest.mock import patch

from researcher.scripts.schema_contract import canonicalize, parse_json_strict
from researcher.service import mcp_worker
from researcher.service.mcp_evidence import MCPEvidenceError, _normalize
from researcher.service.tests.test_mcp_evidence import receipt
from researcher.service.tests.test_mcp_sdk import PINNED_AVAILABLE
from researcher.service.tests.test_mcp_tools import registration


class MCPWorkerTests(unittest.TestCase):
    def setUp(self):
        self.config = registration()
        self.args = {"query": "context"}
        self.lane = _normalize(self.config, self.args, receipt(), None)

    def call(self, **kwargs):
        return mcp_worker.bounded_collect_mcp(self.config, self.args, **kwargs)

    def run_output(self, output, **kwargs):
        with patch.object(mcp_worker, "_run", return_value=canonicalize(output)) as run:
            result = self.call(**kwargs)
        return result, run

    def assert_error(self, code, call, *, ambiguous=True):
        with self.assertRaises(MCPEvidenceError) as raised:
            call()
        self.assertEqual(raised.exception.code, code)
        self.assertIs(raised.exception.ambiguous, ambiguous)
        return raised.exception

    def child_main(self, payload):
        stdin = io.TextIOWrapper(io.BytesIO(payload))
        stdout, stderr = io.StringIO(), io.StringIO()
        old_disable = logging.root.manager.disable
        try:
            with (
                patch.object(sys, "stdin", stdin),
                patch.object(sys, "stdout", stdout),
                patch.object(sys, "stderr", stderr),
            ):
                status = mcp_worker.main()
        finally:
            logging.disable(old_disable)
        return status, stdout.getvalue(), stderr.getvalue()

    def test_valid_result_is_revalidated_and_credential_only_in_stdin(self):
        token = "offline-explicit-credential"
        result, run = self.run_output({"result": self.lane}, credential=token)
        self.assertEqual(result, self.lane)
        payload, deadline = run.call_args.args
        self.assertEqual(parse_json_strict(payload.decode())["credential"], token)
        self.assertLessEqual(
            deadline - time.monotonic(), self.config["timeout_seconds"] + 5
        )
        self.assertNotIn(token, canonicalize(result).decode())
        run.assert_called_once()

    def test_counterfeit_child_result_is_unknown(self):
        for field, value in (
            ("authority", "accepted"),
            ("model_calls", False),
            ("output_sha256", "bad"),
        ):
            with self.subTest(field=field):
                lane = deepcopy(self.lane)
                lane[field] = value
                self.assert_error(
                    "MCP_WORKER_OUTPUT_INVALID",
                    lambda: self.run_output({"result": lane}),
                )

    def test_changed_text_digest_or_extra_evidence_rejected(self):
        for change in ("text", "digest", "extra"):
            with self.subTest(change=change):
                lane = deepcopy(self.lane)
                if change == "text":
                    lane["evidence"][0]["text"] = '{"text":"changed"}'
                elif change == "digest":
                    lane["evidence"][0]["sha256"] = "sha256:" + "0" * 64
                else:
                    lane["evidence"].append(deepcopy(lane["evidence"][0]))
                self.assert_error(
                    "MCP_WORKER_OUTPUT_INVALID",
                    lambda: self.run_output({"result": lane}),
                )

    def test_error_ambiguity_preserved(self):
        for attempted, unknown in ((False, False), (True, False), (True, True)):
            output = {
                "error": "TIMEOUT",
                "call_attempted": attempted,
                "ambiguous": unknown,
            }
            error = self.assert_error(
                "TIMEOUT", lambda: self.run_output(output), ambiguous=unknown
            )
            self.assertIs(error.call_attempted, attempted)

    def test_invalid_error_contract_cannot_clear_quarantine(self):
        for output in (
            {"error": "TIMEOUT", "ambiguous": 0, "call_attempted": True},
            {"error": "bad private detail", "ambiguous": False, "call_attempted": True},
            {"error": "TIMEOUT", "ambiguous": True, "call_attempted": False},
            {"error": "TIMEOUT", "ambiguous": False},
        ):
            with self.subTest(output=output):
                self.assert_error(
                    "MCP_WORKER_OUTPUT_INVALID", lambda: self.run_output(output)
                )

    def test_invalid_raw_child_output_is_not_exposed(self):
        token = "offline-credential-reflection"
        for output in (token.encode(), b"x" * (mcp_worker.MAX_OUTPUT_BYTES + 1)):
            with patch.object(mcp_worker, "_run", return_value=output):
                error = self.assert_error(
                    "MCP_WORKER_OUTPUT_INVALID", lambda: self.call(credential=token)
                )
            self.assertNotIn(token, "".join(traceback.format_exception(error)))

    def test_escaped_credential_reflection_in_child_output_rejected(self):
        token = 'offline-quoted-"-token'
        lane = deepcopy(self.lane)
        lane["evidence"][0]["text"] = canonicalize({"text": token}).decode()
        self.assert_error(
            "MCP_WORKER_OUTPUT_INVALID",
            lambda: self.run_output({"result": lane}, credential=token),
        )

    def test_bad_inputs_never_spawn_worker(self):
        with patch.object(mcp_worker, "_run") as run:
            self.assert_error(
                "INVALID_CREDENTIAL",
                lambda: self.call(credential="short"),
                ambiguous=False,
            )
            self.config["url"] = "https://127.0.0.1/mcp"
            self.assert_error("UNSAFE_ENDPOINT", self.call, ambiguous=False)
        run.assert_not_called()

    def test_worker_command_environment_and_stderr_are_isolated(self):
        real = subprocess.Popen
        with patch.object(mcp_worker.subprocess, "Popen", wraps=real) as spawned:
            output = mcp_worker._run(b"{}", time.monotonic() + 5)
        self.assertEqual(
            parse_json_strict(output.decode())["error"], "INVALID_MCP_READ"
        )
        command = spawned.call_args.args[0]
        self.assertEqual(
            command, [sys.executable, "-B", "-m", "researcher.service.mcp_worker"]
        )
        kwargs = spawned.call_args.kwargs
        self.assertEqual(set(kwargs["env"]), {"PATH", "PYTHONPATH", "PYTHONUTF8"})
        self.assertEqual(kwargs["env"]["PATH"], os.defpath)
        self.assertEqual(kwargs["stderr"], subprocess.DEVNULL)
        self.assertEqual(kwargs["cwd"], Path(mcp_worker.__file__).resolve().parents[2])

    def test_start_failure_is_known_and_sanitized(self):
        with patch.object(
            mcp_worker.subprocess,
            "Popen",
            side_effect=OSError("private startup detail"),
        ):
            error = self.assert_error(
                "MCP_WORKER_START_FAILED",
                lambda: mcp_worker._run(b"{}", time.monotonic() + 5),
                ambiguous=False,
            )
        self.assertNotIn(
            "private startup detail", "".join(traceback.format_exception(error))
        )

    def process_exchange(self, code, *, timeout=2):
        process = subprocess.Popen(
            [sys.executable, "-B", "-c", code],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        try:
            return mcp_worker._exchange(process, b"{}", time.monotonic() + timeout)
        finally:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=2)
            process.stdin.close()
            process.stdout.close()

    def test_pipe_output_is_bounded_while_reading(self):
        self.assert_error(
            "MCP_WORKER_OUTPUT_LIMIT",
            lambda: self.process_exchange(
                "import sys;sys.stdout.buffer.write(b'x'*300000);sys.stdout.flush()"
            ),
        )

    def test_stalled_child_has_unknown_absolute_timeout(self):
        self.assert_error(
            "MCP_WALL_TIMEOUT",
            lambda: self.process_exchange("import time;time.sleep(5)", timeout=0.05),
        )

    def test_pipe_stdin_and_stdout_exchange_completes(self):
        output = self.process_exchange(
            "import sys;sys.stdout.buffer.write(sys.stdin.buffer.read())"
        )
        self.assertEqual(output, b"{}")

    def test_child_exit_failure_is_unknown(self):
        self.assert_error(
            "MCP_WORKER_FAILED", lambda: self.process_exchange("raise SystemExit(2)")
        )

    def test_child_disables_logging_and_discards_incidental_output(self):
        token = "offline-print-and-log-token"
        request = canonicalize(
            {"registration": self.config, "arguments": self.args, "credential": token}
        )

        def noisy(*args, **kwargs):
            logging.getLogger("mcp").error(token)
            print(token)
            print(token, file=sys.stderr)
            return self.lane

        with patch.object(mcp_worker, "collect_mcp", side_effect=noisy):
            status, stdout, stderr = self.child_main(request)
        self.assertEqual(status, 0)
        self.assertEqual(parse_json_strict(stdout)["result"], self.lane)
        self.assertEqual(stderr, "")
        self.assertNotIn(token, stdout)

    def test_child_unexpected_exception_is_sanitized(self):
        payload = canonicalize(
            {"registration": self.config, "arguments": self.args, "credential": None}
        )
        with patch.object(
            mcp_worker, "collect_mcp", side_effect=RuntimeError("private detail")
        ):
            _, stdout, stderr = self.child_main(payload)
        self.assertEqual(
            parse_json_strict(stdout),
            {"error": "MCP_WORKER_FAILED", "ambiguous": True, "call_attempted": True},
        )
        self.assertNotIn("private detail", stdout + stderr)

    @unittest.skipUnless(PINNED_AVAILABLE, "requires optional pinned MCP SDK")
    def test_actual_sdk_malformed_initialize_cannot_log_reflected_credential(self):
        from researcher.service.tests.test_mcp_sdk import ActualMCPTests

        case = ActualMCPTests(
            "test_actual_sdk_signatures_and_complete_protocol_exchange"
        )
        case.setUp()
        # We borrow transport fixtures, not the IsolatedAsyncioTestCase runner.
        # Register cleanup on this running TestCase rather than an unstarted one.
        for patched in case.patches:
            self.addCleanup(patched.stop)
        token = "OFFLINE-TEST-CREDENTIAL-ONLY"
        case.config["timeout_seconds"] = 1
        case.invalid_json = ('{"jsonrpc":"' + token + '"}').encode()
        captured = []

        class Sink(logging.Handler):
            def emit(self, record):
                captured.append(self.format(record))

        sink = Sink()
        logger = logging.getLogger("mcp.client.streamable_http")
        logger.addHandler(sink)
        self.addCleanup(logger.removeHandler, sink)
        payload = canonicalize(
            {"registration": case.config, "arguments": self.args, "credential": token}
        )
        _, stdout, stderr = self.child_main(payload)
        self.assertEqual(parse_json_strict(stdout)["error"], "TIMEOUT")
        self.assertEqual(captured, [])
        self.assertNotIn(token, stdout + stderr)
        self.assertEqual(len(case.requests), 1)


if __name__ == "__main__":
    unittest.main()
