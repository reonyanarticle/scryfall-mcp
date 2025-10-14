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
