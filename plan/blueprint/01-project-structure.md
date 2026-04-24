# 01 — Project Structure & File Responsibilities

---

## Layer Breakdown

### 1. Entry Point — `app/main.py`

- Create FastAPI app instance
- Include all routers
- Register middleware (logging, CORS)
- Startup/shutdown events (initialize providers, registry)

```python
app = FastAPI(
    title="AI Generative Core",
    version="1.0.0",
    description="Universal AI Gateway for SaaS applications"
)
app.add_middleware(RequestLoggingMiddleware)
app.include_router(api_router, prefix="/api/v1")
```

---

### 2. Configuration — `app/config.py`

- Load `.env` via `pydantic-settings`
- Typed settings: `OLLAMA_BASE_URL`, `GEMINI_API_KEY`, timeouts, log level
- Validate required configs at startup

---

### 3. API Layer — `app/api/`

| File | Purpose |
|---|---|
| `router.py` | Combines all endpoint routers |
| `endpoints/generate.py` | `POST /generate` — text & multimodal |
| `endpoints/stream.py` | `POST /stream` — SSE streaming |
| `endpoints/models.py` | `GET /models` — list models |
| `endpoints/embedding.py` | `POST /embedding` — vector embedding |
| `dependencies.py` | FastAPI `Depends()` — inject services |

**Key Rule**: Endpoints ONLY parse request → call service → return response. NO business logic.

---

### 4. Schemas — `app/schemas/`

| File | Purpose |
|---|---|
| `common.py` | `ProviderEnum`, `Capability` enum, shared types |
| `requests.py` | `GenerateRequest`, `StreamRequest`, `EmbeddingRequest` |
| `responses.py` | `GenerateResponse`, `ModelInfo`, `EmbeddingResponse` |

---

### 5. Services — `app/services/`

| File | Purpose |
|---|---|
| `generator.py` | `GeneratorService` — orchestrates providers |
| `model_registry.py` | `ModelRegistry` — model catalog & capabilities |

---

### 6. Providers — `app/providers/`

| File | Purpose |
|---|---|
| `base.py` | `BaseProvider` — abstract contract |
| `ollama.py` | `OllamaProvider` — Ollama API integration |
| `gemini.py` | `GeminiProvider` — Google Gemini integration |

---

### 7. Core — `app/core/`

| File | Purpose |
|---|---|
| `exceptions.py` | Custom exception classes |
| `logging.py` | Loguru configuration |
| `middleware.py` | Request/response logging middleware |

---

### 8. Utilities — `app/utils/`

| File | Purpose |
|---|---|
| `image.py` | Image encoding/decoding, URL→base64, validation |

---

## Data Flow

```
Request → Endpoint → Service → Provider → External API
                                    ↓
Response ← Endpoint ← Service ← Provider ← External API
```

> **Next**: See [02-provider-layer.md](./02-provider-layer.md)
