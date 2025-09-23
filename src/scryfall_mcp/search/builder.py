"""Query builder for Scryfall search syntax.

This module provides functionality to build and convert search queries
from natural language (especially Japanese) to Scryfall search syntax.
"""

from __future__ import annotations

import re
from typing import Any

from ..i18n import JAPANESE_CARD_NAMES, get_current_mapping


class QueryBuilder:
    """Builds Scryfall search queries from natural language input."""

    def __init__(self) -> None:
        """Initialize the query builder."""
        self._mapping = get_current_mapping()

    def build_query(self, text: str, locale: str | None = None) -> str:
        """Build a Scryfall query from natural language text.

        Parameters
        ----------
        text : str
            Natural language search text
        locale : str, optional
            Locale code for language-specific processing

        Returns
        -------
        str
            Scryfall search query
        """
        if locale and locale != self._mapping.language_code:
            # Update mapping if locale changed
            from ..i18n import get_locale_manager
            manager = get_locale_manager()
            self._mapping = manager.get_mapping(locale)

        # Clean and normalize the input
        normalized_text = self._normalize_text(text)

        # Process the text through various conversion steps
        query = self._convert_basic_terms(normalized_text)
        query = self._convert_colors(query)
        query = self._convert_types(query)
        query = self._convert_operators(query)
        query = self._convert_card_names(query)
        query = self._convert_phrases(query)
        query = self._clean_query(query)

        return query

    def _normalize_text(self, text: str) -> str:
        """Normalize input text.

        Parameters
        ----------
        text : str
            Raw input text

        Returns
        -------
        str
            Normalized text
        """
        # Remove extra whitespace
        text = re.sub(r"\s+", " ", text.strip())

        # Handle Japanese specific normalizations
        if self._mapping.language_code == "ja":
            # Convert full-width numbers to half-width
            text = self._convert_fullwidth_numbers(text)

            # Convert full-width operators to half-width
            text = text.replace("＝", "=").replace("！", "!")
            text = text.replace("（", "(").replace("）", ")")
            text = text.replace("［", "[").replace("］", "]")

        return text

    def _convert_fullwidth_numbers(self, text: str) -> str:
        """Convert full-width numbers to half-width.

        Parameters
        ----------
        text : str
            Text with potential full-width numbers

        Returns
        -------
        str
            Text with half-width numbers
        """
        fullwidth_to_halfwidth = {
            "０": "0", "１": "1", "２": "2", "３": "3", "４": "4",
            "５": "5", "６": "6", "７": "7", "８": "8", "９": "9",
        }

        for fw, hw in fullwidth_to_halfwidth.items():
            text = text.replace(fw, hw)

        return text

    def _convert_basic_terms(self, text: str) -> str:
        """Convert basic search terms.

        Parameters
        ----------
        text : str
            Input text

        Returns
        -------
        str
            Text with converted basic terms
        """
        for term, scryfall_term in self._mapping.search_keywords.items():
            if scryfall_term:  # Only replace if there's a mapping
                # Use word boundaries for exact matches
                pattern = rf"\b{re.escape(term)}\b"
                text = re.sub(pattern, scryfall_term, text, flags=re.IGNORECASE)

        return text

    def _convert_colors(self, text: str) -> str:
        """Convert color references.

        Parameters
        ----------
        text : str
            Input text

        Returns
        -------
        str
            Text with converted colors
        """
        # Handle Japanese color patterns
        if self._mapping.language_code == "ja":
            # Pattern: "白いクリーチャー" -> "c:w t:creature"
            color_creature_pattern = r"(白|青|黒|赤|緑|無色)い?の?(クリーチャー|アーティファクト|エンチャント|インスタント|ソーサリー|土地|プレインズウォーカー)"

            def replace_color_type(match: Any) -> str:
                color_ja, type_ja = match.groups()
                color_code = {
                    "白": "w", "青": "u", "黒": "b", "赤": "r", "緑": "g", "無色": "c",
                }.get(color_ja, "")

                type_code = {
                    "クリーチャー": "creature",
                    "アーティファクト": "artifact",
                    "エンチャント": "enchantment",
                    "インスタント": "instant",
                    "ソーサリー": "sorcery",
                    "土地": "land",
                    "プレインズウォーカー": "planeswalker",
                }.get(type_ja, "")

                return f"c:{color_code} t:{type_code}"

            text = re.sub(color_creature_pattern, replace_color_type, text)

        return text

    def _convert_types(self, text: str) -> str:
        """Convert card type references.

        Parameters
        ----------
        text : str
            Input text

        Returns
        -------
        str
            Text with converted types
        """
        # This is handled partially in _convert_colors for Japanese
        # Additional type-only conversions can be added here
        return text

    def _convert_operators(self, text: str) -> str:
        """Convert comparison operators.

        Parameters
        ----------
        text : str
            Input text

        Returns
        -------
        str
            Text with converted operators
        """
        if self._mapping.language_code == "ja":
            # Handle Japanese numeric comparisons
            # Pattern: "パワーが3以上" -> "p>=3"
            power_pattern = r"パワーが?(\d+)(以上|以下|より大きい|未満|と?等しい)?"

            def replace_power(match: Any) -> str:
                number, operator_ja = match.groups()
                operator = {
                    "以上": ">=",
                    "以下": "<=",
                    "より大きい": ">",
                    "未満": "<",
                    "等しい": "=",
                    "と等しい": "=",
                }.get(operator_ja or "等しい", "=")

                return f"p{operator}{number}"

            text = re.sub(power_pattern, replace_power, text)

            # Similar for toughness
            toughness_pattern = r"タフネスが?(\d+)(以上|以下|より大きい|未満|と?等しい)?"

            def replace_toughness(match: Any) -> str:
                number, operator_ja = match.groups()
                operator = {
                    "以上": ">=",
                    "以下": "<=",
                    "より大きい": ">",
                    "未満": "<",
                    "等しい": "=",
                    "と等しい": "=",
                }.get(operator_ja or "等しい", "=")

                return f"tou{operator}{number}"

            text = re.sub(toughness_pattern, replace_toughness, text)

            # Mana cost patterns
            mana_pattern = r"(マナ総量|点数で見たマナコスト|マナコスト)が?(\d+)(以上|以下|より大きい|未満|と?等しい)?"

            def replace_mana(match: Any) -> str:
                cost_type, number, operator_ja = match.groups()

                field = "mv"  # Default to mana value
                if cost_type == "点数で見たマナコスト":
                    field = "cmc"
                elif cost_type == "マナコスト":
                    field = "m"

                operator = {
                    "以上": ">=",
                    "以下": "<=",
                    "より大きい": ">",
                    "未満": "<",
                    "等しい": "=",
                    "と等しい": "=",
                }.get(operator_ja or "等しい", "=")

                return f"{field}{operator}{number}"

            text = re.sub(mana_pattern, replace_mana, text)

        return text

    def _convert_card_names(self, text: str) -> str:
        """Convert card names from local language to English.

        Parameters
        ----------
        text : str
            Input text

        Returns
        -------
        str
            Text with converted card names
        """
        if self._mapping.language_code == "ja":
            # Convert Japanese card names to English
            for ja_name, en_name in JAPANESE_CARD_NAMES.items():
                text = text.replace(ja_name, f'"{en_name}"')

        return text

    def _convert_phrases(self, text: str) -> str:
        """Convert common phrases.

        Parameters
        ----------
        text : str
            Input text

        Returns
        -------
        str
            Text with converted phrases
        """
        for phrase, replacement in self._mapping.phrases.items():
            if replacement:  # Only replace if there's a mapping
                text = text.replace(phrase, replacement)

        return text

    def _clean_query(self, query: str) -> str:
        """Clean up the final query.

        Parameters
        ----------
        query : str
            Raw converted query

        Returns
        -------
        str
            Cleaned query
        """
        # Remove extra spaces
        query = re.sub(r"\s+", " ", query.strip())

        # Remove redundant operators
        query = re.sub(r"\s+(and|or)\s+", r" \1 ", query)

        # Clean up any remaining artifacts
        query = re.sub(r"\s*:\s*", ":", query)
        query = re.sub(r"\s*([<>=!]+)\s*", r"\1", query)

        return query

    def suggest_corrections(self, text: str) -> list[str]:
        """Suggest corrections for potentially misspelled terms.

        Parameters
        ----------
        text : str
            Input text

        Returns
        -------
        list[str]
            List of suggested corrections
        """
        suggestions = []

        # Check for common misspellings in Japanese
        if self._mapping.language_code == "ja":
            common_mistakes = {
                "くりーちゃー": "クリーチャー",
                "いんすたんと": "インスタント",
                "そーさりー": "ソーサリー",
                "あーてぃふぁくと": "アーティファクト",
                "えんちゃんと": "エンチャント",
            }

            for mistake, correction in common_mistakes.items():
                if mistake in text.lower():
                    suggestions.append(f"'{mistake}' を '{correction}' の間違いですか？")

        return suggestions

    def get_search_help(self) -> dict[str, list[str]]:
        """Get help information for search syntax.

        Returns
        -------
        dict
            Help information organized by category
        """
        if self._mapping.language_code == "ja":
            return {
                "色の指定": [
                    "白いクリーチャー → 白色のクリーチャー",
                    "青のカード → 青色のカード",
                    "赤または緑 → 赤色または緑色",
                ],
                "パワー・タフネス": [
                    "パワーが3以上 → パワー3以上",
                    "タフネス2以下 → タフネス2以下",
                    "パワー5より大きい → パワー6以上",
                ],
                "マナコスト": [
                    "マナ総量3 → マナ総量3",
                    "マナコスト{1}{W} → マナコスト{1}{W}",
                    "点数で見たマナコスト4以下 → CMC4以下",
                ],
                "カードタイプ": [
                    "クリーチャー → クリーチャータイプ",
                    "インスタント → インスタント呪文",
                    "アーティファクト → アーティファクト",
                ],
            }
        return {
            "Colors": [
                "white creatures",
                "blue spells",
                "red or green",
            ],
            "Power/Toughness": [
                "power >= 3",
                "toughness <= 2",
                "power > 5",
            ],
            "Mana Cost": [
                "mana value 3",
                "mana cost {1}{W}",
                "cmc <= 4",
            ],
            "Card Types": [
                "creatures",
                "instants",
                "artifacts",
            ],
        }
