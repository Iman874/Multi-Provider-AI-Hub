"""
Unit tests for OllamaProvider.

All HTTP calls are mocked using `respx` — no real Ollama instance needed.
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
from app.providers.ollama import OllamaProvider

# We can re-use the ollama_provider fixture from conftest.py
# by passing `ollama_provider` as an argument to our tests.

# ============================================================
# Auth tests
# ============================================================

class TestOllamaCloudAuth:
    """Tests for Ollama Cloud authentication headers."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_cloud_sends_auth_header(self, ollama_provider_cloud):
        """Cloud provider sends Authorization header."""
        route = respx.post("http://test-ollama:11434/api/generate").mock(
            return_value=httpx.Response(200, json={
                "response": "cloud reply", "done": True,
            })
        )

        await ollama_provider_cloud.generate(model="glm-5.1:cloud", prompt="Hi")

        request = route.calls[0].request
        assert "Authorization" in request.headers
        assert request.headers["Authorization"].startswith("Bearer test-cloud-key-abc")

    @respx.mock
    @pytest.mark.asyncio
    async def test_local_no_auth_header(self, ollama_provider):
        """Local provider does NOT send Authorization header."""
        route = respx.post("http://test-ollama:11434/api/generate").mock(
            return_value=httpx.Response(200, json={
                "response": "local reply", "done": True,
            })
        )

        await ollama_provider.generate(model="gemma4:e2b", prompt="Hi")

        request = route.calls[0].request
        assert "Authorization" not in request.headers

# ============================================================
# generate() tests
# ============================================================

