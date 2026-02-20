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

Patchwork is a Data Center Rack-to-Rack Patch Cabling Design Assistant. It provides a
Flask-based web interface to upload cabling plans, run deterministic allocations, and
export results.

## English

### Overview
Patchwork helps data center operators design patch cabling layouts. You upload a
`project.yaml` definition, review the generated layout, and export outputs such as
`sessions.csv` and `result.json`.

### Main features
- Flask Web UI with SQLite persistence.
- Deterministic trial allocation for cabling plans.
- SVG visualizations (topology, rack occupancy, pair details).
- Revision diff tracking for logical and physical changes.

### Requirements
- Python 3.10 or later.
- A Python virtual environment tool (for example, `venv`).
- Optional: a modern browser for the Web UI.

### Installation
1. Clone the repository and enter it:
   ```bash
   git clone https://github.com/icecake0141/patchwork.git
   cd patchwork
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
3. Install runtime dependencies:
   ```bash
   pip install -r requirements.txt
   ```

For development work, install dev tooling instead:
```bash
pip install -e ".[dev]"
```

### Basic usage (Web UI)
1. Start the Flask app:
   ```bash
   python app.py
   ```
2. Open http://localhost:5000/upload.
3. Upload a `project.yaml` file (see `examples/quick-start/sample-project.yaml`).
4. Download exported results (`result.json`, `sessions.csv`) from the UI.

### HTML/UI notes
The Web UI uses HTML templates under `templates/` and static assets under `static/`. You
can customize those files if you need to adjust the UI styling or layout.

### Documentation
- `docs/` contains API and quick-start references.
- `examples/quick-start/README.md` provides a step-by-step sample workflow.

### Contributing
Thank you for considering a contribution!
1. Create a feature branch and keep changes focused.
2. Run checks before opening a PR:
   ```bash
   ruff check .
   black --check .
   mypy .
   pytest -q
   pre-commit run --all-files
   ```
3. Submit a pull request with a clear summary and rationale.

### License
Licensed under the Apache License 2.0. See `LICENSE` for details.

### Contact
Please use GitHub Issues to ask questions or report bugs.

## 日本語 (Japanese)

### 概要
Patchwork はデータセンターのラック間パッチ配線を設計するための補助ツールです。
`project.yaml` をアップロードすると、配線割り当てを計算し、結果を
`sessions.csv` や `result.json` として出力できます。

### 主な機能
- Flask 製の Web UI と SQLite の保存機能。
- 配線計画の決定的な割り当てアルゴリズム。
- SVG 可視化（トポロジー、ラック占有、ペア詳細）。
- 論理／物理の差分（リビジョン）管理。

### 動作環境
- Python 3.10 以上。
- 仮想環境ツール（例: `venv`）。
- Web UI を利用するためのブラウザ。

### インストール
1. リポジトリを取得して移動します。
   ```bash
   git clone https://github.com/icecake0141/patchwork.git
   cd patchwork
   ```
2. 仮想環境を作成して有効化します。
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
3. 依存関係をインストールします。
   ```bash
   pip install -r requirements.txt
   ```

開発用途では次を実行してください。
```bash
pip install -e ".[dev]"
```

### 基本的な使い方（Web UI）
1. アプリを起動します。
   ```bash
   python app.py
   ```
2. http://localhost:5000/upload を開きます。
3. `project.yaml` をアップロードします
   （`examples/quick-start/sample-project.yaml` を参照）。
4. 結果（`result.json`, `sessions.csv`）を UI からダウンロードします。

### HTML/UI について
Web UI は `templates/` の HTML テンプレートと `static/` のアセットを利用します。
UI の見た目や構成を変更したい場合はこれらのファイルを編集してください。

### ドキュメント
- `docs/` に API とクイックスタートの資料があります。
- `examples/quick-start/README.md` にサンプル手順があります。

### コントリビュート
貢献ありがとうございます。
1. ブランチを作成し、変更範囲を明確にします。
2. PR 前に次のコマンドを実行してください。
   ```bash
   ruff check .
   black --check .
   mypy .
   pytest -q
   pre-commit run --all-files
   ```
3. 変更内容と目的を明確にした PR を作成してください。

### ライセンス
Apache License 2.0 です。詳細は `LICENSE` を参照してください。

### 連絡先
質問や不具合報告は GitHub Issues をご利用ください。
