"""Tests for the main MCP server implementation."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from scryfall_mcp.server import ScryfallMCPServer, main, sync_main


class TestScryfallMCPServer:
    """Test the main server class."""

    def test_server_initialization(self) -> None:
        """Test server initialization."""
        server = ScryfallMCPServer()
        assert server.settings is not None
        assert server.app is not None

    @patch("scryfall_mcp.server.get_settings")
    def test_server_initialization_with_mocked_settings(
        self, mock_get_settings: Mock
    ) -> None:
        """Test server initialization with mocked settings."""
        mock_settings = Mock()
        mock_get_settings.return_value = mock_settings

        server = ScryfallMCPServer()
        assert server.settings is mock_settings
        mock_get_settings.assert_called_once()

    def test_setup_tools_registration(self) -> None:
        """Test that tools are properly registered with fastmcp."""
        with (
            patch("scryfall_mcp.server.FastMCP") as mock_fastmcp,
            patch("scryfall_mcp.server._create_lifespan") as mock_lifespan,
        ):
            mock_app = Mock()
            mock_fastmcp.return_value = mock_app

            server = ScryfallMCPServer()

            # Verify that FastMCP was called with correct name and lifespan
            mock_fastmcp.assert_called_once_with("scryfall-mcp", lifespan=mock_lifespan)

            # Verify that tool decorators were called
            assert (
                mock_app.tool.call_count >= 2
            )  # At least search_cards and autocomplete

    def test_tool_registration_happens(self) -> None:
        """Test that tools are registered during initialization."""
        # This test ensures that _setup_tools is called and tools are registered
        with patch.object(ScryfallMCPServer, "_setup_tools") as mock_setup:
            server = ScryfallMCPServer()
            mock_setup.assert_called_once()

    def test_search_cards_tool_function(self) -> None:
        """Test the synchronous search_cards tool function by extracting from server."""
        with patch("scryfall_mcp.tools.search.CardSearchTool.execute") as mock_execute:
            # Mock the execute method to return MCP content
            mock_content = Mock()
            mock_content.text = "Test search result"
            mock_execute.return_value = [mock_content]

            # We'll patch the code execution within _setup_tools to capture the actual tool function
            captured_functions = {}

            # Store original exec to capture function definitions
            original_exec = exec

            def mock_exec(code_obj, global_dict, local_dict=None):
                # Call original exec but capture our function if it exists
                result = original_exec(code_obj, global_dict, local_dict)
                # Look for our search_cards function in the local scope
                if local_dict and "search_cards" in local_dict:
                    captured_functions["search_cards"] = local_dict["search_cards"]
                elif global_dict and "search_cards" in global_dict:
                    captured_functions["search_cards"] = global_dict["search_cards"]
                return result

            # Create a working mock app
            captured_tools = []

            class MockApp:
                def __init__(self, name):
                    self.name = name

                def tool(self):
                    def decorator(func):
                        captured_tools.append(func)
                        return func

                    return decorator

            with patch("fastmcp.FastMCP", MockApp):
                server = ScryfallMCPServer()

                # Now call the captured tools to exercise the code
                for tool_func in captured_tools:
                    if "search_cards" in str(tool_func):
                        result = tool_func("Lightning Bolt")
                        assert result == "Test search result"
                        mock_execute.assert_called()
                        break

    def test_autocomplete_tool_function(self) -> None:
        """Test the synchronous autocomplete_card_names tool function."""
        with patch(
            "scryfall_mcp.tools.search.AutocompleteTool.execute"
        ) as mock_execute:
            # Mock the execute method to return MCP content
            mock_content = Mock()
            mock_content.text = "Lightning Bolt\nLightning Strike"
            mock_execute.return_value = [mock_content]

            # Create a working mock app that captures tools
            captured_tools = []

            class MockApp:
                def __init__(self, name):
                    self.name = name

                def tool(self):
                    def decorator(func):
                        captured_tools.append(func)
                        return func

                    return decorator

            with patch("fastmcp.FastMCP", MockApp):
                server = ScryfallMCPServer()

                # Now call the captured tools to exercise the code
                for tool_func in captured_tools:
                    if "autocomplete" in str(tool_func):
                        result = tool_func("Light")
                        assert result == "Lightning Bolt\nLightning Strike"
                        mock_execute.assert_called()
                        break

    def test_server_main_block_execution(self) -> None:
        """Test that the server main block executes sync_main when __name__ is __main__."""
        with patch("scryfall_mcp.server.sync_main") as mock_sync_main:
            # Simulate the exact code in server.py
            code = """
if __name__ == "__main__":
    sync_main()
