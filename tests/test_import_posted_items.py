"""投稿済み履歴の一括取り込みスクリプト（src/import_posted_items.py）のテスト。

実行方法:
    python -m unittest tests.test_import_posted_items -v
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src import import_posted_items


class ImportPostedItemsTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.tmp_path = Path(self.tmpdir.name)
        self.posted_items_path = self.tmp_path / "posted_items.json"
        patcher = mock.patch.object(
            import_posted_items, "POSTED_ITEMS_PATH", self.posted_items_path
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def _write_input(self, data) -> Path:
        input_path = self.tmp_path / "input.json"
        input_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return input_path

    def test_imports_new_items_into_posted_items_json(self):
        input_path = self._write_input(
            [
                {
                    "item_code": "shop:a",
                    "item_url": "https://item.rakuten.co.jp/shop/a/",
                    "product_name": "商品A",
                    "posted_at": "2026-09-01T00:00:00Z",
                }
            ]
        )
        import_posted_items.main([str(input_path)])

        saved = json.loads(self.posted_items_path.read_text(encoding="utf-8"))
        self.assertEqual(saved["posted_item_codes"], ["shop:a"])
        self.assertEqual(len(saved["posted_items"]), 1)

    def test_does_not_double_register_items_already_present(self):
        input_path = self._write_input([{"item_code": "shop:a"}])
        import_posted_items.main([str(input_path)])
        import_posted_items.main([str(input_path)])

        saved = json.loads(self.posted_items_path.read_text(encoding="utf-8"))
        self.assertEqual(len(saved["posted_items"]), 1)

    def test_missing_input_file_raises_system_exit(self):
        with self.assertRaises(SystemExit):
            import_posted_items.main([str(self.tmp_path / "does_not_exist.json")])

    def test_non_list_json_raises_system_exit(self):
        input_path = self._write_input({"not": "a list"})
        with self.assertRaises(SystemExit):
            import_posted_items.main([str(input_path)])

    def test_wrong_number_of_arguments_raises_system_exit(self):
        with self.assertRaises(SystemExit):
            import_posted_items.main([])
        with self.assertRaises(SystemExit):
            import_posted_items.main(["a", "b"])


if __name__ == "__main__":
    unittest.main()
