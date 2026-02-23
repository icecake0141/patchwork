<!-- SPDX-License-Identifier: Apache-2.0 -->
<!--
This file was created or modified with the assistance of an AI (Large Language Model). Review for correctness and security.
-->

# API Documentation

This document describes the interfaces and allocation behavior implemented in this repository.

## HTTP / Web UI Endpoints

- `GET /`
  - Redirects to `/upload`.

- `GET /upload`
  - Upload page for `project.yaml` and list of saved projects.

- `POST /upload`
  - Accepts multipart form field `project_yaml`.
  - Parses YAML, validates with `ProjectInput`, runs deterministic allocation, stores trial result, redirects to `/trial`.

- `GET /trial`
  - Shows current trial result from session (topology summary, rack occupancy SVGs, wiring SVG, integrated wiring view).

- `POST /save`
  - Saves current trial as a project revision.
  - Form fields: `project_name` (required by UI flow, default fallback exists), `note` (optional).

- `GET /projects/<project_id>?revision_id=<optional>`
  - Displays saved revision details and visualizations.

- `GET /revisions/<revision_id>/export/sessions.csv`
  - Exports per-session wiring CSV.

- `GET /revisions/<revision_id>/export/bom.csv`
  - Exports BOM CSV.

- `GET /revisions/<revision_id>/export/result.json`
  - Exports allocation result JSON.

- `GET /revisions/<revision_id>/export/wiring.svg`
  - Exports wiring SVG.

- `GET /revisions/<revision_id>/export/wiring.drawio`
  - Exports editable Draw.io XML converted from wiring SVG.
  - Edge style includes line-jump readability settings (`jumpStyle=arc`, `jumpSize=6`).

- `GET /revisions/<revision_id>/export/integrated_wiring.drawio`
  - Exports editable Draw.io XML containing Integrated Wiring View (Aggregate/Detailed pages).
  - Edge style includes line-jump readability settings (`jumpStyle=arc`, `jumpSize=6`).

- `GET /revisions/<revision_id>/export/integrated_wiring_interactive.svg?mode=aggregate|detailed`
  - Exports standalone Integrated Wiring SVG with embedded controls:
    media/rack checkbox filters, click-to-focus highlight, zoom/pan, and Gap Jump Scale selector.

- `GET /revisions/<revision_id>/export/rack_occupancy.drawio`
  - Exports Draw.io XML containing a single combined Rack Occupancy sheet.

- `GET /diff/<project_id>?rev1=<id>&rev2=<id>`
  - Compares two revisions (logical + physical views).

- `GET /pair-svg/<revision_id>/<rack_a>/<rack_b>`
  - Returns pair detail SVG for one rack pair.

## Runtime / Request Constraints

- Maximum upload payload is 1 MiB (`MAX_CONTENT_LENGTH = 1024 * 1024`).
- Session secret key is read from `SECRET_KEY`; default fallback is `dev-secret`.

## Input Validation Rules (ProjectInput)

- Unknown keys are rejected (`extra="forbid"`) for all nested models.
- `racks[].id` must be unique.
- `demands[].id` must be unique.
- `demands[].src` and `demands[].dst` must be different.
- Every demand must reference existing rack IDs.
- `count` must be greater than 0.
- Unsupported endpoint types / ordering categories / sort strategies / allocation directions are rejected.

## Revision Persistence Rules

- `project_id` is deterministic from project name: `prj_<sha256(name)[:16]>`.
- `revision_id` includes timestamp + input YAML hash seed: `rev_<sha256(name+time+yaml)[:16]>`.
- At DB persistence, IDs for panel/module/cable/session are namespaced with revision prefix (`<revision_id>:<id>`).
- In saved sessions, `cable_id` is rewritten to the persisted cable DB ID for referential consistency.

## Diff Semantics

- Logical diff compares by `session_id`:
  - `added`: IDs only in newer revision
  - `removed`: IDs only in older revision
  - `modified`: same `session_id` but row payload changed
- Physical diff compares by physical tuple key:
  - `(media, src_rack, src_face, src_u, src_slot, src_port, dst_rack, dst_face, dst_u, dst_slot, dst_port)`
  - `added`/`removed` by tuple existence
  - `collisions` when same physical tuple exists in both revisions but maps to different `session_id`

