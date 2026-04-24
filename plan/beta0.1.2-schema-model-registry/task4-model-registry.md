# Task 4 — Model Registry

> **Modul**: beta0.1.2 — Schema & Model Registry  
> **Estimasi**: Medium (60–90 menit)  
> **Dependencies**: Task 1 (Common Types), beta0.1.1 Task 3 (Exceptions)

---

## 1. Judul Task

Implementasi `app/services/model_registry.py` — ModelCapability dataclass dan ModelRegistry class yang menyimpan catalog semua model beserta capability-nya.

---

## 2. Deskripsi

Membuat sistem registry terpusat untuk semua AI model. Registry menyimpan informasi tentang setiap model (nama, provider, dan capability — text, image, embedding) dan menyediakan method untuk register, lookup, dan list model. **Tidak ada model yang di-hardcode di endpoint** — semuanya melalui registry ini.

---

## 3. Tujuan Teknis

- Dataclass `ModelCapability` untuk menyimpan metadata model
- Class `ModelRegistry` dengan method: `register()`, `get_model()`, `list_models()`
- Method `register_defaults()` yang mendaftarkan 6 model bawaan (3 Ollama + 3 Gemini)
- Key format `"{provider}:{model_name}"` untuk mencegah collision
- Raise `ModelNotFoundError` jika model tidak ditemukan

---

## 4. Scope

### ✅ Yang Dikerjakan

- Implementasi `app/services/model_registry.py`
- `ModelCapability` dataclass
- `ModelRegistry` class dengan 4 methods
- 6 default models

### ❌ Yang Tidak Dikerjakan

- Auto-discovery model dari Ollama API
- Persistent storage (registry in-memory saja)
- Model hot-reload saat runtime

---

## 5. Langkah Implementasi

### Step 1: Buat `app/services/model_registry.py`

```python
"""
Model Registry for AI Generative Core.

Provides a central catalog of all available AI models and their capabilities.
Models are registered at startup and queried by the GeneratorService
to validate requests before routing them to providers.
"""

from dataclasses import dataclass

from loguru import logger

from app.core.exceptions import ModelNotFoundError


@dataclass
class ModelCapability:
    """
    Metadata and capabilities of a single AI model.

    Attributes:
        name: Model identifier (e.g. "llama3.2", "gemini-2.0-flash")
        provider: Provider that hosts this model ("ollama", "gemini")
        supports_text: Whether the model can generate text
        supports_image: Whether the model accepts image input (multimodal)
        supports_embedding: Whether the model can generate embeddings
    """

    name: str
    provider: str
    supports_text: bool = True
    supports_image: bool = False
    supports_embedding: bool = False


class ModelRegistry:
    """
    Central catalog of all available models.

    Models are registered at startup via register() or register_defaults().
    The registry is queried by GeneratorService to:
    1. Check if a model exists
    2. Validate model capabilities (image support, embedding support)
    3. List available models for the GET /models endpoint
    """

    def __init__(self):
        self._models: dict[str, ModelCapability] = {}

    def _make_key(self, provider: str, name: str) -> str:
        """Generate unique registry key from provider and model name."""
        return f"{provider}:{name}"

    def register(self, model: ModelCapability) -> None:
        """
        Register a model in the catalog.

        Args:
            model: ModelCapability instance to register.
        """
        key = self._make_key(model.provider, model.name)
        self._models[key] = model
        logger.debug(
            "Registered model: {key}",
            key=key,
        )

    def get_model(self, provider: str, name: str) -> ModelCapability:
        """
        Look up a model by provider and name.

        Args:
            provider: Provider identifier (e.g. "ollama")
            name: Model name (e.g. "llama3.2")

        Returns:
            ModelCapability for the requested model.

        Raises:
            ModelNotFoundError: If the model is not registered.
        """
        key = self._make_key(provider, name)
        model = self._models.get(key)
        if model is None:
            raise ModelNotFoundError(provider=provider, model=name)
        return model

    def list_models(self, provider: str | None = None) -> list[ModelCapability]:
        """
        List all registered models, optionally filtered by provider.

        Args:
            provider: If provided, only return models from this provider.

        Returns:
            List of ModelCapability instances.
        """
        models = list(self._models.values())
        if provider:
            models = [m for m in models if m.provider == provider]
        return models

    def register_defaults(self) -> None:
        """
        Register the default set of known models.

        Called at startup to populate the registry with commonly used models.
        These can be overridden or extended at runtime.
        """
        defaults = [
            # --- Ollama models ---
            ModelCapability(
                name="llama3.2",
                provider="ollama",
                supports_text=True,
                supports_image=False,
                supports_embedding=False,
            ),
            ModelCapability(
                name="llama3.2-vision",
                provider="ollama",
                supports_text=True,
                supports_image=True,
                supports_embedding=False,
            ),
            ModelCapability(
                name="qwen3-embedding:0.6b",
                provider="ollama",
                supports_text=False,
                supports_image=False,
                supports_embedding=True,
            ),
            # --- Gemini models ---
            ModelCapability(
                name="gemini-2.0-flash",
                provider="gemini",
                supports_text=True,
                supports_image=True,
                supports_embedding=False,
            ),
            ModelCapability(
                name="gemini-2.5-flash-preview-04-17",
                provider="gemini",
                supports_text=True,
                supports_image=True,
                supports_embedding=False,
            ),
            ModelCapability(
                name="text-embedding-004",
                provider="gemini",
                supports_text=False,
                supports_image=False,
                supports_embedding=True,
            ),
        ]

        for model in defaults:
            self.register(model)

        logger.info(
            "Registered {count} default models",
            count=len(defaults),
        )
```

