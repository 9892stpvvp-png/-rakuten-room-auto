"""投稿候補一覧をファイルに保存する部分。"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from . import atomic_io


def save_candidates(candidates: list[dict[str, Any]], output_dir: Path) -> tuple[Path, Path]:
    """投稿候補一覧をJSONとMarkdownの2種類で保存し、それぞれの保存先パスを返す。

    JSON: プログラムで再利用しやすいデータ形式
    Markdown: 人間がGitHub上やエディタでそのまま読める一覧（全件）

    書き込みはatomic_io経由で行い、GitHub Actionsのジョブタイムアウト・
    手動キャンセル等で書き込み途中にプロセスが終了しても、書きかけの
    壊れたファイルが残らないようにする（publish_room_page.pyが
    find_latest_candidates_json()でこのJSONを最新候補として読み込むため）。
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"candidates_{timestamp}.json"
    markdown_path = output_dir / f"candidates_{timestamp}.md"

    atomic_io.write_json_atomic(json_path, candidates)
    atomic_io.write_text_atomic(
        markdown_path,
        render_candidates_markdown(
            candidates, title=f"投稿候補一覧（{timestamp}）", include_extra=True
        ),
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


def build_supply_diagnostics_markdown(
    category_diagnostics: list[dict[str, Any]],
    convenience_count: int,
    consumable_count: int,
    convenience_target: int,
    consumable_target: int,
) -> str:
    """GitHub ActionsのSummaryに表示する、候補生成の内訳（目標件数に届かなかった
    場合の原因確認用）。

    「暮らしの便利グッズ」「消耗品・飲料」それぞれの実際の件数／目標件数と、
    カテゴリー（keywordsの各エントリ）ごとに、条件フィルタ・投稿済み除外を
    通過した件数、実際に試した検索ワード（extra_keywordsで追加探索した
    場合はその一覧も）を一覧にする。目標件数に届いている日も参考として
    常に表示する。
    """
    lines = [
        "## 候補生成の内訳（不足時の原因確認用）",
        "",
        f"- 暮らしの便利グッズ: {convenience_count}/{convenience_target}件",
        f"- 消耗品・飲料: {consumable_count}/{consumable_target}件",
        "",
        "| カテゴリー | 枠 | 条件通過（投稿済み除外後） | 試した検索ワード |",
        "|---|---|---|---|",
    ]
    for diag in category_diagnostics:
        group_label = "便利グッズ" if diag["group"] == "convenience" else "消耗品・飲料"
        keywords_display = " → ".join(diag["keywords_tried"])
        lines.append(f"| {diag['category']} | {group_label} | {diag['found']}件 | {keywords_display} |")
    lines.append("")
    return "\n".join(lines) + "\n"


def build_genre_selection_summary_markdown(
    category_diagnostics: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    total_after_filters: int,
    target: int,
    quality_filtered_out: int,
    posted_excluded_total: int,
) -> str:
    """GitHub ActionsのSummaryに表示する、全ジャンル化後の候補選定の内訳。

    「暮らしの便利グッズ5件＋消耗品・飲料5件」という固定構成は前提にせず、
    全ジャンルを1つのプールとして扱った選定結果を報告する。

    ・候補数（品質条件・重複除外を通過した件数）／最終採用数
    ・品質条件で除外した件数／投稿済み履歴による重複除外件数
    ・候補不足の有無
    ・ジャンル（カテゴリー）別・商品タイプ別の採用件数
    ・需要・人気の判断に使ったデータ（楽天公式ランキングAPIを実際に
      利用できたかどうかを、事実に基づいて表示する。未確認情報を
      ランキングデータとして扱わないため）
    ・カテゴリーごとに試した検索ワード（keywordsの各エントリ単位。
      新規候補の採否に関わらず、探索した内容が分かるよう全件表示する）
    """
    shortage = len(candidates) < target
    genre_counts: dict[str, int] = defaultdict(int)
    type_counts: dict[str, int] = defaultdict(int)
    for item in candidates:
        genre = item.get("_category", "") or "(不明)"
        genre_counts[genre] += 1
        product_type = item.get("_product_type", "") or "(不明)"
        type_counts[product_type] += 1

    lines = [
        "## 全ジャンル候補選定の内訳",
        "",
        f"- 品質条件・重複除外を通過した候補数: {total_after_filters}件",
        f"- 最終採用数: {len(candidates)}/{target}件"
        + ("（候補不足のため目標に届きませんでした）" if shortage else "（目標を達成）"),
        f"- 品質条件（レビュー評価・件数等）で除外した件数: {quality_filtered_out}件",
        f"- 投稿済み履歴による重複除外: {posted_excluded_total}件",
        "",
        "### ジャンル別の採用件数",
        "",
        "| ジャンル | 件数 |",
        "|---|---|",
    ]
    for genre, count in sorted(genre_counts.items(), key=lambda kv: -kv[1]):
        lines.append(f"| {genre} | {count}件 |")

    lines.extend(
        [
            "",
            "### 商品タイプ別の採用件数",
            "",
            "| 商品タイプ | 件数 |",
            "|---|---|",
        ]
    )
    for product_type, count in sorted(type_counts.items(), key=lambda kv: -kv[1]):
        lines.append(f"| {product_type} | {count}件 |")

    lines.extend(
        [
            "",
            "### 需要・人気の判断に使ったデータ",
            "",
            "- 使用データ: 楽天ウェブサービス商品検索API（IchibaItem/Search）の"
            "レビュー件数・レビュー評価、および検索結果内でのレビュー件数順"
            "（sort=-reviewCount。検索結果内での人気度の目安）",
            "- 楽天公式ランキングAPI（IchibaItem/Ranking等）の利用: "
            "**していません**（実装上、商品検索APIのみを呼び出しています。"
            "取得できないデータを売れ筋・ランキングとして扱っていません）",
            "",
            "### カテゴリーごとに試した検索ワード",
            "",
            "| カテゴリー | 枠 | 条件通過（投稿済み除外後） | 試した検索ワード |",
            "|---|---|---|---|",
        ]
    )
    for diag in category_diagnostics:
        group_label = "便利グッズ" if diag["group"] == "convenience" else "消耗品・飲料"
        keywords_display = " → ".join(diag["keywords_tried"])
        lines.append(f"| {diag['category']} | {group_label} | {diag['found']}件 | {keywords_display} |")
    lines.append("")
    return "\n".join(lines) + "\n"


def build_product_type_diversity_markdown(
    selected_types: list[str],
    deprioritized_types: list[str],
    restored_types: list[str],
) -> str:
    """GitHub ActionsのSummaryに表示する、商品タイプの偏り防止の状況。

    ・今回選ばれた商品タイプ
    ・直近の投稿で多いため優先度を下げた商品タイプ（完全除外ではない）
    ・候補不足のため、優先度を下げつつも結局復帰して選ばれた商品タイプ
    を一覧にする。簡潔さを優先し、件数などの詳細は載せない。
    """

    def _bullet_block(title: str, values: list[str]) -> list[str]:
        block = [f"**{title}**："]
        if values:
            block.extend(f"・{value}" for value in values)
        else:
            block.append("（なし）")
        block.append("")
        return block

    lines = ["## 商品タイプの偏り防止", ""]
    lines.extend(_bullet_block("今回選ばれた商品タイプ", selected_types))
    lines.extend(_bullet_block("最近多いため優先度を下げた商品タイプ", deprioritized_types))
    lines.extend(_bullet_block("不足のため復帰させた商品タイプ", restored_types))
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
