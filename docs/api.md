<!-- SPDX-License-Identifier: Apache-2.0 -->
<!--
This file was created or modified with the assistance of an AI (Large Language Model). Review for correctness and security.
-->

# API Documentation

This document provides a concise overview of any programmatic interfaces the project exposes (HTTP endpoints, Python package public API, CLI commands, etc). Fill in details relevant to the repository.

## HTTP / Web UI (if applicable)
- POST /upload
  - Description: Upload a project YAML for trial allocation.
  - Request: multipart/form-data with `project.yaml`.
  - Response: JSON with trial results or validation errors.

- GET /project/{id}/result
  - Description: Fetch results for a saved project.
  - Response: JSON with allocation and metadata.

(Replace or extend the above with actual endpoints implemented by the repo.)

## Python package public API (if applicable)
- patchwork.core.run_trial(project_yaml: str) -> dict
  - Description: Run deterministic allocation and return results.
  - Inputs: project YAML or parsed structure.
  - Outputs: result object (document shape here).

- patchwork.export.to_svg(result: dict, path: str) -> None
  - Description: Render topology as SVG.

(Add real module/function names and signatures from codebase.)

## CLI
- `python app.py` (starts web UI)
- `scripts/export_results.py --project-id <id>`

## Examples
See `examples/quick-start` for a minimal end-to-end example.

## 日本語訳

このドキュメントは、プロジェクトが公開するプログラムインターフェース
（HTTP エンドポイント、Python パッケージの公開 API、CLI コマンドなど）を簡潔にまとめたものです。

### HTTP / Web UI（該当する場合）
- POST /upload
  - 説明: 試行割り当てのために project YAML をアップロードします。
  - リクエスト: `project.yaml` を含む multipart/form-data。
  - レスポンス: 試行結果または検証エラーを含む JSON。

- GET /project/{id}/result
  - 説明: 保存済みプロジェクトの結果を取得します。
  - レスポンス: 割り当て結果とメタデータを含む JSON。

（上記は、リポジトリで実装されている実際のエンドポイントに置き換えるか拡張してください。）

### Python パッケージ公開 API（該当する場合）
- patchwork.core.run_trial(project_yaml: str) -> dict
  - 説明: 決定的割り当てを実行して結果を返します。
  - 入力: project YAML またはパース済み構造。
  - 出力: 結果オブジェクト（形状はこのドキュメントに記載）。

- patchwork.export.to_svg(result: dict, path: str) -> None
  - 説明: トポロジーを SVG として描画します。

（コードベースに合わせて、実際のモジュール/関数名とシグネチャに更新してください。）

### CLI
- `python app.py`（Web UI を起動）
- `scripts/export_results.py --project-id <id>`

### 例
最小のエンドツーエンド例は `examples/quick-start` を参照してください。
