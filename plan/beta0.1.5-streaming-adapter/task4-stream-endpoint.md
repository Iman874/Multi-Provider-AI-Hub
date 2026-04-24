# Task 4 — POST /stream Endpoint (SSE)

> **Modul**: beta0.1.5 — Streaming Adapter  
> **Estimasi**: Medium (60–90 menit)  
> **Dependencies**: Task 3 (GeneratorService.stream())

---

## 1. Judul Task

Implementasi `app/api/endpoints/stream.py` — POST /stream endpoint yang mengirim Server-Sent Events (SSE) menggunakan `sse-starlette`.

---

## 2. Deskripsi

Membuat SSE streaming endpoint yang menerima `StreamRequest` dan mengirim token per token ke client via Server-Sent Events. Format output uniform: `data: {"token": "..."}` per event, diakhiri `data: [DONE]`. Menggunakan `sse-starlette` package untuk SSE response handling.

---

## 3. Tujuan Teknis

- Route: `POST /stream`
- Request body: `StreamRequest`
- Response: `EventSourceResponse` (Content-Type: text/event-stream)
- Event format: `data: {"token": "..."}` per token
- Termination marker: `data: [DONE]`
- Validation errors return JSON (not SSE) karena terjadi sebelum streaming

---

## 4. Scope

### ✅ Yang Dikerjakan

- Implementasi `app/api/endpoints/stream.py`
- SSE event generator function
- Proper error handling (pre-stream validation vs mid-stream)

### ❌ Yang Tidak Dikerjakan

- WebSocket alternative
- Client-side SDK
- Retry/reconnect logic

---

## 5. Langkah Implementasi

### Step 1: Buat `app/api/endpoints/stream.py`

```python
"""
Streaming endpoint — Server-Sent Events (SSE) for token-by-token generation.

Uses sse-starlette to send EventSourceResponse.
All validation happens BEFORE streaming starts, so errors
return proper JSON responses (not broken SSE streams).
"""

import json

from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse
from loguru import logger

from app.api.dependencies import get_generator_service
from app.schemas.requests import StreamRequest
from app.schemas.responses import ErrorResponse
from app.services.generator import GeneratorService

router = APIRouter()


@router.post(
    "/stream",
    summary="Stream generated tokens via SSE",
    description="Send a prompt and receive AI-generated tokens one at a time "
    "via Server-Sent Events (SSE). Each event contains a JSON object "
    'with a "token" field. The stream ends with a `[DONE]` marker.',
    responses={
        400: {"model": ErrorResponse, "description": "Capability not supported"},
        404: {"model": ErrorResponse, "description": "Provider or model not found"},
        502: {"model": ErrorResponse, "description": "Provider connection error"},
        504: {"model": ErrorResponse, "description": "Provider timeout"},
    },
)
async def stream_generate(
    request: StreamRequest,
    service: GeneratorService = Depends(get_generator_service),
):
    """
    Stream AI-generated tokens via Server-Sent Events.

    SSE output format:
        data: {"token": "Hello"}
        data: {"token": " world"}
        data: {"token": "!"}
        data: [DONE]

    Client consumption (JavaScript):
        const source = new EventSource('/api/v1/stream', ...);
        source.onmessage = (e) => {
            if (e.data === '[DONE]') { source.close(); return; }
            const { token } = JSON.parse(e.data);
            // append token to UI
        };
    """

    async def event_generator():
        """
        Internal generator that yields SSE-formatted events.

        Validation errors from GeneratorService are raised before
        this generator starts, so they result in proper JSON error
        responses via the global exception handler.
        """
        try:
            async for token in service.stream(request):
                yield {
                    "data": json.dumps({"token": token}),
                }
        except Exception as e:
            # Mid-stream error — log and send error event
            logger.error(
                "Stream error: {error}",
                error=str(e),
            )
            yield {
                "data": json.dumps({
                    "error": str(e),
                    "code": getattr(e, "code", "STREAM_ERROR"),
                }),
            }

        # Send termination marker
        yield {"data": "[DONE]"}

    return EventSourceResponse(event_generator())
```

### Step 2: Verifikasi import

```bash
python -c "
from app.api.endpoints.stream import router
print(f'Routes: {len(router.routes)}')
for route in router.routes:
    print(f'  {route.methods} {route.path}')
"
```

Output:

```
Routes: 1
  {'POST'} /stream
```

---

## 6. Output yang Diharapkan

### File: `app/api/endpoints/stream.py`

Isi seperti Step 1 di atas.

### SSE Output (curl)

```bash
curl -N -X POST http://localhost:8000/api/v1/stream \
  -H "Content-Type: application/json" \
  -d '{"provider":"ollama","model":"llama3.2","input":"Say hello"}'
```

Output:

```
data: {"token": "Hello"}

data: {"token": "!"}

data: {"token": " How"}

data: {"token": " can"}

data: {"token": " I"}

data: {"token": " help"}

data: {"token": " you"}

data: {"token": "?"}

data: [DONE]

```

### Error Response (pre-stream validation)

```bash
curl -X POST http://localhost:8000/api/v1/stream \
  -H "Content-Type: application/json" \
  -d '{"provider":"openai","model":"test","input":"hi"}'
```

Response (regular JSON, NOT SSE — karena validation error):

```json
422 Unprocessable Entity
{
    "detail": [{"msg": "Input should be 'ollama' or 'gemini'", ...}]
}
```

---

## 7. Dependencies

- **Task 3** — `GeneratorService.stream()` method
- **beta0.1.2 Task 2** — `StreamRequest` schema
- **Package**: `sse-starlette` (sudah di requirements.txt)

---

## 8. Acceptance Criteria

- [ ] File `app/api/endpoints/stream.py` ada
- [ ] Router memiliki `POST /stream` route
- [ ] Response Content-Type is `text/event-stream`
- [ ] Each token sent as `data: {"token": "..."}`
- [ ] Stream ends with `data: [DONE]`
- [ ] Validation errors (provider/model not found) return JSON, not SSE
- [ ] Mid-stream errors logged and sent as error event
- [ ] `EventSourceResponse` digunakan (bukan custom SSE)

---

## 9. Estimasi

**Medium** — SSE pattern baru, event generator design, error boundary between JSON/SSE.
