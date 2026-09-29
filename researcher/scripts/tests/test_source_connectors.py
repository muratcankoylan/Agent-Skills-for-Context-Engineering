from __future__ import annotations

import hashlib
import json
import socket
import threading
import time
import unittest
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime
from typing import Callable
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from researcher.scripts import source_connectors

from researcher.scripts.source_connectors import (
    ArxivAtomAdapter,
    ConnectorDisabledError,
    ConnectorError,
    ContactsDisabledAdapter,
    GitHubAPIAdapter,
    GitHubAtomAdapter,
    HackerNewsAPIAdapter,
    Lead,
    LeadPage,
    LimitExceededError,
    Limits,
    MalformedResponseError,
    ManualSeedAdapter,
    PolicyError,
    PinnedHTTPSTransport,
    QuerySpec,
    RetryAfter,
    RSSAtomAdapter,
    TransportRequest,
    TransportResponse,
    XRecentSearchAdapter,
    replay_discovery,
)


PUBLIC_V4 = "93.184.216.34"
FIXED_NOW = datetime(2026, 8, 25, 12, 0, tzinfo=UTC)


class FakeClock:
    def __init__(self) -> None:
        self.value = 100.0

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


class ScriptedResolver:
    def __init__(self, answers: dict[str, list[tuple[str, ...]]]):
        self.answers = {host: list(values) for host, values in answers.items()}
        self.calls: list[tuple[str, int]] = []

    def __call__(self, hostname: str, port: int) -> tuple[str, ...]:
        self.calls.append((hostname, port))
        values = self.answers[hostname]
        if len(values) > 1:
            return values.pop(0)
        return values[0]


TransportStep = TransportResponse | Callable[[TransportRequest], TransportResponse]


class ScriptedTransport:
    def __init__(self, *steps: TransportStep):
        self.steps = list(steps)
        self.requests: list[TransportRequest] = []

    def request(self, request: TransportRequest) -> TransportResponse:
        self.requests.append(request)
        if not self.steps:
            raise AssertionError("unexpected network request")
        step = self.steps.pop(0)
        return step(request) if callable(step) else step


def resolver_for(*hosts: str, address: str = PUBLIC_V4) -> ScriptedResolver:
    return ScriptedResolver({host: [(address,)] for host in hosts})


def response(
    body: bytes,
    media_type: str,
    *,
    status: int = 200,
    headers: tuple[tuple[str, str], ...] = (),
    truncated: bool = False,
) -> TransportResponse:
    return TransportResponse(
        status,
        (("Content-Type", media_type), ("Content-Length", str(len(body))), *headers),
        body,
        truncated,
    )


def atom_feed(*entries: str) -> bytes:
    return (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<feed xmlns="http://www.w3.org/2005/Atom">' + "".join(entries) + "</feed>"
    ).encode()


def atom_entry(
    title: str,
    link: str,
    *,
    stable_id: str | None = None,
    summary: str = "Summary",
) -> str:
    escaped_link = link.replace("&", "&amp;")
    identifier = f"<id>{stable_id}</id>" if stable_id else ""
    return (
        "<entry>"
        f'{identifier}<title>{title}</title><link href="{escaped_link}"/>'
        "<updated>2026-08-25T00:00:00Z</updated>"
        f"<summary>{summary}</summary>"
        "</entry>"
    )


def rss_feed(*items: str) -> bytes:
    return (
        '<?xml version="1.0"?><rss version="2.0"><channel>'
        + "".join(items)
        + "</channel></rss>"
    ).encode()


def rss_item(title: str, link: str, *, guid: str | None = None) -> str:
    escaped_link = link.replace("&", "&amp;")
    identifier = f"<guid>{guid}</guid>" if guid else ""
    return f"<item>{identifier}<title>{title}</title><link>{escaped_link}</link></item>"


class ContractTests(unittest.TestCase):
    def test_required_contracts_are_frozen(self) -> None:
        query = QuerySpec("agents")
        limits = Limits()
        lead = Lead("manual:1", "manual", "Title", "https://example.com/one")
        page = ManualSeedAdapter([lead], now=lambda: FIXED_NOW).discover(query, limits)
        for value, field, replacement in (
            (query, "text", "changed"),
            (limits, "max_items", 1),
            (lead, "title", "changed"),
            (page.receipt, "item_count", 0),
            (page, "items", ()),
        ):
            with self.subTest(type=type(value).__name__):
                with self.assertRaises(FrozenInstanceError):
                    setattr(value, field, replacement)

    def test_invalid_limits_and_control_characters_fail_before_work(self) -> None:
        with self.assertRaises(ValueError):
            Limits(max_requests=-1)
        with self.assertRaises(ValueError):
            Limits(max_seconds=float("inf"))
        with self.assertRaises(ValueError):
            QuerySpec("bad\x00query")
        with self.assertRaises(ValueError):
            Limits(max_bytes=1_500_001)
        with self.assertRaises(ValueError):
            Limits(max_requests=65)

    def test_receipt_is_explicitly_observation_only(self) -> None:
        seed = Lead("manual:1", "manual", "Title", "https://example.com/one")
        page = ManualSeedAdapter([seed], now=lambda: FIXED_NOW).discover(
            QuerySpec(), Limits()
        )
        self.assertTrue(page.receipt.observation_only)
        self.assertFalse(page.receipt.authoritative)
        self.assertEqual(page.receipt.request_count, 0)
        self.assertEqual(page.receipt.total_bytes, 0)


class ManualSeedTests(unittest.TestCase):
    def test_manual_adapter_filters_and_pages_without_io(self) -> None:
        seeds = (
            Lead("manual:1", "manual", "Agent systems", "https://example.com/one"),
            Lead("manual:2", "manual", "Robotics", "https://example.com/two"),
            Lead("manual:3", "manual", "Agent evaluation", "https://example.com/three"),
        )
        adapter = ManualSeedAdapter(seeds, now=lambda: FIXED_NOW)
        first = adapter.discover(QuerySpec("agent"), Limits(max_items=1))
        self.assertEqual([item.identity for item in first.items], ["manual:1"])
        self.assertEqual(first.next_cursor, "1")
        second = adapter.discover(
            QuerySpec("agent", first.next_cursor), Limits(max_items=1)
        )
        self.assertEqual([item.identity for item in second.items], ["manual:3"])
        self.assertIsNone(second.next_cursor)