## Python Allocation API

- `services.allocator.allocate(project: ProjectInput) -> dict[str, Any]`
  - Core deterministic wiring allocator.
  - Input: validated `ProjectInput` model.
  - Output keys:
    - `project`, `input_hash`
    - `panels`, `modules`, `cables`, `sessions`
    - `warnings`, `errors`
    - `metrics`
    - `pair_details`

## Wiring Decision Logic (Demand -> Panel Placement)

### 1) Normalize demands by unordered rack pair
- Each demand is folded into a canonical pair key using natural rack ordering.
- Counts are aggregated by endpoint type per pair:
  - `mmf_lc_duplex`
  - `smf_lc_duplex`
  - `mpo12`
  - `utp_rj45`

### 2) Decide processing order
- Pair iteration order is controlled by `settings.ordering.peer_sort`:
  - `natural_trailing_digits` (default)
  - `lexicographic`
- Category execution order is controlled by `settings.ordering.slot_category_priority`.
  - Default: `[mpo_e2e, lc_mmf, lc_smf, utp]`

### 3) Reserve physical panel slots per rack
- Each rack has an independent `RackSlotAllocator`.
- One allocation index maps to `(u, slot)` with `slots_per_u`.
- `allocation_direction` behavior:
  - `top_down`: U increases from `U1` upward.
  - `bottom_up`: U decreases from `max_u` downward.
- If allocation exceeds rack capacity, a `RackOverflowError` is recorded in `errors`.

### 4) Category-specific module placement and session mapping

#### MPO end-to-end (`mpo_e2e` -> `mpo12` demands)
- Required slots per rack pair: `ceil(count / 12)`.
- For each slot chunk:
  - Reserve one slot on each rack.
  - Place `mpo12_pass_through_12port` module on both sides (`dedicated=1`).
  - Create up to 12 one-to-one sessions (`src_port == dst_port`).
  - Create one cable per used port with MPO polarity profile.

#### LC breakout (`lc_mmf` / `lc_smf`)
- Required slots per rack pair: `ceil(count / 12)`.
- For each slot chunk:
  - Reserve one slot on each rack.
  - Place `lc_breakout_2xmpo12_to_12xlcduplex` module on both sides (`dedicated=1`).
  - Create two MPO trunk cables per chunk (MPO port 1 and 2).
  - Map LC ports `1..6` to MPO-1 and `7..12` to MPO-2.
  - Fiber-pair mapping per MPO local port:
    - 1->(1,2), 2->(3,4), 3->(5,6), 4->(7,8), 5->(9,10), 6->(11,12)

#### UTP (`utp` -> `utp_rj45` demands)
- UTP is allocated by rack-peer counts at the point where `utp` appears in priority.
- On each rack:
  - Peers are processed in configured peer sort order.
  - A `utp_6xrj45` module is created when a new slot is needed.
  - Ports are filled sequentially (`1..6`) and leftover capacity is reused for subsequent peers in the same rack.
- After both rack sides are prepared, sessions are paired by index between both peer-side port lists.

### 5) Build panels/cables/sessions with deterministic IDs
- IDs (`panel_id`, `module_id`, `cable_id`, `session_id`) are generated from SHA-256 of canonical strings.
- This makes repeated runs deterministic for identical normalized inputs.
- Cables are sorted by `cable_id`, then assigned sequential `cable_seq`.

### 6) Output ordering and diagnostics
- `panels` sorted by rack natural order and U.
- `modules` sorted by rack/U/slot.
- `sessions` sorted by `session_id`.
- `warnings` includes non-fatal mismatches (for example UTP side count mismatch).
- `errors` includes rack overflow and other fatal allocation issues.

## Integrated Wiring Interaction Notes

- Aggregate mode groups sessions by
  `(src_rack, src_u, src_slot, dst_rack, dst_u, dst_slot, media)` and draws one conceptual route per group.
- Detailed mode renders per-session routes and labels.
- Click-to-focus is toggle-based:
  - Click wire/label once -> focus selection and dim non-related routes.
  - Click the same target again or click empty canvas -> clear focus state.
- Gap Jump Scale selector supports `Auto`, `Auto × 0.50`, `Auto × 0.75`, `Auto × 1.25`, `Auto × 1.50`, `Auto × 2.00`.

