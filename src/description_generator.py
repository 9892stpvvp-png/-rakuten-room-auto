"""楽天ROOMの紹介文欄にそのままコピペできる紹介文を作る部分。

条件：
- 箇条書き（・）は使わず、2〜3文程度の自然な文章にする
- 押し売り感のない自然な日本語。「〜できそう」「〜に便利そう」「〜したい人に
  おすすめ」など、実際に使用していない立場でも不自然にならない表現を使う
- 「使ってみました」「買ってよかった」など、実際に使用したと誤解される
  表現は使わない
- 実際の商品データ（商品名など）から確認できないことは書かない
- 絵文字は文章の終わりなど意味の合う場所に自然に入れる（各行の先頭に機械的に
  付けない）。1投稿あたり2〜4個程度、😊✨♪なども使い楽天ROOMらしい柔らかい
  雰囲気にする。商品と関係のない絵文字は使わない
- レビュー評価・レビュー件数は紹介文の本文には原則含めない
  （候補一覧には別項目として表示される）
- ハッシュタグは3〜5個程度、商品に合ったものを自動生成する。
  「#暮らしの便利グッズ」は基本的に入れる。ハッシュタグには絵文字を付けない
- 500文字以内
- 同じ定型文を全商品に使い回さない。商品名に明記されている特徴
  （マグネット式、折りたたみ式など）があれば優先して文章に組み込み、
  確実に読み取れない場合は無理に特徴を作らず、カテゴリ共通の安全な
  言い回しで補う

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

# 導入文・箇条書きの絵文字をここから選ぶ。カテゴリに合う絵文字に加えて、
# 楽天ROOMらしい柔らかい雰囲気を出すための絵文字（😊✨♪）をどのカテゴリでも
# 使えるようにしている。商品ごとにローテーションさせることで「自然に選べる」
# ようにしている。
CATEGORY_EMOJIS: dict[str, list[str]] = {
    "掃除": ["🧹", "🧽", "✨", "😊", "♪"],
    "収納": ["🧺", "🧲", "🧴", "📦", "✨", "😊", "♪"],
    "キッチン": ["🍳", "🥣", "🥄", "✨", "😊", "♪"],
    "時短": ["⏱️", "⚡", "🍳", "✨", "😊", "♪"],
    DEFAULT_CATEGORY: ["🏠", "✨", "💡", "😊", "♪"],
}

# 特徴が見つからなかったときに文の主語として使う、カテゴリを表す名詞。
CATEGORY_NOUNS: dict[str, str] = {
    "掃除": "掃除グッズ",
    "収納": "収納グッズ",
    "キッチン": "キッチングッズ",
    "時短": "時短家電",
    DEFAULT_CATEGORY: "便利グッズ",
}

# 上のCATEGORY_NOUNSと同じ言葉が特徴の文言と重複しないようにするための、
# カテゴリごとの中心となる言葉（例："収納できる"+"収納グッズ"のような
# 重複を避けるために使う）。
_CATEGORY_NOUN_CORE: dict[str, str] = {
    "掃除": "掃除",
    "収納": "収納",
    "キッチン": "キッチン",
    "時短": "時短",
    DEFAULT_CATEGORY: "便利",
}

# 「暮らし全般」は基本ハッシュタグの「#暮らしの便利グッズ」と重複しないよう、
# 別のハッシュタグを割り当てている（重複すると、サブトピックに一致しない商品では
# ハッシュタグが2個（#暮らしの便利グッズ + #便利グッズ）しか付かなくなってしまうため）。
HASHTAG_BY_CATEGORY: dict[str, str] = {
    "掃除": "#掃除グッズ",
    "収納": "#収納",
    "キッチン": "#キッチン便利グッズ",
    "時短": "#時短アイテム",
    DEFAULT_CATEGORY: "#暮らし雑貨",
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


def _resolve_by_category(value: str | dict[str, str], category: str) -> str:
    """固定文言、またはカテゴリ別の辞書から、カテゴリに応じた値を選ぶ。"""
    if isinstance(value, dict):
        return value.get(category, value.get(DEFAULT_CATEGORY, ""))
    return value


# 商品名から検出できたときだけ使う、商品の設計・仕様に関する具体的な特徴の
# 「節」（あとに名詞を直接続けられる形。例：「マグネットで浮かせて設置できる」＋
# 「収納グッズです」）と、それに添える絵文字。検出したキーワードそのものではなく、
# 商品情報から読み取れる客観的な特徴（構造・素材・使い方）だけを表す表現にとどめ、
# 効果や体験談は含めない。
#
# 文言・絵文字はどちらも、基本は固定値（str）だが、カテゴリによって自然な表現が
# 変わるもの（例：「大容量」は収納用品なら「収納できる」だが、調理家電なら
# 「調理しやすい」）は、カテゴリ名をキーにした辞書（dict）で指定できる。
FEATURE_CLAUSES: list[tuple[str, str | dict[str, str], str | dict[str, str]]] = [
    ("マグネット", "マグネットで浮かせて設置できる", "🧲"),
    ("吸盤", "吸盤で好きな場所に取り付けられる", "🧲"),
    (
        "吊り下げ",
        {
            "収納": "吊り下げて収納できる",
            DEFAULT_CATEGORY: "吊り下げて使える",
        },
        "🪝",
    ),
    ("突っ張り", "つっぱり棒式で取り付けやすい", "📏"),
    ("折りたた", "使わないときはコンパクトに折りたためる", "📦"),
    ("折り畳み", "使わないときはコンパクトに折りたためる", "📦"),
    ("水切り", "水切りしやすい", "💧"),
    ("防水", "水回りでも使いやすい", "☔"),
    ("スリム", "省スペースに置きやすい", "📏"),
    (
        "大容量",
        {
            "収納": "たっぷり収納できる",
            "キッチン": "一度にたっぷり調理しやすい",
            "時短": "一度にたっぷり使える",
            "掃除": "一度にたっぷり集められる",
            DEFAULT_CATEGORY: "たっぷり使える",
        },
        {
            "収納": "✨",
            "キッチン": "🍳",
            "時短": "⏱️",
            "掃除": "🧹",
            DEFAULT_CATEGORY: "💡",
        },
    ),
    ("軽量", "持ち運びしやすい", "🪶"),
    ("シリコン", "シリコン製で洗いやすい", "🧴"),
    ("ステンレス", "サビに強い", "🔩"),
    ("蓋付き", "フタ付きでホコリを防ぎやすい", "📦"),
    ("フタ付き", "フタ付きでホコリを防ぎやすい", "📦"),
    ("引き出し", "引き出し式で取り出しやすい", "📦"),
    ("自立", "自立して置き場所を選びにくい", "📦"),
    ("食洗機", "食洗機で洗える", "🍽️"),
    ("電子レンジ", "電子レンジで使える", "🍽️"),
    ("充電式", "充電式で繰り返し使える", "⚡"),
    ("コードレス", "コードレスで扱いやすい", "⚡"),
]

# 特徴が見つからなかったときに使う、導入文（1文目）のカテゴリ共通の言い回し。
OPENING_FALLBACK_SENTENCES: dict[str, list[str]] = {
    "掃除": [
        "汚れが気になる場所のお手入れに使えそうな掃除グッズです",
        "普段の掃除をちょっとラクにしてくれそうなアイテムです",
    ],
    "収納": [
        "散らかりがちな物をすっきりまとめられそうな収納グッズです",
        "収納スペースを有効に使えそうな便利アイテムです",
    ],
    "キッチン": [
        "キッチンでの作業をスムーズにしてくれそうなキッチングッズです",
        "毎日の調理や片付けに取り入れやすそうなアイテムです",
    ],
    "時短": [
        "日々のちょっとした作業を時短できそうなアイテムです",
        "忙しい日にも取り入れやすそうな時短家電です",
    ],
    DEFAULT_CATEGORY: [
        "暮らしをちょっと快適にしてくれそうな便利グッズです",
        "日々の小さな不便を解消してくれそうなアイテムです",
    ],
}

# 2文目：ためらいのない断定を避けた、やわらかい「おすすめ・メリット」の一文。
BENEFIT_SENTENCES: dict[str, list[str]] = {
    "掃除": [
        "気になる汚れをサッと落とせそうで、お手入れの時間を短くできそうです",
        "お手入れの手間を減らしたい人におすすめしたい掃除グッズです",
        "毎日のちょっとした掃除がラクになりそうです",
    ],
    "収納": [
        "取り出しやすくて、お部屋がスッキリ見えそうです",
        "毎日の片付けをラクにしたい人におすすめしたい収納グッズです",
        "散らかりがちな物をまとめて、すっきり整理できそうです",
    ],
    "キッチン": [
        "取り出しやすくて、キッチンがスッキリ見えそうです",
        "毎日の料理や後片付けをラクにしたい人におすすめです",
        "キッチン周りをすっきり整えたい人に便利そうです",
    ],
    "時短": [
        "忙しい日の家事を少しでもラクにしたい人におすすめです",
        "毎日のちょっとした手間を減らせそうです",
        "時間に追われがちな日にも取り入れやすそうです",
    ],
    DEFAULT_CATEGORY: [
        "暮らしのちょっとした不便を解消したい人におすすめです",
        "毎日の生活に取り入れやすそうなアイテムです",
        "ちょっとした場面で役立ちそうです",
    ],
}

# 3文目（付くこともある）：カテゴリ共通の、やわらかい締めの一文。
CLOSING_SENTENCES: list[str] = [
    "暮らしをちょっとラクにしてくれる便利グッズです",
    "気になる方はチェックしてみてほしいアイテムです",
    "毎日にちょっとした余裕をプラスしてくれそうです",
]

# 商品名にこれらの言葉が含まれる場合、より具体的なハッシュタグを1つ追加する。
SUBTOPIC_HASHTAGS: list[tuple[str, str | dict[str, str]]] = [
    ("お風呂", {"掃除": "#お風呂掃除", "収納": "#お風呂収納", DEFAULT_CATEGORY: "#お風呂グッズ"}),
    ("浴室", {"掃除": "#お風呂掃除", "収納": "#お風呂収納", DEFAULT_CATEGORY: "#お風呂グッズ"}),
    ("バスルーム", {"掃除": "#お風呂掃除", "収納": "#お風呂収納", DEFAULT_CATEGORY: "#お風呂グッズ"}),
    ("キッチン", {"収納": "#キッチン収納", "掃除": "#キッチン掃除", DEFAULT_CATEGORY: "#キッチングッズ"}),
    ("トイレ", {"掃除": "#トイレ掃除", "収納": "#トイレ収納", DEFAULT_CATEGORY: "#トイレグッズ"}),
    ("クローゼット", "#クローゼット収納"),
    ("玄関", "#玄関収納"),
    ("旅行", "#トラベルグッズ"),
    ("トラベル", "#トラベルグッズ"),
]


def generate_description(
    item: dict[str, Any],
    category: str,
    base_hashtags: list[str],
    max_length: int = 500,
) -> str:
    """商品情報から、箇条書きを使わない自然な文章＋ハッシュタグの1ブロックを組み立てる。

    2〜3文程度の文章に、文末など自然な位置に絵文字を添える
    （1投稿あたり2〜4個程度）。レビュー評価・件数は本文に含めない。
    """
    category = category if category in CATEGORY_NOUNS else DEFAULT_CATEGORY
    name = item.get("name", "") or ""

    # 商品ごとに言い回しを変えるための目印（商品コードが無ければ商品名を使う）。
    seed_source = item.get("item_code") or name
    seed = sum(ord(c) for c in seed_source) if seed_source else 0

    sentence1_text, sentence1_emoji = _build_sentence1(name, category, seed)
    benefit_variants = BENEFIT_SENTENCES[category]
    sentence2_text = benefit_variants[(seed // 3) % len(benefit_variants)]
    pool = CATEGORY_EMOJIS[category]
    sentence2_emoji = pool[(seed // 3 + 1) % len(pool)]

    parts = [(sentence1_text, sentence1_emoji), (sentence2_text, sentence2_emoji)]

    # 3文になることもある（2〜3文程度、のバリエーションを出すため）。
    if seed % 3 == 0:
        closing_text = CLOSING_SENTENCES[seed % len(CLOSING_SENTENCES)]
        closing_emoji = pool[(seed // 5 + 2) % len(pool)]
        parts.append((closing_text, closing_emoji))

    parts = _dedupe_adjacent_emojis(parts, pool)

    # 最初の文に、余韻を添える2つ目の絵文字を付けることがある
    # （例：「🛁✨」のように文末に絵文字を2つ重ねる、楽天ROOMでよくある表現）。
    used_emojis = {emoji for _text, emoji in parts}
    lines = []
    for i, (text, emoji) in enumerate(parts):
        line = f"{text}{emoji}"
        if i == 0 and seed % 10 < 3:
            # 文章全体（他の文で使う分も含めて）で被らない絵文字だけを候補にする。
            bonus_pool = [e for e in pool if e not in used_emojis]
            if bonus_pool:
                bonus = bonus_pool[(seed // 7) % len(bonus_pool)]
                line += bonus
                used_emojis.add(bonus)
        lines.append(line)

    body = "\n".join(lines)
    hashtag_line = " ".join(_build_hashtags(category, name, base_hashtags))

    description = f"{body}\n\n{hashtag_line}"

    if len(description) > max_length:
        description = description[: max_length - 1].rstrip() + "…"

    return description


def _build_sentence1(name: str, category: str, seed: int) -> tuple[str, str]:
    """1文目（特徴を織り込んだ導入文）と、その文に添える絵文字を組み立てる。"""
    clause, emoji = _top_feature_clause(name, category)
    if clause:
        noun = CATEGORY_NOUNS[category]
        if _CATEGORY_NOUN_CORE[category] in clause:
            noun = "アイテム"
        return f"{clause}{noun}です", emoji

    variants = OPENING_FALLBACK_SENTENCES[category]
    text = variants[seed % len(variants)]
    pool = CATEGORY_EMOJIS[category]
    return text, pool[seed % len(pool)]


def _top_feature_clause(name: str, category: str) -> tuple[str, str]:
    """商品名から、最初に見つかった特徴の（節, 絵文字）を返す。見つからなければ空文字。"""
    for keyword, clause_spec, emoji_spec in FEATURE_CLAUSES:
        if keyword in name:
            clause = _resolve_by_category(clause_spec, category)
            emoji = _resolve_by_category(emoji_spec, category)
            if clause:
                return clause, emoji
    return "", ""


def _dedupe_adjacent_emojis(
    parts: list[tuple[str, str]], pool: list[str]
) -> list[tuple[str, str]]:
    """隣り合う文で同じ絵文字が続かないように調整する。"""
    result: list[tuple[str, str]] = []
    prev_emoji = None
    for text, emoji in parts:
        if emoji == prev_emoji:
            alt = next((candidate for candidate in pool if candidate != prev_emoji), emoji)
            emoji = alt
        result.append((text, emoji))
        prev_emoji = emoji
    return result


def _build_hashtags(category: str, name: str, base_hashtags: list[str]) -> list[str]:
    """カテゴリ・商品名に応じて3〜5個程度のハッシュタグを組み立てる。"""
    tags = list(base_hashtags)

    category_tag = HASHTAG_BY_CATEGORY.get(category, "")
    if category_tag and category_tag not in tags:
        tags.append(category_tag)

    for keyword, tag_spec in SUBTOPIC_HASHTAGS:
        if keyword in name:
            tag = _resolve_by_category(tag_spec, category)
            if tag and tag not in tags:
                tags.append(tag)
            break

    if "#便利グッズ" not in tags:
        tags.append("#便利グッズ")

    return list(dict.fromkeys(tags))[:5]
