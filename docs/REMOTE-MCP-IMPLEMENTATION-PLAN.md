# Remote MCP Implementation Plan

Issue #8対応のための詳細な実装計画書。

## 概要

現在のscryfall-mcpはLocal MCP（stdio transport）として動作していますが、Remote MCP対応により以下のメリットが得られます：

- 簡単なセットアップ: URLを指定するだけで利用可能
- マルチテナント: 複数ユーザーでの利用が可能
- 真の並行処理: 複数クエリの同時実行
- 24/7可用性: 常時稼働サービスとして提供

## 技術調査結果

### Streamable HTTP対応状況

**FastMCP 2.3で完全対応済み**

- **リリース状況**: FastMCP 2.3でStreamable HTTP transportが実装済み
- **実装方法**: `mcp.run(transport="http", host="127.0.0.1", port=8000, path="/mcp")`
- **単一エンドポイント**: 送受信を1つのHTTPエンドポイントで処理、双方向通信対応
- **業界標準化**: MCP仕様の最新ドラフトでStreamable HTTPが推奨プロトコルに採用
- **Cloudflare公式サポート**: CloudflareがPython MCPサーバーのホスティングを公式サポート

### 現在の実装状況

#### server.py

現在のScryfallMCPServer.run()はstdioモードのみをサポート：

```python
# src/scryfall_mcp/server.py:337-346
async def run(self) -> None:
    """Run the MCP server."""
    try:
        # 現在はstdioモードのみ
        await self.app.run_stdio_async()
    except Exception:
        logger.exception("Server error")
        raise
```

**必要な変更**: transport選択ロジックの追加

#### settings.py

現在264の設定項目があるが、Remote MCP向けの設定が未定義。

**必要な追加項目**:

- `transport_mode`: stdio | http | streamable_http
- `http_host`, `http_port`, `http_path`
- `oauth_enabled`, `jwt_secret_key`, `jwt_algorithm`
- `allowed_origins` (CORS)
- `rate_limit_per_user` (マルチテナント対応)

#### rate_limiter.py

- **現状**: asyncio.Lockでスレッドセーフ実装済み
- **Remote MCP対応**: ユーザー単位のレート制限追加が必要
  - user_id別のRateLimiterインスタンス管理
  - Redisベースの分散レート制限

#### キャッシュシステム

- **現状**: MemoryCacheとRedisCache実装済み
- **Remote MCP要件**: Redis必須（複数Workerインスタンス間での共有キャッシュ）

## 技術選定

### Transport方式

- **推奨**: Streamable HTTP
- **理由**: 単一エンドポイント、双方向通信、serverless環境で運用しやすい

### ホスティングプラットフォーム

#### 第1推奨: Cloudflare Workers

**選定理由**:

- 公式MCP対応
- ワンクリックデプロイ（`wrangler deploy`）
- OAuth統合が自動提供される
- コストパフォーマンス: 無料枠100k req/日、egress料金なし
- Python対応（2025年）
- グローバルエッジ配信で低レイテンシ

**コスト試算（月額）**:

- 5,000 req/月: $0.75（ほぼKVストレージのみ）
- 100万 req/月: $20（Worker $5 + KV $15程度）

#### 第2推奨: AWS Lambda + API Gateway

**選定理由**:

- 既存Python実装がそのまま動作
- 大きな無料枠（月100万リクエストまで無料）
- エコシステム充実（API Gateway、ElastiCache、CloudWatch）
- コールドスタート対策可能（SnapStart、Graviton2対応）

**コスト試算（月額）**:

- 5,000 req/月: $12（Redis t4g.micro）
- 100万 req/月: $16-20（Lambda $4 + Redis $12 + API Gateway $0）

### 認証方式

- **OAuth 2.1**: 業界標準の認証プロトコル
- **JWT**: トークンベース認証
- **プロバイダー候補**: Auth0、Cloudflare Access、Keycloak

## 実装計画（8週間）

### Phase 1: Transport対応 (Week 1-2)

#### タスク1.1: server.pyの修正

**ファイル**: `src/scryfall_mcp/server.py:337-346`

**変更内容**:

