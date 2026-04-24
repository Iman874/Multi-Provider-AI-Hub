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
