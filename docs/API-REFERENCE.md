# API仕様書

## MCPツール一覧

### search_cards

Magic: The Gatheringのカードを検索します。

#### パラメータ

| パラメータ | 型 | 必須 | デフォルト | 説明 |
|------------|----|----|-----------|------|
| `query` | string | ✓ | - | 検索クエリ（自然言語またはScryfall構文） |
| `language` | string | - | null | 言語コード（"en", "ja"） |
| `max_results` | integer | - | 20 | 最大検索結果数（1-100） |
| `include_images` | boolean | - | true | 画像を含めるか |
| `format_filter` | string | - | null | フォーマット指定（"standard", "modern"等） |

#### レスポンス

```json
[
  {
    "type": "text",
    "text": "検索結果サマリー"
  },
  {
    "type": "image",
    "data": "base64画像データ",
    "mimeType": "image/jpeg"
  }
]
```

#### 使用例

```python
# 基本検索
search_cards({
    "query": "Lightning Bolt"
})

# 日本語検索
search_cards({
    "query": "白いクリーチャー",
    "language": "ja",
    "max_results": 10
})

# フォーマット指定
search_cards({
    "query": "counterspell",
    "format_filter": "standard"
})
```

### autocomplete_card_names

カード名の自動補完を提供します。

#### パラメータ

| パラメータ | 型 | 必須 | デフォルト | 説明 |
|------------|----|----|-----------|------|
| `query` | string | ✓ | - | 補完対象の文字列 |
| `language` | string | - | null | 言語コード |

#### レスポンス

```json
[
  {
    "type": "text",
    "text": "候補リスト"
  }
]
```

#### 使用例

```python
# カード名補完
autocomplete_card_names({
    "query": "Light"
})
# 結果: ["Lightning Bolt", "Lightning Strike", "Lightning Helix"]
```

## Scryfall検索構文

### 基本検索

| 構文 | 説明 | 例 |
|------|------|-------|
| `name:カード名` | 名前検索 | `name:"Lightning Bolt"` |
| `type:タイプ` | タイプライン検索 | `type:creature` |
| `color:色` | 色指定 | `color:red` |
| `mana:コスト` | マナコスト検索 | `mana:{1}{R}` |

### 高度な検索

| 構文 | 説明 | 例 |
|------|------|-------|
| `power>=X` | パワー条件 | `power>=3` |
| `cmc<=X` | マナ総量条件 | `cmc<=4` |
| `format:フォーマット` | フォーマット指定 | `format:standard` |
| `set:セット` | セット指定 | `set:znr` |

### 日本語検索対応

#### 色の指定

| 日本語 | 英語 | Scryfall構文 |
|--------|------|-------------|
| 白 | white | c:w |
| 青 | blue | c:u |
| 黒 | black | c:b |
| 赤 | red | c:r |
| 緑 | green | c:g |

#### タイプの指定

| 日本語 | 英語 | Scryfall構文 |
|--------|------|-------------|
| クリーチャー | creature | t:creature |
| インスタント | instant | t:instant |
| ソーサリー | sorcery | t:sorcery |
| エンチャント | enchantment | t:enchantment |
| アーティファクト | artifact | t:artifact |

#### 演算子

| 日本語 | 英語 | Scryfall構文 |
|--------|------|-------------|
| 以上 | greater than or equal | >= |
| 以下 | less than or equal | <= |
| より大きい | greater than | > |
| 未満 | less than | < |
| 等しい | equal | = |

## エラーハンドリング

### エラーレスポンス

```json
[
  {
    "type": "text",
    "text": "エラー: 検索に失敗しました。詳細: Invalid query syntax"
  }
]
```

### 一般的なエラー

| エラー | 原因 | 対処法 |
|--------|------|--------|
| Invalid query | 構文エラー | 検索構文を確認 |
| No results found | 結果なし | 検索条件を緩和 |
| Rate limit exceeded | レート制限 | 少し待ってから再試行 |
| Service unavailable | サービス停止 | 時間をおいて再試行 |

## レート制限

- **制限**: 10リクエスト/秒
- **リトライ**: 指数バックオフで自動リトライ
- **サーキットブレーカー**: 連続失敗時は一時停止

## キャッシュ

- **検索結果**: 30分
- **カード詳細**: 24時間
- **価格情報**: 6時間
- **セット情報**: 1週間