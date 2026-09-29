"""Offline connector diagnostics, not provider authentication or retrieval evidence."""

from dataclasses import FrozenInstanceError, replace
import json
import socket
import unittest
from unittest.mock import MagicMock, patch
from urllib.parse import quote

from researcher.service.connector_checks import (
    MAX_RESPONSE_BYTES, PROBES, _https, probe_request,
)
from researcher.service.contracts import ServiceError

SECRET = 'synthetic-fixture+token/="not-live"'
JSON_HEADERS = {"Content-Type": "application/json"}


def response(name):
    if name == "openai_models":
        return {"object": "list", "data": [{"object": "model", "id": "fixture-model", "owned_by": "private-account"}]}
    if name == "github_repo":
        return {"id": 123, "full_name": "muratcankoylan/Agent-Skills-for-Context-Engineering",
                "private": False, "owner": {"login": "private-account"}}
    if name == "github_identity":
        return {"id": 123, "login": "private-account", "type": "User"}
    if name == "firecrawl_scrape":
        return {"success": True, "data": {"markdown": "Reserved documentation domains.",
                "metadata": {"sourceURL": "https://www.iana.org/domains/reserved", "statusCode": 200}}}
    if name == "firecrawl_papers":
        return {"success": True, "results": [{"paperId": "123", "primaryId": "arxiv:2105.05233",
                "title": "Fixture paper", "abstract": "Fixture abstract", "ids": {"arxiv": ["2105.05233"]},
                "score": 0.01}]}
    if name == "firecrawl_credits":
        return {"success": True, "data": {"remainingCredits": 1000, "planCredits": 500000,
                "billingPeriodStart": "2026-09-01T00:00:00Z", "billingPeriodEnd": "2026-10-01T00:00:00Z"}}
    if name == "openalex_auth":
        return {"api_key": "masked-private-key", "rate_limit": {"daily_budget_usd": 1,
                "daily_used_usd": 0.125, "daily_remaining_usd": 0.875,
                "prepaid_balance_usd": 0, "prepaid_remaining_usd": 0}}
    row = {"url": "https://www.iana.org/domains/reserved", "title": "Example Domains",
           "publish_date": None, "excerpts": ["Reserved for documentation."]}
    if name == "parallel_search":
        return {"search_id": "private-search", "session_id": "private-session", "results": [row]}
    return {"extract_id": "private-extract", "session_id": "private-session", "results": [row], "errors": []}


