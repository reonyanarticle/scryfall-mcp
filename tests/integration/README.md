# 結合テスト (Integration Tests)

Scryfall MCP Serverの結合テストスイートです。

## 概要

このディレクトリには、MCPプロトコル経由でサーバー全体の動作を検証する結合テストが含まれています。

## テストファイル

### test_e2e_query_pipeline.py
クエリ処理パイプライン全体のエンドツーエンドテストです。

- Parser → Builder → Processor → Presenterの全体フロー検証
- 日本語キーワード能力検索のテスト（Issue #2実装の検証）
- 英語・日本語両方のクエリ変換テスト
- 複雑度評価、ロケール切り替えのテスト

```bash
uv run pytest tests/integration/test_e2e_query_pipeline.py -v
```

**テスト対象**:
- 日本語キーワード能力検索（飛行、接死、速攻など）
- 複雑な日本語クエリ（複数条件、マナ総量、レアリティなど）
- 英語クエリの変換
- ロケール切り替え
- 空クエリの処理
- クエリ複雑度評価

### test_mcp_connection.py
MCPプロトコルの基本的な接続をテストします。

- サーバーの初期化
- プロトコルバージョンの確認
- サーバー情報の取得
- サーバー機能の確認

```bash
uv run python tests/integration/test_mcp_connection.py
```

### test_mcp_tools_list.py
利用可能なツールの一覧取得をテストします。

- ツールリストの取得
- 各ツールのメタデータ確認
- 入力スキーマの検証

```bash
uv run python tests/integration/test_mcp_tools_list.py
```

### test_mcp_tool_call.py
MCPプロトコル経由での実際のツール呼び出しをテストします。

- search_cardsツールの呼び出し
- autocomplete_card_namesツールの呼び出し
- 英語・日本語両方での検索
- レスポンス形式の検証

```bash
uv run python tests/integration/test_mcp_tool_call.py
```

### test_mcp_tools.py
サーバー内部のツール実装を直接テストします。

- 実際のScryfall API呼び出しを含む
- 多言語対応の検証
- 自然言語クエリの変換確認
- エラーハンドリングの検証

```bash
uv run python tests/integration/test_mcp_tools.py
```

## 実行方法

### 全テストの実行

```bash
# すべての結合テストを実行
uv run pytest tests/integration/ -v

# 特定のテストファイルを実行
uv run pytest tests/integration/test_mcp_connection.py -v
```

### 個別実行

各テストファイルは単独で実行可能です:

```bash
uv run python tests/integration/test_mcp_connection.py
uv run python tests/integration/test_mcp_tools_list.py
uv run python tests/integration/test_mcp_tool_call.py
uv run python tests/integration/test_mcp_tools.py
```

## 注意事項

### API呼び出し

一部のテストは実際のScryfall APIを呼び出します:
- `test_mcp_tools.py`: 実際のAPI呼び出しあり
- `test_mcp_tool_call.py`: 実際のAPI呼び出しあり

レート制限（100ms間隔）に注意してください。

### 環境変数

必要に応じて以下の環境変数を設定できます:

```bash
# ログレベル
export LOG_LEVEL=DEBUG

# デフォルト言語
export SCRYFALL_MCP_DEFAULT_LOCALE=ja

# キャッシュ設定
export CACHE_ENABLED=true
export CACHE_BACKEND=memory
```

## CI/CDでの実行

GitHub Actionsなどで実行する場合:

```yaml
- name: Run Integration Tests
  run: |
    uv run python tests/integration/test_mcp_connection.py
    uv run python tests/integration/test_mcp_tools_list.py
    # API呼び出しを含むテストは適宜制限
```

## トラブルシューティング

### タイムアウトエラー

長時間実行される場合、タイムアウト値を増やしてください:

```python
proc = subprocess.Popen(..., timeout=30)
```

### API制限エラー

Scryfall APIのレート制限に達した場合:
1. テスト間隔を空ける
2. キャッシュを有効化
3. モックを使用

### プロトコルエラー

MCPプロトコルのバージョン不一致の場合:
1. fastmcpのバージョン確認
2. プロトコルバージョンの更新
3. リクエスト形式の確認

## 参考資料

- [MCP Testing Guide](../docs/MCP-TESTING.md) - 詳細なテストガイド
- [MCP Specification](https://modelcontextprotocol.io/)
- [Scryfall API Docs](https://scryfall.com/docs/api)
