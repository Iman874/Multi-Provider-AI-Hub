"""
Unit tests for GeneratorService auto routing.

Tests cover: target ordering, health-aware filtering, generate fallback,
embedding fallback, and streaming behavior before and after the first token.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from app.core.exceptions import (
    AIGatewayError,
    ProviderAPIError,
    ProviderConnectionError,
    ProviderTimeoutError,
)
from app.schemas.requests import EmbeddingRequest, GenerateRequest, StreamRequest
from app.services.generator import GeneratorService
from app.services.model_registry import ModelCapability, ModelRegistry


class FakeProvider:
    """Minimal provider stub used for GeneratorService unit tests."""

    def __init__(self, name: str):
        """
        Initialize the fake provider.

        Args:
            name: Provider identifier used by GeneratorService.
        """
        self._name = name
        self.generate = AsyncMock()
        self.embedding = AsyncMock()
        self._stream_impl = self._empty_stream
        self.stream_calls = 0

    @property
    def name(self) -> str:
        """
        Return the provider name.

        Returns:
            Provider identifier string.
        """
        return self._name

    async def stream(
        self,
        model: str,
        prompt: str,
        images: list[str] | None = None,
    ):
        """
        Stream tokens using the configured async generator implementation.

        Args:
            model: Requested model name.
            prompt: Input prompt.
            images: Optional multimodal images.

        Yields:
            Token strings produced by the configured stream implementation.
        """
        self.stream_calls += 1
        async for token in self._stream_impl(model, prompt, images):
            yield token

    @staticmethod
    async def _empty_stream(
        model: str,
        prompt: str,
        images: list[str] | None = None,
    ):
        """
        Return an empty async generator.

        Args:
            model: Requested model name.
            prompt: Input prompt.
            images: Optional multimodal images.

        Yields:
            No tokens.
        """
        if False:
            yield model or prompt or images  # pragma: no cover

    def set_stream_impl(self, impl) -> None:
        """
        Set the async generator implementation used by stream().

        Args:
            impl: Async generator callable for token streaming.

        Returns:
            None.
        """
        self._stream_impl = impl

    def supports_image(self, model: str) -> bool:
        """
        Return whether the provider supports images.

        Args:
            model: Requested model name.

        Returns:
            False. Capability checks are handled by ModelRegistry in tests.
        """
        return False

    async def fetch_models(self) -> list:
        """
        Return no models for the fake provider.

        Returns:
            Empty list.
        """
        return []


@pytest.fixture
def registry() -> ModelRegistry:
    """Create a model registry with text, vision, embedding, and stream variants."""
    registry = ModelRegistry()
    registry.register(
        ModelCapability(
            name="nvidia-chat",
            provider="nvidia",
            supports_text=True,
            supports_streaming=True,
        )
    )
    registry.register(
        ModelCapability(
            name="nvidia-embed",
            provider="nvidia",
            supports_text=False,
            supports_embedding=True,
            supports_streaming=False,
        )
    )
    registry.register(
        ModelCapability(
            name="gemini-text",
            provider="gemini",
            supports_text=True,
            supports_streaming=True,
        )
    )
    registry.register(
        ModelCapability(
            name="gemini-vision",
            provider="gemini",
            supports_text=True,
            supports_image=True,
            supports_streaming=True,
        )
    )
    registry.register(
        ModelCapability(
            name="ollama-chat",
            provider="ollama",
            supports_text=True,
            supports_streaming=True,
        )
    )
    registry.register(
        ModelCapability(
            name="ollama-embed",
            provider="ollama",
            supports_text=False,
            supports_embedding=True,
            supports_streaming=False,
        )
    )
    registry.register(
        ModelCapability(
            name="ollama-z-nostream",
            provider="ollama",
            supports_text=True,
            supports_streaming=False,
        )
    )
    return registry


@pytest.fixture
def providers() -> dict[str, FakeProvider]:
    """Create fake providers for nvidia, gemini, and ollama."""
    return {
        "nvidia": FakeProvider("nvidia"),
        "gemini": FakeProvider("gemini"),
        "ollama": FakeProvider("ollama"),
    }


@pytest.fixture
def health_checker():
    """Create a mock HealthChecker that marks all providers as available by default."""
    checker = MagicMock()
    checker.is_provider_up.side_effect = lambda name: True
    return checker


@pytest.fixture
def service(
    providers: dict[str, FakeProvider],
    registry: ModelRegistry,
    health_checker,
) -> GeneratorService:
    """Create a GeneratorService wired with fake providers and a mock HealthChecker."""
    return GeneratorService(
        providers=providers,
        registry=registry,
        cache=None,
        health_checker=health_checker,
    )


def test_get_auto_routing_targets_orders_by_priority(service: GeneratorService):
    """Auto targets should be ordered nvidia, gemini, then ollama."""
    targets = service._get_auto_routing_targets()

    assert [(target.provider, target.name) for target in targets] == [
        ("nvidia", "nvidia-chat"),
        ("gemini", "gemini-text"),
        ("gemini", "gemini-vision"),
        ("ollama", "ollama-chat"),
        ("ollama", "ollama-z-nostream"),
    ]


def test_get_auto_routing_targets_skips_down_provider(
    service: GeneratorService,
    health_checker,
):
    """Providers marked DOWN by HealthChecker should be removed from targets."""
    health_checker.is_provider_up.side_effect = lambda name: name != "nvidia"

    targets = service._get_auto_routing_targets()

    assert all(target.provider != "nvidia" for target in targets)
    assert targets[0].provider == "gemini"


def test_get_auto_routing_targets_filters_image_models(service: GeneratorService):
    """Image requests should only consider models with supports_image=True."""
    targets = service._get_auto_routing_targets(requires_image=True)

    assert [(target.provider, target.name) for target in targets] == [
        ("gemini", "gemini-vision"),
    ]


def test_get_auto_routing_targets_filters_streaming_models(service: GeneratorService):
    """Streaming requests should exclude models without streaming support."""
    targets = service._get_auto_routing_targets(requires_streaming=True)

    assert all(target.supports_streaming for target in targets)
    assert ("ollama", "ollama-z-nostream") not in {
        (target.provider, target.name) for target in targets
    }


def test_generate_request_rejects_auto_model_for_explicit_provider():
    """GenerateRequest should require a real model when provider is not auto."""
    with pytest.raises(ValidationError):
        GenerateRequest(provider="gemini", input="hello")


@pytest.mark.asyncio
async def test_generate_auto_prefers_nvidia(
    service: GeneratorService,
    providers: dict[str, FakeProvider],
):
    """Auto generate should use NVIDIA first when it succeeds."""
    providers["nvidia"].generate.return_value = {
        "output": "nvidia response",
        "provider": "nvidia",
        "model": "nvidia-chat",
        "usage": None,
        "metadata": None,
    }

    response = await service.generate(
        GenerateRequest(provider="auto", model="auto", input="hello"),
    )

    assert response.provider == "nvidia"
    assert response.model == "nvidia-chat"
    assert providers["nvidia"].generate.await_count == 1
    assert providers["gemini"].generate.await_count == 0
    assert providers["ollama"].generate.await_count == 0


@pytest.mark.asyncio
async def test_generate_auto_falls_back_to_gemini(
    service: GeneratorService,
    providers: dict[str, FakeProvider],
):
    """Auto generate should fall back to Gemini when NVIDIA times out."""
    providers["nvidia"].generate.side_effect = ProviderTimeoutError(
        provider="nvidia",
        timeout=30,
    )
    providers["gemini"].generate.return_value = {
        "output": "gemini response",
        "provider": "gemini",
        "model": "gemini-text",
        "usage": None,
        "metadata": None,
    }

    response = await service.generate(
        GenerateRequest(provider="auto", model="auto", input="hello"),
    )

    assert response.provider == "gemini"
    assert response.model == "gemini-text"
    assert providers["nvidia"].generate.await_count == 1
    assert providers["gemini"].generate.await_count == 1
    assert providers["ollama"].generate.await_count == 0


@pytest.mark.asyncio
async def test_generate_auto_raises_when_all_targets_fail(
    service: GeneratorService,
    providers: dict[str, FakeProvider],
):
    """Auto generate should raise AIGatewayError when all targets fail."""
    providers["nvidia"].generate.side_effect = ProviderAPIError(
        provider="nvidia",
        status=500,
        detail="server error",
    )
    providers["gemini"].generate.side_effect = ProviderAPIError(
        provider="gemini",
        status=503,
        detail="unavailable",
    )
    providers["ollama"].generate.side_effect = ProviderConnectionError(
        provider="ollama",
        detail="offline",
    )

    with pytest.raises(AIGatewayError) as exc_info:
        await service.generate(
            GenerateRequest(provider="auto", model="auto", input="hello"),
        )

    assert exc_info.value.code == "AUTO_ROUTING_FAILED"


@pytest.mark.asyncio
async def test_embedding_auto_filters_and_falls_back(
    service: GeneratorService,
    providers: dict[str, FakeProvider],
):
    """Auto embedding should use only embedding models and fall back when needed."""
    providers["nvidia"].embedding.side_effect = ProviderConnectionError(
        provider="nvidia",
        detail="offline",
    )
    providers["ollama"].embedding.return_value = [0.1, 0.2, 0.3]

    response = await service.embedding(
        EmbeddingRequest(provider="auto", model="auto", input="embed this"),
    )

    assert response.provider == "ollama"
    assert response.model == "ollama-embed"
    assert response.embedding == [0.1, 0.2, 0.3]
    assert providers["nvidia"].embedding.await_count == 1
    assert providers["gemini"].embedding.await_count == 0
    assert providers["ollama"].embedding.await_count == 1


@pytest.mark.asyncio
async def test_stream_auto_falls_back_before_first_token(
    service: GeneratorService,
    providers: dict[str, FakeProvider],
):
    """Auto stream should retry a new provider if the first target fails before yielding."""

    async def fail_before_first(
        model: str,
        prompt: str,
        images: list[str] | None = None,
    ):
        """Raise before yielding the first token."""
        raise ProviderConnectionError(provider="nvidia", detail="offline")
        if False:
            yield model or prompt or images  # pragma: no cover

    async def gemini_tokens(
        model: str,
        prompt: str,
        images: list[str] | None = None,
    ):
        """Yield a successful Gemini token stream."""
        yield "Hello"
        yield " world"

    providers["nvidia"].set_stream_impl(fail_before_first)
    providers["gemini"].set_stream_impl(gemini_tokens)

    tokens = []
    async for token in service.stream(
        StreamRequest(provider="auto", model="auto", input="hello"),
    ):
        tokens.append(token)

    assert tokens == ["Hello", " world"]
    assert providers["nvidia"].stream_calls == 1
    assert providers["gemini"].stream_calls == 1
    assert providers["ollama"].stream_calls == 0


@pytest.mark.asyncio
async def test_stream_auto_does_not_fallback_after_first_token(
    service: GeneratorService,
    providers: dict[str, FakeProvider],
):
    """Auto stream must not switch providers after the first token is sent."""

    async def fail_after_first(
        model: str,
        prompt: str,
        images: list[str] | None = None,
    ):
        """Yield one token and then raise an API error."""
        yield "partial"
        raise ProviderAPIError(provider="nvidia", status=500, detail="boom")

    async def gemini_tokens(
        model: str,
        prompt: str,
        images: list[str] | None = None,
    ):
        """Yield fallback tokens if called."""
        yield "should-not-run"

    providers["nvidia"].set_stream_impl(fail_after_first)
    providers["gemini"].set_stream_impl(gemini_tokens)

    iterator = service.stream(
        StreamRequest(provider="auto", model="auto", input="hello"),
    )

    first_token = await anext(iterator)
    assert first_token == "partial"

    with pytest.raises(ProviderAPIError):
        await anext(iterator)

    assert providers["nvidia"].stream_calls == 1
    assert providers["gemini"].stream_calls == 0
