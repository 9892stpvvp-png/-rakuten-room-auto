"""投稿ページ用データ書き出し（src/publish_room_page.py）の回帰テスト。

実際のファイル入出力の一部（find_latest_candidates_json）は一時ディレクトリを
使ってテストし、データ整形（build_room_page_data）は純粋関数として
テストする。

実行方法:
    python -m unittest tests.test_publish_room_page -v
"""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from src import publish_room_page as pub


def make_candidate(**overrides) -> dict:
    base = {
        "item_code": "shop:item001",
        "name": "テスト商品",
        "price": 1980,
        "review_average": 4.5,
        "review_count": 300,
        "item_url": "https://item.rakuten.co.jp/shop/item001/",
        "image_url": "https://example.com/item001.jpg",
        "description": "🏠 テストのキャッチコピー✨\n\n悩み...\n\n解決◎\n\n✔️ 1\n✔️ 2\n✔️ 3\n\n締め☺️\n\n#タグ",
        "_category": "収納",
    }
    base.update(overrides)
    return base


class BuildRoomPageDataTest(unittest.TestCase):
    def test_includes_expected_fields_without_modifying_description(self):
        description = "🏠 一文字も変えてはいけない紹介文✨\n\n#タグ #タグ2"
        candidate = make_candidate(description=description)
        now_utc = datetime(2026, 9, 14, 6, 30, 0, tzinfo=timezone.utc)

        data = pub.build_room_page_data([candidate], now_utc=now_utc)

        self.assertEqual(len(data["items"]), 1)
        item = data["items"][0]
        self.assertEqual(item["description"], description)
        self.assertEqual(item["item_code"], "shop:item001")
        self.assertEqual(item["name"], "テスト商品")
        self.assertEqual(item["price"], 1980)
        self.assertEqual(item["review_average"], 4.5)
        self.assertEqual(item["review_count"], 300)
        self.assertEqual(item["item_url"], "https://item.rakuten.co.jp/shop/item001/")
        self.assertEqual(item["image_url"], "https://example.com/item001.jpg")
        self.assertEqual(item["category"], "収納")

    def test_generated_at_jst_is_utc_plus_nine(self):
        # 2026-09-14 06:30 UTC = 2026-09-14 15:30 JST。
        now_utc = datetime(2026, 9, 14, 6, 30, 0, tzinfo=timezone.utc)
        data = pub.build_room_page_data([make_candidate()], now_utc=now_utc)
        self.assertEqual(data["generated_at_jst"], "2026/09/14 15:30")

    def test_date_rollover_near_midnight_utc(self):
        # 2026-09-13 23:50 UTC = 2026-09-14 08:50 JST。
        now_utc = datetime(2026, 9, 13, 23, 50, 0, tzinfo=timezone.utc)
        data = pub.build_room_page_data([make_candidate()], now_utc=now_utc)
        self.assertEqual(data["generated_at_jst"], "2026/09/14 08:50")

    def test_limits_to_top_n_items(self):
        candidates = [make_candidate(item_code=f"shop:item{i:03d}") for i in range(15)]
        data = pub.build_room_page_data(candidates, limit=10)
        self.assertEqual(len(data["items"]), 10)

    def test_fewer_than_limit_items_are_all_included(self):
        candidates = [make_candidate(item_code=f"shop:item{i:03d}") for i in range(3)]
        data = pub.build_room_page_data(candidates, limit=10)
        self.assertEqual(len(data["items"]), 3)

    def test_empty_candidates_produces_empty_items(self):
        data = pub.build_room_page_data([])
        self.assertEqual(data["items"], [])

    def test_missing_fields_default_safely(self):
        # 商品データに項目が欠けていても例外にならないことを確認する。
        data = pub.build_room_page_data([{}])
        item = data["items"][0]
        self.assertEqual(item["name"], "")
        self.assertEqual(item["price"], 0)
        self.assertEqual(item["review_average"], 0)
        self.assertEqual(item["review_count"], 0)
        self.assertEqual(item["group_label"], "")

    def test_group_label_is_included_for_room_page_badge(self):
        convenience = make_candidate(item_code="a", _display_group="便利グッズ")
        consumable = make_candidate(item_code="b", _display_group="消耗品")
        beverage = make_candidate(item_code="c", _display_group="飲料")

        data = pub.build_room_page_data([convenience, consumable, beverage])

        labels = [item["group_label"] for item in data["items"]]
        self.assertEqual(labels, ["便利グッズ", "消耗品", "飲料"])

    def test_convenience_and_consumable_counts_are_aggregated(self):
        candidates = (
            [make_candidate(item_code=f"conv{i}", _display_group="便利グッズ") for i in range(5)]
            + [make_candidate(item_code=f"cons{i}", _display_group="消耗品") for i in range(3)]
            + [make_candidate(item_code=f"bev{i}", _display_group="飲料") for i in range(2)]
        )

        data = pub.build_room_page_data(candidates)

        self.assertEqual(data["convenience_count"], 5)
        self.assertEqual(data["consumable_count"], 5)


