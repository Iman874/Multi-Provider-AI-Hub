# Task 5 — Provider Factory & Dependency Integration

> **Modul**: beta0.1.9 — Multi API Key Management  
> **Estimasi**: Medium (30 menit)  
> **Dependencies**: Task 1, Task 2, Task 3, Task 4

---

## 1. Judul Task

Update provider factory dan error handler agar menginisialisasi `KeyManager` dari `.env` dan meneruskannya ke provider constructor.

---

## 2. Deskripsi

Saat ini `create_provider()` di `app/providers/__init__.py` membuat `OllamaProvider(base_url, timeout)` dan `GeminiProvider(api_key, timeout)`. Task ini mengubahnya agar:
- Ollama: parse `OLLAMA_API_KEYS` → buat `KeyManager` → pass ke `OllamaProvider`
- Gemini: parse `GEMINI_API_KEYS` (fallback `GEMINI_API_KEY`) → buat `KeyManager` → pass ke `GeminiProvider`
- Error handler di `app/main.py` menangani `AllKeysExhaustedError` → HTTP 503

---

## 3. Tujuan Teknis

- `create_provider()` membuat `KeyManager` instances untuk kedua provider
- Helper function `_parse_keys(csv_string)` untuk parsing comma-separated keys
- Error handler `AllKeysExhaustedError` → 503
- Log jumlah key saat startup (tanpa expose key)

---

## 4. Scope

### ✅ Yang Dikerjakan
- Edit `app/providers/__init__.py`
- Edit `app/main.py` — tambah error handler
- Verifikasi server startup

### ❌ Yang Tidak Dikerjakan
- Testing (Task 6)
- Frontend changes (out of scope)

---

## 5. Langkah Implementasi

### Step 1: Edit `app/providers/__init__.py`

```python
"""
Provider factory for AI Generative Core.
"""

from loguru import logger

from app.config import Settings
from app.providers.base import BaseProvider
from app.providers.ollama import OllamaProvider
from app.providers.gemini import GeminiProvider
from app.services.key_manager import KeyManager


def _parse_keys(csv_string: str) -> list[str]:
    """
    Parse comma-separated API keys string into a list.

    Strips whitespace, filters empty strings.
    "key1,key2,key3" → ["key1", "key2", "key3"]
    "" → []
    """
    if not csv_string or not csv_string.strip():
        return []
    return [k.strip() for k in csv_string.split(",") if k.strip()]


def create_provider(provider_name: str, settings: Settings) -> BaseProvider | None:
    """
    Factory function to create a provider instance by name.
    """
    match provider_name:
        case "ollama":
            # Parse Ollama Cloud API keys (opsional)
            ollama_keys = _parse_keys(settings.OLLAMA_API_KEYS)
            key_manager = None
            if ollama_keys:
                key_manager = KeyManager(
                    name="ollama_cloud",
                    keys=ollama_keys,
                )
                logger.info(
                    "Ollama Cloud: {count} API key(s) loaded",
                    count=len(ollama_keys),
                )

            return OllamaProvider(
                base_url=settings.OLLAMA_BASE_URL,
                timeout=settings.OLLAMA_TIMEOUT,
                key_manager=key_manager,
            )

        case "gemini":
            # Parse Gemini API keys (multi → fallback single)
            gemini_keys = _parse_keys(settings.GEMINI_API_KEYS)
            if not gemini_keys:
                # Fallback ke single key lama
                if settings.GEMINI_API_KEY:
                    gemini_keys = [settings.GEMINI_API_KEY]
                else:
                    logger.warning(
                        "Gemini provider skipped: no API keys configured"
                    )
                    return None

            key_manager = KeyManager(
                name="gemini",
                keys=gemini_keys,
            )
            logger.info(
                "Gemini: {count} API key(s) loaded",
                count=len(gemini_keys),
            )

            return GeminiProvider(
                key_manager=key_manager,
                timeout=settings.GEMINI_TIMEOUT,
            )

        case _:
            raise ValueError(f"Unknown provider: '{provider_name}'")
```

### Step 2: Edit `app/main.py` — tambah error handler

Tambahkan import dan error handler baru:

```python
from app.core.exceptions import AIGatewayError, AllKeysExhaustedError

# Di bagian error handlers, tambahkan:
@app.exception_handler(AllKeysExhaustedError)
async def all_keys_exhausted_handler(request, exc: AllKeysExhaustedError):
    return JSONResponse(
        status_code=503,
        content={"error": exc.message, "code": exc.code},
    )
```

**Catatan**: Jika sudah ada generic handler untuk `AIGatewayError`, pastikan `AllKeysExhaustedError` di-handle sebelum generic handler, atau update generic handler agar mengembalikan status 503 untuk code `ALL_KEYS_EXHAUSTED`.

### Step 3: Verifikasi server startup

```powershell
.\venv\Scripts\python -c "
from app.config import settings
from app.providers import create_provider

ollama = create_provider('ollama', settings)
print('Ollama created:', ollama is not None)

gemini = create_provider('gemini', settings)
print('Gemini created:', gemini is not None)
"
```

---

## 6. Output yang Diharapkan

### Log startup (contoh):
```
INFO | KeyManager 'ollama_cloud' initialized: 1 key(s), cooldown=60s
INFO | Ollama Cloud: 1 API key(s) loaded
INFO | OllamaProvider initialized: http://localhost:11434 (timeout=120s, cloud_keys=1)
INFO | KeyManager 'gemini' initialized: 1 key(s), cooldown=60s
INFO | Gemini: 1 API key(s) loaded
INFO | GeminiProvider initialized (timeout=120s, keys=1)
```

### Error response (semua key habis):
```json
HTTP 503

{
  "error": "All API keys for 'gemini' are exhausted or rate-limited",
  "code": "ALL_KEYS_EXHAUSTED"
}
```

---

## 7. Dependencies

- **Task 1** — Config fields + `AllKeysExhaustedError`
- **Task 2** — `KeyManager` class
- **Task 3** — `OllamaProvider` menerima `key_manager`
- **Task 4** — `GeminiProvider` menerima `key_manager`

---

## 8. Acceptance Criteria

- [ ] Server startup berhasil dengan `.env` baru (multi-key format)
- [ ] Server startup berhasil dengan `.env` lama (single key, backward compatible)
- [ ] Server startup berhasil tanpa API key apapun (Gemini di-skip, Ollama lokal jalan)
- [ ] Log startup menunjukkan jumlah key (BUKAN key-nya)
- [ ] `AllKeysExhaustedError` → HTTP 503 response
- [ ] `_parse_keys("a,b,c")` → `["a", "b", "c"]`
- [ ] `_parse_keys("")` → `[]`
- [ ] `_parse_keys("  a , b , c  ")` → `["a", "b", "c"]` (whitespace stripped)

---

## 9. Estimasi

**Medium** — Modifikasi 2 file, logic parsing sederhana, tapi perlu verifikasi backward compatibility.
