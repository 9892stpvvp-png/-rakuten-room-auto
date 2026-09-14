"""JSON・テキストファイルを、書き込み途中で壊れた状態を残さない形で保存するための
小さなヘルパー。

通常の`open(path, "w")`＋書き込みは、書き込みの途中でプロセスが強制終了された
場合（GitHub Actionsのジョブタイムアウト・手動キャンセル・予期しないクラッシュ等）、
書きかけの不完全な（壊れた）ファイルがそのまま残ってしまう可能性がある。

ここでは「同じディレクトリに一時ファイルを書き、書き終わってから`os.replace()`で
本来のファイル名に置き換える」という手順にすることで、書き込みが完了しなかった
場合には既存のファイルがそのまま残るようにしている
（`os.replace()`は同一ファイルシステム上ではアトミックな操作であるため、
置き換えの途中で中途半端な内容のファイルが観測されることはない）。

TikTok向けの選定履歴（data/tiktok_history.json）・日次コンテンツ
（tiktok/daily_content.json・tiktok/daily_content.md）の保存で使う。
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def write_text_atomic(path: Path, text: str, encoding: str = "utf-8") -> None:
    """テキストファイルを壊れにくい形で書き出す（書き込み途中の内容が残らない）。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding=encoding) as f:
            f.write(text)
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def write_json_atomic(path: Path, data: Any) -> None:
    """JSONファイルを壊れにくい形で書き出す（内容はensure_ascii=Falseで整形する）。"""
    write_text_atomic(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")
