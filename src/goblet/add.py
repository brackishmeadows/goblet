from __future__ import annotations

from .increment import increment
from .subtract import subtract
from .words import LARGE_NUMBER, ONE, UNKNOWN_NUMBER, SymbolicNumber, WordNumber, is_large_number, is_unknown_number, is_zero


def add(left: SymbolicNumber, right: SymbolicNumber) -> SymbolicNumber:
    if is_unknown_number(left) or is_unknown_number(right):
        return UNKNOWN_NUMBER
    if is_large_number(left) or is_large_number(right):
        return LARGE_NUMBER

    result = left
    countdown = right
    while not is_zero(countdown):
        result = increment(result)
        if is_large_number(result):
            return LARGE_NUMBER
        countdown = subtract(countdown, ONE)
    return result


def add_trace(left: WordNumber, right: WordNumber) -> tuple[SymbolicNumber, list[str]]:
    steps = []
    result: SymbolicNumber = left
    countdown = right
    while not is_zero(countdown):
        before = result
        result = increment(result)
        steps.append(
            f"{_render_for_trace(before)} plus one becomes {_render_for_trace(result)}"
        )
        if is_large_number(result):
            return LARGE_NUMBER, steps
        countdown = subtract(countdown, ONE)
    return result, steps


def _render_for_trace(value: SymbolicNumber) -> str:
    from .render import render_number

    return render_number(value)
