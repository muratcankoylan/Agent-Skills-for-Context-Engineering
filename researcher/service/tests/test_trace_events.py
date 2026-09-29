"""Metadata-only Event export contract tests. No provider calls or credentials."""
from copy import deepcopy
import io
import json
import os
import subprocess
import unittest
from unittest.mock import MagicMock, patch

from researcher.service import trace_events as events, tracing
from researcher.service.contracts import ServiceError

SECRET = "fixture-write-key-never-release-as-data"
PROJECT = "research-fixture"


def payload():
    return {"resourceSpans": [{"resource": {"attributes": [{"key": "service.name",
        "value": {"stringValue": "context-research-harness"}}]}, "scopeSpans": [{"scope": {
        "name": "researcher.service", "version": "1"}, "spans": [{"traceId": "a" * 32,
        "spanId": "b" * 16, "name": "organization.cycle", "kind": 1,
        "startTimeUnixNano": "1700000000123456789", "endTimeUnixNano": "1700000001123999999",
        "status": {"code": 1}, "attributes": []}]}]}]}


def spans(value):
    return value["resourceSpans"][0]["scopeSpans"][0]["spans"]


class TraceEventTests(unittest.TestCase):
    def call(self, status=204, headers=None, raw=b"", value=None):
        self.transport = MagicMock(return_value=(status, headers or {}, raw))
        return events.export_events(payload() if value is None else value, credential=SECRET,
                                    project_id=PROJECT, transport=self.transport)

    def test_exact_root_projection_nonmutating_and_metadata_only(self):
        value = payload()
        spans(value)[0]["attributes"] = [
            {"key": "fixture", "value": {"boolValue": True}},
            {"key": "model_ref", "value": {"stringValue": "a" * 32}},
            {"key": "input_tokens", "value": {"intValue": "12"}},
        ]
        original = deepcopy(value)
        projected = events.project_events(value)
        self.assertEqual(projected, [{"event_id": "a" * 32, "user_id": "context-research-harness",
            "event": "organization.cycle", "timestamp": "2023-11-14T22:13:20.123456789Z",
            "properties": {"metadata_only": True, "status": "ok", "duration_ms": 1000, "fixture": True}}])
        self.assertEqual(value, original)
        self.assertNotIn("model_ref", json.dumps(projected))
        self.assertNotIn("input_tokens", json.dumps(projected))
        self.assertEqual(set(projected[0]), {"event_id", "user_id", "event", "timestamp", "properties"})

    def test_status_unknown_is_not_success_and_fixture_absence_is_not_false(self):
        for code, expected in ((0, "unset"), (1, "ok"), (2, "error")):
            value = payload()
            spans(value)[0]["status"]["code"] = code
            result = events.project_events(value)[0]["properties"]
            self.assertEqual(result["status"], expected)
            self.assertNotIn("fixture", result)
        spans(value)[0]["attributes"] = [{"key": "fixture", "value": {"boolValue": False}}]
        self.assertIs(events.project_events(value)[0]["properties"]["fixture"], False)

    def test_root_only_and_multiple_traces(self):
        value = payload()
        child = deepcopy(spans(value)[0])
        child.update(spanId="c" * 16, parentSpanId="b" * 16, name="pipeline.run")
        other = deepcopy(spans(value)[0])
        other.update(traceId="d" * 32, spanId="e" * 16)
        spans(value).extend([child, other])
        self.assertEqual([item["event_id"] for item in events.project_events(value)], ["a" * 32, "d" * 32])
        self.assertEqual(self.call(value=value)["event_count"], 2)

    def test_duplicate_root_trace_ids_are_not_silently_merged(self):
        value = payload()
        other = deepcopy(spans(value)[0])
        other["spanId"] = "c" * 16
        spans(value).append(other)
        transport = MagicMock()
        with self.assertRaisesRegex(ServiceError, "TRACE_EVENT_DUPLICATE_ROOT"):
            events.export_events(value, credential=SECRET, project_id=PROJECT, transport=transport)
        transport.assert_not_called()

    def test_child_only_is_empty_without_io_or_credential_requirement(self):
        value = payload()
        spans(value)[0]["parentSpanId"] = "c" * 16
        with patch.object(events, "_isolated", side_effect=AssertionError("network forbidden")):
            result = events.export_events(value, credential="", project_id="")
        self.assertEqual(result, {"schema": "trace-event-export/v1", "status": "empty", "attempted": False,
                                  "event_count": 0, "error_code": None})
        events.validate_event_result(result, 0)

    def test_invalid_otlp_privacy_and_associations_fail_before_io(self):
        variants = []
        for key in ("prompt", "gen_ai.input.messages", "http.url", "tool.arguments"):
            value = payload()
            spans(value)[0]["attributes"] = [{"key": key, "value": {"stringValue": SECRET}}]
            variants.append(value)
        value = payload()
        spans(value)[0]["name"] = SECRET
        variants.append(value)
        value = payload()
        spans(value)[0]["attributes"] = [
            {"key": tracing.EVENT_ID_ATTRIBUTE, "value": {"stringValue": "c" * 32}},
            {"key": tracing.EVENT_USER_ATTRIBUTE, "value": {"stringValue": tracing.EVENT_USER}}]
        variants.extend([value, {}, {"resourceSpans": []}])
        for value in variants:
            transport = MagicMock()
            with self.assertRaises(ServiceError) as error:
                events.export_events(value, credential=SECRET, project_id=PROJECT, transport=transport)
            self.assertNotIn(SECRET, str(error.exception))
            transport.assert_not_called()

    def test_matching_associations_do_not_leak_or_change_event_projection(self):
        value = payload()
        expected = events.project_events(value)
        spans(value)[0]["attributes"] = [
            {"key": tracing.EVENT_ID_ATTRIBUTE, "value": {"stringValue": "a" * 32}},
            {"key": tracing.EVENT_USER_ATTRIBUTE, "value": {"stringValue": tracing.EVENT_USER}}]
        self.assertEqual(events.project_events(value), expected)

    def test_good_204_has_fixed_wire_and_one_attempt(self):
        result = self.call(headers={"Content-Length": "0"})
        self.assertEqual(result, {"schema": "trace-event-export/v1", "status": "exported", "attempted": True,
                                  "event_count": 1, "error_code": None, "http_status": 204})
        events.validate_event_result(result, 1)
        url, headers, body, timeout = self.transport.call_args.args
        self.assertEqual(url, "https://api.raindrop.ai/v1/events/track")
        self.assertEqual(timeout, 10)
        self.assertEqual(json.loads(body), events.project_events(payload()))
        self.assertEqual(headers["Authorization"], "Bearer " + SECRET)
        self.assertEqual(headers["X-Raindrop-Project-Id"], PROJECT)
        self.assertNotIn(SECRET.encode(), body)
        self.transport.assert_called_once()

    def test_only_empty_204_and_exact_200_json_are_acknowledged(self):
        cases = [(200, {}, b"{}", "UNEXPECTED_CONTENT_TYPE"),
                 (201, {}, b"", "UNEXPECTED_HTTP_STATUS"),
                 (204, {}, SECRET.encode(), "NONEMPTY_ACKNOWLEDGEMENT"),
                 (204, {"content-length": "1"}, b"", "INVALID_RESPONSE_LENGTH"),
                 (204, {"content-length": "-1"}, b"", "INVALID_RESPONSE_LENGTH"),
                 (204, {"content-length": "x"}, b"", "INVALID_RESPONSE_LENGTH"),
                 (204, {"content-encoding": "gzip"}, b"", "UNEXPECTED_ENCODING"),
                 (204, {"transfer-encoding": "chunked"}, b"", "MALFORMED_TRANSPORT")]
        for status, headers, raw, error in cases:
            with self.subTest(status=status, error=error):
                result = self.call(status=status, headers=headers, raw=raw)
                self.assertEqual((result["status"], result["error_code"]), ("unknown", error))
                self.assertNotIn(SECRET, json.dumps(result))
                self.transport.assert_called_once()
                events.validate_event_result(result, 1)

    def test_200_ack_matches_complete_submitted_id_set_in_any_order(self):
        value = payload()
        other = deepcopy(spans(value)[0])
        other.update(traceId="c" * 32, spanId="d" * 16)
        spans(value).append(other)
        raw = json.dumps({"events": [{"event_id": "c" * 32}, {"event_id": "a" * 32}]}).encode()
        result = self.call(status=200, headers={"Content-Type": "application/json; charset=utf-8",
                           "Content-Length": str(len(raw))}, raw=raw, value=value)
        self.assertEqual((result["status"], result["event_count"], result["http_status"]), ("exported", 2, 200))
        events.validate_event_result(result, 2)
        self.transport.assert_called_once()
        # No event IDs or acknowledgement content cross the receipt boundary.
        self.assertNotIn("c" * 32, json.dumps(result))

    def test_200_ack_rejects_missing_foreign_duplicate_and_wrong_typed_ids(self):
        variants = [{}, {"events": []}, {"events": None}, {"events": {}},
            {"events": [{"event_id": "b" * 32}]}, {"events": [{"event_id": None}]},
            {"events": [{"event_id": True}]}, {"events": [{"event_id": 123}]},
            {"events": [{"event_id": "a" * 32}, {"event_id": "a" * 32}]},
            {"events": [{"event_id": "a" * 32}], "extra": SECRET},
            {"events": [{"event_id": "a" * 32, "extra": SECRET}]},
            {"events": ["a" * 32]}]
        for acknowledgement in variants:
            result = self.call(status=200, headers={"content-type": "application/json"},
                               raw=json.dumps(acknowledgement).encode())
            self.assertEqual((result["status"], result["error_code"]), ("unknown", "MALFORMED_ACKNOWLEDGEMENT"))
            events.validate_event_result(result, 1)
            self.assertNotIn(SECRET, json.dumps(result))
            self.transport.assert_called_once()
        value = payload()
        other = deepcopy(spans(value)[0])
        other.update(traceId="c" * 32, spanId="d" * 16)
        spans(value).append(other)
        for ids in (["a" * 32, "a" * 32], ["a" * 32, "e" * 32], ["a" * 32]):
            result = self.call(status=200, headers={"content-type": "application/json"},
                               raw=json.dumps({"events": [{"event_id": identity} for identity in ids]}).encode(), value=value)
            self.assertEqual(result["error_code"], "MALFORMED_ACKNOWLEDGEMENT")

    def test_200_ack_strict_json_framing_encoding_and_size(self):
        valid = json.dumps({"events": [{"event_id": "a" * 32}]}).encode()
        cases = [(b'{"events":[],"events":[]}', {}, "MALFORMED_ACKNOWLEDGEMENT"),
            (b'{"events":[{"event_id":"x","event_id":"y"}]}', {}, "MALFORMED_ACKNOWLEDGEMENT"),
            (b'{"events":NaN}', {}, "MALFORMED_ACKNOWLEDGEMENT"),
            (b'{"events":Infinity}', {}, "MALFORMED_ACKNOWLEDGEMENT"),
            (b'\xff', {}, "MALFORMED_ACKNOWLEDGEMENT"),
            (valid + b"unexpected", {}, "MALFORMED_ACKNOWLEDGEMENT"),
            (valid, {"content-length": "1"}, "INVALID_RESPONSE_LENGTH"),
            (valid, {"content-length": "+60"}, "INVALID_RESPONSE_LENGTH"),
            (valid, {"content-encoding": "gzip"}, "UNEXPECTED_ENCODING"),
            (valid, {"content-type": "text/plain"}, "UNEXPECTED_CONTENT_TYPE"),
            (valid, {"transfer-encoding": "chunked", "content-length": str(len(valid))}, "MALFORMED_TRANSPORT"),
            (b"x" * (events.MAX_RESPONSE_BYTES + 1), {}, "RESPONSE_TOO_LARGE")]
        for raw, overrides, code in cases:
            result = self.call(status=200, headers={"content-type": "application/json", **overrides}, raw=raw)
            self.assertEqual(result["error_code"], code)
            events.validate_event_result(result, 1)
        self.assertEqual(self.call(status=200, headers={"content-type": "application/json", "transfer-encoding": "chunked"},
                                  raw=valid)["status"], "exported")

    def test_200_ack_supports_bounded_hundred_root_batch(self):
        value = payload()
        original = spans(value)[0]
        spans(value)[:] = [dict(original, traceId=f"{index + 1:032x}", spanId=f"{index + 1:016x}") for index in range(100)]
        raw = json.dumps({"events": [{"event_id": span["traceId"]} for span in spans(value)]}).encode()
        result = self.call(status=200, headers={"content-type": "application/json"}, raw=raw, value=value)
        self.assertEqual((result["status"], result["event_count"]), ("exported", 100))
        events.validate_event_result(result, 100)

    def test_native_200_reads_bounded_body_and_child_does_not_emit_it(self):
        raw = json.dumps({"events": [{"event_id": "a" * 32}]}).encode()
        connection, response = MagicMock(), MagicMock()
        connection.getresponse.return_value = response
        response.status = 200
        response.getheaders.return_value = [("content-type", "application/json"), ("content-length", str(len(raw)))]
        response.read1.side_effect = [raw[:20], raw[20:], b""]
        with patch.object(events.http.client, "HTTPSConnection", return_value=connection):
            body, count, headers = events._prepare(payload(), SECRET, PROJECT, False)
            result = events._dispatch(body, count, headers, events._native)
        self.assertEqual(result["status"], "exported")
        self.assertEqual(response.read1.call_count, 3)
        connection.close.assert_called_once()
        packet = {"payload": payload(), "credential": SECRET, "project_id": PROJECT, "allow_default_project": False}
        stdin, stdout = MagicMock(), io.StringIO()
        stdin.buffer = io.BytesIO(json.dumps(packet).encode())
        with patch.object(events.sys, "stdin", stdin), patch.object(events.sys, "stdout", stdout), \
             patch.object(events, "_native", return_value=(200, {"content-type": "application/json"}, raw)):
            events._worker()
        child_result = json.loads(stdout.getvalue())
        self.assertEqual(child_result["status"], "exported")
        events.validate_event_result(child_result, 1)
        self.assertNotIn("a" * 32, stdout.getvalue())
        self.assertNotIn(SECRET, stdout.getvalue())

    def test_native_200_oversized_body_and_declared_length_fail_closed(self):
        for length, chunks in ((str(events.MAX_RESPONSE_BYTES + 1), []),
                               (None, [b"x" * (events.MAX_RESPONSE_BYTES + 1)])):
            connection, response = MagicMock(), MagicMock()
            connection.getresponse.return_value = response
            response.status = 200
            response.getheaders.return_value = [("content-type", "application/json")] + ([] if length is None else [("content-length", length)])
            response.read1.side_effect = chunks
            with patch.object(events.http.client, "HTTPSConnection", return_value=connection):
                result = events._dispatch(b"[]", 1, {}, events._native)
            self.assertEqual(result["error_code"], "RESPONSE_TOO_LARGE")
            connection.close.assert_called_once()
            if length is not None:
                response.read1.assert_not_called()

    def test_malformed_headers_and_transport_shapes_are_unknown(self):
        for headers in ({"Content-Length": "0", "content-length": "0"},
                        {"content-length": "0", "transfer-encoding": "chunked"},
                        {"x-bad": "secret\nline"}, {"bad name": "x"}, {"x": 1}):
            self.assertEqual(self.call(headers=headers)["error_code"], "MALFORMED_TRANSPORT")
        for response in ((True, {}, b""), (204, {}, ""), (204,), (204, [], b"")):
            result = events.export_events(payload(), credential=SECRET, project_id=PROJECT,
                                          transport=MagicMock(return_value=response))
            self.assertEqual(result["status"], "unknown")
            events.validate_event_result(result, 1)

    def test_redirect_rejection_server_failure_have_no_retry_or_remote_text(self):
        for status, expected, error in ((302, "unknown", "REDIRECT_REFUSED"),
                (401, "rejected", "HTTP_REJECTED"), (429, "rejected", "HTTP_REJECTED"),
                (500, "unknown", "UNEXPECTED_HTTP_STATUS")):
            result = self.call(status=status, headers={"location": "https://other.invalid/" + SECRET}, raw=SECRET.encode())
            self.assertEqual((result["status"], result["error_code"]), (expected, error))
            self.assertNotIn(SECRET, json.dumps(result))
            self.transport.assert_called_once()

    def test_transport_exception_is_closed_and_attempted(self):
        for exception, code in ((TimeoutError(SECRET), "TIMEOUT"), (RuntimeError(SECRET), "TRANSPORT_ERROR")):
            transport = MagicMock(side_effect=exception)
            result = events.export_events(payload(), credential=SECRET, project_id=PROJECT, transport=transport)
            self.assertEqual((result["status"], result["error_code"], result["attempted"]), ("unknown", code, True))
            self.assertNotIn(SECRET, json.dumps(result))
            transport.assert_called_once()

    def test_invalid_config_and_credential_reflection_have_no_io(self):
        for key, project, allow in (("", PROJECT, False), (SECRET + "\n", PROJECT, False),
                (SECRET, "default", False), (SECRET, "", True), (SECRET, PROJECT, 1),
                ("organization.cycle", PROJECT, False), ("fixture", "fixture", False)):
            transport = MagicMock()
            with self.assertRaises(ServiceError):
                events.export_events(payload(), credential=key, project_id=project,
                                     allow_default_project=allow, transport=transport)
            transport.assert_not_called()
        transport = MagicMock(return_value=(204, {}, b""))
        self.assertEqual(events.export_events(payload(), credential=SECRET, project_id="default",
            allow_default_project=True, transport=transport)["status"], "exported")

    def test_isolated_process_credential_only_stdin_and_no_ambient_config(self):
        receipt = {"schema": "trace-event-export/v1", "status": "exported", "attempted": True,
                   "event_count": 1, "error_code": None}
        with patch.dict(os.environ, {"HTTP_PROXY": SECRET, "RAINDROP_WRITE_KEY": SECRET}), \
             patch.object(events.subprocess, "run", return_value=subprocess.CompletedProcess([], 0,
                 json.dumps(receipt).encode(), b"")) as run:
            self.assertEqual(events.export_events(payload(), credential=SECRET, project_id="default",
                                                  allow_default_project=True), receipt)
        args, kwargs = run.call_args.args[0], run.call_args.kwargs
        self.assertEqual(args[-2:], ["-m", "researcher.service.trace_events"])
        self.assertNotIn(SECRET, json.dumps(args))
        self.assertNotIn(SECRET, json.dumps(kwargs["env"]))
        self.assertEqual(set(kwargs["env"]), {"PATH", "PYTHONPATH", "PYTHONUTF8"})
        self.assertEqual(kwargs["timeout"], 10)
        packet = json.loads(kwargs["input"])
        self.assertEqual(packet["credential"], SECRET)
        self.assertIs(packet["allow_default_project"], True)

    def test_worker_failures_and_receipt_tampering_never_return_raw_output(self):
        answers = [(1, b"", b""), (0, SECRET.encode(), b""), (0, b"{}", SECRET.encode()),
                   (0, b"x" * 4097, b""), (0, b'{"schema":"trace-event-export/v1","schema":"wrong"}', b"")]
        for returncode, stdout, stderr in answers:
            with patch.object(events.subprocess, "run", return_value=subprocess.CompletedProcess([], returncode, stdout, stderr)):
                result = events.export_events(payload(), credential=SECRET, project_id=PROJECT)
            self.assertEqual(result["error_code"], "WORKER_FAILED")
            self.assertNotIn(SECRET, json.dumps(result))
        for exception, code, attempted in ((subprocess.TimeoutExpired([SECRET], 10), "WALL_TIMEOUT", True),
                                           (OSError(SECRET), "WORKER_START_FAILED", False)):
            with patch.object(events.subprocess, "run", side_effect=exception):
                result = events.export_events(payload(), credential=SECRET, project_id=PROJECT)
            self.assertEqual((result["error_code"], result["attempted"]), (code, attempted))
            events.validate_event_result(result, 1)

    def test_closed_receipt_rejects_unknown_fields_and_inconsistent_states(self):
        good = self.call()
        variants = [dict(good, extra="secret"), dict(good, event_count=True), dict(good, attempted=1),
                    dict(good, status="empty"), dict(good, status="rejected", error_code=None),
                    dict(good, status="unknown", error_code=SECRET),
                    dict(good, status="unknown", error_code="WORKER_START_FAILED"),
                    dict(good, status="unknown", error_code="TIMEOUT", attempted=False),
                    dict(good, status="unknown", error_code="HTTP_REJECTED")]
        for value in variants:
            with self.assertRaises(ServiceError):
                events.validate_event_result(value, 1)
        for count in (-1, 101, True, "1"):
            with self.assertRaises(ServiceError):
                events.validate_event_result(good, count)

    def test_optional_http_status_is_exact_and_legacy_receipts_remain_valid(self):
        result = self.call(status=201)
        self.assertEqual(result["http_status"], 201)
        self.assertEqual(result["status"], "unknown")
        events.validate_event_result(result, 1)
        legacy = dict(result)
        del legacy["http_status"]
        events.validate_event_result(legacy, 1)
        legacy = self.call()
        del legacy["http_status"]
        events.validate_event_result(legacy, 1)
        # A historical unknown200 observation must not be reinterpreted merely
        # because a later implementation recognizes a stricter200 contract.
        events.validate_event_result(dict(result, http_status=200), 1)
        for observed in (True, 99, 600, "200", None, 204, 301, 401):
            with self.assertRaises(ServiceError):
                events.validate_event_result(dict(result, http_status=observed), 1)
        empty = {"schema": "trace-event-export/v1", "status": "empty", "attempted": False,
                 "event_count": 0, "error_code": None, "http_status": 204}
        with self.assertRaises(ServiceError):
            events.validate_event_result(empty, 0)

    def test_worker_revalidates_packet_and_outputs_only_closed_receipt(self):
        packet = {"payload": payload(), "credential": SECRET, "project_id": PROJECT, "allow_default_project": False}
        variants = [dict(packet, url="https://other.invalid"), dict(packet, allow_default_project=1),
                    dict(packet, credential="bad\nkey"), dict(packet, payload={})]
        for value in variants:
            stdin, stdout = MagicMock(), io.StringIO()
            stdin.buffer = io.BytesIO(json.dumps(value).encode())
            with patch.object(events.sys, "stdin", stdin), patch.object(events.sys, "stdout", stdout), \
                 patch.object(events, "_native") as native:
                with self.assertRaises(SystemExit):
                    events._worker()
            native.assert_not_called()
            self.assertEqual(stdout.getvalue(), "")
        stdin, stdout = MagicMock(), io.StringIO()
        stdin.buffer = io.BytesIO(json.dumps(packet).encode())
        with patch.object(events.sys, "stdin", stdin), patch.object(events.sys, "stdout", stdout), \
             patch.object(events, "_native", return_value=(204, {}, b"")) as native:
            events._worker()
        result = json.loads(stdout.getvalue())
        events.validate_event_result(result, 1)
        self.assertNotIn(SECRET, stdout.getvalue())
        native.assert_called_once()

    def test_native_fixed_origin_closes_connection_and_does_not_read_error_body(self):
        connection, response = MagicMock(), MagicMock()
        connection.getresponse.return_value = response
        response.status = 401
        response.getheaders.return_value = [("content-type", "application/json")]
        with patch.object(events.http.client, "HTTPSConnection", return_value=connection) as factory:
            self.assertEqual(events._native(events.ENDPOINT, {}, b"[]", 10), (401, {"content-type": "application/json"}, b""))
        factory.assert_called_once_with("api.raindrop.ai", timeout=10)
        connection.request.assert_called_once_with("POST", "/v1/events/track", body=b"[]", headers={})
        connection.close.assert_called_once()
        response.read1.assert_not_called()
        with patch.object(events.http.client, "HTTPSConnection") as factory:
            for url, timeout in (("https://other.invalid", 10), (events.ENDPOINT, 11), (events.ENDPOINT, True)):
                with self.assertRaises(events.wire._TransportError):
                    events._native(url, {}, b"[]", timeout)
            factory.assert_not_called()

    def test_native_duplicate_framing_and_deadline_fail_closed(self):
        connection, response = MagicMock(), MagicMock()
        connection.getresponse.return_value = response
        response.status = 204
        response.getheaders.return_value = [("Content-Length", "0"), ("content-length", "0")]
        with patch.object(events.http.client, "HTTPSConnection", return_value=connection):
            result = events._dispatch(b"[]", 1, {}, events._native)
        self.assertEqual(result["error_code"], "MALFORMED_TRANSPORT")
        response.getheaders.return_value = []
        with patch.object(events.http.client, "HTTPSConnection", return_value=connection), \
             patch.object(events.time, "monotonic", side_effect=[1, 12]):
            result = events._dispatch(b"[]", 1, {}, events._native)
        self.assertEqual(result["error_code"], "TIMEOUT")
        response.read1.assert_not_called()


if __name__ == "__main__":
    unittest.main()
