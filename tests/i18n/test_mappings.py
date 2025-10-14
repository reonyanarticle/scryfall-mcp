"""Tests for language mappings."""

from __future__ import annotations

import pytest

from scryfall_mcp.i18n.constants import (
    MAGIC_COLORS,
    MAGIC_TYPES,
    SCRYFALL_KEYWORDS,
    SEARCH_PATTERNS,
)
from scryfall_mcp.i18n.mappings.en import english_mapping
from scryfall_mcp.i18n.mappings.ja import JAPANESE_CARD_NAMES, japanese_mapping
from scryfall_mcp.models import LanguageMapping


class TestCommonMappings:
    """Test common mapping definitions."""

    def test_scryfall_keywords(self):
        """Test Scryfall keywords set."""
        assert "c" in SCRYFALL_KEYWORDS
        assert "color" in SCRYFALL_KEYWORDS
        assert "t" in SCRYFALL_KEYWORDS
        assert "type" in SCRYFALL_KEYWORDS
        assert "p" in SCRYFALL_KEYWORDS
        assert "power" in SCRYFALL_KEYWORDS
        assert "usd" in SCRYFALL_KEYWORDS

        # Check that it's a set
        assert isinstance(SCRYFALL_KEYWORDS, set)
        assert len(SCRYFALL_KEYWORDS) > 50  # Should have many keywords

    def test_magic_colors(self):
        """Test Magic color definitions."""
        assert MAGIC_COLORS == ["W", "U", "B", "R", "G"]
        assert isinstance(MAGIC_COLORS, list)

    def test_magic_types(self):
        """Test Magic type definitions."""
        essential_types = {
            "Artifact",
            "Creature",
            "Enchantment",
            "Instant",
            "Land",
            "Planeswalker",
            "Sorcery",
            "Basic",
            "Legendary",
        }
        assert essential_types.issubset(MAGIC_TYPES)
        assert isinstance(MAGIC_TYPES, set)

    def test_search_patterns(self):
        """Test search pattern definitions."""
        assert "mana_cost_pattern" in SEARCH_PATTERNS
        assert "number_pattern" in SEARCH_PATTERNS
        assert "quoted_text_pattern" in SEARCH_PATTERNS

        # Test that patterns are valid regex
        import re

        for pattern_name, pattern in SEARCH_PATTERNS.items():
            try:
                re.compile(pattern)
            except re.error:
                pytest.fail(f"Invalid regex pattern for {pattern_name}: {pattern}")


class TestLanguageMapping:
    """Test LanguageMapping base class."""

    def test_language_mapping_structure(self):
        """Test that LanguageMapping has required structure."""
        # Both mappings should be instances of LanguageMapping
        assert isinstance(english_mapping, LanguageMapping)
        assert isinstance(japanese_mapping, LanguageMapping)

    def test_required_fields(self):
        """Test that mappings have all required fields."""
        for mapping in [english_mapping, japanese_mapping]:
            assert hasattr(mapping, "language_code")
            assert hasattr(mapping, "language_name")
            assert hasattr(mapping, "locale_code")
            assert hasattr(mapping, "colors")
            assert hasattr(mapping, "types")
            assert hasattr(mapping, "operators")
            assert hasattr(mapping, "formats")
            assert hasattr(mapping, "rarities")
            assert hasattr(mapping, "set_types")
            assert hasattr(mapping, "search_keywords")
            assert hasattr(mapping, "phrases")

    def test_color_mappings_consistency(self):
        """Test that color mappings are consistent."""
        required_colors = {"white", "blue", "black", "red", "green", "colorless"}

        for mapping in [english_mapping, japanese_mapping]:
            assert set(mapping.colors.keys()) == required_colors
            # All values should map to single character codes
            for color, code in mapping.colors.items():
                assert len(code) == 1
                assert code.lower() in "wubrgc"

    def test_operator_mappings_consistency(self):
        """Test that operator mappings are consistent."""
        required_operators = {
            "equals",
            "not_equals",
            "less_than",
            "less_than_or_equal",
            "greater_than",
            "greater_than_or_equal",
            "contains",
            "not_contains",
        }

        for mapping in [english_mapping, japanese_mapping]:
            assert set(mapping.operators.keys()) == required_operators

    def test_format_mappings_consistency(self):
        """Test that format mappings are consistent."""
        required_formats = {
            "standard",
            "pioneer",
            "modern",
            "legacy",
            "vintage",
            "commander",
            "pauper",
            "historic",
            "alchemy",
            "brawl",
        }

        for mapping in [english_mapping, japanese_mapping]:
            assert set(mapping.formats.keys()) == required_formats

    def test_rarity_mappings_consistency(self):
        """Test that rarity mappings are consistent."""
        required_rarities = {"common", "uncommon", "rare", "mythic", "special", "bonus"}

        for mapping in [english_mapping, japanese_mapping]:
            assert set(mapping.rarities.keys()) == required_rarities


