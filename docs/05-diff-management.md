# 05. 差分管理・バージョニング方針

元データは**年1回更新**（年度版）。共有データソースとして、過去版の再現性と変更追跡を担保する。

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

## 年次更新フロー（想定）

```
1. 元データ取得      … CKAN から当年度CSVを取得。取得日時・元URL・チェックサムを記録。
2. スナップショット   … raw を年度別に保管（リポジトリには置かず Release/別ストレージ。.gitignore）。
3. 正規化           … [02][04] に従い統一JSONを生成。
4. 差分検出         … 前年版と id 単位で diff（後述）。
5. AI分類（差分のみ） … 新規・PR文変更分のみ Claude Sonnet で再分類。前年タグを id で引き継ぎ。
6. 検証            … [04] の整合チェック＋スキーマ検証（JSON Schema）＋件数回帰。
7. 配布            … Release `data-<year>.<schema>` を作成（[06]）。
```

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
