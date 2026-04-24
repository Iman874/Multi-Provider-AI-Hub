# Task 3 — GeneratorService Integration

## 1. Judul Task
Integrasikan `CacheService` ke dalam `GeneratorService` — cache check sebelum provider call, store response setelah generate/embedding

## 2. Deskripsi
Mengubah alur `generate()` dan `embedding()` di `GeneratorService` agar memeriksa cache terlebih dahulu sebelum memanggil provider, lalu menyimpan response ke cache setelah berhasil. Menambahkan `metadata.cached` ke response. Stream TIDAK di-cache.

## 3. Tujuan Teknis
- `CacheService` diinisialisasi di `initialize_services()` dan diinjek ke `GeneratorService`
- `generate()` — cache check → miss → provider call → store → return (metadata.cached=false)
- `generate()` — cache check → hit → return cached (metadata.cached=true, cache_age_seconds)
- `embedding()` — sama pattern: cache check → provider call → store
- `stream()` — TIDAK berubah (no caching)
- `get_cache_service()` dependency tersedia

## 4. Scope
### Yang dikerjakan
- `app/services/generator.py` — update `__init__`, `generate()`, `embedding()` dengan cache logic
- `app/api/dependencies.py` — tambah `_cache_service` singleton, `get_cache_service()`, init di `initialize_services()`

### Yang TIDAK dikerjakan
- CacheService logic (sudah Task 2)
- Cache endpoints — Task 4
- Unit tests — Task 5

## 5. Langkah Implementasi

### Step 1: Update `app/api/dependencies.py` — tambah CacheService singleton
Tambah import:
```python
from app.services.cache_service import CacheService
```

Tambah singleton:
```python
_cache_service: CacheService | None = None
```

Tambah getter:
```python
def get_cache_service() -> CacheService | None:
    """FastAPI dependency: provides CacheService instance."""
    return _cache_service
```

### Step 2: Update `initialize_services()` di `app/api/dependencies.py`
Update global declaration:
```python
global _model_registry, _generator_service, _providers, _cache_service
```

Tambahkan SEBELUM pembuatan GeneratorService (karena GeneratorService butuh cache):
```python
    # --- 3. Create Cache Service ---
    _cache_service = CacheService(
        enabled=settings.CACHE_ENABLED,
        ttl=settings.CACHE_TTL,
        max_size=settings.CACHE_MAX_SIZE,
    )
```

Update pembuatan GeneratorService (inject cache):
```python
    # --- 4. Create Generator Service ---
    _generator_service = GeneratorService(
        providers=_providers,
        registry=_model_registry,
        cache=_cache_service,
    )
```

### Step 3: Update `GeneratorService.__init__()` di `app/services/generator.py`
Tambah import di bagian atas:
```python
import time
```

Update `__init__` signature dan body:
```python
    def __init__(
        self,
        providers: dict[str, BaseProvider],
        registry: ModelRegistry,
        cache: "CacheService | None" = None,
    ):
        """
        Initialize GeneratorService.

        Args:
            providers: Dict mapping provider names to BaseProvider instances.
            registry: ModelRegistry instance for model lookup and validation.
            cache: Optional CacheService for response caching.
        """
        self._providers = providers
        self._registry = registry
        self._cache = cache
        logger.info(
            "GeneratorService initialized with providers: {providers}, cache: {cache}",
            providers=list(providers.keys()),
            cache="enabled" if cache and cache.is_enabled else "disabled",
        )
```

### Step 4: Update `generate()` — KRITIS: cache integration
Replace method `generate()` (lines 72-137 in current file):

```python
    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        """
        Generate text or multimodal response.

        Flow:
        1. Resolve provider by name
        2. Lookup model in registry (validates existence)
        3. If images provided → check model supports multimodal
        4. Check cache (before calling provider)
        5. Call provider.generate() (on cache miss)
        6. Store result in cache
        7. Wrap result in GenerateResponse with metadata.cached flag
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

        # 4. Check cache (BEFORE calling provider)
        cache_key = None
        if self._cache and self._cache.is_enabled:
            cache_key = self._cache.make_key(
                provider=request.provider.value,
                model=request.model,
                prompt=request.input,
                images=request.images,
            )
            cached = self._cache.get(cache_key)
            if cached is not None:
                logger.debug(
                    "Cache HIT: provider={provider}, model={model}, key={key}",
                    provider=request.provider.value,
                    model=request.model,
                    key=cache_key[:8],
                )
                # Build response from cached data with cache metadata
                usage = None
                if cached.get("usage"):
                    usage = UsageInfo(**cached["usage"])

                return GenerateResponse(
                    output=cached["output"],
                    provider=cached.get("provider", request.provider.value),
                    model=cached.get("model", request.model),
                    usage=usage,
                    metadata={
                        "cached": True,
                    },
                )

        logger.debug(
            "Generating: provider={provider}, model={model}",
            provider=request.provider.value,
            model=request.model,
        )

        # 5. Call provider (cache MISS)
        result = await provider.generate(
            model=request.model,
            prompt=request.input,
            images=request.images,
        )

        # 6. Store in cache
        if cache_key and self._cache:
            self._cache.put(cache_key, result)

        # 7. Build and return normalized response
        usage = None
        if result.get("usage"):
            usage = UsageInfo(**result["usage"])

        return GenerateResponse(
            output=result["output"],
            provider=result.get("provider", request.provider.value),
            model=result.get("model", request.model),
            usage=usage,
            metadata={"cached": False},
        )
```

