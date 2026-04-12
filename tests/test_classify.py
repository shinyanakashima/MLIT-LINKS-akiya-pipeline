"""classify のテスト: スキーマ生成・整合・マッピング・バッチ流れ（モック）。"""

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
        json_keys = [a["key"] for a in spec["axes"]]
        code_keys = [a["key"] for a in C.AXES]
        self.assertEqual(code_keys, json_keys)
        self.assertEqual(C.TAGS_SCHEMA_VERSION, spec["schema_version"])

    def test_tool_schema_required_and_types(self):
        schema = C.build_tool_schema()
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(schema["properties"]["renovation_needed"]["enum"][0], "required")
        self.assertEqual(schema["properties"]["kominka"]["type"], "boolean")
        self.assertIn("confidence", schema["required"])
        self.assertNotIn("evidence", schema["required"])  # 任意

    def test_system_prompt_lists_axes(self):
        p = C.build_system_prompt()
        self.assertIn("renovation_needed", p)
        self.assertIn("record_tags", p)


class MappingTest(unittest.TestCase):
    def test_tags_from_tool_input(self):
        tool_input = {ax["key"]: (False if ax["type"] == "bool" else "unknown") for ax in C.AXES}
        tool_input.update({"kominka": True, "confidence": "high", "evidence": {"kominka": "古民家"}})
        tags = C.tags_from_tool_input(tool_input, model="claude-sonnet-4-6")
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
        n = C.apply_tags(recs, {"1": {"labels": {}}})
        self.assertEqual(n, 1)
        self.assertIsNotNone(recs[0]["tags"])
        self.assertIsNone(recs[1]["tags"])


# ── バッチ流れのモック ─────────────────────────────────────────


def _msg_with_tool(tool_input):
    block = types.SimpleNamespace(type="tool_use", name=C.TOOL_NAME, input=tool_input)
    return types.SimpleNamespace(content=[block])


class _FakeBatches:
    def __init__(self, results):
        self._results = results

    def create(self, requests):
        self._n = len(requests)
        return types.SimpleNamespace(id="batch_test")

    def retrieve(self, batch_id):
        return types.SimpleNamespace(processing_status="ended")

    def results(self, batch_id):
        return iter(self._results)


class _FakeClient:
    def __init__(self, results):
        self.messages = types.SimpleNamespace(batches=_FakeBatches(results))


class BatchFlowTest(unittest.TestCase):
    def test_classify_returns_tags_by_id(self):
        ti = {ax["key"]: (False if ax["type"] == "bool" else "unknown") for ax in C.AXES}
        ti.update({"farmland_attached": True, "confidence": "high"})
        results = [
            types.SimpleNamespace(
                custom_id="1",
                result=types.SimpleNamespace(type="succeeded", message=_msg_with_tool(ti)),
            ),
            types.SimpleNamespace(  # 失敗エントリは無視される
                custom_id="2", result=types.SimpleNamespace(type="errored", message=None)
            ),
        ]
        clf = C.Classifier(client=_FakeClient(results))
        recs = [{"id": "1", "strong_points": "家庭菜園付き", "category_raw": "売買居住用"},
                {"id": "2", "strong_points": "古民家"}]
        out = clf.classify(recs, poll_interval=0)
        self.assertIn("1", out)
        self.assertTrue(out["1"]["labels"]["farmland_attached"])
        self.assertNotIn("2", out)

    def test_classify_empty_when_no_targets(self):
        clf = C.Classifier(client=_FakeClient([]))
        self.assertEqual(clf.classify([{"id": "1", "strong_points": None}]), {})


if __name__ == "__main__":
    unittest.main()
