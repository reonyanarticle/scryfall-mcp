# Scryfall MCP Server - AI Agent Instructions

このドキュメントは、Scryfall MCP Serverプロジェクトに対する重要な設計思想、技術的制約、および改善課題をまとめたものです。

## プロジェクト概要

Magic: The GatheringのカードデータをMCP (Model Context Protocol)経由でAIアシスタントに提供するサーバー。Scryfall APIとの統合により、日本語を含む自然言語でのカード検索機能を提供します。

## 重要な技術的制約

### Scryfall API制約
- **レート制限**: 最大10 requests/second、リクエスト間隔75-100ms以上を維持
- **必須HTTPヘッダー**: `User-Agent`と`Accept`ヘッダーがないと403でブロック
- **データ制限**: 1ページ最大175カード

### 開発規約
- **型ヒント必須**: PEP585準拠、pydanticベース
- **docstring必須**: Numpy styleで記載
- **非同期処理**: すべてのI/O処理はasync/await
- **早期リターン推奨**: 深いネスト回避

### ドキュメント方針
- **動的情報は記載しない**: テスト数、カバレッジ率、コミットハッシュ、日付などの変動する情報は記載しない
- **理由**: これらの情報はgitログ、テスト実行結果、CIで確認可能。ドキュメントに記載すると更新漏れで陳腐化する
- **例外**: バージョン番号、リリース日などリリースに紐づく情報は記載可
- **OK**: "全テスト合格"、"カバレッジ90%以上を維持"（目標値）
- **NG**: "389テスト合格"、"95%カバレッジ"（具体的な数値）、"2025-10-05"（日付）

## 実装済みアーキテクチャ

### 並行性セーフなロケール管理
```python
# contextvarsベースのスレッドセーフ実装
_current_locale_context: contextvars.ContextVar[str] = contextvars.ContextVar(
    "current_locale", default="en"
)

@contextmanager
def use_locale(locale_code: str):
    """リクエスト毎に独立したロケールコンテキスト"""
    token = _current_locale_context.set(locale_code)
    try:
        yield locale_code
    finally:
        _current_locale_context.reset(token)
```

### 2層キャッシュシステム
- **L1 (Memory)**: LRU、最大1000エントリ、インメモリ高速キャッシュ
- **L2 (Redis)**: TTL付き永続化、複数プロセス間共有
- **グレースフルフォールバック**: Redis接続失敗時もメモリキャッシュで継続動作

### 検索パイプライン分離
```
自然言語クエリ → Parser → QueryBuilder → Presenter → MCPレスポンス
                    ↓          ↓           ↓
               ParsedQuery → BuiltQuery → EmbeddedResource
```

### 構造化MCPレスポンス
- **EmbeddedResource**: カードメタデータをJSONで構造化保持
- **カスタムURIスキーマ**: `card://scryfall/{id}` による一意識別
- **MCP標準準拠**: TextContentとEmbeddedResourceのみ使用（ImageContentは非標準のため削除）

### 多言語エラーハンドリング
- **ステータス別対応**: 400/403/429/500+系の詳細ガイダンス
- **実行可能な提案**: クエリ固有の回復方法提示
- **多言語サポート**: 日本語・英語での詳細エラーメッセージ

### ネイティブ多言語カード検索
```python
# 日本語カード名をそのまま Scryfall API に渡す
def _convert_card_names(self, text: str) -> str:
    """Pass card names as-is to Scryfall.

    Scryfall natively supports multilingual card names through
    the printed_name field and lang: parameter.
    """
    return text  # No pre-translation needed

# search.py で言語フィルタを追加
if request.language and request.language != "en":
    scryfall_query += f" lang:{request.language}"

search_result = await client.search_cards(
    query=scryfall_query,
    include_multilingual=True,  # 多言語カードデータを取得
)
```
- **完全カバレッジ**: 全27000+カードを自動サポート
- **メンテナンスフリー**: 新セットの手動登録が不要
- **ネイティブファジーマッチング**: Scryfallの高精度検索を活用

