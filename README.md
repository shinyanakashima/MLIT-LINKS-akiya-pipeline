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

## 現在のフェーズ：設計

このリポジトリは現在**設計ドキュメントのみ**を含みます。実装（パイプラインコード）は
本設計の合意後に着手します。設計の出発点は、元データの実地調査に基づく
(1) 正規化スキーマ と (2) PR文分類のタグ体系 です。

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
