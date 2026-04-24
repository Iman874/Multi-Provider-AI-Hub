# Task 5 — Router Update & Integration Test

> **Modul**: beta0.1.5 — Streaming Adapter  
> **Estimasi**: Low (30–45 menit)  
> **Dependencies**: Task 4 (Stream Endpoint)

---

## 1. Judul Task

Update `app/api/router.py` — include stream endpoint, lalu end-to-end test streaming dari kedua provider.

---

## 2. Deskripsi

Menambahkan stream router ke central API router dan memverifikasi bahwa streaming berfungsi end-to-end dari kedua provider (Ollama dan Gemini). Termasuk validasi SSE format yang seragam.

---

## 3. Tujuan Teknis

- `api_router` include `stream.router` dengan tag "Streaming"
- Kedua provider streaming berfungsi dan menghasilkan SSE format identik
- `[DONE]` marker selalu dikirim di akhir stream
- Error scenarios tetap return JSON (bukan SSE)

---

## 4. Scope

### ✅ Yang Dikerjakan

- Update `app/api/router.py`
- End-to-end test: Ollama streaming
- End-to-end test: Gemini streaming
- Verify SSE format uniformity

### ❌ Yang Tidak Dikerjakan

- Client-side consuming code
- Performance benchmarking

---

## 5. Langkah Implementasi

### Step 1: Update `app/api/router.py`

```python
"""
Central API router that combines all endpoint routers.
"""

from fastapi import APIRouter

from app.api.endpoints import models, generate, stream

api_router = APIRouter(prefix="/api/v1")

# --- Register endpoint routers ---
api_router.include_router(models.router, tags=["Models"])
api_router.include_router(generate.router, tags=["Generation"])
api_router.include_router(stream.router, tags=["Streaming"])
```

### Step 2: Restart server

```bash
uvicorn app.main:app --reload --port 8000
```

Verify startup log — should still show all providers and models.

### Step 3: Test Ollama streaming

```bash
curl -N -X POST http://localhost:8000/api/v1/stream \
  -H "Content-Type: application/json" \
  -d '{"provider":"ollama","model":"llama3.2","input":"Count from 1 to 5"}'
```

Expected output (tokens appear one at a time):

```
data: {"token": "1"}

data: {"token": ","}

data: {"token": " 2"}

data: {"token": ","}

data: {"token": " 3"}

data: {"token": ","}

data: {"token": " 4"}

data: {"token": ","}

data: {"token": " 5"}

data: [DONE]

```

### Step 4: Test Gemini streaming

```bash
curl -N -X POST http://localhost:8000/api/v1/stream \
  -H "Content-Type: application/json" \
  -d '{"provider":"gemini","model":"gemini-2.0-flash","input":"Count from 1 to 5"}'
```

Expected output (same SSE format, possibly larger chunks):

```
data: {"token": "1, 2"}

data: {"token": ", 3, 4"}

data: {"token": ", 5"}

data: [DONE]

```

### Step 5: Verify format uniformity

Both providers MUST produce:
- `data: {"token": "..."}` per event
- `data: [DONE]` at the end
- No other format differences

### Step 6: Test error scenarios

```bash
# Provider not found
curl -X POST http://localhost:8000/api/v1/stream \
  -H "Content-Type: application/json" \
  -d '{"provider":"openai","model":"test","input":"hi"}'
# → 422 Validation Error (ProviderEnum)

# Model not found (pre-stream → JSON error)
curl -X POST http://localhost:8000/api/v1/stream \
  -H "Content-Type: application/json" \
  -d '{"provider":"ollama","model":"nonexistent","input":"hi"}'
# → SSE starts but first event is error, then [DONE]
```

### Step 7: Verify Swagger UI

Buka `http://localhost:8000/docs`:

- Section "System": `GET /health`
- Section "Models": `GET /api/v1/models`
- Section "Generation": `POST /api/v1/generate`
- Section **"Streaming"**: `POST /api/v1/stream` ← **NEW**

### Step 8: Test client disconnect

```bash
# Start streaming, then Ctrl+C mid-stream
curl -N -X POST http://localhost:8000/api/v1/stream \
  -H "Content-Type: application/json" \
  -d '{"provider":"ollama","model":"llama3.2","input":"Write a long essay about AI"}'
# Press Ctrl+C after a few tokens

# Check server — should NOT crash or log unhandled exception
```

---

## 6. Output yang Diharapkan

### Updated Router

```diff
+from app.api.endpoints import models, generate, stream

+api_router.include_router(stream.router, tags=["Streaming"])
```

### Endpoint Summary (after beta0.1.5)

| Method | Path | Tag | Status |
|---|---|---|---|
| GET | `/health` | System | Existing |
| GET | `/api/v1/models` | Models | Existing |
| POST | `/api/v1/generate` | Generation | Existing |
| POST | `/api/v1/stream` | Streaming | **NEW** |

### Uniform SSE Format (both providers)

```
data: {"token": "<text>"}
...
data: [DONE]
```

---

## 7. Dependencies

- **Task 4** — `stream.router` from `app/api/endpoints/stream.py`
- **Running Ollama** for Ollama stream test
- **GEMINI_API_KEY** for Gemini stream test

---

## 8. Acceptance Criteria

- [ ] `app/api/router.py` includes stream router
- [ ] `POST /api/v1/stream` with Ollama → tokens streamed via SSE
- [ ] `POST /api/v1/stream` with Gemini → tokens streamed via SSE
- [ ] Both providers use identical SSE format (`data: {"token": "..."}`)
- [ ] Stream terminates with `data: [DONE]`
- [ ] Invalid provider → 422 validation error (JSON, not SSE)
- [ ] Client disconnect mid-stream → no server crash
- [ ] Swagger UI shows all 4 endpoints with correct tags
- [ ] `POST /generate` still works (no regression)
- [ ] `GET /models` still works (no regression)

---

## 9. Estimasi

**Low** — 1-line router change + thorough testing.
