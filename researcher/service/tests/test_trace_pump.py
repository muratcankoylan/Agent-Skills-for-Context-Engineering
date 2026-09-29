"""Foreground export contracts with fake transport; no credentials or network."""
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

from researcher.service.contracts import ServiceError
from researcher.service.trace_export import ENDPOINT, TIMEOUT_SECONDS
from researcher.service.trace_events import ENDPOINT as EVENT_ENDPOINT
from researcher.service.trace_pump import TracePump
from researcher.service.tracing import TraceJournal, Tracer


SECRET = "private-fixture-trace-key"


class TracePumpTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.journal = TraceJournal(self.root / "telemetry")
        self.tracer = Tracer(self.journal)
        self.transport = Mock(return_value=(200, {"content-type": "application/json"}, b"{}"))
        self.events = Mock(return_value=(204, {}, b""))
        self.now = 100

    def span(self):
        with self.tracer.span("organization.cycle"):
            pass

    def pump(self, **overrides):
        trace_transport = overrides.pop("transport", self.transport)
        def routed_transport(url, *args):
            return (self.events if url == EVENT_ENDPOINT else trace_transport)(url, *args)
        options = {"credential": SECRET, "project_id": "fixture-test", "live": True,
                   "transport": routed_transport if callable(trace_transport) else trace_transport,
                   "clock": lambda: self.now}
        return TracePump(self.root, **{**options, **overrides})

    def test_constructor_has_no_io_and_credentials_are_not_in_repr(self):
        with patch("researcher.service.trace_pump.journal_at", side_effect=AssertionError("I/O")):
            pump = self.pump()
        self.transport.assert_not_called()
        self.assertNotIn(SECRET, repr(pump))
        self.assertNotIn(str(self.root), repr(pump))

    def test_explicit_live_gate_precedes_state_or_network(self):
        for live in (False, None, 0, 1, "true"):
            with self.subTest(live=live), patch("researcher.service.trace_pump.journal_at") as opened:
                with self.assertRaisesRegex(ServiceError, "TRACE_EXPORT_LIVE_REQUIRED"):
                    self.pump(live=live)
                opened.assert_not_called()
        self.transport.assert_not_called()

    def test_invalid_configuration_fails_before_io(self):
        invalid = [{"credential": ""}, {"credential": "bad key"}, {"project_id": ""},
                   {"project_id": "Private"}, {"project_id": "default"},
                   {"allow_default_project": 1}, {"interval_seconds": True},
                   {"interval_seconds": 4}, {"interval_seconds": 3601}, {"limit": 0},
                   {"limit": 101}, {"limit": True}, {"clock": None}, {"transport": 1}]
        with patch("researcher.service.trace_pump.journal_at") as opened:
            for options in invalid:
                with self.subTest(options=options), self.assertRaises(ServiceError):
                    self.pump(**options)
            opened.assert_not_called()
        self.transport.assert_not_called()

    def test_default_project_requires_approval_and_preserves_explicit_wire(self):
        self.span()
        result = self.pump(project_id="default", allow_default_project=True).tick()
        self.assertEqual(result["status"], "exported")
        url, headers, _, timeout = self.transport.call_args.args
        self.assertEqual((url, timeout), (ENDPOINT, TIMEOUT_SECONDS))
        self.assertEqual(headers["X-Raindrop-Project-Id"], "default")
        self.assertEqual(headers["Authorization"], "Bearer " + SECRET)
        self.assertNotIn(SECRET, json.dumps(result))

    def test_tick_exports_one_bounded_batch_and_cadence_prevents_hot_loop(self):
        for _ in range(3):
            self.span()
        pump = self.pump(limit=2)
        first = pump.tick()
        self.assertEqual((first["status"], first["delivery"]["span_count"]), ("exported", 2))
        self.assertEqual(self.journal.status()["pending_export"], 1)
        for moment in (100, 101, 159):
            self.now = moment
            self.assertEqual(pump.tick()["status"], "deferred")
        self.assertEqual(self.transport.call_count, 1)
        self.now = 160
        self.assertEqual(pump.tick()["delivery"]["span_count"], 1)
        self.assertEqual(self.transport.call_count, 2)
        self.now = 220
        self.assertEqual(pump.tick()["status"], "empty")
        self.assertEqual(self.transport.call_count, 2)

    def test_running_spans_are_not_fabricated_as_completed(self):
        pump = self.pump()
        with self.tracer.span("organization.cycle"):
            self.assertEqual(pump.tick()["status"], "empty")
            self.transport.assert_not_called()
        self.now += 60
        self.assertEqual(pump.tick()["delivery"]["span_count"], 1)

    def test_default_tick_never_drains_more_than_one_hundred_spans(self):
        for _ in range(101):
            self.span()
        result = self.pump().tick()
        self.assertEqual(result["delivery"]["span_count"], 100)
        self.assertEqual(self.transport.call_count, 1)
        self.assertEqual(self.journal.status()["pending_export"], 1)

    def test_empty_tick_obeys_cadence_even_when_new_work_arrives(self):
        pump = self.pump()
        self.assertEqual(pump.tick()["status"], "empty")
        self.span()
        self.assertEqual(pump.tick()["status"], "deferred")
        self.transport.assert_not_called()
        self.now += 60
        self.assertEqual(pump.tick()["status"], "exported")

    def test_failure_latches_and_new_spans_are_not_consumed(self):
        cases = [(403, b"private rejected body", "rejected"),
                 (200, b'{"partialSuccess":{"rejectedSpans":1,"errorMessage":"private"}}', "partial"),
                 (500, b"private remote failure", "unknown")]
        for status, body, expected in cases:
            with self.subTest(expected=expected):
                self.span()
                self.transport.return_value = (status, {"content-type": "application/json"}, body)
                pump = self.pump()
                result = pump.tick()
                self.assertEqual((result["status"], result["delivery"]["status"]), ("halted", expected))
                calls = self.transport.call_count
                self.span()
                pending = self.journal.status()["pending_export"]
                self.now += 60
                self.assertEqual(pump.tick()["status"], "halted")
                self.assertEqual(self.transport.call_count, calls)
                self.assertEqual(self.journal.status()["pending_export"], pending)
                self.assertNotIn("private", json.dumps(result))

    def test_restart_never_resends_unknown_claim_and_can_send_new_span(self):
        self.span()
        self.transport.side_effect = TimeoutError("private")
        self.assertEqual(self.pump().tick()["delivery"]["status"], "unknown")
        self.transport.side_effect = None
        self.assertEqual(self.pump().tick()["status"], "empty")
        self.assertEqual(self.transport.call_count, 1)
        self.span()
        self.assertEqual(self.pump().tick()["delivery"]["span_count"], 1)
        self.assertEqual(self.transport.call_count, 2)
        self.assertEqual(self.journal.status()["unacknowledged_spans"], 1)

    def test_default_batch_restart_does_not_export_children_of_rejected_root_event(self):
        with self.tracer.span("organization.cycle"):
            for _ in range(101):
                with self.tracer.span("source.retrieve", attributes={"provider": "arxiv"}):
                    pass
        self.events.return_value = (401, {}, b"")
        first = self.pump().tick()
        self.assertEqual(first["status"], "halted")
        self.assertEqual(first["delivery"]["span_count"], 100)
        self.assertEqual(first["delivery"]["events"]["status"], "rejected")
        retained = self.journal.export_rows()
        self.assertEqual(self.journal.status()["pending_export"], 2)
        self.events.reset_mock()
        self.transport.reset_mock()
        restarted = self.pump()
        result = restarted.tick()
        self.assertEqual((result["status"], result["error_code"]),
                         ("halted", "TRACE_EVENT_ROOT_UNCONFIRMED"))
        self.assertIsNone(result["delivery"])
        self.assertEqual(self.journal.export_rows(), retained)
        self.assertEqual(self.journal.status()["pending_export"], 2)
        self.assertEqual(self.journal.status()["unacknowledged_spans"], 102)
        self.events.assert_not_called()
        self.transport.assert_not_called()
        self.assertEqual(restarted.tick()["error_code"], "TRACE_EVENT_ROOT_UNCONFIRMED")

    def test_default_batch_healthy_restart_exports_remaining_children_without_recreating_event(self):
        with self.tracer.span("organization.cycle"):
            for _ in range(101):
                with self.tracer.span("source.retrieve", attributes={"provider": "arxiv"}):
                    pass
        first = self.pump().tick()
        self.assertEqual((first["status"], first["delivery"]["span_count"]), ("exported", 100))
        retained = self.journal.export_rows()[0]
        second = self.pump().tick()
        self.assertEqual((second["status"], second["delivery"]["span_count"]), ("exported", 2))
        self.assertEqual(second["delivery"]["events"]["status"], "empty")
        self.assertEqual(self.events.call_count, 1)
        self.assertEqual(self.transport.call_count, 2)
        self.assertEqual(self.journal.export_rows()[0], retained)
        self.assertEqual(self.journal.status()["pending_export"], 0)
        self.assertEqual(self.journal.status()["unacknowledged_spans"], 0)

    def test_intent_failure_prevents_network_and_halts(self):
        self.span()
        pump = self.pump()
        with patch.object(TraceJournal, "begin_export", side_effect=OSError("private path")):
            self.assertEqual(pump.tick()["error_code"], "TRACE_PUMP_LOCAL_FAILURE")
        self.transport.assert_not_called()
        self.assertEqual(self.journal.status()["pending_export"], 1)
        self.now += 60
        self.assertEqual(pump.tick()["status"], "halted")

    def test_ack_receipt_failure_is_quarantined_after_restart(self):
        self.span()
        with patch.object(TraceJournal, "finish_export", side_effect=OSError("private path")):
            self.assertEqual(self.pump().tick()["status"], "halted")
        self.assertEqual(self.journal.status()["unfinished_exports"], 1)
        self.assertEqual(self.pump().tick()["status"], "empty")
        self.assertEqual(self.transport.call_count, 1)

    def test_missing_journal_is_not_created_or_repaired(self):
        missing = self.root / "new-state"
        pump = TracePump(missing, credential=SECRET, project_id="fixture-test", live=True,
                         transport=self.transport)
        self.assertEqual(pump.tick()["error_code"], "TRACE_JOURNAL_NOT_FOUND")
        self.assertFalse(missing.exists())
        self.transport.assert_not_called()

    def test_invalid_existing_journal_is_not_repaired(self):
        key = self.journal.directory / "correlation.key"
        key.unlink()
        before = {str(p): p.read_bytes() for p in self.journal.directory.iterdir() if p.is_file()}
        self.assertEqual(self.pump().tick()["status"], "halted")
        self.assertFalse(key.exists())
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.journal.directory.iterdir() if p.is_file()})
        self.transport.assert_not_called()

    def test_only_telemetry_state_changes(self):
        sentinel = self.root / "budget-and-effect-authority"
        sentinel.write_bytes(b"private immutable accounting fixture")
        before = (sentinel.read_bytes(), sentinel.stat().st_mtime_ns, sentinel.stat().st_mode)
        self.span()
        self.assertEqual(self.pump().tick()["status"], "exported")
        self.assertEqual(before, (sentinel.read_bytes(), sentinel.stat().st_mtime_ns, sentinel.stat().st_mode))

    def test_exception_codes_are_closed_and_do_not_reflect(self):
        class BrokenCode(ServiceError):
            def __init__(self):
                pass

            @property
            def code(self):
                raise RuntimeError(SECRET)

        for error in (ServiceError(SECRET), ServiceError([SECRET]), BrokenCode(), OSError(SECRET)):
            with self.subTest(kind=type(error).__name__), patch(
                    "researcher.service.trace_pump.journal_at", side_effect=error):
                result = self.pump().tick()
                self.assertEqual(result["error_code"], "TRACE_PUMP_LOCAL_FAILURE")
                self.assertNotIn(SECRET, json.dumps(result))
        with patch("researcher.service.trace_pump.journal_at", side_effect=ServiceError("TRACE_RECOVERY_REQUIRED")):
            self.assertEqual(self.pump().tick()["error_code"], "TRACE_RECOVERY_REQUIRED")

    def test_invalid_clock_halts_without_io(self):
        for now in (True, None, "100", -1, float("nan"), float("inf"), 10**1000):
            with self.subTest(kind=type(now).__name__), patch("researcher.service.trace_pump.journal_at") as opened:
                result = self.pump(clock=lambda: now).tick()
                self.assertEqual(result["error_code"], "TRACE_PUMP_CLOCK_FAILED")
                opened.assert_not_called()
        with patch("researcher.service.trace_pump.journal_at") as opened:
            self.assertEqual(self.pump(clock=Mock(side_effect=OSError(SECRET))).tick()["status"], "halted")
            opened.assert_not_called()

    def test_clock_rollback_halts_instead_of_loosening_cadence(self):
        pump = self.pump()
        self.assertEqual(pump.tick()["status"], "empty")
        self.now -= 1
        self.assertEqual(pump.tick()["error_code"], "TRACE_PUMP_CLOCK_FAILED")
        self.now += 1000
        self.assertEqual(pump.tick()["status"], "halted")
        self.transport.assert_not_called()

    def test_concurrent_tick_is_nonblocking_and_does_not_duplicate_attempt(self):
        self.span()
        entered, released = threading.Event(), threading.Event()

        def transport(*_args):
            entered.set()
            if not released.wait(5):
                raise TimeoutError()
            return 200, {"content-type": "application/json"}, b"{}"

        pump, results = self.pump(transport=transport), []
        thread = threading.Thread(target=lambda: results.append(pump.tick()))
        thread.start()
        try:
            self.assertTrue(entered.wait(5))
            self.assertEqual(pump.tick()["status"], "busy")
        finally:
            released.set()
            thread.join(5)
        self.assertFalse(thread.is_alive())
        self.assertEqual(results[0]["status"], "exported")
        self.assertEqual(self.journal.status()["export_attempts"], 1)

    def test_process_interrupt_preserves_durable_claim_without_retry(self):
        self.span()
        self.transport.side_effect = KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):
            self.pump().tick()
        self.transport.side_effect = None
        self.assertEqual(self.pump().tick()["status"], "empty")
        self.assertEqual(self.journal.status()["unfinished_exports"], 1)
        self.assertEqual(self.transport.call_count, 1)