class ConnectorChecksTests(unittest.TestCase):
    def call(self, name="openai_models", *, data=None, status=200, headers=None, body=None):
        body = body if body is not None else json.dumps(response(name) if data is None else data).encode()
        self.transport = MagicMock(return_value=(status, JSON_HEADERS if headers is None else headers, body))
        result = probe_request(PROBES[name], SECRET, self.transport)
        self.assertEqual(self.transport.call_count, 1)
        self.assertEqual(set(result), {"schema", "name", "classification", "http_status", "counts"})
        self.assertNotIn(SECRET, json.dumps(result))
        return result

    def test_closed_probes_have_bounded_costs_and_immutable_definitions(self):
        self.assertEqual(set(PROBES), {"openai_models", "github_repo", "firecrawl_credits", "openalex_auth",
                                      "parallel_search", "parallel_extract", "github_identity",
                                      "firecrawl_scrape", "firecrawl_papers"})
        self.assertEqual(sum(p.reserve_micro_usd for p in PROBES.values()), 12000)
        with self.assertRaises(TypeError):
            PROBES["other"] = PROBES["openai_models"]
        with self.assertRaises(FrozenInstanceError):
            PROBES["openai_models"].url = "https://evil.invalid"

    def test_valid_contracts_emit_only_aggregate_counts(self):
        expected = {"openai_models": {"model_count": 1}, "github_repo": {"repository_count": 1},
                    "github_identity": {"authenticated_identity_count": 1},
                    "firecrawl_scrape": {"page_count": 1, "markdown_bytes": 31},
                    "firecrawl_papers": {"paper_count": 1, "abstract_count": 1},
                    "firecrawl_credits": {"credits_available": 1},
                    "openalex_auth": {"budget_available": 1},
                    "parallel_search": {"result_count": 1, "error_count": 0},
                    "parallel_extract": {"result_count": 1, "error_count": 0}}
        for name in PROBES:
            with self.subTest(name=name):
                result = self.call(name)
                self.assertEqual(result["classification"], "success")
                self.assertEqual(result["counts"], expected[name])
                for private in ("private-account", "private-search", "private-session", "fixture-model", "500000", "masked-private-key"):
                    self.assertNotIn(private, json.dumps(result))

    def test_wire_auth_method_payload_and_timeout_are_fixed(self):
        for name, probe in PROBES.items():
            self.call(name)
            method, url, headers, body, timeout = self.transport.call_args.args
            self.assertEqual((method, url, body, timeout), (probe.method, probe.url, probe.payload, 30))
            if name.startswith("parallel_"):
                self.assertEqual(headers["x-api-key"], SECRET)
                self.assertNotIn("Authorization", headers)
            else:
                self.assertEqual(headers["Authorization"], "Bearer " + SECRET)
            self.assertNotIn(SECRET, url)
            self.assertEqual(headers["Accept-Encoding"], "identity")
        self.assertEqual(json.loads(PROBES["parallel_search"].payload)["advanced_settings"], {"max_results": 1})
        self.assertEqual(json.loads(PROBES["parallel_extract"].payload)["urls"], ["https://www.iana.org/domains/reserved"])
        self.assertEqual(json.loads(PROBES["firecrawl_scrape"].payload), {
            "url": "https://www.iana.org/domains/reserved", "formats": ["markdown"], "onlyMainContent": True,
            "proxy": "basic", "timeout": 20000, "parsers": [], "storeInCache": False})

    def test_caller_cannot_override_registry_endpoint_method_cost_or_body(self):
        probe = PROBES["openai_models"]
        class ForgedString(str):
            def __eq__(self, other):
                return True
        cases = [None, {}, replace(probe, name="other"), replace(probe, credential_env="OTHER_SECRET"),
                 replace(probe, method="POST"), replace(probe, url="https://api.openai.com/v1/responses"),
                 replace(probe, url="https://api.openai.com.evil.invalid/v1/models"),
                 replace(probe, url="http://api.openai.com/v1/models"),
                 replace(probe, url=ForgedString("https://evil.invalid")),
                 replace(probe, payload=b"{}"), replace(probe, reserve_micro_usd=False),
                 replace(PROBES["parallel_search"], payload=bytearray(PROBES["parallel_search"].payload))]
        for fake in cases:
            with self.subTest(fake=type(fake).__name__):
                transport = MagicMock()
                with self.assertRaises(ServiceError) as caught:
                    probe_request(fake, SECRET, transport)
                self.assertEqual(caught.exception.code, "UNREGISTERED_CONNECTOR_PROBE")
                transport.assert_not_called()

    def test_invalid_credential_never_reaches_transport(self):
        for value in (None, "", "short", "space token", "line\nbreak", "non-ascii-α", "x" * 4097, True):
            transport = MagicMock()
            with self.subTest(value_type=type(value).__name__), self.assertRaises(ServiceError) as caught:
                probe_request(PROBES["openai_models"], value, transport)
            self.assertEqual(caught.exception.code, "INVALID_SOURCE_CREDENTIAL")
            transport.assert_not_called()

    def test_http_status_classification_does_not_echo_error_bodies(self):
        expected = {401: "auth_rejected", 402: "billing_blocked", 403: "permission_denied",
                    429: "rate_limited", 404: "endpoint_unavailable", 405: "endpoint_unavailable",
                    410: "endpoint_unavailable", 301: "endpoint_unavailable", 307: "endpoint_unavailable",
                    500: "endpoint_unavailable", 503: "endpoint_unavailable", 422: "schema_invalid"}
        for status, classification in expected.items():
            with self.subTest(status=status):
                result = self.call(status=status, body=b"private-provider-error-not-json")
                self.assertEqual(result["classification"], classification)
                self.assertEqual(result["counts"], {})
                self.assertNotIn("private-provider", json.dumps(result))

    def test_transport_exception_is_sanitized_and_never_retried(self):
        transport = MagicMock(side_effect=RuntimeError(SECRET))
        result = probe_request(PROBES["openai_models"], SECRET, transport)
        transport.assert_called_once()
        self.assertEqual(result["classification"], "transport_unknown")
        self.assertIsNone(result["http_status"])
        self.assertNotIn(SECRET, json.dumps(result))

    def test_raw_encoded_json_and_header_credential_reflection_fail_closed(self):
        encoded = [SECRET.encode(), quote(SECRET, safe="").encode(), json.dumps(SECRET).encode(),
                   ('"' + ''.join('\\u%04x' % ord(ch) for ch in SECRET) + '"').encode()]
        for reflected in encoded:
            for status in (200, 401):
                with self.subTest(encoding=encoded.index(reflected), status=status):
                    result = self.call(status=status, body=reflected)
                    self.assertEqual(result["classification"], "schema_invalid")
        self.assertEqual(self.call(headers={**JSON_HEADERS, "x-private": SECRET})["classification"], "schema_invalid")
        data = response("openai_models")
        data["ignored-field"] = SECRET
        self.assertEqual(self.call(data=data)["classification"], "schema_invalid")

    def test_duplicate_keys_nonfinite_utf8_and_nondict_json_rejected(self):
        for body in (b'{"object":"list","data":[],"data":[]}', b'{"x":NaN}', b'{"x":Infinity}',
                     b'[]', b'null', b'\xff', b'{'):
            with self.subTest(body=body):
                self.assertEqual(self.call(body=body)["classification"], "schema_invalid")

    def test_response_size_framing_compression_and_header_limits(self):
        for headers in ({}, {"Content-Type": "text/html"}, {**JSON_HEADERS, "Content-Encoding": "gzip"},
                        {**JSON_HEADERS, "Content-Length": "99999"},
                        {**JSON_HEADERS, "Content-Length": "0", "Transfer-Encoding": "chunked"},
                        {**JSON_HEADERS, "Content-Length": "-1"},
                        {**JSON_HEADERS, "Transfer-Encoding": "gzip"},
                        [("Content-Type", "application/json"), ("content-type", "application/json")],
                        {**JSON_HEADERS, "x-extra": "x" * 65537}):
            with self.subTest(headers_kind=type(headers).__name__):
                self.assertEqual(self.call(headers=headers)["classification"], "schema_invalid")
        self.assertEqual(self.call(body=b"x" * (MAX_RESPONSE_BYTES + 1))["classification"], "schema_invalid")
        for status in (True, 99, 600, "200"):
            self.assertEqual(self.call(status=status)["classification"], "schema_invalid")

    def test_repeated_noncritical_cors_headers_do_not_reject_valid_response(self):
        pairs = [("Content-Type", "application/json"), ("access-control-expose-headers", "x-one"),
                 ("Access-Control-Expose-Headers", "x-two")]
        self.assertEqual(self.call(headers=pairs)["classification"], "success")

    def test_openai_and_github_narrow_success_validation(self):
        for data in ({"object": "list"}, {"object": "list", "data": ["not-model"]},
                     {"object": "other", "data": []}, {"object": "list", "data": [{"object": "model", "id": 42}]}):
            self.assertEqual(self.call(data=data)["classification"], "schema_invalid")
        for field, value in (("id", True), ("id", 0), ("full_name", "unrelated/repo"), ("private", "false")):
            data = response("github_repo")
            data[field] = value
            self.assertEqual(self.call("github_repo", data=data)["classification"], "schema_invalid")

    def test_firecrawl_does_not_equate_http200_to_success(self):
        for field, value in (("remainingCredits", True), ("remainingCredits", -1),
                             ("remainingCredits", "1000"), ("planCredits", None), ("billingPeriodStart", "")):
            data = response("firecrawl_credits")
            data["data"][field] = value
            self.assertEqual(self.call("firecrawl_credits", data=data)["classification"], "schema_invalid")
        data = response("firecrawl_credits")
        data["success"] = False
        self.assertEqual(self.call("firecrawl_credits", data=data)["classification"], "schema_invalid")
        data = response("firecrawl_credits")
        data["data"]["remainingCredits"] = 0
        self.assertEqual(self.call("firecrawl_credits", data=data)["counts"], {"credits_available": 0})

    def test_scrape_rejects_empty_wrong_source_error_status_and_partial_results(self):
        for change in ("empty", "url", "status", "warning", "error", "success"):
            data = response("firecrawl_scrape")
            if change == "empty":
                data["data"]["markdown"] = " "
            elif change == "url":
                data["data"]["metadata"]["sourceURL"] = "https://unrelated.example"
            elif change == "status":
                data["data"]["metadata"]["statusCode"] = 403
            elif change == "warning":
                data["data"]["warning"] = "Partial scrape"
            elif change == "error":
                data["data"]["metadata"]["error"] = "provider detail"
            else:
                data["success"] = False
            with self.subTest(change=change):
                self.assertEqual(self.call("firecrawl_scrape", data=data)["classification"], "schema_invalid")

    def test_paper_search_rejects_oversized_false_and_missing_identity(self):
        for change in ("success", "extra", "id"):
            data = response("firecrawl_papers")
            if change == "success":
                data["success"] = False
            elif change == "extra":
                data["results"] *= 2
            else:
                del data["results"][0]["primaryId"]
            self.assertEqual(self.call("firecrawl_papers", data=data)["classification"], "schema_invalid")
        self.assertEqual(self.call("firecrawl_papers", data={"success": True, "results": []})["counts"],
                         {"paper_count": 0, "abstract_count": 0})

    def test_openalex_quota_requires_finite_numeric_fields_without_exposing_balances(self):
        for value in (True, "1", -1, None):
            data = response("openalex_auth")
            data["rate_limit"]["daily_budget_usd"] = value
            self.assertEqual(self.call("openalex_auth", data=data)["classification"], "schema_invalid")
        data = response("openalex_auth")
        del data["rate_limit"]["prepaid_balance_usd"]
        self.assertEqual(self.call("openalex_auth", data=data)["classification"], "schema_invalid")
        data = response("openalex_auth")
        data["rate_limit"]["daily_remaining_usd"] = 0
        self.assertEqual(self.call("openalex_auth", data=data)["counts"], {"budget_available": 0})

    def test_parallel_search_empty_results_are_valid_but_report_zero(self):
        data = response("parallel_search")
        data["results"] = []
        result = self.call("parallel_search", data=data)
        self.assertEqual(result["classification"], "success")
        self.assertEqual(result["counts"]["result_count"], 0)

    def test_parallel_extract_requires_actual_requested_content_without_errors(self):
        for change in ("errors", "empty", "wrong-url", "missing-content", "missing-errors"):
            data = response("parallel_extract")
            if change == "errors":
                data["errors"] = [{"url": "https://www.iana.org/domains/reserved", "content": "private-failure"}]
            elif change == "empty":
                data["results"] = []
            elif change == "wrong-url":
                data["results"][0]["url"] = "https://wrong.example"
            elif change == "missing-content":
                data["results"][0]["excerpts"] = []
            else:
                del data["errors"]
            with self.subTest(change=change):
                self.assertEqual(self.call("parallel_extract", data=data)["classification"], "schema_invalid")

    def test_default_transport_has_no_ambient_proxy_or_private_dns_path(self):
        with patch("researcher.service.connector_checks._system_resolver", return_value=("127.0.0.1",)), \
             patch("socket.create_connection") as connect:
            result = probe_request(PROBES["openai_models"], SECRET)
        self.assertEqual(result["classification"], "transport_unknown")
        connect.assert_not_called()

    def test_default_transport_closes_resources_and_does_not_follow_redirect(self):
        connection, raw, tls, timer, reply = (MagicMock() for _ in range(5))
        reply.status = 307
        reply.getheaders.return_value = [("Location", "https://evil.invalid/"), ("Content-Length", "0")]
        reply.read1.return_value = b""
        connection.getresponse.return_value = reply
        with patch("researcher.service.connector_checks._system_resolver", return_value=("8.8.8.8",)), \
             patch("socket.create_connection", return_value=raw) as connect, \
             patch("ssl.create_default_context") as context, \
             patch("http.client.HTTPSConnection", return_value=connection), \
             patch("threading.Timer", return_value=timer):
            context.return_value.wrap_socket.return_value = tls
            result = _https("GET", PROBES["openai_models"].url + "?fixed=1", {}, None, 30)
        self.assertEqual(result[0], 307)
        connect.assert_called_once()
        self.assertEqual(connect.call_args.args, (("8.8.8.8", 443),))
        self.assertEqual(context.return_value.wrap_socket.call_args.kwargs["server_hostname"], "api.openai.com")
        connection.request.assert_called_once_with("GET", "/v1/models?fixed=1", body=None, headers={})
        timer.start.assert_called_once()
        timer.cancel.assert_called_once()
        reply.close.assert_called_once()
        connection.close.assert_called_once()
        tls.close.assert_called_once()

    def test_default_transport_deadline_can_shutdown_trickling_socket(self):
        connection, raw, tls, reply = (MagicMock() for _ in range(4))
        reply.status = 200
        reply.getheaders.return_value = []
        reply.read1.return_value = b""
        connection.getresponse.return_value = reply
        callbacks = []
        def timer_factory(seconds, callback):
            self.assertGreater(seconds, 0)
            self.assertLessEqual(seconds, 30)
            callbacks.append(callback)
            return MagicMock()
        with patch("researcher.service.connector_checks._system_resolver", return_value=("8.8.8.8",)), \
             patch("socket.create_connection", return_value=raw), \
             patch("ssl.create_default_context") as context, \
             patch("http.client.HTTPSConnection", return_value=connection), \
             patch("threading.Timer", side_effect=timer_factory):
            context.return_value.wrap_socket.return_value = tls
            _https("GET", PROBES["openai_models"].url, {}, None, 30)
            callbacks[0]()
        tls.shutdown.assert_called_once_with(socket.SHUT_RDWR)


if __name__ == "__main__":
    unittest.main()
