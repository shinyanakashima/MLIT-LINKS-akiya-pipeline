"""フィールド単位の正規化。

元CSVの1行（dict）を、正規化スキーマ（docs/02 / schema/akiya-property.schema.json）の
レコード（dict）に変換する。登録・成約の列構成差は ``row.get`` で吸収する。

設計原則（docs/02）:
- 確実に機械処理できるものだけ正規化し、自由記述は生値を保持する。
- 欠損は補完せず None（JSONでは null）。
- 生値を捨てない（金額・駅距離・築年は ``*_raw`` を併置）。
"""

from __future__ import annotations

import re
from typing import Any

from . import sources  # 年度・出典は configure() で上書きされ得るため実行時に参照する

# ── 小さなパーサ ──────────────────────────────────────────────


def clean_str(value: str | None) -> str | None:
    """前後トリム・改行をLF統一。空文字列は None にする。全角空白は保持。"""
    if value is None:
        return None
    s = value.replace("\r\n", "\n").replace("\r", "\n").strip()
    return s or None


def parse_int(value: str | None) -> int | None:
    """純粋な整数のみ受理。それ以外（空・単位付き等）は None。"""
    s = clean_str(value)
    if s is None or not re.fullmatch(r"\d+", s):
        return None
    return int(s)


def parse_float(value: str | None) -> float | None:
    """純粋な数値のみ受理。それ以外は None。"""
    s = clean_str(value)
    if s is None or not re.fullmatch(r"\d+(\.\d+)?", s):
        return None
    return float(s)


def parse_yen(value: str | None) -> int | None:
    """金額（円・整数）。0 は「応談・非公開」とみなし None（docs/02）。"""
    n = parse_int(value)
    return n if n else None  # 0 と None をまとめて None に


def parse_bool_arinashi(value: str | None) -> bool | None:
    """「有り」→True / 「無し」→False / その他・空→None。"""
    s = clean_str(value)
    if s is None:
        return None
    if s in ("有り", "有", "あり"):
        return True
    if s in ("無し", "無", "なし"):
        return False
    return None


# ── 取引種別・用途（PROPERTY_CATEGORY の分解） ─────────────────

_DEAL = {"売買": "sale", "賃貸": "rent"}
_USE = {"居住用": "residential", "事業用": "commercial", "土地": "land"}


def split_category(category: str | None) -> tuple[str | None, str | None]:
    """PROPERTY_CATEGORY を (deal_type, use_type) に分解（docs/02）。

    例: "売買居住用" → ("sale", "residential")
    """
    s = clean_str(category)
    if s is None:
        return None, None
    deal = next((v for k, v in _DEAL.items() if s.startswith(k)), None)
    use = next((v for k, v in _USE.items() if s.endswith(k)), None)
    return deal, use


# ── 築年（DATE_OF_CONSTRUCTION、実質「年」精度） ────────────────


def parse_construction_year(value: str | None) -> int | None:
    """"YYYY/M/D" 等から年を取り出す。妥当範囲(1850〜当年)外は None。"""
    s = clean_str(value)
    if s is None:
        return None
    m = re.match(r"(\d{4})", s)
    if not m:
        return None
    year = int(m.group(1))
    return year if 1850 <= year <= sources.DATASET_YEAR else None


# ── 駅距離（単位不統一。docs/02 単位統一） ─────────────────────

_MINUTES_THRESHOLD = 60  # これ以下の単位なし数値は徒歩分とみなす


def parse_station_distance(value: str | None) -> dict[str, Any] | None:
    """最寄駅徒歩距離を {raw, minutes, meters, unit_confidence} に正規化。

    - 単位付き("4分"/"750m") → 確実にパースし unit_confidence="high"
    - 単位なし数値           → ヒューリスティック(≤60=分, >60=m) で unit_confidence="low"
    """
    raw = clean_str(value)
    if raw is None:
        return None

    minutes: int | None = None
    meters: int | None = None
    confidence = "low"

    m_min = re.fullmatch(r"(\d+)\s*分", raw)
    m_met = re.fullmatch(r"(\d+)\s*[mｍ]", raw)
    if m_min:
        minutes = int(m_min.group(1))
        confidence = "high"
    elif m_met:
        meters = int(m_met.group(1))
        confidence = "high"
    elif re.fullmatch(r"\d+", raw):
        n = int(raw)
        if n <= _MINUTES_THRESHOLD:
            minutes = n
        else:
            meters = n
        confidence = "low"
    # それ以外（自由記述）は raw のみ保持、minutes/meters は None

    return {"raw": raw, "minutes": minutes, "meters": meters, "unit_confidence": confidence}


# ── レコード組み立て ───────────────────────────────────────────


