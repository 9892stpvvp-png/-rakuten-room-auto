# AI STATUS

Task ID: user-request-description-genre-011-final-review-fix（ユーザーからの直接依頼）
Status: DONE

## 最終更新

Claude Codeが、2026-09-29 15:50生成分の`room/data/candidates.json`の
最終レビューで残った3点（おねしょズボンの不自然な用途表現、もつ煮の
未確認な調理方法、ハンガーラックの寸法/耐荷重の情報不足）だけを修正
した。**すでに正しいと確認された7商品のdescription、商品選定・
ランキング・商品タイプ判定の大きな仕組みには一切触れていない**。

## 1. 修正した3点

1. **おねしょズボン（plusiine:10000361）**: `FEATURE_CLAUSES`の
   「防水」キーワードが「完全防水」に反応し、「水回りでも使いやすい」
   という不自然な用途表現を機械的に付けていた。商品タイプ単位で
   FEATURE_CLAUSESの特定キーワードを除外できる`_FEATURE_CLAUSE_
   SUPPRESSED_FOR_PRODUCT_TYPE`を新設し、「おねしょズボン」「おねしょ
   パンツ」で「防水」を候補から除外した。
2. **国産豚のもつ煮（kan-etsubussan:10000031）**: 商品名から確認できる
   のは「レトルト」だけで、「温めるだけ」という具体的な調理方法までは
   確認できないため、テンプレートの文言を「食事やおつまみに取り入れ
   やすいもつ煮」という安全な表現に変更した。
3. **業務用ハンガーラック（bidoseikatsu:10000017）**: 幅90cm・高さ
   180cm・耐荷重100kgのうち幅しか紹介文に反映されていなかった。寸法
   ラベルが2つ以上ある場合はまとめて示し、耐荷重は別の確認できる仕様
   として示す`_extract_dimension_and_capacity_facts()`を新設した。

## 2. 変更したdescription

| item_code | 変更前の問題 | 変更後 |
|---|---|---|
| plusiine:10000361 | 「✔️ 水回りでも使いやすい」（不自然な用途） | 「✔️ 子どものおねしょ対策に取り入れやすい」 |
| kan-etsubussan:10000031 | 「温めるだけで食べられるもつ煮」（未確認の調理方法） | 「食事やおつまみに取り入れやすいもつ煮」（「3袋・10袋・20袋から選べる」は維持） |
| bidoseikatsu:10000017 | 「✔️ 幅は約90cm」のみ（高さ・耐荷重が欠落） | 「✔️ 幅90cm・高さ180cm」「✔️ 耐荷重100kg」（「約」を追加せず原文どおり） |

## 3. 追加テスト数

`tests/test_description_generator.py`に`Sept29FinalReviewFixTest`
（**10件**）を追加した。既存のハンガーラック寸法テスト1件も新しい
期待値に更新した。

## 4. 全テスト結果

`python3 -m pytest -q`と`python3 -m unittest discover -s tests`の両方で
**470件全て成功**（本タスク開始前は460件）。

## 5. 他7件が不変であること

`room/data/candidates.json`（2026-09-29 15:50生成分）のうち、指摘の
あった3商品以外の7商品（wagaku0204・makuake-store・mugendo・
charmying・dailymukuri・at-life・shopmarna）の`description`は、
Pythonスクリプトで前回生成分と1バイトも変わっていないことを確認した
（回帰なし）。`git diff --stat room/data/candidates.json`でも変更が
`description`フィールド3件分のみであることを確認済み。

## 6. 10商品・順番・generated_at_jstが不変であること

Pythonスクリプトで新旧JSONを比較し、10商品全てで`item_code`・
`name`・`price`・`review_average`・`review_count`・`category`が完全
一致することを確認した。`generated_at_jst`（2026/09/29 15:50）・
items配列の順序・件数（10件）も無変更。

## 7. 商品選定ロジックを変更していないこと

`git status`で変更ファイルが`src/description_generator.py`・
`tests/test_description_generator.py`・`room/data/candidates.json`・
`docs/DESIGN.md`・`docs/AI_STATUS.md`のみであることを確認済み。
`src/ranking.py`・`src/main.py`・`select_top_candidates()`・
`daily_target`・`max_per_category`・レビュー評価条件・レビュー件数
条件・重複防止・直近投稿の偏り調整・`data/posted_items.json`・
GitHub Actions実行時刻・楽天API認証情報・投稿済み登録ワークフローには
一切変更していない。

## 変更ファイル

- `src/description_generator.py`：`_FEATURE_CLAUSE_SUPPRESSED_FOR_
  PRODUCT_TYPE`を新設し`_top_feature_clause()`に組み込み。「もつ煮」
  「モツ煮」テンプレートのhook_text/worry_lines/solution_text/
  checklist_coreを変更。`_DIMENSION_LABEL_VALUE_PATTERN`・
  `_LOAD_CAPACITY_VALUE_PATTERN`・`_extract_dimension_and_capacity_
  facts()`を新設し`_build_checklist()`に組み込み。
- `tests/test_description_generator.py`：`Sept29FinalReviewFixTest`
  （10件）を追加。既存のハンガーラック寸法テスト1件の期待値を更新。
- `room/data/candidates.json`：2026-09-29 15:50生成分のうち3商品
  （plusiine・kan-etsubussan・bidoseikatsu）の`description`フィールド
  のみ再生成。他7商品は無変更。
- `docs/DESIGN.md`（44章に記録）・`docs/AI_STATUS.md`（このファイル）。

`src/ranking.py`・`src/main.py`・`src/dedupe.py`・`src/filters.py`・
`config/settings.example.yaml`・`data/posted_items.json`・
`room/index.html`・`.github/workflows/`・楽天API認証情報には一切変更
していない。

## 残る制約

- `_FEATURE_CLAUSE_SUPPRESSED_FOR_PRODUCT_TYPE`は商品タイプ単位で
  個別に登録する方式のため、他の商品タイプで同様の問題が見つかった
  場合は同じ辞書へ追加する形で対応できる。
- `_extract_dimension_and_capacity_facts()`は寸法ラベルが2つ以上ある
  場合のみ動作する。ラベルが1つしかない商品名では従来の言い回しの
  まま。
- 商品選定・カテゴリー割り当て自体は引き続き今回のスコープ外。

## 8. コミットID

このファイルの更新を含むコミットのハッシュは、コミット後にgit logで
確認できる（下記に反映）。

## セキュリティ

秘密情報（Rakuten Application ID、Access Key、各種トークン等）は
コード・ログ・README・本ファイルに一切含めていない。楽天ROOMへの
機械的な自動投稿・自動ログイン・購入操作は実装していない（本タスクの
変更は紹介文の文章内容のみ）。
