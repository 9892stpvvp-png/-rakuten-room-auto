# AI STATUS

Task ID: user-request-description-genre-009-pet-animal-guess-fix（ユーザーからの直接依頼）
Status: DONE

## 最終更新

Claude Codeが、2026-09-28 15:51生成分の`room/data/candidates.json`で残っていた文章表現・安全フォールバックを最終調整した。**商品選定・ランキング・商品タイプ判定の大きな構造・数値判定の安定部分には触れていない**。

## 1. ペット用品フォールバックの修正内容

`GENERIC_TEMPLATES["ペット用品"]`（description-genre-008で新設）が「愛犬・愛猫」を固定で含んでおり、category="ペット用品"という情報だけを根拠に、商品名からは確認できない両方の対象動物を毎回自動生成していた（高齢犬用商品にも「愛猫」が混入）。これを、対象動物を限定しないneutral版（「ペットとの暮らしに取り入れやすいペット用品」）に変更し、犬用専用の`_PET_GENERIC_TEMPLATE_DOG`・猫用専用の`_PET_GENERIC_TEMPLATE_CAT`を新設した。`_resolve_pet_generic_template(name)`が商品名を判定して適切なテンプレートを選ぶ。

## 2. 対象動物の推測防止方法

商品名の末尾が「犬用」であれば犬向けと判定する（「愛犬用」「高齢犬用」「子犬用」等も末尾が「犬用」のため自然にカバーできる）。「猫用」も同様に猫向けと判定する。両方確認できる場合、またはどちらも確認できない場合は、対象動物を限定しないneutral版のままにする（安全側のフォールバック）。商品タイプ自体（ドッグフード・おもちゃ等）は引き続き断定しない。`_select_template()`にcategory=="ペット用品"の分岐を追加し、`_resolve_pet_generic_template(name)`を経由するようにした。

## 3. ハッシュタグ修正

`_CATEGORY_SUPPRESS_GENERIC_HASHTAGS`（現在は「ペット用品」のみ）を新設し`_build_hashtags()`に組み込んだ。このカテゴリーでは、商品タイプが判定できなくても、base_hashtags・#便利グッズは付けず、カテゴリー別タグ（#ペット用品）だけを使う。他のGENERIC_TEMPLATESカテゴリー（お茶・水・家電等）は、ジャンル自体は分かっていても具体的な商品タイプまでは確認しにくいことが多いため、今回は対象を「ペット用品」のみに絞った（安全側の判断）。

## 4. ヒップシートの安全表現修正

hook_text・worry_lines・solution_text・checklist_core・closing_variantsから「負担を軽くしやすい」という効果表現を削除し、「抱っこのときに使いやすい」という用途ベースの表現に変更した。収納ポケット・折りたたみ等、商品名から確認できる構造的な仕様はそのまま反映される。

## 5. 「○人前」の数量表現修正

`_SERVINGS_UNIT_SUFFIX_PATTERN`（末尾が「人前」）を新設し、複合表記の一部ではない単独の「◯人前」表記は、「で使いやすい」を付けず、商品名の表記そのまま（例：「6人前」）を返すようにした。複合表記の一部としての「人前」（例：「170g×4袋・計8人前」）は、description-genre-005/008で対応済みの処理のまま変更していない。

## 6. 追加テスト数

`tests/test_description_generator.py`に`DescriptionGenre009RegressionTest`（**11件**）を追加した。

1. 高齢犬用商品に「愛猫」を追加しない
2. 対象動物不明のペット用品に犬/猫を勝手に追加しない
3. タイトルに犬用と明記された場合のみ犬表現を許可
4. タイトルに猫用と明記された場合のみ猫表現を許可
5. ペット用品フォールバックに#暮らしの便利グッズを付けない
6. ペット用品フォールバックに#便利グッズを付けない
7. ヒップシートで負担軽減効果を断定しない
8. ヒップシート20kgを商品重量にしない（回帰確認）
9. 「6人前」に「で使いやすい」を追加しない
10. 「4人前」に「で使いやすい」を追加しない
11. 過去の複合数量表現（170g×4袋・計8人前、54枚入り×15個・計810枚、80枚入り×40個）を壊さない

既存の`test_hashtag_block_has_three_to_five_tags_and_no_emoji`（GENERIC_TEMPLATES全カテゴリーでハッシュタグ3〜5個を確認するテスト）は、「ペット用品」だけ最小1個を許容するよう更新した（商品タイプ未確定時は#ペット用品のみで安全に紹介する、という今回の意図的な仕様のため）。

## 7. 全テスト結果

`python3 -m pytest -q` と `python3 -m unittest discover -s tests` の両方で**441件全て成功**（本タスク開始前は430件）。既存テストは1件の期待値更新のみで、新規11件を追加して達成した。

## 8. 今日の10件の最終確認結果

