# Goblet Manual

Status: living manual

This tool evaluates small English-number arithmetic expressions without converting the phrases into ordinary numeric values for arithmetic.

Supported number phrases run from `zero` through `nine hundred and ninety nine`.

Anything beyond that value ceiling renders as:

```text
a large number
```

If symbolic structure is lost badly enough that the value cannot be placed, it renders as:

```text
an unknown number
```

These are different. `a large number` is known to be beyond the supported ceiling. `an unknown number` could be less than, equal to, or greater than another value.

Mixed fractions may pass just above the whole-number ceiling:

```text
nine hundred and ninety nine and one over nine hundred and ninety nine
```

The symbolic overflow phrase `a large number` means at least one more than the ceiling when it is used as a dividend:

```text
a large number divided by five
becomes at least two hundred

six divided by a large number
becomes at most six over a large number
```

## Run Command

From the repository root:

```powershell
& ..\tools\python-3.13.13-embed-amd64\python.exe run.py "seven times six"
```

## Number Style

Input accepts optional `and`:

```text
one hundred five
one hundred and five
```

Output uses British-style `and` after hundreds:

```text
one hundred and five
nine hundred and ninety nine
```

## Division

Command:

```powershell
& ..\tools\python-3.13.13-embed-amd64\python.exe run.py "twenty seven divided by five"
```

Output:

```text
five and two fifths
```

More examples:

```text
one divided by nine becomes one ninth
two hundred and seventy three divided by fifty two becomes five and one quarter
one divided by twenty one becomes one over twenty one
a large number divided by five becomes at least two hundred
six divided by a large number becomes at most six over a large number
six divided by zero becomes error: division by zero
```

## Multiplication

Command:

```powershell
& ..\tools\python-3.13.13-embed-amd64\python.exe run.py "twelve times twelve"
```

Output:

```text
one hundred and forty four
```

The tool also accepts `multiplied by`:

```text
thirty seven multiplied by twenty seven becomes nine hundred and ninety nine
one hundred times ten becomes a large number
```

## Addition And Subtraction

Commands:

```powershell
& ..\tools\python-3.13.13-embed-amd64\python.exe run.py "seven plus three"
& ..\tools\python-3.13.13-embed-amd64\python.exe run.py "seven minus three"
```

Output:

```text
ten
four
```

Bounded addition preserves the resulting interval:

```text
at most five plus three becomes at least three and at most eight
at least five plus three becomes at least eight
at most five plus at most three becomes at most eight
```

Bounded subtraction preserves results that stay at least zero and names any required condition:

```text
at least five minus three becomes at least two
at most five minus three becomes at most two when the left value is at least three
at most five minus at most three becomes at most five when the left value is at least the right value
```

Subtraction cannot be less than zero. If every possible result would be less than zero, it returns an error.

Fraction addition and subtraction are also supported:

```text
one half plus one third becomes five sixths
one half plus one half becomes one
two thirds minus one third becomes one third
one and one half plus two thirds becomes two and one sixth
five and two fifths plus one third becomes five and eleven fifteenths
```

If exact fraction scale is lost after symbolic overflow, the result becomes:

```text
an unknown number
```

## Symbolic Comparisons

Comparison commands return:

```text
true
false
unknown
likely true; ...
likely false; ...
```

Supported operators:

```text
is greater than
is less than
equals
is equal to
is at least
is at most
```

Examples:

```text
seven is greater than three becomes true
seven divided by three is greater than two becomes true
a large number divided by five is greater than one hundred becomes true
a large number divided by five is greater than two hundred becomes true unless it is two hundred
six divided by a large number is less than one becomes true
six divided by a large number equals zero becomes false
at most five is less than five becomes likely true; false only if it is five
at most five is greater than four becomes likely false; true for values greater than four and at most five
```

Comparison uses interval logic for bounded values. For finite bounded ranges, `likely` means the satisfying subrange is more than half of the total range. For unbounded ranges, the tool avoids likelihood language and names the hinge instead.

Comparisons with `an unknown number` stay unknown because the value cannot be placed:

```text
an unknown number is greater than five becomes unknown
```

Trace mode shows the ranges behind uncertain comparisons:

