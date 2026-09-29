from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any
from unittest.mock import patch

from researcher.scripts.event_store import (
    BackupDestinationExists,
    EventIdentityConflict,
    EventStore,
    EventStoreError,
    IdempotencyConflict,
    InvalidCursor,
    JournalCorrupt,
    MigrationAhead,
    MigrationDrift,
    RestoreInvalid,
    SubjectVersionConflict,
)
from researcher.scripts.run_projector import ResearchRunProjector
from researcher.scripts.schema_contract import canonical_digest, canonicalize, sha256_bytes
from researcher.scripts.validate_event_journal import build_report


ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "researcher" / "schemas" / "fixtures" / "records" / "organization-event.json"
MIGRATION_MANIFEST = ROOT / "researcher" / "event_journal" / "migrations" / "manifest.json"


def event_id(serial: int) -> str:
    return f"evt_018f3e40-7b80-7a21-8000-{serial:012x}"


def initial_event(*, run_id: str = "20260810-120000-journal-contract", serial: int = 4) -> dict[str, Any]:
    event = json.loads(FIXTURE.read_text(encoding="utf-8"))
    event["id"] = event_id(serial)
    event["correlation_event_id"] = event["id"]
    event["subject"]["id"] = run_id
    event["payload"]["run_id"] = run_id
    event["payload"]["evidence"] = f"researcher/runs/{run_id}"
    event["payload"]["initialization"]["editable_surfaces"] = [
        f"researcher/runs/{run_id}/sources/",
        f"researcher/runs/{run_id}/proposals/",
    ]
    event["idempotency"]["key_digest"] = sha256_bytes(f"{run_id}:0".encode())
    event["payload_digest"] = canonical_digest(event["payload"])
    return event


def transition_event(
    prior: dict[str, Any],
    *,
    version: int,
    to_state: str,
    serial: int,
    from_state: str | None = None,
) -> dict[str, Any]:
    event = deepcopy(prior)
    run_id = str(prior["subject"]["id"])
    prior_state = str(prior["payload"]["to_state"])
    event["id"] = event_id(serial)
    event["subject"]["version"] = version
    event["event_type"] = f"research_run.{to_state}"
    event["occurred_at"] = f"2026-08-10T12:{version - 1:02}:00Z"
    event["causation_event_id"] = prior["id"]
    event["correlation_event_id"] = prior["correlation_event_id"]
    event["idempotency"]["key_digest"] = sha256_bytes(f"{run_id}:{version - 1}".encode())
    reason = "run closed" if to_state == "closed" else f"run {to_state}"
    event["payload"].update(
        {
            "history_index": version - 1,
            "from_state": from_state if from_state is not None else prior_state,
            "to_state": to_state,
            "reason": reason,
            "evidence": f"researcher/runs/{run_id}/reports/{to_state}.json",
            "initialization": None,
            "closure": (
                {
                    "status": "reference-only",
                    "reason": reason,
                    "closed_at": event["occurred_at"],
                }
                if to_state == "closed"
                else None
            ),
        }
    )
    event["payload_digest"] = canonical_digest(event["payload"])
    return event


class EventStoreTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.database = self.root / "journal.sqlite3"
        self.store = EventStore(self.database, clock=lambda: "2026-08-11T12:00:00Z")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def assert_code(self, code: str, callback) -> EventStoreError:
        with self.assertRaises(EventStoreError) as captured:
            callback()
        self.assertEqual(captured.exception.code, code)
        return captured.exception


