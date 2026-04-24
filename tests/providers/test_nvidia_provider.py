"""
Unit tests for NvidiaProvider.

All HTTP calls are mocked using `respx` — no real NVIDIA API needed.
Tests cover: generate, stream, embedding, error handling.
"""

import json

import httpx
import pytest
import respx

from app.core.exceptions import (
    ProviderAPIError,
    ProviderConnectionError,
    ProviderTimeoutError,
)
from app.providers.nvidia import NvidiaProvider


# ============================================================
# Fixture
# ============================================================

@pytest.fixture
def nvidia_provider():
    """Create a NvidiaProvider instance for testing."""
    return NvidiaProvider(
        api_key="nvapi-test-key-123",
        base_url="https://test-nvidia.api.com/v1",
        timeout=30,
    )


# ============================================================
# generate() tests
# ============================================================

class TestNvidiaGenerate:
    """Tests for NvidiaProvider.generate()."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_generate_success(self, nvidia_provider):
        """Successful generate returns normalized dict."""
        respx.post("https://test-nvidia.api.com/v1/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": "chatcmpl-abc123",
                    "model": "meta/llama-3.3-70b-instruct",
                    "choices": [
                        {
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": "Hello! How can I help?",
                            },
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 10,
                        "completion_tokens": 8,
                        "total_tokens": 18,
                    },
                },
            )
        )

        result = await nvidia_provider.generate(
            model="meta/llama-3.3-70b-instruct",
            prompt="Hello",
        )

        assert result["output"] == "Hello! How can I help?"
        assert result["provider"] == "nvidia"
        assert result["model"] == "meta/llama-3.3-70b-instruct"
        assert result["usage"]["prompt_tokens"] == 10
        assert result["usage"]["completion_tokens"] == 8
        assert result["usage"]["total_tokens"] == 18
        assert result["metadata"]["finish_reason"] == "stop"

    @respx.mock
    @pytest.mark.asyncio
    async def test_generate_payload_format(self, nvidia_provider):
        """Verify the JSON payload sent to NVIDIA API."""
        route = respx.post("https://test-nvidia.api.com/v1/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json={
                    "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
                    "usage": {},
                },
            )
        )

        await nvidia_provider.generate(
            model="meta/llama-3.3-70b-instruct",
            prompt="Test prompt",
        )

        request = route.calls[0].request
        body = json.loads(request.content)
        assert body["model"] == "meta/llama-3.3-70b-instruct"
        assert body["messages"] == [{"role": "user", "content": "Test prompt"}]
        assert body["max_tokens"] == 4096

    @respx.mock
    @pytest.mark.asyncio
    async def test_generate_sends_auth_header(self, nvidia_provider):
        """Request includes Bearer token from API key."""
        route = respx.post("https://test-nvidia.api.com/v1/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json={
                    "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
                    "usage": {},
                },
            )
        )

        await nvidia_provider.generate(model="test-model", prompt="Hi")

        request = route.calls[0].request
        assert request.headers["Authorization"] == "Bearer nvapi-test-key-123"

    @respx.mock
    @pytest.mark.asyncio
    async def test_generate_http_error(self, nvidia_provider):
        """Non-200 status raises ProviderAPIError."""
        respx.post("https://test-nvidia.api.com/v1/chat/completions").mock(
            return_value=httpx.Response(
                401,
                text='{"error": "Invalid API key"}',
            )
        )

        with pytest.raises(ProviderAPIError) as exc:
            await nvidia_provider.generate(model="test-model", prompt="hi")

        assert "HTTP 401" in exc.value.message

    @respx.mock
    @pytest.mark.asyncio
    async def test_generate_timeout(self, nvidia_provider):
        """Timeout raises ProviderTimeoutError."""
        respx.post("https://test-nvidia.api.com/v1/chat/completions").mock(
            side_effect=httpx.TimeoutException("timed out")
        )

        with pytest.raises(ProviderTimeoutError) as exc:
            await nvidia_provider.generate(model="test-model", prompt="hi")

        assert "timed out" in exc.value.message

    @respx.mock
    @pytest.mark.asyncio
    async def test_generate_connection_error(self, nvidia_provider):
        """Connection error raises ProviderConnectionError."""
        respx.post("https://test-nvidia.api.com/v1/chat/completions").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        with pytest.raises(ProviderConnectionError) as exc:
            await nvidia_provider.generate(model="test-model", prompt="hi")

        assert "Connection failed" in exc.value.message


# ============================================================
# stream() tests
# ============================================================

class TestNvidiaStream:
    """Tests for NvidiaProvider.stream()."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_stream_success(self, nvidia_provider):
        """Stream yields tokens from SSE lines."""
        sse_lines = (
            'data: {"choices":[{"delta":{"role":"assistant","content":"Hello"}}]}\n\n'
            'data: {"choices":[{"delta":{"content":" world"}}]}\n\n'
            'data: {"choices":[{"delta":{"content":"!"}}]}\n\n'
            'data: [DONE]\n\n'
        )
        respx.post("https://test-nvidia.api.com/v1/chat/completions").mock(
            return_value=httpx.Response(
                200,
                content=sse_lines.encode(),
                headers={"content-type": "text/event-stream"},
            )
        )

        tokens = []
        async for token in nvidia_provider.stream(
            model="meta/llama-3.3-70b-instruct", prompt="Hi"
        ):
            tokens.append(token)

        assert tokens == ["Hello", " world", "!"]

    @respx.mock
    @pytest.mark.asyncio
    async def test_stream_skips_empty_deltas(self, nvidia_provider):
        """Empty delta content is skipped."""
        sse_lines = (
            'data: {"choices":[{"delta":{"role":"assistant"}}]}\n\n'
            'data: {"choices":[{"delta":{"content":"A"}}]}\n\n'
            'data: {"choices":[{"delta":{"content":""}}]}\n\n'
            'data: {"choices":[{"delta":{"content":"B"}}]}\n\n'
            'data: [DONE]\n\n'
        )
        respx.post("https://test-nvidia.api.com/v1/chat/completions").mock(
            return_value=httpx.Response(
                200,
                content=sse_lines.encode(),
                headers={"content-type": "text/event-stream"},
            )
        )

        tokens = []
        async for token in nvidia_provider.stream(
            model="test-model", prompt="test"
        ):
            tokens.append(token)

        assert tokens == ["A", "B"]

    @respx.mock
    @pytest.mark.asyncio
    async def test_stream_http_error(self, nvidia_provider):
        """Non-200 status during stream raises ProviderAPIError."""
        respx.post("https://test-nvidia.api.com/v1/chat/completions").mock(
            return_value=httpx.Response(429, text="Rate limit exceeded")
        )

        with pytest.raises(ProviderAPIError):
            async for _ in nvidia_provider.stream(
                model="test-model", prompt="test"
            ):
                pass

    @respx.mock
    @pytest.mark.asyncio
    async def test_stream_timeout(self, nvidia_provider):
        """Timeout during stream raises ProviderTimeoutError."""
        respx.post("https://test-nvidia.api.com/v1/chat/completions").mock(
            side_effect=httpx.TimeoutException("stream timed out")
        )

        with pytest.raises(ProviderTimeoutError):
            async for _ in nvidia_provider.stream(
                model="test-model", prompt="test"
            ):
                pass


