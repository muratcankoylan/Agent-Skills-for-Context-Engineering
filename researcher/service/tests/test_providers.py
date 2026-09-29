"""Offline native-wire contracts; model identifiers here are fixtures, not availability claims."""

from copy import deepcopy
from dataclasses import replace
import io
import json
import traceback
import unittest
from unittest.mock import MagicMock, patch

from researcher.service.providers import (
    MAX_REQUEST_BYTES, MAX_RESPONSE_BYTES, ModelRequest, ProviderError, complete,
)


def payload(provider="openai"):
    if provider == "openai":
        return {"object": "response", "status": "completed", "id": "resp_fixture",
                "model": "gpt-fixture-2026-09-10", "error": None, "incomplete_details": None,
                "output": [{"type": "reasoning", "id": "rs_fixture", "summary": []},
                           {"type": "message", "status": "completed", "role": "assistant",
                            "content": [{"type": "output_text", "text": "answer"}]}],
                "usage": {"input_tokens": 11, "output_tokens": 7, "total_tokens": 18}}
    if provider == "anthropic":
        return {"type": "message", "role": "assistant", "id": "msg_fixture",
                "model": "claude-fixture-20260910", "stop_reason": "end_turn",
                "content": [{"type": "text", "text": "answer"}],
                "usage": {"input_tokens": 11, "output_tokens": 7,
                          "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}}
    return {"responseId": "gemini_fixture", "modelVersion": "gemini-fixture-001",
            "candidates": [{"finishReason": "STOP", "content": {"role": "model",
                            "parts": [{"text": "answer"}]}}],
            "usageMetadata": {"promptTokenCount": 11, "candidatesTokenCount": 7,
                              "thoughtsTokenCount": 0, "totalTokenCount": 18}}


class ProviderTests(unittest.TestCase):
    def request(self, provider="openai"):
        model = payload(provider)["modelVersion" if provider == "gemini" else "model"]
        return ModelRequest(provider, model, "system boundary", "research α", 64, 20)

    def call(self, data=None, provider="openai", *, raw=None, status=200, headers=None, request=None):
        response = raw if raw is not None else json.dumps(data if data is not None else payload(provider)).encode()
        self.transport = MagicMock(return_value=(status, headers or {"Content-Type": "application/json"}, response))
        return complete(request or self.request(provider), credential="fixture-secret", transport=self.transport)

    def error(self, code, *args, **kwargs):
        with self.assertRaises(ProviderError) as caught:
            self.call(*args, **kwargs)
        self.assertEqual(caught.exception.code, code)
        self.assertTrue(caught.exception.ambiguous)
        self.assertNotIn("fixture-secret", str(caught.exception))
        self.assertEqual(self.transport.call_count, 1)

    def test_native_openai_encoding_and_usage(self):
        result = self.call()
        url, headers, body, timeout = self.transport.call_args.args
        self.assertEqual(url, "https://api.openai.com/v1/responses")
        self.assertEqual(headers["Authorization"], "Bearer fixture-secret")
        sent = json.loads(body)
        self.assertEqual(sent["instructions"], "system boundary")
        self.assertEqual(sent["input"], "research α")
        self.assertEqual(sent["max_output_tokens"], 64)
        self.assertEqual(sent["tools"], [])
        self.assertEqual(sent["truncation"], "disabled")
        self.assertFalse(sent["store"])
        self.assertFalse(sent["stream"])
        self.assertEqual(timeout, 20)
        self.assertEqual((result.text, result.input_tokens, result.output_tokens), ("answer", 11, 7))
        self.assertEqual(result.request_id, "resp_fixture")

    def test_native_anthropic_encoding_and_cache_accounting(self):
        data = payload("anthropic")
        data["usage"].update(cache_read_input_tokens=3, cache_creation_input_tokens=2)
        result = self.call(data, "anthropic")
        url, headers, body, _ = self.transport.call_args.args
        self.assertEqual(url, "https://api.anthropic.com/v1/messages")
        self.assertEqual(headers["x-api-key"], "fixture-secret")
        self.assertEqual(headers["anthropic-version"], "2023-06-01")
        sent = json.loads(body)
        self.assertEqual(sent["system"], "system boundary")
        self.assertEqual(sent["messages"], [{"role": "user", "content": "research α"}])
        self.assertEqual(sent["max_tokens"], 64)
        self.assertEqual(result.input_tokens, 16)

    def test_native_gemini_encoding_and_thought_accounting(self):
        data = payload("gemini")
        data["usageMetadata"].update(thoughtsTokenCount=3, totalTokenCount=21)
        data["candidates"][0]["content"]["parts"].insert(0, {"text": "internal thought", "thought": True})
        result = self.call(data, "gemini")
        url, headers, body, _ = self.transport.call_args.args
        self.assertEqual(url, "https://generativelanguage.googleapis.com/v1beta/models/gemini-fixture-001:generateContent")
        self.assertNotIn("fixture-secret", url)
        self.assertEqual(headers["x-goog-api-key"], "fixture-secret")
        sent = json.loads(body)
        self.assertEqual(sent["systemInstruction"], {"parts": [{"text": "system boundary"}]})
        self.assertEqual(sent["generationConfig"], {"candidateCount": 1, "maxOutputTokens": 64})
        self.assertEqual((result.text, result.output_tokens), ("answer", 10))

    def test_bad_inputs_have_no_effect(self):
        cases = [replace(self.request(), provider="custom"), replace(self.request(), provider=[]), replace(self.request(), max_output_tokens=True),
                 replace(self.request(), timeout_seconds=0), replace(self.request(), timeout_seconds=301),
                 replace(self.request(), max_output_tokens=0), replace(self.request(), prompt=" "),
                 replace(self.request(), prompt="\ud800"), replace(self.request(), system=None)]
        for model in ("latest", "gpt-latest", "gpt.latest", "default", "auto", "../secret", "m:run", "m?key=x", "models/x", "https://evil.test", "x\nHeader:bad"):
            cases.append(replace(self.request(), model=model))
        for request in cases:
            with self.subTest(request=request):
                transport = MagicMock()
                with self.assertRaises(ProviderError) as caught:
                    complete(request, credential="fixture-secret", transport=transport)
                self.assertFalse(caught.exception.ambiguous)
                transport.assert_not_called()

    def test_bad_credentials_never_appear_in_errors(self):
        for credential in ("", "secret\nheader", "secret\rheader", "é", "x" * 4097, None):
            transport = MagicMock()
            with self.assertRaises(ProviderError) as caught:
                complete(self.request(), credential=credential, transport=transport)
            self.assertEqual(caught.exception.code, "INVALID_CREDENTIAL")
            self.assertFalse(caught.exception.ambiguous)
            transport.assert_not_called()

    def test_request_size_is_bounded_before_network(self):
        transport = MagicMock()
        with self.assertRaises(ProviderError) as caught:
            complete(replace(self.request(), prompt="a" * MAX_REQUEST_BYTES), credential="fixture-secret", transport=transport)
        self.assertEqual(caught.exception.code, "REQUEST_TOO_LARGE")
        self.assertFalse(caught.exception.ambiguous)
        transport.assert_not_called()

    def test_transport_failure_traceback_is_redacted_and_not_retried(self):
        transport = MagicMock(side_effect=RuntimeError("fixture-secret sensitive remote body"))
        try:
            complete(self.request(), credential="fixture-secret", transport=transport)
        except ProviderError as error:
            self.assertEqual(error.code, "TRANSPORT_ERROR")
            rendered = "".join(traceback.format_exception(type(error), error, error.__traceback__))
            self.assertNotIn("sensitive remote body", rendered)
        else:
            self.fail("transport error was swallowed")
        self.assertEqual(transport.call_count, 1)

    def test_redirect_and_http_errors_are_never_retried(self):
        for status in (301, 302, 307, 308):
            with self.subTest(status=status):
                self.error("REDIRECT_REFUSED", status=status, headers={"Location": "https://evil.test"})
        for status in (400, 401, 403, 429, 500, 503):
            with self.subTest(status=status):
                self.error("HTTP_ERROR", status=status, raw=b"fixture-secret remote error")

    def test_native_transport_closes_without_following_redirect(self):
        connection = MagicMock()
        connection.getresponse.return_value.status = 307
        connection.getresponse.return_value.getheaders.return_value = [("location", "https://evil.test")]
        with patch("researcher.service.providers.http.client.HTTPSConnection", return_value=connection) as constructor:
            with self.assertRaises(ProviderError) as caught:
                complete(self.request(), credential="fixture-secret")
        self.assertEqual(caught.exception.code, "REDIRECT_REFUSED")
        constructor.assert_called_once_with("api.openai.com", timeout=20)
        connection.request.assert_called_once()
        connection.close.assert_called_once()
        connection.getresponse.return_value.read1.assert_not_called()

    def test_native_response_read_limit_closes_connection(self):
        connection = MagicMock()
        response = connection.getresponse.return_value
        response.status = 200
        response.getheaders.return_value = [("content-type", "application/json")]
        oversized = io.BytesIO(b" " * (MAX_RESPONSE_BYTES + 50))
        response.read1.side_effect = oversized.read1
        with patch("researcher.service.providers.http.client.HTTPSConnection", return_value=connection):
            with self.assertRaises(ProviderError) as caught:
                complete(self.request(), credential="fixture-secret")
        self.assertEqual(caught.exception.code, "RESPONSE_TOO_LARGE")
        self.assertEqual(oversized.tell(), MAX_RESPONSE_BYTES + 1)
        connection.close.assert_called_once()

    def test_timeouts_are_ambiguous_without_retry(self):
        transport = MagicMock(side_effect=TimeoutError("fixture-secret timeout"))
        with self.assertRaises(ProviderError) as caught:
            complete(self.request(), credential="fixture-secret", transport=transport)
        self.assertEqual(caught.exception.code, "TIMEOUT")
        self.assertTrue(caught.exception.ambiguous)
        self.assertNotIn("fixture-secret", str(caught.exception))
        self.assertEqual(transport.call_count, 1)

    def test_native_duplicate_framing_headers_are_rejected(self):
        connection = MagicMock()
        response = connection.getresponse.return_value
        response.status = 200
        response.getheaders.return_value = [("Content-Length", "12"), ("content-length", "15")]
        with patch("researcher.service.providers.http.client.HTTPSConnection", return_value=connection):
            with self.assertRaises(ProviderError) as caught:
                complete(self.request(), credential="fixture-secret")
        self.assertEqual(caught.exception.code, "MALFORMED_TRANSPORT")
        connection.close.assert_called_once()

    def test_repeated_uninterpreted_cors_headers_do_not_change_framing(self):
        connection = MagicMock()
        response = connection.getresponse.return_value
        response.status = 200
        response.getheaders.return_value = [("Content-Type", "application/json"),
            ("Access-Control-Expose-Headers", "X-Request-ID"),
            ("access-control-expose-headers", "X-RateLimit-Limit")]
        body = io.BytesIO(json.dumps(payload()).encode())
        response.read1.side_effect = body.read1
        with patch("researcher.service.providers.http.client.HTTPSConnection", return_value=connection):
            result = complete(self.request(), credential="fixture-secret")
        self.assertEqual(result.text, "answer")
        connection.request.assert_called_once()
        connection.close.assert_called_once()

    def test_response_byte_cap_and_json_boundaries(self):
        self.error("RESPONSE_TOO_LARGE", raw=b" " * (MAX_RESPONSE_BYTES + 1))
        for raw in (b"{", b"\xff", b'{"a":1,"a":2}', b'{"x":NaN}', b'{"x":Infinity}'):
            with self.subTest(raw=raw):
                self.error("MALFORMED_JSON", raw=raw)
        self.error("MALFORMED_RESPONSE", raw=b"[]")
        self.error("UNEXPECTED_CONTENT_TYPE", headers={"Content-Type": "text/html"})
        self.error("UNEXPECTED_ENCODING", headers={"Content-Type": "application/json", "Content-Encoding": "gzip"})
        self.error("MALFORMED_TRANSPORT", headers={"content-type": "application/json", "content-encoding": 7})
        self.error("TRUNCATED_RESPONSE", headers={"content-type": "application/json", "content-length": "9999"})
        self.error("MALFORMED_TRANSPORT", headers={"content-type": "application/json", "content-length": "NaN"})

    def test_usage_must_be_nonnegative_integers_with_consistent_totals(self):
        for provider in ("openai", "anthropic", "gemini"):
            for bad in (None, True, -1, 1.2, "7", 2**53):
                with self.subTest(provider=provider, bad=bad):
                    data = payload(provider)
                    usage = data["usageMetadata" if provider == "gemini" else "usage"]
                    usage["candidatesTokenCount" if provider == "gemini" else "output_tokens"] = bad
                    self.error("MALFORMED_USAGE", data, provider)
        for provider in ("openai", "gemini"):
            data = payload(provider)
            data["usageMetadata" if provider == "gemini" else "usage"]["totalTokenCount" if provider == "gemini" else "total_tokens"] = 999
            self.error("MALFORMED_USAGE", data, provider)

    def test_openai_refusal_partial_and_tool_results_fail(self):
        data = payload()
        data["status"] = "incomplete"
        self.error("INCOMPLETE_RESPONSE", data)
        data = payload()
        data["output"][1]["content"] = [{"type": "refusal", "refusal": "refused"}]
        self.error("REFUSAL", data)
        data["output"][1]["content"] = [{"type": "output_text", "text": ""}]
        self.error("EMPTY_RESPONSE", data)
        data["output"][1]["status"] = "in_progress"
        self.error("UNEXPECTED_CONTENT", data)
        data = payload()
        data["output"].append({"type": "function_call", "name": "run"})
        self.error("UNEXPECTED_CONTENT", data)
        data = payload()
        data["output"][0]["status"] = "in_progress"
        self.error("INCOMPLETE_RESPONSE", data)

    def test_anthropic_all_nonterminal_stops_fail(self):
        for stop in ("max_tokens", "tool_use", "pause_turn", "stop_sequence", "model_context_window_exceeded", None):
            data = payload("anthropic")
            data["stop_reason"] = stop
            self.error("INCOMPLETE_RESPONSE", data, "anthropic")
        data["stop_reason"] = "refusal"
        self.error("REFUSAL", data, "anthropic")

    def test_gemini_partial_refused_multiple_and_tool_results_fail(self):
        for finish in ("MAX_TOKENS", "SAFETY", "RECITATION", None):
            data = payload("gemini")
            data["candidates"][0]["finishReason"] = finish
            self.error("INCOMPLETE_RESPONSE", data, "gemini")
        data = payload("gemini")
        data["promptFeedback"] = {"blockReason": "SAFETY"}
        self.error("REFUSAL", data, "gemini")
        data = payload("gemini")
        data["candidates"].append(deepcopy(data["candidates"][0]))
        self.error("UNEXPECTED_CONTENT", data, "gemini")
        data = payload("gemini")
        data["candidates"][0]["content"]["parts"] = [{"functionCall": {"name": "run"}}]
        self.error("UNEXPECTED_CONTENT", data, "gemini")

    def test_remote_error_and_excess_output_fail(self):
        self.error("PROVIDER_RESPONSE_ERROR", {"error": {"message": "fixture-secret"}})
        self.error("OUTPUT_LIMIT_EXCEEDED", request=replace(self.request(), max_output_tokens=6))

    def test_model_and_request_ids_are_validated(self):
        for value in (None, 42, "", "bad\nmodel"):
            data = payload()
            data["model"] = value
            self.error("MALFORMED_RESPONSE", data)
        data = payload()
        data["id"] = {"bad": "id"}
        self.error("MALFORMED_RESPONSE", data)


if __name__ == "__main__":
    unittest.main()
