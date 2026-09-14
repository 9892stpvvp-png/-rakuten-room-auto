# AI TASK

Status: READY
Owner: ChatGPT -> Claude Code
Task ID: handoff-test-001

## 目的
ChatGPT から GitHub を介して Claude Code に指示を渡し、ユーザーが長い指示文をコピー＆ペーストしなくても作業を引き継げることを確認する。

## 今回のテストタスク
1. `CLAUDE.md` とこの `docs/AI_TASK.md` を読む。
2. 現在の楽天ROOM候補検索システムを確認する。
3. コードや設定は変更しない。
4. 次の4点だけを確認する。
   - GitHub Actions の候補検索ワークフローが存在すること
   - 投稿済み商品の重複除外用データ/処理が存在すること
   - ROOM紹介文生成処理が存在すること
   - 楽天ROOMへの自動投稿処理が実装されていないこと
5. 確認結果を `docs/AI_STATUS.md` に書く。
6. `docs/AI_STATUS.md` の更新だけをコミットして main に push する。コードは変更しない。

## 完了時に `docs/AI_STATUS.md` へ必ず書く内容
- Task ID: handoff-test-001
- Status: DONE または BLOCKED
- 確認した内容
- 変更したファイル
- テスト/確認結果
- 未解決事項

## 安全ルール
- Application ID、Access Key、トークン、パスワード等の秘密情報は表示・記録・コミットしない。
- 楽天ROOMへの自動投稿、自動ログイン、購入操作を追加しない。
- 今回はコード変更禁止。
