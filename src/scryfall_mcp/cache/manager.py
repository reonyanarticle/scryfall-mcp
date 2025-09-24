"""Cache manager and factory functions.

This module provides the main cache management interface and factory functions
for creating cache instances based on configuration.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

from ..settings import get_settings
from .backends import CacheProtocol, CompositeCache, MemoryCache, RedisCache

logger = logging.getLogger(__name__)


class CacheManager:
    """Cache manager providing high-level caching operations."""

    def __init__(self, cache: CacheProtocol):
        """Initialize cache manager.

        Parameters
        ----------
        cache : CacheProtocol
            Cache backend to use
        """
        self.cache = cache

    def build_key(self, namespace: str, **params: Any) -> str:
        """Build a cache key from namespace and parameters.

        Parameters
        ----------
        namespace : str
            Cache namespace (e.g., 'search_cards', 'card_detail')
        **params : Any
            Parameters to include in the key

        Returns
        -------
        str
            Generated cache key
        """
        # Sort parameters for consistent keys
        sorted_params = sorted(params.items())
        param_str = "&".join(f"{k}={v}" for k, v in sorted_params)

        # Hash long parameter strings to avoid key length issues
        if len(param_str) > 100:
            param_hash = hashlib.md5(param_str.encode()).hexdigest()
            return f"{namespace}:{param_hash}"

        return f"{namespace}:{param_str}"

    async def get(self, namespace: str, **params: Any) -> Any | None:
        """Get a cached value.

        Parameters
        ----------
        namespace : str
            Cache namespace
        **params : Any
            Parameters that identify the cached item

        Returns
        -------
        Any, optional
            Cached value if found
        """
        key = self.build_key(namespace, **params)
        return await self.cache.get(key)

    async def set(self, namespace: str, value: Any, ttl: int | None = None, **params: Any) -> None:
        """Set a cached value.

        Parameters
        ----------
        namespace : str
            Cache namespace
        value : Any
            Value to cache
        ttl : int, optional
            Time to live in seconds
        **params : Any
            Parameters that identify the cached item
        """
        key = self.build_key(namespace, **params)
        await self.cache.set(key, value, ttl)

    async def delete(self, namespace: str, **params: Any) -> None:
        """Delete a cached value.

        Parameters
        ----------
        namespace : str
            Cache namespace
        **params : Any
            Parameters that identify the cached item
        """
        key = self.build_key(namespace, **params)
        await self.cache.delete(key)

    async def clear(self) -> None:
        """Clear all cached values."""
        await self.cache.clear()

    async def close(self) -> None:
        """Close the cache manager."""
        await self.cache.close()

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        if hasattr(self.cache, 'get_stats'):
            return self.cache.get_stats()
        return {"type": "unknown"}


# Global cache instance
_cache_manager: CacheManager | None = None


def get_cache() -> CacheManager | None:
    """Get the global cache manager instance.

    Returns
    -------
    CacheManager, optional
        Cache manager if caching is enabled, None otherwise
    """
    global _cache_manager

    settings = get_settings()

    if not settings.cache_enabled:
        return None

    if _cache_manager is None:
        _cache_manager = _create_cache_manager()

    return _cache_manager


def _create_cache_manager() -> CacheManager:
    """Create a cache manager based on settings.

    Returns
    -------
    CacheManager
        Configured cache manager
    """
    settings = get_settings()

    # Create memory cache (L1)
    memory_cache = MemoryCache(
        max_size=settings.cache_max_size,
        default_ttl=settings.cache_ttl_default
    )

    # Create Redis cache (L2) if configured
    redis_cache = None
    if settings.cache_backend in ["redis", "composite"] and settings.cache_redis_url:
        try:
            redis_cache = RedisCache(
                redis_url=settings.cache_redis_url,
                key_prefix="scryfall_mcp:"
            )
            logger.info("Redis cache initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize Redis cache: {e}")

    # Create appropriate cache based on backend setting
    cache: CacheProtocol
    if settings.cache_backend == "memory":
        cache = memory_cache
        logger.info("Using memory-only cache")
    elif settings.cache_backend == "redis" and redis_cache:
        cache = redis_cache
        logger.info("Using Redis-only cache")
    elif settings.cache_backend == "composite":
        cache = CompositeCache(memory_cache, redis_cache)
        logger.info("Using composite (memory + Redis) cache")
    else:
        # Fallback to memory cache
        cache = memory_cache
        logger.info("Falling back to memory-only cache")

    return CacheManager(cache)


async def close_cache() -> None:
    """Close the global cache manager."""
    global _cache_manager
    if _cache_manager:
        await _cache_manager.close()
        _cache_manager = None


# Cache TTL constants based on data type
CACHE_TTL_SEARCH = 30 * 60  # 30 minutes for search results
CACHE_TTL_CARD = 24 * 60 * 60  # 24 hours for card details
CACHE_TTL_PRICE = 6 * 60 * 60  # 6 hours for price information
CACHE_TTL_SET = 7 * 24 * 60 * 60  # 1 week for set information
CACHE_TTL_AUTOCOMPLETE = 60 * 60  # 1 hour for autocomplete results