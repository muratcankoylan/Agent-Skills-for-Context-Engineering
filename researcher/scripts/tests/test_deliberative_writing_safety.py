"""Run PR132 safety scenarios in isolated, credential-free Python children.

The root suite needs no pytest, installed example, or provider dependencies.
Example imports and sys.path changes happen only in children, not test discovery.
"""
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = Path(__file__).resolve()
EXAMPLE = ROOT / "examples/deliberative-writing-loop"


def _command(role, argument):
    return [sys.executable, "-I", "-B", str(SCRIPT), role, str(argument)]


def _environment():
    # Do not inherit keys, proxy settings, Python paths, or user configuration.
    return {"PATH": os.defpath, "LANG": "C", "LC_ALL": "C"}


class DeliberativeWritingSafetyTests(unittest.TestCase):
    def _run(self, scenario):
        before_path = tuple(sys.path)
        before_modules = {key for key in sys.modules if key == "dwl" or key.startswith("dwl.")}
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                _command("--scenario", scenario), cwd=directory, env=_environment(),
                capture_output=True, text=True, timeout=30, check=False,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(tuple(sys.path), before_path)
        self.assertEqual(
            {key for key in sys.modules if key == "dwl" or key.startswith("dwl.")}, before_modules,
        )

    def test_unsettled_liability_counts_before_effect(self):
        self._run("liability")

    def test_nonfinite_and_invalid_caps_refused(self):
        self._run("invalid_caps")

    def test_unknown_reservations_survive_restart(self):
        self._run("restart")

    def test_cooperating_processes_share_admission(self):
        self._run("concurrent")

    def test_process_death_prevents_automatic_replay(self):
        self._run("crash")

    def test_completion_receipt_failure_prevents_replay(self):
        self._run("receipt_failure")

    def test_changed_inputs_cannot_reuse_completed_cell(self):
        self._run("cache_identity")

    def test_paid_adapters_refuse_before_socket_or_admission(self):
        self._run("paid_refusal")


