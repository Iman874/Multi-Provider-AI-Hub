# Task 4 — POST /embedding Endpoint

> **Modul**: beta0.1.6 — Embedding Endpoint  
> **Estimasi**: Low (20–30 menit)  
> **Dependencies**: Task 3 (GeneratorService.embedding())

---

## 1. Judul Task

Implementasi `app/api/endpoints/embedding.py` — POST /embedding endpoint yang menerima text dan mengembalikan embedding vector.

---

## 2. Deskripsi

Membuat thin endpoint yang menerima `EmbeddingRequest`, memanggil `GeneratorService.embedding()`, dan mengembalikan `EmbeddingResponse`. Sama seperti `/generate` — endpoint TIDAK memiliki business logic.

---

## 3. Tujuan Teknis

- Route: `POST /embedding`
- Request body: `EmbeddingRequest`
- Response: `EmbeddingResponse`
- Inject `GeneratorService` via Depends
- Endpoint code hanya ~5 baris

---

## 4. Scope

### ✅ Yang Dikerjakan

- Implementasi `app/api/endpoints/embedding.py`

### ❌ Yang Tidak Dikerjakan

- Business logic (in service)
- Batch embedding
- Error handling (in global handler)

---

## 5. Langkah Implementasi

### Step 1: Buat `app/api/endpoints/embedding.py`

```python
"""
Embedding endpoint — Generate vector embeddings from text.

Delegates all logic to GeneratorService.
This endpoint contains NO business logic.
"""

from fastapi import APIRouter, Depends

from app.api.dependencies import get_generator_service
from app.schemas.requests import EmbeddingRequest
from app.schemas.responses import EmbeddingResponse, ErrorResponse
from app.services.generator import GeneratorService

router = APIRouter()


@router.post(
    "/embedding",
    response_model=EmbeddingResponse,
    summary="Generate text embedding",
    description="Generate a vector embedding from input text using the specified "
    "provider and embedding model. The model must support embedding capability.",
    responses={
        400: {"model": ErrorResponse, "description": "Model doesn't support embedding"},
        404: {"model": ErrorResponse, "description": "Provider or model not found"},
        502: {"model": ErrorResponse, "description": "Provider connection error"},
        504: {"model": ErrorResponse, "description": "Provider timeout"},
    },
)
async def create_embedding(
    request: EmbeddingRequest,
    service: GeneratorService = Depends(get_generator_service),
) -> EmbeddingResponse:
    """
    Generate embedding vector from text.

    The model must have embedding capability (e.g. nomic-embed-text, text-embedding-004).
    Text generation models (e.g. llama3.2) will return a 400 error.
    """
    return await service.embedding(request)
```

### Step 2: Verifikasi import

```bash
python -c "
from app.api.endpoints.embedding import router
print(f'Routes: {len(router.routes)}')
for route in router.routes:
    print(f'  {route.methods} {route.path}')
"
```

Output:

```
Routes: 1
  {'POST'} /embedding
```

---

## 6. Output yang Diharapkan

### File: `app/api/endpoints/embedding.py`

Isi seperti Step 1 di atas.

### API Behavior

**Request:**
```json
POST /api/v1/embedding
{
    "provider": "ollama",
    "model": "nomic-embed-text",
    "input": "Hello world"
}
```

**Response 200:**
```json
{
    "embedding": [0.0123, -0.0456, 0.0789, ...],
    "provider": "ollama",
    "model": "nomic-embed-text"
}
```

**Response 400 (capability error):**
```json
{
    "error": "Model 'llama3.2' does not support 'embedding'",
    "code": "CAPABILITY_NOT_SUPPORTED"
}
```

---

## 7. Dependencies

- **Task 3** — `GeneratorService.embedding()` method
- **beta0.1.2 Task 2** — `EmbeddingRequest` schema
- **beta0.1.2 Task 3** — `EmbeddingResponse`, `ErrorResponse` schemas

---

## 8. Acceptance Criteria

- [ ] File `app/api/endpoints/embedding.py` ada
- [ ] Router memiliki `POST /embedding` route
- [ ] Endpoint menerima `EmbeddingRequest` body
- [ ] Endpoint returns `EmbeddingResponse`
- [ ] Endpoint code is thin — no business logic
- [ ] Swagger UI shows error response schemas (400, 404, 502, 504)

---

## 9. Estimasi

**Low** — Same thin-endpoint pattern as `/generate`.
