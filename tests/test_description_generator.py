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

## 紹介文フォーマットの変更（導入文＋箇条書き → 自然な文章）

紹介文の形式を「導入文＋箇条書き（・）＋レビュー行」から、箇条書きを
使わない2〜3文程度の自然な文章に変更した。この変更に伴い、レビュー評価・
件数は本文に含めなくなった（候補一覧には別項目として表示されるため）。
絵文字も「各行の先頭に機械的に付ける」方式から「文末など意味の合う場所に
自然に入れる」方式に変わり、1投稿あたりの個数も3〜6個から2〜4個に変更した。

この書き換えの過程で、1文目に「余韻の2つ目の絵文字」を足す処理が、
その行自身の絵文字とだけ重複を避けていて、他の文で既に使っている絵文字とは
重複してしまう不具合が見つかった（例：1文目が「🧲😊」、2文目も「😊」で
終わってしまう）。文章全体で既に使われている絵文字を避けるように修正した。

## 商品名の単語だけで特徴を決めつける問題の修正

上記の文章形式化のあと、実際のSummaryで次のような「商品名に含まれる単語と、
商品全体の用途が食い違う」問題が見つかった。

- 三角コーナー（生ゴミの水切り用）の商品名に「吸盤」が含まれ、紹介文が
  「吸盤で好きな場所に取り付けられる」になっていた
- 味噌マドラーの商品名に「ステンレス」が含まれ、紹介文が「サビに強い
  キッチングッズです」になっていた（マドラーの本来の用途である
  「味噌を溶かしやすい」ことが伝わらない）
- ドアストッパーの商品名に「マグネット」が含まれ、紹介文が「マグネットで
  浮かせて設置できる」になっていた（実際は扉を固定するための商品）

原因は、商品名から見つかった構造・仕様の単語（マグネット・吸盤・ステンレス等）を
そのまま1文目（紹介文の主役）にしていたこと。商品名はSEO対策で多くの単語が
詰め込まれており、単語が含まれること＝それが商品全体の用途、とは限らない。

対応として、`PRODUCT_TYPE_HINTS`（商品の種類そのものが分かる場合の、
用途に沿った1文目）を`FEATURE_CLAUSES`（構造・仕様の単語一致）より優先させ、
`FEATURE_CLAUSES`は見つかっても1文目の主役にはせず、2文目に「〜なので、」
という理由として添えるだけにした。また、商品の用途に繋がりにくい「ステンレス
＝サビに強い」という素材だけの表現は`FEATURE_CLAUSES`から削除した。
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

    def test_real_items_never_use_experience_implying_phrases(self):
        # 「使ってみました」「買ってよかった」など、実際に使用したと誤解される
        # 表現は使わない、という生成ルールの回帰テスト。
        real_items_and_categories = [
            (REAL_SOUP_MAKER, "時短"),
            (REAL_REFILL_MINI, "収納"),
            (REAL_CARDBOARD_STOCKER, "収納"),
            (REAL_MAGIC_TAPE, "収納"),
            (REAL_COMPRESSION_BAG, "収納"),
            (REAL_MAGNET_RACK, "収納"),
            (REAL_MAGNET_HOOK, "収納"),
            (REAL_AIR_FRYER, "時短"),
        ]
        for item, category in real_items_and_categories:
            description = dg.generate_description(item, category=category, base_hashtags=BASE_HASHTAGS)
            for phrase in ("使ってみました", "買ってよかった", "使ってみて", "買ってみました"):
                self.assertNotIn(phrase, description, f"{item['name'][:20]}: {description}")

    def test_real_items_body_does_not_contain_review_numbers(self):
        # レビュー評価・レビュー件数は紹介文の本文には原則含めない、というルールの確認。
        for item in (REAL_SOUP_MAKER, REAL_MAGNET_RACK, REAL_AIR_FRYER):
            description = dg.generate_description(item, category="収納", base_hashtags=BASE_HASHTAGS)
            self.assertNotIn("レビュー評価", description)
            self.assertNotIn("レビュー件数", description)


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


def _body_lines(description: str) -> list[str]:
    """紹介文からハッシュタグ行を除いた、文章部分の行一覧を返す。"""
    body = description.split("\n\n", 1)[0]
    return body.splitlines()


