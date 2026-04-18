# 07. 出力ファイル仕様（データ利用者向け）

本書は、本データ基盤が配布する**正規化済みデータの利用者**（他プロジェクト開発者・自治体・研究者）の
ためのリファレンスです。これだけ読めばデータを取り込めることを目指します。

- 正準スキーマ（機械可読）: [`schema/akiya-property.schema.json`](../schema/akiya-property.schema.json)（JSON Schema Draft 2020-12）
- タグ語彙: [`schema/tags.json`](../schema/tags.json) ／ 設計: [03](03-tag-taxonomy.md)
- **LLM/エージェントに渡す用**: [`prompts/akiya-dataset.md`](../prompts/akiya-dataset.md)（本仕様をプロンプト化したもの）
- ライセンス: **CC-BY 4.0**（出典表示が必須。§9）

---

## 1. 概要

- **1物件 = 1レコード（JSONオブジェクト）。** 物件には「登録（募集中）」と「成約済」が含まれる。
- **登録物件と成約物件は統合済み**で、`status` で区別する（[04](04-matching-schema.md)）。
- **キーは英語 snake_case で安定**。表記ゆれ・BOM・売買/賃貸の混在・単位不統一はすべて吸収済み。
- **欠損は `null`**。基盤側で補完・代表値埋めはしない（§6）。
- **座標（緯度経度）は無い。** 位置は都道府県＋市区町村まで（§6）。

## 2. 配布ファイルと形式

GitHub Releases（将来は Cloudflare R2）でリリース単位に以下を配布する（[06](06-distribution-license.md)）。

| ファイル | 形式 | 用途 |
| --- | --- | --- |
| `akiya-<year>.json` | JSON 配列 | 全件を一括ロード |
| `akiya-<year>.jsonl` | JSON Lines（1行=1レコード） | ストリーム/逐次処理・大規模取込 |
| `manifest.json` | JSON | 件数・スキーマ版・出典・ライセンス等のメタ |

- 文字コード **UTF-8（BOMなし）** / 改行 **LF** / 日付 **ISO 8601**（`YYYY-MM-DD`）。
- `json` と `jsonl` は同一内容（タグ等も両方に反映済み）。
- リリースタグ: `data-<year>.<schema_major>.<schema_minor>`（例 `data-2025.1.0`）。§7参照。

### manifest.json の例

```json
{
  "dataset_year": 2025,
  "schema_version": "1.0",
  "license": "CC-BY-4.0",
  "source_url": "https://www.geospatial.jp/ckan/dataset/links-akiyabank-2025",
  "record_counts": {
    "total": 8678, "registered": 7475, "closed": 1203,
    "closed_overlap": 271, "closed_only": 932, "tagged": 4943
  }
}
```

## 3. レコード構造（実例）

### 例1: 登録・売買・タグ付き

```json
{
  "id": "9000109",
  "dataset_year": 2025,
  "source": "registered",
  "status": "registered",
  "deal_type": "sale",
  "use_type": "residential",
  "category_raw": "売買居住用",
  "location": { "prefecture": "奈良県", "city": "吉野郡黒滝村", "point": null },
  "price_yen": 1000000,
  "rent_monthly_yen": null,
  "amount_raw": "1000000",
  "building": {
    "construction_year": 1950, "construction_date_raw": "1950/1/1",
    "structure": "木造", "layout": "4DK",
    "building_area_sqm": 100.56, "total_units": 2
  },
  "land": {
    "land_area_sqm": 549.91, "land_measurement_method": "公簿",
    "land_category": "宅地", "land_ownership": null,
    "city_planning_area": "非線引区域", "use_district": null,
    "floor_area_ratio": null, "building_coverage_ratio": null,
    "private_road": "無し", "setback": "無し", "connected_roads": "指定なし"
  },
  "access": {
    "train_line": "近鉄吉野線", "station": "下市口",
    "station_distance": { "raw": "16200", "minutes": null, "meters": 16200, "unit_confidence": "low" }
  },
  "flags": { "farmland": false, "retail_premises": false, "for_office_use": "1800", "interior_customizable": "1800" },
  "utilities": { "water_supply": "公営", "gas_supply": "プロパン", "drainage": "浄化槽" },
  "facilities": { "bath": "専用", "toilet": "専用", "parking": "無", "garden": "有り", "stove_heating": "ガス", "bath_note": null, "toilet_note": null, "bicycle_parking": null, "washer_place": null },
  "nearby_distances": { "shopping_district": "21200", "elementary_school": null, "junior_high_school": null, "supermarket": null, "convenience_store": null, "drug_store": null, "hospital": null, "playground": null, "bank": null },
  "strong_points": "改修は必要ですが、ロケーション抜群の立地にある物件",
  "tags": {
    "schema_version": "1.0", "model": "gpt-4.1-mini",
    "labels": {
      "renovation_needed": "required", "migration_friendly": false, "business_usable": false,
      "subsidy_mentioned": false, "vr_tour": false, "farmland_attached": false, "kominka": false,
      "view_nature": false, "near_school": false, "near_shopping": false,
      "parking_emphasized": false, "move_in_ready": false
    },
    "confidence": "high"
  },
  "contract": null,
  "provenance": {
    "source_file": "01_tourokubukken.csv", "source_row_index": 22, "dataset_year": 2025,
    "retrieved_date": null, "source_url": "https://www.geospatial.jp/ckan/dataset/links-akiyabank-2025",
    "license": "CC-BY-4.0"
  }
}
```

