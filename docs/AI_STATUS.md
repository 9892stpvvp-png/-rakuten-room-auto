# AI STATUS

Task ID: reliability-003
Status: DONE

## 最終更新
Claude Code が、`data/posted_items.json`（投稿済み履歴）の読み書き経路を監査し、書き込み処理をアトミック化した。

## 監査結果

`data/posted_items.json`を書き換える処理は`src/dedupe.py`の`append_posted_items()`（内部で`_save_posted_items()`を呼ぶ）の1箇所だけで、他に直接書き込む箇所は無かった。

- `_save_posted_items()`はこれまで`path.open("w", encoding="utf-8")` + `json.dump()`で直接書き込んでいた。GitHub Actionsのジョブタイムアウト・手動キャンセル・予期しないクラッシュ等で書き込みの途中にプロセスが終了すると、書きかけの不完全な（壊れた）JSONがそのまま残る可能性があった。
- PR #9で追加済みの`src/atomic_io.py`（`write_text_atomic` / `write_json_atomic`）は、`data/tiktok_history.json`・`tiktok/daily_content.json`・`tiktok/daily_content.md`の保存（`src/tiktok_selector.py`・`src/tiktok_daily.py`）では既に使われていたが、`data/posted_items.json`の保存だけは未対応のまま残っていた（docs/DESIGN.md 23章の対応範囲外）。
- 読み込み側（`load_posted_items` / `load_posted_item_codes`）・重複判定ロジック（`match_posted_reason`等、item_code→URL→商品名→match_keywordsの優先順位）には問題を確認しなかった（変更不要と判断）。

## 実施内容

- `src/dedupe.py`の`_save_posted_items()`を、新規実装を追加せず既存の`atomic_io.write_json_atomic()`を再利用する形に変更した（同種の書き込み実装を重複させないため）。
- `append_posted_items()`のシグネチャ・戻り値（`AppendResult`）・重複判定ロジック・読み込み側の関数は一切変更していない。
- `docs/DESIGN.md`に26章として、原因・対応内容を記録した。

## 変更ファイル
- `src/dedupe.py`（`_save_posted_items()`を`atomic_io.write_json_atomic()`経由に変更）
- `tests/test_dedupe.py`（アトミック書き込みの回帰テストを追加）
- `docs/DESIGN.md`（26章を追加）
- `docs/AI_STATUS.md`（このファイル）

商品検索条件（`src/main.py`・`config/`）、重複判定ロジック本体、TikTok関連（`src/tiktok_*.py`）、GitHub Actionsの既存ワークフローには一切手を加えていない。

## テスト結果

追加したテスト（`tests/test_dedupe.py` `AppendPostedItemsAtomicWriteTest`）で確認した内容:
- 正常に保存・再読込できること（既存の`AppendPostedItemsTest`で確認済み、今回も回帰なし）
- 書き込み途中（`os.fdopen`）で例外が発生しても、既存の`posted_items.json`の内容が変更前のまま残ること
- 書き込み失敗時に一時ファイルが残らないこと
- `_save_posted_items()`が実際に`atomic_io.write_json_atomic()`を経由していること（重複実装の回帰防止）
- 重複判定（item_code / URL / 商品名 / match_keywords）の既存挙動に変化がないこと（既存の`MatchPostedReasonTest`・`IsPostedAndRemoveDuplicatesTest`等が全て成功）

実行結果:
- `python3 -m unittest tests.test_dedupe tests.test_atomic_io -v` → **73 passed**
- `python3 -m unittest discover -s tests -v` → **217 passed**、`tests.test_main`のみ収集時に`ModuleNotFoundError: No module named 'dotenv'`で失敗（このサンドボックス環境に`python-dotenv`が未インストールのため。`src/main.py`のトップレベルimportが原因で、今回の変更とは無関係。`requirements.txt`には元から記載済みで、CI環境や`pip install -r requirements.txt`を実行済みの環境では発生しない）。
- 秘密情報（Application ID、Access Key等）は表示・記録していません

## 本番運用上の残課題
- 特になし。`data/posted_items.json`の書き込みは、他のJSON/Markdown出力（`tiktok_history.json`・`daily_content.json`等）と同じアトミック書き込み方式に統一された。

## 外部サービス/ユーザー操作が必要な項目
- 特になし。今回の変更は内部の書き込み処理のみで、ユーザー操作・外部サービスの利用方法に変更はない。

## 次にChatGPTが判断すべき点
- `src/storage.py`（候補一覧`data/candidates/candidates_*.json`）・`src/publish_room_page.py`（`room/data/candidates.json`）も同様に`path.open("w")` + `json.dump()`で直接書き込んでいるが、これらは投稿済み履歴（重複防止の基盤データ）ではなく毎回作り直す生成物であるため、今回のタスク範囲（投稿済み履歴の破損リスク低減）には含めなかった。壊れた場合の影響は「次回生成まで表示が乱れる」程度に留まり、`posted_items.json`ほど重要ではないと考えているが、同様にアトミック化する価値があるかはChatGPT側で判断してほしい。

## セキュリティ
Application ID、Access Key、トークン、パスワード等の秘密情報はここに記載しないこと。
