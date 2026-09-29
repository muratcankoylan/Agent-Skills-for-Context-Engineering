"""Offline managed Agents API wire contracts; no model availability or cost claim."""

import base64
import io
import json
import os
from pathlib import Path
import subprocess
import traceback
import unittest
from unittest.mock import MagicMock, patch

from researcher.service.openai_agents import AgentsClient, AgentsError, BASE_URL, MAX_BYTES, _native


SECRET = "fixture-secret"
SESSION = "sess_fixture"
TURN = "turn_fixture"


def request():
    return {"environment": {"type": "none"},
            "agent": {"model": "gpt-fixture-2026-09-10", "instructions": "Research boundary", "tools": [],
                      "multi_agent": {"enabled": False}}, "input": "Research α", "stream": False}


def session(**changes):
    return {"object": "agent.session", "id": SESSION, "status": "idle", "error": None,
            "created_at": 1, "last_active_at": 2, "metadata": {}, "required_actions": [], "usage": None,
            "environment": {"type": "none"},
            "agent": {"id": "agent_fixture", "model": "gpt-fixture-2026-09-10"}, **changes}


def turn(**changes):
    return {"object": "agent.session.turn", "id": TURN, "session_id": SESSION, "agent_id": "agent_fixture",
            "created_at": 1, "started_at": 1, "completed_at": 2, "subagent_id": None, "error": None,
            "status": "completed", "usage": None, **changes}


def item(**changes):
    return {"type": "message", "id": "msg_fixture", "turn_id": TURN, "role": "assistant",
            "phase": "final_answer", "status": "completed", "content": [{"type": "output_text", "text": "Result α"}],
            **changes}


def page(*rows, has_more=False):
    return {"object": "list", "data": list(rows), "first_id": rows[0]["id"] if rows else None,
            "last_id": rows[-1]["id"] if rows else None, "has_more": has_more}


def usage():
    return {"input_tokens": 11, "input_tokens_details": {"cached_tokens": 3},
            "output_tokens": 7, "output_tokens_details": {"reasoning_tokens": 2}, "total_tokens": 18}