class MigrationAndConfigurationTests(EventStoreTestCase):
    def test_fresh_database_uses_pinned_wal_full_strict_contract(self) -> None:
        report = self.store.verify_integrity()
        self.assertEqual(report.entry_count, 0)
        self.assertEqual(self.database.stat().st_mode & 0o777, 0o600)
        connection = sqlite3.connect(self.database)
        try:
            self.assertEqual(connection.execute("PRAGMA journal_mode").fetchone()[0], "wal")
            self.assertEqual(connection.execute("PRAGMA synchronous").fetchone()[0], 2)
            self.assertEqual(connection.execute("PRAGMA application_id").fetchone()[0], 1095388748)
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 1)
            strict = connection.execute(
                "SELECT strict FROM pragma_table_list WHERE name = 'journal_entries'"
            ).fetchone()[0]
            self.assertEqual(strict, 1)
        finally:
            connection.close()

    def test_migration_digest_drift_and_ahead_database_fail_closed(self) -> None:
        document = json.loads(MIGRATION_MANIFEST.read_text(encoding="utf-8"))
        document["migrations"][0]["digest"] = "sha256:" + "0" * 64
        manifest = self.root / "manifest.json"
        manifest.write_text(json.dumps(document), encoding="utf-8")
        self.assert_code(
            "MIGRATION_DRIFT",
            lambda: EventStore(self.root / "drift.sqlite3", migration_manifest=manifest),
        )

        connection = sqlite3.connect(self.database)
        connection.execute("PRAGMA user_version = 2")
        connection.close()
        self.assert_code("MIGRATION_AHEAD", lambda: EventStore(self.database))

    def test_migrations_execute_only_the_verified_in_memory_statements(self) -> None:
        migration_path = ROOT / "researcher" / "event_journal" / "migrations" / "0001-initial.sql"
        original_read_text = Path.read_text

        def swapped_read_text(path: Path, *args, **kwargs) -> str:
            if path.resolve() == migration_path.resolve():
                return original_read_text(path, *args, **kwargs) + "\nCREATE TABLE injected(value TEXT);\n"
            return original_read_text(path, *args, **kwargs)

        database = self.root / "migration-snapshot.sqlite3"
        with patch.object(Path, "read_text", swapped_read_text):
            store = EventStore(database, registry=self.store.registry)
        self.assertEqual(store.verify_integrity().entry_count, 0)
        connection = sqlite3.connect(database)
        try:
            self.assertIsNone(
                connection.execute(
                    "SELECT name FROM sqlite_schema WHERE name = 'injected'"
                ).fetchone()
            )
        finally:
            connection.close()

    def test_initialization_rejects_dangling_symlinks_and_maps_races(self) -> None:
        dangling_target = self.root / "dangling-target.sqlite3"
        dangling_link = self.root / "dangling-link.sqlite3"
        dangling_link.symlink_to(dangling_target)
        self.assert_code("JOURNAL_CORRUPT", lambda: EventStore(dangling_link))
        self.assertFalse(dangling_target.exists())

        invalid = self.root / "not-sqlite.sqlite3"
        invalid.write_bytes(b"not a sqlite database")
        self.assert_code("JOURNAL_CORRUPT", lambda: EventStore(invalid))

        racing = self.root / "racing.sqlite3"
        barrier = threading.Barrier(4)
        results: list[str] = []
        lock = threading.Lock()

        def initialize() -> None:
            barrier.wait()
            try:
                EventStore(racing, busy_timeout_ms=1)
                result = "ok"
            except EventStoreError as exc:
                result = exc.code
            except Exception as exc:  # pragma: no cover - this is the regression assertion.
                result = exc.__class__.__name__
            with lock:
                results.append(result)

        threads = [threading.Thread(target=initialize) for _ in range(4)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=15)
        self.assertTrue(all(result in {"ok", "JOURNAL_BUSY"} for result in results), results)
        self.assertIn("ok", results)
        self.assertEqual(EventStore(racing).verify_integrity().entry_count, 0)


