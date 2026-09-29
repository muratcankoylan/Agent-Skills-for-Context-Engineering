"""Closed transport diagnostics, fake HTTP only; never retry unknown delivery."""
import http.client
import io
import json
from pathlib import Path
import ssl
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from researcher.service import codex_gateway as gateway
from researcher.service.contracts import ServiceError
from researcher.service.openai_campaign import initialize
from researcher.service.providers import ProviderError, _https_post
from researcher.service.tests.test_codex_campaign import task, upstream, wire

SENTINEL = "synthetic-private-error-not-for-output"
CREDENTIAL = "synthetic-transport-credential"


class GatewayTransportTests(unittest.TestCase):
    def child(self, response=None, *, error=None, packet=None, raw_input=None):
        packet = packet if packet is not None else {"body": "{}", "credential": CREDENTIAL, "timeout": 1}
        stdin = type("Input", (), {"buffer": io.BytesIO(raw_input if raw_input is not None else json.dumps(packet).encode())})()
        output = io.BytesIO()
        stdout = type("Output", (), {"buffer": output})()
        stderr = io.StringIO()
        options = {"side_effect": error} if error is not None else {"return_value": response}
        with patch.object(gateway.sys, "stdin", stdin), patch.object(gateway.sys, "stdout", stdout), \
                patch.object(gateway.sys, "stderr", stderr), \
                patch("researcher.service.providers._https_post", **options) as post:
            code = gateway._forward_child()
        self.assertEqual(stderr.getvalue(), "")
        if code:
            self.assertEqual(output.getvalue(), b"")
            self.assertIn(code, gateway.FORWARD_EXIT_CODES)
        return code, output.getvalue(), post.call_count

    def test_http_statuses_have_fixed_codes_and_no_remote_output(self):
        cases = {401: "HTTP_AUTH_REJECTED", 403: "HTTP_AUTH_REJECTED", 429: "HTTP_RATE_LIMITED",
                 400: "HTTP_CLIENT_ERROR", 404: "HTTP_CLIENT_ERROR", 499: "HTTP_CLIENT_ERROR",
                 500: "HTTP_SERVER_ERROR", 503: "HTTP_SERVER_ERROR", 599: "HTTP_SERVER_ERROR",
                 301: "HTTP_REDIRECT", 307: "HTTP_REDIRECT", 399: "HTTP_REDIRECT",
                 100: "HTTP_STATUS_UNEXPECTED", 201: "HTTP_STATUS_UNEXPECTED", 204: "HTTP_STATUS_UNEXPECTED"}
        for status, name in cases.items():
            with self.subTest(status=status):
                code, _, count = self.child((status, {"private": SENTINEL}, SENTINEL.encode()))
                self.assertEqual(gateway.FORWARD_EXIT_CODES[code], name)
                self.assertEqual(count, 1)

    def test_typed_exceptions_are_closed_and_never_reflected(self):
        cases = [(ssl.SSLError(SENTINEL), "TRANSPORT_TLS_ERROR"),
                 (TimeoutError(SENTINEL), "TRANSPORT_TIMEOUT"),
                 (ConnectionResetError(SENTINEL), "TRANSPORT_NETWORK_ERROR"),
                 (http.client.BadStatusLine(SENTINEL), "RESPONSE_FRAMING_INVALID"),
                 (http.client.IncompleteRead(SENTINEL.encode()), "RESPONSE_FRAMING_INVALID"),
                 (ProviderError("TIMEOUT", SENTINEL), "TRANSPORT_TIMEOUT"),
                 (ProviderError("MALFORMED_TRANSPORT", SENTINEL), "RESPONSE_FRAMING_INVALID"),
                 (ProviderError("RESPONSE_TOO_LARGE", SENTINEL), "RESPONSE_LIMIT"),
                 (ProviderError(SENTINEL, SENTINEL), "FORWARD_WORKER_ERROR"),
                 (RuntimeError(SENTINEL), "FORWARD_WORKER_ERROR")]
        for error, expected in cases:
            with self.subTest(expected=expected):
                code, _, count = self.child(error=error)
                self.assertEqual(gateway.FORWARD_EXIT_CODES[code], expected)
                self.assertEqual(count, 1)

    def test_strict_type_framing_and_size_refusals_are_preserved(self):
        raw = upstream()
        cases = [({}, raw, "RESPONSE_TYPE_INVALID"),
                 ({"Content-Type": "application/json"}, raw, "RESPONSE_TYPE_INVALID"),
                 ({"Content-Encoding": "gzip"}, raw, "RESPONSE_FRAMING_INVALID"),
                 ({"Content-Length": str(len(raw)), "Transfer-Encoding": "chunked"}, raw, "RESPONSE_FRAMING_INVALID"),
                 ({"Transfer-Encoding": "gzip"}, raw, "RESPONSE_FRAMING_INVALID"),
                 ({"Content-Length": "bad"}, raw, "RESPONSE_FRAMING_INVALID"),
                 ({"Content-Length": "²"}, raw, "RESPONSE_FRAMING_INVALID"),
                 ({"Content-Length": "9" * 5000}, raw, "RESPONSE_FRAMING_INVALID"),
                 ({"Content-Length": str(len(raw) + 1)}, raw, "RESPONSE_FRAMING_INVALID"),
                 ({}, b"", "RESPONSE_LIMIT"),
                 ({}, b"x" * (gateway.MAX_RESPONSE + 1), "RESPONSE_LIMIT")]
        for headers, body, expected in cases:
            selected = {"Content-Type": "text/event-stream", **headers}
            if headers == {} and body == raw:
                selected = {}
            with self.subTest(expected=expected, headers=headers):
                code, _, count = self.child((200, selected, body))
                self.assertEqual(gateway.FORWARD_EXIT_CODES[code], expected)
                self.assertEqual(count, 1)

    def test_valid_sse_is_unchanged(self):
        raw = upstream()
        for framing in ({"Content-Length": str(len(raw))}, {"Transfer-Encoding": "chunked"}, {}):
            code, output, count = self.child((200, {"Content-Type": "text/event-stream; charset=utf-8", **framing}, raw))
            self.assertEqual((code, output, count), (0, raw, 1))

    def test_invalid_worker_input_never_dispatches(self):
        base = {"body": "{}", "credential": CREDENTIAL, "timeout": 1}
        invalid = [{}, {**base, "extra": SENTINEL}, {**base, "body": None}, {**base, "body": ""},
                   {**base, "credential": "bad\ncredential"}, {**base, "credential": "x" * 4097},
                   {**base, "timeout": True}, {**base, "timeout": 0}, {**base, "timeout": 121}]
        for packet in invalid:
            code, _, count = self.child(packet=packet)
            self.assertEqual(gateway.FORWARD_EXIT_CODES[code], "FORWARD_INPUT_INVALID")
            self.assertEqual(count, 0)
        for raw in (b"not json", b"{\"body\":1,\"body\":2}", b"x" * (gateway.MAX_REQUEST + 8193)):
            code, _, count = self.child(raw_input=raw)
            self.assertEqual(gateway.FORWARD_EXIT_CODES[code], "FORWARD_INPUT_INVALID")
            self.assertEqual(count, 0)

    def test_parent_accepts_only_silent_allowlisted_failure_codes(self):
        for code, name in gateway.FORWARD_EXIT_CODES.items():
            for stdout, stderr in ((b"", b""), (SENTINEL.encode(), b""), (b"", SENTINEL.encode())):
                result = subprocess.CompletedProcess([], code, stdout, stderr)
                with patch.object(gateway.subprocess, "run", return_value=result) as run, self.assertRaises(ServiceError) as caught:
                    gateway.forward(b"{}", credential=CREDENTIAL, timeout_seconds=1)
                expected = name if not stdout and not stderr else "WORKER_FAILED"
                self.assertEqual(caught.exception.code, "CODEX_GATEWAY_" + expected)
                self.assertNotIn(SENTINEL, str(caught.exception))
                self.assertEqual(run.call_count, 1)
        for code in (-9, 2, 19, 34, 127):
            with patch.object(gateway.subprocess, "run", return_value=subprocess.CompletedProcess([], code, b"", b"")), \
                    self.assertRaisesRegex(ServiceError, "^CODEX_GATEWAY_WORKER_FAILED$"):
                gateway.forward(b"{}", credential=CREDENTIAL)

    def test_parent_timeout_start_failure_and_invalid_input_are_safe(self):
        for error, expected in ((subprocess.TimeoutExpired([SENTINEL], 1, output=SENTINEL.encode()), "WALL_TIMEOUT"),
                                (OSError(SENTINEL), "WORKER_START_FAILED")):
            with patch.object(gateway.subprocess, "run", side_effect=error) as run, self.assertRaises(ServiceError) as caught:
                gateway.forward(b"{}", credential=CREDENTIAL)
            self.assertEqual(caught.exception.code, "CODEX_GATEWAY_" + expected)
            self.assertNotIn(SENTINEL, str(caught.exception))
            self.assertEqual(run.call_count, 1)
        with patch.object(gateway.subprocess, "run") as run, self.assertRaisesRegex(ServiceError, "FORWARD_INPUT_INVALID"):
            gateway.forward(b"{}", credential=CREDENTIAL, timeout_seconds=121)
        run.assert_not_called()

    def test_parent_success_bounds_and_deadline_do_not_change(self):
        raw = upstream()
        with patch.object(gateway.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, raw, b"")) as run:
            self.assertEqual(gateway.forward(b"{}", credential=CREDENTIAL, timeout_seconds=7), raw)
        self.assertEqual(run.call_args.kwargs["timeout"], 7)
        self.assertNotIn(CREDENTIAL, str(run.call_args.args))
        self.assertNotIn(CREDENTIAL, str(run.call_args.kwargs["env"]))
        for stdout, stderr in ((b"", b""), (raw, SENTINEL.encode()), (b"x" * (gateway.MAX_RESPONSE + 1), b"")):
            with patch.object(gateway.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, stdout, stderr)), \
                    self.assertRaisesRegex(ServiceError, "^CODEX_GATEWAY_WORKER_FAILED$"):
                gateway.forward(b"{}", credential=CREDENTIAL)

    def test_native_http_failure_does_not_read_remote_body_or_follow_redirect(self):
        for status in (301, 401, 429, 503):
            response = unittest.mock.Mock(status=status)
            response.getheaders.return_value = [("Content-Type", "application/json"), ("X-Private", SENTINEL)]
            connection = unittest.mock.Mock()
            connection.getresponse.return_value = response
            with patch("researcher.service.providers.http.client.HTTPSConnection", return_value=connection):
                actual = _https_post(gateway.ENDPOINT, {"Authorization": "Bearer " + CREDENTIAL}, b"{}", 1)
            self.assertEqual(actual, (status, {"Content-Type": "application/json"}, b""))
            self.assertEqual(connection.request.call_count, 1)
            response.read1.assert_not_called()
            connection.close.assert_called_once()

    def test_classified_failures_keep_unknown_reservation_and_cannot_redispatch(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = initialize(Path(temporary).resolve() / "authority", cap_microusd=100_000_000, prior_spend_microusd=0)
            for code, name in gateway.FORWARD_EXIT_CODES.items():
                job = "proof-" + str(code)
                store.enqueue(job, {"fixture": True})
                store.next_job(job)
                def make():
                    return gateway.Gateway(store, job, task(), credential=CREDENTIAL, now=lambda: 1790683200)
                with store.worker_lock(), patch.object(gateway.subprocess, "run",
                        return_value=subprocess.CompletedProcess([], code, b"", b"")) as run:
                    with self.assertRaises(ServiceError) as caught:
                        make().exchange(json.dumps(wire()).encode())
                    self.assertEqual(caught.exception.code, "CODEX_GATEWAY_" + name)
                    effect = store.inspect(job)["effects"][0]
                    self.assertEqual(effect["state"], "unknown")
                    self.assertGreater(effect["reserved_microusd"], 0)
                    with store._history_snapshot() as database:
                        self.assertIsNone(database.execute("SELECT output FROM effects WHERE job=?", (job,)).fetchone()[0])
                    with self.assertRaises(ServiceError):
                        make().exchange(json.dumps(wire()).encode())
                    self.assertEqual(run.call_count, 1)


if __name__ == "__main__":
    unittest.main()
