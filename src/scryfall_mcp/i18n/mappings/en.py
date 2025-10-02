"""English language mappings.

This module provides the base English mappings for all Magic: The Gathering
terms and search syntax. This serves as the fallback language.
"""

from __future__ import annotations

from ...models import LanguageMapping


class EnglishMapping(LanguageMapping):
    """English language mappings for Magic: The Gathering terms."""

    def __init__(self) -> None:
        """Initialize English mappings."""
        super().__init__(
            language_code="en",
            language_name="English",
            locale_code="en_US",
            colors={
                "white": "w",
                "blue": "u",
                "black": "b",
                "red": "r",
                "green": "g",
                "colorless": "c",
            },
            types={
                # Basic types
                "artifact": "artifact",
                "creature": "creature",
                "enchantment": "enchantment",
                "instant": "instant",
                "land": "land",
                "planeswalker": "planeswalker",
                "sorcery": "sorcery",
                # Supertypes
                "basic": "basic",
                "legendary": "legendary",
                "snow": "snow",
                # Common subtypes
                "equipment": "equipment",
                "aura": "aura",
                "vehicle": "vehicle",
                "token": "token",
            },
            operators={
                "equals": "=",
                "not_equals": "!=",
                "less_than": "<",
                "less_than_or_equal": "<=",
                "greater_than": ">",
                "greater_than_or_equal": ">=",
                "contains": ":",
                "not_contains": "-",
            },
            formats={
                "standard": "standard",
                "pioneer": "pioneer",
                "modern": "modern",
                "legacy": "legacy",
                "vintage": "vintage",
                "commander": "commander",
                "pauper": "pauper",
                "historic": "historic",
                "alchemy": "alchemy",
                "brawl": "brawl",
            },
            rarities={
                "common": "common",
                "uncommon": "uncommon",
                "rare": "rare",
                "mythic": "mythic",
                "special": "special",
                "bonus": "bonus",
            },
            set_types={
                "core": "core",
                "expansion": "expansion",
                "masters": "masters",
                "draft_innovation": "draft_innovation",
                "commander": "commander",
                "planechase": "planechase",
                "archenemy": "archenemy",
                "from_the_vault": "from_the_vault",
                "premium_deck": "premium_deck",
                "duel_deck": "duel_deck",
                "starter": "starter",
                "box": "box",
                "promo": "promo",
                "token": "token",
                "memorabilia": "memorabilia",
                "treasure_chest": "treasure_chest",
                "spellbook": "spellbook",
                "arsenal": "arsenal",
            },
            search_keywords={
                # Basic search terms
                "color": "c",
                "colors": "c",
                "color_identity": "id",
                "identity": "id",
                "mana": "m",
                "mana_cost": "m",
                "converted_mana_cost": "cmc",
                "mana_value": "mv",
                "type": "t",
                "types": "t",
                "oracle": "o",
                "oracle_text": "o",
                "power": "p",
                "toughness": "tou",
                "loyalty": "loy",
                "rarity": "r",
                "set": "s",
                "edition": "e",
                "block": "b",
                "format": "f",
                "artist": "a",
                "flavor": "fl",
                "flavor_text": "ft",
                "watermark": "w",
                "year": "year",
                "price": "usd",
                "language": "lang",
                # Boolean terms
                "is": "is",
                "not": "not",
                "and": "",  # implicit in Scryfall
                "or": "or",
                # Special keywords
                "multicolor": "multicolor",
                "multicolored": "multicolor",
                "monocolored": "monocolor",
                "monocolor": "monocolor",
                "colorless": "colorless",
                "reprint": "reprint",
                "new": "new",
                "old": "old",
                "foil": "foil",
                "nonfoil": "nonfoil",
                "digital": "digital",
                "paper": "paper",
                "promo": "promo",
                "unique": "unique",
                "funny": "funny",
                "legal": "legal",
                "banned": "banned",
                "restricted": "restricted",
            },
            phrases={
                # Common search phrases
                "cards with": "",
                "cards that": "",
                "creatures with": "t:creature",
                "artifacts with": "t:artifact",
                "enchantments with": "t:enchantment",
                "instants with": "t:instant",
                "sorceries with": "t:sorcery",
                "planeswalkers with": "t:planeswalker",
                "lands with": "t:land",
                # Power/toughness
                "power equal to": "p=",
                "power greater than": "p>",
                "power less than": "p<",
                "toughness equal to": "tou=",
                "toughness greater than": "tou>",
                "toughness less than": "tou<",
                # Mana cost
                "mana cost": "m:",
                "converted mana cost": "cmc:",
                "mana value": "mv:",
                "costs": "m:",
                # Colors
                "white cards": "c:w",
                "blue cards": "c:u",
                "black cards": "c:b",
                "red cards": "c:r",
                "green cards": "c:g",
                "colorless cards": "c:c",
                # Formats
                "legal in": "f:",
                "banned in": "banned:",
                "restricted in": "restricted:",
                # Sets
                "from set": "s:",
                "in set": "s:",
                "from": "s:",
                # Text search
                "with text": "o:",
                "oracle text": "o:",
                "flavor text": "ft:",
                # Price
                "price under": "usd<",
                "price over": "usd>",
                "price exactly": "usd:",
                "costs under": "usd<",
                "costs over": "usd>",
                # Common responses
                "no results found": "No cards found matching your search.",
                "too many results": "Too many results. Please refine your search.",
                "search error": "There was an error with your search.",
                "invalid query": "Invalid search query.",
                # Card information
                "mana cost info": "Mana Cost",
                "type line": "Type",
                "oracle text info": "Oracle Text",
                "flavor text info": "Flavor Text",
                "power and toughness": "Power/Toughness",
                "loyalty": "Loyalty",
                "rarity": "Rarity",
                "set": "Set",
                "artist": "Artist",
                "collector number": "Collector Number",
                "price": "Price",
                "legalities": "Legalities",
                # Currency
                "usd": "USD",
                "eur": "EUR",
                "tix": "TIX",
                "dollars": "USD",
                "euros": "EUR",
                "tickets": "TIX",
            },
        )


# Global instance
english_mapping = EnglishMapping()