class TestEnglishMapping:
    """Test English language mapping."""

    def test_english_mapping_metadata(self):
        """Test English mapping metadata."""
        assert english_mapping.language_code == "en"
        assert english_mapping.language_name == "English"
        assert english_mapping.locale_code == "en_US"

    def test_english_color_mappings(self):
        """Test English color mappings."""
        expected_colors = {
            "white": "w",
            "blue": "u",
            "black": "b",
            "red": "r",
            "green": "g",
            "colorless": "c",
        }
        assert english_mapping.colors == expected_colors

    def test_english_search_keywords(self):
        """Test English search keywords."""
        keywords = english_mapping.search_keywords

        # Test basic search terms
        assert keywords["color"] == "c"
        assert keywords["mana"] == "m"
        assert keywords["type"] == "t"
        assert keywords["power"] == "p"
        assert keywords["rarity"] == "r"

        # Test that some values are empty (implicit operators)
        assert keywords["and"] == ""

    def test_english_phrases(self):
        """Test English phrases."""
        phrases = english_mapping.phrases

        # Test creature-specific phrases
        assert phrases["creatures with"] == "t:creature"
        assert phrases["white cards"] == "c:w"

        # Test power/toughness phrases
        assert phrases["power greater than"] == "p>"
        assert phrases["toughness equal to"] == "tou="

    def test_english_type_mappings(self):
        """Test English type mappings."""
        types = english_mapping.types

        # Basic types should map to themselves
        assert types["creature"] == "creature"
        assert types["artifact"] == "artifact"
        assert types["enchantment"] == "enchantment"


