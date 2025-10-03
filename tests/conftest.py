"""Test configuration and fixtures."""

from __future__ import annotations

import asyncio
import os
from typing import Any
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import httpx
import pytest

from scryfall_mcp.models import Card, SearchResult
from scryfall_mcp.settings import Settings


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_settings() -> Settings:
    """Create test settings."""
    # Override environment variables for testing
    env_overrides = {
        "SCRYFALL_MCP_SCRYFALL_BASE_URL": "https://api.scryfall.com",
        "SCRYFALL_MCP_SCRYFALL_RATE_LIMIT_MS": "100",
        "SCRYFALL_MCP_CACHE_ENABLED": "true",
        "SCRYFALL_MCP_CACHE_BACKEND": "memory",
        "SCRYFALL_MCP_DEFAULT_LOCALE": "en",
        "SCRYFALL_MCP_DEBUG": "true",
        "SCRYFALL_MCP_MOCK_API": "true",
    }

    # Temporarily set environment variables
    original_values = {}
    for key, value in env_overrides.items():
        original_values[key] = os.environ.get(key)
        os.environ[key] = value

    try:
        settings = Settings()
        yield settings
    finally:
        # Restore original environment variables
        for key, original_value in original_values.items():
            if original_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original_value


@pytest.fixture
def mock_httpx_client():
    """Create a mock httpx client."""
    client = Mock(spec=httpx.AsyncClient)
    client.request = AsyncMock()
    client.aclose = AsyncMock()
    client.is_closed = False
    return client


@pytest.fixture
def sample_card_data() -> dict[str, Any]:
    """Sample card data for testing."""
    return {
        "object": "card",
        "id": str(uuid4()),
        "oracle_id": str(uuid4()),
        "multiverse_ids": [123456],
        "name": "Lightning Bolt",
        "lang": "en",
        "released_at": "1993-08-05",
        "uri": "https://api.scryfall.com/cards/test",
        "scryfall_uri": "https://scryfall.com/card/test",
        "layout": "normal",
        "highres_image": True,
        "image_status": "highres_scan",
        "mana_cost": "{R}",
        "cmc": 1.0,
        "type_line": "Instant",
        "oracle_text": "Lightning Bolt deals 3 damage to any target.",
        "colors": ["R"],
        "color_identity": ["R"],
        "keywords": [],
        "legalities": {
            "standard": "not_legal",
            "future": "not_legal",
            "historic": "legal",
            "gladiator": "legal",
            "pioneer": "legal",
            "explorer": "legal",
            "modern": "legal",
            "legacy": "legal",
            "pauper": "not_legal",
            "vintage": "legal",
            "penny": "not_legal",
            "commander": "legal",
            "oathbreaker": "legal",
            "brawl": "not_legal",
            "historicbrawl": "legal",
            "alchemy": "not_legal",
            "paupercommander": "not_legal",
            "duel": "legal",
            "oldschool": "not_legal",
            "premodern": "legal",
            "predh": "legal",
        },
        "games": ["paper", "mtgo", "arena"],
        "reserved": False,
        "foil": True,
        "nonfoil": True,
        "finishes": ["nonfoil", "foil"],
        "oversized": False,
        "promo": False,
        "reprint": True,
        "variation": False,
        "set_id": str(uuid4()),
        "set": "lea",
        "set_name": "Limited Edition Alpha",
        "set_type": "core",
        "set_uri": "https://api.scryfall.com/sets/lea",
        "set_search_uri": "https://api.scryfall.com/cards/search?order=set&q=e%3Alea",
        "scryfall_set_uri": "https://scryfall.com/sets/lea",
        "rulings_uri": "https://api.scryfall.com/cards/test/rulings",
        "prints_search_uri": "https://api.scryfall.com/cards/search?order=released&q=oracleid%3Atest",
        "collector_number": "161",
        "digital": False,
        "rarity": "common",
        "card_back_id": str(uuid4()),
        "artist": "Christopher Rush",
        "border_color": "black",
        "frame": "1993",
        "full_art": False,
        "textless": False,
        "booster": True,
        "story_spotlight": False,
        "prices": {
            "usd": "1.50",
            "usd_foil": "3.00",
            "eur": "1.25",
            "eur_foil": "2.50",
            "tix": "0.10",
        },
        "related_uris": {
            "gatherer": "https://gatherer.wizards.com/Pages/Card/Details.aspx?multiverseid=123456",
            "tcgplayer_infinite_articles": "https://tcgplayer.com/infinite/search?q=Lightning+Bolt",
            "tcgplayer_infinite_decks": "https://tcgplayer.com/infinite/search?q=Lightning+Bolt&view=deck",
            "edhrec": "https://edhrec.com/route/?cc=Lightning+Bolt",
        },
        "purchase_uris": {
            "tcgplayer": "https://tcgplayer.com/product/test",
            "cardmarket": "https://cardmarket.com/en/Magic/Products/Singles/test",
            "cardhoarder": "https://cardhoarder.com/cards/test",
        },
    }


@pytest.fixture
def sample_card(sample_card_data) -> Card:
    """Sample Card object for testing."""
    return Card(**sample_card_data)


@pytest.fixture
def sample_search_result(sample_card) -> SearchResult:
    """Sample SearchResult object for testing."""
    return SearchResult(
        object="list",
        total_cards=1,
        has_more=False,
        data=[sample_card],
    )


@pytest.fixture
def mock_scryfall_response():
    """Mock successful Scryfall API response."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "object": "list",
        "total_cards": 1,
        "has_more": False,
        "data": [],
    }
    return mock_response


@pytest.fixture
def mock_scryfall_error_response():
    """Mock error Scryfall API response."""
    mock_response = Mock()
    mock_response.status_code = 404
    mock_response.json.return_value = {
        "object": "error",
        "code": "not_found",
        "status": 404,
        "details": "No cards found.",
    }
    mock_response.text = "Not Found"
    return mock_response
