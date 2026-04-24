"""
Unit tests for HealthChecker service.

Tests cover: probe strategies (mocked), status transitions,
threshold logic, recovery, degraded detection, and query methods.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx

from app.services.health_checker import HealthChecker, ProviderStatus


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


@pytest.mark.asyncio
async def test_gemini_up(checker_both: HealthChecker):
    """Test Gemini probe success via SDK → status UP."""
    # mock_gemini_provider already has models.list() returning []
    status = await checker_both.check_provider("gemini")

    assert status.status == "up"
    assert status.consecutive_failures == 0
    assert status.latency_ms >= 0
    assert status.error_message is None


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


def test_overall_healthy(checker_both: HealthChecker):
    """Test overall status is 'healthy' when all providers are UP."""
    # Default status is UP for all
    assert checker_both.get_overall_status() == "healthy"


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
