# Liar's Labyrinth

Status: game design note

## Current Prototype

A small scripted terminal prototype exists.

Run scripted demo:

```powershell
& ..\tools\python-3.13.13-embed-amd64\python.exe run.py --labyrinth examples\liars-labyrinth-demo.txt
```

Run interactive mode:

```powershell
& ..\tools\python-3.13.13-embed-amd64\python.exe run.py --labyrinth-play
```

Double-click launcher:

```text
examples\play-liars-labyrinth.bat
```

Current prototype limits:

- three fixed rooms
- deterministic claimant intentions
- rounds contain per-agent turns
- every mobile agent starts with one turn per round
- speed controls turns per round
- no real belief update yet
- observances are logged as events, not reasoned over
- cup effects resolve immediately
- slap cancels one claimant action
- peril doors kill rather than damage
- claimants can move independently into other rooms
- stationary animal claimants can make claims
- animals do not have hit points and cannot be hurt
- claimant hit points are hidden behind condition words
- present claimants produce fresh claims each round
- agents remember actions they tried and may refuse to repeat failed ones
- observances belong to individual agents
- moving to the next room ends the current turn's old-room resolution

## Premise

Liar's Labyrinth is a turn-based social hazard crawler.

You are trapped in a maze with unreliable claimants. They make claims, believe or disbelieve each other, announce what they intend to do next, and then try to act. Doors may lead to peril. Cups may poison, heal, distort truthfulness, or change how trustworthy someone appears.

The player is also an agent in the maze, but not necessarily a claimant.

The player can ask, tell, sip, move, and slap.

The core pressure:

```text
you can see intentions, but not truth
you can stop one action, but not the whole room
you can influence belief, but not control minds
```

## Player Verbs

Keep the first playable version to five verbs.

```text
ask
tell
sip
move
slap
```

### Ask

Ask an agent about a claim, object, door, cup, or another claimant.

Examples:

```text
ask Aster about the brass door
ask Bram about Vey
ask Vey about the iron cup
```

An answer is not guaranteed to be true. It is an event that can later become evidence.

### Tell

Tell an agent a claim.

Examples:

```text
tell Bram the brass door leads to peril
tell Vey the bone cup is poisoned
tell Aster Bram is a liar
```

The told agent may believe, doubt, ignore, repeat, or act on it.

### Sip

Drink one fifth from a cup.

Examples:

```text
sip the brass cup
sip the iron cup
```

A sip may poison, heal, grant more actions, remove actions, change truthfulness, or alter perceived trustworthiness.

### Move

Move through a door.

Examples:

```text
move through the brass door
move through the bone door
```

Doors may lead forward, loop back, split the party, hurt the mover, or end the room.

### Slap

Cancel one claimant's intended action this turn.

Examples:

```text
slap Aster
slap Bram
```

The slap is crude, reliable, and socially costly.

It should be funny, but not free. Slapped claimants may lose trust, hide intentions, rush actions, or later refuse help.

## Round Structure

Each round:

1. The room state is shown.
2. Claimants make or repeat claims.
3. Claimants update beliefs.
4. Claimants choose intended actions.
5. The player sees those intended actions.
6. The player takes one scripted action.
7. Unblocked claimant turns resolve according to speed.
8. Cups, doors, poison, antidotes, and injuries resolve.
9. Observances are recorded.

Example intent display:

```text
Aster intends to move through the brass door.
Bram intends to sip the iron cup.
Vey intends to ask Bram about the bone cup.
```

The player has one action by default.

Cup effects may increase or decrease future turns per round.

## Claimants

Each claimant has:

```text
hp: 3
speed: 1
truth rate
belief rate
disbelief rate
nerve
trust map
observances
goals
intended action
```

### Hit Points

Agents have three hit points.

At zero hit points, an agent is dead, incapacitated, or lost to the maze. The exact fiction can vary by room, but the state is out of play.

### Speed

Speed controls how many turns an agent gets each round.

Everyone starts with:

```text
speed: 1
```

A speed of 2 means the agent takes two turns in that round. Haste effects may increase speed. Stupor effects may later reduce it.

### Truth Rate

How often the claimant makes true claims when they speak from available knowledge.

This is not omniscience. A truthful claimant can still be wrong if their belief is wrong.

### Belief And Disbelief

Claimants have rates for accepting or rejecting claims.

They may believe:

- the player
- a trusted claimant
- repeated claims
- claims that match their observances
- claims made confidently

They may disbelieve:

- known liars
- contradicted claims
- claims from slapped agents
- claims that would force them to abandon an intended action

### Nerve

How likely the claimant is to act despite uncertainty.

High nerve claimants open doors and sip cups too early.

Low nerve claimants freeze, ask more questions, or follow others.

## Cups

Cups are full or empty in fifths.

Each fifth is one sip.

Example:

```text
the brass cup: 5/5
the iron cup: 2/5
the bone cup: 0/5
```

Possible cup effects:

```text
poison: lose 1 hp
antidote: remove poison
haste: gain 1 action next turn
stupor: lose 1 action next turn
truth draught: next claim must be true if the speaker knows the truth
liar draught: next claim is inverted
glamour: others perceive the drinker as more truthful
stain: others perceive the drinker as less truthful
clarity: increase belief in observed facts
fog: decrease confidence in observed facts
```

