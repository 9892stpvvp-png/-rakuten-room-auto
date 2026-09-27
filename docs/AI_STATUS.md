# AI STATUS

Task ID: user-request-description-genre-007-quantity-vs-variety（ユーザーからの直接依頼）
Status: DONE

## 最終更新

Claude Codeが、2026-09-27 15:47生成分の`room/data/candidates.json`で残っていた2点（ドッグフードの数量・種類表現、韃靼そば茶のハッシュタグ）を最終調整した。**商品選定・商品タイプ判定の3段階構造・出現位置優先判定・description-genre-006で確立した既存の安定したロジックには触れていない**。

## 1. ドッグフードの修正内容

商品名「選べる小袋 3袋セット」から、3袋が異なる種類で構成されると自動的に断定しないよう修正した。修正前は「3袋セットでいろいろな種類を試しやすい」となっていたが、修正後は「3袋セット」（数量のみ、種類数の断定なし）になる。

## 2. 数量と種類数をどう分離したか

`_VARIETY_COUNT_INDICATOR_WORDS`から「選べる」「種類」「種から」を削除し、単語自体が「複数の選択肢からの詰め合わせ」を意味する「よりどり」「アソート」だけを残した。代わりに、「◯種類から選べる」「◯種から選べる」のように、選択肢の数（◯種／◯種類）が数字で明示され、かつそれが「選べる」に直接つながっている場合だけアソートと判定する`_VARIETY_EXPLICIT_SPECIES_PATTERN`を新設した。

- 「よりどり」「アソート」：単語自体の意味だけで安全に判定できるため、他に数字の根拠が無くても引き続きアソート表現にする。
- 「◯種類から選べる」「◯種から選べる」：数量（例：6本）と選択肢の数（例：40種）の両方が数字で明示され、「選べる」に直接つながっている場合だけアソートと判定する（例：「40種から選べる6本」→○）。
- 単なる「選べる」「種類」：数量と直接結びつく数字の根拠が無い場合は、アソートと判定しない（例：「選べる小袋 3袋セット」→×）。

この結果、ドッグフードは「3袋セット」になり、アロマオイル「40種から選べる6本」は従来通り「6本セットでいろいろな種類を試しやすい」を維持した。「1種類を選べる」（マミーポコパンツ等）は`_SINGLE_CHOICE_PATTERN`により引き続き除外される。副次的に、既存のハンガー商品「10本単位で選べる16色」（色の選択肢と本数は無関係）で発生していた同種の誤りも合わせて修正された。

## 3. 韃靼そば茶のハッシュタグ修正

`_PRODUCT_TYPE_HASHTAG_OVERRIDES`に「韃靼そば茶」「ダッタンそば茶」「だったんそば茶」「そば茶」を追加し、`_find_hashtag_override_by_name()`を新設した。`_build_hashtags()`は、まず`match_product_type_keyword()`（PRODUCT_TYPE_TEMPLATES一致）の結果でタグを探し、一致しない場合に`_find_hashtag_override_by_name()`（商品名と_PRODUCT_TYPE_HASHTAG_OVERRIDESの見出し語を直接照合）でタグを探すようにした。これにより、紹介文の本文はGENERIC_TEMPLATES["お茶"]の安全な汎用文のまま（商品タイプ判定の構造は変更していない）、ハッシュタグだけ「#お茶 #韃靼そば茶」という商品本体に合ったタグになった（#暮らしの便利グッズ・#便利グッズは付かなくなった）。この仕組みは、他のGENERIC_TEMPLATESフォールバック商品（水・洗剤等）でも、_PRODUCT_TYPE_HASHTAG_OVERRIDESに商品名を追加するだけで同様に適用できる。

## 4. 追加テスト数

`tests/test_description_generator.py`に`DescriptionGenre007RegressionTest`（**6件**）を追加した。

1. 「選べる小袋3袋セット」から3種類セットと断定しない
2. 数量と種類数を別に扱う（明確な根拠がある場合はアソート表現を維持）
3. 明確な根拠がない場合「いろいろな種類を試しやすい」を生成しない（マミーポコパンツ・よりどり系は既存の挙動を維持）
4. 韃靼そば茶に#暮らしの便利グッズを付けない
5. 韃靼そば茶に#便利グッズを付けない
6. 韃靼そば茶の商品本体に合ったタグを生成する

## 5. 全テスト結果

`python3 -m pytest -q` と `python3 -m unittest discover -s tests` の両方で**415件全て成功**（本タスク開始前は409件）。既存409件は1件も修正せず、新規6件追加のみで達成した。

## 6. 10件の最終確認結果

