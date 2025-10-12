# リファクタリングと結合テスト改善の推奨事項

調査日: 2025-10-12
調査対象: Scryfall MCP Server全体

## 📊 調査結果サマリー

### 現在のコード品質
- **総行数**: 6,465行（src/）
- **複雑度の高い関数**: 7個
- **テストカバレッジ**: builder.py 99%, locales.py 98%
- **既存の結合テスト**: 5ファイル

## 🔴 高優先度: リファクタリングが必要な箇所

### 1. `search/presenter.py` - `_format_single_card()`
**問題**:
- 複雑度: 16 (推奨: ≤10)
- 分岐数: 21 (推奨: ≤12)
- 行数: 99行

**原因**:
```python
# 日本語/英語の条件分岐が大量に重複
if is_japanese:
    card_text += f"**タイプ**: {type_line_display}\n"
else:
    card_text += f"**Type**: {type_line_display}\n"
```

**リファクタリング案**:

#### 案A: テンプレートメソッドパターン
```python
class CardFormatter:
    """Base card formatter."""
    @abstractmethod
    def format_type_line(self, type_line: str) -> str:
        pass

    @abstractmethod
    def format_power_toughness(self, power: str, toughness: str) -> str:
        pass

class JapaneseCardFormatter(CardFormatter):
    def format_type_line(self, type_line: str) -> str:
        return f"**タイプ**: {type_line}\n"

    def format_power_toughness(self, power: str, toughness: str) -> str:
        return f"**パワー/タフネス**: {power}/{toughness}\n"

class EnglishCardFormatter(CardFormatter):
    def format_type_line(self, type_line: str) -> str:
        return f"**Type**: {type_line}\n"

    def format_power_toughness(self, power: str, toughness: str) -> str:
        return f"**Power/Toughness**: {power}/{toughness}\n"
```

#### 案B: 翻訳辞書の使用（シンプル）
```python
# i18n/constants.pyに追加
CARD_LABELS = {
    "ja": {
        "type": "タイプ",
        "power_toughness": "パワー/タフネス",
        "oracle_text": "効果",
        "set": "セット",
        "view_on_scryfall": "Scryfallで詳細を見る",
    },
    "en": {
        "type": "Type",
        "power_toughness": "Power/Toughness",
        "oracle_text": "Oracle Text",
        "set": "Set",
        "view_on_scryfall": "View on Scryfall",
    }
}

# presenter.pyで使用
def _format_single_card(self, card: Card, index: int, options: SearchOptions) -> TextContent:
    labels = CARD_LABELS[self._mapping.language_code]
    card_text = f"## {index}. {card_name}\n\n"

    if type_line_display:
        card_text += f"**{labels['type']}**: {type_line_display}\n"

    if card.power is not None and card.toughness is not None:
        card_text += f"**{labels['power_toughness']}**: {card.power}/{card.toughness}\n"
    # ...
```

**推奨**: 案B（翻訳辞書）- シンプルで保守性が高い

**効果**:
- 複雑度: 16 → 8 (50%削減)
- 分岐数: 21 → 10 (52%削減)
- 行数: 99 → 60 (39%削減)

---

### 2. `search/processor.py` - `get_query_explanation()`
**問題**:
- 複雑度: 18 (推奨: ≤10)
- 分岐数: 17 (推奨: ≤12)
- 行数: 111行

**原因**:
```python
# 日本語/英語のマッピング辞書が重複
if self._mapping.language_code == "ja":
    color_names = {"w": "白", "u": "青", ...}
    type_names = {"creature": "クリーチャー", ...}
    op_name = {">=": "以上", "<=": "以下", ...}
else:
    # 英語版の同じロジック
```

**リファクタリング案**:

#### 案: マッピング辞書をi18n/constants.pyに移動
```python
# i18n/constants.py
QUERY_EXPLANATION_MAPPINGS = {
    "ja": {
        "colors": {"w": "白", "u": "青", "b": "黒", "r": "赤", "g": "緑", "c": "無色"},
        "types": {
            "creature": "クリーチャー",
            "artifact": "アーティファクト",
            "enchantment": "エンチャント",
            "instant": "インスタント",
            "sorcery": "ソーサリー",
            "land": "土地",
            "planeswalker": "プレインズウォーカー",
        },
        "operators": {
            ">=": "以上",
            "<=": "以下",
            ">": "より大きい",
            "<": "未満",
            "=": "等しい",
        },
        "fields": {
            "mv": "マナ総量",
            "cmc": "点数で見たマナコスト",
        },
        "labels": {
            "colors": "色",
            "types": "タイプ",
            "power": "パワー",
            "toughness": "タフネス",
            "general_search": "一般的な検索",
        }
    },
    "en": {
        "colors": {"w": "W", "u": "U", "b": "B", "r": "R", "g": "G", "c": "C"},
        "types": {
            "creature": "Creature",
            "artifact": "Artifact",
            # ... 英語版は基本的に大文字化のみ
        },
        "operators": {
            ">=": ">=",
            "<=": "<=",
            ">": ">",
            "<": "<",
            "=": "=",
        },
        "fields": {
            "mv": "Mana Value",
            "cmc": "CMC",
        },
        "labels": {
            "colors": "Colors",
            "types": "Types",
            "power": "Power",
            "toughness": "Toughness",
            "general_search": "General search",
        }
    }
}

# processor.pyで使用
def get_query_explanation(self, query: str) -> str:
    mappings = QUERY_EXPLANATION_MAPPINGS[self._mapping.language_code]
    parts = []

    color_matches = re.findall(r"c:([wubrgc]+)", query, re.IGNORECASE)
    if color_matches:
        colors = [mappings["colors"].get(c, c) for match in color_matches for c in match]
        parts.append(f"{mappings['labels']['colors']}: {', '.join(colors)}")

    # 他のマッチングも同様にシンプル化
    return ", ".join(parts) if parts else mappings["labels"]["general_search"]
```

