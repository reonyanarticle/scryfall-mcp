"""Tests for search processor module."""

from __future__ import annotations

import pytest

from scryfall_mcp.i18n import set_current_locale
from scryfall_mcp.search.processor import SearchProcessor


class TestSearchProcessor:
    """Test SearchProcessor class."""

    @pytest.fixture
    def processor(self):
        """Create a search processor for testing."""
        return SearchProcessor()

    @pytest.fixture(autouse=True)
    def reset_locale(self):
        """Reset locale to English before each test."""
        set_current_locale("en")
        yield
        set_current_locale("en")

    def test_initialization(self, processor):
        """Test search processor initialization."""
        assert processor._mapping is not None
        assert processor._query_builder is not None
        assert processor._mapping.language_code == "en"

    async def test_process_query_english(self, processor):
        """Test processing English query."""
        result = await processor.process_query("Lightning Bolt")

        assert result["original_query"] == "Lightning Bolt"
        assert result["scryfall_query"] == "Lightning Bolt"
        assert result["detected_intent"] in ["card_search", "general_search"]
        assert result["language"] == "en"
        assert "extracted_entities" in result
        assert "suggestions" in result

    async def test_process_query_japanese(self, processor):
        """Test processing Japanese query."""
        set_current_locale("ja")
        processor = SearchProcessor()

        result = await processor.process_query("白いクリーチャー")

        assert result["original_query"] == "白いクリーチャー"
        assert "c:w" in result["scryfall_query"]
        assert "t:creature" in result["scryfall_query"]
        assert result["language"] == "ja"

    def test_detect_intent_english(self, processor):
        """Test intent detection in English."""
        test_cases = [
            ("find Lightning Bolt", "card_search"),
            ("search for creatures", "card_search"),
            ("show me artifacts", "card_search"),
            ("price of Black Lotus", "price_inquiry"),
            ("how much does this cost", "price_inquiry"),
            ("what does this card do", "rules_inquiry"),
            ("rules for flying", "rules_inquiry"),
            ("deck with blue cards", "deck_building"),
            ("build a deck", "deck_building"),
            ("random query", "general_search"),
        ]

        for query, expected_intent in test_cases:
            detected = processor._detect_intent(query)
            assert detected == expected_intent

    def test_detect_intent_japanese(self, processor):
        """Test intent detection in Japanese."""
        set_current_locale("ja")
        processor = SearchProcessor()

        test_cases = [
            ("稲妻を探して", "card_search"),
            ("クリーチャーを検索", "card_search"),
            ("カードを見つけて", "card_search"),
            ("価格を教えて", "price_inquiry"),
            ("値段はいくら", "price_inquiry"),
            ("ルールを説明", "rules_inquiry"),
            ("効果は何", "rules_inquiry"),
            ("デッキを構築", "deck_building"),
            ("採用したい", "deck_building"),
            ("適当なクエリ", "general_search"),
        ]

        for query, expected_intent in test_cases:
            detected = processor._detect_intent(query)
            assert detected == expected_intent

    def test_extract_entities_english(self, processor):
        """Test entity extraction in English."""
        query = "find red creatures with power greater than 3"
        entities = processor._extract_entities(query)

        assert "red" in entities["colors"]
        assert "creature" in entities["types"]
        assert "3" in entities["numbers"]

    def test_extract_entities_japanese(self, processor):
        """Test entity extraction in Japanese."""
        set_current_locale("ja")
        processor = SearchProcessor()

        query = "パワー3以上の赤いクリーチャー"
        entities = processor._extract_entities(query)

        assert "red" in entities["colors"]
        assert "creature" in entities["types"]
        assert "3" in entities["numbers"]

    def test_extract_entities_card_names(self, processor):
        """Test extraction of card names."""
        # Test quoted names
        query = 'find "Lightning Bolt" and "Black Lotus"'
        entities = processor._extract_entities(query)

        assert "Lightning Bolt" in entities["card_names"]
        assert "Black Lotus" in entities["card_names"]

    def test_extract_entities_japanese_card_names(self, processor):
        """Test that unquoted Japanese card names are NOT extracted as entities.

        Japanese card names are no longer extracted as distinct entities since
        we deprecated the static JAPANESE_CARD_NAMES dictionary. Unquoted card
        names remain as part of the query text and Scryfall handles them natively.

        Quoted card names (e.g., "稲妻") are still extracted.
        """
        set_current_locale("ja")
        processor = SearchProcessor()

        # Unquoted card names are NOT extracted
        query = "稲妻と平地を探して"
        entities = processor._extract_entities(query)
        assert len(entities["card_names"]) == 0

        # But quoted card names ARE extracted
        query_quoted = '"稲妻"と"平地"を探して'
        entities_quoted = processor._extract_entities(query_quoted)
        assert "稲妻" in entities_quoted["card_names"]
        assert "平地" in entities_quoted["card_names"]

    def test_extract_entities_comprehensive(self, processor):
        """Test comprehensive entity extraction."""
        query = "red and blue creatures with power 3 toughness 4 from standard"
        entities = processor._extract_entities(query)

        assert "red" in entities["colors"]
        assert "blue" in entities["colors"]
        assert "creature" in entities["types"]
        assert "3" in entities["numbers"]
        assert "4" in entities["numbers"]

    def test_suggest_query_improvements_english(self, processor):
        """Test query improvement suggestions in English."""
        # Vague query
        suggestions = processor.suggest_query_improvements("cards")
        assert len(suggestions) > 0
        assert any("colors" in suggestion.lower() for suggestion in suggestions)

        # Card name without quotes
        suggestions = processor.suggest_query_improvements(
            "Lightning Bolt without quotes"
        )
        assert any("quotes" in suggestion for suggestion in suggestions)

    def test_suggest_query_improvements_japanese(self, processor):
        """Test query improvement suggestions in Japanese."""
        set_current_locale("ja")
        processor = SearchProcessor()

        # Vague query
        suggestions = processor.suggest_query_improvements("カード")
        assert len(suggestions) > 0

        # Card name without quotes
        suggestions = processor.suggest_query_improvements("稲妻の検索")
        assert len(suggestions) > 0

    def test_validate_query_valid(self, processor):
        """Test validation of valid queries."""
        valid_queries = [
            "c:r t:creature",
            'name:"Lightning Bolt"',
            "power>=3 toughness<=5",
            "f:standard cmc<=4",
        ]

        for query in valid_queries:
            is_valid, errors = processor.validate_query(query)
            assert is_valid is True
            assert len(errors) == 0

    def test_validate_query_invalid(self, processor):
        """Test validation of invalid queries."""
        invalid_queries = [
            '"unmatched quotes',  # Unmatched quotes
            "power>>=3",  # Invalid operator
            "color:",  # Empty search term
        ]

        for query in invalid_queries:
            is_valid, errors = processor.validate_query(query)
            assert is_valid is False
            assert len(errors) > 0

    def test_validate_query_japanese_errors(self, processor):
        """Test query validation with Japanese error messages."""
        set_current_locale("ja")
        processor = SearchProcessor()

        is_valid, errors = processor.validate_query('"未完成の引用符')
        assert is_valid is False
        assert len(errors) > 0
        assert any("引用符" in error for error in errors)

    def test_get_query_explanation_english(self, processor):
        """Test query explanation in English."""
        query = "c:r t:creature p>=3"
        explanation = processor.get_query_explanation(query)

        assert "Colors: R" in explanation
        assert "Types: Creature" in explanation
        assert "Power >= 3" in explanation

    def test_get_query_explanation_japanese(self, processor):
        """Test query explanation in Japanese."""
        set_current_locale("ja")
        processor = SearchProcessor()

        query = "c:r t:creature p>=3"
        explanation = processor.get_query_explanation(query)

        assert "色: 赤" in explanation
        assert "タイプ: クリーチャー" in explanation
        assert "パワー3以上" in explanation

    def test_get_query_explanation_complex(self, processor):
        """Test explanation of complex queries."""
        query = "c:wu t:creature p>=3 tou<=5 mv=4"
        explanation = processor.get_query_explanation(query)

        assert "Colors: W, U" in explanation
        assert "Types: Creature" in explanation
        assert "Power >= 3" in explanation
        assert "Toughness <= 5" in explanation
        assert "Mana Value = 4" in explanation

    def test_get_query_explanation_empty(self, processor):
        """Test explanation of queries with no recognizable parts."""
        query = "random text without scryfall syntax"
        explanation = processor.get_query_explanation(query)

        assert explanation == "General search"

    def test_get_query_explanation_japanese_empty(self, processor):
        """Test explanation of empty queries in Japanese."""
        set_current_locale("ja")
        processor = SearchProcessor()

        query = "意味のないテキスト"
        explanation = processor.get_query_explanation(query)

        assert explanation == "一般的な検索"

    async def test_process_query_with_locale_switch(self, processor):
        """Test processing query with locale switching."""
        # Process English query
        result_en = await processor.process_query("white creatures", "en")
        assert result_en["language"] == "en"

        # Process Japanese query with explicit locale
        result_ja = await processor.process_query("白いクリーチャー", "ja")
        assert result_ja["language"] == "ja"
        assert "c:w" in result_ja["scryfall_query"]

    def test_entity_extraction_edge_cases(self, processor):
        """Test entity extraction edge cases."""
        # Empty query
        entities = processor._extract_entities("")
        assert all(len(entity_list) == 0 for entity_list in entities.values())

        # Query with no entities
        entities = processor._extract_entities("random text")
        assert all(len(entity_list) == 0 for entity_list in entities.values())

        # Query with multiple numbers
        entities = processor._extract_entities("power 1 2 3 toughness 4 5")
        numbers = entities["numbers"]
        assert "1" in numbers
        assert "2" in numbers
        assert "3" in numbers
        assert "4" in numbers
        assert "5" in numbers

    def test_competitive_query_suggestions(self, processor):
        """Test suggestions for competitive queries."""
        competitive_queries = [
            "tournament deck",
            "competitive creatures",
            "meta cards",
            "tier 1 deck",
        ]

        for query in competitive_queries:
            suggestions = processor.suggest_query_improvements(query)
            # Should suggest format restrictions
            assert any("format" in suggestion.lower() for suggestion in suggestions)

    def test_japanese_competitive_suggestions(self, processor):
        """Test competitive suggestions in Japanese."""
        set_current_locale("ja")
        processor = SearchProcessor()

        suggestions = processor.suggest_query_improvements("競技用のカード")
        assert len(suggestions) > 0

    def test_intent_detection_edge_cases(self, processor):
        """Test intent detection edge cases."""
        # Empty query
        intent = processor._detect_intent("")
        assert intent == "general_search"

        # Very short query
        intent = processor._detect_intent("a")
        assert intent == "general_search"

        # Mixed case
        intent = processor._detect_intent("FIND Lightning Bolt")
        assert intent == "card_search"

    async def test_query_processing_integration(self, processor):
        """Test complete query processing integration."""
        query = "find red creatures with power 3 or higher"
        result = await processor.process_query(query)

        # Check all expected fields are present
        required_fields = [
            "original_query",
            "scryfall_query",
            "detected_intent",
            "extracted_entities",
            "suggestions",
            "language",
        ]
        for field in required_fields:
            assert field in result

        # Check that scryfall query was properly built
        scryfall_query = result["scryfall_query"]
        assert isinstance(scryfall_query, str)

        # Check entities were extracted
        entities = result["extracted_entities"]
        assert "colors" in entities
        assert "types" in entities
        assert "numbers" in entities

    async def test_japanese_integration(self, processor):
        """Test complete Japanese processing integration."""
        set_current_locale("ja")
        processor = SearchProcessor()

        query = "パワー3以上の赤いクリーチャーを探して"
        result = await processor.process_query(query)

        assert result["original_query"] == query
        assert "c:r" in result["scryfall_query"]
        assert "t:creature" in result["scryfall_query"]
        assert "p>=3" in result["scryfall_query"]
        assert result["detected_intent"] == "card_search"
        assert result["language"] == "ja"

        # Check entities
        entities = result["extracted_entities"]
        assert "red" in entities["colors"]
        assert "creature" in entities["types"]
        assert "3" in entities["numbers"]
