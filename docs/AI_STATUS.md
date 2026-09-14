# AI STATUS

Task ID: tiktok-affiliate-002
Status: DONE

## 最終更新
Claude Code が、TikTok日次生成の本番運用上の穴を`main`最新状態を基準に監査し、見つかった問題を安全に修正した。

## 発見した問題

1. **TikTok側だけ失敗すると、成功していたROOM側の更新まで失われる（最重要）**
   `search_candidates.yml`は、ROOM候補生成→スマホ投稿ページのデータ書き出し→TikTokコンテンツ生成→コミット・pushの順のステップ構成。GitHub Actionsは前のステップが失敗すると後続ステップを実行しないデフォルト挙動のため、**ROOM候補生成・投稿ページのデータ書き出しが成功していても、TikTokコンテンツ生成だけが失敗すると、最後の「コミットしてプッシュ」ステップごと実行されず、成功していたROOM側の新しい候補データまでコミットされずに失われる**状態だった。
2. **同じ日に手動で複数回実行すると、履歴に同日の記録が何件も積み重なる**
   `tiktok_selector.record_selection()`が選定結果を無条件で追記していたため、同じ日にワークフローを複数回手動実行すると、`data/tiktok_history.json`に同じ日付の記録が複数残ってしまう「不自然な二重記録」が起きる状態だった。
3. **書き込み途中でプロセスが終了すると、JSONファイルが壊れた状態で残る可能性**
   `data/tiktok_history.json`・`tiktok/daily_content.json`・`tiktok/daily_content.md`はいずれも`open(path, "w")`で直接書き込んでおり、GitHub Actionsのジョブタイムアウトや手動キャンセル等で書き込み途中にプロセスが終了すると、書きかけの不完全なファイルが残る可能性があった。

## 確認して問題が無かった項目

- **日次実行をまたいだ履歴の永続化**: `data/tiktok_history.json`は毎回のワークフロー実行の最後にコミット・pushされ、次回実行は`actions/checkout@v4`でその最新状態から始まるため、永続化の仕組み自体は元から正しく機能していた（問題1は「失敗時にコミットされない」という別の問題であり、区別して対応した）。
- **GitHub Actionsが生成物だけを安全にコミットすること**: 最後のコミットステップは`git add -A`等ではなく`room/data/candidates.json`・`tiktok/daily_content.json`・`tiktok/daily_content.md`・`data/tiktok_history.json`の4ファイルだけを明示的に指定しており、`.env`や`data/candidates/`（`.gitignore`対象）等の意図しないファイルが混入する余地はない。変更不要と判断した。
- **iPhone向け`tiktok/index.html`のデータ連携**: `daily_content.json`をキャッシュを無視して取得し（`cache: "no-store"`・タイムスタンプ付きクエリ）、取得失敗時・商品名が無い場合にそれぞれ分かりやすいメッセージを表示する作りで、商品名・台本・テロップ・ナレーション・キャプション・ハッシュタグ・動画制作メモそれぞれに「コピー」ボタンが付いている。追加の問題は見つからなかった。

## 実施した作業

- `.github/workflows/search_candidates.yml`
  - TikTokコンテンツ生成ステップに`id: tiktok`を付与。
  - 最後の「投稿ページ・TikTok用データをコミットしてプッシュ」ステップに`if: always()`を付け、TikTok生成が失敗・スキップされてもROOM側のデータだけは確実にコミットされるようにした。`steps.tiktok.outcome == 'success'`のときだけ`tiktok/`・`data/tiktok_history.json`を`git add`対象に含めるようにし、TikTok側の新旧データが矛盾した状態でコミットされないようにした。
  - TikTok生成ステップだけが失敗した場合に、Actionsの実行結果ページ（Summary）へ分かりやすい説明を書き出す新しいステップを追加した。
- `src/tiktok_selector.py`
  - `record_selection()`で、新しい記録を追記する前に同じ日付の既存記録を取り除くようにした（同日再実行時の二重記録を防止）。
  - 履歴ファイルの書き込みを、新設した`atomic_io.write_json_atomic()`経由に変更。
- `src/tiktok_daily.py`
  - `daily_content.json`・`daily_content.md`の書き出しを、`atomic_io`経由のアトミックな書き込みに変更。
- `src/atomic_io.py`（新規）
  - 「一時ファイルに書いてから`os.replace()`で置き換える」アトミックな書き込みヘルパー（`write_text_atomic`・`write_json_atomic`）を追加。
- `tests/test_atomic_io.py`（新規）・`tests/test_tiktok_selector.py`
  - アトミック書き込みの正常系・異常系（書き込み失敗時に元のファイルが壊れず一時ファイルも残らないこと）、同日再実行時に履歴が1件に保たれることを確認するテストを追加。
- `docs/DESIGN.md`・`README.md`
  - 監査結果・対応内容・確認して問題が無かった項目を追記。

商品検索・条件判定・重複チェック・紹介文生成・ROOM側の5+5選定ロジック・TikTok商品選定のカテゴリローテーション/item_code重複防止（前回tiktok-affiliate-001で追加）・スマホ投稿ページ・Secretsの扱いには変更していない。

## 変更したファイル
- `.github/workflows/search_candidates.yml`
- `src/tiktok_selector.py`
- `src/tiktok_daily.py`
- `src/atomic_io.py`（新規）
- `tests/test_atomic_io.py`（新規）
- `tests/test_tiktok_selector.py`
- `docs/DESIGN.md`
- `README.md`
- `docs/AI_STATUS.md`（このファイル）

## テスト結果
- `python3 -m pytest -q` → **215 passed**（既存206件＋今回追加した9件、すべて成功。既存機能に回帰は無い）
- `.github/workflows/search_candidates.yml`は`python3 -c "import yaml; yaml.safe_load(...)"`でYAML構文を確認済み
- 秘密情報（Application ID、Access Key等）は表示・記録していません

## 本番運用上の残課題
- 今回の修正はローカルでのユニットテスト・YAML構文確認までで、実際のGitHub Actions実行環境での動作確認（TikTok生成を意図的に失敗させてROOM側だけコミットされることを確認する等）はできていません。次回の日次実行、または手動での`workflow_dispatch`実行時の結果を確認していただくことをおすすめします。
- `data/posted_items.json`（ROOM投稿済み履歴）の書き込み（`src/dedupe.py`の`_save_posted_items`）は、今回スコープ外のためアトミック書き込みに変更していません。同種の「書き込み途中のプロセス終了で壊れる」リスクは理論上残っていますが、今回のタスク（TikTok日次生成）の範囲外と判断しました。

## 外部サービス/ユーザー操作が必要な項目
- 特になし（今回新規の外部サービス登録・課金操作は発生していません）。

## 次にChatGPTが判断すべき点
- `data/posted_items.json`の書き込みも同様にアトミック化すべきか（残課題参照）。
- 今回の3つの修正（コミット失敗時の分離・同日再実行時の重複防止・アトミック書き込み）の設計が意図通りか確認をお願いしたい。
- PRを作成済み: https://github.com/9892stpvvp-png/-rakuten-room-auto/pull/9 （ブランチ`claude/kaishi-ah0jdp` → `main`）。マージはユーザー側でお願いします。

## セキュリティ
Application ID、Access Key、トークン、パスワード等の秘密情報はここに記載しないこと。
