"""投稿候補一覧をファイルに保存する部分。"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


def save_candidates(candidates: list[dict[str, Any]], output_dir: Path) -> tuple[Path, Path]:
    """投稿候補一覧をJSONとMarkdownの2種類で保存し、それぞれの保存先パスを返す。

    JSON: プログラムで再利用しやすいデータ形式
    Markdown: 人間がGitHub上やエディタでそのまま読める一覧
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"candidates_{timestamp}.json"
    markdown_path = output_dir / f"candidates_{timestamp}.md"

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(candidates, f, ensure_ascii=False, indent=2)

    markdown_path.write_text(_to_markdown(candidates, timestamp), encoding="utf-8")

    return json_path, markdown_path


def _to_markdown(candidates: list[dict[str, Any]], timestamp: str) -> str:
    lines = [
        f"# 投稿候補一覧（{timestamp}）",
        "",
        f"{len(candidates)}件の候補が見つかりました。"
        "内容と商品画像を確認し、良いものを選んで楽天ROOMに手動で投稿してください。",
        "",
    ]

    if not candidates:
        lines.append("今回は条件を満たす新しい候補が見つかりませんでした。")
        return "\n".join(lines) + "\n"

    for i, item in enumerate(candidates, start=1):
        lines.extend(
            [
                f"## {i}. {item.get('name', '(商品名不明)')}",
                "",
                f"- 価格: {item.get('price', 0):,}円",
                f"- レビュー評価: {item.get('review_average', 0):.1f}"
                f"（{item.get('review_count', 0)}件）",
                f"- ショップ: {item.get('shop_name', '')}",
                f"- 商品ページ: {item.get('item_url', '')}",
                f"- 商品画像: {item.get('image_url', '')}",
                "",
                "紹介文（コピペ用）:",
                "",
                "```",
                item.get("description", ""),
                "```",
                "",
            ]
        )

    return "\n".join(lines) + "\n"
