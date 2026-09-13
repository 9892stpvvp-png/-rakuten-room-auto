"""楽天ROOMの紹介文欄にそのままコピペできる紹介文を作る部分。

条件：
- 押し売り感のない自然な日本語
- 商品紹介文＋箇条書き＋ハッシュタグを1つの連続した文章ブロックにする
- 500文字以内
"""

from __future__ import annotations

from typing import Any


def generate_description(
    item: dict[str, Any],
    hashtags: list[str],
    max_length: int = 500,
) -> str:
    """商品情報から紹介文を組み立てる。"""
    name = item.get("name", "").strip()
    catch_copy = (item.get("catch_copy") or "").strip()
    price = item.get("price", 0)

    intro = f"{name}を見つけました。"
    if catch_copy:
        intro += f"{catch_copy}"

    points = [
        "毎日の家事がちょっとラクになるアイテムです",
        f"価格の目安は{price:,}円前後",
        f"レビュー評価{item.get('review_average', 0):.1f}・{item.get('review_count', 0)}件と、実際に使った人からの評判も良いです",
    ]
    bullet_block = " / ".join(f"・{p}" for p in points)

    hashtag_block = " ".join(hashtags)

    description = f"{intro} {bullet_block} {hashtag_block}".strip()

    if len(description) > max_length:
        description = description[: max_length - 1].rstrip() + "…"

    return description
