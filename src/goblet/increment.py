from __future__ import annotations

from .words import LARGE_NUMBER, SUCCESSOR, UNKNOWN_NUMBER, SymbolicNumber, WordNumber, is_large_number, is_unknown_number


def increment_digit(digit: str) -> tuple[str, bool]:
    if digit == "nine":
        return "zero", True
    return SUCCESSOR[digit], False


def decrement_digit(digit: str) -> str:
    from .words import PREDECESSOR

    if digit == "zero":
        raise ValueError("cannot decrement zero")
    return PREDECESSOR[digit]


def increment(value: SymbolicNumber) -> SymbolicNumber:
    if is_unknown_number(value):
        return UNKNOWN_NUMBER
    if is_large_number(value):
        return LARGE_NUMBER

    ones, carry = increment_digit(value.ones)
    if not carry:
        return WordNumber(value.hundreds, value.tens, ones)

    tens, carry = increment_digit(value.tens)
    if not carry:
        return WordNumber(value.hundreds, tens, ones)

    hundreds, carry = increment_digit(value.hundreds)
    if carry:
        return LARGE_NUMBER

    return WordNumber(hundreds, tens, ones)
