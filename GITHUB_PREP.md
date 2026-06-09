# GitHub Prep

Status: ready to publish

## Current State

This directory is shaped as a standalone Python repository:

- package source in `src/goblet/`
- tests in `tests/`
- public runner in `run.py`
- package metadata in `pyproject.toml`
- GitHub Actions test workflow in `.github/workflows/tests.yml`
- project docs in `README.md`, `MANUAL.md`, `PRD.md`, and `docs/`

## License

MIT license is included in `LICENSE`.

## Suggested First Commit

```powershell
git init
git add .
git commit -m "Initial Goblet symbolic reasoning engine"
```

## Suggested Remote Push

After creating an empty GitHub repo:

```powershell
git branch -M main
git remote add origin https://github.com/<user>/goblet.git
git push -u origin main
```

## Verification

From this directory:

```powershell
python -m unittest discover -s tests
```

Local field-office command:

```powershell
& ..\tools\python-3.13.13-embed-amd64\python.exe -m unittest discover -s tests
```