class TestOllamaGenerate:
    """Tests for OllamaProvider.generate()."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_generate_success(self, ollama_provider):
        """Successful generate returns normalized dict."""
        respx.post("http://test-ollama:11434/api/generate").mock(
            return_value=httpx.Response(
                200,
                json={
                    "model": "gemma4:e2b",
                    "response": "Hello! How can I help?",
                    "done": True,
                    "prompt_eval_count": 5,
                    "eval_count": 8,
                    "total_duration": 1234567890,
                    "load_duration": 100000000,
                },
            )
        )

        result = await ollama_provider.generate(
            model="gemma4:e2b",
            prompt="Hello",
        )

        assert result["output"] == "Hello! How can I help?"
        assert result["provider"] == "ollama"
        assert result["model"] == "gemma4:e2b"
        assert result["usage"]["prompt_tokens"] == 5
        assert result["usage"]["completion_tokens"] == 8
        assert result["usage"]["total_tokens"] == 13

    @respx.mock
    @pytest.mark.asyncio
    async def test_generate_payload_format(self, ollama_provider):
        """Verify the JSON payload sent to Ollama API."""
        route = respx.post("http://test-ollama:11434/api/generate").mock(
            return_value=httpx.Response(
                200,
                json={"response": "ok", "done": True},
            )
        )

        await ollama_provider.generate(model="gemma4:e2b", prompt="Test prompt")

        request = route.calls[0].request
        body = json.loads(request.content)
        assert body["model"] == "gemma4:e2b"
        assert body["prompt"] == "Test prompt"
        assert body["stream"] is False

    @respx.mock
    @pytest.mark.asyncio
    async def test_generate_with_images(self, ollama_provider):
        """Images are included in payload with data URI stripped."""
        route = respx.post("http://test-ollama:11434/api/generate").mock(
            return_value=httpx.Response(
                200,
                json={"response": "I see an image", "done": True},
            )
        )

        await ollama_provider.generate(
            model="gemma4:e2b",
            prompt="Describe",
            images=["data:image/jpeg;base64,/9j/4AAQ", "/9j/RAW"],
        )

        request = route.calls[0].request
        body = json.loads(request.content)
        # data URI prefix should be stripped
        assert body["images"] == ["/9j/4AAQ", "/9j/RAW"]

    @respx.mock
    @pytest.mark.asyncio
    async def test_generate_http_error(self, ollama_provider):
        """Non-200 status raises ProviderAPIError."""
        respx.post("http://test-ollama:11434/api/generate").mock(
            return_value=httpx.Response(
                404,
                text='{"error":"model not found"}',
            )
        )

        with pytest.raises(ProviderAPIError) as exc:
            await ollama_provider.generate(model="nonexistent", prompt="hi")

        assert "HTTP 404" in exc.value.message

    @respx.mock
    @pytest.mark.asyncio
    async def test_generate_timeout(self, ollama_provider):
        """Timeout raises ProviderTimeoutError."""
        respx.post("http://test-ollama:11434/api/generate").mock(
            side_effect=httpx.TimeoutException("timed out")
        )

        with pytest.raises(ProviderTimeoutError) as exc:
            await ollama_provider.generate(model="gemma4:e2b", prompt="hi")

        assert "timed out" in exc.value.message

    @respx.mock
    @pytest.mark.asyncio
    async def test_generate_connection_error(self, ollama_provider):
        """Connection refused raises ProviderConnectionError."""
        respx.post("http://test-ollama:11434/api/generate").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        with pytest.raises(ProviderConnectionError) as exc:
            await ollama_provider.generate(model="gemma4:e2b", prompt="hi")

        assert "Connection refused" in exc.value.message


# ============================================================
# stream() tests
# ============================================================

class TestOllamaStream:
    """Tests for OllamaProvider.stream()."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_stream_success(self, ollama_provider):
        """Stream yields tokens from NDJSON lines."""
        ndjson_lines = (
            '{"model":"gemma4:e2b","response":"Hello","done":false}\n'
            '{"model":"gemma4:e2b","response":" world","done":false}\n'
            '{"model":"gemma4:e2b","response":"","done":true}\n'
        )
        respx.post("http://test-ollama:11434/api/generate").mock(
            return_value=httpx.Response(
                200,
                content=ndjson_lines.encode(),
                headers={"content-type": "application/x-ndjson"},
            )
        )

        tokens = []
        async for token in ollama_provider.stream(
            model="gemma4:e2b", prompt="Hi"
        ):
            tokens.append(token)

        assert tokens == ["Hello", " world"]

    @respx.mock
    @pytest.mark.asyncio
    async def test_stream_skips_malformed_json(self, ollama_provider):
        """Malformed JSON lines are skipped without crashing."""
        ndjson_lines = (
            '{"response":"Good","done":false}\n'
            'NOT-VALID-JSON\n'
            '{"response":" day","done":false}\n'
            '{"response":"","done":true}\n'
        )
        respx.post("http://test-ollama:11434/api/generate").mock(
            return_value=httpx.Response(
                200,
                content=ndjson_lines.encode(),
                headers={"content-type": "application/x-ndjson"},
            )
        )

        tokens = []
        async for token in ollama_provider.stream(
            model="gemma4:e2b", prompt="Hi"
        ):
            tokens.append(token)

        assert tokens == ["Good", " day"]

    @respx.mock
    @pytest.mark.asyncio
    async def test_stream_skips_empty_lines(self, ollama_provider):
        """Empty lines in NDJSON are skipped."""
        ndjson_lines = (
            '{"response":"A","done":false}\n'
            '\n'
            '   \n'
            '{"response":"B","done":false}\n'
            '{"response":"","done":true}\n'
        )
        respx.post("http://test-ollama:11434/api/generate").mock(
            return_value=httpx.Response(
                200,
                content=ndjson_lines.encode(),
                headers={"content-type": "application/x-ndjson"},
            )
        )

        tokens = []
        async for token in ollama_provider.stream(
            model="gemma4:e2b", prompt="test"
        ):
            tokens.append(token)

        assert tokens == ["A", "B"]

    @respx.mock
    @pytest.mark.asyncio
    async def test_stream_http_error(self, ollama_provider):
        """Non-200 status during stream raises ProviderAPIError."""
        respx.post("http://test-ollama:11434/api/generate").mock(
            return_value=httpx.Response(500, text="Internal server error")
        )

        with pytest.raises(ProviderAPIError):
            async for _ in ollama_provider.stream(
                model="gemma4:e2b", prompt="test"
            ):
                pass

    @respx.mock
    @pytest.mark.asyncio
    async def test_stream_timeout(self, ollama_provider):
        """Timeout during stream raises ProviderTimeoutError."""
        respx.post("http://test-ollama:11434/api/generate").mock(
            side_effect=httpx.TimeoutException("stream timed out")
        )

        with pytest.raises(ProviderTimeoutError):
            async for _ in ollama_provider.stream(
                model="gemma4:e2b", prompt="test"
            ):
                pass

    @respx.mock
    @pytest.mark.asyncio
    async def test_stream_connection_error(self, ollama_provider):
        """Connection error during stream raises ProviderConnectionError."""
        respx.post("http://test-ollama:11434/api/generate").mock(
            side_effect=httpx.ConnectError("refused")
        )

        with pytest.raises(ProviderConnectionError):
            async for _ in ollama_provider.stream(
                model="gemma4:e2b", prompt="test"
            ):
                pass


