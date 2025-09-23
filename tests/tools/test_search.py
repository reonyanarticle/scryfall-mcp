"""Tests for search tools module."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import pytest
from mcp.types import TextContent

from scryfall_mcp.api.client import ScryfallAPIError
from scryfall_mcp.api.models import SearchResult
from scryfall_mcp.tools.search import (
    AutocompleteRequest,
    AutocompleteTool,
    CardSearchTool,
    SearchCardsRequest,
)


class TestSearchCardsRequest:
    """Test SearchCardsRequest model."""

    def test_valid_request(self):
        """Test valid search request."""
        request = SearchCardsRequest(
            query="Lightning Bolt",
            language="en",
            max_results=10,
            include_images=True,
            format_filter="modern",
        )

        assert request.query == "Lightning Bolt"
        assert request.language == "en"
        assert request.max_results == 10
        assert request.include_images is True
        assert request.format_filter == "modern"

    def test_minimal_request(self):
        """Test minimal search request."""
        request = SearchCardsRequest(query="test")

        assert request.query == "test"
        assert request.language is None
        assert request.max_results == 20  # Default
        assert request.include_images is True  # Default
        assert request.format_filter is None

    def test_validation_errors(self):
        """Test request validation."""
        # Test max_results validation
        with pytest.raises(ValueError):
            SearchCardsRequest(query="test", max_results=0)

        with pytest.raises(ValueError):
            SearchCardsRequest(query="test", max_results=200)


class TestAutocompleteRequest:
    """Test AutocompleteRequest model."""

    def test_valid_request(self):
        """Test valid autocomplete request."""
        request = AutocompleteRequest(
            query="Light",
            language="ja",
        )

        assert request.query == "Light"
        assert request.language == "ja"

    def test_minimal_request(self):
        """Test minimal autocomplete request."""
        request = AutocompleteRequest(query="test")

        assert request.query == "test"
        assert request.language is None


class TestCardSearchTool:
    """Test CardSearchTool class."""

    def test_get_tool_definition(self):
        """Test tool definition."""
        tool_def = CardSearchTool.get_tool_definition()

        assert tool_def.name == "search_cards"
        assert "Magic: The Gathering" in tool_def.description
        assert "Japanese" in tool_def.description
        assert tool_def.inputSchema is not None

    @pytest.mark.asyncio
    async def test_execute_success(self, sample_search_result):
        """Test successful tool execution."""
        arguments = {
            "query": "Lightning Bolt",
            "language": "en",
            "max_results": 5,
            "include_images": True,
        }

        with patch("scryfall_mcp.tools.search.SearchProcessor") as mock_processor_class:
            with patch("scryfall_mcp.tools.search.get_client") as mock_get_client:
                # Setup mocks
                mock_processor = Mock()
                mock_processor.process_query.return_value = {
                    "original_query": "Lightning Bolt",
                    "scryfall_query": "Lightning Bolt",
                    "detected_intent": "card_search",
                    "extracted_entities": {},
                    "suggestions": [],
                }
                mock_processor_class.return_value = mock_processor

                mock_client = AsyncMock()
                mock_client.search_cards.return_value = sample_search_result
                mock_get_client.return_value = mock_client

                # Execute tool
                result = await CardSearchTool.execute(arguments)

                # Check results
                assert len(result) >= 2  # Summary + at least one card
                assert isinstance(result[0], TextContent)
                assert "検索結果" in result[0].text or "Search Results" in result[0].text

                # Check that client was called correctly
                mock_client.search_cards.assert_called_once()
                call_args = mock_client.search_cards.call_args
                assert call_args[1]["query"] == "Lightning Bolt"

    @pytest.mark.asyncio
    async def test_execute_with_japanese(self, sample_search_result):
        """Test tool execution with Japanese query."""
        arguments = {
            "query": "白いクリーチャー",
            "language": "ja",
            "max_results": 10,
        }

        with patch("scryfall_mcp.tools.search.SearchProcessor") as mock_processor_class:
            with patch("scryfall_mcp.tools.search.get_client") as mock_get_client:
                # Setup mocks
                mock_processor = Mock()
                mock_processor.process_query.return_value = {
                    "original_query": "白いクリーチャー",
                    "scryfall_query": "c:w t:creature",
                    "detected_intent": "card_search",
                    "extracted_entities": {},
                    "suggestions": [],
                }
                mock_processor_class.return_value = mock_processor

                mock_client = AsyncMock()
                mock_client.search_cards.return_value = sample_search_result
                mock_get_client.return_value = mock_client

                with patch("scryfall_mcp.tools.search.set_current_locale") as mock_set_locale:
                    result = await CardSearchTool.execute(arguments)

                    # Check that locale was set
                    mock_set_locale.assert_called_with("ja")

                    # Check that processed query was used
                    call_args = mock_client.search_cards.call_args
                    assert call_args[1]["query"] == "c:w t:creature"

    @pytest.mark.asyncio
    async def test_execute_with_format_filter(self, sample_search_result):
        """Test tool execution with format filter."""
        arguments = {
            "query": "Lightning Bolt",
            "format_filter": "standard",
        }

        with patch("scryfall_mcp.tools.search.SearchProcessor") as mock_processor_class:
            with patch("scryfall_mcp.tools.search.get_client") as mock_get_client:
                mock_processor = Mock()
                mock_processor.process_query.return_value = {
                    "original_query": "Lightning Bolt",
                    "scryfall_query": "Lightning Bolt",
                    "detected_intent": "card_search",
                    "extracted_entities": {},
                    "suggestions": [],
                }
                mock_processor_class.return_value = mock_processor

                mock_client = AsyncMock()
                mock_client.search_cards.return_value = sample_search_result
                mock_get_client.return_value = mock_client

                await CardSearchTool.execute(arguments)

                # Check that format filter was added
                call_args = mock_client.search_cards.call_args
                assert call_args[1]["query"] == "Lightning Bolt f:standard"

    @pytest.mark.asyncio
    async def test_execute_no_results(self):
        """Test tool execution with no results."""
        arguments = {"query": "nonexistent card"}

        with patch("scryfall_mcp.tools.search.SearchProcessor") as mock_processor_class:
            with patch("scryfall_mcp.tools.search.get_client") as mock_get_client:
                # Setup mocks for no results
                mock_processor = Mock()
                mock_processor.process_query.return_value = {
                    "original_query": "nonexistent card",
                    "scryfall_query": "nonexistent card",
                    "detected_intent": "card_search",
                    "extracted_entities": {},
                    "suggestions": [],
                }
                mock_processor_class.return_value = mock_processor

                empty_result = SearchResult(
                    object="list",
                    total_cards=0,
                    has_more=False,
                    data=[],
                )

                mock_client = AsyncMock()
                mock_client.search_cards.return_value = empty_result
                mock_get_client.return_value = mock_client

                result = await CardSearchTool.execute(arguments)

                # Should return no results message
                assert len(result) == 1
                assert isinstance(result[0], TextContent)
                assert "No cards found" in result[0].text or "見つかりません" in result[0].text

    @pytest.mark.asyncio
    async def test_execute_api_error(self):
        """Test tool execution with API error."""
        arguments = {"query": "invalid query"}

        with patch("scryfall_mcp.tools.search.SearchProcessor") as mock_processor_class:
            with patch("scryfall_mcp.tools.search.get_client") as mock_get_client:
                mock_processor = Mock()
                mock_processor.process_query.return_value = {
                    "original_query": "invalid query",
                    "scryfall_query": "invalid query",
                    "detected_intent": "card_search",
                    "extracted_entities": {},
                    "suggestions": [],
                }
                mock_processor_class.return_value = mock_processor

                mock_client = AsyncMock()
                mock_client.search_cards.side_effect = ScryfallAPIError("Invalid query", 400)
                mock_get_client.return_value = mock_client

                result = await CardSearchTool.execute(arguments)

                # Should return error message
                assert len(result) == 1
                assert isinstance(result[0], TextContent)
                assert "エラー" in result[0].text or "error" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_execute_with_suggestions(self, sample_search_result):
        """Test tool execution with suggestions."""
        arguments = {"query": "Lightning"}

        with patch("scryfall_mcp.tools.search.SearchProcessor") as mock_processor_class:
            with patch("scryfall_mcp.tools.search.get_client") as mock_get_client:
                mock_processor = Mock()
                mock_processor.process_query.return_value = {
                    "original_query": "Lightning",
                    "scryfall_query": "Lightning",
                    "detected_intent": "card_search",
                    "extracted_entities": {},
                    "suggestions": ["Did you mean Lightning Bolt?"],
                }
                mock_processor_class.return_value = mock_processor

                mock_client = AsyncMock()
                mock_client.search_cards.return_value = sample_search_result
                mock_get_client.return_value = mock_client

                result = await CardSearchTool.execute(arguments)

                # Should include suggestions
                suggestion_content = next(
                    (item for item in result if isinstance(item, TextContent) and "Suggestions" in item.text),
                    None,
                )
                assert suggestion_content is not None
                assert "Lightning Bolt" in suggestion_content.text

    @pytest.mark.asyncio
    async def test_execute_unexpected_error(self):
        """Test tool execution with unexpected error."""
        arguments = {"query": "test"}

        with patch("scryfall_mcp.tools.search.SearchProcessor") as mock_processor_class:
            mock_processor_class.side_effect = Exception("Unexpected error")

            result = await CardSearchTool.execute(arguments)

            # Should return error message
            assert len(result) == 1
            assert isinstance(result[0], TextContent)
            assert "error" in result[0].text.lower()

    def test_format_search_summary_english(self):
        """Test search summary formatting in English."""
        processed = {
            "original_query": "Lightning Bolt",
            "scryfall_query": "Lightning Bolt",
            "detected_intent": "card_search",
            "extracted_entities": {},
            "suggestions": [],
        }

        summary = CardSearchTool._format_search_summary(processed, 10, 5, "en")

        assert "Search Results" in summary
        assert "Lightning Bolt" in summary
        assert "Total cards: 10" in summary
        assert "Showing: 5" in summary

    def test_format_search_summary_japanese(self):
        """Test search summary formatting in Japanese."""
        processed = {
            "original_query": "白いクリーチャー",
            "scryfall_query": "c:w t:creature",
            "detected_intent": "card_search",
            "extracted_entities": {},
            "suggestions": [],
        }

        summary = CardSearchTool._format_search_summary(processed, 15, 8, "ja")

        assert "検索結果" in summary
        assert "白いクリーチャー" in summary
        assert "総カード数: 15" in summary
        assert "表示: 8" in summary

    def test_format_card_result_english(self, sample_card):
        """Test card result formatting in English."""
        result = CardSearchTool._format_card_result(sample_card, 1, "en")

        assert "1. Lightning Bolt" in result
        assert "Mana Cost: {R}" in result
        assert "Type: Instant" in result
        assert "Rarity: common" in result

    def test_format_card_result_japanese(self, sample_card):
        """Test card result formatting in Japanese."""
        result = CardSearchTool._format_card_result(sample_card, 2, "ja")

        assert "2. Lightning Bolt" in result
        assert "マナコスト: {R}" in result
        assert "タイプ: Instant" in result
        assert "レアリティ: common" in result

    def test_format_card_result_with_power_toughness(self, sample_card):
        """Test card result formatting with power/toughness."""
        # Modify sample card to have power/toughness
        sample_card.power = "2"
        sample_card.toughness = "3"

        result = CardSearchTool._format_card_result(sample_card, 1, "en")

        assert "Power/Toughness: 2/3" in result

    def test_format_card_result_with_loyalty(self, sample_card):
        """Test card result formatting with loyalty."""
        # Modify sample card to have loyalty
        sample_card.loyalty = "4"

        result = CardSearchTool._format_card_result(sample_card, 1, "en")

        assert "Loyalty: 4" in result


class TestAutocompleteTool:
    """Test AutocompleteTool class."""

    def test_get_tool_definition(self):
        """Test tool definition."""
        tool_def = AutocompleteTool.get_tool_definition()

        assert tool_def.name == "autocomplete_card_names"
        assert "suggestions" in tool_def.description
        assert tool_def.inputSchema is not None

    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Test successful autocomplete execution."""
        arguments = {
            "query": "Light",
            "language": "en",
        }

        suggestions = ["Lightning Bolt", "Lightning Strike", "Lightning Helix"]

        with patch("scryfall_mcp.tools.search.get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.autocomplete_card_name.return_value = suggestions
            mock_get_client.return_value = mock_client

            result = await AutocompleteTool.execute(arguments)

            # Check results
            assert len(result) == 1
            assert isinstance(result[0], TextContent)
            assert "Suggestions for 'Light'" in result[0].text
            assert "Lightning Bolt" in result[0].text
            assert "Lightning Strike" in result[0].text

    @pytest.mark.asyncio
    async def test_execute_no_suggestions(self):
        """Test autocomplete with no suggestions."""
        arguments = {"query": "nonexistent"}

        with patch("scryfall_mcp.tools.search.get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.autocomplete_card_name.return_value = []
            mock_get_client.return_value = mock_client

            result = await AutocompleteTool.execute(arguments)

            # Should return no suggestions message
            assert len(result) == 1
            assert isinstance(result[0], TextContent)
            assert "No suggestions found" in result[0].text or "No cards found" in result[0].text or "見つかりません" in result[0].text

    @pytest.mark.asyncio
    async def test_execute_with_japanese(self):
        """Test autocomplete with Japanese language setting."""
        arguments = {
            "query": "ライト",
            "language": "ja",
        }

        suggestions = ["Lightning Bolt", "Light Up the Stage"]

        with patch("scryfall_mcp.tools.search.get_client") as mock_get_client:
            with patch("scryfall_mcp.tools.search.set_current_locale") as mock_set_locale:
                mock_client = AsyncMock()
                mock_client.autocomplete_card_name.return_value = suggestions
                mock_get_client.return_value = mock_client

                result = await AutocompleteTool.execute(arguments)

                # Check that locale was set
                mock_set_locale.assert_called_with("ja")

                # Check results format
                assert len(result) == 1
                assert isinstance(result[0], TextContent)
                assert "候補" in result[0].text  # Japanese for "suggestions"

    @pytest.mark.asyncio
    async def test_execute_error(self):
        """Test autocomplete with error."""
        arguments = {"query": "test"}

        with patch("scryfall_mcp.tools.search.get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.autocomplete_card_name.side_effect = Exception("API error")
            mock_get_client.return_value = mock_client

            result = await AutocompleteTool.execute(arguments)

            # Should return error message
            assert len(result) == 1
            assert isinstance(result[0], TextContent)
            assert "error" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_execute_limit_suggestions(self):
        """Test that autocomplete limits suggestions to 10."""
        arguments = {"query": "a"}

        # Return more than 10 suggestions
        many_suggestions = [f"Card {i}" for i in range(15)]

        with patch("scryfall_mcp.tools.search.get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.autocomplete_card_name.return_value = many_suggestions
            mock_get_client.return_value = mock_client

            result = await AutocompleteTool.execute(arguments)

            # Should limit to 10
            assert len(result) == 1
            text = result[0].text
            suggestion_lines = [line for line in text.split("\n") if line.startswith("- ")]
            assert len(suggestion_lines) == 10
