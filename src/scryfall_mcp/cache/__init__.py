"""Cache system for Scryfall MCP Server.

This module provides a multi-layer cache system with memory and Redis backends
to optimize API calls and response times.
"""

from __future__ import annotations

from .backends import CompositeCache, MemoryCache, RedisCache
from .manager import (
    CacheManager,
    get_cache,
    get_cache_ttl_card,
    get_cache_ttl_search,
    get_cache_ttl_set,
)

__all__ = [
    "CacheManager",
    "MemoryCache",
    "RedisCache",
    "CompositeCache",
    "get_cache",
    "get_cache_ttl_search",
    "get_cache_ttl_card",
    "get_cache_ttl_set",
]