# ============================================================
# embedding() tests
# ============================================================

class TestNvidiaEmbedding:
    """Tests for NvidiaProvider.embedding()."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_embedding_success(self, nvidia_provider):
        """Successful embedding returns vector."""
        respx.post("https://test-nvidia.api.com/v1/embeddings").mock(
            return_value=httpx.Response(
                200,
                json={
                    "data": [
                        {"embedding": [0.1, 0.2, 0.3], "index": 0}
                    ],
                    "model": "nvidia/nv-embedqa-e5-v5",
                    "usage": {"prompt_tokens": 5, "total_tokens": 5},
                },
            )
        )

        result = await nvidia_provider.embedding(
            model="nvidia/nv-embedqa-e5-v5",
            input_text="Hello",
        )
        assert result == [0.1, 0.2, 0.3]

    @respx.mock
    @pytest.mark.asyncio
    async def test_embedding_sends_input_type(self, nvidia_provider):
        """Embedding request includes input_type='query' for NVIDIA models."""
        route = respx.post("https://test-nvidia.api.com/v1/embeddings").mock(
            return_value=httpx.Response(
                200,
                json={
                    "data": [{"embedding": [0.1], "index": 0}],
                    "usage": {},
                },
            )
        )

        await nvidia_provider.embedding(
            model="nvidia/nv-embedqa-e5-v5",
            input_text="Test",
        )

        request = route.calls[0].request
        body = json.loads(request.content)
        assert body["input_type"] == "query"

    @respx.mock
    @pytest.mark.asyncio
    async def test_embedding_empty_error(self, nvidia_provider):
        """Empty data array raises ProviderAPIError."""
        respx.post("https://test-nvidia.api.com/v1/embeddings").mock(
            return_value=httpx.Response(
                200,
                json={"data": [], "usage": {}},
            )
        )

        with pytest.raises(ProviderAPIError) as exc:
            await nvidia_provider.embedding(
                model="nvidia/nv-embedqa-e5-v5",
                input_text="Hello",
            )
        assert "Empty embedding returned" in exc.value.message

    @respx.mock
    @pytest.mark.asyncio
    async def test_embedding_http_error(self, nvidia_provider):
        """Non-200 status during embedding raises ProviderAPIError."""
        respx.post("https://test-nvidia.api.com/v1/embeddings").mock(
            return_value=httpx.Response(400, text='{"error": "bad model"}')
        )

        with pytest.raises(ProviderAPIError):
            await nvidia_provider.embedding(
                model="bad-model",
                input_text="Hello",
            )


# ============================================================
# supports_image() & close() tests
# ============================================================

class TestNvidiaHelpers:
    """Tests for supports_image() and close()."""

    def test_supports_image_returns_false(self, nvidia_provider):
        """supports_image() returns False (no vision support yet)."""
        assert nvidia_provider.supports_image("any-model") is False

    def test_name_property(self, nvidia_provider):
        """Provider name is 'nvidia'."""
        assert nvidia_provider.name == "nvidia"

    @pytest.mark.asyncio
    async def test_close(self, nvidia_provider):
        """close() calls aclose on the httpx client."""
        await nvidia_provider.close()
        assert nvidia_provider._client.is_closed


class TestNvidiaFetchModels:
    """Tests for NvidiaProvider.fetch_models()."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_models_sets_reasoning_from_curated_catalog(self, nvidia_provider):
        """Curated NVIDIA ids are marked as reasoning-capable."""
        respx.get("https://test-nvidia.api.com/v1/models").mock(
            return_value=httpx.Response(
                200,
                json={
                    "data": [
                        {"id": "qwen/qwen3-next-80b-a3b-thinking"},
                        {"id": "nvidia/nv-embedqa-e5-v5"},
                    ]
                },
            )
        )

        models = await nvidia_provider.fetch_models()

        assert len(models) == 2
        assert models[0].supports_reasoning is True
        assert models[1].supports_embedding is True
        assert models[1].supports_reasoning is False
