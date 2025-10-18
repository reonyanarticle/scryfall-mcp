"""Set-related utilities and caching.

This module provides utilities for fetching and caching set information,
particularly for dynamic latest set retrieval (Issue #3).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .client import ScryfallAPIClient

logger = logging.getLogger(__name__)

# Global cache for latest expansion set code
_latest_set_cache: dict[str, tuple[str, datetime]] = {}
CACHE_TTL_HOURS = 168  # 1 week (7 days * 24 hours) as per CLAUDE.md spec


async def get_latest_expansion_code(client: ScryfallAPIClient) -> str:
    """Get the latest expansion set code with 1-week caching.

    This function fetches the latest standard-legal expansion set code
    from Scryfall API and caches it for 1 week to minimize API calls.

    Parameters
    ----------
    client : ScryfallAPIClient
        The Scryfall API client instance

    Returns
    -------
    str
        The latest expansion set code (e.g., "mkm")

    Notes
    -----
    - Cache TTL: 1 week (168 hours) as per CLAUDE.md specification
    - Fallback: Returns "mkm" if API call fails
    - Thread-safe: Uses asyncio for concurrent access
    """
    cache_key = "latest_expansion"
    now = datetime.now()

    # Check cache
    if cache_key in _latest_set_cache:
        cached_code, cached_time = _latest_set_cache[cache_key]
        if now - cached_time < timedelta(hours=CACHE_TTL_HOURS):
            logger.debug(f"Using cached latest expansion code: {cached_code}")
            return cached_code

    # Fetch from API
    try:
        logger.info("Fetching latest expansion set from Scryfall API")
        latest_set = await client.get_latest_expansion_set()

        if latest_set and latest_set.code:
            set_code = latest_set.code.lower()
            _latest_set_cache[cache_key] = (set_code, now)
            logger.info(f"Latest expansion set: {latest_set.name} ({set_code})")
            return set_code
        else:
            logger.warning("No expansion set found, using fallback")
            return "mkm"  # Fallback

    except Exception as e:
        logger.error(f"Error fetching latest expansion set: {e}", exc_info=True)
        # Return cached value if available, otherwise fallback
        if cache_key in _latest_set_cache:
            cached_code, _ = _latest_set_cache[cache_key]
            logger.warning(f"Using stale cache due to error: {cached_code}")
            return cached_code
        logger.warning("Using fallback set code: mkm")
        return "mkm"  # Fallback


def get_latest_expansion_code_sync() -> str:
    """Synchronous wrapper for getting the latest expansion code.

    This function provides a synchronous interface for getting the latest
    expansion code. It attempts to use asyncio to fetch from cache or API.

    Returns
    -------
    str
        The latest expansion set code, or "mkm" as fallback

    Notes
    -----
    This is intended for use in synchronous contexts like module-level
    initialization. For async contexts, use get_latest_expansion_code() directly.
    """
    # Check if we have a cached value (synchronous)
    cache_key = "latest_expansion"
    now = datetime.now()

    if cache_key in _latest_set_cache:
        cached_code, cached_time = _latest_set_cache[cache_key]
        if now - cached_time < timedelta(hours=CACHE_TTL_HOURS):
            return cached_code

    # If no valid cache, return fallback for sync contexts
    # The cache will be populated on first async API call
    logger.debug("No cached latest expansion in sync context, using fallback")
    return "mkm"


def clear_latest_set_cache() -> None:
    """Clear the latest set cache.

    This is useful for testing or when you want to force a refresh
    of the latest set information.
    """
    global _latest_set_cache
    _latest_set_cache.clear()
    logger.info("Latest set cache cleared")
