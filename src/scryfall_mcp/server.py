"""Main MCP server implementation for Scryfall integration.

This module implements the core MCP server that provides Magic: The Gathering
card information through the Model Context Protocol with Japanese language support.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

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
async def _create_lifespan() -> AsyncIterator[None]:
    """Lifecycle manager for the MCP server.

    Handles startup and shutdown operations including:
    - Locale detection and initialization
    - Resource allocation
    - Cleanup on shutdown
    """
    # Startup
    detected_locale = detect_and_set_locale()
    logger.info("Detected and set locale: %s", detected_locale)

    locale_manager = get_locale_manager()
    supported_locales = locale_manager.get_supported_locale_codes()
    logger.info("Supported locales: %s", supported_locales)

    settings = get_settings()
    logger.info("Starting Scryfall MCP Server (fastmcp)")
    logger.info("Settings: %s", settings.model_dump())

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
            max_results: int = 20,
            include_images: bool = True,
            format_filter: str | None = None,
        ) -> list[TextContent | ImageContent | EmbeddedResource]:
            """Search for Magic: The Gathering cards.

            Args:
                ctx: FastMCP context for progress reporting and logging
                query: Search query (natural language or Scryfall syntax)
                language: Language code ("en", "ja")
                max_results: Maximum number of results (1-175)
                include_images: Whether to include card images
                format_filter: Format filter ("standard", "modern", etc.)

            Returns:
                List of MCP content items (text, images, embedded resources)
            """
            ctx.info(
                f"Search cards called: query='{query}', language={language}, max_results={max_results}"
            )

            arguments = {
                "query": query,
                "language": language,
                "max_results": max_results,
                "include_images": include_images,
                "format_filter": format_filter,
            }

            try:
                ctx.report_progress(0, 100, "Searching for cards...")
                # Return structured MCP content directly
                result = await CardSearchTool.execute(arguments)
                ctx.report_progress(100, 100, "Search complete")
                return result
            except Exception as e:
                ctx.error(f"Error in search_cards: {e}")
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

            Args:
                ctx: FastMCP context for progress reporting and logging
                query: Partial card name to complete
                language: Language code for completion

            Returns:
                List of MCP text content with suggestions
            """
            ctx.info(f"Autocomplete called: query='{query}', language={language}")

            arguments = {
                "query": query,
                "language": language,
            }

            try:
                ctx.report_progress(0, 100, "Getting autocomplete suggestions...")
                # Return structured MCP content directly
                result = await AutocompleteTool.execute(arguments)
                ctx.report_progress(100, 100, "Autocomplete complete")
                return result
            except Exception as e:
                ctx.error(f"Error in autocomplete: {e}")
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
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception:
        logger.exception("Fatal error")
        sys.exit(1)


if __name__ == "__main__":
    sync_main()
