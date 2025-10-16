"""Centralized Pydantic models for Scryfall MCP Server.

All BaseModel-based data models should be defined in this module.
This ensures consistent validation and type safety across the application.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator
from typing_extensions import TypedDict

# ============================================================================
# Search Models (from search/models.py)
# ============================================================================


class ParsedQuery(BaseModel):
    """Parsed natural language query with extracted entities."""

    original_text: str
    normalized_text: str
    intent: str
    entities: dict[str, list[str]]
    language: str


class BuiltQuery(BaseModel):
    """Built Scryfall query with metadata."""

    scryfall_query: str
    original_query: str
    suggestions: list[str]
    query_metadata: dict[str, Any]


class SearchOptions(BaseModel):
    """Search presentation options.

    Attributes
    ----------
    max_results : int
        Maximum number of results to return (default: 10).
        Reduced from 20 to prevent BrokenPipeError with large responses.
        Users can override to request up to 175 results.
    format_filter : str | None
        Optional format filter (e.g., "standard", "modern")
    language : str | None
        Optional language code for search (e.g., "en", "ja")
    use_annotations : bool
        Whether to use MCP Annotations for content (default: True)
    include_keywords : bool
        Include keyword abilities in output (default: True)
    include_artist : bool
        Include artist information in output (default: True)
    include_mana_production : bool
        Include mana production for lands (default: True)

    Notes
    -----
    Image data is not included in responses to comply with MCP ImageContent spec.
    Image URLs are provided in Scryfall links within card details.
    """

    max_results: int = 10  # Reduced from 20 to prevent pipe overflow
    format_filter: str | None = None
    language: str | None = None

    # Display control parameters
    use_annotations: bool = True
    include_keywords: bool = True
    include_artist: bool = True
    include_mana_production: bool = True

    # Opt-in legalities information
    include_legalities: bool = False


# ============================================================================
# Tool Request Models (from tools/search.py)
# ============================================================================


class SearchCardsRequest(BaseModel):
    """Request model for card search.

    Note
    ----
    max_results defaults to 10 (reduced from 20) to prevent BrokenPipeError
    on macOS systems with 16KB pipe buffer limits. Users can override up to 175.
    Image data is not included in responses to comply with MCP ImageContent spec
    (requires base64, not URLs). Image links are provided in card details instead.
    """

    query: str = Field(description="Natural language search query (supports Japanese)")
    language: str | None = Field(default=None, description="Language code (ja, en)")
    max_results: int | None = Field(
        default=10, ge=1, le=175, description="Maximum number of results"
    )
    format_filter: str | None = Field(
        default=None, description="Filter by Magic format (standard, modern, etc.)"
    )

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
        default=False, description="Include format legalities (legal/banned/restricted only)"
    )


class AutocompleteRequest(BaseModel):
    """Request model for card name autocomplete."""

    query: str = Field(description="Partial card name")
    language: str | None = Field(default=None, description="Language code (ja, en)")


# ============================================================================
# Cache Models (from cache/backends.py)
# ============================================================================


class CacheEntry(BaseModel):
    """Cache entry with metadata."""

    value: Any
    expires_at: float | None = None
    created_at: float

    def is_expired(self) -> bool:
        """Check if the entry has expired."""
        import time

        if self.expires_at is None:
            return False
        return time.time() > self.expires_at


# ============================================================================
# Internationalization Models (from i18n/locales.py and i18n/mappings/common.py)
# ============================================================================


class ColorMapping(TypedDict):
    """Color name to Scryfall color code mapping."""

    white: str
    blue: str
    black: str
    red: str
    green: str
    colorless: str


class TypeMapping(TypedDict):
    """Card type translations."""

    # Basic types
    artifact: str
    creature: str
    enchantment: str
    instant: str
    land: str
    planeswalker: str
    sorcery: str

    # Supertypes
    basic: str
    legendary: str
    snow: str

    # Common subtypes
    equipment: str
    aura: str
    vehicle: str
    token: str


class OperatorMapping(TypedDict):
    """Search operator translations."""

    equals: str
    not_equals: str
    less_than: str
    less_than_or_equal: str
    greater_than: str
    greater_than_or_equal: str
    contains: str
    not_contains: str


class FormatMapping(TypedDict):
    """Magic format names."""

    standard: str
    pioneer: str
    modern: str
    legacy: str
    vintage: str
    commander: str
    pauper: str
    historic: str
    alchemy: str
    brawl: str


class RarityMapping(TypedDict):
    """Rarity translations."""

    common: str
    uncommon: str
    rare: str
    mythic: str
    special: str
    bonus: str


class SetTypeMapping(TypedDict):
    """Set type translations."""

    core: str
    expansion: str
    masters: str
    draft_innovation: str
    commander: str
    planechase: str
    archenemy: str
    from_the_vault: str
    premium_deck: str
    duel_deck: str
    starter: str
    box: str
    promo: str
    token: str
    memorabilia: str
    treasure_chest: str
    spellbook: str
    arsenal: str


class LanguageMapping(BaseModel):
    """Base class for language-specific mappings."""

    # Metadata
    language_code: str
    language_name: str
    locale_code: str

    # Core mappings
    colors: ColorMapping
    types: TypeMapping
    operators: OperatorMapping
    formats: FormatMapping
    rarities: RarityMapping
    set_types: SetTypeMapping

    # Search terms
    search_keywords: dict[str, str]

    # Common phrases
    phrases: dict[str, str]

    model_config = ConfigDict(validate_assignment=True)


class TranslationProtocol(Protocol):
    """Protocol for translation providers."""

    def translate_to_english(self, text: str, from_lang: str) -> str:
        """Translate text to English."""
        ...

    def translate_from_english(self, text: str, to_lang: str) -> str:
        """Translate text from English."""
        ...

    def detect_language(self, text: str) -> str:
        """Detect the language of text."""
        ...


class LocaleInfo(BaseModel):
    """Information about a locale."""

    code: str
    language: str
    language_code: str
    country: str | None = None
    country_code: str | None = None
    encoding: str | None = None
    is_default: bool = False
    is_fallback: bool = False

    @field_validator("code")
    @classmethod
    def validate_locale_code(cls, v: str) -> str:
        """Validate locale code format."""
        if not v or len(v) < 2:
            raise ValueError("Invalid locale code")
        return v.lower()


# ============================================================================
# Scryfall API Models (from api/models.py)
# ============================================================================


class ImageUris(BaseModel):
    """Card image URIs in different sizes."""

    small: HttpUrl | None = None
    normal: HttpUrl | None = None
    large: HttpUrl | None = None
    png: HttpUrl | None = None
    art_crop: HttpUrl | None = None
    border_crop: HttpUrl | None = None


class Legalities(BaseModel):
    """Card format legalities."""

    standard: str = "not_legal"
    future: str = "not_legal"
    historic: str = "not_legal"
    gladiator: str = "not_legal"
    pioneer: str = "not_legal"
    explorer: str = "not_legal"
    modern: str = "not_legal"
    legacy: str = "not_legal"
    pauper: str = "not_legal"
    vintage: str = "not_legal"
    penny: str = "not_legal"
    commander: str = "not_legal"
    oathbreaker: str = "not_legal"
    brawl: str = "not_legal"
    historicbrawl: str = "not_legal"
    alchemy: str = "not_legal"
    paupercommander: str = "not_legal"
    duel: str = "not_legal"
    oldschool: str = "not_legal"
    premodern: str = "not_legal"
    predh: str = "not_legal"


class Prices(BaseModel):
    """Card pricing information."""

    usd: str | None = None
    usd_foil: str | None = None
    usd_etched: str | None = None
    eur: str | None = None
    eur_foil: str | None = None
    tix: str | None = None

    @field_validator(
        "usd", "usd_foil", "usd_etched", "eur", "eur_foil", "tix", mode="before"
    )
    @classmethod
    def validate_price_string(cls, v: str | None) -> str | None:
        """Validate price strings."""
        if v is None:
            return v
        if isinstance(v, str) and v.strip() == "":
            return None
        try:
            Decimal(str(v))
            return v
        except (ValueError, TypeError, Exception):
            return None


class PurchaseUris(BaseModel):
    """Purchase links for the card."""

    tcgplayer: HttpUrl | None = None
    cardmarket: HttpUrl | None = None
    cardhoarder: HttpUrl | None = None


class RelatedUris(BaseModel):
    """Related URIs for the card."""

    gatherer: HttpUrl | None = None
    tcgplayer_infinite_articles: HttpUrl | None = None
    tcgplayer_infinite_decks: HttpUrl | None = None
    edhrec: HttpUrl | None = None


class CardFace(BaseModel):
    """Individual card face (for double-faced cards)."""

    object: str = "card_face"
    name: str
    mana_cost: str | None = None
    type_line: str
    oracle_text: str | None = None
    colors: list[str] | None = None
    power: str | None = None
    toughness: str | None = None
    loyalty: str | None = None
    flavor_text: str | None = None
    illustration_id: UUID | None = None
    image_uris: ImageUris | None = None
    color_indicator: list[str] | None = None


class Card(BaseModel):
    """Scryfall card object."""

    # Core Fields
    object: str = "card"
    id: UUID
    oracle_id: UUID
    multiverse_ids: list[int] = Field(default_factory=list)
    mtgo_id: int | None = None
    mtgo_foil_id: int | None = None
    tcgplayer_id: int | None = None
    cardmarket_id: int | None = None

    # Gameplay Fields
    name: str
    lang: str = "en"
    released_at: date
    uri: HttpUrl
    scryfall_uri: HttpUrl
    layout: str
    highres_image: bool = False
    image_status: str = "missing"
    image_uris: ImageUris | None = None
    mana_cost: str | None = None
    cmc: float | None = None
    type_line: str
    oracle_text: str | None = None
    colors: list[str] | None = None
    color_identity: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    produced_mana: list[str] | None = None
    all_parts: list[dict[str, Any]] | None = None
    card_faces: list[CardFace] | None = None
    legalities: Legalities
    games: list[str] = Field(default_factory=list)
    reserved: bool = False
    foil: bool = False
    nonfoil: bool = True
    finishes: list[str] = Field(default_factory=list)
    oversized: bool = False
    promo: bool = False
    reprint: bool = False
    variation: bool = False
    set_id: UUID
    set: str
    set_name: str
    set_type: str
    set_uri: HttpUrl
    set_search_uri: HttpUrl
    scryfall_set_uri: HttpUrl
    rulings_uri: HttpUrl
    prints_search_uri: HttpUrl
    collector_number: str
    digital: bool = False
    rarity: str
    flavor_text: str | None = None
    card_back_id: UUID | None = None
    artist: str | None = None
    artist_ids: list[UUID] | None = None
    illustration_id: UUID | None = None
    border_color: str = "black"
    frame: str = "2015"
    frame_effects: list[str] | None = None
    security_stamp: str | None = None
    full_art: bool = False
    textless: bool = False
    booster: bool = False
    story_spotlight: bool = False
    prices: Prices
    related_uris: RelatedUris
    purchase_uris: PurchaseUris

    # Gameplay Fields (continued)
    power: str | None = None
    toughness: str | None = None
    loyalty: str | None = None
    life_modifier: str | None = None
    hand_modifier: str | None = None
    color_indicator: list[str] | None = None
    edhrec_rank: int | None = None
    penny_rank: int | None = None
    preview: dict[str, Any] | None = None

    # Multilingual Fields
    # These fields contain the card information as printed in non-English languages
    printed_name: str | None = None
    printed_type_line: str | None = None
    printed_text: str | None = None


class SearchResult(BaseModel):
    """Search result response from Scryfall."""

    object: str = "list"
    total_cards: int
    has_more: bool
    next_page: HttpUrl | None = None
    data: list[Card]
    warnings: list[str] | None = None

    @field_validator("data")
    @classmethod
    def validate_cards(cls, v: list[Card]) -> list[Card]:
        """Validate that all items in data are Card objects."""
        return v


class ScryfallError(BaseModel):
    """Scryfall API error response."""

    object: str = "error"
    code: str
    status: int
    warnings: list[str] | None = None
    details: str | None = None


class Set(BaseModel):
    """Scryfall set object."""

    object: str = "set"
    id: UUID
    code: str
    mtgo_code: str | None = None
    arena_code: str | None = None
    tcgplayer_id: int | None = None
    name: str
    set_type: str
    released_at: date | None = None
    block_code: str | None = None
    block: str | None = None
    parent_set_code: str | None = None
    card_count: int
    printed_size: int | None = None
    digital: bool = False
    foil_only: bool = False
    nonfoil_only: bool = False
    scryfall_uri: HttpUrl
    uri: HttpUrl
    icon_svg_uri: HttpUrl
    search_uri: HttpUrl


class Ruling(BaseModel):
    """Card ruling object."""

    object: str = "ruling"
    oracle_id: UUID
    source: str
    published_at: date
    comment: str


class Catalog(BaseModel):
    """Catalog response for various game data."""

    object: str = "catalog"
    uri: HttpUrl | None = None
    total_values: int
    data: list[str]


class BulkData(BaseModel):
    """Bulk data download information."""

    object: str = "bulk_data"
    id: UUID
    type: str
    updated_at: datetime
    uri: HttpUrl
    name: str
    description: str
    size: int
    download_uri: HttpUrl
    content_type: str = "application/json"
    content_encoding: str = "gzip"


class Migration(BaseModel):
    """Card migration information."""

    object: str = "migration"
    id: UUID
    uri: HttpUrl
    performed_at: datetime
    migration_strategy: str
    old_scryfall_id: UUID
    new_scryfall_id: UUID
    note: str | None = None


# Response type unions
ScryfallResponse = (
    Card | SearchResult | Set | Ruling | Catalog | BulkData | Migration | ScryfallError
)
