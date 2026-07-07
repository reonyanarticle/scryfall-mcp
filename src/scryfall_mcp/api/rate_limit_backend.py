"""Rate limiting backend abstractions for distributed and local storage."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from collections import OrderedDict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from redis.asyncio import Redis  # type: ignore[import-not-found]


class RateLimitBackend(ABC):
    """Abstract backend for distributed rate limiting.

    This protocol defines the interface for rate limiting storage backends,
    enabling easy swapping between Redis, in-memory, and other implementations.
    """

    @abstractmethod
    async def increment_and_check(
        self, key: str, limit: int, window_seconds: int
    ) -> tuple[int, bool]:
        """Increment request counter and check if limit exceeded.

        Parameters
        ----------
        key : str
            Unique rate limit key (e.g., "rate_limit:user123")
        limit : int
            Maximum requests allowed within window
        window_seconds : int
            Time window duration in seconds

        Returns
        -------
        tuple[int, bool]
            Tuple of (current_count, is_exceeded) where:
            - current_count: Number of requests in current window
            - is_exceeded: True if limit was exceeded, False otherwise

        Raises
        ------
        ConnectionError
            If backend is unavailable
        TimeoutError
            If operation times out
        """
        ...


class RedisRateLimitBackend(RateLimitBackend):
    """Redis-based distributed rate limiting backend.

    Uses Redis INCR and EXPIRE commands for atomic rate limiting
    across multiple server instances.

    Parameters
    ----------
    redis_client : Redis
        Async Redis client instance

    Examples
    --------
    >>> import redis.asyncio as redis
    >>> client = await redis.from_url("redis://localhost:6379")
    >>> backend = RedisRateLimitBackend(client)
    >>> count, exceeded = await backend.increment_and_check(
    ...     "rate_limit:user123", limit=100, window_seconds=60
    ... )
    """

    def __init__(self, redis_client: Redis) -> None:
        """Initialize Redis backend.

        Parameters
        ----------
        redis_client : Redis
            Async Redis client for rate limit storage
        """
        self._redis = redis_client

    async def increment_and_check(
        self, key: str, limit: int, window_seconds: int
    ) -> tuple[int, bool]:
        """Implement Redis-based rate limiting with atomic operations.

        Uses Redis INCR for atomic increment and EXPIRE for time window.
        First request in window sets the expiry time.

        Parameters
        ----------
        key : str
            Redis key for rate limit counter
        limit : int
            Maximum requests per window
        window_seconds : int
            Window duration in seconds

        Returns
        -------
        tuple[int, bool]
            (current_count, is_exceeded)
        """
        # Atomic increment
        current = await self._redis.incr(key)

        # Set expiry on first request in window
        if current == 1:
            await self._redis.expire(key, window_seconds)

        is_exceeded = current > limit
        return current, is_exceeded

    async def close(self) -> None:
        """Close Redis connection."""
        await self._redis.aclose()


class MemoryRateLimitBackend(RateLimitBackend):
    """In-memory rate limiting backend for single-instance deployments.

    Uses fixed-window counting with the same semantics as
    `RedisRateLimitBackend` (INCR within a window, reject when the count
    exceeds the limit), so swapping backends does not change enforcement
    behavior. Suitable for development and single-server deployments.

    Parameters
    ----------
    max_users : int, optional
        Maximum number of users to track before LRU eviction (default: 10000)

    Examples
    --------
    >>> backend = MemoryRateLimitBackend()
    >>> count, exceeded = await backend.increment_and_check(
    ...     "rate_limit:user123", limit=100, window_seconds=60
    ... )
    """

    def __init__(self, max_users: int = 10000) -> None:
        """Initialize memory backend with LRU eviction.

        Parameters
        ----------
        max_users : int, optional
            Maximum number of users to track before LRU eviction (default: 10000)
        """
        # key -> (window_start_monotonic, request_count)
        self._windows: OrderedDict[str, tuple[float, int]] = OrderedDict()
        self._max_users = max_users

    async def increment_and_check(
        self, key: str, limit: int, window_seconds: int
    ) -> tuple[int, bool]:
        """Implement fixed-window rate limiting in memory.

        Mirrors the Redis backend: increments the counter for the current
        window and reports whether the limit is exceeded. Implements LRU
        eviction when max_users is exceeded.

        Parameters
        ----------
        key : str
            Rate limit key
        limit : int
            Maximum requests per window
        window_seconds : int
            Window duration in seconds

        Returns
        -------
        tuple[int, bool]
            (current_count, is_exceeded)
        """
        now = time.monotonic()
        window_start, count = self._windows.get(key, (now, 0))

        # Start a fresh window when the previous one has elapsed
        if now - window_start >= window_seconds:
            window_start, count = now, 0

        count += 1
        self._windows[key] = (window_start, count)
        self._windows.move_to_end(key)

        # Evict oldest entries if over capacity (LRU)
        while len(self._windows) > self._max_users:
            self._windows.popitem(last=False)

        return count, count > limit
