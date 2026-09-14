"""TikTok投稿向けの台本・テロップ・ナレーション・キャプション・ハッシュタグ・
動画制作メモを組み立てる部分。

実際に商品を購入・使用していない前提のため、体験談を装う表現（「使ってみた」
「買ってよかった」等）は一切使わない。紹介文生成（description_generator）で
すでに使っている、商品情報だけを根拠にした安全な言い回しのテンプレート
（get_template_components）を再利用することで、体験談表現が紛れ込まない
ようにしている。

今回はここまで（1商品選定＋投稿素材のテキスト生成＋スマホ表示）で止める。
動画ファイルの生成・外部の動画生成API連携・TikTokへの自動投稿は行わない。
"""

from __future__ import annotations

from typing import Any, NamedTuple

from . import description_generator

# 実際に商品を購入・使用していない前提のため、体験談を装う表現は生成しない。
# このリストは、生成結果にこれらの言葉が紛れ込んでいないことを確認するための
# 安全確認用（テンプレート自体はこれらの言葉を一切使っていない）。
BANNED_PHRASES: list[str] = [
    "買ってよかった",
    "使ってみた",
    "使ってみました",
    "愛用してい",
    "本当に便利だった",
    "絶対",
    "実際に試した",
    "私も使っています",
    "購入品",
    "買ってみました",
]

# ナレーションの長さから読み上げ秒数を見積もるための目安（1秒あたりの文字数）。
# 厳密なTTS計測ではなく、台本が15〜20秒程度に収まっているかを確認するための
# 簡易的な目安。
NARRATION_CHARS_PER_SECOND = 6.0

# ①のフック（冒頭の一言）。毎回同じにならないよう、商品コードに応じて
# 複数パターンから選ぶ。いずれも「見つけた／気になる」という、事実と推測を
# 分けた表現にしている（購入・使用したと誤解される表現は使わない）。
_HOOK_VARIANTS: list[str] = [
    "これ知ってる？👀",
    "こんなアイテム見つけました👀",
    "気になるアイテム見つけた🔍",
]

# ⑥キャプションの書き出し（カテゴリ別）。最後は必ず「気になるアイテム✨」
# 「楽天ROOMに載せています。」で締め、使用経験を装う表現にならないようにする。
_CAPTION_LEAD_BY_CATEGORY: dict[str, str] = {
    "掃除": "お掃除をラクにしたい人に",
    "収納": "お部屋をスッキリさせたい人に",
    "キッチン": "キッチン作業をラクにしたい人に",
    "時短": "家事を時短したい人に",
    description_generator.DEFAULT_CATEGORY: "暮らしを少しラクにしたい人に",
    "洗剤": "洗剤のストックを切らしたくない人に",
    "キッチン消耗品": "キッチン用品のストックを切らしたくない人に",
    "日用品": "日用品のストックを切らしたくない人に",
    "水": "お水のストックを切らしたくない人に",
    "お茶": "お茶のストックを切らしたくない人に",
    "ジュース": "飲み物のストックを切らしたくない人に",
}

# ⑦ハッシュタグの固定分。「#購入品」「#買ってよかった」のような、実際に
# 購入したという誤解を招くタグは含めない。
_FIXED_HASHTAGS: list[str] = [
    "#楽天ROOM",
    "#楽天ルーム",
    "#楽天で見つけた",
    "#暮らしの便利グッズ",
    "#便利グッズ",
]

# ナレーション文を整えるときに末尾から取り除く装飾記号（絵文字・記号）。
_TRAILING_DECORATION = "…😅✨👀🔍◎☺️🧹🏠🍳⏱️🧴📦、"


class TikTokContent(NamedTuple):
    script: str
    telops: list[str]
    narration: str
    caption: str
    hashtags: list[str]
    video_notes: list[str]


def _product_label(name: str, category: str) -> str:
    """テロップ・台本で使う、短い商品の呼び名を決める。

    商品名から具体的な商品の種類が分かればそれ（例：「水切りボウル」）を、
    分からなければカテゴリ名（例：「収納アイテム」）を使う。
    """
    keyword = description_generator.match_product_type_keyword(name)
    if keyword:
        return keyword
    if category and category != description_generator.DEFAULT_CATEGORY:
        return f"{category}アイテム"
    return "気になるアイテム"


