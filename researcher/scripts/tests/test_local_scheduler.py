from __future__ import annotations

import math
import os
import sqlite3
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from researcher.scripts.local_scheduler import (
    InvalidSchedule,
    InvalidTime,
    LocalScheduler,
    SchedulerStoreUnsafe,
    WorkOrderConflict,
    main,
)


class LocalSchedulerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.database = self.root / "runtime" / "scheduler.sqlite3"
        self.scheduler = LocalScheduler(self.database)

    def register(self, **overrides):
        values = {
            "schedule_id": "source-discovery",
            "action": "discover.sources",
            "interval_seconds": 300,
            "next_due_at": "2026-08-25T12:00:00Z",
            "payload": {"connector": "manual", "query_digest": "sha256:" + "a" * 64},
            "observed_at": "2026-08-25T11:59:00Z",
        }
        values.update(overrides)
        return self.scheduler.register(**values)

    def test_register_is_idempotent_and_updates_are_versioned(self) -> None:
        first = self.register()
        repeated = self.register()
        self.assertEqual(first, repeated)
        changed = self.register(interval_seconds=600)
        self.assertEqual(changed.version, 2)
        self.assertEqual(changed.interval_seconds, 600)

    def test_due_tick_is_deterministic_idempotent_and_bounded(self) -> None:
        self.register(interval_seconds=60)
        first = self.scheduler.tick(observed_at="2026-08-25T12:02:00Z", max_orders=2)
        self.assertEqual(len(first), 2)
        self.assertEqual(
            [order.due_at for order in first],
            ["2026-08-25T12:00:00Z", "2026-08-25T12:01:00Z"],
        )
        second = self.scheduler.tick(observed_at="2026-08-25T12:02:00Z", max_orders=2)
        self.assertEqual([order.due_at for order in second], ["2026-08-25T12:02:00Z"])
        self.assertEqual(self.scheduler.tick(observed_at="2026-08-25T12:02:00Z"), ())
        self.assertEqual(
            len(
                set(order.work_order_id for order in self.scheduler.list_work_orders())
            ),
            3,
        )

    def test_zero_tick_capacity_has_no_side_effect(self) -> None:
        before = self.register()
        self.assertEqual(
            self.scheduler.tick(observed_at="2026-08-25T12:00:00Z", max_orders=0), ()
        )
        self.assertEqual(
            self.scheduler.get_schedule(before.schedule_id).next_due_at,
            before.next_due_at,
        )
        self.assertEqual(self.scheduler.list_work_orders(), ())

    def test_rewound_slot_cannot_silently_accept_a_changed_payload(self) -> None:
        self.register()
        self.scheduler.tick(observed_at="2026-08-25T12:00:00Z")
        self.register(payload={"connector": "different-source"})
        with self.assertRaises(WorkOrderConflict):
            self.scheduler.tick(observed_at="2026-08-25T12:00:00Z")
        self.assertEqual(len(self.scheduler.list_work_orders()), 1)

    def test_duplicate_slot_recovery_is_bounded_by_scanned_slots(self) -> None:
        self.register(interval_seconds=1, next_due_at="2026-08-25T00:00:00Z")
        first = self.scheduler.tick(observed_at="2026-08-25T00:00:00Z", max_orders=1)
        self.assertEqual(len(first), 1)
        connection = sqlite3.connect(self.database)
        try:
            connection.execute(
                "UPDATE schedules SET next_due_at = '2026-08-25T00:00:00Z'"
            )
            connection.commit()
        finally:
            connection.close()
        recovered = self.scheduler.tick(
            observed_at="2026-08-25T12:00:00Z", max_orders=1
        )
        self.assertEqual(recovered, ())
        self.assertEqual(
            self.scheduler.get_schedule("source-discovery").next_due_at,
            "2026-08-25T00:00:01Z",
        )

    def test_claim_reclaim_and_stale_fence(self) -> None:
        self.register()
        [order] = self.scheduler.tick(observed_at="2026-08-25T12:00:00Z")
        first = self.scheduler.claim(
            worker_id="worker-one",
            observed_at="2026-08-25T12:00:00Z",
            lease_seconds=10,
        )
        self.assertIsNotNone(first)
        assert first is not None and first.fence is not None
        self.assertIsNone(
            self.scheduler.claim(
                worker_id="worker-two",
                observed_at="2026-08-25T12:00:09Z",
                lease_seconds=10,
            )
        )
        reclaimed = self.scheduler.claim(
            worker_id="worker-two",
            observed_at="2026-08-25T12:00:10Z",
            lease_seconds=10,
        )
        assert reclaimed is not None and reclaimed.fence is not None
        self.assertEqual(reclaimed.work_order_id, order.work_order_id)
        self.assertEqual(reclaimed.attempt, 2)
        self.assertNotEqual(reclaimed.fence, first.fence)
        with self.assertRaises(WorkOrderConflict):
            self.scheduler.complete(
                order.work_order_id,
                fence=first.fence,
                result={"ok": True},
                observed_at="2026-08-25T12:00:11Z",
            )
        completed = self.scheduler.complete(
            order.work_order_id,
            fence=reclaimed.fence,
            result={"ok": True},
            observed_at="2026-08-25T12:00:11Z",
        )
        self.assertEqual(completed.state, "succeeded")

    def test_retry_preserves_identity_and_consumes_an_attempt(self) -> None:
        self.register()
        [order] = self.scheduler.tick(observed_at="2026-08-25T12:00:00Z")
        claimed = self.scheduler.claim(
            worker_id="worker-one",
            observed_at="2026-08-25T12:00:00Z",
            lease_seconds=10,
        )
        assert claimed is not None and claimed.fence is not None
        retriable = self.scheduler.fail(
            order.work_order_id,
            fence=claimed.fence,
            result={"classification": "transient"},
            retry=True,
            observed_at="2026-08-25T12:00:01Z",
        )
        self.assertEqual(retriable.state, "queued")
        self.assertEqual(
            self.scheduler.fail(
                order.work_order_id,
                fence=claimed.fence,
                result={"classification": "transient"},
                retry=True,
                observed_at="2026-08-25T12:00:01Z",
            ),
            retriable,
        )
        second = self.scheduler.claim(
            worker_id="worker-one",
            observed_at="2026-08-25T12:00:02Z",
            lease_seconds=10,
        )
        assert second is not None
        self.assertEqual(second.work_order_id, order.work_order_id)
        self.assertEqual(second.attempt, 2)

    def test_concurrent_ticks_create_one_work_order_per_slot(self) -> None:
        self.register()
        barrier = threading.Barrier(8)
        results: list[tuple[str, ...]] = []
        lock = threading.Lock()

        def tick() -> None:
            barrier.wait()
            identifiers = tuple(
                item.work_order_id
                for item in LocalScheduler(self.database).tick(
                    observed_at="2026-08-25T12:00:00Z"
                )
            )
            with lock:
                results.append(identifiers)

        threads = [threading.Thread(target=tick) for _ in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=20)
        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual(sum(len(item) for item in results), 1)
        self.assertEqual(len(self.scheduler.list_work_orders()), 1)

    def test_invalid_actions_times_payloads_and_bounds_fail_before_write(self) -> None:
        invalid = [
            {"schedule_id": "../escape"},
            {"action": "network.fetch"},
            {"interval_seconds": True},
            {"interval_seconds": 0},
            {"next_due_at": "not-a-time"},
            {"next_due_at": "2026-08-25T12:00:00"},
            {"payload": {"score": math.nan}},
            {"payload": []},
            {"payload": False},
        ]
        for override in invalid:
            with (
                self.subTest(override=override),
                self.assertRaises((InvalidSchedule, InvalidTime)),
            ):
                self.register(**override)
        connection = sqlite3.connect(self.database)
        try:
            self.assertEqual(
                connection.execute("SELECT count(*) FROM schedules").fetchone()[0], 0
            )
        finally:
            connection.close()

    def test_database_symlink_and_hardlink_are_rejected(self) -> None:
        target = self.root / "target.sqlite3"
        LocalScheduler(target)
        alias = self.root / "alias.sqlite3"
        alias.symlink_to(target)
        with self.assertRaises(SchedulerStoreUnsafe):
            LocalScheduler(alias)
        alias.unlink()
        os.link(target, alias)
        with self.assertRaises(SchedulerStoreUnsafe):
            LocalScheduler(target)

    def test_unknown_database_and_future_version_are_not_adopted(self) -> None:
        for application_id, version in ((42, 1), (1095519604, 999), (0, 0)):
            path = self.root / f"foreign-{application_id}-{version}.sqlite3"
            connection = sqlite3.connect(path)
            connection.execute("CREATE TABLE unrelated(value TEXT)")
            connection.execute(f"PRAGMA application_id = {application_id}")
            connection.execute(f"PRAGMA user_version = {version}")
            connection.commit()
            connection.close()
            original = path.read_bytes()
            with self.subTest(version=version), self.assertRaises(SchedulerStoreUnsafe):
                LocalScheduler(path)
            self.assertEqual(path.read_bytes(), original)

    def test_declared_version_cannot_hide_schema_drift(self) -> None:
        connection = sqlite3.connect(self.database)
        connection.execute("DROP INDEX work_orders_claim")
        connection.commit()
        connection.close()
        with self.assertRaises(SchedulerStoreUnsafe):
            LocalScheduler(self.database)

    def test_ancestor_alias_and_sidecar_alias_are_rejected(self) -> None:
        alias = self.root / "alias-directory"
        alias.symlink_to(self.database.parent, target_is_directory=True)
        with self.assertRaises(SchedulerStoreUnsafe):
            LocalScheduler(alias / "scheduler.sqlite3")
        sidecar = Path(str(self.database) + "-wal")
        self.assertFalse(sidecar.exists())
        sidecar.symlink_to(self.root / "outside")
        with self.assertRaises(SchedulerStoreUnsafe):
            self.scheduler.list_work_orders()

    def test_expired_lease_cannot_complete_before_another_worker_reclaims(self) -> None:
        self.register()
        self.scheduler.tick(observed_at="2026-08-25T12:00:00Z")
        claimed = self.scheduler.claim(
            worker_id="worker", observed_at="2026-08-25T12:00:00Z", lease_seconds=10
        )
        assert claimed is not None
        for timestamp in ("2026-08-25T11:59:59Z", "2026-08-25T12:00:10Z"):
            with (
                self.subTest(timestamp=timestamp),
                self.assertRaises(WorkOrderConflict),
            ):
                self.scheduler.complete(
                    claimed.work_order_id,
                    fence=claimed.fence or "",
                    result={"ok": True},
                    observed_at=timestamp,
                )
        self.assertEqual(
            self.scheduler.get_work_order(claimed.work_order_id).state, "running"
        )

    def test_exhausted_expired_and_queued_attempts_reach_terminal_state(self) -> None:
        for retry in (False, True):
            self.register(schedule_id=f"exhausted-{str(retry).lower()}")
        self.scheduler.tick(observed_at="2026-08-25T12:00:00Z")
        first = self.scheduler.claim(
            worker_id="worker",
            observed_at="2026-08-25T12:00:00Z",
            lease_seconds=10,
            max_attempts=1,
        )
        second = self.scheduler.claim(
            worker_id="worker",
            observed_at="2026-08-25T12:00:00Z",
            lease_seconds=10,
            max_attempts=1,
        )
        assert first is not None and second is not None
        self.scheduler.fail(
            second.work_order_id,
            fence=second.fence or "",
            result={"error": "transient"},
            observed_at="2026-08-25T12:00:01Z",
            retry=True,
        )
        self.assertIsNone(
            self.scheduler.claim(
                worker_id="worker",
                observed_at="2026-08-25T12:00:10Z",
                lease_seconds=10,
                max_attempts=1,
            )
        )
        self.assertTrue(
            all(
                order.state == "failed"
                and order.result == {"error_code": "ATTEMPTS_EXHAUSTED"}
                for order in self.scheduler.list_work_orders()
            )
        )

    def test_future_work_cannot_be_claimed_with_an_earlier_clock(self) -> None:
        self.register()
        self.scheduler.tick(observed_at="2026-08-25T12:00:00Z")
        self.assertIsNone(
            self.scheduler.claim(
                worker_id="worker", observed_at="2026-08-25T11:59:59Z", lease_seconds=10
            )
        )

    def test_parallel_claims_give_one_worker_the_lease(self) -> None:
        self.register()
        self.scheduler.tick(observed_at="2026-08-25T12:00:00Z")
        barrier = threading.Barrier(8)

        def claim(index):
            scheduler = LocalScheduler(self.database)
            barrier.wait()
            return scheduler.claim(
                worker_id=f"worker-{index}",
                observed_at="2026-08-25T12:00:00Z",
                lease_seconds=10,
            )

        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(claim, range(8)))
        self.assertEqual(sum(item is not None for item in results), 1)

    def test_tick_rollback_preserves_cursor_when_insert_fails(self) -> None:
        schedule = self.register()
        connection = sqlite3.connect(self.database)
        connection.execute(
            "CREATE TRIGGER injected_failure BEFORE INSERT ON work_orders BEGIN SELECT RAISE(ABORT, 'injected'); END"
        )
        connection.commit()
        connection.close()
        with self.assertRaises(sqlite3.IntegrityError):
            self.scheduler.tick(observed_at="2026-08-25T12:00:00Z")
        self.assertEqual(self.scheduler.get_schedule(schedule.schedule_id), schedule)
        self.assertEqual(self.scheduler.list_work_orders(), ())

    def test_cli_reports_non_authoritative_effect_free_tick(self) -> None:
        args = [
            "--database",
            str(self.root / "cli.sqlite3"),
            "register",
            "--id",
            "daily-health",
            "--action",
            "health.snapshot",
            "--interval-seconds",
            "86400",
            "--next-due-at",
            "2026-08-25T12:00:00Z",
            "--observed-at",
            "2026-08-25T11:00:00Z",
        ]
        self.assertEqual(main(args), 0)
        self.assertEqual(
            main(
                [
                    "--database",
                    str(self.root / "cli.sqlite3"),
                    "tick",
                    "--observed-at",
                    "2026-08-25T12:00:00Z",
                ]
            ),
            0,
        )


if __name__ == "__main__":
    unittest.main()
