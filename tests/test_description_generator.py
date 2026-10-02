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

# 2026-09-19の本番実行（room/data/candidates.json）で実際に取得された、
# 購入制限（お一人様1本限り）のある商品名。複数のテストクラスで使う。
GRAPE_JUICE_NAME = (
    "お1人様ご家族様1本限り！ドール グレープ　100％ 200ml※皆様、日頃お世話になって"
    "おります。申し訳ございませんが、一人でも多くの方に試しいただきたいと思いますので"
    "お一人様ご家族様1本まででお願いいたします。 【2sp_121217_red】"
)

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
        # 「ペット用品」は全ジャンル型のジャンルとして確認できているため、
        # 具体的な商品タイプが判定できない場合、旧来の汎用タグ
        # （base_hashtags・#便利グッズ）を機械的に付けず、カテゴリー別タグ
        # （#ペット用品）だけになる（description-genre-009対応。他の
        # カテゴリーは従来通り3〜5個のタグを維持する）。
        categories_with_minimum_one_tag = {"ペット用品"}
        for category in dg.GENERIC_TEMPLATES:
            description = dg.generate_description(item, category=category, base_hashtags=BASE_HASHTAGS)
            hashtag_line = _blocks(description)[5]
            hashtags = hashtag_line.split(" ")
            min_tags = 1 if category in categories_with_minimum_one_tag else 3
            self.assertGreaterEqual(len(hashtags), min_tags, f"category={category}: {hashtag_line}")
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
        self.assertIn("詰め替えタイプで使いやすい", checklist)
        # 「ごみを減らせる」等の確認できない環境効果は断定しない
        # （description-genre-004対応）。
        self.assertNotIn("ごみを減らし", checklist)

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


