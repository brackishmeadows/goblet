# Goblet

![A golden goblet with blue ornamentation](e5684fdf-7f5f-4979-87e2-92f95fbded75.png)

A tiny symbolic arithmetic engine for English number phrases.

It does not convert phrases into normal numeric primitives for arithmetic. It parses constrained English into symbolic slots, then works through successor, predecessor, borrowing, repeated addition, repeated subtraction, fraction reduction, interval bounds, and traceable comparisons.

The broader idea is [bounded legible reasoning](docs/bounded-legible-reasoning.md): small deterministic systems that preserve uncertainty in human-readable language.

## Play Liar's Labyrinth

[Open the browser prototype](web/) or read the [Liar's Labyrinth systems notes](docs/liars-labyrinth.md).

Liar's Labyrinth is a command-first social hazard crawler built on Goblet's
symbolic reasoning. You question liars, compare testimony, ask miniature
honest/liar puzzles, track memory and trust, and try to survive rooms where
agents can mislead each other, fall asleep, follow goals, or push someone
through the wrong door.

## What It Can Say

```text
seven plus three
-> ten

twenty seven divided by five
-> five and two fifths

one half plus one third
-> five sixths

a large number divided by five
-> at least two hundred

six divided by a large number
-> at most six over a large number

at most five is greater than four
-> likely false; true for values greater than four and at most five

cube root of two is less than nine sevenths
-> true

an unknown number is greater than five
-> unknown
```

## Features

- Exact English-number arithmetic from `zero` through `nine hundred and ninety nine`
- Addition, subtraction, multiplication, division, prime checks, and random range generation
- Fraction and mixed-number rendering such as `five and two fifths`
- Fraction addition and subtraction such as `one half plus one third`
- Bounded values such as `at least five`, `at most twelve`, and `a large number`
- A distinct `an unknown number` value for cases where exact scale is lost
- Symbolic comparisons with `true`, `false`, `unknown`, exception clauses, and finite-range likelihood clauses
- Named root bounds such as `square root of two`, `cube root of two`, and `fourth root of two`
- Trace mode that explains rewrite steps, bounds, true regions, and false regions
- Classic honest/liar puzzle solving with possible-world traces
- Liar's Labyrinth: a command-first social hazard crawler using Goblet questions, liar puzzles, testimony, recall, trust, and agent goals
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

Fraction arithmetic:

```text
one half plus one third
-> five sixths

two thirds minus one third
-> one third

five and two fifths plus one third
-> five and eleven fifteenths

one over nine hundred and ninety nine plus one over nine hundred and ninety eight
-> an unknown number
```

Symbolic comparisons:

```text
a large number divided by five is greater than two hundred
-> true unless it is two hundred

six divided by a large number equals zero
-> false

at most five is less than five
-> likely true; false only if it is five

square root of two is greater than twenty four seventeenths
-> true

square root of four equals two
-> true

cube root of eight equals two
-> true

fifth root of thirty two equals two
-> true
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

Fraction trace:

```powershell
python run.py --trace "one half plus one third"
```

```text
one half plus one third
one half needs three to share a denominator
one times three becomes three
two times three becomes six
one half becomes three sixths
one third needs two to share a denominator
one times two becomes two
three times two becomes six
one third becomes two sixths
three sixths plus two sixths becomes five sixths
five sixths is already reduced
one half plus one third becomes five sixths
```

Root trace:

```powershell
python run.py --trace "square root of two is greater than one"
```

```text
square root of two is greater than one
finding bounds for square root of two
testing twenty four seventeenths
twenty four times twenty four becomes five hundred and seventy six
seventeen times seventeen becomes two hundred and eighty nine
two times two hundred and eighty nine becomes five hundred and seventy eight
five hundred and seventy six is less than five hundred and seventy eight
twenty four seventeenths is below square root of two
testing seventeen twelfths
seventeen times seventeen becomes two hundred and eighty nine
twelve times twelve becomes one hundred and forty four
two times one hundred and forty four becomes two hundred and eighty eight
two hundred and eighty nine is greater than two hundred and eighty eight
seventeen twelfths is above square root of two
square root of two is greater than twenty four seventeenths and less than seventeen twelfths
left range: greater than twenty four seventeenths and less than seventeen twelfths
right range: exactly one
comparison becomes true
```

Random range:

```powershell
python run.py --random "at least eight" "at most twelve"
```

Prime check:

```powershell
python run.py --prime "seven"
```

Classic liars puzzle:

```powershell
python run.py --liars examples/aster-bram.goblet-liars
```

Liar's Labyrinth:

```powershell
python run.py --labyrinth examples/liars-labyrinth-demo.txt
python run.py --labyrinth-play
```

## Tests

```powershell
python -m unittest discover -s tests
```

Field-office local Python command:

```powershell
& ..\tools\python-3.13.13-embed-amd64\python.exe -m unittest discover -s tests
```

## Browser Prototype

The static browser prototype lives in [web/](web/). Serve the repository root
with a static server, then open `http://localhost:8000/web/`.

When GitHub Pages is enabled for this repository, the browser build is published at
`https://brackishmeadows.github.io/goblet/`.

The same session layer is available from the CLI:

```powershell
python run.py --labyrinth-post state.goblet start optional-seed
python run.py --labyrinth-post state.goblet help
```

## Documentation

- [Manual](MANUAL.md): command syntax and examples
- [PRD](PRD.md): original product requirements and constraints
- [Browser PRD](docs/browser_prd.md): static Pyodide prototype plan
- [Classic Liars Puzzles](docs/liars.md): file format, solver behavior, and trace mode
- [Liar's Labyrinth](docs/liars-labyrinth.md): game systems, commands, and current prototype state
- [Web Prototype README](web/README.md): local browser run notes
- [Bounded Legible Reasoning](docs/bounded-legible-reasoning.md): broader design note
- [Witness Machine Interop Note](docs/witness-machine-interop-note.md): research note on possible Hat/Goblet synthesis
- [Handoff Report](reports/handoff-report.md): implementation state and known limits

## Current Limits

- No decimals
- No values less than zero
- Root support searches for provable rational cages inside the current symbolic ceiling
- Inputs are bounded to English cardinal phrases from `zero` through `nine hundred and ninety nine`
- Some exact fraction comparisons can become `unknown` if symbolic cross-products overflow the supported ceiling
- Some fraction arithmetic can become `an unknown number` if exact scale is lost after symbolic overflow
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

The test suite includes a static cheat detector for these shortcuts.

## License

MIT. See [LICENSE](LICENSE).
