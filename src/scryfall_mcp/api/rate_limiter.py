"""Rate limiting implementation for Scryfall API.

This module provides rate limiting functionality to ensure compliance with
Scryfall's API rate limits (max 10 requests/second with 75-100ms intervals).
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .rate_limit_backend import RateLimitBackend

from ..settings import MAX_BACKOFF_SECONDS, get_settings

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter with exponential backoff support.

    This class implements rate limiting to ensure we don't exceed Scryfall's
    API limits. It supports both basic rate limiting and exponential backoff
    for handling 429 responses.
    """

    def __init__(self, rate_limit_ms: int | None = None) -> None:
        """Initialize the rate limiter.

        Parameters
        ----------
        rate_limit_ms : int | None, optional (default: None)
            Rate limit interval in milliseconds. If None, uses settings value.
        """
        settings = get_settings()
        self._rate_limit_ms = rate_limit_ms or settings.scryfall_rate_limit_ms
        self._last_request_time: float = 0.0
        self._backoff_until: float = 0.0
        self._consecutive_failures: int = 0
        self._max_backoff_seconds: float = MAX_BACKOFF_SECONDS
        self._lock = asyncio.Lock()  # Protect shared state from concurrent access

    async def acquire(self) -> None:
        """Acquire permission to make a request.

        This method will block until it's safe to make a request, considering
        both rate limiting and any active exponential backoff.

        Thread-safe: Uses asyncio.Lock to prevent race conditions.

        Notes
        -----
        The lock is INTENTIONALLY held across the sleep: Scryfall's rate
        limit is global, so all outgoing requests must be serialized. A
        429/503 backoff therefore delays every pending request, by design.
        """
        async with self._lock:
            now = time.time()

            # Handle exponential backoff
            if self._backoff_until > now:
                wait_time = self._backoff_until - now
                await asyncio.sleep(wait_time)
                now = time.time()

            # Handle regular rate limiting
            time_since_last = now - self._last_request_time
            required_interval = self._rate_limit_ms / 1000.0

            if time_since_last < required_interval:
                wait_time = required_interval - time_since_last
                await asyncio.sleep(wait_time)

            self._last_request_time = time.time()

    def record_success(self) -> None:
        """Record a successful request.

        This resets the failure counter and any active backoff.
        """
        self._consecutive_failures = 0
        self._backoff_until = 0.0

    def record_failure(self, status_code: int | None = None) -> None:
        """Record a failed request and apply exponential backoff.

        Parameters
        ----------
        status_code : int | None, optional (default: None)
            HTTP status code of the failed request. Used to determine
            if exponential backoff should be applied.
        """
        self._consecutive_failures += 1

        # Apply exponential backoff for specific error codes
        if status_code in (429, 503, 502, 504):
            backoff_seconds = min(
                2**self._consecutive_failures,
                self._max_backoff_seconds,
            )
            self._backoff_until = time.time() + backoff_seconds

    def reset(self) -> None:
        """Reset the rate limiter state."""
        self._last_request_time = 0.0
        self._backoff_until = 0.0
        self._consecutive_failures = 0

    @property
    def rate_limit_ms(self) -> int:
        """Get the current rate limit interval in milliseconds."""
        return self._rate_limit_ms

    @property
    def is_backing_off(self) -> bool:
        """Check if the rate limiter is currently in backoff mode."""
        return time.time() < self._backoff_until

    @property
    def backoff_remaining(self) -> float:
        """Get the remaining backoff time in seconds."""
        if not self.is_backing_off:
            return 0.0
        return max(0.0, self._backoff_until - time.time())


