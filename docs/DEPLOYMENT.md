# Remote MCP デプロイメント（コスト最適化版）

## 概要

Remote MCP (HTTP/Streamable HTTP transport)により、Scryfall MCP ServerをHTTPエンドポイントとして公開し、Claude.aiなど外部クライアントから利用可能にします。**コスト最適化版**では、ElastiCache/VPCを削除し、メモリキャッシュのみを使用する軽量構成で**月額$0-2（試算）**を目安とします。

## ディレクトリ構造

```
deploy/
└── aws/                    # AWS Lambda デプロイメント設定
    ├── serverless.yml      # Serverless Framework IaC定義（無料枠最適化）
    ├── lambda_handler.py   # Lambda エントリポイント (Mangum統合)
    └── package.json        # Node.js依存関係 (Serverless Framework)
```

デプロイガイドは本ドキュメント（`docs/DEPLOYMENT.md`）が正本。

## 主要コンポーネント

> 以下は各コンポーネントの概要。設定値・実装の正本は `deploy/aws/` の各ファイルであり、変更時はそちらを参照すること。

### 1. serverless.yml - Infrastructure as Code（無料枠最適化）

AWS Lambda、API Gateway、AWS Budgetsのみでシンプルに構成。VPC/ElastiCacheは削除。

**主要な設定項目**:
- **runtime**: Python 3.12, ARM64 (Graviton2、20%コスト削減)
- **メモリ**: 256MB（512MBから削減）
- **タイムアウト**: 30秒
- **HTTP API**: CORS設定（JWT認証は任意）
- **AWS Budgets**: 月$1超過で80%到達時アラート
- **CloudWatch Logs**: 7日自動削除
- **Secrets**: AWS SSM Parameter Store（User-Agentのみ必須）

**環境変数**:
| 変数名 | 値 | 説明 |
|--------|-----|------|
| `SCRYFALL_MCP_TRANSPORT_MODE` | `streamable_http` | Remote MCP有効化 |
| `SCRYFALL_MCP_CACHE_BACKEND` | `memory` | メモリキャッシュ（Redis不要） |
| `SCRYFALL_MCP_OAUTH_ENABLED` | `false` | OAuth認証（初回は無効） |
| `SCRYFALL_MCP_USER_AGENT` | SSM Parameter | Scryfall API連絡先（必須） |
| `SCRYFALL_MCP_JWT_SECRET_KEY` | SSM Parameter | JWT署名鍵（OAuth有効時のみ） |

### 2. lambda_handler.py - Lambda エントリポイント

Mangum ASGI adapterによりFastMCP (Starlette/FastAPI)をAWS Lambdaで実行。

**主要機能**:
- **Cold start最適化**: グローバルスコープでサーバーインスタンスをキャッシュ
- **Lazy initialization**: `get_server()`による遅延初期化
- **Mangum統合**: ASGI↔Lambda event変換を自動化
- **デバッグログ**: 開発環境でリクエストIDとパスをログ出力

実装の詳細は `deploy/aws/lambda_handler.py` を参照（コードをここに複製しない）。

### 3. package.json - Serverless Framework 依存関係

Node.js依存関係を管理し、デプロイスクリプトを提供。

**scripts**:
- `deploy:dev`: 開発環境デプロイ
- `deploy:staging`: ステージング環境デプロイ
- `deploy:production`: 本番環境デプロイ
- `info`: デプロイ情報表示
- `remove`: リソース削除

## デプロイ手順

### 1. AWS認証情報の設定

```bash
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_DEFAULT_REGION="us-east-1"
```

### 2. Serverless Frameworkのインストール

```bash
cd deploy/aws
npm install
```

### 3. シークレットの設定 (AWS SSM Parameter Store)

```bash
# JWT Secret Key
aws ssm put-parameter \
  --name "/scryfall-mcp/dev/JWT_SECRET_KEY" \
  --type "SecureString" \
  --value "your-256-bit-secret-key"

# OAuth Issuer URL
aws ssm put-parameter \
  --name "/scryfall-mcp/dev/OAUTH_ISSUER_URL" \
  --type "String" \
  --value "https://your-oauth-provider.com"

# User-Agent (Scryfall API)
aws ssm put-parameter \
  --name "/scryfall-mcp/dev/SCRYFALL_MCP_USER_AGENT" \
  --type "String" \
  --value "YourApp/1.0 (your-email@example.com)"
```

上記コマンドは `scripts/manage_secrets.py`（Typer CLI）でインタラクティブに実行することもできる。

### 4. デプロイ実行

```bash
# 開発環境
npm run deploy:dev

# 本番環境
npm run deploy:production
```

### 5. デプロイ確認

