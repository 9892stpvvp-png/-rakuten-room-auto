# AI STATUS

Task ID: user-request-description-genre-012-product-body-over-category（ユーザーからの直接依頼）
Status: DONE

## 最終更新

Claude Codeが、2026-09-30 15:51生成分の`room/data/candidates.json`の
ユーザー手動レビューで指摘された新系統の問題（categoryと商品タイトル
から確認できる本体が食い違う商品、否定文脈の誤認、付属品属性の誤転写、
新しい数量表記の形）を、個別パッチではなく汎用的な仕組みで修正した。
**商品選定・ランキング・既存の3段階判定構造には触れていない**。

## 1. 今回の根本原因

`_select_template()`の判定順位（PRODUCT_TYPE_TEMPLATES→GENERIC_
TEMPLATES[category]）自体はすでに商品名優先の設計だったが、フェイス
ローラー・ベビー枕・ハンドスピナー・ハンバーグ・牛すじカレー・次亜
塩素酸水・石鹸カス用スクレーパーのキーワードが未登録だったため、
category任せの安全フォールバックに落ちていた。

## 2. 商品本体 > categoryの改善方法

3段階構造は変更せず、具体的な商品本体を示す7キーワードを`PRODUCT_
TYPE_TEMPLATES`へ追加した。これにより、category=掃除でもフェイス
ローラーは美容ケア用品として、category=キッチンでも次亜塩素酸水は
除菌・消臭用品として、商品名からの判定が自動的に優先される。

## 3. 「業務用」の誤解釈防止

`FEATURE_CLAUSES`の「業務用」→「業務用サイズでたっぷり使いやすい」を
削除した。「業務用」は販売上の属性であり、商品の実際のサイズ・容量を
保証しない。具体的な容量・重量・寸法・個数が明記されている場合のみ、
その数値をそのまま使う。

## 4. 複合数量の意味判定改善

「5g x 50p（250g）」のような、1包あたりの重量×包数（p/P表記）＋括弧内
合計の表記を専用パターンで抜き出し、「5g×50包・計250g」に組み立て
直す`_PACK_WITH_PAREN_TOTAL_PATTERN`を新設した。

## 5. A×B/C型数量の改善

「130g×10個/20個」のような、1単位あたりの内容量×個数の直後に「/」で
区切った別の個数が続く表記を`_UNIT_LEADING_COUNT_OPTIONS_PATTERN`で
抜き出し、「1個あたり130g・10個または20個から選べる」に組み立て直す。
最初の個数だけに固定しない。

## 6. 否定文脈の判定改善

`_NEGATION_MENTION_SUFFIX_PATTERN`（「ではない」「では◯◯ない」
「不使用」）・`_NEGATION_MENTION_PREFIX_PATTERN`（「非」）を新設し、
`_iter_product_type_keyword_matches()`に組み込んだ。「レトルトでは
味わえない本格カレー」の「レトルト」を商品本体判定から除外する。

## 7. 付属品属性の誤転写防止

`_ACCESSORY_NOUN_BEFORE_SUFFIX_PATTERN`を新設し、`_top_feature_
clause()`に組み込んだ。「マグネットリモコン付き」の「マグネット」を
扇風機本体の仕様と誤認しないようにした（キーワード直後に別の名詞を
はさんで「付き」が続く場合だけ除外し、「マグネット付き」のように
直接続く場合は従来どおり本体の特徴として扱う）。

## 8. 健康/美容/衛生表現の安全化

フェイスローラー（血行促進・むくみ・リフトアップ等）、ベビー枕
（絶壁防止・吐き戻し防止等）、次亜塩素酸水（無害・除菌効果等）に
ついて、いずれも効果の断定を含まない安全なテンプレートを新設した
（確認できる用途・仕様・位置づけだけを反映）。

## 9. 新しく追加した商品タイプ

石鹸カス／スクレーパー、フェイスローラー、ベビー枕／ベビーピロー、
ハンドスピナー、ハンバーグ、牛すじカレーの6商品タイプ7キーワード。

## 10. ハッシュタグ改善

新規7キーワード＋既存の「ハンガー」に`_PRODUCT_TYPE_HASHTAG_
OVERRIDES`を追加（#暮らしの便利グッズ・#便利グッズを排除）。加えて、
商品本体判定済みの商品にSUBTOPIC_HASHTAGS（場所を示す語からの追加
タグ）が用途列挙由来の誤ったジャンルタグ（例：次亜塩素酸水の
「#キッチングッズ」）を紛れ込ませる問題を修正し、商品本体判定が
確認できる場合はSUBTOPIC_HASHTAGSを追加しないようにした。

## 11. 追加テスト数

`tests/test_description_generator.py`に`Sept30BatchRegressionTest`
（23件）・`NegationContextGeneralizationTest`（4件）・
`AccessoryAttributionGeneralizationTest`（2件）の計**29件**を追加した。

## 12. 全テスト結果

`python3 -m pytest -q`と`python3 -m unittest discover -s tests`の両方で
**499件全て成功**（本タスク開始前は470件）。

## 13. 9/30の10件の最終確認結果

`room/data/candidates.json`（2026-09-30 15:51生成分）の全10商品の
`description`フィールドを最新ロジックで再生成し、人手で全件レビュー
した。