def _child(role, argument):
    # This function is never called during root unittest import/discovery.
    sys.path.insert(0, str(EXAMPLE / "src"))
    from dwl.adapters.base import Budget, BudgetExceeded, LiveExecutionDisabled, MockAdapter
    from dwl.state import run_once

    if role == "--reserve":
        budget = Budget(max_calls=10, max_usd=.003, ledger_path=Path(argument))
        for _ in range(20):
            try:
                budget.charge("openai", 100, 0)
            except BudgetExceeded:
                break
        return
    if role == "--crash":
        run_once(Path(argument), {"task": "crash-witness"}, lambda: os._exit(19))
        raise AssertionError("crash fixture unexpectedly returned")
    if role != "--scenario":
        raise ValueError("unknown child role")

    check = unittest.TestCase()
    if argument == "liability":
        budget = Budget(max_calls=20, max_usd=.001)
        for _ in range(3):
            budget.charge("openai", 100, 0)
        with check.assertRaises(BudgetExceeded):
            budget.charge("openai", 100, 0)
        check.assertEqual(budget.summary()["liability_microusd"], 900)
        check.assertEqual(budget.summary()["unknown_calls"], 3)
    elif argument == "invalid_caps":
        for value in [float("nan"), float("inf"), -float("inf"), -1, True]:
            with check.assertRaises(ValueError):
                Budget(max_usd=value)
        for value in [True, 1.0, -1, 10001]:
            with check.assertRaises(ValueError):
                Budget(max_calls=value)
    elif argument == "restart":
        path = Path.cwd() / "budget.json"
        original = Budget(max_calls=2, max_usd=.0006, ledger_path=path)
        original.charge("openai", 100, 0)
        restarted = Budget(max_calls=2, max_usd=.0006, ledger_path=path)
        restarted.charge("openai", 100, 0)
        third = Budget(max_calls=2, max_usd=.0006, ledger_path=path)
        check.assertEqual(third.summary()["liability_microusd"], 600)
        check.assertEqual(third.summary()["unknown_calls"], 2)
        with check.assertRaises(BudgetExceeded):
            third.charge("openai", 100, 0)
        with check.assertRaises(ValueError):
            Budget(max_calls=3, max_usd=.0006, ledger_path=path)
    elif argument == "concurrent":
        path = Path.cwd() / "budget.json"
        workers = []
        try:
            for _ in range(4):
                workers.append(subprocess.Popen(
                    _command("--reserve", path), cwd=Path.cwd(), env=_environment(),
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                ))
            for worker in workers:
                stdout, stderr = worker.communicate(timeout=10)
                check.assertEqual(worker.returncode, 0, stdout + stderr)
        finally:
            for worker in workers:
                if worker.poll() is None:
                    worker.kill()
                worker.communicate()
        budget = Budget(max_calls=10, max_usd=.003, ledger_path=path)
        check.assertEqual(budget.summary()["calls"], 10)
        check.assertEqual(budget.summary()["liability_microusd"], 3000)
    elif argument == "crash":
        path = Path.cwd() / "operation.json"
        result = subprocess.run(
            _command("--crash", path), cwd=Path.cwd(), env=_environment(),
            capture_output=True, text=True, timeout=10, check=False,
        )
        check.assertEqual(result.returncode, 19, result.stdout + result.stderr)
        attempted = []
        with check.assertRaises(RuntimeError):
            run_once(path, {"task": "crash-witness"}, lambda: attempted.append(True))
        check.assertEqual(attempted, [])
    elif argument == "receipt_failure":
        from unittest.mock import patch
        import dwl.state as state
        path = Path.cwd() / "operation.json"
        original_write = state.atomic_json
        def fail_completion(destination, value):
            if value["status"] == "completed":
                raise OSError("injected receipt failure")
            return original_write(destination, value)
        attempted = []
        with patch.object(state, "atomic_json", fail_completion), check.assertRaises(OSError):
            run_once(path, {"task": "write-failure"}, lambda: attempted.append(True))
        with check.assertRaises(RuntimeError):
            run_once(path, {"task": "write-failure"}, lambda: attempted.append(True))
        check.assertEqual(attempted, [True])
    elif argument == "cache_identity":
        from dwl.benchmark import BenchItem, run_item
        from dwl.persona import compile_persona
        persona = compile_persona("sample", EXAMPLE / "personas/sample-essayist/corpus")
        item = BenchItem("same-id", "Original brief.", "sample", "oneshot", "mock")
        results = Path.cwd() / "results"
        first = run_item(item, MockAdapter(["The ledger never lies."]), persona, results, 100)
        identical = MockAdapter(["This must not execute."])
        check.assertEqual(run_item(item, identical, persona, results, 100), first)
        changed = BenchItem("same-id", "Changed brief.", "sample", "oneshot", "mock")
        with check.assertRaises(ValueError):
            run_item(changed, identical, persona, results, 100)
        with check.assertRaises(ValueError):
            run_item(item, identical, persona, results, 999)
        identical.model = "changed-model"
        with check.assertRaises(ValueError):
            run_item(item, identical, persona, results, 100)
        check.assertEqual(identical.calls, [])
    elif argument == "paid_refusal":
        from unittest.mock import patch
        from dwl.adapters.openai import OpenAIAdapter
        from dwl.adapters.anthropic import AnthropicAdapter
        from dwl.adapters.pangram import PangramClient
        with patch("socket.socket", side_effect=AssertionError("unexpected network")):
            for kind in [OpenAIAdapter, AnthropicAdapter]:
                budget = Budget(max_calls=10, max_usd=1)
                with patch.dict(os.environ, {"OPENAI_API_KEY": "fake", "ANTHROPIC_API_KEY": "fake"}):
                    adapter = kind(budget=budget)
                    with check.assertRaises(LiveExecutionDisabled):
                        adapter.complete("system", "user")
                check.assertEqual(budget.calls, 0)
            detector = PangramClient(enabled=True)
            check.assertFalse(detector.available)
            with check.assertRaises(LiveExecutionDisabled):
                detector.score("A harmless fixture.")
    else:
        raise ValueError("unknown safety scenario")


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] in {"--scenario", "--reserve", "--crash"}:
        _child(sys.argv[1], sys.argv[2])
    else:
        unittest.main()
