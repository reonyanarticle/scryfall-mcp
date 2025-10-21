# Authentication and Authorization

Remote MCP対応の認証・認可システム実装ガイド。

## 目次

1. [概要](#概要)
2. [認証フロー](#認証フロー)
3. [JWT（JSON Web Token）](#jwt-json-web-token)
4. [OAuth 2.1 + PKCE](#oauth-21--pkce)
5. [レート制限](#レート制限)
6. [セキュリティ設定](#セキュリティ設定)
7. [トラブルシューティング](#トラブルシューティング)
8. [参考資料](#参考資料)

---

## 概要

### システム構成

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

### コンポーネント

| コンポーネント | ファイル | 役割 |
|--------------|---------|------|
| **JWT Middleware** | `src/scryfall_mcp/auth/middleware.py` | JWT検証（ASGI middleware） |
| **OAuth Client** | `src/scryfall_mcp/auth/oauth.py` | OAuth 2.1フロー実装 |
| **Rate Limiter** | `src/scryfall_mcp/api/rate_limiter.py` | ユーザー別レート制限 |
| **Settings** | `src/scryfall_mcp/settings.py` | セキュリティ設定と検証 |

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

### 実装状況

| フェーズ | 機能 | 状態 |
|---------|------|------|
| Phase 1 | Streamable HTTP Transport | ✅ 完了 |
| Phase 2 | JWT検証、OAuth 2.1、レート制限 | ✅ 完了 |
| Phase 3 | トークンリフレッシュ、監査ログ | 🔄 未実装 |
| Phase 4 | E2E統合 | 🔄 未実装 |

---

## JWT (JSON Web Token)

### 概要

RFC 7519で定義された、クレーム（claim）を安全に転送するトークン形式。

**構造:**
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyMTIzIiwiaWF0IjoxNjkwMDAwMDAwLCJleHAiOjE2OTAwMDM2MDB9.signature
│─────────────── Header ──────────────│─────────────────── Payload ─────────────────────│─ Signature ─│
```

### 実装

#### Middleware設定

```python
from fastapi import FastAPI
from scryfall_mcp.auth.middleware import JWTValidationMiddleware
from scryfall_mcp.settings import get_settings

app = FastAPI()
app.add_middleware(JWTValidationMiddleware, settings=get_settings())
```

#### 検証フロー

1. **Bearer Token抽出**
   ```
   Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
                        ↓
                  トークン文字列を取得
   ```

2. **JWT検証**
   - 署名検証
   - 有効期限（exp）
   - 発行時刻（iat）
   - 有効開始時刻（nbf）

3. **ペイロード取得**
   ```python
   payload = {
       "sub": "user123",      # ユーザーID
       "iat": 1690000000,     # 発行時刻
       "exp": 1690003600,     # 有効期限（1時間）
       "nbf": 1690000000,     # 有効開始時刻
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

#### 自動検証

`validate_jwt_production_requirements`による起動時チェック：

```python
# OAuth有効時の検証
if self.oauth_enabled:
    # JWT secretが空 → エラー
    if not self.jwt_secret_key:
        raise ValueError("jwt_secret_key is required")

    # 32文字未満 → エラー
    if len(self.jwt_secret_key) < 32:
        raise ValueError("jwt_secret_key must be at least 32 characters")
```

### セキュリティ推奨設定

| 項目 | 推奨値 | 理由 |
|------|-------|------|
| **Secret Key** | 32文字以上 | ブルートフォース攻撃対策 |
| **Algorithm** | HS256 / RS256 | 標準的な署名方式 |
| **有効期限** | 1時間 | セキュリティとUXのバランス |
| **Refresh Token** | 7日間 | 長期セッション維持 |
| **Clock Skew** | 60秒 | 時刻ずれ許容範囲 |

**本番環境での禁止事項：**
- ❌ デフォルトsecret使用
- ❌ 32文字未満のsecret
- ❌ ログへのJWT出力
- ❌ HTTP通信（HTTPS必須）

---

## OAuth 2.1 + PKCE

### 概要

OAuth 2.0のベストプラクティスをまとめた最新仕様。主な改善：

- **PKCE必須化**（コード横取り攻撃対策）
- Implicit Flow廃止
- Refresh Token Rotation推奨
- リダイレクトURI完全一致必須化

### PKCE（Proof Key for Code Exchange）

RFC 7636で定義された、Authorization Code Flowのセキュリティ拡張。

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

### 実装

#### 1. Authorization URL生成

```python
from scryfall_mcp.auth.oauth import OAuthClient
from scryfall_mcp.settings import get_settings

oauth_client = OAuthClient(get_settings())

# PKCE付き認可URL生成
auth_url, code_verifier, state = await oauth_client.get_authorization_url(
    redirect_uri="https://your-app.example.com/callback",
    scope="openid profile email",
)

# code_verifierとstateをセッションに保存
# ユーザーをauth_urlにリダイレクト
```

#### 2. Authorization Code受け取り

コールバックURLで`code`と`state`を検証：

```python
# CSRF対策: stateの一致確認
if received_state != stored_state:
    raise ValueError("Invalid state")
```

#### 3. Token取得

```python
token = await oauth_client.exchange_code_for_token(
    code=authorization_code,
    redirect_uri="https://your-app.example.com/callback",
    code_verifier=stored_code_verifier,
)

# token.access_token: JWT
# token.refresh_token: リフレッシュトークン
# token.expires_in: 有効期限（秒）
```

#### 4. Token Refresh（Phase 3実装予定）

```python
new_token = await oauth_client.refresh_token(
    refresh_token=token.refresh_token
)
```

### 設定

#### 環境変数

```bash
# OAuth Provider設定
export OAUTH_ENABLED=true
export OAUTH_CLIENT_ID="your_client_id"
export OAUTH_AUTHORIZATION_URL="https://auth.provider.com/oauth/authorize"
export OAUTH_TOKEN_URL="https://auth.provider.com/oauth/token"

# JWT設定
export JWT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
export JWT_ALGORITHM="HS256"
```

#### 自動検証

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

### 2階層レート制限

Remote MCP環境では複数ユーザーが同じサーバーを共有するため、2階層でレート制限を実装：

```text
┌─────────────────────────────────────┐
│   Scryfall API (グローバル)         │
│     10 req/sec (75ms間隔)           │
└───────────────┬─────────────────────┘
                │
        ┌───────┴───────┐
        ▼               ▼
┌─────────────┐  ┌─────────────┐
│  User A     │  │  User B     │
│  100 req/min│  │  100 req/min│
└─────────────┘  └─────────────┘
```

### 実装

#### Backend抽象化

```python
from scryfall_mcp.api.rate_limiter import RateLimiterManager
from scryfall_mcp.api.rate_limit_backend import RedisRateLimitBackend, MemoryRateLimitBackend

# Redis（分散環境推奨）
import redis.asyncio as redis
redis_client = await redis.from_url("redis://localhost:6379")
backend = RedisRateLimitBackend(redis_client)
manager = RateLimiterManager(backend=backend)

# メモリ（開発環境）
backend = MemoryRateLimitBackend()
manager = RateLimiterManager(backend=backend)
```

#### 使用例

```python
from scryfall_mcp.api.exceptions import RateLimitExceededError

# ユーザー別レート制限
try:
    await manager.acquire_user_limit(user_id="user123", limit=100)
except RateLimitExceededError as e:
    # e.user_id, e.limit, e.retry_after, e.current_count
    raise

# Scryfall APIレート制限
await manager.acquire_scryfall_limit()

# API呼び出し
response = await scryfall_client.search_cards(query)
```

### Backend実装詳細

#### Redisキー構造

```text
rate_limit:user123
│         │       │
│         │       └─ User ID
│         └───────── Namespace
└─────────────────── Prefix

Value: 5           # リクエスト数
TTL: 45 seconds    # ウィンドウ残り時間
```

#### アルゴリズム

```python
async def increment_and_check(self, key: str, limit: int, window_seconds: int):
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

#### メモリBackend

LRU eviction付きの開発環境向け実装：

**特性:**

- ✅ Redis不要
- ✅ ゼロレイテンシー
- ⚠️ 単一プロセスのみ
- ⚠️ 再起動でリセット

### 設定

#### 環境変数

```bash
# Scryfall API (ms/req)
export SCRYFALL_RATE_LIMIT_MS=100  # 10 req/sec

# ユーザーAPI (req/min)
export USER_RATE_LIMIT_PER_MIN=100

# Redis（オプション）
export REDIS_HOST=localhost
export REDIS_PORT=6379
```

#### カスタマイズ

```python
# プレミアムユーザー
await manager.acquire_user_limit("premium_user", limit=200)

# 匿名ユーザー
await manager.acquire_user_limit("anonymous", limit=50)
```

### 監視

#### ログ

```python
import logging
logging.getLogger("scryfall_mcp.api.rate_limiter").setLevel(logging.DEBUG)

# 出力例:
# DEBUG: User user123 rate limit: 45/100
# WARNING: Redis unavailable, falling back to memory
```

#### Redis監視

```bash
redis-cli KEYS "rate_limit:*"
redis-cli GET "rate_limit:user123"
redis-cli TTL "rate_limit:user123"
```

---

## セキュリティ設定

### CORS

HTTP transportモード使用時は必須。

#### 自動検証

```python
# HTTP/Streamable HTTP使用時
if self.transport_mode in ("http", "streamable_http"):
    # 空の場合 → エラー
    if not self.allowed_origins:
        raise ValueError("allowed_origins is required for HTTP transport")

    # 本番環境でワイルドカード → 警告
    if "*" in self.allowed_origins and not self.debug:
            logger.warning(
                "SECURITY WARNING: CORS wildcard '*' is insecure in production"
            )

    return self
```

#### 推奨設定

```bash
# 本番環境
export ALLOWED_ORIGINS='["https://claude.ai", "https://app.example.com"]'

# 開発環境のみ
export ALLOWED_ORIGINS='["*"]'
export DEBUG=true
```

**原則:**

- ✅ 本番: 具体的なオリジン指定
- ❌ 本番: ワイルドカード禁止
- ✅ HTTPSのみ許可

### Transport別セキュリティ

| Transport | 認証 | CORS | TLS | 用途 |
|-----------|------|------|-----|------|
| **stdio** | 不要 | 不要 | 不要 | ローカル |
| **http** | 推奨 | 必須 | 推奨 | LAN |
| **streamable_http** | 必須 | 必須 | 必須 | 本番 |

### デプロイ前チェック

```bash
# 設定確認
uv run python -c "from scryfall_mcp.settings import get_settings; print(get_settings())"

# JWT生成
uv run python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## トラブルシューティング

### よくあるエラー

#### 1. JWT Secret未設定

```text
ValueError: jwt_secret_key is required when oauth_enabled=True
```

**解決:**

```bash
export JWT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
```

#### 2. Secret短すぎる

```text
ValueError: jwt_secret_key must be at least 32 characters
```

**解決:** 32文字以上を生成

```bash
python -c "import secrets; print(len(secrets.token_urlsafe(32)))"  # 43文字
```

#### 3. CORS未設定

```text
ValueError: allowed_origins is required for HTTP transport
```

**解決:**

```bash
export ALLOWED_ORIGINS='["https://your-app.example.com"]'
```

#### 4. ワイルドカードCORS

```text
SECURITY WARNING: CORS wildcard '*' is insecure in production
```

**解決:**

```bash
# 本番環境
export ALLOWED_ORIGINS='["https://claude.ai"]'
```

#### 5. JWT検証失敗

```text
401 Unauthorized: Invalid token: Signature verification failed
```

**デバッグ:**

```bash
# Secret確認
echo $JWT_SECRET_KEY

# JWTデコード
python -c "
from jose import jwt
token = sys.argv[1]
print(jwt.get_unverified_claims(token))
" "YOUR_JWT_TOKEN"
```

**解決:** サーバーとクライアントで同じ秘密鍵を使用

#### 6. Token有効期限切れ

```text
401 Unauthorized: Invalid token: Token has expired
```

**解決:** 新トークン取得（またはRefresh Token使用）

#### 7. Authorization header不足

```text
HTTPException: Authorization header missing
```

**解決:**

```bash
# 正しい形式
curl -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..." \
     https://your-server.example.com/search
```

#### 8. PKCE検証エラー

```text
OAuth error: invalid_grant - Code verifier mismatch
```

**原因:** `code_verifier`が一致しない

**デバッグ:**

```python
from scryfall_mcp.auth.oauth import OAuthClient
verifier, challenge = OAuthClient(settings).generate_pkce_pair()

# 検証
import base64, hashlib
expected = base64.urlsafe_b64encode(
    hashlib.sha256(verifier.encode()).digest()
).rstrip(b"=").decode()
assert challenge == expected
```

#### 9. レート制限超過

```text
429 Too Many Requests: Rate limit exceeded
Retry-After: 60
```

**解決:**

1. 60秒待機
2. リクエスト頻度削減
3. レート制限緩和リクエスト

**Redis接続失敗時:**

```text
WARNING: Redis unavailable, falling back to memory
```

影響: 単一プロセス内のみレート制限有効

**解決:**

```bash
redis-cli ping  # 接続確認

# Check Redis configuration
echo $REDIS_HOST
echo $REDIS_PORT

# Restart Redis
redis-server /etc/redis/redis.conf
```

---

### デバッグ

#### JWT検証

```python
from scryfall_mcp.auth.middleware import JWTValidationMiddleware
from scryfall_mcp.settings import get_settings
from jose import jwt
import time

settings = get_settings()
middleware = JWTValidationMiddleware(None, settings)

payload = {"sub": "test_user", "iat": int(time.time()), "exp": int(time.time()) + 3600}
token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

try:
    decoded = middleware._decode_and_verify_token(token)
    print("✅ JWT validation passed:", decoded)
except Exception as e:
    print("❌ JWT validation failed:", e)
```

#### PKCE検証

```python
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

#### レート制限

```python
import asyncio
from scryfall_mcp.api.rate_limiter import RateLimiterManager
from scryfall_mcp.api.rate_limit_backend import MemoryRateLimitBackend

async def test_rate_limiting():
    backend = MemoryRateLimitBackend()
    manager = RateLimiterManager(backend=backend)

    for i in range(150):
        try:
            await manager.acquire_user_limit("user123", limit=100)
            print(f"✅ Request {i+1}")
        except Exception as e:
            print(f"❌ Blocked: {e}")
            break

asyncio.run(test_rate_limiting())
```

---

## 参考資料

### 仕様

- OAuth 2.1: <https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-10>
- PKCE (RFC 7636): <https://datatracker.ietf.org/doc/html/rfc7636>
- JWT (RFC 7519): <https://datatracker.ietf.org/doc/html/rfc7519>
- Bearer Token (RFC 6750): <https://datatracker.ietf.org/doc/html/rfc6750>

### ライブラリ

- python-jose: <https://python-jose.readthedocs.io/>
- FastAPI: <https://fastapi.tiangolo.com/advanced/middleware/>
- httpx: <https://www.python-httpx.org/>
- redis-py: <https://redis-py.readthedocs.io/>

### 内部ドキュメント

- 実装計画: `docs/REMOTE-MCP-IMPLEMENTATION-PLAN.md`
- 設定ガイド: `docs/CONFIGURATION.md`
- API仕様: `docs/API-REFERENCE.md`
- 開発ガイド: `docs/DEVELOPMENT.md`

---

**最終更新:** 2025-10-20
**ステータス:** Phase 2実装完了、Phase 3開発待ち
