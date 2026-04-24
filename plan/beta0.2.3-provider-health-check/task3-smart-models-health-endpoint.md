# Task 3 — Smart Model Listing & Health Providers Endpoint

## 1. Judul Task
Update `GET /models` untuk filter provider DOWN dan buat endpoint baru `GET /health/providers`

## 2. Deskripsi
Menambahkan "smart" filtering pada model listing agar model dari provider yang DOWN tidak muncul secara default, menambahkan field `available` ke response, dan membuat endpoint baru yang menampilkan detail status kesehatan semua provider dengan summary.

## 3. Tujuan Teknis
- `GET /api/v1/models` — secara default menyaring model dari provider DOWN
- `GET /api/v1/models?include_unavailable=true` — tampilkan semua model + field `available`
- `GET /health/providers` — detail status per provider + summary (total, up, down, degraded)
- Response schemas baru: `ModelInfoWithAvailability`, `ProviderHealthDetail`, `HealthProvidersResponse`

## 4. Scope
### Yang dikerjakan
- `app/schemas/responses.py` — tambah response schemas baru
- `app/api/endpoints/models.py` — update dengan `include_unavailable` param + health filter
- `app/main.py` — tambah endpoint `GET /health/providers`
- `app/api/dependencies.py` — tambah `get_health_checker()` dependency (getter only, init di Task 4)

### Yang TIDAK dikerjakan
- Inisialisasi HealthChecker di `initialize_services()` — Task 4
- Background monitor — Task 4
- Unit tests — Task 5

## 5. Langkah Implementasi

### Step 1: Tambah response schemas di `app/schemas/responses.py`
Tambahkan di akhir file:

```python
class ModelInfoWithAvailability(BaseModel):
    """
    Extended model info with provider availability status.
    """

    name: str = Field(
        ..., description="Model name", examples=["llama3.2", "gemini-2.5-pro"]
    )
    provider: str = Field(
        ..., description="Provider name", examples=["ollama", "gemini"]
    )
    supports_text: bool = Field(
        ..., description="Whether the model supports text generation"
    )
    supports_image: bool = Field(
        ..., description="Whether the model supports image/multimodal input"
    )
    supports_embedding: bool = Field(
        ..., description="Whether the model supports vector embedding"
    )
    available: bool = Field(
        ..., description="Whether the provider is currently available (UP or DEGRADED)"
    )


class ProviderHealthDetail(BaseModel):
    """Health status detail for a single provider."""

    status: str = Field(
        ..., description="Provider status: up, down, or degraded"
    )
    last_check: Optional[str] = Field(
        default=None, description="ISO timestamp of last health check"
    )
    last_success: Optional[str] = Field(
        default=None, description="ISO timestamp of last successful check"
    )
    latency_ms: Optional[float] = Field(
        default=None, description="Last probe latency in milliseconds"
    )
    consecutive_failures: int = Field(
        default=0, description="Number of consecutive probe failures"
    )
    error: Optional[str] = Field(
        default=None, description="Last error message"
    )


class HealthSummary(BaseModel):
    """Summary counts of provider health statuses."""

    total: int = Field(..., description="Total number of providers")
    up: int = Field(..., description="Providers in UP status")
    down: int = Field(..., description="Providers in DOWN status")
    degraded: int = Field(..., description="Providers in DEGRADED status")


class HealthProvidersResponse(BaseModel):
    """Response for GET /health/providers endpoint."""

    status: str = Field(
        ..., description="Overall system status: healthy, degraded, or unhealthy"
    )
    providers: dict[str, ProviderHealthDetail] = Field(
        ..., description="Per-provider health details"
    )
    summary: HealthSummary = Field(
        ..., description="Summary counts"
    )
```

### Step 2: Tambah `get_health_checker()` di `app/api/dependencies.py`
Tambah import dan singleton:

```python
# Di imports, tambahkan:
from app.services.health_checker import HealthChecker

# Di singleton instances, tambahkan:
_health_checker: HealthChecker | None = None
```

Tambah getter function:
```python
def get_health_checker() -> HealthChecker | None:
    """
    FastAPI dependency: provides HealthChecker instance.

    Returns None if health checker not initialized (graceful degradation).
    """
    return _health_checker
```

> **Note**: Inisialisasi `_health_checker` di `initialize_services()` dilakukan di Task 4. Untuk saat ini, getter mengembalikan `None` dan endpoints handle gracefully.

### Step 3: Update `app/api/endpoints/models.py`
Replace seluruh konten file:

```python
"""
Models endpoint — List available AI models and their capabilities.

Supports smart filtering based on provider health status.
Models from DOWN providers are hidden by default.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_model_registry, get_health_checker
from app.schemas.responses import ModelInfo, ModelInfoWithAvailability
from app.services.health_checker import HealthChecker
from app.services.model_registry import ModelRegistry

router = APIRouter()


@router.get(
    "/models",
    response_model=list[ModelInfoWithAvailability],
    summary="List available models",
    description="Returns all registered AI models with their capabilities. "
    "By default, models from DOWN providers are hidden. "
    "Use include_unavailable=true to show all models.",
)
async def list_models(
    provider: Optional[str] = Query(
        default=None,
        description="Filter models by provider (e.g. 'ollama', 'gemini')",
        examples=["ollama", "gemini"],
    ),
    include_unavailable: bool = Query(
        default=False,
        description="If true, include models from DOWN providers",
    ),
    registry: ModelRegistry = Depends(get_model_registry),
    health_checker: HealthChecker | None = Depends(get_health_checker),
) -> list[ModelInfoWithAvailability]:
    """
    List all available models, optionally filtered by provider.

    If health checker is active:
    - Default: only models from UP/DEGRADED providers
    - include_unavailable=true: all models with `available` field

    If health checker not initialized: all models shown as available.
    """
    models = registry.list_models(provider=provider)

    # Filter DOWN providers (unless include_unavailable is True)
    if not include_unavailable and health_checker:
        available_providers = health_checker.get_available_providers()
        models = [m for m in models if m.provider in available_providers]

    return [
        ModelInfoWithAvailability(
            name=m.name,
            provider=m.provider,
            supports_text=m.supports_text,
            supports_image=m.supports_image,
            supports_embedding=m.supports_embedding,
            available=(
                health_checker.is_provider_up(m.provider)
                if health_checker
                else True
            ),
        )
        for m in models
    ]
```