class AgentsClientTests(unittest.TestCase):
    def client(self, data=None, *, raw=None, status=200, headers=None):
        body = raw if raw is not None else json.dumps(session() if data is None else data).encode()
        self.transport = MagicMock(return_value=(status, {"Content-Type": "application/json"} if headers is None else headers, body))
        return AgentsClient(SECRET, self.transport, timeout_seconds=20)

    def assert_error(self, code, call, *, ambiguous=True, calls=1):
        with self.assertRaises(AgentsError) as caught:
            call()
        self.assertEqual(caught.exception.code, code)
        self.assertIs(caught.exception.ambiguous, ambiguous)
        self.assertNotIn(SECRET, str(caught.exception))
        self.assertNotIn(SECRET, "".join(traceback.format_exception(caught.exception)))
        self.assertEqual(self.transport.call_count, calls)

    def test_create_native_session_not_responses_no_guessed_limits(self):
        client = self.client()
        self.assertEqual(client.create(request()), session())
        method, url, headers, body, timeout = self.transport.call_args.args
        self.assertEqual((method, url, timeout), ("POST", BASE_URL, 20))
        self.assertEqual(headers["Authorization"], "Bearer " + SECRET)
        self.assertEqual(headers["OpenAI-Beta"], "agents=v1")
        self.assertNotIn("Idempotency-Key", headers)
        self.assertEqual(json.loads(body), request())
        self.assertNotIn(SECRET, body.decode())
        self.assertNotIn(SECRET, repr(client))
        self.assertEqual(self.transport.call_count, 1)

    def test_agent_id_reference_is_supported_without_model_override(self):
        payload = {"environment": {"type": "none"}, "agent_id": "agent_saved", "input": "Research"}
        self.client().create(payload)
        self.assertEqual(json.loads(self.transport.call_args.args[3]), payload)

    def test_create_accepts_http_201_once(self):
        client = self.client(status=201)
        self.assertEqual(client.create(request()), session())
        self.assertEqual(self.transport.call_count, 1)

    def test_http_201_is_not_success_for_retrieval_or_cancellation(self):
        self.assert_error("HTTP_ERROR", lambda: self.client(status=201).retrieve(SESSION), ambiguous=False)
        self.assert_error("HTTP_ERROR", lambda: self.client(status=201).cancel(SESSION, "op-1"))

    def test_retrieve_checks_identity_and_preserves_nullable_usage(self):
        self.assertIsNone(self.client().retrieve(SESSION)["usage"])
        method, url, _, body, _ = self.transport.call_args.args
        self.assertEqual((method, url, body), ("GET", BASE_URL + "/" + SESSION, None))
        client = self.client(session(id="sess_other"))
        self.assert_error("SESSION_ID_MISMATCH", lambda: client.retrieve(SESSION), ambiguous=False)

    def test_failed_session_is_not_http_error_or_successful_turn(self):
        data = session(status="failed", error="Provider failed")
        self.assertEqual(self.client(data).retrieve(SESSION), data)

    def test_turn_contract_keeps_root_subagents_and_nullable_usage(self):
        rows = page(turn(), turn(id="turn_sub", subagent_id="sub_fixture", status="cancelled", usage=usage()))
        self.assertEqual(self.client(rows).turns(SESSION, after="turn_before"), rows)
        self.assertEqual(self.transport.call_args.args[1], BASE_URL + "/" + SESSION + "/turns?limit=100&order=asc&after=turn_before")

    def test_items_returns_original_page_cursors_no_undocumented_filter(self):
        rows = page(item(turn_id="turn_other"), item(id="msg_second"), has_more=True)
        self.assertEqual(self.client(rows).items(SESSION, TURN), rows)
        self.assertEqual(self.transport.call_args.args[1], BASE_URL + "/" + SESSION + "/items?limit=100&order=asc")
        self.assertEqual(self.client(page()).items(SESSION, TURN), page())

    def test_legacy_user_message_null_id_and_opaque_tool_items(self):
        rows = page(item(id=None, role="user", phase=None, content=[{"type": "input_text", "text": "Question"}]),
                    {"type": "function_call", "id": "call_fixture", "turn_id": TURN, "arguments": {"untrusted": True}})
        self.assertEqual(self.client(rows).items(SESSION, TURN), rows)

    def test_cancel_uses_documented_event_and_header_not_turn_id(self):
        for status in (200, 202, 204):
            with self.subTest(status=status):
                client = self.client(status=status, raw=b"", headers={})
                self.assertIsNone(client.cancel(SESSION, "cancel-job-1"))
                method, url, headers, body, _ = self.transport.call_args.args
                self.assertEqual((method, url), ("POST", BASE_URL + "/" + SESSION + "/events"))
                self.assertEqual(headers["Idempotency-Key"], "cancel-job-1")
                self.assertEqual(json.loads(body), {"events": [{"type": "agent.session.input.cancel"}]})
                self.assertEqual(self.transport.call_count, 1)

    def test_cancel_rejects_unexpected_body(self):
        client = self.client({"cancelled": True})
        self.assert_error("UNEXPECTED_CANCEL_RESPONSE", lambda: client.cancel(SESSION, "op-1"))
        client = self.client({}, status=204)
        self.assert_error("MALFORMED_TRANSPORT", lambda: client.cancel(SESSION, "op-1"))

    def test_invalid_credentials_and_timeouts_never_dispatch(self):
        self.client()
        for credential in (None, "", "a\nb", "a b", "é", "x" * 4097):
            with self.subTest(credential_type=type(credential).__name__):
                self.assert_error("INVALID_CREDENTIAL", lambda: AgentsClient(credential, self.transport), ambiguous=False, calls=0)
        for timeout in (False, 0, 301, 1.2, "20"):
            self.assert_error("INVALID_TIMEOUT", lambda: AgentsClient(SECRET, self.transport, timeout), ambiguous=False, calls=0)

    def test_invalid_ids_cursors_and_operation_keys_never_dispatch(self):
        for identifier in (None, "", "../sess", "sess/a", "sess?x=1", "https://example.com", "a" * 201, []):
            client = self.client()
            self.assert_error("INVALID_IDENTIFIER", lambda: client.retrieve(identifier), ambiguous=False, calls=0)
            self.assert_error("INVALID_IDENTIFIER", lambda: client.items(SESSION, identifier), ambiguous=False, calls=0)
        for cursor in ("../cursor", False, []):
            client = self.client()
            self.assert_error("INVALID_IDENTIFIER", lambda: client.turns(SESSION, cursor), ambiguous=False, calls=0)
        for key in (None, "", "line\nbreak", "key space", "x" * 257):
            client = self.client()
            self.assert_error("INVALID_OPERATION_KEY", lambda: client.cancel(SESSION, key), ambiguous=False, calls=0)

    def test_invalid_create_shapes_and_aliases_have_no_effect(self):
        payloads = [[], {**request(), "max_tokens": 20}, {**request(), "budget": 1},
                    {**request(), "stream": True}, {**request(), "input": False},
                    {**request(), "environment": {"type": []}},
                    {**request(), "agent": {"model": "gpt-fixture", "max_turns": 2}}]
        for payload in payloads:
            client = self.client()
            self.assert_error("INVALID_CREATE_REQUEST", lambda: client.create(payload), ambiguous=False, calls=0)
        for model in ("latest", "gpt-latest", "gpt-auto", "default"):
            payload = request()
            payload["agent"]["model"] = model
            client = self.client()
            self.assert_error("INVALID_MODEL", lambda: client.create(payload), ambiguous=False, calls=0)
        payload = request()
        del payload["input"]
        client = self.client()
        self.assert_error("INITIAL_INPUT_REQUIRED", lambda: client.create(payload), ambiguous=False, calls=0)

    def test_request_size_complexity_and_non_json_are_preflight_errors(self):
        nested = {}
        for _ in range(66):
            nested = {"nested": nested}
        cases = [("REQUEST_TOO_LARGE", "x" * MAX_BYTES), ("JSON_COMPLEXITY_LIMIT", nested),
                 ("MALFORMED_JSON", float("nan")), ("MALFORMED_JSON", object()),
                 ("MALFORMED_JSON", "\ud800"), ("MALFORMED_JSON", {1: "non-string key"})]
        for code, value in cases:
            payload = request()
            payload["metadata"] = {"entry": value}
            client = self.client()
            self.assert_error(code, lambda: client.create(payload), ambiguous=False, calls=0)

    def test_request_credential_reflection_values_keys_and_operation_key(self):
        for metadata in ({"key": SECRET}, {SECRET: "value"}):
            client = self.client()
            self.assert_error("CREDENTIAL_REFLECTION", lambda: client.create({**request(), "metadata": metadata}), ambiguous=False, calls=0)
        client = self.client()
        self.assert_error("CREDENTIAL_REFLECTION", lambda: client.cancel(SESSION, SECRET), ambiguous=False, calls=0)

    def test_session_id_credential_reflection_never_enters_url(self):
        for identifier in (SECRET, "sess_" + SECRET):
            client = self.client()
            self.assert_error("CREDENTIAL_REFLECTION", lambda: client.retrieve(identifier), ambiguous=False, calls=0)
            self.assert_error("CREDENTIAL_REFLECTION", lambda: client.turns(identifier), ambiguous=False, calls=0)
            self.assert_error("CREDENTIAL_REFLECTION", lambda: client.items(identifier, TURN), ambiguous=False, calls=0)

    def test_cursor_credential_reflection_never_enters_url(self):
        for cursor in (SECRET, "cursor_" + SECRET):
            client = self.client()
            self.assert_error("CREDENTIAL_REFLECTION", lambda: client.turns(SESSION, cursor), ambiguous=False, calls=0)
            self.assert_error("CREDENTIAL_REFLECTION", lambda: client.items(SESSION, TURN, cursor), ambiguous=False, calls=0)

    def test_cancel_session_credential_reflection_is_known_not_dispatched(self):
        for identifier in (SECRET, "sess_" + SECRET):
            client = self.client()
            self.assert_error("CREDENTIAL_REFLECTION", lambda: client.cancel(identifier, "op-1"), ambiguous=False, calls=0)

    def test_http_errors_are_safe_conservative_and_never_retried(self):
        for status, code in ((302, "REDIRECT_REFUSED"), (401, "AUTH_ERROR"), (403, "AUTH_ERROR"),
                             (429, "RATE_OR_SPEND_LIMIT"), (500, "HTTP_ERROR"), (202, "HTTP_ERROR")):
            client = self.client(raw=SECRET.encode(), status=status, headers={"Location": "https://untrusted.example"})
            self.assert_error(code, lambda: client.create(request()))
            client = self.client(raw=SECRET.encode(), status=status)
            self.assert_error(code, lambda: client.retrieve(SESSION), ambiguous=False)

    def test_transport_exception_and_timeout_have_ambiguous_writes_only(self):
        for error, code in ((RuntimeError(SECRET), "TRANSPORT_ERROR"), (TimeoutError(SECRET), "TIMEOUT")):
            for method in ("create", "retrieve", "cancel"):
                client = self.client()
                self.transport.side_effect = error
                call = {"create": lambda: client.create(request()), "retrieve": lambda: client.retrieve(SESSION),
                        "cancel": lambda: client.cancel(SESSION, "op-1")}[method]
                self.assert_error(code, call, ambiguous=method != "retrieve")

    def test_invalid_transport_types_and_size(self):
        for result in ((True, {}, b"{}"), (200, [], b"{}"), (200, {}, "{}"),
                       (200, {"Content-Type": 1}, b"{}"), (200, {"Content-Type": "application/json", "content-type": "application/json"}, b"{}")):
            client = self.client()
            self.transport.return_value = result
            self.assert_error("MALFORMED_TRANSPORT", lambda: client.create(request()))
        client = self.client(raw=b"x" * (MAX_BYTES + 1))
        self.assert_error("RESPONSE_TOO_LARGE", lambda: client.create(request()))

    def test_content_type_encoding_and_framing(self):
        for headers, code in (({}, "UNEXPECTED_CONTENT_TYPE"), ({"Content-Type": "text/html"}, "UNEXPECTED_CONTENT_TYPE"),
                              ({"Content-Encoding": "gzip"}, "UNEXPECTED_ENCODING"),
                              ({"Content-Length": "1"}, "TRUNCATED_RESPONSE"),
                              ({"Content-Length": "-2"}, "TRUNCATED_RESPONSE"),
                              ({"Transfer-Encoding": "gzip"}, "MALFORMED_TRANSPORT"),
                              ({"Transfer-Encoding": "chunked", "Content-Length": "2"}, "MALFORMED_TRANSPORT")):
            client = self.client(raw=b"{}", headers=headers)
            self.assert_error(code, lambda: client.create(request()))

    def test_strict_json_duplicate_keys_nonfinite_surrogates_and_truncation(self):
        for raw in (b'{"id":1,"id":2}', b'{"x":NaN}', b'{"x":Infinity}', b'{"x":1e999}',
                    b'{"x":"\\ud800"}', b'{"x":', b'[]', b'null', b'\xff', b'{}{}'):
            client = self.client(raw=raw)
            self.assert_error("MALFORMED_JSON", lambda: client.create(request()))

    def test_response_reflection_raw_escaped_keys_and_headers(self):
        escaped = "".join("\\u%04x" % ord(char) for char in SECRET)
        for raw in (json.dumps({"token": SECRET}).encode(), ('{"token":"' + escaped + '"}').encode(),
                    ('{"' + escaped + '":"value"}').encode()):
            client = self.client(raw=raw)
            self.assert_error("CREDENTIAL_REFLECTION", lambda: client.create(request()))
        client = self.client(headers={"X-Reflected": SECRET})
        self.assert_error("CREDENTIAL_REFLECTION", lambda: client.create(request()))

    def test_api_error_object_is_not_a_session(self):
        client = self.client({"error": {"code": "project_spend_limit_exceeded"}})
        self.assert_error("API_RESPONSE_ERROR", lambda: client.create(request()))

    def test_invalid_session_shapes_are_typed_errors(self):
        cases = [session(status=[]), session(environment={"type": []}), session(agent=[]),
                 session(metadata=[]), session(required_actions={}), session(error={}),
                 session(created_at=True), session(required_actions=[{"type": "unknown"}])]
        for data in cases:
            client = self.client(data)
            self.assert_error("MALFORMED_SESSION", lambda: client.retrieve(SESSION), ambiguous=False)
        client = self.client(session(environment={"type": "openai_hosted"}))
        self.assert_error("INVALID_IDENTIFIER", lambda: client.create(request()))

    def test_create_malformed_usage_retains_safe_session_id_for_recovery(self):
        for status in (200, 201):
            with self.subTest(status=status):
                client = self.client(session(usage={}), status=status)
                with self.assertRaises(AgentsError) as caught:
                    client.create(request())
                self.assertEqual(caught.exception.code, "MALFORMED_USAGE")
                self.assertEqual(caught.exception.session_id, SESSION)
                self.assertTrue(caught.exception.ambiguous)
                self.assertNotIn(SESSION, str(caught.exception))
                self.assertEqual(self.transport.call_count, 1)

    def test_create_never_retains_reflected_or_invalid_session_identity(self):
        for data in (session(id="../unsafe"), session(id=SECRET), session(metadata={"reflected": SECRET}),
                     session(object="wrong", usage={})):
            client = self.client(data)
            with self.assertRaises(AgentsError) as caught:
                client.create(request())
            self.assertIsNone(caught.exception.session_id)
            self.assertNotIn(SECRET, str(caught.exception))
            self.assertEqual(self.transport.call_count, 1)

    def test_required_actions_remain_visible_to_coordinator(self):
        actions = [{"type": "function_call", "call_id": "call_fixture", "name": "lookup", "turn_id": TURN, "arguments": {}},
                   {"type": "environment_connection", "environment_id": "env_fixture"}]
        self.assertEqual(self.client(session(status="requires_action", required_actions=actions)).retrieve(SESSION)["required_actions"], actions)

    def test_usage_is_validated_not_invented_from_null(self):
        self.assertEqual(self.client(session(usage=usage())).retrieve(SESSION)["usage"], usage())
        cases = [[], {}, {**usage(), "input_tokens": True}, {**usage(), "total_tokens": 19},
                 {**usage(), "output_tokens_details": {"reasoning_tokens": 8}},
                 {**usage(), "input_tokens_details": {"cached_tokens": -1}}]
        for value in cases:
            client = self.client(page(turn(usage=value)))
            self.assert_error("MALFORMED_USAGE", lambda: client.turns(SESSION), ambiguous=False)

    def test_invalid_turn_linkage_status_and_error(self):
        for row in (turn(session_id="sess_other"), turn(status=[]), turn(status="idle"),
                    turn(started_at=False), turn(error={"message": 123}), turn(created_at=-1)):
            client = self.client(page(row))
            self.assert_error("MALFORMED_TURN", lambda: client.turns(SESSION), ambiguous=False)

    def test_invalid_item_shapes(self):
        for row in (item(role=[]), item(phase=[]), item(status="failed"), item(content={}),
                    item(content=[{"type": [], "text": "unsafe"}]), item(content=[{"type": "output_text", "text": 1}])):
            client = self.client(page(row))
            self.assert_error("MALFORMED_ITEM", lambda: client.items(SESSION, TURN), ambiguous=False)

    def test_page_invariants_and_cursor_progress(self):
        cases = [{**page(turn()), "has_more": 1}, {**page(turn()), "last_id": "turn_other"},
                 page(turn(), turn()), page(has_more=True), page(*[turn(id=f"turn_{index}") for index in range(101)])]
        for data in cases:
            client = self.client(data)
            self.assert_error("MALFORMED_PAGE", lambda: client.turns(SESSION), ambiguous=False)
        client = self.client(page(turn(), has_more=True))
        self.assert_error("PAGINATION_NOT_ADVANCING", lambda: client.turns(SESSION, after=TURN), ambiguous=False)


