"""Bounded arithmetic expression evaluation for the calculator example tool."""

from __future__ import annotations

import ast
import math
import operator
from collections.abc import Callable
from dataclasses import dataclass

MAX_EXPRESSION_LENGTH = 512
MAX_AST_NODES = 128
MAX_AST_DEPTH = 32
MAX_INTEGER_BITS = 1024
MAX_ABS_EXPONENT = 100
MAX_ABS_ROUND_DIGITS = 100


class CalculatorError(ValueError):
    """Raised when an expression is invalid, unsupported, or exceeds a bound."""


RealNumber = int | float


@dataclass(frozen=True)
class FunctionSpec:
    function: Callable[..., RealNumber]
    minimum_arguments: int
    maximum_arguments: int


_BINARY_OPERATORS: dict[type[ast.operator], Callable[[RealNumber, RealNumber], RealNumber]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
}
_UNARY_OPERATORS: dict[type[ast.unaryop], Callable[[RealNumber], RealNumber]] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}
_CONSTANTS: dict[str, float] = {
    "e": math.e,
    "pi": math.pi,
}
_FUNCTIONS: dict[str, FunctionSpec] = {
    "abs": FunctionSpec(abs, 1, 1),
    "cos": FunctionSpec(math.cos, 1, 1),
    "exp": FunctionSpec(math.exp, 1, 1),
    "log": FunctionSpec(math.log, 1, 2),
    "log10": FunctionSpec(math.log10, 1, 1),
    "pow": FunctionSpec(pow, 2, 2),
    "round": FunctionSpec(round, 1, 2),
    "sin": FunctionSpec(math.sin, 1, 1),
    "sqrt": FunctionSpec(math.sqrt, 1, 1),
    "tan": FunctionSpec(math.tan, 1, 1),
}


def _validate_number(value: object) -> RealNumber:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CalculatorError("calculation must produce a real number")
    if isinstance(value, int):
        if value.bit_length() > MAX_INTEGER_BITS:
            raise CalculatorError(
                f"integer exceeds the {MAX_INTEGER_BITS}-bit calculation limit"
            )
        return value
    if not math.isfinite(value):
        raise CalculatorError("calculation must produce a finite result")
    return value


def _validate_exponent(value: RealNumber) -> None:
    if abs(value) > MAX_ABS_EXPONENT:
        raise CalculatorError(
            f"exponent magnitude exceeds the limit of {MAX_ABS_EXPONENT}"
        )


def _validate_tree(tree: ast.AST) -> None:
    node_count = 0
    stack = [(tree, 1)]
    while stack:
        node, depth = stack.pop()
        node_count += 1
        if node_count > MAX_AST_NODES:
            raise CalculatorError(f"expression exceeds the {MAX_AST_NODES}-node limit")
        if depth > MAX_AST_DEPTH:
            raise CalculatorError(f"expression exceeds the depth limit of {MAX_AST_DEPTH}")
        stack.extend((child, depth + 1) for child in ast.iter_child_nodes(node))


def _call_function(name: str, arguments: list[RealNumber]) -> RealNumber:
    specification = _FUNCTIONS.get(name)
    if specification is None:
        raise CalculatorError(f"function is not allowed: {name}")

    argument_count = len(arguments)
    if not specification.minimum_arguments <= argument_count <= specification.maximum_arguments:
        if specification.minimum_arguments == specification.maximum_arguments:
            expected = str(specification.minimum_arguments)
        else:
            expected = (
                f"{specification.minimum_arguments} or {specification.maximum_arguments}"
            )
        raise CalculatorError(f"{name} expects {expected} argument(s)")

    if name == "pow":
        _validate_exponent(arguments[1])
    elif name == "round" and argument_count == 2:
        digits = arguments[1]
        if not isinstance(digits, int):
            raise CalculatorError("round precision must be an integer")
        if abs(digits) > MAX_ABS_ROUND_DIGITS:
            raise CalculatorError(
                f"round precision magnitude exceeds the limit of {MAX_ABS_ROUND_DIGITS}"
            )

    try:
        return _validate_number(specification.function(*arguments))
    except CalculatorError:
        raise
    except (ArithmeticError, TypeError, ValueError) as exc:
        raise CalculatorError(f"calculation failed: {exc}") from None


def _evaluate_node(node: ast.AST) -> RealNumber:
    if isinstance(node, ast.Constant):
        return _validate_number(node.value)

    if isinstance(node, ast.Name):
        try:
            return _CONSTANTS[node.id]
        except KeyError:
            raise CalculatorError(f"name is not allowed: {node.id}") from None

    if isinstance(node, ast.UnaryOp):
        operation = _UNARY_OPERATORS.get(type(node.op))
        if operation is None:
            raise CalculatorError(f"operator is not allowed: {type(node.op).__name__}")
        return _validate_number(operation(_evaluate_node(node.operand)))

    if isinstance(node, ast.BinOp):
        left = _evaluate_node(node.left)
        right = _evaluate_node(node.right)
        if isinstance(node.op, ast.Pow):
            _validate_exponent(right)
            operation = operator.pow
        else:
            operation = _BINARY_OPERATORS.get(type(node.op))
            if operation is None:
                raise CalculatorError(
                    f"operator is not allowed: {type(node.op).__name__}"
                )
        try:
            return _validate_number(operation(left, right))
        except CalculatorError:
            raise
        except (ArithmeticError, TypeError, ValueError) as exc:
            raise CalculatorError(f"calculation failed: {exc}") from None

    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise CalculatorError("only direct calls to allowed functions are supported")
        if node.keywords:
            raise CalculatorError("keyword arguments are not supported")
        arguments = [_evaluate_node(argument) for argument in node.args]
        return _call_function(node.func.id, arguments)

    raise CalculatorError(f"unsupported syntax: {type(node).__name__}")


def evaluate_expression(expression: str) -> RealNumber:
    """Evaluate a small allowlisted real-number expression.

    Supported syntax is numeric literals, parentheses, ``+``, ``-``, ``*``,
    ``/``, ``//``, ``%``, ``**``, unary signs, constants ``pi`` and ``e``, and
    the functions ``sqrt``, ``sin``, ``cos``, ``tan``, ``log``, ``log10``,
    ``exp``, ``pow``, ``abs``, and ``round``.
    """

    if not isinstance(expression, str):
        raise CalculatorError("expression must be a string")
    if not expression.strip():
        raise CalculatorError("expression must not be empty")
    if len(expression) > MAX_EXPRESSION_LENGTH:
        raise CalculatorError(
            f"expression exceeds the {MAX_EXPRESSION_LENGTH}-character limit"
        )

    try:
        tree = ast.parse(expression, mode="eval")
    except (MemoryError, RecursionError, SyntaxError, ValueError):
        raise CalculatorError("invalid expression syntax") from None

    _validate_tree(tree)
    try:
        return _validate_number(_evaluate_node(tree.body))
    except RecursionError:
        raise CalculatorError("expression exceeds the evaluation depth limit") from None
