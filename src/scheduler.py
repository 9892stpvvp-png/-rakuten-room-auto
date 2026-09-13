"""商品候補検索を「毎日、日本時間19:30〜21:00のランダムな1分」に自動実行する
ための、スケジュール決定・発火判定のロジック。

## 仕組み

1. 毎日 日本時間19:30（`.github/workflows/schedule_next_run.yml`）に、
   「翌日」の19:30〜21:00の範囲から1分単位でランダムな時刻を1つ選び、
   `data/schedule/schedule_log.json` に追記する（`decide` コマンド）。
2. 日本時間19:30〜21:00の間、1分おきに
   `.github/workflows/run_scheduled_search.yml` が実行され、
   「今日の予定時刻に達しているか」を確認する（`check` コマンド）。
   達していれば、そのワークフローが `search_candidates.yml`
   （既存の商品候補検索ワークフロー）を起動し、実行済みとして記録する
   （`mark-fired` コマンド）。これにより、同じ日に2回自動実行されることはない。

商品候補検索そのもの（`src/main.py` 以下）やGitHub ActionsのSecretsは
このモジュールから一切変更しない。あくまで「いつ起動するか」だけを
決める部分。

## なぜ「90分sleepして待つ」方式を使わないか

1つのジョブが90分間sleepし続ける方式は、その間ずっとRunnerを専有してしまい、
途中で失敗した場合にもリカバリーしにくい。代わりに、GitHub Actionsの
`schedule`（cron）トリガーを1分刻みで設定し、日本時間19:30〜21:00の間、
短時間で終わる「確認だけ」のジョブを繰り返し実行する方式にしている
（各ジョブは数秒で終わり、対象時刻でなければ何もせず終了する）。

## 状態の持ち方（`data/schedule/schedule_log.json`）

日付ごとのエントリの配列。「翌日分を決める処理」と「今日の予定を確認する処理」
が同じ19:30台に重なっても壊れないよう、両者を1つの値で共有せず、日付をキーに
した別々のエントリとして持たせている（例：ある日の19:30に翌日分を新規追加
する時点で、その日自身の予定がまだ未発火（例：20:52予定）ということがあり
うるため）。
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

JST = timezone(timedelta(hours=9))
UTC = timezone.utc

# 実行時刻の範囲：日本時間19:30〜21:00（両端を含む、91通りの1分刻み）。
WINDOW_START_HOUR, WINDOW_START_MINUTE = 19, 30
WINDOW_END_HOUR, WINDOW_END_MINUTE = 21, 0
WINDOW_MINUTES = 91

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCHEDULE_LOG_PATH = PROJECT_ROOT / "data" / "schedule" / "schedule_log.json"

# 古いエントリを消さずに残しておく日数（無限に増え続けないようにするため）。
KEEP_DAYS = 14


def pick_random_time_jst(target_date: date, rng: random.Random | None = None) -> datetime:
    """target_date（日本時間の日付）の19:30〜21:00の範囲から、1分単位で
    ランダムな時刻（タイムゾーン付きdatetime、日本時間）を1つ選ぶ。"""
    rng = rng if rng is not None else random.Random()
    offset_minutes = rng.randint(0, WINDOW_MINUTES - 1)
    start = datetime(
        target_date.year, target_date.month, target_date.day,
        WINDOW_START_HOUR, WINDOW_START_MINUTE, tzinfo=JST,
    )
    return start + timedelta(minutes=offset_minutes)


def load_schedule_log(path: Path | None = None) -> list[dict[str, Any]]:
    # デフォルト引数にSCHEDULE_LOG_PATHを直接指定すると、関数定義時の値に
    # 固定されてしまい、テストでモジュール変数を差し替えても反映されない
    # （Pythonのデフォルト引数は定義時に評価されるため）。呼び出し時に
    # 毎回モジュール変数を読みに行くよう、Noneを既定値にしている。
    path = path if path is not None else SCHEDULE_LOG_PATH
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        content = f.read().strip()
    return json.loads(content) if content else []


def save_schedule_log(entries: list[dict[str, Any]], path: Path | None = None) -> None:
    path = path if path is not None else SCHEDULE_LOG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)
        f.write("\n")


def prune_old_entries(
    entries: list[dict[str, Any]], today: date, keep_days: int = KEEP_DAYS
) -> list[dict[str, Any]]:
    """keep_days日より古いエントリを取り除く（ファイルが無限に増えないようにする）。"""
    cutoff = today - timedelta(days=keep_days)
    return [e for e in entries if date.fromisoformat(e["date"]) >= cutoff]


def decide_next_run(
    now_utc: datetime,
    entries: list[dict[str, Any]] | None = None,
    rng: random.Random | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    """「翌日」（日本時間基準）の実行予定を決めて追加する。

    すでに翌日分の予定が存在する場合は何もしない（同じ日に`decide`が複数回
    実行されても、翌日分が重複して追加されたり上書きされたりしない）。

    戻り値: (更新後のentries, 新しく追加したentry。すでに決定済みならNone)
    """
    now_jst = now_utc.astimezone(JST)
    tomorrow = (now_jst + timedelta(days=1)).date()
    entries = list(entries) if entries is not None else load_schedule_log()

    if any(e["date"] == tomorrow.isoformat() for e in entries):
        return entries, None

    target_jst = pick_random_time_jst(tomorrow, rng)
    target_utc = target_jst.astimezone(UTC)
    new_entry: dict[str, Any] = {
        "date": tomorrow.isoformat(),
        "time_jst": target_jst.strftime("%H:%M"),
        "datetime_utc": target_utc.strftime("%Y-%m-%dT%H:%M:00Z"),
        "fired": False,
        "decided_at_utc": now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    entries = entries + [new_entry]
    entries = prune_old_entries(entries, tomorrow)
    return entries, new_entry


def find_due_entry(now_utc: datetime, entries: list[dict[str, Any]]) -> dict[str, Any] | None:
    """「今まさに実行すべきエントリ」（日本時間の今日の日付・未発火・予定時刻を
    過ぎている）があれば返す。無ければNone。

    日付が一致するエントリだけを見るため、19:30台に「翌日分」が新しく
    決まっていても、今日の分とは別のエントリとして扱われ、混同しない。
    """
    today_str = now_utc.astimezone(JST).date().isoformat()
    for entry in entries:
        if entry["date"] != today_str or entry.get("fired"):
            continue
        target_utc = datetime.strptime(entry["datetime_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
        if now_utc >= target_utc:
            return entry
    return None


def mark_fired(
    entries: list[dict[str, Any]], date_str: str, now_utc: datetime
) -> tuple[list[dict[str, Any]], bool]:
    """date_strの未発火エントリを「発火済み」にする。

    戻り値: (更新後のentries, 実際にマークできたか)
    対象が見つからない（すでに発火済み、またはそもそも存在しない）場合はFalse。
    """
    updated: list[dict[str, Any]] = []
    marked = False
    for entry in entries:
        if entry["date"] == date_str and not entry.get("fired") and not marked:
            entry = dict(entry)
            entry["fired"] = True
            entry["fired_at_utc"] = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
            marked = True
        updated.append(entry)
    return updated, marked


def _write_github_output(pairs: dict[str, str]) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as f:
        for key, value in pairs.items():
            f.write(f"{key}={value}\n")


def _write_github_step_summary(text: str) -> None:
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as f:
        f.write(text)


def cli_decide() -> None:
    now_utc = datetime.now(UTC)
    entries, new_entry = decide_next_run(now_utc)
    if new_entry is None:
        print("翌日分の実行時刻はすでに決定済みのため、何もしません。")
        _write_github_output({"changed": "false"})
        return

    save_schedule_log(entries)
    print(f"翌日の実行時刻を決定しました: {new_entry['date']} {new_entry['time_jst']} JST")
    _write_github_output(
        {
            "changed": "true",
            "date": new_entry["date"],
            "time_jst": new_entry["time_jst"],
        }
    )
    _write_github_step_summary(
        "## 商品候補検索の自動実行スケジュール\n\n"
        f"次回自動実行予定：{new_entry['date']} {new_entry['time_jst']} JST\n"
    )


def cli_check() -> None:
    now_utc = datetime.now(UTC)
    entries = load_schedule_log()
    entry = find_due_entry(now_utc, entries)
    if entry is None:
        print("本日の実行予定時刻にはまだ達していません（または本日の予定がありません）。")
        _write_github_output({"due": "false"})
        return

    print(f"本日の実行予定時刻になりました: {entry['date']} {entry['time_jst']} JST")
    _write_github_output({"due": "true", "date": entry["date"], "time_jst": entry["time_jst"]})


def cli_mark_fired(date_str: str) -> None:
    now_utc = datetime.now(UTC)
    entries = load_schedule_log()
    entries, marked = mark_fired(entries, date_str, now_utc)
    if not marked:
        raise SystemExit(f"{date_str} の未発火の実行予定が見つかりませんでした。")
    save_schedule_log(entries)
    print(f"{date_str} の自動実行を記録しました。")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="商品候補検索の自動実行スケジュールを管理する")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("decide", help="翌日の実行時刻を決める")
    subparsers.add_parser("check", help="本日の実行予定時刻に達しているか確認する")
    mark_parser = subparsers.add_parser("mark-fired", help="指定した日付の自動実行を記録する")
    mark_parser.add_argument("--date", required=True, help="YYYY-MM-DD形式の日付")

    args = parser.parse_args(argv)

    if args.command == "decide":
        cli_decide()
    elif args.command == "check":
        cli_check()
    elif args.command == "mark-fired":
        cli_mark_fired(args.date)


if __name__ == "__main__":
    main(sys.argv[1:])
