"""Tests for locales module."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from scryfall_mcp.i18n.locales import (
    LocaleInfo,
    LocaleManager,
    detect_and_set_locale,
    get_current_mapping,
    get_locale_manager,
    set_current_locale,
)


class TestLocaleInfo:
    """Test LocaleInfo model."""

    def test_locale_info_creation(self):
        """Test LocaleInfo creation."""
        locale_info = LocaleInfo(
            code="ja_JP",
            language="Japanese",
            language_code="ja",
            country="Japan",
            country_code="JP",
            encoding="UTF-8",
            is_default=True,
            is_fallback=False,
        )

        assert locale_info.code == "ja_jp"  # Should be lowercased
        assert locale_info.language == "Japanese"
        assert locale_info.language_code == "ja"
        assert locale_info.country == "Japan"
        assert locale_info.is_default is True

    def test_locale_info_validation(self):
        """Test LocaleInfo validation."""
        # Test invalid locale code
        with pytest.raises(ValueError):
            LocaleInfo(
                code="",
                language="English",
                language_code="en",
            )

        with pytest.raises(ValueError):
            LocaleInfo(
                code="x",
                language="English",
                language_code="en",
            )


class TestLocaleManager:
    """Test LocaleManager class."""

    @pytest.fixture
    def locale_manager(self):
        """Create a fresh locale manager for testing."""
        return LocaleManager()

    def test_initialization(self, locale_manager):
        """Test locale manager initialization."""
        assert len(locale_manager._mappings) >= 2  # en and ja
        assert "en" in locale_manager._mappings
        assert "ja" in locale_manager._mappings
        assert locale_manager.get_current_locale() == "en"  # Default

    def test_is_supported(self, locale_manager):
        """Test is_supported method."""
        assert locale_manager.is_supported("en") is True
        assert locale_manager.is_supported("ja") is True
        assert locale_manager.is_supported("fr") is False
        assert locale_manager.is_supported("invalid") is False

    def test_set_locale_valid(self, locale_manager):
        """Test setting valid locale."""
        from scryfall_mcp.i18n import use_locale

        # Test using context manager
        with use_locale("ja"):
            assert locale_manager.get_current_locale() == "ja"

        # Should revert to default after context
        assert locale_manager.get_current_locale() == "en"

    def test_set_locale_invalid(self, locale_manager):
        """Test setting invalid locale."""
        import pytest

        from scryfall_mcp.i18n import use_locale

        # Should raise error for invalid locale
        with pytest.raises(ValueError, match="Unsupported locale"):
            with use_locale("invalid"):
                pass

    def test_get_mapping_current(self, locale_manager):
        """Test getting mapping for current locale."""
        from scryfall_mcp.i18n import use_locale

        # Test default locale
        mapping = locale_manager.get_mapping()
        assert mapping.language_code == "en"

        # Test specific locale in context
        with use_locale("ja"):
            mapping = locale_manager.get_mapping()
            assert mapping.language_code == "ja"
            assert mapping.language_name == "日本語"

    def test_get_mapping_specific(self, locale_manager):
        """Test getting specific mapping."""
        en_mapping = locale_manager.get_mapping("en")
        assert en_mapping.language_code == "en"

        ja_mapping = locale_manager.get_mapping("ja")
        assert ja_mapping.language_code == "ja"

    def test_get_mapping_fallback(self, locale_manager):
        """Test mapping fallback for unsupported locale."""
        # Should fallback to fallback locale (en)
        mapping = locale_manager.get_mapping("unsupported")
        assert mapping.language_code == "en"

    def test_get_supported_locales(self, locale_manager):
        """Test getting supported locales."""
        locales = locale_manager.get_supported_locales()
        assert len(locales) >= 2

        locale_codes = {locale.language_code for locale in locales}
        assert "en" in locale_codes
        assert "ja" in locale_codes

    def test_get_supported_locale_codes(self, locale_manager):
        """Test getting supported locale codes."""
        codes = locale_manager.get_supported_locale_codes()
        assert "en" in codes
        assert "ja" in codes
        assert isinstance(codes, set)

    def test_get_locale_info(self, locale_manager):
        """Test getting locale information."""
        # Current locale
        info = locale_manager.get_locale_info()
        assert info.language_code == locale_manager.get_current_locale()

        # Specific locale
        en_info = locale_manager.get_locale_info("en")
        assert en_info.language_code == "en"
        assert en_info.language == "English"

        # Unsupported locale
        unknown_info = locale_manager.get_locale_info("unknown")
        assert unknown_info.language_code == "unknown"
        assert unknown_info.language == "Unknown"

    def test_parse_locale_string(self, locale_manager):
        """Test locale string parsing."""
        # Test various formats
        assert locale_manager._parse_locale_string("en_US.UTF-8") == "en"
        assert locale_manager._parse_locale_string("ja_JP") == "ja"
        assert locale_manager._parse_locale_string("en") == "en"
        assert locale_manager._parse_locale_string("fr_FR.UTF-8") == "fr"

        # Test invalid formats
        assert locale_manager._parse_locale_string("") is None
        assert locale_manager._parse_locale_string("1") is None
        assert locale_manager._parse_locale_string("X") is None

    def test_detect_locale(self, locale_manager):
        """Test locale detection."""
        # Test with environment variables
        test_cases = [
            ("en_US.UTF-8", "en"),
            ("ja_JP.UTF-8", "ja"),
            ("fr_FR", "en"),  # Unsupported, should fallback to default
        ]

        for env_value, expected in test_cases:
            with patch.dict(os.environ, {"LANG": env_value}):
                detected = locale_manager.detect_locale()
                assert detected == expected

    def test_detect_locale_fallback(self, locale_manager):
        """Test locale detection fallback."""
        # Clear environment variables
        env_vars = ["LC_ALL", "LC_CTYPE", "LANG", "LANGUAGE"]
        with patch.dict(os.environ, dict.fromkeys(env_vars, ""), clear=True):
            detected = locale_manager.detect_locale()
            # Should fallback to default
            assert detected == locale_manager._default_locale

    def test_add_mapping(self, locale_manager):
        """Test adding new language mapping."""
        from scryfall_mcp.i18n.mappings.common import LanguageMapping

        # Create a mock mapping
        new_mapping = LanguageMapping(
            language_code="fr",
            language_name="Français",
            locale_code="fr_FR",
            colors={"white": "w", "blue": "u", "black": "b", "red": "r", "green": "g", "colorless": "c"},
            types={"artifact": "artifact", "creature": "creature", "enchantment": "enchantment",
                   "instant": "instant", "land": "land", "planeswalker": "planeswalker", "sorcery": "sorcery",
                   "basic": "basic", "legendary": "legendary", "snow": "snow",
                   "equipment": "equipment", "aura": "aura", "vehicle": "vehicle", "token": "token"},
            operators={"equals": "=", "not_equals": "!=", "less_than": "<", "less_than_or_equal": "<=",
                      "greater_than": ">", "greater_than_or_equal": ">=", "contains": ":", "not_contains": "-"},
            formats={"standard": "standard", "pioneer": "pioneer", "modern": "modern", "legacy": "legacy",
                    "vintage": "vintage", "commander": "commander", "pauper": "pauper", "historic": "historic",
                    "alchemy": "alchemy", "brawl": "brawl"},
            rarities={"common": "common", "uncommon": "uncommon", "rare": "rare", "mythic": "mythic",
                     "special": "special", "bonus": "bonus"},
            set_types={"core": "core", "expansion": "expansion", "masters": "masters", "draft_innovation": "draft_innovation",
                      "commander": "commander", "planechase": "planechase", "archenemy": "archenemy",
                      "from_the_vault": "from_the_vault", "premium_deck": "premium_deck", "duel_deck": "duel_deck",
                      "starter": "starter", "box": "box", "promo": "promo", "token": "token",
                      "memorabilia": "memorabilia", "treasure_chest": "treasure_chest", "spellbook": "spellbook",
                      "arsenal": "arsenal"},
            search_keywords={},
            phrases={},
        )

        # Add mapping
        result = locale_manager.add_mapping(new_mapping)
        assert result is True
        assert locale_manager.is_supported("fr")

        # Try to add same mapping again
        result = locale_manager.add_mapping(new_mapping)
        assert result is False  # Already exists

    def test_reload_mappings(self, locale_manager):
        """Test reloading mappings."""
        original_count = len(locale_manager._mappings)

        # Add a temporary mapping
        from scryfall_mcp.i18n.mappings.common import LanguageMapping
        temp_mapping = LanguageMapping(
            language_code="temp",
            language_name="Temporary",
            locale_code="temp",
            colors={"white": "w", "blue": "u", "black": "b", "red": "r", "green": "g", "colorless": "c"},
            types={"artifact": "artifact", "creature": "creature", "enchantment": "enchantment",
                   "instant": "instant", "land": "land", "planeswalker": "planeswalker", "sorcery": "sorcery",
                   "basic": "basic", "legendary": "legendary", "snow": "snow",
                   "equipment": "equipment", "aura": "aura", "vehicle": "vehicle", "token": "token"},
            operators={"equals": "=", "not_equals": "!=", "less_than": "<", "less_than_or_equal": "<=",
                      "greater_than": ">", "greater_than_or_equal": ">=", "contains": ":", "not_contains": "-"},
            formats={"standard": "standard", "pioneer": "pioneer", "modern": "modern", "legacy": "legacy",
                    "vintage": "vintage", "commander": "commander", "pauper": "pauper", "historic": "historic",
                    "alchemy": "alchemy", "brawl": "brawl"},
            rarities={"common": "common", "uncommon": "uncommon", "rare": "rare", "mythic": "mythic",
                     "special": "special", "bonus": "bonus"},
            set_types={"core": "core", "expansion": "expansion", "masters": "masters", "draft_innovation": "draft_innovation",
                      "commander": "commander", "planechase": "planechase", "archenemy": "archenemy",
                      "from_the_vault": "from_the_vault", "premium_deck": "premium_deck", "duel_deck": "duel_deck",
                      "starter": "starter", "box": "box", "promo": "promo", "token": "token",
                      "memorabilia": "memorabilia", "treasure_chest": "treasure_chest", "spellbook": "spellbook",
                      "arsenal": "arsenal"},
            search_keywords={},
            phrases={},
        )
        locale_manager.add_mapping(temp_mapping)
        assert len(locale_manager._mappings) == original_count + 1

        # Reload should reset to original
        locale_manager.reload_mappings()
        assert len(locale_manager._mappings) == original_count
        assert not locale_manager.is_supported("temp")


class TestGlobalFunctions:
    """Test global locale functions."""

    def test_get_locale_manager_singleton(self):
        """Test that get_locale_manager returns singleton."""
        manager1 = get_locale_manager()
        manager2 = get_locale_manager()
        assert manager1 is manager2

    def test_get_current_mapping(self):
        """Test getting current mapping through global function."""
        mapping = get_current_mapping()
        assert mapping.language_code in ["en", "ja"]

    def test_set_current_locale(self):
        """Test setting current locale through global function."""
        original_locale = get_locale_manager().get_current_locale()

        # Set to different locale
        new_locale = "ja" if original_locale != "ja" else "en"
        result = set_current_locale(new_locale)
        assert result is True
        assert get_locale_manager().get_current_locale() == new_locale

        # Reset to original
        set_current_locale(original_locale)

    def test_detect_and_set_locale(self):
        """Test detecting and setting locale."""
        with patch.dict(os.environ, {"LANG": "ja_JP.UTF-8"}):
            detected = detect_and_set_locale()
            assert detected == "ja"
            # Note: detect_and_set_locale no longer sets global state,
            # it just returns the detected locale
            # The actual setting would be done via context manager

    def test_locale_detection_with_unsupported_language(self):
        """Test locale detection with unsupported language."""
        with patch.dict(os.environ, {"LANG": "fr_FR.UTF-8"}):
            detected = detect_and_set_locale()
            # Should fallback to default (en)
            assert detected == "en"

    def test_environment_variable_priority(self):
        """Test environment variable priority for locale detection."""
        manager = LocaleManager()

        # LC_ALL should take priority
        with patch.dict(os.environ, {
            "LC_ALL": "ja_JP.UTF-8",
            "LANG": "en_US.UTF-8",
        }):
            detected = manager.detect_locale()
            assert detected == "ja"

        # LANG should be used if LC_ALL is not set
        with patch.dict(os.environ, {
            "LANG": "ja_JP.UTF-8",
        }, clear=True):
            detected = manager.detect_locale()
            assert detected == "ja"

    def test_locale_detection_error_handling(self):
        """Test error handling in locale detection."""
        manager = LocaleManager()

        # Test with locale that raises exception
        with patch("locale.getdefaultlocale", side_effect=Exception("Test error")):
            detected = manager.detect_locale()
            # Should fallback to default
            assert detected == manager._default_locale

class TestContextvarLocale:
    """Test contextvar-based locale management."""

    @pytest.mark.asyncio
    async def test_concurrent_locale_contexts(self):
        """Test that different locales work concurrently without interference."""
        import asyncio
        from scryfall_mcp.i18n import use_locale, get_current_mapping

        results = []
        
        async def task_with_locale(locale_code: str, expected_lang: str):
            """Task that uses specific locale."""
            with use_locale(locale_code):
                # Simulate some async work
                await asyncio.sleep(0.01)
                mapping = get_current_mapping()
                results.append((locale_code, mapping.language_code, expected_lang))
                # Verify context is maintained
                assert mapping.language_code == expected_lang

        # Run concurrent tasks with different locales
        tasks = [
            task_with_locale("ja", "ja"),
            task_with_locale("en", "en"),
            task_with_locale("ja", "ja"),
            task_with_locale("en", "en"),
        ]

        await asyncio.gather(*tasks)

        # Verify all tasks got their expected locales
        assert len(results) == 4
        for locale_code, actual_lang, expected_lang in results:
            assert actual_lang == expected_lang, f"Task with {locale_code} got {actual_lang}, expected {expected_lang}"

    def test_locale_context_isolation(self):
        """Test that locale context is properly isolated."""
        from scryfall_mcp.i18n import use_locale, get_locale_manager

        manager = get_locale_manager()
        
        # Default should be 'en'
        assert manager.get_current_locale() == "en"
        
        # Test nested contexts
        with use_locale("ja"):
            assert manager.get_current_locale() == "ja"
            
            with use_locale("en"):
                assert manager.get_current_locale() == "en"
            
            # Should revert to outer context
            assert manager.get_current_locale() == "ja"
        
        # Should revert to default
        assert manager.get_current_locale() == "en"

    def test_use_locale_error_handling(self):
        """Test error handling in use_locale context manager."""
        from scryfall_mcp.i18n import use_locale, get_locale_manager
        import pytest

        manager = get_locale_manager()
        
        # Test invalid locale
        with pytest.raises(ValueError, match="Unsupported locale"):
            with use_locale("invalid"):
                pass
        
        # Ensure context is clean after error
        assert manager.get_current_locale() == "en"
        
        # Test exception within context
        with pytest.raises(RuntimeError):
            with use_locale("ja"):
                assert manager.get_current_locale() == "ja"
                raise RuntimeError("Test error")
        
        # Should still revert to default
        assert manager.get_current_locale() == "en"
