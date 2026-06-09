from __future__ import annotations

from dataclasses import dataclass

from .add import add
from .compare import compare
from .divide import divide, parse_division_expression, quotient_and_remainder, reduce_fraction
from .multiply import multiply
from .normalize import parse_number
from .render import render_mixed
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


def rational_from_mixed(
    quotient: SymbolicNumber, numerator: WordNumber, denominator: WordNumber
) -> Rational:
    if is_large_number(quotient):
        return Rational(quotient, denominator)
    whole = multiply(quotient, denominator)
    improper = add(whole, numerator)
    return Rational(improper, denominator)
