from __future__ import annotations

from dataclasses import dataclass

from .add import add
from .compare import compare
from .divide import divide, parse_division_expression, quotient_and_remainder, reduce_fraction
from .multiply import multiply
from .normalize import parse_number
from .render import render_fraction, render_mixed, render_number
from .subtract import subtract
from .words import ONE, ORDINAL_SPECIAL, SymbolicNumber, WordNumber, ZERO, is_large_number


@dataclass(frozen=True)
class Rational:
    numerator: SymbolicNumber
    denominator: SymbolicNumber


ORDINAL_TO_CARDINAL = {ordinal: cardinal for cardinal, ordinal in ORDINAL_SPECIAL.items()}
ORDINAL_TO_CARDINAL["quarter"] = "four"
ORDINAL_TO_CARDINAL["quarters"] = "four"
ORDINAL_TO_CARDINAL["halves"] = "two"


def parse_rational(text: str) -> Rational:
    cleaned = text.lower().strip()
    if " divided by " in cleaned:
        dividend, divisor = parse_division_expression(cleaned)
        if is_large_number(dividend) or is_large_number(divisor):
            raise ValueError("bounded division is not supported inside fraction arithmetic")
        quotient, numerator, denominator = divide(dividend, divisor)
        return rational_from_mixed(quotient, numerator, denominator)

    try:
        value = parse_number(cleaned)
        if is_large_number(value):
            raise ValueError("unbounded value is not supported inside fraction arithmetic")
        return Rational(value, ONE)
    except ValueError:
        pass

    if " over " in cleaned:
        return parse_fraction(cleaned)

    if " and " in cleaned:
        whole_text, fraction_text = cleaned.split(" and ", 1)
        whole = parse_number(whole_text)
        if is_large_number(whole):
            raise ValueError("unbounded mixed number is not supported")
        fraction = parse_fraction(fraction_text)
        return rational_from_mixed(whole, fraction.numerator, fraction.denominator)

    return parse_fraction(cleaned)


def parse_fraction(text: str) -> Rational:
    if " over " in text:
        numerator_text, denominator_text = text.split(" over ", 1)
        numerator = parse_number(numerator_text)
        denominator = parse_number(denominator_text)
        if is_large_number(numerator) or is_large_number(denominator):
            raise ValueError("unbounded fraction is not supported")
        return Rational(numerator, denominator)

    tokens = text.split()
    if len(tokens) < 2:
        raise ValueError(f"unsupported fraction phrase: {text}")

    numerator_text = " ".join(tokens[:-1])
    denominator_text = denominator_cardinal(tokens[-1])
    numerator = parse_number(numerator_text)
    denominator = parse_number(denominator_text)
    if is_large_number(numerator) or is_large_number(denominator):
        raise ValueError("unbounded fraction is not supported")
    return Rational(numerator, denominator)


def denominator_cardinal(ordinal: str) -> str:
    singular = ordinal[:-1] if ordinal.endswith("s") else ordinal
    if ordinal in ORDINAL_TO_CARDINAL:
        return ORDINAL_TO_CARDINAL[ordinal]
    if singular in ORDINAL_TO_CARDINAL:
        return ORDINAL_TO_CARDINAL[singular]
    raise ValueError(f"unsupported fraction denominator: {ordinal}")


def add_rationals(left: Rational, right: Rational) -> Rational:
    left_scaled = multiply(left.numerator, right.denominator)
    right_scaled = multiply(right.numerator, left.denominator)
    numerator = add(left_scaled, right_scaled)
    denominator = multiply(left.denominator, right.denominator)
    return reduce_rational(Rational(numerator, denominator))


def subtract_rationals(left: Rational, right: Rational) -> Rational:
    left_scaled = multiply(left.numerator, right.denominator)
    right_scaled = multiply(right.numerator, left.denominator)
    if is_large_number(left_scaled) or is_large_number(right_scaled):
        return Rational(left_scaled, multiply(left.denominator, right.denominator))
    if compare(left_scaled, right_scaled) == "less":
        raise ValueError("subtraction would be less than zero")
    numerator = subtract(left_scaled, right_scaled)
    denominator = multiply(left.denominator, right.denominator)
    return reduce_rational(Rational(numerator, denominator))


