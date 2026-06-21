# Classic Liars Puzzles

Status: current implementation note

`src/goblet/liars.py` solves small honest/liar logic puzzles by enumerating all
possible worlds and rejecting worlds where a speaker's honesty does not match
the truth of their statement.

This module is separate from Liar's Labyrinth social simulation. In classic
liars puzzles, each person is simply `honest` or `liar` for the whole puzzle.
In the labyrinth, agents can have fractional lie profiles, partial memories,
trust shifts, and bad information. Do not blur those models together. That way
lies the soft swamp.

## CLI

Run a puzzle file:

```powershell
python run.py --liars examples\aster-bram.goblet-liars
```

Trace the rejected worlds:

```powershell
python run.py --trace --liars examples\aster-bram.goblet-liars
```

Installed package form:

```powershell
python -m goblet --liars examples\aster-bram.goblet-liars
python -m goblet --trace --liars examples\aster-bram.goblet-liars
```

## File Format

Puzzle files have two sections:

```text
people:
  Aster
  Bram

statements:
  Aster calls Bram a liar
  Bram calls Aster a liar
```

Supported statement forms:

```text
NAME calls NAME honest
NAME calls NAME a liar
```

Names in statements must appear in `people:`. Duplicate people are rejected.

## Output

If no worlds survive:

```text
contradiction
no possible worlds
```

If exactly one world survives:

```text
forced
possible world:
- Aster honest, Bram liar
```

If multiple worlds survive:

```text
ambiguous
possible worlds:
- Aster honest, Bram liar
- Aster liar, Bram honest
```

Trace mode prints each supposed world, the first contradiction that rejects it,
the surviving worlds, and a grouped summary of rejected worlds.

## Example Files

Current examples:

- `examples/aster-bram.goblet-liars`
- `examples/single-claim.goblet-liars`
- `examples/self-snare.goblet-liars`
- `examples/three-witnesses.goblet-liars`
- `examples/echo-pair.goblet-liars`
- `examples/free-third.goblet-liars`
- `examples/cross-snare.goblet-liars`

The test suite checks these examples as executable documentation.

## Labyrinth Interop

Inside Liar's Labyrinth, agents can be asked a one-line classic puzzle:

```text
ask Aster liars: Ash calls Bex a liar; Bex calls Ash honest
```

The asked agent can still lie about the result according to labyrinth rules.
The puzzle model remains classic honest/liar logic; the speaker's answer is a
labyrinth social event.
