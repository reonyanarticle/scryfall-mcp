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

#### User-Agent設定ウィザード
**実装内容**:
- 初回起動時の対話式セットアップウィザード
- メールアドレス・HTTPS URLのバリデーション
- プラットフォーム固有の設定ディレクトリ
  - macOS: `~/Library/Application Support/scryfall-mcp/`
  - Linux: `~/.config/scryfall-mcp/`
  - Windows: `%APPDATA%\Local\scryfall-mcp\`
- CLIコマンド: `setup`, `config`, `reset`, `--help`

#### PII保護とファイルパーミッション
**実装済みセキュリティ対策**:
- 設定ディレクトリ: `mode=0o700` (所有者のみアクセス可能)
- 設定ファイル: `chmod(0o600)` (所有者のみ読み書き可能)
- User-Agent検証強化:
  - 空白文字・プレースホルダー値のバリデーション
  - 非対話モードでの起動時チェック（未設定時はエラー終了）
- 機密情報のログ出力防止:
  - Redis認証情報・連絡先情報を含む設定のログ出力を削除
  - 必要最小限の情報のみログに記録

```python
# setup_wizard.py
def get_config_dir() -> Path:
    # PII保護: 所有者のみアクセス可能
    config_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    return config_dir

# settings.py
def get_settings() -> Settings:
    # 起動時検証: User-Agent必須
    user_agent_val = _settings.user_agent.strip() if _settings.user_agent else ""
    is_placeholder = "unconfigured" in user_agent_val.lower()

    if not user_agent_val or is_placeholder:
        if not sys.stdin.isatty():
            # 非対話モードで未設定 → エラー終了
            print("ERROR: User-Agent not configured. Run 'scryfall-mcp setup' first.", file=sys.stderr)
            sys.exit(1)
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