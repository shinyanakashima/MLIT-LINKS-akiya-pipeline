# MLIT-LINKS-akiya-pipeline

国土交通省 Project LINKS「空き家バンク」オープンデータ（2025年度）を、表記ゆれ・欠損・
列構成の差異を吸収した**正規化済みJSON**として再配布するためのデータ基盤リポジトリ。

自社の他プロジェクト（4リポジトリ）が共通して取り込む**共有データソース**になることを
前提に設計しています。

- 元データ: [Project LINKS 空き家バンク 登録物件＋成約物件（2025年度）](https://www.geospatial.jp/ckan/dataset/links-akiyabank-2025)
- 成果物ライセンス: **CC-BY 4.0**（元データのライセンスを継承）
- 配布: GitHub Releases（大容量化したら Cloudflare R2 を想定）

## 想定ユーザーとユースケース

| ユーザー | ユースケース |
| --- | --- |
| 自社の他プロジェクト開発者 | 表記ゆれ・欠損を気にせず使える正規化済みJSONを取り込む |
| 自治体職員 | CC-BY 4.0 の整形済みデータを二次利用する |
| 研究者 | PR文（STRONG_POINTS）の分類タグ付きデータで分析する |

## 現在の状態

設計（[docs/](docs/)）に基づき、**正規化パイプラインの本体（取得・正規化・突合・JSON出力）を実装済み**。
実データで件数が設計値と一致し、出力 8,678 件すべてが JSON Schema 検証を通過することを確認しています。

| 機能 | 状態 |
| --- | --- |
| BOM安全CSV読込・フィールド内改行対応 | ✅ 実装済み |
| 正規化（売買/賃貸分離・単位統一・型付け・列名整理） | ✅ 実装済み |
| 登録×成約の突合（union・`status`生成・`contract`付与） | ✅ 実装済み |
| JSON / JSON Lines / manifest 出力・CLI | ✅ 実装済み |
| STRONG_POINTS の AI分類（Claude Sonnet バッチ） | ⏳ 次フェーズ（[docs/03](docs/03-tag-taxonomy.md)） |
| 差分管理・Releases配布の自動化 | ⏳ 次フェーズ（[docs/05](docs/05-diff-management.md), [docs/06](docs/06-distribution-license.md)） |

## 使い方

```bash
# CKANから元CSVを取得して、正規化・突合し dist/ に出力
python -m akiya_pipeline.cli build --fetch --out-dir dist

# 取得済みのローカルCSVを使う場合
python -m akiya_pipeline.cli build \
    --registered data/raw/01_tourokubukken.csv \
    --closed     data/raw/02_seiyakubukken.csv \
    --out-dir dist
```

出力（`dist/`）:
- `akiya-2025.json` … 全件・正規化済み（JSON配列）
- `akiya-2025.jsonl` … 同（JSON Lines）
- `manifest.json` … 件数サマリ・スキーマ版・出典・ライセンス

### テスト

```bash
PYTHONPATH=src python -m unittest discover -s tests
```

実データ統合テスト（件数検証）は `data/raw/` に元CSVがある場合のみ実行されます。

## ディレクトリ構成

```
src/akiya_pipeline/   パイプライン本体
  sources.py          CKANリソース定義・取得
  csv_reader.py       BOM安全CSV読込
  normalize.py        フィールド正規化（売買/賃貸分離・単位統一・型付け）
  match.py            登録×成約 突合（union・status・contract）
  pipeline.py         統合・JSON出力・manifest
  cli.py              CLI
schema/               JSON Schema・タグ語彙
docs/                 設計ドキュメント
tests/                テスト（unittest、依存ゼロ）
```

## ドキュメント

| ドキュメント | 内容 |
| --- | --- |
| [docs/01-data-source-notes.md](docs/01-data-source-notes.md) | 元データの実地調査メモ（列構成・欠損率・既知の課題の実測） |
| [docs/02-normalization-schema.md](docs/02-normalization-schema.md) | 正規化スキーマ（統一レコード定義・列マッピング・型・欠損方針・単位統一） |
| [docs/03-tag-taxonomy.md](docs/03-tag-taxonomy.md) | STRONG_POINTS のAI分類タグ体系と Claude Sonnet バッチ設計 |
| [docs/04-matching-schema.md](docs/04-matching-schema.md) | 登録ID×成約IDの突合スキーマ（成約フラグ生成方針） |
| [docs/05-diff-management.md](docs/05-diff-management.md) | 年1更新を見越した差分管理・バージョニング方針 |
| [docs/06-distribution-license.md](docs/06-distribution-license.md) | 配布形態・CC-BY 4.0・出典表示の方針 |

## スキーマ（機械可読）

| ファイル | 内容 |
| --- | --- |
| [schema/akiya-property.schema.json](schema/akiya-property.schema.json) | 正規化済み物件レコードの JSON Schema（Draft 2020-12） |
| [schema/tags.json](schema/tags.json) | 分類タグ語彙（カテゴリ・値・定義） |

## 設計の前提（要約）

- **粒度**: 正規化レコードは「物件1件 = JSONオブジェクト1件」。
- **統合範囲**: 登録物件と成約物件を**和集合（union）**で統合し、`status` で募集中/成約済を表現する
  （成約物件の大半は登録ファイルから消えるため、単純なフラグ付けでは取りこぼす — [04](docs/04-matching-schema.md) 参照）。
- **緯度経度なし**: 元データは都道府県＋市区町村まで。座標は持たない（ジオコーディングは将来課題）。
- **欠損前提**: 成約額・成約日は欠損が9割前後。欠損は `null` で明示し、補完しない。
- **AI分類**: STRONG_POINTS を Claude Sonnet の Message Batches でビルド時に一括分類し、
  タグ付き静的JSONを生成する（[03](docs/03-tag-taxonomy.md)）。

---

出典: 国土交通省 Project LINKS「空き家バンク（2025年度）」/ ライセンス CC-BY 4.0
