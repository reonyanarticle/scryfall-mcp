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
from ..models import (
    AutocompleteRequest,
    BuiltQuery,
    SearchCardsRequest,
    SearchOptions,
    SearchResult,
)
from ..search.builder import QueryBuilder
from ..search.parser import SearchParser
from ..search.presenter import SearchPresenter

logger = logging.getLogger(__name__)


class CardSearchTool:
    """Tool for searching Magic: The Gathering cards."""

    @staticmethod
    def get_tool_definition() -> Tool:
        """Get the MCP tool definition.

        Returns
        -------
        Tool
            MCP tool definition for card search
        """
        return Tool(
            name="search_cards",
            description=(
                "Search for Magic: The Gathering cards using natural language. "
                "Supports Japanese queries like '白いクリーチャー', '稲妻', 'パワー3以上のクリーチャー', '最新のエクスパンション'. "
                "Automatically fetches the latest expansion set when querying for '最新のエクスパンション' or '最新のセット'."
            ),
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
            request = CardSearchTool._validate_request(arguments)

            with use_locale(request.language or "en"):
                builder, presenter, built = await CardSearchTool._build_query_pipeline(
                    request
                )

                scryfall_query = CardSearchTool._add_query_filters(
                    built.scryfall_query, request
                )
                built.scryfall_query = scryfall_query

                logger.info(f"Searching with query: {scryfall_query}")

                result = await CardSearchTool._execute_api_search(
                    scryfall_query, request
                )
                if isinstance(result, list):  # Error occurred
                    return result

                search_options = CardSearchTool._create_search_options(request)
                return presenter.present_results(result, built, search_options)

        except Exception as e:
            return CardSearchTool._handle_unexpected_error(e, arguments)

    @staticmethod
    def _validate_request(arguments: dict[str, Any]) -> SearchCardsRequest:
        """Validate and parse request arguments.

        Parameters
        ----------
        arguments : dict
            Raw tool arguments

        Returns
        -------
        SearchCardsRequest
            Validated request object
        """
        return SearchCardsRequest(**arguments)

    @staticmethod
    async def _build_query_pipeline(
        request: SearchCardsRequest,
    ) -> tuple[QueryBuilder, SearchPresenter, BuiltQuery]:
        """Build the query processing pipeline.

        Parameters
        ----------
        request : SearchCardsRequest
            Validated search request

        Returns
        -------
        tuple
            (builder, presenter, built_query)
        """
        mapping = get_current_mapping()
        parser = SearchParser(mapping)
        builder = QueryBuilder(mapping)
        presenter = SearchPresenter(mapping)

        parsed = parser.parse(request.query)
        built = await builder.build(parsed)

        return builder, presenter, built

    @staticmethod
    def _add_query_filters(
        scryfall_query: str, request: SearchCardsRequest
    ) -> str:
        """Add format and language filters to query.

        Parameters
        ----------
        scryfall_query : str
            Base Scryfall query
        request : SearchCardsRequest
            Search request with filter options

        Returns
        -------
        str
            Query with filters applied
        """
        if request.format_filter:
            scryfall_query += f" f:{request.format_filter}"

        # Add language filter if specified (for multilingual card search)
        # Note: Don't add lang filter for set-only searches, as not all sets
        # have cards in all languages (e.g., Marvel sets are English-only)
        is_set_only_search = (
            scryfall_query.strip().startswith("s:")
            and " " not in scryfall_query.strip()
        )
        if (
            request.language
            and request.language != "en"
            and not is_set_only_search
        ):
            scryfall_query += f" lang:{request.language}"

        return scryfall_query

    @staticmethod
    async def _execute_api_search(
        scryfall_query: str, request: SearchCardsRequest
    ) -> SearchResult | list[TextContent | ImageContent | EmbeddedResource]:
        """Execute API search and handle errors.

        Parameters
        ----------
        scryfall_query : str
            Formatted Scryfall query
        request : SearchCardsRequest
            Original search request

        Returns
        -------
        SearchResult | list[TextContent | ImageContent | EmbeddedResource]
            Search results or error content
        """
        client = await get_client()

        try:
            search_result = await client.search_cards(
                query=scryfall_query,
                page=1,
                include_multilingual=True,
            )
        except ScryfallAPIError as e:
            return CardSearchTool._handle_api_error(e, request)

        if not search_result.data:
            return CardSearchTool._handle_no_results(request)

        return search_result

    @staticmethod
    def _handle_api_error(
        error: ScryfallAPIError, request: SearchCardsRequest
    ) -> list[TextContent | ImageContent | EmbeddedResource]:
        """Handle Scryfall API errors.

        Parameters
        ----------
        error : ScryfallAPIError
            API error exception
        request : SearchCardsRequest
            Original search request

        Returns
        -------
        list[TextContent | ImageContent | EmbeddedResource]
            Formatted error message
        """
        error_handler = get_error_handler()

        category = ErrorCategory.API_ERROR
        if error.status_code == 400:
            category = ErrorCategory.SEARCH_SYNTAX_ERROR
        elif error.status_code == 429:
            category = ErrorCategory.RATE_LIMIT_ERROR
        elif error.status_code in (500, 502, 503, 504):
            category = ErrorCategory.SERVICE_UNAVAILABLE
        elif "timeout" in error.context.get(
            "category", ""
        ) or "network_error" in error.context.get("category", ""):
            category = ErrorCategory.NETWORK_ERROR

        context = ErrorContext(
            category=category,
            status_code=error.status_code,
            original_error=str(error),
            user_query=request.query,
            language=request.language or "en",
            additional_info=error.context,
        )

        error_info = error_handler.handle_error(context)
        formatted_error = error_handler.format_error_message(error_info)
        return [TextContent(type="text", text=formatted_error)]

    @staticmethod
    def _handle_no_results(request: SearchCardsRequest) -> list[TextContent | ImageContent | EmbeddedResource]:
        """Handle no results case.

        Parameters
        ----------
        request : SearchCardsRequest
            Original search request

        Returns
        -------
        list[TextContent | ImageContent | EmbeddedResource]
            No results guidance message
        """
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

    @staticmethod
    def _create_search_options(request: SearchCardsRequest) -> SearchOptions:
        """Create SearchOptions from request parameters.

        Parameters
        ----------
        request : SearchCardsRequest
            Search request

        Returns
        -------
        SearchOptions
            Search presentation options
        """
        return SearchOptions(
            max_results=request.max_results or 10,
            format_filter=request.format_filter,
            language=request.language,
            use_annotations=request.use_annotations,
            include_keywords=request.include_keywords,
            include_artist=request.include_artist,
            include_mana_production=request.include_mana_production,
            include_legalities=request.include_legalities,
        )

    @staticmethod
    def _handle_unexpected_error(
        error: Exception, arguments: dict[str, Any]
    ) -> list[TextContent | ImageContent | EmbeddedResource]:
        """Handle unexpected errors.

        Parameters
        ----------
        error : Exception
            Unexpected error
        arguments : dict
            Original arguments

        Returns
        -------
        list[TextContent | ImageContent | EmbeddedResource]
            Formatted error message
        """
        logger.error(f"Error in card search: {error}", exc_info=True)

        error_handler = get_error_handler()
        context = ErrorContext(
            category=ErrorCategory.UNKNOWN_ERROR,
            original_error=str(error),
            user_query=arguments.get("query"),
            language=arguments.get("language", "en"),
            additional_info={"error_type": type(error).__name__},
        )

        error_info = error_handler.handle_error(context)
        formatted_error = error_handler.format_error_message(error_info)
        return [TextContent(type="text", text=formatted_error)]


class AutocompleteTool:
    """Tool for card name autocompletion."""

    @staticmethod
    def get_tool_definition() -> Tool:
        """Get the MCP tool definition.

        Returns
        -------
        Tool
            MCP tool definition for autocomplete
        """
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

            with use_locale(request.language or "en"):
                client = await get_client()
                suggestions = await client.autocomplete_card_name(request.query)

                if not suggestions:
                    mapping = get_current_mapping()
                    no_results_msg = mapping.phrases.get(
                        "no results found", "No suggestions found."
                    )
                    return [TextContent(type="text", text=no_results_msg)]

                result_text = AutocompleteTool._format_suggestions(
                    suggestions, request
                )
                return [TextContent(type="text", text=result_text)]

        except Exception as e:
            return AutocompleteTool._handle_error(e, arguments)

    @staticmethod
    def _format_suggestions(
        suggestions: list[str], request: AutocompleteRequest
    ) -> str:
        """Format autocomplete suggestions.

        Parameters
        ----------
        suggestions : list[str]
            Card name suggestions
        request : AutocompleteRequest
            Original request

        Returns
        -------
        str
            Formatted suggestions text
        """
        if request.language == "ja":
            result_text = f"**'{request.query}'の候補:**\n"
        else:
            result_text = f"**Suggestions for '{request.query}':**\n"

        for suggestion in suggestions[:10]:  # Limit to 10 suggestions
            result_text += f"- {suggestion}\n"

        return result_text

    @staticmethod
    def _handle_error(error: Exception, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle autocomplete errors.

        Parameters
        ----------
        error : Exception
            Error that occurred
        arguments : dict
            Original arguments

        Returns
        -------
        list[TextContent]
            Formatted error message
        """
        logger.error(f"Error in autocomplete: {error}", exc_info=True)

        error_handler = get_error_handler()
        context = ErrorContext(
            category=ErrorCategory.UNKNOWN_ERROR,
            original_error=str(error),
            user_query=arguments.get("query"),
            language=arguments.get("language", "en"),
            additional_info={
                "error_type": type(error).__name__,
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