## v0.1.0での主要な改善

### セキュリティ強化（2025-10-04）

#### User-Agent設定
**実装内容**:

**主要な設定方法（MCP使用時）**: 環境変数
- Claude DesktopなどのMCPクライアントでは、`claude_desktop_config.json`の`env`セクションで設定
- 環境変数名: `SCRYFALL_MCP_USER_AGENT`
- 形式: `"YourApp/1.0 (your-email@example.com)"` または `"YourApp/1.0 (https://github.com/username/repo)"`
- 設定なしでツール呼び出し時、設定手順を含むメッセージを表示

**設定ウィザード（CLI使用時）**: 対話式セットアップ
- スタンドアローン実行時のみ使用
- メールアドレス・HTTPS URLのバリデーション
- プラットフォーム固有の設定ディレクトリ
  - macOS: `~/Library/Application Support/scryfall-mcp/`
  - Linux: `~/.config/scryfall-mcp/`
  - Windows: `%APPDATA%\Local\scryfall-mcp\`
- CLIコマンド: `setup`, `config`, `reset`, `--help` （非推奨：MCP使用時は環境変数を推奨）

#### PII保護とファイルパーミッション
**実装済みセキュリティ対策**:
- 設定ディレクトリ: `mode=0o700` (所有者のみアクセス可能)
- 設定ファイル: `chmod(0o600)` (所有者のみ読み書き可能)
- User-Agent検証:
  - 空白文字・プレースホルダー値（"setup-recommended"）のバリデーション
  - `is_user_agent_configured()` ヘルパー関数
- ツールレベルでの検証:
  - `search_cards` 実行時にUser-Agent設定を確認
  - 未設定時は環境変数設定手順を含むエラーメッセージを返却
- 機密情報のログ出力防止:
  - Redis認証情報・連絡先情報を含む設定のログ出力を削除
  - 必要最小限の情報のみログに記録

```python
# tools/search.py - ツールレベルでの検証
async def execute(arguments: dict[str, Any]) -> list[TextContent | EmbeddedResource]:
    # Check if User-Agent is configured before allowing search
    if not is_user_agent_configured():
        config_message = (
            "⚠️ **User-Agent Configuration Required**\n\n"
            "Before searching for cards, you need to configure your contact information "
            "for Scryfall API compliance.\n\n"
            "**Please add the following to your Claude Desktop configuration:**\n\n"
            # ... 設定手順を詳細に表示 ...
        )
        return [TextContent(type="text", text=config_message)]

# settings.py - 検証ヘルパー
def is_user_agent_configured() -> bool:
    """Check if User-Agent has been properly configured."""
    settings = get_settings()
    user_agent = settings.user_agent.strip() if settings.user_agent else ""

    if not user_agent or "setup-recommended" in user_agent.lower():
        return False

    return True
```

### MCP仕様準拠とプロトコル修正

#### Critical: Lifespan Context Manager修正
**問題**: FastMCPがlifespanコンテキストマネージャーに`app`引数を渡すが、実装が受け取っていなかった。
```
TypeError: _create_lifespan() takes 0 positional arguments but 1 was given
```

**実装済み解決策**:
- `_create_lifespan(app: FastMCP) -> AsyncIterator[None]` に修正
- FastMCPのlifespanプロトコルに準拠
- サーバーが正常にstdioモードで起動可能に

#### MCP Content型の構造化出力（Critical修正完了）
**問題**: ツールがMCP Content型を文字列に変換していた。また、ImageContentがMCP仕様に存在しない。

**実装済み解決策**:
- ツールが直接`list[TextContent | EmbeddedResource]`を返すように修正
- **ImageContent削除**: MCP仕様に存在しないため削除（v0.1.0破壊的変更）
- 画像データの代わりに画像URLをtext内に含める
- MCPプロトコル準拠の構造化データ出力
- `tests/integration/test_mcp_content_validation.py`で検証完了

#### FastMCP Context注入
**追加機能**:
- 全ツールに`Context`パラメータを追加
- `ctx.info()`: ログ出力
- `ctx.report_progress()`: 進捗報告
- `ctx.error()`: エラーログ
- より良い可観測性とユーザーフィードバック

#### Asynccontextmanagerベースのライフサイクル管理
**実装完了**:
```python
@asynccontextmanager
async def _create_lifespan(app: FastMCP) -> AsyncIterator[None]:
    """Lifecycle manager for the MCP server."""
    # Startup
    detected_locale = detect_and_set_locale()
    logger.info("Detected and set locale: %s", detected_locale)

    try:
        yield
    finally:
        # Shutdown/cleanup
        await close_client()
        logger.info("Scryfall MCP Server stopped")
