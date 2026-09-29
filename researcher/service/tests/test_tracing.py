"""Private telemetry is bounded metadata, never authority or an effect retry."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from contextlib import redirect_stderr
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from researcher.service.contracts import ServiceError
from researcher.service import tracing as module


SECRET = "fixture-secret-prompt-provider-token-NEVER-EXPORT"


class TracingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="tracing-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.root.chmod(0o700)
        self.journal = module.TraceJournal(self.root / "telemetry")
        self.tracer = module.Tracer(self.journal)

    def completed(self, operation="workflow.execute", **attributes):
        with self.tracer.span(operation, attributes=attributes) as span:
            return span

    def test_closed_metadata_rejects_payloads_enums_and_wrong_scalar_types(self):
        for attributes in ({"prompt": SECRET}, {"provider": SECRET}, {"items": True},
                           {"items": -1}, {"items": 1.5}, {"items": 2**53},
                           {"fixture": 1}, {"http.status_code": 99},
                           {"http.status_code": 600}, {"operation_ref": SECRET}, []):
            with self.subTest(attributes=attributes), self.assertRaises(ServiceError):
                module._attributes(attributes)
        value = {"provider": "openai", "fixture": True, "items": 0, "http.status_code": 200}
        self.assertEqual(module._attributes(value), value)
        self.assertIsNot(module._attributes(value), value)

    def test_decorator_never_records_arguments_results_or_exception_text(self):
        owner = SimpleNamespace(tracer=self.tracer)

        @module.traced("workflow.effect")
        def effect(self, payload, *, credential):
            return {"payload": payload, "credential": credential}

        self.assertEqual(effect(owner, SECRET, credential=SECRET),
                         {"payload": SECRET, "credential": SECRET})
        error = ServiceError(SECRET)
        with self.assertRaises(ServiceError) as caught:
            with self.tracer.span("source.retrieve"):
                raise error
        self.assertIs(caught.exception, error)
        rows = self.journal.rows()
        self.assertEqual(rows[-1]["attributes"]["error.type"], "ServiceError")
        self.assertEqual(rows[-1]["attributes"]["error.code_ref"], self.journal.reference(SECRET))
        self.assertNotIn(SECRET, json.dumps(rows))
        self.assertNotIn(SECRET, json.dumps(module.otlp_payload(rows)))
        for path in self.journal.directory.iterdir():
            self.assertNotIn(SECRET.encode(), path.read_bytes())

    def test_invalid_annotations_do_not_persist_or_change_effect_result(self):
        with self.tracer.span("model.call", attributes={"prompt": SECRET}) as span:
            span.annotate(prompt=SECRET)
            span.annotate(provider="openai", model_ref=self.journal.reference(SECRET))
            span.reference("session_ref", SECRET)
        row = self.journal.rows()[0]
        self.assertNotIn(SECRET, json.dumps(row))
        self.assertEqual(set(row["attributes"]), {"provider", "model_ref", "session_ref"})
        self.assertGreaterEqual(self.tracer.health()["write_failures"], 2)

    def test_parent_child_ids_and_context_restore(self):
        self.assertIsNone(module.current_span())
        with self.tracer.span("pipeline.run", identity="private-job") as parent:
            with module.child_span("source.retrieve", provider="arxiv") as child:
                self.assertIs(module.current_span(), child)
                self.assertEqual(child.trace_id, parent.trace_id)
                self.assertEqual(child.parent_id, parent.span_id)
                self.assertNotEqual(child.span_id, parent.span_id)
            self.assertIs(module.current_span(), parent)
        self.assertIsNone(module.current_span())
        self.assertEqual(parent.trace_id, self.journal.reference("pipeline.run:private-job"))
        rows = self.journal.rows()
        self.assertEqual([row["status"] for row in rows], ["ok", "ok"])
        self.assertRegex(parent.trace_id, r"^[a-f0-9]{32}$")
        self.assertRegex(parent.span_id, r"^[a-f0-9]{16}$")

    def test_child_without_current_span_has_no_effect(self):
        with module.child_span("source.retrieve") as span:
            self.assertIsNone(span)
        module.annotate(provider="openai")
        self.assertEqual(self.journal.rows(), [])

    def test_async_tasks_keep_distinct_parent_contexts(self):
        async def task():
            with self.tracer.span("agent.research") as parent:
                await asyncio.sleep(0)
                with module.child_span("model.call") as child:
                    await asyncio.sleep(0)
                    self.assertIs(module.current_span(), child)
                    return parent.trace_id, parent.span_id, child.parent_id

        async def run():
            return await asyncio.gather(task(), task())

        values = asyncio.run(run())
        self.assertNotEqual(values[0][0], values[1][0])
        self.assertTrue(all(parent == child_parent for _, parent, child_parent in values))
        self.assertIsNone(module.current_span())

    def test_threads_do_not_inherit_another_threads_parent(self):
        gate = threading.Barrier(2)

        def work():
            self.assertIsNone(module.current_span())
            with self.tracer.span("source.retrieve") as span:
                gate.wait(timeout=3)
                self.assertIs(module.current_span(), span)
                return span.trace_id, span.parent_id

        with self.tracer.span("pipeline.run") as root:
            with ThreadPoolExecutor(max_workers=2) as executor:
                values = list(executor.map(lambda _: work(), range(2)))
        self.assertEqual(len({root.trace_id, *(trace for trace, _ in values)}), 3)
        self.assertTrue(all(parent is None for _, parent in values))
        self.assertEqual(self.journal.status()["unfinished_spans"], 0)

    def test_async_decorator_spans_awaited_work_and_preserves_return_value(self):
        owner = SimpleNamespace(tracer=self.tracer)

        @module.traced("mcp.invoke")
        async def invoke(self):
            await asyncio.sleep(0)
            self.current = module.current_span()
            return 42

        self.assertEqual(asyncio.run(invoke(owner)), 42)
        self.assertIsNotNone(owner.current)
        self.assertEqual(owner.current.operation, "mcp.invoke")
        self.assertEqual(self.journal.rows()[0]["status"], "ok")

    def test_monotonic_duration_does_not_follow_wall_clock_rollback(self):
        ticks = iter((100, 150))
        clock = module.Tracer(self.journal, wall_ns=lambda: 1_000_000,
                              monotonic_ns=lambda: next(ticks))
        with clock.span("source.verify"):
            pass
        row = self.journal.rows()[0]
        self.assertEqual((row["start_ns"], row["end_ns"], row["duration_ns"]),
                         (1_000_000, 1_000_050, 50))

    def test_unknown_operation_is_not_written_and_cannot_decorate(self):
        with self.assertRaises(ValueError):
            module.traced(SECRET)
        with self.tracer.span(SECRET):
            result = 7
        self.assertEqual(result, 7)
        self.assertEqual(self.journal.rows(), [])
        self.assertEqual(self.tracer.health()["last_failure"], "TRACE_WRITE_FAILED")

    def test_interrupted_spans_preserve_original_exception_and_restore_context(self):
        for error in (KeyboardInterrupt(SECRET), SystemExit(SECRET)):
            with self.subTest(error=type(error).__name__):
                with self.assertRaises(type(error)) as caught:
                    with self.tracer.span("model.call"):
                        raise error
                self.assertIs(caught.exception, error)
                self.assertIsNone(module.current_span())
        self.assertEqual([row["status"] for row in self.journal.rows()], ["interrupted"] * 2)
        self.assertNotIn(SECRET, json.dumps(self.journal.rows()))

    def test_start_write_failure_does_not_skip_effect_or_leak_error(self):
        calls = []
        with patch.object(self.journal, "begin", side_effect=OSError(SECRET)):
            with self.tracer.span("model.call"):
                calls.append("one effect")
        self.assertEqual(calls, ["one effect"])
        self.assertEqual(self.journal.rows(), [])
        self.assertEqual(self.tracer.health()["last_failure"], "TRACE_WRITE_FAILED")
        self.assertNotIn(SECRET, json.dumps(self.tracer.health()))

    def test_finish_write_failure_does_not_replace_effect_exception(self):
        effect_error = ValueError("original fixture effect failure")
        with patch.object(self.journal, "finish", side_effect=OSError(SECRET)):
            with self.assertRaises(ValueError) as caught:
                with self.tracer.span("model.call"):
                    raise effect_error
        self.assertIs(caught.exception, effect_error)
        self.assertEqual(self.journal.status()["unfinished_spans"], 1)
        self.assertEqual(self.tracer.health()["last_failure"], "TRACE_WRITE_FAILED")

    def test_capacity_is_bounded_without_changing_effect_semantics(self):
        journal = module.TraceJournal(self.root / "small", max_spans=2)
        tracer = module.Tracer(journal)
        effects = []
        for value in range(3):
            with tracer.span("source.retrieve"):
                effects.append(value)
        self.assertEqual(effects, [0, 1, 2])
        self.assertEqual(journal.status()["spans"], 2)
        self.assertEqual(tracer.health()["write_failures"], 1)
        for limit in (0, True, module.MAX_SPANS + 1):
            with self.subTest(limit=limit), self.assertRaises(ServiceError):
                module.TraceJournal(self.root / "invalid", max_spans=limit)
        self.assertFalse((self.root / "invalid").exists())

    def test_concurrent_capacity_checks_have_one_winner(self):
        journal = module.TraceJournal(self.root / "small", max_spans=1)
        gate = threading.Barrier(2)

        def begin(index):
            gate.wait(timeout=3)
            try:
                journal.begin("a" * 32, str(index) * 16, None, "source.retrieve", 1, {})
                return "ok"
            except ServiceError as error:
                return error.code

        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(executor.map(begin, (1, 2)))
        self.assertEqual(sorted(outcomes), ["TRACE_CAPACITY_REACHED", "ok"])
        self.assertEqual(journal.status()["spans"], 1)

    def test_unfinished_span_survives_restart_without_invented_completion(self):
        self.journal.begin("a" * 32, "b" * 16, None, "model.call", 1, {})
        reopened = module.TraceJournal(self.journal.directory)
        self.assertEqual(reopened.status()["unfinished_spans"], 1)
        self.assertEqual(reopened.rows(pending=True), [])
        with self.assertRaises(ServiceError):
            module.otlp_payload(reopened.rows())

    def test_reference_stable_on_reopen_and_unlinkable_between_journals(self):
        value = self.journal.reference(SECRET)
        reopened = module.TraceJournal(self.journal.directory)
        self.assertEqual(reopened.reference(SECRET), value)
        other = module.TraceJournal(self.root / "other")
        self.assertNotEqual(other.reference(SECRET), value)
        self.assertNotIn(SECRET, value)
        for invalid in (123, None, "x" * 4097):
            with self.assertRaises(ServiceError):
                self.journal.reference(invalid)

    def test_existing_read_only_journal_reads_but_refuses_mutations(self):
        completed = self.completed()
        journal = module.TraceJournal(self.journal.directory, initialize=False, read_only=True)
        self.assertEqual(journal.reference(SECRET), self.journal.reference(SECRET))
        self.assertEqual(journal.rows(), self.journal.rows())
        self.assertEqual(journal.status()["spans"], 1)
        self.assertEqual(journal.export_rows(), [])
        for action in (
            lambda: journal.begin_export([completed.span_id]),
            lambda: journal.prune_exported(before_ns=2**63 - 1),
            lambda: journal.begin("a" * 32, "b" * 16, None, "model.call", 1, {}),
        ):
            with self.assertRaisesRegex(ServiceError, "TRACE_READ_ONLY"):
                action()
        with journal.connect(read_only=True) as db:
            self.assertEqual(db.execute("PRAGMA query_only").fetchone()[0], 1)
            with self.assertRaises(sqlite3.OperationalError):
                db.execute("DELETE FROM spans")
        self.assertEqual(self.journal.status()["spans"], 1)

    def test_existing_mutable_open_supports_only_explicit_export_and_prune_effects(self):
        completed = self.completed()
        journal = module.TraceJournal(self.journal.directory, initialize=False)
        attempt = journal.begin_export([completed.span_id])
        journal.finish_export(attempt, self.export_result())
        self.assertEqual(journal.status()["pending_export"], 0)
        self.assertEqual(journal.prune_exported(before_ns=2**63 - 1), 1)
        self.assertEqual(journal.export_rows()[0]["status"], "exported")

    def test_open_modes_require_explicit_booleans_and_no_implicit_readonly_init(self):
        for options in ({"initialize": 0}, {"read_only": 1}, {"read_only": True}):
            with self.subTest(options=options), self.assertRaisesRegex(ServiceError, "TRACE_INVALID_OPEN_MODE"):
                module.TraceJournal(self.root / "never-created", **options)
            self.assertFalse((self.root / "never-created").exists())

    def test_existing_readonly_connection_does_not_repair_after_open(self):
        journal = module.TraceJournal(self.journal.directory, initialize=False, read_only=True)
        self.journal.path.write_bytes(b"")
        with self.assertRaises(ServiceError):
            journal.status()
        self.assertEqual(self.journal.path.read_bytes(), b"")

    def test_unsafe_permissions_and_symlink_database_are_rejected(self):
        self.journal.path.chmod(0o644)
        with self.assertRaises(ServiceError):
            self.journal.rows()
        self.journal.path.chmod(0o600)
        outside = self.root / "outside"
        outside.write_bytes(b"must not modify")
        outside.chmod(0o600)
        self.journal.path.unlink()
        self.journal.path.symlink_to(outside)
        with self.assertRaises(ServiceError):
            self.journal.rows()
        self.assertEqual(outside.read_bytes(), b"must not modify")

    def test_symlink_parent_and_sqlite_sidecar_rejected(self):
        alias = self.root / "alias"
        alias.symlink_to(self.journal.directory, target_is_directory=True)
        with self.assertRaises(ServiceError):
            module.TraceJournal(alias)
        outside = self.root / "outside"
        outside.write_bytes(b"must not modify")
        outside.chmod(0o600)
        (self.journal.directory / "traces.sqlite3-journal").symlink_to(outside)
        with self.assertRaises(ServiceError):
            self.journal.rows()
        self.assertEqual(outside.read_bytes(), b"must not modify")

    def test_corrupt_database_disables_tracer_without_repair_or_effect_change(self):
        self.journal.path.write_bytes(b"corrupt sqlite fixture")
        tracer = module.Tracer.at(self.root)
        self.assertFalse(tracer.health()["available"])
        with tracer.span("model.call"):
            result = 42
        self.assertEqual(result, 42)
        self.assertEqual(self.journal.path.read_bytes(), b"corrupt sqlite fixture")

    def test_corrupt_correlation_key_fails_without_replacing_it(self):
        key = self.journal.directory / "correlation.key"
        key.write_bytes(b"bad")
        with self.assertRaises(ServiceError):
            module.TraceJournal(self.journal.directory)
        self.assertEqual(key.read_bytes(), b"bad")

    def test_begin_rejects_non_metadata_ids_and_invalid_timestamps(self):
        valid = ["a" * 32, "b" * 16, None, "model.call", 1, {}]
        for index, value in ((0, SECRET), (0, "0" * 32), (1, SECRET), (1, "0" * 16),
                             (2, SECRET), (2, "b" * 16), (4, True), (4, -1), (4, 2**63)):
            arguments = valid.copy()
            arguments[index] = value
            with self.subTest(index=index, value=value), self.assertRaises(ServiceError):
                self.journal.begin(*arguments)
        self.assertEqual(self.journal.rows(), [])

    def test_finish_rejects_inconsistent_and_wrong_type_clocks_without_mutation(self):
        self.journal.begin("a" * 32, "b" * 16, None, "model.call", 100, {})
        for ended, duration in ((99, 1), (101, -1), (101, 2), (True, 0), (101, True), (2**63, 1)):
            with self.subTest(ended=ended, duration=duration), self.assertRaises(ServiceError):
                self.journal.finish("b" * 16, ended, duration, "ok", {})
        self.assertEqual(self.journal.status()["unfinished_spans"], 1)

    def test_corrupt_stored_rows_fail_closed_before_export(self):
        self.completed()
        original = self.journal.rows()[0]
        for column, invalid in (("trace_id", SECRET), ("operation", SECRET), ("status", SECRET),
                                ("end_ns", -1), ("duration_ns", -1), ("attributes", '{"prompt":"secret"}')):
            with self.subTest(column=column):
                with sqlite3.connect(self.journal.path) as db:
                    db.execute(f"UPDATE spans SET {column}=?", (invalid,))
                with self.assertRaises(ServiceError):
                    self.journal.rows()
                value = json.dumps(original[column]) if column == "attributes" else original[column]
                with sqlite3.connect(self.journal.path) as db:
                    db.execute(f"UPDATE spans SET {column}=?", (value,))

    def test_export_acknowledgment_is_bounded_and_transactional(self):
        completed = self.completed()
        self.journal.begin("a" * 32, "b" * 16, None, "model.call", 1, {})
        for ids in ([], [completed.span_id] * 2, ["c" * 16], [completed.span_id, "b" * 16],
                    ["1" * 16] * (module.MAX_EXPORT + 1)):
            with self.subTest(ids=ids), self.assertRaises(ServiceError):
                self.journal.begin_export(ids)
            self.assertEqual(self.journal.status()["pending_export"], 1)
        attempt = self.journal.begin_export([completed.span_id])
        self.journal.finish_export(attempt, self.export_result())
        self.journal.finish_export(attempt, self.export_result())
        self.assertEqual(self.journal.rows(pending=True), [])
        self.assertEqual(self.journal.status()["unfinished_spans"], 1)

    def test_prune_requires_acknowledgment_and_preserves_pending_and_running(self):
        exported = self.completed()
        self.completed()
        self.journal.begin("a" * 32, "b" * 16, None, "model.call", 1, {})
        attempt = self.journal.begin_export([exported.span_id])
        self.journal.finish_export(attempt, self.export_result())
        end = self.journal.rows()[0]["end_ns"]
        self.assertEqual(self.journal.prune_exported(before_ns=end), 0)
        self.assertEqual(self.journal.prune_exported(before_ns=end + 1), 1)
        self.assertEqual(self.journal.status()["spans"], 2)
        self.assertEqual(self.journal.status()["pending_export"], 1)
        self.assertEqual(self.journal.status()["unfinished_spans"], 1)

    def test_query_and_retention_limits_reject_boolean_or_out_of_range(self):
        for kwargs in ({"limit": True}, {"limit": 0}, {"limit": 101}, {"after": True}, {"after": -1}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ServiceError):
                self.journal.rows(**kwargs)
        for before in (-1, True, 1.1):
            with self.assertRaises(ServiceError):
                self.journal.prune_exported(before_ns=before)

    def test_otlp_payload_has_only_registered_metadata_and_typed_values(self):
        self.completed("model.call", provider="openai", fixture=True, input_tokens=3)
        payload = module.otlp_payload(self.journal.rows())
        module.validate_otlp(payload)
        span = payload["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
        self.assertEqual(span["kind"], 3)
        attributes = {row["key"]: row["value"] for row in span["attributes"]}
        self.assertEqual(attributes, {"gen_ai.system": {"stringValue": "openai"},
                                      module.EVENT_ID_ATTRIBUTE: {"stringValue": span["traceId"]},
                                      module.EVENT_USER_ATTRIBUTE: {"stringValue": module.EVENT_USER},
                                      "fixture": {"boolValue": True}, "gen_ai.usage.input_tokens": {"intValue": "3"}})
        self.assertEqual(set(payload), {"resourceSpans"})

    def test_usage_detail_metadata_has_closed_typed_wire_without_invented_counters(self):
        self.completed("sdk.turn", input_tokens=20, output_tokens=10,
                       cached_input_tokens=0, reasoning_output_tokens=7, usage_details_known=False)
        payload = module.otlp_payload(self.journal.rows())
        module.validate_otlp(payload)
        attributes = {row["key"]: row["value"]
                      for row in payload["resourceSpans"][0]["scopeSpans"][0]["spans"][0]["attributes"]}
        self.assertEqual(attributes["cached_input_tokens"], {"intValue": "0"})
        self.assertEqual(attributes["reasoning_output_tokens"], {"intValue": "7"})
        self.assertEqual(attributes["usage_details_known"], {"boolValue": False})
        self.assertNotIn("cache_write_input_tokens", attributes)
        for key in ("cached_input_tokens", "cache_write_input_tokens", "reasoning_output_tokens"):
            for value in (None, False, -1, "0", 0.5):
                with self.subTest(key=key, value=value), self.assertRaises(ServiceError):
                    module._attributes({key: value})
        with self.assertRaises(ServiceError):
            module._attributes({"usage_details_known": 1})

    def test_otlp_closed_validation_rejects_payload_injection_and_malformed_fields(self):
        self.completed("model.call")
        valid = module.otlp_payload(self.journal.rows())
        mutations = [lambda p, s: p.update(secret=SECRET),
                     lambda p, s: s.update(body=SECRET),
                     lambda p, s: s.update(name=SECRET),
                     lambda p, s: s.update(traceId="0" * 32),
                     lambda p, s: s.update(parentSpanId=s["spanId"]),
                     lambda p, s: s.update(kind=True),
                     lambda p, s: s.update(startTimeUnixNano="-1"),
                     lambda p, s: s.update(endTimeUnixNano="0"),
                     lambda p, s: s.update(status={"code": True}),
                     lambda p, s: s.update(attributes=[{"key": "prompt", "value": {"stringValue": SECRET}}]),
                     lambda p, s: s.update(attributes=[{"key": "items", "value": {"intValue": "1"}}] * 2)]
        for mutate in mutations:
            payload = deepcopy(valid)
            span = payload["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
            mutate(payload, span)
            with self.assertRaises(ServiceError):
                module.validate_otlp(payload)
        for invalid in (None, [], {}, {"resourceSpans": [None]}):
            with self.assertRaises(ServiceError):
                module.validate_otlp(invalid)

    def test_export_rejects_empty_oversized_duplicate_and_unfinished_batches(self):
        self.completed()
        rows = self.journal.rows()
        for invalid in ([], rows * 2, rows * (module.MAX_EXPORT + 1)):
            with self.assertRaises(ServiceError):
                module.otlp_payload(invalid)
        self.journal.begin("a" * 32, "b" * 16, None, "model.call", 1, {})
        with self.assertRaises(ServiceError):
            module.otlp_payload(self.journal.rows())

    def test_instrument_sync_async_and_no_active_trace(self):
        @module.instrument("source.verify")
        def verify(value):
            return value, module.current_span()

        @module.instrument("mcp.read")
        async def read(value):
            await asyncio.sleep(0)
            return value, module.current_span()

        self.assertEqual(verify(SECRET), (SECRET, None))
        self.assertEqual(asyncio.run(read(SECRET)), (SECRET, None))
        self.assertEqual(self.journal.rows(), [])
        with self.tracer.span("workflow.execute") as parent:
            _, sync_span = verify(SECRET)
            _, async_span = asyncio.run(read(SECRET))
            self.assertEqual(sync_span.parent_id, parent.span_id)
            self.assertEqual(async_span.parent_id, parent.span_id)
        self.assertEqual(len(self.journal.rows()), 3)
        self.assertNotIn(SECRET, json.dumps(self.journal.rows()))
        with self.assertRaises(ValueError):
            module.instrument(SECRET)

    def test_decorators_use_active_parent_journal_across_owners(self):
        other = module.TraceJournal(self.root / "other")
        owner = SimpleNamespace(tracer=module.Tracer(other))

        @module.traced("workflow.effect")
        def effect(self):
            return module.current_span()

        @module.traced("mcp.invoke")
        async def invoke(self):
            await asyncio.sleep(0)
            return module.current_span()

        with self.tracer.span("organization.cycle") as parent:
            for span in (effect(owner), asyncio.run(invoke(owner))):
                self.assertIs(span.tracer, self.tracer)
                self.assertEqual(span.parent_id, parent.span_id)
        self.assertEqual(len(self.journal.rows()), 3)
        self.assertEqual(other.rows(), [])

    def test_async_cancellation_is_interrupted_without_exception_payload(self):
        owner = SimpleNamespace(tracer=self.tracer)

        @module.traced("mcp.invoke")
        async def cancelled(self):
            raise asyncio.CancelledError(SECRET)

        with self.assertRaises(asyncio.CancelledError):
            asyncio.run(cancelled(owner))
        row = self.journal.rows()[0]
        self.assertEqual(row["status"], "interrupted")
        self.assertEqual(row["attributes"], {"error.type": "CancelledError"})
        self.assertNotIn(SECRET, json.dumps(row))

    def test_actual_workflow_role_names_remain_closed_metadata(self):
        for role in ("researcher", "critic", "skill_editor", "evaluator"):
            self.completed("model.call", role=role, provider="openai", fixture=True)
        self.assertEqual([row["attributes"]["role"] for row in self.journal.rows()],
                         ["researcher", "critic", "skill_editor", "evaluator"])
        self.assertEqual(self.tracer.health()["write_failures"], 0)

    def test_annotation_overflow_validates_merged_values_before_mutation(self):
        # A lower test-only capacity exercises the merge invariant without
        # introducing unregistered fields into the production allowlist.
        initial = {"provider": "openai"}
        with patch.object(module, "MAX_ATTRIBUTES", 1):
            with self.tracer.span("model.call", attributes=initial) as span:
                span.annotate(items=1)
                self.assertEqual(span.attributes, initial)
            self.assertEqual(self.journal.rows()[0]["attributes"], initial)

    def test_first_failure_warns_once_and_broken_diagnostic_sink_does_not_raise(self):
        stream = io.StringIO()
        with redirect_stderr(stream):
            self.tracer._failure(SECRET)
            self.tracer._failure("TRACE_WRITE_FAILED")
        self.assertEqual(len(stream.getvalue().splitlines()), 1)
        self.assertNotIn(SECRET, stream.getvalue())
        self.assertEqual(json.loads(stream.getvalue())["code"], "TRACE_INTERNAL_FAILURE")
        fresh = module.Tracer(None)
        with patch("sys.stderr.write", side_effect=OSError(SECRET)):
            fresh._failure("TRACE_WRITE_FAILED")
        self.assertEqual(fresh.health()["write_failures"], 1)

    def test_throwing_exception_code_property_cannot_replace_effect_exception(self):
        class BrokenCode(Exception):
            @property
            def code(self):
                raise ValueError(SECRET)

        error = BrokenCode("original effect")
        with self.assertRaises(BrokenCode) as caught:
            with self.tracer.span("workflow.effect"):
                raise error
        self.assertIs(caught.exception, error)
        self.assertEqual(self.journal.rows()[0]["status"], "error")
        self.assertNotIn(SECRET, json.dumps(self.journal.rows()))

    def test_clock_failures_do_not_skip_effect_or_replace_its_exception(self):
        for clock_name in ("wall_ns", "monotonic_ns"):
            with self.subTest(clock=clock_name):
                with patch.object(self.tracer, clock_name, side_effect=OSError(SECRET)):
                    with self.tracer.span("workflow.effect"):
                        result = 42
                self.assertEqual(result, 42)
        self.assertEqual(self.journal.rows(), [])
        original = ValueError("original effect")
        with patch.object(self.tracer, "monotonic_ns", side_effect=[1, OSError(SECRET)]):
            with self.assertRaises(ValueError) as caught:
                with self.tracer.span("workflow.effect"):
                    raise original
        self.assertIs(caught.exception, original)
        self.assertEqual(self.journal.status()["unfinished_spans"], 1)

    def export_result(self, status="exported", count=1):
        return {"schema": "trace-export-result/v1", "status": status, "attempted": True,
                "span_count": count, "rejected_spans": 0 if status == "exported" else None,
                "warning": False, "error_code": None if status == "exported" else "TIMEOUT"}

    def test_export_intent_survives_restart_and_never_resends_unknown_effect(self):
        span = self.completed()
        attempt = self.journal.begin_export([span.span_id])
        self.assertRegex(attempt, r"^[a-f0-9]{32}$")
        self.assertEqual(self.journal.rows(pending=True), [])
        reopened = module.TraceJournal(self.journal.directory)
        self.assertEqual(reopened.status()["unfinished_exports"], 1)
        self.assertEqual(reopened.export_rows()[0]["status"], "running")
        with self.assertRaisesRegex(ServiceError, "ALREADY_ATTEMPTED"):
            reopened.begin_export([span.span_id])
        reopened.finish_export(attempt, self.export_result("unknown"))
        self.assertEqual(reopened.status()["unfinished_exports"], 0)
        self.assertEqual(reopened.status()["unknown_exports"], 1)
        self.assertEqual(reopened.status()["pending_export"], 0)
        self.assertEqual(reopened.status()["unacknowledged_spans"], 1)
        self.assertEqual(reopened.rows()[0]["exported"], 0)
        with self.assertRaisesRegex(ServiceError, "ALREADY_ATTEMPTED"):
            reopened.begin_export([span.span_id])
        self.assertEqual(reopened.export_rows()[0]["result"]["error_code"], "TIMEOUT")

    def test_full_export_ack_is_atomic_idempotent_and_allows_pruning(self):
        span = self.completed()
        attempt = self.journal.begin_export([span.span_id])
        result = self.export_result()
        self.journal.finish_export(attempt, result)
        self.journal.finish_export(attempt, result)
        row = self.journal.rows()[0]
        self.assertEqual(row["exported"], 1)
        self.assertEqual(self.journal.status()["unfinished_exports"], 0)
        with self.assertRaisesRegex(ServiceError, "ALREADY_FINISHED"):
            self.journal.finish_export(attempt, self.export_result("unknown"))
        self.assertEqual(self.journal.prune_exported(before_ns=row["end_ns"] + 1), 1)
        self.assertEqual(self.journal.export_rows()[0]["result"], result)
        self.assertEqual(self.journal.export_rows(after=1), [])

    def test_partial_and_rejected_exports_do_not_mark_or_retry_spans(self):
        for status, error in (("partial", "PARTIAL_REJECTION"), ("rejected", "HTTP_REJECTED")):
            with self.subTest(status=status):
                span = self.completed()
                attempt = self.journal.begin_export([span.span_id])
                result = {**self.export_result(), "status": status, "rejected_spans": 1, "error_code": error}
                self.journal.finish_export(attempt, result)
                with self.assertRaisesRegex(ServiceError, "ALREADY_ATTEMPTED"):
                    self.journal.begin_export([span.span_id])
        self.assertTrue(all(row["exported"] == 0 for row in self.journal.rows()))
        self.assertEqual(self.journal.rows(pending=True), [])
        self.assertEqual([row["status"] for row in self.journal.export_rows()], ["partial", "rejected"])

    def test_export_result_forgery_or_raw_payload_cannot_complete_intent(self):
        span = self.completed()
        attempt = self.journal.begin_export([span.span_id])
        for mutation in ({"secret": SECRET}, {"span_count": True}, {"span_count": 2},
                         {"attempted": False}, {"rejected_spans": True}, {"error_code": SECRET},
                         {"warning": 1}, {"status": SECRET}):
            with self.subTest(mutation=mutation), self.assertRaises(ServiceError):
                self.journal.finish_export(attempt, {**self.export_result(), **mutation})
            self.assertEqual(self.journal.export_rows()[0]["status"], "running")
            self.assertEqual(self.journal.rows()[0]["exported"], 0)
        self.assertNotIn(SECRET, json.dumps(self.journal.export_rows()))

    def test_receipt_write_failure_rolls_back_span_ack_and_keeps_unknown_intent(self):
        span = self.completed()
        attempt = self.journal.begin_export([span.span_id])
        with sqlite3.connect(self.journal.path) as db:
            db.execute("CREATE TRIGGER fail_export BEFORE UPDATE ON export_attempts "
                       "BEGIN SELECT RAISE(ABORT, 'fixture write failure'); END")
        with self.assertRaises(ServiceError):
            self.journal.finish_export(attempt, self.export_result())
        self.assertEqual(self.journal.rows()[0]["exported"], 0)
        self.assertEqual(self.journal.export_rows()[0]["status"], "running")
        with self.assertRaisesRegex(ServiceError, "ALREADY_ATTEMPTED"):
            self.journal.begin_export([span.span_id])

    def test_export_claim_race_has_one_winner(self):
        span = self.completed()
        gate = threading.Barrier(2)

        def begin(_):
            gate.wait(timeout=3)
            try:
                return self.journal.begin_export([span.span_id])
            except ServiceError as error:
                return error.code

        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(executor.map(begin, range(2)))
        self.assertEqual(outcomes.count("TRACE_EXPORT_ALREADY_ATTEMPTED"), 1)
        self.assertEqual(self.journal.status()["export_attempts"], 1)

    def test_export_attempts_and_queries_are_bounded_without_claiming_extra_spans(self):
        first = self.completed()
        second = self.completed()
        with patch.object(module, "MAX_EXPORT_ATTEMPTS", 1):
            self.journal.begin_export([first.span_id])
            with self.assertRaisesRegex(ServiceError, "CAPACITY_REACHED"):
                self.journal.begin_export([second.span_id])
        self.assertEqual([row["span_id"] for row in self.journal.rows(pending=True)], [second.span_id])
        for kwargs in ({"limit": 0}, {"limit": 101}, {"limit": True}, {"after": -1}, {"after": True}):
            with self.assertRaises(ServiceError):
                self.journal.export_rows(**kwargs)
        for ids in ([], [{}], [None], [first.span_id] * 2, ["c" * 16], ["c" * 16] * 101):
            with self.assertRaises(ServiceError):
                self.journal.begin_export(ids)

    def test_export_read_rejects_corrupt_metadata_without_reflection(self):
        span = self.completed()
        self.journal.begin_export([span.span_id])
        with sqlite3.connect(self.journal.path) as db:
            db.execute("UPDATE export_attempts SET span_ids=?", (json.dumps([SECRET]),))
        with self.assertRaises(ServiceError) as caught:
            self.journal.export_rows()
        self.assertNotIn(SECRET, str(caught.exception))

    def test_otlp_standard_aliases_accept_only_closed_values_and_no_logical_duplicates(self):
        self.completed("model.call", provider="openai", input_tokens=3, output_tokens=4)
        valid = module.otlp_payload(self.journal.rows())
        for attribute in ({"key": "input_tokens", "value": {"intValue": "3"}},
                          {"key": "provider", "value": {"stringValue": "openai"}}):
            payload = deepcopy(valid)
            payload["resourceSpans"][0]["scopeSpans"][0]["spans"][0]["attributes"].append(attribute)
            with self.assertRaises(ServiceError):
                module.validate_otlp(payload)
        payload = deepcopy(valid)
        attributes = payload["resourceSpans"][0]["scopeSpans"][0]["spans"][0]["attributes"]
        attributes[:] = [{"key": "gen_ai.system", "value": {"stringValue": "arxiv"}}]
        with self.assertRaises(ServiceError):
            module.validate_otlp(payload)
        attributes[:] = [{"key": "provider", "value": {"stringValue": "arxiv"}}]
        module.validate_otlp(payload)

    def test_operational_associations_are_derived_for_every_span_and_cannot_carry_content(self):
        with self.tracer.span("organization.cycle"):
            with self.tracer.span("source.retrieve", attributes={"provider": "arxiv"}):
                pass
        payload = module.otlp_payload(self.journal.rows())
        spans = payload["resourceSpans"][0]["scopeSpans"][0]["spans"]
        for span in spans:
            attributes = {a["key"]: a["value"] for a in span["attributes"]}
            self.assertEqual(attributes[module.EVENT_ID_ATTRIBUTE], {"stringValue": span["traceId"]})
            self.assertEqual(attributes[module.EVENT_USER_ATTRIBUTE], {"stringValue": module.EVENT_USER})
        for key, value in ((module.EVENT_ID_ATTRIBUTE, SECRET), (module.EVENT_ID_ATTRIBUTE, "f" * 32),
                           (module.EVENT_USER_ATTRIBUTE, SECRET)):
            variant = deepcopy(payload)
            attributes = variant["resourceSpans"][0]["scopeSpans"][0]["spans"][0]["attributes"]
            next(a for a in attributes if a["key"] == key)["value"] = {"stringValue": value}
            with self.assertRaises(ServiceError):
                module.validate_otlp(variant)
        for name in ("duplicate", "partial"):
            variant = deepcopy(payload)
            attributes = variant["resourceSpans"][0]["scopeSpans"][0]["spans"][0]["attributes"]
            if name == "duplicate":
                attributes.append(deepcopy(attributes[0]))
            else:
                attributes.pop(0)
            with self.assertRaises(ServiceError):
                module.validate_otlp(variant)

    def test_event_phase_progress_survives_restart_without_changing_legacy_schema(self):
        span = self.completed()
        attempt = self.journal.begin_export([span.span_id])
        events = {"schema": "trace-event-export/v1", "status": "exported", "attempted": True,
                  "event_count": 1, "error_code": None}
        self.journal.record_event_export(attempt, events)
        reopened = module.TraceJournal(self.journal.directory, initialize=False, read_only=True)
        saved = reopened.export_rows()[0]
        self.assertEqual(saved["status"], "running")
        self.assertEqual(saved["result"], {"schema": "trace-export-progress/v2", "events": events})
        self.assertEqual(reopened.rows(pending=True), [])
        self.assertEqual(reopened.status()["unfinished_exports"], 1)
        traces = self.export_result()
        result = {"schema": "trace-export-result/v2", "status": "exported", "attempted": True,
                  "span_count": 1, "events": events, "traces": traces}
        self.journal.finish_export(attempt, result)
        self.assertEqual(reopened.export_rows()[0]["result"], result)
        self.assertEqual(reopened.rows()[0]["exported"], 1)

    def test_only_leaf_capabilities_are_typed_tools_with_registered_names(self):
        for name in module.TOOLS:
            self.completed(name)
        payload = module.otlp_payload(self.journal.rows())
        spans = payload["resourceSpans"][0]["scopeSpans"][0]["spans"]
        for span in spans:
            attributes = {a["key"]: a["value"] for a in span["attributes"]}
            if span["name"] in module.TOOL_SPANS:
                self.assertEqual(attributes[module.TOOL_KIND_ATTRIBUTE], {"stringValue": "tool"})
                self.assertEqual(attributes[module.TOOL_NAME_ATTRIBUTE], {"stringValue": span["name"]})
            else:
                self.assertNotIn(module.TOOL_KIND_ATTRIBUTE, attributes)
        for name, key, value in (("workflow.effect", module.TOOL_KIND_ATTRIBUTE, "tool"),
                                 ("source.retrieve", module.TOOL_KIND_ATTRIBUTE, "agent"),
                                 ("source.retrieve", module.TOOL_NAME_ATTRIBUTE, SECRET)):
            variant = deepcopy(payload)
            span = next(s for s in variant["resourceSpans"][0]["scopeSpans"][0]["spans"] if s["name"] == name)
            span["attributes"] = [a for a in span["attributes"] if a["key"] != key]
            span["attributes"].append({"key": key, "value": {"stringValue": value}})
            with self.assertRaises(ServiceError):
                module.validate_otlp(variant)

    def test_event_result_cannot_be_replaced_or_forged_at_finalization(self):
        span = self.completed()
        attempt = self.journal.begin_export([span.span_id])
        events = {"schema": "trace-event-export/v1", "status": "exported", "attempted": True,
                  "event_count": 1, "error_code": None}
        result = {"schema": "trace-export-result/v2", "status": "exported", "attempted": True,
                  "span_count": 1, "events": events, "traces": self.export_result()}
        with self.assertRaises(ServiceError):
            self.journal.finish_export(attempt, result)
        with self.assertRaises(ServiceError):
            self.journal.record_event_export(attempt, {**events, "event_count": 0})
        self.journal.record_event_export(attempt, events)
        with self.assertRaises(ServiceError):
            self.journal.finish_export(attempt, self.export_result())
        with self.assertRaises(ServiceError):
            self.journal.record_event_export(attempt, {**events, "status": "unknown", "error_code": "TIMEOUT"})
        for change in ({"attempted": False}, {"status": "unknown"}, {"traces": None},
                       {"events": {**events, "status": "unknown", "error_code": "TIMEOUT"}}):
            with self.assertRaises(ServiceError):
                self.journal.finish_export(attempt, {**result, **change})
        self.assertEqual(self.journal.rows()[0]["exported"], 0)


if __name__ == "__main__":
    unittest.main()
