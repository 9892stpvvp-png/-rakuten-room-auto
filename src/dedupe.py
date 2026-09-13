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


def remove_within_run_duplicates(
    items: list[dict[str, Any]],
    seen_item_codes: set[str],
) -> list[dict[str, Any]]:
    """同じ実行の中で、複数のキーワード検索にまたがって重複した商品を取り除く。

    seen_item_codes は呼び出し側がキーワードをまたいで使い回すセット。
    このセット自体を更新するため、実行済みのキーワード分がここに蓄積されていく。
    """
    unique_items = []
    for item in items:
        code = item.get("item_code")
        if code in seen_item_codes:
            continue
        seen_item_codes.add(code)
        unique_items.append(item)
    return unique_items
