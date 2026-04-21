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

# 既定値（reset 用に保持）。年次更新は configure() で上書きできる。
_DEFAULT_YEAR = DATASET_YEAR
_DEFAULT_PAGE = DATASET_PAGE
_URL_OVERRIDES: dict[str, str] = {}

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


def configure(
    *,
    year: int | None = None,
    dataset_page: str | None = None,
    registered_url: str | None = None,
    closed_url: str | None = None,
) -> None:
    """年次更新用の上書き設定。指定された項目だけ差し替える（None は無視）。

    年度ごとに変わる取得URL・年度・出典URLを、コード編集なしに差し替えるための入口。
    列構成が変わった場合は normalize/match の調整が別途必要（docs/05）。
    """
    global DATASET_YEAR, DATASET_PAGE
    if year is not None:
        DATASET_YEAR = int(year)
    if dataset_page:
        DATASET_PAGE = dataset_page
    if registered_url:
        _URL_OVERRIDES["registered"] = registered_url
    if closed_url:
        _URL_OVERRIDES["closed"] = closed_url


def reset() -> None:
    """configure() の上書きを既定値に戻す（主にテスト用）。"""
    global DATASET_YEAR, DATASET_PAGE
    DATASET_YEAR = _DEFAULT_YEAR
    DATASET_PAGE = _DEFAULT_PAGE
    _URL_OVERRIDES.clear()


def effective_url(resource: Resource) -> str:
    """上書きがあればそのURL、なければ既定の resource.url を返す。"""
    return _URL_OVERRIDES.get(resource.key, resource.url)


def download(resource: Resource, dest_dir: Path, *, overwrite: bool = False) -> Path:
    """リソースを dest_dir に保存し、保存先パスを返す。"""
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / resource.filename
    if dest.exists() and not overwrite:
        return dest
    with urllib.request.urlopen(effective_url(resource), timeout=120) as resp:  # noqa: S310
        dest.write_bytes(resp.read())
    return dest