`room/data/candidates.json`（2026-09-28 15:51生成分）の全10商品の`description`フィールドを最新ロジックで再生成し、人手で全件レビューした。今回修正した5件（calmisence・yakunosoba・naganosoba・peaceone・kurosu）の`description`だけが変更され、それ以外の5件（lecdirect・larutan・furumiyashop・freedom-shops・angelingg）は前回生成分から1バイトも変わっていないことをPythonスクリプトで確認した（回帰なし）。

| item_code | 商品 | 確認結果 |
|---|---|---|
| calmisence:10000000 | ヒップシート | 「抱っこのときに使いやすい」に変更、負担軽減効果の断定なし、20kgの重量誤認なし |
| yakunosoba:10000147 | 夜久野そば | 「6人前」（「で使いやすい」の機械的付与なし） |
| naganosoba:10000033 | 信州戸隠そば | 「4人前」（「で使いやすい」の機械的付与なし） |
| peaceone:10001236 | サイエンス シニア小粒（高齢犬用） | 「愛犬」表現（タイトルの「高齢犬用」から確認）、#ペット用品のみ |
| kurosu:10003426 | サンジョルディ たまごちゃん | 対象動物を限定しない表現（タイトルから犬猫いずれも未確認）、#ペット用品のみ |
| その他5商品 | おしりふき・ミルクウォーマー・車用サンシェード・折りたたみ傘・ほこり取りスポンジ | 前回生成分から1バイトも変わらず（回帰なし） |

不自然な数値表現・対象動物の推測・未確認の健康/身体効果は10件とも残っていないことを確認した。全件500文字以内（149〜198文字）。

## 9. 商品・item_code・順番が変わっていないこと

`git diff --stat room/data/candidates.json`で変更が`description`フィールド5件分（calmisence・yakunosoba・naganosoba・peaceone・kurosu）のみであることを確認済み。加えてPythonスクリプトで新旧JSONを比較し、10商品全てで`item_code`・`name`・`price`・`review_average`・`review_count`・`category`が完全一致することを確認した。`generated_at_jst`（2026/09/28 15:51）・items配列の順序・件数（10件）も無変更。

## 10. 商品選定ロジックを変更していないこと

`git status`で変更ファイルが`src/description_generator.py`・`tests/test_description_generator.py`・`room/data/candidates.json`・`docs/DESIGN.md`・`docs/AI_STATUS.md`のみであることを確認済み。`src/ranking.py`・`src/main.py`・`select_top_candidates()`・`daily_target`・`max_per_category`・レビュー条件・重複防止・投稿済み履歴・GitHub Actions・楽天API、および前回までに確立した商品タイプ判定の3段階構造・出現位置優先判定・具体性による優先度・複合数量の言い回しには一切触れていない。

## 変更ファイル

- `src/description_generator.py`：`GENERIC_TEMPLATES["ペット用品"]`をneutral版に変更し、`_PET_GENERIC_TEMPLATE_DOG`・`_PET_GENERIC_TEMPLATE_CAT`・`_resolve_pet_generic_template()`を新設、`_select_template()`に組み込み。`_CATEGORY_SUPPRESS_GENERIC_HASHTAGS`を新設し`_build_hashtags()`に組み込み。ヒップシートのhook_text/worry_lines/solution_text/checklist_core/closing_variantsから効果表現を削除。`_SERVINGS_UNIT_SUFFIX_PATTERN`を新設し`_phrase_for_quantity()`に組み込み。
- `tests/test_description_generator.py`：`DescriptionGenre009RegressionTest`（11件）を追加。既存のハッシュタグ数テスト1件の期待値を更新。
- `room/data/candidates.json`：2026-09-28 15:51生成分のうち5商品（calmisence・yakunosoba・naganosoba・peaceone・kurosu）の`description`フィールドのみ再生成。他5商品は無変更。
- `docs/DESIGN.md`（42章に記録）・`docs/AI_STATUS.md`（このファイル）。

`src/ranking.py`・`src/main.py`・`src/dedupe.py`・`src/filters.py`・`config/settings.example.yaml`・`data/posted_items.json`・`room/index.html`・`.github/workflows/`・楽天API認証情報には一切変更していない。

## 残る制約

- `_resolve_pet_generic_template()`の対象動物判定は「犬用」「猫用」の末尾一致のみで行っている。「わんちゃん用」「にゃんこ用」のような別表記には対応していない。
- `_CATEGORY_SUPPRESS_GENERIC_HASHTAGS`は現在「ペット用品」のみ登録している。他のGENERIC_TEMPLATESカテゴリーで同様の問題が見つかった場合は、同じ集合に追加する形で対応できる。
- 商品選定・カテゴリー割り当て自体（検索元カテゴリーと実際の商品ジャンルの乖離）は引き続き今回のスコープ外。

## 11. コミットID

このファイルの更新を含むコミットのハッシュは、コミット後にgit logで確認できる（下記に反映）。

## セキュリティ

秘密情報（Rakuten Application ID、Access Key、各種トークン等）はコード・ログ・README・本ファイルに一切含めていない。楽天ROOMへの機械的な自動投稿・自動ログイン・購入操作は実装していない（本タスクの変更は紹介文の文章内容とハッシュタグのみ）。
