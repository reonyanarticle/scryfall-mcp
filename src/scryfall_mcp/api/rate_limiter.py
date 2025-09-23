"""Rate limiting implementation for Scryfall API.

This module provides rate limiting functionality to ensure compliance with
Scryfall's API rate limits (max 10 requests/second with 75-100ms intervals).
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from typing import Any

from ..settings import get_settings


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
        rate_limit_ms : int, optional
            Rate limit interval in milliseconds. If None, uses settings value.
        """
        settings = get_settings()
        self._rate_limit_ms = rate_limit_ms or settings.scryfall_rate_limit_ms
        self._last_request_time: float = 0.0
        self._backoff_until: float = 0.0
        self._consecutive_failures: int = 0
        self._max_backoff_seconds: float = 300.0  # 5 minutes max

    async def acquire(self) -> None:
        """Acquire permission to make a request.

        This method will block until it's safe to make a request, considering
        both rate limiting and any active exponential backoff.
        """
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
        status_code : int, optional
            HTTP status code of the failed request. Used to determine
            if exponential backoff should be applied.
        """
        self._consecutive_failures += 1

        # Apply exponential backoff for specific error codes
        if status_code in (429, 503, 502, 504):
            backoff_seconds = min(
                2 ** self._consecutive_failures,
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
        failure_threshold : int, optional
            Number of consecutive failures before opening the circuit.
        recovery_timeout : int, optional
            Time in seconds to wait before trying to close the circuit.
        """
        settings = get_settings()
        self._failure_threshold = (
            failure_threshold or settings.circuit_breaker_failure_threshold
        )
        self._recovery_timeout = (
            recovery_timeout or settings.circuit_breaker_recovery_timeout
        )

        self._failure_count: int = 0
        self._last_failure_time: float = 0.0
        self._state: str = "closed"  # closed, open, half_open

    async def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute a function with circuit breaker protection.

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
            If the circuit breaker is open
        """
        if self._state == "open":
            if time.time() - self._last_failure_time > self._recovery_timeout:
                self._state = "half_open"
            else:
                raise CircuitBreakerOpenError("Circuit breaker is open")

        try:
            result = await func(*args, **kwargs)
            self._record_success()
            return result
        except Exception:
            self._record_failure()
            raise

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
