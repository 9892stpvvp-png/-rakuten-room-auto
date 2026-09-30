# AI STATUS

Task ID: user-request-description-genre-010-product-body-detection-generalization（ユーザーからの直接依頼）
Status: DONE

## 最終更新

Claude Codeが、2026-09-29 15:50生成分の`room/data/candidates.json`の
ユーザー手動レビューで指摘された4つの系統的な問題（特典語・用途語・
複合語の一部分の誤認、具体的商品名があるのに汎用ジャンルへフォール
バック）を、個別パッチではなく汎用的な仕組みとして修正した。**商品
選定・ランキング・数値判定の安定部分には触れていない**。

## 1. 根本原因

`_iter_product_type_keyword_matches()`が出現位置と登録順のみで優先度を
決めており、レビュー特典等の特典文脈の語句、および複合語の一部分と
既存の汎用キーワードとの競合を区別できていなかった。数量抽出側にも、
個数系の複数選択肢・単数表現・寸法ラベルの区別に対応する仕組みが
なかった。

## 2. 商品本体判定の改善方法

`_GENERIC_FALLBACK_PRODUCT_TYPE_KEYWORDS`に既存の汎用語「ハンガー」
「水垢」を追加し、より具体的な複合語（「ハンガーラック」「マルチ
クロス」等）が優先されるようにした。具体的商品名がある10件について
`PRODUCT_TYPE_TEMPLATES`へ新規複合語キーワードを追加し、汎用フォール
バックへ落ちないようにした。

## 3. 特典語の除外方法

`_PROMOTIONAL_MENTION_PREFIX_PATTERN`（レビューで/レビュー特典/レビュー
投稿で/購入特典/プレゼント/おまけ、のいずれかが直前にある場合に除外
する接頭辞パターン）を新設した。既存の`_FEATURE_MENTION_SUFFIX_
PATTERN`（接尾辞版）と対になる仕組みで、マッチ位置より前の部分文字列
に対して判定する。「レビューでスポンジ」の「スポンジ」は除外され、
本物の商品名としてのスポンジ商品は従来通り機能する。

## 4. 複合語優先の改善

新規12キーワード（おねしょズボン/おねしょパンツ/スタイ/お食事
エプロン/保冷バッグ/保冷ふろしき/もつ煮/モツ煮/ハンガーラック/
コートハンガー/マルチクロス/キッチンツール）を`PRODUCT_TYPE_
TEMPLATES`へ追加した。既存の優先度判定ロジック自体は変更していない。
なお「キッチンスポンジ」も当初追加したが、`match_product_type_
keyword()`が`main.py`の商品タイプ多様性ランキングと共有されている
ため既存ランキングテストが壊れ、キーワード追加自体を取り消して
`_PRODUCT_TYPE_HASHTAG_OVERRIDES`へのハッシュタグ追加のみで対応した
（商品タイプ判定は「スポンジ」のまま、ランキングに影響なし）。

## 5. 数値意味判定への影響

「耐荷重100kg」はdescription-genre-008で確立済みの`_is_confirmed_
kg_weight()`が既に正しく除外しており、新規コード追加は不要だった。
「幅90cm」「高さ180cm」の区別のため`_DIMENSION_LABEL_WORDS`・
`_DIMENSION_LABEL_WINDOW`（4文字）・`_dimension_label_for()`を新設し、
ラベル語が数値の直前4文字以内にあればそれを使い、なければ「サイズ」
にフォールバックする安全側の設計とした。

## 6. 新規対応商品タイプ

おねしょズボン・おねしょパンツ・スタイ・お食事エプロン・保冷バッグ・
保冷ふろしき・もつ煮・モツ煮・ハンガーラック・コートハンガー・
マルチクロス・キッチンツールの12種類。

## 7. 数量表現の改善

個数系の複数選択肢（「3袋 10袋 20袋」→「3袋・10袋・20袋から選べる」）
に対応する専用パターンを重量/サイズ系とは別に新設し、
`_phrase_for_size_options()`を拡張した。「1個セット」のような不自然な
表現を避けるため`_SINGLE_COUNT_QUANTITY_PATTERN`・`_IRI_SUFFIX_
PATTERN`を新設し早期リターンとして組み込んだ（2個以上のセット表記には
影響なし）。

## 8. ハッシュタグ改善

新規12キーワードと「スポンジ」に`_PRODUCT_TYPE_HASHTAG_OVERRIDES`の
エントリを追加し、具体的な商品タイプ名を反映したハッシュタグを使う
ようにした。

## 9. 追加テスト数

`tests/test_description_generator.py`に`Sept29BatchRegressionTest`
（**19件**）を追加した。

## 10. 全テスト結果

`python3 -m pytest -q`と`python3 -m unittest discover -s tests`の両方で
**460件全て成功**（本タスク開始前は441件）。

## 11. 今日の10件の最終確認結果

`room/data/candidates.json`（2026-09-29 15:50生成分）の全10商品の
`description`フィールドを最新ロジックで再生成し、人手で全件レビュー
した。ユーザー指摘の9件の`description`だけが変更され、回帰保存対象の
mugendo（稲庭うどん）は前回生成分から1バイトも変わっていないことを
Pythonスクリプトで確認した（回帰なし）。

