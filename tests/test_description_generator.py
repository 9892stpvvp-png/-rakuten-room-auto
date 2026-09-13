"""紹介文生成の回帰テスト。

実際にGitHub Actionsの上位10件で見つかった「商品情報にない特徴が紹介文に
混入する」バグの再発を防ぐためのテスト。標準ライブラリのunittestのみを使い、
追加のライブラリ（pytestなど）は必要ない。

実行方法:
    python -m unittest tests.test_description_generator -v
または:
    python -m unittest discover -s tests
"""

from __future__ import annotations

import unittest

from src import description_generator as dg


def make_item(
    name: str,
    item_caption: str = "",
    review_average: float = 4.5,
    review_count: int = 200,
    item_code: str = "",
) -> dict:
    return {
        "item_code": item_code or name,
        "name": name,
        "catch_copy": "",
        "item_caption": item_caption,
        "price": 1000,
        "review_average": review_average,
        "review_count": review_count,
        "item_url": "https://item.rakuten.co.jp/shop/example/",
        "image_url": "https://example.com/example.jpg",
        "shop_name": "テストショップ",
    }


BASE_HASHTAGS = ["#楽天ROOM", "#暮らしの便利グッズ"]


class FeatureHintFalsePositiveRegressionTest(unittest.TestCase):
    """商品情報から確認できない特徴が紹介文に混入しないことを確認する。

    商品説明（itemCaption）の後半に、他商品との比較や付属品の説明として
    無関係な単語（充電式・ステンレス・透明など）が含まれていても、
    それを商品自体の特徴として誤って拾ってはいけない。
    """

    def test_soup_maker_does_not_claim_rechargeable(self):
        # 「スープメーカー」自体は充電式ではないが、説明文の後半に
        # 比較対象として「充電式」という単語が登場するケースを再現する。
        item = make_item(
            name="スープメーカー",
            item_caption=(
                "毎日の食卓に温かいスープを手軽に。"
                "充電式のハンディブレンダーと比較されることも多いですが、"
                "本製品はコンセントに差し込んで使うタイプです。"
            ),
        )
        description = dg.generate_description(item, category="キッチン", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("充電式", description)

    def test_refill_mini_does_not_claim_stainless(self):
        # 「詰め替えそのまま MINI」自体はステンレス製ではないが、説明文の後半に
        # 対応するボトルの説明として「ステンレス」という単語が登場するケースを再現する。
        item = make_item(
            name="詰め替えそのまま MINI",
            item_caption=(
                "ボトルに直接ジョイントして詰め替えができるミニサイズです。"
                "ステンレスボトルの口径にも対応しています。"
            ),
        )
        description = dg.generate_description(item, category="キッチン", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("ステンレス", description)

    def test_cardboard_stocker_does_not_claim_stainless(self):
        # 「段ボールストッカー」自体はステンレス製ではないが、説明文の後半に
        # 付属フックの素材として「ステンレス」という単語が登場するケースを再現する。
        item = make_item(
            name="段ボールストッカー",
            item_caption=(
                "たたんだ段ボールをすっきりまとめて置けるストッカーです。"
                "持ち手はステンレス素材のフックに掛けることもできます。"
            ),
        )
        description = dg.generate_description(item, category="収納", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("ステンレス", description)

    def test_magic_tape_does_not_claim_transparent(self):
        # 「魔法のテープ」自体は透明な収納ケースではないが、説明文の後半に
        # 一緒に使うと便利な組み合わせ商品として「透明」という単語が登場するケースを再現する。
        item = make_item(
            name="魔法のテープ",
            item_caption=(
                "貼ってはがせる便利な両面テープです。"
                "透明な収納ケースと一緒に使うのもおすすめです。"
            ),
        )
        description = dg.generate_description(item, category=dg.DEFAULT_CATEGORY, base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("中身が見えてわかりやすいタイプ", description)


class FeatureHintTruePositiveTest(unittest.TestCase):
    """商品名・商品説明の最初の一文に明記されている特徴は、引き続き正しく反映されることを確認する。"""

    def test_magnet_rack_still_detects_magnet_from_name(self):
        item = make_item(
            name="tower マグネットバスルームラック",
            item_caption="マグネットで壁面に浮かせて設置できるバスルームラックです。水はねが多い浴室でも使いやすい設計です。",
        )
        description = dg.generate_description(item, category="収納", base_hashtags=BASE_HASHTAGS)
        self.assertIn("マグネット", description)


class CategoryRefinementRegressionTest(unittest.TestCase):
    """検索キーワード由来のカテゴリが商品内容と合わない場合に、商品名から補正されることを確認する。"""

    def test_clothes_compression_bag_is_reclassified_as_storage(self):
        item = make_item(name="衣類圧縮袋 トラベル用 8枚セット")
        # 「掃除 便利グッズ」での検索結果に混ざった、という想定。
        refined = dg.refine_category(item, "掃除")
        self.assertEqual(refined, "収納")

    def test_clothes_compression_bag_hashtag_is_storage_not_cleaning(self):
        item = make_item(name="衣類圧縮袋 トラベル用 8枚セット")
        category = dg.refine_category(item, "掃除")
        description = dg.generate_description(item, category=category, base_hashtags=BASE_HASHTAGS)
        self.assertIn("#収納", description)
        self.assertNotIn("#掃除グッズ", description)

    def test_category_matching_own_keywords_is_not_changed(self):
        item = make_item(name="フロアワイパー 掃除用モップ")
        refined = dg.refine_category(item, "掃除")
        self.assertEqual(refined, "掃除")

    def test_category_with_no_keyword_match_is_unchanged(self):
        item = make_item(name="何にでも使える便利グッズX")
        refined = dg.refine_category(item, dg.DEFAULT_CATEGORY)
        self.assertEqual(refined, dg.DEFAULT_CATEGORY)


class DescriptionFormatTest(unittest.TestCase):
    """紹介文の基本フォーマット（文字数・箇条書きの数・ハッシュタグ）を確認する。"""

    def test_description_within_max_length(self):
        item = make_item(name="テスト商品", item_caption="これはテスト用の商品説明です。")
        description = dg.generate_description(item, category="収納", base_hashtags=BASE_HASHTAGS, max_length=500)
        self.assertLessEqual(len(description), 500)

    def test_description_has_two_to_four_bullet_points(self):
        item = make_item(name="テスト商品", item_caption="")
        description = dg.generate_description(item, category="収納", base_hashtags=BASE_HASHTAGS)
        bullet_count = description.count("・")
        self.assertGreaterEqual(bullet_count, 2)
        self.assertLessEqual(bullet_count, 4)

    def test_review_fact_is_always_included(self):
        item = make_item(name="テスト商品", review_average=4.2, review_count=345)
        description = dg.generate_description(item, category="キッチン", base_hashtags=BASE_HASHTAGS)
        self.assertIn("4.2", description)
        self.assertIn("345件", description)

    def test_no_feature_hint_falls_back_to_safe_generic_points(self):
        # 商品説明が空でも、無理に特徴を作らずカテゴリ共通の安全な言い回しで
        # 埋められることを確認する（推測で特徴を作らないという条件3の確認）。
        item = make_item(name="なんの変哲もない商品", item_caption="")
        description = dg.generate_description(item, category="時短", base_hashtags=BASE_HASHTAGS)
        for hint_keyword, hint_phrase in dg.FEATURE_HINTS:
            self.assertNotIn(hint_phrase, description)


if __name__ == "__main__":
    unittest.main()
