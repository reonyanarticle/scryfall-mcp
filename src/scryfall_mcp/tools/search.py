"""Search tools for the Scryfall MCP Server.

This module provides MCP tools for searching Magic: The Gathering cards
using natural language queries with Japanese support.
"""

from __future__ import annotations

import logging
from typing import Any

from mcp import Tool
from mcp.types import EmbeddedResource, ImageContent, TextContent

from ..api.client import ScryfallAPIError, get_client
from ..errors import ErrorCategory, ErrorContext, get_error_handler
from ..i18n import get_current_mapping, use_locale
from ..models import AutocompleteRequest, SearchCardsRequest, SearchOptions
from ..search.builder import QueryBuilder
from ..search.parser import SearchParser
from ..search.presenter import SearchPresenter

logger = logging.getLogger(__name__)


class CardSearchTool:
    """Tool for searching Magic: The Gathering cards."""

    @staticmethod
    def get_tool_definition() -> Tool:
        """Get the MCP tool definition."""
        return Tool(
            name="search_cards",
            description="Search for Magic: The Gathering cards using natural language. Supports Japanese queries like '白いクリーチャー', '稲妻', 'パワー3以上のクリーチャー'.",
            inputSchema=SearchCardsRequest.model_json_schema(),
        )

    @staticmethod
    async def execute(
        arguments: dict[str, Any],
    ) -> list[TextContent | ImageContent | EmbeddedResource]:
        """Execute the card search using the refactored pipeline.

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

            # Use context-based locale management
            with use_locale(request.language or "en"):
                # Get locale-aware components
                mapping = get_current_mapping()
                parser = SearchParser(mapping)
                builder = QueryBuilder(mapping)
                presenter = SearchPresenter(mapping)

                # Step 1: Parse the natural language query
                parsed = parser.parse(request.query)

                # Step 2: Build the Scryfall query
                built = builder.build(parsed)

                # Add format filter if specified
                scryfall_query = built.scryfall_query
                if request.format_filter:
                    scryfall_query += f" f:{request.format_filter}"

                # Add language filter if specified (for multilingual card search)
                if request.language and request.language != "en":
                    scryfall_query += f" lang:{request.language}"

                # Update the built query with the modified query
                built.scryfall_query = scryfall_query

                logger.info(f"Searching with query: {scryfall_query}")

                # Step 3: Execute the search
                client = await get_client()
                try:
                    search_result = await client.search_cards(
                        query=scryfall_query,
                        page=1,
                        include_multilingual=True,  # Enable multilingual card data
                    )
                except ScryfallAPIError as e:
                    # Use enhanced error handling
                    error_handler = get_error_handler()

                    # Determine error category based on status code and context
                    category = ErrorCategory.API_ERROR
                    if e.status_code == 400:
                        category = ErrorCategory.SEARCH_SYNTAX_ERROR
                    elif e.status_code == 429:
                        category = ErrorCategory.RATE_LIMIT_ERROR
                    elif e.status_code in (500, 502, 503, 504):
                        category = ErrorCategory.SERVICE_UNAVAILABLE
                    elif "timeout" in e.context.get(
                        "category", ""
                    ) or "network_error" in e.context.get("category", ""):
                        category = ErrorCategory.NETWORK_ERROR

                    context = ErrorContext(
                        category=category,
                        status_code=e.status_code,
                        original_error=str(e),
                        user_query=request.query,
                        language=request.language or "en",
                        additional_info=e.context,
                    )

                    error_info = error_handler.handle_error(context)
                    formatted_error = error_handler.format_error_message(error_info)
                    return [TextContent(type="text", text=formatted_error)]

                # Handle no results with enhanced guidance
                if not search_result.data:
                    error_handler = get_error_handler()
                    context = ErrorContext(
                        category=ErrorCategory.NO_RESULTS_ERROR,
                        original_error="No cards found",
                        user_query=request.query,
                        language=request.language or "en",
                    )

                    error_info = error_handler.handle_error(context)
                    formatted_error = error_handler.format_error_message(error_info)
                    return [TextContent(type="text", text=formatted_error)]

                # Step 4: Present the results
                search_options = SearchOptions(
                    max_results=request.max_results or 10,
                    format_filter=request.format_filter,
                    language=request.language,
                    use_annotations=request.use_annotations,
                    include_keywords=request.include_keywords,
                    include_artist=request.include_artist,
                    include_mana_production=request.include_mana_production,
                    include_legalities=request.include_legalities,
                )

                return presenter.present_results(search_result, built, search_options)

        except Exception as e:
            logger.error(f"Error in card search: {e}", exc_info=True)

            # Use enhanced error handling for unexpected errors
            error_handler = get_error_handler()
            context = ErrorContext(
                category=ErrorCategory.UNKNOWN_ERROR,
                original_error=str(e),
                user_query=arguments.get("query"),
                language=arguments.get("language", "en"),
                additional_info={"error_type": type(e).__name__},
            )

            error_info = error_handler.handle_error(context)
            formatted_error = error_handler.format_error_message(error_info)
            return [TextContent(type="text", text=formatted_error)]


class AutocompleteTool:
    """Tool for card name autocompletion."""

    @staticmethod
    def get_tool_definition() -> Tool:
        """Get the MCP tool definition."""
        return Tool(
            name="autocomplete_card_names",
            description="Get card name suggestions for partial input. Useful for finding exact card names.",
            inputSchema=AutocompleteRequest.model_json_schema(),
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

            # Use context-based locale management
            with use_locale(request.language or "en"):
                client = await get_client()

                # Get suggestions from Scryfall
                suggestions = await client.autocomplete_card_name(request.query)

                if not suggestions:
                    mapping = get_current_mapping()
                    no_results_msg = mapping.phrases.get(
                        "no results found", "No suggestions found."
                    )
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

            # Use enhanced error handling for autocomplete errors
            error_handler = get_error_handler()
            context = ErrorContext(
                category=ErrorCategory.UNKNOWN_ERROR,
                original_error=str(e),
                user_query=arguments.get("query"),
                language=arguments.get("language", "en"),
                additional_info={
                    "error_type": type(e).__name__,
                    "operation": "autocomplete",
                },
            )

            error_info = error_handler.handle_error(context)
            formatted_error = error_handler.format_error_message(error_info)
            return [TextContent(type="text", text=formatted_error)]


# Export tools
SEARCH_TOOLS = [
    CardSearchTool,
    AutocompleteTool,
]
