"""match のテスト: union・status 生成・contract 付与（docs/04）。"""

import unittest

from akiya_pipeline import match as M


def _reg(id_, **kw):
    return {"PROPERTY_NUMBER_ID": id_, "PROPERTY_CATEGORY": "売買居住用", **kw}


def _clo(id_, **kw):
    return {"ID": id_, "PROPERTY_CATEGORY": "売買居住用", **kw}


class ContractDateTest(unittest.TestCase):
    def test_us_format_to_iso(self):
        self.assertEqual(M._parse_contract_date("02/25/25"), "2025-02-25")
        self.assertEqual(M._parse_contract_date("12/24/25"), "2025-12-24")

    def test_invalid_or_missing(self):
        self.assertIsNone(M._parse_contract_date(""))
        self.assertIsNone(M._parse_contract_date("2025/02/25"))  # 別フォーマット
        self.assertIsNone(M._parse_contract_date("13/40/25"))  # 範囲外


class BuildDatasetTest(unittest.TestCase):
    def test_three_groups(self):
        # 登録: A(成約に無い), B(両方にある)
        registered = [_reg("A"), _reg("B")]
        # 成約: B(両方), C(成約のみ)
        closed = [
            _clo("B", CONTRACT_INFO_DATE="02/25/25", **{"CONTRACT_INFO_AMOUNT/RENT": "2000000"}),
            _clo("C"),
        ]
        ds = M.build_dataset(registered, closed)
        by_id = {r["id"]: r for r in ds}

        self.assertEqual(len(ds), 3)  # A + B + C（B は二重計上しない）

        # A: 登録のみ → registered
        self.assertEqual(by_id["A"]["status"], "registered")
        self.assertIsNone(by_id["A"]["contract"])

        # B: 両方にある → closed、属性は登録由来・contract は成約由来
        self.assertEqual(by_id["B"]["status"], "closed")
        self.assertEqual(by_id["B"]["source"], "registered")
        self.assertEqual(by_id["B"]["contract"]["date"], "2025-02-25")
        self.assertEqual(by_id["B"]["contract"]["amount_yen"], 2000000)

        # C: 成約のみ → closed、成約由来
        self.assertEqual(by_id["C"]["status"], "closed")
        self.assertEqual(by_id["C"]["source"], "closed")
        self.assertTrue(by_id["C"]["contract"]["is_closed"])

    def test_closed_count_equals_seiyaku_total(self):
        registered = [_reg("A"), _reg("B")]
        closed = [_clo("B"), _clo("C"), _clo("D")]
        ds = M.build_dataset(registered, closed)
        n_closed = sum(1 for r in ds if r["status"] == "closed")
        self.assertEqual(n_closed, 3)  # 成約総数と一致


if __name__ == "__main__":
    unittest.main()
