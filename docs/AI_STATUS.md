# AI STATUS

Task ID: user-request-product-type-diversity-anti-repetition（ユーザーからの直接依頼）
Status: DONE

## 最終更新

Claude Codeが、「同じ商品タイプ（スポンジ・段ボールストッカー等）が連日候補に出る」問題について、原因調査→実装方針決定→最小限の修正→回帰テスト追加→全テスト実行→実データを使ったシミュレーション→修正前後の比較、の順に対応した。完全重複除外（既存機能）は変更せず、「同じ商品タイプの連投」を**除外ではなく優先度調整**で抑える仕組みを追加した。

## 同じ商品タイプが連日出た根本原因

1. `config/settings.yaml`のkeywordsは固定の検索ワード一覧で、日ごとに検索ワード自体をローテーションする仕組みが無い。
2. 楽天ウェブサービスAPI（`rakuten_api.search_items`）は常にレビュー件数降順で返すため、同じキーワードで検索する限り、同じ商品タイプのトップ商品（例：レビュー件数が突出したスポンジ）が毎回上位に来る。
3. 投稿済み履歴による重複除外（`dedupe.py`）は「完全に同じ商品」（item_code／URL／正規化商品名／match_keywords）だけを見ており、「商品タイプ」という粒度の判定はそもそも持っていない（＝別メーカーのスポンジ、別店舗の段ボールストッカーは正しく「別商品」として通過する）。
4. `ranking.py`の並び替え（`sort_by_quality`/`sort_consumable_items`）はレビュー実績のみによる完全に決定的な順序で、ランダム性も商品タイプの偏りを考慮する仕組みも無かった。

「個々の商品は重複していないが、同じ商品タイプばかりが上位に来る」状態が、これらの組み合わせで起きていた。実際に本番の`data/posted_items.json`（105件）でシミュレーションしたところ、直近7日で「スポンジ」5回・「段ボールストッカー」3回・「ハンガー」3回・「圧縮袋」6回などが検出され、ユーザーの挙げた具体例がそのまま実データで再現された。

## 採用した偏り防止方式

完全除外とは明確に別の、2段階の仕組みにした。

- **完全重複** → 従来通り`dedupe.py`が除外（一切変更なし）。
- **同商品タイプの連投** → **除外せず、並び順の優先度だけを下げる**（`ranking.priority_tier`）。

`ranking.diversify_top()`が既に持っている「1巡目はカテゴリー上限を守って選ぶ→2巡目は上限を無視して残りから埋める」という2巡構造を利用し、`diversify_top()`自体は変更せず、その手前の並べ替えに「優先度の段階（tier）」を主要な並び替えキーとして追加しただけにした。こうすることで、「優先度の高い候補が十分にあれば後回しにされ、足りなければ自動的に繰り上がる」という、ユーザーが求めた「完全除外ではなく段階的なグレースフルデグラデーション」がコードの追加なしに実現できている。

- `ranking.type_tier(count)`: 直近の投稿回数を0〜3の段階に変換（0回→0、1回→1、2回→2、3回以上→3で頭打ち。固定の数値にこだわらず、既存コードに合う単純な打ち切りにした）。
- `ranking.priority_tier(item, recent_type_counts, recent_category_counts)`: 商品タイプ・カテゴリーそれぞれの段階を合算（両方の粒度の偏りを同じ仕組みで抑える）。
- `sort_by_quality`/`sort_consumable_items`/`select_balanced_top`に`recent_type_counts`・`recent_category_counts`・`rng`を追加のキーワード引数として追加（**すべて省略可能。省略時は従来と完全に同じ動作**）。並び替えキーの先頭に`priority_tier`を置き、レビュー実績はその次点にした。

## 商品タイプの判定方法

新しい手書き辞書は作らず、既存の紹介文生成用インフラを再利用した。`description_generator.classify_product_type(name, category)`を追加し、まず既存の`match_product_type_keyword(name)`（`PRODUCT_TYPE_TEMPLATES`の見出し語、スポンジ・段ボールストッカー・ハンガー・水垢・炊飯器等25種類）で具体的な商品の種類を判定し、一致しなければ検索キーワードに付けたカテゴリー（例：「水」「お茶」「洗剤」「収納」）をそのまま商品タイプとして扱う。紹介文生成と候補選定が同じ判定関数を根拠にするため、両者の商品タイプ判定がバラバラにならない。

