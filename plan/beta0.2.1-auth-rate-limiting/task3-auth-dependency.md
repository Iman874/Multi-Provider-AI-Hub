# Task 3 — Auth Dependency

## 1. Judul Task
Implementasi FastAPI dependency `verify_gateway_token` untuk validasi token dan rate limiting

## 2. Deskripsi
Membuat async function `verify_gateway_token` yang berfungsi sebagai FastAPI dependency. Function ini memvalidasi header `Authorization: Bearer <token>`, melakukan constant-time comparison, dan mengecek rate limit. Akan di-inject ke router di Task 4.

## 3. Tujuan Teknis
- Async dependency yang bisa di-inject via `Depends()`
- Validasi format `Bearer <token>`
- Constant-time comparison via `hmac.compare_digest` (cegah timing attack)
- Integrasi dengan `RateLimiter` dari Task 2
- Auto-disable jika `GATEWAY_TOKEN` kosong

## 4. Scope
### Yang dikerjakan
- `app/core/auth.py` — file baru

### Yang TIDAK dikerjakan
- Registrasi dependency ke router (Task 4)
- Exception handlers (Task 4)
- Response headers `X-RateLimit-*` (Task 4)

## 5. Langkah Implementasi

### Step 1: Buat file `app/core/auth.py`

```python
"""
Gateway authentication dependency.

Validates Bearer token from Authorization header and checks rate limit.
Auth is disabled when GATEWAY_TOKEN is empty (development mode).
"""

import hmac

from fastapi import Request
from loguru import logger

from app.config import settings
from app.core.exceptions import AuthenticationError, RateLimitExceededError
from app.services.rate_limiter import RateLimiter


# --- Module-level singletons (initialized once at import) ---
_token: str = settings.GATEWAY_TOKEN.strip()
_rate_limiter = RateLimiter(max_rpm=settings.RATE_LIMIT_RPM)


def get_rate_limiter() -> RateLimiter:
    """Access the global rate limiter instance (for response headers)."""
    return _rate_limiter


async def verify_gateway_token(request: Request) -> str | None:
    """
    FastAPI dependency — validate Bearer token + rate limit.

    Auth flow:
    1. GATEWAY_TOKEN empty? → skip auth (dev mode), return None
    2. Read Authorization header from request
    3. Validate "Bearer <token>" format
    4. Constant-time compare token with GATEWAY_TOKEN
    5. Check rate limit via RateLimiter
    6. Return validated token string

    Args:
        request: FastAPI Request object.

    Returns:
        Validated token string if auth active, None if auth disabled.

    Raises:
        AuthenticationError: Missing header, invalid format, or wrong token.
        RateLimitExceededError: Global rate limit exceeded.
    """
    # 1. Auth disabled — GATEWAY_TOKEN is empty
    if not _token:
        return None

    # 2. Read Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise AuthenticationError("Missing Authorization header")

    # 3. Parse "Bearer <token>" format
    parts = auth_header.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise AuthenticationError(
            "Invalid format, expected: Authorization: Bearer <token>"
        )

    incoming_token = parts[1].strip()
    if not incoming_token:
        raise AuthenticationError("Empty token")

    # 4. Constant-time comparison (prevent timing attack)
    if not hmac.compare_digest(_token, incoming_token):
        raise AuthenticationError("Invalid token")

    # 5. Rate limit check
    if not _rate_limiter.check():
        raise RateLimitExceededError(limit=_rate_limiter._max_rpm)

    return incoming_token
```

## 6. Output yang Diharapkan

**Token valid:**
```
Authorization: Bearer my-secret-token
→ function returns "my-secret-token"
```

**Token salah:**
```
Authorization: Bearer wrong-token
→ raises AuthenticationError("Invalid token")
```

**Header missing:**
```
(no Authorization header)
→ raises AuthenticationError("Missing Authorization header")
```

**Format salah:**
```
Authorization: Token abc123
→ raises AuthenticationError("Invalid format, expected: Authorization: Bearer <token>")
```

**Auth disabled:**
```
GATEWAY_TOKEN="" (di .env)
→ function returns None (tanpa cek apapun)
```

**Rate limited:**
```
(after exceeding RPM limit)
→ raises RateLimitExceededError(limit=120)
```

## 7. Dependencies
- Task 1 — `AuthenticationError` dan `RateLimitExceededError` harus sudah ada
- Task 2 — `RateLimiter` class harus sudah ada

## 8. Acceptance Criteria
- [ ] Token valid → return token string
- [ ] Token salah → `AuthenticationError` dengan detail "Invalid token"
- [ ] Header missing → `AuthenticationError` dengan detail "Missing Authorization header"
- [ ] Format bukan "Bearer xxx" → `AuthenticationError` dengan detail "Invalid format..."
- [ ] Token kosong "Bearer " → `AuthenticationError` dengan detail "Empty token"
- [ ] `GATEWAY_TOKEN=""` → return None tanpa cek header apapun
- [ ] Rate limit exceeded → `RateLimitExceededError` dengan limit yang benar
- [ ] Menggunakan `hmac.compare_digest()` untuk token comparison
- [ ] Token TIDAK pernah di-log (tidak ada `logger.info/debug` yang print token)
- [ ] `get_rate_limiter()` mengembalikan singleton `RateLimiter` instance

## 9. Estimasi
Medium (~30 menit)
