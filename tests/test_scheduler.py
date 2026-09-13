"""商品候補検索の自動実行スケジュール（src/scheduler.py）の回帰テスト。

「日本時間19:30〜21:00の範囲から1分単位でランダムな時刻を選ぶ」処理と、
「同じ日に2回自動実行しない」ための発火判定ロジックを確認する。
実際のファイル入出力やGitHub Actionsには依存せず、日時計算の部分だけを
テストする（`entries`・`now_utc`を直接渡せるようにしてあるため）。

実行方法:
    python -m unittest tests.test_scheduler -v
"""

from __future__ import annotations

import random
import unittest
from datetime import date, datetime, timedelta, timezone

from src import scheduler as sch

JST = timezone(timedelta(hours=9))
UTC = timezone.utc


def _utc(text: str) -> datetime:
    return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)


class PickRandomTimeTest(unittest.TestCase):
    """19:30〜21:00の範囲・1分単位、という条件そのものを確認する。"""

    def test_result_is_always_within_window(self):
        target = date(2026, 9, 14)
        for seed in range(500):
            rng = random.Random(seed)
            result = sch.pick_random_time_jst(target, rng)
            self.assertEqual(result.date(), target)
            self.assertGreaterEqual(
                (result.hour, result.minute), (sch.WINDOW_START_HOUR, sch.WINDOW_START_MINUTE)
            )
            self.assertLessEqual(
                (result.hour, result.minute), (sch.WINDOW_END_HOUR, sch.WINDOW_END_MINUTE)
            )

    def test_result_is_minute_granularity(self):
        target = date(2026, 9, 14)
        for seed in range(200):
            rng = random.Random(seed)
            result = sch.pick_random_time_jst(target, rng)
            self.assertEqual(result.second, 0)
            self.assertEqual(result.microsecond, 0)

    def test_lower_boundary_is_reachable(self):
        # rng.randint(0, 90) が 0 を返したとき、19:30ちょうどになることを確認する。
        rng = random.Random()
        rng.randint = lambda a, b: 0  # type: ignore[method-assign]
        result = sch.pick_random_time_jst(date(2026, 9, 14), rng)
        self.assertEqual((result.hour, result.minute), (19, 30))

    def test_upper_boundary_is_reachable_and_not_exceeded(self):
        # rng.randint(0, 90) が 90 を返したとき、21:00ちょうどになる
        # （21:00を超えることはない）ことを確認する。
        rng = random.Random()
        rng.randint = lambda a, b: 90  # type: ignore[method-assign]
        result = sch.pick_random_time_jst(date(2026, 9, 14), rng)
        self.assertEqual((result.hour, result.minute), (21, 0))

    def test_window_covers_exactly_91_distinct_minutes(self):
        target = date(2026, 9, 14)
        seen = set()
        for offset in range(sch.WINDOW_MINUTES):
            rng = random.Random()
            rng.randint = lambda a, b, offset=offset: offset  # type: ignore[method-assign]
            result = sch.pick_random_time_jst(target, rng)
            seen.add((result.hour, result.minute))
        self.assertEqual(len(seen), 91)
        self.assertIn((19, 30), seen)
        self.assertIn((21, 0), seen)


