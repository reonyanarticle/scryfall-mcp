# Testing Guide

Scryfall MCP Serverの包括的なテストガイド。ローカル開発からAWS Lambdaデプロイ後のテストまで、すべてのシナリオをカバーします。

## 目次

1. [ローカル開発でのテスト](#ローカル開発でのテスト)
2. [認証テスト](#認証テスト)
3. [AWS Lambda デプロイ後のテスト](#aws-lambda-デプロイ後のテスト)
4. [MCP Inspector使用方法](#mcp-inspector使用方法)
5. [自動テスト実行](#自動テスト実行)
6. [トラブルシューティング](#トラブルシューティング)
7. [ベストプラクティス](#ベストプラクティス)

---

## ローカル開発でのテスト

### 1. stdio transport (Claude Desktop統合)

Claude DesktopでローカルのMCPサーバーをテストする標準的な方法です。

#### セットアップ

**Claude Desktop設定ファイルを編集:**

```bash
# macOS/Linux
code ~/Library/Application\ Support/Claude/claude_desktop_config.json

# Windows
code %APPDATA%\Claude\claude_desktop_config.json
```

**設定例:**

```json
{
  "mcpServers": {
    "scryfall": {
      "command": "uv",
      "args": [
        "--directory",
        "/Users/tomoya/scryfall-mcp",
        "run",
        "scryfall-mcp"
      ],
      "env": {
        "SCRYFALL_MCP_USER_AGENT": "ScryfallMCP/0.1.0 (your-email@example.com)",
        "SCRYFALL_MCP_LOG_LEVEL": "DEBUG",
        "SCRYFALL_MCP_CACHE_BACKEND": "memory"
      }
    }
  }
}
```

**重要な環境変数:**

| 変数名 | 必須 | 説明 | デフォルト |
|--------|------|------|-----------|
| `SCRYFALL_MCP_USER_AGENT` | ✅ | Scryfall API連絡先 | - |
| `SCRYFALL_MCP_LOG_LEVEL` | ❌ | ログレベル（DEBUG/INFO/WARNING/ERROR） | INFO |
| `SCRYFALL_MCP_CACHE_BACKEND` | ❌ | キャッシュバックエンド（memory/redis） | memory |
| `SCRYFALL_MCP_TRANSPORT_MODE` | ❌ | Transportモード（stdio） | stdio |

#### 動作確認

1. **Claude Desktopを再起動**
   ```bash
   # macOS
   killall Claude && open -a Claude
   ```

2. **MCPサーバー接続確認**
   - Claude Desktopのチャット画面下部にMCPアイコン（工具マーク）が表示される
   - アイコンをクリックして「scryfall」サーバーが接続済みと表示される

3. **ツール呼び出しテスト**
   ```
   User: Search for "Lightning Bolt" in Magic cards
   Claude: [search_cards ツールを呼び出し]
   ```

4. **ログ確認**
   ```bash
   # Claude Desktop Logs (macOS)
   tail -f ~/Library/Logs/Claude/mcp*.log

   # サーバーログ (stderr)
   # Claude Desktopのログに含まれる
   ```

#### トラブルシューティング

**接続失敗:**
```bash
# 設定ファイル構文チェック
python -m json.tool ~/Library/Application\ Support/Claude/claude_desktop_config.json

# uvコマンドパス確認
which uv

# 手動起動テスト
cd /Users/tomoya/scryfall-mcp
uv run scryfall-mcp
```

**User-Agent未設定エラー:**
```
❌ User-Agent が設定されていません
```

**解決:** 環境変数を設定してClaude Desktopを再起動

---

### 2. Streamable HTTP transport (Remote MCP)

HTTP経由でMCPサーバーをテストする開発モード。

#### ローカルサーバー起動

```bash
# 環境変数設定
export SCRYFALL_MCP_TRANSPORT_MODE=streamable_http
export SCRYFALL_MCP_HTTP_HOST=0.0.0.0
export SCRYFALL_MCP_HTTP_PORT=8000
export SCRYFALL_MCP_USER_AGENT="ScryfallMCP/0.1.0 (your-email@example.com)"
export SCRYFALL_MCP_LOG_LEVEL=DEBUG

# サーバー起動
uv run scryfall-mcp
```

**期待される出力:**

```text
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:scryfall_mcp.server:Detected and set locale: en
INFO:scryfall_mcp.server:Supported locales: ['en', 'ja']
INFO:scryfall_mcp.server:Starting Scryfall MCP Server (fastmcp)
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

#### 動作確認

**1. ヘルスチェック:**

```bash
curl http://localhost:8000/
```

**期待される応答:**
```json
{
  "name": "scryfall-mcp",
  "version": "0.1.0"
}
```

**2. MCP tools/list リクエスト:**

```bash
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/list",
    "id": 1
  }'
```

**期待される応答:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "tools": [
      {
        "name": "search_cards",
        "description": "Search for Magic: The Gathering cards",
        "inputSchema": {...}
      },
      {
        "name": "autocomplete",
        "description": "Autocomplete card names",
        "inputSchema": {...}
      }
    ]
  }
}
```

**3. カード検索テスト:**

```bash
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "search_cards",
      "arguments": {
        "query": "Lightning Bolt",
        "max_results": 1
      }
    },
    "id": 2
  }'
```

---

## 認証テスト

### Email認証のテスト

#### 1. ローカルでのEmail認証設定

**環境変数:**

```bash
export SCRYFALL_MCP_EMAIL_AUTH_ENABLED=true
export SCRYFALL_MCP_EMAIL_AUTH_CREDENTIALS='{
  "user1@example.com": "$2b$12$...",
  "user2@example.com": "$2b$12$..."
}'
```

**認証情報の生成:**

```python
from scryfall_mcp.auth.email import hash_secret

# シークレットをハッシュ化
hashed = hash_secret("my-secure-password")
print(hashed)  # $2b$12$...
```

**JSON形式:**

```json
{
  "user1@example.com": "$2b$12$KIXqZ9vL...",
  "user2@example.com": "$2b$12$A7bQR3mP..."
}
```

#### 2. Basic認証テスト

```bash
# Base64エンコード: user1@example.com:my-secure-password
echo -n "user1@example.com:my-secure-password" | base64
# 出力: dXNlcjFAZXhhbXBsZS5jb206bXktc2VjdXJlLXBhc3N3b3Jk

# 認証付きリクエスト
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Authorization: Basic dXNlcjFAZXhhbXBsZS5jb206bXktc2VjdXJlLXBhc3N3b3Jk" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/list",
    "id": 1
  }'
```

**認証失敗テスト:**

```bash
# 誤ったパスワード
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Authorization: Basic dXNlcjFAZXhhbXBsZS5jb206d3JvbmctcGFzc3dvcmQ=" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/list",
    "id": 1
  }'
```

**期待される応答:**
```json
{
  "error": {
    "code": 401,
    "message": "Invalid credentials"
  }
}
```

#### 3. レート制限テスト

```bash
# 100回連続でリクエスト（ユーザー別レート制限: 100 req/min）
for i in {1..101}; do
  echo "Request $i"
  curl -X POST http://localhost:8000/mcp \
    -H "Authorization: Basic dXNlcjFAZXhhbXBsZS5jb206bXktc2VjdXJlLXBhc3N3b3Jk" \
    -H "Content-Type: application/json" \
    -d '{"jsonrpc": "2.0", "method": "tools/list", "id": '$i'}'
  echo ""
done
```

**101回目のリクエストで期待される応答:**

```json
{
  "error": {
    "code": 429,
    "message": "Rate limit exceeded: 100 requests per minute"
  }
}
```

---

### JWT認証のテスト

#### 1. JWT Secret生成

```bash
# 32文字以上のランダム文字列を生成
python -c "import secrets; print(secrets.token_urlsafe(32))"
# 出力例: 8y7Js9Kp2Lm4Nq5Rt6Vw8Xz0Ab1Cd3Ef5Gh7Ij9Kl
```

#### 2. JWTトークン生成（テスト用）

```python
from jose import jwt
import time

# 設定
SECRET_KEY = "8y7Js9Kp2Lm4Nq5Rt6Vw8Xz0Ab1Cd3Ef5Gh7Ij9Kl"
ALGORITHM = "HS256"

# ペイロード
payload = {
    "sub": "user123",           # ユーザーID
    "iat": int(time.time()),     # 発行時刻
    "exp": int(time.time()) + 3600,  # 有効期限（1時間）
    "nbf": int(time.time())      # 有効開始時刻
}

# トークン生成
token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
print(token)
```

#### 3. JWT検証テスト

```bash
# 環境変数設定
export SCRYFALL_MCP_OAUTH_ENABLED=true
export SCRYFALL_MCP_JWT_SECRET_KEY="8y7Js9Kp2Lm4Nq5Rt6Vw8Xz0Ab1Cd3Ef5Gh7Ij9Kl"
export SCRYFALL_MCP_JWT_ALGORITHM=HS256

# サーバー起動
uv run scryfall-mcp
```

**有効なJWTでリクエスト:**

```bash
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/list",
    "id": 1
  }'
```

**無効なJWTでリクエスト:**

```bash
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer invalid-token" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/list",
    "id": 1
  }'
```

**期待される応答:**
```json
{
  "error": {
    "code": 401,
    "message": "Invalid token: Signature verification failed"
  }
}
```

---

## AWS Lambda デプロイ後のテスト

### 1. デプロイ確認

```bash
cd deploy/aws

# デプロイ情報確認
npx serverless info --stage dev
```

**出力例:**

```text
Service Information
service: scryfall-mcp
stage: dev
region: us-east-1
stack: scryfall-mcp-dev
api endpoint: https://abc123.execute-api.us-east-1.amazonaws.com
functions:
  mcp: scryfall-mcp-dev-mcp
```

### 2. API Gateway endpoint テスト

#### ヘルスチェック

```bash
ENDPOINT="https://abc123.execute-api.us-east-1.amazonaws.com"

curl $ENDPOINT/mcp
```

**期待される応答:**

```json
{
  "name": "scryfall-mcp",
  "version": "0.1.0"
}
```

#### MCP tools/list

```bash
curl -X POST $ENDPOINT/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/list",
    "id": 1
  }'
```

### 3. Email認証テスト（Lambda）

#### SSM Parameter Storeに認証情報を設定

```bash
# 認証情報JSON作成
cat > /tmp/email_creds.json <<EOF
{
  "user@example.com": "\$2b\$12\$KIXqZ9vL..."
}
EOF

# SSMに保存
aws ssm put-parameter \
  --name "/scryfall-mcp/dev/EMAIL_AUTH_CREDENTIALS" \
  --type "SecureString" \
  --value "$(cat /tmp/email_creds.json)" \
  --overwrite

# 削除
rm /tmp/email_creds.json
```

#### 認証付きリクエスト

```bash
# Basic認証ヘッダー生成
AUTH=$(echo -n "user@example.com:my-password" | base64)

curl -X POST $ENDPOINT/mcp \
  -H "Content-Type: application/json" \
  -H "Authorization: Basic $AUTH" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "search_cards",
      "arguments": {"query": "Lightning Bolt"}
    },
    "id": 2
  }'
```

### 4. JWT認証テスト（Lambda）

#### JWT Secret設定（SSM Parameter Store）

```bash
# Secret生成
JWT_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(32))")

# SSMに保存
aws ssm put-parameter \
  --name "/scryfall-mcp/dev/JWT_SECRET_KEY" \
  --type "SecureString" \
  --value "$JWT_SECRET" \
  --overwrite
```

#### JWT生成とテスト

```python
# generate_jwt.py
from jose import jwt
import time
import sys

SECRET_KEY = sys.argv[1]  # SSMから取得したsecret
ALGORITHM = "HS256"

payload = {
    "sub": "test_user",
    "iat": int(time.time()),
    "exp": int(time.time()) + 3600,
    "nbf": int(time.time())
}

token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
print(token)
```

```bash
# JWT生成
JWT_SECRET=$(aws ssm get-parameter --name "/scryfall-mcp/dev/JWT_SECRET_KEY" --with-decryption --query "Parameter.Value" --output text)
TOKEN=$(python generate_jwt.py "$JWT_SECRET")

# リクエスト
curl -X POST $ENDPOINT/mcp \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "search_cards",
      "arguments": {"query": "Black Lotus"}
    },
    "id": 3
  }'
```

### 5. レート制限検証

#### Scryfall APIレート制限（グローバル）

```bash
# 秒間10リクエスト以上送信してテスト
for i in {1..15}; do
  echo "Request $i"
  curl -X POST $ENDPOINT/mcp \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "search_cards", "arguments": {"query": "Forest"}}, "id": '$i'}'
  echo ""
done
```

**期待される動作:**

- 1-10回目: 正常応答
- 11回目以降: 75-100ms間隔で自動レート制限（サーバー側）

#### ユーザー別レート制限

```bash
# ユーザー別制限: 100 req/min
# 101回のリクエストを1分以内に送信
for i in {1..101}; do
  curl -s -X POST $ENDPOINT/mcp \
    -H "Authorization: Basic $AUTH" \
    -H "Content-Type: application/json" \
    -d '{"jsonrpc": "2.0", "method": "tools/list", "id": '$i'}' \
    | jq -r '.error.message // "OK"'
done
```

**期待される出力:**

```text
OK
OK
...
OK (100回)
Rate limit exceeded: 100 requests per minute
```

### 6. CloudWatch Logs確認

```bash
# 最新のログストリーム確認
aws logs tail /aws/lambda/scryfall-mcp-dev-mcp --follow

# エラーログのみフィルタ
aws logs filter-log-events \
  --log-group-name /aws/lambda/scryfall-mcp-dev-mcp \
  --filter-pattern "ERROR" \
  --start-time $(date -u -d '5 minutes ago' +%s)000
```

### 7. Lambda Metrics確認

```bash
# 関数メトリクス取得
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=scryfall-mcp-dev-mcp \
  --start-time $(date -u -d '1 hour ago' --iso-8601=seconds) \
  --end-time $(date -u --iso-8601=seconds) \
  --period 300 \
  --statistics Sum

# エラー率確認
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value=scryfall-mcp-dev-mcp \
  --start-time $(date -u -d '1 hour ago' --iso-8601=seconds) \
  --end-time $(date -u --iso-8601=seconds) \
  --period 300 \
  --statistics Sum
```

---

## MCP Inspector使用方法

MCP Inspectorは、MCP Protocolの開発・デバッグに特化したGUIツールです。

### インストール

```bash
npm install -g @modelcontextprotocol/inspector
```

### stdio接続（ローカルサーバー）

```bash
# MCP Inspector起動
npx @modelcontextprotocol/inspector uv \
  --directory /Users/tomoya/scryfall-mcp \
  run scryfall-mcp
```

**ブラウザが自動的に開きます:**
- URL: `http://localhost:5173`
- サーバー接続確認: 左側にサーバー情報が表示される
- ツール一覧: `search_cards`, `autocomplete` が表示される

### HTTP接続（Remote MCP）

#### ローカルサーバー

```bash
# ターミナル1: サーバー起動
export SCRYFALL_MCP_TRANSPORT_MODE=streamable_http
uv run scryfall-mcp

# ターミナル2: MCP Inspector起動
npx @modelcontextprotocol/inspector http://localhost:8000/mcp
```

#### AWS Lambda

```bash
# デプロイ済みLambda endpoint
npx @modelcontextprotocol/inspector https://abc123.execute-api.us-east-1.amazonaws.com/mcp
```

**認証付きエンドポイント:**

MCP Inspectorは認証ヘッダーを追加する機能がないため、以下の対処法を使用：

1. **一時的に認証無効化（開発環境のみ）**
   ```bash
   export SCRYFALL_MCP_EMAIL_AUTH_ENABLED=false
   export SCRYFALL_MCP_OAUTH_ENABLED=false
   ```

2. **ローカルプロキシ経由**
   ```bash
   # local_proxy.py
   from fastapi import FastAPI, Request
   import httpx

   app = FastAPI()

   @app.api_route("/mcp/{path:path}", methods=["GET", "POST"])
   async def proxy(request: Request, path: str):
       body = await request.body()
       headers = dict(request.headers)
       headers["Authorization"] = "Basic dXNlcjFAZXhhbXBsZS5jb206cGFzc3dvcmQ="

       async with httpx.AsyncClient() as client:
           response = await client.request(
               method=request.method,
               url=f"http://localhost:8000/mcp/{path}",
               content=body,
               headers=headers
           )
           return response.json()

   # 起動: uvicorn local_proxy:app --port 9000
   # Inspector: npx @modelcontextprotocol/inspector http://localhost:9000/mcp
   ```

### デバッグTips

#### 1. リクエスト/レスポンス確認

MCP Inspector GUI:
- **Tools** タブ: ツール一覧と引数確認
- **Call Tool** ボタン: ツール実行テスト
- **Request** タブ: JSON-RPC request確認
- **Response** タブ: JSON-RPC response確認

#### 2. Prompts確認

```bash
# ブラウザでPrompts一覧確認
# URL: http://localhost:5173
# Prompts タブ → "scryfall_setup" を選択
```

#### 3. Resources確認

```bash
# Resources タブ → URI一覧
# scryfall://setup-guide をクリックして内容確認
```

#### 4. サーバーログ

```bash
# サーバーログを並行表示
tail -f /path/to/server.log &
npx @modelcontextprotocol/inspector http://localhost:8000/mcp
```

---

## 自動テスト実行

### 全テスト実行

```bash
# プロジェクトルートで実行
uv run pytest
```

**期待される出力:**

```text
================================ test session starts =================================
platform darwin -- Python 3.11.7, pytest-8.0.0, pluggy-1.4.0
rootdir: /Users/tomoya/scryfall-mcp
configfile: pyproject.toml
plugins: asyncio-0.23.3, cov-4.1.0
collected 510 items

tests/test_settings.py ....                                                    [  1%]
tests/api/test_client.py ....................                                  [  5%]
tests/auth/test_email_auth.py ........................                         [ 10%]
tests/auth/test_jwt_middleware.py ....................                         [ 15%]
...
tests/integration/test_mcp_tools.py ............                              [100%]

================================ 510 passed in 45.23s ================================
```

### カバレッジ測定

```bash
# カバレッジレポート生成
uv run pytest --cov=scryfall_mcp --cov-report=term-missing

# HTMLレポート生成
uv run pytest --cov=scryfall_mcp --cov-report=html

# ブラウザで確認
open htmlcov/index.html
```

**期待されるカバレッジ:**

```text
Name                                    Stmts   Miss  Cover   Missing
---------------------------------------------------------------------
src/scryfall_mcp/__init__.py                5      0   100%
src/scryfall_mcp/server.py                 89      3    97%   245-247
src/scryfall_mcp/settings.py               67      2    97%   123, 156
src/scryfall_mcp/api/client.py            145      5    97%   234-238
src/scryfall_mcp/auth/email.py             78      1    99%   156
src/scryfall_mcp/auth/middleware.py        92      4    96%   178-181
...
---------------------------------------------------------------------
TOTAL                                    2847     78    97%
```

### 特定モジュールのテスト

```bash
# 認証テストのみ
uv run pytest tests/auth/ -v

# 統合テストのみ
uv run pytest tests/integration/ -v

# 特定ファイル
uv run pytest tests/auth/test_email_auth.py -v

# 特定テストクラス
uv run pytest tests/auth/test_email_auth.py::TestParseBasicAuthHeader -v

# 特定テスト関数
uv run pytest tests/auth/test_email_auth.py::TestParseBasicAuthHeader::test_parse_valid_basic_auth -v
```

### 並列実行

```bash
# pytest-xdist使用（高速化）
uv run pytest -n auto

# 4プロセス並列
uv run pytest -n 4
```

### CI/CD統合

#### GitHub Actions (`.github/workflows/test.yml`)

```yaml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh

      - name: Install dependencies
        run: uv sync

      - name: Run tests
        run: uv run pytest --cov=scryfall_mcp --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
```

### テスト監視モード

```bash
# ファイル変更時に自動テスト実行
uv run pytest-watch
```

---

## トラブルシューティング

### 認証エラー

#### 1. Email認証失敗

**エラー:**
```json
{
  "error": {
    "code": 401,
    "message": "Invalid credentials"
  }
}
```

**デバッグ手順:**

1. **認証情報確認**
   ```bash
   # 環境変数確認
   echo $SCRYFALL_MCP_EMAIL_AUTH_CREDENTIALS

   # パースエラー確認
   echo $SCRYFALL_MCP_EMAIL_AUTH_CREDENTIALS | python -m json.tool
   ```

2. **ハッシュ検証**
   ```python
   from scryfall_mcp.auth.email import verify_secret

   hashed = "$2b$12$KIXqZ9vL..."
   password = "my-password"

   if verify_secret(password, hashed):
       print("✅ Password matches")
   else:
       print("❌ Password mismatch")
   ```

3. **Base64エンコード確認**
   ```bash
   echo -n "user@example.com:password" | base64
   # dXNlckBleGFtcGxlLmNvbTpwYXNzd29yZA==
   ```

#### 2. JWT検証失敗

**エラー:**
```json
{
  "error": {
    "code": 401,
    "message": "Invalid token: Signature verification failed"
  }
}
```

**デバッグ手順:**

1. **Secret Key一致確認**
   ```bash
   # サーバー側
   echo $SCRYFALL_MCP_JWT_SECRET_KEY

   # クライアント側（トークン生成時）
   echo $JWT_SECRET_KEY
   ```

2. **トークンデコード**
   ```python
   from jose import jwt

   token = "eyJhbGciOiJIUzI1NiIs..."

   # 検証なしでデコード
   claims = jwt.get_unverified_claims(token)
   print(claims)

   # ヘッダー確認
   header = jwt.get_unverified_header(token)
   print(header)  # {"alg": "HS256", "typ": "JWT"}
   ```

3. **有効期限確認**
   ```python
   import time
   from jose import jwt

   claims = jwt.get_unverified_claims(token)
   now = int(time.time())

   print(f"Issued at: {claims['iat']} (now: {now})")
   print(f"Expires at: {claims['exp']} (now: {now})")

   if claims['exp'] < now:
       print("❌ Token expired")
   else:
       print(f"✅ Valid for {claims['exp'] - now} seconds")
   ```

---

### コールドスタート対応

**問題:** Lambda初回リクエストが3-5秒かかる

**デバッグ:**

```bash
# CloudWatch Insights Query
aws logs insights start-query \
  --log-group-name /aws/lambda/scryfall-mcp-dev-mcp \
  --start-time $(date -u -d '1 hour ago' +%s) \
  --end-time $(date -u +%s) \
  --query-string 'fields @timestamp, @duration | filter @type = "REPORT" | stats avg(@duration), max(@duration) by bin(5m)'
```

**対策:**

1. **Provisioned Concurrency設定**
   ```yaml
   # serverless.yml
   functions:
     mcp:
       provisionedConcurrency: 1  # 常時1インスタンス稼働
   ```

2. **定期的なウォームアップ**
   ```bash
   # EventBridge (CloudWatch Events) で5分ごとにPing
   aws events put-rule \
     --name scryfall-mcp-warmup \
     --schedule-expression "rate(5 minutes)"

   aws events put-targets \
     --rule scryfall-mcp-warmup \
     --targets "Id"="1","Arn"="arn:aws:lambda:us-east-1:123456789012:function:scryfall-mcp-dev-mcp"
   ```

3. **メモリサイズ増加**
   ```yaml
   # serverless.yml
   provider:
     memorySize: 1024  # 768MB → 1024MB
   ```

---

### レート制限エラー

#### Scryfall API レート制限

**エラーログ:**
```text
WARNING:scryfall_mcp.api.client:Rate limit approaching, waiting 100ms
```

**対策:**

1. **リクエスト間隔確認**
   ```python
   # RateLimiterManager設定確認
   from scryfall_mcp.settings import get_settings

   settings = get_settings()
   print(f"Rate limit: {settings.scryfall_rate_limit_ms}ms")  # 100ms推奨
   ```

2. **バーストリクエスト回避**
   ```python
   # 連続リクエストは避ける
   import asyncio

   results = []
   for query in queries:
       result = await client.search_cards(query)
       results.append(result)
       await asyncio.sleep(0.1)  # 100ms wait
   ```

#### ユーザー別レート制限

**エラー:**
```json
{
  "error": {
    "code": 429,
    "message": "Rate limit exceeded: 100 requests per minute",
    "retry_after": 60
  }
}
```

**デバッグ:**

```bash
# Redis確認（使用している場合）
redis-cli KEYS "rate_limit:*"
redis-cli GET "rate_limit:user@example.com"
redis-cli TTL "rate_limit:user@example.com"

# メモリバックエンド確認
# ログにカウント情報が出力される
# DEBUG: User user@example.com rate limit: 95/100
```

**対策:**

1. **リクエスト頻度削減**
2. **Retry-After ヘッダーに従う**
   ```python
   if response.status_code == 429:
       retry_after = int(response.headers.get("Retry-After", 60))
       await asyncio.sleep(retry_after)
   ```

3. **レート制限緩和リクエスト（プレミアムユーザー等）**

---

### 環境変数未設定

**エラー:**
```text
ValueError: jwt_secret_key is required when oauth_enabled=True
```

**確認:**

```bash
# すべての環境変数確認
env | grep SCRYFALL_MCP

# 特定変数
echo $SCRYFALL_MCP_JWT_SECRET_KEY
```

**解決:**

```bash
# .envファイル作成（ローカル開発）
cat > .env <<EOF
SCRYFALL_MCP_USER_AGENT="ScryfallMCP/0.1.0 (your-email@example.com)"
SCRYFALL_MCP_JWT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
SCRYFALL_MCP_OAUTH_ENABLED=true
SCRYFALL_MCP_LOG_LEVEL=DEBUG
EOF

# 環境変数読み込み
export $(cat .env | xargs)
```

---

## ベストプラクティス

### セキュリティ

1. **シークレット管理**
   - ✅ AWS SSM Parameter Store使用（Lambda）
   - ✅ 環境変数使用（ローカル）
   - ❌ コードにハードコーディング禁止
   - ❌ Gitにコミット禁止

2. **認証情報のローテーション**
   ```bash
   # 定期的にJWT Secretを変更
   NEW_SECRET=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')

   aws ssm put-parameter \
     --name "/scryfall-mcp/dev/JWT_SECRET_KEY" \
     --type "SecureString" \
     --value "$NEW_SECRET" \
     --overwrite
   ```

3. **ログからPII除去**
   - メールアドレス、パスワード、JWTトークンはログに出力しない
   - `scryfall_mcp.auth.email.mask_email()` 使用

### テスト設計

1. **モック化**
   ```python
   import pytest
   from unittest.mock import AsyncMock, patch

   @pytest.mark.asyncio
   async def test_search_cards():
       with patch("scryfall_mcp.api.client.ScryfallAPIClient.search_cards") as mock:
           mock.return_value = AsyncMock(return_value={"data": []})
           # テスト実行
   ```

2. **フィクスチャ活用**
   ```python
   @pytest.fixture
   def mock_settings():
       return Settings(
           user_agent="Test/1.0",
           oauth_enabled=False
       )
   ```

3. **パラメトライズドテスト**
   ```python
   @pytest.mark.parametrize("query,expected", [
       ("Lightning Bolt", 10),
       ("Black Lotus", 5),
       ("Forest", 175),
   ])
   def test_search_results(query, expected):
       # テスト実行
   ```

### CI/CD

1. **ステージング環境テスト**
   ```bash
   # デプロイ後に自動テスト
   npm run deploy:staging
   ./scripts/integration-test.sh https://staging.api.example.com
   ```

2. **カバレッジ閾値**
   ```bash
   # 95%未満でCI失敗
   uv run pytest --cov=scryfall_mcp --cov-fail-under=95
   ```

3. **並列テスト**
   ```yaml
   # .github/workflows/test.yml
   strategy:
     matrix:
       python-version: ['3.11', '3.12']
   ```

---

## 参考資料

### ドキュメント

- **MCP Protocol**: https://modelcontextprotocol.io/
- **FastMCP**: https://github.com/jlowin/fastmcp
- **Scryfall API**: https://scryfall.com/docs/api
- **認証設定**: `/docs/AUTHENTICATION.md`
- **デプロイガイド**: `/docs/DEPLOYMENT.md`（作成予定）

### ツール

- **MCP Inspector**: https://github.com/modelcontextprotocol/inspector
- **pytest**: https://docs.pytest.org/
- **pytest-asyncio**: https://pytest-asyncio.readthedocs.io/
- **pytest-cov**: https://pytest-cov.readthedocs.io/

### AWS

- **Lambda Documentation**: https://docs.aws.amazon.com/lambda/
- **CloudWatch Logs Insights**: https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/AnalyzingLogData.html
- **SSM Parameter Store**: https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-parameter-store.html

---

**最終更新:** 2025-11-04
**ステータス:** 完全版
