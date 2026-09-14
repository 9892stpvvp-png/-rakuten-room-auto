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

重複判定は次の優先順位で行う（is_posted / match_posted_reason）。

    1. item_code（安定した商品ID）が一致するか
    2. 正規化した商品URLが一致するか
    3. 正規化した商品名が一致するか（item_code・item_urlが無い過去投稿等の
       ための補助的な判定。誤判定を避けるため、正規化後の「完全一致」だけを
       見る。あいまい一致・部分一致はしない）
    4. match_keywords（登録した特徴語）がすべて商品名に含まれるか（3の
       完全一致よりさらに情報が少ない過去投稿——スクリーンショットからしか
       商品を特定できない場合等——のための補助判定。他の3つより優先度を
       下げてある。全語一致（AND）だけを見る。1語だけの登録は誤判定の
       リスクが高いため無視する）
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any, NamedTuple


class PostedIndex(NamedTuple):
    """投稿済み履歴から作る、重複判定用の索引。"""

    item_codes: set[str]
    normalized_urls: set[str]
    normalized_product_names: set[str]
    match_keyword_sets: list[tuple[str, ...]]


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


# 商品名の正規化で無視する販売文言・宣伝表現（例として挙げられたものだけを
# 対象にする。ブランド名・シリーズ名・サイズ・容量・本数・個数・型番などの
# 商品を区別する情報は対象に含めない）。
_AD_PHRASE_PATTERNS: list[re.Pattern[str]] = [
    re.compile("送料無料"),
    re.compile(r"ポイント\s*\d*\s*倍"),
    re.compile("ランキング"),
    re.compile("公式"),
    re.compile("限定"),
    re.compile("レビュー特典"),
    re.compile("ギフト"),
    re.compile("SNSで(?:も)?話題"),
    re.compile("365日発送"),
    re.compile("クーポン"),
    re.compile("セール"),
]

# 装飾記号（【】《》等の括弧記号そのもの・絵文字用の記号）。括弧の中身
# （商品名の一部であることが多い）は消さず、記号だけを取り除く。
_DECORATIVE_CHARS_PATTERN = re.compile(
    r"[【】《》〈〉「」『』［］\[\]()（）!！?？・*＊#＃★☆]+"
)

# よく使われる絵文字の範囲（Unicodeブロック単位）。厳密な絵文字判定ではないが、
# 商品名比較の邪魔になりやすい代表的な範囲だけを対象にしている。
_EMOJI_PATTERN = re.compile(
    "["
    "\U0001f300-\U0001faff"
    "\U00002600-\U000027bf"
    "\U0001f1e6-\U0001f1ff"
    "\U00002b00-\U00002bff"
    "️"
    "]+",
    flags=re.UNICODE,
)

_WHITESPACE_PATTERN = re.compile(r"\s+")


def normalize_product_name(name: str) -> str:
    """商品名を、販売文言・装飾記号・絵文字・余分な空白・全角/半角差・英字の
    大文字小文字の違いを無視して比較できる形に正規化する。

    ブランド名・シリーズ名・サイズ・容量・本数・個数・型番など、商品を
    区別するために重要な情報（例：「ワイド」と「ラージ」、「1個」と
    「5個セット」）はそのまま残す。この関数はあくまで「正規化後の完全一致」で
    重複判定するための下ごしらえであり、あいまい一致（部分一致・類似度判定）
    は行わない（似ているだけの別商品を誤って除外しないため）。
    """
    if not name:
        return ""

    normalized = unicodedata.normalize("NFKC", name)
    normalized = _EMOJI_PATTERN.sub(" ", normalized)
    for pattern in _AD_PHRASE_PATTERNS:
        normalized = pattern.sub(" ", normalized)
    normalized = _DECORATIVE_CHARS_PATTERN.sub(" ", normalized)
    normalized = normalized.lower()
    return _WHITESPACE_PATTERN.sub(" ", normalized).strip()


