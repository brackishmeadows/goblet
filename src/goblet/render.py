from __future__ import annotations

from .compare import compare
from .words import (
    DIGIT_TO_TENS,
    ONE,
    ONES_TO_TEENS,
    ORDINAL_SPECIAL,
    SymbolicNumber,
    TWENTY,
    WordNumber,
    ZERO,
    is_large_number,
    is_unknown_number,
)


def render_number(value: SymbolicNumber) -> str:
    if is_unknown_number(value):
        return "an unknown number"
    if is_large_number(value):
        return "a large number"

    if value == ZERO:
        return "zero"

    parts = []
    if value.hundreds != "zero":
        parts.append(f"{value.hundreds} hundred")

    tail = _render_under_hundred(value.tens, value.ones)
    if tail:
        if parts:
            parts.append("and")
        parts.append(tail)

    return " ".join(parts)


def _render_under_hundred(tens: str, ones: str) -> str:
    if tens == "zero":
        return "" if ones == "zero" else ones
    if tens == "one":
        return ONES_TO_TEENS[ones]

    tens_word = DIGIT_TO_TENS[tens]
    if ones == "zero":
        return tens_word
    return f"{tens_word} {ones}"


def render_fraction(numerator: SymbolicNumber, denominator: SymbolicNumber) -> str:
    if is_unknown_number(numerator) or is_unknown_number(denominator):
        return "an unknown number"

    numerator_words = render_number(numerator)
    if is_large_number(numerator):
        return numerator_words

    if _should_render_as_over(denominator):
        return f"{numerator_words} over {render_number(denominator)}"

    denominator_words = render_fraction_denominator(denominator)
    if compare(numerator, ONE) == "equal":
        if denominator_words.startswith("one "):
            return denominator_words
        return f"{numerator_words} {denominator_words}"
    return f"{numerator_words} {_plural_ordinal(denominator_words)}"


def render_mixed(quotient: SymbolicNumber, numerator: SymbolicNumber, denominator: SymbolicNumber) -> str:
    if is_unknown_number(quotient) or is_unknown_number(numerator) or is_unknown_number(denominator):
        return "an unknown number"
    if is_large_number(quotient):
        return "a large number"

    if numerator == ZERO:
        return render_number(quotient)
    fraction = render_fraction(numerator, denominator)
    if quotient == ZERO:
        return fraction
    return f"{render_number(quotient)} and {fraction}"


def render_at_least_mixed(
    quotient: SymbolicNumber, numerator: SymbolicNumber, denominator: SymbolicNumber
) -> str:
    if is_unknown_number(quotient) or is_unknown_number(numerator) or is_unknown_number(denominator):
        return "an unknown number"
    if is_large_number(quotient):
        return "a large number"
    return f"at least {render_mixed(quotient, numerator, denominator)}"


def render_at_most_large_denominator(numerator: SymbolicNumber) -> str:
    if is_unknown_number(numerator):
        return "an unknown number"
    if is_large_number(numerator):
        return "a large number"
    if numerator == ZERO:
        return "zero"
    return f"at most {render_number(numerator)} over a large number"


def render_ordinal(value: SymbolicNumber) -> str:
    if is_unknown_number(value):
        return "an unknown number"
    if is_large_number(value):
        return "a large number"

    cardinal = render_number(value)
    if cardinal in ORDINAL_SPECIAL:
        return ORDINAL_SPECIAL[cardinal]

    if value.tens == "zero" and value.ones == "zero":
        return f"{value.hundreds} hundredth"

    if value.ones == "zero":
        return ORDINAL_SPECIAL[cardinal]

    prefix = render_number(WordNumber(value.hundreds, value.tens, "zero"))
    ones_ordinal = ORDINAL_SPECIAL[value.ones]
    if value.hundreds == "zero" and value.tens == "zero":
        return ones_ordinal
    return f"{prefix} {ones_ordinal}"


def render_fraction_denominator(value: SymbolicNumber) -> str:
    if render_number(value) == "four":
        return "quarter"
    return render_ordinal(value)


def _should_render_as_over(denominator: SymbolicNumber) -> bool:
    if is_large_number(denominator):
        return True

    if compare(denominator, TWENTY) != "greater":
        return False
    if denominator.hundreds != "zero":
        return denominator.tens != "zero" or denominator.ones != "zero"
    return denominator.ones != "zero"


def _plural_ordinal(ordinal: str) -> str:
    if ordinal.endswith("half"):
        return f"{ordinal[:-4]}halves"
    if ordinal.endswith("quarter"):
        return f"{ordinal}s"
    if ordinal.endswith("y"):
        return f"{ordinal[:-1]}ies"
    return f"{ordinal}s"
