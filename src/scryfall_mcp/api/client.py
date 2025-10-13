"""Scryfall API client implementation.

This module provides a comprehensive client for interacting with the Scryfall API,
including rate limiting, error handling, and response validation.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from typing import Any, cast
from urllib.parse import urljoin

import httpx

from ..cache import CACHE_TTL_AUTOCOMPLETE, CACHE_TTL_CARD, CACHE_TTL_SEARCH, get_cache
from ..models import (
    BulkData,
    Card,
    Catalog,
    Ruling,
    SearchResult,
    Set,
)
from ..settings import get_settings
from .rate_limiter import (
    CircuitBreakerOpenError,
    get_circuit_breaker,
    get_rate_limiter,
)

logger = logging.getLogger(__name__)


class ScryfallAPIError(Exception):
    """Base exception for Scryfall API errors with enhanced context."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Initialize the API error.

        Parameters
        ----------
        message : str
            Error message
        status_code : int, optional
            HTTP status code
        context : dict, optional
            Additional context information for error handling
        """
        super().__init__(message)
        self.status_code = status_code
        self.context = context or {}


class ScryfallAPIClient:
    """Asynchronous Scryfall API client with rate limiting and error handling."""

    def __init__(self, base_url: str | None = None) -> None:
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
        self._session: httpx.AsyncClient | None = None

    async def __aenter__(self) -> ScryfallAPIClient:
        """Async context manager entry."""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
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

    def _build_error_context(
        self, endpoint: str, params: dict[str, Any] | None, **kwargs: Any
    ) -> dict[str, Any]:
        """Build error context dictionary for error handling.

        Parameters
        ----------
        endpoint : str
            API endpoint path
        params : dict, optional
            Query parameters
        **kwargs : Any
            Additional context fields

        Returns
        -------
        dict
            Error context dictionary
        """
        context = {
            "query": params.get("q") if params else None,
            "endpoint": endpoint,
        }
        context.update(kwargs)
        return context

    async def _execute_http_request(
        self, method: str, url: str, params: dict[str, Any] | None
    ) -> httpx.Response:
        """Execute HTTP request with rate limiting and circuit breaker.

        Parameters
        ----------
        method : str
            HTTP method (GET, POST, etc.)
        url : str
            Full request URL
        params : dict, optional
            Query parameters

        Returns
        -------
        httpx.Response
            HTTP response

        Raises
        ------
        CircuitBreakerOpenError
            If circuit breaker is open
        """
        await self._rate_limiter.acquire()
        response = await self._circuit_breaker.call(
            self._session.request,  # type: ignore[union-attr]
            method,
            url,
            params=params,
        )
        return cast("httpx.Response", response)

    def _should_retry(self, status_code: int, retry_count: int) -> bool:
        """Check if error should be retried.

        Parameters
        ----------
        status_code : int
            HTTP status code
        retry_count : int
            Current retry attempt count

        Returns
        -------
        bool
            True if should retry, False otherwise
        """
        return status_code in (429, 503, 502, 504) and retry_count < self._max_retries

    def _parse_error_data(self, response: httpx.Response) -> dict[str, Any]:
        """Parse error data from HTTP response.

        Parameters
        ----------
        response : httpx.Response
            HTTP response

        Returns
        -------
        dict
            Parsed error data or empty dict
        """
        error_data: dict[str, Any] = {}
        with contextlib.suppress(json.JSONDecodeError):
            error_data = response.json()
        return error_data

    def _is_scryfall_error_object(self, error_data: dict[str, Any]) -> bool:
        """Check if error data is a Scryfall error object.

        Parameters
        ----------
        error_data : dict
            Parsed error data

        Returns
        -------
        bool
            True if Scryfall error object, False otherwise
        """
        return "object" in error_data and error_data["object"] == "error"

    def _build_api_error_context(
        self,
        status_code: int,
        endpoint: str,
        params: dict[str, Any] | None,
        response: httpx.Response,
    ) -> dict[str, Any]:
        """Build error context for Scryfall API errors.

        Parameters
        ----------
        status_code : int
            HTTP status code
        endpoint : str
            API endpoint path
        params : dict, optional
            Query parameters
        response : httpx.Response
            HTTP response

        Returns
        -------
        dict
            Error context dictionary
        """
        context = self._build_error_context(endpoint, params, category="api_error")

        if status_code == 400:
            context["category"] = "search_syntax"
        elif status_code == 429:
            context["category"] = "rate_limit"
            context["retry_after"] = response.headers.get("Retry-After", "5")

        return context

    async def _handle_error_response(
        self,
        response: httpx.Response,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None,
        retry_count: int,
    ) -> dict[str, Any]:
        """Handle non-200 HTTP responses.

        Parameters
        ----------
        response : httpx.Response
            HTTP response
        method : str
            HTTP method
        endpoint : str
            API endpoint path
        params : dict, optional
            Query parameters
        retry_count : int
            Current retry attempt count

        Returns
        -------
        dict
            Parsed JSON response (if retry succeeds)

        Raises
        ------
        ScryfallAPIError
            If error is not retryable or max retries exceeded
        """
        # Parse error data
        error_data = self._parse_error_data(response)

        # Record failure for rate limiting
        self._rate_limiter.record_failure(response.status_code)

        # Handle retryable errors
        if self._should_retry(response.status_code, retry_count):
            logger.warning(
                f"Retryable error {response.status_code}, "
                f"retry {retry_count + 1}/{self._max_retries}",
            )
            await asyncio.sleep(2**retry_count)  # Exponential backoff
            return await self._make_request(method, endpoint, params, retry_count + 1)

        # Handle Scryfall API errors
        if self._is_scryfall_error_object(error_data):
            context = self._build_api_error_context(
                response.status_code, endpoint, params, response
            )
            raise ScryfallAPIError(
                error_data.get("details", f"API error: {response.status_code}"),
                response.status_code,
                context,
            )

        # Handle other HTTP errors
        context = self._build_error_context(endpoint, params, category="http_error")
        raise ScryfallAPIError(
            f"HTTP error {response.status_code}: {response.text}",
            response.status_code,
            context,
        )

    async def _handle_timeout(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None,
        retry_count: int,
    ) -> dict[str, Any]:
        """Handle request timeout exceptions.

        Parameters
        ----------
        method : str
            HTTP method
        endpoint : str
            API endpoint path
        params : dict, optional
            Query parameters
        retry_count : int
            Current retry attempt count

        Returns
        -------
        dict
            Parsed JSON response (if retry succeeds)

        Raises
        ------
        ScryfallAPIError
            If max retries exceeded
        """
        self._rate_limiter.record_failure()

        if retry_count < self._max_retries:
            logger.warning(
                f"Request timeout, retry {retry_count + 1}/{self._max_retries}"
            )
            await asyncio.sleep(2**retry_count)
            return await self._make_request(method, endpoint, params, retry_count + 1)

        context = self._build_error_context(endpoint, params, category="timeout")
        raise ScryfallAPIError("Request timeout", 408, context) from None

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
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
            # Execute HTTP request with rate limiting and circuit breaker
            response = await self._execute_http_request(method, url, params)

            # Handle successful response
            if response.status_code == 200:
                self._rate_limiter.record_success()
                return dict(response.json())

            # Handle error responses
            return await self._handle_error_response(
                response, method, endpoint, params, retry_count
            )

        except CircuitBreakerOpenError as e:
            context = self._build_error_context(
                endpoint, params, category="service_unavailable"
            )
            raise ScryfallAPIError(
                "Service temporarily unavailable (circuit breaker open)",
                503,
                context,
            ) from e
        except httpx.TimeoutException:
            return await self._handle_timeout(method, endpoint, params, retry_count)
        except httpx.RequestError as e:
            self._rate_limiter.record_failure()
            context = self._build_error_context(
                endpoint, params, category="network_error", error_type=type(e).__name__
            )
            raise ScryfallAPIError(f"Request failed: {e}", None, context) from e

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
        # Check cache first
        cache = get_cache()
        if cache:
            cached = await cache.get(
                "search_cards",
                query=query,
                unique=unique,
                order=order,
                direction=direction,
                include_extras=include_extras,
                include_multilingual=include_multilingual,
                include_variations=include_variations,
                page=page,
            )
            if cached:
                return SearchResult(**cached)

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
        result = SearchResult(**data)

        # Cache the result
        if cache:
            await cache.set(
                "search_cards",
                result.model_dump(),
                ttl=CACHE_TTL_SEARCH,
                query=query,
                unique=unique,
                order=order,
                direction=direction,
                include_extras=include_extras,
                include_multilingual=include_multilingual,
                include_variations=include_variations,
                page=page,
            )

        return result

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
        # Check cache first
        cache = get_cache()
        if cache:
            cached = await cache.get("card_by_id", card_id=card_id)
            if cached:
                return Card(**cached)

        data = await self._make_request("GET", f"/cards/{card_id}")
        result = Card(**data)

        # Cache the result
        if cache:
            await cache.set(
                "card_by_id", result.model_dump(), ttl=CACHE_TTL_CARD, card_id=card_id
            )

        return result

    async def get_card_by_name(
        self,
        name: str,
        exact: bool = False,
        set_code: str | None = None,
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

    async def get_random_card(self, query: str | None = None) -> Card:
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
        # Check cache first
        cache = get_cache()
        if cache:
            cached = await cache.get("autocomplete", query=query)
            if cached:
                cached_list: list[str] = cached
                return cached_list

        params = {"q": query}
        data = await self._make_request("GET", "/cards/autocomplete", params)
        catalog = Catalog(**data)
        result = catalog.data

        # Cache the result
        if cache:
            await cache.set(
                "autocomplete", result, ttl=CACHE_TTL_AUTOCOMPLETE, query=query
            )

        return result


# Global client instance
_client: ScryfallAPIClient | None = None


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
