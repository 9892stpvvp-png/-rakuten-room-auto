"""候補商品の並び順を決める部分。

- レビュー実績（購入・利用動向の目安）による品質スコアの算出
- 同じカテゴリ内で「用途がほぼ同じ」類似商品を1件に絞り込む
- 上位N件が特定のカテゴリに偏りすぎないようにする
- 「暮らしの便利グッズ」5件＋「消耗品・飲料」5件のバランスで上位候補を選ぶ
"""

from __future__ import annotations

import difflib
import random
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

# 毎日の候補を分ける2つの枠。settings.yamlのkeywordsの各エントリに
# 付ける「group」の値として使う。
CONVENIENCE_GROUP = "convenience"  # 暮らしの便利グッズ
CONSUMABLE_GROUP = "consumable"  # 消耗品・飲料

# 「消耗品・飲料」枠のうち、飲料にあたるカテゴリ（複数本セット優先・
# アルコール除外の対象になる）。
BEVERAGE_CATEGORIES: set[str] = {"水", "お茶", "ジュース"}

# 商品名・キャッチコピーにこれらの言葉が含まれる、または「24本」「48缶」の
# ように数量＋単位が含まれる場合、複数本セット（ケース・まとめ買い）と判定する。
_MULTIPACK_WORDS = ["ケース", "箱買い", "まとめ買い", "セット買い", "業務用"]
_MULTIPACK_COUNT_PATTERN = re.compile(r"\d+\s*(本|缶|個|袋|枚)")

# 直近の投稿回数を「優先度を下げる段階」に変換する際の上限
# （3回以上はそれ以上下げない。無理に細かい数値を増やさないための単純な打ち切り）。
_MAX_TYPE_TIER = 3


def quality_score(item: dict[str, Any]) -> tuple[float, float]:
    """レビュー件数（購入・利用動向の目安）を最優先し、レビュー評価を次点で比較するためのスコア。"""
    return (item.get("review_count", 0), item.get("review_average", 0))


def type_tier(count: int) -> int:
    """直近の投稿回数を「優先度を下げる段階」に変換する
    （0回→0、1回→1、2回→2、3回以上→3。既存コードに合わせた単純な打ち切り）。
    """
    if count <= 0:
        return 0
    return min(count, _MAX_TYPE_TIER)


def priority_tier(
    item: dict[str, Any],
    recent_type_counts: dict[str, int] | None = None,
    recent_category_counts: dict[str, int] | None = None,
) -> int:
    """商品の優先度の段階（0が最優先。数字が大きいほど下げる）を返す。

    直近よく投稿している「商品タイプ」（item["_product_type"]、
    description_generator.classify_product_type()の判定結果）と
    「カテゴリー」（item["_category"]）それぞれの回数から段階を求め、
    合算する（完全除外はしない＝この段階は並び順を後ろにずらすためだけに
    使う。呼び出し側でtop_n件に絞る前の全件を渡していれば、優先度の
    高い候補が足りない場合に自動的に繰り上がる）。
    """
    tier = 0
    if recent_type_counts:
        tier += type_tier(recent_type_counts.get(item.get("_product_type", ""), 0))
    if recent_category_counts:
        tier += type_tier(recent_category_counts.get(item.get("_category", ""), 0))
    return tier


def _parse_posted_at(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def compute_recent_type_counts(
    posted_items: list[dict[str, Any]],
    type_of: Callable[[dict[str, Any]], str],
    *,
    now: datetime | None = None,
    lookback_days: int = 7,
) -> dict[str, int]:
    """直近lookback_days日以内に投稿した商品を、type_of()の判定結果ごとに数える。

    投稿日時（posted_at）が保存されていない過去データ（旧形式の投稿済み履歴）は、
    日時を勝手に推測できないため集計の対象から除外する（誤って優先度を
    下げすぎないようにするための安全側の判断。データ自体は変更しない）。
    """
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=lookback_days)
    counts: dict[str, int] = defaultdict(int)
    for entry in posted_items:
        posted_at = entry.get("posted_at")
        if not posted_at:
            continue
        parsed = _parse_posted_at(posted_at)
        if parsed is None or parsed < cutoff:
            continue
        type_value = type_of(entry)
        if type_value:
            counts[type_value] += 1
    return dict(counts)


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


def sort_by_quality(
    items: list[dict[str, Any]],
    recent_type_counts: dict[str, int] | None = None,
    recent_category_counts: dict[str, int] | None = None,
    rng: random.Random | None = None,
) -> list[dict[str, Any]]:
    """レビュー件数・レビュー評価が良い順に並べ替える。

    recent_type_counts／recent_category_countsを渡すと、直近よく投稿している
    商品タイプ・カテゴリーの優先度を段階的に下げる（priority_tier参照）。
    完全に除外するわけではないため、優先度の高い候補が足りない場合は
    diversify_top・select_balanced_topの既存の繰り上げ処理がそのまま働く。
    rngを渡すと、優先度・レビュー実績が同点の商品同士の並び順にだけ
    ランダム性を持たせる（品質順そのものは変えない＝安定ソートのため、
    先に指定したrngでシャッフルしてから並べ替える）。
    """
    working = list(items)
    if rng is not None:
        rng.shuffle(working)

    def key(item: dict[str, Any]) -> tuple[int, float, float]:
        tier = priority_tier(item, recent_type_counts, recent_category_counts)
        count, average = quality_score(item)
        return (tier, -count, -average)

    return sorted(working, key=key)


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


