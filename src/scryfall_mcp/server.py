"""Main MCP server implementation for Scryfall integration.

This module implements the core MCP server that provides Magic: The Gathering
card information through the Model Context Protocol with Japanese language support.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from typing import Any, Optional, Sequence

import mcp.server.stdio
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from .api.client import close_client
from .i18n import detect_and_set_locale, get_locale_manager
from .settings import get_settings
from .tools.search import SEARCH_TOOLS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr  # MCP uses stdout for communication
)
logger = logging.getLogger(__name__)


class ScryfallMCPServer:
    """Main Scryfall MCP Server implementation."""

    def __init__(self) -> None:
        """Initialize the MCP server."""
        self.settings = get_settings()
        self.server = Server("scryfall-mcp")
        self._setup_handlers()

    def _setup_handlers(self) -> None:
        """Set up MCP server handlers."""

        @self.server.list_tools()
        async def handle_list_tools() -> list[types.Tool]:
            """List available tools."""
            tools = []
            for tool_class in SEARCH_TOOLS:
                tools.append(tool_class.get_tool_definition())

            logger.info(f"Listed {len(tools)} tools")
            return tools

        @self.server.call_tool()
        async def handle_call_tool(
            name: str, arguments: Optional[dict[str, Any]]
        ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
            """Handle tool execution."""
            logger.info(f"Tool called: {name} with args: {arguments}")

            if arguments is None:
                arguments = {}

            # Find and execute the appropriate tool
            for tool_class in SEARCH_TOOLS:
                tool_def = tool_class.get_tool_definition()
                if tool_def.name == name:
                    try:
                        return await tool_class.execute(arguments)
                    except Exception as e:
                        logger.error(f"Error executing tool {name}: {e}", exc_info=True)
                        error_msg = f"Tool execution failed: {e}"
                        return [types.TextContent(type="text", text=error_msg)]

            # Tool not found
            error_msg = f"Unknown tool: {name}"
            logger.error(error_msg)
            return [types.TextContent(type="text", text=error_msg)]

        @self.server.list_resources()
        async def handle_list_resources() -> list[types.Resource]:
            """List available resources."""
            # For now, we don't provide any static resources
            # Could be extended to provide card databases, set lists, etc.
            return []

        @self.server.read_resource()
        async def handle_read_resource(uri: types.AnyUrl) -> str:
            """Read a resource."""
            # Not implemented yet
            raise ValueError(f"Resource not found: {uri}")

        @self.server.list_prompts()
        async def handle_list_prompts() -> list[types.Prompt]:
            """List available prompts."""
            # Could provide predefined search prompts
            return []

        @self.server.get_prompt()
        async def handle_get_prompt(
            name: str, arguments: Optional[dict[str, str]]
        ) -> types.GetPromptResult:
            """Get a prompt."""
            # Not implemented yet
            raise ValueError(f"Prompt not found: {name}")

    async def run(self) -> None:
        """Run the MCP server."""
        try:
            # Initialize locale
            detected_locale = detect_and_set_locale()
            logger.info(f"Detected and set locale: {detected_locale}")

            # Log server startup
            logger.info("Starting Scryfall MCP Server")
            logger.info(f"Settings: {self.settings.dict()}")

            # Get locale manager info
            locale_manager = get_locale_manager()
            supported_locales = locale_manager.get_supported_locale_codes()
            logger.info(f"Supported locales: {supported_locales}")

            # Run the server
            async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
                await self.server.run(
                    read_stream,
                    write_stream,
                    InitializationOptions(
                        server_name="scryfall-mcp",
                        server_version="0.1.0",
                        capabilities=self.server.get_capabilities(
                            notification_options=NotificationOptions(),
                            experimental_capabilities={},
                        ),
                    ),
                )
        except Exception as e:
            logger.error(f"Server error: {e}", exc_info=True)
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
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    sync_main()