Cup effects should be legible after testing. If a cup changes social trust, the UI must show that something changed, even if the exact mechanism remains uncertain.

## Doors

Doors may lead to safety, progress, peril, loops, or split rooms.

If an agent moves through a door that leads to peril, they die. Peril is not a chip-damage tax. It is a hard maze verdict.

Minimum door states:

```text
safe
peril
unknown
```

Possible door outcomes:

```text
safe passage
1 damage
poison
loop back
separate from group
advance to next room
false exit
```

Do not add elaborate destination lore in the first prototype. Doors are a pressure device first.

## Observances

Agents collect observances.

An observance is a witnessed relation between a claim, an action, and an outcome.

Example:

```text
observance:
  Aster claimed the brass door was safe.
  Bram moved through the brass door.
  Bram took 1 damage.
  Aster's claim was false.
```

Another:

```text
observance:
  Vey claimed the bone cup was antidote.
  Aster sipped the bone cup.
  Aster's poison ended.
  Vey's claim was true.
```

Observances update confidence.

They can affect:

- trust in claimants
- confidence about doors
- confidence about cups
- willingness to act
- willingness to follow the player
- likelihood of announcing true intentions

## Belief State

Each agent maintains beliefs with confidence.

Examples:

```text
Aster is truthful: 60%
Bram is truthful: 20%
the brass door leads to peril: 75%
the iron cup is poisoned: unknown
the bone cup is antidote: 80%
```

Do not pretend this needs exact probability in the first prototype.

Confidence can begin as coarse labels:

```text
unknown
suspected
believed
known
```

The important thing is that agents remember why their beliefs changed.

## Animals

Rooms may contain stationary animals.

Animals do not move through the maze, but they can make claims and they can be liars.

For now, animals do not have hit points and cannot be hurt. They are fixtures of the room's testimony layer, not little party members.

Examples:

```text
the wax moth claims the iron door leads onward.
the iron rook claims the wax cup is poison.
the glass crow claims the salt cup slows the drinker.
```

Animals are not default objects. They are room witnesses.

They should be useful, suspicious, and slightly annoying.

## Intentions

Claimants announce intended actions before they act.

Example:

```text
Aster intends to open the brass door.
Bram intends to sip the iron cup.
Vey intends to wait.
```

The player can use this to triage.

One slap can stop one intended action.

The player should often face two bad intentions and one action.

That is the engine.

## Player As Agent

The player is an agent with:

```text
hp: 3
actions per turn
observances
reputation
```

The player may make claims. Claimants can believe or disbelieve the player.

The player might not be categorized as honest/liar in the same way as claimants, but the maze should still remember player behavior.

If the player lies repeatedly, claimants should adapt.

If the player slaps repeatedly, claimants should adapt.

## Goals

Primary goal:

```text
reach the end of the labyrinth
```

Possible end-state bonuses:

```text
everyone survives
only one person survives
no one drinks poison
all claimants reach the end
you never slap anyone
you slap everyone at least once
you never lie
you escape alone
```

These goals should not all be compatible.

The game should allow ugly success and costly mercy.

## Iteration Between Rooms

The first version should persist state across rooms, not generate a giant campaign.

Persist:

- hp
- poison
- trust
- observances
- confidence about agents
- reputation for slapping or lying
- cup effects with duration
- claimant room position

Do not persist:

- every room object
- every transient claim
- hidden lore not used by behavior

The maze becomes interesting when the player's earlier manipulation survives into later rooms.

## Smallest Prototype

Build the smallest ugly version:

```text
3 rooms
3 claimants
3 hp each
2 doors per room
2 cups per room
1 player action per turn
visible intended actions
slap cancels one claimant action
basic observance log
coarse confidence labels
```

No procedural generation yet.

No animation needed.

No full natural language parser.

## First Prototype Room

Room 1:

```text
doors:
  BrassDoor
  IronDoor

cups:
  BoneCup: 5/5
  GlassCup: 5/5

claimants:
  Aster
  Bram
  Vey
```

Hidden truth:

```text
the brass door leads to peril
the iron door advances
the bone cup is poison
the glass cup grants haste
```

Opening claims:

```text
Aster claims the brass door is safe.
Bram claims the bone cup is poison.
Vey claims Aster is a liar.
```

Initial intentions:

```text
Aster intends to move through the brass door.
Bram intends to sip the glass cup.
Vey intends to ask Bram about the bone cup.
```

Player pressure:

```text
Do you slap Aster, sip the glass cup first, ask Bram for more evidence, or tell Aster not to move?
```

## Why It Might Work

The player is not solving a static riddle.

The player is managing a room full of semi-rational agents about to do stupid things with partial information.

The fun comes from:

- visible intent
- limited intervention
- unreliable testimony
- persistent trust
- dangerous objects
- bad but tempting actions
- deductions that become social leverage

## Hard Part

The hard part is readability.

If agents update beliefs invisibly, the game becomes mush.

If agents explain everything, the game becomes paperwork.

The interface needs to show:

- what each agent intends
- what each agent believes strongly
- what changed this turn
- why an observance mattered

The game dies if the player cannot tell whether they are making a clever intervention or poking a black box.

## Design Rule

Every turn should produce one of these:

```text
I knew it.
I was wrong.
They believed the wrong person.
I can only stop one of them.
I made this worse.
```

If a turn produces none of those, the room is too inert.
