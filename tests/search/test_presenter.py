"""Tests for search presenter module."""

from __future__ import annotations

from uuid import uuid4

import pytest
from mcp.types import EmbeddedResource, ImageContent, TextContent

from scryfall_mcp.api.models import Card, CardFace, ImageUris, SearchResult
from scryfall_mcp.i18n import english_mapping, japanese_mapping
from scryfall_mcp.search.models import BuiltQuery, SearchOptions
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

    def test_present_results_basic_en(self, en_presenter, sample_search_result, basic_built_query):
        """Test basic result presentation in English."""
        options = SearchOptions(max_results=10, include_images=False)
        results = en_presenter.present_results(sample_search_result, basic_built_query, options)

        assert len(results) >= 1
        assert isinstance(results[0], TextContent)
        assert "Search Results" in results[0].text
        assert "test query" in results[0].text
        assert "Cards Found" in results[0].text and "1" in results[0].text

    def test_present_results_basic_ja(self, ja_presenter, sample_search_result, basic_built_query):
        """Test basic result presentation in Japanese."""
        options = SearchOptions(max_results=10, include_images=False)
        results = ja_presenter.present_results(sample_search_result, basic_built_query, options)

        assert len(results) >= 1
        assert isinstance(results[0], TextContent)
        assert "検索結果" in results[0].text
        assert "test query" in results[0].text
        assert "1枚" in results[0].text

    def test_present_results_with_images(self, en_presenter, card_with_images, basic_built_query):
        """Test result presentation with images."""
        search_result = SearchResult(
            object="list",
            total_cards=1,
            has_more=False,
            data=[card_with_images],
        )
        options = SearchOptions(max_results=10, include_images=True)
        results = en_presenter.present_results(search_result, basic_built_query, options)

        # Should have: summary + card text + card resource + image
        image_contents = [r for r in results if isinstance(r, ImageContent)]
        assert len(image_contents) >= 1
        assert image_contents[0].mimeType == "image/jpeg"

    def test_present_results_without_images(self, en_presenter, card_with_images, basic_built_query):
        """Test result presentation without images."""
        search_result = SearchResult(
            object="list",
            total_cards=1,
            has_more=False,
            data=[card_with_images],
        )
        options = SearchOptions(max_results=10, include_images=False)
        results = en_presenter.present_results(search_result, basic_built_query, options)

        # Should not have image contents
        image_contents = [r for r in results if isinstance(r, ImageContent)]
        assert len(image_contents) == 0

    def test_present_results_with_suggestions(self, en_presenter, sample_search_result):
        """Test result presentation with suggestions."""
        built_query = BuiltQuery(
            original_query="test",
            scryfall_query="test",
            query_metadata={},
            suggestions=["Try using exact card names", "Use more specific terms"],
        )
        options = SearchOptions(max_results=10, include_images=False)
        results = en_presenter.present_results(sample_search_result, built_query, options)

        # Find suggestions content
        suggestion_contents = [r for r in results if isinstance(r, TextContent) and "Suggestions" in r.text]
        assert len(suggestion_contents) >= 1
        assert "Try using exact card names" in suggestion_contents[0].text
        assert "Use more specific terms" in suggestion_contents[0].text

    def test_present_results_with_suggestions_ja(self, ja_presenter, sample_search_result):
        """Test result presentation with suggestions in Japanese."""
        built_query = BuiltQuery(
            original_query="テスト",
            scryfall_query="test",
            query_metadata={},
            suggestions=["正確なカード名を使用してください", "より具体的な用語を使用してください"],
        )
        options = SearchOptions(max_results=10, include_images=False)
        results = ja_presenter.present_results(sample_search_result, built_query, options)

        # Find suggestions content
        suggestion_contents = [r for r in results if isinstance(r, TextContent) and "検索のヒント" in r.text]
        assert len(suggestion_contents) >= 1
        assert "正確なカード名を使用してください" in suggestion_contents[0].text

    def test_present_results_complex_query(self, en_presenter, sample_search_result, complex_built_query):
        """Test result presentation with complex query explanation."""
        options = SearchOptions(max_results=10, include_images=False)
        results = en_presenter.present_results(sample_search_result, complex_built_query, options)

        # Find query explanation content
        explanation_contents = [r for r in results if isinstance(r, TextContent) and "Query Analysis" in r.text]
        assert len(explanation_contents) >= 1
        assert "Complexity" in explanation_contents[0].text and "complex" in explanation_contents[0].text
        assert "Colors" in explanation_contents[0].text
        assert "red" in explanation_contents[0].text

    def test_present_results_complex_query_ja(self, ja_presenter, sample_search_result, complex_built_query):
        """Test result presentation with complex query explanation in Japanese."""
        options = SearchOptions(max_results=10, include_images=False)
        results = ja_presenter.present_results(sample_search_result, complex_built_query, options)

        # Find query explanation content
        explanation_contents = [r for r in results if isinstance(r, TextContent) and "検索クエリの詳細" in r.text]
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

    def test_create_summary_partial_results(self, en_presenter, basic_built_query, sample_card):
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
        options = SearchOptions(max_results=10, include_images=False)
        card_text = en_presenter._format_single_card(sample_card, 1, options)

        assert isinstance(card_text, TextContent)
        assert "## 1. Lightning Bolt" in card_text.text
        assert "{R}" in card_text.text
        assert "Type" in card_text.text and "Instant" in card_text.text
        assert "3 damage" in card_text.text

    def test_format_single_card_ja(self, ja_presenter, sample_card):
        """Test card formatting in Japanese."""
        options = SearchOptions(max_results=10, include_images=False)
        card_text = ja_presenter._format_single_card(sample_card, 1, options)

        assert isinstance(card_text, TextContent)
        assert "## 1. Lightning Bolt" in card_text.text
        assert "タイプ" in card_text.text
        assert "効果" in card_text.text
        assert "セット" in card_text.text

    def test_format_creature_card(self, en_presenter, creature_card):
        """Test creature card formatting with power/toughness."""
        options = SearchOptions(max_results=10, include_images=False)
        card_text = en_presenter._format_single_card(creature_card, 1, options)

        assert "2/3" in card_text.text

    def test_format_creature_card_ja(self, ja_presenter, creature_card):
        """Test creature card formatting in Japanese."""
        options = SearchOptions(max_results=10, include_images=False)
        card_text = ja_presenter._format_single_card(creature_card, 1, options)

        assert "2/3" in card_text.text

    def test_format_card_with_rarity(self, en_presenter, sample_card):
        """Test card formatting with rarity information."""
        options = SearchOptions(max_results=10, include_images=False)
        card_text = en_presenter._format_single_card(sample_card, 1, options)

        assert "Common" in card_text.text

    def test_format_card_with_rarity_ja(self, ja_presenter, sample_card):
        """Test card formatting with rarity in Japanese."""
        options = SearchOptions(max_results=10, include_images=False)
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
        resource = en_presenter._create_card_resource(sample_card, 1)

        assert isinstance(resource, EmbeddedResource)
        assert resource.type == "resource"
        assert "card://scryfall/" in str(resource.resource.uri)
        assert resource.resource.mimeType == "application/json"
        assert "Lightning Bolt" in resource.resource.text

    def test_create_card_resource_with_faces(self, en_presenter, double_faced_card):
        """Test creating embedded resource for double-faced card."""
        resource = en_presenter._create_card_resource(double_faced_card, 1)

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
        options = SearchOptions(max_results=10, include_images=False)
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
        options = SearchOptions(max_results=3, include_images=False)
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
        card_texts = [r for r in results if isinstance(r, TextContent) and "## " in r.text]
        assert len(card_texts) <= 3

    def test_rarity_translations(self, en_presenter, sample_card_data):
        """Test all rarity translations in English."""
        rarities = ["common", "uncommon", "rare", "mythic"]
        expected = ["Common", "Uncommon", "Rare", "Mythic Rare"]

        for rarity, expected_text in zip(rarities, expected):
            data = sample_card_data.copy()
            data["rarity"] = rarity
            card = Card(**data)
            options = SearchOptions(max_results=10, include_images=False)
            card_text = en_presenter._format_single_card(card, 1, options)
            assert expected_text in card_text.text

    def test_rarity_translations_ja(self, ja_presenter, sample_card_data):
        """Test all rarity translations in Japanese."""
        rarities = ["common", "uncommon", "rare", "mythic"]
        expected = ["コモン", "アンコモン", "レア", "神話レア"]

        for rarity, expected_text in zip(rarities, expected):
            data = sample_card_data.copy()
            data["rarity"] = rarity
            card = Card(**data)
            options = SearchOptions(max_results=10, include_images=False)
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

        options = SearchOptions(max_results=10, include_images=False)
        card_text = en_presenter._format_single_card(card, 1, options)

        # Should still have basic info
        assert "Lightning Bolt" in card_text.text
        assert "Type" in card_text.text

    def test_scryfall_link_en(self, en_presenter, sample_card):
        """Test Scryfall link in English."""
        options = SearchOptions(max_results=10, include_images=False)
        card_text = en_presenter._format_single_card(sample_card, 1, options)

        assert "View on Scryfall" in card_text.text

    def test_scryfall_link_ja(self, ja_presenter, sample_card):
        """Test Scryfall link in Japanese."""
        options = SearchOptions(max_results=10, include_images=False)
        card_text = ja_presenter._format_single_card(sample_card, 1, options)

        assert "Scryfallで詳細を見る" in card_text.text
