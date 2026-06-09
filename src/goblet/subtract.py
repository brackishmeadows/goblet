from __future__ import annotations

from .compare import compare_digit, greater_or_equal
from .increment import decrement_digit
from .words import PREDECESSOR, WordNumber


def _subtract_digit(top: str, bottom: str) -> str:
    result = top
    countdown = bottom
    while countdown != "zero":
        result = PREDECESSOR[result]
        countdown = PREDECESSOR[countdown]
    return result


def _subtract_digit_with_borrow(top: str, bottom: str) -> str:
    result = top
    countdown = bottom
    while countdown != "zero":
        result = "nine" if result == "zero" else PREDECESSOR[result]
        countdown = PREDECESSOR[countdown]
    return result


def _borrow_from_hundreds(hundreds: str) -> tuple[str, str]:
    if hundreds == "zero":
        raise ValueError("cannot borrow from zero hundreds")
    return decrement_digit(hundreds), "nine"


def subtract(left: WordNumber, right: WordNumber) -> WordNumber:
    if not greater_or_equal(left, right):
        raise ValueError("cannot subtract larger symbolic value")

    hundreds = left.hundreds
    tens = left.tens

    if compare_digit(left.ones, right.ones) == "less":
        ones = _subtract_digit_with_borrow(left.ones, right.ones)
        if tens == "zero":
            hundreds, tens = _borrow_from_hundreds(hundreds)
        else:
            tens = decrement_digit(tens)
    else:
        ones = _subtract_digit(left.ones, right.ones)

    if compare_digit(tens, right.tens) == "less":
        tens_result = _subtract_digit_with_borrow(tens, right.tens)
        hundreds = decrement_digit(hundreds)
    else:
        tens_result = _subtract_digit(tens, right.tens)

    hundreds_result = _subtract_digit(hundreds, right.hundreds)
    return WordNumber(hundreds_result, tens_result, ones)
