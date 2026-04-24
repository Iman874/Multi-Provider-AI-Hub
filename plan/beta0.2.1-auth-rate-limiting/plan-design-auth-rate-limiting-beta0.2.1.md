# Blueprint: AI Generative Core — Auth & Rate Limiting (beta0.2.1)

## 1. Visi & Tujuan

Saat ini, AI Gateway sepenuhnya terbuka — siapa pun yang mengetahui URL server bisa mengakses semua endpoint tanpa autentikasi. Ini menciptakan risiko serius:

1. **Penyalahgunaan Kuota**: Pihak luar bisa menembak endpoint dan menguras Gemini API Key / GPU Ollama
2. **Tidak Ada Identitas**: Gateway tidak tahu siapa yang melakukan request, sehingga tidak bisa membatasi penggunaan
3. **Tidak Siap SaaS**: Backend SaaS butuh minimal Service-to-Service auth agar aman

Modul **beta0.2.1** membangun **Single Token Authentication** dan **Rate Limiting**:
- Satu **static token** disimpan di `.env` sebagai `GATEWAY_TOKEN`
- Frontend/consumer wajib mengirim `Authorization: Bearer <token>` di setiap request ke `/api/v1/*`
- Request tanpa/salah token → **401 Unauthorized**
- Rate limiting global → **429 Too Many Requests** jika melebihi batas per menit
- `/health`, `/docs`, `/openapi.json` tetap **publik** tanpa auth
- Jika `GATEWAY_TOKEN` kosong → auth **dinonaktifkan** (development mode, backward compatible)

---

## 2. Scope Development

### ✅ Yang Dikerjakan
- **Single Token Auth**: FastAPI dependency yang memvalidasi `Authorization: Bearer <token>`
- **Config Update**: `GATEWAY_TOKEN` dan `RATE_LIMIT_RPM` di `.env`
- **Rate Limiter Service**: In-memory sliding window counter (global, bukan per-user)
- **Exception Baru**: `AuthenticationError` (401), `RateLimitExceededError` (429)
- **Response Headers**: `X-RateLimit-Limit`, `X-RateLimit-Remaining`
- **Unit Tests**: Auth dependency + rate limiter + integration test

### ❌ Yang Tidak Dikerjakan
- Multi-token / multi-user (cukup 1 token untuk Service-to-Service)
- JWT token issuance / refresh
- User login/register
- Database token storage
- Per-endpoint rate limiting (global saja)
- Per-user rate limiting (tidak ada multi-user)

---

## 3. Arsitektur & Desain

### 3.1. Konfigurasi (`.env`)

```env
# --- Gateway Auth ---
# Static service token. Frontend harus kirim: Authorization: Bearer <token>
# Kosongkan untuk disable auth (development mode)
GATEWAY_TOKEN=my-secret-gateway-token-2026

# Rate limit: max requests per minute (0 = unlimited)
RATE_LIMIT_RPM=120
```

**Aturan Loading**:
1. `GATEWAY_TOKEN` ada dan tidak kosong → auth **aktif**, semua `/api/v1/*` wajib token
2. `GATEWAY_TOKEN` kosong / `""` → auth **dinonaktifkan** (backward compatible, development mode)
3. `RATE_LIMIT_RPM=0` → rate limiting dinonaktifkan
4. `RATE_LIMIT_RPM=120` → max 120 request/menit secara global

### 3.2. Config Update (`app/config.py`)

Tambah 2 field baru di class `Settings`:

```python
# --- Gateway Auth ---
GATEWAY_TOKEN: str = ""       # Static token, kosong = auth disabled
RATE_LIMIT_RPM: int = 120     # 0 = unlimited
```

Tidak ada perubahan pada field existing. Update `APP_VERSION` ke `"0.2.1"`.

### 3.3. Exception Baru (`app/core/exceptions.py`)

Dua exception baru ditambahkan ke hierarchy:

