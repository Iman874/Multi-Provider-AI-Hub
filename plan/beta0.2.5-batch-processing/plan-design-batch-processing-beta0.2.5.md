# Blueprint: AI Generative Core — Batch Processing (beta0.2.5)

## 1. Visi & Tujuan

Saat ini, setiap request generate/embedding hanya bisa memproses **satu prompt per request**. Untuk use case SaaS yang membutuhkan processing massal — misalnya:

1. **Embedding pipeline**: Index 100 dokumen sekaligus untuk RAG
2. **Bulk generation**: Proses banyak prompt untuk content pipeline
3. **A/B testing**: Jalankan prompt yang sama ke beberapa model sekaligus

Client harus mengirim N request terpisah, yang mengakibatkan:
- **N kali HTTP overhead** (connection, auth, rate limit check)
- **Tidak atomic** — sebagian bisa gagal, sebagian berhasil
- **Sulit di-manage** — client harus track progress masing-masing

Modul **beta0.2.5** membangun **Batch Processing Layer**:
- `POST /api/v1/batch/generate` — Multiple prompts, satu request, concurrent execution
- `POST /api/v1/batch/embedding` — Multiple texts, satu request, batch embedding
- Setiap item di-process secara **concurrent** (asyncio.gather) dengan configurable concurrency limit
- Partial failure handling — item yang gagal tetap mengembalikan error detail, yang berhasil tetap di-return
- Integrasi dengan **CacheService** — setiap item di-check cache secara individual
- Integrasi dengan **HealthChecker** — skip provider yang DOWN secara otomatis
- Configurable via `.env`: max batch size dan concurrency limit

---

## 2. Scope Development

### ✅ Yang Dikerjakan
- **BatchGenerateRequest schema**: List of items, shared provider/model atau per-item override
- **BatchEmbeddingRequest schema**: List of input texts
- **BatchGenerateResponse schema**: List of results with per-item status
- **BatchEmbeddingResponse schema**: List of embeddings with per-item status
- **BatchService**: Orchestrator dengan concurrency control via asyncio.Semaphore
- **Batch endpoints**: `POST /batch/generate`, `POST /batch/embedding`
- **Config**: `BATCH_MAX_SIZE`, `BATCH_CONCURRENCY`
- **Unit Tests**: 10+ tests

### ❌ Yang Tidak Dikerjakan
- Background job / async queue (semua batch diproses synchronously dalam satu request)
- Webhook callback setelah selesai
- Priority queue / scheduling
- Per-item streaming (batch = non-streaming only)
- Cross-provider batch (satu batch = satu provider, satu model)

---

## 3. Arsitektur & Desain

### 3.1. Konfigurasi (`.env`)

```env
# --- Batch Processing ---
BATCH_MAX_SIZE=20         # Maximum items per batch request
BATCH_CONCURRENCY=5       # Max concurrent provider calls within a batch
```

**Config di `app/config.py`**:
```python
# --- Batch Processing ---
BATCH_MAX_SIZE: int = 20
BATCH_CONCURRENCY: int = 5
```

### 3.2. Request Schemas

```python
class BatchGenerateItem(BaseModel):
    """Single item in a batch generate request."""

    input: str = Field(
        ..., min_length=1, description="Text prompt for generation"
    )
    images: Optional[list[str]] = Field(
        default=None,
        description="Optional images for multimodal input",
    )


class BatchGenerateRequest(BaseModel):
    """Request body for POST /batch/generate."""

    provider: ProviderEnum = Field(
        ..., description="AI provider to use"
    )
    model: str = Field(
        ..., description="Model name"
    )
    items: list[BatchGenerateItem] = Field(
        ...,
        min_length=1,
        description="List of prompts to generate",
    )


class BatchEmbeddingRequest(BaseModel):
    """Request body for POST /batch/embedding."""

    provider: ProviderEnum = Field(
        ..., description="AI provider to use"
    )
    model: str = Field(
        ..., description="Embedding model name"
    )
    inputs: list[str] = Field(
        ...,
        min_length=1,
        description="List of texts to embed",
    )
```

### 3.3. Response Schemas

