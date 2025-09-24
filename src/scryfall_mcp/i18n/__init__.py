"""Internationalization system for Scryfall MCP Server.

This module provides basic internationalization support with a focus on
Japanese language support for Magic: The Gathering card searches.
"""

from __future__ import annotations

from .locales import (
    LocaleInfo,
    LocaleManager,
    detect_and_set_locale,
    get_current_mapping,
    get_locale_manager,
    set_current_locale,
    use_locale,
)
from .mappings.common import LanguageMapping
from .mappings.en import english_mapping
from .mappings.ja import JAPANESE_CARD_NAMES, japanese_mapping

__all__ = [
    "JAPANESE_CARD_NAMES",
    "LanguageMapping",
    "LocaleInfo",
    "LocaleManager",
    "detect_and_set_locale",
    "english_mapping",
    "get_current_mapping",
    "get_locale_manager",
    "japanese_mapping",
    "set_current_locale",
    "use_locale",
]
