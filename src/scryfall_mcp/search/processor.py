"""Natural language processing for search queries.

This module provides natural language understanding capabilities
for Magic: The Gathering card searches, with special focus on Japanese.
"""

from __future__ import annotations

import re
from typing import Any

from ..i18n import LanguageMapping, get_current_mapping
from ..models import BuiltQuery, ParsedQuery
from .builder import QueryBuilder
from .parser import SearchParser


class SearchProcessor:
    """Orchestrates the search pipeline: Parser → QueryBuilder → (Presenter handled separately)."""

    def __init__(self, locale_mapping: LanguageMapping | None = None) -> None:
        """Initialize the search processor.

        Parameters
        ----------
        locale_mapping : LanguageMapping | None, optional (default: None)
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
        locale : str | None, optional (default: None)
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
        from ..i18n.constants import QUERY_EXPLANATION_MAPPINGS

        mappings = QUERY_EXPLANATION_MAPPINGS[self._mapping.language_code]
        parts = []

        # Parse different parts of the query
        color_matches = re.findall(r"c:([wubrgc]+)", query, re.IGNORECASE)
        type_matches = re.findall(r"t:(\w+)", query, re.IGNORECASE)
        power_matches = re.findall(r"p([<>=!]+)(\d+)", query, re.IGNORECASE)
        toughness_matches = re.findall(r"tou([<>=!]+)(\d+)", query, re.IGNORECASE)
        mana_matches = re.findall(r"(mv|cmc)([<>=!]+)(\d+)", query, re.IGNORECASE)

        # Colors
        if color_matches:
            colors = [
                mappings["colors"].get(c, c) for match in color_matches for c in match
            ]
            parts.append(f"{mappings['labels']['colors']}: {', '.join(colors)}")

        # Types
        if type_matches:
            types = [mappings["types"].get(t.lower(), t) for t in type_matches]
            parts.append(f"{mappings['labels']['types']}: {', '.join(types)}")

        # Format based on language (Japanese has no spaces, English has spaces)
        is_japanese = self._mapping.language_code == "ja"

        # Power
        if power_matches:
            for op, val in power_matches:
                op_name = mappings["operators"].get(op, op)
                if is_japanese:
                    parts.append(f"{mappings['labels']['power']}{val}{op_name}")
                else:
                    parts.append(f"{mappings['labels']['power']} {op_name} {val}")

        # Toughness
        if toughness_matches:
            for op, val in toughness_matches:
                op_name = mappings["operators"].get(op, op)
                if is_japanese:
                    parts.append(f"{mappings['labels']['toughness']}{val}{op_name}")
                else:
                    parts.append(f"{mappings['labels']['toughness']} {op_name} {val}")

        # Mana value
        if mana_matches:
            for field, op, val in mana_matches:
                field_name = mappings["fields"].get(field, field)
                op_name = mappings["operators"].get(op, op)
                if is_japanese:
                    parts.append(f"{field_name}{val}{op_name}")
                else:
                    parts.append(f"{field_name} {op_name} {val}")

        separator = "、" if self._mapping.language_code == "ja" else ", "
        return separator.join(parts) if parts else mappings["labels"]["general_search"]