class Sept21BatchRegressionTest(unittest.TestCase):
    """2026-09-21に生成されたroom/data/candidates.jsonで実際に見つかった
    問題（description-match-002）の回帰テスト。商品名は本番で実際に
    取得された表記をそのまま使っている。"""

    SPONGE_NAME = (
        "最短翌日 ダスキンスポンジ 6個セット キッチン 台所用 抗菌 送料無料 プレゼント 母の日 "
        "だすきん ポイント消費 最安値 ハードタイプ 台所用スポンジ ダスキン スポンジ "
        "ポイント消化 送料無 ダスキンのスポンジ ダスキンスポンジ送料無料 3個入り "
        "ダスキン食器洗いスポンジ"
    )
    LIMESCALE_SHEET_NAME = (
        "【錫村商店公式】水垢落とし 研磨 シート 尿石 トイレ 洗面台 陶器【落ちない水垢に】"
        "水垢ペーパー 2枚入り｜洗剤不要でしっかり除去 プロ仕様"
    )
    RICE_COOKER_NAME = (
        "nikome ニコメ 一人暮らし 炊飯器 2合 少量 ミニ マルチライスクッカー 多機能炊飯器 "
        "コンパクト 小型 おしゃれ かわいい お弁当 簡単操作 ほったらかし調理 時短 調理 家電 "
        "便利 調理家電 新生活 ギフト プレゼント 時短家電 便利家電 電気調理器具"
    )
    BARLEY_TEA_NAME = (
        "国産 はとむぎ茶 6g×50包 （300g 大容量 ティーバッグ） ほんぢ園 ＜はと麦茶 100% "
        "ペットボトル よりお得！ ティーパック ハト麦茶 ハトムギ ノンカフェイン 【LC】＞ "
        "送料無料 ／セ／ ●"
    )

    # 1. 食器洗いスポンジに「使い捨て」と勝手に追加されない。
    def test_dish_sponge_does_not_claim_disposable(self):
        item = make_item(name=self.SPONGE_NAME)
        description = dg.generate_description(item, category="キッチン消耗品", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("使い捨て", description)
        self.assertIn("食器洗い", description)

    # 2. 水垢落とし研磨シートにティッシュ/トイレットペーパーの文章が出ない。
    def test_limescale_sheet_does_not_get_tissue_toilet_paper_wording(self):
        item = make_item(name=self.LIMESCALE_SHEET_NAME)
        description = dg.generate_description(item, category="日用品", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("ティッシュ", description)
        self.assertNotIn("トイレットペーパー", description)

    # 3. 水垢ペーパーに水垢掃除に関係する商品固有情報が反映される。
    def test_limescale_sheet_reflects_product_specific_info(self):
        item = make_item(name=self.LIMESCALE_SHEET_NAME)
        description = dg.generate_description(item, category="日用品", base_hashtags=BASE_HASHTAGS)
        self.assertIn("水垢", description)
        checklist = _blocks(description)[3]
        self.assertTrue(
            any(keyword in checklist for keyword in ("トイレ", "洗面台", "陶器", "洗剤を使わず")),
            checklist,
        )

    # 4. 2合炊飯器が一般的な時短家電文だけにならず、炊飯器の商品情報が反映される。
    def test_rice_cooker_does_not_fall_back_to_generic_time_saving_appliance(self):
        item = make_item(name=self.RICE_COOKER_NAME)
        description = dg.generate_description(item, category="時短", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("その家事、もっと時短できるかも", description)
        self.assertIn("炊飯", description)

    def test_rice_cooker_reflects_confirmed_feature(self):
        item = make_item(name=self.RICE_COOKER_NAME)
        description = dg.generate_description(item, category="時短", base_hashtags=BASE_HASHTAGS)
        checklist = _blocks(description)[3]
        self.assertTrue(
            any(keyword in checklist for keyword in ("一人暮らし", "ほったらかし")),
            checklist,
        )

    # 5. 6g×50包の商品について単純に「6gで使いやすい」だけにならない。
    def test_barley_tea_quantity_extraction_keeps_full_pack_info(self):
        phrase = dg._extract_quantity_phrase(self.BARLEY_TEA_NAME)
        self.assertEqual(phrase, "6g×50包")
        item = make_item(name=self.BARLEY_TEA_NAME)
        description = dg.generate_description(item, category="お茶", base_hashtags=BASE_HASHTAGS)
        checklist = _blocks(description)[3]
        self.assertIn("6g×50包", checklist)
        self.assertNotIn("✔️ 6gで使いやすい", checklist)

    # 6. 前回修正した洗濯洗剤→食器洗い誤用途が再発しない（回帰確認）。
    def test_laundry_detergent_still_does_not_mention_dishwashing_regression(self):
        item = make_item(name="【1種類を選べる】アタックZERO 洗濯洗剤 ワンハンド 本体(380g×4セット)")
        description = dg.generate_description(item, category="洗剤", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("食器洗い", description)
        self.assertIn("洗濯", description)

    # 7. 購入制限商品に「まとめ買い」が再発しない（回帰確認）。
    def test_purchase_limited_item_still_has_no_bulk_buying_phrase_regression(self):
        item = make_item(name=GRAPE_JUICE_NAME)
        description = dg.generate_description(item, category="ジュース", base_hashtags=BASE_HASHTAGS)
        for phrase in ("まとめ買い", "まとめて", "大量"):
            self.assertNotIn(phrase, description, description)


class Sept19BatchRegressionTest(unittest.TestCase):
    """2026-09-19に生成されたroom/data/candidates.jsonの10件で実際に
    見つかった問題（description-match-002）の回帰テスト。商品名は本番で
    実際に取得された表記をそのまま使っている。"""

    HANGER_NAME = (
        "極太PVCコーティング 滑らないハンガー 100本セット （軽くて丈夫！衣類が滑らず、"
        "かさばらないからクローゼットもスッキリの便利なハンガー） 10本単位で選べる16色 "
        "収納 洋服 和服 軽い 軽量 洗濯 外干し 部屋干し ステンレス ランドリー 上着 "
        "ジャケット コート スーツ"
    )
    CARDBOARD_STOCKER_NAME = (
        "持ち運びできる段ボールストッカー プラス 段ボールストッカー ダンボールストッカー "
        "段ボール 整理 束ねる まとめる ダンボール 持ちやすい 便利グッズ ひも通し 紐通し "
        "ゴミ リサイクル 収納 片付け ゴミ捨て 移動 持ち運び コジット メール便送料無料"
    )
    HAIR_IRON_POUCH_NAME = (
        "＼レビューで選べる特典あり／ ヘアアイロンポーチ ヘアアイロンケース カバー スリム "
        "ミニ 耐熱 38mm 対応 持ち運び 旅行 便利グッズ 熱いまま 吊り下げ ヘアアイロン収納 "
        "耐熱ポーチ 小さめ アイロンポーチ ヘアアイロン 収納 かわいい おしゃれ コテ"
    )
    BUTTER_CUTTER_NAME = (
        "leye オークス ワイヤーでスーッと切れるバターカッター LS1551 5gカット 200g 450g "
        "ステンレスカッター バター小分け 時短グッズ 製パン パン作り 製菓 お菓子作り ケーキ "
        "計量 おしゃれ 調理器具 キッチンツール 日本製"
    )
    STAIN_REMOVER_NAME = (
        "《20ml×2個セット》総合1位 衣類のしみ抜き剤『スポッとる』【送料無料】"
        "諦めていた服のシミが落ちる！クリーニング屋ふみさんの染み抜き剤"
    )
    LAUNDRY_DETERGENT_NAME = "【1種類を選べる】アタックZERO 洗濯洗剤 ワンハンド 本体(380g×4セット)【アタックZERO】"

    # 1. 滑らないハンガーの商品紹介に、商品固有の特徴が最低1つ以上反映される。
    def test_hanger_reflects_product_specific_feature(self):
        item = make_item(name=self.HANGER_NAME)
        description = dg.generate_description(item, category="収納", base_hashtags=BASE_HASHTAGS)
        self.assertIn("ハンガー", description)
        # カテゴリー共通の「身の回りの物の置き場所」に頼っていないことの確認。
        self.assertNotIn("身の回りの物の置き場所", description)
        checklist = _blocks(description)[3]
        self.assertTrue(
            any(keyword in checklist for keyword in ("滑り", "100本", "まとめて")),
            checklist,
        )

    # 2. 段ボールストッカーが「身の回りの物の収納」だけで終わらず、
    #    段ボール整理に関係する内容になる。
    def test_cardboard_stocker_is_about_cardboard_not_generic_storage(self):
        item = make_item(name=self.CARDBOARD_STOCKER_NAME)
        description = dg.generate_description(item, category="収納", base_hashtags=BASE_HASHTAGS)
        self.assertIn("段ボール", description)
        self.assertNotIn("身の回りの物の置き場所", description)
        self.assertNotIn("身の回りの物をすっきりまとめやすい", description)

    # 3. 耐熱ヘアアイロンポーチに、取得済み情報から確認できる特徴が反映される。
    def test_hair_iron_pouch_reflects_confirmed_features(self):
        item = make_item(name=self.HAIR_IRON_POUCH_NAME)
        description = dg.generate_description(item, category="収納", base_hashtags=BASE_HASHTAGS)
        self.assertTrue(
            any(keyword in description for keyword in ("ヘアアイロン", "耐熱")),
            description,
        )
        self.assertNotIn("身の回りの物の置き場所", description)

    # 4. バターカッターに、バターを切る用途と商品固有情報が反映される。
    def test_butter_cutter_reflects_use_and_product_specific_info(self):
        item = make_item(name=self.BUTTER_CUTTER_NAME)
        description = dg.generate_description(item, category="キッチン", base_hashtags=BASE_HASHTAGS)
        self.assertIn("バター", description)
        self.assertNotIn("毎日の料理や後片付け", description)
        checklist = _blocks(description)[3]
        self.assertTrue(
            any(keyword in checklist for keyword in ("5gカット", "計量")),
            checklist,
        )

    # 5. 衣類しみ抜き剤に、「毎日のように使う洗剤」など根拠のない使用頻度を
    #    追加しない。
    def test_stain_remover_does_not_claim_daily_use(self):
        item = make_item(name=self.STAIN_REMOVER_NAME)
        description = dg.generate_description(item, category="洗剤", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("毎日のように使う洗剤", description)
        self.assertNotIn("毎日", description)
        self.assertIn("シミ", description)

    # 6. 「お一人様1本まで」等の購入制限がある商品に、「まとめ買い」
    #    「まとめてストック」など矛盾する表現を生成しない（一般化された判定）。
    def test_purchase_limited_grape_juice_has_no_bulk_buying_phrase(self):
        item = make_item(name=GRAPE_JUICE_NAME)
        description = dg.generate_description(item, category="ジュース", base_hashtags=BASE_HASHTAGS)
        for phrase in ("まとめ買い", "まとめて", "大量"):
            self.assertNotIn(phrase, description, description)

    def test_purchase_limit_detection_is_generalized_not_hardcoded(self):
        # 今回の商品名だけの特別対応ではなく、購入制限を示す表現全般を
        # 検出できることを確認する（別カテゴリー・別の言い回しでも機能する）。
        self.assertTrue(dg._is_purchase_limited("お一人様1点まで 高級はちみつ 300g"))
        self.assertTrue(dg._is_purchase_limited("数量限定 プレミアム紅茶 100g"))
        self.assertTrue(dg._is_purchase_limited("3本まで 特選オリーブオイル"))
        self.assertFalse(dg._is_purchase_limited("お茶 ペットボトル 24本セット"))

    def test_purchase_limited_water_has_no_bulk_buying_phrase(self):
        # ジュース以外のカテゴリーでも同様に機能することの確認。
        item = make_item(name="お一人様1本限り 高級炭酸水 500ml")
        description = dg.generate_description(item, category="水", base_hashtags=BASE_HASHTAGS)
        for phrase in ("まとめ買い", "まとめて", "大量"):
            self.assertNotIn(phrase, description, description)

    def test_quantity_phrase_does_not_pick_up_purchase_limit_number(self):
        # 「1本限り」は商品の内容量ではないため、数量抽出（4項目目）に
        # 誤って使われず、実際の内容量（200ml）が使われることを確認する。
        phrase = dg._extract_quantity_phrase(GRAPE_JUICE_NAME)
        self.assertEqual(phrase, "200ml")

    # 8. 前回修正した洗濯用洗剤について、「食器洗い」が再発しない。
    def test_laundry_detergent_still_does_not_mention_dishwashing(self):
        item = make_item(name=self.LAUNDRY_DETERGENT_NAME)
        description = dg.generate_description(item, category="洗剤", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("食器洗い", description)
        self.assertIn("洗濯", description)

    # 9. 取得できない特徴を勝手に追加しない。
    def test_no_invented_features_for_products_without_confirmed_facts(self):
        # 商品名に容量・特徴語が一切無い場合、4項目目（数量由来）は追加されず、
        # 存在しない特徴も書かれない。
        item = make_item(name="なんの変哲もない収納ラック")
        description = dg.generate_description(item, category="収納", base_hashtags=BASE_HASHTAGS)
        checklist_lines = _blocks(description)[3].splitlines()
        self.assertEqual(len(checklist_lines), 3, checklist_lines)

    def test_no_invented_quantity_for_grape_juice_dishwashing_or_caffeine(self):
        item = make_item(name=GRAPE_JUICE_NAME)
        description = dg.generate_description(item, category="ジュース", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("カフェイン", description)
        self.assertNotIn("紙パック", description)


class BatchDiversityTest(unittest.TestCase):
    """generate_descriptions_for_batch()のテスト。同じバッチ内で
    ①キャッチコピー・⑤締めの一言が両方一致してしまう場合に、別パターンを
    選び直すことを確認する（■7・同一生成バッチ内の類似回避）。"""

    def test_batch_resolves_a_real_signature_collision_from_2026_09_19(self):
        # 2026-09-19の本番データ（room/data/candidates.json）で実際に、
        # からだにユーグレナ（いちごオレ）とドールグレープが同じ①⑤の組み合わせに
        # なっていた（個別生成の場合）。item_codeも実際の値をそのまま使う
        # （①⑤の組み合わせはitem_codeから決まる商品コードに依存するため）。
        item_a = make_item(
            name=(
                "からだにユーグレナ 旬摘みスッキリいちごオレ 24本 ユーグレナ ミドリムシ "
                "みどりむし ミドリむし 健康食品 健康飲料 栄養補助食品 栄養ドリンク "
                "野菜ジュース 男性 女性 ビタミン ミネラル アミノ酸 鉄 野菜 フルーツ 果物 "
                "鉄分 ドリンク 腸内環境 食物繊維 紙パック"
            ),
            item_code="midorimushishop:10000479",
        )
        item_b = make_item(
            name=GRAPE_JUICE_NAME,
            item_code="laitnature:10000872",
        )

        individual_a = dg.generate_description(item_a, category="ジュース", base_hashtags=BASE_HASHTAGS)
        individual_b = dg.generate_description(item_b, category="ジュース", base_hashtags=BASE_HASHTAGS)
        self.assertEqual(
            dg._description_shape_signature(individual_a),
            dg._description_shape_signature(individual_b),
            "このテストの前提（個別生成では衝突する）が崩れています",
        )

        batch_descriptions = dg.generate_descriptions_for_batch(
            [item_a, item_b], ["ジュース", "ジュース"], base_hashtags=BASE_HASHTAGS
        )
        signatures = {dg._description_shape_signature(d) for d in batch_descriptions}
        self.assertEqual(len(signatures), 2, batch_descriptions)

    def test_batch_never_crashes_and_returns_same_count_as_input(self):
        items = [make_item(name=f"テスト商品{i}", item_code=f"code-{i}") for i in range(12)]
        categories = ["収納"] * 12
        descriptions = dg.generate_descriptions_for_batch(items, categories, base_hashtags=BASE_HASHTAGS)
        self.assertEqual(len(descriptions), 12)
        for description in descriptions:
            self.assertIsInstance(description, str)
            self.assertTrue(description)

    def test_batch_does_not_change_output_when_no_collision(self):
        # 衝突が無い場合は、1件ずつgenerate_description()した場合と同じ結果になる。
        items = [
            make_item(name="水切りボウル 便利グッズ", item_code="a"),
            make_item(name="ロボット掃除機 全自動", item_code="b"),
        ]
        categories = ["キッチン", "時短"]
        batch_descriptions = dg.generate_descriptions_for_batch(items, categories, base_hashtags=BASE_HASHTAGS)
        individual_descriptions = [
            dg.generate_description(item, category=category, base_hashtags=BASE_HASHTAGS)
            for item, category in zip(items, categories)
        ]
        self.assertEqual(batch_descriptions, individual_descriptions)


# 同カテゴリーの商品を複数生成した場合でも、完全同一または商品名だけを
# 入れ替えたようなほぼ同一文章にならないことの確認（■7）。
class CategoryDiversityRegressionTest(unittest.TestCase):
    def test_multiple_storage_products_do_not_produce_near_identical_descriptions(self):
        names = [
            "極太PVCコーティング 滑らないハンガー 100本セット 収納 洗濯 部屋干し",
            "持ち運びできる段ボールストッカー 段ボール 整理 束ねる リサイクル",
            "耐熱 ヘアアイロンポーチ 38mm対応 旅行 吊り下げ",
        ]
        descriptions = [
            dg.generate_description(make_item(name=name), category="収納", base_hashtags=BASE_HASHTAGS)
            for name in names
        ]
        signatures = {dg._description_shape_signature(d) for d in descriptions}
        self.assertEqual(len(signatures), 3, descriptions)

        checklists = [_blocks(d)[3] for d in descriptions]
        self.assertEqual(len(set(checklists)), 3, checklists)


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


class ClassifyProductTypeTest(unittest.TestCase):
    """候補選定側の商品タイプ連投防止（src/ranking.py）が使うclassify_product_type()。

    紹介文生成で使っているPRODUCT_TYPE_TEMPLATES／match_product_type_keyword()を
    そのまま再利用し、判定ロジックが紹介文生成と候補選定でバラバラにならない
    ことを確認する。
    """

    def test_uses_the_specific_product_type_keyword_when_matched(self):
        self.assertEqual(
            dg.classify_product_type("ダスキン スポンジ 3個セット", "キッチン"), "スポンジ"
        )

    def test_generalizes_to_other_registered_keywords_too(self):
        self.assertEqual(
            dg.classify_product_type("折りたたみ 段ボールストッカー おしゃれ", "収納"),
            "段ボールストッカー",
        )

    def test_falls_back_to_the_given_category_when_no_keyword_matches(self):
        self.assertEqual(dg.classify_product_type("よくある収納ラック", "収納"), "収納")

    def test_falls_back_to_default_category_when_neither_is_available(self):
        self.assertEqual(dg.classify_product_type("何かの商品", ""), dg.DEFAULT_CATEGORY)

    def test_stays_consistent_with_match_product_type_keyword(self):
        for item, category in ALL_REAL_ITEMS_AND_CATEGORIES:
            product_name = item.get("name", "")
            expected = dg.match_product_type_keyword(product_name) or category
            self.assertEqual(dg.classify_product_type(product_name, category), expected)


class Sept22BatchRegressionTest(unittest.TestCase):
    """2026-09-22生成分のroom/data/candidates.jsonで実際に見つかった、
    「商品名の意味を取り違えた紹介文」の回帰テスト（description-fix-003）。
    商品名は本番で実際に取得された表記をそのまま使っている。"""

    CLEANER_STAND_NAME = (
        "tower《 山崎実業 コードレスクリーナースタンド タワー 》公式 白 黒 ダイソンスタンド dyson "
        "掃除機 スタンド V8slim V7slim V11 V10 V8 V7 V6 DC59 DC61 DC62 DC75 コードレス "
        "スティッククリーナースタンド 収納 おしゃれ 3540 3541 YAMAZAKI"
    )
    BOWL_COLANDER_NAME = (
        "【レビューでプレゼント有り】ボルコラ ボール・コランダー セット ザル ボウル セット 耐熱 "
        "リベラリスタ キッチン ざる プラスチック ふた付き フタ付き 温野菜 電子レンジ対応 "
        "食洗機対応 時短 調理器具 便利 リスオンラインショップ"
    )
    RANGE_HOOD_FILTER_NAME = (
        "＼全品ポイント2倍／【楽天総合1位】 スターフィルター 換気扇フィルター レンジフードフィルター "
        "レンジフィルターカバー スターターセット 枠2枚+フィルター4枚 シロッコファン 不燃性ガラス "
        "繊維タイプ 新居 新築 一人暮らし 節約 便利グッズ 新生活 引っ越"
    )
    KAWANE_TEA_NAME = (
        "JAS有機栽培 川根茶ブランド 粉末茶 10秒簡単！500mlペットボトル茶50本分が作れる "
        "お茶 個包装0.8g×50"
    )
    DISHWASHER_DETERGENT_NAME = (
        "ランキング1位！3冠達成！【送料無料】finish ビッグパック 大容量 150個入り "
        "フィニッシュ　タブレット 食洗機用洗剤 パワーキューブ ビッグパック 食器洗い機用洗剤 "
        "キッチン用洗剤 　食洗機用洗剤　 食器洗浄機用　洗剤　食器洗い機用 "
        "5g × 150粒 750g 台所用合成洗剤"
    )
    TOILET_TANK_CLEANER_NAME = "【木村石鹸 公式】C SERIES トイレタンクの洗浄剤　つけおき 除菌"

    # 1. コードレスクリーナースタンドを掃除機本体として紹介しない。
    def test_cleaner_stand_is_not_introduced_as_the_vacuum_itself(self):
        item = make_item(name=self.CLEANER_STAND_NAME)
        description = dg.generate_description(item, category="掃除", base_hashtags=BASE_HASHTAGS)
        self.assertIn("スタンド", description)
        self.assertIn("収納", description)

    # 2. クリーナースタンドに「汚れのお手入れ」が出ない（掃除機本体向けの文言が混ざらない）。
    def test_cleaner_stand_does_not_get_stain_care_wording(self):
        item = make_item(name=self.CLEANER_STAND_NAME)
        description = dg.generate_description(item, category="掃除", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("汚れ", description)
        self.assertNotIn("その汚れ、気になってませんか", description)

    # 3. ボール/コランダーのフタから「ホコリ防止」を推測しない。
    def test_lidded_bowl_set_does_not_claim_dust_prevention(self):
        item = make_item(name=self.BOWL_COLANDER_NAME)
        description = dg.generate_description(item, category="キッチン", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("ホコリ", description)

    def test_lid_feature_clause_states_fact_only(self):
        # フタ付き・蓋付き自体はFEATURE_CLAUSESとして残すが、確認できない
        # 目的（ホコリを防ぐ）までは主張しない安全な言い回しにする。
        self.assertEqual(dg._top_feature_clause("フタ付き 収納ケース", "収納"), ("フタ付きで使いやすい", "📦"))

    # 4. レンジフードフィルターを一般キッチングッズだけで紹介しない。
    def test_range_hood_filter_is_not_only_generic_kitchen_goods(self):
        item = make_item(name=self.RANGE_HOOD_FILTER_NAME)
        description = dg.generate_description(item, category="キッチン", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("毎日の料理や後片付け、地味に手間じゃない", description)
        self.assertIn("換気扇", description)
        self.assertIn("フィルター", description)

    # 「一人暮らし」は広告用の対象者向けキーワードであり、商品本体の
    # 特徴として優先して採用しない（FEATURE_CLAUSESから削除済み）。
    def test_range_hood_filter_does_not_feature_target_audience_marketing_words(self):
        item = make_item(name=self.RANGE_HOOD_FILTER_NAME)
        description = dg.generate_description(item, category="キッチン", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("一人暮らし向けで使いやすい", description)

    def test_holder_combined_quantity_is_kept_as_one_coherent_phrase(self):
        # 「枠2枚+フィルター4枚」を分割して片方の数字だけを拾わない。
        phrase = dg._extract_quantity_phrase(self.RANGE_HOOD_FILTER_NAME)
        self.assertEqual(phrase, "枠2枚+フィルター4枚")

    # 5. 「50本分」を「50本入り」と誤認しない。
    def test_tea_bags_per_bottle_yield_is_not_mistaken_for_pack_count(self):
        description_source_phrase = dg._extract_quantity_phrase(self.KAWANE_TEA_NAME)
        self.assertNotEqual(description_source_phrase, "50本")
        item = make_item(name=self.KAWANE_TEA_NAME)
        description = dg.generate_description(item, category="お茶", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("50本で使いやすい", description)

    # 6. 0.8g×50等の数量表現を意味を保って扱う。
    def test_individually_packaged_quantity_keeps_its_meaning(self):
        phrase = dg._extract_quantity_phrase(self.KAWANE_TEA_NAME)
        self.assertEqual(phrase, "0.8g×50")

    # 7. 食洗機用洗剤を一般的な手洗い用洗剤として紹介しない。
    def test_dishwasher_detergent_is_not_introduced_as_hand_washing_detergent(self):
        item = make_item(name=self.DISHWASHER_DETERGENT_NAME)
        description = dg.generate_description(item, category="洗剤", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("普段の食器洗いに使いやすい", description)
        self.assertIn("食洗機", description)

    def test_dishwasher_detergent_subtype_matching_selects_expected_template(self):
        self.assertIs(
            dg._match_detergent_subtype(self.DISHWASHER_DETERGENT_NAME),
            dg._DISHWASHER_DETERGENT_TEMPLATE,
        )
        # 手洗い用の「食器用洗剤」は、これまでどおり食洗機用とは別テンプレート。
        self.assertIs(
            dg._match_detergent_subtype("食器用洗剤 大容量 詰め替え用"),
            dg._DISHWASHING_DETERGENT_TEMPLATE,
        )

    # 8. トイレタンク洗浄剤を一般日用品だけで紹介しない。
    def test_toilet_tank_cleaner_is_not_only_generic_daily_goods(self):
        item = make_item(name=self.TOILET_TANK_CLEANER_NAME)
        description = dg.generate_description(item, category="日用品", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("切らすと地味に困る日用品", description)
        self.assertIn("トイレタンク", description)
        self.assertIn("つけおき", description)

    # 9. 以前修正した洗濯洗剤→食器洗い誤用途が再発しない（回帰確認）。
    def test_laundry_detergent_still_does_not_mention_dishwashing_regression(self):
        item = make_item(name="【1種類を選べる】アタックZERO 洗濯洗剤 ワンハンド 本体(380g×4セット)")
        description = dg.generate_description(item, category="洗剤", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("食器洗い", description)
        self.assertIn("洗濯", description)

    # 10. 購入制限商品→まとめ買い誤表現が再発しない（回帰確認）。
    def test_purchase_limited_item_still_has_no_bulk_buying_phrase_regression(self):
        item = make_item(name=GRAPE_JUICE_NAME)
        description = dg.generate_description(item, category="ジュース", base_hashtags=BASE_HASHTAGS)
        for phrase in ("まとめ買い", "まとめて", "大量"):
            self.assertNotIn(phrase, description, description)

    def test_one_person_household_removed_from_feature_clauses(self):
        # 「一人暮らし」は商品本体の構造・仕様ではなく広告用の対象者向け
        # キーワードのため、FEATURE_CLAUSESから削除されていることを確認する。
        keywords = [keyword for keyword, _clause, _emoji in dg.FEATURE_CLAUSES]
        self.assertNotIn("一人暮らし", keywords)


class Sept23BatchRegressionTest(unittest.TestCase):
    """2026-09-23生成分のroom/data/candidates.jsonで実際に見つかった、
    「カテゴリーから具体的な用途を断定してしまう」問題の回帰テスト
    （description-fix-004）。商品名は本番で実際に取得された表記をそのまま使っている。"""

    HEAT_PLATE_NAME = (
        "マイクロウェーブヒートプレートライト | 焼き魚がレンジで数分 マイクロウェーブヒートシリーズ "
        "マイクロウェーブヒート レンジで焼き魚 レンジ調理 電子レンジ で焼き魚 電子レンジ調理 "
        "調理器具 時短 便利 電子レンジ魚調理"
    )
    GRATER_NAME = (
        "下村工業 プログレード 軽くおろせるやさしいおろし器 大根おろし おろし器 おろし金 卸金 "
        "時短グッズ 燕三条 日本製 PG-668【送料無料】"
    )
    PET_DRYER_STAND_NAME = (
        "ドライヤースタンド ペット用 犬 猫 フリーハンド ハンズフリー ヘアドライヤー 両手が空く "
        "ペットの毛の乾燥も簡単便利。 ドライヤーホルダー 固定 犬 クリップ 時短グッズ シンプル "
        "置型 黒 固定機 アーム 伸縮 簡単 使いやすい ヘアケア 便利グッズ 犬 猫"
    )
    A2CARE_NAME = (
        "A2Care 除菌 消臭スプレー 300ml ANA 採用 感染対策 日本製 MA-T アルコールフリー 赤ちゃん "
        "ペット 無香料 部屋 車内 玄関 ゴミ箱 トイレ 衣類 猫 タバコ 生乾き臭 カビ対策 消臭 消臭剤 "
        "無臭空間 ノンアルコール ウイルス 花粉"
    )
    WASHING_MACHINE_TUB_CLEANER_NAME = (
        "★【 洗濯槽快×10個セット 業務用箱なし 専用新ネット1枚付 】 カビ防止 除菌 消臭 部屋干し 梅雨 "
        "洗濯槽クリーナー 洗濯槽 洗濯槽洗剤 洗濯機 洗たく槽 洗濯爽快 掃除 洗濯槽クリーニング "
        "ホタテ 帆立 貝殻"
    )

    # 1. ヒートプレートを家電と判定しない。
    def test_heat_plate_is_not_judged_as_an_appliance(self):
        item = make_item(name=self.HEAT_PLATE_NAME)
        description = dg.generate_description(item, category="時短", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("時短家電", description)
        self.assertNotIn("家電", description)

    # 2. 「電子レンジで使用」から電子レンジ本体と誤認しない。
    def test_heat_plate_is_not_mistaken_for_the_microwave_itself(self):
        item = make_item(name=self.HEAT_PLATE_NAME)
        description = dg.generate_description(item, category="時短", base_hashtags=BASE_HASHTAGS)
        self.assertIn("電子レンジで", description)
        self.assertIn("ヒートプレート", description)
        # 「電子レンジ」で調理する器具であって、電子レンジ本体を紹介しているのではない。
        self.assertNotIn("そんな家事の時間を短くしてくれそうな時短家電", description)

    # 3. 手動おろし器を時短家電と判定しない。
    def test_manual_grater_is_not_judged_as_a_time_saving_appliance(self):
        item = make_item(name=self.GRATER_NAME)
        description = dg.generate_description(item, category="時短", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("時短家電", description)
        self.assertNotIn("家電", description)
        self.assertIn("おろし", description)

    # 4. おろし器に「家事をおまかせ」が出ない。
    def test_manual_grater_does_not_get_hands_off_automation_wording(self):
        item = make_item(name=self.GRATER_NAME)
        description = dg.generate_description(item, category="時短", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("おまかせ", description)

    # 5. ペット用ドライヤースタンドを収納用品と誤認しない。
    def test_pet_dryer_stand_is_not_mistaken_for_a_storage_item(self):
        item = make_item(name=self.PET_DRYER_STAND_NAME)
        description = dg.generate_description(item, category="時短", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("まとめて収納できるスタンド", description)
        self.assertNotIn("ヘアーアイロンもまとめて整理できる", description)

    # 6. ハンズフリー/固定用途を反映する。
    def test_pet_dryer_stand_reflects_hands_free_fixed_use(self):
        item = make_item(name=self.PET_DRYER_STAND_NAME)
        description = dg.generate_description(item, category="時短", base_hashtags=BASE_HASHTAGS)
        self.assertTrue(
            any(keyword in description for keyword in ("ハンズフリー", "固定")),
            description,
        )

    def test_dryer_stand_without_hands_free_context_still_uses_storage_template(self):
        # 文脈語（ハンズフリー・固定等）が無い、従来通りの収納用ドライヤー
        # スタンドは、これまでどおり収納用テンプレートのままであることを確認する
        # （上書きが過剰適用されて既存の挙動を壊していないことの確認）。
        item = make_item(name="山崎実業 tower ドライヤースタンド 洗面所 収納 おしゃれ")
        description = dg.generate_description(item, category="収納", base_hashtags=BASE_HASHTAGS)
        self.assertIn("まとめて収納できるスタンド", description)

    # 7. 洗濯槽クリーナーを衣類用洗濯洗剤として紹介しない。
    def test_washing_machine_tub_cleaner_is_not_introduced_as_laundry_detergent(self):
        item = make_item(name=self.WASHING_MACHINE_TUB_CLEANER_NAME)
        description = dg.generate_description(item, category="洗剤", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("毎日のお洗濯に使いやすい", description)
        self.assertNotIn("普段のお洗濯に使いやすい", description)
        self.assertIn("洗濯槽", description)

    def test_washing_machine_tub_cleaner_subtype_matching_selects_expected_template(self):
        self.assertIs(
            dg._match_detergent_subtype(self.WASHING_MACHINE_TUB_CLEANER_NAME),
            dg._WASHING_MACHINE_TUB_CLEANER_TEMPLATE,
        )
        # 通常の衣類用洗濯洗剤は、これまでどおり別テンプレート。
        self.assertIs(
            dg._match_detergent_subtype("泥汚れ用 洗濯洗剤 部屋干し対応"),
            dg._LAUNDRY_DETERGENT_TEMPLATE,
        )

    # 8. A2Careをキッチン専用品として紹介しない。
    def test_multi_purpose_spray_is_not_introduced_as_kitchen_only(self):
        item = make_item(name=self.A2CARE_NAME)
        description = dg.generate_description(item, category="キッチン消耗品", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("毎日のキッチン作業に使いやすい", description)
        self.assertNotIn("キッチン専用", description)

    # 9. カテゴリーだけでは具体用途を断定しない（商品名がPRODUCT_TYPE_TEMPLATES・
    #    DETERGENT_SUBTYPE_TEMPLATESのどれにも一致しない、未知の商品タイプの場合）。
    def test_unmatched_product_in_time_saving_category_does_not_assume_appliance(self):
        item = make_item(name="なんの変哲もない暮らしの道具")
        self.assertIsNone(dg._match_product_type(item["name"]))
        description = dg.generate_description(item, category="時短", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("家電", description)
        self.assertNotIn("おまかせ", description)

    def test_unmatched_product_in_kitchen_supply_category_does_not_assume_kitchen_task(self):
        item = make_item(name="なんの変哲もない暮らしの道具")
        self.assertIsNone(dg._match_product_type(item["name"]))
        description = dg.generate_description(item, category="キッチン消耗品", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("毎日のキッチン作業に使いやすい", description)

    # 10. 未知の商品タイプでもカテゴリー由来の誤用途を生成しない
    #     （GENERIC_TEMPLATES自体に、断定的な言い回しが残っていないことの確認）。
    def test_generic_time_saving_template_does_not_assume_appliance_or_automation(self):
        template = dg.GENERIC_TEMPLATES["時短"]
        forbidden = ("時短家電", "家電", "おまかせ")
        texts = [template.hook_text, template.solution_text, template.checklist_fallback]
        texts += template.checklist_core
        for text in texts:
            for phrase in forbidden:
                self.assertNotIn(phrase, text, text)

    def test_generic_kitchen_supply_template_does_not_assume_kitchen_task(self):
        template = dg.GENERIC_TEMPLATES["キッチン消耗品"]
        self.assertNotIn("毎日のキッチン作業に使いやすい", template.checklist_core)
        for variant in template.solution_variants:
            self.assertNotIn("キッチン作業に使いやすそう", variant)


class Sept25BatchRegressionTest(unittest.TestCase):
    """2026-09-25生成分のroom/data/candidates.jsonで実際に見つかった、
    全ジャンル型移行後の紹介文誤分類の回帰テスト（description-genre-002）。
    商品名は本番で実際に取得された表記をそのまま使っている。"""

    NAME_STAMP_NAME = (
        "【 期間限定 送料無料 】 おなまえBOX ★ お名前スタンプ 安心のレビュー4.5万超 ひらがな 漢字 "
        "ローマ字 スーパーセット アイロン不要油性スタンプ台 選べる付属品 フォント 入園準備 入学 布 "
        "タグ おむつスタンプ 出産祝い おなまえスタンプ 子ども 保育園 名前スタンプ"
    )
    AROMA_OIL_NAME = (
        "アロマオイル AEAJ認定 40種から選べる6本 各5ml 精油 返品保証付 送料無料 100%ピュア "
        "エッセンシャルオイル セット アロマ 加湿器 オーガニック お試し ラベンダー オレンジ 天然"
    )
    DIAPER_CAKE_NAME = (
        "おむつケーキ 男の子 女の子 ギフト 名入れ 出産祝い サッシー Sassy 知育玩具 3段 マンスリー"
        "カード タオル おもちゃ ケーキオムツ 赤ちゃん ベビー 可愛い 誕生日 ループタオル フェイス"
        "タオル 歯がため 月齢カード 成長記録 ベビーアルテ"
    )
    FOLDING_PARASOL_NAME = (
        "【クーポン利用で最安2178円・酸化チタンシリーズ】「年間ランキング受賞」「楽天1位」"
        "＼Radi-Cool素材使用／日傘 折りたたみ 形状記憶 完全遮光 自動開閉 傘 超軽量 わずか210g "
        "折りたたみ傘 ワンタッチ 自動開閉 遮熱 晴雨兼用 遮光率100% UVカット 撥水加工 親骨 6本骨"
    )
    MENS_PARASOL_NAME = (
        "日傘 折りたたみ メンズ 遮熱 晴雨兼用 大きい 60cm 遮光率100％ UVカット率100% 紫外線対策 "
        "熱中症対策 通勤 通学 スポーツ観戦 アウトドア 男の日傘 大きめ おすすめ 人気 丈夫 軽量 "
        "3つ折 手動開閉 シンプル 無地 涼しい ひんやり傘 リーベン 0804"
    )
    ULTRASONIC_HUMIDIFIER_NAME = (
        "[6%クーポン] 加湿器 超音波加湿器 次亜塩素酸水対応 タワー型 おしゃれ 卓上加湿器 超音波式加湿器 "
        "アロマ加湿器 卓上 オフィス 大容量 小型 コンパクト 自動停止機能 LEDライト付き 静音 省エネ "
        "節電 エコ"
    )
    RETORT_CURRY_NAME = (
        "カレー レトルトカレー 五島軒 公式 函館・五島軒の極上ほぐし肉カレー4食セット 1日100セット"
        "限定 送料無料 ネコポス便 お試し"
    )
    RAMEN_NAME = (
        "＼5年連続受賞！比内地鶏ラーメン！／1日3万食完売 楽天1位 グルメ大賞 金賞 秋田比内地鶏ラーメン "
        "乾麺 6食 麺・スープ付 トッピング無 あっさり 塩ラーメン 塩味 具無し ダイエット カロリー"
        "控えめ 夜食 送料無料 秋田 林泉堂"
    )
    FACE_ROLLER_NAME = (
        "【楽天1位★無料ラッピング】美顔ローラー 美顔器 リフトアップ 【微弱電流】【防水仕様】"
        "【充電不要】 小顔ローラー 美顔ローラー メンズ マイクロカレント 美顔器 ローラー 全身用 "
        "ローラー 美容グッズ 美容 グッズ 氷ローラー 女性 男性 誕生日 敬老の日 母の日 誕生日"
    )
    HYBRID_HUMIDIFIER_NAME = (
        "[早期割り10%クーポン] [1年保証] 加湿器 ハイブリッド加湿器 2WAY タワー型 スリム おしゃれ "
        "ハイブリッド式加湿器 アロマ加湿器 卓上 オフィス 大容量 リモコン付き 業務用 自動停止機能 "
        "ダウンライト付き 静音 省エネ 節電 エコ"
    )

    # 1. お名前スタンプを汎用生活用品だけで紹介しない。
    def test_name_stamp_is_not_only_generic_life_goods(self):
        item = make_item(name=self.NAME_STAMP_NAME)
        description = dg.generate_description(item, category="ベビー用品", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("そんな暮らしの小さな不便を解消してくれそうな便利グッズ", description)
        self.assertIn("お名前スタンプ", description)
        self.assertTrue(any(k in description for k in ("ひらがな", "漢字", "ローマ字", "布", "タグ", "おむつ")))

    # 2. アロマオイルを家電として紹介しない。
    def test_aroma_oil_is_not_introduced_as_a_home_appliance(self):
        item = make_item(name=self.AROMA_OIL_NAME)
        description = dg.generate_description(item, category="家電", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("そんな暮らしの小さな不便を解消してくれそうな便利グッズ", description)
        self.assertIn("アロマオイル", description)
        self.assertNotIn("#家電", description)

    def test_aroma_oil_does_not_claim_health_or_therapeutic_effects(self):
        item = make_item(name=self.AROMA_OIL_NAME)
        description = dg.generate_description(item, category="家電", base_hashtags=BASE_HASHTAGS)
        for phrase in ("リラックス効果", "治療", "改善", "健康になる"):
            self.assertNotIn(phrase, description)

    # 3. おむつケーキを一般生活用品として紹介しない。
    def test_diaper_cake_is_not_introduced_as_generic_life_goods(self):
        item = make_item(name=self.DIAPER_CAKE_NAME)
        description = dg.generate_description(item, category="ベビー用品", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("そんな暮らしの小さな不便を解消してくれそうな便利グッズ", description)
        self.assertIn("出産祝い", description)
        self.assertIn("おむつケーキ", description)

    # 4. 日傘を日傘として認識する。
    def test_folding_parasol_is_recognized_as_a_parasol(self):
        item = make_item(name=self.FOLDING_PARASOL_NAME)
        description = dg.generate_description(item, category="ファッション", base_hashtags=BASE_HASHTAGS)
        self.assertIn("日傘", description)
        self.assertNotIn("暮らしの中の小さな「困った」", description)

    def test_mens_parasol_is_recognized_as_a_parasol(self):
        item = make_item(name=self.MENS_PARASOL_NAME)
        description = dg.generate_description(item, category="ファッション", base_hashtags=BASE_HASHTAGS)
        self.assertIn("日傘", description)

    # 5. 「6本骨」を6個の商品数量として扱わない。
    def test_umbrella_rib_count_is_not_mistaken_for_product_quantity(self):
        phrase = dg._extract_quantity_phrase(self.FOLDING_PARASOL_NAME)
        self.assertNotEqual(phrase, "6本")
        item = make_item(name=self.FOLDING_PARASOL_NAME)
        description = dg.generate_description(item, category="ファッション", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("6本で使いやすい", description)

    # 6. 超音波加湿器を加湿器として認識する。
    def test_ultrasonic_humidifier_is_recognized_as_a_humidifier(self):
        item = make_item(name=self.ULTRASONIC_HUMIDIFIER_NAME)
        description = dg.generate_description(item, category="家電", base_hashtags=BASE_HASHTAGS)
        self.assertIn("加湿器", description)
        self.assertIn("加湿", description)

    # 7. レトルトカレーを食品として紹介する。
    def test_retort_curry_is_introduced_as_food(self):
        item = make_item(name=self.RETORT_CURRY_NAME)
        description = dg.generate_description(item, category="食品", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("そんな暮らしの小さな不便を解消してくれそうな便利グッズ", description)
        self.assertIn("レトルトカレー", description)

    # 8. ラーメンを食品として紹介する。
    def test_ramen_is_introduced_as_food(self):
        item = make_item(name=self.RAMEN_NAME)
        description = dg.generate_description(item, category="食品", base_hashtags=BASE_HASHTAGS)
        self.assertIn("ラーメン", description)
        # タイトルの「ダイエット」「カロリー控えめ」を健康効果として拡大解釈しない。
        self.assertNotIn("ダイエット", description)
        self.assertNotIn("痩せ", description)

    def test_ramen_quantity_and_curry_quantity_are_not_confused(self):
        self.assertEqual(dg._extract_quantity_phrase(self.RETORT_CURRY_NAME), "4食")
        self.assertEqual(dg._extract_quantity_phrase(self.RAMEN_NAME), "6食")

    # 9. 美顔ローラーを美容用品として紹介する。
    def test_face_roller_is_introduced_as_a_beauty_item(self):
        item = make_item(name=self.FACE_ROLLER_NAME)
        description = dg.generate_description(item, category="美容", base_hashtags=BASE_HASHTAGS)
        self.assertIn("美顔ローラー", description)

    # 10. 美容効果を勝手に断定しない。
    def test_face_roller_does_not_claim_beauty_effects(self):
        item = make_item(name=self.FACE_ROLLER_NAME)
        description = dg.generate_description(item, category="美容", base_hashtags=BASE_HASHTAGS)
        for phrase in ("小顔になる", "リフトアップする", "若返る", "むくみが取れる", "小顔効果"):
            self.assertNotIn(phrase, description)

    # 11. ハイブリッド加湿器をリモコン収納用品として誤認しない。
    def test_hybrid_humidifier_is_not_mistaken_for_a_remote_control_organizer(self):
        item = make_item(name=self.HYBRID_HUMIDIFIER_NAME)
        description = dg.generate_description(item, category="生活雑貨", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("リモコンの置き場所", description)
        self.assertNotIn("収納ラック", description)
        self.assertIn("加湿器", description)

    # 12. 「リモコン付き」は本体判定より低い優先度になる。
    def test_remote_control_mention_does_not_override_the_actual_product(self):
        # 「リモコン付き」は加湿器という商品本体の付属品としての言及であり、
        # 「リモコン」というキーワードにマッチしても、それを商品本体とは
        # 判定しない（加湿器の商品タイプが優先される）。
        self.assertEqual(dg.match_product_type_keyword("リモコン付き ハイブリッド加湿器"), "加湿器")
        self.assertEqual(dg.match_product_type_keyword("リモコン付き 加湿器 卓上"), "加湿器")
        # 商品本体がリモコンそのもの（付属品としての言及ではない）の場合は、
        # 従来どおりリモコン向けテンプレートのまま。
        self.assertEqual(dg.match_product_type_keyword("リモコン 収納ラック おしゃれ"), "リモコン")

    # 13. 4食/6食/6本骨/60cm/210gの意味を混同しない。
    def test_quantity_units_are_not_confused_across_items(self):
        self.assertEqual(dg._extract_quantity_phrase(self.RETORT_CURRY_NAME), "4食")
        self.assertEqual(dg._extract_quantity_phrase(self.RAMEN_NAME), "6食")
        self.assertEqual(dg._extract_quantity_phrase(self.FOLDING_PARASOL_NAME), "210g")
        self.assertEqual(dg._extract_quantity_phrase(self.MENS_PARASOL_NAME), "60cm")
        self.assertEqual(dg._extract_quantity_phrase(self.AROMA_OIL_NAME), "6本")

    def test_hashtags_reflect_actual_product_type_not_mismatched_category(self):
        # 検索元カテゴリーが実際の商品ジャンルと矛盾する場合、ハッシュタグも
        # 本体の商品タイプを優先する（アロマオイルが「家電」カテゴリーでも
        # #家電にはならない）。
        item = make_item(name=self.AROMA_OIL_NAME)
        description = dg.generate_description(item, category="家電", base_hashtags=BASE_HASHTAGS)
        hashtag_line = description.split("\n\n")[-1]
        self.assertNotIn("#家電", hashtag_line)
        self.assertIn("#アロマ", hashtag_line)

    def test_all_ten_items_are_understandable_from_the_description_alone(self):
        # 「何の商品か読めば分かる」ことの最低限の確認：各商品を特徴づける
        # 語が紹介文本文に含まれていることを確認する。
        expectations = {
            self.NAME_STAMP_NAME: "お名前スタンプ",
            self.AROMA_OIL_NAME: "アロマオイル",
            self.DIAPER_CAKE_NAME: "おむつケーキ",
            self.FOLDING_PARASOL_NAME: "日傘",
            self.MENS_PARASOL_NAME: "日傘",
            self.ULTRASONIC_HUMIDIFIER_NAME: "加湿器",
            self.RETORT_CURRY_NAME: "レトルトカレー",
            self.RAMEN_NAME: "ラーメン",
            self.FACE_ROLLER_NAME: "美顔ローラー",
            self.HYBRID_HUMIDIFIER_NAME: "加湿器",
        }
        for name, expected_keyword in expectations.items():
            item = make_item(name=name)
            description = dg.generate_description(item, category="暮らし全般", base_hashtags=BASE_HASHTAGS)
            self.assertIn(expected_keyword, description, description)
            self.assertLessEqual(len(description), 500)


class DescriptionGenre003RegressionTest(unittest.TestCase):
    """2026-09-25 15:48生成分の最終調整（description-genre-003）の回帰テスト。

    ①数字＋「で使いやすい」という画一的な言い回しの改善（単位や周辺語から
    個数・重量・サイズの意味を保持する）、②具体的な商品タイプが判定できた
    商品には#暮らしの便利グッズ・#便利グッズを機械的に付けない、③ラーメンの
    未確認表現（「お店の味」）の削除、の3点を確認する。商品名は
    Sept25BatchRegressionTestと同じ、本番で実際に取得された表記を再利用する。
    """

    AROMA_OIL_NAME = Sept25BatchRegressionTest.AROMA_OIL_NAME
    FOLDING_PARASOL_NAME = Sept25BatchRegressionTest.FOLDING_PARASOL_NAME
    MENS_PARASOL_NAME = Sept25BatchRegressionTest.MENS_PARASOL_NAME
    RETORT_CURRY_NAME = Sept25BatchRegressionTest.RETORT_CURRY_NAME
    RAMEN_NAME = Sept25BatchRegressionTest.RAMEN_NAME
    FACE_ROLLER_NAME = Sept25BatchRegressionTest.FACE_ROLLER_NAME
    DIAPER_CAKE_NAME = Sept25BatchRegressionTest.DIAPER_CAKE_NAME
    HYBRID_HUMIDIFIER_NAME = Sept25BatchRegressionTest.HYBRID_HUMIDIFIER_NAME

    # 1.「6本で使いやすい」を生成しない。
    def test_aroma_oil_does_not_generate_generic_6_hon_phrase(self):
        item = make_item(name=self.AROMA_OIL_NAME)
        description = dg.generate_description(item, category="家電", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("6本で使いやすい", description)

    # 2.「210gで使いやすい」を生成しない。
    def test_folding_parasol_does_not_generate_generic_210g_phrase(self):
        item = make_item(name=self.FOLDING_PARASOL_NAME)
        description = dg.generate_description(item, category="ファッション", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("210gで使いやすい", description)

    # 3.「60cmで使いやすい」を生成しない。
    def test_mens_parasol_does_not_generate_generic_60cm_phrase(self):
        item = make_item(name=self.MENS_PARASOL_NAME)
        description = dg.generate_description(item, category="ファッション", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("60cmで使いやすい", description)

    # 4. 6本/210g/60cmそれぞれの意味（個数の種類・重さ・サイズ）を保持する。
    def test_quantity_phrases_keep_their_unit_specific_meaning(self):
        aroma_description = dg.generate_description(
            make_item(name=self.AROMA_OIL_NAME), category="家電", base_hashtags=BASE_HASHTAGS
        )
        self.assertIn("6本セットでいろいろな種類を試しやすい", aroma_description)

        parasol_description = dg.generate_description(
            make_item(name=self.FOLDING_PARASOL_NAME), category="ファッション", base_hashtags=BASE_HASHTAGS
        )
        self.assertIn("重さは約210g", parasol_description)

        mens_parasol_description = dg.generate_description(
            make_item(name=self.MENS_PARASOL_NAME), category="ファッション", base_hashtags=BASE_HASHTAGS
        )
        self.assertIn("サイズは約60cm", mens_parasol_description)

    # 5. 食品に#暮らしの便利グッズを機械的につけない。
    def test_food_items_do_not_get_mechanical_kurashi_hashtag(self):
        for name, category in (
            (self.RETORT_CURRY_NAME, "食品"),
            (self.RAMEN_NAME, "食品"),
        ):
            with self.subTest(name=name):
                item = make_item(name=name)
                description = dg.generate_description(item, category=category, base_hashtags=BASE_HASHTAGS)
                hashtag_line = description.split("\n\n")[-1]
                self.assertNotIn("#暮らしの便利グッズ", hashtag_line)

    # 6. 美容用品に#暮らしの便利グッズを機械的につけない。
    def test_beauty_item_does_not_get_mechanical_kurashi_hashtag(self):
        item = make_item(name=self.FACE_ROLLER_NAME)
        description = dg.generate_description(item, category="美容", base_hashtags=BASE_HASHTAGS)
        hashtag_line = description.split("\n\n")[-1]
        self.assertNotIn("#暮らしの便利グッズ", hashtag_line)
        self.assertIn("#美容", hashtag_line.split(" "))

    # 7. ベビーギフト（おむつケーキ）に#便利グッズを機械的につけない。
    def test_baby_gift_does_not_get_mechanical_benri_hashtag(self):
        item = make_item(name=self.DIAPER_CAKE_NAME)
        description = dg.generate_description(item, category="ベビー用品", base_hashtags=BASE_HASHTAGS)
        hashtag_line = description.split("\n\n")[-1]
        self.assertNotIn("#便利グッズ", hashtag_line)
        self.assertIn("#出産祝い", hashtag_line)
        self.assertIn("#ベビー用品", hashtag_line)

    # 8. ラーメンに未確認の「お店の味」を生成しない。
    def test_ramen_does_not_claim_restaurant_quality_taste(self):
        item = make_item(name=self.RAMEN_NAME)
        description = dg.generate_description(item, category="食品", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("お店の味", description)
        self.assertIn("ラーメン", description)

    # 9. 前回修正したハイブリッド加湿器の誤認防止が維持される。
    def test_hybrid_humidifier_misclassification_fix_still_holds(self):
        item = make_item(name=self.HYBRID_HUMIDIFIER_NAME)
        description = dg.generate_description(item, category="生活雑貨", base_hashtags=BASE_HASHTAGS)
        self.assertIn("加湿器", description)
        self.assertNotIn("リモコンの置き場所", description)
        self.assertNotIn("収納ラック", description)
        hashtag_line = description.split("\n\n")[-1]
        self.assertIn("#加湿器", hashtag_line)


class Sept26BatchRegressionTest(unittest.TestCase):
    """2026-09-26生成分のroom/data/candidates.jsonで実際に見つかった、
    新しい商品タイプの誤分類・数量表現の不自然さの回帰テスト
    （description-genre-004）。商品名は本番で実際に取得された表記を
    そのまま使っている。全ジャンル選定方式・商品選定ロジック・
    ランキングは変更していない（紹介文生成側の商品タイプ判定・数量判定・
    ハッシュタグだけが対象）。"""

    DEER_ANTLER_NAME = (
        "北海道産 鹿の角 ＼極太サイズ／鹿角 エゾシカ 犬 おもちゃ ペット おもちゃ TV取材多数 "
        "愛玩動物飼養管理士店長 推薦 デンタルケア 大型犬 中型犬 しつけ / いたずら / 甘噛み防止 "
        "犬の玩具 口臭対策 エゾシカ鹿角 犬 しつけ｜翌日発送"
    )
    PET_BOWL_NAME = (
        "【レビュー1,500件】ペット健康アドバイザー推奨 早食い防止 ペット 犬 フードボウル "
        "ペットボウル スローフード 丸飲み 防止 食器 ペット用品 丸洗い可能 餌入れ 小型 中型 大型 "
        "猫 ねこ いぬ ペットフード ドッグフード 早食い 防止皿 ペットフードボウル MILASIC公式"
    )
    CR1220_BATTERY_NAME = "リチウムコイン電池（CR1220）10個セット【体温計用電池　メール便送料無料】"
    LR41_BATTERY_NAME = (
        "アルカリボタン電池（LR41）20P【送料無料　ag3 lr41 LEDペンライト ペンライト コンサート "
        "医療 看護 ナース 看護師 ledペンライト 電池式】"
    )
    CIRCULATOR_NAME = (
        "[即日出荷] [レビュー11000件超え／高評価4.43点] サーキュレーター 360°首振り 洗える 扇風機 "
        "DCモーター コードレス ACモーター リモコン付き 省エネ 軽量 丸洗い DCファン 360度首振り "
        "3D首振り 卓上扇風機"
    )
    DIAPER_PANTS_NAME = (
        "【1種類を選べる】マミーポコパンツ 大きめで長〜く使える オムツ M L BIG(3個)【マミーポコパンツ】"
    )
    BABY_WIPES_NAME = (
        "【80枚×40個】おしりナップ やわらか厚手仕上げ 限定デザイン(森のかくれんぼ) | 0ヵ月〜 "
        "おしり拭き お尻拭き お尻ふき おしりふき ナップ おてふき 体拭き からだふき 詰め替え "
        "赤ちゃん 赤ちゃん用品 ベビー用品 衛生用品"
    )
    ECO_BAG_NAME = (
        "＼楽天ランキング 1位獲得／ エコバッグ コンビニサイズ コンビニ バッグ コンビニエコバッグ "
        "マチ広 折りたたみ コンパクト ミニ 2個セット マチ コンビニバッグ おしゃれ レジバッグ "
        "洗える 弁当 おにぎり 海苔 花柄 ストライプ ボーダー ブランド ecobag02"
    )
    LIVING_FAN_NAME = (
        "扇風機 左右首振り リビング扇風機 風量3段階 押しボタン 切りタイマー 静音 省エネ YLT-AG30E "
        "30cm羽根 首ふり リビングファン サーキュレーター おしゃれ シンプル 換気 熱中症対策 山善 "
        "YAMAZEN 【送料無料】"
    )
    HIMOKAWA_UDON_NAME = (
        "ひもかわうどん 帯麺 乾麺 めん170g × 4袋 8人前 濃縮つゆ8人前 送料無料 ひも川 通販 人気"
        "【ポスト投函配送】"
    )

    # 1. 鹿角を犬用おもちゃ（ペット用品）として認識する。
    def test_deer_antler_is_recognized_as_a_pet_toy(self):
        item = make_item(name=self.DEER_ANTLER_NAME)
        description = dg.generate_description(item, category="ペット用品", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("そんな暮らしの小さな不便を解消してくれそうな便利グッズ", description)
        self.assertIn("鹿の角", description)
        for phrase in ("口臭が改善する", "歯が健康になる", "口臭が良くなる"):
            self.assertNotIn(phrase, description)

    # 2. 早食い防止ペットボウルをペット用品として認識する。
    def test_pet_bowl_is_recognized_as_pet_goods(self):
        item = make_item(name=self.PET_BOWL_NAME)
        description = dg.generate_description(item, category="ペット用品", base_hashtags=BASE_HASHTAGS)
        self.assertIn("フードボウル", description)
        self.assertIn("早食い防止", description)
        self.assertNotIn("健康になる", description)

    # 3. CR1220（リチウムコイン電池）を電池として認識する（カテゴリーは
    # 「健康」だが、商品本体を優先する）。
    def test_cr1220_is_recognized_as_a_battery_not_health_goods(self):
        item = make_item(name=self.CR1220_BATTERY_NAME)
        description = dg.generate_description(item, category="健康", base_hashtags=BASE_HASHTAGS)
        self.assertIn("電池", description)
        hashtag_line = description.split("\n\n")[-1]
        self.assertNotIn("#健康グッズ", hashtag_line)
        self.assertIn("#ボタン電池", hashtag_line)

    # 4. LR41（アルカリボタン電池）を電池として認識する（医療機器として
    # 扱わない）。
    def test_lr41_is_recognized_as_a_battery_not_medical_device(self):
        item = make_item(name=self.LR41_BATTERY_NAME)
        description = dg.generate_description(item, category="健康", base_hashtags=BASE_HASHTAGS)
        self.assertIn("電池", description)
        for phrase in ("医療機器", "看護師が選ぶ"):
            self.assertNotIn(phrase, description)

    # 5. 「10個で使いやすい」ではなく「10個セット」等、数量の意味をそのまま
    # 表現する。
    def test_cr1220_quantity_is_expressed_as_a_set_not_generic_usability(self):
        description = dg.generate_description(
            make_item(name=self.CR1220_BATTERY_NAME), category="健康", base_hashtags=BASE_HASHTAGS
        )
        self.assertIn("10個セット", description)
        self.assertNotIn("10個で使いやすい", description)

    # 6. マミーポコパンツを紙おむつとして認識する。
    def test_diaper_pants_is_recognized_as_a_diaper(self):
        item = make_item(name=self.DIAPER_PANTS_NAME)
        description = dg.generate_description(item, category="ベビー用品", base_hashtags=BASE_HASHTAGS)
        self.assertIn("おむつ", description)

    # 7. 「1種類を選べる」＋「3個」を、3種類の詰め合わせセットと誤認しない
    # （M/L/BIGを同時に試せるとは書かない）。
    def test_diaper_pants_single_choice_is_not_mistaken_for_a_variety_set(self):
        item = make_item(name=self.DIAPER_PANTS_NAME)
        description = dg.generate_description(item, category="ベビー用品", base_hashtags=BASE_HASHTAGS)
        self.assertIn("3個セット", description)
        self.assertNotIn("3個セットでいろいろな種類を試しやすい", description)
        for phrase in ("M/L/BIGを同時に", "M・L・BIGを同時に", "3種類を同時に試せる"):
            self.assertNotIn(phrase, description)

    # 8. おしりふき（おしりナップ）をおしりふきとして認識する。
    def test_baby_wipes_is_recognized_as_baby_wipes(self):
        item = make_item(name=self.BABY_WIPES_NAME)
        description = dg.generate_description(item, category="ベビー用品", base_hashtags=BASE_HASHTAGS)
        self.assertIn("おしりふき", description)

    # 9. 「80枚」に落とさず「80枚×40個」という複合数量を保持する。
    def test_baby_wipes_quantity_keeps_the_full_compound_meaning(self):
        phrase = dg._extract_quantity_phrase(self.BABY_WIPES_NAME)
        self.assertEqual(phrase, "80枚×40個")
        item = make_item(name=self.BABY_WIPES_NAME)
        description = dg.generate_description(item, category="ベビー用品", base_hashtags=BASE_HASHTAGS)
        # 「80枚×40個」→「80枚入り×40個」という、数量の意味を保持した
        # 自然な言い回しになっている（description-genre-005対応）。
        self.assertIn("80枚入り×40個", description)
        self.assertNotIn("✔️ 80枚で使いやすい", description)
        self.assertNotIn("80枚×40個で使いやすい", description)

    # 10. 「詰め替え」から「ごみを減らせる」等の環境効果を推測しない
    # （「詰め替えタイプ」までは可）。
    def test_baby_wipes_refill_does_not_claim_less_garbage(self):
        item = make_item(name=self.BABY_WIPES_NAME)
        description = dg.generate_description(item, category="ベビー用品", base_hashtags=BASE_HASHTAGS)
        self.assertIn("詰め替えタイプ", description)
        self.assertNotIn("ごみを減らし", description)
        self.assertNotIn("ゴミを減らし", description)

    # 11. エコバッグをエコバッグとして認識する。
    def test_eco_bag_is_recognized_as_an_eco_bag(self):
        item = make_item(name=self.ECO_BAG_NAME)
        description = dg.generate_description(item, category="ファッション", base_hashtags=BASE_HASHTAGS)
        self.assertIn("エコバッグ", description)
        self.assertNotIn("そんな暮らしの小さな不便を解消してくれそうな便利グッズ", description)
        # この商品には天気・気温の話は不要（description-genre-004対応）。
        for phrase in ("気温", "暑い日", "寒い日"):
            self.assertNotIn(phrase, description)

    # 12. 「2個で使いやすい」ではなく「2個セット」等、数量の意味を保つ。
    def test_eco_bag_quantity_is_expressed_as_a_set(self):
        description = dg.generate_description(
            make_item(name=self.ECO_BAG_NAME), category="ファッション", base_hashtags=BASE_HASHTAGS
        )
        self.assertIn("2個セット", description)
        self.assertNotIn("2個で使いやすい", description)

    # 13. サーキュレーターをサーキュレーターとして認識する（「家電」という
    # 汎用文にしない）。
    def test_circulator_is_recognized_as_a_circulator(self):
        item = make_item(name=self.CIRCULATOR_NAME)
        description = dg.generate_description(item, category="家電", base_hashtags=BASE_HASHTAGS)
        self.assertIn("サーキュレーター", description)
        self.assertNotIn("そんな暮らしの小さな不便を解消してくれそうな便利グッズ", description)

    # 14. 扇風機を扇風機として認識する（「家電」という汎用文にしない。
    # 熱中症対策等の健康効果は断定しない）。
    def test_living_fan_is_recognized_as_a_fan(self):
        item = make_item(name=self.LIVING_FAN_NAME)
        description = dg.generate_description(item, category="家電", base_hashtags=BASE_HASHTAGS)
        self.assertIn("扇風機", description)
        for phrase in ("熱中症を防げる", "熱中症対策になる", "熱中症を予防できる"):
            self.assertNotIn(phrase, description)

    # 15. 「30cm羽根」を商品の数量として誤認しない。
    def test_fan_blade_size_is_not_mistaken_for_product_quantity(self):
        phrase = dg._extract_quantity_phrase(self.LIVING_FAN_NAME)
        self.assertNotIn("30cm", phrase)
        item = make_item(name=self.LIVING_FAN_NAME)
        description = dg.generate_description(item, category="家電", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("30cmで使いやすい", description)
        self.assertNotIn("サイズは約30cm", description)

    # 16. サーキュレーター・扇風機のいずれも、両方の語が同じ商品名に
    # 混在していても、商品タイトルの中で先に登場する語（＝実際の商品
    # 本体）を優先する（description-genre-004対応の位置優先判定）。
    def test_circulator_and_fan_prefer_the_earlier_mentioned_keyword(self):
        self.assertEqual(dg.match_product_type_keyword(self.CIRCULATOR_NAME), "サーキュレーター")
        self.assertEqual(dg.match_product_type_keyword(self.LIVING_FAN_NAME), "扇風機")

    # 17. ひもかわうどんを食品（うどん）として紹介する。
    def test_himokawa_udon_is_introduced_as_udon(self):
        item = make_item(name=self.HIMOKAWA_UDON_NAME)
        description = dg.generate_description(item, category="食品", base_hashtags=BASE_HASHTAGS)
        self.assertIn("うどん", description)
        self.assertNotIn("そんな暮らしの小さな不便を解消してくれそうな便利グッズ", description)

    # 18. 「170g×4袋」を保持する（170gだけに落とさない）。
    def test_udon_quantity_keeps_the_weight_times_bag_count(self):
        item = make_item(name=self.HIMOKAWA_UDON_NAME)
        description = dg.generate_description(item, category="食品", base_hashtags=BASE_HASHTAGS)
        self.assertIn("170g", description)
        self.assertIn("4袋", description)

    # 19. 「8人前」を保持する。
    def test_udon_quantity_keeps_the_serving_count(self):
        item = make_item(name=self.HIMOKAWA_UDON_NAME)
        description = dg.generate_description(item, category="食品", base_hashtags=BASE_HASHTAGS)
        self.assertIn("8人前", description)

    # 20. 商品タイプに合ったハッシュタグが付き、未確認の健康/美容効果を
    # 生成しない（今回の10商品まとめての最終確認）。
    def test_all_ten_items_have_matching_hashtags_and_no_unconfirmed_effects(self):
        expectations = {
            self.DEER_ANTLER_NAME: ("ペット用品", "#ペット用品"),
            self.PET_BOWL_NAME: ("ペット用品", "#ペット用品"),
            self.CR1220_BATTERY_NAME: ("健康", "#ボタン電池"),
            self.LR41_BATTERY_NAME: ("健康", "#ボタン電池"),
            self.CIRCULATOR_NAME: ("家電", "#サーキュレーター"),
            self.DIAPER_PANTS_NAME: ("ベビー用品", "#おむつ"),
            self.BABY_WIPES_NAME: ("ベビー用品", "#おしりふき"),
            self.ECO_BAG_NAME: ("ファッション", "#エコバッグ"),
            self.LIVING_FAN_NAME: ("家電", "#扇風機"),
            self.HIMOKAWA_UDON_NAME: ("食品", "#うどん"),
        }
        forbidden_phrases = (
            "健康になる", "改善する", "治る", "痩せる", "リフトアップ", "小顔になる",
        )
        for name, (category, expected_tag) in expectations.items():
            item = make_item(name=name)
            description = dg.generate_description(item, category=category, base_hashtags=BASE_HASHTAGS)
            hashtag_line = description.split("\n\n")[-1]
            self.assertIn(expected_tag, hashtag_line, description)
            for phrase in forbidden_phrases:
                self.assertNotIn(phrase, description, description)
            self.assertLessEqual(len(description), 500)


class DescriptionGenre005RegressionTest(unittest.TestCase):
    """2026-09-26 15:46生成分の最終調整（description-genre-005）の回帰
    テスト。同じ商品タイプ（ボタン電池）でも、確認できない他商品固有の
    用途（CR1220の「体温計用」をLR41へ流用する等）を混入させないこと、
    複合数量表現（80枚×40個・170g×4袋 8人前）を自然な言い回しに整える
    こと、ひもかわうどんの導入文が商品の性質と矛盾しないことを確認する。
    商品名はSept26BatchRegressionTestと同じ、本番で実際に取得された
    表記を再利用する。"""

    CR1220_BATTERY_NAME = Sept26BatchRegressionTest.CR1220_BATTERY_NAME
    LR41_BATTERY_NAME = Sept26BatchRegressionTest.LR41_BATTERY_NAME
    BABY_WIPES_NAME = Sept26BatchRegressionTest.BABY_WIPES_NAME
    HIMOKAWA_UDON_NAME = Sept26BatchRegressionTest.HIMOKAWA_UDON_NAME

    # 1. LR41紹介文に「体温計」を勝手に追加しない（CR1220の商品固有情報を
    # 流用しない）。
    def test_lr41_description_does_not_borrow_cr1220_thermometer_claim(self):
        item = make_item(name=self.LR41_BATTERY_NAME)
        description = dg.generate_description(item, category="健康", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("体温計", description)

    # 2. CR1220はタイトルに「体温計用」とあるため、その情報は使用可能。
    def test_cr1220_description_may_use_its_own_thermometer_claim(self):
        item = make_item(name=self.CR1220_BATTERY_NAME)
        description = dg.generate_description(item, category="健康", base_hashtags=BASE_HASHTAGS)
        self.assertIn("体温計", description)

    # 3. 同じ商品タイプ（ボタン電池）間で、商品固有の用途を流用しない
    # （CR1220とLR41で、確認できる用途が異なることを確認する）。
    def test_battery_products_do_not_share_each_others_specific_use_case(self):
        cr1220_description = dg.generate_description(
            make_item(name=self.CR1220_BATTERY_NAME), category="健康", base_hashtags=BASE_HASHTAGS
        )
        lr41_description = dg.generate_description(
            make_item(name=self.LR41_BATTERY_NAME), category="健康", base_hashtags=BASE_HASHTAGS
        )
        self.assertIn("体温計", cr1220_description)
        self.assertNotIn("体温計", lr41_description)
        self.assertIn("LEDペンライト", lr41_description)
        self.assertNotIn("LEDペンライト", cr1220_description)

    # 4. 「20Pで使いやすい」を生成しない。
    def test_lr41_does_not_generate_generic_20p_phrase(self):
        item = make_item(name=self.LR41_BATTERY_NAME)
        description = dg.generate_description(item, category="健康", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("20Pで使いやすい", description)
        self.assertIn("20P", description)

    # 5. 「80枚×40個」→数量の意味を保持した自然な表現（80枚入り×40個）に
    # なる。
    def test_baby_wipes_compound_quantity_becomes_natural_phrasing(self):
        item = make_item(name=self.BABY_WIPES_NAME)
        description = dg.generate_description(item, category="ベビー用品", base_hashtags=BASE_HASHTAGS)
        self.assertIn("80枚入り×40個", description)

    # 6. 「80枚×40個で使いやすい」を生成しない。
    def test_baby_wipes_does_not_generate_the_old_unnatural_phrase(self):
        item = make_item(name=self.BABY_WIPES_NAME)
        description = dg.generate_description(item, category="ベビー用品", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("80枚×40個で使いやすい", description)

    # 7. 「170g×4袋・8人前」の意味を保持する。
    def test_udon_quantity_and_servings_are_both_kept(self):
        item = make_item(name=self.HIMOKAWA_UDON_NAME)
        description = dg.generate_description(item, category="食品", base_hashtags=BASE_HASHTAGS)
        self.assertIn("170g", description)
        self.assertIn("4袋", description)
        self.assertIn("8人前", description)

    # 8. 「170g×4袋 8人前で使いやすい」を生成しない。
    def test_udon_does_not_generate_the_old_unnatural_phrase(self):
        item = make_item(name=self.HIMOKAWA_UDON_NAME)
        description = dg.generate_description(item, category="食品", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("170g × 4袋 8人前で使いやすい", description)
        self.assertNotIn("170g×4袋 8人前で使いやすい", description)

    # 9. ひもかわうどんに不自然な「茹でるのが手間」という導入を生成しない
    # （乾麺である本商品自体も茹でる必要があるため、悩みの解決にならない）。
    def test_udon_intro_does_not_claim_boiling_is_a_hassle(self):
        item = make_item(name=self.HIMOKAWA_UDON_NAME)
        description = dg.generate_description(item, category="食品", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("茹でるところから始めると", description)
        self.assertNotIn("茹でるのが", description)


class Sept27BatchRegressionTest(unittest.TestCase):
    """2026-09-27 15:47生成分のroom/data/candidates.jsonで実際に見つかった、
    商品本体判定の誤り（description-genre-006）の回帰テスト。商品名に
    複数の商品タイプ語が含まれる場合、単純な出現位置だけでなく、より
    具体的な商品タイプ語を優先することを確認する。商品名は本番で実際に
    取得された表記をそのまま使っている。"""

    AROMA_OIL_5_SET_NAME = (
        "ブレンド お試し よりどり5本セット (各5ml) エッセンシャルオイル 精油 アロマオイル "
        "【送料無料】 全20種 メール便 (追跡番号付き) 代金引換不可 アロマディフューザー "
        "アロマ加湿器"
    )
    MASK_SPRAY_NAME = (
        "マスクスプレー アロマスプレー よりどり3本 30ml 篠山精油 花粉スプレー 香りを楽しむ "
        "アロマ 精油 ハーブウォーター スプレー レモングラス ひのき 杉 ゼラニウム ハッカ "
        "プチギフト アロマオイル ピローミスト 天然成分100%"
    )
    DOG_FOOD_NAME = (
        "［公式 ドッグフード工房］ドッグフード 無添加 国産 馬肉 鶏肉 野菜畑 鹿肉 小麦不使用 "
        "選べる小袋 3袋セット｜厳選自然素材 天然食材 栄養食材 ドライフード ペットフード "
        "獣医師推奨 全犬種 全年齢 毛並み 目 涙やけ におい"
    )
    GOAT_MILK_NAME = (
        "【P5倍!9/30迄】【まとめ買い割引適応！】 無添加 ヤギミルクパウダー 100g 500g 1000g "
        "全脂粉乳 脱脂粉乳 ヤギミルク 保存料 オーガニック 山羊 やぎ ミルク 粉末 パウダー "
        "ペット用 愛犬用 小型犬 大型犬 栄養豊富 タンパク質 ミネラル ペットフード ドッグフード "
        "おやつ"
    )
    SWADDLE_NAME = (
        "スワドルメリー おくるみ スワドル スリーパー 新生児 通気性 すわどる 手が出せる キッズ "
        "赤ちゃん ベビー モロー反射 くま レモン 星 おしゃれ かわいい 寝かしつけ 夜泣き 退院 綿 "
        "100 男の子 女の子 出産祝い ベビー用品 手出し コペルタ 通年 春 夏 秋 冬 兼 用"
    )
    DIAPER_PAIL_NAME = (
        "＼最大5万ポイント当たる!／＼楽天1位獲得！／ 防臭 ウッビー Ubbi おむつペール "
        "カートリッジ不要 おむつ ゴミ箱 臭わない インテリア オムツ ペール おむつ処理ポット 18L "
        "赤ちゃん ベビー 出産祝い 出産準備 ペット 犬 猫 トイレ 介護 ペットシーツ ネコ砂"
    )
    DIAPER_STOCKER_NAME = (
        "口コミ2800件!!＜芸能人愛用＞楽天1位6冠≪レビュー特典≫LARUTAN おむつストッカー "
        "蓋付き 仕切り 収納 オムツストッカー お世話セット おむつバッグ 大容量 ベビー用品 "
        "収納ケース おむつ入れ おもちゃ バッグ 出産準備 赤ちゃん 出産祝い おしゃれ おむつケーキ "
        "ギフト"
    )

    # 1. アロマスプレーをアロマオイルと誤認しない（「アロマオイル」という
    # 関連語が後半にあっても、商品本体のスプレーを優先する）。
    def test_mask_spray_is_not_mistaken_for_aroma_oil(self):
        item = make_item(name=self.MASK_SPRAY_NAME)
        description = dg.generate_description(item, category="生活雑貨", base_hashtags=BASE_HASHTAGS)
        self.assertIn("アロマスプレー", description)
        self.assertNotIn("ディフューザー", description)
        for phrase in ("花粉を防ぐ", "花粉症に効く", "花粉症に良い"):
            self.assertNotIn(phrase, description)

    # 2. アロマオイル本体は従来通り正しく判定する（アロマスプレー対応を
    # 追加しても、本物のアロマオイルまでスプレー扱いしない）。
    def test_real_aroma_oil_is_still_recognized_as_aroma_oil_not_spray(self):
        item = make_item(name=self.AROMA_OIL_5_SET_NAME)
        description = dg.generate_description(item, category="生活雑貨", base_hashtags=BASE_HASHTAGS)
        self.assertIn("アロマオイル", description)
        self.assertNotIn("スプレー", description)
        hashtag_line = description.split("\n\n")[-1]
        self.assertIn("#アロマオイル", hashtag_line)

    # 3. ドッグフードを犬用フードとして認識する（暮らしの便利グッズ扱いに
    # しない）。
    def test_dog_food_is_recognized_as_dog_food(self):
        item = make_item(name=self.DOG_FOOD_NAME)
        description = dg.generate_description(item, category="ペット用品", base_hashtags=BASE_HASHTAGS)
        self.assertIn("ドッグフード", description)
        self.assertNotIn("そんな暮らしの小さな不便を解消してくれそうな便利グッズ", description)
        for phrase in ("毛並みが改善する", "涙やけが治る", "健康になる"):
            self.assertNotIn(phrase, description)

    # 4. ヤギミルクをペット用食品として認識する。
    def test_goat_milk_is_recognized_as_pet_food(self):
        item = make_item(name=self.GOAT_MILK_NAME)
        description = dg.generate_description(item, category="ペット用品", base_hashtags=BASE_HASHTAGS)
        self.assertIn("ヤギミルク", description)
        self.assertNotIn("そんな暮らしの小さな不便を解消してくれそうな便利グッズ", description)

    # 5. 「100g 500g 1000g」を「重さは約100g」のように最初の値だけに
    # 固定しない。
    def test_goat_milk_multiple_sizes_are_not_fixed_to_the_first_value(self):
        item = make_item(name=self.GOAT_MILK_NAME)
        description = dg.generate_description(item, category="ペット用品", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("重さは約100g", description)
        self.assertIn("100g", description)
        self.assertIn("500g", description)
        self.assertIn("1000g", description)

    # 6. スワドル/おくるみをスワドル/おくるみとして認識する。
    def test_swaddle_is_recognized_as_a_swaddle(self):
        item = make_item(name=self.SWADDLE_NAME)
        description = dg.generate_description(item, category="ベビー用品", base_hashtags=BASE_HASHTAGS)
        self.assertTrue("スワドル" in description or "おくるみ" in description)
        for phrase in ("夜泣きを改善する", "よく眠れる", "モロー反射を防ぐ"):
            self.assertNotIn(phrase, description)

    # 7. おむつペールをゴミ箱として認識する。
    def test_diaper_pail_is_recognized_as_a_trash_can(self):
        item = make_item(name=self.DIAPER_PAIL_NAME)
        description = dg.generate_description(item, category="ベビー用品", base_hashtags=BASE_HASHTAGS)
        self.assertIn("ゴミ箱", description)
        self.assertNotIn("臭いが完全になくなる", description)

    # 8. おむつペールを紙おむつと誤認しない。
    def test_diaper_pail_is_not_mistaken_for_a_paper_diaper(self):
        item = make_item(name=self.DIAPER_PAIL_NAME)
        description = dg.generate_description(item, category="ベビー用品", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("おむつ選び、地味に悩みませんか", description)
        self.assertNotIn("紙おむつ◎", description)

    # 9. おむつストッカーを収納用品として認識する。
    def test_diaper_stocker_is_recognized_as_storage_goods(self):
        item = make_item(name=self.DIAPER_STOCKER_NAME)
        description = dg.generate_description(item, category="収納", base_hashtags=BASE_HASHTAGS)
        self.assertIn("おむつストッカー", description)
        hashtag_line = description.split("\n\n")[-1]
        self.assertIn("#おむつ収納", hashtag_line)

    # 10. おむつストッカーを紙おむつと誤認しない。
    def test_diaper_stocker_is_not_mistaken_for_a_paper_diaper(self):
        item = make_item(name=self.DIAPER_STOCKER_NAME)
        description = dg.generate_description(item, category="収納", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("おむつ選び、地味に悩みませんか", description)
        self.assertNotIn("紙おむつ◎", description)

    # 11. 具体的複合商品名が一般語より優先される（「おむつ」という一般語を
    # 含んでいても、複合語「おむつペール」「おむつストッカー」を商品本体
    # として優先する）。
    def test_specific_compound_product_name_outranks_generic_word(self):
        self.assertEqual(dg.match_product_type_keyword(self.DIAPER_PAIL_NAME), "おむつペール")
        self.assertEqual(dg.match_product_type_keyword(self.DIAPER_STOCKER_NAME), "おむつストッカー")

    # 12. 健康効果を勝手に生成しない（今回の新規6商品まとめての確認）。
    def test_new_product_types_do_not_generate_unconfirmed_health_effects(self):
        forbidden_phrases = (
            "改善する", "治る", "健康になる", "花粉症に効く", "よく眠れる", "臭いが完全になくなる",
        )
        for name, category in (
            (self.MASK_SPRAY_NAME, "生活雑貨"),
            (self.DOG_FOOD_NAME, "ペット用品"),
            (self.GOAT_MILK_NAME, "ペット用品"),
            (self.SWADDLE_NAME, "ベビー用品"),
            (self.DIAPER_PAIL_NAME, "ベビー用品"),
            (self.DIAPER_STOCKER_NAME, "収納"),
        ):
            item = make_item(name=name)
            description = dg.generate_description(item, category=category, base_hashtags=BASE_HASHTAGS)
            for phrase in forbidden_phrases:
                self.assertNotIn(phrase, description, description)

    # 13. 商品タイプに合ったハッシュタグが付く（今回の新規6商品）。
    def test_new_product_types_get_matching_hashtags(self):
        expectations = {
            self.MASK_SPRAY_NAME: ("生活雑貨", "#アロマスプレー"),
            self.DOG_FOOD_NAME: ("ペット用品", "#ドッグフード"),
            self.GOAT_MILK_NAME: ("ペット用品", "#犬用品"),
            self.SWADDLE_NAME: ("ベビー用品", "#スワドル"),
            self.DIAPER_PAIL_NAME: ("ベビー用品", "#おむつゴミ箱"),
            self.DIAPER_STOCKER_NAME: ("収納", "#おむつ収納"),
        }
        for name, (category, expected_tag) in expectations.items():
            item = make_item(name=name)
            description = dg.generate_description(item, category=category, base_hashtags=BASE_HASHTAGS)
            hashtag_line = description.split("\n\n")[-1]
            self.assertIn(expected_tag, hashtag_line, description)
            self.assertNotIn("#暮らしの便利グッズ", hashtag_line)
            self.assertNotIn("#便利グッズ", hashtag_line)
            self.assertLessEqual(len(description), 500)

    # 14. 別商品の固有情報を流用しない（今回新設したテンプレート同士でも、
    # 前回description-genre-005の設計方針が維持されていることを確認）。
    def test_new_templates_do_not_borrow_unconfirmed_specifics_across_items(self):
        dog_food_description = dg.generate_description(
            make_item(name=self.DOG_FOOD_NAME), category="ペット用品", base_hashtags=BASE_HASHTAGS
        )
        goat_milk_description = dg.generate_description(
            make_item(name=self.GOAT_MILK_NAME), category="ペット用品", base_hashtags=BASE_HASHTAGS
        )
        self.assertNotIn("ヤギミルク", dog_food_description)
        self.assertNotIn("ドッグフード", goat_milk_description.split("◎")[0])


class DescriptionGenre007RegressionTest(unittest.TestCase):
    """2026-09-27 15:47生成分の最終調整（description-genre-007）の回帰
    テスト。①数量と種類数を分離し、明確な根拠がない場合に「いろいろな
    種類を試しやすい」を生成しないこと、②GENERIC_TEMPLATESの汎用文を
    使う消耗品（韃靼そば茶等）でも、商品本体に合ったハッシュタグを使い、
    #暮らしの便利グッズ・#便利グッズを機械的に付けないこと、を確認する。
    商品名はSept27BatchRegressionTestと同じ、本番で実際に取得された
    表記を再利用する。"""

    DOG_FOOD_NAME = Sept27BatchRegressionTest.DOG_FOOD_NAME
    AROMA_OIL_NAME = (
        "アロマオイル AEAJ認定 40種から選べる6本 各5ml 精油 返品保証付 送料無料 100%ピュア "
        "エッセンシャルオイル セット アロマ 加湿器 オーガニック お試し ラベンダー オレンジ 天然"
    )
    MASK_SPRAY_NAME = Sept27BatchRegressionTest.MASK_SPRAY_NAME
    DIAPER_PANTS_NAME = (
        "【1種類を選べる】マミーポコパンツ 大きめで長〜く使える オムツ M L BIG(3個)【マミーポコパンツ】"
    )
    BUCKWHEAT_TEA_NAME = (
        "国産 韃靼そば茶 1kg [ 北海道産 など 国産100％ ] ほんぢ園 ＜ ペットボトルよりお得 蕎麦茶 "
        "ダッタンそば茶 だったんそばちゃ 韃靼そばちゃ だったんそば茶 韃靼そば ルチン "
        "ノンカフェイン ＞ 送料無料 同梱不可 ／ラ／"
    )

    # 1. 「選べる小袋3袋セット」から3種類セットと断定しない。
    def test_dog_food_does_not_assume_three_varieties_from_bare_selectable(self):
        item = make_item(name=self.DOG_FOOD_NAME)
        description = dg.generate_description(item, category="ペット用品", base_hashtags=BASE_HASHTAGS)
        self.assertIn("3袋セット", description)
        self.assertNotIn("3袋セットでいろいろな種類を試しやすい", description)

    # 2. 数量と種類数を別に扱う（明確な根拠（40種から選べる等）がある
    # 場合は従来通りアソート表現を維持する）。
    def test_quantity_and_variety_count_are_handled_separately(self):
        aroma_oil_description = dg.generate_description(
            make_item(name=self.AROMA_OIL_NAME), category="家電", base_hashtags=BASE_HASHTAGS
        )
        self.assertIn("6本セットでいろいろな種類を試しやすい", aroma_oil_description)

        dog_food_description = dg.generate_description(
            make_item(name=self.DOG_FOOD_NAME), category="ペット用品", base_hashtags=BASE_HASHTAGS
        )
        self.assertNotIn("いろいろな種類を試しやすい", dog_food_description)

    # 3. 明確な根拠がない場合「いろいろな種類を試しやすい」を生成しない
    # （「選べる」が商品本体の数量と無関係な文脈で使われている場合。
    # マミーポコパンツの「1種類を選べる」も引き続き除外されることを確認）。
    def test_bare_selectable_word_without_species_count_does_not_trigger_variety(self):
        item = make_item(name=self.DIAPER_PANTS_NAME)
        description = dg.generate_description(item, category="ベビー用品", base_hashtags=BASE_HASHTAGS)
        self.assertIn("3個セット", description)
        self.assertNotIn("3個セットでいろいろな種類を試しやすい", description)

        # 「よりどり」は単語自体が複数種類からの詰め合わせを意味するため、
        # 引き続きアソート表現を維持する。
        mask_spray_description = dg.generate_description(
            make_item(name=self.MASK_SPRAY_NAME), category="生活雑貨", base_hashtags=BASE_HASHTAGS
        )
        self.assertIn("3本セットでいろいろな種類を試しやすい", mask_spray_description)

    # 4. 韃靼そば茶に#暮らしの便利グッズを付けない。
    def test_buckwheat_tea_does_not_get_mechanical_kurashi_hashtag(self):
        item = make_item(name=self.BUCKWHEAT_TEA_NAME)
        description = dg.generate_description(item, category="お茶", base_hashtags=BASE_HASHTAGS)
        hashtag_line = description.split("\n\n")[-1]
        self.assertNotIn("#暮らしの便利グッズ", hashtag_line)

    # 5. 韃靼そば茶に#便利グッズを付けない。
    def test_buckwheat_tea_does_not_get_mechanical_benri_hashtag(self):
        item = make_item(name=self.BUCKWHEAT_TEA_NAME)
        description = dg.generate_description(item, category="お茶", base_hashtags=BASE_HASHTAGS)
        hashtag_line = description.split("\n\n")[-1]
        self.assertNotIn("#便利グッズ", hashtag_line)

    # 6. 韃靼そば茶の商品本体に合ったタグを生成する。
    def test_buckwheat_tea_gets_a_product_specific_hashtag(self):
        item = make_item(name=self.BUCKWHEAT_TEA_NAME)
        description = dg.generate_description(item, category="お茶", base_hashtags=BASE_HASHTAGS)
        hashtag_line = description.split("\n\n")[-1]
        self.assertIn("#お茶", hashtag_line)
        self.assertIn("#韃靼そば茶", hashtag_line)
        # 紹介文の本文（GENERIC_TEMPLATES["お茶"]の安全な汎用文）は
        # 変更していないため、商品タイプ判定の構造自体は維持されている。
        self.assertIn("お茶", description)


class Sept28BatchRegressionTest(unittest.TestCase):
    """2026-09-28 15:51生成分のroom/data/candidates.jsonで実際に見つかった、
    商品本体判定・数値/重量判定・ペット用品の安全フォールバックの誤りの
    回帰テスト（description-genre-008）。商品名は本番で実際に取得された
    表記をそのまま使っている。"""

    HIP_SEAT_NAME = (
        "【楽天1位】ヒップシート コペルタ 抱っこ紐 コンパクト おむつ おしりふき 収納ポケット付き "
        "20kg 抱っこ カバン 荷物 ショルダー バッグ 折り畳み 折りたたみ 赤ちゃん 前向き "
        "ウエストポーチ 簡単 シングル 人気 出産祝い 新生児 腰痛対策 ママ ギフト ベビー用品 軽量"
    )
    MILK_WARMER_NAME = (
        "口コミ3400件!!◆楽天1位17冠◆芸能人愛用＜管理栄養士推薦＞離乳食冊子付き♪ミルクウォーマー "
        "ボトルウォーマー 哺乳瓶ウォーマー ミルク 調乳ポット 離乳食 缶ミルク 双子 哺乳瓶 "
        "ウォーマー 保温 調乳 母乳 除菌 ベビー 出産準備 赤ちゃん ベビー用品 出産祝い ギフト"
    )
    CAR_SUNSHADE_NAME = (
        "【クーポン利用で最安2280円】「楽天1位 37冠達成！」サンシェード 車 傘 フロント 10本骨 "
        "自動車用 日よけ 車用品 フロント カーサンシェー UVカット 遮光率100％ 断熱100％ "
        "傘型サンシェード 車用サンシェード 大きいサイズ シェード 簡単取付 車種汎用 日本製"
    )
    YAKUNO_SOBA_NAME = (
        "乾麺夜久野そば6人前つゆ付 祝★レビュー2400件♪ メール便でお届け 国産そば粉使用 内祝い "
        "やくのそば 国内産 ざる 蕎麦 10倍 年越しそば 年越し"
    )
    FOLDING_UMBRELLA_NAME = (
        "【10％OFFクーポン配布中！】折りたたみ傘 メンズ 軽量【楽天第1位 260g超軽量 "
        "10本骨12本骨追加】折り畳み傘 ワンタッチ 軽量 折りたたみ傘 メンズ 自動開閉 折り畳み傘 "
        "メンズ レディー 折りたたみ傘 ワンタッチ 撥水速乾 耐強風 男女兼 梅雨 スポーツ観戦 《u43》"
    )
    NAGANO_SOBA_NAME = (
        "お試しセット 信州戸隠そば 信州そば 本十割そば 信州戸隠そば乾麺2種 おまけ付 蕎麦 "
        "乾麺（4人前）"
    )
    DUST_SPONGE_NAME = (
        "【最大40%オフクーポン★お買い物マラソン】ほこり取り スポンジ ダスタースポンジ "
        "ほこり取りスポンジ 掃除スポンジ 埃取り ホコリ取り 掃除用品 掃除グッズ 便利グッズ 水拭き "
        "繰り返し使える 水洗い可能 髪の毛取り 巾木掃除 サッシ掃除 洗濯機まわり"
    )
    UNKNOWN_SENIOR_DOG_NAME = "【 サイエンス 】　シニア　小粒　【高齢犬用】　12kg"
    UNKNOWN_PET_TOY_NAME = "サンジョルディ たまごちゃん"
    BABY_WIPES_810_NAME = (
        "おしりふき まとめ買い 水99.9 厚手 水分たっぷり シート【送料無料】54枚×15個 計810枚"
        "【肌にやさしい】 おしり拭き お尻拭き お尻ふき 厚手 赤ちゃん おしりふき厚手 ベビー "
        "レック ダイレクト"
    )
    OLD_BABY_WIPES_NAME = (
        "【80枚×40個】おしりナップ やわらか厚手仕上げ 限定デザイン(森のかくれんぼ) | 0ヵ月〜 "
        "おしり拭き お尻拭き お尻ふき おしりふき ナップ おてふき 体拭き からだふき 詰め替え "
        "赤ちゃん 赤ちゃん用品 ベビー用品 衛生用品"
    )

    # 1. ヒップシートをおしりふきと誤認しない。
    def test_hip_seat_is_not_mistaken_for_baby_wipes(self):
        item = make_item(name=self.HIP_SEAT_NAME)
        description = dg.generate_description(item, category="収納", base_hashtags=BASE_HASHTAGS)
        self.assertIn("ヒップシート", description)
        self.assertNotIn("おしりふき、気づくとすぐ無くなっていない", description)

    # 2. 「20kg」をヒップシート本体重量と誤認しない。
    def test_hip_seat_20kg_is_not_mistaken_for_product_weight(self):
        item = make_item(name=self.HIP_SEAT_NAME)
        description = dg.generate_description(item, category="収納", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("重さは約20kg", description)
        self.assertNotIn("腰痛が改善する", description)
        self.assertNotIn("腰痛が治る", description)

    # 3. ミルクウォーマーを正しく判定する。
    def test_milk_warmer_is_recognized_correctly(self):
        item = make_item(name=self.MILK_WARMER_NAME)
        description = dg.generate_description(item, category="ベビー用品", base_hashtags=BASE_HASHTAGS)
        self.assertIn("ミルクウォーマー", description)
        self.assertNotIn("赤ちゃんとの暮らしに取り入れやすいベビー用品◎", description)
        for phrase in ("除菌力が高い", "常に一定の温度", "○分で温まる"):
            self.assertNotIn(phrase, description)

    # 4. 車用サンシェードを日傘/ファッション用品と誤認しない。
    def test_car_sunshade_is_not_mistaken_for_a_parasol_or_fashion_item(self):
        item = make_item(name=self.CAR_SUNSHADE_NAME)
        description = dg.generate_description(item, category="ファッション", base_hashtags=BASE_HASHTAGS)
        self.assertIn("サンシェード", description)
        self.assertNotIn("日傘", description)
        self.assertNotIn("普段のおでかけに取り入れやすいアイテム◎", description)

    # 5. 「10本骨」を10個セットと誤認しない。
    def test_car_sunshade_rib_count_is_not_mistaken_for_product_quantity(self):
        item = make_item(name=self.CAR_SUNSHADE_NAME)
        description = dg.generate_description(item, category="ファッション", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("10個セット", description)
        self.assertNotIn("10本で使いやすい", description)

    # 6. 乾麺そばを汎用食品だけで終わらせない。
    def test_dried_soba_is_not_only_generic_food(self):
        for name in (self.YAKUNO_SOBA_NAME, self.NAGANO_SOBA_NAME):
            item = make_item(name=name)
            description = dg.generate_description(item, category="食品", base_hashtags=BASE_HASHTAGS)
            self.assertIn("そば", description)
            self.assertNotIn("手軽に楽しめそうな食品◎", description)
            self.assertNotIn("ストックしておきたい食品◎", description)

    # 7. 折りたたみ傘を正しく判定する。
    def test_folding_umbrella_is_recognized_correctly(self):
        item = make_item(name=self.FOLDING_UMBRELLA_NAME)
        description = dg.generate_description(item, category="ファッション", base_hashtags=BASE_HASHTAGS)
        self.assertIn("折りたたみ傘", description)
        self.assertNotIn("普段のおでかけに取り入れやすいアイテム◎", description)

    # 8. 「260g超軽量」は明示された商品重量として使用できる。
    def test_folding_umbrella_260g_is_confirmed_as_product_weight(self):
        item = make_item(name=self.FOLDING_UMBRELLA_NAME)
        description = dg.generate_description(item, category="ファッション", base_hashtags=BASE_HASHTAGS)
        self.assertIn("重さは約260g", description)

    # 9. 「10本骨」「12本骨」を数量セットと誤認しない。
    def test_folding_umbrella_rib_counts_are_not_mistaken_for_product_quantity(self):
        item = make_item(name=self.FOLDING_UMBRELLA_NAME)
        description = dg.generate_description(item, category="ファッション", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("10本で使いやすい", description)
        self.assertNotIn("12本で使いやすい", description)
        self.assertNotIn("10本骨", description)
        self.assertNotIn("12本骨", description)

    # 10. ほこり取りスポンジを食器洗いスポンジと誤認しない。
    def test_dust_sponge_is_not_mistaken_for_a_dishwashing_sponge(self):
        item = make_item(name=self.DUST_SPONGE_NAME)
        description = dg.generate_description(item, category="掃除", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("食器洗い", description)
        self.assertTrue(
            any(keyword in description for keyword in ("ほこり取り", "ダスタースポンジ", "掃除スポンジ", "ホコリ")),
            description,
        )

    # 11. 商品タイプを確定できないペット商品は、暮らし用品ではなく
    # ペット用品へ安全にフォールバックする。
    def test_unclear_pet_products_fall_back_to_pet_goods_not_generic_life_goods(self):
        for name in (self.UNKNOWN_SENIOR_DOG_NAME, self.UNKNOWN_PET_TOY_NAME):
            item = make_item(name=name)
            description = dg.generate_description(item, category="ペット用品", base_hashtags=BASE_HASHTAGS)
            self.assertNotIn("そんな暮らしの小さな不便を解消してくれそうな便利グッズ", description)
            self.assertIn("ペット", description)

    # 12. 商品タイプを確定できないペット商品を、勝手に「ドッグフード」
    # 「犬用おもちゃ」等と断定しない。
    def test_unclear_pet_products_do_not_get_a_fabricated_specific_type(self):
        senior_dog_description = dg.generate_description(
            make_item(name=self.UNKNOWN_SENIOR_DOG_NAME), category="ペット用品", base_hashtags=BASE_HASHTAGS
        )
        self.assertNotIn("ドッグフード", senior_dog_description)
        self.assertNotIn("重さは約12kg", senior_dog_description)

        pet_toy_description = dg.generate_description(
            make_item(name=self.UNKNOWN_PET_TOY_NAME), category="ペット用品", base_hashtags=BASE_HASHTAGS
        )
        for phrase in ("犬用おもちゃ", "噛むおもちゃ"):
            self.assertNotIn(phrase, pet_toy_description)

    # 13. 「54枚×15個」→「54枚入り×15個・計810枚」という、数量の意味を
    # 保持した自然な表現になる。
    def test_baby_wipes_compound_quantity_with_explicit_total_is_kept(self):
        item = make_item(name=self.BABY_WIPES_810_NAME)
        description = dg.generate_description(item, category="ベビー用品", base_hashtags=BASE_HASHTAGS)
        self.assertIn("54枚入り×15個・計810枚", description)
        self.assertNotIn("54枚入り×15個で使いやすい", description)

    # 14. 過去の「80枚×40個」等の複合数量判定を壊さない（回帰確認）。
    def test_previous_compound_quantity_without_explicit_total_still_works(self):
        item = make_item(name=self.OLD_BABY_WIPES_NAME)
        description = dg.generate_description(item, category="ベビー用品", base_hashtags=BASE_HASHTAGS)
        self.assertIn("80枚入り×40個で使いやすい", description)

    # 15. 具体的商品タイプが判定できる商品には、旧
    # #暮らしの便利グッズ／#便利グッズ を付けない。
    def test_new_product_types_do_not_get_mechanical_kurashi_hashtags(self):
        expectations = {
            self.HIP_SEAT_NAME: ("収納", "#ヒップシート"),
            self.MILK_WARMER_NAME: ("ベビー用品", "#ミルクウォーマー"),
            self.CAR_SUNSHADE_NAME: ("ファッション", "#サンシェード"),
            self.YAKUNO_SOBA_NAME: ("食品", "#そば"),
            self.FOLDING_UMBRELLA_NAME: ("ファッション", "#折りたたみ傘"),
            self.NAGANO_SOBA_NAME: ("食品", "#そば"),
            self.DUST_SPONGE_NAME: ("掃除", "#ほこり取り"),
        }
        for name, (category, expected_tag) in expectations.items():
            item = make_item(name=name)
            description = dg.generate_description(item, category=category, base_hashtags=BASE_HASHTAGS)
            hashtag_line = description.split("\n\n")[-1]
            self.assertIn(expected_tag, hashtag_line, description)
            self.assertNotIn("#暮らしの便利グッズ", hashtag_line)
            self.assertNotIn("#便利グッズ", hashtag_line)
            self.assertLessEqual(len(description), 500)


class DescriptionGenre009RegressionTest(unittest.TestCase):
    """2026-09-28 15:51生成分の最終調整（description-genre-009）の回帰
    テスト。①ペット用品の安全フォールバックで対象動物（犬・猫）を推測
    しないこと、②ペット用品フォールバックの旧ハッシュタグ削除、
    ③ヒップシートの効果表現の安全化、④「◯人前」の数量表現の自然化、
    を確認する。商品名はSept28BatchRegressionTestと同じ、本番で実際に
    取得された表記を再利用する。"""

    UNKNOWN_SENIOR_DOG_NAME = Sept28BatchRegressionTest.UNKNOWN_SENIOR_DOG_NAME
    UNKNOWN_PET_TOY_NAME = Sept28BatchRegressionTest.UNKNOWN_PET_TOY_NAME
    HIP_SEAT_NAME = Sept28BatchRegressionTest.HIP_SEAT_NAME
    YAKUNO_SOBA_NAME = Sept28BatchRegressionTest.YAKUNO_SOBA_NAME
    NAGANO_SOBA_NAME = Sept28BatchRegressionTest.NAGANO_SOBA_NAME
    BABY_WIPES_810_NAME = Sept28BatchRegressionTest.BABY_WIPES_810_NAME
    OLD_BABY_WIPES_NAME = Sept28BatchRegressionTest.OLD_BABY_WIPES_NAME

    # 1. 高齢犬用商品に「愛猫」を追加しない。
    def test_senior_dog_product_does_not_add_cat_wording(self):
        item = make_item(name=self.UNKNOWN_SENIOR_DOG_NAME)
        description = dg.generate_description(item, category="ペット用品", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("愛猫", description)
        self.assertNotIn("猫", description)
        self.assertIn("愛犬", description)

    # 2. 対象動物不明のペット用品に犬/猫を勝手に追加しない。
    def test_unclear_pet_product_does_not_guess_the_target_animal(self):
        item = make_item(name=self.UNKNOWN_PET_TOY_NAME)
        description = dg.generate_description(item, category="ペット用品", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("愛犬", description)
        self.assertNotIn("愛猫", description)

    # 3. タイトルに「犬用」と明記された場合のみ犬表現を許可する。
    def test_dog_wording_is_used_only_when_title_confirms_it(self):
        confirmed_description = dg.generate_description(
            make_item(name=self.UNKNOWN_SENIOR_DOG_NAME), category="ペット用品", base_hashtags=BASE_HASHTAGS
        )
        self.assertIn("愛犬", confirmed_description)

        unconfirmed_description = dg.generate_description(
            make_item(name=self.UNKNOWN_PET_TOY_NAME), category="ペット用品", base_hashtags=BASE_HASHTAGS
        )
        self.assertNotIn("愛犬", unconfirmed_description)

    # 4. タイトルに「猫用」と明記された場合のみ猫表現を許可する
    # （汎用的な仕組みの確認：猫用商品を仮定してテストする）。
    def test_cat_wording_is_used_only_when_title_confirms_it(self):
        item = make_item(name="キャットフード 猫用 国産 1kg")
        description = dg.generate_description(item, category="ペット用品", base_hashtags=BASE_HASHTAGS)
        self.assertIn("愛猫", description)
        self.assertNotIn("愛犬", description)

    # 5. ペット用品フォールバックに#暮らしの便利グッズを付けない。
    def test_pet_fallback_does_not_get_mechanical_kurashi_hashtag(self):
        for name in (self.UNKNOWN_SENIOR_DOG_NAME, self.UNKNOWN_PET_TOY_NAME):
            item = make_item(name=name)
            description = dg.generate_description(item, category="ペット用品", base_hashtags=BASE_HASHTAGS)
            hashtag_line = description.split("\n\n")[-1]
            self.assertNotIn("#暮らしの便利グッズ", hashtag_line)

    # 6. ペット用品フォールバックに#便利グッズを付けない。
    def test_pet_fallback_does_not_get_mechanical_benri_hashtag(self):
        for name in (self.UNKNOWN_SENIOR_DOG_NAME, self.UNKNOWN_PET_TOY_NAME):
            item = make_item(name=name)
            description = dg.generate_description(item, category="ペット用品", base_hashtags=BASE_HASHTAGS)
            hashtag_line = description.split("\n\n")[-1]
            self.assertNotIn("#便利グッズ", hashtag_line)
            self.assertIn("#ペット用品", hashtag_line)

    # 7. ヒップシートで負担軽減効果を断定しない。
    def test_hip_seat_does_not_claim_reduced_burden(self):
        item = make_item(name=self.HIP_SEAT_NAME)
        description = dg.generate_description(item, category="収納", base_hashtags=BASE_HASHTAGS)
        for phrase in ("負担を軽く", "腰痛を改善", "腰への負担を軽減", "腕への負担を軽減"):
            self.assertNotIn(phrase, description)
        self.assertIn("ヒップシート", description)

    # 8. ヒップシート20kgを商品重量にしない（回帰確認）。
    def test_hip_seat_20kg_is_still_not_treated_as_product_weight(self):
        item = make_item(name=self.HIP_SEAT_NAME)
        description = dg.generate_description(item, category="収納", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("重さは約20kg", description)

    # 9. 「6人前」→「6人前で使いやすい」にしない。
    def test_yakuno_soba_servings_does_not_add_generic_usability_phrase(self):
        item = make_item(name=self.YAKUNO_SOBA_NAME)
        description = dg.generate_description(item, category="食品", base_hashtags=BASE_HASHTAGS)
        self.assertIn("6人前", description)
        self.assertNotIn("6人前で使いやすい", description)

    # 10. 「4人前」→「4人前で使いやすい」にしない。
    def test_nagano_soba_servings_does_not_add_generic_usability_phrase(self):
        item = make_item(name=self.NAGANO_SOBA_NAME)
        description = dg.generate_description(item, category="食品", base_hashtags=BASE_HASHTAGS)
        self.assertIn("4人前", description)
        self.assertNotIn("4人前で使いやすい", description)

    # 11. 過去の複合数量表現（170g×4袋・計8人前、54枚入り×15個・計810枚、
    # 80枚入り×40個）を壊さない（回帰確認）。
    def test_previous_compound_quantity_expressions_still_work(self):
        udon_description = dg.generate_description(
            make_item(
                name=(
                    "ひもかわうどん 帯麺 乾麺 めん170g × 4袋 8人前 濃縮つゆ8人前 送料無料 ひも川 "
                    "通販 人気【ポスト投函配送】"
                )
            ),
            category="食品",
            base_hashtags=BASE_HASHTAGS,
        )
        self.assertIn("170g × 4袋・計8人前", udon_description)

        new_wipes_description = dg.generate_description(
            make_item(name=self.BABY_WIPES_810_NAME), category="ベビー用品", base_hashtags=BASE_HASHTAGS
        )
        self.assertIn("54枚入り×15個・計810枚", new_wipes_description)

        old_wipes_description = dg.generate_description(
            make_item(name=self.OLD_BABY_WIPES_NAME), category="ベビー用品", base_hashtags=BASE_HASHTAGS
        )
        self.assertIn("80枚入り×40個で使いやすい", old_wipes_description)


class Sept29BatchRegressionTest(unittest.TestCase):
    """2026-09-29 15:50生成分のroom/data/candidates.jsonで実際に見つかった、
    商品本体判定の誤り（description-genre-010）の回帰テスト。「レビュー
    特典」「用途語」「複合語の一部分」を商品本体と誤認しないこと、数値の
    意味（幅・高さ・耐荷重の区別、数量1個の扱い、選択肢の並び）を正しく
    扱うことを確認する。商品名は本番で実際に取得された表記をそのまま
    使っている。"""

    BEDWETTING_PANTS_NAME = (
        "楽天No.1 おねしょ ズボン 秋 小学生 完全防水 夏素材 おねしょズボン 保育園 防水 パンツ "
        "ケット 子ども 子供 こども 女の子 男の子 冬 漏れない パジャマ トレーニングパンツ トイトレ "
        "綿100% おねしょパンツ"
    )
    MEAL_APRON_NAME = (
        "【人気カラー在庫復活！】 テマロン スタイ お食事エプロン 長袖 食べこぼし 離乳食 掴み食べ "
        "ベビーエプロン 保育園 撥水 大きめ 男の子 女の子 赤ちゃん おしゃれ BLW 子供用 幼児 "
        "ベビー用品 出産祝い 送料無料"
    )
    COOLER_BAG_NAME = (
        "【楽天デイリー1位】【Makuake公式】 保冷バッグ ORIBA ふろしき 保冷 保温 ふろしき 風呂敷 "
        "買い物 アルミコート素材 接着力 耐久力 冷たさ持続 衛生的 大容量 肉 魚 野菜 ドリンク "
        "乳製品 刺身 アイス 冷凍食品 お弁当 洗濯機 プレゼント ギフト Makuake マクアケ"
    )
    MOTSUNI_NAME = (
        "国産豚のもつ煮 3袋 10袋 20袋　レトルト 310g / 1袋 もつ煮込み 国産豚 もつ煮 レトルト "
        "モツ煮 お取り寄せ ギフト おつまみ 保存食 こんにゃく ピリ辛 惣菜 晩酌 家飲み ご飯のお供 "
        "1000円ポッキリ ビールに合う"
    )
    HANGER_RACK_NAME = (
        "業務用 ハンガーラック 組立不要 頑丈 幅90cm 耐荷重100kg 高さ180cm S-Class900 高耐荷重 "
        "コートハンガー 洋服掛け 衣類収納 大容量 パイプハンガー 店舗什器 什器 キャスター付き "
        "アパレル 大量収納 在庫管理 日本製 アイアン 溶接構造 スチール製 ハンガー什器 タフグラン"
    )
    LR41_SINGLE_NAME = "アルカリボタン電池（LR41）1個から販売 【送料無料 AG3/LR41 1.5V】"
    MULTI_CLOTH_NAME = (
        "〈10%OFFクーポンあり/3枚セット〉国内大手メーカー採用、汚れ拭き・吸水性・耐久性抜群 "
        "daily特注マルチクロス3枚セット キッチン 洗面所 鏡拭き 窓拭き 雑巾 テーブルダスター "
        "吸水性 速乾 水垢取り お掃除用品 北欧 おしゃれ マイクロファイバー お掃除クロス mukuri"
    )
    KITCHEN_SPONGE_SINGLE_NAME = (
        "【お試し・初回購入限定】太陽油脂　パックスナチュロン　キッチンスポンジ 1個入 "
        "PAX NATURONの束子・スポンジ ( 4904735053095 ) ※色は選べません ※本商品　初めての購入者"
        "限定価格　お一人様1回限り"
    )
    KITCHEN_TOOLS_SET_NAME = (
        "レビューでスポンジ【マーナ公式】キッチンツール 5点セット食洗機対応 シリコン 耐熱 菜ばし "
        "トング お玉 フライ返し スプーンヘラ 調理スプーン 壁掛け 吊り下げ 収納 使いやすい "
        "おしゃれ かわいい キッチン 便利グッズ 調理器具 一人暮らし 新生活 ギフト X162"
    )

    # 1. おねしょズボンを汎用ベビー用品だけで終わらせない。
    def test_bedwetting_pants_is_not_only_generic_baby_goods(self):
        item = make_item(name=self.BEDWETTING_PANTS_NAME)
        description = dg.generate_description(item, category="ベビー用品", base_hashtags=BASE_HASHTAGS)
        self.assertIn("おねしょ", description)
        self.assertNotIn("赤ちゃんとの暮らしに取り入れやすいベビー用品◎", description)

    # 2. おねしょズボンを赤ちゃん専用と決めつけない。
    def test_bedwetting_pants_does_not_assume_babies_only(self):
        item = make_item(name=self.BEDWETTING_PANTS_NAME)
        description = dg.generate_description(item, category="ベビー用品", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("赤ちゃんとの暮らし", description)
        for phrase in ("絶対に漏れない", "完全に防げる"):
            self.assertNotIn(phrase, description)

    # 3. お食事エプロンを具体的に判定する。
    def test_meal_apron_is_recognized_specifically(self):
        item = make_item(name=self.MEAL_APRON_NAME)
        description = dg.generate_description(item, category="ベビー用品", base_hashtags=BASE_HASHTAGS)
        self.assertTrue("スタイ" in description or "エプロン" in description)
        self.assertNotIn("赤ちゃんとの暮らしに取り入れやすいベビー用品◎", description)

    # 4. 保冷バッグを汎用ファッションと誤認しない。
    def test_cooler_bag_is_not_mistaken_for_generic_fashion_item(self):
        item = make_item(name=self.COOLER_BAG_NAME)
        description = dg.generate_description(item, category="ファッション", base_hashtags=BASE_HASHTAGS)
        self.assertIn("保冷", description)
        self.assertNotIn("普段のおでかけに取り入れやすいアイテム◎", description)
        self.assertNotIn("天気や気温で困ることがあります", description)

    # 5. もつ煮を具体的食品として判定する。
    def test_motsuni_is_recognized_as_a_specific_food(self):
        item = make_item(name=self.MOTSUNI_NAME)
        description = dg.generate_description(item, category="食品", base_hashtags=BASE_HASHTAGS)
        self.assertIn("もつ煮", description)
        self.assertNotIn("手軽に楽しめそうな食品◎", description)

    # 6. 3袋/10袋/20袋を選択肢として扱う。
    def test_motsuni_bag_options_are_treated_as_choices(self):
        item = make_item(name=self.MOTSUNI_NAME)
        description = dg.generate_description(item, category="食品", base_hashtags=BASE_HASHTAGS)
        self.assertIn("3袋・10袋・20袋から選べる", description)
        self.assertNotIn("3袋セット", description)

    # 7. 「310g / 1袋」の意味を壊さない（3袋×310gのように勝手に計算
    # しない）。
    def test_motsuni_per_bag_weight_is_not_multiplied(self):
        phrase = dg._extract_quantity_phrase(self.MOTSUNI_NAME)
        self.assertEqual(phrase, "3袋 10袋 20袋")
        item = make_item(name=self.MOTSUNI_NAME)
        description = dg.generate_description(item, category="食品", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("930g", description)

    # 8. ハンガーラックをハンガーと誤認しない。
    def test_hanger_rack_is_not_mistaken_for_a_plain_hanger(self):
        item = make_item(name=self.HANGER_RACK_NAME)
        description = dg.generate_description(item, category="収納", base_hashtags=BASE_HASHTAGS)
        self.assertIn("ハンガーラック", description)
        self.assertNotIn("衣類が滑りにくく、まとめて揃えやすいハンガー◎", description)

    # 9. 幅90cm / 高さ180cm / 耐荷重100kgを区別する。
    def test_hanger_rack_dimensions_are_distinguished(self):
        item = make_item(name=self.HANGER_RACK_NAME)
        description = dg.generate_description(item, category="収納", base_hashtags=BASE_HASHTAGS)
        self.assertIn("幅90cm・高さ180cm", description)
        self.assertIn("耐荷重100kg", description)
        self.assertNotIn("サイズは約90cm", description)

    # 10. 耐荷重100kgを商品重量と誤認しない。
    def test_hanger_rack_load_capacity_is_not_mistaken_for_product_weight(self):
        item = make_item(name=self.HANGER_RACK_NAME)
        description = dg.generate_description(item, category="収納", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("重さは約100kg", description)

    # 11. LR41の「1個」を「1個セット」にしない。
    def test_lr41_single_unit_is_not_expressed_as_a_set(self):
        item = make_item(name=self.LR41_SINGLE_NAME)
        description = dg.generate_description(item, category="健康", base_hashtags=BASE_HASHTAGS)
        self.assertIn("1個", description)
        self.assertNotIn("1個セット", description)

    # 12. マルチクロスを研磨シートと誤認しない。
    def test_multi_cloth_is_not_mistaken_for_an_abrasive_sheet(self):
        item = make_item(name=self.MULTI_CLOTH_NAME)
        description = dg.generate_description(item, category="掃除", base_hashtags=BASE_HASHTAGS)
        self.assertIn("マルチクロス", description)
        self.assertNotIn("お手入れシート◎", description)

    # 13. タイトルにない「研磨」を生成しない。
    def test_multi_cloth_does_not_generate_unconfirmed_abrasive_claim(self):
        item = make_item(name=self.MULTI_CLOTH_NAME)
        description = dg.generate_description(item, category="掃除", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("研磨", description)

    # 14. キッチンスポンジ「1個入」を「1個セット」にしない。
    def test_kitchen_sponge_single_unit_is_not_expressed_as_a_set(self):
        item = make_item(name=self.KITCHEN_SPONGE_SINGLE_NAME)
        description = dg.generate_description(item, category="キッチン消耗品", base_hashtags=BASE_HASHTAGS)
        self.assertIn("1個入", description)
        self.assertNotIn("1個セット", description)

    # 15. レビュー特典のスポンジを商品本体と誤認しない。
    def test_review_incentive_sponge_is_not_mistaken_for_the_product_itself(self):
        item = make_item(name=self.KITCHEN_TOOLS_SET_NAME)
        description = dg.generate_description(item, category="キッチン", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("食器洗いに使いやすいキッチン用スポンジ◎", description)

    # 16. マーナの商品をキッチンツール5点セットとして判定する。
    def test_marna_product_is_recognized_as_a_kitchen_tools_set(self):
        item = make_item(name=self.KITCHEN_TOOLS_SET_NAME)
        description = dg.generate_description(item, category="キッチン", base_hashtags=BASE_HASHTAGS)
        self.assertIn("キッチンツール", description)

    # 17. 本物のスポンジ商品は引き続きスポンジとして判定する（回帰確認）。
    def test_genuine_sponge_product_is_still_recognized_as_a_sponge(self):
        self.assertEqual(dg.match_product_type_keyword(self.KITCHEN_SPONGE_SINGLE_NAME), "スポンジ")
        item = make_item(name=self.KITCHEN_SPONGE_SINGLE_NAME)
        description = dg.generate_description(item, category="キッチン消耗品", base_hashtags=BASE_HASHTAGS)
        self.assertIn("スポンジ", description)

    # 18. 具体的商品タイプに旧#暮らしの便利グッズ/#便利グッズを付けない。
    def test_new_product_types_do_not_get_mechanical_kurashi_hashtags(self):
        expectations = {
            self.BEDWETTING_PANTS_NAME: ("ベビー用品", "#おねしょズボン"),
            self.MEAL_APRON_NAME: ("ベビー用品", "#お食事エプロン"),
            self.COOLER_BAG_NAME: ("ファッション", "#保冷バッグ"),
            self.MOTSUNI_NAME: ("食品", "#もつ煮"),
            self.HANGER_RACK_NAME: ("収納", "#ハンガーラック"),
            self.MULTI_CLOTH_NAME: ("掃除", "#マルチクロス"),
            self.KITCHEN_SPONGE_SINGLE_NAME: ("キッチン消耗品", "#キッチンスポンジ"),
            self.KITCHEN_TOOLS_SET_NAME: ("キッチン", "#キッチンツール"),
        }
        for name, (category, expected_tag) in expectations.items():
            item = make_item(name=name)
            description = dg.generate_description(item, category=category, base_hashtags=BASE_HASHTAGS)
            hashtag_line = description.split("\n\n")[-1]
            self.assertIn(expected_tag, hashtag_line, description)
            self.assertNotIn("#暮らしの便利グッズ", hashtag_line)
            self.assertNotIn("#便利グッズ", hashtag_line)
            self.assertLessEqual(len(description), 500)

    # 19. 稲庭うどんの商品タイプ・数量・ハッシュタグを壊さない（回帰確認）。
    def test_inaniwa_udon_regression_is_preserved(self):
        item = make_item(
            name=(
                "【オシャレパッケージでお届け】稲庭うどん プチギフト 送料無料 メール便 ポスト投函 "
                "うどん 乾麺 グルメ お取り寄せ 稲庭うどん（6人前） 無限堂 秋田 おしゃれ パッケージ "
                "贈答品 御礼 ご挨拶 気軽 手軽 お返し ご当地グルメ プレゼント 稲庭うどん"
            )
        )
        description = dg.generate_description(item, category="食品", base_hashtags=BASE_HASHTAGS)
        self.assertIn("うどん", description)
        self.assertIn("6人前", description)
        self.assertNotIn("6人前で使いやすい", description)
        hashtag_line = description.split("\n\n")[-1]
        self.assertIn("#グルメ", hashtag_line)
        self.assertIn("#うどん", hashtag_line)


class Sept29FinalReviewFixTest(unittest.TestCase):
    """2026-09-29 15:50生成分の最終確認で残った3点（おねしょズボンの
    「水回りでも使いやすい」・もつ煮の未確認な「温めるだけ」・ハンガー
    ラックの幅/高さ/耐荷重の表現）を修正したことを確認する。それ以外の
    7商品のdescriptionは変更していないことも合わせて確認する。"""

    BEDWETTING_PANTS_NAME = Sept29BatchRegressionTest.BEDWETTING_PANTS_NAME
    MOTSUNI_NAME = Sept29BatchRegressionTest.MOTSUNI_NAME
    HANGER_RACK_NAME = Sept29BatchRegressionTest.HANGER_RACK_NAME
    MEAL_APRON_NAME = Sept29BatchRegressionTest.MEAL_APRON_NAME
    COOLER_BAG_NAME = Sept29BatchRegressionTest.COOLER_BAG_NAME
    LR41_SINGLE_NAME = Sept29BatchRegressionTest.LR41_SINGLE_NAME
    MULTI_CLOTH_NAME = Sept29BatchRegressionTest.MULTI_CLOTH_NAME
    KITCHEN_SPONGE_SINGLE_NAME = Sept29BatchRegressionTest.KITCHEN_SPONGE_SINGLE_NAME
    KITCHEN_TOOLS_SET_NAME = Sept29BatchRegressionTest.KITCHEN_TOOLS_SET_NAME

    # 1. おねしょズボンに「水回りでも使いやすい」が出ない。
    def test_bedwetting_pants_does_not_mention_water_areas(self):
        item = make_item(name=self.BEDWETTING_PANTS_NAME)
        description = dg.generate_description(item, category="ベビー用品", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("水回りでも使いやすい", description)
        self.assertIn("おねしょ", description)

    # 2. もつ煮に根拠のない「温めるだけ」が出ない。
    def test_motsuni_does_not_claim_unconfirmed_cooking_method(self):
        item = make_item(name=self.MOTSUNI_NAME)
        description = dg.generate_description(item, category="食品", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("温めるだけ", description)
        self.assertIn("もつ煮", description)

    # 3. もつ煮の3袋・10袋・20袋の選択肢表現を維持する（回帰確認）。
    def test_motsuni_size_options_phrase_is_preserved(self):
        item = make_item(name=self.MOTSUNI_NAME)
        description = dg.generate_description(item, category="食品", base_hashtags=BASE_HASHTAGS)
        self.assertIn("3袋・10袋・20袋から選べる", description)
        self.assertNotIn("930g", description)

    # 4. ハンガーラックの90cmを幅として扱う。
    def test_hanger_rack_90cm_is_treated_as_width(self):
        item = make_item(name=self.HANGER_RACK_NAME)
        description = dg.generate_description(item, category="収納", base_hashtags=BASE_HASHTAGS)
        self.assertIn("幅90cm", description)

    # 5. ハンガーラックの180cmを高さとして扱う。
    def test_hanger_rack_180cm_is_treated_as_height(self):
        item = make_item(name=self.HANGER_RACK_NAME)
        description = dg.generate_description(item, category="収納", base_hashtags=BASE_HASHTAGS)
        self.assertIn("高さ180cm", description)

    # 6. ハンガーラックの100kgを耐荷重として扱う。
    def test_hanger_rack_100kg_is_treated_as_load_capacity(self):
        item = make_item(name=self.HANGER_RACK_NAME)
        description = dg.generate_description(item, category="収納", base_hashtags=BASE_HASHTAGS)
        self.assertIn("耐荷重100kg", description)

    # 7. ハンガーラックの100kgを商品重量として扱わない。
    def test_hanger_rack_100kg_is_not_treated_as_product_weight(self):
        item = make_item(name=self.HANGER_RACK_NAME)
        description = dg.generate_description(item, category="収納", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("重さは約100kg", description)

    # 8. ハンガーラックに根拠のない「約」を付けない（原文どおり「幅90cm」）。
    def test_hanger_rack_dimensions_do_not_add_unconfirmed_approximation(self):
        item = make_item(name=self.HANGER_RACK_NAME)
        description = dg.generate_description(item, category="収納", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("幅は約90cm", description)
        self.assertNotIn("高さは約180cm", description)

    # 9. ハンガーラックは耐荷重100kgを「必ず安全」等の保証表現に拡大しない。
    def test_hanger_rack_load_capacity_is_not_expanded_into_a_guarantee(self):
        item = make_item(name=self.HANGER_RACK_NAME)
        description = dg.generate_description(item, category="収納", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("必ず", description)
        self.assertNotIn("安全", description)

    # 10. 正しい7商品のdescriptionが変わらない（回帰確認）。
    def test_seven_already_correct_items_are_unchanged(self):
        cases = [
            (self.MEAL_APRON_NAME, "ベビー用品", "#お食事エプロン"),
            (self.COOLER_BAG_NAME, "ファッション", "#保冷バッグ"),
            (self.LR41_SINGLE_NAME, "健康", None),
            (self.MULTI_CLOTH_NAME, "掃除", "#マルチクロス"),
            (self.KITCHEN_SPONGE_SINGLE_NAME, "キッチン消耗品", "#キッチンスポンジ"),
            (self.KITCHEN_TOOLS_SET_NAME, "キッチン", "#キッチンツール"),
        ]
        for name, category, expected_tag in cases:
            item = make_item(name=name)
            description = dg.generate_description(item, category=category, base_hashtags=BASE_HASHTAGS)
            first = dg.generate_description(item, category=category, base_hashtags=BASE_HASHTAGS)
            self.assertEqual(description, first)
            if expected_tag:
                self.assertIn(expected_tag, description)
        # LR41は「1個」を維持し、「1個セット」に戻らないことを個別に確認する。
        item = make_item(name=self.LR41_SINGLE_NAME)
        description = dg.generate_description(item, category="健康", base_hashtags=BASE_HASHTAGS)
        self.assertIn("1個", description)
        self.assertNotIn("1個セット", description)
        # マーナのキッチンツールがスポンジへ戻っていないことを確認する。
        item = make_item(name=self.KITCHEN_TOOLS_SET_NAME)
        description = dg.generate_description(item, category="キッチン", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("食器洗いに使いやすいキッチン用スポンジ◎", description)
        # マルチクロスが研磨シートへ戻っていないことを確認する。
        item = make_item(name=self.MULTI_CLOTH_NAME)
        description = dg.generate_description(item, category="掃除", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("研磨", description)


class Sept30BatchRegressionTest(unittest.TestCase):
    """2026-09-30 15:51生成分の商品名で、商品本体判定をAPI側categoryより
    優先する一般化（description-genre-012）を確認する。商品名は本番で
    実際に取得された表記をそのまま使っている。"""

    SOAP_SCUM_SCRAPER_NAME = (
        "【錫村商店公式】石鹸カス 落とし ヘラ スクレーパー 掃除道具 浴室 湯垢 ヌメリ【落ちない石鹸カスに】"
        "根岸棒｜削って除去 プロ仕様 業務用"
    )
    SOBA_TEA_NAME = (
        "国産 韃靼そば茶 5g x 50p（250g 大容量 ティーバッグ） ほんぢ園 ＜ペットボトルよりお得 蕎麦茶 "
        "ダッタンそば茶 だったんそばちゃ 韃靼そばちゃ だったんそば茶 韃靼そば ルチン ノンカフェイン "
        "そば茶国産＞送料無料【LC】／セ／●"
    )
    FACE_ROLLER_NAME = (
        "【公式】鍼 マッサージ フェイスローラー ボディ 頭皮ケア ブラシ 血行促進 むくみ 胸鎖乳突筋美顔器 "
        "リフトアップ ほうれい線 コロコロ 鍼 小顔 たるみ 充電不要 ギフト プレゼント HALIFT （ハリフト）シリーズ"
    )
    BABY_PILLOW_NAME = (
        "【楽天1位】絶壁防止枕 ベビー枕 洗える 吐き戻し防止 赤ちゃん 枕 まくら 絶壁防止 出産祝い ベビー用品 "
        "ベビー 絶壁 枕 三面調節 通気性抜群 丸洗い 新生児 0ヶ月 向き癖防止 高さ調節 子供 ベビーピロー "
        "向き癖丸い頭 ベビーまくら 通気 睡眠サポート"
    )
    HAND_SPINNER_NAME = (
        "2026年【TV紹介品】 ギフト無料 Polaristure 【正規品】くるくるスピンフレンド ハンドスピナー 赤ちゃん "
        "お風呂 おもちゃ 赤ちゃん おもちゃ 0歳 固定バンドでベビーカーOK 【食品衛生法試験合格】 "
        "蝶/てんとう虫/ハチ 3点セット 箱付き"
    )
    HAMBURG_NAME = (
        "【33%OFFクーポン！9/30〜10/1】【楽天グルメ大賞受賞】ふるさと納税で大人気 累計4000万個突破！"
        "食の便利屋きよかわ デミソース ハンバーグ 湯煎 鉄板焼 ハンバーグ 130g×10個/20個 温めるだけ 冷凍 "
        "美味しい 小分け 大容量 冷凍食品 レトルト"
    )
    BEEF_TENDON_CURRY_NAME = (
        "【レトルトでは味わえない本格カレー】じっくり煮込んだ牛すじの旨味がたっぷりとろけた、"
        "ちょっとスパイシーな専門店のコク旨牛すじカレー！牛すじカレー専門店「戸紀屋」のこだわり"
        "牛すじカレー 3パックセット"
    )
    PVC_HANGER_NAME = (
        "極太PVCコーティング 滑らないハンガー 30本セット （軽くて丈夫！衣類が滑らず、かさばらないから"
        "クローゼットもスッキリの便利なハンガー） 10本単位で選べる16色 収納 洋服 和服 軽い 軽量 洗濯 "
        "外干し 部屋干し ステンレス ランドリー 上着 ジャケット コート スーツ"
    )
    HYPOCHLOROUS_WATER_NAME = (
        "サライウォーター2L 次亜塩素酸水 除菌 消臭【7/8リアルタイムランキング1位】次亜塩素酸 無害 "
        "消臭除菌水 靴 塩素 臭い キッチン 犬 猫 ペット臭 衛生 子ども たばこ 靴 嘔吐処理 スプレー トイレ臭 "
        "におい カビ 汗臭 消臭剤 除菌剤 即送 遮光袋付 空間除菌 ギフト容器"
    )
    DESK_FAN_NAME = (
        "【楽天総合ランキング1位】【正規品】【予約受付中】卓上扇風機 South Light 扇風機 壁掛け 吊り下げ "
        "マグネットリモコン付き LED照明機能付き 1台3役 サーキュレーター USB充電 風量3段階 パワフル送風 "
        "ギフト i-00004"
    )

    # 1. 石鹸カス用スクレーパーを具体的に判定する。
    def test_soap_scum_scraper_is_recognized_specifically(self):
        item = make_item(name=self.SOAP_SCUM_SCRAPER_NAME)
        description = dg.generate_description(item, category="掃除", base_hashtags=BASE_HASHTAGS)
        self.assertTrue("石鹸カス" in description or "スクレーパー" in description)
        self.assertNotIn("そんな掃除の手間を減らしてくれそうな掃除グッズ◎", description)

    # 2. 「業務用」だけで大容量/大型/たっぷりを生成しない。
    def test_gyoumuyou_does_not_generate_bulk_size_claim(self):
        item = make_item(name=self.SOAP_SCUM_SCRAPER_NAME)
        description = dg.generate_description(item, category="掃除", base_hashtags=BASE_HASHTAGS)
        for phrase in ("業務用サイズ", "大容量", "たっぷり", "大型"):
            self.assertNotIn(phrase, description, description)

    # 3. 韃靼そば茶5g×50Pを商品重量5gにしない。
    def test_soba_tea_5g_is_not_mistaken_for_product_weight(self):
        item = make_item(name=self.SOBA_TEA_NAME)
        description = dg.generate_description(item, category="お茶", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("重さは約5g", description)

    # 4. 5g×50包・計250gの意味を区別する。
    def test_soba_tea_pack_and_total_are_distinguished(self):
        item = make_item(name=self.SOBA_TEA_NAME)
        description = dg.generate_description(item, category="お茶", base_hashtags=BASE_HASHTAGS)
        self.assertIn("5g×50包", description)
        self.assertIn("計250g", description)

    # 5. category=掃除でもフェイスローラーを掃除用品にしない。
    def test_face_roller_is_not_treated_as_a_cleaning_product_despite_category(self):
        item = make_item(name=self.FACE_ROLLER_NAME)
        description = dg.generate_description(item, category="掃除", base_hashtags=BASE_HASHTAGS)
        self.assertIn("フェイスローラー", description)
        self.assertNotIn("そんな掃除の手間を減らしてくれそうな掃除グッズ◎", description)

    # 6. HALIFTで美容効果を断定しない。
    def test_face_roller_does_not_claim_beauty_effects(self):
        item = make_item(name=self.FACE_ROLLER_NAME)
        description = dg.generate_description(item, category="掃除", base_hashtags=BASE_HASHTAGS)
        for phrase in (
            "むくみが取れる", "小顔になる", "リフトアップする",
            "ほうれい線が消える", "血行が良くなる", "改善する",
        ):
            self.assertNotIn(phrase, description, description)

    # 7. ベビー枕を具体的に判定する。
    def test_baby_pillow_is_recognized_specifically(self):
        item = make_item(name=self.BABY_PILLOW_NAME)
        description = dg.generate_description(item, category="ベビー用品", base_hashtags=BASE_HASHTAGS)
        self.assertIn("枕", description)
        self.assertNotIn("赤ちゃんとの暮らしに取り入れやすいベビー用品◎", description)

    # 8. ベビー枕で身体効果を断定しない。
    def test_baby_pillow_does_not_claim_health_effects(self):
        item = make_item(name=self.BABY_PILLOW_NAME)
        description = dg.generate_description(item, category="ベビー用品", base_hashtags=BASE_HASHTAGS)
        for phrase in ("絶壁を防ぐ", "頭の形を改善する", "吐き戻しを防ぐ", "向き癖を治す"):
            self.assertNotIn(phrase, description, description)

    # 9. ハンドスピナーを具体的に判定する。
    def test_hand_spinner_is_recognized_specifically(self):
        item = make_item(name=self.HAND_SPINNER_NAME)
        description = dg.generate_description(item, category="ベビー用品", base_hashtags=BASE_HASHTAGS)
        self.assertIn("ハンドスピナー", description)
        self.assertNotIn("赤ちゃんとの暮らしに取り入れやすいベビー用品◎", description)

    # 10. 3点セットを正しく扱う。
    def test_hand_spinner_3_piece_set_is_handled_correctly(self):
        item = make_item(name=self.HAND_SPINNER_NAME)
        description = dg.generate_description(item, category="ベビー用品", base_hashtags=BASE_HASHTAGS)
        self.assertIn("3点セット", description)

    # 11. 130g×10個/20個を10個固定にしない。
    def test_hamburg_pack_count_options_are_not_fixed_to_one_value(self):
        item = make_item(name=self.HAMBURG_NAME)
        description = dg.generate_description(item, category="食品", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("130g×10個で使いやすい", description)
        self.assertIn("10個", description)
        self.assertIn("20個", description)

    # 12. 130gを1個あたりとして扱う。
    def test_hamburg_130g_is_treated_as_per_unit_amount(self):
        item = make_item(name=self.HAMBURG_NAME)
        description = dg.generate_description(item, category="食品", base_hashtags=BASE_HASHTAGS)
        self.assertIn("1個あたり130g", description)

    # 13. 牛すじカレーを具体的に判定する。
    def test_beef_tendon_curry_is_recognized_specifically(self):
        item = make_item(name=self.BEEF_TENDON_CURRY_NAME)
        description = dg.generate_description(item, category="食品", base_hashtags=BASE_HASHTAGS)
        self.assertIn("牛すじカレー", description)
        self.assertNotIn("ストックしておきたい食品◎", description)

    # 14. 「レトルトでは味わえない」をレトルト商品と誤認しない。
    def test_beef_tendon_curry_negation_context_is_not_misread_as_retort(self):
        item = make_item(name=self.BEEF_TENDON_CURRY_NAME)
        description = dg.generate_description(item, category="食品", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("温めるだけで食べられるレトルトカレー", description)

    # 15. ハンガー30本セットを維持する（回帰確認）。
    def test_pvc_hanger_30_pack_set_is_preserved(self):
        item = make_item(name=self.PVC_HANGER_NAME)
        description = dg.generate_description(item, category="収納", base_hashtags=BASE_HASHTAGS)
        self.assertIn("30本セット", description)
        self.assertIn("衣類が滑り落ちにくい", description)

    # 16. ハンガーの旧汎用タグを削除する。
    def test_pvc_hanger_old_generic_hashtags_are_removed(self):
        item = make_item(name=self.PVC_HANGER_NAME)
        description = dg.generate_description(item, category="収納", base_hashtags=BASE_HASHTAGS)
        hashtag_line = description.split("\n\n")[-1]
        self.assertIn("#ハンガー", hashtag_line)
        self.assertNotIn("#暮らしの便利グッズ", hashtag_line)
        self.assertNotIn("#便利グッズ", hashtag_line)

    # 17. category=キッチンでも次亜塩素酸水をキッチングッズにしない。
    def test_hypochlorous_water_is_not_treated_as_a_kitchen_product_despite_category(self):
        item = make_item(name=self.HYPOCHLOROUS_WATER_NAME)
        description = dg.generate_description(item, category="キッチン", base_hashtags=BASE_HASHTAGS)
        self.assertIn("次亜塩素酸水", description)
        self.assertNotIn("キッチングッズ", description)
        self.assertNotIn("料理や後片付けをラクにする", description)

    # 18. 2Lを商品容量として扱う。
    def test_hypochlorous_water_2l_is_treated_as_confirmed_volume(self):
        item = make_item(name=self.HYPOCHLOROUS_WATER_NAME)
        description = dg.generate_description(item, category="キッチン", base_hashtags=BASE_HASHTAGS)
        self.assertIn("容量は2L", description)
        self.assertNotIn("容量は約2L", description)

    # 19. 次亜塩素酸水で安全性/除菌効果を過剰断定しない。
    def test_hypochlorous_water_does_not_overclaim_safety_or_disinfection(self):
        item = make_item(name=self.HYPOCHLOROUS_WATER_NAME)
        description = dg.generate_description(item, category="キッチン", base_hashtags=BASE_HASHTAGS)
        for phrase in (
            "完全に無害", "人体に安全", "ペットに絶対安全", "病原体を確実に除去",
            "空間を完全除菌", "感染症予防",
        ):
            self.assertNotIn(phrase, description, description)

    # 20. 「マグネットリモコン付き」を本体マグネット設置と誤認しない。
    def test_desk_fan_magnet_remote_is_not_read_as_magnetic_mounting(self):
        item = make_item(name=self.DESK_FAN_NAME)
        description = dg.generate_description(item, category="収納", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("マグネットで取り付けられる", description)

    # 21. 扇風機の商品本体判定を維持する（回帰確認）。
    def test_desk_fan_product_type_is_preserved(self):
        item = make_item(name=self.DESK_FAN_NAME)
        description = dg.generate_description(item, category="収納", base_hashtags=BASE_HASHTAGS)
        self.assertIn("扇風機", description)
        hashtag_line = description.split("\n\n")[-1]
        self.assertIn("#扇風機", hashtag_line)

    # 22. 既存の特典語除外を壊さない（回帰確認）。
    def test_review_incentive_exclusion_is_preserved(self):
        name = (
            "レビューでスポンジ【マーナ公式】キッチンツール 5点セット食洗機対応 シリコン 耐熱 菜ばし "
            "トング お玉 フライ返し スプーンヘラ 調理スプーン 壁掛け 吊り下げ 収納 使いやすい おしゃれ "
            "かわいい キッチン 便利グッズ 調理器具 一人暮らし 新生活 ギフト X162"
        )
        item = make_item(name=name)
        description = dg.generate_description(item, category="キッチン", base_hashtags=BASE_HASHTAGS)
        self.assertIn("キッチンツール", description)
        self.assertNotIn("食器洗いに使いやすいキッチン用スポンジ◎", description)

    # 23. 既存の複数数量選択肢を壊さない（回帰確認）。
    def test_existing_multi_quantity_options_are_preserved(self):
        item = make_item(
            name="国産豚のもつ煮 3袋 10袋 20袋　レトルト 310g / 1袋 もつ煮込み 国産豚 もつ煮"
        )
        description = dg.generate_description(item, category="食品", base_hashtags=BASE_HASHTAGS)
        self.assertIn("3袋・10袋・20袋から選べる", description)
        self.assertNotIn("930g", description)


class NegationContextGeneralizationTest(unittest.TestCase):
    """商品本体判定の否定文脈除外（_NEGATION_MENTION_SUFFIX_PATTERN・
    _NEGATION_MENTION_PREFIX_PATTERN）が、特定商品の個別対応ではなく
    汎用的に機能することを確認する（description-genre-012対応）。"""

    def test_suffix_negation_dewa_nai_excludes_keyword(self):
        self.assertIsNone(dg.match_product_type_keyword("レトルトカレーではない専門店のこだわりカレー"))

    def test_suffix_negation_dewa_ajiwaenai_excludes_keyword(self):
        self.assertIsNone(
            dg.match_product_type_keyword("レトルトカレーでは味わえない専門店のこだわりカレー")
        )

    def test_prefix_negation_hi_excludes_keyword(self):
        self.assertIsNone(dg.match_product_type_keyword("非レトルトカレー的な専門店のカレー"))

    def test_positive_context_still_matches(self):
        self.assertEqual(
            dg.match_product_type_keyword("本格レトルトカレー 温めるだけ"), "レトルトカレー"
        )


class AccessoryAttributionGeneralizationTest(unittest.TestCase):
    """付属品の属性を商品本体の機能へ誤転写しない一般ルール
    （_ACCESSORY_NOUN_BEFORE_SUFFIX_PATTERN）が、扇風機以外の商品名でも
    汎用的に機能することを確認する（description-genre-012対応）。"""

    def test_accessory_noun_directly_before_tsuki_is_excluded(self):
        # 「防水」の直後に別の名詞（ケース）をはさんで「付き」が続くため、
        # 「防水」は除外され、次に見つかる本体自体の特徴（自立）が使われる
        # ことを確認する（除外されて空文字になるのではなく、正しく次の
        # 候補へ進むことまで検証する）。
        clause, _emoji = dg._top_feature_clause("防水ケース付き 自立式スマホスタンド", "収納")
        self.assertNotIn("水回りでも使いやすい", clause)
        self.assertEqual(clause, "自立して置き場所を選びにくい")

    def test_direct_product_body_feature_is_still_recognized(self):
        # キーワード自体に直接「付き」が続く場合（間に別の名詞がない）は
        # 従来どおり商品本体の特徴として扱う。
        clause, _emoji = dg._top_feature_clause("マグネット付き収納ラック", "収納")
        self.assertEqual(clause, "マグネットで取り付けられる")


class Sept30FinalReviewFixTest(unittest.TestCase):
    """2026-09-30 15:51生成分の最終レビューで残った3点（牛すじカレーの
    「専門店の味」という品質評価表現、PVCハンガーの「持ち運びしやすい」
    という未確認の用途拡張、卓上扇風機の「吊り下げて収納できる」という
    未確認の用途拡張）を修正したことを確認する。それ以外の7商品の
    descriptionは変更していないことも合わせて確認する。"""

    BEEF_TENDON_CURRY_NAME = Sept30BatchRegressionTest.BEEF_TENDON_CURRY_NAME
    PVC_HANGER_NAME = Sept30BatchRegressionTest.PVC_HANGER_NAME
    DESK_FAN_NAME = Sept30BatchRegressionTest.DESK_FAN_NAME
    SOAP_SCUM_SCRAPER_NAME = Sept30BatchRegressionTest.SOAP_SCUM_SCRAPER_NAME
    SOBA_TEA_NAME = Sept30BatchRegressionTest.SOBA_TEA_NAME
    FACE_ROLLER_NAME = Sept30BatchRegressionTest.FACE_ROLLER_NAME
    BABY_PILLOW_NAME = Sept30BatchRegressionTest.BABY_PILLOW_NAME
    HAND_SPINNER_NAME = Sept30BatchRegressionTest.HAND_SPINNER_NAME
    HAMBURG_NAME = Sept30BatchRegressionTest.HAMBURG_NAME
    HYPOCHLOROUS_WATER_NAME = Sept30BatchRegressionTest.HYPOCHLOROUS_WATER_NAME

    # 1. 牛すじカレーに「専門店の味」をこちらの評価として生成しない。
    def test_beef_tendon_curry_does_not_generate_quality_evaluation(self):
        item = make_item(name=self.BEEF_TENDON_CURRY_NAME)
        description = dg.generate_description(item, category="食品", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("専門店の味を自宅で楽しめる", description)
        self.assertIn("牛すじカレーを自宅で楽しめる", description)

    # 2. 牛すじカレーで未確認の調理の手軽さを断定しない。
    def test_beef_tendon_curry_does_not_claim_unconfirmed_convenience(self):
        item = make_item(name=self.BEEF_TENDON_CURRY_NAME)
        description = dg.generate_description(item, category="食品", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("手軽に食事を済ませたい人におすすめ", description)
        self.assertIn("牛すじカレー", description)
        self.assertIn("3パックセット", description)

    # 3. 「軽量」だけで「持ち運びしやすい」を生成しない。
    def test_lightweight_alone_does_not_generate_portability_claim(self):
        item = make_item(name=self.PVC_HANGER_NAME)
        description = dg.generate_description(item, category="収納", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("持ち運びしやすい", description)

    # 3b. ただし「持ち運び」等が明記されていれば従来どおり使える（回帰防止）。
    def test_lightweight_with_explicit_portability_word_still_works(self):
        clause, _emoji = dg._top_feature_clause("軽量で持ち運びに便利なボトル", "キッチン")
        self.assertEqual(clause, "持ち運びしやすい")

    # 4. ハンガーで絶対的な滑り防止表現へ拡張しない。
    def test_pvc_hanger_does_not_expand_into_absolute_anti_slip_guarantee(self):
        item = make_item(name=self.PVC_HANGER_NAME)
        description = dg.generate_description(item, category="収納", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("衣類が滑り落ちるのを防ぎたい人に便利そう", description)
        self.assertIn("衣類が滑り落ちにくい", description)
        self.assertIn("30本セット", description)

    # 4b. 旧タグが復活していないこと。
    def test_pvc_hanger_old_generic_hashtags_still_absent(self):
        item = make_item(name=self.PVC_HANGER_NAME)
        description = dg.generate_description(item, category="収納", base_hashtags=BASE_HASHTAGS)
        hashtag_line = description.split("\n\n")[-1]
        self.assertIn("#ハンガー", hashtag_line)
        self.assertNotIn("#暮らしの便利グッズ", hashtag_line)
        self.assertNotIn("#便利グッズ", hashtag_line)

    # 5. 「吊り下げ」だけで「吊り下げ収納」にしない。扇風機は「吊り下げて使える」。
    def test_desk_fan_hanging_is_not_expanded_into_storage_claim(self):
        item = make_item(name=self.DESK_FAN_NAME)
        description = dg.generate_description(item, category="収納", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("吊り下げて収納できる", description)
        self.assertIn("吊り下げて使える", description)

    # 6. 「マグネットリモコン」を本体マグネット設置と誤認しない（回帰確認）。
    def test_desk_fan_magnet_remote_still_not_read_as_magnetic_mounting(self):
        item = make_item(name=self.DESK_FAN_NAME)
        description = dg.generate_description(item, category="収納", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("マグネットで取り付けられる", description)
        self.assertIn("扇風機", description)
        hashtag_line = description.split("\n\n")[-1]
        self.assertIn("#扇風機", hashtag_line)

    # 7. 変更しない7商品のdescriptionが不変であることを確認する。
    def test_seven_unrelated_items_are_unchanged(self):
        cases = [
            (self.SOAP_SCUM_SCRAPER_NAME, "掃除", "石鹸カス", "スクレーパー"),
            (self.SOBA_TEA_NAME, "お茶", "5g×50包", "計250g"),
            (self.FACE_ROLLER_NAME, "掃除", "フェイスローラー", None),
            (self.BABY_PILLOW_NAME, "ベビー用品", "枕", None),
            (self.HAND_SPINNER_NAME, "ベビー用品", "ハンドスピナー", "3点セット"),
            (self.HAMBURG_NAME, "食品", "1個あたり130g", "10個または20個"),
            (self.HYPOCHLOROUS_WATER_NAME, "キッチン", "次亜塩素酸水", None),
        ]
        for name, category, expect_a, expect_b in cases:
            item = make_item(name=name)
            description = dg.generate_description(item, category=category, base_hashtags=BASE_HASHTAGS)
            self.assertIn(expect_a, description, description)
            if expect_b:
                self.assertIn(expect_b, description, description)
        # HALIFTの美容効果断定なし・次亜塩素酸水の安全性過剰断定なし・
        # ベビー枕の身体効果断定なしを個別に再確認する。
        item = make_item(name=self.FACE_ROLLER_NAME)
        description = dg.generate_description(item, category="掃除", base_hashtags=BASE_HASHTAGS)
        for phrase in ("むくみが取れる", "小顔になる", "リフトアップする"):
            self.assertNotIn(phrase, description)
        item = make_item(name=self.HYPOCHLOROUS_WATER_NAME)
        description = dg.generate_description(item, category="キッチン", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("キッチングッズ", description)
        for phrase in ("完全に無害", "人体に安全", "病原体を確実に除去"):
            self.assertNotIn(phrase, description)
        item = make_item(name=self.BABY_PILLOW_NAME)
        description = dg.generate_description(item, category="ベビー用品", base_hashtags=BASE_HASHTAGS)
        for phrase in ("絶壁を防ぐ", "吐き戻しを防ぐ", "向き癖を治す"):
            self.assertNotIn(phrase, description)


class Oct01BatchRegressionTest(unittest.TestCase):
    """2026-10-01 15:51生成分の商品名で、PRODUCT_TYPE_TEMPLATESに未登録の
    商品がcategory由来の汎用description（暮らしアイテム・時短グッズ等）へ
    落ちてしまう問題への一般化対応（description-genre-014）を確認する。
    商品名は本番で実際に取得された表記をそのまま使っている。"""

    THERMO_HYGROMETER_NAME = (
        "湿度計 温度計 温湿度計 温湿計 温度湿度計 おしゃれ デジタル 見やすい 置き掛け兼用 マグネット "
        "アラーム付 ナチュラル 小型 コンパクト 木目調 便利グッズ デザイン ギフト【ポイント10倍 送料無料】"
        "［ タニタ 温湿度計 TT572 ］"
    )
    DUSTPAN_NAME = (
        "ちりとり捨楽 45L 70L / ちりとり 屋外 おしゃれ 自立 ゴミ袋 レジ袋 装着 落ち葉 ちりとり 捨 楽 "
        "フレーム 大掃除 清掃用品 屋外 掃き掃除 大型 小型 スリム 便利グッズ 落葉 玄関 落ち葉集め "
        "掃除グッズ 写楽 スリム コンパクト 枯葉 ガーデニング ちりとり集草バッグ"
    )
    TOILET_CLEANER_NAME = "マイルドアシッドEL 1Lトイレクリーナー 業務用 トイレ洗剤 尿石除去 黄ばみ除去"
    WET_WIPES_NAME = (
        "**人気商品**ノンアルコール 99%除菌 ウエットティッシュ 除菌シート80枚入 3個 6個 12個＼ "
        "ノンアル 厚手 大判 無香料 ／送料無料 除菌ティッシュ まとめ買い VINDA 楽天スーパーセール "
        "買い回りマラソン 備蓄 防災"
    )
    STORAGE_BOX_NAME = (
        "★注目商品★【4個セット】収納ボックス キャスター付き 収納ケース 衣類収納ボックス 衣装ケース "
        "クローゼット 押入れ収納 プラスチック 洋服 透明 アイリスオーヤマ キャリーストッカー コロ付き "
        "ローラー フタ付き AA-740E"
    )
    BED_IN_BED_NAME = (
        "レビュー投稿特典あり！【公式販売店】ファルスカ ベッドインベッド　フレックス | "
        "添い寝☆川の字☆折り畳み☆持ち運び☆ベビーベッド☆お座りサポート☆お食事シート☆"
        "5歳まで使用できる【赤ちゃん】【ベビー用品】【あす楽対応】"
    )
    UNDER_SINK_RACK_NAME = (
        "シンク下 収納 伸縮 ラック スライド キッチン収納 調味料 調味料ラック 隙間収納 キッチン 台所 "
        "棚 収納棚 1段 シンプル シンク下引き出し 伸縮棚 シンク下伸縮棚 ホワイト シンク下収納 "
        "最大幅70 奥行40 アイリスオーヤマ USD-1V[RNG]"
    )
    GYUTAN_STEW_NAME = (
        "牛タン シチュー 180g×4袋 レトルト レンジ 食品 全国送料無料 "
        "カネタ●牛たんシチュー180g×4袋●k-03"
    )
    TENGU_SOBA_NAME = (
        "【愛されて130余年】そば 蕎麦 乾麺 天狗そば お試し 6人前セット 3袋 山形 お土産 田舎そば "
        "田舎蕎麦 板そば ざるそば 盛りそば soba 国産 ギフト 贈答 山形 天童 山本製麺 お祝い 内祝い "
        "誕生日 ご挨拶 乾蕎麦 送料無料 非常食 保存食 備蓄"
    )
    BROOM_DUSTPAN_SET_NAME = (
        "特典あり《 tidy Sweep スウィープ 》ほうきちりとりセット ホーキ 箒 室内用 屋外用 ベランダ用 "
        "長柄 自立 軽い 掃除道具 コンパクト お掃除グッズ シンプル おしゃれ 白 グレー レモン ブラウン "
        "ベージュ ブルー カフェ 飲食店 オフィス ティディ スイープ"
    )

    # 1. 温湿度計を汎用暮らしアイテムにしない。
    def test_thermo_hygrometer_is_not_only_generic_lifestyle_item(self):
        item = make_item(name=self.THERMO_HYGROMETER_NAME)
        description = dg.generate_description(item, category="暮らし全般", base_hashtags=BASE_HASHTAGS)
        self.assertIn("温湿度計", description)
        self.assertNotIn("毎日の暮らしに取り入れやすそうなアイテム◎", description)

    # 2. 温湿度計のマグネットを付属品誤認しない（確認できる仕様として使用可能）。
    def test_thermo_hygrometer_magnet_is_usable_as_a_confirmed_spec(self):
        item = make_item(name=self.THERMO_HYGROMETER_NAME)
        description = dg.generate_description(item, category="暮らし全般", base_hashtags=BASE_HASHTAGS)
        self.assertIn("マグネットで取り付けられる", description)
        self.assertNotIn("壁に貼れる", description)

    # 3. ちりとりを具体的に判定する。
    def test_dustpan_is_recognized_specifically(self):
        item = make_item(name=self.DUSTPAN_NAME)
        description = dg.generate_description(item, category="暮らし全般", base_hashtags=BASE_HASHTAGS)
        self.assertIn("ちりとり", description)
        self.assertNotIn("毎日の暮らしに取り入れやすそうなアイテム◎", description)

    # 4. 45L/70Lを根拠なく商品容量と断定しない。
    def test_dustpan_45l_70l_is_not_treated_as_confirmed_capacity(self):
        item = make_item(name=self.DUSTPAN_NAME)
        description = dg.generate_description(item, category="暮らし全般", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("45L・70Lから選べる", description)
        self.assertNotIn("容量45L", description)

    # 5. トイレクリーナーを汎用日用品にしない。
    def test_toilet_cleaner_is_not_only_generic_daily_goods(self):
        item = make_item(name=self.TOILET_CLEANER_NAME)
        description = dg.generate_description(item, category="日用品", base_hashtags=BASE_HASHTAGS)
        self.assertIn("トイレ", description)
        self.assertNotIn("普段の暮らしに取り入れやすい日用品◎", description)

    # 6. 1Lを商品容量として扱う（確認できれば使用可能。確認できない場合は省略する安全側の仕様）。
    def test_toilet_cleaner_does_not_fabricate_capacity(self):
        item = make_item(name=self.TOILET_CLEANER_NAME)
        description = dg.generate_description(item, category="日用品", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("容量は約1L", description)

    # 7. 業務用を大容量へ変換しない（回帰確認）。
    def test_toilet_cleaner_gyoumuyou_does_not_convert_to_bulk_size(self):
        item = make_item(name=self.TOILET_CLEANER_NAME)
        description = dg.generate_description(item, category="日用品", base_hashtags=BASE_HASHTAGS)
        for phrase in ("業務用サイズ", "大容量", "たっぷり"):
            self.assertNotIn(phrase, description, description)
        for phrase in ("尿石が必ず落ちる", "黄ばみを完全除去"):
            self.assertNotIn(phrase, description, description)

    # 8. 除菌シートを具体的に判定する。
    def test_wet_wipes_is_recognized_specifically(self):
        item = make_item(name=self.WET_WIPES_NAME)
        description = dg.generate_description(item, category="日用品", base_hashtags=BASE_HASHTAGS)
        self.assertIn("ウェットティッシュ", description)
        self.assertNotIn("まとめてストックしておけそうな日用品◎", description)

    # 9. 80枚入と3/6/12個の意味を分離する。
    def test_wet_wipes_content_and_count_options_are_separated(self):
        item = make_item(name=self.WET_WIPES_NAME)
        description = dg.generate_description(item, category="日用品", base_hashtags=BASE_HASHTAGS)
        self.assertIn("80枚入り・3個・6個・12個から選べる", description)

    # 10. 99%除菌を効果保証へ拡張しない。
    def test_wet_wipes_does_not_overclaim_disinfection(self):
        item = make_item(name=self.WET_WIPES_NAME)
        description = dg.generate_description(item, category="日用品", base_hashtags=BASE_HASHTAGS)
        for phrase in ("99%確実に除菌できる", "ウイルスを99%除去する", "感染予防できる"):
            self.assertNotIn(phrase, description, description)

    # 11. 収納ボックスを具体的に判定する。
    def test_storage_box_is_recognized_specifically(self):
        item = make_item(name=self.STORAGE_BOX_NAME)
        description = dg.generate_description(item, category="収納", base_hashtags=BASE_HASHTAGS)
        self.assertIn("収納ボックス", description)

    # 12. 4個セットを維持する。
    def test_storage_box_4_piece_set_is_preserved(self):
        item = make_item(name=self.STORAGE_BOX_NAME)
        description = dg.generate_description(item, category="収納", base_hashtags=BASE_HASHTAGS)
        self.assertIn("4個セット", description)
        hashtag_line = description.split("\n\n")[-1]
        self.assertIn("#収納ボックス", hashtag_line)
        self.assertNotIn("#暮らしの便利グッズ", hashtag_line)
        self.assertNotIn("#便利グッズ", hashtag_line)

    # 13. ベッドインベッドを具体的に判定する。
    def test_bed_in_bed_is_recognized_specifically(self):
        item = make_item(name=self.BED_IN_BED_NAME)
        description = dg.generate_description(item, category="ベビー用品", base_hashtags=BASE_HASHTAGS)
        self.assertIn("ベッドインベッド", description)
        self.assertNotIn("赤ちゃんとの暮らしに取り入れやすいベビー用品◎", description)

    # 14. レビュー特典を本体にしない（回帰確認）。
    def test_bed_in_bed_review_incentive_is_not_mistaken_for_the_product(self):
        self.assertEqual(dg.match_product_type_keyword(self.BED_IN_BED_NAME), "ベッドインベッド")

    # 15. 明示的「持ち運び」は使用可能。身体効果・安全性は保証しない。
    def test_bed_in_bed_explicit_portability_is_usable_without_overclaiming(self):
        item = make_item(name=self.BED_IN_BED_NAME)
        description = dg.generate_description(item, category="ベビー用品", base_hashtags=BASE_HASHTAGS)
        self.assertIn("持ち運びやすい", description)
        for phrase in ("安全に添い寝できる", "5歳まで使用できる"):
            self.assertNotIn(phrase, description, description)

    # 16. シンク下伸縮ラックを具体的に判定する。
    def test_under_sink_rack_is_recognized_specifically(self):
        item = make_item(name=self.UNDER_SINK_RACK_NAME)
        description = dg.generate_description(item, category="収納", base_hashtags=BASE_HASHTAGS)
        self.assertIn("シンク下", description)
        self.assertNotIn("キッチンの物をすっきりまとめられそうな収納グッズ◎", description)

    # 17. 単位なし70/40にcmを勝手に追加しない。
    def test_under_sink_rack_does_not_fabricate_units_for_bare_numbers(self):
        item = make_item(name=self.UNDER_SINK_RACK_NAME)
        description = dg.generate_description(item, category="収納", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("70cm", description)
        self.assertNotIn("40cm", description)

    # 18. 牛タンシチューを具体的に判定する。
    def test_gyutan_stew_is_recognized_specifically(self):
        item = make_item(name=self.GYUTAN_STEW_NAME)
        description = dg.generate_description(item, category="食品", base_hashtags=BASE_HASHTAGS)
        self.assertIn("牛たんシチュー", description)
        self.assertNotIn("手軽に楽しめそうな食品◎", description)

    # 19. 180g×4袋を正しく扱う。
    def test_gyutan_stew_quantity_is_handled_correctly(self):
        item = make_item(name=self.GYUTAN_STEW_NAME)
        description = dg.generate_description(item, category="食品", base_hashtags=BASE_HASHTAGS)
        self.assertIn("180g×4袋", description)

    # 20. 数量へ「使いやすい」を付けない。
    def test_gyutan_stew_quantity_does_not_get_mechanical_usability_suffix(self):
        item = make_item(name=self.GYUTAN_STEW_NAME)
        description = dg.generate_description(item, category="食品", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("180g×4袋で使いやすい", description)

    # 21. そばを汎用食品にしない。
    def test_tengu_soba_is_not_only_generic_food(self):
        item = make_item(name=self.TENGU_SOBA_NAME)
        description = dg.generate_description(item, category="食品", base_hashtags=BASE_HASHTAGS)
        self.assertIn("そば", description)
        self.assertNotIn("手軽に楽しめそうな食品◎", description)

    # 22. 6人前と3袋を混同しない。
    def test_tengu_soba_servings_and_bags_are_not_conflated(self):
        item = make_item(name=self.TENGU_SOBA_NAME)
        description = dg.generate_description(item, category="食品", base_hashtags=BASE_HASHTAGS)
        self.assertIn("6人前・3袋セット", description)

    # 23. ほうきちりとりセットを具体的に判定する。
    def test_broom_dustpan_set_is_recognized_specifically(self):
        item = make_item(name=self.BROOM_DUSTPAN_SET_NAME)
        description = dg.generate_description(item, category="掃除", base_hashtags=BASE_HASHTAGS)
        self.assertIn("ほうき", description)
        self.assertNotIn("そんな掃除の手間を減らしてくれそうな掃除グッズ◎", description)

    # 24. 「軽い」だけで持ち運びしやすいを生成しない（回帰確認）。
    def test_broom_dustpan_set_does_not_generate_portability_from_light_alone(self):
        item = make_item(name=self.BROOM_DUSTPAN_SET_NAME)
        description = dg.generate_description(item, category="掃除", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("持ち運びしやすい", description)
        self.assertIn("自立して置き場所を選びにくい", description)

    # 25. 具体的商品判定時に旧汎用タグを付けない（10件まとめて確認）。
    def test_new_product_types_do_not_get_mechanical_old_generic_hashtags(self):
        names = [
            self.THERMO_HYGROMETER_NAME, self.DUSTPAN_NAME, self.TOILET_CLEANER_NAME,
            self.WET_WIPES_NAME, self.STORAGE_BOX_NAME, self.BED_IN_BED_NAME,
            self.UNDER_SINK_RACK_NAME, self.GYUTAN_STEW_NAME, self.TENGU_SOBA_NAME,
            self.BROOM_DUSTPAN_SET_NAME,
        ]
        categories = [
            "暮らし全般", "暮らし全般", "日用品", "日用品", "収納", "ベビー用品",
            "収納", "食品", "食品", "掃除",
        ]
        for name, category in zip(names, categories):
            item = make_item(name=name)
            description = dg.generate_description(item, category=category, base_hashtags=BASE_HASHTAGS)
            hashtag_line = description.split("\n\n")[-1]
            self.assertNotIn("#暮らしの便利グッズ", hashtag_line, description)
            self.assertNotIn("#便利グッズ", hashtag_line, description)
            self.assertLessEqual(len(description), 500)


class RepeatedNounCandidateGeneralizationTest(unittest.TestCase):
    """PRODUCT_TYPE_TEMPLATESに一致しない未知の商品でも、商品名の構造
    （2回以上登場する具体的な語句）から安全に商品本体候補を拾う一般的な
    仕組み（_extract_repeated_noun_candidate / _apply_repeated_noun_
    candidate）を確認する（description-genre-014対応）。"""

    def test_repeated_specific_noun_is_used_as_product_body(self):
        name = "まるごと収穫 完熟マンゴーゼリー 完熟マンゴーゼリー 6個入 贈答用 送料無料"
        self.assertEqual(dg._extract_repeated_noun_candidate(name), "完熟マンゴーゼリー")
        item = make_item(name=name)
        description = dg.generate_description(item, category="食品", base_hashtags=BASE_HASHTAGS)
        self.assertIn("完熟マンゴーゼリー", description)
        hashtag_line = description.split("\n\n")[-1]
        self.assertIn("#完熟マンゴーゼリー", hashtag_line)
        self.assertNotIn("#暮らしの便利グッズ", hashtag_line)
        self.assertNotIn("#便利グッズ", hashtag_line)

    def test_only_repeated_promotional_words_do_not_trigger_the_mechanism(self):
        name = "送料無料 送料無料 人気 人気 おしゃれ おしゃれ 商品"
        self.assertIsNone(dg._extract_repeated_noun_candidate(name))
        item = make_item(name=name)
        description = dg.generate_description(item, category="日用品", base_hashtags=BASE_HASHTAGS)
        self.assertIn("日用品◎", description)
        hashtag_line = description.split("\n\n")[-1]
        self.assertIn("#便利グッズ", hashtag_line)

    def test_registered_product_type_keyword_takes_priority_over_candidate(self):
        # PRODUCT_TYPE_TEMPLATESに一致する商品では、繰り返し候補の仕組みは
        # 使われない（商品本体判定の優先順位1・2が常に3・4より先）。
        name = "業務用 ハンガーラック 組立不要 頑丈 幅90cm 耐荷重100kg 高さ180cm"
        item = make_item(name=name)
        description = dg.generate_description(item, category="収納", base_hashtags=BASE_HASHTAGS)
        self.assertIn("ハンガーラック", description)


class Oct02BatchRegressionTest(unittest.TestCase):
    """2026-10-02 15:51生成分の商品名で、category（時短・キッチン等）に
    引っ張られて商品本体とは異なる汎用description（時短グッズ・
    キッチングッズ等）に落ちていた問題の追加対応（description-
    genre-015）を確認する。商品名は本番で実際に取得された表記をそのまま
    使っている。"""

    MUSENMAI_NAME = (
        "[お値打ち価格続行]令和7年産 無洗米 北海道産 ななつぼし 10kg 5kg×2袋 送料無料"
        "【食味ランク特A】 [北海道沖縄へのお届けは別途送料760円] [家事時短で便利な無洗米]"
    )
    HAIR_CATCHER_NAME = (
        "レビューCP実施中！《楽天1位》スタンダードサイズ:直径140mm 【HUBATH お風呂 マグネット "
        "ヘアーキャッチャー STD140 】 排水溝 ゴミ受け 風呂 浴室 掃除 ユニットバス 排水口ネット "
        "ごみ受け 送料無料 極排水 バスルーム 磁石"
    )
    BOWL_COLANDER_SET_NAME = (
        "【在庫完売次第終了】ボール・コランダーセット （旧カラー） ボルコラ ザル ボウル セット "
        "ボールコランダー 耐熱 プラスチック ふた付き 温野菜 電子レンジ対応 食洗機対応 キッチン "
        "調理器具 時短 キッチングッズ"
    )
    RANGE_GRILL_NAME = (
        "レンジで焼ケール 角型 丸型 深型 レンジで焼けーる レンジで焼魚 レンジで焼き魚 レンジ調理器具 "
        "プレート 電子レンジ 魚焼き器 レンジグリル 焼き魚 グリルパン レンジ ヤケール"
    )
    ARIEL_NAME = (
        "【1種類を選べる】 アリエール 洗濯洗剤 液体 詰め替え 超ジャンボ(1000g×4セット)【アリエール 液体】"
    )
    DISH_DETERGENT_NAME = (
        "【 手 肌 に やさしい 食器用洗剤『Chloris Wash for Dish 』お試しサイズ／本体／詰替え用"
        "クロリスディッシュ おしゃれ かわいい ボトル 容器 台所洗剤 キッチン用洗剤 液体洗剤 "
        "手荒れ アロマ の香り 】"
    )

    # 1. 無洗米を「時短グッズ」にしない。
    def test_musenmai_is_not_treated_as_a_generic_jitan_product(self):
        item = make_item(name=self.MUSENMAI_NAME)
        description = dg.generate_description(item, category="時短", base_hashtags=BASE_HASHTAGS)
        self.assertIn("無洗米", description)
        self.assertNotIn("そんな家事の手間を減らしてくれそうな時短グッズ◎", description)

    # 2. 北海道産ななつぼしを米として判定する。
    def test_musenmai_is_recognized_as_rice(self):
        self.assertEqual(dg.match_product_type_keyword(self.MUSENMAI_NAME), "無洗米")

    # 3. 5kg×2袋・合計10kgの意味を維持する。
    def test_musenmai_quantity_breakdown_is_preserved(self):
        item = make_item(name=self.MUSENMAI_NAME)
        description = dg.generate_description(item, category="時短", base_hashtags=BASE_HASHTAGS)
        self.assertIn("5kg×2袋", description)
        self.assertIn("合計10kg", description)
        self.assertNotIn("10kg・5kgから選べる", description)

    # 4. 食味ランク特Aを独自の味評価へ拡張しない。
    def test_musenmai_does_not_expand_taste_rank_into_own_evaluation(self):
        item = make_item(name=self.MUSENMAI_NAME)
        description = dg.generate_description(item, category="時短", base_hashtags=BASE_HASHTAGS)
        for phrase in ("美味しい", "絶品", "特A級のおいしさ"):
            self.assertNotIn(phrase, description, description)

    # 5. ヘアーキャッチャーを「時短グッズ」にしない。
    def test_hair_catcher_is_not_treated_as_a_generic_jitan_product(self):
        item = make_item(name=self.HAIR_CATCHER_NAME)
        description = dg.generate_description(item, category="時短", base_hashtags=BASE_HASHTAGS)
        self.assertIn("ヘアーキャッチャー", description)
        self.assertNotIn("そんな家事の手間を減らしてくれそうな時短グッズ◎", description)

    # 6. 直径140mmへ勝手に「約」を追加しない。
    def test_hair_catcher_diameter_does_not_get_unconfirmed_approximation(self):
        item = make_item(name=self.HAIR_CATCHER_NAME)
        description = dg.generate_description(item, category="時短", base_hashtags=BASE_HASHTAGS)
        self.assertIn("直径140mm", description)
        self.assertNotIn("直径は約140mm", description)

    # 7. マグネット属性を未確認の性能へ拡張しない。重複もしない（回帰確認）。
    def test_hair_catcher_magnet_is_not_expanded_and_not_duplicated(self):
        item = make_item(name=self.HAIR_CATCHER_NAME)
        description = dg.generate_description(item, category="時短", base_hashtags=BASE_HASHTAGS)
        self.assertEqual(description.count("マグネットで取り付けられる"), 1)
        for phrase in ("強力な磁力", "必ず固定できる"):
            self.assertNotIn(phrase, description, description)

    # 8. ボール・コランダーセットを汎用キッチン用品だけにしない。
    def test_bowl_colander_set_is_not_only_generic_kitchen_goods(self):
        item = make_item(name=self.BOWL_COLANDER_SET_NAME)
        description = dg.generate_description(item, category="キッチン", base_hashtags=BASE_HASHTAGS)
        self.assertIn("ボール・コランダーセット", description)
        self.assertNotIn("そんなキッチンでの家事をラクにしてくれそうなキッチングッズ◎", description)

    # 9. 電子レンジ対応・食洗機対応を正しく扱う。
    def test_bowl_colander_set_handles_microwave_and_dishwasher_facts(self):
        item = make_item(name=self.BOWL_COLANDER_SET_NAME)
        description = dg.generate_description(item, category="キッチン", base_hashtags=BASE_HASHTAGS)
        self.assertIn("食洗機対応で使いやすい", description)

    # 10. レンジで焼ケールを電子レンジ調理器等として具体化する。
    def test_range_grill_is_recognized_specifically(self):
        item = make_item(name=self.RANGE_GRILL_NAME)
        description = dg.generate_description(item, category="キッチン", base_hashtags=BASE_HASHTAGS)
        self.assertIn("レンジ調理器具", description)
        self.assertNotIn("そんなキッチンでの家事をラクにしてくれそうなキッチングッズ◎", description)

    # 11. 未確認の焼き性能・調理時間を追加しない。
    def test_range_grill_does_not_add_unconfirmed_cooking_performance(self):
        item = make_item(name=self.RANGE_GRILL_NAME)
        description = dg.generate_description(item, category="キッチン", base_hashtags=BASE_HASHTAGS)
        for phrase in (
            "必ず焼き目が付く", "分で焼ける", "フライパン不要", "油不要", "失敗しない",
        ):
            self.assertNotIn(phrase, description, description)

    # 12. 1000g×4セットに「使いやすい」を付けない。
    def test_ariel_quantity_does_not_get_mechanical_usability_suffix(self):
        item = make_item(name=self.ARIEL_NAME)
        description = dg.generate_description(item, category="洗剤", base_hashtags=BASE_HASHTAGS)
        self.assertIn("1000g×4セット", description)
        self.assertNotIn("1000g×4セットで使いやすい", description)
        hashtag_line = description.split("\n\n")[-1]
        self.assertIn("#アリエール", hashtag_line)
        self.assertNotIn("#暮らしの便利グッズ", hashtag_line)
        self.assertNotIn("#便利グッズ", hashtag_line)

    # 13. 食器用洗剤の手肌効果を過剰断定しない。
    def test_dish_detergent_does_not_overclaim_hand_skin_effects(self):
        item = make_item(name=self.DISH_DETERGENT_NAME)
        description = dg.generate_description(item, category="洗剤", base_hashtags=BASE_HASHTAGS)
        self.assertIn("食器用洗剤", description)
        for phrase in ("手荒れを防ぐ", "肌荒れしない", "敏感肌でも安全", "肌に絶対やさしい"):
            self.assertNotIn(phrase, description, description)
        hashtag_line = description.split("\n\n")[-1]
        self.assertIn("#食器用洗剤", hashtag_line)
        self.assertNotIn("#暮らしの便利グッズ", hashtag_line)
        self.assertNotIn("#便利グッズ", hashtag_line)

    # 14. 具体的商品判定時に旧汎用タグを付けない（6件まとめて確認）。
    def test_new_product_types_do_not_get_mechanical_old_generic_hashtags(self):
        cases = [
            (self.MUSENMAI_NAME, "時短"),
            (self.HAIR_CATCHER_NAME, "時短"),
            (self.BOWL_COLANDER_SET_NAME, "キッチン"),
            (self.RANGE_GRILL_NAME, "キッチン"),
            (self.ARIEL_NAME, "洗剤"),
            (self.DISH_DETERGENT_NAME, "洗剤"),
        ]
        for name, category in cases:
            item = make_item(name=name)
            description = dg.generate_description(item, category=category, base_hashtags=BASE_HASHTAGS)
            hashtag_line = description.split("\n\n")[-1]
            self.assertNotIn("#時短アイテム", hashtag_line, description)
            self.assertNotIn("#暮らしの便利グッズ", hashtag_line, description)
            self.assertNotIn("#便利グッズ", hashtag_line, description)
            self.assertLessEqual(len(description), 500)

    # 15. description-genre-013までの回帰テストを維持する（前回から継続中の
    # 4商品が、今回の追加修正でも一般化ロジックのみで正しいことを確認する）。
    def test_four_continuing_items_use_the_same_generalized_logic(self):
        campaign365_name = "マイルドアシッドEL 1Lトイレクリーナー 業務用 トイレ洗剤 尿石除去 黄ばみ除去"
        marubeni_name = (
            "**人気商品**ノンアルコール 99%除菌 ウエットティッシュ 除菌シート80枚入 3個 6個 12個＼ "
            "ノンアル 厚手 大判 無香料 ／送料無料 除菌ティッシュ まとめ買い VINDA 楽天スーパーセール "
            "買い回りマラソン 備蓄 防災"
        )
        roomy_name = (
            "湿度計 温度計 温湿度計 温湿計 温度湿度計 おしゃれ デジタル 見やすい 置き掛け兼用 "
            "マグネット アラーム付 ナチュラル 小型 コンパクト 木目調 便利グッズ デザイン ギフト"
            "【ポイント10倍 送料無料】［ タニタ 温湿度計 TT572 ］"
        )
        winkl_name = (
            "ちりとり捨楽 45L 70L / ちりとり 屋外 おしゃれ 自立 ゴミ袋 レジ袋 装着 落ち葉 ちりとり "
            "捨 楽 フレーム 大掃除 清掃用品 屋外 掃き掃除 大型 小型 スリム 便利グッズ 落葉 玄関 "
            "落ち葉集め 掃除グッズ 写楽 スリム コンパクト 枯葉 ガーデニング ちりとり集草バッグ"
        )
        cases = [
            (campaign365_name, "日用品", "トイレ"),
            (marubeni_name, "日用品", "ウェットティッシュ"),
            (roomy_name, "暮らし全般", "温湿度計"),
            (winkl_name, "暮らし全般", "ちりとり"),
        ]
        for name, category, expect in cases:
            item = make_item(name=name)
            description = dg.generate_description(item, category=category, base_hashtags=BASE_HASHTAGS)
            self.assertIn(expect, description, description)
            hashtag_line = description.split("\n\n")[-1]
            self.assertNotIn("#暮らしの便利グッズ", hashtag_line, description)
            self.assertNotIn("#便利グッズ", hashtag_line, description)


if __name__ == "__main__":
    unittest.main()
