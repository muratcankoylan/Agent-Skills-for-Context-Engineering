from __future__ import annotations

import json
import os
import sqlite3
import stat
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from researcher.scripts import research_pipeline as pipeline
from researcher.scripts.local_rehearsal import RehearsalError
from researcher.scripts.local_scheduler import LocalScheduler, SchedulerStoreUnsafe
from researcher.scripts.research_evidence import ResearchEvidenceError
from researcher.scripts.source_connectors import ArxivAtomAdapter, ConnectorError
from researcher.scripts.tests.test_source_connectors import (
    ScriptedTransport,
    atom_entry,
    atom_feed,
    resolver_for,
    response,
)


class ResearchPipelineTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.directory = self.root / "run"
        self.body = atom_feed(
            atom_entry(
                "Research fixture",
                "https://arxiv.org/abs/2501.00001",
                stable_id="http://arxiv.org/abs/2501.00001",
            )
        )
        self.transport = ScriptedTransport(response(self.body, "application/atom+xml"))

    def factory(self, name, sink, **offline):
        self.assertEqual(name, "arxiv")
        search = offline.pop("arxiv_search", None) or {"scope": "all", "match": "terms"}
        if offline:
            return ArxivAtomAdapter(
                capture_sink=sink,
                search_scope=search["scope"],
                search_match=search["match"],
                **offline,
            )
        return ArxivAtomAdapter(
            transport=self.transport,
            resolver=resolver_for("export.arxiv.org"),
            capture_sink=sink,
        )

    def run_once(self, **overrides):
        arguments = dict(
            runtime_dir=self.directory,
            query="context engineering",
            selected_skills=["context-fundamentals"],
            adapter_factory=self.factory,
        )
        arguments.update(overrides)
        return pipeline.run_pipeline(**arguments)

    def read_only(self):
        return pipeline.read_verified_observation(
            self.directory, require_live=False, read_only=True
        )

    def storage_snapshot(self):
        records = {}
        for path in [self.directory, *sorted(self.directory.rglob("*"))]:
            info = path.lstat()
            records[str(path.relative_to(self.directory))] = (
                info.st_mode,
                info.st_ino,
                info.st_nlink,
                info.st_size,
                info.st_mtime_ns,
                info.st_ctime_ns,
                path.read_bytes()
                if stat.S_ISREG(info.st_mode)
                else os.readlink(path)
                if stat.S_ISLNK(info.st_mode)
                else None,
            )
        return records

    def test_read_only_verification_has_no_initialization_or_writes(self):
        expected = self.run_once()
        before = self.storage_snapshot()
        actual_open, actual_connect = os.open, sqlite3.connect

        def open_read_only(path, flags, *args, **kwargs):
            self.assertFalse(
                flags & (os.O_CREAT | os.O_TRUNC | os.O_RDWR | os.O_WRONLY)
            )
            return actual_open(path, flags, *args, **kwargs)

        def connect_read_only(database, *args, **kwargs):
            self.assertTrue(
                database == ":memory:"
                or (
                    str(database).endswith("?mode=ro&immutable=1")
                    and kwargs.get("uri") is True
                )
            )
            return actual_connect(database, *args, **kwargs)

        with (
            patch("os.open", side_effect=open_read_only),
            patch("os.mkdir", side_effect=AssertionError("no initialization")),
            patch("os.chmod", side_effect=AssertionError("no mode repair")),
            patch("os.fsync", side_effect=AssertionError("no write flush")),
            patch("sqlite3.connect", side_effect=connect_read_only),
        ):
            self.assertEqual(self.read_only(), expected)
        self.assertEqual(before, self.storage_snapshot())
        self.assertEqual(len(self.transport.requests), 1)
        self.assertFalse(list(self.directory.glob("scheduler.sqlite3-*")))

    def test_read_only_missing_storage_is_rejected_without_repair(self):
        self.run_once()
        for relative in (
            ".run.lock",
            "scheduler.sqlite3",
            "evidence/.lock",
            "evidence/bodies",
            "evidence/observations",
            "evidence",
        ):
            path = self.directory / relative
            saved = self.root / "saved-component"
            path.rename(saved)
            try:
                before = self.storage_snapshot()
                with (
                    self.subTest(relative=relative),
                    self.assertRaises((ValueError, RuntimeError, OSError)),
                ):
                    self.read_only()
                self.assertFalse(path.exists())
                self.assertEqual(before, self.storage_snapshot())
            finally:
                saved.rename(path)

    def test_read_only_missing_blob_is_not_retrieved(self):
        result = self.run_once()
        digest = result["sources"][0]["captures"][0]["body_sha256"].split(":")[1]
        path = self.directory / "evidence/bodies" / digest
        path.rename(self.root / "saved-body")
        before = self.storage_snapshot()
        with self.assertRaises(ResearchEvidenceError):
            self.read_only()
        self.assertEqual(before, self.storage_snapshot())
        self.assertEqual(len(self.transport.requests), 1)

    def test_read_only_rejects_aliases_and_fifo_locks_without_changes(self):
        self.run_once()
        for relative in (
            ".run.lock",
            "scheduler.sqlite3",
            "evidence/.lock",
            "evidence/bodies",
        ):
            path = self.directory / relative
            saved = self.root / "saved-component"
            path.rename(saved)
            path.symlink_to(saved)
            try:
                before = self.storage_snapshot()
                with (
                    self.subTest(relative=relative),
                    self.assertRaises((ValueError, RuntimeError, OSError)),
                ):
                    self.read_only()
                self.assertEqual(before, self.storage_snapshot())
            finally:
                path.unlink()
                saved.rename(path)
        for relative in (".run.lock", "evidence/.lock"):
            path = self.directory / relative
            saved = self.root / "saved-lock"
            path.rename(saved)
            os.mkfifo(path, mode=0o600)
            try:
                before = self.storage_snapshot()
                with (
                    self.subTest(fifo=relative),
                    self.assertRaises((ValueError, RuntimeError, OSError)),
                ):
                    self.read_only()
                self.assertEqual(before, self.storage_snapshot())
            finally:
                path.unlink()
                saved.rename(path)

    def test_read_only_does_not_chmod_unsafe_storage(self):
        self.run_once()
        for relative in ("scheduler.sqlite3", ".run.lock", "evidence/.lock"):
            path = self.directory / relative
            path.chmod(0o644)
            try:
                before = self.storage_snapshot()
                with (
                    self.subTest(relative=relative),
                    self.assertRaises((ValueError, RuntimeError, OSError)),
                ):
                    self.read_only()
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o644)
                self.assertEqual(before, self.storage_snapshot())
            finally:
                path.chmod(0o600)

    def test_read_only_never_ignores_or_checkpoints_live_wal(self):
        self.run_once()
        connection = sqlite3.connect(self.directory / "scheduler.sqlite3")
        try:
            connection.execute("PRAGMA wal_autocheckpoint=0")
            connection.execute("UPDATE work_orders SET state='failed'")
            connection.commit()
            self.assertGreater(
                (self.directory / "scheduler.sqlite3-wal").stat().st_size, 0
            )
            before = self.storage_snapshot()
            with self.assertRaisesRegex(SchedulerStoreUnsafe, "checkpointed"):
                self.read_only()
            self.assertEqual(before, self.storage_snapshot())
        finally:
            connection.close()

    def test_read_only_rejects_pending_journal_and_preserves_empty_sidecars(self):
        expected = self.run_once()
        path = self.directory / "scheduler.sqlite3-journal"
        path.write_bytes(b"unreconciled")
        path.chmod(0o600)
        before = self.storage_snapshot()
        with self.assertRaisesRegex(SchedulerStoreUnsafe, "checkpointed"):
            self.read_only()
        self.assertEqual(before, self.storage_snapshot())
        path.unlink()
        for suffix in ("-wal", "-shm"):
            (self.directory / ("scheduler.sqlite3" + suffix)).touch(mode=0o600)
        before = self.storage_snapshot()
        self.assertEqual(self.read_only(), expected)
        self.assertEqual(before, self.storage_snapshot())

    def test_read_only_scheduler_refuses_writes_and_detects_later_change(self):
        self.run_once()
        path = self.directory / "scheduler.sqlite3"
        scheduler = LocalScheduler(path, read_only=True)
        before = self.storage_snapshot()
        with self.assertRaisesRegex(SchedulerStoreUnsafe, "cannot mutate"):
            scheduler.tick(observed_at="2026-09-07T00:00:00Z")
        self.assertEqual(before, self.storage_snapshot())
        os.utime(path, ns=(path.stat().st_atime_ns, path.stat().st_mtime_ns + 1000))
        with self.assertRaisesRegex(SchedulerStoreUnsafe, "changed"):
            scheduler.list_work_orders()

    def test_read_only_evidence_store_refuses_capture(self):
        result = self.run_once()
        store = pipeline.LocalResearchEvidenceStore(
            self.directory / "evidence", read_only=True
        )
        observation, body = store.read(result["sources"][0]["captures"][0])
        before = self.storage_snapshot()
        with self.assertRaises(ResearchEvidenceError) as error:
            store.capture(observation, body)
        self.assertEqual(error.exception.code, "EVIDENCE_READ_ONLY")
        self.assertEqual(before, self.storage_snapshot())

    def test_read_only_storage_size_identity_and_hardlink_checks(self):
        self.run_once()
        path = self.directory / "scheduler.sqlite3"
        with patch(
            "researcher.scripts.local_scheduler.MAX_READ_ONLY_DATABASE_BYTES", 100
        ):
            with self.assertRaisesRegex(SchedulerStoreUnsafe, "bounds"):
                self.read_only()
        alias = self.root / "hardlink"
        os.link(path, alias)
        before = self.storage_snapshot()
        try:
            with self.assertRaises(SchedulerStoreUnsafe):
                self.read_only()
            self.assertEqual(before, self.storage_snapshot())
        finally:
            alias.unlink()
        connection = sqlite3.connect(path)
        connection.execute("PRAGMA application_id=1")
        connection.close()
        before = self.storage_snapshot()
        with self.assertRaisesRegex(SchedulerStoreUnsafe, "identity"):
            self.read_only()
        self.assertEqual(before, self.storage_snapshot())

    def test_actual_adapter_capture_context_report_and_zero_models(self):
        result = self.run_once()
        self.assertEqual(result["status"], "awaiting_researcher")
        self.assertEqual(result["model_calls"], 0)
        self.assertFalse(result["production_ready"])
        source = result["sources"][0]
        self.assertEqual(len(source["captures"]), 1)
        self.assertTrue(source["capture_complete"])
        store = pipeline.LocalResearchEvidenceStore(self.directory / "evidence")
        self.assertEqual(store.read_body(source["captures"][0]), self.body)
        self.assertGreater(result["context_bytes"], 1000)
        self.assertTrue((self.directory / "research-handoff.json").is_file())
        self.assertEqual(self.run_once(), result)
        self.assertEqual(len(self.transport.requests), 1)

    def test_empty_response_is_partial_not_a_scientific_success(self):
        self.transport = ScriptedTransport(
            response(atom_feed(), "application/atom+xml")
        )
        result = self.run_once()
        self.assertEqual(result["status"], "partial")
        self.assertIn("No matching leads", result["blockers"][-1])

    def test_rate_limit_persists_evidence_without_sleep_or_retry(self):
        self.transport = ScriptedTransport(
            response(
                b"limited", "text/plain", status=429, headers=(("retry-after", "60"),)
            )
        )
        result = self.run_once()
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["sources"][0]["retry_after_seconds"], 60)
        self.assertEqual(len(result["sources"][0]["captures"]), 1)
        self.assertEqual(self.run_once(), result)
        self.assertEqual(len(self.transport.requests), 1)

    def test_malformed_source_is_captured_and_failed(self):
        self.transport = ScriptedTransport(response(b"not XML", "application/atom+xml"))
        result = self.run_once()
        self.assertEqual(result["sources"][0]["status"], "failed")
        self.assertEqual(len(result["sources"][0]["captures"]), 1)
        self.assertEqual(result["status"], "partial")

    def test_late_callback_cannot_mutate_returned_or_persisted_record(self):
        result = self.run_once()
        captured = result["sources"][0]["captures"][0]
        observation = pipeline.LocalResearchEvidenceStore(
            self.directory / "evidence"
        ).read_observation(captured)
        release = threading.Event()
        done = threading.Event()

        class DelayedAdapter:
            def __init__(adapter, sink):
                adapter.sink = sink

            def discover(adapter, query, limits):
                def late():
                    release.wait(5)
                    try:
                        adapter.sink(observation, self.body)
                    finally:
                        done.set()

                threading.Thread(target=late, daemon=True).start()
                raise ConnectorError("TIME_LIMIT", "private details must not escape")

        failed = self.run_once(
            runtime_dir=self.root / "delayed",
            adapter_factory=lambda name, sink: DelayedAdapter(sink),
        )
        persisted = (self.root / "delayed/observation.json").read_bytes()
        release.set()
        self.assertTrue(done.wait(5))
        self.assertEqual(failed["sources"][0]["captures"], [])
        self.assertEqual(
            (self.root / "delayed/observation.json").read_bytes(), persisted
        )
        self.assertNotIn("private details", persisted.decode())

    def test_inputs_are_checked_before_network(self):
        for overrides in (
            {"query": ""},
            {"selected_skills": ["absent-skill"]},
            {"max_context_bytes": 1},
            {"sources": ["x"]},
            {"live": True},
            {"sources": ["arxiv", "arxiv"]},
        ):
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                self.run_once(**overrides)
        self.assertEqual(self.transport.requests, [])

    def test_live_network_requires_explicit_opt_in(self):
        with self.assertRaisesRegex(pipeline.ResearchPipelineError, "live-public"):
            self.run_once(adapter_factory=None)

    def test_access_time_change_is_not_a_content_mutation(self):
        path = self.root / "access-time.txt"
        path.write_bytes(b"unchanged")
        os.utime(path, ns=(1_000_000_000, path.stat().st_mtime_ns))
        self.assertEqual(pipeline._read_bytes(path), b"unchanged")

    def test_context_tamper_is_rejected_not_overwritten(self):
        self.run_once()
        path = self.directory / "context-pack.json"
        path.write_bytes(path.read_bytes() + b" ")
        before = path.read_bytes()
        with self.assertRaisesRegex(
            pipeline.ResearchPipelineError, "context checkpoint"
        ):
            self.run_once()
        self.assertEqual(path.read_bytes(), before)

    def test_missing_context_on_completed_run_is_rejected(self):
        self.run_once()
        (self.directory / "context-pack.json").unlink()
        with self.assertRaisesRegex(pipeline.ResearchPipelineError, "lost its context"):
            self.run_once()

    def test_modified_source_and_report_are_rejected(self):
        self.run_once()
        for name in (
            "source-arxiv.json",
            "report.md",
            "research-handoff.json",
            "observation.json",
        ):
            path = self.directory / name
            original = path.read_bytes()
            path.write_bytes(original + b" ")
            with (
                self.subTest(name=name),
                self.assertRaises((pipeline.ResearchPipelineError, RehearsalError)),
            ):
                self.run_once()
            path.write_bytes(original)

    def test_captured_body_corruption_is_rejected(self):
        result = self.run_once()
        digest = result["sources"][0]["captures"][0]["body_sha256"].split(":")[1]
        candidates = list((self.directory / "evidence/bodies").rglob(digest))
        self.assertEqual(len(candidates), 1)
        candidates[0].write_bytes(b"corrupt")
        with self.assertRaises(ResearchEvidenceError):
            self.run_once()

    def test_symlink_report_is_rejected(self):
        self.run_once()
        report = self.directory / "report.md"
        target = self.root / "report-copy.md"
        target.write_bytes(report.read_bytes())
        report.unlink()
        report.symlink_to(target)
        with self.assertRaises((OSError, pipeline.ResearchPipelineError)):
            self.run_once()

    def test_changed_query_cannot_resume(self):
        self.run_once()
        with self.assertRaisesRegex(pipeline.ResearchPipelineError, "inputs changed"):
            self.run_once(query="different question")

    def test_interrupted_source_is_not_automatically_retried(self):
        with patch.object(self, "factory", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.run_once()
        with self.assertRaisesRegex(pipeline.ResearchPipelineError, "unknown outcome"):
            self.run_once()
        self.assertEqual(self.transport.requests, [])

    def test_artifact_commit_gap_resumes_without_network(self):
        with patch.object(LocalScheduler, "complete", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.run_once()
        result = self.run_once()
        self.assertEqual(result["status"], "awaiting_researcher")
        self.assertEqual(len(self.transport.requests), 1)
        self.assertEqual(
            LocalScheduler(self.directory / "scheduler.sqlite3")
            .list_work_orders()[0]
            .attempt,
            2,
        )

    def test_authority_change_in_commit_gap_is_rejected(self):
        with patch.object(LocalScheduler, "complete", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.run_once()
        path = self.directory / "observation.json"
        record = json.loads(path.read_bytes())
        record["model_calls"] = False
        pipeline._write(path, record)
        with self.assertRaisesRegex(
            pipeline.ResearchPipelineError, "authority mismatch"
        ):
            self.run_once()

    def test_fixtures_cannot_publish_as_live(self):
        self.run_once()
        with self.assertRaisesRegex(pipeline.ResearchPipelineError, "fixture"):
            pipeline.publish_view([self.directory], self.root / "view.json")

    def test_publication_is_read_only_and_summary_contains_no_evidence(self):
        # Test-only transport injection through the production adapter constructor.
        with patch.object(pipeline, "_adapter", side_effect=self.factory):
            result = self.run_once(adapter_factory=None, live=True)
        with patch.object(
            pipeline, "run_pipeline", side_effect=AssertionError("view executed work")
        ):
            view = pipeline.publish_view([self.directory], self.root / "view.json")
        self.assertEqual(view["runs"][0]["run_id"], result["run_id"])
        self.assertEqual(view["runs"][0]["capture_count"], 1)
        self.assertNotIn("Research fixture", json.dumps(view))
        self.assertNotIn(str(self.directory), json.dumps(view))
        with self.assertRaisesRegex(pipeline.ResearchPipelineError, "repeat"):
            pipeline.publish_view(
                [self.directory, self.directory], self.root / "view.json"
            )

    def test_publication_cannot_resume_incomplete_live_run(self):
        with patch.object(pipeline, "_adapter", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.run_once(adapter_factory=None, live=True)
        with patch.object(
            pipeline, "run_pipeline", side_effect=AssertionError("executed")
        ):
            with self.assertRaisesRegex(pipeline.ResearchPipelineError, "not complete"):
                pipeline.publish_view([self.directory], self.root / "view.json")


if __name__ == "__main__":
    unittest.main()
