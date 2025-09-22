"""Tests for API client module."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import httpx
import pytest

from scryfall_mcp.api.client import (
    ScryfallAPIClient,
    ScryfallAPIError,
    get_client,
    close_client,
)
from scryfall_mcp.api.models import Card, SearchResult


class TestScryfallAPIClient:
    """Test ScryfallAPIClient class."""

    @pytest.fixture
    async def client(self, test_settings):
        """Create a client for testing."""
        client = ScryfallAPIClient()
        yield client
        await client.close()

    @pytest.fixture
    def mock_response_success(self, sample_card_data):
        """Mock successful HTTP response."""
        response = Mock()
        response.status_code = 200
        response.json.return_value = {
            "object": "list",
            "total_cards": 1,
            "has_more": False,
            "data": [sample_card_data]
        }
        return response

    @pytest.fixture
    def mock_response_error(self):
        """Mock error HTTP response."""
        response = Mock()
        response.status_code = 404
        response.json.return_value = {
            "object": "error",
            "code": "not_found",
            "status": 404,
            "details": "No cards found."
        }
        response.text = "Not Found"
        return response

    @pytest.mark.asyncio
    async def test_client_initialization(self, client):
        """Test client initialization."""
        assert client._base_url == "https://api.scryfall.com"
        assert client._timeout == 30
        assert client._max_retries == 5

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test client as context manager."""
        async with ScryfallAPIClient() as client:
            assert client._session is not None

    @pytest.mark.asyncio
    async def test_make_request_success(self, client, mock_response_success):
        """Test successful API request."""
        with patch.object(client, '_session') as mock_session:
            mock_session.request = AsyncMock(return_value=mock_response_success)
            mock_session.is_closed = False

            result = await client._make_request("GET", "/cards/search")

            assert result["object"] == "list"
            assert result["total_cards"] == 1
            mock_session.request.assert_called_once()

    @pytest.mark.asyncio
    async def test_make_request_error(self, client, mock_response_error):
        """Test API request with error response."""
        with patch.object(client, '_session') as mock_session:
            mock_session.request = AsyncMock(return_value=mock_response_error)
            mock_session.is_closed = False

            with pytest.raises(ScryfallAPIError) as exc_info:
                await client._make_request("GET", "/cards/search")

            assert exc_info.value.status_code == 404
            assert "No cards found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_make_request_timeout(self, client):
        """Test API request timeout."""
        with patch.object(client, '_session') as mock_session:
            mock_session.request = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
            mock_session.is_closed = False

            with pytest.raises(ScryfallAPIError) as exc_info:
                await client._make_request("GET", "/cards/search")

            # Circuit breaker opens after retries, so check for either timeout or circuit breaker message
            error_msg = str(exc_info.value).lower()
            assert "timeout" in error_msg or "circuit breaker" in error_msg

    @pytest.mark.asyncio
    async def test_make_request_retry_on_429(self, client):
        """Test retry logic on 429 status."""
        # Reset circuit breaker before test
        client._circuit_breaker.reset()
        
        # First call returns 429, second call succeeds
        error_response = Mock()
        error_response.status_code = 429
        error_response.json.return_value = {"object": "error", "code": "rate_limited"}

        success_response = Mock()
        success_response.status_code = 200
        success_response.json.return_value = {"result": "success"}

        with patch.object(client, '_session') as mock_session:
            mock_session.request = AsyncMock(side_effect=[error_response, success_response])
            mock_session.is_closed = False

            with patch('asyncio.sleep', new_callable=AsyncMock):  # Speed up test
                result = await client._make_request("GET", "/cards/search")

            assert result["result"] == "success"
            assert mock_session.request.call_count == 2

    @pytest.mark.asyncio
    async def test_search_cards(self, client, mock_response_success):
        """Test search_cards method."""
        with patch.object(client, '_make_request', return_value=mock_response_success.json.return_value) as mock_request:
            result = await client.search_cards("Lightning Bolt")

            assert isinstance(result, SearchResult)
            assert result.total_cards == 1
            assert len(result.data) == 1
            assert isinstance(result.data[0], Card)

            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert call_args[0][0] == "GET"
            assert call_args[0][1] == "/cards/search"
            assert call_args[0][2]["q"] == "Lightning Bolt"

    @pytest.mark.asyncio
    async def test_search_cards_with_options(self, client, mock_response_success):
        """Test search_cards with various options."""
        with patch.object(client, '_make_request', return_value=mock_response_success.json.return_value) as mock_request:
            await client.search_cards(
                query="Lightning Bolt",
                unique="prints",
                order="cmc",
                direction="desc",
                include_extras=True,
                page=2
            )

            call_args = mock_request.call_args
            # params is the third positional argument
            params = call_args[0][2]
            assert params["q"] == "Lightning Bolt"
            assert params["unique"] == "prints"
            assert params["order"] == "cmc"
            assert params["dir"] == "desc"
            assert params["include_extras"] is True
            assert params["page"] == 2

    @pytest.mark.asyncio
    async def test_get_card_by_id(self, client, sample_card_data):
        """Test get_card_by_id method."""
        with patch.object(client, '_make_request', return_value=sample_card_data) as mock_request:
            card_id = "12345678-1234-1234-1234-123456789012"
            result = await client.get_card_by_id(card_id)

            assert isinstance(result, Card)
            assert result.name == "Lightning Bolt"

            mock_request.assert_called_once_with("GET", f"/cards/{card_id}")

    @pytest.mark.asyncio
    async def test_get_card_by_name_exact(self, client, sample_card_data):
        """Test get_card_by_name with exact matching."""
        with patch.object(client, '_make_request', return_value=sample_card_data) as mock_request:
            result = await client.get_card_by_name("Lightning Bolt", exact=True)

            assert isinstance(result, Card)
            call_args = mock_request.call_args
            params = call_args[0][2]
            assert params["exact"] == "Lightning Bolt"

    @pytest.mark.asyncio
    async def test_get_card_by_name_fuzzy(self, client, sample_card_data):
        """Test get_card_by_name with fuzzy matching."""
        with patch.object(client, '_make_request', return_value=sample_card_data) as mock_request:
            result = await client.get_card_by_name("Lightning", fuzzy=True)

            assert isinstance(result, Card)
            call_args = mock_request.call_args
            params = call_args[0][2]
            assert params["fuzzy"] == "Lightning"

    @pytest.mark.asyncio
    async def test_get_card_by_name_with_set(self, client, sample_card_data):
        """Test get_card_by_name with set specification."""
        with patch.object(client, '_make_request', return_value=sample_card_data) as mock_request:
            result = await client.get_card_by_name("Lightning Bolt", set_code="lea")

            assert isinstance(result, Card)
            call_args = mock_request.call_args
            params = call_args[0][2]
            assert params["fuzzy"] == "Lightning Bolt"
            assert params["set"] == "lea"

    @pytest.mark.asyncio
    async def test_get_random_card(self, client, sample_card_data):
        """Test get_random_card method."""
        with patch.object(client, '_make_request', return_value=sample_card_data) as mock_request:
            result = await client.get_random_card()

            assert isinstance(result, Card)
            mock_request.assert_called_once_with("GET", "/cards/random", None)

    @pytest.mark.asyncio
    async def test_get_random_card_with_query(self, client, sample_card_data):
        """Test get_random_card with query filter."""
        with patch.object(client, '_make_request', return_value=sample_card_data) as mock_request:
            result = await client.get_random_card("c:r")

            assert isinstance(result, Card)
            call_args = mock_request.call_args
            params = call_args[0][2]
            assert params["q"] == "c:r"

    @pytest.mark.asyncio
    async def test_get_card_rulings(self, client):
        """Test get_card_rulings method."""
        rulings_data = {
            "object": "list",
            "data": [
                {
                    "object": "ruling",
                    "oracle_id": str(uuid4()),
                    "source": "wotc",
                    "published_at": "2020-01-01",
                    "comment": "This is a ruling."
                }
            ]
        }

        with patch.object(client, '_make_request', return_value=rulings_data) as mock_request:
            card_id = "12345678-1234-1234-1234-123456789012"
            result = await client.get_card_rulings(card_id)

            assert len(result) == 1
            assert result[0].comment == "This is a ruling."
            mock_request.assert_called_once_with("GET", f"/cards/{card_id}/rulings")

    @pytest.mark.asyncio
    async def test_get_sets(self, client):
        """Test get_sets method."""
        sets_data = {
            "object": "list",
            "data": [
                {
                    "object": "set",
                    "id": str(uuid4()),
                    "code": "lea",
                    "name": "Limited Edition Alpha",
                    "set_type": "core",
                    "card_count": 295,
                    "scryfall_uri": "https://scryfall.com/sets/lea",
                    "uri": "https://api.scryfall.com/sets/lea",
                    "icon_svg_uri": "https://c2.scryfall.com/file/scryfall-symbols/sets/lea.svg",
                    "search_uri": "https://api.scryfall.com/cards/search?q=e%3Alea"
                }
            ]
        }

        with patch.object(client, '_make_request', return_value=sets_data) as mock_request:
            result = await client.get_sets()

            assert len(result) == 1
            assert result[0].code == "lea"
            assert result[0].name == "Limited Edition Alpha"

    @pytest.mark.asyncio
    async def test_autocomplete_card_name(self, client):
        """Test autocomplete_card_name method."""
        autocomplete_data = {
            "object": "catalog",
            "uri": "https://api.scryfall.com/cards/autocomplete",
            "total_values": 3,
            "data": ["Lightning Bolt", "Lightning Strike", "Lightning Helix"]
        }

        with patch.object(client, '_make_request', return_value=autocomplete_data) as mock_request:
            result = await client.autocomplete_card_name("Lightning")

            assert len(result) == 3
            assert "Lightning Bolt" in result
            assert "Lightning Strike" in result

            call_args = mock_request.call_args
            params = call_args[0][2]
            assert params["q"] == "Lightning"

    @pytest.mark.asyncio
    async def test_circuit_breaker_integration(self, client):
        """Test that circuit breaker is properly integrated."""
        from scryfall_mcp.api.rate_limiter import CircuitBreakerOpenError

        with patch.object(client._circuit_breaker, 'call', side_effect=CircuitBreakerOpenError("Circuit open")):
            with pytest.raises(ScryfallAPIError) as exc_info:
                await client._make_request("GET", "/cards/search")

            assert "temporarily unavailable" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_session_management(self, client):
        """Test HTTP session management."""
        # Initially no session
        assert client._session is None

        # Ensure session creates one
        await client._ensure_session()
        assert client._session is not None
        assert not client._session.is_closed

        # Close should clean up
        await client.close()
        assert client._session is None or client._session.is_closed


