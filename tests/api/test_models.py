"""Tests for API models."""

from __future__ import annotations

from datetime import date
from uuid import UUID

import pytest
from pydantic import ValidationError

from scryfall_mcp.models import (
    AutocompleteRequest,
    BulkData,
    Card,
    CardFace,
    Catalog,
    ImageUris,
    Legalities,
    Prices,
    Ruling,
    ScryfallError,
    SearchCardsRequest,
    SearchResult,
    Set,
)


class TestImageUris:
    """Test ImageUris model."""

    def test_valid_image_uris(self):
        """Test valid image URIs."""
        image_uris = ImageUris(
            small="https://c1.scryfall.com/file/scryfall-cards/small/test.jpg",
            normal="https://c1.scryfall.com/file/scryfall-cards/normal/test.jpg",
            large="https://c1.scryfall.com/file/scryfall-cards/large/test.jpg",
            png="https://c1.scryfall.com/file/scryfall-cards/png/test.png",
        )

        assert str(image_uris.small).endswith("small/test.jpg")
        assert str(image_uris.normal).endswith("normal/test.jpg")
        assert str(image_uris.large).endswith("large/test.jpg")
        assert str(image_uris.png).endswith("png/test.png")

    def test_optional_fields(self):
        """Test that all fields are optional."""
        image_uris = ImageUris()
        assert image_uris.small is None
        assert image_uris.normal is None
        assert image_uris.large is None
        assert image_uris.png is None

    def test_invalid_url_validation(self):
        """Test that invalid URLs raise ValidationError."""
        # Invalid URL format
        with pytest.raises(ValidationError) as exc_info:
            ImageUris(small="not a url")
        assert "url" in str(exc_info.value).lower()

        # Non-HTTP(S) URL
        with pytest.raises(ValidationError) as exc_info:
            ImageUris(normal="ftp://example.com/image.jpg")
        assert "url" in str(exc_info.value).lower()

        # Malformed URL
        with pytest.raises(ValidationError) as exc_info:
            ImageUris(large="http://")
        assert "url" in str(exc_info.value).lower()


class TestLegalities:
    """Test Legalities model."""

    def test_default_legalities(self):
        """Test default legality values."""
        legalities = Legalities()
        assert legalities.standard == "not_legal"
        assert legalities.modern == "not_legal"
        assert legalities.legacy == "not_legal"
        assert legalities.vintage == "not_legal"
        assert legalities.commander == "not_legal"

    def test_custom_legalities(self):
        """Test custom legality values."""
        legalities = Legalities(
            standard="legal",
            modern="legal",
            legacy="legal",
            vintage="restricted",
            commander="legal",
        )

        assert legalities.standard == "legal"
        assert legalities.modern == "legal"
        assert legalities.legacy == "legal"
        assert legalities.vintage == "restricted"
        assert legalities.commander == "legal"


class TestPrices:
    """Test Prices model."""

    def test_valid_prices(self):
        """Test valid price strings."""
        prices = Prices(
            usd="1.50",
            usd_foil="3.00",
            eur="1.25",
            eur_foil="2.50",
            tix="0.10",
        )

        assert prices.usd == "1.50"
        assert prices.usd_foil == "3.00"
        assert prices.eur == "1.25"
        assert prices.eur_foil == "2.50"
        assert prices.tix == "0.10"

    def test_invalid_prices(self):
        """Test that invalid price strings are converted to None."""
        prices = Prices(
            usd="invalid",
            usd_foil="not_a_number",
            eur="",
        )

        assert prices.usd is None
        assert prices.usd_foil is None
        assert prices.eur is None

    def test_none_prices(self):
        """Test None prices."""
        prices = Prices()
        assert prices.usd is None
        assert prices.usd_foil is None
        assert prices.eur is None