# match_keywordsによる補助判定を有効にするために必要な最低キーワード数。
# 1語だけの登録（例：["tower"]、["マーナ"]、["収納"]）は、無関係な商品まで
# 誤って除外してしまうリスクが高いため、判定に使わない（登録自体は
# 妨げないが、索引の構築時に無視される＝一致判定には一切影響しない）。
_MIN_MATCH_KEYWORDS = 2


def _normalize_for_keyword_match(text: str) -> str:
    """match_keywordsの一致判定用に、商品名・キーワードをNFKC正規化・
    小文字化する（normalize_product_nameと異なり、販売文言・装飾記号の
    除去は行わない。あくまで全角/半角・大文字小文字の違いだけを吸収する）。
    """
    if not text:
        return ""
    return unicodedata.normalize("NFKC", text).lower()


def match_all_keywords(candidate_name: str, keywords: list[str]) -> bool:
    """候補の商品名に、指定したキーワードが（NFKC正規化・小文字化した上で）
    すべて含まれているかどうかを判定する（AND判定。1つでも欠けていれば
    不一致）。

    キーワードが _MIN_MATCH_KEYWORDS 未満の場合は、誤判定を避けるため
    常にFalseを返す（「山崎実業」単独のように広すぎる登録で無関係な
    商品まで除外してしまうことを防ぐ）。
    """
    valid_keywords = [kw for kw in keywords if kw and kw.strip()]
    if len(valid_keywords) < _MIN_MATCH_KEYWORDS:
        return False

    normalized_candidate = _normalize_for_keyword_match(candidate_name)
    if not normalized_candidate:
        return False

    for keyword in valid_keywords:
        normalized_keyword = _normalize_for_keyword_match(keyword)
        if not normalized_keyword or normalized_keyword not in normalized_candidate:
            return False
    return True


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
    """投稿済み履歴から、item_code・正規化済みURL・正規化済み商品名・
    match_keywordsの組の一覧を作る。"""
    item_codes = {item["item_code"] for item in posted_items if item.get("item_code")}

    normalized_urls = {
        normalize_item_url(item["item_url"]) for item in posted_items if item.get("item_url")
    }
    normalized_urls.discard("")

    normalized_product_names = {
        normalize_product_name(item["product_name"])
        for item in posted_items
        if item.get("product_name")
    }
    normalized_product_names.discard("")

    match_keyword_sets: list[tuple[str, ...]] = []
    for item in posted_items:
        keywords = item.get("match_keywords") or []
        valid_keywords = tuple(kw for kw in keywords if kw and kw.strip())
        if len(valid_keywords) >= _MIN_MATCH_KEYWORDS:
            match_keyword_sets.append(valid_keywords)

    return PostedIndex(
        item_codes=item_codes,
        normalized_urls=normalized_urls,
        normalized_product_names=normalized_product_names,
        match_keyword_sets=match_keyword_sets,
    )


def match_posted_reason(item: dict[str, Any], posted_index: PostedIndex) -> str | None:
    """商品が投稿済み履歴に含まれるかどうかを判定し、一致した根拠
    （"item_code" / "url" / "product_name" / "match_keywords"）を返す。
    一致しなければNone。

    1. item_code（安定した商品ID）が一致するか
    2. 正規化した商品URLが一致するか
    3. 正規化した商品名が一致するか（item_code・URLが取れない過去投稿向けの
       補助判定。他の2つより優先度を下げる）
    4. 登録したmatch_keywordsがすべて商品名に含まれるか（3よりさらに情報が
       少ない過去投稿向けの補助判定。他の3つより優先度を下げる）

    候補商品（キー名"name"）・投稿済み履歴のレコード（キー名"product_name"）
    のどちらの形でも商品名を拾えるようにしている。
    """
    code = item.get("item_code")
    if code and code in posted_index.item_codes:
        return "item_code"

    url = normalize_item_url(item.get("item_url", ""))
    if url and url in posted_index.normalized_urls:
        return "url"

    raw_name = item.get("name") or item.get("product_name") or ""

    normalized_name = normalize_product_name(raw_name)
    if normalized_name and normalized_name in posted_index.normalized_product_names:
        return "product_name"

    for keywords in posted_index.match_keyword_sets:
        if match_all_keywords(raw_name, keywords):
            return "match_keywords"

    return None


