# 07 — Error Handling Strategy

---

## Custom Exception Hierarchy

File: `app/core/exceptions.py`

```python
class AIGatewayError(Exception):
    """Base exception for all application errors."""
    def __init__(self, message: str, code: str):
        self.message = message
        self.code = code
        super().__init__(message)


class ProviderNotFoundError(AIGatewayError):
    """Requested provider does not exist or is disabled."""
    def __init__(self, provider: str):
        super().__init__(
            message=f"Provider '{provider}' not found or disabled",
            code="PROVIDER_NOT_FOUND",
        )


class ModelNotFoundError(AIGatewayError):
    """Requested model not registered in registry."""
    def __init__(self, provider: str, model: str):
        super().__init__(
            message=f"Model '{model}' not found for provider '{provider}'",
            code="MODEL_NOT_FOUND",
        )


class ModelCapabilityError(AIGatewayError):
    """Model doesn't support the requested capability."""
    def __init__(self, model: str, capability: str):
        super().__init__(
            message=f"Model '{model}' does not support '{capability}'",
            code="CAPABILITY_NOT_SUPPORTED",
        )


class ProviderConnectionError(AIGatewayError):
    """Failed to connect to provider API."""
    def __init__(self, provider: str, detail: str = ""):
        super().__init__(
            message=f"Cannot connect to '{provider}': {detail}",
            code="PROVIDER_CONNECTION_ERROR",
        )


class ProviderTimeoutError(AIGatewayError):
    """Provider API request timed out."""
    def __init__(self, provider: str, timeout: int):
        super().__init__(
            message=f"Request to '{provider}' timed out after {timeout}s",
            code="PROVIDER_TIMEOUT",
        )


class ProviderAPIError(AIGatewayError):
    """Provider returned an error response."""
    def __init__(self, provider: str, status: int, detail: str = ""):
        super().__init__(
            message=f"Provider '{provider}' error (HTTP {status}): {detail}",
            code="PROVIDER_API_ERROR",
        )
```

---

## FastAPI Exception Handlers

File: `app/main.py` (registered at startup)

```python
from fastapi.responses import JSONResponse

@app.exception_handler(AIGatewayError)
async def gateway_error_handler(request, exc: AIGatewayError):
    status_map = {
        "PROVIDER_NOT_FOUND": 404,
        "MODEL_NOT_FOUND": 404,
        "CAPABILITY_NOT_SUPPORTED": 400,
        "PROVIDER_CONNECTION_ERROR": 502,
        "PROVIDER_TIMEOUT": 504,
        "PROVIDER_API_ERROR": 502,
    }
    return JSONResponse(
        status_code=status_map.get(exc.code, 500),
        content={
            "error": exc.message,
            "code": exc.code,
        },
    )
```

---

## Error Response Format (Standard)

```json
{
    "error": "Model 'llama3.2' does not support 'image'",
    "code": "CAPABILITY_NOT_SUPPORTED",
    "detail": null
}
```

---

## Error Code Reference

| Code | HTTP | Meaning |
|---|---|---|
| `PROVIDER_NOT_FOUND` | 404 | Provider doesn't exist or disabled |
| `MODEL_NOT_FOUND` | 404 | Model not in registry |
| `CAPABILITY_NOT_SUPPORTED` | 400 | Model can't do requested operation |
| `PROVIDER_CONNECTION_ERROR` | 502 | Can't reach provider API |
| `PROVIDER_TIMEOUT` | 504 | Provider took too long |
| `PROVIDER_API_ERROR` | 502 | Provider returned error |

---

## Logging Middleware

File: `app/core/middleware.py`

```python
class RequestLoggingMiddleware:
    """
    Log every request/response with:
    - Method, path, status code
    - Duration (ms)
    - Provider & model (if present in body)
    - Error details (if any)
    """
    async def __call__(self, request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration = (time.perf_counter() - start) * 1000

        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=round(duration, 2),
        )
        return response
```

---

## Timeout Handling Strategy

```python
# In each provider, wrap HTTP calls with timeout handling:

try:
    response = await self._client.post(url, json=payload)
except httpx.TimeoutException:
    raise ProviderTimeoutError(self.name, self._timeout)
except httpx.ConnectError:
    raise ProviderConnectionError(self.name, "Connection refused")
```

> **Next**: See [08-implementation-order.md](./08-implementation-order.md)
