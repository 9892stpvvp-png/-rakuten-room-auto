# AI STATUS

Task ID: tiktok-affiliate-001
Status: DONE

## 最終更新
Claude Code がTikTokアフィリエイト機能の現状監査を行い、完成形（`docs/AI_TASK.md`記載の7項目）との差分を確認した。安全に実装できる不足部分（TikTok選定のitem_code単位の重複防止）を実装し、テスト・ドキュメントを更新した。

## 監査結果（完成形7項目との対比）

1. **毎日の投稿候補を自動生成できる**: 対応済み。`run_scheduled_search.yml`が毎日JST15:30に`search_candidates.yml`を起動し、`python -m src.main`が候補を生成する。
2. **商品候補、台本、紹介文、ハッシュタグを一式で出力できる**: 対応済み。ROOM側は`description_generator.py`が紹介文＋ハッシュタグを、TikTok側は`tiktok_content_generator.py`が台本・テロップ・ナレーション・キャプション・ハッシュタグ・動画制作メモを生成する（`tiktok_daily.py`が一連の処理を実行し、`tiktok/daily_content.json`・`tiktok/daily_content.md`に書き出す）。
3. **過去候補/投稿済みとの重複をできるだけ避けられる**: ROOM側（`dedupe.py`、`posted_items.json`基準の4段階判定）は対応済みだが、監査の結果、TikTok選定（`tiktok_selector.py`）にはカテゴリ単位のローテーション（直近3件と同じカテゴリを減点）はあるものの、**同じ商品（item_code）を連日選んでしまう可能性がある不足**を発見した。ROOM側の重複除外は「実際にROOMへ投稿済みか」だけを見るため、まだ人間が投稿していない商品は候補の上位10件に何日も残り続けることがあり、TikTok選定がカテゴリしか見ていないとその商品が繰り返し選ばれ得るため。→ 今回、安全に実装できる不足部分として対応した（詳細は下記「実施した作業」）。
4. **iPhoneから見やすい確認ページを用意する**: 対応済み。`room/index.html`・`tiktok/index.html`ともにモバイル最適化済み（390px幅で横スクロールなし、コピー機能付き、Playwrightでの実機確認済みとdocs/DESIGN.mdに記載）。追加の不具合は見つからなかった。
5. **GitHub Actionsで定期実行できる**: 対応済み。`run_scheduled_search.yml`が毎日1回起動する構成で、cronの性質上同日重複実行も起きない。
6. **秘密情報をGitHubへ露出しない**: 対応済み。`RAKUTEN_APP_ID`・`RAKUTEN_ACCESS_KEY`はRepository Secrets経由のみで、`rakuten_api.py`はエラーメッセージ中の秘密情報をマスクする処理（`_mask_secrets`）を持つ。ログ・README・生成物に秘密情報が出力される箇所は見つからなかった。
7. **TikTokへの自動投稿は実装しない**: 対応済み（未実装であることを確認）。`tiktok_content_generator.py`・`tiktok_daily.py`のdocstringにも明記されており、動画ファイル生成・外部動画生成API連携・TikTokへの自動投稿にあたるコード（selenium/playwright等によるTikTok操作）はリポジトリ内に存在しない。

## 実施した作業

監査で見つかった「TikTok選定が同じ商品を連日選んでしまう可能性がある」という不足に対応した。

- `src/tiktok_selector.py`
  - `_recent_item_codes()`を追加。履歴ファイル（`data/tiktok_history.json`、直近`HISTORY_KEEP_LAST`＝30件を保持）からitem_code一覧を集める。
  - `select_for_tiktok()`で、本日の候補から直近に選定済みのitem_codeを持つ商品を基本的に除外してから、既存のカテゴリベースのスコアリング（便利グッズ優先→優先ジャンル→カテゴリローテーション減点→レビュー件数タイブレーク）を行うように変更。
  - ただし、本日の候補が全て過去に選定済みの商品しかない日（除外すると0件になってしまう日）は、除外せず従来どおり選定する安全策（フォールバック）を入れている。
  - 既存のカテゴリローテーション機能・選定理由の組み立て・履歴の記録処理（`record_selection`）は変更していない。
- `tests/test_tiktok_selector.py`
  - 直近に選定済みの商品は候補が他にあれば除外されることを確認するテストを追加。
  - 本日の候補が全て過去に選定済みの場合はフォールバックして選定できる（0件にならない）ことを確認するテストを追加。
- `docs/DESIGN.md`・`README.md`
  - TikTok商品選定の説明に、今回追加したitem_code単位の重複防止と、その背景（ROOM側の重複除外とTikTok選定の違い）を追記。

商品検索・条件判定・重複チェック・紹介文生成・ROOM側の5+5選定ロジック・スマホ投稿ページ・GitHub Actionsのワークフロー構成・Secretsの扱いには一切手を加えていない。

## 変更したファイル
- `src/tiktok_selector.py`（item_code単位の重複防止ロジックを追加）
- `tests/test_tiktok_selector.py`（上記の新規テスト2件を追加）
- `docs/DESIGN.md`（TikTok選定セクションに今回の変更内容を追記）
- `README.md`（TikTok商品選定の説明を更新）
- `docs/AI_STATUS.md`（このファイル）

## テスト結果
- `python3 -m pytest -q` → **206 passed**（既存204件＋今回追加した2件すべて成功。既存機能に回帰は無い）
- 秘密情報（Application ID、Access Key等）は表示・記録していません

## 未解決事項
- なし（監査で見つかった不足のうち、安全に実装できるものは今回すべて対応済み）

## 外部サービスやユーザー操作が必要な項目
- 楽天ウェブサービスのRepository Secrets（`RAKUTEN_APP_ID`・`RAKUTEN_ACCESS_KEY`）は既に前提として登録済みという想定で進めた（今回新規の外部サービス登録・課金操作は発生していない）。
- 本番動作の最終確認（実際にGitHub Actionsを走らせて、TikTok選定が同じ商品を連日選ばなくなっていることを確認する等）はユーザー側でお願いしたい。

## 次にChatGPTが確認すべき点
- 今回追加したitem_code単位の重複防止ロジックの設計（除外→候補0件ならフォールバックして除外なしで選定）が、意図通りか確認をお願いしたい。
- 今回のタスクではPRの作成まで求められているが、本セッションの運用ルールにより`main`への直接pushではなく専用ブランチ（`claude/kaishi-ah0jdp`）へpushしている。PR作成もこのセッションから対応する。

## セキュリティ
Application ID、Access Key、トークン、パスワード等の秘密情報はここに記載しないこと。
