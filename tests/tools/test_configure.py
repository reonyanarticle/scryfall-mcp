"""Tests for configuration tools."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from mcp.types import TextContent

from scryfall_mcp.tools.configure import ConfigureUserAgentTool


class TestConfigureUserAgentTool:
    """Tests for ConfigureUserAgentTool."""

    def test_get_tool_definition(self):
        """Test tool definition structure."""
        tool_def = ConfigureUserAgentTool.get_tool_definition()

        assert tool_def.name == "configure_user_agent"
        assert "contact information" in tool_def.description.lower()
        assert tool_def.inputSchema is not None

    @pytest.mark.asyncio
    async def test_execute_with_valid_email(self, tmp_path: Path):
        """Test configuration with valid email."""
        # Mock config directory
        with patch("scryfall_mcp.tools.configure.save_config") as mock_save, patch(
            "scryfall_mcp.tools.configure.reload_settings"
        ) as mock_reload:
            # Setup mock
            mock_save.return_value = {
                "user_agent": "Scryfall-MCP-Server/0.1.0 (test@example.com)",
                "contact": "test@example.com",
            }

            # Execute
            arguments = {"contact": "test@example.com"}
            result = await ConfigureUserAgentTool.execute(arguments)

            # Verify
            assert len(result) == 1
            assert isinstance(result[0], TextContent)
            assert "✅" in result[0].text
            assert "test@example.com" in result[0].text
            assert mock_save.called
            assert mock_reload.called

    @pytest.mark.asyncio
    async def test_execute_with_valid_https_url(self, tmp_path: Path):
        """Test configuration with valid HTTPS URL."""
        with patch("scryfall_mcp.tools.configure.save_config") as mock_save, patch(
            "scryfall_mcp.tools.configure.reload_settings"
        ) as mock_reload:
            # Setup mock
            mock_save.return_value = {
                "user_agent": "Scryfall-MCP-Server/0.1.0 (https://github.com/user/repo)",
                "contact": "https://github.com/user/repo",
            }

            # Execute
            arguments = {"contact": "https://github.com/user/repo"}
            result = await ConfigureUserAgentTool.execute(arguments)

            # Verify
            assert len(result) == 1
            assert isinstance(result[0], TextContent)
            assert "✅" in result[0].text
            assert "https://github.com/user/repo" in result[0].text

    @pytest.mark.asyncio
    async def test_execute_with_invalid_email(self):
        """Test configuration with invalid email."""
        arguments = {"contact": "invalid-email"}
        result = await ConfigureUserAgentTool.execute(arguments)

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "❌" in result[0].text
        assert "Invalid Contact Information" in result[0].text

    @pytest.mark.asyncio
    async def test_execute_with_http_url(self):
        """Test configuration with HTTP URL (should fail)."""
        arguments = {"contact": "http://example.com"}
        result = await ConfigureUserAgentTool.execute(arguments)

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "❌" in result[0].text
        assert "https://" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_execute_with_empty_contact(self):
        """Test configuration with empty contact."""
        arguments = {"contact": ""}
        result = await ConfigureUserAgentTool.execute(arguments)

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "❌" in result[0].text

    @pytest.mark.asyncio
    async def test_execute_with_whitespace_contact(self):
        """Test configuration with whitespace-only contact."""
        arguments = {"contact": "   "}
        result = await ConfigureUserAgentTool.execute(arguments)

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "❌" in result[0].text

    @pytest.mark.asyncio
    async def test_execute_save_error(self):
        """Test handling of save errors."""
        with patch(
            "scryfall_mcp.tools.configure.save_config",
            side_effect=IOError("Disk full"),
        ):
            arguments = {"contact": "test@example.com"}
            result = await ConfigureUserAgentTool.execute(arguments)

            assert len(result) == 1
            assert isinstance(result[0], TextContent)
            assert "❌" in result[0].text
            assert "error" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_execute_validates_before_saving(self):
        """Test that validation happens before save_config is called."""
        with patch("scryfall_mcp.tools.configure.save_config") as mock_save:
            arguments = {"contact": "invalid"}
            result = await ConfigureUserAgentTool.execute(arguments)

            # save_config should not be called for invalid contact
            assert not mock_save.called
            assert "❌" in result[0].text
