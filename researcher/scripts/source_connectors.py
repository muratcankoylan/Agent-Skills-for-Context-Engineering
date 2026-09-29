#!/usr/bin/env python3
"""Bounded, observation-only source connectors.

This module is deliberately pre-accept and non-authoritative. Connectors return
immutable observations and never mutate queues or acceptance state. An explicit
capture sink may persist exact response bytes as private observations. There is
no arbitrary URL-fetch entry point: every network adapter owns
its endpoint and exact-host allowlist, while RSS/Atom feeds require an explicit
trusted-host configuration.

The injected resolver and transport boundaries make policy behavior testable
without network access. The default transport connects to the already-validated
IP address and uses the original hostname for TLS verification, preventing a
second DNS lookup between policy validation and connection establishment.
"""

from __future__ import annotations

import hashlib
import base64
import binascii
import http.client
import ipaddress
import json
import math
import os
import queue
import re
import socket
import ssl
import threading
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from typing import Callable, Iterable, Literal, Mapping, Protocol, Sequence, TypeAlias
from urllib.parse import quote, urlencode, urljoin, urlsplit, urlunsplit


USER_AGENT = "agent-skills-source-connectors/0.1 (observation-only)"
ABSOLUTE_MAX_ITEMS = 500
ABSOLUTE_MAX_REQUESTS = 64
ABSOLUTE_MAX_PAGES = 10
ABSOLUTE_MAX_BYTES = 1_500_000
ABSOLUTE_MAX_SECONDS = 30.0
ABSOLUTE_MAX_REDIRECTS = 5
REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})
SAFE_RESPONSE_HEADERS = frozenset(
    {
        "content-length",
        "content-type",
        "etag",
        "last-modified",
        "retry-after",
        "x-ratelimit-limit",
        "x-ratelimit-remaining",
        "x-ratelimit-reset",
        "x-rate-limit-limit",
        "x-rate-limit-remaining",
        "x-rate-limit-reset",
    }
)
XML_MEDIA_TYPES = frozenset(
    {"application/atom+xml", "application/rss+xml", "application/xml", "text/xml"}
)
JSON_MEDIA_TYPES = frozenset({"application/json", "application/problem+json"})
REPOSITORY_RE = re.compile(r"[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}\Z")
# getaddrinfo has no deadline API. Bound outstanding daemon lookups as well as
# caller wait time so a stuck system resolver cannot grow threads indefinitely.
_DNS_SLOTS = threading.BoundedSemaphore(8)
_CAPTURE_SLOTS = threading.BoundedSemaphore(4)
# Local discovery bound, not a guarantee of a provider-stable result snapshot.
_ARXIV_MAX_OFFSET = 30_000
_ATOM_NS = "http://www.w3.org/2005/Atom"
_ARXIV_NS = "http://arxiv.org/schemas/atom"
_RSS_CONTENT_NS = "http://purl.org/rss/1.0/modules/content/"
_XML_BASE = "{http://www.w3.org/XML/1998/namespace}base"
_ARXIV_ID = re.compile(
    r"(?P<work>(?:[0-9]{4}\.[0-9]{4,5}|[A-Za-z-]+(?:\.[A-Za-z]{2})?/[0-9]{7}))"
    r"(?:v(?P<version>[1-9][0-9]*))?\Z"
)
_X_LEGACY_FIELDS = "created_at,author_id,lang"
_X_ENRICHED_LEGACY_FIELDS = _X_LEGACY_FIELDS + ",entities,note_tweet,referenced_tweets"


class ConnectorError(RuntimeError):
    """Fail-closed connector error with a stable machine-readable code."""

    def __init__(self, code: str, message: str, receipt: Receipt | None = None):
        super().__init__(message)
        self.code = code
        self.receipt = receipt


class ConnectorDisabledError(ConnectorError):
    """The connector has no authority or credential to make an observation."""


class PolicyError(ConnectorError):
    """A request violated the outbound network policy."""


class LimitExceededError(ConnectorError):
    """A request or response exceeded a caller-supplied hard limit."""


class MalformedResponseError(ConnectorError):
    """A response failed its source-specific structural contract."""


@dataclass(frozen=True, slots=True)
class QuerySpec:
    """Connector-neutral query and opaque source cursor."""

    text: str = ""
    cursor: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.text, str) or len(self.text) > 2_048:
            raise ValueError("query text must be a string of at most 2048 characters")
        if any(
            ord(character) < 32 and character not in "\t\n" for character in self.text
        ):
            raise ValueError("query text contains an unsupported control character")
        if self.cursor is not None:
            if not isinstance(self.cursor, str) or len(self.cursor) > 2_048:
                raise ValueError("cursor must be a string of at most 2048 characters")
            if "\r" in self.cursor or "\n" in self.cursor:
                raise ValueError("cursor cannot contain line breaks")


@dataclass(frozen=True, slots=True)
class Limits:
    """Hard, per-discovery-call ceilings; zero means make no network request."""

    max_items: int = 50
    max_requests: int = 8
    max_pages: int = 1
    max_bytes: int = 1_500_000
    max_seconds: float = 30.0
    max_redirects: int = 3

    def __post_init__(self) -> None:
        integer_limits = {
            "max_items": self.max_items,
            "max_requests": self.max_requests,
            "max_pages": self.max_pages,
            "max_bytes": self.max_bytes,
            "max_redirects": self.max_redirects,
        }
        for name, value in integer_limits.items():
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        if (
            isinstance(self.max_seconds, bool)
            or not isinstance(self.max_seconds, (int, float))
            or not math.isfinite(float(self.max_seconds))
            or self.max_seconds < 0
        ):
            raise ValueError("max_seconds must be a finite non-negative number")
        absolute_ceilings = {
            "max_items": (self.max_items, ABSOLUTE_MAX_ITEMS),
            "max_requests": (self.max_requests, ABSOLUTE_MAX_REQUESTS),
            "max_pages": (self.max_pages, ABSOLUTE_MAX_PAGES),
            "max_bytes": (self.max_bytes, ABSOLUTE_MAX_BYTES),
            "max_seconds": (float(self.max_seconds), ABSOLUTE_MAX_SECONDS),
            "max_redirects": (self.max_redirects, ABSOLUTE_MAX_REDIRECTS),
        }
        for name, (value, ceiling) in absolute_ceilings.items():
            if value > ceiling:
                raise ValueError(
                    f"{name} exceeds the connector absolute ceiling {ceiling}"
                )

    @property
    def permits_observation(self) -> bool:
        return all(
            (
                self.max_items > 0,
                self.max_requests > 0,
                self.max_pages > 0,
                self.max_bytes > 0,
                self.max_seconds > 0,
            )
        )


@dataclass(frozen=True, slots=True, repr=False)
class Lead:
    """Untrusted private observation, granting no fetch or acceptance authority.

    URLs retain source-supplied queries because these can identify the article.
    Public projection must review these values, just as it reviews source text.
    """

    identity: str
    source: str
    title: str
    url: str
    published_at: str | None = None
    summary: str = ""
    metadata: tuple[tuple[str, str], ...] = ()

    def __repr__(self) -> str:
        return (
            f"Lead(identity={self.identity!r}, source={self.source!r}, "
            f"url={_redact_request_url(self.url)!r})"
        )

    def __post_init__(self) -> None:
        for name, value, maximum in (
            ("identity", self.identity, 160),
            ("source", self.source, 64),
            ("title", self.title, 8_192),
            ("url", self.url, 8_192),
            ("summary", self.summary, 16_384),
        ):
            if not isinstance(value, str) or not value or len(value) > maximum:
                if name == "summary" and value == "":
                    continue
                raise ValueError(
                    f"{name} must be a non-empty string within {maximum} characters"
                )
        if self.published_at is not None and (
            not isinstance(self.published_at, str) or len(self.published_at) > 128
        ):
            raise ValueError("published_at must be null or a short string")
        if not isinstance(self.metadata, tuple) or any(
            not isinstance(item, tuple)
            or len(item) != 2
            or not all(isinstance(value, str) for value in item)
            for item in self.metadata
        ):
            raise ValueError("metadata must be a tuple of string pairs")
        parsed = urlsplit(self.url)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
        ):
            raise ValueError("lead URLs must be credential-free HTTPS URLs")


@dataclass(frozen=True, slots=True)
class ResponseObservation:
    """Redacted provenance for one exact response body."""

    request_url: str
    query_redacted: bool
    resolved_ips: tuple[str, ...]
    connected_ip: str
    status_code: int
    media_type: str
    response_bytes: int
    response_sha256: str
    elapsed_ms: int
    safe_headers: tuple[tuple[str, str], ...] = ()
    truncated: bool = False


# Sinks receive only redacted observation metadata and the exact bounded body.
# Return values are caller-owned private records, not acceptance authority. The
# sink must be safe to run on a worker thread and write only immutable captures;
# a timed-out sink can finish an orphan after discovery has already failed.
ResponseCaptureSink: TypeAlias = Callable[[ResponseObservation, bytes], object]


@dataclass(frozen=True, slots=True)
class Receipt:
    """Aggregate, non-authoritative receipt for one connector call."""

    connector: str
    observed_at: str
    observations: tuple[ResponseObservation, ...]
    request_count: int
    total_bytes: int
    elapsed_ms: int
    item_count: int
    observation_only: bool = True
    authoritative: bool = False

    def __post_init__(self) -> None:
        if self.request_count < len(self.observations):
            raise ValueError("request_count cannot be below completed observations")
        if self.total_bytes != sum(item.response_bytes for item in self.observations):
            raise ValueError("total_bytes must equal observed exact response bytes")
        if self.item_count < 0 or self.elapsed_ms < 0:
            raise ValueError("receipt counters cannot be negative")
        if not self.observation_only or self.authoritative:
            raise ValueError("source connector receipts are observation-only")


@dataclass(frozen=True, slots=True)
class LeadPage:
    """A bounded page of untrusted leads and its exact observation receipt."""

    items: tuple[Lead, ...]
    next_cursor: str | None
    receipt: Receipt

    def __post_init__(self) -> None:
        if self.receipt.item_count != len(self.items):
            raise ValueError("receipt item_count must equal the page size")


@dataclass(frozen=True, slots=True)
class RetryAfter:
    """Typed, non-sleeping rate-limit result."""

    retry_after_seconds: int | None
    receipt: Receipt

    def __post_init__(self) -> None:
        if self.retry_after_seconds is not None and self.retry_after_seconds < 0:
            raise ValueError("retry_after_seconds cannot be negative")


DiscoveryResult: TypeAlias = LeadPage | RetryAfter


@dataclass(frozen=True, slots=True, repr=False)
class TransportRequest:
    """Pinned-IP transport request; repr intentionally omits query and values."""

    url: str
    connect_ip: str
    headers: tuple[tuple[str, str], ...]
    deadline: float
    max_bytes: int

    def __repr__(self) -> str:
        return (
            "TransportRequest("
            f"url={_redact_request_url(self.url)!r}, "
            f"connect_ip={self.connect_ip!r}, "
            f"header_names={tuple(name for name, _ in self.headers)!r}, "
            f"deadline={self.deadline!r}, max_bytes={self.max_bytes!r})"
        )


@dataclass(frozen=True, slots=True)
class TransportResponse:
    status_code: int
    headers: tuple[tuple[str, str], ...]
    body: bytes
    truncated: bool = False

    def __post_init__(self) -> None:
        if (
            isinstance(self.status_code, bool)
            or not isinstance(self.status_code, int)
            or not 100 <= self.status_code <= 599
        ):
            raise ValueError("status_code must be an HTTP status integer")
        if not isinstance(self.headers, tuple) or any(
            not isinstance(item, tuple) or len(item) != 2 for item in self.headers
        ):
            raise ValueError("headers must be a tuple of pairs")
        if not isinstance(self.body, bytes):
            raise ValueError("body must be exact bytes")
        if not isinstance(self.truncated, bool):
            raise ValueError("truncated must be boolean")


class Resolver(Protocol):
    def __call__(self, hostname: str, port: int) -> Sequence[str]: ...


class Transport(Protocol):
    def request(self, request: TransportRequest) -> TransportResponse: ...


