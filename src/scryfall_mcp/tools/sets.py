"""Set information tools for the Scryfall MCP Server.

This module provides MCP tools for retrieving Magic: The Gathering set information.
"""

from __future__ import annotations

import logging
from typing import Any

from mcp import Tool
from mcp.types import TextContent

from ..api.client import get_client
from ..api.sets import get_latest_expansion_code

logger = logging.getLogger(__name__)


class GetLatestExpansionSetTool:
    """Tool for getting the latest expansion set information."""

    @staticmethod
    def get_tool_definition() -> Tool:
        """Get the MCP tool definition."""
        return Tool(
            name="get_latest_expansion_set",
            description=(
                "Get information about the latest Magic: The Gathering expansion set. "
                "Returns the set name, code, release date, and card count. "
                "Use this when the user asks '最新のエクスパンション' or 'latest expansion'."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        )

    @staticmethod
    async def execute(_arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the latest expansion set retrieval.

        Parameters
        ----------
        arguments : dict
            Tool arguments (empty for this tool)

        Returns
        -------
        list[TextContent]
            List containing set information
        """
        try:
            # Get client and fetch latest expansion
            client = await get_client()
            latest_set = await client.get_latest_expansion_set()

            if not latest_set:
                return [
                    TextContent(
                        type="text",
                        text=(
                            "❌ **最新のエクスパンションセットが見つかりませんでした**\n\n"
                            "Scryfall APIから最新のエクスパンションセット情報を取得できませんでした。"
                        ),
                    )
                ]

            # Get the set code for search hint
            set_code = await get_latest_expansion_code(client)

            # Format response
            response_text = (
                f"🎴 **最新のエクスパンションセット**\n\n"
                f"**名前**: {latest_set.name}\n"
                f"**コード**: `{latest_set.code.upper()}`\n"
                f"**リリース日**: {latest_set.released_at}\n"
                f"**カード数**: {latest_set.card_count}枚\n"
                f"**タイプ**: {latest_set.set_type}\n\n"
                f"💡 **このセットのカードを検索するには**:\n"
                f"`search_cards`ツールで「最新のエクスパンション」または「s:{set_code}」で検索してください。"
            )

            return [TextContent(type="text", text=response_text)]

        except Exception as e:
            logger.error(f"Error fetching latest expansion set: {e}", exc_info=True)
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
