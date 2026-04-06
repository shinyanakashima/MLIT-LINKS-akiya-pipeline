# 01. 元データ実地調査メモ

> 本メモは、後続の正規化スキーマ・タグ体系設計の根拠となる**実測値**を記録するもの。
> 調査日: 2026-05-31 / 対象: Project LINKS 空き家バンク 2025年度。

## 1. データソース

| ファイル | 内容 | 行数 | 列数 | エンコーディング |
| --- | --- | --- | --- | --- |
| `01_tourokubukken.csv` | 登録物件（募集中） | 7,746 | 45 | UTF-8 **(BOM付き)** |
| `02_seiyakubukken.csv` | 成約物件 | 1,203 | 51 | UTF-8 **(BOM付き)** |
| `99_..._dataspecificationdocument_2025.xlsx` | データ仕様書 | — | — | XLSX |

ダウンロードURL（CKAN resource）:

- 登録: `https://www.geospatial.jp/ckan/dataset/da1b7c8d-164f-4fdd-977b-3c49c7396c08/resource/d1cbba16-4972-4bab-bcf5-e275b26a18de/download/01_tourokubukken.csv`
- 成約: `https://www.geospatial.jp/ckan/dataset/da1b7c8d-164f-4fdd-977b-3c49c7396c08/resource/1dcf6cac-13bc-4505-b7dd-20dba3258a1d/download/02_seiyakubukken.csv`
- 仕様書: `https://www.geospatial.jp/ckan/dataset/da1b7c8d-164f-4fdd-977b-3c49c7396c08/resource/220cf926-cd1a-4c4e-bba2-9d2b0c074d59/download/99_akiyabank_dataspecificationdocument_2025.xlsx`

## 2. 既知の課題の実測

ブリーフに挙がっていた課題を実データで確認した結果。

### 2.1 BOM付きUTF-8 / フィールド内改行
- 両ファイルとも先頭に UTF-8 BOM（`EF BB BF`）あり。読み込み時は `utf-8-sig` 相当の除去が必須。
- `STRONG_POINTS`（PR文）に**フィールド内改行**を含む行が登録で **1,539 件**。RFC 4180 準拠の
  CSVパーサ（クオート対応）で読む前提。素朴な行分割は不可。

### 2.2 売買と賃貸が AMOUNT/RENT 列に混在
- `AMOUNT/RENT` 列は売買価格と月額賃料が同一列に混在。
- ただし **`PROPERTY_CATEGORY` で判別可能**。値は以下の6種（登録物件の分布）:

  | PROPERTY_CATEGORY | 件数 | 比率 | 取引種別 | 用途 |
  | --- | --- | --- | --- | --- |
  | 売買居住用 | 4,883 | 63.0% | 売買 | 居住 |
  | 売買土地 | 2,082 | 26.9% | 売買 | 土地 |
  | 賃貸居住用 | 537 | 6.9% | 賃貸 | 居住 |
  | 賃貸土地 | 165 | 2.1% | 賃貸 | 土地 |
  | 賃貸事業用 | 41 | 0.5% | 賃貸 | 事業 |
  | 売買事業用 | 38 | 0.5% | 売買 | 事業 |

- 金額の桁も種別を裏付ける（売買居住用 中央値 480万円 / 賃貸居住用 中央値 4.5万円）。
- `AMOUNT/RENT == 0` が 6 件 → 「応談・非公開」とみなし `null` 扱い候補。

### 2.3 駅距離の単位不統一
- **登録**: `DISTANCE_TO_NEAREST_STATION_ON_FOOT` は**数値のみ（単位なし）**。しかも
  分とメートルが混在している疑いが濃厚。非空 4,379 件のうち **≤60 が 1,470 件（徒歩分の可能性）**、
  **>60 が 2,909 件（メートルの可能性、最大 200,000）**。
  → 値だけからは単位を確定できない。**生値を保持しつつ、ヒューリスティック推定値に確信度フラグを付す**方針（[02](02-normalization-schema.md) §単位統一）。
- **成約**: 単位付き。`分`（477件）/ `m`（309件）。こちらはパースで確実に分離可能。

### 2.4 登録と成約で列構成が違う
- 列名・列数が異なる（45 vs 51）。成約のみに `CONTRACT_INFO_DATE` / `CONTRACT_INFO_AMOUNT/RENT` /
  `NUMBER_OF_ROOMS` / `BATH_NOTE` / `BICYCLE_PARKING` / `DISTANCE_TO_COMBINIENCE_STORE`（原文ママ・スペルミス） /
  `DISTANCE_TO_PLAYGROUND` / `DISTANCE_TO_BANK` / `LOCAL_GOVERNMENT_PREFECTURE` / `LOCAL_GOVERNMENT_CITY` などがある。
- 登録のキーは `PROPERTY_NUMBER_ID`、成約のキーは `ID`（同じID空間）。
- 列名に原文の誤記あり（`GUS_SUPPLY`＝GAS, `DISTANCE_TO_COMBINIENCE_STORE`＝CONVENIENCE）。
  正規化後の英語キーで吸収する。

