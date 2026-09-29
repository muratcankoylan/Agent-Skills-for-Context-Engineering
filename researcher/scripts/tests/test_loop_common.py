from __future__ import annotations

import errno
import json
import math
import multiprocessing
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from researcher.scripts import loop_common


ACQUISITION_ERROR_NUMBERS = (
    errno.EACCES,
    errno.EAGAIN,
    errno.EINTR,
    errno.EIO,
    errno.ENOLCK,
)


def _hold_queue_lock(lock_dir: str, acquired, release) -> None:
    loop_common.LOCK_DIR = Path(lock_dir)
    with loop_common.queue_lock("contention"):
        acquired.set()
        if not release.wait(timeout=5):
            raise RuntimeError("test did not release the held lock")


def _wait_for_queue_lock(lock_dir: str, started, acquired) -> None:
    loop_common.LOCK_DIR = Path(lock_dir)
    started.set()
    with loop_common.queue_lock("contention"):
        acquired.set()


class LoopCommonLockingTests(unittest.TestCase):
    def test_strict_json_parser_rejects_duplicate_keys_at_nested_depth(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicate JSON key: value"):
            loop_common.strict_json_loads(
                '{"outer":{"value":1,"value":2}}'
            )

    def test_strict_json_parser_rejects_every_nonfinite_constant(self) -> None:
        for constant in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(constant=constant), self.assertRaisesRegex(
                loop_common.NonFiniteJSONNumberError,
                rf"non-finite JSON number is not permitted: {constant}",
            ):
                loop_common.strict_json_loads(f'{{"value":{constant}}}')

    def test_supervisor_rejects_hardlinked_run_state(self) -> None:
        reference = (
            Path(loop_common.__file__).resolve().parents[1]
            / "runs"
            / "20260515-035228-executable-autonomous-research-frameworks"
            / "run-state.json"
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            run_dir = root / "20260515-035228-executable-autonomous-research-frameworks"
            run_dir.mkdir()
            outside = root / "outside-state.json"
            outside.write_bytes(reference.read_bytes())
            os.link(outside, run_dir / "run-state.json")
            self.assertIsNone(loop_common.load_run_state(run_dir))

    def test_supervisor_rejects_future_dated_run_state(self) -> None:
        reference = (
            Path(loop_common.__file__).resolve().parents[1]
            / "runs"
            / "20260515-035228-executable-autonomous-research-frameworks"
            / "run-state.json"
        )
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = (
                Path(temporary).resolve()
                / "20260515-035228-executable-autonomous-research-frameworks"
            )
            run_dir.mkdir()
            state = json.loads(reference.read_text(encoding="utf-8"))
            state["created_at"] = "2099-01-01T00:00:00+00:00"
            state["updated_at"] = "2099-01-01T00:00:00+00:00"
            for entry in state["state_history"]:
                entry["timestamp"] = "2099-01-01T00:00:00+00:00"
            (run_dir / "run-state.json").write_text(
                json.dumps(state) + "\n",
                encoding="utf-8",
            )
            self.assertIsNone(loop_common.load_run_state(run_dir))

    def test_runtime_initializer_rejects_a_symlinked_queue_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            outside = root / "outside"
            outside.mkdir()
            queue = root / "queue"
            queue.symlink_to(outside, target_is_directory=True)
            with patch.object(loop_common, "QUEUE_DIR", queue), self.assertRaisesRegex(
                ValueError, "runtime queue directory is unsafe"
            ):
                loop_common.initialize_runtime_queue_ledgers()
            self.assertEqual(list(outside.iterdir()), [])

    def test_runtime_initializer_creates_complete_empty_set_idempotently(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            queue = Path(temporary).resolve() / "queue"
            queue.mkdir()
            with patch.object(loop_common, "QUEUE_DIR", queue):
                first = loop_common.initialize_runtime_queue_ledgers()
                second = loop_common.initialize_runtime_queue_ledgers()
            self.assertEqual({path.name for path in first}, set(loop_common.RUNTIME_QUEUE_LEDGERS))
            self.assertEqual(second, [])
            self.assertTrue(all((queue / name).read_bytes() == b"" for name in loop_common.RUNTIME_QUEUE_LEDGERS))

    def test_runtime_ledgers_reject_hardlinked_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            queue = root / "queue"
            queue.mkdir()
            outside = root / "outside.jsonl"
            outside.touch()
            os.link(outside, queue / "inbox.jsonl")
            for name in set(loop_common.RUNTIME_QUEUE_LEDGERS) - {"inbox.jsonl"}:
                (queue / name).touch()
            with patch.object(loop_common, "QUEUE_DIR", queue):
                with self.assertRaisesRegex(ValueError, "runtime queue ledger is unsafe"):
                    loop_common.initialize_runtime_queue_ledgers()
                with self.assertRaisesRegex(ValueError, "runtime queue ledger is unsafe"):
                    loop_common.require_runtime_queue_ledgers()

    def test_run_enumeration_rejects_a_symlinked_runs_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            outside = root / "outside"
            outside.mkdir()
            (outside / "run-x").mkdir()
            runs = root / "runs"
            runs.symlink_to(outside, target_is_directory=True)
            with patch.object(loop_common, "RUNS_DIR", runs), self.assertRaisesRegex(
                ValueError, "runtime runs directory is unsafe"
            ):
                loop_common.list_run_dirs()

    def test_queue_lock_fails_before_yield_for_every_acquisition_error(self) -> None:
        for error_number in ACQUISITION_ERROR_NUMBERS:
            with self.subTest(error_number=error_number), tempfile.TemporaryDirectory() as temporary:
                body_entered = False
                error = OSError(error_number, os.strerror(error_number))
                with (
                    patch.object(loop_common, "LOCK_DIR", Path(temporary)),
                    patch.object(loop_common.fcntl, "flock", side_effect=error) as flock,
                    self.assertRaises(OSError) as captured,
                ):
                    with loop_common.queue_lock("inbox"):
                        body_entered = True

                self.assertEqual(captured.exception.errno, error_number)
                self.assertFalse(body_entered)
                flock.assert_called_once()

    def test_append_jsonl_fails_before_write_for_every_acquisition_error(self) -> None:
        for error_number in ACQUISITION_ERROR_NUMBERS:
            with self.subTest(error_number=error_number), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                target = root / "events.jsonl"
                baseline = b'{"prior":true}\n'
                target.write_bytes(baseline)
                error = OSError(error_number, os.strerror(error_number))
                with (
                    patch.object(loop_common, "LOCK_DIR", root / "locks"),
                    patch.object(loop_common.fcntl, "flock", side_effect=error) as flock,
                    patch.object(loop_common.os, "fsync") as fsync,
                    self.assertRaises(OSError) as captured,
                ):
                    loop_common.append_jsonl(target, {"must_not_appear": True})

                self.assertEqual(captured.exception.errno, error_number)
                self.assertEqual(target.read_bytes(), baseline)
                flock.assert_called_once()
                fsync.assert_not_called()

    def test_queue_lock_rejects_symlink_and_hardlink_lock_inodes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            locks = root / "locks"
            locks.mkdir()
            outside = root / "outside.lock"
            outside.touch()
            (locks / "inbox.lock").symlink_to(outside)
            with patch.object(loop_common, "LOCK_DIR", locks), self.assertRaises(OSError):
                with loop_common.queue_lock("inbox"):
                    pass

            (locks / "inbox.lock").unlink()
            os.link(outside, locks / "inbox.lock")
            with patch.object(loop_common, "LOCK_DIR", locks), self.assertRaisesRegex(
                ValueError, "single-link regular file"
            ):
                with loop_common.queue_lock("inbox"):
                    pass

    def test_queue_lock_reports_replaced_path_as_durability_uncertain(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            locks = Path(temporary).resolve() / "locks"
            with patch.object(loop_common, "LOCK_DIR", locks), self.assertRaisesRegex(
                loop_common.DurabilityUncertainError,
                "lock pathname changed",
            ):
                with loop_common.queue_lock("replaced"):
                    lock_path = locks / "replaced.lock"
                    lock_path.unlink()
                    lock_path.touch(mode=0o600)

    def test_append_acquisition_failure_does_not_create_target(self) -> None:
        for error_number in ACQUISITION_ERROR_NUMBERS:
            with self.subTest(error_number=error_number), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                target = root / "events.jsonl"
                error = OSError(error_number, os.strerror(error_number))
                with (
                    patch.object(loop_common, "LOCK_DIR", root / "locks"),
                    patch.object(loop_common.fcntl, "flock", side_effect=error),
                    self.assertRaises(OSError),
                ):
                    loop_common.append_jsonl(target, {"must_not_appear": True})

                self.assertFalse(target.exists())

    def test_append_rejects_final_and_parent_symlinks_without_external_write(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            outside = root / "outside"
            outside.mkdir()
            outside_file = outside / "events.jsonl"
            outside_file.write_text('{"prior":true}\n', encoding="utf-8")
            final_link = root / "events.jsonl"
            final_link.symlink_to(outside_file)
            with (
                patch.object(loop_common, "LOCK_DIR", root / "locks"),
                self.assertRaises(OSError),
            ):
                loop_common.append_jsonl(final_link, {"injected": True})
            self.assertEqual(outside_file.read_text(encoding="utf-8"), '{"prior":true}\n')

            linked_parent = root / "reports"
            linked_parent.symlink_to(outside, target_is_directory=True)
            with (
                patch.object(loop_common, "LOCK_DIR", root / "locks"),
                self.assertRaisesRegex(ValueError, "real directory"),
            ):
                loop_common.append_jsonl(linked_parent / "new.jsonl", {"injected": True})
            self.assertFalse((outside / "new.jsonl").exists())

    def test_append_rejects_fifo_without_blocking(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fifo = root / "events.jsonl"
            os.mkfifo(fifo)
            with (
                patch.object(loop_common, "LOCK_DIR", root / "locks"),
                self.assertRaises(OSError),
            ):
                loop_common.append_jsonl(fifo, {"injected": True})

    def test_jsonl_duplicate_keys_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "ambiguous.jsonl"
            path.write_text('{"status":"good","status":"bad"}\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
                loop_common.read_jsonl(path)

    def test_jsonl_nonfinite_numbers_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "nonfinite.jsonl"
            path.write_text('{"status":"bad","value":NaN}\n', encoding="utf-8")
            with self.assertRaisesRegex(
                loop_common.NonFiniteJSONNumberError,
                "non-finite JSON number is not permitted: NaN",
            ):
                loop_common.read_jsonl(path)

    def test_durable_json_writers_reject_nonfinite_numbers_before_mutation(self) -> None:
        writers = {
            "json": lambda path, value: loop_common.write_json(
                path, {"value": value}
            ),
            "jsonl-replace": lambda path, value: loop_common.write_jsonl(
                path, [{"value": value}]
            ),
            "jsonl-append": lambda path, value: loop_common.append_jsonl(
                path, {"value": value}
            ),
        }
        values = (math.nan, math.inf, -math.inf)
        for writer_name, writer in writers.items():
            for value in values:
                with (
                    self.subTest(writer=writer_name, value=value),
                    tempfile.TemporaryDirectory() as temporary,
                ):
                    root = Path(temporary)
                    target = root / "durable.jsonl"
                    baseline = b'{"prior":true}\n'
                    target.write_bytes(baseline)
                    with (
                        patch.object(loop_common, "LOCK_DIR", root / "locks"),
                        self.assertRaisesRegex(
                            ValueError,
                            "Out of range float values are not JSON compliant",
                        ),
                    ):
                        writer(target, value)
                    self.assertEqual(target.read_bytes(), baseline)
                    self.assertFalse((root / "locks").exists())

    def test_append_fsyncs_before_unlock(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "events.jsonl"
            target.write_text('{"sequence": 0}\n', encoding="utf-8")
            events: list[str] = []

            def record_flock(_file_descriptor: int, operation: int) -> None:
                events.append("lock" if operation == loop_common.fcntl.LOCK_EX else "unlock")

            with (
                patch.object(loop_common, "LOCK_DIR", root / "locks"),
                patch.object(loop_common.fcntl, "flock", side_effect=record_flock),
                patch.object(loop_common.os, "fsync", side_effect=lambda _fd: events.append("fsync")),
            ):
                loop_common.append_jsonl(target, {"sequence": 1})

            self.assertEqual(events, ["lock", "lock", "fsync", "unlock", "unlock"])
            self.assertEqual(
                target.read_text(encoding="utf-8"),
                '{"sequence": 0}\n{"sequence": 1}\n',
            )

    def test_first_append_fsyncs_file_and_parent_before_unlock(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "events.jsonl"
            events: list[str] = []

            def record_flock(_file_descriptor: int, operation: int) -> None:
                events.append("lock" if operation == loop_common.fcntl.LOCK_EX else "unlock")

            with (
                patch.object(loop_common, "LOCK_DIR", root / "locks"),
                patch.object(loop_common.fcntl, "flock", side_effect=record_flock),
                patch.object(loop_common.os, "fsync", side_effect=lambda _fd: events.append("fsync")),
            ):
                loop_common.append_jsonl(target, {"sequence": 1})

            self.assertEqual(events, ["lock", "lock", "fsync", "unlock", "fsync", "unlock"])
            self.assertEqual(target.read_text(encoding="utf-8"), '{"sequence": 1}\n')

    def test_unlock_failure_is_reported_after_successful_body(self) -> None:
        unlock_error = OSError(errno.EIO, os.strerror(errno.EIO))
        with tempfile.TemporaryDirectory() as temporary:
            with (
                patch.object(loop_common, "LOCK_DIR", Path(temporary)),
                patch.object(loop_common.fcntl, "flock", side_effect=[None, unlock_error]),
                self.assertRaises(
                    loop_common.LockReleaseOutcomeUncertainError
                ) as captured,
            ):
                with loop_common.queue_lock("inbox"):
                    pass

        self.assertIs(captured.exception.__cause__, unlock_error)
        self.assertTrue(captured.exception.effects_may_have_committed)

    def test_unlock_failure_does_not_mask_active_body_exception(self) -> None:
        class BodyFailure(RuntimeError):
            pass

        unlock_error = OSError(errno.ENOLCK, os.strerror(errno.ENOLCK))
        with tempfile.TemporaryDirectory() as temporary:
            with (
                patch.object(loop_common, "LOCK_DIR", Path(temporary)),
                patch.object(loop_common.fcntl, "flock", side_effect=[None, unlock_error]),
                self.assertRaises(BodyFailure),
            ):
                with loop_common.queue_lock("inbox"):
                    raise BodyFailure("primary failure")

    def test_append_and_rollback_fsync_failure_is_typed_as_uncertain(self) -> None:
        fsync_error = OSError(errno.EIO, "ledger fsync failed")
        unlock_error = OSError(errno.ENOLCK, "unlock failed")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "events.jsonl"
            target.touch()
            with (
                patch.object(loop_common, "LOCK_DIR", root / "locks"),
                patch.object(loop_common.fcntl, "flock", side_effect=[None, None, unlock_error, unlock_error]),
                patch.object(loop_common.os, "fsync", side_effect=fsync_error),
                self.assertRaises(loop_common.AppendRollbackError) as captured,
            ):
                loop_common.append_jsonl(target, {"operation": "uncertain"})

            visible = target.read_text(encoding="utf-8")

        self.assertIs(captured.exception.__cause__, fsync_error)
        self.assertTrue(captured.exception.effects_may_have_committed)
        self.assertEqual(visible, "")

    def test_post_replace_directory_fsync_failure_is_durability_uncertain(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "state.json"
            target.write_text('{"state":"old"}\n', encoding="utf-8")
            directory_error = OSError(errno.EIO, "directory fsync failed")
            with (
                patch.object(
                    loop_common.os,
                    "fsync",
                    side_effect=[None, directory_error],
                ),
                self.assertRaises(loop_common.DurabilityUncertainError) as captured,
            ):
                loop_common.write_json(target, {"state": "new"})

            self.assertIs(captured.exception.__cause__, directory_error)
            self.assertEqual(
                target.read_text(encoding="utf-8"),
                '{\n  "state": "new"\n}\n',
            )

    def test_atomic_write_rejects_symlinked_parent_without_external_write(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            outside = root / "outside"
            outside.mkdir()
            reports = root / "reports"
            reports.symlink_to(outside, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "real directory"):
                loop_common.write_text(reports / "status.md", "escaped\n")
            self.assertFalse((outside / "status.md").exists())

    @unittest.skipUnless(
        "fork" in multiprocessing.get_all_start_methods(),
        "requires POSIX fork multiprocessing",
    )
    def test_queue_lock_serializes_processes(self) -> None:
        context = multiprocessing.get_context("fork")
        with tempfile.TemporaryDirectory() as temporary:
            holder_acquired = context.Event()
            release_holder = context.Event()
            waiter_started = context.Event()
            waiter_acquired = context.Event()
            holder = context.Process(
                target=_hold_queue_lock,
                args=(temporary, holder_acquired, release_holder),
            )
            waiter = context.Process(
                target=_wait_for_queue_lock,
                args=(temporary, waiter_started, waiter_acquired),
            )

            holder.start()
            waiter_started_ok = False
            try:
                self.assertTrue(holder_acquired.wait(timeout=5))
                waiter.start()
                waiter_started_ok = waiter_started.wait(timeout=5)
                self.assertTrue(waiter_started_ok)
                self.assertFalse(waiter_acquired.wait(timeout=0.2))
                release_holder.set()
                self.assertTrue(waiter_acquired.wait(timeout=5))
            finally:
                release_holder.set()
                holder.join(timeout=5)
                if waiter_started_ok:
                    waiter.join(timeout=5)
                for process in (holder, waiter):
                    if process.is_alive():
                        process.terminate()
                        process.join(timeout=5)

            self.assertEqual(holder.exitcode, 0)
            self.assertEqual(waiter.exitcode, 0)


if __name__ == "__main__":
    unittest.main()
