"""Tests for set information tools."""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest

from scryfall_mcp.models import Set as ScryfallSet
from scryfall_mcp.tools.sets import GetLatestExpansionSetTool


class TestGetLatestExpansionSetTool:
    """Tests for GetLatestExpansionSetTool."""

    def test_get_tool_definition(self):
        """Test tool definition."""
        tool_def = GetLatestExpansionSetTool.get_tool_definition()

        assert tool_def.name == "get_latest_expansion_set"
        assert "latest" in tool_def.description.lower()
        assert "expansion" in tool_def.description.lower()
        assert tool_def.inputSchema["type"] == "object"
        assert tool_def.inputSchema["required"] == []

    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Test successful execution."""
        # Mock set data
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

        with (
            patch("scryfall_mcp.tools.sets.get_client") as mock_get_client,
            patch("scryfall_mcp.tools.sets.get_latest_expansion_code") as mock_get_code,
        ):
            mock_client = AsyncMock()
            mock_client.get_latest_expansion_set = AsyncMock(return_value=mock_set)
            mock_get_client.return_value = mock_client
            mock_get_code.return_value = "spm"

            result = await GetLatestExpansionSetTool.execute({})

            assert len(result) == 1
            assert result[0].type == "text"
            assert "Marvel's Spider-Man" in result[0].text
            assert "SPM" in result[0].text
            assert "2025-09-26" in result[0].text
            assert "286" in result[0].text

    @pytest.mark.asyncio
    async def test_execute_no_set_found(self):
        """Test when no set is found."""
        with patch("scryfall_mcp.tools.sets.get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get_latest_expansion_set = AsyncMock(return_value=None)
            mock_get_client.return_value = mock_client

            result = await GetLatestExpansionSetTool.execute({})

            assert len(result) == 1
            assert result[0].type == "text"
            assert "見つかりませんでした" in result[0].text

    @pytest.mark.asyncio
    async def test_execute_error(self):
        """Test error handling."""
        with patch("scryfall_mcp.tools.sets.get_client") as mock_get_client:
            mock_get_client.side_effect = Exception("API Error")

            result = await GetLatestExpansionSetTool.execute({})

            assert len(result) == 1
            assert result[0].type == "text"
            assert "エラー" in result[0].text
            assert "API Error" in result[0].text
