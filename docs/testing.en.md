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

# Testing & Validation

## Local Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Required Validation Commands
- Lint: `ruff check .`
- Format check: `black --check .`
- Type check: `mypy .`
- Unit/integration tests: `pytest -q`
- Pre-commit: `pre-commit run --all-files`

## Optional Docker Integration Test
```bash
RUN_DOCKER_TESTS=1 pytest -q tests/test_docker_compose.py
```

## Test Areas
- Input model validation: `tests/test_models_validation.py`, `tests/test_models.py`
- Allocation behavior: `tests/test_allocator_*.py`, `tests/test_slot_category_priority.py`, `tests/test_peer_sort.py`, `tests/test_allocation_direction.py`
- Export behavior: `tests/test_export.py`
- DB behavior: `tests/test_db.py`
- End-to-end smoke: `tests/test_acceptance_smoke.py`, `tests/test_allocator_acceptance.py`
- Onboarding samples: `tests/test_onboarding_samples.py`

## CI Summary
GitHub Actions (`.github/workflows/ci.yml`) runs:
- `ruff`, `black --check`, `mypy`
- `pytest -q`
- conditional Docker integration on `main` push when Docker-related files changed