```python
async def run(self, transport_mode: str | None = None) -> None:
    """Run the MCP server with specified transport.

    Parameters
    ----------
    transport_mode : str | None, optional (default: None)
        Transport mode override. If None, uses settings value.
    """
    mode = transport_mode or self.settings.transport_mode

    try:
        if mode == "stdio":
            await self.app.run_stdio_async()
        elif mode in ("http", "streamable_http"):
            await self.app.run(
                transport="http",
                host=self.settings.http_host,
                port=self.settings.http_port,
                path=self.settings.http_path
            )
        else:
            raise ValueError(f"Unsupported transport: {mode}")
    except Exception:
        logger.exception("Server error")
        raise
```

**テスト方法**:
```bash
# ユニットテスト
pytest tests/server_test.py::test_transport_mode_http

# 手動確認
python -m scryfall_mcp --transport streamable_http --http-host 127.0.0.1 --http-port 8080
```

**期待される成果**:
- stdio、http、streamable_httpの3モードで動作
- 既存のstdio互換性維持
- テスト合格率100%

#### タスク1.2: __main__.pyのCLI更新

**ファイル**: `src/scryfall_mcp/__main__.py`

**変更内容**:

```python
import argparse

def main():
    parser = argparse.ArgumentParser(description="Scryfall MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http", "streamable_http"],
        default="stdio",
        help="Transport mode for MCP server"
    )
    parser.add_argument(
        "--http-host",
        default="127.0.0.1",
        help="HTTP server host (for http/streamable_http mode)"
    )
    parser.add_argument(
        "--http-port",
        type=int,
        default=8000,
        help="HTTP server port (for http/streamable_http mode)"
    )
    parser.add_argument(
        "--http-path",
        default="/mcp",
        help="HTTP endpoint path (for http/streamable_http mode)"
    )

    args = parser.parse_args()

    # Override settings with CLI arguments
    settings = get_settings()
    if args.transport:
        settings.transport_mode = args.transport
    if args.http_host:
        settings.http_host = args.http_host
    if args.http_port:
        settings.http_port = args.http_port
    if args.http_path:
        settings.http_path = args.http_path

    # Run server
    server = ScryfallMCPServer()
    asyncio.run(server.run())
```

**テスト方法**:
```bash
# ヘルプ表示
python -m scryfall_mcp --help

# ユニットテスト
pytest tests/test_cli.py::test_transport_cli_args
```

**期待される成果**:
- CLI引数で全トランスポートモード指定可能
- 環境変数との統合（CLI優先）
- ヘルプメッセージの正確性

#### タスク1.3: settings.pyの拡張

**ファイル**: `src/scryfall_mcp/settings.py:17-280`

**追加フィールド**:

```python
class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # ... 既存設定（264行） ...

    # Remote MCP Configuration
    transport_mode: str = Field(
        default="stdio",
        pattern="^(stdio|http|streamable_http)$",
        description="Transport mode for MCP server",
    )
    http_host: str = Field(
        default="127.0.0.1",
        description="HTTP server host for remote transport",
    )
    http_port: int = Field(
        default=8000,
        ge=1024,
        le=65535,
        description="HTTP server port for remote transport",
    )
    http_path: str = Field(
        default="/mcp",
        description="HTTP endpoint path for MCP protocol",
    )

    # Authentication Configuration
    oauth_enabled: bool = Field(
        default=False,
        description="Enable OAuth 2.1 authentication for remote MCP",
    )
    jwt_secret_key: str = Field(
        default="",
        description="JWT signing secret (REQUIRED in production)",
    )
    jwt_algorithm: str = Field(
        default="HS256",
        pattern="^(HS256|HS384|HS512|RS256|RS384|RS512)$",
        description="JWT algorithm for token verification",
    )
    allowed_origins: list[str] = Field(
        default=["*"],
        description="CORS allowed origins (use specific domains in production)",
    )

    # Multi-tenant Rate Limiting
    rate_limit_per_user: int = Field(
        default=100,
        ge=1,
        le=10000,
        description="Rate limit per user (requests per minute)",
    )
```

**テスト方法**:
```bash
# デフォルト値テスト
pytest tests/test_settings.py::test_transport_defaults

# バリデーションテスト
pytest tests/test_settings.py::test_transport_validation

# .env.exampleの更新確認
cat .env.example | grep TRANSPORT
```

