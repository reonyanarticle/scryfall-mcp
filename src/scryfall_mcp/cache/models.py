"""Cache-layer data models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class CacheEntry(BaseModel):
    """Cache entry with metadata."""

    value: Any
    expires_at: float | None = None
    created_at: float

    def is_expired(self) -> bool:
        """Check if the entry has expired."""
        import time

        if self.expires_at is None:
            return False
        return time.time() > self.expires_at