## 直近履歴の扱い（7日・日時の捏造禁止）

`ranking.compute_recent_type_counts(posted_items, type_of, lookback_days=7)`は、投稿済み履歴から**`posted_at`が実際に保存されている（かつ7日以内の）レコードだけ**を対象に集計する。`posted_at`が無いレコード（現在の`data/posted_items.json`は105件中39件が旧形式でposted_atが無い）は、日時を推測せず**集計対象からスキップする**（安全側の判断）。`main.py`はこの履歴ファイルへの書き込みを一切行わない（書き込みは従来通り`dedupe.append_posted_items`だけが行う）ため、既存データを壊す・書き換えるリスクは無い。

`main.py`の`_posted_entry_product_type(entry)`は、投稿済みレコードの`product_name`・`category`から商品タイプを判定するが、`category`が保存されていないレコードは`DEFAULT_CATEGORY`へフォールバックさせず空文字（＝集計対象外）にし、情報が無いものを実在のカテゴリーと誤認しないようにしている。

## 旧posted_itemsとの互換性

- `data/posted_items.json`の既存105件（`posted_at`ありが66件、無しが39件）は**一切削除・書き換えしていない**（今回の変更でこのファイルに書き込む処理は追加していない）。
- `dedupe.py`のスキーマ・`_normalize_incoming_item()`は以前から`category`フィールドに対応していたが、投稿ページ（`room/index.html`）側がこれまで`category`を記録・書き出ししていなかったため、`state.posted[itemCode]`への保存箇所と`buildPostedExportRecords()`に`category: (item && item.category) || ""`を追記した。既存のlocalStorage・既存のエクスポート形式には無かったフィールドを追加しただけで、既存の動作（投稿済み表示・フィルタ・エクスポート）は変えていない。今後「投稿済みにする」操作をした分から`category`が保存されるようになる。

## 10件不足時の動作

`priority_tier`は並び順を後ろにずらすだけで、候補そのものを消さない。`select_balanced_top`に渡す候補一覧は従来通りフィルタ済みの全件であるため、優先度の高い候補が足りなければ`diversify_top`の2巡目・枠間の補充ロジック（無変更）がそのまま働き、同商品タイプでも自動的に繰り上がる。**品質条件（レビュー評価・件数等）を緩める処理は一切追加していない**。10件に届かない場合、従来通りそのまま少ない件数で終了する（品質条件を緩めて埋めることはしない）。

## ランダム性の仕組み

`main.py`は当日（JST日付文字列）を種にした`random.Random`（`_daily_random_seed`）を1つ作り、`select_balanced_top`に渡す。`sort_by_quality`/`sort_consumable_items`は、渡されたrngで候補一覧をシャッフルしてから安定ソートするため、**優先度・レビュー実績が完全に同点の商品同士の並びだけ**がランダムになり、優先度・品質順そのものは変わらない（「完全ランダムではなく偏りを抑えたランダム」という指示に沿った設計）。同じ日のうちの再実行では同じ順になり、日付が変われば自然に変わる。rngは呼び出し側から注入できる設計のため、テストではseedを固定して再現性を確保している。

## 診断情報

`storage.build_product_type_diversity_markdown()`を追加し、GitHub ActionsのSummaryに「今回選ばれた商品タイプ」「最近多いため優先度を下げた商品タイプ」「不足のため復帰させた商品タイプ」を簡潔に表示する。

## 変更したファイル

- `src/description_generator.py`: `classify_product_type()`を追加。
- `src/ranking.py`: `type_tier`/`priority_tier`/`compute_recent_type_counts`を追加。`sort_by_quality`/`sort_consumable_items`/`select_balanced_top`に`recent_type_counts`/`recent_category_counts`/`rng`（すべて省略可能）を追加。
- `src/main.py`: 直近7日の商品タイプ・カテゴリー件数の集計（`_posted_entry_product_type`）、日次シード乱数の生成（`_daily_random_seed`）、`item["_product_type"]`の設定、`select_balanced_top`への引き渡し、偏り防止の診断情報出力を追加。
- `src/storage.py`: `build_product_type_diversity_markdown()`を追加。
- `room/index.html`: 投稿済み登録時に`category`を保存・エクスポートするよう追記（後方互換の追加フィールド）。
- `tests/test_ranking.py`・`tests/test_description_generator.py`・`tests/test_main.py`: 追加テスト（下記）。
- `docs/DESIGN.md`（31章に記録）・`docs/AI_STATUS.md`（このファイル）。

