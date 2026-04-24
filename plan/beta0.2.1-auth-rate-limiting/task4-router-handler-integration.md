# Task 4 — Router & Exception Handler Integration

## 1. Judul Task
Integrasi auth dependency ke API router dan tambah exception handlers

## 2. Deskripsi
Menghubungkan `verify_gateway_token` ke `api_router` agar semua `/api/v1/*` terlindungi. Tambah exception handlers untuk 401 dan 429.

## 3. Tujuan Teknis
- Semua `/api/v1/*` butuh token valid
- `/health`, `/docs` tetap publik
- Error 401 → JSON + `WWW-Authenticate: Bearer`
- Error 429 → JSON + `Retry-After`
- Startup log menunjukkan status auth

## 4. Scope
### Yang dikerjakan
- `app/api/router.py` — inject `Depends(verify_gateway_token)`
- `app/main.py` — 2 exception handlers + startup log

### Yang TIDAK dikerjakan
- Response middleware untuk `X-RateLimit-Remaining` per-response

## 5. Langkah Implementasi

### Step 1: Update `app/api/router.py`
```python
from fastapi import APIRouter, Depends
from app.api.endpoints import models, generate, stream, embedding
from app.core.auth import verify_gateway_token

api_router = APIRouter(
    prefix="/api/v1",
    dependencies=[Depends(verify_gateway_token)],
)
# include_router calls tetap sama
```

### Step 2: Tambah handlers di `app/main.py`
Import `AuthenticationError`, `RateLimitExceededError`. Tambah SEBELUM handler `AllKeysExhaustedError`:

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
        headers={"Retry-After": str(exc.retry_after), "X-RateLimit-Limit": str(settings.RATE_LIMIT_RPM)},
    )
```

### Step 3: Startup log di `lifespan`
```python
if settings.GATEWAY_TOKEN:
    logger.info("Auth: enabled (token configured)")
else:
    logger.info("Auth: disabled (development mode)")
if settings.RATE_LIMIT_RPM > 0:
    logger.info("Rate limit: {rpm} req/min", rpm=settings.RATE_LIMIT_RPM)
else:
    logger.info("Rate limit: unlimited")
```

## 6. Output yang Diharapkan
- `POST /api/v1/generate` tanpa token → 401 `{"error": "...", "code": "AUTHENTICATION_FAILED"}`
- `POST /api/v1/generate` token valid → 200
- `GET /health` tanpa token → 200 (publik)
- Rate limit exceeded → 429 + `Retry-After` header

## 7. Dependencies
- Task 1, Task 2, Task 3

## 8. Acceptance Criteria
- [ ] Semua `/api/v1/*` endpoints → 401 tanpa token
- [ ] `/health` dan `/docs` → 200 tanpa token
- [ ] 401 response punya header `WWW-Authenticate: Bearer`
- [ ] 429 response punya header `Retry-After` dan `X-RateLimit-Limit`
- [ ] Startup log menunjukkan auth dan rate limit status

## 9. Estimasi
Medium (~30 menit)