class NetworkPolicyTests(unittest.TestCase):
    def adapter(
        self,
        transport: ScriptedTransport,
        resolver: ScriptedResolver,
        *,
        clock: FakeClock | None = None,
    ) -> RSSAtomAdapter:
        return RSSAtomAdapter(
            "https://feeds.example/research.atom",
            allowed_hosts={"feeds.example", "redirect.example"},
            transport=transport,
            resolver=resolver,
            clock=clock or FakeClock(),
            now=lambda: FIXED_NOW,
        )

    def test_zero_limit_makes_no_network_request(self) -> None:
        for limits in (
            Limits(max_items=0),
            Limits(max_requests=0),
            Limits(max_pages=0),
            Limits(max_bytes=0),
            Limits(max_seconds=0),
        ):
            with self.subTest(limits=limits):
                transport = ScriptedTransport()
                page = self.adapter(
                    transport,
                    resolver_for("feeds.example", "redirect.example"),
                ).discover(QuerySpec(cursor="watermark"), limits)
                self.assertIsInstance(page, LeadPage)
                self.assertEqual(page.items, ())
                self.assertEqual(page.next_cursor, "watermark")
                self.assertEqual(transport.requests, [])

    def test_loopback_private_and_reserved_addresses_are_rejected(self) -> None:
        addresses = (
            "127.0.0.1",
            "10.10.10.10",
            "169.254.1.1",
            "::1",
            "fd00::1",
            "2001:db8::1",
        )
        for address in addresses:
            with self.subTest(address=address):
                transport = ScriptedTransport()
                resolver = ScriptedResolver({"feeds.example": [(address,)]})
                adapter = RSSAtomAdapter(
                    "https://feeds.example/research.atom",
                    allowed_hosts={"feeds.example"},
                    transport=transport,
                    resolver=resolver,
                    now=lambda: FIXED_NOW,
                )
                with self.assertRaises(PolicyError) as captured:
                    adapter.discover(QuerySpec(), Limits())
                self.assertEqual(captured.exception.code, "DNS_NOT_PUBLIC")
                self.assertEqual(transport.requests, [])

    def test_mixed_public_and_private_dns_answer_fails_closed(self) -> None:
        resolver = ScriptedResolver({"feeds.example": [(PUBLIC_V4, "10.0.0.9")]})
        transport = ScriptedTransport()
        adapter = RSSAtomAdapter(
            "https://feeds.example/research.atom",
            allowed_hosts={"feeds.example"},
            transport=transport,
            resolver=resolver,
            now=lambda: FIXED_NOW,
        )
        with self.assertRaises(PolicyError) as captured:
            adapter.discover(QuerySpec(), Limits())
        self.assertEqual(captured.exception.code, "DNS_NOT_PUBLIC")
        self.assertEqual(transport.requests, [])

    def test_url_credentials_are_rejected_at_configuration_boundary(self) -> None:
        with self.assertRaises(PolicyError) as captured:
            RSSAtomAdapter(
                "https://user:password@feeds.example/feed.atom",
                allowed_hosts={"feeds.example"},
                transport=ScriptedTransport(),
                resolver=resolver_for("feeds.example"),
                now=lambda: FIXED_NOW,
            )
        self.assertEqual(captured.exception.code, "URL_CREDENTIALS")

    def test_redirect_to_private_address_is_revalidated_and_rejected(self) -> None:
        redirect = response(
            b"",
            "text/plain",
            status=302,
            headers=(("Location", "https://redirect.example/internal"),),
        )
        transport = ScriptedTransport(redirect)
        resolver = ScriptedResolver(
            {
                "feeds.example": [(PUBLIC_V4,)],
                "redirect.example": [("192.168.1.8",)],
            }
        )
        with self.assertRaises(PolicyError) as captured:
            self.adapter(transport, resolver).discover(QuerySpec(), Limits())
        self.assertEqual(captured.exception.code, "DNS_NOT_PUBLIC")
        self.assertEqual(len(transport.requests), 1)

    def test_same_hostname_dns_rebinding_is_revalidated_and_rejected(self) -> None:
        redirect = response(
            b"",
            "text/plain",
            status=302,
            headers=(("Location", "/second.atom"),),
        )
        transport = ScriptedTransport(redirect)
        resolver = ScriptedResolver({"feeds.example": [(PUBLIC_V4,), ("127.0.0.1",)]})
        with self.assertRaises(PolicyError) as captured:
            self.adapter(transport, resolver).discover(QuerySpec(), Limits())
        self.assertEqual(captured.exception.code, "DNS_NOT_PUBLIC")
        self.assertEqual(
            resolver.calls,
            [("feeds.example", 443), ("feeds.example", 443)],
        )
        self.assertEqual(len(transport.requests), 1)

    def test_redirect_to_non_allowlisted_subdomain_is_rejected_exactly(self) -> None:
        redirect = response(
            b"",
            "text/plain",
            status=302,
            headers=(("Location", "https://sub.feeds.example/feed"),),
        )
        transport = ScriptedTransport(redirect)
        resolver = resolver_for("feeds.example", "redirect.example")
        with self.assertRaises(PolicyError) as captured:
            self.adapter(transport, resolver).discover(QuerySpec(), Limits())
        self.assertEqual(captured.exception.code, "HOST_NOT_ALLOWED")
        self.assertEqual(len(transport.requests), 1)

    def test_truncated_response_fails_closed_with_exact_partial_digest(self) -> None:
        body = b"<feed"
        transport = ScriptedTransport(
            response(body, "application/atom+xml", truncated=True)
        )
        with self.assertRaises(MalformedResponseError) as captured:
            self.adapter(
                transport,
                resolver_for("feeds.example", "redirect.example"),
            ).discover(QuerySpec(), Limits())
        self.assertEqual(captured.exception.code, "TRUNCATED_RESPONSE")
        receipt = captured.exception.receipt
        self.assertIsNotNone(receipt)
        assert receipt is not None
        self.assertEqual(
            receipt.observations[0].response_sha256,
            "sha256:" + hashlib.sha256(body).hexdigest(),
        )

    def test_total_byte_limit_is_enforced_against_injected_transport(self) -> None:
        transport = ScriptedTransport(response(b"1234", "application/atom+xml"))
        with self.assertRaises(LimitExceededError) as captured:
            self.adapter(
                transport,
                resolver_for("feeds.example", "redirect.example"),
            ).discover(QuerySpec(), Limits(max_bytes=3))
        self.assertEqual(captured.exception.code, "BYTE_LIMIT")

    def test_wall_time_limit_is_checked_after_transport(self) -> None:
        clock = FakeClock()

        def slow(_: TransportRequest) -> TransportResponse:
            clock.advance(1.1)
            return response(atom_feed(), "application/atom+xml")

        transport = ScriptedTransport(slow)
        with self.assertRaises(LimitExceededError) as captured:
            self.adapter(
                transport,
                resolver_for("feeds.example", "redirect.example"),
                clock=clock,
            ).discover(QuerySpec(), Limits(max_seconds=1))
        self.assertEqual(captured.exception.code, "TIME_LIMIT")

    def test_compressed_content_is_rejected_before_parsing(self) -> None:
        transport = ScriptedTransport(
            response(
                b"compressed",
                "application/atom+xml",
                headers=(("Content-Encoding", "gzip"),),
            )
        )
        with self.assertRaises(PolicyError) as captured:
            self.adapter(
                transport,
                resolver_for("feeds.example", "redirect.example"),
            ).discover(QuerySpec(), Limits())
        self.assertEqual(captured.exception.code, "CONTENT_ENCODING_UNSUPPORTED")

    def test_failed_transport_attempt_has_receipt_and_counts_toward_budget(
        self,
    ) -> None:
        def fail(_: TransportRequest) -> TransportResponse:
            raise ConnectorError("TRANSPORT_FAILURE", "test connection failed")

        transport = ScriptedTransport(fail)
        with self.assertRaises(ConnectorError) as captured:
            self.adapter(transport, resolver_for("feeds.example")).discover(
                QuerySpec(), Limits(max_requests=1)
            )
        receipt = captured.exception.receipt
        assert receipt is not None
        self.assertEqual(receipt.request_count, 1)
        self.assertEqual(receipt.observations, ())
        self.assertEqual(receipt.total_bytes, 0)

    def test_dns_time_consumes_deadline_before_any_transport_effect(self) -> None:
        clock = FakeClock()

        def slow_resolver(hostname: str, port: int) -> tuple[str, ...]:
            clock.advance(1.1)
            return (PUBLIC_V4,)

        transport = ScriptedTransport()
        adapter = RSSAtomAdapter(
            "https://feeds.example/feed.atom",
            allowed_hosts={"feeds.example"},
            transport=transport,
            resolver=slow_resolver,
            clock=clock,
            now=lambda: FIXED_NOW,
        )
        with self.assertRaises(LimitExceededError) as captured:
            adapter.discover(QuerySpec(), Limits(max_seconds=1))
        self.assertEqual(captured.exception.code, "TIME_LIMIT")
        assert captured.exception.receipt is not None
        self.assertEqual(captured.exception.receipt.request_count, 0)
        self.assertEqual(transport.requests, [])

    def test_system_dns_returns_by_deadline_when_os_lookup_stalls(self) -> None:
        finish = threading.Event()
        completed = threading.Event()

        def stalled(*args: object, **kwargs: object) -> list[object]:
            try:
                finish.wait(2)
                return []
            finally:
                completed.set()

        try:
            with patch.object(socket, "getaddrinfo", side_effect=stalled):
                started = time.monotonic()
                with self.assertRaises(LimitExceededError) as captured:
                    source_connectors._system_resolver(
                        "feeds.example", 443, timeout=0.02
                    )
                self.assertEqual(captured.exception.code, "TIME_LIMIT")
                self.assertLess(time.monotonic() - started, 0.5)
        finally:
            finish.set()
            self.assertTrue(completed.wait(1))

    def test_absolute_deadline_stops_slow_trickled_headers(self) -> None:
        client, server = socket.socketpair()
        done = threading.Event()

        class TestTLSContext:
            def wrap_socket(
                self, connection: socket.socket, **kwargs: object
            ) -> socket.socket:
                return connection

        def trickle() -> None:
            try:
                server.recv(4096)
                for value in b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n":
                    server.sendall(bytes([value]))
                    if done.wait(0.02):
                        break
            except OSError:
                pass
            finally:
                server.close()

        peer = threading.Thread(target=trickle, daemon=True)
        peer.start()
        started = time.monotonic()
        try:
            with patch.object(socket, "create_connection", return_value=client):
                with self.assertRaises(LimitExceededError) as captured:
                    PinnedHTTPSTransport(ssl_context=TestTLSContext()).request(
                        TransportRequest(
                            "https://feeds.example/feed",
                            PUBLIC_V4,
                            (),
                            started + 0.06,
                            1000,
                        )
                    )
                self.assertEqual(captured.exception.code, "TIME_LIMIT")
                self.assertLess(time.monotonic() - started, 0.5)
        finally:
            done.set()
            client.close()
            peer.join(timeout=1)


