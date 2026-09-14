"""過去にROOMへ投稿済みの商品一覧を、投稿済み履歴（data/posted_items.json）へ
一括登録するための補助スクリプト。

商品ID・商品URLなどを含むJSONファイルを渡すと、既存の履歴と重複しない商品だけを
追加する。楽天ROOMへのログイン・Cookie・セッション情報を使った自動取得は行わない
（あくまで、人間が用意したリストを取り込むための処理）。スマホ投稿ページの
「投稿済みデータをコピー」ボタンでコピーしたJSONをそのままファイルに保存して
渡すこともできる。

使い方:
    python -m src.import_posted_items input.json

input.jsonの形式（商品情報の配列）:
    [
      {
        "item_code": "shop:item001",
        "item_url": "https://item.rakuten.co.jp/shop/item001/",
        "product_name": "...",
        "posted_at": "2026-09-14T12:00:00Z",
        "category": "収納"
      },
      ...
    ]

item_codeの代わりにproduct_id、product_nameの代わりにnameのキーも使える。
すでに履歴にある商品（item_code一致→商品URL一致→商品名一致、の優先順位で判定）
は二重登録しない。

item_code・item_urlが分からない過去の投稿（例えば楽天ROOMの投稿履歴画面から
商品名だけを書き写した場合等）も、商品名だけで登録できる。
    [
      {
        "product_name": "マーナ シートケース",
        "item_code": null,
        "item_url": null,
        "posted_at": null,
        "category": "過去投稿"
      },
      ...
    ]

過去のROOM投稿をまとめて初期登録したい場合は、data/past_posted_items_seed.json
に商品名一覧を追記してから、このスクリプトの引数にそのファイルを渡す。
    python -m src.import_posted_items data/past_posted_items_seed.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from . import dedupe

PROJECT_ROOT = Path(__file__).resolve().parent.parent
POSTED_ITEMS_PATH = PROJECT_ROOT / "data" / "posted_items.json"


def main(argv: list[str] | None = None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        raise SystemExit("使い方: python -m src.import_posted_items <取り込むJSONファイルのパス>")

    input_path = Path(argv[0])
    if not input_path.exists():
        raise SystemExit(f"ファイルが見つかりません: {input_path}")

    with input_path.open("r", encoding="utf-8") as f:
        new_items = json.load(f)

    if not isinstance(new_items, list):
        raise SystemExit("取り込むJSONは商品情報の配列（リスト）にしてください。")

    result = dedupe.append_posted_items(new_items, POSTED_ITEMS_PATH)
    print(
        f"投稿済み履歴に追加しました: {result.added}件"
        f"（重複のためスキップ: {result.skipped}件、履歴の総数: {result.total}件）"
    )
    print(f"保存先: {POSTED_ITEMS_PATH}")


if __name__ == "__main__":
    main()
