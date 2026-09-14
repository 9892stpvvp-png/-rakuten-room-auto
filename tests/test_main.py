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
        # 4つの便利グッズキーワードの商品をすべて投稿済み履歴に登録し、
        # 便利グッズ枠を大きく不足させる（_default_fake_searchは同じキーワードから
        # 似た名前の商品を3件返すため、フェーズ2の類似商品統合で1件に絞られる。
        # つまり残る1キーワード分も最終的には1件になる）。
        # 消耗品・飲料枠から補充されて合計10件になることを確認する。
        excluded_keywords = ["収納 便利グッズ", "キッチン 時短グッズ", "時短家電", "生活雑貨 便利グッズ"]
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
        def fake_search_scarce_convenience(keyword: str, **kwargs):
            if keyword == "掃除 便利グッズ":
                return [_make_item("shop:only_cleaning_item", "掃除 便利グッズ 商品0")]
            if keyword in ("収納 便利グッズ", "キッチン 時短グッズ", "時短家電", "生活雑貨 便利グッズ"):
                return []
            return _default_fake_search(keyword, **kwargs)

        candidates = self._run_main(fake_search_scarce_convenience)
        convenience = [c for c in candidates if c["_group"] == "convenience"]
        consumable = [c for c in candidates if c["_group"] == "consumable"]

        self.assertEqual(len(convenience), 1)
        self.assertEqual(len(consumable), 9)
        self.assertEqual(len(candidates), 10)


if __name__ == "__main__":
    unittest.main()
