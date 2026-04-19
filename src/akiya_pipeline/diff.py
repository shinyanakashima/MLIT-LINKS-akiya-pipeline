"""年次差分検出（docs/05-diff-management.md）。

前年版と当年版を id 単位で突合し、レコードの変化を分類する:
- added          当年に新規出現したID
- removed         前年にあり当年に消えたID
- status_changed  registered ⇄ closed などの状態遷移
- field_changed   属性（価格・面積・PR文等）が変化
- unchanged       変化なし

カテゴリは相互排他（status_changed を field_changed より優先）。
"""

from __future__ import annotations

from typing import Any

# 比較から除外するキー（年度で必ず変わる/派生物/由来メタ）。
_EXCLUDE_TOP = {"dataset_year", "tags", "provenance", "status"}


def _content(record: dict[str, Any]) -> dict[str, Any]:
    """属性比較の対象（除外キーを落とした内容）。"""
    return {k: v for k, v in record.items() if k not in _EXCLUDE_TOP}


def _changed_fields(prev: dict[str, Any], curr: dict[str, Any]) -> list[str]:
    """内容が変化したトップレベルキー（除外キーを除く）を返す。"""
    pc, cc = _content(prev), _content(curr)
    keys = set(pc) | set(cc)
    return sorted(k for k in keys if pc.get(k) != cc.get(k))


def diff_datasets(
    prev_records: list[dict[str, Any]], curr_records: list[dict[str, Any]]
) -> dict[str, Any]:
    """前年→当年の差分を構造化して返す。"""
    prev = {r["id"]: r for r in prev_records}
    curr = {r["id"]: r for r in curr_records}
    prev_ids, curr_ids = set(prev), set(curr)

    added = sorted(curr_ids - prev_ids)
    removed = sorted(prev_ids - curr_ids)

    status_changed: list[dict[str, Any]] = []
    field_changed: list[dict[str, Any]] = []
    unchanged = 0
    strong_points_changed: list[str] = []  # タグ再分類対象（docs/05）

    for cid in sorted(prev_ids & curr_ids):
        p, c = prev[cid], curr[cid]
        if (p.get("strong_points") or "") != (c.get("strong_points") or ""):
            strong_points_changed.append(cid)
        if p.get("status") != c.get("status"):
            status_changed.append({"id": cid, "from": p.get("status"), "to": c.get("status")})
        elif _content(p) != _content(c):
            field_changed.append({"id": cid, "fields": _changed_fields(p, c)})
        else:
            unchanged += 1

    return {
        "prev_year": prev_records[0]["dataset_year"] if prev_records else None,
        "curr_year": curr_records[0]["dataset_year"] if curr_records else None,
        "summary": {
            "added": len(added),
            "removed": len(removed),
            "status_changed": len(status_changed),
            "field_changed": len(field_changed),
            "unchanged": unchanged,
            "strong_points_changed": len(strong_points_changed),
        },
        "added": added,
        "removed": removed,
        "status_changed": status_changed,
        "field_changed": field_changed,
        "strong_points_changed": strong_points_changed,
    }


def summary_line(diff: dict[str, Any]) -> str:
    """Release ノート等に載せる1行サマリ。"""
    s = diff["summary"]
    return (
        f"added {s['added']} / removed {s['removed']} / "
        f"status_changed {s['status_changed']} / field_changed {s['field_changed']} / "
        f"unchanged {s['unchanged']}"
    )
