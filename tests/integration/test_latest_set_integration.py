"""Integration tests for latest set functionality."""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest

from scryfall_mcp.api.sets import clear_latest_set_cache, get_latest_expansion_code
from scryfall_mcp.i18n import get_current_mapping, set_current_locale
from scryfall_mcp.models import Set as ScryfallSet
from scryfall_mcp.search.builder import QueryBuilder
from scryfall_mcp.search.parser import SearchParser
from scryfall_mcp.tools.sets import GetLatestExpansionSetTool


@pytest.fixture(autouse=True)
async def clear_cache():
    """Clear cache before each test."""
    await clear_latest_set_cache()
    yield
    await clear_latest_set_cache()


class TestLatestSetIntegration:
    """Integration tests for latest set functionality."""

    @pytest.mark.asyncio
    async def test_latest_set_query_pipeline(self):
        """Test complete pipeline from Japanese query to Scryfall query."""
        # Setup
        set_current_locale("ja")
        mapping = get_current_mapping()
        parser = SearchParser(mapping)
        builder = QueryBuilder(mapping)

        # Mock the API call
        mock_set = ScryfallSet(
            object="set",
            id=UUID("00000000-0000-0000-0000-000000000000"),
            code="spm",
            name="Marvel's Spider-Man",
            uri="https://api.scryfall.com/sets/spm",
            scryfall_uri="https://scryfall.com/sets/spm",
            search_uri="https://api.scryfall.com/cards/search?q=e:spm",
            icon_svg_uri="https://api.scryfall.com/sets/spm/icon.svg",
            released_at=date(2025, 9, 26),
            set_type="expansion",
            card_count=286,
            digital=False,
            nonfoil_only=False,
            foil_only=False,
        )

        with patch("scryfall_mcp.api.client.get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get_latest_expansion_set = AsyncMock(return_value=mock_set)
            mock_get_client.return_value = mock_client

            # Test various Japanese queries
            test_queries = [
                "最新のエクスパンション",
                "最新のセット",
                "最新セット",
                "新しいエクスパンション",
                "一番新しいセット",
            ]

            for query in test_queries:
                # Parse and build
                parsed = parser.parse(query)
                built = await builder.build(parsed)

                # Verify the query was converted to set search
                assert built.scryfall_query.startswith("s:")
                assert "spm" in built.scryfall_query.lower()
                assert "__LATEST_SET__" not in built.scryfall_query

    @pytest.mark.asyncio
    async def test_get_latest_set_tool_integration(self):
        """Test get_latest_expansion_set tool integration."""
        mock_set = ScryfallSet(
            object="set",
            id=UUID("00000000-0000-0000-0000-000000000000"),
            code="mkm",
            name="Murders at Karlov Manor",
            uri="https://api.scryfall.com/sets/mkm",
            scryfall_uri="https://scryfall.com/sets/mkm",
            search_uri="https://api.scryfall.com/cards/search?q=e:mkm",
            icon_svg_uri="https://api.scryfall.com/sets/mkm/icon.svg",
            released_at=date(2024, 2, 9),
            set_type="expansion",
            card_count=286,
            digital=False,
            nonfoil_only=False,
            foil_only=False,
        )

        with (
            patch("scryfall_mcp.tools.sets.get_client") as mock_get_client,
            patch("scryfall_mcp.tools.sets.get_latest_expansion_code") as mock_get_code,
        ):
            mock_client = AsyncMock()
            mock_client.get_latest_expansion_set = AsyncMock(return_value=mock_set)
            mock_get_client.return_value = mock_client
            mock_get_code.return_value = "mkm"

            # Execute tool
            result = await GetLatestExpansionSetTool.execute({})

            # Verify response
            assert len(result) == 1
            assert result[0].type == "text"
            assert "Murders at Karlov Manor" in result[0].text
            assert "MKM" in result[0].text
            assert "2024-02-09" in result[0].text

    @pytest.mark.asyncio
    async def test_cache_integration(self):
        """Test that caching works correctly across multiple calls."""
        mock_set = ScryfallSet(
            object="set",
            id=UUID("00000000-0000-0000-0000-000000000000"),
            code="test",
            name="Test Set",
            uri="https://api.scryfall.com/sets/test",
            scryfall_uri="https://scryfall.com/sets/test",
            search_uri="https://api.scryfall.com/cards/search?q=e:test",
            icon_svg_uri="https://api.scryfall.com/sets/test/icon.svg",
            released_at=date(2024, 1, 1),
            set_type="expansion",
            card_count=100,
            digital=False,
            nonfoil_only=False,
            foil_only=False,
        )

        mock_client = AsyncMock()
        mock_client.get_latest_expansion_set = AsyncMock(return_value=mock_set)

        # First call - should fetch from API
        code1 = await get_latest_expansion_code(mock_client)
        assert code1 == "test"
        assert mock_client.get_latest_expansion_set.call_count == 1

        # Second call - should use cache
        code2 = await get_latest_expansion_code(mock_client)
        assert code2 == "test"
        assert mock_client.get_latest_expansion_set.call_count == 1  # Still 1

        # Clear cache
        await clear_latest_set_cache()

        # Third call - should fetch again
        code3 = await get_latest_expansion_code(mock_client)
        assert code3 == "test"
        assert mock_client.get_latest_expansion_set.call_count == 2

    @pytest.mark.asyncio
    async def test_language_filter_not_added_for_set_only_search(self):
        """Test that language filter is not added for set-only searches."""
        # This is a regression test for the issue where lang:ja was added
        # to set-only searches, causing 404 errors
        set_current_locale("ja")

        mock_set = ScryfallSet(
            object="set",
            id=UUID("00000000-0000-0000-0000-000000000000"),
            code="spm",
            name="Marvel's Spider-Man",
            uri="https://api.scryfall.com/sets/spm",
            scryfall_uri="https://scryfall.com/sets/spm",
            search_uri="https://api.scryfall.com/cards/search?q=e:spm",
            icon_svg_uri="https://api.scryfall.com/sets/spm/icon.svg",
            released_at=date(2025, 9, 26),
            set_type="expansion",
            card_count=286,
            digital=False,
            nonfoil_only=False,
            foil_only=False,
        )

        with patch("scryfall_mcp.api.client.get_client") as mock_get_client:
            # Setup mocks
            mock_client = AsyncMock()
            mock_client.get_latest_expansion_set = AsyncMock(return_value=mock_set)
            mock_get_client.return_value = mock_client

            # Build query
            mapping = get_current_mapping()
            parser = SearchParser(mapping)
            builder = QueryBuilder(mapping)

            parsed = parser.parse("最新のエクスパンション")
            built = await builder.build(parsed)

            # The query should be just "s:spm", not "s:spm lang:ja"
            assert built.scryfall_query == "s:spm"
            assert "lang:" not in built.scryfall_query
