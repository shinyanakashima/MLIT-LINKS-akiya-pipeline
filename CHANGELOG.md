# Changelog

スキーマ版（schema_version）の変更履歴。データセット年とは独立に追跡する（docs/05）。

形式は [Keep a Changelog](https://keepachangelog.com/) に準拠。

## [Unreleased]

### Added
- 設計フェーズ初版。実データ調査に基づく設計ドキュメント一式。
  - `docs/01-data-source-notes.md` 元データ実地調査メモ
  - `docs/02-normalization-schema.md` 正規化スキーマ
  - `docs/03-tag-taxonomy.md` STRONG_POINTS 分類タグ体系（Claude Sonnet バッチ設計）
  - `docs/04-matching-schema.md` 登録×成約 突合スキーマ
  - `docs/05-diff-management.md` 差分管理・バージョニング方針
  - `docs/06-distribution-license.md` 配布・ライセンス
  - `schema/akiya-property.schema.json` 物件レコード JSON Schema（schema_version 1.0）
  - `schema/tags.json` 分類タグ語彙（schema_version 1.0）

- 正規化パイプライン本体（標準ライブラリのみ）:
  - `src/akiya_pipeline/` 取得・BOM安全読込・正規化・突合・JSON/JSONL/manifest出力・CLI
  - `tests/` unittest（依存ゼロ）。実データで件数が設計値と一致・全件 JSON Schema 検証通過。

### Notes
- 未実装: AI分類実行（Claude Sonnet バッチ）・差分管理/配布の自動化（次フェーズ）。
- 未解決: 駅距離の単位（仕様書 99_…xlsx で要確認）。docs/02 未解決事項を参照。
