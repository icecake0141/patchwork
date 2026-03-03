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

# テストと検証

## ローカルセットアップ
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## 推奨検証コマンド
- Lint: `ruff check .`
- フォーマット確認: `black --check .`
- 型チェック: `mypy .`
- 単体/結合テスト: `pytest -q`
- pre-commit: `pre-commit run --all-files`

## 任意の Docker 統合テスト
```bash
RUN_DOCKER_TESTS=1 pytest -q tests/test_docker_compose.py
```

## テスト対象領域
- 入力モデル検証: `tests/test_models_validation.py`, `tests/test_models.py`
- 割り当て挙動: `tests/test_allocator_*.py`, `tests/test_slot_category_priority.py`, `tests/test_peer_sort.py`, `tests/test_allocation_direction.py`
- エクスポート: `tests/test_export.py`
- DB: `tests/test_db.py`
- E2E スモーク: `tests/test_acceptance_smoke.py`, `tests/test_allocator_acceptance.py`
- オンボーディングサンプル: `tests/test_onboarding_samples.py`

## CI 概要
GitHub Actions（`.github/workflows/ci.yml`）で以下を実行:
- `ruff`, `black --check`, `mypy`
- `pytest -q`
- Docker 関連ファイル変更時の `main` push で Docker 統合テスト