def is_posted(item: dict[str, Any], posted_index: PostedIndex) -> bool:
    """商品が投稿済み履歴に含まれるかどうかを判定する（判定順位はmatch_posted_reason参照）。"""
    return match_posted_reason(item, posted_index) is not None


def remove_duplicates(
    items: list[dict[str, Any]],
    posted_index: PostedIndex,
) -> list[dict[str, Any]]:
    """過去に投稿済みの商品を候補から取り除く。"""
    return [item for item in items if not is_posted(item, posted_index)]


def remove_duplicates_with_breakdown(
    items: list[dict[str, Any]],
    posted_index: PostedIndex,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """過去に投稿済みの商品を候補から取り除きつつ、item_code／url／product_name
    ／match_keywordsのどの判定方法で何件除外したかを集計する
    （GitHub Actions Summary表示用）。
    """
    kept: list[dict[str, Any]] = []
    breakdown = {"item_code": 0, "url": 0, "product_name": 0, "match_keywords": 0}
    for item in items:
        reason = match_posted_reason(item, posted_index)
        if reason is None:
            kept.append(item)
        else:
            breakdown[reason] += 1
    return kept, breakdown


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

    item_code→商品URL→商品名→match_keywordsの順で重複を判定し、既存の履歴、
    および今回追記しようとしているリスト自身の中で重複する商品は二重登録
    しない。各レコードのキー名のゆれ（product_id→item_code、name→
    product_name）も吸収する。item_code・商品URL・商品名が無く、
    match_keywordsだけの過去投稿（例：`{"match_keywords": ["マーナ",
    "シートケース"], "item_code": null, "item_url": null}`）も登録できる。

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
        if (
            not item.get("item_code")
            and not item.get("item_url")
            and not item.get("product_name")
            and not item.get("match_keywords")
        ):
            # 商品を特定できる情報（商品コード・商品URL・商品名・
            # match_keywordsのいずれも）が無ければ登録しない。
            skipped += 1
            continue
        if is_posted(item, posted_index):
            skipped += 1
            continue

        existing.append(item)
        if item.get("item_code"):
            posted_index.item_codes.add(item["item_code"])
        normalized_url = normalize_item_url(item.get("item_url", ""))
        if normalized_url:
            posted_index.normalized_urls.add(normalized_url)
        normalized_name = normalize_product_name(item.get("product_name", ""))
        if normalized_name:
            posted_index.normalized_product_names.add(normalized_name)
        valid_keywords = tuple(kw for kw in item.get("match_keywords", []) if kw and kw.strip())
        if len(valid_keywords) >= _MIN_MATCH_KEYWORDS:
            posted_index.match_keyword_sets.append(valid_keywords)
        added += 1

    _save_posted_items(existing, path)
    return AppendResult(added=added, skipped=skipped, total=len(existing))


def _clean_str(value: Any) -> str:
    """None・欠落・空文字を全て空文字に揃える（JSONの null を安全に扱うため）。"""
    return value if isinstance(value, str) and value else ""


def _clean_keywords(value: Any) -> list[str]:
    """match_keywordsの値（リスト以外・null・空文字混入等）を安全なリストに揃える。"""
    if not isinstance(value, list):
        return []
    return [kw for kw in value if isinstance(kw, str) and kw.strip()]


def _normalize_incoming_item(raw_item: dict[str, Any]) -> dict[str, Any]:
    """取り込むレコードのキー名のゆれ（product_id・name等）や、値がnullの
    場合を吸収して統一形式にする。"""
    return {
        "item_code": _clean_str(raw_item.get("item_code")) or _clean_str(raw_item.get("product_id")),
        "item_url": _clean_str(raw_item.get("item_url")),
        "product_name": _clean_str(raw_item.get("product_name")) or _clean_str(raw_item.get("name")),
        "posted_at": _clean_str(raw_item.get("posted_at")),
        "category": _clean_str(raw_item.get("category")),
        "match_keywords": _clean_keywords(raw_item.get("match_keywords")),
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
