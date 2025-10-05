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
from ..settings import is_user_agent_configured

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
        # Check if User-Agent is configured before allowing search
        if not is_user_agent_configured():
            config_message = (
                "⚠️ **Scryfall MCP Serverを使用するには、連絡先情報の設定が必要です**\n\n"
                "Scryfall APIのガイドラインに従い、User-Agentに連絡先情報を含める必要があります。\n"
                "これにより、API利用時の問題発生時にScryfallから連絡を受けることができます。\n\n"
                "**📋 設定方法**\n\n"
                "Claude Desktopの設定ファイルを開き、以下の内容を追加してください：\n\n"
                "**macOS/Linux:** `~/Library/Application Support/Claude/claude_desktop_config.json`\n"
                "**Windows:** `%APPDATA%\\Claude\\claude_desktop_config.json`\n\n"
                "```json\n"
                "{\n"
                '  "mcpServers": {\n'
                '    "scryfall": {\n'
                '      "command": "uv",\n'
                '      "args": ["--directory", "/path/to/scryfall-mcp", "run", "scryfall-mcp"],\n'
                '      "env": {\n'
                '        "SCRYFALL_MCP_USER_AGENT": "YourApp/1.0 (your-email@example.com)"\n'
                "      }\n"
                "    }\n"
                "  }\n"
                "}\n"
                "```\n\n"
                "**✏️ 連絡先情報の例**\n"
                "- メールアドレス: `YourApp/1.0 (yourname@example.com)`\n"
                "- GitHubリポジトリ: `YourApp/1.0 (https://github.com/username/repo)`\n"
                "- その他URL: `YourApp/1.0 (https://example.com/contact)`\n\n"
                "**⚠️ 重要**\n"
                "- `your-email@example.com` を実際の連絡先に置き換えてください\n"
                "- `/path/to/scryfall-mcp` をこのプロジェクトの実際のパスに置き換えてください\n"
                "- 設定後、Claude Desktopを再起動してください\n\n"
                "**💡 なぜこの設定が必要なのか？**\n\n"
                "Scryfallは無料で高品質なMTGデータAPIを提供していますが、適切な利用を促進するため、"
                "すべてのクライアントに連絡先情報の提供を求めています。これにより：\n"
                "- レート制限違反時に警告を受けることができます\n"
                "- API変更時に事前通知を受けることができます\n"
                "- 問題が発生した際に迅速に対応できます\n\n"
                "設定完了後、再度カード検索をお試しください！"
            )
            return [TextContent(type="text", text=config_message)]

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