def reduce_rational(value: Rational) -> Rational:
    if is_large_number(value.numerator) or is_large_number(value.denominator):
        return value
    numerator, denominator = reduce_fraction(value.numerator, value.denominator)
    return Rational(numerator, denominator)


def render_rational(value: Rational) -> str:
    if is_large_number(value.numerator) and value.denominator == ONE:
        return "a large number"
    if is_large_number(value.numerator) or is_large_number(value.denominator):
        return "an unknown number"
    quotient, remainder = quotient_and_remainder(value.numerator, value.denominator)
    return render_mixed(quotient, remainder, value.denominator)


def trace_fraction_operation(expression: str, operator: str, left_text: str, right_text: str) -> list[str]:
    left = parse_rational(left_text)
    right = parse_rational(right_text)
    steps = [expression]

    shared_denominator = multiply(left.denominator, right.denominator)
    left_scaled = multiply(left.numerator, right.denominator)
    right_scaled = multiply(right.numerator, left.denominator)

    steps.extend(
        rewrite_steps(
            left,
            left_scaled,
            right.denominator,
            shared_denominator,
            left_text,
        )
    )
    steps.extend(
        rewrite_steps(
            right,
            right_scaled,
            left.denominator,
            shared_denominator,
            right_text,
        )
    )

    if is_large_number(shared_denominator) or is_large_number(left_scaled) or is_large_number(right_scaled):
        steps.append("the shared-denominator rewrite overflowed the supported ceiling")
        steps.append("the exact ratio cannot be placed")
        steps.append(f"{expression} becomes an unknown number")
        return steps

    if operator == "plus":
        numerator = add(left_scaled, right_scaled)
        steps.append(
            f"{render_fraction(left_scaled, shared_denominator)} plus "
            f"{render_fraction(right_scaled, shared_denominator)} becomes "
            f"{render_fraction(numerator, shared_denominator)}"
        )
        result = reduce_rational(Rational(numerator, shared_denominator))
    else:
        if compare(left_scaled, right_scaled) == "less":
            raise ValueError("subtraction would be less than zero")
        numerator = subtract(left_scaled, right_scaled)
        steps.append(
            f"{render_fraction(left_scaled, shared_denominator)} minus "
            f"{render_fraction(right_scaled, shared_denominator)} becomes "
            f"{render_fraction(numerator, shared_denominator)}"
        )
        result = reduce_rational(Rational(numerator, shared_denominator))

    unreduced = Rational(numerator, shared_denominator)
    if result == unreduced:
        steps.append(f"{render_rational(result)} is already reduced")
    else:
        steps.append(f"{render_rational(unreduced)} reduces to {render_rational(result)}")
    steps.append(f"{expression} becomes {render_rational(result)}")
    return steps


def rewrite_steps(
    value: Rational,
    scaled_numerator: SymbolicNumber,
    scale: SymbolicNumber,
    shared_denominator: SymbolicNumber,
    original_text: str,
) -> list[str]:
    rendered = render_rational(value)
    scale_words = render_number(scale)
    steps = [
        f"{rendered} needs {scale_words} to share a denominator",
        f"{render_number(value.numerator)} times {scale_words} becomes {render_number(scaled_numerator)}",
        f"{render_number(value.denominator)} times {scale_words} becomes {render_number(shared_denominator)}",
    ]
    if is_large_number(scaled_numerator) or is_large_number(shared_denominator):
        steps.append(f"{original_text} becomes an unknown number")
    else:
        steps.append(f"{original_text} becomes {render_fraction(scaled_numerator, shared_denominator)}")
    return steps


def rational_from_mixed(
    quotient: SymbolicNumber, numerator: WordNumber, denominator: WordNumber
) -> Rational:
    if is_large_number(quotient):
        return Rational(quotient, denominator)
    whole = multiply(quotient, denominator)
    improper = add(whole, numerator)
    return Rational(improper, denominator)
