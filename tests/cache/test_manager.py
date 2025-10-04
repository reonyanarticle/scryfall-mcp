"""Tests for cache manager implementation."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

from scryfall_mcp.cache.manager import CacheManager, get_cache, _create_cache_manager
from scryfall_mcp.cache.backends import MemoryCache


class TestCacheManager:
    """Test cache manager functionality."""

    @pytest.fixture
    def cache_manager(self):
        """Create a cache manager with memory backend."""
        cache = MemoryCache(max_size=10)
        return CacheManager(cache)

    def test_build_key_simple(self, cache_manager):
        """Test simple key building."""
        key = cache_manager.build_key("test", param1="value1", param2="value2")
        assert key == "test:param1=value1&param2=value2"

    def test_build_key_with_long_params(self, cache_manager):
        """Test key building with long parameters (should be hashed)."""
        long_value = "x" * 200
        key = cache_manager.build_key("test", param1=long_value)
        # Should be hashed due to length
        assert key.startswith("test:")
        assert len(key) < 100  # Should be shorter due to hashing

    def test_build_key_parameter_order(self, cache_manager):
        """Test that parameter order doesn't affect key generation."""
        key1 = cache_manager.build_key("test", a=1, b=2, c=3)
        key2 = cache_manager.build_key("test", c=3, a=1, b=2)
        assert key1 == key2

    @pytest.mark.asyncio
    async def test_cache_operations(self, cache_manager):
        """Test basic cache operations through manager."""
        # Test set and get
        await cache_manager.set("namespace", "test_value", param1="value1")
        result = await cache_manager.get("namespace", param1="value1")
        assert result == "test_value"

        # Test with TTL
        await cache_manager.set("namespace", "ttl_value", ttl=60, param2="value2")
        result = await cache_manager.get("namespace", param2="value2")
        assert result == "ttl_value"

    @pytest.mark.asyncio
    async def test_delete_and_clear(self, cache_manager):
        """Test delete and clear operations."""
        # Set some values
        await cache_manager.set("namespace1", "value1", param="test1")
        await cache_manager.set("namespace2", "value2", param="test2")

        # Test delete specific key
        await cache_manager.delete("namespace1", param="test1")
        assert await cache_manager.get("namespace1", param="test1") is None
        assert await cache_manager.get("namespace2", param="test2") == "value2"

        # Test clear all
        await cache_manager.clear()
        assert await cache_manager.get("namespace2", param="test2") is None

    @pytest.mark.asyncio
    async def test_close(self, cache_manager):
        """Test cache manager close operation."""
        await cache_manager.close()
        # Should not raise any errors

    def test_get_stats(self, cache_manager):
        """Test cache statistics."""
        stats = cache_manager.get_stats()
        assert "type" in stats


