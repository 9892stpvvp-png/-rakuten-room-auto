"""過去に紹介した商品との重複をチェックし、投稿済み履歴（data/posted_items.json）を
管理する部分。

履歴ファイルは次の2つのキーを持つ。

    {
      "posted_item_codes": ["shop:item001", ...],   # 後方互換用（item_codeだけの一覧）
      "posted_items": [                               # 商品ごとの詳しい記録
        {
          "item_code": "shop:item001",
          "item_url": "https://item.rakuten.co.jp/shop/item001/",
          "product_name": "...",
          "posted_at": "2026-09-14T06:30:00+00:00",
          "category": "収納"
        },
        ...
      ]
    }

"posted_items" が無い（"posted_item_codes" だけの旧形式の）ファイルも読み込める。
履歴への書き込みは append_posted_items() だけが行う。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, NamedTuple


class PostedIndex(NamedTuple):
    """投稿済み履歴から作る、重複判定用の索引。"""

    item_codes: set[str]
    normalized_urls: set[str]


class AppendResult(NamedTuple):
    """append_posted_items() の結果。"""

    added: int
    skipped: int
    total: int


def normalize_item_url(url: str) -> str:
    """商品URLを、クエリ文字列・フラグメント・末尾スラッシュの違いを無視して
    比較できる形に正規化する。"""
    if not url:
        return ""
    url = url.split("#", 1)[0]
    url = url.split("?", 1)[0]
    return url.rstrip("/")


def load_posted_items(path: Path) -> list[dict[str, Any]]:
    """投稿済み履歴ファイルを読み込む。ファイルが無ければ空リストを返す。

    新形式（"posted_items"キー）があればそのまま返す。旧形式
    （"posted_item_codes"キーのみ）しか無い場合は、item_codeだけを持つ
    簡易レコードに変換して返す（既存データを壊さないための後方互換）。
    """
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    posted_items = data.get("posted_items")
    if posted_items is not None:
        return list(posted_items)

    return [{"item_code": code} for code in data.get("posted_item_codes", []) if code]


def load_posted_item_codes(path: Path) -> set[str]:
    """過去に投稿した商品コードの一覧だけを読み込む（後方互換用）。"""
    return {item["item_code"] for item in load_posted_items(path) if item.get("item_code")}


def build_posted_index(posted_items: list[dict[str, Any]]) -> PostedIndex:
    """投稿済み履歴から、item_codeの集合と正規化済みURLの集合を作る。"""
    item_codes = {item["item_code"] for item in posted_items if item.get("item_code")}
    normalized_urls = {
        normalize_item_url(item["item_url"]) for item in posted_items if item.get("item_url")
    }
    normalized_urls.discard("")
    return PostedIndex(item_codes=item_codes, normalized_urls=normalized_urls)


def is_posted(item: dict[str, Any], posted_index: PostedIndex) -> bool:
    """商品が投稿済み履歴に含まれるかどうかを判定する。

    1. item_code（安定した商品ID）が一致するか
    2. 正規化した商品URLが一致するか
    の順で確認する。
    """
    code = item.get("item_code")
    if code and code in posted_index.item_codes:
        return True
    url = normalize_item_url(item.get("item_url", ""))
    if url and url in posted_index.normalized_urls:
        return True
    return False


def remove_duplicates(
    items: list[dict[str, Any]],
    posted_index: PostedIndex,
) -> list[dict[str, Any]]:
    """過去に投稿済みの商品を候補から取り除く。"""
    return [item for item in items if not is_posted(item, posted_index)]


def remove_within_run_duplicates(
    items: list[dict[str, Any]],
    seen_item_codes: set[str],
) -> list[dict[str, Any]]:
    """同じ実行の中で、複数のキーワード検索にまたがって重複した商品を取り除く。

    seen_item_codes は呼び出し側がキーワードをまたいで使い回すセット。
    このセット自体を更新するため、実行済みのキーワード分がここに蓄積されていく。
    """
    unique_items = []
    for item in items:
        code = item.get("item_code")
        if code in seen_item_codes:
            continue
        seen_item_codes.add(code)
        unique_items.append(item)
    return unique_items


def append_posted_items(new_items: list[dict[str, Any]], path: Path) -> AppendResult:
    """投稿済み履歴に新しい商品を追記する（履歴ファイルを書き換える唯一の関数）。

    item_code（無ければ正規化した商品URL）で重複を判定し、既存の履歴、
    および今回追記しようとしているリスト自身の中で重複する商品は二重登録
    しない。各レコードのキー名のゆれ（product_id→item_code、name→
    product_name）も吸収する。

    将来、別の手段（手動の一括登録スクリプトや、ROOM側の正式なエクスポート
    機能等）で履歴を自動更新できるように、履歴への書き込み処理をこの関数に
    分離してある。ここでは楽天ROOMへのログイン・Cookie・セッション情報を
    使った自動取得・自動投稿は一切行わない。
    """
    existing = load_posted_items(path)
    posted_index = build_posted_index(existing)

    added = 0
    skipped = 0
    for raw_item in new_items:
        item = _normalize_incoming_item(raw_item)
        if not item.get("item_code") and not item.get("item_url"):
            # 商品を特定できる情報が無ければ登録しない。
            skipped += 1
            continue
        if is_posted(item, posted_index):
            skipped += 1
            continue

        existing.append(item)
        if item.get("item_code"):
            posted_index.item_codes.add(item["item_code"])
        normalized = normalize_item_url(item.get("item_url", ""))
        if normalized:
            posted_index.normalized_urls.add(normalized)
        added += 1

    _save_posted_items(existing, path)
    return AppendResult(added=added, skipped=skipped, total=len(existing))


def _normalize_incoming_item(raw_item: dict[str, Any]) -> dict[str, Any]:
    """取り込むレコードのキー名のゆれ（product_id・name等）を吸収して統一形式にする。"""
    return {
        "item_code": raw_item.get("item_code") or raw_item.get("product_id") or "",
        "item_url": raw_item.get("item_url", ""),
        "product_name": raw_item.get("product_name") or raw_item.get("name", ""),
        "posted_at": raw_item.get("posted_at", ""),
        "category": raw_item.get("category", ""),
    }


def _save_posted_items(posted_items: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "posted_item_codes": sorted(
            {item["item_code"] for item in posted_items if item.get("item_code")}
        ),
        "posted_items": posted_items,
    }
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
