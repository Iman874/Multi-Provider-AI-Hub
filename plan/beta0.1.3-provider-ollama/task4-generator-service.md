# Task 4 — Generator Service

> **Modul**: beta0.1.3 — Provider Abstraction & Ollama  
> **Estimasi**: Medium (60–90 menit)  
> **Dependencies**: Task 1 (BaseProvider), beta0.1.2 Task 4 (ModelRegistry), beta0.1.2 Task 2+3 (Schemas)

---

## 1. Judul Task

Implementasi `app/services/generator.py` — GeneratorService yang berfungsi sebagai orchestrator utama, routing request ke provider yang tepat dengan validasi capability.

---

## 2. Deskripsi

Membuat service layer yang menjadi **satu-satunya jalur** antara endpoint dan provider. Endpoint TIDAK BOLEH langsung memanggil provider — semua harus melalui `GeneratorService`. Service ini bertugas: resolve provider, validate model di registry, check capability, call provider, dan normalize response.

---

## 3. Tujuan Teknis

- Class `GeneratorService` yang menerima `providers` dict dan `ModelRegistry`
- Method `_get_provider(name)` — resolve provider atau raise error
- Method `generate(request)` — full orchestration flow
- Validasi: provider exists, model registered, capability check (image support)
- Return `GenerateResponse` Pydantic model

---

## 4. Scope

### ✅ Yang Dikerjakan

- Implementasi `app/services/generator.py`
- Method `generate()` fully implemented

### ❌ Yang Tidak Dikerjakan

- Method `stream()` → beta0.1.5
- Method `embedding()` → beta0.1.6

---

## 5. Langkah Implementasi

### Step 1: Buat `app/services/generator.py`

```python
"""
Generator Service — Central orchestrator for AI operations.

All endpoint requests MUST go through this service.
The service handles:
1. Provider resolution (which provider to call)
2. Model validation (does the model exist in registry)
3. Capability checking (does the model support the requested operation)
4. Provider invocation (call the actual AI provider)
5. Response normalization (wrap in standard response schema)
"""

from loguru import logger

from app.core.exceptions import (
    ModelCapabilityError,
    ProviderNotFoundError,
)
from app.providers.base import BaseProvider
from app.schemas.requests import GenerateRequest
from app.schemas.responses import GenerateResponse, UsageInfo
from app.services.model_registry import ModelRegistry


class GeneratorService:
    """
    Orchestrator for all AI generation operations.

    This is the ONLY service that endpoints should call.
    Endpoints must NEVER call providers directly.
    """

    def __init__(
        self,
        providers: dict[str, BaseProvider],
        registry: ModelRegistry,
    ):
        """
        Initialize GeneratorService.

        Args:
            providers: Dict mapping provider names to BaseProvider instances.
                       e.g. {"ollama": OllamaProvider, "gemini": GeminiProvider}
            registry: ModelRegistry instance for model lookup and validation.
        """
        self._providers = providers
        self._registry = registry
        logger.info(
            "GeneratorService initialized with providers: {providers}",
            providers=list(providers.keys()),
        )

    def _get_provider(self, provider_name: str) -> BaseProvider:
        """
        Resolve a provider by name.

        Args:
            provider_name: Provider identifier (e.g. "ollama")

        Returns:
            BaseProvider instance.

        Raises:
            ProviderNotFoundError: If the provider is not registered or disabled.
        """
        provider = self._providers.get(provider_name)
        if provider is None:
            raise ProviderNotFoundError(provider_name)
        return provider

    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        """
        Generate text or multimodal response.

        Flow:
        1. Resolve provider by name
        2. Lookup model in registry (validates existence)
        3. If images provided → check model supports multimodal
        4. Call provider.generate()
        5. Wrap result in GenerateResponse

        Args:
            request: Validated GenerateRequest from endpoint.

        Returns:
            GenerateResponse with normalized output.

        Raises:
            ProviderNotFoundError: Provider not registered.
            ModelNotFoundError: Model not in registry.
            ModelCapabilityError: Model doesn't support requested capability.
            ProviderConnectionError: Cannot reach provider.
            ProviderTimeoutError: Provider took too long.
            ProviderAPIError: Provider returned error.
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
            "Generating: provider={provider}, model={model}",
            provider=request.provider.value,
            model=request.model,
        )

        # 4. Call provider
        result = await provider.generate(
            model=request.model,
            prompt=request.input,
            images=request.images,
        )

        # 5. Build and return normalized response
        usage = None
        if result.get("usage"):
            usage = UsageInfo(**result["usage"])

        return GenerateResponse(
            output=result["output"],
            provider=result.get("provider", request.provider.value),
            model=result.get("model", request.model),
            usage=usage,
            metadata=result.get("metadata"),
        )
```