**期待される成果**:
- Pydanticバリデーション合格
- 既存設定との互換性維持
- `.env.example`更新完了

#### タスク1.4: ローカルHTTPモード動作確認

**ファイル**: `tests/integration/test_http_transport.py`（新規）

**テスト内容**:

```python
import pytest
import httpx
from scryfall_mcp.server import ScryfallMCPServer

@pytest.mark.asyncio
async def test_http_transport_basic():
    """Test basic HTTP transport functionality."""
    server = ScryfallMCPServer()

    # Start server in background
    # ... (FastMCPのテストパターンに従う)

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://127.0.0.1:8000/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "tools/list",
                "params": {},
                "id": 1
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        assert "tools" in data["result"]
```

**実行方法**:
```bash
pytest tests/integration/test_http_transport.py -s -v
```

**期待される成果**:
- HTTPモードでMCPプロトコル通信成功
- ツールリスト取得確認
- エラーハンドリング動作確認

### Phase 2: 認証基盤 (Week 3)

#### タスク2.1: JWTミドルウェア実装

**ファイル**: `src/scryfall_mcp/auth/middleware.py`（新規）

**実装内容**:

```python
"""JWT validation middleware for Remote MCP authentication."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import HTTPException, Request
from jose import JWTError, jwt

if TYPE_CHECKING:
    from ..settings import Settings


class JWTValidationMiddleware:
    """Middleware for validating JWT tokens in MCP requests.

    This middleware extracts and validates JWT tokens from the Authorization
    header, adding user information to the request scope for downstream handlers.
    """

    def __init__(self, app, settings: Settings) -> None:
        """Initialize JWT validation middleware.

        Parameters
        ----------
        app
            ASGI application instance
        settings : Settings
            Application settings containing JWT configuration
        """
        self.app = app
        self.settings = settings

    async def __call__(self, scope, receive, send):
        """Process request and validate JWT token.

        Parameters
        ----------
        scope
            ASGI scope dict
        receive
            ASGI receive callable
        send
            ASGI send callable

        Raises
        ------
        HTTPException
            If token is missing, invalid, or expired
        """
        if scope["type"] == "http":
            headers = dict(scope["headers"])
            auth_header = headers.get(b"authorization", b"").decode()

            if not auth_header.startswith("Bearer "):
                raise HTTPException(
                    status_code=401,
                    detail="Missing or invalid Authorization header"
                )

            token = auth_header[7:]  # Remove "Bearer " prefix

            try:
                payload = jwt.decode(
                    token,
                    self.settings.jwt_secret_key,
                    algorithms=[self.settings.jwt_algorithm]
                )
                scope["user"] = payload  # Add user info to scope
            except JWTError as e:
                raise HTTPException(
                    status_code=401,
                    detail=f"Invalid token: {e}"
                )

        await self.app(scope, receive, send)
```

**テスト方法**:
```bash
pytest tests/auth/test_jwt_middleware.py -v
```

**期待される成果**:
- JWT検証成功時にuser情報がscopeに追加される
- 無効なトークンで401エラー
- トークン欠損時に適切なエラーメッセージ

#### タスク2.2: OAuth 2.1フロー実装

**ファイル**: `src/scryfall_mcp/auth/oauth.py`（新規）

**実装内容**:

```python
"""OAuth 2.1 authentication flow for Remote MCP."""

from __future__ import annotations

import secrets
from typing import TYPE_CHECKING

import httpx
from pydantic import BaseModel

if TYPE_CHECKING:
    from ..settings import Settings


class OAuthToken(BaseModel):
    """OAuth token response model."""

    access_token: str
    token_type: str
    expires_in: int
    refresh_token: str | None = None
    scope: str | None = None


class OAuthClient:
    """OAuth 2.1 client implementation.

    Supports Authorization Code with PKCE flow for secure authentication.
    """

    def __init__(self, settings: Settings) -> None:
        """Initialize OAuth client.

        Parameters
        ----------
        settings : Settings
            Application settings containing OAuth configuration
        """
        self.settings = settings
        self.client = httpx.AsyncClient()

    def generate_pkce_pair(self) -> tuple[str, str]:
        """Generate PKCE code verifier and challenge.

        Returns
        -------
        tuple[str, str]
            Code verifier and code challenge
        """
        code_verifier = secrets.token_urlsafe(32)
        # code_challenge = base64url(sha256(code_verifier))
        # ... (実装省略)
        return code_verifier, "challenge"

    async def get_authorization_url(self) -> str:
        """Get authorization URL for user login.

        Returns
        -------
        str
            Authorization URL with PKCE parameters
        """
        # ... (実装省略)
        return "https://auth0.example.com/authorize?..."

    async def exchange_code_for_token(self, code: str) -> OAuthToken:
        """Exchange authorization code for access token.

        Parameters
        ----------
        code : str
            Authorization code from OAuth provider

        Returns
        -------
        OAuthToken
            Access token and metadata
        """
        # ... (実装省略)
        pass
```

**CLI補助コマンド**:
```bash
python -m scryfall_mcp.oauth login
```

**テスト方法**:
```bash
pytest tests/auth/test_oauth_flow.py
```

**期待される成果**:
- PKCE対応のOAuth 2.1フロー実装
- Auth0/Cloudflare Access連携成功
- トークンリフレッシュ機能

#### タスク2.3: ユーザー単位レート制限

**ファイル**: `src/scryfall_mcp/api/rate_limiter.py`

**追加実装**:

```python
class RateLimiterManager:
    """Manage per-user rate limiters with Redis backing.

    This class provides distributed rate limiting across multiple worker
    instances using Redis as a shared state store.
    """

    def __init__(self, redis_client) -> None:
        """Initialize rate limiter manager.

        Parameters
        ----------
        redis_client
            Redis client instance for distributed state
        """
        self.redis = redis_client
        self.limiters: dict[str, RateLimiter] = {}

    async def acquire(self, user_id: str, limit: int = 100) -> None:
        """Acquire rate limit permission for user.

        Parameters
        ----------
        user_id : str
            Unique user identifier from JWT payload
        limit : int, optional (default: 100)
            Maximum requests per minute for this user

        Raises
        ------
        HTTPException
            If user has exceeded rate limit
        """
        key = f"rate_limit:{user_id}"
        current = await self.redis.incr(key)

        if current == 1:
            await self.redis.expire(key, 60)  # 1-minute window

        if current > limit:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded",
                headers={"Retry-After": "60"}
            )
```

**テスト方法**:
```bash
# ユニットテスト
pytest tests/api/test_rate_limiter.py::test_user_rate_limit

# ベンチマーク
python scripts/bench_rate_limiter.py
```

**期待される成果**:
- ユーザー単位でレート制限適用
- Redis障害時のフォールバック動作
- Retry-Afterヘッダー付与

### Phase 3: ホスティング準備 (Week 4)

#### タスク3.1: Cloudflare Workers設定

**ファイル**: `wrangler.toml`（新規）

```toml
name = "scryfall-mcp"
main = "worker.py"
compatibility_date = "2025-01-01"
compatibility_flags = ["python_workers"]

[env.production]
vars = { SCRYFALL_MCP_TRANSPORT_MODE = "streamable_http" }

[[kv_namespaces]]
binding = "CACHE"
id = "YOUR_KV_NAMESPACE_ID"
preview_id = "YOUR_PREVIEW_KV_NAMESPACE_ID"

[observability]
enabled = true
```

**ファイル**: `worker.py`（新規）

```python
"""Cloudflare Workers entry point for Remote MCP."""

from scryfall_mcp.server import ScryfallMCPServer


async def handler(request):
    """Handle incoming MCP requests.

    Parameters
    ----------
    request
        Cloudflare Workers Request object

    Returns
    -------
        Response object compatible with Workers runtime
    """
    server = ScryfallMCPServer()
    # Convert Workers request to ASGI format
    # ... (Cloudflare Workers ASGIアダプター実装)
    return await server.app(request)
```

**デプロイコマンド**:
```bash
# ドライラン
wrangler deploy --dry-run

# ステージングデプロイ
wrangler deploy --env staging

# 本番デプロイ
wrangler deploy --env production
```