class DecideNextRunTest(unittest.TestCase):
    """翌日分の実行予定を決める処理（decide_next_run）を確認する。"""

    def test_targets_tomorrow_in_jst(self):
        # 2026-09-13 10:30 UTC = 2026-09-13 19:30 JST。翌日は2026-09-14。
        now_utc = _utc("2026-09-13T10:30:00Z")
        entries, new_entry = sch.decide_next_run(now_utc, entries=[], rng=random.Random(1))
        self.assertIsNotNone(new_entry)
        assert new_entry is not None
        self.assertEqual(new_entry["date"], "2026-09-14")
        self.assertEqual(len(entries), 1)

    def test_date_rollover_near_midnight_utc(self):
        # 2026-09-13 23:50 UTC = 2026-09-14 08:50 JST。翌日(JST)は2026-09-15。
        now_utc = _utc("2026-09-13T23:50:00Z")
        _entries, new_entry = sch.decide_next_run(now_utc, entries=[], rng=random.Random(1))
        assert new_entry is not None
        self.assertEqual(new_entry["date"], "2026-09-15")

    def test_is_idempotent_when_tomorrow_already_decided(self):
        # 同じ日に何度decideを実行しても、翌日分が重複して追加されない
        # （ワークフローが何らかの理由で複数回動いても壊れないようにするため）。
        now_utc = _utc("2026-09-13T10:30:00Z")
        entries, first = sch.decide_next_run(now_utc, entries=[], rng=random.Random(1))
        entries, second = sch.decide_next_run(now_utc, entries=entries, rng=random.Random(2))
        self.assertIsNotNone(first)
        self.assertIsNone(second)
        self.assertEqual(len(entries), 1)

    def test_new_entry_is_not_marked_fired(self):
        now_utc = _utc("2026-09-13T10:30:00Z")
        _entries, new_entry = sch.decide_next_run(now_utc, entries=[], rng=random.Random(1))
        assert new_entry is not None
        self.assertFalse(new_entry["fired"])

    def test_does_not_disturb_todays_still_pending_entry(self):
        # 「今日(2026-09-13)自身の予定」がまだ発火していない状態
        # （例：19:30時点ではまだ来ていない20:52予定）で翌日分を決めても、
        # 今日の未発火エントリが消えたり上書きされたりしないことを確認する
        # （19:30の「翌日分決定」と「今日の発火判定」が同じ時刻に重なる
        # レースを避けるための設計）。
        todays_pending = {
            "date": "2026-09-13",
            "time_jst": "20:52",
            "datetime_utc": "2026-09-13T11:52:00Z",
            "fired": False,
            "decided_at_utc": "2026-09-12T10:30:00Z",
        }
        now_utc = _utc("2026-09-13T10:30:00Z")  # ちょうど19:30 JST
        entries, new_entry = sch.decide_next_run(now_utc, entries=[todays_pending], rng=random.Random(1))
        assert new_entry is not None
        self.assertEqual(new_entry["date"], "2026-09-14")
        dates = sorted(e["date"] for e in entries)
        self.assertEqual(dates, ["2026-09-13", "2026-09-14"])
        still_there = next(e for e in entries if e["date"] == "2026-09-13")
        self.assertFalse(still_there["fired"])
        self.assertEqual(still_there["time_jst"], "20:52")

    def test_prunes_entries_older_than_keep_days(self):
        old_entry = {
            "date": "2026-08-01",
            "time_jst": "20:00",
            "datetime_utc": "2026-08-01T11:00:00Z",
            "fired": True,
            "decided_at_utc": "2026-07-31T10:30:00Z",
        }
        now_utc = _utc("2026-09-13T10:30:00Z")
        entries, _new_entry = sch.decide_next_run(now_utc, entries=[old_entry], rng=random.Random(1))
        self.assertNotIn(old_entry, entries)


class FindDueEntryTest(unittest.TestCase):
    """「今まさに実行すべきか」の判定（find_due_entry）を確認する。"""

    def _entry(self, **overrides):
        base = {
            "date": "2026-09-14",
            "time_jst": "20:17",
            "datetime_utc": "2026-09-14T11:17:00Z",
            "fired": False,
        }
        base.update(overrides)
        return base

    def test_not_due_before_target_time(self):
        entries = [self._entry()]
        now_utc = _utc("2026-09-14T11:16:00Z")
        self.assertIsNone(sch.find_due_entry(now_utc, entries))

    def test_due_exactly_at_target_time(self):
        entries = [self._entry()]
        now_utc = _utc("2026-09-14T11:17:00Z")
        result = sch.find_due_entry(now_utc, entries)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result["date"], "2026-09-14")

    def test_still_due_if_checker_run_was_delayed(self):
        # GitHub Actionsのスケジュール実行が遅延した場合でも、
        # 発火済みでなければ「まだ実行すべき」と判定できることを確認する
        # （取りこぼしを防ぐため）。
        entries = [self._entry()]
        now_utc = _utc("2026-09-14T11:30:00Z")
        self.assertIsNotNone(sch.find_due_entry(now_utc, entries))

    def test_not_due_once_fired(self):
        entries = [self._entry(fired=True, fired_at_utc="2026-09-14T11:17:05Z")]
        now_utc = _utc("2026-09-14T12:00:00Z")
        self.assertIsNone(sch.find_due_entry(now_utc, entries))

    def test_not_due_for_a_different_date(self):
        # 翌日分がすでに決まっていても、日付が一致しなければ発火しない
        # （decide_next_runとの日付ズレによる誤発火を防ぐ）。
        entries = [self._entry(date="2026-09-15", datetime_utc="2026-09-15T10:30:00Z")]
        now_utc = _utc("2026-09-14T23:59:00Z")
        self.assertIsNone(sch.find_due_entry(now_utc, entries))

    def test_only_todays_entry_is_considered_among_multiple(self):
        entries = [
            self._entry(date="2026-09-13", time_jst="19:45", datetime_utc="2026-09-13T10:45:00Z", fired=True),
            self._entry(date="2026-09-14", time_jst="20:17", datetime_utc="2026-09-14T11:17:00Z"),
            self._entry(date="2026-09-15", time_jst="19:40", datetime_utc="2026-09-15T10:40:00Z"),
        ]
        now_utc = _utc("2026-09-14T11:20:00Z")
        result = sch.find_due_entry(now_utc, entries)
        assert result is not None
        self.assertEqual(result["date"], "2026-09-14")


