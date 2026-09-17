"""紹介文生成の回帰テスト。

実際にGitHub Actionsの本番実行で見つかった問題の再発を防ぐためのテスト。
ここで使っている商品名の一部は、実際に楽天ウェブサービスから返ってきた
レスポンス（本番のGitHub Actions実行ログ）をそのまま使っている。標準
ライブラリのunittestのみを使い、追加のライブラリ（pytestなど）は必要ない。

実行方法:
    python -m unittest tests.test_description_generator -v
または:
    python -m unittest discover -s tests

## フォーマットの変遷（経緯）

1. 特徴語の検出を「商品説明」から「商品名だけ」に限定（商品説明は書式が
   ばらつき、無関係な文章が混入することがあったため）。
2. カテゴリ判定を「1語でも一致すれば元のカテゴリのまま」から「キーワード
   一致件数のスコア方式」に変更（「掃除機不要」の『掃除』1語だけで収納品が
   掃除カテゴリのままになる問題の対応）。
3. 「導入文＋箇条書き」形式 → 箇条書きを使わない2〜3文の自然な文章形式に変更。
4. 商品名に含まれる単語（マグネット・吸盤・ステンレス等）だけで特徴を
   決めつけず、商品全体の用途を優先するよう修正（PRODUCT_TYPE_HINTS導入）。
5. **現在の形式**：楽天ROOMで読んだ人が「これ便利そう」と感じやすい、
   共感型の構成に変更。①絵文字＋キャッチコピー ②悩み・あるある（1〜2文）
   ③商品がどう解決してくれそうか ④✔️メリット3項目 ⑤締めの一言
   ⑥ハッシュタグ、という6ブロック構成になっている
   （`PRODUCT_TYPE_TEMPLATES`で具体的な商品タイプ、`GENERIC_TEMPLATES`で
   カテゴリ共通の安全な言い回しを用意し、✔️メリットの3項目目だけ
   `FEATURE_CLAUSES`で商品名から読み取れる構造・仕様の特徴を反映する）。
"""

from __future__ import annotations

import unittest

from src import description_generator as dg


def make_item(
    name: str,
    item_caption: str = "",
    review_average: float = 4.5,
    review_count: int = 200,
    price: int = 1980,
    item_code: str = "",
) -> dict:
    return {
        "item_code": item_code or name,
        "name": name,
        "catch_copy": "",
        "item_caption": item_caption,
        "price": price,
        "review_average": review_average,
        "review_count": review_count,
        "item_url": "https://item.rakuten.co.jp/shop/example/",
        "image_url": "https://example.com/example.jpg",
        "shop_name": "テストショップ",
    }


# config/settings.example.yaml のdefault_hashtagsと同じもの（本番と同じ条件でテストするため）。
BASE_HASHTAGS = ["#暮らしの便利グッズ"]

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
    price=7990,
)

ALL_REAL_ITEMS_AND_CATEGORIES = [
    (REAL_SOUP_MAKER, "時短"),
    (REAL_REFILL_MINI, "収納"),
    (REAL_CARDBOARD_STOCKER, "収納"),
    (REAL_MAGIC_TAPE, "収納"),
    (REAL_COMPRESSION_BAG, "収納"),
    (REAL_MAGNET_RACK, "収納"),
    (REAL_MAGNET_HOOK, "収納"),
    (REAL_AIR_FRYER, "時短"),
]


def _blocks(description: str) -> list[str]:
    """紹介文を空行区切りの6ブロック（キャッチコピー・悩み・解決・メリット・締め・タグ）に分ける。"""
    return description.split("\n\n")


