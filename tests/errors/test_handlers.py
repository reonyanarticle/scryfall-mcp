"""Tests for error handlers module."""

from __future__ import annotations

import pytest

from scryfall_mcp.errors.handlers import (
    EnhancedErrorHandler,
    ErrorCategory,
    ErrorContext,
    get_error_handler,
)


class TestErrorContext:
    """Test ErrorContext dataclass."""

    def test_basic_context(self):
        """Test basic error context creation."""
        context = ErrorContext(
            category=ErrorCategory.API_ERROR,
            status_code=500,
            original_error="Server error",
            user_query="test query",
            language="en",
        )

        assert context.category == ErrorCategory.API_ERROR
        assert context.status_code == 500
        assert context.original_error == "Server error"
        assert context.user_query == "test query"
        assert context.language == "en"

    def test_context_with_defaults(self):
        """Test error context with default values."""
        context = ErrorContext(category=ErrorCategory.UNKNOWN_ERROR)

        assert context.status_code is None
        assert context.original_error == ""
        assert context.user_query is None
        assert context.language == "en"
        assert context.additional_info is None

    def test_context_with_additional_info(self):
        """Test error context with additional information."""
        context = ErrorContext(
            category=ErrorCategory.NETWORK_ERROR,
            additional_info={"retry_after": 60, "endpoint": "/search"},
        )

        assert context.additional_info["retry_after"] == 60
        assert context.additional_info["endpoint"] == "/search"