**テスト方法**:
```bash
# ローカルテスト
wrangler dev

# 統合テスト
pytest tests/deploy/test_worker_entrypoint.py
```

**期待される成果**:
- Cloudflare Workersで動作
- KVストレージでキャッシュ機能
- グローバルエッジ配信確認

#### タスク3.2: AWS Lambda代替案

**ファイル**: `serverless.yml`（新規）

```yaml
service: scryfall-mcp

provider:
  name: aws
  runtime: python3.11
  region: us-east-1
  architecture: arm64
  httpApi:
    cors: true
    authorizers:
      jwtAuthorizer:
        type: jwt
        identitySource: $request.header.Authorization
        issuerUrl: https://YOUR-AUTH0-DOMAIN.auth0.com/
        audience: scryfall-mcp-api

functions:
  mcp:
    handler: lambda_handler.handler
    memorySize: 512
    timeout: 30
    events:
      - httpApi:
          path: /mcp
          method: ANY
          authorizer:
            name: jwtAuthorizer
    environment:
      SCRYFALL_MCP_TRANSPORT_MODE: streamable_http
      SCRYFALL_MCP_CACHE_BACKEND: redis
      SCRYFALL_MCP_CACHE_REDIS_URL: !Ref RedisEndpoint

resources:
  Resources:
    RedisCluster:
      Type: AWS::ElastiCache::CacheCluster
      Properties:
        Engine: redis
        CacheNodeType: cache.t4g.micro
        NumCacheNodes: 1
```

**ファイル**: `lambda_handler.py`（新規）

```python
"""AWS Lambda handler for Remote MCP."""

from mangum import Mangum

from scryfall_mcp.server import ScryfallMCPServer

server = ScryfallMCPServer()
handler = Mangum(server.app, lifespan="off")
```

**デプロイコマンド**:
```bash
# パッケージ作成
npm exec serverless package

# ステージングデプロイ
npm exec serverless deploy --stage staging

# 本番デプロイ
npm exec serverless deploy --stage production
```

**テスト方法**:
```bash
pytest tests/deploy/test_lambda_handler.py
```

**期待される成果**:
- AWS Lambdaで動作
- API Gateway統合成功
- ElastiCache接続確認

#### タスク3.3: 環境変数・シークレット管理

**ファイル**: `scripts/set_secrets.sh`（新規）

```bash
#!/bin/bash
# Set secrets for Cloudflare Workers or AWS Lambda

ENV=${1:-staging}

if [ "$ENV" = "cloudflare" ]; then
    wrangler secret put SCRYFALL_MCP_JWT_SECRET_KEY
    wrangler secret put SCRYFALL_MCP_USER_AGENT
elif [ "$ENV" = "aws" ]; then
    aws ssm put-parameter \
        --name "/scryfall-mcp/JWT_SECRET_KEY" \
        --value "$JWT_SECRET_KEY" \
        --type SecureString
fi
```

**ファイル**: `.env.example`（更新）

```bash
# ... 既存設定 ...

# Remote MCP Configuration
SCRYFALL_MCP_TRANSPORT_MODE=stdio
SCRYFALL_MCP_HTTP_HOST=127.0.0.1
SCRYFALL_MCP_HTTP_PORT=8000
SCRYFALL_MCP_HTTP_PATH=/mcp

# Authentication (REQUIRED for production Remote MCP)
SCRYFALL_MCP_OAUTH_ENABLED=false
SCRYFALL_MCP_JWT_SECRET_KEY=your-secret-key-here-min-32-chars
SCRYFALL_MCP_JWT_ALGORITHM=HS256
SCRYFALL_MCP_ALLOWED_ORIGINS=*

# Multi-tenant Rate Limiting
SCRYFALL_MCP_RATE_LIMIT_PER_USER=100
```

**テスト方法**:
```bash
# ドライラン
bash scripts/set_secrets.sh --dry-run

# ステージング
bash scripts/set_secrets.sh staging
```

**期待される成果**:
- シークレット管理手順書完成
- `.env.example`更新
- セキュリティベストプラクティス遵守

### Phase 4: デプロイとテスト (Week 5-6)

