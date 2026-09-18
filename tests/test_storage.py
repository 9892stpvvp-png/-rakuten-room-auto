"""投稿候補一覧の保存（src/storage.py）の回帰テスト。

実行方法:
    python -m unittest tests.test_storage -v
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src import storage


def make_candidate(**overrides) -> dict:
    base = {
        "item_code": "shop:item001",
        "name": "テスト商品",
        "price": 1980,
        "review_average": 4.5,
        "review_count": 300,
        "item_url": "https://item.rakuten.co.jp/shop/item001/",
        "image_url": "https://example.com/item001.jpg",
        "description": "紹介文",
        "shop_name": "テストショップ",
    }
    base.update(overrides)
    return base


class SaveCandidatesTest(unittest.TestCase):
    def test_saves_json_and_markdown_and_returns_their_paths(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            candidates = [make_candidate()]

            json_path, markdown_path = storage.save_candidates(candidates, output_dir)

            self.assertTrue(json_path.exists())
            self.assertTrue(markdown_path.exists())
            saved = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(saved, candidates)
            self.assertIn("テスト商品", markdown_path.read_text(encoding="utf-8"))

    def test_creates_missing_output_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "nested" / "candidates"
            json_path, markdown_path = storage.save_candidates([make_candidate()], output_dir)
            self.assertTrue(json_path.exists())
            self.assertTrue(markdown_path.exists())


class SaveCandidatesAtomicWriteTest(unittest.TestCase):
    """書き込み途中で例外が起きても、既存のcandidates_*.jsonが壊れた状態で
    残らないことを確認する（atomic_io経由での保存の回帰テスト）。

    publish_room_page.pyのfind_latest_candidates_json()は「最も新しい
    candidates_*.json」をそのまま読み込むため、壊れかけのファイルが残ると
    後段の投稿ページ生成が壊れたデータを読み込んでしまう。
    """

    def test_no_partial_json_file_left_when_write_fails(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            with mock.patch("os.fdopen", side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    storage.save_candidates([make_candidate()], output_dir)

            remaining = list(output_dir.iterdir())
            self.assertEqual(remaining, [])

    def test_uses_atomic_io_for_json_and_markdown(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            with mock.patch(
                "src.storage.atomic_io.write_json_atomic", wraps=storage.atomic_io.write_json_atomic
            ) as mocked_json, mock.patch(
                "src.storage.atomic_io.write_text_atomic", wraps=storage.atomic_io.write_text_atomic
            ) as mocked_text:
                storage.save_candidates([make_candidate()], output_dir)
            # write_json_atomic()は内部でwrite_text_atomic()を呼ぶため、
            # write_text_atomicはJSON分とMarkdown分の合計2回呼ばれる。
            mocked_json.assert_called_once()
            self.assertEqual(mocked_text.call_count, 2)


if __name__ == "__main__":
    unittest.main()
