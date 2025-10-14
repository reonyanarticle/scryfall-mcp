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

# ============================================================================
# Card Label Translations (for presenter formatting)
# ============================================================================

CARD_LABELS: dict[str, dict[str, str]] = {
    "ja": {
        "type": "タイプ",
        "mana_cost": "マナコスト",
        "power_toughness": "パワー/タフネス",
        "loyalty": "忠誠度",
        "oracle_text": "効果",
        "flavor_text": "フレーバーテキスト",
        "set": "セット",
        "rarity": "レアリティ",
        "artist": "アーティスト",
        "collector_number": "コレクター番号",
        "view_on_scryfall": "Scryfallで詳細を見る",
        "search_results": "検索結果",
        "showing_results": "件中",
        "total_results": "件を表示",
        "of": "の",
    },
    "en": {
        "type": "Type",
        "mana_cost": "Mana Cost",
        "power_toughness": "Power/Toughness",
        "loyalty": "Loyalty",
        "oracle_text": "Oracle Text",
        "flavor_text": "Flavor Text",
        "set": "Set",
        "rarity": "Rarity",
        "artist": "Artist",
        "collector_number": "Collector Number",
        "view_on_scryfall": "View on Scryfall",
        "search_results": "Search Results",
        "showing_results": "Showing",
        "total_results": "results",
        "of": "of",
    },
}

# ============================================================================
# Ability Pattern Matching Constants (Phase 2)
# ============================================================================

# Pattern to match color/type/keyword ability keywords (stops pattern matching before these)
ABILITY_COLOR_TYPE_PATTERN = r"(?:白い|白の|青い|青の|黒い|黒の|赤い|赤の|緑い|緑の|無色の|無色|クリーチャー|インスタント|ソーサリー|アーティファクト|エンチャント|飛行|速攻|接死|トランプル|警戒|絆魂|呪禁|到達|威迫|瞬速|先制攻撃|二段攻撃)"

# Known effect phrases for Phase 2 pattern matching
ABILITY_KNOWN_EFFECTS: dict[str, str] = {
    "カードを引く": 'o:"draw"',
    "カードを1枚引く": 'o:"draw a card"',
    "カードを2枚引く": 'o:"draw two cards"',
    "破壊": 'o:"destroy"',
    "破壊する": 'o:"destroy"',
    "追放": 'o:"exile"',
    "追放する": 'o:"exile"',
    "生け贄": 'o:"sacrifice"',
    "生け贄に捧げる": 'o:"sacrifice"',
    "ライフを得る": 'o:"gain life"',
    "ライフを失う": 'o:"lose life"',
    "ダメージを与える": 'o:"deals damage"',
    "トークンを生成": 'o:"create"',
    "トークンを生成する": 'o:"create"',
}

# ============================================================================
# Query Explanation Mappings (for processor)
# ============================================================================

QUERY_EXPLANATION_MAPPINGS: dict[str, dict[str, dict[str, str]]] = {
    "ja": {
        "colors": {
            "w": "白",
            "u": "青",
            "b": "黒",
            "r": "赤",
            "g": "緑",
            "c": "無色",
        },
        "types": {
            "creature": "クリーチャー",
            "artifact": "アーティファクト",
            "enchantment": "エンチャント",
            "instant": "インスタント",
            "sorcery": "ソーサリー",
            "land": "土地",
            "planeswalker": "プレインズウォーカー",
            "legendary": "伝説の",
            "basic": "基本",
            "snow": "雪",
        },
        "operators": {
            ">=": "以上",
            "<=": "以下",
            ">": "より大きい",
            "<": "未満",
            "=": "等しい",
            ":": "含む",
        },
        "fields": {
            "mv": "マナ総量",
            "cmc": "点数で見たマナコスト",
            "pow": "パワー",
            "power": "パワー",
            "tou": "タフネス",
            "toughness": "タフネス",
            "loy": "忠誠度",
            "loyalty": "忠誠度",
        },
        "keywords": {
            "flying": "飛行",
            "haste": "速攻",
            "deathtouch": "接死",
            "trample": "トランプル",
            "vigilance": "警戒",
            "lifelink": "絆魂",
            "hexproof": "呪禁",
            "reach": "到達",
            "menace": "威迫",
            "flash": "瞬速",
        },
        "labels": {
            "colors": "色",
            "types": "タイプ",
            "power": "パワー",
            "toughness": "タフネス",
            "loyalty": "忠誠度",
            "mana_value": "マナ総量",
            "keyword": "キーワード",
            "oracle_text": "効果",
            "general_search": "一般的な検索",
        },
    },
    "en": {
        "colors": {
            "w": "W",
            "u": "U",
            "b": "B",
            "r": "R",
            "g": "G",
            "c": "C",
        },
        "types": {
            "creature": "Creature",
            "artifact": "Artifact",
            "enchantment": "Enchantment",
            "instant": "Instant",
            "sorcery": "Sorcery",
            "land": "Land",
            "planeswalker": "Planeswalker",
            "legendary": "Legendary",
            "basic": "Basic",
            "snow": "Snow",
        },
        "operators": {
            ">=": ">=",
            "<=": "<=",
            ">": ">",
            "<": "<",
            "=": "=",
            ":": "contains",
        },
        "fields": {
            "mv": "Mana Value",
            "cmc": "CMC",
            "pow": "Power",
            "power": "Power",
            "tou": "Toughness",
            "toughness": "Toughness",
            "loy": "Loyalty",
            "loyalty": "Loyalty",
        },
        "keywords": {
            "flying": "Flying",
            "haste": "Haste",
            "deathtouch": "Deathtouch",
            "trample": "Trample",
            "vigilance": "Vigilance",
            "lifelink": "Lifelink",
            "hexproof": "Hexproof",
            "reach": "Reach",
            "menace": "Menace",
            "flash": "Flash",
        },
        "labels": {
            "colors": "Colors",
            "types": "Types",
            "power": "Power",
            "toughness": "Toughness",
            "loyalty": "Loyalty",
            "mana_value": "Mana Value",
            "keyword": "Keyword",
            "oracle_text": "Oracle Text",
            "general_search": "General search",
        },
    },
}
