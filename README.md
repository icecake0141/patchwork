<!--
Copyright 2026 Patchwork Authors
SPDX-License-Identifier: Apache-2.0

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

This file was created or modified with the assistance of an AI (Large Language Model).
Review required for correctness, security, and licensing.
-->

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

## Continuous Integration (CI)
GitHub Actions runs the following checks on push/pull request:
- `ruff check .`
- `black --check .`
- `mypy .`
- `pytest -q`
- `pre-commit run --all-files`

Workflow file: `.github/workflows/ci.yml`

## Validation commands
```bash
ruff check .
black --check .
mypy .
pytest
```
