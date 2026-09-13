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
- 同じ定型文を全商品に使い回さない。商品名に明記されている構造・仕様の特徴
  （マグネット式、折りたたみ式など）があれば文章に組み込むが、あくまで
  「何に使う商品か」「使うと何がラクになるか」を主役にし、仕様の言葉を
  紹介文の主題にしすぎない。確実に読み取れない場合は無理に特徴を作らず、
  カテゴリ共通の安全な言い回しで補う

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

注意（商品名の単語だけで特徴を決めつけない）：
商品名はSEO対策で色々な単語が詰め込まれていることが多く、「商品名に単語が
含まれる＝それが商品の主な特徴」とは限らない（例：三角コーナーの商品名に
「吸盤」という単語が含まれていても、商品全体の用途は生ゴミの水切りであり、
「吸盤で取り付けるタイプ」を紹介文の主役にすると不自然になる。同様に、
味噌マドラーの「ステンレス」やドアストッパーの「マグネット」も、商品全体の
用途とは異なる説明になってしまっていた）。

この問題への対応として、次の2段構えにしている。

1. `PRODUCT_TYPE_HINTS`：商品名から「この商品が何であるか」がほぼ確実に
   分かる場合は、構造・仕様の単語一致より先にこちらを優先し、商品全体の
   用途に沿った文章をそのまま1文目として使う。
2. `FEATURE_CLAUSES`：商品全体の用途が特定できない場合のみ、構造・仕様の
   特徴を2文目に「〜なので、」という理由として添える（1文目の主役にはしない）。
   商品の素材だけを述べる表現（「ステンレス製＝サビに強い」等、使うと何が
   ラクになるかに繋がらない表現）は対象から外している。
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


# 商品名から「この商品が具体的に何であるか」がほぼ確実に分かる場合に使う、
# 商品全体の用途に沿った1文目（そのまま文として使える完成した文）と絵文字。
# FEATURE_CLAUSES（構造・仕様の単語一致）より必ず先に判定する。これは、
# 商品名に「吸盤」「マグネット」「ステンレス」などの単語が含まれていても、
# それが商品全体の用途ではないことがある（三角コーナーの「吸盤」、
# ドアストッパーの「マグネット」等）ため、商品の種類そのものが分かって
# いるならそちらの説明を優先するための仕組み。
PRODUCT_TYPE_HINTS: list[tuple[str, str, str]] = [
    ("三角コーナー", "生ゴミの水切りをラクにしてくれそうな三角コーナーです", "💧"),
    ("ドアストッパー", "ドアを開けたままキープしやすいドアストッパーです", "🚪"),
    ("ドアストップ", "ドアを開けたままキープしやすいドアストッパーです", "🚪"),
    ("マドラー", "味噌などをなめらかに溶かしやすいマドラーです", "🥄"),
]


def _top_product_type_sentence(name: str) -> tuple[str, str]:
    """商品名から、具体的な商品の種類が分かる1文目（文, 絵文字）を返す。無ければ空文字。"""
    for keyword, sentence, emoji in PRODUCT_TYPE_HINTS:
        if keyword in name:
            return sentence, emoji
    return "", ""


