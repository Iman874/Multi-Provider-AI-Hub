# Plan-Design: NVIDIA NIM Provider — beta0.2.6

> **Version**: beta0.2.6  
> **Module**: NVIDIA NIM Provider (Exploration & Integration)  
> **Status**: 📝 Plan  
> **Depends On**: beta0.2.5  
> **Created**: 2026-04-24

---

## 1. Latar Belakang

### Apa itu NVIDIA NIM?

**NVIDIA NIM (NVIDIA Inference Microservices)** adalah layanan cloud yang menyediakan akses ke 100+ model AI melalui **OpenAI-compatible REST API**. Artinya, format endpoint-nya sama persis dengan OpenAI:

- `POST /v1/chat/completions` — Text generation
- `POST /v1/embeddings` — Vector embeddings

### Informasi API

| Parameter | Value |
|-----------|-------|
| **Base URL** | `https://integrate.api.nvidia.com/v1` |
| **Auth** | `Authorization: Bearer nvapi-...` |
| **Protocol** | OpenAI-compatible REST API |
| **Streaming** | ✅ Supported (SSE, same as OpenAI) |
| **Embeddings** | ✅ Supported (`/v1/embeddings`) |

### Mengapa penting?

1. **100+ model** — Termasuk Llama 3.x, Mistral, DeepSeek-R1, Nemotron, dll.
2. **OpenAI-compatible** — Bisa pakai format yang sudah standar
3. **Free tier** — Ada quota gratis untuk prototyping di `build.nvidia.com`
4. **Tidak perlu GPU** — Inference dijalankan di NVIDIA DGX Cloud

### Fokus Version Ini

> ⚠️ **Version ini bersifat EXPLORATORY** — tujuan utama adalah **memahami dan menguji API**, bukan feature-complete integration.

Goal:
1. Riset: request/response format aktual dari NVIDIA NIM
2. Buat exploratory script untuk test endpoint secara manual
3. Implementasi `NvidiaProvider` ke gateway architecture
4. Register beberapa model default dari NVIDIA catalog
5. Verifikasi semua flow: generate, stream, embedding

---

## 2. Riset API — Format Request/Response

### 2.1 Chat Completions (Text Generation)

**Endpoint**: `POST https://integrate.api.nvidia.com/v1/chat/completions`

**Request**:
```json
{
  "model": "nvidia/llama-3.1-nemotron-70b-instruct",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello, what is machine learning?"}
  ],
  "max_tokens": 1024,
  "temperature": 0.7,
  "stream": false
}
```

**Response**:
```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "model": "nvidia/llama-3.1-nemotron-70b-instruct",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Machine learning is a subset of AI..."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 20,
    "completion_tokens": 50,
    "total_tokens": 70
  }
}
```

### 2.2 Chat Completions (Streaming)

**Request**: Same as above but `"stream": true`

**Response** (SSE):
```
data: {"id":"chatcmpl-abc123","choices":[{"index":0,"delta":{"role":"assistant","content":"Machine"}}]}
data: {"id":"chatcmpl-abc123","choices":[{"index":0,"delta":{"content":" learning"}}]}
data: {"id":"chatcmpl-abc123","choices":[{"index":0,"delta":{"content":" is"}}]}
data: [DONE]
```

### 2.3 Embeddings

**Endpoint**: `POST https://integrate.api.nvidia.com/v1/embeddings`

**Request**:
```json
{
  "model": "nvidia/nv-embedqa-e5-v5",
  "input": "Machine learning is fascinating"
}
```

**Response**:
```json
{
  "object": "list",
  "data": [
    {
      "object": "embedding",
      "embedding": [0.012, -0.045, 0.078, ...],
      "index": 0
    }
  ],
  "model": "nvidia/nv-embedqa-e5-v5",
  "usage": {
    "prompt_tokens": 5,
    "total_tokens": 5
  }
}
```

### 2.4 Perbedaan dengan Provider Saat Ini

