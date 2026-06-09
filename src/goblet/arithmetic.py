from __future__ import annotations

from dataclasses import dataclass

from .add import add
from .compare import compare
from .fraction import (
    add_rationals,
    parse_rational,
    render_rational,
    subtract_rationals,
    trace_fraction_operation,
)
from .normalize import parse_number
from .render import render_number
from .subtract import subtract
from .words import LARGE_NUMBER, UNKNOWN_NUMBER, SymbolicNumber, WordNumber, ZERO, is_large_number, is_unknown_number


@dataclass(frozen=True)
class WholeInterval:
    lower: SymbolicNumber
    upper: SymbolicNumber
    condition: str | None = None


def arithmetic_expression(expression: str) -> str:
    left_text, operator, right_text = parse_arithmetic_expression(expression)
    if not is_bounded_text(left_text) and not is_bounded_text(right_text):
        left_rational = parse_rational(left_text)
        right_rational = parse_rational(right_text)
        if operator == "plus":
            return render_rational(add_rationals(left_rational, right_rational))
        if operator == "minus":
            return render_rational(subtract_rationals(left_rational, right_rational))

    left = parse_whole_interval(left_text)
    right = parse_whole_interval(right_text)
    if operator == "plus":
        return render_whole_interval(add_intervals(left, right))
    if operator == "minus":
        return render_whole_interval(subtract_intervals(left, right))
    raise ValueError(f"unsupported arithmetic operator: {operator}")


def trace_arithmetic_expression(expression: str) -> list[str]:
    left_text, operator, right_text = parse_arithmetic_expression(expression)
    if (
        not is_bounded_text(left_text)
        and not is_bounded_text(right_text)
        and (is_fraction_text(left_text) or is_fraction_text(right_text))
    ):
        return trace_fraction_operation(expression, operator, left_text, right_text)
    return [expression, arithmetic_expression(expression)]


def parse_arithmetic_expression(expression: str) -> tuple[str, str, str]:
    lowered = expression.lower()
    for marker, operator in ((" plus ", "plus"), (" minus ", "minus")):
        if marker in lowered:
            left, right = lowered.split(marker, 1)
            return left.strip(), operator, right.strip()
    raise ValueError("expected addition or subtraction expression")


def is_bounded_text(text: str) -> bool:
    return text.startswith("at least ") or text.startswith("at most ")


def is_fraction_text(text: str) -> bool:
    return " over " in text or " and " in text or any(
        text.endswith(f" {word}")
        for word in (
            "half",
            "halves",
            "third",
            "thirds",
            "quarter",
            "quarters",
            "fourth",
            "fourths",
            "fifth",
            "fifths",
            "sixth",
            "sixths",
            "seventh",
            "sevenths",
            "eighth",
            "eighths",
            "ninth",
            "ninths",
            "tenth",
            "tenths",
            "eleventh",
            "elevenths",
            "twelfth",
            "twelfths",
            "thirteenth",
            "thirteenths",
            "fourteenth",
            "fourteenths",
            "fifteenth",
            "fifteenths",
            "sixteenth",
            "sixteenths",
            "seventeenth",
            "seventeenths",
            "eighteenth",
            "eighteenths",
            "nineteenth",
            "nineteenths",
            "twentieth",
            "twentieths",
        )
    )


def parse_whole_interval(text: str) -> WholeInterval:
    if text.startswith("at least "):
        value = parse_number(text[len("at least ") :])
        if is_large_number(value):
            raise ValueError("lower bound has no supported finite values")
        return WholeInterval(value, LARGE_NUMBER)

    if text.startswith("at most "):
        value = parse_number(text[len("at most ") :])
        return WholeInterval(ZERO, value)

    value = parse_number(text)
    if is_unknown_number(value):
        return WholeInterval(UNKNOWN_NUMBER, UNKNOWN_NUMBER)
    if is_large_number(value):
        raise ValueError("unbounded value is not supported for public addition or subtraction")
    return WholeInterval(value, value)


def add_intervals(left: WholeInterval, right: WholeInterval) -> WholeInterval:
    if is_unknown_number(left.lower) or is_unknown_number(right.lower):
        return WholeInterval(UNKNOWN_NUMBER, UNKNOWN_NUMBER)
    lower = add(left.lower, right.lower)
    upper = add_upper_bounds(left.upper, right.upper)
    return WholeInterval(lower, upper, merge_conditions(left.condition, right.condition))


def subtract_intervals(left: WholeInterval, right: WholeInterval) -> WholeInterval:
    if is_unknown_number(left.lower) or is_unknown_number(right.lower):
        return WholeInterval(UNKNOWN_NUMBER, UNKNOWN_NUMBER)
    if is_large_number(right.upper):
        raise ValueError("cannot subtract an unbounded symbolic value")
    if not is_large_number(left.upper) and compare(left.upper, right.lower) == "less":
        raise ValueError("subtraction would be less than zero")

    condition = merge_conditions(left.condition, right.condition)
    if compare(left.lower, right.upper) == "less":
        lower = ZERO
        if is_exact_whole_interval(right):
            condition_text = f"the left value is at least {render_number(right.upper)}"
        else:
            condition_text = "the left value is at least the right value"
        condition = merge_conditions(
            condition,
            condition_text,
        )
    else:
        lower = subtract(left.lower, right.upper)

    if is_large_number(left.upper):
        upper: SymbolicNumber = LARGE_NUMBER
    else:
        upper = subtract(left.upper, right.lower)

    return WholeInterval(lower, upper, condition)


def add_upper_bounds(left: SymbolicNumber, right: SymbolicNumber) -> SymbolicNumber:
    if is_large_number(left) or is_large_number(right):
        return LARGE_NUMBER
    return add(left, right)


def render_whole_interval(value: WholeInterval) -> str:
    if is_unknown_number(value.lower) or is_unknown_number(value.upper):
        rendered = "an unknown number"
    elif is_large_number(value.lower):
        rendered = "a large number"
    elif not is_large_number(value.upper) and value.lower == value.upper:
        rendered = render_number(value.lower)
    elif is_large_number(value.upper) and value.lower == ZERO:
        rendered = "at most a large number"
    elif value.lower == ZERO:
        rendered = f"at most {render_number(value.upper)}"
    elif is_large_number(value.upper):
        rendered = f"at least {render_number(value.lower)}"
    else:
        rendered = f"at least {render_number(value.lower)} and at most {render_number(value.upper)}"

    if value.condition:
        return f"{rendered} when {value.condition}"
    return rendered


def merge_conditions(left: str | None, right: str | None) -> str | None:
    if left and right:
        return f"{left} and {right}"
    return left or right


def is_exact_whole_interval(value: WholeInterval) -> bool:
    return not is_large_number(value.upper) and value.lower == value.upper