```powershell
& ..\tools\python-3.13.13-embed-amd64\python.exe run.py --trace "a large number divided by five is greater than two hundred"
```

Output:

```text
a large number divided by five is greater than two hundred
left range: at least two hundred
right range: exactly two hundred
comparison becomes true unless it is two hundred
not guaranteed because the ranges overlap
could be true if the left value lands above the right value
could be false if the left value lands at or below the right value
```

Finite bounded traces can also show true and false regions:

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

## Trace Mode

Trace mode shows the symbolic rewrite steps.

Command:

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

Multiplication trace:

```powershell
& ..\tools\python-3.13.13-embed-amd64\python.exe run.py --trace "three times four"
```

Output:

```text
three times four
zero plus three becomes three; count becomes one
three plus three becomes six; count becomes two
six plus three becomes nine; count becomes three
nine plus three becomes twelve; count becomes four
three times four becomes twelve
```

Fraction trace:

```powershell
& ..\tools\python-3.13.13-embed-amd64\python.exe run.py --trace "one half plus one third"
```

Output:

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

## Random Whole Numbers

Command:

```powershell
& ..\tools\python-3.13.13-embed-amd64\python.exe run.py --random "one hundred and five" "one hundred and ten"
```

Example output:

```text
one hundred and seven
```

The range is inclusive.

Bounds can use `at least` for the lower endpoint and `at most` for the upper endpoint:

```powershell
& ..\tools\python-3.13.13-embed-amd64\python.exe run.py --random "at least eight" "at most twelve"
```

`at most a large number` caps the supported finite range at `nine hundred and ninety nine`. `at least a large number` has no supported finite values and returns an error.

## Prime Checks

Command:

```powershell
& ..\tools\python-3.13.13-embed-amd64\python.exe run.py --prime "seven"
```

Output:

```text
seven is prime
```

Composite example:

```powershell
& ..\tools\python-3.13.13-embed-amd64\python.exe run.py --prime "forty nine"
```

Output:

```text
forty nine is not prime; divisor is seven
```

Prime trace:

```powershell
& ..\tools\python-3.13.13-embed-amd64\python.exe run.py --trace --prime "nine"
```

Output:

```text
nine is at least two
nine divided by two leaves one
nine divided by three leaves zero
nine is not prime; divisor is three
```

## Fraction Wording

Natural denominators use ordinary English where the result reads cleanly:

```text
one half
one quarter
three quarters
two fifths
one thirtieth
one hundredth
```

Compound denominators above twenty use `over`:

```text
one over twenty one
two over one hundred and five
```

## Current Limits

- No decimals.
- No values less than zero.
- No irrational numbers.
- Public addition and subtraction support exact whole numbers and bounded whole-number intervals.
- Public addition and subtraction support exact fractions and mixed numbers.
- Random ranges only generate whole numbers.
- Random ranges accept `at least` on the lower endpoint and `at most` on the upper endpoint.
- Division uses `at least` and `at most` as output-only bound language.
- Comparisons support exact values, exact division expressions, and bounded division expressions.
- Comparison trace mode shows operand ranges and the conditions that would make an unknown comparison true or false.
- Fraction trace mode shows denominator sharing, numerator rewriting, and reduction.
- Finite bounded comparison traces show true and false regions when they can be rendered cleanly.
- Finite bounded comparisons can return `likely true` or `likely false` when symbolic midpoint comparison shows one side occupies more than half the range.
- Fractions with `a large number` as a bound denominator are not reduced yet.
- `an unknown number` means exact scale was lost; it is not the same as `a large number`.
- Fraction arithmetic may return `an unknown number` when cross-products overflow and the resulting ratio cannot be placed.
- Some exact fraction comparisons may become `unknown` if symbolic cross-products overflow the supported whole-number ceiling.
- Prime checking uses slow symbolic trial division.
- Arithmetic inputs are bounded to `zero` through `nine hundred and ninety nine`.

## Internal Rule

The arithmetic path must not use ordinary numeric conversion or ordinary arithmetic operators.

Forbidden in core arithmetic:

```text
int(...)
parseInt
/
//
%
ordinary *
```

The machine is allowed to use Python for control flow, data structures, tests, and random selection. The arithmetic itself must move through symbolic word rules.
