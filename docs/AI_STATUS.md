# AI STATUS

Task ID: user-request-description-genre-013-final-review-fix（ユーザーからの直接依頼）
Status: DONE

## 最終更新

Claude Codeが、2026-09-30 15:51生成分の`room/data/candidates.json`の
最終レビューで残った3点（牛すじカレーの品質評価表現、PVCハンガーの
未確認の持ち運び用途、卓上扇風機の未確認の収納用途）だけを修正した。
**description-genre-012で確立した商品本体判定等の大きなロジックには
一切触れていない**。すでに正しいと確認された7商品のdescriptionも
変更していない。

## 1. 修正した3件

1. **牛すじカレー（curry-tokiya:10000000）**: 「専門店の味を自宅で
   楽しめる」（味の品質評価）を「牛すじカレーを自宅で楽しめる」に、
   「手軽に食事を済ませたい人におすすめ」（未確認の調理の手軽さ）を
   「牛すじカレーが気になる人におすすめ」に変更。
2. **PVCハンガー30本セット（shinbido:10002620）**: 「軽量」だけで
   「持ち運びしやすい」を生成しないよう、追加確認語（持ち運び/携帯/
   ポータブル）を要求する仕組みを新設。「衣類が滑り落ちるのを防ぎたい
   人に便利そう」（絶対的な効果保証）を「衣類が滑りにくいハンガーを
   探している人におすすめ」に変更。
3. **卓上扇風機（exception5251:10000042）**: 「吊り下げて収納できる」
   （category="収納"だけを根拠にした未確認の収納用途）を「吊り下げて
   使える」に変更。

## 2. 変更後のdescription

| item_code | 変更前の問題 | 変更後 |
|---|---|---|
| curry-tokiya:10000000 | 「専門店の味を自宅で楽しめる」「手軽に食事を済ませたい人におすすめ」 | 「牛すじカレーを自宅で楽しめる」「牛すじカレーが気になる人におすすめ」（3パックセット維持） |
| shinbido:10002620 | 「✔️ 持ち運びしやすい」「衣類が滑り落ちるのを防ぎたい人に便利そう」 | 「✔️ クローゼットをすっきり整えやすい」「衣類が滑りにくいハンガーを探している人におすすめ」（30本セット維持） |
| exception5251:10000042 | 「✔️ 吊り下げて収納できる」 | 「✔️ 吊り下げて使える」（マグネットリモコン誤認は引き続き発生せず） |

## 3. 回帰防止として変更した内容

- `_FEATURE_CLAUSE_REQUIRES_CONFIRMATION`を新設し`_top_feature_
  clause()`に組み込み。FEATURE_CLAUSESのキーワードごとに、追加で確認
  したい語（例：「軽量」→「持ち運び」「携帯」「ポータブル」）を登録
  できる汎用的な仕組み。該当語がタイトルに無ければその特徴は使わない。
- `FEATURE_CLAUSES`の「吊り下げ」を、category別のdict分岐（収納→
  「吊り下げて収納できる」）から、常に「吊り下げて使える」を使う単一
  の文字列に変更。categoryだけを根拠に具体的な用途へ拡張しないように
  した。
- 「牛すじカレー」テンプレートのchecklist_core・closing_variantsを
  品質評価・未確認の利便性を含まない表現に変更。
- 「ハンガー」テンプレートのclosing_variantsから絶対的な効果保証の
  表現を1件削除。

## 4. 追加テスト数

`tests/test_description_generator.py`に`Sept30FinalReviewFixTest`
（**9件**）を追加した。

## 5. 全テスト結果

`python3 -m pytest -q`と`python3 -m unittest discover -s tests`の両方で
**508件全て成功**（本タスク開始前は499件）。

## 6. 他7件が不変であること

`room/data/candidates.json`（2026-09-30 15:51生成分）のうち、指摘の
あった3商品以外の7商品（suzumura-shoten・honjien-3・sunsumarche・
ai-corp・polaristure・kiyokawa1981・g-sarai）の`description`は、
Pythonスクリプトで前回生成分と1バイトも変わっていないことを確認した
（回帰なし）。`git diff --stat room/data/candidates.json`でも変更が
`description`フィールド3件分のみであることを確認済み。

## 7. 10商品・順番・generated_at_jstが不変であること

Pythonスクリプトで新旧JSONを比較し、10商品全てで`item_code`・
`name`・`price`・`review_average`・`review_count`・`category`が完全
一致することを確認した。`generated_at_jst`（2026/09/30 15:51）・
items配列の順序・件数（10件）も無変更。

## 8. 商品選定ロジックを変更していないこと

`git status`で変更ファイルが`src/description_generator.py`・
`tests/test_description_generator.py`・`room/data/candidates.json`・
`docs/DESIGN.md`・`docs/AI_STATUS.md`のみであることを確認済み。
`src/ranking.py`・`src/main.py`・`select_top_candidates()`・
`daily_target`・`max_per_category`・重複防止・直近投稿の偏り調整・
`data/posted_items.json`・GitHub Actions実行時刻・楽天API認証情報・
投稿済み登録ワークフローには一切変更していない。

## 変更ファイル

- `src/description_generator.py`：`_FEATURE_CLAUSE_REQUIRES_
  CONFIRMATION`を新設し`_top_feature_clause()`に組み込み。FEATURE_
  CLAUSESの「吊り下げ」をcategory別dict分岐から単一文字列に変更。
  「牛すじカレー」テンプレートのchecklist_core/closing_variantsを
  変更。「ハンガー」テンプレートのclosing_variants 1件を変更。
- `tests/test_description_generator.py`：`Sept30FinalReviewFixTest`
  （9件）を追加。
- `room/data/candidates.json`：2026-09-30 15:51生成分のうち3商品
  （curry-tokiya・shinbido・exception5251）の`description`フィールド
  のみ再生成。他7商品は無変更。
- `docs/DESIGN.md`（46章に記録）・`docs/AI_STATUS.md`（このファイル）。

`src/ranking.py`・`src/main.py`・`src/dedupe.py`・`src/filters.py`・
`config/settings.example.yaml`・`data/posted_items.json`・
`room/index.html`・`.github/workflows/`・楽天API認証情報には一切変更
していない。

## 残る制約

- `_FEATURE_CLAUSE_REQUIRES_CONFIRMATION`は現在「軽量」のみ登録して
  いる。他のFEATURE_CLAUSESキーワードで同様の問題が見つかった場合は、
  同じ辞書へ追加する形で対応できる。
- 「吊り下げ」はcategoryに関わらず常に「吊り下げて使える」を使う
  （タイトルに「収納」が明記されていても、より具体的な表現へは拡張
  しない安全側のフォールバック）。
- 商品選定・カテゴリー割り当て自体は引き続き今回のスコープ外。

## 9. コミットID

このファイルの更新を含むコミットのハッシュは、コミット後にgit logで
確認できる（下記に反映）。

## セキュリティ

秘密情報（Rakuten Application ID、Access Key、各種トークン等）は
コード・ログ・README・本ファイルに一切含めていない。楽天ROOMへの
機械的な自動投稿・自動ログイン・購入操作は実装していない（本タスクの
変更は紹介文の文章内容のみ）。
