from __future__ import annotations

import random
from collections.abc import Sequence

from .compare import compare, greater_or_equal
from .increment import increment
from .normalize import parse_number
from .render import render_number
from .words import MAX_WORD_NUMBER, WordNumber, is_large_number


def values_between(lower: WordNumber, upper: WordNumber) -> list[WordNumber]:
    if compare(lower, upper) == "greater":
        raise ValueError("lower bound is greater than upper bound")

    values = [lower]
    current = lower
    while not greater_or_equal(current, upper):
        current = increment(current)
        values.append(current)
    return values


def random_number_between(
    lower_phrase: str,
    upper_phrase: str,
    chooser: random.Random | None = None,
) -> str:
    chooser = chooser or random
    lower = parse_lower_bound(lower_phrase)
    upper = parse_upper_bound(upper_phrase)
    return render_number(_choose(values_between(lower, upper), chooser))


def parse_lower_bound(phrase: str) -> WordNumber:
    marker, number_phrase = _split_bound_phrase(phrase)
    if marker == "at most":
        raise ValueError("lower bound cannot use at most")

    value = parse_number(number_phrase)
    if is_large_number(value):
        raise ValueError("lower bound has no supported finite values")
    return value


def parse_upper_bound(phrase: str) -> WordNumber:
    marker, number_phrase = _split_bound_phrase(phrase)
    if marker == "at least":
        raise ValueError("upper bound cannot use at least")

    value = parse_number(number_phrase)
    if is_large_number(value):
        if marker == "at most":
            return MAX_WORD_NUMBER
        raise ValueError("upper bound is unbounded")
    return value


def _split_bound_phrase(phrase: str) -> tuple[str | None, str]:
    cleaned = phrase.lower().strip()
    for marker in ("at least", "at most"):
        prefix = f"{marker} "
        if cleaned.startswith(prefix):
            return marker, cleaned[len(prefix) :]
    return None, cleaned


def _choose(values: Sequence[WordNumber], chooser: random.Random) -> WordNumber:
    return chooser.choice(values)
