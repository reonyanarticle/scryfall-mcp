"""Main MCP server implementation for Scryfall integration.

This module implements the core MCP server that provides Magic: The Gathering
card information through the Model Context Protocol with Japanese language support.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

from fastmcp import Context, FastMCP
from mcp.types import EmbeddedResource, ImageContent, TextContent

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

from .api.client import close_client
from .i18n import detect_and_set_locale, get_locale_manager
from .resources import load_setup_guide
from .settings import get_settings
from .tools.search import AutocompleteTool, CardSearchTool

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,  # MCP uses stdout for communication
)
logger = logging.getLogger(__name__)


async def _handle_tool_error(
    ctx: Context,
    error: Exception,
    tool_name: str,
    language: str | None = None,
) -> list[TextContent]:
    """Handle tool execution errors with logging and localized messages.

    Parameters
    ----------
    ctx : Context
        FastMCP context for error reporting
    error : Exception
        The exception that occurred
    tool_name : str
        Name of the tool that errored
    language : str | None, optional
        Language code for error message

    Returns
    -------
    list[TextContent]
        Error message as MCP text content
    """
    await ctx.error(f"Error in {tool_name}: {error}")
    logger.exception(f"Error in {tool_name}")

    # Localized error messages
    if language == "ja":
        error_messages = {
            "search_cards": f"検索エラー: {error}",
            "autocomplete": f"オートコンプリートエラー: {error}",
        }
    else:
        error_messages = {
            "search_cards": f"Search error: {error}",
            "autocomplete": f"Autocomplete error: {error}",
        }

    error_msg = error_messages.get(tool_name, f"Error in {tool_name}: {error}")
    return [TextContent(type="text", text=error_msg)]


@asynccontextmanager
async def _create_lifespan(_app: FastMCP) -> AsyncIterator[None]:
    """Lifecycle manager for the MCP server.

    Handles startup and shutdown operations including:
    - Locale detection and initialization
    - Resource allocation
    - Cleanup on shutdown

    Parameters
    ----------
    _app : FastMCP
        FastMCP application instance (unused, required by FastMCP)

    Yields
    ------
    None
        Control is yielded during server runtime
    """
    # Startup
    detected_locale = detect_and_set_locale()
    logger.info("Detected and set locale: %s", detected_locale)

    locale_manager = get_locale_manager()
    supported_locales = locale_manager.get_supported_locale_codes()
    logger.info("Supported locales: %s", supported_locales)

    settings = get_settings()
    logger.info("Starting Scryfall MCP Server (fastmcp)")
    logger.info("Default locale: %s", settings.default_locale)
    logger.info("Cache enabled: %s", settings.cache_enabled)
    # Do not log full settings to avoid exposing credentials and PII

    try:
        yield
    finally:
        # Shutdown/cleanup
        await close_client()
        logger.info("Scryfall MCP Server stopped")


class ScryfallMCPServer:
    """Main Scryfall MCP Server implementation using fastmcp."""

    def __init__(self) -> None:
        """Initialize the MCP server."""
        self.settings = get_settings()
        self.app = FastMCP("scryfall-mcp", lifespan=_create_lifespan)
        self._setup_tools()
        self._setup_prompts()
        self._setup_resources()

    def _setup_prompts(self) -> None:
        """Set up MCP prompts using fastmcp decorators."""

        @self.app.prompt()
        def scryfall_setup() -> str:
            """Scryfall API setup guide for User-Agent configuration.

            Returns
            -------
            str
                Complete setup instructions for configuring SCRYFALL_MCP_USER_AGENT
            """
            return load_setup_guide(language="ja")

    def _setup_resources(self) -> None:
        """Set up MCP resources using fastmcp decorators."""

        @self.app.resource("scryfall://setup-guide")
        def get_setup_guide() -> str:
            """Scryfall API setup guide for User-Agent configuration.

            Returns
            -------
            str
                Complete setup instructions with configuration examples
            """
            return load_setup_guide(language="ja")

    def _setup_tools(self) -> None:
        """Set up MCP tools using fastmcp decorators."""

        # Search cards tool
        @self.app.tool()
        async def search_cards(
            ctx: Context,
            query: str,
            language: str | None = None,
            max_results: int = 10,
            format_filter: str | None = None,
        ) -> str | list[TextContent | ImageContent | EmbeddedResource]:
            """Search for Magic: The Gathering cards.

            Parameters
            ----------
            ctx : Context
                FastMCP context for progress reporting and logging
            query : str
                Search query (natural language or Scryfall syntax)
            language : str | None, optional
                Language code ("en", "ja")
            max_results : int, optional
                Maximum number of results (1-175, default: 10)
            format_filter : str | None, optional
                Format filter ("standard", "modern", etc.)

            Returns
            -------
            str | list[TextContent | ImageContent | EmbeddedResource]
                Setup guide (str) or list of MCP content items

            Notes
            -----
            Image data is not included to comply with MCP ImageContent spec.
            Image URLs are provided in Scryfall links within card details.
            """
            from .settings import is_user_agent_configured

            # Check User-Agent configuration before processing
            if not is_user_agent_configured():
                # Raise error with reference to setup guide resource
                error_message = (
                    "❌ **User-Agent が設定されていません**\n\n"
                    "Scryfall APIを使用するには、環境変数 SCRYFALL_MCP_USER_AGENT の設定が必要です。\n\n"
                    "📖 **詳細なセットアップガイド:**\n"
                    "MCP Resourcesから `scryfall://setup-guide` を参照してください。\n"
                    "または、以下の手順で設定してください：\n\n"
                    "1. Claude Desktop設定ファイルを開く\n"
                    "   - macOS/Linux: ~/Library/Application Support/Claude/claude_desktop_config.json\n"
                    "   - Windows: %APPDATA%\\Claude\\claude_desktop_config.json\n\n"
                    "2. SCRYFALL_MCP_USER_AGENT 環境変数を追加\n"
                    '   "SCRYFALL_MCP_USER_AGENT": "YourApp/1.0 (your-email@example.com)"\n\n'
                    "3. Claude Desktopを再起動\n\n"
                    "詳細: https://scryfall.com/docs/api"
                )
                await ctx.error(error_message)
                raise ValueError(error_message)

            await ctx.info(
                f"Search cards called: query='{query}', language={language}, max_results={max_results}"
            )

            arguments = {
                "query": query,
                "language": language,
                "max_results": max_results,
                "format_filter": format_filter,
            }

            await ctx.report_progress(0, 100, "Searching for cards...")
            # Return structured MCP content directly
            try:
                result = await CardSearchTool.execute(arguments)
                await ctx.report_progress(100, 100, "Search complete")
                return result
            except Exception as e:
                return await _handle_tool_error(ctx, e, "search_cards", language)

        # Autocomplete tool
        @self.app.tool()
        async def autocomplete_card_names(
            ctx: Context,
            query: str,
            language: str | None = None,
        ) -> list[TextContent]:
            """Get card name autocompletion suggestions.

            Parameters
            ----------
            ctx : Context
                FastMCP context for progress reporting and logging
            query : str
                Partial card name to complete
            language : str | None, optional
                Language code for completion

            Returns
            -------
            list[TextContent]
                List of MCP text content with suggestions
            """
            await ctx.info(f"Autocomplete called: query='{query}', language={language}")

            arguments = {
                "query": query,
                "language": language,
            }

            await ctx.report_progress(0, 100, "Getting autocomplete suggestions...")
            # Return structured MCP content directly
            try:
                result = await AutocompleteTool.execute(arguments)
                await ctx.report_progress(100, 100, "Autocomplete complete")
                return result
            except Exception as e:
                return await _handle_tool_error(ctx, e, "autocomplete", language)

    async def run(self) -> None:
        """Run the MCP server.

        The lifespan context manager handles startup and shutdown operations.
        """
        try:
            # Run the fastmcp server in stdio mode for MCP compatibility
            await self.app.run_stdio_async()
        except Exception:
            logger.exception("Server error")
            raise


async def main() -> None:
    """Main entry point."""
    server = ScryfallMCPServer()
    await server.run()


def sync_main() -> None:
    """Synchronous entry point for console scripts."""

    def handle_exception(
        loop: asyncio.AbstractEventLoop, context: dict[str, Any]
    ) -> None:
        """Custom exception handler to suppress harmless shutdown errors.

        Suppresses BrokenPipeError that occurs when the MCP client disconnects
        while the stdio transport is still flushing. This is a known issue in
        the MCP SDK's stdio.py that should be fixed upstream.

        Args:
            loop: The event loop
            context: Exception context dict
        """
        exception = context.get("exception")

        # Suppress BrokenPipeError during shutdown (MCP SDK bug)
        if isinstance(exception, BrokenPipeError):
            logger.debug(
                "Suppressed BrokenPipeError during shutdown (client disconnected)"
            )
            return

        # Let default handler handle other exceptions
        loop.default_exception_handler(context)

    try:
        # Set exception handler before running
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.set_exception_handler(handle_exception)

        try:
            loop.run_until_complete(main())
        finally:
            loop.close()
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception:
        logger.exception("Fatal error")
        sys.exit(1)


if __name__ == "__main__":
    sync_main()
