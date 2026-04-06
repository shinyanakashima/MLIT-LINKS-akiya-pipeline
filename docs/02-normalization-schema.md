# 02. 正規化スキーマ

統一レコードの定義・列マッピング・型・欠損方針・単位統一ルール。
機械可読版は [`schema/akiya-property.schema.json`](../schema/akiya-property.schema.json)（JSON Schema Draft 2020-12）。

## 設計原則

1. **物件1件 = JSONオブジェクト1件。** 出力は1物件1レコードの配列、または JSON Lines（[06](06-distribution-license.md)）。
2. **キーは英語 snake_case。** 元の英語列名の誤記（`GUS_SUPPLY`, `COMBINIENCE`）はここで吸収する。
3. **値の正規化は「曖昧さを増やさない範囲」に留める。** 確実に機械処理できるもの（BOM除去・
   取引種別分離・単位パース・型付け・boolean化）だけ正規化し、自由記述（設備・PR文・間取り）は
   生値を保持する。
4. **欠損は補完しない。** 欠損・非公開・`0`（金額）は `null` で明示する。利用側が方針を選べるよう、
   推定を伴う値には確信度フラグ・生値を併記する。
5. **生値を捨てない。** 正規化で情報が落ちる項目（金額・駅距離・築年）は `*_raw` を必ず併置する。
6. **登録／成約を1スキーマで表現。** 差分は `status` / `source` / `contract` で吸収する（[04](04-matching-schema.md)）。

## レコード構造（概観）

```jsonc
{
  "id": "9000002",                    // 物件ID（登録 PROPERTY_NUMBER_ID / 成約 ID）
  "dataset_year": 2025,
  "source": "registered",             // 由来ファイル: registered | closed
  "status": "registered",             // 募集中/成約済: registered | closed
  "deal_type": "sale",                // 売買/賃貸: sale | rent
  "use_type": "residential",          // 用途: residential | commercial | land
  "category_raw": "売買居住用",        // 元 PROPERTY_CATEGORY

  "location": { "prefecture": "山梨県", "city": "甲府市" },

  "price_yen": 19800000,              // 売買価格（deal_type=sale のみ、それ以外 null）
  "rent_monthly_yen": null,          // 月額賃料（deal_type=rent のみ）
  "amount_raw": "19800000",          // 元 AMOUNT/RENT

  "building": {
    "construction_year": 1958,       // 築年（年精度）
    "construction_date_raw": "1958/2/1",
    "structure": "木造",              // CONSTRUCTION（"指定なし"→null）
    "layout": "4SLDK",               // LAYOUT/NUMBER_OF_ROOMS（生値）
    "building_area_sqm": 95.2,       // OCCUPATION_AREA
    "total_units": null              // TOTAL_NUMBER_OF_UNITS
  },

  "land": {
    "land_area_sqm": 160.5,          // SIZE_OF_LOT
    "land_measurement_method": null, // SIZE_OF_LOT_MEASUREMENT_METHOD
    "land_category": null,           // LAND_CATEGORY
    "land_ownership": "所有権",        // LAND_OWNERSHIP
    "city_planning_area": null,      // CITY_PLANNING_AREA
    "use_district": null,            // USE_DISTRICT
    "floor_area_ratio": null,        // FLOOR_AREA_RATIO（%）
    "building_coverage_ratio": null, // BUILDING_COVERAGE_RATIO（%）
    "private_road": "...",           // PRIVATE_ROAD
    "setback": "...",                // SETBACK
    "connected_roads": "..."         // NUMBER_OF_CONNECTED_ROADS
  },

  "access": {
    "train_line": "中央本線",          // NEAREST_TRAIN_LINE
    "station": "甲府駅",               // NEAREST_STATION
    "station_distance": {            // DISTANCE_TO_NEAREST_STATION_ON_FOOT（§単位統一）
      "raw": "3600",
      "minutes": null,
      "meters": 3600,
      "unit_confidence": "low"       // 登録(数値のみ)は low、成約(単位付き)は high
    }
  },

  "flags": {
    "farmland": false,               // FARMLAND（有り→true）
    "retail_premises": false,        // RETAIL_PREMISES
    "for_office_use": null,          // FOR_OFFICE_USE
    "interior_customizable": null    // INTERIOR_CUSTOMIZABILITY
  },

  "utilities": {                     // 自由記述・生値保持（欠損多）
    "water_supply": null, "gas_supply": null, "drainage": null
  },
  "facilities": {                    // 自由記述・生値保持（欠損多）
    "bath": null, "toilet": null, "toilet_note": null, "parking": null,
    "garden": null, "washer_place": null, "stove_heating": null,
    "bicycle_parking": null          // 成約のみ
  },
  "nearby_distances": {              // 自由記述・生値保持（高欠損）
    "elementary_school": null, "junior_high_school": null,
    "supermarket": null, "convenience_store": null, "drug_store": null,
    "hospital": null, "shopping_district": null, "playground": null, "bank": null
  },

  "strong_points": "甲府市中心部に近く利便性良好。…",  // PR文 生値
  "tags": null,                      // AI分類結果（[03] 参照、未分類時 null）

  "contract": null,                  // 成約情報（status=closed のみ。[04] 参照）

  "provenance": {
    "source_file": "01_tourokubukken.csv",
    "source_row_index": 1,
    "dataset_year": 2025,
    "retrieved_date": "2026-05-31",
    "source_url": "https://www.geospatial.jp/ckan/dataset/links-akiyabank-2025",
    "license": "CC-BY-4.0"
  }
}
```

