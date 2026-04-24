# Task 5 — Unit Tests HealthChecker

## 1. Judul Task
Implementasi 10 unit tests untuk `HealthChecker` service

## 2. Deskripsi
Menulis unit tests lengkap yang memvalidasi semua aspek `HealthChecker`: probe strategies (mock HTTP/SDK), status transition logic (UP → DOWN → recovery), threshold grace period, degraded detection, available providers filtering, dan overall status calculation. Tests menggunakan `pytest` dengan mock `httpx` dan mock providers.

## 3. Tujuan Teknis
- 10 test cases baru di `tests/services/test_health_checker.py`
- Coverage: probe strategies, status transitions, threshold logic, recovery, degraded, query methods, model filtering
- All probes mocked (tidak hit real API)
- Semua existing tests tetap PASS

## 4. Scope
### Yang dikerjakan
- `tests/services/test_health_checker.py` — file baru, 10 test functions

### Yang TIDAK dikerjakan
- Integration test endpoint (bisa ditambah nanti)
- Real provider probe testing

## 5. Langkah Implementasi

### Step 1: Buat file `tests/services/test_health_checker.py`

```python
"""
Unit tests for HealthChecker service.

Tests cover: probe strategies (mocked), status transitions,
threshold logic, recovery, degraded detection, and query methods.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx

from app.services.health_checker import HealthChecker, ProviderStatus
```

### Step 2: Setup fixtures — mock providers
```python
@pytest.fixture
def mock_ollama_provider():
    """Create a mock Ollama provider."""
    provider = MagicMock()
    provider.name = "ollama"
    provider._base_url = "http://localhost:11434"
    return provider


@pytest.fixture
def mock_gemini_provider():
    """Create a mock Gemini provider."""
    provider = MagicMock()
    provider.name = "gemini"
    # Mock _get_client to return a mock client
    mock_client = MagicMock()
    mock_client.models.list.return_value = []
    provider._get_client.return_value = (mock_client, "fake-key")
    return provider


@pytest.fixture
def checker_ollama(mock_ollama_provider):
    """HealthChecker with only Ollama provider."""
    return HealthChecker(
        providers={"ollama": mock_ollama_provider},
        timeout=5,
        threshold=3,
    )


@pytest.fixture
def checker_both(mock_ollama_provider, mock_gemini_provider):
    """HealthChecker with both Ollama and Gemini providers."""
    return HealthChecker(
        providers={
            "ollama": mock_ollama_provider,
            "gemini": mock_gemini_provider,
        },
        timeout=5,
        threshold=3,
    )
```

### Step 3: Test 1 — `test_ollama_up` (probe success → UP)
```python
@pytest.mark.asyncio
async def test_ollama_up(checker_ollama: HealthChecker):
    """Test Ollama probe success → status UP."""
    # Mock successful HTTP response
    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch("app.services.health_checker.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        status = await checker_ollama.check_provider("ollama")

    assert status.status == "up"
    assert status.consecutive_failures == 0
    assert status.latency_ms is not None
    assert status.latency_ms >= 0
    assert status.error_message is None
    assert status.last_success is not None
```

### Step 4: Test 2 — `test_ollama_down` (N failures → DOWN)
```python
@pytest.mark.asyncio
async def test_ollama_down(checker_ollama: HealthChecker):
    """Test Ollama N consecutive failures → status DOWN."""
    # Mock connection refused
    with patch("app.services.health_checker.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.ConnectError("Connection refused")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        # Probe threshold (3) times
        for i in range(3):
            status = await checker_ollama.check_provider("ollama")

    assert status.status == "down"
    assert status.consecutive_failures == 3
    assert status.error_message == "Connection refused"
```

### Step 5: Test 3 — `test_gemini_up` (SDK success → UP)
```python
@pytest.mark.asyncio
async def test_gemini_up(checker_both: HealthChecker):
    """Test Gemini probe success via SDK → status UP."""
    # mock_gemini_provider already has models.list() returning []
    status = await checker_both.check_provider("gemini")

    assert status.status == "up"
    assert status.consecutive_failures == 0
    assert status.latency_ms >= 0
    assert status.error_message is None
```

### Step 6: Test 4 — `test_gemini_degraded` (auth error → DEGRADED)
```python
@pytest.mark.asyncio
async def test_gemini_degraded(mock_ollama_provider):
    """Test Gemini auth error (reachable but 401/403) → DEGRADED."""
    # Create gemini provider with auth failure
    mock_gemini = MagicMock()
    mock_gemini.name = "gemini"
    mock_client = MagicMock()
    mock_client.models.list.side_effect = Exception("403 Forbidden: Invalid API key")
    mock_gemini._get_client.return_value = (mock_client, "bad-key")

    checker = HealthChecker(
        providers={"gemini": mock_gemini},
        timeout=5,
        threshold=3,
    )

    status = await checker.check_provider("gemini")

    assert status.status == "degraded"
    assert status.error_message is not None
    assert "Auth issue" in status.error_message
    assert status.consecutive_failures == 0  # partial success
```

### Step 7: Test 5 — `test_recovery` (DOWN → success → UP)
```python
@pytest.mark.asyncio
async def test_recovery(checker_ollama: HealthChecker):
    """Test recovery: DOWN → probe success → UP."""
    # First: force DOWN by probing 3 failures
    with patch("app.services.health_checker.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.ConnectError("Connection refused")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        for _ in range(3):
            await checker_ollama.check_provider("ollama")

    assert checker_ollama.get_status("ollama").status == "down"

    # Now: probe succeeds → recovery to UP
    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch("app.services.health_checker.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        status = await checker_ollama.check_provider("ollama")

    assert status.status == "up"
    assert status.consecutive_failures == 0
```

