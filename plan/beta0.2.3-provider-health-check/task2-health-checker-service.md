# Task 2 — HealthChecker Service (Probe Strategies + Status Logic)

## 1. Judul Task
Implementasi `HealthChecker` service dengan probe strategies (Ollama HTTP, Gemini SDK) dan status transition logic

## 2. Deskripsi
Membangun service inti yang melakukan health probe ke setiap AI provider dan mengelola status transition (up/down/degraded) berdasarkan threshold consecutive failures dan latency. Service ini menjadi sumber kebenaran untuk status provider di seluruh aplikasi.

## 3. Tujuan Teknis
- `HealthChecker` menyediakan: `check_provider()`, `check_all()`, `get_status()`, `get_all_statuses()`, `is_provider_up()`, `get_available_providers()`, `get_overall_status()`
- Ollama probe: HTTP GET ke `/api/tags` dengan timeout
- Gemini probe: `models.list()` via SDK — lightweight, no token consumed
- Status transition: UP → DEGRADED (slow) / DOWN (threshold failures), DOWN → UP (recovery on success)
- Degraded detection: latency > `timeout * 500ms` (50% of timeout) atau auth error tapi reachable

## 4. Scope
### Yang dikerjakan
- `app/services/health_checker.py` — extend file dari Task 1, tambah `HealthChecker` class

### Yang TIDAK dikerjakan
- Endpoint / Router — Task 3
- Background monitor loop — Task 4
- Dependency injection wiring — Task 4
- Unit tests — Task 5
- Smart model listing — Task 3

## 5. Langkah Implementasi

### Step 1: Tambah imports di `app/services/health_checker.py`
Tambahkan imports yang dibutuhkan (setelah imports existing dari Task 1):
```python
import time
from dataclasses import dataclass

import httpx
from loguru import logger

from app.providers.base import BaseProvider
```

### Step 2: Implementasi `HealthChecker.__init__()`
Tambahkan class setelah `ProviderStatus` dataclass:

```python
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
```

### Step 3: Implementasi Ollama probe
```python
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
```

### Step 4: Implementasi Gemini probe
```python
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
```

### Step 5: Implementasi probe dispatcher
```python
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
            case _:
                return False, 0.0, f"Unknown provider: {name}"
```

### Step 6: Implementasi `check_provider()` — KRITIS: status transition logic
```python
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
```

### Step 7: Implementasi `check_all()`
```python
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
```

### Step 8: Implementasi getter methods
```python
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
```

## 6. Output yang Diharapkan

Setelah implementasi, verifikasi manual (saat Ollama running):
```python
from app.services.health_checker import HealthChecker, ProviderStatus
from app.providers.ollama import OllamaProvider

# Create minimal provider for testing
provider = OllamaProvider(base_url="http://localhost:11434", timeout=120)
checker = HealthChecker(
    providers={"ollama": provider},
    timeout=5,
    threshold=3,
)

# Check Ollama
import asyncio
status = asyncio.run(checker.check_provider("ollama"))
print(f"Ollama: {status.status}, latency: {status.latency_ms:.1f}ms")
# Expected: "up", latency < 100ms

# Available providers
print(f"Available: {checker.get_available_providers()}")
# Expected: ["ollama"]

# Overall status
print(f"Overall: {checker.get_overall_status()}")
# Expected: "healthy" (if ollama is up) or "degraded" (if mixed)
```

## 7. Dependencies
- **Task 1** — `ProviderStatus` dataclass, config fields

## 8. Acceptance Criteria
- [ ] `HealthChecker.__init__()` → initializes status for each provider
- [ ] `_probe_ollama()` → HTTP GET `/api/tags`, returns (success, latency_ms, error)
- [ ] `_probe_gemini()` → SDK `models.list()`, auth errors → partial success
- [ ] `_probe()` → dispatches to correct strategy by name
- [ ] `check_provider()` — success → UP, success + slow → DEGRADED, auth error → DEGRADED
- [ ] `check_provider()` — failure below threshold → keep current status
- [ ] `check_provider()` — failure at/above threshold → DOWN
- [ ] `check_provider()` — was DOWN + success → UP (recovery)
- [ ] `check_all()` → probes all providers, returns dict of statuses
- [ ] `get_status()` → current status without probing
- [ ] `is_provider_up()` → True if not DOWN, True if unknown
- [ ] `get_available_providers()` → list of non-DOWN providers
- [ ] `get_overall_status()` → "healthy" (all UP) / "degraded" (mixed) / "unhealthy" (all DOWN)
- [ ] All probes have try-catch, no unhandled exceptions
- [ ] Server bisa start tanpa error

## 9. Estimasi
Medium (~45 menit)