### 例2: 成約・contract あり（抜粋）

```json
{
  "id": "9001016", "source": "registered", "status": "closed",
  "deal_type": "sale", "use_type": "residential",
  "location": { "prefecture": "愛媛県", "city": "八幡浜市", "point": null },
  "price_yen": 9800000,
  "contract": { "is_closed": true, "date": "2025-10-24", "date_raw": "10/24/25", "amount_yen": 28000, "amount_raw": "28000" }
}
```

## 4. フィールド・リファレンス

凡例 — 型の `?` は `null` あり。詳細・制約は JSON Schema が正準。

### トップレベル

| キー | 型 | 説明 |
| --- | --- | --- |
| `id` | string | 物件ID（年度内で一意。突合・前年引継ぎのキー） |
| `dataset_year` | int | 元データの年度（例 2025） |
| `source` | enum | 由来ファイル: `registered` / `closed` |
| `status` | enum | **募集中/成約済: `registered` / `closed`（成約フラグ）** |
| `deal_type` | enum | 取引種別: `sale` / `rent` |
| `use_type` | enum | 用途: `residential` / `commercial` / `land` |
| `category_raw` | string | 元の物件種別（例「売買居住用」） |
| `price_yen` | int? | 売買価格（円）。`deal_type=sale` 時のみ。0/非公開は null |
| `rent_monthly_yen` | int? | 月額賃料（円）。`deal_type=rent` 時のみ |
| `amount_raw` | string? | 元の金額文字列 |
| `strong_points` | string? | PR自由文（改行はLF）。タグ分類の元 |
| `tags` | object? | AI分類結果（§5）。PR文が空なら `null` |
| `contract` | object? | 成約情報（§4 contract）。`status=registered` では `null` |

### location / building / land / access

- `location`: `prefecture`, `city`（必須）, `point`（将来の座標用。現状 `null`）。
- `building`: `construction_year`(int?), `construction_date_raw`(string?), `structure`(string?),
  `layout`(string? 例「4DK」), `building_area_sqm`(number?), `total_units`(int?)。
- `land`: `land_area_sqm`(number?), `land_category`, `land_ownership`, `city_planning_area`,
  `use_district`, `floor_area_ratio`(number? %), `building_coverage_ratio`(number? %),
  `land_measurement_method`, `private_road`, `setback`, `connected_roads`。
- `access`: `train_line`(string?), `station`(string?), `station_distance`(object?)。

#### `access.station_distance`（重要・要注意）

```jsonc
{ "raw": "16200", "minutes": null, "meters": 16200, "unit_confidence": "low" }
```

- 元データは登録＝単位なし数値、成約＝単位付き（分/m）で**単位が不統一**。
- `unit_confidence`:
  - `high` … 元値に単位明記（信頼できる）
  - **`low` … 単位を値から推定（≤60→分, >60→m）。鵜呑みにせず `raw` を確認すること。**
- 距離で絞り込む処理は `unit_confidence=="high"` のみ採用するか、`raw` で再判定する設計を推奨。

### flags / utilities / facilities / nearby_distances

- `flags.farmland` / `flags.retail_premises`: bool（「有り」→true）。
- `flags.for_office_use` / `flags.interior_customizable`: **未正規化の生値（string?）**。
  元データに数値等が混在し値域が未確定のため、現状は生値のまま（[02](02-normalization-schema.md) 未解決事項）。
- `utilities`（water_supply / gas_supply / drainage）, `facilities`（bath / toilet / parking / garden 等）,
  `nearby_distances`（elementary_school / supermarket / hospital 等）: いずれも**自由記述の生値（string?）で高欠損**。
  検索キーには使わず、表示・補助情報として扱うこと。

### `contract`（`status=closed` のみ）

| キー | 型 | 説明 |
| --- | --- | --- |
| `is_closed` | bool | 常に true |
| `date` | string? | 成約日（ISO `YYYY-MM-DD`）。**欠損約87%** |
| `date_raw` | string? | 元の値（米国式 MM/DD/YY） |
| `amount_yen` | int? | 成約額（円）。**欠損約92%** |
| `amount_raw` | string? | 元の値 |