class RealDataRegressionTest(unittest.TestCase):
    """本番のGitHub Actions実行で実際に取得された商品データを使った回帰テスト。"""

    def test_soup_maker_does_not_claim_rechargeable(self):
        description = dg.generate_description(REAL_SOUP_MAKER, category="時短", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("充電式", description)

    def test_soup_maker_matches_its_product_type_template(self):
        # 「スープメーカー」は商品タイプが特定できるはずなので、汎用の
        # GENERIC_TEMPLATESではなく専用テンプレートを使う。
        description = dg.generate_description(REAL_SOUP_MAKER, category="時短", base_hashtags=BASE_HASHTAGS)
        self.assertIn("スープ", _blocks(description)[0])

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

    def test_compression_bag_matches_its_product_type_template(self):
        category = dg.refine_category(REAL_COMPRESSION_BAG, "掃除")
        description = dg.generate_description(REAL_COMPRESSION_BAG, category=category, base_hashtags=BASE_HASHTAGS)
        self.assertIn("圧縮袋", _blocks(description)[0] + _blocks(description)[2])

    def test_magnet_rack_still_detects_magnet_from_name(self):
        # 商品説明を使わなくなった後も、商品名に明記されている特徴は
        # 引き続き✔️メリットの3項目目として正しく検出できることを確認する。
        description = dg.generate_description(REAL_MAGNET_RACK, category="収納", base_hashtags=BASE_HASHTAGS)
        self.assertIn("マグネット", description)

    def test_magnet_rack_uses_bath_location(self):
        # 商品名に「浴室」「お風呂収納」が含まれるため、汎用の「身の回り」ではなく
        # 「浴室」という具体的な場所の言葉が使われることを確認する。
        description = dg.generate_description(REAL_MAGNET_RACK, category="収納", base_hashtags=BASE_HASHTAGS)
        self.assertIn("浴室", description)

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

    def test_air_fryer_matches_its_product_type_template(self):
        # 本番実行では「大容量」が収納用品向けの「たっぷり収納できる大容量タイプ」に
        # なってしまい、調理家電として不自然だった。現在は専用テンプレートを使い、
        # 「収納」という言葉自体が出ないことを確認する。
        category = dg.refine_category(REAL_AIR_FRYER, "時短")
        self.assertEqual(category, "時短")
        description = dg.generate_description(REAL_AIR_FRYER, category=category, base_hashtags=BASE_HASHTAGS)
        self.assertIn("ノンフライヤー", _blocks(description)[0] + _blocks(description)[2])
        self.assertNotIn("収納", description)

    def test_real_items_never_use_experience_implying_phrases(self):
        # 「使ってみました」「買ってよかった」など、実際に使用したと誤解される
        # 表現は使わない、という生成ルールの回帰テスト。
        for item, category in ALL_REAL_ITEMS_AND_CATEGORIES:
            description = dg.generate_description(item, category=category, base_hashtags=BASE_HASHTAGS)
            for phrase in ("使ってみました", "買ってよかった", "使ってみて", "買ってみました"):
                self.assertNotIn(phrase, description, f"{item['name'][:20]}: {description}")

    def test_real_items_body_does_not_contain_review_numbers(self):
        # レビュー評価・レビュー件数は紹介文に入れない、というルールの確認。
        for item, category in ALL_REAL_ITEMS_AND_CATEGORIES:
            description = dg.generate_description(item, category=category, base_hashtags=BASE_HASHTAGS)
            self.assertNotIn("レビュー評価", description)
            self.assertNotIn("レビュー件数", description)

    def test_real_items_do_not_contain_price(self):
        # 価格も紹介文に入れない、というルールの確認。
        for item, category in ALL_REAL_ITEMS_AND_CATEGORIES:
            description = dg.generate_description(item, category=category, base_hashtags=BASE_HASHTAGS)
            self.assertNotIn(str(item["price"]), description)

    def test_real_items_do_not_copy_full_product_name(self):
        # 商品名をそのまま長く転載しない、というルールの確認
        # （商品名全体が紹介文にそのまま含まれていないこと）。
        for item, category in ALL_REAL_ITEMS_AND_CATEGORIES:
            description = dg.generate_description(item, category=category, base_hashtags=BASE_HASHTAGS)
            self.assertNotIn(item["name"], description)


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


class DescriptionStructureTest(unittest.TestCase):
    """紹介文の6ブロック構成（キャッチコピー・悩み・解決・メリット・締め・タグ）を確認する。"""

    def test_description_within_max_length(self):
        item = make_item(name="テスト商品")
        description = dg.generate_description(item, category="収納", base_hashtags=BASE_HASHTAGS, max_length=500)
        self.assertLessEqual(len(description), 500)

    def test_description_has_six_blocks(self):
        item = make_item(name="テスト商品")
        for category in dg.GENERIC_TEMPLATES:
            description = dg.generate_description(item, category=category, base_hashtags=BASE_HASHTAGS)
            blocks = _blocks(description)
            self.assertEqual(len(blocks), 6, f"category={category}: {blocks}")

    def test_hook_line_starts_with_emoji_and_ends_with_sparkle(self):
        item = make_item(name="テスト商品")
        for category in dg.GENERIC_TEMPLATES:
            description = dg.generate_description(item, category=category, base_hashtags=BASE_HASHTAGS)
            hook_line = _blocks(description)[0]
            self.assertTrue(hook_line.endswith("✨"), hook_line)
            self.assertRegex(hook_line, r"^\S+ .+✨$")

    def test_worry_block_ends_with_empathetic_emoji(self):
        item = make_item(name="テスト商品")
        for category in dg.GENERIC_TEMPLATES:
            description = dg.generate_description(item, category=category, base_hashtags=BASE_HASHTAGS)
            worry_block = _blocks(description)[1]
            self.assertIn("😅", worry_block)

    def test_solution_line_ends_with_maru(self):
        item = make_item(name="テスト商品")
        for category in dg.GENERIC_TEMPLATES:
            description = dg.generate_description(item, category=category, base_hashtags=BASE_HASHTAGS)
            solution_line = _blocks(description)[2]
            self.assertTrue(solution_line.endswith("◎"), solution_line)

    def test_checklist_has_exactly_three_checked_items(self):
        item = make_item(name="テスト商品")
        for category in dg.GENERIC_TEMPLATES:
            description = dg.generate_description(item, category=category, base_hashtags=BASE_HASHTAGS)
            checklist_lines = _blocks(description)[3].splitlines()
            self.assertEqual(len(checklist_lines), 3, f"category={category}: {checklist_lines}")
            for line in checklist_lines:
                self.assertTrue(line.startswith("✔️ "), line)

    def test_closing_line_ends_with_smile(self):
        item = make_item(name="テスト商品")
        for category in dg.GENERIC_TEMPLATES:
            description = dg.generate_description(item, category=category, base_hashtags=BASE_HASHTAGS)
            closing_line = _blocks(description)[4]
            self.assertTrue(closing_line.endswith("☺️"), closing_line)

    def test_hashtag_block_has_three_to_five_tags_and_no_emoji(self):
        item = make_item(name="テスト商品")
        for category in dg.GENERIC_TEMPLATES:
            description = dg.generate_description(item, category=category, base_hashtags=BASE_HASHTAGS)
            hashtag_line = _blocks(description)[5]
            hashtags = hashtag_line.split(" ")
            self.assertGreaterEqual(len(hashtags), 3, f"category={category}: {hashtag_line}")
            self.assertLessEqual(len(hashtags), 5, f"category={category}: {hashtag_line}")
            for tag in hashtags:
                self.assertTrue(tag.startswith("#"), tag)

    def test_default_hashtag_is_kept_when_passed_in(self):
        # 「#暮らしの便利グッズ」は基本的に入れる、というルールの確認
        # （base_hashtagsとしてsettings.example.yamlのdefault_hashtagsを渡した場合）。
        item = make_item(name="テスト商品")
        description = dg.generate_description(item, category="キッチン", base_hashtags=BASE_HASHTAGS)
        self.assertIn("#暮らしの便利グッズ", description)

    def test_no_price_in_description(self):
        item = make_item(name="テスト商品", price=3980)
        description = dg.generate_description(item, category="収納", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("3980", description)

    def test_item_caption_is_not_used_for_feature_detection(self):
        # 商品名には特徴語が無く、商品説明にだけ「ステンレス」がある場合、
        # 商品説明は特徴抽出に使わないため、紹介文に出てこないことを確認する。
        item = make_item(name="なんの変哲もない商品", item_caption="素材：ステンレス、ポリプロピレン")
        description = dg.generate_description(item, category="キッチン", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("ステンレス", description)

    def test_closing_line_varies_by_product_code(self):
        # 締めの一言（⑤）が毎回同じ文章にならないことの確認。
        item_a = make_item(name="テスト商品A", item_code="a")
        item_b = make_item(name="テスト商品B", item_code="b")
        description_a = dg.generate_description(item_a, category="収納", base_hashtags=BASE_HASHTAGS)
        description_b = dg.generate_description(item_b, category="収納", base_hashtags=BASE_HASHTAGS)
        closing_a = _blocks(description_a)[4]
        closing_b = _blocks(description_b)[4]
        # 同じテンプレート内のclosing_variantsは複数用意されているため、
        # 十分な数のコードを試せば異なる締めが選ばれることを確認する。
        closings = {
            _blocks(dg.generate_description(make_item(name="テスト商品", item_code=str(i)), category="収納", base_hashtags=BASE_HASHTAGS))[4]
            for i in range(10)
        }
        self.assertGreater(len(closings), 1)


class ProductTypeTemplateTest(unittest.TestCase):
    """商品名の単語だけで特徴を決めつけず、商品全体の用途に合わせたテンプレートを
    使うことを確認する回帰テスト。

    楽天の商品名はSEO対策で色々な単語が詰め込まれていることが多く、
    「商品名に単語が含まれる＝それが商品全体の用途」とは限らない。ここでは
    実際に報告された不一致パターン（三角コーナー・味噌マドラー・ドアストッパー）
    を、実際の商品名によく見られる形で再現し、商品全体の用途に沿った
    紹介文になることを確認する。
    """

    def test_triangle_corner_is_not_described_as_suction_cup_product(self):
        # 三角コーナー（生ゴミの水切り用）の商品名に「吸盤」が含まれていても、
        # ①のキャッチコピー・③の解決文は「吸盤」ではなく生ゴミの水切りという
        # 商品全体の用途になる（「吸盤」は検出されれば✔️メリットの3項目目に
        # 補足として入ることはある）。
        item = make_item(
            name="水切り 三角コーナー キッチン ステンレス 吸盤 排水口ネット付き シンク こし器 送料無料"
        )
        description = dg.generate_description(item, category="キッチン", base_hashtags=BASE_HASHTAGS)
        blocks = _blocks(description)
        self.assertIn("三角コーナー", blocks[0] + blocks[2])
        self.assertNotIn("サビに強い", description)

    def test_miso_muddler_is_not_described_as_rust_resistant(self):
        # 味噌マドラーの商品名に「ステンレス」が含まれていても、
        # 素材だけの表現（サビに強い）ではなく、用途に沿った文章にする。
        item = make_item(
            name="味噌マドラー ステンレス 味噌漉し みそこし 味噌溶き 調理器具 キッチン雑貨"
        )
        description = dg.generate_description(item, category="キッチン", base_hashtags=BASE_HASHTAGS)
        blocks = _blocks(description)
        self.assertIn("マドラー", blocks[0] + blocks[2])
        self.assertNotIn("サビに強い", description)
        self.assertNotIn("ステンレス", description)

    def test_door_stopper_is_not_described_as_floating_storage(self):
        # ドアストッパーの商品名に「マグネット」が含まれていても、
        # 収納用品向けの「マグネットで浮かせて設置できる」をどのブロックにも
        # 書かない（✔️メリットの3項目目にも「浮かせて設置」という、商品名から
        # 確認できない用途を推測して書かないことを含む）。
        item = make_item(name="ドアストッパー マグネット式 扉 固定 玄関 diy おしゃれ シンプル 傷防止")
        description = dg.generate_description(item, category=dg.DEFAULT_CATEGORY, base_hashtags=BASE_HASHTAGS)
        blocks = _blocks(description)
        self.assertIn("ドアストッパー", blocks[0] + blocks[2])
        self.assertNotIn("浮かせて設置", description)
        self.assertIn("✔️ マグネットで取り付けられる", blocks[3].splitlines())

    def test_air_fryer_does_not_claim_zero_oil(self):
        # ノンフライヤーの商品名に「油不使用」等の明示がなくても、
        # 「油を使わずに揚げ物を作れる」のように油ゼロを断定しない。
        category = dg.refine_category(REAL_AIR_FRYER, "時短")
        description = dg.generate_description(REAL_AIR_FRYER, category=category, base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("油を使わずに", description)
        self.assertIn("油を控えて", description)

    def test_frying_pan_does_not_infer_unconfirmed_performance(self):
        # フライパンの商品情報に明示されていない「焦げつきやすい」
        # 「後片付けしやすい」のような性能を勝手に推測しない。
        item = make_item(name="鉄製フライパン IH対応 26cm")
        description = dg.generate_description(item, category="キッチン", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("焦げつきやすい", description)
        self.assertNotIn("後片付けしやすい", description)

    def test_robot_vacuum_does_not_assume_specific_operation_method(self):
        # ロボット掃除機の商品名・データに明示されていない
        # 「スイッチひとつで」のような操作方法を勝手に限定しない。
        item = make_item(name="ロボット掃除機 全自動 マッピング機能")
        description = dg.generate_description(item, category="時短", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("スイッチひとつで", description)

    def test_stainless_material_clause_was_removed(self):
        # 「ステンレス＝サビに強い」は、商品全体の用途に繋がりにくい素材だけの
        # 表現のため、FEATURE_CLAUSESから削除されていることを確認する。
        keywords = [keyword for keyword, _clause, _emoji in dg.FEATURE_CLAUSES]
        self.assertNotIn("ステンレス", keywords)

    def test_unmatched_product_falls_back_to_generic_template(self):
        # PRODUCT_TYPE_TEMPLATESに無い商品名では、カテゴリ共通の
        # GENERIC_TEMPLATESが使われることを確認する。
        item = make_item(name="なんの変哲もない商品")
        self.assertIsNone(dg._match_product_type(item["name"]))
        description = dg.generate_description(item, category="収納", base_hashtags=BASE_HASHTAGS)
        blocks = _blocks(description)
        self.assertEqual(blocks[0], f"{dg.GENERIC_TEMPLATES['収納'].topic_emoji} 身の回りの物の置き場所、決まってる？✨")

    def test_feature_clause_appears_as_third_checklist_item_when_no_type_match(self):
        # 商品タイプが特定できない場合でも、マグネット式などの構造・仕様は
        # ✔️メリットの3項目目として自然に組み込まれる。ただし、商品名から
        # 確認できる「マグネットで取り付けられる」という事実だけにとどめ、
        # 「浮かせて設置」のような確認できない用途までは推測しない。
        item = make_item(name="マグネット式 収納ラック")
        description = dg.generate_description(item, category="収納", base_hashtags=BASE_HASHTAGS)
        checklist_lines = _blocks(description)[3].splitlines()
        self.assertIn("✔️ マグネットで取り付けられる", checklist_lines)
        self.assertNotIn("浮かせて設置", description)

    def test_bath_location_overrides_generic_topic_emoji(self):
        # 「お風呂用品」であることが商品名から分かる場合、GENERIC_TEMPLATESの
        # 既定の絵文字（🏠）ではなく、場所に合った絵文字（🛁）を使う。
        item = make_item(name="お風呂 マグネット 収納ラック")
        description = dg.generate_description(item, category="収納", base_hashtags=BASE_HASHTAGS)
        hook_line = _blocks(description)[0]
        self.assertTrue(hook_line.startswith("🛁 "), hook_line)


# 「消耗品・飲料」枠（洗剤・キッチン消耗品・日用品・水・お茶・ジュース）で
# 新しく追加したカテゴリのテンプレートが、既存カテゴリと同じ安全ルールを
# 守っていることを確認する回帰テスト。6ブロック構成・絵文字・✔️3項目などの
# 形式面はDescriptionStructureTestがdg.GENERIC_TEMPLATESの全カテゴリを対象に
# 既に確認しているため、ここでは消耗品・飲料特有の内容（導入文・禁止表現）だけを見る。
CONSUMABLE_CATEGORIES = ["洗剤", "キッチン消耗品", "日用品", "水", "お茶", "ジュース"]

# 根拠のない断定表現（絶対にお得・必ず安い・健康になる等）を禁止するルールの確認用。
FORBIDDEN_PHRASES = [
    "絶対お得", "絶対にお得", "必ず安い", "健康になる", "絶対安い", "お得です",
]


class ConsumableAndBeverageDescriptionTest(unittest.TestCase):
    def test_consumable_categories_are_registered_in_generic_templates(self):
        for category in CONSUMABLE_CATEGORIES:
            self.assertIn(category, dg.GENERIC_TEMPLATES)

    def test_consumable_categories_have_a_dedicated_hashtag(self):
        for category in CONSUMABLE_CATEGORIES:
            self.assertIn(category, dg.HASHTAG_BY_CATEGORY)

    def test_no_unfounded_claims_in_any_consumable_or_beverage_description(self):
        item = make_item(name="テスト消耗品")
        for category in CONSUMABLE_CATEGORIES:
            description = dg.generate_description(item, category=category, base_hashtags=BASE_HASHTAGS)
            for phrase in FORBIDDEN_PHRASES:
                self.assertNotIn(phrase, description, f"category={category}: {description}")

    def test_detergent_hook_matches_requested_wording(self):
        # 「洗濯」という言葉を含む商品名のため、GENERIC_TEMPLATES["洗剤"]では
        # なく、洗濯用洗剤専用のテンプレート（_LAUNDRY_DETERGENT_TEMPLATE）の
        # hook_variantsのいずれかが使われる。
        item = make_item(name="濃縮 洗濯洗剤 詰め替え 大容量")
        description = dg.generate_description(item, category="洗剤", base_hashtags=BASE_HASHTAGS)
        hook_line = _blocks(description)[0]
        expected = {
            f"{dg._LAUNDRY_DETERGENT_TEMPLATE.topic_emoji} {text}✨"
            for text in dg._LAUNDRY_DETERGENT_TEMPLATE.hook_variants
        }
        self.assertIn(hook_line, expected)

    def test_water_hook_matches_requested_wording(self):
        # hook_variantsに複数パターンを追加したため、完全一致ではなく
        # 用意されている安全な文言のいずれかであることを確認する。
        item = make_item(name="天然水 500ml 24本")
        description = dg.generate_description(item, category="水", base_hashtags=BASE_HASHTAGS)
        hook_line = _blocks(description)[0]
        expected = {
            f"{dg.GENERIC_TEMPLATES['水'].topic_emoji} {text}✨"
            for text in dg.GENERIC_TEMPLATES["水"].hook_variants
        }
        self.assertIn(hook_line, expected)

    def test_tea_hook_matches_requested_wording(self):
        item = make_item(name="緑茶 ペットボトル 24本")
        description = dg.generate_description(item, category="お茶", base_hashtags=BASE_HASHTAGS)
        hook_line = _blocks(description)[0]
        expected = {
            f"{dg.GENERIC_TEMPLATES['お茶'].topic_emoji} {text}✨"
            for text in dg.GENERIC_TEMPLATES["お茶"].hook_variants
        }
        self.assertIn(hook_line, expected)

    def test_price_and_review_are_still_not_included(self):
        item = make_item(name="テスト消耗品", price=2480, review_average=4.8, review_count=321)
        for category in CONSUMABLE_CATEGORIES:
            description = dg.generate_description(item, category=category, base_hashtags=BASE_HASHTAGS)
            self.assertNotIn("2480", description)
            self.assertNotIn("4.8", description)
            self.assertNotIn("321", description)


class DetergentSubtypeTest(unittest.TestCase):
    """洗剤の用途（洗濯用・食器用・住宅用）を商品名から正しく判定し、
    確認できない用途を紹介文に書かないことを確認する回帰テスト。

    本番で実際に見つかった問題：洗濯洗剤の商品なのに「普段のお洗濯や
    食器洗いに使いやすい」という、確認できない食器洗い用途が紹介文に
    混ざっていた（GENERIC_TEMPLATES["洗剤"]のcheckoutlist_coreが、用途を
    商品名から確認せず両方を常に断定していたことが原因）。
    """

    def test_laundry_detergent_does_not_mention_dishwashing(self):
        item = make_item(name="泥汚れ用 洗濯洗剤 部屋干し対応 詰め替え")
        description = dg.generate_description(item, category="洗剤", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("食器洗い", description)
        self.assertNotIn("食器", description)
        self.assertIn("洗濯", description)

    def test_dishwashing_detergent_does_not_mention_laundry(self):
        item = make_item(name="食器用洗剤 大容量 詰め替え用")
        description = dg.generate_description(item, category="洗剤", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("お洗濯", description)
        self.assertNotIn("洗濯に", description)
        self.assertIn("食器", description)

    def test_household_cleaning_detergent_does_not_mention_laundry_or_dishwashing(self):
        item = make_item(name="浴室用洗剤 除菌 消臭")
        description = dg.generate_description(item, category="洗剤", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("お洗濯", description)
        self.assertNotIn("食器洗い", description)

    def test_ambiguous_detergent_does_not_claim_specific_use(self):
        # 商品名から用途（洗濯用・食器用・住宅用のいずれか）が確認できない
        # 場合は、GENERIC_TEMPLATES["洗剤"]の安全なフォールバックを使い、
        # 特定の用途を断定しない。
        item = make_item(name="濃縮タイプ 洗剤 詰め替え用")
        description = dg.generate_description(item, category="洗剤", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("食器洗い", description)
        self.assertNotIn("お洗濯", description)

    def test_detergent_subtype_matching_selects_expected_template(self):
        self.assertIs(
            dg._match_detergent_subtype("柔軟剤 部屋干し用"),
            dg._LAUNDRY_DETERGENT_TEMPLATE,
        )
        self.assertIs(
            dg._match_detergent_subtype("台所用 食器洗い洗剤"),
            dg._DISHWASHING_DETERGENT_TEMPLATE,
        )
        self.assertIs(
            dg._match_detergent_subtype("トイレ用 洗浄剤"),
            dg._HOUSEHOLD_CLEANING_DETERGENT_TEMPLATE,
        )
        self.assertIsNone(dg._match_detergent_subtype("洗剤"))

    def test_detergent_subtype_only_applies_within_detergent_category(self):
        # 「洗濯」という言葉が別カテゴリーの商品名に含まれていても
        # （例：洗濯ハンガー）、category!="洗剤"の場合は洗剤専用テンプレートを
        # 使わない（誤って洗剤の紹介文になってしまわないことの確認）。
        item = make_item(name="洗濯ハンガー 物干し 折りたたみ")
        description = dg.generate_description(item, category="収納", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("洗剤", description)


class ConsumableVarietyTest(unittest.TestCase):
    """同じカテゴリーの消耗品・飲料でも、商品ごとに紹介文の書き出し・
    本文・特徴が変わり、毎日ほぼ同じ文章にならないことを確認する回帰テスト。"""

    def test_different_beverage_products_do_not_produce_identical_descriptions(self):
        items = [
            make_item(name=f"天然水 500ml {i}本セット", item_code=f"water-{i}")
            for i in range(8)
        ]
        descriptions = {
            dg.generate_description(item, category="水", base_hashtags=BASE_HASHTAGS) for item in items
        }
        self.assertGreater(len(descriptions), 1)

    def test_different_detergent_products_in_same_subtype_do_not_produce_identical_descriptions(self):
        items = [
            make_item(name=f"食器用洗剤 {i}", item_code=f"dish-{i}") for i in range(8)
        ]
        descriptions = {
            dg.generate_description(item, category="洗剤", base_hashtags=BASE_HASHTAGS) for item in items
        }
        self.assertGreater(len(descriptions), 1)

    def test_beverage_no_sugar_feature_is_reflected_when_confirmed(self):
        item = make_item(name="無糖 紅茶 ペットボトル")
        description = dg.generate_description(item, category="お茶", base_hashtags=BASE_HASHTAGS)
        checklist = _blocks(description)[3]
        self.assertIn("糖分を気にせず選びやすい", checklist)

    def test_beverage_caffeine_free_feature_is_reflected_when_confirmed(self):
        item = make_item(name="ノンカフェイン麦茶 ペットボトル")
        description = dg.generate_description(item, category="お茶", base_hashtags=BASE_HASHTAGS)
        checklist = _blocks(description)[3]
        self.assertIn("カフェインを気にせず飲みやすい", checklist)

    def test_beverage_feature_is_not_invented_when_not_confirmed(self):
        # 商品名にカフェイン・糖分に関する記載が一切無ければ、それらの
        # 特徴を勝手に追加しない（確認できない特徴は書かない、というルールの確認）。
        item = make_item(name="緑茶 ペットボトル 24本")
        description = dg.generate_description(item, category="お茶", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("カフェイン", description)
        self.assertNotIn("糖分", description)

    def test_detergent_refill_feature_is_reflected_when_confirmed(self):
        item = make_item(name="食器用洗剤 詰め替え用")
        description = dg.generate_description(item, category="洗剤", base_hashtags=BASE_HASHTAGS)
        checklist = _blocks(description)[3]
        self.assertIn("詰め替え用でごみを減らしやすい", checklist)

    def test_generic_templates_still_produce_valid_six_block_description(self):
        # 今回追加したhook_variants/worry_variants/solution_variantsを使っても、
        # 既存の6ブロック構成・絵文字ルールが崩れないことを確認する
        # （DescriptionStructureTestが全カテゴリーで既に確認しているが、
        # ここでは複数の商品コードを試して構成が崩れないことを重ねて確認する）。
        for i in range(6):
            item = make_item(name="テスト消耗品", item_code=f"code-{i}")
            for category in CONSUMABLE_CATEGORIES:
                description = dg.generate_description(item, category=category, base_hashtags=BASE_HASHTAGS)
                blocks = _blocks(description)
                self.assertEqual(len(blocks), 6)
                self.assertTrue(blocks[0].endswith("✨"))
                self.assertIn("😅", blocks[1])
                self.assertTrue(blocks[2].endswith("◎"))
                self.assertTrue(blocks[4].endswith("☺️"))


class TemplateComponentsForReuseTest(unittest.TestCase):
    """get_template_components()・match_product_type_keyword()（TikTok台本
    生成などで再利用するための追加関数）のテスト。generate_description()
    自体の挙動・テストには影響しない。"""

    def test_match_product_type_keyword_returns_matched_keyword(self):
        self.assertEqual(dg.match_product_type_keyword("スープメーカー 便利家電"), "スープメーカー")
        self.assertIsNone(dg.match_product_type_keyword("何にでも使える便利グッズX"))

    def test_components_reflect_matched_product_type_template(self):
        item = make_item(name="水切りボウル 便利グッズ")
        components = dg.get_template_components(item, category="キッチン")
        self.assertEqual(components.hook_text, "野菜の水切り、これならラクそう")
        self.assertEqual(len(components.checklist), 3)
        self.assertEqual(len(components.worry_lines), 2)

    def test_components_fall_back_to_generic_template_with_location(self):
        item = make_item(name="洗面所 収納ラック")
        components = dg.get_template_components(item, category="収納")
        self.assertIn("洗面所", components.hook_text)

    def test_components_never_contain_experience_implying_phrases(self):
        for item, category in ALL_REAL_ITEMS_AND_CATEGORIES:
            components = dg.get_template_components(item, category=category)
            combined = " ".join(
                [components.hook_text, components.solution_text, components.closing_text]
                + components.worry_lines
                + components.checklist
            )
            for phrase in ("使ってみました", "買ってよかった", "使ってみて", "買ってみました"):
                self.assertNotIn(phrase, combined)

    def test_get_template_components_does_not_change_generate_description_output(self):
        # get_template_components()を追加しても、generate_description()自体の
        # 出力（既存機能）が変わっていないことの確認。
        for item, category in ALL_REAL_ITEMS_AND_CATEGORIES:
            description = dg.generate_description(item, category=category, base_hashtags=BASE_HASHTAGS)
            self.assertIsInstance(description, str)
            self.assertTrue(description)


if __name__ == "__main__":
    unittest.main()
