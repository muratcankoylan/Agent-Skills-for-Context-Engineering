"""Import capability and real-process exclusion, not a Windows locking backend."""

from __future__ import annotations

import builtins
import errno
import importlib.util
import json
import multiprocessing
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import loop_common as subject  # noqa: E402


def import_without_lock_backend():
    actual = builtins.__import__

    def blocked(name, *args, **kwargs):
        if name == "fcntl":
            raise ModuleNotFoundError("unavailable", name="fcntl")
        return actual(name, *args, **kwargs)

    spec = importlib.util.spec_from_file_location("lock_capability_probe", SCRIPTS / "loop_common.py")
    module = importlib.util.module_from_spec(spec)
    with patch("builtins.__import__", side_effect=blocked):
        spec.loader.exec_module(module)
    return module


def contend(lock_dir, ledger, ready, active, overlaps, worker):
    subject.LOCK_DIR = Path(lock_dir)
    if not ready.wait(10):
        raise TimeoutError("test barrier")
    for sequence in range(12):
        with subject.queue_lock("transactions"):
            with active.get_lock():
                if active.value:
                    overlaps.value += 1
                active.value += 1
            time.sleep(0.002)
            with active.get_lock():
                active.value -= 1
        subject.append_jsonl(Path(ledger), {"worker": worker, "sequence": sequence})


def old_writer(ledger, held, release):
    with Path(ledger).open("a") as handle:
        subject.fcntl.flock(handle.fileno(), subject.fcntl.LOCK_EX)
        held.set()
        if not release.wait(10):
            raise TimeoutError("legacy writer barrier")
        subject.fcntl.flock(handle.fileno(), subject.fcntl.LOCK_UN)


def new_writer(lock_dir, ledger, started, finished):
    subject.LOCK_DIR = Path(lock_dir)
    started.set()
    subject.append_jsonl(Path(ledger), {"id": "new"})
    finished.set()


class CapabilityTests(unittest.TestCase):
    def test_import_without_backend_keeps_read_helpers_available(self):
        module = import_without_lock_backend()
        self.assertIsNone(module.fcntl)
        self.assertTrue(module.utc_now())
        self.assertNotIn("threading", module.__dict__)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "read.json"
            path.write_text('{"ok":true}')
            self.assertEqual(module.load_json(path), {"ok": True})

    def test_missing_backend_refuses_effect_before_creating_paths(self):
        module = import_without_lock_backend()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            module.LOCK_DIR = root / "locks"
            with self.assertRaises(module.LockingUnavailableError):
                with module.queue_lock("inbox"):
                    self.fail("unprotected body entered")
            with self.assertRaises(module.LockingUnavailableError):
                module.append_jsonl(root / "new" / "events.jsonl", {"id": 1})
            self.assertEqual(list(root.iterdir()), [])


