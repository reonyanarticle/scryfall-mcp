"""Enhanced error handling system for the Scryfall MCP Server."""

from __future__ import annotations

from .handlers import (
    EnhancedErrorHandler,
    ErrorCategory,
    ErrorContext,
    get_error_handler,
)

__all__ = [
    "ErrorCategory",
    "ErrorContext",
    "EnhancedErrorHandler",
    "get_error_handler",
]
