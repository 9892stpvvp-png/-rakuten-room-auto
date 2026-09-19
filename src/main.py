"""実行の入り口。

商品候補の収集 → 条件判定 → 重複チェック → 紹介文生成 → 候補一覧の保存 を順番に行う。
楽天ROOMへの投稿はここでは行わない。保存された候補一覧を人間が確認し、手動で投稿する。
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

from . import dedupe, description_generator, filters, ranking, rakuten_api, storage

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SETTINGS_PATH = PROJECT_ROOT / "config" / "settings.yaml"
SETTINGS_EXAMPLE_PATH = PROJECT_ROOT / "config" / "settings.example.yaml"
POSTED_ITEMS_PATH = PROJECT_ROOT / "data" / "posted_items.json"
CANDIDATES_DIR = PROJECT_ROOT / "data" / "candidates"


def load_settings() -> dict:
    settings_path = SETTINGS_PATH if SETTINGS_PATH.exists() else SETTINGS_EXAMPLE_PATH
    with settings_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _parse_keyword_entry(entry: str | dict) -> tuple[str, str, str]:
    """settings.yamlのkeywords要素から (検索キーワード, カテゴリ名, 枠) を取り出す。

    「枠」は ranking.CONVENIENCE_GROUP（暮らしの便利グッズ）か
    ranking.CONSUMABLE_GROUP（消耗品・飲料）のいずれか。省略された場合、
    または文字列だけのエントリの場合は、これまでどおり「暮らしの便利グッズ」
    として扱う。
    """
    if isinstance(entry, dict):
        return (
            entry["keyword"],
            entry.get("category", description_generator.DEFAULT_CATEGORY),
            entry.get("group", ranking.CONVENIENCE_GROUP),
        )
    return entry, description_generator.DEFAULT_CATEGORY, ranking.CONVENIENCE_GROUP


def _display_group(group: str, category: str) -> str:
    """スマホ投稿ページ（room/）に表示する小さなカテゴリ表示（便利グッズ／消耗品／飲料）を決める。"""
    if group == ranking.CONVENIENCE_GROUP:
        return "便利グッズ"
    if category in ranking.BEVERAGE_CATEGORIES:
        return "飲料"
    return "消耗品"


def main() -> None:
    load_dotenv()
    app_id = os.environ.get("RAKUTEN_APP_ID")
    access_key = os.environ.get("RAKUTEN_ACCESS_KEY")

    if not app_id or app_id == "ここにアプリIDを入力":
        raise SystemExit(
            "RAKUTEN_APP_ID が設定されていません。"
            ".env ファイル、またはGitHubのRepository SecretsにアプリIDを設定してください"
            "（.env.example を参照）。"
        )
    if not access_key:
        print(
            "警告: RAKUTEN_ACCESS_KEY が設定されていません。"
            "2026年以降の楽天ウェブサービスではアクセスキーが必要な場合があります。"
            "APIエラーが出る場合はアクセスキーを設定してください。"
        )

    settings = load_settings()
    criteria = settings["selection_criteria"]
    endpoint = settings.get("api_endpoint")
    allowed_origin = settings.get("allowed_origin")
    ng_keywords = settings.get("ng_keywords", [])
    off_theme_keywords = settings.get("off_theme_keywords", [])
    alcohol_keywords = settings.get("alcohol_keywords", [])
    consumable_durable_accessory_keywords = settings.get("consumable_durable_accessory_keywords", [])
    base_hashtags = settings.get("default_hashtags", ["#暮らしの便利グッズ"])
    posted_items_history = dedupe.load_posted_items(POSTED_ITEMS_PATH)
    posted_index = dedupe.build_posted_index(posted_items_history)
    posted_history_total = len(posted_items_history)
    posted_excluded_by_item_code = 0
    posted_excluded_by_url = 0
    posted_excluded_by_product_name = 0
    posted_excluded_by_match_keywords = 0
    seen_item_codes: set[str] = set()

    # フェーズ1: キーワードごとに検索し、条件を満たさない商品・重複を取り除く。
    # 「暮らしの便利グッズ」枠と「消耗品・飲料」枠は、keywordsの各エントリに
    # 付けた group（ranking.CONVENIENCE_GROUP / ranking.CONSUMABLE_GROUP）で判別する。
    filtered_items = []
    for entry in settings["keywords"]:
        keyword, category, group = _parse_keyword_entry(entry)

        try:
            items = rakuten_api.search_items(
                keyword=keyword,
                app_id=app_id,
                access_key=access_key,
                hits=settings.get("items_per_keyword", 10),
                endpoint=endpoint,
                allowed_origin=allowed_origin,
            )
        except rakuten_api.RakutenApiError as exc:
            raise SystemExit(str(exc)) from exc

        items = filters.filter_by_review(
            items,
            min_review_average=criteria["min_review_average"],
            min_review_count=criteria["min_review_count"],
        )
        items = filters.filter_by_ng_keywords(items, ng_keywords)
        items = filters.filter_by_off_theme_keywords(items, off_theme_keywords)
        if category in ranking.BEVERAGE_CATEGORIES:
            items = filters.filter_by_alcohol_keywords(items, alcohol_keywords)
        if group == ranking.CONSUMABLE_GROUP:
            items = filters.filter_by_durable_accessory_keywords(
                items, consumable_durable_accessory_keywords
            )
        items, posted_exclusion_breakdown = dedupe.remove_duplicates_with_breakdown(items, posted_index)
        posted_excluded_by_item_code += posted_exclusion_breakdown["item_code"]
        posted_excluded_by_url += posted_exclusion_breakdown["url"]
        posted_excluded_by_product_name += posted_exclusion_breakdown["product_name"]
        posted_excluded_by_match_keywords += posted_exclusion_breakdown["match_keywords"]
        items = dedupe.remove_within_run_duplicates(items, seen_item_codes)

        for item in items:
            item["_group"] = group
            # 「消耗品・飲料」枠は検索キーワード自体が商品種別そのものなので、
            # 「暮らしの便利グッズ」枠のような商品名からのカテゴリ補正は行わない
            # （補正ロジックのキーワード一覧は便利グッズ向けのため、例えば
            # 洗剤の商品名にある「洗剤」の一語で掃除カテゴリに誤補正されるのを防ぐ）。
            if group == ranking.CONVENIENCE_GROUP:
                item["_category"] = description_generator.refine_category(item, category)
            else:
                item["_category"] = category
            item["_display_group"] = _display_group(item["_group"], item["_category"])
        filtered_items.extend(items)

    # フェーズ2: 同じカテゴリ内で用途がほぼ同じ類似商品を1件に絞る。
    unique_items = ranking.deduplicate_similar_items(
        filtered_items,
        similarity_threshold=settings.get("similarity_threshold", 0.55),
    )

    # フェーズ3: 「暮らしの便利グッズ」5件＋「消耗品・飲料」5件のバランスで上位候補を選ぶ
    # （どちらかの枠が5件に満たない場合だけ、もう片方の枠から補充する）。
    convenience_items = [item for item in unique_items if item["_group"] == ranking.CONVENIENCE_GROUP]
    consumable_items = [item for item in unique_items if item["_group"] == ranking.CONSUMABLE_GROUP]
    candidates = ranking.select_balanced_top(
        convenience_items,
        consumable_items,
        convenience_target=settings.get("convenience_target", 5),
        consumable_target=settings.get("consumable_target", 5),
        convenience_max_per_category=settings.get("summary_max_per_category", 3),
        consumable_max_per_category=settings.get("consumable_max_per_category", 2),
    )

    # フェーズ4: 紹介文を生成する（商品固有の特徴が分かればそれを反映する）。
    # 選ばれた最終候補（最大10件）に対してまとめて生成することで、同じ日の
    # バッチ内で①キャッチコピー・⑤締めの一言が両方一致してしまう（構成が
    # 強く似た文章になる）組み合わせを避けやすくしている
    # （generate_descriptions_for_batch）。選ばれなかった候補の紹介文まで
    # 生成しないため、以前（全unique_itemsに対して1件ずつ生成）より無駄も無い。
    descriptions = description_generator.generate_descriptions_for_batch(
        candidates,
        [item["_category"] for item in candidates],
        base_hashtags=base_hashtags,
        max_length=settings.get("description_max_length", 500),
    )
    for item, description in zip(candidates, descriptions):
        item["description"] = description

    json_path, markdown_path = storage.save_candidates(candidates, CANDIDATES_DIR)
    print(f"{len(candidates)}件の投稿候補を保存しました。")
    print(f"  - 一覧（人間が見る用）: {markdown_path}")
    print(f"  - 一覧（データ用）: {json_path}")
    print("内容を確認し、良いものを選んで楽天ROOMに手動で投稿してください。")
    posted_excluded_total = (
        posted_excluded_by_item_code
        + posted_excluded_by_url
        + posted_excluded_by_product_name
        + posted_excluded_by_match_keywords
    )
    print(
        f"投稿済み履歴による除外: {posted_excluded_total}件"
        f"（item_code: {posted_excluded_by_item_code}件 / URL: {posted_excluded_by_url}件"
        f" / 商品名: {posted_excluded_by_product_name}件"
        f" / match_keywords: {posted_excluded_by_match_keywords}件、履歴の総数: {posted_history_total}件）"
    )

    write_github_step_summary(
        storage.build_posted_history_summary_markdown(
            excluded_by_item_code=posted_excluded_by_item_code,
            excluded_by_url=posted_excluded_by_url,
            excluded_by_product_name=posted_excluded_by_product_name,
            excluded_by_match_keywords=posted_excluded_by_match_keywords,
            new_candidate_count=len(candidates),
            history_total=posted_history_total,
        )
    )
    write_github_step_summary(
        storage.build_summary_markdown(candidates, limit=settings.get("summary_item_limit", 10))
    )


def write_github_step_summary(markdown: str) -> None:
    """GitHub ActionsのSummary欄に候補一覧を書き出す。

    GITHUB_STEP_SUMMARY が設定されていない環境（自分のパソコンでの実行など）では何もしない。
    スマートフォンでもGitHubの実行結果ページを開くだけで候補を確認できるようにするためのもの。
    """
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return

    with open(summary_path, "a", encoding="utf-8") as f:
        f.write(markdown)


if __name__ == "__main__":
    main()