class TestEnhancedErrorHandler:
    """Test EnhancedErrorHandler class."""

    @pytest.fixture
    def handler(self):
        """Create error handler instance."""
        return EnhancedErrorHandler()

    def test_handle_error_400_en(self, handler):
        """Test handling 400 error in English."""
        context = ErrorContext(
            category=ErrorCategory.SEARCH_SYNTAX_ERROR,
            status_code=400,
            user_query="invalid query",
            language="en",
        )

        error_info = handler.handle_error(context)

        assert "Invalid search syntax" in error_info["message"]
        assert "guidance" in error_info
        assert "Card names are spelled correctly" in error_info["guidance"]
        assert "examples" in error_info

    def test_handle_error_400_ja(self, handler):
        """Test handling 400 error in Japanese."""
        context = ErrorContext(
            category=ErrorCategory.SEARCH_SYNTAX_ERROR,
            status_code=400,
            user_query="無効なクエリ",
            language="ja",
        )

        error_info = handler.handle_error(context)

        assert "検索構文にエラーがあります" in error_info["message"]
        assert "guidance" in error_info
        assert "カード名の綴りが正確か" in error_info["guidance"]

    def test_handle_error_403(self, handler):
        """Test handling 403 error."""
        context = ErrorContext(
            category=ErrorCategory.API_ERROR,
            status_code=403,
            language="en",
        )

        error_info = handler.handle_error(context)

        assert "Access to Scryfall API was denied" in error_info["message"]
        assert "technical" in error_info
        assert "User-Agent" in error_info["technical"]

    def test_handle_error_404(self, handler):
        """Test handling 404 error."""
        context = ErrorContext(
            category=ErrorCategory.API_ERROR,
            status_code=404,
            language="en",
        )

        error_info = handler.handle_error(context)

        assert "not found" in error_info["message"].lower()

    def test_handle_error_429_en(self, handler):
        """Test handling rate limit error in English."""
        context = ErrorContext(
            category=ErrorCategory.RATE_LIMIT_ERROR,
            status_code=429,
            language="en",
        )

        error_info = handler.handle_error(context)

        assert "Rate limit exceeded" in error_info["message"]
        assert "wait" in error_info["guidance"].lower()

    def test_handle_error_429_ja(self, handler):
        """Test handling rate limit error in Japanese."""
        context = ErrorContext(
            category=ErrorCategory.RATE_LIMIT_ERROR,
            status_code=429,
            language="ja",
        )

        error_info = handler.handle_error(context)

        assert "アクセス頻度が高すぎます" in error_info["message"]

    def test_handle_error_500(self, handler):
        """Test handling 500 error."""
        context = ErrorContext(
            category=ErrorCategory.SERVICE_UNAVAILABLE,
            status_code=500,
            language="en",
        )

        error_info = handler.handle_error(context)

        assert "server error" in error_info["message"].lower()

    def test_handle_error_502(self, handler):
        """Test handling 502 error."""
        context = ErrorContext(
            category=ErrorCategory.SERVICE_UNAVAILABLE,
            status_code=502,
            language="en",
        )

        error_info = handler.handle_error(context)

        assert "connect" in error_info["message"].lower()

    def test_handle_error_503(self, handler):
        """Test handling 503 error."""
        context = ErrorContext(
            category=ErrorCategory.SERVICE_UNAVAILABLE,
            status_code=503,
            language="en",
        )

        error_info = handler.handle_error(context)

        assert "unavailable" in error_info["message"].lower()

    def test_handle_error_504(self, handler):
        """Test handling 504 error."""
        context = ErrorContext(
            category=ErrorCategory.SERVICE_UNAVAILABLE,
            status_code=504,
            language="en",
        )

        error_info = handler.handle_error(context)

        assert "timed out" in error_info["message"].lower()

    def test_handle_no_results_error_en(self, handler):
        """Test handling no results error in English."""
        context = ErrorContext(
            category=ErrorCategory.NO_RESULTS_ERROR,
            user_query="nonexistent card",
            language="en",
        )

        error_info = handler.handle_error(context)

        assert "No cards found" in error_info["message"]
        assert "guidance" in error_info
        assert "Broadening your search" in error_info["guidance"]

    def test_handle_no_results_error_ja(self, handler):
        """Test handling no results error in Japanese."""
        context = ErrorContext(
            category=ErrorCategory.NO_RESULTS_ERROR,
            user_query="存在しないカード",
            language="ja",
        )

        error_info = handler.handle_error(context)

        assert "見つかりませんでした" in error_info["message"]

    def test_handle_search_syntax_error(self, handler):
        """Test handling search syntax error."""
        context = ErrorContext(
            category=ErrorCategory.SEARCH_SYNTAX_ERROR,
            language="en",
        )

        error_info = handler.handle_error(context)

        assert "syntax" in error_info["message"].lower()

    def test_handle_network_error_en(self, handler):
        """Test handling network error in English."""
        context = ErrorContext(
            category=ErrorCategory.NETWORK_ERROR,
            language="en",
        )

        error_info = handler.handle_error(context)

        assert "Network error" in error_info["message"]
        assert "internet connection" in error_info["guidance"].lower()

    def test_handle_network_error_ja(self, handler):
        """Test handling network error in Japanese."""
        context = ErrorContext(
            category=ErrorCategory.NETWORK_ERROR,
            language="ja",
        )

        error_info = handler.handle_error(context)

        assert "ネットワークエラー" in error_info["message"]

    def test_handle_unknown_error_en(self, handler):
        """Test handling unknown error in English."""
        context = ErrorContext(
            category=ErrorCategory.UNKNOWN_ERROR,
            original_error="Unexpected error occurred",
            language="en",
        )

        error_info = handler.handle_error(context)

        assert "Unexpected error occurred" in error_info["message"]

    def test_handle_unknown_error_ja(self, handler):
        """Test handling unknown error in Japanese."""
        context = ErrorContext(
            category=ErrorCategory.UNKNOWN_ERROR,
            original_error="予期しないエラー",
            language="ja",
        )

        error_info = handler.handle_error(context)

        assert "予期しないエラー" in error_info["message"]

    def test_format_error_message_basic(self, handler):
        """Test basic error message formatting."""
        error_info = {
            "message": "Test error",
            "guidance": "Try this instead",
        }

        formatted = handler.format_error_message(error_info)

        assert "❌" in formatted
        assert "Test error" in formatted
        assert "💡" in formatted
        assert "Try this instead" in formatted

    def test_format_error_message_with_examples(self, handler):
        """Test error message formatting with examples."""
        error_info = {
            "message": "Test error",
            "guidance": "Some guidance",
            "examples": "Example: 'test query'",
        }

        formatted = handler.format_error_message(error_info)

        assert "📝" in formatted
        assert "Example:" in formatted or "例:" in formatted

    def test_format_error_message_with_technical(self, handler):
        """Test error message formatting with technical details."""
        error_info = {
            "message": "Test error",
            "guidance": "Some guidance",
            "technical": "Technical details here",
        }

        formatted = handler.format_error_message(error_info, include_technical=True)

        assert "🔧" in formatted
        assert "Technical details here" in formatted

    def test_format_error_message_without_technical(self, handler):
        """Test error message formatting without technical details."""
        error_info = {
            "message": "Test error",
            "guidance": "Some guidance",
            "technical": "Technical details here",
        }

        formatted = handler.format_error_message(error_info, include_technical=False)

        assert "Technical details here" not in formatted

    def test_query_recovery_japanese_quotes(self, handler):
        """Test query recovery suggestions for Japanese quotes."""
        suggestions = handler._get_query_recovery_suggestions(
            "「Lightning Bolt」", "en"
        )

        assert "English quotes" in suggestions

    def test_query_recovery_japanese_quotes_ja(self, handler):
        """Test query recovery suggestions for Japanese quotes in Japanese."""
        suggestions = handler._get_query_recovery_suggestions("「稲妻」", "ja")

        assert "日本語の引用符" in suggestions

    def test_query_recovery_complex_syntax(self, handler):
        """Test query recovery suggestions for complex syntax."""
        query = "c:red t:creature pow>=3 tou<=5 (cmc:2 OR cmc:3) format:modern"
        suggestions = handler._get_query_recovery_suggestions(query, "en")

        assert "breaking down" in suggestions.lower()

    def test_query_recovery_card_name(self, handler):
        """Test query recovery suggestions for card name."""
        suggestions = handler._get_query_recovery_suggestions("Lightning Bolt", "en")

        assert "partial search" in suggestions.lower()

    def test_query_recovery_card_name_ja(self, handler):
        """Test query recovery suggestions for card name in Japanese."""
        suggestions = handler._get_query_recovery_suggestions("稲妻", "ja")

        assert "部分検索" in suggestions or "英語名" in suggestions

    def test_contains_japanese_quotes(self, handler):
        """Test detection of Japanese quotes."""
        assert handler._contains_japanese_quotes("「test」")
        assert handler._contains_japanese_quotes("「test」query")
        assert not handler._contains_japanese_quotes("'test'")
        assert not handler._contains_japanese_quotes('"test"')

    def test_has_complex_syntax(self, handler):
        """Test detection of complex syntax."""
        # Complex queries
        assert handler._has_complex_syntax("a:1 b:2 c:3 d:4")  # Many fields
        assert handler._has_complex_syntax("(a OR b) AND (c OR d)")  # Many parens
        assert handler._has_complex_syntax("pow>=3 tou<=5 cmc>2")  # Many operators

        # Simple queries
        assert not handler._has_complex_syntax("Lightning Bolt")
        assert not handler._has_complex_syntax("c:red")
        assert not handler._has_complex_syntax("pow>=3")

    def test_appears_to_be_card_name(self, handler):
        """Test detection of card name queries."""
        # Card names
        assert handler._appears_to_be_card_name("Lightning Bolt")
        assert handler._appears_to_be_card_name("Black Lotus")
        assert handler._appears_to_be_card_name("稲妻")

        # Not card names
        assert not handler._appears_to_be_card_name("c:red t:creature")
        assert not handler._appears_to_be_card_name("pow>=3")
        assert not handler._appears_to_be_card_name(
            "very long query with many words exceeding limit"
        )

    def test_error_messages_coverage(self, handler):
        """Test that error messages are defined for all status codes."""
        # English messages
        en_messages = handler._error_messages["en"]
        assert 400 in en_messages
        assert 403 in en_messages
        assert 404 in en_messages
        assert 429 in en_messages
        assert 500 in en_messages
        assert 502 in en_messages
        assert 503 in en_messages
        assert 504 in en_messages
        assert "no_results" in en_messages
        assert "search_syntax" in en_messages
        assert "network" in en_messages
        assert "timeout" in en_messages

        # Japanese messages
        ja_messages = handler._error_messages["ja"]
        assert 400 in ja_messages
        assert 403 in ja_messages
        assert 404 in ja_messages
        assert 429 in ja_messages
        assert 500 in ja_messages
        assert 502 in ja_messages
        assert 503 in ja_messages
        assert 504 in ja_messages
        assert "no_results" in ja_messages
        assert "search_syntax" in ja_messages
        assert "network" in ja_messages
        assert "timeout" in ja_messages

    def test_get_error_handler_singleton(self):
        """Test that get_error_handler returns a singleton."""
        handler1 = get_error_handler()
        handler2 = get_error_handler()

        assert handler1 is handler2

    def test_query_recovery_no_suggestions(self, handler):
        """Test query recovery with no applicable suggestions."""
        suggestions = handler._get_query_recovery_suggestions("simple query", "en")

        # Should either be empty or contain card name suggestions
        assert isinstance(suggestions, str)

    def test_handle_error_with_query_suggestions(self, handler):
        """Test that handle_error includes query-specific suggestions."""
        context = ErrorContext(
            category=ErrorCategory.NO_RESULTS_ERROR,
            user_query="「test」",
            language="en",
        )

        error_info = handler.handle_error(context)

        # Should include both general guidance and query-specific suggestions
        assert "guidance" in error_info
        assert "quotes" in error_info["guidance"].lower()

    def test_handle_error_fallback_language(self, handler):
        """Test error handling with unsupported language falls back to English."""
        context = ErrorContext(
            category=ErrorCategory.API_ERROR,
            status_code=500,
            language="fr",  # Unsupported language
        )

        error_info = handler.handle_error(context)

        # Should use English messages
        assert "error" in error_info["message"].lower()

    def test_all_error_categories_handled(self, handler):
        """Test that all error categories can be handled."""
        categories = [
            ErrorCategory.API_ERROR,
            ErrorCategory.NETWORK_ERROR,
            ErrorCategory.VALIDATION_ERROR,
            ErrorCategory.SEARCH_SYNTAX_ERROR,
            ErrorCategory.RATE_LIMIT_ERROR,
            ErrorCategory.NO_RESULTS_ERROR,
            ErrorCategory.SERVICE_UNAVAILABLE,
            ErrorCategory.UNKNOWN_ERROR,
        ]

        for category in categories:
            context = ErrorContext(category=category, language="en")
            error_info = handler.handle_error(context)

            # All should return valid error info
            assert "message" in error_info
            assert isinstance(error_info["message"], str)
