# AI STATUS

Task ID: user-request-description-genre-014-015-unknown-product-type-generalization（ユーザーからの直接依頼、2件連続）
Status: DONE

## 最終更新

Claude Codeが、2026-10-01 15:51生成分と2026-10-02 15:51生成分の2件の
レビューで指摘された「商品タイトルに具体的な商品本体が明記されている
にもかかわらず、未知の商品タイプだとcategory由来の汎用descriptionへ
戻ってしまう」問題を、個別パッチの積み重ねではなく一般化した仕組みで
解決した。**商品選定・ランキング・既存の3段階判定構造には触れていない**。

## 1. 10/2で追加対応した内容

description-genre-014（10/1分、新規キーワード9商品タイプ14件＋未知の
商品タイプへの一般化フォールバック）を実装した後、10/2分のレビューで
さらに4商品タイプ（無洗米・ヘアーキャッチャー・ボール・コランダー
セット・レンジ調理器具）とその数量/寸法表現の問題が見つかったため、
同じ一般化ロジックの枠内で追加対応した（description-genre-015）。
前回から継続していた4商品（トイレクリーナー・除菌ウェットティッシュ・
温湿度計・ちりとり）は、個別パッチを重ねず、既存の一般化ロジックのみ
で正しく判定されることを確認した。

## 2. 10件すべての変更後description

| item_code | 商品 | 変更後 |
|---|---|---|
| hseason:10000349 | 無洗米（北海道産ななつぼし） | 「研がずに使える無洗米◎」「5kg×2袋・合計10kg」#お米 #無洗米 |
| sinkatec:10000428 | ヘアーキャッチャー | 「排水口のお手入れに使いやすいヘアーキャッチャー◎」「直径140mm」（約なし）#お風呂掃除 #ヘアーキャッチャー |
| rakuten24:11279561 | アリエール（洗濯洗剤） | 「1000g×4セット」（使いやすい付加なし）#洗濯洗剤 #アリエール |
| campaign365:10000008 | トイレクリーナー | 「トイレのお手入れに使うクリーナー◎」#掃除グッズ #トイレ掃除 |
| marubeni-pps:10000026 | 除菌ウェットティッシュ | 「80枚入り・3個・6個・12個から選べる」#日用品 #ウェットティッシュ |
| mamano:10000068 | 食器用洗剤 | 「毎日の食器洗いに使いやすそうな食器用洗剤◎」手肌効果の断定なし #食器用洗剤 #キッチン用品 |
| roomy:10008839 | 温湿度計 | 「温度と湿度を確認しやすい温湿度計◎」#温湿度計 #温度計 |
| winkl:10000154 | ちりとり | 「屋外の掃き掃除に使いやすいちりとり◎」45L/70Lの数量断定なし #掃除グッズ #ちりとり |
| risu-onlineshop:10002535 | ボール・コランダーセット | 「ザルとボウルが一緒に使えるボール・コランダーセット◎」#キッチン用品 #ボウル |
| justrich:10001292 | レンジ調理器具 | 「レンジで使えるレンジ調理器具◎」未確認の焼き性能なし #キッチン用品 #電子レンジ調理器 |

## 3. 追加した汎用ルール

1. **`_extract_repeated_noun_candidate()`**：PRODUCT_TYPE_TEMPLATESに
   未登録の商品でも、商品名の中で2回以上登場する語句（販促語・
   カテゴリー名等のdenylistを除く）を安全な商品本体候補として拾い、
   GENERIC_TEMPLATESのsolution_text・ハッシュタグに反映する。自由
   生成・推測は行わず、該当候補が無ければ従来どおり安全フォール
   バックのまま。
2. **`_QUANTITY_EXTRACTION_SUPPRESSED_FOR_PRODUCT_TYPE`**：数値の意味が
   商品タイトルだけでは一意に確定できない商品タイプ（例：ちりとりの
   「45L 70L」）では、数量抽出自体を行わない。
3. **`_WEIGHT_OR_VOLUME_LEADING_PATTERN`**：重さ/容量が先頭にある
   組み合わせ（「180g×4袋」「1000g×4セット」等）には「で使いやすい」
   を機械的に付加しない。
4. **`_WEIGHT_TOTAL_WITH_PACK_BREAKDOWN_PATTERN`**：「10kg 5kg×2袋」の
   ような合計量＋パック内訳の表記を、選択肢一覧と誤認せず「5kg×2袋・
   合計10kg」に組み立て直す。
5. **`_SIZE_PHRASE_EXACT_FOR_PRODUCT_TYPE`**：タイトル自体に「約」が
   無い明確な寸法表記（例：「直径140mm」）では、商品タイプ単位で
   「約」の付加を止められる。
6. **`_PACKAGE_CONTENT_WITH_COUNT_OPTIONS_PATTERN`・`_SERVINGS_SET_
   WITH_COUNT_PATTERN`**：「80枚入 3個 6個 12個」「6人前セット 3袋」の
   ような内容量＋選択肢の表記を分けて示す。
7. 商品本体判定済みの商品では、`_build_hashtags()`でbase_hashtags・
   #便利グッズ・#時短アイテムを機械的に付けない（未知の商品タイプ
   フォールバックでも同様）。

