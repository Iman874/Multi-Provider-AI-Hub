# Task 6 — Models Endpoint & Router

> **Modul**: beta0.1.2 — Schema & Model Registry  
> **Estimasi**: Medium (45–60 menit)  
> **Dependencies**: Task 3 (Response Schemas), Task 5 (Dependency Injection)

---

## 1. Judul Task

Implementasi `app/api/endpoints/models.py` (GET /models endpoint) dan `app/api/router.py` (central API router).

---

## 2. Deskripsi

Membuat endpoint pertama yang menghasilkan data nyata — `GET /api/v1/models` mengembalikan daftar semua model yang terdaftar di registry beserta capability-nya. Juga membuat central router yang akan digunakan untuk menggabungkan semua endpoint di masa depan.

---

## 3. Tujuan Teknis

- `GET /api/v1/models` — return `list[ModelInfo]`
- Optional query parameter `provider` untuk filter
- Central `api_router` yang include semua sub-routers
- Endpoint menggunakan `Depends(get_model_registry)` untuk akses registry
- Response di-convert dari `ModelCapability` → `ModelInfo`

---

## 4. Scope

### ✅ Yang Dikerjakan

- Implementasi `app/api/endpoints/models.py`
- Implementasi `app/api/router.py`

### ❌ Yang Tidak Dikerjakan

- Endpoints /generate, /stream, /embedding → beta0.1.3+
- Auto-discovery model dari Ollama API
- Model CRUD (create/update/delete) — registry is read-only via API

---

## 5. Langkah Implementasi

### Step 1: Buat `app/api/endpoints/models.py`

```python
"""
Models endpoint — List available AI models and their capabilities.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_model_registry
from app.schemas.responses import ModelInfo
from app.services.model_registry import ModelRegistry

router = APIRouter()


@router.get(
    "/models",
    response_model=list[ModelInfo],
    summary="List available models",
    description="Returns all registered AI models with their capabilities. "
    "Optionally filter by provider.",
)
async def list_models(
    provider: Optional[str] = Query(
        default=None,
        description="Filter models by provider (e.g. 'ollama', 'gemini')",
        examples=["ollama", "gemini"],
    ),
    registry: ModelRegistry = Depends(get_model_registry),
) -> list[ModelInfo]:
    """
    List all available models, optionally filtered by provider.

    This endpoint queries the ModelRegistry and returns metadata
    for each registered model, including capability flags.
    """
    models = registry.list_models(provider=provider)

    return [
        ModelInfo(
            name=m.name,
            provider=m.provider,
            supports_text=m.supports_text,
            supports_image=m.supports_image,
            supports_embedding=m.supports_embedding,
        )
        for m in models
    ]
```

### Step 2: Buat `app/api/router.py`

```python
"""
Central API router that combines all endpoint routers.

All business endpoints are prefixed with /api/v1.
New endpoint modules are added here as they are implemented.
"""

from fastapi import APIRouter

from app.api.endpoints import models

api_router = APIRouter(prefix="/api/v1")

# --- Register endpoint routers ---
api_router.include_router(models.router, tags=["Models"])

# Future endpoints (beta0.1.3+):
# api_router.include_router(generate.router, tags=["Generation"])
# api_router.include_router(stream.router, tags=["Streaming"])
# api_router.include_router(embedding.router, tags=["Embedding"])
```

### Step 3: Verifikasi (standalone — tanpa server)

```bash
python -c "
from app.api.router import api_router
print(f'Routes: {len(api_router.routes)}')
for route in api_router.routes:
    print(f'  {route.methods} {route.path}')
"
```

Output yang diharapkan:

```
Routes: 1
  {'GET'} /api/v1/models
```

---

## 6. Output yang Diharapkan

### File: `app/api/endpoints/models.py` dan `app/api/router.py`

Isi seperti Step 1 & 2 di atas.

### API Response: GET /api/v1/models

```json
[
    {
        "name": "llama3.2",
        "provider": "ollama",
        "supports_text": true,
        "supports_image": false,
        "supports_embedding": false
    },
    {
        "name": "llama3.2-vision",
        "provider": "ollama",
        "supports_text": true,
        "supports_image": true,
        "supports_embedding": false
    },
    {
        "name": "nomic-embed-text",
        "provider": "ollama",
        "supports_text": false,
        "supports_image": false,
        "supports_embedding": true
    },
    {
        "name": "gemini-2.0-flash",
        "provider": "gemini",
        "supports_text": true,
        "supports_image": true,
        "supports_embedding": false
    },
    {
        "name": "gemini-2.5-flash-preview-04-17",
        "provider": "gemini",
        "supports_text": true,
        "supports_image": true,
        "supports_embedding": false
    },
    {
        "name": "text-embedding-004",
        "provider": "gemini",
        "supports_text": false,
        "supports_image": false,
        "supports_embedding": true
    }
]
```

### API Response: GET /api/v1/models?provider=gemini

```json
[
    {
        "name": "gemini-2.0-flash",
        "provider": "gemini",
        "supports_text": true,
        "supports_image": true,
        "supports_embedding": false
    },
    {
        "name": "gemini-2.5-flash-preview-04-17",
        "provider": "gemini",
        "supports_text": true,
        "supports_image": true,
        "supports_embedding": false
    },
    {
        "name": "text-embedding-004",
        "provider": "gemini",
        "supports_text": false,
        "supports_image": false,
        "supports_embedding": true
    }
]
```

---

## 7. Dependencies

- **Task 3** — `ModelInfo` dari `app/schemas/responses.py`
- **Task 5** — `get_model_registry` dari `app/api/dependencies.py`
- **Task 4** — `ModelRegistry` class

---

## 8. Acceptance Criteria

- [ ] File `app/api/endpoints/models.py` ada
- [ ] File `app/api/router.py` ada
- [ ] `api_router` bisa di-import tanpa error
- [ ] `GET /api/v1/models` return JSON array
- [ ] Response berisi 6 default models
- [ ] `GET /api/v1/models?provider=ollama` return 3 models
- [ ] `GET /api/v1/models?provider=gemini` return 3 models
- [ ] `GET /api/v1/models?provider=openai` return empty array `[]`
- [ ] Setiap model memiliki: name, provider, supports_text, supports_image, supports_embedding
- [ ] Swagger UI menampilkan endpoint dengan query parameter

---

## 9. Estimasi

**Medium** — Endpoint + router setup, conversion logic ModelCapability → ModelInfo.
