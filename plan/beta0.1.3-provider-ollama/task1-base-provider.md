# Task 1 — Abstract Base Provider

> **Modul**: beta0.1.3 — Provider Abstraction & Ollama  
> **Estimasi**: Low (30–45 menit)  
> **Dependencies**: beta0.1.2 selesai

---

## 1. Judul Task

Implementasi `app/providers/base.py` — Abstract base class yang mendefinisikan kontrak wajib untuk semua AI provider.

---

## 2. Deskripsi

Membuat abstract class `BaseProvider` menggunakan Python ABC. Class ini mendefinisikan **4 abstract methods** yang HARUS diimplementasi oleh setiap provider (Ollama, Gemini, dan provider masa depan). Ini menjamin arsitektur Open/Closed — menambah provider baru tidak perlu mengubah kode existing.

---

## 3. Tujuan Teknis

- Abstract class `BaseProvider(ABC)` dengan `@abstractmethod`
- Abstract property `name` → str (identifier provider)
- Abstract method `generate()` → dict (text/multimodal generation)
- Abstract method `stream()` → AsyncGenerator (token streaming)
- Abstract method `embedding()` → list[float] (vector embedding)
- Abstract method `supports_image()` → bool (capability check)
- Concrete method `close()` → cleanup resources (default no-op)

---

## 4. Scope

### ✅ Yang Dikerjakan

- Implementasi `app/providers/base.py`

### ❌ Yang Tidak Dikerjakan

- Implementasi konkrit (Ollama/Gemini) → task 2, beta0.1.4
- Provider factory → task 3

---

## 5. Langkah Implementasi

### Step 1: Buat `app/providers/base.py`

```python
"""
Abstract base provider for AI Generative Core.

All AI providers (Ollama, Gemini, etc.) MUST inherit from this class
and implement all abstract methods. This ensures a consistent interface
across providers, enabling the service layer to work with any provider
without knowing its implementation details.
"""

from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional


class BaseProvider(ABC):
    """
    Abstract contract for all AI providers.

    Adding a new provider requires:
    1. Create a new class extending BaseProvider
    2. Implement all abstract methods
    3. Register in provider factory
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Unique provider identifier.

        Returns:
            Provider name string, e.g. "ollama", "gemini"
        """
        ...

    @abstractmethod
    async def generate(
        self,
        model: str,
        prompt: str,
        images: Optional[list[str]] = None,
    ) -> dict:
        """
        Generate text or multimodal response.

        Args:
            model: Model identifier (e.g. "llama3.2", "gemini-2.0-flash")
            prompt: Text input/prompt
            images: Optional list of base64-encoded images

        Returns:
            Normalized dict with keys:
            - output (str): Generated text
            - model (str): Model used
            - provider (str): Provider name
            - usage (dict | None): Token usage stats
            - metadata (dict | None): Additional info (e.g. duration)
        """
        ...

    @abstractmethod
    async def stream(
        self,
        model: str,
        prompt: str,
        images: Optional[list[str]] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream generated tokens one at a time.

        Args:
            model: Model identifier
            prompt: Text input/prompt
            images: Optional list of base64-encoded images

        Yields:
            Individual token strings as they are generated.
        """
        ...

    @abstractmethod
    async def embedding(
        self,
        model: str,
        input_text: str,
    ) -> list[float]:
        """
        Generate embedding vector from text.

        Args:
            model: Embedding model identifier
            input_text: Text to embed

        Returns:
            List of floats representing the embedding vector.
        """
        ...

    @abstractmethod
    def supports_image(self, model: str) -> bool:
        """
        Check if a specific model supports image/multimodal input.

        Args:
            model: Model identifier to check

        Returns:
            True if the model accepts image input.
        """
        ...

    async def close(self) -> None:
        """
        Cleanup provider resources (HTTP clients, connections, etc).

        Override in subclass if cleanup is needed.
        Default implementation is a no-op.
        """
        pass
```

### Step 2: Verifikasi

```bash
python -c "
from app.providers.base import BaseProvider

# Cannot instantiate abstract class
try:
    p = BaseProvider()
except TypeError as e:
    print(f'Cannot instantiate: {e}')

# Verify it's an abstract class
import inspect
abstract_methods = [
    name for name, method in inspect.getmembers(BaseProvider)
    if getattr(method, '__isabstractmethod__', False)
]
print(f'Abstract methods: {abstract_methods}')
"
```

Output yang diharapkan:

```
Cannot instantiate: Can't instantiate abstract class BaseProvider with abstract methods ...
Abstract methods: ['embedding', 'generate', 'name', 'stream', 'supports_image']
```

---

## 6. Output yang Diharapkan

### File: `app/providers/base.py`

Isi seperti Step 1 di atas.

### Contract Summary

| Method | Signature | Returns |
|---|---|---|
| `name` (property) | — | `str` |
| `generate()` | `(model, prompt, images?)` | `dict` |
| `stream()` | `(model, prompt, images?)` | `AsyncGenerator[str, None]` |
| `embedding()` | `(model, input_text)` | `list[float]` |
| `supports_image()` | `(model)` | `bool` |
| `close()` | — | `None` |

---

## 7. Dependencies

- **beta0.1.1 Task 1** — folder `app/providers/` dan `__init__.py` harus ada

---

## 8. Acceptance Criteria

- [ ] File `app/providers/base.py` ada
- [ ] `from app.providers.base import BaseProvider` berhasil
- [ ] `BaseProvider()` → `TypeError` (cannot instantiate abstract)
- [ ] 5 abstract members: `name`, `generate`, `stream`, `embedding`, `supports_image`
- [ ] `close()` adalah concrete method (default no-op)
- [ ] Semua methods memiliki docstring yang jelas
- [ ] Type hints lengkap di semua signatures

---

## 9. Estimasi

**Low** — Pure abstract class definition, no logic.
