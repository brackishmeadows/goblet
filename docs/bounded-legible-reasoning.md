# Bounded Legible Reasoning

Status: design note

## Thesis

The broader experiment is not just symbolic arithmetic.

It is bounded legible reasoning: small deterministic systems that reason in constrained human-readable language without collapsing into fake intelligence or sterile formalism.

Goblet is the first specimen. Its real value is the answer grammar it has developed:

```text
true
false
unknown
true unless it is two hundred
likely false; true for values greater than four and at most five
at least two hundred
at most six over a large number
an unknown number
```

This grammar is useful when the honest answer is conditional, partial, or bounded.

## Core Pattern

The engine should:

- use constrained English
- preserve uncertainty
- expose transformations
- refuse hidden coercion
- render results as conditional language
- stop at the edge of its rulebox

The point is not to simulate general intelligence. The point is to make a narrow reasoner that does not lie about its jurisdiction.

## Answer Grammar

Most software wants one of two shapes:

```text
true / false
```

or:

```text
number with decimal confidence
```

This engine is allowed to answer with more useful intermediate shapes:

```text
unknown
true unless...
true only if...
likely true; false only if...
likely false; true for values...
at least...
at most...
```

This is not Bayesian reasoning. Do not invent a prior.

Use `likely` only when a finite bounded range can be split by a midpoint or satisfying span. For unbounded ranges, give a witness range, exception, or hinge instead.

## Large Versus Unknown

`a large number` and `an unknown number` are not the same.

`a large number` means the value is definitely beyond the supported ceiling.

`an unknown number` means the system lost enough structure that the value cannot be placed. It may be less than, equal to, or greater than another value.

This distinction matters because overflow is not always magnitude. A ratio with a large numerator and a large denominator might be small, equal to one, large, or reducible if its hidden structure were known.

## Hidden Assumptions

The engine forces shortcuts to become explicit.

Instead of silently turning a phrase into a primitive number, it exposes the movement:

```text
subtract five repeatedly
quotient grows
remainder remains
fraction reduces
```

The same trace style can apply outside arithmetic:

```text
member may use the tool if induction is complete
induction is not complete
therefore tool use is not allowed
```

The value is not sophistication. The value is making the hinge visible.

## Controlled English As Executable Specification

Many real systems have rules that are written in human-ish language:

```text
discount applies if total is at least twenty dollars
users may cancel at least twenty four hours before booking
members may access tools after induction
```

The useful target is not full natural-language understanding. It is controlled English as executable specification: narrow grammar, explicit states, testable outcomes.

## Useful Domains

This pattern may fit small domains where rules matter more than fluency:

- coupon and deal logic
- grocery threshold decisions
- budgeting with incomplete information
- tabletop and board-game adjudication
- membership and access systems
- rent or resource stress models
- scheduling uncertainty
- bounded planning games
- eligibility and requirement checking

The engine is not smarter than a language model. It is more stubborn. That is the feature.

## Partial Worlds

The symbolic values also suggest a pattern for partially instantiated worlds:

```text
site is known to exist
site size is an unknown number
danger is at least seven
debt is at most five favors
```

Rules can operate before everything is generated or known.

This is useful for game logic, procedural fiction, simulations with fog, and document games where the world exists partly as constraints.

## AI Auditing

A narrow symbolic engine can check the parts of a fluent answer that are actually rule-shaped.

Example:

```text
LLM claim: this always follows
symbolic check: true only if the value is greater than four
```

This is not "AI verifies AI" mush. It is a small deterministic checker catching overconfident claims inside a narrow domain.

## Creative Branch

The richest creative branch is rules as prose, prose as rules.

Examples:

```text
the door opens if the key is held and the moon is not absent
the curse weakens when three promises are kept
the debt is at least seven favors
```

The surface can be poetic. The adjudicator underneath should be deterministic.

This connects naturally to:

- Inform-style systems
- tabletop engines
- Hat-like controlled documents
- symbolic state machines
- procedural fiction

## Shed Rule

Do not let this become the whole house.

This should remain a small deterministic clerk with a documented jurisdiction. It can live in a shed:

- a folder
- a CLI
- a testing module
- a documented symbolic reasoning goblet
- a side-lab with limits and a broom in the corner

The risk is not apocalypse. The risk is accidental infrastructure.

Keep the shed. Visit it. Do not let it move into the bedroom.

## What Not To Do

- Do not broaden into general natural-language understanding.
- Do not use probability language without a finite bounded basis.
- Do not let undefined words sneak into rendered output.
- Do not hide coercions into primitive arithmetic.
- Do not make every future project depend on this.

## Next Honest Moves

- Add fraction addition and subtraction while preserving exact structure where possible.
- Use `an unknown number` when fraction overflow loses scale.
- Add trace output that explains why exact fraction placement was lost.
- Add a cheat-detector test for forbidden arithmetic shortcuts.
- Try one non-arithmetic controlled-English rule domain as a separate experiment.