`data/posted_items.json`の既存データ・紹介文生成の既存動作・GitHub Pages投稿画面の基本操作・15:30 JSTの実行スケジュール・TikTok関連・楽天API認証・秘密情報には一切変更していない。

## 追加テスト

1. **完全重複除外は今まで通り**: 既存の`tests/test_dedupe.py`・`test_main.py`の重複除外テストが無変更のまま成功することを確認（`dedupe.py`自体は未変更）。
2. **昨日スポンジ→今日はスポンジと非スポンジ両方ある場合、非スポンジが優先**: `test_ranking.py`の`test_sponge_deprioritized_below_other_type_but_not_excluded`、および`test_main.py`の`ProductTypeDiversityPipelineTest`（実際のパイプライン全体を通した統合テスト。詳細は下記「修正前後の比較」参照）。
3. **スポンジしか適合商品が無ければ品質条件を緩めず復帰**: `test_sponge_only_candidate_still_selected_without_loosening_quality`。
4. **段ボールストッカーでも同じ仕組みが働く**: `test_cardboard_stocker_uses_the_same_generic_mechanism`（商品タイプ名をハードコードした専用ロジックではなく、`priority_tier`という同じ汎用の仕組みで動くことを確認）。
5. **直近に出ていない商品タイプは不必要にペナルティを受けない**: `PriorityTierTest.test_recently_unseen_type_is_not_penalized`。
6. **既存の便利グッズ5＋消耗品/飲料5バランス処理を壊さない**: `test_existing_five_and_five_balance_is_unaffected_by_new_optional_arguments`、および既存の`SelectBalancedTopTest`全件が無変更のまま成功。
7. **候補不足時に品質条件を緩めない**: `test_shortage_never_fabricates_items_only_reorders_existing_candidates`（ranking側は渡された候補を並べ替えるだけで新しい商品を作らないことを確認）。
8. **posted_items.jsonの旧形式でも動作する**: `ComputeRecentTypeCountsTest.test_works_with_old_format_entries_missing_fields`。
9. **投稿日時が無い旧データに架空の日付を追加しない**: `ComputeRecentTypeCountsTest.test_entries_without_posted_at_are_skipped_not_fabricated`、`PostedEntryProductTypeTest.test_missing_category_is_not_fabricated`。
10. **ランダム性はseedで再現できる**: `RandomnessIsSeedableTest`（同じseedなら同じ順、rng無しなら決定的、優先度段階が違えばrngがあっても順序は変わらないことを確認）。

これに加え、`description_generator.classify_product_type()`の単体テスト（`ClassifyProductTypeTest`）、`main.py`の`_daily_random_seed`・`_posted_entry_product_type`の単体テストも追加した。

## 全テスト結果

`python3 -m pytest -q` と `python3 -m unittest discover -s tests` の両方で **300件全て成功**（本タスク開始前は269件）。既存テストは1件も修正しておらず、新規追加31件のみで達成した（新しい引数がすべて省略可能な設計のため、既存の呼び出し側・既存テストへの影響が無かった）。

## シミュレーション結果（実データ）

実際の`data/posted_items.json`（105件、うちposted_atあり66件）に対して`compute_recent_type_counts`を実行したところ、直近7日以内の実績として以下が検出された（抜粋、tier=優先度を下げる段階）。

```
商品タイプ:  圧縮袋 6回(tier3) / スポンジ 5回(tier3) / ロボット掃除機 3回(tier3)
            ハンガー 3回(tier3) / 段ボールストッカー 3回(tier3) / ドアストッパー 2回(tier2) ...
カテゴリー:  収納 3回(tier3) / 時短 1回(tier1) / キッチン 1回(tier1) ...
```

ユーザーが挙げた「スポンジ」「段ボールストッカー」が、実データでもそのまま最大段階（tier=3）まで優先度が下がる対象として検出された。

## 修正前後の比較（架空の新商品4件、実データの直近実績を使用）

