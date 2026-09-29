"""Offline delivery/CLI contracts. No vendor credentials or network."""
from contextlib import redirect_stdout, redirect_stderr
import io
import json
import os
from pathlib import Path
import sqlite3
import stat
import tempfile
import unittest
from unittest.mock import Mock, patch

from researcher.service.contracts import ServiceError
from researcher.service.trace_cli import export_pending, main
from researcher.service.trace_events import ENDPOINT as EVENT_ENDPOINT
from researcher.service.tracing import TraceJournal, Tracer


def snapshot(root):
    result = {}
    for path in (root, *sorted(root.rglob("*"))):
        info = path.lstat()
        data = (os.readlink(path) if path.is_symlink() else
                path.read_bytes() if stat.S_ISREG(info.st_mode) else None)
        result[str(path.relative_to(root))] = (info.st_mode, info.st_mtime_ns, data)
    return result


class TraceCLITests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.journal = TraceJournal(self.root / "telemetry")
        self.tracer = Tracer(self.journal)
        with self.tracer.span("workflow.execute"):
            pass
        self.transport = Mock(return_value=(200, {"content-type": "application/json"}, b"{}"))
        self.events = Mock(return_value=(204, {}, b""))

    def routed_transport(self, url, *args):
        return (self.events if url == EVENT_ENDPOINT else self.transport)(url, *args)

    def export(self, **kwargs):
        return export_pending(self.journal, credential="rotated-fixture-secret",
                              project_id="fixture-test", live=True,
                              transport=self.routed_transport, **kwargs)

    def test_full_ack_marks_and_second_export_does_no_io(self):
        self.assertEqual(self.export()["status"], "exported")
        self.assertEqual(self.journal.rows(pending=True), [])
        self.assertEqual(self.export()["status"], "empty")
        self.assertEqual(self.transport.call_count, 1)
        self.assertEqual(self.events.call_count, 1)
        receipt = self.journal.export_rows()[0]["result"]
        self.assertEqual(receipt["schema"], "trace-export-result/v2")
        self.assertEqual(receipt["events"]["event_count"], 1)
        self.assertEqual(receipt["traces"]["span_count"], 1)

    def test_invalid_config_or_missing_live_never_claims_or_calls(self):
        with self.assertRaises(ServiceError):
            export_pending(self.journal, credential="secret", project_id="fixture", transport=self.transport)
        with self.assertRaises(ServiceError):
            export_pending(self.journal, credential="", project_id="fixture", live=True, transport=self.transport)
        self.assertEqual(len(self.journal.rows(pending=True)), 1)
        self.transport.assert_not_called()

    def test_timeout_intent_does_not_retransmit_or_mark_accepted(self):
        self.transport.side_effect = TimeoutError("private path and server secret")
        result = self.export()
        self.assertEqual(result["status"], "unknown")
        self.assertNotIn("private", json.dumps(result))
        self.assertEqual(self.journal.rows()[0]["exported"], 0)
        self.assertEqual(self.export()["status"], "empty")
        self.assertEqual(self.transport.call_count, 1)
        rows = self.journal.export_rows()
        self.assertEqual(len(rows), 1)

    def test_partial_ack_does_not_retransmit_whole_batch(self):
        self.transport.return_value = (200, {"content-type": "application/json"},
                                      b'{"partialSuccess":{"rejectedSpans":"1","errorMessage":"secret"}}')
        self.assertEqual(self.export()["status"], "partial")
        self.assertEqual(self.journal.rows()[0]["exported"], 0)
        self.export()
        self.assertEqual(self.transport.call_count, 1)

    def test_export_intent_write_failure_prevents_network(self):
        with patch.object(self.journal, "begin_export", side_effect=OSError("disk")):
            with self.assertRaises(OSError):
                self.export()
        self.transport.assert_not_called()

    def test_acknowledged_upload_with_receipt_write_failure_is_not_retried(self):
        with patch.object(self.journal, "finish_export", side_effect=OSError("private failure")):
            with self.assertRaises(OSError):
                self.export()
        reopened = TraceJournal(self.journal.directory)
        self.assertEqual(reopened.status()["unfinished_exports"], 1)
        self.assertEqual(reopened.rows()[0]["exported"], 0)
        result = export_pending(reopened, credential="rotated-fixture-secret", project_id="fixture-test",
                                live=True, transport=self.transport)
        self.assertEqual(result["status"], "empty")
        self.assertEqual(self.transport.call_count, 1)
        self.assertEqual(reopened.export_rows()[0]["status"], "running")

    def test_missing_live_flag_fails_before_opening_state(self):
        err = io.StringIO()
        with redirect_stderr(err), patch("researcher.service.trace_cli.journal_at") as opened:
            self.assertEqual(main(["export", "--state", "/not/opened", "--env-file", "/not/read"]), 1)
        opened.assert_not_called()
        self.assertEqual(json.loads(err.getvalue()), {"error": "TRACE_EXPORT_LIVE_REQUIRED"})

    def test_cli_inspection_and_catalog_are_offline_and_metadata_only(self):
        for args in (["status", "--state", str(self.root)], ["preview", "--state", str(self.root)],
                     ["list", "--state", str(self.root)], ["deliveries", "--state", str(self.root)], ["tools"]):
            out = io.StringIO()
            with patch("socket.socket.connect", side_effect=AssertionError("network forbidden")), redirect_stdout(out):
                self.assertEqual(main(args), 0)
            self.assertIsInstance(json.loads(out.getvalue()), dict)

    def test_inspection_of_empty_telemetry_never_initializes_it(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            directory = root / "telemetry"
            directory.mkdir(mode=0o700)
            before = directory.stat().st_mtime_ns
            with redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
                self.assertEqual(main(["status", "--state", str(root)]), 1)
            self.assertEqual(list(directory.iterdir()), [])
            self.assertEqual(directory.stat().st_mtime_ns, before)

    def test_valid_inspection_keeps_every_file_byte_mode_and_mtime_unchanged(self):
        before = snapshot(self.root)
        for command in ("status", "list", "deliveries", "preview"):
            with self.subTest(command=command), redirect_stdout(io.StringIO()):
                self.assertEqual(main([command, "--state", str(self.root)]), 0)
            self.assertEqual(snapshot(self.root), before)

    def test_incomplete_or_corrupt_storage_is_never_repaired_by_any_cli_command(self):
        mutations = ("trace.lock", "correlation.key", "traces.sqlite3", "bad-key", "bad-db",
                     "empty-db", "missing-table", "unexpected-trigger", "recovery-journal", "wal-mode")
        for mutation in mutations:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                journal = TraceJournal(root / "telemetry")
                if mutation in {"trace.lock", "correlation.key", "traces.sqlite3"}:
                    (journal.directory / mutation).unlink()
                elif mutation == "bad-key":
                    (journal.directory / "correlation.key").write_bytes(b"short")
                elif mutation in {"bad-db", "empty-db"}:
                    journal.path.write_bytes(b"not a database" if mutation == "bad-db" else b"")
                elif mutation == "recovery-journal":
                    sidecar = journal.directory / "traces.sqlite3-journal"
                    sidecar.write_bytes(b"pending recovery must not be touched")
                    sidecar.chmod(0o600)
                else:
                    with sqlite3.connect(journal.path) as db:
                        if mutation == "missing-table":
                            db.execute("DROP TABLE export_claims")
                        elif mutation == "unexpected-trigger":
                            db.execute("CREATE TRIGGER unapproved AFTER INSERT ON spans BEGIN DELETE FROM spans; END")
                        else:
                            db.execute("PRAGMA journal_mode=WAL")
                before = snapshot(root)
                for command in ("status", "list", "deliveries", "preview", "export", "prune"):
                    args = [command, "--state", str(root)]
                    if command == "export":
                        args += ["--live", "--env-file", "/not/read"]
                    elif command == "prune":
                        args += ["--apply", "--older-than-days", "1"]
                    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()), \
                         patch("researcher.service.trace_cli.read_env_file", side_effect=AssertionError("no credentials")), \
                         patch("researcher.service.trace_cli.export_payload", side_effect=AssertionError("no network")):
                        self.assertEqual(main(args), 1)
                    self.assertEqual(snapshot(root), before, command)

    def test_missing_telemetry_and_unsafe_existing_paths_do_not_create_or_chmod(self):
        for mutation in ("directory", "key-link", "key-hardlink", "lock-link", "db-mode"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                if mutation != "directory":
                    journal = TraceJournal(root / "telemetry")
                    key = journal.directory / "correlation.key"
                    if mutation == "key-hardlink":
                        os.link(key, root / "second-key")
                    elif mutation in {"key-link", "lock-link"}:
                        target = key if mutation == "key-link" else journal.directory / "trace.lock"
                        outside = root / "outside"
                        target.rename(outside)
                        target.symlink_to(outside)
                    else:
                        journal.path.chmod(0o644)
                before = snapshot(root)
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    self.assertEqual(main(["status", "--state", str(root)]), 1)
                self.assertEqual(snapshot(root), before)

    def test_prune_without_approval_never_opens_storage(self):
        with redirect_stderr(io.StringIO()), patch("researcher.service.trace_cli.journal_at") as opened:
            self.assertEqual(main(["prune", "--state", "/not/opened", "--older-than-days", "1"]), 1)
        opened.assert_not_called()

    def test_cli_no_live_flag_refuses_before_reading_env(self):
        err = io.StringIO()
        with redirect_stderr(err), patch("researcher.service.trace_cli.read_env_file") as read:
            self.assertEqual(main(["export", "--state", str(self.root), "--env-file", "/not/read"]), 1)
        read.assert_not_called()
        self.assertEqual(json.loads(err.getvalue()), {"error": "TRACE_EXPORT_LIVE_REQUIRED"})

    def test_cli_preflight_needs_no_state_and_never_initializes_or_calls(self):
        for project, expected_exit in (("fixture-test", 0), ("default", 1), ("UPPER", 1)):
            with self.subTest(expected_exit=expected_exit):
                out = io.StringIO()
                with redirect_stdout(out), patch("researcher.service.trace_cli.read_env_file",
                        return_value={"RAINDROP_WRITE_KEY": "private-fixture-key", "RAINDROP_PROJECT_ID": project}), \
                     patch("researcher.service.trace_cli.journal_at", side_effect=AssertionError("state forbidden")), \
                     patch("researcher.service.trace_cli.export_payload", side_effect=AssertionError("network forbidden")):
                    self.assertEqual(main(["preflight", "--env-file", "/private/fixture"]), expected_exit)
                value = json.loads(out.getvalue())
                self.assertEqual(value["schema"], "trace-export-preflight/v1")
                self.assertFalse(value["network_checked"])
                self.assertNotIn("private-fixture-key", out.getvalue())
                self.assertNotIn("/private/fixture", out.getvalue())

    def test_default_project_cli_opt_in_and_blank_refusal(self):
        for project, options, code in (("default", [], 1), ("default", ["--allow-default-project"], 0),
                                       ("", ["--allow-default-project"], 1)):
            out = io.StringIO()
            with redirect_stdout(out), patch("researcher.service.trace_cli.read_env_file",
                    return_value={"RAINDROP_WRITE_KEY": "private-fixture-key", "RAINDROP_PROJECT_ID": project}):
                self.assertEqual(main(["preflight", "--env-file", "/private/fixture", *options]), code)
            self.assertNotIn("private-fixture-key", out.getvalue())
        out = io.StringIO()
        with redirect_stdout(out), patch("researcher.service.trace_cli.read_env_file",
                return_value={"RAINDROP_WRITE_KEY": "private-fixture-key", "RAINDROP_PROJECT_ID": "default"}), \
             patch("researcher.service.trace_cli.export_payload", return_value={
                 "schema": "trace-export-result/v1", "status": "exported", "attempted": True,
                 "span_count": 1, "rejected_spans": 0, "warning": False, "error_code": None}) as send, \
             patch("researcher.service.trace_cli.export_events", return_value={
                 "schema": "trace-event-export/v1", "status": "exported", "attempted": True,
                 "event_count": 1, "error_code": None}):
            self.assertEqual(main(["export", "--state", str(self.root), "--env-file", "/private/fixture",
                                   "--live", "--allow-default-project"]), 0)
        self.assertIs(send.call_args.kwargs["allow_default_project"], True)
        self.assertEqual(self.journal.status()["export_attempts"], 1)

    def test_event_rejection_or_unknown_prevents_otlp_and_whole_batch_retry(self):
        self.events.return_value = (403, {}, b"private failure")
        result = self.export()
        self.assertEqual(result["status"], "rejected")
        self.assertIsNone(result["traces"])
        self.transport.assert_not_called()
        self.assertEqual(self.export()["status"], "empty")
        self.assertEqual(self.events.call_count, 1)

    def test_event_ack_is_saved_before_trace_attempt(self):
        def trace(*args):
            saved = self.journal.export_rows()[0]
            self.assertEqual(saved["status"], "running")
            self.assertEqual(saved["result"]["events"]["status"], "exported")
            raise TimeoutError("private uncertainty")
        self.transport.side_effect = trace
        result = self.export()
        self.assertEqual(result["status"], "unknown")
        self.assertEqual(result["events"]["status"], "exported")
        self.assertEqual(result["traces"]["status"], "unknown")
        self.assertEqual(self.export()["status"], "empty")
        self.assertEqual(self.events.call_count, 1)

    def test_event_receipt_write_failure_prevents_trace_and_retains_claim(self):
        with patch.object(self.journal, "record_event_export", side_effect=OSError("private disk")):
            with self.assertRaises(OSError):
                self.export()
        self.events.assert_called_once()
        self.transport.assert_not_called()
        self.assertEqual(self.export()["status"], "empty")
        self.assertEqual(self.journal.export_rows()[0]["status"], "running")

    def test_root_then_child_batch_publishes_event_only_once(self):
        self.export()  # Finish the unrelated setup root.
        with self.tracer.span("organization.cycle"):
            with self.tracer.span("source.retrieve", attributes={"provider": "arxiv"}):
                pass
        roots = self.export(limit=1)
        children = self.export(limit=1)
        self.assertEqual(roots["events"]["event_count"], 1)
        self.assertEqual(children["events"], {"schema": "trace-event-export/v1", "status": "empty",
                         "attempted": False, "event_count": 0, "error_code": None})
        self.assertEqual(self.events.call_count, 2)
        self.assertEqual(self.transport.call_count, 3)
        self.assertEqual(self.journal.status()["pending_export"], 0)

    def test_unfinished_root_blocks_manual_child_export_before_claim_or_http(self):
        self.export()
        self.events.reset_mock()
        self.transport.reset_mock()
        with self.tracer.span("organization.cycle"):
            with self.tracer.span("source.retrieve"):
                pass
            before = self.journal.export_rows()
            with self.assertRaisesRegex(ServiceError, "TRACE_EVENT_ROOT_UNCONFIRMED"):
                self.export()
            self.assertEqual(self.journal.export_rows(), before)
            self.assertEqual(self.journal.status()["pending_export"], 1)
            self.events.assert_not_called()
            self.transport.assert_not_called()
        self.assertEqual(self.export()["status"], "exported")

    def test_legacy_root_otlp_ack_does_not_authorize_child_event_association(self):
        self.export()
        with self.tracer.span("organization.cycle"):
            with self.tracer.span("source.retrieve"):
                pass
        root = self.journal.rows(pending=True)[0]
        attempt = self.journal.begin_export([root["span_id"]])
        self.journal.finish_export(attempt, {"schema": "trace-export-result/v1", "status": "exported",
            "attempted": True, "span_count": 1, "rejected_spans": 0, "warning": False, "error_code": None})
        self.events.reset_mock()
        self.transport.reset_mock()
        before = self.journal.export_rows()
        with self.assertRaisesRegex(ServiceError, "TRACE_EVENT_ROOT_UNCONFIRMED"):
            self.export()
        self.assertEqual(self.journal.export_rows(), before)
        self.assertEqual(self.journal.status()["pending_export"], 1)
        self.events.assert_not_called()
        self.transport.assert_not_called()

    def test_unknown_root_event_blocks_children_without_claiming_or_retry(self):
        self.export()
        with self.tracer.span("organization.cycle"):
            with self.tracer.span("source.retrieve"):
                pass
        self.events.return_value = (500, {}, b"")
        self.assertEqual(self.export(limit=1)["events"]["status"], "unknown")
        self.events.reset_mock()
        self.transport.reset_mock()
        before = self.journal.export_rows()
        with self.assertRaisesRegex(ServiceError, "TRACE_EVENT_ROOT_UNCONFIRMED"):
            self.export()
        self.assertEqual(self.journal.export_rows(), before)
        self.assertEqual(self.journal.status()["pending_export"], 1)
        self.events.assert_not_called()
        self.transport.assert_not_called()

    def test_successful_event_with_unknown_otlp_allows_child_only_continuation(self):
        self.export()
        with self.tracer.span("organization.cycle"):
            with self.tracer.span("source.retrieve"):
                pass
        self.transport.side_effect = TimeoutError("private transport uncertainty")
        root_result = self.export(limit=1)
        self.assertEqual((root_result["status"], root_result["events"]["status"]), ("unknown", "exported"))
        saved_root = self.journal.export_rows()[-1]
        self.transport.side_effect = None
        self.events.reset_mock()
        self.transport.reset_mock()
        result = self.export()
        self.assertEqual((result["status"], result["events"]["status"]), ("exported", "empty"))
        self.events.assert_not_called()
        self.transport.assert_called_once()
        self.assertEqual(self.journal.export_rows()[-2], saved_root)
        self.assertEqual(self.journal.status()["unacknowledged_spans"], 1)

    def test_saved_event_success_progress_is_sufficient_after_receipt_write_crash(self):
        self.export()
        with self.tracer.span("organization.cycle"):
            with self.tracer.span("source.retrieve"):
                pass
        with patch.object(self.journal, "finish_export", side_effect=OSError("local failure")):
            with self.assertRaises(OSError):
                self.export(limit=1)
        saved_root = self.journal.export_rows()[-1]
        self.assertEqual(saved_root["result"]["schema"], "trace-export-progress/v2")
        self.assertEqual(saved_root["result"]["events"]["status"], "exported")
        self.journal = TraceJournal(self.journal.directory)
        self.events.reset_mock()
        self.transport.reset_mock()
        self.assertEqual(self.export()["status"], "exported")
        self.assertEqual(self.journal.export_rows()[-2], saved_root)
        self.events.assert_not_called()
        self.transport.assert_called_once()

    def test_corrupt_event_receipt_or_root_claim_binding_refuses_before_io(self):
        self.export()
        with self.tracer.span("organization.cycle"):
            with self.tracer.span("source.retrieve"):
                pass
        self.export(limit=1)
        attempt = self.journal.export_rows()[-1]
        unrelated_attempt_id = self.journal.export_rows()[0]["attempt_id"]
        self.events.reset_mock()
        self.transport.reset_mock()
        invalid = dict(attempt["result"])
        invalid["events"] = {**invalid["events"], "event_count": 2}
        with self.journal.connect() as db:
            db.execute("UPDATE export_attempts SET result=? WHERE attempt_id=?",
                       (json.dumps(invalid), attempt["attempt_id"]))
        with self.assertRaisesRegex(ServiceError, "TRACE_INVALID_EXPORT_RECEIPT"):
            self.export()
        with self.journal.connect() as db:
            db.execute("UPDATE export_attempts SET result=? WHERE attempt_id=?",
                       (json.dumps(attempt["result"]), attempt["attempt_id"]))
            db.execute("UPDATE export_claims SET attempt_id=? WHERE span_id=?",
                       (unrelated_attempt_id, attempt["span_ids"][0]))
        with self.assertRaisesRegex(ServiceError, "TRACE_INVALID_EXPORT_RECEIPT"):
            self.export()
        self.assertEqual(self.journal.status()["pending_export"], 1)
        self.events.assert_not_called()
        self.transport.assert_not_called()

    def test_missing_local_root_never_infers_an_event_from_child_trace_id(self):
        self.export()
        self.journal.begin("c" * 32, "d" * 16, "e" * 16, "source.retrieve", 100, {})
        self.journal.finish("d" * 16, 200, 100, "ok", {})
        before = self.journal.export_rows()
        self.events.reset_mock()
        self.transport.reset_mock()
        with self.assertRaisesRegex(ServiceError, "TRACE_EVENT_ROOT_UNCONFIRMED"):
            self.export()
        self.assertEqual(self.journal.export_rows(), before)
        self.assertEqual(self.journal.status()["pending_export"], 1)
        self.events.assert_not_called()
        self.transport.assert_not_called()

    def test_historical_otlp_ack_is_not_republished_as_an_event(self):
        row = self.journal.rows()[0]
        attempt = self.journal.begin_export([row["span_id"]])
        legacy = {"schema": "trace-export-result/v1", "status": "exported", "attempted": True,
                  "span_count": 1, "rejected_spans": 0, "warning": False, "error_code": None}
        self.journal.finish_export(attempt, legacy)
        self.assertEqual(self.export()["status"], "empty")
        self.events.assert_not_called()
        self.transport.assert_not_called()
        self.assertEqual(self.journal.export_rows()[0]["result"], legacy)

    def test_retention_only_removes_confirmed_exported_rows(self):
        with self.assertRaises(ServiceError):
            self.journal.prune_exported(before_ns=-1)
        self.assertEqual(self.journal.prune_exported(before_ns=2**63 - 1), 0)
        self.export()
        self.assertEqual(self.journal.prune_exported(before_ns=2**63 - 1), 1)


if __name__ == "__main__":
    unittest.main()
