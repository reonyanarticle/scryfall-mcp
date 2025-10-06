"""Internationalization constants and vocabularies.

This module contains static vocabularies and constants used for
internationalization and search query processing. These constants
are separated from settings.py to avoid mixing runtime configuration
with static data.
"""

from __future__ import annotations

# ============================================================================
# Scryfall Search Keywords
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

# ============================================================================
# Magic: The Gathering Constants
# ============================================================================

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

# ============================================================================
# Search Patterns
# ============================================================================

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
