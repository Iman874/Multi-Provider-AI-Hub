# Project Structure — AI Generative Core

> **Snapshot Version**: beta0.2.5-batch-processing
> **Last Updated**: 2026-04-23

---

## Folder Structure

```
ai-local-api/
├── .agents/
│   └── rules/
│       └── my-style.md              # Coding style rules for all contributors & AI agents
│
├── app/                              # ← Main application package
│   ├── __init__.py
│   ├── main.py                       # FastAPI entry point, lifespan, exception handlers
│   ├── config.py                     # Pydantic Settings (env-based configuration)
│   │
│   ├── api/                          # API Layer — endpoint definitions
│   │   ├── __init__.py
│   │   ├── router.py                 # Central APIRouter (prefix: /api/v1)
│   │   ├── dependencies.py           # DI: singleton services, initialize_services()
│   │   ├── endpoints/
│   │   │   ├── __init__.py
│   │   │   ├── models.py             # GET  /api/v1/models
│   │   │   ├── generate.py           # POST /api/v1/generate
│   │   │   ├── stream.py             # POST /api/v1/stream (SSE)
│   │   │   ├── embedding.py          # POST /api/v1/embedding
│   │   │   ├── chat.py               # POST /api/v1/chat, GET/DELETE history
│   │   │   ├── cache.py              # GET /api/v1/cache/stats, DELETE /api/v1/cache
│   │   │   └── batch.py              # POST /api/v1/batch/generate, POST /api/v1/batch/embedding
│   ├── core/                         # Cross-cutting infrastructure
│   │   ├── __init__.py
│   │   ├── auth.py                   # Gateway authentication dependency & rate limit checks
│   │   ├── exceptions.py             # Custom exception hierarchy (AIGatewayError base)
│   │   ├── logging.py                # Loguru setup (JSON / text format)
│   │   └── middleware.py             # Request logging middleware (method, path, status, ms)
│   │
│   ├── providers/                    # Provider Layer — AI integrations
│   │   ├── __init__.py               # Provider factory: create_provider()
│   │   ├── base.py                   # BaseProvider ABC (generate, stream, embedding, close)
│   │   ├── ollama.py                 # OllamaProvider (httpx → Ollama HTTP API)
│   │   └── gemini.py                 # GeminiProvider (google-genai SDK)
│   │
│   ├── schemas/                      # Pydantic V2 data contracts
│   │   ├── __init__.py
│   │   ├── common.py                 # ProviderEnum (ollama, gemini)
│   │   ├── requests.py               # GenerateRequest, StreamRequest, EmbeddingRequest
│   │   └── responses.py              # GenerateResponse, EmbeddingResponse, ModelInfo, ErrorResponse, UsageInfo
│   │
│   ├── services/                     # Service Layer — business logic
│   │   ├── __init__.py
│   │   ├── generator.py              # GeneratorService (central orchestrator)
│   │   ├── key_manager.py            # KeyManager (round-robin API key rotation + blacklist)
│   │   ├── model_registry.py         # ModelRegistry + ModelCapability dataclass
│   │   ├── rate_limiter.py           # In-memory sliding window rate limiter
│   │   ├── session_manager.py        # In-memory chat session store and history manager
│   │   ├── cache_service.py          # CacheService (In-memory LRU cache)
│   │   ├── health_checker.py         # Background provider probing and status tracking
│   │   └── batch_service.py          # Concurrent batch processing with semaphore control
│   │
│   └── utils/                        # Shared utilities
│       ├── __init__.py
│       └── image.py                  # Image processing (base64 strip, MIME detect, validate)
│
├── tests/                            # Test suite
│   ├── __init__.py
│   ├── conftest.py                   # Shared fixtures
│   ├── test_api/                     # API-level tests (scaffolded)
│   ├── test_providers/               # Provider tests (scaffolded)
│   └── test_services/                # Service tests (scaffolded)
│
├── plan/                             # Development plans & documentation
│   ├── ROADMAP.md                    # Master roadmap (Phase 1 + Phase 2)
│   ├── blueprint/                    # Architecture blueprint docs (8 files)
│   ├── current_version/              # ← Current state snapshot (you are here)
│   ├── beta0.1.1-foundation-core/
│   ├── beta0.1.2-schema-model-registry/
│   ├── beta0.1.3-provider-ollama/
│   ├── beta0.1.4-provider-gemini/
│   ├── beta0.1.5-streaming-adapter/
│   ├── beta0.1.6-embedding-endpoint/
│   ├── beta0.1.7-multimodal-handling/
│   ├── beta0.1.8-provider-testing/
│   ├── beta0.1.9-dynamic-api-keys/
│   ├── beta0.2.1-auth-rate-limiting/     # ✅ Done
│   ├── beta0.2.2-conversation-history/   # ✅ Done
│   ├── beta0.2.3-provider-health-check/  # ✅ Done
│   ├── beta0.2.4-caching-layer/          # ✅ Done
│   └── beta0.2.5-batch-processing/       # ✅ Done
│
├── venv/                             # Python virtual environment
├── .env                              # Environment variables (secrets, not committed)
├── .env.example                      # Env template for new developers
├── .gitignore
├── pyproject.toml                    # Build config (setuptools)
├── requirements.txt                  # Pinned dependencies
└── how_to_run.md                     # Setup & run instructions
```

