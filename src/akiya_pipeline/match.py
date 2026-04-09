"""登録×成約の突合（union → status 生成・contract 付与）。

設計は docs/04-matching-schema.md。

ルール:
- 物件IDが成約ファイルに存在すれば status="closed"、なければ "registered"。
- 物件属性は登録を正とし、両方にあるIDには成約から contract のみ取り込む。
- 登録に無い成約（成約のみ）は成約行から正規化して追加する。
"""

from __future__ import annotations

import re
from typing import Any, Iterable

from . import normalize as N


def build_contract(seiyaku_row: dict[str, str]) -> dict[str, Any]:
    """成約行から contract オブジェクトを組み立てる（docs/04）。"""
    return {
        "is_closed": True,
        "date": _parse_contract_date(seiyaku_row.get("CONTRACT_INFO_DATE")),
        "date_raw": N.clean_str(seiyaku_row.get("CONTRACT_INFO_DATE")),
        "amount_yen": N.parse_yen(seiyaku_row.get("CONTRACT_INFO_AMOUNT/RENT")),
        "amount_raw": N.clean_str(seiyaku_row.get("CONTRACT_INFO_AMOUNT/RENT")),
    }


def _parse_contract_date(value: str | None) -> str | None:
    """成約日 "MM/DD/YY"（米国式）を ISO 8601 "20YY-MM-DD" に変換。

    パース不能・欠損は None。年は2桁→2000+YY（データセットが2025年度のため妥当）。
    """
    s = N.clean_str(value)
    if s is None:
        return None
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{2})", s)
    if not m:
        return None
    month, day, yy = (int(g) for g in m.groups())
    if not (1 <= month <= 12 and 1 <= day <= 31):
        return None
    return f"{2000 + yy:04d}-{month:02d}-{day:02d}"


def build_dataset(
    registered_rows: Iterable[dict[str, str]],
    closed_rows: Iterable[dict[str, str]],
) -> list[dict[str, Any]]:
    """登録・成約の生行から、統合済みの正規化レコード列を生成する。"""
    closed_rows = list(closed_rows)
    closed_by_id = {cid: row for row in closed_rows if (cid := N.clean_str(row.get("ID")))}

    out: list[dict[str, Any]] = []

    # 1) 登録を主軸に走査。成約に載っていれば closed + contract。
    registered_ids: set[str] = set()
    for i, row in enumerate(registered_rows):
        rec = N.normalize(row, source="registered", row_index=i)
        if rec["id"] is not None:
            registered_ids.add(rec["id"])
        closed = closed_by_id.get(rec["id"])
        if closed is not None:
            rec["status"] = "closed"
            rec["contract"] = build_contract(closed)
        else:
            rec["status"] = "registered"
            rec["contract"] = None
        out.append(rec)

    # 2) 登録に無い成約のみ追加（成約後に登録一覧から消えた物件）。
    for i, row in enumerate(closed_rows):
        cid = N.clean_str(row.get("ID"))
        if cid in registered_ids:
            continue
        rec = N.normalize(row, source="closed", row_index=i)
        rec["status"] = "closed"
        rec["contract"] = build_contract(row)
        out.append(rec)

    return out