def _to_sentence(text: str) -> str:
    """文の末尾の装飾記号を取り除き、句点で終わる自然な一文にする
    （ナレーション用。AI音声でそのまま読み上げやすくするため）。"""
    cleaned = text.rstrip(_TRAILING_DECORATION)
    if not cleaned:
        return ""
    if not cleaned.endswith(("。", "！", "？")):
        cleaned += "。"
    return cleaned


def estimate_duration_seconds(narration: str) -> float:
    """ナレーション文の文字数から、読み上げ秒数の目安を見積もる（簡易計算）。

    厳密なTTS計測ではなく、台本が15〜20秒程度に収まっているかどうかを
    確認するための目安。
    """
    char_count = len(narration.replace("\n", "").replace("、", "").replace("。", ""))
    return round(char_count / NARRATION_CHARS_PER_SECOND, 1)


def build_hashtags(category: str) -> list[str]:
    """カテゴリに応じて5〜8個程度のハッシュタグを組み立てる。"""
    tags = list(_FIXED_HASHTAGS)
    category_tag = description_generator.HASHTAG_BY_CATEGORY.get(category, "")
    if category_tag and category_tag not in tags:
        tags.append(category_tag)
    tags.append("#楽天市場")
    return list(dict.fromkeys(tags))


def build_content(item: dict[str, Any]) -> TikTokContent:
    """選ばれた商品1件から、TikTok投稿向けの素材一式を組み立てる。"""
    category = item.get("category", "") or description_generator.DEFAULT_CATEGORY
    name = item.get("name", "") or ""
    components = description_generator.get_template_components(item, category)

    seed_source = item.get("item_code") or name
    seed = sum(ord(c) for c in seed_source) if seed_source else 0
    hook = _HOOK_VARIANTS[seed % len(_HOOK_VARIANTS)]

    product_label = _product_label(name, category)
    # ✔️メリット3項目のうち、台本・テロップでは2項目までにとどめる
    # （15〜20秒の尺に収めるため）。
    features = components.checklist[:2]

    # ③ 台本（画面で読む用。1行ずつ改行して見やすくする）。
    # 0〜3秒：フック／3〜8秒：悩み／8〜14秒：特徴／14〜18秒：まとめ／
    # 18〜20秒：楽天ROOMへの導線、という構成に対応させている。
    script_lines = [hook]
    script_lines.extend(components.worry_lines)
    script_lines.append(f"この{product_label}は、")
    for feature in features:
        script_lines.append(f"・{feature}")
    script_lines.append(f"{components.closing_text}✨")
    script_lines.append("楽天ROOMに載せています。")
    script = "\n".join(script_lines)

    # ⑤ ナレーション（AI音声でそのまま読める、句読点入りの自然な文章）。
    worry_sentence = _to_sentence("".join(components.worry_lines))
    feature_sentence = "".join(_to_sentence(f) for f in features if f)
    closing_sentence = _to_sentence(components.closing_text)
    narration_parts = [
        _to_sentence(hook),
        worry_sentence,
        f"この{product_label}は、",
        feature_sentence,
        closing_sentence,
        "楽天ROOMに載せています。",
    ]
    narration = "".join(part for part in narration_parts if part)

    # ④ テロップ（1画面あたり短い文字、5〜7個程度）。
    telops = [
        hook,
        components.worry_lines[0].rstrip("、"),
        product_label,
        *features,
        components.closing_text,
        "楽天ROOMに載せています",
    ]

    # ⑥ TikTokキャプション。
    caption_lead = _CAPTION_LEAD_BY_CATEGORY.get(
        category, _CAPTION_LEAD_BY_CATEGORY[description_generator.DEFAULT_CATEGORY]
    )
    caption = f"{caption_lead}気になるアイテム✨\n楽天ROOMに載せています。"

    # ⑦ ハッシュタグ。
    hashtags = build_hashtags(category)

    # ⑧ 動画制作メモ（無料/低コストの「商品画像＋テロップ＋音声」編集を前提）。
    video_notes = [
        "0〜3秒：商品画像をゆっくりズームイン",
        f"3〜8秒：商品画像を少し横移動しながら「{telops[1]}」のテロップを表示",
        "8〜14秒：特徴のテロップを1つずつ表示（"
        + ("→".join(features) if features else product_label)
        + "）",
        "14〜20秒：商品画像＋「楽天ROOMに載せています」のテロップ、AI音声・BGMをフェードアウト",
    ]

    return TikTokContent(
        script=script,
        telops=telops,
        narration=narration,
        caption=caption,
        hashtags=hashtags,
        video_notes=video_notes,
    )
