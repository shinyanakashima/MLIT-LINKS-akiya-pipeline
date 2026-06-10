# MLIT-LINKS-akiya-pipeline

国土交通省 Project LINKS が公開する「空き家バンク」オープンデータを、**そのままでは使いにくい
表記ゆれ・欠損・年度ごとの列構成の差異を吸収した正規化済みJSON**に変換して再配布するための
データ基盤です。

CSVを直接ダウンロードして自前で前処理する代わりに、**検証済みの統一フォーマットのJSON/JSON Lines**を
取り込めば、空き家物件データをすぐに利用できます。

- **元データ**: [Project LINKS 空き家バンク 登録物件＋成約物件（2025年度）](https://www.geospatial.jp/ckan/dataset/links-akiyabank-2025)
- **ライセンス**: 成果物データは **CC-BY 4.0**（元データのライセンスを継承）。出典表示は [ATTRIBUTION.md](ATTRIBUTION.md) を参照。
- **配布**: [GitHub Releases](../../releases)（タグ例: `data-2025.1`）
- **収録件数**: 8,678 件（募集中＋成約済の和集合）

## このデータで何ができるか

| こんな人に | できること |
| --- | --- |
| アプリ・サービス開発者 | 表記ゆれ・欠損を気にせず使える正規化済みJSONを取り込んで、空き家検索/地図/分析機能を作れる |
| 自治体職員・公共データ利用者 | CC-BY 4.0 の整形済みデータを二次利用できる（元CSVの整形作業が不要） |
| 研究者・データ分析者 | 物件のPR文（STRONG_POINTS）にAIで分類タグが付与済みのため、定量分析にすぐ使える |

> もとは複数プロジェクトの共通データソースとして設計されたものですが、データ自体はオープンデータ
> （CC-BY 4.0）なので、誰でも自由に利用・再配布できます。

## データを入手して使う

データ利用者がやることは基本これだけです。**パイプラインを自分で動かす必要はありません。**

1. [Releases](../../releases) から最新の成果物を取得する。
2. 中身（フィールド・enum・欠損の扱い・取込例）は **[docs/07-output-spec.md（出力ファイル仕様）](docs/07-output-spec.md)** を読む。
   - データ利用者がまず読むべき唯一のリファレンスです。

配布される主なファイル:

| ファイル | 内容 |
| --- | --- |
| `akiya-2025.json` | 全件・正規化済み（JSON配列） |
| `akiya-2025.jsonl` | 同上（1行1レコードの JSON Lines。ストリーミング処理向け） |
| `manifest.json` | 件数サマリ・スキーマ版・出典・ライセンスのメタ情報 |
| `diff-*.json` | 前年版との差分（追加/削除/状態変化/フィールド変化） |

AI/エージェントにこのデータを扱わせたい場合は、出力仕様をそのまま渡せるプロンプト化版
[prompts/akiya-dataset.md](prompts/akiya-dataset.md) を利用できます。

機械可読なスキーマ:

| ファイル | 内容 |
| --- | --- |
| [schema/akiya-property.schema.json](schema/akiya-property.schema.json) | 物件レコードの JSON Schema（Draft 2020-12）。取込時のバリデーションに使える |
| [schema/tags.json](schema/tags.json) | AI分類タグの語彙（カテゴリ・値・定義） |

## このデータの性質（利用前に知っておくと良い前提）

- **粒度**: 1物件 = 1 JSONオブジェクト。
- **募集中と成約済を統合**: 登録物件と成約物件を**和集合（union）**で統合し、各レコードの `status` で
  募集中/成約済を表現する。成約物件の多くは登録ファイルから消えるため、単純なフラグ付けでは
  取りこぼす（[docs/04](docs/04-matching-schema.md) 参照）。
- **座標は持たない**: 元データは都道府県＋市区町村まで。緯度経度はなく、`location.point` は将来拡張用に
  常に `null`。地図表示が必要なら利用側でジオコーディングする。
- **欠損は埋めない**: 成約額・成約日は9割前後が欠損。欠損は `null` で明示し、推測で補完しない。
- **PR文のAI分類**: 物件のPR文（STRONG_POINTS）に分類タグが付与済み。分類はビルド時に一括実行して
  結果をJSONに焼き込むため、**利用側に実行時のAI API呼び出しは不要**（[docs/03](docs/03-tag-taxonomy.md)）。

---

# パイプラインを動かす人向け（開発・運用）

ここから下は、データを生成・更新する側（このリポジトリのメンテナ）向けの情報です。
**データを使うだけなら読む必要はありません。**

## 仕組み

このリポジトリは **UIを持たないヘッドレスのデータパイプライン**です。画面アプリではなく、
「信頼できる正規化済みJSON」を生成・配布することだけが役割です。

```
GitHub Actions（年次 schedule / 手動 dispatch）
  ① 元CSV取得（CKAN）→ ② 正規化・突合 → ③ STRONG_POINTS をAIで分類
  → ④ JSON/JSONL/manifest/diff 生成 → ⑤ GitHub Releases へ公開
```

- **常駐プロセス不要。** 年1回（＋必要なら手動）バッチを1回流すだけ。計算環境は GitHub Actions。
- **AI API キーが必要なのはビルド時（③）だけ。** `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` は
  Actions の Secrets に格納する。配布物・利用側ともに実行時APIには非依存。
- **配布は静的データ。** GitHub Releases（容量が大きくなれば Cloudflare R2 等への移行を想定）。

## 実装状況

設計（[docs/](docs/)）に基づき本体を実装済み。実データで件数が設計値と一致し、出力 8,678 件すべてが
JSON Schema 検証を通過することを確認済み。

| 機能 | 状態 |
| --- | --- |
| BOM安全CSV読込・フィールド内改行対応 | ✅ |
| 正規化（売買/賃貸分離・単位統一・型付け・列名整理） | ✅ |
| 登録×成約の突合（union・`status`生成・`contract`付与） | ✅ |
| JSON / JSON Lines / manifest 出力・CLI | ✅ |
| STRONG_POINTS の AI分類（Anthropic / OpenAI プラグイン・バッチ＋構造化出力強制） | ✅（実行は各社APIキーが必要） |
| GitHub Actions（CI＝テスト / Build＝取得・分類・公開） | ✅ |
| GitHub Releases 自動公開（年次schedule/手動） | ✅（[docs/06](docs/06-distribution-license.md)） |
| 年次差分管理（差分検出・前年タグ引き継ぎ） | ✅（[docs/05](docs/05-diff-management.md)） |

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

### AI分類（STRONG_POINTS のタグ付け）

Anthropic / OpenAI を `--provider` で切替（プラグイン化）。バッチ＋構造化出力強制（`temperature=0`、
Anthropic=tool use / OpenAI=Structured Outputs）で一括分類する。タグ体系は
[docs/03](docs/03-tag-taxonomy.md) / [schema/tags.json](schema/tags.json)。

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

# 前年タグの引き継ぎ（PR文が同一の物件は再分類しない＝コスト削減）
python -m akiya_pipeline.cli classify --in dist/akiya-2026.json --provider openai \
    --prev akiya-2025.json
```

### 年次差分

```bash
# 前年版との差分を検出（added/removed/status_changed/field_changed）
python -m akiya_pipeline.cli diff --prev akiya-2025.json --curr akiya-2026.json \
    --out dist/diff-2025-2026.json
```

詳細は [docs/05](docs/05-diff-management.md)。年次 Build ではこの差分を Release に同梱する。

### 年次更新（コード編集なし）

列構成が前年と同じなら、年度・取得URLを入力で上書きするだけで更新できる。

```bash
python -m akiya_pipeline.cli build --fetch --year 2026 \
    --registered-url <CKANのCSV URL> --closed-url <CKANのCSV URL> \
    --dataset-page <データセットページURL> --out-dir dist
# 環境変数 AKIYA_YEAR / AKIYA_REGISTERED_URL / AKIYA_CLOSED_URL / AKIYA_DATASET_PAGE でも可
```

運用ランブックは [docs/05](docs/05-diff-management.md)。

### GitHub Actions

- `.github/workflows/ci.yml` … push/PR でテスト＋スキーマ検証。
- `.github/workflows/build.yml` … 手動 or 年次で 取得→正規化→突合→（前年タグ引継ぎ）AI分類→
  年次差分→Releases公開。AI分類には Secrets のAPIキーを使用。

### テスト

```bash
PYTHONPATH=src python -m unittest discover -s tests
```

依存ゼロの unittest。実データ統合テスト（件数検証）は `data/raw/` に元CSVがある場合のみ実行される。

## ディレクトリ構成

```
src/akiya_pipeline/   パイプライン本体
  sources.py          CKANリソース定義・取得（年度/URLは入力で上書き可）
  csv_reader.py       BOM安全CSV読込
  normalize.py        フィールド正規化（売買/賃貸分離・単位統一・型付け）
  match.py            登録×成約 突合（union・status・contract）
  classify.py         STRONG_POINTS のAI分類（プロバイダ非依存）
  diff.py             年次差分検出
  pipeline.py         統合・JSON出力・manifest
  cli.py              CLI（build / classify / diff）
schema/               JSON Schema・タグ語彙
docs/                 設計ドキュメント
prompts/              利用側AI向けプロンプト
tests/                テスト（unittest、依存ゼロ）
.github/workflows/    CI（テスト）・Build（取得・分類・配布）
```

## 設計ドキュメント

| ドキュメント | 内容 |
| --- | --- |
| **[docs/07-output-spec.md](docs/07-output-spec.md)** | **出力ファイル仕様（データ利用者向けリファレンス）** |
| [docs/01-data-source-notes.md](docs/01-data-source-notes.md) | 元データの実地調査メモ（列構成・欠損率・既知の課題の実測） |
| [docs/02-normalization-schema.md](docs/02-normalization-schema.md) | 正規化スキーマ（統一レコード定義・列マッピング・型・欠損方針・単位統一） |
| [docs/03-tag-taxonomy.md](docs/03-tag-taxonomy.md) | STRONG_POINTS のAI分類タグ体系とバッチ設計 |
| [docs/04-matching-schema.md](docs/04-matching-schema.md) | 登録ID×成約IDの突合スキーマ（成約フラグ生成方針） |
| [docs/05-diff-management.md](docs/05-diff-management.md) | 差分管理・バージョニング方針・年次更新ランブック |
| [docs/06-distribution-license.md](docs/06-distribution-license.md) | 配布形態・CC-BY 4.0・出典表示の方針 |

---

出典: 国土交通省 Project LINKS「空き家バンク（2025年度）」/ ライセンス CC-BY 4.0
