# Goblet

A tiny symbolic arithmetic engine for English number phrases.

It does not convert phrases into normal numeric primitives for arithmetic. It parses constrained English into symbolic slots, then works through successor, predecessor, borrowing, repeated addition, repeated subtraction, fraction reduction, interval bounds, and traceable comparisons.

The broader idea is [bounded legible reasoning](docs/bounded-legible-reasoning.md): small deterministic systems that preserve uncertainty in human-readable language.

## What It Can Say

```text
seven plus three
-> ten

twenty seven divided by five
-> five and two fifths

a large number divided by five
-> at least two hundred

six divided by a large number
-> at most six over a large number

at most five is greater than four
-> likely false; true for values greater than four and at most five

an unknown number is greater than five
-> unknown
```

## Features

- Exact English-number arithmetic from `zero` through `nine hundred and ninety nine`
- Addition, subtraction, multiplication, division, prime checks, and random range generation
- Fractions and mixed numbers such as `five and two fifths`
- Bounded values such as `at least five`, `at most twelve`, and `a large number`
- A distinct `an unknown number` value for cases where exact scale is lost
- Symbolic comparisons with `true`, `false`, `unknown`, exception clauses, and finite-range likelihood clauses
- Trace mode that explains rewrite steps, bounds, true regions, and false regions
- No ordinary numeric conversion in the arithmetic path

## Install

From this directory:

```powershell
python -m pip install -e .
```

Then run:

```powershell
goblet "twenty seven divided by five"
```

You can also run without installing:

```powershell
python run.py "twenty seven divided by five"
```

Field-office local Python command:

```powershell
& ..\tools\python-3.13.13-embed-amd64\python.exe run.py "twenty seven divided by five"
```

## Examples

Exact arithmetic:

```text
seven plus three
-> ten

seven minus three
-> four

twelve times twelve
-> one hundred and forty four

twenty seven divided by five
-> five and two fifths
```

Bounded arithmetic:

```text
at most five plus three
-> at least three and at most eight

at most five minus three
-> at most two when the left value is at least three
```

Symbolic comparisons:

```text
a large number divided by five is greater than two hundred
-> true unless it is two hundred

six divided by a large number equals zero
-> false

at most five is less than five
-> likely true; false only if it is five
```

Trace mode:

```powershell
python run.py --trace "at most five is greater than four"
```

```text
at most five is greater than four
left range: at most five
right range: exactly four
comparison becomes likely false; true for values greater than four and at most five
true region: greater than four and at most five
false region: at least zero and at most four
not guaranteed because the ranges overlap
could be true if the left value lands above the right value
could be false if the left value lands at or below the right value
```

Random range:

```powershell
python run.py --random "at least eight" "at most twelve"
```

Prime check:

```powershell
python run.py --prime "seven"
```

## Tests

```powershell
python -m unittest discover -s tests
```

Field-office local Python command:

```powershell
& ..\tools\python-3.13.13-embed-amd64\python.exe -m unittest discover -s tests
```

## Documentation

- [Manual](MANUAL.md): command syntax and examples
- [PRD](PRD.md): original product requirements and constraints
- [Bounded Legible Reasoning](docs/bounded-legible-reasoning.md): broader design note
- [Handoff Report](reports/handoff-report.md): implementation state and known limits

## Current Limits

- No decimals
- No values less than zero
- No irrational numbers
- Inputs are bounded to English cardinal phrases from `zero` through `nine hundred and ninety nine`
- Some exact fraction comparisons can become `unknown` if symbolic cross-products overflow the supported ceiling
- Fractions with `a large number` as a bound denominator are not reduced yet
- `an unknown number` means exact scale was lost; it is not the same as `a large number`

## Internal Rule

The arithmetic path must not use ordinary numeric conversion or ordinary arithmetic shortcuts.

Forbidden in core arithmetic:

```text
int(...)
parseInt
/
//
%
ordinary *
```

Python is allowed for control flow, data structures, tests, and random selection. The arithmetic itself moves through symbolic word rules.

## License

MIT. See [LICENSE](LICENSE).