class MarkFiredTest(unittest.TestCase):
    """発火済みへの記録（mark_fired）と、それによる二重発火防止を確認する。"""

    def test_marks_matching_unfired_entry(self):
        entries = [
            {
                "date": "2026-09-14",
                "time_jst": "20:17",
                "datetime_utc": "2026-09-14T11:17:00Z",
                "fired": False,
            }
        ]
        now_utc = _utc("2026-09-14T11:17:03Z")
        updated, marked = sch.mark_fired(entries, "2026-09-14", now_utc)
        self.assertTrue(marked)
        self.assertTrue(updated[0]["fired"])
        self.assertEqual(updated[0]["fired_at_utc"], "2026-09-14T11:17:03Z")

    def test_returns_false_when_already_fired(self):
        entries = [
            {
                "date": "2026-09-14",
                "time_jst": "20:17",
                "datetime_utc": "2026-09-14T11:17:00Z",
                "fired": True,
                "fired_at_utc": "2026-09-14T11:17:05Z",
            }
        ]
        now_utc = _utc("2026-09-14T11:20:00Z")
        _updated, marked = sch.mark_fired(entries, "2026-09-14", now_utc)
        self.assertFalse(marked)

    def test_returns_false_when_date_not_found(self):
        now_utc = _utc("2026-09-14T11:20:00Z")
        _updated, marked = sch.mark_fired([], "2026-09-14", now_utc)
        self.assertFalse(marked)

    def test_full_cycle_prevents_double_run_on_same_day(self):
        # decide → find_due_entry(due) → mark_fired → find_due_entry(もう due にならない)
        # という一連の流れで、同じ日に2回実行判定されないことを確認する。
        entries, new_entry = sch.decide_next_run(
            _utc("2026-09-13T10:30:00Z"), entries=[], rng=random.Random(1)
        )
        assert new_entry is not None
        target_utc = _utc(new_entry["datetime_utc"])

        # 予定時刻ちょうどでは「実行すべき」と判定される。
        due = sch.find_due_entry(target_utc, entries)
        self.assertIsNotNone(due)

        # 発火済みにする。
        entries, marked = sch.mark_fired(entries, new_entry["date"], target_utc)
        self.assertTrue(marked)

        # 同じ日のうちに何度確認しても、もう「実行すべき」にはならない。
        later_same_day = target_utc + timedelta(minutes=5)
        self.assertIsNone(sch.find_due_entry(later_same_day, entries))
        end_of_window = target_utc.replace(hour=12, minute=0, second=0)
        self.assertIsNone(sch.find_due_entry(end_of_window, entries))


class PruneOldEntriesTest(unittest.TestCase):
    def test_keeps_recent_and_drops_old(self):
        today = date(2026, 9, 14)
        entries = [
            {"date": "2026-08-01", "time_jst": "20:00"},
            {"date": "2026-09-13", "time_jst": "20:00"},
            {"date": "2026-09-14", "time_jst": "20:00"},
        ]
        result = sch.prune_old_entries(entries, today, keep_days=14)
        dates = {e["date"] for e in result}
        self.assertNotIn("2026-08-01", dates)
        self.assertIn("2026-09-13", dates)
        self.assertIn("2026-09-14", dates)


if __name__ == "__main__":
    unittest.main()
