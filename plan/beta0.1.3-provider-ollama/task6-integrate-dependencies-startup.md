# Task 6 — Update Dependencies, Router & Startup

> **Modul**: beta0.1.3 — Provider Abstraction & Ollama  
> **Estimasi**: Medium (60–90 menit)  
> **Dependencies**: Task 2–5 (semua task sebelumnya)

---

## 1. Judul Task

Update `app/api/dependencies.py`, `app/api/router.py`, dan `app/main.py` untuk mengintegrasikan provider, generator service, dan generate endpoint ke running server.

---

## 2. Deskripsi

Task terakhir yang menghubungkan semua komponen beta0.1.3 ke server yang sudah berjalan. Setelah task ini selesai, `POST /api/v1/generate` bisa dipanggil dan menghasilkan AI output dari Ollama.

3 file yang perlu diupdate:
1. `dependencies.py` — tambah provider init + generator service
2. `router.py` — tambah generate endpoint
3. `main.py` — tambah provider cleanup di shutdown

---

## 3. Tujuan Teknis

- `initialize_services()` membuat OllamaProvider, GeneratorService, dan register ke DI
- `get_generator_service()` Depends function tersedia
- `api_router` include generate endpoint
- Startup: log active providers, test Ollama connectivity
- Shutdown: close all provider HTTP clients

---

## 4. Scope

### ✅ Yang Dikerjakan

- Update `app/api/dependencies.py`
- Update `app/api/router.py`
- Update `app/main.py`

### ❌ Yang Tidak Dikerjakan

- New files (semua file baru sudah di task 1–5)
- GeminiProvider initialization → beta0.1.4

---

## 5. Langkah Implementasi

### Step 1: Update `app/api/dependencies.py`

Replace isi file yang ada dengan versi lengkap:

```python
"""
FastAPI dependency injection setup.

Provides singleton service instances to endpoints via Depends().
Services are initialized once during application startup.
"""

from loguru import logger

from app.config import Settings
from app.providers import create_provider
from app.providers.base import BaseProvider
from app.services.generator import GeneratorService
from app.services.model_registry import ModelRegistry


# --- Singleton instances ---
_model_registry: ModelRegistry | None = None
_generator_service: GeneratorService | None = None
_providers: dict[str, BaseProvider] = {}


def get_model_registry() -> ModelRegistry:
    """FastAPI dependency: provides ModelRegistry instance."""
    if _model_registry is None:
        raise RuntimeError("ModelRegistry not initialized. Call initialize_services() first.")
    return _model_registry


def get_generator_service() -> GeneratorService:
    """FastAPI dependency: provides GeneratorService instance."""
    if _generator_service is None:
        raise RuntimeError("GeneratorService not initialized. Call initialize_services() first.")
    return _generator_service


def get_providers() -> dict[str, BaseProvider]:
    """Get all active provider instances (for shutdown cleanup)."""
    return _providers


def initialize_services(settings: Settings) -> None:
    """
    Initialize all service singletons.

    Called once during application startup. Creates:
    1. AI Providers (Ollama, and Gemini when available)
    2. Model Registry with default models
    3. Generator Service that orchestrates providers

    Args:
        settings: Application settings instance.
    """
    global _model_registry, _generator_service, _providers

    # --- 1. Create providers ---
    provider_names = ["ollama", "gemini"]
    for name in provider_names:
        provider = create_provider(name, settings)
        if provider is not None:
            _providers[name] = provider

    logger.info(
        "Active providers: {providers}",
        providers=list(_providers.keys()),
    )

    # --- 2. Create Model Registry ---
    _model_registry = ModelRegistry()
    _model_registry.register_defaults()

    model_count = len(_model_registry.list_models())
    logger.info(
        "Model registry: {count} models registered",
        count=model_count,
    )

    # --- 3. Create Generator Service ---
    _generator_service = GeneratorService(
        providers=_providers,
        registry=_model_registry,
    )
```

### Step 2: Update `app/api/router.py`

```python
"""
Central API router that combines all endpoint routers.
"""

from fastapi import APIRouter

from app.api.endpoints import models, generate

api_router = APIRouter(prefix="/api/v1")

# --- Register endpoint routers ---
api_router.include_router(models.router, tags=["Models"])
api_router.include_router(generate.router, tags=["Generation"])
```

### Step 3: Update `app/main.py`

Perubahan pada `main.py`:

1. **Import** `get_providers` dari dependencies
2. **Startup**: tambah Ollama connectivity check
3. **Shutdown**: close all provider HTTP clients

File lengkap setelah update:

