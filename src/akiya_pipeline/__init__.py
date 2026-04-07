"""国交省 Project LINKS 空き家バンク オープンデータの正規化パイプライン。

設計は docs/ を参照:
- 02-normalization-schema.md  正規化スキーマ
- 04-matching-schema.md        登録×成約 突合
"""

__version__ = "0.1.0"

# 正規化スキーマの構造版（docs/05 のバージョニング方針）。
SCHEMA_VERSION = "1.0"
