<<<<<<< HEAD
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
=======
<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- This file was created or modified with the assistance of an AI (Large Language Model). -->
# Patchwork Flask Skeleton (spec 15.1 起点)

Upload → Trial → Save → Project Detail の最小導線を持つ Flask アプリです。

## セットアップ

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 起動

```bash
flask --app app run --debug
```

ブラウザ: `http://127.0.0.1:5000/upload`

## 入力YAML例

```yaml
project_name: demo-project
workers:
  - alice
  - bob
tasks:
  - task-1
  - task-2
  - task-3
```

## 出力例

Trial実行後:
- `trials` テーブルに trial データ保存
- `session['trial_id']` に trial ID を保存

Save実行後:
- `projects` / `allocations` テーブルに保存
- `exports/project_<id>.csv`
- `exports/project_<id>.json`

CSV例:

```csv
worker,task,score
alice,task-1,1.0
bob,task-2,0.9
alice,task-3,1.0
```

JSON例:

```json
{
  "project_name": "demo-project",
  "summary": {"workers": 2, "tasks": 3, "allocations": 3},
  "allocations": [
    {"worker": "alice", "task": "task-1", "score": 1.0}
  ]
}
>>>>>>> origin/main
```