# PRODUCT_TYPE_HINTSで商品の種類が特定できなかった場合のみ、2文目に理由として
# 添える構造・仕様の特徴の「節」（「〜なので、」に続けられる形。例：
# 「マグネットで浮かせて設置できる」＋「ので、〜」）と、それに添える絵文字。
# 検出したキーワードそのものではなく、商品情報から読み取れる客観的な特徴
# （構造・使い方）だけを表す表現にとどめ、効果や体験談は含めない。
# 商品の素材だけを述べる表現（例：ステンレス＝サビに強い）は、商品全体の
# 用途に繋がりにくく紹介文の主題として不自然になりやすいため対象にしていない。
#
# 文言・絵文字はどちらも、基本は固定値（str）だが、カテゴリによって自然な表現が
# 変わるもの（例：「大容量」は収納用品なら「収納できる」だが、調理家電なら
# 「調理しやすい」）は、カテゴリ名をキーにした辞書（dict）で指定できる。
FEATURE_CLAUSES: list[tuple[str, str | dict[str, str], str | dict[str, str]]] = [
    ("マグネット", "マグネットで浮かせて設置できる", "🧲"),
    ("吸盤", "吸盤で好きな場所に取り付けられる", "✨"),
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
# 商品の種類が特定できない場合の「安全な言い回し」で、常に「何に使う商品か」を
# 表すことを優先している。
OPENING_FALLBACK_SENTENCES: dict[str, list[str]] = {
    "掃除": [
        "汚れが気になる場所のお手入れに使えそうな掃除グッズです",
        "普段の掃除をちょっとラクにしてくれそうなアイテムです",
        "気になる汚れをサッと片付けたいときに使えそうです",
    ],
    "収納": [
        "散らかりがちな物をすっきりまとめられそうな収納グッズです",
        "収納スペースを有効に使えそうな便利アイテムです",
        "身の回りの物を使いやすく整理できそうです",
    ],
    "キッチン": [
        "キッチンでの作業をスムーズにしてくれそうなキッチングッズです",
        "毎日の調理や片付けに取り入れやすそうなアイテムです",
        "料理の下ごしらえや後片付けに使えそうです",
    ],
    "時短": [
        "日々のちょっとした作業を時短できそうなアイテムです",
        "忙しい日にも取り入れやすそうな時短家電です",
        "手間のかかる作業をサッと済ませたいときに便利そうです",
    ],
    DEFAULT_CATEGORY: [
        "暮らしをちょっと快適にしてくれそうな便利グッズです",
        "日々の小さな不便を解消してくれそうなアイテムです",
        "普段の生活にすっと取り入れやすそうなアイテムです",
    ],
}

# 2文目：ためらいのない断定を避けた、やわらかい「おすすめ・メリット」の一文。
BENEFIT_SENTENCES: dict[str, list[str]] = {
    "掃除": [
        "気になる汚れをサッと落とせそうで、お手入れの時間を短くできそうです",
        "お手入れの手間を減らしたい人におすすめしたい掃除グッズです",
        "毎日のちょっとした掃除がラクになりそうです",
        "毎日の家事の負担を少し減らしたい人にぴったりです",
        "サッと使えて、忙しい日にも取り入れやすそうです",
    ],
    "収納": [
        "取り出しやすくて、お部屋がスッキリ見えそうです",
        "毎日の片付けをラクにしたい人におすすめしたい収納グッズです",
        "散らかりがちな物をまとめて、すっきり整理できそうです",
        "見た目もすっきり整えたい人に向いていそうです",
        "使いたい物をすぐ取り出せるようになりそうです",
    ],
    "キッチン": [
        "取り出しやすくて、キッチンがスッキリ見えそうです",
        "毎日の料理や後片付けをラクにしたい人におすすめです",
        "キッチン周りをすっきり整えたい人に便利そうです",
        "調理や後片付けの手間を少し減らしたい人に向いていそうです",
        "毎日のキッチン作業を快適にしてくれそうです",
    ],
    "時短": [
        "忙しい日の家事を少しでもラクにしたい人におすすめです",
        "毎日のちょっとした手間を減らせそうです",
        "時間に追われがちな日にも取り入れやすそうです",
        "家事に取られる時間を少しでも減らしたい人に向いていそうです",
        "毎日のちょっとした作業がスムーズになりそうです",
    ],
    DEFAULT_CATEGORY: [
        "暮らしのちょっとした不便を解消したい人におすすめです",
        "毎日の生活に取り入れやすそうなアイテムです",
        "ちょっとした場面で役立ちそうです",
        "気になっていた小さな不便を解消してくれそうです",
        "毎日の暮らしにそっと寄り添ってくれそうなアイテムです",
    ],
}

# 3文目（付くこともある）：カテゴリ共通の、やわらかい締めの一文。
CLOSING_SENTENCES: list[str] = [
    "暮らしをちょっとラクにしてくれる便利グッズです",
    "気になる方はチェックしてみてほしいアイテムです",
    "毎日にちょっとした余裕をプラスしてくれそうです",
    "毎日を少しだけ快適にしてくれそうなアイテムです",
    "気になる場面で活躍してくれそうです",
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
    1文目は常に「何に使う商品か」を表す文にし、構造・仕様の特徴（マグネット式・
    大容量など）が商品名から分かる場合も、2文目に理由として添えるだけにとどめ、
    仕様の言葉が紹介文の主役にならないようにする。
    """
    category = category if category in CATEGORY_EMOJIS else DEFAULT_CATEGORY
    name = item.get("name", "") or ""

    # 商品ごとに言い回しを変えるための目印（商品コードが無ければ商品名を使う）。
    seed_source = item.get("item_code") or name
    seed = sum(ord(c) for c in seed_source) if seed_source else 0

    sentence1_text, sentence1_emoji, product_type_matched = _build_sentence1(name, category, seed)
    sentence2_text, sentence2_emoji = _build_sentence2(name, category, seed, skip_feature=product_type_matched)

    parts = [(sentence1_text, sentence1_emoji), (sentence2_text, sentence2_emoji)]

    pool = CATEGORY_EMOJIS[category]

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


def _build_sentence1(name: str, category: str, seed: int) -> tuple[str, str, bool]:
    """1文目（商品全体の用途を表す導入文）と絵文字、商品の種類を特定できたかを返す。

    商品の種類そのものが商品名から分かる場合（PRODUCT_TYPE_HINTS）を最優先し、
    分からない場合はカテゴリ共通の安全な言い回し（OPENING_FALLBACK_SENTENCES）
    を使う。どちらの場合も、構造・仕様の単語（マグネット・大容量など）だけを
    根拠に1文目を作ることはしない。
    """
    product_type_sentence, product_type_emoji = _top_product_type_sentence(name)
    if product_type_sentence:
        return product_type_sentence, product_type_emoji, True

    variants = OPENING_FALLBACK_SENTENCES[category]
    text = variants[seed % len(variants)]
    pool = CATEGORY_EMOJIS[category]
    return text, pool[seed % len(pool)], False


def _build_sentence2(name: str, category: str, seed: int, skip_feature: bool) -> tuple[str, str]:
    """2文目（おすすめ・メリット）を組み立てる。

    商品の種類が1文目で特定できていない場合に限り、商品名から読み取れる
    構造・仕様の特徴が見つかれば「〜なので、」という理由として添える
    （あくまで2文目内の理由であり、文章全体の主役にはしない）。
    """
    benefit_variants = BENEFIT_SENTENCES[category]
    benefit_text = benefit_variants[(seed // 3) % len(benefit_variants)]
    pool = CATEGORY_EMOJIS[category]
    benefit_emoji = pool[(seed // 3 + 1) % len(pool)]

    if skip_feature:
        return benefit_text, benefit_emoji

    clause, clause_emoji = _top_feature_clause(name, category)
    if clause:
        return f"{clause}ので、{benefit_text}", clause_emoji
    return benefit_text, benefit_emoji


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
