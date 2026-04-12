"""STRONG_POINTS のAI分類（Claude Sonnet / Message Batches）。

設計は docs/03-tag-taxonomy.md。

- 分類はビルド時に一括実行し、結果（tags）を静的JSONに焼き込む（実行時API非依存）。
- 構造化出力は tool use（record_tags）で JSON Schema を強制し、パース失敗を防ぐ。
- 長いタクソノミ定義は prompt caching で固定し、物件ごとの差分は本文のみ。

実行には ANTHROPIC_API_KEY と `anthropic` パッケージ（extras: classify）が必要。
"""

from __future__ import annotations

import time
from typing import Any, Iterable

# 分類タグ語彙の版（dataset_year / 正規化スキーマ版とは独立。docs/05）。
TAGS_SCHEMA_VERSION = "1.0"
DEFAULT_MODEL = "claude-sonnet-4-6"

# ── タクソノミ（schema/tags.json と一致させる。test_classify が整合を検証） ──
# type: "bool" | "enum"
AXES: list[dict[str, Any]] = [
    {"key": "renovation_needed", "type": "enum",
     "values": ["required", "done", "as_is", "unknown"],
     "desc": "改修要否。required=要改修, done=改修済, as_is=現状渡し, unknown=記述なし"},
    {"key": "migration_friendly", "type": "bool", "desc": "移住・田舎暮らし・定住促進を訴求"},
    {"key": "business_usable", "type": "bool", "desc": "店舗/事務所/民泊等の事業転用を訴求"},
    {"key": "subsidy_mentioned", "type": "bool", "desc": "補助金・助成・支援制度への言及"},
    {"key": "vr_tour", "type": "bool", "desc": "VR内覧・オンライン内見・動画内覧への言及"},
    {"key": "farmland_attached", "type": "bool", "desc": "農地・畑・田・家庭菜園が付帯"},
    {"key": "kominka", "type": "bool", "desc": "古民家・伝統的家屋・茅葺等"},
    {"key": "view_nature", "type": "bool", "desc": "眺望・海/山ビュー・自然環境の良さを訴求"},
    {"key": "near_school", "type": "bool", "desc": "学校・保育園・通学利便を訴求"},
    {"key": "near_shopping", "type": "bool", "desc": "スーパー・商店街・買物利便を訴求"},
    {"key": "parking_emphasized", "type": "bool", "desc": "駐車場（複数台可等）を積極訴求"},
    {"key": "move_in_ready", "type": "bool", "desc": "即入居可・家具家電付き等"},
]

TOOL_NAME = "record_tags"


def build_tool_schema() -> dict[str, Any]:
    """record_tags ツールの input_schema（出力を強制するJSON Schema）。"""
    props: dict[str, Any] = {}
    for ax in AXES:
        if ax["type"] == "enum":
            props[ax["key"]] = {"type": "string", "enum": ax["values"], "description": ax["desc"]}
        else:
            props[ax["key"]] = {"type": "boolean", "description": ax["desc"]}
    props["confidence"] = {"type": "string", "enum": ["high", "medium", "low"]}
    props["evidence"] = {
        "type": "object",
        "additionalProperties": {"type": "string"},
        "description": "任意。true にした軸の根拠語句（短く）。",
    }
    required = [ax["key"] for ax in AXES] + ["confidence"]
    return {"type": "object", "properties": props, "required": required, "additionalProperties": False}


def build_system_prompt() -> str:
    """タクソノミ定義＋出力規約（prompt caching 対象の固定部）。"""
    lines = [
        "あなたは日本の空き家バンク物件のPR文（STRONG_POINTS）を分類する専門家です。",
        "各軸について、PR文中に明示的な根拠がある場合のみタグを付与してください。",
        "",
        "# 分類軸",
    ]
    for ax in AXES:
        if ax["type"] == "enum":
            lines.append(f"- {ax['key']} (enum: {', '.join(ax['values'])}): {ax['desc']}")
        else:
            lines.append(f"- {ax['key']} (true/false): {ax['desc']}")
    lines += [
        "",
        "# 出力規約",
        "1. PR文中に明示的な根拠がある場合のみ true。推測・一般論で true にしない。",
        "2. bool 軸は常に true/false を返す（言及なし=false。null は使わない）。",
        "3. enum 軸は根拠がなければ unknown。",
        "4. evidence は任意。true にした軸の根拠語句を短く。",
        f"5. 必ず {TOOL_NAME} ツールを使って出力する。説明文は出さない。",
    ]
    return "\n".join(lines)