**効果**:
- 複雑度: 18 → 9 (50%削減)
- 分岐数: 17 → 8 (53%削減)
- 行数: 111 → 55 (50%削減)
- 保守性: マッピング辞書が一元管理され、変更が容易

---

### 3. `search/parser.py` - `_extract_entities()`
**問題**:
- 複雑度: 11 (推奨: ≤10)
- 行数: 複雑なネストしたロジック

**リファクタリング案**: 小さなヘルパーメソッドに分割
```python
def _extract_entities(self, text: str) -> dict[str, list[str]]:
    """Extract entities from text."""
    return {
        "colors": self._extract_colors(text),
        "types": self._extract_types(text),
        "keywords": self._extract_keywords(text),
        "operators": self._extract_operators(text),
    }

def _extract_colors(self, text: str) -> list[str]:
    """Extract color entities."""
    colors = []
    # シンプルな色抽出ロジック
    return colors

def _extract_types(self, text: str) -> list[str]:
    """Extract type entities."""
    # ...
```

---

### 4. `errors/handlers.py` - `handle_error()`
**問題**:
- 複雑度: 11 (推奨: ≤10)
- 長いif-elif-elseチェーン

**リファクタリング案**: ディスパッチテーブル
```python
# エラータイプごとのハンドラーマッピング
ERROR_HANDLERS = {
    ScryfallAPIError: _handle_api_error,
    CacheError: _handle_cache_error,
    ValidationError: _handle_validation_error,
    TimeoutError: _handle_timeout_error,
    # ...
}

def handle_error(error: Exception) -> ErrorResponse:
    """Handle errors using dispatch table."""
    error_type = type(error)
    handler = ERROR_HANDLERS.get(error_type, _handle_generic_error)
    return handler(error)

def _handle_api_error(error: ScryfallAPIError) -> ErrorResponse:
    """Handle Scryfall API errors."""
    # ...

def _handle_cache_error(error: CacheError) -> ErrorResponse:
    """Handle cache errors."""
    # ...
```

---

## 🟡 中優先度: 改善が望ましい箇所

### 5. `api/client.py` - 関数の引数が多すぎる
```python
# 現在: 8個の引数
def search_cards(self, query, unique, order, dir, include_extras,
                 include_multilingual, include_variations, page):
    pass

# 改善: データクラスでグループ化
@dataclass
class SearchParams:
    query: str
    unique: str = "cards"
    order: str = "name"
    dir: str = "auto"
    include_extras: bool = False
    include_multilingual: bool = False
    include_variations: bool = False
    page: int = 1

def search_cards(self, params: SearchParams):
    pass
```

---

## 🟢 結合テストの不足箇所

### 優先度A: エンドツーエンドのクエリパイプラインテスト

**不足している内容**:
現在の結合テストはツール単位のテストのみで、Parser→Builder→Processor→Presenterの全体フローをテストしていない。

**追加すべきテスト**:
```python
# tests/integration/test_e2e_query_pipeline.py

class TestEndToEndQueryPipeline:
    """Test complete query processing pipeline."""

    async def test_japanese_keyword_ability_e2e(self):
        """Test Japanese keyword ability search end-to-end.

        Tests Issue #2 implementation through the entire stack.
        """
        # 日本語の自然言語クエリ
        query = "飛行を持つ赤いクリーチャーでパワー3以上"

        # Parser
        parsed = parser.parse(query)
        assert "飛行" in parsed.entities["keywords"]

        # Builder
        built = builder.build(parsed)
        assert "keyword:flying" in built.scryfall_query
        assert "c:r" in built.scryfall_query
        assert "p>=3" in built.scryfall_query

        # Processor (API呼び出し)
        result = await processor.process(built.scryfall_query)
        assert result.total_cards > 0

        # Presenter
        formatted = presenter.format(result)
        assert "飛行" in formatted or "Flying" in formatted

    async def test_complex_japanese_query_e2e(self):
        """Test complex Japanese query end-to-end."""
        query = "白と青のクリーチャーでマナ総量3以下の伝説の"
        # 全パイプラインのテスト

    async def test_english_query_e2e(self):
        """Test English query end-to-end."""
        query = "red creatures with haste and power greater than 3"
        # 全パイプラインのテスト
```

