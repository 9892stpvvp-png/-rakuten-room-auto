# AI TASK

Status: READY
Owner: ChatGPT -> Claude Code
Task ID: reliability-003

## 目的
楽天ROOM/TikTok候補生成の既存機能を壊さず、投稿済み履歴ファイルの破損リスクを減らし、本番の日次運用をさらに安定させる。
ユーザーへの途中確認は不要。ChatGPT が仕様・レビューを担当し、Claude Code が実装・テスト・PR作成を担当する。

## 今回の重点タスク
1. `CLAUDE.md` とこの `docs/AI_TASK.md` を読む。
2. `main` の最新状態を基準に `data/posted_items.json` の読み書き経路を監査する。
3. `src/dedupe.py` など、投稿済み履歴を書き込む処理で、書き込み途中の中断・例外によって JSON が破損する可能性があれば、安全にアトミック書き込みへ変更する。
4. PR #9 で追加済みの `src/atomic_io.py` を再利用できる場合は再利用し、同種の書き込み実装を重複させない。
5. 以下を自動テストで確認する。
   - 正常に保存・再読込できること
   - 書き込み途中に例外が起きても既存の `posted_items.json` が壊れないこと
   - 重複判定（item_code / URL / 商品名）の既存挙動が変わらないこと
   - 既存テストを含めすべて成功すること
6. 必要に応じて README / DESIGN を最小限更新する。
7. 既存の楽天ROOM候補検索、TikTok候補生成、GitHub Actionsの日次生成を壊さない。
8. TikTok/楽天ROOMへの自動投稿・自動ログイン・自動購入は実装しない。
9. 課金が必要な外部サービス、動画生成API、秘密情報の扱い変更は追加しない。

## 完了条件
- `data/posted_items.json` の書き込み破損リスクが確認され、必要ならアトミック化されている
- 既存の重複判定ロジックに回帰がない
- 必要なテストが追加され、既存テストを含め成功している
- 変更は専用ブランチで行い、PRを作成している
- `docs/AI_STATUS.md` に以下を記載している
  - Task ID: reliability-003
  - Status: DONE または BLOCKED
  - 監査結果
  - 実施内容
  - 変更ファイル
  - テスト結果
  - 本番運用上の残課題
  - 外部サービス/ユーザー操作が必要な項目
  - 次にChatGPTが判断すべき点

## 安全ルール
- Application ID、Access Key、APIキー、トークン、パスワード、MFA情報などの秘密情報は表示・記録・コミットしない。
- `.env` や実値の資格情報はコミットしない。
- TikTok/楽天ROOMへの自動投稿、自動ログイン、自動購入は実装しない。
- 課金が発生する外部サービスを勝手に有効化しない。
- 未確認の効果や誇張表現を商品紹介文に入れない。
- 既存のROOM候補検索・重複管理・紹介文生成・TikTok候補生成を壊さない。

<!-- auto-start trigger: 2026-09-18 -->


<!-- auto-start retrigger: 2026-09-18 -->

<!-- auto-start retrigger after bot allowlist: 2026-09-18 -->

<!-- auto-start retrigger after checkout fix: 2026-09-18 -->

<!-- auto-start retrigger after tool permissions fix: 2026-09-18 -->
