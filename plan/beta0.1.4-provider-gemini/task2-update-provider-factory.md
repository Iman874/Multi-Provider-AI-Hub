# Task 2 — Update Provider Factory

> **Modul**: beta0.1.4 — Gemini Provider  
> **Estimasi**: Low (10–15 menit)  
> **Dependencies**: Task 1 (GeminiProvider)

---

## 1. Judul Task

Update `app/providers/__init__.py` — Aktivasi Gemini case di factory function `create_provider()`.

---

## 2. Deskripsi

Mengganti placeholder Gemini di factory function dengan implementasi nyata. Saat `create_provider("gemini", settings)` dipanggil dan API key ada, factory akan return `GeminiProvider` instance. Jika API key kosong, return `None` dengan warning log.

---

## 3. Tujuan Teknis

- Case `"gemini"` di factory sekarang membuat `GeminiProvider` (bukan placeholder)
- Cek `GEMINI_API_KEY`: kosong → skip, ada → create instance
- Import `GeminiProvider` dari `app.providers.gemini`

---

## 4. Scope

### ✅ Yang Dikerjakan

- Update `app/providers/__init__.py`

### ❌ Yang Tidak Dikerjakan

- File lain — hanya factory yang berubah

---

## 5. Langkah Implementasi

### Step 1: Update `app/providers/__init__.py`

```python
"""
Provider factory for AI Generative Core.

Provides a single function to create provider instances by name.
"""

from loguru import logger

from app.config import Settings
from app.providers.base import BaseProvider
from app.providers.ollama import OllamaProvider
from app.providers.gemini import GeminiProvider


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
            if not settings.GEMINI_API_KEY:
                logger.warning("Gemini provider skipped: GEMINI_API_KEY not set")
                return None
            return GeminiProvider(
                api_key=settings.GEMINI_API_KEY,
                timeout=settings.GEMINI_TIMEOUT,
            )
        case _:
            raise ValueError(f"Unknown provider: '{provider_name}'")
```

### Step 2: Verifikasi

```bash
python -c "
from app.config import settings
from app.providers import create_provider

# Ollama — always works
ollama = create_provider('ollama', settings)
print(f'Ollama: {ollama.name}')

# Gemini — depends on API key
gemini = create_provider('gemini', settings)
if gemini:
    print(f'Gemini: {gemini.name}')
else:
    print('Gemini: skipped (no API key)')
"
```

---

## 6. Output yang Diharapkan

### File: `app/providers/__init__.py`

Perubahan dari beta0.1.3:

```diff
+from app.providers.gemini import GeminiProvider

         case "gemini":
-            # GeminiProvider will be implemented in beta0.1.4
             if not settings.GEMINI_API_KEY:
                 logger.warning("Gemini provider skipped: GEMINI_API_KEY not set")
                 return None
-            logger.warning("Gemini provider not yet implemented (beta0.1.4)")
-            return None
+            return GeminiProvider(
+                api_key=settings.GEMINI_API_KEY,
+                timeout=settings.GEMINI_TIMEOUT,
+            )
```

---

## 7. Dependencies

- **Task 1** — `GeminiProvider` harus sudah ada

---

## 8. Acceptance Criteria

- [ ] `create_provider("gemini", settings)` return `GeminiProvider` jika API key ada
- [ ] `create_provider("gemini", settings)` return `None` jika API key kosong
- [ ] `create_provider("ollama", settings)` tetap berfungsi (no regression)
- [ ] Warning log muncul saat Gemini di-skip
- [ ] Tidak ada `"not yet implemented"` placeholder lagi

---

## 9. Estimasi

**Low** — 3 baris berubah di file existing.