## 4. 追加テスト数

`tests/test_description_generator.py`に`Oct01BatchRegressionTest`
（25件）・`RepeatedNounCandidateGeneralizationTest`（3件）・
`Oct02BatchRegressionTest`（15件）の計**43件**を追加した。

## 5. 全テスト数と結果

`python3 -m pytest -q`と`python3 -m unittest discover -s tests`の両方で
**551件全て成功**（本タスク開始前は508件）。

## 6. 10件の人手確認結果

`room/data/candidates.json`（2026-10-02 15:51生成分）の全10商品の
`description`フィールドを最新ロジックで再生成し、人手で全件レビュー
した。文章だけで何の商品か分かること、商品本体がcategoryより優先
されていること、数量・寸法の意味が正しいこと、「約」を勝手に追加して
いないこと、未確認の用途・性能・健康/衛生/肌への効果を追加していない
こと、旧汎用タグが残っていないこと、具体的な商品タグになっていること、
紹介文＋ハッシュタグが一続きであること、全件500文字以内（155〜196
文字）であることを確認した。

## 7. 10商品・順番・generated_at_jstが不変であること

Pythonスクリプトで新旧JSONを比較し、10商品全てで`item_code`・
`name`・`price`・`review_average`・`review_count`・`category`が完全
一致することを確認した。`generated_at_jst`（2026/10/02 15:51）・
items配列の順序・件数（10件）も無変更。

## 8. 商品選定ロジックを変更していないこと

`git status`で変更ファイルが`src/description_generator.py`・
`tests/test_description_generator.py`・`room/data/candidates.json`・
`docs/DESIGN.md`・`docs/AI_STATUS.md`のみであることを確認済み。
`src/ranking.py`・`src/main.py`・`select_top_candidates()`・
`daily_target`・`max_per_category`・評価4.0以上条件・レビュー100件
以上条件・重複防止・直近投稿の偏り調整・`data/posted_items.json`・
GitHub Actions実行時刻・楽天API認証情報・投稿済み登録ワークフローには
一切変更していない。

## 変更ファイル

- `src/description_generator.py`：`_extract_repeated_noun_candidate()`・
  `_apply_repeated_noun_candidate()`を新設し`_select_template()`・
  `_build_hashtags()`に組み込み。`_QUANTITY_EXTRACTION_SUPPRESSED_
  FOR_PRODUCT_TYPE`・`_WEIGHT_OR_VOLUME_LEADING_PATTERN`・
  `_WEIGHT_TOTAL_WITH_PACK_BREAKDOWN_PATTERN`・`_SIZE_PHRASE_EXACT_
  FOR_PRODUCT_TYPE`・`_PACKAGE_CONTENT_WITH_COUNT_OPTIONS_PATTERN`・
  `_SERVINGS_SET_WITH_COUNT_PATTERN`を新設し`_build_checklist()`・
  `_phrase_for_quantity()`・`_extract_quantity_phrase()`に組み込み。
  `PRODUCT_TYPE_TEMPLATES`に13商品タイプ・21キーワードを追加。
  `_PRODUCT_TYPE_HASHTAG_OVERRIDES`に対応するエントリ（「アリエール」
  「食器用洗剤」を含む）を追加。
- `tests/test_description_generator.py`：`Oct01BatchRegressionTest`
  （25件）・`RepeatedNounCandidateGeneralizationTest`（3件）・
  `Oct02BatchRegressionTest`（15件）を追加。
- `room/data/candidates.json`：2026-10-02 15:51生成分の全10商品の
  `description`フィールドを再生成。
- `docs/DESIGN.md`（47・48章に記録）・`docs/AI_STATUS.md`（このファイル）。

`src/ranking.py`・`src/main.py`・`src/dedupe.py`・`src/filters.py`・
`config/settings.example.yaml`・`data/posted_items.json`・
`room/index.html`・`.github/workflows/`・楽天API認証情報には一切変更
していない。

## 残る制約

- `_extract_repeated_noun_candidate()`は「2回以上登場する語句」という
  弱い手がかりに依存する。denylistに登録されていない販促語が偶然2回
  登場した場合に誤って拾う可能性があり、今後見つかれば追加登録する。
- `_SIZE_PHRASE_EXACT_FOR_PRODUCT_TYPE`は現在「ヘアーキャッチャー」の
  みを登録している。
- 「レンジで焼ケール」の「角型・丸型・深型」は、数値を伴わない選択肢
  表記のため確認する仕組みが無く、今回は安全側に倒して紹介文に含めて
  いない。
- 商品選定・カテゴリー割り当て自体は引き続き今回のスコープ外。

## 9. コミットID

このファイルの更新を含むコミットのハッシュは、コミット後にgit logで
確認できる（下記に反映）。

## セキュリティ

秘密情報（Rakuten Application ID、Access Key、各種トークン等）は
コード・ログ・README・本ファイルに一切含めていない。楽天ROOMへの
機械的な自動投稿・自動ログイン・購入操作は実装していない（本タスクの
変更は紹介文の文章内容とハッシュタグのみ）。
