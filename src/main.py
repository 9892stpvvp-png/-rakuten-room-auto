"""実行の入り口。

商品候補の収集 → 条件判定 → 重複チェック → 紹介文生成 → 候補一覧の保存 を順番に行う。
楽天ROOMへの投稿はここでは行わない。保存された候補一覧を人間が確認し、手動で投稿する。
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

from . import dedupe, description_generator, filters, rakuten_api, storage

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SETTINGS_PATH = PROJECT_ROOT / "config" / "settings.yaml"
SETTINGS_EXAMPLE_PATH = PROJECT_ROOT / "config" / "settings.example.yaml"
POSTED_ITEMS_PATH = PROJECT_ROOT / "data" / "posted_items.json"
CANDIDATES_DIR = PROJECT_ROOT / "data" / "candidates"


def load_settings() -> dict:
    settings_path = SETTINGS_PATH if SETTINGS_PATH.exists() else SETTINGS_EXAMPLE_PATH
    with settings_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main() -> None:
    load_dotenv()
    app_id = os.environ.get("RAKUTEN_APP_ID")
    if not app_id or app_id == "ここにアプリIDを入力":
        raise SystemExit(
            "RAKUTEN_APP_ID が設定されていません。"
            ".env ファイルに楽天ウェブサービスのアプリIDを設定してください（.env.example を参照）。"
        )

    settings = load_settings()
    criteria = settings["selection_criteria"]
    posted_item_codes = dedupe.load_posted_item_codes(POSTED_ITEMS_PATH)

    candidates = []
    for keyword in settings["keywords"]:
        items = rakuten_api.search_items(
            keyword=keyword,
            app_id=app_id,
            hits=settings.get("items_per_keyword", 10),
        )
        items = filters.filter_by_review(
            items,
            min_review_average=criteria["min_review_average"],
            min_review_count=criteria["min_review_count"],
        )
        items = dedupe.remove_duplicates(items, posted_item_codes)

        for item in items:
            item["description"] = description_generator.generate_description(
                item,
                hashtags=settings.get("default_hashtags", []),
                max_length=settings.get("description_max_length", 500),
            )
            candidates.append(item)

    output_path = storage.save_candidates(candidates, CANDIDATES_DIR)
    print(f"{len(candidates)}件の投稿候補を保存しました: {output_path}")
    print("内容を確認し、良いものを選んで楽天ROOMに手動で投稿してください。")


if __name__ == "__main__":
    main()
