"""楽天ROOMの紹介文欄にそのままコピペできる紹介文を作る部分。

紹介文は、読んだ人が「これ便利そう」「欲しい」と感じやすい、共感型の
構成にする。基本構成は次の5パート＋ハッシュタグ。

    ① 絵文字＋短いキャッチコピー（商品を使う人の悩み・メリットが一目で分かる）
    ② その商品を使う前にありがちな悩み・面倒（1〜2文、共感できる自然な文章）
    ③ 商品がどう解決してくれそうか（商品名から分かる範囲で自然に紹介）
    ④ ✔️を使った3項目のメリット（商品名・商品情報から確認できる内容だけ）
    ⑤ 自然な一言の締め（商品に合わせて毎回変える）
    ⑥ ハッシュタグ3〜5個

条件：
- レビュー評価・レビュー件数・価格は紹介文に入れない
- 商品名をそのまま長く転載しない
- 広告っぽすぎる文章にしない。実際に使った・購入したと誤解される表現
  （「使ってみました」「買ってよかった」等）は使わない
- 商品情報にない効果・性能を作らない（存在しない機能を書かない）
- 同じ定型文を全商品に使い回さない。商品ごとの具体的な用途・悩みを優先する
- 絵文字は商品内容に合うものを自然に使う
- 500文字以内。読みやすいよう適度に改行する

注意（特徴抽出に商品説明・itemCaptionを使わない理由）：
当初は商品説明（itemCaption）の最初の一文も検出対象にしていたが、実際の
楽天ウェブサービスのレスポンスを確認したところ、次のような問題が見つかった。

1. 商品説明が句点（。）を含まない仕様一覧形式（「素材/材質：エラストマー、
   ステンレス、…」等）のことがあり、「最初の一文」のつもりが説明文全体を
   拾ってしまい、製品の一部品の素材などを商品全体の特徴として誤って
   拾ってしまう
2. まれに、その商品とは無関係な説明文がそのまま入っている（別商品の
   説明文が誤って使われているとみられるケースがあった）

そのため、特徴語の検出は「商品名」だけに限定している。

注意（商品名の単語だけで特徴を決めつけない）：
商品名はSEO対策で色々な単語が詰め込まれていることが多く、「商品名に単語が
含まれる＝それが商品の主な特徴」とは限らない。このため、次の2段構えにしている。

1. `PRODUCT_TYPE_TEMPLATES`：商品名から「この商品が何であるか」がほぼ確実に
   分かる場合に使う、商品全体の用途に沿った悩み・解決・メリットのテンプレート
   （ロボット掃除機・スープメーカー・ノンフライヤー・フライパン等、よくある
   商品タイプを収録）。
2. `GENERIC_TEMPLATES`：商品の種類が特定できない場合に使う、カテゴリ共通の
   安全なテンプレート。

どちらの場合も、✔️メリットの3項目のうち2項目はテンプレートの安全な内容を
使い、残り1項目は商品名から`FEATURE_CLAUSES`（マグネット式・折りたたみ式等の
構造・仕様）が読み取れればそれを使う（読み取れなければテンプレートの
安全な言い回しで補う）。素材だけを述べる表現（例：ステンレス＝サビに強い）は
商品全体の用途に繋がりにくいため対象にしていない。
"""

from __future__ import annotations

from typing import Any, NamedTuple

DEFAULT_CATEGORY = "暮らし全般"

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


# 商品名から、商品を使う場所が分かる場合に、その場所を表す言葉。
# 「お部屋」のような汎用表現ではなく、商品名から読み取れる具体的な場所
# （お風呂用品なら「浴室」、キッチン用品なら「キッチン」等）を使うための一覧。
LOCATION_HINTS: list[tuple[str, str]] = [
    ("お風呂", "浴室"),
    ("浴室", "浴室"),
    ("バスルーム", "浴室"),
    ("キッチン", "キッチン"),
    ("玄関", "玄関"),
    ("トイレ", "トイレ"),
    ("クローゼット", "クローゼット"),
    ("洗面所", "洗面所"),
]