@unittest.skipIf(getattr(subject, "fcntl", None) is None, "requires POSIX flock")
class LockTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.patch = patch.object(subject, "LOCK_DIR", self.root / "locks")
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def test_all_acquisition_errors_prevent_queue_body(self):
        for code in (errno.EACCES, errno.EAGAIN, errno.EIO):
            with self.subTest(code=code):
                with patch.object(subject.fcntl, "flock", side_effect=OSError(code, "denied")) as lock:
                    with self.assertRaises(OSError):
                        with subject.queue_lock("inbox"):
                            self.fail("denial was ignored")
                self.assertEqual(lock.call_count, 1)

    def test_denial_preserves_existing_append_target(self):
        target = self.root / "events.jsonl"
        seed = b'{"seed":1}\n'
        target.write_bytes(seed)
        with patch.object(subject.fcntl, "flock", side_effect=OSError(errno.EACCES, "denied")):
            with self.assertRaises(OSError):
                subject.append_jsonl(target, {"id": 1})
        self.assertEqual(target.read_bytes(), seed)

    def test_denial_does_not_create_new_append_target(self):
        target = self.root / "events.jsonl"
        with patch.object(subject.fcntl, "flock", side_effect=OSError(errno.EACCES, "denied")):
            with self.assertRaises(OSError):
                subject.append_jsonl(target, {"id": 1})
        self.assertFalse(target.exists())

    def test_target_lock_denial_never_appends_or_removes_existing_file(self):
        target = self.root / "events.jsonl"
        seed = b'{"seed":1}\n'
        target.write_bytes(seed)
        original = subject.fcntl.flock
        acquisitions = 0

        def deny_target(fd, operation):
            nonlocal acquisitions
            if operation == subject.fcntl.LOCK_EX:
                acquisitions += 1
                if acquisitions == 2:
                    raise OSError(errno.EACCES, "target denied")
            original(fd, operation)

        with patch.object(subject.fcntl, "flock", side_effect=deny_target):
            with self.assertRaises(OSError):
                subject.append_jsonl(target, {"id": 1})
        self.assertEqual(acquisitions, 2)
        self.assertEqual(target.read_bytes(), seed)

    def fail_release(self, descriptor, operation):
        if operation == subject.fcntl.LOCK_UN:
            raise OSError(errno.EIO, "unlock failed")
        self.original_flock(descriptor, operation)

    def test_release_failure_reports_uncertainty_after_body(self):
        self.original_flock = subject.fcntl.flock
        entered = []
        with patch.object(subject.fcntl, "flock", side_effect=self.fail_release):
            with self.assertRaises(subject.LockReleaseOutcomeUncertainError) as raised:
                with subject.queue_lock("inbox"):
                    entered.append(True)
        self.assertEqual(entered, [True])
        self.assertTrue(raised.exception.effects_may_have_committed)

    def test_release_failure_after_append_does_not_imply_safe_retry(self):
        self.original_flock = subject.fcntl.flock
        target = self.root / "events.jsonl"
        with patch.object(subject.fcntl, "flock", side_effect=self.fail_release):
            with self.assertRaises(subject.LockReleaseOutcomeUncertainError) as raised:
                subject.append_jsonl(target, {"id": 1})
        self.assertTrue(raised.exception.effects_may_have_committed)
        self.assertEqual(json.loads(target.read_text()), {"id": 1})

    def test_body_exception_is_not_replaced_by_unlock_exception(self):
        self.original_flock = subject.fcntl.flock
        with patch.object(subject.fcntl, "flock", side_effect=self.fail_release):
            with self.assertRaisesRegex(ValueError, "body failure"):
                with subject.queue_lock("inbox"):
                    raise ValueError("body failure")

    def test_invalid_names_rejected_without_lock_creation(self):
        for name in ("../escape", str(self.root / "absolute"), "inbox\n", "", None, "x" * 129):
            with self.subTest(name=name), self.assertRaises(ValueError):
                with subject.queue_lock(name):
                    self.fail("invalid lock name entered")
        self.assertFalse(subject.LOCK_DIR.exists())

    def test_lock_symlink_cannot_redirect_lock_identity(self):
        subject.LOCK_DIR.mkdir()
        target = self.root / "outside"
        target.write_text("preserve")
        (subject.LOCK_DIR / "inbox.lock").symlink_to(target)
        with self.assertRaises(OSError):
            with subject.queue_lock("inbox"):
                self.fail("symlink lock admitted")
        self.assertEqual(target.read_text(), "preserve")

    def test_hardlinked_and_nonregular_locks_rejected(self):
        subject.LOCK_DIR.mkdir()
        target = self.root / "outside"
        target.write_text("preserve")
        os.link(target, subject.LOCK_DIR / "hard.lock")
        os.mkfifo(subject.LOCK_DIR / "pipe.lock")
        for name in ("hard", "pipe"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                with subject.queue_lock(name):
                    self.fail("aliased or nonregular lock admitted")
        self.assertEqual(target.read_text(), "preserve")

    @unittest.skipUnless("fork" in multiprocessing.get_all_start_methods(), "requires fork")
    def test_legacy_inode_lock_excludes_new_writer(self):
        ctx = multiprocessing.get_context("fork")
        for trial in range(2):
            with self.subTest(trial=trial):
                target = self.root / f"events-{trial}.jsonl"
                seed = b'{"seed":1}\n'
                target.write_bytes(seed)
                held, release, started, finished = (ctx.Event() for _ in range(4))
                legacy = ctx.Process(target=old_writer, args=(str(target), held, release))
                new = ctx.Process(target=new_writer, args=(str(subject.LOCK_DIR), str(target),
                                  started, finished))
                legacy.start()
                try:
                    self.assertTrue(held.wait(5))
                    new.start()
                    self.assertTrue(started.wait(5))
                    self.assertFalse(finished.wait(0.2), "new writer bypassed existing inode lock")
                    self.assertEqual(target.read_bytes(), seed)
                    release.set()
                    self.assertTrue(finished.wait(5))
                finally:
                    release.set()
                    for process in (legacy, new):
                        if process.pid is not None:
                            process.join(5)
                            if process.is_alive():
                                process.terminate()
                                process.join(5)
                self.assertEqual([legacy.exitcode, new.exitcode], [0, 0])
                self.assertEqual(len(target.read_text().splitlines()), 2)

    def test_hardlinked_append_target_refused_without_rollback_or_mutation(self):
        # The integrated path contract is stricter than the original PR: reject
        # aliases outright instead of allowing them under a shared inode lock.
        target = self.root / "events.jsonl"
        seed = b'{"seed":1}\n'
        target.write_bytes(seed)
        alias = self.root / "alias.jsonl"
        os.link(target, alias)
        with patch.object(subject, "_rollback_failed_append") as rollback:
            with self.assertRaises(ValueError):
                subject.append_jsonl(alias, {"id": 1})
        rollback.assert_not_called()
        self.assertEqual(target.read_bytes(), seed)
        self.assertEqual(alias.read_bytes(), seed)

    def test_rollback_preserves_bytes_committed_before_target_lock_acquisition(self):
        target = self.root / "events.jsonl"
        seed = b'{"seed":1}\n'
        prior = b'{"legacy":1}\n'
        target.write_bytes(seed)
        original_flock = subject.fcntl.flock
        acquisitions = 0

        def acquire_after_legacy_write(fd, operation):
            nonlocal acquisitions
            if operation == subject.fcntl.LOCK_EX:
                acquisitions += 1
                if acquisitions == 2:
                    # Simulate a writer finishing between open() and flock().
                    with target.open("ab") as legacy:
                        legacy.write(prior)
            original_flock(fd, operation)

        with patch.object(subject.fcntl, "flock", side_effect=acquire_after_legacy_write):
            with patch.object(subject.os, "write", side_effect=OSError("write failed")):
                with self.assertRaises(OSError):
                    subject.append_jsonl(target, {"id": 1})
        self.assertEqual(acquisitions, 2)
        self.assertEqual(target.read_bytes(), seed + prior)

    @unittest.skipUnless("fork" in multiprocessing.get_all_start_methods(), "requires fork")
    def test_real_process_contention(self):
        ctx = multiprocessing.get_context("fork")
        start, active, overlaps = ctx.Event(), ctx.Value("i", 0), ctx.Value("i", 0)
        target = self.root / "events.jsonl"
        processes = [ctx.Process(target=contend, args=(str(subject.LOCK_DIR), str(target), start,
                     active, overlaps, worker)) for worker in range(4)]
        for process in processes:
            process.start()
        start.set()
        try:
            for process in processes:
                process.join(15)
        finally:
            for process in processes:
                if process.is_alive():
                    process.terminate()
                    process.join(5)
        self.assertEqual([p.exitcode for p in processes], [0] * 4)
        self.assertEqual(active.value, 0)
        self.assertEqual(overlaps.value, 0)
        rows = [json.loads(line) for line in target.read_text().splitlines()]
        self.assertEqual(len(rows), 48)
        self.assertEqual({(row["worker"], row["sequence"]) for row in rows},
                         {(worker, sequence) for worker in range(4) for sequence in range(12)})


if __name__ == "__main__":
    unittest.main()
