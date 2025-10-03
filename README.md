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

### 基本的な使用方法

```bash
# MCPサーバーの起動
uv run python -m scryfall_mcp

# Claude等のAIアシスタントから以下のツールが利用可能:
# - search_cards: カード検索
# - autocomplete_card_names: カード名補完
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
│   ├── cache/            # キャッシュシステム
│   ├── i18n/             # 国際化・多言語対応
│   ├── search/           # 検索クエリ処理
│   ├── tools/            # MCPツール実装
│   ├── server.py         # MCPサーバーメイン
│   ├── settings.py       # 設定管理・定数定義
│   └── models.py         # データモデル・型定義
├── tests/                # テストスイート
└── docs/                 # ドキュメント
```

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

- [API仕様書](docs/API-REFERENCE.md)
- [多言語対応ガイド](docs/INTERNATIONALIZATION.md)
- [開発者ガイド](docs/DEVELOPMENT.md)
- [設定ガイド](docs/CONFIGURATION.md)

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