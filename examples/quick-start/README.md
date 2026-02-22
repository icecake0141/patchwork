<!-- SPDX-License-Identifier: Apache-2.0 -->
<!--
This file was created or modified with the assistance of an AI (Large Language Model). Review for correctness and security.
-->

# Quick Start (Example)

This quick-start demonstrates a minimal workflow to run Patchwork locally and process a sample project.

## Prerequisites
- Python 3.10+
- virtualenv

## Steps

### 1. Create and activate a virtual environment
```bash
python -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Start the app (Flask WebUI)
```bash
python app.py
```
Open http://localhost:5000/upload

### 4. Upload the sample project file

Upload `examples/quick-start/sample-project.yaml` via the Web UI at http://localhost:5000/upload.

### 5. Export / view results

After allocation, use the UI to download:
- `sessions.csv` — per-port patch wiring schedule
- `bom.csv` — Bill of Materials (panels, modules, cables)
- `result.json` — full structured allocation result

---

## Input Format — `project.yaml`

A `project.yaml` file describes racks, demands, and optional settings.

### Top-level fields

| Field      | Type    | Required | Description |
|------------|---------|----------|-------------|
| `version`  | integer | Yes      | Schema version. Must be `1`. |
| `project`  | object  | Yes      | Project metadata (`name`, optional `note`). |
| `racks`    | list    | Yes      | Rack definitions (see below). |
| `demands`  | list    | Yes      | Cabling demands (see below). |
| `settings` | object  | No       | Allocation settings (defaults shown below). |

### `racks` items

| Field    | Type    | Required | Description |
|----------|---------|----------|-------------|
| `id`     | string  | Yes      | Unique rack identifier (e.g. `R01`). |
| `name`   | string  | Yes      | Human-readable rack name. |
| `max_u`  | integer | No       | Rack height in U. Default: `42`. |

### `demands` items

| Field           | Type    | Required | Description |
|-----------------|---------|----------|-------------|
| `id`            | string  | Yes      | Unique demand identifier (e.g. `D001`). |
| `src`           | string  | Yes      | Source rack `id`. |
| `dst`           | string  | Yes      | Destination rack `id`. |
| `endpoint_type` | string  | Yes      | Connection type. One of: `mmf_lc_duplex`, `smf_lc_duplex`, `mpo12`, `utp_rj45`. |
| `count`         | integer | Yes      | Number of connections required (> 0). |

### `settings` (optional, all fields have defaults)

```yaml
settings:
  fixed_profiles:
    lc_demands:
      trunk_polarity: A          # "A" or "B"
      breakout_module_variant: AF
    mpo_e2e:
      trunk_polarity: B
      pass_through_variant: A
  ordering:
    slot_category_priority: [mpo_e2e, lc_mmf, lc_smf, utp]
    peer_sort: natural_trailing_digits
  panel:
    slots_per_u: 4               # Slots per 1U patch panel
    allocation_direction: top_down
    u_label_mode: ascending      # U label style in Rack Panel Occupancy UI
