"""Tests for cache backend implementations."""

from __future__ import annotations

import asyncio
import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from scryfall_mcp.cache.backends import (
    CacheEntry,
    MemoryCache,
    RedisCache,
    CompositeCache,
)


class TestCacheEntry:
    """Test CacheEntry model."""

    def test_cache_entry_creation(self):
        """Test cache entry creation."""
        entry = CacheEntry(value="test", created_at=time.time())
        assert entry.value == "test"
        assert entry.expires_at is None
        assert not entry.is_expired()

    def test_cache_entry_with_expiration(self):
        """Test cache entry with expiration."""
        now = time.time()
        entry = CacheEntry(
            value="test",
            expires_at=now + 60,
            created_at=now
        )
        assert not entry.is_expired()

        # Create expired entry
        expired_entry = CacheEntry(
            value="test",
            expires_at=now - 60,
            created_at=now - 120
        )
        assert expired_entry.is_expired()


class TestMemoryCache:
    """Test in-memory cache implementation."""

    @pytest.fixture
    def memory_cache(self):
        """Create a memory cache instance."""
        return MemoryCache(max_size=3, default_ttl=60)

    @pytest.mark.asyncio
    async def test_basic_operations(self, memory_cache):
        """Test basic cache operations."""
        # Test get on empty cache
        assert await memory_cache.get("key1") is None

        # Test set and get
        await memory_cache.set("key1", "value1")
        assert await memory_cache.get("key1") == "value1"

        # Test update
        await memory_cache.set("key1", "updated_value")
        assert await memory_cache.get("key1") == "updated_value"

    @pytest.mark.asyncio
    async def test_ttl_expiration(self, memory_cache):
        """Test TTL expiration."""
        # Set with short TTL
        await memory_cache.set("key1", "value1", ttl=1)
        assert await memory_cache.get("key1") == "value1"

        # Wait for expiration
        await asyncio.sleep(1.1)
        assert await memory_cache.get("key1") is None

    @pytest.mark.asyncio
    async def test_lru_eviction(self, memory_cache):
        """Test LRU eviction when cache is full."""
        # Fill cache to max size
        await memory_cache.set("key1", "value1")
        await memory_cache.set("key2", "value2")
        await memory_cache.set("key3", "value3")

        # Access keys to establish LRU order: key1 (oldest) -> key2 -> key3 (newest)
        await memory_cache.get("key1")
        await memory_cache.get("key2")
        await memory_cache.get("key3")

        # Add one more - should evict key1 (least recently used)
        await memory_cache.set("key4", "value4")

        # key1 should be evicted
        assert await memory_cache.get("key1") is None
        assert await memory_cache.get("key2") == "value2"
        assert await memory_cache.get("key3") == "value3"
        assert await memory_cache.get("key4") == "value4"

    @pytest.mark.asyncio
    async def test_delete_and_clear(self, memory_cache):
        """Test delete and clear operations."""
        # Set some values
        await memory_cache.set("key1", "value1")
        await memory_cache.set("key2", "value2")

        # Test delete
        await memory_cache.delete("key1")
        assert await memory_cache.get("key1") is None
        assert await memory_cache.get("key2") == "value2"

        # Test clear
        await memory_cache.clear()
        assert await memory_cache.get("key2") is None

    def test_get_stats(self, memory_cache):
        """Test cache statistics."""
        stats = memory_cache.get_stats()
        assert stats["type"] == "memory"
        assert stats["max_size"] == 3
        assert "size" in stats


class TestRedisCache:
    """Test Redis cache implementation."""

    @pytest.fixture
    def redis_cache(self):
        """Create a Redis cache instance."""
        return RedisCache(redis_url="redis://localhost:6379", key_prefix="test:")

    @pytest.mark.asyncio
    async def test_connection_failure(self, redis_cache):
        """Test handling of Redis connection failures."""
        # Should handle connection failure gracefully
        result = await redis_cache.get("test_key")
        assert result is None

        # Set should not raise error
        await redis_cache.set("test_key", "test_value")

    @pytest.mark.asyncio
    async def test_key_prefix(self, redis_cache):
        """Test that keys are properly prefixed."""
        assert redis_cache._make_key("test") == "test:test"

    def test_get_stats(self, redis_cache):
        """Test Redis cache statistics."""
        stats = redis_cache.get_stats()
        assert stats["type"] == "redis"
        assert "available" in stats
        assert "url" in stats

    @pytest.mark.asyncio
    @patch('redis.asyncio.from_url')
    async def test_redis_operations_with_mock(self, mock_redis_from_url):
        """Test Redis operations with mocked Redis."""
        # Setup mock Redis client
        mock_redis = AsyncMock()
        mock_redis.ping.return_value = True
        mock_redis.get.return_value = None
        mock_redis.setex = AsyncMock()
        mock_redis.set = AsyncMock()
        mock_redis.delete = AsyncMock()
        mock_redis_from_url.return_value = mock_redis

        cache = RedisCache()

        # Test successful get
        mock_redis.get.return_value = '"test_value"'
        result = await cache.get("test_key")
        assert result == "test_value"

        # Test set with TTL
        await cache.set("test_key", "test_value", ttl=60)
        mock_redis.setex.assert_called_once_with("scryfall:test_key", 60, '"test_value"')

        # Test set without TTL
        await cache.set("test_key2", "test_value2")
        mock_redis.set.assert_called_once_with("scryfall:test_key2", '"test_value2"')


class TestCompositeCache:
    """Test composite cache implementation."""

    @pytest.fixture
    def composite_cache(self):
        """Create a composite cache instance."""
        memory_cache = MemoryCache(max_size=3)
        redis_cache = RedisCache()  # Will fail to connect, but that's ok for testing
        return CompositeCache(memory_cache, redis_cache)

    @pytest.mark.asyncio
    async def test_cache_hierarchy(self, composite_cache):
        """Test L1 -> L2 cache hierarchy."""
        # Set value (should go to both layers)
        await composite_cache.set("key1", "value1")

        # Should be retrievable
        assert await composite_cache.get("key1") == "value1"

    @pytest.mark.asyncio
    async def test_memory_only_fallback(self):
        """Test composite cache with memory only."""
        memory_cache = MemoryCache(max_size=3)
        composite = CompositeCache(memory_cache, None)

        await composite.set("key1", "value1")
        assert await composite.get("key1") == "value1"

    @pytest.mark.asyncio
    async def test_operations_with_both_layers(self, composite_cache):
        """Test all operations work with both cache layers."""
        # Set, get, delete, clear should all work
        await composite_cache.set("key1", "value1")
        result = await composite_cache.get("key1")
        assert result == "value1"

        await composite_cache.delete("key1")
        assert await composite_cache.get("key1") is None

        await composite_cache.set("key2", "value2")
        await composite_cache.clear()
        assert await composite_cache.get("key2") is None

    def test_get_stats(self, composite_cache):
        """Test composite cache statistics."""
        stats = composite_cache.get_stats()
        assert stats["type"] == "composite"
        assert "memory" in stats
        assert "redis" in stats