### Step 4: Tambah `GET /health/providers` di `app/main.py`
Tambahkan endpoint di `app/main.py`, setelah existing `/health` endpoint:

```python
from datetime import datetime, timezone

# Import tambahan di bagian atas file:
from app.api.dependencies import initialize_services, get_providers, get_health_checker
from app.schemas.responses import (
    HealthProvidersResponse,
    ProviderHealthDetail,
    HealthSummary,
)
```

Tambah endpoint:
```python
@app.get(
    "/health/providers",
    response_model=HealthProvidersResponse,
    tags=["System"],
    summary="Provider health status",
    description="Returns detailed health status for all AI providers.",
)
async def health_providers() -> HealthProvidersResponse:
    """Detailed health status for all AI providers."""
    health_checker = get_health_checker()

    if health_checker is None:
        # Health checker not initialized yet
        return HealthProvidersResponse(
            status="healthy",
            providers={},
            summary=HealthSummary(total=0, up=0, down=0, degraded=0),
        )

    all_statuses = health_checker.get_all_statuses()
    providers_detail = {}

    for name, status in all_statuses.items():
        providers_detail[name] = ProviderHealthDetail(
            status=status.status,
            last_check=(
                datetime.fromtimestamp(status.last_check, tz=timezone.utc).isoformat()
                if status.last_check
                else None
            ),
            last_success=(
                datetime.fromtimestamp(status.last_success, tz=timezone.utc).isoformat()
                if status.last_success
                else None
            ),
            latency_ms=status.latency_ms,
            consecutive_failures=status.consecutive_failures,
            error=status.error_message,
        )

    # Summary
    statuses_list = [s.status for s in all_statuses.values()]
    summary = HealthSummary(
        total=len(statuses_list),
        up=statuses_list.count("up"),
        down=statuses_list.count("down"),
        degraded=statuses_list.count("degraded"),
    )

    return HealthProvidersResponse(
        status=health_checker.get_overall_status(),
        providers=providers_detail,
        summary=summary,
    )
```

## 6. Output yang Diharapkan

### `GET /api/v1/models` (default — filter DOWN)
Saat Ollama UP dan Gemini DOWN:
```json
[
    {
        "name": "llama3.2",
        "provider": "ollama",
        "supports_text": true,
        "supports_image": true,
        "supports_embedding": false,
        "available": true
    }
]
```
Gemini models tidak muncul karena DOWN.

### `GET /api/v1/models?include_unavailable=true`
```json
[
    {
        "name": "llama3.2",
        "provider": "ollama",
        "supports_text": true,
        "supports_image": true,
        "supports_embedding": false,
        "available": true
    },
    {
        "name": "gemini-2.5-pro",
        "provider": "gemini",
        "supports_text": true,
        "supports_image": true,
        "supports_embedding": false,
        "available": false
    }
]
```

### `GET /health/providers`
```json
{
    "status": "degraded",
    "providers": {
        "ollama": {
            "status": "up",
            "last_check": "2026-04-23T10:00:00+00:00",
            "last_success": "2026-04-23T10:00:00+00:00",
            "latency_ms": 12.5,
            "consecutive_failures": 0,
            "error": null
        },
        "gemini": {
            "status": "down",
            "last_check": "2026-04-23T10:00:00+00:00",
            "last_success": "2026-04-23T09:55:00+00:00",
            "latency_ms": null,
            "consecutive_failures": 5,
            "error": "Connection refused"
        }
    },
    "summary": {
        "total": 2,
        "up": 1,
        "down": 1,
        "degraded": 0
    }
}
```

## 7. Dependencies
- **Task 1** — Config fields, `ProviderStatus` dataclass
- **Task 2** — `HealthChecker` class (service logic)

## 8. Acceptance Criteria
- [ ] `ModelInfoWithAvailability` schema — extends `ModelInfo` with `available` field
- [ ] `ProviderHealthDetail` schema — status, timestamps, latency, failures, error
- [ ] `HealthSummary` schema — total, up, down, degraded counts
- [ ] `HealthProvidersResponse` schema — status, providers dict, summary
- [ ] `get_health_checker()` dependency — returns `None` jika belum initialized
- [ ] `GET /api/v1/models` — default: filter model dari provider DOWN
- [ ] `GET /api/v1/models?include_unavailable=true` — tampilkan semua dengan `available` field
- [ ] `GET /api/v1/models` — graceful jika `health_checker` is None (show all as available)
- [ ] `GET /health/providers` — detail status + summary + overall status
- [ ] `GET /health/providers` — graceful jika health checker belum init (empty response)
- [ ] Timestamps di-format ISO 8601
- [ ] Endpoints muncul di Swagger UI (`/docs`)
- [ ] Server bisa start tanpa error
- [ ] Semua existing tests tetap PASS

## 9. Estimasi
Medium (~30 menit)
