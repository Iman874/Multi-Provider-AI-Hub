# Task 3 — GeneratorService.embedding()

> **Modul**: beta0.1.6 — Embedding Endpoint  
> **Estimasi**: Low (30–45 menit)  
> **Dependencies**: Task 1, Task 2, beta0.1.3 Task 4 (GeneratorService existing)

---

## 1. Judul Task

Tambahkan method `embedding()` di `app/services/generator.py` — orchestrate embedding requests dengan capability validation.

---

## 2. Deskripsi

Menambah method `embedding()` ke `GeneratorService` yang memvalidasi bahwa model yang diminta **mendukung embedding** (`supports_embedding == True`) sebelum memanggil provider. Model text-only seperti `llama3.2` harus ditolak dengan error 400.

---

## 3. Tujuan Teknis

- Method `embedding(request: EmbeddingRequest)` → `EmbeddingResponse`
- Same validation flow: provider → model → capability check
- **Capability check khusus**: `model_info.supports_embedding` must be `True`
- Call `provider.embedding(model, input_text)`
- Wrap result dalam `EmbeddingResponse`

---

## 4. Scope

### ✅ Yang Dikerjakan

- Add `embedding()` method to `app/services/generator.py`
- Import `EmbeddingRequest` and `EmbeddingResponse`

### ❌ Yang Tidak Dikerjakan

- Changes to `generate()` or `stream()` methods
- Batch embedding logic

---

## 5. Langkah Implementasi

### Step 1: Add `embedding()` method to `GeneratorService`

Add the following method to the existing class in `app/services/generator.py`:

```python
    async def embedding(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """
        Generate embedding vector from text.

        Flow:
        1. Resolve provider
        2. Validate model exists in registry
        3. Validate model supports embedding capability
        4. Call provider.embedding()
        5. Wrap in EmbeddingResponse

        Args:
            request: Validated EmbeddingRequest from endpoint.

        Returns:
            EmbeddingResponse with embedding vector.

        Raises:
            ProviderNotFoundError: Provider not registered.
            ModelNotFoundError: Model not in registry.
            ModelCapabilityError: Model doesn't support embedding.
        """
        # 1. Resolve provider
        provider = self._get_provider(request.provider.value)

        # 2. Validate model exists
        model_info = self._registry.get_model(
            provider=request.provider.value,
            name=request.model,
        )

        # 3. Validate embedding capability
        if not model_info.supports_embedding:
            raise ModelCapabilityError(
                model=request.model,
                capability="embedding",
            )

        logger.debug(
            "Embedding: provider={provider}, model={model}",
            provider=request.provider.value,
            model=request.model,
        )

        # 4. Call provider
        vector = await provider.embedding(
            model=request.model,
            input_text=request.input,
        )

        # 5. Return normalized response
        return EmbeddingResponse(
            embedding=vector,
            provider=request.provider.value,
            model=request.model,
        )
```

### Step 2: Add imports

Add to the imports section of `app/services/generator.py`:

```python
from app.schemas.requests import GenerateRequest, StreamRequest, EmbeddingRequest
from app.schemas.responses import GenerateResponse, UsageInfo, EmbeddingResponse
```

> **Note**: `GenerateRequest` and `StreamRequest` are already imported. Just add `EmbeddingRequest` and `EmbeddingResponse`.

### Step 3: Verifikasi (unit — with mock)

```bash
python -c "
import asyncio
from unittest.mock import AsyncMock, MagicMock
from app.services.generator import GeneratorService
from app.services.model_registry import ModelRegistry, ModelCapability
from app.schemas.requests import EmbeddingRequest
from app.core.exceptions import ModelCapabilityError

# Setup
registry = ModelRegistry()
registry.register(ModelCapability('nomic-embed-text', 'ollama', False, False, True))
registry.register(ModelCapability('llama3.2', 'ollama', True, False, False))

mock_provider = MagicMock()
mock_provider.name = 'ollama'
mock_provider.embedding = AsyncMock(return_value=[0.1, 0.2, 0.3, 0.4, 0.5])

service = GeneratorService(
    providers={'ollama': mock_provider},
    registry=registry,
)

async def test():
    # 1. Success: embedding model
    req = EmbeddingRequest(provider='ollama', model='nomic-embed-text', input='test')
    resp = await service.embedding(req)
    print(f'Embedding length: {len(resp.embedding)}')
    print(f'Provider: {resp.provider}')
    print(f'Model: {resp.model}')

    # 2. Error: text model for embedding
    try:
        req2 = EmbeddingRequest(provider='ollama', model='llama3.2', input='test')
        await service.embedding(req2)
    except ModelCapabilityError as e:
        print(f'Error: {e.code} — {e.message}')

asyncio.run(test())
"
```

Output:

```
Embedding length: 5
Provider: ollama
Model: nomic-embed-text
Error: CAPABILITY_NOT_SUPPORTED — Model 'llama3.2' does not support 'embedding'
```

---

## 6. Output yang Diharapkan

### Method Flow

```
embedding(request)
  ├─ _get_provider(name) → BaseProvider or ProviderNotFoundError
  ├─ registry.get_model(provider, model) → or ModelNotFoundError
  ├─ if !supports_embedding → ModelCapabilityError("embedding")
  ├─ provider.embedding(model, input_text) → list[float]
  └─ return EmbeddingResponse(embedding=vector, provider, model)
```

### Capability Validation Matrix

| Model | supports_embedding | Result |
|---|---|---|
| `nomic-embed-text` | ✅ True | → proceed |
| `text-embedding-004` | ✅ True | → proceed |
| `llama3.2` | ❌ False | → 400 CAPABILITY_NOT_SUPPORTED |
| `gemini-2.0-flash` | ❌ False | → 400 CAPABILITY_NOT_SUPPORTED |

---

## 7. Dependencies

- **beta0.1.3 Task 4** — existing `GeneratorService` class
- **Task 1** — `OllamaProvider.embedding()` implemented
- **Task 2** — `GeminiProvider.embedding()` implemented
- **beta0.1.2 Task 2** — `EmbeddingRequest` schema
- **beta0.1.2 Task 3** — `EmbeddingResponse` schema

---

## 8. Acceptance Criteria

- [ ] `GeneratorService` has `embedding()` method
- [ ] `embedding()` returns `EmbeddingResponse` with vector
- [ ] Provider not found → raise `ProviderNotFoundError`
- [ ] Model not found → raise `ModelNotFoundError`
- [ ] Model without embedding support → raise `ModelCapabilityError`
- [ ] Debug log emitted when embedding is called
- [ ] `generate()` and `stream()` unchanged (no regression)

---

## 9. Estimasi

**Low** — Same orchestration pattern as `generate()`, one extra validation check.