# GENERIC_TEMPLATES（商品の種類が特定できない場合）で、場所が分かったときに
# 先頭の絵文字を場所に合わせて変えるための対応表。
LOCATION_TOPIC_EMOJI: dict[str, str] = {
    "浴室": "🛁",
    "洗面所": "🪞",
    "玄関": "🚪",
    "キッチン": "🍳",
    "トイレ": "🚽",
    "クローゼット": "👕",
}


def _resolve_location(name: str, default: str = "身の回り") -> str:
    """商品名から使う場所が分かればその言葉を、分からなければdefaultを返す。"""
    for keyword, location in LOCATION_HINTS:
        if keyword in name:
            return location
    return default


# PRODUCT_TYPE_TEMPLATES・GENERIC_TEMPLATESで使う、投稿1件分のテンプレート。
# hook_text：①のキャッチコピー本文（絵文字は別途付与）
# topic_emoji：①の先頭に置く、内容に合った絵文字
# worry_lines：②の悩み・あるあるの文章（1〜2行、最後は「…😅」等で終える）
# solution_text：③の「商品がどう解決してくれそうか」の文章（末尾に「◎」を付与）
# checklist_core：④の✔️メリットのうち、商品タイプに応じた安全な2項目
# checklist_fallback：④の3項目目のうち、商品名から特徴が読み取れなかった場合に使う項目
# closing_variants：⑤の締めの一言（商品コードに応じて複数パターンから選ぶ）
class _PostTemplate(NamedTuple):
    hook_text: str
    topic_emoji: str
    worry_lines: list[str]
    solution_text: str
    checklist_core: list[str]
    checklist_fallback: str
    closing_variants: list[str]