class AppendContractTests(EventStoreTestCase):
    def test_append_duplicate_identity_and_idempotency_precedence(self) -> None:
        first = initial_event()
        first_receipt = self.store.append(first, 0)
        second = transition_event(first, version=2, to_state="retrieved", serial=5)
        self.store.append(second, 1)

        duplicate = self.store.append(first, 0)
        self.assertTrue(duplicate.duplicate)
        self.assertEqual(duplicate.sequence, first_receipt.sequence)
        self.assertEqual(duplicate.entry_hash, first_receipt.entry_hash)

        reused_id = deepcopy(first)
        reused_id["idempotency"]["key_digest"] = sha256_bytes(b"different-key")
        self.assert_code("EVENT_ID_CONFLICT", lambda: self.store.append(reused_id, 0))

        reused_key = initial_event(run_id="20260810-120001-second-run", serial=6)
        reused_key["idempotency"] = deepcopy(first["idempotency"])
        self.assert_code("IDEMPOTENCY_CONFLICT", lambda: self.store.append(reused_key, 0))

    def test_duplicate_retry_validates_the_matched_historical_receipt(self) -> None:
        first = initial_event()
        second = initial_event(run_id="20260810-120001-second-run", serial=6)
        self.store.append(first, 0)
        self.store.append(second, 0)
        connection = sqlite3.connect(self.database)
        trigger_sql = connection.execute(
            "SELECT sql FROM sqlite_schema WHERE name = 'journal_entries_immutable_update'"
        ).fetchone()[0]
        connection.execute("DROP TRIGGER journal_entries_immutable_update")
        connection.execute(
            "UPDATE journal_entries SET entry_hash = ? WHERE sequence = 1",
            ("sha256:" + "0" * 64,),
        )
        connection.execute(trigger_sql)
        connection.commit()
        connection.close()
        self.assert_code("JOURNAL_CORRUPT", lambda: self.store.append(first, 0))

    def test_subject_version_conflicts_and_invalid_inputs_write_nothing(self) -> None:
        first = initial_event()
        self.store.append(first, 0)
        second = transition_event(first, version=2, to_state="retrieved", serial=5)
        self.assert_code("SUBJECT_VERSION_CONFLICT", lambda: self.store.append(second, 0))
        self.assert_code("EVENT_STORE_ERROR", lambda: self.store.append(second, True))

        oversized = initial_event(run_id="20260810-120001-oversized-run", serial=6)
        oversized["payload"]["initialization"]["locked_surfaces"] = [
            f"surface-{index:04}-" + "x" * 480 for index in range(140)
        ]
        oversized["payload_digest"] = canonical_digest(oversized["payload"])
        self.assertGreater(len(canonicalize(oversized)), 65_536)
        self.assert_code("EVENT_STORE_ERROR", lambda: self.store.append(oversized, 0))
        self.assertEqual(self.store.verify_integrity().entry_count, 1)

    def test_subject_correlation_and_causation_must_continue_exactly(self) -> None:
        first = initial_event()
        self.store.append(first, 0)
        wrong_cause = transition_event(first, version=2, to_state="retrieved", serial=5)
        wrong_cause["causation_event_id"] = event_id(90)
        self.assert_code("EVENT_CAUSATION_CONFLICT", lambda: self.store.append(wrong_cause, 1))

        wrong_correlation = transition_event(first, version=2, to_state="retrieved", serial=6)
        wrong_correlation["correlation_event_id"] = event_id(91)
        wrong_correlation["idempotency"]["key_digest"] = sha256_bytes(b"wrong-correlation")
        self.assert_code(
            "EVENT_CAUSATION_CONFLICT",
            lambda: self.store.append(wrong_correlation, 1),
        )
        self.assertEqual(self.store.verify_integrity().entry_count, 1)

    def test_concurrent_same_subject_writers_yield_one_commit(self) -> None:
        first = initial_event()
        self.store.append(first, 0)
        left = transition_event(first, version=2, to_state="retrieved", serial=5)
        right = transition_event(first, version=2, to_state="evaluated", serial=6)
        right["idempotency"]["key_digest"] = sha256_bytes(b"competing-writer")
        barrier = threading.Barrier(2)
        results: list[str] = []
        lock = threading.Lock()

        def writer(event: dict[str, Any]) -> None:
            local = EventStore(self.database, clock=lambda: "2026-08-11T12:00:01Z")
            barrier.wait()
            try:
                local.append(event, 1)
                result = "committed"
            except EventStoreError as exc:
                result = exc.code
            with lock:
                results.append(result)

        threads = [threading.Thread(target=writer, args=(event,)) for event in (left, right)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=15)
        self.assertEqual(sorted(results), ["SUBJECT_VERSION_CONFLICT", "committed"])
        self.assertEqual(self.store.verify_integrity().entry_count, 2)

    def test_transaction_rollback_and_after_commit_retry(self) -> None:
        class FailBeforeCommit(EventStore):
            def _before_commit(self, connection, receipt) -> None:
                raise RuntimeError("injected before commit")

        failing = FailBeforeCommit(self.database, clock=lambda: "2026-08-11T12:00:00Z")
        with self.assertRaisesRegex(RuntimeError, "injected"):
            failing.append(initial_event(), 0)
        self.assertEqual(self.store.verify_integrity().entry_count, 0)

        class FailAfterCommit(EventStore):
            def _after_commit(self, receipt) -> None:
                raise RuntimeError("injected after commit")

        committed = FailAfterCommit(self.database, clock=lambda: "2026-08-11T12:00:00Z")
        with self.assertRaisesRegex(RuntimeError, "after commit"):
            committed.append(initial_event(), 0)
        retry = self.store.append(initial_event(), 0)
        self.assertTrue(retry.duplicate)
        self.assertEqual(self.store.verify_integrity().entry_count, 1)

    def test_process_exit_before_commit_leaves_no_partial_event(self) -> None:
        script = f"""
import json, os
from pathlib import Path
from researcher.scripts.event_store import EventStore
class Killed(EventStore):
    def _before_commit(self, connection, receipt):
        os._exit(17)
store = Killed(Path({str(self.database)!r}), clock=lambda: '2026-08-11T12:00:00Z')
event = json.loads(Path({str(FIXTURE)!r}).read_text())
store.append(event, 0)
"""
        completed = subprocess.run([sys.executable, "-c", script], cwd=ROOT, check=False)
        self.assertEqual(completed.returncode, 17)
        self.assertEqual(self.store.verify_integrity().entry_count, 0)

    def test_append_detaches_caller_owned_nested_values_before_validation(self) -> None:
        snapshot_taken = threading.Event()
        continue_append = threading.Event()

        class PausedStore(EventStore):
            def _after_event_snapshot(self) -> None:
                snapshot_taken.set()
                if not continue_append.wait(timeout=10):
                    raise RuntimeError("test append snapshot wait timed out")

        store = PausedStore(self.database, clock=lambda: "2026-08-11T12:00:00Z")
        event = initial_event()
        original_subject = event["subject"]["id"]
        result: list[object] = []

        def append() -> None:
            try:
                result.append(store.append(event, 0))
            except Exception as exc:  # pragma: no cover - asserted below.
                result.append(exc)

        thread = threading.Thread(target=append)
        thread.start()
        self.assertTrue(snapshot_taken.wait(timeout=10))
        event["subject"]["id"] = "20260810-120000-mutated-caller"
        event["idempotency"]["scope"] = "mutated_scope"
        continue_append.set()
        thread.join(timeout=15)
        self.assertEqual(len(result), 1)
        self.assertFalse(isinstance(result[0], Exception), result)
        receipt = result[0]
        self.assertEqual(receipt.subject_id, original_subject)
        stored = self.store.read().entries[0].event
        self.assertEqual(stored["subject"]["id"], original_subject)
        self.assertEqual(self.store.verify_integrity().entry_count, 1)

    def test_append_uses_bounded_tail_validation_not_full_journal_replay(self) -> None:
        first = initial_event()
        self.store.append(first, 0)

        class NoFullScanOnAppend(EventStore):
            def __init__(self, *args, **kwargs):
                self.allow_full_scan = True
                super().__init__(*args, **kwargs)
                self.allow_full_scan = False

            def _verify_integrity_connection(self, connection):
                if self.allow_full_scan:
                    return super()._verify_integrity_connection(connection)
                raise AssertionError("append invoked a full journal scan")

        store = NoFullScanOnAppend(
            self.database,
            clock=lambda: "2026-08-11T12:00:01Z",
            initialize=False,
        )
        second = transition_event(first, version=2, to_state="retrieved", serial=5)
        receipt = store.append(second, 1)
        self.assertEqual(receipt.sequence, 2)
        self.assertEqual(self.store.verify_integrity().entry_count, 2)