`room/data/candidates.json`（2026-09-27 15:47生成分）の全10商品の`description`フィールドを最新ロジックで再生成し、人手で全件レビューした。今回修正した2件（dogfood-koubou・honjien-3）の`description`だけが変更され、それ以外の8件（アロマオイル・アロマスプレー・美顔ローラー×2・ヤギミルク・スワドル・おむつペール・おむつストッカー）は前回生成分から1バイトも変わっていないことをPythonスクリプトで確認した（回帰なし）。全件500文字以内（153〜197文字）。

| item_code | 商品 | 確認結果 |
|---|---|---|
| dogfood-koubou:10000037 | ドッグフード | 「3袋セット」（種類数の断定なし）。#ペット用品 #ドッグフード |
| honjien-3:10000446 | 韃靼そば茶 | #お茶 #韃靼そば茶（#暮らしの便利グッズ・#便利グッズなし）。本文はGENERIC_TEMPLATES["お茶"]のまま |
| その他8商品 | アロマオイル・アロマスプレー・美顔ローラー×2・ヤギミルク・スワドル・おむつペール・おむつストッカー | 前回生成分から1バイトも変わらず（回帰なし） |

## 7. 商品・item_code・順番が変わっていないこと

`git diff --stat room/data/candidates.json`で変更が`description`フィールド2件分（dogfood-koubou・honjien-3）のみであることを確認済み。加えてPythonスクリプトで新旧JSONを比較し、10商品全てで`item_code`・`name`・`price`・`review_average`・`review_count`・`category`が完全一致することを確認した。`generated_at_jst`（2026/09/27 15:47）・items配列の順序・件数（10件）も無変更。

## 8. 商品選定ロジックを変更していないこと

`git status`で変更ファイルが`src/description_generator.py`・`tests/test_description_generator.py`・`room/data/candidates.json`・`docs/DESIGN.md`・`docs/AI_STATUS.md`のみであることを確認済み。`src/ranking.py`・`src/main.py`・`select_top_candidates()`・`daily_target`・`max_per_category`・レビュー条件・重複防止・投稿済み履歴・GitHub Actions・楽天API、および前回までに確立した商品タイプ判定の3段階構造・出現位置優先判定・具体性による優先度（`_GENERIC_FALLBACK_PRODUCT_TYPE_KEYWORDS`）には一切触れていない。

## 変更ファイル

- `src/description_generator.py`：`_VARIETY_COUNT_INDICATOR_WORDS`から「選べる」「種類」「種から」を削除し、`_VARIETY_EXPLICIT_SPECIES_PATTERN`を新設して数量と種類数を分離。`_PRODUCT_TYPE_HASHTAG_OVERRIDES`に「韃靼そば茶」等4キーワード追加。`_find_hashtag_override_by_name()`を新設し`_build_hashtags()`に組み込み。
- `tests/test_description_generator.py`：`DescriptionGenre007RegressionTest`（6件）を追加。
- `room/data/candidates.json`：2026-09-27 15:47生成分のうち2商品（dogfood-koubou・honjien-3）の`description`フィールドのみ再生成。他8商品は無変更。
- `docs/DESIGN.md`（40章に記録）・`docs/AI_STATUS.md`（このファイル）。

`src/ranking.py`・`src/main.py`・`src/dedupe.py`・`src/filters.py`・`config/settings.example.yaml`・`data/posted_items.json`・`room/index.html`・`.github/workflows/`・楽天API認証情報には一切変更していない。

## 残る制約

- `_find_hashtag_override_by_name()`によるハッシュタグの商品タイプ優先は、`_PRODUCT_TYPE_HASHTAG_OVERRIDES`に商品名（韃靼そば茶等）を個別に登録した場合のみ働く。他の消耗品で同様の問題が見つかった場合は、同じ表に追加する形で対応できる。
- `_VARIETY_EXPLICIT_SPECIES_PATTERN`は「◯種類から選べる」「◯種から選べる」の直接的な組み合わせのみを対象にしている。数字と「選べる」の間に長い文章が挟まる表記は対象外。
- 商品選定・カテゴリー割り当て自体（検索元カテゴリーと実際の商品ジャンルの乖離）は引き続き今回のスコープ外。

## 9. コミットID

このファイルの更新を含むコミットのハッシュは、コミット後にgit logで確認できる（下記に反映）。

## セキュリティ

秘密情報（Rakuten Application ID、Access Key、各種トークン等）はコード・ログ・README・本ファイルに一切含めていない。楽天ROOMへの機械的な自動投稿・自動ログイン・購入操作は実装していない（本タスクの変更は紹介文の文章内容とハッシュタグのみ）。
