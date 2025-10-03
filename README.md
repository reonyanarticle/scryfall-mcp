# Scryfall MCP Server

Magic: The Gatheringのカード情報をMCP (Model Context Protocol)経由でAIアシスタントに提供するサーバー。

## 概要

Scryfall MCP Serverは、Magic: The Gatheringのカード検索と情報取得をAIアシスタントから利用できるようにするMCPサーバーです。自然言語での検索（特に日本語サポート）、レート制限、エラーハンドリング、多言語対応などの機能を提供します。

## 主要機能

- **自然言語カード検索**: 日本語・英語での自然な検索クエリに対応
- **レート制限**: Scryfall API制限に準拠した安全なリクエスト管理
- **サーキットブレーカー**: 障害時の自動復旧機能
- **自動補完**: カード名の入力補助機能
- **高精度検索**: Scryfall検索構文への自動変換

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

Claude Desktop の設定ファイル (`claude_desktop_config.json`) に以下を追加:

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
      ]
    }
  }
}
```

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

Claude Desktop で以下のように質問できます:

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
├── tests/                # テストスイート (360 tests)
├── docs/                 # ドキュメント
└── AGENT.md              # AI開発者向けガイド
```

### 主要コンポーネント

- **API Client**: レート制限・リトライ・サーキットブレーカー搭載
- **Cache System**: L1 (Memory) + L2 (Redis) の2層キャッシュ
- **Search Pipeline**: Parser → Builder → Presenter の責務分離
- **i18n System**: contextvarsベースの並行安全なロケール管理
- **MCP Tools**: 構造化レスポンス対応の検索・補完ツール

## 設定

環境変数または設定ファイルで動作をカスタマイズできます：

```bash
# レート制限設定
SCRYFALL_MCP_RATE_LIMIT_MS=100

# 言語設定
SCRYFALL_MCP_DEFAULT_LOCALE=ja

# キャッシュ設定
SCRYFALL_MCP_CACHE_ENABLED=true
SCRYFALL_MCP_CACHE_BACKEND=memory
```

詳細は [設定ガイド](docs/CONFIGURATION.md) を参照してください。

## 開発

### テスト実行

```bash
# 全テスト実行
uv run pytest

# カバレッジ付きテスト
uv run pytest --cov=scryfall_mcp

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

## ドキュメント

- [API仕様書](docs/API-REFERENCE.md) - MCPツール詳細仕様
- [多言語対応ガイド](docs/INTERNATIONALIZATION.md) - i18n実装詳細
- [開発者ガイド](docs/DEVELOPMENT.md) - 開発環境・コーディング規約
- [設定ガイド](docs/CONFIGURATION.md) - 環境変数・設定項目
- [MCPテストガイド](docs/MCP-TESTING.md) - MCP統合テスト方法
- [AI開発者ガイド](AGENT.md) - 設計思想・技術的制約

## コントリビューション

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

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