class ReadAndIntegrityTests(EventStoreTestCase):
    def test_filtered_pagination_advances_by_globally_scanned_sequence(self) -> None:
        first = initial_event()
        second = initial_event(run_id="20260810-120001-second-run", serial=6)
        self.store.append(first, 0)
        self.store.append(second, 0)
        page = self.store.read(
            scan_limit=1,
            filters={"subject_id": second["subject"]["id"]},
        )
        self.assertEqual(page.entries, ())
        self.assertEqual(page.next_after_sequence, 1)
        self.assertTrue(page.has_more)
        page = self.store.read(
            after_sequence=page.next_after_sequence,
            scan_limit=1,
            filters={"subject_id": second["subject"]["id"]},
        )
        self.assertEqual([item.event["id"] for item in page.entries], [second["id"]])
        self.assertFalse(page.has_more)
        self.assert_code("INVALID_CURSOR", lambda: self.store.read(after_sequence=3))
        self.assert_code("INVALID_CURSOR", lambda: self.store.read(scan_limit=1001))

    def test_immutability_triggers_and_global_corruption_halt_reads_and_appends(self) -> None:
        first = initial_event()
        self.store.append(first, 0)
        connection = sqlite3.connect(self.database)
        try:
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute("UPDATE journal_entries SET event_type = 'changed' WHERE sequence = 1")
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute("DELETE FROM journal_entries WHERE sequence = 1")
        finally:
            connection.close()

        connection = sqlite3.connect(self.database)
        connection.execute("DROP TRIGGER journal_entries_immutable_update")
        connection.execute("UPDATE journal_entries SET event_json = ? WHERE sequence = 1", (b"{}",))
        connection.execute(
            """
            CREATE TRIGGER journal_entries_immutable_update
            BEFORE UPDATE ON journal_entries
            BEGIN SELECT RAISE(ABORT, 'JOURNAL_ENTRY_IMMUTABLE'); END
            """
        )
        connection.commit()
        connection.close()
        self.assert_code("JOURNAL_CORRUPT", self.store.verify_integrity)
        next_event = transition_event(first, version=2, to_state="retrieved", serial=5)
        self.assert_code("JOURNAL_CORRUPT", lambda: self.store.append(next_event, 1))
        self.assert_code("JOURNAL_CORRUPT", self.store.read)

    def test_control_and_subject_index_corruption_are_detected(self) -> None:
        first = initial_event()
        self.store.append(first, 0)
        connection = sqlite3.connect(self.database)
        connection.execute("UPDATE subject_versions SET version = 2")
        connection.commit()
        connection.close()
        self.assert_code("JOURNAL_CORRUPT", self.store.verify_integrity)

        other_database = self.root / "control.sqlite3"
        other = EventStore(other_database, clock=lambda: "2026-08-11T12:00:00Z")
        other.append(first, 0)
        connection = sqlite3.connect(other_database)
        connection.execute("UPDATE journal_control SET last_entry_hash = ?", ("sha256:" + "0" * 64,))
        connection.commit()
        connection.close()
        self.assert_code("JOURNAL_CORRUPT", other.verify_integrity)

    def test_read_verification_uses_one_snapshot_across_concurrent_append(self) -> None:
        first = initial_event()
        second = initial_event(run_id="20260810-120001-second-run", serial=6)
        self.store.append(first, 0)
        rows_scanned = threading.Event()
        continue_read = threading.Event()

        class PausedReader(EventStore):
            def __init__(self, *args, **kwargs):
                self.pause_reads = False
                super().__init__(*args, **kwargs)
                self.pause_reads = True

            def _after_integrity_rows_scanned(self, connection, row_count) -> None:
                if not self.pause_reads:
                    return
                rows_scanned.set()
                if not continue_read.wait(timeout=10):
                    raise RuntimeError("test read snapshot wait timed out")

        reader = PausedReader(self.database)
        result: list[object] = []

        def read() -> None:
            try:
                result.append(reader.read())
            except Exception as exc:  # pragma: no cover - asserted below.
                result.append(exc)

        thread = threading.Thread(target=read)
        thread.start()
        self.assertTrue(rows_scanned.wait(timeout=10))
        self.store.append(second, 0)
        continue_read.set()
        thread.join(timeout=15)
        self.assertEqual(len(result), 1)
        self.assertFalse(isinstance(result[0], Exception), result)
        page = result[0]
        self.assertEqual(page.high_water_sequence, 1)
        self.assertEqual(page.next_after_sequence, 1)
        self.assertEqual(len(page.entries), 1)
        self.assertEqual(self.store.verify_integrity().entry_count, 2)

    def test_exact_schema_fingerprint_rejects_unexpected_triggers_before_append(self) -> None:
        connection = sqlite3.connect(self.database)
        connection.execute(
            """
            CREATE TRIGGER unexpected_journal_trigger
            AFTER INSERT ON journal_entries
            BEGIN
                UPDATE journal_control SET integrity_state = 'operator_halt' WHERE singleton = 1;
            END
            """
        )
        connection.commit()
        connection.close()
        self.assert_code("JOURNAL_CORRUPT", lambda: self.store.append(initial_event(), 0))
        connection = sqlite3.connect(self.database)
        try:
            self.assertEqual(
                connection.execute("SELECT count(*) FROM journal_entries").fetchone()[0],
                0,
            )
            self.assertEqual(
                connection.execute(
                    "SELECT integrity_state FROM journal_control WHERE singleton = 1"
                ).fetchone()[0],
                "healthy",
            )
        finally:
            connection.close()


