# Task 4 — Cache Endpoints (Stats & Clear)

## 1. Judul Task
Implementasi endpoint `GET /api/v1/cache/stats` dan `DELETE /api/v1/cache`, response schemas, dan register di router

## 2. Deskripsi
Membuat 2 endpoint baru untuk monitoring dan management cache: endpoint stats untuk melihat hit rate, ukuran, dan eviction count, serta endpoint clear untuk flush semua cache entries. Termasuk Pydantic response schemas.

## 3. Tujuan Teknis
- `GET /api/v1/cache/stats` — return cache statistics (hits, misses, hit_rate, size, evictions)
- `DELETE /api/v1/cache` — flush semua entries, return count removed
- Pydantic response schemas: `CacheStatsResponse`, `CacheClearResponse`
- Router terdaftar dengan tag "Cache"
- Endpoints muncul di Swagger UI

## 4. Scope
### Yang dikerjakan
- `app/schemas/responses.py` — tambah `CacheStatsResponse` dan `CacheClearResponse`
- `app/api/endpoints/cache.py` — file baru (2 endpoints)
- `app/api/router.py` — register cache router

### Yang TIDAK dikerjakan
- CacheService logic (sudah Task 2)
- GeneratorService integration (sudah Task 3)
- Unit tests — Task 5

## 5. Langkah Implementasi

### Step 1: Tambah response schemas di `app/schemas/responses.py`
Tambahkan di akhir file, setelah class `ErrorResponse`:

```python
class CacheStatsResponse(BaseModel):
    """Response for GET /cache/stats endpoint."""

    total_hits: int = Field(
        ..., description="Total number of cache hits"
    )
    total_misses: int = Field(
        ..., description="Total number of cache misses"
    )
    hit_rate: float = Field(
        ..., description="Cache hit rate (0.0 to 1.0)"
    )
    current_size: int = Field(
        ..., description="Current number of entries in cache"
    )
    max_size: int = Field(
        ..., description="Maximum cache capacity"
    )
    evictions: int = Field(
        ..., description="Total LRU evictions performed"
    )


class CacheClearResponse(BaseModel):
    """Response for DELETE /cache endpoint."""

    message: str = Field(
        ..., description="Confirmation message"
    )
    entries_removed: int = Field(
        ..., description="Number of entries that were cleared"
    )
```

### Step 2: Buat `app/api/endpoints/cache.py`

```python
"""
Cache endpoints — Cache statistics and management.

Provides endpoints to monitor cache performance (hit rate, size)
and to clear the cache when needed.
"""

from fastapi import APIRouter, Depends

from app.api.dependencies import get_cache_service
from app.schemas.responses import CacheStatsResponse, CacheClearResponse
from app.services.cache_service import CacheService

router = APIRouter()


@router.get(
    "/cache/stats",
    response_model=CacheStatsResponse,
    summary="Get cache statistics",
    description="Returns cache performance metrics including "
    "hit rate, current size, and eviction count.",
)
async def cache_stats(
    cache: CacheService | None = Depends(get_cache_service),
) -> CacheStatsResponse:
    """Return current cache statistics."""
    if cache is None:
        # Cache not initialized — return empty stats
        return CacheStatsResponse(
            total_hits=0,
            total_misses=0,
            hit_rate=0.0,
            current_size=0,
            max_size=0,
            evictions=0,
        )

    stats = cache.get_stats()
    return CacheStatsResponse(
        total_hits=stats.total_hits,
        total_misses=stats.total_misses,
        hit_rate=round(stats.hit_rate, 4),
        current_size=stats.current_size,
        max_size=stats.max_size,
        evictions=stats.evictions,
    )


@router.delete(
    "/cache",
    response_model=CacheClearResponse,
    summary="Clear cache",
    description="Remove all entries from the response cache.",
)
async def clear_cache(
    cache: CacheService | None = Depends(get_cache_service),
) -> CacheClearResponse:
    """Clear all cached entries."""
    if cache is None:
        return CacheClearResponse(
            message="Cache not available",
            entries_removed=0,
        )

    count = cache.clear()
    return CacheClearResponse(
        message="Cache cleared",
        entries_removed=count,
    )
```

### Step 3: Update `app/api/router.py`
Tambah import dan register cache router:

```python
# Di imports, tambahkan:
from app.api.endpoints import models, generate, stream, embedding, cache

# Register router, tambahkan baris baru:
api_router.include_router(cache.router, tags=["Cache"])
```

File lengkap setelah update:
```python
"""
Central API router that combines all endpoint routers.
"""

from fastapi import APIRouter

from app.api.endpoints import models, generate, stream, embedding, cache

api_router = APIRouter(prefix="/api/v1")

# --- Register endpoint routers ---
api_router.include_router(models.router, tags=["Models"])
api_router.include_router(generate.router, tags=["Generation"])
api_router.include_router(stream.router, tags=["Streaming"])
api_router.include_router(embedding.router, tags=["Embedding"])
api_router.include_router(cache.router, tags=["Cache"])
```

## 6. Output yang Diharapkan

### `GET /api/v1/cache/stats`
```bash
curl http://localhost:8000/api/v1/cache/stats
```
```json
{
    "total_hits": 42,
    "total_misses": 158,
    "hit_rate": 0.21,
    "current_size": 87,
    "max_size": 1000,
    "evictions": 3
}
```

### `GET /api/v1/cache/stats` (cache kosong, baru start)
```json
{
    "total_hits": 0,
    "total_misses": 0,
    "hit_rate": 0.0,
    "current_size": 0,
    "max_size": 1000,
    "evictions": 0
}
```

### `DELETE /api/v1/cache`
```bash
curl -X DELETE http://localhost:8000/api/v1/cache
```
```json
{
    "message": "Cache cleared",
    "entries_removed": 87
}
```

### `DELETE /api/v1/cache` (cache sudah kosong)
```json
{
    "message": "Cache cleared",
    "entries_removed": 0
}
```

### Swagger UI verification
Buka `http://localhost:8000/docs` dan verifikasi:
- Section "Cache" muncul
- `GET /api/v1/cache/stats` terdaftar
- `DELETE /api/v1/cache` terdaftar
- Response schemas terlihat benar

## 7. Dependencies
- **Task 1** — Config fields
- **Task 2** — `CacheService` class (`get_stats()`, `clear()`)
- **Task 3** — `get_cache_service()` dependency

## 8. Acceptance Criteria
- [ ] `CacheStatsResponse` schema — total_hits, total_misses, hit_rate, current_size, max_size, evictions
- [ ] `CacheClearResponse` schema — message, entries_removed
- [ ] `GET /api/v1/cache/stats` → 200 + cache statistics
- [ ] `GET /api/v1/cache/stats` — graceful jika cache None (returns zeros)
- [ ] `hit_rate` di-round ke 4 desimal
- [ ] `DELETE /api/v1/cache` → 200 + confirmation + count removed
- [ ] `DELETE /api/v1/cache` — graceful jika cache None
- [ ] Cache router terdaftar di `api_router` dengan tag "Cache"
- [ ] Endpoints muncul di Swagger UI (`/docs`)
- [ ] Server bisa start tanpa error
- [ ] Semua existing tests tetap PASS

## 9. Estimasi
Low (~20 menit)
