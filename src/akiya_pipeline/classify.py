"""STRONG_POINTS のAI分類（プロバイダ非依存）。

設計は docs/03-tag-taxonomy.md。

- 分類はビルド時に一括実行し、結果（tags）を静的JSONに焼き込む（実行時API非依存）。
- 構造化出力を強制してパース失敗を防ぐ:
    Anthropic … tool use（record_tags）
    OpenAI    … Structured Outputs（response_format json_schema, strict=true）
- バッチで一括処理:
    Anthropic … Message Batches API
    OpenAI    … Batch API（/v1/chat/completions, 24h window）

実行には対応するキー（ANTHROPIC_API_KEY / OPENAI_API_KEY）と SDK（extras: classify）が必要。
"""

from __future__ import annotations

import io
import json
import time
from typing import Any, Iterable

# 分類タグ語彙の版（dataset_year / 正規化スキーマ版とは独立。docs/05）。
TAGS_SCHEMA_VERSION = "1.0"

DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-4-6",
    "openai": "gpt-4.1-mini",
}

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


# ── 出力スキーマ（共通の軸定義から各プロバイダ向けに生成） ──────


def _label_properties() -> dict[str, Any]:
    props: dict[str, Any] = {}
    for ax in AXES:
        if ax["type"] == "enum":
            props[ax["key"]] = {"type": "string", "enum": ax["values"], "description": ax["desc"]}
        else:
            props[ax["key"]] = {"type": "boolean", "description": ax["desc"]}
    props["confidence"] = {"type": "string", "enum": ["high", "medium", "low"]}
    return props


def build_tool_schema() -> dict[str, Any]:
    """Anthropic tool use 用 input_schema（evidence は任意）。"""
    props = _label_properties()
    props["evidence"] = {
        "type": "object",
        "additionalProperties": {"type": "string"},
        "description": "任意。true にした軸の根拠語句（短く）。",
    }
    required = [ax["key"] for ax in AXES] + ["confidence"]
    return {"type": "object", "properties": props, "required": required, "additionalProperties": False}


def build_openai_schema() -> dict[str, Any]:
    """OpenAI Structured Outputs 用 schema（strict: 全プロパティ required）。"""
    props = _label_properties()
    return {
        "type": "object",
        "properties": props,
        "required": list(props),
        "additionalProperties": False,
    }


def build_system_prompt() -> str:
    """タクソノミ定義＋出力規約（prompt caching の対象になる固定部）。"""
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
        "4. 出力は指定のスキーマに厳密に従い、説明文は出さない。",
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


def tags_from_labels(data: dict[str, Any], *, model: str) -> dict[str, Any]:
    """モデル出力（フラットな labels）を tags オブジェクトに整形する。"""
    labels = {ax["key"]: data.get(ax["key"]) for ax in AXES}
    tags = {
        "schema_version": TAGS_SCHEMA_VERSION,
        "model": model,
        "labels": labels,
        "confidence": data.get("confidence"),
    }
    if data.get("evidence"):
        tags["evidence"] = data["evidence"]
    return tags


def apply_tags(records: list[dict[str, Any]], tags_by_id: dict[str, dict[str, Any]]) -> int:
    """records の各要素に tags を反映し、付与件数を返す。"""
    n = 0
    for r in records:
        t = tags_by_id.get(r["id"])
        if t is not None:
            r["tags"] = t
            n += 1
    return n


def request_preview(record: dict[str, Any], *, provider: str, model: str) -> dict[str, Any]:
    """dry-run 表示用のリクエスト概要（API送信はしない）。"""
    return {
        "provider": provider,
        "model": model,
        "system": build_system_prompt(),
        "user": _user_text(record),
    }


# ── プロバイダ実装 ─────────────────────────────────────────────


class _BaseClassifier:
    provider = ""

    def __init__(self, client: Any = None, *, model: str | None = None):
        self.model = model or DEFAULT_MODELS[self.provider]
        self._client = client

    def classify(
        self, records: list[dict[str, Any]], *, poll_interval: float = 30.0
    ) -> dict[str, dict[str, Any]]:
        raise NotImplementedError


