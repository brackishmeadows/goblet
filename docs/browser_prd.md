# PRD: Liar's Labyrinth Browser Prototype

## Status

Draft for Codex implementation.

## Summary

Ship **Liar's Labyrinth** as a static browser-playable text game using the existing Python game logic. The browser version should preserve the command-first feel of the terminal game while adding enough page structure to make it playable without a terminal.

The intended first build is a **static Pyodide prototype**: the browser downloads Pyodide, loads the `goblet` Python package, runs the labyrinth locally, and stores the save in browser storage. No server is required.

## Goals

- Run Liar's Labyrinth in a browser from static files.
- Reuse the existing Python game logic rather than rewriting the game in JavaScript.
- Provide a small browser-safe session API that can also be used by CLI/play-by-post tests.
- Preserve determinism: same code, same seed, same command sequence should produce the same transcript.
- Persist local game state between page reloads.
- Support transcript export/copy for sharing play logs.
- Keep the command line as the primary interface.

## Non-goals

- Do not build accounts, multiplayer, server persistence, or cloud saves.
- Do not rewrite the game engine in JavaScript.
- Do not make a fully graphical interface in the first pass.
- Do not require a backend service.
- Do not make the browser save format a public compatibility promise in the prototype, though it should be versioned.

## Target user experience

A player opens a web page and sees:

- title: `Liar's Labyrinth`
- seed/new game controls
- a transcript pane
- a command input
- a submit button
- small buttons for `help`, `look`, `recall`, `export transcript`, `reset`
- current save status, such as `saved locally`

Basic flow:

1. Player opens the page.
2. If a local save exists, the page offers `continue` and `new game`.
3. Player starts or continues a game.
4. The game prints the room state.
5. Player types commands like `ask toad assess glass cup`.
6. The browser sends the command to Python via Pyodide.
7. Python returns output lines and updated state.
8. The page appends the output to the transcript and stores the updated state locally.

## Recommended architecture

### Static files

Add a web prototype directory, for example:

```text
web/
  index.html
  app.js
  style.css
  README.md
```

The static web build should load the existing Python package:

```text
goblet/
  __init__.py
  labyrinth.py
  liars.py
  ...
```

The browser will use Pyodide to import a browser session module from the Python package.

### Python browser API

Add a browser-safe API module. Suggested path:

```text
goblet/browser_session.py
```

The API should hide CLI/file-system details and expose pure-ish session operations.

Suggested interface:

```python
def start(seed: str | int | None = None) -> dict:
    """Return a serializable packet containing initial state and output lines."""


def show(save_data: str) -> dict:
    """Return output lines for the current state without advancing the game."""


def step(save_data: str, command: str) -> dict:
    """Apply one command and return updated save data plus output lines."""


def export_transcript(save_data: str) -> str:
    """Return the accumulated transcript as plain text."""
```

Suggested packet shape:

```python
{
    "version": 1,
    "seed": "775070",
    "status": "playing",  # playing | dead | escaped | resigned
    "save_data": "...",   # opaque encoded state for localStorage
    "lines": ["..."],
    "transcript": "...",  # optional; can be stored separately in JS
}
```

### State format

For the prototype, use a simple opaque save string:

- pickle the `LabyrinthPostSession` or equivalent state object
- base64-encode the bytes
- wrap with a small version header

Example:

```text
GOBLET_LABYRINTH_SAVE_V1:<base64 pickle>
```

This is acceptable for a local prototype because the save is only loaded by the same local code. It is not a secure interchange format and should not be imported from untrusted sources without warning.

Later, migrate to a JSON save format if sharing saves or long-term compatibility becomes important.

### Browser storage

Use `localStorage` for the first pass:

```text
goblet.labyrinth.save
goblet.labyrinth.transcript
goblet.labyrinth.seed
goblet.labyrinth.version
```

If save strings become too large, move to IndexedDB.

### JavaScript responsibilities

`app.js` should:

