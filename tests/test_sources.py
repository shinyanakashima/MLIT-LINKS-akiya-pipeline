"""sources の年次更新上書き（configure / effective_url）とその波及。"""

import unittest

from akiya_pipeline import sources, normalize as N


class ConfigureTest(unittest.TestCase):
    def tearDown(self):
        sources.reset()  # グローバル上書きを毎回戻す

    def test_url_override(self):
        self.assertEqual(sources.effective_url(sources.REGISTERED), sources.REGISTERED.url)
        sources.configure(registered_url="https://example.test/reg.csv")
        self.assertEqual(sources.effective_url(sources.REGISTERED), "https://example.test/reg.csv")
        # closed は未指定なので既定のまま
        self.assertEqual(sources.effective_url(sources.CLOSED), sources.CLOSED.url)

    def test_year_and_page_flow_into_records(self):
        sources.configure(year=2030, dataset_page="https://example.test/ds-2030")
        rec = N.normalize({"PROPERTY_NUMBER_ID": "X", "PROPERTY_CATEGORY": "売買土地"},
                          source="registered")
        self.assertEqual(rec["dataset_year"], 2030)
        self.assertEqual(rec["provenance"]["dataset_year"], 2030)
        self.assertEqual(rec["provenance"]["source_url"], "https://example.test/ds-2030")
        # 築年の妥当範囲上限も追従（2030年築は許容される）
        self.assertEqual(N.parse_construction_year("2030/1/1"), 2030)

    def test_reset_restores_defaults(self):
        sources.configure(year=2099)
        sources.reset()
        self.assertEqual(sources.DATASET_YEAR, 2025)
        self.assertEqual(sources.effective_url(sources.REGISTERED), sources.REGISTERED.url)


if __name__ == "__main__":
    unittest.main()
