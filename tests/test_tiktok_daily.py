"""src/tiktok_daily.py の統合テスト。

room/data/candidates.json → TikTokコンテンツ生成 → tiktok/daily_content.json
／tiktok/daily_content.md への書き出し、という一連の流れと、ROOM候補生成が
失敗した場合（room/data/candidates.jsonが無い・候補が0件）に不完全な
データを作らないことを確認する。

実行方法:
    python -m unittest tests.test_tiktok_daily -v
"""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from src import tiktok_daily


def _make_room_page_data(num_items: int = 10) -> dict:
    items = []
    for i in range(num_items):
        group = "便利グッズ" if i < 5 else ("飲料" if i % 2 == 0 else "消耗品")
        category = ["収納", "キッチン", "掃除", "時短", "暮らし全般"][i % 5] if i < 5 else "日用品"
        items.append(
            {
                "item_code": f"shop:item{i}",
                "name": f"テスト商品{i} 便利グッズ",
                "price": 1000 + i,
                "review_average": 4.5,
                "review_count": 300 + i,
                "item_url": f"https://item.rakuten.co.jp/shop/item{i}/",
                "image_url": f"https://example.com/item{i}.jpg",
                "description": "",
                "category": category,
                "group_label": group,
            }
        )
    return {
        "generated_at_jst": "2026/09/14 18:43",
        "items": items,
        "convenience_count": 5,
        "consumable_count": 5,
    }


class LoadRoomCandidatesTest(unittest.TestCase):
    def test_raises_when_file_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "does_not_exist.json"
            with self.assertRaises(SystemExit):
                tiktok_daily.load_room_candidates(path)

    def test_raises_when_items_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "candidates.json"
            path.write_text(json.dumps({"items": []}), encoding="utf-8")
            with self.assertRaises(SystemExit):
                tiktok_daily.load_room_candidates(path)

    def test_loads_items_when_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "candidates.json"
            data = _make_room_page_data()
            path.write_text(json.dumps(data), encoding="utf-8")
            items = tiktok_daily.load_room_candidates(path)
            self.assertEqual(len(items), 10)


class BuildDailyContentTest(unittest.TestCase):
    def test_output_contains_required_schema_fields(self):
        data = _make_room_page_data()
        result = tiktok_daily.build_daily_content(
            data["items"], history=[], now_utc=datetime(2026, 9, 14, 9, 30, tzinfo=timezone.utc)
        )
        for key in (
            "generated_at",
            "product_name",
            "item_code",
            "item_url",
            "selection_reason",
            "script",
            "telops",
            "narration",
            "caption",
            "hashtags",
            "video_notes",
        ):
            self.assertIn(key, result)

        self.assertTrue(result["generated_at"].startswith("2026-09-14T18:30:00"))
        self.assertTrue(result["product_name"])
        self.assertIsInstance(result["telops"], list)
        self.assertIsInstance(result["hashtags"], list)
        self.assertIsInstance(result["video_notes"], list)

    def test_json_round_trip_is_safe(self):
        data = _make_room_page_data()
        result = tiktok_daily.build_daily_content(data["items"], history=[])
        # 日本語を含んでいてもjson.dumpsでそのままシリアライズできることを確認する
        # （ensure_ascii=Falseで書き出す実装のため、往復させても情報が失われない）。
        encoded = json.dumps(result, ensure_ascii=False)
        decoded = json.loads(encoded)
        self.assertEqual(decoded["product_name"], result["product_name"])


class MainEndToEndTest(unittest.TestCase):
    def test_writes_json_and_markdown_without_touching_room_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            room_data_path = tmp_path / "room" / "data" / "candidates.json"
            room_data_path.parent.mkdir(parents=True)
            original_room_data = _make_room_page_data()
            room_data_path.write_text(
                json.dumps(original_room_data, ensure_ascii=False), encoding="utf-8"
            )

            tiktok_json_path = tmp_path / "tiktok" / "daily_content.json"
            tiktok_md_path = tmp_path / "tiktok" / "daily_content.md"
            history_path = tmp_path / "data" / "tiktok_history.json"

            original_room_data_path = tiktok_daily.ROOM_PAGE_DATA_PATH
            original_json_path = tiktok_daily.TIKTOK_JSON_PATH
            original_md_path = tiktok_daily.TIKTOK_MARKDOWN_PATH
            original_dir = tiktok_daily.TIKTOK_DIR

            from src import tiktok_selector

            original_history_path = tiktok_selector.TIKTOK_HISTORY_PATH

            try:
                tiktok_daily.ROOM_PAGE_DATA_PATH = room_data_path
                tiktok_daily.TIKTOK_JSON_PATH = tiktok_json_path
                tiktok_daily.TIKTOK_MARKDOWN_PATH = tiktok_md_path
                tiktok_daily.TIKTOK_DIR = tiktok_json_path.parent
                tiktok_selector.TIKTOK_HISTORY_PATH = history_path

                tiktok_daily.main()

                self.assertTrue(tiktok_json_path.exists())
                self.assertTrue(tiktok_md_path.exists())
                self.assertTrue(history_path.exists())

                # ROOM側のデータ（既存機能）は一切変更されていないことを確認する。
                room_data_after = json.loads(room_data_path.read_text(encoding="utf-8"))
                self.assertEqual(room_data_after, original_room_data)

                output = json.loads(tiktok_json_path.read_text(encoding="utf-8"))
                self.assertTrue(output["product_name"])
                self.assertIn("楽天ROOMに載せています", output["script"])

                markdown = tiktok_md_path.read_text(encoding="utf-8")
                self.assertIn("# 今日のTikTok投稿コンテンツ", markdown)
                self.assertIn(output["product_name"], markdown)
            finally:
                tiktok_daily.ROOM_PAGE_DATA_PATH = original_room_data_path
                tiktok_daily.TIKTOK_JSON_PATH = original_json_path
                tiktok_daily.TIKTOK_MARKDOWN_PATH = original_md_path
                tiktok_daily.TIKTOK_DIR = original_dir
                tiktok_selector.TIKTOK_HISTORY_PATH = original_history_path

    def test_main_exits_without_writing_when_room_data_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            room_data_path = tmp_path / "room" / "data" / "candidates.json"  # 実際には作らない
            tiktok_json_path = tmp_path / "tiktok" / "daily_content.json"

            original_room_data_path = tiktok_daily.ROOM_PAGE_DATA_PATH
            original_json_path = tiktok_daily.TIKTOK_JSON_PATH

            try:
                tiktok_daily.ROOM_PAGE_DATA_PATH = room_data_path
                tiktok_daily.TIKTOK_JSON_PATH = tiktok_json_path

                with self.assertRaises(SystemExit):
                    tiktok_daily.main()

                self.assertFalse(tiktok_json_path.exists())
            finally:
                tiktok_daily.ROOM_PAGE_DATA_PATH = original_room_data_path
                tiktok_daily.TIKTOK_JSON_PATH = original_json_path


if __name__ == "__main__":
    unittest.main()
