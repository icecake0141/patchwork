<!-- SPDX-License-Identifier: Apache-2.0 -->
<!--
This file was created or modified with the assistance of an AI (Large Language Model).
Review required for correctness, security, and licensing.
-->

# シナリオB: 混在メディアの4ラック構成（日本語）

## 目的
複数 peer・複数メディアを含む、やや大きい構成で挙動を確認します。

## 入力ファイル
- `examples/onboarding/mixed-4rack.yaml`

## 入力の特徴
- ラック4台（`R01`..`R04`）
- 複数ラックペアに跨る需要5本
- メディア3種（`mmf_lc_duplex`, `mpo12`, `utp_rj45`）
- `peer_sort: natural_trailing_digits` により処理順が安定

## このパターンが有効な理由
- 複数 peer に需要が分散するケースを確認できる
- ほどよい規模で、実務寄りの確認ができる
- カテゴリ優先順位や並び順の影響を見やすい

## 期待される出力の形
### `result.json`
- `metrics.rack_count` は `4`
- `metrics.session_count` は需要合計（`16 + 12 + 8 + 5 + 4 = 45`）
- 正常系では `errors` は空（条件次第で `warnings` はあり得る）

### `sessions.csv`
- データ行は 45 行（ヘッダ除く）
- `media` は `mmf_lc_duplex`, `mpo12`, `utp_rj45`
- ラックペアは `R01-R02`, `R01-R03`, `R02-R04`, `R03-R04`

### `bom.csv`
- 混在メディアのため、module/cable の記述行が増える
- 2ラック構成より数量が増える

### 可視化成果物
- `wiring.svg` はシナリオAより密なトポロジ
- Integrated wiring view の `Aggregate` / `Detailed` 切替が有効

## クイック確認手順
1. `examples/onboarding/mixed-4rack.yaml` をアップロード
2. metrics で `rack_count == 4` と `session_count == 45` を確認
3. Integrated view で media フィルタを切替えて経路を確認
4. 2ラック構成の BOM と比較して複雑化を確認

## スクリーンショット（任意）
- Upload 画面

![混在4ラック Upload 画面](../images/upload-page.png)

- Project detail 画面

![混在4ラック Project detail 画面](../images/mixed-4rack/project-detail.png)

- Integrated Wiring（Aggregate）

![混在4ラック Integrated Wiring Aggregate](../images/mixed-4rack/integrated-aggregate.png)

- Integrated Wiring（Detailed）

![混在4ラック Integrated Wiring Detailed](../images/mixed-4rack/integrated-detailed.png)

## 関連ドキュメント
- [オンボーディング目次](../README.ja.md)
- [English version](mixed-4rack.en.md)
