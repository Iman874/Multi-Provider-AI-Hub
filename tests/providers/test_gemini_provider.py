"""
Unit tests for GeminiProvider.

All API calls are mocked by patching genai.Client.
"""

from unittest.mock import MagicMock, patch
import pytest

from app.core.exceptions import (
    ProviderAPIError,
    ProviderConnectionError,
    ProviderTimeoutError,
)
from google.genai import types

# We use the gemini_provider fixture which already has a mocked genai.Client

# ============================================================
# Auth & Key Rotation tests
# ============================================================

class TestGeminiKeyRotation:
    """Tests for Gemini multi-key retry."""

    @pytest.mark.asyncio
    async def test_retry_on_429(self, gemini_provider):
        """429 on first key triggers retry with second key."""
        # First call: 429 error
        # Second call: success
        call_count = 0
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("429 RESOURCE_EXHAUSTED")
            mock_response = MagicMock()
            mock_response.text = "Success on retry"
            mock_response.usage_metadata = MagicMock(
                prompt_token_count=1,
                candidates_token_count=1,
                total_token_count=2,
            )
            return mock_response

        # Need to mock the client creation or the generate_content method
        # Since _get_client is overridden in fixture to return mock_client,
        # we mock the generate_content on the mock_client
        gemini_provider._client.models.generate_content.side_effect = side_effect

        result = await gemini_provider.generate(
            model="gemini-2.5-pro", prompt="Test"
        )
        assert "Success" in result["output"]
        assert call_count == 2

# ============================================================
# generate() tests
# ============================================================

class TestGeminiGenerate:
    """Tests for GeminiProvider.generate()."""

    @pytest.mark.asyncio
    async def test_generate_success(self, gemini_provider):
        """Successful generate returns normalized dict."""
        mock_response = MagicMock()
        mock_response.text = "Hello from Gemini!"
        mock_response.usage_metadata = MagicMock(
            prompt_token_count=5,
            candidates_token_count=8,
            total_token_count=13,
        )
        gemini_provider._client.models.generate_content.return_value = mock_response

        result = await gemini_provider.generate(
            model="gemini-2.5-pro",
            prompt="Hi",
        )

        assert result["output"] == "Hello from Gemini!"
        assert result["provider"] == "gemini"
        assert result["model"] == "gemini-2.5-pro"
        assert result["usage"]["prompt_tokens"] == 5
        assert result["usage"]["completion_tokens"] == 8
        assert result["usage"]["total_tokens"] == 13

    @pytest.mark.asyncio
    async def test_generate_timeout_error(self, gemini_provider):
        """Deadline exceeded raises ProviderTimeoutError."""
        gemini_provider._client.models.generate_content.side_effect = Exception("Deadline exceeded")

        with pytest.raises(ProviderTimeoutError) as exc:
            await gemini_provider.generate(model="gemini-2.5-pro", prompt="Hi")

        assert "timed out" in exc.value.message

    @pytest.mark.asyncio
    async def test_generate_connection_error(self, gemini_provider):
        """Network error raises ProviderConnectionError."""
        gemini_provider._client.models.generate_content.side_effect = Exception("Network unreachable")

        with pytest.raises(ProviderConnectionError) as exc:
            await gemini_provider.generate(model="gemini-2.5-pro", prompt="Hi")

        assert "Network unreachable" in exc.value.message

    @pytest.mark.asyncio
    async def test_generate_api_error_429(self, gemini_provider):
        """429 Resource Exhausted raises ProviderAPIError with status 429."""
        gemini_provider._client.models.generate_content.side_effect = Exception("429 RESOURCE_EXHAUSTED")

        with pytest.raises(ProviderAPIError) as exc:
            await gemini_provider.generate(model="gemini-2.5-pro", prompt="Hi")

        assert "HTTP 429" in exc.value.message

    @pytest.mark.asyncio
    async def test_generate_api_error_status_code_attr(self, gemini_provider):
        """Exception with status_code attribute is parsed correctly."""
        class MockException(Exception):
            status_code = 403

        gemini_provider._client.models.generate_content.side_effect = MockException("Forbidden")

        with pytest.raises(ProviderAPIError) as exc:
            await gemini_provider.generate(model="gemini-2.5-pro", prompt="Hi")

        assert "HTTP 403" in exc.value.message


# ============================================================
# stream() tests
# ============================================================

class TestGeminiStream:
    """Tests for GeminiProvider.stream()."""

    @pytest.mark.asyncio
    async def test_stream_success(self, gemini_provider):
        """Stream yields tokens from response chunks."""
        chunk1 = MagicMock()
        chunk1.text = "Hello"
        chunk2 = MagicMock()
        chunk2.text = " world"
        
        gemini_provider._client.models.generate_content_stream.return_value = [chunk1, chunk2]

        tokens = []
        async for token in gemini_provider.stream(
            model="gemini-2.5-pro", prompt="Hi"
        ):
            tokens.append(token)

        assert tokens == ["Hello", " world"]

    @pytest.mark.asyncio
    async def test_stream_timeout_error(self, gemini_provider):
        """Timeout during stream raises ProviderTimeoutError."""
        gemini_provider._client.models.generate_content_stream.side_effect = Exception("Deadline exceeded")

        with pytest.raises(ProviderTimeoutError):
            async for _ in gemini_provider.stream(
                model="gemini-2.5-pro", prompt="Hi"
            ):
                pass

    @pytest.mark.asyncio
    async def test_stream_api_error(self, gemini_provider):
        """API error during stream raises ProviderAPIError."""
        class MockAPIError(Exception):
            code = 500

        gemini_provider._client.models.generate_content_stream.side_effect = MockAPIError("Internal Error")

        with pytest.raises(ProviderAPIError) as exc:
            async for _ in gemini_provider.stream(
                model="gemini-2.5-pro", prompt="Hi"
            ):
                pass
        
        assert "HTTP 500" in exc.value.message


