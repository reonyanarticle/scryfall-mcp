# Scryfall MCP Server

Magic: The Gatheringのカード情報を提供するScryfall APIをMCP (Model Context Protocol)経由でAIアシスタントに接続するサーバー。
詳細はAPI Docmentationを参考にすること。https://scryfall.com/docs/api

## 主要機能

- Scryfall検索構文によるカード検索
- 自然言語からScryfall構文への変換
- カード価格情報の取得と通貨換算
- デッキ構成の統計分析
- 多言語カード名のサポート（日本語、英語、その他）
- 地域別価格表示とタイムゾーン対応

## プロジェクト構造

```
scryfall-mcp/
├── docs/                      # ドキュメント類置き場
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

これらのヘッダーがないと403でブロックされる。

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

### Python
- 型ヒントは必須。PEP585に準拠し、基本的にはpydanticを用いて記載。補助としてtypingモジュールを使用すること
- docstringは必須。Numpy styleで記載。
- 1関数1責任
- 早期リターン推奨

### 非同期処理
- I/O処理はすべてasync/await
- CPU boundは別プロセス
- タイムアウト必須設定

### 命名規則
- クラス: PascalCase
- 関数/変数: snake_case
- 定数: UPPER_SNAKE_CASE
- プライベート: _prefix

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

### 地域別価格対応
- 通貨自動変換（USD → JPY, EUR等）
- 地域別価格表示設定
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

GitHub Actionsで以下を実行:
1. リント・フォーマットチェック
2. 型チェック
3. テスト実行
4. カバレッジ測定
