from __future__ import annotations

from dataclasses import dataclass


DIGITS = (
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
)

SUCCESSOR = {
    "zero": "one",
    "one": "two",
    "two": "three",
    "three": "four",
    "four": "five",
    "five": "six",
    "six": "seven",
    "seven": "eight",
    "eight": "nine",
}

PREDECESSOR = {after: before for before, after in SUCCESSOR.items()}

TEENS_TO_ONES = {
    "ten": "zero",
    "eleven": "one",
    "twelve": "two",
    "thirteen": "three",
    "fourteen": "four",
    "fifteen": "five",
    "sixteen": "six",
    "seventeen": "seven",
    "eighteen": "eight",
    "nineteen": "nine",
}

ONES_TO_TEENS = {ones: teen for teen, ones in TEENS_TO_ONES.items()}

TENS_TO_DIGIT = {
    "twenty": "two",
    "thirty": "three",
    "forty": "four",
    "fifty": "five",
    "sixty": "six",
    "seventy": "seven",
    "eighty": "eight",
    "ninety": "nine",
}

DIGIT_TO_TENS = {digit: tens for tens, digit in TENS_TO_DIGIT.items()}

ORDINAL_SPECIAL = {
    "one": "first",
    "two": "half",
    "three": "third",
    "four": "fourth",
    "five": "fifth",
    "six": "sixth",
    "seven": "seventh",
    "eight": "eighth",
    "nine": "ninth",
    "ten": "tenth",
    "eleven": "eleventh",
    "twelve": "twelfth",
    "thirteen": "thirteenth",
    "fourteen": "fourteenth",
    "fifteen": "fifteenth",
    "sixteen": "sixteenth",
    "seventeen": "seventeenth",
    "eighteen": "eighteenth",
    "nineteen": "nineteenth",
    "twenty": "twentieth",
    "thirty": "thirtieth",
    "forty": "fortieth",
    "fifty": "fiftieth",
    "sixty": "sixtieth",
    "seventy": "seventieth",
    "eighty": "eightieth",
    "ninety": "ninetieth",
}


@dataclass(frozen=True)
class WordNumber:
    hundreds: str
    tens: str
    ones: str


@dataclass(frozen=True)
class LargeNumber:
    pass


@dataclass(frozen=True)
class UnknownNumber:
    pass


SymbolicNumber = WordNumber | LargeNumber | UnknownNumber

ZERO = WordNumber("zero", "zero", "zero")
ONE = WordNumber("zero", "zero", "one")
NINE = WordNumber("zero", "zero", "nine")
TWENTY = WordNumber("zero", "two", "zero")
MAX_WORD_NUMBER = WordNumber("nine", "nine", "nine")
LARGE_NUMBER = LargeNumber()
UNKNOWN_NUMBER = UnknownNumber()


def is_zero(value: SymbolicNumber) -> bool:
    return value == ZERO


def is_large_number(value: SymbolicNumber) -> bool:
    return value == LARGE_NUMBER


def is_unknown_number(value: SymbolicNumber) -> bool:
    return value == UNKNOWN_NUMBER
