"""Deterministic tests for the bounded example calculator."""

from __future__ import annotations

import ast
import importlib.util
import json
import math
import sys
import unittest
from pathlib import Path
from types import ModuleType

CALCULATOR_PATH = (
    Path(__file__).resolve().parents[1]
    / "reasoning_trace_optimizer/calculator.py"
)


def _load_calculator() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "interleaved_thinking_calculator",
        CALCULATOR_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load calculator at {CALCULATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


calculator = _load_calculator()
MAX_EXPRESSION_LENGTH = calculator.MAX_EXPRESSION_LENGTH
CalculatorError = calculator.CalculatorError
evaluate_expression = calculator.evaluate_expression


class CalculatorTests(unittest.TestCase):
    def test_example_wires_the_bounded_evaluator_without_eval(self) -> None:
        example = CALCULATOR_PATH.parent.parent / "examples/03_full_optimization.py"
        tree = ast.parse(example.read_text(encoding="utf-8"))
        imports = [node for node in tree.body if isinstance(node, ast.ImportFrom)
                   and node.module == "reasoning_trace_optimizer.calculator"]
        self.assertEqual(len(imports), 1)
        self.assertEqual({name.name for name in imports[0].names},
                         {"CalculatorError", "evaluate_expression"})
        executor = next(node for node in tree.body
                        if isinstance(node, ast.FunctionDef) and node.name == "execute_tool")
        calls = {node.func.id for node in ast.walk(executor)
                 if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
        self.assertIn("evaluate_expression", calls)
        self.assertNotIn("eval", calls)

    def test_actual_example_calculator_branch_rejects_object_access(self) -> None:
        # Compile only this reviewed function. Importing the full example would
        # load .env and provider dependencies, neither needed for arithmetic.
        example = CALCULATOR_PATH.parent.parent / "examples/03_full_optimization.py"
        tree = ast.parse(example.read_text(encoding="utf-8"))
        executor = next(node for node in tree.body
                        if isinstance(node, ast.FunctionDef) and node.name == "execute_tool")
        module = ast.Module(body=[executor], type_ignores=[])
        namespace = {"json": json, "evaluate_expression": evaluate_expression,
                     "CalculatorError": CalculatorError}
        exec(compile(module, str(example), "exec"), namespace)
        execute_tool = namespace["execute_tool"]
        valid = json.loads(execute_tool("calculator", {"expression": "sqrt(16) + 2"}))
        self.assertEqual(valid["status"], "success")
        self.assertEqual(valid["result"], 6)
        rejected = json.loads(execute_tool("calculator", {"expression": "().__class__.__name__"}))
        self.assertEqual(rejected["status"], "error")
        self.assertNotIn("result", rejected)

    def test_arithmetic_precedence_and_numeric_operators(self) -> None:
        self.assertEqual(evaluate_expression("2 + 3 * 4"), 14)
        self.assertEqual(evaluate_expression("17 // 5 + 17 % 5"), 5)
        self.assertEqual(evaluate_expression("-(2 ** 3) + +10"), 2)
        self.assertAlmostEqual(evaluate_expression("7 / 2"), 3.5)

    def test_json_representable_invalid_parser_strings_are_typed(self) -> None:
        for document in ('"\\u0000"', '"\\ud800"'):
            with self.subTest(document=document):
                expression = json.loads(document)
                with self.assertRaisesRegex(CalculatorError, "invalid expression syntax"):
                    evaluate_expression(expression)

    def test_actual_example_calculator_branch_handles_invalid_parser_strings(self) -> None:
        # Only the reviewed tool function is compiled, never the provider setup.
        example = CALCULATOR_PATH.parent.parent / "examples/03_full_optimization.py"
        tree = ast.parse(example.read_text(encoding="utf-8"))
        executor = next(node for node in tree.body
                        if isinstance(node, ast.FunctionDef) and node.name == "execute_tool")
        namespace = {"json": json, "evaluate_expression": evaluate_expression,
                     "CalculatorError": CalculatorError}
        exec(compile(ast.Module(body=[executor], type_ignores=[]), str(example), "exec"),
             namespace)
        for document in ('{"expression":"\\u0000"}', '{"expression":"\\ud800"}'):
            with self.subTest(document=document):
                response = namespace["execute_tool"]("calculator", json.loads(document))
                result = json.loads(response)
                self.assertEqual(result["status"], "error")
                self.assertEqual(result["error"], "invalid expression syntax")
                self.assertNotIn("result", result)

    def test_documented_functions_and_constants(self) -> None:
        expression = "round(sqrt(16) + sin(pi / 2) + log(8, 2), 2)"
        self.assertEqual(evaluate_expression(expression), 8.0)
        self.assertAlmostEqual(evaluate_expression("cos(0) + log10(100)"), 3.0)
        self.assertAlmostEqual(evaluate_expression("tan(0) + abs(-e)"), math.e)
        self.assertAlmostEqual(evaluate_expression("exp(1)"), math.e)
        self.assertEqual(evaluate_expression("pow(2, 10)"), 1024)

    def test_non_string_empty_and_invalid_syntax_are_rejected(self) -> None:
        cases = [None, 4, True, [], {}]
        for expression in cases:
            with self.subTest(expression=expression):
                with self.assertRaisesRegex(CalculatorError, "expression must be a string"):
                    evaluate_expression(expression)  # type: ignore[arg-type]

        for expression in ("", "   ", "2 +"):
            with self.subTest(expression=expression):
                with self.assertRaises(CalculatorError):
                    evaluate_expression(expression)

    def test_python_object_and_execution_escape_syntax_is_rejected(self) -> None:
        attacks = [
            "().__class__.__bases__",
            "pi.__class__",
            "[1][0]",
            "[item for item in (1, 2)]",
            "(item for item in (1, 2))",
            "lambda: 1",
            "__import__('os').system('id')",
            "open('/etc/passwd').read()",
            "sqrt.__call__(4)",
            "(1 if True else 2)",
            "(x := 1)",
            "1 < 2",
            "1 << 2",
            "{'value': 1}",
        ]
        for expression in attacks:
            with self.subTest(expression=expression):
                with self.assertRaises(CalculatorError):
                    evaluate_expression(expression)

    def test_calls_are_direct_positional_and_allowlisted(self) -> None:
        attacks = [
            "min(1, 2)",
            "math.sqrt(4)",
            "round(number=1)",
            "pow(2, 3, 5)",
            "sqrt()",
            "log(1, 2, 3)",
        ]
        for expression in attacks:
            with self.subTest(expression=expression):
                with self.assertRaises(CalculatorError):
                    evaluate_expression(expression)

    def test_booleans_complex_and_non_finite_values_are_rejected(self) -> None:
        expressions = [
            "True",
            "False + 1",
            "1j",
            "1e309",
            "1e308 * 1e308",
            "pow(-1, 0.5)",
            "sqrt(-1)",
            "exp(1000)",
        ]
        for expression in expressions:
            with self.subTest(expression=expression):
                with self.assertRaises(CalculatorError):
                    evaluate_expression(expression)

    def test_size_depth_and_integer_growth_limits(self) -> None:
        oversized = "1" * (MAX_EXPRESSION_LENGTH + 1)
        too_deep = "+".join("1" for _ in range(40))
        balanced_terms = ["1"] * 44
        while len(balanced_terms) > 1:
            balanced_terms = [
                f"({balanced_terms[index]} + {balanced_terms[index + 1]})"
                if index + 1 < len(balanced_terms)
                else balanced_terms[index]
                for index in range(0, len(balanced_terms), 2)
            ]
        too_many_nodes = balanced_terms[0]
        huge_literal = "9" * 400
        # Each operand is below the integer limit; only the product exceeds it.
        huge_product = f"{'9' * 160} * {'9' * 160}"

        for expression in (
            oversized,
            too_deep,
            too_many_nodes,
            huge_literal,
            huge_product,
        ):
            with self.subTest(expression=expression[:40]):
                with self.assertRaises(CalculatorError):
                    evaluate_expression(expression)

    def test_resource_exhaustion_exponents_are_rejected(self) -> None:
        expressions = [
            "10 ** 101",
            "10 ** -101",
            "pow(10, 101)",
            "pow(10, -101)",
            "round(1.25, 101)",
            "round(1.25, -101)",
        ]
        for expression in expressions:
            with self.subTest(expression=expression):
                with self.assertRaises(CalculatorError):
                    evaluate_expression(expression)

    def test_arithmetic_failures_are_typed(self) -> None:
        for expression in ("1 / 0", "0 ** -1", "log(0)"):
            with self.subTest(expression=expression):
                with self.assertRaisesRegex(CalculatorError, "calculation failed"):
                    evaluate_expression(expression)


if __name__ == "__main__":
    unittest.main()