## 列マッピング表

凡例 — 型: `str`/`int`/`float`/`bool`/`obj`。欠損方針: **null**＝欠損は null、**raw**＝生値保持。

| 正規化キー | 元列（登録 / 成約） | 型 | 変換ルール | 欠損方針 |
| --- | --- | --- | --- | --- |
| `id` | PROPERTY_NUMBER_ID / ID | str | トリム。数値でも文字列で保持（ゼロ埋め等の保全） | 必須 |
| `source` | （ファイル由来） | str | `registered`/`closed` | 必須 |
| `status` | （[04] で導出） | str | `registered`/`closed` | 必須 |
| `deal_type` | PROPERTY_CATEGORY 接頭 | str | `売買`→`sale` / `賃貸`→`rent` | 必須 |
| `use_type` | PROPERTY_CATEGORY 接尾 | str | `居住用`→`residential` / `事業用`→`commercial` / `土地`→`land` | 必須 |
| `category_raw` | PROPERTY_CATEGORY | str | そのまま | 必須 |
| `location.prefecture` | PREFECTURE | str | トリム | 必須 |
| `location.city` | CITY | str | トリム | 必須 |
| `price_yen` | AMOUNT/RENT | int | `deal_type=sale` のとき採用。`0`/非数値→null | null |
| `rent_monthly_yen` | AMOUNT/RENT | int | `deal_type=rent` のとき採用。`0`/非数値→null | null |
| `amount_raw` | AMOUNT/RENT | str | そのまま | raw |
| `building.construction_year` | DATE_OF_CONSTRUCTION | int | `YYYY/…` の年部分。範囲外(<1850,>当年)→null | null |
| `building.construction_date_raw` | DATE_OF_CONSTRUCTION | str | そのまま | raw |
| `building.structure` | CONSTRUCTION | str | `指定なし`→null | null |
| `building.layout` | LAYOUT / NUMBER_OF_ROOMS | str | 生値（`4SLDK` 等） | raw |
| `building.building_area_sqm` | OCCUPATION_AREA | float | 純数値パース | null |
| `building.total_units` | TOTAL_NUMBER_OF_UNITS | int | 純数値パース | null |
| `land.land_area_sqm` | SIZE_OF_LOT | float | 純数値パース | null |
| `land.land_measurement_method` | SIZE_OF_LOT_MEASUREMENT_METHOD | str | 生値 | null |
| `land.land_category` | LAND_CATEGORY | str | 生値 | null |
| `land.land_ownership` | LAND_OWNERSHIP | str | 生値 | null |
| `land.city_planning_area` | CITY_PLANNING_AREA | str | 生値 | null |
| `land.use_district` | USE_DISTRICT | str | 生値 | null |
| `land.floor_area_ratio` | FLOOR_AREA_RATIO | float | 純数値パース（%） | null |
| `land.building_coverage_ratio` | BUILDING_COVERAGE_RATIO | float | 純数値パース（%） | null |
| `land.private_road` | PRIVATE_ROAD | str | 生値 | raw |
| `land.setback` | SETBACK | str | 生値 | raw |
| `land.connected_roads` | NUMBER_OF_CONNECTED_ROADS | str | 生値 | raw |
| `access.train_line` | NEAREST_TRAIN_LINE | str | トリム | null |
| `access.station` | NEAREST_STATION | str | トリム | null |
| `access.station_distance` | DISTANCE_TO_NEAREST_STATION_ON_FOOT | obj | §単位統一 | null |
| `flags.farmland` | FARMLAND | bool | `有り`→true / `無し`→false | 既定 false |
| `flags.retail_premises` | RETAIL_PREMISES | bool | 同上（値域は実装時に確認） | 既定 false |
| `flags.for_office_use` | FOR_OFFICE_USE | str/bool | 生値（値域確認後 bool 化検討） | null |
| `flags.interior_customizable` | INTERIOR_CUSTOMIZABILITY | str/bool | 同上 | null |
| `utilities.*` | WATER_SUPPLY / GUS_SUPPLY / DRAINAGE | str | 生値（誤記 GUS→gas に統一） | null |
| `facilities.*` | BATH / TOILET / TOILET_NOTE / PARKING / GARDEN / PLACE_OF_WASHER / STOVE_HEATING_SYSTEM / (BATH_NOTE,BICYCLE_PARKING:成約) | str | 生値 | null |
| `nearby_distances.*` | DISTANCE_TO_* 各種 | str | 生値（誤記 COMBINIENCE→convenience に統一） | null |
| `strong_points` | STRONG_POINTS | str | 改行正規化（CRLF→LF、前後トリム）。内容は保持 | null |
| `tags` | （AI分類） | obj | [03] 参照 | null（未分類） |
| `contract` | CONTRACT_INFO_DATE / CONTRACT_INFO_AMOUNT/RENT | obj | [04] 参照 | null |
| `provenance.*` | （メタ） | obj | 生成時に付与 | 必須 |

