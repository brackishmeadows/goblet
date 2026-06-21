# Suspicion And Puzzle Audit Goblet

Status: branch design note

## Thesis

Goblet does not need to become a general riddle solver.

The stronger branch is a bounded puzzle adjudicator: a small deterministic engine for liars, poison, testimony, hidden states, possible worlds, and puzzle fairness.

Arithmetic Goblet proves:

```text
numbers can stay words while reasoning happens
```

Suspicion Goblet should prove:

```text
uncertainty can stay structured while suspicion happens
```

Puzzle Audit Goblet should prove:

```text
small puzzle systems can be audited before they waste a table's time
```

## What Carries Over

The current Goblet already has the important shape:

- constrained language
- explicit states
- traceable transformations
- refusal to overclaim
- answers like `true`, `false`, `unknown`, `true only if`, and `true unless`

The next branch should keep that discipline. Do not let prose riddles turn the cup into a fog machine.

## Suspicion Goblet

Suspicion Goblet reasons over small worlds with hidden states.

Useful domains:

- liars and truth-tellers
- poison cups and vial safety
- witness testimony
- doors, guards, and traps
- limited tests with delayed results

The engine should output:

```text
forced
impossible
ambiguous
consistent
contradiction
one world remains
three worlds remain
true in all worlds
false in all worlds
true only if Aster is lying
poisoned unless the brass cup contains antidote
```

The key feature is not the answer. The key feature is the trial of worlds.

## Example Naming Rules

Goblet examples should avoid generic placeholder names like `Alice`, `Bob`, `Carol`, `Dave`, `Red`, `Blue`, and `Green`, unless the point is explicitly to contrast with older logic-puzzle forms.

Goblet names should be small, concrete, and memorable, but each word should belong to only one category. Do not reuse the same word across people, materials, objects, and animals.

Core rule:

```text
one word, one shelf
```

People names name people.
Materials name substances.
Object names name objects.
Animal names name animals.

Do not rely on vibes to decide category. If a word could naturally be an object, animal, or material, do not use it as a person name.

### People Names

Use these for speakers, witnesses, suspects, guards, liars, truth-tellers, poisoners, victims, and other human or human-like actors.

The first two default people should stay A/B-coded for readability in tiny examples, but should not use generic placeholder names like `Alice` and `Bob`.

```text
Aster
Bram
Vey
Marn
Kess
Lio
Nera
Senn
Tavi
Orra
Jory
Hale
Mira
Voss
```

People names should not be common object names, animal names, or material names.

Avoid as people names:

```text
Alice
Bob
Bell
Moth
Rook
Candle
Wick
Thorn
Salt
Ash
Brass
Iron
Crow
Hare
```

### Materials

Use these only as materials or modifiers for physical objects.

```text
Ash
Salt
Brass
Iron
Bone
Silver
Glass
Wax
Flint
Oak
Copper
Pewter
```

Preferred use:

```text
objects:
  BrassBell
  GlassKey
  BoneMask
```

Rendered as:

```text
the brass bell
the glass key
the bone mask
```

Avoid using bare material names as objects unless the puzzle explicitly treats the material itself as the object.

### Object Names

Use these for small concrete puzzle objects.

Default object names should be distinct, singular, handheld objects of roughly similar scale: the kind of things that could be hidden in the same breadbox. Avoid broad puzzle-domain nouns like `Cup` and `Door` here because those are likely to be promoted into significant puzzle sets.

```text
Bell
Clock
Knife
Mask
Brush
Key
Lantern
Needle
Mirror
Comb
Coin
Spoon
Vial
Locket
Thimble
```

Standalone examples:

```text
objects:
  Bell
  Knife
  Mirror
```

Composite examples:

```text
objects:
  BrassBell
  IronKnife
  SilverMirror
  WaxLocket
```

### Animal Names

Use these only for animals, familiars, test subjects, tokens, signs, or creature roles.

```text
Moth
Rook
Hare
Crow
Wasp
Eel
Marten
Stag
Viper
Toad
Finch
Adder
```

Do not use animal names as default people names.

### Composite Object Rule

When naming physical objects, prefer:

```text
Material + ObjectName
```

Examples:

```text
  BrassBell
  IronKey
  WaxMask
  CopperNeedle
  PewterVial
  GlassMirror
  BoneComb
```

This keeps the categories clear:

```text
Brass = material
Bell = object
BrassBell = object
BrassBell renders as the brass bell
```

Composite identifiers are parser names. Render them as definite lowercase room objects:

```text
BrassCup -> the brass cup
IronKey -> the iron key
BoneMask -> the bone mask
```

### Category Discipline

A word bank is not a mood list. Each bank has a job.

Bad:

```text
people:
  Bell
  Moth

objects:
  Bell
```

Good:

```text
people:
  Aster
  Bram

objects:
  Bell
  BrassBell

animals:
  Moth
```

If a puzzle intentionally breaks a category, it must say so explicitly. Otherwise, use the category banks exactly.

## First Prototype: Liars

Start with liars before riddles.

Riddles are prose-shaped. Liars are bounded little murder-boxes.

