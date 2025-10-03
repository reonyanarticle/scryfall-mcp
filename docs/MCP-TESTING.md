# MCPテストガイド

Scryfall MCP Serverのテスト方法を説明します。

## 前提条件

- Node.js/npm がインストールされていること
- uvがインストールされていること
- プロジェクト依存関係がインストールされていること（`uv sync`）

## テスト方法

### 1. 基本的な動作確認

MCPサーバーが正常に起動することを確認:

```bash
uv run scryfall-mcp
```

起動すると、FastMCPのバナーが表示されます。

### 2. ツールの統合テスト

提供されているPythonスクリプトで、実際のAPI呼び出しを含むテストを実行:

```bash
uv run python tests/integration/test_mcp_tools.py
```

このテストは以下を確認します:
- 英語でのカード検索 ("Lightning Bolt")
- 日本語でのカード検索 ("稲妻")
- オートコンプリート機能
- 自然言語クエリの処理

### 3. MCPプロトコルのテスト

#### 3.1 接続テスト

MCPプロトコルでサーバーが正しく応答することを確認:

```bash
uv run python tests/integration/test_mcp_connection.py
```

期待される出力:
- Protocol version: 2024-11-05
- Server name: scryfall-mcp
- Server capabilities (tools, prompts, resources)

が表示されます。

#### 3.2 ツール一覧の取得

利用可能なツールの一覧を取得:

```bash
uv run python tests/integration/test_mcp_tools_list.py
```

期待される出力:
- `search_cards`: カード検索ツール
- `autocomplete_card_names`: カード名の自動補完

が表示されます。

#### 3.3 ツール呼び出しテスト

MCPプロトコル経由で実際にツールを呼び出す:

```bash
uv run python tests/integration/test_mcp_tool_call.py
```

各ツールが正常に動作し、適切なレスポンスを返すことを確認します。

### 4. MCPインスペクターの使用

#### 4.1 インスペクターのインストール

```bash
npm install -g @modelcontextprotocol/inspector
```

#### 4.2 設定ファイルを使った起動

プロジェクトには`.mcp.json`設定ファイルが用意されています:

```bash
npx @modelcontextprotocol/inspector --config .mcp.json --server scryfall
```

または、提供されているスクリプトを使用:

```bash
chmod +x run_mcp_inspector.sh
./run_mcp_inspector.sh
```

#### 4.3 CLIモードでの起動

インタラクティブにテストする場合:

```bash
npx @modelcontextprotocol/inspector --cli --transport stdio uv run scryfall-mcp
```

これにより、ブラウザでインスペクターUIが開き、以下の操作が可能になります:
- ツール一覧の表示
- ツールの呼び出し
- レスポンスの確認
- デバッグ情報の表示

## テストケース

### 英語検索

```json
{
  "name": "search_cards",
  "arguments": {
    "query": "Lightning Bolt",
    "language": "en",
    "max_results": 5
  }
}
```

### 日本語検索

```json
{
  "name": "search_cards",
  "arguments": {
    "query": "稲妻",
    "language": "ja",
    "max_results": 5
  }
}
```

### 自然言語クエリ（日本語）

```json
{
  "name": "search_cards",
  "arguments": {
    "query": "赤いクリーチャー",
    "language": "ja",
    "max_results": 10
  }
}
```

期待される動作: `c:r t:creature lang:ja` に変換されて検索されます。

### オートコンプリート

```json
{
  "name": "autocomplete_card_names",
  "arguments": {
    "query": "Light",
    "language": "en"
  }
}
```

## トラブルシューティング

### サーバーが起動しない

1. 依存関係を確認: `uv sync`
2. ログレベルを変更: `LOG_LEVEL=DEBUG uv run scryfall-mcp`

### MCPプロトコルエラー

1. プロトコルバージョンの確認
2. リクエストのJSON形式を確認
3. 必須パラメータの確認

### API エラー

1. ネットワーク接続を確認してください
2. Scryfall APIの状態を確認してください: https://scryfall.com/docs/api
3. レート制限に注意してください（100ms間隔）

## テスト結果の確認

すべてのテストが成功すると、以下が確認できます。

✓ MCPプロトコルでの通信が正常に動作する
✓ 2つのツール（search_cards, autocomplete_card_names）が利用可能である
✓ 英語・日本語両方のカード検索が動作する
✓ 自然言語クエリがScryfallクエリに正しく変換される
✓ 日本語カード名がネイティブサポートで検索可能である（lang:パラメータ自動追加）
✓ オートコンプリート機能が動作する

## CI/CDでのテスト

GitHub Actionsなどで自動テストを実行する場合:

```yaml
- name: Test MCP Protocol
  run: |
    uv run python tests/integration/test_mcp_connection.py
    uv run python tests/integration/test_mcp_tools_list.py
    uv run python tests/integration/test_mcp_tool_call.py
```

## 参考資料

- [MCP Specification](https://modelcontextprotocol.io/)
- [Scryfall API Documentation](https://scryfall.com/docs/api)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