| Aspek | Ollama | Gemini | NVIDIA NIM |
|-------|--------|--------|------------|
| **Protocol** | Custom REST | Google GenAI SDK | OpenAI-compatible |
| **Base URL** | `localhost:11434` | (via SDK) | `integrate.api.nvidia.com/v1` |
| **Generate** | `POST /api/generate` | `client.models.generate_content()` | `POST /v1/chat/completions` |
| **Stream** | `POST /api/generate` (stream=true) | `generate_content(stream=True)` | `POST /v1/chat/completions` (stream=true) |
| **Embedding** | `POST /api/embed` | `client.models.embed_content()` | `POST /v1/embeddings` |
| **Auth** | API key (optional) | API key (required) | `Bearer nvapi-...` (required) |
| **HTTP Client** | `httpx` | `google-genai` SDK | `httpx` |

---

## 3. Arsitektur

### 3.1 Dimana NVIDIA NIM Masuk

```
app/providers/
├── base.py           # BaseProvider (abstract)
├── __init__.py       # create_provider() factory
├── ollama.py         # OllamaProvider — Custom REST
├── gemini.py         # GeminiProvider — Google SDK
└── nvidia.py         # NvidiaProvider — OpenAI-compatible REST (NEW)
```

### 3.2 NvidiaProvider Class

```python
class NvidiaProvider(BaseProvider):
    """
    NVIDIA NIM provider — OpenAI-compatible API.
    
    Base URL: https://integrate.api.nvidia.com/v1
    Auth: Bearer nvapi-...
    """
    
    def __init__(self, api_key: str, timeout: int = 120):
        self._client = httpx.AsyncClient(
            base_url="https://integrate.api.nvidia.com/v1",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
        )
    
    async def generate(self, model, prompt, images=None) -> GenerateResponse:
        # POST /chat/completions → extract choices[0].message.content
        ...
    
    async def stream(self, model, prompt, images=None) -> AsyncGenerator:
        # POST /chat/completions (stream=true) → yield delta.content
        ...
    
    async def embedding(self, model, input_text) -> EmbeddingResponse:
        # POST /embeddings → extract data[0].embedding
        ...
```

### 3.3 Config Additions

```python
# app/config.py
NVIDIA_API_KEY: str = ""           # nvapi-... key
NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
NVIDIA_TIMEOUT: int = 120
```

### 3.4 Model Registry — Default Models

Berdasarkan NVIDIA API Catalog, model-model yang akan diregister:

| Model ID | Tipe | Capabilities |
|----------|------|-------------|
| `nvidia/llama-3.1-nemotron-70b-instruct` | LLM | text, streaming |
| `meta/llama-3.3-70b-instruct` | LLM | text, streaming |
| `deepseek-ai/deepseek-r1` | Reasoning | text, streaming |
| `nvidia/nv-embedqa-e5-v5` | Embedding | embedding |

> **Note**: Daftar model ini akan divalidasi dan diupdate selama fase exploratory testing.

---

## 4. Scope

### Yang Dikerjakan

1. **Exploratory scripts** — Test API manual (generate, stream, embedding)
2. **Config** — `NVIDIA_API_KEY`, `NVIDIA_BASE_URL`, `NVIDIA_TIMEOUT`
3. **NvidiaProvider** — Implement `BaseProvider` interface (generate, stream, embedding)
4. **Provider factory** — Register `"nvidia"` di `create_provider()`
5. **Model defaults** — Register NVIDIA models di `ModelRegistry`
6. **ProviderEnum** — Tambah `"nvidia"` ke enum
7. **Unit tests** — Mock-based tests untuk NvidiaProvider
8. **Integration verification** — Manual test via Swagger UI

### Yang TIDAK Dikerjakan

- Multimodal/vision (NVIDIA vision models punya format berbeda — riset di version lain)
- API key rotation (NVIDIA pakai single key — tidak perlu KeyManager)
- Custom model listing dari NVIDIA catalog (hardcode default saja)
- Performance benchmarking vs provider lain

