"""Rate limiting backend abstractions for distributed and local storage."""

from __future__ import annotations

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

    Uses existing RateLimiter class for per-key rate limiting.
    Suitable for development and single-server deployments.

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
        from .rate_limiter import RateLimiter

        self._limiters: OrderedDict[str, RateLimiter] = OrderedDict()
        self._max_users = max_users

    async def increment_and_check(
        self, key: str, limit: int, window_seconds: int
    ) -> tuple[int, bool]:
        """Implement memory-based rate limiting.

        Creates per-key RateLimiter instances with appropriate intervals.
        Implements LRU eviction when max_users is exceeded.

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
            (1, False) - Memory backend doesn't track exact counts
        """
        from .rate_limiter import RateLimiter

        # Create limiter if not exists
        if key not in self._limiters:
            # Evict oldest if over capacity
            if len(self._limiters) >= self._max_users:
                self._limiters.popitem(last=False)  # Remove oldest (LRU)

            # Calculate per-request interval
            interval_ms = int((window_seconds * 1000.0) / limit)
            self._limiters[key] = RateLimiter(rate_limit_ms=interval_ms)
        else:
            # Move to end (most recently used)
            self._limiters.move_to_end(key)

        # Acquire blocks if rate limit would be exceeded
        await self._limiters[key].acquire()
        return 1, False  # Memory backend doesn't return exact count
