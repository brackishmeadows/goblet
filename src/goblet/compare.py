from __future__ import annotations

from .words import SUCCESSOR, WordNumber


def compare_digit(left: str, right: str) -> str:
    if left == right:
        return "equal"

    cursor = left
    while cursor != "nine":
        cursor = SUCCESSOR[cursor]
        if cursor == right:
            return "less"

    return "greater"


def compare(left: WordNumber, right: WordNumber) -> str:
    for left_digit, right_digit in (
        (left.hundreds, right.hundreds),
        (left.tens, right.tens),
        (left.ones, right.ones),
    ):
        result = compare_digit(left_digit, right_digit)
        if result != "equal":
            return result
    return "equal"


def less_than(left: WordNumber, right: WordNumber) -> bool:
    return compare(left, right) == "less"


def greater_or_equal(left: WordNumber, right: WordNumber) -> bool:
    return compare(left, right) != "less"
