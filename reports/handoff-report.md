# Goblet Handoff Report

Status: working first implementation

## What This Is

Goblet is a Python-hosted symbolic arithmetic engine for English number phrases from `zero` through `nine hundred and ninety nine`.

It currently supports addition, subtraction, division, multiplication, random range generation, and prime checks:
It also supports symbolic comparisons that return `true`, `false`, `unknown`, or precise likelihood clauses for finite bounded ranges.

```text
[number phrase] plus [number phrase]
[number phrase] minus [number phrase]
[fraction phrase] plus [fraction phrase]
[fraction phrase] minus [fraction phrase]
[number phrase] divided by [number phrase]
[number phrase] times [number phrase]
[number phrase] multiplied by [number phrase]
prime check for [number phrase]
[expression] is greater than [expression]
[expression] is less than [expression]
[expression] equals [expression]
[expression] is at least [expression]
[expression] is at most [expression]
```

It also supports random English number generation across an inclusive symbolic range:

```text
random between [lower number phrase] and [upper number phrase]
random between at least [lower number phrase] and at most [upper number phrase]
```

The point is not efficiency. The point is arithmetic by symbolic word pressure: parse phrases into word slots, compare word slots, subtract by predecessor rules, increment by successor rules, reduce fractions symbolically, and render English output.

## Hard Constraint

The arithmetic path must not convert phrases into ordinary numeric values.

Forbidden:

- `int(...)`
- `/`
- `//`
- `%`
- `*`
- numeric division/modulo hidden behind helpers
- precomputed full division lookup tables

Current source scan found none of those forbidden operators in the core arithmetic modules.

## Current Output Policy

Numbers render in British style when hundreds have a nonzero tail:

```text
one hundred and five
nine hundred and ninety nine
```

Anything beyond the supported `999` value ceiling renders as:

```text
a large number
```

Mixed fractions may pass just above the whole-number ceiling:

```text
nine hundred and ninety nine and one over nine hundred and ninety nine
```

When used as a dividend, `a large number` means at least one more than `nine hundred and ninety nine`, which allows lower-bound division:

```text
a large number divided by five
becomes at least two hundred

six divided by a large number
becomes at most six over a large number
```

If symbolic structure is lost badly enough that the value cannot be placed, it renders as:

```text
an unknown number
```

`a large number` means definitely beyond the supported ceiling. `an unknown number` means the exact scale was lost.

Fractions render in readable English when natural:

```text
one half
one quarter
three quarters
two fifths
one thirtieth
one hundredth
```

Compound denominators above twenty use `over` to avoid ugly ordinal mush:

```text
one over twenty one
two over one hundred and five
```

Mixed numbers use `and`:

```text
five and two fifths
seventeen and one half
```

## Examples

```text
twenty seven divided by five
becomes five and two fifths
```

```text
two hundred seventy three divided by fifty two
becomes five and one quarter
```

```text
one divided by twenty one
becomes one over twenty one
```

```text
two divided by one hundred and five
becomes two over one hundred and five
```

```text
one hundred and five divided by six
becomes seventeen and one half
```

```text
nine hundred and ninety nine divided by twenty seven
becomes thirty seven
```

```text
six divided by zero
becomes error: division by zero
```

```text
twelve times twelve
becomes one hundred and forty four
```

```text
thirty seven multiplied by twenty seven
becomes nine hundred and ninety nine
```

```text
one hundred times ten
becomes a large number
```

```text
at most five plus three
becomes at least three and at most eight
```

```text
at most five minus three
becomes at most two when the left value is at least three
```

```text
one half plus one third
becomes five sixths
```

```text
five and two fifths plus one third
becomes five and eleven fifteenths
```

```text
one over nine hundred and ninety nine plus one over nine hundred and ninety eight
becomes an unknown number
```

```text
a large number divided by six
becomes at least one hundred and sixty six and two thirds
```

```text
six divided by a large number
becomes at most six over a large number
```

```text
seven
becomes seven is prime
```

```text
a large number divided by five is greater than one hundred
becomes true
```

```text
a large number divided by five is greater than two hundred
becomes true unless it is two hundred
```

```text
six divided by a large number equals zero
becomes false
```

```text
an unknown number is greater than five
becomes unknown
```

```text
at most five is greater than four
becomes likely false; true for values greater than four and at most five
```

Trace mode explains uncertain comparisons with operand ranges:

```text
a large number divided by five is greater than two hundred
left range: at least two hundred
right range: exactly two hundred
comparison becomes true unless it is two hundred
not guaranteed because the ranges overlap
could be true if the left value lands above the right value
could be false if the left value lands at or below the right value
```

Finite bounded traces can show true and false regions:

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

```text
nine
becomes nine is not prime; divisor is three
```

```text
nine hundred and ninety seven
becomes nine hundred and ninety seven is prime
```

## Trace Mode

Trace mode shows the symbolic subtraction loop and fraction reduction steps:

```powershell
& ..\tools\python-3.13.13-embed-amd64\python.exe run.py --trace "twenty seven divided by five"
```

Output:

