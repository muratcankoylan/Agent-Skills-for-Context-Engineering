"""Offline cloud export wire and containment tests. No live provider access."""

import base64
from copy import deepcopy
import io
import json
import os
import subprocess
import unittest
from unittest.mock import MagicMock, patch

from researcher.service.contracts import ServiceError
from researcher.service import trace_export as export


SECRET = "fixture-credential-never-ship-as-data"
PROJECT = "research-canary"


def payload():
    return {"resourceSpans": [{"resource": {"attributes": [{"key": "service.name",
        "value": {"stringValue": "context-research-harness"}}]}, "scopeSpans": [{"scope": {
        "name": "researcher.service", "version": "1"}, "spans": [{"traceId": "a" * 32,
        "spanId": "b" * 16, "name": "workflow.execute", "kind": 1,
        "startTimeUnixNano": "1700000000000000000", "endTimeUnixNano": "1700000001000000000",
        "status": {"code": 1}, "attributes": []}]}]}]}


def spans(value):
    return value["resourceSpans"][0]["scopeSpans"][0]["spans"]


class ExportTests(unittest.TestCase):
    def test_preflight_categories_are_value_free_and_do_not_network(self):
        cases = [("", "blank", False), (None, "blank", False),
                 ("default", "explicit_default", False), ("PrivateProject", "uppercase", False),
                 ("https://private.invalid", "invalid_characters", False), ("a" * 64, "too_long", False),
                 ("private-project", "explicit_slug", True),
                 ("12345678-1234-1234-1234-123456789abc", "uuid_like_slug", True)]
        with patch.object(export, "_isolated", side_effect=AssertionError("network forbidden")):
            for value, category, ready in cases:
                with self.subTest(category=category):
                    result = export.preflight_config(credential=SECRET, project_id=value)
                    self.assertEqual((result["project_category"], result["local_ready"]), (category, ready))
                    self.assertFalse(result["network_checked"])
                    self.assertFalse(result["authentication_verified"])
                    self.assertFalse(result["project_verified"])
                    self.assertNotIn(SECRET, json.dumps(result))
                    if value and value not in {"default", ""}:
                        self.assertNotIn(value, json.dumps(result))
            for key in ("", None, False, "bad token", "line\nsecret"):
                result = export.preflight_config(credential=key, project_id=PROJECT)
                self.assertFalse(result["local_ready"])
                self.assertIn("TRACE_EXPORT_INVALID_CREDENTIAL", result["error_codes"])

    def call(self, raw=b"{}", *, status=200, headers=None, value=None):
        self.transport = MagicMock(return_value=(status, {"Content-Type": "application/json"}
            if headers is None else headers, raw))
        return export.export_payload(value if value is not None else payload(), credential=SECRET,
                                      project_id=PROJECT, transport=self.transport)

    def test_default_project_requires_exact_boolean_opt_in_and_never_fills_blank(self):
        for approval in (False, 0, 1, "true", None):
            transport = MagicMock()
            with self.assertRaises(ServiceError):
                export.export_payload(payload(), credential=SECRET, project_id="default",
                                      allow_default_project=approval, transport=transport)
            transport.assert_not_called()
        for project in (None, "", "DEFAULT", " default "):
            transport = MagicMock()
            with self.assertRaises(ServiceError):
                export.export_payload(payload(), credential=SECRET, project_id=project,
                                      allow_default_project=True, transport=transport)
            transport.assert_not_called()
        transport = MagicMock(return_value=(200, {"content-type": "application/json"}, b"{}"))
        result = export.export_payload(payload(), credential=SECRET, project_id="default",
                                       allow_default_project=True, transport=transport)
        self.assertEqual(result["status"], "exported")
        self.assertEqual(transport.call_args.args[1]["X-Raindrop-Project-Id"], "default")

    def test_default_project_opt_in_survives_isolated_boundary_and_is_revalidated(self):
        answer = json.dumps({"status": 200, "headers": {"content-type": "application/json"},
                             "body": base64.b64encode(b"{}").decode()}).encode()
        with patch.object(export.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, answer, b"")) as run:
            self.assertEqual(export.export_payload(payload(), credential=SECRET, project_id="default",
                                                  allow_default_project=True)["status"], "exported")
        packet = json.loads(run.call_args.kwargs["input"])
        self.assertIs(packet["allow_default_project"], True)
        for approval, allowed in ((True, True), (False, False), (1, False), ("true", False)):
            packet["allow_default_project"] = approval
            stdin = MagicMock()
            stdin.buffer = io.BytesIO(json.dumps(packet).encode())
            output = io.StringIO()
            with patch.object(export.sys, "stdin", stdin), patch.object(export.sys, "stdout", output), \
                 patch.object(export, "_native", return_value=(200, {"content-type": "application/json"}, b"{}")) as native:
                export._worker()
            self.assertEqual(native.call_count, int(allowed))
            self.assertNotIn(SECRET, output.getvalue())

    def test_fixed_wire_and_nonmutating_full_success(self):
        value = payload()
        original = deepcopy(value)
        result = self.call(value=value)
        self.assertEqual(result, {"schema": "trace-export-result/v1", "status": "exported",
            "attempted": True, "span_count": 1, "rejected_spans": 0, "warning": False, "error_code": None})
        url, headers, body, timeout = self.transport.call_args.args
        self.assertEqual(url, export.ENDPOINT)
        self.assertEqual(timeout, 10)
        self.assertEqual(headers, {"Content-Type": "application/json", "Accept": "application/json",
            "Accept-Encoding": "identity", "Authorization": "Bearer " + SECRET,
            "X-Raindrop-Project-Id": PROJECT})
        self.assertEqual(json.loads(body), value)
        self.assertNotIn(SECRET.encode(), body)
        self.assertEqual(value, original)
        self.transport.assert_called_once()

    def test_invalid_credentials_and_project_have_no_io(self):
        bad_credentials = ["", None, "line\nsecret", "tab\tsecret", "a b", "é", "x" * 4097]
        bad_projects = ["", None, "default", "*", "UPPER", "a/b", "a?b", "-a", "a-", "a" * 64, "a\r\nX: y"]
        for credential, project in [(value, PROJECT) for value in bad_credentials] + [(SECRET, value) for value in bad_projects]:
            with self.subTest(credential_type=type(credential).__name__, project=project):
                transport = MagicMock()
                with self.assertRaises(ServiceError) as caught:
                    export.export_payload(payload(), credential=credential, project_id=project, transport=transport)
                self.assertNotIn(SECRET, str(caught.exception))
                transport.assert_not_called()

    def test_documented_project_slug_boundaries(self):
        for project in ("0", "2nd-project", "a--b", "a" * 63):
            with self.subTest(project=project):
                transport = MagicMock(return_value=(200, {"content-type": "application/json"}, b"{}"))
                self.assertEqual(export.export_payload(payload(), credential=SECRET,
                    project_id=project, transport=transport)["status"], "exported")

    def test_closed_schema_refuses_content_before_io(self):
        variants = []
        for key in ("gen_ai.input.messages", "prompt", "http.url", "tool.arguments", "authorization"):
            value = payload()
            spans(value)[0]["attributes"] = [{"key": key, "value": {"stringValue": SECRET}}]
            variants.append(value)
        value = payload()
        spans(value)[0]["events"] = [{"name": SECRET}]
        variants.append(value)
        value = payload()
        spans(value)[0]["name"] = SECRET
        variants.append(value)
        variants.extend([{}, None, {"resourceSpans": []}])
        for value in variants:
            transport = MagicMock()
            with self.assertRaises(ServiceError):
                export.export_payload(value, credential=SECRET, project_id=PROJECT, transport=transport)
            transport.assert_not_called()

    def test_count_duplicates_and_bad_ids_are_rejected_before_io(self):
        variants = []
        for count in (0, 101):
            value = payload()
            spans(value)[:] = [{**deepcopy(spans(payload())[0]), "spanId": f"{i + 1:016x}"} for i in range(count)]
            variants.append(value)
        value = payload()
        spans(value).append(deepcopy(spans(value)[0]))
        variants.append(value)
        for field, bad in (("traceId", "0" * 32), ("spanId", "not-hex"), ("endTimeUnixNano", "1")):
            value = payload()
            spans(value)[0][field] = bad
            variants.append(value)
        for value in variants:
            transport = MagicMock()
            with self.assertRaises(ServiceError):
                export.export_payload(value, credential=SECRET, project_id=PROJECT, transport=transport)
            transport.assert_not_called()

    def test_size_and_credential_reflection_are_pre_effect(self):
        transport = MagicMock()
        with patch.object(export, "MAX_REQUEST_BYTES", 1):
            with self.assertRaisesRegex(ServiceError, "TRACE_EXPORT_INVALID_PAYLOAD"):
                export.export_payload(payload(), credential=SECRET, project_id=PROJECT, transport=transport)
        with self.assertRaisesRegex(ServiceError, "TRACE_EXPORT_CREDENTIAL_REFLECTION"):
            export.export_payload(payload(), credential="workflow.execute", project_id=PROJECT, transport=transport)
        transport.assert_not_called()

    def test_partial_and_warning_are_distinct_without_diagnostic_echo(self):
        for rejected in (1, "1"):
            result = self.call(json.dumps({"partialSuccess": {"rejectedSpans": rejected,
                "errorMessage": SECRET}}).encode())
            self.assertEqual((result["status"], result["rejected_spans"], result["warning"]), ("partial", 1, True))
            self.assertNotIn(SECRET, json.dumps(result))
            self.transport.assert_called_once()
        result = self.call(json.dumps({"partialSuccess": {"rejectedSpans": "0", "errorMessage": SECRET}}).encode())
        self.assertEqual((result["status"], result["warning"]), ("exported", True))
        self.assertNotIn(SECRET, json.dumps(result))
        for raw in (b'{"partialSuccess":{}}', b'{"partialSuccess":{"rejectedSpans":0}}'):
            self.assertEqual(self.call(raw)["status"], "exported")

    def test_malformed_ack_and_local_workshop_ack_are_unknown(self):
        values = [[], None, {"ok": True, "spansIngested": 1}, {"error": SECRET},
            {"partial_success": {}}, {"partialSuccess": None}, {"partialSuccess": []},
            {"partialSuccess": {"extra": SECRET}}, {"partialSuccess": {"errorMessage": 1}},
            {"partialSuccess": {"errorMessage": "x" * 8193}}, {"partialSuccess": {"errorMessage": "\ud800"}}]
        values += [{"partialSuccess": {"rejectedSpans": value}} for value in
                   (True, -1, 2, 0.0, "1.0", "01", "1e0", "-1", "9" * 100)]
        for data in values:
            with self.subTest(data_type=type(data).__name__):
                result = self.call(json.dumps(data).encode())
                self.assertEqual(result["error_code"], "MALFORMED_ACKNOWLEDGEMENT")
                self.assertEqual(result["status"], "unknown")
                self.transport.assert_called_once()

    def test_duplicate_keys_non_json_and_non_utf8_are_unknown(self):
        for raw in (b"", b"<html>secret</html>", b"\xff", b"{", b'{"partialSuccess":{},"partialSuccess":{}}',
                    b'{"partialSuccess":{"rejectedSpans":NaN}}', b"[" * 2000):
            result = self.call(raw)
            self.assertEqual(result["status"], "unknown")
            self.assertEqual(result["error_code"], "MALFORMED_ACKNOWLEDGEMENT")

    def test_header_framing_and_response_size(self):
        cases = [({}, "UNEXPECTED_CONTENT_TYPE"),
            ({"content-type": "text/plain"}, "UNEXPECTED_CONTENT_TYPE"),
            ({"content-type": "application/json", "content-encoding": "gzip"}, "UNEXPECTED_ENCODING"),
            ({"content-type": "application/json", "content-length": "1"}, "INVALID_RESPONSE_LENGTH"),
            ({"content-type": "application/json", "content-length": "-2"}, "INVALID_RESPONSE_LENGTH"),
            ({"content-type": "application/json", "Content-Type": "application/json"}, "MALFORMED_TRANSPORT"),
            ({"content-type": "application/json", "content-length": "2", "transfer-encoding": "chunked"}, "MALFORMED_TRANSPORT"),
            ({"content-type": "application/json", "transfer-encoding": "gzip, chunked"}, "MALFORMED_TRANSPORT"),
            ({"content-type": "application/json\r\nInjected: secret"}, "MALFORMED_TRANSPORT"),
            ({"content-type": 42}, "MALFORMED_TRANSPORT")]
        for headers, code in cases:
            with self.subTest(code=code):
                self.assertEqual(self.call(headers=headers)["error_code"], code)
        self.assertEqual(self.call(b"x" * (export.MAX_RESPONSE_BYTES + 1))["error_code"], "RESPONSE_TOO_LARGE")
        for headers in ({"content-type": "application/json; charset=utf-8", "content-length": "2"},
                        {"content-type": "application/json", "transfer-encoding": "chunked"}):
            self.assertEqual(self.call(headers=headers)["status"], "exported")

    def test_http_statuses_do_not_follow_or_retry_or_echo(self):
        for status in (301, 302, 307, 308, 400, 401, 403, 413, 429, 500, 502, 503, 504, 201, 204):
            result = self.call(SECRET.encode(), status=status, headers={"Location": "https://untrusted.invalid/" + SECRET})
            self.assertEqual(result["status"], "rejected" if 400 <= status <= 499 else "unknown")
            self.assertNotIn(SECRET, json.dumps(result))
            self.transport.assert_called_once()

    def test_bad_transport_and_exceptions_are_safe(self):
        for value in ((True, {}, b"{}"), (600, {}, b"{}"), (200, [], b"{}"), (200, {}, "{}"), (200,), None):
            transport = MagicMock(return_value=value)
            result = export.export_payload(payload(), credential=SECRET, project_id=PROJECT, transport=transport)
            self.assertEqual(result["status"], "unknown")
            transport.assert_called_once()
        for exception, code in ((RuntimeError(SECRET), "TRANSPORT_ERROR"), (TimeoutError(SECRET), "TIMEOUT")):
            transport = MagicMock(side_effect=exception)
            result = export.export_payload(payload(), credential=SECRET, project_id=PROJECT, transport=transport)
            self.assertEqual(result["error_code"], code)
            self.assertNotIn(SECRET, json.dumps(result))
            transport.assert_called_once()

    def test_isolated_worker_has_minimal_env_stdin_credentials_and_wall_limit(self):
        answer = json.dumps({"status": 200, "headers": {"content-type": "application/json"},
                             "body": base64.b64encode(b"{}").decode()}).encode()
        with patch.object(export.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, answer, b"")) as run:
            result = export.export_payload(payload(), credential=SECRET, project_id=PROJECT)
        self.assertEqual(result["status"], "exported")
        args, kwargs = run.call_args
        self.assertNotIn(SECRET, repr(args))
        self.assertNotIn(SECRET, repr(kwargs["env"]))
        self.assertEqual(set(kwargs["env"]), {"PATH", "PYTHONPATH", "PYTHONUTF8"})
        self.assertEqual(kwargs["timeout"], 10)
        self.assertIn(SECRET, kwargs["input"].decode())
        run.assert_called_once()

    def test_worker_timeout_start_failure_and_malformed_output_are_safe(self):
        for exception, code, attempted in ((subprocess.TimeoutExpired("worker", 10), "WALL_TIMEOUT", True),
                                           (OSError(SECRET), "WORKER_START_FAILED", False)):
            with patch.object(export.subprocess, "run", side_effect=exception) as run:
                result = export.export_payload(payload(), credential=SECRET, project_id=PROJECT)
            self.assertEqual((result["error_code"], result["attempted"]), (code, attempted))
            run.assert_called_once()
        for stdout, stderr in ((b"not-json", b""), (b"{}", SECRET.encode()),
                               (json.dumps({"error": SECRET}).encode(), b""),
                               (b"x" * (2 * export.MAX_RESPONSE_BYTES + 1), b"")):
            with patch.object(export.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, stdout, stderr)):
                result = export.export_payload(payload(), credential=SECRET, project_id=PROJECT)
            self.assertEqual(result["status"], "unknown")
            self.assertNotIn(SECRET, json.dumps(result))

    def test_native_connection_fixed_post_and_no_error_body_read(self):
        connection = MagicMock()
        response = connection.getresponse.return_value
        response.status = 307
        response.getheaders.return_value = [("Location", "https://untrusted.invalid/")]
        with patch.object(export.http.client, "HTTPSConnection", return_value=connection) as constructor:
            result = export._native(export.ENDPOINT, {"Authorization": "Bearer " + SECRET}, b"{}", 10)
        constructor.assert_called_once_with("api.raindrop.ai", timeout=10)
        self.assertEqual(connection.request.call_args.args[:2], ("POST", "/v1/traces"))
        self.assertEqual(result, (307, {}, b""))
        response.read1.assert_not_called()
        connection.close.assert_called_once()

    def test_native_duplicate_framing_oversize_and_deadline(self):
        for headers, clock in (([("Content-Type", "application/json"), ("content-type", "application/json")], None),
                               ([("Content-Length", str(export.MAX_RESPONSE_BYTES + 1))], None),
                               ([("Content-Type", "application/json")], [0, 11])):
            connection = MagicMock()
            response = connection.getresponse.return_value
            response.status = 200
            response.getheaders.return_value = headers
            with patch.object(export.http.client, "HTTPSConnection", return_value=connection):
                with patch.object(export.time, "monotonic", side_effect=clock) if clock else patch.object(export.time, "monotonic", return_value=0):
                    with self.assertRaises(export._TransportError):
                        export._native(export.ENDPOINT, {}, b"{}", 10)
            connection.close.assert_called_once()

    def test_native_bounded_success_and_uninterpreted_duplicate_headers(self):
        connection = MagicMock()
        response = connection.getresponse.return_value
        response.status = 200
        response.getheaders.return_value = [("Content-Type", "application/json"), ("Content-Length", "2"),
                                            ("X-Unknown", "one"), ("X-Unknown", "two")]
        response.read1.side_effect = [b"{}", b""]
        with patch.object(export.http.client, "HTTPSConnection", return_value=connection):
            self.assertEqual(export._native(export.ENDPOINT, {}, b"{}", 10)[2], b"{}")
        self.assertLessEqual(response.read1.call_args.args[0], 8192)
        connection.close.assert_called_once()

    def test_native_stream_size_limit_and_read_failure_close_connection(self):
        for chunks in ([b"x" * (export.MAX_RESPONSE_BYTES + 1)], OSError(SECRET)):
            connection = MagicMock()
            response = connection.getresponse.return_value
            response.status = 200
            response.getheaders.return_value = [("Content-Type", "application/json")]
            response.read1.side_effect = chunks
            with patch.object(export.http.client, "HTTPSConnection", return_value=connection):
                with self.assertRaises((export._TransportError, OSError)):
                    export._native(export.ENDPOINT, {}, b"{}", 10)
            connection.close.assert_called_once()

    def test_worker_invalid_input_has_no_network_and_safe_output(self):
        for packet in ({}, {"url": "https://untrusted.invalid/", "headers": {}, "body": "", "timeout": 10}):
            stdin = MagicMock()
            stdin.buffer = io.BytesIO(json.dumps(packet).encode())
            output = io.StringIO()
            with patch.object(export.sys, "stdin", stdin), patch.object(export.sys, "stdout", output), patch.object(export, "_native") as native:
                export._worker()
            native.assert_not_called()
            self.assertEqual(json.loads(output.getvalue()), {"error": "WORKER_FAILED"})

    def test_worker_revalidates_metadata_and_headers_before_io(self):
        body, _, headers = export._prepare(payload(), SECRET, PROJECT)
        for changed in ("payload", "headers"):
            packet = {"url": export.ENDPOINT, "headers": dict(headers), "body": base64.b64encode(body).decode(), "timeout": 10}
            if changed == "payload":
                value = payload()
                spans(value)[0]["events"] = [{"name": SECRET}]
                packet["body"] = base64.b64encode(json.dumps(value).encode()).decode()
            else:
                packet["headers"]["X-Unapproved"] = SECRET
            stdin = MagicMock()
            stdin.buffer = io.BytesIO(json.dumps(packet).encode())
            output = io.StringIO()
            with patch.object(export.sys, "stdin", stdin), patch.object(export.sys, "stdout", output), patch.object(export, "_native") as native:
                export._worker()
            native.assert_not_called()
            self.assertNotIn(SECRET, output.getvalue())

    def test_real_worker_rejects_foreign_origin_without_network(self):
        root = export.Path(export.__file__).resolve().parents[2]
        # Invalid origin is rejected before transport construction. This checks
        # actual module import/IPC under the production minimal environment.
        packet = {"url": "https://untrusted.invalid/", "headers": {}, "body": "", "timeout": 10}
        result = subprocess.run([os.sys.executable, "-B", "-m", "researcher.service.trace_export"],
            input=json.dumps(packet).encode(), capture_output=True, timeout=10, cwd=root, check=False,
            env={"PATH": os.defpath, "PYTHONPATH": str(root), "PYTHONUTF8": "1"})
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, b"")
        self.assertEqual(json.loads(result.stdout), {"error": "WORKER_FAILED"})


if __name__ == "__main__":
    unittest.main()
