from __future__ import annotations

from .words import (
    DIGITS,
    LARGE_NUMBER,
    SymbolicNumber,
    TEENS_TO_ONES,
    TENS_TO_DIGIT,
    UNKNOWN_NUMBER,
    WordNumber,
    ZERO,
)


def _clean(phrase: str) -> list[str]:
    text = phrase.lower().replace("-", " ")
    return [token for token in text.split() if token != "and"]


def parse_number(phrase: str) -> SymbolicNumber:
    tokens = _clean(phrase)
    if not tokens:
        raise ValueError("empty number phrase")

    if tokens == ["a", "large", "number"]:
        return LARGE_NUMBER
    if tokens == ["an", "unknown", "number"]:
        return UNKNOWN_NUMBER

    if tokens == ["zero"]:
        return ZERO

    if tokens[0] == "a":
        tokens[0] = "one"

    if "hundred" in tokens:
        marker = tokens.index("hundred")
        if marker != 1:
            raise ValueError(f"unsupported number phrase: {phrase}")
        hundreds_word = tokens[0]
        if hundreds_word not in DIGITS or hundreds_word == "zero":
            raise ValueError(f"unsupported number phrase: {phrase}")
        rest = tokens[2:]
        if not rest:
            return WordNumber(hundreds_word, "zero", "zero")
        tail = _parse_under_hundred(rest, phrase)
        return WordNumber(hundreds_word, tail.tens, tail.ones)

    return _parse_under_hundred(tokens, phrase)


def _parse_under_hundred(tokens: list[str], original: str) -> WordNumber:
    if len(tokens) == 1:
        word = tokens[0]
        if word in DIGITS and word != "zero":
            return WordNumber("zero", "zero", word)
        if word in TEENS_TO_ONES:
            return WordNumber("zero", "one", TEENS_TO_ONES[word])
        if word in TENS_TO_DIGIT:
            return WordNumber("zero", TENS_TO_DIGIT[word], "zero")
        raise ValueError(f"unsupported number phrase: {original}")

    if len(tokens) == 2:
        tens, ones = tokens
        if tens in TENS_TO_DIGIT and ones in DIGITS and ones != "zero":
            return WordNumber("zero", TENS_TO_DIGIT[tens], ones)
        raise ValueError(f"unsupported number phrase: {original}")

    raise ValueError(f"unsupported number phrase: {original}")
