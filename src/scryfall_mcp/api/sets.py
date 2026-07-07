"""Set-related utilities and caching.

This module provides utilities for fetching and caching set information,
particularly for dynamic latest set retrieval (Issue #3).
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .client import ScryfallAPIClient

logger = logging.getLogger(__name__)

# Cache TTL: 1 week (7 days * 24 hours) as per CLAUDE.md spec
CACHE_TTL_HOURS = 168


@dataclass
class CacheEntry:
    """Cache entry for latest expansion set code.

    Attributes
    ----------
    code : str
        The expansion set code (e.g., "mkm")
    cached_at : datetime
        UTC timestamp when the entry was cached
    """

    code: str
    cached_at: datetime


class LatestSetCache:
    """Thread-safe cache for latest expansion set code.

    This class provides async-safe caching with TTL support for the latest
    expansion set code. Uses asyncio.Lock to ensure thread safety.

    Attributes
    ----------
    _cache : dict[str, CacheEntry] | None
        Internal cache storage
    _lock : asyncio.Lock
        Lock for thread-safe access
    """

    def __init__(self) -> None:
        """Initialize the cache."""
        self._cache: dict[str, CacheEntry] | None = None
        self._lock: asyncio.Lock | None = None

    def _ensure_lock(self) -> asyncio.Lock:
        """Ensure lock is initialized.

        Returns
        -------
        asyncio.Lock
            The initialized lock
        """
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    async def get(self, key: str, ttl_hours: int) -> str | None:
        """Get cached value if not expired.

        Parameters
        ----------
        key : str
            Cache key
        ttl_hours : int
            Time-to-live in hours

        Returns
        -------
        str | None
            Cached value if available and not expired, None otherwise
        """
        async with self._ensure_lock():
            if self._cache is None or key not in self._cache:
                return None

            entry = self._cache[key]
            now = datetime.now(UTC)
            if now - entry.cached_at < timedelta(hours=ttl_hours):
                logger.debug(f"Cache hit for key '{key}': {entry.code}")
                return entry.code

            logger.debug(f"Cache expired for key '{key}'")
            return None

    async def set(self, key: str, value: str) -> None:
        """Set cache value with current timestamp.

        Parameters
        ----------
        key : str
            Cache key
        value : str
            Value to cache
        """
        async with self._ensure_lock():
            if self._cache is None:
                self._cache = {}

            entry = CacheEntry(code=value, cached_at=datetime.now(UTC))
            self._cache[key] = entry
            logger.debug(f"Cached key '{key}': {value}")

    async def clear(self) -> None:
        """Clear all cache entries."""
        async with self._ensure_lock():
            if self._cache is not None:
                self._cache.clear()
            logger.info("Cache cleared")


# Global cache instance
_cache = LatestSetCache()


async def get_latest_expansion_code(client: ScryfallAPIClient) -> str:
    """Get the latest expansion set code with 1-week caching.

    This function fetches the latest standard-legal expansion set code
    from Scryfall API and caches it for 1 week to minimize API calls.
    Uses thread-safe caching with asyncio.Lock.

    Parameters
    ----------
    client : ScryfallAPIClient
        The Scryfall API client instance

    Returns
    -------
    str
        The latest expansion set code (e.g., "mkm")

    Raises
    ------
    Exception
        If API call fails and no cached/fallback value is available
        (currently returns fallback "mkm" instead of raising)

    Notes
    -----
    - Cache TTL: 1 week (168 hours) as per CLAUDE.md specification
    - Fallback: Returns "mkm" if API call fails
    - Thread-safe: Uses asyncio.Lock for concurrent access protection
    - Uses UTC timestamps to avoid timezone issues

    Examples
    --------
    >>> client = await get_client()
    >>> code = await get_latest_expansion_code(client)
    >>> print(code)
    'mkm'
    """
    cache_key = "latest_expansion"

    # Check cache first
    cached_code = await _cache.get(cache_key, CACHE_TTL_HOURS)
    if cached_code is not None:
        return cached_code

    # Fetch from API
    try:
        logger.info("Fetching latest expansion set from Scryfall API")
        latest_set = await client.get_latest_expansion_set()

        if latest_set and latest_set.code:
            set_code = latest_set.code.lower()
            await _cache.set(cache_key, set_code)
            logger.info(f"Latest expansion set: {latest_set.name} ({set_code})")
            return set_code

        # No expansion set found
        logger.warning("No expansion set found, using fallback")
        from ..i18n.constants import LATEST_SET_CODE_FALLBACK

        return LATEST_SET_CODE_FALLBACK

    except Exception as e:
        logger.error(f"Error fetching latest expansion set: {e}", exc_info=True)

        # Try to get stale cache (ignore TTL)
        async with _cache._ensure_lock():
            if _cache._cache and cache_key in _cache._cache:
                stale_code = _cache._cache[cache_key].code
                logger.warning(f"Using stale cache due to error: {stale_code}")
                return stale_code

        # Final fallback
        logger.warning("Using fallback set code")
        from ..i18n.constants import LATEST_SET_CODE_FALLBACK

        return LATEST_SET_CODE_FALLBACK


async def resolve_latest_set_placeholder(query: str) -> str:
    """Replace the ``__LATEST_SET__`` placeholder with the latest set code.

    Placeholder resolution requires a Scryfall API call, so it lives in the
    I/O layer; the query builder (pure core) leaves the placeholder in place.

    Parameters
    ----------
    query : str
        Query string potentially containing the ``__LATEST_SET__`` placeholder

    Returns
    -------
    str
        Query with the placeholder replaced by the actual set code
        (falls back to `LATEST_SET_CODE_FALLBACK` if the API is unavailable)

    Notes
    -----
    - Uses get_latest_expansion_code() with its 1-week cache
    - Only performs an API call if the placeholder is present
    """
    if "__LATEST_SET__" not in query:
        return query

    try:
        from .client import get_client

        client = await get_client()
        latest_code = await get_latest_expansion_code(client)
    except Exception as e:
        logger.warning(
            f"Failed to fetch latest set, using fallback: {e}", exc_info=True
        )
        from ..i18n.constants import LATEST_SET_CODE_FALLBACK

        latest_code = LATEST_SET_CODE_FALLBACK

    return query.replace("__LATEST_SET__", latest_code)


async def clear_latest_set_cache() -> None:
    """Clear the latest set cache.

    This is useful for testing or when you want to force a refresh
    of the latest set information.

    Notes
    -----
    This function is async to ensure thread-safe cache access.
    """
    await _cache.clear()
