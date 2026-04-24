# Task 3 — Exception Hierarchy

> **Modul**: beta0.1.1 — Foundation Core  
> **Estimasi**: Low (30–45 menit)  
> **Dependencies**: Task 1 (Project Scaffolding)

---

## 1. Judul Task

Implementasi `app/core/exceptions.py` — Custom exception hierarchy untuk seluruh aplikasi.

---

## 2. Deskripsi

Membuat kumpulan custom exception yang akan digunakan di seluruh layer (provider, service, endpoint). Setiap exception memiliki `message` dan `code` yang terstruktur, sehingga bisa di-convert menjadi JSON error response yang konsisten.

---

## 3. Tujuan Teknis

- Base exception `AIGatewayError` dengan atribut `message` dan `code`
- 6 subclass exception untuk skenario spesifik
- Setiap exception auto-generate message berdasarkan parameter
- Exception bisa di-raise dari layer manapun dan di-catch di global handler

---

## 4. Scope

### ✅ Yang Dikerjakan

- Implementasi `app/core/exceptions.py` dengan 7 exception class

### ❌ Yang Tidak Dikerjakan

- Exception handler di FastAPI (itu di task 6)
- HTTP status mapping (itu di task 6)
- Logging saat exception terjadi (itu di task 4 dan 6)

---

## 5. Langkah Implementasi

### Step 1: Buat `app/core/exceptions.py`

```python
"""
Custom exception hierarchy for AI Generative Core.

All application-level errors inherit from AIGatewayError.
Each exception carries a human-readable message and a machine-readable code,
enabling consistent JSON error responses across all endpoints.
"""


class AIGatewayError(Exception):
    """Base exception for all application errors."""

    def __init__(self, message: str, code: str):
        self.message = message
        self.code = code
        super().__init__(message)


class ProviderNotFoundError(AIGatewayError):
    """Raised when the requested provider does not exist or is disabled."""

    def __init__(self, provider: str):
        super().__init__(
            message=f"Provider '{provider}' not found or disabled",
            code="PROVIDER_NOT_FOUND",
        )


class ModelNotFoundError(AIGatewayError):
    """Raised when the requested model is not registered in the registry."""

    def __init__(self, provider: str, model: str):
        super().__init__(
            message=f"Model '{model}' not found for provider '{provider}'",
            code="MODEL_NOT_FOUND",
        )


class ModelCapabilityError(AIGatewayError):
    """Raised when a model doesn't support the requested capability."""

    def __init__(self, model: str, capability: str):
        super().__init__(
            message=f"Model '{model}' does not support '{capability}'",
            code="CAPABILITY_NOT_SUPPORTED",
        )


class ProviderConnectionError(AIGatewayError):
    """Raised when connection to a provider API fails."""

    def __init__(self, provider: str, detail: str = ""):
        msg = f"Cannot connect to '{provider}'"
        if detail:
            msg += f": {detail}"
        super().__init__(
            message=msg,
            code="PROVIDER_CONNECTION_ERROR",
        )


class ProviderTimeoutError(AIGatewayError):
    """Raised when a provider API request exceeds the timeout limit."""

    def __init__(self, provider: str, timeout: int):
        super().__init__(
            message=f"Request to '{provider}' timed out after {timeout}s",
            code="PROVIDER_TIMEOUT",
        )


class ProviderAPIError(AIGatewayError):
    """Raised when a provider returns an error response."""

    def __init__(self, provider: str, status: int, detail: str = ""):
        msg = f"Provider '{provider}' error (HTTP {status})"
        if detail:
            msg += f": {detail}"
        super().__init__(
            message=msg,
            code="PROVIDER_API_ERROR",
        )
```

### Step 2: Update `app/core/__init__.py`

```python
# app/core
```

Tidak perlu export apapun — exceptions akan di-import langsung dari module.

### Step 3: Verifikasi

```bash
python -c "
from app.core.exceptions import (
    AIGatewayError,
    ProviderNotFoundError,
    ModelNotFoundError,
    ModelCapabilityError,
    ProviderConnectionError,
    ProviderTimeoutError,
    ProviderAPIError,
)
e = ProviderNotFoundError('openai')
print(e.message)
print(e.code)
print(isinstance(e, AIGatewayError))
"
```

Output yang diharapkan:

```
Provider 'openai' not found or disabled
PROVIDER_NOT_FOUND
True
```

---

## 6. Output yang Diharapkan

### Exception Reference Table

| Class | Code | Contoh Message |
|---|---|---|
| `AIGatewayError` | (custom) | Base class |
| `ProviderNotFoundError` | `PROVIDER_NOT_FOUND` | Provider 'openai' not found or disabled |
| `ModelNotFoundError` | `MODEL_NOT_FOUND` | Model 'gpt-4' not found for provider 'openai' |
| `ModelCapabilityError` | `CAPABILITY_NOT_SUPPORTED` | Model 'llama3.2' does not support 'image' |
| `ProviderConnectionError` | `PROVIDER_CONNECTION_ERROR` | Cannot connect to 'ollama': Connection refused |
| `ProviderTimeoutError` | `PROVIDER_TIMEOUT` | Request to 'ollama' timed out after 120s |
| `ProviderAPIError` | `PROVIDER_API_ERROR` | Provider 'gemini' error (HTTP 429): Rate limited |

---

## 7. Dependencies

- **Task 1** — folder `app/core/` dan `__init__.py` harus ada

---

## 8. Acceptance Criteria

- [ ] File `app/core/exceptions.py` ada
- [ ] Semua 7 exception class bisa di-import tanpa error
- [ ] `AIGatewayError` punya atribut `message` dan `code`
- [ ] Semua subclass inherit dari `AIGatewayError`
- [ ] `ProviderNotFoundError("ollama").code` == `"PROVIDER_NOT_FOUND"`
- [ ] `ModelNotFoundError("ollama", "llama3").message` mengandung "llama3" dan "ollama"
- [ ] `ProviderConnectionError("ollama", "refused").message` mengandung "refused"
- [ ] `ProviderAPIError("gemini", 429, "rate limit").message` mengandung "429"

---

## 9. Estimasi

**Low** — Hanya class definitions, tidak ada logic kompleks.
