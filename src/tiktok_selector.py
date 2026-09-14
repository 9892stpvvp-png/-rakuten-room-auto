"""毎日の投稿候補10件（room/data/candidates.json）の中から、TikTok投稿向けに
1件だけを選ぶ部分。

商品検索・条件判定・重複チェック・紹介文生成（既存のsrc.main以下）や、
ROOM側の候補選定（便利グッズ5件＋消耗品/飲料5件）には一切手を加えない。
この部分は、すでに選ばれた10件の中から、さらにTikTok向けに1件を選ぶだけの
後処理専用の部分。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, NamedTuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TIKTOK_HISTORY_PATH = PROJECT_ROOT / "data" / "tiktok_history.json"

# 「見た瞬間に用途が分かりやすい」「悩み→解決が短時間で伝えやすい」商品として
# 優先したいジャンルのキーワード。
PRIORITY_KEYWORDS: list[str] = ["掃除", "収納", "キッチン", "時短"]

# ジャンルの偏りを避けるため、直近何件分の選定履歴を「最近選ばれたジャンル」
# として減点対象にするか。
ROTATION_LOOKBACK = 3

# 履歴ファイルに保持しておく件数（無制限に増え続けないようにするため）。
HISTORY_KEEP_LAST = 30

_CONVENIENCE_GROUP_LABEL = "便利グッズ"


class SelectionResult(NamedTuple):
    item: dict[str, Any]
    reason: str


def load_history(path: Path = TIKTOK_HISTORY_PATH) -> list[dict[str, Any]]:
    """過去の選定履歴（日付・item_code・カテゴリ・group_label）を読み込む。
    ファイルが無ければ空リストを返す。"""
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return list(data.get("history", []))


def record_selection(
    entry: dict[str, Any],
    path: Path = TIKTOK_HISTORY_PATH,
    keep_last: int = HISTORY_KEEP_LAST,
) -> None:
    """選定結果を履歴ファイルに追記する（直近keep_last件だけ保持する）。"""
    history = load_history(path)
    history.append(entry)
    history = history[-keep_last:]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump({"history": history}, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _recent_categories(history: list[dict[str, Any]], lookback: int = ROTATION_LOOKBACK) -> set[str]:
    return {entry.get("category", "") for entry in history[-lookback:] if entry.get("category")}


def _recent_item_codes(history: list[dict[str, Any]]) -> set[str]:
    """TikTok向けに過去（履歴ファイルが保持している範囲＝直近HISTORY_KEEP_LAST件）に
    選定済みの商品コード一覧を返す。同じ商品を連日選んでしまうことを避けるための、
    カテゴリ単位のローテーションとは別のitem_code単位の重複チェック用。"""
    return {entry.get("item_code", "") for entry in history if entry.get("item_code")}


def _score_item(item: dict[str, Any], recent_categories: set[str]) -> float:
    score = 0.0

    if item.get("group_label", "") == _CONVENIENCE_GROUP_LABEL:
        score += 3.0
    else:
        # 消耗品・飲料も選定対象からは外さないが、暮らしの便利グッズを
        # 基本的に優先するため加点を低くしている。
        score += 1.0

    text = f"{item.get('category', '')} {item.get('name', '')}"
    if any(keyword in text for keyword in PRIORITY_KEYWORDS):
        score += 1.5

    category = item.get("category", "")
    if category and category in recent_categories:
        # 毎回同じジャンルにならないよう、直近で選ばれたカテゴリは減点する。
        score -= 2.0

    review_count = item.get("review_count", 0) or 0
    # レビュー件数はタイブレーク程度の軽い加点にとどめる（上限を設けて、
    # 件数の差だけで優先順位が決まりすぎないようにする）。
    score += min(review_count, 5000) / 5000 * 0.5

    return score


def _build_reason(item: dict[str, Any], recent_categories: set[str]) -> str:
    parts: list[str] = []
    if item.get("group_label", "") == _CONVENIENCE_GROUP_LABEL:
        parts.append("暮らしの便利グッズ枠で")

    text = f"{item.get('category', '')} {item.get('name', '')}"
    matched = [kw for kw in PRIORITY_KEYWORDS if kw in text]
    if matched:
        parts.append(f"「{matched[0]}」に関連し、悩み→解決が短時間で伝えやすいため")

    category = item.get("category", "")
    if category and category not in recent_categories:
        parts.append("直近の選定ジャンルと重ならないため")

    if not parts:
        parts.append("レビュー評価・件数が高く、興味を引きやすいため")

    return "、".join(parts) + "選定しました。"


def select_for_tiktok(
    candidates: list[dict[str, Any]],
    history: list[dict[str, Any]] | None = None,
) -> SelectionResult:
    """本日の投稿候補10件から、TikTok向けに1件を選ぶ。

    優先順位：
    0. 直近に選定済みの商品（item_code、履歴ファイルが保持している範囲＝
       直近HISTORY_KEEP_LAST件）は基本的に除外する。ただし、本日の候補が
       すべて過去に選定済みの場合（同じ商品しか候補に無い日）まで除外すると
       選定不能になってしまうため、その場合だけ除外せず通常どおり選定する。
    1. 暮らしの便利グッズ（消耗品・飲料より優先）
    2. 掃除・収納・キッチン・時短に関連する商品
    3. レビュー件数（僅差のタイブレーク程度）
    ただし、直近の選定履歴（data/tiktok_history.json）と同じカテゴリは
    減点し、毎回同じジャンルに偏らないようにする。
    """
    if not candidates:
        raise ValueError("候補が0件のため、TikTok向け商品を選定できません。")

    history = history if history is not None else load_history()

    recent_item_codes = _recent_item_codes(history)
    not_recently_featured = [
        item for item in candidates if item.get("item_code") not in recent_item_codes
    ]
    candidate_pool = not_recently_featured or candidates

    recent_categories = _recent_categories(history)

    best_item = max(candidate_pool, key=lambda item: _score_item(item, recent_categories))
    reason = _build_reason(best_item, recent_categories)
    return SelectionResult(item=best_item, reason=reason)
