"""Tests for query builder module.

All end-to-end style tests go through the real production pipeline
(SearchParser.parse -> QueryBuilder.build). The legacy sync entry point
(build_query) was removed; QueryBuilder.build is a pure, synchronous
transformation and leaves the __LATEST_SET__ placeholder untouched
(resolved in the I/O layer by api.sets.resolve_latest_set_placeholder).
"""

from __future__ import annotations

import pytest

from scryfall_mcp.i18n import get_current_mapping, set_current_locale
from scryfall_mcp.search.builder import QueryBuilder
from scryfall_mcp.search.parser import SearchParser


def build_text(builder: QueryBuilder, text: str) -> str:
    """Run text through the real Parser -> QueryBuilder pipeline."""
    parser = SearchParser(builder._mapping)
    return builder.build(parser.parse(text)).scryfall_query


class TestQueryBuilder:
    """Test QueryBuilder class."""

    @pytest.fixture
    def query_builder(self):
        """Create a query builder for testing."""
        mapping = get_current_mapping()
        return QueryBuilder(mapping)

    @pytest.fixture
    def ja_builder(self):
        """Create a Japanese-locale query builder for testing."""
        set_current_locale("ja")
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

    def test_build_pipeline_english(self, query_builder):
        """Test query building in English via the real pipeline."""
        # Simple search
        result = build_text(query_builder, "Lightning Bolt")
        assert result == "Lightning Bolt"

        # Color search
        result = build_text(query_builder, "red creatures")
        assert "creature" in result.lower()

    def test_build_pipeline_japanese(self, ja_builder):
        """Test query building in Japanese via the real pipeline."""
        # Japanese color + type conversion
        result = build_text(ja_builder, "白いクリーチャー")
        assert "c:w" in result
        assert "t:creature" in result

        # Japanese card name pass-through (no conversion) - Scryfall handles
        # multilingual lookup natively
        result = build_text(ja_builder, "稲妻")
        assert "稲妻" in result

    def test_fullwidth_normalization_japanese(self, ja_builder):
        """Test that full-width digits/operators are normalized in the pipeline.

        Normalization lives in SearchParser._normalize_text; this covers the
        integration through build().
        """
        result = build_text(ja_builder, "パワー３以上タフネス５以下")
        assert "p>=3" in result
        assert "tou<=5" in result

    def test_convert_colors_japanese(self, ja_builder):
        """Test Japanese color conversion."""
        test_cases = [
            ("白いクリーチャー", "c:w t:creature"),
            ("青のアーティファクト", "c:u t:artifact"),
            ("赤いインスタント", "c:r t:instant"),
            ("緑のエンチャント", "c:g t:enchantment"),
            ("黒いソーサリー", "c:b t:sorcery"),
        ]

        for input_text, expected_part in test_cases:
            result = ja_builder._convert_colors(input_text)
            assert expected_part in result

    def test_convert_operators_japanese(self, ja_builder):
        """Test Japanese operator conversion."""
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
            result = ja_builder._convert_operators(input_text)
            assert expected in result

    def test_japanese_card_names_pass_through(self, ja_builder):
        """Test Japanese card names are passed through unchanged.

        Japanese card names are passed directly to Scryfall's API which
        natively supports multilingual card names via the printed_name field
        and lang: parameter.
        """
        test_cases = [
            "平地",
            "島",
            "稲妻",
            "エイトグ",
            "アトガトグ",
        ]

        for ja_name in test_cases:
            result = build_text(ja_builder, ja_name)
            assert ja_name in result

    def test_convert_phrases_japanese(self, ja_builder):
        """Test Japanese phrase conversion."""
        test_cases = [
            ("を持つクリーチャー", "t:creature"),
            ("白のカード", "c:w"),
            ("価格が", "usd<"),
        ]

        for phrase, expected_part in test_cases:
            # Create text that includes the phrase
            test_text = f"何か{phrase}何か"
            result = ja_builder._convert_phrases(test_text)
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

    def test_complex_japanese_query(self, ja_builder):
        """Test complex Japanese query building."""
        complex_query = "パワー3以上の赤いクリーチャーでマナ総量5以下"
        result = build_text(ja_builder, complex_query)

        # Should contain all converted parts
        assert "p>=3" in result
        assert "c:r" in result
        assert "t:creature" in result
        assert "mv<=5" in result

    def test_edge_cases(self, query_builder):
        """Test edge cases in query building."""
        # Empty query
        result = build_text(query_builder, "")
        assert result == ""

        # Query with only spaces
        result = build_text(query_builder, "   ")
        assert result == ""

        # Query with special characters
        result = build_text(query_builder, 'name:"Lightning Bolt"')
        assert result == 'name:"Lightning Bolt"'

    def test_mixed_language_query(self, ja_builder):
        """Test query with mixed languages."""
        mixed_query = "白い creature パワー3以上"
        result = build_text(ja_builder, mixed_query)

        # Should handle both languages
        assert "c:w" in result
        assert "p>=3" in result

    def test_operator_precedence(self, query_builder):
        """Test that operator conversion doesn't interfere with existing Scryfall syntax."""
        # Existing Scryfall syntax should be preserved or converted consistently
        scryfall_query = "c:w power>=3 cmc<=4"
        result = build_text(query_builder, scryfall_query)

        # Should be converted consistently
        assert "c:w" in result
        assert "p>=3" in result  # power gets converted to p
        assert "cmc<=4" in result

    def test_basic_term_conversion(self, ja_builder):
        """Test basic search term conversion."""
        test_cases = [
            ("色", "c"),
            ("タイプ", "t"),
            ("パワー", "p"),
            ("レアリティ", "r"),
        ]

        for ja_term, expected in test_cases:
            result = ja_builder._convert_basic_terms(ja_term)
            assert expected in result

    def test_japanese_keyword_ability_search_single(self, ja_builder):
        """Test Japanese keyword ability search - single keyword.

        Single keyword ability with creature type.
        """
        test_cases = [
            ("多相を持つクリーチャー", ["keyword:changeling", "t:creature"]),
            ("飛行を持つクリーチャー", ["keyword:flying", "t:creature"]),
            ("速攻持ちクリーチャー", ["keyword:haste", "t:creature"]),
            ("接死を持つクリーチャー", ["keyword:deathtouch", "t:creature"]),
            ("威迫を持つクリーチャー", ["keyword:menace", "t:creature"]),
        ]

        for input_query, expected_parts in test_cases:
            result = build_text(ja_builder, input_query)
            for expected_part in expected_parts:
                assert expected_part in result, (
                    f"Expected '{expected_part}' in result for query '{input_query}', "
                    f"but got: {result}"
                )

    def test_japanese_keyword_ability_search_multiple(self, ja_builder):
        """Test Japanese keyword ability search - multiple keywords."""
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
            result = build_text(ja_builder, input_query)
            for expected_part in expected_parts:
                assert expected_part in result, (
                    f"Expected '{expected_part}' in result for query '{input_query}', "
                    f"but got: {result}"
                )

    def test_japanese_keyword_ability_with_colors(self, ja_builder):
        """Test Japanese keyword ability search combined with colors."""
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
            result = build_text(ja_builder, input_query)
            for expected_part in expected_parts:
                assert expected_part in result, (
                    f"Expected '{expected_part}' in result for query '{input_query}', "
                    f"but got: {result}"
                )

    def test_japanese_keyword_ability_quoted_keywords(self, ja_builder):
        """Test Japanese keyword abilities that require quotes in Scryfall syntax.

        Multi-word keyword abilities like "first strike" and "double strike".
        """
        test_cases = [
            ("先制攻撃を持つクリーチャー", ['keyword:"first strike"', "t:creature"]),
            ("二段攻撃を持つクリーチャー", ['keyword:"double strike"', "t:creature"]),
            (
                "先制攻撃と飛行を持つクリーチャー",
                ['keyword:"first strike"', "keyword:flying", "t:creature"],
            ),
        ]

        for input_query, expected_parts in test_cases:
            result = build_text(ja_builder, input_query)
            for expected_part in expected_parts:
                assert expected_part in result, (
                    f"Expected '{expected_part}' in result for query '{input_query}', "
                    f"but got: {result}"
                )

    def test_japanese_keyword_ability_all_variations(self, ja_builder):
        """Test all Japanese keyword ability variations.

        Ensures all three variations (base, を持つ, 持ち) work correctly.
        """
        variations = [
            ("飛行", "keyword:flying"),
            ("飛行を持つ", "keyword:flying"),
            ("飛行持ち", "keyword:flying"),
        ]

        for variation, expected in variations:
            result = ja_builder._convert_basic_terms(variation)
            assert expected in result, (
                f"Expected '{expected}' for variation '{variation}', but got: {result}"
            )

    def test_japanese_ability_phrases_death_trigger(self, ja_builder):
        """Test death trigger ability phrases combined with colors and types."""
        test_cases = [
            ("死亡時黒いクリーチャー", ['o:"when ~ dies"', "c:b", "t:creature"]),
            ("死亡したとき緑のクリーチャー", ['o:"when ~ dies"', "c:g", "t:creature"]),
            (
                "墓地に置かれたとき赤いクリーチャー",
                ['o:"when ~ dies"', "c:r", "t:creature"],
            ),
        ]

        for input_query, expected_parts in test_cases:
            result = build_text(ja_builder, input_query)
            for expected_part in expected_parts:
                assert expected_part in result, (
                    f"Expected '{expected_part}' in result for query '{input_query}', "
                    f"but got: {result}"
                )

    def test_japanese_ability_phrases_etb(self, ja_builder):
        """Test ETB (enters the battlefield) ability phrases."""
        test_cases = [
            (
                "戦場に出たとき白いクリーチャー",
                ['o:"enters the battlefield"', "c:w", "t:creature"],
            ),
            (
                "戦場を離れたとき青いクリーチャー",
                ['o:"leaves the battlefield"', "c:u", "t:creature"],
            ),
        ]

        for input_query, expected_parts in test_cases:
            result = build_text(ja_builder, input_query)
            for expected_part in expected_parts:
                assert expected_part in result, (
                    f"Expected '{expected_part}' in result for query '{input_query}', "
                    f"but got: {result}"
                )

    def test_japanese_ability_phrases_control(self, ja_builder):
        """Test control-related ability phrases."""
        test_cases = [
            (
                "あなたがコントロールする緑のクリーチャー",
                ['o:"you control"', "c:g", "t:creature"],
            ),
            (
                "対戦相手がコントロールする黒いクリーチャー",
                ['o:"opponent controls"', "c:b", "t:creature"],
            ),
        ]

        for input_query, expected_parts in test_cases:
            result = build_text(ja_builder, input_query)
            for expected_part in expected_parts:
                assert expected_part in result, (
                    f"Expected '{expected_part}' in result for query '{input_query}', "
                    f"but got: {result}"
                )

    def test_japanese_ability_phrases_effects(self, ja_builder):
        """Test common effect ability phrases like draw, destroy, exile."""
        test_cases = [
            ("カードを引く青いクリーチャー", ['o:"draw"', "c:u", "t:creature"]),
            (
                "カードを1枚引く青いインスタント",
                ['o:"draw a card"', "c:u", "t:instant"],
            ),
            ("破壊黒いインスタント", ['o:"destroy"', "c:b", "t:instant"]),
            ("追放白いソーサリー", ['o:"exile"', "c:w", "t:sorcery"]),
        ]

        for input_query, expected_parts in test_cases:
            result = build_text(ja_builder, input_query)
            for expected_part in expected_parts:
                assert expected_part in result, (
                    f"Expected '{expected_part}' in result for query '{input_query}', "
                    f"but got: {result}"
                )

    def test_japanese_ability_phrases_targeting(self, ja_builder):
        """Test targeting ability phrases."""
        test_cases = [
            (
                "クリーチャーを対象とする赤いインスタント",
                ['o:"target creature"', "c:r", "t:instant"],
            ),
            (
                "プレイヤーを対象とする赤いソーサリー",
                ['o:"target player"', "c:r", "t:sorcery"],
            ),
        ]

        for input_query, expected_parts in test_cases:
            result = build_text(ja_builder, input_query)
            for expected_part in expected_parts:
                assert expected_part in result, (
                    f"Expected '{expected_part}' in result for query '{input_query}', "
                    f"but got: {result}"
                )

    def test_japanese_complex_ability_query(self, ja_builder):
        """Test complex queries with ability phrases."""
        query = "死亡時黒いクリーチャー"
        result = build_text(ja_builder, query)
        assert 'o:"when ~ dies"' in result
        assert "c:b" in result
        assert "t:creature" in result

    def test_japanese_ability_phrases_with_keywords(self, ja_builder):
        """Test ability phrases combined with keyword abilities."""
        query = "飛行を持つあなたがコントロールするクリーチャー"
        result = build_text(ja_builder, query)

        # Should contain both keyword and ability phrase
        assert "keyword:flying" in result
        assert 'o:"you control"' in result
        assert "t:creature" in result

    def test_japanese_phase2_death_trigger_with_effect(self, ja_builder):
        """Test death trigger with effect through the production path."""
        query = "死亡時にカードを1枚引く黒いクリーチャー"
        result = build_text(ja_builder, query)

        # Should contain death trigger
        assert 'o:"when ~ dies"' in result
        # Should contain draw effect
        assert 'o:"draw a card"' in result or 'o:"draw"' in result
        # Should contain color and type
        assert "c:b" in result
        assert "t:creature" in result
        # Should NOT contain Japanese particles
        assert "する" not in result

    def test_japanese_phase2_etb_with_effect(self, ja_builder):
        """Test ETB trigger with effect through the production path."""
        query = "戦場に出たときにトークンを生成する白いクリーチャー"
        result = build_text(ja_builder, query)

        # Should contain ETB trigger
        assert 'o:"enters the battlefield"' in result
        # Should contain create effect
        assert 'o:"create"' in result
        # Should contain color and type
        assert "c:w" in result
        assert "t:creature" in result
        # Should NOT contain Japanese particles
        assert "する" not in result

    def test_japanese_phase2_attack_trigger_with_effect(self, ja_builder):
        """Test attack trigger with effect through the production path."""
        query = "攻撃したときにダメージを与える赤いクリーチャー"
        result = build_text(ja_builder, query)

        # Should contain attack trigger
        assert 'o:"whenever ~ attacks"' in result
        # Should contain damage effect
        assert 'o:"deals damage"' in result
        # Should contain color and type
        assert "c:r" in result
        assert "t:creature" in result
        # Should NOT contain Japanese particles
        assert "する" not in result

    def test_japanese_phase2_complex_multi_ability(self, ja_builder):
        """Test complex query with multiple abilities."""
        query = "死亡時にカードを引く飛行を持つ青いクリーチャー"
        result = build_text(ja_builder, query)

        # Should contain death trigger
        assert 'o:"when ~ dies"' in result
        # Should contain draw effect
        assert 'o:"draw"' in result
        # Should contain flying keyword
        assert "keyword:flying" in result
        # Should contain color and type
        assert "c:u" in result
        assert "t:creature" in result
        # Should NOT contain Japanese particles
        assert "する" not in result

    def test_japanese_phase2_control_with_effect(self, ja_builder):
        """Test control phrase combined with other search terms."""
        query = "あなたがコントロールする緑のクリーチャー"
        result = build_text(ja_builder, query)

        # Should contain control phrase
        assert 'o:"you control"' in result
        # Should contain color and type
        assert "c:g" in result
        assert "t:creature" in result

    def test_japanese_phase2_preserves_phase1_behavior(self, ja_builder):
        """Test that pattern matching preserves exact phrase matches."""
        query = "死亡時黒いクリーチャー"
        result = build_text(ja_builder, query)

        assert 'o:"when ~ dies"' in result
        assert "c:b" in result
        assert "t:creature" in result

    def test_english_queries_unaffected_by_patterns(self, query_builder):
        """Test that English queries are not affected by Japanese patterns."""
        query = "c:r t:creature keyword:flying"
        result = build_text(query_builder, query)

        # Should remain unchanged
        assert "c:r" in result
        assert "t:creature" in result
        assert "keyword:flying" in result

    def test_build_with_parsed_query(self, ja_builder):
        """Test build() method with ParsedQuery object."""
        from scryfall_mcp.models import ParsedQuery

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
            },
        )

        # Build query from parsed object
        result = ja_builder.build(parsed)

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

    def test_build_leaves_latest_set_placeholder(self, query_builder):
        """Test that build() leaves __LATEST_SET__ untouched (pure core).

        Placeholder resolution requires API access and is performed in the
        I/O layer by api.sets.resolve_latest_set_placeholder.
        """
        from scryfall_mcp.models import ParsedQuery

        parsed = ParsedQuery(
            original_text="e:__LATEST_SET__",
            normalized_text="e:__LATEST_SET__",
            intent="search_cards",
            language="en",
            entities={"colors": [], "types": []},
        )

        result = query_builder.build(parsed)
        assert "__LATEST_SET__" in result.scryfall_query

    def test_generate_suggestions_no_specifics(self, query_builder):
        """Test suggestion generation for queries without colors or types."""
        from scryfall_mcp.models import ParsedQuery

        # English query without colors/types
        parsed = ParsedQuery(
            original_text="Lightning Bolt",
            normalized_text="Lightning Bolt",
            intent="search_cards",
            language="en",
            entities={"colors": [], "types": []},
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
            entities={"colors": [], "types": ["creature"]},
        )

        result = query_builder.build(parsed)
        assert any("format" in s.lower() for s in result.suggestions)

    def test_generate_suggestions_japanese_misspelling(self, ja_builder):
        """Test suggestion generation for Japanese misspellings."""
        from scryfall_mcp.models import ParsedQuery

        # Query with common misspelling
        parsed = ParsedQuery(
            original_text="くりーちゃー",
            normalized_text="くりーちゃー",
            intent="search_cards",
            language="ja",
            entities={"colors": [], "types": []},
        )

        result = ja_builder.build(parsed)
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

    def test_fullwidth_operators_japanese_pipeline(self, ja_builder):
        """Test Japanese full-width operator normalization through the pipeline."""
        result = build_text(ja_builder, "パワー＝３")
        assert "p=3" in result

    def test_convert_operators_mana_cost_m_field(self, ja_builder):
        """Test operator conversion for マナコスト to use 'm' field."""
        result = build_text(ja_builder, "マナコスト3以上")
        assert "m>=3" in result

    def test_generate_suggestions_competitive_japanese(self, ja_builder):
        """Test competitive query suggestions in Japanese mode."""
        from scryfall_mcp.models import ParsedQuery

        parsed = ParsedQuery(
            original_text="tournament クリーチャー",
            normalized_text="tournament クリーチャー",
            intent="search_cards",
            language="ja",
            entities={"colors": [], "types": ["creature"], "keywords": []},
        )
        result = ja_builder.build(parsed)
        assert any("f:standard" in s or "f:modern" in s for s in result.suggestions)

    def test_ultra_complex_query_multiple_abilities(self, ja_builder):
        """Test ultra-complex query with 3+ abilities combined."""
        query = "飛行と速攻と死亡時にカードを引く赤いクリーチャーでパワー3以上"
        result = build_text(ja_builder, query)

        # Should contain all components
        assert "keyword:flying" in result
        assert "keyword:haste" in result
        assert 'o:"when ~ dies"' in result
        assert 'o:"draw"' in result
        assert "c:r" in result
        assert "t:creature" in result
        assert "p>=3" in result

    def test_very_long_natural_language_query(self, ja_builder):
        """Test very long natural language query (100+ characters)."""
        query = (
            "モダンフォーマットで使える飛行と先制攻撃を持つ"
            "戦場に出たときにトークンを生成する"
            "白いクリーチャーでパワー2以上タフネス3以下でマナ総量4以下"
        )
        result = build_text(ja_builder, query)

        # Should handle all components without crashing
        assert "keyword:flying" in result
        assert 'keyword:"first strike"' in result
        assert 'o:"enters the battlefield"' in result
        assert 'o:"create"' in result
        assert "c:w" in result
        assert "t:creature" in result
        assert "p>=2" in result
        assert "tou<=3" in result
        assert "mv<=4" in result

    def test_ambiguous_natural_language_query(self, ja_builder):
        """Test ambiguous natural language query with vague terms."""
        query = "強力な赤いクリーチャー"
        result = build_text(ja_builder, query)

        # Should at least extract color and type
        assert "c:r" in result
        assert "t:creature" in result

    def test_mixed_features_complex_query(self, ja_builder):
        """Test complex query mixing format filters with ability phrases."""
        query = "モダンで使える飛行を持つ死亡時にカードを引く青黒のクリーチャー"
        result = build_text(ja_builder, query)

        # Should contain keyword ability
        assert "keyword:flying" in result
        # Should contain death trigger phrase
        assert 'o:"when ~ dies"' in result
        # Should contain draw effect
        assert 'o:"draw"' in result
        # Should contain both colors (blue and black)
        assert "c:u" in result or "c:b" in result or "c:ub" in result
        assert "t:creature" in result

    def test_deeply_nested_trigger_effect_chain(self, ja_builder):
        """Test deeply nested trigger-effect chain query does not crash."""
        query = "死亡時に戦場に出て攻撃したときダメージを与えるトークンを生成する黒いクリーチャー"
        result = build_text(ja_builder, query)

        # Should at least extract death trigger and color/type
        assert 'o:"when ~ dies"' in result
        assert "c:b" in result
        assert "t:creature" in result

    def test_multiple_color_identities_complex(self, ja_builder):
        """Test complex query with multiple color identities."""
        query = "青白の飛行と絆魂を持つクリーチャーでマナ総量3以下"
        result = build_text(ja_builder, query)

        # Should contain both colors
        # Note: Parser may handle this as two separate color terms or as identity
        assert (
            "c:w" in result or "c:u" in result or "c:wu" in result or "id:wu" in result
        )
        # Should contain keywords
        assert "keyword:flying" in result
        assert "keyword:lifelink" in result
        assert "t:creature" in result
        assert "mv<=3" in result

    def test_empty_and_whitespace_edge_cases(self, ja_builder):
        """Test empty and whitespace-only queries."""
        result = build_text(ja_builder, "")
        assert result == "" or result is None

        result = build_text(ja_builder, "   \t\n   ")
        assert result.strip() == "" or result is None

    def test_special_characters_in_query(self, ja_builder):
        """Test queries with special characters."""
        query = '飛行を持つ"天使"というクリーチャー'
        result = build_text(ja_builder, query)

        # Should at least extract keyword and type
        assert "keyword:flying" in result
        assert "t:creature" in result

    def test_numeric_edge_cases(self, ja_builder):
        """Test queries with extreme numeric values."""
        # Test with very large power
        result = build_text(ja_builder, "パワー100以上の赤いクリーチャー")
        assert "p>=100" in result
        assert "c:r" in result

        # Test with zero
        result = build_text(ja_builder, "パワー0のクリーチャー")
        assert "p=0" in result or "p:0" in result