class TestJapaneseMapping:
    """Test Japanese language mapping."""

    def test_japanese_mapping_metadata(self):
        """Test Japanese mapping metadata."""
        assert japanese_mapping.language_code == "ja"
        assert japanese_mapping.language_name == "日本語"
        assert japanese_mapping.locale_code == "ja_JP"

    def test_japanese_color_mappings(self):
        """Test Japanese color mappings are same as English."""
        # Color codes should be the same as English
        assert japanese_mapping.colors == english_mapping.colors

    def test_japanese_search_keywords(self):
        """Test Japanese search keywords."""
        keywords = japanese_mapping.search_keywords

        # Test color keywords
        assert keywords["白"] == "c:w"
        assert keywords["青"] == "c:u"
        assert keywords["黒"] == "c:b"
        assert keywords["赤"] == "c:r"
        assert keywords["緑"] == "c:g"
        assert keywords["無色"] == "c:c"

        # Test card type keywords
        assert keywords["クリーチャー"] == "t:creature"
        assert keywords["アーティファクト"] == "t:artifact"
        assert keywords["インスタント"] == "t:instant"

        # Test comparison operators
        assert keywords["以上"] == ">="
        assert keywords["以下"] == "<="
        assert keywords["より大きい"] == ">"

    def test_japanese_phrases(self):
        """Test Japanese phrases."""
        phrases = japanese_mapping.phrases

        # Test creature-specific phrases
        assert phrases["を持つクリーチャー"] == "t:creature"
        assert phrases["白のカード"] == "c:w"

        # Test power/toughness phrases
        assert phrases["パワーがより大きい"] == "p>"
        assert phrases["タフネスが等しい"] == "tou="

    def test_japanese_card_names(self):
        """Test Japanese card name mappings are deprecated.

        The JAPANESE_CARD_NAMES dictionary is now deprecated because Scryfall
        natively supports multilingual card names. Japanese card names are
        passed directly to Scryfall API which handles the lookup automatically.
        """
        # Test that JAPANESE_CARD_NAMES exists but is empty (deprecated)
        assert isinstance(JAPANESE_CARD_NAMES, dict)
        assert len(JAPANESE_CARD_NAMES) == 0  # Should be empty - deprecated

        # All values should be valid English card names
        for ja_name, en_name in JAPANESE_CARD_NAMES.items():
            assert isinstance(ja_name, str)
            assert isinstance(en_name, str)
            assert len(ja_name) > 0
            assert len(en_name) > 0

    def test_japanese_format_mappings(self):
        """Test Japanese format mappings."""
        keywords = japanese_mapping.search_keywords

        # Test format keywords
        assert keywords["スタンダード"] == "f:standard"
        assert keywords["モダン"] == "f:modern"
        assert keywords["レガシー"] == "f:legacy"
        assert keywords["コマンダー"] == "f:commander"

    def test_japanese_rarity_mappings(self):
        """Test Japanese rarity mappings."""
        keywords = japanese_mapping.search_keywords

        # Test rarity keywords
        assert keywords["コモン"] == "r:common"
        assert keywords["アンコモン"] == "r:uncommon"
        assert keywords["レア"] == "r:rare"
        assert keywords["神話レア"] == "r:mythic"

    def test_japanese_keyword_ability_mappings_phase1(self):
        """Test Japanese keyword ability mappings - Phase 1 (Evergreen keywords).

        Tests implementation of Issue #2: キーワード能力による自然言語検索の精度向上
        Phase 1 covers evergreen keyword abilities that appear in most sets.
        """
        keywords = japanese_mapping.search_keywords

        # Test evergreen keyword abilities with all variations
        # 飛行 (flying)
        assert keywords["飛行"] == "keyword:flying"
        assert keywords["飛行を持つ"] == "keyword:flying"
        assert keywords["飛行持ち"] == "keyword:flying"

        # 速攻 (haste)
        assert keywords["速攻"] == "keyword:haste"
        assert keywords["速攻を持つ"] == "keyword:haste"
        assert keywords["速攻持ち"] == "keyword:haste"

        # 接死 (deathtouch)
        assert keywords["接死"] == "keyword:deathtouch"
        assert keywords["接死を持つ"] == "keyword:deathtouch"
        assert keywords["接死持ち"] == "keyword:deathtouch"

        # トランプル (trample)
        assert keywords["トランプル"] == "keyword:trample"
        assert keywords["トランプルを持つ"] == "keyword:trample"
        assert keywords["トランプル持ち"] == "keyword:trample"

        # 警戒 (vigilance)
        assert keywords["警戒"] == "keyword:vigilance"
        assert keywords["警戒を持つ"] == "keyword:vigilance"
        assert keywords["警戒持ち"] == "keyword:vigilance"

        # 先制攻撃 (first strike) - requires quotes
        assert keywords["先制攻撃"] == 'keyword:"first strike"'
        assert keywords["先制攻撃を持つ"] == 'keyword:"first strike"'
        assert keywords["先制攻撃持ち"] == 'keyword:"first strike"'

        # 二段攻撃 (double strike) - requires quotes
        assert keywords["二段攻撃"] == 'keyword:"double strike"'
        assert keywords["二段攻撃を持つ"] == 'keyword:"double strike"'
        assert keywords["二段攻撃持ち"] == 'keyword:"double strike"'

        # 絆魂 (lifelink)
        assert keywords["絆魂"] == "keyword:lifelink"
        assert keywords["絆魂を持つ"] == "keyword:lifelink"
        assert keywords["絆魂持ち"] == "keyword:lifelink"

        # 呪禁 (hexproof)
        assert keywords["呪禁"] == "keyword:hexproof"
        assert keywords["呪禁を持つ"] == "keyword:hexproof"
        assert keywords["呪禁持ち"] == "keyword:hexproof"

        # 到達 (reach)
        assert keywords["到達"] == "keyword:reach"
        assert keywords["到達を持つ"] == "keyword:reach"
        assert keywords["到達持ち"] == "keyword:reach"

    def test_japanese_keyword_ability_mappings_phase2(self):
        """Test Japanese keyword ability mappings - Phase 2 (Common deciduous keywords).

        Tests implementation of Issue #2: キーワード能力による自然言語検索の精度向上
        Phase 2 covers common deciduous keyword abilities.
        """
        keywords = japanese_mapping.search_keywords

        # Test common deciduous keyword abilities
        # 威迫 (menace)
        assert keywords["威迫"] == "keyword:menace"
        assert keywords["威迫を持つ"] == "keyword:menace"
        assert keywords["威迫持ち"] == "keyword:menace"

        # 瞬速 (flash)
        assert keywords["瞬速"] == "keyword:flash"
        assert keywords["瞬速を持つ"] == "keyword:flash"
        assert keywords["瞬速持ち"] == "keyword:flash"

        # 多相 (changeling)
        assert keywords["多相"] == "keyword:changeling"
        assert keywords["多相を持つ"] == "keyword:changeling"
        assert keywords["多相持ち"] == "keyword:changeling"

        # 防衛 (defender)
        assert keywords["防衛"] == "keyword:defender"
        assert keywords["防衛を持つ"] == "keyword:defender"
        assert keywords["防衛持ち"] == "keyword:defender"

        # 護法 (ward)
        assert keywords["護法"] == "keyword:ward"
        assert keywords["護法を持つ"] == "keyword:ward"
        assert keywords["護法持ち"] == "keyword:ward"

    def test_japanese_ability_phrases_triggers(self):
        """Test Japanese ability phrase mappings - Trigger abilities.

        Tests implementation of Issue #4: 長文クエリ対応
        Tests trigger ability phrases.
        """
        keywords = japanese_mapping.search_keywords

        # Death triggers
        assert keywords["死亡時"] == 'o:"when ~ dies"'
        assert keywords["死亡したとき"] == 'o:"when ~ dies"'
        assert keywords["墓地に置かれたとき"] == 'o:"when ~ dies"'

        # ETB/LTB triggers
        assert keywords["戦場に出たとき"] == 'o:"enters the battlefield"'
        assert keywords["戦場を離れたとき"] == 'o:"leaves the battlefield"'

        # Combat triggers
        assert keywords["攻撃したとき"] == 'o:"whenever ~ attacks"'
        assert keywords["ブロックしたとき"] == 'o:"whenever ~ blocks"'
        assert keywords["ダメージを与えたとき"] == 'o:"whenever ~ deals damage"'

    def test_japanese_ability_phrases_control(self):
        """Test Japanese ability phrase mappings - Control-related.

        Tests implementation of Issue #4: 長文クエリ対応
        Tests control-related phrases.
        """
        keywords = japanese_mapping.search_keywords

        # Control phrases
        assert keywords["あなたがコントロールする"] == 'o:"you control"'
        assert keywords["対戦相手がコントロールする"] == 'o:"opponent controls"'
        assert keywords["対戦相手を対象とする"] == 'o:"target opponent"'

    def test_japanese_ability_phrases_effects(self):
        """Test Japanese ability phrase mappings - Common effects.

        Tests implementation of Issue #4: 長文クエリ対応
        Tests common effect phrases.
        """
        keywords = japanese_mapping.search_keywords

        # Draw effects
        assert keywords["カードを引く"] == 'o:"draw"'
        assert keywords["カードを1枚引く"] == 'o:"draw a card"'
        assert keywords["カードを2枚引く"] == 'o:"draw two cards"'

        # Removal effects
        assert keywords["破壊"] == 'o:"destroy"'
        assert keywords["破壊する"] == 'o:"destroy"'
        assert keywords["追放"] == 'o:"exile"'
        assert keywords["追放する"] == 'o:"exile"'
        assert keywords["生け贄"] == 'o:"sacrifice"'
        assert keywords["生け贄に捧げる"] == 'o:"sacrifice"'

        # Life effects
        assert keywords["ライフを得る"] == 'o:"gain life"'
        assert keywords["ライフを失う"] == 'o:"lose life"'

        # Damage effects
        assert keywords["ダメージを与える"] == 'o:"deals damage"'
        assert keywords["ダメージを受ける"] == 'o:"damage"'

    def test_japanese_ability_phrases_targeting(self):
        """Test Japanese ability phrase mappings - Targeting.

        Tests implementation of Issue #4: 長文クエリ対応
        Tests targeting phrases.
        """
        keywords = japanese_mapping.search_keywords

        # Targeting phrases
        assert keywords["クリーチャーを対象とする"] == 'o:"target creature"'
        assert keywords["プレイヤーを対象とする"] == 'o:"target player"'
        assert keywords["パーマネントを対象とする"] == 'o:"target permanent"'
        assert keywords["呪文を対象とする"] == 'o:"target spell"'