# 商品名から「この商品が具体的に何であるか」がほぼ確実に分かる場合に使う、
# 商品全体の用途に沿ったテンプレート一覧。FEATURE_CLAUSES（構造・仕様の単語
# 一致）より必ず先に判定する。
PRODUCT_TYPE_TEMPLATES: list[tuple[str, _PostTemplate]] = [
    (
        "リモコン",
        _PostTemplate(
            hook_text="リモコンの置き場所、決まってる？",
            topic_emoji="🏠",
            worry_lines=[
                "「リモコンどこいった？」って、",
                "家の中で意外と探しがちですよね…😅",
            ],
            solution_text="そんな小さなストレスを減らしてくれそうな収納ラック",
            checklist_core=["リモコンの定位置を作れる", "スマホなどの収納にも使える"],
            checklist_fallback="置き場所に迷わずサッと片付けられる",
            closing_variants=[
                "「探す時間を減らしたい！」という人に便利そう",
                "リモコンの定位置を決めたい人におすすめ",
            ],
        ),
    ),
    (
        "水切りボウル",
        _PostTemplate(
            hook_text="野菜の水切り、これならラクそう",
            topic_emoji="🥗",
            worry_lines=[
                "サラダを作るときって、",
                "野菜を洗ったあと水を切るのが意外と面倒…😅",
            ],
            solution_text="くるっと傾けるだけで水切りできる便利なボウル",
            checklist_core=["野菜の水切りに使える", "洗ってそのまま使いやすそう"],
            checklist_fallback="キッチン作業をちょっと時短できそう",
            closing_variants=[
                "こういう「毎日の小さな手間」を減らしてくれるアイテム好き",
                "サラダ作りをラクにしたい人におすすめ",
            ],
        ),
    ),
    (
        "シーツハンガー",
        _PostTemplate(
            hook_text="シーツを干す場所、困ってない？",
            topic_emoji="🧺",
            worry_lines=[
                "大きなシーツって、干す場所を取るし",
                "「もっと省スペースで干せたら…」って思いますよね😅",
            ],
            solution_text="そんなときに便利そうなシーツハンガー",
            checklist_core=["シーツを省スペースで干せそう", "室内干しにも便利そう"],
            checklist_fallback="大きな洗濯物の悩みを解決できそう",
            closing_variants=[
                "洗濯の「ちょっと困った」をラクにしてくれるアイテム",
                "大きな洗濯物の干し場所に悩む人におすすめ",
            ],
        ),
    ),
    (
        "ドライヤースタンド",
        _PostTemplate(
            hook_text="洗面所のごちゃつき、これでスッキリ",
            topic_emoji="🪞",
            worry_lines=[
                "ドライヤーやヘアーアイロンって、",
                "使ったあと置き場所に困りがち…😅",
            ],
            solution_text="まとめて収納できるスタンド",
            checklist_core=["ドライヤーをスッキリ収納できる", "ヘアーアイロンもまとめて整理できる"],
            checklist_fallback="洗面所の収納がしやすくなる",
            closing_variants=[
                "「毎日使うものだから、置き場所を決めたい」という人に良さそう",
                "洗面所をすっきりさせたい人におすすめ",
            ],
        ),
    ),
    (
        "ヘアアイロンスタンド",
        _PostTemplate(
            hook_text="洗面所のごちゃつき、これでスッキリ",
            topic_emoji="🪞",
            worry_lines=[
                "ドライヤーやヘアーアイロンって、",
                "使ったあと置き場所に困りがち…😅",
            ],
            solution_text="まとめて収納できるスタンド",
            checklist_core=["ドライヤーをスッキリ収納できる", "ヘアーアイロンもまとめて整理できる"],
            checklist_fallback="洗面所の収納がしやすくなる",
            closing_variants=[
                "「毎日使うものだから、置き場所を決めたい」という人に良さそう",
                "洗面所をすっきりさせたい人におすすめ",
            ],
        ),
    ),
    (
        "ロボット掃除機",
        _PostTemplate(
            hook_text="毎日の床掃除、おまかせできたら楽じゃない？",
            topic_emoji="🤖",
            worry_lines=[
                "掃除機をかけなきゃと思いつつ、",
                "毎日となると地味に手間ですよね…😅",
            ],
            solution_text="毎日の床掃除をおまかせできるロボット掃除機",
            checklist_core=["スイッチひとつで床掃除をおまかせできる", "毎日の掃除の手間を減らせそう"],
            checklist_fallback="忙しい日でも部屋をきれいに保ちやすい",
            closing_variants=[
                "床掃除の時間を減らしたい人におすすめ",
                "毎日のお掃除をラクにしたい人に便利そう",
            ],
        ),
    ),
    (
        "スープメーカー",
        _PostTemplate(
            hook_text="スープ作り、材料入れるだけで完成したら嬉しくない？",
            topic_emoji="🥣",
            worry_lines=[
                "スープを一から作るのは、",
                "地味に手間がかかりますよね…😅",
            ],
            solution_text="材料を入れてスープ作りをおまかせできる調理家電",
            checklist_core=["材料を入れるだけでスープ作りをおまかせできる", "忙しい日でも手軽に使えそう"],
            checklist_fallback="毎日の調理の手間を減らしてくれそう",
            closing_variants=[
                "手軽にスープを楽しみたい人におすすめ",
                "調理の手間を減らしたい人に便利そう",
            ],
        ),
    ),
    (
        "ノンフライヤー",
        _PostTemplate(
            hook_text="揚げ物、油を使わずに作れたらラクじゃない？",
            topic_emoji="🍟",
            worry_lines=[
                "揚げ物って美味しいけど、",
                "油の後片付けが地味に面倒ですよね…😅",
            ],
            solution_text="揚げ物を手軽に作れるノンフライヤー",
            checklist_core=["油を使わずに揚げ物を作れる", "後片付けの手間を減らせそう"],
            checklist_fallback="毎日の料理の幅を広げてくれそう",
            closing_variants=[
                "油を使わずに揚げ物を楽しみたい人におすすめ",
                "後片付けの手間を減らしたい人に便利そう",
            ],
        ),
    ),
    (
        "フライパン",
        _PostTemplate(
            hook_text="毎日使うフライパン、使いやすさで選びたくない？",
            topic_emoji="🍳",
            worry_lines=[
                "焦げつきやすいフライパンだと、",
                "料理のたびにちょっとストレスですよね…😅",
            ],
            solution_text="焼く・煮るなど毎日の料理に使いやすそうなフライパン",
            checklist_core=["毎日の料理に使いやすそう", "普段の調理の幅を広げてくれそう"],
            checklist_fallback="後片付けもしやすくなりそう",
            closing_variants=[
                "毎日の料理をもう少しラクにしたい人におすすめ",
                "使いやすいフライパンを探している人に便利そう",
            ],
        ),
    ),
    (
        "三角コーナー",
        _PostTemplate(
            hook_text="生ゴミの水切り、地味に面倒じゃない？",
            topic_emoji="💧",
            worry_lines=[
                "料理のたびに出る生ゴミ、",
                "水切りや処理が地味に手間ですよね…😅",
            ],
            solution_text="生ゴミの水切りをラクにしてくれそうな三角コーナー",
            checklist_core=["生ゴミの水切りに使える", "キッチンの排水口まわりを清潔に保ちやすい"],
            checklist_fallback="毎日の片付けがちょっとラクになりそう",
            closing_variants=[
                "生ゴミの処理をラクにしたい人におすすめ",
                "キッチンを清潔に保ちたい人に便利そう",
            ],
        ),
    ),
    (
        "水切りかご",
        _PostTemplate(
            hook_text="洗った食器の置き場所、困ってない？",
            topic_emoji="💧",
            worry_lines=[
                "食器を洗ったあと、",
                "乾かす場所に地味に困りますよね…😅",
            ],
            solution_text="洗った食器をしっかり乾かせる水切りかご",
            checklist_core=["洗った食器を乾かせる", "キッチンの水回りをすっきり使いやすい"],
            checklist_fallback="洗い物のあとの片付けがラクになりそう",
            closing_variants=[
                "洗い物のあとの片付けを楽にしたい人におすすめ",
                "キッチンをすっきり使いたい人に便利そう",
            ],
        ),
    ),
    (
        "圧縮袋",
        _PostTemplate(
            hook_text="かさばる衣類の収納、これでスッキリ",
            topic_emoji="📦",
            worry_lines=[
                "衣替えのたびに、",
                "収納スペースの確保に困りますよね…😅",
            ],
            solution_text="かさばる衣類をコンパクトにまとめられる圧縮袋",
            checklist_core=["衣類をコンパクトに圧縮できる", "収納スペースを有効に使える"],
            checklist_fallback="衣替えや持ち運びがラクになりそう",
            closing_variants=[
                "衣替えの収納をラクにしたい人におすすめ",
                "かさばる荷物をコンパクトにしたい人に便利そう",
            ],
        ),
    ),
    (
        "ドアストッパー",
        _PostTemplate(
            hook_text="ドアが勝手に動くの、地味に困らない？",
            topic_emoji="🚪",
            worry_lines=[
                "風が吹くたびにドアが動いて、",
                "地味にストレスですよね…😅",
            ],
            solution_text="ドアを開けたままキープしやすいドアストッパー",
            checklist_core=["扉を開けたままキープできる", "玄関まわりなどで使いやすい"],
            checklist_fallback="扉が不意に動いて困る場面を減らせそう",
            closing_variants=[
                "扉の開閉にちょっと困っている人におすすめ",
                "玄関まわりを使いやすくしたい人に便利そう",
            ],
        ),
    ),
    (
        "ドアストップ",
        _PostTemplate(
            hook_text="ドアが勝手に動くの、地味に困らない？",
            topic_emoji="🚪",
            worry_lines=[
                "風が吹くたびにドアが動いて、",
                "地味にストレスですよね…😅",
            ],
            solution_text="ドアを開けたままキープしやすいドアストッパー",
            checklist_core=["扉を開けたままキープできる", "玄関まわりなどで使いやすい"],
            checklist_fallback="扉が不意に動いて困る場面を減らせそう",
            closing_variants=[
                "扉の開閉にちょっと困っている人におすすめ",
                "玄関まわりを使いやすくしたい人に便利そう",
            ],
        ),
    ),
    (
        "マドラー",
        _PostTemplate(
            hook_text="味噌を溶かすの、地味に時間がかからない？",
            topic_emoji="🥄",
            worry_lines=[
                "味噌汁を作るとき、",
                "味噌を溶くのに地味に手間取りますよね…😅",
            ],
            solution_text="味噌などをなめらかに溶かしやすいマドラー",
            checklist_core=["味噌をなめらかに溶かせる", "毎日の味噌汁作りに使いやすい"],
            checklist_fallback="調理の手間をちょっと減らせそう",
            closing_variants=[
                "味噌汁作りをラクにしたい人におすすめ",
                "毎日の調理をちょっとラクにしたい人に便利そう",
            ],
        ),
    ),
    (
        "モップ",
        _PostTemplate(
            hook_text="床のホコリ、気づいたらすぐ溜まってない？",
            topic_emoji="🧹",
            worry_lines=[
                "掃除機を出すほどじゃないけど、",
                "床のホコリって地味に気になりますよね…😅",
            ],
            solution_text="床のホコリや汚れをサッと拭き取れるモップ",
            checklist_core=["床のホコリや汚れをサッと拭き取れる", "かがまずに掃除がしやすい"],
            checklist_fallback="毎日の床掃除の手間を減らせそう",
            closing_variants=[
                "サッと使える掃除グッズを探している人におすすめ",
                "毎日の床掃除をラクにしたい人に便利そう",
            ],
        ),
    ),
    (
        "フロアワイパー",
        _PostTemplate(
            hook_text="床のホコリ、気づいたらすぐ溜まってない？",
            topic_emoji="🧹",
            worry_lines=[
                "掃除機を出すほどじゃないけど、",
                "床のホコリって地味に気になりますよね…😅",
            ],
            solution_text="床のホコリや汚れをサッと拭き取れるフロアワイパー",
            checklist_core=["床のホコリや汚れをサッと拭き取れる", "かがまずに掃除がしやすい"],
            checklist_fallback="毎日の床掃除の手間を減らせそう",
            closing_variants=[
                "サッと使える掃除グッズを探している人におすすめ",
                "毎日の床掃除をラクにしたい人に便利そう",
            ],
        ),
    ),
]


