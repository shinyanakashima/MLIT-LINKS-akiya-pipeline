"""パイプライン統合: 取得 → 正規化 → 突合 → JSON出力。

AI分類（docs/03）は本体が固まった次フェーズで pipeline に差し込む想定。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import SCHEMA_VERSION, sources
from . import csv_reader, match


def build(registered_csv: str | Path, closed_csv: str | Path) -> list[dict[str, Any]]:
    """2つのCSVから統合済み正規化レコード列を生成する。"""
    registered = csv_reader.read_all(registered_csv)
    closed = csv_reader.read_all(closed_csv)
    return match.build_dataset(registered, closed)


def summarize(records: list[dict[str, Any]]) -> dict[str, int]:
    """件数サマリ（検証・manifest 用）。"""
    closed = sum(1 for r in records if r["status"] == "closed")
    closed_from_registered = sum(
        1 for r in records if r["status"] == "closed" and r["source"] == "registered"
    )
    return {
        "total": len(records),
        "registered": sum(1 for r in records if r["status"] == "registered"),
        "closed": closed,
        "closed_overlap": closed_from_registered,  # 登録∩成約
        "closed_only": closed - closed_from_registered,  # 成約のみ
        "tagged": sum(1 for r in records if r.get("tags") is not None),
    }


def write_json(records: list[dict[str, Any]], path: str | Path) -> None:
    """JSON配列として書き出す（UTF-8・BOMなし・LF）。"""
    Path(path).write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def write_jsonl(records: list[dict[str, Any]], path: str | Path) -> None:
    """JSON Lines として書き出す（ストリーム取込向け）。"""
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def manifest(records: list[dict[str, Any]]) -> dict[str, Any]:
    """配布同梱用メタ（docs/05）。チェックサム等は配布段階で付加する。"""
    return {
        "dataset_year": sources.DATASET_YEAR,
        "schema_version": SCHEMA_VERSION,
        "license": sources.LICENSE,
        "source_url": sources.DATASET_PAGE,
        "record_counts": summarize(records),
    }
