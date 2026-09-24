# AI STATUS

Task ID: user-request-all-genre-selection-policy（ユーザーからの直接依頼）
Status: DONE

## 最終更新

Claude Codeが、商品選定方針を「暮らしの便利グッズ5件＋消耗品・飲料5件」の固定構成から、「楽天市場の売れ筋・人気傾向を参考にしながら、全ジャンルから売れやすい候補を毎日10件選ぶ方式」へ変更した。既存の品質基準・重複防止・商品タイプ偏り防止・紹介文の安全性は維持している。

## 1. 変更前の選定方式

`src.main.main()`のフェーズ3が、`settings.yaml`の各keywordsエントリに付けた`group`（convenience=暮らしの便利グッズ／consumable=消耗品・飲料）で候補を二分し、`ranking.select_balanced_top()`でconvenience枠から5件・consumable枠から5件を選んでいた（片方が5件に満たない場合だけ、もう片方の枠から補充）。

## 2. 変更後の選定方式

`ranking.select_top_candidates()`を新設し、全ジャンルの候補を1つのプールとして扱って上位`daily_target`（10）件を選ぶ。「各ジャンル◯件」という固定ローテーションにはせず、品質（レビュー件数・評価）・直近投稿との偏り防止・適度なランダム性を踏まえ、`max_per_category`（2）の上限内で売れ筋状況に応じて構成が変わる。新しいアルゴリズムは作らず、既存の`sort_by_quality()`（品質・優先度・ランダム性の並び替え）と`diversify_top()`（カテゴリー上限を守りつつ、不足時は上限を超えてでも埋める2巡構造）をそのまま再利用している。

## 3. 楽天公式ランキングデータを実際に取得できたか

**取得できていません（未実装）**。現状調査の結果、`src.rakuten_api.search_items()`が呼び出しているのは楽天ウェブサービスの商品検索API（`IchibaItem/Search`）のみで、`sort=-reviewCount`（レビュー件数降順）以外にランキングを示す情報は取得していません。楽天公式のランキング専用API（`IchibaItem/Ranking`等）を呼び出す関数はコードベースに存在しません。今回、未検証のエンドポイント・認証要件を本番相当のテストなしに新規実装することはリスクが高いと判断し、見送りました。GitHub Actions Summaryにも「楽天公式ランキングAPI（IchibaItem/Ranking等）の利用: **していません**」と事実どおり表示します。

## 4. 需要指標として使用したもの

- レビュー件数・レビュー評価（既存の品質スコア`quality_score`。累積的な購入・利用動向の目安）
- 検索結果内でのレビュー件数順（`sort=-reviewCount`。「検索結果内での人気度」に相当する、実際に取得可能な情報）

「直近の購入動向トレンド」（増加率等）は単発の検索APIからは取得できないため、レビュー件数という累積指標をそのまま代替指標として使っており、存在しないデータを新たに作ってはいません。

## 5. 全ジャンル候補の取得方法

`config/settings.example.yaml`の`keywords`に、食品・美容・家電・生活雑貨・ファッション・ペット用品・ベビー用品・健康の8ジャンル・14エントリを追加した（既存の掃除・収納・キッチン・時短・暮らし全般・洗剤・キッチン消耗品・日用品・水・お茶・ジュースは無変更）。「ファッション」は既存の`off_theme_keywords`（財布・アクセサリー・時計・コスメ等の除外フィルタ、無変更）と衝突しない実用品（折りたたみ傘・エコバッグ）を選定。「健康」は医薬品的な効果効能の誤断定リスクを避け、体温計・血圧計等の非接触・非侵襲の測定機器のみを対象にした。`ng_keywords`に医薬品関連（医薬品各分類・処方薬・サプリメント・医療機器）を追加し、候補選定の入口でも安全策を強化した。

## 6. 偏り防止方法

既存の`priority_tier`（直近7日以内、`posted_at`が実際に保存されている投稿だけを対象にした`_product_type`・`_category`別の優先度調整。完全除外ではなく段階的に優先度を下げるだけ）をそのまま再利用。「大ジャンル/細ジャンル」は既存の`_category`（ジャンル）と`_product_type`（商品タイプ）の2階層をそのまま活用し、新しい3階層目は追加していない。`diversify_top()`の`max_per_category`上限（2）により、同じジャンルへの偏りを抑えつつ、候補が少ないジャンルしかない日は上限を超えてでも埋める（品質条件は緩めない）。

## 7. ランダム性の仕組み

既存の日次シード乱数（`_daily_random_seed()`。JST日付から生成）をそのまま使用。`sort_by_quality()`が優先度・品質が同点の商品同士の並びだけをこのrngでシャッフルする（品質順そのものは変えない）。同じ日のうちの再実行では同じ結果になり、日付が変われば自然に変わる（新規テストで同日再現性を確認済み）。

## 8. 変更したファイル

