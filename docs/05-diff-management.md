# 05. 差分管理・バージョニング方針

元データは**年1回更新**（年度版）。共有データソースとして、過去版の再現性と変更追跡を担保する。

> **実装状況**: 差分検出は `src/akiya_pipeline/diff.py`（CLI `akiya-pipeline diff`）、
> 前年タグの引き継ぎは `classify --prev` で実装済み。年次 Build（`build.yml`）は前年リリースを
> 取得して「タグ引き継ぎ＋差分生成＋Releasesへ差分同梱」を自動で行う。

## バージョニングの2層

| 層 | 何を表すか | 例 | 付与先 |
| --- | --- | --- | --- |
| **データセット年（dataset_year）** | 元データの年度 | `2025`, `2026` | 各レコード・Release タグ |
| **スキーマ版（schema_version）** | 正規化スキーマ／タグ体系の構造版 | `1.0`, `1.1` | リポジトリ・`tags`・メタファイル |

- データ更新（年度版）と、構造変更（列追加等）を**独立に**追跡する。
- Release タグ規約: `data-<year>.<schema_major>.<schema_minor>`（例 `data-2025.1.0`）。
  これにより「2025年度データ・スキーマv1.0」が一意に特定できる。

## 不変条件（年をまたいで守る）

1. **`id` は年度内で安定**。突合（[04](04-matching-schema.md)）と前年タグ引き継ぎ（[03](03-tag-taxonomy.md)）の基盤。
   - 留意: 元データ側でIDが年度間で再利用／再割当される可能性は要監視（年次取込時に検査）。
2. **スキーマ変更は後方互換を原則**:
   - 既存キーのリネーム・型変更・意味変更は **schema_major** を上げる破壊的変更。
   - 新キー・新タグ軸の追加は **schema_minor**（後方互換）。
   - 破壊的変更時は移行メモを `CHANGELOG.md` に記載。
3. **欠損方針は変えない**: 欠損は null。補完を始める場合は別フィールド（`*_imputed`）で、生値を壊さない。

## 年次更新の実行手順（運用ランブック）

取得先（年度ごとに変わる）は**コードに固定せず、入力で上書き**できる。列構成が同じなら
**コード編集は不要**で、「Build dataset」を新しい値で実行するだけ。

### 手順
1. **新年度データのURLを調べる。** geospatial.jp で当年度の「Project LINKS 空き家バンク」を開き、
   登録CSV・成約CSVの**ダウンロードURL**と**データセットページURL**を控える。
2. **「Build dataset」ワークフローを手動実行**（Actions → Run workflow）し、入力に:
   - `year` = 当年度（例 `2026`）
   - `registered_url` / `closed_url` = 1 のCSV URL
   - `dataset_page` = 出典ページURL
   - `provider` = `openai`（既定）、`publish` = `true`
   - これだけで、取得→正規化→突合→**前年タグ引き継ぎ**→**前年差分生成**→Release `data-<year>.<schema>` 公開 まで自動。
3. **検証。** Release ノートの差分サマリ・`manifest.json` の件数、新規/変更分のタグを数件確認。

> CLI 単体でも同様: `akiya-pipeline build --fetch --year 2026 --registered-url … --closed-url … --dataset-page …`
> （環境変数 `AKIYA_YEAR` / `AKIYA_REGISTERED_URL` / `AKIYA_CLOSED_URL` / `AKIYA_DATASET_PAGE` でも可）。

### 列構成が変わっていた場合（例外対応）
元データの列が増減・改名していたら、入力上書きだけでは不足。`normalize.py` / `match.py` を調整し、
**後方互換でなければ `schema_version`（メジャー）を上げる**（上記「不変条件」）。テスト緑・JSON Schema 検証を確認してから配布。

### 年次スケジュール（自動）について
`build.yml` の `schedule`（毎年4/5）は**コード既定の取得先**で走る。当年度のURLは年で変わるため、
**スケジュールに任せきりにせず、上記2の手動実行（新URL指定）を基本**とする
（または事前に既定値を当年度へ更新しておく）。

## 差分検出（id 単位）

前年版と当年版を `id` で突合し、レコード単位の変化を出す。

| 区分 | 意味 |
| --- | --- |
| `added` | 当年に新規出現したID |
| `removed` | 前年にあり当年に消えたID（成約・取下げ等） |
| `status_changed` | `registered` → `closed` など状態遷移 |
| `field_changed` | 属性（価格・面積・PR文等）が変化 |
| `unchanged` | 変化なし |

- 差分サマリは Release ノートに自動記載（例: `added 1,200 / removed 800 / closed 300`）。
- **PR文（STRONG_POINTS）が変化した物件だけ AI 再分類**してコストを抑える（[03](03-tag-taxonomy.md)）。
- 差分成果物（`diff-<prevYear>-<year>.json`）も配布物に含めると、利用側の増分取込が容易。

## 再現性

- 各 Release に同梱するメタファイル `manifest.json`（案）:
  - `dataset_year`, `schema_version`, `generated_at`
  - 元データの `source_url` / `resource_id` / `sha256`（取得時点のチェックサム）
  - `record_counts`（total / registered / closed / tagged）
  - 使用した分類モデル（`claude-sonnet-4-6`）と `tags.schema_version`
- これにより、任意の過去版を「どの元データ・どのスキーマ・どのモデルで作ったか」まで遡れる。

## リポジトリに置くもの / 置かないもの

| 置く | 置かない（.gitignore / 別ストレージ） |
| --- | --- |
| 設計ドキュメント・スキーマ定義・（将来）パイプラインコード | 元CSV（再配布は元データ規約に従い Release で） |
| `CHANGELOG.md` / `manifest.json` の雛形 | 巨大な生成JSON（配布は Release / R2） |
| 正解ラベルセット（小規模・分類QA用） | API キー等のシークレット |
