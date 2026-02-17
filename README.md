# Patchwork (v0 scaffold)

This repository contains a Flask + SQLite scaffold for the Data Center Rack-to-Rack Patch Cabling Design Assistant.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
python app.py
```

Open <http://localhost:5000/upload>.

## What is implemented

- Upload `project.yaml`, validate schema, and run deterministic trial allocation.
- Trial page with summary/session preview and export links for `result.json` and `sessions.csv`.
- Save flow that persists Project/Revision/Panels/Modules/Cables/Sessions to SQLite.
- Revision detail and two fixed diff views (logical session diff and physical termination diff).
- Deterministic IDs based on `sha256` (first 16 hex characters).

## Validation commands

```bash
black .
ruff check .
mypy .
pytest -q
pre-commit run --all-files
```
