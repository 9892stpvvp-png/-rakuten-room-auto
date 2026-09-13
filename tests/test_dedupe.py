"""投稿済み履歴管理・重複チェック（src/dedupe.py）の回帰テスト。

実行方法:
    python -m unittest tests.test_dedupe -v
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src import dedupe


def make_item(item_code: str = "", item_url: str = "", **overrides) -> dict:
    item = {"item_code": item_code, "item_url": item_url}
    item.update(overrides)
    return item


class NormalizeItemUrlTest(unittest.TestCase):
    def test_strips_query_string(self):
        self.assertEqual(
            dedupe.normalize_item_url("https://item.rakuten.co.jp/shop/item001/?scid=abc"),
            "https://item.rakuten.co.jp/shop/item001",
        )

    def test_strips_fragment(self):
        self.assertEqual(
            dedupe.normalize_item_url("https://item.rakuten.co.jp/shop/item001/#reviews"),
            "https://item.rakuten.co.jp/shop/item001",
        )

    def test_strips_trailing_slash(self):
        self.assertEqual(
            dedupe.normalize_item_url("https://item.rakuten.co.jp/shop/item001/"),
            "https://item.rakuten.co.jp/shop/item001",
        )

    def test_empty_string_stays_empty(self):
        self.assertEqual(dedupe.normalize_item_url(""), "")

    def test_two_urls_with_different_query_normalize_to_same_value(self):
        a = dedupe.normalize_item_url("https://item.rakuten.co.jp/shop/item001/?scid=aaa")
        b = dedupe.normalize_item_url("https://item.rakuten.co.jp/shop/item001/?scid=bbb")
        self.assertEqual(a, b)


class LoadPostedItemsTest(unittest.TestCase):
    def test_missing_file_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "posted_items.json"
            self.assertEqual(dedupe.load_posted_items(path), [])

    def test_legacy_format_is_converted_to_item_code_records(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "posted_items.json"
            path.write_text(
                json.dumps({"posted_item_codes": ["shop:a", "shop:b"]}), encoding="utf-8"
            )
            items = dedupe.load_posted_items(path)
            self.assertEqual(
                sorted(item["item_code"] for item in items), ["shop:a", "shop:b"]
            )

    def test_new_format_is_returned_as_is(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "posted_items.json"
            record = {
                "item_code": "shop:a",
                "item_url": "https://item.rakuten.co.jp/shop/a/",
                "product_name": "商品A",
                "posted_at": "2026-09-14T00:00:00Z",
                "category": "収納",
            }
            path.write_text(
                json.dumps({"posted_item_codes": ["shop:a"], "posted_items": [record]}),
                encoding="utf-8",
            )
            items = dedupe.load_posted_items(path)
            self.assertEqual(items, [record])

    def test_load_posted_item_codes_backward_compat_helper(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "posted_items.json"
            path.write_text(json.dumps({"posted_item_codes": ["shop:a"]}), encoding="utf-8")
            self.assertEqual(dedupe.load_posted_item_codes(path), {"shop:a"})


class IsPostedAndRemoveDuplicatesTest(unittest.TestCase):
    def test_matches_by_item_code(self):
        index = dedupe.build_posted_index([make_item(item_code="shop:a")])
        self.assertTrue(dedupe.is_posted(make_item(item_code="shop:a"), index))
        self.assertFalse(dedupe.is_posted(make_item(item_code="shop:b"), index))

    def test_matches_by_normalized_url_even_with_different_item_code(self):
        # 楽天のitem_codeの取れ方が変わる等で、同じ商品でも過去とitem_codeが
        # 一致しないことがある想定。URLが一致すれば投稿済みとみなす。
        posted = make_item(
            item_code="shop:old-code", item_url="https://item.rakuten.co.jp/shop/a/"
        )
        index = dedupe.build_posted_index([posted])
        candidate = make_item(
            item_code="shop:new-code",
            item_url="https://item.rakuten.co.jp/shop/a/?scid=xyz",
        )
        self.assertTrue(dedupe.is_posted(candidate, index))

    def test_remove_duplicates_filters_posted_items(self):
        index = dedupe.build_posted_index([make_item(item_code="shop:a")])
        items = [make_item(item_code="shop:a"), make_item(item_code="shop:b")]
        result = dedupe.remove_duplicates(items, index)
        self.assertEqual([item["item_code"] for item in result], ["shop:b"])

    def test_remove_within_run_duplicates_unchanged_behavior(self):
        seen: set[str] = set()
        items = [make_item(item_code="shop:a"), make_item(item_code="shop:a")]
        result = dedupe.remove_within_run_duplicates(items, seen)
        self.assertEqual(len(result), 1)


class AppendPostedItemsTest(unittest.TestCase):
    def test_adds_new_items_and_persists_to_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "posted_items.json"
            new_items = [
                {
                    "item_code": "shop:a",
                    "item_url": "https://item.rakuten.co.jp/shop/a/",
                    "product_name": "商品A",
                    "posted_at": "2026-09-14T00:00:00Z",
                    "category": "収納",
                }
            ]
            result = dedupe.append_posted_items(new_items, path)
            self.assertEqual(result, dedupe.AppendResult(added=1, skipped=0, total=1))

            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(saved["posted_item_codes"], ["shop:a"])
            self.assertEqual(len(saved["posted_items"]), 1)
            self.assertEqual(saved["posted_items"][0]["product_name"], "商品A")

    def test_skips_item_already_in_history_by_item_code(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "posted_items.json"
            dedupe.append_posted_items([{"item_code": "shop:a"}], path)
            result = dedupe.append_posted_items([{"item_code": "shop:a"}], path)
            self.assertEqual(result.added, 0)
            self.assertEqual(result.skipped, 1)
            self.assertEqual(result.total, 1)

    def test_skips_item_already_in_history_by_url(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "posted_items.json"
            dedupe.append_posted_items(
                [{"item_code": "shop:a", "item_url": "https://item.rakuten.co.jp/shop/a/"}], path
            )
            result = dedupe.append_posted_items(
                [{"item_code": "shop:different-code", "item_url": "https://item.rakuten.co.jp/shop/a/?scid=1"}],
                path,
            )
            self.assertEqual(result.added, 0)
            self.assertEqual(result.skipped, 1)

    def test_skips_duplicates_within_the_same_batch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "posted_items.json"
            result = dedupe.append_posted_items(
                [{"item_code": "shop:a"}, {"item_code": "shop:a"}], path
            )
            self.assertEqual(result.added, 1)
            self.assertEqual(result.skipped, 1)
            self.assertEqual(result.total, 1)

    def test_accepts_product_id_and_name_key_aliases(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "posted_items.json"
            dedupe.append_posted_items(
                [{"product_id": "shop:a", "name": "商品A"}], path
            )
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(saved["posted_items"][0]["item_code"], "shop:a")
            self.assertEqual(saved["posted_items"][0]["product_name"], "商品A")

    def test_preserves_existing_legacy_entries(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "posted_items.json"
            path.write_text(json.dumps({"posted_item_codes": ["shop:old"]}), encoding="utf-8")
            result = dedupe.append_posted_items([{"item_code": "shop:new"}], path)
            self.assertEqual(result.total, 2)
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(sorted(saved["posted_item_codes"]), ["shop:new", "shop:old"])

    def test_records_without_code_or_url_are_skipped(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "posted_items.json"
            result = dedupe.append_posted_items([{"product_name": "商品名のみ"}], path)
            self.assertEqual(result.added, 0)
            self.assertEqual(result.skipped, 1)


if __name__ == "__main__":
    unittest.main()
