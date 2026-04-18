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

## アーキテクチャ（性質）

このリポジトリは **UIを持たないヘッドレスのデータ基盤（パイプライン）** です。画面アプリではなく、
「信頼できるJSON」を生成・配布する**他4プロジェクトの共通土台**です。

- **UIなし。** 人が見る画面が必要になるのは、この土台の上に乗る他プロジェクト側。将来データ閲覧UIが
  必要になれば、別物の静的サイトとして切り出す（public→GitHub Pages / private→ConoHa WING）。
- **計算環境は GitHub Actions。** 常駐プロセスは不要。年1回（＋手動）、下記バッチを1回流すだけ。
  AI分類もこのビルド時に一括実行し、結果をJSONに焼き込むため、**配布物・利用側ともに実行時API非依存**。
- **配布は静的データ。** GitHub Releases（大容量化したら Cloudflare R2）。

```
GitHub Actions（年次 schedule / 手動 dispatch）
  ① 元CSV取得（CKAN）→ ② 正規化・突合 → ③ STRONG_POINTS をAI分類（Claude Sonnet）
  → ④ JSON/JSONL/manifest 生成 → ⑤ Releases / R2 へ配布
```

`ANTHROPIC_API_KEY` が必要なのは Actions のビルド時（③）だけで、Secrets に格納する。

## 現在の状態

設計（[docs/](docs/)）に基づき、**正規化パイプラインの本体（取得・正規化・突合・JSON出力）を実装済み**。
実データで件数が設計値と一致し、出力 8,678 件すべてが JSON Schema 検証を通過することを確認しています。

| 機能 | 状態 |
| --- | --- |
| BOM安全CSV読込・フィールド内改行対応 | ✅ 実装済み |
| 正規化（売買/賃貸分離・単位統一・型付け・列名整理） | ✅ 実装済み |
| 登録×成約の突合（union・`status`生成・`contract`付与） | ✅ 実装済み |
| JSON / JSON Lines / manifest 出力・CLI | ✅ 実装済み |
| STRONG_POINTS の AI分類（Anthropic / OpenAI プラグイン・バッチ＋構造化出力強制） | ✅ 実装済み（実行は各社APIキーが必要） |
| GitHub Actions（CI＝テスト / Build＝取得・分類） | ✅ 実装済み |
| GitHub Releases 自動公開（build.yml、年次schedule/手動） | ✅ 実装済み（[docs/06](docs/06-distribution-license.md)） |
| 差分管理（年次差分検出） | ⏳ 次フェーズ（[docs/05](docs/05-diff-management.md)） |

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

### AI分類（STRONG_POINTS のタグ付け）

Anthropic / OpenAI を `--provider` で切替（プラグイン化）。バッチ＋構造化出力強制で一括分類。

```bash
# 送信せず対象件数・リクエスト内容だけ確認（APIキー不要）
python -m akiya_pipeline.cli classify --in dist/akiya-2025.json --provider openai --dry-run --limit 1

# Anthropic（既定。claude-sonnet-4-6 / Message Batches）
export ANTHROPIC_API_KEY=...                # 通常は Actions の Secrets で注入
pip install "anthropic>=0.40"               # extras: classify-anthropic
python -m akiya_pipeline.cli classify --in dist/akiya-2025.json

# OpenAI（gpt-4.1-mini / Batch API + Structured Outputs）
export OPENAI_API_KEY=...
pip install "openai>=1.50"                   # extras: classify-openai
python -m akiya_pipeline.cli classify --in dist/akiya-2025.json --provider openai --limit 50
```

`temperature=0`＋出力スキーマ強制（Anthropic=tool use / OpenAI=Structured Outputs）で実行。
分類タグ体系は [docs/03](docs/03-tag-taxonomy.md) / [schema/tags.json](schema/tags.json)。

### GitHub Actions

- `.github/workflows/ci.yml` … push/PR でテスト＋スキーマ検証。
- `.github/workflows/build.yml` … 手動 or 年次で 取得→正規化→突合→AI分類→成果物アップロード。
  AI分類には Secrets の `ANTHROPIC_API_KEY` を使用。

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
  classify.py         STRONG_POINTS のAI分類（Claude Sonnet バッチ）
  pipeline.py         統合・JSON出力・manifest
  cli.py              CLI（build / classify）
schema/               JSON Schema・タグ語彙
docs/                 設計ドキュメント
tests/                テスト（unittest、依存ゼロ）
.github/workflows/    CI（テスト）・Build（取得・分類・配布）
```

## ドキュメント

> **データを使う人はまず [docs/07-output-spec.md](docs/07-output-spec.md)（出力ファイル仕様）を参照。**

| ドキュメント | 内容 |
| --- | --- |
| **[docs/07-output-spec.md](docs/07-output-spec.md)** | **出力ファイル仕様（利用者向けリファレンス：配布形式・フィールド・enum・欠損・バージョン・取込例・ライセンス）** |
| [prompts/akiya-dataset.md](prompts/akiya-dataset.md) | 出力仕様を**LLM用プロンプト化**したもの（他プロジェクトのAI/エージェントにそのまま渡せる） |
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
