"""Configuration tool for the Scryfall MCP Server.

This module provides MCP tools for configuring the server,
particularly User-Agent contact information.
"""

from __future__ import annotations

import logging
from typing import Any

from mcp import Tool
from mcp.types import TextContent
from pydantic import BaseModel, Field

from ..setup_wizard import save_config, validate_contact_info
from ..settings import reload_settings

logger = logging.getLogger(__name__)


class ConfigureUserAgentRequest(BaseModel):
    """Request model for User-Agent configuration."""

    contact: str = Field(
        ...,
        description="Contact information (email or HTTPS URL)",
        examples=["user@example.com", "https://github.com/username/repo"],
    )


class ConfigureUserAgentTool:
    """Tool for configuring User-Agent contact information."""

    @staticmethod
    def get_tool_definition() -> Tool:
        """Get the MCP tool definition."""
        return Tool(
            name="configure_user_agent",
            description="Configure your contact information for Scryfall API compliance. Required before using search_cards. Provide your email address or repository URL.",
            inputSchema=ConfigureUserAgentRequest.model_json_schema(),
        )

    @staticmethod
    async def execute(arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the configuration.

        Parameters
        ----------
        arguments : dict
            Tool arguments matching ConfigureUserAgentRequest

        Returns
        -------
        list[TextContent]
            Configuration result message
        """
        try:
            # Validate arguments
            request = ConfigureUserAgentRequest(**arguments)

            # Validate contact info
            if not validate_contact_info(request.contact):
                error_msg = (
                    "❌ **Invalid Contact Information**\n\n"
                    "Please provide valid contact information:\n"
                    "• Email address (e.g., `yourname@example.com`)\n"
                    "• GitHub repository URL (e.g., `https://github.com/username/repo`)\n"
                    "• Other HTTPS URL where you can be reached\n\n"
                    "**Note**: URLs must start with `https://` for security compliance."
                )
                return [TextContent(type="text", text=error_msg)]

            # Save configuration
            config = save_config(request.contact)
            user_agent = config.get("user_agent", "")

            # Reload settings to apply new User-Agent
            reload_settings()

            success_msg = (
                "✅ **User-Agent Configured Successfully**\n\n"
                f"**User-Agent**: `{user_agent}`\n"
                f"**Contact**: `{request.contact}`\n\n"
                "You can now use the `search_cards` tool to search for Magic: The Gathering cards.\n\n"
                "**Configuration saved to**:\n"
                "• macOS: `~/Library/Application Support/scryfall-mcp/config.json`\n"
                "• Linux: `~/.config/scryfall-mcp/config.json`\n"
                "• Windows: `%APPDATA%\\Local\\scryfall-mcp\\config.json`"
            )

            logger.info(f"User-Agent configured via MCP tool: {user_agent}")
            return [TextContent(type="text", text=success_msg)]

        except ValueError as e:
            logger.error(f"Validation error in configure_user_agent: {e}")
            error_msg = f"❌ **Configuration Error**\n\n{str(e)}"
            return [TextContent(type="text", text=error_msg)]

        except Exception as e:
            logger.error(f"Error in configure_user_agent: {e}", exc_info=True)
            error_msg = (
                "❌ **Configuration Error**\n\n"
                f"An unexpected error occurred: {str(e)}\n\n"
                "Please try again or check the server logs for details."
            )
            return [TextContent(type="text", text=error_msg)]


# Export tool
CONFIGURE_TOOLS = [ConfigureUserAgentTool]
