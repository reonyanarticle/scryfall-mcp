"""Common mapping definitions for internationalization.

This module defines the base structures and common mappings used across
all supported languages for the Scryfall MCP Server.
"""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict
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


# Common Scryfall search keywords that don't need translation
SCRYFALL_KEYWORDS: set[str] = {
    # Basic search syntax
    "c", "color", "ci", "id", "identity",
    "m", "mana", "cmc", "mv", "manavalue",
    "t", "type", "o", "oracle",
    "p", "power", "tou", "toughness", "loy", "loyalty",
    "r", "rarity", "s", "set", "e", "edition",
    "b", "block", "f", "format", "banned", "restricted", "legal",
    "a", "artist", "fl", "flavor", "ft", "flavortext",
    "w", "watermark", "border", "frame",
    "is", "not", "year", "date",
    "usd", "eur", "tix", "price",
    "new", "old", "reprint", "firstprint",
    "lang", "language", "foreign",

    # Operators
    "=", "!=", "<", "<=", ">", ">=",
    ":", "and", "or", "-",

    # Special values
    "multicolor", "monocolor", "colorless",
    "spell", "permanent", "historic",
    "vanilla", "french", "hybrid", "phyrexian",
    "split", "flip", "transform", "meld", "leveler",
    "commander", "partner", "companions",
    "digital", "paper", "mtgo", "arena",
    "foil", "nonfoil", "etched", "glossy",
    "promo", "booster", "unique",
    "funny", "acorn", "silver", "gold",
}

# Colors in WUBRG order (standard Magic color ordering)
MAGIC_COLORS: list[str] = ["W", "U", "B", "R", "G"]

# All Magic card types (comprehensive list)
MAGIC_TYPES: set[str] = {
    # Basic types
    "Artifact", "Creature", "Enchantment", "Instant", "Land",
    "Planeswalker", "Sorcery", "Tribal", "Conspiracy", "Phenomenon",
    "Plane", "Scheme", "Vanguard", "Dungeon", "Battle",

    # Supertypes
    "Basic", "Elite", "Host", "Legendary", "Ongoing", "Snow", "World",

    # Artifact subtypes
    "Clue", "Contraption", "Equipment", "Food", "Fortification",
    "Gold", "Treasure", "Vehicle",

    # Enchantment subtypes
    "Aura", "Background", "Cartouche", "Case", "Class", "Curse",
    "Role", "Rune", "Saga", "Shrine",

    # Land subtypes
    "Cave", "Desert", "Forest", "Gate", "Island", "Lair", "Locus",
    "Mine", "Mountain", "Plains", "Power-Plant", "Sphere", "Swamp",
    "Tower", "Urza's",

    # Planeswalker subtypes (just a few examples)
    "Ajani", "Chandra", "Jace", "Liliana", "Nissa", "Vraska",

    # Spell subtypes
    "Adventure", "Arcane", "Lesson", "Trap",
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