def _user_text(record: dict[str, Any]) -> str:
    return (
        f"物件カテゴリ: {record.get('category_raw') or '不明'}\n"
        "PR文:\n\"\"\"\n"
        f"{record.get('strong_points') or ''}\n\"\"\""
    )


def classifiable(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """STRONG_POINTS が非空のレコードのみ（分類対象）。"""
    return [r for r in records if (r.get("strong_points") or "").strip()]


def build_request_params(record: dict[str, Any], *, model: str) -> dict[str, Any]:
    """1物件分の Messages パラメータ（バッチ・単発で共通利用）。"""
    return {
        "model": model,
        "max_tokens": 512,
        "temperature": 0,
        "system": [
            {"type": "text", "text": build_system_prompt(), "cache_control": {"type": "ephemeral"}}
        ],
        "tools": [
            {"name": TOOL_NAME, "description": "PR文の分類タグを記録する", "input_schema": build_tool_schema()}
        ],
        "tool_choice": {"type": "tool", "name": TOOL_NAME},
        "messages": [{"role": "user", "content": _user_text(record)}],
    }


def tags_from_tool_input(tool_input: dict[str, Any], *, model: str) -> dict[str, Any]:
    """ツール出力（フラットな labels）を tags オブジェクトに整形する。"""
    labels = {ax["key"]: tool_input.get(ax["key"]) for ax in AXES}
    tags = {
        "schema_version": TAGS_SCHEMA_VERSION,
        "model": model,
        "labels": labels,
        "confidence": tool_input.get("confidence"),
    }
    if tool_input.get("evidence"):
        tags["evidence"] = tool_input["evidence"]
    return tags


def _extract_tool_input(message: Any) -> dict[str, Any] | None:
    """Messages レスポンスから record_tags の入力を取り出す。"""
    for block in getattr(message, "content", []) or []:
        if getattr(block, "type", None) == "tool_use" and getattr(block, "name", None) == TOOL_NAME:
            return dict(block.input)
    return None


class Classifier:
    """Message Batches を使った一括分類クライアント。

    client を渡さない場合は anthropic.Anthropic() を遅延生成（環境変数のキーを使用）。
    """

    def __init__(self, client: Any = None, *, model: str = DEFAULT_MODEL):
        self.model = model
        self._client = client

    @property
    def client(self) -> Any:
        if self._client is None:
            import anthropic  # 遅延import（extras: classify）

            self._client = anthropic.Anthropic()
        return self._client

    def classify(
        self, records: list[dict[str, Any]], *, poll_interval: float = 30.0
    ) -> dict[str, dict[str, Any]]:
        """対象レコードを分類し {id: tags} を返す（バッチ送信→完了待ち→取得）。"""
        targets = classifiable(records)
        if not targets:
            return {}

        requests = [
            {"custom_id": r["id"], "params": build_request_params(r, model=self.model)}
            for r in targets
        ]
        batch = self.client.messages.batches.create(requests=requests)
        batch_id = batch.id

        while True:
            status = self.client.messages.batches.retrieve(batch_id)
            if status.processing_status == "ended":
                break
            time.sleep(poll_interval)

        out: dict[str, dict[str, Any]] = {}
        for entry in self.client.messages.batches.results(batch_id):
            if entry.result.type != "succeeded":
                continue
            tool_input = _extract_tool_input(entry.result.message)
            if tool_input is not None:
                out[entry.custom_id] = tags_from_tool_input(tool_input, model=self.model)
        return out


def apply_tags(records: list[dict[str, Any]], tags_by_id: dict[str, dict[str, Any]]) -> int:
    """records の各要素に tags を反映し、付与件数を返す。"""
    n = 0
    for r in records:
        t = tags_by_id.get(r["id"])
        if t is not None:
            r["tags"] = t
            n += 1
    return n
