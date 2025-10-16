# Scryfall MCP Server

Magic: The Gatheringのカード情報を提供するScryfall APIをMCP (Model Context Protocol)経由でAIアシスタントに接続するサーバー。
詳細はAPI Documentation (https://scryfall.com/docs/api) を参考にしてください。

## 主要機能

- Scryfall検索構文によるカード検索
- 自然言語からScryfall構文への変換
- カード価格情報の取得と通貨換算
- デッキ構成の統計分析
- 多言語カード名のサポート（日本語、英語、その他）
- 地域別の価格表示とタイムゾーン対応

## プロジェクト構造

```
scryfall-mcp/
├── docs/                      # ドキュメント類置き場（ファイル名は大文字で統一）
│   ├── API-REFERENCE.md       # API仕様書
│   ├── CONFIGURATION.md       # 設定ガイド
│   ├── DEVELOPMENT.md         # 開発者ガイド
│   └── INTERNATIONALIZATION.md # 多言語対応ガイド
├── src/
│   └── scryfall_mcp/
│       ├── __init__.py
│       ├── server.py          # MCPサーバーエントリポイント
│       ├── settings.py        # 環境変数・グローバル変数管理
│       ├── api/
│       │   ├── client.py      # Scryfall APIクライアント
│       │   ├── rate_limiter.py # レート制限実装
│       │   └── models.py      # APIレスポンスモデル
│       ├── cache/
│       │   ├── manager.py     # キャッシュ管理
│       │   └── backends.py    # メモリ/Redis実装
│       ├── search/
│       │   ├── builder.py     # クエリビルダー
│       │   └── processor.py   # 自然言語処理
│       ├── i18n/
│       │   ├── __init__.py    # 多言語化システム
│       │   ├── locales.py     # 地域設定管理
│       │   └── mappings/      # 言語別マッピングデータ
│       │       ├── ja.py      # 日本語マッピング
│       │       ├── en.py      # 英語マッピング
│       │       └── common.py  # 共通マッピング定義
│       └── tools/
│           ├── search.py      # 検索ツール
│           ├── card.py        # カード詳細ツール
│           └── deck.py        # デッキ分析ツール
├── tests/                     # テスト
├── uv.lock
└── pyproject.toml
```

## Scryfall API制約

### レート制限
- 最大10 requests/second
- リクエスト間隔75-100ms以上を維持
- 429エラー時はexponential backoff

### 必須HTTPヘッダー
```
User-Agent: アプリ名とバージョン、連絡先
Accept: application/json;q=0.9,*/*;q=0.8
```

これらのヘッダーがないと403でブロックされます。

### データ取得
- 1ページ最大175カード
- 大量データはBulk Data APIを使用

## キャッシュ戦略

### 階層構成
- L1 (メモリ): LRU, 最大1000エントリ
- L2 (Redis): TTL付き永続化

### TTL設定
- 検索結果: 30分
- カード詳細: 24時間
- 価格情報: 6時間
- セット情報: 1週間

## エラー処理

### サーキットブレーカー
- 失敗閾値: 5回連続
- オープン時間: 60秒
- ハーフオープン試行: 1リクエスト

### リトライポリシー
- 429/503エラー: exponential backoff
- 最大リトライ: 5回
- タイムアウト: 30秒

## カード表示仕様（MCP出力フォーマット）

### 表示フィールド一覧

MCPツール（`search_cards`）でカード検索結果を返す際、以下のフィールドを表示します。

#### 必須フィールド（常に表示）

| # | フィールド | データモデル | 表示条件 | 説明 |
|---|-----------|------------|---------|------|
| 1 | **カード名** | `name` / `printed_name` | 常に表示 | 日本語検索時は`printed_name`優先 |
| 2 | **マナコスト** | `mana_cost` | 値が存在する場合 | `{R}`, `{2}{U}{U}`等のシンボル形式 |
| 3 | **タイプライン** | `type_line` / `printed_type_line` | 常に表示 | 日本語検索時は`printed_type_line`優先 |
| 4 | **パワー/タフネス** | `power` / `toughness` | クリーチャーのみ | 形式: `3/3`, `*/1+*`等 |
| 5 | **オラクルテキスト** | `oracle_text` / `printed_text` | 値が存在する場合 | 日本語検索時は`printed_text`優先 |
| 6 | **セット情報** | `set_name`, `rarity` | 常に表示 | セット名とレアリティを括弧内に表示 |

#### Phase 1追加フィールド（Issue #7対応）

| # | フィールド | データモデル | デフォルト | 表示制御パラメータ | 説明 |
|---|-----------|------------|----------|-------------------|------|
| 7 | **キーワード能力** | `keywords` | ON | `include_keywords` | 飛行、速攻等のキーワード一覧（カンマ区切り） |
| 8 | **イラストレーター** | `artist` | ON | `include_artist` | カードイラストの作成者名 |
| 9 | **マナ生成** | `produced_mana` | ON | `include_mana_production` | **土地専用**: 生成可能なマナ色 |
| 10 | **フォーマット適格性** | `legalities` | 条件付き | `format_filter` | format_filter指定時のみ表示 |

### 表示制御オプション

```python
class SearchOptions(BaseModel):
    """Search presentation options."""

    max_results: int = 10
    format_filter: str | None = None
    language: str | None = None

    # Phase 1: MCP Annotations制御
    use_annotations: bool = True

    # Phase 1: 表示フィールド制御
    include_keywords: bool = True        # デフォルトON
    include_artist: bool = True          # デフォルトON
    include_mana_production: bool = True # デフォルトON（土地専用）
```

### MCP Annotations仕様（Phase 1実装）

すべてのコンテンツにMCP Annotationsを付与し、クライアント側での適切な表示制御を実現します。

#### Annotationsフィールド

```python
from mcp.types import Annotations

Annotations(
    audience: list[Literal['user', 'assistant']] | None = None,
    priority: float (0.0-1.0) | None = None,
)
```

#### audience（対象者）

| 値 | 意味 | 使用例 |
|----|------|--------|
| `["user"]` | ユーザー向け（UIに表示） | カード情報（TextContent） |
| `["assistant"]` | アシスタント向け（LLMコンテキストのみ） | 構造化データ（EmbeddedResource） |
| `["user", "assistant"]` | 両方 | エラーメッセージ |

#### priority（優先度）

| 範囲 | 意味 | 使用例 |
|------|------|--------|
| `1.0` | 最重要 | カード名、マナコスト、タイプライン |
| `0.7-0.9` | 高優先度 | オラクルテキスト、P/T、keywords |
| `0.4-0.6` | 中優先度 | セット、レアリティ、価格 |
| `0.1-0.3` | 低優先度 | artist、EDHREC順位 |

### 実装例

```python
# ユーザー向けコンテンツ（TextContent）
def _format_single_card(
    self, card: Card, index: int, options: SearchOptions
) -> TextContent:
    """Format a single card with MCP Annotations."""

    card_text = f"## {index}. {card.name}"

    if card.mana_cost:
        card_text += f" {card.mana_cost}"

    # ... カード情報をマークダウンで整形 ...

    # キーワード能力（Phase 1新規）
    if options.include_keywords and card.keywords:
        keywords_label = "キーワード能力" if is_japanese else "Keywords"
        card_text += f"**{keywords_label}**: {', '.join(card.keywords)}\n"

    # イラストレーター（Phase 1新規）
    if options.include_artist and card.artist:
        illustrated_by = "イラスト" if is_japanese else "Illustrated by"
        card_text += f"*{illustrated_by} {card.artist}*\n"

    # MCP Annotations付与
    annotations = None
    if options.use_annotations:
        annotations = Annotations(
            audience=["user"],
            priority=0.8
        )

    return TextContent(type="text", text=card_text, annotations=annotations)

# アシスタント向けコンテンツ（EmbeddedResource）
def _create_card_resource(
    self, card: Card, index: int, options: SearchOptions
) -> EmbeddedResource:
    """Create EmbeddedResource with full metadata and Annotations."""

    card_metadata = {
        "id": str(card.id),
        "name": card.name,
        # ... 既存フィールド ...

        # Phase 1新規フィールド
        "keywords": card.keywords if card.keywords else [],
        "artist": card.artist,
        "produced_mana": card.produced_mana,
    }

    # MCP Annotations付与
    annotations = None
    if options.use_annotations:
        annotations = Annotations(
            audience=["assistant"],
            priority=0.6
        )

    return EmbeddedResource(
        type="resource",
        resource=TextResourceContents(
            uri=AnyUrl(f"card://scryfall/{card.id}"),
            mimeType="application/json",
            text=json.dumps(card_metadata, indent=2, ensure_ascii=False),
        ),
        annotations=annotations
    )
```

### 実装参照

- **詳細設計**: `docs/MCP-OUTPUT-DESIGN-REPORT.md`
- **現在の実装**: `src/scryfall_mcp/search/presenter.py` (lines 175-258)
- **データモデル**: `src/scryfall_mcp/models.py` (Card: lines 388-476)
- **MCP仕様**: https://modelcontextprotocol.io/specification/2025-06-18

## コーディング規約

### Python型アノテーション
- **型ヒントは必須**。すべての関数パラメータと戻り値に型アノテーションを付ける
- **PEP 585準拠**: `list[str]`, `dict[str, int]`, `tuple[int, ...]`など組み込み型を使用（Python 3.9+）
- **Union型**: `str | None`, `int | str`のようにパイプ演算子を使用（Python 3.10+）
- **Pydantic優先**: データモデルは`pydantic.BaseModel`を使用し、`Field`で詳細定義
- **標準ライブラリ型**: `collections.abc`モジュールから`Generator`, `Iterator`, `Callable`などをインポート
  ```python
  from collections.abc import Generator, Iterator

  def example() -> Generator[str, None, None]:
      yield "example"
  ```
- **Optional不使用**: `Optional[str]`ではなく`str | None`を使用
- **typing後方互換**: `from __future__ import annotations`を各ファイル先頭に記載

### Docstring規約
- **docstringは必須**: すべての関数、クラス、メソッドにdocstringを記載します
- **NumPy Styleを使用**: 以下の形式に従ってください
  ```python
  def function_name(param1: str, param2: int | None = None) -> bool:
      """Brief description of the function.

      Detailed description if needed. Can span multiple lines.

      Parameters
      ----------
      param1 : str
          Description of param1
      param2 : int | None, optional
          Description of param2 (default: None)

      Returns
      -------
      bool
          Description of return value

      Raises
      ------
      ValueError
          When param1 is empty
      RuntimeError
          When operation fails

      Examples
      --------
      >>> function_name("test", 42)
      True
      """
  ```
- **型表記の統一**: docstring内の型は最新のPython型アノテーション形式を使用してください
  - ✅ `str | None`
  - ❌ `str, optional` (古い表記)
  - ✅ `list[str]`
  - ❌ `List[str]` (typing.List)
- **セクション順序**: Parameters → Returns → Yields → Raises → Examples を守ってください
- **Generator型の記載**は以下のようにしてください。
  ```python
  def generator_func() -> Generator[int, None, None]:
      """Generator function.

      Yields
      ------
      int
          Description of yielded values
      """
  ```

### コード品質
- **1関数1責任**: 各関数は単一の明確な責任を持つようにしてください
- **早期リターン推奨**: ネストを減らし可読性を向上させてください
- **定数は大文字**: モジュールレベル定数は`UPPER_SNAKE_CASE`を使用してください
- **言語依存ファイル命名規則**: 言語コードを拡張子として使用
  - 形式: `{base_name}.{language_code}`
  - 例: `setup_guide.ja` (日本語), `setup_guide.en` (英語)
  - フォールバック: デフォルト言語ファイル（拡張子なし）または`.ja`
  - 実装: `Path(__file__).parent / f"setup_guide.{language}"`
  - 目的: 言語別リソースの管理を簡潔化し、ファイル命名の一貫性を保つ

### 非同期処理
- **I/O処理はasync/await**: すべてのネットワーク、ファイルI/Oは非同期化してください
- **CPU boundは別プロセス**: 重い計算処理は`ProcessPoolExecutor`を使用してください
- **タイムアウト必須**: すべての外部API呼び出しにタイムアウトを設定してください

### 命名規則
- **クラス**: `PascalCase` (例: `ScryfallAPIClient`)
- **関数/変数**: `snake_case` (例: `search_cards`, `max_results`)
- **定数**: `UPPER_SNAKE_CASE` (例: `CACHE_TTL_SEARCH`)
- **プライベート**: `_prefix` (例: `_make_request`, `_session`)
- **プロテクテッド**: 単一アンダースコア`_` (例: `_internal_method`)
- **プライベート強制**: 二重アンダースコア`__`は名前マングリングが必要な場合のみ

## テスト

```bash
# 全テスト実行
uv run pytest

# カバレッジ付き
uv run pytest --cov=scryfall_mcp

# 特定テスト
uv run pytest tests/test_search.py -v

# 監視モード
uv run pytest-watch
```

### テスト方針
- Scryfall APIはモック化
- 非同期処理はpytest-asyncio使用
- カバレッジ目標: 95%以上

## デバッグ

```bash
# 詳細ログ
LOG_LEVEL=DEBUG uv run python -m scryfall_mcp

# プロファイリング
uv run python -m cProfile -o profile.stats main.py
```

## MCP実装の注意点

### stdioモード
- 標準出力には何も出力しない
- ログはstderrまたはファイルへ
- JSON通信を妨げない

### ツール定義
- 引数と戻り値の型を明確に
- エラーはMCPエラー形式で返す
- 長時間処理は進捗通知

## 多言語対応

### 設計方針
- 地域設定（ロケール）による自動切り替え
- フォールバック機能（未対応言語は英語表示）
- 動的ロード（必要な言語のみメモリ使用）

### サポート言語
- 日本語 (ja): 完全対応
- 英語 (en): ベース言語
- その他: 将来対応予定（独語、仏語、中国語等）

### カード名マッピング
- 各言語のマッピングファイルを分離
- 頻出カード優先の段階的実装

### 検索構文変換（多言語）
```python
# 日本語
colors = {"白": "w", "青": "u", "黒": "b", "赤": "r", "緑": "g"}
types = {"クリーチャー": "creature", "インスタント": "instant"}
operators = {"以下": "<=", "以上": ">=", "より大きい": ">"}

# 英語（ベース）
colors = {"white": "w", "blue": "u", "black": "b", "red": "r", "green": "g"}
```

### 地域別の価格対応
- 通貨自動変換（USD → JPY, EUR等）
- 地域別の価格表示設定
- タイムゾーン考慮した価格更新

## セキュリティ

- 環境変数で機密情報管理
- 入力値のサニタイズ必須
- ログに個人情報・APIキー出力禁止

## ライセンス

- Wizards of the Coastのファンコンテンツポリシー遵守
- 価格情報は推定値である旨明記
- 商用利用時は出典表示必須

## トラブルシューティング

### よくあるエラー

| エラー | 原因 | 対処 |
|--------|------|------|
| 429 | レート制限 | SCRYFALL_RATE_LIMIT_MSを増加 |
| 403 | ヘッダー不足 | User-Agent/Acceptヘッダー確認 |
| Redis接続失敗 | サーバー未起動 | redis-server起動 |

## CI/CD

GitHub Actionsで以下を実行します。
1. リント・フォーマットチェック
2. 型チェック
3. テスト実行
4. カバレッジ測定

## ドキュメント規約

### ファイル命名規則
- docs/直下のファイル名は**すべて大文字**で統一すること
- 拡張子は.mdを使用
- 例: API-REFERENCE.md, CONFIGURATION.md, DEVELOPMENT.md

### ドキュメント構成
- API-REFERENCE.md: MCPツール仕様とScryfall検索構文
- CONFIGURATION.md: 環境変数設定ガイド
- DEVELOPMENT.md: 開発環境セットアップと規約
- INTERNATIONALIZATION.md: 多言語対応の実装ガイド
