# Task 1 — Config, Exception & Schemas

## 1. Judul Task
Tambah konfigurasi batch, exception `BatchTooLargeError`, dan semua Pydantic request/response schemas untuk batch processing

## 2. Deskripsi
Menyiapkan fondasi data layer untuk fitur batch processing: environment config, custom exception untuk validasi batch size, dan semua Pydantic V2 schemas yang mendefinisikan kontrak request/response untuk `POST /batch/generate` dan `POST /batch/embedding`.

## 3. Tujuan Teknis
- `BATCH_MAX_SIZE` dan `BATCH_CONCURRENCY` bisa di-configure via `.env`
- `BatchTooLargeError` tersedia sebagai exception class
- Request schemas: `BatchGenerateItem`, `BatchGenerateRequest`, `BatchEmbeddingRequest`
- Response schemas: `BatchGenerateResult`, `BatchGenerateResponse`, `BatchEmbeddingResult`, `BatchEmbeddingResponse`

## 4. Scope

### Yang dikerjakan
- `app/config.py` — tambah 2 field baru
- `.env` dan `.env.example` — tambah 2 environment variable baru
- `app/core/exceptions.py` — tambah class `BatchTooLargeError`
- `app/schemas/requests.py` — tambah 3 class baru
- `app/schemas/responses.py` — tambah 4 class baru
- `app/main.py` — tambah `BATCH_TOO_LARGE` ke `status_map` di exception handler

### Yang TIDAK dikerjakan
- BatchService (Task 2)
- Endpoints & router (Task 3)
- Unit tests (Task 4)

## 5. Langkah Implementasi

### Step 1: Tambah config fields di `app/config.py`
Tambahkan di akhir class `Settings`, setelah field `HEALTH_CHECK_*`:

```python
# --- Batch Processing ---
BATCH_MAX_SIZE: int = 20
BATCH_CONCURRENCY: int = 5
```

### Step 2: Tambah environment variables di `.env` dan `.env.example`
Tambahkan di akhir file:

```env
# --- Batch Processing ---
BATCH_MAX_SIZE=20
BATCH_CONCURRENCY=5
```

### Step 3: Tambah `BatchTooLargeError` di `app/core/exceptions.py`
Tambahkan di akhir file, setelah `RateLimitExceededError`:

```python
class BatchTooLargeError(AIGatewayError):
    """Raised when batch size exceeds the configured maximum limit."""

    def __init__(self, actual: int, maximum: int):
        super().__init__(
            message=f"Batch size {actual} exceeds maximum {maximum}",
            code="BATCH_TOO_LARGE",
        )
        self.actual = actual
        self.maximum = maximum
```

### Step 4: Tambah request schemas di `app/schemas/requests.py`
Tambahkan di akhir file, setelah class `ChatRequest`:

```python
class BatchGenerateItem(BaseModel):
    """Single item in a batch generate request."""

    input: str = Field(
        ...,
        min_length=1,
        description="Text prompt for generation",
    )
    images: Optional[list[str]] = Field(
        default=None,
        description="Optional list of base64-encoded images for multimodal input",
    )


class BatchGenerateRequest(BaseModel):
    """Request body for POST /batch/generate."""

    provider: ProviderEnum = Field(
        ...,
        description="AI provider to use",
        examples=["ollama", "gemini"],
    )
    model: str = Field(
        ...,
        description="Model name",
        examples=["llama3.2", "gemini-2.5-pro"],
    )
    items: list[BatchGenerateItem] = Field(
        ...,
        min_length=1,
        description="List of prompts to generate",
    )


class BatchEmbeddingRequest(BaseModel):
    """Request body for POST /batch/embedding."""

    provider: ProviderEnum = Field(
        ...,
        description="AI provider to use",
        examples=["ollama", "gemini"],
    )
    model: str = Field(
        ...,
        description="Embedding model name",
        examples=["nomic-embed-text", "text-embedding-004"],
    )
    inputs: list[str] = Field(
        ...,
        min_length=1,
        description="List of texts to embed",
    )
```

