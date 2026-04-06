# 03. STRONG_POINTS 分類タグ体系

`STRONG_POINTS`（物件のPR自由文）を AI で分類し、構造化タグを付与する。
分類はビルド時に **Claude Sonnet の Message Batches API** で一括実行し、結果を静的JSONに焼き込む
（実行時にAPIを叩かない＝再配布物は純粋な静的データ）。

- 対象: 登録 4,566 件 ＋ 成約の非空分（STRONG_POINTS が非空のレコードのみ）。
- 想定モデル: **Claude Sonnet（`claude-sonnet-4-6`）**。分類精度を重視。
- 出力: 各レコードの `tags` オブジェクト（[02](02-normalization-schema.md)）。

## タグ体系（語彙）

機械可読版は [`schema/tags.json`](../schema/tags.json)。下表が正準定義。
原則として**各軸は独立**（多ラベル可）。値は `true`/`false`/`null`（言及なし=判断不能は null ではなく
「該当の根拠なし=false」と区別する: §出力規約）。

| 軸キー | 日本語名 | 型 | 定義（PR文中に根拠がある場合に true） |
| --- | --- | --- | --- |
| `renovation_needed` | 改修要否 | enum | `required`(要改修/要リフォーム明記) / `done`(改修済・リフォーム済) / `as_is`(現状渡し) / `unknown` |
| `migration_friendly` | 移住向き | bool | 移住・田舎暮らし・二地拠点・定住促進等を訴求 |
| `business_usable` | 事業利用可 | bool | 店舗/事務所/民泊/古民家カフェ等の事業転用を訴求 |
| `subsidy_mentioned` | 補助金言及 | bool | 補助金・助成・支援制度・改修補助等への言及 |
| `vr_tour` | VR内覧 | bool | VR内覧・オンライン内見・360度・動画内覧等への言及 |
| `farmland_attached` | 農地付き | bool | 農地・畑・田・家庭菜園が付帯（FARMLAND列と相互検証可） |
| `kominka` | 古民家 | bool | 古民家・古民家風・伝統的家屋・茅葺等 |
| `view_nature` | 眺望・自然 | bool | 眺望・海/山/富士山ビュー・自然環境の良さを訴求 |
| `near_school` | 学校至近 | bool | 学校・保育園・通学利便を訴求 |
| `near_shopping` | 買物利便 | bool | スーパー・商店街・買い物利便を訴求 |
| `parking_emphasized` | 駐車場訴求 | bool | 駐車場（複数台可等）を積極訴求 |
| `move_in_ready` | 即入居可 | bool | 即入居可・residence ready・家具家電付き等 |

> 軸は将来追加し得る。**追加は後方互換**（既存軸の意味を変えない・キーをリネームしない）を厳守
> （[05](05-diff-management.md) のバージョニング方針に従う）。

## `tags` 出力スキーマ

```jsonc
"tags": {
  "schema_version": "1.0",
  "model": "claude-sonnet-4-6",
  "labels": {
    "renovation_needed": "required",      // enum
    "migration_friendly": true,
    "business_usable": false,
    "subsidy_mentioned": false,
    "vr_tour": false,
    "farmland_attached": true,
    "kominka": true,
    "view_nature": true,
    "near_school": false,
    "near_shopping": false,
    "parking_emphasized": true,
    "move_in_ready": false
  },
  "evidence": {                            // 任意: 判定根拠の短い抜粋（任意軸のみ）
    "kominka": "築100年の古民家"
  },
  "confidence": "high"                     // high | medium | low（モデル自己申告）
}
```

- STRONG_POINTS が空の物件は `tags: null`（分類対象外）。

## 出力規約（モデルへの指示の核）

1. **PR文中に明示的な根拠がある場合のみ true**。推測・一般論で true にしない。
2. bool 軸は常に `true`/`false` を返す（「言及なし」は `false`）。`null` は使わない。
3. enum 軸（`renovation_needed`）は根拠がなければ `unknown`。
4. `evidence` は任意。誤検出レビュー用に、true にした軸の根拠語句を短く（任意）。
5. 出力は**指定 JSON のみ**。前置き・説明文を出さない。

## Claude Sonnet バッチ設計

### バッチ構成
- **Message Batches API** で非同期一括処理。1リクエスト=1物件（`custom_id` に物件ID）。
- 入力トークン削減のため、**タクソノミ定義（システムプロンプト）を prompt caching** で固定。
  全リクエストで共通の長い指示部をキャッシュし、物件ごとの差分は STRONG_POINTS 本文のみ。
- **構造化出力**: tool use（`record_tags` ツール）で上記スキーマを JSON Schema として強制し、
  パース失敗を防ぐ。

### 推奨パラメータ（実装時の初期値）
- `model`: `claude-sonnet-4-6`
- `max_tokens`: 512（出力は小さい）
- `temperature`: 0（分類は決定的に）
- システムプロンプト: タクソノミ定義＋出力規約（キャッシュ）
- ユーザーメッセージ: 物件のPR文（必要なら `category_raw` を補助文脈として付与）

### 想定プロンプト骨子

```
system（キャッシュ対象）:
  あなたは日本の空き家バンク物件のPR文を分類する専門家です。
  以下の軸に従い、PR文中に明示的根拠がある場合のみタグを付与してください。
  [タクソノミ定義表] / [出力規約] / record_tags ツールで出力。

user:
  物件カテゴリ: {category_raw}
  PR文:
  """
  {strong_points}
  """
```

### 品質保証
- **少量の正解セット（〜100件）を手動ラベリング**し、軸ごとの precision/recall を測る回帰指標とする。
- `confidence: low` または enum=`unknown` が多発する軸は、定義文を見直す。
- `farmland_attached`（タグ）と `flags.farmland`（列由来）の**不一致率**を監視（タグ誤り検知に有効）。
- 全件の**再分類は決定的**（temperature=0＋固定プロンプト）。`schema_version`/`model` を `tags` に記録し、
  再現性とバージョン差分管理（[05](05-diff-management.md)）を担保する。

### コスト・運用メモ
- 年1更新（[05](05-diff-management.md)）かつビルド時バッチのため、**新規・PR文変更分のみ再分類**する
  差分実行が基本（前年タグを `id` で引き継ぐ）。
- Batches はリアルタイム比でコスト有利。`temperature=0`＋caching でさらに低減。
- API キーは CI シークレット（`ANTHROPIC_API_KEY`）で注入。分類結果（タグ付きJSON）はリポジトリ／
  Releases にコミットし、配布物は API 非依存にする。
