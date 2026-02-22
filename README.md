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

[![CI](https://github.com/icecake0141/patchwork/actions/workflows/ci.yml/badge.svg)](https://github.com/icecake0141/patchwork/actions/workflows/ci.yml)
[![Dependabot Updates](https://github.com/icecake0141/patchwork/actions/workflows/dependabot/dependabot-updates/badge.svg)](https://github.com/icecake0141/patchwork/actions/workflows/dependabot/dependabot-updates)

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
4. Download exported results (`result.json`, `sessions.csv`, `bom.csv`) from the UI.

### Input format — `project.yaml`

A `project.yaml` file has four sections: `project` (metadata), `racks`, `demands`, and
optional `settings`.

```yaml
version: 1
project:
  name: example-dc-cabling   # project name (required)
  note: optional note         # free-text note (optional)
racks:
  - id: R01          # unique rack ID
    name: Rack-01    # display name
    max_u: 42        # rack height in U (default 42)
  - id: R02
    name: Rack-02
    max_u: 42
demands:
  - id: D001
    src: R01                    # source rack ID
    dst: R02                    # destination rack ID
    endpoint_type: mmf_lc_duplex  # connection type (see below)
    count: 13                   # number of connections required
  - id: D002
    src: R01
    dst: R02
    endpoint_type: mpo12
    count: 14
```

Supported `endpoint_type` values:

| Value           | Description                          |
|-----------------|--------------------------------------|
| `mmf_lc_duplex` | Multimode fiber, LC duplex connectors |
| `smf_lc_duplex` | Singlemode fiber, LC duplex connectors |
| `mpo12`         | MPO-12 fiber end-to-end              |
| `utp_rj45`      | Copper UTP, RJ-45 connectors         |

See `examples/quick-start/sample-project.yaml` for a full example including `settings`.

The optional `settings.ordering.slot_category_priority` list controls the order in which
demand categories are allocated to rack slots. The default order is
`[mpo_e2e, lc_mmf, lc_smf, utp]`. Change it to allocate categories in a different order,
or omit categories entirely to skip them. Unknown categories are rejected at load time.

The optional `settings.panel.allocation_direction` field controls which end of the rack
panels are filled from. Allowed values:

| Value        | Description                                         |
|--------------|-----------------------------------------------------|
| `top_down`   | Panels allocated starting from U1 upward (default). |
| `bottom_up`  | Panels allocated starting from the highest U downward. |

The optional `settings.panel.u_label_mode` field controls how U numbers are shown in
the Rack Panel Occupancy UI labels:

| Value         | Description |
|---------------|-------------|
| `ascending`   | Display U labels as `U1`, `U2`, `U3`, ... from top to bottom (default). |
| `descending`  | Display U labels as `Umax`, `Umax-1`, ... from top to bottom (for example `U42`, `U41`, ... on a 42U rack). |

`u_label_mode` affects the UI label display only. Allocation behavior is controlled by
`allocation_direction`.

Example:
```yaml
settings:
  panel:
    slots_per_u: 4
    allocation_direction: bottom_up
    u_label_mode: descending
```

See `examples/quick-start/README.md` for the full field reference.

### Output files

After allocation Patchwork produces three downloadable files:

| File           | Description |
|----------------|-------------|
| `sessions.csv` | Per-port patch wiring schedule, one row per connection. |
| `bom.csv`      | Bill of Materials: panels, modules, and cables with quantities. |
| `result.json`  | Full structured allocation result (panels, modules, cables, sessions, metrics). |
| `wiring.svg`   | Visual cable wiring diagram (one line per cable, with source/destination panel positions). |

**`sessions.csv` excerpt:**
```
project_id,revision_id,session_id,media,cable_id,cable_seq,adapter_type,label_a,label_b,...
proj-001,rev-001,ses_068...,utp_rj45,cab_94e...,17,utp_6xrj45,R01U2S1P4,R03U1S1P4,...
proj-001,rev-001,ses_198...,mpo12,cab_8c3...,16,mpo12_pass_through_12port,R01U1S1P10,R02U1S1P10,...
```
Port labels use the format `{rack}U{u}S{slot}P{port}` (e.g. `R01U1S2P3` = rack R01,
panel at U1, slot 2, port 3).

**`bom.csv` excerpt:**
```
item_type,description,quantity
panel,1U patch panel (4 slots/U),4
module,lc_breakout_2xmpo12_to_12xlcduplex,4
module,mpo12_pass_through_12port,4
module,utp_6xrj45,4
cable,mpo12_trunk mmf polarity-A,4
cable,mpo12_trunk polarity-B,14
cable,utp_cable,8
```

**`result.json` metrics section:**
```json
{
  "rack_count": 3,
  "panel_count": 4,
  "module_count": 12,
  "cable_count": 26,
  "session_count": 35
}
```

See `examples/quick-start/README.md` for the complete field reference.

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
4. 結果（`result.json`, `sessions.csv`, `bom.csv`）を UI からダウンロードします。

### 入力形式 — `project.yaml`

`project.yaml` は `project`（メタ情報）、`racks`、`demands`、任意の `settings` の
4つのセクションで構成されます。

```yaml
version: 1
project:
  name: example-dc-cabling   # プロジェクト名（必須）
  note: 任意のメモ            # 自由記述（省略可）
racks:
  - id: R01          # ラック固有 ID
    name: Rack-01    # 表示名
    max_u: 42        # ラック高さ（U）。デフォルト 42
  - id: R02
    name: Rack-02
    max_u: 42
demands:
  - id: D001
    src: R01                    # 送信元ラック ID
    dst: R02                    # 送信先ラック ID
    endpoint_type: mmf_lc_duplex  # 接続種別（下表参照）
    count: 13                   # 必要な接続本数
  - id: D002
    src: R01
    dst: R02
    endpoint_type: mpo12
    count: 14
```

`endpoint_type` に指定できる値：

| 値              | 説明                              |
|-----------------|-----------------------------------|
| `mmf_lc_duplex` | マルチモード光ファイバー、LC デュプレックス |
| `smf_lc_duplex` | シングルモード光ファイバー、LC デュプレックス |
| `mpo12`         | MPO-12 光ファイバー エンドツーエンド |
| `utp_rj45`      | 銅線 UTP、RJ-45 コネクタ          |

`settings` を含む完全なサンプルは `examples/quick-start/sample-project.yaml` を参照してください。

任意の `settings.ordering.slot_category_priority` リストで、カテゴリのスロット割り当て順を制御できます。
デフォルトは `[mpo_e2e, lc_mmf, lc_smf, utp]` です。順序の変更やカテゴリの省略が可能で、
不明なカテゴリは読み込み時にエラーになります。詳細は `examples/quick-start/README.md` を参照してください。

任意の `settings.panel.u_label_mode` で、Rack Panel Occupancy の U 表示方法を切り替えできます。

| 値            | 説明 |
|---------------|------|
| `ascending`   | 上から `U1`, `U2`, `U3`, ... と表示（デフォルト）。 |
| `descending`  | 上から `Umax`, `Umax-1`, ... と表示（42U ラックなら `U42`, `U41`, ...）。 |

`u_label_mode` は UI 上の U 表示ラベルだけを切り替えます。割り当て動作自体は
`allocation_direction` で制御されます。

### 出力ファイル

割り当て完了後、3 つのファイルをダウンロードできます。

| ファイル        | 説明 |
|----------------|------|
| `sessions.csv` | ポートごとのパッチ配線スケジュール（1 行 = 1 接続）。 |
| `bom.csv`      | 部材表：パネル・モジュール・ケーブルの種別と数量。 |
| `result.json`  | 全割り当て結果の構造化 JSON（パネル、モジュール、ケーブル、セッション、メトリクス）。 |

**`sessions.csv` の例（抜粋）：**
```
project_id,revision_id,session_id,media,cable_id,cable_seq,adapter_type,label_a,label_b,...
proj-001,rev-001,ses_068...,utp_rj45,cab_94e...,17,utp_6xrj45,R01U2S1P4,R03U1S1P4,...
proj-001,rev-001,ses_198...,mpo12,cab_8c3...,16,mpo12_pass_through_12port,R01U1S1P10,R02U1S1P10,...
```
ポートラベルは `{ラック}U{U位置}S{スロット}P{ポート}` の形式です
（例：`R01U1S2P3` = ラック R01 の U1 パネル、スロット 2、ポート 3）。

**`bom.csv` の例：**
```
item_type,description,quantity
panel,1U patch panel (4 slots/U),4
module,lc_breakout_2xmpo12_to_12xlcduplex,4
module,mpo12_pass_through_12port,4
module,utp_6xrj45,4
cable,mpo12_trunk mmf polarity-A,4
cable,mpo12_trunk polarity-B,14
cable,utp_cable,8
```

**`result.json` のメトリクスセクション例：**
```json
{
  "rack_count": 3,
  "panel_count": 4,
  "module_count": 12,
  "cable_count": 26,
  "session_count": 35
}
```

各フィールドの詳細は `examples/quick-start/README.md` を参照してください。

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