class TestMappingValidation:
    """Test mapping validation and consistency."""

    def test_no_duplicate_values_in_card_names(self):
        """Test that there are no duplicate values in card name mappings."""
        # Check for duplicate English names
        english_names = list(JAPANESE_CARD_NAMES.values())
        assert len(english_names) == len(set(english_names))

    def test_no_empty_mappings(self):
        """Test that no mappings are empty."""
        for mapping in [english_mapping, japanese_mapping]:
            assert len(mapping.colors) > 0
            assert len(mapping.types) > 0
            assert len(mapping.operators) > 0
            assert len(mapping.formats) > 0
            assert len(mapping.rarities) > 0

    def test_search_keyword_consistency(self):
        """Test that search keywords don't conflict."""
        for mapping in [english_mapping, japanese_mapping]:
            # Check that we don't have conflicting mappings
            keywords = mapping.search_keywords

            # No keyword should map to empty string unless intentional
            empty_mappings = [k for k, v in keywords.items() if v == ""]
            # These are intentional empty mappings (implicit operators)
            allowed_empty = {
                "and",
                "かつ",
                "そして",
                "でかつ",
                "を持つカード",
                "のカード",
            }
            unexpected_empty = set(empty_mappings) - allowed_empty
            assert len(unexpected_empty) == 0, (
                f"Unexpected empty mappings: {unexpected_empty}"
            )

    def test_phrase_consistency(self):
        """Test that phrases are consistent."""
        for mapping in [english_mapping, japanese_mapping]:
            phrases = mapping.phrases

            # Check that phrases with similar meanings have consistent mappings
            color_phrases = {
                k: v
                for k, v in phrases.items()
                if "cards" in k.lower() or "カード" in k
            }
            for phrase, mapping_value in color_phrases.items():
                if mapping_value.startswith("c:"):
                    color_code = mapping_value[2:]
                    assert color_code in "wubrgc", (
                        f"Invalid color code in phrase: {phrase} -> {mapping_value}"
                    )

    def test_japanese_specific_validations(self):
        """Test Japanese-specific validations."""
        # Test that Japanese color words are single characters
        ja_colors = ["白", "青", "黒", "赤", "緑"]
        for color in ja_colors:
            assert len(color) == 1, (
                f"Japanese color should be single character: {color}"
            )

        # JAPANESE_CARD_NAMES is now deprecated - Scryfall handles multilingual names natively
        # No need to validate card name mappings as they're no longer used

    def test_mapping_types_are_correct(self):
        """Test that all mapping values have correct types."""
        for mapping in [english_mapping, japanese_mapping]:
            # Colors should map to single character strings
            for color, code in mapping.colors.items():
                assert isinstance(code, str)
                assert len(code) == 1

            # Operators should map to operator strings
            for op, symbol in mapping.operators.items():
                assert isinstance(symbol, str)
                assert len(symbol) > 0

            # Search keywords should map to strings
            for keyword, scryfall_term in mapping.search_keywords.items():
                assert isinstance(scryfall_term, str)

            # Phrases should map to strings
            for phrase, replacement in mapping.phrases.items():
                assert isinstance(replacement, str)
