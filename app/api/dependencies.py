"""
FastAPI dependency injection setup.

Provides singleton service instances to endpoints via Depends().
Services are initialized once during application startup.
"""

from loguru import logger

from app.config import Settings
from app.providers import create_provider
from app.providers.base import BaseProvider
from app.services.generator import GeneratorService
from app.services.model_registry import ModelRegistry
from app.services.session_manager import SessionManager
from app.services.cache_service import CacheService
from app.services.health_checker import HealthChecker
from app.services.batch_service import BatchService


# --- Singleton instances ---
_model_registry: ModelRegistry | None = None
_generator_service: GeneratorService | None = None
_providers: dict[str, BaseProvider] = {}
_session_manager: SessionManager | None = None
_cache_service: CacheService | None = None
_health_checker: HealthChecker | None = None
_batch_service: BatchService | None = None


def get_model_registry() -> ModelRegistry:
    """FastAPI dependency: provides ModelRegistry instance."""
    if _model_registry is None:
        raise RuntimeError("ModelRegistry not initialized. Call initialize_services() first.")
    return _model_registry


def get_generator_service() -> GeneratorService:
    """FastAPI dependency: provides GeneratorService instance."""
    if _generator_service is None:
        raise RuntimeError("GeneratorService not initialized. Call initialize_services() first.")
    return _generator_service


def get_session_manager() -> SessionManager:
    """FastAPI dependency: provides SessionManager instance."""
    if _session_manager is None:
        raise RuntimeError("SessionManager not initialized. Call initialize_services() first.")
    return _session_manager


def get_cache_service() -> CacheService | None:
    """FastAPI dependency: provides CacheService instance."""
    return _cache_service


def get_health_checker() -> HealthChecker | None:
    """FastAPI dependency: provides HealthChecker instance."""
    return _health_checker


def get_batch_service() -> BatchService:
    """FastAPI dependency: provides BatchService instance."""
    if _batch_service is None:
        raise RuntimeError("BatchService not initialized. Call initialize_services() first.")
    return _batch_service


def get_providers() -> dict[str, BaseProvider]:
    """Get all active provider instances (for shutdown cleanup)."""
    return _providers


def initialize_services(settings: Settings) -> None:
    """
    Initialize all service singletons.

    Called once during application startup. Creates:
    1. AI Providers (Ollama, and Gemini when available)
    2. Model Registry with default models
    3. Generator Service that orchestrates providers

    Args:
        settings: Application settings instance.
    """
    global _model_registry, _generator_service, _providers, _session_manager, _cache_service, _health_checker, _batch_service

    # --- 1. Create providers ---
    provider_names = ["ollama", "gemini", "nvidia"]
    for name in provider_names:
        provider = create_provider(name, settings)
        if provider is not None:
            _providers[name] = provider

    logger.info(
        "Active providers: {providers}",
        providers=list(_providers.keys()),
    )

    # --- 2. Create Model Registry ---
    _model_registry = ModelRegistry()


    # --- 3. Create Cache Service ---
    _cache_service = CacheService(
        enabled=settings.CACHE_ENABLED,
        ttl=settings.CACHE_TTL,
        max_size=settings.CACHE_MAX_SIZE,
    )

    # --- 4. Create Health Checker ---
    _health_checker = HealthChecker(
        providers=_providers,
        timeout=settings.HEALTH_CHECK_TIMEOUT,
        threshold=settings.HEALTH_CHECK_THRESHOLD,
    )

    # --- 5. Create Generator Service ---
    _generator_service = GeneratorService(
        providers=_providers,
        registry=_model_registry,
        cache=_cache_service,
        health_checker=_health_checker,
    )

    # --- 6. Create Session Manager ---
    _session_manager = SessionManager(
        max_history=settings.CHAT_MAX_HISTORY,
        ttl_minutes=settings.CHAT_SESSION_TTL,
    )

    # --- 7. Create Batch Service ---
    _batch_service = BatchService(
        generator=_generator_service,
        max_size=settings.BATCH_MAX_SIZE,
        concurrency=settings.BATCH_CONCURRENCY,
    )

async def initialize_dynamic_models() -> None:
    """
    Fetch and register models dynamically from all active providers.
    
    Should be called from an async context (e.g. application lifespan)
    after initialize_services() has created the provider instances.
    """
    global _model_registry, _providers
    if _model_registry is None:
        return
        
    total_models = 0
    for name, provider in _providers.items():
        try:
            models = await provider.fetch_models()
            for model in models:
                _model_registry.register(model)
                total_models += 1
        except Exception as e:
            logger.error("Failed to fetch models for {name}: {err}", name=name, err=str(e))
            
    logger.info(
        "Model registry: {count} models registered dynamically",
        count=total_models,
    )
