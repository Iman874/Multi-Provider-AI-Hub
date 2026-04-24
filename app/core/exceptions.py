"""
Custom exception hierarchy for AI Generative Core.

All application-level errors inherit from AIGatewayError.
Each exception carries a human-readable message and a machine-readable code,
enabling consistent JSON error responses across all endpoints.
"""


class AIGatewayError(Exception):
    """Base exception for all application errors."""

    def __init__(self, message: str, code: str):
        self.message = message
        self.code = code
        super().__init__(message)


class ProviderNotFoundError(AIGatewayError):
    """Raised when the requested provider does not exist or is disabled."""

    def __init__(self, provider: str):
        super().__init__(
            message=f"Provider '{provider}' not found or disabled",
            code="PROVIDER_NOT_FOUND",
        )


class ModelNotFoundError(AIGatewayError):
    """Raised when the requested model is not registered in the registry."""

    def __init__(self, provider: str, model: str):
        super().__init__(
            message=f"Model '{model}' not found for provider '{provider}'",
            code="MODEL_NOT_FOUND",
        )


class ModelCapabilityError(AIGatewayError):
    """Raised when a model doesn't support the requested capability."""

    def __init__(self, model: str, capability: str):
        super().__init__(
            message=f"Model '{model}' does not support '{capability}'",
            code="CAPABILITY_NOT_SUPPORTED",
        )


class ProviderConnectionError(AIGatewayError):
    """Raised when connection to a provider API fails."""

    def __init__(self, provider: str, detail: str = ""):
        msg = f"Cannot connect to '{provider}'"
        if detail:
            msg += f": {detail}"
        super().__init__(
            message=msg,
            code="PROVIDER_CONNECTION_ERROR",
        )


class ProviderTimeoutError(AIGatewayError):
    """Raised when a provider API request exceeds the timeout limit."""

    def __init__(self, provider: str, timeout: int):
        super().__init__(
            message=f"Request to '{provider}' timed out after {timeout}s",
            code="PROVIDER_TIMEOUT",
        )


class ProviderAPIError(AIGatewayError):
    """Raised when a provider returns an error response."""

    def __init__(self, provider: str, status: int, detail: str = ""):
        msg = f"Provider '{provider}' error (HTTP {status})"
        if detail:
            msg += f": {detail}"
        super().__init__(
            message=msg,
            code="PROVIDER_API_ERROR",
        )


class AllKeysExhaustedError(AIGatewayError):
    """Raised when all API keys in the pool are rate-limited or blacklisted."""

    def __init__(self, provider: str):
        super().__init__(
            message=f"All API keys for '{provider}' are exhausted or rate-limited",
            code="ALL_KEYS_EXHAUSTED",
        )


class SessionNotFoundError(AIGatewayError):
    """Session ID tidak ditemukan atau sudah expired."""

    def __init__(self, session_id: str):
        super().__init__(
            message=f"Chat session '{session_id}' not found or expired",
            code="SESSION_NOT_FOUND",
        )


class AuthenticationError(AIGatewayError):
    """Request tanpa token atau token tidak valid."""

    def __init__(self, detail: str = ""):
        msg = "Authentication failed"
        if detail:
            msg += f": {detail}"
        super().__init__(message=msg, code="AUTHENTICATION_FAILED")


class RateLimitExceededError(AIGatewayError):
    """Request melebihi batas rate limit per menit."""

    def __init__(self, limit: int, retry_after: int = 60):
        self.retry_after = retry_after
        super().__init__(
            message=f"Rate limit exceeded: max {limit} requests/minute",
            code="RATE_LIMIT_EXCEEDED",
        )


class BatchTooLargeError(AIGatewayError):
    """Raised when batch size exceeds the configured maximum limit."""

    def __init__(self, actual: int, maximum: int):
        super().__init__(
            message=f"Batch size {actual} exceeds maximum {maximum}",
            code="BATCH_TOO_LARGE",
        )
        self.actual = actual
        self.maximum = maximum