### 2.5 成約額・成約日の欠損
- 成約ファイル内（1,203件）での欠損率:
  - `CONTRACT_INFO_DATE`: **86.9% 欠損**（実値 158 件）
  - `CONTRACT_INFO_AMOUNT/RENT`: **92.2% 欠損**（実値 94 件）
  - `ID`: 欠損 0%
- 成約日フォーマットは `MM/DD/YY`（米国式、例 `02/25/25` = 2025-02-25）。
  築年月日 `YYYY/M/D` とは別フォーマットなので個別パースが必要。

### 2.6 緯度経度なし
- 位置情報は `PREFECTURE` ＋ `CITY` まで。座標列なし。
- `CITY` は政令市・郡を含む完全表記（例 `南松浦郡新上五島町`, `吉野郡黒滝村`）。

### 2.7 築年は実質「年」精度
- `DATE_OF_CONSTRUCTION` は `YYYY/M/D` 形式だが、**日部分は 4,294/(非空) 件が `1`**。
  月も建築時期の目安に過ぎず、実質「年（〜年月）精度」。`construction_year` を主フィールドとし、
  生値を別途保持する。

## 3. ID 突合（登録×成約）の実測 — 重要

- 成約の非空ID 1,203 件のうち、登録 `PROPERTY_NUMBER_ID` に**一致したのは 271 件のみ**。
- 残り **932 件は登録ファイルに存在しない**（成約後に登録一覧から削除されたと解釈）。
- → 「登録レコードに成約フラグを立てる」だけでは 932 件を取りこぼす。
  **両ファイルの和集合**で統合し、`status` で表現する設計が必要（[04](04-matching-schema.md)）。

## 4. 列ごとの欠損率（登録物件 7,746 件）

正規化時の欠損方針・型選択の根拠。主要列を抜粋（全列は調査済み）。

| 列 | 欠損率 | 備考 |
| --- | --- | --- |
| PROPERTY_NUMBER_ID / PROPERTY_CATEGORY / PREFECTURE / CITY | 0.0% | 必須キー・確実に存在 |
| CONSTRUCTION / PRIVATE_ROAD / SETBACK / NUMBER_OF_CONNECTED_ROADS / FARMLAND / RETAIL_PREMISES | 0.0% | 既定値（「指定なし」等）で埋まっている |
| AMOUNT/RENT | 10.9% | |
| SIZE_OF_LOT | 11.5% | 非空はすべて純数値 |
| LAYOUT | 6.5% | 例 `4SLDK`, `2DK`, `R` |
| OCCUPATION_AREA | 37.2% | 非空はすべて純数値（㎡） |
| NEAREST_STATION / NEAREST_TRAIN_LINE | 40.8% | |
| STRONG_POINTS | 41.1% | 非空 4,566 件＝AI分類の対象 |
| DISTANCE_TO_NEAREST_STATION_ON_FOOT | 43.5% | 単位不明（§2.3） |
| DATE_OF_CONSTRUCTION | 44.6% | 年精度（§2.7） |
| LAND_CATEGORY / DRAINAGE / WATER_SUPPLY | 48〜49% | |
| CITY_PLANNING_AREA | 56.3% | |
| FLOOR_AREA_RATIO / BUILDING_COVERAGE_RATIO | 66% | 非空は純数値（%） |
| LAND_OWNERSHIP | 72.2% | 大半 `所有権` |
| USE_DISTRICT | 74.5% | |
| STOVE_HEATING_SYSTEM / GARDEN / PLACE_OF_WASHER | 80〜86% | 設備系は高欠損 |
| TOTAL_NUMBER_OF_UNITS | 90.4% | 非空は純数値 |
| DISTANCE_TO_DRUG_STORE / SUPERMARKET / HOSPITAL | 84〜91% | 周辺距離は高欠損・自由記述 |

**示唆**: 設備・周辺距離系は欠損が大きく自由記述ゆれも多いため「補完せず生値＋null」。
数値系（面積・容積率・建ぺい率・戸数）は非空がすべて純数値なので安全に型付け可能。

## 5. 正規化に効く値域メモ

- `CONSTRUCTION`（構造）: `木造` `鉄骨造` `RC(鉄筋コンクリート)` `軽量鉄骨造` `ブロック造`
  `SRC(鉄骨鉄筋コンクリート)` `鉄筋ブロック造` `CFT(コンクリート充填鋼管)` `その他` `指定なし`。
  → `指定なし` は `null` 化候補。
- `LAND_OWNERSHIP`（権利）: `所有権`（多数）/ `定期地上権` `旧法地上権` `定期賃借権` `一時使用`
  `普通賃借権` `普通地上権` `旧法賃借権`（各少数）。
- `FARMLAND`: `無し`(7,105) / `有り`(641) → boolean 化可能。
- `LAYOUT`: `<数字><記号>` 形式（`4SLDK`, `2DK`）。土地は `R` 等。正規化はせず生値保持を推奨。
