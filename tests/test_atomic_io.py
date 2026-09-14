"""src/atomic_io.py のテスト。

実行方法:
    python -m unittest tests.test_atomic_io -v
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src import atomic_io


class WriteTextAtomicTest(unittest.TestCase):
    def test_writes_new_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.txt"
            atomic_io.write_text_atomic(path, "こんにちは")
            self.assertEqual(path.read_text(encoding="utf-8"), "こんにちは")

    def test_overwrites_existing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.txt"
            path.write_text("古い内容", encoding="utf-8")
            atomic_io.write_text_atomic(path, "新しい内容")
            self.assertEqual(path.read_text(encoding="utf-8"), "新しい内容")

    def test_creates_missing_parent_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested" / "out.txt"
            atomic_io.write_text_atomic(path, "content")
            self.assertEqual(path.read_text(encoding="utf-8"), "content")

    def test_no_leftover_temp_files_after_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.txt"
            atomic_io.write_text_atomic(path, "content")
            remaining = list(Path(tmp).iterdir())
            self.assertEqual(remaining, [path])

    def test_original_file_untouched_and_no_temp_left_when_write_fails(self):
        # 書き込み途中で例外が起きても、既存のファイルが壊れた状態で
        # 残らない（元の内容のまま）ことと、一時ファイルが残らないことを確認する。
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.txt"
            path.write_text("元の内容", encoding="utf-8")

            with mock.patch("os.fdopen", side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    atomic_io.write_text_atomic(path, "書き込めないはずの内容")

            self.assertEqual(path.read_text(encoding="utf-8"), "元の内容")
            remaining = list(Path(tmp).iterdir())
            self.assertEqual(remaining, [path])


class WriteJsonAtomicTest(unittest.TestCase):
    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.json"
            data = {"history": [{"item_code": "c1", "category": "収納"}]}
            atomic_io.write_json_atomic(path, data)
            loaded = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(loaded, data)

    def test_writes_with_ensure_ascii_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.json"
            atomic_io.write_json_atomic(path, {"name": "掃除グッズ"})
            raw = path.read_text(encoding="utf-8")
            self.assertIn("掃除グッズ", raw)


if __name__ == "__main__":
    unittest.main()