# ============================================================
# embedding() tests
# ============================================================

class TestGeminiEmbedding:
    """Tests for GeminiProvider.embedding()."""

    @pytest.mark.asyncio
    async def test_embedding_success(self, gemini_provider):
        """Successful embed returns vector."""
        mock_embedding = MagicMock()
        mock_embedding.embeddings = [MagicMock(values=[0.1, 0.2, 0.3])]
        gemini_provider._client.models.embed_content.return_value = mock_embedding

        result = await gemini_provider.embedding(
            model="text-embedding-004",
            input_text="Hello",
        )
        assert result == [0.1, 0.2, 0.3]

    @pytest.mark.asyncio
    async def test_embedding_empty_error(self, gemini_provider):
        """Empty embeddings array raises ProviderAPIError."""
        mock_embedding = MagicMock()
        mock_embedding.embeddings = []
        gemini_provider._client.models.embed_content.return_value = mock_embedding

        with pytest.raises(ProviderAPIError) as exc:
            await gemini_provider.embedding(
                model="text-embedding-004",
                input_text="Hello",
            )
        assert "Empty embedding returned" in exc.value.message

    @pytest.mark.asyncio
    async def test_embedding_api_error_404(self, gemini_provider):
        """404 error string raises ProviderAPIError with status 404."""
        gemini_provider._client.models.embed_content.side_effect = Exception("404 Model not found")

        with pytest.raises(ProviderAPIError) as exc:
             await gemini_provider.embedding(
                model="invalid-model",
                input_text="Hello",
            )
        assert "HTTP 404" in exc.value.message

    @pytest.mark.asyncio
    async def test_embedding_timeout_error(self, gemini_provider):
        """Timeout raises ProviderTimeoutError."""
        gemini_provider._client.models.embed_content.side_effect = Exception("timeout during embed")

        with pytest.raises(ProviderTimeoutError):
             await gemini_provider.embedding(
                model="text-embedding-004",
                input_text="Hello",
            )


# ============================================================
# _build_contents() tests
# ============================================================

class TestGeminiBuildContents:
    """Tests for GeminiProvider._build_contents()."""

    def test_build_contents_text_only(self, gemini_provider):
        """Text only returns list with single string."""
        contents = gemini_provider._build_contents(prompt="Hello World")
        assert contents == ["Hello World"]

    @patch("app.providers.gemini.types.Part.from_bytes")
    def test_build_contents_with_images(self, mock_from_bytes, gemini_provider):
        """Images are parsed and appended as Part objects."""
        mock_part = MagicMock()
        mock_from_bytes.return_value = mock_part
        
        # We can use a 1x1 base64 GIF to pass validation
        fake_b64 = "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
        
        contents = gemini_provider._build_contents(
            prompt="Hello World",
            images=[fake_b64]
        )
        
        assert len(contents) == 2
        assert contents[0] == "Hello World"
        assert contents[1] == mock_part
        mock_from_bytes.assert_called_once()


# ============================================================
# supports_image() & close() tests
# ============================================================

class TestGeminiHelpers:
    """Tests for supports_image(), name, and close()."""

    def test_supports_image_returns_true(self, gemini_provider):
        """supports_image() always returns True."""
        assert gemini_provider.supports_image("any-model") is True

    def test_name_property(self, gemini_provider):
        """Provider name is 'gemini'."""
        assert gemini_provider.name == "gemini"

    @pytest.mark.asyncio
    async def test_close(self, gemini_provider):
        """close() is a no-op that completes without error."""
        await gemini_provider.close()


class TestGeminiFetchModels:
    """Tests for GeminiProvider.fetch_models()."""

    @pytest.mark.asyncio
    async def test_fetch_models_sets_reasoning_from_metadata(self, gemini_provider):
        """Gemini model metadata drives supports_reasoning."""
        text_model = MagicMock()
        text_model.name = "models/gemini-2.5-pro"
        text_model.thinking = True

        embedding_model = MagicMock()
        embedding_model.name = "models/text-embedding-004"
        embedding_model.thinking = False

        gemini_provider._client.models.list.return_value = [text_model, embedding_model]

        models = await gemini_provider.fetch_models()

        assert len(models) == 2
        assert models[0].name == "gemini-2.5-pro"
        assert models[0].supports_reasoning is True
        assert models[1].supports_embedding is True
        assert models[1].supports_reasoning is False