- `src/ranking.py`: `select_top_candidates()`を新設。`select_balanced_top()`・`CONVENIENCE_GROUP`・`CONSUMABLE_GROUP`は後方互換のため無変更のまま残した。
- `src/main.py`: フェーズ3を`select_top_candidates()`の呼び出しに置き換え。診断情報の集計（品質条件除外件数等）を追加。
- `src/storage.py`: `build_genre_selection_summary_markdown()`を新設（ジャンル別・商品タイプ別の採用件数、ランキングAPI利用有無等）。`build_supply_diagnostics_markdown()`は後方互換のため無変更のまま残した。
- `src/description_generator.py`: `HASHTAG_BY_CATEGORY`に8ジャンル分のハッシュタグを追加。`GENERIC_TEMPLATES[DEFAULT_CATEGORY]`にhook_variants等（文章バリエーション）を追加（新ジャンルの多くがここにフォールバックするため、同じ文章になりすぎないようにするための追加）。
- `config/settings.example.yaml`: 全ジャンル化のkeywords追加、`daily_target`/`max_per_category`の新設（`convenience_target`等を置き換え）、`ng_keywords`に医薬品関連を追加。
- `tests/test_ranking.py`・`tests/test_main.py`: 新規テスト追加、5+5固定を前提にしていたテストの書き換え（詳細は下記）。
- `docs/DESIGN.md`（34章に記録）・`docs/AI_STATUS.md`（このファイル）。

`src/dedupe.py`・`src/filters.py`・`src/rakuten_api.py`・`src/publish_room_page.py`・`src/tiktok_daily.py`・`src/tiktok_selector.py`・`room/index.html`・`data/posted_items.json`・`.github/workflows/`・楽天API認証情報には一切変更していない。

## 9. 追加テスト

`tests/test_ranking.py`に`SelectTopCandidatesTest`（7件）を追加：5+5固定にならない／単一ジャンルへの集中を抑える／重複商品を採用しない／候補不足時に水増ししない／直近ジャンルの優先度調整（完全除外ではない）／同じseedでの再現性。

`tests/test_main.py`に以下を追加・変更：
- 新規：`test_normal_run_does_not_force_five_convenience_and_five_consumable`、`test_normal_run_selects_from_more_than_two_genres`、`test_same_day_rerun_is_reproducible`、`test_ranking_api_is_not_used_and_diagnostics_say_so_honestly`、`test_new_genre_without_specific_template_falls_back_safely`
- 書き換え：`test_posted_history_exclusion_still_reaches_ten_from_other_genres`（旧`...triggers_fallback_to_reach_ten`）、`test_scarce_genres_are_filled_from_other_genres`（旧`test_convenience_shortfall_is_filled_from_consumable`）、`test_supply_diagnostics_summary_shows_counts_and_keywords_tried`（新しい診断markdown形式に対応）
- 頑健化：`test_match_keywords_partial_match_does_not_exclude_candidate`等、全ジャンル化で候補プールが大きくなったことで競合に左右されないよう、無関係キーワードを0件に固定する形に修正
- `RunPipelineTest`・`ProductTypeDiversityPipelineTest`の`setUp()`で`_daily_random_seed`を固定シードにパッチし、テスト実行日に関わらず結果が再現できるようにした（本番の日次シード自体は変更していない）

「既存329件のテストをすべて維持」という指示と、「5+5固定にならないことをテストする」という指示は、5+5固定を直接検証していた数件のテストに関しては両立しないため、それらは同じ観点（除外・品質条件・候補不足時の挙動）を新方式向けに検証する内容へ書き換えた。それ以外の全テストは無変更のまま成功している。

## 10. 全テスト結果

`python3 -m pytest -q` と `python3 -m unittest discover -s tests` の両方で**339件全て成功**（本タスク開始前は329件）。

## 11. 新方式で生成した候補10件（シミュレーション）

このセッションには実際の楽天ウェブサービスのアプリID・アクセスキーが無いため、本番同様のライブAPI実行はできなかった。かわりに、実在の商品名の言い回しに近い合成データ（30種のキーワードそれぞれに現実的な商品名・レビュー件数・評価を持たせたもの）で`src.main.main()`を実行するシミュレーションを行った。`room/data/candidates.json`は本物の実行結果ではないため上書きしていない（次回のGitHub Actions定時実行で本物のデータに更新される）。

| # | 商品名 | ジャンル | 商品タイプ | 評価 | レビュー件数 |
|---|---|---|---|---|---|
| 1 | 野菜生活100 ペットボトル 720ml 15本 | ジュース | ジュース | 4.6 | 7865件 |
| 2 | ムーニー おむつ テープ 新生児 72枚 | ベビー用品 | ベビー用品 | 4.8 | 7481件 |
| 3 | 伊藤園 野菜ジュース 200ml 24本 | ジュース | ジュース | 4.3 | 7399件 |
| 4 | 折りたたみエコバッグ 大容量 撥水加工 | ファッション | ファッション | 4.8 | 7381件 |
| 5 | モンベル 折りたたみ傘 トラベル アンブレラ | ファッション | ファッション | 4.4 | 6309件 |
| 6 | 超音波式 アロマディフューザー 大容量 LEDライト付き | 生活雑貨 | 生活雑貨 | 4.9 | 6307件 |
| 7 | 毛穴撫子 お米のマスク 10枚入り | 美容 | 美容 | 4.1 | 5917件 |
| 8 | 無印良品 レトルトカレー バターチキン 5個 | 食品 | 食品 | 4.4 | 5742件 |
| 9 | 山善 サーキュレーター コンパクト | 家電 | 家電 | 4.0 | 5615件 |
| 10 | タニタ 血圧計 デジタル 家庭用 | 健康 | 健康 | 4.8 | 5296件 |

