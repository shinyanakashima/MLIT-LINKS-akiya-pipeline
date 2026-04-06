# 06. 配布形態・ライセンス

## ライセンス

- 元データ: 国土交通省 Project LINKS「空き家バンク（2025年度）」。**CC-BY 4.0**。
- 本リポジトリの成果物（正規化済みデータ）も **CC-BY 4.0** で再配布する（継承）。
- パイプラインの**コード**は別途オープンソースライセンス（MIT 等）を想定。データとコードの
  ライセンスは分けて明記する。

### 出典表示（CC-BY の Attribution）
配布物・派生物には以下を表示する（例）:

> 出典: 国土交通省 Project LINKS「空き家バンク（2025年度）」を加工して作成。
> 加工: MLIT-LINKS-akiya-pipeline（正規化・取引種別分離・単位統一・PR文分類）。
> ライセンス: CC-BY 4.0。

`provenance` フィールド（[02](02-normalization-schema.md)）に出典URL・ライセンス・取得日を各レコードへ埋め込み、
データ単体でも出典が辿れるようにする。

## 配布形態

### 一次配布: GitHub Releases
- Release タグ規約 `data-<year>.<schema_major>.<schema_minor>`（[05](05-diff-management.md)）。
- 同梱物（案）:

  | ファイル | 内容 |
  | --- | --- |
  | `akiya-<year>.json` | 全件・正規化済み（JSON配列） |
  | `akiya-<year>.jsonl` | 同（JSON Lines。ストリーム取込向け） |
  | `akiya-<year>.registered.jsonl` / `.closed.jsonl` | status 別の分割（任意） |
  | `manifest.json` | メタ（件数・チェックサム・元データ resource_id・分類モデル等） |
  | `diff-<prevYear>-<year>.json` | 前年差分（[05](05-diff-management.md)） |
  | `schema/akiya-property.schema.json` | この版の JSON Schema |
  | `LICENSE` / `ATTRIBUTION` | ライセンス・出典 |

### 二次配布: Cloudflare R2（大容量化時）
- データが GitHub Releases の実用上限に近づいたら R2 に移行。
- R2 では**安定URL**（`/<year>/akiya-<year>.jsonl` 等）と `latest` エイリアスを提供。
- `manifest.json` は両所で同一・チェックサム一致を保証。

## 利用側（他4プロジェクト）への提供形態

- **安定スキーマ**: JSON Schema を配布物に同梱。`schema_version` で互換性判定可能。
- **取込単位の選択肢**: 全件JSON / JSONL / status別分割 / 差分。用途に応じて選べる。
- **APIキー不要**: 配布物は静的データ（AI分類はビルド時に焼き込み済み）。利用側は取得するだけ。
- **`latest` 参照**: 常に最新年度を指すエイリアスを用意し、固定年度参照も可能にする。

## 推奨フォーマット指針

- 文字コード **UTF-8（BOMなし）**。
- 改行 **LF**。
- 日付は **ISO 8601**（`YYYY-MM-DD`）。
- 数値はネイティブ数値型（文字列にしない）。欠損は `null`（空文字列・`"0"` を使わない）。
- キーは英語 snake_case で安定（[02](02-normalization-schema.md)）。
