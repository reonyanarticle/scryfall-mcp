"""Pattern matching for complex ability phrases.

This module provides regex-based pattern matching for complex MTG ability
phrases, enabling Phase 2 support for queries like "死亡時にカードを1枚引く黒いクリーチャー".
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

from ..i18n.constants import ABILITY_COLOR_TYPE_PATTERN, ABILITY_KNOWN_EFFECTS


@dataclass
class AbilityPattern:
    """Represents a regex pattern for matching ability phrases.

    Attributes
    ----------
    name : str
        Pattern name for identification
    pattern : re.Pattern
        Compiled regex pattern
    replacement : Callable
        Function to generate replacement tokens from match
    priority : int
        Priority for pattern application (higher = first)
    """

    name: str
    pattern: re.Pattern
    replacement: Callable[[re.Match], list[str]]
    priority: int = 0


class AbilityPatternMatcher:
    """Matches complex ability phrases using regex patterns.

    This matcher applies regex patterns to query text to extract complex
    ability phrases and convert them to Scryfall oracle text queries.

    Examples
    --------
    >>> matcher = AbilityPatternMatcher(patterns)
    >>> remaining, tokens = matcher.apply("死亡時にカードを引く黒いクリーチャー")
    >>> tokens
    ['o:"when ~ dies"', 'o:"draw"']
    >>> remaining
    '黒いクリーチャー'
    """

    def __init__(self, patterns: list[AbilityPattern]) -> None:
        """Initialize pattern matcher.

        Parameters
        ----------
        patterns : list[AbilityPattern]
            List of ability patterns to apply
        """
        # Sort patterns by priority (higher first)
        self.patterns = sorted(patterns, key=lambda p: p.priority, reverse=True)

    def apply(self, text: str) -> tuple[str, list[str]]:
        """Apply patterns to text.

        Processes text through all patterns in priority order, extracting
        matched ability phrases and converting them to oracle text queries.

        Parameters
        ----------
        text : str
            Query text to process

        Returns
        -------
        tuple[str, list[str]]
            Tuple of (remaining text with matches removed, list of oracle tokens)
        """
        all_tokens: list[str] = []
        remaining = text

        for pattern_spec in self.patterns:
            # Find all matches for this pattern
            matches = list(pattern_spec.pattern.finditer(remaining))

            # Store match positions and tokens to preserve order
            match_data: list[tuple[int, int, list[str]]] = []
            for match in matches:
                new_tokens = pattern_spec.replacement(match)
                match_data.append((match.start(), match.end(), new_tokens))

            # Process matches in reverse order to avoid index issues when removing
            for start, end, tokens in reversed(match_data):
                # Remove matched text, replace with space
                remaining = remaining[:start] + " " + remaining[end:]

            # Add tokens in original order (not reversed)
            for _, _, tokens in match_data:
                all_tokens.extend(tokens)

        # Clean up extra whitespace
        remaining = " ".join(remaining.split())

        return remaining, all_tokens


def create_japanese_patterns(keyword_map: dict[str, str]) -> list[AbilityPattern]:
    """Create Japanese ability patterns for Phase 2.

    Parameters
    ----------
    keyword_map : dict[str, str]
        Mapping from Japanese phrases to oracle text queries

    Returns
    -------
    list[AbilityPattern]
        List of compiled ability patterns
    """
    patterns: list[AbilityPattern] = []

    # "死亡時に〜する" pattern
    def death_trigger_replacement(match: re.Match) -> list[str]:
        tokens = ['o:"when ~ dies"']
        effect = match.group(1).strip()
        if effect:
            # Try to match effect to known phrases
            effect_tokens = _parse_effect(effect, keyword_map)
            tokens.extend(effect_tokens)
        return tokens

    patterns.append(
        AbilityPattern(
            name="death_trigger_with_effect",
            pattern=re.compile(rf"死亡時に(.+?)(?:する)?(?= |{ABILITY_COLOR_TYPE_PATTERN}|$)"),
            replacement=death_trigger_replacement,
            priority=100,
        )
    )

    # "戦場に出たときに〜する" pattern
    def etb_trigger_replacement(match: re.Match) -> list[str]:
        tokens = ['o:"enters the battlefield"']
        effect = match.group(1).strip()
        if effect:
            effect_tokens = _parse_effect(effect, keyword_map)
            tokens.extend(effect_tokens)
        return tokens

    patterns.append(
        AbilityPattern(
            name="etb_trigger_with_effect",
            pattern=re.compile(rf"戦場に出たときに(.+?)(?:する)?(?= |{ABILITY_COLOR_TYPE_PATTERN}|$)"),
            replacement=etb_trigger_replacement,
            priority=100,
        )
    )

    # "攻撃したときに〜する" pattern
    def attack_trigger_replacement(match: re.Match) -> list[str]:
        tokens = ['o:"whenever ~ attacks"']
        effect = match.group(1).strip()
        if effect:
            effect_tokens = _parse_effect(effect, keyword_map)
            tokens.extend(effect_tokens)
        return tokens

    patterns.append(
        AbilityPattern(
            name="attack_trigger_with_effect",
            pattern=re.compile(rf"攻撃したときに(.+?)(?:する)?(?= |{ABILITY_COLOR_TYPE_PATTERN}|$)"),
            replacement=attack_trigger_replacement,
            priority=100,
        )
    )

    # Note: Control-related patterns like "あなたがコントロールする" are handled by
    # Phase 1 dictionary mappings in search_keywords, not Phase 2 pattern matching.
    # Phase 2 focuses on trigger patterns with effects like "死亡時に〜する".

    return patterns


def _parse_effect(effect_text: str, keyword_map: dict[str, str]) -> list[str]:
    """Parse effect text into oracle tokens.

    Parameters
    ----------
    effect_text : str
        Effect description in Japanese
    keyword_map : dict[str, str]
        Mapping from Japanese to oracle syntax

    Returns
    -------
    list[str]
        List of oracle tokens
    """
    tokens: list[str] = []

    # Try exact match first
    if effect_text in keyword_map:
        tokens.append(keyword_map[effect_text])
        return tokens

    # Try partial matches for known phrases
    for phrase, token in ABILITY_KNOWN_EFFECTS.items():
        if phrase in effect_text:
            tokens.append(token)

    return tokens
