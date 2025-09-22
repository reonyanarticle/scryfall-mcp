"""Pydantic models for Scryfall API responses.

This module defines data models that match the Scryfall API response format.
All models include proper typing and validation for reliable data handling.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl, field_validator


class ImageUris(BaseModel):
    """Card image URIs in different sizes."""
    
    small: Optional[HttpUrl] = None
    normal: Optional[HttpUrl] = None
    large: Optional[HttpUrl] = None
    png: Optional[HttpUrl] = None
    art_crop: Optional[HttpUrl] = None
    border_crop: Optional[HttpUrl] = None


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
    
    usd: Optional[str] = None
    usd_foil: Optional[str] = None
    usd_etched: Optional[str] = None
    eur: Optional[str] = None
    eur_foil: Optional[str] = None
    tix: Optional[str] = None
    
    @field_validator("usd", "usd_foil", "usd_etched", "eur", "eur_foil", "tix", mode="before")
    @classmethod
    def validate_price_string(cls, v: Optional[str]) -> Optional[str]:
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
    
    tcgplayer: Optional[HttpUrl] = None
    cardmarket: Optional[HttpUrl] = None
    cardhoarder: Optional[HttpUrl] = None


class RelatedUris(BaseModel):
    """Related URIs for the card."""
    
    gatherer: Optional[HttpUrl] = None
    tcgplayer_infinite_articles: Optional[HttpUrl] = None
    tcgplayer_infinite_decks: Optional[HttpUrl] = None
    edhrec: Optional[HttpUrl] = None


class CardFace(BaseModel):
    """Individual card face (for double-faced cards)."""
    
    object: str = "card_face"
    name: str
    mana_cost: Optional[str] = None
    type_line: str
    oracle_text: Optional[str] = None
    colors: Optional[list[str]] = None
    power: Optional[str] = None
    toughness: Optional[str] = None
    loyalty: Optional[str] = None
    flavor_text: Optional[str] = None
    illustration_id: Optional[UUID] = None
    image_uris: Optional[ImageUris] = None
    color_indicator: Optional[list[str]] = None


class Card(BaseModel):
    """Scryfall card object."""
    
    # Core Fields
    object: str = "card"
    id: UUID
    oracle_id: UUID
    multiverse_ids: list[int] = Field(default_factory=list)
    mtgo_id: Optional[int] = None
    mtgo_foil_id: Optional[int] = None
    tcgplayer_id: Optional[int] = None
    cardmarket_id: Optional[int] = None
    
    # Gameplay Fields
    name: str
    lang: str = "en"
    released_at: date
    uri: HttpUrl
    scryfall_uri: HttpUrl
    layout: str
    highres_image: bool = False
    image_status: str = "missing"
    image_uris: Optional[ImageUris] = None
    mana_cost: Optional[str] = None
    cmc: Optional[float] = None
    type_line: str
    oracle_text: Optional[str] = None
    colors: Optional[list[str]] = None
    color_identity: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    produced_mana: Optional[list[str]] = None
    all_parts: Optional[list[dict[str, Any]]] = None
    card_faces: Optional[list[CardFace]] = None
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
    flavor_text: Optional[str] = None
    card_back_id: Optional[UUID] = None
    artist: Optional[str] = None
    artist_ids: Optional[list[UUID]] = None
    illustration_id: Optional[UUID] = None
    border_color: str = "black"
    frame: str = "2015"
    frame_effects: Optional[list[str]] = None
    security_stamp: Optional[str] = None
    full_art: bool = False
    textless: bool = False
    booster: bool = False
    story_spotlight: bool = False
    prices: Prices
    related_uris: RelatedUris
    purchase_uris: PurchaseUris
    
    # Gameplay Fields (continued)
    power: Optional[str] = None
    toughness: Optional[str] = None
    loyalty: Optional[str] = None
    life_modifier: Optional[str] = None
    hand_modifier: Optional[str] = None
    color_indicator: Optional[list[str]] = None
    edhrec_rank: Optional[int] = None
    penny_rank: Optional[int] = None
    preview: Optional[dict[str, Any]] = None


class SearchResult(BaseModel):
    """Search result response from Scryfall."""
    
    object: str = "list"
    total_cards: int
    has_more: bool
    next_page: Optional[HttpUrl] = None
    data: list[Card]
    warnings: Optional[list[str]] = None
    
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
    warnings: Optional[list[str]] = None
    details: Optional[str] = None


class Set(BaseModel):
    """Scryfall set object."""
    
    object: str = "set"
    id: UUID
    code: str
    mtgo_code: Optional[str] = None
    arena_code: Optional[str] = None
    tcgplayer_id: Optional[int] = None
    name: str
    set_type: str
    released_at: Optional[date] = None
    block_code: Optional[str] = None
    block: Optional[str] = None
    parent_set_code: Optional[str] = None
    card_count: int
    printed_size: Optional[int] = None
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
    uri: HttpUrl
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
    note: Optional[str] = None


# Response type unions
ScryfallResponse = Union[
    Card,
    SearchResult,
    Set,
    Ruling,
    Catalog,
    BulkData,
    Migration,
    ScryfallError
]