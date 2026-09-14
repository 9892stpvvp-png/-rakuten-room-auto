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


class NormalizeProductNameTest(unittest.TestCase):
    def test_strips_listed_ad_phrases(self):
        name = "送料無料 ポイント10倍 ランキング 公式 限定 レビュー特典 ギフト SNSで話題 365日発送 クーポン セール マーナ シートケース"
        self.assertEqual(dedupe.normalize_product_name(name), "マーナ シートケース")

    def test_strips_sns_demo_mo_wadai_variant(self):
        self.assertEqual(
            dedupe.normalize_product_name("マーナ シートケース SNSでも話題!"),
            "マーナ シートケース",
        )

    def test_strips_decorative_brackets_but_keeps_content(self):
        self.assertEqual(
            dedupe.normalize_product_name("【楽天1位】《人気》マーナ シートケース"),
            "楽天1位 人気 マーナ シートケース",
        )

    def test_strips_emoji(self):
        self.assertEqual(
            dedupe.normalize_product_name("マーナ シートケース 🎉✨"),
            "マーナ シートケース",
        )

    def test_collapses_extra_whitespace(self):
        self.assertEqual(
            dedupe.normalize_product_name("マーナ   シートケース\n\n本体"),
            "マーナ シートケース 本体",
        )

    def test_full_width_and_half_width_normalize_to_the_same_value(self):
        full_width = dedupe.normalize_product_name("ＭＡＲＮＡ　シートケース１２３")
        half_width = dedupe.normalize_product_name("MARNA シートケース123")
        self.assertEqual(full_width, half_width)

    def test_english_case_is_ignored(self):
        self.assertEqual(
            dedupe.normalize_product_name("MARNA SheetCase"),
            dedupe.normalize_product_name("marna sheetcase"),
        )

    def test_keeps_brand_and_series_name(self):
        self.assertIn("tower", dedupe.normalize_product_name("tower マグネットバスルームラック"))
        self.assertIn(
            "マグネットバスルームラック",
            dedupe.normalize_product_name("tower マグネットバスルームラック"),
        )

    def test_wide_and_large_are_treated_as_different_products(self):
        wide = dedupe.normalize_product_name("tower マグネットバスルームラック タワー ワイド")
        large = dedupe.normalize_product_name("tower マグネットバスルームラック タワー ラージ")
        self.assertNotEqual(wide, large)

    def test_single_and_five_piece_set_are_treated_as_different_products(self):
        single = dedupe.normalize_product_name("冷凍ごはん容器 1個")
        five_set = dedupe.normalize_product_name("冷凍ごはん容器 5個セット")
        self.assertNotEqual(single, five_set)

    def test_keeps_size_capacity_and_model_number(self):
        normalized = dedupe.normalize_product_name("水切りボウル Mサイズ 2L 型番XY-100")
        for token in ("mサイズ", "2l", "xy-100"):
            self.assertIn(token, normalized)

    def test_empty_string_stays_empty(self):
        self.assertEqual(dedupe.normalize_product_name(""), "")

    def test_decorated_and_plain_names_normalize_to_the_same_value(self):
        decorated = (
            "【送料無料】マーナ　シートケース　ポイント５倍　公式　限定"
            "　レビュー特典　ギフト　SNSでも話題！　365日発送　クーポン　セール　🎉"
        )
        plain = "マーナ シートケース"
        self.assertEqual(dedupe.normalize_product_name(decorated), plain)


