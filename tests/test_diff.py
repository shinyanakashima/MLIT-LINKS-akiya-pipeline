"""diff のテスト: 年次差分の分類とタグ引き継ぎ。"""

import unittest

from akiya_pipeline import diff as D
from akiya_pipeline import classify as C


def rec(id_, *, year=2025, status="registered", price=None, sp=None, tags=None):
    return {
        "id": id_, "dataset_year": year, "status": status,
        "price_yen": price, "strong_points": sp, "tags": tags,
        "provenance": {"source_row_index": 0},
    }


class DiffDatasetsTest(unittest.TestCase):
    def test_categories(self):
        prev = [rec("A", price=100), rec("B", price=200), rec("C", status="registered"), rec("D")]
        curr = [
            rec("A", year=2026, price=100),                 # unchanged（年度除外）
            rec("B", year=2026, price=250),                 # field_changed（価格）
            rec("C", year=2026, status="closed"),           # status_changed
            rec("E", year=2026),                            # added
            # D は無し → removed
        ]
        r = D.diff_datasets(prev, curr)
        self.assertEqual(r["summary"],
                         {"added": 1, "removed": 1, "status_changed": 1,
                          "field_changed": 1, "unchanged": 1, "strong_points_changed": 0})
        self.assertEqual(r["added"], ["E"])
        self.assertEqual(r["removed"], ["D"])
        self.assertEqual(r["status_changed"], [{"id": "C", "from": "registered", "to": "closed"}])
        self.assertEqual(r["field_changed"], [{"id": "B", "fields": ["price_yen"]}])

    def test_status_change_takes_precedence_over_field(self):
        prev = [rec("A", status="registered", price=100)]
        curr = [rec("A", year=2026, status="closed", price=999)]
        r = D.diff_datasets(prev, curr)
        self.assertEqual(r["summary"]["status_changed"], 1)
        self.assertEqual(r["summary"]["field_changed"], 0)

    def test_strong_points_changed_tracked(self):
        prev = [rec("A", sp="庭あり")]
        curr = [rec("A", year=2026, sp="庭あり・改修済")]
        r = D.diff_datasets(prev, curr)
        self.assertEqual(r["strong_points_changed"], ["A"])

    def test_summary_line(self):
        prev = [rec("A")]
        curr = [rec("B", year=2026)]
        self.assertIn("added 1", D.summary_line(D.diff_datasets(prev, curr)))


class ReusePriorTagsTest(unittest.TestCase):
    def test_reuse_when_strong_points_identical(self):
        prev = [rec("A", sp="古民家", tags={"labels": {"kominka": True}})]
        targets = [rec("A", year=2026, sp="古民家"), rec("B", year=2026, sp="新規")]
        reused, todo = C.reuse_prior_tags(targets, prev)
        self.assertIn("A", reused)
        self.assertEqual([t["id"] for t in todo], ["B"])

    def test_no_reuse_when_strong_points_changed(self):
        prev = [rec("A", sp="古民家", tags={"labels": {"kominka": True}})]
        targets = [rec("A", year=2026, sp="古民家・改修済")]
        reused, todo = C.reuse_prior_tags(targets, prev)
        self.assertEqual(reused, {})
        self.assertEqual([t["id"] for t in todo], ["A"])

    def test_no_reuse_when_prev_untagged(self):
        prev = [rec("A", sp="古民家", tags=None)]
        targets = [rec("A", year=2026, sp="古民家")]
        reused, todo = C.reuse_prior_tags(targets, prev)
        self.assertEqual(reused, {})
        self.assertEqual([t["id"] for t in todo], ["A"])


if __name__ == "__main__":
    unittest.main()