Clock: TypeAlias = Callable[[], float]
WallClock: TypeAlias = Callable[[], datetime]


def _system_resolver(
    hostname: str, port: int, *, timeout: float = ABSOLUTE_MAX_SECONDS
) -> tuple[str, ...]:
    if timeout <= 0:
        raise LimitExceededError("TIME_LIMIT", "DNS deadline was exhausted")
    if not _DNS_SLOTS.acquire(blocking=False):
        raise PolicyError("DNS_CAPACITY", "bounded DNS lookup capacity is exhausted")
    result: queue.Queue[object] = queue.Queue(maxsize=1)

    def resolve() -> None:
        try:
            result.put(socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM))
        except Exception as exc:
            result.put(exc)
        finally:
            _DNS_SLOTS.release()

    worker = threading.Thread(target=resolve, name="source-dns", daemon=True)
    try:
        worker.start()
    except Exception:
        _DNS_SLOTS.release()
        raise
    try:
        records = result.get(timeout=timeout)
    except queue.Empty as exc:
        raise LimitExceededError(
            "TIME_LIMIT", "DNS lookup exceeded its deadline"
        ) from exc
    if isinstance(records, Exception):
        raise PolicyError(
            "DNS_FAILURE", "source hostname could not be resolved"
        ) from records
    addresses: list[str] = []
    for record in records:
        address = str(record[4][0])
        if address not in addresses:
            addresses.append(address)
    return tuple(addresses)


