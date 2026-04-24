"""
In-memory sliding window rate limiter.

Uses a deque of timestamps to track requests within a 60-second window.
Thread-safe via threading.Lock.
"""

import time
import threading
from collections import deque

from loguru import logger


class RateLimiter:
    """
    Sliding window counter rate limiter.

    Tracks request timestamps in a deque. On each check, evicts
    timestamps older than 60 seconds, then compares count vs limit.
    """

    WINDOW_SECONDS = 60

    def __init__(self, max_rpm: int):
        """
        Args:
            max_rpm: Maximum requests per minute. 0 = unlimited.
        """
        self._max_rpm = max_rpm
        self._enabled = max_rpm > 0
        self._timestamps: deque[float] = deque()
        self._lock = threading.Lock()

        logger.info(
            "RateLimiter initialized: {rpm} req/min ({status})",
            rpm=max_rpm,
            status="enabled" if self._enabled else "unlimited",
        )

    @property
    def is_enabled(self) -> bool:
        """Whether rate limiting is active."""
        return self._enabled

    def _evict_expired(self, now: float) -> None:
        """Remove timestamps older than WINDOW_SECONDS. Must hold lock."""
        cutoff = now - self.WINDOW_SECONDS
        while self._timestamps and self._timestamps[0] < cutoff:
            self._timestamps.popleft()

    def check(self) -> bool:
        """
        Check if a request is allowed and record it.

        Returns:
            True if within limit, False if rate limited.
        """
        if not self._enabled:
            return True

        now = time.time()
        with self._lock:
            self._evict_expired(now)

            if len(self._timestamps) >= self._max_rpm:
                return False

            self._timestamps.append(now)
            return True

    def get_remaining(self) -> int:
        """
        Get remaining requests allowed in current window.

        Returns:
            Remaining count. -1 if unlimited.
        """
        if not self._enabled:
            return -1

        now = time.time()
        with self._lock:
            self._evict_expired(now)
            return max(0, self._max_rpm - len(self._timestamps))

    def reset(self) -> None:
        """Clear all tracked timestamps. Useful for testing."""
        with self._lock:
            self._timestamps.clear()
