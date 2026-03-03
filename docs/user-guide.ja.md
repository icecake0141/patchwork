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

# ユーザーガイド

## 基本フロー
1. `/upload` を開く。
2. `project.yaml` をアップロード。
3. `/trial` で結果確認。
4. `/save` でリビジョン保存。
5. `/projects/<project_id>` で成果物をエクスポート。

## ダウンロード分類（Project Detail）
- Raw Data: `sessions.csv`, `bom.csv`, `result.json`
- Cable Wiring Diagram: `wiring.svg`, `wiring.drawio`
- Integrated Wiring View: `integrated_wiring.drawio`
- Integrated Wiring View（Interactive）:
  - `integrated_wiring_interactive.svg?mode=aggregate`
  - `integrated_wiring_interactive.svg?mode=detailed`
- Rack Occupancy: `rack_occupancy.drawio`

## Integrated Wiring の操作
- 経路またはラベルをクリックしてフォーカス。
- 同じ対象を再クリック（または空白クリック）で解除。
- media / rack でフィルタ。
- マウス操作でズーム/パン。
- Gap Jump Scale: `Auto`, `Auto x 0.50`, `0.75`, `1.25`, `1.50`, `2.00`。

## 補足
- Draw.io 出力は編集可能ですが、フィルタ/フォーカス等の対話機能は含みません。
- Interactive SVG はブラウザ閲覧向けであり、Draw.io 編集用ではありません。
