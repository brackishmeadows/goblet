# PRD: Goblet

## Summary

Build a toy arithmetic engine that accepts English number phrases from `zero` through `nine hundred ninety nine` and performs division, multiplication, random range generation, and prime checks without converting phrases into numeric primitives.

The core experiment is arithmetic as symbolic rewriting: words stay words, place structure stays grammatical, and operations are performed through comparison, subtraction, borrowing, successor, and normalization rules.

## Product Shape

This is a command-line/library experiment, not a polished app.

Primary user:

- A language-tooling tinkerer who wants to inspect how far arithmetic can be pushed through symbolic phrase rules.

Primary use:

- Input a phrase like `nine hundred ninety nine divided by twenty seven`.
- Receive a phrase result like `thirty seven`.
- For non-even division, receive a mixed fraction, such as `seven divided by three becomes two and one third`.
- Input a phrase like `twelve times twelve`.
- Receive a phrase result like `one hundred and forty four`.
- Ask whether `seven` is prime.
- Receive `seven is prime`.

## Hard Constraint

The engine must not convert number phrases into ordinary numeric values for arithmetic.

Forbidden implementation patterns:

- `int(...)`, `parseInt(...)`, or equivalent numeric parsing for arithmetic.
- Mapping `nine hundred ninety nine` to `999` and using ordinary arithmetic operators.
- Precomputing all division pairs as a lookup table.

Allowed implementation patterns:

- Tokenizing words.
- Normalizing phrase grammar.
- Representing phrases as symbolic slots, such as hundreds/tens/ones words.
- Comparing phrase slots by finite ordering rules.
- Subtracting via symbolic borrow rules.
- Incrementing quotient via successor rules.
- Rendering symbolic state back to English.

## Scope

Inputs:

- English cardinal numbers from `zero` to `nine hundred ninety nine`.
- Division expressions of the form `[number phrase] divided by [number phrase]`.
- Multiplication expressions of the form `[number phrase] times [number phrase]`.
- Multiplication expressions of the form `[number phrase] multiplied by [number phrase]`.
- Prime checks for a single supported number phrase.
- Optional `and` in phrases.
- Optional hyphen normalization if input source includes hyphenated forms.

Outputs:

- Exact quotient phrase when division is even.
- Mixed fraction phrase when division is not even.
- Reduced proper fraction phrase when the dividend is smaller than the divisor.
- `a large number` when an operation produces a value beyond `999`, including mixed fractional overflow.
- Prime status phrases, such as `nine is not prime; divisor is three`.
- Clear error for division by zero.
- Clear error for phrases outside supported range.

## Non-Goals

- Decimals.
- Values less than zero.
- Ordinals.
- Arithmetic above `999`.
- Natural-language ambiguity beyond the supported grammar.
- General Inform 7 implementation in the first pass.
- A GUI or web app.

## Functional Requirements

1. The engine can parse and normalize supported English number phrases.
2. The engine can compare two supported symbolic number phrases.
3. The engine can subtract one symbolic number phrase from another when the minuend is greater than or equal to the subtrahend.
4. The engine can increment a symbolic quotient phrase by one.
5. The engine can divide by repeated symbolic subtraction until the remainder is smaller than the divisor.
6. The engine can reduce a symbolic fraction without numeric conversion.
7. The engine can multiply by repeated symbolic addition.
8. The engine can add by repeated symbolic successor stepping.
9. The engine can check primality by symbolic trial division.
10. The engine can render canonical English output.
11. The engine rejects division by zero.
12. The engine rejects unsupported or malformed phrases.
13. Tests prove that arithmetic behavior is correct for representative cases without relying on numeric conversion in the arithmetic path.

## Proposed Toolchain

Use Python as the host language and test harness.

Suggested structure:

```text
goblet/
  README.md
  PRD.md
  src/
    goblet/
      normalize.py
      compare.py
      add.py
      subtract.py
      increment.py
      reduce_fraction.py
      divide.py
      multiply.py
      prime.py
      render.py
  tests/
```

Suggested test runner:

```text
pytest
```

Python is allowed to manage data structures, loops, files, and tests. It is not allowed to perform arithmetic by converting phrases into numeric values.

## Algorithm Sketch

Normalize input:

```text
a hundred and five
one hundred five
```

Represent symbolically:

```text
one hundred five
becomes hundreds: one, tens: zero, ones: five
```

Compare by slots:

```text
compare hundreds
if equal, compare tens
if equal, compare ones
```

Subtract by rewrite:

```text
seven minus three becomes four
one hundred five minus six
becomes borrow one ten from hundreds through tens
becomes ninety nine
```

Divide:

```text
quotient = zero
remainder = dividend
while remainder >= divisor:
  remainder = remainder - divisor
  quotient = successor(quotient)
```

Multiply:

```text
result = zero
count = multiplier
while count is not zero:
  result = result plus multiplicand
  count = count minus one
```

Add:

```text
result = left
count = right
while count is not zero:
  result = successor(result)
  count = count minus one
```

Reduce fraction:

```text
fraction numerator = remainder
fraction denominator = divisor
find symbolic greatest common divisor
divide numerator and denominator by symbolic divisor
```

Render:

```text
quotient if fraction numerator is zero
proper fraction if quotient is zero
mixed fraction otherwise
```

## Acceptance Tests

Minimum examples:

```text
zero divided by one becomes zero
seven divided by three becomes two and one third
nine divided by three becomes three
one hundred divided by ten becomes ten
one hundred five divided by six becomes seventeen and one half
one divided by two becomes one half
two divided by four becomes one half
nine hundred ninety nine divided by twenty seven becomes thirty seven
nine hundred ninety nine divided by one becomes nine hundred and ninety nine
one divided by zero becomes error: division by zero
one thousand divided by one becomes error: unsupported number phrase
twelve times twelve becomes one hundred and forty four
thirty seven multiplied by twenty seven becomes nine hundred and ninety nine
one hundred times ten becomes a large number
seven becomes seven is prime
nine becomes nine is not prime; divisor is three
```

## Risks

- Repeated subtraction is intentionally simple but slow for worst-case `999 divided by one`.
- Fraction reduction adds another division-like procedure and is the main scope increase.
- Symbolic borrowing can become messy if normalization is loose.
- The project can accidentally cheat through numeric helper functions unless tests and code review explicitly guard against it.
- Supporting too much English grammar will bloat the rule surface. Keep the grammar narrow.

## Future Options

- Add a static/code check that bans numeric arithmetic operators in core arithmetic modules.
- Export the rule set to an Inform 7-style artifact.
- Add addition and subtraction as first-class input operations after their internal machinery is stable.
- Extend trace mode coverage to fraction reduction edge cases.

## Current Decision

Continue with Python plus the standard-library test harness, using symbolic phrase slots and rewrite tables. Do not port to Inform 7 until the rule system is broader and trace output is stable.

## Next Move

Add a formal cheat-detector test and broaden trace coverage for reduced fractions and compound denominators.
