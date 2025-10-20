"""Integration tests for JWT validation middleware."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock

import pytest
from jose import jwt

from scryfall_mcp.auth.middleware import JWTValidationMiddleware
from scryfall_mcp.settings import Settings


class TestJWTValidationMiddlewareIntegration:
    """Test JWT middleware integration with ASGI."""

    @pytest.fixture
    def settings(self) -> Settings:
        """Create test settings with JWT configuration."""
        return Settings(
            oauth_enabled=True,
            jwt_secret_key="test-secret-key-minimum-32-characters-required",
            jwt_algorithm="HS256",
            oauth_client_id="test_client",
            oauth_authorization_url="https://auth.test.com/authorize",
            oauth_token_url="https://auth.test.com/token",
        )

    @pytest.fixture
    def mock_app(self) -> AsyncMock:
        """Create mock ASGI app."""
        return AsyncMock()

    @pytest.fixture
    def middleware(self, mock_app: AsyncMock, settings: Settings) -> JWTValidationMiddleware:
        """Create middleware instance with mock app."""
        return JWTValidationMiddleware(mock_app, settings)

    def create_test_token(
        self,
        settings: Settings,
        user_id: str = "test_user",
        exp_offset: int = 3600,
    ) -> str:
        """Create a test JWT token.

        Parameters
        ----------
        settings : Settings
            Settings instance with JWT configuration
        user_id : str, optional
            User ID to include in token (default: "test_user")
        exp_offset : int, optional
            Expiration offset in seconds from now (default: 3600)

        Returns
        -------
        str
            Encoded JWT token
        """
        now = int(time.time())
        payload = {
            "sub": user_id,
            "iat": now,
            "exp": now + exp_offset,
            "nbf": now,
        }
        return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    @pytest.mark.asyncio
    async def test_middleware_call_with_valid_token(
        self,
        middleware: JWTValidationMiddleware,
        mock_app: AsyncMock,
        settings: Settings,
    ) -> None:
        """Test full middleware execution with valid JWT token."""
        # Create valid token
        token = self.create_test_token(settings, user_id="test_user_123")

        # Create ASGI scope with token
        scope = {
            "type": "http",
            "headers": [(b"authorization", f"Bearer {token}".encode())],
        }

        # Mock receive/send
        receive = AsyncMock()
        send = AsyncMock()

        # Execute middleware
        await middleware(scope, receive, send)

        # Verify user payload was added to scope
        assert "user" in scope
        assert scope["user"]["sub"] == "test_user_123"
        assert "iat" in scope["user"]
        assert "exp" in scope["user"]

        # Verify app was called with modified scope
        mock_app.assert_called_once_with(scope, receive, send)

    @pytest.mark.asyncio
    async def test_middleware_call_with_non_http_scope(
        self,
        middleware: JWTValidationMiddleware,
        mock_app: AsyncMock,
    ) -> None:
        """Test middleware bypasses non-HTTP requests."""
        # Create WebSocket scope (non-HTTP)
        scope = {
            "type": "websocket",
            "headers": [],
        }

        # Mock receive/send
        receive = AsyncMock()
        send = AsyncMock()

        # Execute middleware
        await middleware(scope, receive, send)

        # Verify user payload was NOT added (no validation)
        assert "user" not in scope

        # Verify app was called without modification
        mock_app.assert_called_once_with(scope, receive, send)

    @pytest.mark.asyncio
    async def test_middleware_call_with_invalid_token(
        self,
        middleware: JWTValidationMiddleware,
        mock_app: AsyncMock,
        settings: Settings,
    ) -> None:
        """Test middleware rejects invalid JWT token."""
        from fastapi import HTTPException

        # Create token with wrong secret
        wrong_settings = Settings(
            oauth_enabled=True,
            jwt_secret_key="wrong-secret-key-different-32chars",
            jwt_algorithm="HS256",
            oauth_client_id="test",
            oauth_authorization_url="https://test.com/auth",
            oauth_token_url="https://test.com/token",
        )
        invalid_token = self.create_test_token(wrong_settings)

        # Create ASGI scope with invalid token
        scope = {
            "type": "http",
            "headers": [(b"authorization", f"Bearer {invalid_token}".encode())],
        }

        receive = AsyncMock()
        send = AsyncMock()

        # Execute middleware - should raise exception
        with pytest.raises(HTTPException) as exc_info:
            await middleware(scope, receive, send)

        # Verify 401 Unauthorized
        assert exc_info.value.status_code == 401

        # Verify app was NOT called
        mock_app.assert_not_called()

    @pytest.mark.asyncio
    async def test_validate_jwt_from_scope_integration(
        self,
        middleware: JWTValidationMiddleware,
        settings: Settings,
    ) -> None:
        """Test combined token extraction and validation."""
        # Create valid token
        token = self.create_test_token(settings, user_id="integration_user")

        # Create scope with token
        scope = {
            "type": "http",
            "headers": [(b"authorization", f"Bearer {token}".encode())],
        }

        # Execute validation
        payload = await middleware._validate_jwt_from_scope(scope)

        # Verify payload
        assert payload["sub"] == "integration_user"
        assert "iat" in payload
        assert "exp" in payload
        assert "nbf" in payload
