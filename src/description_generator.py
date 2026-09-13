"""楽天ROOMの紹介文欄にそのままコピペできる紹介文を作る部分。

条件：
- 押し売り感のない自然な日本語
- 実際の商品データ（レビュー評価・件数など）から確認できないことは書かない
- 商品紹介文＋箇条書き（2〜4個）＋ハッシュタグを1つのコピペ用ブロックにする
- 500文字以内
- 同じ定型文を全商品に使い回さない（カテゴリごとに複数の言い回しを用意し、
  商品ごとに変化するデータ（商品コード）に応じてローテーションさせる）
"""

from __future__ import annotations

from typing import Any

DEFAULT_CATEGORY = "暮らし全般"

INTRO_VARIANTS: dict[str, list[str]] = {
    "掃除": [
        "掃除のひと手間を軽くしてくれそうな便利アイテムです。",
        "気になる汚れのお手入れをラクにしてくれそうなアイテムです。",
    ],
    "収納": [
        "収納をすっきり整えたい方に取り入れやすいアイテムです。",
        "散らかりがちな物の整理に役立ちそうなアイテムです。",
    ],
    "キッチン": [
        "キッチンでの作業をちょっとラクにしてくれそうなアイテムです。",
        "毎日の調理や片付けに取り入れやすいアイテムです。",
    ],
    "時短": [
        "毎日のちょっとした時短につながりそうなアイテムです。",
        "忙しい日々の家事をスムーズにしてくれそうなアイテムです。",
    ],
    DEFAULT_CATEGORY: [
        "暮らしを少し快適にしてくれそうな便利アイテムです。",
        "日々のちょっとした不便を解消してくれそうなアイテムです。",
    ],
}

POINT_VARIANTS: dict[str, list[str]] = {
    "掃除": [
        "サッと使えて掃除の手間を減らしやすい",
        "気になる場所のお手入れに取り入れやすい",
        "普段の掃除の流れに組み込みやすい",
    ],
    "収納": [
        "散らかりがちな物をすっきり整理しやすい",
        "限られたスペースを有効に使いやすい",
        "出し入れしやすく続けやすい",
    ],
    "キッチン": [
        "毎日の調理や片付けをスムーズにしやすい",
        "キッチン周りをすっきり保ちやすい",
        "作業スペースを整えやすい",
    ],
    "時短": [
        "日々のちょっとした作業を時短しやすい",
        "忙しい日でも取り入れやすい",
        "手間を減らして自分の時間を増やしやすい",
    ],
    DEFAULT_CATEGORY: [
        "暮らしの中の小さな不便を解消しやすい",
        "毎日の生活に取り入れやすい",
        "気軽に使い始めやすい",
    ],
}

HASHTAG_BY_CATEGORY: dict[str, str] = {
    "掃除": "#掃除グッズ",
    "収納": "#収納",
    "キッチン": "#キッチン便利グッズ",
    "時短": "#時短アイテム",
    DEFAULT_CATEGORY: "#暮らしの便利グッズ",
}


def generate_description(
    item: dict[str, Any],
    category: str,
    base_hashtags: list[str],
    max_length: int = 500,
) -> str:
    """商品情報から、自然な紹介文＋箇条書き＋ハッシュタグの1ブロックを組み立てる。"""
    category = category if category in INTRO_VARIANTS else DEFAULT_CATEGORY

    # 商品ごとに言い回しを変えるための目印（商品コードが無ければ商品名を使う）。
    seed_source = item.get("item_code") or item.get("name", "")
    seed = sum(ord(c) for c in seed_source) if seed_source else 0

    intro_variants = INTRO_VARIANTS[category]
    intro = intro_variants[seed % len(intro_variants)]

    point_variants = POINT_VARIANTS[category]
    point_a = point_variants[seed % len(point_variants)]
    point_b = point_variants[(seed + 1) % len(point_variants)]
    review_point = (
        f"レビュー評価{item.get('review_average', 0):.1f}・"
        f"{item.get('review_count', 0)}件と、実際に使った人からの評価がある"
    )
    points = [point_a, point_b, review_point]

    category_hashtag = HASHTAG_BY_CATEGORY.get(category, "")
    hashtags = list(dict.fromkeys([*base_hashtags, category_hashtag]))
    hashtags = [tag for tag in hashtags if tag]

    bullet_block = "\n".join(f"・{point}" for point in points)
    hashtag_line = " ".join(hashtags)

    description = f"{intro}\n\n{bullet_block}\n\n{hashtag_line}"

    if len(description) > max_length:
        description = description[: max_length - 1].rstrip() + "…"

    return description
