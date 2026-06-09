from __future__ import annotations

from .add import add
from .normalize import parse_number
from .render import render_number
from .subtract import subtract
from .words import LARGE_NUMBER, ONE, UNKNOWN_NUMBER, SymbolicNumber, WordNumber, ZERO, is_large_number, is_unknown_number, is_zero


def multiply(left: SymbolicNumber, right: SymbolicNumber) -> SymbolicNumber:
    if is_unknown_number(left) or is_unknown_number(right):
        return UNKNOWN_NUMBER
    if is_large_number(left) or is_large_number(right):
        return LARGE_NUMBER

    result: SymbolicNumber = ZERO
    countdown = right
    while not is_zero(countdown):
        result = add(result, left)
        if is_large_number(result):
            return LARGE_NUMBER
        countdown = subtract(countdown, ONE)
    return result


def multiply_expression(expression: str) -> str:
    left, right = parse_multiplication_expression(expression)
    return render_number(multiply(left, right))


def trace_multiply_expression(expression: str) -> list[str]:
    left, right = parse_multiplication_expression(expression)
    expression_text = f"{render_number(left)} times {render_number(right)}"
    result: SymbolicNumber = ZERO
    countdown = right
    step_count = ZERO
    steps = [expression_text]

    while not is_zero(countdown):
        before = result
        result = add(result, left)
        step_count = add(step_count, ONE)
        steps.append(
            f"{render_number(before)} plus {render_number(left)} becomes "
            f"{render_number(result)}; count becomes {render_number(step_count)}"
        )
        if is_large_number(result):
            steps.append(f"{expression_text} becomes a large number")
            return steps
        countdown = subtract(countdown, ONE)

    steps.append(f"{expression_text} becomes {render_number(result)}")
    return steps


def parse_multiplication_expression(expression: str) -> tuple[WordNumber, WordNumber]:
    lowered = expression.lower()
    if " multiplied by " in lowered:
        parts = lowered.split(" multiplied by ")
    else:
        parts = lowered.split(" times ")

    if len(parts) != 2:
        raise ValueError("expected '[number phrase] times [number phrase]'")
    return parse_number(parts[0]), parse_number(parts[1])
