from __future__ import annotations

import json
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from researcher.scripts import local_rehearsal
from researcher.scripts.local_scheduler import LocalScheduler


class LocalRehearsalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()

    def run_once(self, **overrides):
        arguments = {
            "runtime_dir": self.root / "run",
            "queries": ("context engineering agents", "agent evaluation"),
            "observed_at": "2026-09-07T12:00:00Z",
            "live_public": False,
            "include_x": False,
        }
        arguments.update(overrides)
        return local_rehearsal.run_rehearsal(**arguments)

    def test_composed_observation_has_byte_bound_inputs_and_no_fake_verifier(
        self,
    ) -> None:
        report = self.run_once()
        run = self.root / "run"
        self.assertTrue(report["harness_execution_ok"])
        self.assertFalse(report["production_ready"])
        self.assertFalse(report["activation_enabled"])
        self.assertEqual(report["authority"], "none")
        self.assertEqual(report["model_calls"], 0)
        self.assertEqual(report["paid_calls"], 0)
        self.assertNotIn("candidate_digest", report)
        self.assertEqual(len(report["scheduled_work_orders"]), 3)
        self.assertTrue(report["results"]["benchmark.catalog"]["passed"])
        prompt = report["results"]["health.snapshot"]
        self.assertFalse(prompt["verification_performed"])
        self.assertFalse(prompt["independence_asserted"])
        self.assertNotIn("verifier_instance_id", prompt)
        manifest = local_rehearsal._read_json(run / "input-manifest.json")
        self.assertEqual(
            report["input_manifest_digest"],
            local_rehearsal.sha256_bytes(local_rehearsal.canonicalize(manifest)),
        )
        self.assertIn("researcher/scripts/local_rehearsal.py", manifest["input_files"])
        persisted = local_rehearsal._read_json(run / "rehearsal-report.json")
        self.assertEqual(persisted, report)

    def test_replay_validates_without_executing_stages(self) -> None:
        first = self.run_once()
        with patch.object(
            local_rehearsal,
            "_execute_stage",
            side_effect=AssertionError("unexpected execution"),
        ):
            self.assertEqual(first, self.run_once())

    def test_report_publication_crash_recovers_from_committed_stage_results(
        self,
    ) -> None:
        write = local_rehearsal._atomic_write

        def crash_at_report(path, payload):
            if path.name == "rehearsal-report.json":
                raise KeyboardInterrupt("simulated process interruption")
            return write(path, payload)

        with patch.object(
            local_rehearsal, "_atomic_write", side_effect=crash_at_report
        ):
            with self.assertRaises(KeyboardInterrupt):
                self.run_once()
        with patch.object(
            local_rehearsal,
            "_execute_stage",
            side_effect=AssertionError("replayed stage"),
        ):
            result = self.run_once()
        self.assertTrue(result["harness_execution_ok"])
        self.assertTrue(
            all(order["attempt"] == 1 for order in result["scheduled_work_orders"])
        )

    def test_crash_after_artifact_before_completion_reuses_observation(self) -> None:
        complete = LocalScheduler.complete
        interrupted = False

        def crash_once(scheduler, *args, **kwargs):
            nonlocal interrupted
            if not interrupted:
                interrupted = True
                raise KeyboardInterrupt("simulated commit gap")
            return complete(scheduler, *args, **kwargs)

        with patch.object(LocalScheduler, "complete", new=crash_once):
            with self.assertRaises(KeyboardInterrupt):
                self.run_once()
        execute = local_rehearsal._execute_stage

        def no_repeat_source(action, **kwargs):
            if action == "discover.sources":
                raise AssertionError(
                    "source observation repeated after durable artifact"
                )
            return execute(action, **kwargs)

        with patch.object(
            local_rehearsal, "_execute_stage", side_effect=no_repeat_source
        ):
            result = self.run_once()
        source = next(
            order
            for order in result["scheduled_work_orders"]
            if order["action"] == "discover.sources"
        )
        self.assertEqual(source["attempt"], 2)
        self.assertTrue(result["harness_execution_ok"])

    def test_failed_stage_is_retryable_and_blocks_dependent_registration(self) -> None:
        with patch.object(
            local_rehearsal, "execute_catalog", return_value={"passed": False}
        ):
            with self.assertRaises(local_rehearsal.RehearsalError):
                self.run_once()
        orders = LocalScheduler(
            self.root / "run" / "scheduler.sqlite3"
        ).list_work_orders()
        self.assertEqual(
            {order.action for order in orders},
            {"discover.sources", "benchmark.catalog"},
        )
        self.assertFalse((self.root / "run" / "rehearsal-report.json").exists())
        result = self.run_once()
        self.assertTrue(result["harness_execution_ok"])
        benchmark = next(
            order
            for order in result["scheduled_work_orders"]
            if order["action"] == "benchmark.catalog"
        )
        self.assertEqual(benchmark["attempt"], 2)

    def test_cached_report_tampering_is_rejected(self) -> None:
        self.run_once()
        report_path = self.root / "run" / "rehearsal-report.json"
        report = json.loads(report_path.read_text())
        report["production_ready"] = True
        report_path.write_text(json.dumps(report))
        with self.assertRaisesRegex(local_rehearsal.RehearsalError, "cached report"):
            self.run_once()

    def test_cached_success_does_not_hide_missing_prompt_artifact(self) -> None:
        self.run_once()
        (self.root / "run" / "prompts" / "builder-instance.json").unlink()
        with self.assertRaises(local_rehearsal.RehearsalError):
            self.run_once()

    def test_changed_result_bytes_fail_digest_binding(self) -> None:
        self.run_once()
        path = self.root / "run" / "source-observations.json"
        original = path.read_text()
        path.write_text(original + " ")
        with self.assertRaisesRegex(local_rehearsal.RehearsalError, "digest"):
            self.run_once()

    def test_x_mode_and_catalog_bytes_are_in_resume_identity(self) -> None:
        catalog = self.root / "catalog.jsonl"
        catalog.write_bytes(local_rehearsal.DEFAULT_CATALOG.read_bytes())
        self.run_once(catalog=catalog)
        with self.assertRaisesRegex(local_rehearsal.RehearsalError, "inputs changed"):
            self.run_once(catalog=catalog, include_x=True)
        catalog.write_bytes(catalog.read_bytes() + b"\n")
        with self.assertRaisesRegex(local_rehearsal.RehearsalError, "inputs changed"):
            self.run_once(catalog=catalog)

    def test_inputs_changing_during_execution_prevent_success_publication(self) -> None:
        identity = local_rehearsal._input_identity
        calls = 0

        def changed_identity(**kwargs):
            nonlocal calls
            calls += 1
            value = identity(**kwargs)
            if calls == 2:
                value["input_files"]["changed-input.py"] = "sha256:" + "a" * 64
            return value

        with patch.object(
            local_rehearsal, "_input_identity", side_effect=changed_identity
        ):
            with self.assertRaisesRegex(
                local_rehearsal.RehearsalError, "changed while"
            ):
                self.run_once()
        self.assertFalse((self.root / "run" / "rehearsal-report.json").exists())

    def test_concurrent_supervisors_cannot_duplicate_stages(self) -> None:
        entered = threading.Event()
        release = threading.Event()
        execute = local_rehearsal._execute_stage

        def hold_source(action, **kwargs):
            if action == "discover.sources":
                entered.set()
                if not release.wait(timeout=10):
                    raise AssertionError("test supervisor release timed out")
            return execute(action, **kwargs)

        with (
            ThreadPoolExecutor(max_workers=1) as pool,
            patch.object(local_rehearsal, "_execute_stage", side_effect=hold_source),
        ):
            future = pool.submit(self.run_once)
            try:
                self.assertTrue(entered.wait(timeout=10))
                with self.assertRaisesRegex(
                    local_rehearsal.RehearsalError, "another supervisor"
                ):
                    self.run_once()
            finally:
                release.set()
            self.assertTrue(future.result(timeout=10)["harness_execution_ok"])

    def test_unbound_old_runtime_and_symlink_roots_are_rejected(self) -> None:
        old = self.root / "old"
        old.mkdir()
        (old / "rehearsal-report.json").write_text("{}")
        with self.assertRaises(local_rehearsal.RehearsalError):
            self.run_once(runtime_dir=old)
        alias = self.root / "alias"
        alias.symlink_to(old, target_is_directory=True)
        with self.assertRaises(local_rehearsal.RehearsalError):
            self.run_once(runtime_dir=alias / "run")

    def test_soak_runs_bounded_offline_cycles_and_exact_replays(self) -> None:
        result = local_rehearsal.run_soak(
            runtime_dir=self.root / "soak",
            queries=("context",),
            iterations=3,
            max_seconds=30,
            observed_at="2026-09-07T12:00:00Z",
        )
        self.assertEqual(result["completed_iterations"], 3)
        self.assertEqual(result["network_calls"], 0)
        self.assertTrue(all(item["replay_identical"] for item in result["cycles"]))
        self.assertEqual(
            len(set(item["report_digest"] for item in result["cycles"])), 3
        )
        self.assertFalse(result["production_ready"])

    def test_invalid_inputs_fail_before_runtime_creation(self) -> None:
        for overrides in (
            {"queries": ()},
            {"queries": "bad"},
            {"live_public": "yes"},
            {"include_x": 1},
        ):
            with (
                self.subTest(overrides=overrides),
                self.assertRaises(local_rehearsal.RehearsalError),
            ):
                self.run_once(**overrides)
            self.assertFalse((self.root / "run").exists())

    def test_cli_ready_gate_stays_red_and_soak_cannot_call_network(self) -> None:
        self.assertEqual(
            local_rehearsal.main(
                [
                    "--runtime-dir",
                    str(self.root / "run"),
                    "--query",
                    "bounded fixture",
                    "--observed-at",
                    "2026-09-07T12:00:00Z",
                    "--require-ready",
                ]
            ),
            2,
        )
        self.assertEqual(
            local_rehearsal.main(
                [
                    "--runtime-dir",
                    str(self.root / "network-soak"),
                    "--soak-iterations",
                    "3",
                    "--live-public",
                ]
            ),
            1,
        )


if __name__ == "__main__":
    unittest.main()
