# 📘 API Documentation — AI Generative Core

> **Version**: beta0.2.8  
> **Base URL**: `http://localhost:8000`  
> **API Prefix**: `/api/v1`  
> **Swagger UI**: `http://localhost:8000/docs`

---

## 📋 Table of Contents

- [1. Getting Started](#1-getting-started)
- [2. Authentication](#2-authentication)
- [3. System Endpoints](#3-system-endpoints)
- [4. Models](#4-models)
- [5. Text Generation](#5-text-generation)
- [6. Streaming (SSE)](#6-streaming-sse)
- [7. Embedding](#7-embedding)
- [8. Chat (Multi-turn)](#8-chat-multi-turn)
- [9. Batch Processing](#9-batch-processing)
- [10. Cache Management](#10-cache-management)
- [11. Error Reference](#11-error-reference)
- [12. Configuration Reference](#12-configuration-reference)

---

## 1. Getting Started

### Prerequisites

| Component | Min Version | Notes |
|-----------|-------------|-------|
| **Python** | 3.10+ | Backend runtime |
| **Ollama** | 0.4+ | Optional — not needed if using Gemini only |

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/Iman874/ai-local-api.git
cd ai-local-api

# 2. Create virtual environment
python -m venv venv

# 3. Activate (Windows)
.\venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Configure environment
copy .env.example .env
# Edit .env — set GEMINI_API_KEY, OLLAMA_API_KEYS, etc.
```

### Running the Server

Open **2 terminals**:

```bash
# Terminal 1 — Ollama (skip if Gemini-only)
ollama serve

# Terminal 2 — Backend
.\venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

Open **http://localhost:8000/docs** for interactive Swagger UI.

### Quick Test

```bash
# Health check
curl http://localhost:8000/health

# List models (no auth needed if GATEWAY_TOKEN is empty)
curl http://localhost:8000/api/v1/models
```

---

## 2. Authentication

Authentication is **optional** — controlled by the `GATEWAY_TOKEN` environment variable.

- **Empty** `GATEWAY_TOKEN` → auth disabled (development mode)
- **Non-empty** `GATEWAY_TOKEN` → all `/api/v1/*` endpoints require Bearer token

### Header Format

```
Authorization: Bearer <your-gateway-token>
```

### Example

```bash
curl -X POST http://localhost:8000/api/v1/generate \
  -H "Authorization: Bearer my-secret-token" \
  -H "Content-Type: application/json" \
  -d '{"provider": "ollama", "model": "gemma4:e2b", "input": "Hello"}'
```

### Rate Limiting

- Configured via `RATE_LIMIT_RPM` (default: 120 requests/minute)
- Set to `0` to disable
- Applies globally per server (not per-user)
- When exceeded → HTTP 429 with `Retry-After` header

---

## 3. System Endpoints

### `GET /health` — Basic Health Check

> **Auth**: Not required | **Rate Limit**: Not applied

```bash
curl http://localhost:8000/health
```

**Response** `200 OK`:
```json
{
  "status": "ok",
  "version": "0.2.8",
  "app_name": "AI Generative Core"
}
```

### `GET /health/providers` — Provider Health Status

> **Auth**: Not required | **Rate Limit**: Not applied

```bash
curl http://localhost:8000/health/providers
```

**Response** `200 OK`:
```json
{
  "status": "healthy",
  "providers": {
    "ollama": {
      "status": "up",
      "last_check": "2026-04-23T09:00:00+00:00",
      "last_success": "2026-04-23T09:00:00+00:00",
      "latency_ms": 12.5,
      "consecutive_failures": 0,
      "error": null
    },
    "gemini": {
      "status": "up",
      "last_check": "2026-04-23T09:00:00+00:00",
      "last_success": "2026-04-23T09:00:00+00:00",
      "latency_ms": 245.3,
      "consecutive_failures": 0,
      "error": null
    }
  },
  "summary": {
    "total": 2,
    "up": 2,
    "down": 0,
    "degraded": 0
  }
}
```

**Overall status logic**:
- `healthy` → all providers UP
- `degraded` → at least one DOWN, but not all
- `unhealthy` → all providers DOWN

---

## 4. Models

### `GET /api/v1/models` — List Available Models

> **Auth**: Required (if enabled) | **Rate Limit**: Applied

**Query Parameters**:

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `provider` | string | `null` | Filter by provider (`ollama`, `gemini`) |
| `include_unavailable` | bool | `false` | Include models from DOWN providers |

```bash
curl http://localhost:8000/api/v1/models
curl "http://localhost:8000/api/v1/models?provider=gemini"
curl "http://localhost:8000/api/v1/models?include_unavailable=true"
```

**Response** `200 OK`:
```json
[
  {
    "name": "gemma4:e2b",
    "provider": "ollama",
    "supports_text": true,
    "supports_image": false,
    "supports_embedding": false,
    "supports_reasoning": false,
    "available": true
  },
  {
    "name": "qwen3-embedding:0.6b",
    "provider": "ollama",
    "supports_text": false,
    "supports_image": false,
    "supports_embedding": true,
    "supports_reasoning": false,
    "available": true
  },
  {
    "name": "gemini-2.5-pro",
    "provider": "gemini",
    "supports_text": true,
    "supports_image": true,
    "supports_embedding": false,
    "supports_reasoning": false,
    "available": true
  },
  {
    "name": "text-embedding-004",
    "provider": "gemini",
    "supports_text": false,
    "supports_image": false,
    "supports_embedding": true,
    "supports_reasoning": false,
    "available": true
  }
]
```

### Default Registered Models

| Model | Provider | Text | Image | Embedding | Reasoning |
|-------|----------|------|-------|-----------|-----------|
| `gemma4:e2b` | ollama | ✅ | ❌ | ❌ | ❌ |
| `qwen3-embedding:0.6b` | ollama | ❌ | ❌ | ✅ | ❌ |
| `gemini-2.5-pro` | gemini | ✅ | ✅ | ❌ | ❌ |
| `gemini-3.0-pro-preview` | gemini | ✅ | ✅ | ❌ | ✅ |
| `gemini-3.1-flash-preview` | gemini | ✅ | ✅ | ❌ | ❌ |
| `text-embedding-004` | gemini | ❌ | ❌ | ✅ | ❌ |
| `deepseek-ai/deepseek-v3.2` | nvidia | ✅ | ❌ | ❌ | ✅ |

---

## 5. Text Generation

### `POST /api/v1/generate` — Generate Text

> **Auth**: Required | **Rate Limit**: Applied | **Caching**: ✅ Enabled

**Request Body**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `provider` | string | ✅ | `"ollama"` or `"gemini"` |
| `model` | string | ✅ | Model name |
| `input` | string | ✅ | Prompt text (min 1 char) |
| `images` | string[] | ❌ | Base64-encoded images (multimodal) |
| `stream` | bool | ❌ | Ignored — use `/stream` endpoint instead |

**Example — Text Generation**:
```bash
curl -X POST http://localhost:8000/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "ollama",
    "model": "gemma4:e2b",
    "input": "Explain what is machine learning in 2 sentences."
  }'
```

**Response** `200 OK`:
```json
{
  "output": "Machine learning is a subset of artificial intelligence where systems learn patterns from data without being explicitly programmed. It enables computers to improve their performance on tasks through experience and statistical analysis.",
  "provider": "ollama",
  "model": "gemma4:e2b",
  "usage": {
    "prompt_tokens": 15,
    "completion_tokens": 42,
    "total_tokens": 57
  },
  "metadata": {
    "cached": false
  }
}
```

**Example — Multimodal (Image + Text, Gemini only)**:
```bash
curl -X POST http://localhost:8000/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "gemini",
    "model": "gemini-2.5-pro",
    "input": "Describe what you see in this image",
    "images": ["iVBORw0KGgoAAAANSUhEUg...base64..."]
  }'
```

> **Note**: If the response is cached, `metadata.cached` will be `true` and the response will be instant.

---

## 6. Streaming (SSE)

### `POST /api/v1/stream` — Stream Tokens via SSE

> **Auth**: Required | **Rate Limit**: Applied | **Caching**: ❌ Not cached

**Request Body**: Same as `/generate` but without `stream` field.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `provider` | string | ✅ | `"ollama"` or `"gemini"` |
| `model` | string | ✅ | Model name |
| `input` | string | ✅ | Prompt text |
| `images` | string[] | ❌ | Base64-encoded images |

**Example**:
```bash
curl -X POST http://localhost:8000/api/v1/stream \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "provider": "ollama",
    "model": "gemma4:e2b",
    "input": "Write a haiku about coding"
  }'
```

**SSE Response** (chunked):
```
data: {"token": "Lines"}
data: {"token": " of"}
data: {"token": " code"}
data: {"token": " flow"}
data: {"token": " like"}
data: {"token": " water"}
data: [DONE]
```

**JavaScript Client**:
```javascript
const response = await fetch('/api/v1/stream', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    provider: 'ollama',
    model: 'gemma4:e2b',
    input: 'Hello world'
  })
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  const text = decoder.decode(value);
  // Parse SSE lines: "data: {...}\n\n"
  for (const line of text.split('\n')) {
    if (line.startsWith('data: ')) {
      const data = line.slice(6);
      if (data === '[DONE]') break;
      const { token } = JSON.parse(data);
      process.stdout.write(token); // append to UI
    }
  }
}
```

---

## 7. Embedding

### `POST /api/v1/embedding` — Generate Vector Embedding

> **Auth**: Required | **Rate Limit**: Applied | **Caching**: ✅ Enabled

**Request Body**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `provider` | string | ✅ | `"ollama"` or `"gemini"` |
| `model` | string | ✅ | Embedding model name |
| `input` | string | ✅ | Text to embed (min 1 char) |

> **Important**: The model must have `supports_embedding: true`. Using a text-generation model will return HTTP 400.

**Example**:
```bash
curl -X POST http://localhost:8000/api/v1/embedding \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "ollama",
    "model": "qwen3-embedding:0.6b",
    "input": "Machine learning is fascinating"
  }'
```

**Response** `200 OK`:
```json
{
  "embedding": [0.0123, -0.0456, 0.0789, ...],
  "provider": "ollama",
  "model": "qwen3-embedding:0.6b"
}
```

> The embedding vector dimension depends on the model (e.g., 1024 for qwen3-embedding, 768 for text-embedding-004).

---

## 8. Chat (Multi-turn)

### `POST /api/v1/chat` — Send Chat Message

> **Auth**: Required | **Rate Limit**: Applied

Server manages conversation history. Send `session_id: null` to start a new session, or provide an existing session ID to continue.

**Request Body**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `provider` | string | ✅ | `"ollama"` or `"gemini"` |
| `model` | string | ✅ | Model name |
| `message` | string | ✅ | User message (min 1 char) |
| `session_id` | string | ❌ | `null` = new session, or existing session ID |
| `system_prompt` | string | ❌ | System prompt (only for new sessions) |

**Example — New Session**:
```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "ollama",
    "model": "gemma4:e2b",
    "message": "What is Python?",
    "session_id": null,
    "system_prompt": "You are a helpful programming tutor."
  }'
```

**Response** `200 OK`:
```json
{
  "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "output": "Python is a high-level, interpreted programming language...",
  "provider": "ollama",
  "model": "gemma4:e2b",
  "usage": {
    "prompt_tokens": 25,
    "completion_tokens": 80,
    "total_tokens": 105
  },
  "turn_count": 2,
  "metadata": null
}
```

**Example — Continue Session**:
```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "ollama",
    "model": "gemma4:e2b",
    "message": "What are its main advantages?",
    "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
  }'
```

### `GET /api/v1/chat/{session_id}/history` — Get History

```bash
curl http://localhost:8000/api/v1/chat/a1b2c3d4-e5f6-7890-abcd-ef1234567890/history
```

**Response** `200 OK`:
```json
{
  "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "provider": "ollama",
  "model": "gemma4:e2b",
  "messages": [
    {
      "role": "system",
      "content": "You are a helpful programming tutor.",
      "timestamp": "2026-04-23T09:00:00",
      "model": null
    },
    {
      "role": "user",
      "content": "What is Python?",
      "timestamp": "2026-04-23T09:00:01",
      "model": null
    },
    {
      "role": "assistant",
      "content": "Python is a high-level...",
      "timestamp": "2026-04-23T09:00:05",
      "model": "gemma4:e2b"
    }
  ],
  "created_at": "2026-04-23T09:00:00",
  "last_active": "2026-04-23T09:00:05",
  "turn_count": 3
}
```

### `DELETE /api/v1/chat/{session_id}` — Delete Session

```bash
curl -X DELETE http://localhost:8000/api/v1/chat/a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

**Response** `200 OK`:
```json
{
  "status": "deleted",
  "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

> Sessions auto-expire after `CHAT_SESSION_TTL` minutes (default 30). Background cleanup runs every 5 minutes.

---

## 9. Batch Processing

Process multiple prompts or texts in a single request with concurrent execution. Each item is processed independently — partial failures are captured per-item without affecting other items.

### `POST /api/v1/batch/generate` — Batch Text Generation

> **Auth**: Required | **Rate Limit**: Applied (once per batch) | **Caching**: ✅ Per-item

**Request Body**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `provider` | string | ✅ | `"ollama"` or `"gemini"` |
| `model` | string | ✅ | Model name |
| `items` | array | ✅ | List of items (min 1, max `BATCH_MAX_SIZE`) |
| `items[].input` | string | ✅ | Prompt text |
| `items[].images` | string[] | ❌ | Base64-encoded images |

**Example**:
```bash
curl -X POST http://localhost:8000/api/v1/batch/generate \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "ollama",
    "model": "gemma4:e2b",
    "items": [
      {"input": "What is Python?"},
      {"input": "What is JavaScript?"},
      {"input": "What is Rust?"}
    ]
  }'
```

**Response** `200 OK`:
```json
{
  "provider": "ollama",
  "model": "gemma4:e2b",
  "total": 3,
  "succeeded": 3,
  "failed": 0,
  "results": [
    {
      "index": 0,
      "status": "success",
      "output": "Python is a high-level programming language...",
      "usage": {"prompt_tokens": 8, "completion_tokens": 30, "total_tokens": 38},
      "error": null,
      "cached": false
    },
    {
      "index": 1,
      "status": "success",
      "output": "JavaScript is a dynamic scripting language...",
      "usage": {"prompt_tokens": 8, "completion_tokens": 28, "total_tokens": 36},
      "error": null,
      "cached": false
    },
    {
      "index": 2,
      "status": "success",
      "output": "Rust is a systems programming language...",
      "usage": {"prompt_tokens": 8, "completion_tokens": 25, "total_tokens": 33},
      "error": null,
      "cached": true
    }
  ]
}
```

**Partial Failure Example** (item 1 fails):
```json
{
  "provider": "ollama",
  "model": "gemma4:e2b",
  "total": 3,
  "succeeded": 2,
  "failed": 1,
  "results": [
    {"index": 0, "status": "success", "output": "...", "usage": {...}, "error": null, "cached": false},
    {"index": 1, "status": "error", "output": null, "usage": null, "error": "Provider timeout after 120s", "cached": false},
    {"index": 2, "status": "success", "output": "...", "usage": {...}, "error": null, "cached": false}
  ]
}
```

### `POST /api/v1/batch/embedding` — Batch Embedding

**Request Body**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `provider` | string | ✅ | `"ollama"` or `"gemini"` |
| `model` | string | ✅ | Embedding model name |
| `inputs` | string[] | ✅ | List of texts (min 1, max `BATCH_MAX_SIZE`) |

**Example**:
```bash
curl -X POST http://localhost:8000/api/v1/batch/embedding \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "ollama",
    "model": "qwen3-embedding:0.6b",
    "inputs": [
      "Machine learning",
      "Deep learning",
      "Natural language processing"
    ]
  }'
```

**Response** `200 OK`:
```json
{
  "provider": "ollama",
  "model": "qwen3-embedding:0.6b",
  "total": 3,
  "succeeded": 3,
  "failed": 0,
  "results": [
    {"index": 0, "status": "success", "embedding": [0.012, -0.045, ...], "error": null, "cached": false},
    {"index": 1, "status": "success", "embedding": [0.034, -0.078, ...], "error": null, "cached": false},
    {"index": 2, "status": "success", "embedding": [0.056, -0.012, ...], "error": null, "cached": false}
  ]
}
```

### Batch Limits

| Config | Default | Description |
|--------|---------|-------------|
| `BATCH_MAX_SIZE` | 20 | Max items per batch request |
| `BATCH_CONCURRENCY` | 5 | Max concurrent provider calls within a batch |

If batch size exceeds `BATCH_MAX_SIZE` → HTTP 400 `BATCH_TOO_LARGE`.

---

## 10. Cache Management

Responses from `/generate` and `/embedding` are cached in-memory using LRU eviction with TTL.

### `GET /api/v1/cache/stats` — Cache Statistics

```bash
curl http://localhost:8000/api/v1/cache/stats
```

**Response** `200 OK`:
```json
{
  "total_hits": 150,
  "total_misses": 420,
  "hit_rate": 0.2632,
  "current_size": 85,
  "max_size": 1000,
  "evictions": 0
}
```

### `DELETE /api/v1/cache` — Clear Cache

```bash
curl -X DELETE http://localhost:8000/api/v1/cache
```

**Response** `200 OK`:
```json
{
  "message": "Cache cleared",
  "entries_removed": 85
}
```

### Cache Configuration

| Config | Default | Description |
|--------|---------|-------------|
| `CACHE_ENABLED` | `true` | Master switch for caching |
| `CACHE_TTL` | `300` | Entry TTL in seconds (5 minutes) |
| `CACHE_MAX_SIZE` | `1000` | Max entries before LRU eviction |

---

## 11. Error Reference

All errors return a consistent JSON structure:

```json
{
  "error": "Human-readable error message",
  "code": "MACHINE_READABLE_CODE"
}
```

### Error Codes

| Code | HTTP | Description |
|------|------|-------------|
| `PROVIDER_NOT_FOUND` | 404 | Provider doesn't exist or is disabled |
| `MODEL_NOT_FOUND` | 404 | Model not registered in registry |
| `SESSION_NOT_FOUND` | 404 | Chat session expired or doesn't exist |
| `CAPABILITY_NOT_SUPPORTED` | 400 | Model doesn't support requested capability |
| `BATCH_TOO_LARGE` | 400 | Batch size exceeds `BATCH_MAX_SIZE` |
| `AUTHENTICATION_FAILED` | 401 | Missing or invalid Bearer token |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests (check `Retry-After` header) |
| `ALL_KEYS_EXHAUSTED` | 503 | All API keys rate-limited or blacklisted |
| `PROVIDER_CONNECTION_ERROR` | 502 | Cannot connect to provider |
| `PROVIDER_TIMEOUT` | 504 | Provider request timed out |
| `PROVIDER_API_ERROR` | 502 | Provider returned an error response |

### Error Examples

**401 — Authentication Failed**:
```json
{
  "error": "Authentication failed: missing or invalid token",
  "code": "AUTHENTICATION_FAILED"
}
```

**429 — Rate Limit Exceeded** (includes headers):
```
HTTP/1.1 429 Too Many Requests
Retry-After: 60
X-RateLimit-Limit: 120

{"error": "Rate limit exceeded: max 120 requests/minute", "code": "RATE_LIMIT_EXCEEDED"}
```

**400 — Batch Too Large**:
```json
{
  "error": "Batch size 25 exceeds maximum 20",
  "code": "BATCH_TOO_LARGE"
}
```

**404 — Model Not Found**:
```json
{
  "error": "Model 'fake-model' not found for provider 'ollama'",
  "code": "MODEL_NOT_FOUND"
}
```

---

## 12. Configuration Reference

All settings are configured via `.env` file or environment variables.

| Variable | Default | Description |
|----------|---------|-------------|
| **App** | | |
| `APP_NAME` | `AI Generative Core` | Application display name |
| `APP_VERSION` | `0.2.5` | Current version |
| `DEBUG` | `false` | Debug mode |
| **Providers** | | |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_TIMEOUT` | `120` | Ollama request timeout (seconds) |
| `OLLAMA_API_KEYS` | `` | Ollama Cloud API keys (comma-separated) |
| `GEMINI_API_KEY` | `` | Single Gemini API key |
| `GEMINI_API_KEYS` | `` | Multiple Gemini keys (comma-separated, priority) |
| `GEMINI_TIMEOUT` | `120` | Gemini request timeout (seconds) |
| **Auth** | | |
| `GATEWAY_TOKEN` | `` | Static service token (empty = auth disabled) |
| `RATE_LIMIT_RPM` | `120` | Max requests/minute (0 = unlimited) |
| **Chat** | | |
| `CHAT_MAX_HISTORY` | `50` | Max messages per session |
| `CHAT_SESSION_TTL` | `30` | Session TTL in minutes |
| **Cache** | | |
| `CACHE_ENABLED` | `true` | Enable/disable response caching |
| `CACHE_TTL` | `300` | Cache entry TTL in seconds |
| `CACHE_MAX_SIZE` | `1000` | Max cache entries (LRU eviction) |
| **Health Check** | | |
| `HEALTH_CHECK_INTERVAL` | `30` | Seconds between health probes |
| `HEALTH_CHECK_TIMEOUT` | `5` | Probe timeout in seconds |
| `HEALTH_CHECK_THRESHOLD` | `3` | Failures before marking DOWN |
| **Batch** | | |
| `BATCH_MAX_SIZE` | `20` | Max items per batch request |
| `BATCH_CONCURRENCY` | `5` | Max concurrent calls within a batch |
| **Logging** | | |
| `LOG_LEVEL` | `INFO` | Log level (DEBUG, INFO, WARNING, ERROR) |
| `LOG_FORMAT` | `json` | Log format (`json` or `text`) |

---

## API Endpoint Summary

| Method | Endpoint | Tag | Description |
|--------|----------|-----|-------------|
| `GET` | `/health` | System | Basic health check |
| `GET` | `/health/providers` | System | Provider health status |
| `GET` | `/api/v1/models` | Models | List available models |
| `POST` | `/api/v1/generate` | Generation | Text/multimodal generation |
| `POST` | `/api/v1/stream` | Streaming | SSE token streaming |
| `POST` | `/api/v1/embedding` | Embedding | Vector embedding |
| `POST` | `/api/v1/chat` | Chat | Multi-turn conversation |
| `GET` | `/api/v1/chat/{id}/history` | Chat | Get session history |
| `DELETE` | `/api/v1/chat/{id}` | Chat | Delete session |
| `POST` | `/api/v1/batch/generate` | Batch | Batch text generation |
| `POST` | `/api/v1/batch/embedding` | Batch | Batch embedding |
| `GET` | `/api/v1/cache/stats` | Cache | Cache statistics |
| `DELETE` | `/api/v1/cache` | Cache | Clear cache |

---

> **Auto-generated for AI Generative Core beta0.2.8** — For interactive exploration, visit the Swagger UI at `http://localhost:8000/docs`.
