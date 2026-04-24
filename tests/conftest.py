"""
Global test fixtures for AI Generative Core.

Provides pre-configured provider instances with mocked external dependencies.
All fixtures are designed so tests run WITHOUT any external services
(no Ollama, no Gemini API key, no internet connection required).
"""

import pytest
from unittest.mock import MagicMock, patch

from app.providers.ollama import OllamaProvider
from app.services.key_manager import KeyManager


# --- OllamaProvider Fixture ---

@pytest.fixture
def ollama_provider():
    """
    Create an OllamaProvider instance pointed at a dummy URL.

    The httpx client inside will be intercepted by `respx` in individual
    tests, so no real HTTP calls are made.
    """
    provider = OllamaProvider(
        base_url="http://test-ollama:11434",
        timeout=30,
    )
    return provider


@pytest.fixture
def ollama_provider_cloud():
    """OllamaProvider with cloud key manager."""
    km = KeyManager("ollama_cloud_test", ["test-cloud-key-abc"])
    return OllamaProvider(
        base_url="http://test-ollama:11434",
        timeout=30,
        key_manager=km,
    )


# --- GeminiProvider Fixture ---

@pytest.fixture
def gemini_provider():
    """
    Create a GeminiProvider with a mocked genai.Client.

    We patch `genai.Client` so the SDK never makes real API calls.
    The mock client is accessible via `provider._client`.
    """
    with patch("app.providers.gemini.genai.Client") as MockClient:
        mock_client = MagicMock()
        MockClient.return_value = mock_client

        # Buat KeyManager dengan fake keys
        key_manager = KeyManager("gemini_test", ["fake-key-1", "fake-key-2"])

        from app.providers.gemini import GeminiProvider

        provider = GeminiProvider(
            key_manager=key_manager,
            timeout=30,
        )
        # Override internal _get_client so tests can mock client behavior easily
        def fake_get_client():
            return mock_client, "fake-key-1"
            
        provider._get_client = fake_get_client
        
        # We also keep provider._client reference for tests that expect it
        provider._client = mock_client
        yield provider
