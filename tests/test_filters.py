"""商品条件フィルタ（src/filters.py）の回帰テスト。

既存のレビュー条件・NGワード・テーマ関連性フィルタは変更していないため、
今回追加したアルコール飲料除外（filter_by_alcohol_keywords）だけをテストする。

実行方法:
    python -m unittest tests.test_filters -v
"""

from __future__ import annotations

import unittest

from src import filters


def make_item(name: str, item_caption: str = "", catch_copy: str = "") -> dict:
    return {"name": name, "catch_copy": catch_copy, "item_caption": item_caption}


ALCOHOL_KEYWORDS = ["ビール", "チューハイ", "ワイン", "日本酒", "焼酎", "アルコール"]


class FilterByAlcoholKeywordsTest(unittest.TestCase):
    def test_removes_item_with_alcohol_in_name(self):
        items = [make_item("国産ビール 24本 ケース")]
        result = filters.filter_by_alcohol_keywords(items, ALCOHOL_KEYWORDS)
        self.assertEqual(result, [])

    def test_keeps_non_alcohol_beverage(self):
        items = [make_item("ミネラルウォーター 500ml 24本")]
        result = filters.filter_by_alcohol_keywords(items, ALCOHOL_KEYWORDS)
        self.assertEqual(len(result), 1)

    def test_checks_catch_copy_and_caption_too(self):
        items = [
            make_item("すっきり炭酸水", catch_copy="家飲みチューハイにも合う"),
            make_item("普通の炭酸水", item_caption="アルコール分は含まれていません"),
        ]
        result = filters.filter_by_alcohol_keywords(items, ALCOHOL_KEYWORDS)
        self.assertEqual(result, [])

    def test_empty_keyword_list_keeps_all_items(self):
        items = [make_item("国産ビール")]
        result = filters.filter_by_alcohol_keywords(items, [])
        self.assertEqual(len(result), 1)

    def test_mixed_list_keeps_only_non_alcohol_items(self):
        water = make_item("天然水 24本")
        beer = make_item("クラフトビール 6本セット")
        result = filters.filter_by_alcohol_keywords([water, beer], ALCOHOL_KEYWORDS)
        self.assertEqual(result, [water])


DURABLE_ACCESSORY_KEYWORDS = ["ホルダー", "スタンド", "ラック", "カバー", "ケース", "トレー", "フック", "ディスペンサー", "収納"]


class FilterByDurableAccessoryKeywordsTest(unittest.TestCase):
    def test_removes_toilet_paper_holder(self):
        items = [make_item("トイレットペーパーホルダー おしゃれ 2連 アイアン")]
        result = filters.filter_by_durable_accessory_keywords(items, DURABLE_ACCESSORY_KEYWORDS)
        self.assertEqual(result, [])

    def test_removes_tissue_case(self):
        items = [make_item("日本製ティッシュケース ペーパーポット おしゃれ")]
        result = filters.filter_by_durable_accessory_keywords(items, DURABLE_ACCESSORY_KEYWORDS)
        self.assertEqual(result, [])

    def test_keeps_actual_consumable_product(self):
        items = [make_item("トイレットペーパー 12ロール ダブル まとめ買い")]
        result = filters.filter_by_durable_accessory_keywords(items, DURABLE_ACCESSORY_KEYWORDS)
        self.assertEqual(len(result), 1)

    def test_empty_keyword_list_keeps_all_items(self):
        items = [make_item("トイレットペーパーホルダー")]
        result = filters.filter_by_durable_accessory_keywords(items, [])
        self.assertEqual(len(result), 1)


if __name__ == "__main__":
    unittest.main()
