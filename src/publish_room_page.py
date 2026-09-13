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
    for item in candidates[:limit]:
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
            }
        )

    return {
        "generated_at_jst": now_jst.strftime("%Y/%m/%d %H:%M"),
        "items": items,
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

    ROOM_PAGE_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with ROOM_PAGE_DATA_PATH.open("w", encoding="utf-8") as f:
        json.dump(page_data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(
        f"投稿ページ用データを書き出しました: {ROOM_PAGE_DATA_PATH}"
        f"（{len(page_data['items'])}件、元データ: {latest.name}）"
    )


if __name__ == "__main__":
    main()