# ============================================================
# embedding() tests
# ============================================================

class TestOllamaEmbedding:
    """Tests for OllamaProvider.embedding()."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_embedding_success(self, ollama_provider):
        """Successful embedding returns vector."""
        respx.post("http://test-ollama:11434/api/embed").mock(
            return_value=httpx.Response(
                200,
                json={"embeddings": [[0.1, 0.2, 0.3]]},
            )
        )

        result = await ollama_provider.embedding(
            model="qwen3-embedding:0.6b",
            input_text="Hello",
        )
        assert result == [0.1, 0.2, 0.3]
        
    @respx.mock
    @pytest.mark.asyncio
    async def test_embedding_empty_error(self, ollama_provider):
        """Empty embeddings array raises ProviderAPIError."""
        respx.post("http://test-ollama:11434/api/embed").mock(
            return_value=httpx.Response(
                200,
                json={"embeddings": []},
            )
        )

        with pytest.raises(ProviderAPIError) as exc:
            await ollama_provider.embedding(
                model="qwen3-embedding:0.6b",
                input_text="Hello",
            )
        assert "Empty embedding returned" in exc.value.message

    @respx.mock
    @pytest.mark.asyncio
    async def test_embedding_http_error(self, ollama_provider):
        """Non-200 status during embedding raises ProviderAPIError."""
        respx.post("http://test-ollama:11434/api/embed").mock(
            return_value=httpx.Response(500, text="Internal server error")
        )

        with pytest.raises(ProviderAPIError):
             await ollama_provider.embedding(
                model="qwen3-embedding:0.6b",
                input_text="Hello",
            )

# ============================================================
# supports_image() & close() tests
# ============================================================

class TestOllamaHelpers:
    """Tests for supports_image() and close()."""

    def test_supports_image_returns_true(self, ollama_provider):
        """supports_image() always returns True."""
        assert ollama_provider.supports_image("any-model") is True

    def test_name_property(self, ollama_provider):
        """Provider name is 'ollama'."""
        assert ollama_provider.name == "ollama"

    @pytest.mark.asyncio
    async def test_close(self, ollama_provider):
        """close() calls aclose on the httpx client."""
        await ollama_provider.close()
        # After close, client should be closed
        assert ollama_provider._client.is_closed


class TestOllamaFetchModels:
    """Tests for OllamaProvider.fetch_models()."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_models_sets_reasoning_from_show_details(self, ollama_provider):
        """Text models use /api/show metadata to detect reasoning support."""
        respx.get("http://test-ollama:11434/api/tags").mock(
            return_value=httpx.Response(
                200,
                json={
                    "models": [
                        {"name": "qwen3:8b"},
                        {"name": "qwen3-embedding:0.6b"},
                    ]
                },
            )
        )
        respx.post("http://test-ollama:11434/api/show").mock(
            return_value=httpx.Response(
                200,
                json={"family": "qwen3", "capabilities": ["completion", "thinking"]},
            )
        )

        models = await ollama_provider.fetch_models()

        assert len(models) == 2
        assert models[0].name == "qwen3:8b"
        assert models[0].supports_reasoning is True
        assert models[1].supports_embedding is True
        assert models[1].supports_reasoning is False

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_models_falls_back_when_show_fails(self, ollama_provider):
        """Reasoning discovery degrades gracefully when /api/show fails."""
        respx.get("http://test-ollama:11434/api/tags").mock(
            return_value=httpx.Response(
                200,
                json={"models": [{"name": "llama3.2"}]},
            )
        )
        respx.post("http://test-ollama:11434/api/show").mock(
            return_value=httpx.Response(404, json={"error": "not found"})
        )

        models = await ollama_provider.fetch_models()

        assert len(models) == 1
        assert models[0].supports_reasoning is False