Minimum model:

```text
people:
  Aster
  Bram

kinds:
  honest
  liar

rules:
  honest statements are true
  liar statements are false

statements:
  Aster calls Bram a liar
  Bram calls Aster a liar
```

Expected output:

```text
ambiguous
possible worlds:
- Aster honest, Bram liar
- Aster liar, Bram honest
```

Trace requirement:

```text
suppose that Aster is honest and Bram is honest.
Aster calls Bram a liar
but we supposed Aster honest, so we cannot allow this
```

The trace should show which statement kills each branch.

Calls assign a kind to a person. They do not affirm or deny another claim.

Later claim-level grammar should use separate verbs:

```text
Aster claims the brass cup is poisoned
Bram denies Aster's claim
Vey affirms Bram's claim
```

## First File Format

Define the smallest `.goblet-liars` shape before implementing clever statements.

```text
people:
  Aster
  Bram

statements:
  Aster calls Bram a liar
  Bram calls Aster a liar
```

Supported v0 statement forms:

```text
[person] calls [person] honest
[person] calls [person] a liar
```

Supported v0 output:

```text
ambiguous
contradiction
possible worlds
trace rejected worlds
```

Explicit v0 non-goals:

- no nested statements
- no `and`
- no `or`
- no alternators
- no random speakers
- no prose clues
- no puzzle generation

## Possible Worlds Policy

The engine should not force a single solution when the rules do not.

For example:

```text
Aster calls Bram honest.
```

Possible output:

```text
ambiguous
possible worlds:
- Aster honest, Bram honest
- Aster liar, Bram liar
```

This is very Goblet. Preserve the fog in a labeled jar.

## Cup Poison Branch

Cups are a puzzle-significant object set. Do not treat `Cup` as a default breadbox object.

Cup poison puzzles reason over whether each cup may be safe, poisoned, or still unknown.

Poison is a good early branch because it looks like arithmetic but behaves like danger.

Minimum model:

```text
cups:
  BrassCup
  IronCup
  BoneCup

states:
  safe
  poisoned
  unknown

rules:
  exactly one cup is poisoned
  BrassCup is safe
  if IronCup is poisoned then BoneCup is safe
```

Possible outputs:

```text
the brass cup is safe
the iron cup or the bone cup is poisoned
```

or, if constraints force it:

```text
the bone cup is poisoned
```

In this specific example, the rule `if IronCup is poisoned then BoneCup is safe` is redundant once `exactly one cup is poisoned` is already active. It would render as `if the iron cup is poisoned then the bone cup is safe`. That redundancy is not a flaw in the note; it is a perfect audit specimen:

```text
warning:
rule 3 discriminates no worlds under current constraints
```

Later poison states can include:

```text
safe
poisoned
unknown
contaminated
antidote
fatal
```

Do not add all of them at once. That is how a logic swamp crowns itself.

## Door Peril Branch

Doors are a puzzle-significant object set. Do not treat `Door` as a default breadbox object.

Door peril puzzles reason over whether each door may lead to safety, peril, or an unknown result.

Minimum model:

```text
doors:
  BrassDoor
  IronDoor
  BoneDoor

states:
  safe
  peril
  unknown

rules:
  exactly one door leads to peril
  the brass door is safe
  if the iron door leads to peril then the bone door is safe
```

Possible outputs:

```text
the brass door is safe
the iron door or the bone door leads to peril
```

or, if constraints force it:

```text
the bone door leads to peril
```

Door rendering should follow the same composite-object rule:

```text
BrassDoor -> the brass door
IronDoor -> the iron door
BoneDoor -> the bone door
```

Do not add destination lore yet. `peril` is a state, not a scene generator.

## Puzzle Audit Goblet

Puzzle Audit Goblet is not a solver. It is a small puzzle-system auditor.

Related note: [Cryptic Adventure Design](cryptic-adventure-design.md), for the table-puzzle discipline of making problems cryptic enough to feel discovered but legible enough for a small group to solve in about ten minutes.

