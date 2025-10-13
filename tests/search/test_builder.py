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

    def test_japanese_ability_phrases_death_trigger(self, query_builder):
        """Test death trigger ability phrases - Issue #4.

        Tests implementation of Issue #4: 長文クエリ対応
        Tests death trigger phrases combined with colors and types.
        """
        set_current_locale("ja")
        mapping = get_current_mapping()
        query_builder = QueryBuilder(mapping)

        # Test death trigger phrases
        test_cases = [
            ("死亡時黒いクリーチャー", ['o:"when ~ dies"', "c:b", "t:creature"]),
            ("死亡したとき緑のクリーチャー", ['o:"when ~ dies"', "c:g", "t:creature"]),
            ("墓地に置かれたとき赤いクリーチャー", ['o:"when ~ dies"', "c:r", "t:creature"]),
        ]

        for input_query, expected_parts in test_cases:
            result = query_builder.build_query(input_query)
            for expected_part in expected_parts:
                assert expected_part in result, (
                    f"Expected '{expected_part}' in result for query '{input_query}', "
                    f"but got: {result}"
                )

    def test_japanese_ability_phrases_etb(self, query_builder):
        """Test ETB ability phrases - Issue #4.

        Tests implementation of Issue #4: 長文クエリ対応
        Tests ETB (enters the battlefield) phrases.
        """
        set_current_locale("ja")
        mapping = get_current_mapping()
        query_builder = QueryBuilder(mapping)

        # Test ETB phrases
        test_cases = [
            ("戦場に出たとき白いクリーチャー", ['o:"enters the battlefield"', "c:w", "t:creature"]),
            ("戦場を離れたとき青いクリーチャー", ['o:"leaves the battlefield"', "c:u", "t:creature"]),
        ]

        for input_query, expected_parts in test_cases:
            result = query_builder.build_query(input_query)
            for expected_part in expected_parts:
                assert expected_part in result, (
                    f"Expected '{expected_part}' in result for query '{input_query}', "
                    f"but got: {result}"
                )

    def test_japanese_ability_phrases_control(self, query_builder):
        """Test control-related ability phrases - Issue #4.

        Tests implementation of Issue #4: 長文クエリ対応
        Tests control-related phrases.
        """
        set_current_locale("ja")
        mapping = get_current_mapping()
        query_builder = QueryBuilder(mapping)

        # Test control phrases
        test_cases = [
            ("あなたがコントロールする緑のクリーチャー", ['o:"you control"', "c:g", "t:creature"]),
            ("対戦相手がコントロールする黒いクリーチャー", ['o:"opponent controls"', "c:b", "t:creature"]),
        ]

        for input_query, expected_parts in test_cases:
            result = query_builder.build_query(input_query)
            for expected_part in expected_parts:
                assert expected_part in result, (
                    f"Expected '{expected_part}' in result for query '{input_query}', "
                    f"but got: {result}"
                )

    def test_japanese_ability_phrases_effects(self, query_builder):
        """Test common effect ability phrases - Issue #4.

        Tests implementation of Issue #4: 長文クエリ対応
        Tests common effect phrases like draw, destroy, exile.
        """
        set_current_locale("ja")
        mapping = get_current_mapping()
        query_builder = QueryBuilder(mapping)

        # Test effect phrases
        test_cases = [
            ("カードを引く青いクリーチャー", ['o:"draw"', "c:u", "t:creature"]),
            ("カードを1枚引く青いインスタント", ['o:"draw a card"', "c:u", "t:instant"]),
            ("破壊黒いインスタント", ['o:"destroy"', "c:b", "t:instant"]),
            ("追放白いソーサリー", ['o:"exile"', "c:w", "t:sorcery"]),
        ]

        for input_query, expected_parts in test_cases:
            result = query_builder.build_query(input_query)
            for expected_part in expected_parts:
                assert expected_part in result, (
                    f"Expected '{expected_part}' in result for query '{input_query}', "
                    f"but got: {result}"
                )

    def test_japanese_ability_phrases_targeting(self, query_builder):
        """Test targeting ability phrases - Issue #4.

        Tests implementation of Issue #4: 長文クエリ対応
        Tests targeting phrases.
        """
        set_current_locale("ja")
        mapping = get_current_mapping()
        query_builder = QueryBuilder(mapping)

        # Test targeting phrases
        test_cases = [
            ("クリーチャーを対象とする赤いインスタント", ['o:"target creature"', "c:r", "t:instant"]),
            ("プレイヤーを対象とする赤いソーサリー", ['o:"target player"', "c:r", "t:sorcery"]),
        ]

        for input_query, expected_parts in test_cases:
            result = query_builder.build_query(input_query)
            for expected_part in expected_parts:
                assert expected_part in result, (
                    f"Expected '{expected_part}' in result for query '{input_query}', "
                    f"but got: {result}"
                )

    def test_japanese_complex_ability_query(self, query_builder):
        """Test complex queries with ability phrases - Issue #4.

        Tests implementation of Issue #4: 長文クエリ対応
        Phase 1: Individual ability phrases are supported.
        """
        set_current_locale("ja")
        mapping = get_current_mapping()
        query_builder = QueryBuilder(mapping)

        # Phase 1: Individual phrases work
        query = "死亡時黒いクリーチャー"
        result = query_builder.build_query(query)
        assert 'o:"when ~ dies"' in result
        assert "c:b" in result
        assert "t:creature" in result

    def test_japanese_ability_phrases_with_keywords(self, query_builder):
        """Test ability phrases combined with keyword abilities - Issue #4.

        Tests implementation of Issue #4: 長文クエリ対応
        Tests combining ability phrases with keyword abilities from Issue #2.
        """
        set_current_locale("ja")
        mapping = get_current_mapping()
        query_builder = QueryBuilder(mapping)

        # Combine ability phrase with keyword ability
        query = "飛行を持つあなたがコントロールするクリーチャー"
        result = query_builder.build_query(query)

        # Should contain both keyword and ability phrase
        assert "keyword:flying" in result
        assert 'o:"you control"' in result
        assert "t:creature" in result

    def test_japanese_phase2_death_trigger_with_effect(self, query_builder):
        """Test Phase 2: death trigger with effect - Issue #4 Phase 2."""
        set_current_locale("ja")
        mapping = get_current_mapping()
        query_builder = QueryBuilder(mapping)
        
        # "死亡時にカードを1枚引く黒いクリーチャー"
        query = "死亡時にカードを1枚引く黒いクリーチャー"
        result = query_builder.build_query(query)
        
        # Should contain death trigger
        assert 'o:"when ~ dies"' in result
        # Should contain draw effect
        assert ('o:"draw a card"' in result or 'o:"draw"' in result)
        # Should contain color and type
        assert "c:b" in result
        assert "t:creature" in result

    def test_japanese_phase2_etb_with_effect(self, query_builder):
        """Test Phase 2: ETB trigger with effect - Issue #4 Phase 2."""
        set_current_locale("ja")
        mapping = get_current_mapping()
        query_builder = QueryBuilder(mapping)
        
        # "戦場に出たときにトークンを生成する白いクリーチャー"
        query = "戦場に出たときにトークンを生成する白いクリーチャー"
        result = query_builder.build_query(query)
        
        # Should contain ETB trigger
        assert 'o:"enters the battlefield"' in result
        # Should contain create effect
        assert 'o:"create"' in result
        # Should contain color and type
        assert "c:w" in result
        assert "t:creature" in result

    def test_japanese_phase2_attack_trigger_with_effect(self, query_builder):
        """Test Phase 2: attack trigger with effect - Issue #4 Phase 2."""
        set_current_locale("ja")
        mapping = get_current_mapping()
        query_builder = QueryBuilder(mapping)
        
        # "攻撃したときにダメージを与える赤いクリーチャー"
        query = "攻撃したときにダメージを与える赤いクリーチャー"
        result = query_builder.build_query(query)
        
        # Should contain attack trigger
        assert 'o:"whenever ~ attacks"' in result
        # Should contain damage effect
        assert 'o:"deals damage"' in result
        # Should contain color and type
        assert "c:r" in result
        assert "t:creature" in result

    def test_japanese_phase2_complex_multi_ability(self, query_builder):
        """Test Phase 2: complex query with multiple abilities."""
        set_current_locale("ja")
        mapping = get_current_mapping()
        query_builder = QueryBuilder(mapping)
        
        # "死亡時にカードを引く飛行を持つ青いクリーチャー"
        query = "死亡時にカードを引く飛行を持つ青いクリーチャー"
        result = query_builder.build_query(query)
        
        # Should contain death trigger
        assert 'o:"when ~ dies"' in result
        # Should contain draw effect
        assert 'o:"draw"' in result
        # Should contain flying keyword
        assert "keyword:flying" in result
        # Should contain color and type
        assert "c:u" in result
        assert "t:creature" in result

    def test_japanese_phase2_control_with_effect(self, query_builder):
        """Test Phase 2: control phrase combined with other search terms.

        Note: Complex patterns like "あなたがコントロールする〜を〜する" are Phase 3 material.
        Phase 2 focuses on trigger patterns like "死亡時に〜する".
        """
        set_current_locale("ja")
        mapping = get_current_mapping()
        query_builder = QueryBuilder(mapping)

        # Simple control phrase (Phase 1 behavior preserved)
        query = "あなたがコントロールする緑のクリーチャー"
        result = query_builder.build_query(query)

        # Should contain control phrase
        assert 'o:"you control"' in result
        # Should contain color and type
        assert "c:g" in result
        assert "t:creature" in result

    def test_japanese_phase2_preserves_phase1_behavior(self, query_builder):
        """Test that Phase 2 preserves Phase 1 exact phrase matches."""
        set_current_locale("ja")
        mapping = get_current_mapping()
        query_builder = QueryBuilder(mapping)
        
        # Phase 1 exact match should still work
        query = "死亡時黒いクリーチャー"
        result = query_builder.build_query(query)
        
        # Should use Phase 1 dictionary lookup
        assert 'o:"when ~ dies"' in result
        assert "c:b" in result
        assert "t:creature" in result

    def test_english_queries_unaffected_by_phase2(self, query_builder):
        """Test that English queries are not affected by Phase 2 patterns."""
        set_current_locale("en")
        mapping = get_current_mapping()
        query_builder = QueryBuilder(mapping)

        # English queries use Scryfall syntax directly
        query = "c:r t:creature keyword:flying"
        result = query_builder.build_query(query)

        # Should remain unchanged
        assert "c:r" in result
        assert "t:creature" in result
        assert "keyword:flying" in result

    def test_build_with_parsed_query(self, query_builder):
        """Test build() method with ParsedQuery object."""
        from scryfall_mcp.models import ParsedQuery

        set_current_locale("ja")
        mapping = get_current_mapping()
        query_builder = QueryBuilder(mapping)

        # Create a ParsedQuery object
        parsed = ParsedQuery(
            original_text="飛行を持つ赤いクリーチャー",
            normalized_text="飛行を持つ赤いクリーチャー",
            intent="search_cards",
            language="ja",
            entities={
                "colors": ["red"],
                "types": ["creature"],
                "keywords": ["flying"],
            }
        )

        # Build query from parsed object
        result = query_builder.build(parsed)

        # Check result structure
        assert hasattr(result, "scryfall_query")
        assert hasattr(result, "original_query")
        assert hasattr(result, "suggestions")
        assert hasattr(result, "query_metadata")

        # Check query content
        assert "keyword:flying" in result.scryfall_query
        assert "c:r" in result.scryfall_query
        assert "t:creature" in result.scryfall_query

        # Check metadata
        assert result.query_metadata["language"] == "ja"
        assert result.query_metadata["intent"] == "search_cards"

    def test_generate_suggestions_no_specifics(self, query_builder):
        """Test suggestion generation for queries without colors or types."""
        from scryfall_mcp.models import ParsedQuery

        # English query without colors/types
        parsed = ParsedQuery(
            original_text="Lightning Bolt",
            normalized_text="Lightning Bolt",
            intent="search_cards",
            language="en",
            entities={"colors": [], "types": []}
        )

        result = query_builder.build(parsed)
        assert len(result.suggestions) > 0
        assert any("colors or card types" in s for s in result.suggestions)

    def test_generate_suggestions_competitive_query(self, query_builder):
        """Test suggestion generation for competitive queries."""
        from scryfall_mcp.models import ParsedQuery

        # Query with competitive keywords
        parsed = ParsedQuery(
            original_text="tournament viable creatures",
            normalized_text="tournament viable creatures",
            intent="search_cards",
            language="en",
            entities={"colors": [], "types": ["creature"]}
        )

        result = query_builder.build(parsed)
        assert any("format" in s.lower() for s in result.suggestions)

    def test_generate_suggestions_japanese_misspelling(self, query_builder):
        """Test suggestion generation for Japanese misspellings."""
        from scryfall_mcp.models import ParsedQuery

        set_current_locale("ja")
        mapping = get_current_mapping()
        query_builder = QueryBuilder(mapping)

        # Query with common misspelling
        parsed = ParsedQuery(
            original_text="くりーちゃー",
            normalized_text="くりーちゃー",
            intent="search_cards",
            language="ja",
            entities={"colors": [], "types": []}
        )

        result = query_builder.build(parsed)
        assert any("クリーチャー" in s for s in result.suggestions)

    def test_assess_complexity_simple(self, query_builder):
        """Test complexity assessment for simple queries."""
        simple_query = "c:w t:creature"
        complexity = query_builder._assess_complexity(simple_query)
        assert complexity == "simple"

    def test_assess_complexity_moderate(self, query_builder):
        """Test complexity assessment for moderate queries."""
        moderate_query = "c:w t:creature p>=3 mv<=4"
        complexity = query_builder._assess_complexity(moderate_query)
        assert complexity == "moderate"

    def test_assess_complexity_complex(self, query_builder):
        """Test complexity assessment for complex queries."""
        # Need >3 operators OR >5 fields to be "complex"
        # This has 4 operators (>=, <=, <=, !=) - regex matches [<>=!]+
        complex_query = "c:w t:creature p>=3 tou<=5 mv<=4 is!=funny"
        complexity = query_builder._assess_complexity(complex_query)
        assert complexity == "complex"

    def test_estimate_results_few(self, query_builder):
        """Test result estimation for specific queries."""
        specific_query = 'c:w t:creature p>=5 tou<=2 mv=4 name:"Angel"'
        estimate = query_builder._estimate_results(specific_query)
        assert estimate == "few"

    def test_estimate_results_moderate(self, query_builder):
        """Test result estimation for moderately specific queries."""
        moderate_query = "c:w t:creature p>=3"
        estimate = query_builder._estimate_results(moderate_query)
        assert estimate == "moderate"

    def test_estimate_results_many(self, query_builder):
        """Test result estimation for broad queries."""
        broad_query = "creature"
        estimate = query_builder._estimate_results(broad_query)
        assert estimate == "many"

    def test_get_search_help_english_detailed(self, query_builder):
        """Test English search help returns all categories."""
        help_info = query_builder.get_search_help()

        # Check all categories exist
        assert "Colors" in help_info
        assert "Power/Toughness" in help_info
        assert "Mana Cost" in help_info
        assert "Card Types" in help_info

        # Check each category has examples
        assert len(help_info["Colors"]) > 0
        assert len(help_info["Power/Toughness"]) > 0
        assert len(help_info["Mana Cost"]) > 0
        assert len(help_info["Card Types"]) > 0

        # Verify specific examples
        assert any("white creatures" in ex for ex in help_info["Colors"])
        assert any("power" in ex.lower() for ex in help_info["Power/Toughness"])

    def test_convert_basic_terms_english(self, query_builder):
        """Test basic term conversion for English."""
        # English should use word boundaries
        test_cases = [
            ("color", "c"),
            ("type", "t"),
            ("power", "p"),
        ]

        for english_term, expected in test_cases:
            result = query_builder._convert_basic_terms(english_term)
            assert expected in result

    def test_normalize_text_japanese_fullwidth_operators(self, query_builder):
        """Test Japanese full-width operator normalization."""
        set_current_locale("ja")
        mapping = get_current_mapping()
        query_builder = QueryBuilder(mapping)

        # Test full-width operators
        test_cases = [
            ("パワー＝３", "パワー=3"),
            ("タフネス！＝５", "タフネス!=5"),
            ("（パワー）", "(パワー)"),
            ("［タフネス］", "[タフネス]"),
        ]

        for input_text, expected in test_cases:
            result = query_builder._normalize_text(input_text)
            assert result == expected

    def test_convert_operators_mana_cost_m_field(self, query_builder):
        """Test operator conversion for マナコスト to use 'm' field."""
        # This covers line 328: field = "m"
        query = "マナコスト3以上"
        result = query_builder.build_query(query, locale="ja")
        assert "m>=3" in result

    def test_generate_suggestions_competitive_japanese(self, query_builder):
        """Test competitive query suggestions in Japanese mode."""
        from scryfall_mcp.models import ParsedQuery

        # This covers line 436: Japanese competitive suggestion
        set_current_locale("ja")
        mapping = get_current_mapping()
        query_builder = QueryBuilder(mapping)

        parsed = ParsedQuery(
            original_text="tournament クリーチャー",
            normalized_text="tournament クリーチャー",
            intent="search_cards",
            language="ja",
            entities={"colors": [], "types": ["creature"], "keywords": []}
        )
        result = query_builder.build(parsed)
        assert any("f:standard" in s or "f:modern" in s for s in result.suggestions)
