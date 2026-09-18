"""毎日の検索結果（上位10件）を、スマホ用投稿ページ（room/）が読み込める
JSONファイルとして書き出す部分。

既存の商品検索・条件判定・重複チェック・紹介文生成（src/main.py 以下）には
一切手を加えない。main.pyがdata/candidates/に保存した最新の候補一覧
（candidates_*.json、すでに上位N件に絞り込み済み）を読み込んで、
投稿ページ用に必要な項目だけを取り出して書き出すだけの、後処理専用の部分。
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from . import atomic_io

JST = timezone(timedelta(hours=9))

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CANDIDATES_DIR = PROJECT_ROOT / "data" / "candidates"
ROOM_PAGE_DATA_PATH = PROJECT_ROOT / "room" / "data" / "candidates.json"

# 投稿ページに表示する最大件数。
PAGE_ITEM_LIMIT = 10


def find_latest_candidates_json(directory: Path = CANDIDATES_DIR) -> Path | None:
    """data/candidates/ の中から、最も新しい candidates_*.json を返す。無ければNone。"""
    files = sorted(directory.glob("candidates_*.json"))
    return files[-1] if files else None


def build_room_page_data(
    candidates: list[dict[str, Any]],
    limit: int = PAGE_ITEM_LIMIT,
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    """候補一覧から、投稿ページで使う項目だけを取り出したデータを組み立てる。

    紹介文（description）は一切加工しない（そのままコピーできるようにするため）。
    """
    now_utc = now_utc if now_utc is not None else datetime.now(timezone.utc)
    now_jst = now_utc.astimezone(JST)

    items = []
    convenience_count = 0
    consumable_count = 0
    for item in candidates[:limit]:
        group_label = item.get("_display_group", "")
        if group_label == "便利グッズ":
            convenience_count += 1
        elif group_label in ("消耗品", "飲料"):
            consumable_count += 1
        items.append(
            {
                "item_code": item.get("item_code", ""),
                "name": item.get("name", ""),
                "price": item.get("price", 0),
                "review_average": item.get("review_average", 0),
                "review_count": item.get("review_count", 0),
                "item_url": item.get("item_url", ""),
                "image_url": item.get("image_url", ""),
                "description": item.get("description", ""),
                "category": item.get("_category", ""),
                # 投稿ページのカード・上部の内訳表示（便利グッズ／消耗品／飲料）用。
                "group_label": group_label,
            }
        )

    return {
        "generated_at_jst": now_jst.strftime("%Y/%m/%d %H:%M"),
        "items": items,
        "convenience_count": convenience_count,
        "consumable_count": consumable_count,
    }


def main() -> None:
    latest = find_latest_candidates_json()
    if latest is None:
        raise SystemExit(
            "data/candidates/ に候補一覧のJSONファイルが見つかりません。"
            "先に python -m src.main を実行してください。"
        )

    with latest.open("r", encoding="utf-8") as f:
        candidates = json.load(f)

    page_data = build_room_page_data(candidates)

    # 投稿ページ（room/index.html）が直接読み込むファイルのため、書き込み途中で
    # プロセスが終了しても壊れたJSONが残らないよう、atomic_io経由で書き出す。
    atomic_io.write_json_atomic(ROOM_PAGE_DATA_PATH, page_data)

    print(
        f"投稿ページ用データを書き出しました: {ROOM_PAGE_DATA_PATH}"
        f"（{len(page_data['items'])}件、元データ: {latest.name}）"
    )


if __name__ == "__main__":
    main()
