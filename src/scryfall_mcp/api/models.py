"""Pydantic models for Scryfall API responses.

This module defines data models that match the Scryfall API response format.
All models include proper typing and validation for reliable data handling.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl, field_validator


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

    @field_validator("usd", "usd_foil", "usd_etched", "eur", "eur_foil", "tix", mode="before")
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
    Card
    | SearchResult
    | Set
    | Ruling
    | Catalog
    | BulkData
    | Migration
    | ScryfallError
)