```
- 起動/シャットダウンロジックの一元化
- リソースの適切なクリーンアップ
- FastMCPのlifespanプロトコルに準拠

#### Cache TTL Scryfall推奨値対応
**問題**: キャッシュTTLが30分/1時間（Scryfall推奨は最低24時間）

**実装済み解決策**:
- `cache_ttl_search`: 30分 → 86400秒（24時間）
- `cache_ttl_default`: 1時間 → 86400秒（24時間）
- Scryfall APIガイドライン準拠

#### RateLimiterのスレッドセーフ化
**問題**: 共有状態が保護されておらず、並行リクエストでレート制限違反の可能性。

**実装済み解決策**:
```python
def __init__(self):
    self._lock = asyncio.Lock()  # 共有状態を保護

async def acquire(self) -> None:
    async with self._lock:
        # レート制限ロジック
```

#### MCP統合テスト追加
**新規テスト**: `tests/integration/test_mcp_content_validation.py`
- TextContent構造検証（`type: "text"`, `text: str`）
- EmbeddedResource構造検証（`type: "resource"`, `resource: dict`）
- ImageContent非存在の検証（MCP仕様準拠確認）
- エラーレスポンスの検証
- 全389テスト成功、カバレッジ95%達成

### テストカバレッジの向上（2025-10-03）
**問題**: Codex分析により、リクエストモデルとバリデーション周りのテストカバレッジ不足が判明。

**実装済み解決策**:
- リクエストモデル（SearchCardsRequest、AutocompleteRequest）の包括的テストを追加
- バリデーションテスト追加:
  - URL検証（ImageUris、Card）
  - 境界値検証（max_results: 1-175）
  - ネストされた構造の検証
  - 必須フィールドの検証
- 全389テスト成功、カバレッジ向上

### 定数の分離
**問題**: settings.pyに実行時設定と静的な語彙データが混在し、モジュールの責務が不明瞭。

**実装済み解決策**:
- `src/scryfall_mcp/i18n/constants.py` を新規作成
- 分離した定数:
  - `SCRYFALL_KEYWORDS` - 検索構文キーワード
  - `MAGIC_COLORS` - 色コード (WUBRG)
  - `MAGIC_TYPES` - カードタイプとサブタイプ
  - `SEARCH_PATTERNS` - 正規表現パターン
- `settings.py` は実行時設定のみに集中
- モジュールの責務が明確化

## 設計課題と実装状況

### 1. 並行性の問題（完了）
**問題**: グローバルなロケール管理により、並行リクエスト間で言語設定が干渉。

**実装済み解決策**:
- `contextvars`を使用したコンテキストスコープのロケール管理
- `src/scryfall_mcp/i18n/locales.py` で実装完了
- `use_locale()` コンテキストマネージャーによるスレッドセーフな言語設定
```python
@contextmanager
def use_locale(locale_code: str):
    """Context manager for setting locale in current context."""
    token = _current_locale_context.set(locale_code)
    try:
        yield locale_code
    finally:
        _current_locale_context.reset(token)