class TestGlobalClient:
    """Test global client management functions."""

    @pytest.mark.asyncio
    async def test_get_client_singleton(self):
        """Test that get_client returns singleton."""
        client1 = await get_client()
        client2 = await get_client()
        assert client1 is client2
        await close_client()

    @pytest.mark.asyncio
    async def test_close_client(self):
        """Test close_client function."""
        # Get a client instance
        client = await get_client()
        assert client is not None

        # Close it
        await close_client()

        # Should be able to get a new one
        new_client = await get_client()
        assert new_client is not None
        await close_client()

    @pytest.mark.asyncio
    async def test_client_headers(self):
        """Test that required headers are set."""
        client = await get_client()
        await client._ensure_session()

        headers = client._session.headers
        assert "User-Agent" in headers
        assert "Accept" in headers
        assert headers["Accept"] == "application/json;q=0.9,*/*;q=0.8"
        await close_client()

    @pytest.mark.asyncio
    async def test_custom_base_url(self):
        """Test client with custom base URL."""
        custom_url = "https://custom.api.com"
        client = ScryfallAPIClient(base_url=custom_url)

        assert client._base_url == custom_url
        await client.close()

    @pytest.mark.asyncio
    async def test_malformed_json_error(self):
        """Test handling of malformed JSON in error responses."""
        error_response = Mock()
        error_response.status_code = 500
        error_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        error_response.text = "Internal Server Error"

        client = await get_client()
        # Reset circuit breaker before test
        client._circuit_breaker.reset()
        
        with patch.object(client, '_session') as mock_session:
            mock_session.request = AsyncMock(return_value=error_response)
            mock_session.is_closed = False

            with pytest.raises(ScryfallAPIError) as exc_info:
                await client._make_request("GET", "/cards/search")

            assert exc_info.value.status_code == 500
            assert "HTTP error 500" in str(exc_info.value)

        await close_client()