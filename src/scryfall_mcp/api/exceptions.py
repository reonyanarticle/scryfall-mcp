"""Custom exceptions for rate limiting."""

from __future__ import annotations


class RateLimitExceededError(Exception):
    """Raised when user exceeds their rate limit.

    This domain exception should be caught by HTTP middleware
    and converted to appropriate HTTP responses (429).

    Parameters
    ----------
    user_id : str
        User identifier who exceeded the limit
    limit : int
        Maximum requests allowed per window
    retry_after : int
        Seconds until rate limit resets
    current_count : int | None, optional
        Actual request count that triggered limit

    Attributes
    ----------
    user_id : str
        User who exceeded the limit
    limit : int
        The rate limit that was exceeded
    retry_after : int
        Seconds until user can retry
    current_count : int | None
        Number of requests made (if available)

    Examples
    --------
    >>> raise RateLimitExceededError("user123", 100, 60, 150)
    RateLimitExceededError: User user123 exceeded rate limit of 100 req/min
    (made 150 requests). Retry after 60s
    """

    def __init__(
        self,
        user_id: str,
        limit: int,
        retry_after: int,
        current_count: int | None = None,
    ) -> None:
        """Initialize rate limit exceeded error.

        Parameters
        ----------
        user_id : str
            User who exceeded the limit
        limit : int
            Maximum requests allowed
        retry_after : int
            Seconds until reset
        current_count : int | None, optional
            Actual request count
        """
        self.user_id = user_id
        self.limit = limit
        self.retry_after = retry_after
        self.current_count = current_count

        msg = f"User {user_id} exceeded rate limit of {limit} req/min"
        if current_count is not None:
            msg += f" (made {current_count} requests)"
        msg += f". Retry after {retry_after}s"

        super().__init__(msg)
