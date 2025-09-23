"""Tests for settings module."""

from __future__ import annotations

import os

import pytest
from pydantic import ValidationError

from scryfall_mcp.settings import Settings, get_settings, reload_settings


class TestSettings:
    """Test the Settings class."""

    def test_default_settings(self):
        """Test default settings values."""
        settings = Settings()

        assert settings.scryfall_base_url == "https://api.scryfall.com"
        assert settings.scryfall_rate_limit_ms == 100
        assert settings.scryfall_timeout_seconds == 30
        assert settings.scryfall_max_retries == 5
        assert settings.cache_enabled is True
        assert settings.cache_backend == "memory"
        assert settings.default_locale == "en"
        assert settings.supported_locales == ["en", "ja"]
        assert settings.fallback_locale == "en"
        assert settings.default_currency == "USD"
        assert settings.debug is False

    def test_environment_variable_override(self):
        """Test that environment variables override defaults."""
        env_vars = {
            "SCRYFALL_MCP_SCRYFALL_RATE_LIMIT_MS": "200",
            "SCRYFALL_MCP_CACHE_ENABLED": "false",
            "SCRYFALL_MCP_DEFAULT_LOCALE": "ja",
            "SCRYFALL_MCP_DEBUG": "true",
        }

        # Set environment variables
        for key, value in env_vars.items():
            os.environ[key] = value

        try:
            settings = Settings()
            assert settings.scryfall_rate_limit_ms == 200
            assert settings.cache_enabled is False
            assert settings.default_locale == "ja"
            assert settings.debug is True
        finally:
            # Clean up environment variables
            for key in env_vars:
                os.environ.pop(key, None)

    def test_validation_errors(self):
        """Test that validation errors are raised for invalid values."""
        # Test invalid rate limit (too low)
        with pytest.raises(ValidationError):
            Settings(scryfall_rate_limit_ms=50)

        # Test invalid rate limit (too high)
        with pytest.raises(ValidationError):
            Settings(scryfall_rate_limit_ms=1500)

        # Test invalid cache backend
        with pytest.raises(ValidationError):
            Settings(cache_backend="invalid")

        # Test invalid locale format
        with pytest.raises(ValidationError):
            Settings(default_locale="invalid")

        # Test invalid currency format
        with pytest.raises(ValidationError):
            Settings(default_currency="invalid")

    def test_locale_validation(self):
        """Test locale validation logic."""
        # Test valid locales
        settings = Settings(
            supported_locales=["en", "ja", "fr"],
            default_locale="ja",
            fallback_locale="en",
        )
        assert settings.default_locale == "ja"
        assert settings.fallback_locale == "en"

        # Test default locale not in supported locales
        with pytest.raises(ValidationError):
            Settings(
                supported_locales=["en", "ja"],
                default_locale="fr",
            )

        # Test fallback locale not in supported locales
        with pytest.raises(ValidationError):
            Settings(
                supported_locales=["en", "ja"],
                fallback_locale="fr",
            )

    def test_currency_validation(self):
        """Test currency validation logic."""
        # Test valid currencies
        settings = Settings(
            supported_currencies=["USD", "JPY", "EUR"],
            default_currency="JPY",
        )
        assert settings.default_currency == "JPY"

        # Test default currency not in supported currencies
        with pytest.raises(ValidationError):
            Settings(
                supported_currencies=["USD", "JPY"],
                default_currency="EUR",
            )

    def test_ttl_settings(self):
        """Test TTL settings validation."""
        settings = Settings(
            cache_ttl_search=3600,
            cache_ttl_card=7200,
            cache_ttl_price=1800,
            cache_ttl_set=86400,
        )

        assert settings.cache_ttl_search == 3600
        assert settings.cache_ttl_card == 7200
        assert settings.cache_ttl_price == 1800
        assert settings.cache_ttl_set == 86400

        # Test minimum TTL values
        with pytest.raises(ValidationError):
            Settings(cache_ttl_search=30)  # Too low

        with pytest.raises(ValidationError):
            Settings(cache_ttl_card=1800)  # Too low

    def test_circuit_breaker_settings(self):
        """Test circuit breaker settings validation."""
        settings = Settings(
            circuit_breaker_failure_threshold=10,
            circuit_breaker_recovery_timeout=120,
        )

        assert settings.circuit_breaker_failure_threshold == 10
        assert settings.circuit_breaker_recovery_timeout == 120

        # Test validation ranges
        with pytest.raises(ValidationError):
            Settings(circuit_breaker_failure_threshold=0)

        with pytest.raises(ValidationError):
            Settings(circuit_breaker_failure_threshold=25)

        with pytest.raises(ValidationError):
            Settings(circuit_breaker_recovery_timeout=5)

        with pytest.raises(ValidationError):
            Settings(circuit_breaker_recovery_timeout=400)

    def test_get_settings_singleton(self):
        """Test that get_settings returns the same instance."""
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2

    def test_reload_settings(self):
        """Test settings reload functionality."""
        # Get initial settings
        initial_settings = get_settings()
        initial_debug = initial_settings.debug

        # Set environment variable
        os.environ["SCRYFALL_MCP_DEBUG"] = str(not initial_debug).lower()

        try:
            # Reload settings
            reloaded_settings = reload_settings()

            # Check that settings were reloaded
            assert reloaded_settings.debug != initial_debug
            assert get_settings() is reloaded_settings
        finally:
            # Clean up
            os.environ.pop("SCRYFALL_MCP_DEBUG", None)
            reload_settings()  # Reset to defaults


class TestSettingsIntegration:
    """Integration tests for settings."""

    def test_settings_with_test_fixture(self, test_settings):
        """Test settings work with test fixture."""
        assert test_settings.debug is True
        assert test_settings.mock_api is True
        assert test_settings.cache_backend == "memory"

    def test_redis_settings(self):
        """Test Redis-specific settings."""
        settings = Settings(
            cache_backend="redis",
            redis_url="redis://localhost:6379/0",
            redis_db=5,
        )

        assert settings.cache_backend == "redis"
        assert settings.redis_url == "redis://localhost:6379/0"
        assert settings.redis_db == 5

        # Test Redis DB validation
        with pytest.raises(ValidationError):
            Settings(redis_db=-1)

        with pytest.raises(ValidationError):
            Settings(redis_db=16)

    def test_supported_locales_validation(self):
        """Test comprehensive locale validation."""
        # Test valid locale codes
        valid_locales = ["en", "ja", "fr", "de", "es", "it", "pt", "ru", "ko", "zh"]
        settings = Settings(supported_locales=valid_locales)
        assert settings.supported_locales == valid_locales

        # Test invalid locale codes
        with pytest.raises(ValidationError):
            Settings(supported_locales=["en", "invalid"])

        with pytest.raises(ValidationError):
            Settings(supported_locales=["en", "ENG"])  # Must be lowercase

        with pytest.raises(ValidationError):
            Settings(supported_locales=["en", "e"])  # Too short

    def test_supported_currencies_validation(self):
        """Test comprehensive currency validation."""
        # Test valid currency codes
        valid_currencies = ["USD", "EUR", "JPY", "GBP", "CAD", "AUD", "CHF", "CNY"]
        settings = Settings(supported_currencies=valid_currencies)
        assert settings.supported_currencies == valid_currencies

        # Test invalid currency codes
        with pytest.raises(ValidationError):
            Settings(supported_currencies=["USD", "invalid"])

        with pytest.raises(ValidationError):
            Settings(supported_currencies=["USD", "usd"])  # Must be uppercase

        with pytest.raises(ValidationError):
            Settings(supported_currencies=["USD", "US"])  # Too short
