# AI STATUS

Task ID: reliability-004
Status: DONE

## 最終更新
Claude Codeが、`data/`・`tiktok/`配下など日次運用で更新される永続JSON/テキストの
書き込み経路を監査し、まだ直接上書きだった2箇所（`data/candidates/`の候補一覧・
`room/data/candidates.json`の投稿ページ用データ）を既存の`src/atomic_io.py`を
再利用してアトミック化した。

## 監査結果

今回の対象は「PR #9・reliability-003で対応済みの箇所と重複しない、日次生成で
更新される永続ファイルの書き込み経路」。`src/`配下の書き込み処理を全て洗い出した
結果は以下の通り。

**既にアトミック化済み（変更不要）:**
- `data/posted_items.json`（`src/dedupe.py`の`_save_posted_items()`）… reliability-003で対応済み
- `data/tiktok_history.json`（`src/tiktok_selector.py`）… PR #9で対応済み
- `tiktok/daily_content.json`・`tiktok/daily_content.md`（`src/tiktok_daily.py`）… PR #9で対応済み

**直接上書きのまま残っていた（今回対応）:**
- `data/candidates/candidates_*.json`・`.md`（`src/storage.py`の`save_candidates()`）
  … `path.open("w")` + `json.dump()` / `Path.write_text()`で直接書き込んでいた。
  この候補一覧は`publish_room_page.py`の`find_latest_candidates_json()`が
  「最も新しいファイル」としてそのまま読み込むため、書き込み途中にプロセスが
  終了して壊れたファイルが残ると、次のステップ（投稿ページ用データ生成）が
  壊れたJSONを読み込んで失敗する可能性があった。
- `room/data/candidates.json`（`src/publish_room_page.py`の`main()`）
  … 同じく直接書き込みだった。このファイルは投稿ページ（`room/index.html`）が
  ブラウザから直接読み込むファイルであり、壊れると投稿ページの表示に影響する。

**対象外と判断（読み込み専用・ログ用途・スコープ外）:**
- `src/main.py`・`src/tiktok_daily.py`の`write_github_step_summary()`
  （`GITHUB_STEP_SUMMARY`への追記）… GitHub Actionsが管理する実行1回限りの
  一時ファイルで、永続データではない。追記(`"a"`)前提のため、`os.replace()`による
  アトミック置き換えとは書き込みモデルが異なり、対象外と判断した。
- `data/past_posted_items_seed.json`・`data/past_posted_items_unresolved.json`
  … 手動投入用のシードファイルで、日次生成では書き込まれない（読み込みのみ）。
- 各種`settings_path.open("r")`等の読み込み処理… 書き込みではないため対象外。

## 実施内容

- `src/storage.py`の`save_candidates()`: `data/candidates/candidates_*.json`と
  `.md`の書き込みを、`atomic_io.write_json_atomic()` / `atomic_io.write_text_atomic()`
  経由に変更した。新規実装は追加していない（既存の`atomic_io.py`を再利用）。
  戻り値（保存先パスのタプル）・Markdown整形処理は変更していない。
- `src/publish_room_page.py`の`main()`: `room/data/candidates.json`の書き込みを
  `atomic_io.write_json_atomic()`経由に変更した。データ整形
  （`build_room_page_data()`）・最新ファイル検索（`find_latest_candidates_json()`）
  のロジックは変更していない。
- `docs/DESIGN.md`に27章として、監査結果・対応内容を記録した。
- `docs/AI_STATUS.md`（このファイル）。

商品検索条件（`src/main.py`・`config/`）、重複判定ロジック、紹介文生成、
TikTok関連（`src/tiktok_*.py`）、`data/posted_items.json`まわり（前回対応済み）、
GitHub Actionsの既存ワークフローには一切手を加えていない。

## 変更ファイル
- `src/storage.py`（`save_candidates()`を`atomic_io`経由に変更）
- `src/publish_room_page.py`（`main()`を`atomic_io`経由に変更）
- `tests/test_storage.py`（新規追加：正常保存・アトミック書き込みの回帰テスト）
- `tests/test_publish_room_page.py`（`MainAtomicWriteTest`を追加）
- `docs/DESIGN.md`（27章を追加）
- `docs/AI_STATUS.md`（このファイル）

## テスト結果

追加したテストで確認した内容:
- `tests/test_storage.py`（`SaveCandidatesTest`・`SaveCandidatesAtomicWriteTest`）
  - 正常にJSON・Markdownが保存され、戻り値のパスが存在すること
  - 出力先ディレクトリが無い場合でも自動作成されること
  - 書き込み途中（`os.fdopen`）で例外が発生しても、出力先ディレクトリに
    壊れかけのファイルが残らないこと
  - JSON・Markdownの保存が実際に`atomic_io.write_json_atomic()` /
    `write_text_atomic()`を経由していること（重複実装の回帰防止）
- `tests/test_publish_room_page.py`（`MainAtomicWriteTest`）
  - `main()`が正常に`room/data/candidates.json`を書き出すこと
  - 書き込み途中で例外が発生しても、既存の`room/data/candidates.json`が
    変更前のまま残り、一時ファイルも残らないこと
  - `main()`が実際に`atomic_io.write_json_atomic()`を経由していること

実行結果:
- `python3 -m unittest tests.test_storage tests.test_publish_room_page tests.test_atomic_io tests.test_dedupe -v` → **93 passed**
- `python3 -m unittest discover -s tests -v` → **224件収集、223 passed**、
  `tests.test_main`のみ収集時に`ModuleNotFoundError: No module named 'dotenv'`で
  失敗（reliability-003の時と同じ、このサンドボックス環境に`python-dotenv`が
  未インストールのためで、今回の変更とは無関係。`src/main.py`のトップレベル
  importが原因。`requirements.txt`には元から記載済みで、CI環境や
  `pip install -r requirements.txt`実行済みの環境では発生しない）。
- 秘密情報（Application ID、Access Key等）は表示・記録していません

## 本番運用上の残課題
- 特になし。日次運用で更新される永続JSON/テキストの主要な書き込み経路
  （投稿済み履歴・TikTok履歴・TikTok日次コンテンツ・候補一覧・投稿ページ用
  データ）は全て`atomic_io`経由のアトミック書き込みに統一された。

## 外部サービス/ユーザー操作が必要な項目
- 特になし。今回の変更は内部の書き込み処理のみで、ユーザー操作・外部サービスの
  利用方法に変更はない。

## 次にChatGPTが判断すべき点
- 特になし。前回（reliability-003）で保留となっていた2箇所（`storage.py`・
  `publish_room_page.py`）へ今回対応したことで、監査対象は一巡した。

## セキュリティ
Application ID、Access Key、トークン、パスワード等の秘密情報はここに記載しないこと。