```text
twenty seven divided by five
twenty seven minus five becomes twenty two; quotient becomes one
twenty two minus five becomes seventeen; quotient becomes two
seventeen minus five becomes twelve; quotient becomes three
twelve minus five becomes seven; quotient becomes four
seven minus five becomes two; quotient becomes five
two is less than five
two fifths is already reduced
twenty seven divided by five becomes five and two fifths
```

## Implementation Shape

Core package:

```text
src/goblet/
  words.py       finite word tables and WordNumber slots
  normalize.py   phrase parsing and normalization
  compare.py     symbolic slot comparison
  increment.py   successor/predecessor stepping
  add.py          symbolic addition by repeated successor
  subtract.py    symbolic subtraction with borrowing
  arithmetic.py   public addition/subtraction and bounded interval arithmetic
  fraction.py     exact rational parsing, addition, subtraction, and overflow fallback
  divide.py      repeated subtraction division and symbolic fraction reduction
  multiply.py    repeated symbolic addition multiplication
  prime.py       symbolic trial division prime checks
  render.py      British-style number and fraction rendering
  random_range.py symbolic inclusive range expansion and random choice
  relation.py    symbolic comparison via interval logic
```

Local runner:

```text
run.py
```

Tests:

```text
tests/test_goblet.py
```

## Commands That Worked

From the repository root:

```powershell
& ..\tools\python-3.13.13-embed-amd64\python.exe -m unittest discover -s tests
```

Result:

```text
Ran 13 tests
OK
```

Example run:

```powershell
& ..\tools\python-3.13.13-embed-amd64\python.exe run.py "twenty seven divided by five"
```

Output:

```text
five and two fifths
```

Multiplication run:

```powershell
& ..\tools\python-3.13.13-embed-amd64\python.exe run.py "twelve times twelve"
```

Output:

```text
one hundred and forty four
```

Random range run:

```powershell
& ..\tools\python-3.13.13-embed-amd64\python.exe run.py --random "one hundred and five" "one hundred and ten"
```

Example output:

```text
one hundred and seven
```

Bounded random range run:

```powershell
& ..\tools\python-3.13.13-embed-amd64\python.exe run.py --random "at least eight" "at most twelve"
```

Example output:

```text
eleven
```

Prime run:

```powershell
& ..\tools\python-3.13.13-embed-amd64\python.exe run.py --prime "seven"
```

Output:

```text
seven is prime
```

## Known Limits

- Addition, subtraction, division, multiplication, random range generation, prime checking, and symbolic comparison only.
- Public addition and subtraction support exact whole numbers and bounded whole-number intervals.
- Public addition and subtraction support exact fractions and mixed numbers.
- Comparisons support exact values, exact division expressions, and bounded division expressions.
- Comparison trace mode shows operand ranges and the conditions that would make an unknown comparison true or false.
- Finite bounded comparison traces show true and false regions when they can be rendered cleanly.
- Finite bounded comparisons can return `likely true` or `likely false` when symbolic midpoint comparison shows one side occupies more than half the range.
- Inputs only support English cardinal phrases from `zero` through `nine hundred and ninety nine`.
- The special phrase `a large number` is accepted as an unbounded dividend for lower-bound division.
- The special phrase `a large number` is accepted as an unbounded divisor for upper-bound division.
- Division uses `at least` and `at most` as output-only bound language for now.
- Random ranges accept `at least` on the lower endpoint and `at most` on the upper endpoint.
- `at most a large number` caps random generation at the supported finite ceiling.
- `at least a large number` has no supported finite random values.
- Fractions with `a large number` as a bound denominator are not reduced yet.
- `an unknown number` means exact scale was lost; it is not the same as `a large number`.
- Fraction arithmetic may return `an unknown number` when cross-products overflow and the resulting ratio cannot be placed.
- Some exact fraction comparisons may become `unknown` if symbolic cross-products overflow the supported whole-number ceiling.
- No decimals.
- No values less than zero.
- No irrational numbers. Division over bounded integer phrases only produces rational results.
- Repeated subtraction, repeated addition, symbolic range expansion, and trial division prime checks are intentionally slow but acceptable at this scale.
- Overflow past the value `nine hundred and ninety nine` is represented by the renderable sentinel `a large number`, including mixed fractional overflow.
- Fraction wording is pragmatic, not exhaustive English grammar.
- The embedded Python on this machine does not respect the normal package import setup cleanly, so tests and runner insert `src` into `sys.path`.

## Next Useful Moves

1. Add a formal cheat-detector test that fails if forbidden arithmetic operators appear in core modules.
2. Add a stronger exact rational comparison path for cases where symbolic cross-products overflow.
3. Add random expression generation, such as choosing random dividend and divisor phrases for puzzle prompts.
4. Add trace output for symbolic comparisons.
5. Consider an Inform 7-flavoured port now that trace mode exposes the rewrite model.

## What Not To Do Next

- Do not add decimals. That is a different swamp.
- Do not optimize repeated subtraction yet. Speed is not the point.
- Do not broaden English grammar until trace mode has more coverage.
- Do not port to Inform 7 before the rule behaviour is stable.

## Sharp Summary

The machine works. It is not secretly a calculator. It is a small symbolic division goblet where English phrases are broken into slots and bullied through successor, predecessor, comparison, borrowing, and GCD reduction until they confess a fraction.
