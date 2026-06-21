# Witness Machine Interop Note

Status: research captured, benched

## Current Claim

Goblet and Hat should not be merged at the runtime layer yet.

The useful shared idea is not "calculator" and not "language." It is visible computation under constraint: a small machine where every answer leaves inspectable footprints.

Goblet is currently the arithmetic proof domain.
Hat is currently a candidate execution grammar.

The larger possible project is a visible-reasoning workbench for tiny symbolic domains.

## Why This Exists

Recent work on Goblet has made symbolic arithmetic legible:

- English number phrases are parsed into constrained symbolic forms.
- Arithmetic proceeds through successor, predecessor, borrowing, repeated addition, repeated subtraction, reduction, and bounded comparison.
- Trace mode explains the transformation path.
- The implementation intentionally refuses ordinary numeric shortcuts.

Hat explores a neighboring pressure:

- scope literals as values
- explicit and ambient execution modes
- rule-like dispatch through the `?` cascade
- `ret` and `assert` as bounded control flow
- literal values that do not automatically become native host values

The projects may be cousins, or Hat may become a host grammar for Goblet-like proof rituals. That is the research question.

## Shared Shape

| Hat | Goblet | Shared idea |
| --- | --- | --- |
| scopes | symbolic state | meaning lives in containers |
| `do`, `don`, `doff`, `dont` | rewrite and trace modes | execution is a posture |
| `?` cascade | rule dispatch | choose by shape, not brute force |
| `ret` | resolved answer | exit with a value |
| `assert` | contradiction or impossible case | pressure-test the world |
| literals | English number phrases | data is deliberately non-native |
| ambient execution | trace context | invisible rules matter |

## Working Name

Do not call the larger idea `HatGoblet` except as a throwaway merge label.

Possible names:

- Witness Machine
- Proofglass
- Tracewright
- Boundwork
- Lantern Engine
- Rite Engine

Current best label: **Witness Machine**.

It names the point, not the ingredients: computation that can be witnessed.

## Minimal Bridge

Do not combine C and Python yet. Shared plumbing before shared semantics would create adapters without proving the idea.

Make an interop case format first:

```yaml
case: seven plus five
mode: symbolic_arithmetic
expect:
  result: twelve
  trace_contains:
    - seven plus five
    - successor
    - becomes twelve
```

Both projects could eventually consume or emit this kind of artifact:

- Goblet can already emit result and trace text.
- Hat could be tested against the same proof cases if it grows symbolic rewrite support.
- The case format gives shared gravity before shared runtime.

## Killer Experiment

Take one Goblet operation and express it as Hat-shaped pseudocode.

Start with successor addition:

```text
add ?
  (left is zero) : ret right;

  (right is zero) : ret left;

  (*) :
    do trace "decrement right";
    do trace "increment left";
    ret add successor(left) predecessor(right);
```

This is not proposed Hat syntax. It is the target shape.

If this expresses cleanly, Hat may be a viable rule host.
If it gets ugly immediately, Hat is conceptual kin, not infrastructure.

That distinction matters. Do not weld the bones together just because they rhyme.

## Possible Larger Whole

A visible-reasoning workbench for tiny symbolic domains:

- arithmetic
- fractions
- bounded comparisons
- grammar transforms
- toy legal rules
- inventory logic
- game-rule adjudication
- small oracle systems

Goblet would supply explainable symbolic operations.
Hat would supply bounded execution grammar.

The union is not a calculator. It is a small machine for making thought inspectable.

## What Not To Do Next

- Do not embed Python in C or C in Python yet.
- Do not port Goblet into Hat until one Hat-shaped operation is pleasant to express.
- Do not rename Goblet around this larger idea.
- Do not broaden Goblet's arithmetic surface just to feed the larger concept.
- Do not turn this into a PRD until there is an actual workflow and user.

## Honest Next Moves

Resume only if one of these becomes true:

- Hat grows enough syntax to express successor addition as a rule ritual.
- Goblet needs a declarative trace or rewrite rule layer.
- A shared test corpus would help both projects.
- There is a concrete demo target for visible reasoning beyond arithmetic.

First practical task if resumed:

1. Write three interop cases in a tiny YAML or Markdown format.
2. Include one exact arithmetic case, one bounded comparison case, and one contradiction/impossible case.
3. Try to express the exact arithmetic case in Hat-shaped pseudocode.
4. Decide whether Hat is host, cousin, or reference.

## Evidence

Commands that verified Goblet's current state:

```powershell
& ..\tools\python-3.13.13-embed-amd64\python.exe -m unittest discover -s tests
```

Result:

```text
Ran 19 tests
OK
```

Relevant artifacts:

- `README.md`
- `reports/handoff-report.md`
- `docs/bounded-legible-reasoning.md`
- `src/goblet/relation.py`
- `tests/test_no_cheating.py`

