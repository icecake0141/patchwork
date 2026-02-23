<!-- SPDX-License-Identifier: Apache-2.0 -->
<!--
This file was created or modified with the assistance of an AI (Large Language Model).
Review required for correctness, security, and licensing.
-->

# シナリオA: シンプルな2ラック構成（日本語）

## 目的
最小構成で、入力と出力の対応関係を理解します。

## 入力ファイル
- `examples/onboarding/simple-2rack.yaml`

## 入力の特徴
- ラック2台（`R01`, `R02`）
- 1つのラックペアに対して需要2本
- メディアは最小混在（`mmf_lc_duplex`, `utp_rj45`）

## このパターンが有効な理由
- 初回実行の確認が速い
- ラベル（`R01U...` -> `R02U...`）を追いやすい
- MPO や peer 増加前のベースラインに向く

## 期待される出力の形
### `result.json`
- `metrics.rack_count` は `2`
- `metrics.session_count` は需要合計（`12 + 6 = 18`）
- 正常系では `errors` は空

### `sessions.csv`
- データ行は 18 行（ヘッダ除く）
- `media` は `mmf_lc_duplex` と `utp_rj45`
- `src_rack` / `dst_rack` は `R01` / `R02` のみ

### `bom.csv`
- 少なくとも `panel` / `module` / `cable` が含まれる
- 数量は需要数とモジュール収容数に応じて増減

### 可視化成果物
- `wiring.svg` は単一 peer のシンプルな配線関係
- Integrated view でも重なりが少なく確認しやすい

## クイック確認手順
1. `examples/onboarding/simple-2rack.yaml` をアップロード
2. `result.json` の metrics で `session_count == 18` を確認
3. `sessions.csv` でラックペアが1種類のみであることを確認
4. BOM の使用メディアに対応する数量が 0 でないことを確認

## スクリーンショット（任意）
- Upload 画面

![シンプル2ラック Upload 画面](../images/simple-2rack/upload-page.png)

- Project detail 画面

![シンプル2ラック Project detail 画面](../images/simple-2rack/project-detail.png)

- Integrated Wiring（Aggregate）

![シンプル2ラック Integrated Wiring Aggregate](../images/simple-2rack/integrated-aggregate.png)

- Integrated Wiring（Detailed）

![シンプル2ラック Integrated Wiring Detailed](../images/simple-2rack/integrated-detailed.png)

## 関連ドキュメント
- [オンボーディング目次](../README.ja.md)
- [English version](simple-2rack.en.md)
