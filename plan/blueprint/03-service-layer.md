# 03 — Service Layer Design

---

## GeneratorService

File: `app/services/generator.py`

### Responsibilities

1. **Route** request ke provider yang tepat
2. **Validate** capability model (image support, embedding support)
3. **Normalize** response ke format standard
4. **Handle** errors dari provider layer

### Class Design

```python
class GeneratorService:
    """
    Orchestrator utama. Semua request dari endpoint HARUS 
    melewati service ini — TIDAK BOLEH langsung ke provider.
    """

    def __init__(
        self,
        providers: dict[str, BaseProvider],
        registry: ModelRegistry,
    ):
        self._providers = providers   # {"ollama": OllamaProvider, ...}
        self._registry = registry

    def _get_provider(self, provider_name: str) -> BaseProvider:
        """Resolve provider by name. Raise if not found."""
        provider = self._providers.get(provider_name)
        if not provider:
            raise ProviderNotFoundError(provider_name)
        return provider

    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        """
        Flow:
        1. Resolve provider
        2. Check model exists in registry
        3. If images → validate model supports multimodal
        4. Call provider.generate()
        5. Wrap in GenerateResponse
        """
        provider = self._get_provider(request.provider)
        model_info = self._registry.get_model(request.provider, request.model)

        if request.images and not model_info.supports_image:
            raise ModelCapabilityError(
                model=request.model,
                capability="image",
            )

        result = await provider.generate(
            model=request.model,
            prompt=request.input,
            images=request.images,
        )

        return GenerateResponse(
            output=result["output"],
            provider=request.provider,
            model=request.model,
            usage=result.get("usage"),
            metadata=result.get("metadata"),
        )

    async def stream(
        self, request: StreamRequest
    ) -> AsyncGenerator[str, None]:
        """
        Flow:
        1. Resolve provider
        2. Validate model
        3. Yield tokens from provider.stream()
        """
        provider = self._get_provider(request.provider)
        self._registry.get_model(request.provider, request.model)

        async for token in provider.stream(
            model=request.model,
            prompt=request.input,
            images=request.images,
        ):
            yield token

    async def embedding(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """
        Flow:
        1. Resolve provider
        2. Validate model supports embedding
        3. Call provider.embedding()
        4. Return vector
        """
        provider = self._get_provider(request.provider)
        model_info = self._registry.get_model(request.provider, request.model)

        if not model_info.supports_embedding:
            raise ModelCapabilityError(
                model=request.model,
                capability="embedding",
            )

        vector = await provider.embedding(
            model=request.model,
            input_text=request.input,
        )

        return EmbeddingResponse(
            embedding=vector,
            provider=request.provider,
            model=request.model,
        )
```

---

## ModelRegistry

File: `app/services/model_registry.py`

### Responsibilities

1. **Store** daftar model yang tersedia beserta capability-nya
2. **Lookup** model by provider + name
3. **Register** model baru (dari config atau runtime)
4. **List** semua model untuk endpoint `GET /models`

### Data Structure

```python
@dataclass
class ModelCapability:
    name: str                    # e.g. "llama3.2"
    provider: str                # e.g. "ollama"
    supports_text: bool = True
    supports_image: bool = False
    supports_embedding: bool = False


class ModelRegistry:
    """
    Central catalog of all available models.
    Models diregister saat startup, bukan hardcode di endpoint.
    """

    def __init__(self):
        self._models: dict[str, ModelCapability] = {}
        # Key format: "{provider}:{model_name}"

    def register(self, model: ModelCapability) -> None:
        key = f"{model.provider}:{model.name}"
        self._models[key] = model

    def get_model(self, provider: str, name: str) -> ModelCapability:
        key = f"{provider}:{name}"
        model = self._models.get(key)
        if not model:
            raise ModelNotFoundError(provider=provider, model=name)
        return model

    def list_models(
        self, provider: str | None = None
    ) -> list[ModelCapability]:
        models = list(self._models.values())
        if provider:
            models = [m for m in models if m.provider == provider]
        return models

    def register_defaults(self) -> None:
        """Register known default models at startup."""
        defaults = [
            # Ollama models
            ModelCapability("llama3.2", "ollama", True, False, False),
            ModelCapability("llama3.2-vision", "ollama", True, True, False),
            ModelCapability("nomic-embed-text", "ollama", False, False, True),
            # Gemini models
            ModelCapability("gemini-2.0-flash", "gemini", True, True, False),
            ModelCapability("gemini-2.5-flash-preview-04-17", "gemini", True, True, False),
            ModelCapability("text-embedding-004", "gemini", False, False, True),
        ]
        for model in defaults:
            self.register(model)
```

### Registry Initialization (at startup)

```python
# In app/main.py startup event:

registry = ModelRegistry()
registry.register_defaults()

# Optionally: auto-discover Ollama models
# tags = await ollama_provider.list_local_models()
# for tag in tags:
#     registry.register(ModelCapability(...))
```

---

## Dependency Injection

File: `app/api/dependencies.py`

```python
from functools import lru_cache

# Singleton instances — created once at startup
_generator_service: GeneratorService | None = None
_model_registry: ModelRegistry | None = None

def get_generator_service() -> GeneratorService:
    """FastAPI dependency for GeneratorService."""
    assert _generator_service is not None
    return _generator_service

def get_model_registry() -> ModelRegistry:
    """FastAPI dependency for ModelRegistry."""
    assert _model_registry is not None
    return _model_registry

def initialize_services(settings: Settings) -> None:
    """Called once during app startup."""
    global _generator_service, _model_registry

    # Create providers
    providers = {
        "ollama": OllamaProvider(settings.OLLAMA_BASE_URL, settings.OLLAMA_TIMEOUT),
        "gemini": GeminiProvider(settings.GEMINI_API_KEY, settings.GEMINI_TIMEOUT),
    }

    # Create registry
    _model_registry = ModelRegistry()
    _model_registry.register_defaults()

    # Create service
    _generator_service = GeneratorService(providers, _model_registry)
```

> **Next**: See [04-api-layer.md](./04-api-layer.md)
