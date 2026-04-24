# Task 3 — Provider Factory

> **Modul**: beta0.1.3 — Provider Abstraction & Ollama  
> **Estimasi**: Low (20–30 menit)  
> **Dependencies**: Task 2 (OllamaProvider)

---

## 1. Judul Task

Implementasi `app/providers/__init__.py` — Factory function `create_provider()` yang instantiate provider berdasarkan nama.

---

## 2. Deskripsi

Membuat factory function yang berfungsi sebagai single entry point untuk membuat provider instances. Function ini menerima nama provider dan settings, lalu return instance `BaseProvider` yang sesuai. Ini memastikan provider creation logic terpusat di satu tempat.

---

## 3. Tujuan Teknis

- Function `create_provider(provider_name, settings)` → `BaseProvider`
- Match `"ollama"` → return `OllamaProvider`
- Match `"gemini"` → skip dengan log warning (belum implemented)
- Unknown → raise `ValueError`

---

## 4. Scope

### ✅ Yang Dikerjakan

- Implementasi `app/providers/__init__.py` (overwrite existing empty `__init__.py`)

### ❌ Yang Tidak Dikerjakan

- GeminiProvider creation → beta0.1.4

---

## 5. Langkah Implementasi

### Step 1: Buat `app/providers/__init__.py`

```python
"""
Provider factory for AI Generative Core.

Provides a single function to create provider instances by name.
This is the only place where provider classes are imported and instantiated.
"""

from loguru import logger

from app.config import Settings
from app.providers.base import BaseProvider
from app.providers.ollama import OllamaProvider


def create_provider(provider_name: str, settings: Settings) -> BaseProvider | None:
    """
    Factory function to create a provider instance by name.

    Args:
        provider_name: Provider identifier ("ollama", "gemini", etc.)
        settings: Application settings with provider configuration.

    Returns:
        BaseProvider instance, or None if the provider should be skipped.

    Raises:
        ValueError: If the provider name is not recognized.
    """
    match provider_name:
        case "ollama":
            return OllamaProvider(
                base_url=settings.OLLAMA_BASE_URL,
                timeout=settings.OLLAMA_TIMEOUT,
            )
        case "gemini":
            # GeminiProvider will be implemented in beta0.1.4
            if not settings.GEMINI_API_KEY:
                logger.warning("Gemini provider skipped: GEMINI_API_KEY not set")
                return None
            logger.warning("Gemini provider not yet implemented (beta0.1.4)")
            return None
        case _:
            raise ValueError(f"Unknown provider: '{provider_name}'")
```

### Step 2: Verifikasi

```bash
python -c "
from app.config import settings
from app.providers import create_provider
from app.providers.base import BaseProvider

# Create Ollama provider
provider = create_provider('ollama', settings)
print(f'Created: {provider.name}')
print(f'Is BaseProvider: {isinstance(provider, BaseProvider)}')

# Gemini → None (not implemented yet)
gemini = create_provider('gemini', settings)
print(f'Gemini: {gemini}')

# Unknown → error
try:
    create_provider('openai', settings)
except ValueError as e:
    print(f'Error: {e}')
"
```

Output:

```
Created: ollama
Is BaseProvider: True
Gemini: None
Error: Unknown provider: 'openai'
```

---

## 6. Output yang Diharapkan

### File: `app/providers/__init__.py`

Isi seperti Step 1 di atas.

### Behavior

| Input | Output |
|---|---|
| `"ollama"` | `OllamaProvider` instance |
| `"gemini"` (no API key) | `None` + warning log |
| `"gemini"` (with API key) | `None` + "not yet implemented" warning |
| `"openai"` | `ValueError` |

---

## 7. Dependencies

- **Task 2** — `OllamaProvider` dari `app/providers/ollama.py`
- **beta0.1.1 Task 2** — `Settings` dari `app/config.py`

---

## 8. Acceptance Criteria

- [ ] File `app/providers/__init__.py` berisi factory function (bukan empty)
- [ ] `create_provider("ollama", settings)` return `OllamaProvider`
- [ ] `create_provider("gemini", settings)` return `None` (stub)
- [ ] `create_provider("openai", settings)` raise `ValueError`
- [ ] Return type is `BaseProvider | None`
- [ ] Warning log muncul saat Gemini di-skip

---

## 9. Estimasi

**Low** — Simple match/case factory.
