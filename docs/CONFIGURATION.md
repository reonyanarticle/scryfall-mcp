# 設定ガイド

## 環境変数

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
| `SCRYFALL_MCP_REDIS_DB` | `0` | Redisデータベース番号 |

### TTL設定

Scryfallの推奨に従い、最低24時間のキャッシュを設定しています。

| 変数名 | デフォルト | 最小値 | 説明 |
|--------|-----------|--------|------|
| `SCRYFALL_MCP_CACHE_TTL_SEARCH` | `86400` (24時間) | 86400 | 検索結果TTL（秒）※Scryfall推奨 |
| `SCRYFALL_MCP_CACHE_TTL_CARD` | `86400` (24時間) | 3600 | カード詳細TTL（秒） |
| `SCRYFALL_MCP_CACHE_TTL_PRICE` | `21600` (6時間) | 300 | 価格情報TTL（秒） |
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
| `SCRYFALL_MCP_LOG_FORMAT` | デフォルトフォーマット | ログ形式 |

### 開発設定

| 変数名 | デフォルト | 説明 |
|--------|-----------|------|
| `SCRYFALL_MCP_DEBUG` | `false` | デバッグモード |
| `SCRYFALL_MCP_MOCK_API` | `false` | モックAPI使用 |

## 設定例

### 基本設定

```bash
# .env ファイル
SCRYFALL_MCP_DEFAULT_LOCALE=ja
SCRYFALL_MCP_RATE_LIMIT_MS=150
SCRYFALL_MCP_CACHE_ENABLED=true
```

### プロダクション設定

```bash
# プロダクション環境
SCRYFALL_MCP_LOG_LEVEL=WARNING
SCRYFALL_MCP_CACHE_BACKEND=redis
SCRYFALL_MCP_REDIS_URL=redis://localhost:6379
SCRYFALL_MCP_RATE_LIMIT_MS=75
```

### 開発設定

```bash
# 開発環境
SCRYFALL_MCP_DEBUG=true
SCRYFALL_MCP_LOG_LEVEL=DEBUG
SCRYFALL_MCP_MOCK_API=true
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
SCRYFALL_MCP_CACHE_TTL_SEARCH=900

# パフォーマンス重視
SCRYFALL_MCP_CACHE_MAX_SIZE=2000
SCRYFALL_MCP_CACHE_TTL_SEARCH=3600
```

## トラブルシューティング

### よくある設定問題

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
# 設定値の確認
uv run python -c "from scryfall_mcp.settings import get_settings; print(get_settings())"
```