### Step 5: Update `embedding()` — same cache pattern
Replace method `embedding()` (lines 190-245 in current file):

```python
    async def embedding(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """
        Generate embedding vector from text.

        Flow:
        1. Resolve provider
        2. Validate model exists in registry
        3. Validate model supports embedding capability
        4. Check cache (before calling provider)
        5. Call provider.embedding() (on cache miss)
        6. Store result in cache
        7. Wrap in EmbeddingResponse
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

        # 4. Check cache
        cache_key = None
        if self._cache and self._cache.is_enabled:
            cache_key = self._cache.make_key(
                provider=request.provider.value,
                model=request.model,
                prompt=request.input,
            )
            cached = self._cache.get(cache_key)
            if cached is not None:
                logger.debug(
                    "Cache HIT (embedding): key={key}",
                    key=cache_key[:8],
                )
                return EmbeddingResponse(
                    embedding=cached["embedding"],
                    provider=cached.get("provider", request.provider.value),
                    model=cached.get("model", request.model),
                )

        logger.debug(
            "Embedding: provider={provider}, model={model}",
            provider=request.provider.value,
            model=request.model,
        )

        # 5. Call provider
        vector = await provider.embedding(
            model=request.model,
            input_text=request.input,
        )

        # 6. Store in cache
        if cache_key and self._cache:
            self._cache.put(cache_key, {
                "embedding": vector,
                "provider": request.provider.value,
                "model": request.model,
            })

        # 7. Return normalized response
        return EmbeddingResponse(
            embedding=vector,
            provider=request.provider.value,
            model=request.model,
        )
```

### Step 6: Verifikasi `stream()` — NO changes
`stream()` method harus tetap TIDAK berubah. Streaming responses tidak di-cache. Verifikasi bahwa method ini TIDAK menyentuh `self._cache`.

## 6. Output yang Diharapkan

### Cache MISS (first call):
```bash
curl -X POST http://localhost:8000/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{"provider":"ollama","model":"llama3.2","input":"Apa itu AI?"}'
```
```json
{
    "output": "AI adalah...",
    "provider": "ollama",
    "model": "llama3.2",
    "usage": {"prompt_tokens": 5, "completion_tokens": 20, "total_tokens": 25},
    "metadata": {"cached": false}
}
```

### Cache HIT (second identical call — instant!):
```json
{
    "output": "AI adalah...",
    "provider": "ollama",
    "model": "llama3.2",
    "usage": {"prompt_tokens": 5, "completion_tokens": 20, "total_tokens": 25},
    "metadata": {"cached": true}
}
```

### Stream — NO cache metadata (unchanged):
Streaming endpoint tetap berfungsi normal tanpa cache interference.

## 7. Dependencies
- **Task 1** — Config fields (`CACHE_ENABLED`, `CACHE_TTL`, `CACHE_MAX_SIZE`)
- **Task 2** — `CacheService` class

## 8. Acceptance Criteria
- [ ] `CacheService` initialized in `initialize_services()` with config values
- [ ] `get_cache_service()` dependency available
- [ ] `GeneratorService.__init__()` accepts optional `cache` parameter
- [ ] `generate()` — cache miss: calls provider, stores in cache, `metadata.cached: false`
- [ ] `generate()` — cache hit: returns cached response instantly, `metadata.cached: true`
- [ ] `generate()` — identical request → cache HIT (same provider+model+prompt+images)
- [ ] `generate()` — different prompt → cache MISS (different key)
- [ ] `embedding()` — cache miss: calls provider, stores in cache
- [ ] `embedding()` — cache hit: returns cached embedding instantly
- [ ] `stream()` — NO caching (unchanged, no metadata.cached)
- [ ] `CACHE_ENABLED=false` → generate/embedding bypass cache entirely
- [ ] `metadata` field always present in generate response (either `cached: true` or `cached: false`)
- [ ] Server bisa start tanpa error
- [ ] Semua existing tests tetap PASS (may need to update tests checking `metadata` field)

## 9. Estimasi
Medium (~30 menit)
