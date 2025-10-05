# Scryfall MCP Server

Magic: The Gatheringのカード情報をMCP (Model Context Protocol)経由でAIアシスタントに提供するサーバー。

## 概要

Scryfall MCP Serverは、Magic: The Gatheringのカード検索と情報取得をAIアシスタントから利用できるようにするMCPサーバーです。自然言語での検索（特に日本語サポート）、レート制限、エラーハンドリング、多言語対応などの機能を提供します。

## 主要機能

- **自然言語カード検索**: 日本語・英語での自然な検索クエリに対応
- **MCP準拠の構造化出力**: TextContent、EmbeddedResourceによる高品質なデータ提供
- **リアルタイム進捗報告**: FastMCP Context注入による詳細なログとプログレス通知
- **レート制限**: Scryfall API制限に準拠した安全なリクエスト管理（スレッドセーフ実装）
- **サーキットブレーカー**: 障害時の自動復旧機能
- **自動補完**: カード名の入力補助機能
- **高精度検索**: Scryfall検索構文への自動変換
- **Scryfall推奨キャッシュ**: 最低24時間のキャッシュTTLでAPI負荷を軽減

## クイックスタート

### 前提条件

- Python 3.11+
- uv (推奨) または pip
- Claude Desktop または MCP対応AIアシスタント

### インストール

```bash
# リポジトリのクローン
git clone https://github.com/reonyanarticle/scryfall-mcp.git
cd scryfall-mcp

# 依存関係のインストール
uv sync

# テストの実行
uv run pytest
```

### MCP サーバーとしての使用

#### 1. Claude Desktop での設定

Claude Desktop の設定ファイル (`claude_desktop_config.json`) に以下を追加してください。

