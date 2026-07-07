# 設定ガイド

## 環境変数

### 必須設定

#### User-Agent設定（必須）

| 変数名 | デフォルト | 説明 |
|--------|-----------|------|
| `SCRYFALL_MCP_USER_AGENT` | *(なし)* | User-Agent文字列（連絡先情報を含む）|

**形式**: `"YourApp/1.0 (contact-info)"`

**連絡先情報の例**:
- メールアドレス: `YourApp/1.0 (yourname@example.com)`
- GitHubリポジトリ: `YourApp/1.0 (https://github.com/username/repo)`
- その他URL: `YourApp/1.0 (https://example.com/contact)`

**重要**: この設定はScryfall API利用に必須です。未設定の場合、検索ツールは設定を促すメッセージを返します。

**Claude Desktop での設定例**:
```json
{
  "mcpServers": {
    "scryfall": {
      "command": "uv",
      "args": ["--directory", "/path/to/scryfall-mcp", "run", "scryfall-mcp"],
      "env": {
        "SCRYFALL_MCP_USER_AGENT": "MyApp/1.0 (myemail@example.com)"
      }
    }
  }
}
```

### API設定

| 変数名 | デフォルト | 説明 |
|--------|-----------|------|
| `SCRYFALL_MCP_BASE_URL` | `https://api.scryfall.com` | Scryfall APIのベースURL |
| `SCRYFALL_MCP_RATE_LIMIT_MS` | `100` | リクエスト間隔（ミリ秒） |
| `SCRYFALL_MCP_TIMEOUT_SECONDS` | `30` | HTTPタイムアウト（秒） |
| `SCRYFALL_MCP_MAX_RETRIES` | `5` | 最大リトライ回数 |

### 多言語化設定

| 変数名 | デフォルト | 説明 |
|--------|-----------|------|
| `SCRYFALL_MCP_DEFAULT_LOCALE` | `en` | デフォルト言語 |
| `SCRYFALL_MCP_SUPPORTED_LOCALES` | `["en", "ja"]` | サポート言語 |
| `SCRYFALL_MCP_FALLBACK_LOCALE` | `en` | フォールバック言語 |

### キャッシュ設定

| 変数名 | デフォルト | 説明 |
|--------|-----------|------|
| `SCRYFALL_MCP_CACHE_ENABLED` | `true` | キャッシュ有効化 |
| `SCRYFALL_MCP_CACHE_BACKEND` | `memory` | キャッシュバックエンド |
| `SCRYFALL_MCP_CACHE_MAX_SIZE` | `1000` | メモリキャッシュ最大サイズ |

### Redis設定（Redis使用時）

| 変数名 | デフォルト | 説明 |
|--------|-----------|------|
| `SCRYFALL_MCP_REDIS_URL` | `null` | Redis接続URL |

### TTL設定

Scryfallの推奨に従い、最低24時間のキャッシュを設定しています。

| 変数名 | デフォルト | 最小値 | 説明 |
|--------|-----------|--------|------|
| `SCRYFALL_MCP_CACHE_TTL_SEARCH` | `86400` (24時間) | 86400 | 検索結果TTL（秒）※Scryfall推奨 |
| `SCRYFALL_MCP_CACHE_TTL_CARD` | `86400` (24時間) | 3600 | カード詳細TTL（秒） |
| `SCRYFALL_MCP_CACHE_TTL_SET` | `604800` (1週間) | 86400 | セット情報TTL（秒） |
| `SCRYFALL_MCP_CACHE_TTL_DEFAULT` | `86400` (24時間) | 86400 | デフォルトTTL（秒）※Scryfall推奨 |

### サーキットブレーカー設定

| 変数名 | デフォルト | 説明 |
|--------|-----------|------|
| `SCRYFALL_MCP_CIRCUIT_BREAKER_FAILURE_THRESHOLD` | `5` | 失敗閾値 |
| `SCRYFALL_MCP_CIRCUIT_BREAKER_RECOVERY_TIMEOUT` | `60` | 復旧タイムアウト（秒） |

### ログ設定

| 変数名 | デフォルト | 説明 |
|--------|-----------|------|
| `SCRYFALL_MCP_LOG_LEVEL` | `INFO` | ログレベル |

### 開発設定

| 変数名 | デフォルト | 説明 |
|--------|-----------|------|
| `SCRYFALL_MCP_DEBUG` | `false` | デバッグモード |

### 認証設定（Remote MCP使用時のみ）

認証機能を使うには `auth` extra が必要です（`pip install 'scryfall-mcp[auth]'`）。詳細は [AUTHENTICATION.md](AUTHENTICATION.md) を参照。

| 変数名 | デフォルト | 説明 |
|--------|-----------|------|
| `SCRYFALL_MCP_OAUTH_ENABLED` | `false` | OAuth 2.1 / JWT認証の有効化 |
| `SCRYFALL_MCP_JWT_SECRET_KEY` | *(なし)* | JWT署名鍵（32文字以上・SecretStrとして扱われrepr出力でマスクされる） |
| `SCRYFALL_MCP_JWT_ALGORITHM` | `HS256` | JWT署名アルゴリズム |
| `SCRYFALL_MCP_JWT_AUDIENCE` | `scryfall-mcp-api` | 検証するaudienceクレーム（API Gateway authorizerと一致させる。空文字で無効化） |
| `SCRYFALL_MCP_JWT_ISSUER` | *(なし)* | 検証するissuerクレーム（空文字で無効化） |
| `SCRYFALL_MCP_EMAIL_AUTH_ENABLED` | `false` | メール認証（OAuthの簡易代替）の有効化 |