### Step 5: Tambah response schemas di `app/schemas/responses.py`
Tambahkan di akhir file, setelah class `HealthProvidersResponse`:

```python
class BatchGenerateResult(BaseModel):
    """Result for a single item in batch generate."""

    index: int = Field(..., description="Original index in request")
    status: str = Field(..., description="'success' or 'error'")
    output: Optional[str] = Field(
        default=None, description="Generated text (on success)"
    )
    usage: Optional[UsageInfo] = Field(
        default=None, description="Token usage (on success)"
    )
    error: Optional[str] = Field(
        default=None, description="Error message (on failure)"
    )
    cached: bool = Field(
        default=False, description="Whether result was from cache"
    )


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
    embedding: Optional[list[float]] = Field(
        default=None, description="Embedding vector (on success)"
    )
    error: Optional[str] = Field(
        default=None, description="Error message (on failure)"
    )
    cached: bool = Field(
        default=False, description="Whether result was from cache"
    )


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

### Step 6: Tambah `BATCH_TOO_LARGE` ke exception handler di `app/main.py`
Di dalam fungsi `gateway_error_handler()`, tambahkan entry ke `status_map`:

```python
status_map = {
    "PROVIDER_NOT_FOUND": 404,
    "MODEL_NOT_FOUND": 404,
    "SESSION_NOT_FOUND": 404,
    "CAPABILITY_NOT_SUPPORTED": 400,
    "BATCH_TOO_LARGE": 400,            # ← tambah ini
    "PROVIDER_CONNECTION_ERROR": 502,
    "PROVIDER_TIMEOUT": 504,
    "PROVIDER_API_ERROR": 502,
}
```

## 6. Output yang Diharapkan

Setelah Step 1–6 selesai, verifikasi:

**Config berhasil dimuat:**
```python
from app.config import settings
assert settings.BATCH_MAX_SIZE == 20
assert settings.BATCH_CONCURRENCY == 5
```

**Exception bisa di-raise:**
```python
from app.core.exceptions import BatchTooLargeError
exc = BatchTooLargeError(actual=25, maximum=20)
assert exc.code == "BATCH_TOO_LARGE"
assert exc.actual == 25
```

**Schemas bisa di-instantiate:**
```python
from app.schemas.requests import BatchGenerateRequest, BatchGenerateItem
req = BatchGenerateRequest(
    provider="gemini",
    model="gemini-2.5-pro",
    items=[BatchGenerateItem(input="Hello")]
)
assert len(req.items) == 1
```

## 7. Dependencies
- Tidak ada (task pertama)

## 8. Acceptance Criteria
- [ ] `BATCH_MAX_SIZE` dan `BATCH_CONCURRENCY` ada di `app/config.py` dengan default 20 dan 5
- [ ] `.env` dan `.env.example` berisi `BATCH_MAX_SIZE` dan `BATCH_CONCURRENCY`
- [ ] `BatchTooLargeError` ada di `app/core/exceptions.py`, menyimpan `actual` dan `maximum`
- [ ] `BatchGenerateItem` — `input` (required), `images` (optional)
- [ ] `BatchGenerateRequest` — `provider`, `model`, `items` (min_length=1)
- [ ] `BatchEmbeddingRequest` — `provider`, `model`, `inputs` (min_length=1)
- [ ] `BatchGenerateResult` — `index`, `status`, `output`, `usage`, `error`, `cached`
- [ ] `BatchGenerateResponse` — `provider`, `model`, `total`, `succeeded`, `failed`, `results`
- [ ] `BatchEmbeddingResult` — `index`, `status`, `embedding`, `error`, `cached`
- [ ] `BatchEmbeddingResponse` — `provider`, `model`, `total`, `succeeded`, `failed`, `results`
- [ ] `BATCH_TOO_LARGE` → HTTP 400 di `gateway_error_handler` status_map
- [ ] Server bisa start tanpa error (`uvicorn app.main:app`)
- [ ] Semua existing tests tetap PASS

## 9. Estimasi
Low (~20 menit)