class FindLatestCandidatesJsonTest(unittest.TestCase):
    def test_returns_none_when_directory_has_no_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self.assertIsNone(pub.find_latest_candidates_json(Path(tmpdir)))

    def test_returns_none_when_directory_does_not_exist(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            missing = Path(tmpdir) / "does_not_exist"
            self.assertIsNone(pub.find_latest_candidates_json(missing))

    def test_picks_the_lexicographically_latest_file(self):
        # ファイル名がタイムスタンプ(candidates_YYYYMMDD_HHMMSS.json)なので、
        # 文字列として最も大きいものが最新になる。
        with tempfile.TemporaryDirectory() as tmpdir:
            directory = Path(tmpdir)
            (directory / "candidates_20260912_153000.json").write_text("[]", encoding="utf-8")
            (directory / "candidates_20260913_153000.json").write_text("[]", encoding="utf-8")
            (directory / "candidates_20260913_140000.json").write_text("[]", encoding="utf-8")

            latest = pub.find_latest_candidates_json(directory)
            assert latest is not None
            self.assertEqual(latest.name, "candidates_20260913_153000.json")

    def test_ignores_non_matching_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            directory = Path(tmpdir)
            (directory / "candidates_20260913_153000.json").write_text("[]", encoding="utf-8")
            (directory / "candidates_20260913_153000.md").write_text("# x", encoding="utf-8")
            (directory / "readme.txt").write_text("x", encoding="utf-8")

            latest = pub.find_latest_candidates_json(directory)
            assert latest is not None
            self.assertEqual(latest.name, "candidates_20260913_153000.json")


class MainAtomicWriteTest(unittest.TestCase):
    """main()がroom/data/candidates.jsonをatomic_io経由で書き出すことの回帰テスト。

    このファイルは投稿ページ（room/index.html）が直接読み込むため、書き込み
    途中でプロセスが終了しても壊れたJSONが残らないことを確認する。
    """

    def _make_candidates_file(self, directory: Path) -> Path:
        candidates_file = directory / "candidates_20260913_153000.json"
        candidates_file.write_text(
            json.dumps([{"item_code": "shop:a", "name": "商品A"}], ensure_ascii=False),
            encoding="utf-8",
        )
        return candidates_file

    def test_writes_room_page_data_successfully(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            candidates_file = self._make_candidates_file(Path(tmpdir))
            room_page_path = Path(tmpdir) / "room" / "data" / "candidates.json"

            with mock.patch.object(
                pub, "find_latest_candidates_json", return_value=candidates_file
            ), mock.patch.object(pub, "ROOM_PAGE_DATA_PATH", room_page_path):
                pub.main()

            saved = json.loads(room_page_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["items"][0]["item_code"], "shop:a")

    def test_existing_file_untouched_and_no_temp_left_when_write_fails(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            candidates_file = self._make_candidates_file(Path(tmpdir))
            room_page_dir = Path(tmpdir) / "room" / "data"
            room_page_dir.mkdir(parents=True)
            room_page_path = room_page_dir / "candidates.json"
            room_page_path.write_text('{"items": []}', encoding="utf-8")

            with mock.patch.object(
                pub, "find_latest_candidates_json", return_value=candidates_file
            ), mock.patch.object(pub, "ROOM_PAGE_DATA_PATH", room_page_path), mock.patch(
                "os.fdopen", side_effect=OSError("disk full")
            ):
                with self.assertRaises(OSError):
                    pub.main()

            self.assertEqual(room_page_path.read_text(encoding="utf-8"), '{"items": []}')
            remaining = list(room_page_dir.iterdir())
            self.assertEqual(remaining, [room_page_path])

    def test_uses_atomic_io_write_json_atomic(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            candidates_file = self._make_candidates_file(Path(tmpdir))
            room_page_path = Path(tmpdir) / "room" / "data" / "candidates.json"

            with mock.patch.object(
                pub, "find_latest_candidates_json", return_value=candidates_file
            ), mock.patch.object(pub, "ROOM_PAGE_DATA_PATH", room_page_path), mock.patch(
                "src.publish_room_page.atomic_io.write_json_atomic",
                wraps=pub.atomic_io.write_json_atomic,
            ) as mocked_write:
                pub.main()

            mocked_write.assert_called_once()


if __name__ == "__main__":
    unittest.main()
