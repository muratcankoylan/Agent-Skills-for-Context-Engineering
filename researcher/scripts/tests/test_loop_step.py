"""Regression tests for the removed legacy network retrieval path."""

from __future__ import annotations

import socket
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "researcher" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import loop_step  # noqa: E402


class LegacyNetworkRemovalTests(unittest.TestCase):
    def test_initialized_run_always_parks_without_network_or_file_writes(self) -> None:
        common_prefix = f"https://example.test/{'same-prefix-' * 24}"
        urls = [f"{common_prefix}first?token=one", f"{common_prefix}second?token=two"]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            run_dir = root / "run"
            with mock.patch.object(loop_step, "park_run") as park, mock.patch.object(
                socket,
                "create_connection",
            ) as socket_connect, mock.patch.object(
                urllib.request,
                "urlopen",
            ) as urlopen:
                results = [
                    loop_step.advance_initialized(run_dir, {"source_url": url})
                    for url in urls
                ]

            self.assertEqual(
                results,
                [
                    {"action": "parked", "run_id": "run", "reason": "manual retrieval required"},
                    {"action": "parked", "run_id": "run", "reason": "manual retrieval required"},
                ],
            )
            self.assertEqual(park.call_count, 2)
            socket_connect.assert_not_called()
            urlopen.assert_not_called()
            self.assertFalse(run_dir.exists())
            self.assertEqual(list(root.iterdir()), [])

    def test_loop_step_module_has_no_network_retrieval_surface(self) -> None:
        source = Path(loop_step.__file__).read_text(encoding="utf-8")
        self.assertFalse(hasattr(loop_step, "fetch_url"))
        self.assertFalse(hasattr(loop_step, "attempt_retrieval"))
        for forbidden in (
            "import http.client",
            "import socket",
            "urllib.request",
            "--allow-fetch",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)

    def test_cli_rejects_removed_allow_fetch_flag(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(Path(loop_step.__file__)), "--allow-fetch", "--json"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertIn("unrecognized arguments: --allow-fetch", completed.stderr)

    def test_inbox_catalog_is_not_consumed_or_treated_as_runnable_work(self) -> None:
        source = {"source_id": "a" * 32, "url": "https://example.test/source"}
        with mock.patch.object(
            loop_step, "require_runtime_queue_ledgers", return_value={}
        ), mock.patch.object(
            loop_step, "reap_closed_runs", return_value=[]
        ), mock.patch.object(
            loop_step,
            "queue_snapshot",
            return_value={
                "parse_ok": True,
                "referential_ok": True,
                "unknown": 0,
                "pending_reap": 0,
                "_pending_reap": [],
                "_buckets": {"active": [], "parked": [], "closed": [], "unknown": []},
            },
        ), mock.patch.object(
            loop_step, "read_jsonl", return_value=[source]
        ), mock.patch.object(loop_step, "record_event") as record:
            result = loop_step.loop_step(
                {"budgets": {"max_parked": 12}}
            )
        self.assertEqual(result, {"ok": True, "action": "no-op"})
        self.assertNotIn("manual-init-required", repr(record.call_args_list))

    def test_invalid_budget_or_missing_ledgers_fails_before_reaping(self) -> None:
        with mock.patch.object(
            loop_step, "require_runtime_queue_ledgers", return_value={}
        ), mock.patch.object(loop_step, "reap_closed_runs") as reap, self.assertRaisesRegex(
            ValueError, "max_parked"
        ):
            loop_step.loop_step({"budgets": {"max_parked": True}})
        reap.assert_not_called()

        with mock.patch.object(
            loop_step,
            "require_runtime_queue_ledgers",
            side_effect=ValueError("runtime queue ledgers are not initialized"),
        ), mock.patch.object(loop_step, "reap_closed_runs") as reap, self.assertRaisesRegex(
            ValueError, "not initialized"
        ):
            loop_step.loop_step({"budgets": {"max_parked": 12}})
        reap.assert_not_called()

    def test_park_and_reap_share_one_transaction_lock_without_lost_update(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            parked_path = root / "parked.jsonl"
            done_path = root / "done.jsonl"
            parked_path.write_text(
                '{"parked_at":"2026-08-17T00:00:00+00:00",'
                '"reason":"closed","run_id":"closed-run"}\n',
                encoding="utf-8",
            )
            done_path.write_text("", encoding="utf-8")
            closed_run = root / "closed-run"
            (closed_run / "reports").mkdir(parents=True)
            closed_state = {
                "current_state": "closed",
                "close_status": "rejected",
                "close_reason": "not accepted",
                "state_history": [
                    {"timestamp": "2026-08-17T00:00:01+00:00"}
                ],
            }
            (closed_run / "reports" / "closure.json").write_text(
                '{"closed_at":"2026-08-17T00:00:01+00:00",'
                '"integrity_errors":[],"reason":"not accepted",'
                '"reviewed_by":"operator","status":"rejected"}\n',
                encoding="utf-8",
            )
            done_write_started = threading.Event()
            allow_done_write = threading.Event()
            park_finished = threading.Event()
            errors: list[BaseException] = []
            real_write_jsonl = loop_step.write_jsonl

            def pausing_write(path: Path, records: object) -> None:
                if path == done_path and not done_write_started.is_set():
                    done_write_started.set()
                    if not allow_done_write.wait(timeout=5):
                        raise RuntimeError("test did not release done write")
                real_write_jsonl(path, records)  # type: ignore[arg-type]

            def reap() -> None:
                try:
                    loop_step.reap_closed_runs([closed_run])
                except BaseException as exc:
                    errors.append(exc)

            def park() -> None:
                try:
                    loop_step.park_run("active-run", "needs review")
                except BaseException as exc:
                    errors.append(exc)
                finally:
                    park_finished.set()

            lock_module = sys.modules[loop_step.queue_lock.__module__]
            with mock.patch.object(loop_step, "PARKED_FILE", parked_path), mock.patch.object(
                loop_step, "DONE_FILE", done_path
            ), mock.patch.object(
                loop_step, "load_run_state", return_value=closed_state
            ), mock.patch.object(
                loop_step, "write_jsonl", side_effect=pausing_write
            ), mock.patch.object(
                lock_module, "LOCK_DIR", root / "locks"
            ):
                reap_thread = threading.Thread(target=reap)
                park_thread = threading.Thread(target=park)
                reap_thread.start()
                self.assertTrue(done_write_started.wait(timeout=5))
                park_thread.start()
                self.assertFalse(park_finished.wait(timeout=0.2))
                allow_done_write.set()
                reap_thread.join(timeout=5)
                park_thread.join(timeout=5)

            self.assertEqual(errors, [])
            self.assertFalse(reap_thread.is_alive())
            self.assertFalse(park_thread.is_alive())
            self.assertEqual(
                [record["run_id"] for record in loop_step.read_jsonl(parked_path)],
                ["active-run"],
            )
            self.assertEqual(
                [record["run_id"] for record in loop_step.read_jsonl(done_path)],
                ["closed-run"],
            )

    def test_reap_rejects_missing_closure_before_done_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            parked_path = root / "parked.jsonl"
            done_path = root / "done.jsonl"
            parked_path.write_text("", encoding="utf-8")
            done_path.write_text("", encoding="utf-8")
            closed_run = root / "closed-run"
            closed_run.mkdir()
            state = {
                "current_state": "closed",
                "close_status": "rejected",
                "close_reason": "not accepted",
                "state_history": [
                    {"timestamp": "2026-08-17T00:00:01+00:00"}
                ],
            }
            lock_module = sys.modules[loop_step.queue_lock.__module__]
            with mock.patch.object(
                loop_step, "PARKED_FILE", parked_path
            ), mock.patch.object(
                loop_step, "DONE_FILE", done_path
            ), mock.patch.object(
                loop_step, "load_run_state", return_value=state
            ), mock.patch.object(
                lock_module, "LOCK_DIR", root / "locks"
            ), self.assertRaisesRegex(ValueError, "cannot reap invalid closed run"):
                loop_step.reap_closed_runs([closed_run])
            self.assertEqual(done_path.read_text(encoding="utf-8"), "")

if __name__ == "__main__":
    unittest.main()
