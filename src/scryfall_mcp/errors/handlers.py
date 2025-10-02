"""Enhanced error handlers with status-specific guidance."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any


class ErrorCategory(Enum):
    """Categories of errors that can occur."""

    API_ERROR = "api_error"
    NETWORK_ERROR = "network_error"
    VALIDATION_ERROR = "validation_error"
    SEARCH_SYNTAX_ERROR = "search_syntax_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    NO_RESULTS_ERROR = "no_results_error"
    SERVICE_UNAVAILABLE = "service_unavailable"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class ErrorContext:
    """Context information for errors."""

    category: ErrorCategory
    status_code: int | None = None
    original_error: str = ""
    user_query: str | None = None
    language: str = "en"
    additional_info: dict[str, Any] | None = None


class EnhancedErrorHandler:
    """Enhanced error handler with status-specific guidance."""

    def __init__(self):
        """Initialize the error handler."""
        self._error_messages = self._build_error_messages()

    def _build_error_messages(self) -> dict[str, dict[int | str, dict[str, str]]]:
        """Build comprehensive error message mappings."""
        return {
            "ja": {
                # HTTP Status codes
                400: {
                    "message": "検索構文にエラーがあります",
                    "guidance": "以下を確認してください：\n• カード名の綴りが正確か\n• 演算子（>=, <=等）が適切か\n• 引用符が正しく閉じられているか",
                    "examples": "例: 'パワー3以上のクリーチャー', '白いカード', '稲妻'",
                },
                403: {
                    "message": "Scryfall APIへのアクセスが拒否されました",
                    "guidance": "サーバーの設定に問題があります。管理者にお問い合わせください。",
                    "technical": "User-AgentまたはAcceptヘッダーが不足している可能性があります。",
                },
                404: {
                    "message": "指定されたリソースが見つかりません",
                    "guidance": "検索条件を確認してください。カードが存在しない可能性があります。",
                    "examples": "例: カード名の綴りを確認する、部分検索を試す",
                },
                429: {
                    "message": "アクセス頻度が高すぎます",
                    "guidance": "少しお待ちください。検索頻度を下げて数秒後に再試行してください。",
                    "technical": "Scryfall APIの制限（10リクエスト/秒）に達しています。",
                },
                500: {
                    "message": "Scryfallサーバーでエラーが発生しています",
                    "guidance": "しばらくしてから再試行してください。問題が続く場合はScryfall側の一時的な障害の可能性があります。",
                    "technical": "Scryfall APIサーバーの内部エラーです。",
                },
                502: {
                    "message": "Scryfallサーバーに接続できません",
                    "guidance": "ネットワーク接続を確認し、しばらく後に再試行してください。",
                    "technical": "Bad Gateway - プロキシサーバーエラーまたはアップストリーム接続エラーです。",
                },
                503: {
                    "message": "Scryfallサービスが一時的に利用できません",
                    "guidance": "メンテナンス中の可能性があります。しばらく後に再試行してください。",
                    "technical": "Service Unavailable - サーバーが一時的に過負荷またはメンテナンス中です。",
                },
                504: {
                    "message": "Scryfallサーバーの応答がタイムアウトしました",
                    "guidance": "検索条件を簡略化するか、しばらく後に再試行してください。",
                    "technical": "Gateway Timeout - アップストリームサーバーの応答が遅すぎます。",
                },
                # Application-specific errors
                "no_results": {
                    "message": "検索条件に一致するカードが見つかりませんでした",
                    "guidance": "以下を試してください：\n• 検索条件を緩くする\n• カード名の綴りを確認する\n• 部分検索を試す\n• 英語名での検索を試す",
                    "examples": "例: '稲妻' → '稲', 'Lightning Bolt'",
                },
                "search_syntax": {
                    "message": "検索構文が正しくありません",
                    "guidance": "正しい検索構文を使用してください",
                    "examples": "例: '稲妻', 'パワー3以上', '白いクリーチャー', 'c:red t:creature'",
                },
                "network": {
                    "message": "ネットワークエラーが発生しました",
                    "guidance": "インターネット接続を確認し、再試行してください。",
                    "technical": "DNS解決エラーまたは接続タイムアウトです。",
                },
                "timeout": {
                    "message": "リクエストがタイムアウトしました",
                    "guidance": "検索条件を簡略化するか、しばらく後に再試行してください。",
                    "technical": "Scryfallサーバーからの応答が30秒以内に返されませんでした。",
                },
            },
            "en": {
                # HTTP Status codes
                400: {
                    "message": "Invalid search syntax",
                    "guidance": "Please check:\n• Card names are spelled correctly\n• Operators (>=, <= etc.) are used properly\n• Quotes are properly closed",
                    "examples": "Examples: 'creatures with power >= 3', 'white cards', 'Lightning Bolt'",
                },
                403: {
                    "message": "Access to Scryfall API was denied",
                    "guidance": "There is a server configuration issue. Please contact the administrator.",
                    "technical": "Missing User-Agent or Accept headers may be the cause.",
                },
                404: {
                    "message": "The specified resource was not found",
                    "guidance": "Please verify your search criteria. The card may not exist.",
                    "examples": "Try: checking card name spelling, using partial search",
                },
                429: {
                    "message": "Rate limit exceeded",
                    "guidance": "Please wait a moment. Reduce search frequency and retry in a few seconds.",
                    "technical": "Scryfall API limit (10 requests/second) has been reached.",
                },
                500: {
                    "message": "Scryfall server error occurred",
                    "guidance": "Please try again later. If the problem persists, it may be a temporary Scryfall service issue.",
                    "technical": "Internal server error from Scryfall API.",
                },
                502: {
                    "message": "Cannot connect to Scryfall server",
                    "guidance": "Please check your network connection and try again later.",
                    "technical": "Bad Gateway - proxy server error or upstream connection error.",
                },
                503: {
                    "message": "Scryfall service is temporarily unavailable",
                    "guidance": "The service may be under maintenance. Please try again later.",
                    "technical": "Service Unavailable - server temporarily overloaded or under maintenance.",
                },
                504: {
                    "message": "Scryfall server response timed out",
                    "guidance": "Try simplifying your search criteria or retry later.",
                    "technical": "Gateway Timeout - upstream server response too slow.",
                },
                # Application-specific errors
                "no_results": {
                    "message": "No cards found matching your search criteria",
                    "guidance": "Try:\n• Broadening your search criteria\n• Checking card name spelling\n• Using partial search\n• Searching in English",
                    "examples": "Examples: 'Lightning' instead of 'Lightning Bolt', broader terms",
                },
                "search_syntax": {
                    "message": "Invalid search syntax",
                    "guidance": "Please use proper search syntax",
                    "examples": "Examples: 'Lightning Bolt', 'power >= 3', 'white creatures', 'c:red t:creature'",
                },
                "network": {
                    "message": "Network error occurred",
                    "guidance": "Please check your internet connection and try again.",
                    "technical": "DNS resolution error or connection timeout.",
                },
                "timeout": {
                    "message": "Request timed out",
                    "guidance": "Try simplifying your search criteria or retry later.",
                    "technical": "No response received from Scryfall server within 30 seconds.",
                },
            },
        }

    def handle_error(self, context: ErrorContext) -> dict[str, str]:
        """Handle error and return user-friendly message with guidance.

        Parameters
        ----------
        context : ErrorContext
            Error context information

        Returns
        -------
        dict[str, str]
            Dictionary with 'message', 'guidance', 'examples', and 'technical' fields
        """
        lang_messages = self._error_messages.get(
            context.language, self._error_messages["en"]
        )

        # Try to get specific error message based on status code or category
        error_info = None

        if context.status_code and context.status_code in lang_messages:
            error_info = lang_messages[context.status_code]
        elif context.category == ErrorCategory.NO_RESULTS_ERROR:
            error_info = lang_messages.get("no_results")
        elif context.category == ErrorCategory.SEARCH_SYNTAX_ERROR:
            error_info = lang_messages.get("search_syntax")
        elif context.category == ErrorCategory.NETWORK_ERROR:
            error_info = lang_messages.get("network")
        elif context.category == ErrorCategory.RATE_LIMIT_ERROR:
            error_info = lang_messages.get(429)

        # Fallback to generic error
        if not error_info:
            if context.language == "ja":
                error_info = {
                    "message": f"エラーが発生しました: {context.original_error}",
                    "guidance": "しばらく後に再試行してください。",
                    "technical": f"詳細: {context.original_error}",
                }
            else:
                error_info = {
                    "message": f"An error occurred: {context.original_error}",
                    "guidance": "Please try again later.",
                    "technical": f"Details: {context.original_error}",
                }

        # Add query-specific suggestions if available
        if context.user_query:
            recovery_suggestions = self._get_query_recovery_suggestions(
                context.user_query, context.language
            )
            if recovery_suggestions:
                current_guidance = error_info.get("guidance", "")
                if current_guidance and not current_guidance.endswith("\n"):
                    current_guidance += "\n"
                error_info["guidance"] = current_guidance + recovery_suggestions

        return error_info

    def _get_query_recovery_suggestions(self, query: str, language: str) -> str:
        """Get query-specific recovery suggestions.

        Parameters
        ----------
        query : str
            Original user query
        language : str
            User language

        Returns
        -------
        str
            Recovery suggestions specific to the query
        """
        suggestions = []

        # Check for common query patterns and suggest improvements
        if self._contains_japanese_quotes(query):
            if language == "ja":
                suggestions.append("• 日本語の引用符を英語の引用符に変更してください")
            else:
                suggestions.append(
                    "• Try using English quotes instead of Japanese quotes"
                )

        if self._has_complex_syntax(query):
            if language == "ja":
                suggestions.append("• 複雑な検索条件を分割してみてください")
            else:
                suggestions.append("• Try breaking down complex search conditions")

        if self._appears_to_be_card_name(query):
            if language == "ja":
                suggestions.append(f"• '{query}'の部分検索を試してください")
                suggestions.append("• 英語名での検索を試してください")
            else:
                suggestions.append(f"• Try partial search for '{query}'")
                suggestions.append("• Check for spelling variations")

        return "\n".join(suggestions) if suggestions else ""

    def _contains_japanese_quotes(self, query: str) -> bool:
        """Check if query contains Japanese-style quotes."""
        return "「" in query or "」" in query

    def _has_complex_syntax(self, query: str) -> bool:
        """Check if query has complex syntax that might be causing issues."""
        # Count operators, parentheses, and other complex syntax elements
        operators = len(re.findall(r"[<>=!]+", query))
        parentheses = query.count("(") + query.count(")")
        fields = len(re.findall(r"\w+:", query))

        return operators > 2 or parentheses > 2 or fields > 3

    def _appears_to_be_card_name(self, query: str) -> bool:
        """Check if query appears to be a card name search."""
        # Simple heuristic: no operators, no field specifiers, not too long
        has_operators = bool(re.search(r"[<>=!]+", query))
        has_fields = bool(re.search(r"\w+:", query))
        is_reasonable_length = len(query.split()) <= 4

        return not has_operators and not has_fields and is_reasonable_length

    def format_error_message(
        self, error_info: dict[str, str], include_technical: bool = False
    ) -> str:
        """Format error information into a user-friendly message.

        Parameters
        ----------
        error_info : dict[str, str]
            Error information from handle_error
        include_technical : bool
            Whether to include technical details

        Returns
        -------
        str
            Formatted error message
        """
        message_parts = []

        # Add main error message
        if "message" in error_info:
            message_parts.append(f"❌ **{error_info['message']}**")

        # Add guidance
        if "guidance" in error_info:
            message_parts.append(
                f"\n💡 **ガイド:**\n{error_info['guidance']}"
                if "ガイド" in error_info["guidance"]
                or "guide" not in error_info["guidance"].lower()
                else f"\n💡 **Guide:**\n{error_info['guidance']}"
            )

        # Add examples
        if "examples" in error_info:
            message_parts.append(
                f"\n📝 **例:** {error_info['examples']}"
                if "例:" in error_info.get("examples", "")
                else f"\n📝 **Examples:** {error_info['examples']}"
            )

        # Add technical details if requested
        if include_technical and "technical" in error_info:
            message_parts.append(
                f"\n🔧 **詳細:** {error_info['technical']}"
                if "詳細" in error_info.get("technical", "")
                else f"\n🔧 **Technical:** {error_info['technical']}"
            )

        return "\n".join(message_parts)


# Global error handler instance
_error_handler: EnhancedErrorHandler | None = None


def get_error_handler() -> EnhancedErrorHandler:
    """Get the global error handler instance.

    Returns
    -------
    EnhancedErrorHandler
        Global error handler instance
    """
    global _error_handler
    if _error_handler is None:
        _error_handler = EnhancedErrorHandler()
    return _error_handler
