# Task 3 — GeneratorService.stream()

> **Modul**: beta0.1.5 — Streaming Adapter  
> **Estimasi**: Low (30–45 menit)  
> **Dependencies**: Task 1, Task 2, beta0.1.3 Task 4 (GeneratorService existing)

---

## 1. Judul Task

Tambahkan method `stream()` di `app/services/generator.py` — orchestrate streaming requests melalui provider.

---

## 2. Deskripsi

Menambah method `stream()` ke `GeneratorService` yang sudah ada. Pattern-nya sama persis dengan `generate()` — resolve provider, validate model, check capability — tapi instead of returning result, ia **yield tokens** dari `provider.stream()`.

---

## 3. Tujuan Teknis

- Method `stream(request: StreamRequest)` → `AsyncGenerator[str, None]`
- Same validation flow as `generate()`: provider → model → capability check
- Delegate to `provider.stream()` dan forward yield tokens
- Validation errors raised BEFORE streaming starts

---

## 4. Scope

### ✅ Yang Dikerjakan

- Add `stream()` method to `app/services/generator.py`
- Import `StreamRequest` schema

### ❌ Yang Tidak Dikerjakan

- Changes to `generate()` method
- SSE wrapping (that's the endpoint's job)

---

## 5. Langkah Implementasi

### Step 1: Add `stream()` method to `GeneratorService`

Add the following method to the existing `GeneratorService` class in `app/services/generator.py`:

```python
    async def stream(
        self, request: StreamRequest
    ) -> AsyncGenerator[str, None]:
        """
        Stream generated tokens from provider.

        Flow is identical to generate() for validation:
        1. Resolve provider
        2. Validate model in registry
        3. Check image capability
        4. Delegate to provider.stream()

        All validation errors are raised BEFORE any tokens are yielded,
        ensuring the endpoint can return proper error responses.

        Args:
            request: Validated StreamRequest from endpoint.

        Yields:
            Token strings as they are generated.
        """
        # 1. Resolve provider
        provider = self._get_provider(request.provider.value)

        # 2. Validate model exists in registry
        model_info = self._registry.get_model(
            provider=request.provider.value,
            name=request.model,
        )

        # 3. Check image capability if images provided
        if request.images and not model_info.supports_image:
            raise ModelCapabilityError(
                model=request.model,
                capability="image",
            )

        logger.debug(
            "Streaming: provider={provider}, model={model}",
            provider=request.provider.value,
            model=request.model,
        )

        # 4. Delegate to provider stream
        async for token in provider.stream(
            model=request.model,
            prompt=request.input,
            images=request.images,
        ):
            yield token
```

### Step 2: Add imports

Add to the imports section of `app/services/generator.py`:

```python
from typing import AsyncGenerator
from app.schemas.requests import GenerateRequest, StreamRequest
```

> **Note**: `GenerateRequest` is already imported. Just add `StreamRequest` and `AsyncGenerator`.

### Step 3: Verifikasi (unit — with mock)

```bash
python -c "
import asyncio
from unittest.mock import AsyncMock, MagicMock
from app.services.generator import GeneratorService
from app.services.model_registry import ModelRegistry, ModelCapability
from app.schemas.requests import StreamRequest
from app.core.exceptions import ProviderNotFoundError

# Setup
registry = ModelRegistry()
registry.register(ModelCapability('test-model', 'ollama', True, False, False))

async def mock_stream(*args, **kwargs):
    for token in ['Hello', ' ', 'world', '!']:
        yield token

mock_provider = MagicMock()
mock_provider.name = 'ollama'
mock_provider.stream = mock_stream

service = GeneratorService(
    providers={'ollama': mock_provider},
    registry=registry,
)

async def test():
    req = StreamRequest(provider='ollama', model='test-model', input='Hello')
    tokens = []
    async for token in service.stream(req):
        tokens.append(token)
    print(f'Tokens: {tokens}')
    print(f'Full: {\"\" .join(tokens)}')

    # Error case
    try:
        req2 = StreamRequest(provider='gemini', model='test', input='hi')
        async for _ in service.stream(req2):
            pass
    except ProviderNotFoundError as e:
        print(f'Error: {e.code}')

asyncio.run(test())
"
```

Output:

```
Tokens: ['Hello', ' ', 'world', '!']
Full: Hello world!
Error: PROVIDER_NOT_FOUND
```

---

## 6. Output yang Diharapkan

### Method Flow

```
stream(request)
  ├─ _get_provider(name) → BaseProvider or ProviderNotFoundError
  ├─ registry.get_model(provider, model) → or ModelNotFoundError
  ├─ if images + !supports_image → ModelCapabilityError
  └─ async for token in provider.stream(...):
       yield token
```

### Key Design: Validation Before Streaming

All errors (ProviderNotFound, ModelNotFound, CapabilityError) are raised **before** any tokens are yielded. This is critical because once SSE streaming starts, HTTP status is already 200 — errors can't change the status code.

---

## 7. Dependencies

- **beta0.1.3 Task 4** — existing `GeneratorService` class
- **Task 1** — `OllamaProvider.stream()` implemented
- **Task 2** — `GeminiProvider.stream()` implemented
- **beta0.1.2 Task 2** — `StreamRequest` schema

---

## 8. Acceptance Criteria

- [ ] `GeneratorService` has `stream()` method
- [ ] `stream()` yields token strings from provider
- [ ] Provider not found → raise `ProviderNotFoundError` (before any yield)
- [ ] Model not found → raise `ModelNotFoundError` (before any yield)
- [ ] Images + no support → raise `ModelCapabilityError` (before any yield)
- [ ] Debug log emitted when streaming starts
- [ ] `generate()` method is unchanged (no regression)

---

## 9. Estimasi

**Low** — Same pattern as `generate()`, just async generator wrapper.
