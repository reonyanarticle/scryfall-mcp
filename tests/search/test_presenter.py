"""Tests for search presenter module."""

from __future__ import annotations

import pytest
from mcp.types import EmbeddedResource, ImageContent, TextContent

from scryfall_mcp.i18n import english_mapping, japanese_mapping
from scryfall_mcp.models import (
    BuiltQuery,
    Card,
    SearchOptions,
    SearchResult,
)
from scryfall_mcp.search.presenter import SearchPresenter


class TestSearchPresenter:
    """Test SearchPresenter class."""

    @pytest.fixture
    def en_presenter(self):
        """Create an English presenter."""
        return SearchPresenter(english_mapping)

    @pytest.fixture
    def ja_presenter(self):
        """Create a Japanese presenter."""
        return SearchPresenter(japanese_mapping)

    @pytest.fixture
    def basic_built_query(self):
        """Create a basic built query."""
        return BuiltQuery(
            original_query="test query",
            scryfall_query="test",
            query_metadata={},
            suggestions=[],
        )

    @pytest.fixture
    def complex_built_query(self):
        """Create a complex built query with metadata."""
        return BuiltQuery(
            original_query="complex query",
            scryfall_query="c:red t:creature pow>=3",
            query_metadata={
                "query_complexity": "complex",
                "estimated_results": "100+",
                "extracted_entities": {
                    "colors": ["red"],
                    "types": ["creature"],
                    "numbers": ["3"],
                    "card_names": [],
                    "sets": [],
                    "formats": [],
                },
            },
            suggestions=["Try narrowing down with specific mana cost"],
        )

    @pytest.fixture
    def card_with_images(self, sample_card_data):
        """Create a card with image URIs."""
        data = sample_card_data.copy()
        data["image_uris"] = {
            "small": "https://example.com/small.jpg",
            "normal": "https://example.com/normal.jpg",
            "large": "https://example.com/large.jpg",
            "png": "https://example.com/card.png",
            "art_crop": "https://example.com/art.jpg",
            "border_crop": "https://example.com/border.jpg",
        }
        return Card(**data)

    @pytest.fixture
    def creature_card(self, sample_card_data):
        """Create a creature card with power/toughness."""
        data = sample_card_data.copy()
        data["type_line"] = "Creature — Human Wizard"
        data["power"] = "2"
        data["toughness"] = "3"
        return Card(**data)

    @pytest.fixture
    def double_faced_card(self, sample_card_data):
        """Create a double-faced card."""
        data = sample_card_data.copy()
        data["name"] = "Delver of Secrets // Insectile Aberration"
        data["card_faces"] = [
            {
                "name": "Delver of Secrets",
                "mana_cost": "{U}",
                "type_line": "Creature — Human Wizard",
                "oracle_text": "At the beginning of your upkeep...",
                "power": "1",
                "toughness": "1",
            },
            {
                "name": "Insectile Aberration",
                "mana_cost": "",
                "type_line": "Creature — Human Insect",
                "oracle_text": "Flying",
                "power": "3",
                "toughness": "2",
            },
        ]
        return Card(**data)

    def test_present_results_basic_en(
        self, en_presenter, sample_search_result, basic_built_query
    ):
        """Test basic result presentation in English."""
        options = SearchOptions(
            max_results=10,
        )
        results = en_presenter.present_results(
            sample_search_result, basic_built_query, options
        )

        assert len(results) >= 1
        assert isinstance(results[0], TextContent)
        assert "Search Results" in results[0].text
        assert "test query" in results[0].text
        assert "Cards Found" in results[0].text and "1" in results[0].text

    def test_present_results_basic_ja(
        self, ja_presenter, sample_search_result, basic_built_query
    ):
        """Test basic result presentation in Japanese."""
        options = SearchOptions(
            max_results=10,
        )
        results = ja_presenter.present_results(
            sample_search_result, basic_built_query, options
        )

        assert len(results) >= 1
        assert isinstance(results[0], TextContent)
        assert "検索結果" in results[0].text
        assert "test query" in results[0].text
        assert "1枚" in results[0].text

    def test_present_results_no_image_data(
        self, en_presenter, card_with_images, basic_built_query
    ):
        """Test that ImageContent is not included (MCP spec compliance)."""
        search_result = SearchResult(
            object="list",
            total_cards=1,
            has_more=False,
            data=[card_with_images],
        )
        options = SearchOptions(
            max_results=10,
        )
        results = en_presenter.present_results(
            search_result, basic_built_query, options
        )

        # ImageContent removed - MCP spec requires base64, not URLs
        # Image URLs are in text content and EmbeddedResource instead
        image_contents = [r for r in results if isinstance(r, ImageContent)]
        assert len(image_contents) == 0

        # Verify image URL is in text content
        text_contents = [r for r in results if isinstance(r, TextContent)]
        assert any("scryfall.com" in tc.text for tc in text_contents)

    def test_present_results_with_suggestions(self, en_presenter, sample_search_result):
        """Test result presentation with suggestions."""
        built_query = BuiltQuery(
            original_query="test",
            scryfall_query="test",
            query_metadata={},
            suggestions=["Try using exact card names", "Use more specific terms"],
        )
        options = SearchOptions(
            max_results=10,
        )
        results = en_presenter.present_results(
            sample_search_result, built_query, options
        )

        # Find suggestions content
        suggestion_contents = [
            r for r in results if isinstance(r, TextContent) and "Suggestions" in r.text
        ]
        assert len(suggestion_contents) >= 1
        assert "Try using exact card names" in suggestion_contents[0].text
        assert "Use more specific terms" in suggestion_contents[0].text

    def test_present_results_with_suggestions_ja(
        self, ja_presenter, sample_search_result
    ):
        """Test result presentation with suggestions in Japanese."""
        built_query = BuiltQuery(
            original_query="テスト",
            scryfall_query="test",
            query_metadata={},
            suggestions=[
                "正確なカード名を使用してください",
                "より具体的な用語を使用してください",
            ],
        )
        options = SearchOptions(
            max_results=10,
        )
        results = ja_presenter.present_results(
            sample_search_result, built_query, options
        )

        # Find suggestions content
        suggestion_contents = [
            r
            for r in results
            if isinstance(r, TextContent) and "検索のヒント" in r.text
        ]
        assert len(suggestion_contents) >= 1
        assert "正確なカード名を使用してください" in suggestion_contents[0].text

    def test_present_results_complex_query(
        self, en_presenter, sample_search_result, complex_built_query
    ):
        """Test result presentation with complex query explanation."""
        options = SearchOptions(
            max_results=10,
        )
        results = en_presenter.present_results(
            sample_search_result, complex_built_query, options
        )

        # Find query explanation content
        explanation_contents = [
            r
            for r in results
            if isinstance(r, TextContent) and "Query Analysis" in r.text
        ]
        assert len(explanation_contents) >= 1
        assert (
            "Complexity" in explanation_contents[0].text
            and "complex" in explanation_contents[0].text
        )
        assert "Colors" in explanation_contents[0].text
        assert "red" in explanation_contents[0].text

    def test_present_results_complex_query_ja(
        self, ja_presenter, sample_search_result, complex_built_query
    ):
        """Test result presentation with complex query explanation in Japanese."""
        options = SearchOptions(
            max_results=10,
        )
        results = ja_presenter.present_results(
            sample_search_result, complex_built_query, options
        )

        # Find query explanation content
        explanation_contents = [
            r
            for r in results
            if isinstance(r, TextContent) and "検索クエリの詳細" in r.text
        ]
        assert len(explanation_contents) >= 1
        assert "複雑さ" in explanation_contents[0].text
        assert "色" in explanation_contents[0].text

    def test_create_summary_has_more(self, en_presenter, basic_built_query):
        """Test summary creation with more results available."""
        search_result = SearchResult(
            object="list",
            total_cards=100,
            has_more=True,
            data=[],
        )
        summary = en_presenter._create_summary(search_result, basic_built_query)

        assert isinstance(summary, TextContent)
        assert "More results are available" in summary.text

    def test_create_summary_has_more_ja(self, ja_presenter, basic_built_query):
        """Test summary creation with more results available in Japanese."""
        search_result = SearchResult(
            object="list",
            total_cards=100,
            has_more=True,
            data=[],
        )
        summary = ja_presenter._create_summary(search_result, basic_built_query)

        assert isinstance(summary, TextContent)
        assert "さらに多くの結果があります" in summary.text

    def test_create_summary_partial_results(
        self, en_presenter, basic_built_query, sample_card
    ):
        """Test summary creation showing partial results."""
        search_result = SearchResult(
            object="list",
            total_cards=50,
            has_more=False,
            data=[sample_card],  # Only 1 card in data but 50 total
        )
        summary = en_presenter._create_summary(search_result, basic_built_query)

        assert "showing first 1" in summary.text

    def test_format_single_card_basic(self, en_presenter, sample_card):
        """Test basic card formatting."""
        options = SearchOptions(
            max_results=10,
        )
        card_text = en_presenter._format_single_card(sample_card, 1, options)

        assert isinstance(card_text, TextContent)
        assert "## 1. Lightning Bolt" in card_text.text
        assert "{R}" in card_text.text
        assert "Type" in card_text.text and "Instant" in card_text.text
        assert "3 damage" in card_text.text

    def test_format_single_card_ja(self, ja_presenter, sample_card):
        """Test card formatting in Japanese."""
        options = SearchOptions(
            max_results=10,
        )
        card_text = ja_presenter._format_single_card(sample_card, 1, options)

        assert isinstance(card_text, TextContent)
        assert "## 1. Lightning Bolt" in card_text.text
        assert "タイプ" in card_text.text
        assert "効果" in card_text.text
        assert "セット" in card_text.text

    def test_format_creature_card(self, en_presenter, creature_card):
        """Test creature card formatting with power/toughness."""
        options = SearchOptions(
            max_results=10,
        )
        card_text = en_presenter._format_single_card(creature_card, 1, options)

        assert "2/3" in card_text.text

    def test_format_creature_card_ja(self, ja_presenter, creature_card):
        """Test creature card formatting in Japanese."""
        options = SearchOptions(
            max_results=10,
        )
        card_text = ja_presenter._format_single_card(creature_card, 1, options)

        assert "2/3" in card_text.text

    def test_format_card_with_rarity(self, en_presenter, sample_card):
        """Test card formatting with rarity information."""
        options = SearchOptions(
            max_results=10,
        )
        card_text = en_presenter._format_single_card(sample_card, 1, options)

        assert "Common" in card_text.text

    def test_format_card_with_rarity_ja(self, ja_presenter, sample_card):
        """Test card formatting with rarity in Japanese."""
        options = SearchOptions(
            max_results=10,
        )
        card_text = ja_presenter._format_single_card(sample_card, 1, options)

        assert "コモン" in card_text.text

    def test_format_prices(self, en_presenter):
        """Test price formatting."""
        prices = {
            "usd": "10.50",
            "eur": "9.25",
            "tix": "2.5",
        }
        price_text = en_presenter._format_prices(prices)

        assert "$10.50" in price_text
        assert "€9.25" in price_text
        assert "2.5 tix" in price_text
        assert "Price" in price_text

    def test_format_prices_ja(self, ja_presenter):
        """Test price formatting in Japanese."""
        prices = {
            "usd": "10.50",
            "eur": None,
            "tix": None,
        }
        price_text = ja_presenter._format_prices(prices)

        assert "$10.50" in price_text
        assert "価格" in price_text

    def test_format_prices_empty(self, en_presenter):
        """Test price formatting with no prices."""
        prices = {
            "usd": None,
            "eur": None,
            "tix": None,
        }
        price_text = en_presenter._format_prices(prices)

        assert price_text == ""

    def test_create_card_resource(self, en_presenter, sample_card):
        """Test creating embedded card resource."""
        options = SearchOptions(max_results=10)
        resource = en_presenter._create_card_resource(sample_card, 1, options)

        assert isinstance(resource, EmbeddedResource)
        assert resource.type == "resource"
        assert "card://scryfall/" in str(resource.resource.uri)
        assert resource.resource.mimeType == "application/json"
        assert "Lightning Bolt" in resource.resource.text

    def test_create_card_resource_with_faces(self, en_presenter, double_faced_card):
        """Test creating embedded resource for double-faced card."""
        options = SearchOptions(max_results=10)
        resource = en_presenter._create_card_resource(double_faced_card, 1, options)

        assert isinstance(resource, EmbeddedResource)
        assert "card_faces" in resource.resource.text
        assert "Delver of Secrets" in resource.resource.text
        assert "Insectile Aberration" in resource.resource.text

    def test_serialize_urls(self, en_presenter):
        """Test URL serialization."""
        from pydantic import HttpUrl

        data = {
            "url1": HttpUrl("https://example.com/1"),
            "url2": HttpUrl("https://example.com/2"),
            "url3": None,
        }
        serialized = en_presenter._serialize_urls(data)

        assert serialized["url1"] == "https://example.com/1"
        assert serialized["url2"] == "https://example.com/2"
        assert serialized["url3"] is None

    def test_create_query_explanation_entities(self, en_presenter):
        """Test query explanation with various entity types."""
        built_query = BuiltQuery(
            original_query="test",
            scryfall_query="test",
            query_metadata={
                "query_complexity": "complex",
                "estimated_results": "50",
                "extracted_entities": {
                    "colors": ["red", "blue"],
                    "types": ["creature", "instant"],
                    "numbers": ["3", "5"],
                    "card_names": ["Lightning Bolt"],
                    "sets": ["LEA"],
                    "formats": ["modern"],
                },
            },
            suggestions=[],
        )
        explanation = en_presenter._create_query_explanation(built_query)

        assert "Colors" in explanation.text and "red, blue" in explanation.text
        assert "Types" in explanation.text and "creature, instant" in explanation.text
        assert "Numbers" in explanation.text and "3, 5" in explanation.text
        assert "Card Names" in explanation.text and "Lightning Bolt" in explanation.text
        assert "Sets" in explanation.text and "LEA" in explanation.text
        assert "Formats" in explanation.text and "modern" in explanation.text

    def test_create_query_explanation_entities_ja(self, ja_presenter):
        """Test query explanation with entities in Japanese."""
        built_query = BuiltQuery(
            original_query="test",
            scryfall_query="test",
            query_metadata={
                "query_complexity": "complex",
                "extracted_entities": {
                    "colors": ["赤"],
                    "types": ["クリーチャー"],
                    "numbers": [],
                    "card_names": [],
                    "sets": [],
                    "formats": [],
                },
            },
            suggestions=[],
        )
        explanation = ja_presenter._create_query_explanation(built_query)

        assert "色" in explanation.text

    def test_format_cards_multiple(self, en_presenter, sample_card):
        """Test formatting multiple cards."""
        cards = [sample_card, sample_card]
        options = SearchOptions(
            max_results=10,
        )
        results = en_presenter._format_cards(cards, options)

        # Each card should produce 2 items: text content + embedded resource
        assert len(results) == 4  # 2 cards * 2 items each
        text_contents = [r for r in results if isinstance(r, TextContent)]
        embedded_resources = [r for r in results if isinstance(r, EmbeddedResource)]
        assert len(text_contents) == 2
        assert len(embedded_resources) == 2

    def test_format_cards_with_limit(self, en_presenter, sample_card):
        """Test formatting cards respects max_results limit."""
        cards = [sample_card] * 5
        options = SearchOptions(
            max_results=3,
        )
        search_result = SearchResult(
            object="list",
            total_cards=5,
            has_more=False,
            data=cards,
        )
        built_query = BuiltQuery(
            original_query="test",
            scryfall_query="test",
            query_metadata={},
            suggestions=[],
        )
        results = en_presenter.present_results(search_result, built_query, options)

        # Should only format first 3 cards
        card_texts = [
            r for r in results if isinstance(r, TextContent) and "## " in r.text
        ]
        assert len(card_texts) <= 3

    def test_rarity_translations(self, en_presenter, sample_card_data):
        """Test all rarity translations in English."""
        rarities = ["common", "uncommon", "rare", "mythic"]
        expected = ["Common", "Uncommon", "Rare", "Mythic Rare"]

        for rarity, expected_text in zip(rarities, expected, strict=False):
            data = sample_card_data.copy()
            data["rarity"] = rarity
            card = Card(**data)
            options = SearchOptions(
                max_results=10,
            )
            card_text = en_presenter._format_single_card(card, 1, options)
            assert expected_text in card_text.text

    def test_rarity_translations_ja(self, ja_presenter, sample_card_data):
        """Test all rarity translations in Japanese."""
        rarities = ["common", "uncommon", "rare", "mythic"]
        expected = ["コモン", "アンコモン", "レア", "神話レア"]

        for rarity, expected_text in zip(rarities, expected, strict=False):
            data = sample_card_data.copy()
            data["rarity"] = rarity
            card = Card(**data)
            options = SearchOptions(
                max_results=10,
            )
            card_text = ja_presenter._format_single_card(card, 1, options)
            assert expected_text in card_text.text

    def test_card_without_optional_fields(self, en_presenter, sample_card_data):
        """Test formatting card with minimal data."""
        data = sample_card_data.copy()
        data["mana_cost"] = None
        data["oracle_text"] = None
        data["power"] = None
        data["toughness"] = None
        # Set prices to all None values
        data["prices"] = {
            "usd": None,
            "usd_foil": None,
            "eur": None,
            "eur_foil": None,
            "tix": None,
        }
        card = Card(**data)

        options = SearchOptions(
            max_results=10,
        )
        card_text = en_presenter._format_single_card(card, 1, options)

        # Should still have basic info
        assert "Lightning Bolt" in card_text.text
        assert "Type" in card_text.text

    def test_scryfall_link_en(self, en_presenter, sample_card):
        """Test Scryfall link in English."""
        options = SearchOptions(
            max_results=10,
        )
        card_text = en_presenter._format_single_card(sample_card, 1, options)

        assert "View on Scryfall" in card_text.text

    def test_scryfall_link_ja(self, ja_presenter, sample_card):
        """Test Scryfall link in Japanese."""
        options = SearchOptions(
            max_results=10,
        )
        card_text = ja_presenter._format_single_card(sample_card, 1, options)

        assert "Scryfallで詳細を見る" in card_text.text

    def test_japanese_multilingual_card_display(
        self, ja_presenter, sample_card_data
    ):
        """Test that Japanese cards display printed_name, printed_type_line, and printed_text."""
        # Create a Japanese card with multilingual fields
        data = sample_card_data.copy()
        data["lang"] = "ja"
        data["printed_name"] = "稲妻"
        data["printed_type_line"] = "インスタント"
        data["printed_text"] = "稲妻は、クリーチャー1体かプレインズウォーカー1体かプレイヤー1人を対象とする。稲妻はそれに3点のダメージを与える。"
        card = Card(**data)

        options = SearchOptions(
            max_results=10,
        )
        card_text = ja_presenter._format_single_card(card, 1, options)

        # Should display Japanese printed name
        assert "稲妻" in card_text.text
        # Should display Japanese type line
        assert "インスタント" in card_text.text
        # Should display Japanese oracle text
        assert "稲妻は、クリーチャー1体かプレインズウォーカー1体かプレイヤー1人を対象とする" in card_text.text
        assert "**効果**:" in card_text.text

    def test_japanese_card_without_printed_fields(
        self, ja_presenter, sample_card_data
    ):
        """Test that Japanese cards fall back to English fields when printed fields are missing."""
        # Create a Japanese search without multilingual fields
        data = sample_card_data.copy()
        data["lang"] = "en"  # English card searched in Japanese
        card = Card(**data)

        options = SearchOptions(
            max_results=10,
        )
        card_text = ja_presenter._format_single_card(card, 1, options)

        # Should fall back to English name and text
        assert "Lightning Bolt" in card_text.text
        assert "Instant" in card_text.text
        assert "Lightning Bolt deals 3 damage to any target." in card_text.text
        assert "**効果**:" in card_text.text

    def test_english_card_ignores_printed_fields(
        self, en_presenter, sample_card_data
    ):
        """Test that English searches ignore printed_name even if present."""
        # Create a card with Japanese printed fields (shouldn't happen in practice)
        data = sample_card_data.copy()
        data["printed_name"] = "稲妻"
        data["printed_type_line"] = "インスタント"
        card = Card(**data)

        options = SearchOptions(
            max_results=10,
        )
        card_text = en_presenter._format_single_card(card, 1, options)

        # Should display English name, not printed_name
        assert "Lightning Bolt" in card_text.text
        assert "Instant" in card_text.text
        # Should not display Japanese fields
        assert "稲妻" not in card_text.text
        assert "インスタント" not in card_text.text

    # Phase 1 Tests: Keywords, Artist, Mana Production, Legalities, Annotations

    def test_keywords_display_en(self, en_presenter, sample_card_data):
        """Test keywords display in English."""
        data = sample_card_data.copy()
        data["keywords"] = ["Flying", "Haste", "Trample"]
        card = Card(**data)

        options = SearchOptions(max_results=10, include_keywords=True)
        card_text = en_presenter._format_single_card(card, 1, options)

        assert "Keywords" in card_text.text
        assert "Flying, Haste, Trample" in card_text.text

    def test_keywords_display_ja(self, ja_presenter, sample_card_data):
        """Test keywords display in Japanese."""
        data = sample_card_data.copy()
        data["keywords"] = ["Flying", "Haste"]
        card = Card(**data)

        options = SearchOptions(max_results=10, include_keywords=True)
        card_text = ja_presenter._format_single_card(card, 1, options)

        assert "キーワード能力" in card_text.text
        assert "Flying, Haste" in card_text.text

    def test_keywords_hidden_when_disabled(self, en_presenter, sample_card_data):
        """Test keywords are hidden when include_keywords=False."""
        data = sample_card_data.copy()
        data["keywords"] = ["Flying", "Haste"]
        card = Card(**data)

        options = SearchOptions(max_results=10, include_keywords=False)
        card_text = en_presenter._format_single_card(card, 1, options)

        assert "Keywords" not in card_text.text
        assert "Flying" not in card_text.text

    def test_artist_display_en(self, en_presenter, sample_card_data):
        """Test artist display in English."""
        data = sample_card_data.copy()
        data["artist"] = "Christopher Rush"
        card = Card(**data)

        options = SearchOptions(max_results=10, include_artist=True)
        card_text = en_presenter._format_single_card(card, 1, options)

        assert "Illustrated by Christopher Rush" in card_text.text

    def test_artist_display_ja(self, ja_presenter, sample_card_data):
        """Test artist display in Japanese."""
        data = sample_card_data.copy()
        data["artist"] = "Christopher Rush"
        card = Card(**data)

        options = SearchOptions(max_results=10, include_artist=True)
        card_text = ja_presenter._format_single_card(card, 1, options)

        assert "イラスト Christopher Rush" in card_text.text

    def test_artist_hidden_when_disabled(self, en_presenter, sample_card_data):
        """Test artist is hidden when include_artist=False."""
        data = sample_card_data.copy()
        data["artist"] = "Christopher Rush"
        card = Card(**data)

        options = SearchOptions(max_results=10, include_artist=False)
        card_text = en_presenter._format_single_card(card, 1, options)

        assert "Illustrated by" not in card_text.text

    def test_mana_production_display_en(self, en_presenter, sample_card_data):
        """Test mana production display for lands in English."""
        data = sample_card_data.copy()
        data["type_line"] = "Land"
        data["produced_mana"] = ["W", "U"]
        card = Card(**data)

        options = SearchOptions(max_results=10, include_mana_production=True)
        card_text = en_presenter._format_single_card(card, 1, options)

        assert "Produces" in card_text.text
        assert "{W}" in card_text.text
        assert "{U}" in card_text.text

    def test_mana_production_display_ja(self, ja_presenter, sample_card_data):
        """Test mana production display for lands in Japanese."""
        data = sample_card_data.copy()
        data["type_line"] = "Land"  # type_line is always in English in real API data
        data["printed_type_line"] = "土地"  # Japanese printed type
        data["produced_mana"] = ["R", "G"]
        card = Card(**data)

        options = SearchOptions(max_results=10, include_mana_production=True)
        card_text = ja_presenter._format_single_card(card, 1, options)

        assert "生成マナ" in card_text.text
        assert "{R}" in card_text.text
        assert "{G}" in card_text.text

    def test_mana_production_not_shown_for_nonlands(self, en_presenter, sample_card_data):
        """Test mana production is not shown for non-land cards."""
        data = sample_card_data.copy()
        data["type_line"] = "Creature — Elf Druid"
        data["produced_mana"] = ["G"]
        card = Card(**data)

        options = SearchOptions(max_results=10, include_mana_production=True)
        card_text = en_presenter._format_single_card(card, 1, options)

        assert "Produces" not in card_text.text

    def test_mana_production_hidden_when_disabled(self, en_presenter, sample_card_data):
        """Test mana production is hidden when include_mana_production=False."""
        data = sample_card_data.copy()
        data["type_line"] = "Land"
        data["produced_mana"] = ["W"]
        card = Card(**data)

        options = SearchOptions(max_results=10, include_mana_production=False)
        card_text = en_presenter._format_single_card(card, 1, options)

        assert "Produces" not in card_text.text

    def test_format_legality_display_en(self, en_presenter, sample_card_data):
        """Test format legality display in English."""
        data = sample_card_data.copy()
        data["legalities"] = {
            "standard": "legal",
            "modern": "banned",
            "legacy": "restricted",
            "vintage": "not_legal",
        }
        card = Card(**data)

        options = SearchOptions(max_results=10, format_filter="modern")
        card_text = en_presenter._format_single_card(card, 1, options)

        assert "Modern" in card_text.text
        assert "Banned" in card_text.text

    def test_format_legality_display_ja(self, ja_presenter, sample_card_data):
        """Test format legality display in Japanese."""
        data = sample_card_data.copy()
        data["legalities"] = {"standard": "legal"}
        card = Card(**data)

        options = SearchOptions(max_results=10, format_filter="standard")
        card_text = ja_presenter._format_single_card(card, 1, options)

        assert "Standard" in card_text.text
        assert "適正" in card_text.text

    def test_format_legality_all_statuses(self, en_presenter, sample_card_data):
        """Test all format legality statuses."""
        statuses = {
            "legal": "Legal",
            "not_legal": "Not Legal",
            "restricted": "Restricted",
            "banned": "Banned",
        }

        for status, expected in statuses.items():
            data = sample_card_data.copy()
            data["legalities"] = {"modern": status}
            card = Card(**data)

            options = SearchOptions(max_results=10, format_filter="modern")
            card_text = en_presenter._format_single_card(card, 1, options)

            assert expected in card_text.text

    def test_format_legality_not_shown_without_filter(self, en_presenter, sample_card_data):
        """Test format legality is not shown when no format_filter is set."""
        data = sample_card_data.copy()
        data["legalities"] = {"modern": "legal"}
        card = Card(**data)

        options = SearchOptions(max_results=10)
        card_text = en_presenter._format_single_card(card, 1, options)

        assert "Modern" not in card_text.text or "Type" in card_text.text  # "Modern" might appear elsewhere

    def test_annotations_in_format_single_card(self, en_presenter, sample_card_data):
        """Test MCP Annotations are included in _format_single_card."""
        card = Card(**sample_card_data)

        options = SearchOptions(max_results=10, use_annotations=True)
        card_text = en_presenter._format_single_card(card, 1, options)

        assert card_text.annotations is not None
        assert card_text.annotations.audience == ["user", "assistant"]
        assert card_text.annotations.priority == 0.8

    def test_annotations_disabled_in_format_single_card(self, en_presenter, sample_card_data):
        """Test Annotations are not included when use_annotations=False."""
        card = Card(**sample_card_data)

        options = SearchOptions(max_results=10, use_annotations=False)
        card_text = en_presenter._format_single_card(card, 1, options)

        assert card_text.annotations is None

    def test_annotations_in_create_card_resource(self, en_presenter, sample_card_data):
        """Test MCP Annotations are included in _create_card_resource."""
        card = Card(**sample_card_data)

        options = SearchOptions(max_results=10, use_annotations=True)
        resource = en_presenter._create_card_resource(card, 1, options)

        assert resource.annotations is not None
        assert resource.annotations.audience == ["assistant"]
        assert resource.annotations.priority == 0.6

    def test_annotations_disabled_in_create_card_resource(self, en_presenter, sample_card_data):
        """Test Annotations are not included in resource when use_annotations=False."""
        card = Card(**sample_card_data)

        options = SearchOptions(max_results=10, use_annotations=False)
        resource = en_presenter._create_card_resource(card, 1, options)

        assert resource.annotations is None

    def test_phase1_metadata_in_resource(self, en_presenter, sample_card_data):
        """Test Phase 1 metadata fields are included in card resource."""
        data = sample_card_data.copy()
        data["keywords"] = ["Flying", "Haste"]
        data["flavor_text"] = "The spark of genius ignites in the strangest of places."
        data["artist"] = "Christopher Rush"
        data["produced_mana"] = ["R"]
        data["edhrec_rank"] = 42
        card = Card(**data)

        options = SearchOptions(max_results=10)
        resource = en_presenter._create_card_resource(card, 1, options)

        import json
        resource_data = json.loads(resource.resource.text)

        assert resource_data["keywords"] == ["Flying", "Haste"]
        assert resource_data["flavor_text"] == "The spark of genius ignites in the strangest of places."
        assert resource_data["artist"] == "Christopher Rush"
        assert resource_data["produced_mana"] == ["R"]
        assert resource_data["edhrec_rank"] == 42

    def test_combined_phase1_features(self, en_presenter, sample_card_data):
        """Test all Phase 1 features working together."""
        data = sample_card_data.copy()
        data["keywords"] = ["Flying", "Vigilance"]
        data["artist"] = "Seb McKinnon"
        data["type_line"] = "Land"
        data["produced_mana"] = ["W", "U"]
        data["legalities"] = {"modern": "legal"}
        card = Card(**data)

        options = SearchOptions(
            max_results=10,
            format_filter="modern",
            include_keywords=True,
            include_artist=True,
            include_mana_production=True,
            use_annotations=True,
        )
        card_text = en_presenter._format_single_card(card, 1, options)

        # All Phase 1 features should be present
        assert "Keywords" in card_text.text
        assert "Flying, Vigilance" in card_text.text
        assert "Produces" in card_text.text
        assert "{W}" in card_text.text
        assert "{U}" in card_text.text
        assert "Modern" in card_text.text
        assert "Legal" in card_text.text
        assert "Illustrated by Seb McKinnon" in card_text.text
        assert card_text.annotations is not None

    # Phase 3 Tests: include_legalities

    def test_legalities_in_resource_when_enabled(self, en_presenter, sample_card_data):
        """Test Phase 3: legalities are included in resource when include_legalities=True."""
        data = sample_card_data.copy()
        data["legalities"] = {
            "standard": "not_legal",
            "modern": "legal",
            "legacy": "legal",
            "vintage": "restricted",
            "commander": "banned",
            "pauper": "not_legal",
        }
        card = Card(**data)

        options = SearchOptions(max_results=10, include_legalities=True)
        resource = en_presenter._create_card_resource(card, 1, options)

        import json
        resource_data = json.loads(resource.resource.text)

        # Should include legalities, but exclude "not_legal" entries
        assert "legalities" in resource_data
        assert "modern" in resource_data["legalities"]
        assert resource_data["legalities"]["modern"] == "legal"
        assert "legacy" in resource_data["legalities"]
        assert resource_data["legalities"]["legacy"] == "legal"
        assert "vintage" in resource_data["legalities"]
        assert resource_data["legalities"]["vintage"] == "restricted"
        assert "commander" in resource_data["legalities"]
        assert resource_data["legalities"]["commander"] == "banned"
        # not_legal entries should be excluded
        assert "standard" not in resource_data["legalities"]
        assert "pauper" not in resource_data["legalities"]

    def test_legalities_not_in_resource_when_disabled(self, en_presenter, sample_card_data):
        """Test Phase 3: legalities are excluded when include_legalities=False (default)."""
        data = sample_card_data.copy()
        data["legalities"] = {
            "standard": "legal",
            "modern": "legal",
        }
        card = Card(**data)

        options = SearchOptions(max_results=10, include_legalities=False)
        resource = en_presenter._create_card_resource(card, 1, options)

        import json
        resource_data = json.loads(resource.resource.text)

        # legalities should not be included when disabled
        assert "legalities" not in resource_data

    def test_legalities_empty_when_all_not_legal(self, en_presenter, sample_card_data):
        """Test Phase 3: legalities field is not added if all statuses are not_legal."""
        data = sample_card_data.copy()
        data["legalities"] = {
            "standard": "not_legal",
            "modern": "not_legal",
            "legacy": "not_legal",
            "vintage": "not_legal",
            "commander": "not_legal",
        }
        card = Card(**data)

        options = SearchOptions(max_results=10, include_legalities=True)
        resource = en_presenter._create_card_resource(card, 1, options)

        import json
        resource_data = json.loads(resource.resource.text)

        # legalities field should not be present if all entries are not_legal
        assert "legalities" not in resource_data

    def test_all_features_combined_phase1_and_phase3(self, en_presenter, sample_card_data):
        """Test Phase 1 + Phase 3: All features working together."""
        data = sample_card_data.copy()
        data["keywords"] = ["Flying", "Vigilance", "Lifelink"]
        data["artist"] = "Seb McKinnon"
        data["type_line"] = "Land"
        data["produced_mana"] = ["W", "U", "B"]
        data["legalities"] = {
            "standard": "legal",
            "modern": "legal",
            "legacy": "legal",
            "vintage": "restricted",
            "commander": "legal",
            "pauper": "not_legal",
        }
        card = Card(**data)

        # Enable ALL Phase 1 + Phase 3 features
        options = SearchOptions(
            max_results=10,
            format_filter="modern",
            include_keywords=True,
            include_artist=True,
            include_mana_production=True,
            include_legalities=True,  # Phase 3
            use_annotations=True,
        )

        # Test TextContent (user-facing)
        card_text = en_presenter._format_single_card(card, 1, options)
        assert "Keywords" in card_text.text
        assert "Flying, Vigilance, Lifelink" in card_text.text
        assert "Produces" in card_text.text
        assert "{W}" in card_text.text
        assert "{U}" in card_text.text
        assert "{B}" in card_text.text
        assert "Modern" in card_text.text
        assert "Legal" in card_text.text
        assert "Illustrated by Seb McKinnon" in card_text.text
        assert card_text.annotations is not None
        assert card_text.annotations.audience == ["user", "assistant"]

        # Test EmbeddedResource (machine-readable)
        import json
        resource = en_presenter._create_card_resource(card, 1, options)
        resource_data = json.loads(resource.resource.text)

        # Phase 1 fields in resource
        assert resource_data["keywords"] == ["Flying", "Vigilance", "Lifelink"]
        assert resource_data["artist"] == "Seb McKinnon"
        assert resource_data["produced_mana"] == ["W", "U", "B"]

        # Phase 3: legalities in resource (not_legal excluded)
        assert "legalities" in resource_data
        assert "standard" in resource_data["legalities"]
        assert resource_data["legalities"]["standard"] == "legal"
        assert "modern" in resource_data["legalities"]
        assert "legacy" in resource_data["legalities"]
        assert "vintage" in resource_data["legalities"]
        assert resource_data["legalities"]["vintage"] == "restricted"
        assert "commander" in resource_data["legalities"]
        assert "pauper" not in resource_data["legalities"]  # not_legal excluded

        # Annotations in resource
        assert resource.annotations is not None
        assert resource.annotations.audience == ["assistant"]
