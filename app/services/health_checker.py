"""
Health Checker — Provider health monitoring service.

Probes AI providers periodically to determine availability.
Tracks status (up/down/degraded), latency, and failure streaks.
Used by model listing to filter unavailable providers and by
the health endpoint to report system status.
"""

import time
from dataclasses import dataclass

import httpx
from loguru import logger

from app.providers.base import BaseProvider


@dataclass
class ProviderStatus:
    """Current health status of an AI provider."""

    provider: str                       # "ollama" | "gemini"
    status: str = "up"                  # "up" | "down" | "degraded"
    last_check: float = 0.0            # Unix timestamp of last probe
    last_success: float | None = None   # Last successful probe timestamp
    consecutive_failures: int = 0       # Failure streak count
    latency_ms: float | None = None     # Last probe latency in milliseconds
    error_message: str | None = None    # Last error detail (if any)


class HealthChecker:
    """
    Provider health monitoring service.

    Probes providers periodically, tracks failure streaks,
    and determines availability status (up/down/degraded).
    """

    def __init__(
        self,
        providers: dict[str, BaseProvider],
        timeout: int = 5,
        threshold: int = 3,
    ):
        """
        Initialize HealthChecker.

        Args:
            providers: Dict mapping provider names to BaseProvider instances.
            timeout: Probe timeout in seconds.
            threshold: Consecutive failures before marking DOWN.
        """
        self._providers = providers
        self._timeout = timeout
        self._threshold = threshold
        self._statuses: dict[str, ProviderStatus] = {}

        # Initialize status for each provider
        for name in providers:
            self._statuses[name] = ProviderStatus(provider=name)

        logger.info(
            "HealthChecker initialized: providers={providers}, "
            "timeout={timeout}s, threshold={threshold}",
            providers=list(providers.keys()),
            timeout=timeout,
            threshold=threshold,
        )

    async def _probe_ollama(self) -> tuple[bool, float, str | None]:
        """
        Probe Ollama via HTTP GET /api/tags.

        Returns:
            Tuple of (success, latency_ms, error_message).
        """
        provider = self._providers.get("ollama")
        if provider is None:
            return False, 0.0, "Provider not configured"

        # Get base URL from provider instance
        base_url = getattr(provider, "_base_url", "http://localhost:11434")
        start = time.perf_counter()

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(f"{base_url}/api/tags")
                latency = (time.perf_counter() - start) * 1000

                if resp.status_code == 200:
                    return True, latency, None
                else:
                    return False, latency, f"HTTP {resp.status_code}"
        except httpx.TimeoutException:
            latency = (time.perf_counter() - start) * 1000
            return False, latency, "Timeout"
        except httpx.ConnectError:
            latency = (time.perf_counter() - start) * 1000
            return False, latency, "Connection refused"
        except Exception as e:
            latency = (time.perf_counter() - start) * 1000
            return False, latency, str(e)[:100]

    async def _probe_gemini(self) -> tuple[bool, float, str | None]:
        """
        Probe Gemini via lightweight models.list() SDK call.

        No tokens consumed. Auth errors (401/403) are treated as
        "reachable but degraded" since the API is responding.

        Returns:
            Tuple of (success, latency_ms, error_message).
        """
        provider = self._providers.get("gemini")
        if provider is None:
            return False, 0.0, "Provider not configured"

        start = time.perf_counter()

        try:
            # Access _get_client from GeminiProvider to get SDK client
            client, key = provider._get_client()
            # models.list() is lightweight — no token consumption
            _models = client.models.list()
            latency = (time.perf_counter() - start) * 1000
            return True, latency, None
        except Exception as e:
            latency = (time.perf_counter() - start) * 1000
            error_str = str(e)

            # 401/403 = API is reachable but auth issue → partial success (DEGRADED)
            if "401" in error_str or "403" in error_str:
                return True, latency, "Auth issue (reachable)"

            return False, latency, error_str[:100]

    async def _probe_nvidia(self) -> tuple[bool, float, str | None]:
        """
        Probe NVIDIA NIM via HTTP GET /models.

        Lightweight call — no tokens consumed. Validates API reachability
        and authentication.

        Returns:
            Tuple of (success, latency_ms, error_message).
        """
        provider = self._providers.get("nvidia")
        if provider is None:
            return False, 0.0, "Provider not configured"

        base_url = getattr(provider, "_base_url", "https://integrate.api.nvidia.com/v1")
        api_key = getattr(provider, "_api_key", "")
        start = time.perf_counter()

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(
                    f"{base_url}/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                latency = (time.perf_counter() - start) * 1000

                if resp.status_code == 200:
                    return True, latency, None
                elif resp.status_code in (401, 403):
                    return True, latency, "Auth issue (reachable)"
                else:
                    return False, latency, f"HTTP {resp.status_code}"
        except httpx.TimeoutException:
            latency = (time.perf_counter() - start) * 1000
            return False, latency, "Timeout"
        except httpx.ConnectError:
            latency = (time.perf_counter() - start) * 1000
            return False, latency, "Connection refused"
        except Exception as e:
            latency = (time.perf_counter() - start) * 1000
            return False, latency, str(e)[:100]

    async def _probe(self, name: str) -> tuple[bool, float, str | None]:
        """
        Dispatch probe to appropriate strategy based on provider name.

        Args:
            name: Provider name ("ollama" or "gemini").

        Returns:
            Tuple of (success, latency_ms, error_message).
        """
        match name:
            case "ollama":
                return await self._probe_ollama()
            case "gemini":
                return await self._probe_gemini()
            case "nvidia":
                return await self._probe_nvidia()
            case _:
                return False, 0.0, f"Unknown provider: {name}"

    async def check_provider(self, name: str) -> ProviderStatus:
        """
        Probe a single provider and update its status.

        Status transition rules:
        - Success + fast → UP
        - Success + slow (latency > timeout * 500ms) → DEGRADED
        - Failure + below threshold → keep current status (grace period)
        - Failure + at/above threshold → DOWN
        - Was DOWN + success → UP (recovery)

        Args:
            name: Provider name.

        Returns:
            Updated ProviderStatus.
        """
        if name not in self._statuses:
            self._statuses[name] = ProviderStatus(provider=name)

        status = self._statuses[name]
        success, latency, error = await self._probe(name)

        status.last_check = time.time()
        status.latency_ms = latency
        status.error_message = error

        if success:
            status.consecutive_failures = 0
            status.last_success = time.time()

            # Check for degraded (slow response or auth issue)
            degraded_threshold_ms = self._timeout * 500  # 50% of timeout in ms
            if error and "Auth issue" in error:
                status.status = "degraded"
            elif latency > degraded_threshold_ms:
                status.status = "degraded"
            else:
                status.status = "up"
        else:
            status.consecutive_failures += 1
            if status.consecutive_failures >= self._threshold:
                status.status = "down"
            # else: keep current status (grace period)

        self._statuses[name] = status

        logger.debug(
            "Health check {provider}: {status} (latency={latency:.1f}ms, failures={failures})",
            provider=name,
            status=status.status,
            latency=latency,
            failures=status.consecutive_failures,
        )

        return status

    async def check_all(self) -> dict[str, ProviderStatus]:
        """
        Probe all registered providers.

        Returns:
            Dict mapping provider names to their updated ProviderStatus.
        """
        results = {}
        for name in self._providers:
            results[name] = await self.check_provider(name)
        return results

    def get_status(self, name: str) -> ProviderStatus:
        """
        Get current status of a provider (without probing).

        Args:
            name: Provider name.

        Returns:
            ProviderStatus (default UP if never checked).
        """
        if name not in self._statuses:
            return ProviderStatus(provider=name)
        return self._statuses[name]

    def get_all_statuses(self) -> dict[str, ProviderStatus]:
        """Get current status of all providers (without probing)."""
        return dict(self._statuses)

    def is_provider_up(self, name: str) -> bool:
        """
        Check if a provider is available (UP or DEGRADED).

        DOWN providers return False.

        Args:
            name: Provider name.

        Returns:
            True if provider is not DOWN.
        """
        status = self._statuses.get(name)
        if status is None:
            return True  # Unknown = assume available
        return status.status != "down"

    def get_available_providers(self) -> list[str]:
        """
        Get list of provider names that are NOT down.

        Returns:
            List of available provider names.
        """
        return [
            name for name, status in self._statuses.items()
            if status.status != "down"
        ]

    def get_overall_status(self) -> str:
        """
        Calculate overall system health status.

        Returns:
            - "healthy": All providers UP
            - "degraded": Some providers UP/DEGRADED, some DOWN
            - "unhealthy": All providers DOWN
        """
        if not self._statuses:
            return "healthy"

        statuses = [s.status for s in self._statuses.values()]

        if all(s == "up" for s in statuses):
            return "healthy"
        elif all(s == "down" for s in statuses):
            return "unhealthy"
        else:
            return "degraded"
