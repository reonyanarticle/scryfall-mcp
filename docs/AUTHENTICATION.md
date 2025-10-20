# Authentication and Authorization

Scryfall MCP ServerのRemote MCP対応における認証・認可システムの実装ガイド。

## 目次

1. [概要](#概要)
2. [認証フロー](#認証フロー)
3. [JWT（JSON Web Token）](#jwt-json-web-token)
4. [OAuth 2.1 with PKCE](#oauth-21-with-pkce)
5. [レート制限](#レート制限)
6. [セキュリティ設定](#セキュリティ設定)
7. [トラブルシューティング](#トラブルシューティング)

---

## 概要

### 認証システムの構成

Scryfall MCP Serverは、Remote MCP接続のセキュリティを確保するために以下のコンポーネントを提供します。

```
┌─────────────────┐
│   MCP Client    │
│  (Claude Code)  │
└────────┬────────┘
         │ 1. Authorization Request
         ▼
┌─────────────────┐
│ OAuth Provider  │
│ (Auth Server)   │
└────────┬────────┘
         │ 2. Authorization Code + PKCE
         ▼
┌─────────────────┐
│   MCP Client    │
└────────┬────────┘
         │ 3. Exchange Code for JWT
         ▼
┌─────────────────┐
│  MCP Server     │
│ (This Server)   │
└────────┬────────┘
         │ 4. JWT Validation
         ▼
┌─────────────────┐
│ Protected Tools │
│  (Scryfall API) │
└─────────────────┘
```

### 主要コンポーネント

| コンポーネント | ファイル | 役割 |
|--------------|---------|------|
| **JWT Middleware** | `src/scryfall_mcp/auth/middleware.py` | ASGI middleware for JWT validation |
| **OAuth Client** | `src/scryfall_mcp/auth/oauth.py` | OAuth 2.1 flow implementation |
| **Rate Limiter** | `src/scryfall_mcp/api/rate_limiter.py` | Per-user rate limiting |
| **Settings** | `src/scryfall_mcp/settings.py` | Security configuration & validation |

---

## 認証フロー

### 完全な認証フロー

```mermaid
sequenceDiagram
    participant User
    participant Client as MCP Client
    participant Server as MCP Server
    participant Auth as OAuth Provider
    participant API as Scryfall API

    User->>Client: Connect to Remote MCP
    Client->>Server: Request authentication
    Server->>Client: Return authorization URL
    Client->>User: Open browser for login
    User->>Auth: Login & authorize
    Auth->>Client: Authorization code (with PKCE)
    Client->>Server: Exchange code for JWT
    Server->>Auth: Verify code + code_verifier
    Auth->>Server: Issue JWT tokens
    Server->>Client: Return access_token & refresh_token

    loop Authenticated Requests
        Client->>Server: MCP request + JWT
        Server->>Server: Validate JWT
        Server->>Server: Check rate limit
        Server->>API: Forward request
        API->>Server: Response
        Server->>Client: MCP response
    end

    Client->>Server: Refresh token (when expired)
    Server->>Auth: Validate refresh_token
    Auth->>Server: New access_token
    Server->>Client: Updated JWT
```

### フェーズ別の実装状況

| フェーズ | 機能 | 状態 |
|---------|------|------|
| Phase 1 | Streamable HTTP Transport | ✅ 完了 |
| Phase 2 | JWT Validation, OAuth 2.1, Rate Limiting | ✅ 完了 |
| Phase 3 | Token Refresh, Audit Logging | 🔄 未実装 |
| Phase 4 | End-to-End Integration | 🔄 未実装 |

---

## JWT (JSON Web Token)

### JWTとは

JWT (JSON Web Token) は、RFC 7519で定義された、安全にクレーム（claim）を転送するためのトークン形式です。

**構造:**
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyMTIzIiwiaWF0IjoxNjkwMDAwMDAwLCJleHAiOjE2OTAwMDM2MDB9.signature
│─────────────── Header ──────────────│─────────────────── Payload ─────────────────────│─ Signature ─│
```

### JWT検証の実装

#### Middleware構成

```python
from fastapi import FastAPI
from scryfall_mcp.auth.middleware import JWTValidationMiddleware
from scryfall_mcp.settings import get_settings

app = FastAPI()
settings = get_settings()

# Add JWT validation middleware
app.add_middleware(JWTValidationMiddleware, settings=settings)
```

#### 検証プロセス

1. **Bearer Token抽出** (`_extract_bearer_token`)
   ```
   Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
                        ↓
                  Extract token string
   ```

2. **JWT検証** (`_decode_and_verify_token`)
   - 署名検証（Signature verification）
   - 有効期限チェック（exp: expiration time）
   - 発行時刻チェック（iat: issued at）
   - 有効開始時刻チェック（nbf: not before）

3. **ユーザー情報の取り出し**
   ```python
   payload = {
       "sub": "user123",      # Subject (user ID)
       "iat": 1690000000,     # Issued at
       "exp": 1690003600,     # Expiration (1 hour)
       "nbf": 1690000000,     # Not before
   }
   ```

### JWT設定

#### 必須環境変数

```bash
# JWT Secret Key (32文字以上必須)
export JWT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"

# JWT Algorithm
export JWT_ALGORITHM="HS256"

# OAuth有効化
export OAUTH_ENABLED=true
```

#### Settings検証

`src/scryfall_mcp/settings.py` の `validate_jwt_production_requirements` により、以下が自動検証されます：

```python
@model_validator(mode="after")
def validate_jwt_production_requirements(self) -> Settings:
    """Ensure JWT secret is configured when OAuth is enabled."""
    if self.oauth_enabled:
        # JWT secret必須
        if not self.jwt_secret_key:
            raise ValueError("jwt_secret_key is required")

        # 32文字以上必須（セキュリティ要件）
        if len(self.jwt_secret_key) < 32:
            raise ValueError("jwt_secret_key must be at least 32 characters")

    return self
```

### セキュリティベストプラクティス

| 項目 | 推奨値 | 理由 |
|------|-------|------|
| **Secret Key長** | 32文字以上 | ブルートフォース攻撃への耐性 |
| **Algorithm** | HS256 or RS256 | HMAC-SHA256 or RSA-SHA256 |
| **Token有効期限** | 1時間 | セキュリティとUXのバランス |
| **Refresh Token** | 7日間 | 長期セッション維持 |
| **Clock Skew** | 60秒 | サーバー間の時刻ずれ許容 |

**重要**: 本番環境では以下を絶対に避けること：
- ❌ デフォルト値のJWT secret
- ❌ 短いsecret key（32文字未満）
- ❌ ログへのJWT出力
- ❌ HTTPでのJWT送信（HTTPS必須）

---

## OAuth 2.1 with PKCE

### OAuth 2.1とは

OAuth 2.1は、OAuth 2.0のベストプラクティスをまとめた最新仕様です。主な改善点：

- **PKCE必須化** (Proof Key for Code Exchange)
- Implicit Flowの廃止
- Refresh Token Rotationの推奨
- リダイレクトURI完全一致の必須化

### PKCE (Proof Key for Code Exchange)

PKCE (RFC 7636) は、Authorization Code Flowにおけるコード横取り攻撃を防ぐための拡張仕様です。

#### PKCEフロー

```
1. Client generates code_verifier (random 43-128 chars)
   code_verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"

2. Client computes code_challenge (SHA-256 hash)
   code_challenge = BASE64URL(SHA256(code_verifier))
                  = "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"

3. Authorization Request (with code_challenge)
   GET /authorize?response_type=code
                 &client_id=CLIENT_ID
                 &redirect_uri=REDIRECT_URI
                 &code_challenge=E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM
                 &code_challenge_method=S256
                 &state=RANDOM_STATE

4. Authorization Server returns code
   https://redirect-uri.example.com/callback?code=AUTH_CODE&state=RANDOM_STATE

5. Token Request (with code_verifier)
   POST /token
   {
       "grant_type": "authorization_code",
       "code": "AUTH_CODE",
       "redirect_uri": "REDIRECT_URI",
       "code_verifier": "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
   }

6. Authorization Server validates:
   - SHA256(code_verifier) == stored code_challenge
   - Returns access_token if valid
```

### 実装例

#### Step 1: Authorization URL生成

```python
from scryfall_mcp.auth.oauth import OAuthClient
from scryfall_mcp.settings import get_settings

settings = get_settings()
oauth_client = OAuthClient(settings)

# Generate authorization URL with PKCE
auth_url, code_verifier, state = await oauth_client.get_authorization_url(
    redirect_uri="https://your-app.example.com/callback",
    scope="openid profile email",
)

# Store code_verifier and state securely (e.g., session storage)
# Redirect user to auth_url
print(f"Visit: {auth_url}")
```

生成されるURL例：
```
https://auth.example.com/authorize?
  response_type=code&
  client_id=YOUR_CLIENT_ID&
  redirect_uri=https%3A%2F%2Fyour-app.example.com%2Fcallback&
  code_challenge=E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM&
  code_challenge_method=S256&
  state=RANDOM_STATE_123&
  scope=openid+profile+email
```

#### Step 2: Authorization Codeの受け取り

ユーザーがログインすると、以下のURLにリダイレクトされます：

```
https://your-app.example.com/callback?
  code=AUTHORIZATION_CODE_123&
  state=RANDOM_STATE_123
```

**検証項目:**
1. `state` パラメーターが元の値と一致するか（CSRF対策）
2. `code` パラメーターが存在するか

#### Step 3: Tokenの取得

```python
# Exchange authorization code for tokens
token = await oauth_client.exchange_code_for_token(
    code="AUTHORIZATION_CODE_123",
    redirect_uri="https://your-app.example.com/callback",
    code_verifier=code_verifier,  # From Step 1
)

# token.access_token: JWT access token
# token.refresh_token: Refresh token (optional)
# token.expires_in: Token lifetime in seconds
```

#### Step 4: Token Refresh（Phase 3で実装予定）

```python
# Refresh expired access token
new_token = await oauth_client.refresh_token(
    refresh_token=token.refresh_token
)
```

### OAuth設定

#### 環境変数

```bash
# OAuth Provider Configuration
export OAUTH_ENABLED=true
export OAUTH_CLIENT_ID="your_client_id_from_provider"
export OAUTH_CLIENT_SECRET="your_client_secret_from_provider"  # 将来実装
export OAUTH_AUTHORIZATION_URL="https://auth.provider.com/oauth/authorize"
export OAUTH_TOKEN_URL="https://auth.provider.com/oauth/token"

# JWT Configuration (for token validation)
export JWT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
export JWT_ALGORITHM="HS256"
```

#### Settings検証

OAuth有効時に以下が自動検証されます（`validate_jwt_production_requirements`）：

```python
if oauth_enabled:
    assert jwt_secret_key, "JWT secret required"
    assert len(jwt_secret_key) >= 32, "Secret too short"
```

### セキュリティ考慮事項

| リスク | 対策 | 実装状況 |
|--------|------|---------|
| **コード横取り攻撃** | PKCE (RFC 7636) | ✅ 実装済み |
| **CSRF攻撃** | state parameter | ✅ 実装済み |
| **トークン漏洩** | HTTPS必須、短い有効期限 | ✅ 設定で対応 |
| **リプレイ攻撃** | 使用済みcodeの無効化 | 🔄 Provider側で実装 |
| **トークンリフレッシュ** | Refresh Token Rotation | 🔄 Phase 3で実装予定 |

**重要な実装詳細:**

1. **code_verifierの生成** (`generate_pkce_pair`)
   ```python
   # 43-128文字のランダム文字列（RFC 7636準拠）
   code_verifier = secrets.token_urlsafe(43)  # 43 chars minimum
   ```

2. **code_challengeの計算**
   ```python
   # S256メソッド（SHA-256ハッシュ）
   verifier_bytes = code_verifier.encode("ascii")
   challenge_digest = hashlib.sha256(verifier_bytes).digest()
   code_challenge = base64.urlsafe_b64encode(challenge_digest).rstrip(b"=").decode()
   ```

3. **stateの生成**
   ```python
   # CSRF対策用のランダム文字列
   state = secrets.token_urlsafe(32)
   ```

---

## レート制限

### 概要

Remote MCP環境では、複数のユーザーが同じサーバーを共有するため、以下の2階層のレート制限を実装しています。

```
┌─────────────────────────────────────┐
│   Global Scryfall API Rate Limit   │
│     10 requests/second (75ms間隔)   │
└───────────────┬─────────────────────┘
                │
        ┌───────┴───────┐
        ▼               ▼
┌─────────────┐  ┌─────────────┐
│  User A     │  │  User B     │
│  100 req/min│  │  100 req/min│
└─────────────┘  └─────────────┘
```

### RateLimiterManagerの実装

#### アーキテクチャ

```python
from scryfall_mcp.api.rate_limiter import RateLimiterManager

# Redis利用時（分散環境推奨）
import redis
redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)
manager = RateLimiterManager(redis_client=redis_client)

# メモリのみ利用時（開発環境）
manager = RateLimiterManager()  # Automatic fallback to memory
```

#### 使用例

```python
from fastapi import HTTPException

# User-specific rate limiting
try:
    await manager.acquire_user_limit(
        user_id="user123",
        limit=100,  # 100 requests per minute
    )
except HTTPException as e:
    # HTTP 429 Too Many Requests
    # Retry-After: 60 (seconds)
    raise

# Global Scryfall API rate limiting
await manager.acquire_scryfall_limit()

# Now safe to make API request
response = await scryfall_client.search_cards(query)
```

### Redis実装の詳細

#### Redisキー構造

```
rate_limit:user123
│         │       │
│         │       └─ User ID
│         └───────── Namespace
└─────────────────── Prefix

Value: 5           # Current request count
TTL: 45 seconds    # Remaining time in window
```

#### アルゴリズム

```python
async def _acquire_redis(self, user_id: str, limit: int) -> None:
    """Redis-based rate limiting with sliding window."""
    key = f"rate_limit:{user_id}"

    # Increment counter
    current = await redis.incr(key)

    # Set TTL on first request (60 second window)
    if current == 1:
        await redis.expire(key, 60)

    # Check limit
    if current > limit:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": "60"},
        )
```

### メモリフォールバック

Redis障害時、自動的にメモリベースのレート制限に切り替わります。

```python
async def acquire_user_limit(self, user_id: str, limit: int) -> None:
    """Acquire rate limit with automatic fallback."""
    if self._use_redis:
        try:
            await self._acquire_redis(user_id, limit)
        except Exception:
            logger.warning("Redis unavailable, falling back to memory")
            self._use_redis = False  # Disable Redis for this instance
            await self._acquire_memory(user_id, limit)
    else:
        await self._acquire_memory(user_id, limit)
```

**メモリ実装の特性:**
- ✅ Redis不要（開発環境に最適）
- ✅ ゼロレイテンシー
- ⚠️ 単一プロセスのみ有効
- ⚠️ 再起動時にカウンターリセット

### レート制限設定

#### 環境変数

```bash
# Scryfall API rate limit (ms between requests)
export SCRYFALL_RATE_LIMIT_MS=100  # 100ms = 10 req/sec (Scryfall default)

# User API rate limit (requests per minute)
export USER_RATE_LIMIT_PER_MIN=100  # Default: 100 req/min per user

# Redis configuration (optional)
export REDIS_HOST=localhost
export REDIS_PORT=6379
export REDIS_DB=0
```

#### カスタマイズ例

```python
# High-priority users: 200 req/min
await manager.acquire_user_limit("premium_user", limit=200)

# Anonymous users: 50 req/min
await manager.acquire_user_limit("anonymous", limit=50)
```

### 監視とデバッグ

#### ログ出力

```python
import logging

logger = logging.getLogger("scryfall_mcp.api.rate_limiter")
logger.setLevel(logging.DEBUG)

# Output:
# DEBUG: User user123 rate limit: 45/100 requests used
# WARNING: Redis unavailable, falling back to memory-based rate limiting
# INFO: User user123 rate limit exceeded (100/100)
```

#### Redisモニタリング

```bash
# Check current rate limit keys
redis-cli KEYS "rate_limit:*"

# Check specific user
redis-cli GET "rate_limit:user123"
redis-cli TTL "rate_limit:user123"

# Monitor real-time
redis-cli MONITOR | grep "rate_limit"
```

---

## セキュリティ設定

### CORS (Cross-Origin Resource Sharing)

HTTP transportモード使用時、CORS設定が必須です。

#### Settings検証

```python
@model_validator(mode="after")
def validate_cors_production_requirements(self) -> Settings:
    """Ensure CORS is properly configured for HTTP transport."""
    if self.transport_mode in ("http", "streamable_http"):
        # CORS設定必須
        if not self.allowed_origins:
            raise ValueError("allowed_origins is required for HTTP transport")

        # Wildcard警告（本番環境）
        if "*" in self.allowed_origins and not self.debug:
            logger.warning(
                "SECURITY WARNING: CORS wildcard '*' is insecure in production"
            )

    return self
```

#### 推奨設定

```bash
# Production (specific origins only)
export ALLOWED_ORIGINS='["https://claude.ai", "https://app.example.com"]'

# Development (allow all - DEBUG MODE ONLY)
export ALLOWED_ORIGINS='["*"]'
export DEBUG=true
```

**セキュリティ原則:**
- ✅ 本番環境では具体的なオリジンを指定
- ❌ 本番環境でワイルドカード `*` は絶対に使用しない
- ✅ HTTPSのみ許可（HTTPは拒否）

### Transport Mode別のセキュリティ

| Transport | 認証 | CORS | TLS | 用途 |
|-----------|------|------|-----|------|
| **stdio** | 不要 | 不要 | 不要 | ローカル開発 |
| **http** | 推奨 | 必須 | 推奨 | LAN内サーバー |
| **streamable_http** | 必須 | 必須 | 必須 | 本番環境 |

### 本番環境チェックリスト

起動時に以下が自動検証されます：

```python
# settings.py validators
✅ JWT_SECRET_KEY: 32文字以上
✅ OAUTH_ENABLED: JWT設定が揃っているか
✅ ALLOWED_ORIGINS: ワイルドカード使用時に警告
✅ TRANSPORT_MODE: HTTP時にCORS設定必須
```

**デプロイ前の確認:**

```bash
# 1. 環境変数チェック
uv run python -c "from scryfall_mcp.settings import get_settings; print(get_settings())"

# 2. セキュリティ検証
uv run python -c "
from scryfall_mcp.settings import Settings
settings = Settings(
    oauth_enabled=True,
    transport_mode='streamable_http',
    allowed_origins=['https://app.example.com'],
    jwt_secret_key='YOUR_32_CHAR_SECRET_HERE'
)
print('✅ Security validation passed')
"

# 3. JWT生成テスト
uv run python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## トラブルシューティング

### よくあるエラー

#### 1. JWT Secret Key関連

**エラー:**
```
ValueError: jwt_secret_key is required when oauth_enabled=True
```

**原因:** OAuth有効化時にJWT秘密鍵が未設定

**解決:**
```bash
export JWT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
```

---

**エラー:**
```
ValueError: jwt_secret_key must be at least 32 characters for security
```

**原因:** JWT秘密鍵が短すぎる

**解決:** 32文字以上の秘密鍵を生成
```bash
python -c "import secrets; print(len(secrets.token_urlsafe(32)))"  # 43 chars
```

---

#### 2. CORS関連

**エラー:**
```
ValueError: allowed_origins is required for HTTP transport
```

**原因:** HTTP transport使用時にCORS未設定

**解決:**
```bash
export ALLOWED_ORIGINS='["https://your-app.example.com"]'
```

---

**警告:**
```
SECURITY WARNING: CORS wildcard '*' is insecure in production
```

**原因:** 本番環境でワイルドカードCORS使用

**解決:** 具体的なオリジンを指定
```bash
# Before (insecure)
export ALLOWED_ORIGINS='["*"]'

# After (secure)
export ALLOWED_ORIGINS='["https://claude.ai", "https://app.example.com"]'
```

---

#### 3. JWT検証エラー

**エラー:**
```
401 Unauthorized: Invalid token: Signature verification failed
```

**原因:** JWT署名が無効（秘密鍵の不一致）

**デバッグ:**
```bash
# Check JWT secret consistency
echo $JWT_SECRET_KEY

# Decode JWT (without verification)
python -c "
import sys
from jose import jwt
token = sys.argv[1]
print(jwt.get_unverified_claims(token))
" "YOUR_JWT_TOKEN"
```

**解決:** サーバーとクライアントで同じ秘密鍵を使用

---

**エラー:**
```
401 Unauthorized: Invalid token: Token has expired
```

**原因:** JWTの有効期限切れ

**解決:**
1. 新しいトークンを取得
2. Refresh Tokenを使用（Phase 3で実装予定）

---

#### 4. OAuth関連

**エラー:**
```
HTTPException: Authorization header missing
```

**原因:** Bearer tokenがリクエストヘッダーにない

**解決:**
```bash
# Correct format
curl -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..." \
     https://your-server.example.com/search

# Incorrect (no "Bearer" prefix)
curl -H "Authorization: eyJhbGciOiJIUzI1NiIs..." \
     https://your-server.example.com/search
```

---

**エラー:**
```
OAuth error: invalid_grant - Code verifier mismatch
```

**原因:** PKCEの`code_verifier`が一致しない

**デバッグ:**
```python
# Check code_verifier/challenge generation
from scryfall_mcp.auth.oauth import OAuthClient
client = OAuthClient(settings)
verifier, challenge = client.generate_pkce_pair()

# Verify challenge is correctly computed
import base64, hashlib
expected = base64.urlsafe_b64encode(
    hashlib.sha256(verifier.encode()).digest()
).rstrip(b"=").decode()
assert challenge == expected, "PKCE computation error"
```

---

#### 5. レート制限関連

**エラー:**
```
429 Too Many Requests: Rate limit exceeded
Retry-After: 60
```

**原因:** レート制限超過（100 requests/minute）

**解決:**
1. 60秒待機してリトライ
2. リクエスト頻度を下げる
3. レート制限の緩和をリクエスト

---

**警告:**
```
WARNING: Redis unavailable, falling back to memory-based rate limiting
```

**原因:** Redis接続失敗

**影響:**
- 単一プロセス内のみレート制限有効
- 水平スケール時にレート制限が独立

**解決:**
```bash
# Check Redis connectivity
redis-cli ping
# PONG

# Check Redis configuration
echo $REDIS_HOST
echo $REDIS_PORT

# Restart Redis
redis-server /etc/redis/redis.conf
```

---

### デバッグコマンド

#### JWT検証テスト

```python
# test_jwt_validation.py
from scryfall_mcp.auth.middleware import JWTValidationMiddleware
from scryfall_mcp.settings import get_settings
from jose import jwt
import time

settings = get_settings()
middleware = JWTValidationMiddleware(None, settings)

# Create test token
payload = {
    "sub": "test_user",
    "iat": int(time.time()),
    "exp": int(time.time()) + 3600,
}
token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

# Test validation
try:
    decoded = middleware._decode_and_verify_token(token)
    print("✅ JWT validation passed:", decoded)
except Exception as e:
    print("❌ JWT validation failed:", e)
```

#### OAuth PKCE検証

```python
# test_pkce.py
from scryfall_mcp.auth.oauth import OAuthClient
from scryfall_mcp.settings import get_settings
import base64, hashlib

settings = get_settings()
client = OAuthClient(settings)

# Generate PKCE pair
verifier, challenge = client.generate_pkce_pair()

print(f"Code Verifier: {verifier}")
print(f"Code Challenge: {challenge}")

# Verify challenge computation
expected = base64.urlsafe_b64encode(
    hashlib.sha256(verifier.encode()).digest()
).rstrip(b"=").decode()

if challenge == expected:
    print("✅ PKCE generation correct")
else:
    print(f"❌ PKCE mismatch: expected {expected}, got {challenge}")
```

#### レート制限テスト

```python
# test_rate_limiter.py
import asyncio
from scryfall_mcp.api.rate_limiter import RateLimiterManager

async def test_rate_limiting():
    manager = RateLimiterManager()  # Memory-based

    # Simulate 150 requests from user123
    for i in range(150):
        try:
            await manager.acquire_user_limit("user123", limit=100)
            print(f"✅ Request {i+1} allowed")
        except Exception as e:
            print(f"❌ Request {i+1} blocked: {e}")
            break

asyncio.run(test_rate_limiting())
```

---

## 参考資料

### 仕様書

- **OAuth 2.1**: https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-10
- **PKCE (RFC 7636)**: https://datatracker.ietf.org/doc/html/rfc7636
- **JWT (RFC 7519)**: https://datatracker.ietf.org/doc/html/rfc7519
- **Bearer Token (RFC 6750)**: https://datatracker.ietf.org/doc/html/rfc6750

### ライブラリ

- **python-jose**: https://python-jose.readthedocs.io/
- **FastAPI**: https://fastapi.tiangolo.com/advanced/middleware/
- **httpx**: https://www.python-httpx.org/
- **redis-py**: https://redis-py.readthedocs.io/

### 内部ドキュメント

- **実装計画**: `docs/REMOTE-MCP-IMPLEMENTATION-PLAN.md`
- **設定ガイド**: `docs/CONFIGURATION.md`
- **API仕様**: `docs/API-REFERENCE.md`
- **開発ガイド**: `docs/DEVELOPMENT.md`

---

**最終更新:** 2025-10-20
**ステータス:** Phase 2実装完了、Phase 3開発待ち