class FeedAdapterTests(unittest.TestCase):
    def test_capped_feed_resume_returns_remaining_entries(self) -> None:
        body = atom_feed(
            *[
                atom_entry(
                    f"Agent {number}",
                    f"https://articles.example/{number}",
                    stable_id=f"id:{number}",
                )
                for number in (3, 2, 1)
            ]
        )
        adapter = RSSAtomAdapter(
            "https://feeds.example/feed.atom",
            allowed_hosts={"feeds.example"},
            transport=ScriptedTransport(
                *[response(body, "application/atom+xml") for _ in range(4)]
            ),
            resolver=resolver_for("feeds.example"),
            now=lambda: FIXED_NOW,
        )
        cursor = None
        seen = []
        for _ in range(4):
            page = adapter.discover(QuerySpec("agent", cursor), Limits(max_items=1))
            assert isinstance(page, LeadPage)
            seen.extend(item.title for item in page.items)
            cursor = page.next_cursor
        self.assertEqual(seen, ["Agent 3", "Agent 2", "Agent 1"])

    def test_feed_cursor_query_mismatch_fails_before_network(self) -> None:
        body = atom_feed(atom_entry("Agent memory", "https://articles.example/1"))
        transport = ScriptedTransport(
            response(body, "application/atom+xml"),
            response(body, "application/atom+xml"),
        )
        adapter = RSSAtomAdapter(
            "https://feeds.example/feed.atom",
            allowed_hosts={"feeds.example"},
            transport=transport,
            resolver=resolver_for("feeds.example"),
            now=lambda: FIXED_NOW,
        )
        page = adapter.discover(QuerySpec("agent"), Limits(max_items=1))
        assert isinstance(page, LeadPage)
        with self.assertRaises(ConnectorError) as captured:
            adapter.discover(QuerySpec("memory", page.next_cursor), Limits(max_items=1))
        self.assertEqual(captured.exception.code, "CURSOR_SCOPE_MISMATCH")
        self.assertEqual(len(transport.requests), 1)

    def test_prepended_items_wait_until_capped_window_is_drained(self) -> None:
        # Every entry has the same timestamp: ordering/resume depends on stable
        # identities, not timestamp uniqueness or a clock comparison.
        def feed(numbers: tuple[int, ...]) -> bytes:
            return atom_feed(
                *[
                    atom_entry(
                        f"Agent {number}",
                        f"https://articles.example/{number}",
                        stable_id=f"id:{number}",
                    )
                    for number in numbers
                ]
            )

        bodies = [feed((3, 2, 1))] + [feed((4, 3, 2, 1))] * 4
        adapter = RSSAtomAdapter(
            "https://feeds.example/feed.atom",
            allowed_hosts={"feeds.example"},
            transport=ScriptedTransport(
                *[response(body, "application/atom+xml") for body in bodies]
            ),
            resolver=resolver_for("feeds.example"),
            now=lambda: FIXED_NOW,
        )
        cursor = None
        seen = []
        for _ in bodies:
            page = adapter.discover(QuerySpec("agent", cursor), Limits(max_items=1))
            assert isinstance(page, LeadPage)
            seen.extend(item.title for item in page.items)
            cursor = page.next_cursor
            assert cursor is not None
            self.assertLessEqual(len(cursor), 2048)
        self.assertEqual(seen, ["Agent 3", "Agent 2", "Agent 1", "Agent 4"])

    def test_changed_or_missing_resume_window_fails_explicitly(self) -> None:
        def feed(numbers: tuple[int, ...]) -> bytes:
            return atom_feed(
                *[
                    atom_entry(
                        f"Agent {number}",
                        f"https://articles.example/{number}",
                        stable_id=f"id:{number}",
                    )
                    for number in numbers
                ]
            )

        for changed in ((2, 1), (3, 2), (3, 4, 2, 1), (3, 1, 2)):
            with self.subTest(changed=changed):
                adapter = RSSAtomAdapter(
                    "https://feeds.example/feed.atom",
                    allowed_hosts={"feeds.example"},
                    transport=ScriptedTransport(
                        response(feed((3, 2, 1)), "application/atom+xml"),
                        response(feed(changed), "application/atom+xml"),
                    ),
                    resolver=resolver_for("feeds.example"),
                    now=lambda: FIXED_NOW,
                )
                page = adapter.discover(QuerySpec(), Limits(max_items=1))
                assert isinstance(page, LeadPage)
                with self.assertRaises(ConnectorError) as captured:
                    adapter.discover(
                        QuerySpec(cursor=page.next_cursor), Limits(max_items=1)
                    )
                self.assertEqual(captured.exception.code, "CURSOR_STALE")
                assert captured.exception.receipt is not None
                self.assertEqual(captured.exception.receipt.request_count, 1)

    def test_missing_committed_watermark_fails_explicitly(self) -> None:
        first = atom_feed(
            atom_entry("One", "https://articles.example/1", stable_id="id:1")
        )
        second = atom_feed(
            atom_entry("Two", "https://articles.example/2", stable_id="id:2")
        )
        adapter = RSSAtomAdapter(
            "https://feeds.example/feed.atom",
            allowed_hosts={"feeds.example"},
            transport=ScriptedTransport(
                response(first, "application/atom+xml"),
                response(second, "application/atom+xml"),
            ),
            resolver=resolver_for("feeds.example"),
            now=lambda: FIXED_NOW,
        )
        page = adapter.discover(QuerySpec(), Limits())
        assert isinstance(page, LeadPage)
        with self.assertRaises(ConnectorError) as captured:
            adapter.discover(QuerySpec(cursor=page.next_cursor), Limits())
        self.assertEqual(captured.exception.code, "CURSOR_STALE")

    def test_feed_scope_binding_covers_url_without_exposing_query(self) -> None:
        canary = "PRIVATE-QUERY-CANARY"
        body = atom_feed(atom_entry(canary, "https://articles.example/1"))
        first = RSSAtomAdapter(
            "https://feeds.example/feed.atom?channel=one",
            allowed_hosts={"feeds.example"},
            transport=ScriptedTransport(response(body, "application/atom+xml")),
            resolver=resolver_for("feeds.example"),
            now=lambda: FIXED_NOW,
        ).discover(QuerySpec(canary), Limits())
        assert isinstance(first, LeadPage)
        assert first.next_cursor is not None
        self.assertNotIn(canary, repr(first.next_cursor))
        decoded = source_connectors.base64.urlsafe_b64decode(
            first.next_cursor[8:]
        ).decode()
        self.assertNotIn(canary, decoded)
        transport = ScriptedTransport()
        second = RSSAtomAdapter(
            "https://feeds.example/feed.atom?channel=two",
            allowed_hosts={"feeds.example"},
            transport=transport,
            resolver=resolver_for("feeds.example"),
            now=lambda: FIXED_NOW,
        )
        with self.assertRaises(ConnectorError) as captured:
            second.discover(QuerySpec(canary, first.next_cursor), Limits())
        self.assertEqual(captured.exception.code, "CURSOR_SCOPE_MISMATCH")
        self.assertNotIn(canary, str(captured.exception))
        self.assertEqual(transport.requests, [])

    def test_duplicate_feed_identity_is_rejected_before_cursor_advances(self) -> None:
        body = atom_feed(
            atom_entry("One", "https://articles.example/1", stable_id="duplicate"),
            atom_entry("Two", "https://articles.example/2", stable_id="duplicate"),
        )
        with self.assertRaises(MalformedResponseError) as captured:
            RSSAtomAdapter(
                "https://feeds.example/feed.atom",
                allowed_hosts={"feeds.example"},
                transport=ScriptedTransport(response(body, "application/atom+xml")),
                resolver=resolver_for("feeds.example"),
                now=lambda: FIXED_NOW,
            ).discover(QuerySpec(), Limits(max_items=1))
        self.assertEqual(captured.exception.code, "FEED_IDENTITY_DUPLICATE")

    def test_legacy_or_malformed_feed_cursors_fail_before_request(self) -> None:
        for cursor in ("rss_atom:sha256:" + "a" * 64, "feed-v1:!bad!", "feed-v1:e30="):
            with self.subTest(cursor=cursor):
                transport = ScriptedTransport()
                with self.assertRaises(ConnectorError) as captured:
                    RSSAtomAdapter(
                        "https://feeds.example/feed.atom",
                        allowed_hosts={"feeds.example"},
                        transport=transport,
                        resolver=resolver_for("feeds.example"),
                        now=lambda: FIXED_NOW,
                    ).discover(QuerySpec(cursor=cursor), Limits())
                self.assertEqual(captured.exception.code, "CURSOR_INVALID")
                self.assertEqual(transport.requests, [])

    def test_github_atom_uses_same_query_bound_capped_resume(self) -> None:
        body = atom_feed(
            atom_entry(
                "Agent one",
                "https://github.com/acme/project/commit/1",
                stable_id="commit:1",
            ),
            atom_entry(
                "Agent two",
                "https://github.com/acme/project/commit/2",
                stable_id="commit:2",
            ),
        )
        adapter = GitHubAtomAdapter(
            "acme/project",
            resource="commits",
            transport=ScriptedTransport(
                response(body, "application/atom+xml"),
                response(body, "application/atom+xml"),
            ),
            resolver=resolver_for("github.com"),
            now=lambda: FIXED_NOW,
        )
        first = adapter.discover(QuerySpec("agent"), Limits(max_items=1))
        assert isinstance(first, LeadPage)
        second = adapter.discover(
            QuerySpec("agent", first.next_cursor), Limits(max_items=1)
        )
        assert isinstance(second, LeadPage)
        self.assertEqual([item.title for item in second.items], ["Agent two"])

    def test_atom_output_is_item_bounded_and_digest_is_exact(self) -> None:
        body = atom_feed(
            atom_entry("One", "https://articles.example/One", stable_id="tag:one"),
            atom_entry("Two", "https://articles.example/Two", stable_id="tag:two"),
            atom_entry(
                "Three", "https://articles.example/Three", stable_id="tag:three"
            ),
        )
        transport = ScriptedTransport(
            response(body, "application/atom+xml; charset=utf-8")
        )
        page = RSSAtomAdapter(
            "https://feeds.example/feed.atom",
            allowed_hosts={"feeds.example"},
            transport=transport,
            resolver=resolver_for("feeds.example"),
            now=lambda: FIXED_NOW,
        ).discover(QuerySpec(), Limits(max_items=2))
        self.assertIsInstance(page, LeadPage)
        assert isinstance(page, LeadPage)
        self.assertEqual([item.title for item in page.items], ["One", "Two"])
        self.assertEqual(page.receipt.total_bytes, len(body))
        self.assertEqual(
            page.receipt.observations[0].response_sha256,
            "sha256:" + hashlib.sha256(body).hexdigest(),
        )

    def test_rss_links_have_collision_resistant_case_sensitive_identities(self) -> None:
        body = rss_feed(
            rss_item("Upper token", "https://articles.example/Paper?Token=ABC"),
            rss_item("Lower token", "https://articles.example/Paper?Token=abc"),
            rss_item("Lower path", "https://articles.example/paper?Token=ABC"),
        )
        transport = ScriptedTransport(response(body, "application/rss+xml"))
        page = RSSAtomAdapter(
            "https://feeds.example/feed.xml",
            allowed_hosts={"feeds.example"},
            transport=transport,
            resolver=resolver_for("feeds.example"),
            now=lambda: FIXED_NOW,
        ).discover(QuerySpec(), Limits())
        assert isinstance(page, LeadPage)
        self.assertEqual(len({item.identity for item in page.items}), 3)
        self.assertEqual(page.items[0].url, "https://articles.example/Paper?Token=ABC")
        self.assertEqual(page.items[1].url, "https://articles.example/Paper?Token=abc")
        self.assertEqual(page.items[2].url, "https://articles.example/paper?Token=ABC")
        self.assertNotIn("Token=ABC", repr(page.items[0]))

    def test_feed_query_scans_past_nonmatching_items_within_the_bounded_body(
        self,
    ) -> None:
        body = atom_feed(
            atom_entry("Unrelated", "https://articles.example/one"),
            atom_entry("Agent systems", "https://articles.example/two"),
        )
        transport = ScriptedTransport(response(body, "application/atom+xml"))
        page = RSSAtomAdapter(
            "https://feeds.example/feed.atom",
            allowed_hosts={"feeds.example"},
            transport=transport,
            resolver=resolver_for("feeds.example"),
            now=lambda: FIXED_NOW,
        ).discover(QuerySpec("agent"), Limits(max_items=1))
        assert isinstance(page, LeadPage)
        self.assertEqual([item.title for item in page.items], ["Agent systems"])

    def test_malformed_atom_fails_closed(self) -> None:
        transport = ScriptedTransport(
            response(b"<feed><entry>", "application/atom+xml")
        )
        adapter = RSSAtomAdapter(
            "https://feeds.example/feed.atom",
            allowed_hosts={"feeds.example"},
            transport=transport,
            resolver=resolver_for("feeds.example"),
            now=lambda: FIXED_NOW,
        )
        with self.assertRaises(MalformedResponseError) as captured:
            adapter.discover(QuerySpec(), Limits())
        self.assertEqual(captured.exception.code, "XML_MALFORMED")

    def test_utf16_dtd_cannot_bypass_entity_rejection(self) -> None:
        body = (
            '<?xml version="1.0" encoding="utf-16"?>'
            '<!DOCTYPE feed [<!ENTITY message "Entity content">]>'
            '<feed xmlns="http://www.w3.org/2005/Atom">'
            '<entry><title>&message;</title><link href="https://example.com/a"/>'
            "</entry></feed>"
        ).encode("utf-16")
        with self.assertRaises(MalformedResponseError) as captured:
            RSSAtomAdapter(
                "https://feeds.example/feed.atom",
                allowed_hosts={"feeds.example"},
                transport=ScriptedTransport(response(body, "application/atom+xml")),
                resolver=resolver_for("feeds.example"),
                now=lambda: FIXED_NOW,
            ).discover(QuerySpec(), Limits())
        self.assertEqual(captured.exception.code, "XML_UNSAFE")

    def test_deep_json_provider_structure_fails_closed(self) -> None:
        body = b"[" * 1500 + b"0" + b"]" * 1500
        with self.assertRaises(MalformedResponseError) as captured:
            GitHubAPIAdapter(
                "acme/project",
                transport=ScriptedTransport(response(body, "application/json")),
                resolver=resolver_for("api.github.com"),
                now=lambda: FIXED_NOW,
            ).discover(QuerySpec(), Limits())
        # This is valid JSON but not a GitHub release array. Some Python
        # decoders exhaust their recursion budget before provider validation;
        # both paths must retain a typed failure and the observation receipt.
        assert captured.exception.receipt is not None
        self.assertEqual(captured.exception.receipt.request_count, 1)
        self.assertEqual(captured.exception.receipt.total_bytes, len(body))

    def test_json_parser_recursion_failure_has_stable_translation(self) -> None:
        adapter = GitHubAPIAdapter(
            "acme/project",
            transport=ScriptedTransport(response(b"[]", "application/json")),
            resolver=resolver_for("api.github.com"),
            now=lambda: FIXED_NOW,
        )
        with patch.object(source_connectors.json, "loads", side_effect=RecursionError):
            with self.assertRaises(MalformedResponseError) as captured:
                adapter.discover(QuerySpec(), Limits())
        self.assertEqual(captured.exception.code, "JSON_MALFORMED")
        assert captured.exception.receipt is not None
        self.assertEqual(captured.exception.receipt.request_count, 1)

    def test_html_challenge_with_200_status_fails_closed(self) -> None:
        challenge = b"<html><title>Verifying your browser</title></html>"
        transport = ScriptedTransport(response(challenge, "text/html"))
        adapter = RSSAtomAdapter(
            "https://feeds.example/feed.atom",
            allowed_hosts={"feeds.example"},
            transport=transport,
            resolver=resolver_for("feeds.example"),
            now=lambda: FIXED_NOW,
        )
        with self.assertRaises(MalformedResponseError) as captured:
            adapter.discover(QuerySpec(), Limits())
        self.assertEqual(captured.exception.code, "MEDIA_TYPE_UNEXPECTED")

    def test_429_returns_typed_retry_after_without_sleeping(self) -> None:
        body = b'{"error":"rate limited"}'
        transport = ScriptedTransport(
            response(
                body,
                "application/problem+json",
                status=429,
                headers=(("Retry-After", "17"),),
            )
        )
        result = RSSAtomAdapter(
            "https://feeds.example/feed.atom",
            allowed_hosts={"feeds.example"},
            transport=transport,
            resolver=resolver_for("feeds.example"),
            now=lambda: FIXED_NOW,
        ).discover(QuerySpec(), Limits())
        self.assertIsInstance(result, RetryAfter)
        assert isinstance(result, RetryAfter)
        self.assertEqual(result.retry_after_seconds, 17)
        self.assertEqual(result.receipt.request_count, 1)
        self.assertEqual(
            result.receipt.observations[0].response_sha256,
            "sha256:" + hashlib.sha256(body).hexdigest(),
        )


