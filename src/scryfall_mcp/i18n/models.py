"""Internationalization data models and mapping types."""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict, field_validator
from typing_extensions import TypedDict


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