class IsolatedTransportTests(unittest.TestCase):
    def test_worker_credentials_stay_out_of_argv_and_ambient_environment(self):
        body = json.dumps(session()).encode()
        answer = json.dumps({"status": 200, "headers": {"Content-Type": "application/json"},
                             "body": base64.b64encode(body).decode()}).encode()
        with patch("researcher.service.openai_agents.subprocess.run", return_value=subprocess.CompletedProcess([], 0, answer, b"")) as run:
            result = AgentsClient(SECRET).retrieve(SESSION)
        self.assertEqual(result, session())
        args, kwargs = run.call_args
        self.assertNotIn(SECRET, repr(args))
        self.assertEqual(set(kwargs["env"]), {"PATH", "PYTHONPATH", "PYTHONUTF8"})
        self.assertEqual(kwargs["timeout"], 30)
        self.assertIn(SECRET, kwargs["input"].decode())
        self.assertEqual(run.call_count, 1)

    def test_wall_timeout_is_fail_closed_without_retry(self):
        with patch("researcher.service.openai_agents.subprocess.run", side_effect=subprocess.TimeoutExpired("worker", 1)) as run:
            with self.assertRaises(AgentsError) as caught:
                AgentsClient(SECRET, timeout_seconds=1).create(request())
        self.assertEqual(caught.exception.code, "WALL_TIMEOUT")
        self.assertTrue(caught.exception.ambiguous)
        self.assertEqual(run.call_count, 1)

    def test_worker_start_failure_is_known_not_dispatched(self):
        with patch("researcher.service.openai_agents.subprocess.run", side_effect=OSError(SECRET)):
            with self.assertRaises(AgentsError) as caught:
                AgentsClient(SECRET).create(request())
        self.assertEqual(caught.exception.code, "WORKER_START_FAILED")
        self.assertFalse(caught.exception.ambiguous)
        self.assertNotIn(SECRET, str(caught.exception))

    def test_worker_corrupt_or_noisy_output_is_not_returned(self):
        for stdout, stderr in ((b"[]", b""), (b"{}", b""), (b"", SECRET.encode()), (b"x" * (2 * MAX_BYTES + 1), b"")):
            with patch("researcher.service.openai_agents.subprocess.run", return_value=subprocess.CompletedProcess([], 0, stdout, stderr)):
                with self.assertRaises(AgentsError):
                    AgentsClient(SECRET).retrieve(SESSION)

    def test_worker_module_runs_without_service_dependencies_or_network(self):
        root = Path(__file__).resolve().parents[3]
        payload = {"method": "GET", "url": "https://invalid.example/v1/agents/sessions", "headers": {}, "body": None, "timeout": 1}
        result = subprocess.run([os.sys.executable, "-B", "-m", "researcher.service.openai_agents"],
                                input=json.dumps(payload).encode(), capture_output=True, cwd=root, timeout=3,
                                env={"PATH": os.defpath, "PYTHONPATH": str(root), "PYTHONUTF8": "1"}, check=False)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, b"")
        self.assertEqual(json.loads(result.stdout), {"error": "INVALID_ENDPOINT"})

    def test_native_uses_fixed_https_once_and_closes_on_redirect(self):
        connection, response = MagicMock(), MagicMock()
        response.status = 302
        response.getheaders.return_value = [("Location", "https://invalid.example")]
        connection.getresponse.return_value = response
        with patch("researcher.service.openai_agents.http.client.HTTPSConnection", return_value=connection) as connect:
            status, _, body = _native("GET", BASE_URL + "/" + SESSION, {}, None, 3)
        self.assertEqual((status, body), (302, b""))
        connect.assert_called_once_with("api.openai.com", timeout=3)
        connection.request.assert_called_once()
        response.read1.assert_not_called()
        connection.close.assert_called_once()

    def test_native_rejects_oversize_duplicate_framing_and_deadline(self):
        for case, code in (("oversize", "RESPONSE_TOO_LARGE"), ("duplicate", "MALFORMED_TRANSPORT"), ("deadline", "TIMEOUT")):
            connection, response = MagicMock(), MagicMock()
            response.status = 200
            response.getheaders.return_value = [("Content-Type", "application/json")]
            if case == "duplicate":
                response.getheaders.return_value.append(("content-type", "application/json"))
            response.read1.side_effect = [b"x" * (MAX_BYTES + 1), b""]
            connection.getresponse.return_value = response
            ticks = [0, 4] if case == "deadline" else [0, 0, 0]
            with patch("researcher.service.openai_agents.http.client.HTTPSConnection", return_value=connection), patch("researcher.service.openai_agents.time.monotonic", side_effect=ticks):
                with self.assertRaises(AgentsError) as caught:
                    _native("GET", BASE_URL, {}, None, 3)
            self.assertEqual(caught.exception.code, code)
            connection.close.assert_called_once()


    def test_native_repeated_cors_headers_do_not_reject_created_or_read_session(self):
        for status in (200, 201):
            with self.subTest(status=status):
                connection, response = MagicMock(), MagicMock()
                response.status = status
                response.getheaders.return_value = [("Content-Type", "application/json"),
                    ("Access-Control-Expose-Headers", "X-Request-ID"),
                    ("access-control-expose-headers", "X-RateLimit-Limit")]
                body = io.BytesIO(json.dumps(session()).encode())
                response.read1.side_effect = body.read1
                connection.getresponse.return_value = response
                client = AgentsClient(SECRET, _native, timeout_seconds=20)
                with patch("researcher.service.openai_agents.http.client.HTTPSConnection", return_value=connection):
                    result = client.create(request()) if status == 201 else client.retrieve(SESSION)
                self.assertEqual(result["id"], SESSION)
                connection.request.assert_called_once()
                connection.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
