"""Tests for EmailAuthMiddleware integration."""

from __future__ import annotations

import base64
import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

# Skip all tests if fastapi is not installed
pytest.importorskip("fastapi")

from scryfall_mcp.auth.email import hash_secret
from scryfall_mcp.auth.middleware import EmailAuthMiddleware
from scryfall_mcp.settings import Settings


class TestEmailAuthMiddleware:
    """Test EmailAuthMiddleware integration."""

    @pytest.fixture
    def settings(self) -> Settings:
        """Create test settings with email auth."""
        email = "test@example.com"
        secret = "test-secret-123"
        hashed = hash_secret(secret)

        return Settings(
            email_auth_credentials={email: hashed},
            email_blocklist_patterns=["blocked@*"],
        )

    @pytest.fixture
    def middleware(self, settings: Settings) -> EmailAuthMiddleware:
        """Create middleware instance."""
        mock_app = AsyncMock()
        return EmailAuthMiddleware(mock_app, settings)

    def create_basic_auth_header(self, email: str, secret: str) -> str:
        """Create Basic auth header value."""
        credentials = f"{email}:{secret}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"

    @pytest.mark.asyncio
    async def test_successful_authentication(
        self, middleware: EmailAuthMiddleware
    ) -> None:
        """Test successful authentication flow."""
        # Arrange
        auth_header = self.create_basic_auth_header("test@example.com", "test-secret-123")
        scope = {
            "type": "http",
            "headers": [(b"authorization", auth_header.encode())],
        }
        receive = MagicMock()
        send = MagicMock()

        # Act
        await middleware(scope, receive, send)

        # Assert
        middleware.app.assert_awaited_once()
        assert "user" in scope
        assert scope["user"]["email"] == "test@example.com"
        assert "masked_email" in scope["user"]

    @pytest.mark.asyncio
    async def test_missing_authorization_header(
        self, middleware: EmailAuthMiddleware
    ) -> None:
        """Test authentication fails without header."""
        from fastapi import HTTPException

        scope = {"type": "http", "headers": []}
        receive = MagicMock()
        send = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            await middleware(scope, receive, send)

        assert exc_info.value.status_code == 401
        assert "Missing Authorization" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_invalid_header_format(self, middleware: EmailAuthMiddleware) -> None:
        """Test authentication fails with Bearer token."""
        from fastapi import HTTPException

        scope = {
            "type": "http",
            "headers": [(b"authorization", b"Bearer jwt-token")],
        }
        receive = MagicMock()
        send = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            await middleware(scope, receive, send)

        assert exc_info.value.status_code == 401
        assert "Invalid Authorization" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_wrong_secret(self, middleware: EmailAuthMiddleware) -> None:
        """Test authentication fails with wrong secret."""
        from fastapi import HTTPException

        auth_header = self.create_basic_auth_header("test@example.com", "wrong-secret")
        scope = {
            "type": "http",
            "headers": [(b"authorization", auth_header.encode())],
        }
        receive = MagicMock()
        send = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            await middleware(scope, receive, send)

        assert exc_info.value.status_code == 401
        assert "Invalid email or secret" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_blocked_email(self, middleware: EmailAuthMiddleware) -> None:
        """Test authentication fails for blocked email."""
        from fastapi import HTTPException

        # "blocked@*" pattern should match
        auth_header = self.create_basic_auth_header("blocked@spam.com", "any-secret")
        scope = {
            "type": "http",
            "headers": [(b"authorization", auth_header.encode())],
        }
        receive = MagicMock()
        send = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            await middleware(scope, receive, send)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_non_http_scope_bypasses_auth(
        self, middleware: EmailAuthMiddleware
    ) -> None:
        """Test non-HTTP requests bypass authentication."""
        scope = {"type": "websocket"}
        receive = MagicMock()
        send = MagicMock()

        await middleware(scope, receive, send)

        middleware.app.assert_awaited_once()
        # No authentication required for non-HTTP

    @pytest.mark.asyncio
    async def test_successful_auth_logs_masked_email(
        self, middleware: EmailAuthMiddleware, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test successful authentication logs masked email."""
        auth_header = self.create_basic_auth_header("test@example.com", "test-secret-123")
        scope = {
            "type": "http",
            "headers": [(b"authorization", auth_header.encode())],
        }
        receive = MagicMock()
        send = MagicMock()

        with caplog.at_level(logging.INFO):
            await middleware(scope, receive, send)

        # Check log contains masked email, not full email
        assert "User authenticated:" in caplog.text
        assert "te:" in caplog.text  # Masked prefix
        assert "test@example.com" not in caplog.text  # PII not exposed

    @pytest.mark.asyncio
    async def test_failed_auth_logs_masked_email(
        self, middleware: EmailAuthMiddleware, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test failed authentication logs masked email."""
        from fastapi import HTTPException

        auth_header = self.create_basic_auth_header("test@example.com", "wrong-secret")
        scope = {
            "type": "http",
            "headers": [(b"authorization", auth_header.encode())],
        }
        receive = MagicMock()
        send = MagicMock()

        with caplog.at_level(logging.WARNING):
            with pytest.raises(HTTPException):
                await middleware(scope, receive, send)

        # Check log contains masked email, not full email
        assert "Authentication failed" in caplog.text
        assert "te:" in caplog.text  # Masked prefix
        assert "test@example.com" not in caplog.text  # PII not exposed


class TestEmailMasking:
    """Test PII masking for GDPR/CCPA compliance."""

    def test_mask_email_standard_format(self) -> None:
        """Test masking returns prefix + hash."""
        masked = EmailAuthMiddleware._mask_email("user@example.com")

        # Format: "us:12345678" (2-char prefix + 8-char hash)
        assert masked.startswith("us:")
        assert len(masked) == 11  # 2 + 1 (colon) + 8

    def test_mask_email_different_emails_different_hashes(self) -> None:
        """Test different emails produce different hashes."""
        masked1 = EmailAuthMiddleware._mask_email("user1@example.com")
        masked2 = EmailAuthMiddleware._mask_email("user2@example.com")

        assert masked1 != masked2

    def test_mask_email_same_email_same_hash(self) -> None:
        """Test same email produces consistent hash."""
        email = "user@example.com"
        masked1 = EmailAuthMiddleware._mask_email(email)
        masked2 = EmailAuthMiddleware._mask_email(email)

        # Deterministic hashing for log correlation
        assert masked1 == masked2

    def test_mask_email_single_char_email(self) -> None:
        """Test masking handles single-character emails."""
        masked = EmailAuthMiddleware._mask_email("a")

        # Single char should still be masked
        assert masked.startswith("a:")
        assert len(masked) == 10  # 1 + 1 (colon) + 8

    def test_mask_email_empty_string(self) -> None:
        """Test masking handles empty string edge case."""
        masked = EmailAuthMiddleware._mask_email("")

        # Empty prefix + hash
        assert masked.startswith(":")
        assert len(masked) == 9  # 0 + 1 (colon) + 8
