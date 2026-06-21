# Liar's Labyrinth Web Prototype

This is a static Pyodide shell around the existing Python game logic. It does
not need a backend server, but it should be served from a local static server so
the browser can fetch the Python package files.

Run from the repository root:

```bash
python -m http.server 8000
```

Then open:

```text
http://localhost:8000/web/
```

The page stores its opaque local save and transcript in `localStorage` under:

```text
goblet.labyrinth.save
goblet.labyrinth.transcript
goblet.labyrinth.seed
goblet.labyrinth.version
```

The prototype save string is a versioned base64 pickle intended only for this
local browser build. Do not import saves from untrusted sources.
