# 04 — API Layer Design

---

## Router Setup

File: `app/api/router.py`

```python
from fastapi import APIRouter
from app.api.endpoints import generate, stream, models, embedding

api_router = APIRouter()
api_router.include_router(generate.router, tags=["Generation"])
api_router.include_router(stream.router, tags=["Streaming"])
api_router.include_router(models.router, tags=["Models"])
api_router.include_router(embedding.router, tags=["Embedding"])
```

---

## Endpoint 1: POST /generate

File: `app/api/endpoints/generate.py`

### Behavior

- Jika `images` ada → mode multimodal
- Jika tidak → text generation biasa
- Endpoint **tidak tahu** detail provider — semuanya lewat service

### Implementation

```python
@router.post("/generate", response_model=GenerateResponse)
async def generate(
    request: GenerateRequest,
    service: GeneratorService = Depends(get_generator_service),
):
    return await service.generate(request)
```

### Example Request

```json
{
    "provider": "ollama",
    "model": "llama3.2",
    "input": "Explain quantum computing in simple terms",
    "images": null,
    "stream": false
}
```

### Example Response

```json
{
    "output": "Quantum computing uses quantum bits (qubits)...",
    "provider": "ollama",
    "model": "llama3.2",
    "usage": {
        "prompt_tokens": 12,
        "completion_tokens": 156,
        "total_tokens": 168
    },
    "metadata": {
        "duration_ms": 2340
    }
}
```

### Multimodal Request

```json
{
    "provider": "gemini",
    "model": "gemini-2.0-flash",
    "input": "Describe what you see in this image",
    "images": ["data:image/jpeg;base64,/9j/4AAQ..."],
    "stream": false
}
```

---

## Endpoint 2: POST /stream

File: `app/api/endpoints/stream.py`

### Behavior

- Returns SSE (Server-Sent Events) via `text/event-stream`
- Setiap token dikirim sebagai satu event
- Final event: `[DONE]`

### Implementation

```python
from sse_starlette.sse import EventSourceResponse

@router.post("/stream")
async def stream(
    request: StreamRequest,
    service: GeneratorService = Depends(get_generator_service),
):
    async def event_generator():
        async for token in service.stream(request):
            yield {"data": json.dumps({"token": token})}
        yield {"data": "[DONE]"}

    return EventSourceResponse(event_generator())
```

### SSE Output Format

```
data: {"token": "Quantum"}

data: {"token": " computing"}

data: {"token": " uses"}

data: {"token": "..."}

data: [DONE]
```

---

## Endpoint 3: GET /models

File: `app/api/endpoints/models.py`

### Behavior

- Mengembalikan semua model dari `ModelRegistry`
- Optional filter by `provider` query param

### Implementation

```python
@router.get("/models", response_model=list[ModelInfo])
async def list_models(
    provider: str | None = None,
    registry: ModelRegistry = Depends(get_model_registry),
):
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

### Example Response

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
        "name": "gemini-2.0-flash",
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

## Endpoint 4: POST /embedding

File: `app/api/endpoints/embedding.py`

### Implementation

```python
@router.post("/embedding", response_model=EmbeddingResponse)
async def create_embedding(
    request: EmbeddingRequest,
    service: GeneratorService = Depends(get_generator_service),
):
    return await service.embedding(request)
```

### Example Request

```json
{
    "provider": "ollama",
    "model": "nomic-embed-text",
    "input": "The quick brown fox jumps over the lazy dog"
}
```

### Example Response

```json
{
    "embedding": [0.0123, -0.0456, 0.0789, ...],
    "provider": "ollama",
    "model": "nomic-embed-text"
}
```

---

## Endpoint Summary

| Method | Path | Purpose | Response |
|---|---|---|---|
| POST | `/api/v1/generate` | Text/multimodal gen | `GenerateResponse` |
| POST | `/api/v1/stream` | SSE streaming | `text/event-stream` |
| GET | `/api/v1/models` | List models | `list[ModelInfo]` |
| POST | `/api/v1/embedding` | Vector embedding | `EmbeddingResponse` |

> **Next**: See [05-schemas.md](./05-schemas.md)
