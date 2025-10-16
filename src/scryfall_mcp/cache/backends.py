"""Cache backend implementations.

This module provides different cache backend implementations:
- MemoryCache: In-memory LRU cache with TTL
- RedisCache: Redis-based distributed cache
- CompositeCache: Multi-layer cache combining memory and Redis
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from collections import OrderedDict
from typing import Any

from ..models import CacheEntry

logger = logging.getLogger(__name__)


class CacheProtocol(ABC):
    """Abstract base class for cache implementations."""

    @abstractmethod
    async def get(self, key: str) -> Any | None:
        """Get a value from the cache.

        Parameters
        ----------
        key : str
            Cache key

        Returns
        -------
        Any, optional
            Cached value if found, None otherwise
        """

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set a value in the cache.

        Parameters
        ----------
        key : str
            Cache key
        value : Any
            Value to cache
        ttl : int, optional
            Time to live in seconds
        """

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete a key from the cache.

        Parameters
        ----------
        key : str
            Cache key to delete
        """

    @abstractmethod
    async def clear(self) -> None:
        """Clear all cache entries."""

    @abstractmethod
    async def close(self) -> None:
        """Close the cache backend and clean up resources."""


class MemoryCache(CacheProtocol):
    """In-memory LRU cache with TTL support."""

    def __init__(self, max_size: int = 1000, default_ttl: int | None = None) -> None:
        """Initialize the memory cache.

        Parameters
        ----------
        max_size : int
            Maximum number of entries in cache
        default_ttl : int | None, optional
            Default TTL in seconds (default: None)
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Any | None:
        """Get a value from memory cache."""
        async with self._lock:
            if key not in self._cache:
                return None

            entry = self._cache[key]

            # Check expiration
            if entry.is_expired():
                del self._cache[key]
                return None

            # Move to end (LRU)
            self._cache.move_to_end(key)
            return entry.value

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set a value in memory cache."""
        async with self._lock:
            now = time.time()
            ttl = ttl or self.default_ttl
            expires_at = now + ttl if ttl is not None else None

            entry = CacheEntry(value=value, expires_at=expires_at, created_at=now)

            # Add/update entry
            self._cache[key] = entry
            self._cache.move_to_end(key)

            # Enforce size limit
            while len(self._cache) > self.max_size:
                self._cache.popitem(last=False)

    async def delete(self, key: str) -> None:
        """Delete a key from memory cache."""
        async with self._lock:
            self._cache.pop(key, None)

    async def clear(self) -> None:
        """Clear all entries from memory cache."""
        async with self._lock:
            self._cache.clear()

    async def close(self) -> None:
        """Close memory cache (no-op)."""
        pass

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        return {
            "type": "memory",
            "size": len(self._cache),
            "max_size": self.max_size,
            "hit_ratio": None,  # Could be implemented with counters
        }


class RedisCache(CacheProtocol):
    """Redis-based distributed cache."""

    def __init__(
        self, redis_url: str = "redis://localhost:6379", key_prefix: str = "scryfall:"
    ):
        """Initialize Redis cache.

        Parameters
        ----------
        redis_url : str
            Redis connection URL
        key_prefix : str
            Prefix for all cache keys
        """
        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self._redis = None
        self._available = False

    async def _get_redis(self) -> Any | None:
        """Get Redis connection, creating if necessary."""
        if self._redis is None:
            try:
                import redis.asyncio as redis

                self._redis = redis.from_url(self.redis_url, decode_responses=True)  # type: ignore[no-untyped-call]
                # Test connection
                if self._redis is not None:
                    await self._redis.ping()
                self._available = True
                logger.info(f"Connected to Redis at {self.redis_url}")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}")
                self._available = False
                self._redis = None
        return self._redis

    def _make_key(self, key: str) -> str:
        """Add prefix to key."""
        return f"{self.key_prefix}{key}"

    async def get(self, key: str) -> Any | None:
        """Get a value from Redis cache."""
        redis = await self._get_redis()
        if not redis or not self._available:
            return None

        try:
            value = await redis.get(self._make_key(key))
            if value is None:
                return None
            return json.loads(value)
        except Exception as e:
            logger.warning(f"Redis get error: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set a value in Redis cache."""
        redis = await self._get_redis()
        if not redis or not self._available:
            return

        try:
            serialized = json.dumps(value, default=str)
            if ttl:
                await redis.setex(self._make_key(key), ttl, serialized)
            else:
                await redis.set(self._make_key(key), serialized)
        except Exception as e:
            logger.warning(f"Redis set error: {e}")

    async def delete(self, key: str) -> None:
        """Delete a key from Redis cache."""
        redis = await self._get_redis()
        if not redis or not self._available:
            return

        try:
            await redis.delete(self._make_key(key))
        except Exception as e:
            logger.warning(f"Redis delete error: {e}")

    async def clear(self) -> None:
        """Clear all prefixed keys from Redis cache."""
        redis = await self._get_redis()
        if not redis or not self._available:
            return

        try:
            keys = await redis.keys(f"{self.key_prefix}*")
            if keys:
                await redis.delete(*keys)
        except Exception as e:
            logger.warning(f"Redis clear error: {e}")

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        return {
            "type": "redis",
            "available": self._available,
            "url": self.redis_url,
        }


class CompositeCache(CacheProtocol):
    """Multi-layer cache combining memory (L1) and Redis (L2)."""

    def __init__(
        self, memory_cache: MemoryCache, redis_cache: RedisCache | None = None
    ):
        """Initialize composite cache.

        Parameters
        ----------
        memory_cache : MemoryCache
            L1 memory cache
        redis_cache : RedisCache, optional
            L2 Redis cache
        """
        self.memory_cache = memory_cache
        self.redis_cache = redis_cache

    async def get(self, key: str) -> Any | None:
        """Get value with L1 -> L2 -> miss strategy."""
        # Try L1 (memory) first
        value = await self.memory_cache.get(key)
        if value is not None:
            return value

        # Try L2 (Redis) if available
        if self.redis_cache:
            value = await self.redis_cache.get(key)
            if value is not None:
                # Write back to L1
                await self.memory_cache.set(key, value)
                return value

        return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set value in both L1 and L2."""
        # Write to both layers
        await self.memory_cache.set(key, value, ttl)
        if self.redis_cache:
            await self.redis_cache.set(key, value, ttl)

    async def delete(self, key: str) -> None:
        """Delete key from both layers."""
        await self.memory_cache.delete(key)
        if self.redis_cache:
            await self.redis_cache.delete(key)

    async def clear(self) -> None:
        """Clear both cache layers."""
        await self.memory_cache.clear()
        if self.redis_cache:
            await self.redis_cache.clear()

    async def close(self) -> None:
        """Close both cache backends."""
        await self.memory_cache.close()
        if self.redis_cache:
            await self.redis_cache.close()

    def get_stats(self) -> dict[str, Any]:
        """Get statistics from both cache layers."""
        stats = {
            "type": "composite",
            "memory": self.memory_cache.get_stats(),
        }
        if self.redis_cache:
            stats["redis"] = self.redis_cache.get_stats()
        return stats
