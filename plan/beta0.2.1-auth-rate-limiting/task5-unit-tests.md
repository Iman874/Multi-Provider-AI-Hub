# Task 5 — Unit Tests

## 1. Judul Task
Unit tests untuk RateLimiter dan Auth dependency

## 2. Deskripsi
Membuat test suite lengkap: 8 test untuk RateLimiter, 8 test untuk `verify_gateway_token`. Memastikan existing tests tidak rusak.

## 3. Tujuan Teknis
- 16 test baru total (8 rate limiter + 8 auth)
- Zero regression pada 52 existing tests
- Mock `time.time()` untuk window expiry
- Mock `_token` untuk auth disabled scenario

## 4. Scope
### Yang dikerjakan
- `tests/core/__init__.py` — init file
- `tests/core/test_auth.py` — 8 tests
- `tests/services/test_rate_limiter.py` — 8 tests

### Yang TIDAK dikerjakan
- Integration tests terhadap real endpoints (manual test saja)

## 5. Langkah Implementasi

### Step 1: Buat `tests/core/__init__.py` (empty file)

### Step 2: Buat `tests/services/test_rate_limiter.py`

```python
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
```

### Step 3: Buat `tests/core/test_auth.py`

```python
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from starlette.testclient import TestClient
from app.core.exceptions import AuthenticationError, RateLimitExceededError

class TestVerifyGatewayToken:
    @pytest.mark.asyncio
    async def test_valid_token(self):
        """Valid Bearer token → returns token string."""
        # Patch _token and create mock Request with valid header

    @pytest.mark.asyncio
    async def test_invalid_token(self):
        """Wrong token → raises AuthenticationError."""

    @pytest.mark.asyncio
    async def test_missing_header(self):
        """No Authorization header → raises AuthenticationError."""

    @pytest.mark.asyncio
    async def test_malformed_no_bearer(self):
        """'Token xxx' format → raises AuthenticationError."""

    @pytest.mark.asyncio
    async def test_malformed_empty_token(self):
        """'Bearer ' (empty after Bearer) → raises AuthenticationError."""

    @pytest.mark.asyncio
    async def test_auth_disabled(self):
        """_token="" → returns None without any checks."""

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self):
        """Rate limiter returns False → raises RateLimitExceededError."""

    def test_public_health_endpoint(self):
        """GET /health without token → 200."""
        # Use TestClient, assert 200
```

## 6. Output yang Diharapkan
```
$ pytest tests/ -v
...
tests/services/test_rate_limiter.py::TestRateLimiter::test_within_limit PASSED
tests/services/test_rate_limiter.py::TestRateLimiter::test_exceed_limit PASSED
tests/services/test_rate_limiter.py::TestRateLimiter::test_window_expiry PASSED
tests/services/test_rate_limiter.py::TestRateLimiter::test_unlimited PASSED
tests/services/test_rate_limiter.py::TestRateLimiter::test_remaining_count PASSED
tests/services/test_rate_limiter.py::TestRateLimiter::test_remaining_unlimited PASSED
tests/services/test_rate_limiter.py::TestRateLimiter::test_reset PASSED
tests/services/test_rate_limiter.py::TestRateLimiter::test_is_enabled PASSED
tests/core/test_auth.py::TestVerifyGatewayToken::test_valid_token PASSED
tests/core/test_auth.py::TestVerifyGatewayToken::test_invalid_token PASSED
... (8 more auth tests)
... (52 existing tests)
========================= 68 passed =========================
```

## 7. Dependencies
- Task 1, Task 2, Task 3, Task 4 — semua harus selesai

## 8. Acceptance Criteria
- [ ] 8 rate limiter tests → all PASS
- [ ] 8 auth dependency tests → all PASS
- [ ] 52 existing tests → all PASS (zero regression)
- [ ] `pytest tests/ -v` → 68 total, 68 passed
- [ ] Window expiry test menggunakan mock `time.time()`
- [ ] Auth disabled test menggunakan mock/patch `_token`

## 9. Estimasi
Medium (~60 menit)