```python
class BatchItemStatus(str, Enum):
    """Status of an individual batch item."""
    success = "success"
    error = "error"


class BatchGenerateResult(BaseModel):
    """Result for a single item in batch generate."""

    index: int = Field(..., description="Original index in request")
    status: str = Field(..., description="'success' or 'error'")
    output: Optional[str] = Field(None, description="Generated text (on success)")
    usage: Optional[UsageInfo] = Field(None, description="Token usage (on success)")
    error: Optional[str] = Field(None, description="Error message (on failure)")
    cached: bool = Field(False, description="Whether result was from cache")


class BatchGenerateResponse(BaseModel):
    """Response for POST /batch/generate."""

    provider: str = Field(..., description="Provider used")
    model: str = Field(..., description="Model used")
    total: int = Field(..., description="Total items submitted")
    succeeded: int = Field(..., description="Items that succeeded")
    failed: int = Field(..., description="Items that failed")
    results: list[BatchGenerateResult] = Field(
        ..., description="Per-item results (ordered by index)"
    )


class BatchEmbeddingResult(BaseModel):
    """Result for a single item in batch embedding."""

    index: int = Field(..., description="Original index in request")
    status: str = Field(..., description="'success' or 'error'")
    embedding: Optional[list[float]] = Field(None, description="Vector (on success)")
    error: Optional[str] = Field(None, description="Error message (on failure)")
    cached: bool = Field(False, description="Whether result was from cache")


class BatchEmbeddingResponse(BaseModel):
    """Response for POST /batch/embedding."""

    provider: str = Field(..., description="Provider used")
    model: str = Field(..., description="Model used")
    total: int = Field(..., description="Total items submitted")
    succeeded: int = Field(..., description="Items that succeeded")
    failed: int = Field(..., description="Items that failed")
    results: list[BatchEmbeddingResult] = Field(
        ..., description="Per-item results (ordered by index)"
    )
```

### 3.4. BatchService (`app/services/batch_service.py`)

```
┌──────────────────────────────────────────────────────────┐
│                     BatchService                          │
├──────────────────────────────────────────────────────────┤
│ _generator: GeneratorService                              │
│ _max_size: int                                            │
│ _concurrency: int                                         │
│ _semaphore: asyncio.Semaphore                             │
├──────────────────────────────────────────────────────────┤
│ generate_batch(request) → BatchGenerateResponse           │
│ embedding_batch(request) → BatchEmbeddingResponse         │
│ _process_generate_item(index, item, provider, model)      │
│ _process_embedding_item(index, text, provider, model)     │
└──────────────────────────────────────────────────────────┘
```

**Flow `generate_batch()`:**
```python
async def generate_batch(self, request: BatchGenerateRequest) -> BatchGenerateResponse:
    # 1. Validate batch size
    if len(request.items) > self._max_size:
        raise BatchTooLargeError(len(request.items), self._max_size)

    # 2. Validate provider & model ONCE (fail fast)
    provider = self._generator._get_provider(request.provider.value)
    model_info = self._generator._registry.get_model(
        provider=request.provider.value,
        name=request.model,
    )

    # 3. Process all items concurrently with semaphore
    tasks = [
        self._process_generate_item(i, item, request.provider, request.model)
        for i, item in enumerate(request.items)
    ]
    results = await asyncio.gather(*tasks, return_exceptions=False)

    # 4. Build response
    succeeded = sum(1 for r in results if r.status == "success")
    return BatchGenerateResponse(
        provider=request.provider.value,
        model=request.model,
        total=len(results),
        succeeded=succeeded,
        failed=len(results) - succeeded,
        results=sorted(results, key=lambda r: r.index),
    )
```

**Flow `_process_generate_item()`:**
```python
async def _process_generate_item(
    self, index: int, item: BatchGenerateItem,
    provider: ProviderEnum, model: str,
) -> BatchGenerateResult:
    async with self._semaphore:
        try:
            # Reuse GeneratorService.generate() — gets cache for free
            request = GenerateRequest(
                provider=provider,
                model=model,
                input=item.input,
                images=item.images,
            )
            response = await self._generator.generate(request)

            return BatchGenerateResult(
                index=index,
                status="success",
                output=response.output,
                usage=response.usage,
                cached=response.metadata.get("cached", False) if response.metadata else False,
            )
        except Exception as e:
            logger.warning(
                "Batch item {idx} failed: {err}",
                idx=index, err=str(e),
            )
            return BatchGenerateResult(
                index=index,
                status="error",
                error=str(e),
            )
```

### 3.5. Exception Baru

