"""楽天ROOMの紹介文欄にそのままコピペできる紹介文を作る部分。

条件：
- 押し売り感のない自然な日本語
- 実際の商品データ（商品名・キャッチコピー・商品説明・レビュー評価など）から
  確認できないことは書かない（実際に使用したかのような表現や断定的な効果は書かない）
- 商品紹介文＋箇条書き（2〜4個）＋ハッシュタグを1つのコピペ用ブロックにする
- 500文字以内
- 同じ定型文を全商品に使い回さない。商品名・キャッチコピー・商品説明から
  読み取れる特徴（マグネット式、折りたたみ式など）があれば優先して使い、
  読み取れない場合のみカテゴリ共通の言い回しで補う
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

# 商品名・キャッチコピー・商品説明から検出できたときだけ使う、商品の設計・仕様に関する
# 具体的な言い回し。検出したキーワードそのものではなく、商品情報から読み取れる
# 客観的な特徴（構造・素材・使い方）だけを表す表現にとどめ、効果や体験談は含めない。
FEATURE_HINTS: list[tuple[str, str]] = [
    ("マグネット", "マグネットで浮かせて設置できるタイプ"),
    ("吸盤", "吸盤で好きな場所に取り付けられるタイプ"),
    ("吊り下げ", "吊り下げて収納できるタイプ"),
    ("突っ張り", "つっぱり棒式で取り付けやすいタイプ"),
    ("折りたた", "使わないときはコンパクトに折りたためる"),
    ("折り畳み", "使わないときはコンパクトに折りたためる"),
    ("水切り", "水切りしやすい設計"),
    ("防水", "水回りでも使いやすい防水仕様"),
    ("スリム", "省スペースに置きやすいスリム設計"),
    ("大容量", "たっぷり収納できる大容量タイプ"),
    ("軽量", "持ち運びしやすい軽量設計"),
    ("シリコン", "お手入れしやすいシリコン素材"),
    ("ステンレス", "サビに強いステンレス製"),
    ("蓋付き", "ホコリを防ぎやすい蓋付きタイプ"),
    ("フタ付き", "ホコリを防ぎやすい蓋付きタイプ"),
    ("透明", "中身が見えてわかりやすいタイプ"),
    ("引き出し", "引き出し式で取り出しやすい"),
    ("自立", "自立するので置き場所を選びにくい"),
    ("食洗機", "食洗機に対応しているタイプ"),
    ("電子レンジ", "電子レンジに対応しているタイプ"),
    ("充電式", "繰り返し使える充電式タイプ"),
    ("コードレス", "コードレスで扱いやすいタイプ"),
]


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

    searchable_text = (
        f"{item.get('name', '')} {item.get('catch_copy', '')} {item.get('item_caption', '')}"
    )
    feature_points = _feature_hint_points(searchable_text, max_hints=2)

    point_variants = POINT_VARIANTS[category]
    idx = seed
    while len(feature_points) < 2:
        candidate = point_variants[idx % len(point_variants)]
        if candidate not in feature_points:
            feature_points.append(candidate)
        idx += 1

    review_point = (
        f"レビュー評価{item.get('review_average', 0):.1f}・"
        f"{item.get('review_count', 0)}件と、実際に使った人からの評価がある"
    )
    points = [*feature_points, review_point]

    category_hashtag = HASHTAG_BY_CATEGORY.get(category, "")
    hashtags = list(dict.fromkeys([*base_hashtags, category_hashtag]))
    hashtags = [tag for tag in hashtags if tag]

    bullet_block = "\n".join(f"・{point}" for point in points)
    hashtag_line = " ".join(hashtags)

    description = f"{intro}\n\n{bullet_block}\n\n{hashtag_line}"

    if len(description) > max_length:
        description = description[: max_length - 1].rstrip() + "…"

    return description


def _feature_hint_points(searchable_text: str, max_hints: int) -> list[str]:
    """商品名・キャッチコピー・商品説明から、具体的な特徴の言い回しを検出する。"""
    matched: list[str] = []
    for keyword, phrase in FEATURE_HINTS:
        if keyword in searchable_text and phrase not in matched:
            matched.append(phrase)
        if len(matched) >= max_hints:
            break
    return matched
