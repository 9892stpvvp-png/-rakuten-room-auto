"""紹介文生成の回帰テスト。

実際にGitHub Actionsの本番実行で見つかった「商品情報にない特徴が紹介文に
混入する」バグの再発を防ぐためのテスト。ここで使っている商品名は、実際に
楽天ウェブサービスから返ってきたレスポンス（本番のGitHub Actions実行ログ）を
そのまま使っている。標準ライブラリのunittestのみを使い、追加のライブラリ
（pytestなど）は必要ない。

実行方法:
    python -m unittest tests.test_description_generator -v
または:
    python -m unittest discover -s tests

## 見つかった問題と対応（経緯）

1回目の修正では、特徴語の検出対象を「商品名＋商品説明の最初の一文」に
限定したが、それでも本番のSummaryには誤った特徴が残っていた。実際の
レスポンスを確認したところ、原因は次の2点だった。

- 商品説明（itemCaption）が句点（。）を含まない仕様一覧形式
  （例：「素材/材質：エラストマー、ステンレス、…」）のことがあり、
  「最初の一文」のつもりが説明文全体を拾ってしまっていた
- まれに、その商品とは無関係な説明文が入っていた
  （「スープメーカー」の説明文の冒頭が搾乳機の説明になっていた）

このため、特徴語の検出は商品説明を一切使わず「商品名」だけに限定した。
また、カテゴリ判定も「商品名に1語でも含まれていれば元のカテゴリのまま」
という単純な判定だと、「掃除機不要」という言葉に含まれる『掃除』の1語
だけで『収納』の商品（衣類圧縮袋）が『掃除』カテゴリのままになって
しまうことが分かったため、キーワードの一致件数で比較するスコア方式に
変更した。
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

# 以下は実際にGitHub Actionsの本番実行(2026-09-13)で取得された商品名・商品説明。
REAL_SOUP_MAKER = make_item(
    name=(
        "【限定価格+特典あり】◆楽天1位3冠◆ スープメーカー 時短家電 ポタージュ スムージー "
        "冷製スープ 離乳食 豆乳 ブレンダー 自動調理ポット 全自動調理器 ミキサー おかゆ おから "
        "タイパ ミキサー シャーベット アイス 氷OK カレー 育児 出産祝い ギフト プレゼント LARUTAN"
    ),
    item_caption=(
        "ロングヒット！人気アイテム 片胸・両胸派も！充電式でラクラク搾乳 "
        "メーカー希望小売価格はメーカーサイトに基づいて掲載していますLARUTAN ポットクッカー "
        "ロングヒット！人気アイテム 【おいしくお使いいただくために】 本製品は、公式レシピ"
    ),
)

REAL_REFILL_MINI = make_item(
    name=(
        "【メーカー公式】詰め替えそのまま MINI3個組み セット MS-6W ホワイト 国産 日本産 "
        "メーカー直営 シャンプー コンディショナー リンス 詰め替えボトル 詰替 ディスペンサー "
        "ぶら下げ 洗剤パック 空中収納 吊り下げ お風呂 浮かせる収納"
    ),
    item_caption=(
        "商品情報素材/材質ポンプ：エラストマー、ポリアセタール、シリコーンゴム、ステンレス、"
        "ポリプロピレン、ホルダー：ポリアセタール、ステンレス、ポリプロピレン、"
        "ABS樹脂サイズ/寸法約5.1×3.5×9.6(長さ)cm、ホルダー：約4.1×3.4"
    ),
)

REAL_CARDBOARD_STOCKER = make_item(
    name=(
        "【当日発送】段ボールストッカー ダンボールストッカー 白 【段ボールを定位置まとめる】 "
        "ダンボールラック ダンボール収納 キャスター付き おしゃれ 段ボールストッカー スタンド "
        "収納 ラック 段ボール置き 段ボール立て"
    ),
    item_caption=(
        "■サイズ・容量 ■商品名：ダンボールストッカー ■カラー：ホワイト / ブラック "
        "■耐荷重：5kg ■収納部外寸：約W30×D25×H44.5cm（キャスター含む） "
        "■収納目安：約10～15枚 ■商品紹介 ■【段ボールを定位置に】収納場所・"
    ),
)

REAL_MAGIC_TAPE = make_item(
    name=(
        "【雑誌＆TV等紹介】魔法のテープ 正規品 高品質 はがせる 水洗い 両面テープ ナノテープ "
        "透明両面テープ 強力両面テープ 超強力 魔法のテープ極 粘着 強力 固定 防災 地震対策 "
        "（幅3cm 長さ1M）万能 送料無料 SNSでも話題! あす楽 便利グッズ 浮かせる収納 壁紙 車 DIY 多用途"
    ),
    item_caption=(
        "商品情報　商品名 iHouse all 両面テープ 魔法のテープ 極 粘着テープ 両面テープ 強力 "
        "両面テープ 剥がせる 両面テープ はがせる 両面テープ 超強力 強力両面テープ 透明 強力 "
        "防水 耐熱 超強力 張り替え あと残らない 便"
    ),
)

REAL_COMPRESSION_BAG = make_item(
    name=(
        "＼雑誌に掲載されました！／＼楽天ランキング1位獲得！／ 圧縮袋 圧縮 衣類 押すだけ "
        "掃除機不要 2枚セット 衣類圧縮袋 立体圧縮袋 手押し 衣類 収納 圧縮ボックス 衣類ケース "
        "カビ対策 防カビ ポンプ不要 衣類収納 衣替え 旅行 vc-bag-02"
    ),
    item_caption=(
        "テストする女性誌「LDK」 Best Buy 受賞 立体圧縮袋 2枚入り｜ポンプ不要 サイクロン排気 "
        "大容量 透明窓付き 防湿・防虫 jiangオリジナルの立体圧縮袋（2枚入り）。"
    ),
)

REAL_MAGNET_RACK = make_item(
    name=(
        "tower 《 山崎実業 マグネットバスルームラック タワー ワイド 》 幅27cm バスラック "
        "ディスペンサー シャンプーボトル フック4個付き お風呂収納 壁面 浴室 壁掛け 収納棚 "
        "浮かせる マグネットラック 磁石 公式 白 黒 おしゃれ 別注 9776 9777 YAMAZAKI"
    ),
    item_caption=(
        "■Detail -商品説明- 大人気のtowerの磁石がくっつく浴室壁面収納、マグネットバスルーム"
        "シリーズに、towerとコラボして生まれた当社オリジナル別注サイズのマグネットバスルーム"
        "ラックワイドが登場！"
    ),
)

REAL_MAGNET_HOOK = make_item(
    name=(
        "tower 《 山崎実業 マグネットバスルームフック タワー ラージ 》 5連フック 幅広タイプ "
        "壁付けマグネット収納 浮かせる収納 掃除用具 掃除道具 壁掛け マグネット 磁石 引っ掛け "
        "お風呂収納 すっきり おしゃれ 公式 シンプル 白 黒 YAMAZAKI"
    ),
    item_caption=(
        "■Detail -商品説明- 大人気のtowerの磁石がくっつく浴室壁面収納、マグネットバスルーム"
        "シリーズに、towerとコラボして生まれた当社オリジナル別注アイテムが仲間入り。"
        "便利な5連フックを幅広にすることでより様々なアイテムに対応で"
    ),
)

REAL_AIR_FRYER = make_item(
    name=(
        "【9/13 限定セール★最安値⇒7,990円】SAMKYO ノンフライヤー 4.2L 可視窓 大容量 1-4人用 "
        "エアフライヤー タッチパネル レシピ付き ノンフライヤー機 電気フライヤー 揚げ物 惣菜 "
        "1年保証 F40"
    ),
    item_caption=(
        "メーカー希望小売価格はメーカーサイトに基づいて掲載しています 商品説明 "
        "---------------------------------------------------- 商品紹介 "
        "--------------------------"
    ),
)


class RealDataRegressionTest(unittest.TestCase):
    """本番のGitHub Actions実行で実際に取得された商品データを使った回帰テスト。"""

    def test_soup_maker_does_not_claim_rechargeable(self):
        description = dg.generate_description(REAL_SOUP_MAKER, category="時短", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("充電式", description)

    def test_refill_mini_does_not_claim_stainless(self):
        description = dg.generate_description(REAL_REFILL_MINI, category="収納", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("ステンレス", description)

    def test_refill_mini_is_reclassified_as_storage(self):
        # 本番実行では「掃除」カテゴリのまま#掃除グッズになっていた商品。
        # 商品名には「空中収納」「吊り下げ」「浮かせる収納」など収納の言葉が多い。
        refined = dg.refine_category(REAL_REFILL_MINI, "掃除")
        self.assertEqual(refined, "収納")

    def test_refill_mini_hashtag_is_storage_not_cleaning(self):
        category = dg.refine_category(REAL_REFILL_MINI, "掃除")
        description = dg.generate_description(REAL_REFILL_MINI, category=category, base_hashtags=BASE_HASHTAGS)
        self.assertIn("#収納", description)
        self.assertNotIn("#掃除グッズ", description)

    def test_cardboard_stocker_does_not_claim_stainless(self):
        description = dg.generate_description(REAL_CARDBOARD_STOCKER, category="収納", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("ステンレス", description)

    def test_magic_tape_does_not_claim_waterproof_or_transparent_contents(self):
        description = dg.generate_description(REAL_MAGIC_TAPE, category="収納", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("防水仕様", description)
        self.assertNotIn("中身が見えてわかりやすいタイプ", description)

    def test_compression_bag_is_reclassified_as_storage(self):
        # 商品名に「掃除機不要」という言葉が含まれるため、単純な1語一致の判定だと
        # 「掃除」カテゴリのままになってしまっていた（実際に本番で起きた問題）。
        refined = dg.refine_category(REAL_COMPRESSION_BAG, "掃除")
        self.assertEqual(refined, "収納")

    def test_compression_bag_hashtag_is_storage_not_cleaning(self):
        category = dg.refine_category(REAL_COMPRESSION_BAG, "掃除")
        description = dg.generate_description(REAL_COMPRESSION_BAG, category=category, base_hashtags=BASE_HASHTAGS)
        self.assertIn("#収納", description)
        self.assertNotIn("#掃除グッズ", description)

    def test_magnet_rack_still_detects_magnet_from_name(self):
        # 商品説明を使わなくなった後も、商品名に明記されている特徴は
        # 引き続き正しく検出できることを確認する。
        description = dg.generate_description(REAL_MAGNET_RACK, category="収納", base_hashtags=BASE_HASHTAGS)
        self.assertIn("マグネット", description)

    def test_magnet_hook_is_reclassified_as_storage(self):
        # 本番実行では「掃除」カテゴリのまま#掃除グッズになっていた商品。
        # 商品名に「掃除用具」「掃除道具」という言葉があるが、これらは
        # クリーナー・モップ等の掃除道具そのものではないため掃除カテゴリの
        # キーワードには一致せず、「収納」「フック」の方が優先されるべき。
        refined = dg.refine_category(REAL_MAGNET_HOOK, "掃除")
        self.assertEqual(refined, "収納")

    def test_magnet_hook_hashtag_is_storage_not_cleaning(self):
        category = dg.refine_category(REAL_MAGNET_HOOK, "掃除")
        description = dg.generate_description(REAL_MAGNET_HOOK, category=category, base_hashtags=BASE_HASHTAGS)
        self.assertIn("#収納", description)
        self.assertNotIn("#掃除グッズ", description)

    def test_air_fryer_large_capacity_does_not_use_storage_wording(self):
        # 本番実行では「大容量」が収納用品向けの「たっぷり収納できる大容量タイプ」に
        # なってしまい、調理家電として不自然だった。カテゴリは「時短」のまま。
        category = dg.refine_category(REAL_AIR_FRYER, "時短")
        self.assertEqual(category, "時短")
        description = dg.generate_description(REAL_AIR_FRYER, category=category, base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("収納できる大容量タイプ", description)
        self.assertNotIn("収納", description)


class CategoryRefinementTest(unittest.TestCase):
    """refine_category()の基本的な挙動を確認する。"""

    def test_category_matching_own_keywords_is_not_changed(self):
        item = make_item(name="フロアワイパー 掃除用モップ")
        self.assertEqual(dg.refine_category(item, "掃除"), "掃除")

    def test_category_with_no_keyword_match_is_unchanged(self):
        item = make_item(name="何にでも使える便利グッズX")
        self.assertEqual(dg.refine_category(item, dg.DEFAULT_CATEGORY), dg.DEFAULT_CATEGORY)

    def test_tie_prefers_assigned_category(self):
        # 「モップ」(掃除)と「ケース」(収納)が1件ずつで同点の場合は、元のカテゴリを優先する。
        item = make_item(name="モップ ケース")
        self.assertEqual(dg.refine_category(item, "掃除"), "掃除")
        self.assertEqual(dg.refine_category(item, "収納"), "収納")

    def test_cleaning_tool_word_is_required_not_just_kanji(self):
        # 「掃除」という言葉だけでは掃除カテゴリと判定しない
        # （「掃除機不要」等の宣伝文句に頻出するため）。
        item = make_item(name="お掃除がラクになる 収納ラック")
        self.assertEqual(dg.refine_category(item, "掃除"), "収納")

    def test_negated_vacuum_cleaner_phrase_does_not_count_as_cleaning(self):
        item = make_item(name="衣類圧縮袋 掃除機不要 収納ケース")
        self.assertEqual(dg.refine_category(item, "掃除"), "収納")

    def test_actual_vacuum_cleaner_still_counts_as_cleaning(self):
        item = make_item(name="コードレス掃除機 ハンディクリーナー")
        self.assertEqual(dg.refine_category(item, dg.DEFAULT_CATEGORY), "掃除")


class DescriptionFormatTest(unittest.TestCase):
    """紹介文の基本フォーマット（文字数・箇条書きの数・ハッシュタグ）を確認する。"""

    def test_description_within_max_length(self):
        item = make_item(name="テスト商品")
        description = dg.generate_description(item, category="収納", base_hashtags=BASE_HASHTAGS, max_length=500)
        self.assertLessEqual(len(description), 500)

    def test_description_has_two_to_four_bullet_points(self):
        item = make_item(name="テスト商品")
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
        # 商品名に特徴語が無くても、無理に特徴を作らずカテゴリ共通の安全な
        # 言い回しで埋められることを確認する（推測で特徴を作らないという条件の確認）。
        item = make_item(name="なんの変哲もない商品")
        description = dg.generate_description(item, category="時短", base_hashtags=BASE_HASHTAGS)
        for _hint_keyword, hint_phrase, _hint_emoji in dg.FEATURE_HINTS:
            resolved_phrase = dg._resolve_by_category(hint_phrase, "時短")
            self.assertNotIn(resolved_phrase, description)

    def test_item_caption_is_not_used_for_feature_detection(self):
        # 商品名には特徴語が無く、商品説明にだけ「ステンレス」がある場合、
        # 商品説明は特徴抽出に使わないため、紹介文に出てこないことを確認する。
        item = make_item(name="なんの変哲もない商品", item_caption="素材：ステンレス、ポリプロピレン")
        description = dg.generate_description(item, category="キッチン", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("ステンレス", description)


# 紹介文で使われうる絵文字をすべて集めた集合（テストでの絵文字カウント・検出に使う）。
def _all_known_emojis() -> set[str]:
    emojis: set[str] = {dg.REVIEW_EMOJI}
    for pool in dg.CATEGORY_EMOJIS.values():
        emojis.update(pool)
    for points in dg.POINT_VARIANTS.values():
        for _text, emoji in points:
            emojis.add(emoji)
    for _keyword, _phrase_spec, emoji_spec in dg.FEATURE_HINTS:
        if isinstance(emoji_spec, dict):
            emojis.update(emoji_spec.values())
        else:
            emojis.add(emoji_spec)
    return emojis


ALL_KNOWN_EMOJIS = _all_known_emojis()


class EmojiFormatTest(unittest.TestCase):
    """紹介文への絵文字の付け方を確認する。"""

    def _count_known_emojis(self, text: str) -> int:
        return sum(text.count(emoji) for emoji in ALL_KNOWN_EMOJIS)

    def test_total_emoji_count_is_within_expected_range(self):
        item = make_item(name="テスト商品")
        for category in dg.CATEGORY_EMOJIS:
            description = dg.generate_description(item, category=category, base_hashtags=BASE_HASHTAGS)
            count = self._count_known_emojis(description)
            self.assertGreaterEqual(count, 3, f"category={category}: {description}")
            self.assertLessEqual(count, 6, f"category={category}: {description}")

    def test_intro_line_starts_with_category_emoji(self):
        item = make_item(name="テスト商品")
        for category, pool in dg.CATEGORY_EMOJIS.items():
            description = dg.generate_description(item, category=category, base_hashtags=BASE_HASHTAGS)
            intro_line = description.split("\n", 1)[0]
            first_token = intro_line.split(" ", 1)[0]
            self.assertIn(first_token, pool, f"category={category}: {intro_line!r}")

    def test_review_line_uses_star_emoji(self):
        item = make_item(name="テスト商品", review_average=4.6, review_count=999)
        description = dg.generate_description(item, category="収納", base_hashtags=BASE_HASHTAGS)
        review_line = next(line for line in description.splitlines() if "レビュー評価" in line)
        self.assertTrue(review_line.startswith(f"・{dg.REVIEW_EMOJI} "), review_line)

    def test_hashtag_line_has_no_emoji(self):
        item = make_item(name="テスト商品")
        for category in dg.CATEGORY_EMOJIS:
            description = dg.generate_description(item, category=category, base_hashtags=BASE_HASHTAGS)
            hashtag_line = description.splitlines()[-1]
            self.assertTrue(hashtag_line.startswith("#"), hashtag_line)
            for emoji in ALL_KNOWN_EMOJIS:
                self.assertNotIn(emoji, hashtag_line)

    def test_magnet_rack_bullet_uses_magnet_emoji(self):
        description = dg.generate_description(REAL_MAGNET_RACK, category="収納", base_hashtags=BASE_HASHTAGS)
        self.assertIn("・🧲 マグネット", description)

    def test_air_fryer_bullet_does_not_use_storage_emoji_for_capacity(self):
        # 「大容量」の絵文字も、収納カテゴリ向けの📦を時短カテゴリでは使わない。
        category = dg.refine_category(REAL_AIR_FRYER, "時短")
        description = dg.generate_description(REAL_AIR_FRYER, category=category, base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("📦", description)

    def test_no_emoji_repeated_back_to_back_in_bullets(self):
        # 特徴を検出できない商品でも、箇条書き2件の絵文字が同じにならないことを確認する
        # （POINT_VARIANTSの各カテゴリ内で絵文字が重複していないことの確認）。
        item = make_item(name="なんの変哲もない商品")
        for category in dg.CATEGORY_EMOJIS:
            description = dg.generate_description(item, category=category, base_hashtags=BASE_HASHTAGS)
            bullet_lines = [line for line in description.splitlines() if line.startswith("・")]
            bullet_emojis = [line.split(" ", 1)[0].removeprefix("・") for line in bullet_lines]
            self.assertEqual(
                len(bullet_emojis), len(set(bullet_emojis)), f"category={category}: {bullet_emojis}"
            )


if __name__ == "__main__":
    unittest.main()