| item_code | 商品 | 確認結果 |
|---|---|---|
| suzumura-shoten:10000014 | 石鹸カス用スクレーパー | 「スクレーパー」として判定、業務用→サイズ変換なし、#掃除グッズ #お風呂掃除 |
| honjien-3:10003226 | 韃靼そば茶 | 「5g×50包・計250g」、重さは約5gの誤記なし、#お茶 #韃靼そば茶 |
| sunsumarche:10000989 | HALIFTフェイスローラー | category=掃除でも「フェイスローラー」として判定、美容効果の断定なし、#美容グッズ #フェイスケア |
| ai-corp:10000095 | ベビー枕 | 「枕」として具体的判定、健康効果の断定なし、#ベビー用品 #ベビー枕 |
| polaristure:10000000 | ハンドスピナー3点セット | 「ハンドスピナー」として判定、3点セット正しく反映、#ベビー用品 #赤ちゃんおもちゃ |
| kiyokawa1981:10000021 | デミソースハンバーグ | 「1個あたり130g・10個または20個から選べる」、#グルメ #ハンバーグ |
| curry-tokiya:10000000 | 牛すじカレー | 「レトルトでは味わえない」を誤認せず「牛すじカレー」として判定、#グルメ #カレー |
| shinbido:10002620 | PVCハンガー30本セット | 30本セット維持、旧汎用タグ削除、#収納 #ハンガー |
| g-sarai:10000074 | サライウォーター次亜塩素酸水 | category=キッチンでも「次亜塩素酸水」として判定、安全性の過剰断定なし、「容量は2L」（約なし）、#衛生用品 #次亜塩素酸水 |
| exception5251:10000042 | 卓上扇風機 | マグネットリモコン付きを本体マグネット設置と誤認せず、#家電 #扇風機 |

不自然な数値表現・未確認の健康/美容/衛生効果の断定・付属品属性の誤
転写・用途語由来の誤ったハッシュタグは10件とも残っていないことを
確認した。全件500文字以内（152〜202文字）。

## 14. 10商品・item_code・順番・generated_at_jstが不変であること

`git diff --stat room/data/candidates.json`で変更が`description`
フィールド10件分のみであることを確認済み。加えてPythonスクリプトで
新旧JSONを比較し、10商品全てで`item_code`・`name`・`price`・
`review_average`・`review_count`・`category`が完全一致することを
確認した。`generated_at_jst`（2026/09/30 15:51）・items配列の順序・
件数（10件）も無変更。

## 15. 商品選定ロジックを変更していないこと

`git status`で変更ファイルが`src/description_generator.py`・
`tests/test_description_generator.py`・`room/data/candidates.json`・
`docs/DESIGN.md`・`docs/AI_STATUS.md`のみであることを確認済み。
`src/ranking.py`・`src/main.py`・`select_top_candidates()`・
`daily_target`・`max_per_category`・評価4.0以上条件・レビュー100件
以上条件・重複防止・直近投稿の偏り調整・`data/posted_items.json`・
GitHub Actions実行時刻・楽天API認証情報・投稿済み登録ワークフローには
一切変更していない。

## 変更ファイル

- `src/description_generator.py`：FEATURE_CLAUSESから「業務用」を削除。
  `_NEGATION_MENTION_SUFFIX_PATTERN`・`_NEGATION_MENTION_PREFIX_
  PATTERN`を新設し`_iter_product_type_keyword_matches()`に組み込み。
  `_ACCESSORY_NOUN_BEFORE_SUFFIX_PATTERN`を新設し`_top_feature_
  clause()`に組み込み。`PRODUCT_TYPE_TEMPLATES`に7キーワードを追加。
  `_UNIT_LEADING_COUNT_OPTIONS_PATTERN`・`_PACK_WITH_PAREN_TOTAL_
  PATTERN`・「N点セット」パターンを新設し`_QUANTITY_PATTERNS`・
  `_phrase_for_quantity()`に組み込み。容量（ml/L）の言い回しから「約」
  を削除。`_PRODUCT_TYPE_HASHTAG_OVERRIDES`に8キーワード（新規7＋
  ハンガー）を追加。`_build_hashtags()`でSUBTOPIC_HASHTAGSを
  override_tagsがある場合はスキップするよう変更。
- `tests/test_description_generator.py`：`Sept30BatchRegressionTest`
  （23件）・`NegationContextGeneralizationTest`（4件）・
  `AccessoryAttributionGeneralizationTest`（2件）を追加。
- `room/data/candidates.json`：2026-09-30 15:51生成分の全10商品の
  `description`フィールドを再生成。
- `docs/DESIGN.md`（45章に記録）・`docs/AI_STATUS.md`（このファイル）。

`src/ranking.py`・`src/main.py`・`src/dedupe.py`・`src/filters.py`・
`config/settings.example.yaml`・`data/posted_items.json`・
`room/index.html`・`.github/workflows/`・楽天API認証情報には一切変更
していない。

## 残る制約

- `_NEGATION_MENTION_SUFFIX_PATTERN`は「ではない」「では◯◯ない」
  「不使用」の直後に続く語のみを対象としている。
- `_ACCESSORY_NOUN_BEFORE_SUFFIX_PATTERN`はキーワード直後に別の名詞＋
  「付き」が続く形だけを対象としている。
- SUBTOPIC_HASHTAGSは、商品本体判定済みの商品では一律で追加しない
  設計にしたため、場所別の補足タグを追加したい場合は個別に
  `_PRODUCT_TYPE_HASHTAG_OVERRIDES`へ登録する必要がある。
- 商品選定・カテゴリー割り当て自体は引き続き今回のスコープ外。

## 16. コミットID

このファイルの更新を含むコミットのハッシュは、コミット後にgit logで
確認できる（下記に反映）。

## セキュリティ

秘密情報（Rakuten Application ID、Access Key、各種トークン等）は
コード・ログ・README・本ファイルに一切含めていない。楽天ROOMへの
機械的な自動投稿・自動ログイン・購入操作は実装していない（本タスクの
変更は紹介文の文章内容とハッシュタグのみ）。
