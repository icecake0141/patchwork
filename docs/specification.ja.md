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

# 仕様

## 対象範囲
Patchwork は `project.yaml` からラック間配線を決定的に割り当てます。

対応 endpoint_type:
- `mmf_lc_duplex`
- `smf_lc_duplex`
- `mpo12`
- `utp_rj45`

## 入力モデル
トップレベル項目:
- `version`（既定値 `1`）
- `project`
- `racks`
- `demands`
- `settings`

バリデーション:
- 未知キーは拒否（`extra="forbid"`）。
- `racks[].id` と `demands[].id` は一意。
- `demands[].src` と `demands[].dst` は異なる必要あり。
- `demands[].count` は `0` より大きい必要あり。
- 参照ラック ID は実在必須。

## 割り当て挙動
- 既定カテゴリ順: `mpo_e2e -> lc_mmf -> lc_smf -> utp`。
- ピア並び替え:
  - `natural_trailing_digits`（既定）
  - `lexicographic`
- パネル設定:
  - `slots_per_u`（既定 `4`）
  - `allocation_direction`: `top_down`（既定）または `bottom_up`
  - `u_label_mode`: `ascending`（既定）または `descending`（表示のみ）
- `aggregatable=true` は `mpo12` / `mmf_lc_duplex` / `smf_lc_duplex` で有効。

## 出力モデル
主な出力:
- `sessions.csv`
- `bom.csv`
- `result.json`
- `wiring.svg` / `wiring.drawio`
- `integrated_wiring.drawio`
- `integrated_wiring_interactive.svg`（`mode=aggregate|detailed`）
- `rack_occupancy.drawio`

`result.json` の主要キー:
- `panels`, `modules`, `cables`, `sessions`
- `warnings`, `errors`, `metrics`, `pair_details`

## Integrated Wiring View
- Trial / Project Detail で利用可能。
- UI の経路モード: `direct`, `detour`, `highway`, `stagger`。
- 操作:
  - media/rack フィルタ
  - クリックフォーカス
  - ズーム/パン
  - Gap Jump Scale（`Auto`, `Auto x 0.50`, `0.75`, `1.25`, `1.50`, `2.00`）

## 関連ドキュメント
- [API](api.ja.md)
- [テストと検証](testing.ja.md)
