# 多言語対応ガイド

## 概要

Scryfall MCP Serverは、日本語と英語のバイリンガル対応を提供し、自然言語での検索クエリを正しいScryfall API構文に変換します。

## 対応言語

### 現在サポート中

- **英語 (en)**: ベース言語、完全対応
- **日本語 (ja)**: カード名、検索語、自然言語クエリ対応

### 将来対応予定

- ドイツ語 (de)
- フランス語 (fr)
- 中国語 (zh)
- スペイン語 (es)

## 言語検出と切り替え

### 自動検出

```python
# 環境変数での設定
SCRYFALL_MCP_DEFAULT_LOCALE=ja

# システムロケールからの自動検出
import locale
system_locale = locale.getdefaultlocale()[0]  # "ja_JP" -> "ja"
```

### 手動指定

```python
# ツール呼び出し時に言語指定
search_cards({
    "query": "白いクリーチャー",
    "language": "ja"
})

# プログラムからの設定
from scryfall_mcp.i18n import set_current_locale
set_current_locale("ja")
```

## 日本語の検索機能

### カード名のネイティブサポート

日本語のカード名は、Scryfallの`printed_name`フィールドと`lang:`パラメータによるネイティブサポートにより、事前翻訳なしで直接検索できます。

```python
# 日本語カード名をそのまま使用
"稲妻" -> Scryfallが自動的に "Lightning Bolt" とマッチング
"平地" -> Scryfallが自動的に "Plains" とマッチング
"島" -> Scryfallが自動的に "Island" とマッチング

# lang: パラメータで言語フィルタリング
query = "稲妻 lang:ja"  # 日本語版のみ検索
query = "Lightning Bolt lang:ja"  # 英語名で日本語版を検索
```

**利点**:
- 全27000+カードに自動対応
- 新セットの手動登録が不要
- Scryfallのファジーマッチングを活用
- 複数言語の同時サポート

### 色の指定

```python
# 日本語色名 -> Scryfall構文
"白いクリーチャー" -> "c:w t:creature"
"青のインスタント" -> "c:u t:instant"
"赤いソーサリー" -> "c:r t:sorcery"
"緑のエンチャント" -> "c:g t:enchantment"
"黒いアーティファクト" -> "c:b t:artifact"
```

### カードタイプの変換

```python
# 日本語タイプ -> Scryfall構文
"クリーチャー" -> "t:creature"
"インスタント" -> "t:instant"
"ソーサリー" -> "t:sorcery"
"エンチャント" -> "t:enchantment"
"アーティファクト" -> "t:artifact"
"プレインズウォーカー" -> "t:planeswalker"
"土地" -> "t:land"
```

### 数値・演算子の変換

```python
# 全角数字 -> 半角数字
"３" -> "3"
"１０" -> "10"

# 日本語演算子 -> Scryfall演算子
"以上" -> ">="
"以下" -> "<="
"より大きい" -> ">"
"未満" -> "<"
"等しい" -> "="
```

### 複合クエリの例

```python
# 複雑な日本語クエリ
"パワー３以上の赤いクリーチャーでマナ総量５以下"
# ↓ 変換後
"p>=3 c:r t:creature mv<=5"

# マナコスト指定
"マナコスト２の白いクリーチャー"
# ↓ 変換後
"mv=2 c:w t:creature"
```

## マッピングシステム

### 言語マッピングの構造

```python
# src/scryfall_mcp/i18n/mappings/ja.py
JAPANESE_MAPPING = LanguageMapping(
    language_code="ja",
    language_name="日本語",
    colors={
        "白": "w",
        "青": "u",
        # ...
    },
    types={
        "クリーチャー": "creature",
        "インスタント": "instant",
        # ...
    },
    operators={
        "以上": ">=",
        "以下": "<=",
        # ...
    },
    # 注: card_names辞書は非推奨
    # Scryfallがネイティブに多言語カード名をサポートするため、
    # 事前翻訳辞書は不要になりました
)
```

### カード名検索の実装

```python
# 旧方式（非推奨）: 静的辞書による事前翻訳
# card_names = {"稲妻": "Lightning Bolt", ...}
# translated = card_names.get(japanese_name)

# 新方式（推奨）: Scryfallネイティブサポート
def _convert_card_names(self, text: str) -> str:
    """日本語カード名をそのまま渡す"""
    return text  # Scryfallが自動的に多言語名を処理

# 検索時にlang:パラメータを追加
if language == "ja":
    query += " lang:ja"

# include_multilingual=Trueで多言語データを取得
result = await client.search_cards(
    query=query,
    include_multilingual=True
)
```

### 新しい言語の追加

1. **マッピングファイルの作成**

```python
# src/scryfall_mcp/i18n/mappings/de.py (ドイツ語の例)
GERMAN_MAPPING = LanguageMapping(
    language_code="de",
    language_name="Deutsch",
    colors={
        "weiß": "w",
        "blau": "u",
        "schwarz": "b",
        "rot": "r",
        "grün": "g",
    },
    types={
        "kreatur": "creature",
        "spontanzauber": "instant",
        # ...
    }
)
```

2. **マッピングの登録**