#### タスク4.1: Cloudflare Workers初回デプロイ

**手順**:

1. Cloudflare アカウントセットアップ
2. KV Namespace作成
3. Secrets設定
4. デプロイ実行

**コマンド**:
```bash
# KV Namespace作成
wrangler kv:namespace create CACHE
wrangler kv:namespace create CACHE --preview

# Secrets設定
wrangler secret put SCRYFALL_MCP_JWT_SECRET_KEY
wrangler secret put SCRYFALL_MCP_USER_AGENT

# デプロイ
wrangler deploy --env staging

# ログ監視
wrangler tail --env staging
```

**テスト方法**:
```bash
# MCP Inspector使用
npx @modelcontextprotocol/inspector https://staging.your-domain.com/mcp

# 統合テスト
pytest tests/integration/test_remote_client.py --env staging
```

**期待される成果**:
- ステージング環境で動作確認
- MCP Inspectorでツールリスト取得成功
- エラーログゼロ

#### タスク4.2: 負荷テスト

**ファイル**: `scripts/load_test.py`（新規）

```python
"""Load testing script for Remote MCP server."""

import asyncio
from typing import Any

import httpx


async def send_request(client: httpx.AsyncClient, url: str, token: str) -> dict[str, Any]:
    """Send single MCP request.

    Parameters
    ----------
    client : httpx.AsyncClient
        HTTP client instance
    url : str
        MCP endpoint URL
    token : str
        JWT authentication token

    Returns
    -------
    dict[str, Any]
        Response JSON data
    """
    response = await client.post(
        url,
        json={
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "search_cards",
                "arguments": {"query": "Lightning Bolt"}
            },
            "id": 1
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    return response.json()


async def run_load_test(url: str, token: str, concurrent: int, total: int) -> None:
    """Run load test with specified concurrency.

    Parameters
    ----------
    url : str
        MCP endpoint URL
    token : str
        JWT authentication token
    concurrent : int
        Number of concurrent requests
    total : int
        Total number of requests
    """
    async with httpx.AsyncClient() as client:
        tasks = []
        for _ in range(total):
            tasks.append(send_request(client, url, token))
            if len(tasks) >= concurrent:
                await asyncio.gather(*tasks)
                tasks = []

        if tasks:
            await asyncio.gather(*tasks)
```

**実行方法**:
```bash
# 100同時接続
python scripts/load_test.py --target https://staging.example.com/mcp --concurrent 100 --total 10000

# レポート生成
python scripts/load_test.py --report
```

**期待される成果**:
- 1000同時接続でp95 < 500ms
- エラー率 < 1%
- レポート保存（`docs/perf_report_week6.md`）

#### タスク4.3: エラーハンドリング改善

**ファイル**: `src/scryfall_mcp/errors/handlers.py`（更新）

```python
"""Centralized error handling for MCP server."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

if TYPE_CHECKING:
    from ..settings import Settings


class MCPErrorHandler:
    """Centralized error handler for MCP protocol errors."""

    @staticmethod
    async def handle_http_exception(
        request: Request,
        exc: HTTPException
    ) -> JSONResponse:
        """Handle HTTP exceptions with MCP error format.

        Parameters
        ----------
        request : Request
            FastAPI request object
        exc : HTTPException
            HTTP exception to handle

        Returns
        -------
        JSONResponse
            JSON-RPC 2.0 error response
        """
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "jsonrpc": "2.0",
                "error": {
                    "code": exc.status_code,
                    "message": exc.detail
                },
                "id": None
            }
        )
```

**テスト方法**:
```bash
pytest tests/test_error_handling.py -v
```

**期待される成果**:
- 統一されたエラーレスポンス形式
- ログの構造化（JSON形式）
- ステージングでエラーシナリオ確認

### Phase 5: 監視・運用 (Week 7)

#### タスク5.1: ログ・メトリクス収集

**ファイル**: `docs/MONITORING.md`（新規）

監視ガイドラインの内容:
- Cloudflare Analytics設定方法
- Workers KVメトリクス確認方法
- Grafanaダッシュボード設定（AWS Lambda用）

