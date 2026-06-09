from __future__ import annotations

from .compare import compare
from .divide import quotient_and_remainder
from .increment import increment
from .normalize import parse_number
from .render import render_number
from .words import ONE, WordNumber, ZERO, is_zero

TWO = WordNumber("zero", "zero", "two")


def prime_status(value: WordNumber) -> tuple[bool, WordNumber | None]:
    if compare(value, TWO) == "less":
        return False, None

    candidate = TWO
    while compare(candidate, value) == "less":
        _, remainder = quotient_and_remainder(value, candidate)
        if is_zero(remainder):
            return False, candidate
        candidate = increment(candidate)

    return True, None


def prime_expression(phrase: str) -> str:
    value = parse_number(phrase)
    is_prime, divisor = prime_status(value)
    rendered = render_number(value)
    if is_prime:
        return f"{rendered} is prime"
    if divisor is None:
        return f"{rendered} is not prime"
    return f"{rendered} is not prime; divisor is {render_number(divisor)}"


def trace_prime_expression(phrase: str) -> list[str]:
    value = parse_number(phrase)
    rendered = render_number(value)
    if compare(value, TWO) == "less":
        return [f"{rendered} is less than two", f"{rendered} is not prime"]

    steps = [f"{rendered} is at least two"]
    candidate = TWO
    while compare(candidate, value) == "less":
        _, remainder = quotient_and_remainder(value, candidate)
        steps.append(
            f"{rendered} divided by {render_number(candidate)} leaves "
            f"{render_number(remainder)}"
        )
        if is_zero(remainder):
            steps.append(f"{rendered} is not prime; divisor is {render_number(candidate)}")
            return steps
        candidate = increment(candidate)

    steps.append(f"{rendered} is prime")
    return steps
