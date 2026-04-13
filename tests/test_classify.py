"""classify のテスト: スキーマ生成・整合・マッピング・両プロバイダのバッチ流れ（モック）。"""

import json
import types
import unittest
from pathlib import Path

from akiya_pipeline import classify as C

TAGS_JSON = Path(__file__).resolve().parent.parent / "schema" / "tags.json"


class TaxonomyTest(unittest.TestCase):
    def test_axes_match_tags_json(self):
        # コードの AXES と schema/tags.json の語彙がドリフトしないこと。
        spec = json.loads(TAGS_JSON.read_text(encoding="utf-8"))
        self.assertEqual([a["key"] for a in C.AXES], [a["key"] for a in spec["axes"]])
        self.assertEqual(C.TAGS_SCHEMA_VERSION, spec["schema_version"])

    def test_anthropic_tool_schema(self):
        schema = C.build_tool_schema()
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(schema["properties"]["renovation_needed"]["enum"][0], "required")
        self.assertEqual(schema["properties"]["kominka"]["type"], "boolean")
        self.assertIn("confidence", schema["required"])
        self.assertNotIn("evidence", schema["required"])  # 任意

    def test_openai_schema_strict_all_required(self):
        schema = C.build_openai_schema()
        self.assertFalse(schema["additionalProperties"])
        # strict: 全プロパティが required、evidence は含めない
        self.assertEqual(set(schema["required"]), set(schema["properties"]))
        self.assertNotIn("evidence", schema["properties"])

    def test_system_prompt_lists_axes(self):
        p = C.build_system_prompt()
        self.assertIn("renovation_needed", p)
        self.assertIn("kominka", p)


class MappingTest(unittest.TestCase):
    def test_tags_from_labels(self):
        data = {ax["key"]: (False if ax["type"] == "bool" else "unknown") for ax in C.AXES}
        data.update({"kominka": True, "confidence": "high", "evidence": {"kominka": "古民家"}})
        tags = C.tags_from_labels(data, model="m")
        self.assertEqual(tags["schema_version"], C.TAGS_SCHEMA_VERSION)
        self.assertTrue(tags["labels"]["kominka"])
        self.assertEqual(tags["labels"]["renovation_needed"], "unknown")
        self.assertEqual(tags["evidence"], {"kominka": "古民家"})

    def test_classifiable_filters_empty(self):
        recs = [{"id": "1", "strong_points": "庭付き"}, {"id": "2", "strong_points": None},
                {"id": "3", "strong_points": "  "}]
        self.assertEqual([r["id"] for r in C.classifiable(recs)], ["1"])

    def test_apply_tags(self):
        recs = [{"id": "1", "tags": None}, {"id": "2", "tags": None}]
        self.assertEqual(C.apply_tags(recs, {"1": {"labels": {}}}), 1)
        self.assertIsNotNone(recs[0]["tags"])
        self.assertIsNone(recs[1]["tags"])

    def test_make_classifier_default_models(self):
        self.assertEqual(C.make_classifier("anthropic", client=object()).model, "claude-sonnet-4-6")
        self.assertEqual(C.make_classifier("openai", client=object()).model, "gpt-4.1-mini")
        with self.assertRaises(ValueError):
            C.make_classifier("bogus", client=object())


def _labels(**override):
    d = {ax["key"]: (False if ax["type"] == "bool" else "unknown") for ax in C.AXES}
    d["confidence"] = "high"
    d.update(override)
    return d


# ── Anthropic モック ───────────────────────────────────────────


class _AnthBatches:
    def __init__(self, results):
        self._results = results

    def create(self, requests):
        return types.SimpleNamespace(id="b")

    def retrieve(self, _id):
        return types.SimpleNamespace(processing_status="ended")

    def results(self, _id):
        return iter(self._results)


class _AnthClient:
    def __init__(self, results):
        self.messages = types.SimpleNamespace(batches=_AnthBatches(results))


class AnthropicFlowTest(unittest.TestCase):
    def test_classify(self):
        block = types.SimpleNamespace(type="tool_use", name=C.TOOL_NAME,
                                      input=_labels(farmland_attached=True))
        results = [
            types.SimpleNamespace(custom_id="1", result=types.SimpleNamespace(
                type="succeeded", message=types.SimpleNamespace(content=[block]))),
            types.SimpleNamespace(custom_id="2", result=types.SimpleNamespace(
                type="errored", message=None)),
        ]
        clf = C.AnthropicClassifier(client=_AnthClient(results))
        recs = [{"id": "1", "strong_points": "家庭菜園付き", "category_raw": "売買居住用"},
                {"id": "2", "strong_points": "古民家"}]
        out = clf.classify(recs, poll_interval=0)
        self.assertTrue(out["1"]["labels"]["farmland_attached"])
        self.assertNotIn("2", out)


# ── OpenAI モック ──────────────────────────────────────────────


class _OAIFiles:
    def __init__(self, output_text):
        self._text = output_text

    def create(self, file, purpose):
        return types.SimpleNamespace(id="file_in")

    def content(self, _id):
        return types.SimpleNamespace(text=self._text)


class _OAIBatches:
    def create(self, input_file_id, endpoint, completion_window):
        return types.SimpleNamespace(id="batch")

    def retrieve(self, _id):
        return types.SimpleNamespace(status="completed", output_file_id="file_out")


class _OAIClient:
    def __init__(self, output_text):
        self.files = _OAIFiles(output_text)
        self.batches = _OAIBatches()


class OpenAIFlowTest(unittest.TestCase):
    def test_classify(self):
        line = json.dumps({
            "custom_id": "1",
            "response": {"status_code": 200,
                         "body": {"choices": [{"message": {"content": json.dumps(_labels(kominka=True))}}]}},
        })
        clf = C.OpenAIClassifier(client=_OAIClient(line + "\n"))
        recs = [{"id": "1", "strong_points": "築100年の古民家", "category_raw": "売買居住用"}]
        out = clf.classify(recs, poll_interval=0)
        self.assertTrue(out["1"]["labels"]["kominka"])
        self.assertEqual(out["1"]["model"], "gpt-4.1-mini")

    def test_empty_when_no_targets(self):
        clf = C.OpenAIClassifier(client=_OAIClient(""))
        self.assertEqual(clf.classify([{"id": "1", "strong_points": None}]), {})


if __name__ == "__main__":
    unittest.main()