```

#### `settings` field details

| Path | Meaning | Allowed / expected values | Current implementation status |
|------|---------|---------------------------|-------------------------------|
| `fixed_profiles.lc_demands.trunk_polarity` | Trunk polarity used for LC demand trunks (`mmf_lc_duplex` / `smf_lc_duplex`). Reflected in cable `polarity_type`. | Common values: `A` / `B` (string) | **Active** |
| `fixed_profiles.lc_demands.breakout_module_variant` | Variant label recorded on LC breakout modules (`polarity_variant`). | String (example: `AF`, `BF`) | **Active** |
| `fixed_profiles.mpo_e2e.trunk_polarity` | Trunk polarity used for `mpo12` end-to-end trunks. Reflected in cable `polarity_type`. | Common values: `A` / `B` (string) | **Active** |
| `fixed_profiles.mpo_e2e.pass_through_variant` | Variant label recorded on MPO pass-through modules (`polarity_variant`). | String (example: `A`, `B`) | **Active** |
| `ordering.slot_category_priority` | Priority order for slot allocation by category (`mpo_e2e`, `lc_mmf`, `lc_smf`, `utp`). Categories are allocated in the listed order; categories absent from the list are silently skipped; unknown categories are rejected by validation. | List of strings (subset of `mpo_e2e`, `lc_mmf`, `lc_smf`, `utp`) | **Active** |
| `ordering.peer_sort` | Peer rack sorting strategy used for pair processing. | `natural_trailing_digits` (default) or `lexicographic` | **Active** |
| `panel.slots_per_u` | Number of module slots in each 1U panel; affects panel/slot progression and panel count. | Positive integer (default `4`) | **Active** |
| `panel.allocation_direction` | Panel fill direction. `top_down` fills from U1 upward (default); `bottom_up` fills from the rack's highest U downward. | `top_down` or `bottom_up` (default: `top_down`) | **Active** |
| `panel.u_label_mode` | U label style in Rack Panel Occupancy UI. `ascending` shows `U1`, `U2`, ... from top to bottom; `descending` shows `Umax`, `Umax-1`, ... from top to bottom. | `ascending` or `descending` (default: `ascending`) | **Active** |

Notes:
- Unknown extra keys under `settings` are rejected by schema validation (`extra="forbid"`).

### Sample `project.yaml`

```yaml
version: 1
project:
  name: example-dc-cabling
  note: optional free-text note
racks:
  - id: R01
    name: Rack-01
    max_u: 42
  - id: R02
    name: Rack-02
    max_u: 42
  - id: R03
    name: Rack-03
    max_u: 42
demands:
  - id: D001
    src: R01
    dst: R02
    endpoint_type: mmf_lc_duplex
    count: 13
  - id: D002
    src: R01
    dst: R02
    endpoint_type: mpo12
    count: 14
  - id: D003
    src: R01
    dst: R03
    endpoint_type: utp_rj45
    count: 8
