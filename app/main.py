"""
AI Generative Core — FastAPI Application Entry Point.

Run with: uvicorn app.main:app --reload --port 8000
"""

from contextlib import asynccontextmanager
import asyncio

from datetime import datetime, timezone

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from app.config import settings
from app.core.exceptions import (
    AIGatewayError,
    AllKeysExhaustedError,
    AuthenticationError,
    RateLimitExceededError,
)
from app.core.logging import setup_logging
from app.core.middleware import RequestLoggingMiddleware
from app.api.dependencies import (
    initialize_services,
    initialize_dynamic_models,
    get_providers,
    get_session_manager,
    get_health_checker,
)
from app.api.router import api_router
from app.schemas.responses import (
    HealthProvidersResponse,
    ProviderHealthDetail,
    HealthSummary,
)


async def _session_cleanup_loop(interval: int = 300):
    """
    Background task — periodically cleanup expired chat sessions.

    Runs every `interval` seconds (default 5 minutes).
    Calls SessionManager.cleanup_expired() to remove sessions
    that exceeded their TTL.

    Args:
        interval: Seconds between cleanup runs (default 300 = 5 minutes).
    """
    while True:
        await asyncio.sleep(interval)
        try:
            session_mgr = get_session_manager()
            count = session_mgr.cleanup_expired()
            if count > 0:
                logger.info(
                    "Session cleanup: removed {n} expired sessions",
                    n=count,
                )
        except Exception as e:
            logger.error("Session cleanup error: {err}", err=str(e))


async def _health_monitor_loop(interval: int = 30):
    """
    Background task — periodically probe all providers for health status.

    Runs every `interval` seconds. Logs warnings for DOWN providers.

    Args:
        interval: Seconds between health check runs.
    """
    while True:
        await asyncio.sleep(interval)
        try:
            health_checker = get_health_checker()
            if health_checker is None:
                continue
            statuses = await health_checker.check_all()
            for name, status in statuses.items():
                if status.status == "down":
                    logger.warning(
                        "Provider '{name}' is DOWN: {err}",
                        name=name,
                        err=status.error_message,
                    )
        except Exception as e:
            logger.error("Health monitor error: {err}", err=str(e))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # === STARTUP ===
    setup_logging(
        log_level=settings.LOG_LEVEL,
        log_format=settings.LOG_FORMAT,
    )

    logger.info("=" * 50)
    logger.info(f"{settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info("=" * 50)
    logger.info(f"Debug mode: {settings.DEBUG}")
    logger.info(f"Ollama URL: {settings.OLLAMA_BASE_URL}")
    logger.info(
        f"Gemini API Key: {'configured' if settings.GEMINI_API_KEY else 'not set'}"
    )

    if settings.GATEWAY_TOKEN:
        logger.info("Auth: enabled (token configured)")
    else:
        logger.info("Auth: disabled (development mode)")
    if settings.RATE_LIMIT_RPM > 0:
        logger.info("Rate limit: {rpm} req/min", rpm=settings.RATE_LIMIT_RPM)
    else:
        logger.info("Rate limit: unlimited")

    # Initialize services (providers, registry, generator, cache, health checker)
    initialize_services(settings)
    
    # Fetch models dynamically from APIs
    await initialize_dynamic_models()

    # Initial health check (replaces ad-hoc Ollama check)
    health_checker = get_health_checker()
    if health_checker:
        initial_statuses = await health_checker.check_all()
        for name, status in initial_statuses.items():
            if status.status == "up":
                logger.info(
                    "Provider '{name}': UP (latency: {latency:.1f}ms)",
                    name=name,
                    latency=status.latency_ms or 0,
                )
            elif status.status == "degraded":
                logger.warning(
                    "Provider '{name}': DEGRADED — {err}",
                    name=name,
                    err=status.error_message,
                )
            else:
                logger.warning(
                    "Provider '{name}': DOWN — {err}",
                    name=name,
                    err=status.error_message,
                )

    # Start background health monitor
    health_monitor_task = asyncio.create_task(
        _health_monitor_loop(interval=settings.HEALTH_CHECK_INTERVAL),
        name="health-monitor",
    )
    logger.info(
        "Health monitor started (interval: {interval}s)",
        interval=settings.HEALTH_CHECK_INTERVAL,
    )

    # Start background session cleanup task
    cleanup_task = asyncio.create_task(
        _session_cleanup_loop(),
        name="session-cleanup",
    )
    logger.info("Session cleanup task started (interval: 5min)")

    yield

    # === SHUTDOWN ===
    # Cancel background health monitor
    health_monitor_task.cancel()
    try:
        await health_monitor_task
    except asyncio.CancelledError:
        pass
    logger.info("Health monitor stopped")

    # Cancel background cleanup task
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    logger.info("Session cleanup task stopped")

    providers = get_providers()
    for name, provider in providers.items():
        await provider.close()
        logger.debug(f"Closed provider: {name}")

    logger.info("Shutting down AI Generative Core...")


# --- Create FastAPI app ---
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Universal AI Gateway for SaaS applications. "
    "Supports multiple AI providers (Ollama, Gemini) "
    "with text generation, streaming, embedding, and multimodal capabilities.",
    lifespan=lifespan,
)

# --- Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)

# --- API Router ---
app.include_router(api_router)


# --- Exception Handlers ---
@app.exception_handler(AuthenticationError)
async def auth_error_handler(request: Request, exc: AuthenticationError):
    return JSONResponse(
        status_code=401,
        content={"error": exc.message, "code": exc.code},
        headers={"WWW-Authenticate": "Bearer"},
    )


@app.exception_handler(RateLimitExceededError)
async def rate_limit_handler(request: Request, exc: RateLimitExceededError):
    return JSONResponse(
        status_code=429,
        content={"error": exc.message, "code": exc.code},
        headers={
            "Retry-After": str(exc.retry_after),
            "X-RateLimit-Limit": str(settings.RATE_LIMIT_RPM),
        },
    )


@app.exception_handler(AllKeysExhaustedError)
async def all_keys_exhausted_handler(request: Request, exc: AllKeysExhaustedError):
    """Handler for exhausted API keys."""
    return JSONResponse(
        status_code=503,
        content={"error": exc.message, "code": exc.code},
    )


@app.exception_handler(AIGatewayError)
async def gateway_error_handler(request: Request, exc: AIGatewayError):
    """Global handler for all AIGatewayError subclasses."""
    status_map = {
        "PROVIDER_NOT_FOUND": 404,
        "MODEL_NOT_FOUND": 404,
        "SESSION_NOT_FOUND": 404,
        "CAPABILITY_NOT_SUPPORTED": 400,
        "BATCH_TOO_LARGE": 400,
        "AUTO_ROUTING_UNAVAILABLE": 503,
        "AUTO_ROUTING_FAILED": 503,
        "PROVIDER_CONNECTION_ERROR": 502,
        "PROVIDER_TIMEOUT": 504,
        "PROVIDER_API_ERROR": 502,
    }
    status_code = status_map.get(exc.code, 500)
    logger.error(
        "Request failed: {code} - {message}",
        code=exc.code,
        message=exc.message,
    )
    return JSONResponse(
        status_code=status_code,
        content={"error": exc.message, "code": exc.code},
    )


# --- Health Check ---
@app.get("/health", tags=["System"], summary="Health check")
async def health_check():
    """Check if the server is running and healthy."""
    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "app_name": settings.APP_NAME,
    }


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
