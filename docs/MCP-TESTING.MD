# MCP Testing Guide

このドキュメントでは、Scryfall MCP ServerのMCP（Model Context Protocol）機能をテストする方法について説明します。

## 自動化テストスクリプト

### JSON-RPC直接テスト

最も信頼性の高いテスト方法です：

```bash
# MCP統合テストを実行
uv run python scripts/mcp_test.py
```

このスクリプトは以下をテストします：
- MCPプロトコルの初期化
- ツール一覧の取得
- 各ツールの呼び出し（autocomplete_card_names、search_cards）

### 全体テストスイート

プロジェクト全体のテストを実行：

```bash
# 全テストを実行（linting、type check、unit tests、MCP tests）
./scripts/run_tests.sh
```

## MCP Inspector を使用したテスト

### インストール

```bash
# Node.js 20+ が必要
npm install -g @modelcontextprotocol/inspector
```

### 基本的な使用方法

#### 1. ツール一覧の取得

```bash
npx -y @modelcontextprotocol/inspector --cli --transport stdio "./run_server.sh" --method tools/list
```

#### 2. インタラクティブ UI での検証

```bash
npx -y @modelcontextprotocol/inspector --transport stdio "./run_server.sh"
```

ブラウザでインタラクティブなUIが開き、以下が可能になります：
- ツールの詳細確認
- ツールの手動実行
- リアルタイムでの結果確認

## CI/CD 統合

GitHub Actions での自動テストが設定されています：

- **Unit Tests**: 既存の pytest ベースのテスト
- **MCP Integration Tests**: JSON-RPC 直接通信テスト
- **MCP Inspector Compatibility**: tools/list エンドポイントの検証
- **Security Checks**: bandit + safety による脆弱性チェック

## トラブルシューティング

### 一般的な問題

1. **"Connection closed" エラー**
   - サーバーが正しく初期化されているか確認
   - `initialized` 通知が送信されているか確認

2. **"Input validation error" エラー**
   - ツールの引数が正しい形式か確認
   - required パラメータが含まれているか確認

3. **timeout エラー**
   - ネットワーク接続を確認
   - Scryfall API のレート制限に達していないか確認

### デバッグ

詳細なログ出力でデバッグ：

```bash
LOG_LEVEL=DEBUG uv run python scripts/mcp_test.py
```

### 手動でのJSON-RPC通信テスト

```bash
# サーバー起動
uv run python -m scryfall_mcp

# 別ターミナルから
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0.0"}}}' | nc localhost 8080
```

## 対応済みのMCPプロトコル機能

- ✅ JSON-RPC 2.0 プロトコル
- ✅ stdio トランスポート
- ✅ initialize / initialized フロー
- ✅ tools/list メソッド
- ✅ tools/call メソッド
- ✅ 非同期ツール実行
- ✅ エラーハンドリング
- ✅ structured content 応答

## 制限事項

- HTTP/SSE トランスポートは未サポート
- リソース機能は未実装
- プロンプト機能は未実装