class MatchPostedReasonTest(unittest.TestCase):
    def test_matches_by_item_code(self):
        index = dedupe.build_posted_index([make_item(item_code="shop:a")])
        self.assertEqual(
            dedupe.match_posted_reason(make_item(item_code="shop:a"), index), "item_code"
        )
        self.assertIsNone(dedupe.match_posted_reason(make_item(item_code="shop:b"), index))

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
        self.assertEqual(dedupe.match_posted_reason(candidate, index), "url")

    def test_matches_by_product_name_when_code_and_url_are_absent(self):
        # 過去のROOM投稿のように、item_code・item_urlが取れない商品でも、
        # 商品名の完全一致（正規化後）で投稿済みと判定できる。
        posted = make_item(product_name="マーナ シートケース")
        index = dedupe.build_posted_index([posted])
        candidate = make_item(name="【送料無料】マーナ　シートケース　公式")
        self.assertEqual(dedupe.match_posted_reason(candidate, index), "product_name")

    def test_item_code_match_takes_priority_over_product_name(self):
        # item_codeが一致していれば、商品名が正規化後に一致しなくてもitem_code
        # 判定が優先されることを確認する（優先順位1）。
        posted = make_item(item_code="shop:a", product_name="旧商品名")
        index = dedupe.build_posted_index([posted])
        candidate = make_item(item_code="shop:a", name="まったく違う商品名")
        self.assertEqual(dedupe.match_posted_reason(candidate, index), "item_code")

    def test_url_match_takes_priority_over_product_name(self):
        posted = make_item(item_url="https://item.rakuten.co.jp/shop/a/", product_name="旧商品名")
        index = dedupe.build_posted_index([posted])
        candidate = make_item(
            item_url="https://item.rakuten.co.jp/shop/a/", name="まったく違う商品名"
        )
        self.assertEqual(dedupe.match_posted_reason(candidate, index), "url")

    def test_similar_but_different_product_names_are_not_matched(self):
        # 商品名が似ているだけで別商品を除外しない（部分一致ではなく完全一致）。
        posted = make_item(product_name="tower マグネットバスルームラック タワー ワイド")
        index = dedupe.build_posted_index([posted])
        candidate = make_item(name="tower マグネットバスルームラック タワー ラージ")
        self.assertIsNone(dedupe.match_posted_reason(candidate, index))

    def test_different_quantity_variants_are_not_matched(self):
        posted = make_item(product_name="冷凍ごはん容器 1個")
        index = dedupe.build_posted_index([posted])
        candidate = make_item(name="冷凍ごはん容器 5個セット")
        self.assertIsNone(dedupe.match_posted_reason(candidate, index))

    def test_empty_normalized_name_never_matches(self):
        # 装飾を全部取り除いたら空文字になるような商品名同士を、誤って
        # 「両方空文字だから一致」としないことを確認する。
        posted = make_item(product_name="🎉✨")
        index = dedupe.build_posted_index([posted])
        candidate = make_item(name="🎊🎈")
        self.assertIsNone(dedupe.match_posted_reason(candidate, index))


class IsPostedAndRemoveDuplicatesTest(unittest.TestCase):
    def test_matches_by_item_code(self):
        index = dedupe.build_posted_index([make_item(item_code="shop:a")])
        self.assertTrue(dedupe.is_posted(make_item(item_code="shop:a"), index))
        self.assertFalse(dedupe.is_posted(make_item(item_code="shop:b"), index))

    def test_matches_by_normalized_url_even_with_different_item_code(self):
        posted = make_item(
            item_code="shop:old-code", item_url="https://item.rakuten.co.jp/shop/a/"
        )
        index = dedupe.build_posted_index([posted])
        candidate = make_item(
            item_code="shop:new-code",
            item_url="https://item.rakuten.co.jp/shop/a/?scid=xyz",
        )
        self.assertTrue(dedupe.is_posted(candidate, index))

    def test_matches_by_product_name(self):
        index = dedupe.build_posted_index([make_item(product_name="マーナ シートケース")])
        candidate = make_item(name="マーナ シートケース")
        self.assertTrue(dedupe.is_posted(candidate, index))

    def test_remove_duplicates_filters_posted_items(self):
        index = dedupe.build_posted_index([make_item(item_code="shop:a")])
        items = [make_item(item_code="shop:a"), make_item(item_code="shop:b")]
        result = dedupe.remove_duplicates(items, index)
        self.assertEqual([item["item_code"] for item in result], ["shop:b"])

    def test_remove_duplicates_also_filters_by_product_name(self):
        index = dedupe.build_posted_index([make_item(product_name="マーナ シートケース")])
        items = [
            make_item(item_code="shop:a", name="マーナ シートケース"),
            make_item(item_code="shop:b", name="別の商品"),
        ]
        result = dedupe.remove_duplicates(items, index)
        self.assertEqual([item["item_code"] for item in result], ["shop:b"])

    def test_remove_within_run_duplicates_unchanged_behavior(self):
        seen: set[str] = set()
        items = [make_item(item_code="shop:a"), make_item(item_code="shop:a")]
        result = dedupe.remove_within_run_duplicates(items, seen)
        self.assertEqual(len(result), 1)