```

### 2. 責任の混在（完了）
**問題**: `CardSearchTool.execute`メソッドに複数の責任が集中。

**実装済み解決策**:
- パーサー → クエリビルダー → プレゼンターのパイプライン分離
- `src/scryfall_mcp/search/` モジュールで実装完了
  - `parser.py`: 自然言語解析
  - `builder.py`: Scryfallクエリ構築
  - `presenter.py`: MCP出力フォーマット
  - `models.py`: データモデル定義

### 3. 未実装のキャッシュシステム（完了）
**以前の問題**: 設定にキャッシュ項目はあるが実装は空。

**実装済み解決策**:
- メモリ + Redis の2層キャッシュシステム実装完了
- `src/scryfall_mcp/cache/` モジュールで実装完了
  - `backends.py`: Memory/Redis/Composite cache実装
  - `manager.py`: キャッシュマネージャーとファクトリー
- 設定済みTTL（検索結果30分、カード詳細24時間、オートコンプリート15分）
- Redis接続失敗時のグレースフルフォールバック

### 4. 静的な日本語マッピング（完了）
**以前の問題**:
- 日本語カード名辞書は40カードのみ（全27000カードの0.15%）。
- 新カードへの対応が手動で困難。
- Scryfallのネイティブ多言語機能を活用していなかった。

**実装済み解決策**:
- カード名の事前翻訳を廃止し、日本語のまま Scryfall API に渡す方式に変更
- `lang:` パラメータによる言語フィルタリングを追加
- `include_multilingual=True` で多言語カードデータを取得
- Scryfallの `printed_name` フィールドとネイティブファジーマッチングを活用
- 完全なカードカバレッジ（全27000+カード対応）、メンテナンスフリー

### 5. MCP機能の未活用（完了）
**問題**: fastmcpの豊富なコンテンツタイプが文字列に変換される。

**実装済み解決策**:
- 構造化MCPレスポンスの実装完了
- `EmbeddedResource`によるメタデータ保持
- カスタムURIスキーマ（`card://scryfall/{id}`）による構造化データ
- TextContentとEmbeddedResourceの適切な使い分け
- **ImageContent削除**: MCP仕様に存在しないため削除（画像URLで代替）

### 6. エラーハンドリング強化（完了）
**実装済み解決策**:
- ステータス別詳細エラー情報（400/403/429/500+系）
- 日本語・英語両方での実行可能なガイダンス
- `src/scryfall_mcp/errors/` モジュールで実装完了
- クエリ固有の回復提案機能

### 7. MCPエラーハンドリングのベストプラクティス

#### エラーメッセージの簡潔性
**問題**: 長すぎるエラーメッセージがClaude Desktop側で適切に表示されない

**実装済み解決策**:
- User-Agent未設定エラーを簡潔なフォーマットに変更
- 冗長な説明を削除し、必要最小限の情報に絞る
- 箇条書きと明確なセクション分けで可読性向上

**MCPツールからのエラー返却の原則**:
```python
# ❌ 悪い例: 長すぎる説明
config_message = (
    "詳細な背景説明が何段落も続く...\n"
    "さらに追加の説明...\n"
    "なぜこれが必要か、さらに詳しく...\n"
    "歴史的な背景...\n"
    # 合計30行以上の説明
)

# 良い例: 簡潔で実用的、ポジティブなトーン
config_message = (
    "🔧 **Scryfall API 初回セットアップ**\n\n"
    "Scryfall APIをご利用いただくには、以下の設定を行ってください：\n\n"
    "**1. Claude Desktop設定ファイルを開く**\n"
    "- macOS/Linux: `~/Library/Application Support/Claude/claude_desktop_config.json`\n"
    "- Windows: `%APPDATA%\\Claude\\claude_desktop_config.json`\n\n"
    "**2. 以下の内容を追加**\n"
    "```json\n{...}\n```\n\n"
    "**3. プレースホルダーを実際の値に置き換え**\n"
    "**4. Claude Desktopを再起動**\n\n"
    "設定完了後、再度カード検索をお試しください。\n\n"
    "詳細情報: https://scryfall.com/docs/api"
)
```

#### メッセージトーンの重要性
**問題**: ⚠️マークや「必要です」などのエラートーンがClaude Desktop側で「ツールエラー」として認識され、チャットインターフェースに表示されない

