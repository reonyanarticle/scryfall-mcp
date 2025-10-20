"""Tests for Settings validators - JWT and CORS security validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from scryfall_mcp.settings import Settings


class TestJWTProductionRequirements:
    """Test JWT production requirements validator."""

    def test_jwt_requirements_enabled_with_valid_secret(self) -> None:
        """Test OAuth enabled with valid JWT secret."""
        settings = Settings(
            oauth_enabled=True,
            jwt_secret_key="x" * 32,  # 32 characters
            oauth_client_id="test_client",
            oauth_authorization_url="https://auth.test.com/authorize",
            oauth_token_url="https://auth.test.com/token",
        )

        assert settings.oauth_enabled is True
        assert len(settings.jwt_secret_key) == 32

    def test_jwt_requirements_enabled_without_secret(self) -> None:
        """Test OAuth enabled but no JWT secret raises error."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                oauth_enabled=True,
                jwt_secret_key="",  # Empty secret
                oauth_client_id="test_client",
                oauth_authorization_url="https://auth.test.com/authorize",
                oauth_token_url="https://auth.test.com/token",
            )

        # Verify error message
        error_msg = str(exc_info.value)
        assert "jwt_secret_key is required" in error_msg
        assert "oauth_enabled=True" in error_msg

    def test_jwt_requirements_short_secret(self) -> None:
        """Test JWT secret < 32 characters raises error."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                oauth_enabled=True,
                jwt_secret_key="short",  # Only 5 characters
                oauth_client_id="test_client",
                oauth_authorization_url="https://auth.test.com/authorize",
                oauth_token_url="https://auth.test.com/token",
            )

        error_msg = str(exc_info.value)
        assert "at least 32 characters" in error_msg

    def test_jwt_requirements_disabled(self) -> None:
        """Test OAuth disabled (JWT secret not required)."""
        settings = Settings(
            oauth_enabled=False,
            jwt_secret_key="",  # Empty is OK when OAuth disabled
        )

        assert settings.oauth_enabled is False
        assert settings.jwt_secret_key == ""


class TestOAuthConfiguration:
    """Test OAuth configuration validator."""

    def test_oauth_configuration_complete(self) -> None:
        """Test OAuth enabled with all required configuration."""
        settings = Settings(
            oauth_enabled=True,
            jwt_secret_key="x" * 32,
            oauth_client_id="test_client_123",
            oauth_authorization_url="https://auth.provider.com/oauth/authorize",
            oauth_token_url="https://auth.provider.com/oauth/token",
        )

        assert settings.oauth_client_id == "test_client_123"
        assert settings.oauth_authorization_url == "https://auth.provider.com/oauth/authorize"
        assert settings.oauth_token_url == "https://auth.provider.com/oauth/token"

    def test_oauth_configuration_missing_client_id(self) -> None:
        """Test OAuth enabled but client_id missing raises error."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                oauth_enabled=True,
                jwt_secret_key="x" * 32,
                oauth_client_id="",  # Missing
                oauth_authorization_url="https://auth.test.com/authorize",
                oauth_token_url="https://auth.test.com/token",
            )

        error_msg = str(exc_info.value)
        assert "oauth_client_id is required" in error_msg

    def test_oauth_configuration_missing_authorization_url(self) -> None:
        """Test OAuth enabled but authorization_url missing raises error."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                oauth_enabled=True,
                jwt_secret_key="x" * 32,
                oauth_client_id="test_client",
                oauth_authorization_url="",  # Missing
                oauth_token_url="https://auth.test.com/token",
            )

        error_msg = str(exc_info.value)
        assert "oauth_authorization_url is required" in error_msg

    def test_oauth_configuration_missing_token_url(self) -> None:
        """Test OAuth enabled but token_url missing raises error."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                oauth_enabled=True,
                jwt_secret_key="x" * 32,
                oauth_client_id="test_client",
                oauth_authorization_url="https://auth.test.com/authorize",
                oauth_token_url="",  # Missing
            )

        error_msg = str(exc_info.value)
        assert "oauth_token_url is required" in error_msg


class TestCORSProductionRequirements:
    """Test CORS production requirements validator."""

    def test_cors_requirements_http_with_origins(self) -> None:
        """Test HTTP transport with specific origins."""
        settings = Settings(
            transport_mode="http",
            allowed_origins=["https://app.example.com", "https://claude.ai"],
        )

        assert settings.transport_mode == "http"
        assert len(settings.allowed_origins) == 2
        assert "https://app.example.com" in settings.allowed_origins

    def test_cors_requirements_http_without_origins(self) -> None:
        """Test HTTP transport but no allowed_origins raises error."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                transport_mode="http",
                allowed_origins=[],  # Empty
            )

        error_msg = str(exc_info.value)
        assert "allowed_origins is required" in error_msg
        assert "HTTP transport" in error_msg

    def test_cors_requirements_streamable_http_without_origins(self) -> None:
        """Test streamable_http transport without origins raises error."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                transport_mode="streamable_http",
                allowed_origins=[],
            )

        error_msg = str(exc_info.value)
        assert "allowed_origins is required" in error_msg

    def test_cors_requirements_wildcard_in_production(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test CORS validator warns about wildcard in production."""
        import logging

        caplog.set_level(logging.WARNING)

        Settings(
            transport_mode="http",
            allowed_origins=["*"],
            debug=False,  # Production mode
        )

        # Verify warning was logged
        assert "SECURITY WARNING" in caplog.text
        assert "CORS wildcard '*'" in caplog.text
        assert "insecure in production" in caplog.text

    def test_cors_requirements_wildcard_in_debug(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test CORS wildcard allowed in debug mode without warning."""
        import logging

        caplog.set_level(logging.WARNING)

        Settings(
            transport_mode="http",
            allowed_origins=["*"],
            debug=True,  # Debug mode
        )

        # Verify NO warning was logged
        assert "SECURITY WARNING" not in caplog.text

    def test_cors_requirements_stdio_mode_no_validation(self) -> None:
        """Test stdio transport mode doesn't require CORS configuration."""
        settings = Settings(
            transport_mode="stdio",
            allowed_origins=[],  # Empty is OK for stdio
        )

        assert settings.transport_mode == "stdio"
        assert len(settings.allowed_origins) == 0
