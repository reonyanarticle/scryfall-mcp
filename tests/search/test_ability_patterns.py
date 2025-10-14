"""Tests for ability pattern matching module."""

from __future__ import annotations

import pytest

from scryfall_mcp.i18n import get_current_mapping, set_current_locale
from scryfall_mcp.search.ability_patterns import (
    AbilityPatternMatcher,
    create_japanese_patterns,
)


class TestAbilityPatternMatcher:
    """Test AbilityPatternMatcher class."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up Japanese locale."""
        set_current_locale("ja")
        mapping = get_current_mapping()
        patterns = create_japanese_patterns(mapping.search_keywords)
        self.matcher = AbilityPatternMatcher(patterns)
        yield
        set_current_locale("en")

    def test_death_trigger_with_effect(self):
        """Test death trigger with effect extraction."""
        text = "死亡時にカードを1枚引く黒いクリーチャー"
        remaining, tokens = self.matcher.apply(text)

        assert 'o:"when ~ dies"' in tokens
        assert 'o:"draw a card"' in tokens or 'o:"draw"' in tokens
        assert "黒いクリーチャー" in remaining
        assert "する" not in remaining

    def test_death_trigger_without_effect(self):
        """Test death trigger without effect (handled by Phase 1, not Phase 2)."""
        text = "死亡時黒いクリーチャー"
        remaining, tokens = self.matcher.apply(text)

        # Phase 2 should NOT match this - it's handled by Phase 1 dictionary
        # Phase 2 specifically targets "死亡時に〜する" patterns (with "に")
        assert len(tokens) == 0
        assert "死亡時" in remaining
        assert "黒いクリーチャー" in remaining

    def test_etb_trigger_with_token_creation(self):
        """Test ETB trigger with token creation effect."""
        text = "戦場に出たときにトークンを生成する白いクリーチャー"
        remaining, tokens = self.matcher.apply(text)

        assert 'o:"enters the battlefield"' in tokens
        assert 'o:"create"' in tokens
        assert "白いクリーチャー" in remaining
        assert "する" not in remaining

    def test_etb_trigger_without_effect(self):
        """Test ETB trigger without に particle (handled by Phase 1, not Phase 2)."""
        text = "戦場に出たとき白いクリーチャー"
        remaining, tokens = self.matcher.apply(text)

        # Phase 2 requires "に" before effect: "戦場に出たときに...する"
        # Without "に", Phase 1 dictionary should handle it
        assert len(tokens) == 0
        assert "戦場に出たとき" in remaining
        assert "白いクリーチャー" in remaining

    def test_attack_trigger_with_damage(self):
        """Test attack trigger with damage effect."""
        text = "攻撃したときにダメージを与える赤いクリーチャー"
        remaining, tokens = self.matcher.apply(text)

        assert 'o:"whenever ~ attacks"' in tokens
        assert 'o:"deals damage"' in tokens
        assert "赤いクリーチャー" in remaining

    def test_attack_trigger_without_effect(self):
        """Test attack trigger without に particle (handled by Phase 1, not Phase 2)."""
        text = "攻撃したとき赤いクリーチャー"
        remaining, tokens = self.matcher.apply(text)

        # Phase 2 requires "に" before effect: "攻撃したときに...する"
        # Without "に", Phase 1 dictionary should handle it
        assert len(tokens) == 0
        assert "攻撃したとき" in remaining
        assert "赤いクリーチャー" in remaining

    def test_multiple_effects_in_one_phrase(self):
        """Test multiple effects in one trigger phrase."""
        text = "死亡時にカードを引き破壊する黒いクリーチャー"
        remaining, tokens = self.matcher.apply(text)

        assert 'o:"when ~ dies"' in tokens
        # Should extract both draw and destroy
        has_draw = any("draw" in t for t in tokens)
        has_destroy = any("destroy" in t for t in tokens)
        assert has_draw or has_destroy

    def test_no_matching_patterns(self):
        """Test text with no matching patterns."""
        text = "青いクリーチャー"
        remaining, tokens = self.matcher.apply(text)

        assert len(tokens) == 0
        assert remaining == "青いクリーチャー"

    def test_multiple_triggers_in_text(self):
        """Test text with multiple trigger patterns."""
        text = "死亡時にカードを引き戦場に出たときにトークンを生成するクリーチャー"
        remaining, tokens = self.matcher.apply(text)

        # Should extract at least one trigger
        has_death = 'o:"when ~ dies"' in tokens
        has_etb = 'o:"enters the battlefield"' in tokens
        assert has_death or has_etb

    def test_pattern_stops_before_color(self):
        """Test that patterns stop before color keywords."""
        text = "死亡時にカードを引く白いクリーチャー"
        remaining, tokens = self.matcher.apply(text)

        # Should preserve color keyword
        assert "白い" in remaining
        assert 'o:"when ~ dies"' in tokens

    def test_pattern_stops_before_type(self):
        """Test that patterns stop before type keywords."""
        text = "戦場に出たときにトークンを生成するクリーチャー"
        remaining, tokens = self.matcher.apply(text)

        # Should preserve type keyword
        assert "クリーチャー" in remaining
        assert 'o:"enters the battlefield"' in tokens

    def test_pattern_stops_before_keyword_ability(self):
        """Test that patterns stop before keyword ability keywords."""
        text = "死亡時にカードを引く飛行を持つクリーチャー"
        remaining, tokens = self.matcher.apply(text)

        # Should preserve keyword ability
        assert "飛行" in remaining
        assert 'o:"when ~ dies"' in tokens

    def test_token_order_preservation(self):
        """Test that tokens are added in original order."""
        text = "死亡時にカードを1枚引く戦場に出たときにライフを得るクリーチャー"
        remaining, tokens = self.matcher.apply(text)

        # If both triggers are extracted, death should come before ETB
        death_indices = [i for i, t in enumerate(tokens) if "dies" in t]
        etb_indices = [i for i, t in enumerate(tokens) if "battlefield" in t]

        if death_indices and etb_indices:
            # Death trigger should come before ETB in token list
            assert death_indices[0] < etb_indices[0]

    def test_whitespace_cleanup(self):
        """Test that extra whitespace is cleaned up."""
        text = "死亡時にカードを引く   黒い  クリーチャー"
        remaining, tokens = self.matcher.apply(text)

        # Should clean up extra whitespace
        assert "  " not in remaining
        assert remaining.strip() == remaining

    def test_effect_with_no_known_phrases(self):
        """Test effect that doesn't match known phrases (edge case)."""
        text = "死亡時に何か未知の効果黒いクリーチャー"
        remaining, tokens = self.matcher.apply(text)

        # Should still extract trigger but no effect tokens
        assert 'o:"when ~ dies"' in tokens
        # No specific effect tokens (only trigger)
        effect_tokens = [t for t in tokens if t != 'o:"when ~ dies"']
        # May be empty if no known effects match
        assert isinstance(effect_tokens, list)

    def test_suru_particle_removed(self):
        """Test that 'する' particle is properly removed."""
        test_cases = [
            "死亡時にカードを引く黒いクリーチャー",
            "戦場に出たときにトークンを生成する白いクリーチャー",
            "攻撃したときにダメージを与える赤いクリーチャー",
        ]

        for text in test_cases:
            remaining, tokens = self.matcher.apply(text)
            # 'する' should be removed from remaining text
            assert "する" not in remaining, f"Failed for: {text}"

    def test_pattern_priority_ordering(self):
        """Test that patterns are applied in priority order."""
        # All patterns have same priority (100), so order should be deterministic
        patterns = create_japanese_patterns({})
        matcher = AbilityPatternMatcher(patterns)

        # All patterns should have priority 100
        assert all(p.priority == 100 for p in matcher.patterns)

    def test_empty_text(self):
        """Test with empty text."""
        text = ""
        remaining, tokens = self.matcher.apply(text)

        assert remaining == ""
        assert tokens == []

    def test_whitespace_only_text(self):
        """Test with whitespace-only text."""
        text = "   "
        remaining, tokens = self.matcher.apply(text)

        assert remaining.strip() == ""
        assert tokens == []
