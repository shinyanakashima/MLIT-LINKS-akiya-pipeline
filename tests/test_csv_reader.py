"""csv_reader のテスト: BOM除去・フィールド内改行。"""

import tempfile
import unittest
from pathlib import Path

from akiya_pipeline import csv_reader


class ReadRowsTest(unittest.TestCase):
    def _write(self, content: bytes) -> Path:
        tmp = Path(tempfile.mkdtemp()) / "t.csv"
        tmp.write_bytes(content)
        return tmp

    def test_strips_bom(self):
        # 先頭に UTF-8 BOM を付与してもヘッダ名が汚れないこと。
        path = self._write("﻿ID,NAME\r\n1,foo\r\n".encode("utf-8"))
        rows = csv_reader.read_all(path)
        self.assertEqual(rows[0]["ID"], "1")  # "﻿ID" になっていない
        self.assertEqual(list(rows[0].keys()), ["ID", "NAME"])

    def test_keeps_in_field_newline(self):
        # クオート内の改行を1フィールドとして保持すること。
        path = self._write('ID,PR\r\n1,"line1\nline2"\r\n'.encode("utf-8"))
        rows = csv_reader.read_all(path)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["PR"], "line1\nline2")


if __name__ == "__main__":
    unittest.main()
