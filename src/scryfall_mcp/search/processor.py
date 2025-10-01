"""Natural language processing for search queries.

This module provides natural language understanding capabilities
for Magic: The Gathering card searches, with special focus on Japanese.
"""

from __future__ import annotations

import re
from typing import Any

from ..i18n import get_current_mapping, LanguageMapping
from .builder import QueryBuilder
from .parser import SearchParser
from .models import ParsedQuery, BuiltQuery


class SearchProcessor:
    """Orchestrates the search pipeline: Parser → QueryBuilder → (Presenter handled separately)."""

    def __init__(self, locale_mapping: LanguageMapping | None = None) -> None:
        """Initialize the search processor.

        Parameters
        ----------
        locale_mapping : LanguageMapping, optional
            Language-specific mappings. If None, uses current locale mapping.
        """
        self._mapping = locale_mapping or get_current_mapping()
        self._parser = SearchParser(self._mapping)
        self._query_builder = QueryBuilder(self._mapping)

    def process_query(self, text: str, locale: str | None = None) -> dict[str, Any]:
        """Process a natural language search query through the pipeline.

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
        # Update mapping if locale changed
        if locale and locale != self._mapping.language_code:
            from ..i18n import get_locale_manager
            manager = get_locale_manager()
            self._mapping = manager.get_mapping(locale)
            self._parser = SearchParser(self._mapping)
            self._query_builder = QueryBuilder(self._mapping)

        # Parse the natural language query
        parsed = self._parser.parse(text)

        # Build the Scryfall query
        built = self._query_builder.build(parsed)

        # Return structured result for backward compatibility
        return {
            "original_query": built.original_query,
            "scryfall_query": built.scryfall_query,
            "detected_intent": parsed.intent,
            "extracted_entities": parsed.entities,
            "suggestions": built.suggestions,
            "language": parsed.language,
            "query_metadata": built.query_metadata,
        }

    def process_with_pipeline(self, text: str) -> tuple[ParsedQuery, BuiltQuery]:
        """Process query and return structured pipeline results.

        Parameters
        ----------
        text : str
            Natural language search text

        Returns
        -------
        tuple[ParsedQuery, BuiltQuery]
            Parsed query and built query for use with presenter
        """
        parsed = self._parser.parse(text)
        built = self._query_builder.build(parsed)
        return parsed, built

    def _detect_intent(self, text: str) -> str:
        """Legacy method for backward compatibility.

        Parameters
        ----------
        text : str
            Input text

        Returns
        -------
        str
            Detected intent
        """
        parsed = self._parser.parse(text)
        return parsed.intent

    def _extract_entities(self, text: str) -> dict[str, list[str]]:
        """Legacy method for backward compatibility.

        Parameters
        ----------
        text : str
            Input text

        Returns
        -------
        dict
            Extracted entities by category
        """
        parsed = self._parser.parse(text)
        return parsed.entities

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
        parsed = self._parser.parse(text)
        return self._parser.suggest_improvements(parsed)

    def validate_query(self, query: str) -> tuple[bool, list[str]]:
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
        return self._parser.validate_syntax(query)

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
        color_matches = re.findall(r"c:([wubrgc]+)", query, re.IGNORECASE)
        type_matches = re.findall(r"t:(\w+)", query, re.IGNORECASE)
        power_matches = re.findall(r"p([<>=!]+)(\d+)", query, re.IGNORECASE)
        toughness_matches = re.findall(r"tou([<>=!]+)(\d+)", query, re.IGNORECASE)
        mana_matches = re.findall(r"(mv|cmc)([<>=!]+)(\d+)", query, re.IGNORECASE)

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
                    "planeswalker": "プレインズウォーカー",
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