```python
class AuthenticationError(AIGatewayError):
    """Request tanpa token atau token salah."""
    def __init__(self, detail: str = ""):
        msg = "Authentication failed"
        if detail:
            msg += f": {detail}"
        super().__init__(message=msg, code="AUTHENTICATION_FAILED")
        # HTTP 401 Unauthorized


class RateLimitExceededError(AIGatewayError):
    """Request melebihi batas rate limit per menit."""
    def __init__(self, limit: int, retry_after: int = 60):
        self.retry_after = retry_after
        super().__init__(
            message=f"Rate limit exceeded: max {limit} requests/minute",
            code="RATE_LIMIT_EXCEEDED",
        )
        # HTTP 429 Too Many Requests
```

### 3.4. Rate Limiter Service (`app/services/rate_limiter.py`)

**Algoritma: Sliding Window Counter** menggunakan `collections.deque`.

```
┌──────────────────────────────────────────────────┐
│               RateLimiter                        │
├──────────────────────────────────────────────────┤
│ _max_rpm: int                 # Max req/min      │
│ _enabled: bool                # Active?          │
│ _timestamps: deque[float]     # Request timestamps│
│ _lock: threading.Lock         # Thread safety    │
├──────────────────────────────────────────────────┤
│ check() → bool                # Apakah boleh?    │
│ get_remaining() → int         # Sisa kuota       │
│ is_enabled → bool             # Rate limit aktif? │
│ reset()                       # Clear window     │
└──────────────────────────────────────────────────┘
```

**Pseudocode `check()`**:
```
def check() -> bool:
    if not _enabled:
        return True

    now = time.time()
    with _lock:
        # 1. Buang timestamp yang > 60 detik lalu
        while _timestamps and _timestamps[0] < now - 60:
            _timestamps.popleft()

        # 2. Cek apakah masih di bawah limit
        if len(_timestamps) >= _max_rpm:
            return False  # Rate limited

        # 3. Catat request ini
        _timestamps.append(now)
        return True
```

**Pseudocode `get_remaining()`**:
```
def get_remaining() -> int:
    if not _enabled:
        return -1  # Unlimited

    now = time.time()
    with _lock:
        # Buang expired
        while _timestamps and _timestamps[0] < now - 60:
            _timestamps.popleft()
        return max(0, _max_rpm - len(_timestamps))
```

### 3.5. Auth Dependency (`app/core/auth.py`)

Auth diimplementasi sebagai **FastAPI Dependency** (bukan Starlette middleware), sehingga bisa di-inject selektif ke router tertentu saja. Endpoint publik (`/health`, `/docs`) tidak terkena auth.

```python
# app/core/auth.py

from fastapi import Request
from app.config import settings
from app.core.exceptions import AuthenticationError, RateLimitExceededError

# Singleton instances (diinisialisasi saat import)
_token: str = settings.GATEWAY_TOKEN.strip()
_rate_limiter: RateLimiter = RateLimiter(max_rpm=settings.RATE_LIMIT_RPM)

async def verify_gateway_token(request: Request) -> str | None:
    """
    FastAPI dependency — validasi token dan rate limit.

    Returns:
        Token string jika auth aktif, None jika auth disabled.

    Flow:
    1. Auth disabled (token kosong)? → SKIP, return None
    2. Baca Authorization header
    3. Parse format "Bearer <token>"
    4. Cocokkan dengan GATEWAY_TOKEN
    5. Cek rate limit
    6. Return token
    """
    # 1. Auth disabled
    if not _token:
        return None

    # 2. Baca header
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise AuthenticationError("Missing Authorization header")

    # 3. Parse "Bearer xxx"
    parts = auth_header.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise AuthenticationError("Invalid format, expected: Bearer <token>")

    incoming_token = parts[1].strip()

    # 4. Validasi token
    if incoming_token != _token:
        raise AuthenticationError("Invalid token")

    # 5. Rate limit check
    if not _rate_limiter.check():
        raise RateLimitExceededError(limit=_rate_limiter._max_rpm)

    return incoming_token
```

### 3.6. Router Integration

Dependency di-inject ke `api_router` sehingga semua endpoint di bawah `/api/v1/*` terlindungi:

```python
# app/api/router.py
from app.core.auth import verify_gateway_token

api_router = APIRouter(
    prefix="/api/v1",
    dependencies=[Depends(verify_gateway_token)],  # ← Auth untuk SEMUA endpoint
)
```

