"""Main MCP server implementation for Scryfall integration.

This module implements the core MCP server that provides Magic: The Gathering
card information through the Model Context Protocol with Japanese language support.
"""

from __future__ import annotations

import asyncio
import logging
import sys

from fastmcp import FastMCP

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


class ScryfallMCPServer:
    """Main Scryfall MCP Server implementation using fastmcp."""

    def __init__(self) -> None:
        """Initialize the MCP server."""
        self.settings = get_settings()
        self.app = FastMCP("scryfall-mcp")
        self._setup_tools()

    def _setup_tools(self) -> None:
        """Set up MCP tools using fastmcp decorators."""
        # Search cards tool
        @self.app.tool()
        async def search_cards(
            query: str,
            language: str | None = None,
            max_results: int = 20,
            include_images: bool = True,
            format_filter: str | None = None,
        ) -> str:
            """Search for Magic: The Gathering cards.

            Args:
                query: Search query (natural language or Scryfall syntax)
                language: Language code ("en", "ja")
                max_results: Maximum number of results (1-100)
                include_images: Whether to include card images
                format_filter: Format filter ("standard", "modern", etc.)

            Returns:
                Formatted search results with card information
            """
            return await self._search_cards_async(
                query, language, max_results, include_images, format_filter,
            )

        # Autocomplete tool
        @self.app.tool()
        async def autocomplete_card_names(
            query: str,
            language: str | None = None,
        ) -> str:
            """Get card name autocompletion suggestions.

            Args:
                query: Partial card name to complete
                language: Language code for completion

            Returns:
                List of suggested card names
            """
            logger.info(
                "autocomplete_card_names called with query='%s', language='%s'",
                query, language,
            )
            return await self._autocomplete_async(query, language)

    async def _search_cards_async(
        self,
        query: str,
        language: str | None = None,
        max_results: int = 20,
        include_images: bool = True,
        format_filter: str | None = None,
    ) -> str:
        """Async implementation of card search."""
        arguments = {
            "query": query,
            "language": language,
            "max_results": max_results,
            "include_images": include_images,
            "format_filter": format_filter,
        }

        try:
            results = await CardSearchTool.execute(arguments)
            # Convert MCP content to string for fastmcp
            content_parts = []
            for result in results:
                if hasattr(result, "text"):
                    content_parts.append(result.text)
                elif hasattr(result, "data") and hasattr(result, "mimeType"):
                    content_parts.append(f"[Image: {result.mimeType}]")
            return "\n\n".join(content_parts)
        except Exception as e:
            logger.exception("Error in search_cards")
            return f"Error: {e}"

    async def _autocomplete_async(
        self,
        query: str,
        language: str | None = None,
    ) -> str:
        """Async implementation of autocomplete."""
        arguments = {
            "query": query,
            "language": language,
        }

        try:
            results = await AutocompleteTool.execute(arguments)
            # Convert MCP content to string for fastmcp
            content_parts = []
            for result in results:
                if hasattr(result, "text"):
                    content_parts.append(result.text)
            return "\n\n".join(content_parts)
        except Exception as e:
            logger.exception("Error in autocomplete")
            return f"Error: {e}"

    async def run(self) -> None:
        """Run the MCP server."""
        try:
            # Initialize locale
            detected_locale = detect_and_set_locale()
            logger.info("Detected and set locale: %s", detected_locale)

            # Log server startup
            logger.info("Starting Scryfall MCP Server (fastmcp)")
            logger.info("Settings: %s", self.settings.model_dump())

            # Get locale manager info
            locale_manager = get_locale_manager()
            supported_locales = locale_manager.get_supported_locale_codes()
            logger.info("Supported locales: %s", supported_locales)

            # Run the fastmcp server in stdio mode for MCP compatibility
            await self.app.run_stdio_async()
        except Exception:
            logger.exception("Server error")
            raise
        finally:
            # Cleanup
            await close_client()
            logger.info("Scryfall MCP Server stopped")


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
