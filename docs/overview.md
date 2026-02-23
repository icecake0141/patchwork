<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- This file was created or modified with the assistance of an AI (Large Language Model). -->
# Overview

This implementation follows the design spec for rack-to-rack cabling allocation:

- Supported media: MMF/SMF LC duplex, MPO12, UTP RJ45.
- Slot category priority: MPO E2E → LC MMF → LC SMF → UTP.
- Mixed-in-U allocation is enabled by contiguous slot reservation.
- Deterministic IDs use SHA-256 canonical strings.
- Saved revisions persist generated `panel/module/cable/session` rows in SQLite.

## Settings: `ordering.peer_sort`

The `ordering.peer_sort` setting controls how rack-peer pairs are ordered during
allocation. The value is read from the project YAML under `settings.ordering.peer_sort`.

Supported values:

| Value | Behaviour |
|---|---|
| `natural_trailing_digits` (default) | Sorts rack IDs by the trailing numeric suffix first (numeric order), then by the full string. `R2` sorts before `R10`. |
| `lexicographic` | Sorts rack IDs as plain strings. `R10` sorts before `R2` because `"1" < "2"`. |

Any other value is rejected at validation time with a clear error message.

**Example** (project YAML):

```yaml
settings:
  ordering:
    peer_sort: lexicographic
```

## Settings: `panel.u_label_mode`

The `panel.u_label_mode` setting controls how U numbers are displayed in the Rack Panel
Occupancy UI. This affects display labels only; allocation behavior is controlled by
`settings.panel.allocation_direction`.

Supported values:

| Value | Behaviour |
|---|---|
| `ascending` (default) | Shows U labels as `U1`, `U2`, `U3`, ... from top to bottom. |
| `descending` | Shows U labels as `Umax`, `Umax-1`, ... from top to bottom (for example `U42`, `U41`, ... on a 42U rack). |

**Example** (project YAML):

```yaml
settings:
  panel:
    u_label_mode: descending
```

UI pages:
- Upload
- Trial
- Project detail
- Diff (logical + physical tabs)

## Integrated Wiring View

Trial / Project detail includes an additional **Integrated Wiring View** that overlays
inter-rack wiring on Rack Occupancy coordinates (`rack`, `u`, `slot`).

Purpose:
- Keep panel-slot location context while inspecting end-to-end cabling.
- Provide a quick switch between cable-level aggregation and session-level detail.

Constraints and behavior:
- Existing `wiring.svg` export remains unchanged; integrated view is additive UI output.
- Rendering groups sessions by `(src_rack, src_u, src_slot, dst_rack, dst_u, dst_slot, media)`.
- Group-internal ordering is `(src_port, dst_port)` ascending.
- Overlap reduction is minimal lane offset by index inside each group.
- Fixed media colors: `mmf_lc_duplex`, `smf_lc_duplex`, `mpo12`, `utp_rj45`.
- UI interactions are lightweight (no external JS): wheel zoom, drag pan, hover highlight,
  mode toggle, media/rack filters, click-to-focus, and Gap Jump Scale selection.
- Crossing readability in SVG uses gap+overpass rendering with adaptive scale (`Auto`) and
  user multipliers (`×0.50`, `×0.75`, `×1.25`, `×1.50`, `×2.00`).
- Draw.io exports (`wiring.drawio`, `integrated_wiring.drawio`) remain editable and apply
  edge jump styling (`jumpStyle=arc`, `jumpSize=6`) for crossing readability.

## 日本語訳

この実装は、ラック間配線割り当てに関する設計仕様に準拠しています。

- 対応メディア: MMF/SMF LC duplex、MPO12、UTP RJ45。
- スロットカテゴリ優先順位: MPO E2E → LC MMF → LC SMF → UTP。
- Mixed-in-U 割り当ては連続スロット予約により有効化されています。
- 決定的 ID は SHA-256 の正規化文字列を使用します。
- 保存されたリビジョンでは、生成された `panel/module/cable/session` 行を SQLite に永続化します。

### 設定: `ordering.peer_sort`

`ordering.peer_sort` は、割り当て中にラックのピアペアをどの順序で処理するかを制御します。
この値は project YAML の `settings.ordering.peer_sort` から読み取られます。

サポート値:

| 値 | 挙動 |
|---|---|
| `natural_trailing_digits`（デフォルト） | ラック ID の末尾数値サフィックスを優先して数値順で並べ替え、その後に文字列全体で比較します。`R2` は `R10` より先に並びます。 |
| `lexicographic` | ラック ID を単純な文字列として並べ替えます。`"1" < "2"` となるため、`R10` は `R2` より先に並びます。 |

上記以外の値は検証時に明確なエラーメッセージで拒否されます。

**例**（project YAML）:

```yaml
settings:
  ordering:
    peer_sort: lexicographic
```

### 設定: `panel.u_label_mode`

`panel.u_label_mode` は、Rack Panel Occupancy UI における U 番号の表示方法を制御します。
この設定は表示ラベルのみに影響し、割り当て動作は `settings.panel.allocation_direction` により制御されます。

サポート値:

| 値 | 挙動 |
|---|---|
| `ascending`（デフォルト） | 上から下へ `U1`, `U2`, `U3`, ... と表示します。 |
| `descending` | 上から下へ `Umax`, `Umax-1`, ... と表示します（例: 42U ラックでは `U42`, `U41`, ...）。 |

**例**（project YAML）:

```yaml
settings:
  panel:
    u_label_mode: descending
```

UI ページ:
- Upload
- Trial
- Project detail
- Diff（論理 + 物理タブ）
