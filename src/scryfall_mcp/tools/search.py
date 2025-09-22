"""Search tools for the Scryfall MCP Server.

This module provides MCP tools for searching Magic: The Gathering cards
using natural language queries with Japanese support.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from mcp import Tool
from mcp.types import TextContent, ImageContent, EmbeddedResource
from pydantic import BaseModel, Field

from ..api.client import get_client, ScryfallAPIError
from ..api.models import SearchResult, Card
from ..search.processor import SearchProcessor
from ..i18n import get_current_mapping, set_current_locale

logger = logging.getLogger(__name__)


class SearchCardsRequest(BaseModel):
    """Request model for card search."""

    query: str = Field(description="Natural language search query (supports Japanese)")
    language: Optional[str] = Field(default=None, description="Language code (ja, en)")
    max_results: Optional[int] = Field(default=20, ge=1, le=175, description="Maximum number of results")
    include_images: Optional[bool] = Field(default=True, description="Include card images in results")
    format_filter: Optional[str] = Field(default=None, description="Filter by Magic format (standard, modern, etc.)")


class CardSearchTool:
    """Tool for searching Magic: The Gathering cards."""

    @staticmethod
    def get_tool_definition() -> Tool:
        """Get the MCP tool definition."""
        return Tool(
            name="search_cards",
            description="Search for Magic: The Gathering cards using natural language. Supports Japanese queries like '白いクリーチャー', '稲妻', 'パワー3以上のクリーチャー'.",
            inputSchema=SearchCardsRequest.model_json_schema()
        )

    @staticmethod
    async def execute(arguments: dict[str, Any]) -> list[TextContent | ImageContent | EmbeddedResource]:
        """Execute the card search.

        Parameters
        ----------
        arguments : dict
            Tool arguments matching SearchCardsRequest

        Returns
        -------
        list
            List of MCP content items
        """
        try:
            # Validate arguments
            request = SearchCardsRequest(**arguments)

            # Set language if specified
            if request.language:
                set_current_locale(request.language)

            # Initialize processor and client
            processor = SearchProcessor()
            client = await get_client()

            # Process the natural language query
            processed = processor.process_query(request.query, request.language)
            scryfall_query = processed["scryfall_query"]

            # Add format filter if specified
            if request.format_filter:
                scryfall_query += f" f:{request.format_filter}"

            logger.info(f"Searching with query: {scryfall_query}")

            # Search for cards
            try:
                search_result = await client.search_cards(
                    query=scryfall_query,
                    page=1
                )
            except ScryfallAPIError as e:
                return [TextContent(
                    type="text",
                    text=f"検索エラー: {e}" if request.language == "ja" else f"Search error: {e}"
                )]

            # Limit results
            cards = search_result.data[:request.max_results]

            if not cards:
                mapping = get_current_mapping()
                no_results_msg = mapping.phrases.get("no results found", "No cards found.")
                return [TextContent(type="text", text=no_results_msg)]

            # Format results
            content_items = []

            # Add search summary
            summary = CardSearchTool._format_search_summary(
                processed, search_result.total_cards, len(cards), request.language
            )
            content_items.append(TextContent(type="text", text=summary))

            # Add card results
            for i, card in enumerate(cards, 1):
                card_text = CardSearchTool._format_card_result(card, i, request.language)
                content_items.append(TextContent(type="text", text=card_text))

                # Add card image if requested and available
                if request.include_images and card.image_uris and card.image_uris.normal:
                    content_items.append(ImageContent(
                        type="image",
                        data=str(card.image_uris.normal),
                        mimeType="image/jpeg"
                    ))

            # Add suggestions if available
            if processed["suggestions"]:
                suggestions_text = "\n".join(processed["suggestions"])
                if request.language == "ja":
                    suggestions_text = f"**提案:**\n{suggestions_text}"
                else:
                    suggestions_text = f"**Suggestions:**\n{suggestions_text}"
                content_items.append(TextContent(type="text", text=suggestions_text))

            return content_items

        except Exception as e:
            logger.error(f"Error in card search: {e}", exc_info=True)
            error_msg = f"予期しないエラーが発生しました: {e}" if request.language == "ja" else f"An unexpected error occurred: {e}"
            return [TextContent(type="text", text=error_msg)]

    @staticmethod
    def _format_search_summary(
        processed: dict[str, Any],
        total_cards: int,
        shown_cards: int,
        language: Optional[str]
    ) -> str:
        """Format search summary."""
        if language == "ja":
            summary = f"**検索結果**\n"
            summary += f"元のクエリ: {processed['original_query']}\n"
            summary += f"Scryfallクエリ: {processed['scryfall_query']}\n"
            summary += f"総カード数: {total_cards}枚\n"
            summary += f"表示: {shown_cards}枚\n"
            if processed['detected_intent'] != 'general_search':
                summary += f"検索意図: {processed['detected_intent']}\n"
        else:
            summary = f"**Search Results**\n"
            summary += f"Original query: {processed['original_query']}\n"
            summary += f"Scryfall query: {processed['scryfall_query']}\n"
            summary += f"Total cards: {total_cards}\n"
            summary += f"Showing: {shown_cards}\n"
            if processed['detected_intent'] != 'general_search':
                summary += f"Intent: {processed['detected_intent']}\n"

        return summary

    @staticmethod
    def _format_card_result(card: Card, index: int, language: Optional[str]) -> str:
        """Format a single card result."""
        if language == "ja":
            result = f"**{index}. {card.name}**\n"
            result += f"マナコスト: {card.mana_cost or 'なし'}\n"
            result += f"タイプ: {card.type_line}\n"

            if card.oracle_text:
                result += f"テキスト: {card.oracle_text}\n"

            if card.power is not None and card.toughness is not None:
                result += f"パワー/タフネス: {card.power}/{card.toughness}\n"
            elif card.loyalty is not None:
                result += f"忠誠度: {card.loyalty}\n"

            result += f"レアリティ: {card.rarity}\n"
            result += f"セット: {card.set_name} ({card.set.upper()})\n"

            # Price information
            if card.prices.usd:
                result += f"価格: ${card.prices.usd} USD"
                if card.prices.eur:
                    result += f", €{card.prices.eur} EUR"
                result += "\n"

        else:
            result = f"**{index}. {card.name}**\n"
            result += f"Mana Cost: {card.mana_cost or 'None'}\n"
            result += f"Type: {card.type_line}\n"

            if card.oracle_text:
                result += f"Text: {card.oracle_text}\n"

            if card.power is not None and card.toughness is not None:
                result += f"Power/Toughness: {card.power}/{card.toughness}\n"
            elif card.loyalty is not None:
                result += f"Loyalty: {card.loyalty}\n"

            result += f"Rarity: {card.rarity}\n"
            result += f"Set: {card.set_name} ({card.set.upper()})\n"

            # Price information
            if card.prices.usd:
                result += f"Price: ${card.prices.usd} USD"
                if card.prices.eur:
                    result += f", €{card.prices.eur} EUR"
                result += "\n"

        return result


class AutocompleteRequest(BaseModel):
    """Request model for card name autocomplete."""

    query: str = Field(description="Partial card name")
    language: Optional[str] = Field(default=None, description="Language code (ja, en)")


class AutocompleteTool:
    """Tool for card name autocompletion."""

    @staticmethod
    def get_tool_definition() -> Tool:
        """Get the MCP tool definition."""
        return Tool(
            name="autocomplete_card_names",
            description="Get card name suggestions for partial input. Useful for finding exact card names.",
            inputSchema=AutocompleteRequest.model_json_schema()
        )

    @staticmethod
    async def execute(arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the autocomplete search.

        Parameters
        ----------
        arguments : dict
            Tool arguments matching AutocompleteRequest

        Returns
        -------
        list[TextContent]
            List of autocomplete suggestions
        """
        try:
            request = AutocompleteRequest(**arguments)

            if request.language:
                set_current_locale(request.language)

            client = await get_client()

            # Get suggestions from Scryfall
            suggestions = await client.autocomplete_card_name(request.query)

            if not suggestions:
                mapping = get_current_mapping()
                no_results_msg = mapping.phrases.get("no results found", "No suggestions found.")
                return [TextContent(type="text", text=no_results_msg)]

            # Format suggestions
            if request.language == "ja":
                result_text = f"**'{request.query}'の候補:**\n"
            else:
                result_text = f"**Suggestions for '{request.query}':**\n"

            for suggestion in suggestions[:10]:  # Limit to 10 suggestions
                result_text += f"- {suggestion}\n"

            return [TextContent(type="text", text=result_text)]

        except Exception as e:
            logger.error(f"Error in autocomplete: {e}", exc_info=True)
            error_msg = f"オートコンプリートエラー: {e}" if request.language == "ja" else f"Autocomplete error: {e}"
            return [TextContent(type="text", text=error_msg)]


# Export tools
SEARCH_TOOLS = [
    CardSearchTool,
    AutocompleteTool,
]