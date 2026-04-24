# Task 7 — Integrate with main.py

> **Modul**: beta0.1.2 — Schema & Model Registry  
> **Estimasi**: Low (30–45 menit)  
> **Dependencies**: Task 5 (Dependency Injection), Task 6 (Models Endpoint & Router)

---

## 1. Judul Task

Update `app/main.py` — Integrate API router dan service initialization ke FastAPI lifespan.

---

## 2. Deskripsi

Menghubungkan semua komponen beta0.1.2 ke entry point yang sudah ada dari beta0.1.1. Dua perubahan utama:

1. Panggil `initialize_services()` di startup event
2. Include `api_router` di FastAPI app

Setelah task ini, server bisa dijalankan dan `GET /api/v1/models` berfungsi.

---

## 3. Tujuan Teknis

- `initialize_services(settings)` dipanggil saat startup (setelah logging setup)
- `api_router` di-include ke FastAPI app
- Startup log menampilkan jumlah model terdaftar
- `GET /api/v1/models` accessible dan return data
- Health check (`GET /health`) tetap berfungsi

---

## 4. Scope

### ✅ Yang Dikerjakan

- Update `app/main.py`:
  - Import `api_router` dan `initialize_services`
  - Panggil `initialize_services()` di lifespan startup
  - `app.include_router(api_router)`

### ❌ Yang Tidak Dikerjakan

- Provider initialization → beta0.1.3
- New endpoints → beta0.1.3+
- Mengubah exception handlers atau middleware (tetap sama)

---

## 5. Langkah Implementasi

### Step 1: Update `app/main.py`

Ubah file `app/main.py` yang sudah ada (dari beta0.1.1 task 6) dengan menambahkan 2 hal:

**Tambahkan import:**

```python
from app.api.dependencies import initialize_services
from app.api.router import api_router
```

**Update lifespan function — tambahkan setelah config summary log:**

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
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

    # >>> NEW: Initialize services <<<
    initialize_services(settings)

    yield

    # === SHUTDOWN ===
    logger.info("Shutting down AI Generative Core...")
```

**Include router — tambahkan setelah middleware section:**

```python
# --- API Router ---
app.include_router(api_router)
```

### Step 2: File lengkap `app/main.py` setelah update

```python
"""
AI Generative Core — FastAPI Application Entry Point.

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
from app.api.dependencies import initialize_services
from app.api.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
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

    # Initialize services (model registry, etc.)
    initialize_services(settings)

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

# --- API Router ---
app.include_router(api_router)


# --- Exception Handlers ---
@app.exception_handler(AIGatewayError)
async def gateway_error_handler(request, exc: AIGatewayError):
    """Global handler for all AIGatewayError subclasses."""
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

### Step 3: Jalankan server

```bash
uvicorn app.main:app --reload --port 8000
```

Startup log sekarang harus menampilkan:

```
... | INFO | ==================================================
... | INFO | AI Generative Core v0.1.1
... | INFO | ==================================================
... | INFO | Debug mode: True
... | INFO | Ollama URL: http://localhost:11434
... | INFO | Gemini API Key: not set
... | INFO | Registered 6 default models
... | INFO | Services initialized: 6 models registered
```

### Step 4: Test endpoints

```bash
# Health check (tetap berfungsi)
curl http://localhost:8000/health

# List all models (NEW)
curl http://localhost:8000/api/v1/models

# Filter by provider (NEW)
curl http://localhost:8000/api/v1/models?provider=ollama
```

### Step 5: Verify Swagger UI

Buka `http://localhost:8000/docs`:

- Harus ada section "System" dengan `GET /health`
- Harus ada section "Models" dengan `GET /api/v1/models`
- `GET /api/v1/models` harus menampilkan query parameter `provider`
- Response schema harus menampilkan `ModelInfo` object

---

## 6. Output yang Diharapkan

### Perubahan pada `app/main.py`

| Baris | Perubahan |
|---|---|
| Import section | +2 imports: `initialize_services`, `api_router` |
| Lifespan startup | +1 call: `initialize_services(settings)` |
| After middleware | +1 line: `app.include_router(api_router)` |

### Endpoint Summary

| Method | Path | Status |
|---|---|---|
| GET | `/health` | ✅ Existing (beta0.1.1) |
| GET | `/api/v1/models` | ✅ NEW |

---

## 7. Dependencies

- **Task 5** — `initialize_services` dari `app/api/dependencies.py`
- **Task 6** — `api_router` dari `app/api/router.py`
- **beta0.1.1 Task 6** — existing `app/main.py`

---

## 8. Acceptance Criteria

- [ ] `uvicorn app.main:app --reload` berjalan tanpa error
- [ ] Startup log menampilkan "Services initialized: 6 models registered"
- [ ] `GET /health` tetap return `{"status": "ok", ...}`
- [ ] `GET /api/v1/models` return JSON array dengan 6 models
- [ ] `GET /api/v1/models?provider=gemini` return 3 models
- [ ] Swagger UI menampilkan kedua sections: System + Models
- [ ] Request logging masih berfungsi (log setiap request)

---

## 9. Estimasi

**Low** — Hanya 3 perubahan kecil di file existing.
