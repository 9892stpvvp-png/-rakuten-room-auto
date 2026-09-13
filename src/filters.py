"""レビュー評価・テーマとの関連性などの条件で商品を絞り込む部分。"""

from __future__ import annotations

from typing import Any


def filter_by_review(
    items: list[dict[str, Any]],
    min_review_average: float,
    min_review_count: int,
) -> list[dict[str, Any]]:
    """レビュー評価とレビュー件数の条件を満たす商品だけを残す。

    広告対象・ポイント倍率・ランキング入賞・SALE・メディア掲載の有無は判定に使わない。
    """
    return [
        item
        for item in items
        if item.get("review_average", 0) >= min_review_average
        and item.get("review_count", 0) >= min_review_count
    ]


def filter_by_ng_keywords(
    items: list[dict[str, Any]],
    ng_keywords: list[str],
) -> list[dict[str, Any]]:
    """福袋・ランダム・訳あり詰め合わせなど、ROOMで紹介しにくい商品を除外する。

    商品名や商品説明にNGワードが含まれているかどうかで簡易的に判定する。
    """
    if not ng_keywords:
        return items
    return [
        item
        for item in items
        if not _contains_any(_searchable_text(item), ng_keywords)
    ]


def filter_by_theme_relevance(
    items: list[dict[str, Any]],
    theme_keywords: list[str],
) -> list[dict[str, Any]]:
    """「暮らしの便利グッズ」というテーマから大きく外れる商品を除外する。

    商品名や商品説明にテーマ関連の言葉が1つも含まれない場合は除外する簡易的な判定。
    """
    if not theme_keywords:
        return items
    return [
        item
        for item in items
        if _contains_any(_searchable_text(item), theme_keywords)
    ]


def _searchable_text(item: dict[str, Any]) -> str:
    return f"{item.get('name', '')} {item.get('catch_copy', '')}"


def _contains_any(text: str, words: list[str]) -> bool:
    return any(word in text for word in words if word)
