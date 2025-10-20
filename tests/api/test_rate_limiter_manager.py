"""Tests for RateLimiterManager - multi-tenant rate limiting."""

from __future__ import annotations

import pytest

from scryfall_mcp.api.exceptions import RateLimitExceededError
from scryfall_mcp.api.rate_limit_backend import RateLimitBackend
from scryfall_mcp.api.rate_limiter import RateLimiterManager


class MockRateLimitBackend(RateLimitBackend):
    """Mock backend for testing rate limiting logic.

    Parameters
    ----------
    should_exceed : bool, optional
        If True, simulates rate limit exceeded (default: False)
    error_on_check : Exception | None, optional
        If provided, raises this error on increment_and_check
    """

    def __init__(
        self,
        should_exceed: bool = False,
        error_on_check: Exception | None = None,
    ) -> None:
        """Initialize mock backend.

        Parameters
        ----------
        should_exceed : bool, optional
            Whether to simulate exceeded limit
        error_on_check : Exception | None, optional
            Exception to raise if set
        """
        self.should_exceed = should_exceed
        self.error_on_check = error_on_check
        self.calls: list[tuple[str, int, int]] = []

    async def increment_and_check(
        self, key: str, limit: int, window_seconds: int
    ) -> tuple[int, bool]:
        """Mock rate limit check.

        Parameters
        ----------
        key : str
            Rate limit key
        limit : int
            Request limit
        window_seconds : int
            Time window

        Returns
        -------
        tuple[int, bool]
            (count, is_exceeded)

        Raises
        ------
        Exception
            If error_on_check is set
        """
        self.calls.append((key, limit, window_seconds))

        if self.error_on_check:
            raise self.error_on_check

        count = 150 if self.should_exceed else 1
        return count, self.should_exceed


class TestRateLimiterManager:
    """Test RateLimiterManager with mock backend."""

    @pytest.fixture
    def mock_backend_healthy(self) -> MockRateLimitBackend:
        """Create mock backend that allows requests."""
        return MockRateLimitBackend(should_exceed=False)

    @pytest.fixture
    def mock_backend_exceeded(self) -> MockRateLimitBackend:
        """Create mock backend that simulates exceeded limit."""
        return MockRateLimitBackend(should_exceed=True)

    @pytest.fixture
    def manager(
        self, mock_backend_healthy: MockRateLimitBackend
    ) -> RateLimiterManager:
        """Create manager with healthy backend."""
        return RateLimiterManager(backend=mock_backend_healthy)

    @pytest.mark.asyncio
    async def test_acquire_user_limit_success(
        self,
        manager: RateLimiterManager,
        mock_backend_healthy: MockRateLimitBackend,
    ) -> None:
        """Test successful rate limit acquisition."""
        await manager.acquire_user_limit("user123", limit=100)

        # Verify backend was called correctly
        assert len(mock_backend_healthy.calls) == 1
        assert mock_backend_healthy.calls[0] == ("rate_limit:user123", 100, 60)

    @pytest.mark.asyncio
    async def test_acquire_user_limit_exceeded(
        self, mock_backend_exceeded: MockRateLimitBackend
    ) -> None:
        """Test rate limit exceeded raises custom exception."""
        manager = RateLimiterManager(backend=mock_backend_exceeded)

        with pytest.raises(RateLimitExceededError) as exc_info:
            await manager.acquire_user_limit("user123", limit=100)

        # Verify exception details
        assert exc_info.value.user_id == "user123"
        assert exc_info.value.limit == 100
        assert exc_info.value.retry_after == 60
        assert exc_info.value.current_count == 150

    @pytest.mark.asyncio
    async def test_acquire_user_limit_custom_window(
        self,
        manager: RateLimiterManager,
        mock_backend_healthy: MockRateLimitBackend,
    ) -> None:
        """Test rate limiting with custom time window."""
        await manager.acquire_user_limit("user456", limit=50, window_seconds=120)

        assert mock_backend_healthy.calls[0] == ("rate_limit:user456", 50, 120)

    @pytest.mark.asyncio
    async def test_acquire_user_limit_multiple_users(
        self,
        manager: RateLimiterManager,
        mock_backend_healthy: MockRateLimitBackend,
    ) -> None:
        """Test rate limiting tracks multiple users separately."""
        await manager.acquire_user_limit("user1", limit=100)
        await manager.acquire_user_limit("user2", limit=50)
        await manager.acquire_user_limit("user3", limit=200)

        assert len(mock_backend_healthy.calls) == 3
        assert mock_backend_healthy.calls[0][0] == "rate_limit:user1"
        assert mock_backend_healthy.calls[1][0] == "rate_limit:user2"
        assert mock_backend_healthy.calls[2][0] == "rate_limit:user3"

    @pytest.mark.asyncio
    async def test_acquire_scryfall_limit(self, manager: RateLimiterManager) -> None:
        """Test global Scryfall API rate limiting."""
        # Should not raise exception
        await manager.acquire_scryfall_limit()

        # Verify Scryfall limiter exists
        assert manager._scryfall_limiter is not None

    @pytest.mark.asyncio
    async def test_backend_connection_error_propagates(self) -> None:
        """Test that backend connection errors propagate to caller."""
        backend = MockRateLimitBackend(
            error_on_check=ConnectionError("Redis unavailable")
        )
        manager = RateLimiterManager(backend=backend)

        with pytest.raises(ConnectionError, match="Redis unavailable"):
            await manager.acquire_user_limit("user123", limit=100)