---

## Key Components

### Entry Point

| File | Role |
|------|------|
| `app/main.py` | FastAPI app creation, lifespan (startup/shutdown with background tasks), CORS, middleware registration, global exception handlers, health endpoints |

### Configuration

| File | Role |
|------|------|
| `app/config.py` | `Settings` class via `pydantic-settings`, loads from `.env`, exposes singleton `settings` |
| `.env` / `.env.example` | Runtime config: Ollama URL, Gemini API keys, log level, timeouts |

### API Layer (Endpoints)

| File | Endpoint | Role |
|------|----------|------|
| `app/api/router.py` | — | Central `APIRouter` with `/api/v1` prefix, includes all endpoint routers |
| `app/api/dependencies.py` | — | Singleton DI: `initialize_services()`, `get_generator_service()`, `get_model_registry()`, etc. |
| `app/api/endpoints/models.py` | `GET /models` | List registered models with capability flags and health filter |
| `app/api/endpoints/generate.py` | `POST /generate` | Sync text/multimodal generation |
| `app/api/endpoints/stream.py` | `POST /stream` | SSE token-by-token streaming |
| `app/api/endpoints/embedding.py` | `POST /embedding` | Vector embedding generation |
| `app/api/endpoints/chat.py` | `POST /chat`, `GET /chat/{id}/history`, `DELETE /chat/{id}` | Multi-turn chat session management |
| `app/api/endpoints/cache.py` | `GET /cache/stats`, `DELETE /cache` | Cache monitoring and management endpoints |
| `app/api/endpoints/batch.py` | `POST /batch/generate`, `POST /batch/embedding` | Batch processing with concurrent execution |

### Service Layer (Business Logic)

| File | Class | Role |
|------|-------|------|
| `app/services/generator.py` | `GeneratorService` | Central orchestrator: resolves provider → validates model → checks capability → calls provider → normalizes response |
| `app/services/model_registry.py` | `ModelRegistry` | Catalog of all models with `ModelCapability` (text/image/embedding/streaming flags) |
| `app/services/key_manager.py` | `KeyManager` | Multi-key pool with round-robin rotation, temporary blacklisting on failure, auto-recovery |
| `app/services/rate_limiter.py` | `RateLimiter` | In-memory sliding window counter for global rate limiting |
| `app/services/session_manager.py` | `SessionManager` | Manages chat sessions with CRUD, FIFO trimming, and TTL expiration |
| `app/services/cache_service.py` | `CacheService` | Manages response caching with LRU eviction and TTL expiration |
| `app/services/health_checker.py` | `HealthChecker` | Background probing for providers, tracking status, failures, and latency |
| `app/services/batch_service.py` | `BatchService` | Concurrent multi-item generation and embedding with semaphore concurrency control |

### Provider Layer (AI Integrations)