class AnthropicClassifier(_BaseClassifier):
    """Anthropic Message Batches + tool use。"""

    provider = "anthropic"

    @property
    def client(self) -> Any:
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic()
        return self._client

    def _params(self, record: dict[str, Any]) -> dict[str, Any]:
        return {
            "model": self.model,
            "max_tokens": 512,
            "temperature": 0,
            "system": [
                {"type": "text", "text": build_system_prompt(), "cache_control": {"type": "ephemeral"}}
            ],
            "tools": [
                {"name": TOOL_NAME, "description": "PR文の分類タグを記録する",
                 "input_schema": build_tool_schema()}
            ],
            "tool_choice": {"type": "tool", "name": TOOL_NAME},
            "messages": [{"role": "user", "content": _user_text(record)}],
        }

    def classify(self, records, *, poll_interval=30.0):
        targets = classifiable(records)
        if not targets:
            return {}
        requests = [{"custom_id": r["id"], "params": self._params(r)} for r in targets]
        batch = self.client.messages.batches.create(requests=requests)
        while self.client.messages.batches.retrieve(batch.id).processing_status != "ended":
            time.sleep(poll_interval)

        out: dict[str, dict[str, Any]] = {}
        for entry in self.client.messages.batches.results(batch.id):
            if entry.result.type != "succeeded":
                continue
            for block in getattr(entry.result.message, "content", []) or []:
                if getattr(block, "type", None) == "tool_use" and getattr(block, "name", None) == TOOL_NAME:
                    out[entry.custom_id] = tags_from_labels(dict(block.input), model=self.model)
                    break
        return out


class OpenAIClassifier(_BaseClassifier):
    """OpenAI Batch API + Structured Outputs。"""

    provider = "openai"

    @property
    def client(self) -> Any:
        if self._client is None:
            import openai

            self._client = openai.OpenAI()
        return self._client

    def _body(self, record: dict[str, Any]) -> dict[str, Any]:
        return {
            "model": self.model,
            "max_tokens": 512,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": build_system_prompt()},
                {"role": "user", "content": _user_text(record)},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": TOOL_NAME, "strict": True, "schema": build_openai_schema()},
            },
        }

    def classify(self, records, *, poll_interval=30.0):
        targets = classifiable(records)
        if not targets:
            return {}
        # Batch 入力 JSONL を組み立ててアップロード
        lines = [
            json.dumps(
                {"custom_id": r["id"], "method": "POST", "url": "/v1/chat/completions",
                 "body": self._body(r)},
                ensure_ascii=False,
            )
            for r in targets
        ]
        buf = io.BytesIO(("\n".join(lines) + "\n").encode("utf-8"))
        buf.name = "batch_input.jsonl"
        infile = self.client.files.create(file=buf, purpose="batch")
        batch = self.client.batches.create(
            input_file_id=infile.id, endpoint="/v1/chat/completions", completion_window="24h"
        )
        while True:
            b = self.client.batches.retrieve(batch.id)
            if b.status == "completed":
                break
            if b.status in ("failed", "expired", "cancelled"):
                raise RuntimeError(f"OpenAI batch {b.status}: {batch.id}")
            time.sleep(poll_interval)

        content = self.client.files.content(b.output_file_id)
        text = content.text if hasattr(content, "text") else content.read().decode("utf-8")

        out: dict[str, dict[str, Any]] = {}
        for line in text.splitlines():
            if not line.strip():
                continue
            obj = json.loads(line)
            resp = obj.get("response") or {}
            if resp.get("status_code") not in (200, None):
                continue
            try:
                msg = resp["body"]["choices"][0]["message"]["content"]
                data = json.loads(msg)
            except (KeyError, IndexError, json.JSONDecodeError, TypeError):
                continue
            out[obj["custom_id"]] = tags_from_labels(data, model=self.model)
        return out


_PROVIDERS = {"anthropic": AnthropicClassifier, "openai": OpenAIClassifier}


def make_classifier(provider: str, *, model: str | None = None, client: Any = None) -> _BaseClassifier:
    """プロバイダ名から分類クライアントを生成する。"""
    if provider not in _PROVIDERS:
        raise ValueError(f"unknown provider: {provider}（{list(_PROVIDERS)} から選択）")
    return _PROVIDERS[provider](client=client, model=model)
