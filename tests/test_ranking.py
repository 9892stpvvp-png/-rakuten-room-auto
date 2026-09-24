"""候補の並び順・選定ロジック（src/ranking.py）の回帰テスト。

「暮らしの便利グッズ」5件＋「消耗品・飲料」5件のバランス選定
（select_balanced_top）と、飲料の複数本セット優先（is_multipack /
sort_consumable_items）に加えて、同じ商品タイプ・カテゴリーが連日
続けて選ばれることを抑える優先度調整（priority_tier /
compute_recent_type_counts / sort_by_quality・sort_consumable_itemsの
recent_type_counts・recent_category_counts・rng引数）を中心にテストする。

実行方法:
    python -m unittest tests.test_ranking -v
"""

from __future__ import annotations

import random
import unittest
from datetime import datetime, timezone

from src import ranking


def make_item(
    item_code: str,
    category: str,
    review_count: int = 500,
    review_average: float = 4.5,
    name: str = "",
    product_type: str = "",
) -> dict:
    return {
        "item_code": item_code,
        "name": name or item_code,
        "catch_copy": "",
        "_category": category,
        "_product_type": product_type,
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


class TypeTierTest(unittest.TestCase):
    def test_zero_count_is_tier_zero(self):
        self.assertEqual(ranking.type_tier(0), 0)

    def test_counts_increase_tier_up_to_the_cap(self):
        self.assertEqual(ranking.type_tier(1), 1)
        self.assertEqual(ranking.type_tier(2), 2)
        self.assertEqual(ranking.type_tier(3), 3)

    def test_counts_beyond_cap_do_not_increase_tier_further(self):
        self.assertEqual(ranking.type_tier(4), 3)
        self.assertEqual(ranking.type_tier(50), 3)


class PriorityTierTest(unittest.TestCase):
    def test_zero_when_no_recent_counts_given(self):
        item = make_item("a", "キッチン", name="スポンジ", product_type="スポンジ")
        self.assertEqual(ranking.priority_tier(item), 0)

    def test_sums_product_type_and_category_tiers(self):
        item = make_item("a", "キッチン消耗品", name="スポンジ", product_type="スポンジ")
        tier = ranking.priority_tier(
            item,
            recent_type_counts={"スポンジ": 2},
            recent_category_counts={"キッチン消耗品": 1},
        )
        self.assertEqual(tier, 3)

    def test_recently_unseen_type_is_not_penalized(self):
        # 直近に出ていない商品タイプ（ハンガー）は、他の商品タイプ（スポンジ）が
        # 何度投稿されていても不必要にペナルティを受けない。
        item = make_item("a", "収納", name="ハンガー", product_type="ハンガー")
        tier = ranking.priority_tier(
            item,
            recent_type_counts={"スポンジ": 5},
            recent_category_counts={"キッチン消耗品": 5},
        )
        self.assertEqual(tier, 0)


class ComputeRecentTypeCountsTest(unittest.TestCase):
    def test_counts_only_entries_within_the_lookback_window(self):
        now = datetime(2026, 9, 21, tzinfo=timezone.utc)
        posted = [
            {"product_name": "スポンジA", "posted_at": "2026-09-20T10:00:00Z"},
            {"product_name": "スポンジB", "posted_at": "2026-09-10T10:00:00Z"},  # 7日より前
        ]
        counts = ranking.compute_recent_type_counts(
            posted,
            lambda e: "スポンジ" if "スポンジ" in e.get("product_name", "") else "",
            now=now,
        )
        self.assertEqual(counts, {"スポンジ": 1})

    def test_entries_without_posted_at_are_skipped_not_fabricated(self):
        # posted_atが保存されていない（旧形式の）投稿は、日時を勝手に補わず
        # 集計対象から除外する。
        now = datetime(2026, 9, 21, tzinfo=timezone.utc)
        posted = [
            {"product_name": "スポンジ", "posted_at": ""},
            {"product_name": "スポンジ"},
        ]
        counts = ranking.compute_recent_type_counts(posted, lambda e: "スポンジ", now=now)
        self.assertEqual(counts, {})

    def test_works_with_old_format_entries_missing_fields(self):
        # 旧形式（item_codeだけ）のposted_itemsにはposted_atが無いため、
        # エラーにならず、単に集計対象から外れる。
        now = datetime(2026, 9, 21, tzinfo=timezone.utc)
        posted = [{"item_code": "shop:old001"}]
        counts = ranking.compute_recent_type_counts(posted, lambda e: "何か", now=now)
        self.assertEqual(counts, {})


class SortByQualityWithPriorityTierTest(unittest.TestCase):
    def test_recently_seen_type_is_deprioritized_but_not_excluded(self):
        sponge = make_item("sponge", "キッチン", review_count=900, name="スポンジ", product_type="スポンジ")
        other = make_item("other", "キッチン", review_count=300, name="水切りかご", product_type="水切りかご")

        result = ranking.sort_by_quality([sponge, other], recent_type_counts={"スポンジ": 1})

        self.assertEqual([i["item_code"] for i in result], ["other", "sponge"])
        self.assertIn("sponge", [i["item_code"] for i in result])

    def test_falls_back_to_deprioritized_type_when_it_is_the_only_option(self):
        sponge = make_item("sponge", "キッチン", review_count=900, name="スポンジ", product_type="スポンジ")

        result = ranking.sort_by_quality([sponge], recent_type_counts={"スポンジ": 5})

        self.assertEqual([i["item_code"] for i in result], ["sponge"])

    def test_no_recent_counts_behaves_exactly_like_before(self):
        a = make_item("a", "収納", review_count=500)
        b = make_item("b", "収納", review_count=300)

        self.assertEqual(
            [i["item_code"] for i in ranking.sort_by_quality([b, a])],
            [i["item_code"] for i in ranking.sort_by_quality([b, a], recent_type_counts={}, recent_category_counts={})],
        )


class RandomnessIsSeedableTest(unittest.TestCase):
    def _tied_items(self):
        return [
            make_item("x", "収納", review_count=500, review_average=4.5),
            make_item("y", "収納", review_count=500, review_average=4.5),
            make_item("z", "収納", review_count=500, review_average=4.5),
        ]

    def test_same_seed_produces_same_order(self):
        items = self._tied_items()
        result1 = ranking.sort_by_quality(list(items), rng=random.Random(42))
        result2 = ranking.sort_by_quality(list(items), rng=random.Random(42))
        self.assertEqual(
            [i["item_code"] for i in result1],
            [i["item_code"] for i in result2],
        )

    def test_without_rng_result_is_deterministic(self):
        items = self._tied_items()
        result1 = ranking.sort_by_quality(list(items))
        result2 = ranking.sort_by_quality(list(items))
        self.assertEqual(
            [i["item_code"] for i in result1],
            [i["item_code"] for i in result2],
        )

    def test_randomness_never_reorders_across_different_tiers(self):
        # ランダム性は同点（同じ優先度段階・同じ品質）の商品同士の並びにしか
        # 影響しない。優先度段階が違えば、rngを渡しても順序は変わらない。
        sponge = make_item("sponge", "キッチン", review_count=900, name="スポンジ", product_type="スポンジ")
        other = make_item("other", "キッチン", review_count=900, review_average=4.5, name="水切りかご", product_type="水切りかご")

        for seed in range(5):
            result = ranking.sort_by_quality(
                [sponge, other],
                recent_type_counts={"スポンジ": 1},
                rng=random.Random(seed),
            )
            self.assertEqual([i["item_code"] for i in result], ["other", "sponge"])


class SelectBalancedTopWithProductTypeDiversityTest(unittest.TestCase):
    def _make_group(self, category: str, count: int, prefix: str) -> list[dict]:
        return [
            make_item(f"{prefix}{i}", category, review_count=500 - i)
            for i in range(count)
        ]

    def test_sponge_deprioritized_below_other_type_but_not_excluded(self):
        # 「昨日スポンジを投稿していて、今日スポンジと別商品タイプの両方がある場合」
        sponge = make_item("sponge1", "キッチン", review_count=900, name="スポンジ", product_type="スポンジ")
        hanger = make_item("hanger1", "収納", review_count=200, name="ハンガー", product_type="ハンガー")
        consumable = self._make_group("洗剤", 2, "cons")

        result = ranking.select_balanced_top(
            [sponge, hanger],
            consumable,
            convenience_target=2,
            consumable_target=2,
            recent_type_counts={"スポンジ": 1},
        )

        conv_order = [i["item_code"] for i in result if i["item_code"] in ("sponge1", "hanger1")]
        self.assertEqual(conv_order, ["hanger1", "sponge1"])
        self.assertIn("sponge1", [i["item_code"] for i in result])

    def test_sponge_only_candidate_still_selected_without_loosening_quality(self):
        # 「スポンジしか条件適合商品がない場合は、品質条件を緩めずスポンジを復帰できる」
        sponge = make_item("sponge1", "キッチン", review_count=900, name="スポンジ", product_type="スポンジ")
        consumable = self._make_group("洗剤", 2, "cons")

        result = ranking.select_balanced_top(
            [sponge],
            consumable,
            convenience_target=2,
            consumable_target=2,
            recent_type_counts={"スポンジ": 5},
        )

        self.assertIn("sponge1", [i["item_code"] for i in result])

    def test_cardboard_stocker_uses_the_same_generic_mechanism(self):
        # 「段ボールストッカーについても同じ仕組みが働く」（商品タイプ名を
        # ハードコードした専用ロジックではなく、同じpriority_tierの仕組みを再利用）。
        stocker = make_item(
            "stocker1", "収納", review_count=900, name="段ボールストッカー", product_type="段ボールストッカー"
        )
        hanger = make_item("hanger1", "収納", review_count=200, name="ハンガー", product_type="ハンガー")
        consumable = self._make_group("洗剤", 2, "cons")

        result = ranking.select_balanced_top(
            [stocker, hanger],
            consumable,
            convenience_target=2,
            consumable_target=2,
            recent_type_counts={"段ボールストッカー": 1},
        )

        conv_order = [i["item_code"] for i in result if i["item_code"] in ("stocker1", "hanger1")]
        self.assertEqual(conv_order, ["hanger1", "stocker1"])

    def test_existing_five_and_five_balance_is_unaffected_by_new_optional_arguments(self):
        convenience = self._make_group("収納", 8, "conv")
        consumable = self._make_group("洗剤", 8, "cons")

        without_tiers = ranking.select_balanced_top(convenience, consumable)
        with_empty_tiers = ranking.select_balanced_top(
            convenience, consumable, recent_type_counts={}, recent_category_counts={}
        )

        self.assertEqual(
            [i["item_code"] for i in without_tiers],
            [i["item_code"] for i in with_empty_tiers],
        )
        self.assertEqual(len(without_tiers), 10)

    def test_shortage_never_fabricates_items_only_reorders_existing_candidates(self):
        # 「候補不足時に品質条件を緩めない」: ranking側は渡された候補を並べ替える
        # だけで、条件を満たさない新しい商品を作り出すことはない。
        sponge = make_item("sponge1", "キッチン", review_count=900, name="スポンジ", product_type="スポンジ")

        result = ranking.select_balanced_top(
            [sponge],
            [],
            convenience_target=5,
            consumable_target=5,
            recent_type_counts={"スポンジ": 5},
        )

        self.assertEqual([i["item_code"] for i in result], ["sponge1"])


class SelectTopCandidatesTest(unittest.TestCase):
    """全ジャンル化（description-genre-001）の選定方式select_top_candidates。

    「暮らしの便利グッズ」枠／「消耗品・飲料」枠という固定の5+5構成を前提に
    せず、全ジャンルを1つのプールとして扱って上位N件を選ぶことを確認する。
    """

    def _make_group(self, category: str, count: int, prefix: str) -> list[dict]:
        return [
            make_item(f"{prefix}{i}", category, review_count=500 - i, product_type=category)
            for i in range(count)
        ]

    def test_does_not_force_a_fixed_five_five_split(self):
        # 「便利グッズ」寄り・「消耗品」寄りという区別を一切持たず、ジャンルが
        # 2つだけでも合計target件数だけを見て選ぶ（5+5固定にならない）。
        items = self._make_group("食品", 6, "food") + self._make_group("美容", 6, "beauty")

        result = ranking.select_top_candidates(items, target=10, max_per_category=5)

        self.assertEqual(len(result), 10)
        food_count = sum(1 for i in result if i["item_code"].startswith("food"))
        beauty_count = sum(1 for i in result if i["item_code"].startswith("beauty"))
        self.assertEqual(food_count + beauty_count, 10)

    def test_does_not_concentrate_on_a_single_genre_when_many_are_available(self):
        # 「10件すべて同一ジャンルになりにくい」ことの確認。多くのジャンルが
        # 十分な候補を持つ場合、max_per_categoryの上限により1ジャンルに
        # 集中しない。
        genres = ["食品", "美容", "家電", "ペット用品", "ベビー用品", "健康", "ファッション", "生活雑貨"]
        items: list[dict] = []
        for i, genre in enumerate(genres):
            items.extend(self._make_group(genre, 3, f"g{i}_"))

        result = ranking.select_top_candidates(items, target=10, max_per_category=2)

        self.assertEqual(len(result), 10)
        selected_genres = {i["_category"] for i in result}
        self.assertGreater(len(selected_genres), 2, selected_genres)
        counts_per_genre: dict[str, int] = {}
        for item in result:
            counts_per_genre[item["_category"]] = counts_per_genre.get(item["_category"], 0) + 1
        self.assertTrue(all(count <= 2 for count in counts_per_genre.values()), counts_per_genre)

    def test_no_duplicate_item_codes(self):
        items = self._make_group("食品", 15, "food")
        result = ranking.select_top_candidates(items, target=10, max_per_category=10)
        codes = [i["item_code"] for i in result]
        self.assertEqual(len(codes), len(set(codes)))

    def test_shortage_returns_fewer_than_target_without_fabricating(self):
        # 候補不足時に品質条件を緩めて水増ししない（渡された候補以上には増えない）。
        items = self._make_group("食品", 3, "food")
        result = ranking.select_top_candidates(items, target=10, max_per_category=2)
        self.assertEqual(len(result), 3)
        self.assertEqual({i["item_code"] for i in result}, {"food0", "food1", "food2"})

    def test_recently_common_genre_is_deprioritized_but_not_excluded(self):
        # 「大ジャンル」（category）レベルでの偏り防止：直近よく投稿している
        # ジャンルの商品は優先度が下がるが、完全除外はしない。
        common_genre_items = self._make_group("ペット用品", 3, "pet")
        rare_genre_item = self._make_group("健康", 1, "health")

        result = ranking.select_top_candidates(
            common_genre_items + rare_genre_item,
            target=4,
            max_per_category=4,
            recent_category_counts={"ペット用品": 3},
        )
        codes = [i["item_code"] for i in result]
        self.assertEqual(codes[0], "health0")
        self.assertIn("pet0", codes)  # 除外はされていない

    def test_same_seed_produces_the_same_selection(self):
        # 「同日の再実行で再現性がある」ことの確認（同じseedのrngを渡せば同じ結果）。
        items = self._make_group("食品", 20, "food")
        result1 = ranking.select_top_candidates(
            list(items), target=10, max_per_category=10, rng=random.Random(42)
        )
        result2 = ranking.select_top_candidates(
            list(items), target=10, max_per_category=10, rng=random.Random(42)
        )
        self.assertEqual(
            [i["item_code"] for i in result1],
            [i["item_code"] for i in result2],
        )


if __name__ == "__main__":
    unittest.main()
