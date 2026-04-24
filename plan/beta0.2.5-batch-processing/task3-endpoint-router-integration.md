# Task 3 — Endpoint, Router & Dependency Integration

## 1. Judul Task
Buat batch endpoints, register router, dan integrasi `BatchService` ke dependency injection

## 2. Deskripsi
Menghubungkan `BatchService` ke FastAPI: membuat endpoint file, mendaftarkan router, menambahkan singleton `BatchService` ke DI layer, dan menginisialisasinya saat startup.

## 3. Tujuan Teknis
- `POST /api/v1/batch/generate` endpoint
- `POST /api/v1/batch/embedding` endpoint
- `get_batch_service()` dependency function
- `BatchService` diinisialisasi di `initialize_services()`
- Router terdaftar di `api_router`

## 4. Scope
### Yang dikerjakan
- `app/api/endpoints/batch.py` — file baru (2 endpoints)
- `app/api/dependencies.py` — tambah singleton + getter + init
- `app/api/router.py` — register batch router

### Yang TIDAK dikerjakan
- BatchService logic (Task 2)
- Unit tests (Task 4)

## 5. Langkah Implementasi

### Step 1: Buat `app/api/endpoints/batch.py`

```python
"""
Batch endpoints — Process multiple prompts/texts in a single request.
"""

from fastapi import APIRouter, Depends

from app.api.dependencies import get_batch_service
from app.schemas.requests import BatchGenerateRequest, BatchEmbeddingRequest
from app.schemas.responses import BatchGenerateResponse, BatchEmbeddingResponse
from app.services.batch_service import BatchService

router = APIRouter()


@router.post(
    "/batch/generate",
    response_model=BatchGenerateResponse,
    summary="Batch text generation",
    description="Process multiple prompts in a single request with concurrent execution. "
    "Each item is processed independently — partial failures are captured per-item.",
)
async def batch_generate(
    request: BatchGenerateRequest,
    batch_service: BatchService = Depends(get_batch_service),
) -> BatchGenerateResponse:
    """Batch generate text for multiple prompts."""
    return await batch_service.generate_batch(request)


@router.post(
    "/batch/embedding",
    response_model=BatchEmbeddingResponse,
    summary="Batch embedding generation",
    description="Generate embeddings for multiple texts in a single request.",
)
async def batch_embedding(
    request: BatchEmbeddingRequest,
    batch_service: BatchService = Depends(get_batch_service),
) -> BatchEmbeddingResponse:
    """Batch generate embeddings for multiple texts."""
    return await batch_service.embedding_batch(request)
```

### Step 2: Update `app/api/dependencies.py`

**Tambah import:**
```python
from app.services.batch_service import BatchService
```

**Tambah singleton:**
```python
_batch_service: BatchService | None = None
```

**Tambah getter function (setelah `get_health_checker`):**
```python
def get_batch_service() -> BatchService:
    """FastAPI dependency: provides BatchService instance."""
    if _batch_service is None:
        raise RuntimeError("BatchService not initialized. Call initialize_services() first.")
    return _batch_service
```

**Update `initialize_services()` — tambah `_batch_service` ke global statement dan init di akhir:**
```python
global ..., _batch_service

# --- 7. Create Batch Service ---
_batch_service = BatchService(
    generator=_generator_service,
    max_size=settings.BATCH_MAX_SIZE,
    concurrency=settings.BATCH_CONCURRENCY,
)
```

### Step 3: Register router di `app/api/router.py`

**Tambah import:**
```python
from app.api.endpoints import models, generate, stream, embedding, chat, cache, batch
```

**Tambah router registration:**
```python
api_router.include_router(batch.router, tags=["Batch"])
```

## 6. Output yang Diharapkan

Setelah selesai, kedua endpoint harus muncul di Swagger UI (`/docs`):
- `POST /api/v1/batch/generate` — tag "Batch"
- `POST /api/v1/batch/embedding` — tag "Batch"

Server harus bisa start tanpa error:
```
uvicorn app.main:app --reload --port 8000
```

## 7. Dependencies
- **Task 1** — Schemas
- **Task 2** — `BatchService` class

## 8. Acceptance Criteria
- [ ] `app/api/endpoints/batch.py` — 2 endpoints
- [ ] `get_batch_service()` dependency function ada di `dependencies.py`
- [ ] `_batch_service` singleton diinisialisasi di `initialize_services()`
- [ ] Router terdaftar di `api_router` dengan tag "Batch"
- [ ] Endpoints muncul di Swagger UI (`/docs`)
- [ ] Server start tanpa error
- [ ] Auth & rate limiting berlaku otomatis (inherited dari `api_router` dependencies)
- [ ] Semua existing tests tetap PASS

## 9. Estimasi
Low (~30 menit)