class DescriptionFormatTest(unittest.TestCase):
    """紹介文の基本フォーマット（文字数・文の数・ハッシュタグ・禁止表現）を確認する。"""

    def test_description_within_max_length(self):
        item = make_item(name="テスト商品")
        description = dg.generate_description(item, category="収納", base_hashtags=BASE_HASHTAGS, max_length=500)
        self.assertLessEqual(len(description), 500)

    def test_description_has_no_bullet_markers(self):
        # 箇条書き「・」は使わない、という生成ルールの確認。
        item = make_item(name="テスト商品")
        for category in dg.CATEGORY_EMOJIS:
            description = dg.generate_description(item, category=category, base_hashtags=BASE_HASHTAGS)
            self.assertNotIn("・", description)

    def test_description_has_two_or_three_sentences(self):
        item = make_item(name="テスト商品")
        for category in dg.CATEGORY_EMOJIS:
            description = dg.generate_description(item, category=category, base_hashtags=BASE_HASHTAGS)
            lines = _body_lines(description)
            self.assertIn(len(lines), (2, 3), f"category={category}: {lines}")

    def test_review_stats_are_not_included_in_body(self):
        item = make_item(name="テスト商品", review_average=4.2, review_count=345)
        description = dg.generate_description(item, category="キッチン", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("4.2", description)
        self.assertNotIn("345件", description)

    def test_no_feature_hint_falls_back_to_safe_generic_points(self):
        # 商品名に特徴語が無くても、無理に特徴を作らずカテゴリ共通の安全な
        # 言い回しで埋められることを確認する（推測で特徴を作らないという条件の確認）。
        item = make_item(name="なんの変哲もない商品")
        description = dg.generate_description(item, category="時短", base_hashtags=BASE_HASHTAGS)
        for _keyword, clause_spec, _emoji_spec in dg.FEATURE_CLAUSES:
            resolved_clause = dg._resolve_by_category(clause_spec, "時短")
            self.assertNotIn(resolved_clause, description)

    def test_item_caption_is_not_used_for_feature_detection(self):
        # 商品名には特徴語が無く、商品説明にだけ「ステンレス」がある場合、
        # 商品説明は特徴抽出に使わないため、紹介文に出てこないことを確認する。
        item = make_item(name="なんの変哲もない商品", item_caption="素材：ステンレス、ポリプロピレン")
        description = dg.generate_description(item, category="キッチン", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("ステンレス", description)

    def test_hashtag_count_is_between_three_and_five(self):
        item = make_item(name="テスト商品")
        for category in dg.CATEGORY_EMOJIS:
            description = dg.generate_description(item, category=category, base_hashtags=BASE_HASHTAGS)
            hashtag_line = description.splitlines()[-1]
            hashtags = hashtag_line.split(" ")
            self.assertGreaterEqual(len(hashtags), 3, f"category={category}: {hashtag_line}")
            self.assertLessEqual(len(hashtags), 5, f"category={category}: {hashtag_line}")

    def test_default_hashtag_is_kept_when_passed_in(self):
        # 「#暮らしの便利グッズ」は基本的に入れる、というルールの確認
        # （base_hashtagsとしてsettings.example.yamlのdefault_hashtagsを渡した場合）。
        item = make_item(name="テスト商品")
        description = dg.generate_description(item, category="キッチン", base_hashtags=BASE_HASHTAGS)
        self.assertIn("#暮らしの便利グッズ", description)

    def test_no_category_noun_duplication_in_feature_sentence(self):
        # 「大容量」→「収納」カテゴリでは「たっぷり収納できる収納グッズです」のような
        # 重複した言い回しにならないことを確認する。
        item = make_item(name="大容量 収納ボックス")
        description = dg.generate_description(item, category="収納", base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("収納できる収納グッズです", description)

    def test_same_category_produces_varied_sentences_across_products(self):
        # 商品カテゴリだけで文章を決めず、商品名によって紹介文が変わることの確認。
        item_a = make_item(name="マグネット式 キッチンラック", item_code="a")
        item_b = make_item(name="折りたたみ式 水切りラック", item_code="b")
        description_a = dg.generate_description(item_a, category="キッチン", base_hashtags=BASE_HASHTAGS)
        description_b = dg.generate_description(item_b, category="キッチン", base_hashtags=BASE_HASHTAGS)
        self.assertNotEqual(description_a, description_b)


class ProductTypeMismatchRegressionTest(unittest.TestCase):
    """商品名に含まれる単語だけで特徴を決めつけないことを確認する回帰テスト。

    楽天の商品名はSEO対策で色々な単語が詰め込まれていることが多く、
    「商品名に単語が含まれる＝それが商品全体の用途」とは限らない。
    ここでは実際に報告された3つの不一致パターン（三角コーナー・味噌マドラー・
    ドアストッパー）を、実際の商品名によく見られる形（色々な単語が
    詰め込まれた商品名）で再現し、商品全体の用途に沿った文章になることを確認する。
    """

    def test_triangle_corner_is_not_described_as_suction_cup_item(self):
        # 三角コーナー（生ゴミの水切り用）の商品名に「吸盤」が含まれていても、
        # 「吸盤で好きな場所に取り付けられる」を紹介文の主役にしない。
        item = make_item(
            name="水切り 三角コーナー キッチン ステンレス 吸盤 排水口ネット付き シンク こし器 送料無料"
        )
        description = dg.generate_description(item, category="キッチン", base_hashtags=BASE_HASHTAGS)
        self.assertIn("三角コーナー", description)
        self.assertNotIn("吸盤で好きな場所に取り付けられる", description)
        self.assertNotIn("サビに強い", description)

    def test_miso_muddler_is_not_described_as_rust_resistant(self):
        # 味噌マドラーの商品名に「ステンレス」が含まれていても、
        # 素材だけの表現（サビに強い）ではなく、用途に沿った文章にする。
        item = make_item(
            name="味噌マドラー ステンレス 味噌漉し みそこし 味噌溶き 調理器具 キッチン雑貨"
        )
        description = dg.generate_description(item, category="キッチン", base_hashtags=BASE_HASHTAGS)
        self.assertIn("マドラー", description)
        self.assertNotIn("サビに強い", description)
        self.assertNotIn("ステンレス", description)

    def test_door_stopper_is_not_described_as_floating_storage(self):
        # ドアストッパーの商品名に「マグネット」が含まれていても、
        # 収納用品向けの「マグネットで浮かせて設置できる」を紹介文の主役にしない。
        item = make_item(name="ドアストッパー マグネット式 扉 固定 玄関 diy おしゃれ シンプル 傷防止")
        description = dg.generate_description(item, category=dg.DEFAULT_CATEGORY, base_hashtags=BASE_HASHTAGS)
        body = "\n".join(_body_lines(description))
        self.assertIn("ドアストッパー", body)
        self.assertNotIn("浮かせて設置", body)
        self.assertNotIn("収納", body)

    def test_stainless_material_clause_was_removed(self):
        # 「ステンレス＝サビに強い」は、商品全体の用途に繋がりにくい素材だけの
        # 表現のため、FEATURE_CLAUSESから削除されていることを確認する。
        keywords = [keyword for keyword, _clause, _emoji in dg.FEATURE_CLAUSES]
        self.assertNotIn("ステンレス", keywords)

    def test_sentence1_never_headlines_with_structural_feature_alone(self):
        # 商品の種類が特定できない商品では、構造・仕様の単語（マグネットなど）を
        # 1文目（紹介文の主役）にせず、カテゴリ共通の用途ベースの文章を使う。
        item = make_item(name="マグネット式 収納ラック")
        sentence1, _emoji, product_type_matched = dg._build_sentence1(item["name"], "収納", seed=0)
        self.assertFalse(product_type_matched)
        self.assertIn(sentence1, dg.OPENING_FALLBACK_SENTENCES["収納"])

    def test_structural_feature_appears_only_as_reason_in_sentence2(self):
        # マグネット式の収納ラックのように商品の種類が特定できない場合でも、
        # 特徴自体は2文目に「〜なので、」という理由として自然に組み込まれる。
        item = make_item(name="マグネット式 収納ラック")
        description = dg.generate_description(item, category="収納", base_hashtags=BASE_HASHTAGS)
        self.assertIn("マグネットで浮かせて設置できるので、", description)


# 紹介文で使われうる絵文字をすべて集めた集合（テストでの絵文字カウント・検出に使う）。
def _all_known_emojis() -> set[str]:
    emojis: set[str] = set()
    for pool in dg.CATEGORY_EMOJIS.values():
        emojis.update(pool)
    for _keyword, _clause_spec, emoji_spec in dg.FEATURE_CLAUSES:
        if isinstance(emoji_spec, dict):
            emojis.update(v for v in emoji_spec.values() if v)
        elif emoji_spec:
            emojis.add(emoji_spec)
    for _keyword, _sentence, emoji in dg.PRODUCT_TYPE_HINTS:
        if emoji:
            emojis.add(emoji)
    return emojis


ALL_KNOWN_EMOJIS = _all_known_emojis()


class EmojiFormatTest(unittest.TestCase):
    """紹介文への絵文字の付け方を確認する。"""

    def _count_known_emojis(self, text: str) -> int:
        return sum(text.count(emoji) for emoji in ALL_KNOWN_EMOJIS)

    def test_total_emoji_count_is_within_expected_range(self):
        # 1投稿につき2〜4個程度、というルールの確認。
        item = make_item(name="テスト商品")
        for category in dg.CATEGORY_EMOJIS:
            description = dg.generate_description(item, category=category, base_hashtags=BASE_HASHTAGS)
            count = self._count_known_emojis(description)
            self.assertGreaterEqual(count, 2, f"category={category}: {description}")
            self.assertLessEqual(count, 4, f"category={category}: {description}")

    def test_sentences_end_with_emoji_not_start_with_it(self):
        # 絵文字は文末に自然に入れる。各行の先頭へ機械的に付けない、というルールの確認。
        item = make_item(name="テスト商品")
        for category in dg.CATEGORY_EMOJIS:
            description = dg.generate_description(item, category=category, base_hashtags=BASE_HASHTAGS)
            for line in _body_lines(description):
                self.assertFalse(
                    any(line.startswith(emoji) for emoji in ALL_KNOWN_EMOJIS),
                    f"category={category}: {line!r}",
                )
                self.assertTrue(
                    any(line.endswith(emoji) for emoji in ALL_KNOWN_EMOJIS),
                    f"category={category}: {line!r}",
                )

    def test_hashtag_line_has_no_emoji(self):
        item = make_item(name="テスト商品")
        for category in dg.CATEGORY_EMOJIS:
            description = dg.generate_description(item, category=category, base_hashtags=BASE_HASHTAGS)
            hashtag_line = description.splitlines()[-1]
            self.assertTrue(hashtag_line.startswith("#"), hashtag_line)
            for emoji in ALL_KNOWN_EMOJIS:
                self.assertNotIn(emoji, hashtag_line)

    def test_magnet_rack_uses_magnet_emoji(self):
        description = dg.generate_description(REAL_MAGNET_RACK, category="収納", base_hashtags=BASE_HASHTAGS)
        self.assertIn("🧲", description)

    def test_air_fryer_does_not_use_storage_emoji_for_capacity(self):
        # 「大容量」の絵文字も、収納カテゴリ向けの絵文字を時短カテゴリでは使わない。
        category = dg.refine_category(REAL_AIR_FRYER, "時短")
        description = dg.generate_description(REAL_AIR_FRYER, category=category, base_hashtags=BASE_HASHTAGS)
        self.assertNotIn("📦", description)

    def test_dedupe_adjacent_emojis_avoids_back_to_back_repeats(self):
        # 隣り合う文で同じ絵文字が続かないようにする_dedupe_adjacent_emojis()の確認。
        pool = ["🧹", "🧽", "✨", "😊", "♪"]
        parts = [("文1", "🧹"), ("文2", "🧹"), ("文3", "✨")]
        result = dg._dedupe_adjacent_emojis(parts, pool)
        emojis = [emoji for _text, emoji in result]
        self.assertNotEqual(emojis[0], emojis[1])

    def test_bulk_format_invariants_across_many_products(self):
        # 商品名・カテゴリを幅広く変えても、フォーマットのルール（箇条書きなし・
        # 文の数2〜3・絵文字数2〜4・ハッシュタグ行に絵文字なし）が常に守られることを
        # 確認する回帰テスト（本番で見つかった絵文字の重複バグの再発防止も兼ねる）。
        sample_names = [
            "マグネット式 収納ラック",
            "吸盤タイプ フック",
            "折りたたみ式 水切りかご",
            "スリムタイプ ゴミ箱",
            "大容量 保存容器セット",
            "軽量 掃除用モップ",
            "シリコン製 キッチンツール",
            "ステンレス製 調理器具",
            "蓋付き 収納ボックス",
            "充電式 コードレスクリーナー",
            "なんの変哲もない商品",
            "普通の便利グッズ",
        ]
        for category in dg.CATEGORY_EMOJIS:
            for i, name in enumerate(sample_names):
                item = make_item(name=name, item_code=f"{category}-{i}")
                description = dg.generate_description(item, category=category, base_hashtags=BASE_HASHTAGS)

                self.assertNotIn("・", description)

                lines = _body_lines(description)
                self.assertIn(len(lines), (2, 3), f"{category}/{name}: {lines}")

                count = self._count_known_emojis(description)
                self.assertGreaterEqual(count, 2, f"{category}/{name}: {description}")
                self.assertLessEqual(count, 4, f"{category}/{name}: {description}")

                hashtag_line = description.splitlines()[-1]
                for emoji in ALL_KNOWN_EMOJIS:
                    self.assertNotIn(emoji, hashtag_line, f"{category}/{name}: {hashtag_line}")


if __name__ == "__main__":
    unittest.main()