### Step 2: Verifikasi (unit — dengan mock)

```bash
python -c "
import asyncio
from unittest.mock import AsyncMock, MagicMock
from app.services.generator import GeneratorService
from app.services.model_registry import ModelRegistry, ModelCapability
from app.schemas.requests import GenerateRequest
from app.core.exceptions import ProviderNotFoundError, ModelCapabilityError

# Setup
registry = ModelRegistry()
registry.register(ModelCapability('test-model', 'ollama', True, False, False))

mock_provider = MagicMock()
mock_provider.name = 'ollama'
mock_provider.generate = AsyncMock(return_value={
    'output': 'Hello from mock!',
    'model': 'test-model',
    'provider': 'ollama',
    'usage': {'prompt_tokens': 5, 'completion_tokens': 10, 'total_tokens': 15},
    'metadata': None,
})

service = GeneratorService(
    providers={'ollama': mock_provider},
    registry=registry,
)

async def test():
    # 1. Success case
    req = GenerateRequest(provider='ollama', model='test-model', input='Hello')
    resp = await service.generate(req)
    print(f'Output: {resp.output}')
    print(f'Provider: {resp.provider}')
    print(f'Usage: {resp.usage}')

    # 2. Provider not found
    try:
        req2 = GenerateRequest(provider='gemini', model='test', input='hi')
        await service.generate(req2)
    except ProviderNotFoundError as e:
        print(f'Error: {e.code}')

asyncio.run(test())
"
```

Output:

```
Output: Hello from mock!
Provider: ollama
Usage: prompt_tokens=5 completion_tokens=10 total_tokens=15
Error: PROVIDER_NOT_FOUND
```

---

## 6. Output yang Diharapkan

### File: `app/services/generator.py`

Isi seperti Step 1 di atas.

### Method Flow

```
generate(request)
  ├─ _get_provider(name) → BaseProvider or ProviderNotFoundError
  ├─ registry.get_model(provider, model) → ModelCapability or ModelNotFoundError
  ├─ if images + !supports_image → ModelCapabilityError
  ├─ provider.generate(model, prompt, images) → dict
  └─ return GenerateResponse(output, provider, model, usage, metadata)
```

---

## 7. Dependencies

- **Task 1** — `BaseProvider` type for providers dict
- **beta0.1.2 Task 2** — `GenerateRequest` schema
- **beta0.1.2 Task 3** — `GenerateResponse`, `UsageInfo` schemas
- **beta0.1.2 Task 4** — `ModelRegistry` for model lookup
- **beta0.1.1 Task 3** — Exception classes

---

## 8. Acceptance Criteria

- [ ] File `app/services/generator.py` ada
- [ ] `GeneratorService` bisa di-instantiate dengan providers dict dan registry
- [ ] `generate()` return `GenerateResponse` yang valid
- [ ] Provider not found → raise `ProviderNotFoundError`
- [ ] Model not found → raise `ModelNotFoundError` (via registry)
- [ ] Images + model doesn't support image → raise `ModelCapabilityError`
- [ ] Usage info di-wrap dalam `UsageInfo` Pydantic model
- [ ] Debug log muncul saat generate dipanggil

---

## 9. Estimasi

**Medium** — Business logic orchestration, multiple validation paths, async patterns.