### 優先度B: キャッシュ統合テスト

**不足している内容**:
キャッシュとAPI呼び出しの統合が結合テストで検証されていない。

**追加すべきテスト**:
```python
# tests/integration/test_cache_integration.py

class TestCacheIntegration:
    """Test cache integration with API calls."""

    async def test_cache_hit_reduces_api_calls(self):
        """Verify cache hits reduce API calls."""
        query = "c:r t:creature"

        # First call - cache miss
        start = time.time()
        result1 = await search(query)
        first_call_time = time.time() - start

        # Second call - cache hit
        start = time.time()
        result2 = await search(query)
        second_call_time = time.time() - start

        assert result1 == result2
        assert second_call_time < first_call_time * 0.5  # 50%以上高速

    async def test_cache_respects_locale(self):
        """Verify cache stores results per locale."""
        query = "Lightning Bolt"

        # English
        result_en = await search(query, locale="en")

        # Japanese
        result_ja = await search(query, locale="ja")

        # Should have different presentations
        assert result_en != result_ja
```

### 優先度C: エラーハンドリングのエンドツーエンド

**不足している内容**:
エラーが発生した際のエンドツーエンドの挙動が検証されていない。

**追加すべきテスト**:
```python
# tests/integration/test_error_handling_e2e.py

class TestErrorHandlingEndToEnd:
    """Test error handling across the entire stack."""

    async def test_invalid_query_handling(self):
        """Test handling of invalid Scryfall queries."""
        invalid_queries = [
            "c:purple",  # Invalid color
            "t:invalid_type",  # Invalid type
            "p:abc",  # Invalid power value
        ]

        for query in invalid_queries:
            result = await search_cards(query)
            assert result.is_error
            assert result.error_message is not None

    async def test_api_error_recovery(self):
        """Test recovery from API errors."""
        # Rate limit exceeded
        # Network timeout
        # 500 error

    async def test_cache_error_fallback(self):
        """Test fallback when cache fails."""
        # キャッシュが失敗してもAPIから取得できることを確認
```

### 優先度D: 多言語対応のエンドツーエンド

**不足している内容**:
Issue #4で提案された長文クエリのテストがない。

**追加すべきテスト**:
```python
# tests/integration/test_multilingual_e2e.py

class TestMultilingualEndToEnd:
    """Test multilingual support end-to-end."""

    async def test_japanese_long_form_query(self):
        """Test Japanese long-form queries (Issue #4)."""
        # 長文クエリのテスト
        long_queries = [
            "死亡時にカードを1枚引く黒いクリーチャー",
            "戦場に出たときにトークンを生成する白のエンチャント",
        ]

        for query in long_queries:
            result = await search_cards(query, locale="ja")
            # 現状はPhase 1実装のため部分的にマッチすればOK
            assert result.total_cards >= 0

    async def test_locale_switching(self):
        """Test switching locales mid-session."""
        # 英語で検索
        result_en = await search_cards("Lightning Bolt", locale="en")

        # 日本語で検索
        result_ja = await search_cards("稲妻", locale="ja")

        # 同じカードを指しているはず
        assert result_en.cards[0].name == result_ja.cards[0].name
```

---

## 📝 実装の優先順位

### Phase 1 (即座に実施可能)
1. ✅ **presenter.py**: 翻訳辞書リファクタリング（1-2時間）
2. ✅ **processor.py**: マッピング辞書の外部化（1-2時間）

### Phase 2 (短期的に実施)
3. **parser.py**: ヘルパーメソッド分割（2-3時間）
4. **handlers.py**: ディスパッチテーブル化（2-3時間）
5. **E2Eテスト**: クエリパイプラインテスト（3-4時間）

### Phase 3 (中長期的に実施)
6. **client.py**: 引数のデータクラス化（2-3時間）
7. **キャッシュ統合テスト**（2-3時間）
8. **エラーハンドリングE2Eテスト**（2-3時間）
9. **多言語E2Eテスト**（2-3時間）

---

## 📈 期待される効果

### コード品質
- **複雑度**: 平均30-50%削減
- **保守性**: マッピング辞書の一元管理により変更が容易に
- **可読性**: 関数が短く、責任が明確に

### テストカバレッジ
- **結合テスト**: 5ファイル → 9ファイル（+80%）
- **E2Eカバレッジ**: クリティカルパスの完全検証
- **バグ検出**: 早期発見・早期修正

### 開発効率
- **新機能追加**: リファクタリングにより影響範囲が明確に
- **デバッグ**: 小さな関数により問題箇所の特定が容易に
- **多言語対応**: 新しい言語の追加が簡単に

---

## 🎯 まとめ

現在のコードベースは全体的に高品質ですが、以下の改善により更に向上します：

1. **複雑な関数のリファクタリング**: 4つの高複雑度関数を簡略化
2. **マッピング辞書の一元管理**: i18n/constants.pyへの集約
3. **E2E結合テストの追加**: クリティカルパスの完全検証

これらの改善により、保守性・可読性・テスト性が大幅に向上し、今後の機能追加や多言語対応がより容易になります。