def is_multipack(item: dict[str, Any]) -> bool:
    """商品名・キャッチコピーから、複数本セット（ケース・箱買い・まとめ買い）と
    判定できるかどうかを返す。「24本」「48缶」のような数量＋単位の表記、または
    「ケース」「まとめ買い」等の言葉が含まれていれば複数本セットとみなす。
    """
    text = f"{item.get('name', '')} {item.get('catch_copy', '')}"
    if any(word in text for word in _MULTIPACK_WORDS):
        return True
    return bool(_MULTIPACK_COUNT_PATTERN.search(text))


def sort_consumable_items(
    items: list[dict[str, Any]],
    recent_type_counts: dict[str, int] | None = None,
    recent_category_counts: dict[str, int] | None = None,
    rng: random.Random | None = None,
) -> list[dict[str, Any]]:
    """「消耗品・飲料」枠の商品を並べ替える。

    飲料（BEVERAGE_CATEGORIES）については、複数本セット（is_multipack）の
    商品を単品の商品より優先する。それ以外（飲料以外の消耗品）は、
    これまでどおりレビュー実績（quality_score）だけで並べる。
    recent_type_counts／recent_category_counts／rngの扱いはsort_by_qualityと同じ
    （直近よく投稿しているタイプ・カテゴリーの優先度を段階的に下げつつ、
    完全除外はしない。同点の並び順にだけランダム性を持たせる）。
    """
    working = list(items)
    if rng is not None:
        rng.shuffle(working)

    def sort_key(item: dict[str, Any]) -> tuple[int, int, float, float]:
        category = item.get("_category", "")
        is_low_priority_single_beverage = category in BEVERAGE_CATEGORIES and not is_multipack(item)
        tier = priority_tier(item, recent_type_counts, recent_category_counts)
        count, average = quality_score(item)
        return (1 if is_low_priority_single_beverage else 0, tier, -count, -average)

    return sorted(working, key=sort_key)


def select_balanced_top(
    convenience_items: list[dict[str, Any]],
    consumable_items: list[dict[str, Any]],
    convenience_target: int = 5,
    consumable_target: int = 5,
    convenience_max_per_category: int = 3,
    consumable_max_per_category: int = 2,
    recent_type_counts: dict[str, int] | None = None,
    recent_category_counts: dict[str, int] | None = None,
    rng: random.Random | None = None,
) -> list[dict[str, Any]]:
    """「暮らしの便利グッズ」枠と「消耗品・飲料」枠から、5件＋5件（合計最大10件）を選ぶ。

    基本は各枠からconvenience_target件・consumable_target件を選ぶが、
    どちらかの枠の候補が不足している場合（枠内の全候補を選んでもtarget件に
    満たない場合）だけ、もう片方の枠の残り候補から不足分を補充する。
    合計はconvenience_target + consumable_target件を超えない。

    recent_type_counts／recent_category_counts／rngはsort_by_quality・
    sort_consumable_itemsにそのまま渡す（直近よく投稿している商品タイプ・
    カテゴリーの優先度を段階的に下げる。品質条件（レビュー評価・件数等）
    には一切影響しない）。
    """
    total_target = convenience_target + consumable_target

    conv_ranked = diversify_top(
        sort_by_quality(convenience_items, recent_type_counts, recent_category_counts, rng),
        top_n=convenience_target,
        max_per_category=convenience_max_per_category,
    )
    cons_ranked = diversify_top(
        sort_consumable_items(consumable_items, recent_type_counts, recent_category_counts, rng),
        top_n=consumable_target,
        max_per_category=consumable_max_per_category,
    )

    conv_chosen = conv_ranked[:convenience_target]
    conv_rest = conv_ranked[convenience_target:]
    cons_chosen = cons_ranked[:consumable_target]
    cons_rest = cons_ranked[consumable_target:]

    conv_deficit = convenience_target - len(conv_chosen)
    cons_deficit = consumable_target - len(cons_chosen)

    if conv_deficit > 0 and cons_rest:
        fill = cons_rest[:conv_deficit]
        cons_chosen = cons_chosen + fill

    if cons_deficit > 0 and conv_rest:
        fill = conv_rest[:cons_deficit]
        conv_chosen = conv_chosen + fill

    result = conv_chosen + cons_chosen

    # 念のため、同じ商品コードが両方の枠に混ざっていた場合の重複を取り除く
    # （通常はキーワードごとに検索対象が分かれているため発生しない）。
    seen_codes: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for item in result:
        code = item.get("item_code", "")
        if code and code in seen_codes:
            continue
        if code:
            seen_codes.add(code)
        deduped.append(item)

    return deduped[:total_target]