**主要メトリクス**:
- リクエスト数（total, success, error）
- レスポンスタイム（p50, p95, p99）
- エラー率（4xx, 5xx）
- キャッシュヒット率
- Scryfall APIレート制限残量

**テスト方法**:
```bash
# 設定テンプレート生成
python scripts/setup_observability.py --dry-run

# Cloudflare Analytics確認
wrangler tail --format json | jq '.logs[]'
```

**期待される成果**:
- 監視ダッシュボード構築
- メトリクス収集開始
- ドキュメント完成

#### タスク5.2: アラート設定

**アラート条件**:
- エラー率 > 5%（5分間継続）
- P95レスポンスタイム > 2秒
- キャッシュヒット率 < 50%
- Scryfall APIレート制限到達

**通知先**:
- Slack（ステージング: #scryfall-mcp-alerts）
- PagerDuty（本番のみ）

**テスト方法**:
```bash
# テスト通知
python scripts/test_alerts.py --slack-webhook $SLACK_WEBHOOK
```

**期待される成果**:
- アラート通知成功
- エスカレーション手順確立
- Runbook作成

#### タスク5.3: ドキュメント整備

**新規ドキュメント**:

1. `docs/DEPLOYMENT.md` - デプロイ手順書
2. `docs/MONITORING.md` - 監視・運用ガイド
3. `docs/RUNBOOK.md` - 障害対応手順
4. `docs/SECURITY.md` - セキュリティガイドライン

**レビュー観点**:
- 手順の正確性
- スクリーンショット完備
- トラブルシューティング項目充実

**期待される成果**:
- 全ドキュメントレビュー完了
- チーム内共有完了
- Knowledge base反映

### Phase 6: 最終調整 (Week 8)

#### タスク6.1: パフォーマンスチューニング

**最適化項目**:

1. Redis接続プール調整
2. HTTP keep-alive設定
3. キャッシュTTL最適化
4. レスポンス圧縮（gzip）

**テスト方法**:
```bash
# ベンチマーク（最適化前）
python scripts/load_test.py --profile --output before.json

# 最適化実施
# ...

# ベンチマーク（最適化後）
python scripts/load_test.py --profile --output after.json

# 比較レポート
python scripts/compare_benchmark.py before.json after.json
```

**期待される成果**:
- レスポンスタイム20%改善
- キャッシュヒット率80%以上
- レポート保存（`docs/perf_report_week8.md`）

#### タスク6.2: セキュリティ監査

**チェック項目**:

1. OAuth設定レビュー（スコープ、リダイレクトURI）
2. JWTキーマネジメント手順確認
3. 依存ライブラリ脆弱性スキャン
4. 公開エンドポイントのセキュリティスキャン

**実行コマンド**:
```bash
# 依存関係脆弱性チェック
pip-audit

# セキュリティスキャン
bandit -r src/

# エンドポイントスキャン（許可範囲内）
nmap -sV https://staging.example.com
```

**期待される成果**:
- Critical脆弱性ゼロ
- セキュリティ担当者承認
- 監査レポート作成（`docs/security_audit.md`）

#### タスク6.3: README更新

**更新内容**:

1. Remote MCP使用方法セクション追加
2. Cloudflare/AWSデプロイ手順リンク
3. トラブルシューティング項目追加
4. アーキテクチャ図更新

**ファイル**: `README.md`

追加セクション例:

```markdown
## Remote MCP Usage

### Quick Start (Cloudflare Workers)

1. Clone the repository
2. Configure secrets
3. Deploy to Cloudflare

\`\`\`bash
git clone https://github.com/reonyanarticle/scryfall-mcp.git
cd scryfall-mcp

# Set secrets
wrangler secret put SCRYFALL_MCP_JWT_SECRET_KEY
wrangler secret put SCRYFALL_MCP_USER_AGENT

# Deploy
wrangler deploy --env production
\`\`\`

### Authentication

Remote MCP requires OAuth 2.1 authentication. Configure your MCP client:

\`\`\`json
{
  "mcpServers": {
    "scryfall": {
      "url": "https://your-domain.com/mcp",
      "auth": {
        "type": "oauth2",
        "authorization_url": "https://auth0.example.com/authorize",
        "token_url": "https://auth0.example.com/token",
        "client_id": "YOUR_CLIENT_ID"
      }
    }
  }
}
\`\`\`

For detailed deployment instructions, see [DEPLOYMENT.md](docs/DEPLOYMENT.md).
```

