# CLAUDE.md（Scryfall MCP Server 開発ガイド）

作業前に必読。本書は**要約とポインタ**に徹し、詳細ルールは `.claude/rules/` に集約する。
Magic: The Gathering のカードデータを MCP 経由で AI アシスタントに提供するサーバー。Scryfall API との統合により、日本語を含む自然言語でのカード検索を提供する。

## 禁止事項（必須・詳細は .claude/rules/）

- ❌ Scryfall への**レート制限を無視しない**（最大 10 req/s、リクエスト間隔 75–100ms 以上、`User-Agent`＋`Accept` ヘッダー必須）→ [.claude/rules/coding.md](.claude/rules/coding.md)
- ❌ **テストで実 API を叩かない**（Scryfall はモック化必須）。
- ❌ **stdout に print しない**（stdio transport が壊れる）。ログは標準 `logging` で stderr へ。
- ❌ `ImageContent` を使わない（MCP 仕様に存在しない）。MCP 出力は `TextContent` と `EmbeddedResource` のみ。
- ❌ ユーザー向けコンテンツに `audience=["user"]` 単独を使わない（UI 表示が保証されない）。**必ず `["user", "assistant"]`**。
- ❌ ドキュメントに**動的情報（テスト数・カバレッジ%・日付・コミットハッシュ）を書かない** → [.claude/rules/documentation.md](.claude/rules/documentation.md)
- ❌ ログに個人情報・API キー・Redis 認証情報・User-Agent の連絡先を出さない。

## 開発ルール（詳細＝[.claude/rules/python.md](.claude/rules/python.md)）

- Python 3.12 / 依存管理は uv / lint＋整形＝Ruff・型＝mypy --strict / pytest（カバレッジ95%目標）。
- 型ヒント必須（PEP 585、`X | None`、`Optional` 不可）。docstring は **NumPy style** 必須。
- I/O はすべて `async`/`await`（httpx async）。ただし惰性で全付与しない。
- 関数は50行以内・ネスト最大3レベル・早期リターン・単一責任。ハンガリアン記法禁止。
- プロジェクト固有の制約（Scryfall API・MCP 出力・i18n・セキュリティ）＝[.claude/rules/coding.md](.claude/rules/coding.md)。
- ドキュメント作成＝[.claude/rules/documentation.md](.claude/rules/documentation.md)。

## アーキテクチャ要点

- **検索パイプライン**：自然言語クエリ → Parser → QueryBuilder → Presenter → MCP レスポンス（`src/scryfall_mcp/search/`）。コアは純粋に保ち、I/O（`api/` `cache/`）と分離。
- **MCP ツールは3つ**：`search_cards` / `autocomplete_card_names` / `get_latest_expansion_set`。ツール関数は薄く、ロジックはサービス層へ。
- **多言語**：ロケールは `contextvars`（並行性セーフ）。日本語カード名は事前翻訳せず Scryfall のネイティブ多言語対応（`lang:` フィルタ＋ `include_multilingual`）を使う。
- **2層キャッシュ**：メモリ（L1・LRU）＋ Redis（L2・任意）。Redis 障害時はメモリで継続。TTL は Scryfall 推奨の最低24時間。
- **エラーハンドリング**：ステータス別（400/403/429/500+）・日英の実行可能なガイダンス。該当なしはエラーでなくメッセージ。設定不備はエラー＋MCP Resource（`scryfall://setup-guide`）で案内。
- カード表示仕様の正本：[docs/CARD-DISPLAY-SPEC.md](docs/CARD-DISPLAY-SPEC.md)。

## docs 索引（正本の対応）

- 開発環境・ワークフロー：[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)／テスト：[docs/TESTING-GUIDE.md](docs/TESTING-GUIDE.md)
- 設定・環境変数：[docs/CONFIGURATION.md](docs/CONFIGURATION.md)／API：[docs/API-REFERENCE.md](docs/API-REFERENCE.md)
- カード表示仕様：[docs/CARD-DISPLAY-SPEC.md](docs/CARD-DISPLAY-SPEC.md)／i18n：[docs/INTERNATIONALIZATION.md](docs/INTERNATIONALIZATION.md)
- Remote MCP デプロイ（AWS Lambda）：[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)（設計：[docs/REMOTE-MCP-IMPLEMENTATION-PLAN.md](docs/REMOTE-MCP-IMPLEMENTATION-PLAN.md)）

## 品質ゲート（コミット前に必ず通す）

```bash
uv run ruff check src/ tests/ --fix
uv run ruff format src/ tests/
uv run mypy src/
uv run pytest --cov=scryfall_mcp --cov-report=term-missing
```

## skill / サブエージェント（作業の重さで使い分ける）

- skill：`/test`（**haiku**・テスト実行と報告のみ）、`/qa`（**sonnet**・失敗を修正して通るまで）、`/commit`（**sonnet**・混入チェック込みの日本語コミット）、`/mcp-smoke`（**sonnet**・3ツールの実挙動を PASS/FAIL）。
- サブエージェント：`python-code-reviewer`（sonnet）＝コード差分の規約準拠レビュー（正本＝`.claude/rules/`）。`python-test-debugger`（sonnet）＝テスト失敗の分析・カバレッジ調査。`markdown-proofreader`（haiku）＝ドキュメントの文章品質・AI っぽさチェック。
- 実装の区切りでは `/qa` →（server.py / tools/ に触れたら）`/mcp-smoke` →（コード差分があれば）`python-code-reviewer` の順で自己検証してから完了報告する。

## 進め方（対話ルール）

- 設計・計画・ドキュメントだけを頼まれたら、承認前に実装コードを書かない（スコープ確認が先）。
- 成果物は**検証してから完了報告**（テストが通る・仕様に合うことを確認。「たぶん動く」で渡さない）。
- User-Agent 等の機密設定値をコード・ログ・ドキュメントにハードコードしない。

このドキュメントは設計決定の現状を反映するよう更新すること（作業履歴・タスクバックログは書かず、git / PR 履歴と GitHub Issues に残す）。