---

## 5. Exploratory Testing Plan

Sebelum implementasi, buat script test di `scripts/test_nvidia_api.py`:

### Test 1: Basic Connection
```python
import httpx

resp = httpx.get(
    "https://integrate.api.nvidia.com/v1/models",
    headers={"Authorization": "Bearer nvapi-..."}
)
print(resp.json())  # List available models
```

### Test 2: Chat Completion
```python
resp = httpx.post(
    "https://integrate.api.nvidia.com/v1/chat/completions",
    headers={"Authorization": "Bearer nvapi-..."},
    json={
        "model": "meta/llama-3.3-70b-instruct",
        "messages": [{"role": "user", "content": "Hello!"}],
        "max_tokens": 100
    }
)
print(resp.json())
```

### Test 3: Streaming
```python
with httpx.stream("POST", 
    "https://integrate.api.nvidia.com/v1/chat/completions",
    headers={"Authorization": "Bearer nvapi-..."},
    json={
        "model": "meta/llama-3.3-70b-instruct",
        "messages": [{"role": "user", "content": "Hello!"}],
        "max_tokens": 100,
        "stream": True
    }
) as resp:
    for line in resp.iter_lines():
        print(line)
```

### Test 4: Embedding
```python
resp = httpx.post(
    "https://integrate.api.nvidia.com/v1/embeddings",
    headers={"Authorization": "Bearer nvapi-..."},
    json={
        "model": "nvidia/nv-embedqa-e5-v5",
        "input": "Test embedding text"
    }
)
print(resp.json())
```

> **Output dari exploratory tests ini akan menentukan detail implementasi NvidiaProvider.**

---

## 6. Task Breakdown (Estimasi)

| # | Task | Scope | Estimasi |
|---|------|-------|----------|
| 1 | Exploratory Scripts & API Testing | `scripts/test_nvidia_api.py` — manual API exploration | 30 min |
| 2 | Config, Enum & Provider Skeleton | Config fields, ProviderEnum update, NvidiaProvider file | 30 min |
| 3 | NvidiaProvider Implementation | generate(), stream(), embedding() methods | 1 hr |
| 4 | Factory, Registry & Integration | create_provider(), model defaults, dependencies.py | 30 min |
| 5 | Unit Tests | Mock-based provider tests | 45 min |

**Total estimasi: ~3 jam**

---

## 7. Risiko & Mitigasi

| Risiko | Dampak | Mitigasi |
|--------|--------|---------|
| Free tier rate limit ketat | Testing terhambat | Gunakan sleep antar request, batch testing |
| Model ID berubah/deprecated | Provider error at runtime | Log warning, graceful error handling |
| Format response berbeda dari OpenAI spec | Parsing gagal | Exploratory test dulu, validasi format aktual |
| NVIDIA API down / maintenance | Provider unavailable | HealthChecker sudah handle ini otomatis |
| Embedding model tidak available di free tier | Embedding test gagal | Fallback ke text model dulu, embedding opsional |

---

## 8. Success Criteria

- [ ] Exploratory scripts berhasil test generate, stream, dan embedding
- [ ] `NvidiaProvider` implement semua method di `BaseProvider`
- [ ] `POST /api/v1/generate` dengan `provider: "nvidia"` berhasil
- [ ] `POST /api/v1/stream` dengan `provider: "nvidia"` berhasil (SSE tokens)
- [ ] `POST /api/v1/embedding` dengan `provider: "nvidia"` berhasil
- [ ] `GET /api/v1/models?provider=nvidia` menampilkan model-model NVIDIA
- [ ] Health check probe untuk NVIDIA provider berfungsi
- [ ] Unit tests PASS
- [ ] Semua existing tests tetap PASS (zero regression)
- [ ] Server start tanpa error saat `NVIDIA_API_KEY` kosong (provider di-skip)