**テスト方法**:
```bash
# Markdownリント
markdownlint README.md docs/*.md

# リンク切れチェック
markdown-link-check README.md
```

**期待される成果**:
- README完全更新
- リンク切れゼロ
- レビュー承認

## 影響を受けるファイル一覧

### 修正が必要なファイル

1. `src/scryfall_mcp/server.py` - transport選択ロジック追加
2. `src/scryfall_mcp/settings.py` - Remote MCP設定追加
3. `src/scryfall_mcp/__main__.py` - CLI引数追加
4. `src/scryfall_mcp/api/rate_limiter.py` - ユーザー単位レート制限
5. `pyproject.toml` - 依存関係追加
6. `README.md` - Remote MCP使用方法追加

### 新規作成が必要なファイル

1. `src/scryfall_mcp/auth/middleware.py` - JWT検証
2. `src/scryfall_mcp/auth/oauth.py` - OAuth 2.1フロー
3. `wrangler.toml` - Cloudflare Workers設定
4. `worker.py` - Cloudflare Workersエントリポイント
5. `serverless.yml` - AWS Lambda設定（代替案）
6. `lambda_handler.py` - AWS Lambdaハンドラー（代替案）
7. `docs/DEPLOYMENT.md` - デプロイ手順書
8. `docs/MONITORING.md` - 監視・運用ガイド
9. `docs/RUNBOOK.md` - 障害対応手順
10. `docs/SECURITY.md` - セキュリティガイドライン
11. `scripts/load_test.py` - 負荷テストスクリプト
12. `scripts/set_secrets.sh` - シークレット管理スクリプト

## リスク管理

### 技術的リスク

**リスク1: Streamable HTTP実装による未知のバグ**
- 影響度: 中
- 対策: Week 2で統合テスト充実、FastMCPリリースノート追随

**リスク2: OAuth統合の複雑度**
- 影響度: 高
- 対策: Auth0/Cloudflare Accessのテンプレート活用、ステージングで早期検証

**リスク3: Redis依存増加**
- 影響度: 中
- 対策: マネージドRedis（Upstash/ElastiCache）のSLA確認、フォールバックとしてメモリキャッシュ保持

### スケジュールリスク

**リスク1: 外部リソース設定待ち**
- 影響度: 中
- 対策: 事前に権限申請、Week 3終了時に進捗確認

**リスク2: QA負荷**
- 影響度: 低
- 対策: Week 5からQA巻き込み、回帰テスト自動化

### 対策

- 毎週レビュー、計画フィードバック
- 重要タスクのペア作業
- リリース前にフェーズゲートレビュー

## 成功基準

### パフォーマンス
- 1000同時接続でp95レスポンス < 500ms
- エラー率 < 1%
- 再デプロイ時のダウンタイム < 1分

### セキュリティ
- OAuth 2.1 + JWTで認証必須
- 未認証アクセスは即座に拒否
- `pip-audit`でCritical脆弱性ゼロ

### 可用性
- Cloudflare Workers本番稼働
- 24時間監視体制
- Runbook完備
- 初期インシデント対応訓練完了

## 参考資料

- [Model Context Protocol Specification (2025-03-26)](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports)
- [FastMCP Remote Transport Documentation](https://gofastmcp.com/clients/transports)
- [Cloudflare MCP Server Guide](https://developers.cloudflare.com/agents/guides/remote-mcp-server/)
- [MCP Authorization Spec (OAuth 2.1)](https://modelcontextprotocol.io/specification/2025-06-18/basic/security_best_practices)
- [RFC 8707 - Resource Indicators](https://datatracker.ietf.org/doc/html/rfc8707)
- [Cloudflare Workers Pricing](https://www.cloudflare.com/plans/developer-platform/)
- [AWS Lambda Pricing Calculator](https://aws.amazon.com/lambda/pricing/)
- [FastMCP 2.3 Release: Streamable HTTP](https://www.jlowin.dev/blog/fastmcp-2-3-streamable-http)
