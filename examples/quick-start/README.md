<!-- SPDX-License-Identifier: Apache-2.0 -->
<!--
This file was created or modified with the assistance of an AI (Large Language Model). Review for correctness and security.
-->

# Quick Start (Example)

This quick-start demonstrates a minimal workflow to run Patchwork locally and process a sample project.

Prerequisites
- Python 3.10+ (or repo-specified version)
- virtualenv

Steps
1. Create and activate a virtual environment
```bash
python -m venv .venv
source .venv/bin/activate
```

2. Install dependencies
```bash
pip install -r requirements.txt
```

3. Start the app (Flask WebUI)
```bash
python app.py
```
Open http://localhost:5000/upload

4. Example project file
- Put a sample `project.yaml` into `examples/quick-start/sample-project.yaml` (create one from your domain spec).
- Upload it via the Web UI or call the API endpoint (see `docs/api.md`).

5. Export / view results
- After the run, use the UI to download `result.json` or `sessions.csv`.
- Or run an export script if provided.

Notes
- Replace the above commands with the exact scripts or entrypoints in the repository as appropriate.
