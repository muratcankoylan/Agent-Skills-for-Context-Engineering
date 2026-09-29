"""One-shot, fixed-endpoint diagnostics. The caller owns admission and cost state.

Success proves only the narrow response contract, never production readiness or
unrestricted provider access. Injected transports are trusted test dependencies.
No credential discovery, raw response persistence, redirects, or retries occur.
"""

from __future__ import annotations

from dataclasses import dataclass
import http.client
import json
import math
import socket
import ssl
import threading
import time
from types import MappingProxyType
from typing import Mapping
from urllib.parse import quote, quote_plus, urlsplit

from researcher.scripts.source_connectors import _resolve_public_ips, _system_resolver
from researcher.scripts.source_search import credential_value
from .contracts import ServiceError

MAX_RESPONSE_BYTES = 1024 * 1024
TIMEOUT_SECONDS = 30
_REPOSITORY = "muratcankoylan/Agent-Skills-for-Context-Engineering"
_EXTRACT_URL = "https://www.iana.org/domains/reserved"


@dataclass(frozen=True, slots=True)
class Probe:
    name: str
    credential_env: str
    method: str
    url: str
    payload: bytes | None
    reserve_micro_usd: int


def _body(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


PROBES = MappingProxyType({p.name: p for p in (
    Probe("openai_models", "OPENAI_API_KEY", "GET", "https://api.openai.com/v1/models", None, 0),
    Probe("github_repo", "RESEARCH_GITHUB_TOKEN", "GET", "https://api.github.com/repos/" + _REPOSITORY, None, 0),
    Probe("github_identity", "RESEARCH_GITHUB_TOKEN", "GET", "https://api.github.com/user", None, 0),
    Probe("firecrawl_credits", "FIRECRAWL_API_KEY", "GET", "https://api.firecrawl.dev/v2/team/credit-usage", None, 0),
    Probe("firecrawl_scrape", "FIRECRAWL_API_KEY", "POST", "https://api.firecrawl.dev/v2/scrape", _body({
        "url": _EXTRACT_URL, "formats": ["markdown"], "onlyMainContent": True,
        "proxy": "basic", "timeout": 20000, "parsers": [], "storeInCache": False,
    }), 10_000),
    Probe("firecrawl_papers", "FIRECRAWL_API_KEY", "GET",
          "https://api.firecrawl.dev/v2/search/research/papers?query=agent%20memory%20retrieval&k=1", None, 0),
    Probe("openalex_auth", "OPENALEX_API_KEY", "GET", "https://api.openalex.org/rate-limit", None, 0),
    Probe("parallel_search", "PARALLEL_API_KEY", "POST", "https://api.parallel.ai/v1/search", _body({
        "search_queries": ["context engineering agent retrieval"], "mode": "fast",
        "max_chars_total": 1500, "advanced_settings": {"max_results": 1},
    }), 1000),
    Probe("parallel_extract", "PARALLEL_API_KEY", "POST", "https://api.parallel.ai/v1/extract", _body({
        "urls": [_EXTRACT_URL], "objective": "Identify why these domains are reserved", "max_chars_total": 1500,
    }), 1000),
)})


def _registered(probe):
    if (type(probe) is not Probe
            or any(type(getattr(probe, name)) is not str for name in ("name", "credential_env", "method", "url"))
            or probe.payload is not None and type(probe.payload) is not bytes
            or type(probe.reserve_micro_usd) is not int
            or probe.name not in PROBES or probe != PROBES[probe.name]):
        raise ServiceError("UNREGISTERED_CONNECTOR_PROBE")


def _https(method, url, headers, body, timeout_seconds):
    """Pinned public DNS, verified TLS, and an absolute exchange deadline.

    Reuse the connector resolver's bounded DNS worker pool; HTTP never resolves
    the hostname a second time. A watchdog also bounds trickled HTTP headers.
    """
    parsed = urlsplit(url)
    deadline = time.monotonic() + timeout_seconds

    def remaining():
        value = deadline - time.monotonic()
        if value <= 0:
            raise TimeoutError()
        return value

    addresses = _resolve_public_ips(
        lambda host, port: _system_resolver(host, port, timeout=remaining()), parsed.hostname, 443)
    connection = http.client.HTTPSConnection(parsed.hostname, timeout=remaining())
    raw = tls = timer = response = None

    def interrupt():
        active = tls if tls is not None else raw
        if active is not None:
            try:
                active.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

    try:
        raw = socket.create_connection((addresses[0], 443), timeout=remaining())
        tls = ssl.create_default_context().wrap_socket(raw, server_hostname=parsed.hostname,
                                                       do_handshake_on_connect=False)
        raw = None
        timer = threading.Timer(remaining(), interrupt)
        timer.daemon = True
        timer.start()
        tls.settimeout(remaining())
        tls.do_handshake()
        connection.sock = tls
        target = parsed.path + ("?" + parsed.query if parsed.query else "")
        connection.request(method, target, body=body, headers=headers)
        response = connection.getresponse()
        pairs = response.getheaders()
        chunks, size = [], 0
        while size <= MAX_RESPONSE_BYTES:
            tls.settimeout(remaining())
            chunk = response.read1(min(65536, MAX_RESPONSE_BYTES + 1 - size))
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
        if size > MAX_RESPONSE_BYTES:
            raise ValueError()
        return response.status, pairs, b"".join(chunks)
    finally:
        if timer is not None:
            timer.cancel()
        if response is not None:
            response.close()
        connection.close()
        if tls is not None:
            tls.close()
        if raw is not None:
            raw.close()


def _json(body):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError()
            result[key] = value
        return result

    def invalid(_):
        raise ValueError()

    return json.loads(body.decode("utf-8"), object_pairs_hook=unique, parse_constant=invalid)


def _reflects(credential, body, headers, data=None):
    variants = {credential, quote(credential, safe=""), quote_plus(credential, safe=""),
                json.dumps(credential)[1:-1], json.dumps(credential, ensure_ascii=False)[1:-1]}
    raw = body + repr(headers).encode("utf-8")
    if any(value.encode("utf-8") in raw for value in variants):
        return True
    # Decode JSON strings as well: escaped characters must not hide a reflected
    # credential in an unknown field. Duplicate-key bodies are rejected anyway.
    pending = [data]
    while pending:
        value = pending.pop()
        if isinstance(value, str) and any(item in value for item in variants):
            return True
        if isinstance(value, dict):
            pending.extend(value.keys())
            pending.extend(value.values())
        elif isinstance(value, list):
            pending.extend(value)
    return False


def _headers(raw):
    pairs = list(raw.items()) if isinstance(raw, Mapping) else raw
    if not isinstance(pairs, (list, tuple)) or len(pairs) > 100:
        raise ValueError()
    result, size = {}, 0
    critical = {"content-type", "content-length", "content-encoding", "transfer-encoding", "mcp-session-id"}
    for pair in pairs:
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            raise ValueError()
        name, value = pair
        if (not isinstance(name, str) or not isinstance(value, str)
                or any(ch in name + value for ch in "\r\n")):
            raise ValueError()
        size += len(name.encode()) + len(value.encode())
        name = name.lower()
        if size > 65536 or name in critical and name in result:
            raise ValueError()
        result[name] = value
    return result


def _text(value):
    return isinstance(value, str) and bool(value.strip()) and len(value) <= 8192


def _number(value):
    return type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 2**53 - 1


def _success(probe, data):
    if not isinstance(data, dict):
        raise ValueError()
    if probe.name == "openai_models":
        rows = data.get("data")
        if (data.get("object") != "list" or not isinstance(rows, list) or len(rows) > 10000
                or any(not isinstance(row, dict) or row.get("object") != "model"
                       or not _text(row.get("id")) for row in rows)):
            raise ValueError()
        return {"model_count": len(rows)}
    if probe.name == "github_repo":
        if (type(data.get("id")) is not int or data["id"] <= 0
                or data.get("full_name") != _REPOSITORY or type(data.get("private")) is not bool):
            raise ValueError()
        return {"repository_count": 1}
    if probe.name == "github_identity":
        if (type(data.get("id")) is not int or data["id"] <= 0
                or not _text(data.get("login")) or data.get("type") not in {"User", "Bot"}):
            raise ValueError()
        return {"authenticated_identity_count": 1}
    if probe.name == "firecrawl_scrape":
        item = data.get("data")
        if data.get("success") is not True or not isinstance(item, dict):
            raise ValueError()
        metadata = item.get("metadata")
        markdown = item.get("markdown")
        if (not isinstance(metadata, dict) or metadata.get("sourceURL") != _EXTRACT_URL
                or type(metadata.get("statusCode")) is not int or metadata["statusCode"] != 200
                or metadata.get("error") or item.get("warning")
                or not isinstance(markdown, str) or not markdown.strip()):
            raise ValueError()
        return {"page_count": 1, "markdown_bytes": len(markdown.encode("utf-8"))}
    if probe.name == "firecrawl_papers":
        rows = data.get("results")
        if data.get("success") is not True or not isinstance(rows, list) or len(rows) > 1:
            raise ValueError()
        for item in rows:
            if (not isinstance(item, dict) or not _text(item.get("paperId"))
                    or not _text(item.get("primaryId")) or not _text(item.get("title"))
                    or not isinstance(item.get("abstract"), str) or not isinstance(item.get("ids"), dict)
                    or not _number(item.get("score"))):
                raise ValueError()
        return {"paper_count": len(rows), "abstract_count": sum(bool(row["abstract"].strip()) for row in rows)}
    if probe.name == "firecrawl_credits":
        item = data.get("data")
        if (data.get("success") is not True or not isinstance(item, dict)
                or not _number(item.get("remainingCredits")) or not _number(item.get("planCredits"))
                or not _text(item.get("billingPeriodStart")) or not _text(item.get("billingPeriodEnd"))):
            raise ValueError()
        return {"credits_available": int(item["remainingCredits"] > 0)}
    if probe.name == "openalex_auth":
        item = data.get("rate_limit")
        fields = ("daily_budget_usd", "daily_used_usd", "daily_remaining_usd",
                  "prepaid_balance_usd", "prepaid_remaining_usd")
        if not isinstance(item, dict) or any(not _number(item.get(name)) for name in fields):
            raise ValueError()
        # Deliberately do not retain even the provider's masked api_key or the
        # account's balances. Accessibility is not a billing/auth outage proof.
        return {"budget_available": int(item["daily_remaining_usd"] > 0 or item["prepaid_remaining_usd"] > 0)}
    identity = "search_id" if probe.name == "parallel_search" else "extract_id"
    rows = data.get("results")
    if not _text(data.get(identity)) or not _text(data.get("session_id")) or not isinstance(rows, list) or len(rows) > 1:
        raise ValueError()
    for row in rows:
        if (not isinstance(row, dict) or not _text(row.get("url"))
                or urlsplit(row["url"]).scheme not in {"http", "https"}
                or row.get("title") is not None and not isinstance(row["title"], str)
                or row.get("publish_date") is not None and not isinstance(row["publish_date"], str)
                or not isinstance(row.get("excerpts"), list)
                or not all(isinstance(text, str) for text in row["excerpts"])):
            raise ValueError()
    if probe.name == "parallel_extract":
        if (data.get("errors") != [] or len(rows) != 1 or rows[0]["url"] != _EXTRACT_URL
                or not any(text.strip() for text in rows[0]["excerpts"])):
            raise ValueError()
    return {"result_count": len(rows), "error_count": 0}


def probe_request(probe: Probe, credential: str, transport=None) -> dict:
    """Perform at most one request; return only fixed enums and aggregate counts.

    Invalid local inputs raise a sanitized ServiceError before any effect. A
    successful public GitHub read is not proof of write scope or token identity.
    The caller must reserve probe.reserve_micro_usd before invoking this method.
    """
    _registered(probe)
    try:
        if credential_value(credential) is None:
            raise ValueError()
    except ValueError:
        raise ServiceError("INVALID_SOURCE_CREDENTIAL") from None
    headers = {"Accept": "application/json", "Accept-Encoding": "identity",
               "User-Agent": "context-research-connector-check/1", "Connection": "close"}
    if probe.name.startswith("parallel_"):
        headers["x-api-key"] = credential
    else:
        headers["Authorization"] = "Bearer " + credential
    if probe.payload is not None:
        headers["Content-Type"] = "application/json"
    if probe.name.startswith("github_"):
        headers["X-GitHub-Api-Version"] = "2022-11-28"
    report = {"schema": "connector-probe/v1", "name": probe.name,
              "classification": "transport_unknown", "http_status": None, "counts": {}}
    try:
        status, raw_headers, body = (transport or _https)(
            probe.method, probe.url, headers, probe.payload, TIMEOUT_SECONDS)
    except Exception:
        return report
    try:
        if type(status) is not int or not 100 <= status <= 599:
            raise ValueError()
        report["http_status"] = status
        if not isinstance(body, bytes) or len(body) > MAX_RESPONSE_BYTES:
            raise ValueError()
        response_headers = _headers(raw_headers)
        if _reflects(credential, body, raw_headers):
            raise ValueError()
        length = response_headers.get("content-length")
        if length is not None and (not length.isascii() or not length.isdecimal()
                                   or int(length) != len(body) or "transfer-encoding" in response_headers):
            raise ValueError()
        if response_headers.get("transfer-encoding", "chunked").lower() != "chunked":
            raise ValueError()
        if response_headers.get("content-encoding", "identity").lower() != "identity":
            raise ValueError()
        data = None
        if body:
            try:
                data = _json(body)
            except (ValueError, UnicodeError, RecursionError):
                if status == 200:
                    raise
        if _reflects(credential, b"", raw_headers, data):
            raise ValueError()
        if status != 200:
            report["classification"] = {
                401: "auth_rejected", 402: "billing_blocked", 403: "permission_denied",
                429: "rate_limited", 404: "endpoint_unavailable", 405: "endpoint_unavailable",
                410: "endpoint_unavailable",
            }.get(status, "endpoint_unavailable" if status >= 500 or 300 <= status < 400 else "schema_invalid")
            return report
        if response_headers.get("content-type", "").split(";", 1)[0].strip().lower() != "application/json":
            raise ValueError()
        report["counts"] = _success(probe, data)
        report["classification"] = "success"
    except Exception:
        report["classification"] = "schema_invalid"
        report["counts"] = {}
    return report