class ProjectionTests(EventStoreTestCase):
    def _assert_projection_path_denied(self, callback, expected) -> None:
        def files() -> dict[str, object]:
            result: dict[str, object] = {}
            for path in self.root.rglob("*"):
                name = str(path.relative_to(self.root))
                if path.is_symlink():
                    result[name] = ("link", os.readlink(path))
                elif path.is_file():
                    result[name] = ("file", path.stat().st_mode, path.read_bytes())
                else:
                    result[name] = ("directory", path.stat().st_mode)
            return result

        before = files()
        source_bytes = self.database.read_bytes()
        self.assert_code("PROJECTION_CORRUPT", callback)
        self.assertEqual(files(), before, "denial modified or created fixture files")
        self.assertEqual(self.database.read_bytes(), source_bytes)
        self.assertEqual(self.store.verify_integrity(), expected)

    def test_projection_paths_cannot_overlap_journal_or_reserved_sidecars(self) -> None:
        self.store.append(initial_event(), 0)
        expected = self.store.verify_integrity()
        for suffix in ("", "-wal", "-shm", "-journal", ".operator-halt"):
            with self.subTest(suffix=suffix):
                destination = Path(f"{self.database}{suffix}")
                self._assert_projection_path_denied(
                    lambda: ResearchRunProjector(self.store, path=destination).rebuild(),
                    expected,
                )

    def test_projection_normalized_and_symlink_ancestor_aliases_are_denied(self) -> None:
        self.store.append(initial_event(), 0)
        expected = self.store.verify_integrity()
        nested = self.root / "nested"
        nested.mkdir()
        alias = self.root / "ancestor-alias"
        alias.symlink_to(self.root, target_is_directory=True)
        for destination in (
            nested / ".." / self.database.name,
            self.root / "missing-parent" / ".." / self.database.name,
            alias / self.database.name,
            alias / f"{self.database.name}-wal",
            alias / f"{self.database.name}.operator-halt",
        ):
            with self.subTest(destination=destination):
                self._assert_projection_path_denied(
                    lambda: ResearchRunProjector(self.store, path=destination).rebuild(),
                    expected,
                )

    def test_projection_existing_hardlink_aliases_are_denied(self) -> None:
        self.store.append(initial_event(), 0)
        expected = self.store.verify_integrity()
        for index, suffix in enumerate(("", "-wal", "-shm", "-journal", ".operator-halt")):
            with self.subTest(suffix=suffix):
                protected = Path(f"{self.database}{suffix}")
                if suffix:
                    protected.write_bytes(b"")
                    protected.chmod(0o600)
                alias = self.root / f"hardlink-{index}.sqlite3"
                os.link(protected, alias)
                self._assert_projection_path_denied(
                    lambda: ResearchRunProjector(self.store, path=alias).rebuild(),
                    expected,
                )
                alias.unlink()
                if suffix and protected.exists():
                    protected.unlink()

    def test_projection_lock_hardlink_to_journal_is_denied_before_lock_open(self) -> None:
        self.store.append(initial_event(), 0)
        expected = self.store.verify_integrity()
        destination = self.root / "view.sqlite3"
        os.link(self.database, Path(f"{destination}.lock"))
        self._assert_projection_path_denied(
            lambda: ResearchRunProjector(self.store, path=destination).rebuild(),
            expected,
        )

    def test_projection_path_reassignment_cannot_bypass_constructor_validation(self) -> None:
        self.store.append(initial_event(), 0)
        expected = self.store.verify_integrity()
        projector = ResearchRunProjector(self.store)
        projector.path = self.database
        self._assert_projection_path_denied(projector.rebuild, expected)
        self._assert_projection_path_denied(projector.snapshot, expected)

    def test_projection_alias_created_after_construction_is_denied(self) -> None:
        self.store.append(initial_event(), 0)
        expected = self.store.verify_integrity()
        projector = ResearchRunProjector(self.store)
        os.link(self.database, projector.path)
        self._assert_projection_path_denied(projector.rebuild, expected)
        self._assert_projection_path_denied(projector.snapshot, expected)

    def test_projection_checks_the_current_source_path_before_rebuild(self) -> None:
        projector = ResearchRunProjector(self.store)
        source = EventStore(projector.path, clock=lambda: "2026-08-11T12:00:00Z")
        source.append(initial_event(), 0)
        expected = source.verify_integrity()
        self.store.path = source.path
        self._assert_projection_path_denied(projector.rebuild, expected)

    def test_projection_path_changes_during_rebuild_cannot_retarget_publication(self) -> None:
        self.store.append(initial_event(), 0)
        expected = self.store.verify_integrity()

        class RetargetDuringRead(ResearchRunProjector):
            def _expected_snapshot(inner, to_sequence):
                result = super()._expected_snapshot(to_sequence)
                inner.path = self.database
                return result

        class RetargetDuringPublication(ResearchRunProjector):
            def _before_commit(inner, connection, snapshot) -> None:
                inner.path = self.database

        for projector_class in (RetargetDuringRead, RetargetDuringPublication):
            with self.subTest(projector_class=projector_class.__name__):
                projector = projector_class(self.store)
                # This operation starts with a valid output, so its lock is legitimate.
                # Pre-create it to assert that a late denial leaves no other artifacts.
                lock = Path(f"{projector.path}.lock")
                lock.write_bytes(b"")
                lock.chmod(0o600)
                self._assert_projection_path_denied(projector.rebuild, expected)

    def test_skipped_legacy_shape_rebuilds_deterministically(self) -> None:
        first = initial_event()
        retrieved = transition_event(first, version=2, to_state="retrieved", serial=5)
        closed = transition_event(retrieved, version=3, to_state="closed", serial=6)
        for expected, event in enumerate((first, retrieved, closed)):
            self.store.append(event, expected)
        projector = ResearchRunProjector(self.store)
        first_snapshot = projector.rebuild()
        second_snapshot = projector.rebuild()
        self.assertEqual(first_snapshot.state_digest, second_snapshot.state_digest)
        self.assertEqual(first_snapshot.projections[0].current_state, "closed")
        self.assertEqual(first_snapshot.projections[0].close_status, "reference-only")
        self.assertEqual(projector.snapshot(), second_snapshot)

    def test_inconsistent_subject_is_quarantined_without_stopping_others(self) -> None:
        first = initial_event()
        divergent = transition_event(
            first,
            version=2,
            to_state="evaluated",
            serial=5,
            from_state="retrieved",
        )
        other = initial_event(run_id="20260810-120001-second-run", serial=6)
        self.store.append(first, 0)
        self.store.append(divergent, 1)
        self.store.append(other, 0)
        snapshot = ResearchRunProjector(self.store).rebuild()
        self.assertEqual(len(snapshot.quarantines), 1)
        self.assertEqual(snapshot.quarantines[0].reason_code, "RUN_PROJECTION_STATE_DIVERGED")
        states = {item.subject_id: item.current_state for item in snapshot.projections}
        self.assertEqual(states[first["subject"]["id"]], "initialized")
        self.assertEqual(states[other["subject"]["id"]], "initialized")

    def test_closed_state_is_terminal_for_projection(self) -> None:
        first = initial_event()
        closed = transition_event(first, version=2, to_state="closed", serial=5)
        after_close = transition_event(closed, version=3, to_state="evaluated", serial=6)
        for expected, event in enumerate((first, closed, after_close)):
            self.store.append(event, expected)
        snapshot = ResearchRunProjector(self.store).rebuild()
        self.assertEqual(snapshot.projections[0].current_state, "closed")
        self.assertEqual(snapshot.quarantines[0].reason_code, "RUN_PROJECTION_CLOSED_TERMINAL")

    def test_failed_rebuild_preserves_last_complete_projection(self) -> None:
        first = initial_event()
        self.store.append(first, 0)
        healthy = ResearchRunProjector(self.store)
        prior = healthy.rebuild()
        second = transition_event(first, version=2, to_state="retrieved", serial=5)
        self.store.append(second, 1)

        class FailingProjector(ResearchRunProjector):
            def _before_commit(self, connection, snapshot) -> None:
                raise RuntimeError("injected projection failure")

        with self.assertRaisesRegex(RuntimeError, "injected"):
            FailingProjector(self.store).rebuild()
        self.assertEqual(healthy.snapshot(), prior)
        updated = healthy.rebuild()
        self.assertNotEqual(updated.state_digest, prior.state_digest)

    def test_projection_checkpoint_and_quarantine_provenance_fail_closed(self) -> None:
        first = initial_event()
        divergent = transition_event(
            first,
            version=2,
            to_state="evaluated",
            serial=5,
            from_state="retrieved",
        )
        self.store.append(first, 0)
        self.store.append(divergent, 1)
        projector = ResearchRunProjector(self.store)
        projector.rebuild()

        connection = sqlite3.connect(projector.path)
        connection.execute(
            "UPDATE projection_quarantines SET created_at = '2026-08-11T00:00:00Z'"
        )
        connection.commit()
        connection.close()
        self.assert_code("PROJECTION_CORRUPT", projector.snapshot)

        projector.rebuild()
        connection = sqlite3.connect(projector.path)
        connection.execute("UPDATE projector_control SET projector_version = '9.0.0'")
        connection.commit()
        connection.close()
        self.assert_code("PROJECTION_CORRUPT", projector.snapshot)

    def test_projection_database_corruption_does_not_halt_journal_and_rebuild_recovers(self) -> None:
        first = initial_event()
        self.store.append(first, 0)
        projector = ResearchRunProjector(self.store)
        expected = projector.rebuild()

        connection = sqlite3.connect(projector.path)
        connection.execute("DROP TABLE research_run_projections")
        connection.commit()
        connection.close()

        self.assertEqual(self.store.read().entries[0].event["id"], first["id"])
        self.assertEqual(self.store.verify_integrity().entry_count, 1)
        self.assert_code("PROJECTION_CORRUPT", projector.snapshot)
        self.assertEqual(projector.rebuild(), expected)
        self.assertEqual(projector.snapshot(), expected)

    def test_concurrent_rebuilds_preserve_subject_state_and_tail(self) -> None:
        first = initial_event()
        self.store.append(first, 0)
        older_snapshot_ready = threading.Event()
        allow_older_publish = threading.Event()

        class PausedProjector(ResearchRunProjector):
            def _publish_snapshot(self, snapshot, updated_at) -> None:
                older_snapshot_ready.set()
                if not allow_older_publish.wait(timeout=10):
                    raise RuntimeError("test projection publish wait timed out")
                super()._publish_snapshot(snapshot, updated_at)

        older = PausedProjector(self.store)
        newer = ResearchRunProjector(self.store)
        results: list[object] = []

        def rebuild(projector: ResearchRunProjector) -> None:
            try:
                results.append(projector.rebuild())
            except Exception as exc:  # pragma: no cover - asserted below.
                results.append(exc)

        older_thread = threading.Thread(target=rebuild, args=(older,))
        older_thread.start()
        self.assertTrue(older_snapshot_ready.wait(timeout=10))
        second = transition_event(first, version=2, to_state="retrieved", serial=5)
        self.store.append(second, 1)
        newer_thread = threading.Thread(target=rebuild, args=(newer,))
        newer_thread.start()
        allow_older_publish.set()
        older_thread.join(timeout=15)
        newer_thread.join(timeout=15)
        self.assertEqual(len(results), 2)
        self.assertFalse(any(isinstance(result, Exception) for result in results), results)
        final = newer.snapshot()
        self.assertIsNotNone(final)
        assert final is not None
        self.assertEqual(final.last_sequence, 2)
        self.assertEqual(final.projections[0].current_state, "retrieved")

    def test_concurrent_rebuilds_cannot_publish_an_older_projection_last(self) -> None:
        first = initial_event()
        self.store.append(first, 0)
        snapshot_ready = threading.Event()
        continue_publish = threading.Event()

        class PausedProjector(ResearchRunProjector):
            def _publish_snapshot(self, snapshot, updated_at) -> None:
                snapshot_ready.set()
                if not continue_publish.wait(timeout=10):
                    raise RuntimeError("test projection publish wait timed out")
                super()._publish_snapshot(snapshot, updated_at)

        older = PausedProjector(self.store)
        newer = ResearchRunProjector(self.store)
        results: list[object] = []

        def rebuild(projector: ResearchRunProjector) -> None:
            try:
                results.append(projector.rebuild())
            except Exception as exc:  # pragma: no cover - asserted below.
                results.append(exc)

        old_thread = threading.Thread(target=rebuild, args=(older,))
        old_thread.start()
        self.assertTrue(snapshot_ready.wait(timeout=10))
        second = transition_event(first, version=2, to_state="retrieved", serial=5)
        self.store.append(second, 1)
        new_thread = threading.Thread(target=rebuild, args=(newer,))
        new_thread.start()
        continue_publish.set()
        old_thread.join(timeout=15)
        new_thread.join(timeout=15)
        self.assertEqual(len(results), 2)
        self.assertFalse(any(isinstance(result, Exception) for result in results), results)
        self.assertEqual(newer.snapshot().last_sequence, 2)


