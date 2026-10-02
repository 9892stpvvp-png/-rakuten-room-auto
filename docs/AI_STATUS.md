# AI STATUS

Task ID: user-request-description-genre-016-no-evaluative-suffix-generalization（ユーザーからの直接依頼）
Status: DONE

## 最終更新

Claude Codeが、2026-10-02 15:51生成分の再確認で指摘された「確認できた
仕様・数量・素材・対応機能に、根拠のない評価・効果表現（使いやすい・
便利・置きやすい等）を機械的に付加している」というパターンを、個別
商品へのif分岐ではなく、問題の根本である共有定義（FEATURE_CLAUSES）
自体の修正として一般化対応した。**商品選定・ランキング・既存の3段階
判定構造には触れていない**。

## 1. 根本原因

`FEATURE_CLAUSES`の一部の共有エントリ（スリム・自立・耐熱）が、確認
できる事実に評価・効果表現を機械的に結合していた。加えて、直前のタスク
（description-genre-014/015）で新設したボール・コランダーセット／
レンジ調理器具／無洗米／ちりとりのテンプレートも、同じ傾向で書かれて
いた。

## 2. 一般化した修正内容

個別商品への`if`分岐は追加せず、共有定義そのものを事実だけの言い回しに
修正した（該当キーワードを含む全ての商品に一度に反映される）。

- `FEATURE_CLAUSES`「スリム」：「省スペースに置きやすい」→「スリムな
  形状」。
- `FEATURE_CLAUSES`「自立」：「自立して置き場所を選びにくい」→
  「自立する仕様」。
- `FEATURE_CLAUSES`「耐熱」：「耐熱素材で使いやすい」→「耐熱素材」。
- 「無洗米」のchecklist_fallback：「ストックしておくと便利」→
  「令和7年産」（確認できる別の事実）。
- 「ちりとり」のchecklist_core：「自立して置きやすい」を削除し
  「ゴミ袋を装着して使える」に置き換え（FEATURE_CLAUSESとの重複回避）。
- 「ボール・コランダーセット」のchecklist_core：「食洗機対応で使い
  やすい」→「食洗機対応」。
- 「レンジ調理器具」のchecklist_core：「焼き料理に使いやすい」→
  「焼き料理に使える」。

「電子レンジで使える」「食洗機で洗える」「マグネットで取り付けられる」
「詰め替えタイプで使いやすい」「フタ付きで使いやすい」等、過去タスクで
既に承認済みの能力表現には触れていない。対象は④✔️メリットの箇条書き
（仕様・数量・サイズ・素材・対応機能の説明）に限定し、共感型6ブロック
の雰囲気（①〜③の導入文・⑤締めの一言）は維持した。

## 3. 追加テスト数

`tests/test_description_generator.py`に`NoEvaluativeSuffixGeneralization
Test`（**11件**）を追加した。

## 4. 全テスト数と結果

`python3 -m pytest -q`と`python3 -m unittest discover -s tests`の両方で
**562件全て成功**（本タスク開始前は551件）。既存テストのうち、新しい
事実表現に合わせて期待値を更新したのは3件（「自立」関連2件、「食洗機
対応」関連1件）。検証している挙動自体（付属品属性の除外・商品本体
判定）は変わっていない。

## 5. 変更されたdescription

| item_code | 商品 | 変更内容 |
|---|---|---|
| hseason:10000349 | 無洗米 | 「✔️ ストックしておくと便利」→「✔️ 令和7年産」 |
| winkl:10000154 | ちりとり | 「✔️ 自立して置きやすい」「✔️ 省スペースに置きやすい」→「✔️ ゴミ袋を装着して使える」「✔️ スリムな形状」 |
| risu-onlineshop:10002535 | ボール・コランダーセット | 「✔️ 食洗機対応で使いやすい」「✔️ 耐熱素材で使いやすい」→「✔️ 食洗機対応」「✔️ 耐熱素材」 |
| justrich:10001292 | レンジ調理器具 | 「✔️ 焼き料理に使いやすい」→「✔️ 焼き料理に使える」（「✔️ 電子レンジで使える」は事実表現のため維持） |

## 6. 10件の人手確認結果

`room/data/candidates.json`（2026-10-02 15:51生成分）のうち、評価語の
自動付加が見つかった4商品の`description`フィールドのみ再生成し、
10件全件を人手でレビューした。残り6商品（sinkatec・rakuten24・
campaign365・marubeni-pps・mamano・roomy）は前回生成分から1バイトも
変わっていないことをPythonスクリプトで確認した（回帰なし）。文章だけ
で何の商品か分かること、商品本体がcategoryより優先されていること、
数値・数量の意味が正しいこと、仕様・数量に根拠のない評価語を追加して
いないこと、未確認の性能・効果を推測していないこと、旧汎用タグが残って
いないこと、具体的な商品タグになっていること、全件500文字以内（152〜
196文字）であることを確認した。

## 7. 商品・順番・generated_at_jstが不変であること

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

- `src/description_generator.py`：`FEATURE_CLAUSES`の「スリム」「自立」
  「耐熱」3エントリを事実表現に変更。「無洗米」「ちりとり」「ボール・
  コランダーセット」（2キーワード分）「レンジ調理器具」（3キーワード
  分）テンプレートのchecklist_core/checklist_fallbackを変更。
- `tests/test_description_generator.py`：`NoEvaluativeSuffixGeneralization
  Test`（11件）を追加。既存テスト3件の期待値を新しい事実表現に更新。
- `room/data/candidates.json`：2026-10-02 15:51生成分のうち4商品
  （hseason・winkl・risu-onlineshop・justrich）の`description`
  フィールドのみ再生成。他6商品は無変更。
- `docs/DESIGN.md`（49章に記録）・`docs/AI_STATUS.md`（このファイル）。

`src/ranking.py`・`src/main.py`・`src/dedupe.py`・`src/filters.py`・
`config/settings.example.yaml`・`data/posted_items.json`・
`room/index.html`・`.github/workflows/`・楽天API認証情報には一切変更
していない。

## 残る制約

- 今回のFEATURE_CLAUSES修正は「スリム」「自立」「耐熱」の3エントリに
  限定している。他の共有エントリで同様の評価語自動付加が今後見つかれば
  同じ考え方で修正できる。
- 商品選定・カテゴリー割り当て自体は引き続き今回のスコープ外。

## 9. コミットID

このファイルの更新を含むコミットのハッシュは、コミット後にgit logで
確認できる（下記に反映）。

## セキュリティ

秘密情報（Rakuten Application ID、Access Key、各種トークン等）は
コード・ログ・README・本ファイルに一切含めていない。楽天ROOMへの
機械的な自動投稿・自動ログイン・購入操作は実装していない（本タスクの
変更は紹介文の文章内容のみ）。