class TestMemoryRateLimitBackend:
    """Test in-memory rate limiting backend."""

    @pytest.mark.asyncio
    async def test_memory_backend_basic(self) -> None:
        """Test memory backend allows requests."""
        from scryfall_mcp.api.rate_limit_backend import MemoryRateLimitBackend

        backend = MemoryRateLimitBackend()
        count, exceeded = await backend.increment_and_check(
            "rate_limit:user123", limit=100, window_seconds=60
        )

        assert count == 1
        assert exceeded is False

    @pytest.mark.asyncio
    async def test_memory_backend_multiple_keys(self) -> None:
        """Test memory backend handles multiple keys."""
        from scryfall_mcp.api.rate_limit_backend import MemoryRateLimitBackend

        backend = MemoryRateLimitBackend()

        await backend.increment_and_check("rate_limit:user1", 100, 60)
        await backend.increment_and_check("rate_limit:user2", 50, 60)

        assert len(backend._limiters) == 2

    @pytest.mark.asyncio
    async def test_memory_backend_lru_eviction(self) -> None:
        """Test memory backend evicts least recently used keys."""
        from scryfall_mcp.api.rate_limit_backend import MemoryRateLimitBackend

        backend = MemoryRateLimitBackend(max_users=2)

        # Fill to capacity
        await backend.increment_and_check("rate_limit:user1", 100, 60)
        await backend.increment_and_check("rate_limit:user2", 100, 60)

        # This should evict user1 (oldest)
        await backend.increment_and_check("rate_limit:user3", 100, 60)

        assert len(backend._limiters) == 2
        assert "rate_limit:user1" not in backend._limiters
        assert "rate_limit:user2" in backend._limiters
        assert "rate_limit:user3" in backend._limiters

    @pytest.mark.asyncio
    async def test_memory_backend_lru_move_to_end(self) -> None:
        """Test memory backend moves accessed keys to end (MRU)."""
        from scryfall_mcp.api.rate_limit_backend import MemoryRateLimitBackend

        backend = MemoryRateLimitBackend(max_users=2)

        # Fill to capacity
        await backend.increment_and_check("rate_limit:user1", 100, 60)
        await backend.increment_and_check("rate_limit:user2", 100, 60)

        # Access user1 again (moves to end)
        await backend.increment_and_check("rate_limit:user1", 100, 60)

        # This should evict user2 (now oldest)
        await backend.increment_and_check("rate_limit:user3", 100, 60)

        assert len(backend._limiters) == 2
        assert "rate_limit:user1" in backend._limiters  # Still present (MRU)
        assert "rate_limit:user2" not in backend._limiters  # Evicted
        assert "rate_limit:user3" in backend._limiters
