"""候補選定パイプライン全体（src/main.py）の統合テスト。

楽天ウェブサービスへの実際のアクセスは行わず、src.rakuten_api.search_items を
差し替えて疑似的な検索結果を返す。実際のconfig/settings.example.yamlをそのまま
使うことで、本番と同じキーワード・カテゴリ・group（便利グッズ／消耗品・飲料）
構成で「暮らしの便利グッズ5件＋消耗品・飲料5件」の選定ロジックを検証する。

飲料の複数本セット優先など、より細かい選定ロジックそのものは
tests/test_ranking.py で個別にテストしている。ここでは、main.pyの
パイプライン全体（検索→フィルタ→重複除去→紹介文生成→5+5選定→保存）が
壊れていないことを確認する。

実行方法:
    python -m unittest tests.test_main -v
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src import main as main_module
from src import rakuten_api


def _make_item(item_code: str, name: str, review_average: float = 4.6, review_count: int = 500) -> dict:
    return {
        "item_code": item_code,
        "name": name,
        "catch_copy": "",
        "item_caption": "",
        "price": 1980,
        "review_average": review_average,
        "review_count": review_count,
        "item_url": f"https://item.rakuten.co.jp/shop/{item_code}/",
        "image_url": "https://example.com/example.jpg",
        "shop_name": "テストショップ",
    }


def _slug(keyword: str) -> str:
    return keyword.replace(" ", "_").replace("%", "pct")


def _default_fake_search(keyword: str, **_kwargs) -> list[dict]:
    """キーワードごとに、条件（レビュー4.0以上・100件以上）を満たす商品を3件返す疑似検索。"""
    slug = _slug(keyword)
    return [_make_item(f"shop:{slug}_{i}", f"{keyword} 商品{i}") for i in range(3)]


def _all_keywords_for_categories(categories: list[str]) -> list[str]:
    """settings.example.yamlの実際のkeywordsから、指定したカテゴリーに属する
    エントリの検索ワード（keyword本体＋extra_keywords）を全て集める。

    「あるカテゴリーが（追加探索も含めて）完全に候補切れ」というシナリオを
    テストする際、settings.example.yaml側でextra_keywordsの中身が変わっても
    テストが追従できるよう、キーワード文字列をハードコードせずここで
    動的に取得する。
    """
    settings = main_module.load_settings()
    keywords: list[str] = []
    for entry in settings["keywords"]:
        keyword, category, _group, extra_keywords = main_module._parse_keyword_entry(entry)
        if category in categories:
            keywords.append(keyword)
            keywords.extend(extra_keywords)
    return keywords


class RunPipelineTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        tmp_path = Path(self.tmpdir.name)
        self.candidates_dir = tmp_path / "candidates"
        self.posted_items_path = tmp_path / "posted_items.json"

        candidates_patcher = mock.patch.object(main_module, "CANDIDATES_DIR", self.candidates_dir)
        posted_patcher = mock.patch.object(main_module, "POSTED_ITEMS_PATH", self.posted_items_path)
        candidates_patcher.start()
        posted_patcher.start()
        self.addCleanup(candidates_patcher.stop)
        self.addCleanup(posted_patcher.stop)

        os.environ["RAKUTEN_APP_ID"] = "dummy-app-id-for-tests"
        os.environ["RAKUTEN_ACCESS_KEY"] = "dummy-access-key-for-tests"
        os.environ.pop("GITHUB_STEP_SUMMARY", None)
        self.addCleanup(lambda: os.environ.pop("RAKUTEN_APP_ID", None))
        self.addCleanup(lambda: os.environ.pop("RAKUTEN_ACCESS_KEY", None))

    def _run_main(self, fake_search=_default_fake_search) -> list[dict]:
        with mock.patch.object(rakuten_api, "search_items", side_effect=fake_search):
            main_module.main()
        latest = sorted(self.candidates_dir.glob("candidates_*.json"))[-1]
        with latest.open(encoding="utf-8") as f:
            return json.load(f)

    def test_normal_run_splits_five_convenience_and_five_consumable(self):
        candidates = self._run_main()

        self.assertLessEqual(len(candidates), 10)
        convenience = [c for c in candidates if c["_group"] == "convenience"]
        consumable = [c for c in candidates if c["_group"] == "consumable"]
        self.assertEqual(len(convenience), 5)
        self.assertEqual(len(consumable), 5)
        self.assertEqual(len(convenience) + len(consumable), len(candidates))

    def test_each_item_has_a_display_group_for_the_room_page(self):
        candidates = self._run_main()
        for item in candidates:
            self.assertIn(item["_display_group"], ("便利グッズ", "消耗品", "飲料"))
            if item["_group"] == "convenience":
                self.assertEqual(item["_display_group"], "便利グッズ")
            else:
                self.assertIn(item["_display_group"], ("消耗品", "飲料"))

    def test_no_duplicate_item_codes(self):
        candidates = self._run_main()
        codes = [c["item_code"] for c in candidates]
        self.assertEqual(len(codes), len(set(codes)))

    def test_alcohol_items_are_excluded_even_if_highest_rated(self):
        def fake_search_with_alcohol(keyword: str, **kwargs):
            items = _default_fake_search(keyword, **kwargs)
            if keyword == "ミネラルウォーター":
                # レビュー件数を突出させ、除外されなければ確実に上位選出される条件にする。
                items.append(_make_item("shop:beer_case", "国産ビール 24本 ケース", review_count=9000))
            return items

        candidates = self._run_main(fake_search_with_alcohol)
        names = [c["name"] for c in candidates]
        codes = [c["item_code"] for c in candidates]
        self.assertNotIn("shop:beer_case", codes)
        self.assertFalse(any("ビール" in name for name in names))

    def test_posted_items_are_not_reselected(self):
        first_run = self._run_main()
        already_posted_code = first_run[0]["item_code"]

        self.posted_items_path.parent.mkdir(parents=True, exist_ok=True)
        with self.posted_items_path.open("w", encoding="utf-8") as f:
            json.dump({"posted_item_codes": [already_posted_code]}, f)

        second_run = self._run_main()
        codes = [c["item_code"] for c in second_run]
        self.assertNotIn(already_posted_code, codes)

    def test_durable_accessory_items_are_excluded_from_consumable_group(self):
        # 実際の本番実行で、「トイレットペーパー」キーワードの検索結果に
        # トイレットペーパー本体ではなく「トイレットペーパーホルダー」
        # （消耗品ではなく耐久品）が混ざる問題が見つかったため、その再発防止テスト。
        def fake_search_with_holder(keyword: str, **kwargs):
            items = _default_fake_search(keyword, **kwargs)
            if keyword == "トイレットペーパー":
                items.append(
                    _make_item("shop:tp_holder", "トイレットペーパーホルダー おしゃれ 2連", review_count=9000)
                )
            return items

        candidates = self._run_main(fake_search_with_holder)
        codes = [c["item_code"] for c in candidates]
        names = [c["name"] for c in candidates]
        self.assertNotIn("shop:tp_holder", codes)
        self.assertFalse(any("ホルダー" in name for name in names))

    def test_posted_items_excluded_by_url_even_with_different_item_code(self):
        # 楽天側の仕様変更等でitem_codeの取れ方が変わっても、商品URLが一致すれば
        # 投稿済みとみなして除外できることを確認する（重複判定の優先順位2番目）。
        shared_url = "https://item.rakuten.co.jp/shop/shared-product/"

        def fake_search_specific(keyword: str, **kwargs):
            if keyword == "掃除 便利グッズ":
                item = _make_item("shop:new_code_for_shared_product", "掃除便利グッズX")
                item["item_url"] = shared_url
                return [item]
            return _default_fake_search(keyword, **kwargs)

        self.posted_items_path.parent.mkdir(parents=True, exist_ok=True)
        with self.posted_items_path.open("w", encoding="utf-8") as f:
            json.dump(
                {
                    "posted_items": [
                        {
                            "item_code": "shop:old_code_different_from_candidate",
                            "item_url": shared_url + "?scid=tracking123",
                        }
                    ]
                },
                f,
            )

        candidates = self._run_main(fake_search_specific)
        codes = [c["item_code"] for c in candidates]
        self.assertNotIn("shop:new_code_for_shared_product", codes)

    def test_posted_history_exclusion_triggers_fallback_to_reach_ten(self):
        # 4つの便利グッズカテゴリー（収納・キッチン・時短・暮らし全般）について、
        # 本来の検索ワードだけでなくextra_keywords（追加探索用）で見つかる
        # 商品もすべて投稿済み履歴に登録し、便利グッズ枠を大きく不足させる
        # （_default_fake_searchは同じキーワードから似た名前の商品を3件返すため、
        # フェーズ2の類似商品統合で1件に絞られる。つまり残る1カテゴリー分も
        # 最終的には1件になる）。消耗品・飲料枠から補充されて合計10件になる
        # ことを確認する。
        excluded_keywords = _all_keywords_for_categories(["収納", "キッチン", "時短", "暮らし全般"])
        excluded_codes = []
        for kw in excluded_keywords:
            slug = _slug(kw)
            excluded_codes.extend(f"shop:{slug}_{i}" for i in range(3))

        self.posted_items_path.parent.mkdir(parents=True, exist_ok=True)
        with self.posted_items_path.open("w", encoding="utf-8") as f:
            json.dump({"posted_item_codes": excluded_codes}, f)

        candidates = self._run_main()
        convenience = [c for c in candidates if c["_group"] == "convenience"]
        consumable = [c for c in candidates if c["_group"] == "consumable"]

        for code in excluded_codes:
            self.assertNotIn(code, [c["item_code"] for c in candidates])
        self.assertEqual(len(convenience), 1)
        self.assertEqual(len(consumable), 9)
        self.assertEqual(len(candidates), 10)

    def test_github_step_summary_includes_posted_history_stats(self):
        summary_path = Path(self.tmpdir.name) / "step_summary.md"
        os.environ["GITHUB_STEP_SUMMARY"] = str(summary_path)
        self.addCleanup(lambda: os.environ.pop("GITHUB_STEP_SUMMARY", None))

        self.posted_items_path.parent.mkdir(parents=True, exist_ok=True)
        with self.posted_items_path.open("w", encoding="utf-8") as f:
            json.dump({"posted_item_codes": ["shop:some_old_code"]}, f)

        self._run_main()

        content = summary_path.read_text(encoding="utf-8")
        self.assertIn("投稿済み履歴による重複防止", content)
        self.assertIn("投稿済み履歴によって除外した件数", content)
        self.assertIn("item_codeによる除外件数", content)
        self.assertIn("URLによる除外件数", content)
        self.assertIn("商品名履歴による除外件数", content)
        self.assertIn("match_keywordsによる除外件数", content)
        self.assertIn("今回選ばれた新規候補", content)
        self.assertIn("現在の投稿済み履歴の総数: 1件", content)

    def test_match_keywords_history_excludes_matching_candidate(self):
        # item_code・item_url・完全一致するproduct_nameのいずれも分からない
        # 過去投稿（match_keywordsだけの履歴）でも、全キーワードを含む候補を
        # 除外できることを確認する。
        def fake_search_specific(keyword: str, **kwargs):
            if keyword == "掃除 便利グッズ":
                return [_make_item("shop:cleaning_v", "山崎実業 tower マグネットクリーナー ワイド")]
            return _default_fake_search(keyword, **kwargs)

        self.posted_items_path.parent.mkdir(parents=True, exist_ok=True)
        with self.posted_items_path.open("w", encoding="utf-8") as f:
            json.dump(
                {
                    "posted_items": [
                        {
                            "match_keywords": ["tower", "マグネットクリーナー", "ワイド"],
                            "item_code": None,
                            "item_url": None,
                            "product_name": None,
                        }
                    ]
                },
                f,
            )

        candidates = self._run_main(fake_search_specific)
        codes = [c["item_code"] for c in candidates]
        self.assertNotIn("shop:cleaning_v", codes)

    def test_match_keywords_partial_match_does_not_exclude_candidate(self):
        # 一部のキーワードしか含まない候補（別モデル・別サイズ等）は
        # 除外しないことを確認する。
        def fake_search_specific(keyword: str, **kwargs):
            if keyword == "掃除 便利グッズ":
                return [_make_item("shop:cleaning_u", "山崎実業 tower マグネットクリーナー ラージ")]
            return _default_fake_search(keyword, **kwargs)

        self.posted_items_path.parent.mkdir(parents=True, exist_ok=True)
        with self.posted_items_path.open("w", encoding="utf-8") as f:
            json.dump(
                {
                    "posted_items": [
                        {"match_keywords": ["tower", "マグネットクリーナー", "ワイド"]}
                    ]
                },
                f,
            )

        candidates = self._run_main(fake_search_specific)
        codes = [c["item_code"] for c in candidates]
        self.assertIn("shop:cleaning_u", codes)

    def test_single_word_match_keywords_never_excludes_candidates(self):
        # ["tower"]のような1語だけのmatch_keywordsは、無関係な商品まで
        # 除外してしまわないよう機能しない（誤判定防止）。
        def fake_search_specific(keyword: str, **kwargs):
            if keyword == "掃除 便利グッズ":
                return [_make_item("shop:cleaning_t", "tower マグネットフック")]
            return _default_fake_search(keyword, **kwargs)

        self.posted_items_path.parent.mkdir(parents=True, exist_ok=True)
        with self.posted_items_path.open("w", encoding="utf-8") as f:
            json.dump({"posted_items": [{"match_keywords": ["tower"]}]}, f)

        candidates = self._run_main(fake_search_specific)
        codes = [c["item_code"] for c in candidates]
        self.assertIn("shop:cleaning_t", codes)

    def test_product_name_only_history_excludes_matching_candidate(self):
        # item_code・item_urlが分からない過去投稿（商品名だけの履歴）でも、
        # 同じ商品名の候補を除外できることを確認する。
        def fake_search_specific(keyword: str, **kwargs):
            if keyword == "掃除 便利グッズ":
                return [_make_item("shop:cleaning_x", "激安クリーナー Aシリーズ")]
            return _default_fake_search(keyword, **kwargs)

        self.posted_items_path.parent.mkdir(parents=True, exist_ok=True)
        with self.posted_items_path.open("w", encoding="utf-8") as f:
            json.dump(
                {
                    "posted_items": [
                        {
                            "product_name": "激安クリーナー Aシリーズ",
                            "item_code": None,
                            "item_url": None,
                            "posted_at": None,
                            "category": "過去投稿",
                        }
                    ]
                },
                f,
            )

        candidates = self._run_main(fake_search_specific)
        codes = [c["item_code"] for c in candidates]
        self.assertNotIn("shop:cleaning_x", codes)

    def test_decorated_product_name_in_history_still_matches(self):
        # 販売文言・装飾記号・絵文字が付いた商品名でも、正規化後の完全一致で
        # 投稿済みと判定できることを確認する。
        def fake_search_specific(keyword: str, **kwargs):
            if keyword == "掃除 便利グッズ":
                return [
                    _make_item(
                        "shop:cleaning_y",
                        "【送料無料】激安クリーナー　Ｂシリーズ　公式　限定 🎉",
                    )
                ]
            return _default_fake_search(keyword, **kwargs)

        self.posted_items_path.parent.mkdir(parents=True, exist_ok=True)
        with self.posted_items_path.open("w", encoding="utf-8") as f:
            json.dump({"posted_items": [{"product_name": "激安クリーナー Bシリーズ"}]}, f)

        candidates = self._run_main(fake_search_specific)
        codes = [c["item_code"] for c in candidates]
        self.assertNotIn("shop:cleaning_y", codes)

    def test_size_variant_in_history_does_not_exclude_different_variant(self):
        # 「ワイド」と「ラージ」のように似ているだけの別商品は除外しない
        # （正規化後の完全一致だけで判定するため、部分一致では除外されない）。
        def fake_search_specific(keyword: str, **kwargs):
            if keyword == "掃除 便利グッズ":
                return [_make_item("shop:cleaning_z", "クリーナー Cシリーズ ラージ")]
            return _default_fake_search(keyword, **kwargs)

        self.posted_items_path.parent.mkdir(parents=True, exist_ok=True)
        with self.posted_items_path.open("w", encoding="utf-8") as f:
            json.dump({"posted_items": [{"product_name": "クリーナー Cシリーズ ワイド"}]}, f)

        candidates = self._run_main(fake_search_specific)
        codes = [c["item_code"] for c in candidates]
        self.assertIn("shop:cleaning_z", codes)

    def test_item_code_match_is_not_overridden_by_product_name_mismatch(self):
        # item_codeが一致していれば、履歴の商品名が違っていても（表記ゆれ等）
        # item_code判定が優先されて除外されることを確認する。
        def fake_search_specific(keyword: str, **kwargs):
            if keyword == "掃除 便利グッズ":
                return [_make_item("shop:cleaning_w", "新しい商品名のクリーナー")]
            return _default_fake_search(keyword, **kwargs)

        self.posted_items_path.parent.mkdir(parents=True, exist_ok=True)
        with self.posted_items_path.open("w", encoding="utf-8") as f:
            json.dump(
                {
                    "posted_items": [
                        {"item_code": "shop:cleaning_w", "product_name": "まったく違う古い商品名"}
                    ]
                },
                f,
            )

        candidates = self._run_main(fake_search_specific)
        codes = [c["item_code"] for c in candidates]
        self.assertNotIn("shop:cleaning_w", codes)

    def test_convenience_shortfall_is_filled_from_consumable(self):
        # 「収納・キッチン・時短・暮らし全般」は、本来の検索ワードだけでなく
        # extra_keywords（追加探索）を試しても0件のまま、というシナリオ。
        scarce_keywords = set(_all_keywords_for_categories(["収納", "キッチン", "時短", "暮らし全般"]))

        def fake_search_scarce_convenience(keyword: str, **kwargs):
            if keyword == "掃除 便利グッズ":
                return [_make_item("shop:only_cleaning_item", "掃除 便利グッズ 商品0")]
            if keyword in scarce_keywords:
                return []
            return _default_fake_search(keyword, **kwargs)

        candidates = self._run_main(fake_search_scarce_convenience)
        convenience = [c for c in candidates if c["_group"] == "convenience"]
        consumable = [c for c in candidates if c["_group"] == "consumable"]

        self.assertEqual(len(convenience), 1)
        self.assertEqual(len(consumable), 9)
        self.assertEqual(len(candidates), 10)

    def test_extra_keyword_is_used_when_primary_keyword_yields_nothing(self):
        # 「収納 便利グッズ」の結果が0件でも、settings.example.yamlに登録した
        # extra_keywordsの1つ目（"収納グッズ"）で見つかれば、そちらを使って
        # 収納カテゴリーが埋まることを確認する（2026-09-21実行分での
        # 候補不足（7件）への対応：単一キーワード依存で候補が0件になる
        # カテゴリーへの追加探索）。
        def fake_search(keyword: str, **kwargs):
            if keyword == "収納 便利グッズ":
                return []
            return _default_fake_search(keyword, **kwargs)

        candidates = self._run_main(fake_search)
        storage_names = [c["name"] for c in candidates if c.get("_category") == "収納"]
        self.assertTrue(
            any("収納グッズ" in name for name in storage_names),
            f"extra_keywordsが使われていない: {storage_names}",
        )

    def test_extra_keywords_are_not_queried_when_primary_already_has_results(self):
        # 無駄なAPI呼び出しを避けるため、本来の検索ワードで十分な結果が
        # あるときはextra_keywordsを一切検索しないことを確認する。
        queried_keywords: list[str] = []

        def fake_search(keyword: str, **kwargs):
            queried_keywords.append(keyword)
            return _default_fake_search(keyword, **kwargs)

        self._run_main(fake_search)

        settings = main_module.load_settings()
        all_extra_keywords: set[str] = set()
        for entry in settings["keywords"]:
            _keyword, _category, _group, extra_keywords = main_module._parse_keyword_entry(entry)
            all_extra_keywords.update(extra_keywords)

        queried_extra_keywords = all_extra_keywords & set(queried_keywords)
        self.assertEqual(queried_extra_keywords, set(), f"不要に検索された: {queried_extra_keywords}")

    def test_extra_keyword_results_still_go_through_quality_filters(self):
        # 追加探索（extra_keywords）で見つかった商品にも、レビュー評価4.0以上・
        # 件数100件以上等の既存の品質条件がそのまま適用されることを確認する
        # （候補不足を理由に条件を緩めていないことの確認）。
        def fake_search(keyword: str, **kwargs):
            if keyword == "収納 便利グッズ":
                return []
            if keyword == "収納グッズ":
                # レビュー件数が条件（100件以上）を満たさない商品。
                return [_make_item("shop:low_review_storage", "収納グッズ 低評価品", review_count=10)]
            return _default_fake_search(keyword, **kwargs)

        candidates = self._run_main(fake_search)
        codes = [c["item_code"] for c in candidates]
        self.assertNotIn("shop:low_review_storage", codes)

    def test_shortfall_is_not_padded_when_supply_is_genuinely_insufficient(self):
        # 便利グッズ・消耗品/飲料のどちらも、本来の検索ワード・extra_keywords
        # 全てを試しても十分な件数が見つからない場合、無理に10件へ埋めない
        # （重複や条件未達の商品を追加しない）ことを確認する。
        def fake_search(keyword: str, **kwargs):
            if keyword == "掃除 便利グッズ":
                return [_make_item("shop:only_cleaning_item", "掃除 便利グッズ 商品0")]
            return []

        candidates = self._run_main(fake_search)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["item_code"], "shop:only_cleaning_item")

    def test_supply_diagnostics_summary_shows_counts_and_keywords_tried(self):
        summary_path = Path(self.tmpdir.name) / "step_summary.md"
        os.environ["GITHUB_STEP_SUMMARY"] = str(summary_path)
        self.addCleanup(lambda: os.environ.pop("GITHUB_STEP_SUMMARY", None))

        def fake_search(keyword: str, **kwargs):
            if keyword == "収納 便利グッズ":
                return []
            return _default_fake_search(keyword, **kwargs)

        self._run_main(fake_search)

        content = summary_path.read_text(encoding="utf-8")
        self.assertIn("候補生成の内訳（不足時の原因確認用）", content)
        self.assertIn("暮らしの便利グッズ: 5/5件", content)
        self.assertIn("消耗品・飲料: 5/5件", content)
        # 収納カテゴリーの行に、本来の検索ワードと実際に使われた追加検索ワードの
        # 両方が記録されていることを確認する。
        self.assertIn("収納 便利グッズ → 収納グッズ", content)


class DailyRandomSeedTest(unittest.TestCase):
    """同じ商品タイプ・カテゴリーの連投防止で使う乱数シード（_daily_random_seed）。

    「同じ日のうちの再実行では同じ順、日付が変われば自然に変わる」ことを確認する。
    """

    def test_same_jst_date_produces_the_same_seed(self):
        from datetime import datetime, timedelta, timezone

        jst = timezone(timedelta(hours=9))
        morning = datetime(2026, 9, 21, 1, 0, tzinfo=jst)
        evening = datetime(2026, 9, 21, 23, 0, tzinfo=jst)
        self.assertEqual(
            main_module._daily_random_seed(morning), main_module._daily_random_seed(evening)
        )

    def test_different_dates_produce_different_seeds(self):
        from datetime import datetime, timedelta, timezone

        jst = timezone(timedelta(hours=9))
        day1 = datetime(2026, 9, 21, 12, 0, tzinfo=jst)
        day2 = datetime(2026, 9, 22, 12, 0, tzinfo=jst)
        self.assertNotEqual(
            main_module._daily_random_seed(day1), main_module._daily_random_seed(day2)
        )


class PostedEntryProductTypeTest(unittest.TestCase):
    """投稿済み履歴1件から商品タイプを判定する_posted_entry_product_type。

    候補側のitem["_product_type"]（description_generator.classify_product_type）と
    同じ判定ロジック（match_product_type_keyword優先）を使うこと、
    categoryが無い過去データを勝手にDEFAULT_CATEGORY等へ補完しないことを確認する。
    """

    def test_uses_specific_product_type_keyword_when_matched(self):
        entry = {"product_name": "ダスキン スポンジ 3個セット", "category": "キッチン消耗品"}
        self.assertEqual(main_module._posted_entry_product_type(entry), "スポンジ")

    def test_falls_back_to_stored_category_when_no_keyword_matches(self):
        entry = {"product_name": "よくある収納ラック", "category": "収納"}
        self.assertEqual(main_module._posted_entry_product_type(entry), "収納")

    def test_missing_category_is_not_fabricated(self):
        # categoryが保存されていない過去データは、判定できる情報が無いので
        # 空文字を返す（DEFAULT_CATEGORY等を勝手に補わない＝集計対象から自然に外れる）。
        entry = {"product_name": "何かの商品"}
        self.assertEqual(main_module._posted_entry_product_type(entry), "")


class ProductTypeDiversityPipelineTest(unittest.TestCase):
    """商品タイプの偏り防止（priority_tier）をパイプライン全体で確認する統合テスト。

    「スポンジを投稿した翌日に別メーカーのスポンジが出た場合」の再現。
    """

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        tmp_path = Path(self.tmpdir.name)
        self.candidates_dir = tmp_path / "candidates"
        self.posted_items_path = tmp_path / "posted_items.json"

        candidates_patcher = mock.patch.object(main_module, "CANDIDATES_DIR", self.candidates_dir)
        posted_patcher = mock.patch.object(main_module, "POSTED_ITEMS_PATH", self.posted_items_path)
        candidates_patcher.start()
        posted_patcher.start()
        self.addCleanup(candidates_patcher.stop)
        self.addCleanup(posted_patcher.stop)

        os.environ["RAKUTEN_APP_ID"] = "dummy-app-id-for-tests"
        os.environ["RAKUTEN_ACCESS_KEY"] = "dummy-access-key-for-tests"
        os.environ.pop("GITHUB_STEP_SUMMARY", None)
        self.addCleanup(lambda: os.environ.pop("RAKUTEN_APP_ID", None))
        self.addCleanup(lambda: os.environ.pop("RAKUTEN_ACCESS_KEY", None))

    def _run_main(self, fake_search) -> list[dict]:
        with mock.patch.object(rakuten_api, "search_items", side_effect=fake_search):
            main_module.main()
        latest = sorted(self.candidates_dir.glob("candidates_*.json"))[-1]
        with latest.open(encoding="utf-8") as f:
            return json.load(f)

    def _seed_posted_history_with_recent_sponge(self):
        from datetime import datetime, timedelta, timezone

        recent = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        self.posted_items_path.parent.mkdir(parents=True, exist_ok=True)
        with self.posted_items_path.open("w", encoding="utf-8") as f:
            json.dump(
                {
                    "posted_item_codes": ["shop:old_sponge"],
                    "posted_items": [
                        {
                            "item_code": "shop:old_sponge",
                            "item_url": "https://item.rakuten.co.jp/shop/old_sponge/",
                            "product_name": "旧スポンジ商品A",
                            "posted_at": recent,
                            "category": "キッチン消耗品",
                        }
                    ],
                },
                f,
            )

    def test_sponge_from_a_different_brand_is_deprioritized_but_still_selectable(self):
        # 「スポンジを投稿した翌日に別メーカーのスポンジが出た場合」の再現。
        # item_code・URL・商品名が違う（＝完全重複ではない）ため既存の重複除外には
        # 引っかからず、代わりに優先度調整（このテストの主題）だけが働く。
        self._seed_posted_history_with_recent_sponge()

        # 「消耗品・飲料」枠の他のキーワード（extra_keywordsを含む）は今回0件にし、
        # 検証対象の2商品（スポンジ／ラップ）だけで優先順位を確認できるようにする。
        settings = main_module.load_settings()
        other_consumable_keywords: set[str] = set()
        for entry in settings["keywords"]:
            kw, _category, group, extra = main_module._parse_keyword_entry(entry)
            if group == main_module.ranking.CONSUMABLE_GROUP:
                other_consumable_keywords.add(kw)
                other_consumable_keywords.update(extra)
        other_consumable_keywords.discard("キッチンスポンジ")
        other_consumable_keywords.discard("食品用ラップ")

        def fake_search(keyword: str, **kwargs):
            if keyword == "キッチンスポンジ":
                return [
                    _make_item(
                        "shop:new_sponge_brandX", "ブランドX キッチンスポンジ 5個入り", review_count=9000
                    )
                ]
            if keyword == "食品用ラップ":
                return [_make_item("shop:wrap_item", "野菜つつむ 食品用ラップ", review_count=300)]
            if keyword in other_consumable_keywords:
                return []
            return _default_fake_search(keyword, **kwargs)

        candidates = self._run_main(fake_search)
        codes = [c["item_code"] for c in candidates]

        # 別メーカーのスポンジ（完全重複ではない）は除外されず、候補に残る。
        self.assertIn("shop:new_sponge_brandX", codes)
        self.assertIn("shop:wrap_item", codes)

        sponge_item = next(c for c in candidates if c["item_code"] == "shop:new_sponge_brandX")
        self.assertEqual(sponge_item["_product_type"], "スポンジ")

        # 同じ「消耗品・飲料」枠・同じカテゴリーの中では、直近投稿していない
        # 商品タイプ（ラップ）が優先され、スポンジより前に並ぶ
        # （除外ではなく優先度を下げているだけ、という設計の確認）。
        self.assertLess(codes.index("shop:wrap_item"), codes.index("shop:new_sponge_brandX"))


if __name__ == "__main__":
    unittest.main()
