"""Main MCP server implementation for Scryfall integration.

This module implements the core MCP server that provides Magic: The Gathering
card information through the Model Context Protocol with Japanese language support.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any, cast

from fastmcp import Context, FastMCP
from mcp.types import EmbeddedResource, ImageContent, TextContent

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

from .api.client import close_client
from .i18n import detect_and_set_locale, get_locale_manager
from .resources import load_setup_guide
from .settings import get_settings
from .tools.search import AutocompleteTool, CardSearchTool
from .tools.sets import GetLatestExpansionSetTool

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
) -> list[TextContent | ImageContent | EmbeddedResource]:
    """Handle tool execution errors with logging and localized messages.

    Parameters
    ----------
    ctx : Context
        FastMCP context for error reporting
    error : Exception
        The exception that occurred
    tool_name : str
        Name of the tool that errored
    language : str | None, optional (default: None)
        Language code for error message

    Returns
    -------
    list[TextContent | ImageContent | EmbeddedResource]
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
        
        # Add authentication middleware if enabled
        # Note: FastMCP internally uses Starlette, access via fastmcp.app._starlette_app
        if self.settings.email_auth_enabled:
            from scryfall_mcp.auth import EmailAuthMiddleware
            # FastMCP uses Starlette internally, middleware needs to be added there
            if hasattr(self.app, '_starlette_app'):
                self.app._starlette_app.add_middleware(EmailAuthMiddleware, settings=self.settings)
        elif self.settings.oauth_enabled:
            from scryfall_mcp.auth import JWTValidationMiddleware
            if hasattr(self.app, '_starlette_app'):
                self.app._starlette_app.add_middleware(JWTValidationMiddleware, settings=self.settings)
        
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
            use_annotations: bool = True,
            include_keywords: bool = True,
            include_artist: bool = True,
            include_mana_production: bool = True,
            include_legalities: bool = False,
        ) -> str | list[TextContent | ImageContent | EmbeddedResource]:
            """Search for Magic: The Gathering cards.

            Parameters
            ----------
            ctx : Context
                FastMCP context for progress reporting and logging
            query : str
                Search query (natural language or Scryfall syntax)
            language : str | None, optional (default: None)
                Language code ("en", "ja")
            max_results : int, optional (default: 10)
                Maximum number of results (1-175, default: 10)
            format_filter : str | None, optional (default: None)
                Format filter ("standard", "modern", etc.)
            use_annotations : bool, optional (default: True)
                Include MCP annotations for text and metadata output
            include_keywords : bool, optional (default: True)
                Include keyword abilities in card summaries
            include_artist : bool, optional (default: True)
                Include artist attribution in card summaries
            include_mana_production : bool, optional (default: True)
                Include mana production details for land cards
            include_legalities : bool, optional (default: False)
                Include compact format legalities in embedded resources

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
                "use_annotations": use_annotations,
                "include_keywords": include_keywords,
                "include_artist": include_artist,
                "include_mana_production": include_mana_production,
                "include_legalities": include_legalities,
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
        ) -> list[TextContent | ImageContent | EmbeddedResource]:
            """Get card name autocompletion suggestions.

            Parameters
            ----------
            ctx : Context
                FastMCP context for progress reporting and logging
            query : str
                Partial card name to complete
            language : str | None, optional (default: None)
                Language code for completion

            Returns
            -------
            list[TextContent | ImageContent | EmbeddedResource]
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
                return cast(
                    "list[TextContent | ImageContent | EmbeddedResource]", result
                )
            except Exception as e:
                return await _handle_tool_error(ctx, e, "autocomplete", language)

        # Latest expansion set info tool
        @self.app.tool()
        async def get_latest_expansion_set(
            ctx: Context,
        ) -> list[TextContent]:
            """Get information about the latest Magic: The Gathering expansion set.

            Parameters
            ----------
            ctx : Context
                FastMCP context for progress reporting and logging

            Returns
            -------
            list[TextContent]
                Latest expansion set information
            """
            await ctx.info("Getting latest expansion set information")

            await ctx.report_progress(0, 100, "Fetching latest expansion set...")
            try:
                result = await GetLatestExpansionSetTool.execute({})
                await ctx.report_progress(100, 100, "Latest expansion set retrieved")
                return result
            except Exception as e:
                await ctx.error(f"Error getting latest expansion set: {e}")
                return [
                    TextContent(
                        type="text",
                        text=(
                            f"❌ **エラーが発生しました**\n\n"
                            f"最新のエクスパンションセット情報の取得中にエラーが発生しました。\n\n"
                            f"**エラー**: {e}"
                        ),
                    )
                ]

    async def run(self, transport_mode: str | None = None) -> None:
        """Run the MCP server with specified transport.

        Parameters
        ----------
        transport_mode : str | None, optional
            Transport mode override. If None, uses settings value.
            Valid values: "stdio", "http", "streamable_http"

        Raises
        ------
        ValueError
            If unsupported transport mode is specified
        """
        mode = transport_mode or self.settings.transport_mode

        try:
            if mode == "stdio":
                # Run in stdio mode for local MCP compatibility
                await self.app.run_stdio_async()
            elif mode in ("http", "streamable_http"):
                # Run in HTTP mode for Remote MCP
                await self.app.run(
                    transport="http",
                    host=self.settings.http_host,
                    port=self.settings.http_port,
                    path=self.settings.http_path,
                )
            else:
                raise ValueError(f"Unsupported transport mode: {mode}")
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

        Parameters
        ----------
        loop : asyncio.AbstractEventLoop
            The event loop
        context : dict[str, Any]
            Exception context dict
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
