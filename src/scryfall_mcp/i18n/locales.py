"""Locale management for internationalization.

This module provides locale detection, management, and configuration
for the Scryfall MCP Server internationalization system.
"""

from __future__ import annotations

import contextvars
import locale
import logging
import os
from collections.abc import Generator
from contextlib import contextmanager

from ..models import LanguageMapping, LocaleInfo
from ..settings import get_settings
from .mappings.en import english_mapping
from .mappings.ja import japanese_mapping

logger = logging.getLogger(__name__)
# Context variable for per-request locale management
_current_locale_context: contextvars.ContextVar[str] = contextvars.ContextVar(
    "current_locale", default="en"
)


class LocaleManager:
    """Manages locale detection and language mapping resolution."""

    def __init__(self) -> None:
        """Initialize the locale manager."""
        self._settings = get_settings()
        self._mappings: dict[str, LanguageMapping] = {}
        self._available_locales: dict[str, LocaleInfo] = {}
        self._default_locale: str = self._settings.default_locale
        self._fallback_locale: str = self._settings.fallback_locale

        # Load built-in mappings
        self._load_built_in_mappings()
        self._initialize_locales()

    def _load_built_in_mappings(self) -> None:
        """Load built-in language mappings."""
        self._mappings["en"] = english_mapping
        self._mappings["ja"] = japanese_mapping

        logger.info(f"Loaded {len(self._mappings)} language mappings")

    def _initialize_locales(self) -> None:
        """Initialize available locales."""
        # Add locales for each available mapping
        for lang_code, mapping in self._mappings.items():
            locale_info = LocaleInfo(
                code=mapping.locale_code,
                language=mapping.language_name,
                language_code=lang_code,
                is_default=(lang_code == self._default_locale),
                is_fallback=(lang_code == self._fallback_locale),
            )
            self._available_locales[lang_code] = locale_info

        logger.info(f"Initialized {len(self._available_locales)} locales")

    def detect_locale(self) -> str:
        """Detect the system locale.

        Returns
        -------
        str
            Detected locale code
        """
        try:
            # Try environment variables first
            for env_var in ["LC_ALL", "LC_CTYPE", "LANG", "LANGUAGE"]:
                if env_value := os.environ.get(env_var):
                    if locale_code := self._parse_locale_string(env_value):
                        if self.is_supported(locale_code):
                            return locale_code

            # Try system locale
            system_locale, _ = locale.getdefaultlocale()
            if system_locale:
                if locale_code := self._parse_locale_string(system_locale):
                    if self.is_supported(locale_code):
                        return locale_code

        except Exception as e:
            logger.warning(f"Failed to detect system locale: {e}")

        # Fallback to default
        return self._default_locale

    def _parse_locale_string(self, locale_str: str) -> str | None:
        """Parse a locale string to extract language code.

        Parameters
        ----------
        locale_str : str
            Locale string (e.g., "en_US.UTF-8", "ja_JP", "en")

        Returns
        -------
        str | None
            Language code if valid, None otherwise
        """
        if not locale_str:
            return None

        # Handle common formats: en_US.UTF-8, en_US, en
        parts = locale_str.lower().split("_")[0].split(".")[0]

        if len(parts) >= 2 and parts.isalpha():
            return parts

        return None

    def get_current_locale(self) -> str:
        """Get the current locale code from context or default.

        Returns
        -------
        str
            Current locale code
        """
        return _current_locale_context.get(self._default_locale)

    def get_mapping(self, locale_code: str | None = None) -> LanguageMapping:
        """Get language mapping for a locale.

        Parameters
        ----------
        locale_code : str, optional
            Locale code. If None, uses current locale.

        Returns
        -------
        LanguageMapping
            Language mapping instance
        """
        if locale_code is None:
            locale_code = self.get_current_locale()

        if locale_code in self._mappings:
            return self._mappings[locale_code]

        # Fallback to fallback locale
        if self._fallback_locale in self._mappings:
            logger.warning(
                f"Locale {locale_code} not found, using fallback {self._fallback_locale}",
            )
            return self._mappings[self._fallback_locale]

        # Last resort: return first available mapping
        if self._mappings:
            fallback_key = next(iter(self._mappings))
            logger.error(
                f"Fallback locale {self._fallback_locale} not found, "
                f"using {fallback_key}",
            )
            return self._mappings[fallback_key]

        raise RuntimeError("No language mappings available")

    def is_supported(self, locale_code: str) -> bool:
        """Check if a locale is supported.

        Parameters
        ----------
        locale_code : str
            Locale code to check

        Returns
        -------
        bool
            True if supported, False otherwise
        """
        return locale_code in self._mappings

    def get_supported_locales(self) -> list[LocaleInfo]:
        """Get list of supported locales.

        Returns
        -------
        list[LocaleInfo]
            List of supported locale information
        """
        return list(self._available_locales.values())

    def get_supported_locale_codes(self) -> set[str]:
        """Get set of supported locale codes.

        Returns
        -------
        set[str]
            Set of supported locale codes
        """
        return set(self._mappings.keys())

    def add_mapping(self, mapping: LanguageMapping) -> bool:
        """Add a new language mapping.

        Parameters
        ----------
        mapping : LanguageMapping
            Language mapping to add

        Returns
        -------
        bool
            True if successfully added, False if already exists
        """
        if mapping.language_code in self._mappings:
            logger.warning(f"Mapping for {mapping.language_code} already exists")
            return False

        self._mappings[mapping.language_code] = mapping

        # Add locale info
        locale_info = LocaleInfo(
            code=mapping.locale_code,
            language=mapping.language_name,
            language_code=mapping.language_code,
        )
        self._available_locales[mapping.language_code] = locale_info

        logger.info(f"Added mapping for language: {mapping.language_name}")
        return True

    def reload_mappings(self) -> None:
        """Reload all language mappings."""
        self._mappings.clear()
        self._available_locales.clear()
        self._load_built_in_mappings()
        self._initialize_locales()
        logger.info("Reloaded all language mappings")

    def get_locale_info(self, locale_code: str | None = None) -> LocaleInfo:
        """Get detailed locale information.

        Parameters
        ----------
        locale_code : str, optional
            Locale code. If None, uses current locale.

        Returns
        -------
        LocaleInfo
            Locale information
        """
        if locale_code is None:
            locale_code = self.get_current_locale()

        if locale_code in self._available_locales:
            return self._available_locales[locale_code]

        # Fallback info
        return LocaleInfo(
            code=locale_code,
            language="Unknown",
            language_code=locale_code,
        )


