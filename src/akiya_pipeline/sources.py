"""元データソース（CKAN リソース）の定義と取得。

出典: 国土交通省 Project LINKS「空き家バンク（2025年度）」/ CC-BY 4.0
https://www.geospatial.jp/ckan/dataset/links-akiyabank-2025
"""

from __future__ import annotations

import urllib.request
from dataclasses import dataclass
from pathlib import Path

DATASET_YEAR = 2025
DATASET_PAGE = "https://www.geospatial.jp/ckan/dataset/links-akiyabank-2025"
LICENSE = "CC-BY-4.0"

_BASE = (
    "https://www.geospatial.jp/ckan/dataset/"
    "da1b7c8d-164f-4fdd-977b-3c49c7396c08/resource"
)


@dataclass(frozen=True)
class Resource:
    """配布元の1リソース（CSVファイル）。"""

    key: str  # "registered" | "closed"
    filename: str
    resource_id: str

    @property
    def url(self) -> str:
        return f"{_BASE}/{self.resource_id}/download/{self.filename}"


REGISTERED = Resource(
    key="registered",
    filename="01_tourokubukken.csv",
    resource_id="d1cbba16-4972-4bab-bcf5-e275b26a18de",
)
CLOSED = Resource(
    key="closed",
    filename="02_seiyakubukken.csv",
    resource_id="1dcf6cac-13bc-4505-b7dd-20dba3258a1d",
)
RESOURCES = (REGISTERED, CLOSED)


def download(resource: Resource, dest_dir: Path, *, overwrite: bool = False) -> Path:
    """リソースを dest_dir に保存し、保存先パスを返す。"""
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / resource.filename
    if dest.exists() and not overwrite:
        return dest
    with urllib.request.urlopen(resource.url, timeout=120) as resp:  # noqa: S310
        dest.write_bytes(resp.read())
    return dest