### Step 2: Verifikasi

```bash
python -c "
from app.services.model_registry import ModelRegistry, ModelCapability
from app.core.exceptions import ModelNotFoundError

registry = ModelRegistry()
registry.register_defaults()

# List all models
all_models = registry.list_models()
print(f'Total models: {len(all_models)}')

# List Ollama models only
ollama = registry.list_models(provider='ollama')
print(f'Ollama models: {len(ollama)}')
for m in ollama:
    print(f'  - {m.name} (text={m.supports_text}, image={m.supports_image}, embed={m.supports_embedding})')

# Lookup specific model
model = registry.get_model('ollama', 'llama3.2')
print(f'Found: {model.name} from {model.provider}')

# Lookup nonexistent → error
try:
    registry.get_model('ollama', 'nonexistent')
except ModelNotFoundError as e:
    print(f'Error: {e.message} (code={e.code})')
"
```

Output yang diharapkan:

```
Total models: 6
Ollama models: 3
  - llama3.2 (text=True, image=False, embed=False)
  - llama3.2-vision (text=True, image=True, embed=False)
  - qwen3-embedding:0.6b (text=False, image=False, embed=True)
Found: llama3.2 from ollama
Error: Model 'nonexistent' not found for provider 'ollama' (code=MODEL_NOT_FOUND)
```

---

## 6. Output yang Diharapkan

### File: `app/services/model_registry.py`

Isi seperti Step 1 di atas.

### Default Models Registered

| Name | Provider | Text | Image | Embedding |
|---|---|---|---|---|
| `llama3.2` | ollama | ✅ | ❌ | ❌ |
| `llama3.2-vision` | ollama | ✅ | ✅ | ❌ |
| `qwen3-embedding:0.6b` | ollama | ❌ | ❌ | ✅ |
| `gemini-2.0-flash` | gemini | ✅ | ✅ | ❌ |
| `gemini-2.5-flash-preview-04-17` | gemini | ✅ | ✅ | ❌ |
| `text-embedding-004` | gemini | ❌ | ❌ | ✅ |

---

## 7. Dependencies

- **beta0.1.1 Task 3** — `ModelNotFoundError` dari `app/core/exceptions.py`
- **beta0.1.1 Task 4** — `loguru` untuk logging

---

## 8. Acceptance Criteria

- [ ] File `app/services/model_registry.py` ada
- [ ] `ModelCapability` dan `ModelRegistry` bisa di-import
- [ ] `register_defaults()` mendaftarkan 6 model
- [ ] `list_models()` return 6 models
- [ ] `list_models(provider="ollama")` return 3 models
- [ ] `list_models(provider="gemini")` return 3 models
- [ ] `get_model("ollama", "llama3.2")` return `ModelCapability`
- [ ] `get_model("ollama", "nonexistent")` raise `ModelNotFoundError`
- [ ] Custom model bisa di-register: `registry.register(ModelCapability(...))`
- [ ] Key format internal: `"{provider}:{model_name}"`

---

## 9. Estimasi

**Medium** — Dataclass + class dengan beberapa methods dan validasi logic.