class TestCacheFactory:
    """Test cache factory functions."""

    @patch("scryfall_mcp.cache.manager.get_settings")
    def test_get_cache_disabled(self, mock_get_settings):
        """Test get_cache when caching is disabled."""
        mock_settings = AsyncMock()
        mock_settings.cache_enabled = False
        mock_get_settings.return_value = mock_settings

        result = get_cache()
        assert result is None

    @patch("scryfall_mcp.cache.manager.get_settings")
    def test_get_cache_memory_backend(self, mock_get_settings):
        """Test cache creation with memory backend."""
        mock_settings = AsyncMock()
        mock_settings.cache_enabled = True
        mock_settings.cache_backend = "memory"
        mock_settings.cache_max_size = 100
        mock_settings.cache_ttl_default = 3600
        mock_get_settings.return_value = mock_settings

        # Reset global cache
        import scryfall_mcp.cache.manager

        scryfall_mcp.cache.manager._cache_manager = None

        cache_manager = get_cache()
        assert cache_manager is not None
        assert isinstance(cache_manager, CacheManager)

    @patch("scryfall_mcp.cache.manager.get_settings")
    def test_create_cache_manager_memory(self, mock_get_settings):
        """Test cache manager creation with memory backend."""
        mock_settings = AsyncMock()
        mock_settings.cache_backend = "memory"
        mock_settings.cache_max_size = 50
        mock_settings.cache_ttl_default = 1800
        mock_get_settings.return_value = mock_settings

        manager = _create_cache_manager()
        assert isinstance(manager, CacheManager)
        stats = manager.get_stats()
        assert stats["type"] == "memory"

    @patch("scryfall_mcp.cache.manager.get_settings")
    def test_create_cache_manager_composite(self, mock_get_settings):
        """Test cache manager creation with composite backend."""
        mock_settings = AsyncMock()
        mock_settings.cache_backend = "composite"
        mock_settings.cache_max_size = 50
        mock_settings.cache_ttl_default = 1800
        mock_settings.cache_redis_url = "redis://localhost:6379"
        mock_get_settings.return_value = mock_settings

        manager = _create_cache_manager()
        assert isinstance(manager, CacheManager)
        stats = manager.get_stats()
        assert stats["type"] == "composite"

    @patch("scryfall_mcp.cache.manager.get_settings")
    def test_create_cache_manager_redis_fallback(self, mock_get_settings):
        """Test fallback to memory when Redis fails."""
        mock_settings = AsyncMock()
        mock_settings.cache_backend = "redis"
        mock_settings.cache_max_size = 50
        mock_settings.cache_ttl_default = 1800
        mock_settings.cache_redis_url = "redis://invalid:6379"
        mock_get_settings.return_value = mock_settings

        # Redis should fail to connect, falling back to memory
        manager = _create_cache_manager()
        assert isinstance(manager, CacheManager)

    @pytest.mark.asyncio
    async def test_close_cache_function(self):
        """Test global cache close function."""
        from scryfall_mcp.cache.manager import close_cache

        # Should not raise even if no cache is initialized
        await close_cache()

    @patch("scryfall_mcp.cache.manager.get_settings")
    def test_singleton_behavior(self, mock_get_settings):
        """Test that get_cache returns the same instance."""
        mock_settings = AsyncMock()
        mock_settings.cache_enabled = True
        mock_settings.cache_backend = "memory"
        mock_settings.cache_max_size = 100
        mock_settings.cache_ttl_default = 3600
        mock_get_settings.return_value = mock_settings

        # Reset global cache
        import scryfall_mcp.cache.manager

        scryfall_mcp.cache.manager._cache_manager = None

        cache1 = get_cache()
        cache2 = get_cache()
        assert cache1 is cache2  # Should be the same instance


class TestCacheIntegration:
    """Test cache integration scenarios."""

    @pytest.mark.asyncio
    async def test_concurrent_access(self):
        """Test concurrent cache access."""
        import asyncio
        from scryfall_mcp.cache.backends import MemoryCache

        cache = MemoryCache(max_size=10)
        manager = CacheManager(cache)

        async def set_value(i):
            await manager.set("test", f"value_{i}", key=f"key_{i}")
            return await manager.get("test", key=f"key_{i}")

        # Run concurrent operations
        tasks = [set_value(i) for i in range(5)]
        results = await asyncio.gather(*tasks)

        # All operations should succeed
        for i, result in enumerate(results):
            assert result == f"value_{i}"

    @pytest.mark.asyncio
    async def test_namespace_isolation(self):
        """Test that different namespaces are isolated."""
        from scryfall_mcp.cache.backends import MemoryCache

        cache = MemoryCache(max_size=10)
        manager = CacheManager(cache)

        # Set same key in different namespaces
        await manager.set("namespace1", "value1", key="same_key")
        await manager.set("namespace2", "value2", key="same_key")

        # Should get different values
        result1 = await manager.get("namespace1", key="same_key")
        result2 = await manager.get("namespace2", key="same_key")

        assert result1 == "value1"
        assert result2 == "value2"
