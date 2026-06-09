from __future__ import annotations

from .compare import compare, less_than
from .normalize import parse_number
from .increment import increment
from .render import (
    render_at_least_mixed,
    render_at_most_large_denominator,
    render_fraction,
    render_mixed,
    render_number,
)
from .subtract import subtract
from .words import MAX_WORD_NUMBER, ONE, SymbolicNumber, WordNumber, ZERO, is_large_number, is_zero


def quotient_and_remainder(dividend: WordNumber, divisor: WordNumber) -> tuple[WordNumber, WordNumber]:
    if is_zero(divisor):
        raise ValueError("division by zero")

    quotient = ZERO
    remainder = dividend
    while not less_than(remainder, divisor):
        remainder = subtract(remainder, divisor)
        quotient = increment(quotient)
    return quotient, remainder


def divide(dividend: WordNumber, divisor: WordNumber) -> tuple[WordNumber, WordNumber, WordNumber]:
    quotient, remainder = quotient_and_remainder(dividend, divisor)
    if is_zero(remainder):
        return quotient, ZERO, ONE

    numerator, denominator = reduce_fraction(remainder, divisor)
    return quotient, numerator, denominator


def divide_large_lower_bound(divisor: WordNumber) -> tuple[SymbolicNumber, WordNumber, WordNumber]:
    if is_zero(divisor):
        raise ValueError("division by zero")

    quotient, remainder = quotient_and_remainder(MAX_WORD_NUMBER, divisor)
    numerator = increment(remainder)
    if is_large_number(numerator):
        raise ValueError("symbolic lower-bound numerator overflowed")

    if compare(numerator, divisor) == "equal":
        return increment(quotient), ZERO, ONE

    reduced_numerator, reduced_denominator = reduce_fraction(numerator, divisor)
    return quotient, reduced_numerator, reduced_denominator


def reduce_fraction(numerator: WordNumber, denominator: WordNumber) -> tuple[WordNumber, WordNumber]:
    divisor = greatest_common_divisor(numerator, denominator)
    reduced_numerator, numerator_remainder = quotient_and_remainder(numerator, divisor)
    reduced_denominator, denominator_remainder = quotient_and_remainder(denominator, divisor)

    if not is_zero(numerator_remainder) or not is_zero(denominator_remainder):
        raise ValueError("symbolic fraction reduction failed")

    return reduced_numerator, reduced_denominator


def greatest_common_divisor(left: WordNumber, right: WordNumber) -> WordNumber:
    a = left
    b = right
    while not is_zero(b):
        _, remainder = quotient_and_remainder(a, b)
        a = b
        b = remainder
    return a


def divide_expression(expression: str) -> str:
    dividend, divisor = parse_division_expression(expression)
    if is_large_number(divisor):
        if is_large_number(dividend):
            raise ValueError("cannot divide two unbounded symbolic values")
        return render_at_most_large_denominator(dividend)
    if is_large_number(dividend):
        quotient, numerator, denominator = divide_large_lower_bound(divisor)
        return render_at_least_mixed(quotient, numerator, denominator)

    quotient, numerator, denominator = divide(dividend, divisor)
    return render_mixed(quotient, numerator, denominator)


def trace_divide_expression(expression: str) -> list[str]:
    dividend, divisor = parse_division_expression(expression)
    expression_text = f"{render_number(dividend)} divided by {render_number(divisor)}"
    if is_large_number(divisor):
        if is_large_number(dividend):
            raise ValueError("cannot divide two unbounded symbolic values")
        result = render_at_most_large_denominator(dividend)
        return [
            expression_text,
            "a large number means at least one more than nine hundred and ninety nine",
            f"{expression_text} becomes {result}",
        ]
    if is_large_number(dividend):
        quotient, numerator, denominator = divide_large_lower_bound(divisor)
        result = render_at_least_mixed(quotient, numerator, denominator)
        return [
            expression_text,
            "a large number means at least one more than nine hundred and ninety nine",
            f"{expression_text} becomes {result}",
        ]

    quotient, remainder, division_steps = quotient_and_remainder_trace(dividend, divisor)

    steps = [expression_text, *division_steps]
    if is_zero(remainder):
        result = render_mixed(quotient, ZERO, ONE)
        steps.append(f"{expression_text} becomes {result}")
        return steps

    numerator, denominator, reduction_steps = reduce_fraction_trace(remainder, divisor)
    steps.extend(reduction_steps)
    result = render_mixed(quotient, numerator, denominator)
    steps.append(f"{expression_text} becomes {result}")
    return steps


def parse_division_expression(expression: str) -> tuple[SymbolicNumber, SymbolicNumber]:
    parts = expression.lower().split(" divided by ")
    if len(parts) != 2:
        raise ValueError("expected '[number phrase] divided by [number phrase]'")
    return parse_number(parts[0]), parse_number(parts[1])


def quotient_and_remainder_trace(
    dividend: WordNumber, divisor: WordNumber
) -> tuple[WordNumber, WordNumber, list[str]]:
    if is_zero(divisor):
        raise ValueError("division by zero")

    steps = []
    quotient = ZERO
    remainder = dividend
    while not less_than(remainder, divisor):
        before = remainder
        remainder = subtract(remainder, divisor)
        quotient = increment(quotient)
        steps.append(
            f"{render_number(before)} minus {render_number(divisor)} becomes "
            f"{render_number(remainder)}; quotient becomes {render_number(quotient)}"
        )

    steps.append(f"{render_number(remainder)} is less than {render_number(divisor)}")
    return quotient, remainder, steps


def reduce_fraction_trace(
    numerator: WordNumber, denominator: WordNumber
) -> tuple[WordNumber, WordNumber, list[str]]:
    divisor, gcd_steps = greatest_common_divisor_trace(numerator, denominator)
    if divisor == ONE:
        return numerator, denominator, [
            f"{render_fraction(numerator, denominator)} is already reduced"
        ]

    reduced_numerator, numerator_remainder = quotient_and_remainder(numerator, divisor)
    reduced_denominator, denominator_remainder = quotient_and_remainder(denominator, divisor)
    if not is_zero(numerator_remainder) or not is_zero(denominator_remainder):
        raise ValueError("symbolic fraction reduction failed")

    reduced_fraction = render_fraction(reduced_numerator, reduced_denominator)
    original_fraction = f"{render_number(numerator)} over {render_number(denominator)}"
    steps = [
        *gcd_steps,
        f"{original_fraction} reduces by {render_number(divisor)}",
        f"{original_fraction} becomes {reduced_fraction}",
    ]
    return reduced_numerator, reduced_denominator, steps


def greatest_common_divisor_trace(
    left: WordNumber, right: WordNumber
) -> tuple[WordNumber, list[str]]:
    steps = [
        "greatest common divisor search starts with "
        f"{render_number(left)} and {render_number(right)}"
    ]
    a = left
    b = right
    while not is_zero(b):
        _, remainder = quotient_and_remainder(a, b)
        steps.append(
            f"{render_number(a)} divided by {render_number(b)} leaves "
            f"{render_number(remainder)}"
        )
        a = b
        b = remainder
    steps.append(f"greatest common divisor becomes {render_number(a)}")
    return a, steps
