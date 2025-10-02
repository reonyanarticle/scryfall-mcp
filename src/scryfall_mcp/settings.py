"""Configuration settings for Scryfall MCP Server.

This module manages environment variables and global settings for the application.
Supports multiple locales and provides secure configuration management.
"""

from __future__ import annotations

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Scryfall API Configuration
    scryfall_base_url: str = Field(
        default="https://api.scryfall.com",
        description="Base URL for Scryfall API",
    )
    scryfall_rate_limit_ms: int = Field(
        default=100,
        ge=75,
        le=1000,
        description="Rate limit interval in milliseconds (75-1000ms)",
    )
    scryfall_timeout_seconds: int = Field(
        default=30,
        ge=5,
        le=120,
        description="HTTP request timeout in seconds",
    )
    scryfall_max_retries: int = Field(
        default=5,
        ge=0,
        le=10,
        description="Maximum number of retry attempts",
    )

    # HTTP Headers
    user_agent: str = Field(
        default="Scryfall-MCP-Server/0.1.0 (contact@example.com)",
        description="User-Agent header for API requests",
    )
    accept_header: str = Field(
        default="application/json;q=0.9,*/*;q=0.8",
        description="Accept header for API requests",
    )

    # Cache Configuration
    cache_enabled: bool = Field(
        default=True,
        description="Enable/disable caching system",
    )
    cache_backend: str = Field(
        default="memory",
        pattern="^(memory|redis|composite)$",
        description="Cache backend type: memory, redis, or composite",
    )
    cache_max_size: int = Field(
        default=1000,
        ge=100,
        le=10000,
        description="Maximum cache entries for memory backend",
    )

    # Redis Configuration (if using redis backend)
    cache_redis_url: str | None = Field(
        default=None,
        description="Redis connection URL",
    )
    redis_db: int = Field(
        default=0,
        ge=0,
        le=15,
        description="Redis database number",
    )

    # Cache TTL Settings (in seconds)
    cache_ttl_search: int = Field(
        default=1800,  # 30 minutes
        ge=60,
        description="TTL for search results",
    )
    cache_ttl_card: int = Field(
        default=86400,  # 24 hours
        ge=3600,
        description="TTL for card details",
    )
    cache_ttl_price: int = Field(
        default=21600,  # 6 hours
        ge=300,
        description="TTL for price information",
    )
    cache_ttl_set: int = Field(
        default=604800,  # 1 week
        ge=86400,
        description="TTL for set information",
    )
    cache_ttl_default: int = Field(
        default=3600,  # 1 hour
        ge=300,
        description="Default TTL for cached items",
    )

    # Internationalization
    default_locale: str = Field(
        default="en",
        pattern="^[a-z]{2}$",
        description="Default locale (ISO 639-1 code)",
    )
    supported_locales: list[str] = Field(
        default=["en", "ja"],
        description="List of supported locales",
    )
    fallback_locale: str = Field(
        default="en",
        pattern="^[a-z]{2}$",
        description="Fallback locale when translation is not available",
    )

    # Currency and Pricing
    default_currency: str = Field(
        default="USD",
        pattern="^[A-Z]{3}$",
        description="Default currency code (ISO 4217)",
    )
    supported_currencies: list[str] = Field(
        default=["USD", "JPY", "EUR", "GBP"],
        description="List of supported currencies",
    )

    # Circuit Breaker Configuration
    circuit_breaker_failure_threshold: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of failures before opening circuit",
    )
    circuit_breaker_recovery_timeout: int = Field(
        default=60,
        ge=10,
        le=300,
        description="Circuit breaker recovery timeout in seconds",
    )

    # Logging
    log_level: str = Field(
        default="INFO",
        pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$",
        description="Logging level",
    )
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log message format",
    )

    # Development Settings
    debug: bool = Field(
        default=False,
        description="Enable debug mode",
    )
    mock_api: bool = Field(
        default=False,
        description="Use mock API responses for testing",
    )

    @field_validator("supported_locales")
    @classmethod
    def validate_supported_locales(cls, v: list[str]) -> list[str]:
        """Validate that all supported locales are valid ISO 639-1 codes."""
        import re

        pattern = re.compile(r"^[a-z]{2}$")
        for locale in v:
            if not pattern.match(locale):
                raise ValueError(f"Invalid locale code: {locale}")
        return v

    @field_validator("supported_currencies")
    @classmethod
    def validate_supported_currencies(cls, v: list[str]) -> list[str]:
        """Validate that all supported currencies are valid ISO 4217 codes."""
        import re

        pattern = re.compile(r"^[A-Z]{3}$")
        for currency in v:
            if not pattern.match(currency):
                raise ValueError(f"Invalid currency code: {currency}")
        return v

    @model_validator(mode="after")
    def validate_locale_currency_consistency(self) -> Settings:
        """Ensure default locales and currencies are in their supported lists."""
        # Validate default locale
        if self.supported_locales and self.default_locale not in self.supported_locales:
            raise ValueError(
                f"Default locale {self.default_locale} not in supported locales {self.supported_locales}"
            )

        # Validate fallback locale
        if (
            self.supported_locales
            and self.fallback_locale not in self.supported_locales
        ):
            raise ValueError(
                f"Fallback locale {self.fallback_locale} not in supported locales {self.supported_locales}"
            )

        # Validate default currency
        if (
            self.supported_currencies
            and self.default_currency not in self.supported_currencies
        ):
            raise ValueError(
                f"Default currency {self.default_currency} not in supported currencies {self.supported_currencies}"
            )

        return self

    model_config = SettingsConfigDict(
        env_prefix="SCRYFALL_MCP_",
        case_sensitive=False,
        validate_assignment=True,
    )


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the global settings instance.

    Returns
    -------
    Settings
        The configured settings instance
    """
    return settings


def reload_settings() -> Settings:
    """Reload settings from environment variables.

    Returns
    -------
    Settings
        The reloaded settings instance
    """
    global settings
    settings = Settings()
    return settings


# ============================================================================
# Internationalization Constants (from i18n/mappings/common.py)
# ============================================================================

# Common Scryfall search keywords that don't need translation
SCRYFALL_KEYWORDS: set[str] = {
    # Basic search syntax
    "c",
    "color",
    "ci",
    "id",
    "identity",
    "m",
    "mana",
    "cmc",
    "mv",
    "manavalue",
    "t",
    "type",
    "o",
    "oracle",
    "p",
    "power",
    "tou",
    "toughness",
    "loy",
    "loyalty",
    "r",
    "rarity",
    "s",
    "set",
    "e",
    "edition",
    "b",
    "block",
    "f",
    "format",
    "banned",
    "restricted",
    "legal",
    "a",
    "artist",
    "fl",
    "flavor",
    "ft",
    "flavortext",
    "w",
    "watermark",
    "border",
    "frame",
    "is",
    "not",
    "year",
    "date",
    "usd",
    "eur",
    "tix",
    "price",
    "new",
    "old",
    "reprint",
    "firstprint",
    "lang",
    "language",
    "foreign",
    # Operators
    "=",
    "!=",
    "<",
    "<=",
    ">",
    ">=",
    ":",
    "and",
    "or",
    "-",
    # Special values
    "multicolor",
    "monocolor",
    "colorless",
    "spell",
    "permanent",
    "historic",
    "vanilla",
    "french",
    "hybrid",
    "phyrexian",
    "split",
    "flip",
    "transform",
    "meld",
    "leveler",
    "commander",
    "partner",
    "companions",
    "digital",
    "paper",
    "mtgo",
    "arena",
    "foil",
    "nonfoil",
    "etched",
    "glossy",
    "promo",
    "booster",
    "unique",
    "funny",
    "acorn",
    "silver",
    "gold",
}

# Colors in WUBRG order (standard Magic color ordering)
MAGIC_COLORS: list[str] = ["W", "U", "B", "R", "G"]

# All Magic card types (comprehensive list)
MAGIC_TYPES: set[str] = {
    # Basic types
    "Artifact",
    "Creature",
    "Enchantment",
    "Instant",
    "Land",
    "Planeswalker",
    "Sorcery",
    "Tribal",
    "Conspiracy",
    "Phenomenon",
    "Plane",
    "Scheme",
    "Vanguard",
    "Dungeon",
    "Battle",
    # Supertypes
    "Basic",
    "Elite",
    "Host",
    "Legendary",
    "Ongoing",
    "Snow",
    "World",
    # Artifact subtypes
    "Clue",
    "Contraption",
    "Equipment",
    "Food",
    "Fortification",
    "Gold",
    "Treasure",
    "Vehicle",
    # Enchantment subtypes
    "Aura",
    "Background",
    "Cartouche",
    "Case",
    "Class",
    "Curse",
    "Role",
    "Rune",
    "Saga",
    "Shrine",
    # Land subtypes
    "Cave",
    "Desert",
    "Forest",
    "Gate",
    "Island",
    "Lair",
    "Locus",
    "Mine",
    "Mountain",
    "Plains",
    "Power-Plant",
    "Sphere",
    "Swamp",
    "Tower",
    "Urza's",
    # Planeswalker subtypes (just a few examples)
    "Ajani",
    "Chandra",
    "Jace",
    "Liliana",
    "Nissa",
    "Vraska",
    # Spell subtypes
    "Adventure",
    "Arcane",
    "Lesson",
    "Trap",
}

# Common search patterns that need special handling
SEARCH_PATTERNS: dict[str, str] = {
    # Mana cost patterns
    "mana_cost_pattern": r"\{[WUBRGCXYZ0-9]+\}",
    "hybrid_mana_pattern": r"\{[WUBRG]/[WUBRGCP]\}",
    "phyrexian_mana_pattern": r"\{[WUBRG]/P\}",
    # Numeric patterns
    "number_pattern": r"\d+",
    "comparison_pattern": r"[<>=!]+",
    # Text patterns
    "quoted_text_pattern": r'"[^"]*"',
    "card_name_pattern": r"![^!]*!",
}
