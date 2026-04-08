"""normalize のテスト: 分解・単位統一・型付け・欠損方針。"""

import unittest

from akiya_pipeline import normalize as N


class ParsersTest(unittest.TestCase):
    def test_clean_str(self):
        self.assertIsNone(N.clean_str(""))
        self.assertIsNone(N.clean_str("  "))
        self.assertEqual(N.clean_str(" foo "), "foo")
        self.assertEqual(N.clean_str("a\r\nb"), "a\nb")
        self.assertEqual(N.clean_str("家庭菜園付き　駐車場"), "家庭菜園付き　駐車場")  # 全角空白保持

    def test_parse_int_float(self):
        self.assertEqual(N.parse_int("123"), 123)
        self.assertIsNone(N.parse_int("12.3"))
        self.assertIsNone(N.parse_int("4分"))
        self.assertEqual(N.parse_float("12.3"), 12.3)
        self.assertEqual(N.parse_float("160"), 160.0)

    def test_parse_yen_zero_is_none(self):
        self.assertEqual(N.parse_yen("19800000"), 19800000)
        self.assertIsNone(N.parse_yen("0"))  # 応談・非公開
        self.assertIsNone(N.parse_yen(""))

    def test_split_category(self):
        self.assertEqual(N.split_category("売買居住用"), ("sale", "residential"))
        self.assertEqual(N.split_category("賃貸土地"), ("rent", "land"))
        self.assertEqual(N.split_category("売買事業用"), ("sale", "commercial"))
        self.assertEqual(N.split_category(""), (None, None))

    def test_construction_year(self):
        self.assertEqual(N.parse_construction_year("1958/2/1"), 1958)
        self.assertIsNone(N.parse_construction_year("3000/1/1"))  # 範囲外
        self.assertIsNone(N.parse_construction_year(""))

    def test_station_distance_units(self):
        self.assertEqual(
            N.parse_station_distance("4分"),
            {"raw": "4分", "minutes": 4, "meters": None, "unit_confidence": "high"},
        )
        self.assertEqual(
            N.parse_station_distance("750m"),
            {"raw": "750m", "minutes": None, "meters": 750, "unit_confidence": "high"},
        )
        # 単位なし: ≤60 は分、>60 はメートル、いずれも low
        self.assertEqual(N.parse_station_distance("3")["minutes"], 3)
        self.assertEqual(N.parse_station_distance("3")["unit_confidence"], "low")
        self.assertEqual(N.parse_station_distance("3600")["meters"], 3600)
        self.assertEqual(N.parse_station_distance("3600")["unit_confidence"], "low")

    def test_bool_arinashi(self):
        self.assertTrue(N.parse_bool_arinashi("有り"))
        self.assertFalse(N.parse_bool_arinashi("無し"))
        self.assertIsNone(N.parse_bool_arinashi(""))


class NormalizeRecordTest(unittest.TestCase):
    def test_sale_record_routes_amount_to_price(self):
        row = {
            "PROPERTY_NUMBER_ID": "9000002",
            "PROPERTY_CATEGORY": "売買居住用",
            "PREFECTURE": "山梨県",
            "CITY": "甲府市",
            "AMOUNT/RENT": "19800000",
            "DATE_OF_CONSTRUCTION": "1958/2/1",
            "CONSTRUCTION": "木造",
            "FARMLAND": "無し",
        }
        rec = N.normalize(row, source="registered", row_index=0)
        self.assertEqual(rec["deal_type"], "sale")
        self.assertEqual(rec["price_yen"], 19800000)
        self.assertIsNone(rec["rent_monthly_yen"])
        self.assertEqual(rec["building"]["construction_year"], 1958)
        self.assertFalse(rec["flags"]["farmland"])
        self.assertEqual(rec["source"], "registered")

    def test_rent_record_routes_amount_to_rent(self):
        row = {
            "ID": "9000056",
            "PROPERTY_CATEGORY": "賃貸居住用",
            "PREFECTURE": "大阪府",
            "CITY": "高石市",
            "AMOUNT/RENT": "50000",
            "NUMBER_OF_ROOMS": "2DK",
        }
        rec = N.normalize(row, source="closed", row_index=0)
        self.assertEqual(rec["deal_type"], "rent")
        self.assertEqual(rec["rent_monthly_yen"], 50000)
        self.assertIsNone(rec["price_yen"])
        self.assertEqual(rec["building"]["layout"], "2DK")  # NUMBER_OF_ROOMS 由来
        self.assertEqual(rec["id"], "9000056")

    def test_structure_shitei_nashi_is_none(self):
        rec = N.normalize({"CONSTRUCTION": "指定なし"}, source="registered")
        self.assertIsNone(rec["building"]["structure"])


if __name__ == "__main__":
    unittest.main()
