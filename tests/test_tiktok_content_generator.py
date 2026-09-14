"""src/tiktok_content_generator.py のテスト。

実行方法:
    python -m unittest tests.test_tiktok_content_generator -v
"""

from __future__ import annotations

import unittest

from src import tiktok_content_generator as tcg


def make_item(name: str, category: str, group_label: str = "便利グッズ", item_code: str = "") -> dict:
    return {
        "item_code": item_code or name,
        "name": name,
        "price": 1980,
        "review_average": 4.6,
        "review_count": 500,
        "item_url": "https://item.rakuten.co.jp/shop/example/",
        "image_url": "https://example.com/example.jpg",
        "description": "",
        "category": category,
        "group_label": group_label,
    }


# 実際に本番のROOM候補として選ばれた商品名（2026-09-14実行分）を使った回帰テスト用データ。
REAL_ITEMS = [
    make_item(
        "【雑誌&TV等紹介】魔法のテープ 正規品 高品質 はがせる 水洗い 両面テープ ナノテープ "
        "透明両面テープ 強力両面テープ 超強力 魔法のテープ極 粘着 強力 固定 防災 地震対策 "
        "（幅3cm 長さ1M）万能 送料無料 SNSでも話題! あす楽 便利グッズ 浮かせる収納 壁紙 車 DIY 多用途",
        "収納",
    ),
    make_item(
        "【楽天1位★P6倍 生活の便利グッズ！】三角コーナー 浮かせる 本体 三角コーナー いらず "
        "強力吸盤 ステンレス製 水切りネットホルダー 対応 生ごみスタンド 折りたたみ ネット 50枚付き "
        "省スペース キッチンドレイン キッチン雑貨 水槽対応 生ゴミホルダー 生ゴミ処理",
        "キッチン",
    ),
    make_item(
        "【限定価格+特典あり】◆楽天1位3冠◆ スープメーカー 時短家電 ポタージュ スムージー "
        "冷製スープ 離乳食 豆乳 ブレンダー 自動調理ポット 全自動調理器 ミキサー おかゆ おから "
        "タイパ ミキサー シャーベット アイス 氷OK カレー 育児 出産祝い ギフト プレゼント LARUTAN",
        "時短",
    ),
    make_item(
        "水 ミネラルウォーター 熊野古道水 2L 12本 送料無料 天然水 軟水『送料無料（一部地域除く）』",
        "水",
        group_label="飲料",
    ),
    make_item(
        "【ふるさと納税】 【配送月が選べる】 トイレットペーパー ダブル 便利な小容量登場 再生紙 "
        "24ロールor64ロールor72ロール 日用品 フルーツカラー ブルーベリー ミックスベリー トロピカル "
        "香料 香り付き 消耗品 備蓄 生活用品 鶴見製紙 トイレ用品 沼津市 静岡県",
        "日用品",
        group_label="消耗品",
    ),
]


class BuildContentTest(unittest.TestCase):
    def test_never_generates_banned_phrases(self):
        for item in REAL_ITEMS:
            content = tcg.build_content(item)
            combined = "\n".join(
                [content.script, content.narration, content.caption]
                + content.telops
                + content.video_notes
            )
            for phrase in tcg.BANNED_PHRASES:
                self.assertNotIn(
                    phrase, combined, f"{item['name'][:20]}: 禁止表現「{phrase}」が含まれています"
                )

    def test_telops_are_short_and_within_count_range(self):
        for item in REAL_ITEMS:
            content = tcg.build_content(item)
            self.assertGreaterEqual(len(content.telops), 5)
            self.assertLessEqual(len(content.telops), 7)
            for telop in content.telops:
                self.assertLessEqual(len(telop), 30, f"テロップが長すぎます: {telop!r}")

    def test_hashtags_within_count_range_and_no_purchase_claim_tags(self):
        for item in REAL_ITEMS:
            content = tcg.build_content(item)
            self.assertGreaterEqual(len(content.hashtags), 5)
            self.assertLessEqual(len(content.hashtags), 8)
            for tag in content.hashtags:
                self.assertNotIn("購入品", tag)
                self.assertNotIn("買ってよかった", tag)

    def test_script_duration_is_roughly_15_to_20_seconds(self):
        for item in REAL_ITEMS:
            content = tcg.build_content(item)
            duration = tcg.estimate_duration_seconds(content.narration)
            # 商品名の長さ・テンプレート内容によって多少前後するため、
            # 「15〜20秒程度」に対して余裕を持たせた範囲で確認する。
            self.assertGreaterEqual(duration, 13.0, f"{item['name'][:20]}: {duration}秒")
            self.assertLessEqual(duration, 23.0, f"{item['name'][:20]}: {duration}秒")

    def test_narration_ends_with_room_call_to_action(self):
        for item in REAL_ITEMS:
            content = tcg.build_content(item)
            self.assertTrue(content.narration.endswith("楽天ROOMに載せています。"))
            self.assertTrue(content.caption.endswith("楽天ROOMに載せています。"))

    def test_json_serializable_output_shape(self):
        content = tcg.build_content(REAL_ITEMS[0])
        self.assertIsInstance(content.script, str)
        self.assertIsInstance(content.telops, list)
        self.assertTrue(all(isinstance(t, str) for t in content.telops))
        self.assertIsInstance(content.narration, str)
        self.assertIsInstance(content.caption, str)
        self.assertIsInstance(content.hashtags, list)
        self.assertTrue(all(isinstance(h, str) for h in content.hashtags))
        self.assertIsInstance(content.video_notes, list)
        self.assertTrue(all(isinstance(n, str) for n in content.video_notes))

    def test_consumable_group_item_still_generates_valid_content(self):
        # 消耗品・飲料が選ばれた場合でも、体験談を装わない安全な文面を生成できる。
        water_item = REAL_ITEMS[3]
        content = tcg.build_content(water_item)
        self.assertIn("楽天ROOMに載せています", content.script)
        for phrase in tcg.BANNED_PHRASES:
            self.assertNotIn(phrase, content.caption)


if __name__ == "__main__":
    unittest.main()
