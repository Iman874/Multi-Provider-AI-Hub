# Task 5 — Request Logging Middleware

> **Modul**: beta0.1.1 — Foundation Core  
> **Estimasi**: Medium (45–90 menit)  
> **Dependencies**: Task 4 (Logging System)

---

## 1. Judul Task

Implementasi `app/core/middleware.py` — ASGI middleware yang mencatat setiap HTTP request dan response ke log.

---

## 2. Deskripsi

Membuat middleware yang otomatis mencatat informasi setiap request masuk: HTTP method, path, status code, dan durasi (dalam ms). Middleware ini berjalan untuk **setiap request** tanpa harus menambahkan kode di setiap endpoint.

---

## 3. Tujuan Teknis

- Class middleware yang compatible dengan Starlette/FastAPI
- Log setiap request completion dengan: method, path, status_code, duration_ms
- Menggunakan loguru (bukan standard logging)
- Tidak memblokir atau mengubah request/response
- Performance overhead minimal

---

## 4. Scope

### ✅ Yang Dikerjakan

- Implementasi `app/core/middleware.py`
- Class `RequestLoggingMiddleware` (BaseHTTPMiddleware)
- Log request info saat response selesai

### ❌ Yang Tidak Dikerjakan

- Request body logging (privacy concern + performance)
- Response body logging
- Rate limiting
- Authentication middleware

---

## 5. Langkah Implementasi

### Step 1: Buat `app/core/middleware.py`

```python
"""
Request logging middleware for AI Generative Core.

Automatically logs every HTTP request with method, path, status code,
and duration in milliseconds. Integrates with loguru.
"""

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from loguru import logger


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs every incoming HTTP request.

    Logs:
    - HTTP method (GET, POST, etc.)
    - Request path (/api/v1/generate, etc.)
    - Response status code (200, 404, 500, etc.)
    - Request duration in milliseconds
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.perf_counter()

        # Process the request
        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Log the request
        logger.info(
            "Request completed: {method} {path} → {status} ({duration:.1f}ms)",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration=duration_ms,
        )

        return response
```

### Step 2: Verifikasi (akan ditest bersama task 6)

Middleware tidak bisa ditest standalone — perlu FastAPI app. Verifikasi akan dilakukan di task 6 saat `main.py` dibuat. Namun pastikan:

```bash
python -c "from app.core.middleware import RequestLoggingMiddleware; print('OK')"
```

Output: `OK`

---

## 6. Output yang Diharapkan

### File: `app/core/middleware.py`

Isi seperti Step 1 di atas.

### Log Output (setelah terintegrasi di task 6)

Setiap request akan menghasilkan log entry seperti:

**Text format:**
```
2026-04-22 22:30:00 | INFO     | app.core.middleware:dispatch:42 | Request completed: GET /health → 200 (1.2ms)
```

**JSON format:**
```json
{
  "text": "Request completed: GET /health → 200 (1.2ms)",
  "record": {
    "level": {"name": "INFO"},
    "extra": {
      "method": "GET",
      "path": "/health",
      "status": 200,
      "duration": 1.234
    }
  }
}
```

---

## 7. Dependencies

- **Task 4** — loguru harus sudah di-setup
- **Package**: `starlette` (sudah termasuk di FastAPI)

---

## 8. Acceptance Criteria

- [ ] File `app/core/middleware.py` ada
- [ ] `RequestLoggingMiddleware` bisa di-import tanpa error
- [ ] Class inherit dari `BaseHTTPMiddleware`
- [ ] Method `dispatch()` mencatat: method, path, status_code, duration_ms
- [ ] Menggunakan `loguru.logger` (bukan `logging`)
- [ ] Duration dihitung dalam milliseconds
- [ ] Tidak mengubah request atau response (pass-through)

---

## 9. Estimasi

**Medium** — Perlu memahami Starlette middleware pattern, tapi implementasinya tidak kompleks.
