"""候補商品の並び順を決める部分。

- レビュー実績（購入・利用動向の目安）による品質スコアの算出
- 同じカテゴリ内で「用途がほぼ同じ」類似商品を1件に絞り込む
- 上位N件が特定のカテゴリに偏りすぎないようにする
"""

from __future__ import annotations

import difflib
from collections import defaultdict
from typing import Any


def quality_score(item: dict[str, Any]) -> tuple[float, float]:
    """レビュー件数（購入・利用動向の目安）を最優先し、レビュー評価を次点で比較するためのスコア。"""
    return (item.get("review_count", 0), item.get("review_average", 0))


def deduplicate_similar_items(
    items: list[dict[str, Any]],
    similarity_threshold: float = 0.55,
) -> list[dict[str, Any]]:
    """同じカテゴリ内で、商品名が似ている（用途がほぼ同じと思われる）商品をまとめる。

    掃除・収納・キッチンなど別カテゴリの商品は比較対象にしない
    （別カテゴリであれば残してよいという方針のため）。
    グループの中ではレビュー評価・レビュー件数が最も良い1件だけを残す。
    """
    by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        by_category[item.get("_category", "")].append(item)

    result: list[dict[str, Any]] = []
    for group in by_category.values():
        result.extend(_dedupe_group_by_similarity(group, similarity_threshold))
    return result


def _dedupe_group_by_similarity(
    group: list[dict[str, Any]],
    threshold: float,
) -> list[dict[str, Any]]:
    # 品質スコアが高い順に見ていき、すでに採用した商品と名前が似ていたらスキップする。
    ordered = sorted(group, key=quality_score, reverse=True)
    selected: list[dict[str, Any]] = []
    for item in ordered:
        if any(_is_similar_name(item.get("name", ""), s.get("name", ""), threshold) for s in selected):
            continue
        selected.append(item)
    return selected


def _is_similar_name(name_a: str, name_b: str, threshold: float) -> bool:
    if not name_a or not name_b:
        return False
    return difflib.SequenceMatcher(None, name_a, name_b).ratio() >= threshold


def sort_by_quality(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """レビュー件数・レビュー評価が良い順に並べ替える。"""
    return sorted(items, key=quality_score, reverse=True)


def diversify_top(
    items: list[dict[str, Any]],
    top_n: int,
    max_per_category: int,
) -> list[dict[str, Any]]:
    """品質順に並んだ商品の先頭top_n件を、カテゴリが偏りすぎないように選び直す。

    上位に入りきらなかった商品は、そのままの品質順で後ろに続ける
    （Artifactに保存する全件のデータとしては変わらず残る）。
    """
    chosen: list[dict[str, Any]] = []
    chosen_codes: set[str] = set()
    category_counts: dict[str, int] = defaultdict(int)

    # 1st pass: カテゴリごとの上限を守りながら上位を選ぶ
    for item in items:
        if len(chosen) >= top_n:
            break
        category = item.get("_category", "")
        if category_counts[category] < max_per_category:
            chosen.append(item)
            chosen_codes.add(item.get("item_code", ""))
            category_counts[category] += 1

    # 2nd pass: 上限のせいでtop_nに満たない場合、残りから品質順に埋める
    if len(chosen) < top_n:
        for item in items:
            if len(chosen) >= top_n:
                break
            code = item.get("item_code", "")
            if code in chosen_codes:
                continue
            chosen.append(item)
            chosen_codes.add(code)

    rest = [item for item in items if item.get("item_code", "") not in chosen_codes]
    return chosen + rest
