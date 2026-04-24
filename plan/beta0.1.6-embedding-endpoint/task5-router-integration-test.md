# Task 5 — Router Update & Integration Test

> **Modul**: beta0.1.6 — Embedding Endpoint  
> **Estimasi**: Low (30–45 menit)  
> **Dependencies**: Task 4 (Embedding Endpoint)

---

## 1. Judul Task

Update `app/api/router.py` — include embedding endpoint, lalu end-to-end test embedding dari kedua provider dengan capability validation.

---

## 2. Deskripsi

Menambahkan embedding router ke central API router dan memverifikasi embedding berfungsi end-to-end: Ollama (`qwen3-embedding:0.6b`), Gemini (`text-embedding-004` — jika API aktif), dan capability error (text model → 400).

---

## 3. Tujuan Teknis

- `api_router` include `embedding.router` dengan tag "Embedding"
- Kedua provider embedding berfungsi dan return `list[float]`
- Capability validation aktif: text model → 400 error
- All existing endpoints unchanged (no regression)

---

## 4. Scope

### ✅ Yang Dikerjakan

- Update `app/api/router.py`
- End-to-end test: Ollama embedding
- End-to-end test: Gemini embedding
- Test capability validation

### ❌ Yang Tidak Dikerjakan

- Embedding quality evaluation
- Performance benchmarks

---

## 5. Langkah Implementasi

### Step 1: Update `app/api/router.py`

```python
"""
Central API router that combines all endpoint routers.
"""

from fastapi import APIRouter

from app.api.endpoints import models, generate, stream, embedding

api_router = APIRouter(prefix="/api/v1")

# --- Register endpoint routers ---
api_router.include_router(models.router, tags=["Models"])
api_router.include_router(generate.router, tags=["Generation"])
api_router.include_router(stream.router, tags=["Streaming"])
api_router.include_router(embedding.router, tags=["Embedding"])
```

### Step 2: Restart server

```bash
uvicorn app.main:app --reload --port 8000
```

### Step 3: Test Ollama embedding

```bash
curl -X POST http://localhost:8000/api/v1/embedding \
  -H "Content-Type: application/json" \
  -d '{"provider":"ollama","model":"qwen3-embedding:0.6b","input":"Hello world"}'
```

Expected response:

```json
{
    "embedding": [0.0123, -0.0456, 0.0789, ...],
    "provider": "ollama",
    "model": "qwen3-embedding:0.6b"
}
```

Verify:
- `embedding` is an array of floats
- Array length > 0 (typically 1024 for qwen3-embedding:0.6b)

### Step 4: Test Gemini embedding (opsional — API mungkin tidak aktif)

> ⚠️ Jika test ini gagal (error 4xx/5xx), **task tetap SELESAI**. Embedding tersedia via Ollama.

```bash
curl -X POST http://localhost:8000/api/v1/embedding \
  -H "Content-Type: application/json" \
  -d '{"provider":"gemini","model":"text-embedding-004","input":"Hello world"}'
```

Jika API aktif:

```json
{
    "embedding": [0.0412, -0.0231, 0.0567, ...],
    "provider": "gemini",
    "model": "text-embedding-004"
}
```

Jika API tidak aktif: akan return error 502 — ini **expected** dan bukan bug.

### Step 5: Test capability validation — text model

```bash
curl -X POST http://localhost:8000/api/v1/embedding \
  -H "Content-Type: application/json" \
  -d '{"provider":"ollama","model":"llama3.2","input":"Hello"}'
```

Expected 400 response:

```json
{
    "error": "Model 'llama3.2' does not support 'embedding'",
    "code": "CAPABILITY_NOT_SUPPORTED"
}
```

### Step 6: Test capability validation — Gemini text model

```bash
curl -X POST http://localhost:8000/api/v1/embedding \
  -H "Content-Type: application/json" \
  -d '{"provider":"gemini","model":"gemini-2.0-flash","input":"Hello"}'
```

Expected 400 response:

```json
{
    "error": "Model 'gemini-2.0-flash' does not support 'embedding'",
    "code": "CAPABILITY_NOT_SUPPORTED"
}
```

### Step 7: Regression test

```bash
# All existing endpoints must still work
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/models

curl -X POST http://localhost:8000/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{"provider":"ollama","model":"llama3.2","input":"hi"}'

curl -N -X POST http://localhost:8000/api/v1/stream \
  -H "Content-Type: application/json" \
  -d '{"provider":"ollama","model":"llama3.2","input":"hi"}'
```

### Step 8: Verify Swagger UI

Buka `http://localhost:8000/docs`:

- Section "System": `GET /health`
- Section "Models": `GET /api/v1/models`
- Section "Generation": `POST /api/v1/generate`
- Section "Streaming": `POST /api/v1/stream`
- Section **"Embedding"**: `POST /api/v1/embedding` ← **NEW**

---

## 6. Output yang Diharapkan

### Final Endpoint Summary (after beta0.1.6)

| Method | Path | Tag | Status |
|---|---|---|---|
| GET | `/health` | System | Existing |
| GET | `/api/v1/models` | Models | Existing |
| POST | `/api/v1/generate` | Generation | Existing |
| POST | `/api/v1/stream` | Streaming | Existing |
| POST | `/api/v1/embedding` | Embedding | **NEW** |

### Uniform Embedding Format (both providers)

```json
{
    "embedding": [float, float, ...],
    "provider": "string",
    "model": "string"
}
```

---

## 7. Dependencies

- **Task 4** — `embedding.router` from `app/api/endpoints/embedding.py`
- **Running Ollama** with `qwen3-embedding:0.6b` model
- **GEMINI_API_KEY** for Gemini embedding test *(opsional — test bisa di-skip)*

---

## 8. Acceptance Criteria

- [ ] `app/api/router.py` includes embedding router
- [ ] `POST /api/v1/embedding` Ollama → returns float vector
- [ ] `POST /api/v1/embedding` Gemini → returns float vector *(ATAU error jika API tidak aktif — tetap pass)*
- [ ] Both providers return identical response format
- [ ] Text model (`llama3.2`) → 400 CAPABILITY_NOT_SUPPORTED
- [ ] Text model (`gemini-2.0-flash`) → 400 CAPABILITY_NOT_SUPPORTED
- [ ] `GET /health` still works
- [ ] `POST /generate` still works
- [ ] `POST /stream` still works
- [ ] Swagger UI shows all 5 endpoints with correct tags

---

## 9. Estimasi

**Low** — 1-line router change + thorough e2e testing.
