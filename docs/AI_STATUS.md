# AI STATUS

Task ID: user-request-posted-items-auto-register（ChatGPTのAI_TASK.md経由ではなく、ユーザーからの直接依頼）
Status: DONE

## 最終更新
Claude Code が、「ROOMで実際に投稿した商品をposted_items.jsonへ手作業なく安全に反映したい」というユーザーからの直接依頼に対応した。

## 依頼内容の要点
- 商品候補を作る処理・`data/candidates.json`・`data/posted_items.json`・`src.import_posted_items`・GitHub Actions・現在の重複判定の仕組みを把握したうえで、
- 既存の仕組みを壊さずに、「実際にROOMへ投稿済みになった商品だけ」を`posted_items.json`へ自動登録する方法を設計・実装する。
- 「ROOMへ本当に投稿されたこと」を自動判定できない場合は、推測で実装せず、(1)現在どこまで自動化できるか (2)不足している情報・連携 (3)最も安全で簡単な実装方法、を報告する。

## 調査結果：「ROOMへ本当に投稿されたこと」の完全自動判定は不可能

1. **現在どこまで自動化できるか**: 商品候補の生成（検索→条件判定→重複除外→紹介文生成→`data/candidates/`・`room/data/candidates.json`への保存）は既に毎日自動化されている。投稿済み履歴への登録は、従来「スマホ投稿ページで自己申告→JSONをコピー→ローカルに保存→`python -m src.import_posted_items`を手動実行→git commit/push」という人手を挟む経路のみだった。
2. **完全自動化に不足している情報・連携**: 楽天ROOMには投稿履歴を読み取れる公式APIが存在しない（このプロジェクトが使う楽天ウェブサービスAPIは商品検索専用）。ROOM側の投稿状況を確認する唯一の技術的手段はROOMへの自動ログイン・Cookie/セッション利用・画面スクレイピングだが、これはCLAUDE.mdおよび各タスクの安全ルールで明確に禁止されている。したがって、「候補に出ただけの商品」と「実際に投稿済みの商品」をプログラムだけで区別する情報・連携は存在せず、最終的には人間の自己申告（スマホ投稿ページでの「投稿済みにする」操作）に頼るしかない。これは今回新たに生じた制約ではなく、従来の仕組みも元々同じ自己申告を前提にしていた。
3. **最も安全で簡単な実装方法**: 「投稿完了の自動判定」自体は実装不可能なため、既存の自己申告データ（スマホ投稿ページの「投稿済みにする」）を`posted_items.json`へ反映するまでの**手作業だけを取り除く**方針を採った。GitHub Actionsの`workflow_dispatch`（手動実行・テキスト入力欄付き）を新設し、コピーしたJSONを貼り付けて実行するだけで、ローカルでのファイル保存・Python実行・git操作なしに登録できるようにした。`workflow_dispatch`はGitHub標準の権限モデルにより、このリポジトリへの書き込み権限を持つ人しか実行できないため、独自の権限チェックを実装する必要がなく、GitHub Issue等の第三者が起票できる仕組みより安全と判断した。

## 実施した作業

- `.github/workflows/import_posted_items.yml`（新規）: `workflow_dispatch`でJSONを貼り付けて実行する手動ワークフロー。貼り付けられたJSONをファイルに書き出し、既存の`python -m src.import_posted_items`（変更なしのロジック）に渡し、`data/posted_items.json`に変化があった場合だけコミット・push する。入力値は`env:`経由で渡し、シェルインジェクションを避けている。
- `src/import_posted_items.py`: `json.load()`失敗時に生のトレースバックではなく分かりやすい日本語メッセージで`SystemExit`するよう改善（既存の重複判定・取り込みロジック自体は変更なし）。
- `room/index.html`: 「① 投稿済みデータをコピー」の隣に「② GitHubへ登録する」リンク（Actionsワークフローのページを新しいタブで開く）を追加。コピーするJSONを、Actionsの入力欄でも安全に扱えるよう1行のJSON（改行なし）に変更（取り込み処理はJSONの改行有無を区別しないため、既存のローカルファイル経由の取り込みに影響なし）。
- `README.md`・`docs/DESIGN.md`: 上記の調査結果・設計判断・使い方を追記。

商品候補生成・重複判定（item_code→URL→商品名→match_keywords）・既存のGitHub Actions（`search_candidates.yml`・`run_scheduled_search.yml`）・`data/posted_items.json`の既存データには一切変更していない（追記のみで削除なし）。ROOMへの自動投稿・自動ログイン・投稿状況の自動判定は実装していない。

## 変更したファイル
- `.github/workflows/import_posted_items.yml`（新規）
- `src/import_posted_items.py`
- `room/index.html`
- `tests/test_import_posted_items.py`
- `README.md`
- `docs/DESIGN.md`
- `docs/AI_STATUS.md`（このファイル）

## テスト結果
- `python3 -m pytest -q` → **217 passed**（既存215件＋今回追加した2件、すべて成功。既存機能に回帰は無い）
- `.github/workflows/import_posted_items.yml`のYAML構文を`yaml.safe_load`で確認
- `room/index.html`が変更後もHTMLとして正しくパースできることを`html.parser`で確認
- 秘密情報（Application ID、Access Key等）は表示・記録していません

## 自動化後の流れ
1. スマホ投稿ページでROOMへ実際に投稿した商品を「投稿済みにする」で記録する（変更なし・人間の自己申告）
2. 「① 投稿済みデータをコピー」でJSONをコピーする（変更なし）
3. 「② GitHubへ登録する」を開き、GitHubの「Actions」タブで「投稿済み商品を登録する」ワークフローの「Run workflow」→入力欄にJSONを貼り付け→実行する（新規。パソコン・Python・git操作・ChatGPTへの貼り付けは不要）
4. ワークフローが`data/posted_items.json`を更新し、自動でコミット・pushする（新規）

## オーナー側に残る操作
- 実際に楽天ROOMへ投稿する操作そのもの（安全ルール上、自動化していません）
- スマホ投稿ページで「投稿済みにする」を押す自己申告操作（ROOMへの投稿完了をプログラムだけで確認する手段が存在しないため）
- コピーしたJSONをGitHub Actionsの入力欄に貼り付けて「Run workflow」を押す操作（この1手順だけが今回新たに残る操作で、以前あった「ローカル保存・コマンド実行・git commit/push」は不要になりました）

## 本番運用上の残課題
- 今回の変更は自動テスト・YAML構文確認までで、実際のGitHub Actions実行環境（`workflow_dispatch`の入力欄への貼り付け・実行）での動作確認はできていません。次回、実際にROOM投稿後にこのワークフローを試していただくことをおすすめします。
- GitHub Actionsの`workflow_dispatch`テキスト入力欄には（明文化された公式の上限は把握していませんが）大きすぎるJSONを貼り付けると失敗する可能性があります。一度に登録する件数が多い日（数十件など）は、複数回に分けて実行することをおすすめします。

## 外部サービス/ユーザー操作が必要な項目
- 特になし（今回新規の外部サービス登録・課金操作は発生していません。GitHub Actionsの標準機能のみを使用）

## 次にChatGPTが判断すべき点
- 今回の設計（GitHub Issue経由ではなく`workflow_dispatch`のテキスト入力を採用したこと、権限チェックをGitHub標準の書き込み権限モデルに委ねたこと）が意図通りか確認をお願いしたい。
- 「実際に投稿されたこと」の自動判定自体は技術的に不可能という結論について、認識に相違がないか確認をお願いしたい。

## セキュリティ
Application ID、Access Key、トークン、パスワード等の秘密情報はここに記載しないこと。
