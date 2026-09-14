# AI TASK

Status: READY
Owner: ChatGPT -> Claude Code

## 目的
ChatGPT と Claude Code の間で、ユーザーが長い指示文や作業結果を毎回手動コピー＆ペーストしなくても、GitHub を共通の受け渡し場所として使えるようにする。

## 今回のタスク
1. この `CLAUDE.md` と `docs/AI_TASK.md` を作業開始時に読む運用にする。
2. 現在の楽天ROOM候補検索システムを確認する。
3. 既存の GitHub Actions、候補検索、重複除外、紹介文生成を壊さない。
4. 作業結果を `docs/AI_STATUS.md` に記録する。
5. 変更が必要な場合は専用ブランチで作業し、テスト後にPRを作成する。

## 現在わかっている状態
- GitHub Actions による楽天ROOM商品候補取得が動作している。
- 投稿済み商品は重複判定対象として管理されている。
- 商品選定と紹介文生成の改善が main にマージ済み。
- 楽天ROOMへの自動投稿は対象外。ユーザーによる手動投稿を維持する。

## 完了条件
- Claude Code がこのファイルから指示を受け取れる。
- 作業結果が `docs/AI_STATUS.md` に残る。
- 秘密情報がGitHubに保存されない。
- 既存テストが壊れていない。
