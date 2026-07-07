"""Application-boundary request models and model façade.

Each layer owns its data models (`api/models.py`, `search/models.py`,
`i18n/models.py`, `cache/models.py`); this module keeps the MCP-facing
request models and re-exports everything for backward compatibility, so
`from scryfall_mcp.models import Card` keeps working.
"""

from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel, Field, field_validator

# --- Compatibility re-exports (explicit `as` form for mypy strict) ---
from .api.models import (
    BulkData as BulkData,
)
from .api.models import (
    Card as Card,
)
from .api.models import (
    CardFace as CardFace,
)
from .api.models import (
    Catalog as Catalog,
)
from .api.models import (
    ImageUris as ImageUris,
)
from .api.models import (
    Legalities as Legalities,
)
from .api.models import (
    Migration as Migration,
)
from .api.models import (
    Prices as Prices,
)
from .api.models import (
    PurchaseUris as PurchaseUris,
)
from .api.models import (
    RelatedUris as RelatedUris,
)
from .api.models import (
    Ruling as Ruling,
)
from .api.models import (
    ScryfallError as ScryfallError,
)
from .api.models import (
    SearchResult as SearchResult,
)
from .api.models import (
    Set as Set,
)
from .cache.models import CacheEntry as CacheEntry
from .i18n.models import (
    ColorMapping as ColorMapping,
)
from .i18n.models import (
    FormatMapping as FormatMapping,
)
from .i18n.models import (
    LanguageMapping as LanguageMapping,
)
from .i18n.models import (
    LocaleInfo as LocaleInfo,
)
from .i18n.models import (
    OperatorMapping as OperatorMapping,
)
from .i18n.models import (
    RarityMapping as RarityMapping,
)
from .i18n.models import (
    SetTypeMapping as SetTypeMapping,
)
from .i18n.models import (
    TranslationProtocol as TranslationProtocol,
)
from .i18n.models import (
    TypeMapping as TypeMapping,
)
from .search.models import (
    BuiltQuery as BuiltQuery,
)
from .search.models import (
    ParsedQuery as ParsedQuery,
)
from .search.models import (
    SearchOptions as SearchOptions,
)


class SearchCardsRequest(BaseModel):
    """Request model for card search.

    Note
    ----
    max_results defaults to 10 (reduced from 20) to prevent BrokenPipeError
    on macOS systems with 16KB pipe buffer limits. Users can override up to 175.
    Image data is not included in responses to comply with MCP ImageContent spec
    (requires base64, not URLs). Image links are provided in card details instead.
    """

    # Allowlists: these values are spliced into the Scryfall query string
    # (f:{format} / lang:{language}), so free-form input would allow search
    # operator injection. Keep in sync with https://scryfall.com/docs/api
    VALID_FORMATS: ClassVar[frozenset[str]] = frozenset(
        {
            "standard",
            "future",
            "historic",
            "timeless",
            "gladiator",
            "pioneer",
            "explorer",
            "modern",
            "legacy",
            "pauper",
            "vintage",
            "penny",
            "commander",
            "oathbreaker",
            "standardbrawl",
            "brawl",
            "alchemy",
            "paupercommander",
            "duel",
            "oldschool",
            "premodern",
            "predh",
        }
    )
    VALID_LANGUAGES: ClassVar[frozenset[str]] = frozenset(
        {
            "en",
            "es",
            "fr",
            "de",
            "it",
            "pt",
            "ja",
            "ko",
            "ru",
            "zhs",
            "zht",
            "he",
            "la",
            "grc",
            "ar",
            "sa",
            "ph",
        }
    )

    query: str = Field(description="Natural language search query (supports Japanese)")
    language: str | None = Field(default=None, description="Language code (ja, en)")
    max_results: int | None = Field(
        default=10, ge=1, le=175, description="Maximum number of results"
    )
    format_filter: str | None = Field(
        default=None, description="Filter by Magic format (standard, modern, etc.)"
    )

    @field_validator("format_filter")
    @classmethod
    def validate_format_filter(cls, value: str | None) -> str | None:
        """Validate format_filter against known Magic formats."""
        if value is None:
            return None
        normalized = value.strip().lower()
        if normalized not in cls.VALID_FORMATS:
            raise ValueError(
                f"Unknown format: {value!r}. "
                f"Valid formats: {', '.join(sorted(cls.VALID_FORMATS))}"
            )
        return normalized

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: str | None) -> str | None:
        """Validate language against Scryfall-supported language codes."""
        if value is None:
            return None
        normalized = value.strip().lower()
        if normalized not in cls.VALID_LANGUAGES:
            raise ValueError(
                f"Unknown language: {value!r}. "
                f"Valid languages: {', '.join(sorted(cls.VALID_LANGUAGES))}"
            )
        return normalized

    # Display control parameters
    use_annotations: bool = Field(
        default=True, description="Use MCP Annotations for metadata"
    )
    include_keywords: bool = Field(
        default=True, description="Include keyword abilities"
    )
    include_artist: bool = Field(default=True, description="Include artist information")
    include_mana_production: bool = Field(
        default=True, description="Include mana production for lands"
    )

    # Opt-in legalities information
    include_legalities: bool = Field(
        default=False,
        description="Include format legalities (legal/banned/restricted only)",
    )


class AutocompleteRequest(BaseModel):
    """Request model for card name autocomplete."""

    query: str = Field(description="Partial card name")
    language: str | None = Field(default=None, description="Language code (ja, en)")

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: str | None) -> str | None:
        """Validate language against Scryfall-supported language codes.

        Shares the allowlist with SearchCardsRequest so both request models
        accept the same language inputs.
        """
        if value is None:
            return None
        normalized = value.strip().lower()
        if normalized not in SearchCardsRequest.VALID_LANGUAGES:
            raise ValueError(
                f"Unknown language: {value!r}. "
                f"Valid languages: {', '.join(sorted(SearchCardsRequest.VALID_LANGUAGES))}"
            )
        return normalized


# --- Compatibility re-exports (explicit `as` form for mypy strict) ---