@contextmanager
def use_locale(locale_code: str) -> Generator[str, None, None]:
    """Context manager for setting locale in current context.

    Parameters
    ----------
    locale_code : str
        Locale code to set

    Yields
    ------
    str
        The locale code that was set

    Raises
    ------
    ValueError
        If locale code is not supported
    """
    manager = get_locale_manager()

    if not manager.is_supported(locale_code):
        raise ValueError(f"Unsupported locale: {locale_code}")

    # Set the locale in the context
    token = _current_locale_context.set(locale_code)
    try:
        yield locale_code
    finally:
        _current_locale_context.reset(token)


# Global locale manager instance
_locale_manager: LocaleManager | None = None


def get_locale_manager() -> LocaleManager:
    """Get the global locale manager instance.

    Returns
    -------
    LocaleManager
        The global locale manager instance
    """
    global _locale_manager
    if _locale_manager is None:
        _locale_manager = LocaleManager()
    return _locale_manager


def get_current_mapping() -> LanguageMapping:
    """Get the current language mapping.

    Returns
    -------
    LanguageMapping
        Current language mapping
    """
    return get_locale_manager().get_mapping()


def set_current_locale(locale_code: str) -> bool:
    """Set the current locale in context.

    Parameters
    ----------
    locale_code : str
        Locale code to set

    Returns
    -------
    bool
        True if successfully set, False otherwise
    """
    manager = get_locale_manager()
    if not manager.is_supported(locale_code):
        return False

    _current_locale_context.set(locale_code)
    return True


def detect_and_set_locale() -> str:
    """Detect and set the system locale.

    Returns
    -------
    str
        The detected and set locale code
    """
    manager = get_locale_manager()
    detected = manager.detect_locale()
    # Set in context rather than globally
    set_current_locale(detected)
    return detected
