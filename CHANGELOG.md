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
- AI分類（`classify.py`）: プロバイダ非依存（プラグイン化）。
  - Anthropic（Message Batches + tool use）/ OpenAI（Batch API + Structured Outputs）。
  - 既定モデル: anthropic=claude-sonnet-4-6 / openai=gpt-4.1-mini。CLI `--provider` で切替。
  - CLI `classify`（`--provider` / `--dry-run` / `--limit`）。語彙は schema/tags.json と整合検証。
- GitHub Actions: `ci.yml`（テスト＋スキーマ検証）、`build.yml`（取得→分類→成果物アップロード）。

- `docs/07-output-spec.md`: データ利用者向けの出力ファイル仕様（配布形式・フィールド・enum・
  欠損方針・バージョニング・取込例・ライセンス）。README から導線を追加。
- `build.yml`: 本番運用向けに更新。schedule 実行でも分類＋公開を自動化、provider 既定を openai に。
  成果物を GitHub Releases へ公開（タグ `data-<year>.<schema>`、手動は publish 入力で制御）。
- `prompts/akiya-dataset.md`: 出力仕様を LLM/エージェント用プロンプトにまとめたもの。
  他プロジェクトに配布して利用側AIへ渡せる。docs/07 と同期。
- 差分管理（`diff.py` / CLI `diff`）: 前年版と id 単位で added/removed/status_changed/field_changed
  を検出し diff JSON を出力。`classify --prev` で PR文が同一の物件は前年タグを引き継ぎ再分類を省く。

### Fixed
- `classify` 実行後に json / jsonl / manifest を一括再生成するよう修正。従来は `.json` のみ更新し、
  `.jsonl` にタグが入らず、`manifest.json` の `tagged` が 0 のままで配布物が不整合だった。

### Notes
- AI分類の実行には対応キー（`ANTHROPIC_API_KEY` / `OPENAI_API_KEY`、Actions の Secrets）が必要。
  配布物は実行時API非依存。
- 未実装: 差分管理・Releases自動公開（次フェーズ）。
- 未解決: 駅距離の単位（仕様書 99_…xlsx で要確認）。docs/02 未解決事項を参照。
