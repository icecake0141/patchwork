<!-- SPDX-License-Identifier: Apache-2.0 -->
<!--
This file was created or modified with the assistance of an AI (Large Language Model).
Review required for correctness, security, and licensing.
-->

# 初見ユーザ向けオンボーディングガイド（日本語）

このガイドは、2つの実践パターンで **どの入力を与えると、どの出力が得られるか** を説明します。

## 推奨の読み順（目次）
1. このガイドの目的と到達点
2. 最小入力構造（`project.yaml`）
3. パターンA — シンプルな2ラック構成
4. パターンB — やや複雑な4ラック構成
5. 出力の読み方（`result.json` / `sessions.csv` / `bom.csv` / 図面系）
6. よくあるバリデーションエラー
7. 次のステップ

## 1) このガイドの目的と到達点
- `project.yaml` をゼロから作成できる。
- 実行前に、生成される出力の形を予測できる。
- Trial / Project detail の結果を素早く確認できる。

## 2) 最小入力構造（`project.yaml`）
有効な入力は次の要素で構成されます。
- `version`
- `project`
- `racks`
- `demands`
- （任意）`settings`

完全な項目定義は `examples/quick-start/README.md` と `docs/api.md` を参照してください。

## 3) パターンA — シンプルな2ラック構成
- ドキュメント: [Simple 2-rack scenario（英語）](scenarios/simple-2rack.en.md)
- ドキュメント: [シンプルな2ラック構成（日本語）](scenarios/simple-2rack.ja.md)
- 入力ファイル: `examples/onboarding/simple-2rack.yaml`
- 想定用途: まずは1ペア構成で最短理解したい場合。

## 4) パターンB — やや複雑な4ラック構成
- ドキュメント: [Mixed 4-rack scenario（英語）](scenarios/mixed-4rack.en.md)
- ドキュメント: [混在メディアの4ラック構成（日本語）](scenarios/mixed-4rack.ja.md)
- 入力ファイル: `examples/onboarding/mixed-4rack.yaml`
- 想定用途: 複数 peer・複数 media の割当挙動を確認したい場合。

## 5) 出力の読み方
- `result.json`: 割当結果全体（`panels`, `modules`, `cables`, `sessions`, `metrics`）
- `sessions.csv`: 1接続（1セッション）ごとのポート割当表
- `bom.csv`: 必要部材の集計
- `wiring.svg` / `integrated_wiring.drawio` / `rack_occupancy.drawio`: 可視化成果物

## 6) よくあるバリデーションエラー
- ラックID / 需要ID の重複
- `src` と `dst` が同一
- 未定義ラックを `src` / `dst` に指定
- 非対応 `endpoint_type` や設定値の誤り

## 7) 次のステップ
- Web UI の `/upload` からオンボーディング用サンプルを投入
- シナリオ記載の期待出力と突き合わせ
- その後、実案件向けの YAML に展開

## 8) スクリーンショット
- スクリーンショットは `docs/onboarding/images/` 配下に配置できます。
- 推奨のファイル名・配置は `docs/onboarding/images/README.md` を参照してください。
- 実ファイルを配置すると、各シナリオページの画像リンクからそのまま参照できます。

## English version
- [Onboarding Guide (English)](README.en.md)
