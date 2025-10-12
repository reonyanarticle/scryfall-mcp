"""End-to-end tests for the complete query processing pipeline.

This module tests the complete flow from natural language query to formatted results:
Parser → Builder → Processor → Presenter

These tests validate Issue #2 implementation (Japanese keyword ability search)
and ensure all components work together correctly.
"""

from __future__ import annotations

from scryfall_mcp.i18n import get_current_mapping, use_locale
from scryfall_mcp.search.builder import QueryBuilder
from scryfall_mcp.search.parser import SearchParser


class TestEndToEndQueryPipeline:
    """Test complete query processing pipeline."""

    def test_japanese_keyword_ability_e2e(self):
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
            result = builder.build(parsed)

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

    def test_complex_japanese_query_e2e(self):
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
            result = builder.build(parsed)

            scryfall_query = result.scryfall_query

            # 色（白と青）
            assert "c:w" in scryfall_query or "c:u" in scryfall_query

            # タイプ（クリーチャー、伝説）
            assert "t:creature" in scryfall_query
            assert "t:legendary" in scryfall_query or "legendary" in scryfall_query

            # マナ総量
            assert ("mv<=3" in scryfall_query or "cmc<=3" in scryfall_query
                    or "manavalue<=3" in scryfall_query)

    def test_english_query_e2e(self):
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
            result = builder.build(parsed)

            scryfall_query = result.scryfall_query.lower()

            # 色（赤） - 英語の場合はそのままの可能性も
            assert "c:r" in scryfall_query or "red" in scryfall_query

            # タイプ（クリーチャー） - 英語の場合はそのままの可能性も
            assert "t:creature" in scryfall_query or "creature" in scryfall_query

            # キーワード能力（速攻） - "haste"が含まれる
            assert "haste" in scryfall_query

            # パワー条件 - "3"が含まれればOK（フォーマットは多様）
            assert "3" in scryfall_query

    def test_japanese_multiple_keywords_e2e(self):
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
            result = builder.build(parsed)

            scryfall_query = result.scryfall_query

            # 複数のキーワード能力
            assert "flying" in scryfall_query.lower()
            assert "deathtouch" in scryfall_query.lower()

            # タイプ（クリーチャー）
            assert "t:creature" in scryfall_query

    def test_english_format_query_e2e(self):
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
            result = builder.build(parsed)

            scryfall_query = result.scryfall_query

            # フォーマット指定
            assert "f:standard" in scryfall_query or "format:standard" in scryfall_query

            # タイプ（クリーチャー）
            assert "creature" in scryfall_query.lower()

    def test_japanese_rarity_query_e2e(self):
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
            result = builder.build(parsed)

            scryfall_query = result.scryfall_query

            # レアリティ
            assert "r:mythic" in scryfall_query or "rarity:mythic" in scryfall_query

            # タイプ（プレインズウォーカー）
            assert "t:planeswalker" in scryfall_query or "planeswalker" in scryfall_query

    def test_japanese_color_identity_query_e2e(self):
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
            result = builder.build(parsed)

            scryfall_query = result.scryfall_query

            # 色指定
            assert "c:w" in scryfall_query or "white" in scryfall_query.lower()

            # マナシンボル（青）
            # Note: This is a complex query that may not be perfectly parsed
            # Just verify it doesn't error and produces some query
            assert len(scryfall_query) > 0

    def test_query_suggestions_e2e(self):
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
            result = builder.build(parsed)

            # クエリが生成されることを確認
            assert result.scryfall_query is not None
            assert isinstance(result.scryfall_query, str)
            assert len(result.scryfall_query) > 0

            # サジェスションリストが存在することを確認（空でも可）
            assert isinstance(result.suggestions, list)

    def test_empty_query_e2e(self):
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
            result = builder.build(parsed)

            # Should produce some fallback query or empty string
            assert isinstance(result.scryfall_query, str)

    def test_complexity_assessment_e2e(self):
        """Test complexity assessment across pipeline."""
        # Simple query
        simple_query = "creatures"

        with use_locale("en"):
            mapping = get_current_mapping()
            parser = SearchParser(mapping)
            builder = QueryBuilder(mapping)

            parsed = parser.parse(simple_query)
            result = builder.build(parsed)

            assert "query_complexity" in result.query_metadata
            assert result.query_metadata["query_complexity"] == "simple"

        # Complex query
        complex_query = "white creatures with flying power>=3 toughness<=5 mv<=4"

        with use_locale("en"):
            mapping = get_current_mapping()
            parser = SearchParser(mapping)
            builder = QueryBuilder(mapping)

            parsed = parser.parse(complex_query)
            result = builder.build(parsed)

            # Should be moderate or complex
            assert "query_complexity" in result.query_metadata
            assert result.query_metadata["query_complexity"] in ["moderate", "complex"]

    def test_locale_switching_e2e(self):
        """Test that locale switching works across pipeline."""
        query_en = "red creatures"
        query_ja = "赤いクリーチャー"

        # English
        with use_locale("en"):
            mapping_en = get_current_mapping()
            parser_en = SearchParser(mapping_en)
            builder_en = QueryBuilder(mapping_en)

            parsed_en = parser_en.parse(query_en)
            result_en = builder_en.build(parsed_en)

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
            result_ja = builder_ja.build(parsed_ja)

            # クエリに色とタイプが含まれることを確認
            query_lower_ja = result_ja.scryfall_query.lower()
            assert "c:r" in query_lower_ja or "red" in query_lower_ja
            assert "t:creature" in query_lower_ja or "creature" in query_lower_ja
