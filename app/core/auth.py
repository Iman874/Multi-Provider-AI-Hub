"""
Gateway authentication dependency.

Validates Bearer token from Authorization header and checks rate limit.
Auth is disabled when GATEWAY_TOKEN is empty (development mode).
"""

import hmac

from fastapi import Request
from loguru import logger

from app.config import settings
from app.core.exceptions import AuthenticationError, RateLimitExceededError
from app.services.rate_limiter import RateLimiter


# --- Module-level singletons (initialized once at import) ---
_token: str = settings.GATEWAY_TOKEN.strip()
_rate_limiter = RateLimiter(max_rpm=settings.RATE_LIMIT_RPM)


def get_rate_limiter() -> RateLimiter:
    """Access the global rate limiter instance (for response headers)."""
    return _rate_limiter


async def verify_gateway_token(request: Request) -> str | None:
    """
    FastAPI dependency — validate Bearer token + rate limit.

    Auth flow:
    1. GATEWAY_TOKEN empty? → skip auth (dev mode), return None
    2. Read Authorization header from request
    3. Validate "Bearer <token>" format
    4. Constant-time compare token with GATEWAY_TOKEN
    5. Check rate limit via RateLimiter
    6. Return validated token string

    Args:
        request: FastAPI Request object.

    Returns:
        Validated token string if auth active, None if auth disabled.

    Raises:
        AuthenticationError: Missing header, invalid format, or wrong token.
        RateLimitExceededError: Global rate limit exceeded.
    """
    # 1. Auth disabled — GATEWAY_TOKEN is empty
    if not _token:
        return None

    # 2. Read Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise AuthenticationError("Missing Authorization header")

    # 3. Parse "Bearer <token>" format
    parts = auth_header.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise AuthenticationError(
            "Invalid format, expected: Authorization: Bearer <token>"
        )

    incoming_token = parts[1].strip()
    if not incoming_token:
        raise AuthenticationError("Empty token")

    # 4. Constant-time comparison (prevent timing attack)
    if not hmac.compare_digest(_token, incoming_token):
        raise AuthenticationError("Invalid token")

    # 5. Rate limit check
    if not _rate_limiter.check():
        raise RateLimitExceededError(limit=_rate_limiter._max_rpm)

    return incoming_token