Endpoint yang tetap **publik** (di luar `api_router`):
- `GET /health` — health check
- `GET /docs` — Swagger UI
- `GET /openapi.json` — OpenAPI spec

### 3.7. Exception Handlers (`app/main.py`)

Dua handler baru ditambahkan:

```python
@app.exception_handler(AuthenticationError)
async def auth_error_handler(request: Request, exc: AuthenticationError):
    return JSONResponse(
        status_code=401,
        content={"error": exc.message, "code": exc.code},
        headers={"WWW-Authenticate": "Bearer"},
    )

@app.exception_handler(RateLimitExceededError)
async def rate_limit_handler(request: Request, exc: RateLimitExceededError):
    return JSONResponse(
        status_code=429,
        content={"error": exc.message, "code": exc.code},
        headers={
            "Retry-After": str(exc.retry_after),
            "X-RateLimit-Limit": str(settings.RATE_LIMIT_RPM),
        },
    )
```

### 3.8. Response Headers

Setiap response yang melewati auth akan menyertakan info rate limit. Ini diimplementasikan sebagai **middleware kecil** di `app/core/auth.py`:

```
X-RateLimit-Limit: 120         # Max RPM yang dikonfigurasi
X-RateLimit-Remaining: 87      # Sisa request di window 60 detik ini
```

### 3.9. Request Flow Diagram

```
Client Request
  │  Authorization: Bearer my-secret-gateway-token-2026
  ▼
┌──────────────────────────────────────────────────────────┐
│ verify_gateway_token() — FastAPI Dependency              │
│                                                          │
│ 1. Path di luar /api/v1? → SKIP (publik)                │
│ 2. GATEWAY_TOKEN kosong? → SKIP (dev mode, return None)  │
│ 3. Header Authorization ada?                             │
│    └── Tidak ada → 401 "Missing Authorization header"    │
│ 4. Format "Bearer <token>"?                              │
│    └── Salah → 401 "Invalid format"                      │
│ 5. Token cocok dengan GATEWAY_TOKEN?                     │
│    └── Tidak → 401 "Invalid token"                       │
│ 6. Rate limit check (sliding window)                     │
│    └── Exceeded → 429 "Rate limit exceeded"              │
│ 7. PASS → lanjut ke endpoint handler                     │
└──────────────────────────────────────────────────────────┘
  │
  ▼
Router → GeneratorService → Provider → Response
  │
  ▼
Response + X-RateLimit-Limit + X-RateLimit-Remaining headers
```

### 3.10. Security Considerations

1. **Token di log**: Token TIDAK BOLEH muncul di log. `RequestLoggingMiddleware` tidak log header `Authorization`.
2. **Timing attack**: Gunakan `hmac.compare_digest()` untuk perbandingan token (constant-time comparison).
3. **CORS**: Header `Authorization` sudah di-allow oleh CORS middleware (`allow_headers=["*"]`).
4. **HTTPS**: Untuk production, WAJIB gunakan HTTPS agar token tidak bocor di transit. Ini tanggung jawab reverse proxy (Nginx/Caddy), bukan Gateway.

---

## 4. Breakdowns (Daftar Task)

### Task 1 — Config & Exception Update

**File yang diubah**: `app/config.py`, `app/core/exceptions.py`, `.env`, `.env.example`

**Langkah spesifik:**
1. Tambah di `Settings`:
   - `GATEWAY_TOKEN: str = ""`
   - `RATE_LIMIT_RPM: int = 120`
2. Update `APP_VERSION` → `"0.2.1"`
3. Tambah `AuthenticationError` di `exceptions.py`:
   - `__init__(self, detail: str = "")`
   - `code = "AUTHENTICATION_FAILED"`
4. Tambah `RateLimitExceededError` di `exceptions.py`:
   - `__init__(self, limit: int, retry_after: int = 60)`
   - `self.retry_after = retry_after`
   - `code = "RATE_LIMIT_EXCEEDED"`
5. Update `.env`:
   - Tambah `GATEWAY_TOKEN=` (kosong default)
   - Tambah `RATE_LIMIT_RPM=120`
6. Update `.env.example` dengan dokumentasi

