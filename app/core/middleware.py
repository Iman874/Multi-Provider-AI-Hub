"""
Request logging middleware for AI Generative Core.

Automatically logs every HTTP request with method, path, status code,
and duration in milliseconds. Integrates with loguru.
"""

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from loguru import logger


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs every incoming HTTP request.

    Logs:
    - HTTP method (GET, POST, etc.)
    - Request path (/api/v1/generate, etc.)
    - Response status code (200, 404, 500, etc.)
    - Request duration in milliseconds
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.perf_counter()

        # Process the request
        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Log the request
        logger.info(
            "Request completed: {method} {path} -> {status} ({duration:.1f}ms)",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration=duration_ms,
        )

        return response
