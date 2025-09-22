"""Natural language processing for search queries.

This module provides natural language understanding capabilities
for Magic: The Gathering card searches, with special focus on Japanese.
"""

from __future__ import annotations

import re
from typing import Optional, Set, Tuple

from .builder import QueryBuilder
from ..i18n import get_current_mapping


class SearchProcessor:
    """Processes natural language search queries."""

    def __init__(self) -> None:
        """Initialize the search processor."""
        self._mapping = get_current_mapping()
        self._query_builder = QueryBuilder()

    def process_query(self, text: str, locale: Optional[str] = None) -> dict[str, str]:
        """Process a natural language search query.

        Parameters
        ----------
        text : str
            Natural language search text
        locale : str, optional
            Locale code for language-specific processing

        Returns
        -------
        dict
            Processing results with query and metadata
        """
        if locale and locale != self._mapping.language_code:
            # Update mapping if locale changed
            from ..i18n import get_locale_manager
            manager = get_locale_manager()
            self._mapping = manager.get_mapping(locale)

        # Detect query intent and structure
        intent = self._detect_intent(text)
        entities = self._extract_entities(text)

        # Build the Scryfall query
        scryfall_query = self._query_builder.build_query(text, locale)

        # Get suggestions for improvements
        suggestions = self._query_builder.suggest_corrections(text)

        return {
            "original_query": text,
            "scryfall_query": scryfall_query,
            "detected_intent": intent,
            "extracted_entities": entities,
            "suggestions": suggestions,
            "language": self._mapping.language_code,
        }

    def _detect_intent(self, text: str) -> str:
        """Detect the intent of the search query.

        Parameters
        ----------
        text : str
            Input text

        Returns
        -------
        str
            Detected intent
        """
        text_lower = text.lower()

        # Card search intents
        if self._mapping.language_code == "ja":
            if any(word in text for word in ["探して", "検索", "見つけて", "カード"]):
                return "card_search"
            elif any(word in text for word in ["価格", "値段", "相場"]):
                return "price_inquiry"
            elif any(word in text for word in ["ルール", "効果", "テキスト"]):
                return "rules_inquiry"
            elif any(word in text for word in ["デッキ", "構築", "採用"]):
                return "deck_building"
        else:
            # Card search patterns
            if any(phrase in text_lower for phrase in ["find", "search", "show me", "get"]):
                return "card_search"
            # Price inquiry patterns
            elif any(phrase in text_lower for phrase in ["price of", "how much", "cost"]):
                return "price_inquiry"
            # Rules inquiry patterns
            elif any(phrase in text_lower for phrase in ["what does", "rules for", "how does"]):
                return "rules_inquiry"
            # Deck building patterns
            elif any(phrase in text_lower for phrase in ["deck with", "build a deck"]):
                return "deck_building"

        return "general_search"

    def _extract_entities(self, text: str) -> dict[str, list[str]]:
        """Extract entities from the search query.

        Parameters
        ----------
        text : str
            Input text

        Returns
        -------
        dict
            Extracted entities by category
        """
        entities = {
            "colors": [],
            "types": [],
            "numbers": [],
            "card_names": [],
            "sets": [],
            "formats": [],
        }

        # Extract numbers
        numbers = re.findall(r'\d+', text)
        entities["numbers"] = numbers

        # Extract colors
        if self._mapping.language_code == "ja":
            color_mapping = {
                "白": "white", "青": "blue", "黒": "black",
                "赤": "red", "緑": "green", "無色": "colorless"
            }
            for ja_color, en_color in color_mapping.items():
                if ja_color in text:
                    entities["colors"].append(en_color)
        else:
            color_words = ["white", "blue", "black", "red", "green", "colorless"]
            for color in color_words:
                if color in text.lower():
                    entities["colors"].append(color)

        # Extract card types
        if self._mapping.language_code == "ja":
            type_mapping = {
                "クリーチャー": "creature",
                "アーティファクト": "artifact",
                "エンチャント": "enchantment",
                "インスタント": "instant",
                "ソーサリー": "sorcery",
                "土地": "land",
                "プレインズウォーカー": "planeswalker",
            }
            for ja_type, en_type in type_mapping.items():
                if ja_type in text:
                    entities["types"].append(en_type)
        else:
            type_words = [
                "creature", "artifact", "enchantment", "instant",
                "sorcery", "land", "planeswalker"
            ]
            for card_type in type_words:
                if card_type in text.lower():
                    entities["types"].append(card_type)

        # Extract quoted card names
        quoted_names = re.findall(r'"([^"]+)"', text)
        entities["card_names"].extend(quoted_names)

        # Extract potential card names from Japanese mapping
        if self._mapping.language_code == "ja":
            from ..i18n import JAPANESE_CARD_NAMES
            for ja_name in JAPANESE_CARD_NAMES:
                if ja_name in text:
                    entities["card_names"].append(JAPANESE_CARD_NAMES[ja_name])

        return entities

    def suggest_query_improvements(self, text: str) -> list[str]:
        """Suggest improvements to the search query.

        Parameters
        ----------
        text : str
            Original search query

        Returns
        -------
        list[str]
            List of suggested improvements
        """
        suggestions = []

        entities = self._extract_entities(text)

        # Suggest more specific searches
        if not entities["colors"] and not entities["types"]:
            if self._mapping.language_code == "ja":
                suggestions.append("色やカードタイプを指定すると、より具体的な検索ができます")
            else:
                suggestions.append("Try specifying colors or card types for more specific results")

        # Suggest using quotes for card names
        if self._mapping.language_code == "ja":
            # Check for potential card names without quotes
            from ..i18n import JAPANESE_CARD_NAMES
            for ja_name in JAPANESE_CARD_NAMES:
                if ja_name in text and f'"{ja_name}"' not in text:
                    suggestions.append(f"カード名'{ja_name}'は引用符で囲むと正確に検索できます")
        else:
            # Check for capitalized words that might be card names
            potential_names = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
            for name in potential_names:
                if f'"{name}"' not in text:
                    suggestions.append(f"Use quotes around '{name}' if it's a card name")

        # Suggest format restrictions for competitive queries
        if any(word in text.lower() for word in ["tournament", "competitive", "meta", "tier"]):
            if self._mapping.language_code == "ja":
                suggestions.append("競技用検索には f:standard や f:modern などでフォーマットを指定してみてください")
            else:
                suggestions.append("For competitive searches, try adding format restrictions like f:standard or f:modern")

        return suggestions

    def validate_query(self, query: str) -> Tuple[bool, list[str]]:
        """Validate a Scryfall search query.

        Parameters
        ----------
        query : str
            Scryfall search query to validate

        Returns
        -------
        tuple[bool, list[str]]
            (is_valid, list_of_errors)
        """
        errors = []

        # Check for basic syntax errors
        if query.count('"') % 2 != 0:
            if self._mapping.language_code == "ja":
                errors.append("引用符が正しく閉じられていません")
            else:
                errors.append("Unmatched quotes in query")

        # Check for invalid operators
        invalid_operators = re.findall(r'[<>=!]{3,}', query)
        if invalid_operators:
            if self._mapping.language_code == "ja":
                errors.append(f"無効な演算子: {', '.join(invalid_operators)}")
            else:
                errors.append(f"Invalid operators: {', '.join(invalid_operators)}")

        # Check for empty search terms
        if re.search(r':\s*($|\s)', query):
            if self._mapping.language_code == "ja":
                errors.append("空の検索条件があります")
            else:
                errors.append("Empty search terms found")

        return len(errors) == 0, errors

    def get_query_explanation(self, query: str) -> str:
        """Get an explanation of what a Scryfall query does.

        Parameters
        ----------
        query : str
            Scryfall search query

        Returns
        -------
        str
            Human-readable explanation
        """
        parts = []

        # Parse different parts of the query
        color_matches = re.findall(r'c:([wubrgc]+)', query, re.IGNORECASE)
        type_matches = re.findall(r't:(\w+)', query, re.IGNORECASE)
        power_matches = re.findall(r'p([<>=!]+)(\d+)', query, re.IGNORECASE)
        toughness_matches = re.findall(r'tou([<>=!]+)(\d+)', query, re.IGNORECASE)
        mana_matches = re.findall(r'(mv|cmc)([<>=!]+)(\d+)', query, re.IGNORECASE)

        if self._mapping.language_code == "ja":
            if color_matches:
                color_names = {"w": "白", "u": "青", "b": "黒", "r": "赤", "g": "緑", "c": "無色"}
                colors = [color_names.get(c, c) for match in color_matches for c in match]
                parts.append(f"色: {', '.join(colors)}")

            if type_matches:
                type_names = {
                    "creature": "クリーチャー", "artifact": "アーティファクト",
                    "enchantment": "エンチャント", "instant": "インスタント",
                    "sorcery": "ソーサリー", "land": "土地",
                    "planeswalker": "プレインズウォーカー"
                }
                types = [type_names.get(t.lower(), t) for t in type_matches]
                parts.append(f"タイプ: {', '.join(types)}")

            if power_matches:
                for op, val in power_matches:
                    op_name = {">=": "以上", "<=": "以下", ">": "より大きい", "<": "未満", "=": "等しい"}.get(op, op)
                    parts.append(f"パワー{val}{op_name}")

            if toughness_matches:
                for op, val in toughness_matches:
                    op_name = {">=": "以上", "<=": "以下", ">": "より大きい", "<": "未満", "=": "等しい"}.get(op, op)
                    parts.append(f"タフネス{val}{op_name}")

            if mana_matches:
                for field, op, val in mana_matches:
                    field_name = {"mv": "マナ総量", "cmc": "点数で見たマナコスト"}.get(field, field)
                    op_name = {">=": "以上", "<=": "以下", ">": "より大きい", "<": "未満", "=": "等しい"}.get(op, op)
                    parts.append(f"{field_name}{val}{op_name}")

            return "、".join(parts) if parts else "一般的な検索"

        else:
            if color_matches:
                colors = [c.upper() for match in color_matches for c in match]
                parts.append(f"Colors: {', '.join(colors)}")

            if type_matches:
                parts.append(f"Types: {', '.join(type_matches)}")

            if power_matches:
                for op, val in power_matches:
                    parts.append(f"Power {op} {val}")

            if toughness_matches:
                for op, val in toughness_matches:
                    parts.append(f"Toughness {op} {val}")

            if mana_matches:
                for field, op, val in mana_matches:
                    field_name = {"mv": "Mana Value", "cmc": "CMC"}.get(field, field.upper())
                    parts.append(f"{field_name} {op} {val}")

            return ", ".join(parts) if parts else "General search"