## 単位統一ルール

### 金額（AMOUNT/RENT）
- `deal_type` で振り分け: `sale`→`price_yen`、`rent`→`rent_monthly_yen`。一方のみ非null、他方は null。
- 値は円単位の整数。`0` および非数値（応談等）→ null。`amount_raw` に原文を保持。

### 駅距離（DISTANCE_TO_NEAREST_STATION_ON_FOOT）
登録は単位なし数値、成約は単位付き（`分`/`m`）で混在している（[01](01-data-source-notes.md) §2.3）。
出力は常に下記オブジェクトとし、確信度を明示する。

```jsonc
"station_distance": {
  "raw": "<原文>",
  "minutes": <int|null>,   // 徒歩分
  "meters":  <int|null>,   // メートル
  "unit_confidence": "high" | "low"
}
```

- **成約（単位付き）** → `high`。`"4分"`→`{minutes:4}`、`"750m"`→`{meters:750}`。
- **登録（単位なし）** → `low`。値だけからは確定不能なため、暫定ヒューリスティック:
  - `value <= 60` → `minutes` に格納（徒歩分とみなす）
  - `value > 60`  → `meters` に格納（メートルとみなす）
  - いずれも `unit_confidence: "low"`。利用側は `raw` で再判定可能。
- このヒューリスティックは**仕様書（99_…xlsx）で単位定義が確認でき次第、確定ルールに置き換える**
  （未解決事項。下記参照）。

### 築年（DATE_OF_CONSTRUCTION）
- 年精度。`construction_year`（int）を主とし、`construction_date_raw` に原文。
- 妥当範囲（1850〜当該データセット年）外は `null`。

### boolean 化
- `有り`→`true` / `無し`→`false`。判定不能・空→既定値（farmland/retail は false、その他は null）。

### 文字列正規化（全フィールド共通）
- BOM除去（読み込み時 `utf-8-sig`）。
- 前後空白トリム。全角空白（`　`）は内容として保持（PR文の体裁を壊さない）。
- 改行は LF に統一。空文字列は `null` に変換。

## 未解決事項（設計レビューで確定したい）

1. **駅距離の単位**: 登録の数値が分/メートルのどちらか、仕様書で要確認。確定するまでは上記
   ヒューリスティック＋`unit_confidence: low`。
2. **`RETAIL_PREMISES` / `FOR_OFFICE_USE` / `INTERIOR_CUSTOMIZABILITY` の値域**: bool 化可能か、
   自由記述かを実データの全値域で確認してから型確定。
3. **面積の単位**: `OCCUPATION_AREA` / `SIZE_OF_LOT` は㎡前提（仕様書で確認）。
4. **緯度経度**: 現状なし。`location` に都道府県＋市区町村のみ。将来ジオコーディングするなら
   `location.point`（GeoJSON）を後方互換で追加できるよう、`location` をオブジェクトにしてある。
