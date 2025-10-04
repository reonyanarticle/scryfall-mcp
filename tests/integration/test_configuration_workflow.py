"""Integration tests for the configuration workflow.

Tests the end-to-end flow:
1. search_cards without configuration -> error message
2. configure_user_agent with valid contact -> success
3. search_cards with configuration -> search executes
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
from mcp.types import TextContent

from scryfall_mcp.models import SearchResult
from scryfall_mcp.tools.configure import ConfigureUserAgentTool
from scryfall_mcp.tools.search import CardSearchTool


class TestConfigurationWorkflow:
    """Integration tests for configuration workflow."""

    @pytest.mark.asyncio
    async def test_search_without_configuration(self):
        """Test that search_cards requires configuration first."""
        # Mock is_user_agent_configured to return False
        with patch(
            "scryfall_mcp.tools.search.is_user_agent_configured", return_value=False
        ):
            arguments = {"query": "Lightning Bolt"}
            result = await CardSearchTool.execute(arguments)

            # Should return configuration required message
            assert len(result) == 1
            assert isinstance(result[0], TextContent)
            assert "Configuration Required" in result[0].text
            assert "configure_user_agent" in result[0].text

    @pytest.mark.asyncio
    async def test_configure_then_search_success(self, sample_search_result):
        """Test successful flow: configure then search."""
        # Step 1: Configure User-Agent
        with patch("scryfall_mcp.tools.configure.save_config") as mock_save, patch(
            "scryfall_mcp.tools.configure.reload_settings"
        ) as mock_reload:
            mock_save.return_value = {
                "user_agent": "Scryfall-MCP-Server/0.1.0 (test@example.com)",
                "contact": "test@example.com",
            }

            config_result = await ConfigureUserAgentTool.execute(
                {"contact": "test@example.com"}
            )

            # Verify configuration succeeded
            assert len(config_result) == 1
            assert "✅" in config_result[0].text
            assert mock_save.called
            assert mock_reload.called

        # Step 2: Search cards (should work now)
        mock_client = Mock()
        mock_client.search_cards.return_value = sample_search_result

        with patch(
            "scryfall_mcp.tools.search.is_user_agent_configured", return_value=True
        ), patch(
            "scryfall_mcp.tools.search.get_client", return_value=mock_client
        ):
            search_result = await CardSearchTool.execute({"query": "Lightning Bolt"})

            # Should return search results (not configuration error)
            assert len(search_result) >= 1
            # First item should be summary text or resource
            assert search_result[0].type in ("text", "resource")
            # Should not contain configuration required message
            text_contents = [
                r for r in search_result if isinstance(r, TextContent)
            ]
            if text_contents:
                assert "Configuration Required" not in text_contents[0].text

    @pytest.mark.asyncio
    async def test_configure_with_invalid_then_valid(self):
        """Test configuration retry after invalid input."""
        # Step 1: Try invalid contact
        invalid_result = await ConfigureUserAgentTool.execute(
            {"contact": "http://example.com"}
        )
        assert "❌" in invalid_result[0].text
        assert "https://" in invalid_result[0].text.lower()

        # Step 2: Try with valid contact
        with patch("scryfall_mcp.tools.configure.save_config") as mock_save, patch(
            "scryfall_mcp.tools.configure.reload_settings"
        ):
            mock_save.return_value = {
                "user_agent": "Scryfall-MCP-Server/0.1.0 (test@example.com)",
                "contact": "test@example.com",
            }

            valid_result = await ConfigureUserAgentTool.execute(
                {"contact": "test@example.com"}
            )
            assert "✅" in valid_result[0].text

    @pytest.mark.asyncio
    async def test_search_after_configuration_reload(self, sample_search_result):
        """Test that search works after settings reload."""
        # Configure
        with patch("scryfall_mcp.tools.configure.save_config") as mock_save, patch(
            "scryfall_mcp.tools.configure.reload_settings"
        ) as mock_reload:
            mock_save.return_value = {
                "user_agent": "Scryfall-MCP-Server/0.1.0 (test@example.com)",
                "contact": "test@example.com",
            }

            await ConfigureUserAgentTool.execute({"contact": "test@example.com"})

            # Verify reload_settings was called
            assert mock_reload.called

        # Search should now work
        mock_client = Mock()
        mock_client.search_cards.return_value = sample_search_result

        with patch(
            "scryfall_mcp.tools.search.is_user_agent_configured", return_value=True
        ), patch("scryfall_mcp.tools.search.get_client", return_value=mock_client):
            result = await CardSearchTool.execute({"query": "test"})
            # Should get search results, not config error
            assert len(result) >= 1

    @pytest.mark.asyncio
    async def test_multiple_configure_calls(self):
        """Test that configuration can be updated multiple times."""
        configs = [
            "user1@example.com",
            "https://github.com/user1/repo",
            "user2@example.com",
        ]

        for contact in configs:
            with patch(
                "scryfall_mcp.tools.configure.save_config"
            ) as mock_save, patch("scryfall_mcp.tools.configure.reload_settings"):
                mock_save.return_value = {
                    "user_agent": f"Scryfall-MCP-Server/0.1.0 ({contact})",
                    "contact": contact,
                }

                result = await ConfigureUserAgentTool.execute({"contact": contact})
                assert "✅" in result[0].text
                assert contact in result[0].text

    @pytest.mark.asyncio
    async def test_concurrent_configuration_attempts(self):
        """Test handling of concurrent configuration requests."""
        import asyncio

        async def configure_task(contact: str) -> list[TextContent]:
            with patch(
                "scryfall_mcp.tools.configure.save_config"
            ) as mock_save, patch("scryfall_mcp.tools.configure.reload_settings"):
                mock_save.return_value = {
                    "user_agent": f"Scryfall-MCP-Server/0.1.0 ({contact})",
                    "contact": contact,
                }
                return await ConfigureUserAgentTool.execute({"contact": contact})

        # Run multiple configurations concurrently
        tasks = [
            configure_task("user1@example.com"),
            configure_task("user2@example.com"),
            configure_task("user3@example.com"),
        ]

        results = await asyncio.gather(*tasks)

        # All should succeed
        assert len(results) == 3
        for result in results:
            assert len(result) == 1
            assert "✅" in result[0].text
