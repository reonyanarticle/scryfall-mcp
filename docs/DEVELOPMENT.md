# 開発者ガイド

## 開発環境セットアップ

### 前提条件

- Python 3.11+
- uv (推奨) または pip
- Git

### 初期セットアップ

```bash
# リポジトリのクローン
git clone https://github.com/reonyanarticle/scryfall-mcp.git
cd scryfall-mcp

# 仮想環境と依存関係の構築
uv sync

# 開発ツールのインストール
uv add --dev ruff mypy pytest-cov

# pre-commitフックの設定（オプション）
uv run pre-commit install
```

## プロジェクト構造

```
scryfall-mcp/
├── src/scryfall_mcp/           # メインパッケージ
│   ├── __init__.py
│   ├── server.py               # MCPサーバーエントリポイント
│   ├── settings.py             # 設定管理・定数定義
│   ├── models.py               # データモデル・型定義（統合）
│   ├── api/                    # Scryfall APIクライアント
│   │   ├── client.py           # HTTPクライアント
│   │   └── rate_limiter.py     # レート制限とサーキットブレーカー
│   ├── cache/                  # キャッシュシステム
│   ├── i18n/                   # 国際化サポート
│   │   ├── locales.py          # ロケール管理
│   │   └── mappings/           # 言語マッピング
│   ├── search/                 # 検索エンジン
│   │   ├── builder.py          # クエリビルダー
│   │   └── processor.py        # 自然言語処理
│   └── tools/                  # MCPツール
│       └── search.py           # 検索ツール実装
├── tests/                      # テストスイート
├── docs/                       # ドキュメント
├── pyproject.toml             # プロジェクト設定
└── uv.lock                    # 依存関係ロック
```

## 開発ワークフロー

### 1. 機能開発

```bash
# フィーチャーブランチ作成
git checkout -b feature/new-feature

# 開発作業
# ...

# テスト実行
uv run pytest

# コード品質チェック
uv run ruff check src/ tests/
uv run mypy src/

# フォーマット
uv run ruff format src/ tests/
```

### 2. テスト

```bash
# 全テスト実行
uv run pytest

# カバレッジ付きテスト
uv run pytest --cov=scryfall_mcp --cov-report=html

# 特定テストファイル
uv run pytest tests/api/test_client.py -v

# テストの並列実行
uv run pytest -n auto
```

### 3. デバッグ

```bash
# デバッグモードでサーバー起動
SCRYFALL_MCP_DEBUG=true SCRYFALL_MCP_LOG_LEVEL=DEBUG uv run python -m scryfall_mcp

# プロファイリング
uv run python -m cProfile -o profile.stats -m scryfall_mcp
```

## コーディング規約

### Python スタイル

- **PEP 8** 準拠
- **型ヒント** 必須（Python 3.9+ native types使用）
- **docstring** 必須（NumPy style）
- **1関数1責任**
- **早期リターン** 推奨

### 型ヒントの例

```python
# ✅ 良い例（Python 3.9+ native types）
def search_cards(query: str, limit: int = 20) -> list[dict[str, Any]]:
    """カードを検索する。"""
    pass

# ❌ 悪い例（typing module）
from typing import List, Dict
def search_cards(query: str, limit: int = 20) -> List[Dict[str, Any]]:
    pass
```

### 命名規則

```python
# クラス: PascalCase
class ScryfallAPIClient:
    pass

# 関数・変数: snake_case
def search_cards():
    card_name = "Lightning Bolt"

# 定数: UPPER_SNAKE_CASE
MAX_SEARCH_RESULTS = 100

# プライベート: _prefix
def _internal_method():
    pass
```

## テスト方針

### テスト構造

```python
# tests/test_module.py
import pytest
from unittest.mock import Mock, AsyncMock

class TestClassName:
    """Test ClassName class."""

    @pytest.fixture
    def mock_client(self):
        """Create mock client."""
        return Mock()

    @pytest.mark.asyncio
    async def test_method_name(self, mock_client):
        """Test method behavior."""
        # Arrange
        expected = "result"

        # Act
        result = await some_async_function()

        # Assert
        assert result == expected
```

### モック戦略

```python
# Scryfall APIのモック
@pytest.fixture
def mock_scryfall_response():
    return {
        "object": "list",
        "data": [{"name": "Lightning Bolt"}]
    }

# 非同期クライアントのモック
@pytest.fixture
def mock_client():
    client = AsyncMock()
    client.search_cards.return_value = SearchResult(...)
    return client
```

## 新機能の追加

### 1. MCPツールの追加

```python
# src/scryfall_mcp/tools/new_tool.py
from mcp import Tool
from mcp.types import TextContent

class NewTool:
    @staticmethod
    def get_tool_definition() -> Tool:
        return Tool(
            name="new_tool",
            description="New tool description",
            inputSchema={"type": "object", "properties": {...}}
        )

    @staticmethod
    async def execute(arguments: dict[str, Any]) -> list[TextContent]:
        # Implementation
        pass
```

### 2. サーバーへの登録

```python
# src/scryfall_mcp/server.py
from .tools.new_tool import NewTool

SEARCH_TOOLS = [
    CardSearchTool,
    AutocompleteTool,
    NewTool,  # 追加
]
```

### 3. テストの追加

```python
# tests/tools/test_new_tool.py
class TestNewTool:
    def test_get_tool_definition(self):
        tool_def = NewTool.get_tool_definition()
        assert tool_def.name == "new_tool"

    @pytest.mark.asyncio
    async def test_execute(self):
        result = await NewTool.execute({"param": "value"})
        assert isinstance(result, list)
```

## パフォーマンス最適化

### 1. プロファイリング

```bash
# CPU プロファイリング
uv run python -m cProfile -o profile.stats main.py
uv run python -c "import pstats; pstats.Stats('profile.stats').sort_stats('cumulative').print_stats(20)"

# メモリプロファイリング
uv run python -m memory_profiler main.py
```

### 2. 非同期パフォーマンス

```python
# ✅ 並列実行
async def parallel_requests():
    tasks = [
        fetch_card(card_id)
        for card_id in card_ids
    ]
    results = await asyncio.gather(*tasks)
    return results

# ❌ 逐次実行
async def sequential_requests():
    results = []
    for card_id in card_ids:
        result = await fetch_card(card_id)
        results.append(result)
    return results
```

## デバッグ技法

### 1. ログの活用

```python
import logging

logger = logging.getLogger(__name__)

def search_function(query: str):
    logger.debug(f"Starting search with query: {query}")

    try:
        result = api_call(query)
        logger.info(f"Search completed: {len(result)} results")
        return result
    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        raise
```

### 2. デバッガーの使用

```python
# breakpoint() でデバッグポイント設定
def problematic_function():
    data = complex_calculation()
    breakpoint()  # ここで停止
    return process_data(data)
```

## リリースプロセス

### 1. バージョンアップ

```bash
# pyproject.tomlのversion更新
# CHANGELOG.mdの更新

# タグの作成
git tag v1.0.0
git push origin v1.0.0
```

### 2. CI/CDパイプライン

```yaml
# .github/workflows/test.yml
name: Test
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v1
      - run: uv sync
      - run: uv run pytest
      - run: uv run ruff check
      - run: uv run mypy src/
```

## 貢献ガイドライン

1. **Issue作成**: バグ報告や機能要求
2. **Fork & Branch**: feature/bugfix ブランチで開発
3. **テスト**: 新機能には必ずテストを追加
4. **コードレビュー**: PRにはレビューが必要
5. **ドキュメント**: 変更には関連ドキュメントも更新