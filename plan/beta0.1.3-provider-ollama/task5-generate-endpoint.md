# Task 5 — POST /generate Endpoint

> **Modul**: beta0.1.3 — Provider Abstraction & Ollama  
> **Estimasi**: Low (20–30 menit)  
> **Dependencies**: Task 4 (GeneratorService), beta0.1.2 Task 2+3 (Schemas)

---

## 1. Judul Task

Implementasi `app/api/endpoints/generate.py` — POST /generate endpoint yang menerima prompt dan mengembalikan AI-generated text.

---

## 2. Deskripsi

Membuat endpoint pertama yang benar-benar menghasilkan AI output. Endpoint ini **hanya bertugas 3 hal**: parse request, panggil service, return response. **TIDAK ADA business logic di endpoint** — semuanya sudah di-handle oleh `GeneratorService`.

---

## 3. Tujuan Teknis

- Route: `POST /generate`
- Request body: `GenerateRequest`
- Response: `GenerateResponse`
- Inject `GeneratorService` via FastAPI `Depends`
- Endpoint code hanya ~5 baris logic

---

## 4. Scope

### ✅ Yang Dikerjakan

- Implementasi `app/api/endpoints/generate.py`

### ❌ Yang Tidak Dikerjakan

- Business logic (sudah di GeneratorService)
- Error handling (sudah di exception handler global)
- Streaming endpoint → beta0.1.5
- Embedding endpoint → beta0.1.6

---

## 5. Langkah Implementasi

### Step 1: Buat `app/api/endpoints/generate.py`

```python
"""
Generate endpoint — Text and multimodal AI generation.

Delegates all logic to GeneratorService.
This endpoint contains NO business logic.
"""

from fastapi import APIRouter, Depends

from app.api.dependencies import get_generator_service
from app.schemas.requests import GenerateRequest
from app.schemas.responses import ErrorResponse, GenerateResponse
from app.services.generator import GeneratorService

router = APIRouter()


@router.post(
    "/generate",
    response_model=GenerateResponse,
    summary="Generate text or multimodal response",
    description="Send a prompt to an AI provider and receive a generated response. "
    "Supports text-only and multimodal (text + images) input.",
    responses={
        400: {"model": ErrorResponse, "description": "Capability not supported"},
        404: {"model": ErrorResponse, "description": "Provider or model not found"},
        502: {"model": ErrorResponse, "description": "Provider connection error"},
        504: {"model": ErrorResponse, "description": "Provider timeout"},
    },
)
async def generate(
    request: GenerateRequest,
    service: GeneratorService = Depends(get_generator_service),
) -> GenerateResponse:
    """
    Generate AI response from the specified provider and model.

    The request is routed to the appropriate provider (Ollama, Gemini)
    after validating the model exists and supports the requested capabilities.
    """
    return await service.generate(request)
```

### Step 2: Verifikasi (import only)

```bash
python -c "
from app.api.endpoints.generate import router
print(f'Routes: {len(router.routes)}')
for route in router.routes:
    print(f'  {route.methods} {route.path}')
"
```

Output:

```
Routes: 1
  {'POST'} /generate
```

---

## 6. Output yang Diharapkan

### File: `app/api/endpoints/generate.py`

Isi seperti Step 1 di atas.

### API Behavior

**Request:**
```json
POST /api/v1/generate
{
    "provider": "ollama",
    "model": "llama3.2",
    "input": "Say hello in one word"
}
```

**Response 200:**
```json
{
    "output": "Hello!",
    "provider": "ollama",
    "model": "llama3.2",
    "usage": {
        "prompt_tokens": 8,
        "completion_tokens": 2,
        "total_tokens": 10
    },
    "metadata": {
        "total_duration_ns": 1234567890
    }
}
```

**Response 404 (provider not found):**
```json
{
    "error": "Provider 'openai' not found or disabled",
    "code": "PROVIDER_NOT_FOUND"
}
```

---

## 7. Dependencies

- **Task 4** — `GeneratorService`
- **beta0.1.2 Task 2** — `GenerateRequest`
- **beta0.1.2 Task 3** — `GenerateResponse`, `ErrorResponse`
- **Task 6** — `get_generator_service` dependency (next task)

> **Note**: `get_generator_service` belum ada — akan dibuat di Task 6. File ini bisa ditulis sekarang, tapi baru bisa ditest setelah Task 6 selesai.

---

## 8. Acceptance Criteria

- [ ] File `app/api/endpoints/generate.py` ada
- [ ] Router memiliki 1 route: `POST /generate`
- [ ] Endpoint menerima `GenerateRequest` body
- [ ] Endpoint return `GenerateResponse`
- [ ] Endpoint code hanya parse → call → return (no business logic)
- [ ] Swagger UI menampilkan error response schemas (400, 404, 502, 504)
- [ ] Endpoint bisa di-import tanpa error

---

## 9. Estimasi

**Low** — Minimal code, semua logic sudah di service.
