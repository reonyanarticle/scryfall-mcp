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
- **適切なコンテンツタイプ**: TextContent、ImageContent、EmbeddedResourceの使い分け

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

## 最近の改善（2025-10-03）

### テストカバレッジの向上
**問題**: Codex分析により、リクエストモデルとバリデーション周りのテストカバレッジ不足が判明。

**実装済み解決策**:
- リクエストモデル（SearchCardsRequest、AutocompleteRequest）の包括的テストを追加
- バリデーションテスト追加:
  - URL検証（ImageUris、Card）
  - 境界値検証（max_results: 1-175）
  - ネストされた構造の検証
  - 必須フィールドの検証
- 全360テスト成功、カバレッジ向上

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
- ImageContent、TextContent、EmbeddedResourceの適切な使い分け

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