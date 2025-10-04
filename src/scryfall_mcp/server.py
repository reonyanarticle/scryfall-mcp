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
from .settings import get_settings
from .tools.search import AutocompleteTool, CardSearchTool

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,  # MCP uses stdout for communication
)
logger = logging.getLogger(__name__)


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
        ) -> list[TextContent | ImageContent | EmbeddedResource]:
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
            list[TextContent | ImageContent | EmbeddedResource]
                List of MCP content items (text, embedded resources)

            Notes
            -----
            Image data is not included to comply with MCP ImageContent spec.
            Image URLs are provided in Scryfall links within card details.
            """
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
                await ctx.error(f"Error in search_cards: {e}")
                logger.exception("Error in search_cards")
                error_msg = (
                    f"検索エラー: {e}" if language == "ja" else f"Search error: {e}"
                )
                return [TextContent(type="text", text=error_msg)]

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
                await ctx.error(f"Error in autocomplete: {e}")
                logger.exception("Error in autocomplete")
                error_msg = (
                    f"オートコンプリートエラー: {e}"
                    if language == "ja"
                    else f"Autocomplete error: {e}"
                )
                return [TextContent(type="text", text=error_msg)]

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
