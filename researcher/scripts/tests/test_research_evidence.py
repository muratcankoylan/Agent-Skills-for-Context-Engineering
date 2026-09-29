from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from researcher.scripts.research_evidence import (
    CapturedEvidence,
    LocalResearchEvidenceStore,
    ResearchEvidenceError,
)
from researcher.scripts.source_connectors import ResponseObservation


def observation(
    body: bytes = b"exact\x00response\xff", **changes: object
) -> ResponseObservation:
    record = ResponseObservation(
        request_url="https://export.arxiv.org/api/query",
        query_redacted=True,
        resolved_ips=("93.184.216.34",),
        connected_ip="93.184.216.34",
        status_code=200,
        media_type="application/atom+xml",
        response_bytes=len(body),
        response_sha256="sha256:" + hashlib.sha256(body).hexdigest(),
        elapsed_ms=7,
        safe_headers=(("content-type", "application/atom+xml"),),
    )
    return replace(record, **changes)


class ResearchEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.root = self.base / "captures"
        self.store = LocalResearchEvidenceStore(self.root)

    def test_exact_bytes_and_metadata_round_trip_from_json_record(self) -> None:
        body = b"exact\x00response\xff"
        captured = self.store.capture(observation(body), body)
        record = json.loads(json.dumps(captured.as_record()))
        restored = CapturedEvidence.from_record(record)
        self.assertEqual(captured, restored)
        self.assertEqual(self.store.read_body(record), body)
        self.assertEqual(self.store.read_observation(record), observation(body))
        self.assertTrue(record["observation_only"])
        self.assertFalse(record["authoritative"])
        self.assertNotIn(str(self.root), json.dumps(record))
        self.assertEqual(self.root.stat().st_mode & 0o777, 0o700)
        for child in (self.root / "bodies").iterdir():
            self.assertEqual(child.stat().st_mode & 0o777, 0o600)

    def test_dedup_preserves_existing_inode_and_distinct_response_metadata(
        self,
    ) -> None:
        body = b"shared body"
        first = self.store.capture(observation(body), body)
        path = self.root / "bodies" / first.body_sha256[7:]
        inode = path.stat().st_ino
        second = self.store.capture(observation(body), body)
        later = self.store.capture(observation(body, elapsed_ms=10), body)
        self.assertEqual(first, second)
        self.assertEqual(path.stat().st_ino, inode)
        self.assertEqual(later.body_sha256, first.body_sha256)
        self.assertNotEqual(later.metadata_sha256, first.metadata_sha256)
        self.assertEqual(len(list((self.root / "bodies").iterdir())), 1)
        self.assertEqual(len(list((self.root / "observations").iterdir())), 2)

    def test_concurrent_writers_publish_one_verified_body(self) -> None:
        body = b"concurrent" * 1000
        with ThreadPoolExecutor(max_workers=8) as executor:
            records = list(
                executor.map(
                    lambda _: self.store.capture(observation(body), body), range(24)
                )
            )
        self.assertEqual(len(set(records)), 1)
        self.assertEqual(self.store.read_body(records[0]), body)
        self.assertEqual(len(list((self.root / "bodies").iterdir())), 1)

    def test_partial_error_response_is_stored_with_explicit_metadata(self) -> None:
        body = b"<partial"
        captured = self.store.capture(
            observation(body, status_code=503, truncated=True), body
        )
        meta, restored = self.store.read(captured)
        self.assertTrue(meta.truncated)
        self.assertEqual(meta.status_code, 503)
        self.assertEqual(restored, body)
        self.assertFalse(captured.authoritative)

    def test_wrong_body_digest_or_size_fails_before_publication(self) -> None:
        body = b"content"
        for meta in (
            observation(body, response_sha256="sha256:" + "0" * 64),
            observation(body, response_bytes=0),
        ):
            with self.subTest(meta=meta):
                with self.assertRaises(ResearchEvidenceError):
                    self.store.capture(meta, body)
        self.assertEqual(list((self.root / "bodies").iterdir()), [])

    def test_metadata_rejects_raw_query_credentials_unknown_headers_and_unbounded_values(
        self,
    ) -> None:
        body = b"content"
        invalid = (
            {"request_url": "https://example.com/query?private=CANARY"},
            {"request_url": "https://user:CANARY@example.com/query"},
            {"safe_headers": (("authorization", "Bearer CANARY"),)},
            {"safe_headers": (("etag", "a" * 4097),)},
            {"resolved_ips": ("127.0.0.1",), "connected_ip": "127.0.0.1"},
            {"elapsed_ms": True},
            {"query_redacted": 1},
            {"truncated": "false"},
        )
        for changes in invalid:
            with self.subTest(changes=list(changes)):
                with self.assertRaises(ResearchEvidenceError) as captured:
                    self.store.capture(observation(body, **changes), body)
                self.assertNotIn("CANARY", str(captured.exception))
        self.assertEqual(list((self.root / "bodies").iterdir()), [])

    def test_reference_cannot_supply_locator_or_authority_or_traversal(self) -> None:
        body = b"content"
        captured = self.store.capture(observation(body), body)
        for update in (
            {"body_sha256": "../../outside"},
            {"metadata_sha256": "/tmp/arbitrary"},
            {"authoritative": True},
            {"observation_only": False},
            {"locator": "outside"},
            {"size_bytes": True},
        ):
            record = captured.as_record() | update
            with self.subTest(update=update):
                with self.assertRaises(ResearchEvidenceError):
                    self.store.read_body(record)

    def test_corruption_is_detected_and_dedup_does_not_overwrite(self) -> None:
        body = b"content"
        captured = self.store.capture(observation(body), body)
        path = self.root / "bodies" / captured.body_sha256[7:]
        path.write_bytes(b"corrupt")
        for action in (
            lambda: self.store.read_body(captured),
            lambda: self.store.capture(observation(body), body),
        ):
            with self.assertRaises(ResearchEvidenceError):
                action()
        self.assertEqual(path.read_bytes(), b"corrupt")

    def test_metadata_digest_and_body_binding_are_verified(self) -> None:
        first = self.store.capture(observation(b"one"), b"one")
        second = self.store.capture(observation(b"two"), b"two")
        forged = replace(first, metadata_sha256=second.metadata_sha256)
        with self.assertRaises(ResearchEvidenceError):
            self.store.read(forged)
        path = self.root / "observations" / first.metadata_sha256[7:]
        path.write_bytes(b"{}")
        with self.assertRaises(ResearchEvidenceError):
            self.store.read(first)

    def test_root_parent_and_namespace_symlinks_are_rejected(self) -> None:
        outside = self.base / "outside"
        outside.mkdir(mode=0o700)
        link = self.base / "linked"
        link.symlink_to(outside, target_is_directory=True)
        for path in (link, link / "child", self.base / ".." / "escape"):
            with self.subTest(path=path):
                with self.assertRaises(ResearchEvidenceError):
                    LocalResearchEvidenceStore(path)
        bodies = self.root / "bodies"
        bodies.rmdir()
        bodies.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ResearchEvidenceError):
            self.store.capture(observation(b"data"), b"data")
        self.assertEqual(list(outside.iterdir()), [])

    def test_blob_symlink_hardlink_and_fifo_are_rejected(self) -> None:
        body = b"content"
        captured = self.store.capture(observation(body), body)
        path = self.root / "bodies" / captured.body_sha256[7:]
        outside = self.base / "outside"
        outside.write_bytes(body)
        outside.chmod(0o600)
        for kind in ("symlink", "hardlink", "fifo"):
            with self.subTest(kind=kind):
                path.unlink()
                if kind == "symlink":
                    path.symlink_to(outside)
                elif kind == "hardlink":
                    os.link(outside, path)
                else:
                    os.mkfifo(path, mode=0o600)
                with self.assertRaises(ResearchEvidenceError):
                    self.store.read(captured)

    def test_store_root_replacement_is_detected(self) -> None:
        self.root.rename(self.base / "original")
        self.root.mkdir(mode=0o700)
        with self.assertRaises(ResearchEvidenceError):
            self.store.capture(observation(b"data"), b"data")

    def test_lock_replacement_and_public_root_permissions_are_rejected(self) -> None:
        (self.root / ".lock").rename(self.root / ".old-lock")
        (self.root / ".lock").touch(mode=0o600)
        with self.assertRaises(ResearchEvidenceError):
            self.store.capture(observation(b"data"), b"data")
        public = self.base / "public"
        public.mkdir(mode=0o755)
        public.chmod(0o755)
        with self.assertRaises(ResearchEvidenceError):
            LocalResearchEvidenceStore(public)

    def test_aggregate_metadata_limit_and_body_ceiling_precede_writes(self) -> None:
        huge = b"x" * 1_500_001
        with self.assertRaises(ResearchEvidenceError):
            self.store.capture(observation(huge), huge)
        body = b"small"
        with self.assertRaises(ResearchEvidenceError) as captured:
            self.store.capture(
                observation(
                    body, safe_headers=tuple(("etag", "a" * 4_096) for _ in range(10))
                ),
                body,
            )
        self.assertEqual(captured.exception.code, "EVIDENCE_METADATA_LIMIT")
        self.assertEqual(list((self.root / "bodies").iterdir()), [])

    def test_connector_sink_round_trip_uses_private_capture_contract(self) -> None:
        from researcher.scripts.source_connectors import (
            ArxivAtomAdapter,
            Limits,
            QuerySpec,
        )
        from researcher.scripts.tests.test_source_connectors import (
            ScriptedTransport,
            atom_entry,
            atom_feed,
            resolver_for,
            response,
        )

        body = atom_feed(atom_entry("Paper", "http://arxiv.org/abs/2609.12345v1"))
        records = []

        def sink(meta: ResponseObservation, data: bytes) -> None:
            records.append(self.store.capture(meta, data))

        page = ArxivAtomAdapter(
            transport=ScriptedTransport(response(body, "application/atom+xml")),
            resolver=resolver_for("export.arxiv.org"),
            capture_sink=sink,
        ).discover(QuerySpec("context research"), Limits())
        self.assertEqual(len(page.items), 1)
        self.assertEqual(self.store.read_body(records[0].as_record()), body)
        self.assertEqual(
            self.store.read_observation(records[0]), page.receipt.observations[0]
        )

    def test_failed_atomic_publish_exposes_no_partial_target(self) -> None:
        with patch(
            "researcher.scripts.research_evidence.os.link",
            side_effect=OSError("simulated disk failure"),
        ):
            with self.assertRaises(ResearchEvidenceError):
                self.store.capture(observation(b"data"), b"data")
        self.assertEqual(list((self.root / "bodies").iterdir()), [])
        self.assertEqual(list((self.root / "observations").iterdir()), [])


if __name__ == "__main__":
    unittest.main()
