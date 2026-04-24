# Task 2 — Rate Limiter Service

## 1. Judul Task
Implementasi in-memory sliding window rate limiter service

## 2. Deskripsi
Membuat class `RateLimiter` yang menggunakan sliding window counter berbasis `collections.deque` untuk membatasi jumlah request per menit. Service ini akan dipakai oleh auth dependency di Task 3.

## 3. Tujuan Teknis
- Class `RateLimiter` yang standalone dan testable
- Sliding window 60 detik — request lama otomatis di-evict
- Thread-safe dengan `threading.Lock`
- Bisa di-disable dengan `max_rpm=0`

## 4. Scope
### Yang dikerjakan
- `app/services/rate_limiter.py` — file baru, 1 class

### Yang TIDAK dikerjakan
- Integrasi ke auth dependency (Task 3)
- Per-user/per-token rate limiting (global saja)
- Persistent storage (in-memory only)

## 5. Langkah Implementasi

### Step 1: Buat file `app/services/rate_limiter.py`

```python
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
```

## 6. Output yang Diharapkan

Verifikasi manual:
```python
from app.services.rate_limiter import RateLimiter

# Basic usage
rl = RateLimiter(5)
for i in range(5):
    assert rl.check() is True, f"Request {i+1} should pass"
assert rl.check() is False, "Request 6 should be blocked"
assert rl.get_remaining() == 0

# Unlimited
rl_unlim = RateLimiter(0)
assert rl_unlim.check() is True
assert rl_unlim.get_remaining() == -1
assert rl_unlim.is_enabled is False

# Reset
rl.reset()
assert rl.check() is True  # Window cleared, can request again

print("All checks passed!")
```

## 7. Dependencies
- Task 1 (config & exceptions harus sudah ada, meskipun RateLimiter sendiri tidak import dari sana)

## 8. Acceptance Criteria
- [ ] `RateLimiter(120)` → 120 requests allowed, request ke-121 return False
- [ ] `RateLimiter(0)` → `check()` selalu True, `is_enabled` = False
- [ ] `get_remaining()` berkurang 1 setiap `check()` yang return True
- [ ] `get_remaining()` return -1 jika unlimited (RPM=0)
- [ ] Timestamps > 60 detik otomatis di-evict saat `check()` atau `get_remaining()`
- [ ] `reset()` mengosongkan deque → bisa request lagi
- [ ] Thread-safe: semua public methods menggunakan Lock
- [ ] `WINDOW_SECONDS = 60` sebagai class constant
- [ ] Log saat init menunjukkan RPM dan status

## 9. Estimasi
Low (~30 menit)
