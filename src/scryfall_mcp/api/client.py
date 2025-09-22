"""Scryfall API client implementation.

This module provides a comprehensive client for interacting with the Scryfall API,
including rate limiting, error handling, and response validation.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Optional, Union
from urllib.parse import quote_plus, urljoin

import httpx
from pydantic import ValidationError

from .models import (
    BulkData,
    Card,
    Catalog,
    Migration,
    Ruling,
    SearchResult,
    ScryfallError,
    ScryfallResponse,
    Set,
)
from .rate_limiter import (
    CircuitBreakerOpenError,
    get_circuit_breaker,
    get_rate_limiter,
)
from ..settings import get_settings

logger = logging.getLogger(__name__)


class ScryfallAPIError(Exception):
    """Base exception for Scryfall API errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class ScryfallAPIClient:
    """Asynchronous Scryfall API client with rate limiting and error handling."""
    
    def __init__(self, base_url: Optional[str] = None) -> None:
        """Initialize the Scryfall API client.
        
        Parameters
        ----------
        base_url : str, optional
            Base URL for Scryfall API. If None, uses settings value.
        """
        settings = get_settings()
        self._base_url = base_url or settings.scryfall_base_url
        self._timeout = settings.scryfall_timeout_seconds
        self._max_retries = settings.scryfall_max_retries
        self._user_agent = settings.user_agent
        self._accept_header = settings.accept_header
        
        self._rate_limiter = get_rate_limiter()
        self._circuit_breaker = get_circuit_breaker()
        self._session: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self) -> ScryfallAPIClient:
        """Async context manager entry."""
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
    
    async def _ensure_session(self) -> None:
        """Ensure HTTP session is created."""
        if self._session is None or self._session.is_closed:
            self._session = httpx.AsyncClient(
                timeout=httpx.Timeout(self._timeout),
                headers={
                    "User-Agent": self._user_agent,
                    "Accept": self._accept_header,
                },
                follow_redirects=True,
            )
    
    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session and not self._session.is_closed:
            await self._session.aclose()
            self._session = None
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict[str, Any]] = None,
        retry_count: int = 0,
    ) -> dict[str, Any]:
        """Make a rate-limited HTTP request to the Scryfall API.
        
        Parameters
        ----------
        method : str
            HTTP method (GET, POST, etc.)
        endpoint : str
            API endpoint path
        params : dict, optional
            Query parameters
        retry_count : int
            Current retry attempt count
        
        Returns
        -------
        dict
            Parsed JSON response
        
        Raises
        ------
        ScryfallAPIError
            If the API request fails
        """
        await self._ensure_session()
        assert self._session is not None
        
        url = urljoin(self._base_url, endpoint)
        
        try:
            # Apply rate limiting
            await self._rate_limiter.acquire()
            
            # Make request through circuit breaker
            response = await self._circuit_breaker.call(
                self._session.request,
                method,
                url,
                params=params,
            )
            
            # Handle response
            if response.status_code == 200:
                self._rate_limiter.record_success()
                return response.json()
            
            # Handle errors
            error_data = {}
            try:
                error_data = response.json()
            except json.JSONDecodeError:
                pass
            
            # Record failure for rate limiting
            self._rate_limiter.record_failure(response.status_code)
            
            # Handle retryable errors
            if (
                response.status_code in (429, 503, 502, 504)
                and retry_count < self._max_retries
            ):
                logger.warning(
                    f"Retryable error {response.status_code}, "
                    f"retry {retry_count + 1}/{self._max_retries}"
                )
                await asyncio.sleep(2 ** retry_count)  # Exponential backoff
                return await self._make_request(method, endpoint, params, retry_count + 1)
            
            # Handle API errors
            if "object" in error_data and error_data["object"] == "error":
                raise ScryfallAPIError(
                    error_data.get("details", f"API error: {response.status_code}"),
                    response.status_code,
                )
            
            # Handle other HTTP errors
            raise ScryfallAPIError(
                f"HTTP error {response.status_code}: {response.text}",
                response.status_code,
            )
        
        except CircuitBreakerOpenError:
            raise ScryfallAPIError("Service temporarily unavailable (circuit breaker open)")
        except httpx.TimeoutException:
            self._rate_limiter.record_failure()
            if retry_count < self._max_retries:
                logger.warning(f"Request timeout, retry {retry_count + 1}/{self._max_retries}")
                await asyncio.sleep(2 ** retry_count)
                return await self._make_request(method, endpoint, params, retry_count + 1)
            raise ScryfallAPIError("Request timeout")
        except httpx.RequestError as e:
            self._rate_limiter.record_failure()
            raise ScryfallAPIError(f"Request failed: {e}")
    
    async def search_cards(
        self,
        query: str,
        unique: str = "cards",
        order: str = "name",
        direction: str = "auto",
        include_extras: bool = False,
        include_multilingual: bool = False,
        include_variations: bool = False,
        page: int = 1,
    ) -> SearchResult:
        """Search for Magic cards.
        
        Parameters
        ----------
        query : str
            Scryfall search query
        unique : str
            Strategy for omitting similar cards
        order : str
            Field to sort by
        direction : str
            Sort direction
        include_extras : bool
            Include extra cards (tokens, emblems, etc.)
        include_multilingual : bool
            Include non-English cards
        include_variations : bool
            Include rare card variations
        page : int
            Page number for pagination
        
        Returns
        -------
        SearchResult
            Search results with card data
        """
        params = {
            "q": query,
            "unique": unique,
            "order": order,
            "dir": direction,
            "include_extras": include_extras,
            "include_multilingual": include_multilingual,
            "include_variations": include_variations,
            "page": page,
        }
        
        data = await self._make_request("GET", "/cards/search", params)
        return SearchResult(**data)
    
    async def get_card_by_id(self, card_id: str) -> Card:
        """Get a card by its Scryfall ID.
        
        Parameters
        ----------
        card_id : str
            Scryfall card ID
        
        Returns
        -------
        Card
            Card data
        """
        data = await self._make_request("GET", f"/cards/{card_id}")
        return Card(**data)
    
    async def get_card_by_name(
        self,
        name: str,
        exact: bool = False,
        set_code: Optional[str] = None,
        fuzzy: bool = True,
    ) -> Card:
        """Get a card by name.
        
        Parameters
        ----------
        name : str
            Card name
        exact : bool
            Use exact name matching
        set_code : str, optional
            Specific set code to search in
        fuzzy : bool
            Use fuzzy name matching
        
        Returns
        -------
        Card
            Card data
        """
        if exact:
            endpoint = "/cards/named"
            params = {"exact": name}
        else:
            endpoint = "/cards/named"
            params = {"fuzzy": name}
        
        if set_code:
            params["set"] = set_code
        
        data = await self._make_request("GET", endpoint, params)
        return Card(**data)
    
    async def get_random_card(self, query: Optional[str] = None) -> Card:
        """Get a random card.
        
        Parameters
        ----------
        query : str, optional
            Scryfall search query to filter random selection
        
        Returns
        -------
        Card
            Random card data
        """
        params = {"q": query} if query else None
        data = await self._make_request("GET", "/cards/random", params)
        return Card(**data)
    
    async def get_card_rulings(self, card_id: str) -> list[Ruling]:
        """Get rulings for a card.
        
        Parameters
        ----------
        card_id : str
            Scryfall card ID
        
        Returns
        -------
        list[Ruling]
            List of card rulings
        """
        data = await self._make_request("GET", f"/cards/{card_id}/rulings")
        return [Ruling(**ruling) for ruling in data["data"]]
    
    async def get_sets(self) -> list[Set]:
        """Get all Magic sets.
        
        Returns
        -------
        list[Set]
            List of all sets
        """
        data = await self._make_request("GET", "/sets")
        return [Set(**set_data) for set_data in data["data"]]
    
    async def get_set_by_code(self, set_code: str) -> Set:
        """Get a set by its code.
        
        Parameters
        ----------
        set_code : str
            Three or four-letter set code
        
        Returns
        -------
        Set
            Set data
        """
        data = await self._make_request("GET", f"/sets/{set_code}")
        return Set(**data)
    
    async def get_catalog(self, catalog_type: str) -> list[str]:
        """Get a catalog of Magic game data.
        
        Parameters
        ----------
        catalog_type : str
            Type of catalog (card-names, artist-names, word-bank, etc.)
        
        Returns
        -------
        list[str]
            Catalog data
        """
        data = await self._make_request("GET", f"/catalog/{catalog_type}")
        catalog = Catalog(**data)
        return catalog.data
    
    async def get_bulk_data(self) -> list[BulkData]:
        """Get available bulk data downloads.
        
        Returns
        -------
        list[BulkData]
            Available bulk data downloads
        """
        data = await self._make_request("GET", "/bulk-data")
        return [BulkData(**bulk) for bulk in data["data"]]
    
    async def autocomplete_card_name(self, query: str) -> list[str]:
        """Get card name autocompletion suggestions.
        
        Parameters
        ----------
        query : str
            Partial card name
        
        Returns
        -------
        list[str]
            Suggested card names
        """
        params = {"q": query}
        data = await self._make_request("GET", "/cards/autocomplete", params)
        catalog = Catalog(**data)
        return catalog.data


# Global client instance
_client: Optional[ScryfallAPIClient] = None


async def get_client() -> ScryfallAPIClient:
    """Get the global Scryfall API client instance.
    
    Returns
    -------
    ScryfallAPIClient
        The global client instance
    """
    global _client
    if _client is None:
        _client = ScryfallAPIClient()
        await _client._ensure_session()
    return _client


async def close_client() -> None:
    """Close the global client instance."""
    global _client
    if _client:
        await _client.close()
        _client = None