class SourceSpecificAdapterTests(unittest.TestCase):
    def test_arxiv_scope_and_match_encode_explicit_field_queries(self) -> None:
        expected = {
            ("all", "terms"): 'all:"context" AND all:"engineering"',
            ("all", "phrase"): 'all:"context engineering"',
            (
                "title_abstract",
                "terms",
            ): '(ti:"context" OR abs:"context") AND (ti:"engineering" OR abs:"engineering")',
            (
                "title_abstract",
                "phrase",
            ): '(ti:"context engineering" OR abs:"context engineering")',
        }
        for (scope, match), expression in expected.items():
            with self.subTest(scope=scope, match=match):
                transport = ScriptedTransport(
                    response(atom_feed(), "application/atom+xml")
                )
                ArxivAtomAdapter(
                    search_scope=scope,
                    search_match=match,
                    transport=transport,
                    resolver=resolver_for("export.arxiv.org"),
                    now=lambda: FIXED_NOW,
                ).discover(QuerySpec("context engineering"), Limits())
                parameters = parse_qs(urlsplit(transport.requests[0].url).query)
                self.assertEqual(parameters["search_query"], [expression])
                self.assertEqual(parameters["sortBy"], ["submittedDate"])
                self.assertEqual(parameters["sortOrder"], ["descending"])

    def test_arxiv_query_operators_quotes_and_backslashes_remain_literal_data(
        self,
    ) -> None:
        text = 'agent" OR all:other \\memory'
        for scope, match in (("all", "terms"), ("title_abstract", "phrase")):
            with self.subTest(scope=scope, match=match):
                transport = ScriptedTransport(
                    response(atom_feed(), "application/atom+xml")
                )
                ArxivAtomAdapter(
                    search_scope=scope,
                    search_match=match,
                    transport=transport,
                    resolver=resolver_for("export.arxiv.org"),
                    now=lambda: FIXED_NOW,
                ).discover(QuerySpec(text), Limits())
                encoded = parse_qs(urlsplit(transport.requests[0].url).query)[
                    "search_query"
                ][0]
                if match == "phrase":
                    literal = json.dumps(text, ensure_ascii=False)
                    self.assertEqual(encoded, f"(ti:{literal} OR abs:{literal})")
                else:
                    self.assertEqual(
                        encoded,
                        'all:"agent\\"" AND all:"OR" AND all:"all:other" AND all:"\\\\memory"',
                    )

    def test_arxiv_invalid_search_options_fail_before_network_setup(self) -> None:
        for options in (
            {"search_scope": "author"},
            {"search_match": "boolean"},
            {"search_scope": []},
            {"search_match": None},
        ):
            with (
                self.subTest(options=options),
                patch.object(
                    source_connectors,
                    "_SafeHTTPClient",
                    side_effect=AssertionError("client setup forbidden"),
                ),
            ):
                with self.assertRaises(ValueError):
                    ArxivAtomAdapter(**options)

    def test_arxiv_official_http_article_link_is_upgraded_without_http_fetch(
        self,
    ) -> None:
        body = atom_feed(
            atom_entry(
                "Paper",
                "http://arxiv.org/abs/2608.12345v1",
                stable_id="http://arxiv.org/abs/2608.12345v1",
            )
        )
        transport = ScriptedTransport(response(body, "application/atom+xml"))
        page = ArxivAtomAdapter(
            transport=transport,
            resolver=resolver_for("export.arxiv.org"),
            now=lambda: FIXED_NOW,
        ).discover(QuerySpec("context engineering"), Limits(max_items=1))
        assert isinstance(page, LeadPage)
        self.assertEqual(page.items[0].url, "https://arxiv.org/abs/2608.12345v1")
        self.assertTrue(
            all(request.url.startswith("https://") for request in transport.requests)
        )
        self.assertEqual(
            parse_qs(urlsplit(transport.requests[0].url).query)["search_query"],
            ['all:"context" AND all:"engineering"'],
        )

    def test_arxiv_200_error_entry_is_not_a_research_paper(self) -> None:
        body = atom_feed(
            atom_entry(
                "Error",
                "http://arxiv.org/api/errors#invalid_query",
                stable_id="http://arxiv.org/api/errors#invalid_query",
            )
        )
        transport = ScriptedTransport(response(body, "application/atom+xml"))
        with self.assertRaises(MalformedResponseError) as captured:
            ArxivAtomAdapter(
                transport=transport,
                resolver=resolver_for("export.arxiv.org"),
                now=lambda: FIXED_NOW,
            ).discover(QuerySpec("agents"), Limits())
        self.assertEqual(captured.exception.code, "ARXIV_SCHEMA_INVALID")

    def test_generic_feed_does_not_upgrade_arbitrary_http_links(self) -> None:
        body = atom_feed(atom_entry("Paper", "http://articles.example/one"))
        with self.assertRaises(MalformedResponseError):
            RSSAtomAdapter(
                "https://feeds.example/feed.atom",
                allowed_hosts={"feeds.example"},
                transport=ScriptedTransport(response(body, "application/atom+xml")),
                resolver=resolver_for("feeds.example"),
                now=lambda: FIXED_NOW,
            ).discover(QuerySpec(), Limits())

    def test_arxiv_query_is_redacted_from_receipt_and_request_repr(self) -> None:
        body = atom_feed(
            atom_entry(
                "Bounded agents",
                "https://arxiv.org/abs/2608.12345",
                stable_id="https://arxiv.org/abs/2608.12345v1",
            )
        )
        transport = ScriptedTransport(response(body, "application/atom+xml"))
        canary = "NOT-A-REAL-SECRET"
        page = ArxivAtomAdapter(
            transport=transport,
            resolver=resolver_for("export.arxiv.org"),
            now=lambda: FIXED_NOW,
        ).discover(QuerySpec(f"agent systems {canary}"), Limits(max_items=1))
        assert isinstance(page, LeadPage)
        observation = page.receipt.observations[0]
        self.assertEqual(observation.request_url, "https://export.arxiv.org/api/query")
        self.assertTrue(observation.query_redacted)
        self.assertNotIn(canary, repr(page.receipt))
        self.assertNotIn(canary, repr(transport.requests[0]))
        self.assertEqual(page.items[0].url, "https://arxiv.org/abs/2608.12345")

    def test_github_atom_adapter_uses_fixed_official_host(self) -> None:
        body = atom_feed(
            atom_entry(
                "Release v1",
                "https://github.com/acme/project/releases/tag/v1",
                stable_id="tag:github.com,2008:Repository/1/v1",
            )
        )
        transport = ScriptedTransport(response(body, "application/atom+xml"))
        page = GitHubAtomAdapter(
            "acme/project",
            transport=transport,
            resolver=resolver_for("github.com"),
            now=lambda: FIXED_NOW,
        ).discover(QuerySpec(), Limits())
        assert isinstance(page, LeadPage)
        self.assertEqual(len(page.items), 1)
        self.assertEqual(
            transport.requests[0].url, "https://github.com/acme/project/releases.atom"
        )

    def test_github_api_release_and_commit_shapes(self) -> None:
        release = [
            {
                "id": 7,
                "name": "v1",
                "tag_name": "v1",
                "html_url": "https://github.com/acme/project/releases/tag/v1",
                "published_at": "2026-08-25T00:00:00Z",
                "body": "Notes",
            }
        ]
        release_transport = ScriptedTransport(
            response(json.dumps(release).encode(), "application/json")
        )
        release_page = GitHubAPIAdapter(
            "acme/project",
            transport=release_transport,
            resolver=resolver_for("api.github.com"),
            now=lambda: FIXED_NOW,
        ).discover(QuerySpec(), Limits(max_items=1))
        assert isinstance(release_page, LeadPage)
        self.assertEqual(release_page.items[0].title, "v1")

        commit = [
            {
                "sha": "AbC123",
                "html_url": "https://github.com/acme/project/commit/AbC123",
                "commit": {
                    "message": "Preserve Case\n\nBody",
                    "author": {"name": "A", "date": "2026-08-25T00:00:00Z"},
                },
            }
        ]
        commit_transport = ScriptedTransport(
            response(json.dumps(commit).encode(), "application/json")
        )
        commit_page = GitHubAPIAdapter(
            "acme/project",
            resource="commits",
            transport=commit_transport,
            resolver=resolver_for("api.github.com"),
            now=lambda: FIXED_NOW,
        ).discover(QuerySpec(), Limits(max_items=1))
        assert isinstance(commit_page, LeadPage)
        self.assertEqual(commit_page.items[0].title, "Preserve Case")
        self.assertNotEqual(
            release_page.items[0].identity, commit_page.items[0].identity
        )

    def test_github_malformed_json_fails_closed(self) -> None:
        transport = ScriptedTransport(response(b"{", "application/json"))
        adapter = GitHubAPIAdapter(
            "acme/project",
            transport=transport,
            resolver=resolver_for("api.github.com"),
            now=lambda: FIXED_NOW,
        )
        with self.assertRaises(MalformedResponseError) as captured:
            adapter.discover(QuerySpec(), Limits())
        self.assertEqual(captured.exception.code, "JSON_MALFORMED")

    def test_github_preserves_next_page_at_provider_page_size(self) -> None:
        payload = [
            {
                "id": index,
                "name": f"v{index}",
                "html_url": f"https://github.com/acme/project/releases/tag/v{index}",
            }
            for index in range(100)
        ]
        page = GitHubAPIAdapter(
            "acme/project",
            transport=ScriptedTransport(
                response(json.dumps(payload).encode(), "application/json")
            ),
            resolver=resolver_for("api.github.com"),
            now=lambda: FIXED_NOW,
        ).discover(QuerySpec(), Limits(max_items=150))
        assert isinstance(page, LeadPage)
        self.assertEqual(len(page.items), 100)
        self.assertEqual(page.next_cursor, "2")

    def test_duplicate_json_keys_fail_closed(self) -> None:
        transport = ScriptedTransport(
            response(b'[{"id":1,"id":2}]', "application/json")
        )
        adapter = GitHubAPIAdapter(
            "acme/project",
            transport=transport,
            resolver=resolver_for("api.github.com"),
            now=lambda: FIXED_NOW,
        )
        with self.assertRaises(MalformedResponseError) as captured:
            adapter.discover(QuerySpec(), Limits())
        self.assertEqual(captured.exception.code, "JSON_MALFORMED")

    def test_hacker_news_uses_only_official_api_and_hard_request_limit(self) -> None:
        ids = response(b"[101,102,103]", "application/json")
        first = response(
            json.dumps(
                {
                    "id": 101,
                    "title": "Agent evaluation",
                    "url": "https://example.com/agent?tracking=removed",
                    "time": 1_777_777_777,
                    "by": "alice",
                }
            ).encode(),
            "application/json",
        )
        second = response(
            json.dumps({"id": 102, "title": "Ask HN", "time": 1_777_777_778}).encode(),
            "application/json",
        )
        transport = ScriptedTransport(ids, first, second)
        page = HackerNewsAPIAdapter(
            transport=transport,
            resolver=resolver_for("hacker-news.firebaseio.com"),
            now=lambda: FIXED_NOW,
        ).discover(QuerySpec(), Limits(max_items=5, max_requests=3))
        assert isinstance(page, LeadPage)
        self.assertEqual(len(page.items), 2)
        self.assertEqual(page.receipt.request_count, 3)
        self.assertEqual(page.next_cursor, "2")
        self.assertEqual(
            page.items[0].url, "https://example.com/agent?tracking=removed"
        )
        self.assertEqual(page.items[1].url, "https://news.ycombinator.com/item?id=102")
        self.assertTrue(
            all(
                request.url.startswith("https://hacker-news.firebaseio.com/")
                for request in transport.requests
            )
        )

    def test_hacker_news_malformed_id_array_fails_closed(self) -> None:
        transport = ScriptedTransport(response(b'{"ids":[1]}', "application/json"))
        adapter = HackerNewsAPIAdapter(
            transport=transport,
            resolver=resolver_for("hacker-news.firebaseio.com"),
            now=lambda: FIXED_NOW,
        )
        with self.assertRaises(MalformedResponseError) as captured:
            adapter.discover(QuerySpec(), Limits())
        self.assertEqual(captured.exception.code, "HN_SCHEMA_INVALID")

    def test_hacker_news_skips_tombstones_and_keeps_http_discussion_address(
        self,
    ) -> None:
        payloads = [
            [1, 2, 3],
            {"id": 1, "deleted": True},
            {"id": 2, "dead": True},
            {"id": 3, "title": "Legacy article", "url": "http://example.com/one?id=3"},
        ]
        page = HackerNewsAPIAdapter(
            transport=ScriptedTransport(
                *[
                    response(json.dumps(payload).encode(), "application/json")
                    for payload in payloads
                ]
            ),
            resolver=resolver_for("hacker-news.firebaseio.com"),
            now=lambda: FIXED_NOW,
        ).discover(QuerySpec(), Limits(max_requests=4))
        assert isinstance(page, LeadPage)
        self.assertEqual(len(page.items), 1)
        self.assertEqual(page.items[0].url, "https://news.ycombinator.com/item?id=3")
        self.assertEqual(page.receipt.request_count, 4)
        self.assertIsNone(page.next_cursor)


