"""Natural language search query parser."""

from __future__ import annotations

import re

from ..i18n import LanguageMapping
from ..models import ParsedQuery


class SearchParser:
    """Parses natural language queries and extracts structured information."""

    def __init__(self, locale_mapping: LanguageMapping) -> None:
        """Initialize the parser with locale-specific mappings.

        Parameters
        ----------
        locale_mapping : LanguageMapping
            Language-specific mappings for parsing
        """
        self._mapping = locale_mapping

    def parse(self, text: str) -> ParsedQuery:
        """Parse natural language into structured data.

        Parameters
        ----------
        text : str
            Natural language search text

        Returns
        -------
        ParsedQuery
            Parsed query with extracted entities and metadata
        """
        normalized_text = self._normalize_text(text)
        intent = self._detect_intent(text)
        entities = self._extract_entities(text)

        return ParsedQuery(
            original_text=text,
            normalized_text=normalized_text,
            intent=intent,
            entities=entities,
            language=self._mapping.language_code,
        )

    def _normalize_text(self, text: str) -> str:
        """Normalize text for processing.

        Parameters
        ----------
        text : str
            Input text

        Returns
        -------
        str
            Normalized text
        """
        # Remove extra whitespace
        text = re.sub(r"\s+", " ", text.strip())

        # Normalize smart quotes to ASCII quotes
        text = text.replace("“", '"').replace("”", '"')
        text = text.replace("‘", "'").replace("’", "'")

        return text

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
            if any(word in text for word in ["価格", "値段", "相場"]):
                return "price_inquiry"
            if any(word in text for word in ["ルール", "効果", "テキスト"]):
                return "rules_inquiry"
            if any(word in text for word in ["デッキ", "構築", "採用"]):
                return "deck_building"
        # Card search patterns
        elif any(
            phrase in text_lower for phrase in ["find", "search", "show me", "get"]
        ):
            return "card_search"
        # Price inquiry patterns
        elif any(phrase in text_lower for phrase in ["price of", "how much", "cost"]):
            return "price_inquiry"
        # Rules inquiry patterns
        elif any(
            phrase in text_lower for phrase in ["what does", "rules for", "how does"]
        ):
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
        entities: dict[str, list[str]] = {
            "colors": [],
            "types": [],
            "numbers": [],
            "card_names": [],
            "sets": [],
            "formats": [],
        }

        # Extract numbers
        numbers = re.findall(r"\d+", text)
        entities["numbers"] = numbers

        # Extract colors
        if self._mapping.language_code == "ja":
            color_mapping = {
                "白": "white",
                "青": "blue",
                "黒": "black",
                "赤": "red",
                "緑": "green",
                "無色": "colorless",
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
                "creature",
                "artifact",
                "enchantment",
                "instant",
                "sorcery",
                "land",
                "planeswalker",
            ]
            for card_type in type_words:
                if card_type in text.lower():
                    entities["types"].append(card_type)

        # Extract quoted card names
        quoted_names = re.findall(r'"([^"]+)"', text)
        entities["card_names"].extend(quoted_names)

        # Note: Unquoted Japanese card names are no longer extracted as entities
        # They remain as part of the query text and Scryfall handles them natively

        return entities

    def suggest_improvements(self, parsed: ParsedQuery) -> list[str]:
        """Suggest improvements to the search query.

        Parameters
        ----------
        parsed : ParsedQuery
            Parsed query data

        Returns
        -------
        list[str]
            List of suggested improvements
        """
        suggestions = []
        entities = parsed.entities
        text = parsed.original_text

        # Suggest more specific searches
        if not entities["colors"] and not entities["types"]:
            if self._mapping.language_code == "ja":
                suggestions.append(
                    "色やカードタイプを指定すると、より具体的な検索ができます"
                )
            else:
                suggestions.append(
                    "Try specifying colors or card types for more specific results"
                )

        # Suggest using quotes for card names (English only)
        # Note: Japanese card name suggestions removed since we no longer maintain
        # a static dictionary. Scryfall handles Japanese names natively.
        if self._mapping.language_code == "en":
            # Check for capitalized words that might be card names
            potential_names = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", text)
            for name in potential_names:
                if f'"{name}"' not in text:
                    suggestions.append(
                        f"Use quotes around '{name}' if it's a card name"
                    )

        # Suggest format restrictions for competitive queries
        if any(
            word in text.lower()
            for word in ["tournament", "competitive", "meta", "tier"]
        ):
            if self._mapping.language_code == "ja":
                suggestions.append(
                    "競技用検索には f:standard や f:modern などでフォーマットを指定してみてください"
                )
            else:
                suggestions.append(
                    "For competitive searches, try adding format restrictions like f:standard or f:modern"
                )

        return suggestions

    def validate_syntax(self, query: str) -> tuple[bool, list[str]]:
        """Validate Scryfall search query syntax.

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
        invalid_operators = re.findall(r"[<>=!]{3,}", query)
        if invalid_operators:
            if self._mapping.language_code == "ja":
                errors.append(f"無効な演算子: {', '.join(invalid_operators)}")
            else:
                errors.append(f"Invalid operators: {', '.join(invalid_operators)}")

        # Check for empty search terms
        if re.search(r":\s*($|\s)", query):
            if self._mapping.language_code == "ja":
                errors.append("空の検索条件があります")
            else:
                errors.append("Empty search terms found")

        return len(errors) == 0, errors
