# Liar's Labyrinth

Status: game design note

## Current Prototype

Liar's Labyrinth is now both a terminal prototype and a static browser
prototype. The browser shell uses Pyodide and the same Python game logic; it is
not a separate JavaScript rewrite.

Run scripted demo:

```powershell
& ..\tools\python-3.13.13-embed-amd64\python.exe run.py --labyrinth examples\liars-labyrinth-demo.txt
```

Run interactive mode:

```powershell
& ..\tools\python-3.13.13-embed-amd64\python.exe run.py --labyrinth-play
```

Run a seeded random script:

```powershell
& ..\tools\python-3.13.13-embed-amd64\python.exe run.py --labyrinth-random examples\liars-labyrinth-demo.txt salt
```

Run play-by-post/session mode:

```powershell
& ..\tools\python-3.13.13-embed-amd64\python.exe run.py --labyrinth-post state.goblet start salt
& ..\tools\python-3.13.13-embed-amd64\python.exe run.py --labyrinth-post state.goblet help
& ..\tools\python-3.13.13-embed-amd64\python.exe run.py --labyrinth-post state.goblet show
```

Run the local browser prototype:

```powershell
& ..\tools\python-3.13.13-embed-amd64\python.exe -m http.server 8000
```

Then open:

```text
http://localhost:8000/web/
```

Double-click launcher:

```text
examples\play-liars-labyrinth.bat
```

Current prototype state:

- three fixed rooms
- seeded random labyrinth generation
- deterministic claimant intentions
- rounds contain per-agent turns
- every mobile agent starts with one turn per round
- speed controls turns per round
- belief, trust, hypothesis, and goal updates exist but are still prototype-grade
- observances are logged as events and can feed simple trust/hypothesis updates
- cup effects resolve immediately
- slap cancels one claimant action
- peril doors kill rather than damage
- claimants can move independently into other rooms
- stationary animal claimants can make claims
- animals do not have hit points and cannot be hurt
- claimant hit points are hidden behind condition words
- present claimants produce fresh claims each round
- agents remember actions they tried and may refuse to repeat failed ones
- agents avoid choosing sleeping witnesses for their own questions when another plan is available
- fixed witnesses may sleep after repeated questioning
- play-by-post/browser sessions persist state through an opaque prototype save
- observances belong to individual agents
- moving to the next room ends the current turn's old-room resolution

Known prototype limits:

- saves are pickle/base64 prototype data, not a public save format
- random generation is useful but not deeply curated yet
- social reasoning is legible but still blunt
- the browser UI is a command shell, not a graphical room view

## Premise

Liar's Labyrinth is a turn-based social hazard crawler.

You are trapped in a maze with unreliable claimants. They make claims, believe or disbelieve each other, announce what they intend to do next, and then try to act. Doors may lead to peril. Cups may poison, heal, distort truthfulness, or change how trustworthy someone appears.

The player is also an agent in the maze, but not necessarily a claimant.

The player can ask, tell, sip, move, slap, and wait.

The core pressure:

```text
you can see intentions, but not truth
you can stop one action, but not the whole room
you can influence belief, but not control minds
```

## Player Verbs

The original core loop is built around five pressure verbs. The prototype now also includes support commands for looking, help, recall, movement aliases, and session control.

```text
ask
tell
sip
move
slap
```

The current prototype also has support verbs:

```text
look
help/actions
recall/remember
push
quit/exit
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

If the target is sleeping, the command is allowed but does not produce an
answer. The player is told the target is sleeping and can choose whether to slap
them awake, wait, or do something else.

Current question shapes:

```text
ask Aster about the brass door
ask Aster if the bone cup is poison
ask Aster whether the iron door leads onward
ask Aster what twenty seven divided by five is
ask Aster if seven is prime
ask Aster liars: Ash calls Bex a liar; Bex calls Ash honest
ask Aster to assess the bone cup
```

The last four are special:

- `what` and numeric `if/whether` questions call Goblet's symbolic engine.
- `liars:` asks a classic honest/liar mini-puzzle.
- `assess` asks the target to weigh testimony, memory, trust, and body evidence.
- The target can still lie about any answer.

### Tell

Tell an agent a claim.

Examples:

```text
tell Bram the brass door leads to peril
tell Vey the bone cup is poisoned
tell Aster Bram is a liar
```

The told agent may believe, doubt, ignore, repeat, or act on it.

Tell can also give an instruction:

```text
tell Bram to drink the glass cup
tell Aster go iron
tell Vey ask Bram about the bone cup
```

Agents may consider instructions, but they are not command handles. Fixed
witnesses cannot act on movement, sip, or ask instructions.

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

Slap can also wake a sleeping agent. Travellers wake easily. Fixed witnesses may
need more than one slap if their sleep is deep. Yes, this is rude. The game
notices.

### Push

Push forces another present agent toward a visible door.

Examples:

```text
push Aster through the iron door
push Aster iron
```

Healthy agents usually resist. Sleeping or badly hurt agents resist poorly.
Witnesses remember push attempts as coercive.

### Look, Help, Recall

These are non-advancing support commands:

```text
look
look Aster
help
help ask
help the bone cup
recall the iron door
remember Bram
```

`look` repeats the room or inspects an agent. `help` exposes command and concept
pages based on the current room. `recall` searches the player's remembered
actions, claims, outcomes, hearsay, and inferences about a topic.

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

Agents use four health quarters, hidden behind condition words.

At zero health, an agent is dead, incapacitated, or lost to the maze. The exact fiction can vary by room, but the state is out of play.

### Speed

Speed controls how many turns an agent gets each round.

Everyone starts with:

```text
speed: 1
```

A speed of 2 means the agent takes two turns in that round. Haste effects may increase speed. Stupor effects may later reduce it.

### Sleep

Sleeping agents miss their chance to act until they wake. They can still be
targeted by player commands, but questions aimed at them do not get useful
answers while they are asleep.

Autonomous agents notice enough to avoid wasting most question plans on sleeping
targets. A default or generated `ask` plan against a sleeping target is treated
as unavailable, and witness selection filters sleepers out before choosing who
to ask. This is not a hard world rule: the player can still try it, and future
systems may let confused or desperate agents make bad calls on purpose. The
default behavior should not spam the log with doomed questions.

Fixed witnesses can also fall asleep after too many questions. This prevents one
stationary oracle from becoming an infinite safe interrogation machine. Tiny
design mercy, delivered with a stick.

### Memory, Recall, And Trust

Agents maintain individual memory entries. Memory tracks:

- actions seen directly
- outcomes seen directly
- claims made
- claims heard from others
- reported claims
- inferences
- trust judgements tied to evidence

`recall THING` shows the player's memory from or about a subject. Agents use
their own memory to form hypotheses, test claims, follow safe crossings, avoid
known hazards, and update trust in witnesses.

Trust is scoped. A witness can become trusted or distrusted about a particular
topic without becoming globally good or bad forever. That keeps the system from
collapsing into one big reputation number wearing a fake moustache.

### Assessment

Assessment is a social summary query:

```text
ask Bram to assess the wax cup
ask Vey assess the silver door
ask Aster assess witnesses
ask Bram assess the wax cup is poison
```

The assessor weighs direct evidence, memory, hearsay, and source trust. Body
evidence beats gossip, but gossip still matters when direct evidence is missing.
The answer can be distorted by the assessor's lie profile.

Assessment is not omniscience. It is a visible way to ask, "what does this pile
of testimony currently imply?"

### Classic Liars Interop

Classic honest/liar puzzles can be asked inside the labyrinth:

```text
ask Aster liars: Ash calls Bex a liar; Bex calls Ash honest
```

This calls the standalone classic solver described in `docs/liars.md`. The
classic puzzle assumes each named person is honest or a liar inside that puzzle.
The labyrinth agent answering can still lie about the result.

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