def normalize(row: dict[str, str], *, source: str, row_index: int | None = None) -> dict[str, Any]:
    """元CSVの1行を正規化レコードに変換する。

    source: "registered" | "closed"（由来ファイル）
    status / contract は突合段階（match モジュール）で確定・付与する。
    """
    g = row.get
    deal_type, use_type = split_category(g("PROPERTY_CATEGORY"))
    amount = g("AMOUNT/RENT")

    return {
        "id": clean_str(g("PROPERTY_NUMBER_ID") or g("ID")),
        "dataset_year": sources.DATASET_YEAR,
        "source": source,
        "status": None,  # match で確定
        "deal_type": deal_type,
        "use_type": use_type,
        "category_raw": clean_str(g("PROPERTY_CATEGORY")),
        "location": {
            "prefecture": clean_str(g("PREFECTURE")),
            "city": clean_str(g("CITY")),
            "point": None,
        },
        "price_yen": parse_yen(amount) if deal_type == "sale" else None,
        "rent_monthly_yen": parse_yen(amount) if deal_type == "rent" else None,
        "amount_raw": clean_str(amount),
        "building": {
            "construction_year": parse_construction_year(g("DATE_OF_CONSTRUCTION")),
            "construction_date_raw": clean_str(g("DATE_OF_CONSTRUCTION")),
            "structure": _structure(g("CONSTRUCTION")),
            # 登録は LAYOUT、成約は NUMBER_OF_ROOMS
            "layout": clean_str(g("LAYOUT") or g("NUMBER_OF_ROOMS")),
            "building_area_sqm": parse_float(g("OCCUPATION_AREA")),
            "total_units": parse_int(g("TOTAL_NUMBER_OF_UNITS")),
        },
        "land": {
            "land_area_sqm": parse_float(g("SIZE_OF_LOT")),
            "land_measurement_method": clean_str(g("SIZE_OF_LOT_MEASUREMENT_METHOD")),
            "land_category": clean_str(g("LAND_CATEGORY")),
            "land_ownership": clean_str(g("LAND_OWNERSHIP")),
            "city_planning_area": clean_str(g("CITY_PLANNING_AREA")),
            "use_district": clean_str(g("USE_DISTRICT")),
            "floor_area_ratio": parse_float(g("FLOOR_AREA_RATIO")),
            "building_coverage_ratio": parse_float(g("BUILDING_COVERAGE_RATIO")),
            "private_road": clean_str(g("PRIVATE_ROAD")),
            "setback": clean_str(g("SETBACK")),
            "connected_roads": clean_str(g("NUMBER_OF_CONNECTED_ROADS")),
        },
        "access": {
            "train_line": clean_str(g("NEAREST_TRAIN_LINE")),
            "station": clean_str(g("NEAREST_STATION")),
            "station_distance": parse_station_distance(g("DISTANCE_TO_NEAREST_STATION_ON_FOOT")),
        },
        "flags": {
            "farmland": bool(parse_bool_arinashi(g("FARMLAND"))),
            "retail_premises": bool(parse_bool_arinashi(g("RETAIL_PREMISES"))),
            "for_office_use": clean_str(g("FOR_OFFICE_USE")),
            "interior_customizable": clean_str(g("INTERIOR_CUSTOMIZABILITY")),
        },
        "utilities": {
            "water_supply": clean_str(g("WATER_SUPPLY")),
            "gas_supply": clean_str(g("GUS_SUPPLY")),  # 原文の誤記 GUS→gas に統一
            "drainage": clean_str(g("DRAINAGE")),
        },
        "facilities": {
            "bath": clean_str(g("BATH")),
            "bath_note": clean_str(g("BATH_NOTE")),
            "toilet": clean_str(g("TOILET")),
            "toilet_note": clean_str(g("TOILET_NOTE")),
            "parking": clean_str(g("PARKING")),
            "bicycle_parking": clean_str(g("BICYCLE_PARKING")),
            "garden": clean_str(g("GARDEN")),
            "washer_place": clean_str(g("PLACE_OF_WASHER")),
            "stove_heating": clean_str(g("STOVE_HEATING_SYSTEM")),
        },
        "nearby_distances": {
            "elementary_school": clean_str(g("DISTANCE_TO_ELEMENTARY_SCHOOL")),
            "junior_high_school": clean_str(g("DISTANCE_TO_JUNIOR_HIGH_SCHOOL")),
            "supermarket": clean_str(g("DISTANCE_TO_SUPERMARKET")),
            # 原文の誤記 COMBINIENCE→convenience に統一
            "convenience_store": clean_str(g("DISTANCE_TO_COMBINIENCE_STORE")),
            "drug_store": clean_str(g("DISTANCE_TO_DRUG_STORE")),
            "hospital": clean_str(g("DISTANCE_TO_HOSPITAL")),
            "shopping_district": clean_str(g("DISTANCE_TO_SHOPPING_DISTRICT")),
            "playground": clean_str(g("DISTANCE_TO_PLAYGROUND")),
            "bank": clean_str(g("DISTANCE_TO_BANK")),
        },
        "strong_points": clean_str(g("STRONG_POINTS")),
        "tags": None,  # AI分類段階で付与（docs/03）
        "contract": None,  # match で付与
        "provenance": {
            "source_file": "01_tourokubukken.csv" if source == "registered" else "02_seiyakubukken.csv",
            "source_row_index": row_index,
            "dataset_year": sources.DATASET_YEAR,
            "retrieved_date": None,
            "source_url": sources.DATASET_PAGE,
            "license": sources.LICENSE,
        },
    }


def _structure(value: str | None) -> str | None:
    """CONSTRUCTION。"指定なし" は欠損とみなし None。"""
    s = clean_str(value)
    return None if s == "指定なし" else s