class BackupAndRestoreTests(EventStoreTestCase):
    def test_backup_restore_and_post_restore_append(self) -> None:
        first = initial_event()
        self.store.append(first, 0)
        backup_root = self.root / "backups"
        receipt = self.store.backup(backup_root)
        generation = backup_root / receipt.backup_name
        backup = generation / "journal.sqlite3"
        self.assertEqual(
            {path.name for path in generation.iterdir()},
            {"journal.sqlite3", "receipt.json"},
        )
        self.assertEqual(generation.stat().st_mode & 0o777, 0o700)
        self.assertEqual(backup.stat().st_mode & 0o777, 0o600)
        self.assertEqual(receipt.backup_digest, sha256_bytes(backup.read_bytes()))
        restored = self.store.restore_verified(generation, self.root / "restores")
        self.assertEqual(restored.verify_integrity().last_entry_hash, receipt.source_last_entry_hash)
        self.assertEqual(restored.path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(restored.path.parent.stat().st_mode & 0o777, 0o700)
        second = transition_event(first, version=2, to_state="retrieved", serial=5)
        restored.append(second, 1)
        self.assertEqual(restored.verify_integrity().entry_count, 2)
        second_receipt = self.store.backup(backup_root)
        self.assertNotEqual(second_receipt.backup_name, receipt.backup_name)

    def test_corrupt_backup_or_receipt_is_never_published(self) -> None:
        self.store.append(initial_event(), 0)
        backup_root = self.root / "backups"
        receipt = self.store.backup(backup_root)
        generation = backup_root / receipt.backup_name
        backup = generation / "journal.sqlite3"
        backup.write_bytes(backup.read_bytes() + b"tamper")
        destination_root = self.root / "restores"
        self.assert_code(
            "RESTORE_INVALID",
            lambda: self.store.restore_verified(generation, destination_root),
        )
        self.assertFalse(destination_root.exists())

        valid_receipt = self.store.backup(backup_root)
        valid_generation = backup_root / valid_receipt.backup_name
        receipt_path = valid_generation / "receipt.json"
        invalid_receipt = replace(valid_receipt, source_last_sequence=True).to_dict()
        receipt_path.write_bytes(canonicalize(invalid_receipt) + b"\n")
        self.assert_code(
            "RESTORE_INVALID",
            lambda: self.store.restore_verified(valid_generation, self.root / "invalid-restores"),
        )

    def test_backup_publication_is_complete_private_and_closed_world(self) -> None:
        self.store.append(initial_event(), 0)

        invalid_clock = EventStore(self.database, clock=lambda: "not-a-time")
        failed_root = self.root / "failed-backups"
        self.assert_code("EVENT_STORE_ERROR", lambda: invalid_clock.backup(failed_root))
        self.assertEqual(list(failed_root.iterdir()), [])

        old_umask = os.umask(0o022)
        try:
            receipt = self.store.backup(self.root / "private-backups")
        finally:
            os.umask(old_umask)
        generation = self.root / "private-backups" / receipt.backup_name
        self.assertEqual(generation.stat().st_mode & 0o777, 0o700)
        self.assertEqual((generation / "journal.sqlite3").stat().st_mode & 0o777, 0o600)
        self.assertEqual((generation / "receipt.json").stat().st_mode & 0o777, 0o600)

        (generation / "journal.sqlite3-wal").write_bytes(b"stale")
        self.assert_code(
            "RESTORE_INVALID",
            lambda: self.store.restore_verified(generation, self.root / "closed-world-restores"),
        )


class GeneratedEvidenceTests(unittest.TestCase):
    def test_committed_event_journal_report_is_exactly_reproducible(self) -> None:
        path = ROOT / "researcher" / "event_journal" / "generated" / "conformance-report.json"
        self.assertEqual(json.loads(path.read_text(encoding="utf-8")), build_report())


if __name__ == "__main__":
    unittest.main()