```

See `sample-project.yaml` in this directory for the full version including `settings`.

---

## Output Files

### `sessions.csv`

One row per port-to-port patch connection. Columns:

| Column        | Description |
|---------------|-------------|
| `project_id`  | Saved project identifier. |
| `revision_id` | Saved revision identifier. |
| `session_id`  | Deterministic unique ID for this port assignment. |
| `media`       | Connection type (`mmf_lc_duplex`, `smf_lc_duplex`, `mpo12`, `utp_rj45`). |
| `cable_id`    | Cable identifier (shared across ports on the same cable). |
| `cable_seq`   | Sequential cable number for ordering. |
| `adapter_type`| Panel module type used at both ends. |
| `label_a`     | Source label (format: `{rack}U{u}S{slot}P{port}`). |
| `label_b`     | Destination label. |
| `src_rack`    | Source rack ID. |
| `src_face`    | Panel face (`front`). |
| `src_u`       | Panel U position (1-indexed from top). |
| `src_slot`    | Slot within the U (1-indexed). |
| `src_port`    | Port within the slot (1-indexed). |
| `dst_rack`    | Destination rack ID. |
| `dst_face`    | Panel face (`front`). |
| `dst_u`       | Panel U position. |
| `dst_slot`    | Slot within the U. |
| `dst_port`    | Port within the slot. |
| `fiber_a`     | Fiber strand number at source (LC only). |
| `fiber_b`     | Fiber strand number at destination (LC only). |
| `notes`       | Free-text notes (empty by default). |

Sample `sessions.csv` excerpt:
```
project_id,revision_id,session_id,media,cable_id,cable_seq,adapter_type,label_a,label_b,src_rack,src_face,src_u,src_slot,src_port,dst_rack,dst_face,dst_u,dst_slot,dst_port,fiber_a,fiber_b,notes
proj-001,rev-001,ses_068520420be33f56,utp_rj45,cab_94e2c52c9cbef746,17,utp_6xrj45,R01U2S1P4,R03U1S1P4,R01,front,2,1,4,R03,front,1,1,4,,,
proj-001,rev-001,ses_19814ea7921f293f,mpo12,cab_8c311bef72761e4c,16,mpo12_pass_through_12port,R01U1S1P10,R02U1S1P10,R01,front,1,1,10,R02,front,1,1,10,,,
```

---

### `bom.csv`

Bill of Materials summarising required physical hardware. Columns:

| Column        | Description |
|---------------|-------------|
| `item_type`   | Category: `panel`, `module`, or `cable`. |
| `description` | Item description including type variant. |
| `quantity`    | Total quantity required. |

Sample `bom.csv` for the above project:
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

---

### `result.json`

Structured JSON with full allocation details. Top-level keys:

| Key            | Description |
|----------------|-------------|
| `project`      | Echo of the validated input project definition. |
| `input_hash`   | SHA-256 of the canonical input (for change detection). |
| `panels`       | List of 1U panels allocated across racks. |
| `modules`      | List of port modules inserted into panels. |
| `cables`       | List of physical trunk cables with type and polarity. |
| `sessions`     | List of port-to-port patch assignments (same data as `sessions.csv`). |
| `warnings`     | Non-fatal allocation warnings. |
| `errors`       | Fatal errors (e.g. rack overflow). |
| `metrics`      | Summary counts: `rack_count`, `panel_count`, `module_count`, `cable_count`, `session_count`. |
| `pair_details` | Per rack-pair slot usage details. |

Sample `result.json` metrics section:
```json
{
  "rack_count": 3,
  "panel_count": 4,
  "module_count": 12,
  "cable_count": 26,
  "session_count": 35
}
```

---

## 日本語（後半の和訳）

## 入力形式 — `project.yaml`

`project.yaml` は、ラック定義・需要（demands）・任意の設定（settings）を記述します。

### トップレベル項目

| 項目        | 型      | 必須 | 説明 |
|-------------|---------|------|------|
| `version`   | integer | Yes  | スキーマバージョン。`1` 固定。 |
| `project`   | object  | Yes  | プロジェクト情報（`name`、任意で `note`）。 |
| `racks`     | list    | Yes  | ラック定義（下記参照）。 |
| `demands`   | list    | Yes  | 配線需要（下記参照）。 |
| `settings`  | object  | No   | 割り当て設定（未指定時はデフォルト）。 |

### `racks` の各要素

| 項目     | 型      | 必須 | 説明 |
|----------|---------|------|------|
| `id`     | string  | Yes  | 一意なラックID（例: `R01`）。 |
| `name`   | string  | Yes  | 表示名。 |
| `max_u`  | integer | No   | ラック高さ（U）。デフォルト `42`。 |

### `demands` の各要素

| 項目            | 型      | 必須 | 説明 |
|-----------------|---------|------|------|
| `id`            | string  | Yes  | 一意な需要ID（例: `D001`）。 |
| `src`           | string  | Yes  | 送信元ラックの `id`。 |
| `dst`           | string  | Yes  | 送信先ラックの `id`。 |
| `endpoint_type` | string  | Yes  | 接続種別。`mmf_lc_duplex` / `smf_lc_duplex` / `mpo12` / `utp_rj45`。 |
| `count`         | integer | Yes  | 必要接続数（`> 0`）。 |

### `settings`（任意。全項目デフォルトあり）

```yaml
settings:
  fixed_profiles:
    lc_demands:
      trunk_polarity: A          # "A" or "B"
      breakout_module_variant: AF
    mpo_e2e:
      trunk_polarity: B
      pass_through_variant: A
  ordering:
    slot_category_priority: [mpo_e2e, lc_mmf, lc_smf, utp]
    peer_sort: natural_trailing_digits
  panel:
    slots_per_u: 4               # 1Uパッチパネルあたりのスロット数
    allocation_direction: top_down
    u_label_mode: ascending      # Rack Panel Occupancy の U 表示方式
