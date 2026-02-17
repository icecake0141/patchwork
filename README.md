# Patchwork (v0 scaffold)

This is a Flask + SQLite implementation scaffold for the Data Center Rack-to-Rack Patch Cabling Design Assistant.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
python app.py
```

Open <http://localhost:5000/upload>.

## What is implemented

- Upload `project.yaml`, validate schema, run deterministic trial allocation.
- Trial view with summary/session preview and export links for `result.json` and `sessions.csv`.
- Save flow persists Project/Revision/Panels/Modules/Cables/Sessions to SQLite.
- Project detail and fixed two-tab-like diff summary (logical and physical).
- Deterministic IDs (`sha256` first 16 chars).

## Validation commands

```bash
black .
ruff check .
mypy .
pytest
pre-commit run --all-files
```