```python
"""
AI Generative Core — FastAPI Application Entry Point.

Run with: uvicorn app.main:app --reload --port 8000
"""

from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from app.config import settings
from app.core.exceptions import AIGatewayError
from app.core.logging import setup_logging
from app.core.middleware import RequestLoggingMiddleware
from app.api.dependencies import initialize_services, get_providers
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

    # Initialize services (providers, registry, generator)
    initialize_services(settings)

    # Test Ollama connectivity
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            if resp.status_code == 200:
                logger.info("Ollama connection: OK")
            else:
                logger.warning(f"Ollama returned status {resp.status_code}")
    except Exception:
        logger.warning(
            "Ollama not reachable at {url} — requests will fail until Ollama is started",
            url=settings.OLLAMA_BASE_URL,
        )

    yield

    # === SHUTDOWN ===
    providers = get_providers()
    for name, provider in providers.items():
        await provider.close()
        logger.debug(f"Closed provider: {name}")

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
        content={"error": exc.message, "code": exc.code},
    )


# --- Health Check ---
@app.get("/health", tags=["System"], summary="Health check")
async def health_check():
    """Check if the server is running and healthy."""
    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "app_name": settings.APP_NAME,
    }
```

### Step 4: Start server dan test

```bash
# Start server
uvicorn app.main:app --reload --port 8000
```

Startup log:

```
... | AI Generative Core v0.1.1
... | Active providers: ['ollama']
... | Model registry: 6 models registered
... | GeneratorService initialized with providers: ['ollama']
... | Ollama connection: OK
```

### Step 5: Test POST /generate

```bash
curl -X POST http://localhost:8000/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{"provider":"ollama","model":"llama3.2","input":"Say hello in one word"}'
```

Response (Ollama harus running):

```json
{
    "output": "Hello!",
    "provider": "ollama",
    "model": "llama3.2",
    "usage": { "prompt_tokens": 8, "completion_tokens": 2, "total_tokens": 10 },
    "metadata": { "total_duration_ns": 1234567890 }
}
```

### Step 6: Test error scenarios

```bash
# Provider not found
curl -X POST http://localhost:8000/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{"provider":"gemini","model":"test","input":"hi"}'
# → 404: Provider 'gemini' not found or disabled

# Model not found
curl -X POST http://localhost:8000/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{"provider":"ollama","model":"nonexistent","input":"hi"}'
# → 404: Model 'nonexistent' not found for provider 'ollama'

# Invalid provider in request
curl -X POST http://localhost:8000/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{"provider":"openai","model":"test","input":"hi"}'
# → 422: Validation error (ProviderEnum)
```

### Step 7: Verify Swagger UI

Buka `http://localhost:8000/docs`:

- Section "System": `GET /health`
- Section "Models": `GET /api/v1/models`
- Section "Generation": `POST /api/v1/generate` ← **NEW**
  - Request body schema: `GenerateRequest`
  - Response schema: `GenerateResponse`
  - Error responses: 400, 404, 502, 504

---

## 6. Output yang Diharapkan

### Files Modified

| File | Changes |
|---|---|
| `app/api/dependencies.py` | +`_generator_service`, `_providers`, `get_generator_service()`, `get_providers()`, extended `initialize_services()` |
| `app/api/router.py` | +`generate` import and include |
| `app/main.py` | +`get_providers` import, +Ollama connectivity check, +shutdown cleanup |

### Endpoint Summary

| Method | Path | Status |
|---|---|---|
| GET | `/health` | Existing |
| GET | `/api/v1/models` | Existing (beta0.1.2) |
| POST | `/api/v1/generate` | **NEW** |

---

## 7. Dependencies

- **Task 2** — OllamaProvider (created by factory)
- **Task 3** — `create_provider` factory
- **Task 4** — `GeneratorService`
- **Task 5** — `generate.router`

---

## 8. Acceptance Criteria

- [ ] `uvicorn app.main:app --reload` runs without errors
- [ ] Startup log shows active providers and model count
- [ ] Ollama connectivity check runs (OK or warning)
- [ ] `POST /api/v1/generate` with Ollama returns AI text (if Ollama running)
- [ ] Provider not found → 404 JSON error
- [ ] Model not found → 404 JSON error
- [ ] Invalid provider enum → 422 validation error
- [ ] `GET /health` still works
- [ ] `GET /api/v1/models` still works
- [ ] Shutdown closes all provider HTTP clients
- [ ] Swagger UI shows all 3 endpoint groups

---

## 9. Estimasi

**Medium** — Three file updates, integration testing, error scenario verification.