## CLI
- `python app.py` (starts web UI)

## Examples
See `examples/quick-start` for end-to-end examples.

## 日本語訳

このドキュメントは、このリポジトリで実装されているインターフェースと配線割り当て挙動を説明します。

### HTTP / Web UI エンドポイント

- `GET /`
  - `/upload` にリダイレクトします。

- `GET /upload`
  - `project.yaml` のアップロード画面と保存済みプロジェクト一覧を表示します。

- `POST /upload`
  - multipart フィールド `project_yaml` を受け取ります。
  - YAML 解析、`ProjectInput` で検証、決定的割り当てを実行し、試行結果を保存して `/trial` へ遷移します。

- `GET /trial`
  - セッション中の試行結果（トポロジー要約、ラック占有 SVG、配線 SVG、統合配線ビュー）を表示します。

- `POST /save`
  - 現在の試行をプロジェクトのリビジョンとして保存します。
  - フォーム項目: `project_name`（UI フロー上は必須、フォールバックあり）、`note`（任意）。

- `GET /projects/<project_id>?revision_id=<optional>`
  - 保存済みリビジョン詳細と可視化を表示します。

- `GET /revisions/<revision_id>/export/sessions.csv`
  - セッション単位の配線 CSV を出力します。

- `GET /revisions/<revision_id>/export/bom.csv`
  - BOM CSV を出力します。

- `GET /revisions/<revision_id>/export/result.json`
  - 割り当て結果 JSON を出力します。

- `GET /revisions/<revision_id>/export/wiring.svg`
  - 配線 SVG を出力します。

- `GET /revisions/<revision_id>/export/wiring.drawio`
  - 配線 SVG から変換した Draw.io XML を出力します。

- `GET /revisions/<revision_id>/export/integrated_wiring.drawio`
  - Integrated Wiring View（Aggregate/Detailed 2 ページ）を含む Draw.io XML を出力します。

- `GET /revisions/<revision_id>/export/integrated_wiring_interactive.svg?mode=aggregate|detailed`
  - media/rack のチェックボックスフィルタを埋め込んだ Integrated Wiring SVG を出力します。

- `GET /revisions/<revision_id>/export/rack_occupancy.drawio`
  - Rack Occupancy（全ラックを 1 シートでまとめた）Draw.io XML を出力します。

- `GET /diff/<project_id>?rev1=<id>&rev2=<id>`
  - 2 つのリビジョンを比較します（論理 + 物理ビュー）。

- `GET /pair-svg/<revision_id>/<rack_a>/<rack_b>`
  - 指定ラックペアの詳細 SVG を返します。

### 実行時 / リクエスト制約

- アップロード上限は 1 MiB（`MAX_CONTENT_LENGTH = 1024 * 1024`）です。
- セッション秘密鍵は `SECRET_KEY` から読み取り、未設定時は `dev-secret` を使用します。

### 入力バリデーション規則（ProjectInput）

- すべてのネストモデルで未定義キーを拒否します（`extra="forbid"`）。
- `racks[].id` は一意である必要があります。
- `demands[].id` は一意である必要があります。
- `demands[].src` と `demands[].dst` は同一不可です。
- 各 demand は既存ラック ID を参照している必要があります。
- `count` は 0 より大きい必要があります。
- 未対応の endpoint_type / ordering category / sort strategy / allocation_direction は拒否されます。

### リビジョン永続化ルール

- `project_id` は project 名から決定的に生成します: `prj_<sha256(name)[:16]>`。
- `revision_id` は時刻 + 入力 YAML を種に生成します: `rev_<sha256(name+time+yaml)[:16]>`。
- DB 保存時、panel/module/cable/session の ID は `<revision_id>:<id>` 形式で名前空間化されます。
- 保存済み session の `cable_id` は、参照整合性のため永続化後の cable DB ID に置き換えます。

### Diff 判定ルール

- Logical diff は `session_id` 基準で比較:
  - `added`: 新しいリビジョンのみに存在
  - `removed`: 古いリビジョンのみに存在
  - `modified`: `session_id` は同じだが内容が変更