```python
class BatchTooLargeError(AIGatewayError):
    """Raised when batch size exceeds maximum limit."""

    def __init__(self, actual: int, maximum: int):
        super().__init__(
            message=f"Batch size {actual} exceeds maximum {maximum}",
            code="BATCH_TOO_LARGE",
        )
        self.actual = actual
        self.maximum = maximum
```

### 3.6. Batch Endpoints

**File**: `app/api/endpoints/batch.py`

```python
@router.post(
    "/batch/generate",
    response_model=BatchGenerateResponse,
    summary="Batch text generation",
    description="Process multiple prompts in a single request with concurrent execution.",
)
async def batch_generate(
    request: BatchGenerateRequest,
    batch_service: BatchService = Depends(get_batch_service),
) -> BatchGenerateResponse:
    return await batch_service.generate_batch(request)


@router.post(
    "/batch/embedding",
    response_model=BatchEmbeddingResponse,
    summary="Batch embedding generation",
    description="Generate embeddings for multiple texts in a single request.",
)
async def batch_embedding(
    request: BatchEmbeddingRequest,
    batch_service: BatchService = Depends(get_batch_service),
) -> BatchEmbeddingResponse:
    return await batch_service.embedding_batch(request)
```

### 3.7. Integration Points

**Cache Integration:**
- Setiap item dalam batch di-check cache **secara individual**
- Items yang cache HIT dikembalikan instan, sisanya di-process via provider
- Items yang berhasil di-generate disimpan ke cache satu per satu
- Ini terjadi secara otomatis karena batch memanggil `GeneratorService.generate()` yang sudah terintegrasi cache

**Health Check Integration:**
- Batch memvalidasi provider health **satu kali** di awal sebelum processing dimulai
- Jika provider DOWN → fail fast dengan `ProviderUnavailableError` (existing)

**Rate Limiting:**
- Rate limit di-check **satu kali per batch request** (bukan per item)
- Ini konsisten dengan behavior saat ini dimana auth/rate-limit berada di router level

---

## 4. Output yang Diharapkan

### `POST /api/v1/batch/generate`

**Request:**
```json
{
  "provider": "gemini",
  "model": "gemini-2.5-pro",
  "items": [
    { "input": "Apa itu Machine Learning?" },
    { "input": "Apa itu Deep Learning?" },
    { "input": "Apa itu Neural Network?" }
  ]
}
```

**Response (all success):**
```json
{
  "provider": "gemini",
  "model": "gemini-2.5-pro",
  "total": 3,
  "succeeded": 3,
  "failed": 0,
  "results": [
    {
      "index": 0,
      "status": "success",
      "output": "Machine Learning adalah cabang dari...",
      "usage": { "prompt_tokens": 10, "completion_tokens": 50, "total_tokens": 60 },
      "error": null,
      "cached": false
    },
    {
      "index": 1,
      "status": "success",
      "output": "Deep Learning adalah subset dari...",
      "usage": { "prompt_tokens": 10, "completion_tokens": 45, "total_tokens": 55 },
      "error": null,
      "cached": true
    },
    {
      "index": 2,
      "status": "success",
      "output": "Neural Network adalah model komputasi...",
      "usage": { "prompt_tokens": 10, "completion_tokens": 48, "total_tokens": 58 },
      "error": null,
      "cached": false
    }
  ]
}
```

**Response (partial failure):**
```json
{
  "provider": "ollama",
  "model": "gemma4:e2b",
  "total": 3,
  "succeeded": 2,
  "failed": 1,
  "results": [
    { "index": 0, "status": "success", "output": "...", "usage": null, "error": null, "cached": false },
    { "index": 1, "status": "error", "output": null, "usage": null, "error": "Provider timeout after 30s", "cached": false },
    { "index": 2, "status": "success", "output": "...", "usage": null, "error": null, "cached": false }
  ]
}
```

### `POST /api/v1/batch/embedding`

**Request:**
```json
{
  "provider": "gemini",
  "model": "text-embedding-004",
  "inputs": [
    "Machine learning fundamentals",
    "Deep learning architectures",
    "Natural language processing"
  ]
}
```