```python
# src/scryfall_mcp/i18n/mappings/__init__.py
from .de import GERMAN_MAPPING

AVAILABLE_MAPPINGS = {
    "en": ENGLISH_MAPPING,
    "ja": JAPANESE_MAPPING,
    "de": GERMAN_MAPPING,  # 追加
}
```

3. **設定の更新**

```python
# settings.py
supported_locales: list[str] = Field(
    default=["en", "ja", "de"],  # "de"を追加
    description="List of supported locales"
)
```

## 自然言語処理

### 意図検出

```python
def detect_intent(text: str) -> str:
    """クエリの意図を検出"""
    if re.search(r"(デッキ|構築|メタ)", text):
        return "deck_building"
    elif re.search(r"(価格|値段|相場)", text):
        return "price_search"
    else:
        return "card_search"
```

### エンティティ抽出

```python
def extract_entities(text: str) -> dict[str, list[str]]:
    """クエリからエンティティを抽出"""
    entities = {
        "colors": [],
        "types": [],
        "card_names": [],  # 引用符で囲まれたカード名のみ
        "numbers": [],
    }

    # 色の抽出
    for ja_color, en_color in color_mapping.items():
        if ja_color in text:
            entities["colors"].append(en_color)

    # 引用符で囲まれたカード名を抽出
    quoted_names = re.findall(r'"([^"]+)"', text)
    entities["card_names"].extend(quoted_names)

    # 注: 引用符なしの日本語カード名は抽出しない
    # Scryfallが検索時に自動的に処理する

    return entities
```

## 出力の多言語化

### レスポンス言語の制御

```python
def format_search_summary(
    processed: dict[str, Any],
    total_cards: int,
    shown_cards: int,
    language: Optional[str]
) -> str:
    """検索結果サマリーを言語に応じてフォーマット"""
    if language == "ja":
        return f"""
検索結果: {processed['original_query']}
クエリ: {processed['scryfall_query']}
総カード数: {total_cards}
表示: {shown_cards}
        """.strip()
    else:
        return f"""
Search Results: {processed['original_query']}
Query: {processed['scryfall_query']}
Total cards: {total_cards}
Showing: {shown_cards}
        """.strip()
```

### エラーメッセージの多言語化

```python
def get_error_message(error_type: str, language: str) -> str:
    """エラーメッセージを取得"""
    messages = {
        "no_results": {
            "en": "No cards found for your search.",
            "ja": "検索条件に一致するカードが見つかりませんでした。"
        },
        "invalid_query": {
            "en": "Invalid search query. Please check your syntax.",
            "ja": "検索クエリが無効です。構文を確認してください。"
        }
    }
    return messages.get(error_type, {}).get(language, messages[error_type]["en"])
```

## 設定とカスタマイズ

### 言語設定

```bash
# デフォルト言語の設定
SCRYFALL_MCP_DEFAULT_LOCALE=ja

# サポート言語の設定
SCRYFALL_MCP_SUPPORTED_LOCALES=["en", "ja", "de"]

# フォールバック言語
SCRYFALL_MCP_FALLBACK_LOCALE=en
```

### ユーザー言語の優先順位

1. **ツール引数での指定** (`language` パラメータ)
2. **環境変数** (`SCRYFALL_MCP_DEFAULT_LOCALE`)
3. **システムロケール** (自動検出)
4. **フォールバック言語** (英語)

## パフォーマンス最適化

### マッピングのキャッシュ

```python
class LocaleManager:
    def __init__(self):
        self._mappings: dict[str, LanguageMapping] = {}
        self._cache: dict[str, str] = {}

    def translate_term(self, term: str, locale: str) -> str:
        """項目の翻訳（キャッシュ付き）"""
        cache_key = f"{locale}:{term}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # 翻訳処理
        result = self._do_translation(term, locale)
        self._cache[cache_key] = result
        return result
```

### 遅延ロード

```python
def get_mapping(locale: str) -> LanguageMapping:
    """マッピングの遅延ロード"""
    if locale not in _loaded_mappings:
        if locale == "ja":
            from .mappings.ja import JAPANESE_MAPPING
            _loaded_mappings[locale] = JAPANESE_MAPPING
        # 他の言語も同様

    return _loaded_mappings[locale]
```

## テストとデバッグ

### 多言語テスト

```python
@pytest.mark.parametrize("locale,query,expected", [
    ("en", "white creatures", "c:w t:creature"),
    ("ja", "白いクリーチャー", "c:w t:creature"),
    ("de", "weiße Kreaturen", "c:w t:creature"),
])
def test_query_translation(locale, query, expected):
    set_current_locale(locale)
    builder = QueryBuilder()
    result = builder.build_query(query)
    assert expected in result
```

### デバッグ情報

```python
# デバッグモードでの詳細ログ
SCRYFALL_MCP_DEBUG=true

# 翻訳プロセスの追跡
logger.debug(f"Original query: {original_query}")
logger.debug(f"Detected locale: {detected_locale}")
logger.debug(f"Translated query: {translated_query}")
```

## ベストプラクティス

1. **段階的な翻訳**: 完全な翻訳より段階的な改善
2. **フォールバック**: 翻訳できない場合は英語で継続
3. **ユーザーフィードバック**: 翻訳精度の改善に活用
4. **文脈考慮**: 単語単位でなく文脈を考慮した翻訳
5. **テストカバレッジ**: 各言語での包括的テスト