class RestrictedConnectorTests(unittest.TestCase):
    def test_x_is_disabled_by_default_before_network_work(self) -> None:
        transport = ScriptedTransport()
        adapter = XRecentSearchAdapter(
            environ={},
            transport=transport,
            resolver=resolver_for("api.x.com"),
            now=lambda: FIXED_NOW,
        )
        self.assertFalse(adapter.enabled)
        with self.assertRaises(ConnectorDisabledError) as captured:
            adapter.discover(QuerySpec("agents"), Limits())
        self.assertEqual(captured.exception.code, "CONNECTOR_DISABLED")
        self.assertEqual(transport.requests, [])

    def test_x_uses_only_official_host_and_redacts_fake_credential(self) -> None:
        body = json.dumps(
            {
                "data": [
                    {
                        "id": "123456789",
                        "text": "Observation only",
                        "created_at": "2026-08-25T00:00:00Z",
                        "author_id": "42",
                        "lang": "en",
                    }
                ],
                "meta": {"result_count": 1, "next_token": "cursor-2"},
            }
        ).encode()
        transport = ScriptedTransport(response(body, "application/json"))
        fake_token = "unit-test-placeholder"
        page = XRecentSearchAdapter(
            environ={"X_BEARER_TOKEN": fake_token},
            transport=transport,
            resolver=resolver_for("api.x.com"),
            now=lambda: FIXED_NOW,
        ).discover(QuerySpec("agent systems"), Limits(max_items=10))
        assert isinstance(page, LeadPage)
        self.assertEqual(page.items[0].identity, "x:tweet:123456789")
        self.assertEqual(page.next_cursor, "cursor-2")
        self.assertEqual(transport.requests[0].connect_ip, PUBLIC_V4)
        self.assertTrue(transport.requests[0].url.startswith("https://api.x.com/2/"))
        self.assertNotIn(fake_token, repr(transport.requests[0]))
        self.assertNotIn(fake_token, repr(page.receipt))
        self.assertNotIn("agent systems", repr(page.receipt))

    def test_x_rejects_item_limit_below_provider_minimum_before_request(self) -> None:
        transport = ScriptedTransport()
        adapter = XRecentSearchAdapter(
            environ={"X_BEARER_TOKEN": "unit-test-placeholder"},
            transport=transport,
            resolver=resolver_for("api.x.com"),
            now=lambda: FIXED_NOW,
        )
        with self.assertRaises(ConnectorError) as captured:
            adapter.discover(QuerySpec("agents"), Limits(max_items=3))
        self.assertEqual(captured.exception.code, "ITEM_LIMIT_INCOMPATIBLE")
        self.assertEqual(transport.requests, [])

    def test_x_200_json_challenge_shape_fails_closed(self) -> None:
        transport = ScriptedTransport(
            response(b'{"challenge":"verify browser"}', "application/json")
        )
        adapter = XRecentSearchAdapter(
            environ={"X_BEARER_TOKEN": "unit-test-placeholder"},
            transport=transport,
            resolver=resolver_for("api.x.com"),
            now=lambda: FIXED_NOW,
        )
        with self.assertRaises(MalformedResponseError) as captured:
            adapter.discover(QuerySpec("agents"), Limits())
        self.assertEqual(captured.exception.code, "X_SCHEMA_INVALID")

    def test_x_partial_error_response_fails_closed(self) -> None:
        transport = ScriptedTransport(
            response(
                b'{"data":[],"errors":[{"title":"partial"}],"meta":{"result_count":0}}',
                "application/json",
            )
        )
        adapter = XRecentSearchAdapter(
            environ={"X_BEARER_TOKEN": "unit-test-placeholder"},
            transport=transport,
            resolver=resolver_for("api.x.com"),
            now=lambda: FIXED_NOW,
        )
        with self.assertRaises(MalformedResponseError) as captured:
            adapter.discover(QuerySpec("agents"), Limits())
        self.assertEqual(captured.exception.code, "X_PARTIAL_RESPONSE")