class CircuitBreaker:
    """Circuit breaker implementation for API reliability.

    This class implements the circuit breaker pattern to prevent cascading
    failures when the API is experiencing issues.
    """

    def __init__(
        self,
        failure_threshold: int | None = None,
        recovery_timeout: int | None = None,
    ) -> None:
        """Initialize the circuit breaker.

        Parameters
        ----------
        failure_threshold : int | None, optional (default: None)
            Number of consecutive failures before opening the circuit.
        recovery_timeout : int | None, optional (default: None)
            Time in seconds to wait before trying to close the circuit.
        """
        settings = get_settings()
        # `is not None` (not `or`): an explicit 0 must not fall back to the
        # settings default
        self._failure_threshold = (
            failure_threshold
            if failure_threshold is not None
            else settings.circuit_breaker_failure_threshold
        )
        self._recovery_timeout = (
            recovery_timeout
            if recovery_timeout is not None
            else settings.circuit_breaker_recovery_timeout
        )

        self._failure_count: int = 0
        self._last_failure_time: float = 0.0
        self._state: str = "closed"  # closed, open, half_open
        # Protect state transitions across the await suspension points and
        # limit half_open to a single recovery probe at a time
        self._lock = asyncio.Lock()
        self._half_open_trial_active: bool = False

    async def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute a function with circuit breaker protection.

        State transitions are guarded by an asyncio.Lock, and in the
        half_open state only ONE request is allowed through as a recovery
        probe — concurrent requests are rejected instead of stampeding the
        recovering upstream.

        Parameters
        ----------
        func : callable
            The function to execute
        *args : tuple
            Positional arguments for the function
        **kwargs : dict
            Keyword arguments for the function

        Returns
        -------
        Any
            The result of the function call

        Raises
        ------
        CircuitBreakerOpenError
            If the circuit breaker is open, or a recovery probe is already
            in flight while half_open
        """
        is_trial = False
        async with self._lock:
            if self._state == "open":
                if time.time() - self._last_failure_time > self._recovery_timeout:
                    self._state = "half_open"
                else:
                    raise CircuitBreakerOpenError("Circuit breaker is open")

            if self._state == "half_open":
                if self._half_open_trial_active:
                    raise CircuitBreakerOpenError(
                        "Circuit breaker is open (recovery probe in progress)"
                    )
                self._half_open_trial_active = True
                is_trial = True

        try:
            result = await func(*args, **kwargs)
        except Exception:
            async with self._lock:
                self._record_failure()
                if is_trial:
                    self._half_open_trial_active = False
            raise
        else:
            async with self._lock:
                self._record_success()
                if is_trial:
                    self._half_open_trial_active = False
            return result

    def _record_success(self) -> None:
        """Record a successful operation."""
        self._failure_count = 0
        if self._state == "half_open":
            self._state = "closed"

    def _record_failure(self) -> None:
        """Record a failed operation."""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._failure_count >= self._failure_threshold:
            self._state = "open"

    def reset(self) -> None:
        """Reset the circuit breaker to closed state."""
        self._failure_count = 0
        self._last_failure_time = 0.0
        self._state = "closed"
        self._half_open_trial_active = False

    @property
    def state(self) -> str:
        """Get the current state of the circuit breaker."""
        return self._state

    @property
    def failure_count(self) -> int:
        """Get the current failure count."""
        return self._failure_count


class CircuitBreakerOpenError(Exception):
    """Exception raised when circuit breaker is open."""


# Global instances
_rate_limiter: RateLimiter | None = None
_circuit_breaker: CircuitBreaker | None = None


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance.

    Returns
    -------
    RateLimiter
        The global rate limiter instance
    """
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


def get_circuit_breaker() -> CircuitBreaker:
    """Get the global circuit breaker instance.

    Returns
    -------
    CircuitBreaker
        The global circuit breaker instance
    """
    global _circuit_breaker
    if _circuit_breaker is None:
        _circuit_breaker = CircuitBreaker()
    return _circuit_breaker


def reset_rate_limiting() -> None:
    """Reset all rate limiting state."""
    global _rate_limiter, _circuit_breaker
    if _rate_limiter:
        _rate_limiter.reset()
    if _circuit_breaker:
        _circuit_breaker.reset()


class RateLimiterManager:
    """Manage per-user rate limiting with pluggable backends.

    This class coordinates user rate limiting using a configurable backend
    (Redis for distributed, memory for local) and maintains compatibility
    with the existing Scryfall API rate limiter.

    Parameters
    ----------
    backend : RateLimitBackend
        Rate limiting storage backend
    scryfall_limiter : RateLimiter | None, optional
        Global Scryfall API rate limiter. If None, uses default instance.

    Examples
    --------
    >>> from .rate_limit_backend import MemoryRateLimitBackend
    >>> backend = MemoryRateLimitBackend()
    >>> manager = RateLimiterManager(backend)
    >>> await manager.acquire_user_limit("user123", limit=100)
    """

    def __init__(
        self,
        backend: RateLimitBackend,
        scryfall_limiter: RateLimiter | None = None,
    ) -> None:
        """Initialize rate limiter manager.

        Parameters
        ----------
        backend : RateLimitBackend
            Rate limiting backend implementation
        scryfall_limiter : RateLimiter | None, optional
            Scryfall API rate limiter. Uses global instance if None.
        """

        self._backend = backend
        self._scryfall_limiter = scryfall_limiter or get_rate_limiter()

    async def acquire_user_limit(
        self,
        user_id: str,
        limit: int = 100,
        window_seconds: int = 60,
    ) -> None:
        """Acquire rate limit permission for user.

        Parameters
        ----------
        user_id : str
            Unique user identifier from JWT payload
        limit : int, optional
            Maximum requests per window (default: 100)
        window_seconds : int, optional
            Time window in seconds (default: 60)

        Raises
        ------
        RateLimitExceededError
            If user has exceeded their rate limit
        ConnectionError
            If backend is unavailable
        """
        from .exceptions import RateLimitExceededError

        key = f"rate_limit:{user_id}"
        current, is_exceeded = await self._backend.increment_and_check(
            key, limit, window_seconds
        )

        if is_exceeded:
            raise RateLimitExceededError(user_id, limit, window_seconds, current)

    async def acquire_scryfall_limit(self) -> None:
        """Acquire global Scryfall API rate limit.

        This maintains compatibility with the existing Scryfall API
        rate limiting system (10 req/sec).
        """
        await self._scryfall_limiter.acquire()
