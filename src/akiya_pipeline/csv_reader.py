"""BOM安全なCSV読み込み。

元データの既知の課題（docs/01）に対応:
- UTF-8 BOM付き        → utf-8-sig で除去
- フィールド内改行      → csv モジュール（RFC 4180 準拠）でクオート内改行を正しく処理
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterator


def read_rows(path: str | Path) -> Iterator[dict[str, str]]:
    """CSVを1行ずつ dict で返す。BOM・フィールド内改行に対応。

    値は元の文字列のまま（正規化は normalize モジュールが担当）。
    newline="" は csv モジュールの要件（クオート内改行の保全）。
    """
    with open(path, encoding="utf-8-sig", newline="") as f:
        yield from csv.DictReader(f)


def read_all(path: str | Path) -> list[dict[str, str]]:
    """全行をリストで読み込む。"""
    return list(read_rows(path))
