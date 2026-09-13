"""レビュー評価・レビュー件数などの条件で商品を絞り込む部分。"""

from __future__ import annotations

from typing import Any


def filter_by_review(
    items: list[dict[str, Any]],
    min_review_average: float,
    min_review_count: int,
) -> list[dict[str, Any]]:
    """レビュー評価とレビュー件数の条件を満たす商品だけを残す。

    広告対象・ポイント倍率・ランキング入賞・メディア掲載の有無は判定に使わない。
    """
    return [
        item
        for item in items
        if item.get("review_average", 0) >= min_review_average
        and item.get("review_count", 0) >= min_review_count
    ]