**Acceptance Criteria:**
- `settings.GATEWAY_TOKEN` bisa diakses
- `settings.RATE_LIMIT_RPM` bisa diakses
- Kedua exception bisa di-raise dan di-catch
- `RateLimitExceededError` punya atribut `retry_after`
- Backward compatible: kosong = auth disabled

**Estimasi:** Low (20 menit)

---

### Task 2 — Rate Limiter Service

**File yang dibuat**: `app/services/rate_limiter.py`

**Langkah spesifik:**
1. Buat class `RateLimiter`:
   - `__init__(self, max_rpm: int)` — 0 = unlimited
   - `self._timestamps: deque[float]` — sliding window
   - `self._lock: threading.Lock` — thread safety
   - `self._enabled: bool = max_rpm > 0`
2. Method `check() → bool`:
   - Jika disabled → return True
   - Acquire lock
   - Buang timestamp > 60 detik lalu (`popleft`)
   - Jika `len >= max_rpm` → return False
   - Append `time.time()` → return True
3. Method `get_remaining() → int`:
   - Jika disabled → return -1 (unlimited)
   - Acquire lock, buang expired, return `max(0, max_rpm - len)`
4. Property `is_enabled → bool`
5. Method `reset()` — clear deque (untuk testing)
6. Log warning saat rate limit hit pertama kali

**Acceptance Criteria:**
- `RateLimiter(120)` → 120 request/menit diizinkan, ke-121 ditolak
- `RateLimiter(0)` → unlimited (selalu True)
- Window bergeser: request lama (>60s) otomatis di-expire
- `get_remaining()` akurat setelah beberapa request
- `reset()` mengosongkan window
- Thread-safe: concurrent calls tidak crash

**Estimasi:** Medium (30 menit)

---

### Task 3 — Auth Dependency

**File yang dibuat**: `app/core/auth.py`

**Langkah spesifik:**
1. Import dan baca `settings.GATEWAY_TOKEN` di module level
2. Instantiate `RateLimiter(settings.RATE_LIMIT_RPM)` di module level
3. Buat async function `verify_gateway_token(request: Request) → str | None`:
   - Step 1: Cek `_token` kosong → return None (disabled)
   - Step 2: Baca `request.headers.get("Authorization")`
   - Step 3: Split `"Bearer xxx"` → extract token
   - Step 4: Compare dengan `hmac.compare_digest(_token, incoming)` (constant-time)
   - Step 5: Panggil `_rate_limiter.check()` → jika False, raise `RateLimitExceededError`
   - Step 6: Return token string
4. Buat helper function `get_rate_limiter() → RateLimiter` (untuk response headers)
5. Token TIDAK BOLEH di-log (mask jika perlu)

**Acceptance Criteria:**
- Token valid → function returns token string
- Token salah → `AuthenticationError("Invalid token")`
- Header missing → `AuthenticationError("Missing Authorization header")`
- Format salah (bukan "Bearer xxx") → `AuthenticationError("Invalid format")`
- Auth disabled → function returns None tanpa cek apapun
- Rate limit exceeded → `RateLimitExceededError`
- Constant-time comparison untuk cegah timing attack

**Estimasi:** Medium (30 menit)

---

### Task 4 — Router & Exception Handler Integration

**File yang diubah**: `app/api/router.py`, `app/main.py`

**Langkah spesifik:**
1. Update `app/api/router.py`:
   - Import `verify_gateway_token` dari `app.core.auth`
   - Tambahkan `dependencies=[Depends(verify_gateway_token)]` ke `api_router`
2. Update `app/main.py` — exception handlers:
   - `AuthenticationError` → 401 + `WWW-Authenticate: Bearer` header
   - `RateLimitExceededError` → 429 + `Retry-After` + `X-RateLimit-Limit` headers
3. Update `app/main.py` — tambahkan import `AuthenticationError`, `RateLimitExceededError`
4. Update `app/main.py` — startup log:
   - Log `"Auth: enabled"` atau `"Auth: disabled (dev mode)"` saat startup
   - Log `"Rate limit: {rpm} req/min"` atau `"Rate limit: unlimited"`