## 12. 各商品の需要根拠

10件全て、レビュー評価4.0以上・レビュー件数100件以上の品質条件を満たし、そのうえで品質スコア（レビュー件数優先、レビュー評価次点）が高い順に、ジャンルの偏り防止（`max_per_category=2`）を適用して選ばれている。8ジャンルにまたがっており、特定ジャンルへの異常な偏りは無い（同一ジャンルは「ジュース」「ファッション」のみ各2件、他は全て1件）。同一商品タイプの重複も無い。

## 13. 紹介文チェック結果

10件全てについて確認した。

- 商品と用途が一致：確認済み（誤用途の断定は無い）。
- 確認できない用途を作っていない：確認済み（「治る」「改善する」「予防できる」「痩せる」「健康になる」等の効果は使っていない。テストでも確認）。
- 数量の意味：72枚・15本・24本・5個等、いずれも正しく反映。
- カテゴリー由来の誤分類：無い（新ジャンルは全てPRODUCT_TYPE_TEMPLATESに未登録のためDEFAULT_CATEGORYの安全な汎用テンプレートにフォールバックしており、断定的な用途は生成していない）。
- 過去に修正した問題（洗濯洗剤→食器洗い、購入制限→まとめ買い等）は再発していない（回帰テストで確認）。
- 文章の繰り返し：DEFAULT_CATEGORYへのフォールバックが多い（8件中7件）ため、修正前は7件がほぼ同一文章になる問題が見つかり、`GENERIC_TEMPLATES[DEFAULT_CATEGORY]`にhook_variants等を追加して改善した（残っている制約として下記に記載）。

既投稿商品との重複：シミュレーションでは実際の`data/posted_items.json`（125件）を参照し、1件がmatch_keywordsにより投稿済みとして除外されたことを確認した（重複防止が機能している）。

品質条件を満たす候補が10件未満になるケースは、今回のシミュレーションでは発生しなかった（59件の候補プールから10件選定）。

## 14. 既存の投稿フローが維持されていること

- `data/posted_items.json`・投稿済み登録ワークフロー（`import_posted_items.yml`・`src/import_posted_items.py`）は無変更（`git status`で確認）。
- `room/index.html`（GitHub Pagesのスマホ投稿ページ）は無変更。候補データのフィールド構成（`item_code`/`item_url`/`description`/`category`/`group_label`等）は変更しておらず、紹介文コピー・楽天市場を開く・検索ワードコピー・商品URLコピー・投稿済みにする・GitHubへ投稿済み登録の各機能に影響しない。
- `.github/workflows/search_candidates.yml`（GitHub Actionsの実行時刻・処理内容）は無変更。`python -m src.main`のインターフェース（呼び出し方・出力先）を変えていないため、ワークフロー側の変更は不要だった。
- 楽天API認証情報には一切触れていない。

## 15. 残っている制約

- 楽天公式ランキングAPIは利用していない（未実装）。需要・人気の指標はレビュー件数・レビュー評価・検索結果内でのレビュー件数順にとどまる。
- 新しく追加した8ジャンルは`PRODUCT_TYPE_TEMPLATES`・`GENERIC_TEMPLATES`に専用テンプレートを持たず、`DEFAULT_CATEGORY`の汎用テンプレートにフォールバックする（安全だが、ジャンル特有の言い回しではない）。
- `DEFAULT_CATEGORY`のhook_variants等は4パターン程度のため、同じ日にDEFAULT_CATEGORYへフォールバックする商品が多いと、まれに同じ組み合わせになることがある（重複回避リトライで軽減されるが完全には防げない）。
- 医薬品・サプリメント等は`ng_keywords`による機械的なキーワード除外であり、完全な法令チェックではない。
- 今回は実際の楽天APIでの実行確認ができていない（認証情報が本セッションに無いため）。次回のGitHub Actions定時実行（本物の認証情報を使用）で新方式が実際にどう動くか、`data/candidates/`・`room/data/candidates.json`・Actions Summaryで確認できる。

## セキュリティ

秘密情報（Rakuten Application ID、Access Key、各種トークン等）はコード・ログ・README・本ファイルに一切含めていない。楽天ROOMへの機械的な自動投稿・自動ログイン・購入操作は実装していない。広告/PR表示・ポイント倍率・クーポン・ランキング表記を採用/除外の直接条件にはしていない（既存方針を維持）。
