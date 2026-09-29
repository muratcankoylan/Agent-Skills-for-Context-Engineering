"""Deterministic tests for paid-call budgeting in the example package."""

from __future__ import annotations

import ast
import importlib.util
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import ModuleType, SimpleNamespace

EXAMPLE_ROOT = Path(__file__).resolve().parents[1]
BUDGET_PATH = EXAMPLE_ROOT / "reasoning_trace_optimizer/api_budget.py"
PAID_CALL_MODULES = {
    "analyzer.py": 2,
    "capture.py": 2,
    "optimizer.py": 2,
    "skill_generator.py": 1,
}


def _load_budget_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "interleaved_thinking_api_budget",
        BUDGET_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load API budget at {BUDGET_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


budget_module = _load_budget_module()
PaidAPIBudget = budget_module.PaidAPIBudget
PaidAPIAccountingError = budget_module.PaidAPIAccountingError
PaidAPIBudgetExceededError = budget_module.PaidAPIBudgetExceededError
PaidAPIDryRunError = budget_module.PaidAPIDryRunError


def _response(input_tokens: object = 3, output_tokens: object = 4) -> object:
    return SimpleNamespace(
        usage=SimpleNamespace(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
    )


def _dotted_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _dotted_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


class PaidAPIBudgetTests(unittest.TestCase):
    def test_reservation_precedes_call_and_success_records_usage(self) -> None:
        api_budget = PaidAPIBudget(
            max_api_attempts=2,
            max_reserved_output_tokens=20,
        )

        with api_budget.attempt("capture", 10) as attempt:
            self.assertEqual(api_budget.records[0].status, "reserved")
            self.assertEqual(api_budget.reserved_output_tokens, 10)
            attempt.record_usage(_response(input_tokens=7, output_tokens=8))

        self.assertEqual(api_budget.records[0].status, "succeeded")
        self.assertEqual(api_budget.reported_input_tokens, 7)
        self.assertEqual(api_budget.reported_output_tokens, 8)

    def test_attempt_cap_blocks_before_caller_body(self) -> None:
        api_budget = PaidAPIBudget(
            max_api_attempts=1,
            max_reserved_output_tokens=20,
        )
        invoked = 0

        def invoke() -> None:
            nonlocal invoked
            with api_budget.attempt("analyze", 10) as attempt:
                invoked += 1
                attempt.record_usage(_response())

        invoke()
        with self.assertRaises(PaidAPIBudgetExceededError):
            invoke()
        self.assertEqual(invoked, 1)
        self.assertEqual(len(api_budget.records), 1)

    def test_output_reservation_cap_is_cumulative_and_never_refunded(self) -> None:
        api_budget = PaidAPIBudget(
            max_api_attempts=3,
            max_reserved_output_tokens=10,
        )

        with self.assertRaises(TimeoutError):
            with api_budget.attempt("capture", 6):
                raise TimeoutError("provider outcome is unknown")

        with self.assertRaises(PaidAPIBudgetExceededError):
            with api_budget.attempt("retry", 5):
                self.fail("reservation failure must precede the caller body")

        self.assertEqual(api_budget.reserved_output_tokens, 6)
        self.assertEqual(api_budget.records[0].status, "failed_charge_unknown")

    def test_retry_and_multi_call_pair_receive_distinct_attempt_records(self) -> None:
        api_budget = PaidAPIBudget(
            max_api_attempts=3,
            max_reserved_output_tokens=30,
        )

        with self.assertRaises(ConnectionError):
            with api_budget.attempt("capture", 10):
                raise ConnectionError("retryable in the external harness")
        with api_budget.attempt("capture", 10) as retry:
            retry.record_usage(_response())
        with api_budget.attempt("analyze", 10) as paired_call:
            paired_call.record_usage(_response())

        self.assertEqual(
            [record.operation for record in api_budget.records],
            ["capture", "capture", "analyze"],
        )
        self.assertEqual(
            [record.status for record in api_budget.records],
            ["failed_charge_unknown", "succeeded", "succeeded"],
        )

    def test_dry_run_blocks_before_body_and_is_explicitly_non_evidence(self) -> None:
        api_budget = PaidAPIBudget(
            max_api_attempts=1,
            max_reserved_output_tokens=10,
            dry_run=True,
        )
        invoked = False

        with self.assertRaises(PaidAPIDryRunError) as raised:
            with api_budget.attempt("capture", 10):
                invoked = True

        self.assertFalse(invoked)
        self.assertFalse(raised.exception.is_evidence)
        self.assertEqual(api_budget.records, ())

    def test_unknown_malformed_and_over_reserved_usage_fail_closed(self) -> None:
        unknown = PaidAPIBudget(
            max_api_attempts=1,
            max_reserved_output_tokens=10,
        )
        with self.assertRaises(PaidAPIAccountingError):
            with unknown.attempt("unknown-usage", 10):
                pass
        self.assertEqual(unknown.records[0].status, "succeeded_usage_unknown")

        missing_usage = PaidAPIBudget(
            max_api_attempts=1,
            max_reserved_output_tokens=10,
        )
        with self.assertRaises(PaidAPIAccountingError):
            with missing_usage.attempt("missing-usage", 10) as attempt:
                attempt.record_usage(SimpleNamespace(usage=None))
        self.assertEqual(
            missing_usage.records[0].status,
            "succeeded_usage_unknown",
        )

        malformed = PaidAPIBudget(
            max_api_attempts=1,
            max_reserved_output_tokens=10,
        )
        with self.assertRaises(PaidAPIAccountingError):
            with malformed.attempt("malformed-usage", 10) as attempt:
                attempt.record_usage(_response(input_tokens=True))
        self.assertEqual(malformed.records[0].status, "failed_charge_unknown")

        over_reserved = PaidAPIBudget(
            max_api_attempts=1,
            max_reserved_output_tokens=10,
        )
        with self.assertRaises(PaidAPIAccountingError):
            with over_reserved.attempt("over-reserved", 5) as attempt:
                attempt.record_usage(_response(output_tokens=6))
        self.assertEqual(
            over_reserved.records[0].status,
            "succeeded_over_reservation",
        )

    def test_caps_reject_boolean_non_integer_and_non_positive_values(self) -> None:
        for value in (True, False, 0, -1, 1.5, "1", None):
            with self.subTest(field="max_api_attempts", value=value):
                with self.assertRaises(ValueError):
                    PaidAPIBudget(
                        max_api_attempts=value,
                        max_reserved_output_tokens=1,
                    )
            with self.subTest(field="max_reserved_output_tokens", value=value):
                with self.assertRaises(ValueError):
                    PaidAPIBudget(
                        max_api_attempts=1,
                        max_reserved_output_tokens=value,
                    )

    def test_concurrent_reservations_cannot_oversubscribe_cap(self) -> None:
        api_budget = PaidAPIBudget(
            max_api_attempts=8,
            max_reserved_output_tokens=8,
        )

        def reserve(_: int) -> bool:
            try:
                with api_budget.attempt("parallel", 1) as attempt:
                    attempt.record_usage(_response(input_tokens=0, output_tokens=1))
                return True
            except PaidAPIBudgetExceededError:
                return False

        with ThreadPoolExecutor(max_workers=16) as executor:
            accepted = list(executor.map(reserve, range(32)))

        self.assertEqual(sum(accepted), 8)
        self.assertEqual(len(api_budget.records), 8)
        self.assertEqual(api_budget.reserved_output_tokens, 8)


class PaidCallRoutingTests(unittest.TestCase):
    def test_every_sdk_call_is_nested_under_attempt_reservation(self) -> None:
        package_root = EXAMPLE_ROOT / "reasoning_trace_optimizer"
        for filename, expected_calls in PAID_CALL_MODULES.items():
            with self.subTest(filename=filename):
                tree = ast.parse((package_root / filename).read_text(encoding="utf-8"))
                parents: dict[ast.AST, ast.AST] = {}
                for parent in ast.walk(tree):
                    for child in ast.iter_child_nodes(parent):
                        parents[child] = parent

                sdk_calls = [
                    node
                    for node in ast.walk(tree)
                    if isinstance(node, ast.Call)
                    and _dotted_name(node.func)
                    in {"self._client.messages.create", "self._client.messages.stream"}
                ]
                self.assertEqual(len(sdk_calls), expected_calls)

                for sdk_call in sdk_calls:
                    ancestor = parents.get(sdk_call)
                    guarded = False
                    while ancestor is not None:
                        if isinstance(ancestor, ast.With):
                            guarded = any(
                                isinstance(item.context_expr, ast.Call)
                                and _dotted_name(item.context_expr.func)
                                == "self.api_budget.attempt"
                                for item in ancestor.items
                            )
                            if guarded:
                                break
                        ancestor = parents.get(ancestor)
                    self.assertTrue(
                        guarded,
                        f"unguarded SDK call in {filename}:{sdk_call.lineno}",
                    )

    def test_sdk_automatic_retries_are_disabled_at_every_client_boundary(self) -> None:
        package_root = EXAMPLE_ROOT / "reasoning_trace_optimizer"
        for filename in PAID_CALL_MODULES:
            with self.subTest(filename=filename):
                tree = ast.parse((package_root / filename).read_text(encoding="utf-8"))
                constructors = [
                    node
                    for node in ast.walk(tree)
                    if isinstance(node, ast.Call)
                    and _dotted_name(node.func) == "anthropic.Anthropic"
                ]
                self.assertEqual(len(constructors), 1)
                retry_keywords = [
                    keyword
                    for keyword in constructors[0].keywords
                    if keyword.arg == "max_retries"
                ]
                self.assertEqual(len(retry_keywords), 1)
                self.assertIsInstance(retry_keywords[0].value, ast.Constant)
                self.assertEqual(retry_keywords[0].value.value, 0)

    def test_loop_and_cli_share_one_budget_across_multi_call_workflows(self) -> None:
        package_root = EXAMPLE_ROOT / "reasoning_trace_optimizer"
        loop_source = (package_root / "loop.py").read_text(encoding="utf-8")
        cli_source = (package_root / "cli.py").read_text(encoding="utf-8")
        full_example_source = (
            EXAMPLE_ROOT / "examples/03_full_optimization.py"
        ).read_text(encoding="utf-8")

        self.assertIn('"api_budget": self.api_budget', loop_source)
        self.assertEqual(cli_source.count("api_budget=api_budget"), 6)
        self.assertIn("raise SystemExit(3) from None", cli_source)
        self.assertEqual(full_example_source.count("api_budget=api_budget"), 2)
        self.assertEqual(full_example_source.count("api_budget = PaidAPIBudget("), 1)


if __name__ == "__main__":
    unittest.main()