> 成約日・成約額は**欠損が大半**。値がある場合も売出価格と乖離することがあるため、統計利用時は注意。

### `provenance`

`source_file`, `source_row_index`, `dataset_year`, `retrieved_date`, `source_url`, `license`。
データ単体で出典を辿れるよう各レコードに埋め込み（§9）。

## 5. `tags`（AI分類）

```jsonc
"tags": {
  "schema_version": "1.0",      // タグ語彙の版
  "model": "gpt-4.1-mini",      // 分類に使ったモデル
  "labels": { /* 12軸。下記 */ },
  "confidence": "high"          // high | medium | low（モデル自己申告）
}
```

`labels` の12軸（[03](03-tag-taxonomy.md) / [schema/tags.json](../schema/tags.json)）:

| 軸 | 型 | 意味 |
| --- | --- | --- |
| `renovation_needed` | enum | `required`/`done`/`as_is`/`unknown` 改修要否 |
| `migration_friendly` | bool | 移住向き |
| `business_usable` | bool | 事業利用可 |
| `subsidy_mentioned` | bool | 補助金言及 |
| `vr_tour` | bool | VR内覧 |
| `farmland_attached` | bool | 農地・家庭菜園付き |
| `kominka` | bool | 古民家 |
| `view_nature` | bool | 眺望・自然 |
| `near_school` | bool | 学校至近 |
| `near_shopping` | bool | 買物利便 |
| `parking_emphasized` | bool | 駐車場訴求 |
| `move_in_ready` | bool | 即入居可 |

利用上の約束:
- **bool は「PR文に明示的根拠があるとき true」**。言及なしは `false`（不明 ≠ true）。enum は根拠なしで `unknown`。
- `tags` は **PR文（`strong_points`）由来**。構造化列（例 `flags.farmland`）とは観点が異なるため、
  両者は補完関係。両方使うと精度が上がる。
- `strong_points` が空の物件は `tags: null`。

## 6. 欠損・データ品質の約束

- **欠損は `null`。基盤は補完しない。** 穴を埋めるか/どう埋めるかは利用側の判断（用途で最適が異なるため）。
- **座標なし。** `location.point` は将来拡張用で現状 `null`。市区町村名でのジオコーディングは利用側で。
- **駅距離 `unit_confidence=low`** は推定値（§4）。
- **成約日/額は高欠損**（§4 contract）。
- **`flags.for_office_use` / `interior_customizable`** は未正規化の生値。
- 自由記述系（utilities/facilities/nearby_distances）は表記ゆれ・高欠損。検索キーに使わない。

## 7. バージョニングと安定性

2層で管理（[05](05-diff-management.md)）。利用側はリリースタグ `data-<year>.<major>.<minor>` で固定できる。

- `dataset_year`: 元データの年度。
- `schema_version`: 構造版。**後方互換ルール**:
  - **マイナー（1.0→1.1）= 後方互換**。例: タグ軸の追加、新フィールド追加。既存利用者は無視すれば動く。
  - **メジャー（1.0→2.0）= 破壊的**。例: キーのリネーム・型変更・意味変更・削除。

**安定性保証**（メジャー版を上げずに）変えないもの:
- 既存キー名・型・意味、enum 値の意味、欠損の表現（`null`）。

**推奨**: 本番では `latest` ではなく**具体的なリリースタグにピン留め**し、更新時に差分（[05](05-diff-management.md)）を確認してから上げる。

## 8. 取り込み例

```python
# Python: 全件ロード → 募集中の「補助金言及」物件を抽出
import json
records = json.load(open("akiya-2025.json", encoding="utf-8"))
hits = [r for r in records
        if r["status"] == "registered"
        and r.get("tags") and r["tags"]["labels"]["subsidy_mentioned"]]
```

```bash
# jq: JSON Lines から 古民家 かつ 売買 を抽出
jq -c 'select(.deal_type=="sale" and (.tags.labels.kominka // false))' akiya-2025.jsonl
```

```javascript
// Node: jsonl をストリーム的に読む
import { readFileSync } from "node:fs";
const recs = readFileSync("akiya-2025.jsonl","utf8").trim().split("\n").map(JSON.parse);
const closedWithPrice = recs.filter(r => r.status === "closed" && r.contract?.amount_yen != null);
```

## 9. ライセンス・出典表示（必須）

- 本データは **CC-BY 4.0**。利用・再配布時は**出典表示が必須**（[06](06-distribution-license.md) / `ATTRIBUTION.md`）。
- 表示例:

  > 出典: 国土交通省 Project LINKS「空き家バンク（2025年度）」を加工して作成。
  > 加工: MLIT-LINKS-akiya-pipeline。ライセンス: CC-BY 4.0。

- 各レコードの `provenance` に出典URL・ライセンス・年度が入っているため、データ単体でも出典を辿れる。