**Response:**
```json
{
  "provider": "gemini",
  "model": "text-embedding-004",
  "total": 3,
  "succeeded": 3,
  "failed": 0,
  "results": [
    { "index": 0, "status": "success", "embedding": [0.01, -0.03, ...], "error": null, "cached": false },
    { "index": 1, "status": "success", "embedding": [0.05, 0.02, ...], "error": null, "cached": false },
    { "index": 2, "status": "success", "embedding": [-0.01, 0.04, ...], "error": null, "cached": true }
  ]
}
```

---

## 5. Breakdowns (Daftar Task)

### Task 1 — Config, Exception & Schemas
**Files**: `app/config.py`, `app/core/exceptions.py`, `app/schemas/requests.py`, `app/schemas/responses.py`
- Config: `BATCH_MAX_SIZE`, `BATCH_CONCURRENCY`
- Exception: `BatchTooLargeError`
- Request schemas: `BatchGenerateItem`, `BatchGenerateRequest`, `BatchEmbeddingRequest`
- Response schemas: `BatchGenerateResult`, `BatchGenerateResponse`, `BatchEmbeddingResult`, `BatchEmbeddingResponse`
- **Estimasi:** 20 menit

### Task 2 — BatchService Core
**Files**: `app/services/batch_service.py`
- Class `BatchService` with `asyncio.Semaphore` for concurrency control
- `generate_batch()`: validate → gather → build response
- `embedding_batch()`: validate → gather → build response
- `_process_generate_item()`: wrap GeneratorService.generate() with error handling
- `_process_embedding_item()`: wrap GeneratorService.embedding() with error handling
- **Estimasi:** 45 menit

### Task 3 — Endpoint & Integration
**Files**: `app/api/endpoints/batch.py`, `app/api/router.py`, `app/api/dependencies.py`, `app/main.py`
- `POST /api/v1/batch/generate` → `BatchService.generate_batch()`
- `POST /api/v1/batch/embedding` → `BatchService.embedding_batch()`
- `get_batch_service()` dependency in `dependencies.py`
- Init `BatchService` in `initialize_services()`
- Register router, add `BATCH_TOO_LARGE` to exception handler status map
- **Estimasi:** 30 menit

### Task 4 — Unit Tests
**Files**: `tests/services/test_batch_service.py` (10+ tests)
1. `test_batch_generate_success` — 3 items, all succeed
2. `test_batch_embedding_success` — 3 texts, all succeed
3. `test_batch_partial_failure` — 1 fails, 2 succeed → response contains both
4. `test_batch_too_large` — exceed max size → BatchTooLargeError
5. `test_batch_single_item` — 1 item batch = same as individual request
6. `test_batch_cache_integration` — cached items returned with `cached: true`
7. `test_batch_concurrency_limit` — verify semaphore limits concurrent calls
8. `test_batch_provider_validation` — invalid provider → immediate error
9. `test_batch_model_validation` — invalid model → immediate error
10. `test_batch_empty_rejected` — empty items list rejected by Pydantic
- **Estimasi:** 45 menit

---

## 6. Timeline & Estimasi Total

| Task | Scope | Estimasi |
|---|---|---|
| Task 1 | Config, Exception & Schemas | 20 menit |
| Task 2 | BatchService Core | 45 menit |
| Task 3 | Endpoint & Integration | 30 menit |
| Task 4 | Unit Tests | 45 menit |
| **Total** | | **~2.3 jam** |

---

## 7. Acceptance Criteria Global

- [ ] `POST /api/v1/batch/generate` menerima list of items, returns per-item results
- [ ] `POST /api/v1/batch/embedding` menerima list of texts, returns per-item embeddings
- [ ] Batch size divalidasi (`BATCH_MAX_SIZE`) — exceed → 400 error
- [ ] Concurrent processing via asyncio.Semaphore (`BATCH_CONCURRENCY`)
- [ ] Partial failure: item yang gagal return error detail, yang berhasil tetap di-return
- [ ] Setiap item di-check cache secara individual (via GeneratorService)
- [ ] Response item yang cached ditandai `cached: true`
- [ ] Provider & model divalidasi SATU KALI di awal (fail fast)
- [ ] `results` array ordered by `index` (sesuai urutan input)
- [ ] `BatchTooLargeError` → HTTP 400
- [ ] Rate limit di-check sekali per batch request (bukan per item)
- [ ] Endpoints muncul di Swagger UI (`/docs`)
- [ ] Server bisa start tanpa error
- [ ] Semua existing tests tetap PASS (104 tests)
- [ ] 10+ test baru ditambahkan