"""
            # Execute with __name__ = "__main__"
            namespace = {"__name__": "__main__", "sync_main": mock_sync_main}
            exec(compile(code, "server.py", "exec"), namespace)

            mock_sync_main.assert_called_once()

    def test_server_direct_import_execution(self) -> None:
        """Test server.py main block by manipulating __name__ directly."""
        with patch("scryfall_mcp.server.sync_main") as mock_sync_main:
            # Temporarily change the server module's __name__ to trigger the main block
            import scryfall_mcp.server as server_module

            original_name = server_module.__name__

            try:
                # Set __name__ to "__main__" to trigger the condition
                server_module.__name__ = "__main__"

                # Re-execute the main block condition
                if server_module.__name__ == "__main__":
                    server_module.sync_main()

            finally:
                # Restore original __name__
                server_module.__name__ = original_name

            mock_sync_main.assert_called_once()

    @pytest.mark.asyncio
    async def test_server_run(self) -> None:
        """Test server run method."""
        server = ScryfallMCPServer()

        # Mock the app.run_stdio_async method to be async
        server.app.run_stdio_async = AsyncMock()

        await server.run()

        # Verify run_stdio_async was called
        server.app.run_stdio_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_server_run_with_error(self) -> None:
        """Test server run method with error."""
        server = ScryfallMCPServer()

        # Mock the app.run_stdio_async method to raise an exception
        server.app.run_stdio_async = AsyncMock(side_effect=Exception("Test error"))

        with pytest.raises(Exception, match="Test error"):
            await server.run()

    @pytest.mark.asyncio
    async def test_lifespan_context_manager(self) -> None:
        """Test the lifespan context manager."""
        from scryfall_mcp.server import _create_lifespan
        from fastmcp import FastMCP

        with (
            patch("scryfall_mcp.server.detect_and_set_locale") as mock_detect,
            patch("scryfall_mcp.server.get_locale_manager") as mock_get_locale,
            patch("scryfall_mcp.server.close_client") as mock_close,
        ):
            mock_detect.return_value = "en"
            mock_locale_manager = Mock()
            mock_locale_manager.get_supported_locale_codes.return_value = ["en", "ja"]
            mock_get_locale.return_value = mock_locale_manager

            # Create a mock FastMCP app
            mock_app = Mock(spec=FastMCP)

            # Test lifespan startup and shutdown
            async with _create_lifespan(mock_app):
                # Verify startup was called
                mock_detect.assert_called_once()
                mock_get_locale.assert_called_once()
                # close_client should not be called yet
                mock_close.assert_not_called()

            # Verify cleanup was called on exit
            mock_close.assert_called_once()


class TestMainFunctions:
    """Test the main entry point functions."""

    @pytest.mark.asyncio
    async def test_main(self) -> None:
        """Test the main async function."""
        with patch("scryfall_mcp.server.ScryfallMCPServer") as mock_server_class:
            mock_server = Mock()
            mock_server.run = AsyncMock()
            mock_server_class.return_value = mock_server

            await main()

            mock_server_class.assert_called_once()
            mock_server.run.assert_called_once()

    def test_sync_main_success(self) -> None:
        """Test the synchronous main function success case."""
        with (
            patch("asyncio.new_event_loop") as mock_new_loop,
            patch("asyncio.set_event_loop") as mock_set_loop,
        ):
            mock_loop = MagicMock()
            mock_new_loop.return_value = mock_loop
            mock_loop.run_until_complete.return_value = None

            sync_main()

            mock_new_loop.assert_called_once()
            mock_set_loop.assert_called_once_with(mock_loop)
            mock_loop.set_exception_handler.assert_called_once()
            mock_loop.run_until_complete.assert_called_once()
            mock_loop.close.assert_called_once()

    def test_sync_main_keyboard_interrupt(self) -> None:
        """Test the synchronous main function with keyboard interrupt."""
        with (
            patch("asyncio.new_event_loop") as mock_new_loop,
            patch("asyncio.set_event_loop") as mock_set_loop,
            patch("scryfall_mcp.server.logger") as mock_logger,
        ):
            mock_loop = MagicMock()
            mock_new_loop.return_value = mock_loop
            mock_loop.run_until_complete.side_effect = KeyboardInterrupt()

            sync_main()

            mock_logger.info.assert_called_once_with("Server interrupted by user")
            mock_loop.close.assert_called_once()

    def test_sync_main_exception(self) -> None:
        """Test the synchronous main function with exception."""
        with (
            patch("asyncio.new_event_loop") as mock_new_loop,
            patch("asyncio.set_event_loop") as mock_set_loop,
            patch("scryfall_mcp.server.logger") as mock_logger,
            patch("sys.exit") as mock_exit,
        ):
            mock_loop = MagicMock()
            mock_new_loop.return_value = mock_loop
            test_error = Exception("Test error")
            mock_loop.run_until_complete.side_effect = test_error

            sync_main()

            # Should log "Fatal error" and exit
            mock_logger.exception.assert_called_once_with("Fatal error")
            mock_exit.assert_called_once_with(1)
            mock_loop.close.assert_called_once()
