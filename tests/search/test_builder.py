"""Tests for query builder module."""

from __future__ import annotations

import pytest

from scryfall_mcp.i18n import get_current_mapping, set_current_locale
from scryfall_mcp.search.builder import QueryBuilder


class TestQueryBuilder:
    """Test QueryBuilder class."""

    @pytest.fixture
    def query_builder(self):
        """Create a query builder for testing."""
        mapping = get_current_mapping()
        return QueryBuilder(mapping)

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
        mapping = get_current_mapping()
        query_builder = QueryBuilder(mapping)  # Recreate with Japanese locale

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
        mapping = get_current_mapping()
        query_builder = QueryBuilder(mapping)

        # Test Japanese color + type conversion
        result = query_builder.build_query("白いクリーチャー")
        assert "c:w" in result
        assert "t:creature" in result

        # Test Japanese card name pass-through (no conversion)
        result = query_builder.build_query("稲妻")
        # Card name should remain in Japanese - Scryfall handles multilingual lookup
        assert "稲妻" in result

    def test_convert_colors_japanese(self, query_builder):
        """Test Japanese color conversion."""
        set_current_locale("ja")
        mapping = get_current_mapping()
        query_builder = QueryBuilder(mapping)

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
        mapping = get_current_mapping()
        query_builder = QueryBuilder(mapping)

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
        """Test Japanese card name pass-through (no conversion).

        Japanese card names are now passed directly to Scryfall's API
        which natively supports multilingual card names via the printed_name
        field and lang: parameter.
        """
        set_current_locale("ja")
        mapping = get_current_mapping()
        query_builder = QueryBuilder(mapping)

        # Test that Japanese card names are passed through unchanged
        test_cases = [
            "平地",
            "島",
            "稲妻",
            "エイトグ",
            "アトガトグ",
        ]

        for ja_name in test_cases:
            result = query_builder._convert_card_names(ja_name)
            # Card names should be unchanged - Scryfall handles multilingual lookup
            assert result == ja_name

    def test_convert_phrases_japanese(self, query_builder):
        """Test Japanese phrase conversion."""
        set_current_locale("ja")
        mapping = get_current_mapping()
        query_builder = QueryBuilder(mapping)

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
        mapping = get_current_mapping()
        query_builder = QueryBuilder(mapping)

        # Test common misspellings
        suggestions = query_builder.suggest_corrections("くりーちゃー")
        assert len(suggestions) > 0
        assert any("クリーチャー" in suggestion for suggestion in suggestions)

    def test_get_search_help_japanese(self, query_builder):
        """Test search help in Japanese."""
        set_current_locale("ja")
        mapping = get_current_mapping()
        query_builder = QueryBuilder(mapping)

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
        mapping = get_current_mapping()
        query_builder = QueryBuilder(mapping)

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
        mapping = get_current_mapping()
        query_builder = QueryBuilder(mapping)

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
        mapping = get_current_mapping()
        query_builder = QueryBuilder(mapping)

        # Full-width numbers with operators
        query = "パワー３以上タフネス５以下"
        result = query_builder.build_query(query)

        assert "p>=3" in result
        assert "tou<=5" in result

    def test_basic_term_conversion(self, query_builder):
        """Test basic search term conversion."""
        set_current_locale("ja")
        mapping = get_current_mapping()
        query_builder = QueryBuilder(mapping)

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

    def test_japanese_keyword_ability_search_single(self, query_builder):
        """Test Japanese keyword ability search - single keyword.

        Tests implementation of Issue #2: キーワード能力による自然言語検索の精度向上
        Test Case 1: Single keyword ability with creature type.
        """
        set_current_locale("ja")
        mapping = get_current_mapping()
        query_builder = QueryBuilder(mapping)

        # Test single keyword abilities
        test_cases = [
            ("多相を持つクリーチャー", ["keyword:changeling", "t:creature"]),
            ("飛行を持つクリーチャー", ["keyword:flying", "t:creature"]),
            ("速攻持ちクリーチャー", ["keyword:haste", "t:creature"]),
            ("接死を持つクリーチャー", ["keyword:deathtouch", "t:creature"]),
            ("威迫を持つクリーチャー", ["keyword:menace", "t:creature"]),
        ]

        for input_query, expected_parts in test_cases:
            result = query_builder.build_query(input_query)
            for expected_part in expected_parts:
                assert expected_part in result, (
                    f"Expected '{expected_part}' in result for query '{input_query}', "
                    f"but got: {result}"
                )

    def test_japanese_keyword_ability_search_multiple(self, query_builder):
        """Test Japanese keyword ability search - multiple keywords.

        Tests implementation of Issue #2: キーワード能力による自然言語検索の精度向上
        Test Case 2: Multiple keyword abilities combined.
        """
        set_current_locale("ja")
        mapping = get_current_mapping()
        query_builder = QueryBuilder(mapping)

        # Test multiple keyword abilities
        test_cases = [
            (
                "速攻と飛行を持つクリーチャー",
                ["keyword:haste", "keyword:flying", "t:creature"],
            ),
            (
                "警戒と絆魂を持つクリーチャー",
                ["keyword:vigilance", "keyword:lifelink", "t:creature"],
            ),
            (
                "トランプルと接死持ちクリーチャー",
                ["keyword:trample", "keyword:deathtouch", "t:creature"],
            ),
        ]

        for input_query, expected_parts in test_cases:
            result = query_builder.build_query(input_query)
            for expected_part in expected_parts:
                assert expected_part in result, (
                    f"Expected '{expected_part}' in result for query '{input_query}', "
                    f"but got: {result}"
                )

    def test_japanese_keyword_ability_with_colors(self, query_builder):
        """Test Japanese keyword ability search combined with colors.

        Tests implementation of Issue #2: キーワード能力による自然言語検索の精度向上
        Test Case 3: Keyword abilities combined with color and type filters.
        """
        set_current_locale("ja")
        mapping = get_current_mapping()
        query_builder = QueryBuilder(mapping)

        # Test keyword abilities combined with colors
        test_cases = [
            (
                "飛行を持つ赤いクリーチャー",
                ["keyword:flying", "c:r", "t:creature"],
            ),
            (
                "速攻を持つ緑のクリーチャー",
                ["keyword:haste", "c:g", "t:creature"],
            ),
            (
                "威迫を持つ黒いクリーチャー",
                ["keyword:menace", "c:b", "t:creature"],
            ),
            (
                "絆魂を持つ白いクリーチャー",
                ["keyword:lifelink", "c:w", "t:creature"],
            ),
        ]

        for input_query, expected_parts in test_cases:
            result = query_builder.build_query(input_query)
            for expected_part in expected_parts:
                assert expected_part in result, (
                    f"Expected '{expected_part}' in result for query '{input_query}', "
                    f"but got: {result}"
                )

    def test_japanese_keyword_ability_quoted_keywords(self, query_builder):
        """Test Japanese keyword abilities that require quotes in Scryfall syntax.

        Tests implementation of Issue #2: キーワード能力による自然言語検索の精度向上
        Special test for multi-word keyword abilities like "first strike" and "double strike".
        """
        set_current_locale("ja")
        mapping = get_current_mapping()
        query_builder = QueryBuilder(mapping)

        # Test keyword abilities that require quotes
        test_cases = [
            ("先制攻撃を持つクリーチャー", ['keyword:"first strike"', "t:creature"]),
            ("二段攻撃を持つクリーチャー", ['keyword:"double strike"', "t:creature"]),
            (
                "先制攻撃と飛行を持つクリーチャー",
                ['keyword:"first strike"', "keyword:flying", "t:creature"],
            ),
        ]

        for input_query, expected_parts in test_cases:
            result = query_builder.build_query(input_query)
            for expected_part in expected_parts:
                assert expected_part in result, (
                    f"Expected '{expected_part}' in result for query '{input_query}', "
                    f"but got: {result}"
                )

    def test_japanese_keyword_ability_all_variations(self, query_builder):
        """Test all Japanese keyword ability variations.

        Tests implementation of Issue #2: キーワード能力による自然言語検索の精度向上
        Ensures all three variations (base, を持つ, 持ち) work correctly.
        """
        set_current_locale("ja")
        mapping = get_current_mapping()
        query_builder = QueryBuilder(mapping)

        # Test all three variations for a keyword
        keyword = "飛行"
        variations = [
            ("飛行", "keyword:flying"),
            ("飛行を持つ", "keyword:flying"),
            ("飛行持ち", "keyword:flying"),
        ]

        for variation, expected in variations:
            result = query_builder._convert_basic_terms(variation)
            assert expected in result, (
                f"Expected '{expected}' for variation '{variation}', but got: {result}"
            )
