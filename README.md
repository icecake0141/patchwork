# Patchwork (v0)

Data Center Rack-to-Rack Patch Cabling Design Assistant.

## Features
- Flask WebUI + SQLite persistence.
- Upload `project.yaml`, run deterministic trial allocation, then save revision.
- Exports: `sessions.csv`, `result.json`.
- SVG output: topology, rack occupancy, pair detail.
- Revision diff: logical (`session_id`) and physical (termination location).

## Run
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open http://localhost:5000/upload

## Validation commands
```bash
ruff check .
black --check .
mypy .
pytest
```
