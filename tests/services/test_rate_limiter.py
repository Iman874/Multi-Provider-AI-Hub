import time
from unittest.mock import patch

from app.services.rate_limiter import RateLimiter


class TestRateLimiter:
    def test_within_limit(self):
        """N requests within RPM → all return True."""
        rl = RateLimiter(5)
        for _ in range(5):
            assert rl.check() is True

    def test_exceed_limit(self):
        """N+1th request → returns False."""
        rl = RateLimiter(5)
        for _ in range(5):
            rl.check()
        assert rl.check() is False

    def test_window_expiry(self):
        """Requests older than 60s are evicted, freeing capacity."""
        rl = RateLimiter(2)
        rl.check()  # request 1
        rl.check()  # request 2 — now full
        assert rl.check() is False
        # Simulate 61 seconds passing
        with patch("app.services.rate_limiter.time") as mock_time:
            mock_time.time.return_value = time.time() + 61
            assert rl.check() is True  # old ones evicted

    def test_unlimited(self):
        """RPM 0 → always returns True."""
        rl = RateLimiter(0)
        for _ in range(1000):
            assert rl.check() is True

    def test_remaining_count(self):
        """get_remaining decreases with each successful check."""
        rl = RateLimiter(10)
        assert rl.get_remaining() == 10
        rl.check()
        assert rl.get_remaining() == 9
        rl.check()
        assert rl.get_remaining() == 8

    def test_remaining_unlimited(self):
        """RPM 0 → get_remaining returns -1."""
        assert RateLimiter(0).get_remaining() == -1

    def test_reset(self):
        """reset() clears window, allowing requests again."""
        rl = RateLimiter(2)
        rl.check()
        rl.check()
        assert rl.check() is False
        rl.reset()
        assert rl.check() is True

    def test_is_enabled(self):
        """RPM > 0 → enabled, RPM 0 → disabled."""
        assert RateLimiter(10).is_enabled is True
        assert RateLimiter(0).is_enabled is False