Game branch: [Liar's Labyrinth](liars-labyrinth.md), for an iterated turn-based maze where claimants form beliefs, announce intentions, drink from cups, move through perilous doors, and can be slapped out of bad actions.

Target use:

```text
Can this D&D or room-escape group puzzle be solved in five to ten minutes?
Is it fair?
Does it have one intended solution?
Does it require hidden lore?
Are there alternate answers the author missed?
Which clue actually discriminates?
```

Input shape:

- states
- moves
- observations
- win condition
- intended discovery

Output shape:

- possible worlds
- shortest solution path
- alternate solution paths
- ambiguity warnings
- hidden assumption warnings
- difficulty estimate
- clue suggestions

## Discriminating Clues

Make clue work visible.

For each clue, Puzzle Audit Goblet should be able to report how many worlds it kills:

```text
audit:
8 possible worlds before clues
4 survive after clue 1
4 survive after clue 2
2 survive after clue 3
1 survives after clue 4

warning:
clue 2 discriminates no worlds
```

This catches author-bloat. A clue that kills zero worlds may still be atmospheric, but it is not doing logic work. The tool should name that plainly.

## Solvability Shape

Do not merely say `solvable`. Say how the puzzle is solvable.

| Shape | Meaning |
| - | - |
| forced | one solution follows from the stated clues |
| ambiguous | multiple worlds survive |
| overconstrained | no worlds survive |
| redundant | some clues do no work |
| fragile | one clue carries the whole puzzle |
| hidden-assumption | solution requires a rule not stated |
| interaction-required | cannot solve from starting clues; players must test |
| feedback-loop | each action reveals new constraints |

## Puzzle Discovery Shape

A good small group puzzle has:

| Layer | Job |
| - | - |
| Surface | objects, suspects, vials, doors, machines, offerings |
| Moves | what players can try without asking permission |
| Feedback | every move teaches something |
| Discovery | the hidden rule the group is meant to notice |
| Click | the moment the group notices the rule |
| Resolution | one satisfying application of the discovered rule |

The answer is not a word. The answer is a discovered rule.

## Discovery Types

Useful discovery patterns:

| Pattern | Discovery |
| - | - |
| Invariant | something stays constant across transformations |
| Bottleneck | the obvious resource is not the limiting one |
| Information encoding | tests can label possibilities, not only eliminate them |
| Symmetry break | two identical cases differ by one controllable feature |
| Phase shift | the rule changes after observation, time, or sacrifice |
| Local optimum trap | the greedy move works early and fails later |
| Witness logic | one example proves possibility, one counterexample kills certainty |
| Role relocation | truth, poison, or danger attaches to position, time, light, or action, not identity |

This is the generator table. Start here, then dress the puzzle.

## Five To Ten Minute Rule

Use:

- three to seven objects
- two to four possible actions
- one hidden rule
- one misleading but fair interpretation
- feedback after every action
- one final application of the discovered rule

Avoid:

- required puns
- author mind-reading
- obscure real-world facts
- no feedback until the end
- twelve symbols and four alphabets

That last one is escape-room sludge: many locks, not enough truth.

## Example Discovery: Production Before Revelation

Surface:

```text
Three tally stations: BrassBell, IronKey, BoneComb.
BrassBell doubles tokens.
IronKey turns three tokens into five.
BoneComb spends one token to reveal one letter.
The door opens when LOCK is revealed.
You begin with four tokens.
```

Phase rule:

```text
Before any BoneComb pass:
  BrassBell doubles
  IronKey converts three to five

After one BoneComb pass:
  BrassBell adds one
  IronKey converts two to three

After two BoneComb passes:
  BrassBell does nothing
  IronKey converts one to one

After three BoneComb passes:
  all production stops
```

Discovery:

```text
Discovery has a cost.
Observe too early and you collapse the productive system.
```

Audit question:

```text
Can the players produce enough tokens before revelation makes production useless?
```

## Suggested Module Split

Keep arithmetic intact. Add suspicion as a separate branch.

```text
goblet.logic
  truth, falsehood, implication, possible worlds

goblet.liars
  speakers, statements, honest/liar rules

goblet.poison
  cups, vials, safety states, mixing, testing

goblet.doors
  doors, safety/peril states, passage constraints

goblet.audit
  states, moves, observations, win conditions, fairness audit
```

Do not start with `goblet.riddles`. Riddles should arrive later as clue predicates, not as freeform prose.

## CLI Sketch

Separate subcommands are clearer than one overloaded expression parser:

```text
goblet liars puzzle.txt
goblet liars --trace puzzle.txt
goblet liars --worlds puzzle.txt
goblet poison puzzle.txt
goblet poison --capacity rats=3 rounds=1
goblet audit puzzle.txt
```

The arithmetic expression CLI can remain as-is while this branch grows beside it.

## What Not To Do

- Do not build a general riddle solver.
- Do not start with natural-language clue interpretation.
- Do not add alternators, cowards, random speakers, or domain freaks before honest/liar works.
- Do not generate polished fantasy skin before the puzzle system is checkable.
- Do not call a puzzle fair if it depends on hidden lore.
- Do not collapse ambiguity into a single answer because the author wanted one.

## Current Small Example

The smallest `goblet.liars` prototype exists.

It can:

1. Parse a tiny controlled file format with people and statements.
2. Enumerate all honest/liar worlds.
3. Evaluate each statement in each world.
4. Reject contradictory worlds.
5. Render surviving worlds.
6. Trace which statement killed each rejected branch.
7. Group rejected worlds by the reason they were rejected.

Example:

```text
people:
  Aster
  Bram

statements:
  Aster calls Bram a liar
  Bram calls Aster a liar
```

Output:

```text
ambiguous
possible worlds:
- Aster honest, Bram liar
- Aster liar, Bram honest
```

Trace excerpt:

```text
suppose that Aster is honest and Bram is honest.
Aster calls Bram a liar
but we supposed Aster honest, so we cannot allow this
```

## Next Honest Move

Decide the first extension:

- add external facts, so `forced` worlds can appear in v0-style puzzles
- add `different kinds`
- add `exactly one of [person] and [person] is honest`
- add clue discrimination counts for liar statements

Do not add nested speech yet.