- Physical diff は物理タプル基準で比較:
  - `(media, src_rack, src_face, src_u, src_slot, src_port, dst_rack, dst_face, dst_u, dst_slot, dst_port)`
  - `added` / `removed`: タプルの有無で判定
  - `collisions`: 同一タプルが両リビジョンに存在し、`session_id` が異なる場合

### Python 割り当て API

- `services.allocator.allocate(project: ProjectInput) -> dict[str, Any]`
  - 決定的配線割り当ての中核 API です。
  - 入力: 検証済み `ProjectInput`。
  - 出力キー:
    - `project`, `input_hash`
    - `panels`, `modules`, `cables`, `sessions`
    - `warnings`, `errors`
    - `metrics`
    - `pair_details`

### 配線決定ロジック（Demand -> パネル配置）

#### 1) ラックペア単位へ Demand を正規化
- 各 demand は、ラック ID を順序非依存のペアキーに畳み込みます。
- ペアごとに endpoint_type 別カウントを集計します:
  - `mmf_lc_duplex`
  - `smf_lc_duplex`
  - `mpo12`
  - `utp_rj45`

#### 2) 処理順を決定
- ラックペアの処理順は `settings.ordering.peer_sort` で制御します:
  - `natural_trailing_digits`（デフォルト）
  - `lexicographic`
- カテゴリの処理順は `settings.ordering.slot_category_priority` で制御します。
  - デフォルト: `[mpo_e2e, lc_mmf, lc_smf, utp]`

#### 3) ラックごとに物理スロットを予約
- 各ラックは独立した `RackSlotAllocator` を持ちます。
- 割り当てインデックスを `slots_per_u` で `(u, slot)` に変換します。
- `allocation_direction` の挙動:
  - `top_down`: `U1` から上方向へ増加。
  - `bottom_up`: `max_u` から下方向へ減少。
- ラック容量を超えた場合は `RackOverflowError` を `errors` に記録します。

#### 4) カテゴリ別のモジュール配置とセッション化

##### MPO 直結（`mpo_e2e` -> `mpo12`）
- 必要スロット数: `ceil(count / 12)`。
- 各スロット単位で:
  - 両ラックで 1 スロットずつ予約。
  - 両側に `mpo12_pass_through_12port` を配置（`dedicated=1`）。
  - 最大 12 本の 1:1 セッションを作成（`src_port == dst_port`）。
  - 使用ポートごとに MPO 極性プロファイルでケーブルを作成。

##### LC ブレイクアウト（`lc_mmf` / `lc_smf`）
- 必要スロット数: `ceil(count / 12)`。
- 各スロット単位で:
  - 両ラックで 1 スロットずつ予約。
  - 両側に `lc_breakout_2xmpo12_to_12xlcduplex` を配置（`dedicated=1`）。
  - 1 スロットあたり MPO トランク 2 本（MPO port 1/2）を作成。
  - LC port `1..6` は MPO-1、`7..12` は MPO-2 に割り当て。
  - MPO 内ローカルポートのファイバ対応:
    - 1->(1,2), 2->(3,4), 3->(5,6), 4->(7,8), 5->(9,10), 6->(11,12)

##### UTP（`utp` -> `utp_rj45`）
- UTP は、優先順位リスト中で `utp` が現れたタイミングでラック-ピア単位に割り当てます。
- 各ラックで:
  - ピアを設定済みソート順で処理。
  - 新規スロットが必要になった時点で `utp_6xrj45` を作成。
  - ポート `1..6` を順次使用し、余剰ポートは同一ラック内の次ピアで再利用。
- 両ラック側の準備後、ピアごとの両側ポート列をインデックス順で突き合わせてセッション化します。

#### 5) 決定的 ID で panel/cable/session を生成
- `panel_id`, `module_id`, `cable_id`, `session_id` は正規化文字列の SHA-256 から生成します。
- 同一の正規化入力に対して結果は決定的になります。
- `cables` は `cable_id` でソート後、連番 `cable_seq` を付与します。

#### 6) 出力順序と診断情報
- `panels`: ラック自然順 + U 順。
- `modules`: ラック/U/slot 順。
- `sessions`: `session_id` 順。
- `warnings`: 非致命（例: UTP 側数不一致）。
- `errors`: ラックオーバーフローなどの致命的問題。

### CLI
- `python app.py`（Web UI を起動）

### 例
エンドツーエンド例は `examples/quick-start` を参照してください。