class CaptureSinkTests(unittest.TestCase):
    def test_invalid_sink_is_rejected_at_configuration_boundary(self) -> None:
        with self.assertRaises(ValueError):
            ArxivAtomAdapter(capture_sink=42)

    def test_capture_capacity_fails_closed_without_unbounded_workers(self) -> None:
        captured = []
        adapter = RSSAtomAdapter(
            "https://feeds.example/feed",
            allowed_hosts={"feeds.example"},
            transport=ScriptedTransport(response(atom_feed(), "application/atom+xml")),
            resolver=resolver_for("feeds.example"),
            now=lambda: FIXED_NOW,
            capture_sink=lambda meta, body: captured.append((meta, body)),
        )
        with patch.object(
            source_connectors, "_CAPTURE_SLOTS", threading.BoundedSemaphore(0)
        ):
            with self.assertRaises(ConnectorError) as error:
                adapter.discover(QuerySpec(), Limits())
        self.assertEqual(error.exception.code, "CAPTURE_CAPACITY")
        self.assertEqual(captured, [])
        assert error.exception.receipt is not None
        self.assertEqual(error.exception.receipt.request_count, 1)


class ReplayDiscoveryTests(unittest.TestCase):
    def test_configured_arxiv_factory_replays_scoped_phrase_query(self) -> None:
        captures = []
        body = atom_feed(
            atom_entry("Context research", "http://arxiv.org/abs/2609.12345v1")
        )
        original = ArxivAtomAdapter(
            search_scope="title_abstract",
            search_match="phrase",
            transport=ScriptedTransport(response(body, "application/atom+xml")),
            resolver=resolver_for("export.arxiv.org"),
            now=lambda: FIXED_NOW,
            capture_sink=lambda meta, data: captures.append((meta, data)),
        ).discover(QuerySpec("context engineering"), Limits())

        def factory(**kwargs):
            return ArxivAtomAdapter(
                search_scope="title_abstract", search_match="phrase", **kwargs
            )

        result = replay_discovery(
            factory, captures, QuerySpec("context engineering"), Limits()
        )
        assert isinstance(original, LeadPage) and isinstance(result, LeadPage)
        self.assertEqual(result.items, original.items)
        self.assertEqual(result.next_cursor, original.next_cursor)

    def arxiv_capture(self):
        captures = []
        body = atom_feed(
            atom_entry("Agent research", "http://arxiv.org/abs/2609.12345v1")
        )
        result = ArxivAtomAdapter(
            transport=ScriptedTransport(response(body, "application/atom+xml")),
            resolver=resolver_for("export.arxiv.org"),
            now=lambda: FIXED_NOW,
            capture_sink=lambda meta, data: captures.append((meta, data)),
        ).discover(QuerySpec("agents"), Limits(max_items=1))
        return result, captures

    def test_arxiv_replay_matches_real_parser_without_dns_or_network(self) -> None:
        original, captures = self.arxiv_capture()
        with (
            patch.object(
                socket, "getaddrinfo", side_effect=AssertionError("network forbidden")
            ),
            patch.object(
                PinnedHTTPSTransport,
                "request",
                side_effect=AssertionError("network forbidden"),
            ),
        ):
            result = replay_discovery(
                ArxivAtomAdapter, captures, QuerySpec("agents"), Limits(max_items=1)
            )
        assert isinstance(original, LeadPage) and isinstance(result, LeadPage)
        self.assertEqual(result.items, original.items)
        self.assertEqual(result.next_cursor, original.next_cursor)
        self.assertEqual(result.receipt.total_bytes, original.receipt.total_bytes)

    def test_replay_rejects_missing_extra_reordered_and_corrupt_captures(self) -> None:
        _, captures = self.arxiv_capture()
        meta, body = captures[0]
        cases = (
            ([], "REPLAY_MISSING_CAPTURE"),
            (captures + captures, "REPLAY_EXTRA_CAPTURE"),
            ([(meta, body + b"tamper")], "REPLAY_CAPTURE_INVALID"),
            (
                [(replace(meta, request_url="https://export.arxiv.org/wrong"), body)],
                "REPLAY_REQUEST_MISMATCH",
            ),
            ([(replace(meta, query_redacted=False), body)], "REPLAY_REQUEST_MISMATCH"),
            (
                [
                    (
                        replace(
                            meta, resolved_ips=("127.0.0.1",), connected_ip="127.0.0.1"
                        ),
                        body,
                    )
                ],
                "REPLAY_CAPTURE_INVALID",
            ),
        )
        for saved, expected in cases:
            with self.subTest(expected=expected):
                with self.assertRaises(ConnectorError) as error:
                    replay_discovery(
                        ArxivAtomAdapter,
                        saved,
                        QuerySpec("agents"),
                        Limits(max_items=1),
                    )
                self.assertEqual(error.exception.code, expected)

    def test_hacker_news_multiresponse_replay_checks_request_order(self) -> None:
        captures = []
        payloads = [
            [101, 102],
            {"id": 101, "title": "Agent one", "url": "https://example.com/one"},
            {"id": 102, "title": "Agent two", "url": "https://example.com/two"},
        ]
        original = HackerNewsAPIAdapter(
            transport=ScriptedTransport(
                *[
                    response(json.dumps(value).encode(), "application/json")
                    for value in payloads
                ]
            ),
            resolver=resolver_for("hacker-news.firebaseio.com"),
            now=lambda: FIXED_NOW,
            capture_sink=lambda meta, data: captures.append((meta, data)),
        ).discover(QuerySpec("agent"), Limits(max_items=2))
        result = replay_discovery(
            HackerNewsAPIAdapter, captures, QuerySpec("agent"), Limits(max_items=2)
        )
        assert isinstance(original, LeadPage) and isinstance(result, LeadPage)
        self.assertEqual(result.items, original.items)
        self.assertEqual(result.next_cursor, original.next_cursor)
        with self.assertRaises(ConnectorError) as error:
            replay_discovery(
                HackerNewsAPIAdapter,
                [captures[0], captures[2], captures[1]],
                QuerySpec("agent"),
                Limits(max_items=2),
            )
        self.assertEqual(error.exception.code, "REPLAY_REQUEST_MISMATCH")

    def test_numeric_rate_limit_replays_but_unrecorded_context_is_rejected(
        self,
    ) -> None:
        captures = []
        original = ArxivAtomAdapter(
            transport=ScriptedTransport(
                response(
                    b"rate limit",
                    "text/plain",
                    status=429,
                    headers=(("Retry-After", "17"),),
                )
            ),
            resolver=resolver_for("export.arxiv.org"),
            now=lambda: FIXED_NOW,
            capture_sink=lambda meta, data: captures.append((meta, data)),
        ).discover(QuerySpec("agents"), Limits())
        result = replay_discovery(
            ArxivAtomAdapter, captures, QuerySpec("agents"), Limits()
        )
        assert isinstance(original, RetryAfter) and isinstance(result, RetryAfter)
        self.assertEqual(result.retry_after_seconds, original.retry_after_seconds)
        meta, body = captures[0]
        for altered in (
            replace(meta, status_code=302),
            replace(
                meta,
                safe_headers=tuple(
                    (
                        name,
                        "Tue, 25 Aug 2026 12:01:00 GMT"
                        if name == "retry-after"
                        else value,
                    )
                    for name, value in meta.safe_headers
                ),
            ),
        ):
            with self.assertRaises(ConnectorError) as error:
                replay_discovery(
                    ArxivAtomAdapter, [(altered, body)], QuerySpec("agents"), Limits()
                )
            self.assertEqual(error.exception.code, "REPLAY_UNSUPPORTED_RESPONSE")

    def test_factory_cannot_leave_live_transport_or_capture_sink_enabled(self) -> None:
        _, captures = self.arxiv_capture()

        def ignore_injections(**kwargs):
            return ArxivAtomAdapter()

        def retain_sink(**kwargs):
            return ArxivAtomAdapter(**kwargs, capture_sink=lambda meta, data: None)

        for factory in (ignore_injections, retain_sink):
            with self.assertRaises(ConnectorError) as error:
                replay_discovery(factory, captures, QuerySpec("agents"), Limits())
            self.assertEqual(error.exception.code, "REPLAY_FACTORY_INVALID")

    def test_replay_enforces_capture_byte_and_request_limits_before_factory(
        self,
    ) -> None:
        _, captures = self.arxiv_capture()
        for limits in (Limits(max_requests=0), Limits(max_bytes=1)):
            with self.assertRaises(ConnectorError) as error:
                replay_discovery(
                    lambda **kwargs: self.fail("factory should not run"),
                    captures,
                    QuerySpec("agents"),
                    limits,
                )
            self.assertEqual(error.exception.code, "REPLAY_CAPTURE_LIMIT")