class PinnedHTTPSTransport:
    """Minimal GET-only HTTPS transport with pinned address and absolute deadline."""

    def __init__(
        self,
        *,
        clock: Clock = time.monotonic,
        ssl_context: ssl.SSLContext | None = None,
    ):
        self._clock = clock
        self._ssl_context = ssl_context or ssl.create_default_context()

    def _remaining(self, deadline: float) -> float:
        remaining = deadline - self._clock()
        if remaining <= 0:
            raise LimitExceededError(
                "TIME_LIMIT", "connector wall-time limit was exhausted"
            )
        return remaining

    def request(self, request: TransportRequest) -> TransportResponse:
        parsed = urlsplit(request.url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise PolicyError("HTTPS_REQUIRED", "transport accepts only HTTPS URLs")
        port = parsed.port or 443
        target = urlunsplit(("", "", parsed.path or "/", parsed.query, ""))
        try:
            target.encode("ascii")
        except UnicodeEncodeError as exc:
            raise PolicyError(
                "URL_ENCODING", "request URL must be ASCII/percent-encoded"
            ) from exc

        headers = list(request.headers)
        host_header = parsed.hostname if port == 443 else f"{parsed.hostname}:{port}"
        headers.extend((("Host", host_header), ("Connection", "close")))
        for name, value in headers:
            if not name or any(character in name for character in "\r\n:"):
                raise PolicyError("HEADER_INVALID", "request header name is invalid")
            if "\r" in value or "\n" in value:
                raise PolicyError("HEADER_INVALID", "request header value is invalid")
        request_bytes = (
            f"GET {target} HTTP/1.1\r\n"
            + "".join(f"{name}: {value}\r\n" for name, value in headers)
            + "\r\n"
        ).encode("ascii")

        raw_socket: socket.socket | None = None
        tls_socket: ssl.SSLSocket | None = None
        deadline_timer: threading.Timer | None = None

        def interrupt_at_deadline() -> None:
            # Per-read socket timeouts do not stop a peer that trickles headers
            # or chunk framing forever. Shutdown bounds the whole TLS exchange.
            active = tls_socket if tls_socket is not None else raw_socket
            if active is not None:
                try:
                    active.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass

        try:
            raw_socket = socket.create_connection(
                (request.connect_ip, port), timeout=self._remaining(request.deadline)
            )
            raw_socket.settimeout(self._remaining(request.deadline))
            deadline_timer = threading.Timer(
                self._remaining(request.deadline), interrupt_at_deadline
            )
            deadline_timer.daemon = True
            deadline_timer.start()
            tls_socket = self._ssl_context.wrap_socket(
                raw_socket,
                server_hostname=parsed.hostname,
            )
            raw_socket = None  # Ownership transferred to the TLS socket.
            tls_socket.settimeout(self._remaining(request.deadline))
            tls_socket.sendall(request_bytes)
            tls_socket.settimeout(self._remaining(request.deadline))
            response = http.client.HTTPResponse(tls_socket)
            response.begin()
            headers_out = tuple((name, value) for name, value in response.getheaders())
            content_encoding = _first_header(headers_out, "content-encoding")
            if content_encoding and content_encoding.strip().lower() != "identity":
                raise PolicyError(
                    "CONTENT_ENCODING_UNSUPPORTED",
                    "compressed responses are rejected to preserve decoded-byte limits",
                )
            content_length = _content_length(headers_out)
            if content_length is not None and content_length > request.max_bytes:
                raise LimitExceededError(
                    "BYTE_LIMIT", "response exceeds the byte limit"
                )

            chunks: list[bytes] = []
            received = 0
            truncated = False
            while True:
                tls_socket.settimeout(self._remaining(request.deadline))
                allowance = request.max_bytes - received
                if allowance < 0:
                    raise LimitExceededError(
                        "BYTE_LIMIT", "response exceeds the byte limit"
                    )
                try:
                    chunk = response.read(min(65_536, allowance + 1))
                except http.client.IncompleteRead as exc:
                    chunk = exc.partial
                    truncated = True
                if chunk:
                    chunks.append(chunk)
                    received += len(chunk)
                    if received > request.max_bytes:
                        raise LimitExceededError(
                            "BYTE_LIMIT", "response exceeds the byte limit"
                        )
                if truncated or not chunk:
                    break
            if content_length is not None and received != content_length:
                truncated = True
            return TransportResponse(
                response.status, headers_out, b"".join(chunks), truncated
            )
        except (TimeoutError, socket.timeout) as exc:
            raise LimitExceededError(
                "TIME_LIMIT", "connector request exceeded its deadline"
            ) from exc
        except (ssl.SSLError, OSError, http.client.HTTPException) as exc:
            self._remaining(request.deadline)
            raise ConnectorError("TRANSPORT_FAILURE", "HTTPS transport failed") from exc
        finally:
            if deadline_timer is not None:
                deadline_timer.cancel()
            if tls_socket is not None:
                tls_socket.close()
            if raw_socket is not None:
                raw_socket.close()


@dataclass(slots=True)
class _Budget:
    limits: Limits
    clock: Clock
    now: WallClock
    started: float
    observations: list[ResponseObservation]
    request_count: int = 0

    @classmethod
    def start(cls, limits: Limits, clock: Clock, now: WallClock) -> _Budget:
        return cls(limits, clock, now, clock(), [])

    @property
    def deadline(self) -> float:
        return self.started + float(self.limits.max_seconds)

    @property
    def total_bytes(self) -> int:
        return sum(item.response_bytes for item in self.observations)

    def remaining_bytes(self) -> int:
        return self.limits.max_bytes - self.total_bytes

    def before_request(self) -> None:
        if self.request_count >= self.limits.max_requests:
            raise LimitExceededError(
                "REQUEST_LIMIT", "connector request limit was exhausted"
            )
        if self.remaining_bytes() <= 0:
            raise LimitExceededError("BYTE_LIMIT", "connector byte limit was exhausted")
        if self.clock() >= self.deadline:
            raise LimitExceededError(
                "TIME_LIMIT", "connector wall-time limit was exhausted"
            )

    def after_transport(self) -> None:
        if self.clock() > self.deadline:
            raise LimitExceededError(
                "TIME_LIMIT", "connector wall-time limit was exceeded"
            )

    def receipt(self, connector: str, item_count: int) -> Receipt:
        instant = self.now()
        if instant.tzinfo is None or instant.utcoffset() is None:
            raise ValueError("wall clock must return a timezone-aware datetime")
        elapsed_ms = max(0, math.ceil((self.clock() - self.started) * 1_000))
        observations = tuple(self.observations)
        return Receipt(
            connector=connector,
            observed_at=instant.astimezone(UTC)
            .isoformat(timespec="seconds")
            .replace("+00:00", "Z"),
            observations=observations,
            request_count=self.request_count,
            total_bytes=sum(item.response_bytes for item in observations),
            elapsed_ms=elapsed_ms,
            item_count=item_count,
        )


@dataclass(frozen=True, slots=True)
class _FetchedResponse:
    url: str
    body: bytes
    media_type: str


@dataclass(frozen=True, slots=True)
class _RateLimited:
    seconds: int | None


class _SafeHTTPClient:
    def __init__(
        self,
        *,
        transport: Transport | None,
        resolver: Resolver,
        clock: Clock,
        now: WallClock,
        capture_sink: ResponseCaptureSink | None = None,
    ):
        if capture_sink is not None and not callable(capture_sink):
            raise ValueError("capture_sink must be callable")
        self._clock = clock
        self._now = now
        self._resolver = resolver
        self._transport = transport or PinnedHTTPSTransport(clock=clock)
        self._capture_sink = capture_sink

    def _capture(
        self, observation: ResponseObservation, body: bytes, budget: _Budget
    ) -> None:
        if self._capture_sink is None:
            return
        budget.after_transport()
        if not _CAPTURE_SLOTS.acquire(blocking=False):
            raise ConnectorError(
                "CAPTURE_CAPACITY", "bounded capture capacity is exhausted"
            )
        completed: queue.Queue[bool] = queue.Queue(maxsize=1)

        def capture() -> None:
            try:
                assert self._capture_sink is not None
                self._capture_sink(observation, body)
                completed.put(True)
            except BaseException:
                # Exception details can contain private locators or source text.
                completed.put(False)
            finally:
                _CAPTURE_SLOTS.release()

        worker = threading.Thread(target=capture, name="source-capture", daemon=True)
        try:
            worker.start()
        except Exception:
            _CAPTURE_SLOTS.release()
            raise ConnectorError(
                "CAPTURE_FAILURE", "response capture could not start"
            ) from None
        try:
            succeeded = completed.get(timeout=max(0, budget.deadline - self._clock()))
        except queue.Empty:
            # A slow filesystem may finish an immutable orphan after timeout.
            # No successful discovery result or cursor is returned in that case.
            raise LimitExceededError(
                "TIME_LIMIT", "response capture exceeded its deadline"
            ) from None
        if not succeeded:
            raise ConnectorError("CAPTURE_FAILURE", "response capture sink failed")
        budget.after_transport()

    def get(
        self,
        *,
        connector: str,
        url: str,
        allowed_hosts: frozenset[str],
        headers: tuple[tuple[str, str], ...],
        budget: _Budget,
    ) -> _FetchedResponse | _RateLimited:
        try:
            return self._get(
                connector=connector,
                url=url,
                allowed_hosts=allowed_hosts,
                headers=headers,
                budget=budget,
            )
        except ConnectorError as exc:
            if exc.receipt is None:
                exc.receipt = budget.receipt(connector, 0)
            raise

    def _get(
        self,
        *,
        connector: str,
        url: str,
        allowed_hosts: frozenset[str],
        headers: tuple[tuple[str, str], ...],
        budget: _Budget,
    ) -> _FetchedResponse | _RateLimited:
        current_url = url
        redirects = 0
        while True:
            parsed, hostname = _validate_outbound_url(current_url, allowed_hosts)
            budget.before_request()
            resolver = self._resolver
            if resolver is _system_resolver:

                def resolver(host: str, port: int) -> tuple[str, ...]:
                    return _system_resolver(
                        host, port, timeout=budget.deadline - self._clock()
                    )

            resolved_ips = _resolve_public_ips(resolver, hostname, 443)
            budget.before_request()
            connected_ip = resolved_ips[0]
            started = self._clock()
            budget.request_count += 1
            response = self._transport.request(
                TransportRequest(
                    url=current_url,
                    connect_ip=connected_ip,
                    headers=headers,
                    deadline=budget.deadline,
                    max_bytes=budget.remaining_bytes(),
                )
            )
            budget.after_transport()
            normalized_headers = _normalize_headers(response.headers)
            content_encoding = _first_header(normalized_headers, "content-encoding")
            if content_encoding and content_encoding.strip().lower() != "identity":
                raise PolicyError(
                    "CONTENT_ENCODING_UNSUPPORTED",
                    "compressed responses are rejected to preserve decoded-byte limits",
                    budget.receipt(connector, 0),
                )
            if len(response.body) > budget.remaining_bytes():
                raise LimitExceededError(
                    "BYTE_LIMIT", "response exceeds the total byte limit"
                )
            content_length = _content_length(normalized_headers)
            if content_length is not None and len(response.body) != content_length:
                response = TransportResponse(
                    response.status_code,
                    response.headers,
                    response.body,
                    truncated=True,
                )
            media_type = _media_type(normalized_headers)
            observation = ResponseObservation(
                request_url=_redact_request_url(current_url),
                query_redacted=bool(parsed.query),
                resolved_ips=resolved_ips,
                connected_ip=connected_ip,
                status_code=response.status_code,
                media_type=media_type,
                response_bytes=len(response.body),
                response_sha256="sha256:" + hashlib.sha256(response.body).hexdigest(),
                elapsed_ms=max(0, math.ceil((self._clock() - started) * 1_000)),
                safe_headers=_safe_headers(normalized_headers),
                truncated=response.truncated,
            )
            budget.observations.append(observation)
            self._capture(observation, response.body, budget)
            if response.truncated:
                raise MalformedResponseError(
                    "TRUNCATED_RESPONSE",
                    "truncated response was rejected",
                    budget.receipt(connector, 0),
                )

            if response.status_code in REDIRECT_STATUSES:
                location = _first_header(normalized_headers, "location")
                if not location:
                    raise MalformedResponseError(
                        "REDIRECT_INVALID",
                        "redirect response has no Location header",
                        budget.receipt(connector, 0),
                    )
                if redirects >= budget.limits.max_redirects:
                    raise LimitExceededError(
                        "REDIRECT_LIMIT",
                        "connector redirect limit was exhausted",
                        budget.receipt(connector, 0),
                    )
                current_url = urljoin(current_url, location)
                redirects += 1
                continue

            if response.status_code == 429:
                return _RateLimited(_parse_retry_after(normalized_headers, self._now()))
            if not 200 <= response.status_code < 300:
                raise ConnectorError(
                    "HTTP_STATUS",
                    f"source returned HTTP {response.status_code}",
                    budget.receipt(connector, 0),
                )
            return _FetchedResponse(current_url, response.body, media_type)


def _default_now() -> datetime:
    return datetime.now(UTC)


def _normalize_allowed_hosts(hosts: Iterable[str]) -> frozenset[str]:
    normalized: set[str] = set()
    for host in hosts:
        if not isinstance(host, str) or not host or "/" in host or ":" in host:
            raise ValueError("allowed hosts must be exact DNS hostnames without ports")
        try:
            ascii_host = host.encode("idna").decode("ascii").lower().rstrip(".")
        except UnicodeError as exc:
            raise ValueError("allowed host is invalid") from exc
        if not ascii_host or ascii_host.startswith("."):
            raise ValueError("allowed host is invalid")
        normalized.add(ascii_host)
    if not normalized:
        raise ValueError("at least one exact allowed host is required")
    return frozenset(normalized)


def _validate_outbound_url(
    url: str, allowed_hosts: frozenset[str]
) -> tuple[object, str]:
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except (TypeError, ValueError) as exc:
        raise PolicyError("URL_INVALID", "source URL is invalid") from exc
    if parsed.scheme != "https":
        raise PolicyError("HTTPS_REQUIRED", "source URL must use HTTPS")
    if (
        not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise PolicyError(
            "URL_CREDENTIALS", "source URL must have a credential-free hostname"
        )
    try:
        hostname = parsed.hostname.encode("idna").decode("ascii").lower().rstrip(".")
    except UnicodeError as exc:
        raise PolicyError("URL_INVALID", "source hostname is invalid") from exc
    if hostname not in allowed_hosts:
        raise PolicyError(
            "HOST_NOT_ALLOWED", "source hostname is not exactly allowlisted"
        )
    if port not in (None, 443):
        raise PolicyError(
            "PORT_NOT_ALLOWED", "source URL must use the standard HTTPS port"
        )
    if parsed.fragment:
        raise PolicyError("URL_FRAGMENT", "request URLs cannot contain fragments")
    return parsed, hostname


def _resolve_public_ips(
    resolver: Resolver, hostname: str, port: int
) -> tuple[str, ...]:
    try:
        values = resolver(hostname, port)
    except ConnectorError:
        raise
    except Exception as exc:
        raise PolicyError(
            "DNS_FAILURE", "source hostname could not be resolved"
        ) from exc
    addresses: list[str] = []
    for raw in values:
        try:
            address = ipaddress.ip_address(str(raw).split("%", 1)[0])
        except ValueError as exc:
            raise PolicyError(
                "DNS_INVALID", "DNS returned an invalid IP address"
            ) from exc
        if not address.is_global:
            raise PolicyError("DNS_NOT_PUBLIC", "DNS returned a non-public IP address")
        canonical = address.compressed
        if canonical not in addresses:
            addresses.append(canonical)
    if not addresses:
        raise PolicyError("DNS_EMPTY", "DNS returned no usable IP address")
    return tuple(addresses)


def _normalize_headers(
    headers: Iterable[tuple[str, str]],
) -> tuple[tuple[str, str], ...]:
    normalized: list[tuple[str, str]] = []
    for name, value in headers:
        if not isinstance(name, str) or not isinstance(value, str):
            raise MalformedResponseError(
                "HEADER_INVALID", "response headers must be strings"
            )
        if "\r" in name or "\n" in name or "\r" in value or "\n" in value:
            raise MalformedResponseError(
                "HEADER_INVALID", "response header contains a line break"
            )
        normalized.append((name.strip().lower(), value.strip()))
    return tuple(normalized)


def _first_header(headers: Iterable[tuple[str, str]], name: str) -> str | None:
    expected = name.lower()
    for header_name, value in headers:
        if header_name.lower() == expected:
            return value
    return None


def _content_length(headers: Iterable[tuple[str, str]]) -> int | None:
    raw_values = [
        value.strip() for name, value in headers if name.lower() == "content-length"
    ]
    if not raw_values:
        return None
    if len(set(raw_values)) != 1 or not raw_values[0].isdigit():
        raise MalformedResponseError(
            "CONTENT_LENGTH_INVALID", "Content-Length is invalid"
        )
    return int(raw_values[0])


def _media_type(headers: Iterable[tuple[str, str]]) -> str:
    value = _first_header(headers, "content-type")
    return value.split(";", 1)[0].strip().lower() if value else ""


def _safe_headers(headers: Iterable[tuple[str, str]]) -> tuple[tuple[str, str], ...]:
    return tuple(
        (name, value) for name, value in headers if name in SAFE_RESPONSE_HEADERS
    )


def _redact_request_url(url: str) -> str:
    parsed = urlsplit(url)
    hostname = parsed.hostname or "invalid"
    try:
        port = parsed.port
    except ValueError:
        port = None
    netloc = hostname.lower()
    if port and port != 443:
        netloc = f"{netloc}:{port}"
    return urlunsplit((parsed.scheme.lower(), netloc, parsed.path or "/", "", ""))


def _parse_retry_after(headers: Iterable[tuple[str, str]], now: datetime) -> int | None:
    raw = _first_header(headers, "retry-after")
    if raw is None:
        return None
    stripped = raw.strip()
    if stripped.isdigit():
        return int(stripped)
    try:
        instant = parsedate_to_datetime(stripped)
    except (TypeError, ValueError, OverflowError):
        return None
    if instant.tzinfo is None:
        instant = instant.replace(tzinfo=UTC)
    if now.tzinfo is None or now.utcoffset() is None:
        return None
    return max(0, math.ceil((instant - now).total_seconds()))


def _empty_page(connector: str, query: QuerySpec, budget: _Budget) -> LeadPage:
    return LeadPage((), query.cursor, budget.receipt(connector, 0))


def _rate_limit_result(
    connector: str, rate: _RateLimited, budget: _Budget
) -> RetryAfter:
    return RetryAfter(rate.seconds, budget.receipt(connector, 0))


def _require_media_type(
    connector: str,
    response: _FetchedResponse,
    allowed: frozenset[str],
    budget: _Budget,
) -> None:
    if response.media_type not in allowed:
        raise MalformedResponseError(
            "MEDIA_TYPE_UNEXPECTED",
            "source returned an unexpected media type",
            budget.receipt(connector, 0),
        )


def _parse_json(connector: str, response: _FetchedResponse, budget: _Budget) -> object:
    _require_media_type(connector, response, JSON_MEDIA_TYPES, budget)
    try:
        text = response.body.decode("utf-8", errors="strict")
        return json.loads(
            text,
            object_pairs_hook=_strict_object_pairs,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"non-finite JSON number: {value}")
            ),
        )
    except (UnicodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise MalformedResponseError(
            "JSON_MALFORMED",
            "source returned malformed JSON",
            budget.receipt(connector, 0),
        ) from exc


def _strict_object_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate JSON object key")
        value[key] = item
    return value


def _parse_xml(
    connector: str, response: _FetchedResponse, budget: _Budget
) -> ET.Element:
    _require_media_type(connector, response, XML_MEDIA_TYPES, budget)
    uppercase_body = response.body.upper()
    if b"<!DOCTYPE" in uppercase_body or b"<!ENTITY" in uppercase_body:
        raise MalformedResponseError(
            "XML_UNSAFE",
            "DTD and entity declarations are not accepted",
            budget.receipt(connector, 0),
        )

    class NoDTDTreeBuilder(ET.TreeBuilder):
        def doctype(self, name: str, pubid: str | None, system: str | None) -> None:
            # Parser-level rejection also covers UTF-16 declarations that a
            # byte substring scan cannot recognize before character decoding.
            raise MalformedResponseError(
                "XML_UNSAFE",
                "DTD declarations are not accepted",
                budget.receipt(connector, 0),
            )

    try:
        return ET.fromstring(
            response.body, parser=ET.XMLParser(target=NoDTDTreeBuilder())
        )
    except ET.ParseError as exc:
        raise MalformedResponseError(
            "XML_MALFORMED",
            "source returned malformed XML",
            budget.receipt(connector, 0),
        ) from exc


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _child_text(element: ET.Element, names: frozenset[str]) -> str | None:
    for child in element:
        if _local_name(child.tag) in names:
            value = "".join(child.itertext()).strip()
            if value:
                return value
    return None


def _entry_link(
    element: ET.Element, *, bases: Mapping[int, str] | None = None
) -> str | None:
    for child in element:
        if _local_name(child.tag) != "link":
            continue
        href = child.attrib.get("href")
        relation = child.attrib.get("rel", "alternate")
        if href and relation in {"alternate", ""}:
            return (
                urljoin(bases[id(child)], href.strip())
                if bases is not None
                else href.strip()
            )
        value = "".join(child.itertext()).strip()
        if value:
            return urljoin(bases[id(child)], value) if bases is not None else value
    return None


def _canonical_url(url: str, *, base_url: str) -> str:
    absolute = urljoin(base_url, url.strip())
    try:
        parsed = urlsplit(absolute)
        port = parsed.port
    except (TypeError, ValueError) as exc:
        raise ValueError("lead URL is invalid") from exc
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
    ):
        raise ValueError("lead URL must be credential-free HTTPS")
    hostname = parsed.hostname.encode("idna").decode("ascii").lower().rstrip(".")
    netloc = hostname if port in (None, 443) else f"{hostname}:{port}"
    return urlunsplit(("https", netloc, parsed.path or "/", parsed.query, ""))


def _identity(source: str, stable_key: str) -> str:
    digest = hashlib.sha256(f"{source}\0{stable_key}".encode("utf-8")).hexdigest()
    return f"{source}:sha256:{digest}"


def _bounded_text(value: str | None, maximum: int) -> str:
    if not value:
        return ""
    return " ".join(value.split())[:maximum]