| item_code | 商品 | 確認結果 |
|---|---|---|
| plusiine:10000361 | おねしょズボン | 「おねしょズボン」として判定、年齢・完全防水の断定なし、#キッズ用品 #おねしょズボン |
| wagaku0204:10000003 | スタイ/お食事エプロン | 「スタイ」として判定、防水性能の断定なし、#ベビー用品 #お食事エプロン |
| makuake-store:10001375 | 保冷バッグ ORIBA | 「保冷バッグ」として判定、容量の断定なし、#保冷バッグ #買い物グッズ |
| mugendo:10000081 | 稲庭うどん | **前回生成分から1バイトも変わらず（回帰なし）**、「6人前」維持、#グルメ #うどん |
| kan-etsubussan:10000031 | 国産豚のもつ煮 | 「3袋・10袋・20袋から選べる」、310g×3袋の誤計算なし、#グルメ #もつ煮 |
| bidoseikatsu:10000017 | 業務用ハンガーラック | 「ハンガーラック」として判定（ハンガーではない）、「幅は約90cm」、耐荷重100kgを重量と誤認せず、#収納 #ハンガーラック |
| charmying:10000057 | LR41ボタン電池 | 「1個」（「1個セット」ではない）、種別判定は従来通り維持 |
| dailymukuri:10000008 | マルチクロス3枚セット | 「マルチクロス」として判定、「研磨」「水垢」の混入なし |
| at-life:10029304 | キッチンスポンジ1個入 | 「1個入」（「1個セット」ではない）、種別判定（スポンジ）は維持、#キッチン用品 #キッチンスポンジ |
| shopmarna:10006689 | マーナ キッチンツール5点セット | 「キッチンツール」として判定（レビュー特典スポンジと誤認せず）、#キッチン用品 #キッチンツール |

不自然な数値表現・未確認の性能断定・タイトルにない語の混入は10件とも
残っていないことを確認した。全件500文字以内。

## 12. 商品・item_code・順番が変わっていないこと

`git diff --stat room/data/candidates.json`で変更が`description`
フィールド9件分のみであることを確認済み。加えてPythonスクリプトで
新旧JSONを比較し、10商品全てで`item_code`・`name`・`price`・
`review_average`・`review_count`・`category`が完全一致することを
確認した。`generated_at_jst`（2026/09/29 15:50）・items配列の順序・
件数（10件）も無変更。

## 13. 商品選定ロジックを変更していないこと

`git status`で変更ファイルが`src/description_generator.py`・
`tests/test_description_generator.py`・`room/data/candidates.json`・
`docs/DESIGN.md`・`docs/AI_STATUS.md`のみであることを確認済み。
`src/ranking.py`・`src/main.py`・`select_top_candidates()`・
`daily_target`・`max_per_category`・レビュー評価条件・レビュー件数
条件・重複防止・直近投稿の偏り調整・`data/posted_items.json`・
GitHub Actions実行時刻・楽天API認証情報・投稿済み登録ワークフローには
一切変更していない。開発中に一度「キッチンスポンジ」を商品タイプ
キーワードとして追加した際に商品タイプ多様性ランキングのテストが
壊れたため、そのキーワード追加のみを取り消して解決した（ランキング
ロジック自体は変更していない）。

## 変更ファイル

- `src/description_generator.py`：`_PROMOTIONAL_MENTION_PREFIX_
  PATTERN`を新設。`_GENERIC_FALLBACK_PRODUCT_TYPE_KEYWORDS`に
  「ハンガー」「水垢」を追加。`PRODUCT_TYPE_TEMPLATES`に12件の新規
  複合語キーワードを追加。`_PRODUCT_TYPE_HASHTAG_OVERRIDES`に12件+
  「スポンジ」のエントリを追加。`_DIMENSION_LABEL_WORDS`・
  `_DIMENSION_LABEL_WINDOW`・`_dimension_label_for()`を新設。
  `_QUANTITY_PATTERNS`に個数系複数選択肢パターンを追加し
  `_phrase_for_size_options()`を拡張。`_SINGLE_COUNT_QUANTITY_
  PATTERN`・`_IRI_SUFFIX_PATTERN`を新設し`_phrase_for_quantity()`に
  組み込み。
- `tests/test_description_generator.py`：`Sept29BatchRegressionTest`
  （19件）を追加。
- `room/data/candidates.json`：2026-09-29 15:50生成分のうち9商品
  （plusiine・wagaku0204・makuake-store・kan-etsubussan・
  bidoseikatsu・charmying・dailymukuri・at-life・shopmarna）の
  `description`フィールドのみ再生成。mugendoは無変更。
- `docs/DESIGN.md`（43章に記録）・`docs/AI_STATUS.md`（このファイル）。

`src/ranking.py`・`src/main.py`・`src/dedupe.py`・`src/filters.py`・
`config/settings.example.yaml`・`data/posted_items.json`・
`room/index.html`・`.github/workflows/`・楽天API認証情報には一切変更
していない。

## 残る制約

- `_PROMOTIONAL_MENTION_PREFIX_PATTERN`は「レビューで」「レビュー
  特典」「レビュー投稿で」「購入特典」「プレゼント」「おまけ」の
  直後に続く語のみを対象としている。これら以外の表現には対応して
  いない。
- `_GENERIC_FALLBACK_PRODUCT_TYPE_KEYWORDS`は個別に判明した汎用語を
  都度追加する方式のため、未知の複合語パターンには追加登録が必要。
- `_dimension_label_for()`のラベル判定窓は4文字固定。
- 商品選定・カテゴリー割り当て自体（検索元カテゴリーと実際の商品
  ジャンルの乖離）は引き続き今回のスコープ外。

## 14. コミットID

このファイルの更新を含むコミットのハッシュは、コミット後にgit logで
確認できる（下記に反映）。

## セキュリティ

秘密情報（Rakuten Application ID、Access Key、各種トークン等）は
コード・ログ・README・本ファイルに一切含めていない。楽天ROOMへの
機械的な自動投稿・自動ログイン・購入操作は実装していない（本タスクの
変更は紹介文の文章内容とハッシュタグのみ）。
