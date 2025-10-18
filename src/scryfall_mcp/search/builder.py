"""Query builder for Scryfall search syntax.

This module provides functionality to build and convert search queries
from natural language (especially Japanese) to Scryfall search syntax.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any

from ..models import BuiltQuery, ParsedQuery

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ..i18n import LanguageMapping


class QueryBuilder:
    """Builds Scryfall search queries from parsed natural language data."""

    # Japanese operator mappings (shared across all numeric comparisons)
    _JA_OPERATOR_MAP = {
        "以上": ">=",
        "以下": "<=",
        "より大きい": ">",
        "未満": "<",
        "等しい": "=",
        "と等しい": "=",
    }

    # Japanese common misspellings (shared across suggestion methods)
    _JA_COMMON_MISTAKES = {
        "くりーちゃー": "クリーチャー",
        "いんすたんと": "インスタント",
        "そーさりー": "ソーサリー",
        "あーてぃふぁくと": "アーティファクト",
        "えんちゃんと": "エンチャント",
    }

    def __init__(self, locale_mapping: LanguageMapping):
        """Initialize the query builder with locale-specific mappings.

        Parameters
        ----------
        locale_mapping : LanguageMapping
            Language-specific mappings for query building
        """
        self._mapping = locale_mapping

        # Initialize pattern matcher for Japanese (Phase 2)
        self._pattern_matcher = None
        if locale_mapping.language_code == "ja":
            from .ability_patterns import (
                AbilityPatternMatcher,
                create_japanese_patterns,
            )

            patterns = create_japanese_patterns(locale_mapping.search_keywords)
            self._pattern_matcher = AbilityPatternMatcher(patterns)

    async def build(self, parsed: ParsedQuery) -> BuiltQuery:
        """Build Scryfall query from parsed data.

        Parameters
        ----------
        parsed : ParsedQuery
            Parsed query data

        Returns
        -------
        BuiltQuery
            Built query with metadata and suggestions
        """
        # Phase 2: Apply pattern matching FIRST (before other conversions)
        # This prevents other conversions from interfering with pattern matching
        ability_tokens: list[str] = []
        working_text = parsed.normalized_text
        if self._pattern_matcher is not None:
            working_text, ability_tokens = self._pattern_matcher.apply(working_text)

        # Start with normalized text and apply transformations
        # IMPORTANT: _convert_operators must run before _convert_basic_terms
        # to handle patterns like "パワー3以上" before "パワー" gets converted to "p"
        query = self._convert_operators(working_text)
        query = self._convert_colors(query)
        query = self._convert_types(query)
        query = self._convert_basic_terms(query)
        query = self._convert_card_names(query)
        query = self._convert_phrases(query)

        # Add ability tokens from Phase 2 pattern matching
        if ability_tokens:
            query = f"{query} {' '.join(ability_tokens)}"

        query = self._clean_query(query)

        # Issue #3: Replace __LATEST_SET__ placeholder with actual latest set
        query = await self._replace_latest_set_placeholder(query)

        # Generate suggestions based on parsed data
        suggestions = self._generate_suggestions(parsed)

        # Extract query metadata
        metadata = self._extract_metadata(parsed, query)

        return BuiltQuery(
            scryfall_query=query,
            original_query=parsed.original_text,
            suggestions=suggestions,
            query_metadata=metadata,
        )

    def build_query(self, text: str, locale: str | None = None) -> str:
        """Legacy method for backward compatibility.

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
        # This method is kept for backward compatibility
        # In the refactored version, use Parser -> QueryBuilder -> Presenter flow

        # Update mapping if locale changed
        if locale and locale != self._mapping.language_code:
            from ..i18n import get_locale_manager

            manager = get_locale_manager()
            self._mapping = manager.get_mapping(locale)

            # Re-initialize pattern matcher if locale changed to Japanese
            if self._mapping.language_code == "ja":
                from .ability_patterns import (
                    AbilityPatternMatcher,
                    create_japanese_patterns,
                )

                patterns = create_japanese_patterns(self._mapping.search_keywords)
                self._pattern_matcher = AbilityPatternMatcher(patterns)
            else:
                self._pattern_matcher = None

        # Clean and normalize the input
        normalized_text = self._normalize_text(text)

        # Phase 2: Apply pattern matching FIRST (before other conversions)
        # This prevents other conversions from interfering with pattern matching
        ability_tokens: list[str] = []
        if self._pattern_matcher is not None:
            normalized_text, ability_tokens = self._pattern_matcher.apply(normalized_text)

        # Process the text through various conversion steps
        # IMPORTANT: _convert_operators must run before _convert_basic_terms
        # to handle patterns like "パワー3以上" before "パワー" gets converted to "p"
        query = self._convert_operators(normalized_text)
        query = self._convert_colors(query)
        query = self._convert_types(query)
        query = self._convert_basic_terms(query)
        query = self._convert_card_names(query)
        query = self._convert_phrases(query)

        # Add ability tokens from pattern matching
        if ability_tokens:
            query = f"{query} {' '.join(ability_tokens)}"

        query = self._clean_query(query)

        # Issue #3: Replace __LATEST_SET__ placeholder with actual latest set (sync)
        query = self._replace_latest_set_placeholder_sync(query)

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
            "０": "0",
            "１": "1",
            "２": "2",
            "３": "3",
            "４": "4",
            "５": "5",
            "６": "6",
            "７": "7",
            "８": "8",
            "９": "9",
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
        # Sort terms by length (longest first) to avoid partial replacements
        sorted_terms = sorted(
            self._mapping.search_keywords.items(), key=lambda x: len(x[0]), reverse=True
        )

        for term, scryfall_term in sorted_terms:
            if scryfall_term:  # Only replace if there's a mapping
                # For Japanese text, use simple replacement
                # For English, use word boundaries
                if self._mapping.language_code == "ja":
                    text = text.replace(term, scryfall_term)
                else:
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
                    "白": "w",
                    "青": "u",
                    "黒": "b",
                    "赤": "r",
                    "緑": "g",
                    "無色": "c",
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
                operator = self._JA_OPERATOR_MAP.get(operator_ja or "等しい", "=")

                return f"p{operator}{number}"

            text = re.sub(power_pattern, replace_power, text)

            # Similar for toughness
            toughness_pattern = (
                r"タフネスが?(\d+)(以上|以下|より大きい|未満|と?等しい)?"
            )

            def replace_toughness(match: Any) -> str:
                number, operator_ja = match.groups()
                operator = self._JA_OPERATOR_MAP.get(operator_ja or "等しい", "=")

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

                operator = self._JA_OPERATOR_MAP.get(operator_ja or "等しい", "=")

                return f"{field}{operator}{number}"

            text = re.sub(mana_pattern, replace_mana, text)

        return text

    def _convert_card_names(self, text: str) -> str:
        """Pass card names as-is to Scryfall.

        Scryfall natively supports multilingual card names through the printed_name
        field and lang: parameter. No pre-translation is needed.

        Parameters
        ----------
        text : str
            Input text

        Returns
        -------
        str
            Text unchanged (Scryfall handles multilingual names)
        """
        # No conversion needed - Scryfall supports multilingual card names natively
        # The lang: parameter will be added during query execution
        return text

    def _convert_phrases(self, text: str) -> str:
        """Convert common phrases using dictionary replacements.

        Note: Pattern matching (Phase 2) is now handled in build_query()
        before this method is called.

        Parameters
        ----------
        text : str
            Input text

        Returns
        -------
        str
            Text with converted phrases
        """
        # Dictionary-based replacement (Phase 1)
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

    async def _replace_latest_set_placeholder(self, query: str) -> str:
        """Replace __LATEST_SET__ placeholder with actual latest set code.

        This method fetches the latest expansion set code from Scryfall API
        (with 24-hour caching) and replaces the __LATEST_SET__ placeholder.

        Parameters
        ----------
        query : str
            Query string potentially containing __LATEST_SET__ placeholder

        Returns
        -------
        str
            Query with placeholder replaced by actual set code

        Notes
        -----
        - Uses get_latest_expansion_code() with 24h cache
        - Fallback to "mkm" if API call fails
        - Only performs API call if placeholder is present
        """
        if "__LATEST_SET__" not in query:
            return query

        try:
            from ..api.client import get_client
            from ..api.sets import get_latest_expansion_code

            client = await get_client()
            latest_code = await get_latest_expansion_code(client)
            return query.replace("__LATEST_SET__", latest_code)
        except Exception as e:
            logger.warning(
                f"Failed to fetch latest set, using fallback: {e}",
                exc_info=True
            )
            # Fallback to hardcoded value
            from ..i18n.constants import LATEST_SET_CODE_FALLBACK
            return query.replace("__LATEST_SET__", LATEST_SET_CODE_FALLBACK)

    def _replace_latest_set_placeholder_sync(self, query: str) -> str:
        """Synchronous version of _replace_latest_set_placeholder.

        This method replaces __LATEST_SET__ placeholder using the synchronous
        cache accessor. It's used by the legacy build_query() method.

        Parameters
        ----------
        query : str
            Query string potentially containing __LATEST_SET__ placeholder

        Returns
        -------
        str
            Query with placeholder replaced by set code (from cache or fallback)

        Notes
        -----
        - Uses cached value if available
        - Falls back to LATEST_SET_CODE_FALLBACK if no cache
        - Does not perform API calls (sync-safe)
        """
        if "__LATEST_SET__" not in query:
            return query

        try:
            from ..api.sets import get_latest_expansion_code_sync

            latest_code = get_latest_expansion_code_sync()
            return query.replace("__LATEST_SET__", latest_code)
        except Exception as e:
            logger.warning(
                f"Failed to get latest set from cache, using fallback: {e}",
                exc_info=True
            )
            from ..i18n.constants import LATEST_SET_CODE_FALLBACK
            return query.replace("__LATEST_SET__", LATEST_SET_CODE_FALLBACK)

    def _generate_suggestions(self, parsed: ParsedQuery) -> list[str]:
        """Generate suggestions based on parsed query data.

        Parameters
        ----------
        parsed : ParsedQuery
            Parsed query data

        Returns
        -------
        list[str]
            List of suggestions
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

        # Check for common misspellings in Japanese
        if self._mapping.language_code == "ja":
            for mistake, correction in self._JA_COMMON_MISTAKES.items():
                if mistake in text.lower():
                    suggestions.append(
                        f"'{mistake}' を '{correction}' の間違いですか？"
                    )

        return suggestions

    def _extract_metadata(
        self, parsed: ParsedQuery, built_query: str
    ) -> dict[str, Any]:
        """Extract metadata from parsed query and built query.

        Parameters
        ----------
        parsed : ParsedQuery
            Parsed query data
        built_query : str
            Built Scryfall query

        Returns
        -------
        dict
            Query metadata
        """
        return {
            "intent": parsed.intent,
            "extracted_entities": parsed.entities,
            "language": parsed.language,
            "query_complexity": self._assess_complexity(built_query),
            "estimated_results": self._estimate_results(built_query),
        }

    def _assess_complexity(self, query: str) -> str:
        """Assess the complexity of a query.

        Parameters
        ----------
        query : str
            Scryfall query

        Returns
        -------
        str
            Complexity assessment
        """
        operator_count = len(re.findall(r"[<>=!]+", query))
        field_count = len(re.findall(r"\w+:", query))

        if operator_count > 3 or field_count > 5:
            return "complex"
        elif operator_count > 1 or field_count > 2:
            return "moderate"
        else:
            return "simple"

    def _estimate_results(self, query: str) -> str:
        """Estimate the number of results for a query.

        Parameters
        ----------
        query : str
            Scryfall query

        Returns
        -------
        str
            Result count estimation
        """
        # This is a simple heuristic - more specific queries usually return fewer results
        specificity_score = 0

        # Count specific filters
        specificity_score += len(re.findall(r"c:", query))  # Colors
        specificity_score += len(re.findall(r"t:", query))  # Types
        specificity_score += len(re.findall(r"p[<>=!]", query))  # Power
        specificity_score += len(re.findall(r"tou[<>=!]", query))  # Toughness
        specificity_score += len(re.findall(r"mv[<>=!]", query))  # Mana value
        specificity_score += len(re.findall(r'"[^"]+"', query))  # Quoted names

        if specificity_score >= 4:
            return "few"
        elif specificity_score >= 2:
            return "moderate"
        else:
            return "many"

    def suggest_corrections(self, text: str) -> list[str]:
        """Legacy method for backward compatibility.

        Parameters
        ----------
        text : str
            Input text

        Returns
        -------
        list[str]
            List of suggested corrections
        """
        # This method is kept for backward compatibility
        # In the refactored version, suggestions are generated in _generate_suggestions
        suggestions = []

        # Check for common misspellings in Japanese
        if self._mapping.language_code == "ja":
            for mistake, correction in self._JA_COMMON_MISTAKES.items():
                if mistake in text.lower():
                    suggestions.append(
                        f"'{mistake}' を '{correction}' の間違いですか？"
                    )

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
