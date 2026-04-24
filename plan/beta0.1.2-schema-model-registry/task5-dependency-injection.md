# Task 5 — Dependency Injection Setup

> **Modul**: beta0.1.2 — Schema & Model Registry  
> **Estimasi**: Low (30–45 menit)  
> **Dependencies**: Task 4 (Model Registry), beta0.1.1 Task 2 (Config)

---

## 1. Judul Task

Implementasi `app/api/dependencies.py` — Dependency injection setup dengan `initialize_services()` dan FastAPI `Depends()` functions untuk ModelRegistry.

---

## 2. Deskripsi

Membuat modul dependency injection yang menyediakan service instances ke FastAPI endpoints via `Depends()`. Saat startup, `initialize_services()` dipanggil untuk membuat dan menyimpan singleton instances. Endpoints kemudian menggunakan `get_model_registry()` sebagai dependency.

---

## 3. Tujuan Teknis

- Global variable `_model_registry` yang di-initialize saat startup
- Function `initialize_services(settings)` yang membuat registry dan register defaults
- Function `get_model_registry()` untuk FastAPI Depends injection
- Placeholder untuk `_generator_service` (akan diisi di beta0.1.3)

---

## 4. Scope

### ✅ Yang Dikerjakan

- Implementasi `app/api/dependencies.py`
- `initialize_services()` — init ModelRegistry
- `get_model_registry()` — Depends function

### ❌ Yang Tidak Dikerjakan

- GeneratorService initialization → beta0.1.3
- Provider initialization → beta0.1.3
- `get_generator_service()` → stub saja, implementasi di beta0.1.3

---

## 5. Langkah Implementasi

### Step 1: Buat `app/api/dependencies.py`

```python
"""
FastAPI dependency injection setup.

Provides singleton service instances to endpoints via Depends().
Services are initialized once during application startup via
initialize_services() and then injected into endpoint functions.
"""

from loguru import logger

from app.config import Settings
from app.services.model_registry import ModelRegistry


# --- Singleton instances (initialized at startup) ---
_model_registry: ModelRegistry | None = None


def get_model_registry() -> ModelRegistry:
    """
    FastAPI dependency that provides the ModelRegistry instance.

    Usage in endpoint:
        @router.get("/models")
        async def list_models(registry: ModelRegistry = Depends(get_model_registry)):
            ...
    """
    if _model_registry is None:
        raise RuntimeError("ModelRegistry not initialized. Call initialize_services() first.")
    return _model_registry


def initialize_services(settings: Settings) -> None:
    """
    Initialize all service singletons.

    Called once during application startup (in main.py lifespan).
    Creates and configures all services needed by the API endpoints.

    Args:
        settings: Application settings instance.
    """
    global _model_registry

    # --- Model Registry ---
    _model_registry = ModelRegistry()
    _model_registry.register_defaults()

    model_count = len(_model_registry.list_models())
    logger.info(
        "Services initialized: {count} models registered",
        count=model_count,
    )
```

### Step 2: Verifikasi

```bash
python -c "
from app.config import settings
from app.api.dependencies import initialize_services, get_model_registry

# Before init → should raise
try:
    get_model_registry()
except RuntimeError as e:
    print(f'Before init: {e}')

# Initialize
initialize_services(settings)

# After init → should work
registry = get_model_registry()
print(f'After init: {len(registry.list_models())} models')
"
```

Output yang diharapkan:

```
Before init: ModelRegistry not initialized. Call initialize_services() first.
After init: 6 models
```

---

## 6. Output yang Diharapkan

### File: `app/api/dependencies.py`

Isi seperti Step 1 di atas.

### Behavior

| State | `get_model_registry()` |
|---|---|
| Before `initialize_services()` | Raise `RuntimeError` |
| After `initialize_services()` | Return `ModelRegistry` instance |

---

## 7. Dependencies

- **Task 4** — `ModelRegistry` dari `app/services/model_registry.py`
- **beta0.1.1 Task 2** — `Settings` dari `app/config.py`

---

## 8. Acceptance Criteria

- [ ] File `app/api/dependencies.py` ada
- [ ] `initialize_services(settings)` berjalan tanpa error
- [ ] `get_model_registry()` return `ModelRegistry` instance setelah init
- [ ] `get_model_registry()` raise `RuntimeError` sebelum init
- [ ] Registry berisi 6 default models setelah init
- [ ] Log message "Services initialized: 6 models registered" muncul

---

## 9. Estimasi

**Low** — Straightforward DI pattern.