### Step 8: Test 6 — `test_threshold_grace` (1 failure < threshold → stay current)
```python
@pytest.mark.asyncio
async def test_threshold_grace(checker_ollama: HealthChecker):
    """Test that 1 failure < threshold keeps current status (grace period)."""
    # First: probe success to establish UP
    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch("app.services.health_checker.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        await checker_ollama.check_provider("ollama")

    assert checker_ollama.get_status("ollama").status == "up"

    # Now: single failure (below threshold of 3)
    with patch("app.services.health_checker.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.ConnectError("Connection refused")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        status = await checker_ollama.check_provider("ollama")

    # Should NOT be DOWN yet (1 < threshold of 3)
    assert status.status == "up"  # keeps current
    assert status.consecutive_failures == 1
```

### Step 9: Test 7 — `test_available_providers`
```python
@pytest.mark.asyncio
async def test_available_providers(checker_both: HealthChecker):
    """Test get_available_providers returns only non-DOWN providers."""
    # Force ollama DOWN
    with patch("app.services.health_checker.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.ConnectError("refused")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        for _ in range(3):
            await checker_both.check_provider("ollama")

    # Gemini should be UP (mock_gemini_provider models.list works)
    await checker_both.check_provider("gemini")

    available = checker_both.get_available_providers()
    assert "gemini" in available
    assert "ollama" not in available
```

### Step 10: Test 8 — `test_overall_healthy`
```python
def test_overall_healthy(checker_both: HealthChecker):
    """Test overall status is 'healthy' when all providers are UP."""
    # Default status is UP for all
    assert checker_both.get_overall_status() == "healthy"
```

### Step 11: Test 9 — `test_overall_degraded`
```python
@pytest.mark.asyncio
async def test_overall_degraded(checker_both: HealthChecker):
    """Test overall status is 'degraded' when some providers are DOWN."""
    # Force ollama DOWN
    with patch("app.services.health_checker.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.ConnectError("refused")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        for _ in range(3):
            await checker_both.check_provider("ollama")

    # Gemini still UP (default)
    assert checker_both.get_overall_status() == "degraded"
```

### Step 12: Test 10 — `test_is_provider_up`
```python
@pytest.mark.asyncio
async def test_is_provider_up(checker_ollama: HealthChecker):
    """Test is_provider_up returns correct boolean based on status."""
    # Default (never checked) → True
    assert checker_ollama.is_provider_up("ollama") is True

    # Unknown provider → True (assume available)
    assert checker_ollama.is_provider_up("unknown") is True

    # Force DOWN
    with patch("app.services.health_checker.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.ConnectError("refused")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        for _ in range(3):
            await checker_ollama.check_provider("ollama")

    assert checker_ollama.is_provider_up("ollama") is False
```

## 6. Output yang Diharapkan

Jalankan tests:
```bash
pytest tests/services/test_health_checker.py -v
```

Expected output:
```
tests/services/test_health_checker.py::test_ollama_up PASSED
tests/services/test_health_checker.py::test_ollama_down PASSED
tests/services/test_health_checker.py::test_gemini_up PASSED
tests/services/test_health_checker.py::test_gemini_degraded PASSED
tests/services/test_health_checker.py::test_recovery PASSED
tests/services/test_health_checker.py::test_threshold_grace PASSED
tests/services/test_health_checker.py::test_available_providers PASSED
tests/services/test_health_checker.py::test_overall_healthy PASSED
tests/services/test_health_checker.py::test_overall_degraded PASSED
tests/services/test_health_checker.py::test_is_provider_up PASSED

10 passed
```

Jalankan ALL tests:
```bash
pytest -v
```
Expected: Semua existing tests PASS + 10 test baru PASS.

**Note:** Tests membutuhkan `pytest-asyncio` package. Pastikan sudah terinstall:
```bash
pip install pytest-asyncio
```

## 7. Dependencies
- **Task 1** — `ProviderStatus` dataclass
- **Task 2** — `HealthChecker` class

## 8. Acceptance Criteria
- [ ] File `tests/services/test_health_checker.py` dibuat
- [ ] 10 test functions implemented
- [ ] `test_ollama_up` — HTTP 200 → UP, latency tracked, no errors
- [ ] `test_ollama_down` — 3 consecutive failures → DOWN
- [ ] `test_gemini_up` — SDK success → UP
- [ ] `test_gemini_degraded` — auth error 401/403 → DEGRADED (partial success)
- [ ] `test_recovery` — DOWN → probe success → UP, failures reset to 0
- [ ] `test_threshold_grace` — 1 failure below threshold → keeps current status
- [ ] `test_available_providers` — only non-DOWN providers returned
- [ ] `test_overall_healthy` — all UP → "healthy"
- [ ] `test_overall_degraded` — mixed UP/DOWN → "degraded"
- [ ] `test_is_provider_up` — True for UP/unknown, False for DOWN
- [ ] All probes are mocked (no real HTTP/SDK calls)
- [ ] Semua existing tests tetap PASS
- [ ] `pytest` exit code 0

## 9. Estimasi
Medium (~45 menit)
