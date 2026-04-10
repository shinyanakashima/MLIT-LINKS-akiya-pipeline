"""実データ統合テスト。

data/raw に元CSVがある場合のみ実行（gitignore 対象のため CI では自動スキップ）。
docs/04 の整合チェックを件数で検証する。
"""

import unittest
from pathlib import Path

from akiya_pipeline import pipeline

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
REG = RAW / "01_tourokubukken.csv"
CLO = RAW / "02_seiyakubukken.csv"


@unittest.skipUnless(REG.exists() and CLO.exists(), "data/raw に元CSVが無いためスキップ")
class RealDataTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = pipeline.build(REG, CLO)
        cls.summary = pipeline.summarize(cls.records)

    def test_counts_match_design(self):
        # docs/01 §3 / docs/04 の実測値
        self.assertEqual(self.summary["total"], 8678)
        self.assertEqual(self.summary["registered"], 7475)
        self.assertEqual(self.summary["closed"], 1203)
        self.assertEqual(self.summary["closed_overlap"], 271)
        self.assertEqual(self.summary["closed_only"], 932)

    def test_ids_unique(self):
        ids = [r["id"] for r in self.records]
        self.assertEqual(len(ids), len(set(ids)))

    def test_closed_have_contract_registered_dont(self):
        for r in self.records:
            if r["status"] == "closed":
                self.assertIsNotNone(r["contract"])
                self.assertTrue(r["contract"]["is_closed"])
            else:
                self.assertIsNone(r["contract"])

    def test_amount_routing_consistent(self):
        # sale は price のみ、rent は rent のみ（両方非nullは無い）
        for r in self.records:
            if r["deal_type"] == "sale":
                self.assertIsNone(r["rent_monthly_yen"])
            elif r["deal_type"] == "rent":
                self.assertIsNone(r["price_yen"])


if __name__ == "__main__":
    unittest.main()
