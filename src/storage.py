"""投稿候補一覧をファイルに保存する部分。"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


def save_candidates(candidates: list[dict[str, Any]], output_dir: Path) -> tuple[Path, Path]:
    """投稿候補一覧をJSONとMarkdownの2種類で保存し、それぞれの保存先パスを返す。

    JSON: プログラムで再利用しやすいデータ形式
    Markdown: 人間がGitHub上やエディタでそのまま読める一覧（全件）
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"candidates_{timestamp}.json"
    markdown_path = output_dir / f"candidates_{timestamp}.md"

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(candidates, f, ensure_ascii=False, indent=2)

    markdown_path.write_text(
        render_candidates_markdown(
            candidates, title=f"投稿候補一覧（{timestamp}）", include_extra=True
        ),
        encoding="utf-8",
    )

    return json_path, markdown_path


def build_summary_markdown(candidates: list[dict[str, Any]], limit: int = 10) -> str:
    """GitHub ActionsのSummary（実行結果画面）に表示するための、上位N件の一覧を作る。

    スマートフォンのGitHubアプリ／ブラウザからでも、ZIPをダウンロードせずに
    候補の中身（商品名・価格・レビュー評価・件数・商品URL・紹介文）を確認できるようにする。
    """
    return render_candidates_markdown(
        candidates,
        title="楽天ROOM 投稿候補一覧（このページで確認できます）",
        limit=limit,
    )


def build_posted_history_summary_markdown(
    excluded_by_item_code: int,
    excluded_by_url: int,
    excluded_by_product_name: int,
    excluded_by_match_keywords: int,
    new_candidate_count: int,
    history_total: int,
) -> str:
    """GitHub ActionsのSummaryに表示する、投稿済み履歴による重複防止の状況。

    ・投稿済み履歴によって除外した件数（item_code／URL／商品名／
      match_keywordsの内訳つき）
    ・今回選ばれた新規候補の件数
    ・現在の投稿済み履歴の総数
    をまとめて表示する。
    """
    total_excluded = (
        excluded_by_item_code + excluded_by_url + excluded_by_product_name + excluded_by_match_keywords
    )
    lines = [
        "## 投稿済み履歴による重複防止",
        "",
        f"- 投稿済み履歴によって除外した件数: {total_excluded}件",
        f"  - item_codeによる除外件数: {excluded_by_item_code}件",
        f"  - URLによる除外件数: {excluded_by_url}件",
        f"  - 商品名履歴による除外件数: {excluded_by_product_name}件",
        f"  - match_keywordsによる除外件数: {excluded_by_match_keywords}件",
        f"- 今回選ばれた新規候補: {new_candidate_count}件",
        f"- 現在の投稿済み履歴の総数: {history_total}件",
        "",
    ]
    return "\n".join(lines) + "\n"


def render_candidates_markdown(
    candidates: list[dict[str, Any]],
    title: str,
    limit: int | None = None,
    include_extra: bool = False,
) -> str:
    total = len(candidates)
    shown = candidates if limit is None else candidates[:limit]

    lines = [f"# {title}", ""]

    if total == 0:
        lines.append("今回は条件を満たす新しい候補が見つかりませんでした。")
        return "\n".join(lines) + "\n"

    lines.append(
        f"{total}件の候補が見つかりました。"
        "内容と商品画像を確認し、良いものを選んで楽天ROOMに手動で投稿してください。"
    )
    if limit is not None and total > limit:
        lines.append(
            f"※ここでは上位{limit}件のみ表示しています。全件はActionsの「Artifacts」から"
            "ダウンロードできる一覧ファイルで確認できます。"
        )
    lines.append("")

    for i, item in enumerate(shown, start=1):
        block = [
            f"## {i}. {item.get('name', '(商品名不明)')}",
            "",
            f"- 価格: {item.get('price', 0):,}円",
            f"- レビュー評価: {item.get('review_average', 0):.1f}"
            f"（{item.get('review_count', 0)}件）",
            f"- 商品ページ: {item.get('item_url', '')}",
        ]
        if include_extra:
            block.append(f"- ショップ: {item.get('shop_name', '')}")
            block.append(f"- 商品画像: {item.get('image_url', '')}")
        block.extend(
            [
                "",
                "紹介文（コピペ用）:",
                "",
                "```",
                item.get("description", ""),
                "```",
                "",
            ]
        )
        lines.extend(block)

    return "\n".join(lines) + "\n"