def _match_product_type(name: str) -> _PostTemplate | None:
    """商品名から、具体的な商品の種類が分かるテンプレートを返す。無ければNone。"""
    for keyword, template in PRODUCT_TYPE_TEMPLATES:
        if keyword in name:
            return template
    return None


# PRODUCT_TYPE_TEMPLATESで商品の種類が特定できなかった場合に使う、
# カテゴリ共通の安全なテンプレート。
GENERIC_TEMPLATES: dict[str, _PostTemplate] = {
    "掃除": _PostTemplate(
        hook_text="その汚れ、気になってませんか？",
        topic_emoji="🧹",
        worry_lines=["掃除しなきゃと思いつつ、", "つい後回しにしがちですよね…😅"],
        solution_text="そんな掃除の手間を減らしてくれそうな掃除グッズ",
        checklist_core=["気になる汚れのお手入れに使える", "サッと使えて手軽"],
        checklist_fallback="普段のお掃除がちょっとラクになりそう",
        closing_variants=[
            "お手入れの手間を減らしたい人に便利そう",
            "気になる汚れをためずに済ませたい人におすすめ",
        ],
    ),
    "収納": _PostTemplate(
        hook_text="{location}の物の置き場所、決まってる？",
        topic_emoji="🏠",
        worry_lines=["気づけば物が増えて、", "収納場所に困りがちですよね…😅"],
        solution_text="{location}の物をすっきりまとめられそうな収納グッズ",
        checklist_core=["{location}の物をすっきりまとめられる", "必要な物をすぐ取り出しやすい"],
        checklist_fallback="見た目もすっきり整いそう",
        closing_variants=[
            "片付けの手間を減らしたい人に便利そう",
            "すっきりした収納にしたい人におすすめ",
        ],
    ),
    "キッチン": _PostTemplate(
        hook_text="毎日の料理や後片付け、地味に手間じゃない？",
        topic_emoji="🍳",
        worry_lines=["毎日のことだから、", "小さな手間が積み重なりますよね…😅"],
        solution_text="そんなキッチンでの家事をラクにしてくれそうなキッチングッズ",
        checklist_core=["毎日の料理や後片付けに使いやすい", "キッチン作業がスムーズになる"],
        checklist_fallback="使いたいときにサッと取り出せる",
        closing_variants=[
            "毎日の家事をちょっとラクにしたい人におすすめ",
            "キッチン作業を快適にしたい人に便利そう",
        ],
    ),
    "時短": _PostTemplate(
        hook_text="その家事、もっと時短できるかも？",
        topic_emoji="⏱️",
        worry_lines=["毎日のことだから、", "地味に時間がかかりますよね…😅"],
        solution_text="そんな家事の時間を短くしてくれそうな時短家電",
        checklist_core=["毎日の家事にかかる時間を減らせる", "忙しい日にも取り入れやすい"],
        checklist_fallback="手間のかかる家事をおまかせしやすい",
        closing_variants=[
            "家事の時間を短くしたい人におすすめ",
            "忙しい日にも便利そう",
        ],
    ),
    DEFAULT_CATEGORY: _PostTemplate(
        hook_text="その悩み、地味にストレスじゃない？",
        topic_emoji="🏠",
        worry_lines=["小さなことだけど、", "積み重なると気になりますよね…😅"],
        solution_text="そんな暮らしの小さな不便を解消してくれそうな便利グッズ",
        checklist_core=["日々のちょっとした不便を解消できる", "普段の生活に取り入れやすい"],
        checklist_fallback="使うたびに便利さを感じられそう",
        closing_variants=[
            "暮らしを少しラクにしたい人におすすめ",
            "気になる人はチェックしてみてほしい",
        ],
    ),
}