5. Endpoint publik yang TIDAK terkena auth:
   - `GET /health` — sudah di luar `api_router`
   - `GET /docs` — FastAPI built-in
   - `GET /openapi.json` — FastAPI built-in

**Acceptance Criteria:**
- `POST /api/v1/generate` tanpa token → 401 dengan body `{"error": "...", "code": "AUTHENTICATION_FAILED"}`
- `POST /api/v1/generate` dengan token valid → 200 (normal flow)
- `POST /api/v1/generate` dengan token salah → 401
- `GET /health` tanpa token → 200 (publik)
- `GET /docs` tanpa token → 200 (publik)
- Melebihi RPM → 429 dengan `Retry-After` header
- Startup log menunjukkan status auth dan rate limit

**Estimasi:** Medium (30 menit)

---

### Task 5 — Unit Tests

**File yang dibuat**: `tests/core/test_auth.py`, `tests/services/test_rate_limiter.py`

**Langkah spesifik:**

**`tests/services/test_rate_limiter.py`** (8 tests):
1. `test_within_limit` — 5 RPM, 5 requests → semua True
2. `test_exceed_limit` — 5 RPM, 6 requests → terakhir False
3. `test_window_expiry` — request kadaluarsa setelah 60 detik (mock `time.time`)
4. `test_unlimited` — RPM 0 → selalu True
5. `test_remaining_count` — `get_remaining()` berkurang setiap request
6. `test_remaining_unlimited` — RPM 0 → remaining = -1
7. `test_reset` — `reset()` mengosongkan window
8. `test_is_enabled` — RPM > 0 → True, RPM 0 → False

**`tests/core/test_auth.py`** (8 tests):
1. `test_valid_token` — header benar → pass (return token)
2. `test_invalid_token` — token salah → 401
3. `test_missing_header` — tanpa Authorization → 401
4. `test_malformed_header_no_bearer` — "Token xxx" bukan "Bearer xxx" → 401
5. `test_malformed_header_empty` — "Bearer " (kosong) → 401
6. `test_auth_disabled` — `GATEWAY_TOKEN=""` → pass tanpa token
7. `test_rate_limit_exceeded` — mock rate limiter → 429
8. `test_public_endpoints` — `/health` dan `/docs` tanpa auth → 200

**Acceptance Criteria:**
- 16 test baru total
- Semua existing 52 tests tetap PASS (zero-regression)
- Mock `time.time()` untuk window expiry test
- Mock `settings.GATEWAY_TOKEN` untuk auth disabled test

**Estimasi:** Medium (60 menit)

---

## 5. Timeline & Estimasi Total

| Task | Scope | Estimasi |
|---|---|---|
| Task 1 | Config & Exception Update | 20 menit |
| Task 2 | Rate Limiter Service | 30 menit |
| Task 3 | Auth Dependency | 30 menit |
| Task 4 | Router & Handler Integration | 30 menit |
| Task 5 | Unit Tests | 60 menit |
| **Total** | | **~2.8 jam** |

---

## 6. Acceptance Criteria Global

- [ ] Semua endpoint `/api/v1/*` terlindungi oleh single static token
- [ ] `/health`, `/docs`, `/openapi.json` tetap publik
- [ ] Request tanpa token → 401 `AUTHENTICATION_FAILED`
- [ ] Request dengan token salah → 401 `AUTHENTICATION_FAILED`
- [ ] Response 401 menyertakan header `WWW-Authenticate: Bearer`
- [ ] Rate limiting sliding window berfungsi (global)
- [ ] Melebihi rate limit → 429 `RATE_LIMIT_EXCEEDED` + `Retry-After` header
- [ ] Response menyertakan `X-RateLimit-Limit` dan `X-RateLimit-Remaining`
- [ ] `GATEWAY_TOKEN=""` → auth disabled (backward compatible)
- [ ] `RATE_LIMIT_RPM=0` → unlimited
- [ ] Token TIDAK pernah muncul di log
- [ ] Token comparison menggunakan constant-time (`hmac.compare_digest`)
- [ ] Startup log menunjukkan status auth dan rate limit
- [ ] Semua 52 existing tests tetap PASS
- [ ] 16 test baru ditambahkan (8 rate limiter + 8 auth)
