# Task 6 — FastAPI App Entry Point

> **Modul**: beta0.1.1 — Foundation Core  
> **Estimasi**: Medium (60–120 menit)  
> **Dependencies**: Task 2, Task 3, Task 4, Task 5 (semua task sebelumnya)

---

## 1. Judul Task

Implementasi `app/main.py` — FastAPI application entry point dengan startup/shutdown events, middleware registration, exception handlers, CORS, dan health check endpoint.

---

## 2. Deskripsi

Membuat file utama yang menyatukan semua komponen foundation: config, logging, exceptions, dan middleware. File ini adalah satu-satunya entry point yang di-run oleh uvicorn. Setelah task ini selesai, server bisa dijalankan dan menghasilkan response.

---

## 3. Tujuan Teknis

- FastAPI instance dengan metadata (title, version, description)
- Startup event: setup logging, log config summary
- Shutdown event: cleanup placeholder
- CORS middleware enabled (allow all origins untuk development)
- Request logging middleware registered
- Global exception handler untuk `AIGatewayError` → JSON response
- Health check endpoint: `GET /health`
- Server bisa dijalankan dengan `uvicorn app.main:app --reload`

---

## 4. Scope

### ✅ Yang Dikerjakan

- Implementasi `app/main.py`
- Health check endpoint (`GET /health`)
- Exception handler registration
- Middleware registration
- Startup/shutdown lifecycle events

### ❌ Yang Tidak Dikerjakan

- Business endpoints (/generate, /stream, etc.) — beta0.1.3+
- API router — beta0.1.2
- Provider initialization — beta0.1.3
- Service initialization — beta0.1.3

---

## 5. Langkah Implementasi

### Step 1: Buat `app/main.py`

```python
"""
AI Generative Core — FastAPI Application Entry Point.

This is the main file that ties together all foundation components:
configuration, logging, error handling, and middleware.

Run with: uvicorn app.main:app --reload --port 8000
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from app.config import settings
from app.core.exceptions import AIGatewayError
from app.core.logging import setup_logging
from app.core.middleware import RequestLoggingMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # === STARTUP ===
    setup_logging(
        log_level=settings.LOG_LEVEL,
        log_format=settings.LOG_FORMAT,
    )

    logger.info("=" * 50)
    logger.info(f"{settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info("=" * 50)
    logger.info(f"Debug mode: {settings.DEBUG}")
    logger.info(f"Ollama URL: {settings.OLLAMA_BASE_URL}")
    logger.info(
        f"Gemini API Key: {'configured' if settings.GEMINI_API_KEY else 'not set'}"
    )

    yield

    # === SHUTDOWN ===
    logger.info("Shutting down AI Generative Core...")


# --- Create FastAPI app ---
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Universal AI Gateway for SaaS applications. "
    "Supports multiple AI providers (Ollama, Gemini) "
    "with text generation, streaming, embedding, and multimodal capabilities.",
    lifespan=lifespan,
)


# --- Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)


# --- Exception Handlers ---
@app.exception_handler(AIGatewayError)
async def gateway_error_handler(request, exc: AIGatewayError):
    """
    Global handler for all AIGatewayError subclasses.
    Maps error codes to appropriate HTTP status codes.
    """
    status_map = {
        "PROVIDER_NOT_FOUND": 404,
        "MODEL_NOT_FOUND": 404,
        "CAPABILITY_NOT_SUPPORTED": 400,
        "PROVIDER_CONNECTION_ERROR": 502,
        "PROVIDER_TIMEOUT": 504,
        "PROVIDER_API_ERROR": 502,
    }

    status_code = status_map.get(exc.code, 500)

    logger.error(
        "Request failed: {code} — {message}",
        code=exc.code,
        message=exc.message,
    )

    return JSONResponse(
        status_code=status_code,
        content={
            "error": exc.message,
            "code": exc.code,
        },
    )


# --- Health Check ---
@app.get(
    "/health",
    tags=["System"],
    summary="Health check",
    description="Returns server status and version.",
)
async def health_check():
    """Check if the server is running and healthy."""
    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "app_name": settings.APP_NAME,
    }
```

### Step 2: Jalankan server

```bash
uvicorn app.main:app --reload --port 8000
```

Output yang diharapkan di console:

```
2026-04-22 22:30:00 | INFO | Logging initialized
2026-04-22 22:30:00 | INFO | ==================================================
2026-04-22 22:30:00 | INFO | AI Generative Core v0.1.1
2026-04-22 22:30:00 | INFO | ==================================================
2026-04-22 22:30:00 | INFO | Debug mode: True
2026-04-22 22:30:00 | INFO | Ollama URL: http://localhost:11434
2026-04-22 22:30:00 | INFO | Gemini API Key: not set
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

### Step 3: Test health check

```bash
curl http://localhost:8000/health
```

Response:

```json
{
    "status": "ok",
    "version": "0.1.1",
    "app_name": "AI Generative Core"
}
```

### Step 4: Test Swagger UI

Buka browser: `http://localhost:8000/docs`

Harus menampilkan:
- Title: "AI Generative Core"
- Version: "0.1.1"
- Endpoint: `GET /health`

### Step 5: Test exception handler

Untuk memvalidasi exception handler bekerja, tambahkan temporary test endpoint (hapus setelah validasi):

```bash
# Tidak perlu menambah kode — validasi akan dilakukan di beta0.1.3
# ketika endpoint pertama dibuat dan exceptions ter-trigger.
# Untuk sekarang, cukup pastikan import dan registration berhasil.
```

### Step 6: Test request logging

Panggil beberapa endpoint dan cek log:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/docs
curl http://localhost:8000/nonexistent
```

Console harus menampilkan log untuk setiap request:

```
2026-04-22 22:30:01 | INFO | Request completed: GET /health → 200 (1.2ms)
2026-04-22 22:30:02 | INFO | Request completed: GET /docs → 200 (5.3ms)
2026-04-22 22:30:03 | INFO | Request completed: GET /nonexistent → 404 (0.8ms)
```

---

## 6. Output yang Diharapkan

### File: `app/main.py`

Isi seperti Step 1 di atas.

### Server Behavior

| URL | Method | Response |
|---|---|---|
| `/health` | GET | `{"status": "ok", "version": "0.1.1", ...}` |
| `/docs` | GET | Swagger UI HTML page |
| `/openapi.json` | GET | OpenAPI schema JSON |
| `/nonexistent` | GET | `{"detail": "Not Found"}` (FastAPI default 404) |

### Log Output

Setiap request dicatat. Startup menampilkan config summary.

---

## 7. Dependencies

- **Task 2** — `app/config.py` (`settings` import)
- **Task 3** — `app/core/exceptions.py` (`AIGatewayError` import)
- **Task 4** — `app/core/logging.py` (`setup_logging` import)
- **Task 5** — `app/core/middleware.py` (`RequestLoggingMiddleware` import)

---

## 8. Acceptance Criteria

- [ ] `uvicorn app.main:app --reload` berjalan tanpa error
- [ ] Startup log menampilkan app name, version, config summary
- [ ] `GET /health` → `200` dengan `{"status": "ok", "version": "0.1.1", ...}`
- [ ] `GET /docs` → Swagger UI tampil dengan benar
- [ ] Setiap request tercatat di log (method, path, status, duration)
- [ ] CORS headers ada di response (Access-Control-Allow-Origin: *)
- [ ] Exception handler ter-register (tidak error saat import)
- [ ] Shutdown log muncul saat CTRL+C

---

## 9. Estimasi

**Medium** — Menyatukan semua komponen, perlu teliti di lifecycle dan middleware ordering.
