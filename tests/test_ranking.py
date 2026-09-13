"""候補の並び順・選定ロジック（src/ranking.py）の回帰テスト。

「暮らしの便利グッズ」5件＋「消耗品・飲料」5件のバランス選定
（select_balanced_top）と、飲料の複数本セット優先（is_multipack /
sort_consumable_items）を中心にテストする。

実行方法:
    python -m unittest tests.test_ranking -v
"""

from __future__ import annotations

import unittest

from src import ranking


def make_item(
    item_code: str,
    category: str,
    review_count: int = 500,
    review_average: float = 4.5,
    name: str = "",
) -> dict:
    return {
        "item_code": item_code,
        "name": name or item_code,
        "catch_copy": "",
        "_category": category,
        "review_count": review_count,
        "review_average": review_average,
    }


class IsMultipackTest(unittest.TestCase):
    def test_true_when_name_contains_case_word(self):
        item = make_item("a", "水", name="天然水 ケース販売")
        self.assertTrue(ranking.is_multipack(item))

    def test_true_when_name_contains_matomegai(self):
        item = make_item("a", "水", name="天然水 まとめ買いセット")
        self.assertTrue(ranking.is_multipack(item))

    def test_true_when_name_contains_count_and_unit(self):
        item = make_item("a", "水", name="ミネラルウォーター 500ml 24本")
        self.assertTrue(ranking.is_multipack(item))

    def test_false_for_plain_single_item(self):
        item = make_item("a", "水", name="ミネラルウォーター 500ml")
        self.assertFalse(ranking.is_multipack(item))

    def test_checks_catch_copy_too(self):
        item = make_item("a", "水", name="ミネラルウォーター")
        item["catch_copy"] = "まとめ買いがお得な24本セット"
        self.assertTrue(ranking.is_multipack(item))


class SortConsumableItemsTest(unittest.TestCase):
    def test_beverage_multipack_ranked_above_single_even_with_lower_review_count(self):
        single = make_item("single", "水", review_count=900, name="お水 500ml")
        multipack = make_item("multipack", "水", review_count=100, name="お水 24本 ケース")

        result = ranking.sort_consumable_items([single, multipack])

        self.assertEqual([item["item_code"] for item in result], ["multipack", "single"])

    def test_non_beverage_category_is_unaffected_by_multipack_rule(self):
        higher = make_item("higher", "洗剤", review_count=900, name="洗濯洗剤")
        lower = make_item("lower", "洗剤", review_count=100, name="洗濯洗剤 詰め替え ケース")

        result = ranking.sort_consumable_items([lower, higher])

        # 洗剤は飲料カテゴリではないため、is_multipackに関係なくレビュー実績順のまま。
        self.assertEqual([item["item_code"] for item in result], ["higher", "lower"])

    def test_multiple_beverage_categories_each_prefer_their_own_multipack(self):
        water_single = make_item("water_single", "水", review_count=800, name="お水")
        water_case = make_item("water_case", "水", review_count=200, name="お水 24本 ケース")
        tea_single = make_item("tea_single", "お茶", review_count=800, name="緑茶")
        tea_case = make_item("tea_case", "お茶", review_count=200, name="緑茶 24本 ケース")

        result = ranking.sort_consumable_items([water_single, water_case, tea_single, tea_case])
        codes = [item["item_code"] for item in result]

        self.assertLess(codes.index("water_case"), codes.index("water_single"))
        self.assertLess(codes.index("tea_case"), codes.index("tea_single"))


