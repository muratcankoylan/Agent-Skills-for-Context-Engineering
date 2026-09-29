"""Actual loopback HTTP checks; no source, model, or GitHub execution."""

from copy import deepcopy
import http.client
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import socket
import tempfile
import threading
import unittest
from unittest.mock import patch

from researcher.service.api import handler, serve_api
from researcher.service.contracts import ServiceError
from researcher.service.demo import demo_config
from researcher.service.openai_campaign import initialize
from researcher.service.store import Store


ROOT = Path(__file__).resolve().parents[3]
TOKEN = "operator_fixture_token_never_a_real_secret_123456789"


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.config = demo_config()
        second = deepcopy(self.config["schedules"][0])
        second.update(id="second", query="How should research context retain uncertainty?")
        self.config["schedules"].append(second)
        self.store = Store(Path(self.temporary.name).resolve() / "state", self.config,
                           initialize=True)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler(self.store, ROOT, TOKEN))
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever,
                                       kwargs={"poll_interval": 0.01}, daemon=True)
        self.thread.start()
        self.addCleanup(self.close_server)

    def close_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.assertFalse(self.thread.is_alive(), "loopback server failed to stop")

    def request(self, method="GET", path="/v1/status", *, payload=None, headers=(),
                token=TOKEN, frame=True):
        body = payload if isinstance(payload, bytes) else (
            json.dumps(payload).encode() if payload is not None else b"")
        fields = list(headers)
        if token is not None:
            fields.append(("Authorization", "Bearer " + token))
        names = {key.lower() for key, _ in fields}
        if method == "POST":
            if "content-type" not in names:
                fields.append(("Content-Type", "application/json"))
            if frame and "content-length" not in names:
                fields.append(("Content-Length", str(len(body))))
        connection = http.client.HTTPConnection(*self.server.server_address, timeout=2)
        try:
            connection.putrequest(method, path)
            for key, value in fields:
                connection.putheader(key, value)
            connection.endheaders(body)
            response = connection.getresponse()
            raw = response.read()
            self.assertNotIn(TOKEN.encode(), raw)
            self.assertNotIn(self.config["models"]["researcher"]["credential_env"].encode(), raw)
            return response.status, dict(response.getheaders()), json.loads(raw)
        finally:
            connection.close()

    def test_missing_and_wrong_authorization_reject_status_and_health(self):
        for path in ("/v1/status", "/v1/runtime", "/healthz"):
            for token in (None, "wrong_token_that_must_not_be_reflected"):
                with self.subTest(path=path, token=token):
                    status, _, body = self.request(path=path, token=token)
                    self.assertEqual(status, 401)
                    self.assertEqual(body, {"error": "UNAUTHORIZED"})

    def authority_store(self):
        self.store = initialize(Path(self.temporary.name).resolve() / "authority",
            cap_microusd=100_000_000, prior_spend_microusd=0)
        # No request is in flight: route this test's existing loopback server to
        # the actual authority Store, not a mocked status method.
        self.server.RequestHandlerClass = handler(self.store, ROOT, TOKEN)

    def sdk_record(self, job, *, completed=False, provider_completed=False):
        task = {"prompt": "private-fixture-prompt-not-for-status",
                "binding": {"credential_marker": "private-fixture-credential-not-for-status"}}
        self.store.enqueue(job, {"schema": "codex-sdk-work/v1", "task": task})
        self.store.next_job(job)
        self.store.checkpoint(job, "sdk-started", task, {"fixture": True})
        self.store.checkpoint(job, "sdk-thread_started", task,
            {"thread_id": "thread_" + job, "type": "thread_started"})
        self.store.checkpoint(job, "sdk-turn_started", task,
            {"thread_id": "thread_" + job, "turn_id": "turn_" + job, "type": "turn_started"})
        if provider_completed:
            self.store.reserve(job, "sdk-response", task, model_calls=1, micros=25)
            self.store.complete_effect(job, "sdk-response",
                {"response": {"text": "private-fixture-response-not-for-status"}})
        if completed:
            self.store.checkpoint(job, "sdk-result", task,
                {"response": {"text": "private-fixture-response-not-for-status"}})
        self.store.finish(job, "execution_complete" if completed else "reconciliation_required",
            None if completed else "CODEX_TURN_OUTCOME_UNKNOWN")

    def test_authenticated_runtime_is_empty_for_non_sdk_jobs(self):
        self.store.enqueue("historical-native-job", {"schema": "historical-fixture/v1",
            "prompt": "private-fixture-prompt-not-for-status"})
        status, headers, body = self.request(path="/v1/runtime")
        self.assertEqual(status, 200)
        self.assertEqual(body["schema"], "codex-runtime-status/v1")
        self.assertEqual(body["backend"], "codex_sdk")
        self.assertEqual((body["turns"], body["completed_turns"], body["unresolved_turns"]), (0, 0, 0))
        self.assertEqual(body["jobs"], [])
        self.assertFalse(body["automatic_retry"])
        self.assertFalse(body["native_tools_enabled"])
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertNotIn("private-fixture-prompt", json.dumps(body))

    def test_runtime_distinguishes_provider_completion_from_sdk_receipt_without_content(self):
        self.authority_store()
        self.sdk_record("started")
        self.sdk_record("provider-only", provider_completed=True)
        self.sdk_record("completed", completed=True, provider_completed=True)
        status, _, body = self.request(path="/v1/runtime")
        self.assertEqual(status, 200)
        self.assertEqual((body["turns"], body["completed_turns"], body["unresolved_turns"]), (3, 1, 2))
        self.assertEqual(set(body), {"schema", "backend", "sdk_version", "policy", "turns",
            "completed_turns", "unresolved_turns", "jobs", "automatic_retry", "native_tools_enabled"})
        jobs = {row["job_id"]: row for row in body["jobs"]}
        for name, row in jobs.items():
            self.assertEqual(set(row), {"job_id", "backend", "status", "reason", "started",
                "receipt_available", "unresolved", "thread_id", "turn_id", "remote_stop_confirmed"})
            self.assertTrue(row["started"])
            self.assertEqual(row["receipt_available"], name == "completed")
            self.assertEqual(row["unresolved"], name != "completed")
            self.assertEqual(row["thread_id"], "thread_" + name)
            self.assertEqual(row["turn_id"], "turn_" + name)
            self.assertFalse(row["remote_stop_confirmed"])
        for private in ("private-fixture-prompt", "private-fixture-credential", "private-fixture-response",
                        str(self.temporary.name)):
            self.assertNotIn(private, json.dumps(body))

    def test_authority_rejects_generic_job_submission_without_mutation(self):
        self.authority_store()
        before = self.store.status()
        status, _, body = self.request("POST", "/v1/jobs", payload={
            "schedule": "demo", "operation_id": "must-not-admit-sdk-job"})
        self.assertEqual((status, body), (400, {"error": "SOURCE_ADMISSION_API_REQUIRED"}))
        self.assertEqual(self.store.status(), before)

    def test_sdk_authority_pause_resume_preserves_runtime_liability_summary(self):
        self.authority_store()
        self.sdk_record("unknown", provider_completed=True)
        self.store.enqueue("queued-sdk-job", {"schema": "codex-sdk-work/v1", "task": {}})
        before_runtime = self.request(path="/v1/runtime")[2]
        before_usage = self.store.status()["usage"]
        for paused in (True, False):
            status, _, body = self.request("POST", "/v1/pause", payload={"paused": paused})
            self.assertEqual(status, 200)
            self.assertEqual(body["schema"], "research-service-status/v1")
            self.assertEqual(body["paused"], paused)
            self.assertEqual(body["usage"], before_usage)
            self.assertEqual(self.request(path="/healthz")[2], {"alive": True, "paused": paused})
            self.assertEqual(self.request(path="/v1/runtime")[2], before_runtime)
            if paused:
                self.assertIsNone(self.store.next_job("queued-sdk-job"))
        self.assertIsNotNone(self.store.next_job("queued-sdk-job"))
        self.assertEqual(self.store.inspect("unknown")["job"]["status"], "reconciliation_required")

    def test_authenticated_status_has_only_operational_summary(self):
        status, headers, body = self.request()
        self.assertEqual(status, 200)
        self.assertEqual(set(body), {"schema", "production_ready", "paused", "jobs", "usage", "last_event"})
        self.assertEqual(body["schema"], "research-service-status/v1")
        self.assertIs(body["production_ready"], False)
        self.assertIs(body["paused"], False)
        self.assertEqual(body["jobs"], [])
        self.assertEqual(body["usage"], [])
        self.assertEqual(body["last_event"], 0)
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        self.assertIn("default-src 'none'", headers["Content-Security-Policy"])
        self.assertFalse(any(name.lower().startswith("access-control-") for name in headers))
        self.assertNotIn("Set-Cookie", headers)

    def test_authenticated_health_is_not_production_readiness(self):
        status, _, body = self.request(path="/healthz")
        self.assertEqual(status, 200)
        self.assertEqual(body, {"alive": True, "paused": False})

    def test_origin_is_denied_even_with_correct_token(self):
        for method, path, payload in (("GET", "/v1/status", None),
                                      ("POST", "/v1/pause", {"paused": True})):
            with self.subTest(method=method):
                status, headers, body = self.request(method, path, payload=payload,
                                                     headers=[("Origin", "https://example.invalid")])
                self.assertEqual(status, 403)
                self.assertEqual(body, {"error": "DIRECT_BROWSER_OR_STREAMING_DENIED"})
                self.assertFalse(any(name.lower().startswith("access-control-") for name in headers))
        self.assertIs(self.store.status()["paused"], False)

    def test_duplicate_authorization_is_not_last_header_wins(self):
        for value in ("Bearer " + TOKEN, "Bearer wrong"):
            with self.subTest(value=value):
                status, _, body = self.request(headers=[("Authorization", value)])
                self.assertEqual(status, 401)
                self.assertEqual(body, {"error": "UNAUTHORIZED"})

    def test_transfer_encoding_is_denied_before_reading_body(self):
        for method, path in (("GET", "/v1/status"), ("POST", "/v1/pause")):
            with self.subTest(method=method):
                status, _, body = self.request(method, path, frame=False,
                                              headers=[("Transfer-Encoding", "chunked")])
                self.assertEqual(status, 403)
                self.assertEqual(body, {"error": "DIRECT_BROWSER_OR_STREAMING_DENIED"})

    def test_pause_resume_controls_admission_and_worker_selection(self):
        self.assertEqual(self.request("POST", "/v1/jobs", payload={
            "schedule": "demo", "operation_id": "queued-before-pause"})[0], 202)
        status, _, body = self.request("POST", "/v1/pause", payload={"paused": True})
        self.assertEqual(status, 200)
        self.assertIs(body["paused"], True)
        self.assertIsNone(self.store.next_job())
        status, _, body = self.request("POST", "/v1/jobs", payload={
            "schedule": "demo", "operation_id": "blocked-while-paused"})
        self.assertEqual(status, 400)
        self.assertEqual(body, {"error": "ADMISSION_PAUSED"})
        self.assertEqual(len(self.store.status()["jobs"]), 1)
        status, _, body = self.request("POST", "/v1/pause", payload={"paused": False})
        self.assertEqual(status, 200)
        self.assertIs(body["paused"], False)
        status, _, body = self.request("POST", "/v1/jobs", payload={
            "schedule": "demo", "operation_id": "blocked-while-paused"})
        self.assertEqual((status, body), (202, {"admitted": True}))
        self.assertIsNotNone(self.store.next_job())
        self.assertEqual(self.store.status()["usage"], [])

    def test_configured_enqueue_is_idempotent_without_executing_effects(self):
        request = {"schedule": "demo", "operation_id": "same-operation"}
        for admitted in (True, False):
            status, _, body = self.request("POST", "/v1/jobs", payload=request)
            self.assertEqual(status, 202)
            self.assertEqual(body, {"admitted": admitted})
        state = self.store.status()
        self.assertEqual(len(state["jobs"]), 1)
        self.assertEqual(state["jobs"][0]["id"], "api:same-operation")
        self.assertEqual(state["jobs"][0]["status"], "queued")
        self.assertEqual(state["usage"], [])

    def test_changed_operation_identity_cannot_replace_existing_schedule(self):
        self.assertEqual(self.request("POST", "/v1/jobs", payload={
            "schedule": "demo", "operation_id": "same-operation"})[0], 202)
        status, _, body = self.request("POST", "/v1/jobs", payload={
            "schedule": "second", "operation_id": "same-operation"})
        self.assertEqual(status, 400)
        self.assertEqual(body, {"error": "JOB_IDENTITY_COLLISION"})
        self.assertEqual(len(self.store.status()["jobs"]), 1)
        saved = json.loads(self.store.inspect("api:same-operation")["job"]["manifest"])
        self.assertEqual(saved["schedule"]["id"], "demo")

    def test_unknown_schedule_and_invalid_operation_are_not_admitted(self):
        cases = [({"schedule": "unknown", "operation_id": "op"}, "UNKNOWN_SCHEDULE"),
                 ({"schedule": "demo", "operation_id": "../escape"}, "INVALID_OPERATION_ID"),
                 ({"schedule": "demo", "operation_id": True}, "INVALID_OPERATION_ID")]
        for payload, error in cases:
            with self.subTest(payload=payload):
                status, _, body = self.request("POST", "/v1/jobs", payload=payload)
                self.assertEqual(status, 400)
                self.assertEqual(body, {"error": error})
        self.assertEqual(self.store.status()["jobs"], [])

    def test_extra_fields_unknown_routes_and_non_boolean_pause_are_rejected(self):
        for path, payload in (("/v1/pause", {"paused": True, "extra": True}),
                              ("/v1/jobs", {"schedule": "demo", "operation_id": "op", "query": "override"}),
                              ("/v1/unknown", {})):
            with self.subTest(path=path):
                self.assertEqual(self.request("POST", path, payload=payload)[0], 404)
        status, _, body = self.request("POST", "/v1/pause", payload={"paused": 1})
        self.assertEqual((status, body), (400, {"error": "INVALID_PAUSE"}))
        self.assertIs(self.store.status()["paused"], False)
        self.assertEqual(self.store.status()["jobs"], [])

    def test_strict_json_and_utf8_fail_without_state_changes(self):
        for payload, expected in ((b'{"paused":true,"paused":false}', 400),
                                  (b'{"paused":NaN}', 400), (b'{"paused":', 400),
                                  (b'\xff', 400), (b'[]', 404)):
            with self.subTest(payload=payload):
                status, _, _ = self.request("POST", "/v1/pause", payload=payload)
                self.assertEqual(status, expected)
        self.assertIs(self.store.status()["paused"], False)

    def test_invalid_framing_is_rejected_without_waiting_for_unprovided_body(self):
        cases = [[], [("Content-Length", "4097")], [("Content-Length", "-1")],
                 [("Content-Length", "2"), ("Content-Length", "2")],
                 [("Content-Length", "0"), ("Content-Type", "text/plain")]]
        for headers in cases:
            with self.subTest(headers=headers):
                status, _, body = self.request("POST", "/v1/pause", headers=headers, frame=False)
                self.assertEqual((status, body), (400, {"error": "INVALID_REQUEST"}))

    def test_truncated_request_half_close_returns_error_without_timeout(self):
        # Half-close supplies EOF immediately, rather than sleeping for the
        # handler deadline or leaving a blocked request thread during cleanup.
        with socket.create_connection(self.server.server_address, timeout=2) as connection:
            request = ("POST /v1/pause HTTP/1.1\r\nHost: 127.0.0.1\r\n"
                       f"Authorization: Bearer {TOKEN}\r\n"
                       "Content-Type: application/json\r\nContent-Length: 20\r\n\r\n{")
            connection.sendall(request.encode())
            connection.shutdown(socket.SHUT_WR)
            response = http.client.HTTPResponse(connection)
            try:
                response.begin()
                raw = response.read()
                self.assertEqual(response.status, 400)
                self.assertEqual(json.loads(raw), {"error": "INCOMPLETE_REQUEST"})
                self.assertNotIn(TOKEN.encode(), raw)
            finally:
                response.close()
        self.assertIs(self.store.status()["paused"], False)

    def test_serve_preflight_rejects_public_ingress_before_socket_creation(self):
        with patch("researcher.service.api.ThreadingHTTPServer") as server:
            for host, port in (("0.0.0.0", 8787), ("example.invalid", 8787),
                               ("::", 8787), ("127.0.0.1", 0), ("localhost", 65536)):
                with self.subTest(host=host, port=port):
                    with self.assertRaisesRegex(ServiceError, "LOOPBACK_INGRESS_REQUIRED"):
                        serve_api(self.store, ROOT, host, port, TOKEN)
            server.assert_not_called()

    def test_serve_preflight_rejects_weak_token_before_socket_creation(self):
        with patch("researcher.service.api.ThreadingHTTPServer") as server:
            for token in ("", "short", "x" * 31, "x" * 257, "x" * 31 + "!"):
                with self.subTest(token_length=len(token)):
                    with self.assertRaisesRegex(ServiceError, "STRONG_OPERATOR_TOKEN_REQUIRED"):
                        serve_api(self.store, ROOT, "127.0.0.1", 8787, token)
            server.assert_not_called()


if __name__ == "__main__":
    unittest.main()