class RemoveDuplicatesWithBreakdownTest(unittest.TestCase):
    def test_counts_each_exclusion_reason_separately(self):
        posted = [
            make_item(item_code="shop:code-match"),
            make_item(item_url="https://item.rakuten.co.jp/shop/url-match/"),
            make_item(product_name="マーナ シートケース"),
        ]
        index = dedupe.build_posted_index(posted)
        items = [
            make_item(item_code="shop:code-match"),
            make_item(item_url="https://item.rakuten.co.jp/shop/url-match/"),
            make_item(name="マーナ シートケース"),
            make_item(item_code="shop:new", name="新商品"),
        ]

        kept, breakdown = dedupe.remove_duplicates_with_breakdown(items, index)

        self.assertEqual([item["item_code"] for item in kept], ["shop:new"])
        self.assertEqual(breakdown, {"item_code": 1, "url": 1, "product_name": 1})


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

    def test_product_name_only_records_are_accepted(self):
        # 過去のROOM投稿のように、item_code・item_urlが取れない商品でも、
        # 商品名さえあれば登録できる（商品名ベースの補助重複判定のため）。
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "posted_items.json"
            result = dedupe.append_posted_items([{"product_name": "商品名のみ"}], path)
            self.assertEqual(result.added, 1)
            self.assertEqual(result.skipped, 0)

            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(saved["posted_items"][0]["product_name"], "商品名のみ")
            self.assertEqual(saved["posted_items"][0]["item_code"], "")
            self.assertEqual(saved["posted_item_codes"], [])

    def test_records_with_explicit_null_values_are_handled_safely(self):
        # ユーザー提示のseed形式（item_code/item_url/posted_atがnull）を
        # そのまま取り込めることを確認する。
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "posted_items.json"
            result = dedupe.append_posted_items(
                [
                    {
                        "product_name": "マーナ シートケース",
                        "item_code": None,
                        "item_url": None,
                        "posted_at": None,
                        "category": "過去投稿",
                    }
                ],
                path,
            )
            self.assertEqual(result.added, 1)
            saved = json.loads(path.read_text(encoding="utf-8"))
            record = saved["posted_items"][0]
            self.assertEqual(record["product_name"], "マーナ シートケース")
            self.assertEqual(record["item_code"], "")
            self.assertEqual(record["item_url"], "")
            self.assertEqual(record["posted_at"], "")
            self.assertEqual(record["category"], "過去投稿")

    def test_records_with_no_identifying_info_at_all_are_skipped(self):
        # item_code・item_url・product_nameのいずれも無ければ登録しない。
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "posted_items.json"
            result = dedupe.append_posted_items([{"category": "過去投稿"}], path)
            self.assertEqual(result.added, 0)
            self.assertEqual(result.skipped, 1)

    def test_duplicate_product_name_is_not_double_registered(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "posted_items.json"
            dedupe.append_posted_items([{"product_name": "マーナ シートケース"}], path)
            result = dedupe.append_posted_items(
                [{"product_name": "【送料無料】マーナ　シートケース　公式"}], path
            )
            self.assertEqual(result.added, 0)
            self.assertEqual(result.skipped, 1)
            self.assertEqual(result.total, 1)


if __name__ == "__main__":
    unittest.main()