```

#### `settings` 各項目の説明

| パス | 意味 | 設定可能な値（想定） | 現在の実装での反映状況 |
|------|------|----------------------|------------------------|
| `fixed_profiles.lc_demands.trunk_polarity` | LC需要（`mmf_lc_duplex` / `smf_lc_duplex`）で使うトランク極性。ケーブルの `polarity_type` に反映。 | 一般的には `A` / `B`（文字列） | **有効** |
| `fixed_profiles.lc_demands.breakout_module_variant` | LCブレイクアウトモジュールに記録するバリアント名（`polarity_variant`）。 | 文字列（例: `AF`, `BF`） | **有効** |
| `fixed_profiles.mpo_e2e.trunk_polarity` | `mpo12` エンドツーエンド需要で使うトランク極性。ケーブルの `polarity_type` に反映。 | 一般的には `A` / `B`（文字列） | **有効** |
| `fixed_profiles.mpo_e2e.pass_through_variant` | MPOパススルーモジュールに記録するバリアント名（`polarity_variant`）。 | 文字列（例: `A`, `B`） | **有効** |
| `ordering.slot_category_priority` | カテゴリ別（`mpo_e2e`, `lc_mmf`, `lc_smf`, `utp`）のスロット割り当て優先順。リストの順に割り当てる。リストに含まれないカテゴリはスキップ。不明なカテゴリはバリデーションエラー。 | 文字列リスト（`mpo_e2e`, `lc_mmf`, `lc_smf`, `utp` の部分集合） | **有効** |
| `ordering.peer_sort` | ピアラックの並び順戦略。ペア処理順に反映。 | `natural_trailing_digits`（既定）または `lexicographic` | **有効** |
| `panel.slots_per_u` | 1Uパネル内のスロット数。スロット進行・必要パネル数に影響。 | 正の整数（既定 `4`） | **有効** |
| `panel.allocation_direction` | パネルを埋める方向。`top_down` はU1から上方向（既定値）、`bottom_up` はラックの最上位Uから下方向に割り当て。 | `top_down` または `bottom_up`（既定値: `top_down`） | **有効** |
| `panel.u_label_mode` | Rack Panel Occupancy の U 表示方式。`ascending` は上から `U1`, `U2`, ...、`descending` は上から `Umax`, `Umax-1`, ... を表示。 | `ascending` または `descending`（既定値: `ascending`） | **有効** |

補足:
- `settings` 配下で未定義の追加キーはスキーマ検証でエラーになります（`extra="forbid"`）。

### `project.yaml` サンプル

（上記の英語セクションと同じ内容）

このディレクトリの `sample-project.yaml` には、`settings` を含む完全版があります。

---

## 出力ファイル

### `sessions.csv`

ポート間パッチ接続を1行ずつ表したCSVです。主な列:

- `project_id`: 保存済みプロジェクトID
- `revision_id`: 保存済みリビジョンID
- `session_id`: 各ポート割り当ての決定的ユニークID
- `media`: 接続種別（`mmf_lc_duplex` / `smf_lc_duplex` / `mpo12` / `utp_rj45`）
- `cable_id`: ケーブルID（同一ケーブル上の複数ポートで共有）
- `cable_seq`: 並び順用の連番
- `adapter_type`: 両端で使用したモジュール種別
- `label_a`, `label_b`: 送信元/送信先ラベル（`{rack}U{u}S{slot}P{port}`）
- `src_*`, `dst_*`: 送信元/送信先のラック・面・U・スロット・ポート
- `fiber_a`, `fiber_b`: LC接続時のファイバ芯線番号
- `notes`: 備考（既定は空）

---

### `bom.csv`

必要部材（パネル・モジュール・ケーブル）を集計した部材表（BOM）です。列:

- `item_type`: `panel` / `module` / `cable`
- `description`: 部材の説明（型番バリエーション含む）
- `quantity`: 必要数量

---

### `result.json`

割り当て結果の完全な構造化JSONです。主なトップレベルキー:

- `project`: 検証済み入力のエコー
- `input_hash`: 正規化入力の SHA-256（差分検知用）
- `panels`: 各ラックに割り当てられた1Uパネル一覧
- `modules`: パネルに挿入されたモジュール一覧
- `cables`: 物理トランクケーブル一覧（種別・極性を含む）
- `sessions`: ポート間パッチ割り当て一覧（`sessions.csv` と同等）
- `warnings`: 非致命的な警告
- `errors`: 致命的エラー（例: ラックあふれ）
- `metrics`: 集計値（`rack_count`, `panel_count`, `module_count`, `cable_count`, `session_count`）
- `pair_details`: ラックペアごとのスロット利用詳細