class TestCardFace:
    """Test CardFace model."""

    def test_minimal_card_face(self):
        """Test minimal card face."""
        face = CardFace(
            name="Lightning Bolt",
            type_line="Instant",
        )

        assert face.name == "Lightning Bolt"
        assert face.type_line == "Instant"
        assert face.object == "card_face"
        assert face.mana_cost is None
        assert face.oracle_text is None

    def test_complete_card_face(self):
        """Test complete card face."""
        face = CardFace(
            name="Grizzly Bears",
            mana_cost="{1}{G}",
            type_line="Creature — Bear",
            oracle_text="A bear's got to do what a bear's got to do.",
            colors=["G"],
            power="2",
            toughness="2",
            flavor_text="Bears are among the most dangerous creatures in the wild.",
        )

        assert face.name == "Grizzly Bears"
        assert face.mana_cost == "{1}{G}"
        assert face.type_line == "Creature — Bear"
        assert face.colors == ["G"]
        assert face.power == "2"
        assert face.toughness == "2"


class TestCard:
    """Test Card model."""

    def test_minimal_card(self, sample_card_data):
        """Test minimal card creation."""
        # Remove optional fields for minimal test
        minimal_data = {
            key: value for key, value in sample_card_data.items()
            if key in {
                "object", "id", "oracle_id", "name", "lang", "released_at",
                "uri", "scryfall_uri", "layout", "type_line", "legalities",
                "set_id", "set", "set_name", "set_type", "set_uri",
                "set_search_uri", "scryfall_set_uri", "rulings_uri",
                "prints_search_uri", "collector_number", "rarity",
                "border_color", "frame", "prices", "related_uris",
                "purchase_uris",
            }
        }

        card = Card(**minimal_data)
        assert card.name == "Lightning Bolt"
        assert card.lang == "en"
        assert isinstance(card.id, UUID)
        assert isinstance(card.oracle_id, UUID)

    def test_complete_card(self, sample_card):
        """Test complete card with all fields."""
        assert sample_card.name == "Lightning Bolt"
        assert sample_card.mana_cost == "{R}"
        assert sample_card.cmc == 1.0
        assert sample_card.type_line == "Instant"
        assert sample_card.oracle_text == "Lightning Bolt deals 3 damage to any target."
        assert sample_card.colors == ["R"]
        assert sample_card.color_identity == ["R"]
        assert sample_card.rarity == "common"
        assert sample_card.set == "lea"
        assert sample_card.artist == "Christopher Rush"

    def test_card_validation(self):
        """Test card validation."""
        # Test that required fields are enforced
        with pytest.raises(ValidationError):
            Card()

        # Test that UUIDs are properly validated
        with pytest.raises(ValidationError):
            Card(id="invalid-uuid")

    def test_card_url_validation(self):
        """Test that invalid URLs in card data raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Card(
                id="8f05b5e7-c1aa-4a6c-b832-9d53ac0e3bc3",
                oracle_id="8f05b5e7-c1aa-4a6c-b832-9d53ac0e3bc3",
                name="Test Card",
                lang="en",
                released_at="2020-01-01",
                uri="not a valid url",  # Invalid URL
                scryfall_uri="https://scryfall.com/card/test",
                layout="normal",
                type_line="Creature",
                legalities=Legalities(),
                set_id="8f05b5e7-c1aa-4a6c-b832-9d53ac0e3bc3",
                set="tst",
                set_name="Test Set",
                set_type="core",
                set_uri="https://api.scryfall.com/sets/tst",
                set_search_uri="https://api.scryfall.com/cards/search?q=set:tst",
                scryfall_set_uri="https://scryfall.com/sets/tst",
                rulings_uri="https://api.scryfall.com/cards/test/rulings",
                prints_search_uri="https://api.scryfall.com/cards/search?q=name:test",
                collector_number="1",
                rarity="common",
                border_color="black",
                frame="2015",
                prices=Prices(),
                related_uris={},
                purchase_uris={},
            )
        assert "url" in str(exc_info.value).lower()

    def test_card_nested_validation(self):
        """Test validation of nested structures in card data."""
        # Test invalid image_uris
        with pytest.raises(ValidationError) as exc_info:
            Card(
                id="8f05b5e7-c1aa-4a6c-b832-9d53ac0e3bc3",
                oracle_id="8f05b5e7-c1aa-4a6c-b832-9d53ac0e3bc3",
                name="Test Card",
                lang="en",
                released_at="2020-01-01",
                uri="https://api.scryfall.com/cards/test",
                scryfall_uri="https://scryfall.com/card/test",
                layout="normal",
                type_line="Creature",
                legalities=Legalities(),
                set_id="8f05b5e7-c1aa-4a6c-b832-9d53ac0e3bc3",
                set="tst",
                set_name="Test Set",
                set_type="core",
                set_uri="https://api.scryfall.com/sets/tst",
                set_search_uri="https://api.scryfall.com/cards/search?q=set:tst",
                scryfall_set_uri="https://scryfall.com/sets/tst",
                rulings_uri="https://api.scryfall.com/cards/test/rulings",
                prints_search_uri="https://api.scryfall.com/cards/search?q=name:test",
                collector_number="1",
                rarity="common",
                border_color="black",
                frame="2015",
                prices=Prices(),
                related_uris={},
                purchase_uris={},
                image_uris=ImageUris(small="invalid url"),  # Invalid nested URL
            )
        assert "url" in str(exc_info.value).lower()


class TestSearchResult:
    """Test SearchResult model."""

    def test_search_result(self, sample_search_result):
        """Test search result creation."""
        assert sample_search_result.object == "list"
        assert sample_search_result.total_cards == 1
        assert sample_search_result.has_more is False
        assert len(sample_search_result.data) == 1
        assert isinstance(sample_search_result.data[0], Card)

    def test_empty_search_result(self):
        """Test empty search result."""
        result = SearchResult(
            object="list",
            total_cards=0,
            has_more=False,
            data=[],
        )

        assert result.total_cards == 0
        assert result.has_more is False
        assert len(result.data) == 0

    def test_search_result_with_pagination(self, sample_card):
        """Test search result with pagination."""
        result = SearchResult(
            object="list",
            total_cards=100,
            has_more=True,
            next_page="https://api.scryfall.com/cards/search?page=2",
            data=[sample_card],
        )

        assert result.total_cards == 100
        assert result.has_more is True
        assert result.next_page is not None


class TestScryfallError:
    """Test ScryfallError model."""

    def test_scryfall_error(self):
        """Test Scryfall error creation."""
        error = ScryfallError(
            object="error",
            code="not_found",
            status=404,
            details="No cards found matching your search.",
            warnings=["This is a warning"],
        )

        assert error.object == "error"
        assert error.code == "not_found"
        assert error.status == 404
        assert error.details == "No cards found matching your search."
        assert error.warnings == ["This is a warning"]

    def test_minimal_error(self):
        """Test minimal error."""
        error = ScryfallError(
            code="bad_request",
            status=400,
        )

        assert error.code == "bad_request"
        assert error.status == 400
        assert error.object == "error"
        assert error.details is None


class TestSet:
    """Test Set model."""

    def test_set_creation(self):
        """Test set creation."""
        set_data = Set(
            id="5d34a0c7-e61c-4d02-b5ce-84f6e35d5e27",
            code="lea",
            name="Limited Edition Alpha",
            set_type="core",
            card_count=295,
            released_at=date(1993, 8, 5),
            scryfall_uri="https://scryfall.com/sets/lea",
            uri="https://api.scryfall.com/sets/lea",
            icon_svg_uri="https://c2.scryfall.com/file/scryfall-symbols/sets/lea.svg",
            search_uri="https://api.scryfall.com/cards/search?order=set&q=e%3Alea",
        )

        assert set_data.code == "lea"
        assert set_data.name == "Limited Edition Alpha"
        assert set_data.set_type == "core"
        assert set_data.card_count == 295
        assert set_data.released_at == date(1993, 8, 5)


class TestRuling:
    """Test Ruling model."""

    def test_ruling_creation(self):
        """Test ruling creation."""
        ruling = Ruling(
            object="ruling",
            oracle_id="8f05b5e7-c1aa-4a6c-b832-9d53ac0e3bc3",
            source="wotc",
            published_at=date(2020, 1, 1),
            comment="This is a ruling about the card.",
        )

        assert ruling.object == "ruling"
        assert isinstance(ruling.oracle_id, UUID)
        assert ruling.source == "wotc"
        assert ruling.published_at == date(2020, 1, 1)
        assert ruling.comment == "This is a ruling about the card."


class TestCatalog:
    """Test Catalog model."""

    def test_catalog_creation(self):
        """Test catalog creation."""
        catalog = Catalog(
            object="catalog",
            uri="https://api.scryfall.com/catalog/card-names",
            total_values=3,
            data=["Lightning Bolt", "Grizzly Bears", "Black Lotus"],
        )

        assert catalog.object == "catalog"
        assert catalog.total_values == 3
        assert len(catalog.data) == 3
        assert "Lightning Bolt" in catalog.data


class TestBulkData:
    """Test BulkData model."""

    def test_bulk_data_creation(self):
        """Test bulk data creation."""
        from datetime import datetime

        bulk_data = BulkData(
            object="bulk_data",
            id="5d34a0c7-e61c-4d02-b5ce-84f6e35d5e27",
            type="oracle_cards",
            updated_at=datetime(2023, 1, 1, 12, 0, 0),
            uri="https://api.scryfall.com/bulk-data/oracle-cards",
            name="Oracle Cards",
            description="All Oracle cards in Scryfall's database.",
            size=50000000,
            download_uri="https://data.scryfall.io/oracle-cards/oracle-cards.json",
        )

        assert bulk_data.object == "bulk_data"
        assert bulk_data.type == "oracle_cards"
        assert bulk_data.name == "Oracle Cards"
        assert bulk_data.size == 50000000
        assert bulk_data.content_type == "application/json"
        assert bulk_data.content_encoding == "gzip"



class TestSearchCardsRequest:
    """Test SearchCardsRequest model."""

    def test_valid_request(self):
        """Test valid search request."""
        request = SearchCardsRequest(
            query="Lightning Bolt",
            language="en",
            max_results=10,
            include_images=True,
            format_filter="modern",
        )

        assert request.query == "Lightning Bolt"
        assert request.language == "en"
        assert request.max_results == 10
        assert request.include_images is True
        assert request.format_filter == "modern"

    def test_minimal_request(self):
        """Test minimal search request with defaults."""
        request = SearchCardsRequest(query="test")

        assert request.query == "test"
        assert request.language is None
        assert request.max_results == 10  # Default (reduced from 20 for macOS compatibility)
        assert request.include_images is True  # Default
        assert request.format_filter is None

    def test_max_results_validation(self):
        """Test max_results boundary validation."""
        # Valid boundaries
        request = SearchCardsRequest(query="test", max_results=1)
        assert request.max_results == 1

        request = SearchCardsRequest(query="test", max_results=175)
        assert request.max_results == 175

        # Invalid: less than 1
        with pytest.raises(ValidationError) as exc_info:
            SearchCardsRequest(query="test", max_results=0)
        assert "greater than or equal to 1" in str(exc_info.value)

        # Invalid: greater than 175
        with pytest.raises(ValidationError) as exc_info:
            SearchCardsRequest(query="test", max_results=176)
        assert "less than or equal to 175" in str(exc_info.value)

    def test_required_query(self):
        """Test that query is required."""
        with pytest.raises(ValidationError) as exc_info:
            SearchCardsRequest()
        assert "query" in str(exc_info.value)


class TestAutocompleteRequest:
    """Test AutocompleteRequest model."""

    def test_valid_request(self):
        """Test valid autocomplete request."""
        request = AutocompleteRequest(
            query="Light",
            language="en",
        )

        assert request.query == "Light"
        assert request.language == "en"

    def test_minimal_request(self):
        """Test minimal request."""
        request = AutocompleteRequest(query="Bol")

        assert request.query == "Bol"
        assert request.language is None

    def test_required_query(self):
        """Test that query is required."""
        with pytest.raises(ValidationError) as exc_info:
            AutocompleteRequest()
        assert "query" in str(exc_info.value)