| 商品 | レビュー件数 | 修正前の順位 | 修正後の順位（tier） |
|---|---|---|---|
| 新発売スポンジ（新メーカー） | 9000 | 1位 | 2位（tier=4） |
| 隙間収納ラック（直近未投稿タイプ） | 300 | 4位 | 1位（tier=3） |
| 折りたたみ段ボールストッカー（新店舗） | 500 | 2位 | 3位（tier=6） |
| すべらないハンガー | 450 | 3位 | 4位（tier=6） |

レビュー件数最多（9000件）のスポンジが、修正前は無条件で1位だったが、修正後は直近の実績により2位に下がる。一方で、レビュー件数が最も少ない（300件）が直近投稿していない収納ラックが1位に繰り上がる。**いずれの商品も除外はされておらず、4件とも変わらず候補プールに残っている**（並び順が変わるだけ）。

### 具体例1: スポンジを投稿した翌日に別メーカーのスポンジが出た場合

item_code・URL・商品名が異なるため、既存の重複除外（`dedupe.py`）には引っかからず、これまで通り候補として通過する。新しい仕組みでは、直近の「スポンジ」投稿実績により`priority_tier`が高くなるため、**同じ枠・同じカテゴリー内に非スポンジの適合商品があれば、そちらが先に選ばれる**。ただし非スポンジの適合商品が無ければ、品質条件を緩めることなく、このスポンジ自身がそのまま繰り上がって選ばれる。`test_main.py`の`ProductTypeDiversityPipelineTest`で、実際にこのシナリオ（別メーカーの新スポンジが除外されずに残ること、同枠内で商品タイプ未使用のラップの方が先に並ぶこと）を確認済み。

### 具体例2: 段ボールストッカーを投稿した翌日に別店舗の段ボールストッカーが出た場合

同様に、item_code・URL・商品名が異なるため完全重複除外の対象にはならない。商品タイプ判定は店舗名ではなく商品名の「段ボールストッカー」というキーワード一致で行うため、店舗が違っても正しく同じ商品タイプと判定され、直近実績に応じて優先度が下がる（が除外はされない）。`test_ranking.py`の`test_cardboard_stocker_uses_the_same_generic_mechanism`で、スポンジと全く同じ汎用の仕組み（`priority_tier`）が段ボールストッカーにもそのまま機能することを確認済み（商品タイプ名をハードコードした専用のif分岐は一切追加していない）。

## 既存機能への影響

紹介文生成・GitHub Pages投稿画面・投稿済み登録ワークフロー・15:30 JSTの実行スケジュール・TikTok関連・楽天API認証・秘密情報には変更していない（`room/index.html`のcategory追記はエクスポート形式への追加フィールドのみで、既存の読み書き・表示ロジックは変えていない）。新しい引数はすべて省略可能で、省略時（デフォルト）の並び順・選定結果は変更前と完全に一致することをテストで確認している。

## 残っている制約

- 商品タイプの粒度は`PRODUCT_TYPE_TEMPLATES`に登録済みのキーワードに依存する。例えば「緑茶」「麦茶」「そば茶」のように、カテゴリー「お茶」の中でさらに細かく分けたい場合、該当のキーワードが`PRODUCT_TYPE_TEMPLATES`に無ければカテゴリー単位（「お茶」）でしか区別されない（新しい手書き辞書を増やしすぎないという方針を優先した）。
- `category`のposted_items.jsonへの保存は、今回の`room/index.html`修正より後に「投稿済みにする」操作をした分からのみ有効になる。過去の投稿はcategoryが無いままのため、当面はカテゴリー単位の偏り防止が一部の履歴でしか効かない（商品タイプ単位の判定は`product_name`だけで可能なため、この制約を受けない）。
- カテゴリー自体の偏り防止は「優先度を下げる」だけで、固定ローテーションのような強制的な分散は行っていない（ユーザー指示「毎日すべてのカテゴリーを必ず1件ずつ出す固定ローテーションにはしない」に基づく意図的な設計）。
- 実際のGitHub Actions本番実行での挙動確認はこのセッションから直接は行えないため、次回以降の実行結果（Summaryの「商品タイプの偏り防止」欄）で継続的に確認できる。

## セキュリティ

秘密情報（Rakuten Application ID、Access Key、各種トークン等）はコード・ログ・README・本ファイルに一切含めていない。楽天ROOMへの機械的な自動投稿・自動ログイン・購入操作は実装していない（本タスクの変更は候補の並び順調整のみ）。
