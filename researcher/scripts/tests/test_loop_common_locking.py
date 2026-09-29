"""Process-lock and append durability tests for ``loop_common``."""

from __future__ import annotations

import builtins
import errno
import importlib.util
import json
import multiprocessing
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import ModuleType
from unittest.mock import patch


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import loop_common  # noqa: E402


def load_without_fcntl() -> ModuleType:
    """Load an isolated module while simulating an unavailable Unix backend."""

    real_import = builtins.__import__

    def import_hook(name: str, *args: object, **kwargs: object) -> object:
        if name == "fcntl":
            raise ModuleNotFoundError("simulated missing fcntl", name="fcntl")
        return real_import(name, *args, **kwargs)

    module_path = SCRIPTS_DIR / "loop_common.py"
    spec = importlib.util.spec_from_file_location("loop_common_without_fcntl", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {module_path}")
    module = importlib.util.module_from_spec(spec)
    with patch("builtins.__import__", side_effect=import_hook):
        spec.loader.exec_module(module)
    return module


def append_worker(
    ledger: str,
    lock_dir: str,
    start: multiprocessing.synchronize.Event,
    worker: int,
) -> None:
    loop_common.LOCK_DIR = Path(lock_dir)
    if not start.wait(timeout=10):
        raise TimeoutError("append contention start was not released")
    for sequence in range(25):
        loop_common.append_jsonl(
            Path(ledger),
            {"sequence": sequence, "worker": worker},
        )


def queue_lock_worker(
    lock_dir: str,
    start: multiprocessing.synchronize.Event,
    active: multiprocessing.sharedctypes.Synchronized,
    overlap: multiprocessing.sharedctypes.Synchronized,
) -> None:
    loop_common.LOCK_DIR = Path(lock_dir)
    if not start.wait(timeout=10):
        raise TimeoutError("queue-lock contention start was not released")
    for _ in range(12):
        with loop_common.queue_lock("contention"):
            with active.get_lock():
                if active.value:
                    overlap.value = 1
                active.value += 1
            time.sleep(0.002)
            with active.get_lock():
                active.value -= 1


class MissingFcntlTests(unittest.TestCase):
    def test_import_succeeds_but_mutations_fail_before_filesystem_changes(self) -> None:
        module = load_without_fcntl()
        self.assertIsNone(module._fcntl)
        self.assertNotIn("threading", module.__dict__)
        self.assertTrue(module.utc_now())

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ledger = root / "missing-parent" / "events.jsonl"
            module.LOCK_DIR = root / "missing-locks"

            with self.assertRaises(module.LockingUnavailableError):
                module.append_jsonl(ledger, {"id": 1})
            self.assertFalse(ledger.parent.exists())

            entered = False
            with self.assertRaises(module.LockingUnavailableError):
                with module.queue_lock("inbox"):
                    entered = True
            self.assertFalse(entered)
            self.assertFalse(module.LOCK_DIR.exists())


@unittest.skipIf(loop_common._fcntl is None, "requires fcntl.flock")
class LockFailureTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        original_lock_dir = loop_common.LOCK_DIR
        self.addCleanup(setattr, loop_common, "LOCK_DIR", original_lock_dir)
        loop_common.LOCK_DIR = self.root / "queue-locks"

    def test_acquire_errors_do_not_mutate_or_enter_protected_body(self) -> None:
        denied = OSError(errno.EACCES, "simulated lock denial")
        ledger = self.root / "append" / "events.jsonl"

        with patch.object(loop_common._fcntl, "flock", side_effect=denied):
            with self.assertRaises(OSError):
                loop_common.append_jsonl(ledger, {"id": 1})
        self.assertFalse(ledger.exists())

        entered = False
        with patch.object(loop_common._fcntl, "flock", side_effect=denied):
            with self.assertRaises(OSError):
                with loop_common.queue_lock("inbox"):
                    entered = True
        self.assertFalse(entered)

    def test_release_error_is_not_reported_as_success(self) -> None:
        real_flock = loop_common._fcntl.flock

        def fail_release(descriptor: int, operation: int) -> None:
            if operation == loop_common._fcntl.LOCK_UN:
                raise OSError(errno.EIO, "simulated unlock failure")
            real_flock(descriptor, operation)

        entered = False
        with patch.object(loop_common._fcntl, "flock", side_effect=fail_release):
            with self.assertRaises(
                loop_common.LockReleaseOutcomeUncertainError
            ) as raised:
                with loop_common.queue_lock("inbox"):
                    entered = True
        self.assertTrue(entered)
        self.assertTrue(raised.exception.effects_may_have_committed)

    def test_append_release_error_reports_committed_outcome_as_uncertain(self) -> None:
        ledger = self.root / "events.jsonl"
        real_flock = loop_common._fcntl.flock

        def fail_release(descriptor: int, operation: int) -> None:
            if operation == loop_common._fcntl.LOCK_UN:
                raise OSError(errno.EIO, "simulated unlock failure")
            real_flock(descriptor, operation)

        with patch.object(loop_common._fcntl, "flock", side_effect=fail_release):
            with self.assertRaises(
                loop_common.LockReleaseOutcomeUncertainError
            ) as raised:
                loop_common.append_jsonl(ledger, {"event_id": "event-1"})

        self.assertTrue(raised.exception.effects_may_have_committed)
        self.assertEqual(
            [json.loads(line) for line in ledger.read_text().splitlines()],
            [{"event_id": "event-1"}],
        )

    def test_body_error_remains_primary_when_release_also_fails(self) -> None:
        real_flock = loop_common._fcntl.flock

        def fail_release(descriptor: int, operation: int) -> None:
            if operation == loop_common._fcntl.LOCK_UN:
                raise OSError(errno.EIO, "simulated unlock failure")
            real_flock(descriptor, operation)

        with patch.object(loop_common._fcntl, "flock", side_effect=fail_release):
            with self.assertRaisesRegex(ValueError, "protected body failed"):
                with loop_common.queue_lock("inbox"):
                    raise ValueError("protected body failed")

    def test_append_write_error_restores_existing_ledger(self) -> None:
        ledger = self.root / "events.jsonl"
        original = b'{"seed": true}\n'
        ledger.write_bytes(original)

        with patch.object(
            loop_common.os,
            "write",
            side_effect=OSError(errno.EIO, "simulated write failure"),
        ):
            with self.assertRaises(OSError):
                loop_common.append_jsonl(ledger, {"id": 1})

        self.assertEqual(ledger.read_bytes(), original)

    def test_append_write_error_removes_new_ledger(self) -> None:
        ledger = self.root / "new" / "events.jsonl"

        with patch.object(
            loop_common.os,
            "write",
            side_effect=OSError(errno.EIO, "simulated write failure"),
        ):
            with self.assertRaises(OSError):
                loop_common.append_jsonl(ledger, {"id": 1})

        self.assertFalse(ledger.exists())

    def test_partial_append_then_write_error_restores_existing_ledger(self) -> None:
        ledger = self.root / "events.jsonl"
        original = b'{"seed": true}\n'
        ledger.write_bytes(original)
        real_write = loop_common.os.write
        call_count = 0

        def write_part_then_fail(descriptor: int, payload: memoryview) -> int:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                partial_length = max(1, len(payload) // 2)
                return real_write(descriptor, payload[:partial_length])
            raise OSError(errno.EIO, "simulated failure after a partial write")

        with patch.object(loop_common.os, "write", side_effect=write_part_then_fail):
            with self.assertRaises(OSError):
                loop_common.append_jsonl(ledger, {"id": 1})

        self.assertGreaterEqual(call_count, 2)
        self.assertEqual(ledger.read_bytes(), original)

    def test_append_fsync_error_restores_existing_ledger(self) -> None:
        ledger = self.root / "events.jsonl"
        original = b'{"seed": true}\n'
        ledger.write_bytes(original)
        real_fsync = loop_common.os.fsync
        call_count = 0

        def fail_first_fsync(descriptor: int) -> None:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise OSError(errno.EIO, "simulated fsync failure")
            real_fsync(descriptor)

        with patch.object(loop_common.os, "fsync", side_effect=fail_first_fsync):
            with self.assertRaises(OSError):
                loop_common.append_jsonl(ledger, {"id": 1})

        self.assertGreaterEqual(call_count, 2)
        self.assertEqual(ledger.read_bytes(), original)

    def test_append_fsync_error_removes_new_ledger(self) -> None:
        ledger = self.root / "new" / "events.jsonl"

        with patch.object(
            loop_common.os,
            "fsync",
            side_effect=OSError(errno.EIO, "simulated fsync failure"),
        ):
            with self.assertRaises(OSError):
                loop_common.append_jsonl(ledger, {"id": 1})

        self.assertFalse(ledger.exists())

    def test_atomic_queue_write_fsync_error_preserves_target(self) -> None:
        queue = self.root / "queue.jsonl"
        original = b'{"seed": true}\n'
        queue.write_bytes(original)

        with patch.object(
            loop_common.os,
            "fsync",
            side_effect=OSError(errno.EIO, "simulated fsync failure"),
        ):
            with self.assertRaises(OSError):
                with loop_common.queue_lock("inbox"):
                    loop_common.write_jsonl(queue, [{"id": 1}])

        self.assertEqual(queue.read_bytes(), original)
        self.assertEqual(list(queue.parent.glob(f".{queue.name}.*.tmp")), [])


@unittest.skipUnless(
    loop_common._fcntl is not None and "fork" in multiprocessing.get_all_start_methods(),
    "requires Unix fcntl and fork multiprocessing",
)
class MultiprocessContentionTests(unittest.TestCase):
    def test_append_jsonl_preserves_all_records_under_contention(self) -> None:
        context = multiprocessing.get_context("fork")
        with tempfile.TemporaryDirectory() as temporary:
            ledger = Path(temporary) / "events.jsonl"
            lock_dir = str(Path(temporary) / "locks")
            start = context.Event()
            processes = [
                context.Process(
                    target=append_worker,
                    args=(str(ledger), lock_dir, start, worker),
                )
                for worker in range(4)
            ]
            for process in processes:
                process.start()
            start.set()
            try:
                for process in processes:
                    process.join(timeout=20)
            finally:
                for process in processes:
                    if process.is_alive():
                        process.terminate()
                        process.join(timeout=5)

            self.assertEqual([process.exitcode for process in processes], [0] * 4)
            records = [json.loads(line) for line in ledger.read_text().splitlines()]
            self.assertEqual(len(records), 100)
            self.assertEqual(
                {(record["worker"], record["sequence"]) for record in records},
                {(worker, sequence) for worker in range(4) for sequence in range(25)},
            )

    def test_queue_lock_serializes_real_processes(self) -> None:
        context = multiprocessing.get_context("fork")
        with tempfile.TemporaryDirectory() as temporary:
            start = context.Event()
            active = context.Value("i", 0)
            overlap = context.Value("i", 0)
            lock_dir = str(Path(temporary) / "locks")
            processes = [
                context.Process(
                    target=queue_lock_worker,
                    args=(lock_dir, start, active, overlap),
                )
                for _ in range(4)
            ]
            for process in processes:
                process.start()
            start.set()
            try:
                for process in processes:
                    process.join(timeout=20)
            finally:
                for process in processes:
                    if process.is_alive():
                        process.terminate()
                        process.join(timeout=5)

            self.assertEqual([process.exitcode for process in processes], [0] * 4)
            self.assertEqual(active.value, 0)
            self.assertEqual(overlap.value, 0)


if __name__ == "__main__":
    unittest.main()
