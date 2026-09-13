"""楽天ROOMの紹介文欄にそのままコピペできる紹介文を作る部分。

条件：
- 押し売り感のない自然な日本語
- 実際の商品データ（商品名・レビュー評価など）から確認できないことは書かない
  （実際に使用したかのような表現や断定的な効果は書かない）
- 商品紹介文＋箇条書き（2〜4個）＋ハッシュタグを1つのコピペ用ブロックにする
- 500文字以内
- 同じ定型文を全商品に使い回さない。商品名に明記されている特徴
  （マグネット式、折りたたみ式など）があれば優先して使い、確実に読み取れない
  場合は無理に特徴を作らず、カテゴリ共通の安全な言い回しで補う

注意（特徴抽出に商品説明・itemCaptionを使わない理由）：
当初は商品説明（itemCaption）の最初の一文も検出対象にしていたが、実際の
楽天ウェブサービスのレスポンスを確認したところ、次のような問題が見つかった。

1. 商品説明が句点（。）を含まない仕様一覧形式（「素材/材質：エラストマー、
   ステンレス、…」等）のことがあり、「最初の一文」のつもりが説明文全体を
   拾ってしまい、製品の一部品の素材などを商品全体の特徴として誤って
   拾ってしまう
2. まれに、その商品とは無関係な説明文がそのまま入っている（別商品の
   説明文が誤って使われているとみられるケースがあった）

そのため、特徴語の検出は「商品名」だけに限定している。商品名は出品者自身が
検索されるために正確に書くことが多く、上記のような混入が起きにくいため。
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

# 商品名にこれらの言葉が含まれていれば、そのカテゴリに合っているとみなす。
# 検索キーワードから割り当てたカテゴリが商品の実際の内容と合わないことがある
# （例：「衣類圧縮袋」が掃除キーワードの検索結果に混ざる）ため、
# 商品名から見て明らかに別カテゴリだと分かる場合はそちらを優先する。
#
# 「掃除」カテゴリには、商品自体が掃除道具だと言い切れる具体的な言葉だけを入れている
# （「クリーナー」「ワイパー」「ブラシ」「モップ」「掃除機」等）。「掃除」という
# 言葉自体は、「掃除機不要」（収納・便利グッズによくある宣伝文句）のように、
# 掃除道具ではない商品にも頻繁に登場するため、キーワードには含めていない。
CATEGORY_NAME_KEYWORDS: dict[str, list[str]] = {
    "掃除": ["クリーナー", "モップ", "ワイパー", "洗剤", "ブラシ", "雑巾", "掃除機"],
    "収納": [
        "収納", "収納袋", "整理", "ケース", "ボックス", "ラック", "圧縮袋", "オーガナイザー",
        "仕切り", "クローゼット", "ハンガー", "ポーチ", "フック", "ホルダー", "吊り下げ",
        "浮かせる収納",
    ],
    "キッチン": ["キッチン", "調理", "食器", "鍋", "フライパン", "まな板", "水切り", "保存容器"],
    "時短": ["時短", "家電", "スチーマー"],
}

# 商品名に含まれていても判定に使わない言い回し（キーワードを打ち消す表現）。
# 例：「掃除機不要」は『掃除機』を含むが、掃除道具ではないことを意味する宣伝文句のため、
# キーワード一致の判定前にこの部分を取り除く。
NEGATED_PHRASES: list[str] = ["掃除機不要"]


def refine_category(item: dict[str, Any], assigned_category: str) -> str:
    """検索キーワードから割り当てたカテゴリを、商品名から見て適切なものに補正する。

    商品名に含まれる各カテゴリのキーワード数を数え、最も多く一致したカテゴリを
    採用する（単に「1つでも一致すれば元のカテゴリのまま」という判定だと、
    「収納」の言葉を多く含む商品でも、掃除カテゴリのキーワードが1つでもあれば
    掃除カテゴリのままになってしまうため、件数で比較する）。
    最多一致が複数カテゴリで同点の場合は、元のカテゴリを優先する。
    どのカテゴリのキーワードにも一致しない場合は、元のカテゴリのまま
    （暮らし全般などはそのまま）。
    """
    name = item.get("name", "")
    for phrase in NEGATED_PHRASES:
        name = name.replace(phrase, "")

    match_counts = {
        category: sum(1 for keyword in keywords if keyword in name)
        for category, keywords in CATEGORY_NAME_KEYWORDS.items()
    }
    match_counts = {category: count for category, count in match_counts.items() if count > 0}

    if not match_counts:
        return assigned_category

    best_count = max(match_counts.values())
    best_categories = [category for category, count in match_counts.items() if count == best_count]

    if assigned_category in best_categories:
        return assigned_category
    return best_categories[0]


def _contains_any(text: str, words: list[str]) -> bool:
    return any(word in text for word in words if word)


# 商品名から検出できたときだけ使う、商品の設計・仕様に関する具体的な言い回し。
# 検出したキーワードそのものではなく、商品情報から読み取れる客観的な特徴
# （構造・素材・使い方）だけを表す表現にとどめ、効果や体験談は含めない。
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

    feature_points = _feature_hint_points(item.get("name", "") or "", max_hints=2)

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
    """商品名から、具体的な特徴の言い回しを検出する。"""
    matched: list[str] = []
    for keyword, phrase in FEATURE_HINTS:
        if keyword in searchable_text and phrase not in matched:
            matched.append(phrase)
        if len(matched) >= max_hints:
            break
    return matched
