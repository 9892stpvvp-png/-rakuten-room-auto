"""過去に紹介した商品との重複をチェックする部分。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_posted_item_codes(path: Path) -> set[str]:
    """過去に投稿した商品コードの一覧を読み込む。ファイルが無ければ空とみなす。"""
    if not path.exists():
        return set()

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    return set(data.get("posted_item_codes", []))


def remove_duplicates(
    items: list[dict[str, Any]],
    posted_item_codes: set[str],
) -> list[dict[str, Any]]:
    """過去に投稿済みの商品を候補から取り除く。"""
    return [item for item in items if item.get("item_code") not in posted_item_codes]
