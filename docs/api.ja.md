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

# API

## Web エンドポイント
- `GET /` -> `/upload` へリダイレクト
- `GET /upload`
- `POST /upload`（multipart フィールド `project_yaml`）
- `GET /trial`
- `POST /save`
- `GET /projects/<project_id>?revision_id=<optional>`
- `GET /diff/<project_id>?rev1=<id>&rev2=<id>`
- `GET /pair-svg/<revision_id>/<rack_a>/<rack_b>`

## エクスポートエンドポイント
- `GET /revisions/<revision_id>/export/sessions.csv`
- `GET /revisions/<revision_id>/export/bom.csv`
- `GET /revisions/<revision_id>/export/result.json`
- `GET /revisions/<revision_id>/export/wiring.svg`
- `GET /revisions/<revision_id>/export/wiring.drawio`
- `GET /revisions/<revision_id>/export/integrated_wiring.drawio`
- `GET /revisions/<revision_id>/export/integrated_wiring_interactive.svg?mode=aggregate|detailed`
- `GET /revisions/<revision_id>/export/rack_occupancy.drawio`

## 実行時制約
- 最大アップロードサイズ: `1 MiB`（`MAX_CONTENT_LENGTH = 1024 * 1024`）
- セッション秘密鍵: 環境変数 `SECRET_KEY`、未設定時 `dev-secret`

## コア Python API
- `services.allocator.allocate(project: ProjectInput) -> dict[str, Any]`

戻り値の主なキー:
- `project`, `input_hash`
- `panels`, `modules`, `cables`, `sessions`
- `warnings`, `errors`, `metrics`, `pair_details`

## Diff 判定ルール
論理差分キー:
- `session_id`

物理差分キー:
- `(media, src_rack, src_face, src_u, src_slot, src_port, dst_rack, dst_face, dst_u, dst_slot, dst_port)`

## 関連ドキュメント
- [仕様](specification.ja.md)
- [ユーザーガイド](user-guide.ja.md)
