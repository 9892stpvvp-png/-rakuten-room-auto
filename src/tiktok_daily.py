"""毎日のROOM投稿候補10件から、TikTok投稿向けのコンテンツ（1商品選定＋
台本・テロップ・ナレーション・キャプション・ハッシュタグ・動画制作メモ）を
生成し、tiktok/daily_content.json・tiktok/daily_content.md として書き出す
部分。

商品検索・条件判定・重複チェック・紹介文生成・ROOM側の候補選定（便利グッズ
5件＋消耗品/飲料5件）や、スマホ用投稿ページ（room/）には一切手を加えない。
room/data/candidates.json（ROOM候補生成が成功したときだけ更新される、
最新の投稿ページ用データ）を入力として使うため、ROOM候補生成が失敗した
回はこのファイルが更新されず、TikTok側も古いデータのまま実行されてしまう
リスクがある。そのため、GitHub Actions側でもROOM候補生成が成功した直後の
ステップとしてのみ実行する構成にしている（失敗時は後続ステップ自体が
実行されないため、TikTok側だけ単独で不完全なデータを作ることはない）。

今回はここまで（1商品選定＋投稿素材のテキスト生成＋スマホ表示）で止める。
動画ファイルの生成・外部の動画生成API連携・TikTokへの自動投稿は行わない。
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from . import atomic_io, tiktok_content_generator, tiktok_selector

JST = timezone(timedelta(hours=9))

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ROOM_PAGE_DATA_PATH = PROJECT_ROOT / "room" / "data" / "candidates.json"
TIKTOK_DIR = PROJECT_ROOT / "tiktok"
TIKTOK_JSON_PATH = TIKTOK_DIR / "daily_content.json"
TIKTOK_MARKDOWN_PATH = TIKTOK_DIR / "daily_content.md"


def load_room_candidates(path: Path = ROOM_PAGE_DATA_PATH) -> list[dict[str, Any]]:
    """ROOM側の投稿ページ用データ（room/data/candidates.json）から、
    本日の投稿候補10件を読み込む。ファイルが無い・候補が0件の場合は、
    不完全なTikTokデータを作らないようにSystemExitする。"""
    if not path.exists():
        raise SystemExit(
            f"{path} が見つかりません。先にROOM候補生成（python -m src.main "
            "および python -m src.publish_room_page）を実行してください。"
        )

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    items = data.get("items") or []
    if not items:
        raise SystemExit(
            f"{path} に投稿候補が0件のため、TikTok向けコンテンツを生成できません。"
        )
    return items


def build_daily_content(
    candidates: list[dict[str, Any]],
    history: list[dict[str, Any]] | None = None,
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    """本日の投稿候補から、TikTok向けコンテンツ1件分のデータを組み立てる。"""
    now_utc = now_utc if now_utc is not None else datetime.now(timezone.utc)
    now_jst = now_utc.astimezone(JST)

    selection = tiktok_selector.select_for_tiktok(candidates, history=history)
    item = selection.item
    content = tiktok_content_generator.build_content(item)

    return {
        "generated_at": now_jst.strftime("%Y-%m-%dT%H:%M:%S+09:00"),
        "product_name": item.get("name", ""),
        "item_code": item.get("item_code", ""),
        "item_url": item.get("item_url", ""),
        "image_url": item.get("image_url", ""),
        "category": item.get("category", ""),
        "group_label": item.get("group_label", ""),
        "selection_reason": selection.reason,
        "script": content.script,
        "telops": content.telops,
        "narration": content.narration,
        "caption": content.caption,
        "hashtags": content.hashtags,
        "video_notes": content.video_notes,
    }


def render_markdown(data: dict[str, Any]) -> str:
    """スマホでも見やすい、TikTokコンテンツのMarkdown版を組み立てる。"""
    lines = [
        "# 今日のTikTok投稿コンテンツ",
        "",
        f"最終更新：{data.get('generated_at', '')}",
        "",
        f"## 商品：{data.get('product_name', '(商品名不明)')}",
        "",
        f"- カテゴリ：{data.get('category', '')}（{data.get('group_label', '')}）",
        f"- 商品ページ：{data.get('item_url', '')}",
        f"- 商品画像：{data.get('image_url', '')}",
        "",
        "### 選定理由",
        "",
        data.get("selection_reason", ""),
        "",
        "### 台本（15〜20秒想定）",
        "",
        "```",
        data.get("script", ""),
        "```",
        "",
        "### テロップ",
        "",
    ]
    for i, telop in enumerate(data.get("telops", []), start=1):
        lines.append(f"{i}. {telop}")
    lines.extend(
        [
            "",
            "### ナレーション",
            "",
            "```",
            data.get("narration", ""),
            "```",
            "",
            "### TikTokキャプション",
            "",
            "```",
            data.get("caption", ""),
            "```",
            "",
            "### ハッシュタグ",
            "",
            " ".join(data.get("hashtags", [])),
            "",
            "### 動画制作メモ",
            "",
        ]
    )
    for note in data.get("video_notes", []):
        lines.append(f"- {note}")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    # モジュールのグローバル定数をその都度読み直すため、load_room_candidates()・
    # load_history()・record_selection()の既定値には頼らず、ここで明示的に
    # 現在のパス（ROOM_PAGE_DATA_PATH等）を渡している（テストからパスを
    # 差し替えられるようにするため）。
    candidates = load_room_candidates(ROOM_PAGE_DATA_PATH)
    history = tiktok_selector.load_history(tiktok_selector.TIKTOK_HISTORY_PATH)
    data = build_daily_content(candidates, history=history)

    # 書き込み途中でプロセスが終了しても壊れた（書きかけの）ファイルが残らない
    # よう、atomic_io経由で書き出す（GitHub Actionsのジョブタイムアウト・
    # キャンセル対策）。
    atomic_io.write_json_atomic(TIKTOK_JSON_PATH, data)
    atomic_io.write_text_atomic(TIKTOK_MARKDOWN_PATH, render_markdown(data))

    tiktok_selector.record_selection(
        {
            "date": datetime.now(JST).strftime("%Y-%m-%d"),
            "item_code": data.get("item_code", ""),
            "category": data.get("category", ""),
            "group_label": data.get("group_label", ""),
        },
        path=tiktok_selector.TIKTOK_HISTORY_PATH,
    )

    print(f"TikTok向けコンテンツを生成しました: {data.get('product_name', '')}")
    print(f"  - JSON: {TIKTOK_JSON_PATH}")
    print(f"  - Markdown: {TIKTOK_MARKDOWN_PATH}")
    print(f"選定理由: {data.get('selection_reason', '')}")

    write_github_step_summary(
        "## 今日のTikTok投稿コンテンツ\n\n"
        f"- 選ばれた商品: {data.get('product_name', '')}\n"
        f"- 選定理由: {data.get('selection_reason', '')}\n"
    )


def write_github_step_summary(markdown: str) -> None:
    """GitHub ActionsのSummary欄に、選ばれた商品と選定理由を書き出す。

    GITHUB_STEP_SUMMARY が設定されていない環境（自分のパソコンでの実行など）では何もしない。
    """
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return

    with open(summary_path, "a", encoding="utf-8") as f:
        f.write(markdown)


if __name__ == "__main__":
    main()