def _xml_bases(root: ET.Element, response_url: str) -> dict[int, str]:
    bases: dict[int, str] = {}
    pending = [(root, response_url)]
    while pending:
        element, parent_base = pending.pop()
        base = urljoin(parent_base, element.attrib.get(_XML_BASE, ""))
        bases[id(element)] = base
        pending.extend((child, base) for child in element)
    return bases


class _FeedHTMLText(HTMLParser):
    """Text-only feed extraction; no rendering, execution, or linked retrieval."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.hidden = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self.hidden += 1
        elif not self.hidden:
            self.parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self.hidden:
            self.hidden -= 1
        elif not self.hidden:
            self.parts.append(" ")

    def handle_data(self, data: str) -> None:
        if not self.hidden:
            self.parts.append(data)


def _feed_summary(entry: ET.Element) -> tuple[str, str]:
    # Selection is explicit rather than whichever of summary/content appears
    # first in the XML. A content src URL is only a link, never fetched here.
    choices = (
        (f"{{{_RSS_CONTENT_NS}}}encoded", "rss_content_encoded"),
        (f"{{{_ATOM_NS}}}content", "atom_content"),
        ("content", "feed_content"),
        (f"{{{_ATOM_NS}}}summary", "atom_summary"),
        ("summary", "feed_summary"),
        ("description", "rss_description"),
    )
    for tag, kind in choices:
        for child in entry:
            if child.tag != tag:
                continue
            value = " ".join(child.itertext()).strip()
            if not value:
                continue
            if kind in {"rss_content_encoded", "rss_description"} or child.get(
                "type", "text"
            ) in {"html", "text/html"}:
                parser = _FeedHTMLText()
                parser.feed(value)
                parser.close()
                value = "".join(parser.parts)
            normalized = " ".join(value.split())
            if normalized:
                return normalized, kind
    return "", "none"


def _bounded_metadata(
    values: Iterable[tuple[str, str]],
) -> tuple[tuple[str, str], ...]:
    items = tuple(values)
    if (
        len(items) > 96
        or any(len(key) > 64 or len(value) > 8_192 for key, value in items)
        or sum(len((key + value).encode("utf-8")) for key, value in items) > 32_768
    ):
        raise ValueError("source metadata exceeds its bounds")
    return items


def _arxiv_article_metadata(
    entry: ET.Element, article_url: str, bases: Mapping[int, str]
) -> tuple[tuple[str, str], ...]:
    article = urlsplit(article_url)
    identifier = article.path.removeprefix("/abs/")
    match = _ARXIV_ID.fullmatch(identifier)
    if (
        match is None
        or article.port not in (None, 443)
        or article.query
        or article.fragment
    ):
        raise ValueError("arXiv article identity is invalid")
    values = [("work_id", "arxiv:" + match["work"])]
    if match["version"]:
        values.append(("version", match["version"]))
    stable_id = _child_text(entry, frozenset({"id"}))
    if stable_id:
        parsed_id = urlsplit(stable_id)
        if (
            parsed_id.scheme not in {"http", "https"}
            or parsed_id.hostname not in {"arxiv.org", "export.arxiv.org"}
            or parsed_id.path != article.path
            or parsed_id.username
            or parsed_id.password
            or parsed_id.port not in (None, 80, 443)
            or parsed_id.query
            or parsed_id.fragment
        ):
            raise ValueError("arXiv entry identity conflicts with its article link")
    for child in entry:
        if child.tag == f"{{{_ARXIV_NS}}}doi":
            doi = "".join(child.itertext()).strip()
            if doi:
                if not re.fullmatch(r"10\.[0-9]{4,9}/\S+", doi):
                    raise ValueError("arXiv DOI is malformed")
                values.append(("doi", doi))
        elif child.tag == f"{{{_ARXIV_NS}}}primary_category":
            if child.get("term"):
                values.append(("primary_category", child.attrib["term"]))
        elif _local_name(child.tag) == "category" and child.get("term"):
            values.append(("category", child.attrib["term"]))
        elif (
            _local_name(child.tag) == "link"
            and child.get("type") == "application/pdf"
            and child.get("href")
        ):
            candidate = urljoin(bases[id(child)], child.attrib["href"])
            parsed = urlsplit(candidate)
            if (
                parsed.scheme == "http"
                and parsed.hostname in {"arxiv.org", "export.arxiv.org"}
                and parsed.port in (None, 80)
                and not parsed.username
                and not parsed.password
            ):
                candidate = urlunsplit(
                    (
                        "https",
                        parsed.hostname,
                        parsed.path,
                        parsed.query,
                        parsed.fragment,
                    )
                )
            pdf = _canonical_url(candidate, base_url=bases[id(child)])
            parsed = urlsplit(pdf)
            if (
                parsed.hostname not in {"arxiv.org", "export.arxiv.org"}
                or parsed.port not in (None, 443)
                or parsed.path != "/pdf/" + identifier
                or parsed.query
            ):
                raise ValueError("arXiv PDF link does not identify this article")
            values.append(("pdf_url", pdf))
    for key in ("doi", "primary_category", "pdf_url"):
        if len({value for name, value in values if name == key}) > 1:
            raise ValueError("arXiv provenance contains conflicting singleton fields")
    return tuple(dict.fromkeys(values))


def _feed_leads(
    *,
    connector: str,
    response: _FetchedResponse,
    budget: _Budget,
    limit: int | None,
    watermark: str | None,
    terms: tuple[str, ...] = (),
    upgrade_http_hosts: frozenset[str] = frozenset(),
    include_provenance: bool = False,
) -> tuple[Lead, ...]:
    root = _parse_xml(connector, response, budget)
    root_name = _local_name(root.tag)
    if root_name == "feed":
        entries = [child for child in root if _local_name(child.tag) == "entry"]
    elif root_name in {"rss", "rdf"}:
        entries = [child for child in root.iter() if _local_name(child.tag) == "item"]
    else:
        raise MalformedResponseError(
            "FEED_SCHEMA_INVALID",
            "XML document is not an Atom or RSS feed",
            budget.receipt(connector, 0),
        )

    try:
        bases = _xml_bases(root, response.url) if include_provenance else None
    except ValueError as exc:
        raise MalformedResponseError(
            "FEED_ITEM_INVALID",
            "feed XML Base is invalid",
            budget.receipt(connector, 0),
        ) from exc
    leads: list[Lead] = []
    for entry in entries:
        title = _child_text(entry, frozenset({"title"}))
        try:
            raw_link = _entry_link(entry, bases=bases)
        except ValueError as exc:
            raise MalformedResponseError(
                "FEED_ITEM_INVALID",
                "feed link is invalid",
                budget.receipt(connector, 0),
            ) from exc
        stable_id = _child_text(entry, frozenset({"id", "guid"}))
        if not title or not raw_link:
            raise MalformedResponseError(
                "FEED_ITEM_INVALID",
                "feed item is missing a title or link",
                budget.receipt(connector, 0),
            )
        try:
            parsed_link = urlsplit(raw_link)
            if (
                parsed_link.scheme == "http"
                and parsed_link.hostname in upgrade_http_hosts
                and parsed_link.port in (None, 80)
                and parsed_link.username is None
                and parsed_link.password is None
            ):
                raw_link = urlunsplit(
                    (
                        "https",
                        parsed_link.hostname,
                        parsed_link.path,
                        parsed_link.query,
                        parsed_link.fragment,
                    )
                )
            canonical_link = _canonical_url(raw_link, base_url=response.url)
        except (UnicodeError, ValueError) as exc:
            raise MalformedResponseError(
                "FEED_ITEM_INVALID",
                "feed item link is not a credential-free HTTPS URL",
                budget.receipt(connector, 0),
            ) from exc
        if connector == "arxiv":
            article_url = urlsplit(canonical_link)
            if article_url.hostname not in {
                "arxiv.org",
                "export.arxiv.org",
            } or not article_url.path.startswith("/abs/"):
                # arXiv represents API errors as Atom entries, sometimes HTTP
                # 200. Its /api/errors entry must never become a paper lead.
                raise MalformedResponseError(
                    "ARXIV_SCHEMA_INVALID",
                    "arXiv entry is not an article",
                    budget.receipt(connector, 0),
                )
        lead_identity = _identity(connector, stable_id or canonical_link)
        if watermark is not None and lead_identity == watermark:
            break
        published = _child_text(
            entry, frozenset({"published", "updated", "pubdate", "date"})
        )
        summary = _child_text(entry, frozenset({"summary", "description", "content"}))
        authors = [
            _child_text(child, frozenset({"name"})) or ""
            for child in entry
            if _local_name(child.tag) in {"author", "creator"}
        ]
        metadata = tuple(("author", author) for author in authors if author)[:20]
        if include_provenance:
            published = next(
                (
                    value
                    for field in ("published", "pubdate", "date", "updated")
                    if (value := _child_text(entry, frozenset({field})))
                ),
                None,
            )
            summary, summary_kind = _feed_summary(entry)
            if connector == "arxiv" and summary_kind != "none":
                summary_kind = "arxiv_abstract"
            extra = [
                ("article_url", canonical_link),
                ("summary_kind", summary_kind),
                ("summary_truncated", str(len(summary) > 16_384).lower()),
            ]
            if published:
                extra.append(("published", published))
            updated = _child_text(entry, frozenset({"updated"}))
            if updated:
                extra.append(("updated", updated))
            try:
                if connector == "arxiv":
                    assert bases is not None
                    extra.extend(_arxiv_article_metadata(entry, canonical_link, bases))
                metadata = _bounded_metadata((*metadata, *extra))
            except (UnicodeError, ValueError) as exc:
                raise MalformedResponseError(
                    "FEED_PROVENANCE_INVALID",
                    "feed provenance is invalid or exceeds its bounds",
                    budget.receipt(connector, 0),
                ) from exc
        lead = Lead(
            identity=lead_identity,
            source=connector,
            title=_bounded_text(title, 8_192),
            url=canonical_link,
            published_at=_bounded_text(published, 128) or None,
            summary=_bounded_text(summary, 16_384),
            metadata=metadata,
        )
        if terms and not all(
            term
            in f"{lead.title}\n{summary if include_provenance else lead.summary}".casefold()
            for term in terms
        ):
            continue
        leads.append(lead)
        if limit is not None and len(leads) >= limit:
            break
    return tuple(leads)


@dataclass(frozen=True, slots=True)
class _FeedCursor:
    """A query-bound identity window, never an evidence or authority receipt."""

    scope: str
    watermark: str | None = None
    head: str | None = None
    after: str | None = None
    snapshot: str | None = None

    def encode(self) -> str:
        payload = {
            "version": 1,
            "scope": self.scope,
            "watermark": self.watermark,
            "head": self.head,
            "after": self.after,
            "snapshot": self.snapshot,
        }
        encoded = base64.urlsafe_b64encode(
            json.dumps(payload, separators=(",", ":")).encode("utf-8")
        ).decode("ascii")
        return "feed-v1:" + encoded


def _feed_cursor(connector: str, feed_url: str, query: QuerySpec) -> _FeedCursor:
    # Store only a digest of the private query/config, never the literal query.
    scope = hashlib.sha256(
        json.dumps([connector, feed_url, query.text], separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()
    if query.cursor is None:
        return _FeedCursor(scope)
    try:
        if not query.cursor.startswith("feed-v1:"):
            raise ValueError("unsupported cursor version")
        payload = json.loads(
            base64.b64decode(query.cursor[8:], altchars=b"-_", validate=True),
            object_pairs_hook=_strict_object_pairs,
        )
        if not isinstance(payload, dict) or set(payload) != {
            "version",
            "scope",
            "watermark",
            "head",
            "after",
            "snapshot",
        }:
            raise ValueError("invalid cursor fields")
        if type(payload["version"]) is not int or payload["version"] != 1:
            raise ValueError("invalid cursor version")
        if not isinstance(payload["scope"], str) or not re.fullmatch(
            r"[0-9a-f]{64}", payload["scope"]
        ):
            raise ValueError("invalid scope digest")
        for name in ("watermark", "head", "after"):
            value = payload[name]
            if value is not None and (
                not isinstance(value, str)
                or not re.fullmatch(
                    re.escape(connector) + r":sha256:[0-9a-f]{64}", value
                )
            ):
                raise ValueError("invalid cursor identity")
        snapshot = payload["snapshot"]
        if snapshot is not None and (
            not isinstance(snapshot, str) or not re.fullmatch(r"[0-9a-f]{64}", snapshot)
        ):
            raise ValueError("invalid window digest")
        pending_fields = [
            payload[name] is not None for name in ("head", "after", "snapshot")
        ]
        if any(pending_fields) and not all(pending_fields):
            raise ValueError("incomplete window")
    except (ValueError, TypeError, UnicodeError, binascii.Error, RecursionError) as exc:
        raise ConnectorError(
            "CURSOR_INVALID", "feed cursor is malformed or unsupported"
        ) from exc
    if payload["scope"] != scope:
        raise ConnectorError(
            "CURSOR_SCOPE_MISMATCH",
            "feed cursor belongs to a different source or query",
        )
    return _FeedCursor(
        scope, payload["watermark"], payload["head"], payload["after"], snapshot
    )


def _feed_window_digest(items: Sequence[Lead]) -> str:
    return hashlib.sha256(
        json.dumps([item.identity for item in items], separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def _feed_page(
    *,
    connector: str,
    response: _FetchedResponse,
    budget: _Budget,
    query: QuerySpec,
    cursor: _FeedCursor,
    limit: int,
    include_provenance: bool = False,
) -> LeadPage:
    # The exact response-body limit bounds this in-memory scan. No additional
    # network pages or durable state are created. Checking the full identity
    # window lets prepended items wait safely while a capped window is drained.
    observed = _feed_leads(
        connector=connector,
        response=response,
        budget=budget,
        limit=None,
        watermark=None,
        terms=tuple(query.text.casefold().split()),
        include_provenance=include_provenance,
    )
    identities = [item.identity for item in observed]
    if len(set(identities)) != len(identities):
        raise MalformedResponseError(
            "FEED_IDENTITY_DUPLICATE",
            "feed contains ambiguous duplicate identities",
            budget.receipt(connector, 0),
        )
    try:
        end = (
            identities.index(cursor.watermark)
            if cursor.watermark is not None
            else len(observed)
        )
        window = observed[:end]
        if cursor.head is not None:
            start = [item.identity for item in window].index(cursor.head)
            window = window[start:]
            if _feed_window_digest(window) != cursor.snapshot:
                raise ValueError("identity window changed")
            after = [item.identity for item in window].index(cursor.after)
            candidates = window[after + 1 :]
        else:
            candidates = window
    except ValueError as exc:
        raise ConnectorError(
            "CURSOR_STALE",
            "feed changed or lost a resume anchor; restart discovery explicitly",
            budget.receipt(connector, 0),
        ) from exc

    head = cursor.head or (candidates[0].identity if candidates else None)
    items = tuple(candidates[:limit])
    if len(candidates) > limit:
        next_cursor = _FeedCursor(
            cursor.scope,
            cursor.watermark,
            head,
            items[-1].identity,
            cursor.snapshot or _feed_window_digest(window),
        )
    else:
        next_cursor = _FeedCursor(cursor.scope, head or cursor.watermark)
    return LeadPage(items, next_cursor.encode(), budget.receipt(connector, len(items)))


class _NetworkAdapter:
    connector = "source"

    def __init__(
        self,
        *,
        transport: Transport | None,
        resolver: Resolver,
        clock: Clock,
        now: WallClock,
        capture_sink: ResponseCaptureSink | None = None,
    ):
        self._clock = clock
        self._now = now
        self._client = _SafeHTTPClient(
            transport=transport,
            resolver=resolver,
            clock=clock,
            now=now,
            capture_sink=capture_sink,
        )

    def _budget(self, limits: Limits) -> _Budget:
        return _Budget.start(limits, self._clock, self._now)


class ManualSeedAdapter:
    """In-memory/manual observations; this adapter never reads or writes a file."""

    connector = "manual"

    def __init__(
        self,
        seeds: Iterable[Lead],
        *,
        clock: Clock = time.monotonic,
        now: WallClock = _default_now,
    ):
        self._seeds = tuple(seeds)
        self._clock = clock
        self._now = now

    def discover(self, query: QuerySpec, limits: Limits) -> LeadPage:
        budget = _Budget.start(limits, self._clock, self._now)
        if not limits.permits_observation:
            return _empty_page(self.connector, query, budget)
        try:
            offset = int(query.cursor or "0")
        except ValueError as exc:
            raise ConnectorError(
                "CURSOR_INVALID", "manual cursor must be a non-negative integer"
            ) from exc
        if offset < 0:
            raise ConnectorError(
                "CURSOR_INVALID", "manual cursor must be a non-negative integer"
            )
        terms = query.text.casefold().split()
        candidates = [
            lead
            for lead in self._seeds
            if not terms
            or all(term in f"{lead.title}\n{lead.summary}".casefold() for term in terms)
        ]
        items = tuple(candidates[offset : offset + limits.max_items])
        consumed = offset + len(items)
        next_cursor = str(consumed) if consumed < len(candidates) else None
        return LeadPage(items, next_cursor, budget.receipt(self.connector, len(items)))


class RSSAtomAdapter(_NetworkAdapter):
    """Configured feed with query-bound paging; changed resume windows fail closed."""

    connector = "rss_atom"

    def __init__(
        self,
        feed_url: str,
        *,
        allowed_hosts: Iterable[str],
        include_provenance: bool = False,
        transport: Transport | None = None,
        resolver: Resolver = _system_resolver,
        clock: Clock = time.monotonic,
        now: WallClock = _default_now,
        capture_sink: ResponseCaptureSink | None = None,
    ):
        if type(include_provenance) is not bool:
            raise ValueError("include_provenance must be boolean")
        self._include_provenance = include_provenance
        super().__init__(
            transport=transport,
            resolver=resolver,
            clock=clock,
            now=now,
            capture_sink=capture_sink,
        )
        self._allowed_hosts = _normalize_allowed_hosts(allowed_hosts)
        _validate_outbound_url(feed_url, self._allowed_hosts)
        self._feed_url = feed_url

    def discover(self, query: QuerySpec, limits: Limits) -> DiscoveryResult:
        budget = self._budget(limits)
        if not limits.permits_observation:
            return _empty_page(self.connector, query, budget)
        cursor = _feed_cursor(
            self.connector,
            self._feed_url + ("#provenance-v1" if self._include_provenance else ""),
            query,
        )
        response = self._client.get(
            connector=self.connector,
            url=self._feed_url,
            allowed_hosts=self._allowed_hosts,
            headers=(
                ("Accept", ", ".join(sorted(XML_MEDIA_TYPES))),
                ("Accept-Encoding", "identity"),
                ("User-Agent", USER_AGENT),
            ),
            budget=budget,
        )
        if isinstance(response, _RateLimited):
            return _rate_limit_result(self.connector, response, budget)
        return _feed_page(
            connector=self.connector,
            response=response,
            budget=budget,
            query=query,
            cursor=cursor,
            limit=limits.max_items,
            include_provenance=self._include_provenance,
        )


def _arxiv_cursor_scope(query: QuerySpec, scope: str, match: str, sort: str) -> str:
    return hashlib.sha256(
        json.dumps(
            ["arxiv-provenance-v1", query.text, scope, match, sort],
            separators=(",", ":"),
        ).encode()
    ).hexdigest()


def _arxiv_cursor_checksum(data: Mapping[str, object]) -> str:
    # Corruption detection, not authentication. Local cursors grant no authority.
    return hashlib.sha256(
        json.dumps(
            {key: data[key] for key in ("version", "scope", "offset")},
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()


def _arxiv_offset(cursor: str | None, scope: str) -> int:
    if cursor is None:
        return 0
    try:
        if not cursor.startswith("arxiv-v1:"):
            raise ValueError("unsupported cursor")
        data = json.loads(
            base64.b64decode(cursor[9:], altchars=b"-_", validate=True),
            object_pairs_hook=_strict_object_pairs,
        )
        if (
            not isinstance(data, dict)
            or set(data) != {"version", "scope", "offset", "checksum"}
            or type(data["version"]) is not int
            or data["version"] != 1
            or not isinstance(data["scope"], str)
            or not re.fullmatch(r"[0-9a-f]{64}", data["scope"])
            or type(data["offset"]) is not int
            or not 0 <= data["offset"] <= _ARXIV_MAX_OFFSET
            or not isinstance(data["checksum"], str)
            or data["checksum"] != _arxiv_cursor_checksum(data)
        ):
            raise ValueError("invalid cursor fields")
    except (ValueError, TypeError, UnicodeError, RecursionError) as exc:
        raise ConnectorError(
            "CURSOR_INVALID", "arXiv cursor is malformed or out of bounds"
        ) from exc
    if data["scope"] != scope:
        raise ConnectorError(
            "CURSOR_SCOPE_MISMATCH",
            "arXiv cursor belongs to a different query or configuration",
        )
    return data["offset"]


def _arxiv_next_cursor(offset: int, scope: str) -> str:
    if offset > _ARXIV_MAX_OFFSET:
        raise ConnectorError("CURSOR_LIMIT", "arXiv local offset ceiling reached")
    data = {"version": 1, "scope": scope, "offset": offset}
    data["checksum"] = _arxiv_cursor_checksum(data)
    return "arxiv-v1:" + base64.urlsafe_b64encode(
        json.dumps(data, separators=(",", ":")).encode()
    ).decode("ascii")


class ArxivAtomAdapter(_NetworkAdapter):
    """arXiv discovery, with optional provenance and query-bound offset paging.

    Offset paging is over a mutable provider result set, not a snapshot. The
    versioned provenance cursor prevents accidental cross-query/config reuse;
    it is not a signed acceptance record and grants no authority.
    """

    connector = "arxiv"
    _URL = "https://export.arxiv.org/api/query"
    _HOSTS = frozenset({"export.arxiv.org"})

    def __init__(
        self,
        *,
        search_scope: Literal["all", "title_abstract"] = "all",
        search_match: Literal["terms", "phrase"] = "terms",
        sort_by: Literal[
            "relevance", "submittedDate", "lastUpdatedDate"
        ] = "submittedDate",
        include_provenance: bool = False,
        transport: Transport | None = None,
        resolver: Resolver = _system_resolver,
        clock: Clock = time.monotonic,
        now: WallClock = _default_now,
        capture_sink: ResponseCaptureSink | None = None,
    ):
        if not isinstance(search_scope, str) or search_scope not in {
            "all",
            "title_abstract",
        }:
            raise ValueError("arXiv search_scope must be all or title_abstract")
        if not isinstance(search_match, str) or search_match not in {"terms", "phrase"}:
            raise ValueError("arXiv search_match must be terms or phrase")
        if not isinstance(sort_by, str) or sort_by not in {
            "relevance",
            "submittedDate",
            "lastUpdatedDate",
        }:
            raise ValueError(
                "arXiv sort_by must be relevance, submittedDate, or lastUpdatedDate"
            )
        if type(include_provenance) is not bool:
            raise ValueError("include_provenance must be boolean")
        self._search_scope = search_scope
        self._search_match = search_match
        self._sort_by = sort_by
        self._include_provenance = include_provenance
        super().__init__(
            transport=transport,
            resolver=resolver,
            clock=clock,
            now=now,
            capture_sink=capture_sink,
        )

    def discover(self, query: QuerySpec, limits: Limits) -> DiscoveryResult:
        budget = self._budget(limits)
        if not limits.permits_observation:
            return _empty_page(self.connector, query, budget)
        if not query.text.strip():
            raise ConnectorError(
                "QUERY_REQUIRED", "arXiv discovery requires non-empty query text"
            )
        cursor_scope = _arxiv_cursor_scope(
            query, self._search_scope, self._search_match, self._sort_by
        )
        if self._include_provenance:
            offset = _arxiv_offset(query.cursor, cursor_scope)
            if offset + limits.max_items > _ARXIV_MAX_OFFSET:
                raise ConnectorError(
                    "CURSOR_LIMIT", "arXiv page would exceed the local offset ceiling"
                )
        else:
            try:
                offset = int(query.cursor or "0")
            except ValueError as exc:
                raise ConnectorError(
                    "CURSOR_INVALID", "arXiv cursor must be a non-negative integer"
                ) from exc
            if offset < 0:
                raise ConnectorError(
                    "CURSOR_INVALID", "arXiv cursor must be a non-negative integer"
                )
        terms = (
            [query.text.strip()]
            if self._search_match == "phrase"
            else query.text.split()
        )
        expressions = []
        for term in terms:
            literal = json.dumps(term, ensure_ascii=False)
            expressions.append(
                f"(ti:{literal} OR abs:{literal})"
                if self._search_scope == "title_abstract"
                else f"all:{literal}"
            )
        request_url = (
            self._URL
            + "?"
            + urlencode(
                {
                    "search_query": " AND ".join(expressions),
                    "start": offset,
                    "max_results": limits.max_items,
                    "sortBy": self._sort_by,
                    "sortOrder": "descending",
                }
            )
        )
        response = self._client.get(
            connector=self.connector,
            url=request_url,
            allowed_hosts=self._HOSTS,
            headers=(
                ("Accept", "application/atom+xml"),
                ("Accept-Encoding", "identity"),
                ("User-Agent", USER_AGENT),
            ),
            budget=budget,
        )
        if isinstance(response, _RateLimited):
            return _rate_limit_result(self.connector, response, budget)
        items = _feed_leads(
            connector=self.connector,
            response=response,
            budget=budget,
            limit=limits.max_items,
            watermark=None,
            upgrade_http_hosts=frozenset({"arxiv.org", "export.arxiv.org"}),
            include_provenance=self._include_provenance,
        )
        next_cursor = (
            str(offset + len(items)) if len(items) == limits.max_items else None
        )
        if next_cursor is not None and self._include_provenance:
            next_cursor = _arxiv_next_cursor(offset + len(items), cursor_scope)
        return LeadPage(items, next_cursor, budget.receipt(self.connector, len(items)))


class GitHubAtomAdapter(_NetworkAdapter):
    connector = "github_atom"
    _HOSTS = frozenset({"github.com"})

    def __init__(
        self,
        repository: str,
        *,
        resource: Literal["commits", "releases"] = "releases",
        transport: Transport | None = None,
        resolver: Resolver = _system_resolver,
        clock: Clock = time.monotonic,
        now: WallClock = _default_now,
        capture_sink: ResponseCaptureSink | None = None,
    ):
        if not REPOSITORY_RE.fullmatch(repository):
            raise ValueError("repository must have the form owner/name")
        if resource not in {"commits", "releases"}:
            raise ValueError("GitHub Atom resource must be commits or releases")
        super().__init__(
            transport=transport,
            resolver=resolver,
            clock=clock,
            now=now,
            capture_sink=capture_sink,
        )
        owner, name = repository.split("/", 1)
        self._url = f"https://github.com/{quote(owner)}/{quote(name)}/{resource}.atom"

    def discover(self, query: QuerySpec, limits: Limits) -> DiscoveryResult:
        budget = self._budget(limits)
        if not limits.permits_observation:
            return _empty_page(self.connector, query, budget)
        cursor = _feed_cursor(self.connector, self._url, query)
        response = self._client.get(
            connector=self.connector,
            url=self._url,
            allowed_hosts=self._HOSTS,
            headers=(
                ("Accept", "application/atom+xml"),
                ("Accept-Encoding", "identity"),
                ("User-Agent", USER_AGENT),
            ),
            budget=budget,
        )
        if isinstance(response, _RateLimited):
            return _rate_limit_result(self.connector, response, budget)
        return _feed_page(
            connector=self.connector,
            response=response,
            budget=budget,
            query=query,
            cursor=cursor,
            limit=limits.max_items,
        )


class GitHubAPIAdapter(_NetworkAdapter):
    connector = "github_api"
    _HOSTS = frozenset({"api.github.com"})

    def __init__(
        self,
        repository: str,
        *,
        resource: Literal["commits", "releases"] = "releases",
        token: str | None = None,
        transport: Transport | None = None,
        resolver: Resolver = _system_resolver,
        clock: Clock = time.monotonic,
        now: WallClock = _default_now,
        capture_sink: ResponseCaptureSink | None = None,
    ):
        if not REPOSITORY_RE.fullmatch(repository):
            raise ValueError("repository must have the form owner/name")
        if resource not in {"commits", "releases"}:
            raise ValueError("GitHub API resource must be commits or releases")
        if token is not None and (not token or "\r" in token or "\n" in token):
            raise ValueError("GitHub token is invalid")
        super().__init__(
            transport=transport,
            resolver=resolver,
            clock=clock,
            now=now,
            capture_sink=capture_sink,
        )
        self._repository = repository
        self._resource = resource
        self._token = token

    def discover(self, query: QuerySpec, limits: Limits) -> DiscoveryResult:
        budget = self._budget(limits)
        if not limits.permits_observation:
            return _empty_page(self.connector, query, budget)
        try:
            page = int(query.cursor or "1")
        except ValueError as exc:
            raise ConnectorError(
                "CURSOR_INVALID", "GitHub cursor must be a positive integer"
            ) from exc
        if page < 1:
            raise ConnectorError(
                "CURSOR_INVALID", "GitHub cursor must be a positive integer"
            )
        request_url = (
            f"https://api.github.com/repos/{self._repository}/{self._resource}?"
            + urlencode({"per_page": min(limits.max_items, 100), "page": page})
        )
        headers: list[tuple[str, str]] = [
            ("Accept", "application/vnd.github+json"),
            ("Accept-Encoding", "identity"),
            ("User-Agent", USER_AGENT),
            ("X-GitHub-Api-Version", "2022-11-28"),
        ]
        if self._token:
            headers.append(("Authorization", f"Bearer {self._token}"))
        response = self._client.get(
            connector=self.connector,
            url=request_url,
            allowed_hosts=self._HOSTS,
            headers=tuple(headers),
            budget=budget,
        )
        if isinstance(response, _RateLimited):
            return _rate_limit_result(self.connector, response, budget)
        payload = _parse_json(self.connector, response, budget)
        if not isinstance(payload, list):
            raise MalformedResponseError(
                "GITHUB_SCHEMA_INVALID",
                "GitHub API response must be an array",
                budget.receipt(self.connector, 0),
            )
        leads: list[Lead] = []
        for item in payload:
            if not isinstance(item, dict):
                raise MalformedResponseError(
                    "GITHUB_SCHEMA_INVALID",
                    "GitHub API item must be an object",
                    budget.receipt(self.connector, 0),
                )
            lead = (
                self._release_lead(item, response.url, budget)
                if self._resource == "releases"
                else self._commit_lead(item, response.url, budget)
            )
            leads.append(lead)
            if len(leads) >= limits.max_items:
                break
        items = tuple(leads)
        next_cursor = (
            str(page + 1) if len(items) == min(limits.max_items, 100) else None
        )
        return LeadPage(items, next_cursor, budget.receipt(self.connector, len(items)))

    def _release_lead(
        self, item: Mapping[str, object], base_url: str, budget: _Budget
    ) -> Lead:
        stable = item.get("node_id") or item.get("id")
        title = item.get("name") or item.get("tag_name")
        url = item.get("html_url")
        if (
            not isinstance(stable, (str, int))
            or isinstance(stable, bool)
            or not isinstance(title, str)
            or not isinstance(url, str)
        ):
            raise MalformedResponseError(
                "GITHUB_SCHEMA_INVALID",
                "GitHub release lacks stable identity, title, or URL",
                budget.receipt(self.connector, 0),
            )
        try:
            canonical = _canonical_url(url, base_url=base_url)
        except (UnicodeError, ValueError) as exc:
            raise MalformedResponseError(
                "GITHUB_SCHEMA_INVALID",
                "GitHub release URL is invalid",
                budget.receipt(self.connector, 0),
            ) from exc
        published = item.get("published_at")
        body = item.get("body")
        return Lead(
            identity=_identity(self.connector, str(stable)),
            source=self.connector,
            title=_bounded_text(title, 8_192),
            url=canonical,
            published_at=_bounded_text(
                published if isinstance(published, str) else None, 128
            )
            or None,
            summary=_bounded_text(body if isinstance(body, str) else None, 16_384),
        )

    def _commit_lead(
        self, item: Mapping[str, object], base_url: str, budget: _Budget
    ) -> Lead:
        stable = item.get("sha")
        url = item.get("html_url")
        commit = item.get("commit")
        if (
            not isinstance(stable, str)
            or not isinstance(url, str)
            or not isinstance(commit, dict)
        ):
            raise MalformedResponseError(
                "GITHUB_SCHEMA_INVALID",
                "GitHub commit lacks SHA, URL, or commit object",
                budget.receipt(self.connector, 0),
            )
        message = commit.get("message")
        author = commit.get("author")
        if not isinstance(message, str) or not isinstance(author, dict):
            raise MalformedResponseError(
                "GITHUB_SCHEMA_INVALID",
                "GitHub commit lacks message or author object",
                budget.receipt(self.connector, 0),
            )
        try:
            canonical = _canonical_url(url, base_url=base_url)
        except (UnicodeError, ValueError) as exc:
            raise MalformedResponseError(
                "GITHUB_SCHEMA_INVALID",
                "GitHub commit URL is invalid",
                budget.receipt(self.connector, 0),
            ) from exc
        author_name = author.get("name")
        published = author.get("date")
        first_line = message.splitlines()[0].strip() if message else ""
        if not first_line:
            raise MalformedResponseError(
                "GITHUB_SCHEMA_INVALID",
                "GitHub commit message is empty",
                budget.receipt(self.connector, 0),
            )
        metadata = (
            (("author", author_name),)
            if isinstance(author_name, str) and author_name
            else ()
        )
        return Lead(
            identity=_identity(self.connector, stable),
            source=self.connector,
            title=_bounded_text(first_line, 8_192),
            url=canonical,
            published_at=_bounded_text(
                published if isinstance(published, str) else None, 128
            )
            or None,
            summary=_bounded_text(message, 16_384),
            metadata=metadata,
        )


class HackerNewsAPIAdapter(_NetworkAdapter):
    connector = "hacker_news"
    _HOSTS = frozenset({"hacker-news.firebaseio.com"})

    def __init__(
        self,
        *,
        feed: Literal["topstories", "newstories", "beststories"] = "topstories",
        transport: Transport | None = None,
        resolver: Resolver = _system_resolver,
        clock: Clock = time.monotonic,
        now: WallClock = _default_now,
        capture_sink: ResponseCaptureSink | None = None,
    ):
        if feed not in {"topstories", "newstories", "beststories"}:
            raise ValueError("unsupported Hacker News feed")
        super().__init__(
            transport=transport,
            resolver=resolver,
            clock=clock,
            now=now,
            capture_sink=capture_sink,
        )
        self._feed = feed

    def discover(self, query: QuerySpec, limits: Limits) -> DiscoveryResult:
        budget = self._budget(limits)
        if not limits.permits_observation:
            return _empty_page(self.connector, query, budget)
        try:
            offset = int(query.cursor or "0")
        except ValueError as exc:
            raise ConnectorError(
                "CURSOR_INVALID", "Hacker News cursor must be non-negative"
            ) from exc
        if offset < 0:
            raise ConnectorError(
                "CURSOR_INVALID", "Hacker News cursor must be non-negative"
            )
        list_response = self._client.get(
            connector=self.connector,
            url=f"https://hacker-news.firebaseio.com/v0/{self._feed}.json",
            allowed_hosts=self._HOSTS,
            headers=(
                ("Accept", "application/json"),
                ("Accept-Encoding", "identity"),
                ("User-Agent", USER_AGENT),
            ),
            budget=budget,
        )
        if isinstance(list_response, _RateLimited):
            return _rate_limit_result(self.connector, list_response, budget)
        payload = _parse_json(self.connector, list_response, budget)
        if not isinstance(payload, list) or any(
            isinstance(item, bool) or not isinstance(item, int) or item <= 0
            for item in payload
        ):
            raise MalformedResponseError(
                "HN_SCHEMA_INVALID",
                "Hacker News feed response must be an array of positive integer IDs",
                budget.receipt(self.connector, 0),
            )

        leads: list[Lead] = []
        index = offset
        terms = query.text.casefold().split()
        while index < len(payload) and len(leads) < limits.max_items:
            if budget.request_count >= limits.max_requests:
                break
            item_id = payload[index]
            item_response = self._client.get(
                connector=self.connector,
                url=f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json",
                allowed_hosts=self._HOSTS,
                headers=(
                    ("Accept", "application/json"),
                    ("Accept-Encoding", "identity"),
                    ("User-Agent", USER_AGENT),
                ),
                budget=budget,
            )
            if isinstance(item_response, _RateLimited):
                return _rate_limit_result(self.connector, item_response, budget)
            item = _parse_json(self.connector, item_response, budget)
            index += 1
            if item is None:
                continue
            if not isinstance(item, dict):
                raise MalformedResponseError(
                    "HN_SCHEMA_INVALID",
                    "Hacker News item response must be an object or null",
                    budget.receipt(self.connector, 0),
                )
            if item.get("deleted") is True or item.get("dead") is True:
                continue
            lead = self._item_lead(item, item_id, item_response.url, budget)
            if terms and not all(
                term in f"{lead.title}\n{lead.summary}".casefold() for term in terms
            ):
                continue
            leads.append(lead)
        next_cursor = str(index) if index < len(payload) else None
        items = tuple(leads)
        return LeadPage(items, next_cursor, budget.receipt(self.connector, len(items)))

    def _item_lead(
        self,
        item: Mapping[str, object],
        requested_id: int,
        base_url: str,
        budget: _Budget,
    ) -> Lead:
        item_id = item.get("id")
        title = item.get("title")
        if item_id != requested_id or not isinstance(title, str) or not title.strip():
            raise MalformedResponseError(
                "HN_SCHEMA_INVALID",
                "Hacker News item lacks the requested ID or title",
                budget.receipt(self.connector, 0),
            )
        raw_url = item.get("url")
        if raw_url is None:
            public_url = f"https://news.ycombinator.com/item?id={item_id}"
        elif isinstance(raw_url, str):
            try:
                if urlsplit(raw_url).scheme == "http":
                    # HN accepts HTTP-only submissions. Retain the stable HTTPS
                    # discussion link without assuming that site supports TLS.
                    public_url = f"https://news.ycombinator.com/item?id={item_id}"
                else:
                    public_url = _canonical_url(raw_url, base_url=base_url)
            except (UnicodeError, ValueError) as exc:
                raise MalformedResponseError(
                    "HN_SCHEMA_INVALID",
                    "Hacker News item URL is invalid",
                    budget.receipt(self.connector, 0),
                ) from exc
        else:
            raise MalformedResponseError(
                "HN_SCHEMA_INVALID",
                "Hacker News item URL must be a string or null",
                budget.receipt(self.connector, 0),
            )
        published = item.get("time")
        by = item.get("by")
        summary = item.get("text")
        metadata = (("author", by),) if isinstance(by, str) and by else ()
        return Lead(
            identity=f"hacker_news:item:{item_id}",
            source=self.connector,
            title=_bounded_text(title, 8_192),
            url=public_url,
            published_at=str(published)
            if isinstance(published, int) and not isinstance(published, bool)
            else None,
            summary=_bounded_text(
                summary if isinstance(summary, str) else None, 16_384
            ),
            metadata=metadata,
        )


def _x_link_records(entities: object) -> tuple[str, ...]:
    if not isinstance(entities, dict):
        raise ValueError("X entities must be an object")
    urls = entities.get("urls", [])
    if not isinstance(urls, list) or len(urls) > 20:
        raise ValueError("X URL entities exceed their bounds")
    records = []
    for entity in urls:
        if not isinstance(entity, dict):
            raise ValueError("X URL entity must be an object")
        record = {}
        for name in ("url", "expanded_url", "unwound_url"):
            value = entity.get(name)
            if value is None:
                continue
            if not isinstance(value, str) or not 1 <= len(value) <= 8_192:
                raise ValueError("X URL entity value is invalid")
            parsed = urlsplit(value)
            if (
                parsed.scheme not in {"https", "http"}
                or not parsed.hostname
                or parsed.username
                or parsed.password
                or parsed.port not in (None, 80, 443)
                or any(ord(character) < 32 for character in value)
            ):
                raise ValueError("X URL entity is not a credential-free web URL")
            record[name] = value
        if not record:
            raise ValueError("X URL entity has no URL")
        records.append(json.dumps(record, sort_keys=True, separators=(",", ":")))
    return tuple(dict.fromkeys(records))


def _x_reference_records(value: object) -> tuple[str, ...]:
    if not isinstance(value, list) or len(value) > 20:
        raise ValueError("X references exceed their bounds")
    records = []
    for item in value:
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("id"), str)
            or not re.fullmatch(r"[0-9]{1,32}", item["id"])
            or not isinstance(item.get("type"), str)
            or item["type"] not in {"retweeted", "reposted", "quoted", "replied_to"}
        ):
            raise ValueError("X reference is invalid")
        records.append(
            json.dumps(
                {"id": item["id"], "type": item["type"]},
                sort_keys=True,
                separators=(",", ":"),
            )
        )
    return tuple(sorted(set(records)))


def _x_content_metadata(
    item: dict[str, object], text: str, *, include_context: bool = False
) -> tuple[str, tuple[tuple[str, str], ...]]:
    notes: list[tuple[str, str, tuple[str, ...]]] = []
    for name in ("note_tweet", "note_post"):
        if name not in item:
            continue
        note = item[name]
        if (
            not isinstance(note, dict)
            or not isinstance(note.get("text"), str)
            or not note["text"].strip()
        ):
            raise ValueError("X long-form note is invalid")
        links = _x_link_records(note["entities"]) if "entities" in note else ()
        notes.append((name, note["text"], links))
    if len(notes) == 2 and (
        notes[0][1] != notes[1][1] or set(notes[0][2]) != set(notes[1][2])
    ):
        raise ValueError("X long-form aliases conflict")
    kind = "x_post_text"
    links = _x_link_records(item["entities"]) if "entities" in item else ()
    if notes:
        name, text, note_links = notes[0]
        kind = "x_" + name if len(notes) == 1 else "x_long_form_note"
        links = tuple(dict.fromkeys((*links, *note_links)))
    references = []
    for name in ("referenced_tweets", "referenced_posts"):
        if name in item:
            references.append(_x_reference_records(item[name]))
    if len(references) == 2 and references[0] != references[1]:
        raise ValueError("X reference aliases conflict")
    normalized = " ".join(text.split())
    normalized.encode("utf-8")
    metadata = [
        ("summary_kind", kind),
        ("summary_truncated", str(len(normalized) > 16_384).lower()),
        # Official docs disagree on tweet/post names. Enrichment uses only the
        # legacy tweet-field dialect; there is no live proof or fallback retry.
        (
            "request_contract",
            "x-v2-tweets-recent:tweet.fields=" + _X_ENRICHED_LEGACY_FIELDS
            + (",public_metrics,conversation_id" if include_context else ""),
        ),
        ("enrichment_wire_status", "not_live_validated"),
    ]
    # URL records preserve source relationships, including HTTP observations.
    # They never authorize following a link. Outbound policy remains HTTPS-only.
    metadata.extend(("outbound_link", link) for link in links)
    if references:
        metadata.extend(("referenced_post", reference) for reference in references[0])
    if include_context:
        conversation = item.get("conversation_id")
        if conversation is not None:
            if not isinstance(conversation, str) or not re.fullmatch(r"[0-9]{1,32}", conversation):
                raise ValueError("X conversation ID is invalid")
            metadata.append(("conversation_id", conversation))
        metrics = item.get("public_metrics")
        if metrics is not None:
            if not isinstance(metrics, dict) or len(metrics) > 16:
                raise ValueError("X metrics are invalid")
            if any(not isinstance(key, str) or not re.fullmatch(r"[a-z_]{1,64}", key)
                   or type(value) is not int or not 0 <= value <= 2**53 - 1
                   for key, value in metrics.items()):
                raise ValueError("X metrics are invalid")
            metadata.append(("public_metrics", json.dumps(metrics, sort_keys=True, separators=(",", ":"))))
    return normalized, tuple(metadata)


class XRecentSearchAdapter(_NetworkAdapter):
    """Read-only recent-search adapter; disabled without `X_BEARER_TOKEN`."""

    connector = "x"
    _URL = "https://api.x.com/2/tweets/search/recent"
    _HOSTS = frozenset({"api.x.com"})

    def __init__(
        self,
        *,
        environ: Mapping[str, str] | None = None,
        include_provenance: bool = False,
        start_time: int | None = None,
        end_time: int | None = None,
        include_context: bool = False,
        transport: Transport | None = None,
        resolver: Resolver = _system_resolver,
        clock: Clock = time.monotonic,
        now: WallClock = _default_now,
        capture_sink: ResponseCaptureSink | None = None,
    ):
        if type(include_provenance) is not bool:
            raise ValueError("include_provenance must be boolean")
        if type(include_context) is not bool or (include_context and not include_provenance):
            raise ValueError("X context enrichment requires provenance")
        self._include_context = include_context
        self._window = None
        if start_time is not None or end_time is not None:
            if (type(start_time) is not int or type(end_time) is not int
                    or not 0 <= start_time < end_time <= 253402300799
                    or end_time - start_time > 7 * 86400):
                raise ValueError("X window must be increasing UTC seconds, at most seven days")
            self._window = (start_time, end_time)
        self._include_provenance = include_provenance
        environment = os.environ if environ is None else environ
        token = environment.get("X_BEARER_TOKEN")
        if token is not None and (not token or "\r" in token or "\n" in token):
            raise ValueError("X_BEARER_TOKEN is invalid")
        self._bearer_token = token
        super().__init__(
            transport=transport,
            resolver=resolver,
            clock=clock,
            now=now,
            capture_sink=capture_sink,
        )
        if token is not None:
            if __package__:
                from .source_search import CredentialGuardedTransport
            else:
                from source_search import CredentialGuardedTransport
            self._client._transport = CredentialGuardedTransport(self._client._transport, token)

    @property
    def enabled(self) -> bool:
        return self._bearer_token is not None

    def discover(self, query: QuerySpec, limits: Limits) -> DiscoveryResult:
        if self._bearer_token is None:
            raise ConnectorDisabledError(
                "CONNECTOR_DISABLED",
                "X discovery is disabled unless X_BEARER_TOKEN is supplied",
            )
        budget = self._budget(limits)
        if not limits.permits_observation:
            return _empty_page(self.connector, query, budget)
        if not query.text.strip():
            raise ConnectorError(
                "QUERY_REQUIRED", "X recent search requires non-empty query text"
            )
        if limits.max_items < 10:
            raise ConnectorError(
                "ITEM_LIMIT_INCOMPATIBLE",
                "X requires max_items >= 10 to avoid discarding a provider page",
                budget.receipt(self.connector, 0),
            )
        parameters = {
            "query": query.text.strip(),
            "max_results": max(10, min(limits.max_items, 100)),
            "tweet.fields": (
                _X_ENRICHED_LEGACY_FIELDS
                if self._include_provenance
                else _X_LEGACY_FIELDS
            ),
        }
        if self._include_context:
            parameters["tweet.fields"] += ",public_metrics,conversation_id"
        if self._window is not None:
            parameters.update({name: datetime.fromtimestamp(value, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
                               for name, value in zip(("start_time", "end_time"), self._window)})
        if query.cursor:
            parameters["next_token"] = query.cursor
        response = self._client.get(
            connector=self.connector,
            url=self._URL + "?" + urlencode(parameters),
            allowed_hosts=self._HOSTS,
            headers=(
                ("Accept", "application/json"),
                ("Accept-Encoding", "identity"),
                ("Authorization", f"Bearer {self._bearer_token}"),
                ("User-Agent", USER_AGENT),
            ),
            budget=budget,
        )
        if isinstance(response, _RateLimited):
            return _rate_limit_result(self.connector, response, budget)
        payload = _parse_json(self.connector, response, budget)
        if not isinstance(payload, dict):
            raise MalformedResponseError(
                "X_SCHEMA_INVALID",
                "X response must be an object",
                budget.receipt(self.connector, 0),
            )
        if payload.get("errors"):
            raise MalformedResponseError(
                "X_PARTIAL_RESPONSE",
                "X returned a partial/error-bearing response",
                budget.receipt(self.connector, 0),
            )
        raw_data = payload.get("data")
        raw_meta = payload.get("meta")
        valid_empty_result = (
            raw_data is None
            and isinstance(raw_meta, dict)
            and raw_meta.get("result_count") == 0
        )
        if not isinstance(raw_data, list) and not valid_empty_result:
            raise MalformedResponseError(
                "X_SCHEMA_INVALID",
                "X response must contain a data array or an explicit zero-result meta object",
                budget.receipt(self.connector, 0),
            )
        data = [] if raw_data is None else raw_data
        if self._window is not None or self._include_context:
            if (not isinstance(raw_meta, dict) or type(raw_meta.get("result_count")) is not int
                    or raw_meta["result_count"] != len(data) or len(data) > limits.max_items):
                raise MalformedResponseError("X_SCHEMA_INVALID", "bounded X result count is inconsistent",
                                             budget.receipt(self.connector, 0))
        leads: list[Lead] = []
        seen_ids: set[str] = set()
        for item in data:
            if not isinstance(item, dict):
                raise MalformedResponseError(
                    "X_SCHEMA_INVALID",
                    "X data item must be an object",
                    budget.receipt(self.connector, 0),
                )
            tweet_id = item.get("id")
            text = item.get("text")
            if (
                not isinstance(tweet_id, str)
                or not tweet_id.isdigit()
                or not isinstance(text, str)
                or ((self._window is not None or self._include_context)
                    and (not re.fullmatch(r"[0-9]{1,32}", tweet_id) or tweet_id in seen_ids))
            ):
                raise MalformedResponseError(
                    "X_SCHEMA_INVALID",
                    "X data item lacks a numeric ID or text",
                    budget.receipt(self.connector, 0),
                )
            seen_ids.add(tweet_id)
            if self._window is not None:
                try:
                    created = item.get("created_at")
                    if not isinstance(created, str):
                        raise ValueError("X bounded post lacks creation time")
                    timestamp = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    if timestamp.utcoffset() is None or not self._window[0] <= timestamp.timestamp() < self._window[1]:
                        raise ValueError("X post is outside requested window")
                except (ValueError, OverflowError):
                    raise MalformedResponseError("X_PROVENANCE_INVALID", "X timestamp is invalid for its window",
                                                 budget.receipt(self.connector, 0)) from None
            metadata = tuple(
                (key, value)
                for key in ("author_id", "lang")
                if isinstance((value := item.get(key)), str)
            )
            if self._include_provenance:
                try:
                    text, extra = _x_content_metadata(item, text, include_context=self._include_context)
                    metadata = _bounded_metadata((*metadata, *extra))
                except (UnicodeError, ValueError) as exc:
                    raise MalformedResponseError(
                        "X_PROVENANCE_INVALID",
                        "X content provenance is invalid, ambiguous, or exceeds its bounds",
                        budget.receipt(self.connector, 0),
                    ) from exc
            leads.append(
                Lead(
                    identity=f"x:tweet:{tweet_id}",
                    source=self.connector,
                    title=_bounded_text(text, 280),
                    url=f"https://x.com/i/web/status/{tweet_id}",
                    published_at=_bounded_text(
                        item.get("created_at")
                        if isinstance(item.get("created_at"), str)
                        else None,
                        128,
                    )
                    or None,
                    summary=_bounded_text(text, 16_384),
                    metadata=metadata,
                )
            )
            if len(leads) >= limits.max_items:
                break
        meta = raw_meta
        if meta is not None and not isinstance(meta, dict):
            raise MalformedResponseError(
                "X_SCHEMA_INVALID",
                "X meta field must be an object",
                budget.receipt(self.connector, 0),
            )
        next_token = meta.get("next_token") if isinstance(meta, dict) else None
        if next_token is not None and not isinstance(next_token, str):
            raise MalformedResponseError(
                "X_SCHEMA_INVALID",
                "X next_token must be a string",
                budget.receipt(self.connector, 0),
            )
        items = tuple(leads)
        return LeadPage(items, next_token, budget.receipt(self.connector, len(items)))


class ContactsDisabledAdapter:
    """Explicit boundary: contact enrichment is not part of public discovery."""

    connector = "contacts"

    @property
    def enabled(self) -> bool:
        return False

    def discover(self, query: QuerySpec, limits: Limits) -> DiscoveryResult:
        del query, limits
        raise ConnectorDisabledError(
            "CONTACTS_DISABLED",
            "contact enrichment requires a separately authorized private connector",
        )


def replay_discovery(
    adapter_factory: Callable[..., object],
    captures: Sequence[tuple[ResponseObservation, bytes]],
    query: QuerySpec,
    limits: Limits,
) -> DiscoveryResult:
    """Replay bounded captures through a built-in adapter without network or sinks.

    The factory must construct an adapter using the supplied ``transport`` and
    ``resolver`` keyword arguments, with no capture sink or constructor effects.
    The caller binds the original private query/config to its checkpoint and
    compares leads/cursors or rate-limit values; response queries are redacted
    and cannot establish that binding here. Receipt timing is freshly measured.

    Safe capture metadata omits redirect Location and absolute observation time.
    Redirects and HTTP-date Retry-After therefore fail explicitly rather than
    inventing missing provenance. Numeric Retry-After can be replayed exactly.
    """
    if not isinstance(captures, Sequence) or len(captures) > limits.max_requests:
        raise ConnectorError("REPLAY_CAPTURE_LIMIT", "replay exceeds the request bound")
    saved = tuple(captures)
    total_bytes = 0
    for capture in saved:
        if not isinstance(capture, tuple) or len(capture) != 2:
            raise ConnectorError("REPLAY_CAPTURE_INVALID", "replay capture is invalid")
        observation, body = capture
        if (
            not isinstance(observation, ResponseObservation)
            or not isinstance(body, bytes)
            or type(observation.response_bytes) is not int
            or observation.response_bytes != len(body)
            or observation.response_sha256
            != "sha256:" + hashlib.sha256(body).hexdigest()
            or type(observation.status_code) is not int
            or not 100 <= observation.status_code <= 599
            or type(observation.query_redacted) is not bool
            or type(observation.truncated) is not bool
            or not isinstance(observation.request_url, str)
            or len(observation.request_url) > 8192
            or not isinstance(observation.resolved_ips, tuple)
            or not 1 <= len(observation.resolved_ips) <= 32
            or not isinstance(observation.safe_headers, tuple)
            or len(observation.safe_headers) > 64
        ):
            raise ConnectorError(
                "REPLAY_CAPTURE_INVALID", "replay capture failed integrity checks"
            )
        total_bytes += len(body)
        if total_bytes > limits.max_bytes:
            raise ConnectorError(
                "REPLAY_CAPTURE_LIMIT", "replay exceeds the response-byte bound"
            )
        try:
            parsed = urlsplit(observation.request_url)
            if parsed.query or observation.request_url != _redact_request_url(
                observation.request_url
            ):
                raise ValueError("request URL is not redacted")
            _validate_outbound_url(
                observation.request_url, frozenset({parsed.hostname or ""})
            )
            addresses = _resolve_public_ips(
                lambda host, port: observation.resolved_ips, parsed.hostname or "", 443
            )
            headers = _normalize_headers(observation.safe_headers)
            if (
                addresses != observation.resolved_ips
                or observation.connected_ip != addresses[0]
                or any(name not in SAFE_RESPONSE_HEADERS for name, _ in headers)
                or any(len(value) > 4096 for _, value in headers)
                or headers != observation.safe_headers
                or _media_type(headers) != observation.media_type
            ):
                raise ValueError("observation metadata is inconsistent")
        except (ValueError, TypeError, ConnectorError):
            raise ConnectorError(
                "REPLAY_CAPTURE_INVALID", "replay capture metadata is invalid"
            ) from None
        retry_after = _first_header(headers, "retry-after")
        if observation.status_code in REDIRECT_STATUSES or (
            observation.status_code == 429
            and retry_after is not None
            and not retry_after.strip().isdigit()
        ):
            raise ConnectorError(
                "REPLAY_UNSUPPORTED_RESPONSE",
                "response needs uncaptured redirect or wall-clock metadata",
            )

    position = 0

    def current() -> tuple[ResponseObservation, bytes]:
        if position >= len(saved):
            raise ConnectorError(
                "REPLAY_MISSING_CAPTURE", "adapter requested an uncaptured response"
            )
        return saved[position]

    def resolver(hostname: str, port: int) -> tuple[str, ...]:
        observation, _ = current()
        if hostname != urlsplit(observation.request_url).hostname or port != 443:
            raise ConnectorError(
                "REPLAY_REQUEST_MISMATCH",
                "replay request does not match the next capture",
            )
        return observation.resolved_ips

    class ReplayTransport:
        def request(self, request: TransportRequest) -> TransportResponse:
            nonlocal position
            observation, body = current()
            if (
                _redact_request_url(request.url) != observation.request_url
                or bool(urlsplit(request.url).query) != observation.query_redacted
                or request.connect_ip != observation.connected_ip
            ):
                raise ConnectorError(
                    "REPLAY_REQUEST_MISMATCH",
                    "replay request does not match the next capture",
                )
            position += 1
            return TransportResponse(
                observation.status_code,
                observation.safe_headers,
                body,
                truncated=observation.truncated,
            )

    transport = ReplayTransport()
    adapter = adapter_factory(transport=transport, resolver=resolver)
    if __package__:
        from .source_search import CredentialGuardedTransport, HackerNewsSearchAdapter, OpenAlexWorksAdapter
    else:
        from source_search import CredentialGuardedTransport, HackerNewsSearchAdapter, OpenAlexWorksAdapter
    actual_transport = getattr(getattr(adapter, "_client", None), "_transport", None)
    if type(actual_transport) is CredentialGuardedTransport:
        actual_transport = actual_transport.transport
    if (
        type(adapter)
        not in (
            ArxivAtomAdapter,
            RSSAtomAdapter,
            GitHubAtomAdapter,
            GitHubAPIAdapter,
            HackerNewsAPIAdapter,
            XRecentSearchAdapter,
            HackerNewsSearchAdapter,
            OpenAlexWorksAdapter,
        )
        or actual_transport is not transport
        or adapter._client._resolver is not resolver
        or adapter._client._capture_sink is not None
    ):
        raise ConnectorError(
            "REPLAY_FACTORY_INVALID",
            "replay factory did not preserve offline boundaries",
        )
    result = adapter.discover(query, limits)
    if position != len(saved):
        raise ConnectorError(
            "REPLAY_EXTRA_CAPTURE", "adapter left captured responses unused"
        )
    if not isinstance(result, (LeadPage, RetryAfter)):
        raise ConnectorError(
            "REPLAY_RESULT_INVALID", "adapter returned an invalid discovery result"
        )
    return result


__all__ = [
    "ArxivAtomAdapter",
    "ConnectorDisabledError",
    "ConnectorError",
    "ContactsDisabledAdapter",
    "DiscoveryResult",
    "GitHubAPIAdapter",
    "GitHubAtomAdapter",
    "HackerNewsAPIAdapter",
    "Lead",
    "LeadPage",
    "LimitExceededError",
    "Limits",
    "MalformedResponseError",
    "ManualSeedAdapter",
    "PinnedHTTPSTransport",
    "PolicyError",
    "QuerySpec",
    "Receipt",
    "Resolver",
    "ResponseObservation",
    "ResponseCaptureSink",
    "replay_discovery",
    "RetryAfter",
    "RSSAtomAdapter",
    "Transport",
    "TransportRequest",
    "TransportResponse",
    "XRecentSearchAdapter",
]