# GENERIC_TEMPLATESで商品の種類が特定できなかった場合のみ、✔️メリットの3項目目に
# 使う構造・仕様の特徴（「マグネットで浮かせて設置できる」等）と絵文字。
# 検出したキーワードそのものではなく、商品情報から読み取れる客観的な特徴
# （構造・使い方）だけを表す表現にとどめ、効果や体験談は含めない。
# 商品の素材だけを述べる表現（例：ステンレス＝サビに強い）は、商品全体の
# 用途に繋がりにくいため対象にしていない。
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
    """商品情報から、共感型の構成（①キャッチコピー②悩み③解決④✔️メリット3つ
    ⑤締め⑥ハッシュタグ）の紹介文を組み立てる。

    レビュー評価・件数・価格は本文に含めない。商品名から具体的な商品の種類が
    分かる場合（PRODUCT_TYPE_TEMPLATES）はそれを優先し、分からない場合は
    カテゴリ共通の安全なテンプレート（GENERIC_TEMPLATES）を使う。✔️メリットの
    3項目目は、商品名から構造・仕様の特徴が読み取れればそれを使い、
    読み取れなければテンプレートの安全な言い回しで補う。
    """
    category = category if category in GENERIC_TEMPLATES else DEFAULT_CATEGORY
    name = item.get("name", "") or ""

    # 商品ごとに締めの一言を変えるための目印（商品コードが無ければ商品名を使う）。
    seed_source = item.get("item_code") or name
    seed = sum(ord(c) for c in seed_source) if seed_source else 0

    template = _match_product_type(name)
    topic_emoji = None
    if template is None:
        template = GENERIC_TEMPLATES[category]
        location = _resolve_location(name)
        topic_emoji = LOCATION_TOPIC_EMOJI.get(location, template.topic_emoji)
    else:
        location = _resolve_location(name)

    hook_text = template.hook_text.format(location=location)
    solution_text = template.solution_text.format(location=location)
    checklist_core = [text.format(location=location) for text in template.checklist_core]

    clause, _clause_emoji = _top_feature_clause(name, category)
    third_item = clause if clause else template.checklist_fallback.format(location=location)
    checklist = checklist_core + [third_item]

    closing_text = template.closing_variants[seed % len(template.closing_variants)]

    hook_line = f"{topic_emoji or template.topic_emoji} {hook_text}✨"
    worry_block = "\n".join(template.worry_lines)
    solution_line = f"{solution_text}◎"
    checklist_block = "\n".join(f"✔️ {text}" for text in checklist)
    closing_line = f"{closing_text}☺️"
    hashtag_line = " ".join(_build_hashtags(category, name, base_hashtags))

    description = "\n\n".join(
        [hook_line, worry_block, solution_line, checklist_block, closing_line, hashtag_line]
    )

    if len(description) > max_length:
        description = description[: max_length - 1].rstrip() + "…"

    return description


def _top_feature_clause(name: str, category: str) -> tuple[str, str]:
    """商品名から、最初に見つかった特徴の（節, 絵文字）を返す。見つからなければ空文字。"""
    for keyword, clause_spec, emoji_spec in FEATURE_CLAUSES:
        if keyword in name:
            clause = _resolve_by_category(clause_spec, category)
            emoji = _resolve_by_category(emoji_spec, category)
            if clause:
                return clause, emoji
    return "", ""


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