class SelectBalancedTopTest(unittest.TestCase):
    def _make_group(self, category: str, count: int, prefix: str) -> list[dict]:
        return [
            make_item(f"{prefix}{i}", category, review_count=500 - i)
            for i in range(count)
        ]

    def test_normal_case_picks_five_and_five(self):
        convenience = self._make_group("収納", 8, "conv")
        consumable = self._make_group("洗剤", 8, "cons")

        result = ranking.select_balanced_top(convenience, consumable)

        self.assertEqual(len(result), 10)
        conv_count = sum(1 for i in result if i["item_code"].startswith("conv"))
        cons_count = sum(1 for i in result if i["item_code"].startswith("cons"))
        self.assertEqual(conv_count, 5)
        self.assertEqual(cons_count, 5)

    def test_total_never_exceeds_ten(self):
        convenience = self._make_group("収納", 20, "conv")
        consumable = self._make_group("洗剤", 20, "cons")

        result = ranking.select_balanced_top(convenience, consumable)

        self.assertLessEqual(len(result), 10)

    def test_convenience_shortfall_is_filled_from_consumable(self):
        # 便利グッズ側が3件しかない場合、消耗品側から2件補充されて合計10件になる。
        convenience = self._make_group("収納", 3, "conv")
        consumable = self._make_group("洗剤", 10, "cons")

        result = ranking.select_balanced_top(convenience, consumable)

        conv_count = sum(1 for i in result if i["item_code"].startswith("conv"))
        cons_count = sum(1 for i in result if i["item_code"].startswith("cons"))
        self.assertEqual(conv_count, 3)
        self.assertEqual(cons_count, 7)
        self.assertEqual(len(result), 10)

    def test_consumable_shortfall_is_filled_from_convenience(self):
        convenience = self._make_group("収納", 10, "conv")
        consumable = self._make_group("洗剤", 2, "cons")

        result = ranking.select_balanced_top(convenience, consumable)

        conv_count = sum(1 for i in result if i["item_code"].startswith("conv"))
        cons_count = sum(1 for i in result if i["item_code"].startswith("cons"))
        self.assertEqual(cons_count, 2)
        self.assertEqual(conv_count, 8)
        self.assertEqual(len(result), 10)

    def test_both_sides_short_returns_best_effort_without_exceeding_target(self):
        convenience = self._make_group("収納", 2, "conv")
        consumable = self._make_group("洗剤", 3, "cons")

        result = ranking.select_balanced_top(convenience, consumable)

        # 便利グッズ2件 + 消耗品3件(5件補充枠を満たせない) = 合計5件が上限。
        self.assertEqual(len(result), 5)

    def test_consumable_side_respects_max_per_category_diversity(self):
        # カテゴリを3つ（上限2件×3カテゴリ＝最大6件）用意しておけば、
        # 上限を守ったまま5件を選べる（1〜2カテゴリしかないと、上限を守ると
        # 5件に届かないため、2巡目で上限を超えて埋めるのが仕様）。
        # 便利グッズ側は十分な件数を用意し、消耗品側の不足による補充
        # （フォールバック）が起きないようにして、消耗品側だけの分散を見る。
        convenience = self._make_group("収納", 5, "conv")
        water = self._make_group("水", 5, "water")
        tea = self._make_group("お茶", 5, "tea")
        detergent = self._make_group("洗剤", 5, "det")

        result = ranking.select_balanced_top(
            convenience, water + tea + detergent, consumable_target=5, consumable_max_per_category=2
        )

        water_count = sum(1 for i in result if i["item_code"].startswith("water"))
        tea_count = sum(1 for i in result if i["item_code"].startswith("tea"))
        det_count = sum(1 for i in result if i["item_code"].startswith("det"))
        self.assertLessEqual(water_count, 2)
        self.assertLessEqual(tea_count, 2)
        self.assertLessEqual(det_count, 2)
        self.assertEqual(water_count + tea_count + det_count, 5)

    def test_no_duplicate_item_codes_in_result(self):
        convenience = self._make_group("収納", 8, "conv")
        consumable = self._make_group("洗剤", 8, "cons")

        result = ranking.select_balanced_top(convenience, consumable)
        codes = [item["item_code"] for item in result]

        self.assertEqual(len(codes), len(set(codes)))


if __name__ == "__main__":
    unittest.main()
