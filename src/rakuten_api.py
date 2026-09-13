"""楽天ウェブサービス（公式API）から商品情報を取得する部分。

ROOMへの投稿やログインは一切行わない。ここで扱うのは商品検索APIのみ。

注意：楽天ウェブサービスは2026年にAPIの基盤が刷新され、次の点が変わった。

- エンドポイントのドメインが app.rakuten.co.jp から openapi.rakuten.co.jp に変わった
- 認証にアプリID（applicationId）に加えてアクセスキー（accessKey）が必要になった
- リクエストに「Origin」「Referer」ヘッダーを付け、楽天ウェブサービスのアプリ設定にある
  「許可されたWebサイト」に登録したURLと一致させないとHTTP 403で拒否されるようになった
  （ブラウザからのアクセスを前提にした仕組みのため、サーバーから呼び出す場合は
  自分でこれらのヘッダーを付ける必要がある）

楽天側の仕様は今後も変わる可能性があるため、エラーが出る場合は最新の公式ドキュメント
（https://webservice.rakuten.co.jp/documentation/ichiba-item-search）を確認し、
必要であれば config/settings.yaml の api_endpoint / allowed_origin を書き換えること。
"""

from __future__ import annotations

import time
from typing import Any

import requests

DEFAULT_SEARCH_ENDPOINT = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260401"

# 楽天ウェブサービスのレート制限を守るため、リクエストの間隔を空ける（秒）。
REQUEST_INTERVAL_SECONDS = 1.1

# レスポンス本文をログに出す際の最大文字数（ログが長くなりすぎないように）。
MAX_ERROR_BODY_LENGTH = 500


class RakutenApiError(RuntimeError):
    """楽天ウェブサービスの呼び出しに失敗したことを表すエラー。

    メッセージにはHTTPステータスコードや楽天側のエラー説明のみを含み、
    アプリIDやアクセスキーの値そのものは絶対に含めない（万一レスポンス本文に
    含まれていた場合に備えて、マスク処理をしたうえでメッセージに含めている）。
    """


def search_items(
    keyword: str,
    app_id: str,
    access_key: str | None = None,
    hits: int = 10,
    endpoint: str | None = None,
    allowed_origin: str | None = None,
) -> list[dict[str, Any]]:
    """キーワードで商品を検索し、必要な項目だけを取り出して返す。

    Args:
        keyword: 検索キーワード（例: "掃除 便利グッズ"）
        app_id: 楽天ウェブサービスのアプリID
        access_key: 楽天ウェブサービスのアクセスキー（発行されている場合）
        hits: 取得したい商品件数（最大30）
        endpoint: APIのエンドポイントURL（省略時はDEFAULT_SEARCH_ENDPOINT）
        allowed_origin: 楽天ウェブサービスの「許可されたWebサイト」に登録したURL。
            Origin/Refererヘッダーとして送信することでHTTP 403を回避する。

    Returns:
        商品情報の辞書のリスト
    """
    params = {
        "applicationId": app_id,
        "keyword": keyword,
        "hits": hits,
        "sort": "-reviewCount",  # レビュー件数が多い順（売れ行き・購入動向の目安）
    }
    headers = {}
    if access_key:
        # 公式仕様上はヘッダーでの送信が想定されているため、クエリパラメータと
        # ヘッダーの両方に含めることで、どちらの受け取り方であっても対応できるようにする。
        params["accessKey"] = access_key
        headers["accessKey"] = access_key
    if allowed_origin:
        headers["Origin"] = allowed_origin
        headers["Referer"] = allowed_origin

    try:
        response = requests.get(
            endpoint or DEFAULT_SEARCH_ENDPOINT,
            params=params,
            headers=headers,
            timeout=10,
        )
        response.raise_for_status()
    except requests.exceptions.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "不明"
        body = _mask_secrets(exc.response.text if exc.response is not None else "", app_id, access_key)
        hint = (
            "アプリID・アクセスキーが正しいか、'許可されたWebサイト'に登録したURLと"
            "allowed_origin設定が一致しているかを確認してください。"
            if status == 403
            else "アプリID・アクセスキーが正しいか、公式ドキュメントでAPI仕様が変わっていないかを確認してください。"
        )
        raise RakutenApiError(
            f"楽天ウェブサービスの呼び出しに失敗しました（キーワード: {keyword} / HTTPステータス: {status}）。"
            f"{hint} レスポンス内容: {body}"
        ) from exc
    except requests.exceptions.RequestException as exc:
        raise RakutenApiError(
            f"楽天ウェブサービスへの通信中にエラーが発生しました（キーワード: {keyword}）: {type(exc).__name__}"
        ) from exc

    payload = response.json()
    items = [_extract_item(entry["Item"]) for entry in payload.get("Items", [])]

    # 連続してAPIを叩くときにレート制限にかからないよう待機する。
    time.sleep(REQUEST_INTERVAL_SECONDS)

    return items


def _mask_secrets(text: str, app_id: str, access_key: str | None) -> str:
    """レスポンス本文に万一秘密情報が含まれていた場合に備えてマスクする。"""
    if not text:
        return "(本文なし)"
    if app_id:
        text = text.replace(app_id, "[MASKED_APP_ID]")
    if access_key:
        text = text.replace(access_key, "[MASKED_ACCESS_KEY]")
    return text[:MAX_ERROR_BODY_LENGTH]


def _extract_item(raw_item: dict[str, Any]) -> dict[str, Any]:
    """APIのレスポンスから、このプロジェクトで使う項目だけを抜き出す。"""
    image_urls = raw_item.get("mediumImageUrls") or []
    image_url = image_urls[0]["imageUrl"] if image_urls else ""

    return {
        "item_code": raw_item.get("itemCode", ""),
        "name": raw_item.get("itemName", ""),
        "catch_copy": raw_item.get("catchcopy", ""),
        # 商品説明。テーマとの関連性判定や紹介文を具体化するための材料として使う。
        "item_caption": raw_item.get("itemCaption", ""),
        "price": raw_item.get("itemPrice", 0),
        "review_average": float(raw_item.get("reviewAverage", 0) or 0),
        "review_count": int(raw_item.get("reviewCount", 0) or 0),
        "item_url": raw_item.get("itemUrl", ""),
        "image_url": image_url,
        "shop_name": raw_item.get("shopName", ""),
    }