```bash
# エンドポイント情報取得
npx serverless info --stage dev

# ヘルスチェック
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  https://your-api-id.execute-api.us-east-1.amazonaws.com/mcp
```

## セキュリティ設計

### 1. JWT認証 (API Gateway Authorizer)

API GatewayレベルでJWT検証を実施し、無効なトークンはLambdaに到達しない。

```yaml
httpApi:
  authorizers:
    jwtAuthorizer:
      type: jwt
      identitySource: $request.header.Authorization
      issuerUrl: ${ssm:/scryfall-mcp/${self:provider.stage}/OAUTH_ISSUER_URL~true}
      audience:
        - scryfall-mcp-api
```

### 2. CORS設定

Claude.aiとAnthropic APIからのアクセスのみ許可。

```yaml
httpApi:
  cors:
    allowedOrigins:
      - https://claude.ai
      - https://api.anthropic.com
    allowedMethods:
      - GET
      - POST
      - OPTIONS
    allowedHeaders:
      - Authorization
      - Content-Type
```

### 3. セキュリティ考慮事項（Cost-optimized版）

コスト最適化版ではVPCとElastiCache Redisを削除しています。以下の点に注意してください：

- Lambda関数は**パブリックインターネット接続**を持ちます（VPCなし）
- キャッシュは**メモリのみ**使用（Redisなし）
- 本番環境でネットワーク分離が必要な場合は、VPC設定を追加してください（月額$30+のコスト増）

### 4. Secrets管理

JWT秘密鍵などの機密情報はAWS SSM Parameter Storeで管理し、環境変数経由でLambdaに注入。

## コスト見積もり（無料枠最大活用）

> 以下は執筆時点の AWS 料金・無料枠に基づく**試算**。料金体系は変わるため、最新は [AWS 料金ページ](https://aws.amazon.com/pricing/) で確認すること。

**月間100万リクエスト、平均応答時間500msの場合**:
- Lambda (256MB, arm64): $0（無料枠内）
- API Gateway (HTTP API): $0（無料枠内、初年度）
- CloudWatch Logs (7日保持): $0（無料枠内）
- SSM Parameter Store: $0
- **合計**: **$0-2/月**

**無料枠**:
- Lambda: 100万リクエスト/月、40万GB秒/月（永続）
- API Gateway: 100万リクエスト/月（初年度のみ）
- CloudWatch Logs: 5GB保存、50万イベント/月

**無料枠超過後の追加コスト**:
- Lambda: $0.20/百万リクエスト
- API Gateway: $1.00/百万リクエスト（2年目以降）

## トラブルシューティング

### Cold Start対策

**問題**: 初回リクエストが3-5秒かかる

**対処法**:
1. サーバーインスタンスのグローバルキャッシング（実装済み）
2. ARM64アーキテクチャ使用（実装済み、Graviton2で高速化）
3. Provisioned Concurrency設定（コスト増、月$10-15）

```yaml
# serverless.yml（オプション）
functions:
  mcp:
    provisionedConcurrency: 1  # 常時1インスタンス稼働
```

### メモリ不足 (OOM)

**問題**: `Task timed out after 30.00 seconds` または `MemoryError`

**対処法**:
```yaml
# serverless.yml
provider:
  memorySize: 512  # 256MB → 512MBに増加（月$1-2コスト増）
```

### デプロイエラー: "Budget email not set"

**問題**: `serverless deploy`時にBudgets作成エラー

**対処法**:
```bash
# デプロイ時にメールアドレスを指定
npx serverless deploy --stage dev --param="budget_alert_email=your-email@example.com"
```

## 今後の実装予定

### Phase 4: 追加プラットフォーム対応（Cloudflare Workers Python runtime待ち）
- **Cloudflare Workers** (Python runtime正式サポート後)
- **Google Cloud Run** (代替サーバーレス)
- **Kubernetes** (エンタープライズ向け)

### Phase 5: 運用機能強化
- **モニタリング**: CloudWatch Metrics, X-Ray トレーシング
- **アラート**: レート制限接近時の通知
- **ログ集約**: 構造化ログとフィルタリング
- **オートスケール**: API Gateway throttling設定
- **CI/CD**: GitHub ActionsによるデプロイAutomation

## 参考資料

- **AWS Lambda Python**: <https://docs.aws.amazon.com/lambda/latest/dg/lambda-python.html>
- **Serverless Framework**: <https://www.serverless.com/framework/docs>
- **Mangum**: <https://mangum.io/>
- **FastMCP**: <https://github.com/jlowin/fastmcp>
- **MCP Protocol**: <https://modelcontextprotocol.io/>
- **設計文書**: `docs/REMOTE-MCP-IMPLEMENTATION-PLAN.md`

