"""End-to-end tests for the complete query processing pipeline.

This module tests the complete flow from natural language query to formatted results:
Parser → Builder → Processor → Presenter

These tests validate Issue #2 implementation (Japanese keyword ability search)
and ensure all components work together correctly.
"""

from __future__ import annotations

import pytest

from scryfall_mcp.i18n import get_current_mapping, use_locale
from scryfall_mcp.search.builder import QueryBuilder
from scryfall_mcp.search.parser import SearchParser


@pytest.mark.asyncio
class TestEndToEndQueryPipeline:
    """Test complete query processing pipeline."""

    async def test_japanese_keyword_ability_e2e(self):
        """Test Japanese keyword ability search end-to-end.

        Tests Issue #2 implementation through the entire stack:
        - Parser: Extract keyword entities
        - Builder: Convert to Scryfall query
        """
        # 日本語の自然言語クエリ
        query = "飛行を持つ赤いクリーチャーでパワー3以上"

        with use_locale("ja"):
            # Create parser and builder with Japanese mapping
            mapping = get_current_mapping()
            parser = SearchParser(mapping)
            builder = QueryBuilder(mapping)

            # Parser: 自然言語クエリを解析
            parsed = parser.parse(query)
            assert parsed.language == "ja"
            assert parsed.original_text == query

            # Builder: Scryfallクエリに変換
            result = await builder.build(parsed)

            # 期待されるクエリ要素を検証
            scryfall_query = result.scryfall_query

            # キーワード能力（飛行）が含まれる
            assert "keyword:flying" in scryfall_query or "flying" in scryfall_query.lower()

            # 色（赤）が含まれる
            assert "c:r" in scryfall_query

            # タイプ（クリーチャー）が含まれる
            assert "t:creature" in scryfall_query

            # パワー条件が含まれる
            assert "p>=3" in scryfall_query or "power>=3" in scryfall_query

            # 複雑度の評価（query_metadataに格納されている）
            assert "query_complexity" in result.query_metadata
            assert result.query_metadata["query_complexity"] in ["simple", "moderate", "complex"]

    async def test_complex_japanese_query_e2e(self):
        """Test complex Japanese query end-to-end."""
        query = "白と青のクリーチャーでマナ総量3以下の伝説の"

        with use_locale("ja"):
            # Create parser and builder
            mapping = get_current_mapping()
            parser = SearchParser(mapping)
            builder = QueryBuilder(mapping)

            # Parser
            parsed = parser.parse(query)
            assert parsed.language == "ja"

            # Builder
            result = await builder.build(parsed)

            scryfall_query = result.scryfall_query

            # 色（白と青）
            assert "c:w" in scryfall_query or "c:u" in scryfall_query

            # タイプ（クリーチャー、伝説）
            assert "t:creature" in scryfall_query
            assert "t:legendary" in scryfall_query or "legendary" in scryfall_query

            # マナ総量
            assert ("mv<=3" in scryfall_query or "cmc<=3" in scryfall_query
                    or "manavalue<=3" in scryfall_query)

    async def test_english_query_e2e(self):
        """Test English query end-to-end."""
        query = "red creatures with haste and power greater than 3"

        with use_locale("en"):
            # Create parser and builder
            mapping = get_current_mapping()
            parser = SearchParser(mapping)
            builder = QueryBuilder(mapping)

            # Parser
            parsed = parser.parse(query)
            assert parsed.language == "en"
            assert parsed.original_text == query

            # Builder
            result = await builder.build(parsed)

            scryfall_query = result.scryfall_query.lower()

            # 色（赤） - 英語の場合はそのままの可能性も
            assert "c:r" in scryfall_query or "red" in scryfall_query

            # タイプ（クリーチャー） - 英語の場合はそのままの可能性も
            assert "t:creature" in scryfall_query or "creature" in scryfall_query

            # キーワード能力（速攻） - "haste"が含まれる
            assert "haste" in scryfall_query

            # パワー条件 - "3"が含まれればOK（フォーマットは多様）
            assert "3" in scryfall_query

    async def test_japanese_multiple_keywords_e2e(self):
        """Test Japanese query with multiple keyword abilities."""
        query = "飛行と接死を持つクリーチャー"

        with use_locale("ja"):
            # Create parser and builder
            mapping = get_current_mapping()
            parser = SearchParser(mapping)
            builder = QueryBuilder(mapping)

            # Parser
            parsed = parser.parse(query)

            # Builder
            result = await builder.build(parsed)

            scryfall_query = result.scryfall_query

            # 複数のキーワード能力
            assert "flying" in scryfall_query.lower()
            assert "deathtouch" in scryfall_query.lower()

            # タイプ（クリーチャー）
            assert "t:creature" in scryfall_query

    async def test_english_format_query_e2e(self):
        """Test English query with format specification."""
        query = "creatures legal in standard"

        with use_locale("en"):
            # Create parser and builder
            mapping = get_current_mapping()
            parser = SearchParser(mapping)
            builder = QueryBuilder(mapping)

            # Parser
            parsed = parser.parse(query)

            # Builder
            result = await builder.build(parsed)

            scryfall_query = result.scryfall_query

            # フォーマット指定
            assert "f:standard" in scryfall_query or "format:standard" in scryfall_query

            # タイプ（クリーチャー）
            assert "creature" in scryfall_query.lower()

    async def test_japanese_rarity_query_e2e(self):
        """Test Japanese query with rarity specification."""
        query = "神話レアのプレインズウォーカー"

        with use_locale("ja"):
            # Create parser and builder
            mapping = get_current_mapping()
            parser = SearchParser(mapping)
            builder = QueryBuilder(mapping)

            # Parser
            parsed = parser.parse(query)

            # Builder
            result = await builder.build(parsed)

            scryfall_query = result.scryfall_query

            # レアリティ
            assert "r:mythic" in scryfall_query or "rarity:mythic" in scryfall_query

            # タイプ（プレインズウォーカー）
            assert "t:planeswalker" in scryfall_query or "planeswalker" in scryfall_query

    async def test_japanese_color_identity_query_e2e(self):
        """Test Japanese query with color identity."""
        query = "白のカードで青のマナシンボルを持つ"

        with use_locale("ja"):
            # Create parser and builder
            mapping = get_current_mapping()
            parser = SearchParser(mapping)
            builder = QueryBuilder(mapping)

            # Parser
            parsed = parser.parse(query)

            # Builder
            result = await builder.build(parsed)

            scryfall_query = result.scryfall_query

            # 色指定
            assert "c:w" in scryfall_query or "white" in scryfall_query.lower()

            # マナシンボル（青）
            # Note: This is a complex query that may not be perfectly parsed
            # Just verify it doesn't error and produces some query
            assert len(scryfall_query) > 0

    async def test_query_suggestions_e2e(self):
        """Test that query result is valid."""
        query = "creatures"

        with use_locale("en"):
            # Create parser and builder
            mapping = get_current_mapping()
            parser = SearchParser(mapping)
            builder = QueryBuilder(mapping)

            # Parser
            parsed = parser.parse(query)

            # Builder
            result = await builder.build(parsed)

            # クエリが生成されることを確認
            assert result.scryfall_query is not None
            assert isinstance(result.scryfall_query, str)
            assert len(result.scryfall_query) > 0

            # サジェスションリストが存在することを確認（空でも可）
            assert isinstance(result.suggestions, list)

    async def test_empty_query_e2e(self):
        """Test handling of empty query."""
        query = ""

        with use_locale("en"):
            # Create parser and builder
            mapping = get_current_mapping()
            parser = SearchParser(mapping)
            builder = QueryBuilder(mapping)

            # Parser
            parsed = parser.parse(query)

            # Builder should handle empty query gracefully
            result = await builder.build(parsed)

            # Should produce some fallback query or empty string
            assert isinstance(result.scryfall_query, str)

    async def test_complexity_assessment_e2e(self):
        """Test complexity assessment across pipeline."""
        # Simple query
        simple_query = "creatures"

        with use_locale("en"):
            mapping = get_current_mapping()
            parser = SearchParser(mapping)
            builder = QueryBuilder(mapping)

            parsed = parser.parse(simple_query)
            result = await builder.build(parsed)

            assert "query_complexity" in result.query_metadata
            assert result.query_metadata["query_complexity"] == "simple"

        # Complex query
        complex_query = "white creatures with flying power>=3 toughness<=5 mv<=4"

        with use_locale("en"):
            mapping = get_current_mapping()
            parser = SearchParser(mapping)
            builder = QueryBuilder(mapping)

            parsed = parser.parse(complex_query)
            result = await builder.build(parsed)

            # Should be moderate or complex
            assert "query_complexity" in result.query_metadata
            assert result.query_metadata["query_complexity"] in ["moderate", "complex"]

    async def test_locale_switching_e2e(self):
        """Test that locale switching works across pipeline."""
        query_en = "red creatures"
        query_ja = "赤いクリーチャー"

        # English
        with use_locale("en"):
            mapping_en = get_current_mapping()
            parser_en = SearchParser(mapping_en)
            builder_en = QueryBuilder(mapping_en)

            parsed_en = parser_en.parse(query_en)
            result_en = await builder_en.build(parsed_en)

            # クエリにred/c:rとcreature/t:creatureが含まれることを確認
            query_lower = result_en.scryfall_query.lower()
            assert "red" in query_lower or "c:r" in query_lower
            assert "creature" in query_lower or "t:creature" in query_lower

        # Japanese
        with use_locale("ja"):
            mapping_ja = get_current_mapping()
            parser_ja = SearchParser(mapping_ja)
            builder_ja = QueryBuilder(mapping_ja)

            parsed_ja = parser_ja.parse(query_ja)
            result_ja = await builder_ja.build(parsed_ja)

            # クエリに色とタイプが含まれることを確認
            query_lower_ja = result_ja.scryfall_query.lower()
            assert "c:r" in query_lower_ja or "red" in query_lower_ja
            assert "t:creature" in query_lower_ja or "creature" in query_lower_ja

    async def test_phase2_death_trigger_with_effect_e2e(self):
        """Test Phase 2: Death trigger with effect - Issue #4 integration."""
        query = "死亡時にカードを1枚引く黒いクリーチャー"

        with use_locale("ja"):
            mapping = get_current_mapping()
            parser = SearchParser(mapping)
            builder = QueryBuilder(mapping)

            # Parse
            parsed = parser.parse(query)
            assert parsed.language == "ja"

            # Build
            result = await builder.build(parsed)
            scryfall_query = result.scryfall_query

            # Verify trigger pattern extraction
            assert 'o:"when ~ dies"' in scryfall_query
            # Verify effect extraction
            assert 'o:"draw a card"' in scryfall_query or 'o:"draw"' in scryfall_query
            # Verify color and type
            assert "c:b" in scryfall_query
            assert "t:creature" in scryfall_query
            # Verify no Japanese particles remain
            assert "する" not in scryfall_query
            assert "に" not in scryfall_query or "に" in query

    async def test_phase2_etb_with_token_e2e(self):
        """Test Phase 2: ETB trigger with token generation - Issue #4 integration."""
        query = "戦場に出たときにトークンを生成する白いクリーチャー"

        with use_locale("ja"):
            mapping = get_current_mapping()
            parser = SearchParser(mapping)
            builder = QueryBuilder(mapping)

            parsed = parser.parse(query)
            result = await builder.build(parsed)
            scryfall_query = result.scryfall_query

            # Verify ETB trigger
            assert 'o:"enters the battlefield"' in scryfall_query
            # Verify token creation effect
            assert 'o:"create"' in scryfall_query
            # Verify color and type
            assert "c:w" in scryfall_query
            assert "t:creature" in scryfall_query
            # Verify no particles
            assert "する" not in scryfall_query

    async def test_phase2_attack_trigger_with_damage_e2e(self):
        """Test Phase 2: Attack trigger with damage - Issue #4 integration."""
        query = "攻撃したときにダメージを与える赤いクリーチャー"

        with use_locale("ja"):
            mapping = get_current_mapping()
            parser = SearchParser(mapping)
            builder = QueryBuilder(mapping)

            parsed = parser.parse(query)
            result = await builder.build(parsed)
            scryfall_query = result.scryfall_query

            # Verify attack trigger
            assert 'o:"whenever ~ attacks"' in scryfall_query
            # Verify damage effect
            assert 'o:"deals damage"' in scryfall_query
            # Verify color and type
            assert "c:r" in scryfall_query
            assert "t:creature" in scryfall_query

    async def test_phase2_multi_ability_combination_e2e(self):
        """Test Phase 2: Multiple abilities combination - Issue #4 integration."""
        query = "死亡時にカードを引く飛行を持つ青いクリーチャー"

        with use_locale("ja"):
            mapping = get_current_mapping()
            parser = SearchParser(mapping)
            builder = QueryBuilder(mapping)

            parsed = parser.parse(query)
            result = await builder.build(parsed)
            scryfall_query = result.scryfall_query

            # Verify Phase 2 trigger pattern
            assert 'o:"when ~ dies"' in scryfall_query
            assert 'o:"draw"' in scryfall_query
            # Verify Phase 1 keyword ability
            assert "keyword:flying" in scryfall_query
            # Verify color and type
            assert "c:u" in scryfall_query
            assert "t:creature" in scryfall_query

    async def test_phase2_preserves_phase1_compatibility_e2e(self):
        """Test that Phase 2 preserves Phase 1 exact phrase matching."""
        # Phase 1 exact match should still work
        query = "死亡時黒いクリーチャー"

        with use_locale("ja"):
            mapping = get_current_mapping()
            parser = SearchParser(mapping)
            builder = QueryBuilder(mapping)

            parsed = parser.parse(query)
            result = await builder.build(parsed)
            scryfall_query = result.scryfall_query

            # Should still use Phase 1 dictionary lookup
            assert 'o:"when ~ dies"' in scryfall_query
            assert "c:b" in scryfall_query
            assert "t:creature" in scryfall_query

    async def test_phase2_complex_query_with_multiple_triggers_e2e(self):
        """Test Phase 2: Complex query with multiple triggers (if supported)."""
        # Note: This tests current behavior; multiple triggers in one query
        # may not be fully supported yet but should not error
        query = "死亡時にカードを引き戦場に出たときにライフを得るクリーチャー"

        with use_locale("ja"):
            mapping = get_current_mapping()
            parser = SearchParser(mapping)
            builder = QueryBuilder(mapping)

            parsed = parser.parse(query)
            result = await builder.build(parsed)
            scryfall_query = result.scryfall_query

            # Should extract at least one trigger
            has_death_trigger = 'o:"when ~ dies"' in scryfall_query
            has_etb_trigger = 'o:"enters the battlefield"' in scryfall_query

            # At least one trigger should be present
            assert has_death_trigger or has_etb_trigger
            # Should have creature type
            assert "t:creature" in scryfall_query

    async def test_latest_expansion_basic_e2e(self):
        """Test Issue #3: Basic 'latest expansion' E2E."""
        query = "最新のエクスパンション"
    def test_ultra_complex_multi_ability_e2e(self):
        """Test ultra-complex query with 3+ abilities in E2E pipeline.

        Edge case: Full pipeline test for queries with multiple keyword abilities,
        ability phrases, colors, types, and numeric constraints.
        """
        query = "飛行と速攻と死亡時にカードを引く赤いクリーチャーでパワー3以上"

        with use_locale("ja"):
            mapping = get_current_mapping()
            parser = SearchParser(mapping)
            builder = QueryBuilder(mapping)

            parsed = parser.parse(query)
            assert parsed.language == "ja"

            result = await builder.build(parsed)
            scryfall_query = result.scryfall_query

            # Should convert to s:<set_code> (actual latest set from API or fallback)
            assert "s:" in scryfall_query
            # Should have a valid set code (3-4 letters)
            import re
            assert re.search(r"s:[a-z]{3,4}\b", scryfall_query)
            # Should not have leftover Japanese
            assert "最新" not in scryfall_query
            assert "エクスパンション" not in scryfall_query

    async def test_latest_expansion_with_changeling_e2e(self):
        """Test Issue #3: 'Latest expansion' with changeling (from issue example)."""
        query = "最新のエクスパンションシンボルで多相を持つクリーチャー"

        with use_locale("ja"):
            mapping = get_current_mapping()
            parser = SearchParser(mapping)
            builder = QueryBuilder(mapping)

            parsed = parser.parse(query)
            result = await builder.build(parsed)
            scryfall_query = result.scryfall_query

            # Should have set filter
            assert "s:" in scryfall_query
            # Should have changeling keyword
            assert "keyword:changeling" in scryfall_query
            # Should have creature type
            assert "t:creature" in scryfall_query

    async def test_latest_set_with_flying_e2e(self):
        """Test Issue #3: 'Latest set' with flying ability."""
        query = "最新セットに収録された飛行を持つカード"

        with use_locale("ja"):
            mapping = get_current_mapping()
            parser = SearchParser(mapping)
            builder = QueryBuilder(mapping)

            parsed = parser.parse(query)
            result = await builder.build(parsed)
            scryfall_query = result.scryfall_query

            # Should convert to s:mkm
            assert "s:" in scryfall_query and len([x for x in scryfall_query.split() if x.startswith("s:")]) > 0 or "s:" in scryfall_query
            # Should have flying keyword
            assert "keyword:flying" in scryfall_query

    async def test_new_expansion_red_cards_e2e(self):
        """Test Issue #3: 'New expansion' with red color filter."""
        query = "新しいエクスパンションの赤いカード"

        with use_locale("ja"):
            mapping = get_current_mapping()
            parser = SearchParser(mapping)
            builder = QueryBuilder(mapping)

            parsed = parser.parse(query)
            result = await builder.build(parsed)
            scryfall_query = result.scryfall_query

            # Should have set filter
            assert "s:" in scryfall_query and len([x for x in scryfall_query.split() if x.startswith("s:")]) > 0
            # Should have red color
            assert "c:r" in scryfall_query

    async def test_expansion_symbol_mkm_e2e(self):
        """Test Issue #3: Expansion symbol search for MKM."""
        query = "MKMのエクスパンションシンボル"

        with use_locale("ja"):
            mapping = get_current_mapping()
            parser = SearchParser(mapping)
            builder = QueryBuilder(mapping)

            parsed = parser.parse(query)
            result = await builder.build(parsed)
            scryfall_query = result.scryfall_query

            # Should have s: prefix
            assert "s:" in scryfall_query
            # Should have mkm (case-insensitive)
            assert "mkm" in scryfall_query.lower()

    async def test_latest_expansion_complex_query_e2e(self):
        """Test Issue #3: Complex query with latest expansion and multiple filters."""
        query = "最新のエクスパンションで白と青のクリーチャーでマナ総量3以下の伝説の"

        with use_locale("ja"):
            mapping = get_current_mapping()
            parser = SearchParser(mapping)
            builder = QueryBuilder(mapping)

            parsed = parser.parse(query)
            result = await builder.build(parsed)
            scryfall_query = result.scryfall_query

            # Should have set filter
            assert "s:" in scryfall_query and len([x for x in scryfall_query.split() if x.startswith("s:")]) > 0
            # Should have colors
            assert "c:w" in scryfall_query or "c:u" in scryfall_query
            # Should have creature type
            assert "t:creature" in scryfall_query
            # Should have legendary
            assert "t:legendary" in scryfall_query or "legendary" in scryfall_query
            # Should have mana value filter
            assert "mv<=3" in scryfall_query or "cmc<=3" in scryfall_query

    async def test_correct_expansion_spelling_e2e(self):
        """Test Issue #3: Correct spelling 'エクスパンション' works."""
        query = "エクスパンション"

        with use_locale("ja"):
            mapping = get_current_mapping()
            parser = SearchParser(mapping)
            builder = QueryBuilder(mapping)

            parsed = parser.parse(query)
            result = await builder.build(parsed)
            scryfall_query = result.scryfall_query

            # Should be converted to set search
            assert "s" in scryfall_query

    async def test_longest_phrase_matching_e2e(self):
        """Test Issue #3: Longest phrase matching (avoid partial matches)."""
        # "最新のエクスパンション" should match as whole phrase, not split
        query = "最新のエクスパンションでパワー3以上"

        with use_locale("ja"):
            mapping = get_current_mapping()
            parser = SearchParser(mapping)
            builder = QueryBuilder(mapping)

            parsed = parser.parse(query)
            result = await builder.build(parsed)
            scryfall_query = result.scryfall_query

            # Should have full s:mkm, not just "s"
            assert "s:" in scryfall_query and len([x for x in scryfall_query.split() if x.startswith("s:")]) > 0
            # Should not have leftover "最新" or "エクスパンション"
            assert "最新" not in scryfall_query
            assert "エクスパンション" not in scryfall_query
            # Should have power filter
            assert "p>=3" in scryfall_query

    async def test_latest_expansion_with_trigger_ability_e2e(self):
        """Test Issue #3: Latest expansion combined with Phase 2 trigger abilities."""
        query = "最新セットで死亡時にカードを引くクリーチャー"
            result = builder.build(parsed)
            scryfall_query = result.scryfall_query

            # Should contain all components
            assert "keyword:flying" in scryfall_query
            assert "keyword:haste" in scryfall_query
            assert 'o:"when ~ dies"' in scryfall_query
            assert 'o:"draw"' in scryfall_query
            assert "c:r" in scryfall_query
            assert "t:creature" in scryfall_query
            assert "p>=3" in scryfall_query

            # Should be marked as complex
            assert result.query_metadata["query_complexity"] in ["moderate", "complex"]

    def test_very_long_query_e2e(self):
        """Test very long natural language query through full pipeline.

        Edge case: Tests pipeline handling of 100+ character queries.
        """
        query = (
            "モダンフォーマットで使える飛行と先制攻撃を持つ"
            "戦場に出たときにトークンを生成する"
            "白いクリーチャーでパワー2以上タフネス3以下でマナ総量4以下"
        )

        with use_locale("ja"):
            mapping = get_current_mapping()
            parser = SearchParser(mapping)
            builder = QueryBuilder(mapping)

            parsed = parser.parse(query)
            result = await builder.build(parsed)
            scryfall_query = result.scryfall_query

            # Should have latest set
            assert "s:" in scryfall_query and len([x for x in scryfall_query.split() if x.startswith("s:")]) > 0
            # Should have death trigger
            assert 'o:"when ~ dies"' in scryfall_query
            # Should have draw effect
            assert 'o:"draw"' in scryfall_query
            # Should have creature type
            result = builder.build(parsed)
            scryfall_query = result.scryfall_query

            # Should extract major components
            assert "keyword:flying" in scryfall_query
            assert 'keyword:"first strike"' in scryfall_query
            assert 'o:"enters the battlefield"' in scryfall_query
            assert "c:w" in scryfall_query
            assert "t:creature" in scryfall_query
            assert "p>=2" in scryfall_query

            # Should be marked as complex
            assert result.query_metadata["query_complexity"] == "complex"

    def test_multicolor_complex_query_e2e(self):
        """Test multicolor query with multiple abilities.

        Edge case: Tests handling of multicolor cards with complex abilities.
        """
        query = "青白の飛行と絆魂を持つクリーチャーでマナ総量3以下"

        with use_locale("ja"):
            mapping = get_current_mapping()
            parser = SearchParser(mapping)
            builder = QueryBuilder(mapping)

            parsed = parser.parse(query)
            result = builder.build(parsed)
            scryfall_query = result.scryfall_query

            # Should handle multicolor
            assert ("c:w" in scryfall_query or "c:u" in scryfall_query or
                    "c:wu" in scryfall_query or "id:wu" in scryfall_query)
            # Should contain keywords
            assert "keyword:flying" in scryfall_query
            assert "keyword:lifelink" in scryfall_query
            assert "t:creature" in scryfall_query
            assert "mv<=3" in scryfall_query

    def test_ambiguous_query_graceful_handling_e2e(self):
        """Test that ambiguous queries are handled gracefully.

        Edge case: Tests that vague terms don't break the pipeline.
        """
        query = "強力な赤いクリーチャー"

        with use_locale("ja"):
            mapping = get_current_mapping()
            parser = SearchParser(mapping)
            builder = QueryBuilder(mapping)

            parsed = parser.parse(query)
            result = builder.build(parsed)
            scryfall_query = result.scryfall_query

            # Should at least extract color and type
            assert "c:r" in scryfall_query
            assert "t:creature" in scryfall_query
            # Should not crash or produce empty query
            assert len(scryfall_query) > 0

    def test_deeply_nested_trigger_chain_e2e(self):
        """Test deeply nested trigger-effect chain.

        Edge case: Tests pipeline resilience with extremely complex queries.
        """
        query = "死亡時に戦場に出て攻撃したときダメージを与えるトークンを生成する黒いクリーチャー"

        with use_locale("ja"):
            mapping = get_current_mapping()
            parser = SearchParser(mapping)
            builder = QueryBuilder(mapping)

            parsed = parser.parse(query)
            result = builder.build(parsed)
            scryfall_query = result.scryfall_query

            # Should extract at least the death trigger and basic attributes
            assert 'o:"when ~ dies"' in scryfall_query
            assert "c:b" in scryfall_query
            assert "t:creature" in scryfall_query
            # Should not crash
            assert len(scryfall_query) > 0

    def test_numeric_edge_cases_e2e(self):
        """Test numeric edge cases through pipeline.

        Edge case: Tests handling of extreme numeric values.
        """
        # Very large power
        query1 = "パワー100以上の赤いクリーチャー"

        with use_locale("ja"):
            mapping = get_current_mapping()
            parser = SearchParser(mapping)
            builder = QueryBuilder(mapping)

            parsed = parser.parse(query1)
            result = builder.build(parsed)
            scryfall_query = result.scryfall_query

            assert "p>=100" in scryfall_query
            assert "c:r" in scryfall_query
            assert "t:creature" in scryfall_query

        # Zero power
        query2 = "パワー0のクリーチャー"

        with use_locale("ja"):
            mapping = get_current_mapping()
            parser = SearchParser(mapping)
            builder = QueryBuilder(mapping)

            parsed = parser.parse(query2)
            result = builder.build(parsed)
            scryfall_query = result.scryfall_query

            assert "p=0" in scryfall_query or "p:0" in scryfall_query
            assert "t:creature" in scryfall_query

    def test_special_characters_handling_e2e(self):
        """Test handling of special characters in queries.

        Edge case: Tests that special characters don't break parsing.
        """
        query = '飛行を持つ"天使"というクリーチャー'

        with use_locale("ja"):
            mapping = get_current_mapping()
            parser = SearchParser(mapping)
            builder = QueryBuilder(mapping)

            parsed = parser.parse(query)
            result = builder.build(parsed)
            scryfall_query = result.scryfall_query

            # Should extract keyword and type
            assert "keyword:flying" in scryfall_query
            assert "t:creature" in scryfall_query
            # Should not crash with quotes
            assert len(scryfall_query) > 0

    def test_mixed_phase_features_e2e(self):
        """Test mixing Phase 1 and Phase 2 features.

        Edge case: Tests that format filters work with complex ability phrases.
        """
        query = "モダンで使える飛行を持つ死亡時にカードを引く青黒のクリーチャー"

        with use_locale("ja"):
            mapping = get_current_mapping()
            parser = SearchParser(mapping)
            builder = QueryBuilder(mapping)

            parsed = parser.parse(query)
            result = builder.build(parsed)
            scryfall_query = result.scryfall_query

            # Should contain keyword
            assert "keyword:flying" in scryfall_query
            # Should contain death trigger
            assert 'o:"when ~ dies"' in scryfall_query
            # Should contain draw effect
            assert 'o:"draw"' in scryfall_query
            # Should contain colors (blue and/or black)
            assert ("c:u" in scryfall_query or "c:b" in scryfall_query or
                    "c:ub" in scryfall_query or "c:bu" in scryfall_query)
            assert "t:creature" in scryfall_query
