"""Tests for query builder module."""

from __future__ import annotations

import pytest

from scryfall_mcp.i18n import set_current_locale
from scryfall_mcp.search.builder import QueryBuilder


class TestQueryBuilder:
    """Test QueryBuilder class."""

    @pytest.fixture
    def query_builder(self):
        """Create a query builder for testing."""
        return QueryBuilder()

    @pytest.fixture(autouse=True)
    def reset_locale(self):
        """Reset locale to English before each test."""
        set_current_locale("en")
        yield
        set_current_locale("en")

    def test_initialization(self, query_builder):
        """Test query builder initialization."""
        assert query_builder._mapping is not None
        assert query_builder._mapping.language_code == "en"

    def test_normalize_text_basic(self, query_builder):
        """Test basic text normalization."""
        # Test whitespace normalization
        result = query_builder._normalize_text("  hello   world  ")
        assert result == "hello world"

        # Test multiple spaces
        result = query_builder._normalize_text("hello\t\n  world")
        assert result == "hello world"

    def test_normalize_text_japanese(self, query_builder):
        """Test Japanese text normalization."""
        set_current_locale("ja")
        query_builder = QueryBuilder()  # Recreate with Japanese locale

        # Test full-width number conversion
        result = query_builder._normalize_text("パワー３以上")
        assert result == "パワー3以上"

        # Test full-width operators
        result = query_builder._normalize_text("マナコスト＝３")
        assert result == "マナコスト=3"

    def test_convert_fullwidth_numbers(self, query_builder):
        """Test full-width number conversion."""
        test_cases = [
            ("１２３", "123"),
            ("０", "0"),
            ("９", "9"),
            ("パワー３", "パワー3"),
            ("１２３ＡＢＣ", "123ＡＢＣ"),  # Only numbers converted
        ]

        for input_text, expected in test_cases:
            result = query_builder._convert_fullwidth_numbers(input_text)
            assert result == expected

    def test_build_query_english(self, query_builder):
        """Test query building in English."""
        # Simple search
        result = query_builder.build_query("Lightning Bolt")
        assert result == "Lightning Bolt"

        # Color search
        result = query_builder.build_query("red creatures")
        assert "creature" in result.lower()

    def test_build_query_japanese(self, query_builder):
        """Test query building in Japanese."""
        set_current_locale("ja")
        query_builder = QueryBuilder()

        # Test Japanese color + type conversion
        result = query_builder.build_query("白いクリーチャー")
        assert "c:w" in result
        assert "t:creature" in result

        # Test Japanese card name conversion
        result = query_builder.build_query("稲妻")
        assert "Lightning Bolt" in result

    def test_convert_colors_japanese(self, query_builder):
        """Test Japanese color conversion."""
        set_current_locale("ja")
        query_builder = QueryBuilder()

        test_cases = [
            ("白いクリーチャー", "c:w t:creature"),
            ("青のアーティファクト", "c:u t:artifact"),
            ("赤いインスタント", "c:r t:instant"),
            ("緑のエンチャント", "c:g t:enchantment"),
            ("黒いソーサリー", "c:b t:sorcery"),
        ]

        for input_text, expected_part in test_cases:
            result = query_builder._convert_colors(input_text)
            assert expected_part in result

    def test_convert_operators_japanese(self, query_builder):
        """Test Japanese operator conversion."""
        set_current_locale("ja")
        query_builder = QueryBuilder()

        test_cases = [
            ("パワーが3以上", "p>=3"),
            ("パワー5以下", "p<=5"),
            ("パワーが2より大きい", "p>2"),
            ("パワー1未満", "p<1"),
            ("タフネスが4等しい", "tou=4"),
            ("タフネス3と等しい", "tou=3"),
            ("マナ総量2以上", "mv>=2"),
            ("点数で見たマナコスト5以下", "cmc<=5"),
        ]

        for input_text, expected in test_cases:
            result = query_builder._convert_operators(input_text)
            assert expected in result

    def test_convert_card_names_japanese(self, query_builder):
        """Test Japanese card name conversion."""
        set_current_locale("ja")
        query_builder = QueryBuilder()

        # Test basic lands
        test_cases = [
            ("平地", '"Plains"'),
            ("島", '"Island"'),
            ("稲妻", '"Lightning Bolt"'),
        ]

        for ja_name, expected in test_cases:
            result = query_builder._convert_card_names(ja_name)
            assert expected in result

    def test_convert_phrases_japanese(self, query_builder):
        """Test Japanese phrase conversion."""
        set_current_locale("ja")
        query_builder = QueryBuilder()

        test_cases = [
            ("を持つクリーチャー", "t:creature"),
            ("白のカード", "c:w"),
            ("価格が", "usd<"),
        ]

        for phrase, expected_part in test_cases:
            # Create text that includes the phrase
            test_text = f"何か{phrase}何か"
            result = query_builder._convert_phrases(test_text)
            if expected_part:  # Some phrases map to empty string
                assert expected_part in result

    def test_clean_query(self, query_builder):
        """Test query cleaning."""
        test_cases = [
            ("  c:w   t:creature  ", "c:w t:creature"),
            ("c : w", "c:w"),
            ("p >= 3", "p>=3"),
            ("power > = 2", "power>=2"),
            ("a  and  b", "a and b"),
        ]

        for input_query, expected in test_cases:
            result = query_builder._clean_query(input_query)
            assert result == expected

    def test_suggest_corrections_japanese(self, query_builder):
        """Test suggestion for Japanese corrections."""
        set_current_locale("ja")
        query_builder = QueryBuilder()

        # Test common misspellings
        suggestions = query_builder.suggest_corrections("くりーちゃー")
        assert len(suggestions) > 0
        assert any("クリーチャー" in suggestion for suggestion in suggestions)

    def test_get_search_help_japanese(self, query_builder):
        """Test search help in Japanese."""
        set_current_locale("ja")
        query_builder = QueryBuilder()

        help_info = query_builder.get_search_help()

        assert "色の指定" in help_info
        assert "パワー・タフネス" in help_info
        assert "マナコスト" in help_info
        assert "カードタイプ" in help_info

        # Check that help contains useful examples
        color_examples = help_info["色の指定"]
        assert any("白いクリーチャー" in example for example in color_examples)

    def test_get_search_help_english(self, query_builder):
        """Test search help in English."""
        help_info = query_builder.get_search_help()

        assert "Colors" in help_info
        assert "Power/Toughness" in help_info
        assert "Mana Cost" in help_info
        assert "Card Types" in help_info

        # Check that help contains useful examples
        color_examples = help_info["Colors"]
        assert any("white creatures" in example for example in color_examples)

    def test_build_query_with_locale_switch(self, query_builder):
        """Test building query with locale switching."""
        # Start with English
        result_en = query_builder.build_query("white creatures", "en")
        assert "white creatures" in result_en.lower()

        # Switch to Japanese
        result_ja = query_builder.build_query("白いクリーチャー", "ja")
        assert "c:w" in result_ja
        assert "t:creature" in result_ja

    def test_complex_japanese_query(self, query_builder):
        """Test complex Japanese query building."""
        set_current_locale("ja")
        query_builder = QueryBuilder()

        # Complex query with multiple Japanese elements
        complex_query = "パワー3以上の赤いクリーチャーでマナ総量5以下"
        result = query_builder.build_query(complex_query)

        # Should contain all converted parts
        assert "p>=3" in result
        assert "c:r" in result
        assert "t:creature" in result
        assert "mv<=5" in result

    def test_edge_cases(self, query_builder):
        """Test edge cases in query building."""
        # Empty query
        result = query_builder.build_query("")
        assert result == ""

        # Query with only spaces
        result = query_builder.build_query("   ")
        assert result == ""

        # Query with special characters
        result = query_builder.build_query('name:"Lightning Bolt"')
        assert result == 'name:"Lightning Bolt"'

    def test_mixed_language_query(self, query_builder):
        """Test query with mixed languages."""
        set_current_locale("ja")
        query_builder = QueryBuilder()

        # Mix of Japanese and English
        mixed_query = "白い creature パワー3以上"
        result = query_builder.build_query(mixed_query)

        # Should handle both languages
        assert "c:w" in result
        assert "p>=3" in result

    def test_operator_precedence(self, query_builder):
        """Test that operator conversion doesn't interfere with existing Scryfall syntax."""
        # Existing Scryfall syntax should be preserved or converted consistently
        scryfall_query = "c:w power>=3 cmc<=4"
        result = query_builder.build_query(scryfall_query)

        # Should be converted consistently
        assert "c:w" in result
        assert "p>=3" in result  # power gets converted to p
        assert "cmc<=4" in result

    def test_japanese_number_integration(self, query_builder):
        """Test integration of Japanese number conversion with operators."""
        set_current_locale("ja")
        query_builder = QueryBuilder()

        # Full-width numbers with operators
        query = "パワー３以上タフネス５以下"
        result = query_builder.build_query(query)

        assert "p>=3" in result
        assert "tou<=5" in result

    def test_basic_term_conversion(self, query_builder):
        """Test basic search term conversion."""
        set_current_locale("ja")
        query_builder = QueryBuilder()

        # Test individual term conversions
        test_cases = [
            ("色", "c"),
            ("タイプ", "t"),
            ("パワー", "p"),
            ("レアリティ", "r"),
        ]

        for ja_term, expected in test_cases:
            result = query_builder._convert_basic_terms(ja_term)
            assert expected in result
