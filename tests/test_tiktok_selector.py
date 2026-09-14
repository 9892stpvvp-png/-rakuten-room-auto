"""src/tiktok_selector.py のテスト。

実行方法:
    python -m unittest tests.test_tiktok_selector -v
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src import tiktok_selector


def _make_item(
    item_code: str,
    name: str,
    category: str,
    group_label: str = "便利グッズ",
    review_count: int = 500,
) -> dict:
    return {
        "item_code": item_code,
        "name": name,
        "price": 1000,
        "review_average": 4.5,
        "review_count": review_count,
        "item_url": f"https://item.rakuten.co.jp/shop/{item_code}/",
        "image_url": "",
        "description": "",
        "category": category,
        "group_label": group_label,
    }


TEN_CANDIDATES = [
    _make_item("c1", "tower 収納ラック", "収納", "便利グッズ"),
    _make_item("c2", "キッチン水切りボウル", "キッチン", "便利グッズ"),
    _make_item("c3", "掃除用モップ", "掃除", "便利グッズ"),
    _make_item("c4", "時短調理家電", "時短", "便利グッズ"),
    _make_item("c5", "ドアストッパー", "暮らし全般", "便利グッズ"),
    _make_item("d1", "水 2L 12本", "水", "飲料", review_count=10000),
    _make_item("d2", "トイレットペーパー", "日用品", "消耗品"),
    _make_item("d3", "洗剤ストック", "洗剤", "消耗品"),
    _make_item("d4", "お茶 ペットボトル", "お茶", "飲料"),
    _make_item("d5", "染み抜き剤", "洗剤", "消耗品"),
]


class SelectForTikTokTest(unittest.TestCase):
    def test_selects_exactly_one_item(self):
        result = tiktok_selector.select_for_tiktok(TEN_CANDIDATES, history=[])
        self.assertIn(result.item, TEN_CANDIDATES)
        self.assertIsInstance(result.reason, str)
        self.assertTrue(result.reason)

    def test_raises_when_no_candidates(self):
        with self.assertRaises(ValueError):
            tiktok_selector.select_for_tiktok([], history=[])

    def test_prefers_convenience_group_over_consumable(self):
        # 便利グッズ・優先ジャンル該当なしの1件と、消耗品のみの候補を比較。
        candidates = [
            _make_item("a", "ドアストッパー", "暮らし全般", "便利グッズ", review_count=100),
            _make_item("b", "お水 12本", "水", "飲料", review_count=100),
        ]
        result = tiktok_selector.select_for_tiktok(candidates, history=[])
        self.assertEqual(result.item["item_code"], "a")

    def test_prefers_priority_keyword_categories(self):
        candidates = [
            _make_item("a", "ドアストッパー", "暮らし全般", "便利グッズ"),
            _make_item("b", "キッチン用品", "キッチン", "便利グッズ"),
        ]
        result = tiktok_selector.select_for_tiktok(candidates, history=[])
        self.assertEqual(result.item["item_code"], "b")

    def test_avoids_same_genre_as_recent_history(self):
        # 直近の履歴が「収納」の場合、同じ収納カテゴリの候補より、
        # 別カテゴリの便利グッズ候補が選ばれやすくなる。
        candidates = [
            _make_item("a", "tower 収納ラック", "収納", "便利グッズ"),
            _make_item("b", "掃除用モップ", "掃除", "便利グッズ"),
        ]
        history = [{"date": "2026-09-13", "item_code": "x", "category": "収納", "group_label": "便利グッズ"}]
        result = tiktok_selector.select_for_tiktok(candidates, history=history)
        self.assertEqual(result.item["item_code"], "b")

    def test_does_not_repeat_same_genre_back_to_back_over_multiple_days(self):
        history: list[dict] = []
        picked_categories = []
        for _ in range(5):
            result = tiktok_selector.select_for_tiktok(TEN_CANDIDATES, history=history)
            picked_categories.append(result.item["category"])
            history.append(
                {
                    "date": "2026-09-14",
                    "item_code": result.item["item_code"],
                    "category": result.item["category"],
                    "group_label": result.item["group_label"],
                }
            )
        # 連続する2日が同じカテゴリになっていないことを確認する。
        for i in range(1, len(picked_categories)):
            self.assertNotEqual(picked_categories[i], picked_categories[i - 1])


class HistoryPersistenceTest(unittest.TestCase):
    def test_record_and_load_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tiktok_history.json"
            self.assertEqual(tiktok_selector.load_history(path), [])

            tiktok_selector.record_selection(
                {"date": "2026-09-14", "item_code": "c1", "category": "収納", "group_label": "便利グッズ"},
                path=path,
            )
            history = tiktok_selector.load_history(path)
            self.assertEqual(len(history), 1)
            self.assertEqual(history[0]["item_code"], "c1")

    def test_history_is_truncated_to_keep_last_n(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tiktok_history.json"
            for i in range(5):
                tiktok_selector.record_selection(
                    {"date": f"2026-09-{i:02d}", "item_code": f"c{i}", "category": "収納", "group_label": "便利グッズ"},
                    path=path,
                    keep_last=3,
                )
            history = tiktok_selector.load_history(path)
            self.assertEqual(len(history), 3)
            self.assertEqual([h["item_code"] for h in history], ["c2", "c3", "c4"])

    def test_missing_history_file_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "does_not_exist.json"
            self.assertEqual(tiktok_selector.load_history(path), [])


if __name__ == "__main__":
    unittest.main()