| File | Class | Role |
|------|-------|------|
| `app/providers/base.py` | `BaseProvider` | Abstract base class defining the provider contract (generate, stream, embedding, close) |
| `app/providers/__init__.py` | `create_provider()` | Factory function — the only place providers are instantiated |
| `app/providers/ollama.py` | `OllamaProvider` | Ollama integration via `httpx.AsyncClient` → HTTP API (`/api/generate`, `/api/embed`) |
| `app/providers/gemini.py` | `GeminiProvider` | Google Gemini integration via `google-genai` SDK (per-request client with key rotation) |

### Core Infrastructure

| File | Role |
|------|------|
| `app/core/auth.py` | `verify_gateway_token()` | FastAPI dependency for Bearer token validation and rate limit enforcement |
| `app/core/exceptions.py` | Custom exception hierarchy: `AIGatewayError` → `ProviderNotFoundError`, `ModelNotFoundError`, `ModelCapabilityError`, `ProviderConnectionError`, `ProviderTimeoutError`, `ProviderAPIError`, `AllKeysExhaustedError`, `AuthenticationError`, `RateLimitExceededError` |
| `app/core/logging.py` | `setup_logging()` — loguru configuration (JSON for production, colored text for dev) |
| `app/core/middleware.py` | `RequestLoggingMiddleware` — logs every HTTP request with method, path, status, duration |

### Utilities

| File | Role |
|------|------|
| `app/utils/image.py` | Image processing: `strip_data_uri()`, `detect_mime_type()`, `base64_to_bytes()`, `validate_image()` (20MB limit) |

### Schemas (Data Contracts)

| File | Models | Role |
|------|--------|------|
| `app/schemas/common.py` | `ProviderEnum` | Enum of supported providers (ollama, gemini) |
| `app/schemas/requests.py` | `GenerateRequest`, `StreamRequest`, `EmbeddingRequest`, `ChatRequest` | Request body validation with Pydantic V2 |
| `app/schemas/responses.py` | `GenerateResponse`, `EmbeddingResponse`, `ModelInfoWithAvailability`, `ErrorResponse`, `UsageInfo`, `ChatResponse`, `ChatHistoryResponse`, `HealthProvidersResponse`, `ProviderHealthDetail` | Normalized response schemas |

---

## Mapping: Features → Code

| Feature | Primary Files |
|---------|--------------|
| **Health Check** | `app/main.py` (`GET /health`, `GET /health/providers`) → `app/services/health_checker.py` |
| **Model Listing** | `app/api/endpoints/models.py` → `app/services/model_registry.py` & `health_checker.py` |
| **Text Generation** | `app/api/endpoints/generate.py` → `app/services/generator.py` → `app/providers/ollama.py` / `gemini.py` |
| **SSE Streaming** | `app/api/endpoints/stream.py` → `app/services/generator.py` → `app/providers/ollama.py` / `gemini.py` |
| **Embedding** | `app/api/endpoints/embedding.py` → `app/services/generator.py` → `app/providers/ollama.py` / `gemini.py` |
| **Chat History** | `app/api/endpoints/chat.py` → `app/services/session_manager.py` |
| **Multimodal (Image Input)** | `app/utils/image.py` + `app/providers/ollama.py` (strip_data_uri) + `app/providers/gemini.py` (base64_to_bytes + MIME) |
| **Response Caching** | `app/services/cache_service.py` → used by `GeneratorService` & `app/api/endpoints/cache.py` |
| **Dynamic API Keys** | `app/services/key_manager.py` → used by `OllamaProvider` & `GeminiProvider` |
| **Error Handling** | `app/core/exceptions.py` → caught by global handlers in `app/main.py` |
| **Request Logging** | `app/core/middleware.py` (auto-logs every request) |
| **Config Management** | `app/config.py` → loaded from `.env` |
| **Authentication** | `app/core/auth.py` (`verify_gateway_token`) → injected in `app/api/router.py` |
| **Rate Limiting** | `app/services/rate_limiter.py` → called by `app/core/auth.py` |
| **Dependency Injection** | `app/api/dependencies.py` (singletons via FastAPI `Depends()`) |
| **Provider Factory** | `app/providers/__init__.py` (`create_provider()`) |