**実装済み解決策**:
- エラートーン（⚠️、「〜が必要です」）→ セットアップガイドトーン（🔧、「〜を行ってください」）
- 「User-Agent設定が必要です」→ 「Scryfall API 初回セットアップ」
- ネガティブな表現を避け、ポジティブで前向きなガイドとして提示

**理由**:
- MCPクライアント（Claude Desktop）はメッセージのトーンから「エラー」か「正常な応答」かを判断
- エラーと判断されると、ツールレスポンスではなく汎用エラーメッセージが表示される
- セットアップガイドのトーンにすることで、正常な応答として認識され、チャットに表示される

#### TextContentの適切な使用
**実装内容**:
- すべてのエラーは`TextContent(type="text", text=message)`形式で返却
- エラーメッセージは必ず`list[TextContent]`として返す
- 例外をraiseせず、常に構造化レスポンスを返す

**理由**:
- MCPクライアント（Claude Desktop）は構造化レスポンスを期待
- 例外をraiseすると、クライアント側で「ツールの設定に問題があります」という一般的なエラーになる
- TextContentで返すことで、ユーザーに具体的なガイダンスを提供可能

#### 参考情報
- MCP Python SDK: https://github.com/modelcontextprotocol/python-sdk
- MCP仕様: https://modelcontextprotocol.io/
- FastMCP: https://github.com/jlowin/fastmcp

**レッスン**: MCPツールは常にユーザーフレンドリーなメッセージを返し、エラーの場合でも次のアクションを明確に示すこと。

## 必要な追加技術・機能

### 観測可能性
- 構造化ログ、メトリクス、トレーシング
- API呼び出しとレート制限状態の監視
- 運用者がScryfall制限接近を把握可能

### Redis統合
- 現在は依存関係に含まれているが実装なし
- 設定検証とヘルスチェック追加
- または実装まで依存関係から削除

### エラーハンドリング強化
- ステータス別（429 vs 5xx）の詳細エラー情報
- 日本語・英語両方での実行可能なガイダンス
- 部分応答の回避

### 運用機能
- グレースフルシャットダウン
- レディネスプローブ
- キャッシュのウォームアップとリロード機能

## コード品質チェックリスト

### 必須実行コマンド
```bash
# リント・フォーマット
uv run ruff check src/ tests/ --fix
uv run ruff format src/ tests/

# 型チェック（STRICT mode）
uv run mypy src/

# テスト（カバレッジ95%目標）
uv run pytest --cov=scryfall_mcp --cov-report=term-missing
```

### テスト方針
- Scryfall APIはモック化必須
- 非同期処理はpytest-asyncio使用
- 並行性テストを含む多言語検索の回帰テスト

## セキュリティガイドライン

- 環境変数で機密情報管理
- 入力値サニタイズ必須
- ログに個人情報・APIキー出力禁止
- Wizards of the Coastファンコンテンツポリシー遵守

## 開発優先順位

### 完了済み
**High Priority タスク（すべて完了）**
- 並行ロケール管理の修正（contextvarsベース）
- キャッシュシステムの実装（2層キャッシュ）
- 構造化MCPレスポンス対応（EmbeddedResource）
- 日本語カード名検索のアーキテクチャ改善（Scryfallネイティブサポート活用）

**Medium Priority タスク（すべて完了）**
- 検索ツールの責任分離（Parser → QueryBuilder → Presenter）
- エラーハンドリング強化（ステータス別多言語対応）

### 残存タスク

1. **Medium Priority**
   - 観測可能性の追加（構造化ログ、メトリクス、トレーシング）

2. **Low Priority**
   - 日本語NLP強化（トークナイザー統合、ベクター検索）
   - Redis統合完成（ヘルスチェック、設定検証）
   - 運用管理機能（グレースフルシャットダウン、レディネスプローブ）

このドキュメントは定期的に更新し、設計決定と技術的負債の現状を反映させること。