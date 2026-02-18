<!-- SPDX-License-Identifier: Apache-2.0 -->
<!--
This file was created or modified with the assistance of an AI (Large Language Model). Review for correctness and security.
-->

# API Documentation

This document provides a concise overview of any programmatic interfaces the project exposes (HTTP endpoints, Python package public API, CLI commands, etc). Fill in details relevant to the repository.

## HTTP / Web UI (if applicable)
- POST /upload
  - Description: Upload a project YAML for trial allocation.
  - Request: multipart/form-data with `project.yaml`.
  - Response: JSON with trial results or validation errors.

- GET /project/{id}/result
  - Description: Fetch results for a saved project.
  - Response: JSON with allocation and metadata.

(Replace or extend the above with actual endpoints implemented by the repo.)

## Python package public API (if applicable)
- patchwork.core.run_trial(project_yaml: str) -> dict
  - Description: Run deterministic allocation and return results.
  - Inputs: project YAML or parsed structure.
  - Outputs: result object (document shape here).

- patchwork.export.to_svg(result: dict, path: str) -> None
  - Description: Render topology as SVG.

(Add real module/function names and signatures from codebase.)

## CLI
- `python app.py` (starts web UI)
- `scripts/export_results.py --project-id <id>`

## Examples
See `examples/quick-start` for a minimal end-to-end example.