- load Pyodide
- mount/load the `goblet` package files so Python can import them
- call `goblet.browser_session.start/show/step`
- render output lines into the transcript pane
- persist save data and transcript after each command
- handle Enter key submission
- disable input while Pyodide is loading or a command is running
- provide clear errors if Pyodide fails to load

### Python responsibilities

The Python game should remain authoritative for:

- command parsing
- state transitions
- deterministic logic
- game output lines
- save/load encoding
- transcript export formatting where useful

The browser should not duplicate game rules.

## UI requirements

### Required first pass UI

- `New game` button
- optional seed input
- `Continue` button if save exists
- transcript/output pane
- command input
- `Submit` button
- `Help` button that sends `help`
- `Look` button that sends `look`
- `Export transcript` button
- `Reset` button with confirmation
- visible loading state while Pyodide loads

### Nice-to-have UI

- clickable suggested commands from help output
- current room sidebar showing visible agents, cups, and doors
- copy transcript button
- download transcript button
- save export/import for debugging
- seed shown in the UI
- mobile-friendly input focus behaviour

## Determinism requirement

The browser build must preserve this contract:

```text
same code + same seed + same command sequence = same observable transcript
```

Add or keep a regression test that runs the same seed and command sequence twice and compares normalized transcripts.

Suggested test command sequence:

```text
help bex go silver
bex go silver
ask toad assess glass cup
slap toad
ask toad assess silver cup
```

Expected behaviour:

- transcripts match after normalizing file paths or browser-specific metadata
- `show` does not advance the game
- local save/load does not change output

## Acceptance criteria

The first browser prototype is complete when:

- A user can open `web/index.html` from a static server and start a new seeded game.
- The game prints the initial labyrinth output.
- The user can enter a command and receive the correct next output.
- The game state persists across page reloads.
- `help`, `look`, and normal command input work.
- Transcript export produces a readable plain-text log.
- No backend server is required.
- The existing CLI still works.
- Existing Python compile/smoke tests pass.
- Determinism test passes for two identical seeded browser/session runs.

## Implementation plan

### Phase 1: Session API

1. Add `goblet/browser_session.py`.
2. Reuse existing play-by-post/session functions where possible.
3. Add save encoding/decoding helpers:
   - `encode_session(session) -> str`
   - `decode_session(save_data) -> session`
4. Add `start`, `show`, `step`, and `export_transcript` functions.
5. Add unit/smoke tests for API determinism.

### Phase 2: Static web shell

1. Add `web/index.html`, `web/app.js`, and `web/style.css`.
2. Load Pyodide from CDN for the prototype.
3. Load the `goblet` package into Pyodide.
4. Implement start/continue/step UI.
5. Store save data and transcript in localStorage.
6. Add loading and error states.

### Phase 3: Packaging and docs

1. Add `web/README.md` with local test instructions.
2. Document that the first prototype requires serving files from a local static server rather than opening `file://` directly.
3. Suggested local server command:

```bash
python -m http.server 8000
```

4. Document GitHub Pages or itch.io static upload path.

### Phase 4: Polish

1. Add command suggestion buttons for common commands.
2. Add export/download transcript.
3. Add save import/export if useful for bug reports.
4. Improve mobile layout.

## Open questions

- Should the first save format be pickle/base64 or should Codex go directly to JSON?
- Should the browser build hide or expose the experimental classic `liars:` question form?
- Should assessment output be collapsible when it gets long?
- Should the UI show current room entities as clickable command helpers?
- Should static deployment pin a specific Pyodide version?

## Notes for Codex

- Do not change the core game rules while implementing browser support.
- Prefer a thin API layer over moving CLI-specific behaviour into JavaScript.
- Keep the browser API deterministic and easy to smoke test from normal Python.
- The command parser remains the main interface. The browser UI is a frame around the teletype, not a replacement for it.
- Avoid adding non-stdlib Python dependencies unless absolutely necessary for the web build.