## CLIセットアップウィザード（スタンドアローン利用時）

MCPクライアント経由では環境変数（`SCRYFALL_MCP_USER_AGENT`）での設定を推奨しますが、スタンドアローンで実行する場合は対話式ウィザードで設定できます。

```bash
scryfall-mcp setup    # 対話式セットアップ（User-Agentのバリデーション付き）
scryfall-mcp config   # 現在の設定と設定ファイルの場所を表示
scryfall-mcp reset    # 設定を削除して初期化
scryfall-mcp serve    # サーバー起動（サブコマンド省略時も serve が実行される）
```

設定ファイル（`config.json`）はプラットフォーム別の設定ディレクトリに保存されます:

| OS | 設定ディレクトリ |
|----|----------------|
| macOS | `~/Library/Application Support/scryfall-mcp/` |
| Linux | `~/.config/scryfall-mcp/` |
| Windows | `%APPDATA%\Local\scryfall-mcp\` |

連絡先情報（メールアドレス等）を含むため、設定ディレクトリは `0o700`、設定ファイルは `0o600` のパーミッションで作成されます（所有者のみアクセス可能）。

## 設定例

### 基本設定

```bash
# .env ファイル
SCRYFALL_MCP_USER_AGENT="MyApp/1.0 (myemail@example.com)"
SCRYFALL_MCP_DEFAULT_LOCALE=ja
SCRYFALL_MCP_RATE_LIMIT_MS=150
SCRYFALL_MCP_CACHE_ENABLED=true
```

### プロダクション設定

```bash
# プロダクション環境
SCRYFALL_MCP_USER_AGENT="ProductionApp/1.0 (admin@example.com)"
SCRYFALL_MCP_LOG_LEVEL=WARNING
SCRYFALL_MCP_CACHE_BACKEND=redis
SCRYFALL_MCP_REDIS_URL=redis://localhost:6379
SCRYFALL_MCP_RATE_LIMIT_MS=75
```

### 開発設定

```bash
# 開発環境
SCRYFALL_MCP_USER_AGENT="DevApp/1.0 (dev@example.com)"
SCRYFALL_MCP_DEBUG=true
SCRYFALL_MCP_LOG_LEVEL=DEBUG
SCRYFALL_MCP_CACHE_ENABLED=false
```

## パフォーマンスチューニング

### レート制限の調整

```bash
# 保守的（安全）
SCRYFALL_MCP_RATE_LIMIT_MS=150

# 標準
SCRYFALL_MCP_RATE_LIMIT_MS=100

# アグレッシブ（非推奨）
SCRYFALL_MCP_RATE_LIMIT_MS=75
```

### キャッシュの最適化

```bash
# メモリ使用量を抑制
SCRYFALL_MCP_CACHE_MAX_SIZE=500
SCRYFALL_MCP_CACHE_TTL_SEARCH=86400  # 最低TTL（24時間）

# 長期キャッシュを優先（高速化）
SCRYFALL_MCP_CACHE_MAX_SIZE=2000
SCRYFALL_MCP_CACHE_TTL_SEARCH=172800  # 48時間
```

※ `SCRYFALL_MCP_CACHE_TTL_SEARCH` と `SCRYFALL_MCP_CACHE_TTL_DEFAULT` は24時間未満に設定できません。

## トラブルシューティング

### よくある設定問題

#### User-Agent未設定エラー

**症状**: 検索ツールが「User-Agent Configuration Required」メッセージを返す

**対処**: 環境変数を設定
```bash
# Claude Desktop の場合: claude_desktop_config.json に追加
{
  "mcpServers": {
    "scryfall": {
      "env": {
        "SCRYFALL_MCP_USER_AGENT": "YourApp/1.0 (your-email@example.com)"
      }
    }
  }
}

# 環境変数として直接設定する場合
export SCRYFALL_MCP_USER_AGENT="YourApp/1.0 (your-email@example.com)"
```

#### レート制限エラー

```bash
# 対処: 間隔を長くする
SCRYFALL_MCP_RATE_LIMIT_MS=200
```

#### メモリ不足

```bash
# 対処: キャッシュサイズを削減
SCRYFALL_MCP_CACHE_MAX_SIZE=200
```

#### Redis接続エラー

```bash
# 対処: メモリキャッシュに切り替え
SCRYFALL_MCP_CACHE_BACKEND=memory
```

### 設定の検証

```bash
# 設定値の確認（秘密情報を含みうるため全設定のprintは避ける）
uv run python -c "
from scryfall_mcp.settings import get_settings
s = get_settings()
print('user_agent configured:', bool(s.user_agent))
print('cache_backend:', s.cache_backend)
print('default_locale:', s.default_locale)
"
```

