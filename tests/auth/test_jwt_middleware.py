"""Tests for JWT validation middleware."""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest
from jose import jwt

# Skip all tests if fastapi is not installed
pytest.importorskip("fastapi")

from scryfall_mcp.auth.middleware import JWTValidationMiddleware
from scryfall_mcp.settings import Settings


class TestJWTValidationMiddleware:
    """Test JWT validation middleware."""

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
    def middleware(self, settings: Settings) -> JWTValidationMiddleware:
        """Create middleware instance."""
        mock_app = MagicMock()
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
        return jwt.encode(
            payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
        )

    def test_extract_bearer_token_success(
        self, middleware: JWTValidationMiddleware, settings: Settings
    ) -> None:
        """Test successful bearer token extraction."""
        token = "test_token_123"
        scope = {
            "type": "http",
            "headers": [(b"authorization", f"Bearer {token}".encode())],
        }

        extracted = middleware._extract_bearer_token(scope)
        assert extracted == token

    def test_extract_bearer_token_missing_header(
        self, middleware: JWTValidationMiddleware
    ) -> None:
        """Test extraction fails when Authorization header is missing."""
        from fastapi import HTTPException

        scope = {"type": "http", "headers": []}

        with pytest.raises(HTTPException) as exc_info:
            middleware._extract_bearer_token(scope)

        assert exc_info.value.status_code == 401
        assert "Authorization" in exc_info.value.detail

    def test_extract_bearer_token_invalid_format(
        self, middleware: JWTValidationMiddleware
    ) -> None:
        """Test extraction fails with invalid auth header format."""
        from fastapi import HTTPException

        scope = {
            "type": "http",
            "headers": [(b"authorization", b"Basic invalid_format")],
        }

        with pytest.raises(HTTPException) as exc_info:
            middleware._extract_bearer_token(scope)

        assert exc_info.value.status_code == 401

    def test_decode_valid_token(
        self, middleware: JWTValidationMiddleware, settings: Settings
    ) -> None:
        """Test decoding a valid JWT token."""
        token = self.create_test_token(settings, user_id="user123")

        payload = middleware._decode_and_verify_token(token)

        assert payload["sub"] == "user123"
        assert "iat" in payload
        assert "exp" in payload

    def test_decode_expired_token(
        self, middleware: JWTValidationMiddleware, settings: Settings
    ) -> None:
        """Test decoding an expired token raises exception."""
        from fastapi import HTTPException

        token = self.create_test_token(settings, exp_offset=-3600)  # Expired 1 hour ago

        with pytest.raises(HTTPException) as exc_info:
            middleware._decode_and_verify_token(token)

        assert exc_info.value.status_code == 401
        assert "Invalid token" in exc_info.value.detail

    def test_decode_invalid_signature(
        self, middleware: JWTValidationMiddleware, settings: Settings
    ) -> None:
        """Test decoding token with invalid signature."""
        from fastapi import HTTPException

        # Create token with wrong secret
        wrong_settings = Settings(
            oauth_enabled=True,
            jwt_secret_key="wrong-secret-key-different-32chars",
            jwt_algorithm="HS256",
            oauth_client_id="test_client",
            oauth_authorization_url="https://auth.test.com/authorize",
            oauth_token_url="https://auth.test.com/token",
        )
        token = self.create_test_token(wrong_settings)

        with pytest.raises(HTTPException) as exc_info:
            middleware._decode_and_verify_token(token)

        assert exc_info.value.status_code == 401