class CaptureSinkBehaviorTests(unittest.TestCase):
    def test_sink_receives_exact_body_and_only_safe_request_metadata(self) -> None:
        captured = []
        body = atom_feed(atom_entry("Paper", "https://arxiv.org/abs/2609.12345v1"))
        page = ArxivAtomAdapter(
            transport=ScriptedTransport(
                response(
                    body,
                    "application/atom+xml",
                    headers=(("Set-Cookie", "PRIVATE-CANARY"),),
                )
            ),
            resolver=resolver_for("export.arxiv.org"),
            now=lambda: FIXED_NOW,
            capture_sink=lambda meta, data: captured.append((meta, data)),
        ).discover(QuerySpec("PRIVATE-CANARY"), Limits())
        assert isinstance(page, LeadPage)
        self.assertEqual(len(captured), 1)
        meta, data = captured[0]
        self.assertEqual(data, body)
        self.assertEqual(meta, page.receipt.observations[0])
        self.assertNotIn("PRIVATE-CANARY", repr(meta))
        self.assertTrue(meta.query_redacted)
        self.assertFalse(meta.truncated)

    def test_sink_captures_redirect_and_rate_limit_before_return(self) -> None:
        captured = []
        transport = ScriptedTransport(
            response(
                b"redirect",
                "text/plain",
                status=302,
                headers=(("Location", "/latest"),),
            ),
            response(
                b"rate limit",
                "text/plain",
                status=429,
                headers=(("Retry-After", "17"),),
            ),
        )
        result = RSSAtomAdapter(
            "https://feeds.example/feed",
            allowed_hosts={"feeds.example"},
            transport=transport,
            resolver=resolver_for("feeds.example"),
            now=lambda: FIXED_NOW,
            capture_sink=lambda meta, body: captured.append((meta, body)),
        ).discover(QuerySpec(), Limits())
        assert isinstance(result, RetryAfter)
        self.assertEqual([meta.status_code for meta, _ in captured], [302, 429])
        self.assertEqual([body for _, body in captured], [b"redirect", b"rate limit"])
        self.assertEqual(result.receipt.request_count, 2)

    def test_truncated_bytes_are_captured_but_discovery_still_fails(self) -> None:
        captured = []
        body = b"<partial"
        with self.assertRaises(MalformedResponseError) as error:
            RSSAtomAdapter(
                "https://feeds.example/feed",
                allowed_hosts={"feeds.example"},
                transport=ScriptedTransport(
                    response(body, "application/atom+xml", truncated=True)
                ),
                resolver=resolver_for("feeds.example"),
                now=lambda: FIXED_NOW,
                capture_sink=lambda meta, data: captured.append((meta, data)),
            ).discover(QuerySpec(), Limits())
        self.assertEqual(error.exception.code, "TRUNCATED_RESPONSE")
        self.assertEqual(captured[0][1], body)
        self.assertTrue(captured[0][0].truncated)

    def test_failed_sink_blocks_discovery_and_preserves_request_accounting(
        self,
    ) -> None:
        def fail(meta: object, body: bytes) -> None:
            raise ValueError("PRIVATE-CANARY")

        body = atom_feed()
        with self.assertRaises(ConnectorError) as error:
            RSSAtomAdapter(
                "https://feeds.example/feed",
                allowed_hosts={"feeds.example"},
                transport=ScriptedTransport(response(body, "application/atom+xml")),
                resolver=resolver_for("feeds.example"),
                now=lambda: FIXED_NOW,
                capture_sink=fail,
            ).discover(QuerySpec(), Limits())
        self.assertEqual(error.exception.code, "CAPTURE_FAILURE")
        self.assertNotIn("PRIVATE-CANARY", str(error.exception))
        assert error.exception.receipt is not None
        self.assertEqual(error.exception.receipt.request_count, 1)
        self.assertEqual(error.exception.receipt.total_bytes, len(body))

    def test_slow_sink_cannot_extend_discovery_deadline(self) -> None:
        finish = threading.Event()
        completed = threading.Event()

        def slow(meta: object, body: bytes) -> None:
            finish.wait(2)
            completed.set()

        adapter = RSSAtomAdapter(
            "https://feeds.example/feed",
            allowed_hosts={"feeds.example"},
            transport=ScriptedTransport(response(atom_feed(), "application/atom+xml")),
            resolver=resolver_for("feeds.example"),
            now=lambda: FIXED_NOW,
            capture_sink=slow,
        )
        started = time.monotonic()
        try:
            with self.assertRaises(LimitExceededError) as error:
                adapter.discover(QuerySpec(), Limits(max_seconds=0.03))
            self.assertEqual(error.exception.code, "TIME_LIMIT")
            self.assertLess(time.monotonic() - started, 0.5)
            assert error.exception.receipt is not None
            self.assertEqual(error.exception.receipt.request_count, 1)
        finally:
            finish.set()
            self.assertTrue(completed.wait(1))

    def test_capture_is_not_called_for_disabled_or_zero_budget_sources(self) -> None:
        captured = []

        def sink(meta: object, body: bytes) -> None:
            captured.append((meta, body))

        with self.assertRaises(ConnectorDisabledError):
            XRecentSearchAdapter(environ={}, capture_sink=sink).discover(
                QuerySpec("agent"), Limits()
            )
        result = ArxivAtomAdapter(capture_sink=sink).discover(
            QuerySpec("agent"), Limits(max_requests=0)
        )
        self.assertEqual(result.receipt.request_count, 0)
        self.assertEqual(captured, [])

    def test_contacts_are_explicitly_disabled(self) -> None:
        adapter = ContactsDisabledAdapter()
        self.assertFalse(adapter.enabled)
        with self.assertRaises(ConnectorDisabledError) as captured:
            adapter.discover(QuerySpec("person"), Limits())
        self.assertEqual(captured.exception.code, "CONTACTS_DISABLED")


if __name__ == "__main__":
    unittest.main()
