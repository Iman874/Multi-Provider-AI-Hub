"""
Models endpoint — List available AI models and their capabilities.
"""

from collections import defaultdict
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_model_registry, get_health_checker
from app.schemas.responses import ModelInfoWithAvailability
from app.services.model_registry import ModelRegistry
from app.services.health_checker import HealthChecker

router = APIRouter()


@router.get(
    "/models",
    response_model=list[ModelInfoWithAvailability],
    summary="List available models",
    description="Returns registered AI models with their capabilities. "
    "Use `limit` to control how many models per provider are shown (default 3, 0 = all). "
    "Models from DOWN providers are hidden by default.",
)
async def list_models(
    provider: Optional[str] = Query(
        default=None,
        description="Filter models by provider (e.g. 'ollama', 'gemini', 'nvidia')",
        examples=["ollama", "gemini", "nvidia"],
    ),
    limit: int = Query(
        default=3,
        ge=0,
        description="Max models per provider (0 = show all). Default 3.",
    ),
    include_unavailable: bool = Query(
        default=False,
        description="If true, includes models from DOWN providers",
    ),
    registry: ModelRegistry = Depends(get_model_registry),
    health_checker: HealthChecker | None = Depends(get_health_checker),
) -> list[ModelInfoWithAvailability]:
    """
    List available models with optional per-provider limit.
    """
    models = registry.list_models(provider=provider)
    result = []

    # Track count per provider for limit enforcement
    provider_counts: dict[str, int] = defaultdict(int)

    for m in models:
        # Determine availability
        available = True
        if health_checker is not None:
            available = health_checker.is_provider_up(m.provider)

        # Skip unavailable models unless explicitly requested
        if not available and not include_unavailable:
            continue

        # Enforce per-provider limit (0 = unlimited)
        if limit > 0 and provider_counts[m.provider] >= limit:
            continue

        provider_counts[m.provider] += 1

        result.append(
            ModelInfoWithAvailability(
                name=m.name,
                provider=m.provider,
                supports_text=m.supports_text,
                supports_image=m.supports_image,
                supports_embedding=m.supports_embedding,
                supports_reasoning=m.supports_reasoning,
                available=available,
            )
        )

    return result
