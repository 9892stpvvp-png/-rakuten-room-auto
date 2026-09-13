"""楽天ウェブサービス（公式API）から商品情報を取得する部分。

ROOMへの投稿やログインは一切行わない。ここで扱うのは商品検索APIのみ。
"""

from __future__ import annotations

import time
from typing import Any

import requests

SEARCH_ENDPOINT = "https://app.rakuten.co.jp/services/api/IchibaItem/Search/20220601"

# 楽天ウェブサービスのレート制限を守るため、リクエストの間隔を空ける（秒）。
REQUEST_INTERVAL_SECONDS = 1.1


def search_items(
    keyword: str,
    app_id: str,
    hits: int = 10,
) -> list[dict[str, Any]]:
    """キーワードで商品を検索し、必要な項目だけを取り出して返す。

    Args:
        keyword: 検索キーワード（例: "掃除 便利グッズ"）
        app_id: 楽天ウェブサービスのアプリID
        hits: 取得したい商品件数（最大30）

    Returns:
        商品情報の辞書のリスト
    """
    params = {
        "applicationId": app_id,
        "keyword": keyword,
        "hits": hits,
        "sort": "-reviewCount",  # レビュー件数が多い順（売れ行き・購入動向の目安）
    }

    response = requests.get(SEARCH_ENDPOINT, params=params, timeout=10)
    response.raise_for_status()
    payload = response.json()

    items = [_extract_item(entry["Item"]) for entry in payload.get("Items", [])]

    # 連続してAPIを叩くときにレート制限にかからないよう待機する。
    time.sleep(REQUEST_INTERVAL_SECONDS)

    return items


def _extract_item(raw_item: dict[str, Any]) -> dict[str, Any]:
    """APIのレスポンスから、このプロジェクトで使う項目だけを抜き出す。"""
    image_urls = raw_item.get("mediumImageUrls") or []
    image_url = image_urls[0]["imageUrl"] if image_urls else ""

    return {
        "item_code": raw_item.get("itemCode", ""),
        "name": raw_item.get("itemName", ""),
        "catch_copy": raw_item.get("catchcopy", ""),
        "price": raw_item.get("itemPrice", 0),
        "review_average": float(raw_item.get("reviewAverage", 0) or 0),
        "review_count": int(raw_item.get("reviewCount", 0) or 0),
        "item_url": raw_item.get("itemUrl", ""),
        "image_url": image_url,
        "shop_name": raw_item.get("shopName", ""),
    }
