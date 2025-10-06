"""Cache system for Scryfall MCP Server.

This module provides a multi-layer cache system with memory and Redis backends
to optimize API calls and response times.
"""

from __future__ import annotations

from .backends import CompositeCache, MemoryCache, RedisCache
from .manager import (
    CACHE_TTL_AUTOCOMPLETE,
    CACHE_TTL_CARD,
    CACHE_TTL_PRICE,
    CACHE_TTL_SEARCH,
    CACHE_TTL_SET,
    CacheManager,
    get_cache,
)

__all__ = [
    "CacheManager",
    "MemoryCache",
    "RedisCache",
    "CompositeCache",
    "get_cache",
    "CACHE_TTL_SEARCH",
    "CACHE_TTL_CARD",
    "CACHE_TTL_AUTOCOMPLETE",
    "CACHE_TTL_PRICE",
    "CACHE_TTL_SET",
]