**macOS/Linux**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "scryfall": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/scryfall-mcp",
        "run",
        "scryfall-mcp"
      ],
      "env": {
        "SCRYFALL_MCP_USER_AGENT": "YourApp/1.0 (your-email@example.com)"
      }
    }
  }
}
```

**重要**: `SCRYFALL_MCP_USER_AGENT`の設定が必要です。以下のいずれかの形式で連絡先情報を含めてください。
- メールアドレス: `YourApp/1.0 (yourname@example.com)`
- GitHubリポジトリ: `YourApp/1.0 (https://github.com/username/repo)`

設定せずに使用しようとすると、検索ツールが以下のセットアップガイドを表示します。

```
🔧 Scryfall API 初回セットアップ

Scryfall APIをご利用いただくには、以下の設定を行ってください：

1. Claude Desktop設定ファイルを開く
2. 以下の内容を追加
3. プレースホルダーを実際の値に置き換え
4. Claude Desktopを再起動

詳細情報: https://scryfall.com/docs/api
```

**設定後**: Claude Desktopを再起動してください。

#### 2. 利用可能なツール

Claude Desktop で以下のツールが利用可能になります:

**search_cards**
- カード検索（日本語・英語対応）
- 自然言語クエリからScryfall構文への自動変換
- 最大175件の結果を取得

**autocomplete_card_names**
- カード名の入力補完
- 部分一致検索
- 多言語対応

#### 3. 使用例

Claude Desktop で以下のように質問できます。

```
# 日本語での検索
「赤いクリーチャーを検索して」
「稲妻のカード情報を教えて」

# 英語での検索
"Search for blue counterspells"
"Find Lightning Bolt card details"

# 自動補完
「Light で始まるカード名を教えて」
```

### スタンドアロンでの使用

```bash
# MCPサーバーの起動（stdio mode）
uv run scryfall-mcp

# または開発モードで起動
SCRYFALL_MCP_DEBUG=true SCRYFALL_MCP_LOG_LEVEL=DEBUG uv run scryfall-mcp
```

## 📖 使用例

### カード検索

```python
# 基本的な検索
search_cards(query="Lightning Bolt")

# 日本語での検索
search_cards(query="白いクリーチャー", language="ja")

# フォーマット指定検索
search_cards(query="青いカウンター", format_filter="standard")
```

### 自動補完

```python
# カード名の補完
autocomplete_card_names(query="Light")
# -> ["Lightning Bolt", "Lightning Strike", "Lightning Helix"]
```

## 🏗️ アーキテクチャ

```
scryfall-mcp/
├── src/scryfall_mcp/
│   ├── api/              # Scryfall API クライアント
│   │   ├── client.py     # HTTPクライアント実装
│   │   └── rate_limiter.py # レート制限・サーキットブレーカー
│   ├── cache/            # 2層キャッシュシステム
│   │   ├── backends.py   # Memory/Redis/Composite
│   │   └── manager.py    # キャッシュマネージャー
│   ├── i18n/             # 国際化・多言語対応
│   │   ├── constants.py  # 静的語彙データ (NEW)
│   │   ├── locales.py    # ロケール管理
│   │   └── mappings/     # 言語マッピング
│   ├── search/           # 検索パイプライン
│   │   ├── parser.py     # 自然言語解析
│   │   ├── builder.py    # クエリ構築
│   │   └── presenter.py  # MCP出力フォーマット
│   ├── tools/            # MCPツール実装
│   │   └── search.py     # 検索ツール
│   ├── server.py         # MCPサーバーエントリポイント
│   ├── settings.py       # 実行時設定管理
│   └── models.py         # データモデル・型定義
├── tests/                # テストスイート (389 tests, 95% coverage)
├── docs/                 # ドキュメント
└── AGENT.md              # AI開発者向けガイド
```

### 主要コンポーネント

- **API Client**: レート制限・リトライ・サーキットブレーカー搭載（asyncio.Lockによるスレッドセーフ実装）
- **Cache System**: L1 (Memory) + L2 (Redis) の2層キャッシュ（24時間TTL、Scryfall推奨値準拠）
- **Search Pipeline**: Parser → Builder → Presenter の責務分離
- **i18n System**: contextvarsベースの並行安全なロケール管理
- **MCP Tools**: 構造化レスポンス対応の検索・補完ツール（Context注入による進捗報告機能付き）
- **Lifecycle Management**: asynccontextmanagerベースの起動・シャットダウン処理

## 設定

環境変数で動作をカスタマイズできます：

```bash
# User-Agent設定（必須）
SCRYFALL_MCP_USER_AGENT="YourApp/1.0 (your-email@example.com)"

# レート制限設定
SCRYFALL_MCP_RATE_LIMIT_MS=100

# 言語設定
SCRYFALL_MCP_DEFAULT_LOCALE=ja

# キャッシュ設定（Scryfall推奨: 最低24時間）
SCRYFALL_MCP_CACHE_ENABLED=true
SCRYFALL_MCP_CACHE_BACKEND=memory
SCRYFALL_MCP_CACHE_TTL_SEARCH=86400  # 24時間（秒）
SCRYFALL_MCP_CACHE_TTL_DEFAULT=86400 # 24時間（秒）
```

詳細は [設定ガイド](docs/CONFIGURATION.md) を参照してください。

## 開発

### テスト実行

```bash
# 全テスト実行（389テスト）
uv run pytest

# カバレッジ付きテスト
uv run pytest --cov=scryfall_mcp

# MCP統合テスト（Content構造検証）
uv run pytest tests/integration/test_mcp_content_validation.py -v

# 特定テストのみ
uv run pytest tests/api/test_client.py -v
```

### コード品質チェック

```bash
# リント
uv run ruff check src/ tests/

# フォーマット
uv run ruff format src/ tests/

# 型チェック
uv run mypy src/
```

### CI/CD

GitHub Actionsで以下のチェックを自動実行。

**テストスイート**:
- Python 3.11, 3.12マトリックステスト
- 389テスト、95%カバレッジ
- MCP統合テスト（stdio transport）
- MCP Inspector互換性テスト

**品質チェック**:
- Ruff linter（全コード）
- Mypy strict mode type check
- Bandit + Safety セキュリティスキャン

**環境変数**: CIでは`SCRYFALL_MCP_USER_AGENT`を設定必須。
```bash
export SCRYFALL_MCP_USER_AGENT="GitHub-Actions-CI/1.0 (github-actions@github.com)"
```

## MCP仕様準拠

このサーバーは[Model Context Protocol仕様](https://modelcontextprotocol.io/)に完全準拠しています：

### プロトコル対応
- **MCPバージョン**: 2024-11-05
- **通信方式**: stdio (標準入出力)
- **コンテンツタイプ**: TextContent、EmbeddedResource
- **ライフサイクル管理**: asynccontextmanagerベースの起動・シャットダウン

### 構造化レスポンス
- カード情報を`EmbeddedResource`として構造化
- カスタムURIスキーマ: `card://scryfall/{id}`
- 画像URLをテキストとして提供（MCP仕様準拠のため）
- エラーメッセージを多言語対応の`TextContent`として返却

### 観測可能性
- FastMCP Context注入による進捗報告
- `ctx.info()`: 詳細ログ出力
- `ctx.report_progress()`: リアルタイム進捗通知
- `ctx.error()`: エラーログ記録

詳細な実装については [AI開発者ガイド](AGENT.md) を参照してください。

## ドキュメント

- [コントリビューションガイド](docs/CONTRIBUTING.md) - PR受け付けルール・コーディング規約
- [API仕様書](docs/API-REFERENCE.md) - MCPツール詳細仕様
- [多言語対応ガイド](docs/INTERNATIONALIZATION.md) - i18n実装詳細
- [開発者ガイド](docs/DEVELOPMENT.md) - 開発環境・コーディング規約
- [設定ガイド](docs/CONFIGURATION.md) - 環境変数・設定項目
- [MCPテストガイド](docs/MCP-TESTING.md) - MCP統合テスト方法
- [AI開発者ガイド](AGENT.md) - 設計思想・技術的制約

## コントリビューション

Scryfall MCP Serverへのコントリビューションを歓迎します。

### クイックスタート

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### 詳細ガイド

プルリクエストの受け付けルール、コーディング規約、テスト要件などの詳細は [コントリビューションガイドライン](docs/CONTRIBUTING.md) を参照してください。

**重要な要件**:
- 全テスト合格 (389 tests, 95% coverage)
- 型チェック (`mypy`) 合格
- リント (`ruff`) 合格
- NumPy styleのdocstring必須
- カバレッジ90%以上

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。詳細は [LICENSE](LICENSE) ファイルを参照してください。

## 謝辞

- [Scryfall](https://scryfall.com/) - Magic: The Gathering データAPI
- [Model Context Protocol](https://modelcontextprotocol.io/) - AIアシスタント統合プロトコル

## サポート

- Issues: [GitHub Issues](https://github.com/reonyanarticle/scryfall-mcp/issues)
- Discussions: [GitHub Discussions](https://github.com/reonyanarticle/scryfall-mcp/discussions)

---

*Magic: The Gathering is a trademark of Wizards of the Coast LLC.*